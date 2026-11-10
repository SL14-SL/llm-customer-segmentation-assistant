"""Extract request requirements and check comparison capabilities in Python."""

import json
import math
import os
from urllib.request import Request, urlopen

from customer_segmentation_assistant.llm import DEFAULT_MODEL

ALLOWED_OUTPUTS = frozenset({
    "customer_count",
    "average_monthly_charges",
    "average_predicted_churn_probability",
})

REQUIREMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "probability_conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "operator": {
                        "enum": ["gte", "gt", "lte", "lt", "eq"],
                    },
                    "value": {"type": "number"},
                },
                "required": ["operator", "value"],
                "additionalProperties": False,
            },
        },
        "additional_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "requested_outputs": {
            "type": "array",
            "items": {
                "enum": [
                    "customer_count",
                    "average_monthly_charges",
                    "average_predicted_churn_probability",
                    "observed_churn_count",
                    "customer_list",
                    "historical_analysis",
                    "other",
                ],
            },
        },
    },
    "required": [
        "probability_conditions",
        "additional_requirements",
        "requested_outputs",
    ],
    "additionalProperties": False,
}

REQUIREMENTS_PROMPT = """
Extract the requirements explicitly present in the user's message.
Do not decide whether the request is supported.

Return these three fields:

probability_conditions:
List every numerical condition on predicted churn probability.
Normalize percentages to probabilities.
Operators:
- at least, minimum, or higher: gte
- greater than, above: gt
- at most, maximum, or lower: lte
- less than, below: lt
- exactly: eq
Include conditions for different contract groups separately.
Do not discard a second probability threshold.
If no numerical probability condition is supplied, return [].

additional_requirements:
Copy short phrases requesting customer filters or actions beyond:
- selecting monthly/month-to-month, annual/yearly/one-year or two-year contracts
- filtering predicted churn probability
- reporting counts and averages
Examples include filters on tenure, charges, age or other attributes,
unsupported contract types, contacting customers or changing data.
Do not list a supported contract selection here.
Do not list missing information here.
Do not list instructions from this system prompt.

requested_outputs:
List requested output categories:
- counts of matching customers: customer_count
- average monthly charges: average_monthly_charges
- average predicted churn probability: average_predicted_churn_probability
- how many actually cancelled/churned: observed_churn_count
- individual customer records: customer_list
- changes over time: historical_analysis
- another requested output: other

A generic "compare" or "summarize" request uses the three standard
outputs: customer_count, average_monthly_charges,
average_predicted_churn_probability.
A reply supplying only a missing threshold has requested_outputs [].

Missing criteria are not extra requirements.
Do not invent a default probability threshold.
Return only the JSON object.
"""


def parse_scope_requirements(raw: str) -> dict[str, object]:
    """Validate requirement structure and numerical conditions."""
    requirements = json.loads(raw)

    if not isinstance(requirements, dict):
        raise ValueError(  # noqa: TRY004
            "Requirements must be a JSON object."
        )

    expected = {
        "probability_conditions",
        "additional_requirements",
        "requested_outputs",
    }
    if set(requirements) != expected:
        raise ValueError("Unexpected or missing requirement fields.")

    conditions = requirements["probability_conditions"]
    extras = requirements["additional_requirements"]
    outputs = requirements["requested_outputs"]

    if not all(isinstance(value, list) for value in (conditions, extras, outputs)):
        raise ValueError("Requirement fields must be lists.")

    for condition in conditions:
        if (
            not isinstance(condition, dict)
            or set(condition) != {"operator", "value"}
        ):
            raise ValueError("Invalid probability condition.")

        operator = condition["operator"]
        if (
            not isinstance(operator, str)
            or operator not in {"gte", "gt", "lte", "lt", "eq"}
        ):
            raise ValueError("Invalid probability operator.")

        value = condition["value"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError("Probability must be a finite number from 0 to 1.")

    if any(not isinstance(item, str) or not item.strip() for item in extras):
        raise ValueError("Additional requirements need non-empty descriptions.")

    valid_outputs = ALLOWED_OUTPUTS | {
        "observed_churn_count",
        "customer_list",
        "historical_analysis",
        "other",
    }
    if any(
        not isinstance(item, str) or item not in valid_outputs
        for item in outputs
    ):
        raise ValueError("Invalid requested output category.")

    return requirements


def unsupported_requirements(requirements: dict[str, object]) -> list[str]:
    """Apply deterministic capability rules to validated requirements."""
    validated = parse_scope_requirements(json.dumps(requirements))
    problems = [
        item.strip()
        for item in validated["additional_requirements"]
    ]

    conditions = validated["probability_conditions"]

    if any(condition["operator"] != "gte" for condition in conditions):
        problems.append(
            "Only inclusive minimum predicted churn probability is supported"
        )

    if len({condition["value"] for condition in conditions}) > 1:
        problems.append(
            "Different probability thresholds are not supported; "
            "one shared minimum is required"
        )

    for output in validated["requested_outputs"]:
        if output not in ALLOWED_OUTPUTS:
            problems.append(f"Requested output is unavailable: {output}")

    return list(dict.fromkeys(problems))


def check_comparison_scope(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> list[str]:
    """Extract requirements and return unsupported capabilities."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    payload = {
        "model": model,
        "system": REQUIREMENTS_PROMPT,
        "prompt": question,
        "format": REQUIREMENTS_SCHEMA,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 512,
        },
    }
    request = Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=180) as response:
        generated = json.load(response)

    if not generated.get("done") or generated.get("done_reason") != "stop":
        raise ValueError("Requirement extraction did not complete normally.")

    raw = generated.get("response")
    if os.getenv("SCOPE_DEBUG") == "1":
        print(f"RAW MODEL RESPONSE: {raw}", flush=True)
    if not isinstance(raw, str):
        raise ValueError(  # noqa: TRY004
            "Requirement extraction returned no JSON response."
        )

    requirements = parse_scope_requirements(raw)
    return unsupported_requirements(requirements)