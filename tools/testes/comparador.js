// Spec 005: comparador de retorno total (SC-001 a SC-003 e cenários de aceite)
const falhas = [];
const ok = (cond, msg) => { if (!cond) falhas.push(msg); };
const H = window.FEHMIR_HIST_MENSAL, I = window.FEHMIR_IDX_MENSAL;
ok(H && Object.keys(H).length > 50, 'série mensal ausente');
// FR-003: conta pura — 2 meses, provento de 1 no mês 2 a preço 10 → 1,1 cota × 10 = 11 sobre 10
const r = fehmirRetornoTotal({ i: '2020-01', c: [10, 10, 10], d: { 1: 1 } }, '2020-01', '2020-03');
ok(r && Math.abs(r.pts[2][1] - 1.1) < 1e-9, 'retorno total da série de teste: ' + (r && r.pts[2][1]));
const rTx = fehmirRetornoTotal({ i: '2020-01', r: [1, 1, 1] }, '2020-01', '2020-03');
ok(rTx && Math.abs(rTx.pts[2][1] - 1.0201) < 1e-9, 'taxa acumulada: ' + (rTx && rTx.pts[2][1]));
// SC-001 (CDI 5 anos, Investidor10 R$ 1.804,70 em 30/10/2026): até 1%
const fim = cmpSomaMeses(I.CDI.i, I.CDI.r.length - 1), cdi5 = fehmirRetornoTotal(I.CDI, cmpSomaMeses(fim, -60), fim);
const vCdi = cdi5.pts[cdi5.pts.length - 1][1] * 1000;
// SC-002: MXRF11 entre os pares do KNSC11
const sug = fehmirParesSugeridos('KNSC11', 5);
ok(sug.pares.includes('MXRF11'), 'MXRF11 fora dos pares do KNSC11: ' + sug.pares.join(','));
// ficha do ativo: aba Comparar
openModal('MXRF11'); await new Promise(r => setTimeout(r, 500));
switchModalTab('comparar'); await new Promise(r => setTimeout(r, 400));
const body = document.getElementById('m-cmp-body');
ok(body && body.querySelector('.cmp-svg path'), 'gráfico da aba Comparar não desenhou');
ok(/hoje seriam/i.test(body.innerText), 'tabela "hoje seriam" ausente');
const nLinhas = body.querySelectorAll('.cmp-svg path').length;
// legenda: clicar esconde a série
const leg = [...body.querySelectorAll('.cmp-leg')].find(b => /^CDI/.test(b.textContent.trim()));
leg && leg.click(); await new Promise(r => setTimeout(r, 200));
ok(document.querySelectorAll('#m-cmp-body .cmp-svg path').length === nLinhas - 1, 'legenda não escondeu o CDI');
// hover
const rect = document.querySelector('#m-cmp-body .cmp-svg rect'); const bb = rect.getBoundingClientRect();
cmpHover({ clientX: bb.left + bb.width / 2, clientY: bb.top + 10 }, 'modal');
ok(document.querySelector('#m-cmp-body .cmp-tip').style.display !== 'none', 'dica do gráfico não abriu');
// ticker sem histórico: aviso, sem curva inventada
cmpAcao('modal', 'digitado', 'ZZZZ11');
ok(/sem histórico mensal/.test(document.getElementById('m-cmp-body').innerText), 'sem aviso para ticker sem histórico');
closeTicketModal();
// Radar › Comparar retorno
setRadarView('comparar'); await new Promise(r => setTimeout(r, 400));
ok(document.querySelector('#radar-cmp-body .cmp-svg path'), 'comparador livre não desenhou');
const kn = fehmirRetornoTotal(H.KNSC11, cmpSomaMeses(fim, -60), fim);
return { falhas: falhas.length, detalhes: falhas, cdi5: +vCdi.toFixed(2), desvioCdi: +((vCdi / 1804.70 - 1) * 100).toFixed(2), knsc11: kn && { desde: kn.desde, v: +(kn.pts[kn.pts.length - 1][1] * 1000).toFixed(2) }, pares: sug };
