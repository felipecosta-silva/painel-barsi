const sleep = ms => new Promise(r => setTimeout(r, ms));
const errs = [];
const oe = console.error; console.error = (...a) => { errs.push(a.map(String).join(' ').slice(0,200)); oe(...a); };
window.addEventListener('error', e => errs.push('ERR ' + (e.message||'') + ' @' + (e.lineno||'')));
window.addEventListener('unhandledrejection', e => errs.push('REJ ' + String(e.reason).slice(0,200)));
const pads = [/\bNaN\b/, /\bundefined\b/, /\bInfinity\b/, /\[object/, /\bnull\b/, /Carregando/i, /R\$\s*-?0,00\b/, /lorem/i, /TODO|FIXME/];
const visText = () => { const out=[]; const w=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n; while(n=w.nextNode()){ const el=n.parentElement; if(!el||['SCRIPT','STYLE'].includes(el.tagName)) continue; const t=n.textContent.trim(); if(!t) continue; if(el.offsetParent===null && getComputedStyle(el).position!=='fixed') continue; out.push([t, el]); } return out; };
const scan = (loc) => { const hits=[]; for (const [t,el] of visText()) for (const p of pads) if (p.test(t)) { const id = el.id || (el.closest('[id]')?.id) || el.className; hits.push(`${p.source} :: "${t.slice(0,80)}" #${id}`); break; } return hits.length ? {loc, hits: [...new Set(hits)].slice(0,12)} : null; };
const res = [];
const step = async (loc, fn) => { const e0 = errs.length; try { await fn(); } catch(e) { errs.push(loc+' THROW '+e.message); } await sleep(700); const s = scan(loc); if (s) res.push(s); if (errs.length>e0) res.push({loc, erros: errs.slice(e0)}); };
for (const t of ['ativos','conselheiro','analise','radar','mercado','projecao','calc']) await step('main:'+t, () => switchMainTab(t));
await step('main:ativos', () => switchMainTab('ativos'));
for (const v of ['geral','rentabilidade','acoes','fiis','proventos','rebal','extrato','intl','cripto','caixa']) await step('carteira:'+v, () => setCarteiraView(v));
await step('main:radar', () => switchMainTab('radar'));
for (const v of ['cards','table','podio','setorial','duelo']) await step('radar:'+v, () => setRadarView(v));
const tick = [...new Set([...BASE_STOCKS,...OUT_OF_BASE,...FIIS].map(x=>x.t))];
for (const t of tick) { for (const mt of ['grafico','historico-dy','teto','fcd','analistas','origem']) await step(`modal:${t}:${mt}`, async () => { if (!document.querySelector('.modal.open, .modal-overlay.open, #modal.open')) openModal(t); await sleep(400); switchModalTab(mt); }); try { closeTicketModal(); } catch(e){} await sleep(200); }
return { total: res.length, res, errsTotal: errs.length };
