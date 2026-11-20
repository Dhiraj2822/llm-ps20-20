# memory.py
# Pure-Python session memory helpers – NO Streamlit imports here.
# This module is imported by both app.py and test_memory.py.

import re
import json
from typing import Optional

# ---------------------------------------------------------------------------
# Type aliases (keeps signatures readable for the viva)
# ---------------------------------------------------------------------------
Profile = dict  # {"name": str | None, "preferences": list[str]}
Message = dict  # {"role": str, "content": str}


def empty_profile() -> Profile:
    """Return a fresh, empty user profile."""
    return {"name": None, "preferences": []}


# ---------------------------------------------------------------------------
# Regex-based extraction (layer a)
# ---------------------------------------------------------------------------

# Patterns for name detection (case-insensitive)
_NAME_PATTERNS = [
    r"(?:my name is|i am|i'm|call me|you can call me)\s+([A-Za-z]+)",
    r"(?:actually call me|please call me)\s+([A-Za-z]+)",
]

# Patterns for preferences (things the user likes, hates, needs, etc.)
# Light regex pass for obvious, direct patterns.
# Clauses like "so...", "because...", "suggest..." terminate the match.
_PREF_PATTERNS = [
    r"(?:i (?:like|love|enjoy|prefer|adore))\s+([^.,;!?\n]+?)(?:\s+(?:so|because|since|but|and|if|then|to)\b|[.,;!?\n]|$)",
    r"(?:i (?:hate|dislike|don't like|do not like|avoid))\s+([^.,;!?\n]+?)(?:\s+(?:so|because|since|but|and|if|then|to)\b|[.,;!?\n]|$)",
    r"(?:i'?m (?:vegetarian|vegan|pescatarian|diabetic|lactose intolerant))",
    r"(?:i am (?:vegetarian|vegan|pescatarian|diabetic|lactose intolerant))",
    r"(?:i'?m allergic to)\s+([^.,;!?\n]+?)(?:\s+(?:so|because|since|but|and|if|then|to)\b|[.,;!?\n]|$)",
    r"(?:i (?:follow|eat only))\s+([^.,;!?\n]+?)(?:\s*diet)?(?:\s+(?:so|because|since|but|and|if|then|to)\b|[.,;!?\n]|$)",
]

# Reject invalid candidate preferences extracted by regex
_INVALID_PREF_WORDS = {
    "it", "them", "that", "this", "something", "anything", "nothing",
    "him", "her", "me", "us", "you", "doing", "having",
}
_INVALID_SUBSTRINGS = (
    "suggest", "recommend", "because", "so ", "but ", "since ", "please",
    "tell me", "give me", "show me", "want to",
)


def _is_valid_preference(pref: str) -> bool:
    """Validate that a regex-extracted preference is a real topic, not sentence junk."""
    pref_lower = pref.lower().strip()
    if not pref_lower:
        return False
    # Filter pronouns and single nonsense words
    if pref_lower in _INVALID_PREF_WORDS:
        return False
    # Must not contain conversational verbs or clausal connectors
    if any(sub in pref_lower for sub in _INVALID_SUBSTRINGS):
        return False
    # Real preferences are concise (at most 4 words, e.g. "classic rock music")
    if len(pref_lower.split()) > 4:
        return False
    return True


def is_personal_statement(text: str) -> bool:
    """
    Return True if *text* is worth running LLM profile extraction on.

    Logic: skip ONLY if there is zero first-person language in the message.
    Pure questions ("what is recursion") have no 'I'/'my' and are skipped.
    Natural phrases like "I'm a fan of movies" or "I have interest in cricket"
    DO contain first-person language and are passed to the LLM.
    The LLM extraction prompt handles the rest of the nuance.
    """
    lower = text.strip().lower()

    # Pure questions (end with ?) — never contain new personal facts
    if lower.endswith("?"):
        return False

    # If there's no first-person pronoun at all, it cannot be a personal statement
    first_person_markers = (
        " i ", "i'm", "i've", "i'd", "i am", "i have", "i had",
        "i like", "i love", "i hate", "i enjoy", "i prefer",
        "my ", "call me",
    )
    # Prepend a space so "i " matches at the start too
    padded = " " + lower
    return any(marker in padded for marker in first_person_markers)


