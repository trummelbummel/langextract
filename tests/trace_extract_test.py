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
      self.trace.print_grounding_pair(parse, align)
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


if __name__ == "__main__":
  absltest.main()
