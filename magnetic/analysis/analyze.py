#!/usr/bin/env python3
"""MAGNETIC: listen with math.

Blind analysis of the song. Nothing in this file reads the synth's truth log;
validate.py does that afterwards. It measures:

  * tempo and the bar grid (loudness-weighted low-band flux, comb-refined)
  * onsets, and kicks and snares by template matching: the template is learned
    from the song's own most confident hits, and inside tape glides it is warped
    by the measured tape speed, so slowed and sped-up kicks are still found
  * the 808 pitch dive on every kick
  * stutter rolls (a beat-repeat makes one beat self-similar at the 32nd lag)
  * dead silences (digital zero), gated chops, spectral centroid, band energies
  * falling notes (pYIN in the mid band)
  * tape speed: pYIN on the low end divided by the song's root pitch. A tape
    event is a sustained, moving departure from the root (well past the 808's own
    dive); dives are pinned to 0 where they hit silence, rises to 0 where they
    leave it. No low end (the breakdown) or digital silence means the tape is stopped.

Then it finds the structure, picks the 13-bar window on bar lines, cuts it from the
untouched samples and maps everything onto the 30 fps frame grid.

    analyze.py song.wav outdir
"""
import json
import math
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.signal import butter, fftconvolve, find_peaks, sosfiltfilt

FPS = 30
HOP = 256            # STFT / VQT hop, 5.33 ms at 48 kHz
BPO = 48
FMIN = 20.0
NOCT = 9
SIL_DB = -90.0       # digital silence
WINDOW_BARS = 13
PITCH_RATE = 100     # pYIN frames per second
LOW_FMIN = 18.0
KICK_NCC = 0.8


def pdb(x):
    return 10.0 * np.log10(np.maximum(x, 1e-20))


def runs(mask):
    """[start, end) pairs of True runs in a boolean array."""
    m = np.concatenate([[False], np.asarray(mask, bool), [False]]).astype(int)
    d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def norm01(x, lo_pct=5, hi_pct=99):
    lo, hi = np.percentile(x, lo_pct), np.percentile(x, hi_pct)
    return np.clip((x - lo) / max(hi - lo, 1e-9), 0.0, 1.0)


def nanmedian_filter(x, size):
    pad = size // 2
    xp = np.pad(x, pad, mode="edge")
    win = np.lib.stride_tricks.sliding_window_view(xp, size)
    out = np.full(len(x), np.nan)
    ok = ~np.all(np.isnan(win), axis=1)
    out[ok] = np.nanmedian(win[ok], axis=1)
    out[np.isnan(x)] = np.nan
    return out


class Song:
    def __init__(self, path):
        y2, sr = sf.read(path, always_2d=True)
        self.y2, self.sr = y2, sr
        self.y = y2.mean(axis=1)
        self.n = len(self.y)
        self.dur = self.n / sr
        self.fr = sr / HOP
        self.S = np.abs(librosa.stft(self.y, n_fft=2048, hop_length=HOP)) ** 2
        self.f = librosa.fft_frequencies(sr=sr, n_fft=2048)
        self.nf = self.S.shape[1]
        self.t = np.arange(self.nf) / self.fr
        V = np.abs(librosa.vqt(self.y, sr=sr, hop_length=HOP, fmin=FMIN,
                               n_bins=BPO * NOCT, bins_per_octave=BPO))
        self.V = V[:, : self.nf]
        self.vf = librosa.cqt_frequencies(BPO * NOCT, fmin=FMIN, bins_per_octave=BPO)
        self.Vdb = 20 * np.log10(np.maximum(self.V, 1e-9))
        self.Vdb -= self.Vdb.max()

    def band(self, lo, hi):
        return self.S[(self.f >= lo) & (self.f < hi)].sum(axis=0)

    def vbins(self, lo, hi):
        idx = np.nonzero((self.vf >= lo) & (self.vf < hi))[0]
        return idx[0], idx[-1] + 1


# ----------------------------------------------------------------------------- silence

def dead_silences(song, min_len=0.008):
    amp = np.abs(song.y2).max(axis=1)
    sil = amp < 10 ** (SIL_DB / 20)
    out = [[a / song.sr, b / song.sr] for a, b in runs(sil) if (b - a) / song.sr >= min_len]
    mask = np.zeros(song.n, bool)
    for a, b in out:
        mask[int(round(a * song.sr)):int(round(b * song.sr))] = True
    return out, mask


# ----------------------------------------------------------------------------- tempo, beats, bars

