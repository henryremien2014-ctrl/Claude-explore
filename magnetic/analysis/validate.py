#!/usr/bin/env python3
"""Check the blind analysis against the synth's truth log.

    validate.py analysis_dir truth.json [report.png]
"""
import json
import sys
from pathlib import Path

import numpy as np

KIND = {"stop": "tape-stop", "riser_spinup": "riser", "powerdown": "power-down", "start": "tape-start"}


def match(det, truth, tol):
    det, truth = np.asarray(det, float), np.asarray(truth, float)
    errs = [float(np.min(np.abs(det - x))) for x in truth if len(det) and np.min(np.abs(det - x)) < tol]
    fps = [round(float(x), 3) for x in det if not len(truth) or np.min(np.abs(truth - x)) >= tol]
    miss = [round(float(x), 3) for x in truth if not len(det) or np.min(np.abs(det - x)) >= tol]
    return len(errs), len(truth), fps, miss, errs


def main():
    adir, truth_path = Path(sys.argv[1]), Path(sys.argv[2])
    A = json.loads((adir / "analysis.json").read_text())
    T = json.loads(truth_path.read_text())
    tr = np.load(adir / "tracks.npz")
    lines = []
    say = lambda s: (lines.append(s), print(s))
    ok_all = True

    def check(name, cond, detail):
        nonlocal ok_all
        ok_all &= bool(cond)
        say(f"[{'ok' if cond else 'XX'}] {name}: {detail}")

    check("tempo", abs(A["bpm"] - T["bpm"]) < 0.05, f"{A['bpm']:.3f} bpm vs {T['bpm']}")
    bars = np.array(A["bars_s"])
    tb = np.arange(T["song_bars"]) * T["bar_s"]
    err = max(np.min(np.abs(bars - b)) for b in tb)
    check("bar grid", err < 0.003, f"worst bar-line error {err * 1000:.2f} ms")
    w = A["window"]
    check("window", abs(w["t0"] - T["window_s"][0]) < 0.003 and abs(w["t1"] - T["window_s"][1]) < 0.003,
          f"[{w['t0']:.4f}, {w['t1']:.4f}] vs {T['window_s']}")

    for name, det, truth, tol in (("kicks", A["kicks_s"], T["kicks"], 0.02),
                                  ("snares", A["snares_s"], T["snares"], 0.03)):
        h, n, fps, miss, errs = match(det, truth, tol)
        med = 1000 * float(np.median(errs)) if errs else float("nan")
        check(name, h == n and not fps, f"{h}/{n} found, {len(fps)} false {fps[:8]}, missed {miss[:8]}, "
                                       f"median timing error {med:.1f} ms")

    tr_rolls = [(r["t0"], r["div"]) for r in T["rolls"]]
    found = sum(any(abs(r["t0"] - t0) < 0.02 and abs(r["div"] - d) < 1e-3 for r in A["rolls"]) for t0, d in tr_rolls)
    check("stutter rolls", found == len(tr_rolls) and len(A["rolls"]) == len(tr_rolls),
          f"{found}/{len(tr_rolls)} with the right division, {len(A['rolls'])} detected")

    dead_t = [d for d in T["dead"] if d[1] - d[0] > 0.005]
    found = sum(any(abs(a - d[0]) < 0.002 and abs(b - min(d[1], A["duration_s"])) < 0.002
                    for a, b in A["dead_silences_s"]) for d in dead_t)
    check("dead silences", found == len(dead_t), f"{found}/{len(dead_t)} matched to 2 ms")

    for e in T["tape_events"]:
        # The riser's first ~0.4 s winds up from 0.12x: below what the low end can show.
        tol0 = 0.45 if e["type"] == "riser_spinup" else 0.1
        g = [g for g in A["glides"] if g["type"] == KIND[e["type"]] and abs(g["t0"] - e["t0"]) < tol0 + 0.15]
        if g:
            g = g[0]
            check(f"glide {KIND[e['type']]}", abs(g["t0"] - e["t0"]) < tol0 and abs(g["t1"] - e["t1"]) < 0.25,
                  f"{g['t0']:.2f}-{g['t1']:.2f} s vs {e['t0']:.2f}-{e['t1']:.2f} s, "
                  f"speed {g['speed_start']:.2f}->{g['speed_end']:.2f}")
        else:
            check(f"glide {KIND[e['type']]}", False, f"not found (truth {e['t0']:.2f}-{e['t1']:.2f})")
    extra = [g for g in A["glides"] if not any(KIND[e["type"]] == g["type"] and abs(g["t0"] - e["t0"]) < 0.6
                                               for e in T["tape_events"])]
    check("no phantom glides", not extra, f"{len(extra)} extra {[(g['type'], round(g['t0'], 2)) for g in extra]}")

    # Tape speed: the truth transport speed, except that the breakdown has no low end
    # and so counts as a stopped tape by definition.
    tp, speed = tr["tp"], tr["speed"]
    ts = np.interp(tp, np.arange(len(T["speed_1khz"])) / 1000.0, T["speed_1khz"])
    bd = [s for s in T["sections"] if s["name"] == "breakdown"][0]
    ts[(tp >= bd["t0"]) & (tp < bd["t1"])] = 0.0
    rz = [e for e in T["tape_events"] if e["type"] == "riser_spinup"][0]
    in_w = (tp >= T["window_s"][0]) & (tp < T["window_s"][1])
    mae = float(np.mean(np.abs(speed[in_w] - ts[in_w])))
    say(f"     tape speed MAE over the window {mae:.3f}")
    for e in T["tape_events"]:
        m = (tp >= e["t0"]) & (tp < e["t1"])
        say(f"     speed MAE in {KIND[e['type']]:10s} {np.mean(np.abs(speed[m] - ts[m])):.3f}  "
            f"(max {np.max(np.abs(speed[m] - ts[m])):.2f})")
    clock_m = float(np.sum(speed[in_w]) / 100.0)
    clock_t = float(np.sum(ts[in_w]) / 100.0)
    check("tape clock", abs(clock_m - clock_t) < 0.35, f"measured {clock_m:.2f} s of tape vs true {clock_t:.2f} s "
                                                        f"over {T['window_s'][1] - T['window_s'][0]:.1f} s")
    _ = rz

    h, n, fps, miss, _ = match([f["t0"] for f in A["falling_notes"] if 11.0 < f["t0"] < 14.0],
                               [f["t0"] for f in T["falls"]], 0.06)
    check("falling notes (breakdown)", h == n, f"{h}/{n} found, false {fps}, missed {miss}")
    live_chops = [c for c in T["chops"] if not any(d[0] - 1e-3 <= c[0] < d[1] for d in T["dead"])]
    h, n, fps, miss, _ = match([c[0] for c in A["chops_s"]], [c[0] for c in live_chops], 0.02)
    check("gated chops", h == n and not fps, f"{h}/{n} found, false {fps}, missed {miss}")
    imp_truth = [T["kick_in"]] + T["drops"]
    h, n, fps, miss, _ = match(A.get("impacts_s", []), imp_truth, 0.03)
    check("impacts", h == n and not fps, f"{h}/{n} found, false {fps}, missed {miss}")
    drops = [e["t"] for e in A["events"] if e["type"] == "drop"]
    h, n, fps, miss, _ = match(drops, T["drops"], 0.03)
    check("drops", h == n and not fps, f"{h}/{n} found, false {fps}, missed {miss}")
    say(f"     808 pitch dive measured {A['kick_dive_semitones_median']:.2f} st (synth tail dive: -5 st, "
        f"diluted by the sub underneath)")
    say("ALL OK" if ok_all else "SOME CHECKS FAILED")
    (adir / "validation.txt").write_text("\n".join(lines) + "\n")

    if len(sys.argv) > 3:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(18, 7), sharex=True)
        ax[0].plot(tp, ts, color="#b5367a", lw=2.2, label="truth (breakdown = stopped)")
        ax[0].plot(tp, speed, color="#1b1b1b", lw=1.0, label="measured")
        ax[0].plot(tp, tr["ratio"], ".", ms=1.5, color="#e8873a", label="low-end pitch / root")
        ax[0].set_ylim(-0.05, 1.8)
        ax[0].set_ylabel("tape speed")
        ax[0].legend(loc="upper left", frameon=False)
        for e in T["tape_events"]:
            ax[0].axvspan(e["t0"], e["t1"], color="#f3c58f", alpha=0.25, lw=0)
        ax[1].vlines(T["kicks"], 0.55, 1.0, color="#b5367a", lw=1.2, label="true kicks")
        ax[1].vlines(A["kicks_s"], 0.0, 0.45, color="#1b1b1b", lw=1.2, label="detected kicks")
        ax[1].set_yticks([])
        ax[1].legend(loc="upper left", frameon=False)
        for a in ax:
            a.axvline(T["window_s"][0], color="#555", ls="--", lw=0.8)
            a.axvline(T["window_s"][1], color="#555", ls="--", lw=0.8)
        ax[1].set_xlabel("song time (s)")
        plt.tight_layout()
        plt.savefig(sys.argv[3], dpi=80)


if __name__ == "__main__":
    main()
