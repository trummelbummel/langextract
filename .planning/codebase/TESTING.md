---
last_mapped_commit: a4c0aa4c1be98f441ffc7e1d0f85b1067748e1f3
last_mapped_at: 2026-10-09
---
# Testing Patterns

**Analysis Date:** 2026-10-09

## Test Framework

**Runner:**

- `pytest>=7.4.0` collects and runs tests. Declared in the `test` extra of `pyproject.toml` (`pip install -e ".[test]"`). `tomli>=2.0.0` is the other test extra.
- Test bodies are `unittest`-style. Almost every module subclasses `absl.testing.absltest.TestCase` or `absl.testing.parameterized.TestCase` (`tests/factory_test.py`, `tests/resolver_test.py`, `tests/gemini_retry_test.py`). `parameterized.TestCase` is an absl `TestCase`, so `self.assertLen` and `self.enter_context` are available.
- A minority subclass `unittest.TestCase` directly: `tests/io_test.py`, `tests/progress_test.py`, `tests/test_live_api.py`, and part of `tests/test_kwargs_passthrough.py`. Use absl when the file needs `parameterized` or absl assertions.
- Config: `pyproject.toml` `[tool.pytest.ini_options]`. There is no `pytest.ini`, `conftest.py`, or `tox.ini` pytest override beyond the command line in `tox.ini`.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = "Test*"
python_functions = "test_*"
addopts = "-ra"
markers = [
    "live_api: marks tests as requiring live API access",
    "vertex_ai: marks live tests that require Vertex AI credentials",
    "requires_pip: marks tests that perform pip install/uninstall operations",
    "integration: marks integration tests that test multiple components together",
]
```

**Assertion Library:**

- `absl.testing.absltest` assertions on top of `unittest`. Prefer absl helpers when the case is an absl `TestCase`:
  - `self.assertEqual`, `self.assertIs`, `self.assertIsNone`, `self.assertIsInstance`, `self.assertTrue` / `self.assertFalse`
  - `self.assertLen`, `self.assertStartsWith`, `self.assertEmpty` (used in `tests/create_provider_plugin_test.py` and `tests/factory_test.py`)
  - `self.assertRaisesRegex(exc, "regex")` for error text (`tests/tokenizer_test.py`, `tests/resolver_test.py`)
  - `self.assertWarns` / `self.assertWarnsRegex` for `UserWarning` and `FutureWarning` (`tests/extract_precedence_test.py`, `tests/schema_test.py`)
- Plain `assert` is rare and only inside helper functions that are not test methods (`assert_char_interval_match_source` in `tests/resolver_test.py`). Test methods call `self.assert*`.

**Run Commands:**

```bash
pip install -e ".[test]"          # pytest only
pytest tests                      # everything pytest collects, including live/integration if not deselected
pytest -ra -m "not live_api and not requires_pip and not integration"   # default unit slice (what tox runs)

pip install -e ".[openai,dev,test]"
tox                               # py310, py311, py312, format, lint-src, lint-tests
tox -e py311                      # unit tests on one interpreter
tox -e lint-src                   # pylint --rcfile=.pylintrc langextract
tox -e lint-tests                 # pylint --rcfile=tests/.pylintrc tests
tox -e format                     # isort + pyink --check
tox -e live-api                   # tests/test_live_api.py -m live_api (needs API keys)
tox -e ollama-integration         # tests/test_ollama_integration.py
tox -e plugin-smoke               # tests/provider_plugin_test.py::PluginSmokeTest
tox -e plugin-integration         # PluginE2ETest + create_provider_plugin_test.py -m requires_pip

