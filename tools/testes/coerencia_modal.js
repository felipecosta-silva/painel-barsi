// Para cada ativo: abre o modal, passa por todas as abas e junta pares rótulo → valor; acusa rótulo com valores diferentes
const sleep = ms => new Promise(r => setTimeout(r, ms));
const LBL = [['DY', /^(dividend yield|dy( 12m| \(12m\)| atual)?|yield atual)$/i], ['PAYOUT', /^payout( \(%\))?$/i], ['P/L', /^p\/l$/i], ['P/VP', /^p\/vp$/i], ['ROE', /^roe$/i],
  ['TETO', /^(teto( \(régua\))?|preço teto( \(régua\))?|teto final|teto oficial)$/i], ['LPA', /^lpa$/i], ['VPA', /^vpa$/i], ['DPA12', /^dpa \(12m\)$/i], ['COTACAO', /^(cotação atual|preço|preço atual)$/i]];
const norm = v => { const m = String(v).replace(/\s/g, '').match(/-?[\d.]*\d,\d+|-?\d+\.\d+|-?\d+/); if (!m) return null; let s = m[0]; s = s.includes(',') ? s.replace(/\./g, '').replace(',', '.') : s; return +(+s).toFixed(2); };
const tickers = [...new Set([...BASE_STOCKS, ...OUT_OF_BASE, ...FIIS].filter(r => quantidadeAtual(r) > 0).map(r => r.t))];
const out = {};
for (const t of tickers) {
  openModal(t); await sleep(500);
  const vals = {};
  for (const tab of ['grafico', 'historico-dy', 'teto', 'fcd', 'analistas', 'origem']) {
    try { switchModalTab(tab); } catch (e) {}
    await sleep(350);
    const modal = document.querySelector('.modal-overlay.open, .modal.open, #modal-overlay, [id*="modal"][style*="flex"]') || document.body;
    const lines = modal.innerText.split('\n').map(s => s.trim()).filter(Boolean);
    for (let i = 0; i < lines.length - 1; i++) {
      const lb = lines[i].replace(/[^A-Za-zÀ-ú0-9/() %.-]/g, '').trim(); for (const [k, re] of LBL) if (re.test(lb)) { const v = norm(lines[i + 1]); if (v != null) (vals[k] = vals[k] || new Set()).add(v + ' @' + tab); }
    }
  }
  const dif = {};
  for (const k in vals) { const nums = new Set([...vals[k]].map(x => x.split(' @')[0])); if (nums.size > 1) dif[k] = [...vals[k]]; }
  if (Object.keys(dif).length) out[t] = dif;
  try { closeTicketModal(); } catch (e) {} await sleep(150);
}
return out;
