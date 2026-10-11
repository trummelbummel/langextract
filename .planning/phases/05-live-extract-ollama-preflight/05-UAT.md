---
status: testing
phase: 05-live-extract-ollama-preflight
source:
  - 05-VERIFICATION.md
started: 2026-10-11T15:45:00Z
updated: 2026-10-11T15:45:00Z
---

## Current Test

number: 1
name: Live walkthrough with Ollama and gemma3:4b
expected: |
  Exit 0; stage sections with live in/out; last line
  `run: 1 lx.extract, 1 OllamaLanguageModel.infer (1 prompt)`
awaiting: user response

## Tests

### 1. Live walkthrough with Ollama and gemma3:4b
expected: Exit 0; stage sections with live in/out; last line `run: 1 lx.extract, 1 OllamaLanguageModel.infer (1 prompt)`
result: [pending]
why_human: Harvested from 05-02 PLAN human-check; readability of the live walkthrough is a judgment call even when automated exit/line checks pass

### 2. Fail-closed UX when Ollama is down
expected: Exit 1; one `Error:` line on stderr naming the host/fix; empty stdout (no header, no stage sections)
result: [pending]
why_human: Harvested from 05-02 PLAN human-check; confirms the fail-closed UX the developer actually sees

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
