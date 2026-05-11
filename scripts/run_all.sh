#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$REPO_ROOT/.env" ]; then
    export $(cat "$REPO_ROOT/.env" | grep -v '^#' | xargs)
fi

BUNDLED_MODE=false
for arg in "$@"; do
    [ "$arg" = "--bundled" ] && BUNDLED_MODE=true
done

if [ "$BUNDLED_MODE" = true ]; then
    echo "============================================"
    echo "  Wallpaper Catalog — Bundled Pipeline"
    echo "============================================"

    echo ""
    echo "Step 1/7: Downloading from Pixabay..."
    echo "--------------------------------------------"
    python3 "$SCRIPT_DIR/download_from_pixabay.py"

    echo ""
    echo "Step 2/7: Compressing videos (LQ for APK)..."
    echo "--------------------------------------------"
    bash "$SCRIPT_DIR/compress_videos.sh" --lq

    echo ""
    echo "Step 3/7: Generating thumbnails & catalog..."
    echo "--------------------------------------------"
    bash "$SCRIPT_DIR/generate_catalog.sh" --bundled

    echo ""
    echo "Step 4/7: Syncing to Android app..."
    echo "--------------------------------------------"
    bash "$SCRIPT_DIR/sync_to_app.sh"

    echo ""
    echo "Step 5/7: Marking premium (top 30% by popularity)..."
    echo "--------------------------------------------"
    python3 "$SCRIPT_DIR/mark_premium.py"

    echo ""
    echo "Step 6/7: Reordering catalog for variety..."
    echo "--------------------------------------------"
    python3 "$SCRIPT_DIR/reorder_catalog.py"
else
    echo "============================================"
    echo "  Wallpaper Catalog — Remote Pipeline (R2)"
    echo "============================================"

    echo ""
    echo "Step 1/6: Downloading from Pixabay..."
    echo "--------------------------------------------"
    python3 "$SCRIPT_DIR/download_from_pixabay.py"

    echo ""
    echo "Step 2/6: Compressing videos (HQ for R2)..."
    echo "--------------------------------------------"
    bash "$SCRIPT_DIR/compress_videos.sh"

    echo ""
    echo "Step 3/6: Generating thumbnails & catalog (remote)..."
    echo "--------------------------------------------"
    bash "$SCRIPT_DIR/generate_catalog.sh"

    echo ""
    echo "Step 4/6: Uploading to Cloudflare R2..."
    echo "--------------------------------------------"
    bash "$SCRIPT_DIR/upload_to_r2.sh"

    echo ""
    echo "Step 5/6: Marking premium (top 30% by popularity)..."
    echo "--------------------------------------------"
    python3 "$SCRIPT_DIR/mark_premium.py"

    echo ""
    echo "Step 6/6: Reordering catalog for variety..."
    echo "--------------------------------------------"
    python3 "$SCRIPT_DIR/reorder_catalog.py"
fi

echo ""
echo ""
echo "============================================"
echo "  Pipeline complete!"
echo "============================================"

video_count=$(find "$REPO_ROOT/originals/videos" -name "*.mp4" 2>/dev/null | wc -l | tr -d ' ')
image_count=$(find "$REPO_ROOT/originals/images" -name "*.jpg" ! -name "_*" 2>/dev/null | wc -l | tr -d ' ')
catalog_count=$(python3 -c "
import json
with open('$REPO_ROOT/docs/wallpapers.json') as f:
    print(len(json.load(f)['wallpapers']))
" 2>/dev/null || echo "?")

echo ""
echo "  Videos:     $video_count"
echo "  Images:     $image_count"
echo "  Catalog:    $catalog_count wallpapers"
if [ "$BUNDLED_MODE" = true ]; then
    echo "  Mode:       bundled (APK assets)"
else
    echo "  Mode:       remote (Cloudflare R2)"
fi
echo ""

read -rp "Push catalog to GitHub? (y/n): " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Pushing wallpaper-catalog..."
    cd "$REPO_ROOT"
    git add docs/
    git commit -m "update catalog" || echo "  Nothing to commit."
    git push
    echo "Done! Catalog pushed to GitHub Pages."
else
    echo "Skipped push. You can push manually later."
fi
