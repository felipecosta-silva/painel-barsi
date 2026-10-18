"""Fehmir · Robô Semanal de Pareceres (Análise Fundamentalista via Gemini API).

Aplica semanalmente o roteiro de análise aos documentos recentes dos ativos da carteira,
utilizando a cota gratuita do Gemini, e mantém o ciclo de aprendizado de lições.

Saídas:
- dados/pareceres.js
- dados/licoes_candidatas.js
"""
import os
import sys
import re
import json
import datetime
import pathlib

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

# Importar rotinas oficiais do robô de novidades (sem duplicar lógica de API/retentativas)
try:
    from novidades import chamar_gemini_api, tickers_ativos_carteira, descobrir_modelo_flash
except ImportError:
    from tools.novidades import chamar_gemini_api, tickers_ativos_carteira, descobrir_modelo_flash

NOVIDADES_PATH = RAIZ / "dados" / "novidades.js"
HISTORICO_PATH = RAIZ / "dados" / "historico.js"
PARECERES_PATH = RAIZ / "dados" / "pareceres.js"
LICOES_PATH = RAIZ / "dados" / "licoes_candidatas.js"

SCHEMA_PARECER = {
    "type": "OBJECT",
    "properties": {
        "fatos": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Fatos relevantes extraídos estritamente dos documentos oficiais"
        },
        "atribuicao": {
            "type": "STRING",
            "description": "ativo | fluxo | macro (qual domina e por quê)"
        },
        "risco": {
            "type": "STRING",
            "enum": ["idiossincratico", "estrutural"],
            "description": "Classificação do risco principal"
        },
        "risco_motivo": {
            "type": "STRING",
            "description": "Explicação objetiva do risco"
        },
        "caixa_vs_contabil": {
            "type": "STRING",
            "description": "Diferença entre impacto no caixa real vs. impacto contábil/anunciado"
        },
        "gatilhos": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Condições objetivas para mudar de ideia sobre a tese"
        },
        "parecer": {
            "type": "STRING",
            "enum": ["manter", "atencao", "reavaliar_tese"],
            "description": "Parecer objetivo sobre a manutenção da tese"
        },
        "confianca": {
            "type": "STRING",
            "enum": ["baixa", "media", "alta"],
            "description": "Grau de confiança da IA na análise com base nas informações"
        },
        "licao_generica": {
            "type": "STRING",
            "description": "1 regra de análise aprendida de forma geral, sem citar a carteira pessoal (ou null se nenhuma)"
        }
    },
    "required": [
        "fatos", "atribuicao", "risco", "risco_motivo", "caixa_vs_contabil",
        "gatilhos", "parecer", "confianca", "licao_generica"
    ]
}


