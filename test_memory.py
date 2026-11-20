# test_memory.py
# Pytest test suite for Multi-turn Memory Chatbot
#
# LLM calls are fully mocked (ollama not required to run these tests).
# Run with:  pytest test_memory.py -v

from unittest.mock import patch, MagicMock
import pytest

import memory
import config


# ===========================================================================
# memory.regex_extract()
# ===========================================================================

class TestRegexExtract:
    """Test the first-pass regex name and preference detector."""

    def test_name_my_name_is(self):
        result = memory.regex_extract("My name is Dhiraj")
        assert result["name"] == "Dhiraj"

    def test_name_i_am(self):
        result = memory.regex_extract("I am Priya, nice to meet you")
        assert result["name"] == "Priya"

    def test_name_call_me(self):
        result = memory.regex_extract("Please call me Sam")
        assert result["name"] == "Sam"

    def test_name_actually_call_me(self):
        result = memory.regex_extract("Actually call me Raj")
        assert result["name"] == "Raj"

    def test_preference_i_like(self):
        result = memory.regex_extract("I like cricket")
        assert any("cricket" in p.lower() for p in result["preferences"])

    def test_preference_i_love(self):
        result = memory.regex_extract("I love pizza")
        assert any("pizza" in p.lower() for p in result["preferences"])

    def test_preference_vegetarian(self):
        result = memory.regex_extract("I'm vegetarian")
        assert any("vegetarian" in p.lower() for p in result["preferences"])

    def test_preference_allergic(self):
        result = memory.regex_extract("I'm allergic to peanuts")
        assert any("peanut" in p.lower() for p in result["preferences"])

    def test_no_match_returns_none_and_empty(self):
        result = memory.regex_extract("What is the weather today?")
        assert result["name"] is None
        assert result["preferences"] == []

    def test_pronoun_it_not_extracted(self):
        """'I love it' should not treat the pronoun 'it' as a preference."""
        result = memory.regex_extract("I love it")
        assert "it" not in [p.lower() for p in result["preferences"]]

    def test_complex_sentence_does_not_extract_junk(self):
        """Conversational sentences with conjunctions/requests must not pollute regex."""
        sentence = "i have completed my todays homework so now i want to watch a movie because i love it so suggest a mystery thriller movie"
        result = memory.regex_extract(sentence)
        # Regex should not capture clauses like 'it so suggest a mystery thriller movie'
        assert not any("suggest" in p.lower() or p.lower() == "it" for p in result["preferences"])


# ===========================================================================
# memory.merge_profiles()
# ===========================================================================

class TestMergeProfiles:
    """Test that merging follows the assignment rules."""

    def test_name_added_when_new(self):
        old = {"name": None, "preferences": []}
        new = {"name": "Dhiraj", "preferences": []}
        merged = memory.merge_profiles(old, new)
        assert merged["name"] == "Dhiraj"

    def test_name_replaced_by_explicit_new_name(self):
        """A newer explicit name must replace the old one (handles 'call me Sam')."""
        old = {"name": "Dhiraj", "preferences": []}
        new = {"name": "Sam", "preferences": []}
        merged = memory.merge_profiles(old, new)
        assert merged["name"] == "Sam"

    def test_name_not_overwritten_by_null(self):
        """An existing name must never be replaced by None."""
        old = {"name": "Dhiraj", "preferences": []}
        new = {"name": None, "preferences": []}
        merged = memory.merge_profiles(old, new)
        assert merged["name"] == "Dhiraj"

    def test_preferences_merged(self):
        old = {"name": None, "preferences": ["cricket"]}
        new = {"name": None, "preferences": ["vegetarian"]}
        merged = memory.merge_profiles(old, new)
        assert "cricket" in merged["preferences"]
        assert "vegetarian" in merged["preferences"]

    def test_preferences_deduplicated_case_insensitively(self):
        """'Cricket' and 'cricket' are the same preference."""
        old = {"name": None, "preferences": ["Cricket"]}
        new = {"name": None, "preferences": ["cricket"]}
        merged = memory.merge_profiles(old, new)
        # Should contain exactly one entry
        lower_prefs = [p.lower() for p in merged["preferences"]]
        assert lower_prefs.count("cricket") == 1

    def test_multiple_preferences_dedup(self):
        old = {"name": None, "preferences": ["pizza", "cricket"]}
        new = {"name": None, "preferences": ["Pizza", "Chess"]}
        merged = memory.merge_profiles(old, new)
        lower = [p.lower() for p in merged["preferences"]]
        assert lower.count("pizza") == 1
        assert "chess" in lower


