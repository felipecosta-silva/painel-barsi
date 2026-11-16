/* Resultado recorrente dos FIIs que pagam mais do que geram — preenchido pelo Assistente a partir de relatório gerencial ou resumo de vídeo.
   Por mês e por cota: pago = rendimento distribuído; recorrente = aluguéis e juros menos despesas, sem lucro de venda de imóvel;
   naoRecorrente = o que veio de venda de imóvel, ganho de capital ou reserva; origem = de onde veio.
   Só entram fundos e meses com o dado lido em fonte datada. conferido: false = fonte secundária (vídeo), conferir no relatório no Fundos.NET. */
window.FEHMIR_FII_RESULTADO = {
  "XPML11": [
    { mes: "2026-09", pago: 0.92, recorrente: 0.50, naoRecorrente: 0.42, origem: "reserva acumulada",
      fonte: "Vídeos de 16/11/2026: André (Mestre da Riqueza, 06:28) — receita operacional líquida R$ 32,3 mi contra R$ 59,1 mi distribuídos em set/26 (~64,2 mi cotas ⇒ R$ 0,50/cota); Eric Leonardo (05:05) — R$ 0,50 de caixa; reserva caiu de R$ 4,12 (jan) para R$ 0,95/cota (set)", conferido: false },
    { mes: "2026-10", pago: 0.92, recorrente: 0.79, naoRecorrente: 0.13, origem: "reserva acumulada",
      fonte: "ESTIMATIVA, não medido: ponto médio do guidance novo de R$ 0,74–0,84 (vídeos TioFIIs 11/11 e André 16/11), já com as aquisições de Tatuapé e Itaquera. Trocar pelo resultado real do relatório gerencial de outubro", conferido: false }
  ],
  "TRXF11": [
    { mes: "2026-08", pago: 0.93, recorrente: 0.72, naoRecorrente: 0.21, origem: "venda de imóveis",
      fonte: "Vídeo Bruno Chimarelli de 02/11/2026 (07:46), citando o relatório gerencial de agosto", conferido: false }
  ]
};
