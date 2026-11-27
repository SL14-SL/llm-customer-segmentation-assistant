"""Verify agent planner integration with the shared Ollama client."""

import json
from unittest.mock import Mock

import pytest

from customer_segmentation_assistant.comparison import agent


@pytest.mark.parametrize(
    ("remaining_contracts", "response"),
    [
        (
            ["One year"],
            {"kind": "tool_call", "contract": "One year"},
        ),
        (
            [],
            {"kind": "finish"},
        ),
    ],
)
def test_uses_state_dependent_action_schema(
    monkeypatch,
    remaining_contracts,
    response,
):
    generate = Mock(return_value=json.dumps(response))

    monkeypatch.setattr(
        agent,
        "generate_structured_response",
        generate,
    )

    context = {
        "contracts": ["Month-to-month", "One year"],
        "remaining_contracts": remaining_contracts,
        "minimum_churn_probability": 0.7,
        "observations": [],
    }

    action = agent.propose_next_action(
        context,
        model="test-model",
    )

    assert action == response

    generate.assert_called_once_with(
        system=agent.AGENT_PROMPT,
        prompt=json.dumps(context, allow_nan=False),
        schema=agent.next_action_schema(remaining_contracts),
        model="test-model",
        num_predict=512,
    )


def test_rejects_non_object_action(monkeypatch):
    generate = Mock(return_value="[]")

    monkeypatch.setattr(
        agent,
        "generate_structured_response",
        generate,
    )

    context = {
        "remaining_contracts": ["One year"],
    }

    with pytest.raises(ValueError, match="Agent action must be a JSON object"):
        agent.propose_next_action(context)
