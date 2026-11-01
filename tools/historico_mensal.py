"""Fehmir · robô da série mensal de até 11 anos (comparador de ativos, spec 005).

Grava dados/historico_mensal.js com, por ativo, o fechamento mensal (ajustado por desdobramento e grupamento,
como o Yahoo entrega) e o provento por cota de cada mês, mais os índices de comparação:
  CDI (Banco Central SGS 4391, % no mês) · IPCA (SGS 433, % no mês) · IBOV (^BVSP) · SMLL (SMAL11)
  IFIX (via XFIX11, ETF que segue o índice) · IDIV (via DIVO11, ETF que segue o índice) · IVVB11

Formato: window.FEHMIR_HIST_MENSAL = { TICKER: { i: "AAAA-MM", c: [fechamentos], d: { "índice do mês": provento } } }
         window.FEHMIR_IDX_MENSAL = { CDI: { i, r: [% no mês] }, IPCA: { i, r: [...] } }
Sem chave, sem token. Roda: python tools/historico_mensal.py   ·   GitHub Actions (historico.yml), semanal.
Mês sem cotação fica de fora do começo da série; nada é inventado.
"""
import datetime, json, pathlib, sys, time, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "historico_mensal.js"
sys.path.insert(0, str(RAIZ / "tools"))
from atualizar_historico import tickers_do_painel, TICKERS_EXTRAS  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Fehmir/1.0"}
INDICES = {"IBOV": "^BVSP", "SMLL": "SMAL11.SA", "IFIX": "XFIX11.SA", "IDIV": "DIVO11.SA", "IVVB11": "IVVB11.SA"}
EXTRAS = ["KNSC11"]  # pedidos no comparador e ainda fora do painel

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def baixar_json(url, tentativas=3):
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


def mes(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m")


def serie_yahoo(simbolo):
    js = baixar_json("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.request.quote(simbolo)
                     + "?range=max&interval=1mo&events=div")  # corta em 11 anos abaixo (10 anos pedem 121 pontos)
    try:
        r = js["chart"]["result"][0]
        ts, cl = r["timestamp"], r["indicators"]["quote"][0]["close"]
    except Exception:
        return None
    fech = {}
    for t, c in zip(ts, cl):
        if c is not None and c > 0:
            fech[mes(t)] = round(c, 4)  # a última barra do mês vence (Yahoo às vezes repete o mês corrente)
    if len(fech) < 2:
        return None
    meses = sorted(fech)[-133:]
    fech = {k: fech[k] for k in meses}
    # completa buracos com o fechamento anterior (mês sem negócio), nunca antes do primeiro
    todos, (a, m) = [], map(int, meses[0].split("-"))
    fim = meses[-1]
    while True:
        k = f"{a:04d}-{m:02d}"
        todos.append(k)
        if k == fim:
            break
        m += 1
        if m > 12:
            a, m = a + 1, 1
    c, ult = [], None
    for k in todos:
        ult = fech.get(k, ult)
        c.append(ult)
    d = {}
    for ev in ((r.get("events") or {}).get("dividends") or {}).values():
        k = mes(ev["date"])
        if k in todos and ev.get("amount"):
            i = todos.index(k)
            d[str(i)] = round(d.get(str(i), 0) + ev["amount"], 6)
    return {"i": todos[0], "c": c, "d": d}


def serie_sgs(num):
    hoje = datetime.date.today()
    ini = (hoje.replace(year=hoje.year - 11)).strftime("%d/%m/%Y")
    js = baixar_json(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{num}/dados?formato=json&dataInicial={ini}")
    if not isinstance(js, list) or not js:
        return None
    pts = [(x["data"][6:10] + "-" + x["data"][3:5], float(x["valor"])) for x in js]
    pts.sort()
    return {"i": pts[0][0], "r": [v for _, v in pts], "f": pts[-1][0]}


def tickers_do_mercado():
    """Ativos do radar de mercado (dados/mercado.js), para o comparador aceitar qualquer um deles."""
    try:
        txt = (RAIZ / "dados" / "mercado.js").read_text(encoding="utf-8")
        return [x["t"] for x in json.loads(txt.split("window.FEHMIR_MERCADO = ", 1)[1].rsplit(";", 1)[0]) if x.get("t")]
    except Exception:
        return []


def main():
    alvos = sorted(set(tickers_do_painel()) | set(TICKERS_EXTRAS) | set(EXTRAS) | set(tickers_do_mercado()))
    dados, falhas = {}, []
    for t in alvos:
        s = serie_yahoo(t + ".SA")
        if s:
            dados[t] = s
        else:
            falhas.append(t)
        time.sleep(0.15)
    for nome, simb in INDICES.items():
        s = serie_yahoo(simb)
        if s:
            dados["@" + nome] = s
        else:
            falhas.append(nome)
    idx = {}
    for nome, num in (("CDI", 4391), ("IPCA", 433)):
        s = serie_sgs(num)
        if s:
            idx[nome] = s
        else:
            falhas.append(nome)
    if len(dados) < 20:
        print("Poucos ativos (" + str(len(dados)) + "): Yahoo fora do ar? Arquivo mantido.")
        return 1
    meta = {"gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "fonte": "Yahoo Finance (mensal, até 11 anos, ajustado por desdobramento) + Banco Central (SGS 4391 e 433)",
            "rotulos": {"IFIX": "IFIX (via XFIX11)", "IDIV": "IDIV (via DIVO11)", "SMLL": "SMLL (via SMAL11)"},
            "ativos": len(dados), "falhas": falhas}
    SAIDA.write_text(
        "/* Gerado por tools/historico_mensal.py — não editar à mão. */\n"
        "window.FEHMIR_HIST_MENSAL_META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
        "window.FEHMIR_HIST_MENSAL = " + json.dumps(dados, separators=(",", ":")) + ";\n"
        "window.FEHMIR_IDX_MENSAL = " + json.dumps(idx, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    print(f"OK: {len(dados)} séries em {SAIDA.relative_to(RAIZ)} ({SAIDA.stat().st_size / 1024:.0f} KB). Sem dados: {', '.join(falhas) or 'nenhum'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
