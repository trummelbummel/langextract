# Phase 7: Gold-set evaluation metrics - Pattern Map

**Mapped:** 2026-10-11
**Files analyzed:** 8
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `langextract/evaluation/metrics.py` | model / utility | transform | `langextract/prompt_validation.py` (`ValidationReport` / frozen issue dataclasses) | exact |
| `langextract/evaluation/criteria.py` | utility | transform | `langextract/annotation.py` (`_extractions_overlap` None/interval guards) + `langextract/providers/gemini_batch.py` (`Protocol`) | role-match |
| `langextract/evaluation/matching.py` | utility | batch / transform | `langextract/visualization.py` (span filter + deterministic sort) + `annotation._merge_non_overlapping_extractions` | role-match |
| `langextract/evaluation/__init__.py` | service | request-response | `langextract/prompt_validation.py` (`validate_prompt_alignment` + `__all__`) | exact |
| `tests/evaluation_test.py` | test | request-response | `tests/prompt_validation_test.py` + `tests/extract_drop_ungrounded_test.py` | exact |
| `langextract/__init__.py` | config / export | request-response | `langextract/__init__.py` (`_LAZY_MODULES` / PEP 562) | exact |
| `pyproject.toml` | config | — | `pyproject.toml` (`packages` + import-linter contracts) | exact |
| `README.md` and/or `docs/examples/evaluation_ci.md` | config / docs | — | `README.md` More Examples + `docs/examples/output_schema.md` | exact |

## Pattern Assignments

### `langextract/evaluation/metrics.py` (model / utility, transform)

**Analog:** `langextract/prompt_validation.py` (report dataclasses); secondary `langextract/core/types.py` (`ScoredOutput` frozen float fields)

**Imports pattern** (prompt_validation lines 17–28):
```python
from __future__ import annotations

from collections.abc import Sequence
import dataclasses

from langextract.core import data
```

**Core report pattern** (prompt_validation lines 63–104) — copy frozen/mutable dataclass style for `ClassScore` / `EvaluationReport`:
```python
@dataclasses.dataclass(frozen=True)
class ValidationIssue:
  example_index: int
  extraction_class: str
  # ...

@dataclasses.dataclass
class ValidationReport:
  issues: list[ValidationIssue]

  @property
  def has_failed(self) -> bool:
    return any(i.issue_kind is IssueKind.FAILED for i in self.issues)
```

**Frozen score container** (core/types.py lines 69–74) — for per-class / micro P/R/F1 floats:
```python
@dataclasses.dataclass(frozen=True)
class ScoredOutput:
  score: float | None = None
  output: str | None = None
```

**Error / zero-division:** no exception for empty counts — return `0.0` (freeze in tests per RESEARCH). Pure functions; no logging required.

**Public surface:** export helpers via module `__all__` like prompt_validation lines 30–39 (`ValidationReport`, public functions).

---

### `langextract/evaluation/criteria.py` (utility, transform)

**Analog:** `langextract/annotation.py` lines 87–115 (`_extractions_overlap`) for interval None guards; `langextract/providers/gemini_batch.py` lines 38 + 580–583 for `Protocol`; `langextract/visualization.py` lines 250–257 for invalid-interval skip shape.

**Imports pattern:**
```python
from __future__ import annotations

from typing import Protocol

from langextract.core import data
```

**Protocol pattern** (gemini_batch.py lines 580–583) — structural typing; evaluation uses `__call__` per ROADMAP (stdlib Protocol docs), not attribute-only:
```python
class _TextResponse(Protocol):
  """Protocol for inline response objects with text attribute."""

  text: str
```

Adapt to locked `MatchCriterion`:
```python
class MatchCriterion(Protocol):
  def __call__(
      self, predicted: data.Extraction, gold: data.Extraction
  ) -> bool: ...
```

**Core interval-guard pattern** (annotation.py lines 99–112) — reimplement as IoU inside evaluation; do **not** import `_extractions_overlap`:
```python
  if extraction1.char_interval is None or extraction2.char_interval is None:
    return False

  start1, end1 = (
      extraction1.char_interval.start_pos,
      extraction1.char_interval.end_pos,
  )
  start2, end2 = (
      extraction2.char_interval.start_pos,
      extraction2.char_interval.end_pos,
  )

  if start1 is None or end1 is None or start2 is None or end2 is None:
    return False
```
(For `span_iou`: same guards → return `0.0`; half-open `end_pos` exclusive per `CharInterval` docstring in `core/data.py` lines 50–57.)

**Invalid span filter** (visualization.py lines 250–257) — same completeness check for criteria scoring:
```python
    if (
        not extraction.char_interval
        or extraction.char_interval.start_pos is None
        or extraction.char_interval.end_pos is None
        or extraction.char_interval.start_pos
        >= extraction.char_interval.end_pos
    ):
      continue
```

**Callable criteria:** small `@dataclasses.dataclass(frozen=True)` classes with `__call__` (same frozen-config style as `AlignmentPolicy` in prompt_validation.py lines 111–121).

**Layering:** `from langextract.core import data` only — never `langextract.annotation` or `langextract.data` shim from evaluation package.

