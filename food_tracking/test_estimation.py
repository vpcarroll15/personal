"""Unit tests for the AI calorie estimation service."""

import os
from unittest.mock import Mock, patch

from django.test import TestCase

from food_tracking import estimation
from food_tracking.estimation import EstimateResult


class GetClientTests(TestCase):
    """Tests for Anthropic client construction."""

    @patch("food_tracking.estimation.Anthropic")
    def test_get_client_uses_api_key(self, mock_anthropic):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "secret"}):
            estimation._get_client()
        mock_anthropic.assert_called_once_with(api_key="secret")


def _make_tool_use_response(
    description: str = "Burrito bowl",
    total_calories: int = 650,
    confidence: str = "medium",
    items: list | None = None,
) -> Mock:
    """Build a fake Anthropic response containing a record_estimate tool call."""
    block = Mock()
    block.type = "tool_use"
    block.name = estimation.ESTIMATE_TOOL_NAME
    block.input = {
        "description": description,
        "total_calories": total_calories,
        "confidence": confidence,
        "items": items if items is not None else [{"name": "rice", "calories": 200}],
    }
    response = Mock()
    response.content = [block]
    response.stop_reason = "tool_use"
    return response


class RunEstimateTests(TestCase):
    """Tests for the low-level _run_estimate parsing."""

    @patch("food_tracking.estimation._get_client")
    def test_estimate_from_text_parses_tool_call(self, mock_get_client):
        client = Mock()
        client.messages.create.return_value = _make_tool_use_response(
            description="Apple", total_calories=95, confidence="high"
        )
        mock_get_client.return_value = client

        result = estimation.estimate_from_text("one apple")

        self.assertIsInstance(result, EstimateResult)
        self.assertEqual(result.description, "Apple")
        self.assertEqual(result.calories, 95)
        self.assertEqual(result.confidence, "high")

    @patch("food_tracking.estimation._get_client")
    def test_run_estimate_raises_without_tool_use(self, mock_get_client):
        text_block = Mock()
        text_block.type = "text"
        response = Mock()
        response.content = [text_block]
        client = Mock()
        client.messages.create.return_value = response
        mock_get_client.return_value = client

        with self.assertRaises(ValueError):
            estimation.estimate_from_text("mystery food")

    @patch("food_tracking.estimation._get_client")
    def test_estimate_from_text_enables_thinking_with_auto_tool_choice(
        self, mock_get_client
    ):
        client = Mock()
        client.messages.create.return_value = _make_tool_use_response()
        mock_get_client.return_value = client

        estimation.estimate_from_text("pizza slice")

        _, kwargs = client.messages.create.call_args
        self.assertEqual(kwargs["model"], estimation.ESTIMATION_MODEL)
        # Thinking is incompatible with a forced tool choice, so the call must
        # use adaptive thinking + auto tool choice together.
        self.assertEqual(kwargs["thinking"], {"type": "adaptive"})
        self.assertEqual(kwargs["tool_choice"], {"type": "auto"})
        # Effort is capped so recipe estimates don't think past the web
        # server's request timeout.
        self.assertEqual(
            kwargs["output_config"], {"effort": estimation.ESTIMATION_EFFORT}
        )

    @patch("food_tracking.estimation._get_client")
    def test_run_estimate_skips_non_tool_blocks(self, mock_get_client):
        # With auto tool choice the model may emit thinking/text blocks before
        # the tool call; parsing must find the tool_use block among them.
        thinking_block = Mock()
        thinking_block.type = "thinking"
        text_block = Mock()
        text_block.type = "text"
        tool_response = _make_tool_use_response(
            description="Plantains, beans, rice, and pizza", total_calories=1250
        )
        tool_response.content = [thinking_block, text_block] + tool_response.content

        client = Mock()
        client.messages.create.return_value = tool_response
        mock_get_client.return_value = client

        result = estimation.estimate_from_text("plantains, beans, rice, pizza")

        self.assertEqual(result.calories, 1250)


class EstimateFromImageTests(TestCase):
    """Tests for image-based estimation."""

    @patch("food_tracking.estimation._get_client")
    def test_estimate_from_image_builds_image_block(self, mock_get_client):
        client = Mock()
        client.messages.create.return_value = _make_tool_use_response()
        mock_get_client.return_value = client

        estimation.estimate_from_image(b"fakebytes", "image/jpeg", note="big plate")

        _, kwargs = client.messages.create.call_args
        content = kwargs["messages"][0]["content"]
        image_block = content[0]
        self.assertEqual(image_block["type"], "image")
        self.assertEqual(image_block["source"]["media_type"], "image/jpeg")
        # Note is folded into the text prompt.
        self.assertIn("big plate", content[1]["text"])

    def test_estimate_from_image_rejects_unsupported_type(self):
        with self.assertRaises(ValueError):
            estimation.estimate_from_image(b"data", "image/tiff")


class EstimateRecipeTests(TestCase):
    """Tests for recipe-fraction estimation."""

    @patch("food_tracking.estimation._get_client")
    def test_estimate_recipe_includes_percent(self, mock_get_client):
        client = Mock()
        client.messages.create.return_value = _make_tool_use_response()
        mock_get_client.return_value = client

        estimation.estimate_recipe("Big lasagna recipe", 0.25)

        _, kwargs = client.messages.create.call_args
        prompt = kwargs["messages"][0]["content"][0]["text"]
        self.assertIn("25%", prompt)
        self.assertIn("Big lasagna recipe", prompt)


class MalformedEstimateTests(TestCase):
    """Tests for defensive handling of malformed/truncated tool calls."""

    @patch("food_tracking.estimation._get_client")
    def test_missing_field_raises_value_error(self, mock_get_client):
        block = Mock()
        block.type = "tool_use"
        block.name = estimation.ESTIMATE_TOOL_NAME
        block.input = {"description": "Soup"}  # no total_calories
        response = Mock()
        response.content = [block]
        response.stop_reason = "tool_use"
        client = Mock()
        client.messages.create.return_value = response
        mock_get_client.return_value = client

        with self.assertRaises(ValueError):
            estimation.estimate_from_text("soup")

    @patch("food_tracking.estimation._get_client")
    def test_non_numeric_calories_raises_value_error(self, mock_get_client):
        block = Mock()
        block.type = "tool_use"
        block.name = estimation.ESTIMATE_TOOL_NAME
        block.input = {
            "description": "Soup",
            "total_calories": "lots",
            "confidence": "low",
        }
        response = Mock()
        response.content = [block]
        response.stop_reason = "tool_use"
        client = Mock()
        client.messages.create.return_value = response
        mock_get_client.return_value = client

        with self.assertRaises(ValueError):
            estimation.estimate_from_text("soup")

    @patch("food_tracking.estimation._get_client")
    def test_truncated_response_raises_value_error(self, mock_get_client):
        response = Mock()
        response.stop_reason = "max_tokens"
        response.content = []
        client = Mock()
        client.messages.create.return_value = response
        mock_get_client.return_value = client

        with self.assertRaises(ValueError):
            estimation.estimate_from_text("huge meal")

    def test_parse_estimate_rejects_non_dict(self):
        with self.assertRaises(ValueError):
            estimation._parse_estimate("not a dict")

    def test_parse_estimate_defaults_confidence(self):
        result = estimation._parse_estimate(
            {"description": "Apple", "total_calories": 95}
        )
        self.assertEqual(result.confidence, "low")
