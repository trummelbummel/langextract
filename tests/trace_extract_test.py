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
import http.server
import importlib.util
import io
import json
import os
import pathlib
import socket
import sys
import tempfile
import threading
import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
import yaml

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


class TraceExtractWrapperTest(parameterized.TestCase):

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

  def test_print_stage_records_chunk_uses_hash_and_star_block_titles(self):
    chunk = self.trace.StageRecord(
        "chunk",
        {"text_or_documents": "doc text"},
        {"chunk_text": "chunk body"},
    )

    printed = self._print_records([chunk])
    lines = printed.splitlines()

    self.assertIn("##########:", lines)
    self.assertIn("*******:", lines)
    self.assertNotIn("in:", lines)
    self.assertNotIn("out:", lines)

  def test_print_stage_records_model_still_uses_in_out_titles(self):
    printed = self._print_records([self._model_record("x")])
    lines = printed.splitlines()

    self.assertIn("in:", lines)
    self.assertIn("out:", lines)
    self.assertNotIn("##########:", lines)
    self.assertNotIn("*******:", lines)

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

  def test_parse_wrapper_records_raw_text_flags_and_ungrounded_snapshots(self):
    document, _ = self._run_traced_extract(["model", "parse"])

    by_label = {r.label: r for r in self.sink}
    parse = by_label["parse"]
    self.assertEqual(
        parse.in_data["raw_model_text"],
        by_label["model"].out_data["raw_model_text"],
    )
    self.assertEqual(parse.in_data["raw_model_text"], _CANNED)
    self.assertEqual(
        parse.in_data["flags"],
        {
            "format_type": "json",
            "use_fences": False,
            "strict_fences": False,
            "use_wrapper": True,
            "wrapper_key": "extractions",
        },
    )
    self.assertIs(parse.in_data["suppress_parse_errors"], True)
    snapshots = parse.out_data["extractions"]
    self.assertLen(snapshots, 2)
    for snap in snapshots:
      self.assertIsInstance(snap, self.trace.ExtractionSnapshot)
      self.assertIsNone(snap.char_interval)
      self.assertIsNone(snap.alignment_status)
    self.assertLen(document.extractions, 2)
    self.assertIsNotNone(document.extractions[0].char_interval)

  def test_print_stage_records_prints_parse_flags_and_snapshots(self):
    self._run_traced_extract(["model", "parse"])

    printed = self._print_records(self.sink)

    self.assertIn("[parse] Resolver.resolve — langextract/resolver.py", printed)
    parse_part = printed[printed.index("[parse]") :]
    self.assertIn(_CANNED, parse_part)
    self.assertIn("flags:", parse_part)
    self.assertIn("use_fences': False", parse_part)
    self.assertIn("wrapper_key': 'extractions'", parse_part)
    self.assertIn("extractions:", parse_part)

  def _parse_section(self, canned):
    wrappers = self.trace.make_stage_wrappers(self.sink, self.config)
    _patch_stages(self, wrappers, ["model", "parse"])
    _run_offline_extract(self, canned)
    printed = self._print_records(self.sink)
    return printed[printed.index("[parse]") :]

  @parameterized.named_parameters(
      dict(
          testcase_name="not_json",
          canned="not json",
          error="Failed to parse JSON content",
          message="empty_parse_message",
      ),
      dict(
          testcase_name="fenced_without_use_fences",
          canned='```json\n{"extractions": [{"symptom": "headache"}]}\n```',
          error="Failed to parse JSON content",
          message="empty_parse_message",
      ),
      dict(
          testcase_name="valid_empty_list",
          canned='{"extractions": []}',
          error=None,
          message="empty_list_message",
      ),
  )
  def test_parse_callout_follows_raw_text_and_diagnosis(
      self, canned, error, message
  ):
    section = self._parse_section(canned)

    record = next(r for r in self.sink if r.label == "parse")
    self.assertEqual(record.out_data["extractions"], ())
    parse_error = record.out_data["parse_error"]
    if error is None:
      self.assertIsNone(parse_error)
    else:
      self.assertIn(error, parse_error)
    shown = self.config[message].strip()
    other = {"empty_parse_message", "empty_list_message"} - {message}
    self.assertIn(shown, section)
    for name in other:
      self.assertNotIn(self.config[name].strip(), section)
    self.assertLess(section.index(shown), section.index("\nout:"))
    self.assertLess(section.index("raw_model_text"), section.index(shown))
    if error:
      self.assertIn(error, section)
    if "```" in canned:
      self.assertIn("use_fences': False", section)

  def test_parse_callout_for_empty_string_reply(self):
    # The Ollama provider rejects an empty reply before parse, so call the
    # wrapped Resolver.resolve directly.
    wrappers = self.trace.make_stage_wrappers(self.sink, self.config)
    _patch_stages(self, wrappers, ["parse"])
    parser = resolver.Resolver(format_handler=ollama.OLLAMA_FORMAT_HANDLER)

    result = parser.resolve("", suppress_parse_errors=True)

    self.assertEqual(result, [])
    self.assertLen(self.sink, 1)
    self.assertIn(
        "Empty or invalid input string", self.sink[0].out_data["parse_error"]
    )
    printed = self._print_records(self.sink)
    self.assertIn("  raw_model_text: ''", printed.splitlines())
    self.assertIn(self.config["empty_parse_message"].strip(), printed)
    self.assertIn("Empty or invalid input string.", printed)

  def test_parse_callout_escapes_control_characters(self):
    section = self._parse_section("café\x1b[31m")

    self.assertNotIn("\x1b", section)
    self.assertIn("\\x1b", section)
    self.assertIn("café", section)

  @parameterized.named_parameters(
      dict(testcase_name="not_json", canned="not json"),
      dict(testcase_name="valid_empty_list", canned='{"extractions": []}'),
      dict(testcase_name="non_empty", canned=_CANNED),
  )
  def test_parse_diagnosis_adds_no_extra_records(self, canned):
    self._parse_section(canned)

    self.assertEqual(
        sorted(r.label for r in self.sink),
        ["model", "parse"],
    )

  def test_parse_non_empty_records_no_error_and_no_callout(self):
    section = self._parse_section(_CANNED)

    record = next(r for r in self.sink if r.label == "parse")
    self.assertIsNone(record.out_data["parse_error"])
    for name in ("empty_parse_message", "empty_list_message"):
      self.assertNotIn(self.config[name].strip(), section)

  def test_config_has_empty_list_message(self):
    message = self.trace.load_config(self.trace._CONFIG_PATH)[
        "empty_list_message"
    ]

    self.assertIsInstance(message, str)
    self.assertTrue(message.strip())

  def _run_five_stages(self, canned=_CANNED):
    wrappers = self.trace.make_stage_wrappers(self.sink, self.config)
    _patch_stages(self, wrappers, list(_STAGE_TARGETS))
    document, _ = _run_offline_extract(self, canned)
    return document, self._print_records(self.sink)

  def _span_lines(self, section):
    return [l for l in section.splitlines() if "  span=" in l]

  def _align_record(self):
    return next(r for r in self.sink if r.label == "align")

  def _direct_align_section(self, token_offset, char_offset):
    wrappers = self.trace.make_stage_wrappers(self.sink, self.config)
    _patch_stages(self, wrappers, ["align"])
    parser = resolver.Resolver(format_handler=ollama.OLLAMA_FORMAT_HANDLER)
    resolved = parser.resolve(_CANNED, suppress_parse_errors=True)
    args = [resolved, _SOURCE_TEXT, token_offset]
    if char_offset is not None:
      args.append(char_offset)
    list(parser.align(*args))
    printed = self._print_records(self.sink)
    return printed[printed.index("[align]") :]

  def test_align_wrapper_records_chunk_inputs_from_offline_extract(self):
    self._run_five_stages()

    record = self._align_record()
    self.assertEqual(
        [r.label for r in self.sink].count("align"), 1, "one align record"
    )
    self.assertEqual(
        record.in_data,
        {
            "source_text": _SOURCE_TEXT,
            "token_offset": 0,
            "char_offset": 0,
            "n_extractions": 2,
        },
    )
    self.assertIs(type(record.in_data["char_offset"]), int)

  def test_align_wrapper_snapshots_the_extractions_it_yielded(self):
    document, _ = self._run_five_stages()

    snaps = self._align_record().out_data["extractions"]
    headache, elephant = snaps
    self.assertEqual(
        (headache.extraction_text, headache.char_interval),
        ("headache", (18, 26)),
    )
    self.assertEqual(headache.alignment_status, "match_exact")
    self.assertIsNone(elephant.char_interval)
    self.assertEqual(
        snaps, self.trace.snapshot_extractions(document.extractions)
    )

  def test_five_stage_walkthrough_prints_sections_in_catalog_order(self):
    _, printed = self._run_five_stages()

    positions = [
        printed.index(f"[{label}] ")
        for label in ("chunk", "prompt", "model", "parse", "align")
    ]
    self.assertEqual(positions, sorted(positions))
    self.assertCountEqual(
        [r.label for r in self.sink],
        ["chunk", "prompt", "model", "parse", "align"],
    )

  def test_align_section_prints_offsets_spans_slices_and_ungrounded(self):
    _, printed = self._run_five_stages()

    section = printed[printed.index("[align]") :]
    caption = self.config["chunk_offset_caption"]
    self.assertIn(
        f"offsets: token_offset=0  char_offset=0  ({caption})",
        section.splitlines(),
    )
    headache, elephant = self._span_lines(section)
    self.assertIn("[18, 26)", headache)
    self.assertIn("match_exact", headache)
    self.assertTrue(headache.endswith("slice='headache'"), headache)
    self.assertTrue(
        elephant.endswith(self.config["ungrounded_label"]), elephant
    )

  def test_align_section_prints_parse_to_align_pair(self):
    _, printed = self._run_five_stages()

    section = printed[printed.index("[align]") :]
    self.assertIn("grounding pair (parse → align): 2 extractions", section)
    self.assertIn("parse: char_interval=None alignment_status=None", section)
    self.assertIn("align: char_interval=[18, 26)", section)

  @parameterized.named_parameters(
      dict(testcase_name="offsets_5_100", token=5, char=100, span="[118, 126)"),
      dict(
          testcase_name="char_offset_omitted",
          token=0,
          char=None,
          span="[18, 26)",
      ),
  )
  def test_align_section_uses_document_coordinates_minus_offset(
      self, token, char, span
  ):
    section = self._direct_align_section(token, char)

    shown = char or 0
    self.assertIn(f"token_offset={token}  char_offset={shown}", section)
    self.assertNotIn("char_offset=None", section)
    line = self._span_lines(section)[0]
    self.assertIn(span, line)
    self.assertTrue(line.endswith("slice='headache'"), line)

  def test_align_with_empty_parse_records_zero_and_prints_empty_pair(self):
    _, printed = self._run_five_stages("not json")

    record = self._align_record()
    self.assertEqual(record.in_data["n_extractions"], 0)
    self.assertEqual(record.out_data["extractions"], ())
    section = printed[printed.index("[align]") :]
    self.assertIn("grounding pair (parse → align): 0 extractions", section)
    self.assertIn("parse: []", section)
    self.assertIn("align: []", section)


