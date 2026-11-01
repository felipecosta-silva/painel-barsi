// Spec 007 US2 e US5: camada única de posições e hora de cada preço (com a Brapi simulada; nenhum token real)
const falhas = [];
const ok = (cond, msg) => { if (!cond) falhas.push(msg); };
await new Promise(r => setTimeout(r, 1500));
// US2: a fachada devolve as mesmas posições do extrato
const pos = FEHMIR.posicoes(), ext = carregarExtrato();
ok(Object.keys(pos).length > 0, 'FEHMIR.posicoes() vazio');
const somaManual = {};
ext.slice().sort((a, b) => a.data.localeCompare(b.data)).forEach(t => {
  if (t.tipo === 'Compra' || t.tipo === 'Reinvestimento') somaManual[t.ticker] = (somaManual[t.ticker] || 0) + (+t.quant || 0);
  else if (t.tipo === 'Venda') somaManual[t.ticker] = Math.max(0, (somaManual[t.ticker] || 0) - (+t.quant || 0));
});
Object.keys(somaManual).forEach(t => ok(Math.abs((pos[t] ? pos[t].quant : 0) - somaManual[t]) < 1e-6, `quantidade de ${t}: camada ${pos[t] && pos[t].quant} ≠ extrato ${somaManual[t]}`));
const ev = fehmirEvolucaoMensal(null, window.FEHMIR_HIST, 'inicio').slice(-1)[0];
ok(ev && ev.aplicado > 0, 'evolução sem aplicado');
// US5: selo sem token e dica de fonte nas células de preço
const selo0 = document.getElementById('brapi-status').textContent;
ok(/^Preços: robô de \d\d\/\d\d · ativar ao vivo$/.test(selo0), 'selo sem token: ' + selo0);
ok(!!document.querySelector('td[data-label="Preço"][title^="Preço: "]'), 'célula de preço sem dica de fonte');
// US5: Brapi simulada → preço ao vivo vale no Meus Ativos, no patrimônio e na fachada
localStorage.setItem('barsi-brapi-token', 'teste-simulado');
localStorage.removeItem('barsi-quote-cache-v1');
const fetchOrig = window.fetch, agora = new Date().toISOString();
window.fetch = async () => ({ ok: true, json: async () => ({ results: [{ regularMarketPrice: 12.34, regularMarketTime: agora }] }) });
const alvo = Object.keys(pos).find(t => pos[t].quant > 0 && /11$/.test(t)) || 'MXRF11';
await fetchBrapiQuotes({ tickers: [alvo] });
window.fetch = fetchOrig;
localStorage.removeItem('barsi-brapi-token');
ok(FEHMIR.preco(alvo).preco === 12.34, `preço ao vivo não chegou ao obterPrecoAtivo (${alvo})`);
ok(FEHMIR.fontePreco(alvo).fonte === 'Brapi', 'fonte do preço não é Brapi');
ok(/Brapi|Ao vivo/.test(document.getElementById('brapi-status').textContent), 'selo não mudou para a Brapi');
ok(FEHMIR.indicadores(alvo) && FEHMIR.indicadores(alvo).preco === 12.34, 'indicadores sem o preço novo');
ok(fehmirEmPregao(new Date('2026-11-03T15:00:00Z')) === true && fehmirEmPregao(new Date('2026-11-01T15:00:00Z')) === false, 'horário de pregão');
return { falhas: falhas.length, detalhes: falhas.slice(0, 15), alvo, selo0 };
