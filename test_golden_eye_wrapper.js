// Trusted, deterministic OFFLINE execution test; never calls MT5 or places orders.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const root = __dirname;
const indicator = path.join(root, 'strategies/golden_eye_trend_regime.pine');
const hash = () => crypto.createHash('sha256').update(fs.readFileSync(indicator)).digest('hex');
const before = hash();
const source = fs.readFileSync(indicator, 'utf8').split(/\r?\n/);
const wrapper = fs.readFileSync(path.join(root, 'strategies/golden_eye_trend_wrap.pine'), 'utf8').replaceAll('\r\n', '\n');
const retained = source.slice(93,354).join('\n').replaceAll('syminfo.mintick', 'geMinTick');
assert(wrapper.includes(retained), 'Retained local engine differs from original except tick input');
assert(wrapper.includes(source.slice(378,392).join('\n')));
assert(wrapper.includes(source[393]));
assert(!/\b(?:limit|profit|trail_price|trail_points)\s*=/.test(wrapper), 'Unexpected TP or separate trailing order');
const candles = JSON.parse(fs.readFileSync(path.join(root,'strategies/test_candles.json'),'utf8'));
assert.equal(candles.length,720);
for (let i=0;i<candles.length;i++) {
  const c=candles[i];
  for (const key of ['openTime','open','high','low','close','volume']) assert(Number.isFinite(c[key]));
  assert(c.low<=Math.min(c.open,c.close) && c.high>=Math.max(c.open,c.close));
  if(i) assert.equal(c.openTime-candles[i-1].openTime,3600000);
}
const output = JSON.parse(execFileSync(process.execPath,['pinets_bridge.js','strategies/golden_eye_trend_wrap.pine','strategies/test_candles.json','XAUUSD','H1'],{cwd:root,timeout:60000,encoding:'utf8',maxBuffer:2*1024*1024}));
assert.equal(output.ok,true);
assert(output.closed_trades.length>0 && output.latest_signal);
assert.equal(output.stats.closed_trade_count, output.closed_trades.length);
assert.equal(output.bars, candles.length);
assert(Number.isFinite(output.plots['GE Strength'].latest));
(async()=>{
  const {PineTS}=require(path.join(root,'../luxalgo/PineTS/dist/pinets.min.cjs'));
  const r=await new PineTS(candles,'XAUUSD','60').run(wrapper+'\nplot(strategy.position_size, "test_position")\n');
  const values=k=>r.plots[k].data.map(x=>x.value);
  const stops=values('GE Stop (2 ATR ratchet; no TP)'), atr=values('GE ATR'), pos=values('test_position');
  let tested=0;
  for(const t of [...output.closed_trades,...output.open_trades]) {
    const start=candles.findIndex(c=>c.openTime===t.entry_time);
    assert(start>=120);
    const sign=t.entry_id==='GE Long'?1:-1;
    assert(Math.abs(stops[start]-(candles[start].close-sign*2*atr[start]))<1e-7,'Initial stop is not 2 ATR');
    for(let i=start+1;i<candles.length && pos[i]===sign;i++) {
      assert(sign*(stops[i]-stops[i-1])>=-1e-7,'Stop widened');
      tested++;
    }
  }
  assert(tested>0);
  assert.equal(hash(),before,'Original indicator changed');
  console.log(JSON.stringify({ok:true,synthetic_bars:candles.length,closed_trades:output.closed_trades.length,open_trades:output.open_trades.length,ratchet_bars_checked:tested,source_sha256:before,latest_signal:output.latest_signal}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
