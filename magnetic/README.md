# MAGNETIC

One sound clip becomes a looping psychedelic Blender short, and every visual comes from the
sound. The clip is a 13-bar window of a dark glitch bass track synthesized for this piece. The
analysis measures it blind, the choreography turns the measurements into per-frame channels,
Cycles renders the world, and a glitch post pipeline keyed to the same measurements finishes it.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1. Make the sound | `audio/synth.py` | `audio/out/song.wav`, `truth.json` (ground-truth event log) |
| 2. Listen with math | `analysis/analyze.py` | `analysis.json`, `channels.npz`, `window.wav`, spectrogram texture |
|  | `analysis/validate.py` | `validation.txt`: the blind analysis checked against the synth's log |
|  | `analysis/plots.py` | `analysis_overview.png`, `canyon_texture.png`, `channels.png` |
| 3. Choreograph | `blender/choreo.py` | `choreo.npz` (channels), `shots.json`, `frameplan.json` |
| 4. Build the world | `blender/build.py --save` | the `.blend`, every channel baked on one controller object |
| 5. Render | `blender/render.py` | resumable, headless frame renders |
| 6. Glitch post | `post/post.py` | finished frames |
| 7. Deliver | `post/encode.py` | H.264 + AAC |

Rebuild everything:

```sh
py=/home/user/.venvs/mag/bin/python      # Python 3.11 with bpy 4.5 LTS, librosa, OpenCV, OpenColorIO
$py audio/synth.py
$py analysis/analyze.py audio/out/song.wav analysis/out
$py analysis/validate.py analysis/out audio/out/truth.json analysis/out/validation.png
$py analysis/plots.py audio/out/song.wav analysis/out
$py blender/choreo.py
$py blender/build.py --save /home/user/mag-work/magnetic.blend
$py blender/render.py /home/user/mag-work/magnetic.blend /home/user/mag-work/renders/final @frameplan --width 1920 --spp 32 --exr
$py post/post.py /home/user/mag-work/renders/final /home/user/mag-work/post/final
$py post/encode.py /home/user/mag-work/post/final out/magnetic.mp4
```
