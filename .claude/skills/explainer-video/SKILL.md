---
name: explainer-video
description: Make short explainer and motion-graphics videos (MP4) in eight proven styles - kinetic typography synced to a voiceover, whiteboard line drawings, isometric workflow/process diagrams, animated data charts from a CSV, Manim math and concept explainers, app walkthroughs from screenshots, paper-collage animations, and talking-head auto-edits (cut silences, burn in captions, punch-in zooms). Built with Remotion, Manim and FFmpeg; every style has an Avoid list and a "Done means" bar that gets checked on the rendered file, and the isometric style ships as a ready-to-render template. Use this skill whenever someone wants an explainer, "how it works", process, onboarding or product-walkthrough video, an animated chart, a captioned or kinetic-text video, a whiteboard or Manim animation, or a talking-head clip tightened up, even if they don't name a style or a tool.
---

# Explainer videos

This skill covers eight explainer styles. Each has a fixed spec: what to build,
an **Avoid** list, and a **Done means** finish line. The specs come from a
tested prompt pack, and each one is in `references/styles/` word for word,
with notes on how to build and check it.

- Style 3 (isometric workflow) has a ready-made Remotion template that has
  produced delivered videos.
- Styles 2 (whiteboard) and 4 (data chart) have each been built once with
  these notes.
- The other styles' notes are recipes that haven't been built yet.

## Pick the style

| # | Style | The user provides | Built with | Reference |
|---|---|---|---|---|
| 1 | Kinetic typography | Voiceover audio, a font, and background/text/accent colours | Remotion + Whisper | `references/styles/01-kinetic-typography.md` |
| 2 | Whiteboard drawing | A topic | Remotion | `references/styles/02-whiteboard-drawing.md` |
| 3 | Isometric workflow | The steps, in order | Remotion **template** | `references/styles/03-isometric-workflow.md` |
| 4 | Animated data chart | A CSV | Remotion | `references/styles/04-animated-data-chart.md` |
| 5 | Math / concept explainer | A concept | Manim | `references/styles/05-math-concept-manim.md` |
| 6 | App walkthrough | App screenshots, in order | Remotion | `references/styles/06-app-walkthrough.md` |
| 7 | Paper collage | Background images plus transparent PNG cutouts for each scene | Remotion + Pillow | `references/styles/07-paper-collage.md` |
| 8 | Talking-head auto edit | The video file | FFmpeg + Whisper | `references/styles/08-talking-head-auto-edit.md` |

If the user names a style, use it. If not, infer it from what they gave you:

- a CSV → 4
- screenshots → 6
- a voiceover → 1
- footage of someone talking → 8
- a list of steps or a process → 3
- cutout images → 7
- a math or science idea → 5
- any other topic → 2

If two styles fit, pick one and say why in a sentence.

Fill each [bracket] in the style's prompt from what the user said. A topic or
a list of steps can also come from material the user pointed you to, such as
their notes or a repo; say what you used. Required **files** are different.
Never invent a voiceover, a CSV's numbers, screenshots or footage for a real
deliverable; ask for them. If you only need to show what a style looks like,
a clearly labelled placeholder is fine.

## Ground rules

These come from the prompt pack, and they are why the videos come out well:

1. **Use one new, empty folder per video**, for example
   `explainer-videos/<style>-<topic>/`. Dependencies, renders and stills stay
   together, and the list of files created is exact.
2. **Install what you need yourself.** Run `scripts/env_check.sh` first. It
   lists the tools present and the hosts you can reach, so blockers (such as a
   blocked model-download host) show up before you build.
3. **Treat the Avoid list as hard constraints.** Naming exactly what to avoid
   works better than "avoid a generic look", which just swaps one default
   style for another. Check every item, and say in the report how you avoided
   each one.
4. **"Done means" is the finish line.** Check every item on the rendered file,
   not the source, and keep evidence: a command's output, or a still you
   looked at. "It rendered" is not done.
5. **End with the report** below: the exact files created and the result of
   each Done-means check.

## Workflow

1. **Read the style's reference file.** It has the prompt, the inputs, a build
   recipe, pitfalls, and how to verify each Done-means item.
2. **Set up the project** in the new folder:
   - Style 3: copy `assets/templates/isometric-workflow/` and edit `src/steps.ts`.
   - Other Remotion styles: follow `references/remotion.md` (pinned versions,
     local Chromium, bundled fonts, render settings).
   - Manim and FFmpeg: see the style's reference file.
