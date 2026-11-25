// Testes da Spec 012 (Política de dividendos mudou, estrutural, saneamento FR-A1..FR-A4, realismo 60m FR-012)
await new Promise(r => setTimeout(r, 400));
if (typeof window.fehmirCarregarMensal === 'function') {
  await new Promise(r => window.fehmirCarregarMensal(r));
}

const u = typeof window.fehmirUniverso === 'function' ? window.fehmirUniverso() : {};
const radar = typeof RADAR_DATA !== 'undefined' ? RADAR_DATA : [];
const getAtivo = tk => u[tk] || radar.find(x => x.t === tk);

const falhas = [];
const assert = (cond, msg) => { if (!cond) falhas.push(msg); };
const ntnbAt = (typeof loadMacro === 'function' && loadMacro().ntnb != null) ? Number(loadMacro().ntnb) : 7.4;

// 1. TAEE11 (estrutural permanente + FR-A1 9,0% + FR-A2)
// 1. TAEE11 (estrutural permanente + FR-A1 ntnb+1,6% + FR-A2)
const taee = getAtivo('TAEE11');
const avTaee = taee ? window.fehmirAvaliar(taee) : null;
assert(avTaee && avTaee.polVigente, 'TAEE11 polVigente devia ser true');
assert(avTaee && Math.abs(avTaee.taxa - 9.0) < 0.05, `TAEE11 taxa esperada 9.0, veio ${avTaee && avTaee.taxa}`);
assert(avTaee && avTaee.teto >= 28.0 && avTaee.teto <= 29.5, `TAEE11 teto esperado ~28.67, veio ${avTaee && avTaee.teto}`);
assert(avTaee && Math.abs(avTaee.taxa - (ntnbAt + 1.6)) < 0.05, `TAEE11 taxa esperada ${(ntnbAt + 1.6).toFixed(2)}, veio ${avTaee && avTaee.taxa}`);
assert(avTaee && avTaee.teto >= 27.5 && avTaee.teto <= 29.5, `TAEE11 teto esperado ~28.20-28.67, veio ${avTaee && avTaee.teto}`);
const compraTaee = avTaee && avTaee.teto * (1 - avTaee.S.margemMin / 100);
assert(compraTaee && compraTaee >= 26.5 && compraTaee <= 28.0, `TAEE11 compra esperada ~27.23, veio ${compraTaee}`);
assert(compraTaee && compraTaee >= 26.0 && compraTaee <= 28.0, `TAEE11 compra esperada ~26.79-27.23, veio ${compraTaee}`);

// 2. ISAE4 (estrutural em 3 fases + FR-A1 9,0% + FR-A2)
// 2. ISAE4 (estrutural em 3 fases + FR-A1 ntnb+1,6% + FR-A2)
const isae = getAtivo('ISAE4');
const avIsae = isae ? window.fehmirAvaliar(isae) : null;
assert(avIsae && avIsae.polVigente, 'ISAE4 polVigente devia ser true');
assert(avIsae && Math.abs(avIsae.taxa - 9.0) < 0.05, `ISAE4 taxa esperada 9.0, veio ${avIsae && avIsae.taxa}`);
assert(avIsae && avIsae.teto >= 18.5 && avIsae.teto <= 19.7, `ISAE4 teto esperado ~19.10, veio ${avIsae && avIsae.teto}`);
assert(avIsae && Math.abs(avIsae.taxa - (ntnbAt + 1.6)) < 0.05, `ISAE4 taxa esperada ${(ntnbAt + 1.6).toFixed(2)}, veio ${avIsae && avIsae.taxa}`);
assert(avIsae && avIsae.teto >= 18.2 && avIsae.teto <= 19.7, `ISAE4 teto esperado ~18.79-19.10, veio ${avIsae && avIsae.teto}`);
const compraIsae = avIsae && avIsae.teto * (1 - avIsae.S.margemMin / 100);
assert(compraIsae && compraIsae >= 17.6 && compraIsae <= 18.7, `ISAE4 compra esperada ~18.15, veio ${compraIsae}`);
assert(avIsae && avIsae.tetoSemVolta >= 22.5 && avIsae.tetoSemVolta <= 23.8, `ISAE4 tetoSemVolta esperado ~23.11, veio ${avIsae && avIsae.tetoSemVolta}`);
assert(compraIsae && compraIsae >= 17.3 && compraIsae <= 18.7, `ISAE4 compra esperada ~17.85-18.15, veio ${compraIsae}`);
assert(avIsae && avIsae.tetoSemVolta >= 22.0 && avIsae.tetoSemVolta <= 23.8, `ISAE4 tetoSemVolta esperado ~22.73-23.11, veio ${avIsae && avIsae.tetoSemVolta}`);

