// Rodada 32: Classe Renda fixa longo prazo (Tesouro IPCA+) + robô da taxa (dados/tesouro.js)
return (async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const casos = [];
  const falhasLista = [];
  const check = (nome, ok, detalhe) => {
    casos.push({ nome, ok: !!ok, detalhe });
    if (!ok) falhasLista.push(`${nome}: ${detalhe}`);
  };
  const parseBRL = txt => {
    const m = String(txt || '').match(/R\$\s*([\d.]+,\d{2})/);
    return m ? parseFloat(m[1].replace(/\./g, '').replace(',', '.')) : null;
  };

  const tesOrig = window.FEHMIR_TESOURO ? JSON.parse(JSON.stringify(window.FEHMIR_TESOURO)) : null;
  const macroOrig = localStorage.getItem('barsi-macro-v1');
  const abertosOrig = localStorage.getItem('barsi-ma-abertos');

  try {
    // 1. Metas de alocação somam 100% com rf=5 e fiis=32
    const somaMetas = ALOCACAO_ALVO.acoes + ALOCACAO_ALVO.fiis + ALOCACAO_ALVO.intl + ALOCACAO_ALVO.cripto + ALOCACAO_ALVO.rf + ALOCACAO_ALVO.caixa;
    check('1. ALOCACAO_ALVO rf=5, fiis=32 e soma=100%',
      ALOCACAO_ALVO.rf === 5 && ALOCACAO_ALVO.fiis === 32 && somaMetas === 100,
      `rf=${ALOCACAO_ALVO.rf}, fiis=${ALOCACAO_ALVO.fiis}, soma=${somaMetas}`);

    // 2. TESOURO-IPCA-2032 fora das tabelas de ações/FIIs/Radar e sem teto
    const foraAcoesRadar = ![...BASE_STOCKS, ...OUT_OF_BASE, ...FIIS, ...(typeof RADAR_DATA !== 'undefined' ? RADAR_DATA : [])].some(x => x && x.t === 'TESOURO-IPCA-2032');
    check('2. TESOURO-IPCA-2032 não entra em B.A.S.E., FIIs ou Radar', foraAcoesRadar, '');

    // 3. Mesmo valor de mercado nas 3 telas (Visão geral, Rebalanceamento e Extrato) + reage ao PU do robô
    const puTeste = 3500.00;
    if (window.FEHMIR_TESOURO && Array.isArray(window.FEHMIR_TESOURO.titulos)) {
      const tit = window.FEHMIR_TESOURO.titulos.find(t => t.ticker === 'TESOURO-IPCA-2032');
      if (tit) { tit.puVenda = puTeste; tit.puCompra = puTeste + 20; } // valor de mercado = PU de resgate (venda)
    }
    const pos = calcularPosicoesExtrato(carregarExtrato());
    const qRf = pos['TESOURO-IPCA-2032'] ? pos['TESOURO-IPCA-2032'].quant : 0;
    const espSaldo = Number((qRf * puTeste).toFixed(2));

    // Visão geral: alocação + Meus Ativos
    const alloc = obterDadosAlocacaoClasses();
    const vgRf = alloc.saldoRf;
    localStorage.setItem('barsi-ma-abertos', JSON.stringify({ 'RENDA FIXA': true }));
    switchMainTab('ativos');
    setCarteiraView('geral');
    renderMeusAtivos();
    await sleep(150);
    const maRow = [...document.querySelectorAll('#ma-body tr')].find(tr => (tr.textContent || '').includes('TESOURO-IPCA-2032'));
    const maSaldo = maRow ? parseBRL(maRow.children[6]?.textContent) : null;

    // Rebalanceamento
    setCarteiraView('rebal');
    await sleep(150);
    const rebRow = [...document.querySelectorAll('#tbody-rebalanceamento tr')].find(tr => (tr.textContent || '').includes('TESOURO-IPCA-2032'));
    const rebSaldo = rebRow ? parseBRL(rebRow.children[3]?.textContent) : null;

    // Extrato
    setCarteiraView('extrato');
    await sleep(150);
    const extRow = [...document.querySelectorAll('#tbody-extrato-transacoes tr')].find(tr => (tr.textContent || '').includes('TESOURO-IPCA-2032'));
    const fehmirPos = FEHMIR.posicoes()['TESOURO-IPCA-2032'];
    const extMerc = fehmirPos ? Number((fehmirPos.quant * obterPrecoAtivo('TESOURO-IPCA-2032').preco).toFixed(2)) : null;

    check('3. TESOURO-IPCA-2032 presente nas 3 telas com mesmo valor de mercado',
      qRf > 0 && Math.abs(vgRf - espSaldo) <= 0.02 && maSaldo != null && Math.abs(maSaldo - espSaldo) <= 0.02 &&
      rebSaldo != null && Math.abs(rebSaldo - espSaldo) <= 0.02 && !!extRow && Math.abs(extMerc - espSaldo) <= 0.02,
      `q=${qRf}, esp=${espSaldo}, vg=${vgRf}, ma=${maSaldo}, reb=${rebSaldo}, extMerc=${extMerc}, extRow=${!!extRow}`);

    // 4. Fallback sem dados/tesouro.js -> marca "estimado"
    window.FEHMIR_TESOURO = undefined;
    const pEst = obterPrecoAtivo('TESOURO-IPCA-2032');
    check('4. Sem dados/tesouro.js, fallback devolve estimado=true e preço positivo',
      pEst && pEst.estimado === true && pEst.preco > 0, JSON.stringify(pEst));
    window.FEHMIR_TESOURO = tesOrig ? JSON.parse(JSON.stringify(tesOrig)) : undefined;

    // 5. Rebalanceamento: sugere fatia (R$ 40-50) quando taxa >= 7.5%, e NÃO sugere quando < 6.5%
    setCarteiraView('rebal');
    const inpAp = document.getElementById('smart-aporte-val');
    const apAnt = inpAp ? inpAp.value : '300';
    if (inpAp) inpAp.value = '250';
    calcularAporteInteligente();
    const boxSugAlta = document.getElementById('smart-aporte-rf-sugestao');
    const sugOk = !!boxSugAlta && /40|45|50/.test(boxSugAlta.textContent);

    if (window.FEHMIR_TESOURO && Array.isArray(window.FEHMIR_TESOURO.titulos)) {
      window.FEHMIR_TESOURO.titulos.forEach(t => { if (t.nome === 'Tesouro IPCA+') t.taxaCompra = 6.20; });
    }
    calcularAporteInteligente();
    const boxSugBaixa = document.getElementById('smart-aporte-rf-sugestao');
    if (inpAp) { inpAp.value = apAnt; }
    check('5. Rebalanceamento sugere R$ 40-50 quando taxa >= 7,5% e suprime quando < 6,5%',
      sugOk && !boxSugBaixa, `alta=${boxSugAlta && boxSugAlta.textContent.slice(0, 90)} | baixa=${!!boxSugBaixa}`);

    // 6. Conselheiro: ntnb vindo do robô + alertas >= 8% e < 6,5%
    window.FEHMIR_TESOURO = tesOrig ? JSON.parse(JSON.stringify(tesOrig)) : undefined;
    const mLive = loadMacro();
    const ntnbRoboOk = tesOrig ? Math.abs(mLive.ntnb - tesOrig.ntnbMediana) < 0.001 : true;

    if (window.FEHMIR_TESOURO && Array.isArray(window.FEHMIR_TESOURO.titulos)) {
      const t35 = window.FEHMIR_TESOURO.titulos.find(t => t.nome === 'Tesouro IPCA+' && String(t.vencimento).startsWith('2035'));
      if (t35) t35.taxaCompra = 8.15;
    }
    switchMainTab('conselheiro');
    renderConselheiro();
    await sleep(150);
    const alAltaTxt = document.getElementById('cb-alertas')?.textContent || '';
    const alerta8Ok = alAltaTxt.includes('boa hora para a fatia de renda fixa') && alAltaTxt.includes('8%');

    if (window.FEHMIR_TESOURO && Array.isArray(window.FEHMIR_TESOURO.titulos)) {
      window.FEHMIR_TESOURO.titulos.forEach(t => { if (t.nome === 'Tesouro IPCA+') t.taxaCompra = 6.10; });
    }
    const mm = JSON.parse(localStorage.getItem('barsi-macro-v1') || '{}');
    mm.ntnb = 6.10;
    localStorage.setItem('barsi-macro-v1', JSON.stringify(mm));
    renderConselheiro();
    await sleep(150);
    const alBaixaTxt = document.getElementById('cb-alertas')?.textContent || '';
    const alerta65Ok = alBaixaTxt.includes('abaixo de 6,5%');

    check('6. Conselheiro usa ntnb do robô e dispara alertas >= 8% e < 6,5%',
      ntnbRoboOk && alerta8Ok && alerta65Ok,
      `ntnbOk=${ntnbRoboOk}(${mLive.ntnb}/${tesOrig && tesOrig.ntnbMediana}), alerta8Ok=${alerta8Ok}, alerta65Ok=${alerta65Ok}`);
  } finally {
    if (tesOrig) window.FEHMIR_TESOURO = tesOrig;
    if (macroOrig != null) localStorage.setItem('barsi-macro-v1', macroOrig);
    else localStorage.removeItem('barsi-macro-v1');
    if (abertosOrig != null) localStorage.setItem('barsi-ma-abertos', abertosOrig);
    else localStorage.removeItem('barsi-ma-abertos');
    if (typeof window.limparCacheTetoOficial === 'function') window.limparCacheTetoOficial();
  }

  return { falhas: falhasLista.length, falhasLista, casos };
})();
