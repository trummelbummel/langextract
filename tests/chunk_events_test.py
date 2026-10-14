# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for per-chunk extraction observability events."""

from __future__ import annotations

import concurrent.futures
import logging
import textwrap
import threading
from typing import NamedTuple

from absl.testing import absltest
from absl.testing import parameterized

from langextract import annotation
from langextract import chunking
from langextract import prompting
from langextract import resolver as resolver_lib
import langextract as lx
from langextract.core import base_model
from langextract.core import data
from langextract.core import events
from langextract.core import tokenizer
from langextract.core import types

# Two sentences each → 2 chunks at max_char_buffer=40 (ChunkIterator).
_DOC_A_TEXT = (
    "Patient reports migraine headache. Doctor prescribed medication daily."
)
_DOC_B_TEXT = "First sentence is short. Second sentence is also short enough."
_BROKEN_MARKER = "MARKER_BROKEN"
_DOC_BROKEN_TEXT = (
    f"Patient reports migraine headache. {_BROKEN_MARKER} prescribed"
    " medication."
)
_MAX_CHAR_BUFFER = 40
_EMPTY_YAML = textwrap.dedent(f"""\
    ```yaml
    {data.EXTRACTIONS_KEY}: []
    ```""")
_VALID_YAML = textwrap.dedent(f"""\
    ```yaml
    {data.EXTRACTIONS_KEY}:
    - PATIENT: "Patient"
      PATIENT_index: 0
    ```""")


class _ExpectedChunk(NamedTuple):
  """Oracle chunk identity from ChunkIterator."""

  document_id: str
  chunk_index: int
  char_start: int | None
  char_end: int | None


def _expected_chunks(
    documents: list[data.Document],
) -> list[_ExpectedChunk]:
  """Oracle chunk identity fields via ChunkIterator."""
  tok = tokenizer.RegexTokenizer()
  expected = []
  for doc in documents:
    for index, chunk in enumerate(
        chunking.ChunkIterator(doc.text, _MAX_CHAR_BUFFER, tok, document=doc)
    ):
      interval = chunk.char_interval
      expected.append(
          _ExpectedChunk(
              document_id=doc.document_id,
              chunk_index=index,
              char_start=interval.start_pos,
              char_end=interval.end_pos,
          )
      )
  return expected


class _RecordingObserver:
  """Records events and the thread id of each callback invocation."""

  def __init__(self):
    self.events: list[events.ExtractionEvent] = []
    self.thread_ids: list[int] = []

  def __call__(self, event: events.ExtractionEvent) -> None:
    self.thread_ids.append(threading.get_ident())
    self.events.append(event)


class _ValidFakeModel(base_model.BaseLanguageModel):
  """Returns valid empty YAML for every prompt; records infer kwargs."""

  def __init__(self, output: str = _EMPTY_YAML):
    super().__init__()
    self.output = output
    self.infer_kwargs: list[dict] = []

  def infer(self, batch_prompts, **kwargs):
    self.infer_kwargs.append(dict(kwargs))
    return [
        [types.ScoredOutput(score=1.0, output=self.output)]
        for _ in batch_prompts
    ]


