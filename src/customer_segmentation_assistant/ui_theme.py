"""Shared styling for the Streamlit interfaces."""

import streamlit as st


def apply_ui_theme() -> None:
    """Apply shared typography and chat styling."""
    st.markdown(
        """
        <style>
        /* Caption text */
        [data-testid="stCaptionContainer"] {
            font-size: 1rem;
            line-height: 1.6;
        }

        [data-testid="stCaptionContainer"] p {
            font-size: 1rem;
            line-height: 1.6;
        }

        /* Body text and Markdown */
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stText"] {
            font-size: 1.05rem;
            line-height: 1.65;
        }

        /* Widget labels */
        label,
        .stSelectbox label,
        .stTextInput label,
        .stTextArea label {
            font-size: 1rem !important;
        }

        /* Expander headers */
        .streamlit-expanderHeader {
            font-size: 1rem;
        }

        /* Sidebar text and captions */
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            font-size: 1rem;
            line-height: 1.6;
        }

        /* User avatar */
        [data-testid="stChatMessageAvatarUser"] {
            background-color: #008569 !important;
            color: #FFFFFF !important;
        }

        /* Assistant avatar */
        [data-testid="stChatMessageAvatarAssistant"] {
            background-color: #65B8A0 !important;
            color: #112F26 !important;
        }

        /* Chat input text */
        [data-testid="stChatInput"] textarea {
            font-size: 1.05rem !important;
            line-height: 1.6 !important;
        }

        /* Chat input placeholder */
        [data-testid="stChatInput"] textarea::placeholder {
            font-size: 1.05rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
