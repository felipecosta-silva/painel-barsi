// Abre o painel num Chrome headless com perfil novo, espera carregar e avalia uma expressão JS
// (pode ser async e deve usar `return`). Funciona no Windows (Chrome padrão) e no GitHub Actions (google-chrome).
//
// Linha de comando: node tools/testes/cdp.js <arquivo-com-expressao.js> [--shot saida.png] [--w 1366] [--h 900] [--theme dark]
// Como módulo:      const { avaliar } = require('./cdp'); const { valor, erros } = await avaliar(codigo, { w, h });
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const RAIZ = path.resolve(__dirname, '..', '..');

function caminhoChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  if (process.platform === 'win32') return 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  if (process.platform === 'darwin') return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  return 'google-chrome';
}

async function avaliar(codigo, opts = {}) {
  const W = opts.w || 1366, H = opts.h || 900;
  const fileUrl = 'file:///' + path.join(RAIZ, 'painel-barsi.html').replace(/\\/g, '/').replace(/^\/+/, '');
  const port = 9400 + Math.floor(Math.random() * 400);
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'fehmir-cdp-'));
  const proc = spawn(caminhoChrome(), ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`,
    `--window-size=${W},${H}`, '--disable-gpu', '--no-sandbox', '--allow-file-access-from-files', 'about:blank'], { stdio: 'ignore' });
  const fim = () => { try { proc.kill(); } catch (e) {} setTimeout(() => { try { fs.rmSync(prof, { recursive: true, force: true }); } catch (e) {} }, 500); };
  try {
    let tabs;
    for (let i = 0; i < 50 && !tabs; i++) {
      await new Promise(r => setTimeout(r, 400));
      try { tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch (e) {}
    }
    if (!tabs) throw new Error('Chrome não respondeu (' + caminhoChrome() + ')');
    const ws = new WebSocket(tabs.find(t => t.type === 'page').webSocketDebuggerUrl);
    let id = 1; const cb = new Map(); const erros = []; let carregou = null;
    const pronto = new Promise(r => { carregou = r; });
    ws.onmessage = e => {
      const d = JSON.parse(e.data);
      if (d.id && cb.has(d.id)) { cb.get(d.id)(d.result || d.error); cb.delete(d.id); }
      if (d.method === 'Page.loadEventFired') carregou();
      if (d.method === 'Runtime.exceptionThrown') erros.push(d.params.exceptionDetails.exception?.description?.split('\n')[0] || d.params.exceptionDetails.text);
    };
    const send = (method, params = {}) => new Promise(r => { const i = id++; cb.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
    await new Promise(r => ws.onopen = r);
    await send('Runtime.enable'); await send('Page.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: W < 600 });
    if (opts.theme) await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: opts.theme }] });
    await send('Page.navigate', { url: fileUrl });
    await Promise.race([pronto, new Promise(r => setTimeout(r, 30000))]);
    await new Promise(r => setTimeout(r, opts.espera || 4000));
    const res = await send('Runtime.evaluate', { expression: `(async()=>{ ${codigo} })()`, awaitPromise: true, returnByValue: true });
    let shot = null;
    if (opts.shot) {
      await new Promise(r => setTimeout(r, 600));
      const s = await send('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(opts.shot, Buffer.from(s.data, 'base64'));
      shot = opts.shot;
    }
    ws.close();
    if (res.exceptionDetails) return { excecao: res.exceptionDetails.exception?.description || res.exceptionDetails.text, erros, shot };
    return { valor: res.result?.value, erros, shot };
  } finally {
    fim();
  }
}
module.exports = { avaliar, RAIZ };

if (require.main === module) {
  const args = process.argv.slice(2);
  const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
  const codigo = args[0] ? fs.readFileSync(args[0], 'utf8') : 'return 1';
  avaliar(codigo, { shot: opt('--shot', null), w: +opt('--w', 1366), h: +opt('--h', 900), theme: opt('--theme', null) }).then(r => {
    if (r.excecao) console.log('EXCEÇÃO:', r.excecao);
    else console.log(JSON.stringify(r.valor, null, 1));
    if (r.shot) console.log('captura:', r.shot);
    if (r.erros.length) console.log('ERROS JS:', r.erros.slice(0, 5));
    setTimeout(() => process.exit(0), 600);
  });
}
