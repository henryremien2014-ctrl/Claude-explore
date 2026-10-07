#!/usr/bin/env python3
"""MAGNETIC: the synthesized track.

Dark glitch bass, 150 bpm, F Phrygian. The song is 16 bars: two pre-roll intro
bars, the 13-bar window that becomes the video (song bars 2-14) and one bar of
silence after the hard cut.

Everything is first laid out on a "tape timeline" (the arrangement with no
transport effects). The output is that tape read back through a playback
position curve P(t), so the tape-stop, the power-down and the tape-start are
real varispeed: pitch and tempo fall together, the way a slowing reel sounds.

Writes out/song.wav (48 kHz, 24-bit) and out/truth.json, the log of every event
the synth placed, in output time, so the blind analysis can be checked against it.
"""
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from numba import njit
from scipy.signal import fftconvolve

OUT = Path(__file__).resolve().parent / "out"

SR = 48000
BPM = 150.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
S16 = BEAT / 4
NBARS = 16
N = int(round(NBARS * BAR * SR))
PAD = int(2.0 * SR)  # the tape runs past the end so the tape-start has material to read
WINDOW_BARS = (2, 15)  # song bars [2, 15): the 13-bar video window

rng = np.random.default_rng(150)


def T(bar, beat=0.0, s16=0.0):
    """Song time (s) of a bar / beat / 16th position, all 0-indexed."""
    return bar * BAR + beat * BEAT + s16 * S16


def I(t):
    return int(round(t * SR))


