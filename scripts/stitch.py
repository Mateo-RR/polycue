"""Normalize clips, mux each scene's voiceover, concatenate, normalize loudness, add subtitles.

Usage:
  stitch.py --slug <slug> --lang <lang> [--subs burn|soft|none] [--preview]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import struct

from _studio import (
    REPO, SHARED, clip_path, fail, load_json, locale_dir, main_wrapper, manifest, print_table, project_dir,
    rel, run, theme, timings, tool, video_info,
)
from tts_sync import align, parse_narration

SAMPLE_RATE = 48000
LOUDNORM = "I=-14:TP=-1:LRA=11"
BREAK_PUNCT = ".?!;:…"
SOFT_PUNCT = ","
MERGE_GAP_SEC = 0.3
BT709_TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]

ISO639_2 = {"es": "spa", "en": "eng", "fr": "fra", "de": "deu", "it": "ita", "pt": "por", "gl": "glg",
            "ca": "cat", "eu": "eus", "nl": "nld", "ja": "jpn", "zh": "zho", "ko": "kor", "ru": "rus"}


# ---------------------------------------------------------------- subtitles

def timed_tokens(narration_text: str, words: list[dict]) -> list[dict]:
    """Narration tokens (with punctuation) timed from the TTS word boundaries."""
    clean, _ = parse_narration(narration_text)
    tokens = clean.split()
    mapping = align(clean, words)
    out = []
    for i, tok in enumerate(tokens):
        if i in mapping:
            w = words[mapping[i]]
            out.append({"text": tok, "start": w["start"], "end": w["end"]})
        else:
            out.append({"text": tok, "start": None, "end": None})
    # Interpolate tokens the TTS did not report (symbols, numbers read differently…).
    for i, t in enumerate(out):
        if t["start"] is None:
            prev_end = next((out[k]["end"] for k in range(i - 1, -1, -1) if out[k]["end"] is not None), 0.0)
            nxt = next((out[k]["start"] for k in range(i + 1, len(out)) if out[k]["start"] is not None), prev_end)
            t["start"], t["end"] = prev_end, max(prev_end, nxt)
    return out


def balance(greedy: list[list[str]], max_chars: int) -> list[str]:
    """Rebalance a two-line cue so both lines have similar length (no widows)."""
    greedy = [line for line in greedy if line]
    if len(greedy) != 2:
        return [" ".join(line) for line in greedy]
    words = greedy[0] + greedy[1]
    best, best_score = None, None
    for cut in range(1, len(words)):
        a, b = " ".join(words[:cut]), " ".join(words[cut:])
        over = max(0, len(a) - max_chars) + max(0, len(b) - max_chars)
        score = (over, abs(len(a) - len(b)))
        if best_score is None or score < best_score:
            best, best_score = [a, b], score
    return best or [" ".join(words)]


def group_cues(tokens: list[dict], max_chars: int, max_lines: int) -> list[dict]:
    cues, lines = [], [[]]

    def close():
        if any(lines):
            toks = [t for line in lines for t in line]
            cues.append({"start": toks[0]["start"], "end": toks[-1]["end"],
                         "lines": balance([[t["text"] for t in line] for line in lines], max_chars)})
        lines.clear()
        lines.append([])

    for tok in tokens:
        current = lines[-1]
        candidate = " ".join([t["text"] for t in current] + [tok["text"]])
        if current and len(candidate) > max_chars:
            if len(lines) < max_lines:
                lines.append([tok])
            else:
                close()
                lines[-1].append(tok)
        else:
            current.append(tok)
        chars = sum(len(" ".join(t["text"] for t in line)) for line in lines)
        last = tok["text"][-1]
        if last in BREAK_PUNCT or (last in SOFT_PUNCT and chars >= max_chars * 0.6 * max_lines / 2):
            close()
    close()
    return cues


def finalize_cues(cues: list[dict], scene_end: float, min_dur: float) -> list[dict]:
    for i, c in enumerate(cues):
        limit = cues[i + 1]["start"] if i + 1 < len(cues) else scene_end
        if c["end"] - c["start"] < min_dur:
            c["end"] = min(c["start"] + min_dur, limit)
        if limit - c["end"] < MERGE_GAP_SEC:
            c["end"] = limit
        c["end"] = min(c["end"], scene_end)
    return cues


def srt_time(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ass_time(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000:d}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_color(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def font_win_height_ratio(font_file) -> float:
    """(usWinAscent + usWinDescent) / unitsPerEm: libass sizes fonts by this height, CSS by the em."""
    data = font_file.read_bytes()
    n = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for i in range(n):
        tag, _, offset, _ = struct.unpack(">4sIII", data[12 + 16 * i: 28 + 16 * i])
        tables[tag.decode()] = offset
    upm = struct.unpack(">H", data[tables["head"] + 18: tables["head"] + 20])[0]
    asc, desc = struct.unpack(">HH", data[tables["OS/2"] + 74: tables["OS/2"] + 78])
    return (asc + desc) / upm


def write_subtitles(cues, slug, lang, orientation, th) -> tuple:
    sub = th["subtitles"]
    sub_dir = project_dir(slug) / "subtitles"
    sub_dir.mkdir(parents=True, exist_ok=True)
    srt_path, ass_path = sub_dir / f"{lang}.srt", sub_dir / f"{lang}.ass"

    with srt_path.open("w", encoding="utf-8", newline="\n") as fh:
        for i, c in enumerate(cues, 1):
            fh.write(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n" + "\n".join(c["lines"]) + "\n\n")

    canvas = th["canvas"][orientation]
    W, H = canvas["width"], canvas["height"]
    zone = th["zones"][orientation]["subtitles"]
    margin = round(W * (1 - th["safe_area"]["ratio"]) / 2)
    cx, cy = W // 2, round(H * (zone["top"] + zone["bottom"]) / 2)
    weight_file = "Inter-Bold.ttf" if sub["weight"] >= 600 else "Inter-Regular.ttf"
    fonts_dir = REPO / th["fonts"]["dir"]
    size = round(sub["size_px"][orientation] * font_win_height_ratio(fonts_dir / weight_file))
    bold = -1 if sub["weight"] >= 600 else 0
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{sub['font']},{size},{ass_color(sub['color'])},{ass_color(sub['highlight_color'])},{ass_color(sub['outline_color'])},&H00000000,{bold},0,0,0,100,100,0,0,1,{sub['outline_px']},0,5,{margin},{margin},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with ass_path.open("w", encoding="utf-8-sig", newline="\n") as fh:
        fh.write(header)
        for c in cues:
            text = "\\N".join(line.replace("{", "(").replace("}", ")") for line in c["lines"])
            fh.write(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{{\\pos({cx},{cy})}}{text}\n")
    return srt_path, ass_path


# ---------------------------------------------------------------- video

def normalize_scene(clip, audio, out, W, H, fps, total_frames, bg) -> None:
    samples = total_frames * SAMPLE_RATE // fps
    # Both engines encode with the BT.601 matrix (Remotion full range, Manim limited and
    # untagged). Decode to RGB with that matrix, then encode limited-range BT.709, so the
    # engines match and players decode them the same. swscale ignores matrix changes in
    # direct YUV→YUV conversions, hence the RGB step.
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos:"
          f"in_color_matrix=bt601,format=gbrp,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{bg.lstrip('#')},setsar=1,fps={fps},"
          f"scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
          f"tpad=stop_mode=clone:stop_duration=5,trim=end_frame={total_frames},setpts=PTS-STARTPTS[v];"
          f"[1:a]aresample={SAMPLE_RATE},aformat=sample_fmts=s16:channel_layouts=stereo,apad,"
          f"atrim=end_sample={samples},asetpts=N/SR/TB[a]")
    run([tool("ffmpeg"), "-y", "-v", "error", "-i", clip, "-i", audio, "-filter_complex", vf,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", *BT709_TAGS, "-r", str(fps), "-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE), out])


def loudnorm_audio(src, out, total_samples: int) -> str:
    """Two-pass EBU R128 normalization to -14 LUFS / -1 dBTP. Returns a short report.

    The result is trimmed/padded to exactly ``total_samples`` so audio never outlasts video.
    """
    p1 = run([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", src, "-vn",
              "-af", f"loudnorm={LOUDNORM}:print_format=json", "-f", "null", "-"])
    blob = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", p1.stderr)
    if not blob:
        fail("loudnorm pass 1 produced no measurement")
    m = json.loads(blob[-1])
    if m["input_i"] in ("-inf", "inf"):
        af = f"aresample={SAMPLE_RATE}"
        report = "audio is silent; loudness not normalized"
    else:
        af = (f"loudnorm={LOUDNORM}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
              f"linear=true:print_format=summary,aresample={SAMPLE_RATE}")
        report = f"input {m['input_i']} LUFS / {m['input_tp']} dBTP → target -14 LUFS / -1 dBTP"
    # Timestamps are rebuilt from the sample count: loudnorm's dynamic mode emits irregular
    # pts, which made the AAC track outlast the video by a couple of frames.
    af += f",apad,atrim=end_sample={total_samples},asetpts=N/SR/TB"
    p2 = run([tool("ffmpeg"), "-y", "-hide_banner", "-nostats", "-i", src, "-vn", "-af", af,
              "-c:a", "aac", "-b:a", "192k", "-ar", str(SAMPLE_RATE), "-ac", "2", out])
    mode = re.search(r"Normalization Type:\s*(\w+)", p2.stderr)
    if mode:
        report += f" ({mode.group(1).lower()} mode)"
    return report


def verify(path, expected_frames, fps, W, H) -> list[str]:
    info = video_info(path)
    problems = []
    if info["video_streams"] != 1 or info["audio_streams"] != 1:
        problems.append(f"streams v={info['video_streams']} a={info['audio_streams']} (expected 1+1)")
    if (info["width"], info["height"]) != (W, H):
        problems.append(f"resolution {info['width']}x{info['height']} (expected {W}x{H})")
    if round(info["fps"]) != fps:
        problems.append(f"fps {info['fps']:g} (expected {fps})")
    if info["pix_fmt"] != "yuv420p":
        problems.append(f"pix_fmt {info['pix_fmt']}")
    expected_sec = expected_frames / fps
    if abs(info["duration"] - expected_sec) > 1 / fps + 1e-3:
        problems.append(f"duration {info['duration']:.3f}s (expected {expected_sec:.3f}s ± 1 frame)")
    if info["frames"] != expected_frames:
        problems.append(f"video frames {info['frames']} (expected {expected_frames})")
    return problems


def main():
    ap = argparse.ArgumentParser(description="Assemble the final video: clips + voiceover + loudness + subtitles.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--subs", choices=["burn", "soft", "none"],
                    help="subtitle mode (default: manifest.subtitles, else none); .srt is always written")
    ap.add_argument("--preview", action="store_true", help="use preview clips and output a half-size video")
    args = ap.parse_args()

    man = manifest(args.slug)
    tim = timings(args.slug, args.lang)
    th = theme()
    fps = tim["fps"]
    orientation = man.get("orientation", "vertical")
    subs = args.subs or man.get("subtitles", "none")
    canvas = th["canvas"][orientation]
    W, H = canvas["width"], canvas["height"]
    if args.preview:
        W, H = W // 2, H // 2
    ldir = locale_dir(args.slug, args.lang)
    narration = load_json(ldir / "narration.json")

    work = project_dir(args.slug) / "renders" / args.lang / ("_stitch_preview" if args.preview else "_stitch")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    # 1. Per-scene normalization + audio mux; collect subtitle cues.
    offset_frames = 0
    parts, cues, rows = [], [], []
    for scene in man["scenes"]:
        sid = scene["id"]
        if sid not in tim["scenes"]:
            fail(f"{sid} missing in timings.json; run tts_sync.py first")
        st = tim["scenes"][sid]
        clip = clip_path(args.slug, args.lang, sid, args.preview)
        audio = ldir / st["audio"]
        for p in (clip, audio):
            if not p.exists():
                fail(f"{sid}: missing {rel(p)}")
        part = work / f"{sid}.mov"
        print(f"[{sid}] normalizing + muxing …", flush=True)
        normalize_scene(clip, audio, part, W, H, fps, st["total_frames"], th["colors"]["background"])
        parts.append(part)

        offset = offset_frames / fps
        scene_end = offset + st["total_frames"] / fps
        toks = timed_tokens(narration[sid]["text"], st["words"])
        for t in toks:
            t["start"] += offset
            t["end"] += offset
        scene_cues = group_cues(toks, th["subtitles"]["max_chars_per_line"][orientation], th["subtitles"]["max_lines"])
        cues += finalize_cues(scene_cues, scene_end, th["subtitles"]["min_duration_sec"])
        rows.append([sid, scene.get("engine"), f"{offset:.3f}", st["total_frames"], f"{st['total_frames'] / fps:.3f}"])
        offset_frames += st["total_frames"]

    # 2. Concatenate (identical parameters → stream copy).
    concat_list = work / "concat.txt"
    concat_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    concat = work / "concat.mov"
    run([tool("ffmpeg"), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", concat])

    # 3. Loudness.
    norm_audio = work / "audio.m4a"
    loud_report = loudnorm_audio(concat, norm_audio, offset_frames * SAMPLE_RATE // fps)

    # 4. Subtitles.
    srt_path, ass_path = write_subtitles(cues, args.slug, args.lang, orientation, th)

    # 5. Outputs.
    out_dir = project_dir(args.slug) / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_preview" if args.preview else ""
    plain = out_dir / f"{args.slug}_{args.lang}{suffix}.mp4"
    lang_tag = ISO639_2.get(args.lang.split("-")[0].lower(), "und")
    cmd = [tool("ffmpeg"), "-y", "-v", "error", "-i", concat, "-i", norm_audio]
    if subs == "soft":
        cmd += ["-i", srt_path, "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0", "-c:s", "mov_text",
                "-metadata:s:s:0", f"language={lang_tag}"]
    else:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    cmd += ["-c:v", "copy", "-c:a", "copy", "-metadata:s:a:0", f"language={lang_tag}", "-movflags", "+faststart", plain]
    run(cmd)
    outputs = [plain]
    if subs == "burn":
        burned = out_dir / f"{args.slug}_{args.lang}{suffix}_subs.mp4"
        fonts_dir = rel(SHARED / "fonts")
        print("burning subtitles …", flush=True)
        run([tool("ffmpeg"), "-y", "-v", "error", "-i", rel(concat), "-i", rel(norm_audio),
             "-vf", f"ass={rel(ass_path)}:fontsdir={fonts_dir}", "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", *BT709_TAGS, "-r", str(fps),
             "-c:a", "copy", "-metadata:s:a:0", f"language={lang_tag}", "-movflags", "+faststart", rel(burned)],
            cwd=REPO)
        outputs.append(burned)
    srt_out = out_dir / f"{args.slug}_{args.lang}{suffix}.srt"
    shutil.copy2(srt_path, srt_out)

    # 6. Verify.
    print()
    print_table(["scene", "engine", "start_s", "frames", "seconds"], rows)
    print(f"\nLoudness: {loud_report}")
    print(f"Subtitles: {len(cues)} cues → {rel(srt_path)}, {rel(ass_path)} (mode: {subs})")
    problems = []
    for out in outputs:
        issues = verify(out, offset_frames, fps, W, H)
        status = "OK" if not issues else "; ".join(issues)
        print(f"  {rel(out)}  [{status}]")
        problems += issues
    print(f"  {rel(srt_out)}")
    print(f"Total: {offset_frames} frames = {offset_frames / fps:.3f}s")
    if problems:
        fail("final verification failed")


if __name__ == "__main__":
    main_wrapper(main)
