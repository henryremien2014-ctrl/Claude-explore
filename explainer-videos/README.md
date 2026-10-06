# Explainer videos

Videos made from the 8-style prompt pack in [`PROMPTS.md`](PROMPTS.md). Each
video gets its own folder.

The pack is also a Claude skill:
[`.claude/skills/explainer-video/`](../.claude/skills/explainer-video/SKILL.md).
Any Claude Code session in this repo loads it automatically. Just describe the
video you want ("make a whiteboard explainer about X", "turn this CSV into an
animated chart"); you don't need to paste the pack.

| # | Style | What you provide | Status |
|---|---|---|---|
| 1 | Kinetic typography | Voiceover audio, a font, 3 hex colours | Recipe only. Transcription is blocked here (see below). |
| 2 | Whiteboard drawing | A topic | Built once in the skill's tests (all checks passed) |
| 3 | Isometric workflow | Your steps, in order | **Ready-made template.** Delivered: [`isometric-workflow/`](isometric-workflow/), the pet-portrait "How it works" video |
| 4 | Animated data chart | A CSV | Built once in the skill's tests (all checks passed) |
| 5 | Math / concept (Manim) | A concept | Recipe only. Manim installs from PyPI; not tested yet. |
| 6 | App walkthrough | App screenshots, in order | Recipe only |
| 7 | Paper collage | Background images and transparent PNG cutouts for each scene | Recipe only. Needs your images. |
| 8 | Talking-head auto edit | The talking-head video | Recipe only. FFmpeg is ready; transcription is blocked here (see below). |

**Transcription note (styles 1 and 8).** Whisper downloads its model weights
from `huggingface.co` or `openaipublic.azureedge.net`. This environment's
network policy blocks both. There are two ways around it:

- Add `huggingface.co` under Allowed domains in the environment's Network
  access settings, and keep the default package-manager list
  (https://code.claude.com/docs/en/cloud-environments#network-access).
- Use the connected ElevenLabs transcription, which costs credits.

## How the skill was tested (2026-10-06)

Three tasks were each run once with the skill and once without it, then graded
against the pack's "Done means" and "Avoid" items.

| Task | With skill | Without skill |
|---|---|---|
| Isometric "how it works", 5 steps (podcast editing service) | 11/11 checks, 14 min | 5/11, 51 min |
| 45 s whiteboard: compound interest | 10/10, 31 min | 3/10, 42 min |
| Animated chart from a 12-month signups CSV | 9/9, 26 min | 4/9, 17 min |

The runs without the skill made polished videos, but they followed a generic
idea of an explainer and broke the pack's rules:

- **Isometric:** 45 s instead of 20, with shadows and confetti.
- **Whiteboard:** a drawing hand and colour, and no SVG files.
- **Chart:** 13 s long, with no finding on the title card and no highlight.

The runs with the skill also turned up about a dozen problems in the skill
itself (text sizes, margins, colour tagging, tabular digits for counters,
version pinning, a wrong example ratio and more). Those are fixed in the
version committed here.