python tests/factory_test.py     # absltest.main() / unittest.main() at the bottom of each file
```

CI (`.github/workflows/ci.yaml`) runs, per Python 3.10/3.11/3.12: `tox -e py${PY_VERSION},lint-src,lint-tests`. Format and `lint-imports` are a separate `format-check` job. `live-api-tests` runs `tox -e live-api` on same-repo PRs and pushes when `GEMINI_API_KEY` or `OPENAI_API_KEY` is configured, and skips cleanly when neither secret is set. Fork PRs do not receive those secrets; a maintainer dispatches live tests from `main` (see `CONTRIBUTING.md`).

`tox.ini` sets `PYTHONWARNINGS = ignore` on the default unit env. A test that only fails when a warning is emitted will pass under tox and still be visible under a bare `pytest`. Assert the warning explicitly (below) instead of relying on filter settings.

## Test File Organization

**Location:**

- All automated tests live in `tests/` at the repo root. They are not co-located with `langextract/`. `pyproject.toml` `[tool.setuptools.exclude-package-data]` excludes `tests*` from the wheel.
- `examples/custom_provider_plugin/test_example_provider.py` is a manual script (`def main()`), not a pytest module. `testpaths = ["tests"]` keeps pytest from collecting it. Do not put CI tests there.
- `benchmarks/` (`benchmarks/benchmark.py`, `benchmarks/fuzzy_benchmark.py`) is not part of the suite.
- There is no `conftest.py` and no shared `tests/fixtures/` package. Helpers sit in the test module that uses them.

**Naming:**

- Match the library module: `langextract/resolver.py` → `tests/resolver_test.py`, `langextract/annotation.py` → `tests/annotation_test.py`.
- Existing `test_*.py` files are the live/integration/kwargs suites: `tests/test_live_api.py`, `tests/test_ollama_integration.py`, `tests/test_gemini_batch_api.py`, `tests/test_kwargs_passthrough.py`. New unit tests use `*_test.py`.
- Class names describe the slice: `FactoryTest`, `ParserTest`, `TestGeminiRetryableErrors`, `PluginSmokeTest`. A leading `Test` is what pytest's `python_classes = "Test*"` filter expects for classes that are not `unittest.TestCase`. Subclassing `absltest.TestCase` or `unittest.TestCase` is collected regardless; still name the class `...Test` or `Test...`.
- Private bases and helpers start with `_`: `_MockClientTest` and `_build_model` in `tests/gemini_retry_test.py`, `_configure_openai_mock` in `tests/test_kwargs_passthrough.py`, `_CreateProviderPluginTestBase` in `tests/create_provider_plugin_test.py`.

**Structure:**

```
tests/
├── factory_test.py                  # unit: factory + routing
├── resolver_test.py                 # unit: parse + alignment
├── gemini_retry_test.py             # unit: retry classification
├── init_test.py                     # lx.extract with a mocked model
├── provider_plugin_test.py          # PluginSmokeTest + PluginE2ETest
├── create_provider_plugin_test.py   # generator script; some methods marked requires_pip
├── test_live_api.py                 # @pytest.mark.live_api
├── test_ollama_integration.py       # pytest functions, marker integration
└── .pylintrc                        # test-only pylint relaxations
```

Each file ends with a script entry so it can run without pytest:

```python
if __name__ == "__main__":
  absltest.main()
```

`tests/io_test.py` and `tests/progress_test.py` call `unittest.main()` instead. `tests/test_live_api.py` and `tests/test_ollama_integration.py` have no `__main__` block; run them through pytest.

## Test Structure

**Suite Organization:**

Default unit case (`tests/factory_test.py`):

```python
class OpenAIRoutingExtractionTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    router.clear()
    self.addCleanup(router.clear)
    self.enter_context(
        mock.patch.object(providers, "load_plugins_once", autospec=True)
    )

  @parameterized.named_parameters(
      dict(
          testcase_name="fallback",
          env={"LANGEXTRACT_API_KEY": "fallback"},
          kwargs={},
          expected="fallback",
      ),
  )
  def test_reasoning_model_key_precedence(self, env, kwargs, expected):
    with mock.patch.dict(os.environ, env, clear=True):
      result = factory._kwargs_with_environment_defaults("o3-mini", kwargs)
    self.assertEqual(result["api_key"], expected)
```

Error table (`tests/resolver_test.py`):

```python
@parameterized.named_parameters(
    dict(
        testcase_name="json_invalid_input",
        resolver=resolver_lib.Resolver(
            format_type=data.FormatType.JSON,
            fence_output=True,
            strict_fences=True,
        ),
        input_text="invalid input",
        expected_exception=resolver_lib.ResolverParsingError,
        expected_regex=".*fence markers.*",
    ),
)
def test_parser_error_cases(
    self, resolver, input_text, expected_exception, expected_regex
):
  with self.assertRaisesRegex(expected_exception, expected_regex):
    resolver.string_to_extraction_data(input_text)