// 3. CMIG4 (estrutural 2 fases + 9,9%)
// 3. CMIG4 (estrutural 2 fases + ntnb+2,5%)
const cmig = getAtivo('CMIG4');
const avCmig = cmig ? window.fehmirAvaliar(cmig) : null;
assert(avCmig && avCmig.polVigente, 'CMIG4 polVigente devia ser true');
assert(avCmig && Math.abs(avCmig.taxa - 9.9) < 0.05, `CMIG4 taxa esperada 9.9, veio ${avCmig && avCmig.taxa}`);
assert(avCmig && avCmig.teto >= 9.0 && avCmig.teto <= 9.8, `CMIG4 teto esperado ~9.43, veio ${avCmig && avCmig.teto}`);
assert(avCmig && Math.abs(avCmig.taxa - (ntnbAt + 2.5)) < 0.05, `CMIG4 taxa esperada ${(ntnbAt + 2.5).toFixed(2)}, veio ${avCmig && avCmig.taxa}`);
assert(avCmig && avCmig.teto >= 8.8 && avCmig.teto <= 9.8, `CMIG4 teto esperado ~9.28-9.43, veio ${avCmig && avCmig.teto}`);
const compraCmig = avCmig && avCmig.teto * (1 - avCmig.S.margemMin / 100);
assert(compraCmig && compraCmig >= 8.1 && compraCmig <= 8.8, `CMIG4 compra esperada ~8.49, veio ${compraCmig}`);
assert(avCmig && avCmig.tetoSemVolta >= 7.0 && avCmig.tetoSemVolta <= 7.8, `CMIG4 tetoSemVolta esperado ~7.37, veio ${avCmig && avCmig.tetoSemVolta}`);
assert(compraCmig && compraCmig >= 8.0 && compraCmig <= 8.8, `CMIG4 compra esperada ~8.35-8.49, veio ${compraCmig}`);
assert(avCmig && avCmig.tetoSemVolta >= 7.0 && avCmig.tetoSemVolta <= 7.8, `CMIG4 tetoSemVolta esperado ~7.26-7.37, veio ${avCmig && avCmig.tetoSemVolta}`);

// 4. PETR4 (US2 + SC-003 + FR-A3 margemMin 20%)
const petr = getAtivo('PETR4');
const avPetr = petr ? window.fehmirAvaliar(petr) : null;
assert(avPetr && avPetr.polVigente, 'PETR4 polVigente devia ser true');
assert(avPetr && avPetr.S && avPetr.S.margemMin === 20, `PETR4 margemMin esperada 20, veio ${avPetr && avPetr.S && avPetr.S.margemMin}`);
assert(avPetr && avPetr.teto >= 25.0 && avPetr.teto <= 28.0, `PETR4 teto esperado 25..28, veio ${avPetr && avPetr.teto}`);
const compraPetr = avPetr && avPetr.teto * (1 - avPetr.S.margemMin / 100);
assert(compraPetr && compraPetr >= 20.0 && compraPetr <= 22.4, `PETR4 compra esperada ~21.17, veio ${compraPetr}`);

// 5. ALUP4 em Transmissão (FR-A1)
const alup = getAtivo('ALUP4');
const avAlup = alup ? window.fehmirAvaliar(alup) : null;
assert(avAlup && avAlup.S && avAlup.S.id === 'transmissao', `ALUP4 devia ser transmissao, veio ${avAlup && avAlup.S && avAlup.S.id}`);
assert(avAlup && Math.abs(avAlup.taxa - 9.0) < 0.05, `ALUP4 taxa esperada 9.0, veio ${avAlup && avAlup.taxa}`);
assert(avAlup && Math.abs(avAlup.taxa - (ntnbAt + 1.6)) < 0.05, `ALUP4 taxa esperada ${(ntnbAt + 1.6).toFixed(2)}, veio ${avAlup && avAlup.taxa}`);

// 6. Saneamento FR-A4 (SBSP3, CSMG3, SAPR11, SAPR4 dentro de -50%..+50% da cotação)
for (const tk of ['SBSP3', 'CSMG3', 'SAPR11', 'SAPR4']) {
  const at = getAtivo(tk);
  const av = at ? window.fehmirAvaliar(at) : null;
  const dist = (av && av.teto > 0 && at.preco > 0) ? (av.teto / at.preco - 1) : null;
  assert(dist != null && dist >= -0.50 && dist <= 0.50, `${tk} teto (${av && av.teto}) fora de -50%..+50% da cotação (${at && at.preco})`);
}
const avCsmg = window.fehmirAvaliar(getAtivo('CSMG3'));
assert(avCsmg && avCsmg.premioEmpresa === 0, `CSMG3 ainda com premioEmpresa ${avCsmg && avCsmg.premioEmpresa}`);
const avSbsp = window.fehmirAvaliar(getAtivo('SBSP3'));
assert(avSbsp && avSbsp.pay === 50, `SBSP3 payout esperado 50%, veio ${avSbsp && avSbsp.pay}`);

// 7. TIMS3 retrocompatibilidade
const avTim = window.fehmirAvaliar(getAtivo('TIMS3'));
assert(avTim && avTim.polVigente && avTim.base_dpa === 'guidance_piso' && avTim.teto > 0, `TIMS3 quebrou: ${JSON.stringify({ base: avTim && avTim.base_dpa, teto: avTim && avTim.teto })}`);

