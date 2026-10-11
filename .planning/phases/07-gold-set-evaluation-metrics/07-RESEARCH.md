# Phase 7: Gold-set evaluation metrics - Research

**Researched:** 2026-10-11
**Domain:** Library NER-style evaluation — span IoU matching, greedy 1:1 assignment, micro/per-class P/R/F1
**Confidence:** HIGH (core types, package seams, and overlap helpers verified in-repo; IoU/micro-avg formulas cross-checked against public NER eval practice)

<user_constraints>
## User Constraints (from ROADMAP Design constraints — no CONTEXT.md)

No phase `07-CONTEXT.md` (user continued without discuss-phase). Treat ROADMAP Phase 7 **Design constraints** as locked decisions.

### Locked Decisions
- Package layout: `langextract/evaluation/` with `criteria.py`, `matching.py`, `metrics.py`, `__init__.py` (`evaluate` + re-exports)
- Match rules are small callables behind a `MatchCriterion` Protocol (`SameClass`, `SpanIoU`, `AttributesEqual`, `TextMatch`); greedy score (`span_iou`) stays separate from yes/no criteria
- No `Evaluation` ABC until a second evaluator exists; `text_eval_func` injects via `TextMatch`, not a subclass hook
- Convenience flags vs full `criteria=` override: mutually exclusive (one way to configure)
- Layering: evaluation imports `core.data` only; core never imports evaluation
- Suggested plan split (≤150 non-test lines each): (1) metrics (2) criteria + span_iou (3) greedy_match (4) evaluate + doc pairing + docs example + e2e
- Requirements EVAL-01..04 and success criteria in ROADMAP Phase 7 (document pairing by `document_id`, IoU threshold default 0.5 per REQUIREMENTS, unaligned preds → FP via IoU 0.0, greedy 1:1, hand-worked tests, CI docs example)
- Diff budget (hard): ≤ ~150 changed non-test lines and ≤ 3 source files per task/commit; ≤ ~400 non-test lines per plan [CITED: CLAUDE.md, .claude/skills/diff-budget/SKILL.md]

### Claude's Discretion
- Exact `EvaluationReport` / per-class dataclass field names
- Zero-division convention when TP=FP=FN=0
- Deterministic tie-break key details beyond “IoU desc”

### Resolved (was discretion; locked by plans)
- Unpaired `document_id` sets → `ValueError` listing missing IDs (identical sets required)
- `extractions is None` → empty list
- Docs: `docs/examples/evaluation_ci.md` + README More Examples link (07-05)
- Lazy `lx.evaluation` only — no top-level `lx.evaluate`

### Deferred Ideas (OUT OF SCOPE)
- Practice Task 1/2/4/5 (drop_ungrounded already done separately; summarize/observers/fallback providers)
- Trace-script Phases 5–6 (independent; Phase 7 must not depend on them)
- Macro-averaged F1, Hungarian/optimal matching, token-level IoU, HTML viz of mismatches
- Single-file `langextract/evaluation.py` from the practice-task sketch (superseded by locked package layout)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | `evaluate(predicted, gold, ...)` scores lists of `AnnotatedDocument` and returns per-class and micro-averaged precision, recall, and F1 | `evaluate` in `evaluation/__init__.py`; `EvaluationReport` + `compute_prf` in `metrics.py`; pair by `document_id` |
| EVAL-02 | Match requires same `extraction_class` and span IoU ≥ configurable threshold (default 0.5); optional `match_attributes`; unaligned predictions (`char_interval is None`) count as false positives | `SameClass` + `SpanIoU(threshold)`; optional `AttributesEqual`; `span_iou` returns 0.0 when interval missing/invalid |
| EVAL-03 | One-to-one greedy matching so one prediction cannot match two gold items | `greedy_match` in `matching.py`: sort by IoU desc + deterministic indices; mark used preds/golds |
| EVAL-04 | Tests cover perfect / below-above IoU / class mismatch / duplicates / empty; hand-worked metrics; docs CI example | absltest + `parameterized` like `tests/data_lib_test.py`; freeze hand-worked table below; README or `docs/examples/` snippet |
</phase_requirements>

## Summary

