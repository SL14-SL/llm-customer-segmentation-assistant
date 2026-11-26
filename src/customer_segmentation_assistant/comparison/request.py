"""Extract and validate the scope of a contract comparison."""

import json

from customer_segmentation_assistant.comparison.scope import (
    check_comparison_scope,
)
from customer_segmentation_assistant.config import DEFAULT_MODEL
from customer_segmentation_assistant.llm.client import generate_structured_response
from customer_segmentation_assistant.segments.extraction import parse_segment_criteria
from customer_segmentation_assistant.segments.tools import CONTRACT_TYPES

COMPARISON_SCHEMA = {
    "type": "object",
    "properties": {
        "contracts": {
            "type": "array",
            "items": {
                "enum": ["Month-to-month", "One year", "Two year"],
            },
            "maxItems": 3,
            "uniqueItems": True,
        },
        "minimum_churn_probability": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": ["contracts", "minimum_churn_probability"],
    "additionalProperties": False,
}

COMPARISON_SCHEMA = {
    "anyOf": [
        COMPARISON_SCHEMA,
        {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["unsupported"]},
                "message": {"type": "string", "minLength": 1},
            },
            "required": ["kind", "message"],
            "additionalProperties": False,
        },
    ],
}

COMPARISON_PROMPT = """
Interpret a request for a narrowly scoped customer comparison.

The ONLY supported inputs are:
- Contract types: Month-to-month, One year, Two year.
- ONE shared inclusive minimum predicted churn probability.

The ONLY supported results are:
- Matching customer count.
- Average monthly charges.
- Average predicted churn probability.

If ANY requested condition, action or result is outside these capabilities,
return an object with kind "unsupported" and a message naming
the specific unsupported requirement in the user's request.
Do not use a generic explanation or copy instructions as the message.

Never silently discard a requirement.
Unsupported requests include:
- Filters on tenure, monthly charges, age or other customer attributes.
- Different probability thresholds for different contracts.
- Maximum, exclusive or range probability conditions.
- Observed churn outcomes, historical analysis or individual customer lists.
- Updating data or contacting customers.

Otherwise return:
{"contracts":[...],"minimum_churn_probability":...}

Contract mappings:
- monthly or month-to-month: "Month-to-month"
- annual, yearly or one-year: "One year"
- two-year: "Two year"

Include only explicitly requested contract types.
Do not add contracts or repeat them.
Use [] when no contract types are supplied.

Extract an explicitly supplied inclusive minimum predicted churn probability.
"At least", "minimum" and "or higher" specify an inclusive minimum.
Convert percentages to probabilities.
0% is 0.0, not missing information.
Use null if no numerical minimum is supplied.
"High risk" alone does not specify a threshold.
Missing supported criteria require clarification, not rejection.

A follow-up answer supplying only a probability is valid.
Numbers describing tenure or other attributes are NOT probabilities.

Do not execute tools, calculate results or ask clarification questions.
Return only the JSON object.
"""


def parse_comparison_request(raw: str) -> dict[str, object]:
    """Validate extracted scope and request missing comparison criteria."""
    try:
        criteria = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Comparison criteria must be valid JSON.") from error

    if not isinstance(criteria, dict):
        raise ValueError(  # noqa: TRY004
            "Comparison criteria must be a JSON object."
        )
    if criteria.get("kind") == "unsupported":
        message = criteria.get("message")

        if (
            set(criteria) != {"kind", "message"}
            or not isinstance(message, str)
            or not message.strip()
        ):
            raise ValueError("Invalid unsupported decision.")

        return {
            "kind": "unsupported",
            "message": message.strip(),
        }
    if set(criteria) != {"contracts", "minimum_churn_probability"}:
        raise ValueError("Unexpected or missing comparison fields.")

    contracts = criteria["contracts"]

    if not isinstance(contracts, list):
        raise ValueError(  # noqa: TRY004
            "Contracts must be a list."
        )

    if any(
        not isinstance(contract, str) or contract not in CONTRACT_TYPES
        for contract in contracts
    ):
        raise ValueError("Unsupported comparison contract.")

    if len(set(contracts)) != len(contracts):
        raise ValueError("Comparison contracts must be distinct.")

    validated = parse_segment_criteria(
        json.dumps(
            {
                "contract": None,
                "minimum_churn_probability": criteria["minimum_churn_probability"],
            }
        )
    )
    threshold = validated["minimum_churn_probability"]

    if len(contracts) < 2 and threshold is None:
        question = (
            "Which at least two contract types and minimum churn "
            "probability should I use?"
        )
    elif len(contracts) < 2:
        question = "Which at least two contract types should I compare?"
    elif threshold is None:
        question = "Which minimum churn probability should I use?"
    else:
        return {
            "kind": "comparison",
            "arguments": {
                "contracts": list(contracts),
                "minimum_churn_probability": threshold,
            },
        }

    return {
        "kind": "clarification",
        "question": question,
    }


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "contracts": {
            "type": "array",
            "items": {
                "enum": ["Month-to-month", "One year", "Two year"],
            },
            "uniqueItems": True,
            "maxItems": 3,
        },
        "minimum_probabilities": {
            "type": "array",
            "items": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
        },
        "unsupported_requirements": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
    },
    "required": [
        "contracts",
        "minimum_probabilities",
        "unsupported_requirements",
    ],
    "additionalProperties": False,
}

