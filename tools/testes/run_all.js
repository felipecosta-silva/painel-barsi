// Bateria de regressão do painel (spec 007 US7). Roda cada teste num Chrome novo, em sequência, e falha se algum critério não bater.
// Uso: node tools/testes/run_all.js [filtro]      (no GitHub Actions: .github/workflows/testes.yml)
const fs = require('fs');
const path = require('path');
const { avaliar } = require('./cdp');

const TESTES = [
  { arq: 'camada_e_precos.js', nome: 'Camada de dados e hora dos preços', ok: v => v && v.falhas === 0 },
  { arq: 'comparador.js', nome: 'Comparador de retorno total', ok: v => v && v.falhas === 0 && Math.abs(v.desvioCdi) <= 1 },
  { arq: 'coerencia_telas.js', nome: 'Mesmo número em todas as telas', ok: v => v && v.divergencias === 0 },
  { arq: 'coerencia_modal.js', nome: 'Mesmo número dentro da ficha do ativo', ok: v => v && typeof v === 'object' && Object.keys(v).length === 0 },
  { arq: 'tetos_telas.js', nome: 'Teto igual em todas as telas', ok: v => v && v.divergenciasCount === 0 },
  { arq: 'fii_recorrente.js', nome: 'Resultado recorrente dos FIIs e veredito do aporte', ok: v => v && v.falhas === 0 },
  { arq: 'meta_renda.js', nome: 'Meta de renda ajustável e calculadora projetiva', ok: v => v && v.falhas === 0 },
  { arq: 'varredura_abas.js', nome: 'Todas as abas sem erro de JavaScript', ok: v => v && v.errsTotal === 0 },
  { arq: 'ordens_e_precos.js', nome: 'Ordens abertas, preço velho e conferência', ok: v => v && v.falhas === 0 }
];

(async () => {
  const filtro = process.argv[2];
  let falhou = 0;
  for (const t of TESTES.filter(x => !filtro || x.arq.includes(filtro))) {
    const ini = Date.now();
    const r = await avaliar(fs.readFileSync(path.join(__dirname, t.arq), 'utf8'));
    const passou = !r.excecao && t.ok(r.valor) && r.erros.length === 0;
    if (!passou) falhou++;
    console.log(`${passou ? 'OK   ' : 'FALHA'} ${t.nome} (${t.arq}, ${Math.round((Date.now() - ini) / 1000)} s)`);
    if (!passou) console.log('      ' + (r.excecao || JSON.stringify(r.valor)).slice(0, 1500) + (r.erros.length ? '\n      erros JS: ' + r.erros.slice(0, 5).join(' | ') : ''));
  }
  console.log(falhou ? `\n${falhou} teste(s) falharam.` : '\nTodos os testes passaram.');
  setTimeout(() => process.exit(falhou ? 1 : 0), 800);
})();
