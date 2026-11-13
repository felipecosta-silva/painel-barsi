// Spec 009 Fase A: ordens abertas (US1, FR-025 "só hoje"), preço velho (US2), cópia que acrescenta (FR-015) e aporte do mês (US4).
// Uso: node tools/testes/cdp.js tools/testes/ordens_e_precos.js   (ou pelo run_all.js)
return (async () => {
  const casos = [];
  const falhasLista = [];
  const info = {};
  function check(nome, ok, detalhe) {
    casos.push({ nome, ok: !!ok, detalhe });
    if (!ok) falhasLista.push(`${nome}: ${detalhe}`);
  }
  const perto = (a, b, tol) => a != null && Math.abs(a - b) <= tol;
  const iso = d => d.toISOString().slice(0, 10);
  const espera = ms => new Promise(r => setTimeout(r, ms));

  // Preço forçado por ticker (o resto segue o preço real)
  const precoOrig = window.FEHMIR.preco;
  const forcados = {};
  window.FEHMIR.preco = (t, d) => (forcados[t] != null ? { preco: forcados[t] } : precoOrig(t, d));
  const fetchOrig = window.fetch;

  try {
    // ---------- T005: fundação ----------
    check('T005 idade 29/10 → 05/11 10h = 3 dias úteis',
      fehmirIdadeUteis('2026-10-29', new Date('2026-11-05T10:00:00-03:00')) === 3,
      `obtido ${fehmirIdadeUteis('2026-10-29', new Date('2026-11-05T10:00:00-03:00'))}`);
    check('T005 02/11 não é dia útil', fehmirDiaUtilB3('2026-11-02') === false, '');
    check('T005 20/11 não é dia útil', fehmirDiaUtilB3('2026-11-20') === false, '');
    check('T005 08/02/2027 (Carnaval) não é dia útil', fehmirDiaUtilB3('2027-02-08') === false, '');
    check('T005 06/11 é dia útil', fehmirDiaUtilB3('2026-11-06') === true, '');
    const extIni = carregarExtrato().length;
    info.extratoPerfilLimpo = extIni;
    check('T005 Extrato do perfil limpo carrega', extIni > 0, `tamanho ${extIni}`);
    const so0 = fehmirLancSoNesteNavegador();
    adicionarTransacao({ id: 'teste-manual-1', data: '2026-11-04', tipo: 'Compra', ticker: 'ITSA4', cat: 'AÇÕES', quant: 1, preco: 13, taxa: 0, total: 13, moeda: 'BRL' });
    const so1 = fehmirLancSoNesteNavegador();
    const seloTxt = document.body.textContent || '';
    check('T020(d) perfil limpo 0; com 1 lançamento manual ⇒ 1 e selo visível',
      so0 === 0 && so1 === 1 && /1 lançamentos? só neste navegador/.test(seloTxt), `antes=${so0} depois=${so1}`);

    // ---------- T012: ordens ----------
    fehmirGravarOrdens([]);
    // (a)
    const sa = fehmirOrdemSalvar({ t: 'BBSE3', quant: 2, limite: 37.14, validade: '2026-11-25', origem: 'reserva' });
    forcados.BBSE3 = 37.55;
    const oa = fehmirOrdens().find(o => o.id === (sa.ordem && sa.ordem.id));
    const ra = fehmirOrdensResumo();
    check('T012(a) BBSE3 salva, distância 1,1% e reserva 74,28',
      sa.ok && oa && perto(oa.distancia, 1.1, 0.05) && perto(ra.porOrigem.reserva, 74.28, 0.001),
      `ok=${sa.ok} dist=${oa && oa.distancia} reserva=${ra.porOrigem.reserva}`);

    // (b) clique real em Executou
    const posAntes = (FEHMIR.posicoes()['BBSE3'] || {}).quant || 0;
    renderOrdensAbertas();
    const btnExec = document.querySelector(`.btn-ordem-executar[data-ordem-id="${sa.ordem.id}"]`);
    if (btnExec) btnExec.click();
    document.getElementById('exec-ordem-quant').value = '2';
    document.getElementById('exec-ordem-preco').value = '37.14';
    document.getElementById('exec-ordem-taxa').value = '0.02';
    const btnConf = document.getElementById('btn-confirmar-execucao-ordem');
    btnConf.click();
    btnConf.click();
    fehmirOrdemExecutar(sa.ordem.id, { quant: 2, preco: 37.14, taxa: 0.02 });
    const posDepois = (FEHMIR.posicoes()['BBSE3'] || {}).quant || 0;
    const lancOrdem = carregarExtrato().filter(t => String(t.id || '').startsWith('ordem-'));
    check('T012(b) clique real: posição +2 e exatamente 1 lançamento "ordem-"',
      !!btnExec && Math.abs(posDepois - posAntes - 2) < 1e-9 && lancOrdem.length === 1 && Math.abs(lancOrdem[0].total - 74.30) < 0.001,
      `botão=${!!btnExec} pos ${posAntes}→${posDepois} lanc=${lancOrdem.length} total=${lancOrdem[0] && lancOrdem[0].total}`);

    // (c) parcial
    const sc = fehmirOrdemSalvar({ t: 'TAEE11', quant: 2, limite: 38.62, validade: '2026-11-25', origem: 'aporte' });
    fehmirOrdemExecutar(sc.ordem.id, { quant: 1, preco: 38.62, taxa: 0 });
    const oc = fehmirOrdens().find(o => o.id === sc.ordem.id);
    check('T012(c) 1 de 2 executada ⇒ parcial e comprometido = 1 × limite',
      oc && oc.situacao === 'parcial' && perto(oc.comprometido, 38.62, 0.001),
      `situacao=${oc && oc.situacao} comprometido=${oc && oc.comprometido}`);

    // (d) cancelar
    const extAntesCanc = carregarExtrato().length;
    fehmirOrdemCancelar(sc.ordem.id);
    const abertasD = fehmirOrdens().filter(o => o.situacao === 'aberta' || o.situacao === 'parcial');
    check('T012(d) cancelar tira das abertas e não mexe no Extrato',
      !abertasD.some(o => o.id === sc.ordem.id) && carregarExtrato().length === extAntesCanc,
      `abertas=${abertasD.map(o => o.t)} extrato ${extAntesCanc}→${carregarExtrato().length}`);

    // (e) vencida
    const ontem = new Date(Date.now() - 86400000);
    const se = fehmirOrdemSalvar({ t: 'CMIG4', quant: 6, limite: 9.84, validade: iso(ontem), origem: 'aporte' });
    const oe = fehmirOrdens().find(o => o.id === se.ordem.id);
    const re = fehmirOrdensResumo();
    check('T012(e) validade ontem ⇒ vencida e fora do comprometido',
      oe && oe.vencida === true && oe.comprometido === 0 && re.porOrigem.aporte === 0,
      `vencida=${oe && oe.vencida} comprometido=${oe && oe.comprometido} aporte=${re.porOrigem.aporte}`);

    // (f) PSSA3
    const sf = fehmirOrdemSalvar({ t: 'PSSA3', quant: 1, limite: 40, validade: '2026-11-25', origem: 'aporte' });
    const of = fehmirOrdens().find(o => o.id === sf.ordem.id);
    info.vereditoPSSA3 = of && of.veredito;
    check('T012(f) PSSA3 ⇒ régua não aprova', of && of.reguaNaoAprova === true && of.veredito !== 'Aportar',
      `veredito=${of && of.veredito}`);

    // (g) "só hoje" (FR-025)
    fehmirGravarOrdens([]);
    const sg = fehmirOrdemSalvar({ t: 'TAEE11', quant: 1, limite: 38.79, origem: 'aporte' });
    const listaG = fehmirCarregarOrdens();
    listaG.forEach(o => { if (o.id === sg.ordem.id) o.criada = ontem.toISOString(); });
    fehmirGravarOrdens(listaG);
    forcados.TAEE11 = 41.17;
    const og1 = fehmirOrdens().find(o => o.id === sg.ordem.id);
    forcados.TAEE11 = 39.90;
    const og2 = fehmirOrdens().find(o => o.id === sg.ordem.id);
    const rg2 = fehmirOrdensResumo();
    fehmirGravarGatilho(2);
    const og3 = fehmirOrdens().find(o => o.id === sg.ordem.id);
    fehmirGravarGatilho(3);
    check('T012(g) validade padrão "dia"', sg.ok && sg.ordem.validade === 'dia', `validade=${sg.ordem && sg.ordem.validade}`);
    check('T012(g) a 41,17: não vence, distância 5,8, não recriar',
      og1 && og1.vencida === false && perto(og1.distancia, 5.78, 0.05) && og1.recriarHoje === false,
      `vencida=${og1 && og1.vencida} dist=${og1 && og1.distancia} recriar=${og1 && og1.recriarHoje}`);
    check('T012(g) a 39,90: recriar hoje, resumo {n:1, total:38,79}',
      og2 && og2.recriarHoje === true && rg2.recriarHoje.n === 1 && perto(rg2.recriarHoje.total, 38.79, 0.001),
      `recriar=${og2 && og2.recriarHoje} resumo=${JSON.stringify(rg2.recriarHoje)}`);
    check('T012(g) gatilho 2% ⇒ não recriar', og3 && og3.recriarHoje === false, `recriar=${og3 && og3.recriarHoje} dist=${og3 && og3.distancia}`);
    renderOrdensAbertas();
    const cardTxt = (document.getElementById('card-ordens-abertas') || {}).textContent || '';
    check('T012(g) cartão mostra "Recriar hoje: 1 ordem" e "recrie hoje na corretora"',
      /Recriar hoje:\s*1\s*ordem/.test(cardTxt) && cardTxt.includes('recrie hoje na corretora'),
      cardTxt.replace(/\s+/g, ' ').slice(0, 300));
    delete forcados.TAEE11;
    delete forcados.BBSE3;

    // ---------- T016: preço velho ----------
    const hist = window.FEHMIR_HIST || {};
    const d1s = fehmirTickersCarteiraB3().map(t => hist[t] && hist[t].d1).filter(Boolean).map(d => String(d).slice(0, 10)).sort();
    const d1 = d1s[d1s.length - 1];
    info.d1Robo = d1;
    let dt = new Date(d1 + 'T12:00:00-03:00'), n = 0;
    while (n < 4) { dt = new Date(dt.getTime() + 86400000); if (fehmirDiaUtilB3(iso(dt))) n++; }
    const agoraA = new Date(iso(dt) + 'T10:00:00-03:00');
    const ia = fehmirRenderFaixaPrecoVelho(agoraA);
    const faixaTxt = (document.getElementById('faixa-preco-velho') || {}).textContent || '';
    const ddmm = d1.slice(8, 10) + '/' + d1.slice(5, 7);
    check('T016(a) d1 + 4 dias úteis ⇒ faixa com "dias úteis" e a data',
      ia.mostrarFaixa && faixaTxt.includes('dias úteis') && faixaTxt.includes(ddmm),
      `mostrar=${ia.mostrarFaixa} texto="${faixaTxt.trim().slice(0, 160)}"`);
    let dtB = new Date(d1 + 'T12:00:00-03:00');
    do { dtB = new Date(dtB.getTime() + 86400000); } while (!fehmirDiaUtilB3(iso(dtB)));
    const ib = fehmirIdadePrecos(new Date(iso(dtB) + 'T19:00:00-03:00'));
    check('T016(b) dia útil seguinte às 19h ⇒ sem faixa', ib.mostrarFaixa === false, `fração=${ib.fracaoVelha}`);
    const metaOrig = window.FEHMIR_HIST_META && window.FEHMIR_HIST_META.gerado;
    window.FEHMIR_HIST_META = window.FEHMIR_HIST_META || {};
    window.FEHMIR_HIST_META.gerado = d1;
    fehmirRenderFaixaPrecoVelho(agoraA);
    const faixaC = (document.getElementById('faixa-preco-velho') || {}).textContent || '';
    check('T016(c) robô parado ⇒ "não atualiza desde"', faixaC.includes('não atualiza desde'), faixaC.trim().slice(0, 200));
    window.FEHMIR_HIST_META.gerado = metaOrig;
    let chamadasBrapi = 0;
    window.fetch = (u, o) => { if (String(u).includes('brapi')) chamadasBrapi++; return fetchOrig(u, o); };
    try { localStorage.removeItem('barsi-brapi-token'); } catch (e) {}
    const btnAt = document.getElementById('btn-faixa-atualizar-agora');
    if (btnAt) btnAt.click();
    await espera(300);
    const msgAt = (document.getElementById('faixa-preco-velho-msg') || {}).textContent || '';
    check('T016(d) sem chave ⇒ frase de Configurações e nenhuma chamada à Brapi',
      !!btnAt && msgAt.includes('Configurações') && chamadasBrapi === 0, `msg="${msgAt.trim()}" chamadas=${chamadasBrapi}`);
    window.fetch = fetchOrig;
    fehmirRenderFaixaPrecoVelho();

    // ---------- T020: cópia que acrescenta ----------
    const copia = JSON.parse(JSON.stringify(exportarCarteiraJSON(true)));
    const tam0 = carregarExtrato().length;
    const r1 = importarCarteiraJSON(JSON.parse(JSON.stringify(copia)));
    const r2 = importarCarteiraJSON(JSON.parse(JSON.stringify(copia)));
    check('T020(a) importar a mesma cópia 2× ⇒ 0 acrescentados e Extrato igual',
      r1.acrescentados === 0 && r2.acrescentados === 0 && carregarExtrato().length === tam0,
      `r1=${r1.acrescentados} r2=${r2.acrescentados} ${tam0}→${carregarExtrato().length}`);
    const idsAntes = carregarExtrato().map(t => t.id).filter(Boolean);
    const copiaNova = JSON.parse(JSON.stringify(copia));
    copiaNova.transacoes.push({ id: 'teste-copia-1', data: '2026-11-03', tipo: 'Compra', ticker: 'ITSA4', cat: 'AÇÕES', quant: 1, preco: 12.34, taxa: 0, total: 12.34, moeda: 'BRL' });
    const r3 = importarCarteiraJSON(copiaNova);
    const idsDepois = new Set(carregarExtrato().map(t => t.id));
    check('T020(b) 1 lançamento novo ⇒ Extrato +1 e nenhum id some',
      r3.acrescentados === 1 && carregarExtrato().length === tam0 + 1 && idsAntes.every(id => idsDepois.has(id)),
      `acrescentados=${r3.acrescentados} tamanho=${carregarExtrato().length}`);
    const copia21 = JSON.parse(JSON.stringify(copia)); copia21.versao = '2.1'; delete copia21.ordens;
    let r4 = null, erro4 = null;
    try { r4 = importarCarteiraJSON(copia21); } catch (e) { erro4 = e.message; }
    check('T020(c) cópia 2.1 sem ordens importa sem erro', !erro4 && r4 && r4.ok, `erro=${erro4}`);

    // ---------- T027: aporte do mês ----------
    check('T027(a) aporte out/26 = 300 e nov/26 = 400',
      fehmirAporteDoMes('2026-10') === 300 && fehmirAporteDoMes('2026-11') === 400,
      `${fehmirAporteDoMes('2026-10')} / ${fehmirAporteDoMes('2026-11')}`);
    fehmirGravarOrdens([]);
    const rb = fehmirResumoAporteMes('2026-11');
    const am = fehmirAportesMes('2026-11');
    const daReservaB = rb.daReserva;
    check('T027(b) usado = compras do mês menos as da reserva',
      perto(rb.usado + daReservaB, am.compras, 0.01), `usado=${rb.usado} daReserva=${daReservaB} compras=${am.compras}`);
    renderCardAporteMes('2026-11');
    adicionarTransacao({ id: 'teste-aporte-100', data: '2026-11-11', tipo: 'Compra', ticker: 'ITSA4', cat: 'AÇÕES', quant: 1, preco: 100, taxa: 0, total: 100, moeda: 'BRL' });
    await espera(100);
    const rc = fehmirResumoAporteMes('2026-11');
    const cardAp = (document.getElementById('card-aporte-mes') || {}).textContent || '';
    check('T027(c) compra de R$ 100 ⇒ sobra cai 100 e o cartão muda sem recarregar',
      perto(rb.sobra - rc.sobra, 100, 0.001) && cardAp.includes(fmtR(rc.sobra)),
      `sobra ${rb.sobra}→${rc.sobra}, cartão="${cardAp.replace(/\s+/g, ' ').slice(0, 160)}"`);
    adicionarTransacao({ id: 'teste-reserva-50', data: '2026-11-11', tipo: 'Compra', ticker: 'ITSA4', cat: 'AÇÕES', quant: 1, preco: 50, taxa: 0, total: 50, moeda: 'BRL', pagoCom: 'reserva' });
    const rd = fehmirResumoAporteMes('2026-11');
    check('T027(d) compra pela reserva ⇒ usado igual e daReserva +50',
      perto(rd.usado, rc.usado, 0.001) && perto(rd.daReserva - rc.daReserva, 50, 0.001),
      `usado ${rc.usado}→${rd.usado} daReserva ${rc.daReserva}→${rd.daReserva}`);
    fehmirOrdemSalvar({ t: 'TAEE11', quant: 1, limite: 48.82, origem: 'aporte' });
    const re2 = fehmirResumoAporteMes('2026-11');
    check('T027(e) ordem de aporte R$ 48,82 ⇒ livre = sobra − 48,82',
      perto(re2.livre, re2.sobra - 48.82, 0.001), `sobra=${re2.sobra} livre=${re2.livre}`);
    const cx = calcularResumoCaixa();
    info.aportesPrevistos = cx.aportesPrevistos;
    check('T027(f) caixa continua contando 300 em outubro', typeof cx.aportesPrevistos === 'number' && fehmirAporteDoMes('2026-10') === 300,
      `aportesPrevistos=${cx.aportesPrevistos}`);
  } catch (e) {
    falhasLista.push('exceção: ' + (e && e.stack || e));
  } finally {
    window.FEHMIR.preco = precoOrig;
    window.fetch = fetchOrig;
  }
  return { falhas: falhasLista.length, falhasLista, info, casos: casos.map(c => (c.ok ? 'OK ' : 'FALHOU ') + c.nome) };
})();