def carregar_js_objeto(caminho, nome_var):
    """Lê um arquivo JS contendo window.VAR = { ... } ou [ ... ]."""
    if not caminho.exists():
        return {} if "{" in nome_var else []
    txt = caminho.read_text(encoding="utf-8", errors="ignore")
    m = re.search(rf'window\.{nome_var}\s*=\s*([\[\{{].*?[\]\}}]);', txt, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception as e:
            print(f"Erro ao parsear {caminho.name}: {e}")
    return {} if "{" in nome_var else []


def salvar_js_objeto(caminho, nome_var, obj, header="/* Gerado por tools/pareceres.py — não editar à mão. */"):
    """Grava objeto Python em formato JS window.VAR = ..."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = f"{header}\nwindow.{nome_var} = {json.dumps(obj, indent=2, ensure_ascii=False)};\n"
    caminho.write_text(conteudo, encoding="utf-8")


def carregar_dados_mercado():
    """Obtém preço atual e DY dos ativos de historico.js."""
    dados_hist = carregar_js_objeto(HISTORICO_PATH, "FEHMIR_HIST")
    res = {}
    if isinstance(dados_hist, dict):
        for t, d in dados_hist.items():
            precos = d.get("c", [])
            preco = precos[-1] if precos else None
            dpa12 = d.get("dpa12")
            dy = (dpa12 / preco * 100) if (preco and dpa12 and preco > 0) else None
            res[t] = {
                "preco": preco,
                "dy": dy,
                "dpa12": dpa12
            }
    return res


def similaridade_licoes(t1, t2):
    """Calcula similaridade de Jaccard entre palavras significativas de duas lições."""
    def tokens(s):
        palavras = re.findall(r'\b[a-zà-ÿ]{4,}\b', s.lower())
        stop = {"para", "como", "mais", "esse", "essa", "esta", "está", "isso", "pela", "pelo", "quando", "onde"}
        return set(p for p in palavras if p not in stop)
    s1, s2 = tokens(t1), tokens(t2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def main():
    print("=== Fehmir · Robô Semanal de Pareceres (Gemini) ===")
    api_key = os.environ.get("GEMINI_API_KEY")

    tickers_carteira = tickers_ativos_carteira()
    novidades = carregar_js_objeto(NOVIDADES_PATH, "FEHMIR_NOVIDADES")
    historico = carregar_dados_mercado()
    pareceres = carregar_js_objeto(PARECERES_PATH, "FEHMIR_PARECERES")
    if not isinstance(pareceres, dict):
        pareceres = {}
    licoes = carregar_js_objeto(LICOES_PATH, "FEHMIR_LICOES")
    if not isinstance(licoes, list):
        licoes = []

    # Identificar ativos com novos documentos para parecer
    elegiveis = []
    for tk in tickers_carteira:
        docs = novidades.get(tk, [])
        # Filtrar documentos que possuam informações analíticas
        docs_validos = [d for d in docs if (d.get("resumido_ia") is True or (d.get("resumo") and len(d.get("resumo")) > 1) or d.get("alertas"))]
        if not docs_validos:
            continue

        ultimo_p = pareceres.get(tk)
        dt_ultimo_p = ultimo_p.get("data") if ultimo_p else "1970-01-01"

        # Verifica se há novos documentos após o parecer existente
        docs_novos = [d for d in docs_validos if (d.get("data") or "") >= dt_ultimo_p]
        tem_critico = any(d.get("gravidade") == "critico" for d in docs_novos)
        tem_atencao = any(d.get("gravidade") == "atencao" for d in docs_novos)

        # Se nunca teve parecer ou se há novos documentos
        if not ultimo_p or docs_novos:
            peso_gravidade = 3 if tem_critico else (2 if tem_atencao else 1)
            elegiveis.append({
                "ticker": tk,
                "docs": docs_validos[:5],  # até 5 documentos mais recentes
                "novos": docs_novos,
                "prioridade": peso_gravidade,
                "sem_parecer": ultimo_p is None
            })

    # Ordenar elegíveis: prioridade de gravidade primeiro, depois quem nunca teve parecer
    elegiveis.sort(key=lambda x: (x["prioridade"], x["sem_parecer"]), reverse=True)
    lote = elegiveis[:10]

    print(f"Ativos na carteira: {len(tickers_carteira)}")
    print(f"Ativos elegíveis para emissão de parecer: {len(elegiveis)}")
    if lote:
        print("Ativos selecionados para este lote (máx 10):", ", ".join(x["ticker"] for x in lote))
    else:
        print("Nenhum ativo necessita de novo parecer nesta execução.")

    if not api_key:
        print("GEMINI_API_KEY ausente: nenhum parecer gerado.")
        print(f"Resumo do lote pendente: {len(lote)} ativos aguardando execução com chave.")
        return 0

    # Lições já aprendidas consolidadas e aprovadas (até 15)
    licoes_para_prompt = [
        lic.get("texto") for lic in licoes
        if lic.get("status") in ("consolidada", "aprovada") and lic.get("status") != "descartada"
    ][:15]

    hoje_iso = datetime.date.today().isoformat()
    pareceres_gerados = 0

    for item in lote:
        tk = item["ticker"]
        docs = item["docs"]
        h_info = historico.get(tk, {})
        preco_str = f"R$ {h_info['preco']:.2f}" if h_info.get("preco") else "não disponível"
        dy_str = f"{h_info['dy']:.1f}%" if h_info.get("dy") else "não disponível"

        prompt_context = f"ATIVO: {tk}\nCotação recente: {preco_str} · DY 12m: {dy_str}\n\nDOCUMENTOS RECENTES DA COMPANHIA/FUNDO:\n"
        fontes_ids = []
        for i, d in enumerate(docs, 1):
            fontes_ids.append(d.get("id") or f"doc_{i}")
            prompt_context += (
                f"\n--- Documento {i}: {d.get('tipo', 'Fato')} ({d.get('data', 'data não informada')}) ---\n"
                f"Título: {d.get('titulo', '')}\n"
                f"Gravidade atribuída no catálogo: {d.get('gravidade', 'info')}\n"
                f"Resumo: {' · '.join(d.get('resumo', []))}\n"
                f"O que mudou: {' · '.join(d.get('mudancas', []))}\n"
                f"Alertas/Riscos: {' · '.join(d.get('alertas', []))}\n"
            )
            met = d.get("metricas") or {}
            met_str = ", ".join(f"{k}: {v}" for k, v in met.items() if v is not None)
            if met_str:
                prompt_context += f"Métricas operacionais reportadas: {met_str}\n"

        if licoes_para_prompt:
            prompt_context += "\nREGRAS DE ANÁLISE JÁ CONSOLIDADAS PELO ROBÔ:\n"
            for lic in licoes_para_prompt:
                prompt_context += f"- {lic}\n"

        instrucoes = (
            "Você é o robô de análise de teses fundamentalistas do método Barsi/renda passiva.\n"
            "Analise os fatos dos documentos acima com extremo rigor analítico.\n\n"
            "Diretrizes obrigatórias:\n"
            "1. Responda em português brasileiro estritamente no formato JSON definido.\n"
            "2. Não recomende compra ou venda (a decisão de aporte é do investidor e segue a regra de preço-teto).\n"
            "3. Baseie-se apenas em fatos objetivos dos documentos; se algo não estiver comprovado, registre a dúvida.\n"
            "4. Defina o parecer da tese:\n"
            "   - 'manter': fundamentos íntegros, eventos normais de rotina ou volatilidade pontual de mercado.\n"
            "   - 'atencao': sinal de alerta relevante que exige acompanhamento nos próximos relatórios (ex.: vacância subindo, alavancagem alta).\n"
            "   - 'reavaliar_tese': risco estrutural à tese original (litígio judicial grave, perda permanente de receita, calote devedor, mudança prejudicial de contrato).\n"
            "5. 'licao_generica': sintetize 1 lição ou regra de ouro aprendida com este caso (máx 150 caracteres), de forma genérica para aplicar em outros ativos, sem citar a carteira pessoal nem tickers específicos. Se não houver nada novo a aprender, use null.\n"
        )

        payload_contents = [
            {
                "parts": [
                    {"text": instrucoes},
                    {"text": prompt_context}
                ]
            }
        ]
        gen_config = {
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA_PARECER
        }

        print(f"Gerando parecer para {tk}...", flush=True)
        res_parecer = chamar_gemini_api(payload_contents, gen_config, context_label=f"Parecer-{tk}")
        if not res_parecer:
            print(f"Não foi possível obter parecer para {tk} nesta rodada.")
            continue

        res_parecer["data"] = hoje_iso
        res_parecer["fontes"] = fontes_ids
        pareceres[tk] = res_parecer
        pareceres_gerados += 1
        print(f"-> Parecer emitido para {tk}: {res_parecer.get('parecer')} (Risco: {res_parecer.get('risco')})")

        # Processar lição genérica se houver
        lic_txt = res_parecer.get("licao_generica")
        if lic_txt and isinstance(lic_txt, str) and lic_txt.strip() and lic_txt.strip().lower() != "null":
            lic_txt = lic_txt.strip()
            # Procurar lição existente similar
            match_encontrado = None
            for ex in licoes:
                if ex.get("status") == "descartada":
                    continue
                if similaridade_licoes(lic_txt, ex.get("texto", "")) >= 0.45:
                    match_encontrado = ex
                    break

            if match_encontrado:
                match_encontrado["contagem"] = match_encontrado.get("contagem", 1) + 1
                if match_encontrado.get("contagem", 1) >= 2 and match_encontrado.get("status") == "candidata":
                    match_encontrado["status"] = "consolidada"
                    print(f"  [Lição promovida a consolidada]: {match_encontrado['texto']}")
            else:
                licoes.append({
                    "texto": lic_txt,
                    "ticker": tk,
                    "data": hoje_iso,
                    "contagem": 1,
                    "status": "candidata"
                })
                print(f"  [Nova lição candidata]: {lic_txt}")

    # Salvar resultados
    salvar_js_objeto(PARECERES_PATH, "FEHMIR_PARECERES", pareceres)
    salvar_js_objeto(LICOES_PATH, "FEHMIR_LICOES", licoes)
    print(f"Sucesso: {pareceres_gerados} pareceres atualizados em {PARECERES_PATH.name}.")
    print(f"Base de lições atualizada: {len(licoes)} lições registradas em {LICOES_PATH.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
