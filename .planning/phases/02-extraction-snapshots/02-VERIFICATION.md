---
phase: 02-extraction-snapshots
verified: 2026-10-10T15:12:00Z
status: passed
score: 9/9 must-haves verified
covered_files:
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - .planning/phases/02-extraction-snapshots/02-01-PLAN.md
  - .planning/phases/02-extraction-snapshots/02-01-SUMMARY.md
  - .planning/phases/02-extraction-snapshots/02-02-PLAN.md
  - .planning/phases/02-extraction-snapshots/02-02-SUMMARY.md
  - config.yaml
  - scripts/trace_extract.py
  - tests/trace_extract_test.py
covered_digest: "v1:sha256:c150cef2d564a38ce72604e560716f674043a983f6ebc35759182c2ccba4d148"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: Extraction snapshots Verification Report

**Phase Goal:** Developer can print ungrounded vs grounded extraction field copies so parse and align stay a before/after pair even after align mutates objects
**Verified:** 2026-10-10T15:12:00Z
**Status:** passed
**Re-verification:** No — initial verification
**Mode:** mvp (goal is not in "As a / I want / so that" form in ROADMAP; verified on the goal-backward outcome: the parse record stays ungrounded after align mutates the live objects)

## Goal Achievement

### Roadmap Success Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| SC1 | Parse-time snapshot shows `char_interval` / `alignment_status` still empty (including empty lists) | ✓ VERIFIED | `_snapshot_extraction` (script L162–178) copies fields at call time. `test_parse_snapshot_survives_align_mutation` runs the real `Resolver.resolve` and snapshots it. It then runs real `Resolver.align` and asserts the live `resolved[0].char_interval` is not None (mutation proven) while `parse[0].char_interval` and `alignment_status` are still None. `test_empty_parse_prints_explicit_empty_lists` covers the empty list: a real `resolve('not json')` returns `[]`, the snapshot is `()`, and the printed output has `0 extractions`, `parse: []` and `align: []`. My independent replay gave parse after align `[(None, None), (None, None)]`. |
| SC2 | Align snapshot of the same logical extractions shows grounding populated (or explicitly ungrounded) without overwriting the parse snapshot | ✓ VERIFIED | Replay: `headache` aligns to `[18, 26)` / `match_exact`. `purple elephant` aligns to `ungrounded` / `ungrounded`, read from `config.yaml` `ungrounded_label`. `ExtractionSnapshot` is `frozen=True`. `attributes` are re-listed one level deep (`_copy_attributes`). `test_snapshot_independent_of_later_mutation` asserts `is not` identity and no leakage. The parse tuple is unchanged after the align snapshot. |
| SC3 | Printed output presents parse and align as a before/after grounding pair | ✓ VERIFIED | `print_grounding_pair` (L206–251) prints `parse:` and then `align:` per extraction. `test_print_grounding_pair_orders_parse_before_align` asserts the align line is directly after the parse line. Live replay output below. |

Replay output (real `Resolver.resolve` → `align`, run by me):

```
grounding pair (parse → align): 2 extractions
  [1] symptom: 'headache'  index=1
    parse: char_interval=None alignment_status=None
    align: char_interval=[18, 26) alignment_status=match_exact
  [2] symptom: 'purple elephant'  index=2
    parse: char_interval=None alignment_status=None
    align: char_interval=ungrounded alignment_status=ungrounded
```

### Plan must_haves (02-01, 02-02)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `snapshot_extractions` of resolve output has None `char_interval` / `alignment_status` | ✓ VERIFIED | Behavioral test passes (see above) |
| 2 | Parse snapshot still None after `Resolver.align` mutates the same objects | ✓ VERIFIED | Same test asserts the live object mutated and the snapshot not |
| 3 | Align snapshot shows `(18, 26)` / `match_exact`; unaligned stays None | ✓ VERIFIED | Same test |
| 4 | Snapshots hold only copied primitives, no live refs | ✓ VERIFIED | Frozen dataclass; tuple/str/dict-copy fields; `is not` asserts in `test_snapshot_independent_of_later_mutation` |
| 5 | Empty → explicit `parse: []` / `align: []`; unaligned → config label on the align side only | ✓ VERIFIED | `test_empty_parse_prints_explicit_empty_lists`, `test_unaligned_extraction_prints_ungrounded_label`. `grep "'ungrounded'" scripts/trace_extract.py` has 0 matches, so the label is read from config. |
| 6 | Positional pairing: duplicates and touching spans stay separate, order stable | ✓ VERIFIED | `test_duplicate_extractions_stay_separate_in_order`, `test_touching_spans_print_as_two_pairs` |
| 7 | `ValueError` on count mismatch (both counts named), `ValueError` on class/text mismatch (position named), `TypeError` on non-snapshot input, all before any output | ✓ VERIFIED | Guards at L220–238 run before the first `print`. Tests assert empty stdout on count mismatch and `position 2` in the message. `test_live_extraction_rejected_with_type_error` checks both sides. |
| 8 | Catalog stdout unchanged; no `grounding pair`, `ungrounded` or `empty_parse_message` printed by `main()` | ✓ VERIFIED | `main()` is unchanged (L255–259). My catalog run exits 0, stage order is correct, the align helper line and `langextract/resolver.py` owner are present, and neither string is in the output. |
| 9 | Prohibitions honored (no deepcopy, no top-level langextract import in the script, nothing under `langextract/` or `examples/`, no WordAligner wrap, no probes or `lx.extract`) | ✓ VERIFIED | 0 `deepcopy` in non-comment script lines. 0 `^(import\|from) langextract` lines in the script. `git diff 156e9f2 HEAD -- langextract examples` is empty. Non-planning files changed: `config.yaml`, `scripts/trace_extract.py`, `tests/trace_extract_test.py` only. |

