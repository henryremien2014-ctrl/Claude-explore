#!/usr/bin/env python3
"""MAGNETIC glitch post, keyed to the analysis.

    post.py renders_dir out_dir [--width W] [--frames a-b] [--png-input]

Per output frame:
  1. source  - the frame plan picks the rendered frame (retrigger stutters, frame-rate holds,
               black on the dead silence)
  2. lens    - in scene-linear light: lens dispersion, bloom, film halation
  3. AgX     - Blender's own OCIO config, 'AgX - Punchy'
  4. trip    - closed-eye visuals, feedback tunnel, pixel-sort melts, datamosh, 6-fold kaleidoscope,
               tracers, VHS tracking + red pitch-down drain + sagging picture, slice displacement,
               chroma split, negative strobe, breathing warp
  5. grade   - the magma grade (each pixel's hue pulled toward the magma ramp at its own OKLab
               lightness, off-palette hues folded in), grain, vignette, the tape-speed readout
"""
import argparse
import json
import math
import os
from pathlib import Path

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")    # must be set before cv2 loads
import cv2  # noqa: E402
import numpy as np
import PyOpenColorIO as OCIO
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
AOUT = ROOT / "analysis" / "out"
OCIO_CFG = "/home/user/.venvs/mag/lib/python3.11/site-packages/bpy/4.5/datafiles/colormanagement/config.ocio"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MAGMA_SRGB = [(0.00, "000004"), (0.10, "140e36"), (0.20, "3b0f70"), (0.30, "641a80"), (0.40, "8c2981"),
              (0.50, "b73779"), (0.60, "de4968"), (0.70, "f7705c"), (0.80, "fe9f6d"), (0.90, "fecf92"),
              (1.00, "fcfdbf")]


def magma_lut(n=1024):
    xs = np.array([p for p, _ in MAGMA_SRGB])
    cols = np.array([[int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] for _, h in MAGMA_SRGB])
    t = np.linspace(0, 1, n)
    return np.stack([np.interp(t, xs, cols[:, c]) for c in range(3)], 1).astype(np.float32)


LUT = magma_lut()


def magma(x):
    return LUT[np.clip((x * (len(LUT) - 1)).astype(np.int32), 0, len(LUT) - 1)]


def lum(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def smoothstep(e0, e1, x):
    u = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return u * u * (3 - 2 * u)


_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],          # OKLab (Ottosson 2020)
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
_M1i, _M2i = np.linalg.inv(_M1).astype(np.float32), np.linalg.inv(_M2).astype(np.float32)


def to_oklab(srgb):
    lin = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return np.cbrt(lin @ _M1.T) @ _M2.T


