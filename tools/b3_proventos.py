import json, base64, urllib.request, ssl, re, time, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CACHE_NOMES = RAIZ / "dados" / "cache_b3_nomes.json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Fehmir/1.0"}

ALIASES_CODIGO = {
    "TRPL": "ISAE",
    "BRIT": "BRST"
}

def carregar_cache():
    if CACHE_NOMES.exists():
        try:
            return json.loads(CACHE_NOMES.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def salvar_cache(cache):
    CACHE_NOMES.parent.mkdir(exist_ok=True)
    CACHE_NOMES.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

def descobrir_trading_name(ticker):
    codigo = re.sub(r'\d+$', '', ticker).upper()
    codigo = ALIASES_CODIGO.get(codigo, codigo)
    cache = carregar_cache()
    if codigo in cache:
        return cache[codigo]
    
    payload = json.dumps({"language": "pt-br", "pageNumber": 1, "pageSize": 20, "company": codigo})
    b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    url = f"https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/{b64}"
    req = urllib.request.Request(url, headers=UA)
    trading_name = None
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for r in data.get("results", []):
                if r.get("issuingCompany") == codigo:
                    trading_name = r.get("tradingName")
                    break
            if not trading_name and data.get("results"):
                trading_name = data["results"][0].get("tradingName")
    except Exception as e:
        print(f"Aviso: falha de rede ao buscar tradingName de {codigo}: {e}")
        return None

    if trading_name:
        cache[codigo] = trading_name
        salvar_cache(cache)
    time.sleep(1)
    return trading_name

def obter_classe_ticker(ticker):
    if ticker.endswith("3"):
        return "ON"
    elif ticker.endswith("4"):
        return "PN"
    elif ticker.endswith("11"):
        return "UNT"
    return None

def buscar_proventos_b3(ticker):
    target_type = obter_classe_ticker(ticker)
    if not target_type:
        return {"ok": False, "erro": f"Classe não mapeada para ticker {ticker}", "por_ano": {}, "eventos": []}
    
    trading_name = descobrir_trading_name(ticker)
    if not trading_name:
        return {"ok": False, "erro": f"tradingName não encontrado na B3 para {ticker}", "por_ano": {}, "eventos": []}
    
    page = 1
    total_pages = 1
    todos_results = []
    
    while page <= total_pages:
        payload = json.dumps({"language": "pt-br", "pageNumber": page, "pageSize": 120, "tradingName": trading_name})
        b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        url = f"https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetListedCashDividends/{b64}"
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                page_info = data.get("page", {})
                total_pages = page_info.get("totalPages", 1)
                results = data.get("results", [])
                todos_results.extend(results)
        except Exception as e:
            print(f"Aviso: falha de rede ao buscar dividendos B3 para {ticker} (página {page}): {e}")
            break
        page += 1
        if page <= total_pages:
            time.sleep(1)

    por_ano = {}
    eventos = []
    achou_tipo = False

    for r in todos_results:
        st = (r.get("typeStock") or "").strip().upper()
        eh_tipo = (st == target_type) or (target_type == "PN" and st.startswith("PN"))
        if eh_tipo:
            achou_tipo = True
            action = (r.get("corporateAction") or "").strip().upper()
            if action in ["DIVIDENDO", "JRS CAP PROPRIO", "RENDIMENTO"]:
                dt = r.get("lastDatePriorEx")
                if dt and len(dt.split("/")) == 3:
                    y = int(dt.split("/")[-1])
                    val_str = (r.get("valueCash") or "0").replace(",", ".")
                    try:
                        val = float(val_str)
                    except ValueError:
                        val = 0.0
                    por_ano[y] = por_ano.get(y, 0.0) + val
                    eventos.append({
                        "data": dt,
                        "ano": y,
                        "valor": val,
                        "tipo": st,
                        "acao": action
                    })

    if not achou_tipo and todos_results:
        return {
            "ok": False,
            "erro": f"Sem registros da classe {target_type} para {trading_name} na B3",
            "trading_name": trading_name,
            "por_ano": {},
            "eventos": []
        }

    return {
        "ok": True,
        "trading_name": trading_name,
        "tipo": target_type,
        "por_ano": {y: round(v, 4) for y, v in sorted(por_ano.items())},
        "eventos": eventos
    }

if __name__ == "__main__":
    for tk in ["CPFE3", "ISAE4", "TEND3", "SUZB3", "IRBR3"]:
        res = buscar_proventos_b3(tk)
        print(f"{tk}: ok={res['ok']}, anos={res.get('por_ano')}, erro={res.get('erro')}")
