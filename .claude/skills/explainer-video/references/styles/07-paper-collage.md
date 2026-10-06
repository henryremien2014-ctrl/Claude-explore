# 7) Paper collage

**Status:** recipe only. Not yet built with this skill, so check each step as you go.

## The prompt

> Make a 30-second paper collage explainer in Remotion about [topic].
>
> I attached background images and transparent PNG cutouts for each scene. Give each cutout a white paper edge. Move the background, middle, and front layers at different speeds, and use a torn-paper transition between scenes.
>
> **Avoid:** a slow zoom on a flat photo, lens flares, film grain over everything.
>
> **Done means:** an MP4 where each scene holds at least 4 seconds and every cutout edge looks clean at full size.

## Inputs

- **For each scene, one background image plus one or more transparent PNG
  cutouts.** These are required. Ask which cutouts are "middle" and which are
  "front" if it isn't obvious.
- **The topic,** and a line of text for each scene if the user wants on-screen words.

## Prepare the cutouts (never modify the originals)

- **Add the paper edge with Pillow:**
  1. Work at 2× size.
  2. Grow the alpha channel by 10–14 px (repeated `ImageFilter.MaxFilter(3)`
     or a distance transform).
  3. Fill the grown area white.
  4. Paste the original on top.
  5. Scale back down.
- **For a hand-cut look,** vary the edge width slightly with seeded,
  low-frequency noise.
- **Save** to `public/cutouts/<name>-paper.png`.
- **Inspect every edged cutout at 100%.** Crop a 400×400 patch along its edge
  and look at it. Check for no leftover halo from the original background, no
  jaggies, and no gaps between the cutout and its white edge.

## Build (1920×1080, 30 fps, 30 s)

- **Scenes:** for example, 5 scenes of 6 s with 0.6 s transitions. Every scene
  must hold, fully visible with no transition running, for at least 4 s. Put
  the start, end and hold length of each scene in `timeline.ts`.
- **Parallax by translation, not zoom:**
  - The background moves slowest (about 8 px/s), middle cutouts about 20 px/s,
    and front cutouts about 40 px/s, all in the same direction.
  - Scale each background by about 1.05× so the motion never reveals an edge.
  - A slight rotation drift on cutouts (±1°) is fine.
- **Torn-paper transition:** reveal the next scene behind a mask with a jagged
  edge (seeded points every ~20 px, ±12 px) that sweeps across in about 0.6 s.
  Draw a 6–10 px white torn edge along the mask line. Build it with an SVG
  `clipPath`, or a CSS `mask-image` made from an SVG path.
- **Not allowed:** no Ken Burns zoom, no lens flares, and no grain over
  everything. If you want texture, use only a subtle paper texture on the
  background layer.

## Verify

- **Scene timing:** in the report, include a table of each scene's start, end
  and hold. Every hold must be at least 4 s. Generate the table from
  `timeline.ts`.
- **Stills:** extract one still mid-scene for each scene and one
  mid-transition, and look at them.
- **Cutout edges at full size:** from the mid-scene stills, crop each cutout's
  edge at 100% (no scaling) and look at it.
- `verify_video.py out/video.mp4 --width 1920 --height 1080 --duration 30`

## Lessons

(Add what you learn when you build this style.)
