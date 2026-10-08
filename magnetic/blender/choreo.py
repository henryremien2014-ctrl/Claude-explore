#!/usr/bin/env python3
"""Choreography: the analysis becomes per-frame animation channels, a shot list and a frame
plan for the post pipeline. Pure numpy; build.py bakes the result onto the scene.

Every timing comes from a measured event (analysis.json), never from a typed frame number:
cuts land on the measured beat grid, the blink rides the second intro roll, the eye opens on
the measured drops, the frame rate decelerates with the measured tape speed.

Rules:
  * Physical state (spike height, the kick wave, where the hero looks, droplet flight) runs on
    the tape clock: when the tape stops, the world stops.
  * Anything cyclic is a function of the loop phase = tape clock / total tape, so it is exactly
    periodic: one full field rotation per loop, noise on circular paths, integer ring turns.
  * Over the last 0.8 s every audio-driven channel blends to the value it has just before
    frame 0, and the camera lands on frame 0's framing, lens and focus.

    choreo.py   ->  analysis/out/choreo.npz, shots.json, frameplan.json
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AOUT = ROOT / "analysis" / "out"
FPS = 30
HERO_C = np.array([0.0, 0.0, 1.75])
EYE_C = 0.80


# ----------------------------------------------------------------------------- small maths

def smoothstep(e0, e1, x):
    u = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return u * u * (3 - 2 * u)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def rot_z(deg_):
    a = math.radians(deg_)
    return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1.0]])


def quat_look(fwd, up=(0, 0, 1.0), axis="Y"):
    """Quaternion (w, x, y, z) turning the local axis ('Y' or '-Z') onto fwd, keeping up."""
    f = unit(fwd)
    u = np.asarray(up, float)
    if abs(np.dot(f, u)) > 0.999:
        u = np.array([0.0, 1.0, 0.0])
    r = unit(np.cross(f, u))
    u2 = np.cross(r, f)
    if axis == "Y":                       # local +Y = forward, local +Z = up, local +X = right
        M = np.stack([r, f, u2], 1)
    else:                                 # camera: local -Z = forward, +Y = up, +X = right
        M = np.stack([r, u2, -f], 1)
    return mat_to_quat(M)


def mat_to_quat(M):
    t = np.trace(M)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (M[2, 1] - M[1, 2]) / s, (M[0, 2] - M[2, 0]) / s, (M[1, 0] - M[0, 1]) / s]
    elif M[0, 0] > M[1, 1] and M[0, 0] > M[2, 2]:
        s = math.sqrt(1.0 + M[0, 0] - M[1, 1] - M[2, 2]) * 2
        q = [(M[2, 1] - M[1, 2]) / s, 0.25 * s, (M[0, 1] + M[1, 0]) / s, (M[0, 2] + M[2, 0]) / s]
    elif M[1, 1] > M[2, 2]:
        s = math.sqrt(1.0 + M[1, 1] - M[0, 0] - M[2, 2]) * 2
        q = [(M[0, 2] - M[2, 0]) / s, (M[0, 1] + M[1, 0]) / s, 0.25 * s, (M[1, 2] + M[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + M[2, 2] - M[0, 0] - M[1, 1]) * 2
        q = [(M[1, 0] - M[0, 1]) / s, (M[0, 2] + M[2, 0]) / s, (M[1, 2] + M[2, 1]) / s, 0.25 * s]
    q = np.array(q)
    return q / np.linalg.norm(q)


def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def quat_inv(q):
    return np.array([q[0], -q[1], -q[2], -q[3]]) / np.dot(q, q)


def quat_rot(q, v):
    p = np.concatenate([[0.0], v])
    return quat_mul(quat_mul(q, p), quat_inv(q))[1:]


def slerp(a, b, t):
    d = np.dot(a, b)
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        q = a + t * (b - a)
        return q / np.linalg.norm(q)
    th = math.acos(d)
    return (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th)


def quat_axis_angle(axis, ang):
    axis = unit(axis)
    return np.concatenate([[math.cos(ang / 2)], axis * math.sin(ang / 2)])


def hermite(p0, p1, v0, v1, u):
    """Cubic Hermite between p0 and p1 with end velocities v0, v1 (per unit u)."""
    u = np.asarray(u, float)[..., None] if np.ndim(p0) else np.asarray(u, float)
    h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    return h00 * p0 + h10 * v0 + h01 * p1 + h11 * v1


# ----------------------------------------------------------------------------- main

def main():
    A = json.loads((AOUT / "analysis.json").read_text())
    ch = dict(np.load(AOUT / "channels.npz"))
    F = A["frames"]
    f = np.arange(F)
    beat_frames = int(round(A["beat_s"] * FPS))                       # 12

    ev = {}
    for e in A["events"]:
        ev.setdefault(e["type"], []).append(e)
    rolls = sorted(ev.get("roll", []), key=lambda e: e["frame0"])
    drops = sorted(e["frame"] for e in ev["drop"])
    stop = ev["tape-stop"][0]
    riser = ev["riser"][0]
    pdown = ev["power-down"][0]
    tstart = ev["tape-start"][0]
    silent = ch["silent"] > 0.5
    dead_runs = []
    for a in range(F):
        if silent[a] and (a == 0 or not silent[a - 1]):
            b = a
            while b < F and silent[b]:
                b += 1
            dead_runs.append((a, b))
    kick_frames = np.nonzero(ch["kick_hit"])[0]
    speed = ch["speed"].copy()
    tape = ch["tape"].copy()
    tape_total = tape[-1] + speed[-1] / FPS
    phase = tape / tape_total                                           # 0 .. 1, periodic
    dtau = speed / FPS                                                  # world seconds per frame

    def snap_beat(fr):
        return int(round(fr / beat_frames) * beat_frames)

    # ----------------------------------------------------------------- structure (all measured)
    blink_f = rolls[1]["frame0"] if len(rolls) > 1 else snap_beat(72)  # the eye blinks on the 2nd intro roll
    cev_f = snap_beat(rolls[2]["frame0"]) if len(rolls) > 2 else blink_f + beat_frames
    kickin_f = ev["kick-in"][0]["frame"]
    stop_f0, stop_f1 = stop["frame0"], stop["frame1"]
    riser_f0 = snap_beat(riser["frame0"] - beat_frames / 2)             # the riser shot starts on its bar
    drop1, drop2 = drops[0], drops[1]
    pd_f0, pd_f1 = pdown["frame0"], pdown["frame1"]
    ts_f0 = tstart["frame0"]
    dive_f0 = F - int(round(0.8 * FPS))                                 # the last 0.8 s

    # ----------------------------------------------------------------- shot list (cuts on beats)
    cuts = [0, cev_f, kickin_f, kickin_f + 4 * beat_frames, stop_f0 - 2 * beat_frames, stop_f0, riser_f0, drop1,
            drop1 + 4 * beat_frames, drop1 + 6 * beat_frames, pd_f0, drop2, drop2 + 4 * beat_frames, ts_f0, dive_f0]
    names = ["stare", "cev", "reveal", "orbit", "low", "bullet", "vertigo", "open", "drop_a", "drop_b", "melt",
             "slam", "close", "kaleido", "dive"]
    assert all(c % beat_frames == 0 for c in cuts), cuts
    assert cuts == sorted(cuts), cuts
    shot_of = np.zeros(F, int)
    for i, c in enumerate(cuts):
        shot_of[c:] = i
    shots = [{"name": n, "f0": c, "f1": (cuts[i + 1] if i + 1 < len(cuts) else F)} for i, (n, c) in enumerate(zip(names, cuts))]

    # ----------------------------------------------------------------- cameras
    cam_loc = np.zeros((F, 3))
    cam_tgt = np.zeros((F, 3))
    lens = np.zeros(F)
    focus = np.zeros(F)
    fstop = np.zeros(F)
    yaw_stare = 20.0
    eye_dir_stare = unit(rot_z(-yaw_stare) @ np.array([0.0, 1.0, 0.06]))
    E_stare = HERO_C + eye_dir_stare * EYE_C
    D0, D1 = 2.30, 1.98                                                 # stare push-in, frame 0 -> blink cut
    stare_v = (D1 - D0) / cuts[1]                                       # metres per frame along the axis

    def stare_cam(fr):
        d = D0 + stare_v * fr
        return E_stare + eye_dir_stare * d + np.array([0, 0, 0.015]), E_stare, 85.0, d - 0.30, 2.0

    def orbit(az, dist, h, tgt=HERO_C):
        a = math.radians(az)
        return tgt + np.array([dist * math.cos(a), dist * math.sin(a), h])

    for i, s in enumerate(shots):
        a, b = s["f0"], s["f1"]
        u = (f[a:b] - a) / max(b - a - 1, 1)
        n = s["name"]
        for k, fr in enumerate(range(a, b)):
            uu = u[k]
            if n == "stare":
                L, T, ln, fd, fs = stare_cam(fr)
            elif n == "cev":
                ang = math.radians(15 * uu)
                L = np.array([0.0, 0.0, 26.0])
                T = np.array([0.001 * math.cos(ang), 0.001 * math.sin(ang), 0.0])
                ln, fd, fs = 30.0, 26.0, 16.0
            elif n == "reveal":
                L = np.array([-9.6 + 2.2 * uu, 0.85 - 0.2 * uu, 1.05 + 0.25 * uu])
                T = HERO_C + np.array([0.0, 0.0, 0.10])
                ln, fd, fs = 24.0, np.linalg.norm(L - HERO_C), 4.0
            elif n == "orbit":
                L = orbit(205 + 55 * uu, 4.4, 0.65)
                T = HERO_C
                ln, fd, fs = 35.0, 4.2, 2.8
            elif n == "low":
                L = np.array([1.9 - 0.2 * uu, 2.25 - 0.15 * uu, 0.02 + 0.05 * uu])
                T = HERO_C + np.array([0.0, 0.0, 0.35])
                ln, fd, fs = 20.0, 2.6, 4.0
            elif n == "bullet":
                L = orbit(60 + 140 * smoothstep(0, 1, uu) * 0.85 + 140 * uu * 0.15, 4.3, 0.2 + 0.6 * uu)
                T = HERO_C
                ln, fd, fs = 40.0, 3.6, 3.2
            elif n == "vertigo":
                d = 15.0 - 11.8 * uu ** 2.2
                L = HERO_C + np.array([-d, 0.35, 0.10 + 0.012 * d])
                T = HERO_C
                ln, fd, fs = 100.0 * d / 15.0, d - 0.9, 5.6
            elif n == "open":
                L = orbit(70, 2.95 - 0.3 * uu, 0.12)
                T = HERO_C + np.array([0.0, 0.0, 0.04])
                ln, fd, fs = 50.0, 2.95 - 0.3 * uu - 0.95, 2.4
            elif n == "drop_a":
                L = np.array([4.4 - 1.7 * uu, 1.25 + 0.45 * uu, 0.30 + 0.22 * uu])   # low in the river channel
                T = HERO_C + np.array([0.0, 0.0, 0.1])
                ln, fd, fs = 24.0, 4.0, 4.0
            elif n == "drop_b":
                L = orbit(-55 + 15 * uu, 2.9, -0.1)
                T = HERO_C
                ln, fd, fs = 35.0, 2.1, 2.8
            elif n == "melt":
                L = orbit(98, 4.2 - 0.3 * uu, 0.55)
                T = HERO_C + np.array([0.0, 0.0, -0.1])
                ln, fd, fs = 45.0, 3.5, 3.2
            elif n == "slam":
                L = HERO_C + np.array([3.2, 3.6, 3.4 - 0.6 * uu])
                T = HERO_C
                ln, fd, fs = 28.0, 5.4, 4.0
            elif n == "close":
                L = orbit(75 + 6 * uu, 2.6, 0.1)
                T = HERO_C + np.array([0.0, 0.0, 0.02])
                ln, fd, fs = 65.0, 1.85, 2.2
            elif n == "kaleido":
                L = E_stare + eye_dir_stare * (5.6 - 0.15 * uu) + np.array([0.0, 0.0, 0.7])   # clear of the walls
                T = E_stare
                ln, fd, fs = 35.0, 5.3, 5.6
            else:                                                       # dive: lands on frame -1 of the stare
                continue
            cam_loc[fr], cam_tgt[fr], lens[fr], focus[fr], fstop[fr] = L, T, ln, fd, fs

    # The dive: Hermite from the kaleido framing into the stare's frame -1, matching its push velocity.
    a, b = cuts[-1], F
    n_d = b - a
    Ls, Ts, lns, fds, fss = cam_loc[a - 1], cam_tgt[a - 1], lens[a - 1], focus[a - 1], fstop[a - 1]
    Le, Te, lne, fde, fse = stare_cam(-1)
    v_end = eye_dir_stare * stare_v * n_d                                # per unit u
    v_start = (cam_loc[a - 1] - cam_loc[a - 2]) * n_d
    for k, fr in enumerate(range(a, b)):
        uu = (k + 1) / n_d                                               # u = 1 at frame -1 of the loop
        cam_loc[fr] = hermite(Ls, Le, v_start, v_end, uu)
        cam_tgt[fr] = Te
        e = 1 - (1 - uu) ** 3
        lens[fr] = lns + (lne - lns) * e
        focus[fr] = np.linalg.norm(cam_loc[fr] - Te) - 0.30
        fstop[fr] = fss + (fse - fss) * e

    # ----------------------------------------------------------------- eye open / blink / melt
    eye_open = np.ones(F)
    eye_open[blink_f:] = 0.0
    eye_open[blink_f:blink_f + 4] = 1.0 - smoothstep(0, 1, (np.arange(4) + 1) / 4)
    for d_f in (drop1, drop2):
        k = np.arange(F - d_f)
        snap = np.clip(1.0 + 0.16 * np.exp(-k / 3.0) * np.sin(k * 0.9) - np.exp(-k / 1.2), 0, 1.2)
        eye_open[d_f:] = snap
    pd = (f >= pd_f0) & (f < pd_f1)
    eye_open[pd] = np.clip(speed[pd], 0, 1) ** 0.7                      # lids droop as the power dies
    eye_open[(f >= pd_f1) & (f < drop2)] = 0.0
    melt = np.zeros(F)
    melt[pd] = (1.0 - np.clip(speed[pd], 0, 1)) ** 0.8
    melt[(f >= pd_f1) & (f < drop2)] = 1.0
    k = np.arange(F - drop2)
    melt[drop2:] = np.exp(-k / 2.0) * (k < 12)                           # the field slams back on

    # ----------------------------------------------------------------- spikes, kick wave (world time)
    sub = ch["sub"]
    target_h = 0.06 + 0.24 * sub + 0.05 * ch["rms"]
    h = np.zeros(F)
    state = target_h[0]
    for _ in range(2):                                                   # run twice: periodic steady state
        for i in range(F):
            k_att = 1 - math.exp(-dtau[i] / 0.05)
            k_rel = 1 - math.exp(-dtau[i] / 0.35)
            kk = k_att if target_h[i] > state else k_rel
            state += (target_h[i] - state) * kk
            h[i] = state
    punch = np.zeros(F)
    punch_age = np.full(F, 5.0)
    age, amp = 5.0, 0.0
    for _ in range(2):
        for i in range(F):
            if ch["kick_hit"][i]:
                age, amp = 0.0, 1.0
            else:
                age += dtau[i]
            punch[i] = amp * math.exp(-age / 0.35)
            punch_age[i] = age
    tremor = 0.25 + 0.75 * ch["high"]

    pupil = 0.30 + 0.20 * ch["kick"]
    for d_f in (drop1, drop2):
        k = np.arange(F - d_f)
        pupil[d_f:] += 0.22 * np.exp(-k / 9.0)                           # opening wide, then constricting
    iris_glow = 0.8 + 0.7 * ch["kick"] + 0.3 * ch["mid"]

    # saccades: a new small offset on every beat, periodic over the loop
    rng = np.random.default_rng(3)
    nbeats = F // beat_frames
    offs = np.vstack([rng.normal(0, [2.0, 1.2], (nbeats, 2))])
    sac = np.zeros((F, 2))
    for i in range(F):
        bi = (i // beat_frames) % nbeats
        prev = offs[(bi - 1) % nbeats]
        tt = min((i % beat_frames) / 2.0, 1.0)                           # a 2-frame jump, then hold
        sac[i] = prev + (offs[bi] - prev) * (tt * tt * (3 - 2 * tt))

    # ----------------------------------------------------------------- hero facing (world time) and gaze
    face_q = np.zeros((F, 4))
    eye_q = np.zeros((F, 4))
    offsets = {"stare": 0, "cev": 0, "reveal": 0, "orbit": 25, "low": -20, "bullet": 0, "vertigo": 0, "open": 6,
               "drop_a": 14, "drop_b": -12, "melt": 10, "slam": 16, "close": 4, "kaleido": 0, "dive": 0}
    q = None
    for i in range(F):
        s = shots[shot_of[i]]
        want_dir = cam_loc[i] - HERO_C
        want_dir = rot_z(offsets[s["name"]]) @ want_dir
        if s["name"] in ("stare", "kaleido", "dive"):
            want_dir = eye_dir_stare
        want = quat_look(want_dir)
        if q is None or (i == s["f0"] and (speed[i] > 0.1 or eye_open[i] > 0.5)):
            q = want                                                     # cut: snap to the new camera
        else:
            q = slerp(q, want, 1 - math.exp(-dtau[i] / 0.25))            # follow in world time
        if s["name"] in ("stare", "kaleido", "dive"):
            q = want
        face_q[i] = q
        eye_world = HERO_C + quat_rot(q, np.array([0.0, EYE_C, 0.0]))
        gaze = cam_loc[i] - eye_world
        gq = quat_look(gaze)
        sq = quat_mul(quat_axis_angle([0, 0, 1], math.radians(sac[i, 0])), quat_axis_angle([1, 0, 0], math.radians(sac[i, 1])))
        eye_q[i] = quat_mul(quat_inv(q), quat_mul(gq, sq))
    gravity = np.array([quat_rot(quat_inv(face_q[i]), np.array([0.0, 0.0, -1.0])) for i in range(F)])

    # ----------------------------------------------------------------- droplets (bullet time)
    drop_tau = np.zeros(F)
    drop_on = np.zeros(F)
    recall = np.zeros(F)
    acc = 0.0
    for i in range(stop_f0, F):
        drop_tau[i] = acc
        acc += dtau[i]
    drop_on[stop_f0:drop1 + 8] = 1.0
    recall[drop1:] = smoothstep(0, 1, (np.arange(F - drop1) + 1) / 7.0)

    # ----------------------------------------------------------------- halo, mandala, sequencer, dust, haze
    halo_glow = 0.45 + 1.0 * ch["kick"] + 0.5 * ch["snare"]
    mandala = np.zeros((F, 7))
    for k in range(7):
        a0 = drop1 + 3 * k
        mandala[:, k] = smoothstep(a0, a0 + 14, f)
        mandala[(f >= pd_f0), k] = 1.0
        a1 = drop2 + 2 * k
        mandala[f >= drop2, k] = smoothstep(a1, a1 + 8, f[f >= drop2])
    mandala_glow = np.zeros(F)
    mandala_glow[f >= drop1] = 0.7 + 0.8 * ch["kick"][f >= drop1]
    mandala_glow[pd] *= np.clip(speed[pd], 0, 1)
    mandala_glow[(f >= pd_f1) & (f < drop2)] = 0.0
    mandala[(f >= pd_f1) & (f < drop2)] = 0.0
    # 16ths on the tape clock, rounded to a whole number of 16-step cycles per loop: periodic.
    steps_per_loop = 16 * max(1, int(round(tape_total / (A["beat_s"] / 4) / 16)))
    seq_step = np.floor(phase * steps_per_loop).astype(int) % 16
    seq = np.zeros((F, 16))
    for i in range(F):
        for back, lvl in enumerate((1.0, 0.45, 0.2, 0.08)):
            seq[i, (seq_step[i] - back) % 16] = lvl * (0.25 + 0.75 * ch["rms"][i])
    seq[silent] = 0.0
    dust_glow = np.full(F, 0.45)
    dust_glow[:kickin_f] = 1.3 + 0.6 * ch["high"][:kickin_f]
    dust_glow[stop_f0:riser_f0] = 0.9
    dust_glow += 0.4 * ch["kick"]
    haze = np.ones(F)
    haze[:kickin_f] = 1.25
    haze[stop_f0:riser_f0] = 1.35

    # ----------------------------------------------------------------- the seam: blend into frame -1
    w = smoothstep(dive_f0, F - 1, f)

    def seam(x):
        x = np.asarray(x, float)
        prev = x[0] - (x[1] - x[0])                                       # the value just before frame 0
        tgt = prev + (f - (F - 1))[:, None] * (x[1] - x[0]) if x.ndim > 1 else prev + (f - (F - 1)) * (x[1] - x[0])
        ww = w[:, None] if x.ndim > 1 else w
        return x * (1 - ww) + tgt * ww

    h, punch, pupil, iris_glow, tremor = (seam(v) for v in (h, punch, pupil, iris_glow, tremor))
    halo_glow, dust_glow, haze, mandala_glow = (seam(v) for v in (halo_glow, dust_glow, haze, mandala_glow))
    mandala = seam(mandala)
    seq = seam(seq)
    eye_open = seam(eye_open)
    kick_seam, snare_seam, sub_seam = seam(ch["kick"]), seam(ch["snare"]), seam(sub)
    punch_age = punch_age * (1 - w) + punch_age[0] * w

    d_open = np.abs(np.diff(eye_open, prepend=eye_open[0]))
    d_melt = np.abs(np.diff(melt, prepend=melt[0]))
    mblur = (speed > 0.05) & ((punch > 0.12) | (d_open > 0.01) | (d_melt > 0.005) | ((recall > 0) & (recall < 1)))
    out = dict(phase=phase, speed=speed, tape=tape, spike_h=h, punch=punch, punch_age=punch_age, mblur=mblur,
               eye_open=eye_open, melt=melt, tremor=tremor, pupil=pupil, iris_glow=iris_glow, spin=2 * np.pi * phase,
               gravity=gravity, face_q=face_q, eye_q=eye_q, drop_tau=drop_tau, drop_on=drop_on, recall=recall,
               halo_glow=halo_glow, mandala=mandala, mandala_glow=mandala_glow, seq=seq, dust_glow=dust_glow,
               haze=haze, cam_loc=cam_loc, cam_tgt=cam_tgt, lens=lens, focus=focus, fstop=fstop, shot=shot_of,
               scroll=phase, kick=ch["kick"], snare=ch["snare"], sub=sub, kick_seam=kick_seam,
               snare_seam=snare_seam, sub_seam=sub_seam)
    np.savez(AOUT / "choreo.npz", **out)
    (AOUT / "shots.json").write_text(json.dumps({"cuts": cuts, "shots": shots, "tape_total": float(tape_total),
                                                 "stop_frame": int(stop_f0), "drops": drops}, indent=1))

    # ----------------------------------------------------------------- frame plan for post
    src = f.copy()
    black = np.zeros(F, bool)
    negative = np.zeros(F, bool)
    for r in rolls:                                                      # 3-frame retrigger stutters
        a, b = r["frame0"], min(r["frame1"], F)
        for i in range(a, b):
            src[i] = a + ((i - a) % 3)
    acc, last = 0.0, pd_f0                                               # frame rate falls with the tape
    for i in range(pd_f0, pd_f1):
        acc += max(speed[i], 0.0)
        if acc >= 1.0 or i == pd_f0:
            acc -= 1.0 if i != pd_f0 else 0.0
            last = i
        src[i] = last
    for a, b in dead_runs:
        if abs(a - pd_f1) <= 3 or b == drop1:                            # the power-down's silent tail, the pre-drop gap
            black[a:b] = True
        elif a >= ts_f0 - beat_frames and b <= ts_f0:                     # tape stopped before the tape-start
            negative[a:b] = True
            src[a:b] = a - 1
            black[a:b] = ((np.arange(a, b) - a) // 3) % 2 == 1
            negative[a:b] &= ~black[a:b]
        else:                                                             # gated silences in the drops
            negative[a:b] = True
    plan = {"src": src.tolist(), "black": black.tolist(), "negative": negative.tolist(),
            "render": sorted(set(int(s) for s, bl in zip(src, black) if not bl)),
            "cuts": cuts, "datamosh": [kickin_f, cuts[3], cuts[8], cuts[12]],
            "falls": [int(round((x["t0"] - A["window"]["t0"]) * FPS)) for x in A["falling_notes"]
                      if stop_f1 - 6 <= (x["t0"] - A["window"]["t0"]) * FPS < drop1],
            "stop": [int(stop_f0), int(stop_f1)], "riser": [int(riser_f0), int(drop1)], "powerdown": [int(pd_f0), int(pd_f1)],
            "tape_start": [int(ts_f0), int(F)], "cev": [int(cev_f), int(kickin_f)], "dive": [int(dive_f0), int(F)],
            "drops": drops, "rolls": [[r["frame0"], r["frame1"]] for r in rolls]}
    (AOUT / "frameplan.json").write_text(json.dumps(plan))
    print(f"frames {F}, tape total {tape_total:.2f} s, cuts {cuts}")
    print(f"unique frames to render: {len(plan['render'])}, black {int(black.sum())}, negative {int(negative.sum())}")
    print("shots: " + ", ".join(f"{s['name']} {s['f0']}-{s['f1']}" for s in shots))


if __name__ == "__main__":
    main()
