# config.py
# Central configuration for the Multi-turn Memory Chatbot
# Edit MODEL_NAME or MAX_HISTORY here; everything else picks it up automatically.

MODEL_NAME: str = "qwen2.5:1.5b-instruct"   # default model; overridable from the sidebar

MAX_HISTORY: int = 12             # max messages sent to the LLM (older ones are trimmed)

# ---------------------------------------------------------------------------
# System prompt – V2 (final)
# Changes over V1 are documented in PROMPT_NOTES.md
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_V2: str = (
    "You are a friendly assistant with session memory. "
    "Use the conversation history and the 'Known about the user' block to remember "
    "what the user told you. "
    "Address the user by name occasionally, not in every message. "
    "Respect their preferences when giving suggestions. "
    "If asked about something the user has not told you, say you don't know yet. "
    "Never invent personal details. "
    "Keep answers concise."
)

# ---------------------------------------------------------------------------
# System prompt – V1 (kept for the PROMPT_NOTES comparison)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_V1: str = (
    "You are a helpful assistant. Remember the user's details."
)

# Which prompt is active right now
SYSTEM_PROMPT: str = SYSTEM_PROMPT_V2