class TraceExtractProbeTest(absltest.TestCase):
  """Call-scoped identity probes (Phase 3)."""

  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()

  def _originals(self):
    return {
        label: cls.__dict__[attr]
        for label, (cls, attr) in _STAGE_TARGETS.items()
    }

  def test_trace_probes_installs_five_and_restores_on_exception(self):
    originals = self._originals()
    raised = False
    try:
      with self.trace.trace_probes():
        for label, (cls, attr) in _STAGE_TARGETS.items():
          self.assertIsNot(
              getattr(cls, attr),
              originals[label],
              msg=f"{label} should be wrapped",
          )
        raise RuntimeError("probe self-check")
    except RuntimeError as exc:
      raised = True
      self.assertEqual(str(exc), "probe self-check")
    self.assertTrue(raised)
    for label, (cls, attr) in _STAGE_TARGETS.items():
      self.assertIs(
          getattr(cls, attr),
          originals[label],
          msg=f"{label} should be restored",
      )

  def test_trace_probes_identity_passthrough_no_side_effects(self):
    template = prompting.PromptTemplateStructured(
        description="Extract symptoms.",
        examples=[
            data.ExampleData(
                text="He has a cough.",
                extractions=[data.Extraction("symptom", "cough")],
            )
        ],
    )
    generator = prompting.QAPromptGenerator(
        template=template,
        format_handler=ollama.OLLAMA_FORMAT_HANDLER,
    )
    builder = prompting.ContextAwarePromptBuilder(generator)
    parser = resolver.Resolver(format_handler=ollama.OLLAMA_FORMAT_HANDLER)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      with self.trace.trace_probes():
        chunk_iter = chunking.ChunkIterator(
            text=_SOURCE_TEXT,
            max_char_buffer=1000,
            tokenizer_impl=tokenizer_lib.RegexTokenizer(),
        )
        chunks = list(iter(chunk_iter))
        self.assertLen(chunks, 1)
        self.assertEqual(chunks[0].chunk_text, _SOURCE_TEXT)

        prompt = builder.build_prompt(
            chunk_text=_SOURCE_TEXT,
            document_id="doc-1",
            additional_context=None,
        )
        self.assertIsInstance(prompt, str)
        self.assertIn(_SOURCE_TEXT, prompt)

        model = ollama.OllamaLanguageModel(
            model_id="gemma3:4b",
            model_url="http://localhost:11434",
            format_type=core_types.FormatType.JSON,
        )

        def fake_query(self, prompt, **kwargs):
          return {"response": _CANNED}

        with mock.patch.object(
            ollama.OllamaLanguageModel, "_ollama_query", fake_query
        ):
          outputs = list(model.infer([prompt]))
        self.assertLen(outputs, 1)
        self.assertEqual(outputs[0][0].output, _CANNED)

        parsed = parser.resolve(_CANNED, suppress_parse_errors=True)
        self.assertLen(parsed, 2)
        aligned = list(
            parser.align(parsed, _SOURCE_TEXT, token_offset=0, char_offset=0)
        )
        self.assertLen(aligned, 2)
        self.assertEqual(aligned[0].extraction_text, "headache")
    self.assertEqual(buf.getvalue(), "")

  def test_probes_active_false_after_exception_exit(self):
    with self.assertRaises(RuntimeError):
      with self.trace.trace_probes():
        self.assertTrue(self.trace._PROBES_ACTIVE)
        raise RuntimeError("boom")
    self.assertFalse(self.trace._PROBES_ACTIVE)

  def test_nested_trace_probes_rejected_with_already_active(self):
    with self.trace.trace_probes():
      with self.assertRaisesRegex(RuntimeError, r"already active"):
        with self.trace.trace_probes():
          pass
    with self.trace.trace_probes():
      self.assertTrue(self.trace._PROBES_ACTIVE)
    self.assertFalse(self.trace._PROBES_ACTIVE)

  def test_trace_probes_normal_exit_restores_and_clears_flag(self):
    originals = self._originals()
    with self.trace.trace_probes():
      for label, (cls, attr) in _STAGE_TARGETS.items():
        self.assertIsNot(getattr(cls, attr), originals[label])
      self.assertTrue(self.trace._PROBES_ACTIVE)
    for label, (cls, attr) in _STAGE_TARGETS.items():
      self.assertIs(getattr(cls, attr), originals[label])
    self.assertFalse(self.trace._PROBES_ACTIVE)

  def test_mid_install_failure_restores_partial_wraps(self):
    originals = self._originals()
    second = list(_STAGE_TARGETS)[1]

    def boom(original):
      raise RuntimeError("inject install failure")

    with self.assertRaisesRegex(RuntimeError, r"inject install failure"):
      with self.trace.trace_probes(wrappers={second: boom}):
        pass
    for label, (cls, attr) in _STAGE_TARGETS.items():
      self.assertIs(
          getattr(cls, attr),
          originals[label],
          msg=f"{label} should be restored after mid-install failure",
      )
    self.assertFalse(self.trace._PROBES_ACTIVE)

  def test_probe_targets_exposes_five_stage_labels(self):
    self.trace._load_probe_targets()
    self.assertIsNotNone(self.trace._PROBE_TARGETS)
    self.assertCountEqual(
        self.trace._PROBE_TARGETS.keys(),
        list(_STAGE_TARGETS),
    )

  def test_trace_probes_partial_wrappers_overlay_and_restore(self):
    originals = self._originals()
    sentinel = object()

    def custom_factory(original):
      del original

      def sentinel_call(self, *args, **kwargs):
        del self, args, kwargs
        return sentinel

      return sentinel_call

    with self.trace.trace_probes(wrappers={"parse": custom_factory}):
      parse_cls, parse_attr = _STAGE_TARGETS["parse"]
      self.assertIs(getattr(parse_cls, parse_attr)(None), sentinel)
      for label, (cls, attr) in _STAGE_TARGETS.items():
        if label == "parse":
          continue
        self.assertIsNot(
            getattr(cls, attr),
            originals[label],
            msg=f"{label} should be identity-wrapped",
        )
    for label, (cls, attr) in _STAGE_TARGETS.items():
      self.assertIs(
          getattr(cls, attr),
          originals[label],
          msg=f"{label} should be restored",
      )

  def test_trace_probes_empty_wrappers_installs_identity(self):
    originals = self._originals()
    with self.trace.trace_probes(wrappers={}):
      for label, (cls, attr) in _STAGE_TARGETS.items():
        self.assertIsNot(
            getattr(cls, attr),
            originals[label],
            msg=f"{label} should be wrapped under wrappers={{}}",
        )
    for label, (cls, attr) in _STAGE_TARGETS.items():
      self.assertIs(getattr(cls, attr), originals[label])

  def test_trace_probes_generator_and_chunk_identity_shapes(self):
    pull_counts = {"model": 0, "align": 0}

    def make_counting_gen(label):
      def original(self, *args, **kwargs):
        del self, args, kwargs
        pull_counts[label] += 1
        yield "a"
        pull_counts[label] += 1
        yield "b"

      return original

    chunk_token = object()

    def chunk_original(self, *args, **kwargs):
      del self, args, kwargs
      return chunk_token

    model_cls, model_attr = _STAGE_TARGETS["model"]
    align_cls, align_attr = _STAGE_TARGETS["align"]
    chunk_cls, chunk_attr = _STAGE_TARGETS["chunk"]
    self.enter_context(
        mock.patch.object(model_cls, model_attr, make_counting_gen("model"))
    )
    self.enter_context(
        mock.patch.object(align_cls, align_attr, make_counting_gen("align"))
    )
    self.enter_context(mock.patch.object(chunk_cls, chunk_attr, chunk_original))

    with self.trace.trace_probes():
      model_gen = getattr(model_cls, model_attr)(None)
      self.assertEqual(pull_counts["model"], 0)
      self.assertEqual(next(model_gen), "a")
      self.assertEqual(pull_counts["model"], 1)
      self.assertEqual(next(model_gen), "b")
      self.assertEqual(pull_counts["model"], 2)

      align_gen = getattr(align_cls, align_attr)(None)
      self.assertEqual(pull_counts["align"], 0)
      self.assertEqual(list(align_gen), ["a", "b"])
      self.assertEqual(pull_counts["align"], 2)

      chunk_result = getattr(chunk_cls, chunk_attr)(None)
      self.assertIs(chunk_result, chunk_token)

  def test_trace_probes_rejects_unknown_wrapper_keys(self):
    with self.assertRaisesRegex(ValueError, r"unknown.*wrapper"):
      with self.trace.trace_probes(wrappers={"not-a-stage": lambda o: o}):
        pass

  def test_self_check_probe_restore_silent_success(self):
    originals = self._originals()
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
      result = self.trace._self_check_probe_restore()
    self.assertIsNone(result)
    self.assertEqual(out.getvalue(), "")
    self.assertEqual(err.getvalue(), "")
    for label, (cls, attr) in _STAGE_TARGETS.items():
      self.assertIs(
          getattr(cls, attr),
          originals[label],
          msg=f"{label} should match pre-check original",
      )
    self.assertFalse(self.trace._PROBES_ACTIVE)

  def test_self_check_probe_restore_failure_exits(self):
    originals = self._originals()

    def noop_restore(saved):
      del saved

    with mock.patch.object(self.trace, "_restore_probe_attrs", noop_restore):
      out = io.StringIO()
      err = io.StringIO()
      with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with self.assertRaises(SystemExit) as cm:
          self.trace._self_check_probe_restore()
      self.assertEqual(cm.exception.code, 1)
      self.assertEqual(out.getvalue(), "")
      self.assertRegex(err.getvalue(), r"(?i)error:.*probe")
    # Clean up leaked wraps from the noop restore so later tests stay isolated.
    for label, (cls, attr) in _STAGE_TARGETS.items():
      setattr(cls, attr, originals[label])
    self.trace._PROBES_ACTIVE = False

  def test_main_runs_self_check_after_catalog_silently(self):
    self.assertTrue(hasattr(self.trace, "_self_check_probe_restore"))
    calls = []

    def spy():
      calls.append(1)

    out = io.StringIO()
    err = io.StringIO()
    with mock.patch.object(self.trace, "_self_check_probe_restore", spy):
      with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = self.trace.main(["--catalog-only"])
    self.assertEqual(code, 0)
    self.assertEqual(calls, [1])
    self.assertEqual(err.getvalue(), "")
    text = out.getvalue()
    labels = [
        "prompt-template",
        "chunk",
        "prompt",
        "model",
        "parse",
        "align",
        "annotated-document",
    ]
    indexes = [text.index(f"[{label}]") for label in labels]
    self.assertEqual(indexes, sorted(indexes))
    self.assertIn("helper: WordAligner.align_extractions", text)
    self.assertNotIn("probe self-check", text)
    self.assertNotIn("grounding pair", text)


