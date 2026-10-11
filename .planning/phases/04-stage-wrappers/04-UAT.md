---
status: testing
phase: 04-stage-wrappers
source:
  - 04-VERIFICATION.md
started: 2026-10-11T08:25:00Z
updated: 2026-10-11T08:25:00Z
---

## Current Test

number: 1
name: Read the five-stage printed walkthrough
expected: |
  Raw model text appears only under [model] (and as input under [parse]);
  flags + callout are under [parse] next to the raw text; offsets/slices/ungrounded
  are under [align]; the output is readable.
awaiting: user response

## Tests

### 1. Read the five-stage printed walkthrough
expected: Print the walkthrough from one offline extract (via `_patch_stages` or an equivalent script) for three replies — canned, `not json`, and `{"extractions": []}` — and confirm raw model text under [model]/flags/callout under [parse]; offsets/spans/slices or ungrounded under [align]; layout acceptable.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
