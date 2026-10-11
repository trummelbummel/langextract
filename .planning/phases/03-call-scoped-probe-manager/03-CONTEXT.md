# Phase 3: Call-scoped probe manager - Context

**Gathered:** 2026-10-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a call-scoped probe installer in `scripts/trace_extract.py` — `trace_probes()` — that wraps the five methods `extract` already calls, always restores class attributes in `finally` (including on exception and mid-install failure), and proves restore via an in-script self-check. No live `lx.extract()`, no Ollama, no stage payload capture (Phase 4), no library API changes.

</domain>

<decisions>
## Implementation Decisions

### Probe API shape
- **D-01:** Enter the probe scope with a context manager: `with trace_probes():`. — **Reversibility:** costly — later phases and the restore self-check assume this enter/exit shape.
- **D-02:** Name the context manager `trace_probes()`.
- **D-03:** Accept an optional `wrappers={...}` map so Phase 4 can inject recording wraps later.
- **D-04:** When `wrappers` is omitted, install identity passthroughs for all five locked targets.

### Phase-3 wrap bodies
- **D-05:** Default wraps are pure identity — call the original and return/yield unchanged; no counters, no breadcrumb prints.
- **D-06:** Generator targets (`ChunkIterator.__iter__`, `OllamaLanguageModel.infer`, `Resolver.align`) use transparent `yield` of each item; never `list()` the original.
- **D-07:** Do not use `functools.wraps` / metadata copying in Phase 3 — restore proof uses class-attribute identity only.
- **D-08:** A partial `wrappers` map fills missing targets with identity; always install all five.

### Prove restore
- **D-09:** After the catalog print, `main` runs an in-script self-check (no live Ollama/`extract`).
- **D-10:** Self-check covers the exception path: raise inside `with`, catch, assert all five originals restored.
- **D-11:** Self-check is silent on success; on failure print to stderr and `SystemExit(1)`.
- **D-12:** Inside `with`, prove install with `is not` against the saved originals for all five class attributes.

### Install failure / re-entry
- **D-13:** If install fails after wrapping some targets, restore already-installed wraps, then re-raise — never leave a partial monkeypatch.
- **D-14:** One-shot only — nested `with trace_probes():` is rejected.
- **D-15:** Detect “already active” with a module-level `_PROBES_ACTIVE` flag, set on enter and cleared in `finally`.
- **D-16:** Re-entry raises `RuntimeError` with a clear message (e.g. `trace_probes() already active`).

### Claude's Discretion
- Exact key type/shape of the `wrappers` map (callable values keyed by stage label vs method reference) — choose whatever Phase 4 can extend cleanly.
- Exact stderr wording for self-check failure.
- Whether normal-exit restore is covered only by the context manager’s `finally` (roadmap criterion #2) without a separate silent success demo — exception-path self-check is mandatory; normal exit follows from the same `finally`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & requirements
- `.planning/PROJECT.md` — script-only milestone; no library API changes
- `.planning/REQUIREMENTS.md` — CTR-01 / CTR-02 (observation stays in the script)
- `.planning/ROADMAP.md` — Phase 3 goal and success criteria (five targets + finally restore)
- `CLAUDE.md` — per-task diff budget (~150 non-test lines / ≤3 source files)

### Research (probe design)
- `.planning/research/ARCHITECTURE.md` — call-scoped class-attribute wraps; five targets; no wrapt; save/restore class attrs not bound methods
- `.planning/research/SUMMARY.md` — Phase 3 rationale; Pitfall 7 (monkeypatch leak / bound restore)
- `.planning/research/FEATURES.md` — stage ownership map for probe targets

### Prior phase context
- `.planning/phases/01-stage-catalog-contracts/01-CONTEXT.md` — catalog/header/`config.yaml` decisions this phase must not break
- `.planning/phases/02-extraction-snapshots/` — snapshot helpers already in the script (do not regress)

### Codebase
- `scripts/trace_extract.py` — sole implementation file for this phase
- `langextract/chunking.py` — `ChunkIterator.__iter__`
- `langextract/prompting.py` — `ContextAwarePromptBuilder.build_prompt`
- `langextract/providers/ollama.py` — `OllamaLanguageModel.infer`
- `langextract/resolver.py` — `Resolver.resolve`, `Resolver.align`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/trace_extract.py`: `load_config`, `STAGE_CATALOG`, `print_call_header`, `print_stage_catalog`, snapshot/grounding helpers from Phases 1–2 — grow probes in this same file.
- Existing test loader pattern in `tests/trace_extract_test.py` (`_load_script_module`) if Phase 3 adds tests later; Phase 3 demo is in-script per D-09.

### Established Patterns
- Call-scoped observer: save class attribute → assign wrap → `try`/`finally` restore (research ARCHITECTURE Pattern 1).
- No `wrapt`; stdlib only for the manager.
- Script may import the five stage classes to install probes; must not edit `langextract/`.

### Integration Points
- New symbols live in `scripts/trace_extract.py` only (`trace_probes`, `_PROBES_ACTIVE`, identity wraps, self-check helper).
- `main` grows: catalog print (unchanged stdout contract) then silent restore self-check.
- Phase 4 will pass real wrappers via `wrappers={...}`; Phase 3 ships identity defaults.

</code_context>

<specifics>
## Specific Ideas

- Five locked targets: `ChunkIterator.__iter__`, `ContextAwarePromptBuilder.build_prompt`, `OllamaLanguageModel.infer`, `Resolver.resolve`, `Resolver.align`
- Do not wrap `WordAligner.align_extractions` (prompt-validation hazard)
- Self-check flow: save originals → `with trace_probes():` assert `is not` → raise → catch → assert originals restored

</specifics>

<deferred>
## Deferred Ideas

- Recording / stage-payload wrappers — Phase 4
- Live `lx.extract()` under probes — Phase 5
- Nested / re-entrant probe stacks — out of MVP
- `functools.wraps` metadata on wraps — not needed for Phase 3 restore proof
- Separate normal-exit demo print line — deferred; `finally` covers normal exit

None — discussion stayed within phase scope for deferred product ideas.

</deferred>

---

*Phase: 3-Call-scoped probe manager*
*Context gathered: 2026-10-11*
