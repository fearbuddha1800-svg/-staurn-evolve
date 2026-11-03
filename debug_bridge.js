const fs = require('fs');
const path = require('path');
const { PineTS, BaseProvider } = require(path.join(__dirname, '..', 'luxalgo', 'PineTS', 'dist', 'pinets.min.cjs'));

const pineCode = fs.readFileSync('strategies/golden_eye_scalper.pine', 'utf-8');
console.log('has @version=6:', /^\s*\/\/@version=6\s*$/m.test(pineCode));

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

const processed = replaceInputTimeframe(pineCode, '60');
const lines = processed.split('\n');
lines.forEach((l, idx) => { if (l.includes('htfTf')) console.log('LINE', (idx+1), ':', l); });

// Now try running the full bridge
async function run() {
  const candles = JSON.parse(fs.readFileSync('strategies/test_candles.json', 'utf-8'));
  const provider = new (class MT5Provider extends BaseProvider {
    constructor(candles) { super({ requiresApiKey: false, providerName: 'MT5' }); this._candles = candles; }
    getSupportedTimeframes() { return new Set(['1', '5', '15', '30', '60', '240', 'D', 'W', 'M']); }
    async _getMarketDataNative(tickerId, tf, limit, sDate, eDate) {
      let data = this._candles;
      if (sDate) data = data.filter(c => c.openTime >= sDate);
      if (eDate) data = data.filter(c => c.openTime <= eDate);
      if (limit) data = data.slice(-limit);
      return data.map(c => ({ openTime: c.openTime, open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume || 0, closeTime: c.openTime + 3600000 }));
    }
    async getSymbolInfo(tickerId) { return { ticker: tickerId, currency: 'USD', minmov: 0.01, pricescale: 100, session: '24x7', timezone: 'UTC' }; }
  })(candles);
  const pine = new PineTS(provider, 'XAUUSD', '60', candles.length);
  try {
    const result = await pine.run(processed);
    console.log('RUN OK, keys:', Object.keys(result));
    console.log('strategy:', JSON.stringify(result.strategy ? Object.keys(result.strategy) : null));
  } catch (e) {
    console.log('RUN ERROR:', e.message);
  }
}
run().then(() => process.exit(0));
