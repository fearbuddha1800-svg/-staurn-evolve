const fs = require('fs');
const path = require('path');

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
    console.log('Found input.timeframe at offset', offset, 'fullCall:', JSON.stringify(fullCall.slice(0, 80)));
    console.log('  before slice ends with:', JSON.stringify(before.slice(-40)));
    console.log('  assignMatch:', assignMatch ? assignMatch[1] : null);
    if (assignMatch) {
      const varName = assignMatch[1];
      const assignmentStart = offset - assignMatch[0].length;
      replacements.push({ start: assignmentStart, end: j, text: varName + ' = ' + literal, varName, literal });
      varMap[varName] = literal;
      console.log('  => replace assignment with:', varName + ' = ' + literal);
    } else {
      const tfMatch = fullCall.match(/input\.timeframe\s*\(\s*(["'])([^"']+)\1/);
      const tf = tfMatch ? tfMatch[2] : defaultTimeframe;
      replacements.push({ start: offset, end: j, text: JSON.stringify(tf), varName: null, literal: JSON.stringify(tf) });
      console.log('  => replace call with:', JSON.stringify(tf));
    }
  }
  replacements.sort((a, b) => b.start - a.start);
  for (const r of replacements) {
    out = out.slice(0, r.start) + r.text + out.slice(r.end);
  }
  for (const [varName, literal] of Object.entries(varMap)) {
    out = out.replace(new RegExp('\\b' + varName + '\\b(?=[,)])', 'g'), literal);
    console.log('  var replace', varName, '->', literal);
  }
  return out;
}

const src = fs.readFileSync('strategies/golden_eye_scalper.pine', 'utf-8');
const lines = src.split('\n');
console.log('=== Line 75 (input.timeframe) ===');
console.log(lines[74]);
console.log('=== Line 146 (request.security) ===');
console.log(lines[145]);

const processed = replaceInputTimeframe(src, '60');
const plines = processed.split('\n');
console.log('=== Processed Line 75 ===');
console.log(plines[74]);
console.log('=== Processed Line 146 ===');
console.log(plines[145]);
