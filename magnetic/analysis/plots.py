#!/usr/bin/env python3
"""Pictures of what the analysis heard.

    plots.py song.wav analysis_dir

Writes analysis_overview.png (spectrogram, event lanes, tape speed, tape clock),
canyon_texture.png (the window's spectrogram that becomes the canyon) and
channels.png (the per-frame channels that drive the scene).
"""
import json
import sys
from pathlib import Path

import librosa
import matplotlib
import numpy as np
import soundfile as sf

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#2b2b2b"
TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e6e5e0"
TINT = "#f1efe8"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": TEXT,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False,
})


def overview(wav, A, tr, out):
    y, sr = sf.read(wav, always_2d=True)
    y = y.mean(axis=1)
    hop = 256
    C = np.abs(librosa.vqt(y, sr=sr, hop_length=hop, fmin=20, n_bins=48 * 9, bins_per_octave=48))
    D = librosa.amplitude_to_db(C, ref=np.max, top_db=80)
    t_end = len(y) / sr
    w0, w1 = A["window"]["t0"], A["window"]["t1"]

    fig, ax = plt.subplots(4, 1, figsize=(20, 13), sharex=True,
                           gridspec_kw={"height_ratios": [4.2, 2.6, 1.3, 1.3], "hspace": 0.12})
    a = ax[0]
    a.imshow(D, origin="lower", aspect="auto", cmap="magma", extent=[0, t_end, 0, D.shape[0]],
             interpolation="nearest")
    yt = [20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240]
    a.set_yticks([48 * np.log2(f / 20) for f in yt])
    a.set_yticklabels([f"{f} Hz" if f < 1000 else f"{f // 1000} kHz" if f % 1000 == 0 else f"{f / 1000:.1f} kHz" for f in yt])
    for i, b in enumerate(A["bars_s"]):
        a.axvline(b, color="white", lw=0.5, alpha=0.35)
        if b < t_end - 0.5:
            a.text(b + 0.05, D.shape[0] - 6, str(i), color="white", fontsize=8, va="top", alpha=0.8)
    for x in (w0, w1):
        a.axvline(x, color="white", lw=1.6, ls=(0, (4, 3)))
    a.text(w0 + 0.08, 14, f"13-bar window  {w0:.4f} s -> {w1:.4f} s", color="white", fontsize=10, weight="bold")
    a.set_title(f"MAGNETIC  -  {A['bpm']:.3f} bpm, root {A['root_hz']:.2f} Hz (F1), variable-Q spectrogram")

    # Event lanes: identity comes from the lane label, so every mark is one ink.
    a = ax[1]
    a.axvspan(w0, w1, color=TINT, lw=0)
    lanes = ["kicks", "snares / impacts", "stutter rolls", "dead silence", "tape glides", "falling notes",
             "gated chops", "structure"]
    yl = {n: len(lanes) - 1 - i for i, n in enumerate(lanes)}
    a.vlines(A["kicks_s"], yl["kicks"] - 0.3, yl["kicks"] + 0.3, color=INK, lw=1.0)
    a.vlines(A["snares_s"], yl["snares / impacts"] - 0.3, yl["snares / impacts"] + 0.3, color=INK, lw=1.0)
    a.plot(A["impacts_s"], [yl["snares / impacts"]] * len(A["impacts_s"]), "D", color=INK, ms=6)
    for r in A["rolls"]:
        a.add_patch(plt.Rectangle((r["t0"], yl["stutter rolls"] - 0.28), r["t1"] - r["t0"], 0.56, color=INK, lw=0))
        a.text(r["t0"], yl["stutter rolls"] + 0.38, "32nds" if r["div"] < 0.07 else "16ths", fontsize=7, color=MUTED)
    for d0, d1 in A["dead_silences_s"]:
        a.add_patch(plt.Rectangle((d0, yl["dead silence"] - 0.28), max(d1 - d0, 0.02), 0.56, color=INK, lw=0))
    for g in A["glides"]:
        a.add_patch(plt.Rectangle((g["t0"], yl["tape glides"] - 0.28), g["t1"] - g["t0"], 0.56, color=INK, lw=0))
        a.text(g["t0"], yl["tape glides"] + 0.38, g["type"], fontsize=8, color=TEXT)
    for f in A["falling_notes"]:
        a.plot([f["t0"], f["t_bottom"]], [yl["falling notes"] + 0.25, yl["falling notes"] - 0.25], color=INK, lw=1.4)
    for c0, c1 in A["chops_s"]:
        a.add_patch(plt.Rectangle((c0, yl["gated chops"] - 0.28), c1 - c0, 0.56, color=INK, lw=0))
    for e in A["events"]:
        if e["type"] in ("drop", "kick-in", "hard-cut", "breakdown"):
            a.plot([e["t"]], [yl["structure"]], "v", color=INK, ms=7)
            a.text(e["t"] + 0.06, yl["structure"] - 0.1, e["type"], fontsize=8, color=TEXT, va="center")
    a.set_yticks(list(yl.values()))
    a.set_yticklabels(list(yl.keys()))
    a.set_ylim(-0.7, len(lanes) - 0.2)
    a.tick_params(axis="y", length=0)
    for b in A["bars_s"]:
        a.axvline(b, color=GRID, lw=0.6, zorder=0)

    tracks = np.load(Path(out).parent / "tracks.npz")
    a = ax[2]
    a.axvspan(w0, w1, color=TINT, lw=0)
    a.plot(tracks["tp"], tracks["speed"], color=INK, lw=1.4)
    a.set_ylabel("tape speed (x)")
    a.set_ylim(-0.05, 1.75)
    a.set_yticks([0, 0.5, 1, 1.5])
    a.grid(axis="y", color=GRID, lw=0.6)
    for txt, yv in (("STOP", 0.0), ("PLAY", 1.0), ("FFWD", 1.5)):
        a.text(t_end - 0.05, yv + 0.04, txt, ha="right", fontsize=8, color=MUTED)

    a = ax[3]
    a.axvspan(w0, w1, color=TINT, lw=0)
    clock = np.cumsum(tracks["speed"]) / 100.0
    a.plot(tracks["tp"], tracks["tp"], color=GRID, lw=1.2)
    a.plot(tracks["tp"], clock, color=INK, lw=1.4)
    a.text(tracks["tp"][-1], tracks["tp"][-1] - 1.2, "real time", ha="right", fontsize=8, color=MUTED)
    a.text(tracks["tp"][-1], clock[-1] - 1.2, "tape clock", ha="right", fontsize=8, color=TEXT)
    a.set_ylabel("tape clock (s)")
    a.set_xlabel("song time (s)")
    a.grid(axis="y", color=GRID, lw=0.6)
    a.set_xlim(0, t_end)
    fig.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)