def tempo_grid(song):
    fr = song.fr
    # Loudness-weighted low-band flux: a dB flux counts the quiet intro's riff as much
    # as the kicks, and its 7-sixteenth note spacing then wins the autocorrelation.
    e = np.sqrt(song.band(25, 150))
    flux = np.maximum(np.diff(e, prepend=e[0]), 0.0)
    flux /= flux.max()
    x = flux - flux.mean()
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    lo, hi = int(fr * 60 / 220), int(fr * 60 / 60)
    k = lo + int(np.argmax(ac[lo:hi]))
    a, b, c = ac[k - 1], ac[k], ac[k + 1]
    period0 = (k + 0.5 * (a - c) / (a - 2 * b + c)) / fr

    idx = np.arange(len(flux))
    best = (-1.0, period0, 0.0)
    for P in period0 * np.linspace(0.996, 1.004, 161):
        nb = int(song.dur / P) + 1
        for ph in np.arange(0.0, P, 0.25 / fr):
            pos = (ph + P * np.arange(nb)) * fr
            pos = pos[pos < len(flux) - 1]
            s = np.interp(pos, idx, flux).sum()
            if s > best[0]:
                best = (s, P, ph)
    _, P, ph = best
    beats = ph + P * np.arange(int((song.dur - ph) / P) + 1)
    while beats[0] - P >= -0.5 * P:     # extend the grid back over a kickless intro
        beats = np.concatenate([[beats[0] - P], beats])
    beats = beats[beats < song.dur]

    sb = pdb(song.band(1500, 5000))
    sflux = np.maximum(np.diff(sb, prepend=sb[0]), 0.0)
    rms = pdb(song.S.sum(axis=0))
    w = int(0.15 * fr)
    m = np.convolve(rms, np.ones(w) / w, mode="valid")
    nov = np.zeros_like(rms)
    nov[w:len(m)] = np.maximum(0.0, m[w:] - m[:-w])
    at = lambda series, times: np.interp(times * fr, idx, series)
    z = lambda v: (v - v.mean()) / (v.std() + 1e-9)
    sfz, nvz = z(at(sflux, beats)), z(at(nov, beats))
    kk = np.arange(len(beats))
    # The snare sits on beat 3 and sections change on beat 1.
    scores = [float(sfz[(kk - o) % 4 == 2].mean() + nvz[(kk - o) % 4 == 0].mean()) for o in range(4)]
    o = int(np.argmax(scores))
    downbeats = beats[(kk - o) % 4 == 0]
    while downbeats[0] - 4 * P > -0.5 * P:
        downbeats = np.concatenate([[downbeats[0] - 4 * P], downbeats])
    return {"bpm": 60.0 / P, "period": P, "beats": beats, "bars": downbeats, "downbeat_scores": scores}


def snap_grid(grid, kick_t):
    """Kicks are measured to the sample; shift the grid phase by their median offset."""
    P = grid["period"]
    if len(kick_t) == 0:
        return grid
    d = (kick_t - grid["beats"][0] + P / 2) % P - P / 2
    off = float(np.median(d))
    g = dict(grid)
    g["beats"] = grid["beats"] + off
    g["bars"] = grid["bars"] + off
    g["phase_correction_s"] = off
    return g


def onsets(song):
    oenv = librosa.onset.onset_strength(y=song.y, sr=song.sr, hop_length=HOP)
    on = librosa.onset.onset_detect(onset_envelope=oenv, sr=song.sr, hop_length=HOP, units="time")
    return on, oenv


# ----------------------------------------------------------------------------- pitch tracks

def pitch_track(song, band, fmin, fmax, sr2, frame_length):
    lo, hi = band
    if lo:
        sos = butter(4, [lo, hi], "bp", fs=song.sr, output="sos")
    else:
        sos = butter(6, hi, "lp", fs=song.sr, output="sos")
    yb = librosa.resample(sosfiltfilt(sos, song.y), orig_sr=song.sr, target_sr=sr2)
    hop = sr2 // PITCH_RATE
    f0, _, _ = librosa.pyin(yb, fmin=fmin, fmax=fmax, sr=sr2, frame_length=frame_length,
                            hop_length=hop, resolution=0.05)
    return np.arange(len(f0)) / PITCH_RATE, f0


# ----------------------------------------------------------------------------- stutter rolls

def _ac_peak(x, d, tol=0.06):
    """Peak normalized autocorrelation of x for lags within d * (1 +- tol)."""
    n = len(x)
    X = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(X * np.conj(X))[:n]
    cs = np.concatenate([[0.0], np.cumsum(x * x)])
    lags = np.arange(int(d * (1 - tol)), int(d * (1 + tol)) + 1)
    r = ac[lags] / np.sqrt(np.maximum(cs[n - lags] * (cs[n] - cs[lags]), 1e-20))
    return float(r.max())


def rolls(song, beats, P, dead_mask, thr=0.6):
    """A beat-repeat replays the same slice every 32nd (or 16th): that beat is then
    strongly self-similar at the slice lag, in the waveform or (for pitch-stepped
    repeats) in the high-band envelope. Ordinary music is not."""
    sos = butter(4, 200, "hp", fs=song.sr, output="sos")
    yh = sosfiltfilt(sos, song.y)
    env = uniform_filter1d(np.abs(yh), int(0.002 * song.sr))
    L = int(P * song.sr)
    found = []
    for b in beats:
        i0 = int(round(b * song.sr))
        if i0 < 0 or i0 + L > song.n or dead_mask[i0:i0 + L].mean() > 0.2:
            continue
        seg, eseg = yh[i0:i0 + L], env[i0:i0 + L] - env[i0:i0 + L].mean()
        s32 = max(_ac_peak(seg, P * song.sr / 8), _ac_peak(eseg, P * song.sr / 8))
        s16 = _ac_peak(seg, P * song.sr / 4)
        if s32 > thr and s32 >= s16 - 0.05:
            found.append({"t0": float(b), "t1": float(b + P), "div": P / 8, "score": s32})
        elif s16 > thr + 0.15:
            found.append({"t0": float(b), "t1": float(b + P), "div": P / 4, "score": s16})
    return found


