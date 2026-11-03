#!/usr/bin/env node
/**
 * Pine series bridge: run a .pine indicator/strategy via PineTS and return the
 * FULL plot series (not just the last N) so the dashboard can overlay them on
 * the chart. Reuses the same MT5Provider contract as pinets_bridge.js.
 *
 * Usage: node pine_series_bridge.js <pine_file> <candles_json> <symbol> <tf>
 * Output: JSON {ok, symbol, timeframe, bars, series:{name:{values:[...]}}, error}
 */
const fs = require('fs');
const path = require('path');
const { PineTS, BaseProvider } = require(path.join(__dirname, '..', 'luxalgo', 'PineTS', 'dist', 'pinets.min.cjs'));

const [,, pineFile, candlesFile, symbol, timeframe] = process.argv;
if (!pineFile || !candlesFile) {
  console.error('Usage: node pine_series_bridge.js <pine_file> <candles_json> <symbol> <tf>');
  process.exit(1);
}

class MT5Provider extends BaseProvider {
  constructor(candles) { super({ requiresApiKey: false, providerName: 'MT5' }); this._candles = candles; }
  getSupportedTimeframes() { return new Set(['1','5','15','30','60','240','D','W','M']); }
  async _getMarketDataNative(tickerId, tf, limit) {
    let data = this._candles;
    if (limit) data = data.slice(-limit);
    return data.map(c => ({ openTime: c.openTime, open: c.open, high: c.high,
      low: c.low, close: c.close, volume: c.volume || 0, closeTime: c.openTime + 3600000 }));
  }
  async getSymbolInfo(t) {
    return { ticker: t, currency: 'USD', minmov: 0.01, pricescale: 100, session: '24x7', timezone: 'UTC' };
  }
}

function num(v) { return (v === null || v === undefined || Number.isNaN(v)) ? null : Number(v); }

async function main() {
  try {
    const pineCode = fs.readFileSync(pineFile, 'utf-8');
    const candles = JSON.parse(fs.readFileSync(candlesFile, 'utf-8'));
    if (!Array.isArray(candles) || !candles.length) {
      console.log(JSON.stringify({ ok: false, error: 'no candles' })); return;
    }
    const pine = new PineTS(new MT5Provider(candles), symbol || 'XAUUSD', timeframe || '60', candles.length);
    const result = await pine.run(pineCode);

    // FULL plot series: plots[name].data is a per-bar array of
    // {title, time, value, options:{color}} objects (NOT raw numbers).
    const series = {};
    if (result.plots) {
      for (const [key, obj] of Object.entries(result.plots)) {
        if (key.startsWith('__')) continue;               // drawing containers
        if (!obj || typeof obj !== 'object' || !Array.isArray(obj.data)) continue;
        const values = [];
        let color = null;
        for (const d of obj.data) {
          if (d && typeof d === 'object') {
            const v = d.value !== undefined ? d.value : (d.close !== undefined ? d.close : null);
            values.push(num(v));
            if (!color && d.options && d.options.color) color = d.options.color;
          } else {
            values.push(num(d));
          }
        }
        if (values.some(v => v !== null)) {
          series[key] = { values, title: obj.title || key, color };
        }
      }
    }
    // strategy fills -> markers for the chart
    const marks = [];
    const st = result.strategy || {};
    const push = (t) => { if (t && t.entry_time != null) marks.push({
      time: t.entry_time, side: (t.size > 0 || t.qty > 0) ? 'buy' : 'sell',
      price: num(t.entry_price), kind: 'entry' }); };
    (st.opentrades || []).forEach(push);
    (st._ledger_entries || []).forEach(push);

    console.log(JSON.stringify({
      ok: true, symbol: symbol || 'XAUUSD', timeframe: timeframe || '60',
      bars: candles.length, series, marks: marks.slice(-40), error: null
    }));
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: String(err && err.message || err).slice(0, 300) }));
  }
}
main();
