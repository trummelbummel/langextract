#!/usr/bin/env python3
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

"""Offline synthetic demo for gold-set evaluation metrics.

Builds predicted/gold AnnotatedDocuments (no network), runs
``lx.evaluation.evaluate`` (default SameClass + SpanIoU(0.5)), prints the
report, optionally writes via ``--output``, and checks against EXPECTED.

Usage:
    python scripts/evaluate_synthetic.py
    python scripts/evaluate_synthetic.py --output /tmp/eval_report.txt
"""

from __future__ import annotations

import argparse
import sys

import langextract as lx

# Hand-checked (SameClass + SpanIoU 0.5):
# doc-perfect: identical condition → TP
# doc-miss: matching condition → TP; pred-only med → FP; gold-only med → FN
_SCORE_FIELDS = ("tp", "fp", "fn", "f1")
EXPECTED = {
    "micro": {"tp": 2, "fp": 1, "fn": 1, "f1": 2 / 3},
    "per_class": {
        "condition": {"tp": 2, "fp": 0, "fn": 0, "f1": 1.0},
        "medication": {"tp": 0, "fp": 1, "fn": 1, "f1": 0.0},
    },
}


def _extraction(
    extraction_class: str, extraction_text: str, start_pos: int, end_pos: int
) -> lx.data.Extraction:
  return lx.data.Extraction(
      extraction_class=extraction_class,
      extraction_text=extraction_text,
      char_interval=lx.data.CharInterval(start_pos=start_pos, end_pos=end_pos),
  )


def build_documents() -> (
    tuple[list[lx.data.AnnotatedDocument], list[lx.data.AnnotatedDocument]]
):
  """Return (predicted, gold); every document sets document_id."""
  perfect_text = "Patient has asthma."
  asthma = _extraction("condition", "asthma", 12, 18)
  miss_text = "Took aspirin; has diabetes; gold expects ibuprofen."
  diabetes = _extraction("condition", "diabetes", 18, 26)  # TP
  aspirin = _extraction("medication", "aspirin", 5, 12)  # FP
  ibuprofen = _extraction("medication", "ibuprofen", 41, 50)  # FN
  predicted = [
      lx.data.AnnotatedDocument(
          document_id="doc-perfect", text=perfect_text, extractions=[asthma]
      ),
      lx.data.AnnotatedDocument(
          document_id="doc-miss",
          text=miss_text,
          extractions=[aspirin, diabetes],
      ),
  ]
  gold = [
      lx.data.AnnotatedDocument(
          document_id="doc-perfect", text=perfect_text, extractions=[asthma]
      ),
      lx.data.AnnotatedDocument(
          document_id="doc-miss",
          text=miss_text,
          extractions=[diabetes, ibuprofen],
      ),
  ]
  return predicted, gold


def format_report(report: lx.evaluation.EvaluationReport) -> str:
  """Readable micro + per-class ClassScore dump."""

  def _line(label: str, score: lx.evaluation.ClassScore) -> str:
    return (
        f"  {label}: tp={score.tp} fp={score.fp} fn={score.fn} "
        f"precision={score.precision!r} recall={score.recall!r} f1={score.f1!r}"
    )

  lines = ["EvaluationReport", _line("micro", report.micro)]
  lines.extend(_line(name, score) for name, score in report.per_class.items())
  return "\n".join(lines) + "\n"


def check_expected(report: lx.evaluation.EvaluationReport) -> None:
  """Exit 1 on stderr when live report disagrees with EXPECTED."""
  mismatches: list[str] = []
  checks = [("micro", report.micro, EXPECTED["micro"])]
  per_class_expected = EXPECTED["per_class"]
  if set(report.per_class) != set(per_class_expected):
    mismatches.append(
        f"per_class keys: live={sorted(report.per_class)!r} "
        f"expected={sorted(per_class_expected)!r}"
    )
  else:
    for class_name, expected_score in per_class_expected.items():
      checks.append((
          f"per_class[{class_name!r}]",
          report.per_class[class_name],
          expected_score,
      ))
  for prefix, live, expected in checks:
    for field_name in _SCORE_FIELDS:
      live_value = getattr(live, field_name)
      if live_value != expected[field_name]:
        mismatches.append(
            f"{prefix}.{field_name}: live={live_value!r} "
            f"expected={expected[field_name]!r}"
        )
  if mismatches:
    print("EXPECTED mismatch:", file=sys.stderr)
    for line in mismatches:
      print(f"  {line}", file=sys.stderr)
    raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
      description="Run gold-set evaluate on synthetic predicted/gold docs."
  )
  parser.add_argument(
      "--output",
      default=None,
      help="Optional path to write the same report text printed to stdout.",
  )
  args = parser.parse_args(argv)
  predicted, gold = build_documents()
  report = lx.evaluation.evaluate(predicted, gold)
  report_text = format_report(report)
  print(report_text, end="")
  if args.output is not None:
    with open(args.output, "w", encoding="utf-8") as output_file:
      output_file.write(report_text)
  check_expected(report)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
