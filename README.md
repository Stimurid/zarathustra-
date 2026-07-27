# zarathustra — Калифорнийский Ид

Prototype of an eight-headed inner council under Tinkuy discipline.
See [CALIFORNIAN_ID/README.md](CALIFORNIAN_ID/README.md) for the working
package.

- **Status:** v0.4.0 candidate
- **Runtime:** Python 3.11+, mock-provider by default (works with no API keys)
- **Tests:** 66/66 passing (`cd CALIFORNIAN_ID && PYTHONPATH=src python -m pytest tests/ -q`)

## What lives here

```
/
├── CALIFORNIAN_ID/                            # the working package
├── CLAUDE_CODE_HANDOFF_CALIFORNIAN_ID.md      # Пик 1-3 spec
└── CLAUDE_CODE_CONTINUATION_CORPUS_DONORS_ZARATHUSTRA.md  # Пик 4 spec
```

## What is deliberately NOT in git

- **Extracted primary-source texts** (`CALIFORNIAN_ID/corpus/zarathustra/normalized/*.txt`)
  — Bakhtin, Jung, Deleuze/Guattari, Latour, Vakhshtein, Gurdjieff,
  Povarnin. These are derivatives of copyrighted books. `SOURCE_MANIFEST.yaml`
  keeps the full provenance skeleton so anyone with legal access to the
  sources can regenerate them.
- **Run traces** (`CALIFORNIAN_ID/runs/`) — regenerable per run.
- **Caches** (`__pycache__/`, `.pytest_cache/`).

## Quick start

```bash
cd CALIFORNIAN_ID
python -m pip install pyyaml pytest
PYTHONPATH=src python -m californian_id validate
PYTHONPATH=src python -m californian_id run --text "Стоит ли ускорять развитие AGI?"
PYTHONPATH=src python -m pytest tests/ -q
```

## Architecture at a glance

Eight heads on one shared **body** of thought:
- 7 ideological lenses (transhumanist, longtermist, effective-altruist,
  accelerationist, rationalist, libertarian, AI-safety).
- 8th head **Zarathustra**: scene-reader, head-caller, tension-regulator,
  question-transformer, chooser of one of **10 completion forms**
  (synthesis is only one of them and never the default).

Around the council:
- **Argumentation machine** (Povarnin + Toulmin + canon): thesis tracking,
  fallacy/trick detection, anti-slop gate.
- **Architectonic reconstruction**: typed delta after each turn.
- **Hybrid managed RAG** over 18 cultural scene/operation cards
  (Bakhtin, Jung, Deleuze/Guattari, Latour, Gurdjieff, Povarnin) + primary
  fragment index.

See [CALIFORNIAN_ID/_work/CORPUS_AND_DONOR_COMPLETION_REPORT.md](CALIFORNIAN_ID/_work/CORPUS_AND_DONOR_COMPLETION_REPORT.md)
for the honest coverage report.

## Contract discipline

- Personas are **lenses**, not impersonations of real people
  (`assignment_prohibited: true`, `forbidden_uses: [participant profiling,
  identity attribution, style imitation, authority claim]`).
- Group Soul Minority Retention Law enforced in every completion form —
  no false consensus, no silent minority erasure.
- Runtime is **host-neutral**. CLI adapter works; Telegram/Feynman
  adapters are contract-only until real access exists.

## License / provenance

Working code and derivatives are the author's work under project's chosen
license. Referenced primary sources (Bakhtin, Jung, Deleuze/Guattari,
Latour, Gurdjieff, Povarnin) remain the property of their authors and
publishers; only short quoted samples appear in cultural cards for
scholarly use, each with `quote_hash` and locator.