Phase 7 adds a **pure library** evaluation package with no new third-party dependencies. Inputs are sequences of `AnnotatedDocument` from `langextract.core.data`. Matching is entity-level: criteria decide yes/no; `span_iou` supplies the greedy ranking score. Metrics aggregate TP/FP/FN per `extraction_class` and micro-average globally. There is **no existing evaluation module** and **no reusable public IoU helper** — `annotation._extractions_overlap` is private, boolean-only, and lives outside the allowed import layer, so `span_iou` must be implemented inside `evaluation/`.

Packaging is the main non-algorithm seam: `pyproject.toml` lists setuptools packages explicitly (must add `langextract.evaluation`), and the top-level `langextract/__init__.py` uses PEP 562 lazy modules (must register `evaluation`). Tests for library modules are **absltest + parameterized**; pytest runs them via `make test`.

**Primary recommendation:** Implement the four-module split exactly as locked; freeze the hand-worked metric table into acceptance tests; register the package in setuptools + lazy export; document a short CI assert on `report.micro.f1`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Span IoU + match criteria | Library (`langextract/evaluation/criteria.py`) | — | Pure functions over `Extraction` / `CharInterval` |
| Greedy 1:1 assignment | Library (`matching.py`) | — | Consumes scores + criteria; no I/O |
| P/R/F1 aggregation | Library (`metrics.py`) | — | TP/FP/FN → floats; no matching logic |
| Doc pairing + public `evaluate` | Library (`evaluation/__init__.py`) | — | Orchestrates match → metrics; re-exports |
| Core data types | Library (`langextract/core/data.py`) | Compat shim `langextract/data.py` | Evaluation imports **core.data only** |
| CI regression example | Docs (README or `docs/examples/`) | User CI | EVAL-04; no runtime dependency |
| Trace script / Ollama | — | Out of scope | Phase 7 independent of Phases 5–6 |

## Project Constraints (from CLAUDE.md)

