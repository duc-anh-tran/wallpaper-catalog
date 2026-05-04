#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VIDEOS_DIR="$REPO_ROOT/originals/videos"
THUMBS_DIR="$REPO_ROOT/docs/thumbs"
CATALOG="$REPO_ROOT/docs/wallpapers.json"
METADATA="$VIDEOS_DIR/_download_metadata.json"

GITHUB_PAGES_BASE="https://duc-anh-tran.github.io/wallpaper-catalog"

if ! command -v ffmpeg &>/dev/null; then
    echo "Error: ffmpeg is not installed."
    echo "Install with: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Linux)"
    exit 1
fi

mkdir -p "$THUMBS_DIR"

echo "=== Generating thumbnails ==="
thumb_created=0
thumb_skipped=0

for video in "$VIDEOS_DIR"/*.mp4; do
    [ -f "$video" ] || continue
    basename="$(basename "$video" .mp4)"
    thumb="$THUMBS_DIR/${basename}.jpg"

    if [ -f "$thumb" ]; then
        echo "  Skipping thumbnail: ${basename}.jpg (exists)"
        ((thumb_skipped++))
        continue
    fi

    echo "  Generating: ${basename}.jpg"
    ffmpeg -y -i "$video" -ss 00:00:02 -vframes 1 -vf "scale=720:-1" -q:v 3 "$thumb" 2>/dev/null
    ((thumb_created++))
done

echo "  Thumbnails created: $thumb_created, skipped: $thumb_skipped"

echo ""
echo "=== Updating wallpapers.json ==="

python3 - "$CATALOG" "$VIDEOS_DIR" "$METADATA" "$GITHUB_PAGES_BASE" << 'PYTHON_SCRIPT'
import sys
import os
import json

catalog_path = sys.argv[1]
videos_dir = sys.argv[2]
metadata_path = sys.argv[3]
pages_base = sys.argv[4]

if os.path.exists(catalog_path):
    with open(catalog_path) as f:
        catalog = json.load(f)
else:
    catalog = {
        "version": 1,
        "categories": ["All", "Nature", "City", "Space", "Abstract", "Seasonal"],
        "wallpapers": [],
    }

metadata = {}
if os.path.exists(metadata_path):
    with open(metadata_path) as f:
        metadata = json.load(f)

metadata_by_filename = {}
for vid_id, info in metadata.items():
    metadata_by_filename[info["filename"]] = info

existing_ids = {w["id"] for w in catalog["wallpapers"]}

max_sort = max((w.get("sort_order", 0) for w in catalog["wallpapers"]), default=0)

added = 0
video_files = sorted(f for f in os.listdir(videos_dir) if f.endswith(".mp4"))

for filename in video_files:
    vid_id = os.path.splitext(filename)[0]

    if vid_id in existing_ids:
        continue

    pretty_name = vid_id.replace("_", " ").title()

    category = "Nature"
    if filename in metadata_by_filename:
        category = metadata_by_filename[filename].get("category", "Nature")

    max_sort += 1
    entry = {
        "id": vid_id,
        "name": pretty_name,
        "category": category,
        "type": "video",
        "video_source": f"bundled:videos/{filename}",
        "thumbnail_url": f"{pages_base}/thumbs/{vid_id}.jpg",
        "is_premium": False,
        "sort_order": max_sort,
    }
    catalog["wallpapers"].append(entry)
    added += 1
    print(f"  Added: {vid_id} ({category})")

with open(catalog_path, "w") as f:
    json.dump(catalog, f, indent=2)
    f.write("\n")

total = len(catalog["wallpapers"])
print(f"\n  New entries added: {added}")
print(f"  Total wallpapers in catalog: {total}")
PYTHON_SCRIPT

echo ""
echo "=== Catalog generation complete ==="
