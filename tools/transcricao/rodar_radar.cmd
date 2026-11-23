@echo off
rem Rodada diária do radar de vídeos (agendada no Windows: "Painel - radar de videos"). Log em %LOCALAPPDATA%\painel-transcricao\radar.log
chcp 65001 >nul
cd /d "%~dp0..\.."
echo ==== %date% %time% >> "%LOCALAPPDATA%\painel-transcricao\radar.log"
"%LOCALAPPDATA%\painel-transcricao\venv\Scripts\python.exe" -X utf8 tools\transcricao\videos.py radar >> "%LOCALAPPDATA%\painel-transcricao\radar.log" 2>&1
for /f %%d in ('powershell -NoProfile -Command "[int](Get-Date).DayOfWeek"') do if "%%d"=="1" "%LOCALAPPDATA%\painel-transcricao\venv\Scripts\python.exe" -X utf8 tools\transcricao\videos.py buscar-ativos --dias 7 --por-ativo 2 >> "%LOCALAPPDATA%\painel-transcricao\radar.log" 2>&1