---

### `langextract/evaluation/matching.py` (utility, batch / transform)

**Analog:** No greedy 1:1 NER matcher exists. Closest: deterministic sort of span candidates in `langextract/visualization.py`; non-overlapping merge walk in `langextract/annotation.py` (`_merge_non_overlapping_extractions`).

**Core sort / filter pattern** (visualization.py ~247–257, 439) — filter invalid intervals, then stable sort before assignment:
```python
  sorted_extractions = sorted(extractions, key=_extraction_sort_key)
```

For greedy match, build candidate triples `(score, pred_i, gold_j)` then:
```python
candidates.sort(key=lambda t: (-t[0], t[1], t[2]))  # IoU desc, then indices
```

**Used-set walk** (annotation merge spirit, lines 75–82) — skip already-taken items:
```python
        for existing_extraction in merged_extractions:
          if existing_extraction.char_interval is not None:
            if _extractions_overlap(extraction, existing_extraction):
              overlaps = True
              break
      if not overlaps:
        merged_extractions.append(extraction)
```
Adapt to boolean `used_pred` / `used_gold` sets instead of overlap.

**Error handling:** pure function; no I/O. Document O(n·m) cost in docstring only.

---

### `langextract/evaluation/__init__.py` (service, request-response)

**Analog:** `langextract/prompt_validation.py` — package-level public function returning a report dataclass + `__all__` re-exports. Secondary: `langextract/extraction.py` for kwarg validation / `ValueError` messaging; `langextract/core/__init__.py` for thin package `__all__`.

**Imports / `__all__` pattern** (prompt_validation lines 17–39):
```python
from __future__ import annotations

from collections.abc import Sequence
import dataclasses

from langextract.core import data

__all__ = [
    "IssueKind",
    "ValidationReport",
    "validate_prompt_alignment",
    # ...
]
```

**Public orchestrator** (prompt_validation lines 130–149) — `evaluate` should take sequences, early-return empty, return report type:
```python
def validate_prompt_alignment(
    examples: Sequence[data.ExampleData],
    aligner: resolver.WordAligner | None = None,
    policy: AlignmentPolicy | None = None,
    tokenizer: tokenizer_lib.Tokenizer | None = None,
) -> ValidationReport:
  if not examples:
    return ValidationReport(issues=[])
```

**Mutual-exclusion / config ValueError** (extraction.py lines 231–236; factory.py lines 142–143):
```python
  if not examples and not schema_active:
    raise ValueError(
        "Examples are required for reliable extraction. Please provide at least"
        " one ExampleData object with sample extractions, or provide"
        " output_schema."
    )
```
```python
  if not config.model_id and not config.provider:
    raise ValueError("Either model_id or provider must be specified")
```
Apply same style when convenience flags and `criteria=` are both set (locked XOR).

**document_id pairing:** follow annotation duplicate-ID raise style (annotation.py lines 318–320) — `raise ...InvalidDocumentError` / prefer plain `ValueError` listing missing IDs for eval (RESEARCH recommendation). Always require explicit `document_id=` in fixtures (auto-gen pitfall: core/data.py lines 237–242).

**Core types to construct in tests/docs** (core/data.py lines 50–60, 85–92, 205–235):
```python
@dataclasses.dataclass
class CharInterval:
  start_pos: int | None = None
  end_pos: int | None = None  # exclusive

# Extraction: extraction_class, extraction_text, char_interval, attributes
# AnnotatedDocument(..., document_id=..., extractions=..., text=...)
```

Treat `extractions is None` as `[]` (same as extraction.py `_drop_ungrounded`: `doc.extractions or []`).

---

### `tests/evaluation_test.py` (test, request-response)

**Analog:** `tests/prompt_validation_test.py` (parameterized hand-worked expectations); fixture builders from `tests/extract_drop_ungrounded_test.py`; explicit `document_id` + `CharInterval` from `tests/data_lib_test.py`.

**Imports / class pattern** (prompt_validation_test.py lines 19–27):
```python
from absl.testing import absltest
from absl.testing import parameterized

from langextract.core import data

class PromptAlignmentValidationTest(parameterized.TestCase):
```

**Fixture helpers** (extract_drop_ungrounded_test.py lines 26–41) — explicit `document_id`, mixed None intervals:
```python
def _mixed_document() -> data.AnnotatedDocument:
  grounded = data.Extraction(
      extraction_class="entity",
      extraction_text="Romeo",
      char_interval=data.CharInterval(start_pos=0, end_pos=5),
  )
  ungrounded = data.Extraction(
      extraction_class="entity",
      extraction_text="ghost",
      char_interval=None,
  )
  return data.AnnotatedDocument(
      document_id="doc-1",
      text="Romeo spoke",
      extractions=[grounded, ungrounded],
  )
```

**Parameterized table** (prompt_validation_test.py lines 29–70; data_lib_test.py lines 36–47) — one `named_parameters` row per RESEARCH hand-worked case (perfect / below-above IoU / class mismatch / duplicates / empty / unaligned / micro vs per-class):
```python
  @parameterized.named_parameters(
      dict(
          testcase_name="exact_alignment",
          # inputs...
          expected_issues=0,
      ),
  )
  def test_alignment_detection(self, ...):
```

