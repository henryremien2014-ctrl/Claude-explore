#!/usr/bin/env python3
"""Encode post frames + the untouched window audio.

    encode.py frames_dir out.mp4 [--preview]

Final: 1920x1080, 30 fps, H.264 High, 20 Mb/s average capped at 25 Mb/s, AAC 320k.
Preview: whatever size the frames are, CRF 23, AAC 192k.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "analysis" / "out" / "window.wav"


def main():
    frames, out = Path(sys.argv[1]), Path(sys.argv[2])
    preview = "--preview" in sys.argv
    # swscale converts RGB with BT.601 coefficients unless told otherwise; the stream is tagged BT.709,
    # so convert with BT.709 too or every player shifts the colours
    video = ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
             "-c:v", "libx264", "-profile:v", "high", "-movflags", "+faststart"]
    if preview:
        video += ["-preset", "medium", "-crf", "23"]
        audio = ["-c:a", "aac", "-b:a", "192k"]
    else:
        video += ["-preset", "slow", "-b:v", "20M", "-maxrate", "25M", "-bufsize", "50M", "-x264-params", "nal-hrd=vbr"]
        audio = ["-c:a", "aac", "-b:a", "320k"]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", "30", "-i", str(frames / "p%04d.png"),
           "-i", str(AUDIO), "-map", "0:v", "-map", "1:a", *video, *audio, "-ar", "48000",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-shortest", str(out)]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main()
