# Transcrição de vídeos (inclusive de membros)

Conteúdo de terceiros, para uso pessoal de estudo. **As transcrições ficam em `estudos/transcricoes/` (fora do Git) e nunca são publicadas.**

## Como funciona
1. **Radar diário** (tarefa do Windows "Painel - radar de videos", 06:00; se o PC estiver desligado, roda quando ligar):
   - lista os vídeos novos dos canais de `canais.json`;
   - transcreve os exclusivos de membros (todos) e os públicos que citam ticker da carteira ou do radar.
2. **Transcrição:** usa a legenda do YouTube em português, que fica pronta em segundos. Se não houver, baixa só o áudio e roda o Whisper (`large-v3-turbo`) no PC, ~1/3 da duração do vídeo.
3. **Saída:**
   - `estudos/transcricoes/AAAA-MM-DD-canal-titulo.md`, com marcação de tempo a cada ~45 s;
   - linha nova em `estudos/transcricoes/FILA.md`;
   - registro em `_processados.json`, para nada se repetir.
4. **Análise:** diga ao Claude "analise a fila de vídeos". Ele lê as transcrições, atualiza os dossiês e marca [x] na fila.

## Comandos
```
python tools/transcricao/videos.py transcrever <link>         # um vídeo qualquer (público ou de membros)
python tools/transcricao/videos.py transcrever <link> --whisper  # ignora a legenda do YouTube
python tools/transcricao/videos.py radar --listar                # o que o radar pegaria, sem baixar
python tools/transcricao/videos.py radar                         # a rodada completa, na hora
node tools/transcricao/cookies_youtube.js --login                # refazer o login do Chrome do robô
```

## Onde fica cada coisa (fora do OneDrive e do Git)
- `%LOCALAPPDATA%\painel-transcricao\` contém:
  - `venv\`: Python 3.12 com faster-whisper e yt-dlp;
  - `chrome-perfil\`: Chrome do robô, logado no YouTube;
  - `cookies.txt`: **dá acesso à conta, não copiar**;
  - `audio\`: temporário;
  - `radar.log`.
- Modelo do Whisper: `%USERPROFILE%\.cache\huggingface\` (~1,6 GB).

## Se algo falhar
- **"perfil do robô não está logado":** rode o `--login`, entre no YouTube e feche a janela.
- **Erro de download do YouTube:** atualize o yt-dlp com `python -m uv pip install --python "%LOCALAPPDATA%\painel-transcricao\venv\Scripts\python.exe" -U "yt-dlp[default]"`.
- **Novo canal:** acrescente em `canais.json` (o `id` começa com UC; veja com `yt-dlp --print channel_id <link de um vídeo>`).
- **PyAV:** mantenha `av` < 16, porque o faster-whisper 1.2 quebra com o PyAV 19.
