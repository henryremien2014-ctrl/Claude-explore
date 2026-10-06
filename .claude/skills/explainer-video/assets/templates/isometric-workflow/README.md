# Isometric workflow template (Remotion)

This renders a 20-second, 1920×1080 explainer. Each step is an isometric
block that rises into place. Then an orange dot travels a path on the floor to
the spot where the next block rises. Each block carries an icon and a numbered
label in plain words. The sample content in `src/steps.ts` (a pet-portrait
shop's ordering steps) is only there to replace.

When you copy this template for a video, rewrite this README for that
project: what the video shows, its steps, and how to re-render it.

## Use it

```bash
cp -r <skill>/assets/templates/isometric-workflow <new empty folder>
cd <new empty folder>
npm install
# edit src/steps.ts (title, steps, icons, footer)
npm run stills -- 80 599       # check a couple of frames first
npm run render                 # out/how-it-works.mp4
```

| File | What to change there |
|---|---|
| `src/steps.ts` | Title, steps (lines + icon), footer. An empty string hides the title or footer. |
| `src/theme.ts` | Colours, fonts, text sizes (labels 68, title 76, footer 60 px), whether the background dot grid shows |
| `src/timeline.ts` | Timing. Steps are spread evenly from 1.0 s to 13.6 s, and the footer fades in at 15.5 s. |
| `src/layout.ts` | Block size and spacing. Rarely needs touching. |
| `src/Icons.tsx` | The icon set. Add new icons in a 100×100 box. |

Commands:

- `npm run icons` renders every icon to `out/icon-sheet.png`.
- `npm run stills -- <frames>` renders PNG stills of the given frames from one bundle.
- `npm run studio` opens a live preview.

## Layout rules

- **2 to 6 steps.** 3 to 5 read best in 20 seconds. With 5 steps each block
  gets about 3.1 s; with 6 steps, 2.5 s.
- Steps 1, 3 and 5 sit in the lower row with their labels below them. Steps
  2, 4 and 6 sit in the upper row with their labels above them.
- Upper-row labels should be one line. Lower-row labels can use two.
- Keep each line to about 14 characters.
- Labels are measured with the real font. Labels near the frame edges are
  pulled inside a 60 px margin.
- If two labels in a row would touch, rendering stops with an error naming
  them. The same happens if the labels can't fit vertically. Shorten the text
  or move it onto two lines.
- Label size is 68 px for up to 4 steps, 64 px for 5 and 60 px for 6. On a
  phone held upright (390 pt wide) that is about 13.8, 13.0 and 12.2 pt. Step
  numbers are 46 px (9.4 pt) and the footer is 60 px (12.2 pt).
- The title and footer sit at least 60 px from the frame edges.
- Icons lie flat on the top face, with their "up" pointing to the upper left.
  To make an icon read upright, draw it turned 45°, as `check` and `user` are.

## Icons

bag, cart, card, money, camera, upload, download, document, mail, chat, phone,
call, calendar, clock, palette, pencil, scissors, sparkle, gear, search, eye,
chart, check, heart, star, user, lock, mic, headphones, sliders, broadcast,
play, send, globe, home, truck, frame, paw

For "book a call", use `call` (a handset) or `calendar`. For audio editing,
use `sliders`; for "goes live", use `broadcast`.

## Built to avoid

- **Shadows:** there are no drop shadows. Depth comes from three face tones.
- **Neon colours:** the palette is muted.
- **Floating particles:** there are none. The background dots are a static grid.
- **Camera spins:** the camera is fixed.

## Notes

- Fonts are DM Sans and Fraunces (SIL OFL), bundled in `public/fonts`, so
  rendering needs no network access.
- `remotion.config.ts` uses a local Chromium when one exists at the given path
  (set `REMOTION_BROWSER` to choose one). Otherwise Remotion downloads its own.
- `remotion.config.ts` also tags the video as BT.709. Untagged video plays with
  visibly shifted colours in Chrome and Safari.
- For a website, also export a poster frame:
  `npx remotion still HowItWorks out/how-it-works-poster.png --frame=599`.
- Remotion is free for individuals and companies of up to 3 employees. Bigger
  companies need a company licence.
