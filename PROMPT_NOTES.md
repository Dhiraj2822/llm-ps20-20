# PROMPT_NOTES.md
# Multi-turn Memory Chatbot: Prompt Iteration Log

**Student:** Dhiraj Sarawale (Roll No: 20, Class: AIA-7)  
**Date:** 2026-11-21  
**Model:** `qwen2.5:1.5b-instruct` (via Ollama)

---

## 1. System Prompt Iteration (V1 vs V2)

The LLM is stateless. On every turn, the Streamlit app resends the capped history plus an injected system prompt containing the user's active profile (`"Known about the user: name = ...; preferences = [...]"`). The quality and constraints of the system prompt dictate whether the bot behaves naturally or exhibits common failure modes (name overuse, hallucinations, verbosity).

### Prompt V1 (Baseline Attempt)
```
You are a helpful assistant. Remember the user's details.
```

### Prompt V2 (Final Production Prompt)
```
You are a friendly assistant with session memory.
Use the conversation history and the 'Known about the user' block to remember what the user told you.
Address the user by name occasionally, not in every message.
Respect their preferences when giving suggestions.
If asked about something the user has not told you, say you don't know yet.
Never invent personal details.
Keep answers concise.
```

---

## 2. Real Observed Outputs (V1 vs V2 Comparison)

Both prompts were executed against the real Streamlit application using the exact test script:

| # | User Input | Actual V1 Output (`SYSTEM_PROMPT_V1`) | Actual V2 Output (`SYSTEM_PROMPT_V2`) | Improvement in V2 |
|---|------------|--------------------------------------|--------------------------------------|-------------------|
| 1 | `Hi, my name is Dhiraj` | "Hello Dhiraj! How can I assist you today?" | "Hello Dhiraj! How can I assist you today?" | Both acknowledge name appropriately |
| 2 | `I like cricket and I'm vegetarian` | "Great to hear that! Do you have any specific preferences when it comes to playing or watching cricket?" | "That's great to hear! Enjoying sports and a healthy diet sounds like a nice balance for you. If you need any suggestions for cricket or vegetarian options, feel free to ask." | V2 acknowledges both preferences coherently |
| 3 | `Explain recursion in two lines` | "Recursion is a method in which a function calls itself repeatedly until a base case is reached." | "Recursion is a method where a problem is solved by breaking it down into smaller instances of the same problem." | Both adhere to brevity constraint |
| 4 | `Suggest a dinner idea` | "How about trying out a vegetarian stir-fry with your favorite vegetables? It's quick, healthy, and can be customized to your preferences." | "How about a vegetarian pasta with a flavorful tomato sauce? It's hearty, comforting, and delicious!" | V2 gives a direct, appetizing suggestion respecting vegetarian preference |
| 5 | `What's my name?` | "Your name is Dhiraj." | "Your name is Dhiraj." | Accurate recall without verbosity |
| 6 | `What do I like?` | "You like cricket and are vegetarian." | "You like cricket and you're vegetarian." | Both recall cricket and vegetarian |
| 7 | (After Clear) `What's my name?` | — | "I don't have that information. Can you tell me your name, or how to ask for it?" | V2 honestly acknowledges lack of information instead of guessing |

### Key Improvements in V2:
1. **Explicit Reference to Injected Block:** Instructing the model to look at the `'Known about the user'` block anchors its attention on the extracted session profile.
2. **Frequency Control for Name:** Adding `"Address the user by name occasionally, not in every message"` prevents the model from repeating the name in every sentence.
3. **Honesty on Missing Facts:** `"If asked about something the user has not told you, say you don't know yet"` prevents hallucinated details when memory is reset or unpopulated.
4. **Enforced Conciseness:** Keeps conversation fast and focused.

---

## 3. Profile Extraction Iteration (Defensive Engineering)

The extraction pipeline consists of two layers:
1. **Layer A:** Regex extraction for direct statements
2. **Layer B:** LLM JSON extraction (`format="json"`, `temperature=0`)

### Challenge 1: Greedy Regex Matching
- **Input:** `"i have completed my todays homework so now i want to watch a movie because i love it so suggest a mystery thriller movie"`
- **Observed Bug:** The pattern matched `"i love"` and greedily captured `"it so suggest a mystery thriller movie"` as a preference.
- **Fix:** Added clausal termination lookaheads (`so`, `because`, `suggest`, etc.) and a validation function `_is_valid_preference()` rejecting pronouns (`it`, `them`), action commands (`suggest`), and strings $\ge 4$ words.

### Challenge 2: Name Overwriting from Adjectives / Diets
- **Input:** `"I like cricket and I'm vegetarian"`
- **Observed Bug:** The name pattern `r"(?:i'm)\s+([A-Za-z]+)"` matched `"vegetarian"` and overwrote `Dhiraj` with `Vegetarian`.
- **Fix:** Added `_NON_NAMES` exclusion set filtering out diets (`vegetarian`, `vegan`), adjectives (`diabetic`, `allergic`, `happy`), and common conversational words.

### Challenge 3: Knowledge Queries Polluting Profile
- **Input:** `"Explain recursion in two lines"`
- **Observed Bug:** LLM JSON extraction initially interpreted queries about topics as user preferences (extracting `"recursion"`).
- **Fix:** Updated the extraction prompt with explicit negative constraints:
  *"Never infer preferences from topics the user asks about — 'what is recursion' does NOT mean they like recursion."*
