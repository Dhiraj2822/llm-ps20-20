# TEST_LOG.md
# PS20: Multi-turn Memory Chatbot — Real Manual Test Log

- **Tester:** Dhiraj Sarawale (Roll No: 20, Class: AIA-7)
- **Problem Statement:** PS20: Multi-turn Memory Chatbot
- **Date & Time:** 2026-11-21 15:18 IST
- **Model:** `qwen2.5:1.5b-instruct` (via local Ollama, temperature=0 for extraction, default for chat)
- **Interface:** Streamlit on `http://localhost:8501` (automated browser interaction via Playwright)
- **Active System Prompt:** V2 (Final)

---

## Real Manual Test Execution (V2 Prompt)

### Turn 1 — Name Introduction
- **User Input:** `Hi, my name is Dhiraj`
- **Observed Assistant Output:**
  > "Hello Dhiraj! How can I assist you today?"
- **Observed Profile State:**
  - Name: `Dhiraj`
  - Preferences: `[]`
- **Result:** **PASS** — Model greeted the user politely by name; sidebar profile recorded `Name: Dhiraj`.

---

### Turn 2 — Preferences Stated
- **User Input:** `I like cricket and I'm vegetarian`
- **Observed Assistant Output:**
  > "That's great to hear! Enjoying sports and a healthy diet sounds like a nice balance for you. If you need any suggestions for cricket or vegetarian options, feel free to ask."
- **Observed Profile State:**
  - Name: `Dhiraj`
  - Preferences: `['cricket', 'vegetarian']`
- **Result:** **PASS** — Both preferences extracted and stored; name `Dhiraj` preserved.

---

### Turn 3 — General Knowledge (No Memory Pollution)
- **User Input:** `Explain recursion in two lines`
- **Observed Assistant Output:**
  > "Recursion is a method where a problem is solved by breaking it down into smaller instances of the same problem."
- **Observed Profile State:**
  - Name: `Dhiraj`
  - Preferences: `['cricket', 'vegetarian']`
- **Result:** **PASS** — Provided concise explanation; did not pollute profile with "recursion".

---

### Turn 4 — Preference-Aware Suggestion
- **User Input:** `Suggest a dinner idea`
- **Observed Assistant Output:**
  > "How about a vegetarian pasta with a flavorful tomato sauce? It's hearty, comforting, and delicious!"
- **Observed Profile State:**
  - Name: `Dhiraj`
  - Preferences: `['cricket', 'vegetarian']`
- **Vegetarian Check:** Strictly vegetarian (tomato pasta with vegetables).
- **Result:** **PASS** — Accurately respected the vegetarian constraint from injected session memory.

---

### Turn 5 — Name Recall
- **User Input:** `What's my name?`
- **Observed Assistant Output:**
  > "Your name is Dhiraj."
- **Observed Profile State:**
  - Name: `Dhiraj`
  - Preferences: `['cricket', 'vegetarian']`
- **Result:** **PASS** — Retrieved name accurately without hallucinations.

---

### Turn 6 — Preferences Recall
- **User Input:** `What do I like?`
- **Observed Assistant Output:**
  > "You like cricket and you're vegetarian."
- **Observed Profile State:**
  - Name: `Dhiraj`
  - Preferences: `['cricket', 'vegetarian']`
- **Result:** **PASS** — Recalled both cricket and vegetarian preferences completely.

---

### Turn 7 — Session Reset & Name Query
- **User Action:** Clicked **"Clear memory / New chat"** button in sidebar
- **User Input:** `What's my name?`
- **Observed Assistant Output:**
  > "I don't have that information. Can you tell me your name, or how to ask for it?"
- **Observed Profile State:**
  - Name: `None` (`not known yet`)
  - Preferences: `[]` (`none noted yet`)
- **Result:** **PASS** — Session state cleared; assistant honestly acknowledged lack of prior information.

---

## Test Summary Table

| Turn # | User Input | Expected Behavior | Actual Behavior | Status |
|:---:|:---|:---|:---|:---:|
| 1 | `Hi, my name is Dhiraj` | Greets by name, stores name in profile | Greeted Dhiraj, profile `name: Dhiraj` | **PASS** |
| 2 | `I like cricket and I'm vegetarian` | Stores preferences without overwriting name | Stored `cricket`, `vegetarian`, preserved `Dhiraj` | **PASS** |
| 3 | `Explain recursion in two lines` | Concise explanation, no memory change | 1-2 line concept, profile unchanged | **PASS** |
| 4 | `Suggest a dinner idea` | Suggests strictly vegetarian meal | Vegetarian pasta with tomato sauce | **PASS** |
| 5 | `What's my name?` | Recalls name as "Dhiraj" | Answered "Your name is Dhiraj." | **PASS** |
| 6 | `What do I like?` | Recalls cricket and vegetarian | Recalled cricket and vegetarian | **PASS** |
| 7 | (After Clear) `What's my name?` | Says it doesn't know the name | "I don't have that information." | **PASS** |

**Score: 7 / 7 Turns Passed (100%)**

---

## Challenges & Fixes

1. **Dietary Descriptor Misclassified as Name:**
   - *Problem:* In turn 2 ("I'm vegetarian"), the name regex `r"(?:i'm)\s+([A-Za-z]+)"` originally captured "Vegetarian" as a replacement name, overwriting "Dhiraj".
   - *Fix:* Added `_NON_NAMES` validation block in `memory.py` excluding common descriptors, diets, and states (`vegetarian`, `vegan`, `allergic`, etc.) from being assigned as user names.

2. **Greedy Regex Clause Capture:**
   - *Problem:* Sentences with conversational transitions like *"because i love it so suggest a mystery thriller movie"* caused regex to capture *"it so suggest a mystery thriller movie"* as a preference.
   - *Fix:* Added clausal stop-boundaries (`so`, `because`, `suggest`) and `_is_valid_preference()` rejecting pronouns (`it`, `them`), action verbs (`suggest`), and strings over 4 words.

3. **General Knowledge Topic Misattribution:**
   - *Problem:* Queries like *"What is recursion"* initially triggered topic extraction, adding "recursion" as a user preference.
   - *Fix:* Formulated strict few-shot negative rules in LLM extraction prompt and pre-filtered query sentences without first-person markers.
