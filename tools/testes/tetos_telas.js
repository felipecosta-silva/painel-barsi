// T012 / SC-002: Auditar tetos em todas as telas contra window.tetoOficial(t).teto
return (() => {
  const parseBRL = (txt) => {
    if (!txt) return null;
    const s = String(txt).trim();
    if (s === '—' || s === '-' || /sem teto/i.test(s)) return null;
    const m = s.match(/R\$\s*([\d.]+,\d{2})/) || s.match(/([\d.]+,\d{2})/);
    if (!m) return null;
    const num = parseFloat(m[1].replace(/\./g, '').replace(',', '.'));
    return isFinite(num) ? num : null;
  };

  const diffOk = (a, b) => {
    if (a == null && b == null) return true;
    if (a == null || b == null) return false;
    return Math.abs(a - b) <= 0.015;
  };

  // Garantir que o filtro do radar mostre todos os cards para auditar
  if (typeof filterRadar === 'function') {
    const sInput = document.getElementById('radar-search-input');
    if (sInput) sInput.value = '';
    if (typeof currentMacroFilter !== 'undefined') currentMacroFilter = 'todos';
    if (typeof currentSetorFilter !== 'undefined') currentSetorFilter = 'todos';
    if (typeof currentStatusFilter !== 'undefined') currentStatusFilter = 'todos';
    filterRadar();
  }

  // Coletar todos os tickers únicos da carteira e do radar
  const tickersSet = new Set();
  [...(typeof BASE_STOCKS !== 'undefined' ? BASE_STOCKS : []),
   ...(typeof OUT_OF_BASE !== 'undefined' ? OUT_OF_BASE : []),
   ...(typeof FIIS !== 'undefined' ? FIIS : []),
   ...(typeof RADAR_DATA !== 'undefined' ? RADAR_DATA : [])
  ].forEach(x => { if (x && x.t) tickersSet.add(x.t); });

  const tickers = Array.from(tickersSet);
  const divergencias = [];
  let checados = 0;

  for (const t of tickers) {
    const av = window.tetoOficial(t);
    const tetoEsp = (av && av.teto > 0) ? Number(av.teto.toFixed(2)) : null;

    // (a) Tabela B.A.S.E. / Fora / FIIs
    const stockRow = [...document.querySelectorAll('#tbody-base tr, #tbody-fora tr')].find(tr => {
      const tk = tr.querySelector('.t')?.textContent?.trim();
      return tk === t;
    });
    if (stockRow) {
      const tds = stockRow.querySelectorAll('td');
      // Coluna 5 (índice 5) é Teto (Régua) em B.A.S.E. e Fora
      const tetoTab = parseBRL(tds[5]?.textContent);
      if (!diffOk(tetoTab, tetoEsp)) {
        divergencias.push({ ticker: t, local: 'Tabela Ações (Teto)', esperado: tetoEsp, encontrado: tetoTab, raw: tds[5]?.textContent?.trim() });
      }
    }

    const fiiRow = [...document.querySelectorAll('#tbody-fiis tr')].find(tr => {
      const tk = tr.querySelector('.t')?.textContent?.trim();
      return tk === t;
    });
    if (fiiRow) {
      const tds = fiiRow.querySelectorAll('td');
      // Coluna 6 (índice 6) é Teto (Régua) em FIIs
      const tetoFiiTab = parseBRL(tds[6]?.textContent);
      if (!diffOk(tetoFiiTab, tetoEsp)) {
        divergencias.push({ ticker: t, local: 'Tabela FIIs (Teto)', esperado: tetoEsp, encontrado: tetoFiiTab, raw: tds[6]?.textContent?.trim() });
      }
    }

    // (b) Card do Radar
    const radarCard = [...document.querySelectorAll('#radar-grid .rc-card')].find(card => {
      const tk = card.querySelector('.rc-ticker')?.textContent?.trim()?.split(/\s+/)[0];
      return tk === t;
    });
    if (radarCard) {
      const boxes = [...radarCard.querySelectorAll('.rc-price-box')];
      const tetoBox = boxes.find(b => /Teto/i.test(b.querySelector('.lbl')?.textContent || ''));
      if (tetoBox) {
        const tetoCard = parseBRL(tetoBox.querySelector('.val')?.textContent);
        if (!diffOk(tetoCard, tetoEsp)) {
          divergencias.push({ ticker: t, local: 'Card Radar', esperado: tetoEsp, encontrado: tetoCard, raw: tetoBox.querySelector('.val')?.textContent?.trim() });
        }
      }
    }

    // (c) Modal (#m-kpi-teto-regua, #m-bi-pt6, #m-stat-teto e linha SVG TETO RÉGUA)
    openModal(t);
    const kpiTeto = parseBRL(document.getElementById('m-kpi-teto-regua')?.textContent);
    const biPt6 = parseBRL(document.getElementById('m-bi-pt6')?.textContent);
    const statTeto = parseBRL(document.getElementById('m-stat-teto')?.textContent);

    if (!diffOk(kpiTeto, tetoEsp)) {
      divergencias.push({ ticker: t, local: 'Modal #m-kpi-teto-regua', esperado: tetoEsp, encontrado: kpiTeto, raw: document.getElementById('m-kpi-teto-regua')?.textContent });
    }
    if (!diffOk(biPt6, tetoEsp)) {
      divergencias.push({ ticker: t, local: 'Modal #m-bi-pt6', esperado: tetoEsp, encontrado: biPt6, raw: document.getElementById('m-bi-pt6')?.textContent });
    }

    // Só checa #m-stat-teto e SVG se o ativo tiver histórico renderizado no gráfico
    const svgTxt = document.getElementById('m-cotacao-svg')?.textContent || '';
    const semHist = /Sem histórico de cotação/i.test(svgTxt);
    if (!semHist) {
      if (!diffOk(statTeto, tetoEsp)) {
        divergencias.push({ ticker: t, local: 'Modal #m-stat-teto', esperado: tetoEsp, encontrado: statTeto, raw: document.getElementById('m-stat-teto')?.textContent });
      }
      // Se linha SVG estiver visível dentro do range Y do gráfico, deve bater com tetoEsp
      const mSvg = svgTxt.match(/TETO RÉGUA\s*R\$\s*([\d.]+,\d{2})/);
      if (mSvg) {
        const svgVal = parseBRL(mSvg[0]);
        if (!diffOk(svgVal, tetoEsp)) {
          divergencias.push({ ticker: t, local: 'Modal SVG linha TETO RÉGUA', esperado: tetoEsp, encontrado: svgVal, raw: mSvg[0] });
        }
      }
      if (/TETO (7%|12%|BARSI)/i.test(svgTxt)) {
        divergencias.push({ ticker: t, local: 'Modal SVG texto legado proibido', esperado: 'TETO RÉGUA', encontrado: svgTxt });
      }
    }

    checados++;
  }

  if (typeof closeModal === 'function') closeTicketModal();

  return {
    totalTickers: tickers.length,
    checados,
    divergenciasCount: divergencias.length,
    divergencias: divergencias.slice(0, 20)
  };
})()