**Assertions:** specific floats (`assertEqual` / `assertAlmostEqual` for `2/3`); `assertRaisesRegex` for XOR / mismatched ID sets. No network / LLM mocks needed.

---

### `langextract/__init__.py` (config / export)

**Analog:** same file — PEP 562 lazy submodule registration.

**Pattern** (lines 30–48, 64–84, 87–98):
```python
__all__ = [
    "extract",
    "visualize",
    "annotation",
    "data",
    # ... add "evaluation"
]

_LAZY_MODULES = {
    "annotation": "langextract.annotation",
    "data": "langextract.data",
    # ... add:
    # "evaluation": "langextract.evaluation",
}
```

Do **not** add top-level `lx.evaluate` wrapper in v1 (RESEARCH A4) — lazy submodule only, unlike `extract`/`visualize`.

---

### `pyproject.toml` (config)

**Analog:** same file — explicit setuptools package list + import-linter contracts.

**Packages list** (lines 81–88):
```toml
[tool.setuptools]
packages = [
    "langextract",
    "langextract._compat",
    "langextract.core",
    "langextract.providers",
    "langextract.providers.schemas"
]
```
Add `"langextract.evaluation"` in the same commit that lands the package.

**Import-linter** (lines 138–163) — add a forbidden contract mirroring core isolation, e.g. evaluation must not import annotation/providers/high-level modules; core must not import evaluation:
```toml
[[tool.importlinter.contracts]]
name = "Core must not import high-level modules"
type = "forbidden"
source_modules = ["langextract.core"]
forbidden_modules = [
  "langextract.annotation",
  "langextract.chunking",
  "langextract.prompting",
  "langextract.resolver",
]
```

---

### `README.md` / `docs/examples/evaluation_ci.md` (docs)

**Analog:** README More Examples bullets (lines 410–432); longer snippet style in `docs/examples/output_schema.md`.

**README link bullet** (README.md lines 420–426):
```markdown
### Medication Extraction
...
**[View Medication Examples →](https://github.com/google/langextract/blob/main/docs/examples/medication_examples.md)**
```

**In-memory CI snippet style** (output_schema.md lines 23–52) — construct `lx.data.AnnotatedDocument` / `Extraction` / `CharInterval` with explicit IDs; assert `report.micro.f1` (or equivalent field). Prefer tiny README subsection **or** 15-line `docs/examples/evaluation_ci.md` + link (RESEARCH Open Question 3).

## Shared Patterns

### Copyright + `from __future__ import annotations`
**Source:** every library module (e.g. `prompt_validation.py` lines 1–17)
**Apply to:** all new `langextract/evaluation/*.py` and `tests/evaluation_test.py`

### Core-only data import
**Source:** `prompt_validation.py` line 27; ROADMAP layering lock
**Apply to:** `criteria.py`, `matching.py`, `metrics.py`, `evaluation/__init__.py`
```python
from langextract.core import data
```

### Explicit `document_id` in fixtures
**Source:** `extract_drop_ungrounded_test.py` lines 37–40; pitfall in `core/data.py` lines 237–242
**Apply to:** all evaluation tests and docs examples

### absltest + `parameterized.named_parameters`
**Source:** `tests/prompt_validation_test.py`, `tests/data_lib_test.py`
**Apply to:** `tests/evaluation_test.py` (not pytest-native for library module tests)

### ValueError for invalid public config
**Source:** `extraction.py` lines 231–236; `factory.py` lines 142–143
**Apply to:** `evaluate(...)` convenience-flags XOR `criteria=`; mismatched `document_id` sets

### CharInterval exclusive-end semantics
**Source:** `langextract/core/data.py` lines 50–57
**Apply to:** `span_iou` and all hand-worked IoU fixtures (`end_pos` exclusive; no `+1`)

### Lazy package export + setuptools registration
**Source:** `langextract/__init__.py` `_LAZY_MODULES`; `pyproject.toml` packages list
**Apply to:** packaging tasks in plan 07-04 (same commit as package introduction)

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | Greedy 1:1 IoU matching has no in-repo peer; use visualization sort + annotation merge as role-matches and RESEARCH algorithm sketch for the algorithm body |

## Metadata

**Analog search scope:** `langextract/**/*.py`, `tests/*_test.py`, `pyproject.toml`, `README.md`, `docs/examples/`
**Files scanned:** ~46 library modules + ~27 test modules (tracked-source gate via `git ls-files`)
**Pattern extraction date:** 2026-10-11
**Tracked analogs verified:** `langextract/prompt_validation.py`, `langextract/annotation.py`, `langextract/visualization.py`, `langextract/core/data.py`, `langextract/core/types.py`, `langextract/__init__.py`, `langextract/extraction.py`, `langextract/factory.py`, `langextract/providers/gemini_batch.py`, `pyproject.toml`, `tests/prompt_validation_test.py`, `tests/extract_drop_ungrounded_test.py`, `tests/data_lib_test.py`, `README.md`, `docs/examples/output_schema.md`