**Score:** 9/9 truths verified (0 present, behavior-unverified). Every behavior-dependent truth (mutation survival, ordering, guards) is backed by a passing behavioral test.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/trace_extract.py` | `ExtractionSnapshot`, `snapshot_extractions`, `print_grounding_pair` with guards | ✓ VERIFIED | Substantive and wired: tests import it via `importlib` and call all three. |
| `tests/trace_extract_test.py` | absltest on real Resolver resolve/align, with edge tests | ✓ VERIFIED | 11 tests, all OK. |
| `config.yaml` | `ungrounded_label: ungrounded` | ✓ VERIFIED | Present at L10; asserted by `test_ungrounded_label_comes_from_config`. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| test | `Resolver.resolve` / `.align` | `OLLAMA_FORMAT_HANDLER`, canned JSON, no model call | ✓ WIRED |
| `snapshot_extractions` | `print_grounding_pair` | two snapshot tuples paired by position | ✓ WIRED |
| `config.yaml ungrounded_label` | `print_grounding_pair` | argument; test reads `load_config(_CONFIG_PATH)['ungrounded_label']` | ✓ WIRED (caller-supplied by design; `main()` wiring is Phase 4) |
| `Resolver.resolve('not json')` → `[]` | printed `parse: []` | empty tuple rendering | ✓ WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| `ExtractionSnapshot` | interval, status, attributes | live `Extraction` from real `Resolver.resolve` / `align` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full phase test file | `.venv/bin/python tests/trace_extract_test.py` | `Ran 11 tests ... OK` | ✓ PASS |
| Catalog stdout and stage-order assertions | `.venv/bin/python scripts/trace_extract.py` plus the plan's order/helper/owner assertions | exit 0, `catalog assertions ok` | ✓ PASS |
| Real resolve → snapshot → align → pair replay | ad-hoc script (output above) | matches expected | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED (no probes declared in this phase's plans; probes are Phase 3 scope).

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| STG-05 | 02-01, 02-02 | Parse stage shows ungrounded extractions (`char_interval` / `alignment_status` still empty), including empty lists | ✓ SATISFIED | SC1 evidence. The helper layer is delivered; the live parse-stage print is wired in Phase 4 by design. |
| STG-08 | 02-01, 02-02 | Parse and align printed as a before/after grounding pair for the same extractions | ✓ SATISFIED | SC3 evidence, plus count and identity guards ensure "same extractions". |

Cross-reference: REQUIREMENTS.md maps exactly STG-05 and STG-08 to Phase 2 (both marked Complete in the traceability table). Both IDs appear in the `requirements:` frontmatter of 02-01-PLAN and 02-02-PLAN. **Orphaned requirements: none.** No Phase 2 ID is unclaimed, and no plan claims an ID mapped to another phase.

### Regression Check (Phase 1)

Phase 1 verification was `passed` (7/7). Phase 1 truths re-checked:
- Seven labels are in order.
- The align helper line is present.
- Owners are repo-relative.
- `config.yaml` is still loaded.
- `redact()` is untouched.
- `git diff 156e9f2 HEAD` shows only additions (script +116/-0, config +3/-0), so no Phase 1 code was altered.

No regressions.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/trace_extract.py` | — | No TBD/FIXME/XXX/TODO/HACK markers, no stubs, no empty implementations | — | None |

### Project Constraints (CLAUDE.md / diff-budget)

| Constraint | Status | Evidence |
|-----------|--------|----------|
| ≤ ~150 non-test lines per task, ≤ 3 source files | ✓ | The phase added 116 script lines plus 3 config lines in total (≈ +79 in 02-01, ≈ +48/−8 in 02-02). That is 2 source files, tests excluded. |
| ≤ ~400 non-test lines per plan | ✓ | Well under. |
| Tests in the same commit as the code | ✓ | RED `test(...)` and GREEN `feat(...)` pairs per task. |
| No unrelated refactor/reformat | ✓ | Additions only. |

### Human Verification Required

None. All phase truths are offline, deterministic and covered by passing behavioral tests; nothing visual or external is involved.

### Notes (informational, non-blocking)

1. **Environment:** bare `python scripts/trace_extract.py` fails with `ModuleNotFoundError: yaml`, because Homebrew Python 3.14 lacks PyYAML. This predates Phase 2, since Phase 1 imports `yaml` at module top. Both plans' literal `<verify>` commands use bare `python` and would fail in this environment. The verification was run with `.venv/bin/python`, as intended. Consider changing the plan verify commands to use `.venv/bin/python`.
2. **Wiring scope:** the helpers are intentionally not called from `main()`, per Phase 1 D-01 and the plan; live wiring is Phase 4 (STG-03/04/06/09). The Phase 2 goal ("developer can print ...") is met at the function level and proven against the real resolver.
3. **Bookkeeping:** the ROADMAP Phase 2 checkbox and progress row still read "In Progress". Both plans are complete (2/2), so the orchestrator should mark Phase 2 complete.

### Gaps Summary

No gaps. The phase goal is achieved: parse and align stay a before/after pair after `Resolver.align` mutates the live objects, and the evidence comes from running the real resolver rather than from SUMMARY claims.

---

_Verified: 2026-10-10T15:12:00Z_
_Verifier: Claude (gsd-verifier)_
