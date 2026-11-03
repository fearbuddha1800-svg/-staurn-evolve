---
slug: agent-reports.signal-source-audit
type: note
graph: gitnexus
---

{
  "scope": "stored signal_received events only; not complete Telegram history",
  "method": "exact entry/SL/ordered-TP geometry within receipt-time window",
  "window_s": 600,
  "malformed_events": 0,
  "unique_messages": 85,
  "sources": {
    "tg:-1001175463265": {
      "messages": 3,
      "not_signal": 3
    },
    "tg:-1001207746934": {
      "messages": 2,
      "needs_review": 1,
      "not_signal": 1
    },
    "tg:-1001284268486": {
      "messages": 4,
      "needs_review": 2,
      "not_signal": 2
    },
    "tg:-1001588519179": {
      "messages": 3,
      "not_signal": 3
    },
    "tg:-1001713690419": {
      "messages": 17,
      "not_signal": 16,
      "parsed_candidates": 1,
      "geometry_unavailable": 1
    },
    "tg:-1001868019139": {
      "messages": 1,
      "needs_review": 1
    },
    "tg:-1001920020352": {
      "messages": 1,
      "not_signal": 1
    },
    "tg:-1002010239852": {
      "messages": 2,
      "not_signal": 1,
      "parsed_candidates": 1,
      "geometry_comparable": 1,
      "first_observed_geometry": 1
    },
    "tg:-1002165799093": {
      "messages": 22,
      "not_signal": 17,
      "needs_review": 4,
      "parsed_candidates": 1,
      "geometry_comparable": 1,
      "first_observed_geometry": 1
    },
    "tg:-1002369502254": {
      "messages": 2,
      "not_signal": 2
    },
    "tg:-1002520344727": {
      "messages": 6,
      "not_signal": 5,
      "parsed_candidates": 1,
      "geometry_comparable": 1,
      "first_observed_geometry": 1
    },
    "tg:-1003196282951": {
      "messages": 9,
      "not_signal": 4,
      "needs_review": 5
    },
    "tg:-1003723702011": {
      "messages": 1,
      "not_signal": 1
    },
    "tg:-1003924380674": {
      "messages": 12,
      "not_signal": 10,
      "parsed_candidates": 1,
      "geometry_comparable": 1,
      "first_observed_geometry": 1,
      "needs_review": 1
    }
  },
  "echoes": [],
  "limitations": [
    "No profitability inference or live policy changes.",
    "First observed source is not proven original author.",
    "Market-only, incomplete and near-match signals are not matched.",
    "Parsed candidates may include recaps; this is not entry approval."
  ]
}