EXTRACTION_PROMPT = """
Extract every requirement from the user's comparison request.
Return JSON only.

contracts:
List ALL explicitly selected contract types.
Return each selected contract as a separate array item.

Supported mappings:
- monthly, month-to-month = Month-to-month
- annual, yearly, one-year, one year = One year
- two-year, two year = Two year

When multiple contract types are connected by "and", commas,
or other enumeration phrases, extract every selected type.
Do not stop after recognizing the first contract.

Do not invent contract types.
Do not include excluded or negated contract types.
Do not repeat contract types.
Use [] if absent.

minimum_probabilities:
List ALL explicitly requested inclusive minimum predicted churn probabilities.
Convert percentages to numbers between 0 and 1.
Include different thresholds separately; never choose just one.
Use [] if absent. Do not invent defaults.
Numbers describing tenure, charges or other attributes are not probabilities.

unsupported_requirements:
List each requested requirement outside these supported capabilities:
- selecting the three supported contract types
- applying inclusive minimum predicted churn probability
- reporting customer counts, average monthly charges and
  average predicted churn probability

Examples of unsupported requirements:
tenure filters, monthly-charge filters, individual customer lists,
observed churn, historical analysis, write operations,
maximum/exclusive/range probability conditions, unknown contract types.

Missing contract types or a missing probability are NOT unsupported.
An answer supplying only a minimum probability is supported.
For clarification replies, extract requirements from the user's answer
and use the supplied context to understand it.
Never discard extra conditions in a clarification answer.
Do not copy these instructions into the output.
"""


def normalize_comparison_extraction(raw: str) -> dict[str, object]:
    """Validate extracted requirements before creating comparison criteria."""
    extracted = json.loads(raw)

    expected_fields = {
        "contracts",
        "minimum_probabilities",
        "unsupported_requirements",
    }

    if not isinstance(extracted, dict) or set(extracted) != expected_fields:
        raise ValueError("Invalid comparison extraction.")

    probabilities = extracted["minimum_probabilities"]
    requirements = extracted["unsupported_requirements"]

    if not isinstance(probabilities, list) or not isinstance(requirements, list):
        raise TypeError("Extracted requirements must be lists.")

    if any(not isinstance(item, str) or not item.strip() for item in requirements):
        raise ValueError("Invalid unsupported requirement.")

    parse_comparison_request(
        json.dumps(
            {
                "contracts": extracted["contracts"],
                "minimum_churn_probability": None,
            }
        )
    )

    normalized_probabilities = []

    for probability in probabilities:
        validated = parse_segment_criteria(
            json.dumps(
                {
                    "contract": None,
                    "minimum_churn_probability": probability,
                }
            )
        )

        threshold = validated["minimum_churn_probability"]

        if threshold is None:
            raise ValueError("Extracted probabilities cannot be null.")

        normalized_probabilities.append(threshold)

    problems = [item.strip() for item in requirements]

    if len(set(normalized_probabilities)) > 1:
        problems.append(
            "Different probability thresholds are not supported; "
            "this comparison requires one shared minimum."
        )

    if problems:
        return {
            "kind": "unsupported",
            "message": "Unsupported requirements: " + "; ".join(problems),
        }

    return {
        "contracts": extracted["contracts"],
        "minimum_churn_probability": (
            normalized_probabilities[0] if normalized_probabilities else None
        ),
    }


def extract_comparison_criteria(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract comparison criteria without executing database queries."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    scope_decision = check_comparison_scope(question)

    if scope_decision is not None:
        return scope_decision

    raw = generate_structured_response(
        system=EXTRACTION_PROMPT,
        prompt=question,
        schema=EXTRACTION_SCHEMA,
        model=model,
        num_predict=256,
    )

    criteria = normalize_comparison_extraction(raw)
    parse_comparison_request(json.dumps(criteria))

    return criteria


def generate_comparison_request(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract comparison criteria and determine the next action."""
    criteria = extract_comparison_criteria(question, model=model)
    return parse_comparison_request(json.dumps(criteria))


def extract_comparison_follow_up(
    question: str,
    *,
    current_criteria: dict[str, object],
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Interpret clarification answers with the known comparison context."""
    scope_decision = check_comparison_scope(question)

    if scope_decision is not None:
        return scope_decision
    contracts = current_criteria["contracts"]
    threshold = current_criteria["minimum_churn_probability"]

    awaiting_threshold = len(contracts) >= 2 and threshold is None

    if awaiting_threshold:
        request = (
            "This is an answer to a clarification question.\n"
            f"Already selected contracts: {json.dumps(contracts)}\n"
            "Assistant asked: Which minimum predicted churn probability "
            "should I use?\n"
            f"User answered: {question}\n\n"
            "Extract the user's inclusive minimum probability. "
            "A reply supplying only this probability is supported. "
            "Preserve any additional requirements for scope checking. "
            "Do not reject the reply because it does not repeat "
            "the selected contracts."
        )
    else:
        request = question

    extracted = extract_comparison_criteria(request, model=model)

    if extracted.get("kind") == "unsupported":
        return extracted

    if awaiting_threshold:
        return {
            "contracts": [],
            "minimum_churn_probability": (extracted["minimum_churn_probability"]),
        }

    return extracted
