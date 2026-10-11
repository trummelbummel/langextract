---
phase: 05-live-extract-ollama-preflight
plan: 02
review: dedup
timestamp: 2026-10-11T07:28:00Z
commit_range: 66eff0b..e4f1e9f
---

# Dedup review — 05-02

## Scope

Commits: `66eff0b` … `e4f1e9f` (includes style-review)
Files: `scripts/trace_extract.py`, `tests/trace_extract_test.py`, `config.yaml`
One-hop: tests load the script via `importlib`; no other production importers of `trace_extract`.

## Module map (summary)

| File | Public / notable symbols | Project imports |
|------|--------------------------|-----------------|
| `scripts/trace_extract.py` | `load_config`, stage wrappers, `trace_probes`, `preflight_ollama`, `check_single_inference`, `run_live`, `main` | lazy `langextract.*` |
| `tests/trace_extract_test.py` | snapshot/wrapper/probe/live/preflight/guard tests; `_StubOllama`, `_STAGE_TARGETS` | `langextract.*`, script via importlib |
| `config.yaml` | call constants only | — |

## Changes applied

| Action | Files | What changed |
|--------|-------|--------------|
| S01 / repeated stub setup | `tests/trace_extract_test.py` | Extracted `_start_stub(test)`; Live, Preflight, and Guard `setUp` share it |
| S03 (prior style) | `tests/trace_extract_test.py` | `_SINGLE_CALL_LINE` already deduped in style-review (`trace._SINGLE_CALL_LINE`) |

## Proposed reorganization (needs human approval)

| Signal | Confidence | Files | Proposal | Impact |
|--------|------------|-------|----------|--------|
| S06 god-module | MEDIUM | `scripts/trace_extract.py` (~1050 lines) | Split catalog/print, wrappers, probes, preflight/CLI in a later plan | Import path changes for tests loading the script as one module |
| S03 / S01 | MEDIUM | `_STAGE_TARGETS` vs `_load_probe_targets()` | Drive tests from `trace._load_probe_targets()` instead of a parallel dict | Touches many probe/wrapper tests; keep until a dedicated cleanup |
| S08 misplaced | LOW | Preflight HTTP beside probes in one script | Acceptable for MVP CLI; revisit with S06 split | — |

## Verdict

1 HIGH/MEDIUM redundancy auto-fixed (stub startup). 3 proposals for later review. No blocking consolidations.

Summary: 4 redundancies considered, 1 auto-fixed (+1 already fixed in style-review), 3 proposals.
