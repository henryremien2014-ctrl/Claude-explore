# 4) Animated data chart

**Status:** built once with this skill (a 12-month signups chart), and it passed
every Done-means check. The notes on sizes, tabular figures and highlighting
come from that build.

## The prompt

> Turn the CSV I attached into a 30-second animated chart video in Remotion.
>
> Pick the chart type that fits the data and tell me why in one sentence. Numbers count up to their real values. Highlight the top value. Open with a title card that states the main finding.
>
> **Avoid:** 3D bars, pie charts, a legend the viewer has to decode, gridlines on every value.
>
> **Done means:** an MP4 where every number matches the CSV. Check 5 values against the file before you finish.

## Inputs

- **The CSV.** It is required; never make up or "clean up" numbers.
- Optional: who will watch it and what they should take away.

## Read the data with code, not by eye

- **Parse it** with Python's `csv`/pandas or papaparse in Node. Print the
  columns, the types, the row count, the minimum and maximum, and the exact
  strings you will show.
- **Note the formatting:** decimals, thousands separators, units, and any
  missing values.
- **Generate the data module from the file** (for example a small script that
  writes `src/data.ts` from the CSV) and copy the CSV into the project. Numbers
  in the video then come straight from the file; never retype them.

## Choose the chart

Choose the chart and say why in one sentence in the report.

| Data shape | Chart |
|---|---|
| Categories with one value | Sorted bar chart; horizontal if the labels are long |
| Change over time | Line chart, or columns for 12 periods or fewer |
| Parts of a whole | Stacked or 100% bar, **never a pie** |
| Two measures per category | Grouped bars or a dot plot |

No 3D, and no dual axes unless the data truly needs them. If a dataviz skill
is available, load it for palette and mark guidance.

## Build (1920×1080, 30 fps, 30 s)

- **0–3 s, title card.** State the main finding as a sentence with its key
  number, in the form "<Metric> peaked in <month> at <value>, <ratio>×
  <baseline>". Compute every number in it from the data, then check the
  arithmetic; round ratios honestly (3.89 is "3.9×", never "nearly 3×").
  Frame 0 should already show the full title card, since players and email
  previews use the first frame as the thumbnail.
- **3–20 s, the build.**
  - Bars or the line grow from zero, staggered, while each value label counts up.
  - Count up with `interpolate(frame, [s, e], [0, value], {clamp, easing})`.
  - Once a count finishes, show the **source string** from the CSV,
    formatted exactly as in the file. This stops float rounding (4819.9996)
    from ever reaching the screen.
- **20–24 s, the highlight.** Give the top value the accent colour and a short
  callout. Everything else stays neutral grey.
- **24–30 s, the hold.** Keep the full chart up, with one summary line.
- **Labels and gridlines.**
  - Put category names and values directly on or next to the marks, with no
    legend.
  - Use no gridlines, or just a baseline plus 2–4 light reference lines.
- **Sizes.** Charts are the one place labels may go below the 60 px default.
  - Value labels need 48 px or more and category labels 44 px or more. On a
    1920-wide frame, 44 px is about 9 pt on a phone.
  - Work out the space first: a label's width is digits × ~0.65 em × font
    size, and it must fit its slot (frame width minus margins, divided by the
    number of bars) with about 25 px to spare. Twelve 4-digit values on 1920 px
    allow about 50 px.
  - Fewer, larger numbers beat many small ones. If there are more than about
    15 rows, show the top 10 and say so.
- **Numbers that count need tabular figures.** If digit widths differ, a
  counting label wobbles sideways every frame.
  - Use a font with the `tnum` feature, such as Inter or IBM Plex Sans, with
    `fontVariantNumeric: 'tabular-nums'`. DM Sans has no `tnum`.
  - Check a font with fontTools: `'tnum'` should appear among its GSUB features.
  - Measure tabular text with a hidden DOM span after the fonts load. Canvas
    `measureText` can't apply `tnum`.
- **Formatting.** Integers may gain thousands separators (4820 to 4,820); it's
  the same number. Keep the source's decimals and units. Say which you did in
  the report.
- **Highlight in two steps.** During the build, all bars are a mid neutral. At
  the highlight, the other bars recede to a light neutral while the top value
  takes the accent. That separates it by lightness as well as hue, so it reads
  in greyscale and for colour-blind viewers.
- **A layout check at render time pays off.** Build a box for every text
  element in the final frame, then fail the render if one leaves the 60 px
  margin, comes within 8 px of other text, or overlaps a bar.

## Verify

- **Data path:** check that the generated data module equals the CSV (same
  values, same strings). Do it with a script, not by eye.
- **5 values:** include the maximum and the minimum. Extract a still after the
  counts finish (for example `--times 21 29`), read the numbers on screen, and
  compare them with the CSV. Put a table in the report with columns: row,
  CSV value, shown in the video, match.
- **Title card:** extract a still at about 1.5 s and confirm the finding it
  states agrees with the data.
- **OCR (optional).** Where Tesseract is available, it can read the labels
  back from the stills as a second check: `apt-get install tesseract-ocr`,
  then `tesseract still.png - --psm 11`.
- `verify_video.py out/video.mp4 --width 1920 --height 1080 --duration 30`
- **Email delivery.** Investor updates often go out by email, where MP4 doesn't
  play inline. Offer a poster PNG of the final frame, and a GIF if needed.
- **Avoid list:** look at the stills for pie or 3D charts, any legend, and
  dense gridlines.

## Lessons

(Add what you learn when you build this style.)
