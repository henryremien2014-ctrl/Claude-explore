# 8) Talking-head auto edit

**Status:** recipe only. Not yet built with this skill, so check each step as you go.

## The prompt

> Edit the talking-head video at [file path] with FFmpeg. Transcribe it with Whisper first.
>
> Remove silences longer than 0.5 seconds. Add burned-in captions, 2 lines max, in the bottom third. Add a 1.2x zoom on the last sentence of each point.
>
> **Avoid:** captions over the face, cuts in the middle of a word, a zoom on every cut.
>
> Save the result as a new file. Never overwrite the original.
>
> **Done means:** the new MP4, a list of every cut with timestamps, and the total time removed.

## Inputs

- **The video file path.** It is required.
- Optionally, how the user splits their talk into "points".

## Never overwrite the original

Write everything to a new folder, for example
`<name>-edit/<name>-edited.mp4`. Before every `ffmpeg` call, check that the
output path differs from the input. Never use `-y` with an output name that
could match the input.

## Steps

1. **Probe the input:** `verify_video.py <input> --audio required`. Note the
   fps, the resolution and the audio rate.
2. **Transcribe with word timestamps,** using the options in style 1's
   reference. Save the result as `words.json`.
3. **Find the silences:**
   - Measure the level with `ffmpeg -i in.mp4 -af volumedetect -f null -`.
   - Run `ffmpeg -i in.mp4 -af silencedetect=noise=<mean-25dB>:d=0.5 -f null - 2>&1 | grep silence_`.
4. **Plan the cuts:**
   - Remove each silence longer than 0.5 s, keeping 0.12–0.2 s of padding on
     both sides so breaths and word tails survive.
   - A cut point must never fall inside a word (between a word's start and
     end in `words.json`); move it into the gap.
   - Write `cuts.csv` with the columns `#, start, end, removed_s`, in the
     original's timestamps.
5. **Choose the points and zooms:**
   - Split the transcript into points: topic segments, marked by phrases like
     "first / second", long pauses, or a change of subject.
   - List the points in the report.
   - For the **last sentence of each point only**, apply a 1.2× punch-in
     (crop to 1/1.2 of the frame, centred on the face, then scale back up)
     for that sentence's duration.
6. **Find the face:** `pip install opencv-python-headless`. Its Haar cascade
   files ship inside the package (`cv2.data.haarcascades`). Detect the face on
   frames sampled every 2 s and use the median box to centre the zooms and
   keep the captions below the chin.
7. **Write the captions** as an ASS file built from the words, with times
   remapped to the edited timeline:
   - at most 2 lines, about 32 characters per line;
   - in the bottom third, with `MarginV` set so the top of a two-line caption
     stays below the face box;
   - a bold sans font at about 5.5% of the frame height, white with a dark
     outline (no glow and no shadow box).
8. **Render:**
   - Use trim/atrim segments plus concat, re-encoded so cuts are
     frame-accurate.
   - Apply the punch-in on the zoom segments.
   - Burn the captions with `ass=captions.ass`.
   - Add 5–10 ms audio fades at every cut so there are no clicks.
   - Encode with `libx264 -crf 18 -pix_fmt yuv420p` and `aac 192k`, at the
     original fps.

## Verify

- `verify_video.py <output> --audio required`. The new duration must equal
  the original minus the total removed (±0.1 s).
- **Cuts:** in the report, list every cut with its start and end in the
  original's time, plus the total time removed. Confirm with a script that no
  cut overlaps a word.
- **Stills:** extract stills at several caption moments and during each zoom.
  Check that captions are in the bottom third, never over the face, and at
  most two lines; and that zooms appear only on point-ending sentences.
- Confirm the original file is unchanged: same size, and the same hash as
  before you started.

## Lessons

(Add what you learn when you build this style.)
