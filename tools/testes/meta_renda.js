// Rodada 20 Parte G + Parte H: Meta de renda ajustável e calculadora projetiva ligada ao teto oficial
return (async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const parseBRL = txt => {
    if (!txt) return null;
    const m = String(txt).match(/R\$\s*([\d.]+(?:,\d{2})?)/);
    if (!m) return null;
    return parseFloat(m[1].replace(/\./g, '').replace(',', '.'));
  };

  const casos = [];
  const falhasLista = [];
  function check(nome, ok, detalhe) {
    casos.push({ nome, ok: !!ok, detalhe });
    if (!ok) falhasLista.push(`${nome}: ${detalhe}`);
  }

  try {
    switchMainTab('projecao');
    await sleep(300);

    // Caso 1: R$ 4.500 x 150 = R$ 675.000
    window.setMetaTaxaModo('150');
    window.setMetaRenda(4500);
    const pat4500_150 = parseBRL(document.getElementById('meta-kpi-patrimonio')?.textContent);
    check('1a. R$ 4.500 × 150 = R$ 675.000', pat4500_150 === 675000, `patrimonio=${pat4500_150}`);

    // Caso 2: R$ 5.000 x 150 = R$ 750.000
    window.setMetaTaxaModo('150');
    window.setMetaRenda(5000);
    const pat5000_150 = parseBRL(document.getElementById('meta-kpi-patrimonio')?.textContent);
    check('1b. R$ 5.000 × 150 = R$ 750.000', pat5000_150 === 750000, `patrimonio=${pat5000_150}`);

    // Caso 3: R$ 5.000 x 200 = R$ 1.000.000
    window.setMetaTaxaModo('200');
    window.setMetaRenda(5000);
    const pat5000_200 = parseBRL(document.getElementById('meta-kpi-patrimonio')?.textContent);
    check('1c. R$ 5.000 × 200 = R$ 1.000.000', pat5000_200 === 1000000, `patrimonio=${pat5000_200}`);

    // Caso 4: Renda do trabalho 4.500 => 54.000 / 2.250 / 450 / 204,55
    const elSal = document.getElementById('meta-salario-input');
    if (elSal) elSal.value = '4500';
    window.atualizarCalculadoraMeta();
    const salAnual = parseBRL(document.getElementById('meta-sal-anual')?.textContent);
    const salEss = parseBRL(document.getElementById('meta-sal-essenciais')?.textContent);
    const salPag = parseBRL(document.getElementById('meta-sal-paguese')?.textContent);
    const salDia = parseBRL(document.getElementById('meta-sal-dia')?.textContent);
    check(
      '2. Renda do trabalho 4.500 => 54.000 / 2.250 / 450 / 204,55',
      salAnual === 54000 && salEss === 2250 && salPag === 450 && Math.abs(salDia - 204.55) <= 0.01,
      `anual=${salAnual}, ess=${salEss}, pag=${salPag}, dia=${salDia}`
    );

    // Caso 5: Nenhum 0.0085 restante em atualizarCalculadoraMeta e texto "~12 anos" fixo removido
    const fnStr = window.atualizarCalculadoraMeta.toString();
    const htmlAll = document.documentElement.outerHTML;
    const ocorrencias0085 = (htmlAll.match(/0\.0085/g) || []).length;
    check(
      '3. Sem 0.0085 em atualizarCalculadoraMeta/simulador e sem texto fixo "~12 anos"',
      !fnStr.includes('0.0085') && ocorrencias0085 <= 1 && !htmlAll.includes('~12 anos'),
      `fnHas0085=${fnStr.includes('0.0085')}, ocorrencias0085=${ocorrencias0085}, tem12Anos=${htmlAll.includes('~12 anos')}`
    );

    // Caso 6 (Parte H): ITSA4 na ficha (após Rodada 24 zerar g da BBSE3) -> linha de referência do setor e botão "usar g do setor" bate com tetoOficial("ITSA4").teto ± 0,05
    switchMainTab('analise');
    await sleep(200);
    localStorage.removeItem('barsi-calc-ITSA4');
    await window.fehmirAnalisar('ITSA4');
    await sleep(300);
    const refEl = document.getElementById('calc-proj-ref-setor-ITSA4');
    const refTxt = refEl ? refEl.textContent.trim() : '';
    const tetoOfItsa = window.tetoOficial('ITSA4').teto;
    window.fehmirUsarGSetorCalc('ITSA4');
    const resProjEl = document.getElementById('calc-res-proj-ITSA4');
    const mTeto = (resProjEl?.innerText || '').match(/Preço teto:\s*R\$\s*([\d.]+,\d{2})/);
    const tetoCalcComG = mTeto ? parseFloat(mTeto[1].replace(/\./g, '').replace(',', '.')) : null;
    window.fehmirResetarCalc('ITSA4', 'projetivo');
    const mTetoPadrao = (document.getElementById('calc-res-proj-ITSA4')?.innerText || '').match(/Preço teto:\s*R\$\s*([\d.]+,\d{2})/);
    const tetoCalcPadrao = mTetoPadrao ? parseFloat(mTetoPadrao[1].replace(/\./g, '').replace(',', '.')) : null;

    check(
      '4. Parte H: ITSA4 com "usar g do setor" = tetoOficial("ITSA4").teto ± 0,05 e linha de referência visível',
      refTxt.includes('Com o crescimento do setor') && tetoCalcComG != null && Math.abs(tetoCalcComG - tetoOfItsa) <= 0.05 && tetoCalcPadrao != null && tetoCalcPadrao < tetoCalcComG,
      `refTxt="${refTxt}", tetoCalcComG=${tetoCalcComG}, tetoOfItsa=${tetoOfItsa?.toFixed(2)}, tetoCalcPadrao=${tetoCalcPadrao}`
    );

    // Caso 7 (Rodada 24 / Rodada 33): Gordon real + g=0 asset-light lendo dados/tetos.js e fórmula dinâmica
    const avBbse = window.tetoOficial('BBSE3');
    const avItsa = window.tetoOficial('ITSA4');
    const tBbseExp = window.FEHMIR_TETOS && window.FEHMIR_TETOS.BBSE3 ? window.FEHMIR_TETOS.BBSE3.teto : null;
    const tItsaExp = window.FEHMIR_TETOS && window.FEHMIR_TETOS.ITSA4 ? window.FEHMIR_TETOS.ITSA4.teto : null;
    const projEspBbse = avBbse ? (avBbse.lpa * ((avBbse.S && avBbse.S.haircut) || 1) * (avBbse.pay / 100) * (1 + avBbse.g / 100) / ((avBbse.req - avBbse.g) / 100)) : null;
    const projEspItsa = avItsa ? (avItsa.lpa * ((avItsa.S && avItsa.S.haircut) || 1) * (avItsa.pay / 100) * (1 + avItsa.g / 100) / ((avItsa.req - avItsa.g) / 100)) : null;
    check(
      '5. Rodada 24: Gordon real + g=0 asset-light (BBSE3 g=0; ITSA4 g=1,5 vs dados/tetos.js)',
      avBbse && avBbse.g === 0 && projEspBbse != null && Math.abs(avBbse.proj - projEspBbse) <= 0.02 &&
      (tBbseExp == null || Math.abs(avBbse.teto - tBbseExp) <= 0.05) &&
      avItsa && Math.abs(avItsa.g - 1.5) <= 0.05 && projEspItsa != null && Math.abs(avItsa.proj - projEspItsa) <= 0.02 &&
      (tItsaExp == null || Math.abs(avItsa.teto - tItsaExp) <= 0.05),
      `BBSE3[g=${avBbse?.g?.toFixed(1)}, proj=${avBbse?.proj?.toFixed(2)}, esp=${projEspBbse?.toFixed(2)}, tetos.js=${tBbseExp}] ITSA4[g=${avItsa?.g?.toFixed(1)}, proj=${avItsa?.proj?.toFixed(2)}, esp=${projEspItsa?.toFixed(2)}, tetos.js=${tItsaExp}]`
    );
  } finally {
    // Restaurar estado limpo
    const elSal = document.getElementById('meta-salario-input');
    if (elSal) elSal.value = '';
    window.setMetaTaxaModo('150');
    window.setMetaRenda(5000);
    try {
      localStorage.removeItem('barsi-meta-v1');
      localStorage.removeItem('barsi-calc-BBSE3');
      localStorage.removeItem('barsi-calc-ITSA4');
    } catch (e) {}
  }

  return { falhas: falhasLista.length, falhasLista, casos };
})();