_STUB_GENERATE_BODY = {
    "response": '{"extractions": [{"symptom": "headache"}]}',
    "done": True,
}
_STUB_TAGS_BODY = {"models": [{"name": "gemma3:4b", "model": "gemma3:4b"}]}


class _StubOllama(http.server.ThreadingHTTPServer):
  """Local Ollama-compatible server with per-path hit counters."""

  daemon_threads = True

  def __init__(self) -> None:
    super().__init__(("127.0.0.1", 0), _StubHandler)
    self.hits = {"/api/tags": 0, "/api/generate": 0}
    self.tags_body = _STUB_TAGS_BODY
    self.tags_status = 200
    self.tags_raw = None
    self.tags_delay = 0.0

  @property
  def url(self) -> str:
    return f"http://127.0.0.1:{self.server_address[1]}"


def _start_stub(test: absltest.TestCase) -> _StubOllama:
  """Start a stub Ollama server and register shutdown on the test."""
  stub = _StubOllama()
  threading.Thread(target=stub.serve_forever, daemon=True).start()
  test.addCleanup(stub.server_close)
  test.addCleanup(stub.shutdown)
  return stub


class _StubHandler(http.server.BaseHTTPRequestHandler):

  def log_message(self, *args) -> None:
    pass

  def _reply(
      self, body: dict, status: int = 200, raw: bytes | None = None
  ) -> None:
    payload = raw if raw is not None else json.dumps(body).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(payload)))
    self.end_headers()
    self.wfile.write(payload)

  def do_GET(self) -> None:  # pylint: disable=invalid-name
    self.server.hits[self.path] = self.server.hits.get(self.path, 0) + 1
    time.sleep(self.server.tags_delay)
    self._reply(
        self.server.tags_body, self.server.tags_status, self.server.tags_raw
    )

  def do_POST(self) -> None:  # pylint: disable=invalid-name
    self.rfile.read(int(self.headers.get("Content-Length", 0)))
    self.server.hits[self.path] = self.server.hits.get(self.path, 0) + 1
    self._reply(_STUB_GENERATE_BODY)


