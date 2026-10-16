"""Fehmir · Robô de Novidades (CVM IPE e Fundos.NET B3 com resumos via Gemini API).

Busca fatos relevantes e relatórios gerenciais dos ativos da carteira (últimos 45-90 dias),
extrai os pontos principais, o que mudou e novos alertas via Gemini Flash,
e atualiza dados/novidades.js.

Regras de segurança:
- Chave apenas via variável de ambiente `GEMINI_API_KEY`.
- Sem chave, o script não quebra: lista os documentos encontrados sem resumo e marca `resumido_ia: False`.
- Documentos catalogados sem chave continuam elegíveis para receber resumo quando a chave estiver disponível.
"""
import os
import io
import sys
import re
import json
import time
import base64
import zipfile
import datetime
import pathlib
import urllib.request
import urllib.parse
import urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PAINEL = RAIZ / "painel-barsi.html"
SAIDA = RAIZ / "dados" / "novidades.js"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://fnet.bmfbovespa.com.br/fnet/publico/abrirGerenciadorDocumentosCVM"
}

# Mapa Oficial Ticker -> CNPJ (21 ativos da carteira + acompanhados)
# Fontes oficiais:
# - FIIs e Fiagros: CVM Informes Mensais (inf_mensal_fii_geral_2024 / 2026 via cruzamento por Código ISIN)
# - Ações: CVM Cadastro de Companhias Abertas (cad_cia_aberta.csv)
MAPA_CNPJ = {
    # FIIs e Fiagros (11 ativos)
    "TRXF11": "28.548.288/0001-52",  # TRX REAL ESTATE FII (ISIN BRTRXFCTF003)
    "RECR11": "28.152.272/0001-26",  # REC RECEBÍVEIS IMOBILIÁRIOS FII (ISIN BRRECRCTF004)
    "GARE11": "37.295.919/0001-60",  # GUARDIAN LOGÍSTICA / GARE FII (ISIN BRGARECTF001)
    "MXRF11": "97.521.225/0001-25",  # MAXI RENDA FII (ISIN BRMXRFCTF008)
    "XPML11": "28.757.546/0001-00",  # XP MALLS FII (ISIN BRXPMLCTF000)
    "VILG11": "24.853.044/0001-22",  # VINCI LOGÍSTICA FII (ISIN BRVILGCTF001)
    "RZTR11": "36.501.128/0001-86",  # RIZA TERRAX FII (ISIN BRRZTRCTF003)
    "GGRC11": "26.614.291/0001-00",  # GGR COVEPI RENDA FII (ISIN BRGGRCCTF002)
    "KNCA11": "41.745.701/0001-37",  # KINEA CRÉDITO AGRO FIAGRO (ISIN BRKNCACTF014)
    "RZAG11": "40.413.979/0001-44",  # RIZA AGRO FIAGRO (ISIN BRRZAGCTF006)
    "HGRE11": "09.072.017/0001-29",  # CSHG REAL ESTATE FII (ISIN BRHGRECTF006)
    # Ações B.A.S.E. e fora da base (8 ativas)
    "BBAS3": "00.000.000/0001-91",   # BANCO DO BRASIL S.A.
    "BBSE3": "17.344.597/0001-94",   # BB SEGURIDADE PARTICIPAÇÕES S.A.
    "TAEE11": "07.859.971/0001-30",  # TRANSMISSORA ALIANÇA DE ENERGIA ELÉTRICA S.A. - TAESA
    "CMIG4": "17.155.730/0001-64",   # COMPANHIA ENERGÉTICA DE MINAS GERAIS - CEMIG
    "CPLE3": "76.483.817/0001-20",   # COMPANHIA PARANAENSE DE ENERGIA - COPEL
    "PETR4": "33.000.167/0001-01",   # PETRÓLEO BRASILEIRO S.A. - PETROBRAS
    "RECV3": "03.342.704/0001-30",   # PETRORECÔNCAVO S.A.
    "LOGG3": "09.041.168/0001-10",   # LOG COMMERCIAL PROPERTIES E PARTICIPAÇÕES S.A.
    # Encerrados (mantidos para histórico e integridade)
    "LAVV3": "26.462.693/0001-28",   # LAVVI EMPREENDIMENTOS IMOBILIÁRIOS S.A.
    "MELK3": "12.181.987/0001-77",   # MELNICK DESENVOLVIMENTO IMOBILIÁRIO S.A.
}


