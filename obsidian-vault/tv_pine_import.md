---
slug: tv_pine_import
type: note
graph: gitnexus
---

"""Conservative TradingView source importer, not a Pine-to-Python transpiler.

Only text transport artifacts and leading tab indentation are normalized. Unknown
Pine constructs are preserved for PineTS validation, never silently rewritten.
"""
from __future__ import annotations
import ast
import re

MAX_SOURCE = 65536


def split_arguments(text: str) -> list[str]:
    parts, start, depth, quote, escape = [], 0, 0, None, False
    for i, char in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return parts


def calls(source: str, pattern: str):
    """Read balanced calls, including multiline/nested args and quoted commas."""
    # Comments cannot introduce declarations or inputs. Preserve string contents.
    source = re.sub(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|//[^\n]*',
                    lambda m: m.group(1) or '', source)
    for match in re.finditer(pattern + r'\s*\(', source):
        begin = match.end()
        depth, quote, escape = 1, None, False
        for i in range(begin, len(source)):
            char = source[i]
            if quote:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == quote:
                    quote = None
            elif char in ('"', "'"):
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if not depth:
                    yield match, split_arguments(source[begin:i])
                    break


def literal(value: str):
    if value in ('true', 'false'):
        return value == 'true'
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value  # Pine expressions remain expressions, never evaluated.


def parse_tv_export(text: str) -> dict:
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_SOURCE:
        raise ValueError('Pine source must be UTF-8 text, at most 65536 bytes')
    source = text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip('\n')
    fence = re.fullmatch(r'```(?:pine|pinescript)?\s*\n(.*)\n```\s*', source, re.S | re.I)
    if fence:
        source = fence.group(1)
    source = '\n'.join(re.sub(r'^[ \t]+', lambda m: m[0].expandtabs(4), line)
                       for line in source.splitlines()) + '\n'
    version = re.search(r'^\s*//@version\s*=\s*(\d+)\s*$', source, re.M)
    if not version or version[1] not in ('5', '6'):
        raise ValueError('Explicit Pine //@version=5 or 6 required; legacy syntax needs manual migration')
    declarations = list(calls(source, r'(?m)^\s*(strategy|indicator)'))
    if len(declarations) != 1:
        raise ValueError('Exactly one strategy() or indicator() declaration required')
    match, args = declarations[0]
    named = {a.split('=', 1)[0].strip(): a.split('=', 1)[1].strip()
             for a in args if re.match(r'^\w+\s*=', a)}
    title = literal(named.get('title', args[0] if args else '"Untitled"'))
    parameters = []
    for match, args in calls(source, r'(?m)^\s*(?:var\s+)?(?:(?:int|float|bool|string)\s+)?(\w+)\s*=\s*input\.(\w+)'):
        named_input = {a.split('=', 1)[0].strip(): a.split('=', 1)[1].strip()
                       for a in args if re.match(r'^\w+\s*=', a)}
        positional = [a for a in args if not re.match(r'^\w+\s*=', a)]
        parameters.append({'name': match[1], 'type': match[2],
                           'default': literal(named_input.get('defval', positional[0] if positional else 'na')),
                           'title': literal(named_input.get('title', positional[1] if len(positional) > 1 else repr(match[1]))),
                           **{k: literal(v) for k, v in named_input.items()
                              if k in ('minval', 'maxval', 'step', 'options')}})
    metadata = dict(re.findall(r'(?m)^\s*//\s*@(?P<key>version|symbols|timeframe)\s*:?\s+(?P<value>[^\n]+)', source))
    semver = metadata.get('version', '0.1.0').strip()
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?', semver):
        raise ValueError('Invalid strategy semantic version')
    warnings = []
    if re.search(r'(?m)^\s*import\s+', source):
        warnings.append('TradingView libraries require local PineTS support; imports were preserved')
    if 'request.security' in source:
        warnings.append('Multi-timeframe requests need an explicit data provider; no TV parity implied')
    return {'source': source, 'name': str(title), 'pine_version': int(version[1]),
            'kind': declarations[0][0][1], 'version': semver,
            'symbols': [s.strip() for s in metadata.get('symbols', '').split(',') if s.strip()],
            'timeframe': metadata.get('timeframe', '').strip() or None,
            'parameters': parameters, 'warnings': warnings}

## Links from
- [[strategy_registry]]
- [[test_strategy_registry]]