class TraceExtractDocumentTest(absltest.TestCase):
  """Config document_path → text_or_documents (quick 261011-cst)."""

  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()
    self.base = self.trace.load_config(self.trace._CONFIG_PATH)
    self.tmp = pathlib.Path(self.enter_context(tempfile.TemporaryDirectory()))

  def _config_with_doc(self, text: str, rel_name: str = "doc.txt") -> dict:
    path = self.tmp / rel_name
    path.write_text(text, encoding="utf-8")
    return {**self.base, "document_path": str(path)}

  def test_extract_kwargs_text_from_document_path_not_sample_text(self):
    body = "Unique document body for kwargs mapping."
    config = self._config_with_doc(body)
    config["sample_text"] = "MUST NOT BE USED"
    kwargs = self.trace._extract_kwargs(config)
    self.assertEqual(kwargs["text_or_documents"], body)
    self.assertNotEqual(kwargs["text_or_documents"], config["sample_text"])

  def test_document_path_resolves_relative_to_repo_root_not_cwd(self):
    body = "repo-relative document contents"
    rel = "data/_trace_doc_test.txt"
    abs_path = self.trace._REPO_ROOT / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(body, encoding="utf-8")
    self.addCleanup(abs_path.unlink)
    config = {**self.base, "document_path": rel}
    cwd = self.tmp / "elsewhere"
    cwd.mkdir()
    prior = pathlib.Path.cwd()
    try:
      os.chdir(cwd)
      kwargs = self.trace._extract_kwargs(config)
    finally:
      os.chdir(prior)
    self.assertEqual(kwargs["text_or_documents"], body)

  def test_missing_document_exits_with_error_and_resolved_path(self):
    missing = self.tmp / "no-such-document.txt"
    config = {**self.base, "document_path": str(missing)}
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
      with self.assertRaises(SystemExit) as cm:
        self.trace._extract_kwargs(config)
    self.assertEqual(cm.exception.code, 1)
    self.assertStartsWith(err.getvalue(), "Error:")
    self.assertIn(str(missing.resolve()), err.getvalue())

  def test_extract_kwargs_includes_chunk_buffer_from_config(self):
    config = self._config_with_doc("short")
    config["max_char_buffer"] = 2500
    config["context_window_chars"] = 120
    kwargs = self.trace._extract_kwargs(config)
    self.assertEqual(kwargs["max_char_buffer"], 2500)
    self.assertEqual(kwargs["context_window_chars"], 120)

  def test_extract_kwargs_passes_null_context_window_chars(self):
    config = self._config_with_doc("short")
    config["max_char_buffer"] = 1000
    config["context_window_chars"] = None
    kwargs = self.trace._extract_kwargs(config)
    self.assertIn("context_window_chars", kwargs)
    self.assertIsNone(kwargs["context_window_chars"])


