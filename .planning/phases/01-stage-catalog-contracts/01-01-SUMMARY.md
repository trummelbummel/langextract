---
phase: 01-stage-catalog-contracts
plan: 01
subsystem: tooling
tags: [trace-extract, config-yaml, stage-catalog, ollama]

requires: []
provides:
  - "Repo-root config.yaml call constants (model_id, model_url, provider)"
  - "scripts/trace_extract.py catalog printer with static call header"
  - "load_config() missing-path exit 1"
affects:
  - 01-02
  - phase-2-extraction-snapshots
  - phase-5-live-extract

actuals:
  tokens: 943
  tasks: 2
  commits: 2

plan_head_before: dc7bf30d4430b89232f5b5a5970ba68ee4581715

tech-stack:
  added: []
  patterns:
    - "Maintainer CLI via python scripts/... with yaml.safe_load of repo-root config"
    - "Module-level STAGE_CATALOG iterated for [label] function — path headers"

key-files:
  created:
    - config.yaml
    - scripts/trace_extract.py
  modified: []

key-decisions:
  - "Call header prints full model_url plus host= netloc for D-09 clarity"
  - "load_config exposed for missing-path testing without deleting real config"
  - "Phase 1 config holds only model_id/model_url/provider (empty_parse/redact deferred to 01-02)"

patterns-established:
  - "STAGE_CATALOG tuple list drives stdout stage sections with blank-line gaps"
  - "Missing config fails closed via SystemExit(1) with resolved path on stderr"

requirements-completed: [CTR-01, CTR-02, STG-01, STG-02]

coverage:
  - id: D1
    description: "Static call header from config.yaml (lx.extract, model_id, provider, model_url host)"
    requirement: CTR-01
    verification:
      - kind: other
        ref: "python scripts/trace_extract.py (assert lx.extract, model_id=gemma3:4b, OllamaLanguageModel, http://localhost:11434)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Seven ordered stage headers with align helper and blank-line separation"
    requirement: STG-01
    verification:
      - kind: other
        ref: "python scripts/trace_extract.py (ordered label index + helper: WordAligner.align_extractions)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Observation stays in script + YAML only (no langextract/ or demo_ollama edits)"
    requirement: CTR-02
    verification:
      - kind: other
        ref: "git diff plan_head..HEAD --name-only equals config.yaml scripts/trace_extract.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Missing config.yaml fails closed with exit 1 via load_config"
    requirement: STG-02
    verification:
      - kind: unit
        ref: "load_config(Path('scripts/_no_such_config.yaml')) raises SystemExit(1)"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-10-10
status: complete
---

# Phase 1 Plan 01: Stage catalog walking skeleton Summary

**Repo-root `config.yaml` plus `scripts/trace_extract.py` print a static `lx.extract` call header and the seven-stage ownership catalog, exiting 0 without Ollama.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-10-10T14:50:13Z
- **Completed:** 2026-10-10T14:53:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `config.yaml` with `model_id: gemma3:4b`, `model_url: http://localhost:11434`, `provider: OllamaLanguageModel`
- Runnable catalog printer: call header + seven `[label] function — path` lines (align helper) with blank-line gaps
- Missing-config path exits 1 via `load_config` without printing the catalog

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end catalog run — config.yaml + script print path** - `fa60430` (feat)
2. **Task 2: Missing-config exit path** - `9a65bf8` (feat)

## Files Created/Modified

- `config.yaml` — Phase 1 call constants only
- `scripts/trace_extract.py` — STAGE_CATALOG printer, `load_config`, static call header

## Decisions Made

- Call header includes full `model_url` and `host=` netloc so both D-09 host intent and the automated full-URL assert are satisfied
- `load_config(path)` is a public helper so missing-path can be tested without renaming the real file
- Deferred `empty_parse_message` / `redact_keys` / `redact()` to plan 01-02 per this plan’s action (call constants only)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] `load_config` + missing-path exit included in tracer commit**
- **Found during:** Task 1 (tracer)
- **Issue:** Threat T-01-03 and Task 2 require fail-closed missing config; shipping catalog without it would leave a hung/unclear path
- **Fix:** Implemented `load_config` with `SystemExit(1)` in the tracer task; Task 2 only hardened the resolved-path error message
- **Files modified:** `scripts/trace_extract.py`
- **Commit:** `fa60430` (implementation), `9a65bf8` (message harden)

**2. [Rule 1 - Bug] Pre-commit pyink rejected first Task 1 commit**
- **Found during:** Task 1 commit
- **Issue:** pyink reformatted an f-string split; commit aborted
- **Fix:** Re-staged reformatted file and committed anew (no amend)
- **Files modified:** `scripts/trace_extract.py`
- **Commit:** `fa60430`

## Known Stubs

None — Phase 1 catalog is intentionally header-only (D-02); no placeholder payloads.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary schemas beyond the accepted T-01-01/T-01-02 surfaces in the plan threat model. T-01-03 mitigated by missing-config exit 1.

## Self-Check: PASSED

- FOUND: `config.yaml`
- FOUND: `scripts/trace_extract.py`
- FOUND: commit `fa60430`
- FOUND: commit `9a65bf8`
