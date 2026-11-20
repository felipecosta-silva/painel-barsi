/* Resultado recorrente dos FIIs que pagam mais do que geram — preenchido pelo Assistente a partir de relatório gerencial ou resumo de vídeo.
   Por mês e por cota: pago = rendimento distribuído; recorrente = aluguéis e juros menos despesas, sem lucro de venda de imóvel;
   naoRecorrente = o que veio de venda de imóvel, ganho de capital ou reserva; origem = de onde veio.
   Só entram fundos e meses com o dado lido em fonte datada. conferido: false = fonte secundária (vídeo), conferir no relatório no Fundos.NET. */
window.FEHMIR_FII_RESULTADO = {
  "GGRC11": [
    { mes: "2026-09", pago: 0.10, recorrente: 0.096, naoRecorrente: 0.004, origem: "reserva acumulada",
      fonte: "Vídeo Maicon Trindade (Investidor de Fábrica) de 16/11/2026 (03:38–03:50): gera R$ 0,096/cota e usa R$ 0,004 de reserva; vídeo Beca Alcântara de 16/11 usa dados de set/26 (PL ~R$ 4 bi). O número 'R$ 9,32 mi × R$ 10,58 mi' da imprensa (usado antes) é de quando o fundo era ~3,5× menor e foi descartado", conferido: false }
  ],
  "XPML11": [
    { mes: "2026-09", pago: 0.92, recorrente: 0.50, naoRecorrente: 0.42, origem: "reserva acumulada",
      fonte: "Vídeos de 16/11/2026: André (Mestre da Riqueza, 06:28) — receita operacional líquida R$ 32,3 mi contra R$ 59,1 mi distribuídos em set/26 (~64,2 mi cotas ⇒ R$ 0,50/cota); Eric Leonardo (05:05) — R$ 0,50 de caixa; reserva caiu de R$ 4,12 (jan) para R$ 0,95/cota (set)", conferido: false }
  ],
  "TRXF11": [
    { mes: "2026-08", pago: 0.93, recorrente: 0.72, naoRecorrente: 0.21, origem: "venda de imóveis",
      fonte: "Vídeo Bruno Chimarelli de 02/11/2026 (07:46), citando o relatório gerencial de agosto", conferido: false },
    { mes: "2026-10", pago: 0.93, recorrente: 0.63, naoRecorrente: 0.30, origem: "reserva acumulada",
      fonte: "Resultado operacional de out/26 R$ 60,54 mi = R$ 0,63/cota (fiis.com.br) e vídeo André Train (Clube do Valor) de 19/11/2026 (0:14): gerou 0,63, pagou 0,93; reserva caiu de R$ 35 mi (jul) para R$ 3,5 mi (out)", conferido: false }
  ],
  "HGBS11": [
    { mes: "2026-10", pago: 0.17, recorrente: 0.123, naoRecorrente: 0.047, origem: "lucro de vendas acumulado (Jardim Sul 19%, I Fashion Outlet)",
      fonte: "Relatório gerencial de out/26 (Fundos.NET id 1388726): resultado operacional R$ 19,07 mi = R$ 0,123/cota (receita imobiliária 0,154 + outras 0,012 − despesas 0,042); resultado total 0,116; média 2026 do operacional R$ 0,143/cota; reserva R$ 0,071/cota após out; guidance de 0,17 só para 2026", conferido: true }
  ]
};
