# README.md

# 🧠 Multi-turn Memory Chatbot

> A private, offline conversational AI assistant with session-aware memory and dynamic profile extraction powered by local LLMs.

---

## Overview

Most standard chatbot implementations are stateless — they forget earlier context as conversation length increases. This system provides **multi-turn conversational memory** by tracking the conversation history and maintaining an evolving user profile (name and preferences) within the session, running completely offline with local LLMs via Ollama. No cloud APIs, credentials, or third-party tracking are required.

---

## Features

| Feature | Detail |
|---------|--------|
| **Full chat history display** | All messages shown with `st.chat_message` |
| **Streamed responses** | Tokens rendered live via `ollama.chat(stream=True)` and `st.write_stream` |
| **Short-term memory** | Entire conversation resent to the LLM each turn, capped at last 12 messages |
| **Profile memory** | Name and preferences extracted via regex + LLM JSON call |
| **Profile injection** | Injected into the system prompt every turn |
| **Sidebar "What I remember"** | Live view of name, preferences, message count |
| **Model selector** | Dropdown populated from `ollama.list()` |
| **Clear / New chat** | Resets messages and profile |
| **Friendly error handling** | Ollama down, model not pulled, other errors — no raw tracebacks |
| **Fully offline** | No internet required after `ollama pull` |

---

## Tech Stack

- **Python 3.10+**
- **Streamlit** — UI
- **Ollama** (local) — LLM server
- **ollama** Python package — official client
- **pytest** — testing (mocked, no Ollama needed)

---

## Prerequisites

1. **Install Ollama**
   ```bash
   # Windows: download from https://ollama.com/download
   ollama serve          # keep this running in a terminal
   ```

2. **Pull a model**
   ```bash
   # Default fast model (runs on almost any laptop):
   ollama pull qwen2.5:1.5b-instruct

   # Or standard mini-project model:
   ollama pull qwen2.5:7b

   # Or medium alternative:
   ollama pull qwen2.5:3b
   ```

---

## Setup & Git Version Control

```bash
# 1. Clone or navigate to the project folder
cd llm-ps20

# 2. Check Git repository status
git status

# 3. Create a virtual environment
python -m venv venv

# 4. Activate it
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt
```

---

## Run the App

```bash
# Activate venv (if not already active)
.\venv\Scripts\Activate.ps1

# Start the Streamlit application
streamlit run app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## Run Tests

```bash
pytest test_memory.py -v
```

Ollama does **not** need to be running for unit tests — LLM calls are mocked. All 46 tests run in under 1 second.

---

## How Memory Works (Viva Explanation)

1. **The model is stateless.** Ollama has no built-in session memory across turns.
2. **The app resends history.** On every turn, `app.py` sends `[system prompt] + last 12 messages` to Ollama.
3. **Two-Layer Profile Extraction:**
   - **Layer A (Regex):** Fast pass for direct, simple patterns (`"my name is X"`, `"I'm vegetarian"`). Validates that candidates are clean nouns $\le 4$ words, rejecting pronouns (`"it"`) and commands (`"suggest..."`).
   - **Layer B (LLM JSON Extraction):** Understands natural expressions of interest (`"fan of X"`, `"interest in X"`, `"into X"`) and extracts clean topics (`["movies", "anime"]`), while ignoring questions (`"what is recursion"` $\rightarrow$ `[]`).
4. **Profile Injection:** The extracted name and preferences are merged and appended to the system prompt every turn: `"Known about the user: name = Dhiraj; preferences = [cricket, vegetarian, movies]"`.
5. **Session Reset:** Clicking *"Clear memory / New chat"* clears `st.session_state.messages` and `st.session_state.profile`, wiping all short-term context.

---

## Project Structure

```
llm-ps20/
├── app.py              # Streamlit UI — chat loop, session state, error handling
├── llm.py              # Ollama calls: stream_chat(), extract_profile(), list_models()
├── memory.py           # Pure-Python helpers: regex extract, merge, trim, profile_to_string
├── config.py           # MODEL_NAME, MAX_HISTORY, system prompt constants
├── test_memory.py      # pytest tests (Ollama mocked)
├── PROMPT_NOTES.md     # Prompt V1 vs V2 comparison with observed outputs
├── TEST_LOG.md         # Manual test run log
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Screenshots

> _Add screenshots here after running the app._

| Chat with memory | Sidebar profile panel |
|------------------|-----------------------|
| _(screenshot)_   | _(screenshot)_        |
