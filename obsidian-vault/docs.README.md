---
slug: docs.README
type: note
graph: gitnexus
---

# Signal Relay documentation

Start with existing [architecture](../ARCHITECTURE.md), [HQ user guide](../HQ_USER_GUIDE.md), [packaging](../ARCHITECTURE_PACKAGING.md), [delivery ledger](../DELIVERY_LEDGER.md), and [remaining blockers](../REMAINING_BLOCKERS.md).

* [API contract and compatibility notes](API_SPECIFICATION.md) / [OpenAPI JSON](openapi.json)
* [Operator runbooks](OPERATOR_RUNBOOKS.md)
* [Developer guide](DEVELOPER_GUIDE.md)
* [Troubleshooting](TROUBLESHOOTING.md)
* [Architecture diagrams and sequence sources](diagrams/README.md)

The source code is authoritative. These procedures are documentation, not approval to start trading or lift safety latches. Validation: `python docs/validate_docs.py`; isolated boundary tests: `python -m unittest test_cockpit_boundary_v2`. Documentation checks do not contact a broker or change runtime flags.