# ----------------------------------------------------------------------------- tape speed

def tape_speed(song, tp, f0, dead_mask, roll_iv, beats):
    n = len(tp)
    idx = np.minimum((tp * song.sr).astype(int), song.n - 1)
    dead = dead_mask[idx]
    lb0, lb1 = song.vbins(25, 70)
    lvl = np.interp(tp, song.t, song.Vdb[lb0:lb1].max(axis=0))
    present = lvl > -40.0
    in_roll = np.zeros(n, bool)
    for r in roll_iv:
        in_roll |= (tp >= r["t0"] - 0.01) & (tp < r["t1"] + 0.01)

    ok = ~np.isnan(f0) & present & ~dead & ~in_roll
    midi = np.round(12 * np.log2(f0[ok] / 440.0) + 69).astype(int)
    root_midi = int(np.bincount(midi - midi.min()).argmax() + midi.min())
    root = float(np.median(f0[ok][midi == root_midi]))

    r = f0 / root
    r[in_roll | dead | ~present] = np.nan
    rs = nanmedian_filter(r, 5)
    floor = LOW_FMIN / root * 1.05      # below this pYIN is pinned at its lower limit
    cand = ~np.isnan(rs) & ((rs < 0.72) | (rs > 1.12))
    segs = []
    for a, b in runs(cand):
        if segs and a - segs[-1][1] < 8:
            segs[-1][1] = b
        else:
            segs.append([a, b])
    segs = [s for s in segs if s[1] - s[0] >= 25]

    speed = np.where(dead | ~present, 0.0, 1.0)
    hb = song.vbins(2000, 10000)
    hi_e = median_filter(np.interp(tp, song.t, pdb((10 ** (song.Vdb[hb[0]:hb[1]] / 10)).sum(axis=0))), 9)
    glides = []
    for a, b in segs:
        v = np.maximum(rs[a:b], floor)
        third = max(1, (b - a) // 3)
        rising = np.nanmean(v[-third:]) > np.nanmean(v[:third])
        if not rising:
            i = a                            # back to the last frame clearly under normal play,
            while i > 0 and not np.isnan(rs[i - 1]) and rs[i - 1] < 0.9 and rs[i - 1] >= rs[i] - 0.03:
                i -= 1
            # then extend the first 0.2 s of the dive back along its own slope to speed 1
            k1 = min(b, i + 20)
            kk = [k for k in range(i, k1) if not np.isnan(rs[k]) and rs[k] > floor]
            if len(kk) >= 5:
                slope, icpt = np.polyfit(kk, rs[kk], 1)
                if slope < 0:
                    i = int(round(max(i - 30, (1.0 - icpt) / slope)))
            start = max(i, 0)
            j = b                            # forward until silence, no low end, or play resumes
            while j < n and not dead[j] and present[j] and not (rs[j] > 0.95 if not np.isnan(rs[j]) else False):
                j += 1
            end = j
            stops = end >= n or dead[min(end, n - 1)] or not present[min(end, n - 1)]
            ends_dead = end >= n or dead[min(end, n - 1)]
            nb = beats[(beats >= start / PITCH_RATE - 0.03) & (beats <= start / PITCH_RATE + 0.2)]
            if len(nb):
                start = int(round(nb[0] * PITCH_RATE))
        else:
            i = a                            # back through the run-up to silence / no low end
            while i > 0 and not dead[i - 1] and present[i - 1] and a - i < 300 and \
                    (np.isnan(rs[i - 1]) or rs[i - 1] <= rs[i] + 0.03):
                i -= 1
            # a riser that grows out of no low end: its noise sweep starts before the low end does
            if i > 0 and not dead[i - 1]:
                while i > 0 and not dead[i - 1] and a - i < 300 and hi_e[i - 1] < hi_e[i] + 0.3:
                    i -= 1
            start = i
            j, steady = b, 0                 # forward to silence, no low end, or 0.2 s back at 1
            while j < n and not dead[j] and present[j] and steady < 20:
                steady = steady + 1 if (not np.isnan(rs[j]) and abs(rs[j] - 1.0) < 0.05) else 0
                j += 1
            end = j - steady
            starts_dead = start == 0 or dead[start - 1] or not present[start - 1]
        kt = [k for k in range(start, end) if not np.isnan(rs[k]) and rs[k] > floor]
        ks = [float(rs[k]) for k in kt]
        span = np.maximum(rs[start:end], floor)
        if np.sum(~np.isnan(span)) < 10 or np.nanmax(span) - np.nanmin(span) < 0.3:
            continue                         # it does not move far: not a tape event
        if not rising:
            ks = list(np.minimum.accumulate(ks)) if ks else []
            at, av = [start] + kt, [ks[0] if ks else 1.0] + ks
            if stops:
                at, av = at + [end], av + [0.0]
        else:
            ks = list(np.maximum.accumulate(ks)) if ks else []
            at, av = kt, ks
            if starts_dead:
                at, av = [start] + at, [0.0] + av
        if len(at) < 2:
            continue
        curve = np.interp(np.arange(start, end), at, av)
        speed[start:end] = curve
        dur = (end - start) / PITCH_RATE
        if rising:
            kind = "tape-start" if starts_dead and (start == 0 or dead[start - 1]) else "riser"
        else:
            kind = "power-down" if ends_dead else "tape-stop"
        glides.append({"type": kind, "t0": start / PITCH_RATE, "t1": end / PITCH_RATE,
                       "speed_start": float(curve[0]), "speed_end": float(curve[-1]),
                       "speed_extreme": float(curve.max() if rising else curve.min())})
    return {"speed": speed, "glides": glides, "root_hz": root, "root_midi": root_midi,
            "ratio": rs, "present": present}


# ----------------------------------------------------------------------------- kicks, snares

def _ncc(x, T):
    L = len(T)
    num = fftconvolve(x, T[::-1], mode="valid")
    e = np.sqrt(np.maximum(np.convolve(x * x, np.ones(L), mode="valid"), 1e-20))
    return num / (e * np.linalg.norm(T))


def attack_times(x, sr, times, search=(-0.03, 0.04)):
    """The sharpest energy jump near each time: mean power over the next 3 ms against
    the previous 10 ms. Sample-accurate attacks, whatever the STFT frame said."""
    e = np.concatenate([[0.0], np.cumsum(x * x)])
    L1, L2 = max(1, int(0.003 * sr)), max(1, int(0.010 * sr))
    out = []
    for t in times:
        a = max(L2, int((t + search[0]) * sr))
        b = min(len(x) - L1, int((t + search[1]) * sr))
        if b <= a:
            continue
        n = np.arange(a, b)
        post = (e[n + L1] - e[n]) / L1
        pre = (e[n] - e[n - L2]) / L2
        out.append(n[np.argmax(post / (pre + 1e-4 * post.max() + 1e-20))] / sr)
    return np.array(out)


def learn_template(x, sr, onsets, pre=0.003, post=0.035):
    L = int(round((pre + post) * sr))
    segs = [x[int(round((t - pre) * sr)):int(round((t - pre) * sr)) + L] for t in onsets
            if int(round((t - pre) * sr)) >= 0 and int(round((t - pre) * sr)) + L <= len(x)]
    T = np.mean(segs, axis=0)
    T /= np.linalg.norm(T)
    sim = np.array([np.dot(s, T) / (np.linalg.norm(s) + 1e-12) for s in segs])
    keep = [s for s, c in zip(segs, sim) if c > 0.6]
    if len(keep) >= 3:
        T = np.mean(keep, axis=0)
        T /= np.linalg.norm(T)
    return T


def template_hits(song, band, seeds, glides, tp, speed, thr, min_gap, sr2=4000, rolls_iv=(),
                  pre=0.003, post=0.035):
    """Learn a template from the seeds' exact attacks, then find every hit by normalized
    cross-correlation; inside tape glides the template is warped by the measured speed."""
    lo, hi = band
    sos = butter(4, [lo, hi], "bp", fs=song.sr, output="sos") if lo else butter(6, hi, "lp", fs=song.sr, output="sos")
    x = librosa.resample(sosfiltfilt(sos, song.y), orig_sr=song.sr, target_sr=sr2)
    T = learn_template(x, sr2, attack_times(x, sr2, seeds), pre, post)
    L = len(T)
    score = np.zeros(len(x))
    ncc = _ncc(x, T)
    score[:len(ncc)] = ncc
    for g in glides:
        a, b = int(g["t0"] * sr2), int(g["t1"] * sr2)
        loc = np.interp(np.arange(a, b) / sr2, tp, speed)
        warped = np.zeros(b - a)
        for s in np.arange(0.3, 1.85, 0.05):
            n = int(L / s)
            Ts = np.interp(np.arange(n) * s, np.arange(L), T)
            seg = x[a:min(b + n, len(x))]
            if len(seg) <= n:
                continue
            c = _ncc(seg, Ts)[: b - a]
            m = np.abs(loc[:len(c)] - s) <= 0.08
            warped[:len(c)][m] = np.maximum(warped[:len(c)][m], c[m])
        score[a:b] = np.maximum(score[a:b], warped)
    # A beat-repeat retriggers the same attack every 32nd: only its first one is a new hit.
    for r in rolls_iv:
        score[int((r["t0"] + 0.02 - pre) * sr2):int((r["t1"] - 0.02 - pre) * sr2)] = 0.0
    peaks, _ = find_peaks(score, height=thr, distance=int(min_gap * sr2))
    return peaks / sr2 + pre, T, score


def kick_seeds(song):
    """Confident kicks: the punch band (80-250 Hz, where the 808 sweep passes) and the
    punch ratio (80-250 over 25-80 Hz) both jump, and the low end is loud."""
    fr = song.fr
    hi = pdb(song.band(80, 250))
    lo = pdb(song.band(25, 80))
    env = pdb(song.band(25, 150))
    top = np.percentile(env, 99.5)
    pr = hi - lo
    a, b, w = int(0.07 * fr), int(0.025 * fr), int(0.025 * fr)
    nov = np.full(song.nf, -99.0)
    for i in range(a, song.nf - w):
        rh = hi[i:i + w].max() - np.median(hi[i - a:i - b])
        rp = pr[i:i + w].max() - np.median(pr[i - a:i - b])
        if env[i:i + w].max() > top - 15:
            nov[i] = min(rh - 10.0, rp - 5.0)
    peaks, _ = find_peaks(nov, height=0.0, distance=int(0.15 * fr))
    return list(peaks / fr)


def snares(song, kick_t):
    fr = song.fr
    band = (song.f >= 1000) & (song.f < 8000)
    P = song.S[band] + 1e-12
    flat = np.exp(np.mean(np.log(P), axis=0)) / np.mean(P, axis=0)
    env = pdb(P.sum(axis=0))
    body = pdb(song.band(150, 300))
    a, b, w, s40 = int(0.07 * fr), int(0.02 * fr), int(0.03 * fr), int(0.045 * fr)
    nov = np.full(song.nf, -99.0)
    for i in range(a, song.nf - s40 - 2):
        if flat[i:i + 6].max() > 0.38:
            pk = env[i:i + w].max()
            ring = env[i + s40] - pk                # still ringing 45 ms later?
            nov[i] = min(pk - np.median(env[i - a:i - b]) - 10.0,
                         body[i:i + w].max() - np.median(body[i - a:i - b]) - 2.0,
                         ring + 9.0)
    peaks, _ = find_peaks(nov, height=0.0, distance=int(0.2 * fr))
    xh = sosfiltfilt(butter(4, 1000, "hp", fs=song.sr, output="sos"), song.y)
    return attack_times(xh, song.sr, peaks / fr, search=(-0.035, 0.035))


def classify_noise_hits(cand, body, sr2, dead, kick_t, grid, glides):
    """A snare is a ringing noise burst whose tonal body matches the learned snare body.
    Bursts that hug the edge of a dead silence are the mix switching back on, unless the
    body match is very strong. Bursts on a bar line where kicks begin are impacts."""
    def body_at(t):
        i = int(round((t - 0.003) * sr2))
        return float(body[max(0, i - 24):i + 25].max()) if i < len(body) else 0.0
    snares_, impacts = [], []
    bars = grid["bars"]
    for t in cand:
        on_bar = np.min(np.abs(bars - t)) < 0.02
        if on_bar and sum(1 for k in kick_t if t - 0.02 < k < t + 1.6) >= 3 and \
                not any(t - 1.0 < k < t - 0.05 for k in kick_t):
            impacts.append(float(t))           # a noise hit where the kicks (re)start
            continue
        b = body_at(t)
        near_edge = any(abs(t - d[1]) < 0.015 or abs(t - d[0]) < 0.015 for d in dead)
        in_glide = any(g["t0"] <= t <= g["t1"] for g in glides)
        if b >= (0.93 if near_edge else 0.75 if in_glide else 0.9):
            snares_.append(float(t))
    return np.array(snares_), np.array(impacts)


def snare_seeds(song):
    """Confident snares: a noise burst (flat 1-8 kHz spectrum) with a big rise."""
    fr = song.fr
    band = (song.f >= 1000) & (song.f < 8000)
    P = song.S[band] + 1e-12
    flat = np.exp(np.mean(np.log(P), axis=0)) / np.mean(P, axis=0)
    env = pdb(P.sum(axis=0))
    a, b, w = int(0.07 * fr), int(0.02 * fr), int(0.02 * fr)
    nov = np.full(song.nf, -99.0)
    for i in range(a, song.nf - w):
        if flat[i:i + 4].max() > 0.4:
            nov[i] = env[i:i + w].max() - np.median(env[i - a:i - b]) - 12.0
    peaks, _ = find_peaks(nov, height=0.0, distance=int(0.2 * fr))
    return list(peaks / fr)


def kick_dives(kick_t, tp, ratio, glides):
    """The 808's own pitch dive: low-end pitch 300 ms after each kick vs. 60 ms after."""
    out = []
    for tk in kick_t:
        if any(g["t0"] - 0.05 <= tk <= g["t1"] for g in glides):
            continue
        a, b = np.interp([tk + 0.06, tk + 0.30], tp, ratio)
        if np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0:
            out.append(12 * math.log2(b / a))
    return out


# ----------------------------------------------------------------------------- notes, chops

def falling_notes(tm, f0m, min_fall=3.0):
    """Voiced runs of the mid-band pitch, split at upward jumps, that fall >= min_fall st."""
    notes = []
    for a, b in runs(~np.isnan(f0m)):
        if b - a < 12:
            continue
        p = 12 * np.log2(f0m[a:b] / 440.0) + 69
        cuts = [0] + [k for k in range(1, len(p)) if p[k] - p[k - 1] > 1.5] + [len(p)]
        for c0, c1 in zip(cuts[:-1], cuts[1:]):
            if c1 - c0 < 12:
                continue
            q = median_filter(p[c0:c1], 3)
            start = float(np.median(q[:3]))
            k_low = int(np.argmin(q))
            fall = start - float(q[k_low])
            if fall >= min_fall:
                notes.append({"t0": float(tm[a + c0]), "t1": float(tm[a + c1 - 1]),
                              "t_bottom": float(tm[a + c0 + k_low]), "semitones": fall,
                              "start_midi": start})
    return notes


def chops(song, bars, P, dead_mask, glides=()):
    """16ths whose mid band (the lead) drops 12 dB under the bar median while the track
    itself is not dead: hard-gated chops."""
    mid = pdb(song.band(300, 1500))
    out = []
    for b in bars:
        steps = b + np.arange(16) * P / 4
        lv = []
        for s in steps:
            i0, i1 = int((s + 0.01) * song.fr), int((s + P / 4 - 0.01) * song.fr)
            lv.append(np.median(mid[i0:i1]) if i1 > i0 and i1 < song.nf else np.nan)
        lv = np.array(lv)
        if np.isnan(lv).any():
            continue
        med = np.median(lv)
        for s, v in zip(steps, lv):
            a = int(s * song.sr)
            in_glide = any(g["t0"] - 0.02 <= s <= g["t1"] for g in glides)
            if v < med - 7 and not in_glide and dead_mask[a:a + int(P / 4 * song.sr)].mean() < 0.5:
                out.append([float(s), float(s + P / 4)])
    return out


# ----------------------------------------------------------------------------- structure and window

def structure(song, grid, kick_t, glides, dead, rl):
    bars, P = grid["bars"], grid["period"]
    bar_len = 4 * P
    kick_bars = [i for i, b in enumerate(bars)
                 if ((kick_t >= b - 0.02) & (kick_t < b + bar_len - 0.02)).sum() >= 2]
    ev = []
    if kick_bars:
        ev.append({"type": "kick-in", "t": float(bars[kick_bars[0]])})
    for g in glides:
        ev.append({"type": g["type"], "t0": g["t0"], "t1": g["t1"]})
    low_db = pdb(song.band(25, 150))
    for i, b in enumerate(bars[1:], 1):
        if b >= song.dur - 0.1:
            continue
        before = low_db[max(0, int((b - 0.25) * song.fr)):int((b - 0.01) * song.fr)]
        after = low_db[int((b + 0.01) * song.fr):int((b + 0.25) * song.fr)]
        if len(before) == 0 or len(after) == 0:
            continue
        # A drop: the low end slams back in on a bar line, right after a dead gap or a riser.
        preceded = any(abs(d[1] - b) < 0.03 for d in dead) or any(
            g["type"] == "riser" and abs(g["t1"] - b) < 0.3 for g in glides)
        loud = np.median(after) > np.percentile(low_db, 95) - 6
        tape_start = any(g["type"] == "tape-start" and abs(g["t0"] - b) < 0.05 for g in glides)
        if preceded and loud and i in kick_bars and not tape_start:
            ev.append({"type": "drop", "t": float(b)})
    for d in dead:
        if d[1] >= song.dur - 0.01 and np.min(np.abs(bars - d[0])) < 0.03 and d[1] - d[0] > bar_len * 0.5:
            ev.append({"type": "hard-cut", "t": float(d[0])})
    for r in rl:
        ev.append({"type": "roll", "t0": r["t0"], "t1": r["t1"], "div": r["div"]})
    # Breakdown: bars after a tape-stop with no kicks and no low end.
    for g in glides:
        if g["type"] == "tape-stop":
            nxt = [b for b in bars if b >= g["t1"] - 0.05]
            if nxt and not any(abs(k - nxt[0]) < bar_len for k in kick_t if k >= nxt[0]):
                ev.append({"type": "breakdown", "t": float(nxt[0])})
    return sorted(ev, key=lambda e: e.get("t", e.get("t0"))), kick_bars


def choose_window(song, bars, events, P):
    bar_len = 4 * P
    best = None
    for k in range(len(bars)):
        w0 = bars[k]
        w1 = w0 + WINDOW_BARS * bar_len
        if w1 > song.dur + 0.02:
            break
        inside = lambda e: w0 - 0.01 <= e.get("t", e.get("t0")) < w1 - 0.01
        types = [e["type"] for e in events if inside(e)]
        need = all(t in types for t in ("tape-stop", "drop", "power-down"))
        score = 10 * need + sum(t in types for t in ("tape-start", "riser", "roll", "kick-in", "breakdown"))
        score += 3 * any(e["type"] == "hard-cut" and abs(e["t"] - w1) < 0.03 for e in events)
        score -= 5 * any(e["type"] == "hard-cut" and inside(e) and e["t"] < w1 - 0.03 for e in events)
        if best is None or score > best[0]:
            best = (score, k, w0, w1, sorted(set(types)))
    if best is None:
        raise SystemExit("song shorter than the window")
    score, k, w0, w1, types = best
    return {"bar_index": int(k), "t0": float(w0), "t1": float(w1), "score": int(score), "contains": types}


# ----------------------------------------------------------------------------- frame mapping

def frame_channels(song, win, grid, kick_t, snare_t, dead_mask, tp, speed, rl, falls, chop_iv):
    w0, w1 = win["t0"], win["t1"]
    F = int(round((w1 - w0) * FPS))
    spf = song.sr // FPS
    i0 = int(round(w0 * song.sr))
    tf = w0 + np.arange(F) / FPS

    def frame_mean(t, series):
        edges = np.searchsorted(t, np.concatenate([tf, [tf[-1] + 1.0 / FPS]]))
        out = np.empty(F)
        for i in range(F):
            a, b = edges[i], edges[i + 1]
            out[i] = series[a:b].mean() if b > a else np.interp(tf[i], t, series)
        return out

    ch = {"t": tf - w0}
    a = song.y2[i0:i0 + F * spf].reshape(F, spf, 2)
    ch["rms_db"] = 10 * np.log10(np.maximum((a ** 2).mean(axis=(1, 2)), 1e-12))
    ch["rms"] = np.clip((ch["rms_db"] + 50.0) / 50.0, 0, 1)
    for name, (lo, hi) in {"sub": (25, 70), "low": (70, 250), "mid": (250, 2000), "high": (2000, 12000)}.items():
        ch[name] = norm01(frame_mean(song.t, pdb(song.band(lo, hi))))
    cen = librosa.feature.spectral_centroid(S=np.sqrt(song.S), freq=song.f)[0]
    ch["centroid_hz"] = frame_mean(song.t, cen)
    ch["centroid"] = np.clip(np.log2(np.maximum(ch["centroid_hz"], 1) / 100.0) / np.log2(80.0), 0, 1)
    oenv = librosa.onset.onset_strength(y=song.y, sr=song.sr, hop_length=HOP)[: song.nf]
    ch["onset"] = norm01(frame_mean(song.t[: len(oenv)], oenv), 5, 99.5)
    ch["silent"] = dead_mask[i0:i0 + F * spf].reshape(F, spf).mean(axis=1)

    def env_from(times, tau):
        e = np.zeros(F)
        hit = np.zeros(F, int)
        for tk in times:
            fi = int(math.floor((tk - w0) * FPS + 0.5))    # the frame on screen when it lands
            if fi >= F or fi < -int(5 * tau * FPS):
                continue
            if fi >= 0:
                hit[fi] = 1
            k = np.arange(F)
            e = np.maximum(e, np.where(k >= fi, np.exp(-np.maximum(k - fi, 0) / FPS / tau), 0.0))
        return e, hit

    ch["kick"], ch["kick_hit"] = env_from(kick_t, 0.12)
    ch["snare"], ch["snare_hit"] = env_from(snare_t, 0.10)

    ch["speed"] = frame_mean(tp, speed)
    ch["tape"] = np.concatenate([[0.0], np.cumsum(ch["speed"][:-1]) / FPS])
    state = np.full(F, "PLAY", dtype=object)
    state[ch["speed"] < 0.97] = "SLOW"
    state[ch["speed"] > 1.03] = "FFWD"
    state[ch["speed"] < 0.02] = "STOP"
    ch["readout"] = state

    ch["roll"] = np.zeros(F)
    ch["roll_div_frames"] = np.zeros(F)
    for r in rl:
        m = (tf >= r["t0"] - 0.5 / FPS) & (tf < r["t1"] - 0.5 / FPS)
        ch["roll"][m] = 1.0
        ch["roll_div_frames"][m] = r["div"] * FPS
    ch["chop"] = np.zeros(F)
    for c0, c1 in chop_iv:
        ch["chop"][(tf >= c0 - 0.5 / FPS) & (tf < c1 - 0.5 / FPS)] = 1.0
    ch["fall"] = np.zeros(F)
    ch["fall_semis"] = np.zeros(F)
    for nte in falls:
        m = (tf >= nte["t0"] - 0.5 / FPS) & (tf < nte["t1"])
        u = (tf[m] - nte["t0"]) / max(nte["t1"] - nte["t0"], 1e-3)
        ch["fall"][m] = np.maximum(ch["fall"][m], np.clip(u, 0, 1))
        ch["fall_semis"][m] = nte["semitones"]

    P = grid["period"]
    beat_pos = (tf - w0) / P
    ch["beat"] = np.floor(beat_pos + 1e-6).astype(int)
    ch["beat_phase"] = beat_pos - ch["beat"]
    ch["bar"] = ch["beat"] // 4
    return ch


# ----------------------------------------------------------------------------- canyon texture

def spectrogram_texture(song, w0, w1, n_bins=256, bpo=28, fmin=25.0, hop=256):
    """Log-frequency (VQT) spectrogram of the window: 25 Hz to 14 kHz in 256 rows, so the
    sub and bass get a third of the canyon's width instead of a mel scale's sliver."""
    a = song.y[int(round(w0 * song.sr)):int(round(w1 * song.sr))]
    V = np.abs(librosa.vqt(a, sr=song.sr, hop_length=hop, fmin=fmin, n_bins=n_bins, bins_per_octave=bpo))
    D = librosa.amplitude_to_db(V, ref=np.max, top_db=80.0)
    return ((D + 80.0) / 80.0).astype(np.float32)   # (bins, cols), 0..1, low frequencies first


# ----------------------------------------------------------------------------- main

def main():
    wav, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    song = Song(wav)

    dead, dead_mask = dead_silences(song)
    grid = tempo_grid(song)
    on, _ = onsets(song)
    rl = rolls(song, grid["beats"], grid["period"], dead_mask)

    tp, f0_low = pitch_track(song, (0, 150), LOW_FMIN, 100.0, 4000, 1024)
    sp = tape_speed(song, tp, f0_low, dead_mask, rl, grid["beats"])

    kick_t, kick_T, kick_score = template_hits(song, (0, 400), kick_seeds(song), sp["glides"], tp,
                                               sp["speed"], thr=KICK_NCC, min_gap=0.15, rolls_iv=rl)
    cand = snares(song, kick_t)
    _, _, body = template_hits(song, (120, 600), cand, sp["glides"], tp, sp["speed"], thr=0.99, min_gap=0.2,
                               sr2=8000, pre=0.003, post=0.045)
    snare_t, impact_t = classify_noise_hits(cand, body, 8000, dead, kick_t, grid, sp["glides"])
    grid = snap_grid(grid, np.array([k for k in kick_t if not any(g["t0"] <= k <= g["t1"] for g in sp["glides"])]))
    dives = kick_dives(kick_t, tp, sp["ratio"], sp["glides"])

    tm, f0_mid = pitch_track(song, (120, 1800), 90.0, 1100.0, 8000, 1024)
    falls = falling_notes(tm, f0_mid, min_fall=2.5)
    chop_iv = chops(song, grid["bars"], grid["period"], dead_mask, sp["glides"])
    events, kick_bars = structure(song, grid, kick_t, sp["glides"], dead, rl)
    win = choose_window(song, grid["bars"], events, grid["period"])

    w0s, w1s = int(round(win["t0"] * song.sr)), int(round(win["t1"] * song.sr))
    sf.write(outdir / "window.wav", song.y2[w0s:w1s].astype(np.float32), song.sr, subtype="PCM_24")

    ch = frame_channels(song, win, grid, kick_t, snare_t, dead_mask, tp, sp["speed"], rl, falls, chop_iv)
    np.save(outdir / "spectrogram_window.npy", spectrogram_texture(song, win["t0"], win["t1"]))
    np.savez(outdir / "channels.npz", **{k: v for k, v in ch.items() if v.dtype != object},
             readout=np.array([str(s) for s in ch["readout"]]))
    np.savez(outdir / "tracks.npz", tp=tp, f0_low=f0_low, speed=sp["speed"], ratio=sp["ratio"],
             tm=tm, f0_mid=f0_mid, kick_template=kick_T if kick_T is not None else np.zeros(1))

    wf = lambda t: int(math.floor((t - win["t0"]) * FPS + 0.5))   # song time -> window frame
    w_events = []
    for e in events:
        e2 = dict(e)
        for key in ("t", "t0", "t1"):
            if key in e:
                e2["frame" if key == "t" else "frame" + key[1:]] = wf(e[key])
        w_events.append(e2)
    report = {
        "file": str(wav), "duration_s": song.dur, "sr": song.sr,
        "bpm": grid["bpm"], "beat_s": grid["period"], "phase_correction_s": grid.get("phase_correction_s", 0.0),
        "downbeat_scores": grid["downbeat_scores"], "bars_s": [float(b) for b in grid["bars"]],
        "n_onsets": int(len(on)), "onsets_s": [float(x) for x in on],
        "kicks_s": [float(x) for x in kick_t], "snares_s": [float(x) for x in snare_t],
        "impacts_s": [float(x) for x in impact_t],
        "kick_dive_semitones_median": float(np.median(dives)) if dives else None,
        "rolls": rl, "dead_silences_s": dead,
        "root_hz": sp["root_hz"], "root_midi": sp["root_midi"], "glides": sp["glides"],
        "falling_notes": falls, "chops_s": chop_iv, "events": w_events, "window": win,
        "frames": int(len(ch["t"])), "fps": FPS,
        "silent_frames": [int(i) for i in np.nonzero(ch["silent"] > 0.5)[0]],
        "kick_frames": [int(i) for i in np.nonzero(ch["kick_hit"])[0]],
    }
    (outdir / "analysis.json").write_text(json.dumps(report, indent=1))

    print(f"tempo {grid['bpm']:.3f} bpm, beat {grid['period'] * 1000:.2f} ms, {len(grid['bars'])} bars, "
          f"first bar {grid['bars'][0]:+.4f} s (phase corrected {report['phase_correction_s'] * 1000:+.1f} ms)")
    print(f"onsets {len(on)}, kicks {len(kick_t)}, snares {len(snare_t)}, impacts {len(impact_t)}, "
          f"808 dive median {report['kick_dive_semitones_median']:.2f} st")
    print(f"root {sp['root_hz']:.2f} Hz (midi {sp['root_midi']})")
    for g in sp["glides"]:
        print(f"  glide {g['type']:10s} {g['t0']:6.2f}-{g['t1']:6.2f} s  speed {g['speed_start']:.2f} -> "
              f"{g['speed_end']:.2f} (extreme {g['speed_extreme']:.2f})")
    print("rolls: " + ", ".join(f"{r['t0']:.2f} ({round(grid['period'] / r['div'])}/beat {r['score']:.2f})" for r in rl))
    print(f"dead silences {len(dead)}, falling notes {len(falls)}, chops {len(chop_iv)}")
    print("events: " + "; ".join(f"{e['type']}@{e.get('t', e.get('t0')):.2f}" for e in events))
    print(f"window: bars {win['bar_index']}..{win['bar_index'] + WINDOW_BARS - 1} [{win['t0']:.4f}, {win['t1']:.4f}] s, "
          f"{report['frames']} frames, score {win['score']}, contains {win['contains']}")


if __name__ == "__main__":
    main()