def mtof(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# ----------------------------------------------------------------------------- DSP kernels

@njit(cache=True)
def saw(freq, ph):
    """Band-limited (polyBLEP) sawtooth with per-sample frequency."""
    n = freq.shape[0]
    out = np.empty(n)
    for i in range(n):
        dt = freq[i] / SR
        ph += dt
        ph -= math.floor(ph)
        v = 2.0 * ph - 1.0
        if dt > 1e-6:
            if ph < dt:
                x = ph / dt
                v -= x + x - x * x - 1.0
            elif ph > 1.0 - dt:
                x = (ph - 1.0) / dt
                v -= x * x + x + x + 1.0
        out[i] = v
    return out


@njit(cache=True)
def sine(freq, ph):
    n = freq.shape[0]
    out = np.empty(n)
    for i in range(n):
        out[i] = math.sin(2.0 * math.pi * ph)
        ph += freq[i] / SR
        ph -= math.floor(ph)
    return out


@njit(cache=True)
def svf(x, fc, res, mode):
    """Zavalishin TPT state-variable filter with per-sample cutoff. mode 0=LP 1=BP 2=HP."""
    n = x.shape[0]
    y = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    k = 2.0 - 2.0 * res
    for i in range(n):
        f = fc[i]
        if f < 10.0:
            f = 10.0
        elif f > 0.45 * SR:
            f = 0.45 * SR
        g = math.tan(math.pi * f / SR)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2
        elif mode == 1:
            y[i] = v1
        else:
            y[i] = x[i] - k * v1 - v2
    return y


@njit(cache=True)
def read(buf, pos):
    """Read a mono buffer at fractional sample positions (cubic Hermite)."""
    n = pos.shape[0]
    L = buf.shape[0]
    out = np.zeros(n)
    for i in range(n):
        p = pos[i]
        j = int(math.floor(p))
        if j < 1 or j + 2 >= L:
            continue
        f = p - j
        y0 = buf[j - 1]
        y1 = buf[j]
        y2 = buf[j + 1]
        y3 = buf[j + 2]
        c1 = 0.5 * (y2 - y0)
        c2 = y0 - 2.5 * y1 + 2.0 * y2 - 0.5 * y3
        c3 = 0.5 * (y3 - y0) + 1.5 * (y1 - y2)
        out[i] = ((c3 * f + c2) * f + c1) * f + y1
    return out


def filt(x, fc, res=0.0, mode=0):
    """SVF over a mono or stereo signal; fc is a scalar or a per-sample array."""
    fc = np.ascontiguousarray(np.broadcast_to(np.asarray(fc, np.float64), (x.shape[0],)))
    if x.ndim == 1:
        return svf(np.ascontiguousarray(x, np.float64), fc, res, mode)
    return np.stack([svf(np.ascontiguousarray(x[:, c], np.float64), fc, res, mode)
                     for c in range(x.shape[1])], axis=1)


def place(bus, sig, t, gain=1.0, pan=0.0):
    """Add a mono (panned) or stereo signal into a stereo bus at time t."""
    if sig.ndim == 1:
        a = (pan + 1.0) * math.pi / 4.0
        sig = np.stack([sig * math.cos(a), sig * math.sin(a)], axis=1) * math.sqrt(2.0)
    i0 = I(t)
    i1 = min(i0 + sig.shape[0], bus.shape[0])
    if i1 > i0:
        bus[i0:i1] += gain * sig[: i1 - i0]


# ----------------------------------------------------------------------------- instruments

F1 = mtof(29)  # 43.65 Hz, the root of everything


def kick808(length=0.40, dive_st=5.0, drive=2.4):
    """808: punch sweep 205 Hz -> F1, then the tail dives a fourth (F1 -> C1)."""
    n = I(length)
    t = np.arange(n) / SR
    f = F1 + (205.0 - F1) * np.exp(-t / 0.011)
    f = f * 2.0 ** (-dive_st * (1.0 - np.exp(-np.maximum(t - 0.05, 0.0) / 0.20)) / 12.0)
    body = sine(f, 0.0)
    amp = np.exp(-t / 0.32) * np.minimum(t / 0.0006, 1.0) * np.clip((length - t) / 0.008, 0.0, 1.0)
    click = filt(rng.standard_normal(n) * np.exp(-t / 0.0022), 3200.0, 0.3, 1)
    x = body * amp + 0.9 * click
    return np.tanh(drive * x) / math.tanh(drive)


def snare(length=0.35):
    n = I(length)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    nb = filt(noise, 2100.0, 0.3, 1) * np.exp(-t / 0.11)
    nh = filt(noise, 6000.0, 0.1, 2) * np.exp(-t / 0.045)
    body = sine(170.0 + 70.0 * np.exp(-t / 0.018), 0.0) * np.exp(-t / 0.075)
    x = 1.6 * nb + 0.5 * nh + 0.9 * body
    x *= np.minimum(t / 0.0008, 1.0) * np.clip((length - t) / 0.01, 0.0, 1.0)
    return np.tanh(2.2 * x) / math.tanh(2.2)


def hat(length=0.06):
    n = I(length)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0):
        x += np.sign(np.sin(2 * np.pi * f * 1.7 * t + rng.random() * 6.283))
    x = filt(filt(x, 10500.0, 0.4, 1), 7000.0, 0.0, 2)
    x = x + 0.4 * filt(rng.standard_normal(n), 8000.0, 0.0, 2)
    return x * np.exp(-t / 0.018) * 0.25


def lead(midi, dur, bend, frac=0.45, curve=1.6, bright=1.0, sub=0.45, rel=0.018):
    """Gritty distorted saw. The tail of every note bends down like tape slowing:
    the pitch ratio follows a motor run-down curve, and the timbre darkens with it."""
    n = I(dur + rel)
    t = np.arange(n) / SR
    u = np.clip((t / dur - (1.0 - frac)) / frac, 0.0, 1.0)
    ratio = 1.0 - (1.0 - 2.0 ** (-bend / 12.0)) * u ** curve
    f0 = mtof(midi) * ratio
    cut = (700.0 + 4200.0 * bright * np.exp(-t / 0.13)) * ratio ** 1.5
    amp = (np.minimum(t / 0.003, 1.0) * np.clip((dur + rel - t) / rel, 0.0, 1.0)
           * (0.55 + 0.45 * ratio))
    chans = []
    for d0, d1 in ((-9.0, 6.0), (8.0, -5.0)):
        x = (saw(f0 * 2 ** (d0 / 1200), rng.random())
             + 0.8 * saw(f0 * 2 ** (d1 / 1200), rng.random())
             + sub * saw(f0 * 0.5, rng.random()))
        x = np.tanh(2.6 * x)
        x = filt(x, cut, 0.32, 0)
        x = np.sin(1.25 * x)  # soft fold for grit
        crushed = np.round(x * 24) / 24  # parallel bit crush
        chans.append((0.8 * x + 0.2 * crushed) * amp)
    return np.stack(chans, axis=1)