def canyon(A, tex, out):
    fig, a = plt.subplots(figsize=(20, 5.2))
    frames = A["frames"]
    a.imshow(tex, origin="lower", aspect="auto", cmap="magma", extent=[0, frames, 0, tex.shape[0]],
             interpolation="nearest")
    for f in (25, 50, 100, 200, 500, 1000, 2000, 5000, 10000):
        k = 28 * np.log2(f / 25.0)
        a.axhline(k, color="white", lw=0.4, alpha=0.25)
        a.text(-4, k, f"{f} Hz" if f < 1000 else f"{f // 1000} kHz", ha="right", va="center", fontsize=8, color=MUTED)
    a.set_yticks([])
    a.set_xticks(range(0, frames + 1, 48))
    a.set_xlabel("video frame (30 fps)  -  one tick per bar")
    a.set_title(f"The canyon: the window's log-frequency spectrogram ({tex.shape[0]} rows x {tex.shape[1]} columns), "
                "bass at the bottom becomes the river, harmonics become the ridges")
    fig.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)


def channels(A, ch, out):
    names = [("rms", "loudness"), ("sub", "sub 25-70 Hz"), ("kick", "kick envelope"), ("snare", "snare envelope"),
             ("centroid", "spectral centroid"), ("onset", "onset strength"), ("speed", "tape speed (x)"),
             ("tape", "tape clock (s)"), ("silent", "dead silence"), ("roll", "stutter roll"),
             ("chop", "gated chop"), ("fall", "falling note")]
    F = len(ch["t"])
    fig, ax = plt.subplots(len(names), 1, figsize=(20, 15), sharex=True, gridspec_kw={"hspace": 0.25})
    x = np.arange(F)
    for a, (k, label) in zip(ax, names):
        v = ch[k]
        if k in ("silent", "roll", "chop"):
            a.fill_between(x, 0, v, step="post", color=INK, lw=0)
        else:
            a.plot(x, v, color=INK, lw=1.1, drawstyle="steps-post" if k in ("speed",) else "default")
        a.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=9)
        a.set_yticks([])
        for b in range(0, F + 1, 48):
            a.axvline(b, color=GRID, lw=0.6, zorder=0)
        a.spines["left"].set_visible(False)
    names_at = {e["type"]: e for e in A["events"]}
    top = ax[0]
    for e in A["events"]:
        f = e.get("frame", e.get("frame0"))
        if f is None or not (0 <= f <= F):
            continue
        if e["type"] in ("roll",):
            continue
        top.annotate(e["type"], (f, 1.0), xytext=(f, 1.45), fontsize=8, color=TEXT, ha="left",
                     arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6), annotation_clip=False)
    _ = names_at
    ax[-1].set_xticks(range(0, F + 1, 48))
    ax[-1].set_xlabel("video frame (30 fps): 12 frames per beat, 48 per bar")
    ax[0].set_title("Per-frame channels for the 624-frame window (these drive the scene)", pad=34)
    fig.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)


def main():
    wav, adir = Path(sys.argv[1]), Path(sys.argv[2])
    A = json.loads((adir / "analysis.json").read_text())
    ch = dict(np.load(adir / "channels.npz"))
    tex = np.load(adir / "spectrogram_window.npy")
    overview(wav, A, None, adir / "analysis_overview.png")
    canyon(A, tex, adir / "canyon_texture.png")
    channels(A, ch, adir / "channels.png")
    print("wrote", ", ".join(p.name for p in sorted(adir.glob("*.png"))))


if __name__ == "__main__":
    main()
