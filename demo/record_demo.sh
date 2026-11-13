#!/usr/bin/env bash
# Record demo/run_demo.sh as a real screen capture (Xvfb + xterm + ffmpeg).
# Output: demo/demo.mp4 (1280x720, 15 fps). Exits 0 on success.
set -u
cd "$(dirname "$0")/.." || exit 1
OUT="demo/demo.mp4"
rm -f "$OUT"

Xvfb :99 -screen 0 1280x720x24 > /tmp/demo-xvfb.log 2>&1 &
XVFB_PID=$!
sleep 2
DISPLAY=:99 LC_ALL=C.UTF-8 xterm -u8 -fa "DejaVu Sans Mono" -fs 13 -geometry 152x44+0+0 \
  -bg black -fg "#e8e8e8" -e "bash demo/run_demo.sh; sleep 3" &
XTERM_PID=$!
sleep 1
ffmpeg -y -f x11grab -video_size 1280x720 -framerate 15 -i :99 \
  -c:v libx264 -preset veryfast -pix_fmt yuv420p -loglevel error "$OUT" &
FF_PID=$!
wait "$XTERM_PID"
kill "$FF_PID" 2>/dev/null
wait "$FF_PID" 2>/dev/null
kill "$XVFB_PID" 2>/dev/null
echo "---"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
ls -la "$OUT"
