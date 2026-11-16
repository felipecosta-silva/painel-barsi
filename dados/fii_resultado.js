/* Resultado recorrente dos FIIs que pagam mais do que geram — preenchido pelo Assistente a partir de relatório gerencial ou resumo de vídeo.
   Por mês e por cota: pago = rendimento distribuído; recorrente = aluguéis e juros menos despesas, sem lucro de venda de imóvel;
   naoRecorrente = o que veio de venda de imóvel, ganho de capital ou reserva; origem = de onde veio.
   Só entram fundos e meses com o dado lido em fonte datada. conferido: false = fonte secundária (vídeo), conferir no relatório no Fundos.NET. */
window.FEHMIR_FII_RESULTADO = {
  "XPML11": [
    { mes: "2026-10", pago: 0.92, recorrente: 0.79, naoRecorrente: 0.13, origem: "reserva acumulada",
      fonte: "Guidance novo de R$ 0,74–0,84 (ponto médio 0,79) citado no vídeo TioFIIs de 11/11/2026; vídeo Eric Leonardo (Liberdade é Logo Ali) de 16/11/2026 (01:46) estima recorrente ~R$ 0,80 e mostra setembro com R$ 0,92 pago contra R$ 0,50 de caixa operacional (05:05) e reserva de R$ 0,95 por cota", conferido: false }
  ],
  "TRXF11": [
    { mes: "2026-08", pago: 0.93, recorrente: 0.72, naoRecorrente: 0.21, origem: "venda de imóveis",
      fonte: "Vídeo Bruno Chimarelli de 02/11/2026 (07:46), citando o relatório gerencial de agosto", conferido: false }
  ]
};
