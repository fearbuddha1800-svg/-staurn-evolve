"""Empire-grade Algorithmic Trading System Framework.

This module provides the complete professional infrastructure for AI-powered
algorithmic trading, including:
- Neural network model interfaces
- Audit ledger with immutable logging
- Telegram signal deduplication
- Offline-to-live upgrade paths
- Strategy transposition from Pine Script
- Real account integration hooks (credentials supplied at runtime)

SANDBOX NOTE: MT5/broker connections are injected at runtime via
the executor/manager. This module never imports live execution modules
at import time - all connections are gated through runtime injection.
"""

from __future__ import annotations
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Runtime-injected surfaces — never imported at module level
# ---------------------------------------------------------------------------
# The caller (executor.py, manager.py) injects these at startup:
#   mt5           → MetaTrader5 compiled module (or mock)
#   CONFIG        → dict with runtime configuration
#   DB            → str path to signals database
#   HALT_FILE     → path to halt flag file (or None)
# ---------------------------------------------------------------------------

mt5 = None  # type: ignore[assignment]
CONFIG = None  # type: ignore[assignment]
DB = str(Path(__file__).resolve().parent / "signals.db")
HALT_FILE = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Audit Ledger — immutable, append-only logging for every signal/decision
# ---------------------------------------------------------------------------

LEDGER_DIR = Path(__file__).resolve().parent / "audit_ledger"
LEDGER_DIR.mkdir(exist_ok=True)

LEDGER_FILE = LEDGER_DIR / "ledger.jsonl"


