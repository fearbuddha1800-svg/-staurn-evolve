---
slug: docs.validate_docs
type: note
graph: gitnexus
---

"""Offline documentation validation; does not import broker/runtime modules."""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / 'docs'
spec = json.loads((DOC / 'openapi.json').read_text(encoding='utf-8'))
source = (ROOT / 'cockpit_runtime.py').read_text(encoding='utf-8-sig')
tree = ast.parse(source)
simple = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'simple' for t in n.targets))
expected = {'/api/' + k.value for k in simple.keys}
expected.update(re.findall(r"path == '(/api/[^']+)'", source))
expected.update({'/api/trace/{ticket}', '/api/candles', '/api/pine_series'})
assert expected == set(spec['paths']), (expected - set(spec['paths']), set(spec['paths']) - expected)
assert set(spec['paths']['/api/session']) == {'post', 'delete'}
for name in ('/api/bootstrap', '/api/pine/compile'):
    assert set(spec['paths'][name]) == {'post'}
for name in expected - {'/api/session', '/api/bootstrap', '/api/pine/compile'}:
    assert set(spec['paths'][name]) == {'get'}, name
ids = [op['operationId'] for ops in spec['paths'].values() for op in ops.values()]
assert len(set(ids)) == len(ids)

def visit(value):
    if isinstance(value, dict):
        if '$ref' in value:
            target = spec
            for part in value['$ref'].split('/')[1:]:
                target = target[part]
        for child in value.values():
            visit(child)
    elif isinstance(value, list):
        for child in value:
            visit(child)
visit(spec)
from jsonschema import Draft202012Validator
for schema in spec['components']['schemas'].values():
    Draft202012Validator.check_schema(schema)
links = 0
for path in DOC.rglob('*.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if not target.startswith(('http:', 'https:', '#')):
            assert (path.parent / target.split('#')[0]).exists(), (path, target)
            links += 1
for path in (DOC / 'diagrams').glob('*.excalidraw'):
    drawing = json.loads(path.read_text(encoding='utf-8'))
    assert drawing['type'] == 'excalidraw' and drawing['version'] == 2
    elements = {e['id']: e for e in drawing['elements']}
    assert len(elements) == len(drawing['elements'])
    for element in elements.values():
        assert element['width'] >= 0 and element['height'] >= 0
        if element.get('containerId'):
            assert element['containerId'] in elements
        for bound in element.get('boundElements') or []:
            assert bound['id'] in elements
for path in (DOC / 'diagrams').glob('*.mmd'):
    text = path.read_text(encoding='utf-8')
    assert text.startswith('sequenceDiagram\n')
    assert text.count('    alt ') == text.count('    end\n'), path
print(json.dumps({'routes': len(expected), 'operations': len(ids), 'markdown_links': links,
                  'excalidraw': len(list((DOC / 'diagrams').glob('*.excalidraw'))),
                  'mermaid': len(list((DOC / 'diagrams').glob('*.mmd'))),
                  'checks': 'PASS; structural validation, not visual rendering'}))