class _ThreadedFakeModel(base_model.BaseLanguageModel):
  """Runs prompts on a thread pool so max_workers>1 exercises workers."""

  def infer(self, batch_prompts, **kwargs):
    def _one(_prompt):
      return [types.ScoredOutput(score=1.0, output=_EMPTY_YAML)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
      futures = [pool.submit(_one, p) for p in batch_prompts]
      return [f.result() for f in futures]


class _UsageFakeModel(base_model.BaseLanguageModel):
  """Returns ScoredOutput with an optional TokenUsage."""

  def __init__(self, usage: types.TokenUsage | None):
    super().__init__()
    self.usage = usage

  def infer(self, batch_prompts, **kwargs):
    return [
        [types.ScoredOutput(score=1.0, output=_EMPTY_YAML, usage=self.usage)]
        for _ in batch_prompts
    ]


class _BrokenChunkFakeModel(base_model.BaseLanguageModel):
  """Returns broken JSON when the prompt contains _BROKEN_MARKER."""

  def infer(self, batch_prompts, **kwargs):
    results = []
    for prompt in batch_prompts:
      if _BROKEN_MARKER in prompt:
        results.append([types.ScoredOutput(score=1.0, output="{not json")])
      else:
        results.append([types.ScoredOutput(score=1.0, output=_EMPTY_YAML)])
    return results


def _make_annotator(
    model: base_model.BaseLanguageModel,
) -> annotation.Annotator:
  return annotation.Annotator(
      language_model=model,
      prompt_template=prompting.PromptTemplateStructured(description=""),
  )


def _two_docs() -> list[data.Document]:
  return [
      data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
      data.Document(text=_DOC_B_TEXT, document_id="doc-b"),
  ]


def _run_annotate(
    model: base_model.BaseLanguageModel,
    docs: list[data.Document],
    **overrides,
) -> _RecordingObserver:
  """Runs annotate_documents with shared defaults; returns the observer."""
  observer = overrides.pop("observer", None) or _RecordingObserver()
  kwargs = {
      "max_char_buffer": _MAX_CHAR_BUFFER,
      "batch_length": 1,
      "show_progress": False,
      "debug": False,
      "on_event": observer,
  }
  kwargs.update(overrides)
  list(_make_annotator(model).annotate_documents(docs, **kwargs))
  return observer


def _events_named(
    observer: _RecordingObserver, name: str
) -> list[events.ExtractionEvent]:
  return [event for event in observer.events if event.name == name]


class ChunkEventsTest(parameterized.TestCase):
  """Acceptance criteria for on_event chunk observability."""

  def test_one_started_and_finished_per_chunk(self):
    docs = _two_docs()
    expected = _expected_chunks(docs)
    self.assertGreaterEqual(len(expected), 4)
    observer = _run_annotate(_ValidFakeModel(), docs, batch_length=3)
    started = _events_named(observer, "chunk_started")
    finished = _events_named(observer, "chunk_finished")
    self.assertLen(started, len(expected))
    self.assertLen(finished, len(expected))
    self.assertTrue(
        all(isinstance(event, events.ChunkStarted) for event in started)
    )
    self.assertTrue(
        all(isinstance(event, events.ChunkFinished) for event in finished)
    )

  def test_chunk_indices_and_ranges_match_chunk_iterator(self):
    docs = _two_docs()
    expected = _expected_chunks(docs)
    observer = _run_annotate(_ValidFakeModel(), docs, batch_length=3)
    started = _events_named(observer, "chunk_started")
    got = [
        _ExpectedChunk(
            document_id=event.document_id,
            chunk_index=event.chunk_index,
            char_start=event.char_start,
            char_end=event.char_end,
        )
        for event in started
    ]
    self.assertEqual(got, expected)
    # Counterexample: must restart per document, not run-global 0..N-1.
    self.assertEqual(
        [event.chunk_index for event in started],
        [chunk.chunk_index for chunk in expected],
    )
    self.assertNotEqual(
        [event.chunk_index for event in started],
        list(range(len(started))),
        msg="chunk_index must be per-document, not run-global",
    )
    finished = _events_named(observer, "chunk_finished")
    for started_event, finished_event in zip(started, finished):
      self.assertEqual(started_event.document_id, finished_event.document_id)
      self.assertEqual(started_event.chunk_index, finished_event.chunk_index)
      self.assertEqual(started_event.char_start, finished_event.char_start)
      self.assertEqual(started_event.char_end, finished_event.char_end)
      self.assertEqual(started_event.pass_index, finished_event.pass_index)
      self.assertEqual(started_event.batch_index, finished_event.batch_index)

  def test_batch_index_groups_chunks(self):
    docs = _two_docs()
    expected = _expected_chunks(docs)
    self.assertEqual(len(expected), 4)
    observer = _run_annotate(_ValidFakeModel(), docs, batch_length=3)
    started = _events_named(observer, "chunk_started")
    self.assertEqual([event.batch_index for event in started], [0, 0, 0, 1])

  def test_pass_index_for_single_and_multi_pass(self):
    docs = [
        data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
    ]
    observer_one = _RecordingObserver()
    annotator = _make_annotator(_ValidFakeModel())
    list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            extraction_passes=1,
            on_event=observer_one,
        )
    )
    started_one = [
        event for event in observer_one.events if event.name == "chunk_started"
    ]
    self.assertNotEmpty(started_one)
    self.assertEqual({event.pass_index for event in started_one}, {0})

    observer_two = _RecordingObserver()
    list(
        annotator.annotate_documents(
            [
                data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
            ],
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            extraction_passes=2,
            on_event=observer_two,
        )
    )
    started_two = [
        event for event in observer_two.events if event.name == "chunk_started"
    ]
    finished_two = [
        event for event in observer_two.events if event.name == "chunk_finished"
    ]
    self.assertEqual(len(started_two), 2 * len(started_one))
    self.assertEqual(len(finished_two), len(started_two))
    self.assertEqual({event.pass_index for event in started_two}, {0, 1})

  def test_finished_duration_outcome_and_counts(self):
    docs = [
        data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
    ]
    observer = _RecordingObserver()
    annotator = _make_annotator(_ValidFakeModel(output=_VALID_YAML))
    results = list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            on_event=observer,
        )
    )
    finished = [
        event for event in observer.events if event.name == "chunk_finished"
    ]
    self.assertNotEmpty(finished)
    for event in finished:
      self.assertIsInstance(event.duration_s, float)
      self.assertGreaterEqual(event.duration_s, 0.0)
      self.assertEqual(event.outcome, events.OUTCOME_OK)
      self.assertIsInstance(event.num_extractions, int)
      self.assertGreaterEqual(event.num_extractions, 0)
    # Sum of per-chunk counts equals total aligned extractions on the doc.
    self.assertEqual(
        sum(event.num_extractions for event in finished),
        len(results[0].extractions),
    )

  def test_raising_observer_does_not_change_result(self):
    docs = _two_docs()
    model = _ValidFakeModel()
    annotator = _make_annotator(model)
    baseline = list(
        annotator.annotate_documents(
            [
                data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
                data.Document(text=_DOC_B_TEXT, document_id="doc-b"),
            ],
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=3,
            show_progress=False,
            debug=False,
            on_event=None,
        )
    )

    def _always_raise(_event):
      raise RuntimeError("observer boom")

    with self.assertLogs(level="WARNING") as log_ctx:
      # Force at least one logging call path; includes absl and stdlib.
      logging.getLogger().warning("probe")
      broken = list(
          _make_annotator(_ValidFakeModel()).annotate_documents(
              [
                  data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
                  data.Document(text=_DOC_B_TEXT, document_id="doc-b"),
              ],
              max_char_buffer=_MAX_CHAR_BUFFER,
              batch_length=3,
              show_progress=False,
              debug=False,
              on_event=_always_raise,
          )
      )
    self.assertEqual(
        [
            (document.document_id, document.text, document.extractions)
            for document in broken
        ],
        [
            (document.document_id, document.text, document.extractions)
            for document in baseline
        ],
    )
    observer_warnings = [
        record
        for record in log_ctx.records
        if "on_event" in record.getMessage()
        or "observer" in record.getMessage().lower()
    ]
    self.assertLen(observer_warnings, 1)

  def test_events_arrive_on_caller_thread(self):
    docs = _two_docs()
    observer = _RecordingObserver()
    caller_ident = threading.get_ident()
    annotator = _make_annotator(_ThreadedFakeModel())
    list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=2,
            show_progress=False,
            debug=False,
            max_workers=4,
            on_event=observer,
        )
    )
    self.assertNotEmpty(observer.events)
    self.assertTrue(
        all(tid == caller_ident for tid in observer.thread_ids),
        msg=f"expected caller {caller_ident}, got {set(observer.thread_ids)}",
    )

  def test_on_event_not_forwarded_to_infer(self):
    docs = [
        data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
    ]
    model = _ValidFakeModel()
    observer = _RecordingObserver()
    annotator = _make_annotator(model)
    list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            on_event=observer,
        )
    )
    self.assertTrue(model.infer_kwargs)
    for kwargs in model.infer_kwargs:
      self.assertNotIn("on_event", kwargs)
    # Events must still be delivered (fails at RED until emission is wired).
    self.assertTrue(
        any(event.name == "chunk_started" for event in observer.events)
    )

  def test_without_on_event_matches_omitted_parameter(self):
    docs = [
        data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
    ]
    annotator = _make_annotator(_ValidFakeModel())
    with_none = list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            on_event=None,
        )
    )
    omitted = list(
        annotator.annotate_documents(
            [
                data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
            ],
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
        )
    )
    self.assertEqual(
        [
            (document.document_id, document.text, document.extractions)
            for document in with_none
        ],
        [
            (document.document_id, document.text, document.extractions)
            for document in omitted
        ],
    )

  def test_extract_str_and_documents_deliver_events(self):
    examples = [
        data.ExampleData(
            text="example",
            extractions=[
                data.Extraction(
                    extraction_class="entity",
                    extraction_text="example",
                )
            ],
        )
    ]
    observer_str = _RecordingObserver()
    lx.extract(
        text_or_documents=_DOC_A_TEXT,
        prompt_description="extract entities",
        examples=examples,
        model=_ValidFakeModel(),
        max_char_buffer=_MAX_CHAR_BUFFER,
        batch_length=1,
        show_progress=False,
        debug=False,
        use_schema_constraints=False,
        fence_output=True,
        on_event=observer_str,
    )
    self.assertTrue(
        any(event.name == "chunk_started" for event in observer_str.events)
    )

    observer_docs = _RecordingObserver()
    lx.extract(
        text_or_documents=_two_docs(),
        prompt_description="extract entities",
        examples=examples,
        model=_ValidFakeModel(),
        max_char_buffer=_MAX_CHAR_BUFFER,
        batch_length=3,
        show_progress=False,
        debug=False,
        use_schema_constraints=False,
        fence_output=True,
        on_event=observer_docs,
    )
    self.assertTrue(
        any(event.name == "chunk_started" for event in observer_docs.events)
    )

  def test_parse_failed_when_suppressed(self):
    docs = [
        data.Document(text=_DOC_BROKEN_TEXT, document_id="doc-broken"),
    ]
    expected = _expected_chunks(docs)
    self.assertLen(expected, 2)
    observer = _RecordingObserver()
    annotator = _make_annotator(_BrokenChunkFakeModel())
    results = list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            suppress_parse_errors=True,
            on_event=observer,
        )
    )
    parse_failed = [
        event for event in observer.events if event.name == "parse_failed"
    ]
    self.assertLen(parse_failed, 1)
    failed = parse_failed[0]
    self.assertIsInstance(failed, events.ParseFailed)
    self.assertNotEmpty(failed.error_type)
    self.assertNotEmpty(failed.message)

    # Find which chunk had the marker via oracle ranges.
    broken_chunk = None
    for chunk in expected:
      if chunk.char_start is not None and chunk.char_end is not None:
        if (
            _BROKEN_MARKER
            in _DOC_BROKEN_TEXT[chunk.char_start : chunk.char_end]
        ):
          broken_chunk = chunk
          break
    self.assertIsNotNone(broken_chunk)
    self.assertEqual(failed.document_id, broken_chunk.document_id)
    self.assertEqual(failed.chunk_index, broken_chunk.chunk_index)
    self.assertEqual(failed.char_start, broken_chunk.char_start)
    self.assertEqual(failed.char_end, broken_chunk.char_end)

    finished = [
        event for event in observer.events if event.name == "chunk_finished"
    ]
    self.assertLen(finished, 2)
    broken_finished = [
        event
        for event in finished
        if event.chunk_index == broken_chunk.chunk_index
        and event.document_id == broken_chunk.document_id
    ]
    self.assertLen(broken_finished, 1)
    self.assertEqual(broken_finished[0].outcome, events.OUTCOME_PARSE_ERROR)
    self.assertEqual(broken_finished[0].num_extractions, 0)
    ok_finished = [
        event for event in finished if event is not broken_finished[0]
    ]
    self.assertTrue(
        all(event.outcome == events.OUTCOME_OK for event in ok_finished)
    )
    self.assertEqual(results[0].extractions, [])

  def test_parse_failed_then_raises_when_unsuppressed(self):
    docs = [
        data.Document(text=_DOC_BROKEN_TEXT, document_id="doc-broken"),
    ]
    observer = _RecordingObserver()
    annotator = _make_annotator(_BrokenChunkFakeModel())
    with self.assertRaises(resolver_lib.ResolverParsingError):
      list(
          annotator.annotate_documents(
              docs,
              max_char_buffer=_MAX_CHAR_BUFFER,
              batch_length=1,
              show_progress=False,
              debug=False,
              suppress_parse_errors=False,
              on_event=observer,
          )
      )
    names = [event.name for event in observer.events]
    self.assertIn("parse_failed", names)
    self.assertIn("chunk_finished", names)
    # Ordering for the broken chunk: started → parse_failed → finished.
    pf_idx = names.index("parse_failed")
    self.assertEqual(names[pf_idx - 1], "chunk_started")
    self.assertEqual(names[pf_idx + 1], "chunk_finished")
    finished = observer.events[pf_idx + 1]
    self.assertEqual(finished.outcome, events.OUTCOME_PARSE_ERROR)

  def test_parse_failed_ordering_when_suppressed(self):
    docs = [
        data.Document(text=_DOC_BROKEN_TEXT, document_id="doc-broken"),
    ]
    observer = _RecordingObserver()
    annotator = _make_annotator(_BrokenChunkFakeModel())
    list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            suppress_parse_errors=True,
            on_event=observer,
        )
    )
    names = [event.name for event in observer.events]
    pf_idx = names.index("parse_failed")
    self.assertEqual(names[pf_idx - 1], "chunk_started")
    self.assertEqual(names[pf_idx + 1], "chunk_finished")

  def test_without_on_event_parse_suppression_unchanged(self):
    docs = [
        data.Document(text=_DOC_BROKEN_TEXT, document_id="doc-broken"),
    ]
    annotator = _make_annotator(_BrokenChunkFakeModel())
    with self.assertLogs(level="WARNING") as log_ctx:
      results = list(
          annotator.annotate_documents(
              docs,
              max_char_buffer=_MAX_CHAR_BUFFER,
              batch_length=1,
              show_progress=False,
              debug=False,
              suppress_parse_errors=True,
          )
      )
    self.assertEqual(results[0].extractions, [])
    self.assertTrue(
        any(
            "Chunk omitted from results" in record.getMessage()
            for record in log_ctx.records
        )
    )
    with self.assertRaises(resolver_lib.ResolverParsingError):
      list(
          annotator.annotate_documents(
              [
                  data.Document(
                      text=_DOC_BROKEN_TEXT, document_id="doc-broken"
                  ),
              ],
              max_char_buffer=_MAX_CHAR_BUFFER,
              batch_length=1,
              show_progress=False,
              debug=False,
              suppress_parse_errors=False,
          )
      )

  def test_extract_default_suppression_still_emits_parse_failed(self):
    examples = [
        data.ExampleData(
            text="example",
            extractions=[
                data.Extraction(
                    extraction_class="entity",
                    extraction_text="example",
                )
            ],
        )
    ]
    observer = _RecordingObserver()
    lx.extract(
        text_or_documents=_DOC_BROKEN_TEXT,
        prompt_description="extract entities",
        examples=examples,
        model=_BrokenChunkFakeModel(),
        max_char_buffer=_MAX_CHAR_BUFFER,
        batch_length=1,
        show_progress=False,
        debug=False,
        use_schema_constraints=False,
        fence_output=True,
        on_event=observer,
    )
    self.assertTrue(
        any(event.name == "parse_failed" for event in observer.events)
    )

  @parameterized.named_parameters(
      (
          "carries_usage_from_scored_output",
          types.TokenUsage(input_tokens=3, output_tokens=5),
      ),
      ("usage_none_without_provider_usage", None),
  )
  def test_chunk_finished_usage(self, usage: types.TokenUsage | None):
    docs = [
        data.Document(text=_DOC_A_TEXT, document_id="doc-a"),
    ]
    observer = _RecordingObserver()
    annotator = _make_annotator(_UsageFakeModel(usage=usage))
    list(
        annotator.annotate_documents(
            docs,
            max_char_buffer=_MAX_CHAR_BUFFER,
            batch_length=1,
            show_progress=False,
            debug=False,
            on_event=observer,
        )
    )
    finished = [
        event for event in observer.events if event.name == "chunk_finished"
    ]
    self.assertNotEmpty(finished)
    self.assertEqual(
        [event.usage for event in finished], [usage] * len(finished)
    )


class TokenUsageConstructionTest(absltest.TestCase):

  def test_scored_output_usage_defaults_to_none(self):
    scored = types.ScoredOutput(score=1.0, output="x")
    self.assertIsNone(scored.usage)


if __name__ == "__main__":
  absltest.main()
