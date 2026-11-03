---
slug: gen_bridge
type: note
graph: gitnexus
---

#!/usr/bin/env python3
"""Generate the corrected pinets_bridge.js."""
from pathlib import Path

content = r"""#!/usr/bin/env node
/**
 * PineTS Bridge: run any TradingView Pine Script strategy on MT5 candle data.
 * Usage: node pinets_bridge.js <pine_file> <candles_json> <symbol> <timeframe>
 * Input:  candles_json = [{openTime, open, high, low, close, volume}, ...]
 * Output: JSON {ok, plots, trades, signals, error} on stdout.
 */
const fs = require('fs');
const path = require('path');
const { PineTS, BaseProvider } = require(path.join(__dirname, '..', 'luxalgo', 'PineTS', 'dist', 'pinets.min.cjs'));

const [,, pineFile, candlesFile, symbol, timeframe] = process.argv;

if (!pineFile || !candlesFile) {
  console.error('Usage: node pinets_bridge.js <pine_file> <candles_json> <symbol> <timeframe>');
  process.exit(1);
}

class MT5Provider extends BaseProvider {
  constructor(candles) {
    super({ requiresApiKey: false, providerName: 'MT5' });
    this._candles = candles;
  }
  getSupportedTimeframes() {
    return new Set(['1', '5', '15', '30', '60', '240', 'D', 'W', 'M']);
  }
  async _getMarketDataNative(tickerId, tf, limit, sDate, eDate) {
    let data = this._candles;
    if (sDate) data = data.filter(c => c.openTime >= sDate);
    if (eDate) data = data.filter(c => c.openTime <= eDate);
    if (limit) data = data.slice(-limit);
    return data.map(c => ({
      openTime: c.openTime,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
      volume: c.volume || 0,
      closeTime: c.openTime + 3600000,
    }));
  }
  async getSymbolInfo(tickerId) {
    return {
      ticker: tickerId,
      currency: 'USD',
      minmov: 0.01,
      pricescale: 100,
      session: '24x7',
      timezone: 'UTC',
    };
  }
}

function replaceInputTimeframe(source, defaultTimeframe) {
  let out = '';
  let i = 0;
  const re = /input\.timeframe\s*\(/g;
  let m;
  while ((m = re.exec(source)) !== null) {
    const offset = m.index;
    const matchLen = m[0].length;
    out += source.slice(i, offset);
    let depth = 1;
    let j = offset + matchLen;
    let inString = false;
    let stringChar = null;
    while (j < source.length && depth > 0) {
      const ch = source[j];
      if (inString) {
        if (ch === stringChar) { inString = false; }
      } else {
        if (ch === '"' || ch === "'") { inString = true; stringChar = ch; }
        else if (ch === '(') { depth++; }
        else if (ch === ')') { depth--; }
      }
      j++;
    }
    const fullCall = source.substring(offset, j);
    const tfMatch = fullCall.match(/input\.timeframe\s*\(\s*(["'])([^"']+)\1/);
    const tf = tfMatch ? tfMatch[2] : defaultTimeframe;
    out += JSON.stringify(tf);
    i = j;
  }
  out += source.slice(i);
  return out;
}

function prepPineForPinets(source) {
  let out = source.replace(/^\/\/@version=6/m, '//@version=5');
  out = out.replace(/\binput\.(int|float|bool|color|source)\s*\(/g, 'input(');
  out = out.replace(/input\.\w+\s*\(/g, (match, offset) => {
    let depth = 1;
    let i = offset + match.length;
    let inString = false;
    let stringChar = null;
    while (i < source.length && depth > 0) {
      const ch = source[i];
      if (inString) {
        if (ch === stringChar) inString = false;
      } else {
        if (ch === '"' || ch === "'") { inString = true; stringChar = ch; }
        else if (ch === '(') depth++;
        else if (ch === ')') depth--;
      }
      i++;
    }
    const fullCall = source.substring(offset, i);
    const head = fullCall.slice(0, fullCall.lastIndexOf(')'));
    const tail = ')';
    const args = head.slice(match.length);
    const cleaned = args
      .replace(/\s*tooltip\s*=\s*(["'])[^"']*\1/g, '')
      .replace(/\s*group\s*=\s*(["'])[^"']*\1/g, '')
      .replace(/\s*group\s*=\s*[A-Za-z_]\w*/g, '')
      .replace(/\s*,\s*,/g, ',')
      .replace(/,\s*$/, '');
    return match + cleaned + tail;
  });
  return out;
}

async function main() {
  try {
    const pineCode = fs.readFileSync(pineFile, 'utf-8');
    const candles = JSON.parse(fs.readFileSync(candlesFile, 'utf-8'));
    if (!Array.isArray(candles) || candles.length === 0) {
      console.log(JSON.stringify({ ok: false, error: 'no candles provided' }));
      return;
    }
    const provider = new MT5Provider(candles);
    const chartTimeframe = ({ M1: '1', M5: '5', M15: '15', M30: '30', H1: '60', H4: '240', D1: 'D', W1: 'W', MN1: 'M' })[timeframe] || timeframe || '60';
    const pine = new PineTS(provider, symbol || 'XAUUSD', chartTimeframe, candles.length);
    let processedCode = pineCode;
    if (/^\s*\/\/@version=6\s*$/m.test(pineCode)) {
      processedCode = replaceInputTimeframe(pineCode, chartTimeframe);
    } else {
      processedCode = prepPineForPinets(replaceInputTimeframe(pineCode, chartTimeframe));
    }
    const result = await pine.run(processedCode);
    const plots = {};
    if (result.plots) {
      for (const [key, plotObj] of Object.entries(result.plots)) {
        if (plotObj && typeof plotObj === 'object' && plotObj.data) {
          const data = plotObj.data;
          if (Array.isArray(data)) {
            const valid = data.map(p => p !== null && typeof p === 'object' ? p.value : p).filter(v => typeof v === 'number' && Number.isFinite(v));
            if (valid.length > 0) {
              plots[key] = { latest: valid[valid.length - 1], recent: valid.slice(-10), count: data.length };
            }
          }
        }
      }
    }
    const strat = result.strategy || {};
    const openTrades = (strat.opentrades || []).map(t => ({ id: t.id, entry_id: t.entry_id, entry_price: t.entry_price, entry_time: t.entry_time, size: t.size, direction: t.size > 0 ? 'long' : 'short' }));
    const closedTrades = (strat.closedtrades || []).map(t => ({ id: t.id, entry_id: t.entry_id, entry_price: t.entry_price, exit_price: t.exit_price, profit: t.profit, entry_time: t.entry_time, exit_time: t.exit_time }));
    const ledgerEntries = (strat._ledger_entries || []).map(e => ({ entry_id: e.entry_id, entry_price: e.entry_price, entry_time: e.entry_time, entry_bar_index: e.entry_bar_index, qty: e.qty }));
    const positionSize = strat.position_size || 0;
    const position = { size: positionSize, direction: positionSize > 0 ? 'long' : positionSize < 0 ? 'short' : 'flat', avg_price: strat.position_avg_price, entry_name: strat.position_entry_name };
    const stats = {
      netprofit: strat.netprofit, grossprofit: strat.grossprofit, grossloss: strat.grossloss, openprofit: strat.openprofit, max_drawdown: strat.max_drawdown, equity: strat.equity, initial_capital: strat.initial_capital, closed_trade_count: closedTrades.length,
      profit_factor: Number.isFinite(strat.grossprofit) && Number.isFinite(strat.grossloss) && strat.grossloss !== 0 ? strat.grossprofit / Math.abs(strat.grossloss) : null,
      commission_paid: (strat.closedtrades || []).length > 0 && (strat.closedtrades || []).every(t => Number.isFinite(t.commission)) ? (strat.closedtrades || []).reduce((total, t) => total + t.commission, 0) : null,
    };
    const lastBar = candles[candles.length - 1];
    let latestSignal = null;
    if (openTrades.length > 0) {
      const t = openTrades[openTrades.length - 1];
      latestSignal = { type: t.direction, price: t.entry_price, time: t.entry_time, active: true, size: t.size };
    } else if (ledgerEntries.length > 0) {
      const e = ledgerEntries[ledgerEntries.length - 1];
      latestSignal = { type: e.qty > 0 ? 'long' : 'short', price: e.entry_price, time: e.entry_time, active: false, size: e.qty };
    }
    console.log(JSON.stringify({ ok: true, symbol: symbol || 'XAUUSD', timeframe: timeframe || '60', bars: candles.length, plots: plots, open_trades: openTrades, closed_trades: closedTrades.slice(-20), ledger: ledgerEntries.slice(-20), position: position, stats: stats, latest_signal: latestSignal, last_close: lastBar.close }));
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err.message, stack: err.stack?.split('\n')[0] }));
  }
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
"""

p = Path('pinets_bridge.js')
p.write_text(content, encoding='utf-8')
print('WROTE', len(content), 'bytes')

