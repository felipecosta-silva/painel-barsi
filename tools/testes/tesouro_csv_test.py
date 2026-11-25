"""Teste unitário do parser e cálculo de mediana do Tesouro Direto (fixture CSV com 3 títulos)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from tesouro import calcular_ntnb_mediana, parse_csv_tesouro  # noqa: E402

FIXTURE_CSV = "\n".join([
    "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha",
    # Data antiga (deve ser ignorada ao pegar max Data Base)
    "Tesouro IPCA+;15/05/2035;18/11/2026;7,10;7,22;2500,00;2480,00;2480,00",
    # 3 títulos na Data Base mais recente (19/11/2026):
    # - IPCA+ 2032 (< 2035: NÃO entra na mediana ntnb longa)
    "Tesouro IPCA+;15/08/2032;19/11/2026;7,82;7,94;3110,97;3088,81;3087,12",
    # - IPCA+ 2035 (>= 2035: entra na mediana)
    "Tesouro IPCA+;15/05/2035;19/11/2026;7,60;7,72;2526,53;2500,95;2499,10",
    # - IPCA+ 2045 (>= 2035: entra na mediana)
    "Tesouro IPCA+;15/05/2045;19/11/2026;7,80;7,92;1255,17;1228,74;1227,50",
    # Extra com Juros Semestrais (>= 2035, mas com cupom -> NÃO entra na mediana sem cupom)
    "Tesouro IPCA+ com Juros Semestrais;15/05/2045;19/11/2026;9,50;9,62;4072,24;4020,53;4019,00",
])


def main() -> int:
    res = parse_csv_tesouro(FIXTURE_CSV)
    assert res["atualizado"] == "2026-11-19", f"Data base inesperada: {res['atualizado']}"
    assert len(res["titulos"]) == 4, f"Esperava 4 títulos em 19/11/2026, veio {len(res['titulos'])}"

    ipca32 = next(t for t in res["titulos"] if t["ticker"] == "TESOURO-IPCA-2032")
    assert ipca32["vencimento"] == "2032-08-15", ipca32
    assert ipca32["taxaCompra"] == 7.82, ipca32
    assert ipca32["puCompra"] == 3110.97, ipca32

    # Mediana dos 2 IPCA+ sem cupom com vencimento >= 2035: (7.60 + 7.80) / 2 = 7.70
    assert res["ntnbMediana"] == 7.70, f"Mediana esperada 7.70, obtida {res['ntnbMediana']}"
    assert res["ntnbTitulos"] == ["2035-05-15", "2045-05-15"], res["ntnbTitulos"]

    # Fixture estrita de 3 títulos sem cupom (>= 2035 + < 2035)
    med3 = calcular_ntnb_mediana([
        {"nome": "Tesouro IPCA+", "vencimento": "2032-08-15", "taxaCompra": 8.10},
        {"nome": "Tesouro IPCA+", "vencimento": "2035-05-15", "taxaCompra": 7.50},
        {"nome": "Tesouro IPCA+", "vencimento": "2040-08-15", "taxaCompra": 7.90},
        {"nome": "Tesouro IPCA+", "vencimento": "2050-08-15", "taxaCompra": 7.60},
    ])
    assert med3 == 7.60, f"Mediana de [7.50, 7.60, 7.90] devia ser 7.60, veio {med3}"

    print("OK tesouro_csv_test: parse, data ISO, exclusao JS/<2035 e mediana (7.70 / 7.60) validados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
