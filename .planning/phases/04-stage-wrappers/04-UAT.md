---
status: complete
phase: 04-stage-wrappers
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
started: 2026-10-11T06:49:17Z
updated: 2026-10-11T07:00:07Z
---

## Current Test

[testing complete]

## Tests

### 1. Model record from offline extract
expected: One offline real lx.extract yields a model StageRecord with full batch prompt in and verbatim raw model text out; out keys are exactly prompt_index, score, raw_model_text
result: pass
coverage_id: 04-01-D1

### 2. Printer catalog order and escapes
expected: print_stage_records prints catalog headers in catalog order, escapes control characters, prints empty raw text as ''
result: pass
coverage_id: 04-01-D2

### 3. Chunk wrapper without recursion
expected: Chunk wrapper yields the same chunks via next() without RecursionError and restores the class attribute
result: pass
coverage_id: 04-01-D3

### 4. Prompt matches model batch prompt
expected: Prompt record equals model batch_prompts[0] for the same offline extract; chunk, prompt, model print in catalog order
result: pass
coverage_id: 04-01-D4

### 5. Parse record fields from offline extract
expected: One offline lx.extract yields a parse record whose in holds the raw model text (== model out), suppress_parse_errors and the five format flags; out holds ungrounded snapshots while the document is still grounded
result: pass
coverage_id: 04-02-D1

### 6. Parse section print layout
expected: [parse] prints header, raw text, flags line and extractions
result: pass
coverage_id: 04-02-D2

### 7. Empty parse callout matrix
expected: Empty parse callout — not json / fenced-with-use_fences=False -> empty_parse_message + error; {"extractions": []} -> empty_list_message only; '' -> empty_parse_message with 'Empty or invalid input string.'
result: pass
coverage_id: 04-02-D3

### 8. Callout escapes and non-empty parse
expected: Callout and raw text escape control characters; diagnosis adds no StageRecord; non-empty parse records parse_error None and prints no callout; config has empty_list_message
result: pass
coverage_id: 04-02-D4

### 9. Align record from offline extract
expected: One offline lx.extract with all five wrappers yields an align record with chunk source_text, token_offset 0, char_offset 0 (int, not None) and n_extractions 2
result: pass
coverage_id: 04-03-D1

### 10. Align snapshots match document
expected: Align out snapshots equal the returned document's extractions (same objects yielded) — headache (18, 26) match_exact, purple elephant ungrounded
result: pass
coverage_id: 04-03-D2

### 11. Five-stage walkthrough catalog order
expected: Five sections print in catalog order chunk, prompt, model, parse, align from one offline call
result: pass
coverage_id: 04-03-D3

### 12. Align section offsets spans slices
expected: [align] prints offsets line with config caption, span/status/slice per extraction, config ungrounded_label for ungrounded, and the parse->align pair
result: pass
coverage_id: 04-03-D4

### 13. Align document coordinates minus offset
expected: Direct align call with token_offset=5, char_offset=100 prints span [118, 126) and slice 'headache'; omitted char_offset prints 0, never None
result: pass
coverage_id: 04-03-D5

### 14. Align with empty parse
expected: Empty parse still writes an align record (n_extractions 0, extractions ()) and prints parse: [] / align: []
result: pass
coverage_id: 04-03-D6

### 15. Walkthrough via trace_probes
expected: Same walkthrough through trace_probes(wrappers=make_stage_wrappers(sink, config)) with originals restored on success and exception (Tests R-T)
result: pass
coverage_id: 04-03-D7

## Summary

total: 15
passed: 15
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
