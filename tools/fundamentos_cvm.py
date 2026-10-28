"""
tools/fundamentos_cvm.py

Baixa demonstrações contábeis oficiais abertas da CVM (ITR e DFP),
processa balanços consolidados e DRE de forma dinâmica para apurar:
- Patrimônio Líquido atribuído aos controladores (BPP)
- Lucro Líquido 12M (DFP ano anterior + ITR YTD atual − ITR YTD ano anterior)
- Ações em circulação (Composição de Capital) com suporte estrito a UNITS
- VPA, LPA e ROE oficiais atualizados
- Checagem de sanidade obrigatória contra valor de mercado de referência

Saída: dados/fundamentos_cvm.js
"""

import csv
import datetime
import json
import os
from pathlib import Path
import sys
import unicodedata
import urllib.request
import zipfile

BASE_DIR = Path(__file__).resolve().parent.parent
MAPA_PATH = BASE_DIR / "tools" / "mapa_cnpj.json"
CACHE_DIR = BASE_DIR / "scratch" / "cvm_cache"
SAIDA = BASE_DIR / "dados" / "fundamentos_cvm.js"
MERCADO_PATH = BASE_DIR / "dados" / "mercado.js"
HISTORICO_PATH = BASE_DIR / "dados" / "historico.js"

UNITS = {
    "TAEE11": {"fator": 3, "ref_ticker": "TAEE4"},
    "SANB11": {"fator": 2, "ref_ticker": "SANB4"},
    "ENGI11": {"fator": 5, "ref_ticker": "ENGI4"},
    "SAPR11": {"fator": 5, "ref_ticker": "SAPR4"},
    "ALUP11": {"fator": 3, "ref_ticker": "ALUP4"},
    "KLBN11": {"fator": 5, "ref_ticker": "KLBN4"},
    "BPAC11": {"fator": 3, "ref_ticker": "BPAC3"}
}


def norm(texto):
    if not texto:
        return ""
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ASCII", "ignore")
        .decode("ASCII")
        .upper()
        .strip()
    )


