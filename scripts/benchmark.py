"""Time the full pipeline of an existing video with different --jobs values.

Each run starts from scratch: it deletes what the pipeline generated for that video and language
(voiceover audio, timings.json, renders, QA frames, subtitles and final videos; never the manifest,
narration, strings or scene code), then runs and times every step:
tts_sync.py → render.py --preview → qa_frames.py → render.py → stitch.py.
At the end it compares every run's final video with the first one, frame by frame (SSIM).

The default order 1 4 4 1 runs each setting twice, once early and once late, so a machine that
slows down as it heats up does not favour either setting. Results go to projects/<slug>/benchmark/.

Usage:
  benchmark.py [--slug monte_carlo_pi] [--lang <lang>] [--jobs 1 4 4 1] [--subs burn|soft|none] [--yes]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from _studio import REPO, fail, main_wrapper, manifest, print_table, rel, tool

STEPS = ["voice", "render_preview", "qa", "render_final", "stitch"]


def generated_paths(project: Path, slug: str, lang: str) -> list[Path]:
    """Everything the pipeline generates for one video and language, i.e. what a run deletes."""
    paths = [project / "locales" / lang / "audio", project / "locales" / lang / "timings.json",
             project / "renders" / lang, project / "qa" / lang,
             project / "subtitles" / f"{lang}.srt", project / "subtitles" / f"{lang}.ass"]
    output = project / "output"
    if output.is_dir():
        paths += sorted(p for p in output.iterdir() if p.name.startswith(f"{slug}_{lang}.")
                        or p.name.startswith(f"{slug}_{lang}_"))
    return paths


def delete(paths: list[Path]) -> None:
    for p in paths:
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


def commands(slug: str, lang: str, jobs: int, subs: str) -> list[tuple[str, list[str]]]:
    base = ["--slug", slug, "--lang", lang]
    return [
        ("voice", ["tts_sync.py", *base]),
        ("render_preview", ["render.py", *base, "--preview", "--jobs", str(jobs)]),
        ("qa", ["qa_frames.py", *base, "--preview", "--at-cues"]),
        ("render_final", ["render.py", *base, "--jobs", str(jobs)]),
        ("stitch", ["stitch.py", *base, "--subs", subs]),
    ]


def ssim(a: Path, b: Path) -> float:
    proc = subprocess.run([tool("ffmpeg"), "-i", str(a), "-i", str(b), "-lavfi", "[0:v][1:v]ssim", "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"All:([0-9.]+)", proc.stderr)
    if not match:
        fail(f"could not compare {rel(a)} with {rel(b)}")
    return float(match.group(1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", default="monte_carlo_pi", help="existing video to time (default: %(default)s)")
    ap.add_argument("--lang", help="language to time (default: the video's source language)")
    ap.add_argument("--jobs", type=int, nargs="+", default=[1, 4, 4, 1], help="one run per value (default: 1 4 4 1)")
    ap.add_argument("--subs", choices=["burn", "soft", "none"], default="burn", help="subtitles for stitch.py")
    ap.add_argument("--yes", action="store_true", help="delete the generated files without asking")
    args = ap.parse_args()

    project = REPO / "projects" / args.slug
    if not (project / "manifest.json").exists():
        available = sorted(p.name for p in (REPO / "projects").iterdir() if (p / "manifest.json").exists())
        fail(f"project not found: {rel(project)}. Available: {', '.join(available)}")
    lang = args.lang or manifest(args.slug)["source_lang"]
    if not (project / "locales" / lang / "narration.json").exists():
        fail(f"{rel(project / 'locales' / lang / 'narration.json')} not found")
    if any(j < 1 for j in args.jobs):
        fail("--jobs values must be at least 1")

    print(f"Each of the {len(args.jobs)} runs first deletes what the pipeline generated for {args.slug} ({lang}):")
    for p in generated_paths(project, args.slug, lang):
        print(f"  {rel(p)}{'/' if p.suffix == '' else ''}")
    if not args.yes:
        if not sys.stdin.isatty():
            fail("not running in a terminal: pass --yes to confirm the deletion")
        try:
            answer = input("Continue? [y/N] ")
        except EOFError:  # e.g. stdin is NUL on Windows, which isatty() reports as a terminal
            fail("no answer to the confirmation: pass --yes to confirm the deletion")
        if answer.strip().lower() not in ("y", "yes"):
            print("Nothing was changed.")
            return

    out_dir = project / "benchmark"
    out_dir.mkdir(exist_ok=True)
    runs = []
    for i, jobs in enumerate(args.jobs, 1):
        delete(generated_paths(project, args.slug, lang))
        print(f"\nRun {i}/{len(args.jobs)}: --jobs {jobs}", flush=True)
        times = {}
        log_path = out_dir / f"run{i}_jobs{jobs}.log"
        with log_path.open("w", encoding="utf-8") as log:
            for step, cmd in commands(args.slug, lang, jobs, args.subs):
                started = time.perf_counter()
                proc = subprocess.run([sys.executable, str(REPO / "scripts" / cmd[0]), *cmd[1:]], cwd=REPO,
                                      capture_output=True, text=True, encoding="utf-8", errors="replace")
                seconds = time.perf_counter() - started
                log.write(f"===== {step} ({seconds:.1f}s, exit {proc.returncode})\n{proc.stdout}\n{proc.stderr}\n")
                if proc.returncode != 0:
                    fail(f"run {i}, step {step} failed; see {rel(log_path)}")
                times[step] = round(seconds, 2)
                print(f"  {step:15s} {seconds:7.1f}s", flush=True)
        final = project / "output" / f"{args.slug}_{lang}{'_subs' if args.subs == 'burn' else ''}.mp4"
        kept = out_dir / f"run{i}_jobs{jobs}.mp4"
        shutil.copy2(final, kept)
        runs.append({"run": i, "jobs": jobs, "steps": times, "total": round(sum(times.values()), 2), "video": kept.name})

    for run in runs[1:]:
        run["ssim_vs_run1"] = ssim(out_dir / run["video"], out_dir / runs[0]["video"])

    # Average per --jobs value, in the order the values first appear.
    settings = list(dict.fromkeys(args.jobs))
    avg = {j: {s: sum(r["steps"][s] for r in runs if r["jobs"] == j) / args.jobs.count(j) for s in STEPS}
           for j in settings}
    rows = []
    for step in STEPS + ["total"]:
        values = [sum(avg[j].values()) if step == "total" else avg[j][step] for j in settings]
        rows.append([step] + [f"{v:.1f}s" for v in values] + [f"{values[0] / v:.2f}x" for v in values[1:]])
    print()
    print_table(["step"] + [f"--jobs {j}" for j in settings] + [f"speed-up {j}" for j in settings[1:]], rows)
    if len(runs) > 1:
        worst = min(r["ssim_vs_run1"] for r in runs[1:])
        print(f"\nSame video as run 1, frame by frame: {'yes' if worst == 1.0 else 'NO'} (lowest SSIM {worst:.6f})")
    (out_dir / "results.json").write_text(json.dumps({"slug": args.slug, "lang": lang, "runs": runs}, indent=2) + "\n",
                                          encoding="utf-8")
    print(f"Results: {rel(out_dir / 'results.json')}")


if __name__ == "__main__":
    main_wrapper(main)
