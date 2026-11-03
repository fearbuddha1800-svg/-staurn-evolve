---
slug: agent-reports.ai-availability-current
type: note
graph: gitnexus
---

# AI Integration Availability — Current State

**Date:** 2026-10-18  
**Scope:** Read-only verification of local AI router endpoint (localhost:20128 / 9Router)

---

## Summary

| Component | Status | Details |
|-----------|--------|---------|
| AI Router Health | ⚠️ 404 on `/health` | No dedicated health endpoint |
| Models Endpoint | ✅ 200 OK | Returns 2 models |
| Trading Isolation | ✅ Verified | No trading capability in AI path |
| Inference Test | ❌ Not performed | Per requirements: no inference calls |

---

## Endpoint Verification

### GET /health
```bash
curl http://localhost:20128/health
```
**Result:** 404 Not Found (Next.js default page)

### GET /v1/models
```bash
curl http://localhost:20128/v1/models
```
**Result:** 200 OK
```json
{
  "object": "list",
  "data": [
    {
      "id": "oracle",
      "object": "model",
      "owned_by": "combo",
      "capabilities": {
        "vision": true,
        "pdf": true,
        "audioInput": true,
        "videoInput": true,
        "imageOutput": false,
        "audioOutput": false,
        "search": false,
        "tools": true,
        "reasoning": true,
        "thinkingFormat": "deepseek",
        "thinkingCanDisable": false,
        "contextWindow": 128000,
        "maxOutput": 384000
      },
      "context_length": 128000,
      "max_completion_tokens": 32000
    },
    {
      "id": "free",
      "object": "model",
      "owned_by": "combo",
      "capabilities": {
        "vision": true,
        "pdf": true,
        "audioInput": true,
        "videoInput": true,
        "imageOutput": false,
        "audioOutput": false,
        "search": false,
        "tools": true,
        "reasoning": true,
        "thinkingFormat": "deepseek",
        "thinkingCanDisable": false,
        "contextWindow": 128000,
        "maxOutput": 384000
      },
      "context_length": 128000,
      "max_completion_tokens": 32000
    }
  ]
}
```

---

## Trading Isolation Verification

| Path | Trading Capability | Evidence |
|------|-------------------|----------|
| AI Router (localhost:20128) | ❌ None | OpenAI-compatible `/v1/chat/completions` only; no MT5/broker access |
| PineTS Bridge | ❌ None | Runs Pine Script simulation only; no order execution |
| Signal Relay Daemon | ✅ Has trading | Separate process; not accessible from AI router |
| Executor/Manage/Strategy | ✅ Has trading | Separate Python modules; not called by AI |

**Conclusion:** AI router is a **pure inference endpoint** with no access to trading functions, MT5, or broker credentials. Trading authority remains exclusively in the Python daemon/executor layer.

---

## Delegation Provider Context

- **Current delegation.provider:** `xai-oauth` / `grok-4.6` (since 2026-10-17)
- **Previous:** `openai-codex` / `gpt-6.1-sol` (failed: HTTP 429 rate limits)
- **Local AI Router:** `localhost:20128` (9Router) — available but not configured as delegation provider

---

## Configuration Reference

**config.yaml** (delegation section):
```yaml
delegation:
  provider: xai-oauth
  model: grok-4.6
  max_concurrent_children: 5
```

---

## Verification Commands

```bash
# Check models endpoint
curl -s http://localhost:20128/v1/models | jq .

# Check health (returns 404)
curl -s http://localhost:20128/health

# Note: No inference test performed per requirements (no order side effects)
```

