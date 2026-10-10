# Phase 1: Stage catalog & contracts - Context

**Gathered:** 2026-10-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a runnable `scripts/trace_extract.py` that prints the seven-stage contract (stable labels + owning function/file) and a static call header, with call/copy constants loaded from repo-root `config.yaml`. No Ollama call, no live in/out payloads, no edits under `langextract/` or `examples/ollama/demo_ollama.py`.

</domain>

<decisions>
## Implementation Decisions

### Phase-1 run output
- **D-01:** Running the script prints catalog only: seven stage sections with owners; no footer about later phases.
- **D-02:** Stage sections are header-only in this phase — omit `in:` / `out:` lines until later phases capture records.
- **D-03:** Successful catalog print exits 0.
- **D-04:** Blank line between stage sections on stdout.

### Section formatting
- **D-05:** Stage header form: `[label] function — path` on one line (bracketed label, em dash before path).
- **D-06:** Paths are repo-relative (e.g. `langextract/prompting.py`), not module-style.
- **D-07:** One primary function + one primary file per stage header (even when research lists two files).
- **D-08:** Under `[align]`, print one helper line: `helper: WordAligner.align_extractions` (not its own stage).

### Call header & config
- **D-09:** Print a static call header in Phase 1 (no network): `lx.extract`, `model_id=gemma3:4b`, `OllamaLanguageModel`, host.
- **D-10:** All constants live in repo-root `config.yaml`, not as Python literals — including the extraction prompt when it is added later. — **Reversibility:** costly — undoing means every later phase already reads YAML keys; script and planners assume this layout.
- **D-11:** Phase 1 `config.yaml` holds call constants only (`model_id`, `model_url`, provider display name). Prompt text is deferred until the live-extract phase.
- **D-12:** Allowed Phase 1 files include `scripts/trace_extract.py` **and** repo-root `config.yaml` (roadmap success criterion that said “only the script” is superseded by D-10/D-12).

### Empty-parse copy & redaction
- **D-13:** Empty-parse sentence lives in `config.yaml` now (research-aligned wording: chunk omitted on parse/schema error; keep raw model text above). Not printed until parse has live data.
- **D-14:** `redact_keys` in `config.yaml` matches `langextract/core/debug_utils.py` (`api_key`, `apikey`, `token`, `secret`, `password`, `authorization`, `bearer`, `jwt`).
- **D-15:** Phase 1 includes a small `redact()` helper stub in the script that uses that key list (ready for later printer payloads).

### Claude's Discretion
- Stage catalog primary owners: take the primary function/file from `.planning/research/FEATURES.md` stage map when research lists multiple files.
- Exact YAML key names for header fields and empty-parse string — choose clear names consistent with `model_id` / `model_url`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & requirements
- `.planning/PROJECT.md` — core value, script-only milestone, Ollama `gemma3:4b`
- `.planning/REQUIREMENTS.md` — CTR-01, CTR-02, STG-01, STG-02 for this phase
- `.planning/ROADMAP.md` — Phase 1 goal and success criteria (file-touch list updated by D-12)
- `CLAUDE.md` — per-task diff budget (~150 non-test lines / ≤3 source files)

### Research (stage contract)
- `.planning/research/FEATURES.md` — stage labels, owners, empty-parse / redaction table stakes
- `.planning/research/ARCHITECTURE.md` — catalog + printer before extract; plain stdout
- `.planning/research/STACK.md` — `model_url` default `http://localhost:11434`; `OLLAMA_BASE_URL` ignored for `gemma3:4b`
- `.planning/research/SUMMARY.md` — Phase 1 rationale (catalog/printer/contracts)

### Codebase
- `.planning/codebase/STRUCTURE.md` — `scripts/` is maintainer CLIs via `python scripts/...`, not console entry points
- `langextract/core/debug_utils.py` — canonical `_REDACT_KEYS` set to mirror in config

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/create_provider_plugin.py` / `scripts/validate_community_providers.py`: pattern for `python scripts/...` maintainer tools (shebang + main), not packaged.
- `langextract/core/debug_utils.py`: `_REDACT_KEYS` list to mirror in `config.yaml` (do not import private helpers if avoidable — copy the key names into config).

### Established Patterns
- PyYAML already used in the library; script may load `config.yaml` with `yaml.safe_load` (library dependency available in editable install).
- Stage labels locked: `prompt-template`, `chunk`, `prompt`, `model`, `parse`, `align`, `annotated-document`.

### Integration Points
- New files: `scripts/trace_extract.py`, repo-root `config.yaml`.
- No integration into `langextract/` package or `examples/ollama/demo_ollama.py`.

</code_context>

<specifics>
## Specific Ideas

- Header line example shape: `[prompt-template] ContextAwarePromptBuilder.build_prompt — langextract/prompting.py`
- Align helper line: `helper: WordAligner.align_extractions`
- User rule: “any constant needs to go into config.yaml including the extraction prompt”

</specifics>

<deferred>
## Deferred Ideas

- Extraction prompt / examples structure in `config.yaml` — live-extract phase (Phase 5)
- Live `in:` / `out:` printing — Phase 4+
- Ollama preflight / network — Phase 5
- Printing the empty-parse sentence on stdout — when parse stage has live data (Phase 4+)

None — discussion stayed within phase scope for deferred product ideas.

</deferred>

---

*Phase: 1-Stage catalog & contracts*
*Context gathered: 2026-10-10*