```

**Patterns:**

- One `TestCase` subclass per behavior group. A file holds several classes (`ParserTest`, `ExtractOrderedEntitiesTest`, `AlignEntitiesTest` in `tests/resolver_test.py`).
- `setUp` always calls `super().setUp()`. Tear down with `self.addCleanup(...)`, not `tearDown`, so cleanup runs when `setUp` itself fails. `tests/factory_test.py` clears `router` this way. `tests/gemini_retry_test.py` starts a `mock.patch` in `setUp` and `addCleanup(patcher.stop)`.
- `self.enter_context(patch)` (absl) is the preferred way to apply a patch for the whole test (`tests/annotation_test.py` patches `gemini.GeminiLanguageModel`).
- Parameterize with `@parameterized.named_parameters` and a `dict` whose first conceptual key is `testcase_name`. The name is snake_case and shows up in the pytest node id. Do not use `@pytest.mark.parametrize` in unit files.
- Build fenced model output with `textwrap.dedent` (`tests/init_test.py`) so the golden JSON stays readable inside the 80-column limit.
- Docstrings on test methods are optional (`tests/.pylintrc` disables `missing-function-docstring`). Add one when the name cannot carry the regression (`tests/test_ollama_integration.py` documents a provider-resolution bug). `tests/progress_test.py` uses a one-line docstring per method; either style is fine.
- Mark expensive tests on the method, not the module, unless the whole module is integration (`pytestmark = pytest.mark.integration` at the top of `tests/test_ollama_integration.py`).

## Mocking

**Framework:** `unittest.mock` (`from unittest import mock`). No `pytest-mock`, no `responses`, no `respx`.

**Patterns:**

Patch the symbol where it is used, with `autospec=True` when the object has a real interface:

```python
@mock.patch.object(openai_sdk, "OpenAI", autospec=True)
def test_extract_with_environment_key(self, mock_client_class, model_id):
  client = mock_client_class.return_value
  ...
```

(`tests/factory_test.py`)

Patch a function on the defining module when the code under test looks it up there:

```python
@mock.patch.object(openai_batch, "infer_batch", autospec=True)
@mock.patch("openai.OpenAI", autospec=True)
def test_infer_batch_reuses_structured_output_params(
    self, mock_openai_class, mock_infer_batch
):
  ...
```

(`tests/test_kwargs_passthrough.py`)

Environment isolation is `mock.patch.dict(os.environ, env, clear=True)` so a developer key on the machine cannot leak in (`tests/factory_test.py`).

Model inference doubles return the real scored-output shape, not a bare string:

```python
mock_model = mock.MagicMock()
mock_model.infer.return_value = [[
    types.ScoredOutput(output=textwrap.dedent("""\
        ```json
        { "extractions": [] }
        ```"""), score=0.9)
]]
mock_model.requires_fence_output = True
```

(`tests/init_test.py`)

SDK responses that the provider reads as attributes should be autospecced from the real type:

```python
response = mock.create_autospec(
    genai.types.GenerateContentResponse, instance=True
)
response.text = text
```

(`tests/gemini_retry_test.py`)

When the router must instantiate a class, write a `Fake*` subclass of `base_model.BaseLanguageModel` with `infer` / `infer_batch` instead of a `MagicMock` (`FakeGeminiProvider`, `FakeOpenAIProvider` in `tests/factory_test.py`). Register it in the test and `addCleanup` the registry clear.

HTTP is patched at the client boundary: `requests.post` (`tests/test_kwargs_passthrough.py`), `genai.Client` (`tests/gemini_retry_test.py`), `openai.OpenAI`.

**What to Mock:**

- Network and SDK clients (`google.genai`, `openai`, `requests`, GCS clients in `tests/test_gemini_batch_api.py`).
- `langextract.providers.load_plugins_once` when the test registers its own fake and must not discover installed plugins (`tests/factory_test.py`).
- Time/sleep in retry tests so backoff does not make the suite slow (patch `time.sleep` in the provider module if a test drives the retry loop).
- `importlib.metadata.entry_points` when asserting plugin discovery without installing a package (`tests/provider_plugin_test.py`).

**What NOT to Mock:**

- `langextract.core.data` classes, the tokenizer, or the resolver alignment logic when that is the behavior under test. Pass real `ExampleData` / `Extraction` / `CharInterval`.
- `router.resolve` in an extraction test that is specifically about routing. Mock the provider class instead and let resolution run (`tests/factory_test.py` `test_extract_with_environment_key`).
- Filesystem path logic in plugin-generator tests. Use a real `tempfile.TemporaryDirectory` (`tests/create_provider_plugin_test.py`).

## Fixtures and Factories

**Test Data:**

- There is no pytest fixture library. The only `@pytest.fixture` is the autouse rate-limit delay in `tests/test_live_api.py`:

```python
@pytest.fixture(autouse=True)
def add_delay_between_tests():
  """Add a small delay between tests to avoid rate limiting."""
  yield
  time.sleep(0.5)