def pad(midis, dur, cutoff, hp=0.0, attack=0.4):
    n = I(dur)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for m in midis:
        for c in range(2):
            for d in (-7.0, 0.0, 7.0):
                cents = d + (2 * c - 1) * 3.0
                out[:, c] += saw(np.full(n, mtof(m) * 2 ** (cents / 1200)), rng.random())
    out = filt(out, cutoff, 0.15, 0)
    if hp:
        out = filt(out, hp, 0.0, 2)
    env = np.minimum(t / attack, 1.0) * np.clip((dur - t) / 0.3, 0.0, 1.0)
    return out * env[:, None] / (3.0 * len(midis))


def sub_tone(dur, attack=0.004, rel=0.01):
    n = I(dur)
    t = np.arange(n) / SR
    x = sine(np.full(n, F1), 0.0) + 0.12 * sine(np.full(n, 2 * F1), 0.0)
    return x * np.minimum(t / attack, 1.0) * np.clip((dur - t) / rel, 0.0, 1.0)


def impact(length=1.4):
    n = I(length)
    t = np.arange(n) / SR
    boom = sine(30.0 + 48.0 * np.exp(-t / 0.08), 0.0) * np.exp(-t / 0.55)
    noise = filt(rng.standard_normal((n, 2)), 3000.0 * np.exp(-t / 0.18) + 180.0, 0.1, 0)
    noise *= np.exp(-t / 0.28)[:, None]
    return np.tanh(1.6 * (boom[:, None] + 0.7 * noise))


def tape_hiss(n):
    w = rng.standard_normal((n, 2))
    W = np.fft.rfft(w, axis=0)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1]
    W /= np.sqrt(f)[:, None]
    p = np.fft.irfft(W, n=n, axis=0)
    p = filt(filt(p, 9000.0, 0.0, 0), 120.0, 0.0, 2)
    return p / np.sqrt(np.mean(p ** 2))


