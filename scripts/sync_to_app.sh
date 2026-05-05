#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VIDEOS_DIR="$REPO_ROOT/originals/videos_compressed"
IMAGES_DIR="$REPO_ROOT/originals/images"
CATALOG="$REPO_ROOT/docs/wallpapers.json"
APP_ASSETS="$REPO_ROOT/../live-wallpaper/app/src/main/assets"

echo "=== Syncing bundled assets to Android app ==="

if [ ! -f "$CATALOG" ]; then
    echo "Error: wallpapers.json not found at $CATALOG"
    exit 1
fi

mkdir -p "$APP_ASSETS/videos"
mkdir -p "$APP_ASSETS/images"

copied=0
missing=0

echo ""
echo "--- Videos ---"
video_files=$(python3 -c "
import json
with open('$CATALOG') as f:
    data = json.load(f)
for w in data['wallpapers']:
    src = w.get('video_source', '')
    if src.startswith('bundled:videos/'):
        print(src.replace('bundled:videos/', ''))
")

while IFS= read -r filename; do
    [ -z "$filename" ] && continue
    src="$VIDEOS_DIR/$filename"
    dest="$APP_ASSETS/videos/$filename"

    if [ ! -f "$src" ]; then
        echo "  WARNING: Missing video: $filename"
        ((missing++))
        continue
    fi

    if [ -f "$dest" ] && [ "$(stat -f%z "$src" 2>/dev/null || stat -c%s "$src")" = "$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest")" ]; then
        echo "  Skipping: $filename (already synced)"
        continue
    fi

    echo "  Copying: $filename"
    cp "$src" "$dest"
    ((copied++))
done <<< "$video_files"

echo ""
echo "--- Images ---"
image_files=$(python3 -c "
import json
with open('$CATALOG') as f:
    data = json.load(f)
for w in data['wallpapers']:
    src = w.get('image_source', '')
    if src.startswith('bundled:images/'):
        print(src.replace('bundled:images/', ''))
")

while IFS= read -r filename; do
    [ -z "$filename" ] && continue
    src="$IMAGES_DIR/$filename"
    dest="$APP_ASSETS/images/$filename"

    if [ ! -f "$src" ]; then
        echo "  WARNING: Missing image: $filename"
        ((missing++))
        continue
    fi

    if [ -f "$dest" ] && [ "$(stat -f%z "$src" 2>/dev/null || stat -c%s "$src")" = "$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest")" ]; then
        echo "  Skipping: $filename (already synced)"
        continue
    fi

    echo "  Copying: $filename"
    cp "$src" "$dest"
    ((copied++))
done <<< "$image_files"

echo ""
echo "=== Copying wallpapers_fallback.json ==="
cp "$CATALOG" "$APP_ASSETS/wallpapers_fallback.json"
echo "  Copied wallpapers.json → wallpapers_fallback.json"

echo ""
echo "=== Sync complete ==="
echo "  Assets copied: $copied"
echo "  Missing: $missing"
echo "  App assets dir: $APP_ASSETS"
