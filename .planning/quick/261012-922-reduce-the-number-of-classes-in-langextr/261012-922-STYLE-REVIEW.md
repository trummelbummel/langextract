# Style review — 261012-922

**Mode:** quick
**Timestamp:** 2026-10-12 05:29 UTC
**Commits under review:** 4513935..32c6ac6 (+ uncommitted style passes)
**Files:** `langextract/evaluation/evaluation.py`

## R15 — Swallowed exceptions

No `try`/`except` candidates in scoped production code. HITL: PASS.

## REFACTORED

| Rule | Change |
|------|--------|
| R37 | inlined _evaluate_documents body into Evaluator.evaluate and deleted the private pass-through |
| R40 | renamed _accumulate_counts_for_document→_counts_for_document; returns dict[str,_CountTriple] instead of mutating caller-owned per_class_counts; evaluate merges returned counts |
| R41 | EvaluationReport now frozen=True with per_class: Mapping[str, ClassScore]; ClassScore already frozen; _CountTriple stays mutable private accumulator |
| R29 | collapsed three parallel sum() over per_class_counts into one loop accumulating micro_counts._CountTriple fields |
| R38 | introduced _DEFAULT_IOU_THRESHOLD; used by SpanIoU.threshold, evaluate(iou_threshold=), and _resolve_criteria exclusivity check. Compare-to-default remains (None sentinel would change which criteria=+ |
| R03 | evaluate now sequences named steps; extracted _aggregate_per_class_counts and _evaluation_report_from_count_triples for aggregate and report phases; greedy_match already had candidate/select helpers |
| R34 | removed redundant bool() wrap around text_eval_func result (already Callable[..., bool]); empty predicted/gold early return kept (docstring + avoids candidate build) |
| R25 | Renamed private _CountTriple.tp/fp/fn to true_positives/false_positives/false_negatives and updated all uses. REPORTED (public API, do not rename): ClassScore.tp/fp/fn (lines 162-164) and prf_from_cou |
| R43 | Removed decision IDs (D-02 / D-03) from TextMatch class docstring. |
| R63 | aligned _candidate_pairs Extraction-sequence params to predictions/references (same names as _counts_for_document); public predicted/gold unchanged |
| R64 | trailing commas + one-item-per-line on MatchCriterion/criteria __call__ signatures, ClassScore ctor, text_eval_func call, _candidate_pairs/_aggregate_per_class_counts/_counts_for_document calls, and d |

## FINDINGS (report-only)

| File | Rule | Finding |
|------|------|---------|
| `langextract/evaluation/evaluation.py` | R31 | conflict: locked 261012-922 consolidation; Evaluator is a no-state namespace (all staticmethods/nested types) with module aliases ClassScore=Evaluator.ClassScore etc.; leave public shape |
| `langextract/evaluation/evaluation.py` | R42 | langextract/evaluation/ __init__.py only re-exports this sibling; stuttering path evaluation.evaluation; dual __all__. Target: git mv evaluation.py -> langextract/evaluation.py, drop package dir, one __all__ (cross-modul |
| `langextract/evaluation/evaluation.py` | R46 | adding a public name requires syncing Evaluator members, module aliases (334-345), __all__ here, and evaluation/__init__.py imports+__all__; derive exports from one source or collapse package (R42) |
| `langextract/evaluation/evaluation.py` | R13 | ClassScore and EvaluationReport cross the evaluation package boundary as plain dataclasses; suggest Pydantic BaseModel with Field descriptions for precision/recall/f1/tp/fp/fn and nested per_class Mapping if API validati |
| `langextract/evaluation/evaluation.py` | R39 | tp/fp/fn clump travels as prf_from_counts args, report_from_counts tuple[int,int,int], ClassScore fields, and private _CountTriple with conversions in evaluate; public ClassScore.tp/fp/fn and report_from_counts tuple sig |
| `langextract/evaluation/evaluation.py` | R27 | report_from_counts public signature uses tuple[int,int,int] for (tp,fp,fn) and unpacks by position; ClassScore.tp/fp/fn and that tuple API are locked — keep _CountTriple privately; changing the public triple would break  |
| `langextract/evaluation/evaluation.py` | R28 | evaluate converts _CountTriple→tuple triples then report_from_counts unpacks them again; micro is correctly derived from per_class_counts (not a parallel running total). Suggest private _report_from_count_triples(Mapping |
| `langextract/evaluation/evaluation.py` | R33 | conflict: R31; greedy_match uses score_fn=None then resolves to Evaluator.span_iou — real default cannot be referenced while class body is open under Evaluator namespace consolidation; leave None sentinel |
| `langextract/evaluation/evaluation.py` | R44 | Public APIs reuse predicted/gold for AnnotatedDocument sequences (evaluate), Extraction sequences (greedy_match), and single Extraction (span_iou/criteria). Suggest distinct public names if a breaking rename is ever acce |
| `langextract/evaluation/evaluation.py` | R62 | new module: main entry Evaluator.evaluate sits after supporting methods (span_iou, criteria, prf_from_counts, greedy_match). Prefer evaluate immediately after result types, then helpers in call order; do not reorder here |
| `langextract/evaluation/evaluation.py` | R30 | _counts_for_document attributes TP to prediction.extraction_class and drops matched gold from FN without requiring SameClass. Violating input: evaluate(..., criteria=[SpanIoU(0.5)]) can match cross-class pairs and credit |

## Coverage

`rules.py check`: **57/57 cells**, 0 invalid. tests group NA (production file).

## Summary

1 file reviewed, 11 refactored, 0 R15 candidates, 11 report-only notes.
Public `ClassScore.tp`/`fp`/`fn`/`f1` and `Evaluator` namespace consolidation left unchanged (locked API / 261012-922).
