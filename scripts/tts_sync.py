"""Narration → mp3 per scene + timings.json (durations, cue times, word times).

Usage:
  tts_sync.py --slug <slug> --lang <lang> [--scenes scene_01 scene_03] [--fit-to <source_lang>] [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import math
import re
import unicodedata

from _studio import (
    fail, load_json, locale_dir, main_wrapper, manifest, media_duration, print_table, rel,
    select_scenes, theme, voices, write_json,
)

CUE_RE = re.compile(r"\[\[([A-Za-z0-9_]+)\]\]")
FIT_TOLERANCE = 0.02  # stop retrying once within 2 % of the target
FIT_CLAMP = 15  # ± percentage points around the configured rate
MAX_FIT_RETRIES = 2
TTS_ATTEMPTS = 3


# ---------------------------------------------------------------- text

def parse_narration(text: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Strip [[cue]] markers. Returns clean text and (cue, word_index, char_pos) per marker."""
    clean_parts: list[str] = []
    cues: list[tuple[str, int, int]] = []
    pos = 0
    for m in CUE_RE.finditer(text):
        clean_parts.append(text[pos:m.start()])
        so_far = re.sub(r"\s+", " ", "".join(clean_parts)).lstrip()
        word_index = len(so_far.split())
        cues.append((m.group(1), word_index, len(so_far)))
        pos = m.end()
    clean_parts.append(text[pos:])
    clean = re.sub(r"\s+", " ", "".join(clean_parts)).strip()
    return clean, cues


def norm(token: str) -> str:
    token = unicodedata.normalize("NFKD", token.lower())
    return "".join(ch for ch in token if unicodedata.category(ch)[0] in "LN")


def align(clean: str, boundaries: list[dict]) -> dict[int, int]:
    """Map clean-text word index → boundary index by sequential token matching."""
    words = [norm(w) for w in clean.split()]
    bwords = [norm(b["text"]) for b in boundaries]
    mapping: dict[int, int] = {}
    j = 0
    for i, w in enumerate(words):
        if not w:
            continue
        for k in range(j, min(j + 4, len(bwords))):
            b = bwords[k]
            if b and (b == w or b.startswith(w) or w.startswith(b)):
                mapping[i] = k
                j = k + 1
                break
    return mapping


# ---------------------------------------------------------------- TTS

def rate_to_int(rate: str) -> int:
    m = re.fullmatch(r"([+-]?\d+)%", rate.strip())
    if not m:
        fail(f"invalid rate {rate!r}; expected e.g. '+0%' or '-10%'")
    return int(m.group(1))


def int_to_rate(value: int) -> str:
    return f"{value:+d}%"


async def _synthesize(text: str, voice: str, rate: str, pitch: str, volume: str, out_path) -> list[dict]:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume, boundary="WordBoundary")
    words: list[dict] = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".part")
    with tmp.open("wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append({"text": chunk["text"], "start": round(start, 3),
                              "end": round(start + chunk["duration"] / 1e7, 3)})
    tmp.replace(out_path)
    return words


def synthesize(text, voice, rate, pitch, volume, out_path) -> list[dict]:
    last_exc = None
    for _ in range(TTS_ATTEMPTS):
        try:
            words = asyncio.run(_synthesize(text, voice, rate, pitch, volume, out_path))
            if not words:
                fail(f"edge-tts returned no word boundary events for voice {voice}")
            return words
        except Exception as exc:  # network hiccups are common; retry
            if exc.__class__.__name__ == "StudioError":
                raise
            last_exc = exc
    fail(f"edge-tts failed for voice {voice} after {TTS_ATTEMPTS} attempts: {last_exc}")


def measure(path) -> float:
    try:
        return media_duration(path)
    except Exception:
        from mutagen.mp3 import MP3

        return float(MP3(str(path)).info.length)


# ---------------------------------------------------------------- main

