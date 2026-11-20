// Cookies do YouTube para o yt-dlp, tirados de um perfil próprio do Chrome (o Chrome não deixa ler os do perfil normal).
// Uso:
//   node tools/transcricao/cookies_youtube.js --login   → abre o Chrome do robô; faça login no YouTube (conta com as assinaturas) e feche a janela
//   node tools/transcricao/cookies_youtube.js           → headless: abre o YouTube, renova a sessão e grava cookies.txt
// Tudo fica em %LOCALAPPDATA%\painel-transcricao (fora do OneDrive e do Git). O cookies.txt dá acesso à conta: nunca copiar para o projeto.
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const BASE = path.join(process.env.LOCALAPPDATA, 'painel-transcricao');
const PERFIL = path.join(BASE, 'chrome-perfil');
const SAIDA = path.join(BASE, 'cookies.txt');
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
fs.mkdirSync(BASE, { recursive: true });

if (process.argv.includes('--login')) {
  console.log('Abrindo o Chrome do robô. Faça login no YouTube com a conta que tem as assinaturas de membro e depois feche a janela.');
  const p = spawn(CHROME, [`--user-data-dir=${PERFIL}`, '--no-first-run', '--no-default-browser-check',
    'https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/'], { stdio: 'ignore' });
  p.on('exit', () => { console.log('Janela fechada. Agora rode sem --login para gravar os cookies.'); });
  return;
}

const port = 9800 + Math.floor(Math.random() * 150);
const proc = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${PERFIL}`,
  '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });

const fim = (cod, msg) => { if (msg) console.log(msg); try { proc.kill(); } catch (e) {} setTimeout(() => process.exit(cod), 800); };
setTimeout(() => fim(2, 'ERRO: tempo esgotado ao falar com o Chrome (o Chrome do robô está aberto em outra janela? feche-a).'), 60000);

(async () => {
  let tabs;
  for (let i = 0; i < 40 && !tabs; i++) {
    await new Promise(r => setTimeout(r, 400));
    try { tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch (e) {}
  }
  if (!tabs) return fim(2, 'ERRO: o Chrome não abriu a porta de depuração (perfil em uso por outra janela?).');
  const ws = new WebSocket(tabs.find(t => t.type === 'page').webSocketDebuggerUrl);
  let id = 1; const cb = new Map();
  ws.onmessage = e => { const d = JSON.parse(e.data); if (d.id && cb.has(d.id)) { cb.get(d.id)(d.result || d.error); cb.delete(d.id); } };
  const send = (method, params = {}) => new Promise(r => { const i = id++; cb.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise(r => ws.onopen = r);
  await send('Network.enable');
  await send('Page.navigate', { url: 'https://www.youtube.com/' });
  await new Promise(r => setTimeout(r, 7000));   // deixa o YouTube renovar a sessão (rotaciona __Secure-*PSIDTS)
  const { cookies = [] } = await send('Network.getAllCookies');
  const uteis = cookies.filter(c => /(^|\.)(youtube\.com|google\.com)$/.test(c.domain.replace(/^\./, '')) || /youtube\.com|google\.com/.test(c.domain));
  const logado = uteis.some(c => c.name === 'LOGIN_INFO') && uteis.some(c => /SAPISID$/.test(c.name));
  const linhas = ['# Netscape HTTP Cookie File', '# Gerado por tools/transcricao/cookies_youtube.js — NÃO compartilhar', ''];
  for (const c of uteis) {
    const dom = c.domain;
    linhas.push([dom, dom.startsWith('.') ? 'TRUE' : 'FALSE', c.path, c.secure ? 'TRUE' : 'FALSE',
      Math.floor(c.expires > 0 ? c.expires : Date.now() / 1000 + 86400 * 30), c.name, c.value].join('\t'));
  }
  fs.writeFileSync(SAIDA, linhas.join('\n') + '\n');
  ws.close();
  fim(logado ? 0 : 3, logado ? `OK: ${uteis.length} cookies gravados (sessão logada).`
    : 'AVISO: o perfil do robô não está logado no YouTube. Rode: node tools/transcricao/cookies_youtube.js --login');
})();
