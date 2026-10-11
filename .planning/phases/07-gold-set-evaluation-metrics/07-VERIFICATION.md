---
phase: 07-gold-set-evaluation-metrics
verified: 2026-10-11T18:51:56.819Z
status: passed
score: 11/11 must-haves verified
covered_files:
  - .planning/REQUIREMENTS.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-01-PLAN.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-01-SUMMARY.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-02-PLAN.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-02-SUMMARY.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-03-PLAN.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-03-SUMMARY.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-04-PLAN.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-04-SUMMARY.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-05-PLAN.md
  - .planning/phases/07-gold-set-evaluation-metrics/07-05-SUMMARY.md
  - README.md
  - docs/examples/evaluation_ci.md
  - langextract/__init__.py
  - langextract/evaluation/__init__.py
  - langextract/evaluation/criteria.py
  - langextract/evaluation/matching.py
  - langextract/evaluation/metrics.py
  - pyproject.toml
  - tests/evaluation_test.py
covered_digest: "v1:sha256:59e4dab0001950d08476ceb4bd390fcb7ce1c96356b5daba3029a88bb402f5ed"
behavior_unverified: 0
overrides_applied: 0
decision_coverage:
  skipped: true
  reason: "No *-CONTEXT.md in phase directory"
human_verification: []
---

# Phase 7: Gold-set evaluation metrics Verification Report

**Phase Goal:** As a library user, I want `evaluate(predicted, gold)` that scores extractions against a labeled gold set (class + span IoU, optional attributes/text, greedy one-to-one matching) and returns per-class and micro precision/recall/F1, so I can run a CI regression check without a custom eval harness.
**Verified:** 2026-10-11T18:51:56.819Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | `evaluate(predicted, gold, ...)` accepts sequences of `AnnotatedDocument`, pairs docs by `document_id`, and returns an `EvaluationReport` with per-class and micro-averaged precision, recall, and F1 | ✓ VERIFIED | `langextract/evaluation/__init__.py` `evaluate` → `_index_by_document_id` + `report_from_counts`; `EvaluateTracerTest` / `EvaluateE2ETest` pass (55/55 suite) |
| 2   | A prediction matches gold only when all configured criteria pass (same class + span IoU ≥ threshold; optional `match_attributes` / `text_eval_func`); unaligned preds (`char_interval is None`) count as FP via IoU 0.0 | ✓ VERIFIED | Default `SameClass`+`SpanIoU(0.5)`; flags append `AttributesEqual`/`TextMatch`; e2e rows `below_threshold`, `unaligned_pred`, `match_attributes_*`, `text_eval_func_*` pass |
| 3   | Matching is one-to-one greedy (score by IoU desc, deterministic tie-break); one prediction cannot match two gold items | ✓ VERIFIED | `matching.py` sort `(-score, pred_index, gold_index)` + used-sets; `GreedyMatchTest` (duplicates, crossing IoU, equal-IoU tie, deterministic) pass |
| 4   | Tests cover perfect match, overlap below/above threshold, class mismatch, duplicate predictions, empty inputs; metrics assert against hand-worked values | ✓ VERIFIED | `MetricsPrfTest`, `CriteriaSpanIoUTest`, `EvaluateE2ETest.test_hand_worked_micro` (parameterized RESEARCH matrix); suite 55 passed |
| 5   | README (or docs) includes a short CI regression example using `evaluate` | ✓ VERIFIED | `docs/examples/evaluation_ci.md` + README Gold-set evaluation link; snippet executed → `micro.f1 == 1.0` |
| 6   | Package layout: `criteria.py` / `matching.py` / `metrics.py` / `__init__.py` (`evaluate` + re-exports) | ✓ VERIFIED | All four modules exist, substantive, exported via `__all__` |
| 7   | Lazy `lx.evaluation.evaluate` works; no top-level `lx.evaluate` | ✓ VERIFIED | `_LAZY_MODULES["evaluation"]`; runtime `lx.evaluation.evaluate is evaluation_module.evaluate`; `hasattr(lx, "evaluate")` is False |
| 8   | No `Evaluation` ABC; `TextMatch` uses `Callable[[str, str], bool]` | ✓ VERIFIED | `MatchCriterion` Protocol only; `TextMatch.text_eval_func: Callable[[str, str], bool]`; no ABC/abstractmethod in package |
| 9   | Layering: evaluation imports `core.data` only (not annotation/providers); core never imports evaluation | ✓ VERIFIED | Import scan + `uv run lint-imports`: "Evaluation must not import high-level pipeline modules" KEPT; "Core must not import high-level modules" KEPT |
| 10  | `criteria=` mutually exclusive with non-default convenience kwargs (raises `ValueError`); document_id set mismatch / duplicate IDs raise | ✓ VERIFIED | `_resolve_criteria` XOR; `EvaluateConfigTest` pass |
| 11  | `prf_from_counts` / `EvaluationReport`: empty→0.0; micro from global TP/FP/FN (not mean of per-class F1) | ✓ VERIFIED | `metrics.py` + `MetricsPrfTest` / `MetricsReportTest.test_report_from_counts_micro_vs_per_class` |

