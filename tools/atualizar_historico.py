"""Fehmir · atualiza o histórico de preços e dividendos (fonte gratuita, sem chave: Yahoo Finance).

Gera dados/historico.js com `window.FEHMIR_HIST = {...}`, que o painel carrega via <script>
(funciona com duplo clique no arquivo e no GitHub Pages). Roda:
  - manualmente:  python tools/atualizar_historico.py
  - automático:   GitHub Actions (.github/workflows/historico.yml), todo dia útil.

Por ticker guarda: ~1 ano de fechamentos e volumes diários (MM200, RSI, range 52s, Medo × Ganância)
e os dividendos/JCP dos últimos 5 anos (DPA por ano e DPA médio 5A, para o teto histórico).
Fonte única (Yahoo): os valores de dividendos podem vir brutos (JCP antes do IR) e ajustados por
desdobramento; conferir em fonte primária antes de decidir (política de dados do .md).
"""
import json, re, sys, time, datetime, pathlib, urllib.request, urllib.error

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PAINEL = RAIZ / "painel-barsi.html"
SAIDA = RAIZ / "dados" / "historico.js"
INDICES = {"^BVSP": "^BVSP", "SMAL11": "SMAL11.SA", "IVVB11": "IVVB11.SA", "XFIX11": "XFIX11.SA"}
INTL_ATIVOS = {"VTI": "VTI", "SCHD": "SCHD"}
CAMBIO = {"USDBRL": "USDBRL=X"}
# Ativos acompanhados em estudos (ex.: bancos) que não aparecem como t:"XXXX" no painel.
# Fonte dos CNPJs na CVM: dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv
TICKERS_EXTRAS = ["ABCB4", "BBDC3", "BPAC11",
                  "KNCR11", "KNIP11", "HGLG11", "BTLG11", "ISNT11", "ISEN11", "RURA11", "VGIA11", "SNAG11"]
CRIPTO_ATIVOS = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Fehmir/1.0"}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def tickers_do_painel():
    """Lê do próprio painel os tickers da carteira e do radar (t:"XXXX3" / t:"XXXX11")."""
    html = PAINEL.read_text(encoding="utf-8", errors="ignore")
    achados = set(re.findall(r'\bt:\s*"([A-Z]{4}\d{1,2})"', html))
    return sorted(achados)


def baixar(simbolo, tentativas=3):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.request.quote(simbolo)
           + "?range=10y&interval=1wk&events=div")  # 10 anos semanais: dividendos e anos completos
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def utc(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc)


