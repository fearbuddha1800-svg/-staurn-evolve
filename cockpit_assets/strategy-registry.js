/* Read-only Pine registry; all user-controlled text uses textContent. */
(() => {
  'use strict';
  const panel = document.createElement('section');
  panel.className = 'panel';
  panel.id = 'pine-registry-panel';
  panel.setAttribute('aria-label', 'Local Pine strategy registry');
  const title = document.createElement('h2');
  title.textContent = 'Pine strategy registry';
  const label = document.createElement('label');
  label.textContent = 'Strategy ';
  label.htmlFor = 'pine-registry-select';
  const select = document.createElement('select');
  select.id = label.htmlFor;
  const refresh = document.createElement('button');
  refresh.type = 'button'; refresh.textContent = 'Refresh strategies';
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  const details = document.createElement('p');
  const metrics = document.createElement('dl');
  const trades = document.createElement('pre');
  const command = document.createElement('code');
  const note = document.createElement('p');
  note.textContent = 'PineTS simulation on closed candles — not live account equity. Backtests run from the trusted local CLI, not this HTTP surface.';
  panel.append(title, label, select, refresh, status, details, metrics, trades, command, note);
  const parent = document.querySelector('#view-chart') || document.querySelector('main') || document.body;
  parent.append(panel);
  let entries = [];
  function show() {
    const entry = entries.find(item => item.id === select.value);
    metrics.replaceChildren(); trades.textContent = ''; command.textContent = '';
    if (!entry) { details.textContent = 'No strategy selected.'; return; }
    details.textContent = `${entry.name || entry.id} · v${entry.version || '?'} · ${(entry.symbols || []).join(', ') || 'symbol not specified'} · ${entry.timeframe || 'timeframe not specified'} · ${entry.status}${entry.error ? ': ' + entry.error : ''}`;
    command.textContent = `python strategy_registry.py backtest --id ${entry.id}`;
    const result = entry.backtest;
    const usable = result && result.ok && !result.stale;
    for (const [name, value] of [
      ['Simulated equity', usable ? result.stats?.equity : null],
      ['Simulated max drawdown', usable ? result.stats?.max_drawdown : null],
      ['Result observation', result?.observed_at ? new Date(result.observed_at * 1000).toISOString() : null]
    ]) {
      const dt = document.createElement('dt'); dt.textContent = name;
      const dd = document.createElement('dd'); dd.textContent = value === null || value === undefined ? 'Unavailable' : String(value);
      metrics.append(dt, dd);
    }
    if (result?.stale) trades.textContent = 'Strategy changed since the last backtest. Results are stale.';
    else if (result && !result.ok) trades.textContent = 'Backtest failed: ' + (result.error || 'unknown error');
    else if (usable) trades.textContent = 'Closed trades (bridge output may be a truncated tail):\n' + JSON.stringify(result.closed_trades || [], null, 2);
    else trades.textContent = 'No backtest result published. No performance is inferred.';
  }
  async function load() {
    refresh.disabled = true;
    try {
      const response = await fetch('/api/strategy_registry', {credentials: 'same-origin', cache: 'no-store'});
      if (!response.ok) throw new Error(`Registry HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.strategies)) throw new Error('Invalid registry payload');
      const previous = select.value;
      entries = data.strategies;
      select.replaceChildren(...entries.map(entry => {
        const option = document.createElement('option'); option.value = entry.id;
        option.textContent = `${entry.name || entry.id} (${entry.version || '?'})`;
        return option;
      }));
      if (entries.some(entry => entry.id === previous)) select.value = previous;
      status.textContent = data.notice || 'Local registry';
      show();
    } catch (error) {
      entries = []; select.replaceChildren(); show();
      status.textContent = error.message;
    } finally { refresh.disabled = false; }
  }
  select.addEventListener('change', show);
  refresh.addEventListener('click', load);
  // Bootstrap authentication is owned by the existing shell. Retry is explicit.
  load();
})();
