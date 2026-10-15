"""Fehmir · Atualiza a base de benchmarks oficiais:
- CDI diário (Banco Central SGS 12)
- IPCA mensal (Banco Central SGS 433)
- Ibovespa diário (Yahoo Finance ^BVSP)
- IFIX (Yahoo Finance se houver, ou null)

Gera dados/benchmarks.js com `window.FEHMIR_BENCH = {...}`.
"""
import json, sys, time, datetime, pathlib, urllib.request, urllib.error

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "benchmarks.js"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Fehmir/1.0"}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def formatar_data_iso(data_str_br):
    """Converte 'DD/MM/AAAA' para 'AAAA-MM-DD'."""
    partes = data_str_br.split("/")
    if len(partes) == 3:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return data_str_br


def formatar_ano_mes(data_str_br):
    """Converte 'DD/MM/AAAA' para 'AAAA-MM'."""
    partes = data_str_br.split("/")
    if len(partes) == 3:
        return f"{partes[2]}-{partes[1]}"
    return data_str_br


def baixar_sgs(serie_num, data_inicio, tentativas=3):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_num}/dados?formato=json&dataInicial={data_inicio}"
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read().decode("utf-8"))
                if isinstance(res, list):
                    return res
                print(f"SGS {serie_num} retornou não-lista: {res}")
                return []
        except Exception as e:
            if i == tentativas - 1:
                print(f"Erro ao baixar SGS {serie_num}: {e}")
                return []
            time.sleep(2 * (i + 1))
    return []


def baixar_ibov_5a():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EBVSP?range=5y&interval=1d"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            js = json.loads(r.read().decode("utf-8"))
            res = js.get("chart", {}).get("result", [{}])[0]
            timestamps = res.get("timestamp") or []
            closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
            serie = []
            for ts, c in zip(timestamps, closes):
                if c is not None and c > 0:
                    dt_iso = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")
                    serie.append([dt_iso, round(c, 2)])
            return serie
    except Exception as e:
        print(f"Erro ao baixar Ibovespa do Yahoo: {e}")
        return []


def baixar_ifix_5a():
    # Tenta obter dados do IFIX. Se não houver série diária confiável com mais de 100 pregões, retorna None.
    for sym in ["IFIX.SA", "^IFIX", "XFIX11.SA"]:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?range=5y&interval=1d"
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                js = json.loads(r.read().decode("utf-8"))
                res = js.get("chart", {}).get("result")
                if res:
                    timestamps = res[0].get("timestamp") or []
                    closes = (res[0].get("indicators", {}).get("quote") or [{}])[0].get("close") or []
                    validos = [[datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d"), round(c, 2)]
                               for t, c in zip(timestamps, closes) if c is not None and c > 0]
                    if len(validos) >= 100:
                        return validos
        except Exception:
            pass
    return None


def main():
    hoje = datetime.date.today()
    data_5a = (hoje - datetime.timedelta(days=5 * 365 + 15)).strftime("%d/%m/%Y")
    data_hoje = hoje.strftime("%d/%m/%Y")

    print(f"1/4 Baixando CDI diário (SGS 12) desde {data_5a}...")
    raw_cdi = baixar_sgs(12, data_5a)
    cdi_serie = []
    for item in raw_cdi:
        try:
            dt = formatar_data_iso(item["data"])
            val = float(item["valor"])
            cdi_serie.append([dt, round(val, 6)])
        except (KeyError, ValueError):
            continue

    print(f"2/4 Baixando IPCA mensal (SGS 433) desde {data_5a}...")
    raw_ipca = baixar_sgs(433, data_5a)
    ipca_serie = []
    for item in raw_ipca:
        try:
            dt = formatar_ano_mes(item["data"])
            val = float(item["valor"])
            ipca_serie.append([dt, round(val, 4)])
        except (KeyError, ValueError):
            continue

    print("3/4 Baixando Ibovespa (^BVSP) 5 anos...")
    ibov_serie = baixar_ibov_5a()

    print("4/4 Tentando IFIX no Yahoo...")
    ifix_serie = baixar_ifix_5a()
    if ifix_serie is None:
        print("  -> IFIX: sem série histórica longa no Yahoo Finance; omitido conforme especificação (null).")

    atualizado_str = hoje.strftime("%Y-%m-%d %H:%M")
    benchmarks_obj = {
        "atualizado": atualizado_str,
        "cdi": cdi_serie,
        "ipca": ipca_serie,
        "ibov": ibov_serie,
        "ifix": ifix_serie
    }

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    conteudo_js = "window.FEHMIR_BENCH = " + json.dumps(benchmarks_obj, ensure_ascii=False, separators=(',', ':')) + ";\n"
    SAIDA.write_text(conteudo_js, encoding="utf-8")
    tamanho_kb = len(conteudo_js.encode("utf-8")) / 1024
    print(f"✅ benchmarks.js gerado com sucesso em {SAIDA} ({tamanho_kb:.1f} KB).")

    # Auditoria e Cálculos de 12 meses
    # 1. CDI 12 meses acumulado
    if len(cdi_serie) >= 250:
        ultimos_252_cdi = cdi_serie[-252:]
        fator_cdi = 1.0
        for _, taxa_dia in ultimos_252_cdi:
            fator_cdi *= (1.0 + taxa_dia / 100.0)
        cdi_12m_pct = (fator_cdi - 1.0) * 100.0
        print(f"Auditoria CDI 12M (~252 pregões): {cdi_12m_pct:.2f}%")

    # 2. IPCA 12 meses acumulado
    if len(ipca_serie) >= 12:
        ultimos_12_ipca = ipca_serie[-12:]
        fator_ipca = 1.0
        for _, taxa_mes in ultimos_12_ipca:
            fator_ipca *= (1.0 + taxa_mes / 100.0)
        ipca_12m_pct = (fator_ipca - 1.0) * 100.0
        meses_nomes = f"{ultimos_12_ipca[0][0]} a {ultimos_12_ipca[-1][0]}"
        print(f"Auditoria IPCA 12M ({meses_nomes}): {ipca_12m_pct:.2f}%")


if __name__ == "__main__":
    main()