def make_ir(rt60, length, damp=0.45, predelay=0.015):
    n = I(length)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        w = rng.standard_normal(n)
        lo = filt(w, 700.0, 0.0, 0)
        ir[:, c] = lo * np.exp(-6.91 * t / rt60) + (w - lo) * np.exp(-6.91 * t / (rt60 * damp))
    k = I(0.002)
    ir[:k] *= np.linspace(0.0, 1.0, k)[:, None]
    ir = np.vstack([np.zeros((I(predelay), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))


def reverb(x, ir):
    mono = x.mean(axis=1)
    return np.stack([fftconvolve(mono, ir[:, c])[: len(mono)] for c in range(2)], axis=1)


# ----------------------------------------------------------------------------- the score

# (16th position, length in 16ths, midi, bend in semitones). Every note bends down.
RIFF_A = [(0, 3, 41, 1.5), (3, 1, 41, 0.5), (4, 2, 44, 1.0), (6, 2, 42, 3.0),
          (8, 2, 41, 1.0), (10, 1, 49, 0.7), (11, 2, 48, 2.0), (13, 3, 41, 7.0)]
RIFF_B = [(0, 3, 41, 1.5), (3, 1, 41, 0.5), (4, 2, 44, 1.0), (6, 1, 46, 0.7),
          (7, 1, 44, 0.7), (8, 2, 42, 2.0), (10, 2, 39, 1.5), (12, 4, 41, 12.0)]
# Breakdown: slow high notes, each falling through most of its length.
FALLS = [(7, 0, 5, 60, 12.0), (7, 6, 3, 61, 5.0), (7, 10, 6, 56, 12.0),
         (8, 0, 4, 65, 7.0), (8, 6, 5, 60, 12.0)]

INTRO_BARS = [0, 1, 2, 3]
KICK_BARS = [4, 5, 6, 9, 10, 11, 12, 13, 14, 15]
RIFF_BARS = INTRO_BARS + [4, 5, 6] + [9, 10, 11, 12, 13, 14, 15]
DROP_BARS = [9, 10, 11, 12, 13, 14, 15]
# Hard chop gates on the lead + sub bus (1 = open), per bar, in 16ths.
CHOPS = {9: "1111110111111011", 10: "1101101111011011", 11: "1" * 16,
         12: "1111101111101101", 13: "1011110111111111", 14: "1" * 16, 15: "1" * 16}
# Full-mix dead silences (output time): every one of these is digital zero.
DEAD = [(T(8, 3, 3), T(9, 0)),        # gap before the drop
        (T(10, 1, 2), T(10, 2)),      # gated silences inside the drop
        (T(10, 3, 2), T(10, 3, 3)),
        (T(11, 3), T(12, 0)),         # after the power-down
        (T(12, 2, 3), T(12, 3)),
        (T(13, 3), T(14, 0)),         # tape stopped before the tape-start
        (T(15, 0), NBARS * BAR)]      # hard cut
# Beat-repeat stutter rolls on the output: (start, end, slice length, semitones per repeat)
ROLLS = [(T(2, 3), T(3, 0), S16 / 2, 0.5),
         (T(3, 2), T(3, 3), S16, 0.0),
         (T(3, 3), T(4, 0), S16 / 2, 0.75),
         (T(5, 3), T(6, 0), S16 / 2, 0.0),
         (T(13, 2), T(13, 3), S16 / 2, -0.5)]


def build_tape():
    L = N + PAD
    s = {k: np.zeros((L, 2)) for k in ("kick", "snare", "hat", "lead", "sub", "pad", "brk", "fx", "hiss")}
    kicks = []
    for b in KICK_BARS:
        for beat in range(4):
            place(s["kick"], kick808(0.40), T(b, beat))
            kicks.append(T(b, beat))
        place(s["snare"], snare(), T(b, 2), pan=0.04)
        for beat in range(4):
            place(s["hat"], hat(), T(b, beat, 2), pan=0.25)
    for b in (2, 3):  # quiet ticks inside the filtered intro
        for beat in range(4):
            place(s["hat"], hat(), T(b, beat, 2), gain=0.6, pan=0.25)

    riff_notes = []
    for b in RIFF_BARS:
        riff = RIFF_A if b % 2 == 0 else RIFF_B
        for pos, ln, midi, bend in riff:
            if b == 13 and pos < 8:
                midi += 12  # drop 2 lifts the first half an octave
            dur = ln * S16 * (0.92 if ln == 1 else 0.97)
            place(s["lead"], lead(midi, dur, bend), T(b, 0, pos))
            riff_notes.append((T(b, 0, pos), dur, midi, bend))

    falls = []
    for b, pos, ln, midi, bend in FALLS:
        dur = ln * S16
        place(s["brk"], lead(midi, dur, bend, frac=0.85, curve=1.25, bright=0.6, sub=0.0, rel=0.06),
              T(b, 0, pos))
        falls.append({"t0": T(b, 0, pos), "t1": T(b, 0, pos) + dur, "semitones": bend, "midi": midi})
    place(s["brk"], pad([53, 60, 66], 2 * BAR, 900.0, hp=170.0, attack=0.05), T(7, 0), gain=0.8)
    place(s["brk"], filt(snare(0.6), 1500.0, 0.1, 0), T(7, 2), gain=0.9)  # lowpassed half-time snare

    # Intro: pad + sub drone under the riff; the whole intro bus is swept open later.
    place(s["pad"], pad([41, 48, 54], 4 * BAR, 2500.0, attack=1.2), T(0, 0))
    place(s["sub"], sub_tone(4 * BAR, attack=1.5), T(0, 0), gain=0.8)
    for b in DROP_BARS + [4, 5, 6]:
        place(s["sub"], sub_tone(BAR), T(b, 0), gain=0.55)

    place(s["fx"], impact(), T(4, 0), gain=0.45)
    place(s["fx"], impact(), T(9, 0), gain=1.0)
    place(s["fx"], impact(), T(12, 0), gain=1.1)
    s["hiss"][:] = tape_hiss(L)
    return s, kicks, riff_notes, falls


def mix_tape(s, kicks):
    L = N + PAD
    t = np.arange(L) / SR
    # Filtered intro: the lead, pad and hats sweep open from 160 Hz to 18 kHz by the kick-in,
    # slow at first so the window opens muffled, with a crescendo under it.
    x = np.clip(t / T(4, 0), 0.0, 1.0)
    sweep = 160.0 * (18000.0 / 160.0) ** (x ** 1.8)
    swell = (0.5 + 0.5 * x ** 2)[:, None]
    for k in ("lead", "pad", "hat"):
        s[k] = filt(s[k], sweep, 0.45, 0) * swell
    s["brk"] = filt(s["brk"], 1400.0, 0.2, 0)  # lowpassed breakdown

    # Sidechain pump keyed by the kicks: light in the groove, heavy in the drops.
    duck = np.zeros(L)
    for tk in kicks:
        depth = 0.85 if tk >= T(9, 0) else 0.4
        i0 = I(tk)
        n = min(I(0.6), L - i0)
        d = np.arange(n) / SR
        shape = np.where(d < 0.004, d / 0.004, np.exp(-(d - 0.004) / 0.11))
        duck[i0:i0 + n] = np.maximum(duck[i0:i0 + n], depth * shape)
    g_sc = (1.0 - duck)[:, None]

    # Hard chop gates on the lead + sub in the drops (0.5 ms ramps, no clicks, no mercy).
    chop = np.ones(L)
    for b, pat in CHOPS.items():
        for step, ch in enumerate(pat):
            if ch == "0":
                chop[I(T(b, 0, step)):I(T(b, 0, step + 1))] = 0.0
    k = I(0.0005)
    chop = np.convolve(chop, np.ones(k) / k, mode="same")[:, None]

    rv_short = make_ir(0.9, 1.6, damp=0.5)
    rv_long = make_ir(3.6, 5.0, damp=0.35, predelay=0.03)
    lead_bus = s["lead"] * g_sc * chop
    tape = (1.00 * s["kick"]
            + 0.55 * s["snare"] + 0.18 * reverb(s["snare"], rv_short)
            + 0.30 * s["hat"] * g_sc
            + 0.42 * lead_bus + 0.10 * reverb(lead_bus, rv_short)
            + 0.50 * s["sub"] * g_sc * chop
            + 0.30 * s["pad"] * g_sc
            + 0.55 * s["brk"] + 0.45 * reverb(s["brk"], rv_long)
            + 0.45 * s["fx"]
            + 10 ** (-46 / 20) * s["hiss"])
    return tape


def transport():
    """Playback position P(t) (s of tape) and tape speed P'(t) for every output sample."""
    t = np.arange(N) / SR
    P = t.copy()
    spd = np.ones(N)

    def seg(a, b):
        m = (t >= a) & (t < b)
        return m, (t[m] - a) / (b - a), b - a

    m, u, D = seg(T(6, 2), T(7, 0))  # tape-stop: linear run-down over two beats
    spd[m] = 1.0 - u
    P[m] = T(6, 2) + D * (u - u ** 2 / 2)
    m, u, D = seg(T(11, 0), T(11, 3))  # power-down: slower, heavier platter
    spd[m] = 1.0 - u ** 1.4
    P[m] = T(11, 0) + D * (u - u ** 2.4 / 2.4)
    m, u, D = seg(T(14, 0), T(14, 2))  # tape-start: motor spin-up ...
    spd[m] = u ** 1.5
    P[m] = T(14, 0) + D * u ** 2.5 / 2.5
    p_mid = T(14, 0) + D / 2.5
    m, v, D = seg(T(14, 2), T(15, 0))  # ... that overshoots into fast-forward
    spd[m] = 1.0 + 0.6 * v
    P[m] = p_mid + D * (v + 0.3 * v ** 2)

    gate = np.ones(N)
    for a, b in DEAD:
        gate[I(a):I(b)] = 0.0
    return P, spd, gate


def riser():
    """The breakdown drone wound up from 0.12x to 1.5x tape speed: the world restarts."""
    a, b = T(8, 0), T(8, 3, 3)
    n = I(b - a)
    u = np.arange(n) / n
    s = 0.12 * 2.0 ** (math.log2(1.5 / 0.12) * u ** 1.1)
    src_n = int(np.sum(s)) + SR
    drone = (saw(np.full(src_n, F1), 0.1)
             + 0.7 * saw(np.full(src_n, mtof(41) * 1.003), 0.3)
             + 0.5 * saw(np.full(src_n, mtof(48) * 0.998), 0.6))
    drone = filt(np.tanh(1.8 * drone), 5000.0, 0.0, 0)
    x = read(drone, np.cumsum(s) + 2.0)
    nz = filt(rng.standard_normal((n, 2)), 200.0 * 40.0 ** (u ** 1.3), 0.5, 1)
    env = (u ** 1.5)[:, None]
    return (0.7 * x[:, None] + 0.35 * nz) * env, s


def roll(buf, a, b, div, semis, gain0=0.55):
    """Beat-repeat: replay the slice that starts at a, every div seconds, until b."""
    i0, i1, L = I(a), I(b), I(div)
    sl = buf[i0:i0 + L].copy()
    reps = int(math.ceil((i1 - i0) / L))
    hits = []
    for k in range(reps):
        j = i0 + k * L
        n = min(L, i1 - j)
        pos = np.clip(np.arange(n) * 2 ** (k * semis / 12), 0, L - 1)
        seg = np.stack([np.interp(pos, np.arange(L), sl[:, c]) for c in range(2)], axis=1)
        f = min(24, n // 4)
        env = np.ones(n)
        env[:f] = np.linspace(0, 1, f)
        env[-f:] = np.linspace(1, 0, f)
        buf[j:j + n] = seg * env[:, None] * (gain0 + (1 - gain0) * k / max(1, reps - 1))
        hits.append(j / SR)
    return hits


def output_times(tau_list, P, spd, gate, min_speed=0.2):
    """Where tape-time events land in output time (skipping jumps, gates and stalled tape)."""
    dP = np.diff(P)
    ok = (np.abs(dP) < 2.0 / SR) & (gate[1:] > 0) & (spd[1:] > min_speed)
    res = []
    for tau in tau_list:
        idx = np.nonzero((P[:-1] < tau) & (P[1:] >= tau) & ok)[0]
        res += [float((i + 1) / SR) for i in idx]
    return sorted(res)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stems, kicks, riff_notes, falls = build_tape()
    tape = mix_tape(stems, kicks)
    P, spd, gate = transport()
    out = np.stack([read(np.ascontiguousarray(tape[:, c]), P * SR) for c in range(2)], axis=1)

    rz, rz_speed = riser()
    place(out, rz, T(8, 0), gain=0.55)

    roll_hits = []
    for a, b, div, semis in ROLLS:
        roll_hits.append({"t0": a, "t1": b, "div": div, "hits": roll(out, a, b, div, semis)})

    # Master: gain-stage, glue saturation, parallel crunch, hard gate, peak at -1 dBFS.
    out /= np.sqrt(np.mean(out[I(T(9, 0)):I(T(11, 0))] ** 2)) * 4.0
    sat = np.tanh(1.6 * out) / math.tanh(1.6)
    crunch = np.repeat(np.round(sat[::2] * 512) / 512, 2, axis=0)[: len(sat)]
    master = 0.88 * sat + 0.12 * crunch
    master *= gate[:, None]
    master *= 10 ** (-1 / 20) / np.max(np.abs(master))
    sf.write(OUT / "song.wav", master.astype(np.float32), SR, subtype="PCM_24")

    # Ground truth, in output time.
    w0, w1 = T(WINDOW_BARS[0]), T(WINDOW_BARS[1])
    truth = {
        "sr": SR, "bpm": BPM, "beat_s": BEAT, "bar_s": BAR, "song_bars": NBARS,
        "window_s": [w0, w1], "window_bars": list(WINDOW_BARS),
        "kick_in": T(4, 0), "drops": [T(9, 0), T(12, 0)], "hard_cut": T(15, 0),
        "kicks": output_times(kicks, P, spd, gate),
        "snares": output_times([T(b, 2) for b in KICK_BARS] + [T(7, 2)], P, spd, gate),
        "rolls": roll_hits,
        "dead": [[a, min(b, NBARS * BAR)] for a, b in DEAD],
        "tape_events": [
            {"type": "stop", "t0": T(6, 2), "t1": T(7, 0), "speed": "1-u"},
            {"type": "riser_spinup", "t0": T(8, 0), "t1": T(8, 3, 3), "speed": "0.12*2^(3.64*u^1.1)"},
            {"type": "powerdown", "t0": T(11, 0), "t1": T(11, 3), "speed": "1-u^1.4"},
            {"type": "start", "t0": T(14, 0), "t1": T(15, 0), "speed": "u^1.5 then 1+0.6v"},
        ],
        "falls": falls,
        "chops": [[T(b, 0, i), T(b, 0, i + 1)] for b, pat in CHOPS.items() for i, c in enumerate(pat)
                  if c == "0" and b not in (11, 14, 15)],
        "riff_notes": [{"t0": a, "dur": d, "midi": m, "bend": bnd} for a, d, m, bnd in riff_notes
                       if a < T(6, 2) or a >= T(9, 0)],
        "sections": [
            {"name": "pre-roll", "t0": T(0), "t1": T(2)},
            {"name": "intro", "t0": T(2), "t1": T(4)},
            {"name": "kick-in", "t0": T(4), "t1": T(6, 2)},
            {"name": "tape-stop", "t0": T(6, 2), "t1": T(7)},
            {"name": "breakdown", "t0": T(7), "t1": T(8)},
            {"name": "riser", "t0": T(8), "t1": T(9)},
            {"name": "drop", "t0": T(9), "t1": T(11)},
            {"name": "power-down", "t0": T(11), "t1": T(12)},
            {"name": "drop-2", "t0": T(12), "t1": T(14)},
            {"name": "tape-start", "t0": T(14), "t1": T(15)},
        ],
    }
    # Tape speed as heard, at 1 kHz: transport speed, the riser's own speed, 0 when gated.
    tt = np.arange(0, N, SR // 1000)
    sp = spd[tt] * gate[tt]
    ra, rb = I(T(8, 0)), I(T(8, 3, 3))
    in_r = (tt >= ra) & (tt < rb)
    sp[in_r] = rz_speed[tt[in_r] - ra]
    truth["speed_1khz"] = [round(float(v), 4) for v in sp]
    (OUT / "truth.json").write_text(json.dumps(truth, indent=1))

    peak = np.max(np.abs(master))
    rms = np.sqrt(np.mean(master[I(w0):I(w1)] ** 2))
    print(f"song.wav  {N / SR:.2f} s  peak {20 * np.log10(peak):.2f} dBFS  "
          f"window rms {20 * np.log10(rms):.2f} dBFS  kicks heard {len(truth['kicks'])}")
    for name, st in stems.items():
        r = np.sqrt(np.mean(st ** 2))
        print(f"  stem {name:6s} rms {20 * np.log10(r + 1e-12):7.2f} dB  peak {np.max(np.abs(st)):.2f}")


if __name__ == "__main__":
    main()
