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

"""Tests for scripts/trace_extract.py extraction snapshots."""

import contextlib
import importlib.util
import io
import pathlib
import sys
from unittest import mock

from absl.testing import absltest

from langextract import chunking
from langextract import data
from langextract import prompting
from langextract import resolver
import langextract as lx
from langextract.core import tokenizer as tokenizer_lib
from langextract.core import types as core_types
from langextract.providers import ollama

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts"
    / "trace_extract.py"
)
_SOURCE_TEXT = "Patient reports a headache since Monday."
_CANNED = (
    '{"extractions": [{"symptom": "headache"}, {"symptom": "purple elephant"}]}'
)


def _load_script_module():
  """Loads scripts/trace_extract.py as a module."""
  spec = importlib.util.spec_from_file_location("trace_extract", _SCRIPT_PATH)
  module = importlib.util.module_from_spec(spec)
  # dataclasses resolves string annotations through sys.modules.
  sys.modules[spec.name] = module
  spec.loader.exec_module(module)
  return module


# Stage label -> (class, attribute) that a stage wrapper replaces.
_STAGE_TARGETS = {
    "chunk": (chunking.ChunkIterator, "__iter__"),
    "prompt": (prompting.ContextAwarePromptBuilder, "build_prompt"),
    "model": (ollama.OllamaLanguageModel, "infer"),
    "parse": (resolver.Resolver, "resolve"),
    "align": (resolver.Resolver, "align"),
}


def _patch_stages(test, wrappers, labels):
  """Installs wrappers[label](original) on each target; restored by cleanup."""
  for label in labels:
    cls, attr = _STAGE_TARGETS[label]
    replacement = wrappers[label](cls.__dict__[attr])
    test.enter_context(mock.patch.object(cls, attr, replacement))


def _run_offline_extract(test, canned):
  """Runs the real lx.extract with only _ollama_query faked.

  Returns:
    (AnnotatedDocument, number of fake HTTP calls).
  """
  calls = []

  def fake_query(self, prompt, **kwargs):
    calls.append(prompt)
    return {"response": canned}

  test.enter_context(
      mock.patch.object(ollama.OllamaLanguageModel, "_ollama_query", fake_query)
  )
  document = lx.extract(
      _SOURCE_TEXT,
      prompt_description="Extract symptoms.",
      examples=[
          data.ExampleData(
              "He has a cough.", [data.Extraction("symptom", "cough")]
          )
      ],
      model_id="gemma3:4b",
      model_url="http://localhost:11434",
      resolver_params={"format_handler": ollama.OLLAMA_FORMAT_HANDLER},
      extraction_passes=1,
      debug=False,
      show_progress=False,
  )
  return document, len(calls)


class TraceExtractSnapshotTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()
    self.resolver = resolver.Resolver(
        format_handler=ollama.OLLAMA_FORMAT_HANDLER
    )
    self.resolved = self.resolver.resolve(_CANNED, suppress_parse_errors=True)

  def _align(self):
    return list(
        self.resolver.align(
            self.resolved, _SOURCE_TEXT, token_offset=0, char_offset=0
        )
    )

  def test_parse_snapshot_survives_align_mutation(self):
    parse = self.trace.snapshot_extractions(self.resolved)
    self.assertLen(parse, 2)
    self.assertEqual([s.extraction_index for s in parse], [1, 2])
    for snap in parse:
      self.assertIsNone(snap.char_interval)
      self.assertIsNone(snap.alignment_status)

    aligned = self._align()
    # The live object was mutated in place by align (the hazard).
    self.assertIsNotNone(self.resolved[0].char_interval)
    # The earlier parse snapshot still shows the ungrounded state.
    self.assertIsNone(parse[0].char_interval)
    self.assertIsNone(parse[0].alignment_status)

    align = self.trace.snapshot_extractions(aligned)
    self.assertEqual(align[0].char_interval, (18, 26))
    self.assertEqual(align[0].alignment_status, "match_exact")
    self.assertIsNone(align[1].char_interval)

  def test_print_grounding_pair_orders_parse_before_align(self):
    parse = self.trace.snapshot_extractions(self.resolved)
    align = self.trace.snapshot_extractions(self._align())

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      self.trace.print_grounding_pair(parse, align, "ungrounded")
    lines = buf.getvalue().splitlines()

    self.assertIn("grounding pair", lines[0])
    idx = next(i for i, ln in enumerate(lines) if "'headache'" in ln)
    parse_line, align_line = lines[idx + 1], lines[idx + 2]
    self.assertIn("parse:", parse_line)
    self.assertIn("char_interval=None", parse_line)
    self.assertIn("alignment_status=None", parse_line)
    self.assertIn("align:", align_line)
    self.assertIn("[18, 26)", align_line)
    self.assertIn("match_exact", align_line)

  def _print_pair(self, parse, align):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      self.trace.print_grounding_pair(parse, align, "ungrounded")
    return buf.getvalue().splitlines()

  def test_empty_parse_prints_explicit_empty_lists(self):
    empty = self.resolver.resolve("not json", suppress_parse_errors=True)
    self.assertEqual(empty, [])
    parse = self.trace.snapshot_extractions(empty)
    align = self.trace.snapshot_extractions(
        list(self.resolver.align([], _SOURCE_TEXT, 0, 0))
    )
    self.assertEqual((parse, align), ((), ()))

    lines = self._print_pair(parse, align)
    self.assertIn("grounding pair (parse → align): 0 extractions", lines[0])
    self.assertTrue(any(ln.endswith("parse: []") for ln in lines))
    self.assertTrue(any(ln.endswith("align: []") for ln in lines))

  def test_unaligned_extraction_prints_ungrounded_label(self):
    parse = self.trace.snapshot_extractions(self.resolved)
    align = self.trace.snapshot_extractions(self._align())
    lines = self._print_pair(parse, align)

    idx = next(i for i, ln in enumerate(lines) if "purple elephant" in ln)
    self.assertIn("char_interval=None alignment_status=None", lines[idx + 1])
    self.assertIn(
        "char_interval=ungrounded alignment_status=ungrounded", lines[idx + 2]
    )
    grounded = next(i for i, ln in enumerate(lines) if "'headache'" in ln)
    self.assertIn("[18, 26)", lines[grounded + 2])
    self.assertIn("match_exact", lines[grounded + 2])

  def _snap(self, text, start=None, end=None, index=1, cls="symptom"):
    char = None if start is None else (start, end)
    return self.trace.ExtractionSnapshot(
        extraction_class=cls,
        extraction_text=text,
        extraction_index=index,
        group_index=None,
        attributes=None,
        char_interval=char,
        token_interval=None,
        alignment_status=None if char is None else "match_exact",
    )

  def test_duplicate_extractions_stay_separate_in_order(self):
    parse = (self._snap("pain", index=1), self._snap("pain", index=2))
    align = (
        self._snap("pain", 0, 4, index=1),
        self._snap("pain", 10, 14, index=2),
    )
    lines = self._print_pair(parse, align)
    self.assertIn("2 extractions", lines[0])
    first = next(i for i, ln in enumerate(lines) if "index=1" in ln)
    second = next(i for i, ln in enumerate(lines) if "index=2" in ln)
    self.assertIn("[1]", lines[first])
    self.assertIn("[0, 4)", lines[first + 2])
    self.assertIn("[2]", lines[second])
    self.assertIn("[10, 14)", lines[second + 2])

  def test_touching_spans_print_as_two_pairs(self):
    parse = (self._snap("alpha", index=1), self._snap("beta", index=2))
    align = (self._snap("alpha", 0, 5, index=1), self._snap("beta", 5, 9, 2))
    lines = self._print_pair(parse, align)
    self.assertIn("2 extractions", lines[0])
    self.assertTrue(any("[0, 5)" in ln for ln in lines))
    self.assertTrue(any("[5, 9)" in ln for ln in lines))

  def test_count_mismatch_raises_before_printing(self):
    parse = (self._snap("pain", index=1), self._snap("pain", index=2))
    align = (self._snap("pain", 0, 4),)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      with self.assertRaisesRegex(ValueError, "2.*1"):
        self.trace.print_grounding_pair(parse, align, "ungrounded")
    self.assertEqual(buf.getvalue(), "")

  def test_text_mismatch_names_position(self):
    parse = (self._snap("pain", index=1), self._snap("pain", index=2))
    align = (self._snap("pain", 0, 4), self._snap("ache", 10, 14))
    with self.assertRaisesRegex(ValueError, "position 2"):
      self._print_pair(parse, align)

  def test_live_extraction_rejected_with_type_error(self):
    live = [data.Extraction("symptom", "pain")]
    align = (self._snap("pain", 0, 4),)
    with self.assertRaises(TypeError):
      self._print_pair(live, align)
    with self.assertRaises(TypeError):
      self._print_pair((self._snap("pain"),), live)

  def test_ungrounded_label_comes_from_config(self):
    config = self.trace.load_config(self.trace._CONFIG_PATH)
    self.assertEqual(config["ungrounded_label"], "ungrounded")

  def test_snapshot_independent_of_later_mutation(self):
    ext = data.Extraction(
        "med",
        "aspirin",
        attributes={"dose": ["5mg"]},
        extraction_index=1,
        group_index=0,
    )
    live_attrs = ext.attributes
    live_dose = ext.attributes["dose"]
    snap = self.trace.snapshot_extractions([ext])[0]

    ext.attributes["dose"].append("10mg")
    ext.attributes["route"] = "oral"
    ext.char_interval = data.CharInterval(0, 7)
    ext.alignment_status = data.AlignmentStatus.MATCH_FUZZY

    self.assertEqual(snap.attributes, {"dose": ["5mg"]})
    self.assertIsNone(snap.char_interval)
    self.assertIsNone(snap.alignment_status)
    self.assertIsNot(snap.attributes, live_attrs)
    self.assertIsNot(snap.attributes["dose"], live_dose)
    self.assertEqual(snap.group_index, 0)

    bare = self.trace.snapshot_extractions([data.Extraction("a", "b")])[0]
    self.assertIsNone(bare.attributes)

    ext.char_interval = data.CharInterval(2, 5)
    ext.alignment_status = data.AlignmentStatus.MATCH_EXACT
    grounded = self.trace.snapshot_extractions([ext])[0]
    self.assertEqual(grounded.char_interval, (2, 5))
    self.assertIsInstance(grounded.char_interval, tuple)
    self.assertIsInstance(grounded.alignment_status, str)


class TraceExtractWrapperTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()
    self.config = self.trace.load_config(self.trace._CONFIG_PATH)
    self.sink = []

  def _print_records(self, records):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      self.trace.print_stage_records(records, self.config)
    return buf.getvalue()

  def _model_record(self, raw_text, prompt="PROMPT TEXT"):
    return self.trace.StageRecord(
        "model",
        {"batch_prompts": (prompt,), "batch_size": 1, "kwargs": {}},
        {"prompt_index": 0, "score": 1.0, "raw_model_text": raw_text},
    )

  def test_model_wrapper_records_prompt_and_raw_text_from_offline_extract(self):
    wrappers = self.trace.make_stage_wrappers(self.sink, self.config)
    _patch_stages(self, wrappers, ["model"])

    document, calls = _run_offline_extract(self, _CANNED)

    self.assertEqual(calls, 1)
    self.assertLen(self.sink, 1)
    record = self.sink[0]
    self.assertEqual(record.label, "model")
    self.assertLen(record.in_data["batch_prompts"], 1)
    self.assertIsInstance(record.in_data["batch_prompts"][0], str)
    self.assertIn(_SOURCE_TEXT, record.in_data["batch_prompts"][0])
    self.assertEqual(record.in_data["batch_size"], 1)
    self.assertEqual(
        record.out_data,
        {"prompt_index": 0, "score": 1.0, "raw_model_text": _CANNED},
    )
    self.assertLen(document.extractions, 2)

  def test_print_stage_records_escapes_control_characters_in_raw_text(self):
    record = self._model_record("café\x1b[31m\nline2", prompt="FULL PROMPT")

    printed = self._print_records([record])

    lines = printed.splitlines()
    self.assertEqual(
        lines[0],
        "[model] OllamaLanguageModel.infer — langextract/providers/ollama.py",
    )
    self.assertIn("in:", lines)
    self.assertIn("out:", lines)
    self.assertIn("FULL PROMPT", printed)
    self.assertIn("    café\\x1b[31m", lines)
    self.assertIn("    line2", lines)
    self.assertNotIn("\x1b", printed)

  def test_print_stage_records_prints_empty_raw_text_explicitly(self):
    printed = self._print_records([self._model_record("")])

    self.assertIn("  raw_model_text: ''", printed.splitlines())

  def test_print_stage_records_follows_catalog_order_and_skips_missing(self):
    chunk = self.trace.StageRecord("chunk", {}, {})

    printed = self._print_records([self._model_record("x"), chunk])

    self.assertLess(printed.index("[chunk]"), printed.index("[model]"))
    self.assertNotIn("[prompt]", printed)

  def test_model_wrapper_redacts_forwarded_kwargs(self):
    def original(self, batch_prompts, **kwargs):
      yield [core_types.ScoredOutput(score=1.0, output="text")]

    wrapped = self.trace.make_model_wrapper(self.sink, ["api_key"])(original)

    list(wrapped(None, batch_prompts=["p"], max_workers=10, api_key="x"))

    self.assertEqual(
        self.sink[0].in_data["kwargs"],
        {"max_workers": 10, "api_key": "<REDACTED>"},
    )

  def test_chunk_wrapper_yields_same_chunks_without_recursion(self):
    original = chunking.ChunkIterator.__dict__["__iter__"]
    # Registered first, so it runs after the patch is undone.
    self.addCleanup(
        lambda: self.assertIs(
            chunking.ChunkIterator.__dict__["__iter__"], original
        )
    )
    wrappers = self.trace.make_stage_wrappers(self.sink, self.config)
    _patch_stages(self, wrappers, ["chunk"])
    chunk_iter = chunking.ChunkIterator(
        text=_SOURCE_TEXT,
        max_char_buffer=1000,
        tokenizer_impl=tokenizer_lib.RegexTokenizer(),
    )

    chunks = list(iter(chunk_iter))

    self.assertLen(chunks, 1)
    self.assertLen(self.sink, 1)
    record = self.sink[0]
    self.assertEqual(record.label, "chunk")
    self.assertEqual(
        record.in_data,
        {"max_char_buffer": 1000, "document_text": _SOURCE_TEXT},
    )
    self.assertEqual(record.out_data["chunk_text"], chunks[0].chunk_text)
    self.assertEqual(record.out_data["chunk_text"], _SOURCE_TEXT)
    self.assertEqual(record.out_data["char_interval"], (0, len(_SOURCE_TEXT)))
    self.assertLen(record.out_data["token_interval"], 2)
    self.assertIsInstance(record.out_data["token_interval"][0], int)
    self.assertIsInstance(record.out_data["document_id"], str)

  def _run_traced_extract(self, labels):
    wrappers = self.trace.make_stage_wrappers(self.sink, self.config)
    _patch_stages(self, wrappers, labels)
    return _run_offline_extract(self, _CANNED)

  def test_prompt_record_matches_model_batch_prompt_from_offline_extract(self):
    _, calls = self._run_traced_extract(["chunk", "prompt", "model"])

    by_label = {r.label: r for r in self.sink}
    self.assertEqual(calls, 1)
    self.assertCountEqual(
        [r.label for r in self.sink], ["chunk", "prompt", "model"]
    )
    self.assertEqual(
        by_label["prompt"].out_data["prompt"],
        by_label["model"].in_data["batch_prompts"][0],
    )
    self.assertEqual(
        by_label["prompt"].in_data["chunk_text"],
        by_label["chunk"].out_data["chunk_text"],
    )
    self.assertIn("additional_context", by_label["prompt"].in_data)
    self.assertIsNone(by_label["prompt"].in_data["additional_context"])

  def test_print_stage_records_orders_chunk_prompt_model_from_extract(self):
    self._run_traced_extract(["chunk", "prompt", "model"])

    printed = self._print_records(list(reversed(self.sink)))

    chunk_at = printed.index("[chunk] ChunkIterator — langextract/chunking.py")
    prompt_at = printed.index("[prompt] ContextAwarePromptBuilder.build_prompt")
    model_at = printed.index("[model] OllamaLanguageModel.infer")
    self.assertLess(chunk_at, prompt_at)
    self.assertLess(prompt_at, model_at)


if __name__ == "__main__":
  absltest.main()