3. **Plan before you animate.** Write the script or storyboard when the style
   asks for one. Keep all timing in one file, in frames, and all words and
   colours in one data file, so later changes are one-line edits.
4. **Build, then render stills at key moments and look at them** before
   rendering the full video. Crowded or overlapping text, things cut off at the
   frame edge, and unreadable labels are cheap to fix at this stage.
   `scripts/remotion-stills.mjs` renders many frames from one bundle.
5. **Render the video.**
6. **Verify on the rendered file.**
   - `python3 scripts/verify_video.py out/video.mp4 --width 1920 --height 1080 --duration 20`
     checks size, duration, fps, frame count and audio.
   - `python3 scripts/extract_stills.py out/video.mp4 --times ... --clean --sheet out/stills/sheet.png`
     pulls exact frames at the moments the Done-means line names (or one per
     step or scene). `--clean` deletes stills from earlier renders so they
     can't be mistaken for evidence. **Open every still and look at it.**
   - `python3 scripts/phone_check.py <still> --size label=68 ...` gives each
     text size in points on a phone, plus a phone-width preview to look at.
   - Run the style-specific checks in its reference file.
7. **Report**, using the format below.

## Design defaults

These keep videos clean when the prompt leaves a choice open.

- **Palette:** use a plain background, one accent colour, and muted everything
  else. Define the colours once, in a theme file.
- **Type:** use one or two fonts, bundled as files (`@fontsource/<font>` from
  npm) rather than fetched at render time. Text that carries the message
  (titles, step labels, captions) should be at least 12 pt on a phone held
  upright:
  - In a 1920-wide video that means 60 px or more (pt = px × 390 / 1920).
  - In a 1080-wide video it means 34 px or more.

  Dense secondary text, such as a chart's value and axis labels, may drop to
  about 9 pt (44 px at 1920 wide). Show fewer labels before going smaller.
  Numbers that count up need a font with tabular figures.
- **Chart guidance from elsewhere:** if a dataviz skill is available, use its
  colour and mark advice, but scale its on-screen sizes up 2–3× for video.
- **Motion:** use quick ease-out entrances from one consistent direction.
  Nothing loops or bounces for decoration. Hold new text long enough to read
  twice (about 1.5 s for a short label).
- **Layout:** keep text off moving shapes, off other text, and inside a 60 px
  margin. If text doesn't fit, shorten it rather than shrinking it below the
  phone minimum.
- **Sound:** add audio only when the style or the user asks for it.

## Environment notes

- Remotion downloads Chrome Headless Shell on its first render. If the machine
  already has one, point `Config.setBrowserExecutable` at it. Playwright's
  copy is at `/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell`.
- Keep `remotion` and every `@remotion/*` package at exactly the same version.
- Whisper models download from `huggingface.co` (whisper.cpp, faster-whisper)
  or `openaipublic.azureedge.net` (openai-whisper). If those hosts are
  blocked, tell the user early and offer the alternatives in style 1's
  reference. Don't try to route around a network policy.
- PNG frames plus H.264 at CRF 16 keep flat graphics and text crisp, and the
  file stays small: 20 s of flat 1080p graphics comes to under 1 MB.
- Tag the video as BT.709 (`Config.setColorSpace('bt709')`, already set in the
  template). Remotion's default output is untagged, and Chrome and Safari then
  shift its colours by up to about 10 levels.
- In containers, Remotion may print "Detected differing memory amounts ...
  docker" on every render. It's harmless; ignore it.

## Report

Finish with this, filled in:

```
**Video:** <path> (<codec>, <W>x<H>, <fps> fps, <frames> frames, <duration> s, <size>)
**Style:** <number and name>, with <what filled the brackets>
**Files created:** <every file, grouped by folder>
**Done means:**
- <criterion>: met / not met. <evidence>
**Avoid list:** <item>: <how it was avoided>
**Choices I made:** <assumptions, placeholders, anything the user should confirm>
**To change it:** edit <file>, then run <render command>
```

If a check fails and you can't fix it, say so plainly in the report. Never
round a failed check up to "met".

When a build teaches you something about a style (a pitfall, a better
technique, a reusable component) and the skill's files are writable (for
example, it lives in the repo's `.claude/skills/`), add it to that style's
reference file under **Lessons**, so the next video starts from it.
