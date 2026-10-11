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

"""Tests for langextract.evaluation.metrics."""

import dataclasses

from absl.testing import absltest
from absl.testing import parameterized


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


if __name__ == "__main__":
  absltest.main()
