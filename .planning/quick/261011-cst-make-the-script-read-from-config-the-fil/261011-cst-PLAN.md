---
phase: 261011-cst
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - config.yaml
  - scripts/trace_extract.py
  - tests/trace_extract_test.py
  - Makefile
autonomous: true
requirements:
  - QUICK-DOC-01
  - QUICK-CHUNK-01
user_setup: []

estimate:
  tokens: 35000
  raw_tokens: 35000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "config.yaml names the live document as data/example_document.md and the script loads that file for text_or_documents"
    - "_extract_kwargs passes max_char_buffer and context_window_chars from config into lx.extract"
    - "Offline unit tests cover filepath loading and chunk kwargs without network or Ollama"
    - "make trace runs the script with no positional document argument (config is source of truth)"
  prohibitions:
    - "Must NOT add a new CLI document flag or positional argument"
    - "Must NOT edit langextract/ or examples/"
    - "Must NOT hit the network in new/updated unit tests"
  artifacts:
    - path: config.yaml
      provides: "document_path plus max_char_buffer and context_window_chars call constants"
      contains: "document_path"
    - path: scripts/trace_extract.py
      provides: "repo-root document load + chunk kwargs in _extract_kwargs"
      contains: "document_path"
    - path: tests/trace_extract_test.py
      provides: "offline coverage for document load and chunk kwargs"
      contains: "document_path"
    - path: Makefile
      provides: "trace target without TRACE_DOCUMENT positional"
      contains: "trace_extract.py"
  key_links:
    - from: "config.yaml document_path"
      to: "_extract_kwargs text_or_documents"
      via: "read file relative to _REPO_ROOT"
      pattern: "document_path"
    - from: "config.yaml max_char_buffer / context_window_chars"
      to: "lx.extract(**_extract_kwargs(config))"
      via: "keys included in the kwargs dict"
      pattern: "max_char_buffer"
---

<objective>
Make the live trace script take its document and chunking settings from config.yaml.

