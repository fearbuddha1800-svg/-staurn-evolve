'use strict';
// Syntax-only validation for trusted local sources. Not an execution sandbox.
const fs = require('fs');
const path = require('path');
try {
  const {Indicator} = require(path.join(__dirname, '..', 'luxalgo', 'PineTS', 'dist', 'pinets.min.cjs'));
  const source = fs.readFileSync(0, 'utf8');
  if (Buffer.byteLength(source) > 65536) throw new Error('Source too large');
  Indicator.from(source).prepare({});
  process.stdout.write(JSON.stringify({ok: true, engine: 'PineTS', mode: 'syntax-only'}));
} catch (err) {
  process.stdout.write(JSON.stringify({ok: false, error: String(err.message).slice(0, 1000)}));
}