# ===========================================================================
# memory.parse_llm_profile()  – JSON failure fallback
# ===========================================================================

class TestParseLlmProfile:
    """Test that bad LLM JSON output never corrupts the profile."""

    def setup_method(self):
        self.existing = {"name": "Dhiraj", "preferences": ["cricket"]}

    def test_valid_json_merges(self):
        json_text = '{"name": "Dhiraj", "preferences": ["vegetarian"]}'
        result = memory.parse_llm_profile(json_text, self.existing)
        assert result["name"] == "Dhiraj"
        assert "vegetarian" in result["preferences"]

    def test_invalid_json_returns_existing(self):
        result = memory.parse_llm_profile("not json at all", self.existing)
        assert result == self.existing

    def test_empty_string_returns_existing(self):
        result = memory.parse_llm_profile("", self.existing)
        assert result == self.existing

    def test_json_array_returns_existing(self):
        """LLM sometimes returns a JSON array instead of an object."""
        result = memory.parse_llm_profile('["name", "Dhiraj"]', self.existing)
        assert result == self.existing

    def test_null_name_in_json_keeps_existing_name(self):
        json_text = '{"name": null, "preferences": []}'
        result = memory.parse_llm_profile(json_text, self.existing)
        assert result["name"] == "Dhiraj"   # never overwrite with null

    def test_missing_keys_returns_existing(self):
        result = memory.parse_llm_profile('{"foo": "bar"}', self.existing)
        # Should not crash, and existing is kept
        assert result["name"] == "Dhiraj"


# ===========================================================================
# memory.trim_history()
# ===========================================================================

class TestTrimHistory:
    """Test that history is trimmed to MAX_HISTORY messages."""

    def _make_messages(self, n: int) -> list[memory.Message]:
        return [{"role": "user", "content": f"msg {i}"} for i in range(n)]

    def test_no_trim_when_under_limit(self):
        msgs = self._make_messages(5)
        result = memory.trim_history(msgs, 12)
        assert result == msgs

    def test_trim_to_max(self):
        msgs = self._make_messages(20)
        result = memory.trim_history(msgs, config.MAX_HISTORY)
        assert len(result) == config.MAX_HISTORY
        # Must be the LAST MAX_HISTORY messages
        assert result[-1]["content"] == "msg 19"
        assert result[0]["content"] == f"msg {20 - config.MAX_HISTORY}"

    def test_trim_exact_boundary(self):
        msgs = self._make_messages(config.MAX_HISTORY)
        result = memory.trim_history(msgs, config.MAX_HISTORY)
        assert len(result) == config.MAX_HISTORY

    def test_empty_messages(self):
        result = memory.trim_history([], config.MAX_HISTORY)
        assert result == []


# ===========================================================================
# memory.empty_profile() and reset semantics
# ===========================================================================

class TestReset:
    """Resetting returns a clean, empty profile."""

    def test_empty_profile_structure(self):
        p = memory.empty_profile()
        assert p["name"] is None
        assert p["preferences"] == []

    def test_empty_profile_is_independent(self):
        """Two calls must return independent dicts (not the same object)."""
        p1 = memory.empty_profile()
        p2 = memory.empty_profile()
        p1["name"] = "Dhiraj"
        assert p2["name"] is None


# ===========================================================================
# llm.extract_profile() – mocked (Ollama not required)
# ===========================================================================

