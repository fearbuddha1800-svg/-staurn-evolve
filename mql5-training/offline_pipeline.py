"""Validate curated provenance and build deterministic retrieval records, offline."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent


def validate(root: Path, manifest: dict) -> list[dict]:
    """Fail closed on malformed provenance; hashes cover local notes, not web pages."""
    if manifest.get('schema_version') != 1 or not manifest.get('sources'):
        raise ValueError('expected schema_version 1 and nonempty sources')
    records = []
    seen = set()
    for source in manifest['sources']:
        required = ('id', 'url', 'title', 'path', 'sha256', 'verified_on',
                    'content_kind', 'rights', 'training_allowed')
        if any(key not in source for key in required):
            raise ValueError('missing source metadata')
        if not all(isinstance(source[key], str) and source[key].strip()
                   for key in required if key != 'training_allowed'):
            raise ValueError('source metadata must be nonempty strings')
        if source['id'] in seen:
            raise ValueError('duplicate source id')
        seen.add(source['id'])
        url = urlsplit(source['url'])
        if (url.scheme != 'https' or url.netloc != 'www.mql5.com'
                or not url.path.startswith('/en/docs/') or url.query or url.fragment):
            raise ValueError('expected official MQL5 documentation URL')
        path = (root / source['path']).resolve()
        if not path.is_relative_to((root / 'curated').resolve()):
            raise ValueError('source path outside curated directory')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != source['sha256']:
            raise ValueError('hash mismatch: ' + source['id'])
        text = data.decode('utf-8').strip()
        if not text or any(token in text.lower() for token in ('todo', 'placeholder', 'tbd')):
            raise ValueError('empty or placeholder source content')
        if source['content_kind'] != 'authored_summary':
            raise ValueError('only authored_summary supported; not a downloaded snapshot')
        if source['training_allowed'] is not False:
            raise ValueError('training export disabled pending separate rights review')
        records.append({'id': source['id'], 'title': source['title'],
                        'url': source['url'], 'text': text,
                        'sha256': source['sha256'], 'training_allowed': False})
    return sorted(records, key=lambda row: row['id'])


def build(root: Path, manifest: dict, output: Path) -> dict:
    """Export retrieval notes, never a training set or model weights."""
    records = validate(root, manifest)
    payload = ''.join(json.dumps(row, sort_keys=True, ensure_ascii=False) + '\n'
                      for row in records).encode('utf-8')
    report = {'schema_version': 1, 'records': len(records), 'training_records': 0,
              'retrieval_sha256': hashlib.sha256(payload).hexdigest(),
              'validation': 'provenance_and_integrity_only',
              'mql5_compiled': False, 'model_trained': False}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'retrieval.jsonl').write_bytes(payload)
    (output / 'validation.json').write_bytes(
        (json.dumps(report, indent=2, sort_keys=True) + '\n').encode('utf-8'))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'offline_output')
    args = parser.parse_args()
    try:
        manifest = json.loads((ROOT / 'source_manifest.json').read_text(encoding='utf-8'))
        print(json.dumps(build(ROOT, manifest, args.output), sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'Validation failed: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