def tickers_ativos_carteira():
    """Lê do painel-barsi.html os tickers de Ações e FIIs com posição aberta."""
    if not PAINEL.exists():
        return list(MAPA_CNPJ.keys())
    html = PAINEL.read_text(encoding="utf-8", errors="ignore")
    tickers = []
    for bloco in ["BASE_STOCKS", "OUT_OF_BASE", "FIIS"]:
        pos = html.find(f"const {bloco}")
        if pos != -1:
            end = html.find("];", pos)
            chunk = html[pos:end]
            achados = re.findall(r't:\s*"([A-Z0-9]+)"', chunk)
            for t in achados:
                if t not in ["LAVV3", "MELK3"] and t in MAPA_CNPJ:
                    tickers.append(t)
    return sorted(list(set(tickers)))


def carregar_cache():
    """Carrega dados/novidades.js se existir."""
    if not SAIDA.exists():
        return {}
    txt = SAIDA.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'window\.FEHMIR_NOVIDADES\s*=\s*(\{.*?\});', txt, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {}


def buscar_fundosnet(ticker, cnpj, dias=45):
    """Busca Relatórios Gerenciais e Fatos Relevantes no Fundos.NET (B3).
    
    Aplica timeout de 25s e até 2 retentativas em caso de lentidão.
    Se não encontrar nenhum documento em 45 dias, expande para 90 dias
    para capturar o último relatório publicado por fundos com publicação bimestral.
    """
    def _requisitar(janela_dias):
        hoje = datetime.date.today()
        inicio = hoje - datetime.timedelta(days=janela_dias)
        params = {
            "d": "1",
            "s": "0",
            "l": "30",
            "cnpjFundo": cnpj,
            "idCategoriaDocumento": "0",
            "idTipoDocumento": "0",
            "situacao": "A",
            "dataInicial": inicio.strftime("%d/%m/%Y"),
            "dataFinal": hoje.strftime("%d/%m/%Y"),
            "_": str(int(time.time() * 1000))
        }
        url = f"https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados?{urllib.parse.urlencode(params)}"
        
        for tentativa in range(3):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=25) as r:
                    js = json.loads(r.read().decode("utf-8", errors="replace"))
                    records = js.get("data", [])
                    docs = []
                    for rec in records:
                        cat = (rec.get("categoriaDocumento") or "").strip()
                        tipo = (rec.get("tipoDocumento") or "").strip()
                        desc = (rec.get("descricaoStatus") or "").strip()
                        texto_completo = f"{cat} {tipo} {desc}".lower()

                        eh_relatorio = "relat" in texto_completo and "gerencial" in texto_completo
                        eh_fato_relevante = "fato relevante" in texto_completo
                        if not (eh_relatorio or eh_fato_relevante):
                            continue

                        doc_id = str(rec.get("id"))
                        tipo_doc = "Relatório Gerencial" if eh_relatorio else "Fato Relevante"

                        data_str = rec.get("dataEntrega") or rec.get("dataReferencia") or ""
                        m_data = re.search(r'(\d{2})/(\d{2})/(\d{4})', data_str)
                        if m_data:
                            data_iso = f"{m_data.group(3)}-{m_data.group(2)}-{m_data.group(1)}"
                        else:
                            data_iso = hoje.strftime("%Y-%m-%d")

                        titulo = tipo or cat
                        if desc and desc != "Ativo com visualização":
                            titulo = f"{titulo} - {desc}"

                        docs.append({
                            "id": f"fnet_{doc_id}",
                            "data": data_iso,
                            "tipo": tipo_doc,
                            "titulo": titulo,
                            "url": f"https://fnet.bmfbovespa.com.br/fnet/publico/downloadDocumento?id={doc_id}",
                            "url_view": f"https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id={doc_id}"
                        })
                    return docs
            except Exception as e:
                if tentativa < 2:
                    time.sleep(2)
                else:
                    return []
        return []

    docs = _requisitar(dias)
    if not docs and dias < 90:
        # Fallback para 90 dias caso não tenha saído nos últimos 45 dias
        docs = _requisitar(90)
    return docs


