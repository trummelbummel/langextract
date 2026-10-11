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

"""Gold-set evaluation metrics package."""

from __future__ import annotations

from langextract.evaluation.criteria import AttributesEqual
from langextract.evaluation.criteria import MatchCriterion
from langextract.evaluation.criteria import SameClass
from langextract.evaluation.criteria import span_iou
from langextract.evaluation.criteria import SpanIoU
from langextract.evaluation.criteria import TextMatch
from langextract.evaluation.metrics import ClassScore
from langextract.evaluation.metrics import EvaluationReport
from langextract.evaluation.metrics import prf_from_counts
from langextract.evaluation.metrics import report_from_counts

__all__ = [
    "AttributesEqual",
    "ClassScore",
    "EvaluationReport",
    "MatchCriterion",
    "SameClass",
    "SpanIoU",
    "TextMatch",
    "prf_from_counts",
    "report_from_counts",
    "span_iou",
]
