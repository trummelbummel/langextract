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

from absl.testing import absltest

from langextract import data
from langextract import resolver
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


if __name__ == "__main__":
  absltest.main()
