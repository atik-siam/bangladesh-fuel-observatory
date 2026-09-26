(() => {
  const MODEL = window.BANGLADESH_FUEL_OBSERVATORY_MODEL;
  const BARREL = MODEL?.method?.barrel_litres || 158.9873;
  const FUELS = {
    diesel: { label: 'Diesel', short: 'Gasoil 10 ppm' },
    petrol: { label: 'Petrol', short: 'RON92' },
    octane: { label: 'Octane', short: 'RON95' }
  };
  const fmt = (v, d = 2) => Number(v).toLocaleString('en-BD', { minimumFractionDigits: d, maximumFractionDigits: d });
  const date = s => s ? new Date(s + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const has = v => Number.isFinite(Number(v));
  const benchmarkSource = key => MODEL.data_snapshot?.sources?.[key] || null;
  const officialEvent = dateStr => (MODEL.official_history || []).find(x => x.date === dateStr) || null;

  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  const statusLabel = status => ({ research_ready: 'research-ready', exploratory: 'exploratory', developing: 'Developing', insufficient_data: 'not yet estimable', available: 'available', unavailable: 'unavailable' }[status] || String(status || 'unknown').replace(/_/g, ' '));
  const statusClass = status => status === 'research_ready' || status === 'available' ? 'good' : ['exploratory','developing'].includes(status) ? 'warn' : 'bad';

  if (!MODEL) {
    document.querySelector('#app')?.replaceChildren();
    document.body.innerHTML = '<main class="wrap"><div class="error"><h2>Model snapshot unavailable</h2><p>The bundled <code>data/model.js</code> file could not be loaded. Keep the <code>data/</code> folder beside <code>index.html</code>.</p></div></main>';
    return;
  }

  const c = MODEL.data_coverage;
  document.querySelector('#marketDate').textContent = date(c.market_end);
  document.querySelector('#officialDate').textContent = date(c.official_end);
  document.querySelector('#snapshotDate').textContent = MODEL.data_snapshot?.updated_at_utc ? new Date(MODEL.data_snapshot.updated_at_utc).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  document.querySelector('#modelDate').textContent = MODEL.generated_at_utc ? new Date(MODEL.generated_at_utc).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  document.querySelector('#window').textContent = `${MODEL.method.policy_window_days} calendar days`;
  document.querySelector('#researchStatus').textContent = statusLabel(MODEL.research_status?.level || 'developing');

  function renderCards() {
    document.querySelector('#fuelCards').innerHTML = Object.entries(FUELS).map(([key, meta]) => {
      const f = MODEL.fuels[key];
      const gap = f.gap_tk_l;
      const gapClass = gap == null ? '' : gap > 0 ? 'positive' : gap < 0 ? 'negative' : '';
      const sufficient = Number(f.eligible_backtest_events || 0) >= MODEL.method.minimum_regression_events;
      const later = f.latest_official_overall_date && f.model_cutoff_date && f.latest_official_overall_date > f.model_cutoff_date;
      const officialReference = f.official_reference_tk_l == null ? '—' : 'Tk ' + fmt(f.official_reference_tk_l);
      const sourceUrl = benchmarkSource(f.benchmark);
      const sourceLink = sourceUrl ? `<a class="inline-source" href="${esc(sourceUrl)}" target="_blank" rel="noreferrer">Verify benchmark ↗</a>` : '';
      return `<article class="card">
        <div class="card-top"><div><div class="fuel-name">${meta.label}</div><div class="fuel-benchmark">${esc(f.benchmark_label)} · ${sourceLink}</div></div><span class="status ${sufficient ? 'good' : 'warn'}">${plural(f.eligible_backtest_events || 0, 'usable event')}</span></div>
        <div class="estimate-label">Model-implied retail estimate</div>
        <div class="estimate">${f.estimated_retail_tk_l == null ? '—' : 'Tk ' + fmt(f.estimated_retail_tk_l)} <small>current calibrated nowcast</small></div>
        <div class="reference-row"><span>Official price known at model cutoff</span><strong>${officialReference}</strong></div>
        <div class="delta ${gapClass}">${gap == null ? 'Official comparison unavailable' : `${gap >= 0 ? '+' : ''}Tk ${fmt(gap)} model − official`}</div>
        ${later ? (() => { const ev = officialEvent(f.latest_official_overall_date); const src = ev?.source_url ? ` <a href="${esc(ev.source_url)}" target="_blank" rel="noreferrer">Verify official source ↗</a>` : ''; return `<div class="later-note">Latest official price in the dataset: Tk ${fmt(f.latest_official_overall_tk_l)} on ${date(f.latest_official_overall_date)}.${src} It is after this fuel's market cutoff and is not used in the nowcast.</div>`; })() : ''}
        <div class="asof">Model cutoff: <strong>${date(f.model_cutoff_date)}</strong> · calibration uses official events strictly before that cutoff.</div>
        <div class="stats">
          <div class="stat"><span>International benchmark equivalent</span><strong>${f.latest_market_value_tk_l == null ? '—' : 'Tk ' + fmt(f.latest_market_value_tk_l)}</strong><small>${date(f.latest_benchmark_date)} · ${f.latest_benchmark_usd_bbl == null ? '—' : fmt(f.latest_benchmark_usd_bbl, 1) + ' USD/bbl'}</small></div>
          <div class="stat"><span>Market-window signal</span><strong>${f.market_signal_tk_l == null ? '—' : 'Tk ' + fmt(f.market_signal_tk_l)}</strong><small>${plural(f.window_observations || 0, 'observation')} · ${f.window_start ? date(f.window_start) : '—'} to ${f.window_end ? date(f.window_end) : '—'}</small></div>
          <div class="stat"><span>Domestic calibration</span><strong>${f.domestic_calibration_residual_tk_l == null ? '—' : `${f.domestic_calibration_residual_tk_l >= 0 ? '+' : ''}Tk ${fmt(f.domestic_calibration_residual_tk_l)}`}</strong><small>median of ${plural(f.calibration_events || 0, 'prior eligible event residual')}</small></div>
          <div class="stat"><span>FX used</span><strong>${f.latest_fx_usd_bdt == null ? '—' : fmt(f.latest_fx_usd_bdt, 2) + ' Tk/USD'}</strong><small>aligned to latest benchmark observation</small></div>
        </div>
      </article>`;
    }).join('');
  }

  function renderMarketChart(fuel) {
    const el = document.querySelector('#historyChart');
    const data = (MODEL.history || []).filter(x => has(x[`${fuel}_market_value`])).sort((a, b) => a.date.localeCompare(b.date));
    document.querySelector('#chartCaption').textContent = `${FUELS[fuel].label}: ${FUELS[fuel].short} benchmark converted to Tk/L using the corresponding USD/BDT observation. This is an international market-equivalent series, not a Bangladesh retail-price series.`;
    if (data.length < 2) { el.innerHTML = '<p class="muted">Not enough observations for this benchmark chart.</p>'; return; }
    const W = 900, H = 290, L = 58, R = 20, T = 22, B = 42;
    const vals = data.map(x => Number(x[`${fuel}_market_value`]));
    const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo || 1) * 0.08, min = lo - pad, max = hi + pad;
    const X = i => L + i * (W - L - R) / (data.length - 1), Y = v => H - B - (v - min) / (max - min) * (H - T - B);
    const path = vals.map((v, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
    const ticks = [0, .25, .5, .75, 1].map(p => { const v = min + p * (max - min); return `<g><line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" class="grid-line"/><text x="${L-9}" y="${Y(v)+4}" text-anchor="end" class="axis">${fmt(v)}</text></g>`; }).join('');
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(FUELS[fuel].label)} international benchmark converted to Tk per litre"><g>${ticks}</g><path d="${path}" class="chart-line"/><text x="${L}" y="12" class="chart-label">International benchmark equivalent · Tk/L</text><text x="${L}" y="${H-14}" class="axis">${date(data[0].date)}</text><text x="${W-R}" y="${H-14}" text-anchor="end" class="axis">${date(data[data.length-1].date)}</text></svg>`;
  }

  function renderBacktestChart(fuel) {
    const el = document.querySelector('#backtestChart');
    const data = (MODEL.backtest_history?.[fuel] || []).filter(x => x.primary != null && x.official != null);
    if (data.length < 2) { el.innerHTML = '<p class="muted">A prediction-vs-official chart will appear after enough eligible events produce at least two valid expanding-calibration predictions.</p>'; return; }
    const W = 900, H = 250, L = 58, R = 20, T = 22, B = 42;
    const vals = data.flatMap(x => [x.official, x.primary].filter(Number.isFinite));
    const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo || 1) * 0.1, min = lo - pad, max = hi + pad;
    const X = i => L + i * (W - L - R) / (data.length - 1), Y = v => H - B - (v - min) / (max - min) * (H - T - B);
    const officialPath = data.map((p, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(p.official).toFixed(1)}`).join(' ');
    const predPath = data.map((p, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(p.primary).toFixed(1)}`).join(' ');
    const ticks = [0, .5, 1].map(p => { const v = min + p * (max - min); return `<g><line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" class="grid-line"/><text x="${L-9}" y="${Y(v)+4}" text-anchor="end" class="axis">${fmt(v)}</text></g>`; }).join('');
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(FUELS[fuel].label)} official versus expanding-calibration estimates"><g>${ticks}</g><path d="${officialPath}" class="chart-line official-line"/><path d="${predPath}" class="chart-line model-line"/><text x="${L}" y="12" class="chart-label">Official vs expanding-calibration estimate · Tk/L</text><text x="${L}" y="${H-14}" class="axis">${date(data[0].date)}</text><text x="${W-R}" y="${H-14}" text-anchor="end" class="axis">${date(data[data.length-1].date)}</text></svg><div class="legend"><span class="legend-official">Official</span><span class="legend-model">Expanding calibration</span></div>`;
  }

  function renderBacktestTable() {
    const rows = [];
    for (const [key, m] of Object.entries(MODEL.backtest)) {
      for (const [name, x] of [["Primary", m.primary_expanding_calibration], ["Naive", m.naive_previous_official]]) {
        rows.push(`<tr><td>${FUELS[key].label}</td><td>${name}</td><td>${x.n}</td><td>${x.mae_tk_l == null ? '—' : 'Tk ' + fmt(x.mae_tk_l)}</td><td>${x.rmse_tk_l == null ? '—' : 'Tk ' + fmt(x.rmse_tk_l)}</td><td>${x.mape_pct == null ? '—' : fmt(x.mape_pct) + '%'}</td><td>${x.mean_error_tk_l == null ? '—' : (x.mean_error_tk_l >= 0 ? '+' : '') + 'Tk ' + fmt(x.mean_error_tk_l)}</td></tr>`);
      }
    }
    document.querySelector('#backtest tbody').innerHTML = rows.join('');
    const notes = Object.entries(MODEL.backtest).map(([key, m]) => {
      const p = m.primary_expanding_calibration, n = m.naive_previous_official;
      if (p.mae_tk_l == null || n.mae_tk_l == null) return '';
      const relation = p.mae_tk_l < n.mae_tk_l ? 'lower' : p.mae_tk_l > n.mae_tk_l ? 'higher' : 'equal';
      return `<div class=\"comparison-note\"><strong>${FUELS[key].label}:</strong> primary MAE is <strong>${relation}</strong> than the naive reference in the current snapshot (${fmt(p.mae_tk_l)} vs ${fmt(n.mae_tk_l)} Tk/L). This is descriptive evidence only; it does not establish model superiority.</div>`;
    }).join('');
    const existing = document.querySelector('#backtestComparison');
    if (existing) existing.innerHTML = notes;
  }

  function renderDiagnostics() {
    const rows = Object.entries(FUELS).map(([key, meta]) => {
      const f = MODEL.fuels[key], r = f.regression || {}, w = f.walk_forward_regression || {};
      return `<div class="diag"><span>${meta.label} · pass-through regression</span><strong><span class="status ${statusClass(r.status)}">${statusLabel(r.status)} · N=${r.n ?? 0}/${MODEL.method.minimum_regression_events} headline</span></strong></div>
      <div class="diag"><span>${meta.label} · walk-forward regression</span><strong><span class="status ${statusClass(w.status)}">${statusLabel(w.status)} · ${w.n ?? 0}/${w.minimum_reportable_predictions ?? MODEL.method.walk_forward_min_reportable} predictions</span></strong></div>`;
    }).join('');
    const noLeak = `<div class="diag"><span>Look-ahead protection</span><strong><span class="status good">enabled</span></strong></div>`;
    const mapping = `<div class="diag"><span>Grade-specific benchmark mapping</span><strong><span class="status good">enabled</span></strong></div>`;
    const selfCal = `<div class="diag"><span>Same-day official-price calibration</span><strong><span class="status good">excluded</span></strong></div>`;
    const threshold = `<div class="diag"><span>Headline regression threshold</span><strong><span class="status warn">N ≥ ${MODEL.method.minimum_regression_events}</span></strong></div>`;
    const counts = Object.entries(FUELS).map(([key, meta]) => `${meta.label}: ${MODEL.fuels[key]?.eligible_backtest_events ?? 0}/${MODEL.research_status?.official_events_total ?? '—'} eligible`).join(' · ');
    const changes = Object.entries(FUELS).map(([key, meta]) => `${meta.label}: ${MODEL.fuels[key]?.official_nonzero_change_events ?? 0} non-zero price changes`).join(' · ');
    document.querySelector('#diagnostics').innerHTML = rows + noLeak + mapping + selfCal + threshold + `<p class="source-note">Official events: ${MODEL.research_status?.official_events_total ?? '—'}. Eligible windows: ${counts}. Non-zero official price changes: ${changes}. Exploratory statistics remain visibly labeled and are not presented as established predictive evidence.</p>`;
  }

  function renderCoverage() {
    const rows = Object.entries(MODEL.data_coverage.by_series || {}).filter(([k]) => k !== 'usd_bdt').map(([fuel, v]) => `<div class="coverage-item"><span>${FUELS[fuel].label} · ${esc(v.benchmark)}</span><strong>${fmt(v.observations, 0)} observations</strong><small>${date(v.start)} → ${date(v.latest)}</small></div>`).join('');
    const fx = MODEL.data_coverage.by_series?.usd_bdt;
    document.querySelector('#coverage').innerHTML = `<div class="coverage-grid">${rows}<div class="coverage-item"><span>USD/BDT</span><strong>${fmt(fx?.observations || 0, 0)} aligned observations</strong><small>${date(fx?.start)} → ${date(fx?.latest)}</small></div><div class="coverage-item"><span>Official price events</span><strong>${fmt(MODEL.data_coverage.official_events, 0)}</strong><small>${date(MODEL.data_coverage.official_start)} → ${date(MODEL.data_coverage.official_end)}</small></div></div><p class="source-note">The bundled market snapshot contains full public benchmark histories available at preparation time. The live GitHub workflow refreshes them online. Series with different publication dates remain explicitly sparse; no synthetic benchmark values are created.</p>`;
  }

  function renderAudit(fuel) {
    const f = MODEL.fuels[fuel];
    document.querySelector('#eventAudit tbody').innerHTML = (f.event_audit || []).map(r => { const src = r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noreferrer">${esc(r.source_name || 'Source')} ↗</a>` : '—'; return `<tr><td>${date(r.date)}</td><td>${r.official_price == null ? '—' : 'Tk ' + fmt(r.official_price)}</td><td>${r.window_observations}</td><td>${r.window_start ? `${date(r.window_start)} → ${date(r.window_end)}` : '—'}</td><td><span class="status ${r.eligible ? 'good' : 'bad'}">${r.eligible ? 'usable' : 'excluded'}</span></td><td>${esc(r.reason.replace(/_/g, ' '))}</td><td>${src}</td></tr>`; }).join('');
  }

  function setupScenario() {
    const sf = document.querySelector('#scenarioFuel'), sb = document.querySelector('#scenarioBenchmark'), sx = document.querySelector('#scenarioFx');
    const update = () => {
      const f = MODEL.fuels[sf.value];
      const marketEq = Number(sb.value) * Number(sx.value) / BARREL;
      const calibration = has(f.domestic_calibration_residual_tk_l) ? Number(f.domestic_calibration_residual_tk_l) : null;
      const modelEstimate = calibration == null ? null : marketEq + calibration;
      const official = has(f.official_reference_tk_l) ? Number(f.official_reference_tk_l) : null;
      document.querySelector('#scenarioBenchmarkValue').textContent = `${Number(sb.value).toFixed(1)} USD/bbl`;
      document.querySelector('#scenarioFxValue').textContent = `${Number(sx.value).toFixed(2)} Tk/USD`;
      document.querySelector('#scenarioMarketValue').textContent = `Tk ${fmt(marketEq)} / litre`;
      const scenarioSource = benchmarkSource(f.benchmark);
      const scenarioSourceEl = document.querySelector('#scenarioBenchmarkSource');
      if (scenarioSourceEl) { scenarioSourceEl.href = scenarioSource || "#"; scenarioSourceEl.style.display = scenarioSource ? "inline-block" : "none"; }
      document.querySelector('#scenarioCalibration').textContent = calibration == null ? 'Not available' : `${calibration >= 0 ? '+' : ''}Tk ${fmt(calibration)} / litre`;
      document.querySelector('#scenarioValue').textContent = modelEstimate == null ? 'Not available' : `Tk ${fmt(modelEstimate)} / litre`;
      document.querySelector('#scenarioOfficial').textContent = official == null ? 'Not available' : `Tk ${fmt(official)} / litre`;
      const later = f.latest_official_overall_date && f.model_cutoff_date && f.latest_official_overall_date > f.model_cutoff_date;
      document.querySelector('#scenarioOfficialDate').textContent = f.official_reference_date ? `Effective ${date(f.official_reference_date)}` : 'Effective —';
      document.querySelector('#scenarioGap').textContent = modelEstimate == null || official == null ? 'No official comparison available at this cutoff' : `${modelEstimate - official >= 0 ? '+' : ''}Tk ${fmt(modelEstimate - official)} vs official price known at cutoff`;
      const context = document.querySelector('#scenarioOfficialContext');
      if (context) {
        if (later) {
          const latest = has(f.latest_official_overall_tk_l) ? `Tk ${fmt(f.latest_official_overall_tk_l)} / litre` : '—';
          context.innerHTML = `<strong>Latest official price:</strong> ${latest} · effective ${date(f.latest_official_overall_date)}<br><span class="context-note">Shown for current context only. It is not used in the point-in-time comparison because ${FUELS[sf.value].short} market data end on ${date(f.model_cutoff_date)}.</span>`;
        } else {
          context.textContent = `This is the latest official price available at the model cutoff of ${date(f.model_cutoff_date)}.`;
        }
      }
    };
    const load = () => { const f = MODEL.fuels[sf.value]; sb.value = f.latest_benchmark_usd_bbl ?? 120; sx.value = f.latest_fx_usd_bdt ?? 123; update(); };
    sf.addEventListener('change', load); sb.addEventListener('input', update); sx.addEventListener('input', update); load();
  }

  renderCards();
  renderBacktestTable();
  renderDiagnostics();
  renderCoverage();
  renderMarketChart('diesel');
  renderBacktestChart('diesel');
  renderAudit('diesel');
  setupScenario();
  document.querySelector('#chartFuel').addEventListener('change', e => renderMarketChart(e.target.value));
  document.querySelector('#backtestFuel').addEventListener('change', e => renderBacktestChart(e.target.value));
  document.querySelector('#auditFuel').addEventListener('change', e => renderAudit(e.target.value));
})();