class TestExtractProfileMocked:
    """
    llm.extract_profile() must gracefully fall back when Ollama errors out.
    We mock ollama.chat so pytest never needs Ollama running.
    """

    def test_success_merges_profile(self):
        """Good JSON response from LLM should be merged into the profile."""
        mock_response = MagicMock()
        mock_response.message.content = '{"name": "Dhiraj", "preferences": ["cricket"]}'

        with patch("ollama.chat", return_value=mock_response):
            import llm as llm_module
            existing = memory.empty_profile()
            result = llm_module.extract_profile("My name is Dhiraj", existing)
            assert result["name"] == "Dhiraj"
            assert "cricket" in result["preferences"]

    def test_connection_error_returns_existing(self):
        """When Ollama is down, extract_profile must return existing unchanged."""
        with patch("ollama.chat", side_effect=ConnectionError("refused")):
            import llm as llm_module
            existing = {"name": "Dhiraj", "preferences": ["cricket"]}
            result = llm_module.extract_profile("hello", existing)
            assert result == existing

    def test_bad_json_returns_existing(self):
        """LLM returns garbage → existing profile preserved."""
        mock_response = MagicMock()
        mock_response.message.content = "I cannot parse this"

        with patch("ollama.chat", return_value=mock_response):
            import llm as llm_module
            existing = {"name": "Priya", "preferences": ["yoga"]}
            result = llm_module.extract_profile("hello", existing)
            assert result == existing


# ===========================================================================
# memory.is_personal_statement()  – question guard
# ===========================================================================

class TestIsPersonalStatement:
    """The guard must reject pure questions and accept any first-person statement."""

    def test_question_what_is_rejected(self):
        # No "I"/"my" at all → skip
        assert memory.is_personal_statement("what is recursion") is False

    def test_question_mark_rejected(self):
        # Ends with ? → always skip
        assert memory.is_personal_statement("What's my name?") is False

    def test_explain_request_rejected(self):
        # No first-person pronoun → skip
        assert memory.is_personal_statement("Explain recursion in two lines") is False

    def test_suggest_request_rejected(self):
        assert memory.is_personal_statement("Suggest a dinner idea") is False

    def test_how_question_rejected(self):
        assert memory.is_personal_statement("how does a neural network work") is False

    # --- should PASS (accepted) ---
    def test_name_statement_accepted(self):
        assert memory.is_personal_statement("My name is Dhiraj") is True

    def test_i_like_accepted(self):
        assert memory.is_personal_statement("I like cricket") is True

    def test_vegetarian_accepted(self):
        assert memory.is_personal_statement("I'm vegetarian") is True

    def test_i_prefer_accepted(self):
        assert memory.is_personal_statement("I prefer Python over Java") is True

    def test_i_have_interest_accepted(self):
        # Natural phrasing the old guard missed
        assert memory.is_personal_statement("I have interest in cricket") is True

    def test_i_am_fan_accepted(self):
        # Fan-of phrasing the old guard missed
        assert memory.is_personal_statement("I'm really a fan of movies") is True

    def test_i_am_into_accepted(self):
        assert memory.is_personal_statement("I am really into hiking") is True

    def test_i_enjoy_accepted(self):
        assert memory.is_personal_statement("I enjoy reading sci-fi") is True


# ===========================================================================
# End-to-end flow (mocked LLM) — name replacement scenario
# ===========================================================================

class TestNameReplacement:
    """
    Simulate the full flow: user first says 'my name is Dhiraj',
    then says 'actually call me Sam'. The profile should update.
    """

    def test_name_replacement_flow(self):
        profile = memory.empty_profile()

        # First message
        r1 = memory.regex_extract("my name is Dhiraj")
        profile = memory.merge_profiles(profile, r1)
        assert profile["name"] == "Dhiraj"

        # Second message – name change
        r2 = memory.regex_extract("actually call me Sam")
        profile = memory.merge_profiles(profile, r2)
        assert profile["name"] == "Sam"
