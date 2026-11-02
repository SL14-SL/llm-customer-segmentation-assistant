"""Interactive demo of the bounded segment-comparison workflow."""

import json
from pathlib import Path

import streamlit as st

from customer_segmentation_assistant.agent import (
    propose_next_action,
    run_comparison,
)
from customer_segmentation_assistant.comparison_conversation import (
    ComparisonConversation,
)
from customer_segmentation_assistant.comparison_request import (
    extract_comparison_follow_up,
)
from customer_segmentation_assistant.demo_data import create_demo_database

DATABASE = Path("data/agent_demo.duckdb")


def reset_conversation() -> None:
    """Start a separate comparison without retaining previous criteria."""
    st.session_state["comparison"] = ComparisonConversation()
    st.session_state["messages"] = []
    st.session_state["decision"] = None
    st.session_state["result"] = None
    st.session_state["actions"] = []


def main() -> None:
    """Render clarification, confirmed scope and visible execution steps."""
    st.set_page_config(
        page_title="Segment Comparison Demo",
        page_icon="🔎",
        layout="wide",
    )

    if "comparison" not in st.session_state:
        reset_conversation()

    st.title("Customer Segment Comparison")
    st.caption(
        "Synthetic customer data · Local Ollama model · "
        "Read-only tools · Computed report"
    )
    st.info(
        "Compare two or three contract types using one shared minimum "
        "predicted churn probability. Supported contracts: Month-to-month, "
        "One year and Two year. Additional filters are not supported."
    )

    if st.sidebar.button("New comparison"):
        reset_conversation()
        st.rerun()

    st.sidebar.markdown(
        "**Example**\n\n"
        "Compare monthly and annual contracts with a minimum "
        "churn probability of 70%."
    )
    st.sidebar.caption(
        "When answering a question about the missing threshold, "
        "supply only the threshold. Start a new comparison to change "
        "the contract selection."
    )

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    message = st.chat_input("Describe a contract comparison in English")

    if message:
        st.session_state["result"] = None
        st.session_state["actions"] = []
        st.session_state["decision"] = None

        st.session_state["messages"].append({
            "role": "user",
            "content": message,
        })

        conversation = st.session_state["comparison"]

        try:
            with st.spinner("Extracting comparison criteria…"):
                extracted = extract_comparison_follow_up(
                    message,
                    current_criteria=conversation.criteria,
                )
                decision = conversation.update(extracted)

            st.session_state["decision"] = decision

            if decision["kind"] == "clarification":
                reply = decision["question"]
            else:
                reply = (
                    "The comparison criteria are complete. "
                    "Check the filters below before running it."
                )

        except Exception as error:  # noqa: BLE001 - display request errors in UI
            reply = (
                f"Could not interpret this request: {type(error).__name__}. "
                "Try rephrasing it or start a new comparison."
            )

        st.session_state["messages"].append({
            "role": "assistant",
            "content": reply,
        })
        st.rerun()

    decision = st.session_state["decision"]

    if decision is not None and decision["kind"] == "comparison":
        arguments = decision["arguments"]

        st.subheader("Recognized filters")
        st.write("**Contracts:** " + ", ".join(arguments["contracts"]))
        st.write(
            "**Minimum predicted churn probability:** "
            f"{arguments['minimum_churn_probability']:.1%}"
        )
        st.caption(
            "Check these filters against your request. "
            "The model can misinterpret natural language."
        )

        if st.button("Run this comparison", type="primary"):
            actions = []
            st.session_state["result"] = None
            st.session_state["actions"] = []

            def visible_planner(context):
                action = propose_next_action(context)
                actions.append({
                    "completed_tool_calls": len(context["observations"]),
                    "action": action,
                })
                return action

            try:
                with st.spinner("Running bounded comparison…"):
                    if not DATABASE.exists():
                        create_demo_database(DATABASE)

                    result = run_comparison(
                        contracts=tuple(arguments["contracts"]),
                        minimum_churn_probability=(
                            arguments["minimum_churn_probability"]
                        ),
                        database=DATABASE,
                        max_tool_calls=4,
                        planner=visible_planner,
                    )

                st.session_state["result"] = result

            except Exception as error:  # noqa: BLE001 - display execution errors in UI
                st.error(
                    "Comparison stopped: "
                    f"{type(error).__name__}: {error}"
                )
            finally:
                st.session_state["actions"] = actions

    if st.session_state["actions"]:
        with st.expander("Model actions", expanded=True):
            for index, action in enumerate(
                st.session_state["actions"],
                start=1,
            ):
                st.write(f"**Step {index}**")
                st.json(action)

    result = st.session_state["result"]

    if result is not None:
        st.subheader("Computed report")
        st.text(result["answer"])
        st.caption(
            f"Completed tool calls: {result['tool_calls']}. "
            "The report is rendered from computed values by Python."
        )

        with st.expander("Tool calls and aggregate results"):
            st.json(result["observations"])

        st.download_button(
            "Download computed results",
            data=json.dumps(result, indent=2),
            file_name="segment-comparison.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()