def buscar_cvm_acoes(tickers_acoes, dias=45):
    """Busca Fatos Relevantes e Comunicados das ações na base aberta da CVM (IPE)."""
    hoje = datetime.date.today()
    corte = hoje - datetime.timedelta(days=dias)
    ano = hoje.year

    cnpj_to_ticker = {}
    for tk in tickers_acoes:
        cnpj = MAPA_CNPJ.get(tk)
        if cnpj:
            cnpj_to_ticker[cnpj] = tk

    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{ano}.zip"
    docs_por_ticker = {tk: [] for tk in tickers_acoes}

    for tentativa in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Fehmir/1.0"})
            with urllib.request.urlopen(req, timeout=35) as r:
                content = r.read()
            z = zipfile.ZipFile(io.BytesIO(content))
            csv_name = [n for n in z.namelist() if n.endswith('.csv')][0]
            with z.open(csv_name) as f:
                import csv
                text_stream = io.TextIOWrapper(f, encoding='latin1', errors='replace')
                reader = csv.DictReader(text_stream, delimiter=';')
                for row in reader:
                    cnpj = row.get("CNPJ_Companhia")
                    if cnpj not in cnpj_to_ticker:
                        continue

                    ticker = cnpj_to_ticker[cnpj]
                    cat = (row.get("Categoria") or "").strip()
                    tipo = (row.get("Tipo") or "").strip()
                    assunto = (row.get("Assunto") or "").strip()
                    dt_ent = (row.get("Data_Entrega") or "").strip()
                    dt_ref = (row.get("Data_Referencia") or "").strip()
                    link = (row.get("Link_Download") or "").strip()
                    proto = (row.get("Protocolo_Entrega") or "").strip()

                    dt_iso = dt_ent[:10] if dt_ent else dt_ref[:10]
                    try:
                        dt_obj = datetime.datetime.strptime(dt_iso, "%Y-%m-%d").date()
                        if dt_obj < corte:
                            continue
                    except Exception:
                        continue

                    aceitar = False
                    tipo_normalizado = "Fato Relevante"
                    if cat.lower() == "fato relevante":
                        aceitar = True
                    elif cat.lower() == "comunicado ao mercado":
                        txt_busca = f"{assunto} {tipo}".lower()
                        palavras = ["dividendo", "jcp", "provento", "aquisi", "venda de ativo", "guidance", "gestão", "gestao", "administra"]
                        if any(p in txt_busca for p in palavras):
                            aceitar = True
                            tipo_normalizado = "Comunicado ao Mercado"

                    if aceitar:
                        docs_por_ticker[ticker].append({
                            "id": f"cvm_{proto}",
                            "data": dt_iso,
                            "tipo": tipo_normalizado,
                            "titulo": assunto or tipo or cat,
                            "url": link,
                            "url_view": link
                        })
            break
        except Exception as e:
            if tentativa < 2:
                time.sleep(2)
            else:
                print(f"Aviso CVM IPE: erro ao baixar/processar zip: {e}")

    return docs_por_ticker


def baixar_pdf(url):
    """Baixa o conteúdo em bytes de um PDF público."""
    for tentativa in range(2):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            if tentativa < 1:
                time.sleep(2)
            else:
                print(f"Erro ao baixar PDF ({url[:60]}...): {e}")
                return None


# Modelo padrão (out/2026: o gemini-2.5-flash foi aposentado para contas novas e a própria API indicou o 3.8-flash).
# Se o Google aposentar este também, o robô consulta a lista de modelos e escolhe sozinho o Flash mais novo.
MODELO_PADRAO = "gemini-3.8-flash"
_modelo_ativo = None
_cota_diaria_esgotada = False


def _versao_modelo(nome):
    nums = re.findall(r"\d+(?:\.\d+)?", nome)
    return float(nums[0]) if nums else 0.0


