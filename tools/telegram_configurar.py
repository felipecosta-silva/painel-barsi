"""Configuração única dos segredos do Telegram no GitHub Actions.

Uso:
1) Mande um oi para o bot no Telegram;
2) python tools/telegram_configurar.py
"""
from __future__ import annotations

import getpass
import json
import subprocess
import sys
import urllib.error
import urllib.request


def tg_chamar(token: str, metodo: str, payload: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{metodo}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if not res.get("ok"):
        raise RuntimeError(f"Telegram API {metodo} falhou: {res}")
    return res.get("result")


def gravar_segredo_gh(nome: str, valor: str) -> None:
    """Grava segredo via GitHub CLI passando o valor pela entrada padrão (nunca por argumento)."""
    subprocess.run(
        ["gh", "secret", "set", nome],
        input=valor,
        text=True,
        check=True,
    )


def extrair_chats(updates: list[dict]) -> dict[int, str]:
    chats: dict[int, str] = {}
    for up in updates or []:
        msg = up.get("message") or up.get("edited_message") or up.get("channel_post") or {}
        chat = msg.get("chat") or {}
        cid = chat.get("id")
        if cid is None:
            continue
        nome = " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")])) or chat.get("title") or chat.get("username") or str(cid)
        if chat.get("username"):
            nome = f"{nome} (@{chat['username']})"
        chats[int(cid)] = nome
    return chats


def main() -> int:
    print("Uso prévio: certifique-se de ter mandado um 'oi' para o bot no Telegram.")
    token = getpass.getpass("Token do bot no Telegram (não aparece na tela): ").strip()
    if not token:
        print("Token vazio. Cancelado.")
        return 1

    try:
        eu = tg_chamar(token, "getMe") or {}
        print(f"\nChave aceita: é do bot \"{eu.get('first_name')}\" (@{eu.get('username')}).")
        print("Se não for o bot em que você mandou o 'oi', feche (Ctrl+C) e pegue a chave certa no BotFather (/mybots → bot → API Token).")
        wh = tg_chamar(token, "getWebhookInfo")
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"Erro ao consultar o bot no Telegram: {exc}")
        return 1

    if wh and wh.get("url"):
        print(f"\n[aviso] O bot possui um webhook ativo ({wh['url']}). Sem removê-lo, getUpdates falha.")
        resp = input("Deseja remover o webhook agora (deleteWebhook)? [s/N]: ").strip().lower()
        if resp not in ("s", "sim", "y", "yes"):
            print("Cancelado. Remova o webhook antes de continuar.")
            return 1
        tg_chamar(token, "deleteWebhook", {"drop_pending_updates": False})
        print("Webhook removido com sucesso.")

    updates = tg_chamar(token, "getUpdates")
    chats = extrair_chats(updates)
    if not chats:
        print("\nNenhuma mensagem encontrada no getUpdates.")
        print("Mande outra mensagem ao bot no Telegram e rode este script de novo.")
        return 1

    print("\nChats encontrados:")
    lista = list(chats.items())
    for idx, (cid, nome) in enumerate(lista, 1):
        print(f"  {idx}) {nome} -> chat_id: {cid}")

    if len(lista) == 1:
        chat_id, nome_sel = lista[0]
    else:
        escolha = input(f"Escolha o número do chat (1-{len(lista)}): ").strip()
        if not escolha.isdigit() or not (1 <= int(escolha) <= len(lista)):
            print("Escolha inválida. Cancelado.")
            return 1
        chat_id, nome_sel = lista[int(escolha) - 1]

    conf = input(f"\nConfirmar gravação dos segredos TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID ({chat_id} · {nome_sel}) via `gh secret set`? [s/N]: ").strip().lower()
    if conf not in ("s", "sim", "y", "yes"):
        print("Cancelado sem alterar segredos.")
        return 0

    try:
        gravar_segredo_gh("TELEGRAM_BOT_TOKEN", token)
        gravar_segredo_gh("TELEGRAM_CHAT_ID", str(chat_id))
    except FileNotFoundError:
        # Sem GitHub CLI: testa o bot e ensina o cadastro pelo site (o token nunca é impresso).
        tg_chamar(token, "sendMessage", {"chat_id": str(chat_id), "text": "✅ Bot conectado. Falta cadastrar os segredos no GitHub."})
        print()
        print("`gh` (GitHub CLI) não está instalado. Cadastre os 2 segredos pelo site:")
        print("  1) Abra https://github.com/felipecosta-silva/painel-barsi/settings/secrets/actions/new")
        print("  2) Name: TELEGRAM_BOT_TOKEN  · Secret: o token que o BotFather mostrou (/mybots → Barsi Bot → API Token)")
        print(f"  3) De novo em 'New repository secret': Name: TELEGRAM_CHAT_ID · Secret: {chat_id}")
        print("  4) Em Actions → 'Alertas Telegram' → 'Run workflow' para testar.")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"Erro ao executar `gh secret set`: código {exc.returncode}")
        return 1

    tg_chamar(token, "sendMessage", {"chat_id": str(chat_id), "text": "✅ Alertas do Painel Barsi ligados"})
    print("Pronto! Segredos salvos no GitHub e mensagem de teste enviada no Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
