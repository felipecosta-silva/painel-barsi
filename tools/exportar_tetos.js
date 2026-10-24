// Fehmir · exporta o teto oficial (fehmirAvaliar, a MESMA função do painel) e a carteira para dados/tetos.js.
// Abre painel-barsi.html em Chrome headless (perfil limpo: Extrato inicial + dados/lancamentos_assistente.js).
// Uso: node tools/exportar_tetos.js        (CHROME_PATH opcional; padrão Windows local ou google-chrome no Linux)
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const RAIZ = path.resolve(__dirname, '..');
const SAIDA = path.join(RAIZ, 'dados', 'tetos.js');
const chrome = process.env.CHROME_PATH ||
  (process.platform === 'win32' ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe' : 'google-chrome');
const url = 'file:///' + path.join(RAIZ, 'painel-barsi.html').replace(/\\/g, '/').replace(/^\//, '');
const porta = 9600 + Math.floor(Math.random() * 300);
const perfil = fs.mkdtempSync(path.join(os.tmpdir(), 'fehmir-tetos-'));

const proc = spawn(chrome, ['--headless=new', `--remote-debugging-port=${porta}`, `--user-data-dir=${perfil}`,
  '--disable-gpu', '--no-sandbox', '--allow-file-access-from-files', 'about:blank'], { stdio: 'ignore' });

const EXPR = `(() => {
  const U = window.fehmirUniverso(), H = window.FEHMIR_HIST || {};
  const tetos = {};
  for (const t of Object.keys(U)) {
    const a = U[t]; if (!a) continue;
    let av = null; try { av = window.fehmirAvaliar(a); } catch (e) { continue; }
    if (!av || !(av.teto > 0)) continue;                       // sem teto ⇒ ausente (nunca 0)
    const h = H[t]; const preco = h && h.c && h.c.length ? h.c[h.c.length - 1] : (a.preco || null);
    const mMin = av.margemMin != null ? av.margemMin : 10;
    tetos[t] = { teto: +av.teto.toFixed(2), compra: +(av.teto * (1 - mMin / 100)).toFixed(2), margemMin: mMin,
      metodo: av.metodo || '', setor: av.setorNome || a.setor || '', src: String(av.src || '').slice(0, 400),
      preco: preco != null ? +(+preco).toFixed(2) : null, data: h && h.d ? h.d[h.d.length - 1] : null };
  }
  const pos = calcularPosicoesExtrato(carregarExtrato()), carteira = {};
  for (const [t, p] of Object.entries(pos)) if (p && p.quant > 1e-9) carteira[t] = +p.quant.toFixed(8);
  return { tetos, carteira };
})()`;

(async () => {
  let alvos;
  for (let i = 0; i < 40 && !alvos; i++) {
    await new Promise(r => setTimeout(r, 500));
    try { alvos = await (await fetch(`http://127.0.0.1:${porta}/json`)).json(); } catch (e) {}
  }
  if (!alvos) throw new Error('Chrome não respondeu em ' + chrome);
  const ws = new WebSocket(alvos.find(t => t.type === 'page').webSocketDebuggerUrl);
  let id = 1; const cb = new Map();
  ws.onmessage = e => { const d = JSON.parse(e.data); if (d.id && cb.has(d.id)) { cb.get(d.id)(d.result || d); cb.delete(d.id); } };
  const send = (method, params = {}) => new Promise(r => { const i = id++; cb.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise(r => ws.onopen = r);
  await send('Page.enable');
  await send('Page.navigate', { url });
  await new Promise(r => setTimeout(r, 6000));
  const res = await send('Runtime.evaluate', { expression: EXPR, returnByValue: true });
  if (res.exceptionDetails || !res.result || !res.result.value) throw new Error('Falha ao avaliar o painel: ' + JSON.stringify(res.exceptionDetails || res).slice(0, 400));
  const { tetos, carteira } = res.result.value;
  const meta = { gerado: new Date().toISOString().slice(0, 16).replace('T', ' '), ativos: Object.keys(tetos).length, carteira: Object.keys(carteira).length,
    fonte: 'fehmirAvaliar do painel-barsi.html (mesma régua do Radar) · carteira = Extrato inicial + lançamentos do assistente' };
  fs.writeFileSync(SAIDA, '/* Gerado por tools/exportar_tetos.js — não editar à mão. */\n' +
    'window.FEHMIR_TETOS_META = ' + JSON.stringify(meta, null, 1) + ';\n' +
    'window.FEHMIR_CARTEIRA = ' + JSON.stringify(carteira) + ';\n' +
    'window.FEHMIR_TETOS = ' + JSON.stringify(tetos, null, 1) + ';\n', 'utf8');
  console.log(`OK: ${meta.ativos} tetos e ${meta.carteira} ativos na carteira em dados/tetos.js`);
  ws.close(); proc.kill();
  setTimeout(() => { try { fs.rmSync(perfil, { recursive: true, force: true }); } catch (e) {} process.exit(0); }, 400);
})().catch(e => { console.error('ERRO:', e.message); proc.kill(); process.exit(1); });
