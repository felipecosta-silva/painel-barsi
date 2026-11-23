"""Transcrição de vídeos do YouTube (inclusive de membros) para o estudo do Felipe.

Uso (roda com qualquer Python; ele se reabre no ambiente próprio):
  python tools/transcricao/videos.py transcrever <link ou id> [mais links...] [--whisper = ignora a legenda]
  python tools/transcricao/videos.py radar              → procura vídeos novos nos canais de canais.json, transcreve os pertinentes
  python tools/transcricao/videos.py radar --listar     → só mostra o que achou e a pontuação, sem baixar
  python tools/transcricao/videos.py buscar-ativos [--dias 30] [--por-ativo 2] [--listar] → busca vídeos recentes dos ativos da carteira
  python tools/transcricao/videos.py marcar-vistos [--publicos] → marca o que existe hoje como visto (só os públicos, com --publicos)

Caminho: legenda do YouTube em português (instantâneo) → se não houver, baixa só o áudio e transcreve no PC com o
faster-whisper (modelo large-v3-turbo, CPU). Saída em estudos/transcricoes/ (só local; nunca publicar: conteúdo de
terceiros, inclusive pago). A fila do que falta analisar fica em estudos/transcricoes/FILA.md.
Ambiente, cookies e áudio ficam em %LOCALAPPDATA%\\painel-transcricao (fora do OneDrive e do Git).
"""
import json, os, re, subprocess, sys, time, datetime as dt
from pathlib import Path

BASE = Path(os.environ["LOCALAPPDATA"]) / "painel-transcricao"
VENV_PY = BASE / "venv" / "Scripts" / "python.exe"
RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "estudos" / "transcricoes"
REGISTRO = SAIDA / "_processados.json"
FILA = SAIDA / "FILA.md"
COOKIES = BASE / "cookies.txt"
CANAIS = Path(__file__).with_name("canais.json")
MODELO = os.environ.get("WHISPER_MODELO", "large-v3-turbo")
FORCAR_WHISPER = "--whisper" in sys.argv

# Reabre no ambiente com faster-whisper e yt-dlp (Python 3.12), se não estiver nele.
if Path(sys.executable).resolve() != VENV_PY.resolve():
    if not VENV_PY.exists():
        sys.exit(f"Ambiente não encontrado em {VENV_PY}. Veja tools/transcricao/LEIAME.md.")
    sys.exit(subprocess.call([str(VENV_PY), "-X", "utf8", __file__, *sys.argv[1:]]))

import yt_dlp  # noqa: E402

SAIDA.mkdir(parents=True, exist_ok=True)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------- cookies ----------
def renovar_cookies():
    """Gera cookies.txt a partir do perfil do Chrome do robô. Devolve True se a sessão está logada."""
    r = subprocess.run(["node", str(Path(__file__).with_name("cookies_youtube.js"))], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    msg = (r.stdout + r.stderr).strip()
    log("cookies:", msg.splitlines()[-1] if msg else f"código {r.returncode}")
    return r.returncode == 0


def opcoes_base():
    o = {"quiet": True, "no_warnings": True, "js_runtimes": {"node": {}}}
    if COOKIES.exists():
        o["cookiefile"] = str(COOKIES)
    return o


# ---------- vocabulário (ajuda o Whisper a escrever tickers certo e pontua pertinência) ----------
def vocabulario():
    txt = (RAIZ / "dados" / "tetos.js").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"FEHMIR_CARTEIRA\s*=\s*(\{.*?\});", txt)
    carteira = [k for k in json.loads(m.group(1)) if re.fullmatch(r"[A-Z]{4}\d{1,2}", k)] if m else []
    radar = sorted(set(re.findall(r'^ "([A-Z]{4}\d{1,2})": \{', txt, re.M)))
    dossies = [p.stem for p in (RAIZ / "estudos" / "dossies").glob("*.md") if re.fullmatch(r"[A-Z]{4}\d{1,2}", p.stem)]
    return carteira, sorted(set(radar) | set(dossies))


