# Test Review — Fix Backlog

Source: `/test-review` smell hunt + mutation weak-passes
Scope: `tests/evaluation_test.py`, `tests/extract_drop_ungrounded_test.py`
Classified: via `/classify-tasks` rules (`.claude/skills/classify-tasks`)

Legend: ✅ simple (autonomous) · ⚠️ complex (needs steering before execution)

Status: `[ ]` open · `[x]` done

---

## Task Classification

| Task | Title | Verdict | Signals | Risk |
|------|-------|---------|---------|------|
| TF-001 | Parametrize XOR config raise twins (S4) | ✅ simple | L1 | Low — test-only collapse |
| TF-002 | Parametrize match_attributes accept/reject (S4) | ✅ simple | L1 | Low — named scenarios keep both paths |
| TF-003 | Parametrize text_eval_func accept/reject (S4) | ✅ simple | L1 | Low — named scenarios keep both paths |
| TF-004 | Documents-path drop_ungrounded coverage (S6) | ✅ simple | L1 | Low — add False/default case |
| TF-005 | All-ungrounded extract yields empty (S6) | ✅ simple | L1 | Low — one negative case |

**Summary: 5 simple / 0 complex out of 5 total tasks**

---

### [x] TF-001: Parametrize XOR config raise twins (S4) ✅

**Smell:** S4 — Copy-paste twins
**Action:** fix (collapse into named_parameters)
**Files:** `tests/evaluation_test.py`
**Verdict:** simple — L1
**Risk:** Low — test-only collapse

**Work**

- Merge `test_criteria_with_nondefault_iou_threshold_raises` and
  `test_criteria_with_match_attributes_raises` into one parametrized test with
  named scenarios (`iou_threshold_xor`, `match_attributes_xor`).

**Done when**

- One test method with `@parameterized.named_parameters`; both XOR paths still fail with ValueError.
- `pytest tests/evaluation_test.py -q` green.

**Steering**

- (n/a — simple)

**Resolution**

- Collapsed XOR raise twins into `test_criteria_with_convenience_flag_raises`.

---

### [x] TF-002: Parametrize match_attributes accept/reject (S4) ✅

**Smell:** S4 — Copy-paste twins
**Action:** fix
**Files:** `tests/evaluation_test.py`
**Verdict:** simple — L1
**Risk:** Low

**Work**

- Collapse `test_match_attributes_true_rejects_unequal_attributes` and
  `test_match_attributes_true_accepts_equal_attributes` into named scenarios
  with expected micro P/R/F1.

**Done when**

- Named parametrized test covers unequal→zeros and equal→ones.
- Suite green.

**Steering**

- (n/a)

**Resolution**

- Collapsed match_attributes accept/reject into `test_match_attributes_true`.

---

### [x] TF-003: Parametrize text_eval_func accept/reject (S4) ✅

**Smell:** S4 — Copy-paste twins
**Action:** fix
**Files:** `tests/evaluation_test.py`
**Verdict:** simple — L1
**Risk:** Low

**Work**

- Collapse `test_text_eval_func_reject_yields_zeros` and
  `test_text_eval_func_accept_yields_ones` into named scenarios.

**Done when**

- Named parametrized test; suite green.

**Steering**

- (n/a)

**Resolution**

- Collapsed text_eval_func accept/reject into `test_text_eval_func`.

---

### [x] TF-004: Documents-path drop_ungrounded coverage (S6) ✅

**Smell:** S6 — Missing negative / alternate path
**Action:** add-case
**Files:** `tests/extract_drop_ungrounded_test.py`
**Verdict:** simple — L1
**Risk:** Low

**Work**

- Documents path only asserts `drop_ungrounded=True`. Add named case(s) that
  `False` (or default) keeps both grounded + ungrounded on the documents path.

**Done when**

- Documents path covered for keep-both behavior; suite green.

**Steering**

- (n/a)

**Resolution**

- Documents path now named_parameters True/False (`test_drop_ungrounded_on_documents_path`).

---

### [x] TF-005: All-ungrounded extract yields empty (S6) ✅

**Smell:** S6 — Missing negative case
**Action:** add-case
**Files:** `tests/extract_drop_ungrounded_test.py`
**Verdict:** simple — L1
**Risk:** Low

**Work**

- When every extraction lacks `char_interval` and `drop_ungrounded=True`,
  result extractions must be empty (string path).

**Done when**

- Focused test asserts empty list; suite green.

**Steering**

- (n/a)

**Resolution**

- Added `test_drop_ungrounded_true_all_ungrounded_yields_empty`.

### [x] TF-006: Extract annotate run helpers in chunk_events_test (S13) ✅

**Smell:** S13 — Duplicated setup
**Action:** fix
**Files:** `tests/chunk_events_test.py`
**Verdict:** simple — L1
**Risk:** Low — test-only helpers

**Work**

- Add `_run_annotate` / `_events_named` and migrate the highest-frequency
  annotate+filter blocks (count/index/batch tests).

**Done when**

- Helpers exist; at least the three batch_length=3 happy-path tests use them.
- Suite green.

**Steering**

- (n/a)

**Resolution**

- Added helpers; migrated `test_one_started_and_finished_per_chunk`,
  `test_chunk_indices_and_ranges_match_chunk_iterator`,
  `test_batch_index_groups_chunks`. Remaining call sites left for TF-007.

### [ ] TF-007: Finish S13 migration + split multi-behavior tests (S13/S4) ✅

**Smell:** S13 / S4 — Remaining duplicated setup; multi-behavior methods
**Action:** fix
**Files:** `tests/chunk_events_test.py`
**Verdict:** simple — L1
**Risk:** Low

**Work**

- Migrate remaining annotate call sites to `_run_annotate` / `_events_named`.
- Split `test_pass_index_for_single_and_multi_pass`,
  `test_extract_str_and_documents_deliver_events`,
  `test_without_on_event_parse_suppression_unchanged` into single-behavior tests
  (aligns with style R19).

**Done when**

- Annotate setup appears once via helpers; named single-behavior tests; suite green.

**Steering**

- (deferred to post-plan gate — open questions none for simple)

### [x] TF-008: Parametrize Ollama usage path twins (S4) ✅

**Smell:** S4 — Copy-paste twins
**Action:** fix
**Files:** `tests/inference_test.py:164`
**Verdict:** simple — L1
**Risk:** Low
**Status:** auto-resolved `aa4efe1` (261014-g6y step 6)

**Work**

- Collapse generate vs gpt-oss usage assertion tests via named_parameters
  (aligns with style R18).

**Done when**

- One parametrized usage test covering both paths; suite green.

**Steering**

- (done)