def voice_settings(man: dict, lang: str, entry: dict) -> dict:
    v = voices()
    defaults = dict(v["defaults"])
    loc = man.get("locales", {}).get(lang)
    if loc is None:
        fail(f"locale {lang} is not registered in manifest.locales")
    base_voice = loc.get("voice") or v["languages"].get(lang, {}).get("default")
    if not base_voice:
        fail(f"no voice configured for {lang} in manifest or shared/voices.json")
    settings = {"voice": base_voice, **{k: loc.get(k, defaults[k]) for k in ("rate", "pitch", "volume")}}
    for k in ("voice", "rate", "pitch", "volume"):
        if entry.get(k):
            settings[k] = entry[k]
    return settings


def scene_hash(clean: str, s: dict, extra: str = "") -> str:
    key = "\n".join([clean, s["voice"], s["rate"], s["pitch"], s["volume"], extra])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def resolve_cues(scene_id, clean, markers, words, duration, expected) -> dict:
    names = [m[0] for m in markers]
    if names != expected:
        missing = [c for c in expected if c not in names]
        extra = [c for c in names if c not in expected]
        dup = sorted({c for c in names if names.count(c) > 1})
        fail(
            f"{scene_id}: cue markers {names} do not match manifest cues {expected}"
            + (f"; missing {missing}" if missing else "")
            + (f"; not in manifest {extra}" if extra else "")
            + (f"; duplicated {dup}" if dup else "")
            + ("; wrong order" if not (missing or extra or dup) else "")
        )
    mapping = align(clean, words)
    fps = theme()["fps"]
    cues = {}
    for name, word_index, char_pos in markers:
        if word_index in mapping:
            sec = words[mapping[word_index]]["start"]
        else:
            sec = duration * char_pos / max(1, len(clean))
            print(f"  WARNING {scene_id}: could not align cue '{name}'; using proportional estimate {sec:.2f}s")
        cues[name] = {"sec": round(sec, 3), "frame": round(sec * fps)}
    return cues


def build_scene(scene, entry, lang, settings, audio_path, fps, padding, extra_hash="", words=None):
    clean, markers = parse_narration(entry["text"])
    duration = measure(audio_path)
    cues = resolve_cues(scene["id"], clean, markers, words, duration, scene.get("cues", []))
    duration_frames = math.ceil(duration * fps)
    total_frames = duration_frames + padding
    return {
        "audio": f"audio/{audio_path.name}",
        "hash": scene_hash(clean, settings, extra_hash),
        "voice": settings["voice"],
        "rate": settings["rate"],
        "duration_sec": round(duration, 3),
        "duration_frames": duration_frames,
        "total_frames": total_frames,
        "total_sec": round(total_frames / fps, 4),
        "cues": cues,
        "words": words,
    }


