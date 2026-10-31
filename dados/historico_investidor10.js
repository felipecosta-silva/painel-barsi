/* Histórico da carteira do Felipe antes do painel, copiado dos prints do Investidor10 que ele mandou em 31/10/2026.
   Fonte: investidor10.com.br (Carteira 1) — Proventos › Histórico mensal; Patrimônio › tooltips da Evolução; Rentabilidade › tabela mensal.
   Só dado lido na tela, nada estimado. O painel usa estes meses só ANTES da carga própria (30/09/2026);
   de 10/2026 em diante vale o cálculo do painel (extrato + robô). */
window.FEHMIR_I10 = {
  fonte: "Investidor10 (prints de 31/10/2026)",
  // proventos recebidos por mês (data de pagamento)
  proventos: {
    "2025-04": 0.04, "2025-05": 22.34, "2025-06": 21.54, "2025-07": 21.41, "2025-08": 34.54, "2025-09": 29.68,
    "2025-10": 30.22, "2025-11": 35.89, "2025-12": 36.44,
    "2026-01": 34.30, "2026-02": 32.14, "2026-03": 43.01, "2026-04": 31.78, "2026-05": 39.08, "2026-06": 38.11,
    "2026-07": 39.35, "2026-08": 38.28, "2026-09": 45.27, "2026-10": 39.97
  },
  // fim de mês: patrimônio (mercado) e valor aplicado; meses sem tooltip enviado ficam de fora
  patrimonio: [
    { mes: "2026-01", mercado: 4015.72, aplicado: 3748.26 },
    { mes: "2026-02", mercado: 4144.83, aplicado: 3839.39 },
    { mes: "2026-03", mercado: 4218.23, aplicado: 3959.07 },
    { mes: "2026-04", mercado: 4304.46, aplicado: 4021.24 },
    { mes: "2026-05", mercado: 4183.03, aplicado: 4044.23 },
    { mes: "2026-06", mercado: 4146.86, aplicado: 4086.41 },
    { mes: "2026-07", mercado: 4319.57, aplicado: 4234.18 },
    { mes: "2026-08", mercado: 4628.74, aplicado: 4642.19 }
  ],
  // compras (c) e vendas (v) por mês — Lançamentos › Consolidação de aportes.
  // 2025: lido do gráfico (aprox., ±R$ 15). 02–08/2026: variação do valor aplicado (meses sem venda). 09/2026: soma da lista de lançamentos.
  aportes: {
    "2025-04": { c: 1760, v: 0, aprox: true }, "2025-05": { c: 740, v: 90, aprox: true }, "2025-06": { c: 410, v: 20, aprox: true },
    "2025-07": { c: 1080, v: 0, aprox: true }, "2025-08": { c: 660, v: 520, aprox: true }, "2025-09": { c: 360, v: 510, aprox: true },
    "2025-10": { c: 200, v: 90, aprox: true }, "2025-11": { c: 0, v: 320, aprox: true }, "2025-12": { c: 0, v: 0 },
    "2026-01": { c: 0, v: 0 }, "2026-02": { c: 91.13, v: 0 }, "2026-03": { c: 119.68, v: 0 }, "2026-04": { c: 62.17, v: 0 },
    "2026-05": { c: 22.99, v: 0 }, "2026-06": { c: 42.18, v: 0 }, "2026-07": { c: 147.77, v: 0 }, "2026-08": { c: 408.01, v: 0 },
    "2026-09": { c: 653.45, v: 0 }
  },
  // rentabilidade mensal da carteira (%)
  rentabilidade: {
    "2025-04": 3.83, "2025-05": 1.62, "2025-06": 0.97, "2025-07": -1.33, "2025-08": 1.71, "2025-09": 2.09,
    "2025-10": 0.91, "2025-11": 3.20, "2025-12": 0.97,
    "2026-01": 3.15, "2026-02": 1.72, "2026-03": -0.03, "2026-04": 1.24, "2026-05": -2.41, "2026-06": -0.88,
    "2026-07": 1.48, "2026-08": -1.52, "2026-09": 0.29, "2026-10": 0.70
  }
};
// Formato que o gráfico de evolução já lê (meses antes da carga do painel)
window.FEHMIR_PATR_HIST = window.FEHMIR_I10.patrimonio.map(x => Object.assign({ fonte: window.FEHMIR_I10.fonte }, x));
