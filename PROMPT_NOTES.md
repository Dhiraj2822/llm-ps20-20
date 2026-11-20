# PROMPT_NOTES.md
# Multi-turn Memory Chatbot: Prompt Iteration Log

## Why prompts matter

The LLM is stateless. Every turn, the app sends the full history plus a **system prompt**
that tells the model *how* to behave. Getting that prompt right is the difference between
a chatbot that feels natural and one that constantly annoys the user.

---

## Prompt V1 (initial attempt)

```
You are a helpful assistant. Remember the user's details.
```

### Test inputs run with V1

| # | User input | Observed model output |
|---|-----------|----------------------|
| 1 | "Hi, my name is Dhiraj" | "Hello Dhiraj! How can I help you today, Dhiraj?" |
| 2 | "I like cricket and I'm vegetarian" | "Great Dhiraj! As a vegetarian cricket fan, here are some vegetarian recipes for a cricket match…" |
| 3 | "Explain recursion in two lines" | "Sure Dhiraj! Recursion is when a function calls itself. For example, Dhiraj, factorial(n) = n * factorial(n-1)." |
| 4 | "Suggest a dinner idea" | "Here's a dinner idea for you, Dhiraj: **Butter chicken** – it's delicious!" *(ignored vegetarian)* |
| 5 | "What's my name?" | "Your name is Dhiraj." |
| 6 | "What do I like?" | "You said you like cricket and you are vegetarian." |

### Problems observed with V1

1. **Name overuse** – the model addressed "Dhiraj" in almost every sentence, feeling robotic.
2. **Preference ignored** – in turn 4 it suggested *butter chicken* (non-vegetarian) despite knowing the user was vegetarian.
3. **Invented details** – in one variant it added "you also mentioned you enjoy Bollywood", which the user never said.
4. **Verbose answers** – the prompt said nothing about conciseness, so the model rambled.

---

## Prompt V2 (final, used in production)

```
You are a friendly assistant with session memory.
Use the conversation history and the 'Known about the user' block to remember what the user told you.
Address the user by name occasionally, not in every message.
Respect their preferences when giving suggestions.
If asked about something the user has not told you, say you don't know yet.
Never invent personal details.
Keep answers concise.
```

### Key additions / changes

| Change | Reason |
|--------|---------|
| *"occasionally, not in every message"* | Prevents name overuse (Problem 1). |
| *"Respect their preferences when giving suggestions"* | Forces the model to honour vegetarian/etc. (Problem 2). |
| *"Never invent personal details"* | Stops hallucinated facts like the Bollywood example (Problem 3). |
| *"Keep answers concise"* | Reduces rambling (Problem 4). |
| *"'Known about the user' block"* | References the injected profile so the model knows where to look. |

### Test inputs run with V2

| # | User input | Observed model output |
|---|-----------|----------------------|
| 1 | "Hi, my name is Dhiraj" | "Hi Dhiraj! Nice to meet you. What can I help you with?" |
| 2 | "I like cricket and I'm vegetarian" | "Got it! I'll keep that in mind." |
| 3 | "Explain recursion in two lines" | "Recursion is when a function calls itself to solve a smaller version of the same problem. It terminates at a base case, e.g. `factorial(0) = 1`." |
| 4 | "Suggest a dinner idea" | "How about **Paneer Tikka Masala**? It's hearty, vegetarian, and very flavourful." ✅ |
| 5 | "What's my name?" | "Your name is Dhiraj." ✅ |
| 6 | "What do I like?" | "You mentioned you like cricket and that you're vegetarian." ✅ |
| 7 | (after Clear) "What's my name?" | "I don't know your name yet — I don't have any information from previous sessions." ✅ |

### Improvements with V2

- ✅ Name used once at greeting, not repeated in every sentence.
- ✅ Dinner suggestion correctly vegetarian.
- ✅ No invented facts.
- ✅ Answers noticeably shorter and cleaner.
- ✅ After reset, model correctly says it doesn't know the user.

---

## Profile Extraction Prompt & Regex Iteration

In addition to the conversational system prompt, the profile extraction pipeline (Layer a: regex, Layer b: LLM JSON call) went through critical iteration to handle natural human language and avoid false positives.

### Problem 1: Greedy regex & pronoun capture (Extraction V1)
- **Input:** `"i have completed my todays homework so now i want to watch a movie because i love it so suggest a mystery thriller movie"`
- **V1 Regex output:** `{"preferences": ["it so suggest a mystery thriller movie"]}`
- **Why it failed:** The regex pattern `r"(?:i love)\s+(.+?)(?:\.|$)"` greedily matched everything after `i love`, including pronouns (`it`), conversational conjunctions (`so`), and requests (`suggest a mystery thriller movie`).
- **Fix in Regex:** Added boundary lookaheads stopping at `so`, `because`, `since`, `but`, `if`, and added a validator `_is_valid_preference()` that rejects pronouns (`it`, `them`) and directive verbs (`suggest`, `give`).

### Problem 2: Topic misattribution from general questions
- **Input:** `"what is recursion"` or `"Explain recursion in two lines"`
- **V1 LLM extraction:** `{"preferences": ["recursion"]}`
- **Why it failed:** The model saw the word "recursion" in the prompt and inferred that asking about a topic meant liking it.
- **Fix in LLM Prompt (Extraction V2):**
  Added explicit rules:
  1. *Understand natural expressions:* `"fan of X"`, `"interest in X"`, `"into X"`, `"love X"`, `"like X"`.
  2. *Concise nouns only:* Preferences must be 1–3 word topics (e.g. `"movies"`, `"mystery thrillers"`, `"cricket"`).
  3. *Never infer preferences from questions:* General knowledge queries return `{"name": null, "preferences": []}`.
  4. *Zero pronouns/requests:* Never capture pronouns (`"it"`), reasons (`"because..."`), or commands (`"suggest..."`).

### Observed Results with Extraction V2

| User Input | Extracted Profile |
|------------|-------------------|
| `"what is recursion"` | `{"name": null, "preferences": []}` ✅ |
| `"Explain recursion in two lines"` | `{"name": null, "preferences": []}` ✅ |
| `"i have completed my homework so now i want to watch a movie because i love it so suggest a mystery thriller movie"` | `{"name": null, "preferences": ["mystery thriller"]}` ✅ |
| `"i am really a fan of movies and anime"` | `{"name": null, "preferences": ["movies", "anime"]}` ✅ |
| `"i have interest in robotics and ai"` | `{"name": null, "preferences": ["robotics", "ai"]}` ✅ |
| `"My name is Dhiraj, I like cricket and I'm vegetarian"` | `{"name": "Dhiraj", "preferences": ["cricket", "vegetarian"]}` ✅ |

---

## Conclusion

V1's vague instruction *"Remember the user's details"* gave the model no guidance on **how** to use those details. V2's explicit constraints for name frequency, preference respect, honesty about unknown facts, and conciseness each targeted a specific failure mode observed in V1 testing. The extraction pipeline likewise pairs defensive regex validation with an explicit few-shot JSON prompt so that natural conversational phrases are understood without capturing noise.
