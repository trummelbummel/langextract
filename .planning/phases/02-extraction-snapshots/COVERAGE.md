# Phase 2: Extraction snapshots — API Coverage

No external API integration: this phase adds pure field-copy helpers (`ExtractionSnapshot`, `snapshot_extractions`, `print_grounding_pair`) to `scripts/trace_extract.py` and one `config.yaml` display key. Tests exercise the in-repo `langextract.resolver.Resolver.resolve` / `Resolver.align` offline on canned JSON. There is no Ollama HTTP call, no `lx.extract` call, no network access, and no new dependency. External integration (local Ollama `gemma3:4b`) starts in Phase 5.
