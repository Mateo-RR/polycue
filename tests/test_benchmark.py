from benchmark import generated_paths


def test_generated_paths_only_cover_the_timed_language(tmp_path):
    project = tmp_path / "demo"
    output = project / "output"
    output.mkdir(parents=True)
    for name in ["demo_en-US.mp4", "demo_en-US_subs.mp4", "demo_en-US.srt", "demo_en-US_preview.mp4",
                 "demo_es-ES.mp4", "demo_es-ES_subs.mp4", "demo_en-USX.mp4", "notes.txt"]:
        (output / name).touch()

    paths = {p.relative_to(project).as_posix() for p in generated_paths(project, "demo", "en-US")}

    assert paths == {
        "locales/en-US/audio", "locales/en-US/timings.json", "renders/en-US", "qa/en-US",
        "subtitles/en-US.srt", "subtitles/en-US.ass",
        "output/demo_en-US.mp4", "output/demo_en-US_subs.mp4", "output/demo_en-US.srt", "output/demo_en-US_preview.mp4",
    }


def test_generated_paths_never_include_authored_files(tmp_path):
    paths = [p.name for p in generated_paths(tmp_path / "demo", "demo", "en-US")]
    for authored in ["manifest.json", "narration.json", "strings.json", "scenes"]:
        assert authored not in paths
