import pytest

from _studio import StudioError
from tts_sync import align, int_to_rate, parse_narration, rate_to_int, resolve_cues


def words(*items):
    """Fake edge-tts word boundaries: one word every 0.5 s."""
    return [{"text": t, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, t in enumerate(items)]


def test_parse_narration_strips_markers_and_records_word_index():
    clean, cues = parse_narration("Cada día llegan [[inbox]] miles de correos, y [[spam]] casi la mitad.")
    assert clean == "Cada día llegan miles de correos, y casi la mitad."
    assert [(name, idx) for name, idx, _ in cues] == [("inbox", 3), ("spam", 7)]


def test_parse_narration_collapses_whitespace_around_markers():
    clean, cues = parse_narration("  [[start]]Hola   mundo  [[end]] ")
    assert clean == "Hola mundo"
    assert [(name, idx) for name, idx, _ in cues] == [("start", 0), ("end", 2)]


def test_align_ignores_punctuation_case_and_accents():
    mapping = align("¡Hola, Mundo! Qué tal", words("hola", "mundo", "que", "tal"))
    assert mapping == {0: 0, 1: 1, 2: 2, 3: 3}


def test_align_skips_tokens_the_voice_does_not_report():
    # "—" has no letters, so it never maps and does not shift the following words.
    mapping = align("uno — dos tres", words("uno", "dos", "tres"))
    assert mapping == {0: 0, 2: 1, 3: 2}


def test_rate_round_trip():
    assert rate_to_int("-10%") == -10
    assert int_to_rate(rate_to_int("+5%")) == "+5%"
    with pytest.raises(StudioError):
        rate_to_int("fast")


def test_resolve_cues_uses_word_start_times(monkeypatch):
    monkeypatch.setattr("tts_sync.theme", lambda: {"fps": 60})
    clean, markers = parse_narration("Primero [[a]] esto y luego [[b]] aquello")
    cues = resolve_cues("scene_01", clean, markers,
                        words("primero", "esto", "y", "luego", "aquello"), 2.5, ["a", "b"])
    assert cues == {"a": {"sec": 0.5, "frame": 30}, "b": {"sec": 2.0, "frame": 120}}


@pytest.mark.parametrize("text, expected, message", [
    ("hola [[b]] mundo [[a]]", ["a", "b"], "wrong order"),
    ("hola [[a]] mundo", ["a", "b"], "missing ['b']"),
    ("hola [[a]] mundo [[a]]", ["a"], "duplicated ['a']"),
])
def test_resolve_cues_rejects_markers_that_do_not_match_manifest(text, expected, message):
    clean, markers = parse_narration(text)
    with pytest.raises(StudioError, match=message.replace("[", r"\[").replace("]", r"\]")):
        resolve_cues("scene_01", clean, markers, [], 0, expected)
