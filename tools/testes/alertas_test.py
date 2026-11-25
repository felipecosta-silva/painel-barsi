"""Testes unitários com fixture dos alertas Telegram + histerese anti-spam + trava de preço velho."""
from __future__ import annotations

import copy
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from alertas import avaliar_alertas  # noqa: E402
from checar_segredos import PADROES  # noqa: E402


def _fixture_base() -> dict:
    return {
        "meta_mercado": {"gerado": "2026-11-25 18:00"},
        "precos": {
            "ITSA4": 12.90,   # <= 13.00 -> DISPARA compra manual
            "VISC11": 95.00,  # > 91.65 -> NÃO dispara
            "TAEE11": 35.00,  # <= 36.00 (automática) -> DISPARA
            "PETR4": 48.50,   # >= 38.00 * 1.2 = 45.60 em cíclica na carteira -> DISPARA venda
        },
        "tetos": {
            "ITSA4": {"teto": 15.00, "compra": 13.50, "setor": "Bancos", "metodo": "Bazin"},
            "VISC11": {"teto": 96.47, "compra": 91.65, "setor": "Shopping", "metodo": "FII"},
            "TAEE11": {"teto": 37.90, "compra": 36.00, "setor": "Elétricas · Transmissão", "metodo": "Bazin"},
            "PETR4": {"teto": 38.00, "compra": 30.40, "setor": "Commodities", "metodo": "Bazin"},
        },
        "carteira": {
            "PETR4": 7,
            "TAEE11": 4,  # automática vale só para carteira + "vigiar" (revisão 32-B)
        },
        "vigiar": set(),
        "silenciar": {},
        "tesouro": {
            "atualizado": "2026-11-25",
            "titulos": [
                {"nome": "Tesouro IPCA+", "ticker": "TESOURO-IPCA-2032", "vencimento": "2032-08-15", "taxaCompra": 7.75}
            ],
        },
        "regras_manuais": [
            {"id": "manual:ITSA4:compra", "ticker": "ITSA4", "tipo": "compra", "condicao": "<=", "valor": 13.00, "texto": "compra 2-3"},
            {"id": "manual:VISC11:compra", "ticker": "VISC11", "tipo": "compra", "condicao": "<=", "valor": 91.65, "texto": "até 2 cotas"},
            {"id": "manual:TESOURO-IPCA-2032:taxa", "ticker": "TESOURO-IPCA-2032", "tipo": "taxa", "condicao": ">=", "valor": 7.50, "texto": "aporte R$ 40-50"},
        ],
        "alertas_analista": [],
        "estado": {"atualizado": None, "regras": {}},
    }


def main() -> int:
    hoje = dt.date(2026, 11, 25)
    d1 = _fixture_base()

    # 1 e 2. Regras que devem disparar vs não disparar (sem lista vazia e sem duplicar ITSA4)
    r1 = avaliar_alertas(d1, hoje=hoje)
    ids1 = {x["id"] for x in r1["novos"]}
    assert "manual:ITSA4:compra" in ids1, f"ITSA4 deveria disparar: {ids1}"
    assert "auto:ITSA4:compra" not in ids1, f"ITSA4 não deve duplicar com automática: {ids1}"
    assert "manual:VISC11:compra" not in ids1, f"VISC11 não deveria disparar a 95,00: {ids1}"
    assert "auto:TAEE11:compra" in ids1, f"TAEE11 automática deveria disparar: {ids1}"
    assert "auto:PETR4:venda" in ids1, f"PETR4 cíclica >= teto*1,2 deveria disparar venda: {ids1}"
    assert "manual:TESOURO-IPCA-2032:taxa" in ids1, f"TESOURO-IPCA-2032 taxa deveria disparar: {ids1}"
    assert r1["mensagem"] and "felipecosta-silva.github.io/painel-barsi/" in r1["mensagem"], r1["mensagem"]

    # 3. Repetição com mesmos valores deve ser suprimida pelo anti-spam
    d2 = copy.deepcopy(d1)
    d2["estado"] = r1["estado_novo"]
    r2 = avaliar_alertas(d2, hoje=hoje)
    assert len(r2["novos"]) == 0 and r2["mensagem"] is None, f"Esperava supressão, veio {r2['novos']}"

    # 4a. Dentro da histerese (+0,5% no preço, -0,03 p.p. na taxa) ainda NÃO reseta nem dispara
    d3 = copy.deepcopy(d1)
    d3["estado"] = r2["estado_novo"]
    d3["precos"]["ITSA4"] = 13.06  # <= 13.00 * 1.01 (13.13) -> ainda preso na histerese
    d3["tesouro"]["titulos"][0]["taxaCompra"] = 7.47  # >= 7.50 - 0.05 (7.45) -> ainda preso
    r3 = avaliar_alertas(d3, hoje=hoje)
    assert r3["estado_novo"]["regras"]["manual:ITSA4:compra"]["ativo"] is True
    assert r3["estado_novo"]["regras"]["manual:TESOURO-IPCA-2032:taxa"]["ativo"] is True

    # 4b. Sai da faixa além da histerese (> +1% no preço e < -0,05 p.p. na taxa) -> reseta
    d4 = copy.deepcopy(d1)
    d4["estado"] = r3["estado_novo"]
    d4["precos"]["ITSA4"] = 13.20  # > 13.13 -> sai
    d4["tesouro"]["titulos"][0]["taxaCompra"] = 7.40  # < 7.45 -> sai
    r4 = avaliar_alertas(d4, hoje=hoje)
    assert r4["estado_novo"]["regras"]["manual:ITSA4:compra"]["ativo"] is False
    assert r4["estado_novo"]["regras"]["manual:TESOURO-IPCA-2032:taxa"]["ativo"] is False

    # 4c. Volta para dentro da faixa -> dispara novamente!
    d5 = copy.deepcopy(d1)
    d5["estado"] = r4["estado_novo"]
    r5 = avaliar_alertas(d5, hoje=hoje)
    ids5 = {x["id"] for x in r5["novos"]}
    assert "manual:ITSA4:compra" in ids5 and "manual:TESOURO-IPCA-2032:taxa" in ids5, f"Deveria voltar a disparar: {ids5}"

    # 5. Preço velho (> 3 dias) bloqueia oportunidades e avisa "preços parados"
    d6 = copy.deepcopy(d1)
    d6["meta_mercado"]["gerado"] = "2026-11-20 18:00"  # 5 dias antes de 2026-11-25
    r6 = avaliar_alertas(d6, hoje=hoje)
    assert r6["bloqueado_preco_velho"] is True
    assert "preços parados" in (r6["mensagem"] or "").lower(), r6["mensagem"]
    assert not any(x["id"].startswith(("manual:", "auto:")) for x in r6["novos"])

    # 6. Padrão de token do Telegram no checar_segredos.py
    tok_fake = "123456789:AA" + ("B" * 33)
    assert any(p.search(tok_fake) for p in PADROES), "checar_segredos.py não detectou padrão Telegram"

    print("OK alertas_test: 6/6 cenários passaram (disparo, não disparo, anti-spam, histerese ida/volta, preço velho >3d, regex segredo Telegram).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
