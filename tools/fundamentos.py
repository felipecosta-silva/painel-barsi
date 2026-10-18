"""Fehmir · robô de fundamentos (ROE, LPA, VPA, P/L, P/VP, fluxo de caixa livre) pela Brapi.

O cadastro do painel envelhece (ex.: ITUB4 com P/L 8,5 no cadastro e 11,9 na Brapi em 18/10/2026).
Este robô busca os fundamentos de cada AÇÃO do painel e grava dados/fundamentos.js com
`window.FEHMIR_FUND = {...}`, que o painel usa por cima do cadastro.

Token: variável de ambiente BRAPI_TOKEN (no GitHub, Secrets). Nunca no código.
Sem token, a Brapi só libera PETR4, VALE3, ITUB4 e MGLU3: o robô roda só esses e sai com código 0.
Roda: python tools/fundamentos.py   ·   GitHub Actions (.github/workflows/fundamentos.yml), semanal.
Dado ausente ou absurdo fica null e vai para `falhas` — nunca 0, nunca o valor do cadastro.
"""
import datetime, json, os, pathlib, re, sys, time, urllib.error, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from atualizar_historico import tickers_do_painel, UA

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "fundamentos.js"
MERCADO = RAIZ / "dados" / "mercado.js"
GRATIS = ["PETR4", "VALE3", "ITUB4", "MGLU3"]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def tipos_do_mercado():
    """Tipo de cada ticker (acao/fii/...) pela varredura do robô de mercado, para pular fundos."""
    try:
        txt = MERCADO.read_text(encoding="utf-8")
        lista = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
        return {x["t"]: x.get("tp") for x in lista if "t" in x}
    except Exception:
        return {}


def e_acao(t, tipos):
    if tipos.get(t):
        return tipos[t] == "acao"
    return t[-1] in "3456"  # sem informação do mercado: final 11 (FII/unit) fica de fora


def buscar(t, token):
    url = "https://brapi.dev/api/quote/" + t + "?modules=defaultKeyStatistics,financialData"
    req = urllib.request.Request(url, headers=dict(UA, **({"Authorization": "Bearer " + token} if token else {})))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("message", "")
        except Exception:
            msg = ""
        return None, "HTTP %s %s" % (e.code, msg)
    except Exception as e:
        return None, str(e)[:120]


def num(v):
    return v if isinstance(v, (int, float)) and v == v else None


def extrair(res):
    r = (res.get("results") or [{}])[0]
    k = r.get("defaultKeyStatistics") or {}
    f = r.get("financialData") or {}
    roe = num(f.get("returnOnEquity"))
    d = {
        "lpa": num(k.get("trailingEps")) if num(k.get("trailingEps")) is not None else num(r.get("earningsPerShare")),
        "vpa": num(k.get("bookValue")),
        "roe": round(roe * 100, 2) if roe is not None else None,
        "pl": num(r.get("priceEarnings")),
        "pvp": num(k.get("priceToBook")),
        "fcf": num(f.get("freeCashflow")),
        "atualizado": (f.get("updatedAt") or k.get("updatedAt") or "")[:10] or None,
    }
    problemas = []
    if d["roe"] is not None and not (-100 <= d["roe"] <= 200):
        problemas.append("ROE absurdo %s" % d["roe"]); d["roe"] = None
    if d["vpa"] is not None and d["vpa"] <= 0:
        problemas.append("VPA <= 0"); d["vpa"] = None; d["pvp"] = None
    for c in ("lpa", "pl", "pvp"):
        if d[c] is not None:
            d[c] = round(d[c], 4)
    if d["lpa"] is None and d["vpa"] is None and d["roe"] is None:
        problemas.append("sem modules (plano não cobre ou ticker sem dados)")
    return d, problemas


def main():
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    tipos = tipos_do_mercado()
    lista = [t for t in tickers_do_painel() if e_acao(t, tipos)] if token else GRATIS
    if not token:
        print("BRAPI_TOKEN ausente: só os tickers grátis", GRATIS)
    fund, falhas, req = {}, [], 0
    for t in lista:
        res, erro = buscar(t, token)
        req += 1
        if erro:
            falhas.append({"t": t, "motivo": erro})
            print("✗", t, erro)
        else:
            d, probs = extrair(res)
            if probs:
                falhas.append({"t": t, "motivo": "; ".join(probs)})
            if any(d[c] is not None for c in ("lpa", "vpa", "roe")):
                fund[t] = d
                print("✓", t, "ROE", d["roe"], "LPA", d["lpa"], "VPA", d["vpa"])
            else:
                print("✗", t, "; ".join(probs))
        time.sleep(0.5)
    meta = {
        "gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": "Brapi (defaultKeyStatistics, financialData)",
        "ok": len(fund), "falhas": falhas, "requisicoes": req, "comToken": bool(token),
    }
    # Se nada veio (API fora do ar, token inválido), não apaga o arquivo anterior.
    if not fund and SAIDA.exists():
        print("Nenhum dado novo; mantendo", SAIDA.name)
        return 0
    SAIDA.write_text(
        "// Gerado por tools/fundamentos.py — não editar à mão.\n"
        "window.FEHMIR_FUND_META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
        "window.FEHMIR_FUND = " + json.dumps(fund, ensure_ascii=False, sort_keys=True) + ";\n",
        encoding="utf-8")
    print("OK: %d ativos, %d falhas, %d requisições → %s" % (len(fund), len(falhas), req, SAIDA))
    return 0


if __name__ == "__main__":
    sys.exit(main())
