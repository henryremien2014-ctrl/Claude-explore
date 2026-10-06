# Claude Explainer Video Prompts
**Ready-to-use prompts for Claude Code / Opus 5.5**

---

## Instructions for Claude

You are an expert video generation agent running inside Claude Code. Your job is to create high-quality explainer videos using the exact prompts and styles below.

**Rules:**
1. Work in an empty folder.
2. Use the strongest available model (Opus 5.5 or equivalent).
3. Install any tools you need (Remotion, Manim, FFmpeg, Whisper, etc.) yourself.
4. Always respect the “Avoid” list in every prompt — this is critical for quality.
5. Every prompt ends with a “Done means” criterion. Do not stop until that criterion is fully met.
6. After finishing a video, list the exact files created and confirm the Done means checks.

### How to use
- Pick one style at a time.
- Replace anything in [brackets] with your actual content.
- Attach any required files (voiceover, CSV, screenshots, video, etc.).
- Let Claude install dependencies and generate the final MP4.

---

## 1) Kinetic Typography

Build a 30-second kinetic typography video in Remotion from the voiceover I attached.

Transcribe it with word-level timestamps. Show each phrase on screen in sync with the audio. Make the 5 most important words bigger and use the accent color on them.

Font: [font name]. Colors: [background hex], [text hex], [accent hex].

**Avoid:** words flying in from every side, gradients, glow effects, every word bouncing.

**Done means:** a 1080x1080 MP4, captions within 2 frames of the audio, and stills checked at 0s, 15s, and 29s.

---

## 2) Whiteboard Drawing

Make a 45-second whiteboard explainer in Remotion about [topic].

Write a 6-scene script first. For each scene, draw one simple black line illustration as SVG paths and animate it drawing on stroke by stroke. Add a short label under each drawing.

**Avoid:** a drawing hand, clip art, color fills, more than one drawing per scene.

**Done means:** the script, the SVG files, and a 1920x1080 MP4 where every drawing finishes before the next scene starts.

---

## 3) Isometric Workflow

Animate this workflow as an isometric explainer in Remotion: [list your steps in order].

Each step is an isometric block that rises into place. A dot then travels along a path to the next block. Label each block in plain words.

**Avoid:** shadows on every element, neon colors, floating particles, camera spins.

**Done means:** a 20-second 1920x1080 MP4, every label readable on a phone screen, and a still checked at each step.

---

## 4) Animated Data Chart

Turn the CSV I attached into a 30-second animated chart video in Remotion.

Pick the chart type that fits the data and tell me why in one sentence. Numbers count up to their real values. Highlight the top value. Open with a title card that states the main finding.

**Avoid:** 3D bars, pie charts, a legend the viewer has to decode, gridlines on every value.

**Done means:** an MP4 where every number matches the CSV. Check 5 values against the file before you finish.

---

## 5) Math and Concept Explainer

Use Manim to make a 60-second explainer of [concept].

Write a short script first. Start with the idea in plain words, build the formula one term at a time, then show it as a graph. Each visual change matches one sentence of the script.

**Avoid:** walls of equations, more than 3 colors, text on top of moving shapes.

**Done means:** the script and a 1080p MP4 with no frame where text overlaps another element.

---

## 6) App Walkthrough

I attached [number] screenshots of my app in order. Build a 40-second walkthrough in Remotion.

In each screenshot, find the button or field the user clicks. Zoom in on it, move a cursor there, and show a one-line callout that explains the step.

**Avoid:** zooming past 2x, spinning transitions, phone or laptop mockups, callouts that cover the button.

**Done means:** a 1920x1080 MP4 where the cursor lands on the right element every time. List the coordinates you used so I can check them.

---

## 7) Paper Collage

Make a 30-second paper collage explainer in Remotion about [topic].

I attached background images and transparent PNG cutouts for each scene. Give each cutout a white paper edge. Move the background, middle, and front layers at different speeds, and use a torn-paper transition between scenes.

**Avoid:** a slow zoom on a flat photo, lens flares, film grain over everything.

**Done means:** an MP4 where each scene holds at least 4 seconds and every cutout edge looks clean at full size.

---

## 8) Talking-Head Auto Edit

Edit the talking-head video at [file path] with FFmpeg. Transcribe it with Whisper first.

Remove silences longer than 0.5 seconds. Add burned-in captions, 2 lines max, in the bottom third. Add a 1.2x zoom on the last sentence of each point.

**Avoid:** captions over the face, cuts in the middle of a word, a zoom on every cut.

Save the result as a new file. Never overwrite the original.

**Done means:** the new MP4, a list of every cut with timestamps, and the total time removed.

---

### Quality Tip
Anthropic’s guidance notes that simply asking Claude to “avoid a generic look” often just swaps one default style for another. Explicitly naming the exact things to avoid (as done in every prompt above) works much better.

When ready, tell Claude which style you want and provide the required files / fill in the [brackets].
