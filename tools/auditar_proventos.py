"""Fehmir · Auditoria semanal de proventos (Yahoo x B3).

Compara os dividendos dos últimos 5 anos fechados entre Yahoo Finance e B3 Oficial.
Identifica:
  - Lacunas na fonte (anos sem provento entre anos pagos)
  - Divergências > 20% entre Yahoo e B3
  - Anos com DPA > 3x a média dos demais anos (amortização / grupamento / extraordinário)
"""

import json, re, sys, pathlib, datetime, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

from b3_proventos import buscar_proventos_b3

HIST_JS = RAIZ / "dados" / "historico.js"

UNITS_ACOES = {'TAEE11', 'ALUP11', 'KLBN11', 'SANB11', 'BPAC11', 'SAPR11', 'ENGI11', 'SULA11'}

def carregar_historico():
    if not HIST_JS.exists():
        print(f"Erro: {HIST_JS} não encontrado.")
        sys.exit(1)
    txt = HIST_JS.read_text(encoding="utf-8")
    m = re.search(r'window\.FEHMIR_HIST\s*=\s*(\{.*?\});?\s*$', txt, re.DOTALL)
    if not m:
        print("Erro: não foi possível extrair window.FEHMIR_HIST")
        sys.exit(1)
    return json.loads(m.group(1))

def obter_acoes(hist):
    acoes = []
    for t in sorted(hist.keys()):
        if t.endswith(('3', '4')) or (t.endswith('11') and t in UNITS_ACOES):
            acoes.append(t)
    return acoes

