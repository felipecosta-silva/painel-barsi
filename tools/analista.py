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
import sys, os, re, json, datetime, pathlib, urllib.request, ssl

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

DADOS = RAIZ / "dados"
SAIDA = DADOS / "alertas.js"
PARECERES_PATH = DADOS / "pareceres.js"
LICOES_CANDIDATAS_PATH = DADOS / "licoes_candidatas.js"
LICOES_ANALISTA_PATH = DADOS / "licoes_analista.js"

LIMIARES = {"movimento_pp": 8, "janela": 5, "provento_pct": 15, "lucro_pct": 15, "realizacao": 1.2,
            "documento_dias": 3, "resolvido_dias": 5, "pareceres_dia": 8}
SETORES_BASE = ("Bancos", "Seguradoras", "Elétricas", "Água", "Telecom", "Saneamento")       # radar da B.A.S.E. sobe para prioridade alta
PRIORIDADE = {"alta": 0, "media": 1, "info": 2}

SCHEMA_PARECER_ANALISTA = {
    "type": "OBJECT",
    "properties": {
        "fatos": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Fatos relevantes extraídos estritamente dos documentos oficiais ou da ficha técnica"
        },
        "causa": {
            "type": "STRING",
            "description": "Causa em camadas: ativo | fluxo | macro (qual domina e por quê)"
        },
        "risco": {
            "type": "STRING",
            "enum": ["idiossincratico", "estrutural"],
            "description": "Classificação do risco principal: idiossincratico (específico) ou estrutural"
        },
        "risco_motivo": {
            "type": "STRING",
            "description": "Explicação objetiva do risco"
        },
        "veredito": {
            "type": "STRING",
            "enum": ["comprar", "manter_sem_aportar", "manter", "realizar_parte", "vender", "estudo"],
            "description": "Veredito objetivo sobre o ativo"
        },
        "gatilhos_mudanca": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Condições objetivas para mudar de ideia sobre o veredito"
        },
        "custo_executar": {
            "type": "STRING",
            "description": "Estimativa de custos práticos para executar a decisão"
        },
        "licao_generica": {
            "type": "STRING",
            "description": "1 regra de análise aprendida de forma geral (ou null se nenhuma)"
        }
    },
    "required": [
        "fatos", "causa", "risco", "risco_motivo", "veredito",
        "gatilhos_mudanca", "custo_executar"
    ]
}

MAPA_SETOR_TAGS = {
    "banc": "banco",
    "segur": "seguradora",
    "elétr": "eletrica",
    "energia": "eletrica",
    "transmiss": "eletrica",
    "telecom": "telecom",
    "commodit": "ciclica",
    "construção": "ciclica",
    "varejo": "ciclica",
    "metal": "ciclica",
    "sider": "ciclica",
    "papel": "ciclica",
    "celulose": "ciclica",
    "crescimento": "crescimento",
    "tecnologia": "crescimento",
    "imobi": "imobiliaria",
    "internacional": "internacional",
    "cripto": "cripto"
}


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


def carregar_licoes_analista():
    return ler_var("licoes_analista.js", "FEHMIR_LICOES_ANALISTA", []) or []


def escolher_licoes(ticker, setor, eh_fii_flag):
    licoes = carregar_licoes_analista()
    tags_alvo = set()
    if eh_fii_flag:
        tags_alvo.add("fii")
    s_lower = (setor or "").lower()
    for k, tag in MAPA_SETOR_TAGS.items():
        if k in s_lower:
            tags_alvo.add(tag)
    
    escolhidas = []
    tk_upper = ticker.upper()
    for l in licoes:
        temas = l.get("tema") or []
        if isinstance(temas, str):
            temas = [temas]
        match_tema = any(t in tags_alvo for t in temas)
        match_ticker = tk_upper in (l.get("texto") or "").upper()
        if match_tema or match_ticker:
            escolhidas.append(l)

    escolhidas.sort(key=lambda x: x.get("data", ""), reverse=True)
    return escolhidas[:8]


