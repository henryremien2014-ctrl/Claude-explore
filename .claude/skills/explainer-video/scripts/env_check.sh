#!/usr/bin/env bash
# What can this machine build? Prints tools, a local Chromium, and which hosts
# the styles depend on are reachable. Safe to run anywhere; changes nothing.
echo "== tools"
for t in node npm npx python3 pip3 ffmpeg ffprobe latex dvisvgm make g++ cmake; do
  if command -v "$t" >/dev/null 2>&1; then printf '  %-8s %s\n' "$t" "$("$t" --version 2>&1 | head -1 | cut -c1-70)";
  else printf '  %-8s MISSING\n' "$t"; fi
done
python3 -c "import PIL; print('  Pillow   ', PIL.__version__)" 2>/dev/null || echo "  Pillow    MISSING (pip install pillow)"
if command -v ffmpeg >/dev/null 2>&1; then
  printf '  ffmpeg filters:'
  for f in ass subtitles silencedetect zoompan drawtext; do
    ffmpeg -hide_banner -filters 2>/dev/null | grep -qE " $f " && printf ' %s' "$f" || printf ' %s(MISSING)' "$f"
  done; echo
fi
echo "== chromium for Remotion (it downloads its own if none is set)"
ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell 2>/dev/null | sed 's/^/  /' || true
for c in google-chrome chromium chromium-browser; do command -v "$c" >/dev/null 2>&1 && echo "  $(command -v $c)"; done
echo "== network (HTTP status; 000 or 403 = blocked)"
for h in registry.npmjs.org pypi.org files.pythonhosted.org storage.googleapis.com fonts.gstatic.com \
         huggingface.co openaipublic.azureedge.net github.com archive.ubuntu.com; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "https://$h/" 2>/dev/null)
  printf '  %-28s %s\n' "$h" "${code:-000}"
done
cat <<'TXT'
== what needs what
  Remotion styles (1,2,3,4,6,7): node + npm registry; Chromium (local, or storage.googleapis.com to download)
  Manim (5): pip (pypi) + Cairo/Pango libs; LaTeX only if you use MathTex/Tex
  Whisper transcription (1,8): model weights from huggingface.co (whisper.cpp, faster-whisper)
                                or openaipublic.azureedge.net (openai-whisper)
  Talking-head edit (8): ffmpeg with ass/subtitles, silencedetect and zoompan
TXT
