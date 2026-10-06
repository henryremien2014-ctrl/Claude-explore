# 3) Isometric workflow

**Status:** proven. The template in `assets/templates/isometric-workflow/`
has produced delivered videos with 4 and 5 steps, and its layout has been
tested with 2 to 6 steps.

## The prompt

> Animate this workflow as an isometric explainer in Remotion: [list your steps in order].
>
> Each step is an isometric block that rises into place. A dot then travels along a path to the next block. Label each block in plain words.
>
> **Avoid:** shadows on every element, neon colors, floating particles, camera spins.
>
> **Done means:** a 20-second 1920x1080 MP4, every label readable on a phone screen, and a still checked at each step.

## Inputs

- **The steps, in order.** 2–6 of them; 3–5 read best in 20 seconds.
- Optional: a title (default "How it works"), a closing footer line (a promise
  or a call to action, such as turnaround time), and brand colours.

## Build from the template

```bash
cp -r <skill>/assets/templates/isometric-workflow <new-folder>
cd <new-folder> && npm install
```

1. **Edit `src/steps.ts`:** set the title, the steps and the footer.
   - Each step has `lines` and an `icon`.
   - Steps 1, 3 and 5 sit in the lower row and can take two lines.
   - Steps 2, 4 and 6 sit in the upper row; keep them to one line.
   - Keep each line to about 14 characters, in plain words a customer would
     use ("Send a photo", not "Asset ingestion").
   - Run `npm run icons` and look at `out/icon-sheet.png` to choose icons.
     If no icon fits, draw a new one in `src/Icons.tsx` (in a 100×100 box)
     and check it on the sheet.
   - Suggested icons: `call` (a handset) or `calendar` for "book a call",
     `sliders` for editing or mixing, `broadcast` for "goes live". `phone` is
     a smartphone, not a call.
2. **Optionally edit `src/theme.ts`** for colours and fonts.
3. **Render stills at each step** (the frame list is below), look at them, and
   fix anything crowded. If a label is too long, the render stops with an
   error naming the two labels that collide; shorten them.
4. **Render the video:** `npm run render` writes `out/how-it-works.mp4`.
5. **Rewrite the project's `README.md`** for this video: what it shows, its
   steps, and how to re-render it. If the video is going on a website, also
   export a poster frame:
   `npx remotion still HowItWorks out/how-it-works-poster.png --frame=599`.

Layout and timing adapt to the number of steps:

- Blocks shrink to fit.
- Labels are measured with the real font and pulled inside the frame margins.
- Labels are 68 px for up to 4 steps, 64 px for 5, and 60 px for 6.
- Steps are spread evenly from 1.0 s to 13.6 s, and the footer appears at 15.5 s.

## Verify

`extract_stills.py out/how-it-works.mp4 --frames <list below> 599 --sheet out/stills/sheet.png`
pulls one settled still per step, after that step's block, icon and label are
in and before the dot leaves:

| Steps | Still frames, one per step |
|---|---|
| 2 | 80, 458 |
| 3 | 80, 269, 458 |
| 4 | 80, 206, 332, 458 |
| 5 | 80, 174, 268, 362, 456 |
| 6 | 80, 155, 230, 305, 380, 455 |

(The formula is `30 + i × floor(378 / (N − 1)) + 50` for step `i`, counting from 0.)

Then:

- `verify_video.py out/how-it-works.mp4 --width 1920 --height 1080 --duration 20 --fps 30`
- **Open every still.** Check that the right block and label are in place,
  that nothing overlaps or is cut off, and that the dot is hidden or between
  blocks.
- **Phone check:** `phone_check.py out/stills/<final>.png --size label=<px> --size title=76 --size footer=60 --size number=46`.
  The label is 68 px for up to 4 steps, 64 for 5 and 60 for 6 (13.8, 13.0
  and 12.2 pt upright). If you changed sizes in `theme.ts`, pass the real
  ones. Give the pt values in the report.

## Avoid list, as built

- **Shadows:** there are no drop shadows. Depth comes from three face tones.
- **Neon colours:** the palette is muted (paper, teal, terracotta, ink).
- **Floating particles:** there are none. The faint background dots are a
  static grid; `SHOW_GRID = false` removes them.
- **Camera spins:** the camera is fixed.

## Lessons

- **Crowding.** The first draft put the title too close to label 2 and the
  footer too close to label 3. The layout now reserves a band between the
  title and the footer.
- **Icon orientation.** Icons lying flat on a top face have their "up"
  pointing to the upper left. A shape that needs to read upright (a tick, a
  person) must be drawn turned 45°.
- **Thin icons.** Thin icons (a brush, a pencil drawn along the wrong
  diagonal) disappear. Bold, closed shapes read best.
- **Measure, don't estimate.** Measuring labels with the loaded font, then
  clamping or failing, beats guessing widths.
- **Footer size.** The footer often carries the promise the user asked to
  include, such as a turnaround time. It was 52 px (10.6 pt), under the
  12 pt rule, so it is now 60 px. The step numbers have a 46 px floor, since
  at 5 steps they had dropped to 8.9 pt.
- **Margins.** Measure the dark-pixel box of the final still. The title and
  footer had crept inside the 60 px margin, so they were moved to `top: 50`
  and `bottom: 56`.
- **Colour.** Untagged H.264 from Remotion shows shifted colours in Chrome
  and Safari. The template now tags its output as BT.709.
- **Labels stay one line in the upper row.** "Upload your raw audio" became
  "Upload raw audio". Shorten the wording rather than squeezing the text,
  and tell the user in the report.
