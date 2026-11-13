// Rodada 20 Parte E + Parte F: Resultado recorrente de FIIs e veredito do Onde Aportar Hoje
return (async () => {
  const orig = JSON.parse(JSON.stringify(window.FEHMIR_FII_RESULTADO || {}));
  const casos = [];
  const falhasLista = [];

  function check(nome, ok, detalhe) {
    casos.push({ nome, ok: !!ok, detalhe });
    if (!ok) falhasLista.push(`${nome}: ${detalhe}`);
  }

  try {
    if (typeof window.limparCacheTetoOficial === 'function') window.limparCacheTetoOficial();

    // Caso 1: TRXF11 com o arquivo real
    const avTrxf = window.tetoOficial('TRXF11');
    const reqTrxf = avTrxf.req || avTrxf.taxa;
    const tetoEspTrxf = 8.64 / (reqTrxf / 100);
    const recTrxf = avTrxf.recorrente;
    check(
      '1. TRXF11 teto pelo recorrente e inflado 0,21',
      avTrxf && Math.abs(avTrxf.teto - tetoEspTrxf) <= 0.02 && recTrxf && Math.abs(recTrxf.inflado - 0.21) <= 0.001,
      `teto=${avTrxf?.teto?.toFixed(2)} (esp=${tetoEspTrxf.toFixed(2)}), inflado=${recTrxf?.inflado?.toFixed(2)}`
    );

    // Caso 2: GARE11 sem dado continua pelo pago
    const avGare = window.tetoOficial('GARE11');
    const hGare = typeof fehmirObterHist === 'function' ? fehmirObterHist('GARE11') : (window.FEHMIR_HIST && window.FEHMIR_HIST['GARE11']);
    const fiiGare = (typeof FIIS !== 'undefined' ? FIIS.find(f => f.t === 'GARE11') : null) || {};
    const rendaGare = (hGare && hGare.dpa12 > 0) ? hGare.dpa12 : (fiiGare.rend ? fiiGare.rend * 12 : fiiGare.dpa);
    const tetoPagoGare = rendaGare / ((avGare.req || avGare.taxa) / 100);
    check(
      '2. GARE11 sem dado mantém teto pelo pago',
      avGare && !avGare.recorrente && Math.abs(avGare.teto - tetoPagoGare) <= 0.02,
      `teto=${avGare?.teto?.toFixed(2)} (esp=${tetoPagoGare.toFixed(2)}), recorrente=${avGare?.recorrente}`
    );

    // Caso 3: Fixture de mês fora da janela (hoje = 2027-03-01 para 2026-08) -> null
    const recForaJanela = window.fehmirRecorrenteFii('TRXF11', 10.87, 67.38, 12.2, '2027-03-01');
    check(
      '3. Mês fora da janela de 6 meses retorna null',
      recForaJanela === null,
      `retorno=${JSON.stringify(recForaJanela)}`
    );

    // Caso 4: Fixture com recorrente >= pago -> null (teto não sobe)
    window.FEHMIR_FII_RESULTADO['TEST11'] = [
      { mes: '2026-08', pago: 0.80, recorrente: 0.85, naoRecorrente: 0, origem: 'aluguéis', conferido: true }
    ];
    const recMaior = window.fehmirRecorrenteFii('TEST11', 9.60, 100, 10, '2026-11-03');
    check(
      '4. Recorrente >= pago retorna null',
      recMaior === null,
      `retorno=${JSON.stringify(recMaior)}`
    );

    // Caso 5: Fixture com 2 meses (0,70 e 0,74 gerados, 0,93 pagos) -> recMes 0,72
    window.FEHMIR_FII_RESULTADO['TEST2M11'] = [
      { mes: '2026-07', pago: 0.93, recorrente: 0.70, naoRecorrente: 0.23, origem: 'venda de imóveis', conferido: false },
      { mes: '2026-08', pago: 0.93, recorrente: 0.74, naoRecorrente: 0.19, origem: 'venda de imóveis', conferido: false }
    ];
    const rec2m = window.fehmirRecorrenteFii('TEST2M11', 10.87, 67.38, 12.2, '2026-11-03');
    check(
      '5. Fixture com 2 meses (0,70 e 0,74) -> recMes = 0,72',
      rec2m !== null && Math.abs(rec2m.recMes - 0.72) <= 0.001,
      `recMes=${rec2m?.recMes}`
    );

    // Caso 6: Texto da fonte do TRXF11 contém "R$ 0,21", "ago/26", "12,8%" e "16,1%"
    const srcTxt = avTrxf?.src || '';
    const temTokens = ['R$ 0,21', 'ago/26', '12,8%', '16,1%'].every(tok => srcTxt.includes(tok));
    check(
      '6. Texto da fonte do TRXF11 contém R$ 0,21, ago/26, 12,8% e 16,1%',
      temTokens,
      `src="${srcTxt}"`
    );

    // Caso 7 (Parte F): calcularAporteInteligente com R$ 211 só inclui ativos com veredito "Aportar"
    // Fixture: força o preço de TAEE11 para 36,00 (e status 'good') para garantir que ela entra na cesta (veredito "Aportar")
    const taeeItem = (typeof BASE_STOCKS !== 'undefined') ? BASE_STOCKS.find(s => s && s.t === 'TAEE11') : null;
    const pAntTaee = taeeItem ? taeeItem.preco : null;
    const stAntTaee = taeeItem ? taeeItem.status : null;
    if (taeeItem) {
      taeeItem.preco = 36.00;
      taeeItem.status = 'good';
    }
    if (typeof window.limparCacheTetoOficial === 'function') window.limparCacheTetoOficial();

    const inpAp = document.getElementById('smart-aporte-val') || document.getElementById('smart-aporte-input');
    const valAnt = inpAp ? inpAp.value : '300';
    if (inpAp) inpAp.value = '211';
    const resAp = window.calcularAporteInteligente ? window.calcularAporteInteligente() : null;
    const cesta = (resAp && Array.isArray(resAp.cesta)) ? resAp.cesta : [];
    const naoAportar = cesta.filter(item => {
      const v = window.fehmirVeredito({ t: item.t, preco: item.preco });
      return !v || v.label !== 'Aportar';
    });
    const foraTxt = document.getElementById('smart-aporte-fora-cesta')?.textContent || '';
    if (inpAp) { inpAp.value = valAnt; window.calcularAporteInteligente(); }
    if (taeeItem) {
      if (pAntTaee != null) taeeItem.preco = pAntTaee;
      if (stAntTaee != null) taeeItem.status = stAntTaee;
    }
    if (typeof window.limparCacheTetoOficial === 'function') window.limparCacheTetoOficial();

    check(
      '7. Parte F: com R$ 211 e TAEE11 a 36,00, ela entra na cesta, nenhum ativo da cesta tem veredito != Aportar e BBSE3 aparece fora da cesta',
      cesta.length > 0 && cesta.some(x => x.t === 'TAEE11') && naoAportar.length === 0 && !cesta.some(x => x.t === 'BBSE3') && foraTxt.includes('BBSE3'),
      `cesta=${cesta.map(x => x.t).join(',')}, naoAportar=${naoAportar.map(x => x.t).join(',')}, foraTxt="${foraTxt}"`
    );
  } finally {
    window.FEHMIR_FII_RESULTADO = orig;
    if (typeof window.limparCacheTetoOficial === 'function') window.limparCacheTetoOficial();
  }

  return { falhas: falhasLista.length, falhasLista, casos };
})();

