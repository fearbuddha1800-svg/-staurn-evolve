import time
from scalp360.ai_extract import AIExtractor, AIExtractConfig, CircuitOpen
from scalp360.neural import evaluate, purged_splits, LogisticChallenger

def test_circuit_breaker_abstains():
    def boom(text, timeout): raise TimeoutError()
    x = AIExtractor(AIExtractConfig(circuit_breaker_fails=1), boom)
    assert "model error" in x.extract("hi").abstained_reason
    assert "circuit" in x.extract("hi").abstained_reason

def test_uncalibrated_confidence_passes_through():
    def llm(text, t): return {"kind": "new_entry", "symbol": "XAUUSD", "side": "SELL",
                              "confidence": 0.97, "evidence": {"entry": "4184/90"}}
    r = AIExtractor(AIExtractConfig(), llm).extract("x")
    assert r.kind == "NEW_ENTRY" and r.evidence.get("entry") == "4184/90"

def test_purge_blocks_leakage():
    n = 100; emb = 5
    for train, test in purged_splits(n, k=5, embargo=emb):
        assert not set(train) & set(test)
        for t in test:
            assert not any(abs(t - tr) <= emb for tr in train), "embargo violated"

def test_eval_rejects_small_samples():
    X = [(0.1,)] * 20; y = [0, 1] * 10
    rep = evaluate(X, y)
    assert rep.decision.startswith("REJECT") and "insufficient" in rep.decision

def test_eval_finds_signal_when_real():
    # feature 0 perfectly separates; 400 samples -> holdout should show lift
    X = [(1.0 if i % 2 == 0 else -1.0,) for i in range(400)]
    y = [1 if i % 2 == 0 else 0 for i in range(400)]
    rep = evaluate(X, y)
    assert rep.holdout_auc >= 0.9, rep
    assert rep.decision in ("PROMOTE", "KEEP_SHADOW")
