---
slug: portfolio_attribution
type: note
graph: gitnexus
---

"""Version-safe adapter to the existing magic-based attribution report."""
import json
import math
from strategy_identity import attribution_report, resolve_magic


def versioned_attribution(deals, registry):
    """Group by (strategy id, version) before calling the legacy id-only helper.

    Uses current registry mapping, not historical version inference. Counts are
    deals, NOT round-trip trades. Broker cash transfers must be filtered upstream.
    """
    try:
        if deals is None:
            return {'available': False, 'reason': 'Broker history unavailable', 'total': None}
        grouped = {}
        for deal in deals:
            magic = deal.get('magic', 0) if isinstance(deal, dict) else getattr(deal, 'magic', 0)
            identity = resolve_magic(magic, registry)
            grouped.setdefault((identity.id, identity.version), []).append(deal)
        by_identity, total_count, total_pl, unknown = {}, 0, 0.0, set()
        for (sid, version), rows in sorted(grouped.items()):
            report = attribution_report(rows, registry)
            item = report['by_identity'][sid]
            if not math.isfinite(item['pl']):
                raise ValueError('Nonfinite deal P&L')
            item['magics'] = sorted(set(int(d.get('magic', 0) if isinstance(d, dict) else getattr(d, 'magic', 0)) for d in rows))
            # JSON tuple encoding avoids delimiter collisions in user-defined IDs.
            by_identity[json.dumps([sid, version], separators=(',', ':'))] = item
            total_count += report['total']['count']
            total_pl += report['total']['pl']
            unknown.update(report['unknown_magic'])
        return {'available': True, 'total': {'count': total_count, 'pl': round(total_pl, 2)},
                'by_identity': by_identity, 'unknown_magic': sorted(unknown),
                'grouping': ['strategy_id', 'version'],
                'methodology': 'MT5 BUY/SELL deals profit + commission + swap + fee, including entry costs; counts are deals, not trades. Current registry magic mapping only; shared legacy magic cannot distinguish underlying engines or historical versions.'}
    except Exception as exc:
        return {'available': False, 'reason': 'Attribution unavailable: ' + type(exc).__name__, 'total': None}

## Links from
- [[cockpit]]
- [[test_portfolio_risk]]
