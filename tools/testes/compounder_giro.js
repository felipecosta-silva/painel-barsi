// Spec 010: régua de compounder (US1), balde de giro (US2), patrimônio da imobiliária (US3) e MELK3 (US4).
// Uso: node tools/testes/cdp.js tools/testes/compounder_giro.js   (ou pelo run_all.js)
return (async () => {
  const casos = [];
  const falhasLista = [];
  const info = {};
  function check(nome, ok, detalhe) {
    casos.push({ nome, ok: !!ok, detalhe });
    if (!ok) falhasLista.push(`${nome}: ${detalhe}`);
  }
  const perto = (a, b, tol) => a != null && b != null && Math.abs(a - b) <= tol;
  const pc = x => x == null ? null : +(x * 100).toFixed(2);

  const precoOrig = window.FEHMIR.preco;
  const posOrig = window.FEHMIR.posicoes;
  const forcados = {};
  window.FEHMIR.preco = (t, d) => (forcados[t] != null ? { preco: forcados[t] } : precoOrig(t, d));
  const listaOrig = JSON.parse(JSON.stringify(window.FEHMIR_COMPOUNDERS));
  const benchOrig = window.FEHMIR_BENCH;
  const vendasOrig = window.FEHMIR_VENDAS_ATIVOS;
  let macroOrig = null;
  try { macroOrig = localStorage.getItem('barsi-macro-v1'); } catch (e) {}
  const giroOrig = (() => { try { return localStorage.getItem('barsi-giro-v1'); } catch (e) { return null; } })();
  const reset = () => { if (typeof limparCacheTetoOficial === 'function') limparCacheTetoOficial(); };

  try {
    // ---------- T008: fundação ----------
    check('T008 TIR([-100,110]) = 10%', perto(fehmirTIR([-100, 110]), 0.10, 0.0005), `${fehmirTIR([-100, 110])}`);
    check('T008 TIR(10 anos, 259,374) = 10%', perto(fehmirTIR([-100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 259.374]), 0.10, 0.001), `${fehmirTIR([-100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 259.374])}`);
    check('T008 TIR sem troca de sinal = null', fehmirTIR([100, 10]) === null, `${fehmirTIR([100, 10])}`);
    const ip = FEHMIR_BENCH.ipca.slice(-12).reduce((a, x) => a * (1 + x[1] / 100), 1);
    check('T008 IPCA 12m igual à conta do teste', perto(fehmirIpca12m(), (ip - 1) * 100, 1e-9), `painel=${fehmirIpca12m()} teste=${(ip - 1) * 100}`);
    localStorage.removeItem('barsi-macro-v1');
    check('T008 macro vazio ⇒ ntnb null (sem reserva)', fehmirMacroReal().ntnb === null, JSON.stringify(fehmirMacroReal()));
    if (macroOrig != null) localStorage.setItem('barsi-macro-v1', macroOrig);

    // ---------- T013: compounder ----------
    const W = fehmirCompounder('WEGE3', Object.assign({}, fehmirUniverso().WEGE3, { preco: 51.61 }));
    const [cp, cb, co] = W.cenarios.map(x => x.tir);
    info.wege3 = { gRef: pc(W.gRef), tir: [pc(cp), pc(cb), pc(co)], entrada: W.precoEntrada && +W.precoEntrada.toFixed(2), exigeG: pc(W.exigeG) };
    check('SC-001 WEGE3 a 51,61: pessimista 2–3,5%, base 7–8,5%, otimista 12–13,5%, entrada R$ 35–38',
      W.aprovado && cp >= 0.02 && cp <= 0.035 && cb >= 0.07 && cb <= 0.085 && co >= 0.12 && co <= 0.135 && W.precoEntrada >= 35 && W.precoEntrada <= 38,
      JSON.stringify(info.wege3));
    reset();
    const tw = tetoOficial('WEGE3');
    check('T010 teto oficial da WEGE3 = preço de entrada (Compounder TIR 10A)',
      tw.metodo === 'Compounder (TIR 10A)' && tw.teto > 30 && tw.teto < 45 && perto(tw.compra, tw.teto, 1e-9), `metodo=${tw.metodo} teto=${tw.teto} compra=${tw.compra}`);

    const tLavvAntes = tetoOficial('LAVV3').teto;
    window.FEHMIR_COMPOUNDERS.ativos.push({ t: 'LAVV3', desde: '2026-11-13', motivo: 'teste' });
    reset();
    const cL = fehmirCompounder('LAVV3');
    check('T013 LAVV3 na lista ⇒ setor cíclico e teto inalterado',
      !cL.aprovado && cL.motivo === 'setor cíclico: usa régua do setor e balde de giro' && tetoOficial('LAVV3').teto === tLavvAntes, `motivo=${cL.motivo} teto ${tLavvAntes}→${tetoOficial('LAVV3').teto}`);

    // um ativo não cíclico com ROE médio de 5 anos < 15%
    const C = window.FEHMIR_FUND_CVM, U = fehmirUniverso(), ult = new Date().getFullYear() - 1;
    const baixo = Object.keys(C).find(t => {
      const u = U[t]; if (!u || u.macro !== 'acoes' || !C[t].roeAnual || !C[t].lucroAnual) return false;
      const S = window.setorDe(u); if (S && (S.id === 'commodity' || S.id === 'construcao')) return false;
      if (/im[oó]veis|log[íi]stica|shopping|imobili/i.test(u.setor || '')) return false;
      const r = Object.keys(C[t].roeAnual).filter(y => +y <= ult).sort().slice(-5).map(y => C[t].roeAnual[y]);
      const l = Object.keys(C[t].lucroAnual).filter(y => +y <= ult).sort().slice(-6);
      return r.length === 5 && r.reduce((a, b) => a + b, 0) / 5 < 15 && l.length >= 5 && l.slice(-5).every(y => C[t].lucroAnual[y] > 0);
    });
    window.FEHMIR_COMPOUNDERS.ativos.push({ t: baixo, desde: '2026-11-13', motivo: 'teste' });
    const cB = fehmirCompounder(baixo);
    check(`T013 ${baixo} (ROE < 15%) ⇒ reprovado na qualidade`, !cB.aprovado && /^reprovado na qualidade de compounder: ROE/.test(cB.motivo), `motivo=${cB.motivo}`);
    window.FEHMIR_COMPOUNDERS = JSON.parse(JSON.stringify(listaOrig));

    const dlOrig = C.WEGE3.dlEbitda;
    C.WEGE3.dlEbitda = null; reset();
    const cN = fehmirCompounder('WEGE3'); const tN = tetoOficial('WEGE3');
    check('T013 dívida não conferida ⇒ selo "não autoriza compra" e teto oficial volta à régua do setor',
      cN.aprovado && cN.selo === 'não autoriza compra' && tN.metodo !== 'Compounder (TIR 10A)', `selo=${cN.selo} metodo=${tN.metodo} teto=${tN.teto}`);
    C.WEGE3.dlEbitda = dlOrig; reset();

    window.FEHMIR_BENCH = undefined; reset();
    const cSemIpca = fehmirCompounder('WEGE3');
    check('SC-006 sem IPCA do robô ⇒ preço de entrada "não calculado" (null)', cSemIpca.precoEntrada === null && cSemIpca.retornoMin === null, `entrada=${cSemIpca.precoEntrada}`);
    window.FEHMIR_BENCH = benchOrig;
    localStorage.removeItem('barsi-macro-v1'); reset();
    const cSemMacro = fehmirCompounder('WEGE3');
    check('SC-006 macro vazio ⇒ teto calculado e Tesouro "não calculado"', cSemMacro.precoEntrada > 0 && cSemMacro.tesouroNominal === null, `entrada=${cSemMacro.precoEntrada} tesouro=${cSemMacro.tesouroNominal}`);
    if (macroOrig != null) localStorage.setItem('barsi-macro-v1', macroOrig);
    reset();

    // cartão na ficha
    openModal('WEGE3'); await new Promise(r => setTimeout(r, 300));
    const card = document.getElementById('m-compounder-card');
    check('T011 cartão da WEGE3 na ficha com cenários e preço de entrada',
      card && card.style.display !== 'none' && /pessimista/i.test(card.textContent) && /Preço de entrada/.test(card.textContent) && /supõe P\/L constante/.test(card.textContent), (card && card.textContent.slice(0, 120)) || 'sem cartão');

    // ---------- T020: balde de giro ----------
    localStorage.removeItem('barsi-giro-v1');
    const giroT = ['PETR4', 'VALE3', 'LOGG3', 'LAVV3', 'MELK3'];
    giroT.forEach(t => fehmirGiroMarcar(t, true));
    const faixas = {};
    let okFaixas = true;
    for (const t of giroT) {
      const tv = tetoOficial(t);
      if (!(tv.teto > 0)) { faixas[t] = 'sem teto'; okFaixas = false; continue; }
      const T = tv.teto, Cp = tv.compra;
      const pontos = [[Cp * 0.99, 'zona de compra'], [(Cp + 1.5 * T) / 2, 'meio'], [1.5 * T * 1.01, 'esticada: degrau 1'], [2 * T * 1.01, 'esticada: degrau 2']];
      faixas[t] = [];
      for (const [p, esperado] of pontos) {
        forcados[t] = p;
        const a = fehmirGiro().ativos.find(x => x.t === t);
        faixas[t].push(a.faixa);
        if (a.faixa !== esperado) okFaixas = false;
      }
      forcados[t] = Cp * 0.99; fehmirGiro();   // volta à zona: zera a escada
    }
    info.faixas = faixas;
    check('SC-002 cinco ativos do giro nas 4 faixas (compra, meio, 1,5×, 2×)', okFaixas, JSON.stringify(faixas));

    const T4 = tetoOficial('PETR4').teto;
    forcados.PETR4 = 1.5 * T4 * 1.01;
    const p4 = fehmirGiro().ativos.find(x => x.t === 'PETR4');
    check('SC-002 PETR4 com 7 ações no degrau 1 ⇒ vender 2', p4.quant === 7 && p4.sugeridaQtd === 2 && p4.proximoDegrau === 1, `quant=${p4.quant} sugerida=${p4.sugeridaQtd}`);

    // SC-003: PM fora da conta
    const comPM = pm => { window.FEHMIR.posicoes = () => { const P = posOrig(); const c = JSON.parse(JSON.stringify(P)); if (c.PETR4) c.PETR4.pm = pm; return c; }; const a = fehmirGiro().ativos.find(x => x.t === 'PETR4'); window.FEHMIR.posicoes = posOrig; return a; };
    const A = comPM(10), B = comPM(100);
    check('SC-003 PM 10 × PM 100 ⇒ mesma faixa, degrau e sugestão (só o lucro de IR muda)',
      A.faixa === B.faixa && A.degrau === B.degrau && A.sugeridaQtd === B.sugeridaQtd && A.lucroIR !== B.lucroIR, `A=${A.faixa}/${A.sugeridaQtd}/${A.lucroIR} B=${B.faixa}/${B.sugeridaQtd}/${B.lucroIR}`);

    check('T020 FII não entra no giro', fehmirGiroMarcar('XPML11', true) === 'FII não entra no giro (venda de FII só por fundamento)' && !fehmirGiroLer().ativos.XPML11, '');
    check('T020 limite fora de 5–30% é recusado', fehmirGiroLimite(40) !== true && fehmirGiroLimite(3) !== true && fehmirGiroLimite(15) === true, '');

    // isenção: R$ 19.900 vendidos no mês + degrau ⇒ tributável
    const mes = new Date().toISOString().slice(0, 7);
    adicionarTransacao({ id: 'teste-giro-venda', data: mes + '-02', tipo: 'Venda', ticker: 'ITSA4', cat: 'AÇÕES', quant: 1000, preco: 19.9, taxa: 0, total: 19900, moeda: 'BRL' });
    const pI = fehmirGiro().ativos.find(x => x.t === 'PETR4');
    check('T020 R$ 19.900 vendidos no mês + degrau ⇒ "venda tributável: 15% sobre o lucro"',
      perto(pI.isencaoFalta, 100, 0.01) && pI.avisos.includes('venda tributável: 15% sobre o lucro'), `falta=${pI.isencaoFalta} avisos=${pI.avisos}`);

    // limite do balde bloqueia compra de ativo do giro
    const g0 = fehmirGiro();
    // Procura um ativo do giro cujo veredito, com o limite folgado (30%) e preço na zona, seja "Aportar"
    fehmirGiroLimite(30);
    let alvo = null, vSem = null;
    for (const t of giroT) {
      const tv = tetoOficial(t); if (!(tv.compra > 0)) continue;
      const u = Object.assign({}, fehmirUniverso()[t], { preco: tv.compra * 0.9 });
      const g30 = fehmirGiro();
      const v = fehmirVeredito(u);
      if (!g30.acimaLimite && v.label === 'Aportar') { alvo = u; vSem = v; break; }
    }
    if (!alvo) {
      // com 37% de peso o balde já passa de 30%: desmarca todos menos LAVV3/MELK3 (posição zero) e testa com eles
      ['PETR4', 'VALE3', 'LOGG3'].forEach(t => fehmirGiroMarcar(t, false));
      for (const t of ['LAVV3', 'MELK3']) {
        const tv = tetoOficial(t); if (!(tv.compra > 0)) continue;
        const u = Object.assign({}, fehmirUniverso()[t], { preco: tv.compra * 0.9 });
        const v = fehmirVeredito(u);
        if (v.label === 'Aportar') { alvo = u; vSem = v; break; }
      }
    }
    let vCom = null, g1 = null;
    if (alvo) {
      fehmirGiroMarcar('PETR4', true);    // PETR4 (7 ações) leva o balde acima de 5%
      fehmirGiroLimite(5);
      g1 = fehmirGiro();
      vCom = fehmirVeredito(alvo);
    }
    info.vereditoGiro = { alvo: alvo && alvo.t, sem: vSem && vSem.label, com: vCom && vCom.label, peso: g1 && +g1.pesoPct.toFixed(1) };
    check('T020 balde acima do limite ⇒ ativo do giro que seria "Aportar" vira "Manter" com o aviso',
      alvo && vSem.label === 'Aportar' && g1.acimaLimite && vCom.label === 'Manter' && /balde de giro acima do limite: [\d,]+% de 5%/i.test(vCom.motivo || ''), JSON.stringify(info.vereditoGiro));
    fehmirGiroLimite(15);
    info.pesoBalde = +g0.pesoPct.toFixed(1);

    // exportar / importar mescla
    ['PETR4', 'VALE3'].forEach(t => fehmirGiroMarcar(t, true));
    const exp = exportarCarteiraJSON(true);
    const giroExp = JSON.parse(JSON.stringify(exp.giro));
    check('T019 exportação leva as marcações do giro', giroExp && giroExp.ativos && giroExp.ativos.PETR4 && giroExp.ativos.VALE3, JSON.stringify(Object.keys((giroExp && giroExp.ativos) || {})));
    localStorage.setItem('barsi-giro-v1', JSON.stringify({ versao: 1, limitePct: 15, ativos: { ITSA4: { desde: '2026-11-13', qtdRef: null, degrau1Data: null, degrausFeitos: [] } } }));
    giroExp.ativos = { PETR4: giroExp.ativos.PETR4, VALE3: giroExp.ativos.VALE3 };
    importarCarteiraJSON({ versao: '2.2', transacoes: [], ordens: [], giro: giroExp });
    const k = Object.keys(fehmirGiroLer().ativos).sort().join(',');
    check('T019 importar 2 marcações num perfil com 1 diferente ⇒ ficam 3', k === 'ITSA4,PETR4,VALE3', k);

    // clique real em "marcar como giro" na ficha
    localStorage.removeItem('barsi-giro-v1');
    openModal('ITSA4'); await new Promise(r => setTimeout(r, 300));
    const btn = document.getElementById('btn-giro-toggle');
    if (btn) btn.click();
    check('T020 clique em "marcar como giro" na ficha marca o ativo', btn && !!fehmirGiroLer().ativos.ITSA4 && /desmarcar/.test(btn.textContent), btn ? btn.textContent : 'sem botão');

    // ---------- T022: patrimônio da LOGG3 ----------
    const tLogAntes = tetoOficial('LOGG3');
    const vpa = (window.FEHMIR_FUND_CVM.LOGG3 && window.FEHMIR_FUND_CVM.LOGG3.vpa) || null;
    check('T022 sem venda registrada ⇒ Bazin com "patrimônio não comprovado"', /patrimônio não comprovado/.test(tLogAntes.src || ''), `teto=${tLogAntes.teto}`);
    const hoje = new Date(), dIso = new Date(hoje.getFullYear(), hoje.getMonth() - 3, 10).toISOString().slice(0, 10);
    window.FEHMIR_VENDAS_ATIVOS = { LOGG3: [{ data: dIso, venda: 95, contabil: 100, fonte: 'https://ri.log.com.br/teste' }] }; reset();
    const t95 = tetoOficial('LOGG3');
    window.FEHMIR_VENDAS_ATIVOS = { LOGG3: [{ data: dIso, venda: 80, contabil: 100, fonte: 'https://ri.log.com.br/teste' }] }; reset();
    const t80 = tetoOficial('LOGG3');
    window.FEHMIR_VENDAS_ATIVOS = vendasOrig; reset();
    info.logg3 = { antes: tLogAntes.teto, venda95: t95.teto, venda80: t80.teto, vpa };
    check('SC-004 venda a 95% ⇒ teto = VPA × 0,9', vpa && t95.teto > tLogAntes.teto && /comprovado/.test(t95.src || ''), JSON.stringify(info.logg3));
    check('SC-004 venda a 80% ⇒ volta ao Bazin com a data e o %', perto(t80.teto, tLogAntes.teto, 0.005) && /saiu a 80% do contábil/.test(t80.src || ''), JSON.stringify(info.logg3));

    // ---------- T024: MELK3 ----------
    const tm = tetoOficial('MELK3');
    info.melk3 = { teto: tm.teto, metodo: tm.metodo };
    check('T024 MELK3 com teto entre R$ 1,20 e R$ 1,60 (Graham limitado pelo P/VP justo)', tm.teto >= 1.2 && tm.teto <= 1.6, JSON.stringify(info.melk3));
  } catch (e) {
    falhasLista.push('exceção: ' + (e && e.stack || e));
  } finally {
    window.FEHMIR.preco = precoOrig;
    window.FEHMIR.posicoes = posOrig;
    window.FEHMIR_COMPOUNDERS = listaOrig;
    window.FEHMIR_BENCH = benchOrig;
    window.FEHMIR_VENDAS_ATIVOS = vendasOrig;
    try { if (macroOrig != null) localStorage.setItem('barsi-macro-v1', macroOrig); } catch (e) {}
    try { if (giroOrig != null) localStorage.setItem('barsi-giro-v1', giroOrig); else localStorage.removeItem('barsi-giro-v1'); } catch (e) {}
    if (typeof limparCacheTetoOficial === 'function') limparCacheTetoOficial();
  }
  return { falhas: falhasLista.length, falhasLista, info, casos: casos.map(c => (c.ok ? 'OK ' : 'FALHOU ') + c.nome) };
})();