**Score:** 11/11 truths verified (0 present, behavior-unverified)

### Decision Coverage

Skipped — no `*-CONTEXT.md` in the phase directory (`workflow.context_coverage_gate` default enabled; nothing to honor).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `langextract/evaluation/metrics.py` | ClassScore, EvaluationReport, prf_from_counts, report_from_counts | ✓ VERIFIED | Exists, substantive, imported by package |
| `langextract/evaluation/criteria.py` | MatchCriterion, span_iou, SameClass, SpanIoU, AttributesEqual, TextMatch | ✓ VERIFIED | Exists, substantive, used by matching + evaluate |
| `langextract/evaluation/matching.py` | greedy_match | ✓ VERIFIED | Exists, substantive, called from evaluate |
| `langextract/evaluation/__init__.py` | evaluate + re-exports | ✓ VERIFIED | Orchestrator + `__all__` |
| `langextract/__init__.py` | evaluation in `__all__` + `_LAZY_MODULES` | ✓ VERIFIED | PEP 562 lazy load |
| `pyproject.toml` | package + import-linter contracts | ✓ VERIFIED | `langextract.evaluation` packages + 2 contracts involving evaluation |
| `tests/evaluation_test.py` | Hand-worked unit + e2e suite | ✓ VERIFIED | 55 tests; tool `contains: def evaluate` false-positive (tests call evaluate, do not define it) |
| `docs/examples/evaluation_ci.md` | CI regression snippet | ✓ VERIFIED | In-memory pair, explicit `document_id`, exclusive `end_pos` |
| `README.md` | Gold-set evaluation link | ✓ VERIFIED | TOC + subsection → `evaluation_ci.md` |

### Key Link Verification

Automated `verify.key-links` reported false because plan `from:` values are symbols, not file paths. Manual wiring:

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `report_from_counts` | `EvaluationReport.micro` / `.per_class` | `prf_from_counts` per triple | ✓ WIRED | `metrics.py` |
| `SpanIoU.__call__` | `span_iou` | `>= threshold` | ✓ WIRED | `criteria.py` |
| `TextMatch` | injected `text_eval_func` | `__call__` | ✓ WIRED | `criteria.py` |
| `greedy_match` | criteria `all()` + `span_iou` score | filter → sort → used-set walk | ✓ WIRED | `matching.py` |
| `evaluate` | `greedy_match` → `report_from_counts` | per-doc counters | ✓ WIRED | `__init__.py` |
| `lx.evaluation` | `langextract.evaluation` | `_LAZY_MODULES` PEP 562 | ✓ WIRED | `langextract/__init__.py` |
| README More Examples | `docs/examples/evaluation_ci.md` | markdown link | ✓ WIRED | README Gold-set section |
| `evaluation_ci.md` | `lx.evaluation.evaluate` | public API in snippet | ✓ WIRED | snippet executed successfully |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `evaluate` | `predicted` / `gold` extractions | Caller-supplied `AnnotatedDocument` sequences | Yes — TP/FP/FN from greedy matches | ✓ FLOWING |
| `EvaluationReport.micro` | `(micro_tp, micro_fp, micro_fn)` | Aggregated match counters | Yes — `prf_from_counts` | ✓ FLOWING |
| Docs example | `report.micro.f1` | Same evaluate path on in-memory docs | Yes — assert 1.0 | ✓ FLOWING |

