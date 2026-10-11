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

"""Tests for langextract.evaluation metrics and match criteria."""

import dataclasses

from absl.testing import absltest
from absl.testing import parameterized

from langextract.core import data


class MetricsPrfTest(parameterized.TestCase):
  """Hand-worked precision/recall/F1 from count triples (EVAL-04)."""

  @parameterized.named_parameters(
      dict(
          testcase_name="perfect_one_tp",
          tp=1,
          fp=0,
          fn=0,
          precision=1.0,
          recall=1.0,
          f1=1.0,
      ),
      dict(
          testcase_name="duplicate_pred_half_precision",
          tp=1,
          fp=1,
          fn=0,
          precision=0.5,
          recall=1.0,
          f1=2.0 / 3.0,
      ),
      dict(
          testcase_name="empty_all_zero",
          tp=0,
          fp=0,
          fn=0,
          precision=0.0,
          recall=0.0,
          f1=0.0,
      ),
      dict(
          testcase_name="fp_only_zero_rates",
          tp=0,
          fp=1,
          fn=0,
          precision=0.0,
          recall=0.0,
          f1=0.0,
      ),
      dict(
          testcase_name="fn_only_zero_rates",
          tp=0,
          fp=0,
          fn=1,
          precision=0.0,
          recall=0.0,
          f1=0.0,
      ),
  )
  def test_prf_from_counts(self, tp, fp, fn, precision, recall, f1):
    from langextract.evaluation import prf_from_counts

    score = prf_from_counts(tp, fp, fn)
    self.assertEqual(score.tp, tp)
    self.assertEqual(score.fp, fp)
    self.assertEqual(score.fn, fn)
    self.assertEqual(score.precision, precision)
    self.assertEqual(score.recall, recall)
    self.assertAlmostEqual(score.f1, f1, places=7)

  def test_class_score_is_frozen(self):
    from langextract.evaluation import ClassScore

    score = ClassScore(precision=1.0, recall=1.0, f1=1.0, tp=1, fp=0, fn=0)
    with self.assertRaises((dataclasses.FrozenInstanceError, AttributeError)):
      score.precision = 0.0  # type: ignore[misc]


class MetricsReportTest(parameterized.TestCase):
  """EvaluationReport aggregation from per-class and micro counts (EVAL-01)."""

  def test_report_from_counts_micro_vs_per_class(self):
    from langextract.evaluation import report_from_counts

    # Insert B before A so alphabetical sort (A then B) is observable.
    report = report_from_counts(
        {"B": (0, 1, 1), "A": (1, 0, 0)}, micro=(1, 1, 1)
    )
    self.assertEqual(list(report.per_class.keys()), ["A", "B"])
    a = report.per_class["A"]
    self.assertEqual(a.precision, 1.0)
    self.assertEqual(a.recall, 1.0)
    self.assertEqual(a.f1, 1.0)
    b = report.per_class["B"]
    self.assertEqual(b.precision, 0.0)
    self.assertEqual(b.recall, 0.0)
    self.assertEqual(b.f1, 0.0)
    self.assertEqual(report.micro.precision, 0.5)
    self.assertEqual(report.micro.recall, 0.5)
    self.assertEqual(report.micro.f1, 0.5)

  def test_report_from_counts_empty(self):
    from langextract.evaluation import report_from_counts

    report = report_from_counts({}, micro=(0, 0, 0))
    self.assertEqual(report.per_class, {})
    self.assertEqual(report.micro.precision, 0.0)
    self.assertEqual(report.micro.recall, 0.0)
    self.assertEqual(report.micro.f1, 0.0)

  def test_evaluation_report_fields_are_per_class_and_micro_only(self):
    from langextract.evaluation import EvaluationReport

    field_names = {f.name for f in dataclasses.fields(EvaluationReport)}
    self.assertEqual(field_names, {"per_class", "micro"})
    self.assertNotIn("macro", field_names)


