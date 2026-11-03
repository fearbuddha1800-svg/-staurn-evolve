---
slug: ai_overlay
type: note
graph: gitnexus
---

"""Point-in-time Golden Edge shadow scoring; no order/promotion authority.

Golden Eye indices are NOT probabilities. Missing values have masks. Untrained
models return exactly 0.5, not measured success. Supply aligned closed bars.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Mapping

from empire_framework import NeuralModelInterface

FEATURE_VERSION = "golden_edge_v1"
PLOT_ALIASES = {
    "regime": ("TrendRegime enum 0 transition / 1 trend / 2 range / 3 expansion / 4 compression",),
    "strength": ("TrendStrength (uncalibrated)",),
    "consensus": ("TrendConsensus (3-group agreement)",),
    "persistence": ("TrendPersistence",),
    "acceleration": ("TrendAcceleration",),
    "disagreement": ("disagreement_index", "Trend disagreement index (not probability)"),
    "dmi_plus": ("dmiPlus", "QG04 adaptive +DI"),
    "dmi_minus": ("dmiMinus", "QG04 adaptive -DI"),
    "adx": ("QG04 adaptive ADX",),
    "mtf_agreement": ("mtfAgreement", "QG14 confirmed MTF agreement fraction"),
    "displacement_atr": ("displacementAtr", "QG09 price-filter displacement / ATR"),
    "er": ("QG19 Efficiency Ratio",),
    "rsi": ("RSI",), "atr": ("ATR",),
    "spread": (), "hour": (), "policy_allowed": (),
}
REGIMES = {0: "transition", 1: "trend", 2: "range", 3: "expansion", 4: "compression"}


def _number(value: Any) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _latest(value: Any) -> float | None:
    """Never search backward past a missing last observation."""
    if isinstance(value, Mapping):
        if "latest" in value:
            return _number(value["latest"])
        value = value.get("data", value.get("value"))
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else None
    if isinstance(value, Mapping):
        value = value.get("value")
    return _number(value)


def _direction(signal: Mapping[str, Any]) -> tuple[str, float]:
    value = str(signal.get("direction") or signal.get("action") or signal.get("type") or "").upper()
    if value in {"LONG", "BUY", "1"}:
        return "LONG", 1.0
    if value in {"SHORT", "SELL", "-1"}:
        return "SHORT", -1.0
    return "FLAT", 0.0


def extract_features(signal: Mapping[str, Any], pine_result: Mapping[str, Any],
                     context: Mapping[str, Any] | None = None
                     ) -> tuple[dict[str, float], dict[str, str], list[str]]:
    """Fixed numeric schema + raw categories for train-only encoding.

    Priority: context, signal golden_eye, result golden_eye, plots.
    Spread is price units; hour is UTC. No outcomes or wall-clock features.
    Category-aware adapters use predict_setup(features, categories).
    """
    ctx = dict(pine_result.get("context") or {})
    ctx.update(signal.get("context") or {})
    ctx.update(context or {})
    sources = [ctx, signal.get("golden_eye") or {},
               pine_result.get("golden_eye") or {}, pine_result.get("plots") or {}]
    _, side = _direction(signal)
    features: dict[str, float] = {"signal_direction": side}
    missing: list[str] = []

    def put(name: str, value: float | None) -> None:
        features[name] = value if value is not None else 0.0
        features[name + "_missing"] = float(value is None)
        if value is None:
            missing.append(name)

    values: dict[str, float | None] = {}
    for name, aliases in PLOT_ALIASES.items():
        value, found = None, False
        for source in sources:
            for key in (name, *aliases):
                if key in source:
                    value, found = _latest(source[key]), True
                    break
            if found:
                break
        if name in {"strength", "consensus", "persistence", "disagreement", "mtf_agreement", "er"}:
            if value is not None and not 0 <= value <= 1:
                value = None
        if name == "regime" and value not in REGIMES:
            value = None
        if name == "hour" and value is not None and not 0 <= value < 24:
            value = None
        if name == "policy_allowed" and value not in (None, 0, 1):
            value = None
        if name in {"spread", "dmi_plus", "dmi_minus", "adx"} and value is not None and value < 0:
            value = None
        if name == "atr" and value is not None and value <= 0:
            value = None
        if name == "rsi" and value is not None and not 0 <= value <= 100:
            value = None
        values[name] = value
    if values["hour"] is None and ctx.get("bar_close_time") is not None:
        try:
            stamp = datetime.fromisoformat(str(ctx["bar_close_time"]).replace("Z", "+00:00"))
            if stamp.tzinfo is not None:
                values["hour"] = float(stamp.astimezone(timezone.utc).hour)
        except (ValueError, TypeError, OverflowError):
            pass
    for name, value in values.items():
        put(name, value)
    for code, label in REGIMES.items():
        features["regime_" + label] = float(values["regime"] == code)
    for name in ("acceleration", "displacement_atr"):
        put(name + "_aligned", None if values[name] is None or not side else values[name] * side)
    plus, minus, atr = values["dmi_plus"], values["dmi_minus"], values["atr"]
    balance = None if plus is None or minus is None or plus + minus <= 0 else (plus - minus) / (plus + minus)
    put("dmi_balance", balance)
    put("dmi_alignment", None if balance is None or not side else balance * side)
    put("spread_atr", None if atr is None or values["spread"] is None else values["spread"] / atr)
    hour = values["hour"]
    put("hour_sin", None if hour is None else math.sin(2 * math.pi * hour / 24))
    put("hour_cos", None if hour is None else math.cos(2 * math.pi * hour / 24))
    categories = {name: str(ctx.get(name) or signal.get(name) or pine_result.get(name) or "unknown")
                  for name in ("symbol", "session", "policy", "timeframe", "setup_id")}
    return features, categories, missing


@dataclass
class AIPrediction:
    direction: str
    confidence: float
    rationale: str
    features: dict[str, float]
    regime: str = "unknown"
    regime_bias: float = 0.0  # Signed DMI balance, not a probability.
    model_status: str = "untrained"
    feature_version: str = FEATURE_VERSION
    categories: dict[str, str] = field(default_factory=dict)
    missing_features: list[str] = field(default_factory=list)
    passes_threshold: bool = False
    mode: str = "shadow"

    @property
    def setup_confidence(self) -> float:
        return self.confidence


class StubNeuralModel(NeuralModelInterface):
    """Exactly neutral until a real evaluated model is supplied."""
    is_trained = False

    def feature_names(self) -> list[str]:
        return list(extract_features({}, {})[0])

    def predict(self, features: dict[str, float]) -> dict[str, Any]:
        side = features.get("signal_direction", 0)
        return {"direction": "LONG" if side > 0 else "SHORT" if side < 0 else "FLAT",
                "confidence": 0.5, "rationale": "stub_model_neutral_untrained"}

    def save(self, path) -> None:
        raise NotImplementedError("No trained artifact to save")

    def load(self, path) -> None:
        raise NotImplementedError("Stub cannot activate trained artifacts")


class AIOverlay:
    """Annotate every signal in shadow; never suppress a rules signal.

    Injected models declare is_trained=True and matching feature_version.
    Scoring is NOT promotion. Activation needs separate independent approval.
    """
    def __init__(self, model: NeuralModelInterface | None = None,
                 min_confidence: float = 0.3):
        if not math.isfinite(min_confidence) or not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be in [0, 1]")
        self.model = model if model is not None else StubNeuralModel()
        self.min_confidence = min_confidence

    def evaluate(self, signal: dict[str, Any], pine_result: dict[str, Any],
                 context: Mapping[str, Any] | None = None) -> AIPrediction:
        features, categories, missing = extract_features(signal, pine_result, context)
        direction, _ = _direction(signal)
        confidence, status, rationale = 0.5, "untrained", "stub_model_neutral_untrained"
        if getattr(self.model, "is_trained", False):
            status, rationale = "invalid", "model_schema_mismatch"
            if getattr(self.model, "feature_version", None) == FEATURE_VERSION:
                try:
                    if hasattr(self.model, "predict_setup"):
                        result = self.model.predict_setup(features, categories)
                    else:
                        result = self.model.predict(features)
                    score = _number(result.get("confidence"))
                    if score is None or not 0 <= score <= 1:
                        raise ValueError("invalid probability")
                    confidence, status = score, "trained_shadow"
                    rationale = str(result.get("rationale", "trained_shadow_prediction"))
                except Exception:
                    status, rationale = "invalid", "model_failure_neutral"
        regime = "unknown" if features["regime_missing"] else REGIMES[int(features["regime"])]
        bias = features["dmi_balance"] if not features["dmi_balance_missing"] else 0.0
        return AIPrediction(
            direction=direction, confidence=confidence, rationale=rationale, features=features,
            regime=regime, regime_bias=bias, model_status=status, categories=categories,
            missing_features=missing,
            passes_threshold=status == "trained_shadow" and confidence >= self.min_confidence,
        )


__all__ = ["AIOverlay", "AIPrediction", "StubNeuralModel", "extract_features", "FEATURE_VERSION"]

## Links from
- [[signal_watcher]]
- [[test_golden_edge_overlay]]