def _ledger_hash(entry: Dict[str, Any]) -> str:
    """Compute a SHA-256 hash of the entry for immutability chaining."""
    snapshot = {k: v for k, v in sorted(entry.items()) if k != "id"}
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def log_signal(
    strategy: str,
    symbol: str,
    signal_type: str,
    price: float,
    confidence: Optional[float],
    sl: Optional[float],
    tp: Optional[float],
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Append an immutable audit-log entry for a trading signal.

    Returns the entry's unique ID (hash-based for verification).
    """
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "price": price,
        "confidence": confidence,
        "sl": sl,
        "tp": tp,
        "metadata": metadata or {},
        "previous_hash": "",
    }
    # Chain to previous entry
    if LEDGER_FILE.exists():
        last_line = LEDGER_FILE.read_text().strip().split("\n")[-1]
        prev_entry = json.loads(last_line)
        entry["previous_hash"] = prev_entry.get("hash", "")
    computed_hash = _ledger_hash(entry)
    entry["hash"] = computed_hash
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry["id"]


def verify_ledger_integrity() -> bool:
    """Verify the full audit ledger chain — every hash links to the prior."""
    if not LEDGER_FILE.exists():
        return True  # empty ledger is valid
    lines = LEDGER_FILE.read_text().strip().split("\n")
    prev_hash = ""
    for line in lines:
        entry = json.loads(line)
        if entry.get("previous_hash") != prev_hash:
            return False
        # Re-compute and verify our hash matches
        computed = _ledger_hash({k: v for k, v in entry.items() if k != "hash"})
        if entry.get("hash") != computed:
            return False
        prev_hash = entry["hash"]
    return True


# ---------------------------------------------------------------------------
# Telegram Signal Deduplication
# ---------------------------------------------------------------------------

SIGNATURE_WINDOW_SECONDS = 300  # 5-minute window for dedup


class TelegramDedup:
    """Deduplicate Telegram signals based on content signature within a window.

    Stores recent signal hashes in memory (reset on process restart).
    In production, persist to Redis or the audit ledger.
    """

    def __init__(self, window_seconds: int = SIGNATURE_WINDOW_SECONDS):
        self.window_seconds = window_seconds
        self._recent: List[Tuple[float, str]] = []  # (timestamp, signature)

    def _signature(self, text: str) -> str:
        """Create a content-based signature for deduplication."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def is_duplicate(self, signal_text: str) -> bool:
        """Return True if this signal was seen within the dedup window."""
        now = time.time()
        sig = self._signature(signal_text)

        # Clean expired entries
        self._recent = [(t, s) for t, s in self._recent if now - t < self.window_seconds]

        # Check for exact match
        for ts, s in self._recent:
            if s == sig:
                return True

        # Add this one
        self._recent.append((now, sig))
        return False


# ---------------------------------------------------------------------------
# Neural Network Model Interface
# ---------------------------------------------------------------------------

class NeuralModelInterface:
    """Abstract interface for neural network models used in trading.

    Concrete implementations must provide:
    - predict(features) -> float (signal strength direction)
    - save(path) / load(path) for persistence
    - feature_names() -> List[str]
    """

    def predict(self, features: Dict[str, float]) -> Dict[str, float]:
        """Return {direction: float, confidence: float, rationale: str}.

        direction: "LONG", "SHORT", or "FLAT"
        confidence: 0.0 - 1.0
        """
        raise NotImplementedError

    def feature_names(self) -> List[str]:
        """Return list of expected feature names."""
        raise NotImplementedError

    def save(self, path: Path) -> None:
        """Persist model weights/state to disk."""
        raise NotImplementedError

    def load(self, path: Path) -> None:
        """Restore model weights/state from disk."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Strategy Framework — transposed from Pine Script + native Python
# ---------------------------------------------------------------------------

try:
    from .strategies.ema_cross import evaluate as ema_evaluate
    from .strategies.transpiled_strategies import (
        ema_cross_strategy as transpiled_ema_cross,
        rsi_ema_trend_strategy as transpiled_rsi_ema_trend,
        rsi as transpiled_rsi,
        crossover as transpiled_crossover,
        crossunder as transpiled_crossunder,
    )
except ImportError:  # standalone script execution
    from strategies.ema_cross import evaluate as ema_evaluate
    from strategies.transpiled_strategies import (
        ema_cross_strategy as transpiled_ema_cross,
        rsi_ema_trend_strategy as transpiled_rsi_ema_trend,
        rsi as transpiled_rsi,
        crossover as transpiled_crossover,
        crossunder as transpiled_crossunder,
    )


def run_strategy_frame(
    close_prices: List[float],
    *,
    strategy: str = "ema_cross",
    rsi_len: int = 14,
    ema_fast: int = 9,
    ema_slow: int = 21,
    atr_len: int = 14,
    use_neural: bool = False,
    neural_model: Optional[NeuralModelInterface] = None,
) -> Dict[str, Any]:
    """Run a strategy strategy on close-price series, optionally with neural overlay.

    Returns dict with signal, confidence, and all conditions evaluated.
    """
    if strategy == "ema_cross":
        base = ema_evaluate(close_prices, fast_len=ema_fast, slow_len=ema_slow)
        # Neural confidence overlay if model provided
        confidence = base["signal"]  # will be LONG/SHORT/None
        if use_neural and neural_model and confidence:
            features = {
                "fast_ema": base["fast_ema"],
                "slow_ema": base["slow_ema"],
                "signal": 1.0 if confidence == "LONG" else -1.0 if confidence == "SHORT" else 0.0,
            }
            nn_result = neural_model.predict(features)
            confidence = nn_result.get("confidence", 0.5)
        return {
            "strategy": "ema_cross",
            "signal": base["signal"],
            "confidence": round(confidence, 4),
            "fast_ema": base["fast_ema"],
            "slow_ema": base["slow_ema"],
        }

    if strategy == "rsi_ema_trend":
        base = transpiled_rsi_ema_trend(
            close_prices,
            rsi_len=rsi_len,
            ema_len=ema_fast,
            atr_len=atr_len,
        )
        # Use the first bar's conditions
        if base["signals"] and base["signals"][0]:
            s = base["signals"][0]
            signal = "LONG" if s.get("long_entry") else ("SHORT" if s.get("short_entry") else None)
        else:
            signal = base.get("mode", "signal_only")
            confidence = 0.5
            return {
                "strategy": "rsi_ema_trend",
                "signal": signal,
                "confidence": confidence,
                "mode": base.get("mode"),
            }

    # Fallback
    return {
        "strategy": strategy,
        "signal": None,
        "confidence": 0.0,
    }


# ---------------------------------------------------------------------------
# Offline-to-Live Upgrade Path Blueprint
# ---------------------------------------------------------------------------

UPGRADE_PATH = LEDGER_DIR / "upgrade_path.json"


def generate_upgrade_blueprint(
    current_config: Dict[str, Any],
    target_infrastructure: str = "live_mt5",
) -> Dict[str, Any]:
    """Generate an explicit offline-to-live upgrade blueprint.

    This documents every change needed to move from offline development
    to live deployment, including:
    - Credential migration (demo → live account)
    - Risk policy activation
    - Order-send enablement
    - Monitoring & alerting setup
    """
    blueprint = {
        "version": "1.0.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "current_infrastructure": "offline",
        "target_infrastructure": target_infrastructure,
        "current_config": current_config,
        "required_changes": [],
        "checklist": [],
    }

    if target_infrastructure == "live_mt5":
        blueprint["required_changes"] = [
            {"step": 1, "action": "Provide live MT5 account credentials",
             "critical": True},
            {"step": 2, "action": "Activate real-order policy in CONFIG",
             "critical": True},
            {"step": 3, "action": "Remove HALT file if present",
             "critical": False},
            {"step": 4, "action": "Test with single small order paper-trading",
             "critical": True},
            {"step": 5, "action": "Enable full live execution pipeline",
             "critical": True},
        ]
        blueprint["checklist"] = [
            "MT5 login credentials verified",
            "Real account balance confirmed",
            "Risk limits set per strategy",
            "Stop-loss/take-profit policies active",
            "Audit ledger path writeable",
            "Telegram notifications configured",
        ]

    UPGRADE_PATH.write_text(json.dumps(blueprint, indent=2))
    return blueprint


# ---------------------------------------------------------------------------
# Module entrypoint — sanity check
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Demonstrate ledger logging
    eid = log_signal(
        strategy="ema_cross",
        symbol="XAUUSD",
        signal_type="LONG",
        price=4145.62,
        confidence=0.87,
        sl=4120.0,
        tp=None,
        metadata={"fast_ema": 4140.0, "slow_ema": 4150.0},
    )
    print(f"Logged signal ID: {eid}")
    print(f"Ledger integrity: {verify_ledger_integrity()}")
    print(f"Ledger entries: {len(LEDGER_FILE.read_text().strip().split(chr(10)))}")