def baixar_zip_se_necessario(url, nome_arquivo):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destino = CACHE_DIR / nome_arquivo
    if destino.exists() and destino.stat().st_size > 100_000:
        return destino

    print(f"Baixando {url} -> {destino.name}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(destino, "wb") as f:
            f.write(resp.read())
        print(f"Download concluído: {destino.name} ({destino.stat().st_size / 1024 / 1024:.1f} MB)")
        return destino
    except Exception as e:
        print(f"Erro ao baixar {url}: {e}")
        return None


def ler_csv_zip(zip_obj, prefixo):
    for n in zip_obj.namelist():
        if prefixo in n:
            raw = zip_obj.read(n).decode("latin1")
            return list(csv.DictReader(raw.splitlines(), delimiter=";"))
    return []


def indexar_por_cnpj(linhas):
    idx = {}
    for r in linhas:
        cnpj = r.get("CNPJ_CIA")
        if not cnpj:
            continue
        if cnpj not in idx:
            idx[cnpj] = []
        idx[cnpj].append(r)
    return idx


def buscar_lucro(tabela_rows, dt_ref, dti, dtf):
    cand_ctrl = None
    cand_cons = None
    for r in tabela_rows:
        if r.get("DT_REFER") == dt_ref and r.get("ORDEM_EXERC") in ["ÚLTIMO", "ULTIMO"]:
            if r.get("DT_INI_EXERC") == dti and r.get("DT_FIM_EXERC") == dtf:
                esc = 1000.0 if r.get("ESCALA_MOEDA") == "MIL" else 1.0
                ds = norm(r.get("DS_CONTA", ""))
                cd = r.get("CD_CONTA", "")
                vl = float(r.get("VL_CONTA") or 0) * esc
                if "ANTES" in ds or "TRIBUTOS SOBRE" in ds:
                    continue
                if cd in ["3.11", "3.09", "3.13"] and ("LUCRO" in ds or "PREJUIZO" in ds or "CONSOLIDADO" in ds or "RESULTADO LIQUIDO" in ds):
                    cand_cons = vl
                elif ("ATRIBUIDO A SOCIOS DA EMPRESA CONTROLADORA" in ds or "CONTROLADOR" in ds or cd in ["3.11.01", "3.09.01", "3.13.01"]) and ("NAO CONTROLADOR" not in ds):
                    if vl != 0:
                        cand_ctrl = vl
                    elif cand_ctrl is None:
                        cand_ctrl = vl
    if cand_ctrl is not None and cand_ctrl != 0:
        return cand_ctrl
    if cand_cons is not None and cand_cons != 0:
        return cand_cons
    if cand_ctrl is not None:
        return cand_ctrl
    return cand_cons


def roe_anual(cnpjs, ano_atual):
    """ROE anual (lucro do ano ÷ PL médio dos controladores no ano) dos 5 anos fechados, pelas DFPs da CVM.
    Devolve {cnpj: {"2021": 23.4, ...}}. Ano sem DFP ou sem dado fica de fora (nunca vira 0)."""
    saida = {c: {} for c in cnpjs}
    for ano in range(ano_atual - 5, ano_atual):
        caminho = baixar_zip_se_necessario(
            f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip", f"dfp_{ano}.zip")
        if not caminho:
            continue
        z = zipfile.ZipFile(caminho)
        for demo in ("con", "ind"):
            dre = indexar_por_cnpj([r for r in ler_csv_zip(z, f"DRE_{demo}_{ano}") if r.get("CNPJ_CIA") in saida])
            bpp = indexar_por_cnpj([r for r in ler_csv_zip(z, f"BPP_{demo}_{ano}") if r.get("CNPJ_CIA") in saida])
            for cnpj in saida:
                if str(ano) in saida[cnpj] or cnpj not in bpp:
                    continue
                dt = f"{ano}-12-31"
                # PL dos controladores no fim do ano (ÚLTIMO) e no fim do ano anterior (PENÚLTIMO): ROE sobre o PL médio
                pls = {}
                for r in bpp[cnpj]:
                    ordem = norm(r.get("ORDEM_EXERC", ""))
                    if r.get("DT_REFER") != dt or ordem not in ("ULTIMO", "PENULTIMO"):
                        continue
                    cd, ds = r.get("CD_CONTA", ""), norm(r.get("DS_CONTA", ""))
                    vl = float(r.get("VL_CONTA") or 0) * (1000.0 if r.get("ESCALA_MOEDA") == "MIL" else 1.0)
                    reg = pls.setdefault(ordem, {"pl": None, "nc": 0.0})
                    if cd in ("2.03", "2.07", "2.08", "2.09") and "PATRIMONIO LIQUIDO" in ds:
                        reg["pl"] = vl
                    elif cd.startswith(("2.03", "2.07", "2.08", "2.09")) and ("NAO CONTROLADOR" in ds or "NAO-CONTROLADOR" in ds):
                        reg["nc"] = vl
                def ctrl(reg):
                    if not reg or reg["pl"] is None:
                        return None
                    v = reg["pl"] - reg["nc"]
                    return v if v > 0 else reg["pl"]
                pl_fim, pl_ini = ctrl(pls.get("ULTIMO")), ctrl(pls.get("PENULTIMO"))
                if pl_fim is None:
                    continue
                pl_medio = (pl_fim + pl_ini) / 2 if pl_ini and pl_ini > 0 else pl_fim
                lucro = buscar_lucro(dre.get(cnpj, []), dt, f"{ano}-01-01", dt)
                if not lucro or pl_medio <= 0:
                    continue
                saida[cnpj][str(ano)] = round(lucro / pl_medio * 100, 2)
    return saida


def main():
    if not MAPA_PATH.exists():
        print(f"Erro: {MAPA_PATH} não encontrado.")
        return 1

    with open(MAPA_PATH, "r", encoding="utf-8") as f:
        mapa = json.load(f)

    # Carregar mercado.js para checagem de sanidade
    merc_dict = {}
    if MERCADO_PATH.exists():
        text_m = MERCADO_PATH.read_text(encoding="utf-8")
        idx_start = text_m.find("window.FEHMIR_MERCADO = ")
        if idx_start != -1:
            json_m = text_m[idx_start + len("window.FEHMIR_MERCADO = "):].strip()
            if json_m.endswith(";"):
                json_m = json_m[:-1].strip()
            try:
                merc_list = json.loads(json_m)
                merc_dict = {item["t"]: item for item in merc_list}
            except Exception:
                pass

    # Carregar historico.js para precos
    hist_dict = {}
    if HISTORICO_PATH.exists():
        text_h = HISTORICO_PATH.read_text(encoding="utf-8")
        idx_h = text_h.find("window.FEHMIR_HIST = ")
        if idx_h != -1:
            try:
                hist_dict = json.loads(text_h[idx_h + len("window.FEHMIR_HIST = "):text_h.rfind(";")].strip())
            except Exception:
                pass

    ano_atual = datetime.datetime.now().year  # 2026
    ano_ant = ano_atual - 1                   # 2025
    ano_ret = ano_atual - 2                   # 2024

    p_itr_atual = baixar_zip_se_necessario(f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano_atual}.zip", f"itr_{ano_atual}.zip")
    p_dfp_ant = baixar_zip_se_necessario(f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano_ant}.zip", f"dfp_{ano_ant}.zip")
    p_itr_ant = baixar_zip_se_necessario(f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano_ant}.zip", f"itr_{ano_ant}.zip")
    p_dfp_ret = baixar_zip_se_necessario(f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano_ret}.zip", f"dfp_{ano_ret}.zip")

    if not p_itr_atual or not p_dfp_ant or not p_itr_ant:
        print("Erro: não foi possível obter os arquivos ZIP da CVM.")
        return 1

    print("Carregando e indexando arquivos da CVM...")
    z_itr_atual = zipfile.ZipFile(p_itr_atual)
    z_dfp_ant = zipfile.ZipFile(p_dfp_ant)
    z_itr_ant = zipfile.ZipFile(p_itr_ant)
    z_dfp_ret = zipfile.ZipFile(p_dfp_ret) if p_dfp_ret else None

    # Composicao de Capital
    cap_linhas = ler_csv_zip(z_itr_atual, f"composicao_capital_{ano_atual}") + ler_csv_zip(z_itr_ant, f"composicao_capital_{ano_ant}")
    cap_idx = indexar_por_cnpj(cap_linhas)

    # BPP (Balanço Patrimonial Passivo)
    bpp_con_atual_idx = indexar_por_cnpj(ler_csv_zip(z_itr_atual, f"BPP_con_{ano_atual}"))
    bpp_ind_atual_idx = indexar_por_cnpj(ler_csv_zip(z_itr_atual, f"BPP_ind_{ano_atual}"))
    bpp_con_ant_idx = indexar_por_cnpj(ler_csv_zip(z_itr_ant, f"BPP_con_{ano_ant}"))
    bpp_ind_ant_idx = indexar_por_cnpj(ler_csv_zip(z_itr_ant, f"BPP_ind_{ano_ant}"))

    # DRE (Demonstração do Resultado do Exercício)
    dre_con_atual_idx = indexar_por_cnpj(ler_csv_zip(z_itr_atual, f"DRE_con_{ano_atual}"))
    dre_ind_atual_idx = indexar_por_cnpj(ler_csv_zip(z_itr_atual, f"DRE_ind_{ano_atual}"))
    dre_con_dfp_ant_idx = indexar_por_cnpj(ler_csv_zip(z_dfp_ant, f"DRE_con_{ano_ant}"))
    dre_ind_dfp_ant_idx = indexar_por_cnpj(ler_csv_zip(z_dfp_ant, f"DRE_ind_{ano_ant}"))
    dre_con_itr_ant_idx = indexar_por_cnpj(ler_csv_zip(z_itr_ant, f"DRE_con_{ano_ant}"))
    dre_ind_itr_ant_idx = indexar_por_cnpj(ler_csv_zip(z_itr_ant, f"DRE_ind_{ano_ant}"))
    dre_con_dfp_ret_idx = indexar_por_cnpj(ler_csv_zip(z_dfp_ret, f"DRE_con_{ano_ret}")) if z_dfp_ret else {}

    dados = {}
    falhas = []
    auditoria_sanidade = []
    sem_referencia = []
    ajustes_escala = []

    print(f"Processando {len(mapa)} ativos...")

    for ticker, info in sorted(mapa.items()):
        cnpj = info["cnpj"]
        rows_cap = cap_idx.get(cnpj, [])
        if not rows_cap:
            falhas.append({"t": ticker, "motivo": f"Sem ações em composicao_capital (CNPJ {cnpj})"})
            continue

        rows_cap_ordenadas = sorted(rows_cap, key=lambda r: r.get("DT_REFER", ""), reverse=True)
        r_cap_recente = rows_cap_ordenadas[0]

        h = hist_dict.get(ticker)
        if h and h.get("c"):
            ultimos_c = h["c"][-5:]
            preco_robo = sorted(ultimos_c)[len(ultimos_c) // 2]
        else:
            preco_robo = None

        mc_ref = merc_dict.get(ticker, {}).get("mc")
        if (not mc_ref or mc_ref == 0) and ticker in UNITS:
            ref_t = UNITS[ticker]["ref_ticker"]
            mc_ref = merc_dict.get(ref_t, {}).get("mc")
        if (not mc_ref or mc_ref == 0) and ticker == "TRPL4":
            mc_ref = merc_dict.get("ISAE4", {}).get("mc")

        tot = float(r_cap_recente.get("QT_ACAO_TOTAL_CAP_INTEGR") or 0)
        tes = float(r_cap_recente.get("QT_ACAO_TOTAL_TESOURO") or 0)

        # Regra genérica de escala contra o trimestre anterior:
        # Se as ações do trimestre mais recente forem ~10x ou ~1000x as do anterior (ou o inverso), usar o anterior
        if len(rows_cap_ordenadas) > 1:
            r_ant = rows_cap_ordenadas[1]
            tot_ant = float(r_ant.get("QT_ACAO_TOTAL_CAP_INTEGR") or 0)
            tes_ant = float(r_ant.get("QT_ACAO_TOTAL_TESOURO") or 0)
            if tot_ant > 0 and tot > 0:
                razao_tri = tot / tot_ant
                if 8.0 <= razao_tri <= 12.0:
                    ajustes_escala.append({"t": ticker, "motivo": f"Ações no tri recente ({tot:,.0f}) ~10x do anterior ({tot_ant:,.0f}); adotado trimestre anterior"})
                    tot, tes = tot_ant, tes_ant
                elif 0.08 <= razao_tri <= 0.12:
                    ajustes_escala.append({"t": ticker, "motivo": f"Ações no tri recente ({tot:,.0f}) ~0.1x do anterior ({tot_ant:,.0f}); adotado trimestre anterior"})
                    tot, tes = tot_ant, tes_ant
                elif 0.0008 <= razao_tri <= 0.0012:
                    ajustes_escala.append({"t": ticker, "motivo": f"Ações no tri recente ({tot:,.0f}) ~0.001x do anterior ({tot_ant:,.0f}); adotado trimestre anterior"})
                    tot, tes = tot_ant, tes_ant
                elif 800.0 <= razao_tri <= 1200.0:
                    ajustes_escala.append({"t": ticker, "motivo": f"Ações no tri recente ({tot:,.0f}) ~1000x do anterior ({tot_ant:,.0f}); adotado trimestre anterior"})
                    tot, tes = tot_ant, tes_ant

        # Regra genérica de capital reportado em milhares (empresas listadas com tot < 1.000.000 de ações no ITR)
        if tot < 1_000_000:
            tot *= 1000.0
            ajustes_escala.append({"t": ticker, "motivo": f"Capital social reportado em milhares ({tot/1000:,.0f} mil ações); normalizado para unidades"})

        circ = tot - tes

        # Ajuste de escala para milhares (ex: TAEE11 onde tot=1033497 e SANB11 onde tot=7498531)
        fator_unit = UNITS[ticker]["fator"] if ticker in UNITS else 1
        teste_impl = (preco_robo * (circ / fator_unit)) / 1e9 if preco_robo else None

        if mc_ref and mc_ref > 0 and teste_impl and teste_impl < mc_ref * 0.05:
            circ *= 1000.0
        elif circ < 50_000_000 and ticker in ["TAEE11", "SANB11", "ENGI11", "SAPR11", "ALUP11"]:
            circ *= 1000.0

        is_unit = ticker in UNITS
        if is_unit:
            acoes_para_calculo = circ / fator_unit
        else:
            acoes_para_calculo = circ

        # 1. BPP
        linhas_bpp = [r for r in bpp_con_atual_idx.get(cnpj, []) if r.get("ORDEM_EXERC") in ["ÚLTIMO", "ULTIMO"]]
        tipo_demo = "con"
        if not linhas_bpp:
            linhas_bpp = [r for r in bpp_ind_atual_idx.get(cnpj, []) if r.get("ORDEM_EXERC") in ["ÚLTIMO", "ULTIMO"]]
            tipo_demo = "ind"
        if not linhas_bpp:
            falhas.append({"t": ticker, "motivo": f"Sem registros BPP na CVM"})
            continue

        dts_bpp = sorted(list(set(r["DT_REFER"] for r in linhas_bpp)))
        dt_refer = dts_bpp[-1]
        linhas_bpp_dt = [r for r in linhas_bpp if r["DT_REFER"] == dt_refer]

        pl_consolidado = None
        pl_nao_ctrl = 0.0
        for r in linhas_bpp_dt:
            esc = 1000.0 if r.get("ESCALA_MOEDA") == "MIL" else 1.0
            cd = r.get("CD_CONTA", "")
            ds = norm(r.get("DS_CONTA", ""))
            vl = float(r.get("VL_CONTA") or 0) * esc
            if cd in ["2.03", "2.07", "2.08", "2.09"] and "PATRIMONIO LIQUIDO" in ds:
                pl_consolidado = vl
            elif cd.startswith(("2.03", "2.07", "2.08", "2.09")) and ("NAO CONTROLADOR" in ds or "NAO-CONTROLADOR" in ds):
                pl_nao_ctrl = vl

        pl_controladores = (pl_consolidado - pl_nao_ctrl) if pl_consolidado is not None else None
        if pl_controladores is None or pl_controladores <= 0:
            pl_controladores = pl_consolidado

        if pl_controladores is None or pl_controladores <= 0:
            falhas.append({"t": ticker, "motivo": f"PL inválido ({pl_controladores})"})
            continue

        # 2. DRE
        tab_dre_atual = dre_con_atual_idx.get(cnpj, []) if tipo_demo == "con" else dre_ind_atual_idx.get(cnpj, [])
        tab_dfp_ant = dre_con_dfp_ant_idx.get(cnpj, []) if tipo_demo == "con" else dre_ind_dfp_ant_idx.get(cnpj, [])
        tab_dre_ant = dre_con_itr_ant_idx.get(cnpj, []) if tipo_demo == "con" else dre_ind_itr_ant_idx.get(cnpj, [])

        dti_ytd = f"{ano_atual}-01-01"
        dtf_ytd = dt_refer
        dt_ant_ytd = f"{ano_ant}-{dt_refer[5:]}"
        dti_ant_ytd = f"{ano_ant}-01-01"
        dt_dfp_ant = f"{ano_ant}-12-31"

        l_ytd = buscar_lucro(tab_dre_atual, dt_refer, dti_ytd, dtf_ytd)
        l_dfp = buscar_lucro(tab_dfp_ant, dt_dfp_ant, dti_ant_ytd, dt_dfp_ant)
        l_ytd_ant = buscar_lucro(tab_dre_ant, dt_ant_ytd, dti_ant_ytd, dt_ant_ytd)

        if l_dfp is not None and l_ytd is not None and l_ytd_ant is not None:
            lucro12m = l_dfp + l_ytd - l_ytd_ant
        elif l_ytd is not None:
            mes_ref = int(dt_refer[5:7])
            lucro12m = (l_ytd / mes_ref) * 12
        else:
            lucro12m = None

        if lucro12m is None:
            falhas.append({"t": ticker, "motivo": f"Sem lucro na DRE para {dt_refer}"})
            continue

        vpa = pl_controladores / acoes_para_calculo
        lpa = lucro12m / acoes_para_calculo
        roe = (lucro12m / pl_controladores * 100) if pl_controladores > 0 else None

        # CHECAGEM DE SANIDADE OBRIGATORIA
        mkt_cap_impl = (preco_robo * acoes_para_calculo) / 1e9 if preco_robo else None
        diff_sanidade = None
        if mkt_cap_impl and mc_ref and mc_ref > 0:
            razao = mkt_cap_impl / mc_ref
            diff_sanidade = (razao - 1.0) * 100
            if abs(diff_sanidade) > 20.0:
                falhas.append({
                    "t": ticker,
                    "motivo": f"Valor de mercado implícito R$ {mkt_cap_impl:.2f} bi diverge {diff_sanidade:+.1f}% do mercado de referência R$ {mc_ref:.2f} bi (razão {razao:.2f}x)"
                })
                continue
            auditoria_sanidade.append({
                "t": ticker,
                "impl": round(mkt_cap_impl, 2),
                "ref": round(mc_ref, 2),
                "diff_pct": round(diff_sanidade, 1),
                "unit": is_unit
            })
        else:
            sem_referencia.append(ticker)

        tri_num = int(dt_refer[5:7]) // 3
        ref_label = f"{tri_num}T{dt_refer[2:4]}"

        dados[ticker] = {
            "lpa": round(lpa, 2),
            "vpa": round(vpa, 2),
            "roe": round(roe, 2),
            "pl_liquido": round(pl_controladores, 0),
            "lucro12m": round(lucro12m, 0),
            "acoes": int(acoes_para_calculo),
            "ref": ref_label,
            "demo": tipo_demo,
            "fonte": f"ITR/DFP CVM ({ref_label})"
        }

    # ROE anual dos 5 anos fechados (régua de bancos: qualidade comprovada = ROE >= 18% em 5 de 5 anos)
    hist_roe = roe_anual({info["cnpj"] for info in mapa.values()}, ano_atual)
    for ticker, info in mapa.items():
        if ticker in dados and hist_roe.get(info["cnpj"]):
            dados[ticker]["roeAnual"] = hist_roe[info["cnpj"]]

    meta = {
        "gerado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": f"CVM Dados Abertos (ITR/DFP consolidado/individual {ano_atual}/{ano_ant})",
        "total_ativos": len(dados),
        "ok": len(dados),
        "falhas": falhas,
        "sanidade_auditada": len(auditoria_sanidade),
        "sem_referencia": sorted(list(set(sem_referencia))),
        "ajustes_escala": ajustes_escala
    }

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    conteudo = (
        "/* Gerado por tools/fundamentos_cvm.py — não editar à mão. */\n"
        "window.FEHMIR_FUND_CVM_META = " + json.dumps(meta, indent=2, ensure_ascii=False) + ";\n"
        "window.FEHMIR_FUND_CVM = " + json.dumps(dados, indent=2, ensure_ascii=False) + ";\n"
    )
    SAIDA.write_text(conteudo, encoding="utf-8")
    print(f"\nOK: {len(dados)} ativos salvos em {SAIDA}. Falhas: {len(falhas)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
