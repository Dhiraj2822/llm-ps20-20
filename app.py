# app.py
# Streamlit UI for Multi-turn Memory Chatbot
# Run with:  streamlit run app.py

import streamlit as st

import config
import memory
import llm


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Multi-turn Memory Chatbot",
    page_icon="🧠",
    layout="centered",
)

st.title("🧠 Multi-turn Memory Chatbot")
st.caption("Local LLM (Qwen2.5 via Ollama) with session memory")


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_session() -> None:
    """Create session-state keys on the very first run."""
    if "messages" not in st.session_state:
        st.session_state.messages: list[memory.Message] = []
    if "profile" not in st.session_state:
        st.session_state.profile: memory.Profile = memory.empty_profile()
    if "model" not in st.session_state:
        st.session_state.model: str = config.MODEL_NAME


_init_session()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Settings")

    # --- Model selector ---
    available_models = llm.list_models()
    # Make sure the currently selected model appears in the list
    if st.session_state.model not in available_models:
        available_models.insert(0, st.session_state.model)

    selected_model = st.selectbox(
        "Model",
        options=available_models,
        index=available_models.index(st.session_state.model),
        help="Models returned by ollama.list(). Switch to qwen2.5:3b on a slow machine.",
    )
    st.session_state.model = selected_model

    st.divider()

    # --- What I remember panel ---
    st.subheader("🗂️ What I remember")
    profile = st.session_state.profile
    name_display = profile.get("name") or "_not known yet_"
    st.markdown(f"**Name:** {name_display}")

    prefs = profile.get("preferences", [])
    if prefs:
        st.markdown("**Preferences:**")
        for p in prefs:
            st.markdown(f"- {p}")
    else:
        st.markdown("**Preferences:** _none noted yet_")

    st.divider()

    # --- Stats ---
    st.markdown(f"**Messages:** {len(st.session_state.messages)}")
    st.markdown(f"**History sent to LLM:** last {config.MAX_HISTORY} messages")

    st.divider()

    # --- Clear button ---
    if st.button("🗑️ Clear memory / New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.profile = memory.empty_profile()
        st.rerun()

    st.divider()

    # --- How memory works expander ---
    with st.expander("ℹ️ How memory works"):
        st.markdown(
            "1. **The model is stateless.** Every turn, the app re-sends the full "
            "conversation history to Ollama.\n"
            "2. **History is capped** at the last "
            f"{config.MAX_HISTORY} messages to stay inside the context window.\n"
            "3. **Your profile** (name & preferences) is extracted from your words "
            "and injected into the system prompt every turn, so the model always "
            "knows who it's talking to."
        )


# ---------------------------------------------------------------------------
# Display existing conversation
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

user_input: str | None = st.chat_input("Type a message…")

if user_input:
    # 1. Show the user's message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Store it
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 3. Update profile – regex pass (fast, no LLM)
    regex_result = memory.regex_extract(user_input)
    st.session_state.profile = memory.merge_profiles(st.session_state.profile, regex_result)

    # 4. Update profile – LLM extraction pass (slow, but more accurate)
    #    Runs in background before the main response so the profile is ready.
    st.session_state.profile = llm.extract_profile(
        user_input,
        st.session_state.profile,
        model=st.session_state.model,
    )

    # 5. Trim history before sending to LLM
    trimmed = memory.trim_history(st.session_state.messages, config.MAX_HISTORY)

    # 6. Stream the assistant reply
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking…"):
                # st.write_stream expects an iterable of strings
                response_text = st.write_stream(
                    llm.stream_chat(
                        messages=trimmed,
                        profile=st.session_state.profile,
                        model=st.session_state.model,
                    )
                )

            # 7. Store the full reply
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )

        except ConnectionError as exc:
            st.error(f"🔌 {exc}")
        except ValueError as exc:
            st.error(f"📦 {exc}")
        except RuntimeError as exc:
            st.error(f"⚠️ Something went wrong: {exc}. The app is still usable.")
        except Exception as exc:
            st.error(
                "⚠️ An unexpected error occurred. Please try again. "
                f"Details: {exc}"
            )

    # 8. Rerun to refresh the sidebar stats (message count, profile)
    st.rerun()