APELIDOS = {  # nome falado/escrito no título → ticker (só os que aparecem em títulos sem o código)
    "CEMIG": "CMIG4", "TAESA": "TAEE11", "BB SEGURIDADE": "BBSE3", "PETROBRAS": "PETR4", "LOG CP": "LOGG3",
    "TIM": "TIMS3", "ISA ENERGIA": "ISAE4", "ISA CTEEP": "ISAE4", "BRADESCO": "BBDC4", "ITAÚSA": "ITSA4", "ITAUSA": "ITSA4",
    "BANCO DO BRASIL": "BBAS3", "SANEPAR": "SAPR11", "COPASA": "CSMG3", "KLABIN": "KLBN4", "MINERADORA VALE": "VALE3", "WEG": "WEGE3",
    "PORTO SEGURO": "PSSA3", "CAIXA SEGURIDADE": "CXSE3", "CPFL": "CPFE3", "ALUPAR": "ALUP11", "COPEL": "CPLE6",
    "ITAÚ": "ITUB4", "ITAU": "ITUB4", "SANTANDER": "SANB11", "BTG": "BPAC11",
}
TEMAS = ["DIVIDEND", "CARTEIRA", "FII", "FUNDOS IMOBILI", "FIAGRO", "DÓLAR", "DOLAR", "SELIC", "JUROS", "APORTE", "BARSI",
         "BAZIN", "RENDA PASSIVA", "APOSENT", "PREÇO TETO", "PRECO TETO", "VALUATION", "INSS", "EXTERIOR", "ETF", "REBALANC", "OPORTUNIDADE"]


def pontuar(titulo, carteira, radar, temas_extra=()):
    t = titulo.upper()
    achados = set(re.findall(r"\b[A-Z]{4}\d{1,2}\b", t))
    for nome, tk in APELIDOS.items():
        if re.search(r"\b" + re.escape(nome) + r"\b", t):
            achados.add(tk)
    na_carteira = sorted(a for a in achados if a in carteira)
    no_radar = sorted(a for a in achados if a in radar and a not in carteira)
    temas = [w.title() for w in [*TEMAS, *temas_extra] if w.upper() in t]
    nota = 3 * len(na_carteira) + 2 * len(no_radar) + (1 if temas else 0)
    motivo = ", ".join(filter(None, [
        "carteira: " + " ".join(na_carteira) if na_carteira else "",
        "radar: " + " ".join(no_radar) if no_radar else "",
        "tema: " + " ".join(temas[:3]) if temas else ""]))
    return nota, motivo or "sem ticker nem tema"


# ---------- legenda do YouTube ----------
def legenda(info):
    """Usa legenda em português (manual > automática). Devolve [(segundos, texto)] ou None."""
    for fonte, chave in (("legenda manual do YouTube", "subtitles"), ("legenda automática do YouTube", "automatic_captions")):
        subs = info.get(chave) or {}
        lang = next((l for l in subs if l in ("pt", "pt-BR", "pt-orig") or l.startswith("pt")), None)
        if chave == "automatic_captions":  # a automática só presta no idioma original do vídeo
            lang = "pt-orig" if "pt-orig" in subs else ("pt" if "pt" in subs and (info.get("language") or "pt").startswith("pt") else None)
        if not lang:
            continue
        fmt = next((f for f in subs[lang] if f.get("ext") == "json3"), None)
        if not fmt:
            continue
        with yt_dlp.YoutubeDL(opcoes_base()) as y:
            dados = json.loads(y.urlopen(fmt["url"]).read().decode("utf-8"))
        segs = []
        for ev in dados.get("events", []):
            txt = "".join(s.get("utf8", "") for s in ev.get("segs") or []).replace("\n", " ").strip()
            if txt:
                segs.append((ev.get("tStartMs", 0) / 1000, txt))
        if len(segs) > 5:
            return segs, fonte
    return None, None


# ---------- whisper ----------
_modelo = None