def main():
    ap = argparse.ArgumentParser(description="Generate voiceover mp3s and timings.json for a project locale.")
    ap.add_argument("--slug", required=True, help="project slug (folder in projects/)")
    ap.add_argument("--lang", required=True, help="locale code, e.g. es-ES")
    ap.add_argument("--scenes", nargs="+", help="only these scene ids (default: all)")
    ap.add_argument("--fit-to", metavar="SOURCE_LANG",
                    help="adjust speech rate (±15%%) so each scene matches the source language duration")
    ap.add_argument("--force", action="store_true", help="regenerate even if the narration hash is unchanged")
    args = ap.parse_args()

    man = manifest(args.slug)
    th = theme()
    fps, padding = th["fps"], th["padding_frames"]
    ldir = locale_dir(args.slug, args.lang)
    narration = load_json(ldir / "narration.json")
    timings_path = ldir / "timings.json"
    old = load_json(timings_path) if timings_path.exists() else {"scenes": {}}
    source = None
    if args.fit_to:
        src_path = locale_dir(args.slug, args.fit_to) / "timings.json"
        if not src_path.exists():
            fail(f"--fit-to {args.fit_to}: {rel(src_path)} not found; run tts_sync for the source first")
        source = load_json(src_path)

    loc = man["locales"].get(args.lang) or fail(f"locale {args.lang} not in manifest.locales")
    out = {
        "lang": args.lang,
        "voice": loc.get("voice") or voices()["languages"][args.lang]["default"],
        "fps": fps,
        "padding_frames": padding,
        "scenes": dict(old.get("scenes", {})),
    }
    # Drop scenes that no longer exist in the manifest.
    out["scenes"] = {k: v for k, v in out["scenes"].items() if k in {s["id"] for s in man["scenes"]}}

    fit_rows = []
    rows = []
    for scene in select_scenes(man, args.scenes):
        sid = scene["id"]
        entry = narration.get(sid)
        if not entry or not entry.get("text"):
            fail(f"{sid}: no narration text in {rel(ldir / 'narration.json')}")
        settings = voice_settings(man, args.lang, entry)
        clean, markers = parse_narration(entry["text"])
        target = None
        extra = ""
        if source:
            if sid not in source["scenes"]:
                fail(f"--fit-to: {sid} missing in {args.fit_to} timings")
            target = source["scenes"][sid]["duration_sec"]
            extra = f"fit:{args.fit_to}:{target}"
        h = scene_hash(clean, settings, extra)
        audio_path = ldir / "audio" / f"{sid}.mp3"
        prev = out["scenes"].get(sid)
        if prev and prev.get("hash") == h and audio_path.exists() and not args.force:
            # The audio only depends on the clean text, but cue markers may have moved:
            # re-resolve cues from the stored word timings (no TTS call needed).
            prev["cues"] = resolve_cues(sid, clean, markers, prev["words"], prev["duration_sec"],
                                        scene.get("cues", []))
            rows.append([sid, "cached", prev["voice"], prev.get("rate", settings["rate"]),
                         f"{prev['duration_sec']:.2f}", prev["total_frames"], len(prev["cues"])])
            continue
        # Validate cues before spending a TTS call.
        names = [m[0] for m in markers]
        if names != scene.get("cues", []):
            resolve_cues(sid, clean, markers, [], 0, scene.get("cues", []))

        words = synthesize(clean, settings["voice"], settings["rate"], settings["pitch"], settings["volume"], audio_path)
        if target:
            base_rate = rate_to_int(settings["rate"])
            rate = base_rate
            achieved = measure(audio_path)
            for _ in range(MAX_FIT_RETRIES):
                if abs(achieved - target) / target <= FIT_TOLERANCE:
                    break
                speed = (1 + rate / 100) * achieved / target
                new_rate = max(base_rate - FIT_CLAMP, min(base_rate + FIT_CLAMP, round((speed - 1) * 100)))
                if new_rate == rate:
                    break
                rate = new_rate
                words = synthesize(clean, settings["voice"], int_to_rate(rate), settings["pitch"],
                                   settings["volume"], audio_path)
                achieved = measure(audio_path)
            fitted = abs(achieved - target) / target <= FIT_TOLERANCE * 2.5
            fit_rows.append([sid, f"{target:.2f}", f"{achieved:.2f}", int_to_rate(rate),
                             "ok" if fitted else "NOT FITTED"])
            settings = {**settings, "rate": int_to_rate(rate)}
        data = build_scene(scene, entry, args.lang, settings, audio_path, fps, padding, extra, words)
        data["hash"] = h
        out["scenes"][sid] = data
        rows.append([sid, "generated", data["voice"], data["rate"], f"{data['duration_sec']:.2f}",
                     data["total_frames"], len(data["cues"])])

    # Keep scenes in manifest order.
    order = [s["id"] for s in man["scenes"]]
    out["scenes"] = {k: out["scenes"][k] for k in order if k in out["scenes"]}
    write_json(timings_path, out)

    print_table(["scene", "status", "voice", "rate", "duration_s", "total_frames", "cues"], rows)
    if fit_rows:
        print()
        print_table(["scene", "target_s", "achieved_s", "rate", "fit"], fit_rows)
    total = sum(s["total_frames"] for s in out["scenes"].values()) / fps
    print(f"\nWrote {rel(timings_path)} (total {total:.2f}s)")


if __name__ == "__main__":
    main_wrapper(main)
