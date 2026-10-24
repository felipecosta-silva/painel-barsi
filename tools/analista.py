"""Fehmir · Analista automático — etapa 1 (alertas, sem Gemini).

Decide sozinho quais ativos da carteira e do radar merecem atenção e grava dados/alertas.js com estado
("desde", "ativo"/"resolvido"). Os tetos vêm de dados/tetos.js (tools/exportar_tetos.js = mesma régua do painel).
Spec: specs/001-analista-automatico (fora do Git).

Uso:
  python tools/analista.py                      # gera dados/alertas.js
  python tools/analista.py --seco               # só mostra, não grava
  python tools/analista.py --simular ITUB4=38   # testa com um preço fictício (não grava)
  python tools/analista.py --simular-base PETR4.dpa12=+50%   # testa mudança contra a base (não grava)
"""
import sys, re, json, datetime, pathlib

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDA = DADOS / "alertas.js"

LIMIARES = {"movimento_pp": 8, "janela": 5, "provento_pct": 15, "lucro_pct": 15, "realizacao": 1.2,
            "documento_dias": 3, "resolvido_dias": 5, "pareceres_dia": 8}
SETORES_BASE = ("Bancos", "Seguradoras", "Elétricas", "Água")       # radar da B.A.S.E. sobe para prioridade alta
PRIORIDADE = {"alta": 0, "media": 1, "info": 2}


def ler_var(arquivo, nome, padrao=None):
    """Lê `window.NOME = <json>;` de um dados/*.js."""
    p = DADOS / arquivo
    if not p.exists():
        return padrao
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"window\." + re.escape(nome) + r"\s*=\s*", txt)
    if not m:
        return padrao
    try:
        return json.JSONDecoder().raw_decode(txt, m.end())[0]
    except Exception:
        return padrao


def br(v, d=2):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def var_pct(c, n):
    return (c[-1] / c[-1 - n] - 1) * 100 if len(c) > n and c[-1 - n] > 0 else None


