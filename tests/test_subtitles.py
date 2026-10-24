from stitch import ass_color, ass_time, balance, finalize_cues, group_cues, srt_time, timed_tokens


def tok(text, start, end=None):
    return {"text": text, "start": start, "end": start + 0.3 if end is None else end}


def test_srt_and_ass_time_formats():
    assert srt_time(3725.0456) == "01:02:05,046"
    assert ass_time(3725.0456) == "1:02:05.05"


def test_ass_color_is_bgr():
    assert ass_color("#38BDF8") == "&H00F8BD38"


def test_balance_splits_two_lines_evenly():
    lines = balance([["uno", "dos", "tres", "cuatro", "cinco"], ["seis"]], max_chars=40)
    assert lines == ["uno dos tres", "cuatro cinco seis"]


def test_group_cues_breaks_on_sentence_end_and_respects_limits():
    tokens = [tok(w, i * 0.4) for i, w in enumerate(
        "Esto es una frase. Y esta es otra frase bastante más larga que no cabe en una línea".split())]
    cues = group_cues(tokens, max_chars=20, max_lines=2)
    assert cues[0]["lines"] == ["Esto es una frase."]
    for c in cues:
        assert len(c["lines"]) <= 2
        assert all(len(line) <= 20 for line in c["lines"])
    # Every word appears exactly once, in order.
    assert " ".join(" ".join(c["lines"]) for c in cues).split() == [t["text"] for t in tokens]


def test_finalize_cues_extends_short_cues_and_closes_small_gaps():
    cues = [{"start": 0.0, "end": 0.2, "lines": ["a"]}, {"start": 1.4, "end": 2.5, "lines": ["b"]},
            {"start": 3.0, "end": 3.6, "lines": ["c"]}]
    out = finalize_cues(cues, scene_end=3.7, min_dur=1.0)
    assert out[0]["end"] == 1.0  # stretched to min_dur; the 0.4 s gap to "b" is kept
    assert out[1]["end"] == 2.5  # already long enough; 0.5 s gap kept
    assert out[2]["end"] == 3.7  # 0.1 s gap to the scene end is merged


def test_timed_tokens_interpolates_words_the_voice_skipped():
    boundaries = [{"text": "Son", "start": 0.0, "end": 0.3}, {"text": "euros", "start": 1.0, "end": 1.4}]
    toks = timed_tokens("Son 42 euros.", boundaries)
    assert [t["text"] for t in toks] == ["Son", "42", "euros."]
    assert toks[1]["start"] == 0.3 and toks[1]["end"] == 1.0
