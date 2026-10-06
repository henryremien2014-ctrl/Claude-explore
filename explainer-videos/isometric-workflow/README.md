# How it works: isometric workflow explainer

Style 3 from the explainer prompt pack (`../PROMPTS.md`), made with Remotion.
It's a 20-second, 1920×1080 video of the pet-portrait shop's ordering steps,
taken from `pet-portraits/README.md` and `order-workflow.md`.

**Video:** [`out/how-it-works.mp4`](out/how-it-works.mp4) (H.264, 30 fps, 600 frames, silent, 0.6 MB)

| # | Block label | Icon on the block |
|---|---|---|
| 1 | Place your order | shopping bag |
| 2 | Send a photo | camera |
| 3 | We create your portrait | artist's palette |
| 4 | Get your files | framed paw print |

The title "How it works" stays in the top-left corner. At 15.5 s this footer
fades in: *Ready in 1–3 business days · 1 free revision* (from message
template A and the shop's offer).

## Timeline

| Time | What happens |
|---|---|
| 0–0.5 s | Title fades in; a dashed outline marks where block 1 will stand |
| 1.0 s | Block 1 rises; its icon, then its label, fade in |
| 4.0–5.1 s | The dot leaves block 1 and travels the path to block 2, leaving an orange trail |
| 5.2 s | Block 2 rises; the same pattern repeats every 4.2 s |
| 13.6 s | Block 4 rises |
| 15.5 s | Footer fades in; everything holds until 20 s |

## Change the words, steps or timing

- **Words and icons:** `src/steps.ts` holds the title, the step labels, the icons and the footer.
- **Timing:** `src/timeline.ts`.
- **Colours and layout:** the constants at the top of `src/HowItWorks.tsx`.

```bash
npm install
npm run render                      # writes out/how-it-works.mp4
npm run studio                      # live preview in the browser
node scripts/stills.mjs 80 206 599  # writes PNG stills of the given frames
```

The layout is a zig-zag: steps 1 and 3 sit low with their labels below them,
and steps 2 and 4 sit high with their labels above them. Keep labels in the
upper row (2 and 4) to one line of about 14 characters. Labels in the lower
row (1 and 3) can use two lines. Adding a 5th step needs a smaller `UNIT` in
`HowItWorks.tsx`.

## "Done means" checks (2026-10-06)

- **20-second 1920×1080 MP4.** Confirmed with ffprobe: h264, yuv420p,
  1920×1080, 30 fps, 600 decoded frames, 20.000 s.
- **Every label readable on a phone screen.** Labels are 68 px tall in the
  1080p frame. That is about 13.8 pt on a 390-pt-wide phone held upright
  (the smallest common case) and about 30 pt full-screen sideways. The title
  comes to 15.4 pt and the footer to 10.6 pt. Checked on a 390-px-wide
  downscale: [`out/stills/phone-width-390px.png`](out/stills/phone-width-390px.png).
- **A still checked at each step.** Each still was taken from the encoded MP4
  after that step's block, icon and label had settled. In every one there is
  no overlap, no clipping, and the dot is hidden:
  [step 1 at 2.7 s](out/stills/step-1-at-2.7s.png),
  [step 2 at 6.9 s](out/stills/step-2-at-6.9s.png),
  [step 3 at 11.1 s](out/stills/step-3-at-11.1s.png),
  [step 4 at 15.3 s](out/stills/step-4-at-15.3s.png),
  [final frame](out/stills/final-at-20.0s.png).

## The "Avoid" list

- **Shadows on every element:** there are no drop shadows anywhere. Depth
  comes only from three tones of teal on each block.
- **Neon colours:** the palette is warm paper `#F5EFE4`, teal `#4F968B`,
  terracotta `#CF633D` and ink `#24201C`.
- **Floating particles:** there are none. The faint dots behind the scene form
  a static isometric grid and never move. Delete the `gridDots` block to
  remove them.
- **Camera spins:** the camera never moves.

## Notes

- Fonts are DM Sans and Fraunces (SIL Open Font License), bundled in
  `public/fonts`, so rendering needs no network access.
- Rendering uses the Chromium already on this machine when it exists (see
  `remotion.config.ts`). Otherwise Remotion downloads its own.
- Remotion's licence is free, including for commercial work, for individuals
  and for-profit companies of up to 3 employees. Bigger companies need a paid
  company licence (see `node_modules/remotion/LICENSE.md`).