def main(argv):
    seco = "--seco" in argv or any(a.startswith("--simular") for a in argv)
    sim_preco, sim_base = {}, {}
    for i, a in enumerate(argv):
        if a == "--simular" and i + 1 < len(argv):
            t, v = argv[i + 1].split("="); sim_preco[t.upper()] = float(v)
        if a == "--simular-base" and i + 1 < len(argv):
            k, v = argv[i + 1].split("="); t, campo = k.split("."); sim_base[(t.upper(), campo)] = float(v.strip("%+")) * (1 if "-" not in v else -1)

    H = ler_var("historico.js", "FEHMIR_HIST", {}) or {}
    T = ler_var("tetos.js", "FEHMIR_TETOS", {}) or {}
    CART = ler_var("tetos.js", "FEHMIR_CARTEIRA", {}) or {}
    CVM = ler_var("fundamentos_cvm.js", "FEHMIR_FUND_CVM", {}) or {}
    NOV = ler_var("novidades.js", "FEHMIR_NOVIDADES", {}) or {}
    MERC = {x.get("t"): x for x in (ler_var("mercado.js", "FEHMIR_MERCADO", []) or [])}
    anterior = ler_var("alertas.js", "FEHMIR_ALERTAS", {}) or {}
    base_ant = (anterior.get("meta") or {}).get("base_fundamentos") or {}
    itens_ant = {x["id"]: x for x in (anterior.get("itens") or [])}
    print(f"historico: {len(H)} · tetos: {len(T)} · carteira: {len(CART)} · CVM: {len(CVM)} · novidades: {len(NOV)} · alertas anteriores: {len(itens_ant)}")

    hoje = datetime.date.today().isoformat()
    novos = {}

    def alerta(t, tipo, prio, texto, numeros, origem):
        novos[f"{t}:{tipo}"] = {"id": f"{t}:{tipo}", "ticker": t, "tipo": tipo, "prioridade": prio, "texto": texto,
                                 "numeros": numeros, "origem": origem, "carteira": t in CART}

    def eh_fii(t):
        s = (T.get(t) or {}).get("setor", "") or ""
        if "FII" in s or "Fiagro" in s:
            return True
        return (MERC.get(t) or {}).get("tp") == "fii"

    # Peso atual de ações e FIIs na carteira × meta (ALOCACAO_ALVO do painel): compra só em classe abaixo da meta.
    metas = {"acoes": 35, "fiis": 45}
    m_alvo = re.search(r"const ALOCACAO_ALVO = \{([^}]*)\}", (RAIZ / "painel-barsi.html").read_text(encoding="utf-8", errors="ignore"))
    if m_alvo:
        for k in ("acoes", "fiis"):
            mk = re.search(k + r":\s*([\d.]+)", m_alvo.group(1))
            if mk:
                metas[k] = float(mk.group(1))
    valor = {"acoes": 0.0, "fiis": 0.0, "outros": 0.0}
    for t, q in CART.items():
        h = H.get(t) or {}
        pr = (h.get("c") or [0])[-1] or 0
        if h.get("moeda") == "USD" or t in ("BTC", "ETH", "SOL"):
            valor["outros"] += q * pr * (5 if h.get("moeda") == "USD" else 1)
        else:
            valor["fiis" if eh_fii(t) else "acoes"] += q * pr
    total = sum(valor.values()) or 1
    peso = {k: valor[k] / total * 100 for k in ("acoes", "fiis")}
    print(f"classes: ações {br(peso['acoes'], 0)}% (meta {br(metas['acoes'], 0)}%) · FIIs {br(peso['fiis'], 0)}% (meta {br(metas['fiis'], 0)}%)")

    idx = {"acao": H.get("^BVSP"), "fii": H.get("XFIX11")}
    n = LIMIARES["janela"]
    universo = [t for t in H if not t.startswith("^") and t not in ("USDBRL", "XFIX11", "SMAL11", "IVVB11")]

    for t in universo:
        h = H[t]; c = list(h.get("c") or []); d = h.get("d") or []
        if len(c) < n + 1 or h.get("moeda") == "USD" or t in ("BTC", "ETH", "SOL"):
            continue
        if t in sim_preco:
            c[-1] = sim_preco[t]
        preco, data = c[-1], (d[-1] if d else hoje)
        na_cart = t in CART
        origem_preco = {"fonte": "robô de preços (Yahoo)", "data": data}

        # 1. Movimento forte contra o índice
        ref = idx["fii" if eh_fii(t) else "acao"]
        va, vi = var_pct(c, n), var_pct(ref.get("c") or [], n) if ref else None
        if va is not None and vi is not None and abs(va - vi) >= LIMIARES["movimento_pp"]:
            nome_idx = "IFIX (XFIX11)" if eh_fii(t) else "Ibovespa"
            alerta(t, "movimento", "media" if na_cart else "info",
                   f"{t} {'+' if va >= 0 else '−'}{br(abs(va), 1)}% em {n} pregões ({nome_idx} {'+' if vi >= 0 else '−'}{br(abs(vi), 1)}%)",
                   {"var": round(va, 2), "var_indice": round(vi, 2), "preco": preco}, origem_preco)

        # 2. Zonas de preço pela régua oficial
        tt = T.get(t)
        if tt and tt.get("compra"):
            setor = tt.get("setor", "")
            if preco <= tt["compra"]:
                classe = "fiis" if eh_fii(t) else "acoes"
                cheia = peso[classe] >= metas[classe]
                prio = "info" if cheia else ("alta" if (na_cart or setor.startswith(SETORES_BASE)) else "info")
                aviso = (f" — mas a classe {'FIIs' if classe == 'fiis' else 'ações'} está em {br(peso[classe], 0)}% (meta {br(metas[classe], 0)}%): aportes pausados"
                         if cheia else "")
                alerta(t, "zona_compra", prio,
                       f"{t} abaixo do preço de compra: R$ {br(preco)} ≤ R$ {br(tt['compra'])} (teto R$ {br(tt['teto'])}, {tt.get('metodo', '')}){aviso}",
                       {"preco": preco, "compra": tt["compra"], "teto": tt["teto"]}, origem_preco)
            elif na_cart and preco >= tt["teto"] * LIMIARES["realizacao"]:
                alerta(t, "zona_realizacao", "media",
                       f"{t} na zona de realização: R$ {br(preco)} ≥ teto × {br(LIMIARES['realizacao'], 1)} (R$ {br(tt['teto'] * LIMIARES['realizacao'])}). "
                       "B.A.S.E. só se vende por fundamento; FII nunca por rebalanceamento.",
                       {"preco": preco, "teto": tt["teto"]}, origem_preco)

    # 3 e 4. Proventos e fundamentos contra a base anterior (primeira execução só grava a base)
    base_nova = {}
    for t in set(universo) | set(CVM):
        dpa12 = (H.get(t) or {}).get("dpa12")
        f = CVM.get(t) or {}
        base_nova[t] = {"dpa12": dpa12, "lucro12m": f.get("lucro12m"), "roe": f.get("roe")}
        b = dict(base_ant.get(t) or {})
        for (st, campo), pct in sim_base.items():
            if st == t and b.get(campo):
                b[campo] = b[campo] / (1 + pct / 100)
        if not b:
            continue
        na_cart = t in CART
        if dpa12 is not None and b.get("dpa12"):
            dv = (dpa12 / b["dpa12"] - 1) * 100
            if abs(dv) >= LIMIARES["provento_pct"]:
                alerta(t, "provento", "alta" if (dv < 0 and na_cart) else "info",
                       f"{t}: proventos de 12 meses {'caíram' if dv < 0 else 'subiram'} {br(abs(dv), 0)}% (R$ {br(b['dpa12'], 4)} → R$ {br(dpa12, 4)} por cota/ação)",
                       {"dpa12": dpa12, "dpa12_antes": round(b["dpa12"], 4)}, {"fonte": "robô de preços (proventos)", "data": hoje})
        if f.get("lucro12m") and b.get("lucro12m"):
            dl = (f["lucro12m"] / b["lucro12m"] - 1) * 100
            if abs(dl) >= LIMIARES["lucro_pct"]:
                alerta(t, "fundamento", "alta" if (dl < 0 and na_cart) else "info",
                       f"{t}: lucro de 12 meses {'caiu' if dl < 0 else 'subiu'} {br(abs(dl), 0)}% na CVM ({f.get('ref', '')}); ROE {br(f.get('roe') or 0, 1)}%",
                       {"lucro12m": f["lucro12m"], "lucro12m_antes": b["lucro12m"], "roe": f.get("roe")},
                       {"fonte": "CVM (ITR/DFP)", "data": f.get("ref", "")})

    # 5. Documentos novos dos ativos da carteira (robô de novidades)
    limite = (datetime.date.today() - datetime.timedelta(days=LIMIARES["documento_dias"])).isoformat()
    for t, docs in NOV.items():
        if t not in CART:
            continue
        recentes = [x for x in (docs or []) if (x.get("data") or "") >= limite]
        if not recentes:
            continue
        g = {"critico": 0, "atencao": 1}
        doc = sorted(recentes, key=lambda x: (g.get(x.get("gravidade"), 2), x.get("data", "")))[0]
        prio = {"critico": "alta", "atencao": "media"}.get(doc.get("gravidade"), "info")
        extra = f" (+{len(recentes) - 1})" if len(recentes) > 1 else ""
        tipo_doc, titulo = (doc.get("tipo") or "documento"), (doc.get("titulo") or "")
        rotulo = tipo_doc if (not titulo or titulo.strip().lower() == tipo_doc.strip().lower()) else f"{tipo_doc} — {titulo}"
        alerta(t, "documento", prio, f"{t}: {rotulo}{extra}",
               {"documentos": len(recentes)}, {"fonte": "CVM/Fundos.NET", "link": doc.get("url"), "data": doc.get("data")})

    # Estado: mantém "desde", resolve o que sumiu, apaga resolvido antigo
    itens = []
    for k, a in novos.items():
        ant = itens_ant.get(k)
        a["desde"] = ant["desde"] if (ant and ant.get("estado") == "ativo") else hoje
        a["ultimo"] = hoje
        a["estado"] = "ativo"
        itens.append(a)
    corte = (datetime.date.today() - datetime.timedelta(days=LIMIARES["resolvido_dias"])).isoformat()
    for k, a in itens_ant.items():
        if k in novos:
            continue
        if a.get("estado") == "ativo":
            a = dict(a, estado="resolvido", resolvido=hoje)
        if a.get("estado") == "resolvido" and (a.get("resolvido") or hoje) >= corte:
            itens.append(a)
    itens.sort(key=lambda x: (x["estado"] != "ativo", PRIORIDADE.get(x["prioridade"], 9), not x.get("carteira"), x["ticker"]))

    ativos = [x for x in itens if x["estado"] == "ativo"]
    cont = {p: sum(1 for x in ativos if x["prioridade"] == p) for p in PRIORIDADE}
    print(f"alertas ativos: {len(ativos)} (alta {cont['alta']} · média {cont['media']} · info {cont['info']}) · resolvidos guardados: {len(itens) - len(ativos)}")
    for x in ativos:
        if x["prioridade"] != "info" or seco:
            print(f"  [{x['prioridade']}] {x['texto']}  · desde {x['desde']}")

    if seco:
        print("(--seco/--simular: nada gravado)")
        return 0
    meta = {"gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "verificados": len(universo), "ativos": len(ativos),
            "limiares": LIMIARES, "base_fundamentos": base_nova if not base_ant else {**base_ant, **base_nova},
            "pareceres_pendentes": []}
    SAIDA.write_text("/* Gerado por tools/analista.py — não editar à mão. */\nwindow.FEHMIR_ALERTAS = " +
                     json.dumps({"meta": meta, "itens": itens}, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"OK: {SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