// 8. Edge cases com restauração garantida
const origTaee = JSON.parse(JSON.stringify(window.FEHMIR_POLITICA_DIV.TAEE11));
try {
  // (a) cap pelo histórico quando estrutural > hist
  window.FEHMIR_POLITICA_DIV.TAEE11.dpa_projetado = 9.0;
  const avCap = window.fehmirAvaliar(taee);
  assert(avCap.teto <= avCap.hist + 0.01, `Teto estrutural superou histórico: ${avCap.teto} > ${avCap.hist}`);

  // (b) dpa_projetado <= 0 -> sem perspectiva
  window.FEHMIR_POLITICA_DIV.TAEE11.dpa_projetado = 0;
  const avZero = window.fehmirAvaliar(taee);
  assert(avZero.teto === null && avZero.base_dpa === 'sem_dividendo_projetado', `DPA 0 devia dar teto null e sem_dividendo_projetado, veio ${avZero.teto} / ${avZero.base_dpa}`);

  // (c) revisão vencida & variação > 5% ações
  window.FEHMIR_POLITICA_DIV.TAEE11 = JSON.parse(JSON.stringify(origTaee));
  window.FEHMIR_POLITICA_DIV.TAEE11.rever_em = '2020-01-01';
  window.FEHMIR_POLITICA_DIV.TAEE11.acoes_cadastro = Math.round(origTaee.acoes_cadastro * 0.8);
  const avExp = window.fehmirAvaliar(taee);
  assert(avExp.polExpirada === true, 'polExpirada devia ser true');
  assert(avExp.polAcoesMudou === true, 'polAcoesMudou devia ser true');

  // (d) entrada sem URL primária é ignorada
  const bbse = getAtivo('BBSE3');
  const avBbseAntes = window.fehmirAvaliar(bbse);
  window.FEHMIR_POLITICA_DIV.BBSE3 = { tipo: 'estrutural', dpa_projetado: 1.0, documento: 'sem-url' };
  const avBbseDepois = window.fehmirAvaliar(bbse);
  assert(!avBbseDepois.polVigente && Math.abs(avBbseDepois.teto - avBbseAntes.teto) < 0.01, 'Entrada sem URL primária não foi ignorada');
  delete window.FEHMIR_POLITICA_DIV.BBSE3;

  // (e) FII é ignorado mesmo se colocado no cadastro
  const hglg = getAtivo('HGLG11');
  if (hglg) {
    window.FEHMIR_POLITICA_DIV.HGLG11 = { tipo: 'estrutural', dpa_projetado: 2.0, documento: 'https://fnet.bmfbovespa.com.br/' };
    const avFii = window.fehmirAvaliar(hglg);
    assert(!avFii.polVigente, 'FII devia ignorar FEHMIR_POLITICA_DIV');
    delete window.FEHMIR_POLITICA_DIV.HGLG11;
  }
} finally {
  window.FEHMIR_POLITICA_DIV.TAEE11 = origTaee;
}

// 9. FR-012 Realismo 60 meses
const rmTaee = window.fehmirRealismoPreco('TAEE11', compraTaee, avTaee.teto);
assert(rmTaee && rmTaee.total === 60 && typeof rmTaee.mesesCompra === 'number' && typeof rmTaee.mesesTeto === 'number', 'fehmirRealismoPreco TAEE11 inválido');
const rmZero = window.fehmirRealismoPreco('TAEE11', 1.0, 2.0);
assert(rmZero && rmZero.zerado === true && rmZero.mesesCompra === 0, 'fehmirRealismoPreco zerado falhou');

// 10. UI Modal (TAEE11 e CMIG4)
if (typeof openModal === 'function') {
  openModal('TAEE11');
  await new Promise(r => setTimeout(r, 150));
  const polHtml = document.getElementById('m-politica-nova-row')?.innerHTML || '';
  const realHtml = document.getElementById('m-realismo-row')?.innerHTML || '';
  assert(polHtml.includes('href="https://'), 'Modal TAEE11 sem link primário clicável');
  assert(polHtml.includes('só conferência'), 'Modal TAEE11 sem histórico só conferência');
  assert(!polHtml.includes('§'), 'Modal TAEE11 não pode citar § na UI');
  assert(realHtml.includes('60 meses'), `Modal TAEE11 sem realismo 60m (${realHtml})`);
  if (typeof closeTicketModal === 'function') closeTicketModal();
}

const n2 = v => (v != null && isFinite(v)) ? +Number(v).toFixed(2) : null;
return {
  falhas: falhas.length,
  mensagens: falhas,
  amostra: {
    TAEE11: avTaee && { teto: n2(avTaee.teto), taxa: avTaee.taxa, compra: n2(compraTaee) },
    ISAE4: avIsae && { teto: n2(avIsae.teto), taxa: avIsae.taxa, compra: n2(compraIsae), semVolta: n2(avIsae.tetoSemVolta) },
    CMIG4: avCmig && { teto: n2(avCmig.teto), taxa: avCmig.taxa, compra: n2(compraCmig), semVolta: n2(avCmig.tetoSemVolta) },
    PETR4: avPetr && { teto: n2(avPetr.teto), taxa: avPetr.taxa, compra: n2(compraPetr) }
  }
};