def baixar_diario(simbolo):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.request.quote(simbolo) + "?range=1y&interval=1d")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def processar(js, diario=None, nome="", falhas_b3=None):
    try:
        res = js["chart"]["result"][0]
    except (KeyError, IndexError, TypeError):
        return None
    ts_longo = [t for t, c in zip(res.get("timestamp") or [], ((res.get("indicators", {}).get("quote") or [{}])[0].get("close") or [])) if c]
    try:
        rd = diario["chart"]["result"][0]
    except (KeyError, IndexError, TypeError):
        return None
    q = (rd.get("indicators", {}).get("quote") or [{}])[0]
    serie = [(t, c, v or 0) for t, c, v in zip(rd.get("timestamp") or [], q.get("close") or [], q.get("volume") or []) if c]
    if len(serie) < 40:
        return None
    ano = serie[-260:]  # ~1 ano de pregões diários
    divs = (res.get("events") or {}).get("dividends") or {}
    lista = sorted((int(d["date"]), float(d["amount"])) for d in divs.values() if d.get("amount"))
    por_ano = {}
    for t, a in lista:
        y = utc(t).year
        por_ano[y] = por_ano.get(y, 0.0) + a
    ano_atual = datetime.date.today().year
    # Fechamentos semanais dos últimos 10 anos para preço médio anual (pmAno)
    q_longo = (res.get("indicators", {}).get("quote") or [{}])[0]
    ts_c_longo = [(t, c) for t, c in zip(res.get("timestamp") or [], q_longo.get("close") or []) if c is not None and c > 0]
    pm_por_ano = {}
    for t, c in ts_c_longo:
        y = utc(t).year
        pm_por_ano.setdefault(y, []).append(c)
    pmAno = {str(y): round(sum(vals) / len(vals), 2) for y, vals in pm_por_ano.items() if y in range(ano_atual - 10, ano_atual + 1) and vals}

    # Contagem de pagamentos por ano
    npag_por_ano = {}
    for t, _ in lista:
        y = utc(t).year
        npag_por_ano[y] = npag_por_ano.get(y, 0) + 1
    nPagAno = {str(y): npag_por_ano.get(y, 0) for y in range(ano_atual - 10, ano_atual + 1)}

    # Anos válidos dos últimos 5 fechados
    inicio = utc(ts_longo[0]) if ts_longo else None
    anos_ok = [y for y in range(ano_atual - 5, ano_atual) if inicio and (inicio.year < y or (inicio.year == y and inicio.month == 1))]
    primeiro_div = min(por_ano) if por_ano else None
    if primeiro_div is not None:
        anos_ok = [y for y in anos_ok if y > primeiro_div or (y == primeiro_div and utc(lista[0][0]).month <= 2)]
    if nome.endswith("11"):
        anos_ok = [y for y in anos_ok if por_ano.get(y, 0) > 0]
    # Lacuna da fonte (25/10/2026): ano sem provento ENTRE anos pagos (antes e depois, até o ano corrente) é
    # quase sempre falha do Yahoo (ex.: CPFE3 2024–2025 pagou ~R$ 2,75 e ~R$ 2,79 e veio zero). Sai da média e
    # fica registrado em "lacunas". Zero no fim da série (corte real) continua contando: zero não é ausência.
    lacunas = []
    for y in anos_ok:
        if por_ano.get(y, 0) == 0 and any(por_ano.get(z, 0) > 0 for z in por_ano if z < y) \
                and any(por_ano.get(z, 0) > 0 for z in range(y + 1, ano_atual + 1)):
            lacunas.append(y)

    fonte_proventos = {}
    divergencias = []
    if lacunas:
        eh_unit = nome.endswith("11") and nome in {"TAEE11", "ALUP11", "KLBN11", "SANB11", "BPAC11", "SAPR11", "ENGI11", "SULA11"}
        eh_acao = nome.endswith(("3", "4")) or eh_unit
        if eh_acao:
            try:
                from b3_proventos import buscar_proventos_b3
                res_b3 = buscar_proventos_b3(nome)
                if res_b3 and res_b3.get("ok"):
                    b3_ano = res_b3.get("por_ano", {})
                    novas_lacunas = []
                    for y in lacunas:
                        if y in b3_ano and b3_ano[y] > 0:
                            # Calibração obrigatória (§item 1 da Rodada 16b):
                            # O ano vizinho anterior e o posterior com dado nas duas fontes precisam ter razão Yahoo / B3 entre 0,9 e 1,1
                            anos_ant = [a for a in por_ano if a < y and por_ano.get(a, 0) > 0 and b3_ano.get(a, 0) > 0]
                            anos_pos = [a for a in por_ano if a > y and por_ano.get(a, 0) > 0 and b3_ano.get(a, 0) > 0]
                            calibrado = False
                            if anos_ant and anos_pos:
                                v_ant = max(anos_ant)
                                v_pos = min(anos_pos)
                                r_ant = por_ano[v_ant] / b3_ano[v_ant]
                                r_pos = por_ano[v_pos] / b3_ano[v_pos]
                                if 0.90 <= r_ant <= 1.10 and 0.90 <= r_pos <= 1.10:
                                    calibrado = True
                            if calibrado:
                                por_ano[y] = b3_ano[y]
                                fonte_proventos[str(y)] = "B3"
                            else:
                                novas_lacunas.append(y)
                        else:
                            novas_lacunas.append(y)
                    lacunas = novas_lacunas
                    # Divergência NUNCA substitui: fica apenas no relatório de auditoria
                elif res_b3 and not res_b3.get("ok"):
                    if falhas_b3 is not None:
                        falhas_b3.append(f"{nome}: {res_b3.get('erro')}")
            except Exception:
                pass

    anos_ok = [y for y in anos_ok if y not in lacunas]
    dpa5 = round(sum(por_ano.get(y, 0.0) for y in anos_ok) / len(anos_ok), 4) if anos_ok and any(por_ano.get(y, 0) for y in anos_ok) else None

    # Anos válidos dos últimos 10 fechados
    anos_ok_10 = [y for y in range(ano_atual - 10, ano_atual) if inicio and (inicio.year < y or (inicio.year == y and inicio.month == 1))]
    if primeiro_div is not None:
        anos_ok_10 = [y for y in anos_ok_10 if y > primeiro_div or (y == primeiro_div and utc(lista[0][0]).month <= 2)]
    if nome.endswith("11"):
        anos_ok_10 = [y for y in anos_ok_10 if por_ano.get(y, 0) > 0]
    anos_ok_10 = [y for y in anos_ok_10 if y not in lacunas]
    dpa10 = round(sum(por_ano.get(y, 0.0) for y in anos_ok_10) / len(anos_ok_10), 4) if anos_ok_10 and any(por_ano.get(y, 0) for y in anos_ok_10) else None

    # Crescimento do dividendo em 5 anos (CAGR)
    cagrDiv5 = None
    if len(anos_ok) >= 3:
        dpa_ini = por_ano.get(anos_ok[0], 0.0)
        dpa_fim = por_ano.get(anos_ok[-1], 0.0)
        if dpa_ini > 0 and dpa_fim > 0:
            cagrDiv5 = round((dpa_fim / dpa_ini) ** (1.0 / (len(anos_ok) - 1)) - 1.0, 4)

    um_ano_atras = time.time() - 365 * 86400
    dpa12 = round(sum(a for t, a in lista if t >= um_ano_atras), 4)

    dois_anos_atras = time.time() - 2 * 365 * 86400
    ev = [[utc(t).strftime("%Y-%m-%d"), round(a, 4)] for t, a in lista if t >= dois_anos_atras]

    # Detecção de proventos extraordinários pelo critério do excesso do ano
    # Para cada ano y dos 5 anos fechados: excesso = dpaAno[y] - mediana(dpaAno dos outros anos dos 5)
    # Se excesso <= 0.3 * mediana: nenhum extra no ano
    # Senão: entre os eventos do ano com valor > 2.5x mediana dos eventos, marcar do maior para o menor enquanto excesso restante >= 50% do evento
    extras = []
    por_ano_extra = {}
    anos_5a = [ano_atual - 5, ano_atual - 4, ano_atual - 3, ano_atual - 2, ano_atual - 1]
    dpas_anuais_5a = {y: por_ano.get(y, 0.0) for y in anos_5a}

    # Eventos de referência nos 5 anos fechados (filtrando micro-proventos mensais de JCP < 0.05 para não distorcer)
    divs_5a = [a for t, a in lista if (ano_atual - 5) <= utc(t).year <= (ano_atual - 1) and a >= 0.05]
    if not divs_5a:
        divs_5a = [a for t, a in lista if (ano_atual - 5) <= utc(t).year <= (ano_atual - 1)]

    if len(divs_5a) >= 1 and any(d > 0 for d in dpas_anuais_5a.values()):
        import statistics
        med_div = statistics.median(divs_5a)

        for y in anos_5a:
            outros_dpas = [dpas_anuais_5a[yo] for yo in anos_5a if yo != y]
            med_outros = statistics.median(outros_dpas) if outros_dpas else 0.0
            dpa_y = dpas_anuais_5a[y]
            excesso = dpa_y - med_outros

            if excesso <= 0.3 * med_outros:
                continue

            # Mediana de eventos de referência (garantindo piso proporcional ao DPA anual dos outros anos)
            med_ev = max(med_div, med_outros / 2.5) if med_outros > 0 else med_div
            cand = [(t, a) for t, a in lista if utc(t).year == y and a > 2.5 * med_ev]
            cand.sort(key=lambda x: x[1], reverse=True)

            exc_rest = excesso
            for t, a in cand:
                if exc_rest >= 0.5 * a:
                    extras.append([utc(t).strftime("%Y-%m-%d"), round(a, 4), round(excesso, 4), round(med_outros, 4)])
                    por_ano_extra[y] = por_ano_extra.get(y, 0.0) + a
                    exc_rest -= a

    dpaAnoExtra = {str(y): round(por_ano_extra.get(y, 0.0), 4) for y in range(ano_atual - 10, ano_atual + 1)}

    return {
        "d0": utc(ano[0][0]).strftime("%Y-%m-%d"),
        "d1": utc(ano[-1][0]).strftime("%Y-%m-%d"),
        "d": [utc(t).strftime("%Y-%m-%d") for t, _, _ in ano],
        "anos5": len(anos_ok),
        "anos10": len(anos_ok_10),
        "c": [round(c, 2) for _, c, _ in ano],
        "v": [int(v // 100) for _, _, v in ano],  # volume em centenas (economiza espaço)
        "dpaAno": {str(y): round(por_ano.get(y, 0.0), 4) for y in range(ano_atual - 10, ano_atual + 1)},
        "dpaAnoExtra": dpaAnoExtra,
        "extras": extras,
        "pmAno": pmAno,
        "nPagAno": nPagAno,
        "dpa12": dpa12,
        "dpa5": dpa5,
        "lacunas": lacunas,
        "fonte_proventos": fonte_proventos,
        "divergencias": divergencias,
        "dpa10": dpa10,
        "cagrDiv5": cagrDiv5,
        "ev": ev,
    }


ALIASES_YAHOO = {
    "TRPL4": "ISAE4.SA",
    "TRPL3": "ISAE3.SA",
    "ISAE4": "ISAE4.SA",
    "ISAE3": "ISAE3.SA",
    "BRIT3": "BRST3.SA",
    "BRST3": "BRST3.SA",
    "XBCI11": "XPCI11.SA",
    "BTC-BRL": "BTC-USD",
    "ETH-BRL": "ETH-USD",
    "SOL-BRL": "SOL-USD",
}


def main():
    tickers = sorted(set(tickers_do_painel()) | set(TICKERS_EXTRAS))
    alvos = {t: t + ".SA" for t in tickers}
    alvos.update(INDICES)
    alvos.update(INTL_ATIVOS)
    alvos.update(CAMBIO)
    alvos.update(CRIPTO_ATIVOS)
    print(f"Baixando {len(alvos)} ativos do Yahoo Finance…")
    dados, falhas, falhas_b3 = {}, [], []
    for nome, simbolo in alvos.items():
        sym = ALIASES_YAHOO.get(nome, simbolo)
        js = baixar(sym)
        reg = processar(js, baixar_diario(sym), nome, falhas_b3) if js else None
        if reg:
            if nome in INTL_ATIVOS:
                reg["moeda"] = "USD"
            elif nome in CRIPTO_ATIVOS:
                reg["moeda"] = "BRL"
                usd_rate = dados.get("USDBRL", {}).get("c", [5.03])[-1] if "USDBRL" in dados else 5.03
                reg["c"] = [round(c * usd_rate, 2) for c in reg["c"]]
            dados[nome] = reg
            if nome == "TRPL4":
                dados["ISAE4"] = reg
            elif nome == "ISAE4":
                dados["TRPL4"] = reg
            elif nome == "BRIT3":
                dados["BRST3"] = reg
            elif nome == "BRST3":
                dados["BRIT3"] = reg
        else:
            falhas.append(nome)
        time.sleep(0.4)  # educado com o servidor
    falhas.extend(falhas_b3)
    meta = {"gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "fonte": "Yahoo Finance (gratuito, sem chave) + B3 Oficial",
            "ativos": len(dados), "falhas": falhas}
    SAIDA.parent.mkdir(exist_ok=True)
    conteudo = ("/* Gerado por tools/atualizar_historico.py — não editar à mão. */\n"
                "window.FEHMIR_HIST_META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
                "window.FEHMIR_HIST = " + json.dumps(dados, separators=(",", ":")) + ";\n")
    SAIDA.write_text(conteudo, encoding="utf-8")
    kb = SAIDA.stat().st_size / 1024
    print(f"OK: {len(dados)} ativos em {SAIDA.relative_to(RAIZ)} ({kb:.0f} KB). Sem dados: {', '.join(falhas) or 'nenhum'}")
    return 0 if dados else 1


if __name__ == "__main__":
    sys.exit(main())