def _extraction(
    extraction_class: str,
    start: int | None,
    end: int | None,
    *,
    text: str = "x",
    attributes: dict | None = None,
    interval: data.CharInterval | None | object = ...,
) -> data.Extraction:
  """Build an Extraction with a half-open CharInterval (or None)."""
  if interval is ...:
    if start is None and end is None:
      char_interval = data.CharInterval(None, None)
    else:
      char_interval = data.CharInterval(start, end)
  else:
    char_interval = interval  # type: ignore[assignment]
  return data.Extraction(
      extraction_class=extraction_class,
      extraction_text=text,
      char_interval=char_interval,
      attributes=attributes,
  )


class CriteriaSpanIoUTest(parameterized.TestCase):
  """Hand-worked exclusive-end span_iou and SameClass/SpanIoU (EVAL-02)."""

  @parameterized.named_parameters(
      dict(
          testcase_name="perfect_identical",
          pred=_extraction("A", 0, 5),
          gold=_extraction("A", 0, 5),
          expected=1.0,
      ),
      dict(
          testcase_name="below_threshold_2_over_18",
          pred=_extraction("A", 0, 10),
          gold=_extraction("A", 8, 18),
          expected=2.0 / 18.0,
      ),
      dict(
          testcase_name="above_threshold_0_8",
          pred=_extraction("A", 0, 10),
          gold=_extraction("A", 2, 10),
          expected=0.8,
      ),
      dict(
          testcase_name="none_char_interval",
          pred=_extraction("A", 0, 5, interval=None),
          gold=_extraction("A", 0, 5),
          expected=0.0,
      ),
      dict(
          testcase_name="partial_none_positions",
          pred=_extraction("A", None, None),
          gold=_extraction("A", 0, 5),
          expected=0.0,
      ),
      dict(
          testcase_name="inverted_end_lt_start",
          pred=_extraction("A", 10, 5),
          gold=_extraction("A", 0, 5),
          expected=0.0,
      ),
      dict(
          testcase_name="touching_exclusive_adjacent",
          pred=_extraction("A", 0, 5),
          gold=_extraction("A", 5, 10),
          expected=0.0,
      ),
  )
  def test_span_iou(self, pred, gold, expected):
    from langextract.evaluation import span_iou

    self.assertAlmostEqual(span_iou(pred, gold), expected, places=7)

  def test_same_class_true_when_equal(self):
    from langextract.evaluation import SameClass

    pred = _extraction("A", 0, 5)
    gold = _extraction("A", 10, 15)
    self.assertTrue(SameClass()(pred, gold))

  def test_same_class_false_when_different(self):
    from langextract.evaluation import SameClass

    pred = _extraction("A", 0, 5)
    gold = _extraction("B", 0, 5)
    self.assertFalse(SameClass()(pred, gold))

  def test_span_iou_criterion_default_threshold_is_half(self):
    from langextract.evaluation import SpanIoU

    self.assertEqual(SpanIoU().threshold, 0.5)

  @parameterized.named_parameters(
      dict(
          testcase_name="matches_above_threshold_0_8",
          pred=_extraction("A", 0, 10),
          gold=_extraction("A", 2, 10),
          threshold=0.5,
          expected=True,
      ),
      dict(
          testcase_name="matches_exactly_half",
          pred=_extraction("A", 0, 10),
          gold=_extraction("A", 5, 10),
          threshold=0.5,
          expected=True,
      ),
      dict(
          testcase_name="fails_below_threshold_2_over_18",
          pred=_extraction("A", 0, 10),
          gold=_extraction("A", 8, 18),
          threshold=0.5,
          expected=False,
      ),
  )
  def test_span_iou_criterion(self, pred, gold, threshold, expected):
    from langextract.evaluation import SpanIoU

    self.assertEqual(SpanIoU(threshold)(pred, gold), expected)


if __name__ == "__main__":
  absltest.main()
