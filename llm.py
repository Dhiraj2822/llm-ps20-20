# llm.py
# All Ollama interactions live here.
# Two public functions: stream_chat() and extract_profile().

import ollama
from typing import Generator

import config
import memory


# ---------------------------------------------------------------------------
# Helper: build the system prompt with the user profile injected
# ---------------------------------------------------------------------------

def _build_system_message(profile: memory.Profile) -> dict:
    """
    Combine the base system prompt with the 'Known about the user' block.
    Returns a dict ready to prepend to the message list.
    """
    full_prompt = config.SYSTEM_PROMPT + "\n\n" + memory.profile_to_string(profile)
    return {"role": "system", "content": full_prompt}


# ---------------------------------------------------------------------------
# Main chat function – streams tokens back to the caller
# ---------------------------------------------------------------------------

def stream_chat(
    messages: list[memory.Message],
    profile: memory.Profile,
    model: str = config.MODEL_NAME,
) -> Generator[str, None, None]:
    """
    Send the conversation history to Ollama and yield response tokens one by one.

    Parameters
    ----------
    messages : list of dicts with 'role' and 'content'
        The trimmed history (already capped at MAX_HISTORY by the caller).
    profile : dict
        Current user profile – injected into the system prompt.
    model : str
        Ollama model tag to use.

    Yields
    ------
    str
        Each text chunk as the model streams it.

    Raises
    ------
    ConnectionError
        When Ollama is not running.
    ValueError
        When the requested model has not been pulled.
    RuntimeError
        For any other Ollama / network error.
    """
    system_msg = _build_system_message(profile)
    payload = [system_msg] + messages   # system prompt goes first

    try:
        stream = ollama.chat(
            model=model,
            messages=payload,
            stream=True,
        )
        for chunk in stream:
            # Each chunk is a ChatResponse; .message.content is the token text
            token = chunk.message.content
            if token:
                yield token

    except ollama.ResponseError as exc:
        # Ollama is running but the model isn't pulled (HTTP 404)
        err_msg = str(exc).lower()
        if "not found" in err_msg or "pull" in err_msg or "404" in err_msg:
            raise ValueError(
                f"Model '{model}' is not pulled. Run: ollama pull {model}"
            ) from exc
        raise RuntimeError(f"Ollama error: {exc}") from exc

    except ollama.RequestError as exc:
        # Ollama is not running / connection refused
        raise ConnectionError(
            "Ollama isn't running. Start it with 'ollama serve' and try again."
        ) from exc

    except Exception as exc:
        # Catch-all for anything else
        err_msg = str(exc).lower()
        if "connection" in err_msg or "refused" in err_msg or "connect" in err_msg:
            raise ConnectionError(
                "Ollama isn't running. Start it with 'ollama serve' and try again."
            ) from exc
        raise RuntimeError(f"Unexpected error: {exc}") from exc


# ---------------------------------------------------------------------------
# Profile extraction via LLM (layer b)
# ---------------------------------------------------------------------------

def extract_profile(
    user_message: str,
    existing_profile: memory.Profile,
    model: str = config.MODEL_NAME,
) -> memory.Profile:
    """
    Ask the LLM to extract name / preferences from *user_message* as strict JSON.

    Uses temperature=0 and format="json" for deterministic output.
    On any failure returns *existing_profile* unchanged.

    Parameters
    ----------
    user_message : str
        The latest message from the user.
    existing_profile : dict
        Profile to merge results into (and to fall back to on failure).
    model : str
        Ollama model tag.

    Returns
    -------
    dict
        Updated profile (or the original if extraction failed).
    """
    # Skip the LLM extraction call entirely if the message is not a
    # personal statement (e.g. questions, general requests).
    # This prevents topics like "recursion" being mistaken for preferences.
    if not memory.is_personal_statement(user_message):
        return existing_profile

    extraction_prompt = (
        'Return only JSON: {"name": string|null, "preferences": [strings]}.\n'
        "Task: Extract the user's name (if stated) and their personal preferences/interests.\n"
        "Rules:\n"
        '1. Understand natural expressions of liking: "fan of X", "interest in X", "into X", "love X", "like X", "enjoy X", "prefer X".\n'
        '2. Preferences MUST be concise topics or nouns (e.g. "movies", "anime", "cricket", "vegetarian", "mystery thrillers").\n'
        '3. NEVER extract pronouns ("it", "them"), entire sentences, reasoning ("because..."), or action requests ("suggest...", "give me...").\n'
        '4. If the message is a general question or knowledge query (e.g. "what is recursion", "explain recursion"), return {"name": null, "preferences": []}.\n'
        '5. If no facts about the user are mentioned, return {"name": null, "preferences": []}.\n\n'
        "Input: " + user_message
    )

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": extraction_prompt}],
            format="json",
            options={"temperature": 0},
        )
        json_text = response.message.content
        return memory.parse_llm_profile(json_text, existing_profile)

    except Exception:
        # Any failure (Ollama down, bad JSON, etc.) → keep existing profile
        return existing_profile


# ---------------------------------------------------------------------------
# List available models (for the sidebar selector)
# ---------------------------------------------------------------------------

def list_models() -> list[str]:
    """
    Return model names from ollama.list().
    Falls back to [config.MODEL_NAME] if Ollama is not reachable.
    """
    try:
        result = ollama.list()
        # result.models is a list of Model objects with a .model attribute
        names = [m.model for m in result.models]
        return names if names else [config.MODEL_NAME]
    except Exception:
        return [config.MODEL_NAME]
