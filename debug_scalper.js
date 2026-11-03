const fs = require('fs');
const path = require('path');
const { PineTS, BaseProvider } = require(path.join(__dirname, '..', 'luxalgo', 'PineTS', 'dist', 'pinets.min.cjs'));

function replaceInputTimeframe(source, defaultTimeframe) {
  let out = source;
  const re = /input\.timeframe\s*\(/g;
  let m;
  const replacements = [];
  const varMap = {};
  while ((m = re.exec(out)) !== null) {
    const offset = m.index;
    const matchLen = m[0].length;
    let depth = 1;
    let j = offset + matchLen;
    let inString = false;
    let stringChar = null;
    while (j < out.length && depth > 0) {
      const ch = out[j];
      if (inString) { if (ch === stringChar) { inString = false; } }
      else {
        if (ch === '"' || ch === "'") { inString = true; stringChar = ch; }
        else if (ch === '(') { depth++; }
        else if (ch === ')') { depth--; }
      }
      j++;
    }
    const fullCall = out.substring(offset, j);
    let before = out.slice(Math.max(0, offset - 100), offset);
    const assignMatch = before.match(/([A-Za-z_]\w*)\s*=\s*$/);
    const literal = JSON.stringify(defaultTimeframe);
    if (assignMatch) {
      const varName = assignMatch[1];
      const assignmentStart = offset - assignMatch[0].length;
      replacements.push({ start: assignmentStart, end: j, text: varName + ' = ' + literal, varName, literal });
      varMap[varName] = literal;
    } else {
      const tfMatch = fullCall.match(/input\.timeframe\s*\(\s*(["'])([^"']+)\1/);
      const tf = tfMatch ? tfMatch[2] : defaultTimeframe;
      replacements.push({ start: offset, end: j, text: JSON.stringify(tf), varName: null, literal: JSON.stringify(tf) });
    }
  }
  replacements.sort((a, b) => b.start - a.start);
  for (const r of replacements) {
    out = out.slice(0, r.start) + r.text + out.slice(r.end);
  }
  for (const [varName, literal] of Object.entries(varMap)) {
    out = out.replace(new RegExp('\\b' + varName + '\\b(?=[,)])', 'g'), literal);
  }
  return out;
}

async function main() {
  const pineCode = fs.readFileSync('strategies/golden_eye_scalper.pine', 'utf-8');
  console.log('Has @version=6:', /^\s*\/\/@version=6\s*$/m.test(pineCode));
  const candles = JSON.parse(fs.readFileSync('strategies/test_candles.json', 'utf-8'));
  const provider = new class extends BaseProvider {
    constructor(candles) {
      super({ requiresApiKey: false, providerName: 'MT5' });
      this._candles = candles;
    }
    getSupportedTimeframes() { return new Set(['1', '5', '15', '30', '60', '240', 'D', 'W', 'M']); }
    async _getMarketDataNative(tickerId, tf, limit, sDate, eDate) {
      let data = this._candles;
      if (sDate) data = data.filter(c => c.openTime >= sDate);
      if (eDate) data = data.filter(c => c.openTime <= eDate);
      if (limit) data = data.slice(-limit);
      return data.map(c => ({ openTime: c.openTime, open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume || 0, closeTime: c.openTime + 3600000 }));
    }
    async getSymbolInfo(tickerId) { return { ticker: tickerId, currency: 'USD', minmov: 0.01, pricescale: 100, session: '24x7', timezone: 'UTC' }; }
  }(candles);
  const chartTimeframe = '60';
  const pine = new PineTS(provider, 'XAUUSD', chartTimeframe, candles.length);
  let processedCode = replaceInputTimeframe(pineCode, chartTimeframe);
  
  // Show what lines 75 and 146 look like after processing
  const plines = processedCode.split('\n');
  console.log('After replaceInputTimeframe:');
  console.log('Line 75:', plines[74]);
  console.log('Line 146:', plines[145]);
  
  // Search for any remaining empty timeframe patterns in security calls
  const securityMatches = processedCode.matchAll(/request\.security\s*\([^)]*\)/g);
  for (const m of securityMatches) {
    console.log('SECURITY CALL:', m[0].slice(0, 120));
  }
  
  try {
    const result = await pine.run(processedCode);
    console.log('OK:', JSON.stringify({ ok: true, bars: result.strategy?.closedtrades?.length || 0 }));
  } catch (err) {
    console.log('ERROR:', err.message);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