def montar_ficha(ticker, H=None, T=None, CVM=None, NOV=None, CART=None):
    if H is None: H = ler_var("historico.js", "FEHMIR_HIST", {}) or {}
    if T is None: T = ler_var("tetos.js", "FEHMIR_TETOS", {}) or {}
    if CVM is None: CVM = ler_var("fundamentos_cvm.js", "FEHMIR_FUND_CVM", {}) or {}
    if NOV is None: NOV = ler_var("novidades.js", "FEHMIR_NOVIDADES", {}) or {}
    if CART is None: CART = ler_var("tetos.js", "FEHMIR_CARTEIRA", {}) or {}

    h = H.get(ticker, {})
    c = list(h.get("c") or [])
    d = h.get("d") or []
    preco = c[-1] if c else None
    data = d[-1] if d else datetime.date.today().isoformat()
    
    t_info = T.get(ticker, {})
    setor = t_info.get("setor") or ("Fundo Imobiliário" if ticker.endswith("11") and ticker not in {"TAEE11", "ALUP11", "KLBN11", "SANB11", "BPAC11", "SAPR11", "ENGI11", "SULA11"} else "Geral")
    eh_fii = "FII" in setor or "Fiagro" in setor or (ticker.endswith("11") and ticker not in {"TAEE11", "ALUP11", "KLBN11", "SANB11", "BPAC11", "SAPR11", "ENGI11", "SULA11"})
    
    idx_ref = H.get("XFIX11" if eh_fii else "^BVSP", {})
    idx_nome = "IFIX (XFIX11)" if eh_fii else "Ibovespa"
    var5d = var_pct(c, 5) if len(c) > 5 else None
    var_idx_5d = var_pct(idx_ref.get("c") or [], 5) if idx_ref.get("c") and len(idx_ref.get("c")) > 5 else None

    teto = t_info.get("teto")
    compra = t_info.get("compra")
    metodo = t_info.get("metodo")
    margem = round((1 - preco / teto) * 100, 1) if (teto and preco) else None

    dpa12 = h.get("dpa12") or 0.0
    dpa5 = h.get("dpa5")
    
    um_ano_atras_iso = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    extras_12m = sum(e[1] for e in (h.get("extras") or []) if len(e) >= 2 and e[0] >= um_ano_atras_iso)
    dy12 = round((dpa12 / preco * 100), 2) if (preco and preco > 0) else None
    dy_recorrente = round((max(0.0, dpa12 - extras_12m) / preco * 100), 2) if (preco and preco > 0) else None

    cvm_info = CVM.get(ticker, {})
    roe = cvm_info.get("roe")
    roe_anual = cvm_info.get("roeAnual") or roe
    lucro12m = cvm_info.get("lucro12m")

    docs_raw = NOV.get(ticker, []) or []
    documentos = []
    for doc in docs_raw:
        documentos.append({
            "titulo": doc.get("titulo") or doc.get("tipo") or "Documento",
            "tipo": doc.get("tipo"),
            "data": doc.get("data"),
            "url": doc.get("url") or doc.get("link"),
            "resumo": doc.get("resumo") or doc.get("texto")
        })

    licoes = escolher_licoes(ticker, setor, eh_fii)

    return {
        "ticker": ticker,
        "preco": preco,
        "data": data,
        "var5d": var5d,
        "var_indice_5d": var_idx_5d,
        "indice_nome": idx_nome,
        "setor": setor,
        "eh_fii": eh_fii,
        "teto": teto,
        "compra": compra,
        "metodo": metodo,
        "margem": margem,
        "dpa12": dpa12,
        "dpa5": dpa5,
        "extras_12m": round(extras_12m, 4),
        "dy12": dy12,
        "dy_recorrente": dy_recorrente,
        "roe": roe,
        "roe_anual": roe_anual,
        "lucro12m": lucro12m,
        "carteira": ticker in CART,
        "documentos": documentos,
        "licoes": licoes
    }


def extrair_numeros_texto(texto):
    padrao = r'((?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+|\d+(?:\.\d+)?)(%?))'
    matches = []
    for m in re.finditer(padrao, texto):
        token_completo = m.group(1)
        raw_num = m.group(2).replace(".", "").replace(",", ".")
        tem_pct = bool(m.group(3))
        tem_rs = "R$" in token_completo
        try:
            val = float(raw_num)
            matches.append((token_completo, val, tem_pct, tem_rs))
        except ValueError:
            pass
    return matches


