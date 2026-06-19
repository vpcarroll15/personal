"""
AI-powered calorie estimation using the Anthropic API.

Provides estimates from a food photo, a free-text description (e.g. dictated
voice notes), or a pasted recipe plus the fraction eaten. Each helper returns a
typed EstimateResult; callers decide whether to persist it as a Consumption.
"""

import base64
import os
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

# Constants
# Defaults to the current Sonnet generation; override (e.g. to bump to a newer
# model) via the FOOD_ESTIMATION_MODEL environment variable, no code change.
ESTIMATION_MODEL = os.environ.get("FOOD_ESTIMATION_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 1024
ESTIMATE_TOOL_NAME = "record_estimate"

SUPPORTED_IMAGE_MEDIA_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)

SYSTEM_PROMPT = (
    "You are a nutrition assistant that estimates the calorie content of food. "
    "Estimate the total calories for the food described, accounting for typical "
    "portion sizes and preparation. Be realistic, not conservative. Always call "
    "the record_estimate tool with your best single-number estimate. If the "
    "portion is ambiguous, assume a typical serving and reflect the uncertainty "
    "in the confidence field."
)

ESTIMATE_TOOL: dict[str, Any] = {
    "name": ESTIMATE_TOOL_NAME,
    "description": "Record a structured calorie estimate for a food item or meal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Short label for the food/meal, e.g. 'Chicken burrito bowl'.",
            },
            "total_calories": {
                "type": "integer",
                "description": "Best single estimate of total calories eaten.",
            },
            "items": {
                "type": "array",
                "description": "Breakdown of the components that make up the total.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "calories": {"type": "integer"},
                    },
                    "required": ["name", "calories"],
                    "additionalProperties": False,
                },
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "How confident the estimate is.",
            },
        },
        "required": ["description", "total_calories", "items", "confidence"],
        "additionalProperties": False,
    },
}


@dataclass
class EstimateResult:
    """A structured calorie estimate returned by the model."""

    description: str
    calories: int
    confidence: str
    items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "calories": self.calories,
            "confidence": self.confidence,
            "items": self.items,
        }


def _get_client() -> Anthropic:
    """Construct an Anthropic client from the environment."""
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _parse_estimate(data: Any) -> EstimateResult:
    """Build an EstimateResult from a tool_use input, validating shape.

    The forced tool call means the SDK hands us a parsed dict (not raw JSON),
    but the model can still omit a field or return a non-numeric calorie value
    (e.g. if the response is truncated). Treat any such shape as a clean,
    user-facing error rather than letting a KeyError/TypeError become a 500.
    """
    if not isinstance(data, dict):
        raise ValueError("Could not read the calorie estimate from the model.")
    try:
        return EstimateResult(
            description=str(data["description"]),
            calories=int(data["total_calories"]),
            confidence=str(data.get("confidence", "low")),
            items=list(data.get("items", [])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Could not read the calorie estimate from the model.") from exc


def _run_estimate(content: list[dict[str, Any]]) -> EstimateResult:
    """Send a user content payload to Claude and parse the forced tool call."""
    client = _get_client()
    response = client.messages.create(
        model=ESTIMATION_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=[ESTIMATE_TOOL],
        tool_choice={"type": "tool", "name": ESTIMATE_TOOL_NAME},
        messages=[{"role": "user", "content": content}],
    )

    if response.stop_reason == "max_tokens":
        raise ValueError("The estimate was cut off — please try again.")

    for block in response.content:
        if block.type == "tool_use" and block.name == ESTIMATE_TOOL_NAME:
            return _parse_estimate(block.input)

    raise ValueError("Claude did not return a calorie estimate.")


def estimate_from_image(
    image_bytes: bytes, media_type: str, note: str = ""
) -> EstimateResult:
    """Estimate calories from a food photo, with an optional text note."""
    if media_type not in SUPPORTED_IMAGE_MEDIA_TYPES:
        raise ValueError(f"Unsupported image type: {media_type}")

    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")
    prompt = "Estimate the calories in this food."
    if note:
        prompt = f"{prompt} Additional context from the user: {note}"

    content: list[dict[str, Any]] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            },
        },
        {"type": "text", "text": prompt},
    ]
    return _run_estimate(content)


def estimate_from_text(text: str) -> EstimateResult:
    """Estimate calories from a free-text food description."""
    prompt = f"Estimate the calories in this food: {text}"
    return _run_estimate([{"type": "text", "text": prompt}])


def estimate_recipe(recipe_text: str, fraction: float) -> EstimateResult:
    """Estimate calories for the portion of a recipe the user actually ate.

    `fraction` is the share of the whole recipe consumed (e.g. 0.25 for a
    quarter). The model computes the recipe's total calories, then scales to the
    eaten portion.
    """
    percent = round(fraction * 100)
    prompt = (
        "Here is a full recipe. Estimate the calories for the entire recipe as "
        f"prepared, then report the calories for the {percent}% of it that the "
        "user ate. Report the eaten portion's calories in total_calories.\n\n"
        f"Recipe:\n{recipe_text}"
    )
    return _run_estimate([{"type": "text", "text": prompt}])