No static/hollow returns on the evaluation path.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full evaluation suite | `.venv/bin/pytest tests/evaluation_test.py -q` | 55 passed in 0.33s | ✓ PASS |
| Hand-worked e2e + IoU + lazy + prf subset | `.venv/bin/pytest tests/evaluation_test.py -k "hand_worked_micro or duplicate_preds_match or lazy_lx or below_threshold or prf_from_counts" -q` | 16 passed | ✓ PASS |
| Lazy export identity | `python -c "import langextract as lx; …"` | `lazy_ok`, no `lx.evaluate` | ✓ PASS |
| Docs CI snippet | Execute `evaluation_ci.md` body | `docs_snippet_ok` micro f1=1.0 | ✓ PASS |
| Import layering | `uv run --with import-linter lint-imports` | 4 contracts kept, 0 broken | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No phase-declared or conventional probes | N/A |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| EVAL-01 | 07-01, 07-04 | evaluate → per-class + micro P/R/F1 | ✓ SATISFIED | `evaluate` + `EvaluationReport` + tracer/e2e tests |
| EVAL-02 | 07-02, 07-04 | class + IoU threshold; optional attrs; unaligned FP | ✓ SATISFIED | criteria + e2e unaligned/attrs/text tests |
| EVAL-03 | 07-03, 07-04 | greedy 1:1 matching | ✓ SATISFIED | `greedy_match` + `GreedyMatchTest` |
| EVAL-04 | 07-01..05 | hand-worked tests + CI docs example | ✓ SATISFIED | 55 tests + `evaluation_ci.md` + README link |

No orphaned Phase 7 requirements — all EVAL-01..04 claimed by plans.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/evaluation_test.py` | EVAL-01..04 | 55 | 0 | 0 | Value (exact floats / hand-worked) | PASS |

**Disabled tests on requirements:** 0
**Circular patterns detected:** 0 (expected values are hand-worked RESEARCH floats, not captured from SUT)
**Insufficient assertions:** 0

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in evaluation package or `evaluation_test.py` | — | — |

Note: `class EvaluationReport` is a dataclass report type, not an Evaluation ABC.

### Prohibitions

| Statement | Evidence | Verdict |
| --------- | -------- | ------- |
| Must not add top-level `lx.evaluate` | `hasattr(lx, "evaluate")` False | ✓ held |
| Must not introduce Evaluation ABC | Protocol + callables only | ✓ held |
| Must not import annotation/providers from evaluation | import scan + lint-imports KEPT | ✓ held |
| Docs must not use `eval`/`exec` or live models | snippet is in-memory only | ✓ held |
| Docs assert shipped field `micro.f1` (not plan typo `f1_score`) | intentional per 07-05 SUMMARY | ✓ held (intent) |

### Human Verification Required

N/A — Library/API foundation phase with no user-facing UI. All acceptance criteria are verifiable programmatically (tests + import-linter + docs snippet execution). No ⚠️ PRESENT_BEHAVIOR_UNVERIFIED truths.

### Gaps Summary

None. Phase goal achieved: library users can call `lx.evaluation.evaluate(predicted, gold)` for CI regression scoring without a custom harness.

---

_Verified: 2026-10-11T18:51:56.819Z_
_Verifier: Claude (gsd-verifier)_

## VERIFICATION PASSED