def whisper(arquivo, dica):
    global _modelo
    from faster_whisper import WhisperModel
    if _modelo is None:
        log(f"carregando o modelo {MODELO} (1ª vez baixa ~1,6 GB)…")
        _modelo = WhisperModel(MODELO, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    segs, info = _modelo.transcribe(str(arquivo), language="pt", vad_filter=True, beam_size=2,
                                    initial_prompt=dica, condition_on_previous_text=False)
    saida, ultimo = [], -60
    for s in segs:
        saida.append((s.start, s.text.strip()))
        if s.start - ultimo >= 300:
            log(f"  … {int(s.start // 60)} de {int(info.duration // 60)} min")
            ultimo = s.start
    return saida


def baixar_audio(vid):
    pasta = BASE / "audio"
    pasta.mkdir(exist_ok=True)
    o = opcoes_base() | {"format": "bestaudio[ext=m4a]/bestaudio", "outtmpl": str(pasta / "%(id)s.%(ext)s")}
    with yt_dlp.YoutubeDL(o) as y:
        info = y.extract_info(vid, download=True)
        return Path(y.prepare_filename(info))


# ---------- saída ----------
def mmss(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def _slug(t, n):
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:n]


def gravar(info, segs, fonte):
    data = info.get("upload_date") or dt.date.today().strftime("%Y%m%d")
    data = f"{data[:4]}-{data[4:6]}-{data[6:]}"
    canal = _slug(info.get("channel") or "canal", 30)
    titulo = _slug(info.get("title") or info["id"], 60)
    arq = SAIDA / f"{data}-{canal}-{titulo}.md"
    blocos, atual, ini = [], [], None
    for t, txt in segs:
        if ini is None:
            ini = t
        atual.append(txt)
        if t - ini >= 45:
            blocos.append(f"**[{mmss(ini)}]** " + " ".join(atual))
            atual, ini = [], None
    if atual:
        blocos.append(f"**[{mmss(ini or 0)}]** " + " ".join(atual))
    cab = [f"# {info.get('title')}", "",
           f"- Canal: {info.get('channel')} · publicado em {data} · duração {mmss(info.get('duration') or 0)}",
           f"- Link: https://www.youtube.com/watch?v={info['id']}" + (" (exclusivo para membros)" if info.get("availability") == "subscriber_only" else ""),
           f"- Transcrição: {fonte} · gerada em {dt.datetime.now():%Y-%m-%d %H:%M}",
           "- Uso pessoal de estudo. Não publicar nem repassar.", "", ""]
    arq.write_text("\n".join(cab) + "\n\n".join(blocos) + "\n", encoding="utf-8")
    return arq


def registro():
    return json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else {}


def salvar_registro(r):
    REGISTRO.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")


def para_fila(info, arq, motivo):
    novo = not FILA.exists()
    with FILA.open("a", encoding="utf-8") as f:
        if novo:
            f.write("# Fila de transcrições para analisar\n\nMarque [x] depois de analisar (o Claude lê o arquivo e atualiza dossiês).\n\n")
        f.write(f"- [ ] {dt.date.today():%d/%m} · {info.get('channel')} · {info.get('title')} · "
                f"`{arq.relative_to(RAIZ).as_posix()}` · {motivo}\n")


def transcrever(vid, motivo="pedido manual", dica_canal=None):
    carteira, radar = vocabulario()
    dica = dica_canal or ("Vídeo sobre investimentos em ações e fundos imobiliários: dividendos, dividend yield, P/VP, Selic, CDI, IPCA, "
            "preço teto, Bazin, Barsi. Tickers: " + ", ".join(carteira + radar[:60]) + ".")
    with yt_dlp.YoutubeDL(opcoes_base()) as y:
        info = y.extract_info(vid, download=False)
    log(f"▶ {info.get('title')} ({mmss(info.get('duration') or 0)})")
    segs, fonte = (None, None) if FORCAR_WHISPER else legenda(info)
    if not segs:
        log("  sem legenda em português: baixando o áudio para o Whisper…")
        audio = baixar_audio(info["id"])
        t0 = time.time()
        segs = whisper(audio, dica)
        fonte = f"Whisper {MODELO} no PC ({(time.time() - t0) / 60:.0f} min)"
        audio.unlink(missing_ok=True)
    arq = gravar(info, segs, fonte)
    r = registro()
    r[info["id"]] = {"titulo": info.get("title"), "canal": info.get("channel"), "arquivo": arq.name,
                     "quando": f"{dt.datetime.now():%Y-%m-%d %H:%M}", "motivo": motivo}
    salvar_registro(r)
    para_fila(info, arq, motivo)
    log(f"  ✔ {arq.relative_to(RAIZ)} ({fonte})")
    return arq


# ---------- radar ----------
def listar(url, n):
    o = opcoes_base() | {"extract_flat": True, "playlistend": n}
    with yt_dlp.YoutubeDL(o) as y:
        return [e for e in (y.extract_info(url, download=False).get("entries") or []) if e and e.get("id")]


def candidatos(n=15):
    canais = json.loads(CANAIS.read_text(encoding="utf-8"))
    for c in canais:
        cid = c["id"]
        fontes = []
        if c.get("membro"):
            fontes.append(("membros", f"https://www.youtube.com/playlist?list=UUMO{cid[2:]}", c.get("membros", "todos")))
        fontes.append(("público", f"https://www.youtube.com/channel/{cid}/videos", c.get("publicos", "pertinentes")))
        for tipo, url, regra in fontes:
            if regra == "nenhum":
                continue
            try:
                for e in listar(url, n):
                    yield c, tipo, regra, e
            except Exception as ex:  # canal fora do ar, mudança no YouTube…
                log(f"  ! {c['nome']} ({tipo}): {str(ex)[:120]}")


def radar(so_listar=False, marcar=False, so_publicos=False):
    carteira, rad = vocabulario()
    reg = registro()
    if not so_listar and not marcar:
        if not renovar_cookies():
            log("  sem sessão logada: vídeos de membros vão falhar (rode cookies_youtube.js --login).")
    fazer, vistos = [], set()
    for c, tipo, regra, e in candidatos():
        if e["id"] in reg or e["id"] in vistos:
            continue
        vistos.add(e["id"])
        nota, motivo = pontuar(e.get("title") or "", carteira, rad, c.get("temas", ()))
        pega = regra == "todos" or (regra == "pertinentes" and nota >= c.get("nota_minima", 2))
        if so_listar:
            print(f"{'✔' if pega else '·'} [{nota}] {c['nome']} ({tipo}) {e.get('title')} — {motivo} — {e['id']}")
        elif marcar:
            if so_publicos and tipo != "público":
                continue
            reg[e["id"]] = {"titulo": e.get("title"), "canal": c["nome"], "arquivo": None, "quando": f"{dt.datetime.now():%Y-%m-%d %H:%M}", "motivo": "marcado como visto"}
        elif pega:
            fazer.append((e["id"], f"{c['nome']} ({tipo}) · {motivo}", c.get("dica")))
        else:
            reg[e["id"]] = {"titulo": e.get("title"), "canal": c["nome"], "arquivo": None, "quando": f"{dt.datetime.now():%Y-%m-%d %H:%M}", "motivo": f"ignorado ({motivo})"}
    if marcar or not so_listar:
        salvar_registro(reg)
    if marcar:
        log(f"marcados como vistos: {len(reg)}")
        return
    for vid, motivo, dica in fazer:
        try:
            transcrever(vid, motivo, dica)
        except Exception as ex:
            log(f"  ✖ {vid}: {str(ex)[:200]}")
    if not so_listar:
        log(f"radar concluído: {len(fazer)} vídeo(s) para transcrever nesta rodada.")


# ---------- busca por ativo ----------
EXTRA_ATIVOS = ["ITSA4"]
CANAIS_CONFIAVEIS = [
    "Clube do Valor", "Investidor de Fábrica", "Beca Alcântara", "Nícolas Agnezi",
    "Eric Leonardo", "Mestre da Riqueza", "TioFIIs", "Traduzindo FIIs", "Visão FII",
    "O Pequeno Investidor", "Bruno Chimarelli", "Invest Cuts", "Professor Mira",
]


def _norm_txt(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().casefold().strip()


def _titulo_tem_ativo(titulo, ticker):
    t = (titulo or "").upper()
    if re.search(r"\b" + re.escape(ticker.upper()) + r"\b", t):
        return True
    t_norm = _norm_txt(titulo)
    for nome, tk in APELIDOS.items():
        if tk == ticker and re.search(r"\b" + re.escape(_norm_txt(nome)) + r"\b", t_norm):
            return True
    return False


def _leo_channel_id():
    if not CANAIS.exists():
        return None
    for c in json.loads(CANAIS.read_text(encoding="utf-8")):
        if "léo" in (c.get("nome") or "").lower() or "geração dividendos" in (c.get("nome") or "").lower():
            return c.get("id")
    return None


def _prioridade_canal(info, leo_id):
    cid = info.get("channel_id") or ""
    canal = _norm_txt(info.get("channel") or info.get("uploader") or "")
    confiaveis = {_norm_txt(x) for x in CANAIS_CONFIAVEIS}
    if leo_id and cid == leo_id:
        return 1, "Léo"
    if canal in confiaveis:
        return 2, "Confiável"
    return 3, "Outro"


def buscar_ativos(dias=30, por_ativo=2, so_listar=False):
    carteira, rad = vocabulario()
    ativos = list(dict.fromkeys([*carteira, *EXTRA_ATIVOS]))
    reg = registro()
    if not so_listar:
        if not renovar_cookies():
            log("  sem sessão logada: vídeos de membros podem falhar (rode cookies_youtube.js --login).")
    leo_id = _leo_channel_id()
    corte = (dt.date.today() - dt.timedelta(days=dias)).strftime("%Y%m%d")
    cache_meta = {}
    o_flat = opcoes_base() | {"extract_flat": True, "playlistend": 20}
    o_meta = opcoes_base()
    transcritos_rodada = set()

    for ticker in ativos:
        log(f"🔎 {ticker} (últimos {dias} dias)…")
        try:
            with yt_dlp.YoutubeDL(o_flat) as y:
                res = y.extract_info(f"https://www.youtube.com/results?search_query={ticker}&sp=CAI%3D", download=False)
                entries = [e for e in (res.get("entries") or []) if e and e.get("id")]
        except Exception as ex:
            log(f"  ! erro na busca de {ticker}: {str(ex)[:120]}")
            continue

        elegiveis = []
        vistos_tk = set()
        for e in entries:
            vid = e["id"]
            if vid in reg or vid in vistos_tk:
                continue
            vistos_tk.add(vid)
            titulo_flat = e.get("title") or ""
            if titulo_flat and not _titulo_tem_ativo(titulo_flat, ticker):
                continue
            if vid not in cache_meta:
                try:
                    with yt_dlp.YoutubeDL(o_meta) as y:
                        cache_meta[vid] = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False) or {}
                except Exception as ex:
                    log(f"  ! {vid}: {str(ex)[:100]}")
                    cache_meta[vid] = {}
            info = cache_meta[vid]
            if not info:
                continue
            titulo = info.get("title") or titulo_flat
            if not _titulo_tem_ativo(titulo, ticker):
                continue
            dur = info.get("duration") or 0
            if not (360 <= dur <= 5400):
                continue
            up = info.get("upload_date") or ""
            if not up or up < corte:
                continue
            tier, tier_nome = _prioridade_canal(info, leo_id)
            nota_p, motivo_p = pontuar(titulo, carteira, rad)
            elegiveis.append((tier, -int(up), -nota_p, tier_nome, nota_p, motivo_p, info))

        elegiveis.sort(key=lambda x: (x[0], x[1], x[2]))
        escolhidos = elegiveis[:por_ativo]
        if not elegiveis:
            print(f"— {ticker}: nenhum candidato novo encontrado nos últimos {dias} dias")
            continue
        for idx, (tier, _, _, tier_nome, nota_p, motivo_p, info) in enumerate(elegiveis):
            vid = info["id"]
            up = info.get("upload_date") or "????????"
            data_fmt = f"{up[:4]}-{up[4:6]}-{up[6:]}" if len(up) == 8 else up
            dur_fmt = mmss(info.get("duration") or 0)
            pega = idx < por_ativo
            canal_nm = info.get("channel") or info.get("uploader") or "?"
            if so_listar or pega:
                print(f"{'✔' if pega else '·'} [P{tier} {tier_nome} | nota {nota_p}] {ticker} · {data_fmt} · {dur_fmt} · {canal_nm} · {info.get('title')} — {motivo_p} — {vid}")
        if not so_listar:
            for _, _, _, _, _, _, info in escolhidos:
                vid = info["id"]
                if vid in transcritos_rodada or vid in registro():
                    continue
                try:
                    transcrever(vid, motivo=f"busca por ativo: {ticker}")
                    transcritos_rodada.add(vid)
                except Exception as ex:
                    log(f"  ✖ {ticker} ({vid}): {str(ex)[:200]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
    elif a[0] == "transcrever":
        renovar_cookies()
        for v in a[1:]:
            if not v.startswith("--"):
                transcrever(v)
    elif a[0] == "radar":
        radar(so_listar="--listar" in a)
    elif a[0] == "buscar-ativos":
        import argparse
        p = argparse.ArgumentParser(prog="videos.py buscar-ativos")
        p.add_argument("--dias", type=int, default=30)
        p.add_argument("--por-ativo", type=int, default=2)
        p.add_argument("--listar", action="store_true")
        ns = p.parse_args(a[1:])
        buscar_ativos(dias=ns.dias, por_ativo=ns.por_ativo, so_listar=ns.listar)
    elif a[0] == "marcar-vistos":
        radar(marcar=True, so_publicos="--publicos" in a)
    else:
        print(__doc__)
