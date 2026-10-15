"""Fehmir · Robô de Novidades (CVM IPE e Fundos.NET B3 com resumos via Gemini API).

Busca fatos relevantes e relatórios gerenciais dos ativos da carteira (últimos 45 dias),
extrai os pontos principais, o que mudou e novos alertas via Gemini Flash,
e atualiza dados/novidades.js.

Regras de segurança:
- Chave apenas via variável de ambiente `GEMINI_API_KEY`.
- Sem chave, o script não quebra: lista os documentos encontrados sem resumo.
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

# Mapa oficial Ticker -> CNPJ (21 ativos da carteira + acompanhados)
MAPA_CNPJ = {
    # FIIs e Fiagros
    "TRXF11": "32.064.079/0001-57",
    "RECR11": "27.876.819/0001-09",
    "GARE11": "37.289.174/0001-50",
    "MXRF11": "97.521.225/0001-25",
    "XPML11": "28.757.546/0001-00",
    "VILG11": "30.297.801/0001-65",
    "RZTR11": "37.525.969/0001-07",
    "GGRC11": "26.614.485/0001-34",
    "KNCA11": "41.748.513/0001-68",
    "RZAG11": "43.344.974/0001-24",
    "HGRE11": "09.072.017/0001-29",
    # Ações B.A.S.E. e fora da base
    "BBAS3": "00.000.000/0001-91",
    "BBSE3": "17.344.597/0001-94",
    "TAEE11": "07.859.971/0001-30",
    "CMIG4": "17.155.730/0001-64",
    "CPLE3": "76.483.817/0001-20",
    "PETR4": "33.000.167/0001-01",
    "RECV3": "03.359.252/0001-05",
    "LOGG3": "09.117.202/0001-96",
    # Encerrados (mantidos para histórico)
    "LAVV3": "26.469.541/0001-57",
    "MELK3": "12.016.920/0001-41",
}


def tickers_ativos_carteira():
    """Lê do painel-barsi.html os tickers de Ações e FIIs com posição aberta."""
    if not PAINEL.exists():
        return list(MAPA_CNPJ.keys())
    html = PAINEL.read_text(encoding="utf-8", errors="ignore")
    # Busca blocos de BASE_STOCKS, OUT_OF_BASE e FIIS
    tickers = []
    for bloco in ["BASE_STOCKS", "OUT_OF_BASE", "FIIS"]:
        pos = html.find(f"const {bloco}")
        if pos != -1:
            end = html.find("];", pos)
            chunk = html[pos:end]
            achados = re.findall(r't:\s*"([A-Z0-9]+)"', chunk)
            for t in achados:
                # Excluir encerrados
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
    """Busca Relatórios Gerenciais e Fatos Relevantes no Fundos.NET (B3)."""
    hoje = datetime.date.today()
    inicio = hoje - datetime.timedelta(days=dias)
    params = {
        "d": "1",
        "s": "0",
        "l": "30",
        "tipoFundo": "1",
        "cnpjFundo": cnpj,
        "idCategoriaDocumento": "0",
        "idTipoDocumento": "0",
        "situacao": "A",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": hoje.strftime("%d/%m/%Y"),
        "_": str(int(time.time() * 1000))
    }
    url = f"https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=8) as r:
            js = json.loads(r.read().decode("utf-8", errors="replace"))
            records = js.get("data", [])
            docs = []
            for rec in records:
                cat = (rec.get("categoriaDocumento") or "").strip()
                tipo = (rec.get("tipoDocumento") or "").strip()
                desc = (rec.get("descricaoStatus") or "").strip()
                texto_completo = f"{cat} {tipo} {desc}".lower()

                # Filtrar apenas Relatório Gerencial ou Fato Relevante
                eh_relatorio = "relat" in texto_completo and "gerencial" in texto_completo
                eh_fato_relevante = "fato relevante" in texto_completo

                if not (eh_relatorio or eh_fato_relevante):
                    continue

                doc_id = str(rec.get("id"))
                tipo_doc = "Relatório Gerencial" if eh_relatorio else "Fato Relevante"

                # Data de entrega ou referência (ISO AAAA-MM-DD)
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
        # Se der timeout ou erro de conexão, pula suavemente
        return []


def buscar_cvm_acoes(tickers_acoes, dias=45):
    """Busca Fatos Relevantes das ações na base aberta da CVM (IPE)."""
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

                # Checagem de data
                dt_iso = dt_ent[:10] if dt_ent else dt_ref[:10]
                try:
                    dt_obj = datetime.datetime.strptime(dt_iso, "%Y-%m-%d").date()
                    if dt_obj < corte:
                        continue
                except Exception:
                    continue

                # Filtragem de categoria
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
    except Exception as e:
        print(f"Aviso CVM IPE: erro ao baixar/processar zip: {e}")

    return docs_por_ticker


def baixar_pdf(url):
    """Baixa o conteúdo em bytes de um PDF público."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except Exception as e:
        print(f"Erro ao baixar PDF ({url[:60]}...): {e}")
        return None