- **Diff budget:** ≤ ~150 non-test lines and ≤ 3 source files per task/commit; ≤ ~400 non-test lines per plan; split rather than compress; no drive-by refactors/reformats.
- **Tests:** Prefer fixtures (`setUp` / `parameterized` for absltest); one behavior per test; name `test_<behavior>_<condition>`; assert specific values; no network/LLM in unit tests; run `make test` before commit.
- **Style:** Follow file being edited (absltest for new library tests matching peers).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `requires-python = ">=3.10"` | Runtime | [VERIFIED: `pyproject.toml:25` — quote: `requires-python = ">=3.10"`] |
| `langextract.core.data` | local 1.7.1 | `Extraction`, `AnnotatedDocument`, `CharInterval` | [VERIFIED: `langextract/core/data.py:50-257`] Only allowed evaluation dependency |
| stdlib `dataclasses`, `typing.Protocol` | stdlib | Report types + `MatchCriterion` | [CITED: docs.python.org/3/library/typing.html#typing.Protocol] Repo already uses `from typing import Protocol` in providers |
| stdlib only for eval math | — | IoU / greedy / P/R/F1 | No sklearn/seqeval — keep zero deps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| absl-py (`absltest`, `parameterized`) | project dep | Unit tests | Match `tests/data_lib_test.py`, `tests/extract_drop_ungrounded_test.py` |
| pytest | via `[test]` extra | Runner | `make test` → `pytest tests -m "not live_api and not integration"` [VERIFIED: `Makefile:13-15`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled IoU + greedy | `seqeval` / spaCy scorers | Extra dep; token/BIO oriented; violates zero-dep library ethos |
| Optimal (Hungarian) matching | Greedy (locked) | Optimal is fairer but heavier and not in requirements |
| Single `evaluation.py` | Package (locked) | Practice-task sketch; ROADMAP package wins |

**Installation:** none — no new packages.

**Version verification:** N/A for new packages. Existing project version `1.7.1` [VERIFIED: `pyproject.toml:22`].

## Package Legitimacy Audit

> No external packages are installed for this phase.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | No new packages |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
predicted: Sequence[AnnotatedDocument]     gold: Sequence[AnnotatedDocument]
              │                                         │
              └──────────────► evaluate() ◄─────────────┘
                              │
                    pair by document_id
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     per-doc Extraction lists      (missing ID → error or FP/FN)*
              │
              ▼
     greedy_match(preds, golds, criteria, score=span_iou)
              │  candidates pass ALL MatchCriterion
              │  sort by (iou desc, pred_idx, gold_idx)
              │  assign 1:1
              ▼
     TP / FP / FN counters (per extraction_class + micro)
              │
              ▼
     EvaluationReport { per_class, micro: {precision, recall, f1, ...} }
```

\* Document-ID mismatch policy: RESOLVED — require identical ID sets; raise ValueError listing missing IDs (see Open Questions).

### Recommended Project Structure
```
langextract/evaluation/
├── __init__.py      # evaluate(), re-exports, default criteria wiring
├── criteria.py      # MatchCriterion, SameClass, SpanIoU, AttributesEqual, TextMatch, span_iou
├── matching.py      # greedy_match(...)
└── metrics.py       # ClassScore / EvaluationReport, prf_from_counts

tests/
└── evaluation_test.py   # absltest + parameterized; hand-worked values

# packaging seams (same commits as exports land):
langextract/__init__.py  # _LAZY_MODULES + __all__
pyproject.toml           # setuptools packages + optional import-linter contract
```

### Pattern 1: MatchCriterion Protocol (yes/no) vs score (float)
**What:** Criteria answer “may these two extractions match?”; `span_iou` ranks candidates for greedy assignment.
**When to use:** Always — locked separation prevents IoU threshold from being double-counted as both score and sole criterion incorrectly.
**Example:**
```python
# Source: typing docs Protocol + __call__; field names from core/data.py
from typing import Protocol
from langextract.core import data

class MatchCriterion(Protocol):
  def __call__(
      self, predicted: data.Extraction, gold: data.Extraction
  ) -> bool: ...
```

### Pattern 2: Convenience flags XOR `criteria=`
**What:** Default path builds `[SameClass(), SpanIoU(iou_threshold)]` (+ optional `AttributesEqual`, `TextMatch(text_eval_func)`). If `criteria=` is passed, convenience kwargs must be left at defaults or raise `ValueError`.
**When to use:** Public `evaluate(...)` only.

### Pattern 3: Lazy public export
**What:** Register `"evaluation": "langextract.evaluation"` in `_LAZY_MODULES` and `__all__` so `import langextract as lx; lx.evaluation.evaluate(...)` works like `lx.data`.
**When to use:** Plan 4 export task. Prefer this over a new top-level `lx.evaluate` wrapper unless docs want parity with `lx.extract` (discretion).

### Anti-Patterns to Avoid
- **Importing `annotation._extractions_overlap`:** Wrong layer; boolean only; not IoU.
- **`Evaluation` ABC / inheritance hooks:** Locked out; use `TextMatch(func)`.
- **Matching across documents:** Pair docs first; never pool all extractions globally.
- **Using inclusive-end IoU (`+1`):** `CharInterval.end_pos` is exclusive [VERIFIED below].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structural match API | Custom ABC metaclass | `typing.Protocol` + `__call__` | Stdlib structural typing; matches locked design |
| Test case matrices | Copy-paste tests | `parameterized.named_parameters` | Project convention |
| Package discovery | Rely on `find_packages` | Explicit `pyproject.toml` packages list | Setuptools list is explicit today — omit → install misses package |
| Layering enforcement | Hope | import-linter contract | Existing contracts for core; add evaluation |

**Key insight:** The algorithm is small; packaging + `document_id` / `None` interval edge cases are where plans usually break.

## Common Pitfalls

### Pitfall 1: Auto-generated `document_id`
**What goes wrong:** Fixtures omit `document_id`; accessing `.document_id` assigns `doc_` + random hex, so predicted and gold never pair.
**Why it happens:** Property generates IDs lazily [VERIFIED: `langextract/core/data.py:237-242`].
**How to avoid:** Always pass explicit `document_id=` in tests and docs examples; never rely on unset IDs for pairing.
**Warning signs:** Perfect-looking extractions score 0; different IDs each run.

### Pitfall 2: `char_interval is None` vs partial `CharInterval`
**What goes wrong:** Treating only `None` as unaligned while `CharInterval(start_pos=None, end_pos=None)` crashes or yields wrong IoU.
**Why it happens:** Both `Extraction.char_interval` and `CharInterval.start_pos`/`end_pos` are optional [VERIFIED: `langextract/core/data.py:50-60,87`].
**How to avoid:** `span_iou` returns `0.0` if either side lacks a complete finite `[start, end)` with `end >= start` (mirror overlap helper’s None checks at `annotation.py:99-112`, but reimplement IoU in evaluation).
**Warning signs:** TypeError on subtraction; NaN F1.

### Pitfall 3: Half-open interval arithmetic
**What goes wrong:** Using inclusive formulas (`+1`) inflates IoU vs exclusive `end_pos`.
**Why it happens:** Some NER papers use inclusive token indices.
**How to avoid:** `inter = max(0, min(e1,e2) - max(s1,s2))`; `union = (e1-s1)+(e2-s2)-inter`; if `union == 0` or `inter == 0` → `0.0`.
**Warning signs:** Hand-worked 0.8 case becomes ≠ 0.8.

### Pitfall 4: Greedy without stable tie-break
**What goes wrong:** Equal IoU pairs match nondeterministically → flaky tests.
**Why it happens:** Sort by IoU only.
**How to avoid:** Sort key `(-iou, pred_index, gold_index)`; document it.
**Warning signs:** Tests pass alone, fail under shuffled inputs.

### Pitfall 5: Micro vs macro confusion
**What goes wrong:** Averaging per-class F1 and calling it micro.
**Why it happens:** Naming mix-up.
**How to avoid:** Micro = global TP/FP/FN then one P/R/F1; per-class = same formulas on class counters. Zero denom → `0.0` for P, R, and F1 (recommended; freeze in tests).
**Warning signs:** Duplicate-pred case F1 ≠ `2/3`.

### Pitfall 6: Forgetting setuptools / lazy export
**What goes wrong:** Editable install or `import langextract.evaluation` fails in CI.
**Why it happens:** Explicit package list [VERIFIED: `pyproject.toml:82-88`].
**How to avoid:** Add `"langextract.evaluation"` in the same commit that introduces the package; update `_LAZY_MODULES`.
**Warning signs:** `ModuleNotFoundError` after `pip install -e .`

### Pitfall 7: Convenience flags + `criteria=` both set
**What goes wrong:** Silent precedence bugs.
**Why it happens:** Dual configuration paths.
**How to avoid:** Mutual exclusion `ValueError` with a clear message (locked).
**Warning signs:** Threshold flag ignored when custom criteria passed.

### Pitfall 8: Counting unmatched gold under wrong class
**What goes wrong:** FN attributed to prediction class or dropped.
**How to avoid:** TP/FP use predicted class of the extraction; FN use gold class. Micro sums all counters.

## Code Examples

### Core field names (verbatim)
```python
# Source: langextract/core/data.py:50-60,85-92,205-235
# CharInterval: start_pos: int | None = None; end_pos: int | None = None
# Extraction: extraction_class: str; extraction_text: str
#   char_interval: CharInterval | None = None
#   attributes: dict[str, str | list[str]] | None = None
# AnnotatedDocument(..., document_id=..., extractions=..., text=...)
```

### span_iou (half-open)
```python
# Source: derived from CharInterval semantics (exclusive end_pos) + NER IoU practice
def span_iou(a: data.Extraction, b: data.Extraction) -> float:
  ca, cb = a.char_interval, b.char_interval
  if ca is None or cb is None:
    return 0.0
  s1, e1, s2, e2 = ca.start_pos, ca.end_pos, cb.start_pos, cb.end_pos
  if None in (s1, e1, s2, e2):
    return 0.0
  inter = max(0, min(e1, e2) - max(s1, s2))
  if inter == 0:
    return 0.0
  union = (e1 - s1) + (e2 - s2) - inter
  return inter / union if union else 0.0
```

### Protocol callable (official typing pattern)
```python
# Source: https://docs.python.org/3/library/typing.html (Combiner Protocol)
from typing import Protocol

class Combiner(Protocol):
  def __call__(self, *vals: bytes, maxlen: int | None = None) -> list[bytes]: ...
```

### Greedy match sketch
```python
# Source: ROADMAP locked algorithm + EDS-NLP/seqeval-style 1:1 micro counting
# 1) Build candidates where all(c(pred, gold) for c in criteria)
# 2) Attach score = span_iou(pred, gold)
# 3) Sort by (-score, pred_i, gold_j)
# 4) Walk; skip if pred_i or gold_j already used; else match
```

### PRF helper
```python
def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
  precision = tp / (tp + fp) if (tp + fp) else 0.0
  recall = tp / (tp + fn) if (tp + fn) else 0.0
  f1 = (
      2 * precision * recall / (precision + recall)
      if (precision + recall)
      else 0.0
  )
  return precision, recall, f1
```

## Hand-worked acceptance cases (freeze in tests)

Assume default criteria: `SameClass` + `SpanIoU(0.5)`; single doc `document_id="d1"` unless noted. Intervals half-open.

| Case | Gold | Predicted | Expected micro (P, R, F1) | Notes |
|------|------|-----------|---------------------------|-------|
| Perfect | A `[0,5)` | A `[0,5)` | (1.0, 1.0, 1.0) | IoU=1.0 |
| Below threshold | A `[0,10)` | A `[8,18)` | (0.0, 0.0, 0.0) | IoU=2/18≈0.111 |
| Above threshold | A `[0,10)` | A `[2,10)` | (1.0, 1.0, 1.0) | IoU=0.8 |
| Class mismatch | A `[0,5)` | B `[0,5)` | (0.0, 0.0, 0.0) | Same span, SameClass fails → FP+FN |
| Duplicate preds | A `[0,5)` | A `[0,5)`, A `[0,5)` | (0.5, 1.0, 2/3) | Second pred FP |
| Empty both | `[]` | `[]` | (0.0, 0.0, 0.0) | Recommended zero-division policy |
| Unaligned pred | A `[0,5)` | A `char_interval=None` | (0.0, 0.0, 0.0) | IoU 0.0 → FP+FN |
| Micro vs per-class | A `[0,5)`; B `[10,15)` | A `[0,5)`; B `[20,25)` | micro (0.5, 0.5, 0.5); A all 1.0; B all 0.0 | One TP, one FP, one FN |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Exact span + type only (CoNLL) | IoU-threshold soft boundary match | Common in span-IE / Presidio-style eval | Tolerates off-by-few char errors |
| Optimal bipartite matching | Greedy by IoU (locked) | — | Simpler, deterministic with tie-break |
| Practice-task single module | Package with Protocol criteria | ROADMAP discuss lock | Fits diff budget + extensibility |

**Deprecated/outdated:**
- Treating evaluation as part of the trace script — Phase 7 is a library feature.

## Suggested plan sizing (diff budget)

| Plan | Deliverable | Est. non-test lines | Source files (≤3) |
|------|-------------|---------------------|-------------------|
| 07-01 | `metrics.py` + unit tests for `prf` / report | ~40–70 | `metrics.py`, maybe `__init__.py` stub |
| 07-02 | `criteria.py` (`span_iou` + criteria) + unit tests | ~80–120 | `criteria.py` |
| 07-03 | `matching.py` greedy + unit tests | ~50–90 | `matching.py` |
| 07-04 | `evaluate`, pairing, setuptools + lazy export, README/docs example, e2e tests | ~100–150 | `__init__.py`, `pyproject.toml` and/or `langextract/__init__.py`, README — **split task if >150** |

If plan 04 exceeds budget: Task A = `evaluate` + pairing + packaging; Task B = docs example + e2e only.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Empty both sides → P=R=F1=0.0 | Hand-worked / Pitfall 5 | CI example expectations flip; need user confirm |
| A2 | Mismatched document_id sets should raise `ValueError` | Open Questions (RESOLVED) | Alternate FP/FN-for-unpaired changes EVAL-01 pairing semantics |
| A3 | Default `iou_threshold=0.5` on `evaluate` / `SpanIoU` | EVAL-02 | REQUIREMENTS says 0.5; confirm kwarg name `iou_threshold` |
| A4 | No top-level `lx.evaluate` in v1 — lazy submodule only | Exports (RESOLVED) | Docs ergonomics only |
| A5 | `AttributesEqual` uses `==` on `attributes` dicts (including `None`) | Criteria | Nested list order sensitivity |

## Open Questions (RESOLVED)

1. **Unpaired `document_id`s** — RESOLVED: require identical predicted/gold ID sets; raise `ValueError` listing IDs missing from either side (adopted in 07-04; RESEARCH A2).
   - What we know: ROADMAP requires pairing by `document_id`; annotation raises on duplicate IDs within a stream.
   - Adopted answer: identical sets required; unpaired IDs are errors, not FP/FN.

2. **`extractions is None`** — RESOLVED: treat as empty list (`doc.extractions or []`) when pairing and matching (adopted in 07-04).
   - What we know: field type is `list[Extraction] | None` [VERIFIED: `langextract/core/data.py:217`].

3. **Docs location** — RESOLVED: `docs/examples/evaluation_ci.md` plus a README More Examples link (plan 07-05).
   - What we know: README has Quick Start + More Examples; `docs/examples/` holds longer guides.

Also locked (exports): no top-level `lx.evaluate`; lazy `lx.evaluation` only (A4 / 07-04).

## Environment Availability

Step 2.6: SKIPPED for external services — phase is code/config/docs only.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python ≥3.10 | library | ✓ | 3.14.2 (host); project requires ≥3.10 | — |
| pytest / absl-py | tests | ✓ (via project extras) | project-managed | — |
| Network / Ollama | — | N/A | — | Not used |

**Missing dependencies with no fallback:** none

## Security Domain

> `workflow.security_enforcement` enabled (ASVS level 1).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Offline scoring; no auth |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Validate sequences/types; reject convenience+`criteria=` conflict; safe handling of `None` intervals/IDs |
| V6 Cryptography | no | — |

### Known Threat Patterns for evaluation APIs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pathological huge extraction lists | Denial of service | Document O(n·m) pairing cost; no unbounded recursion |
| Injection via docs example | Tampering | Docs show local in-memory `AnnotatedDocument`s only — no `eval()` of strings |
| Layering bypass importing annotation internals | Elevation of privilege (design) | Import only `core.data`; import-linter contract |

## Validation Architecture

> Skipped — `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`.

Planner should still include TDD per `workflow.tdd_mode: true`: RED tests with hand-worked values before GREEN implementation for each plan.

## Sources

### Primary (HIGH confidence)
- `langextract/core/data.py` — `CharInterval`, `Extraction`, `AnnotatedDocument` field definitions (Read this session)
- `langextract/__init__.py` — `_LAZY_MODULES` / PEP 562 export pattern (Read this session)
- `pyproject.toml` — setuptools packages list, import-linter, requires-python (Read this session)
- `langextract/annotation.py:87-115` — private overlap helper (None handling reference only)
- `tests/data_lib_test.py`, `tests/extract_drop_ungrounded_test.py` — absltest + parameterized style
- ROADMAP.md Phase 7 Design constraints; REQUIREMENTS.md EVAL-01..04
- https://docs.python.org/3/library/typing.html — `Protocol` + `__call__` pattern [CITED]

### Secondary (MEDIUM confidence)
- NER span IoU as \|A∩B\|/\|A∪B\| with thresholded match — Presidio-research Span.iou, Tagaroo boundary IoU writeup [CITED: websearch]
- Micro P/R/F1 from global TP/FP/FN — EDS-NLP NER metrics / seqeval-style practice [CITED: websearch]

### Tertiary (LOW confidence)
- Context7 unavailable this session (`ctx7` CLI missing); Protocol guidance from official Python docs fetch instead

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib + existing core.data; no new packages
- Architecture: HIGH — locked module split maps cleanly onto verified types and package seams
- Pitfalls: HIGH — `document_id` auto-gen and exclusive-end IoU verified in source

**Research date:** 2026-10-11
**Valid until:** 2026-11-10 (stable library-internal design; re-check if `core.data` shapes change)
