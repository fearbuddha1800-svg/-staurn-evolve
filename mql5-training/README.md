# MQL5 knowledge preparation: offline, no model training

The supported path is `offline_pipeline.py`. It uses only Python's standard
library and never connects to a broker, Telegram, scraper, or model endpoint.
It validates four small authored factual summaries against an explicit manifest
and exports retrieval JSONL. This is a seed knowledge set, not a complete MQL5
corpus, scraped dataset, trained Hermes model, or profitable trading system.

## Run from the repository root

Python 3.11 or later; no installation or dependencies required.
The verified environment exposes Python through `/tmp/quant-tools`:

```sh
PATH=/tmp/quant-tools:$PATH python -m unittest discover -s mql5-training/offline_tests -v
PATH=/tmp/quant-tools:$PATH python mql5-training/offline_pipeline.py
PATH=/tmp/quant-tools:$PATH python -m compileall -q mql5-training/offline_pipeline.py mql5-training/offline_tests
```

For a normal Windows/Python environment use `python` without the PATH prefix.
Tests find the pipeline with the path setup in `offline_tests/test_pipeline.py`.
Run from any working directory by supplying absolute script/test-directory paths.
Outputs default to `mql5-training/offline_output/`; `--output PATH` changes this.
Re-running with unchanged inputs produces identical bytes, including the report.
All inputs validate before output is written. Exit status 1 indicates failure.
This does not lint or typecheck the legacy Python or compile any MQL5 code.

## Provenance and validation scope

`source_manifest.json` identifies official MetaQuotes reference URLs, date checked,
local note paths, SHA-256 hashes, content kind, and rights status. `curated/*.txt`
are original summaries checked against those pages on 2026-11-04, not downloaded
HTML snapshots. Hashes pin local note bytes only; they do not establish the current
webpage contents, independent factual correctness, or a license grant.
The validator checks metadata, duplicates, URL host/path, path containment,
hashes, UTF-8, basic placeholder markers, and disabled training eligibility.
Tests exercise rejection cases and byte-for-byte reproducibility without network.
This lightweight marker check is not a semantic correctness validator.

Sources: [iMA](https://www.mql5.com/en/docs/indicators/ima),
[CopyBuffer](https://www.mql5.com/en/docs/series/copybuffer),
[IndicatorRelease](https://www.mql5.com/en/docs/series/indicatorrelease), and
[OnInit](https://www.mql5.com/en/docs/event_handlers/oninit).
Public availability is not permission to redistribute source examples or train on
them. Every seed record remains `training_allowed: false`; this tool intentionally
rejects changing that flag. Future training support requires an explicit rights
review and a separate schema/export design, not a manifest flag toggle.

## Hermes: retrieval versus training

Hermes can mean NousResearch model weights or the Hermes agent application.
Putting files in an agent workspace or supplying retrieved passages adds context
at inference time; it does not update model weights. This directory exports
retrieval records only. A consumer must still implement search/ranking and insert
selected `text` plus `url` into the model context. No such integration is claimed.

Fine-tuning requires a specific model ID/revision and license, tokenizer and chat
template, reviewed instruction/answer data, source-grouped train/validation/test
splits, a real trainer, compute, recorded hyperparameters, and held-out evaluation.
No training runtime, adapter, checkpoint, tokenizer, or evaluation results exist
here. The [official Hermes 3 model card](https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B)
is an example model reference, not an assertion of which model your agent uses.
Use its tokenizer's chat template when an actual training stack is selected;
these retrieval notes are not ready-made supervised conversations.

Before promoting generated MQL5 answers: review API signatures and data readiness,
compile in MetaEditor, test deterministic indicator behavior in an isolated tester,
and evaluate held-out tasks separately from the source material. Offline Python
checks prove neither compilation nor execution safety nor strategy performance.

## Existing artifact audit: excluded from the supported path

All pre-existing files remain untouched, untrusted research drafts. Do not use
`training_data/training_data.json*` as approved supervised targets.

| Artifact | Finding / limitation |
| --- | --- |
| `training_data_generator.py`, `tdg_*.py` | Hardcoded synthetic answers; TODO outputs; undefined helpers. The main generator uses seven-argument iMA/value-style calls, contrary to MQL5's six-argument handle API. |
| `training_data/*` | Generated answers without sufficient provenance, rights evidence, compilation checks, or held-out evaluation. |
| `framework/experts/hd_ea.mq5` | Placeholder order-flow logic and optional PineTS/model integrations; not verified as buildable or executable. |
| `scrapers/*` | Requires third-party libraries; site parsing and keyword matches do not verify performance or feature support. Not run by the offline path. |
| `analyzers/*` | Feature/gap and architecture proposals; not proof that features are implemented or that market adoption claims generalize. |
| `generate_trainer.py`, `*.b64`, old `test_*.py` | File-generation experiments and smoke scripts, not a trainer or meaningful validation suite. |

GitNexus impact was attempted for `TrainingDataGenerator` in `/code/Personal`.
The `.gitnexus/run.cjs` runner is absent; bootstrap also fails in this environment.
Caller/process risk remains unresolved. Existing functions were not edited;
new isolated files avoid changing their behavior. No commit was made.
