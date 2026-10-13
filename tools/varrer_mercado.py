"""Fehmir · varredura do MERCADO INTEIRO (radar de verdade), grátis e sem chave.

1. Lista pública da Brapi (/api/quote/list, sem token): todas as ações e fundos da B3 com preço, volume e setor.
2. Filtra os líquidos (ações > R$ 2 mi/dia; FIIs/Fiagros/FI-Infra > R$ 1 mi/dia).
3. Para cada um, Yahoo Finance (via tools/atualizar_historico.py): 1 ano de preços + 10 anos de proventos.
4. Calcula métricas e grava dados/mercado.js com `window.FEHMIR_MERCADO`.

O painel aplica a régua setorial (§21) sobre isso: teto histórico = DPA médio 5A ÷ DY exigido do setor.
É uma PRÉ-TRIAGEM só por dividendos: quem passar precisa da ficha completa (LPA, payout, dívida) antes de comprar.
Uso: python tools/varrer_mercado.py   (≈ 6-10 min). Também roda no GitHub Actions.
"""
import json, sys, time, math, datetime, pathlib, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from atualizar_historico import baixar, baixar_diario, processar, UA  # reaproveita o mesmo coletor

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "mercado.js"
LIQ_ACAO, LIQ_FUNDO = 2e6, 1e6

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Subsetor/setor da Brapi → rótulo em português que a régua do painel (SETORES, §21) reconhece
MAPA_SUB = [
    ("bancos", "Bancos"), ("segurad", "Seguradora"), ("previd", "Seguradora"),
    ("energia el", "Elétrica"), ("gua e saneamento", "Água/Saneamento"), ("saneamento", "Água/Saneamento"),
    ("telecomunica", "Telecom"),
    ("petr", "Petróleo/Gás"), ("refino", "Petróleo/Gás"), ("gás", "Petróleo/Gás"),
    ("minera", "Mineração"), ("minerais met", "Mineração"), ("siderurg", "Siderurgia"),
    ("papel e celulose", "Papel/Celulose"), ("agricultura", "Agro"), ("açúcar", "Agro"), ("carnes", "Agro"),
    ("incorpora", "Construção/Incorporação"), ("construção", "Construção/Incorporação"),
    ("varejo", "Varejo/Consumo"), ("calçado", "Varejo/Consumo"), ("vestu", "Varejo/Consumo"), ("eletrodom", "Varejo/Consumo"),
    ("aliment", "Varejo/Consumo"), ("educa", "Varejo/Consumo"), ("medicament", "Varejo/Consumo"), ("méd", "Varejo/Consumo"),
    ("cerveja", "Varejo/Consumo"), ("automóve", "Varejo/Consumo"), ("produtos diversos", "Varejo/Consumo"),
    ("máq", "Industrial"), ("material rodovi", "Industrial"), ("transporte", "Industrial/Logística"),
    ("rodovias", "Industrial/Logística"), ("aluguel de carros", "Industrial/Locação"), ("ferrovi", "Industrial/Logística"),
]
MAPA_SETOR_EN = {
    "Finance": "Financeiro", "Utilities": "Elétrica", "Energy Minerals": "Petróleo/Gás", "Non-Energy Minerals": "Mineração",
    "Process Industries": "Industrial", "Producer Manufacturing": "Industrial", "Retail Trade": "Varejo/Consumo",
    "Consumer Non-Durables": "Varejo/Consumo", "Consumer Durables": "Varejo/Consumo", "Consumer Services": "Varejo/Consumo",
    "Health Services": "Varejo/Consumo", "Health Technology": "Varejo/Consumo", "Transportation": "Industrial/Logística",
    "Communications": "Telecom", "Industrial Services": "Industrial", "Commercial Services": "Outros",
}


def setor_pt(x):
    sub = (x.get("subsector") or "").lower()
    for chave, rot in MAPA_SUB:
        if chave in sub:
            return rot
    return MAPA_SETOR_EN.get(x.get("sector") or "", "Outros")


def lista_b3(tipo):
    url = "https://brapi.dev/api/quote/list?type=" + tipo + "&limit=3000"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode("utf-8")).get("stocks", [])


