"""Read-only redevelopment containment status. Never launches or connects MT5.

python redevelop_status.py --receipt backups/redevelop-.../containment.json
A contained worker is paused, NOT upgraded to newly edited source. Never resume
an old process expecting it to have loaded code that changed on disk.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import psutil


def inspect_receipt(receipt_path, *, process_factory=psutil.Process):
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    root = Path(receipt['root'])
    workers = []
    for item in receipt['suspended']:
        row = {'pid': item['pid'], 'script': item['script']}
        try:
            p = process_factory(item['pid'])
            if p.create_time() != item['create_time']:
                row['state'] = 'pid_reused_not_our_worker'
            else:
                status = p.status()
                row['state'] = 'paused_old_code' if status == psutil.STATUS_STOPPED else status
        except psutil.NoSuchProcess:
            row['state'] = 'exited'
        except psutil.AccessDenied:
            row['state'] = 'unknown_access_denied'
        workers.append(row)
    markers = {name: (root / name).exists() for name in
               ('HALT', 'MAINTENANCE', 'STOP', 'BROKER_CONNECT_ALLOWED', 'SYSTEM_AUTOSTART_ALLOWED')}
    return {'mode': 'read_only', 'markers': markers, 'workers': workers,
            'receipt_workers_contained': all(w['state'] in ('paused_old_code', 'exited') for w in workers),
            'coverage': 'receipt identities only; does not exclude other processes or supervisors',
            'broker_authorization': 'not_probed', 'positions': 'not_probed',
            'warning': 'Automated trailing is paused with manage.py; native broker stops are not altered.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_receipt(args.receipt), indent=2))


if __name__ == '__main__':
    main()