```

  Do not add autouse fixtures to unit modules. They change timing for every test in the file and are invisible to `absltest.main()`.

- Shared inputs are plain functions: `get_basic_medication_examples()` in `tests/test_live_api.py`, `_condition_examples()` in `tests/test_kwargs_passthrough.py`, `_build_model(**overrides)` and `_make_response(text)` in `tests/gemini_retry_test.py`.
- Few-shot examples use the public dataclasses:

```python
data.ExampleData(
    text="Alice arrived.",
    extractions=[
        data.Extraction(
            extraction_class="person", extraction_text="Alice"
        )
    ],
)
```

- Golden JSON strings go through `textwrap.dedent` with an explicit ```` ```json ```` fence when `fence_output=True`.

**Location:**

- Helpers live at module scope in the test file that uses them, below the imports and above the first test class (`tests/resolver_test.py` `assert_char_interval_match_source`, `tests/gemini_retry_test.py`).
- Cross-file fixtures are not used. Duplicate a small example rather than importing another test module.
- Temp dirs: `tempfile.mkdtemp()` plus `self.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)`, or `with tempfile.TemporaryDirectory()` (`tests/create_provider_plugin_test.py`).

## Coverage

**Requirements:** None enforced. `pyproject.toml` has no `[tool.coverage.*]` and no `pytest-cov` dependency. `addopts` is only `-ra` (short summary of skips and xfails). Do not add a coverage gate as part of a feature change.

**View Coverage:**

- Not configured. A local one-off is `pytest --cov=langextract --cov-report=term-missing tests` only if the developer has installed `pytest-cov` themselves. CI will not run it.
- `pytype` is a `dev` extra and `# pytype: disable=` comments exist, but no tox env or CI job runs pytype. Type regressions are not gated.

## Test Types

**Unit Tests:**

- Default path. `tox.ini` `[testenv]` runs:

```bash
pytest -ra -m "not live_api and not requires_pip and not integration"
```

- Cover pure functions and pipeline stages with a fake or mocked model: tokenization (`tests/tokenizer_test.py`), chunking (`tests/chunking_test.py`), prompting (`tests/prompting_test.py`), resolving and alignment (`tests/resolver_test.py`, `tests/fuzzy_alignment_cases_test.py`), schema conversion (`tests/schema_test.py`), factory routing (`tests/factory_test.py`), and `lx.extract` with `mock.patch` on `factory.create_model` (`tests/init_test.py`).
- Provider unit tests construct the provider with a fake API key and patch the SDK (`tests/inference_test.py`, `tests/gemini_retry_test.py`, `tests/openai_batch_test.py`, `tests/test_gemini_batch_api.py`). They must not call the network.

**Integration Tests:**

- Marker `integration`. Excluded from the default tox env.
- `tests/test_ollama_integration.py` is pytest function tests, not absl classes. Module marker: `pytestmark = pytest.mark.integration`. Each test is also `@pytest.mark.skipif(not _ollama_available(), ...)`. `_ollama_available` probes `localhost:11434` with a socket. Run with `tox -e ollama-integration`. The test needs a local `gemma2:2b` model (`README.md`).
- `tests/provider_plugin_test.py::PluginE2ETest.test_pip_install_discovery_and_cleanup` is marked both `requires_pip` and `integration`. It skips itself under Bazel (`TEST_TMPDIR` / `BUILD_WORKING_DIRECTORY`) via `self.skipTest`. `PluginSmokeTest` stays in the default unit run (`tox -e plugin-smoke`).
- `tests/create_provider_plugin_test.py` mixes unit tests of the generator with `@pytest.mark.requires_pip` methods. The pip subset runs only in `tox -e plugin-integration`.

**E2E Tests:**

