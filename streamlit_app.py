"""Local chat interface for customer segmentation."""

from datetime import UTC, datetime
from time import perf_counter
from urllib.error import URLError

import duckdb
import streamlit as st

from customer_segmentation_assistant.database import (
    DEFAULT_DATABASE,
    query_dataframe,
)
from customer_segmentation_assistant.decisions import (
    ClarificationDecision,
    UnsupportedDecision,
)
from customer_segmentation_assistant.llm import DEFAULT_MODEL, generate_decision

MAX_CLARIFICATIONS = 3

st.set_page_config(
    page_title="Customer Segmentation Assistant",
    page_icon="💬",
    layout="wide",
)

st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending_context", [])
st.session_state.setdefault("clarification_count", 0)


def reset_chat() -> None:
    """Clear displayed messages and the current clarification workflow."""
    st.session_state.messages = []
    st.session_state.pending_context = []
    st.session_state.clarification_count = 0


def render_message(message: dict, index: int) -> None:
    """Display one stored message and its optional query result."""
    with st.chat_message(message["role"]):
        st.write(message["content"])

        if "sql" in message:
            with st.expander("View generated SQL"):
                st.code(message["sql"], language="sql")

        if "result" in message:
            result = message["result"]

            if result.empty:
                st.info("No matching customers.")
            else:
                st.dataframe(
                    result,
                    hide_index=True,
                    width="stretch",
                )

                st.download_button(
                    label="Download this result as CSV",
                    data=message["csv"],
                    file_name=message["filename"],
                    mime="text/csv",
                    key=f"download_{index}",
                    on_click="ignore",
                )
        if "error" in message:
            with st.expander("Error details"):
                st.code(message["error"], language=None)

        if "duration" in message:
            st.caption(f"Completed in {message['duration']:.1f} seconds")


def process_question(question: str) -> dict:
    """Resolve a question using pending clarification context."""
    started = perf_counter()
    context = list(st.session_state.pending_context)

    if context:
        context.append(f"Customer answer: {question}")
    else:
        context.append(f"Original customer question: {question}")

    current_request = "\n\n".join(context)
    current_request += (
        "\n\nResolve the current request using all customer answers above. "
        "Generate SQL if the missing information has been supplied."
    )

    decision = generate_decision(current_request)
    
    if isinstance(decision, UnsupportedDecision):
        st.session_state.pending_context = []
        st.session_state.clarification_count = 0

        return {
            "role": "assistant",
            "content": decision.message,
            "duration": perf_counter() - started,
        }

    if isinstance(decision, ClarificationDecision):
        if st.session_state.clarification_count >= MAX_CLARIFICATIONS:
            st.session_state.pending_context = []
            st.session_state.clarification_count = 0

            return {
                "role": "assistant",
                "content": (
                    "I could not resolve the request within three clarification "
                    "answers. Please start a new, more specific question."
                ),
                "duration": perf_counter() - started,
            }

        context.append(f"Assistant clarification: {decision.question}")
        st.session_state.pending_context = context
        st.session_state.clarification_count += 1

        return {
            "role": "assistant",
            "content": decision.question,
            "duration": perf_counter() - started,
        }

    result = query_dataframe(decision.sql)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")

    message = {
        "role": "assistant",
        "content": (
            f"Your query returned {len(result):,} "
            f"{'row' if len(result) == 1 else 'rows'}."
        ),
        "sql": decision.sql,
        "result": result,
        "csv": result.to_csv(index=False).encode("utf-8"),
        "filename": f"segment_{timestamp}.csv",
        "duration": perf_counter() - started,
    }

    st.session_state.pending_context = []
    st.session_state.clarification_count = 0

    return message


with st.sidebar:
    st.title("Customer Segmentation")
    st.caption("Explore customer data in plain English.")

    st.divider()

    st.markdown("**Local model**")
    st.code(DEFAULT_MODEL, language=None)

    st.markdown("**Data access**")
    st.write("Read-only customer queries")

    st.button(
        "New conversation",
        on_click=reset_chat,
        width="stretch",
    )

    st.divider()

    st.markdown("**Example questions**")
    st.write("How many customers are in the dataset?")
    st.write("Show the 5 customers with the highest churn probability.")
    st.write("What is the average churn probability for each contract type?")
    st.write("Show me high-risk customers.")

    st.divider()

    st.caption(
        "Clarification answers apply to the current request. "
        "After a result, the next question starts a new request."
    )


st.title("Customer Segmentation Assistant")
st.caption(
    "Ask a question, clarify your criteria, and explore the results. "
    "Powered by a local language model."
)

if not DEFAULT_DATABASE.is_file():
    st.error(
        f"Customer database not found: {DEFAULT_DATABASE}. "
        "Start the app from the project root and create the database first."
    )
    st.stop()

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.write(
            "What would you like to know about your customers? "
            "You can filter customer segments, compare groups, "
            "or find customers with the highest predicted churn risk."
        )

for index, message in enumerate(st.session_state.messages):
    render_message(message, index)

placeholder = (
    "Answer the clarification question..."
    if st.session_state.pending_context
    else "Ask a question about your customers..."
)

question = st.chat_input(placeholder, max_chars=4000)

if question and question.strip():
    question = question.strip()

    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    try:
        with st.spinner("Preparing your answer with the local model..."):
            answer = process_question(question)

    except (
        URLError,
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
        duckdb.Error,
    ) as error:
        answer = {
            "role": "assistant",
            "content": (
                "The request could not be completed. "
                "Check that Ollama is running, or rephrase your question."
            ),
            "error": str(error),
        }

    st.session_state.messages.append(answer)
    st.rerun()