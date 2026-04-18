"""Tests for shortform.text.cleaner — pure functions, no I/O."""

from shortform.text.cleaner import (
    apply_tts_fixes,
    censor,
    expand_slang,
    prepare_body,
    prepare_title_for_display,
    prepare_title_for_tts,
    split_sentences,
    strip_trailing_sections,
)


class TestExpandSlang:
    def test_expands_aita_at_word_boundary(self):
        assert expand_slang("AITA for leaving?") == "Am I the A-hole for leaving?"

    def test_aitah_wins_over_aita(self):
        # AITAH must be replaced before AITA's regex ever sees the string.
        assert expand_slang("AITAH for this?") == "Am I the A-hole here for this?"

    def test_case_insensitive(self):
        assert expand_slang("aita for this?") == "Am I the A-hole for this?"

    def test_does_not_match_inside_word(self):
        # "PAITA" should not be expanded.
        assert expand_slang("PAITA is a place") == "PAITA is a place"

    def test_tifu_expanded(self):
        assert expand_slang("TIFU by doing X") == "Today I Effed Up by doing X"


class TestCensor:
    def test_substring_match_no_word_boundary(self):
        assert censor("assholes everywhere") == "a**holes everywhere"

    def test_suicid_partial_covers_suicide_and_suicidal(self):
        assert censor("suicide and suicidal") == "suic*de and suic*dal"

    def test_case_insensitive(self):
        assert censor("FUCK this") == "f*** this"

    def test_multiple_words_all_censored(self):
        # Regression: original single-file code only censored the last matching key
        # due to a typo (see cleaner.py module docstring). Ensure all keys apply.
        assert censor("shit and fuck") == "sh** and f***"


class TestApplyTtsFixes:
    def test_ellipsis_becomes_comma(self):
        assert apply_tts_fixes("wait... really") == "wait, really"

    def test_long_ellipsis_becomes_comma(self):
        assert apply_tts_fixes("wait......... really") == "wait, really"


class TestStripTrailingSections:
    def test_strips_tldr(self):
        assert strip_trailing_sections("body text\ntl;dr something") == "body text"

    def test_strips_edit(self):
        assert strip_trailing_sections("body\nEDIT: more") == "body"

    def test_strips_update(self):
        assert strip_trailing_sections("body\nupdate: x") == "body"

    def test_keeps_text_when_no_terminator(self):
        assert strip_trailing_sections("just some body") == "just some body"

    def test_tldr_variants(self):
        assert strip_trailing_sections("body\ntldr x") == "body"
        assert strip_trailing_sections("body\ntl.dr x") == "body"
        assert strip_trailing_sections("body\ntl/dr x") == "body"


class TestSplitSentences:
    def test_splits_on_period(self):
        # Note: the lookbehind requires 3 chars (non-upper, any, .?!) so short
        # sentences like "Hi." don't split — documented heuristic.
        result = split_sentences("Hello world. Another one here.")
        assert len(result) == 2
        assert "Hello world." in result[0]

    def test_splits_on_question_mark(self):
        result = split_sentences("Really happens. Are you sure?")
        assert len(result) == 2

    def test_preserves_dr_honorific(self):
        # "Dr. Smith" should NOT split: the char before "r." is D (uppercase),
        # so the 3-char lookbehind [^A-Z].[.?!] fails on "Dr.".
        result = split_sentences("Dr. Smith arrived late. He was tired.")
        assert len(result) == 2
        assert "Dr. Smith arrived late." in result[0]

    def test_tight_acronym_limitation(self):
        # Known limitation of the original heuristic: "U.S." DOES get split
        # because the window " U." satisfies [^A-Z] (space) + any (U) + . .
        # Documented here so the behavior doesn't silently regress.
        result = split_sentences("The U.S. government did it.")
        assert len(result) >= 2

    def test_ignores_empty_and_whitespace(self):
        assert split_sentences("") == []
        assert split_sentences("   ") == []


class TestPrepareTitle:
    def test_for_tts_expands_slang_no_censor(self):
        assert prepare_title_for_tts("AITA for saying fuck") == "Am I the A-hole for saying fuck"

    def test_for_display_expands_and_censors(self):
        assert (
            prepare_title_for_display("AITA for saying fuck")
            == "Am I the A-hole for saying f***"
        )


class TestPrepareBody:
    def test_end_to_end(self):
        raw = "AITA for real. This is a story.\ntl;dr not relevant"
        result = prepare_body(raw)
        # tl;dr should be stripped, slang expanded, and sentences split.
        assert all("tl;dr" not in s.lower() for s in result)
        joined = " ".join(result)
        assert "Am I the A-hole" in joined

    def test_unescapes_html_entities(self):
        raw = "They said &amp; this is fine. Another sentence."
        result = prepare_body(raw)
        joined = " ".join(result)
        assert "&" in joined
        assert "&amp;" not in joined

    def test_strips_zero_width_space(self):
        raw = "hello\u200bworld is a thing. Another here."
        result = prepare_body(raw)
        joined = " ".join(result)
        assert "\u200b" not in joined

    def test_normalizes_newlines(self):
        raw = "line one ends here.\nline two ends here."
        result = prepare_body(raw)
        joined = " ".join(result)
        assert "\n" not in joined
