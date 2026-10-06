# 6) App walkthrough

**Status:** recipe only. Not yet built with this skill, so check each step as you go.

## The prompt

> I attached [number] screenshots of my app in order. Build a 40-second walkthrough in Remotion.
>
> In each screenshot, find the button or field the user clicks. Zoom in on it, move a cursor there, and show a one-line callout that explains the step.
>
> **Avoid:** zooming past 2x, spinning transitions, phone or laptop mockups, callouts that cover the button.
>
> **Done means:** a 1920x1080 MP4 where the cursor lands on the right element every time. List the coordinates you used so I can check them.

## Inputs

- **The screenshots, in order.** They are required.
- **What gets clicked on each.** Ask, or work it out from the screens and the
  flow, and say which ones you inferred.

## Find each target, and prove it

1. Open each screenshot and find the element the user clicks.
2. Record its box in image pixels in `steps.json`:
   `[{image, target: {x, y, w, h}, callout}]`.
3. Draw that box onto a copy of the screenshot with Pillow and look at it.
   Adjust until it hugs the element. Keep these images as evidence in
   `out/targets/step-N.png`.

## Layout maths (keep it in one module)

- **Fit:** fit each screenshot into 1920×1080 with a margin `m`:
  - `s = min((1920-2m)/W, (1080-2m)/H)`
  - offset `o = ((1920 - s·W)/2, (1080 - s·H)/2)`
  - an image point `p` lands on screen at `o + s·p`.
- **Zoom:** zoom by `z` (2 at most; clamp it and assert) with the transform
  origin set to the target's centre on screen. The target's centre then stays
  put while everything around it grows, so the cursor's destination is simply
  `o + s·centre`.
- **Cursor:** draw an arrow pointer with its tip at the SVG's origin. It moves
  from the previous point to the target with ease-in-out over about 0.8 s,
  then a small click ring plays.
- **Callout:**
  - one line, 50 characters or fewer, 52 px or more;
  - placed on the side of the zoomed target with the most room, 24 px away;
  - assert that its box never intersects the zoomed target box.

## Timing (40 s, 30 fps)

Split the time evenly across the N steps. Each step goes:

1. Zoom in (0.6 s).
2. The cursor moves (0.8 s).
3. Click ring.
4. The callout appears and holds at least 2 s.
5. A cut or short cross-fade to the next screenshot.

No spins, flips or 3D transitions, and no device frames around the screenshots.

## Verify

- **Cursor on target:** for each step, extract the still at the click moment.
  Compute the target's screen box from the same layout module and check that
  the cursor tip lies inside it, using a script that prints pass/fail per
  step. Also look at the stills.
- **Coordinates in the report,** one row per step: image box (x, y, w, h),
  zoom factor, cursor tip on screen (x, y), and callout box.
- `verify_video.py out/video.mp4 --width 1920 --height 1080 --duration 40`

## Lessons

(Add what you learn when you build this style.)
