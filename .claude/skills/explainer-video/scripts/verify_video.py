#!/usr/bin/env python3
"""Check a rendered video against the numbers a "Done means" line asks for.

Examples:
  verify_video.py out/video.mp4 --width 1920 --height 1080 --duration 20
  verify_video.py out/video.mp4 --width 1080 --height 1080 --duration 30 --audio required
  verify_video.py edited.mp4 --audio required --min-duration 5

Prints the file's facts as JSON, then one PASS/FAIL/WARN line per check.
Exits 1 if any check fails. Needs ffprobe on PATH.
"""
import argparse
import json
import subprocess
import sys
from fractions import Fraction


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"ffprobe failed on {path}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--duration", type=float, help="expected duration in seconds")
    ap.add_argument("--tolerance", type=float, default=0.1, help="allowed duration error in seconds (default 0.1)")
    ap.add_argument("--min-duration", type=float)
    ap.add_argument("--max-duration", type=float)
    ap.add_argument("--fps", type=float)
    ap.add_argument("--audio", choices=["required", "none", "any"], default="any")
    a = ap.parse_args()

    info = probe(a.video)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    aud = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    if v is None:
        sys.exit("No video stream found.")
    fps = float(Fraction(v.get("avg_frame_rate") or v.get("r_frame_rate", "0/1")))
    facts = {
        "file": a.video,
        "codec": v.get("codec_name"),
        "profile": v.get("profile"),
        "pix_fmt": v.get("pix_fmt"),
        "width": v.get("width"),
        "height": v.get("height"),
        "fps": round(fps, 3),
        "frames": int(v.get("nb_read_frames") or v.get("nb_frames") or 0),
        "duration_s": round(float(info["format"].get("duration", 0)), 3),
        "size_mb": round(int(info["format"].get("size", 0)) / 1e6, 2),
        "audio_streams": [
            {"codec": s.get("codec_name"), "sample_rate": s.get("sample_rate"), "channels": s.get("channels"),
             "duration_s": round(float(s.get("duration", 0) or 0), 3)}
            for s in aud
        ],
    }
    print(json.dumps(facts, indent=2))

    results = []

    def check(name, ok, detail, level="FAIL"):
        results.append(("PASS" if ok else level, name, detail))

    if a.width is not None:
        check("width", facts["width"] == a.width, f'{facts["width"]} (want {a.width})')
    if a.height is not None:
        check("height", facts["height"] == a.height, f'{facts["height"]} (want {a.height})')
    if a.duration is not None:
        d = facts["duration_s"]
        check("duration", abs(d - a.duration) <= a.tolerance, f"{d} s (want {a.duration} ± {a.tolerance})")
    if a.min_duration is not None:
        check("min duration", facts["duration_s"] >= a.min_duration, f'{facts["duration_s"]} s (want ≥ {a.min_duration})')
    if a.max_duration is not None:
        check("max duration", facts["duration_s"] <= a.max_duration, f'{facts["duration_s"]} s (want ≤ {a.max_duration})')
    if a.fps is not None:
        check("fps", abs(fps - a.fps) < 0.01, f"{facts['fps']} (want {a.fps})")
    if a.audio == "required":
        check("audio", bool(aud), f"{len(aud)} audio stream(s)")
    elif a.audio == "none":
        check("no audio", not aud, f"{len(aud)} audio stream(s)")
    check("codec h264", facts["codec"] == "h264", f'{facts["codec"]} (h264 plays everywhere)', level="WARN")
    check("pixel format", facts["pix_fmt"] == "yuv420p", f'{facts["pix_fmt"]} (yuv420p plays everywhere)', level="WARN")
    check("frame count", facts["frames"] > 0, f'{facts["frames"]} decoded frames')

    for status, name, detail in results:
        print(f"{status:4}  {name}: {detail}")
    sys.exit(1 if any(r[0] == "FAIL" for r in results) else 0)


if __name__ == "__main__":
    main()
