---
status: testing
phase: 01-stage-catalog-contracts
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md]
started: 2026-10-10T15:08:18Z
updated: 2026-10-10T15:08:18Z
---

## Current Test

number: confirm
name: Confirm automated coverage
expected: |
  All Phase 1 deliverables are covered by passing automated verification.
  User confirms the catalog run and contracts match expectations.
awaiting: user response

## Tests

### 1. Static call header from config.yaml (lx.extract, model_id, provider, model_url host)
expected: Static call header from config.yaml (lx.extract, model_id, provider, model_url host)
result: pass
source: automated
coverage_id: D1
plan: 01-01

### 2. Seven ordered stage headers with align helper and blank-line separation
expected: Seven ordered stage headers with align helper and blank-line separation
result: pass
source: automated
coverage_id: D2
plan: 01-01

### 3. Observation stays in script + YAML only (no langextract/ or demo_ollama edits)
expected: Observation stays in script + YAML only (no langextract/ or demo_ollama edits)
result: pass
source: automated
coverage_id: D3
plan: 01-01

### 4. Missing config.yaml fails closed with exit 1 via load_config
expected: Missing config.yaml fails closed with exit 1 via load_config
result: pass
source: automated
coverage_id: D4
plan: 01-01

### 5. empty_parse_message present in config and absent from catalog stdout
expected: empty_parse_message present in config and absent from catalog stdout
result: pass
source: automated
coverage_id: D1
plan: 01-02

### 6. redact_keys matches debug_utils eight names in order
expected: redact_keys matches debug_utils eight names in order
result: pass
source: automated
coverage_id: D2
plan: 01-02

### 7. redact() masks sensitive keys case-insensitively including one nested level
expected: redact() masks sensitive keys case-insensitively including one nested level
result: pass
source: automated
coverage_id: D3
plan: 01-02

### 8. Catalog stdout unchanged (header + seven stages, exit 0)
expected: Catalog stdout unchanged (header + seven stages, exit 0)
result: pass
source: automated
coverage_id: D4
plan: 01-02

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0
awaiting_confirmation: true

## Gaps

[none yet]
