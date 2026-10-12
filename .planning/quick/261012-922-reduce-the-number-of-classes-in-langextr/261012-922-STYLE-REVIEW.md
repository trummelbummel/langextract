# Style review — 261012-922

**Mode:** quick
**Timestamp:** 2026-10-12
**Commits:** f828ce4..7d0386a (+ style follow-up)
**Files:** `langextract/evaluation/__init__.py` (deleted satellites out of scope)

## R15 — Swallowed exceptions

No `try`/`except` in scoped production code. HITL skipped.

## REFACTORED

| Rule | Change |
|------|--------|
| R25 | `span_iou(a, b)` → `span_iou(predicted, gold)`; `ca`/`cb`/`s1`/`e1` → descriptive names |

## FINDINGS

| File | Rule | Finding | Suggestion |
|------|------|---------|------------|
| `__init__.py` | R25 | `ClassScore.tp` / `fp` / `fn` are 2-char public field names | Keep — locked by tests and EVAL public surface; renaming would be a breaking API change |
| `__init__.py` | — | `_evaluate_documents` / `_resolve_criteria` / `_index_by_document_id` remain module-private | Acceptable per plan; optional follow-up to nest as `Evaluator` staticmethods |

## Summary

1 file reviewed, 1 refactored (R25), 0 R15 candidates, 2 report-only notes.
