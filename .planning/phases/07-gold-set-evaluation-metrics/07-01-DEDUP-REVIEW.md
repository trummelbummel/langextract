# Dedup review — 07-01

**Plan:** 07-01
**Commits:** b7e9085..292c1f7
**Timestamp:** 2026-10-11
**Scoped files:** `langextract/evaluation/metrics.py`, `langextract/evaluation/__init__.py`, `tests/evaluation_test.py` (+ one-hop: none yet beyond re-exports)

## Module map (brief)

| File | Public symbols | Notes |
|------|----------------|-------|
| metrics.py | ClassScore, EvaluationReport, prf_from_counts, report_from_counts | New; no overlap with prompt_validation reports (different domain) |
| __init__.py | re-exports only | Thin package surface |
| evaluation_test.py | MetricsPrfTest, MetricsReportTest | Hand-worked rows; no shared fixture yet |

## Signals

| Signal | Confidence | Result |
|--------|------------|--------|
| S01 duplicate helpers | — | None |
| Cross-file PRF math | — | None (first scoring API) |
| Test setup duplication | — | None (parameterized tables only) |

## Auto-applied consolidations

None.

## Propose-only (non-blocking)

None for this plan. Later plans may introduce Extraction fixtures — share via helpers then if duplicated across test classes.

## Summary

No consolidations; package is greenfield and correctly layered.
