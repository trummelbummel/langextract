# Requirements: LangExtract pipeline trace

**Defined:** 2026-10-10
**Core Value:** You can follow one `lx.extract()` call from the prompt through to an `AnnotatedDocument` and see which function owns each stage.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Run

- [x] **RUN-01**: Developer can run `python scripts/trace_extract.py` against local Ollama `gemma3:4b` for one short document
- [x] **RUN-02**: Script fails clearly if Ollama is down or `gemma3:4b` is missing, before printing a fake empty walkthrough
- [x] **RUN-03**: Script uses one `lx.extract()` call and one model `infer` (no second inference, no cloud providers)

### Stages

- [x] **STG-01**: Walkthrough prints stable stage labels in order: prompt-template, chunk, prompt, model, parse, align, annotated-document
- [x] **STG-02**: Each stage names the owning function and repo-relative file
- [x] **STG-03**: Each stage prints live data in and data out for that call (full payloads for the short input)
- [x] **STG-04**: Model stage shows raw model text separate from parsed extractions
- [x] **STG-05**: Parse stage shows ungrounded extractions (`char_interval` / `alignment_status` still empty), including empty lists
- [x] **STG-06**: Align stage shows spans, status, chunk offsets (even when 0), and source slice or `ungrounded`
- [ ] **STG-07**: Final stage prints the `AnnotatedDocument` returned by that `extract()` call
- [x] **STG-08**: Parse and align are printed as a before/after grounding pair for the same extractions
- [x] **STG-09**: Empty parse is called out in words next to the raw model text; parse inputs include format/fence/wrapper flags

### Contract

- [x] **CTR-01**: Observation lives only in `scripts/trace_extract.py` — no library API changes and no reusable tracer
- [x] **CTR-02**: Script does not replace or modify `examples/ollama/demo_ollama.py`

## Practice / library (Phase 7)

Independent of the v1.0 trace script. Practice Task 3 — gold-set evaluation.

### Evaluation

- [x] **EVAL-01**: `evaluate(predicted, gold, ...)` scores lists of `AnnotatedDocument` and returns per-class and micro-averaged precision, recall, and F1
- [x] **EVAL-02**: Match requires same `extraction_class` and span IoU ≥ configurable threshold (default 0.5); optional `match_attributes`; unaligned predictions (`char_interval is None`) count as false positives
- [x] **EVAL-03**: One-to-one greedy matching so one prediction cannot match two gold items
- [x] **EVAL-04**: Tests cover perfect match, below/above IoU threshold, class mismatch, duplicates, empty inputs (hand-worked metrics); docs show a short CI regression example

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Stages

- **STG-10**: Two-chunk input when someone is changing `ChunkIterator` or offset math
- **STG-11**: Prompt-validation line when an example fails alignment and later stages never ran
- **STG-12**: WordAligner parameter echo when alignment quality is the change under discussion

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Reusable tracer, callback manager, or OpenTelemetry exporter | Milestone is one printed call |
| Hooks or new parameters on `lx.extract` | Library changes wait until a specific change is named |
| Second pipeline / second `infer` beside `extract()` | Printed document must match the one call's stages |
| Cloud providers, model switch, or provider tour | Locked to local Ollama `gemma3:4b` |
| Replacing `examples/ollama/demo_ollama.py` | That demo is results/HTML; this script prints stages |
| `debug=True` as the walkthrough | Truncated unstructured logs; no function-and-file contract |
| HTML visualization, JSONL save, progress bars | Not a stage walkthrough; gold-set `evaluate` is Phase 7 |
| Multi-pass, batch APIs, `output_schema`, URL fetch | Not the default Ollama path for this milestone |
| Multi-chunk or full-document trace in v1 | Volume hides the stage contract; one chunk for v1 |
| Persisted trace store | Starts a tracer product |
| Evaluation ABC / LLM-as-judge / document-level evaluator | Premature until a second evaluator exists (Phase 7 uses Protocols + functions) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RUN-01 | Phase 5 | Complete |
| RUN-02 | Phase 5 | Complete |
| RUN-03 | Phase 5 | Complete |
| STG-01 | Phase 1 | Complete |
| STG-02 | Phase 1 | Complete |
| STG-03 | Phase 4 | Complete |
| STG-04 | Phase 4 | Complete |
| STG-05 | Phase 2 | Complete |
| STG-06 | Phase 4 | Complete |
| STG-07 | Phase 6 | Pending |
| STG-08 | Phase 2 | Complete |
| STG-09 | Phase 4 | Complete |
| CTR-01 | Phase 1 | Complete |
| CTR-02 | Phase 1 | Complete |
| EVAL-01 | Phase 7 | Complete |
| EVAL-02 | Phase 7 | Complete |
| EVAL-03 | Phase 7 | Complete |
| EVAL-04 | Phase 7 | Complete |

**Coverage:**

- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓
- EVAL (Phase 7): 4 total, mapped 4, unmapped 0 ✓

---
*Requirements defined: 2026-10-10*
*Last updated: 2026-10-11 — Phase 7 EVAL-01..04 added*