def _clean_preference(raw: str) -> str:
    """Strip trailing punctuation and extra whitespace from a matched preference."""
    return raw.strip().rstrip(".,;!?").strip()


def regex_extract(text: str) -> Profile:
    """
    Quick regex pass over *text* to find the user's name and preferences.

    Returns a partial Profile with whatever it found; unrecognised fields are None / [].
    """
    result: Profile = {"name": None, "preferences": []}
    lower = text.lower()

    # --- name ---
    for pattern in _NAME_PATTERNS:
        m = re.search(pattern, lower)
        if m:
            # Capitalise properly (regex matched lowercase)
            raw_name = m.group(1).strip()
            # Find the same span in the original text to preserve casing
            orig_m = re.search(pattern, text, re.IGNORECASE)
            if orig_m:
                result["name"] = orig_m.group(1).strip().capitalize()
            else:
                result["name"] = raw_name.capitalize()
            break  # first match wins

    # --- preferences ---
    for pattern in _PREF_PATTERNS:
        for m in re.finditer(pattern, lower, re.IGNORECASE):
            if m.lastindex:                     # has a capture group (e.g. "I like X")
                pref = _clean_preference(m.group(1))
            else:                               # whole match is the fact (e.g. "I'm vegetarian")
                # strip the leading "i'm " / "i am " boilerplate
                pref = re.sub(r"^(i'?m |i am )", "", m.group(0), flags=re.IGNORECASE).strip()
            if pref and _is_valid_preference(pref):
                result["preferences"].append(pref)

    return result


# ---------------------------------------------------------------------------
# Profile merging
# ---------------------------------------------------------------------------

def merge_profiles(existing: Profile, new: Profile) -> Profile:
    """
    Merge *new* into *existing* following the assignment rules:

    - Never overwrite a known name with None.
    - A newer *explicit* name replaces the old one (handles "actually call me Sam").
    - Preferences are de-duplicated case-insensitively.
    """
    merged: Profile = {
        "name": existing.get("name"),
        "preferences": list(existing.get("preferences", [])),
    }

    # Name: only update if the new profile actually has one
    if new.get("name"):
        merged["name"] = new["name"]

    # Preferences: add only items not already present (case-insensitive dedup)
    existing_lower = {p.lower() for p in merged["preferences"]}
    for pref in new.get("preferences", []):
        if pref.lower() not in existing_lower:
            merged["preferences"].append(pref)
            existing_lower.add(pref.lower())

    return merged


# ---------------------------------------------------------------------------
# LLM-extracted JSON parsing helper (used in llm.py)
# ---------------------------------------------------------------------------

def parse_llm_profile(json_text: str, existing: Profile) -> Profile:
    """
    Parse the JSON string returned by the LLM extraction call.

    On *any* failure (bad JSON, missing keys, wrong types) the existing profile
    is returned unchanged – the app must never crash because of a bad LLM reply.
    """
    try:
        data = json.loads(json_text)
        if not isinstance(data, dict):
            return existing
        new_profile: Profile = {
            "name": data.get("name") if isinstance(data.get("name"), str) else None,
            "preferences": data.get("preferences", []) if isinstance(data.get("preferences"), list) else [],
        }
        return merge_profiles(existing, new_profile)
    except (json.JSONDecodeError, TypeError, KeyError):
        # Silently keep the old profile – never crash
        return existing


# ---------------------------------------------------------------------------
# History trimming
# ---------------------------------------------------------------------------

def trim_history(messages: list[Message], max_history: int) -> list[Message]:
    """
    Return the last *max_history* messages from the conversation.

    The full list is kept in the UI; only this trimmed slice is sent to the LLM.
    """
    return messages[-max_history:]


# ---------------------------------------------------------------------------
# Profile → readable string for injecting into the system prompt
# ---------------------------------------------------------------------------

def profile_to_string(profile: Profile) -> str:
    """Format the profile as a short block appended to the system prompt."""
    name_str = profile.get("name") or "unknown"
    prefs = profile.get("preferences", [])
    prefs_str = ", ".join(prefs) if prefs else "none noted yet"
    return f"Known about the user: name = {name_str}; preferences = [{prefs_str}]"
