---
phase: 05-live-extract-ollama-preflight
plan: 01
review: dedup
timestamp: 2026-10-11T07:13:00Z
---

# Dedup review — 05-01

## Scope

Commits: `7ccfea4` … `9c45e49`
Files: `scripts/trace_extract.py`, `tests/trace_extract_test.py`, `config.yaml`
One-hop: tests load the script via `importlib`; no other production importers.

## Auto-applied consolidations

None. No HIGH-confidence cross-file identical functions, classes, constants, or type definitions for the 05-01 delta.

## Propose-only

| Signal | Confidence | Finding | Proposal |
|--------|------------|---------|----------|
| S06 god-module | MEDIUM | `scripts/trace_extract.py` ~978 lines: catalog/print, stage wrappers, probes, preflight, CLI | Split in a later plan (print / probes / preflight modules); out of 05-01 budget |
| S01 (test setup) | MEDIUM | Live + Preflight `setUp` both start `_StubOllama` with identical thread/cleanup | Optional `_start_stub(test)` helper in the test module |
| S08 misplaced | LOW | Preflight HTTP lives next to probe install in one script | Acceptable for MVP CLI; revisit with S06 split |

## Verdict

No blocking consolidations. Safe to proceed after human commit approval.