- Live API: `tests/test_live_api.py`. Classes are `unittest.TestCase`. Every live method is decorated `@live_api` (`pytest.mark.live_api`) and a skip marker:

```python
skip_if_no_gemini = pytest.mark.skipif(
    not GEMINI_API_KEY,
    reason="Gemini API key not available (set GEMINI_API_KEY or LANGEXTRACT_API_KEY)",
)
```

  Keys are read at import from `GEMINI_API_KEY` or `LANGEXTRACT_API_KEY`, `OPENAI_API_KEY`, and `LANGEXTRACT_RUN_OPENAI_BATCH_LIVE_TESTS == "1"`. Vertex cases use `@pytest.mark.vertex_ai` plus `skip_if_no_vertex` (`VERTEX_PROJECT` / `GOOGLE_CLOUD_PROJECT` and `google.auth.default()`). `dotenv.load_dotenv(override=True)` runs at import so a local `.env` can supply keys; do not commit that file.
- `tox -e live-api` is `pytest tests/test_live_api.py -v -m live_api --maxfail=1` on Python 3.11. It passes through `GEMINI_API_KEY`, `LANGEXTRACT_API_KEY`, `OPENAI_API_KEY`, `LANGEXTRACT_RUN_OPENAI_BATCH_LIVE_TESTS`, and the Google/Vertex credential variables (`tox.ini` `passenv`).
- Live tests retry transient `LangExtractError`, `ClientError`, `ConnectionError`, `TimeoutError`, `OSError`, and `RuntimeError` with exponential backoff (`INITIAL_RETRY_DELAY`, `MAX_RETRY_DELAY` in `tests/test_live_api.py`). Keep that decorator on new live methods that hit the network. Do not add retries to unit tests.
- No browser or UI end-to-end suite.

## Common Patterns

**Async Testing:**

- The library inference API is synchronous (`Iterator` of scored outputs). There is no `pytest-asyncio` and no `async def` test. Do not introduce async tests for a sync provider. Concurrent behavior is tested by patching the executor or by asserting `max_workers` / `batch_length` wiring in `tests/annotation_test.py`.

**Error Testing:**

```python
with self.assertRaisesRegex(
    tokenizer.InvalidTokenIntervalError,
    "Invalid token interval.*start_index=-1",
):
  tokenizer.tokens_text(
      tokenized, tokenizer.TokenInterval(start_index=-1, end_index=1)
  )
```

(`tests/tokenizer_test.py`)

Match a stable substring of the message, not the whole sentence. Use the exception type the caller is supposed to see (`exceptions.InferenceConfigError`, `resolver_lib.ResolverParsingError`), not the internal `ValueError` that was chained, unless the test is specifically about the unwrapped path.

Warnings:

```python
with self.assertWarns(FutureWarning):
  ...

with warnings.catch_warnings(record=True) as w:
  warnings.simplefilter("always")
  ...
self.assertTrue(any("localhost" in str(warning.message) for warning in w))
```

(`tests/extract_precedence_test.py`, `tests/test_kwargs_passthrough.py`). `simplefilter("always")` is required because `tox.ini` sets `PYTHONWARNINGS=ignore`.

**Registry isolation:**

- Tests that register a provider call `router.clear()` in `setUp` and `self.addCleanup(router.clear)`. Plugin tests also reset `lx.providers._plugins_loaded` and clean `sys.path` (`tests/create_provider_plugin_test.py`). Leaving a registration in place leaks into later tests in the same process.

**Skip vs marker:**

- Environmental absence uses `@pytest.mark.skipif` (no API key, Ollama port closed) so the test is reported as skipped (`-ra` prints the reason).
- Platform absence inside a method uses `self.skipTest("...")` (symlinks, Bazel sandbox).
- Costly opt-in behavior uses a marker the default tox command deselects (`live_api`, `requires_pip`, `integration`). A new test that shells out to pip or calls a paid API must carry the marker or it will run in CI unit jobs.

**Pylint in tests:**

- `tests/.pylintrc` allows protected access, missing docstrings, duplicate fixtures, `invalid-name` (`setUp`, `maxDiff`), unused mock callback args, and higher complexity (`max-statements = 75`, `max-locals = 25`). Still keep a test method focused on one assertion story. A `# pylint: disable=protected-access` on a single line is enough when the parent rc is not what is running.

---

*Testing analysis: 2026-10-09*