class TraceExtractLiveTest(absltest.TestCase):
  """Live path against a local stub Ollama server (Phase 5)."""

  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()
    self.config = self.trace.load_config(self.trace._CONFIG_PATH)
    # Short temp document so the stub still sees exactly one /api/generate.
    tmp = pathlib.Path(self.enter_context(tempfile.TemporaryDirectory()))
    doc = tmp / "short.txt"
    doc.write_text(
        "Patient reports a headache since Monday and takes ibuprofen.",
        encoding="utf-8",
    )
    self.config = {**self.config, "document_path": str(doc)}
    self.stub = _start_stub(self)

  def test_run_live_walks_one_extract_against_stub(self):
    config = {**self.config, "model_url": self.stub.url}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      code = self.trace.run_live(config)
    text = out.getvalue()
    self.assertEqual(code, 0)
    self.assertTrue(text.startswith("lx.extract  model_id=gemma3:4b"))
    self.assertIn("[model] OllamaLanguageModel.infer", text)
    self.assertIn('{"extractions": [{"symptom": "headache"}]}', text)
    self.assertIn("[align] Resolver.align", text)
    self.assertEqual(self.stub.hits, {"/api/tags": 1, "/api/generate": 1})

  def test_extract_kwargs_pins_local_ollama_call(self):
    kwargs = self.trace._extract_kwargs(self.config)
    self.assertEqual(kwargs["model_id"], "gemma3:4b")
    self.assertEqual(kwargs["model_url"], self.config["model_url"])
    self.assertEqual(kwargs["extraction_passes"], 1)
    self.assertIs(kwargs["debug"], False)
    self.assertIs(kwargs["show_progress"], False)
    self.assertIs(kwargs["fetch_urls"], False)
    self.assertEqual(
        kwargs["language_model_params"]["timeout"],
        self.config["request_timeout_s"],
    )

  def test_extract_kwargs_omits_cloud_and_schema_keys(self):
    kwargs = self.trace._extract_kwargs(self.config)
    for key in (
        "model",
        "api_key",
        "output_schema",
        "fence_output",
        "language_model_type",
    ):
      self.assertNotIn(key, kwargs)

  def test_main_catalog_only_needs_no_network(self):
    expected = io.StringIO()
    with contextlib.redirect_stdout(expected):
      self.trace.print_call_header(self.config)
      self.trace.print_stage_catalog()
    out = io.StringIO()
    with mock.patch(
        "urllib.request.urlopen", side_effect=AssertionError("network used")
    ):
      with contextlib.redirect_stdout(out):
        code = self.trace.main(["--catalog-only"])
    self.assertEqual(code, 0)
    self.assertEqual(out.getvalue(), expected.getvalue())


