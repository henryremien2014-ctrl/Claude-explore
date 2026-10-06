# 1) Kinetic typography

**Status:** recipe only. Not yet built with this skill, so check each step as you go.

## The prompt

> Build a 30-second kinetic typography video in Remotion from the voiceover I attached.
>
> Transcribe it with word-level timestamps. Show each phrase on screen in sync with the audio. Make the 5 most important words bigger and use the accent color on them.
>
> Font: [font name]. Colors: [background hex], [text hex], [accent hex].
>
> **Avoid:** words flying in from every side, gradients, glow effects, every word bouncing.
>
> **Done means:** a 1080x1080 MP4, captions within 2 frames of the audio, and stills checked at 0s, 15s, and 29s.

## Inputs

- **The voiceover file** (mp3, wav or m4a). It is required; don't synthesize one
  for a real deliverable. If the user wants a voice generated, that's a
  separate, explicit step using their own TTS tool or credits.
- **A font name.** Most Google Fonts are on npm as `@fontsource/<name>`.
- **Three hex colours.** If they're missing, propose a set and say so in the report.

## Transcribe with word timestamps

Run `scripts/env_check.sh` first, then use the first option that works:

1. **whisper.cpp** through `@remotion/install-whisper-cpp`, using
   `installWhisperCpp`, `downloadWhisperModel`, then `transcribe` with
   token-level timestamps, then `toCaptions`. It needs `github.com`,
   `huggingface.co` and a C++ toolchain.
2. **faster-whisper** (`pip install faster-whisper`) with
   `word_timestamps=True`. Its model comes from `huggingface.co`.
3. **openai-whisper** (`pip install openai-whisper`, which pulls in torch) with
   `word_timestamps=True`. Its model comes from `openaipublic.azureedge.net`.
4. **A speech-to-text connector the user already has**, for example
   ElevenLabs transcription. It costs credits, so ask first.
5. **None of these reachable:** name the blocked host and how to allow it.
   Don't estimate timestamps by hand.

Save the result as `words.json`, a list of `{text, start, end}` in seconds.
Whisper's word *starts* are often 50–300 ms off. Before trusting them,
compare them with the audio's loudness. Decode with
`ffmpeg -i voice.mp3 -ac 1 -ar 16000 -f s16le -`, compute RMS in 10 ms
windows, and check that each word that follows a pause starts where the level
rises. If starts are consistently late or early, snap each start to the
nearest rise within ±150 ms. Note in the report that you did this.

## Build

- **Composition:** 1080×1080 at 30 fps. Set `durationInFrames` to
  `ceil(audioSeconds × 30)`. If the voiceover isn't 30 s, follow the audio and
  say so.
- **Phrases:** group words into phrases of 2–5 words. Break at punctuation or
  at pauses longer than 0.3 s. Show one phrase at a time, centred, on at most
  two lines.
- **Timing:** each word appears at `Math.round(start × fps)`, the frame its
  sound starts. A phrase leaves when the next phrase's first word arrives.
- **Entrances:** every word enters the same way, for example a 5-frame fade
  with a 16 px rise. Nothing comes in from the sides.
- **The 5 key words:** pick them by meaning (the words that carry the message,
  such as key nouns, verbs and numbers), not by how often they occur. Make
  them 1.4–1.6× bigger and use the accent colour. List them in the report.
- **Flat colour only:** no gradients, no glow, no text-shadow. Only the 5 key
  words may get a short, single scale-in.
- **Audio:** `<Audio src={staticFile('voiceover.mp3')} />` from `@remotion/media`.
- **Sizes:** body text should be 64 px or more and key words 96 px or more.
  On a 1080-wide square video, pt = px × 390 / 1080. Use `fitText` from
  `@remotion/layout-utils` so a long phrase never overflows.

## Verify

- `verify_video.py out/video.mp4 --width 1080 --height 1080 --duration <audio s> --audio required`
- **Sync:** write a table of word, audio start (s), first frame shown and
  error (frames), generated from the same `words.json` and frame formula the
  video uses. Every error must be ≤ 2 frames; `Math.round` keeps it at 0.5 or
  less. Put the maximum error in the report, and note how you checked that the
  timestamps match the audio (see the loudness check above).
- `extract_stills.py out/video.mp4 --times 0 15 29`. Open each still and
  confirm three things:
  - The phrase on screen is the one spoken at that moment (check against `words.json`).
  - The key words are big and in the accent colour.
  - Nothing is clipped.
- `phone_check.py <still> --video-width 1080 --size body=64 --size key=96`

## Lessons

(Add what you learn when you build this style.)