def coletar_numeros_ficha(ficha):
    nums = set()
    for k in ["preco", "teto", "compra", "margem", "dpa12", "dpa5", "dy12", "dy_recorrente", "roe", "lucro12m", "var5d", "var_indice_5d"]:
        v = ficha.get(k)
        if v is not None and isinstance(v, (int, float)):
            nums.add(round(abs(float(v)), 2))
    for d in ficha.get("documentos", []):
        res = d.get("resumo") or ""
        if isinstance(res, list):
            res = " ".join(str(x) for x in res)
        tit = d.get("titulo") or ""
        if isinstance(tit, list):
            tit = " ".join(str(x) for x in tit)
        for token, val, pct, rs in extrair_numeros_texto(str(tit) + " " + str(res)):
            nums.add(round(abs(val), 2))
    return nums


def numero_valido(val, tem_pct, tem_rs, nums_ficha):
    if not tem_pct and not tem_rs:
        if 1990 <= val <= 2035 or val in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 24, 30, 31, 365]:
            return True
    val_abs = abs(val)
    for fn in nums_ficha:
        if abs(val_abs - fn) <= max(0.05, fn * 0.01):
            return True
    return False


def verificar_numeros(parecer, ficha):
    nums_ficha = coletar_numeros_ficha(ficha)
    campos_texto = ["causa", "risco_motivo", "custo_executar"]
    motivo_parcial = None
    completo = True

    for campo in campos_texto:
        texto = parecer.get(campo, "")
        if not texto: continue
        frases = re.split(r'(\. |\n|; )', texto)
        novas_frases = []
        for f in frases:
            nums = extrair_numeros_texto(f)
            invalido = None
            for token, val, pct, rs in nums:
                if not numero_valido(val, pct, rs, nums_ficha):
                    invalido = token
                    break
            if invalido:
                completo = False
                motivo_parcial = f"Número sem lastro na ficha: {invalido}"
            else:
                novas_frases.append(f)
        parecer[campo] = "".join(novas_frases).strip()

    for campo in ["fatos", "gatilhos_mudanca"]:
        itens = parecer.get(campo, [])
        novos_itens = []
        for it in itens:
            nums = extrair_numeros_texto(it)
            invalido = None
            for token, val, pct, rs in nums:
                if not numero_valido(val, pct, rs, nums_ficha):
                    invalido = token
                    break
            if invalido:
                completo = False
                motivo_parcial = f"Número sem lastro na ficha: {invalido}"
            else:
                novos_itens.append(it)
        parecer[campo] = novos_itens

    parecer["completo"] = completo
    if not completo:
        parecer["motivo_parcial"] = motivo_parcial
    return parecer


def pos_processar_veredito(parecer, ficha):
    v = parecer.get("veredito")
    preco = ficha.get("preco") or 0.0
    compra = ficha.get("compra") or 0.0
    eh_fii = ficha.get("eh_fii", False)
    setor = ficha.get("setor", "") or ""
    eh_base = any(setor.startswith(pref) for pref in SETORES_BASE)
    risco_tipo = (parecer.get("risco") or "").strip().lower()

    if v == "comprar" and compra > 0 and preco > compra:
        v = "manter_sem_aportar"
    if eh_fii and v in ["vender", "realizar_parte"] and risco_tipo != "estrutural":
        v = "manter"
    if eh_base and v in ["vender", "realizar_parte"] and risco_tipo != "estrutural":
        v = "manter"

    parecer["veredito"] = v
    parecer["regua"] = {
        "teto": ficha.get("teto"),
        "compra": ficha.get("compra"),
        "preco": preco,
        "margem": ficha.get("margem"),
        "metodo": ficha.get("metodo"),
        "setor": setor
    }
    return parecer


