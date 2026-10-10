# Walking Skeleton — LangExtract pipeline trace

**Phase:** 1
**Generated:** 2026-10-10

## Capability Proven End-to-End

A maintainer can run `python scripts/trace_extract.py` (no Ollama) and see a static call header from repo-root `config.yaml` plus the seven-stage ownership catalog on stdout, exiting 0.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Deliverable shape | Maintainer script `scripts/trace_extract.py` via `python scripts/...` | Script-only milestone; not a packaged console entry, not a library API |
| Runtime | CPython 3.12 + editable `langextract` | Matches project stack; script observes the installed library |
| Configuration | Repo-root `config.yaml` loaded with `yaml.safe_load` | D-10/D-12: all constants (including later prompt) live in YAML, not Python literals |
| Model target (declared, not called yet) | Local Ollama `gemma3:4b` at `model_url` | Locked milestone path; Phase 1 prints header only — no network |
| Observation style | Call-scoped class probes in later phases; Phase 1 is catalog + contracts only | Architecture build order: printer/contracts before probes before live extract |
| Directory layout | `scripts/trace_extract.py` + repo-root `config.yaml`; no files under `langextract/` | CTR-01/CTR-02; `examples/ollama/demo_ollama.py` untouched |

## Stack Touched in Phase 1

- [x] Script scaffold (shebang, Apache header, `main`, exit codes)
- [x] Repo-root YAML config load (`model_id`, `model_url`, `provider`)
- [x] Stdout catalog printer — seven `[label] function — path` lines + align helper
- [x] Static call header from config (no Ollama preflight yet)
- [ ] Database — N/A (not a web/data product)
- [ ] HTTP routing / UI — N/A
- [ ] Deployment — local run only: `python scripts/trace_extract.py`

## Out of Scope (Deferred to Later Slices)

- Live `in:` / `out:` payloads (Phase 4+)
- Extraction snapshots (Phase 2)
- Call-scoped probe manager and five method wraps (Phases 3–4)
- Ollama preflight and one `lx.extract()` (Phase 5)
- Printing returned `AnnotatedDocument` (Phase 6)
- Prompt/examples in `config.yaml` (Phase 5)
- Printing `empty_parse_message` on stdout (when parse has live data)
- Edits under `langextract/` or replacement of `examples/ollama/demo_ollama.py`

## Subsequent Slice Plan

Each later phase grows the same script (and YAML) without changing the skeleton decisions above:

- Phase 2: Extraction field snapshots (ungrounded vs grounded)
- Phase 3: Call-scoped probe manager with `finally` restore
- Phase 4: Live stage wrappers (chunk → align) writing records
- Phase 5: Ollama preflight + one `lx.extract()` against `gemma3:4b`
- Phase 6: Print `AnnotatedDocument` and close the walkthrough