def auditar():
    hist = carregar_historico()
    acoes = obter_acoes(hist)
    ano_atual = datetime.date.today().year
    anos_5a = list(range(ano_atual - 5, ano_atual)) # [2021, 2022, 2023, 2024, 2025]

    print("=" * 80)
    print(f"AUDITORIA SEMANAL DE PROVENTOS FEHMIR (YAHOO x B3) — {datetime.date.today().strftime('%d/%m/%Y')}")
    print(f"Universo analisado: {len(acoes)} ações · Anos fechados: {anos_5a[0]} a {anos_5a[-1]}")
    print("=" * 80)
    print()

    lacunas_encontradas = []
    divergencias_encontradas = []
    anomalias_3x = []
    falhas_b3 = []

    total = len(acoes)
    for idx, ticker in enumerate(acoes, 1):
        dados_h = hist.get(ticker, {})
        dpa_ano_yh = dados_h.get("dpaAno", {})

        res_b3 = buscar_proventos_b3(ticker)
        if not res_b3.get("ok"):
            falhas_b3.append({"ticker": ticker, "motivo": res_b3.get("erro")})
            continue

        b3_ano = res_b3.get("por_ano", {})
        if not b3_ano or sum(b3_ano.values()) == 0:
            falhas_b3.append({"ticker": ticker, "motivo": "B3 vazia para o ticker (falha de nome de pregão ou classe)"})
            continue

        # 1. Checar Lacunas e Divergências nos 5 anos fechados
        for y in anos_5a:
            sy = str(y)
            yh_val = float(dpa_ano_yh.get(sy, 0.0))
            b3_val = float(b3_ano.get(y, 0.0))

            # Verificar se é lacuna (ano zerado entre anos com proventos)
            # ou ano marcado em lacunas no histórico
            if yh_val == 0.0 and b3_val > 0.0:
                lacunas_encontradas.append({
                    "ticker": ticker,
                    "ano": y,
                    "yahoo": yh_val,
                    "b3": b3_val,
                    "status": "Preenchível pela B3"
                })
            elif yh_val == 0.0 and b3_val == 0.0:
                # Verificar se o ativo tinha proventos antes e depois
                anos_anteriores = [float(dpa_ano_yh.get(str(z), 0.0)) for z in range(ano_atual - 10, y)]
                anos_posteriores = [float(dpa_ano_yh.get(str(z), 0.0)) for z in range(y + 1, ano_atual + 1)]
                if any(v > 0 for v in anos_anteriores) and any(v > 0 for v in anos_posteriores):
                    lacunas_encontradas.append({
                        "ticker": ticker,
                        "ano": y,
                        "yahoo": 0.0,
                        "b3": 0.0,
                        "status": "Sem dado na fonte (B3 e Yahoo zero)"
                    })

            # Divergência > 20% (apenas quando ambas as fontes possuem valor positivo > 0.05)
            if yh_val > 0.05 and b3_val > 0.05:
                maior = max(yh_val, b3_val)
                diff_pct = abs(yh_val - b3_val) / maior
                if diff_pct > 0.20:
                    divergencias_encontradas.append({
                        "ticker": ticker,
                        "ano": y,
                        "yahoo": yh_val,
                        "b3": b3_val,
                        "diff_pct": diff_pct * 100
                    })
            elif yh_val > 0.05 and b3_val == 0.0:
                falhas_b3.append({"ticker": ticker, "motivo": f"Ano {y} sem dado na B3 (Yahoo R$ {yh_val:.4f})"})

        # 2. Checar ano com DPA > 3x a média dos demais anos
        # Usamos o valor da B3 quando disponível, senão Yahoo
        dpas_5a = {}
        for y in anos_5a:
            b3_v = float(b3_ano.get(y, 0.0))
            yh_v = float(dpa_ano_yh.get(str(y), 0.0))
            dpas_5a[y] = b3_v if b3_v > 0 else yh_v

        for y in anos_5a:
            dpa_y = dpas_5a[y]
            outros = [dpas_5a[yo] for yo in anos_5a if yo != y]
            med_outros = sum(outros) / len(outros) if outros else 0.0
            if med_outros > 0.1 and dpa_y > 3.0 * med_outros:
                anomalias_3x.append({
                    "ticker": ticker,
                    "ano": y,
                    "dpa": dpa_y,
                    "media_outros": med_outros,
                    "razao": dpa_y / med_outros
                })

    # Imprimir Relatório
    print("--- 1. LACUNAS DE PROVENTOS (Anos sem dado entre anos pagos) ---")
    if lacunas_encontradas:
        for it in lacunas_encontradas:
            print(f"  • {it['ticker']} ({it['ano']}): Yahoo R$ {it['yahoo']:.4f} | B3 R$ {it['b3']:.4f} → {it['status']}")
    else:
        print("  Nenhuma lacuna encontrada.")
    print()

    print("--- 2. DIVERGÊNCIAS YAHOO x B3 > 20% (Anos fechados) ---")
    if divergencias_encontradas:
        for it in divergencias_encontradas:
            print(f"  • {it['ticker']} ({it['ano']}): Yahoo R$ {it['yahoo']:.4f} vs B3 R$ {it['b3']:.4f} (Δ {it['diff_pct']:.1f}%)")
    else:
        print("  Nenhuma divergência > 20% encontrada.")
    print()

    print("--- 3. ANOMALIAS: DPA > 3x A MÉDIA DOS DEMAIS ANOS (Amortização/Grupamento) ---")
    if anomalias_3x:
        for it in anomalias_3x:
            print(f"  • {it['ticker']} ({it['ano']}): DPA R$ {it['dpa']:.4f} vs média outros 4A R$ {it['media_outros']:.4f} (Razão: {it['razao']:.1f}x)")
    else:
        print("  Nenhuma anomalia > 3x encontrada.")
    print()

    if falhas_b3:
        print("--- 4. ATIVOS COM FALHA NA CONSULTA B3 ---")
        for it in falhas_b3:
            print(f"  • {it['ticker']}: {it['motivo']}")
        print()

    print("=" * 80)
    print(f"RESUMO: {len(lacunas_encontradas)} lacunas | {len(divergencias_encontradas)} divergências > 20% | {len(anomalias_3x)} anomalias > 3x | {len(falhas_b3)} falhas B3")
    print("=" * 80)

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    auditar()
