#!/usr/bin/env bash
set -euo pipefail

# Add this near the top of run_all.sh, before it calls the Python script:
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  Wallpaper Catalog — Full Pipeline"
echo "============================================"

echo ""
echo "Step 1/3: Downloading videos from Pixabay..."
echo "--------------------------------------------"
python3 "$SCRIPT_DIR/download_from_pixabay.py"

echo ""
echo "Step 2/3: Generating thumbnails & updating catalog..."
echo "--------------------------------------------"
bash "$SCRIPT_DIR/generate_catalog.sh"

echo ""
echo "Step 3/3: Syncing to Android app..."
echo "--------------------------------------------"
bash "$SCRIPT_DIR/sync_to_app.sh"

echo ""
echo "============================================"
echo "  Pipeline complete!"
echo "============================================"

video_count=$(find "$REPO_ROOT/originals/videos" -name "*.mp4" 2>/dev/null | wc -l | tr -d ' ')
thumb_count=$(find "$REPO_ROOT/docs/thumbs" -name "*.jpg" 2>/dev/null | wc -l | tr -d ' ')
catalog_count=$(python3 -c "
import json
with open('$REPO_ROOT/docs/wallpapers.json') as f:
    print(len(json.load(f)['wallpapers']))
" 2>/dev/null || echo "?")

echo ""
echo "  Videos:     $video_count"
echo "  Thumbnails: $thumb_count"
echo "  Catalog:    $catalog_count wallpapers"
echo ""

read -rp "Push to GitHub? (y/n): " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Pushing wallpaper-catalog..."
    cd "$REPO_ROOT"
    git add .
    git commit -m "update catalog"
    git push
    echo "Done! Changes pushed to GitHub."
else
    echo "Skipped push. You can push manually later."
fi
