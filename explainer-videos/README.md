# Explainer videos

Videos made from the 8-style prompt pack in [`PROMPTS.md`](PROMPTS.md). Each
video gets its own folder.

| # | Style | What you provide | Status in this cloud environment |
|---|---|---|---|
| 1 | Kinetic typography | Voiceover audio, font, 3 hex colours | Blocked on transcription. See the note below. |
| 2 | Whiteboard drawing | A topic | Can be built (Remotion works here) |
| 3 | Isometric workflow | Your steps, in order | **Done:** [`isometric-workflow/`](isometric-workflow/), the pet-portrait "How it works" sample |
| 4 | Animated data chart | A CSV | Can be built |
| 5 | Math / concept (Manim) | A concept | Manim installs from PyPI, which is reachable. Not tested yet. |
| 6 | App walkthrough | App screenshots, in order | Can be built |
| 7 | Paper collage | Background images and transparent PNG cutouts for each scene | Can be built once you send the images |
| 8 | Talking-head auto edit | The talking-head video | FFmpeg is installed. Blocked on transcription. See the note below. |

**Transcription note (styles 1 and 8).** Whisper needs to download its model
weights from `huggingface.co` or `openaipublic.azureedge.net`. This
environment's network policy blocks both. There are two ways around it:

- Add `huggingface.co` under Allowed domains in the environment's Network
  access settings, and keep the default package-manager list
  (https://code.claude.com/docs/en/cloud-environments#network-access).
- Use the connected ElevenLabs transcription, which costs credits.

To make the next video, tell Claude the style number, fill in the [brackets],
and attach the files.
