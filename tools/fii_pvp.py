"""Fehmir · robô de P/VP dos FIIs (Fundamentus, tabela pública de todos os fundos imobiliários).

A Brapi e a CVM não trazem o valor patrimonial por cota dos FIIs. O Fundamentus publica numa página só
cotação, DY, P/VP e segmento de todos os FIIs. O robô grava dados/fii_pvp.js com
`window.FEHMIR_FII_PVP = { TICKER: { pvp, preco, vpa, dy, seg } }`; o painel usa o VPA (preço ÷ P/VP)
para recalcular o P/VP com o preço do dia (sinal de possível venda de FII de papel, spec 003).

Roda: python tools/fii_pvp.py   ·   GitHub Actions (.github/workflows/fundamentos.yml), semanal.
Dado ausente ou absurdo (P/VP ≤ 0 ou > 5) fica de fora — nunca 0.
"""
import datetime, html, json, pathlib, re, sys, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "fii_pvp.js"
URL = "https://www.fundamentus.com.br/fii_resultado.php"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Fehmir/1.0"}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def num(s):
    s = s.strip().replace("%", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def main():
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=60) as r:
        txt = r.read().decode("latin-1")
    corpo = txt[txt.index("<tbody"): txt.index("</tbody>")]
    saida = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", corpo, flags=re.S):
        cel = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(cel) < 6 or not re.fullmatch(r"[A-Z]{4}11", cel[0]):
            continue
        # colunas: Papel, Segmento, Cotação, FFO Yield, Dividend Yield, P/VP, ...
        preco, dy, pvp = num(cel[2]), num(cel[4]), num(cel[5])
        if not preco or not pvp or pvp <= 0 or pvp > 5:
            continue
        saida[cel[0]] = {"pvp": round(pvp, 2), "preco": preco, "vpa": round(preco / pvp, 2), "dy": dy, "seg": cel[1]}
    if len(saida) < 100:
        print("Poucos FIIs lidos (" + str(len(saida)) + "): layout do Fundamentus mudou? Arquivo mantido.")
        return 1
    meta = {"gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "fonte": "Fundamentus (fii_resultado)", "n": len(saida)}
    SAIDA.write_text(
        "/* Gerado por tools/fii_pvp.py — não editar à mão. */\n"
        "window.FEHMIR_FII_PVP_META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
        "window.FEHMIR_FII_PVP = " + json.dumps(saida, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    print("OK: " + str(len(saida)) + " FIIs em " + str(SAIDA.relative_to(RAIZ)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