def descobrir_modelo_flash(api_key, excluir=None):
    """Lista os modelos da conta e devolve o Flash mais novo que aceita generateContent (sem lite/preview/imagem/áudio)."""
    url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"
    try:
        req = urllib.request.Request(url, headers={"x-goog-api-key": api_key})
        with urllib.request.urlopen(req, timeout=30) as r:
            modelos = json.loads(r.read().decode("utf-8")).get("models", [])
    except Exception as e:
        print(f"Não consegui listar os modelos do Gemini: {e}", flush=True)
        return None
    candidatos = []
    for m in modelos:
        nome = m.get("name", "").replace("models/", "")
        if "flash" not in nome or "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if any(x in nome for x in ("lite", "preview", "exp", "image", "tts", "audio", "live", "thinking")):
            continue
        candidatos.append(nome)
    candidatos = [c for c in candidatos if c != excluir]
    if not candidatos:
        return None
    candidatos.sort(key=_versao_modelo, reverse=True)
    return candidatos[0]


def resumir_com_gemini(pdf_bytes, ticker, tipo_doc, titulo, metricas_anteriores=None, _tentou_trocar=False):
    """Chama a API do Gemini via REST para extrair resumo, mudanças e alertas."""
    global _modelo_ativo
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    if _modelo_ativo is None:
        _modelo_ativo = os.environ.get("GEMINI_MODEL") or MODELO_PADRAO
        print(f"Modelo Gemini em uso: {_modelo_ativo}", flush=True)
    modelo = _modelo_ativo
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    prompt_texto = (
        f"Você é um analista financeiro rigoroso especializado no método de dividendos e renda passiva.\n"
        f"Analise o documento anexo de {ticker} (Tipo: {tipo_doc}, Título: {titulo}).\n"
        f"Métricas conhecidas do documento anterior: {json.dumps(metricas_anteriores or {}, ensure_ascii=False)}.\n\n"
        f"Instruções:\n"
        f"1. Responda em português.\n"
        f"2. Extraia fatos estritamente presentes no documento. Se um dado não estiver no documento, use null.\n"
        f"3. Destaque o que mudou em relação ao período/documento anterior.\n"
        f"4. Indique novos riscos e alertas (vacância, inadimplência, corte de provento, litígio, emissão, endividamento).\n"
        f"5. Não faça recomendações de compra ou venda.\n"
        f"6. Defina a gravidade: 'info' (rotina, sem risco novo), 'atencao' (mudança relevante ou alerta leve) ou 'critico' (calote, corte brusco, litígio grave, perda de inquilino âncora).\n"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_texto},
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_b64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "resumo": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Até 5 pontos principais do documento"
                    },
                    "mudancas": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "O que mudou em relação ao período ou documento anterior"
                    },
                    "alertas": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Novos riscos identificados"
                    },
                    "metricas": {
                        "type": "OBJECT",
                        "properties": {
                            "vacancia_fisica": {"type": "NUMBER"},
                            "vacancia_financeira": {"type": "NUMBER"},
                            "inadimplencia": {"type": "NUMBER"},
                            "provento_por_cota": {"type": "NUMBER"},
                            "resultado_por_cota": {"type": "NUMBER"},
                            "reserva_por_cota": {"type": "NUMBER"},
                            "ltv": {"type": "NUMBER"}
                        }
                    },
                    "gravidade": {
                        "type": "STRING",
                        "enum": ["info", "atencao", "critico"]
                    }
                },
                "required": ["resumo", "mudancas", "alertas", "metricas", "gravidade"]
            }
        }
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
    )

    global _cota_diaria_esgotada
    erro_code, corpo = None, ""
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidate = res_json.get("candidates", [])[0]
                part_text = candidate.get("content", {}).get("parts", [])[0].get("text", "")
                return json.loads(part_text)
        except urllib.error.HTTPError as e:
            erro_code = e.code
            corpo = e.read().decode("utf-8", errors="replace")[:800]
        except Exception as e:
            print(f"Erro Gemini API ({ticker}): {e}", flush=True)
            if tentativa >= 1:
                return None
            time.sleep(10)
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
            continue
        # 429 = limite do plano gratuito; 500/503 = Google sobrecarregado: espera o que o Google pedir e tenta de novo
        if erro_code in (429, 500, 503) and tentativa < 3:
            if erro_code == 429 and re.search(r"(?i)per ?day|PerDay|daily", corpo):
                print(f"Cota DIÁRIA do Gemini esgotada ({ticker}): o restante fica para a próxima execução.", flush=True)
                _cota_diaria_esgotada = True
                return None
            m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', corpo)
            espera = min(float(m.group(1)) + 2, 90) if m else 20 * (tentativa + 1)
            print(f"Gemini HTTP {erro_code} ({ticker}): aguardando {espera:.0f}s e tentando de novo ({tentativa + 1}/3).", flush=True)
            time.sleep(espera)
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
            continue
        break

    print(f"Erro Gemini API ({ticker}): HTTP {erro_code} · modelo {modelo} · {corpo}", flush=True)
    if erro_code in (404, 503) and not _tentou_trocar:
        # 404 = modelo aposentado; 503 persistente = modelo sobrecarregado: tenta o outro Flash disponível
        novo_modelo = descobrir_modelo_flash(api_key, excluir=modelo)
        if novo_modelo and novo_modelo != modelo:
            print(f"Modelo {modelo} indisponível: trocando para {novo_modelo} e tentando de novo.", flush=True)
            _modelo_ativo = novo_modelo
            return resumir_com_gemini(pdf_bytes, ticker, tipo_doc, titulo, metricas_anteriores, _tentou_trocar=True)
    return None


