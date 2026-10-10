# Phase 4 API Coverage

No external API integration: Phase 4 adds read-only wrappers around five methods `lx.extract()` already calls (`ChunkIterator.__iter__`, `ContextAwarePromptBuilder.build_prompt`, `OllamaLanguageModel.infer`, `Resolver.resolve`, `Resolver.align`) plus stdout printers. Every test runs the real local pipeline offline with only `OllamaLanguageModel._ollama_query` patched in the test, so no network request, Ollama endpoint, or new external service is used. The live Ollama `/api/generate` call is Phase 5's.
