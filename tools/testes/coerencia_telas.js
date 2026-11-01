// Feature 006: o mesmo dado tem de ser igual em todas as telas
const sleep = ms => new Promise(r => setTimeout(r, ms));
const g = id => document.getElementById(id)?.textContent?.trim() || '';
const num = t => { const m = String(t).match(/-?[\d.]+,\d{2}/); return m ? parseFloat(m[0].replace(/\./g, '').replace(',', '.')) : null; };
const div = [];
const patr = fehmirPatrimonioAtual();
const termo0 = g('sn-regime');
// patrimônio
switchMainTab('ativos'); setCarteiraView('geral'); await sleep(600);
const patrGeral = num(g('ward-kpi-patrimonio') || document.querySelector('.mc-ward-val, #mc-patrimonio')?.textContent);
setCarteiraView('rentabilidade'); await sleep(600);
const patrRent = num(g('rent-kpi-patrimonio'));
if (Math.abs(patrRent - patr) > 0.01) div.push(`Rentabilidade patrimônio ${patrRent} ≠ ${patr}`);
setCarteiraView('rebal'); await sleep(600);
const rebSub = num(g('reb-total-sub'));
if (Math.abs(rebSub - patr) > 0.01) div.push(`Rebalanceamento total ${rebSub} ≠ ${patr}`);
const pos = calcularPosicoesExtrato();
document.querySelectorAll('.reb-q').forEach(i => { const q = pos[i.dataset.t]?.quant; if (q != null && Math.abs(+i.value - q) > 1e-9) div.push(`reb-q ${i.dataset.t} ${i.value} ≠ ${q}`); });
const btnReinv = g('btn-reinvestir-prov');
switchMainTab('projecao'); await sleep(800);
const ini = +document.getElementById('in-inicial').value;
if (Math.abs(ini - patr) > 0.01) div.push(`Projeção inicial ${ini} ≠ ${patr}`);
const meta = [...document.querySelectorAll('#tbody-meta-aposentadoria tr')].map(tr => [tr.children[0].textContent.trim(), +tr.children[4].textContent.trim()]);
const abertos = Object.entries(pos).filter(([t, p]) => p.quant > 0 && !['ETFS', 'CRIPTO'].includes(_determinarCategoriaTicker(t))).map(([t]) => t);
meta.forEach(([t, q]) => { if (!pos[t] || Math.abs(pos[t].quant - q) > 1e-9) div.push(`Meta: ${t} você tem ${q} ≠ extrato ${pos[t]?.quant}`); });
abertos.forEach(t => { if (!meta.find(m => m[0] === t)) div.push(`Meta: falta ${t}`); });
// termômetro
switchMainTab('conselheiro'); await sleep(1500);
const termo1 = g('sn-regime');
if (termo0 !== termo1) div.push(`Termômetro ${termo0} → ${termo1}`);
// conselheiro × teto oficial
fehmirHoldings().rows.forEach(r => { const o = tetoOficial(r.t).teto; if (Math.abs((r.teto || 0) - (o || 0)) > 0.01) div.push(`Conselheiro teto ${r.t} ${r.teto} ≠ ${o}`); });
// alertas × teto oficial
switchMainTab('ativos'); setCarteiraView('geral'); await sleep(500);
window.__alertasTodos = true; renderAlertasAnalista();
[...document.querySelectorAll('#alertas-lista > div')].forEach(d => {
  const tx = d.textContent; const m = tx.match(/^\s*★?\s*([A-Z0-9]{4,6})\b.*?teto R\$\s*([\d.]+,\d{2})/);
  if (m) { const o = tetoOficial(m[1]).teto; if (o && Math.abs(num(m[2]) - o) > 0.01) div.push(`Alerta ${m[1]} teto ${m[2]} ≠ ${o.toFixed(2)}`); }
});
// contagem de ativos
const nAtivos = Object.values(pos).filter(p => p.quant > 0).length;
const nCob = +g('stat-total');
const nCad = [...BASE_STOCKS, ...OUT_OF_BASE, ...FIIS].filter(r => quantidadeAtual(r) > 0).length;
if (nCob !== nCad) div.push(`Ativos cobertos ${nCob} ≠ ${nCad} (ações+FIIs abertos)`);
// payout análise × modal (TAEE11)
switchMainTab('analise'); await sleep(300); fehmirAnalisar('TAEE11'); await sleep(800);
const payAn = (document.body.innerText.match(/Payout\s*\n?\s*([\d,.]+)%/) || [])[1];
const av = fehmirAvaliar(Object.assign({}, RADAR_DATA.find(x => x.t === 'TAEE11'), BASE_STOCKS.find(x => x.t === 'TAEE11')));
if (av.payoutUsado != null && payAn && Math.abs(parseFloat(payAn.replace(',', '.')) - av.payoutUsado) > 1) div.push(`Payout Análise ${payAn} ≠ modal ${av.payoutUsado}`);
// DY / P/L / P/VP iguais entre tabelas de ações e FIIs, Meus Ativos e o modal (fonte única: robô + CVM)
switchMainTab('ativos'); setCarteiraView('acoes'); await sleep(500);
const lerTab = (sel, cols) => { const o = {}; document.querySelectorAll(sel + ' tr').forEach(tr => { const t = tr.querySelector('.ticker b, td b')?.textContent.trim(); if (!t) return; o[t] = {}; for (const [k, i] of Object.entries(cols)) o[t][k] = num(tr.children[i]?.textContent || '') ?? parseFloat((tr.children[i]?.textContent || '').replace(',', '.')); }); return o; };
const tabAcoes = Object.assign(lerTab('#tbody-base', { dy: 3 }), lerTab('#tbody-fora', { dy: 3 }));
setCarteiraView('fiis'); await sleep(500);
const tabFiis = {}; document.querySelectorAll('#tbody-fiis tr').forEach(tr => { const t = tr.children[0]?.textContent.trim().split(/\s/)[0]; const td = [...tr.children].find(c => c.dataset.label === 'DY 12m'); if (t && td) tabFiis[t] = { dy: parseFloat(td.textContent.replace(',', '.')) }; });
setCarteiraView('geral'); localStorage.setItem('barsi-ma-abertos', JSON.stringify({ 'AÇÕES': true, 'FIIS': true })); renderMeusAtivos(); await sleep(300);
const ma = {}; document.querySelectorAll('#ma-body .ma-table').forEach(tb => { const ths = [...tb.querySelectorAll('th')].map(h => h.textContent); const iDy = ths.indexOf('DY 12m'), iPl = ths.indexOf('P/L'), iPvp = ths.indexOf('P/VP'); tb.querySelectorAll('tbody tr').forEach(tr => { const c = tr.children; ma[c[0].textContent.trim().split(/\s/)[0]] = { dy: parseFloat(c[iDy].textContent.replace(',', '.')), pl: parseFloat(c[iPl].textContent.replace(',', '.')), pvp: parseFloat(c[iPvp].textContent.replace(',', '.')) }; }); });
for (const t of Object.keys(ma)) {
  openModal(t); await sleep(350);
  const mdy = parseFloat(document.getElementById('m-dy').textContent.replace(',', '.'));
  const mpl = parseFloat(document.getElementById('m-pl').textContent.replace(',', '.'));
  const mpvp = parseFloat(document.getElementById('m-pvp').textContent.replace(',', '.'));
  document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active')); await sleep(100);
  const tab = tabAcoes[t] || tabFiis[t];
  if (tab && isFinite(tab.dy) && Math.abs(tab.dy - mdy) > 0.011) div.push(`DY ${t}: tabela ${tab.dy} ≠ modal ${mdy}`);
  if (isFinite(ma[t].dy) && Math.abs(ma[t].dy - mdy) > 0.011) div.push(`DY ${t}: Meus Ativos ${ma[t].dy} ≠ modal ${mdy}`);
  if (isFinite(ma[t].pl) && isFinite(mpl) && Math.abs(ma[t].pl - mpl) > 0.011) div.push(`P/L ${t}: Meus Ativos ${ma[t].pl} ≠ modal ${mpl}`);
  if (isFinite(ma[t].pvp) && isFinite(mpvp) && Math.abs(ma[t].pvp - mpvp) > 0.011) div.push(`P/VP ${t}: Meus Ativos ${ma[t].pvp} ≠ modal ${mpvp}`);
}
// textos fixos
const html = document.documentElement.outerHTML;
['RZTR11 segue o caso', 'MELK3 e PETR4 mostram', 'calibração do teto de BBSE3', '(R$ 445)'].forEach(t => { if (html.includes(t)) div.push('texto fixo: ' + t); });
const prov = fehmirProventosRecebidos();
return { divergencias: div.length, div, patr, termo: termo1, nAtivos, nCob, provRecebidos: prov.total, provItens: prov.itens.length, provAntes: fehmirProventosAntesDoPainel(), btnReinv, payAn, payModal: av.payoutUsado };
