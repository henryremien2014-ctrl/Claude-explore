# 2) Whiteboard drawing

**Status:** built once with this skill (a 45 s compound-interest explainer), and
it passed every Done-means check. The Lessons at the end come from that build.

## The prompt

> Make a 45-second whiteboard explainer in Remotion about [topic].
>
> Write a 6-scene script first. For each scene, draw one simple black line illustration as SVG paths and animate it drawing on stroke by stroke. Add a short label under each drawing.
>
> **Avoid:** a drawing hand, clip art, color fills, more than one drawing per scene.
>
> **Done means:** the script, the SVG files, and a 1920x1080 MP4 where every drawing finishes before the next scene starts.

## Inputs

- **The topic.** Optionally the audience and the one idea they should leave with.

## Plan: the script comes first

Write `script.md` before drawing anything. It holds 6 scenes of 7.5 s each
(45 s at 30 fps is 1350 frames, so 225 frames per scene). For each scene, give:

- the one sentence the scene explains,
- the single drawing (what it shows, in a few words),
- the label of 2–5 words that sits under the drawing.

The six scenes should build one idea in order (for example: problem, cause,
mechanism, example, result, takeaway). There is no narration audio unless the
user asks for it, so the labels carry the meaning.

## Draw the SVGs

- Write one file per scene: `svg/scene-1.svg` to `svg/scene-6.svg`, each with
  `viewBox="0 0 800 500"` and 6–20 `<path>` strokes.
- Use black strokes only (`stroke="#111"`, `stroke-width="6"`, round caps and
  joins, `fill="none"`). Draw simple, icon-like line art, the way a person
  sketches on a whiteboard. No shading and no clip art.
- Order the paths the way a hand would draw them: big outline first, then
  inner details, then small marks.
- Keep the paths in `src/content.ts` and write the `.svg` files from them with
  a small script, so the deliverable files and the video share one source.
- **Look at every drawing before animating.** Put all six finished drawings on
  one review sheet (a `Still` composition) and render it. Redraw any that
  isn't instantly recognisable; getting the drawings right takes several
  passes.
- **One drawing per scene** means one picture. The same object shown growing
  or repeating within the picture (a snowball at three sizes down one hill)
  still counts as one drawing. Two unrelated pictures side by side don't.

## Animate

- Scene `i` occupies frames `[i×225, (i+1)×225)`. Inside a scene:
  - frames +0 to +10: clear the previous board (a cut, or a quick wipe),
  - draw from +10 to +150,
  - fade the label in from +150 to +165,
  - hold until the scene ends (at least 2 s to read).

  Putting the wipe in the next scene's first 10 frames keeps the full label
  hold, and keeps the stills taken 6 frames before each scene end clean.
- **Stroke by stroke:** split the draw window across the paths in proportion
  to their lengths (`getLength` from `@remotion/paths`). Animate each path with
  `evolvePath(progress, d)` so a stroke starts only when the previous one ends.
  - With round caps, don't render a path at progress 0, since it leaves a dot.
  - At progress 1 or more, render the plain path with no dash, so dash
    rounding can't leave a gap.
- **Position the label** from the strokes' measured bounding box
  (`getBoundingBox` from `@remotion/paths`), not from the viewBox. Every scene
  then has the same gap above its label.
- **Assert the Done-means rule in code:** for every scene, throw if
  `drawEnd >= sceneEnd`, so a timing change can't silently break it.
- **Look:** an off-white board (`#FBFBF8`) and black lines only.
  - Labels use one clean or handwritten-style font (for example
    `@fontsource/patrick-hand`) at 64 px or more, centred under the drawing.
  - No colour anywhere, no hand, and one drawing per scene.

## Verify

- **Files:** `script.md` and six SVGs exist. Check that every `fill` attribute
  is `none` and every stroke is black:
  `grep -o 'fill="[^"]*"' svg/*.svg | sort | uniq -c`.
- `verify_video.py out/video.mp4 --width 1920 --height 1080 --duration 45`
- **Stills to look at:** for each scene, extract one mid-draw (the drawing
  should be partial) and one 6 frames before the scene ends (the drawing
  should be complete, with its label showing). With 225-frame scenes:
  `--frames 80 219 305 444 530 669 755 894 980 1119 1205 1344`.
- In the report, include a table of each scene's start, draw end and scene end
  in seconds.
- **Optional decoded-frame check.** Comparing frames after each draw end with
  the end frame shows that nothing changes after the drawing finishes. Compare
  masks of dark line pixels, not raw pixel differences: H.264 leaves noisy
  pixels even between identical source frames. `ffmpeg -vf signalstats`
  (SATMAX) over all frames gives one number for "no colour".

## Lessons

- **Shapes that misread.** Paired arcs inside a circle read as a face. A spiral
  in a circle reads as a pastry. Plain circles read as balls, so give coins an
  inner ring. Speed lines belong behind or above the motion, not beside it.
- **Show change as growth along a path.** "Snowballing" read only once the ball
  was shown growing down the hill.
- **Choose believable numbers.** A 5% example rate keeps the arithmetic easy
  and avoids promising unrealistic returns. State the assumption in the report.
- **Running TypeScript outside Remotion.** Scripts that import `src/content.ts`
  (an SVG writer, a timing table) run with `npx tsx`.
