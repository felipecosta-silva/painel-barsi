"""Trava anti-vazamento: procura chaves/tokens gravados nos arquivos antes de publicar.
Uso: python tools/checar_segredos.py [arquivos...]   (sem argumentos = arquivos publicados pelo subir_git_pessoal.bat)
Sai com código 1 (e bloqueia a publicação) se achar algo suspeito.
Nunca grave chave no código: o token da Brapi fica só no navegador (botão 🔑 Token do painel)."""
import re, sys, pathlib
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PUBLICADOS = ["index.html", "painel-barsi.html", "README.md", ".gitignore", "Barsi_Bot_Metodologia.md",
              "simulador-renda-passiva.html", "subir_git_pessoal.bat", "HANDOFF_IA.md"]
PADROES = [
    # atribuição de string longa a algo com nome de segredo: token = "abc...", apiKey: 'xyz...'
    re.compile(r"""(?i)(token|api[_-]?key|apikey|secret|senha|password|bearer)['"]?\s*[:=]\s*['"][A-Za-z0-9_\-\.]{16,}['"]"""),
    # token na URL: ?token=abc..., &apikey=...
    re.compile(r"""(?i)[?&](token|api[_-]?key|apikey|key)=[A-Za-z0-9_\-]{12,}"""),
    # cabeçalho com valor fixo: Bearer abc123...
    re.compile(r"""Bearer\s+[A-Za-z0-9_\-\.]{16,}"""),
    # chaves privadas e chaves conhecidas
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),           # AWS
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),  # GitHub
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),      # OpenAI/Anthropic e similares
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),     # Google
]

def checar(caminhos):
    achados = []
    for c in caminhos:
        p = pathlib.Path(c)
        if not p.is_file():
            continue
        try:
            linhas = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for n, linha in enumerate(linhas, 1):
            for rx in PADROES:
                m = rx.search(linha)
                if m:
                    trecho = m.group(0)
                    achados.append(f"{c}:{n}: {trecho[:12]}…  (padrão suspeito)")
    return achados

if __name__ == "__main__":
    alvos = sys.argv[1:] or PUBLICADOS
    achados = checar(alvos)
    if achados:
        print("\n[BLOQUEADO] Possível chave/segredo encontrado. Remova antes de publicar:\n")
        for a in achados:
            print("  - " + a)
        print("\nSe for falso positivo, ajuste o trecho (ex.: não deixe valores longos em variáveis chamadas token/apiKey).")
        sys.exit(1)
    print("[OK] Nenhum segredo encontrado nos arquivos verificados.")