Purpose: Config is the source of truth for which file is extracted and how it is chunked, so `make trace` / `python scripts/trace_extract.py` do not need a CLI document path.
Output: Updated config keys, `_extract_kwargs` / document loading in the script, offline tests, Makefile aligned with config-only document selection.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@config.yaml
@scripts/trace_extract.py
@tests/trace_extract_test.py
@Makefile
@data/example_document.md
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Config document_path → text_or_documents</name>
  <files>config.yaml, scripts/trace_extract.py, tests/trace_extract_test.py, Makefile</files>
  <read_first>
    - config.yaml (sample_text and surrounding call constants)
    - scripts/trace_extract.py (load_config, _extract_kwargs, run_live, main — no positional document arg today)
    - tests/trace_extract_test.py (TraceExtractLiveTest.setUp / test_extract_kwargs_pins_local_ollama_call / test_run_live_walks_one_extract_against_stub — stub expects one /api/generate)
    - Makefile (TRACE_DOCUMENT positional on trace target)
    - data/example_document.md (exists; ~32KB — too long for one chunk at library default 1000)
  </read_first>
  <behavior>
    - Test: config mapping with document_path pointing at a temp UTF-8 file → _extract_kwargs(config)["text_or_documents"] equals that file's exact contents (not sample_text)
    - Test: document_path relative to repo root resolves via _REPO_ROOT even when cwd is elsewhere (chdir to temp, still loads)
    - Test: missing document file → SystemExit(1) and stderr starts with Error: and mentions the resolved path
    - Update existing TraceExtractLiveTest / any test that calls _extract_kwargs or run_live against load_config(_CONFIG_PATH): point document_path at a short temp file (or override in the test config dict) so the stub still sees exactly one /api/generate — do not leave those tests reading the 32KB example doc unintentionally
  </behavior>
  <action>
    Per locked intent: add top-level config key document_path: data/example_document.md. Remove sample_text from config.yaml (nothing else uses it once _extract_kwargs stops reading it). In scripts/trace_extract.py add a small helper (e.g. _load_document_text) that resolves document_path against _REPO_ROOT when relative, reads UTF-8 text, and on missing file prints one Error: line to stderr with the resolved path then raises SystemExit(1). Change _extract_kwargs so text_or_documents is that loaded text (not config sample_text). Do not add CLI document override — main() already has only --catalog-only; leave argparse unchanged. Align Makefile: drop TRACE_DOCUMENT and the positional argument from the trace recipe so it invokes scripts/trace_extract.py with no document path (config owns the file). Estimated diff: ~40 non-test lines across 3 source files (config.yaml, scripts/trace_extract.py, Makefile).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/trace_extract_test.py -q --tb=line -k "extract_kwargs or document or run_live or catalog_only" 2>&1 | tail -20</automated>
  </verify>
  <done>Live kwargs text comes from config document_path file contents; missing path fails closed; Makefile trace uses config only; offline tests cover load + existing live stub still passes with a short temp document.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Config-driven max_char_buffer and context_window_chars</name>
  <files>config.yaml, scripts/trace_extract.py, tests/trace_extract_test.py</files>
  <read_first>
    - scripts/trace_extract.py (_extract_kwargs after Task 1)
    - langextract/extraction.py extract signature (max_char_buffer default 1000, context_window_chars default None)
    - config.yaml (document_path from Task 1)
    - tests/trace_extract_test.py (Task 1 document tests; TraceExtractLiveTest stub one-generate contract)
  </read_first>
  <behavior>
    - Test: config with max_char_buffer and context_window_chars set → _extract_kwargs includes those exact values as top-level kwargs keys
    - Test: context_window_chars: null (YAML null / Python None) → kwargs contain context_window_chars is None (key present, value None)
    - Existing stub live test still returns 0 with one /api/generate when using a short temp document and the configured buffer
  </behavior>
  <action>
    Per locked intent: add max_char_buffer and context_window_chars to config.yaml. Discretion: set max_char_buffer: 1000 and context_window_chars: null to match library defaults while making both explicit and editable; comment briefly that the example document is multi-chunk at 1000 and operators raise max_char_buffer to force one chunk if desired. In _extract_kwargs, pass both keys through into the returned dict for lx.extract. Do not change library code. Do not expand CLI. Estimated diff: ~15 non-test lines across 2 source files (config.yaml, scripts/trace_extract.py).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/trace_extract_test.py -q --tb=line 2>&1 | tail -30</automated>
  </verify>
  <done>_extract_kwargs forwards config chunking fields; offline suite green; no network in unit tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| config.yaml → filesystem read | document_path selects which file bytes become extract input |
| config.yaml → lx.extract kwargs | chunk sizes influence how much text is sent per Ollama call |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261011-01 | Tampering | document_path file read | low | accept | Local developer script; path comes from trusted repo config, not remote input |
| T-261011-02 | Information Disclosure | loaded document → Ollama | low | accept | Same trust model as prior sample_text; operator chooses the file |
| T-261011-SC | Tampering | npm/pip/cargo installs | high | accept | No new packages in this plan |
</threat_model>

<verification>
Full offline suite: `.venv/bin/python -m pytest tests/trace_extract_test.py -q`. Confirm config.yaml has document_path, max_char_buffer, context_window_chars and no sample_text. Confirm Makefile trace line has no positional document.
</verification>

<success_criteria>
- `_extract_kwargs` text_or_documents equals contents of config document_path (repo-relative)
- Chunk kwargs come from config
- Offline tests cover both behaviors; stub live test still one-generate with a short temp doc
- No new CLI document surface; no langextract/ or examples/ edits
</success_criteria>

<output>
Create `.planning/quick/261011-cst-make-the-script-read-from-config-the-fil/261011-cst-SUMMARY.md` when done
</output>