def main():
    falha_ia_total = False
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY ausente: pulando resumos", flush=True)

    tickers = tickers_ativos_carteira()
    fiis = [t for t in tickers if t.endswith("11") and t != "TAEE11"]
    acoes = [t for t in tickers if not t.endswith("11") or t == "TAEE11"]

    print(f"Fehmir Novidades · Verificando {len(tickers)} ativos ({len(acoes)} Ações, {len(fiis)} FIIs)...", flush=True)

    cache = carregar_cache()

    # Indexa documentos existentes por id
    docs_existentes = {}
    for tk, doc_list in cache.items():
        for d in doc_list:
            if "id" in d:
                docs_existentes[d["id"]] = (tk, d)

    # 1. Coleta de Documentos das fontes oficiais
    docs_coletados = {t: [] for t in tickers}

    # Ações via CVM IPE
    print("Consultando CVM IPE para ações...", flush=True)
    docs_cvm = buscar_cvm_acoes(acoes, dias=45)
    for tk, dlist in docs_cvm.items():
        docs_coletados[tk].extend(dlist)

    # FIIs via Fundos.NET
    print("Consultando Fundos.NET para FIIs (com retentativas e timeout 25s)...", flush=True)
    for f in fiis:
        cnpj = MAPA_CNPJ[f]
        dlist = buscar_fundosnet(f, cnpj, dias=45)
        docs_coletados[f].extend(dlist)
        time.sleep(1)

    # 2. Atualização do Cache e identificação de documentos pendentes de resumo por IA
    # Para novos documentos: adiciona ao cache com resumido_ia = False
    for tk in tickers:
        if tk not in cache:
            cache[tk] = []
        for doc in docs_coletados[tk]:
            if doc["id"] not in docs_existentes:
                item_provisorio = {
                    "id": doc["id"],
                    "data": doc["data"],
                    "tipo": doc["tipo"],
                    "titulo": doc["titulo"],
                    "url": doc["url"],
                    "resumo": [f"{doc['tipo']} publicado em {doc['data']}."],
                    "mudancas": [],
                    "alertas": [],
                    "metricas": {
                        "vacancia_fisica": None, "vacancia_financeira": None, "inadimplencia": None,
                        "provento_por_cota": None, "resultado_por_cota": None, "reserva_por_cota": None, "ltv": None
                    },
                    "gravidade": "info",
                    "resumido_ia": False
                }
                cache[tk].append(item_provisorio)
                docs_existentes[doc["id"]] = (tk, item_provisorio)

    # 3. Processamento de Resumos via Gemini (se chave presente)
    # Documentos elegíveis: qualquer documento com resumido_ia == False (respeitando limite de 12 por execução)
    pendentes_ia = []
    for tk in sorted(cache.keys()):
        for d in cache[tk]:
            if not d.get("resumido_ia", False):
                pendentes_ia.append((tk, d))
    # Mais recentes primeiro (o que acabou de sair importa mais); no empate, Fato Relevante antes de relatório
    pendentes_ia.sort(key=lambda p: (p[1].get("data", ""), "fato" in (p[1].get("tipo", "").lower())), reverse=True)

    print(f"Total de documentos pendentes de resumo por IA: {len(pendentes_ia)}", flush=True)

    if api_key and pendentes_ia:
        lote_ia = pendentes_ia[:12]
        resumidos_ok = 0
        print(f"Processando {len(lote_ia)} resumos com Gemini nesta execução...", flush=True)
        for tk, doc in lote_ia:
            print(f" -> Resumindo {tk}: {doc['tipo']} - {doc['titulo'][:45]} ({doc['data']})", flush=True)
            pdf_bytes = baixar_pdf(doc["url"])
            if pdf_bytes:
                ult_metricas = None
                # Busca métricas anteriores conhecidas
                for outro in cache.get(tk, []):
                    if outro.get("id") != doc["id"] and outro.get("metricas"):
                        ult_metricas = outro["metricas"]
                        break

                resumo_data = resumir_com_gemini(pdf_bytes, tk, doc["tipo"], doc["titulo"], ult_metricas)
                if resumo_data:
                    doc["resumo"] = resumo_data.get("resumo") or []
                    doc["mudancas"] = resumo_data.get("mudancas") or []
                    doc["alertas"] = resumo_data.get("alertas") or []
                    doc["metricas"] = resumo_data.get("metricas") or {}
                    doc["gravidade"] = resumo_data.get("gravidade") or "info"
                    doc["resumido_ia"] = True
                    resumidos_ok += 1
            else:
                print(f"    PDF não baixado: {doc['url']}", flush=True)
            if _cota_diaria_esgotada:
                break
            time.sleep(8)  # plano gratuito: ~7 pedidos por minuto, com folga
        print(f"Resumos gerados nesta execução: {resumidos_ok} de {len(lote_ia)}", flush=True)
        if resumidos_ok == 0 and not _cota_diaria_esgotada:
            # Falha visível no GitHub Actions: com chave e pendências, zero resumos é erro (ver mensagens acima)
            falha_ia_total = True

    # 4. Ordenação e corte (máximo 6 por ativo, mais recentes primeiro)
    total_docs = 0
    saida_limpa = {}
    for tk in sorted(cache.keys()):
        # Ordena por data decrescente
        sorted_docs = sorted(cache[tk], key=lambda x: x.get("data", ""), reverse=True)
        saida_limpa[tk] = sorted_docs[:6]
        total_docs += len(saida_limpa[tk])

    SAIDA.parent.mkdir(exist_ok=True)
    conteudo_js = (
        "/* Gerado por tools/novidades.py — não editar à mão. */\n"
        "window.FEHMIR_NOVIDADES = " + json.dumps(saida_limpa, ensure_ascii=False, indent=2) + ";\n"
    )
    SAIDA.write_text(conteudo_js, encoding="utf-8")
    print(f"OK: {total_docs} documentos em {SAIDA.relative_to(RAIZ)}.\n", flush=True)

    # 5. Autoteste e Contagem dos 21 Ativos
    print("================ CONTAGEM POR ATIVO (AUTOTESTE) ================", flush=True)
    avisos_fii = []
    todos_21 = sorted(list(MAPA_CNPJ.keys()))
    for tk in todos_21:
        docs_ativo = saida_limpa.get(tk, [])
        qtd = len(docs_ativo)
        status_ia = sum(1 for d in docs_ativo if d.get("resumido_ia"))
        exemplo = f" (Mais recente: {docs_ativo[0]['data']} - {docs_ativo[0]['tipo']})" if qtd > 0 else ""
        print(f"{tk:7s}: {qtd} docs | IA: {status_ia}/{qtd}{exemplo}", flush=True)

        # Checagem de integridade para FIIs
        if tk.endswith("11") and tk != "TAEE11" and qtd == 0:
            avisos_fii.append(tk)

    if avisos_fii:
        print("\n[AVISOS DE INTEGRIDADE]", flush=True)
        for af in avisos_fii:
            print(f"AVISO: FII {af} sem nenhum documento nos últimos 90 dias (verificar CNPJ).", flush=True)
    else:
        print("\n✅ Integridade de FIIs: 100% dos FIIs possuem documentos recentes catalogados.", flush=True)

    if falha_ia_total:
        print("ERRO: havia chave e documentos pendentes, mas nenhum resumo foi gerado (ver 'Erro Gemini API' / 'PDF não baixado' acima).", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
