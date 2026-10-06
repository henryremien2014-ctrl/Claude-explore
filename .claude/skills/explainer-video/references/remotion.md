# Remotion project setup (styles 1, 2, 4, 6, 7)

The isometric template, `assets/templates/isometric-workflow/`, is a working
example of everything below. Copy its config files instead of writing them
from scratch.

## Create the project

```bash
mkdir -p <new-folder> && cd <new-folder>
V=$(npm view remotion version)            # one version for every remotion package
npm init -y
# -E saves exact versions (no ^), so the packages can't drift apart later
npm i -E remotion@$V @remotion/cli@$V @remotion/fonts@$V react react-dom
npm i -D -E typescript@~5.9 @types/react @remotion/bundler@$V @remotion/renderer@$V @fontsource/<font>
# add only what the style needs, always @$V:
#   @remotion/paths   SVG path drawing (evolvePath, getLength)
#   @remotion/media   <Audio>/<Video>
#   @remotion/layout-utils   measureText / fitText
#   @remotion/captions   caption helpers (createTikTokStyleCaptions)
```

Copy these files from the template:

- `remotion.config.ts`: PNG frames, H.264 at CRF 16, yuv420p, BT.709 colour
  tagging (`Config.setColorSpace('bt709')`, so browsers show the colours as
  designed), and a local Chromium if one exists.
- `tsconfig.json`
- `.gitignore`
- `scripts/stills.mjs`: copy this skill's `scripts/remotion-stills.mjs`. It
  renders the composition named in `COMPOSITION`, or the first one in
  `Root.tsx` if that isn't set.

Then lay out the source:

```
src/index.ts      registerRoot(RemotionRoot)
src/Root.tsx      <Composition id="Main" component={Main} durationInFrames fps width height />
src/content.ts    every word, number and asset name
src/timeline.ts   every timing, in frames
src/theme.ts      colours, fonts, sizes
src/Main.tsx      the scene(s)
public/           fonts, images and audio, referenced with staticFile('...')
```

Add `"render": "remotion render Main out/video.mp4"` to the scripts in
`package.json`.

## Fonts

Fonts load from bundled files, so rendering needs no network access.

```ts
// npm i -D @fontsource/<font>, then copy
// node_modules/@fontsource/<font>/files/<font>-latin-<weight>-normal.woff2 into public/fonts/
import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';
export const fontsReady = loadFont({family: 'DM Sans', url: staticFile('fonts/dm-sans-700.woff2'), weight: '700'});
```

`loadFont` holds the render until the font has loaded. If your code measures
text, wait for the returned promise first: text measured before the font
loads gets the fallback font's width. The template's `HowItWorks.tsx` shows
the pattern with `useDelayRender`.

## APIs you will use (Remotion 4)

- `useCurrentFrame()` and `useVideoConfig()` (which gives `fps`, `width`, `height`, `durationInFrames`).
- `interpolate(frame, [a, b], [from, to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)})`
- `spring({frame, fps, config: {damping, stiffness, mass}, durationInFrames})`
- `<Sequence from={f} durationInFrames={d}>`: children see a local frame that starts at 0.
  `<Series>` chains scenes one after another.
- `<Img src={staticFile('x.png')} />` for images. Rendering waits for them to load.
- Audio: `<Audio src={staticFile('voice.mp3')} />` from `@remotion/media`. In
  recent versions, `Audio` from `remotion` is a deprecated alias of `Html5Audio`.
- SVG stroke drawing: `const e = evolvePath(progress, d)` from `@remotion/paths`,
  then `<path d={d} strokeDasharray={e.strokeDasharray} strokeDashoffset={e.strokeDashoffset} />`.
  `getLength(d)` gives a path's length.
- Async work, such as measuring text or loading data:
  `const {delayRender, continueRender, cancelRender} = useDelayRender(); const [h] = useState(() => delayRender('why'));`
- Randomness: use `random('seed')` from `remotion`. Never use `Math.random()`,
  because frames render in parallel and out of order.

## Render

```bash
npx remotion still Main out/check.png --frame=120     # one still
node scripts/stills.mjs 30 120 450                    # many stills, one bundle (COMPOSITION=Main)
npx remotion render Main out/video.mp4                # the video
```

On 4 cores, 20 s of flat 1080p graphics renders in about 40 s. Rendering
twice gives identical frames.

## Pitfalls

- **Animate from the frame number only.** CSS transitions, CSS animations and
  timers don't follow the frame, so they come out wrong or jittery.
- **Version mismatches.** Different versions across `@remotion/*` packages
  fail with a version error. Pin them all to `$V`.
- **Dimensions.** Odd widths or heights can fail yuv420p encoding. Keep both even.
- **Text overflow.** Long words at large sizes overflow the frame. Measure them
  (`measureText`/`fitText` from `@remotion/layout-utils`, or canvas
  `measureText` after fonts load) and fail loudly rather than letting text clip.
- **Counting numbers.** Use a font with tabular figures (`tnum`, such as Inter)
  and `fontVariantNumeric: 'tabular-nums'`, or the digits will jitter.
  DM Sans has no `tnum`.
- **First render on a new machine.** Remotion may try to download Chrome
  Headless Shell from `storage.googleapis.com`. If that host is blocked,
  point `Config.setBrowserExecutable` at a local Chromium.
