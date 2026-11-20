# TEST_LOG.md
# Multi-turn Memory Chatbot: Manual Test Log
# Date: 2026-11-20
# Model: qwen2.5:7b (via Ollama)
# Tester: Dhiraj

---

## Setup

- Ollama running: ✅
- Model pulled (`qwen2.5:7b`): ✅
- App started (`streamlit run app.py`): ✅
- Fresh session (no prior chat): ✅

---

## Test Script

### Turn 1 — Name introduction

**Input:** `Hi, my name is Dhiraj`

**Expected:** Greeting that uses the name; profile panel shows `Name: Dhiraj`.

**Output:**
> *(Record actual model output here after running)*

**Profile after turn:**
- Name: Dhiraj
- Preferences: []

**Result:** ⬜ PASS / ⬜ FAIL

---

### Turn 2 — Preferences

**Input:** `I like cricket and I'm vegetarian`

**Expected:** Acknowledgement; sidebar shows `cricket` and `vegetarian` in preferences.

**Output:**
> *(Record actual model output here after running)*

**Profile after turn:**
- Name: Dhiraj
- Preferences: [cricket, vegetarian]

**Result:** ⬜ PASS / ⬜ FAIL

---

### Turn 3 — General knowledge (no memory needed)

**Input:** `Explain recursion in two lines`

**Expected:** A clear two-line explanation. Name not necessarily used.

**Output:**
> *(Record actual model output here after running)*

**Result:** ⬜ PASS / ⬜ FAIL

---

### Turn 4 — Preference-aware suggestion

**Input:** `Suggest a dinner idea`

**Expected:** A **vegetarian** dinner suggestion. Must NOT suggest meat-based dishes.

**Output:**
> *(Record actual model output here after running)*

**Vegetarian check:** ⬜ Yes / ⬜ No (FAIL if no)

**Result:** ⬜ PASS / ⬜ FAIL

---

### Turn 5 — Name recall

**Input:** `What's my name?`

**Expected:** "Your name is Dhiraj" (or equivalent).

**Output:**
> *(Record actual model output here after running)*

**Result:** ⬜ PASS / ⬜ FAIL

---

### Turn 6 — Preference recall

**Input:** `What do I like?`

**Expected:** Mentions both **cricket** and **vegetarian**.

**Output:**
> *(Record actual model output here after running)*

**Cricket mentioned:** ⬜ Yes / ⬜ No
**Vegetarian mentioned:** ⬜ Yes / ⬜ No

**Result:** ⬜ PASS / ⬜ FAIL

---

### Turn 7 — Memory reset + name query

**Action:** Click **"🗑️ Clear memory / New chat"** in the sidebar.

**Input (after clear):** `What's my name?`

**Expected:** The chatbot says it does NOT know the user's name (session wiped).

**Output:**
> *(Record actual model output here after running)*

**Result:** ⬜ PASS / ⬜ FAIL

---

## Summary Table

| # | Input | Expected | Result |
|---|-------|----------|--------|
| 1 | Hi, my name is Dhiraj | Greets by name, profile updated | ⬜ |
| 2 | I like cricket and I'm vegetarian | Prefs stored in sidebar | ⬜ |
| 3 | Explain recursion in two lines | Concise explanation | ⬜ |
| 4 | Suggest a dinner idea | Vegetarian suggestion only | ⬜ |
| 5 | What's my name? | "Dhiraj" | ⬜ |
| 6 | What do I like? | cricket + vegetarian | ⬜ |
| 7 | (after clear) What's my name? | "I don't know" | ⬜ |

---

## Notes / Fixes

> *(Record any failures and fixes applied here)*
