// Regras manuais de alerta do Painel Barsi (Rodada 32-B)
// CMIG4, VALE3 e PMLL11 foram omitidos conforme revisão 32: o robô cobre automaticamente via preço <= compra do dados/tetos.js.
window.FEHMIR_ALERTAS_REGRAS = {
  atualizado: "2026-11-25",
  // Regra automática (preço <= compra do tetos.js) vale só para a carteira + esta lista.
  vigiar: ["CMIG4", "VALE3", "PMLL11"],
  // Decisões que bloqueiam o alerta automático (revisar quando o motivo cair).
  silenciar: {
    "TRXF11:compra": "acima de 5% da carteira e recorrente R$ 0,63 contra R$ 0,93 pago; esperar o relatório de nov/26",
    "RZAG11:compra": "sem folga; esperar o relatório de out/26 (Uniggel em RJ)",
    "PETR4:venda": "teto do Léo (38,10) entra na Rodada 33; não realizar pelo 26,15"
  },
  regras: [
    {
      id: "manual:ITSA4:compra",
      ticker: "ITSA4",
      tipo: "compra",
      condicao: "<=",
      valor: 13.00,
      texto: "compra 2–3 ações (Felipe já comprou 2 a R$ 12,99 em 24/11)",
      fonte: "decisão Felipe / Rodada 31-32"
    },
    {
      id: "manual:VISC11:compra",
      ticker: "VISC11",
      tipo: "compra",
      condicao: "<=",
      valor: 91.65,
      texto: "até 2 cotas (reposição de shopping)",
      fonte: "dossiê VISC11 / Rodada 31"
    },
    {
      id: "manual:TAEE11:compra",
      ticker: "TAEE11",
      tipo: "compra",
      condicao: "<=",
      valor: 31.00,
      texto: "gatilho com desconto após revisão da alavancagem",
      fonte: "dossiê TAEE11 / Rodada 31"
    },
    {
      id: "manual:BBSE3:compra",
      ticker: "BBSE3",
      tipo: "compra",
      condicao: "<=",
      valor: 35.50,
      texto: "ordem oportunística",
      fonte: "dossiê BBSE3 / Rodada 31"
    },
    {
      id: "manual:ISAE4:compra",
      ticker: "ISAE4",
      tipo: "compra",
      condicao: "<=",
      valor: 18.15,
      texto: "ordem aberta",
      fonte: "dossiê ISAE4 / Rodada 31"
    },
    {
      id: "manual:PSSA3:compra",
      ticker: "PSSA3",
      tipo: "compra",
      condicao: "<=",
      valor: 36.08,
      texto: "margem corrigida (aguardar 4T26 ou desconto)",
      fonte: "dossiê PSSA3 / Rodada 31"
    },
    {
      id: "manual:WEGE3:compra",
      ticker: "WEGE3",
      tipo: "compra",
      condicao: "<=",
      valor: 42.00,
      texto: "compounder com margem",
      fonte: "dossiê WEGE3 / Rodada 31"
    },
    {
      id: "manual:TESOURO-IPCA-2032:taxa",
      ticker: "TESOURO-IPCA-2032",
      tipo: "taxa",
      condicao: ">=",
      valor: 7.50,
      texto: "aporte R$ 40–50 até a meta de 5%",
      fonte: "Rodada 32 / Tesouro IPCA+"
    }
  ]
};
