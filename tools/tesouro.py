"""Baixa o CSV oficial do Tesouro Direto (Tesouro Transparente) e gera dados/tesouro.js."""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import ssl
import statistics
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dados" / "tesouro.js"
URL_TESOURO = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/"
    "precotaxatesourodireto.csv"
)


def parse_data_br(valor: str) -> str:
    s = (valor or "").strip()
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        d, m, y = s.split("/")
        return f"{y}-{m}-{d}"
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    raise ValueError(f"Data inválida no CSV do Tesouro: {valor!r}")


def parse_num_br(valor: str) -> float | None:
    s = (valor or "").strip()
    if not s or s == "-":
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return round(float(s), 4)


def ticker_titulo(nome: str, vencimento_iso: str) -> str:
    ano = vencimento_iso[:4]
    n = " ".join((nome or "").strip().split())
    mapa = {
        "Tesouro IPCA+": f"TESOURO-IPCA-{ano}",
        "Tesouro IPCA+ com Juros Semestrais": f"TESOURO-IPCA-JS-{ano}",
        "Tesouro Prefixado": f"TESOURO-PRE-{ano}",
        "Tesouro Prefixado com Juros Semestrais": f"TESOURO-PRE-JS-{ano}",
        "Tesouro Selic": f"TESOURO-SELIC-{ano}",
        "Tesouro Renda+ Aposentadoria Extra": f"TESOURO-RENDA-{ano}",
        "Tesouro Educa+": f"TESOURO-EDUCA-{ano}",
        "Tesouro IGPM+ com Juros Semestrais": f"TESOURO-IGPM-JS-{ano}",
    }
    if n in mapa:
        return mapa[n]
    slug = "".join(ch if ch.isalnum() else "-" for ch in n.upper()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"{slug}-{ano}"


def calcular_ntnb_mediana(titulos: list[dict], ano_minimo: int = 2035) -> float | None:
    """Mediana da taxaCompra dos Tesouro IPCA+ sem cupom com vencimento >= ano_minimo."""
    taxas = []
    for t in titulos:
        nome = (t.get("nome") or "").strip()
        if nome != "Tesouro IPCA+":
            continue
        venc = str(t.get("vencimento") or "")
        if len(venc) < 4 or not venc[:4].isdigit():
            continue
        if int(venc[:4]) < ano_minimo:
            continue
        taxa = t.get("taxaCompra")
        if isinstance(taxa, (int, float)) and taxa > 0:
            taxas.append(float(taxa))
    if not taxas:
        return None
    return round(statistics.median(taxas), 2)


def parse_csv_tesouro(texto: str, data_alvo: str | None = None) -> dict:
    """Lê CSV (separado por ;) do Tesouro Transparente e extrai os títulos da última Data Base."""
    leitor = csv.DictReader(io.StringIO(texto.lstrip("\ufeff")), delimiter=";")
    if not leitor.fieldnames:
        raise ValueError("CSV do Tesouro sem cabeçalho.")
    linhas = []
    for raw in leitor:
        row = {str(k or "").strip(): (v or "").strip() for k, v in raw.items()}
        nome = row.get("Tipo Titulo")
        dt_venc = row.get("Data Vencimento")
        dt_base = row.get("Data Base")
        if not nome or not dt_venc or not dt_base:
            continue
        try:
            venc_iso = parse_data_br(dt_venc)
            base_iso = parse_data_br(dt_base)
        except ValueError:
            continue
        linhas.append({
            "nome": nome,
            "vencimento": venc_iso,
            "dataBase": base_iso,
            "taxaCompra": parse_num_br(row.get("Taxa Compra Manha", "")),
            "taxaVenda": parse_num_br(row.get("Taxa Venda Manha", "")),
            "puCompra": parse_num_br(row.get("PU Compra Manha", "")),
            "puVenda": parse_num_br(row.get("PU Venda Manha", "")),
        })

    if not linhas:
        raise ValueError("Nenhuma linha válida encontrada no CSV do Tesouro.")

    data_ref = data_alvo or max(x["dataBase"] for x in linhas)
    do_dia = [x for x in linhas if x["dataBase"] == data_ref]
    if not do_dia:
        raise ValueError(f"Data Base {data_ref} não encontrada no CSV.")

    usados = set()
    titulos = []
    for x in sorted(do_dia, key=lambda r: (r["nome"], r["vencimento"])):
        tk = ticker_titulo(x["nome"], x["vencimento"])
        if tk in usados:
            tk = f"{tk}-{x['vencimento'][5:7]}"
        usados.add(tk)
        titulos.append({
            "nome": x["nome"],
            "ticker": tk,
            "vencimento": x["vencimento"],
            "taxaCompra": round(x["taxaCompra"], 2) if x["taxaCompra"] is not None else None,
            "taxaVenda": round(x["taxaVenda"], 2) if x["taxaVenda"] is not None else None,
            "puCompra": round(x["puCompra"], 2) if x["puCompra"] is not None else None,
            "puVenda": round(x["puVenda"], 2) if x["puVenda"] is not None else None,
        })

    ntnb_med = calcular_ntnb_mediana(titulos, 2035)
    ntnb_vencs = [
        t["vencimento"]
        for t in titulos
        if t["nome"] == "Tesouro IPCA+" and int(t["vencimento"][:4]) >= 2035 and (t["taxaCompra"] or 0) > 0
    ]
    return {
        "atualizado": data_ref,
        "fonte": "Tesouro Transparente (CSV oficial)",
        "ntnbMediana": ntnb_med,
        "ntnbTitulos": ntnb_vencs,
        "titulos": titulos,
    }


def baixar_csv(url: str = URL_TESOURO, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "FehmirPainel/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        print("[aviso] SSL local sem CA do .gov.br; usando contexto sem verificação.", file=sys.stderr)
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
    for enc in ("latin-1", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def gravar_js(dados: dict, destino: Path = OUT) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    conteudo = (
        "// Gerado por tools/tesouro.py — fonte: Tesouro Transparente (CSV oficial)\n"
        f"window.FEHMIR_TESOURO = {json.dumps(dados, ensure_ascii=False, indent=2)};\n"
    )
    destino.write_text(conteudo, encoding="utf-8")


def main() -> int:
    texto = baixar_csv()
    dados = parse_csv_tesouro(texto)
    gravar_js(dados)
    print(
        f"OK dados/tesouro.js atualizado: base={dados['atualizado']} | "
        f"titulos={len(dados['titulos'])} | ntnbMediana={dados['ntnbMediana']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