def _closed_port_url() -> str:
  with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
  return f"http://127.0.0.1:{port}"


class TraceExtractPreflightTest(parameterized.TestCase):
  """Fail-closed preflight through main() (Phase 5, RUN-02)."""

  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()
    self.stub = _start_stub(self)
    # TemporaryDirectory (not absl create_tempdir): make test runs under pytest,
    # where --test_tmpdir is unset and create_tempdir raises UnparsedFlagAccessError.
    tmp = pathlib.Path(self.enter_context(tempfile.TemporaryDirectory()))
    doc = tmp / "short.txt"
    doc.write_text(
        "short clinical sentence for preflight tests.", encoding="utf-8"
    )
    self.config = {
        **self.trace.load_config(self.trace._CONFIG_PATH),
        "model_url": self.stub.url,
        "preflight_timeout_s": 0.2,
        "document_path": str(doc),
        "max_char_buffer": 1000,
    }
    config_path = tmp / "config.yaml"
    config_path.write_text(yaml.safe_dump(self.config), encoding="utf-8")
    self.enter_context(
        mock.patch.object(self.trace, "_CONFIG_PATH", config_path)
    )

  def _run_main(self) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
      code = self.trace.main([])
    return code, out.getvalue(), err.getvalue()

  def _assert_fail_closed(self, expected: list[str]) -> None:
    code, out, err = self._run_main()
    self.assertEqual(code, 1)
    self.assertEqual(out, "")
    self.assertLen(err.splitlines(), 1)
    self.assertStartsWith(err, "Error:")
    for fragment in expected:
      self.assertIn(fragment, err)
    self.assertEqual(self.stub.hits["/api/generate"], 0)

  def test_preflight_fails_closed_when_host_unreachable(self):
    url = _closed_port_url()
    self.config["model_url"] = url
    pathlib.Path(self.trace._CONFIG_PATH).write_text(
        yaml.safe_dump(self.config), encoding="utf-8"
    )
    self._assert_fail_closed([url.removeprefix("http://"), "ollama serve"])

  def test_preflight_fails_closed_when_model_missing(self):
    self.stub.tags_body = {
        "models": [{"name": "gemma3:4b-it-qat"}, {"name": "qwen2.5:7b"}]
    }
    self._assert_fail_closed(["gemma3:4b", "ollama pull gemma3:4b"])

  def test_preflight_fails_closed_on_http_500(self):
    self.stub.tags_status = 500
    self._assert_fail_closed(["HTTP 500"])

  @parameterized.named_parameters(
      dict(testcase_name="not_json", raw=b"not json"),
      dict(testcase_name="no_models_list", raw=b'{"models": "none"}'),
  )
  def test_preflight_fails_closed_on_malformed_tags(self, raw):
    self.stub.tags_raw = raw
    self._assert_fail_closed(["unexpected /api/tags response"])

  def test_preflight_fails_closed_on_timeout(self):
    self.stub.tags_delay = 1.0
    started = time.monotonic()
    self._assert_fail_closed(["not reachable"])
    self.assertLess(time.monotonic() - started, 3.0)

  def test_preflight_accepts_latest_tag(self):
    self.stub.tags_body = {"models": [{"name": "gemma3:4b:latest"}]}
    self.assertIsNone(
        self.trace.preflight_ollama(self.stub.url, "gemma3:4b", 1.0)
    )

  @parameterized.named_parameters(
      dict(testcase_name="file_scheme", url="file:///etc/passwd"),
      dict(testcase_name="no_scheme", url="localhost:11434"),
  )
  def test_preflight_rejects_non_http_url_without_request(self, url):
    with mock.patch(
        "urllib.request.urlopen", side_effect=AssertionError("request sent")
    ):
      with self.assertRaisesRegex(self.trace.PreflightError, "http"):
        self.trace.preflight_ollama(url, "gemma3:4b", 1.0)


