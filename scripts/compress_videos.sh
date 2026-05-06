#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VIDEOS_DIR="$REPO_ROOT/originals/videos"

LQ_MODE=false
for arg in "$@"; do
    [ "$arg" = "--lq" ] && LQ_MODE=true
done

if [ "$LQ_MODE" = true ]; then
    COMPRESSED_DIR="$REPO_ROOT/originals/videos_compressed"
    SCALE="720:1280"
    CRF=28
    echo "  Mode: STANDARD (720x1280, CRF 28) — for bundled/APK"
else
    COMPRESSED_DIR="$REPO_ROOT/originals/videos_compressed_hq"
    SCALE="1080:1920"
    CRF=23
    echo "  Mode: HIGH QUALITY (1080x1920, CRF 23) — for remote/R2"
fi

if ! command -v ffmpeg &>/dev/null; then
    echo "Error: ffmpeg is not installed."
    echo "Install with: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Linux)"
    exit 1
fi

mkdir -p "$COMPRESSED_DIR"

echo "=== Compressing videos ==="
echo "  Source:      $VIDEOS_DIR"
echo "  Destination: $COMPRESSED_DIR"
echo ""

compressed=0
skipped=0
total_before=0
total_after=0

filesize() {
    stat -f%z "$1" 2>/dev/null || stat -c%s "$1"
}

human_size() {
    local bytes=$1
    if [ "$bytes" -ge 1048576 ]; then
        echo "$(echo "scale=1; $bytes / 1048576" | bc)MB"
    else
        echo "$(echo "scale=0; $bytes / 1024" | bc)KB"
    fi
}

for video in "$VIDEOS_DIR"/*.mp4; do
    [ -f "$video" ] || continue
    basename="$(basename "$video")"
    output="$COMPRESSED_DIR/$basename"

    if [ -f "$output" ]; then
        echo "  Skipping: $basename (compressed version exists)"
        size_before=$(filesize "$video")
        size_after=$(filesize "$output")
        total_before=$((total_before + size_before))
        total_after=$((total_after + size_after))
        ((skipped++))
        continue
    fi

    size_before=$(filesize "$video")
    total_before=$((total_before + size_before))

    echo "  Compressing: $basename ($(human_size "$size_before"))..."
    ffmpeg -y -i "$video" \
        -t 15 \
        -vf "scale=${SCALE}:force_original_aspect_ratio=decrease,pad=${SCALE}:(ow-iw)/2:(oh-ih)/2" \
        -c:v libx264 \
        -crf "$CRF" \
        -preset slow \
        -an \
        -movflags +faststart \
        "$output" 2>/dev/null

    size_after=$(filesize "$output")
    total_after=$((total_after + size_after))
    ratio=$(echo "scale=0; 100 - ($size_after * 100 / $size_before)" | bc)

    echo "    $(human_size "$size_before") → $(human_size "$size_after") (${ratio}% smaller)"
    ((compressed++))
done

echo ""
echo "=== Compression complete ==="
echo "  Compressed: $compressed"
echo "  Skipped:    $skipped"
echo "  Total before: $(human_size "$total_before")"
echo "  Total after:  $(human_size "$total_after")"
if [ "$total_before" -gt 0 ]; then
    saved=$((total_before - total_after))
    echo "  Space saved:  $(human_size "$saved")"
fi
