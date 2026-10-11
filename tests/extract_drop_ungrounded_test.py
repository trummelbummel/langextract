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

"""Tests for drop_ungrounded on lx.extract()."""

from unittest import mock

from absl.testing import absltest

import langextract as lx
from langextract.core import data


def _mixed_document() -> data.AnnotatedDocument:
  grounded = data.Extraction(
      extraction_class="entity",
      extraction_text="Romeo",
      char_interval=data.CharInterval(start_pos=0, end_pos=5),
  )
  ungrounded = data.Extraction(
      extraction_class="entity",
      extraction_text="ghost",
      char_interval=None,
  )
  return data.AnnotatedDocument(
      document_id="doc-1",
      text="Romeo spoke",
      extractions=[grounded, ungrounded],
  )


def _all_grounded_document() -> data.AnnotatedDocument:
  grounded = data.Extraction(
      extraction_class="entity",
      extraction_text="Romeo",
      char_interval=data.CharInterval(start_pos=0, end_pos=5),
  )
  return data.AnnotatedDocument(
      document_id="doc-1",
      text="Romeo spoke",
      extractions=[grounded],
  )


class ExtractDropUngroundedTest(absltest.TestCase):
  """Acceptance tests for the drop_ungrounded flag."""

  def setUp(self):
    super().setUp()
    self.examples = [
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
    self.description = "description"

  def _extract_text(self, *, drop_ungrounded: bool | None = None):
    kwargs = {
        "text_or_documents": "Romeo spoke",
        "prompt_description": self.description,
        "examples": self.examples,
        "model_id": "test-model",
        "api_key": "test-key",
        "use_schema_constraints": False,
        "show_progress": False,
    }
    if drop_ungrounded is not None:
      kwargs["drop_ungrounded"] = drop_ungrounded
    return lx.extract(**kwargs)

  @mock.patch("langextract.annotation.Annotator")
  @mock.patch("langextract.extraction.factory.create_model")
  def test_drop_ungrounded_true_keeps_grounded_only_on_string_path(
      self, mock_create_model, mock_annotator_cls
  ):
    mock_create_model.return_value = mock.MagicMock(requires_fence_output=True)
    mock_annotator_cls.return_value.annotate_text.return_value = (
        _mixed_document()
    )

    result = self._extract_text(drop_ungrounded=True)

    self.assertLen(result.extractions, 1)
    self.assertEqual(result.extractions[0].extraction_text, "Romeo")
    self.assertIsNotNone(result.extractions[0].char_interval)

  @mock.patch("langextract.annotation.Annotator")
  @mock.patch("langextract.extraction.factory.create_model")
  def test_drop_ungrounded_false_keeps_both_on_string_path(
      self, mock_create_model, mock_annotator_cls
  ):
    mock_create_model.return_value = mock.MagicMock(requires_fence_output=True)
    mock_annotator_cls.return_value.annotate_text.return_value = (
        _mixed_document()
    )

    result = self._extract_text(drop_ungrounded=False)

    self.assertLen(result.extractions, 2)

  @mock.patch("langextract.annotation.Annotator")
  @mock.patch("langextract.extraction.factory.create_model")
  def test_drop_ungrounded_default_keeps_both_on_string_path(
      self, mock_create_model, mock_annotator_cls
  ):
    mock_create_model.return_value = mock.MagicMock(requires_fence_output=True)
    mock_annotator_cls.return_value.annotate_text.return_value = (
        _mixed_document()
    )

    result = self._extract_text()

    self.assertLen(result.extractions, 2)

  @mock.patch("langextract.annotation.Annotator")
  @mock.patch("langextract.extraction.factory.create_model")
  def test_drop_ungrounded_true_filters_documents_path(
      self, mock_create_model, mock_annotator_cls
  ):
    mock_create_model.return_value = mock.MagicMock(requires_fence_output=True)
    mock_annotator_cls.return_value.annotate_documents.return_value = iter(
        [_mixed_document()]
    )

    result = lx.extract(
        text_or_documents=[data.Document(text="Romeo spoke", document_id="d1")],
        prompt_description=self.description,
        examples=self.examples,
        model_id="test-model",
        api_key="test-key",
        use_schema_constraints=False,
        show_progress=False,
        drop_ungrounded=True,
    )

    self.assertLen(result, 1)
    self.assertLen(result[0].extractions, 1)
    self.assertEqual(result[0].extractions[0].extraction_text, "Romeo")

  @mock.patch("langextract.annotation.Annotator")
  @mock.patch("langextract.extraction.factory.create_model")
  def test_drop_ungrounded_true_logs_removed_count(
      self, mock_create_model, mock_annotator_cls
  ):
    mock_create_model.return_value = mock.MagicMock(requires_fence_output=True)
    mock_annotator_cls.return_value.annotate_text.return_value = (
        _mixed_document()
    )

    with self.assertLogs(level="INFO") as logs:
      self._extract_text(drop_ungrounded=True)

    joined = "\n".join(logs.output)
    self.assertRegex(joined, r"(?i)1.*ungrounded|ungrounded.*1")

  @mock.patch("langextract.annotation.Annotator")
  @mock.patch("langextract.extraction.factory.create_model")
  def test_drop_ungrounded_true_no_log_when_nothing_removed(
      self, mock_create_model, mock_annotator_cls
  ):
    mock_create_model.return_value = mock.MagicMock(requires_fence_output=True)
    mock_annotator_cls.return_value.annotate_text.return_value = (
        _all_grounded_document()
    )

    with self.assertLogs(level="INFO") as logs:
      # Force at least one INFO so assertLogs does not fail when nothing is
      # emitted by drop_ungrounded.
      import logging

      logging.getLogger().info("probe")
      self._extract_text(drop_ungrounded=True)

    joined = "\n".join(logs.output)
    self.assertNotRegex(joined, r"(?i)ungrounded")