@absltest.skipUnless(
    os.environ.get("TRACE_LIVE_OLLAMA") == "1",
    "set TRACE_LIVE_OLLAMA=1 to hit local Ollama",
)
class TraceExtractRealOllamaTest(absltest.TestCase):
  """End-to-end run against local gemma3:4b (Phase 5, RUN-01 SC1)."""

  def test_run_live_completes_against_local_gemma3(self):
    trace = _load_script_module()
    config = trace.load_config(trace._CONFIG_PATH)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      code = trace.run_live(config)
    text = out.getvalue()
    lines = text.splitlines()
    self.assertEqual(code, 0)
    self.assertEqual(lines[-1], trace._SINGLE_CALL_LINE)
    self.assertIn("[model] OllamaLanguageModel.infer", text)


class TraceExtractGuardTest(absltest.TestCase):
  """Single-inference contract (Phase 5, RUN-03)."""

  def setUp(self):
    super().setUp()
    self.trace = _load_script_module()
    self.base = self.trace.load_config(self.trace._CONFIG_PATH)
    tmp = pathlib.Path(self.enter_context(tempfile.TemporaryDirectory()))
    self.doc = tmp / "doc.txt"
    self.doc.write_text(
        "Patient reports a headache since Monday and takes ibuprofen.",
        encoding="utf-8",
    )
    self.stub = _start_stub(self)
    self.config = {
        **self.base,
        "document_path": str(self.doc),
        "model_url": self.stub.url,
        "max_char_buffer": 1000,
    }

  def _model_record(
      self,
      prompts: list[str] | tuple[str, ...],
      prompt_index: int = 0,
      in_data: dict | None = None,
  ) -> object:
    shared = in_data or {
        "batch_prompts": tuple(prompts),
        "batch_size": len(prompts),
        "kwargs": {},
    }
    return self.trace.StageRecord(
        "model",
        shared,
        {
            "prompt_index": prompt_index,
            "score": 1.0,
            "raw_model_text": _CANNED,
        },
    )

  def test_run_live_ends_with_single_call_line_and_one_generate(self):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      code = self.trace.run_live(self.config)
    lines = out.getvalue().splitlines()
    self.assertEqual(code, 0)
    self.assertEqual(lines[-1], self.trace._SINGLE_CALL_LINE)
    self.assertEqual(self.stub.hits, {"/api/tags": 1, "/api/generate": 1})

  def test_check_single_inference_rejects_zero_calls(self):
    msg = self.trace.check_single_inference([])
    self.assertIsNotNone(msg)
    self.assertIn("single-inference contract", msg)
    self.assertIn("0", msg)

  def test_check_single_inference_rejects_two_calls(self):
    records = [
        self._model_record(["p1"]),
        self._model_record(["p2"]),
    ]
    msg = self.trace.check_single_inference(records)
    self.assertIsNotNone(msg)
    self.assertIn("single-inference contract", msg)
    self.assertIn("2", msg)

  def test_check_single_inference_rejects_multi_prompt_batch(self):
    msg = self.trace.check_single_inference(
        [self._model_record(["prompt-a", "prompt-b"])]
    )
    self.assertIsNotNone(msg)
    self.assertIn("2 prompts", msg)

  def test_run_live_refuses_document_longer_than_max_char_buffer(self):
    self.doc.write_text("x" * 1200, encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
      code = self.trace.run_live(self.config)
    self.assertEqual(code, 1)
    self.assertEqual(out.getvalue(), "")
    self.assertStartsWith(err.getvalue(), "Error:")
    self.assertIn("max_char_buffer", err.getvalue())
    self.assertEqual(self.stub.hits.get("/api/tags", 0), 0)
    self.assertEqual(self.stub.hits.get("/api/generate", 0), 0)

  def test_main_returns_1_when_single_inference_guard_fails(self):
    config_path = self.doc.parent / "config.yaml"
    config_path.write_text(yaml.safe_dump(self.config), encoding="utf-8")
    self.enter_context(
        mock.patch.object(self.trace, "_CONFIG_PATH", config_path)
    )
    # Identity wrappers leave the sink empty → 0 Ollama infer records.
    self.enter_context(
        mock.patch.object(
            self.trace,
            "make_stage_wrappers",
            return_value={},
        )
    )
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
      code = self.trace.main([])
    self.assertEqual(code, 1)
    err_text = err.getvalue()
    self.assertIn("single-inference contract", err_text)
    self.assertTrue(
        any(line.startswith("Error:") for line in err_text.splitlines()),
        err_text,
    )


if __name__ == "__main__":
  absltest.main()