def from_oklab(lab):
    lin = np.maximum(((lab @ _M2i.T) ** 3) @ _M1i.T, 0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


class Post:
    def __init__(self, width):
        self.W, self.H = width, width * 9 // 16
        self.s = width / 1920.0
        self.plan = json.loads((AOUT / "frameplan.json").read_text())
        self.C = dict(np.load(AOUT / "choreo.npz"))
        self.ch = dict(np.load(AOUT / "channels.npz"))
        self.readout = [str(x) for x in self.ch["readout"]]
        self.F = len(self.plan["src"])
        mlab = to_oklab(LUT)
        self.mL, self.ma, self.mb = mlab[:, 0], mlab[:, 1], mlab[:, 2]     # lightness rises monotonically
        cfg = OCIO.Config.CreateFromFile(OCIO_CFG)
        dvt = OCIO.DisplayViewTransform()
        dvt.setSrc(cfg.getRoleColorSpace("scene_linear"))
        dvt.setDisplay("sRGB")
        dvt.setView("AgX")
        vp = OCIO.LegacyViewingPipeline()
        vp.setDisplayViewTransform(dvt)
        vp.setLooksOverrideEnabled(True)
        vp.setLooksOverride("AgX - Punchy")
        self.agx = vp.getProcessor(cfg).getDefaultCPUProcessor()
        lin = OCIO.ColorSpaceTransform()
        lin.setSrc("sRGB")
        lin.setDst(cfg.getRoleColorSpace("scene_linear"))
        self.to_lin = cfg.getProcessor(lin).getDefaultCPUProcessor()
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        self.xx, self.yy = xx, yy
        self.cx, self.cy = self.W / 2.0, self.H / 2.0
        self.r = np.hypot((xx - self.cx) / self.cx, (yy - self.cy) / self.cx)          # 1 at the side edges
        self.theta = np.arctan2(yy - self.cy, xx - self.cx)
        self.vign = (1.0 - 0.30 * np.clip(self.r / 1.15, 0, 1) ** 2.4)[..., None]
        self.font = ImageFont.truetype(FONT, max(10, int(round(22 * self.s))))
        self.phos = self.phosphene_events()
        self.prev_clean = None          # previous output before grain/vignette, for temporal effects
        self.trail = None
        self.fb = None
        self.prev_src = None

    # ------------------------------------------------------------------ io
    def load(self, d, f, png_input):
        if png_input:
            p = d / f"f{f:04d}.png"
            img = np.asarray(Image.open(p).convert("RGB"), np.float32) / 255.0
            if img.shape[1] != self.W:
                img = cv2.resize(img, (self.W, self.H), interpolation=cv2.INTER_AREA)
            return img                                                  # already through Blender's AgX
        p = d / f"f{f:04d}.exr"
        img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise FileNotFoundError(p)
        img = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32)
        if img.shape[1] != self.W:
            img = cv2.resize(img, (self.W, self.H), interpolation=cv2.INTER_AREA)
        return img

    # ------------------------------------------------------------------ lens (scene linear)
    def dispersion(self, lin, amt):
        out = lin.copy()
        for c, k in ((0, 1.0 + amt), (2, 1.0 - amt)):
            mx = (self.xx - self.cx) / k + self.cx
            my = (self.yy - self.cy) / k + self.cy
            out[..., c] = cv2.remap(lin[..., c], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return out

    def blur(self, img, sigma):
        """Gaussian blur; wide ones run on a downsampled copy (same look, a fraction of the cost)."""
        d = max(1, int(sigma / 6))
        if d == 1:
            return cv2.GaussianBlur(img, (0, 0), max(sigma, 0.6))
        h, w = img.shape[:2]
        small = cv2.resize(img, (w // d, h // d), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), sigma / d)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

    def bloom(self, lin, strength):
        hi = np.maximum(lin - 1.5, 0.0)                     # only what is brighter than paper white blooms
        acc = np.zeros_like(lin)
        for r, w in ((3, 1.0), (9, 0.8), (24, 0.6), (64, 0.4)):
            acc += w * self.blur(hi, r * self.s)
        return lin + strength * acc / 2.8

    def halation(self, lin, strength):
        hi = np.maximum(lum(lin) - 0.75, 0.0)
        g = cv2.GaussianBlur(hi, (0, 0), max(7 * self.s, 0.6))[..., None]
        return lin + strength * g * np.array([1.0, 0.22, 0.10], np.float32)

    # ------------------------------------------------------------------ trip
    def phosphene_events(self):
        """Intro phosphenes: soft sparks and rings of light born on the intro's onsets (more as the
        filter opens), drifting outward through the dark around the eye. Deterministic per loop."""
        rng = np.random.default_rng(11)
        o, sweep = self.C["onset_rel"], self.C["sweep"]
        end = self.plan["cev"][0]
        ev = []
        for f in range(2, end):
            peak = o[f] > 0.25 and o[f] >= o[f - 1] and o[f] >= o[min(f + 1, end - 1)]
            n = int(round((2 + 7 * o[f]) * (0.4 + 0.6 * sweep[f]))) if peak else int(rng.random() < 0.35)
            for _ in range(n):
                ang = rng.uniform(-np.pi, np.pi)
                rad = rng.uniform(0.32, 1.05)                           # clear of the eye in the middle
                ev.append(dict(f0=f, life=rng.uniform(7, 18), ang=ang, rad=rad, drift=rng.uniform(0.002, 0.008),
                               sig=rng.uniform(2.5, 9.0), ring=rng.random() < 0.3, col=rng.uniform(0.55, 0.97),
                               amp=rng.uniform(0.5, 1.0)))
        return ev

    def phosphenes(self, img, f, amt):
        can = np.zeros_like(img)
        for e in self.phos:
            age = f - e["f0"]
            if age < 0 or age > 2.5 * e["life"]:
                continue
            a = amt * e["amp"] * (1 - np.exp(-(age + 1) / 1.2)) * np.exp(-age / (e["life"] / 2.2))
            if a < 0.01:
                continue
            rr = e["rad"] + e["drift"] * age
            x = self.cx + np.cos(e["ang"]) * rr * self.cx
            y = self.cy + np.sin(e["ang"]) * rr * self.cx
            sig = e["sig"] * self.s * 2.0
            ring_r = (6 + 2.2 * age) * self.s * 2.0 if e["ring"] else 0.0
            R = int(ring_r + 3.5 * sig) + 2
            x0, x1 = max(int(x) - R, 0), min(int(x) + R + 1, self.W)
            y0, y1 = max(int(y) - R, 0), min(int(y) + R + 1, self.H)
            if x0 >= x1 or y0 >= y1:
                continue
            d = np.hypot(self.xx[y0:y1, x0:x1] - x, self.yy[y0:y1, x0:x1] - y)
            g = np.exp(-0.5 * ((d - ring_r) / (sig * (0.35 if e["ring"] else 1.0))) ** 2)
            can[y0:y1, x0:x1] += a * g[..., None] * LUT[int(e["col"] * (len(LUT) - 1))]
        dark = np.clip(1 - lum(img), 0, 1)[..., None] ** 1.5
        return np.clip(img + can * dark, 0, 1)

    def cev(self, img, f, u, pulse):
        """Closed-eye visuals: light through the lids (deep red) and a Kluver form constant. A hexagonal
        lattice laid out in cortical (log-polar) coordinates, so in the visual field it is a honeycomb
        tunnel streaming outward and twisting into a spiral; it strobes with the roll."""
        rho = np.log(self.r + 1e-3)
        th = self.theta + (0.9 + 1.6 * u) * rho                          # log-spiral shear, stays 2pi-periodic
        flow = 2.2 * u + 0.35 * f / 30.0                                 # the tunnel streams outward
        K = 10.392                                                       # 12 * sin(60 deg): hex lattice, integer in theta
        v = (np.cos(12 * th) + np.cos(-K * (rho - flow) - 6 * th) + np.cos(K * (rho - flow) - 6 * th) + 1.5) / 4.5
        fade = smoothstep(0.03, 0.22, self.r)[..., None]                 # fade where the cells get too fine
        cores = smoothstep(0.80, 0.97, v)[..., None]                     # gold cores on the lattice points
        web = np.exp(-((v - 0.42) / 0.035) ** 2)[..., None]              # a magenta contour web between them
        L = np.clip(lum(img) * 1.6, 0, 1)
        lid = magma(np.clip(0.18 + 0.30 * L, 0, 1)) * (0.25 + 0.75 * L[..., None])   # the closed eye, glowing red
        glow = fade * (0.95 * cores * magma(np.array([0.92]))[0]
                       + 0.8 * web * magma(np.array([0.56 + 0.18 * pulse]))[0])
        core = np.exp(-(self.r / 0.10) ** 2)[..., None] * magma(np.array([0.93]))[0]   # light at the tunnel's end
        amt = smoothstep(0.0, 0.25, u) * (0.55 + 0.45 * pulse)
        return np.clip(lid * (1 - 0.5 * amt) + amt * (1.1 * glow + 0.8 * core), 0, 1)

    def retrigger(self, img, e):
        """The roll's retrigger accent: a small zoom punch and a flash on every 3-frame slice."""
        if e < 0.01:
            return img
        M = cv2.getRotationMatrix2D((self.cx, self.cy), 0.0, 1.0 + 0.035 * e)
        img = cv2.warpAffine(img, M, (self.W, self.H), borderMode=cv2.BORDER_REFLECT)
        return np.clip(img * (1 + 0.30 * e), 0, 1)

    def feedback(self, img, amt, f):
        if self.fb is None:
            self.fb = img.copy()
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((self.cx, self.cy), 1.6, 1.0 / 1.075)
        fb = cv2.warpAffine(self.fb, M, (w, h), borderMode=cv2.BORDER_CONSTANT)
        out = np.maximum(img, fb * (0.55 + 0.4 * amt) * amt)
        self.fb = out
        return out

    def pixel_sort(self, img, amt):
        """Melt: inside each column, runs of bright pixels are sorted so the brightest sink."""
        L = lum(img)
        lo = 0.75 - 0.55 * amt
        mask = (L > lo) & (L < 0.995)
        h, w = mask.shape
        mT = mask.T
        start = mT & ~np.concatenate([np.zeros((w, 1), bool), mT[:, :-1]], 1)
        gid = np.cumsum(start.ravel()).reshape(w, h) * mT
        idx = np.nonzero(mT.ravel())[0]
        if len(idx) == 0:
            return img
        g = gid.ravel()[idx]
        lv = L.T.ravel()[idx]
        order = np.lexsort((lv, g))
        flat = img.transpose(1, 0, 2).reshape(-1, 3).copy()
        flat[idx] = flat[idx[order]]
        sorted_img = flat.reshape(w, h, 3).transpose(1, 0, 2)
        sm = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.0)[..., None]
        return img * (1 - sm * amt) + sorted_img * (sm * amt)

    def datamosh(self, cur_src, prev_src, k, n):
        """P-frames without their I-frame: the new shot's motion drags the old shot's pixels."""
        g0 = cv2.cvtColor((prev_src * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        g1 = cv2.cvtColor((cur_src * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        sc = 0.5 if self.W > 960 else 1.0
        if sc != 1.0:
            g0, g1 = cv2.resize(g0, None, fx=sc, fy=sc), cv2.resize(g1, None, fx=sc, fy=sc)
        dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        flow = dis.calc(g1, g0, None)                                   # where each new pixel came from
        if sc != 1.0:
            flow = cv2.resize(flow, (self.W, self.H)) / sc
        flow *= 1.6                                                      # exaggerated bleed
        mx = self.xx + flow[..., 0]
        my = self.yy + flow[..., 1]
        moshed = cv2.remap(self.prev_clean, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        resolve = ((k + 1) / (n + 1)) ** 2.2
        return moshed * (1 - resolve) + cur_src * resolve

    def kaleido(self, img, rot, n=6):
        dx, dy = self.xx - self.cx, self.yy - self.cy
        r = np.hypot(dx, dy)
        th = np.arctan2(dy, dx) - rot
        wedge = 2 * np.pi / n
        t = np.mod(th, wedge)
        t = np.where(t > wedge / 2, wedge - t, t) - np.pi / 2 + wedge / 2
        sx = (self.cx + r * np.cos(t)).astype(np.float32)
        sy = (self.cy + r * np.sin(t)).astype(np.float32)
        return cv2.remap(img, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def tracers(self, img, amt):
        if self.trail is None:
            self.trail = img.copy()
        self.trail = np.maximum(img, self.trail * (0.62 + 0.25 * amt))
        return np.maximum(img, self.trail * 0.7 * amt)

    def vhs(self, img, amt, f):
        rng = np.random.default_rng(1000 + f)
        h, w = img.shape[:2]
        rows = np.arange(h) / h
        out = img.copy()
        for k in range(2):
            by = ((f * 0.045 + 0.47 * k) % 1.3) - 0.15
            band = np.exp(-((rows - by) / (0.035 + 0.02 * k)) ** 2) * amt
            shift = (rng.normal(0, 1, h) * 28 * self.s * band + band * 18 * self.s).astype(np.int32)
            cols = (np.arange(w)[None, :] - shift[:, None]) % w
            out = out[np.arange(h)[:, None], cols]
            noise = rng.random((h, w)).astype(np.float32) * band[:, None] * 0.55
            out = np.clip(out + noise[..., None] * np.array([1.0, 0.75, 0.8], np.float32), 0, 1)
        jitter = (rng.normal(0, 1, h) * 2.0 * self.s * amt).astype(np.int32)
        cols = (np.arange(w)[None, :] - jitter[:, None]) % w
        return out[np.arange(h)[:, None], cols]

    def drain(self, img, amt, front):
        """As the pitch dives the colour drains to red, from the top of the picture down."""
        L = lum(img)
        red = L[..., None] * np.array([0.95, 0.10, 0.07], np.float32)
        mask = (1.0 - smoothstep(front - 0.25, front, self.yy / self.H))[..., None]
        return img * (1 - amt * mask) + red * (amt * mask)

    def sag(self, img, amt):
        """The picture sags like warm film: the middle droops more than the sides."""
        dx = (self.xx - self.cx) / self.cx
        dy = amt * self.H * 0.16 * (1 - dx ** 2) * (self.yy / self.H) ** 0.6
        return cv2.remap(img, self.xx, self.yy - dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    def slices(self, img, f, amt):
        rng = np.random.default_rng(5000 + f)
        out = img.copy()
        h, w = img.shape[:2]
        y = 0
        while y < h:
            bh = int(rng.integers(max(2, h // 60), max(3, h // 9)))
            if rng.random() < 0.55 * amt + 0.2:
                out[y:y + bh] = np.roll(img[y:y + bh], int(rng.normal(0, 0.06) * w * amt), axis=1)
            y += bh
        return out

    def chroma(self, img, px):
        d = int(round(px))
        if d == 0:
            return img
        out = img.copy()
        out[..., 0] = np.roll(img[..., 0], d, axis=1)
        out[..., 2] = np.roll(img[..., 2], -d, axis=1)
        return out

    def negative(self, img):
        return magma(np.clip(1.0 - lum(img), 0, 1) ** 1.2)

    def breathe(self, img, k):
        if abs(k) < 1e-4:
            return img
        rr = np.clip(self.r, 0, 1.4)
        scale = 1.0 + k * (1.0 - 0.5 * rr ** 2)
        mx = (self.xx - self.cx) / scale + self.cx
        my = (self.yy - self.cy) / scale + self.cy
        return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # ------------------------------------------------------------------ grade
    def magma_grade(self, img, k_hue=0.25, k_chroma=0.15):
        """Pull every pixel's hue toward the magma hue at its own OKLab lightness. Lightness is kept
        (blacks stay black), chroma meets the ramp partway, in-palette hues (violet, magenta, red,
        orange, gold) drift a little and off-palette ones (greens, cyans, blues) fold all the way in."""
        lab = to_oklab(np.clip(img, 0, 1).astype(np.float32))
        L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
        ma, mb = np.interp(L, self.mL, self.ma), np.interp(L, self.mL, self.mb)
        C, h = np.hypot(a, b), np.arctan2(b, a)
        dh = (np.arctan2(mb, ma) - h + np.pi) % (2 * np.pi) - np.pi      # shortest way round to the ramp's hue
        deg = np.degrees(h) % 360.0                     # OKLab hue: red 29, orange 55, yellow 110, green 142,
        off = np.clip(np.minimum(deg - 105.0, 280.0 - deg) / 20.0, 0, 1)    # cyan 195, blue 264, magenta 328
        h2 = h + (k_hue + (1 - k_hue) * off) * dh
        C2 = C * (1 - k_chroma) + np.hypot(ma, mb) * k_chroma
        out = np.stack([L, C2 * np.cos(h2), C2 * np.sin(h2)], -1).astype(np.float32)
        return np.clip(from_oklab(out), 0, 1).astype(np.float32)

    def grain(self, img, f):
        rng = np.random.default_rng(9000 + f)
        n = rng.normal(0, 1, (self.H // 2 + 1, self.W // 2 + 1)).astype(np.float32)
        n = cv2.resize(n, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
        L = lum(img)[..., None]
        amp = 0.024 * smoothstep(0.0, 0.10, L) * (0.4 + 0.6 * (1 - L))      # grain lives in the mids; black stays black
        return np.clip(img + n[..., None] * amp, 0, 1)

    def draw_readout(self, img, f):
        state = self.readout[f]
        sp = float(self.C["speed"][f])
        glyph = {"PLAY": ">", "SLOW": ">", "STOP": "#", "FFWD": ">>"}[state]
        txt = f"{state} {glyph} {sp:4.2f}x"
        pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        d = ImageDraw.Draw(pil)
        x, y = int(46 * self.s), self.H - int(64 * self.s)
        col = tuple(int(c * 255) for c in LUT[int(0.92 * (len(LUT) - 1))])
        d.text((x, y), txt, font=self.font, fill=col)
        if state != "STOP" or (f // 8) % 2 == 0:                       # STOP blinks
            r = max(2, int(5 * self.s))
            cy = y + int(13 * self.s)
            dc = tuple(int(c * 255) for c in LUT[int(0.62 * (len(LUT) - 1))])
            d.ellipse((x - 4 * r, cy - r, x - 2 * r, cy + r), fill=dc)
        return np.asarray(pil, np.float32) / 255.0

    # ------------------------------------------------------------------ one frame
    def frame(self, f, src_dir, png_input):
        P, C, ch = self.plan, self.C, self.ch
        F = self.F
        s = P["src"][f]
        speed = float(C["speed"][f])
        kick, snare = float(C["kick_seam"][f]), float(C["snare_seam"][f])   # blended into frame 0 at the seam
        if P["black"][f]:
            img = np.zeros((self.H, self.W, 3), np.float32)
            src_img = img
        else:
            lin = self.load(src_dir, s, png_input)
            lin = self.dispersion(lin, 0.0018 + 0.004 * kick)
            if png_input:                                               # display-referred stand-in
                lin = self.bloom(lin * 1.1, 0.12 + 0.15 * kick)
                lin = self.halation(lin, 0.2)
                img = np.clip(lin, 0, 1).astype(np.float32)
            else:
                lin = self.bloom(lin, 0.22 + 0.25 * kick)
                lin = self.halation(lin, 0.35)
                img = lin.astype(np.float32).copy()
                self.agx.applyRGB(img)
                img = np.clip(img, 0, 1)
            src_img = img.copy()

        def inside(rng_):
            return rng_[0] <= f < rng_[1]

        # the roll's retrigger stutter accent (the frame plan repeats each 3-frame slice)
        accent = 0.0
        for a, b in P["rolls"]:
            if a <= f < b:
                accent = (1.0, 0.45, 0.15)[(f - a) % 3] * (1.0 if (f - a) % 6 < 3 else 0.7)
        # intro phosphenes, rising with the filter sweep
        if f < P["cev"][0] and not P["black"][f]:
            amt = smoothstep(1, 14, f) * (0.35 + 0.65 * float(C["sweep"][f]))
            if amt > 0.005:
                img = self.phosphenes(img, f, 0.9 * amt)
        # closed-eye visuals
        if inside(P["cev"]) and not P["black"][f]:
            u = (f - P["cev"][0]) / max(P["cev"][1] - P["cev"][0], 1)
            img = self.cev(img, f, u, accent)
        # datamosh on chosen cuts
        for c in P["datamosh"]:
            if c <= f < c + 8 and self.prev_clean is not None and self.prev_src is not None and not P["black"][f]:
                img = self.datamosh(src_img, self.prev_src, f - c, 8)
        # bullet time: every falling note melts the picture
        for fall in P["falls"]:
            if fall <= f < fall + 14:
                img = self.pixel_sort(img, smoothstep(0, 1, (f - fall + 1) / 10.0) * (1 - smoothstep(10, 14, f - fall)))
        # the riser: feedback tunnel
        if inside(P["riser"]):
            u = (f - P["riser"][0]) / (P["riser"][1] - P["riser"][0])
            img = self.feedback(img, u ** 1.4, f)
        else:
            self.fb = None
        # tracers in the groove and drop 2
        groove = (P["cuts"][2] <= f < P["stop"][0]) or (P["drops"][1] <= f < P["tape_start"][0] - 12)
        if groove:
            img = self.tracers(img, 0.6 + 0.4 * kick)
        else:
            self.trail = None
        # tape-start: rotating 6-fold kaleidoscope with a spectral colour shift (fades out into the dive)
        ks = P["tape_start"][0]
        kamt = smoothstep(ks - 1, ks + 2, f) * (1 - smoothstep(P["dive"][0] + 2, P["dive"][0] + 12, f))
        if kamt > 0.001:
            rot = 2 * np.pi * (f - ks) / 72.0
            k_img = self.kaleido(img, rot)
            L = lum(k_img)
            shift = (float(ch["centroid"][f]) * 0.6 + (f - ks) / 40.0) % 1.0
            spec = magma((L * 0.85 + shift) % 1.0)
            k_img = k_img * 0.45 + spec * 0.55 * np.clip(L[..., None] * 1.6, 0, 1)
            img = img * (1 - kamt) + k_img * kamt
        # pitch dives: VHS tracking, red drain, and (power-down) the sagging picture
        for key, sag_on in (("stop", False), ("powerdown", True)):
            a, b = P[key]
            if a <= f < b + 2 and not P["black"][f]:
                dive = float(np.clip(1.0 - speed, 0, 1))
                img = self.vhs(img, 0.25 + 0.75 * dive, f)
                img = self.drain(img, 0.85 * dive, 0.15 + 1.1 * dive)
                if sag_on:
                    img = self.sag(img, dive)
        # gated chops: slice displacement
        if ch["chop"][f] > 0.5:
            img = self.slices(img, f, 1.0)
        img = self.retrigger(img, accent)
        # chroma split on hits
        img = self.chroma(img, (6 * snare + 3 * kick + 5 * accent) * self.s)
        # negative strobe on gated silences
        if P["negative"][f]:
            img = self.negative(img)
        # breathing warp on the bass
        img = self.breathe(img, 0.010 * float(C["sub_seam"][f]) + 0.016 * kick)
        self.prev_clean = img.copy()
        self.prev_src = src_img
        # grade and finish
        img = self.magma_grade(img)
        img = self.grain(img, f) * self.vign
        img = self.draw_readout(img, f)
        return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("renders")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--frames", default=None)
    ap.add_argument("--png-input", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    post = Post(a.width)
    f0, f1 = (0, post.F - 1) if not a.frames else map(int, a.frames.split("-"))
    for f in range(f0, f1 + 1):
        img = post.frame(f, Path(a.renders), a.png_input)
        Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out / f"p{f:04d}.png")
        if f % 24 == 0:
            print(f"post {f}/{post.F}", flush=True)


if __name__ == "__main__":
    main()
