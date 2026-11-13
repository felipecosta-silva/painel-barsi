/* Registro de vendas de ativos de imobiliárias de renda (spec 010, FR-009). Só o Claude edita, com fonte primária.
   Formato: "TICKER": [ { data: "AAAA-MM-DD", venda: <R$>, contabil: <R$>, fonte: "https://..." } ]
   Com ≥ 1 venda nos últimos 24 meses e todas a ≥ 90% do valor contábil, o teto passa a ser VPA × 0,9. */
window.FEHMIR_VENDAS_ATIVOS = {};
