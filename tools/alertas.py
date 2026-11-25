"""Avalia regras manuais/automáticas e envia alertas consolidados no Telegram."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DADOS = ROOT / "dados"
PAINEL_URL = "https://felipecosta-silva.github.io/painel-barsi/"
MAX_DIAS_PRECO = 3
CICLICO_RE = re.compile(r"commod|petr|miner|sider|papel|celul|constru|incorpor|varejo|consumo", re.IGNORECASE)


def br(num: float | int, casas: int = 2) -> str:
    txt = f"{float(num):,.{casas}f}"
    return txt.replace(",", "_").replace(".", ",").replace("_", ".")


def ler_js_json(caminho: Path, marcador: str, default=None):
    """Extrai objeto/array JSON atribuído a uma variável window.<marcador> = ...;"""
    if not caminho.exists():
        return default
    texto = caminho.read_text(encoding="utf-8")
    padrao = re.compile(rf"(?:window\.)?{re.escape(marcador)}\s*=\s*", re.MULTILINE)
    m = padrao.search(texto)
    if not m:
        return default
    sub = texto[m.end():].lstrip()
    try:
        dec = json.JSONDecoder()
        val, _ = dec.raw_decode(sub)
        return val
    except json.JSONDecodeError:
        return ler_objeto_js_flex(sub, default)


def ler_objeto_js_flex(trecho: str, default=None):
    """Fallback para arquivos JS com chaves sem aspas (ex.: dados/alertas_regras.js)."""
    # Isola até o ; de fechamento no nível raiz
    nivel = 0
    em_str = None
    esc = False
    fim = len(trecho)
    for idx, ch in enumerate(trecho):
        if esc:
            esc = False
            continue
        if ch == "\\" and em_str:
            esc = True
            continue
        if em_str:
            if ch == em_str:
                em_str = None
            continue
        if ch in ('"', "'"):
            em_str = ch
        elif ch in "{[":
            nivel += 1
        elif ch in "}]":
            nivel -= 1
            if nivel == 0:
                fim = idx + 1
                break
    bloco = trecho[:fim]
    # Remove comentários // fora de strings
    bloco = re.sub(r'(^|\s)//[^\n]*', '', bloco)
    # Adiciona aspas em chaves JS sem aspas fora de strings
    out = []
    i = 0
    n = len(bloco)
    em_str = None
    while i < n:
        ch = bloco[i]
        if em_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(bloco[i + 1])
                i += 2
                continue
            if ch == em_str:
                em_str = None
            i += 1
            continue
        if ch in ('"', "'"):
            em_str = ch
            out.append('"')
            i += 1
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (bloco[j].isalnum() or bloco[j] == "_"):
                j += 1
            ident = bloco[i:j]
            k = j
            while k < n and bloco[k] in " \t\r\n":
                k += 1
            if k < n and bloco[k] == ":":
                out.append(f'"{ident}"')
            else:
                out.append(ident)
            i = j
            continue
        out.append(ch)
        i += 1
    corrigido = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    return json.loads(corrigido)


def carregar_dados(dados_dir: Path = DADOS) -> dict:
    meta_merc = ler_js_json(dados_dir / "mercado.js", "FEHMIR_MERCADO_META", {}) or {}
    lista_merc = ler_js_json(dados_dir / "mercado.js", "FEHMIR_MERCADO", []) or []
    precos = {
        str(x.get("t", "")).upper(): float(x["p"])
        for x in lista_merc
        if isinstance(x, dict) and x.get("t") and isinstance(x.get("p"), (int, float)) and x["p"] > 0
    }
    tetos = ler_js_json(dados_dir / "tetos.js", "FEHMIR_TETOS", {}) or {}
    carteira = ler_js_json(dados_dir / "tetos.js", "FEHMIR_CARTEIRA", {}) or {}
    tesouro = ler_js_json(dados_dir / "tesouro.js", "FEHMIR_TESOURO", {}) or {}
    regras_obj = ler_js_json(dados_dir / "alertas_regras.js", "FEHMIR_ALERTAS_REGRAS", {}) or {}
    alertas_analista = ler_js_json(dados_dir / "alertas.js", "FEHMIR_ALERTAS", {}) or {}
    estado_path = dados_dir / "alertas_estado.json"
    estado = {"atualizado": None, "regras": {}}
    if estado_path.exists():
        try:
            estado = json.loads(estado_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            estado = {"atualizado": None, "regras": {}}
    return {
        "meta_mercado": meta_merc,
        "precos": precos,
        "tetos": tetos,
        "carteira": carteira,
        "tesouro": tesouro,
        "regras_manuais": regras_obj.get("regras") or [],
        "vigiar": {str(t).upper() for t in (regras_obj.get("vigiar") or [])},
        "silenciar": {str(k).upper(): v for k, v in (regras_obj.get("silenciar") or {}).items()},
        "alertas_analista": alertas_analista.get("itens") or [],
        "estado": estado,
    }


def _parse_data_iso(valor: str | None) -> dt.date | None:
    if not valor:
        return None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", str(valor))
    if not m:
        return None
    return dt.date.fromisoformat(m.group(1))


def _taxa_tesouro(tesouro: dict, ticker: str) -> dict | None:
    t_up = ticker.upper()
    for tit in tesouro.get("titulos") or []:
        if str(tit.get("ticker", "")).upper() == t_up:
            return tit
    return None


def _condicao_regra(regra: dict, dados: dict) -> tuple[bool, float | None, bool]:
    """Retorna (satisfeita, valor_atual, ainda_dentro_histerese)."""
    tipo = regra.get("tipo")
    cond = regra.get("condicao")
    alvo = float(regra["valor"])
    ticker = str(regra["ticker"]).upper()

    if tipo == "taxa":
        tit = _taxa_tesouro(dados["tesouro"], ticker)
        atual = float(tit["taxaCompra"]) if tit and isinstance(tit.get("taxaCompra"), (int, float)) and tit["taxaCompra"] > 0 else None
        if atual is None:
            return False, None, False
        if cond == ">=":
            return atual >= alvo, atual, atual >= (alvo - 0.05)
        return atual <= alvo, atual, atual <= (alvo + 0.05)

    atual = dados["precos"].get(ticker)
    if atual is None:
        return False, None, False
    if cond == "<=":
        return atual <= alvo, atual, atual <= alvo * 1.01
    if cond == ">=":
        return atual >= alvo, atual, atual >= alvo * 0.99
    return False, atual, False


def _formatar_linha(regra: dict, atual: float, dados: dict) -> str:
    tipo = regra.get("tipo")
    ticker = str(regra["ticker"]).upper()
    alvo = float(regra["valor"])
    nota = str(regra.get("texto") or "").strip()
    tt = dados["tetos"].get(ticker) or {}

    if tipo == "taxa":
        sufixo = f" · {nota}" if nota else ""
        return f"🏦 {ticker} a {br(atual)}% (≥ {br(alvo)}%){sufixo}"
    if tipo == "venda":
        teto = tt.get("teto")
        extra_teto = f" (teto R$ {br(teto)})" if teto else ""
        return f"🔴 {ticker} R$ {br(atual)} (≥ R$ {br(alvo)}){extra_teto}" + (f" · {nota}" if nota else "")

    teto = tt.get("teto")
    margem = ((1.0 - atual / float(teto)) * 100.0) if teto else None
    partes = [f"🟢 {ticker} R$ {br(atual)} (compra ≤ {br(alvo)})"]
    if margem is not None:
        partes.append(f"margem {br(margem, 1)}%")
    if nota:
        partes.append(nota)
    return " · ".join(partes)


def avaliar_alertas(dados: dict, hoje: dt.date | None = None) -> dict:
    hoje_d = hoje or dt.date.today()
    gerado_str = str((dados["meta_mercado"] or {}).get("gerado") or "")
    dt_merc = _parse_data_iso(gerado_str)
    idade_dias = (hoje_d - dt_merc).days if dt_merc else 999

    estado_ant = dados.get("estado") or {"atualizado": None, "regras": {}}
    regras_est = dict(estado_ant.get("regras") or {})

    if idade_dias > MAX_DIAS_PRECO:
        data_br = dt_merc.strftime("%d/%m/%Y") if dt_merc else "desconhecida"
        aviso_id = "sistema:precos_parados"
        novo_est = dict(regras_est)
        ja_avisou = bool((regras_est.get(aviso_id) or {}).get("ativo"))
        novo_est[aviso_id] = {
            "ativo": True,
            "valor": idade_dias,
            "desde": (regras_est.get(aviso_id) or {}).get("desde") or hoje_d.isoformat(),
            "ultimoEnvio": hoje_d.isoformat(),
        }
        msg_parado = (
            f"⚠️ Preços parados desde {data_br} ({idade_dias} dias sem atualizar): "
            "alertas de compra/venda suspensos até o robô voltar."
        )
        return {
            "bloqueado_preco_velho": True,
            "data_mercado": gerado_str or "sem data",
            "novos": [] if ja_avisou else [{"id": aviso_id, "texto": msg_parado}],
            "mensagem": None if ja_avisou else f"{msg_parado}\n\n🔗 {PAINEL_URL}",
            "aviso_preco_parado": msg_parado,
            "estado_novo": {"atualizado": hoje_d.isoformat(), "regras": novo_est},
        }

    # Preços atualizados -> limpa eventual estado de preços parados
    if "sistema:precos_parados" in regras_est:
        regras_est["sistema:precos_parados"] = {
            **regras_est["sistema:precos_parados"],
            "ativo": False,
        }

    candidatas: list[dict] = []
    manuais_compra: set[str] = set()
    vendas_emitidas: set[str] = set()

    for r in dados["regras_manuais"]:
        tk = str(r.get("ticker", "")).upper()
        if r.get("tipo") == "compra":
            manuais_compra.add(tk)
        candidatas.append(r)

    # Regra automática de compra: só carteira + lista "vigiar" (revisão 32-B: o radar inteiro dava 52 alertas),
    # menos a lista "silenciar" (decisão registrada no dossiê), sem duplicar regra manual.
    silenciar = dados.get("silenciar") or {}
    vigiar = dados.get("vigiar") or set()
    for tk, tt in sorted(dados["tetos"].items()):
        t_up = tk.upper()
        compra = tt.get("compra")
        if t_up in manuais_compra or not isinstance(compra, (int, float)) or compra <= 0:
            continue
        em_cart = (dados["carteira"].get(t_up) or 0) > 0
        if not (em_cart or t_up in vigiar):
            continue
        if t_up in silenciar or f"{t_up}:COMPRA" in silenciar:
            continue
        eh_fii = str(tt.get("setor") or "").upper().startswith("FII")
        candidatas.append({
            "id": f"auto:{t_up}:compra",
            "ticker": t_up,
            "tipo": "compra",
            "condicao": "<=",
            "valor": float(compra),
            "texto": ("em carteira" if em_cart else "vigiado") + " · abaixo da compra"
                     + (" · FII sem prioridade (classe acima da meta)" if eh_fii else ""),
            "fonte": "automática (tetos.js)",
        })

    # Regra automática de venda: cíclica em carteira com p >= teto * 1.2
    for tk, qtd in sorted(dados["carteira"].items()):
        t_up = tk.upper()
        if not isinstance(qtd, (int, float)) or qtd <= 0:
            continue
        tt = dados["tetos"].get(t_up)
        if not tt or not isinstance(tt.get("teto"), (int, float)) or tt["teto"] <= 0:
            continue
        setor = str(tt.get("setor") or "")
        if not CICLICO_RE.search(setor):
            continue
        if t_up in silenciar or f"{t_up}:VENDA" in silenciar:
            continue
        gatilho = round(float(tt["teto"]) * 1.2, 2)
        vendas_emitidas.add(t_up)
        candidatas.append({
            "id": f"auto:{t_up}:venda",
            "ticker": t_up,
            "tipo": "venda",
            "condicao": ">=",
            "valor": gatilho,
            "texto": "cíclica ≥ teto × 1,2 (realizar em escada)",
            "fonte": "automática (tetos.js)",
        })

    novos: list[dict] = []
    novo_est = dict(regras_est)

    for r in candidatas:
        rid = str(r["id"])
        ant = regras_est.get(rid) or {}
        estava_ativo = bool(ant.get("ativo"))
        satisfeita, atual, dentro_hist = _condicao_regra(r, dados)

        if atual is None:
            continue

        if estava_ativo:
            if dentro_hist:
                novo_est[rid] = {**ant, "ativo": True, "valor": atual}
            else:
                novo_est[rid] = {**ant, "ativo": False, "valor": atual, "saiu": hoje_d.isoformat()}
        else:
            if satisfeita:
                linha = _formatar_linha(r, atual, dados)
                novos.append({"id": rid, "ticker": r["ticker"], "tipo": r["tipo"], "texto": linha})
                novo_est[rid] = {
                    "ativo": True,
                    "valor": atual,
                    "desde": hoje_d.isoformat(),
                    "ultimoEnvio": hoje_d.isoformat(),
                }
            elif rid in novo_est:
                novo_est[rid] = {**ant, "ativo": False, "valor": atual}

    # Bônus da revisão 32: alertas ativos novos do analista (realização, provento/lucro fora da faixa)
    ativos_analista_ids = set()
    for it in dados["alertas_analista"]:
        if not isinstance(it, dict) or it.get("estado") != "ativo":
            continue
        tipo_it = it.get("tipo")
        # Revisão 32-B: "zona de realização" do analista fica só no painel (B.A.S.E. não se vende por preço;
        # cíclica já tem a regra própria acima). Provento/fundamento só de ativo em carteira ou vigiado.
        if tipo_it not in ("provento", "fundamento"):
            continue
        tk = str(it.get("ticker", "")).upper()
        if not ((dados["carteira"].get(tk) or 0) > 0 or tk in (dados.get("vigiar") or set())):
            continue
        if tipo_it == "zona_realizacao" and tk in vendas_emitidas:
            continue
        rid = f"analista:{it.get('id') or (tk + ':' + str(tipo_it))}"
        ativos_analista_ids.add(rid)
        ant = regras_est.get(rid) or {}
        if not ant.get("ativo"):
            icone = "🔔" if tipo_it != "zona_realizacao" else "🟠"
            novos.append({"id": rid, "ticker": tk, "tipo": tipo_it, "texto": f"{icone} {it.get('texto')}"})
            novo_est[rid] = {"ativo": True, "desde": hoje_d.isoformat(), "ultimoEnvio": hoje_d.isoformat()}

    for rid, val in list(novo_est.items()):
        if rid.startswith("analista:") and val.get("ativo") and rid not in ativos_analista_ids:
            novo_est[rid] = {**val, "ativo": False, "saiu": hoje_d.isoformat()}

    mensagem = None
    if novos:
        data_ref = dt_merc.strftime("%d/%m/%Y") if dt_merc else gerado_str
        cabecalho = f"📊 Painel Barsi · Alertas ({len(novos)}) · preços de {data_ref}"
        rodape = f"🔗 {PAINEL_URL}"
        linhas_corpo = []
        usado = len(cabecalho) + len(rodape) + 6
        ocultos = 0
        for x in novos:
            ln = x["texto"]
            if usado + len(ln) + 1 <= 3850:
                linhas_corpo.append(ln)
                usado += len(ln) + 1
            else:
                ocultos += 1
        if ocultos:
            linhas_corpo.append(f"… e +{ocultos} alerta(s) no painel.")
        corpo = "\n".join(linhas_corpo)
        mensagem = f"{cabecalho}\n\n{corpo}\n\n{rodape}"

    return {
        "bloqueado_preco_velho": False,
        "data_mercado": gerado_str,
        "novos": novos,
        "mensagem": mensagem,
        "estado_novo": {"atualizado": hoje_d.isoformat(), "regras": novo_est},
    }


def enviar_telegram(token: str, chat_id: str, texto: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": texto,
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if not res.get("ok"):
        raise RuntimeError(f"Falha ao enviar Telegram: {res}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verifica alertas do Painel Barsi e envia no Telegram.")
    ap.add_argument("--simular", action="store_true", help="Imprime a mensagem na tela sem enviar nem salvar estado.")
    args = ap.parse_args(argv)

    dados = carregar_dados(DADOS)
    res = avaliar_alertas(dados)

    if args.simular:
        if res["mensagem"]:
            print(res["mensagem"])
        else:
            print(f"Nenhum alerta novo hoje (base de preços: {res['data_mercado']}).")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[aviso] TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID ausentes no ambiente; passo encerrado sem falhar.")
        return 0

    if res["mensagem"]:
        try:
            enviar_telegram(token, chat_id, res["mensagem"])
            print(f"OK: {len(res['novos'])} alerta(s) enviado(s) ao Telegram.")
        except urllib.error.HTTPError as exc:
            corpo = exc.read().decode("utf-8", "replace")[:300]
            dica = {401: "TELEGRAM_BOT_TOKEN inválido (chave errada ou de outro bot)",
                    400: "TELEGRAM_CHAT_ID errado ou você ainda não mandou 'oi' a este bot",
                    403: "o bot foi bloqueado no Telegram"}.get(exc.code, "")
            print(f"[erro] Telegram HTTP {exc.code}: {corpo} {('→ ' + dica) if dica else ''}", file=sys.stderr)
            return 1
        except (urllib.error.URLError, RuntimeError) as exc:
            print(f"[erro] Envio ao Telegram falhou: {exc}", file=sys.stderr)
            return 1
    else:
        print(f"OK: nenhum alerta novo para enviar (base {res['data_mercado']}).")

    (DADOS / "alertas_estado.json").write_text(
        json.dumps(res["estado_novo"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
