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

    // Caso 6 (Parte H): BBSE3 na ficha -> linha de referência do setor e botão "usar g do setor" bate com tetoOficial("BBSE3").teto ± 0,05
    switchMainTab('analise');
    await sleep(200);
    localStorage.removeItem('barsi-calc-BBSE3');
    await window.fehmirAnalisar('BBSE3');
    await sleep(300);
    const refEl = document.getElementById('calc-proj-ref-setor-BBSE3');
    const refTxt = refEl ? refEl.textContent.trim() : '';
    const tetoOfBbse = window.tetoOficial('BBSE3').teto;
    window.fehmirUsarGSetorCalc('BBSE3');
    const resProjEl = document.getElementById('calc-res-proj-BBSE3');
    const mTeto = (resProjEl?.innerText || '').match(/Preço teto:\s*R\$\s*([\d.]+,\d{2})/);
    const tetoCalcComG = mTeto ? parseFloat(mTeto[1].replace(/\./g, '').replace(',', '.')) : null;
    window.fehmirResetarCalc('BBSE3', 'projetivo');
    const mTetoPadrao = (document.getElementById('calc-res-proj-BBSE3')?.innerText || '').match(/Preço teto:\s*R\$\s*([\d.]+,\d{2})/);
    const tetoCalcPadrao = mTetoPadrao ? parseFloat(mTetoPadrao[1].replace(/\./g, '').replace(',', '.')) : null;

    check(
      '4. Parte H: BBSE3 com "usar g do setor" = tetoOficial("BBSE3").teto ± 0,05 e linha de referência visível',
      refTxt.includes('Com o crescimento do setor') && tetoCalcComG != null && Math.abs(tetoCalcComG - tetoOfBbse) <= 0.05 && tetoCalcPadrao != null && tetoCalcPadrao < tetoCalcComG,
      `refTxt="${refTxt}", tetoCalcComG=${tetoCalcComG}, tetoOfBbse=${tetoOfBbse?.toFixed(2)}, tetoCalcPadrao=${tetoCalcPadrao}`
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
    } catch (e) {}
  }

  return { falhas: falhasLista.length, falhasLista, casos };
})();

