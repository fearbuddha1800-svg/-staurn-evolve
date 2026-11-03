import re

html = open('cockpit_ui.html', encoding='utf-8').read()
ids = set(re.findall(r'id="([^"]+)"', html))
print('HTML element IDs:', len(ids), 'elements')

quant = open('cockpit_assets/quant.js', encoding='utf-8').read()
jq_refs = set(re.findall(r"\$('([^']+)')", quant))
jq_refs2 = set(re.findall(r'$("([^"]+)")', quant))
all_jq = jq_refs | jq_refs2
missing = all_jq - ids
print('quant.js $() references:', len(all_jq))
print('MISSING element IDs for quant.js:', sorted(missing))

mt = open('cockpit_assets/matrix-terminal.js', encoding='utf-8').read()
get_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', mt))
missing2 = get_ids - ids
print('matrix-terminal.js getElementById:', len(get_ids))
print('MISSING element IDs for matrix-terminal.js:', sorted(missing2))

mp = open('cockpit_assets/matrix-panels.js', encoding='utf-8').read()
mp_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', mp))
missing3 = mp_ids - ids
print('matrix-panels.js getElementById:', len(mp_ids))
print('MISSING element IDs for matrix-panels.js:', sorted(missing3))
