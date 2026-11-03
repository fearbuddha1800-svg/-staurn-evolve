---
slug: agent-reports.redevelop-containment
type: note
graph: gitnexus
---

{
  "mode": "read_only",
  "markers": {
    "HALT": true,
    "MAINTENANCE": true,
    "STOP": false,
    "BROKER_CONNECT_ALLOWED": false,
    "SYSTEM_AUTOSTART_ALLOWED": false
  },
  "workers": [
    {
      "pid": 4356,
      "script": "cockpit.py",
      "state": "paused_old_code"
    },
    {
      "pid": 5668,
      "script": "neural_label_collector.py",
      "state": "paused_old_code"
    },
    {
      "pid": 6560,
      "script": "manage.py",
      "state": "paused_old_code"
    },
    {
      "pid": 14844,
      "script": "strategy.py",
      "state": "paused_old_code"
    },
    {
      "pid": 28980,
      "script": "strategy2_live.py",
      "state": "paused_old_code"
    }
  ],
  "receipt_workers_contained": true,
  "coverage": "receipt identities only; does not exclude other processes or supervisors",
  "broker_authorization": "not_probed",
  "positions": "not_probed",
  "warning": "Automated trailing is paused with manage.py; native broker stops are not altered."
}

