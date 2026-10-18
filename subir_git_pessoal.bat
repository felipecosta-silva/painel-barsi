@echo off
chcp 65001 > nul
echo ======================================================================
echo    PUBLICANDO NO SEU GITHUB PESSOAL: felipecosta-silva/painel-barsi
echo    (Configurado com seguranca: NAO AFETA O GIT DA TASCOM)
echo ======================================================================
echo.

cd /d "c:\Users\tasco\OneDrive\Documentos\Agente financeiro"

:: 1. Inicializa o repositório se ainda não existir
if not exist ".git" (
    echo [*] Inicializando repositorio Git local...
    git init
)

:: 1b. Trava anti-vazamento: instala o hook de pre-commit (bloqueia commit com chave/token gravado)
if exist "tools\pre-commit" copy /Y "tools\pre-commit" ".git\hooks\pre-commit" >nul

:: 1d. Remote pessoal e sincronizacao: o robo do GitHub Actions grava dados todo dia util,
::     entao baixa esses commits ANTES de mexer em qualquer arquivo (senao o push e recusado)
git remote remove origin >nul 2>&1
git remote add origin https://github.com/felipecosta-silva/painel-barsi.git
git branch -M main
echo [*] Baixando atualizacoes do GitHub (dados do robo)...
git pull --rebase --autostash origin main
if errorlevel 1 (
    echo.
    echo [CANCELADO] Nao consegui sincronizar com o GitHub. Peca ajuda ao Claude antes de publicar.
    pause
    exit /b 1
)

:: 1a. Atualiza o histórico gratuito (Yahoo) antes de publicar — se falhar, segue com o arquivo anterior
python tools\atualizar_historico.py
python tools\benchmarks.py

:: 1c. Verifica segredos ANTES de publicar (cancela se achar chave/token nos arquivos)
python tools\checar_segredos.py
if errorlevel 1 (
    echo.
    echo [CANCELADO] Remova a chave/token indicado acima e rode de novo. Nada foi publicado.
    pause
    exit /b 1
)

:: 2. Configura autor PESSOAL apenas localmente no projeto
git config user.name "Felipe Costa"
git config user.email "felipecosta-silva@users.noreply.github.com"

echo [*] Autor local configurado: Felipe Costa ^<felipecosta-silva@users.noreply.github.com^>
echo [*] Adicionando arquivos atualizados do Painel...

git add index.html painel-barsi.html README.md .gitignore simulador-renda-passiva.html subir_git_pessoal.bat tools/checar_segredos.py tools/pre-commit tools/atualizar_historico.py tools/benchmarks.py tools/varrer_mercado.py tools/novidades.py tools/pareceres.py tools/fundamentos.py dados/historico.js dados/benchmarks.js dados/mercado.js dados/novidades.js dados/pareceres.js dados/licoes_candidatas.js dados/fundamentos.js .github/workflows/historico.yml .github/workflows/novidades.yml .github/workflows/pareceres.yml .github/workflows/fundamentos.yml
git commit -m "chore: atualizacao do painel e dados (%date%)"

echo.
echo [*] Enviando arquivos para https://github.com/felipecosta-silva/painel-barsi.git...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ======================================================================
    echo   [SUCESSO] Seu Painel Barsi foi publicado no seu GitHub pessoal!
    echo   
    echo   Para ativar a pagina na Web (GitHub Pages):
    echo   1. Acesse: https://github.com/felipecosta-silva/painel-barsi/settings/pages
    echo   2. Em 'Build and deployment' -> 'Branch', escolha 'main' e '/ (root)'
    echo   3. Clique em 'Save'
    echo   4. Em instantes, seu link publico estara no ar em:
    echo      https://felipecosta-silva.github.io/painel-barsi/
    echo ======================================================================
) else (
    echo.
    echo [AVISO] Se pediu login/token, autentique com sua conta felipecosta-silva.
)

echo.
pause

