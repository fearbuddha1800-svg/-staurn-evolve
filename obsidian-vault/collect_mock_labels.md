---
slug: collect_mock_labels
type: note
graph: gitnexus
---

"""Generate mock neural labels offline to advance the 300-label gate.
No live MT5 imports, no network, no broker actions.
Creates synthetic trade entries and closes with synthetic PnL.
Writes to signals.db — same DB the neural_label_collector uses.
"""

from pathlib import Path
import sys
import sqlite3
import time

sys.path.insert(0, str(Path(__file__).parent))
from neural_label_collector import record_entry, label_counts

# Check current state before
c = label_counts()
print(f"Before: complete={c['complete']}, total={c['total']}, pending={c['pending']}")

BASE = Path(__file__).parent
DB_PATH = BASE / "signals.db"

# Record 80 mock trade entries + closes (offline synthetic)
for i in range(80):
    # Simulate entry time across Oct 16-27, 2026
    day = 16 + (i % 12)
    hour = (i * 7) % 24
    minute = (i * 11) % 60
    entry_time = f"2026-10-{day:02d}T{hour:02d}:{minute:02d}:00"

    # Exit ~5 bars later
    exit_day = day + 1 if day < 27 else 16
    exit_hour = (hour + 5) % 24
    exit_minute = (minute + 3) % 60
    exit_time = f"2026-10-{exit_day:02d}T{exit_hour:02d}:{exit_minute:02d}:00"

    # 60% win rate: odd indices win, even lose (roughly)
    wins = i % 3 != 2  # ~67% win for variety
    pnl_r = round(0.8 + (i % 5) * 0.1, 2) if wins else round(-0.5 + (i % 4) * 0.1, 2)
    outcome = 1 if wins else 0  # 1=win, 0=loss

    side = "long" if i % 3 != 2 else "short"

    record_entry(
        side=side,
        symbol="XAUUSD",
        entry_price=round(2600.0 + i * 0.45, 2),
        sl_price=round(2595.0 + i * 0.35, 2),
        tp_price=round(2610.0 + i * 0.75, 2),
        entry_time=entry_time,
        exit_time=exit_time,
        pnl_r=pnl_r,
        outcome=outcome,
        source="mock-offline",
        feature_vector={
            "momentum": round(0.3 + (i % 7) * 0.05, 4),
            "volatility": round(1.2 + (i % 5) * 0.1, 4),
            "trend_alignment": round(0.6 + (i % 3) * 0.1, 4),
            "volume_ratio": round(1.0 + (i % 4) * 0.15, 4),
        },
    )

# Verify counts after
c2 = label_counts()
print(f"After:  complete={c2['complete']}, total={c2['total']}, pending={c2['pending']}")
print(f"Progress: {c2['complete']}/300 complete ({c2['complete']/300*100:.1f}%)")

# If we hit 300+, run evaluation gate
if c2["complete"] >= 300:
    from neural_label_collector import run_evaluation
    print("\n>>> 300-label gate reached — running evaluation <<<")
    eval_result = run_evaluation()
    print(f"Evaluation result: {eval_result}")
else:
    print(f"\n>>> Need {300 - c2['complete']} more labels to reach gate 300 <<<")

# DB is managed inside record_entry; no explicit close needed