def main(argv):
    if "--ficha" in argv:
        idx_f = argv.index("--ficha")
        if idx_f + 1 < len(argv):
            tk = argv[idx_f + 1].upper()
            ficha = montar_ficha(tk)
            print(json.dumps(ficha, indent=2, ensure_ascii=False))
            return 0
        else:
            print("Erro: ticker não informado após --ficha")
            return 1

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
                       + ("Cíclica: realizar parte em escada (até 60%; metade a mercado, metade com ordem +5%); "
                          "vendas de ações até R$ 20 mil/mês são isentas e o que sobra segue pagando dividendos."
                          if (setor.startswith("Commodities") or "Construção" in setor or "Varejo" in setor)
                          else "B.A.S.E. só se vende por fundamento; FII nunca por rebalanceamento."),
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

    # 6. Alerta de possível mudança de política de dividendos (payout 3A vs 5A, §21.9.5)
    politica_cadastrada = ler_var("politica_dividendos.js", "FEHMIR_POLITICA_DIV", {}) or {}
    anos_payout = ["2021", "2022", "2023", "2024", "2025"]
    for t in set(universo) | set(CVM):
        if t in politica_cadastrada:
            continue
        h_t = H.get(t) or {}
        dpa_ano = h_t.get("dpaAno") or {}
        dpa_extra = h_t.get("dpaAnoExtra") or {}
        cv_t = CVM.get(t) or {}
        vpa = cv_t.get("vpa")
        roe_anual = cv_t.get("roeAnual") or {}
        if not vpa or not roe_anual or not dpa_ano:
            continue
        payouts = {}
        for y in anos_payout:
            d = max(0.0, dpa_ano.get(y, 0.0) - dpa_extra.get(y, 0.0))
            ry = roe_anual.get(y)
            if ry and ry > 0 and vpa > 0:
                lpa_y = vpa * (ry / 100.0)
                payouts[y] = d / lpa_y
        if len(payouts) == 5:
            p3 = sum(payouts[y] for y in ["2023", "2024", "2025"]) / 3.0
            p5 = sum(payouts[y] for y in anos_payout) / 5.0
            if p5 >= 0.20:
                diff_pp = abs(p3 - p5) * 100.0
                if diff_pp >= 15.0:
                    razao = p3 / p5
                    if razao > 1.3 or razao < 0.7:
                        alerta(t, "politica_dividendos", "info",
                               f"{t}: possível mudança de política de dividendos — confirmar documento (payout 3A {br(p3*100, 0)}% vs 5A {br(p5*100, 0)}%, razão {br(razao, 2)}×, dif {br(diff_pp, 0)} p.p.)",
                               {"payout3a": round(p3*100, 1), "payout5a": round(p5*100, 1), "razao": round(razao, 2), "diff_pp": round(diff_pp, 1)},
                               {"fonte": "histórico e CVM (payout)", "data": "2021–2025"})

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

    # Fila de pareceres (T014): gatilhos documento, movimento, provento, fundamento
    gatilhos_parecer = {"documento", "movimento", "provento", "fundamento"}
    candidatos = [x for x in ativos if x["tipo"] in gatilhos_parecer]
    candidatos.sort(key=lambda x: (not x.get("carteira"), PRIORIDADE.get(x["prioridade"], 9), x["ticker"]))

    pareceres_existentes = ler_var("pareceres.js", "FEHMIR_PARECERES", {}) or {}
    fila_pareceres = []
    for cand in candidatos:
        tk = cand["ticker"]
        par_ant = pareceres_existentes.get(tk)
        if par_ant:
            mesmo_gatilho = par_ant.get("gatilho") == cand["tipo"]
            mesma_data = par_ant.get("data") == hoje
            if mesmo_gatilho and mesma_data:
                continue
            if cand["tipo"] == "documento":
                url_cand = (cand.get("origem") or {}).get("link")
                urls_par = [d.get("url") or d.get("link") for d in (par_ant.get("documentos") or [])]
                if url_cand and url_cand in urls_par:
                    continue
        if cand not in fila_pareceres:
            fila_pareceres.append(cand)
        if len(fila_pareceres) >= LIMIARES["pareceres_dia"]:
            break

    print(f"fila de pareceres: {len(fila_pareceres)} ativos ({', '.join(x['ticker'] for x in fila_pareceres)})")
    if seco:
        for x in fila_pareceres:
            print(f"  [fila] {x['ticker']}:{x['tipo']} ({x['prioridade']}) - {x['texto']}")

    novos_pareceres = {}
    licoes_novas = []
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and not seco:
        try:
            from novidades import chamar_gemini_api, descobrir_modelo_flash
            modelo = descobrir_modelo_flash(api_key) or "gemini-2.5-flash"
            generation_config = {
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_schema": SCHEMA_PARECER_ANALISTA
            }
            for cand in fila_pareceres:
                tk = cand["ticker"]
                ficha = montar_ficha(tk, H=H, T=T, CVM=CVM, NOV=NOV, CART=CART)
                licoes_txt = "\n".join([f"- ({l.get('data')}): {l.get('texto')}" for l in ficha.get("licoes", [])])
                prompt = f"""Você é o Conselheiro Fehmir, analista de ações e FIIs focado na metodologia Barsi/Bazin.
Analise o ativo {tk} com base EXCLUSIVAMENTE nos fatos da ficha técnica abaixo.

Ficha Técnica Oficial:
{json.dumps(ficha, indent=2, ensure_ascii=False)}

Lições Aprendidas Aplicáveis ao Setor:
{licoes_txt if licoes_txt else "Nenhuma lição específica."}

Gatilho do Alerta: {cand['tipo']} — {cand['texto']}

Diretrizes obrigatórias de análise:
1. Fatos vs opinião: liste fatos objetivos fundamentados nos dados da ficha e documentos oficiais.
2. Causa em camadas: classifique e explique se a dinâmica é do ativo (específico), de fluxo/setor ou macroeconômica.
3. Risco: classifique em 'idiossincratico' (específico/passageiro) ou 'estrutural' (tese quebrada).
4. Veredito: escolha estritamente entre comprar, manter_sem_aportar, manter, realizar_parte, vender, estudo.
5. Gatilhos de mudança: liste 2 a 4 condições objetivas para mudar de veredito.
6. Custo de executar: avalie custos operacionais/fiscais da decisão.
7. Lição genérica: proponha 1 lição duradoura (ou null se nenhuma).

REGRA INEGOCIÁVEL (CONSTITUIÇÃO IV):
Use APENAS os números que constam expressamente na ficha técnica acima. Não invente nenhum número, percentual ou projeção monetária."""

                resp_str = chamar_gemini_api(prompt, generation_config, context_label=f"Parecer-{tk}")
                if resp_str:
                    try:
                        p_data = json.loads(resp_str)
                        p_data["data"] = hoje
                        p_data["gatilho"] = cand["tipo"]
                        p_data["documentos"] = ficha.get("documentos", [])
                        p_data["modelo"] = modelo
                        p_data = verificar_numeros(p_data, ficha)
                        p_data = pos_processar_veredito(p_data, ficha)
                        novos_pareceres[tk] = p_data
                        print(f"  Parecer gerado para {tk}: veredito={p_data['veredito']}, completo={p_data['completo']}")

                        if p_data.get("licao_generica"):
                            licoes_novas.append({
                                "texto": p_data["licao_generica"],
                                "origem": {"ticker": tk, "data": hoje},
                                "status": "a_revisar"
                            })
                    except Exception as e:
                        print(f"Erro ao processar resposta do Gemini para {tk}: {e}")
        except Exception as e:
            print(f"Erro ao integrar Gemini para pareceres: {e}")

    pareceres_pendentes = [x["ticker"] for x in fila_pareceres if x["ticker"] not in novos_pareceres]

    if novos_pareceres:
        pareceres_todos = {**pareceres_existentes, **novos_pareceres}
        conteudo_par = ("/* Gerado por tools/analista.py — não editar à mão. */\n"
                        "window.FEHMIR_PARECERES = " + json.dumps(pareceres_todos, indent=2, ensure_ascii=False) + ";\n")
        PARECERES_PATH.write_text(conteudo_par, encoding="utf-8")
        print(f"OK: {PARECERES_PATH.relative_to(RAIZ)} atualizado com {len(novos_pareceres)} novo(s) parecer(es).")

    if licoes_novas:
        cands_atuais = ler_var("licoes_candidatas.js", "FEHMIR_LICOES", []) or []
        for ln in licoes_novas:
            if not any(ln["texto"][:40].lower() in c.get("texto", "").lower() for c in cands_atuais):
                cands_atuais.append(ln)
        conteudo_lic = ("/* Gerado por tools/analista.py — não editar à mão. */\n"
                        "window.FEHMIR_LICOES = " + json.dumps(cands_atuais, indent=2, ensure_ascii=False) + ";\n")
        LICOES_CANDIDATAS_PATH.write_text(conteudo_lic, encoding="utf-8")

    pareceres_totais = ler_var("pareceres.js", "FEHMIR_PARECERES", {}) or {}
    for a in itens:
        if a["ticker"] in pareceres_totais:
            a["parecer"] = True

    if seco:
        print("(--seco/--simular: nada gravado)")
        return 0
    meta = {"gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "verificados": len(universo), "ativos": len(ativos),
            "limiares": LIMIARES, "base_fundamentos": base_nova if not base_ant else {**base_ant, **base_nova},
            "pareceres_pendentes": pareceres_pendentes}
    SAIDA.write_text("/* Gerado por tools/analista.py — não editar à mão. */\nwindow.FEHMIR_ALERTAS = " +
                     json.dumps({"meta": meta, "itens": itens}, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"OK: {SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