def rsi(c, n=14):
    if len(c) <= n:
        return 50.0
    g = l = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]
        g += max(d, 0); l += max(-d, 0)
    g /= n; l /= n
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n; l = (l * (n - 1) + max(-d, 0)) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def medo_ganancia(c, v):
    """Mesma fórmula do painel: momentum 25, volume 20, calma 20, RSI 20, posição 52s 15."""
    cl = lambda a, lo, hi: max(lo, min(hi, a))
    p = c[-1]; mmN = min(200, len(c)); mm = sum(c[-mmN:]) / mmN; dist = (p / mm - 1) * 100
    v30 = sum(v[-30:]) / max(1, len(v[-30:])); vall = sum(v) / max(1, len(v))
    ret = [math.log(c[i] / c[i - 1]) for i in range(1, len(c)) if c[i - 1] > 0]
    def sd(a):
        if len(a) < 2: return 0.0
        m = sum(a) / len(a); return math.sqrt(sum((x - m) ** 2 for x in a) / len(a))
    vol30, volano = sd(ret[-30:]) * math.sqrt(252), sd(ret) * math.sqrt(252)
    r = rsi(c); mx, mn = max(c), min(c)
    f = {"mom": cl(50 + dist * 2.5, 0, 100), "vol": cl(50 + (v30 / vall - 1) * 100, 0, 100) if vall else 50,
         "volat": cl(50 + (1 - vol30 / volano) * 100, 0, 100) if volano else 50, "rsi": cl(r, 0, 100),
         "pos": (p - mn) / (mx - mn) * 100 if mx > mn else 50}
    score = (f["mom"] * 25 + f["vol"] * 20 + f["volat"] * 20 + f["rsi"] * 20 + f["pos"] * 15) / 100
    return round(score, 1), round(dist, 1), round(r, 1), round(f["pos"], 1), mmN


def main():
    t0 = time.time()
    acoes = [x for x in lista_b3("stock") if (x.get("volume") or 0) * (x.get("close") or 0) > LIQ_ACAO]
    fundos = [x for x in lista_b3("fund") if x.get("subType") in ("fii", "fi-agro", "fi-infra")
              and (x.get("volume") or 0) * (x.get("close") or 0) > LIQ_FUNDO]
    universo = [(x, "acao") for x in acoes] + [(x, "fii") for x in fundos]
    print(f"Universo líquido: {len(acoes)} ações + {len(fundos)} fundos = {len(universo)}. Baixando (Yahoo)…")
    itens, falhas = [], []
    for i, (x, tp) in enumerate(universo, 1):
        t = x["stock"]
        js = baixar(t + ".SA")
        reg = processar(js, baixar_diario(t + ".SA"), t) if js else None
        time.sleep(0.3)
        if not reg:
            falhas.append(t); continue
        c, v = reg["c"], reg["v"]
        fg, dist, r, pos, mmN = medo_ganancia(c, v)
        sub = x.get("subType")
        st = setor_pt(x) if tp == "acao" else ("Fiagro" if sub == "fi-agro" else "FI-Infra (papel)" if sub == "fi-infra" else "FII")
        itens.append({
            "t": t, "n": (x.get("name") or t)[:40], "tp": tp, "st": st, "sub": (x.get("subsector") or "")[:40],
            "p": round(c[-1], 2), "liq": round((x.get("volume") or 0) * (x.get("close") or 0) / 1e6, 1),
            "mc": round((x.get("market_cap") or 0) / 1e9, 2),
            "dpa12": reg["dpa12"], "dpa5": reg["dpa5"], "a5": reg.get("anos5"),
            "min": min(c), "max": max(c), "fg": fg, "dist": dist, "rsi": r, "pos": pos, "mmN": mmN,
        })
        if i % 50 == 0:
            print(f"  {i}/{len(universo)}…")
    meta = {"gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "ativos": len(itens), "falhas": len(falhas),
            "fonte": "Brapi /quote/list (pública) + Yahoo Finance", "minutos": round((time.time() - t0) / 60, 1)}
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text("/* Gerado por tools/varrer_mercado.py — não editar à mão. */\n"
                     "window.FEHMIR_MERCADO_META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
                     "window.FEHMIR_MERCADO = " + json.dumps(itens, ensure_ascii=False, separators=(",", ":")) + ";\n",
                     encoding="utf-8")
    print(f"OK: {len(itens)} ativos em dados/mercado.js ({SAIDA.stat().st_size/1024:.0f} KB), {meta['minutos']} min. Falhas: {len(falhas)}")
    return 0 if itens else 1


if __name__ == "__main__":
    sys.exit(main())
