# 5) Math and concept explainer (Manim)

**Status:** recipe only. Not yet built with this skill, so check each step as you go.

## The prompt

> Use Manim to make a 60-second explainer of [concept].
>
> Write a short script first. Start with the idea in plain words, build the formula one term at a time, then show it as a graph. Each visual change matches one sentence of the script.
>
> **Avoid:** walls of equations, more than 3 colors, text on top of moving shapes.
>
> **Done means:** the script and a 1080p MP4 with no frame where text overlaps another element.

## Inputs

- **The concept.** Optionally the audience level.

## Install (Manim Community)

```bash
pip install manim            # needs Cairo and Pango; on Debian/Ubuntu, if no wheel fits:
# apt-get install -y libcairo2-dev libpango1.0-dev pkg-config python3-dev
manim --version
```

- **LaTeX** is needed only for `MathTex`/`Tex`. Check with `which latex dvisvgm`.
- **Without LaTeX**, build formulas from `Text`/`MarkupText` pieces using
  Unicode (x², ×, π, √, Σ, ≈). Make each term its own mobject so it can
  appear on its own.
- **Render a 1-second test scene** before writing the real one.

## Script first

Write `script.md` with 8–10 sentences for 60 s (about 6–7 s each), in three parts:

1. **The idea in plain words:** 2–3 sentences, no symbols.
2. **The formula, term by term:** one sentence per term, each adding exactly one term.
3. **The graph:** 2–3 sentences, each pairing with one change, such as
   drawing the axes, plotting the curve, or moving a parameter.

Add a table with three columns: sentence, the one visual change it pairs
with, and its start time.

## Build

- **Use one `Scene` class with three fixed zones** that never overlap:
  - the formula or plain-words band at the top,
  - the graph area in the middle,
  - the caption band at the bottom.
  Moving shapes stay inside the graph area. Text never sits where something moves.
- **Show each script sentence as a caption** in the bottom band, so the video
  works without narration. Cross-fade between sentences, and pace each
  sentence's visual change with `self.wait()`.
- **Use at most 3 colours,** defined as constants, for example light text on
  near-black plus two accents. Axes and captions use the text colour.
- **Build terms with `Write`/`FadeIn`** and combine them with
  `TransformMatchingShapes` or `TransformMatchingTex`. Never put more than one
  line of formula on screen.
- **Render:**
  - `manim -qh scene.py ConceptScene` gives 1920×1080 at 60 fps.
  - Set `config.frame_rate = 30` for 30 fps.
  - Copy the result from `media/videos/...` to `out/`.

## Verify

- **No overlap, in code.** After every `play`/`wait`, check every text
  mobject's box (`get_corner(UL)`/`get_corner(DR)`) against every other
  visible mobject's box, and raise on any intersection. During animations,
  check with an updater that runs every frame.
- **No overlap, by eye.** Extract stills every 0.5 s
  (`extract_stills.py --times 0 0.5 1 ... 59.5 --sheet ...`), look at the
  contact sheets, and open full-size stills where anything looks close.
- `verify_video.py out/video.mp4 --width 1920 --height 1080 --min-duration 55 --max-duration 65`
- **Colours:** list the colour constants in the report (3 or fewer).

## Lessons

(Add what you learn when you build this style.)