def resumir_com_gemini(pdf_bytes, ticker, tipo_doc, titulo, metricas_anteriores=None):
    """Chama a API do Gemini via REST para extrair resumo, mudanças e alertas."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    modelo = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
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

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            candidate = res_json.get("candidates", [])[0]
            part_text = candidate.get("content", {}).get("parts", [])[0].get("text", "")
            return json.loads(part_text)
    except Exception as e:
        print(f"Erro Gemini API ({ticker}): {e}")
        return None


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY ausente: pulando resumos", flush=True)

    tickers = tickers_ativos_carteira()
    fiis = [t for t in tickers if t.endswith("11") and t in MAPA_CNPJ]
    acoes = [t for t in tickers if not t.endswith("11") or t in ["TAEE11"]]

    print(f"Fehmir Novidades · Verificando {len(tickers)} ativos ({len(acoes)} Ações, {len(fiis)} FIIs)...", flush=True)

    cache = carregar_cache()
    ids_existentes = set()
    for doc_list in cache.values():
        for d in doc_list:
            if "id" in d:
                ids_existentes.add(d["id"])

    # 1. Coleta de Documentos
    docs_novos_por_ticker = {t: [] for t in tickers}

    # Ações via CVM IPE
    print("Consultando CVM IPE para ações...", flush=True)
    docs_cvm = buscar_cvm_acoes(acoes, dias=45)
    for tk, dlist in docs_cvm.items():
        docs_novos_por_ticker[tk].extend(dlist)

    # FIIs via Fundos.NET
    print("Consultando Fundos.NET para FIIs...", flush=True)
    for f in fiis:
        cnpj = MAPA_CNPJ[f]
        dlist = buscar_fundosnet(f, cnpj, dias=45)
        docs_novos_por_ticker[f].extend(dlist)

    # 2. Processamento e Resumos
    novos_para_processar = []
    for tk in tickers:
        for doc in docs_novos_por_ticker[tk]:
            if doc["id"] not in ids_existentes:
                novos_para_processar.append((tk, doc))

    # Limite estrito de 12 documentos por execução
    novos_para_processar = novos_para_processar[:12]
    print(f"Documentos novos a processar nesta execução: {len(novos_para_processar)}", flush=True)

    for tk, doc in novos_para_processar:
        print(f" -> Processando {tk}: {doc['tipo']} - {doc['titulo'][:50]} ({doc['data']})", flush=True)

        resumo_data = None
        if api_key:
            pdf_bytes = baixar_pdf(doc["url"])
            if pdf_bytes:
                # Obter métricas do documento mais recente já salvo desse ativo
                ult_metricas = None
                if tk in cache and len(cache[tk]) > 0:
                    ult_metricas = cache[tk][0].get("metricas")
                resumo_data = resumir_com_gemini(pdf_bytes, tk, doc["tipo"], doc["titulo"], ult_metricas)
                time.sleep(2.5)  # Respeita o rate limit gratuito

        if not resumo_data:
            resumo_data = {
                "resumo": [f"{doc['tipo']} publicado em {doc['data']}."],
                "mudancas": [],
                "alertas": [],
                "metricas": {
                    "vacancia_fisica": None, "vacancia_financeira": None, "inadimplencia": None,
                    "provento_por_cota": None, "resultado_por_cota": None, "reserva_por_cota": None, "ltv": None
                },
                "gravidade": "info"
            }

        item_final = {
            "id": doc["id"],
            "data": doc["data"],
            "tipo": doc["tipo"],
            "titulo": doc["titulo"],
            "url": doc["url"],
            "resumo": resumo_data.get("resumo") or [],
            "mudancas": resumo_data.get("mudancas") or [],
            "alertas": resumo_data.get("alertas") or [],
            "metricas": resumo_data.get("metricas") or {},
            "gravidade": resumo_data.get("gravidade") or "info"
        }

        if tk not in cache:
            cache[tk] = []
        cache[tk].insert(0, item_final)

    # 3. Ordenação e corte (máximo 6 por ativo)
    total_docs = 0
    saida_limpa = {}
    for tk in sorted(cache.keys()):
        # Ordena por data decrescente
        sorted_docs = sorted(cache[tk], key=lambda x: x.get("data", ""), reverse=True)
        # Limita a 6 por ativo
        saida_limpa[tk] = sorted_docs[:6]
        total_docs += len(saida_limpa[tk])

    SAIDA.parent.mkdir(exist_ok=True)
    conteudo_js = (
        "/* Gerado por tools/novidades.py — não editar à mão. */\n"
        "window.FEHMIR_NOVIDADES = " + json.dumps(saida_limpa, ensure_ascii=False, indent=2) + ";\n"
    )
    SAIDA.write_text(conteudo_js, encoding="utf-8")
    print(f"OK: {total_docs} documentos em {SAIDA.relative_to(RAIZ)}.", flush=True)

    # Registro de contagem para o log
    print("\n--- CONTAGEM DE DOCUMENTOS ENCONTRADOS ---", flush=True)
    for t_alvo in ["RZTR11", "TRXF11", "BBAS3", "TAEE11"]:
        qtd = len(saida_limpa.get(t_alvo, []))
        print(f"{t_alvo}: {qtd} documentos", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
