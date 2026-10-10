# Requirements: LangExtract pipeline trace

**Defined:** 2026-10-10
**Core Value:** You can follow one `lx.extract()` call from the prompt through to an `AnnotatedDocument` and see which function owns each stage.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Run

- [ ] **RUN-01**: Developer can run `python scripts/trace_extract.py` against local Ollama `gemma3:4b` for one short document
- [ ] **RUN-02**: Script fails clearly if Ollama is down or `gemma3:4b` is missing, before printing a fake empty walkthrough
- [ ] **RUN-03**: Script uses one `lx.extract()` call and one model `infer` (no second inference, no cloud providers)

### Stages

- [x] **STG-01**: Walkthrough prints stable stage labels in order: prompt-template, chunk, prompt, model, parse, align, annotated-document
- [x] **STG-02**: Each stage names the owning function and repo-relative file
- [ ] **STG-03**: Each stage prints live data in and data out for that call (full payloads for the short input)
- [ ] **STG-04**: Model stage shows raw model text separate from parsed extractions
- [x] **STG-05**: Parse stage shows ungrounded extractions (`char_interval` / `alignment_status` still empty), including empty lists
- [ ] **STG-06**: Align stage shows spans, status, chunk offsets (even when 0), and source slice or `ungrounded`
- [ ] **STG-07**: Final stage prints the `AnnotatedDocument` returned by that `extract()` call
- [x] **STG-08**: Parse and align are printed as a before/after grounding pair for the same extractions
- [ ] **STG-09**: Empty parse is called out in words next to the raw model text; parse inputs include format/fence/wrapper flags

### Contract

- [x] **CTR-01**: Observation lives only in `scripts/trace_extract.py` — no library API changes and no reusable tracer
- [x] **CTR-02**: Script does not replace or modify `examples/ollama/demo_ollama.py`

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
| HTML visualization, JSONL save, progress bars, eval harness | Covered elsewhere; not a stage walkthrough |
| Multi-pass, batch APIs, `output_schema`, URL fetch | Not the default Ollama path for this milestone |
| Multi-chunk or full-document trace in v1 | Volume hides the stage contract; one chunk for v1 |
| Persisted trace store | Starts a tracer product |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RUN-01 | Phase 5 | Pending |
| RUN-02 | Phase 5 | Pending |
| RUN-03 | Phase 5 | Pending |
| STG-01 | Phase 1 | Complete |
| STG-02 | Phase 1 | Complete |
| STG-03 | Phase 4 | Pending |
| STG-04 | Phase 4 | Pending |
| STG-05 | Phase 2 | Complete |
| STG-06 | Phase 4 | Pending |
| STG-07 | Phase 6 | Pending |
| STG-08 | Phase 2 | Complete |
| STG-09 | Phase 4 | Pending |
| CTR-01 | Phase 1 | Complete |
| CTR-02 | Phase 1 | Complete |

**Coverage:**

- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-10*
*Last updated: 2026-10-10 after roadmap creation*
