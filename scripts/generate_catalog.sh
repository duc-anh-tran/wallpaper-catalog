#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VIDEOS_DIR="$REPO_ROOT/originals/videos"
IMAGES_DIR="$REPO_ROOT/originals/images"
THUMBS_DIR="$REPO_ROOT/docs/thumbs"
CATALOG="$REPO_ROOT/docs/wallpapers.json"
VIDEO_METADATA="$VIDEOS_DIR/_download_metadata.json"
IMAGE_METADATA="$IMAGES_DIR/_download_metadata.json"

GITHUB_PAGES_BASE="https://duc-anh-tran.github.io/wallpaper-catalog"

if ! command -v ffmpeg &>/dev/null; then
    echo "Error: ffmpeg is not installed."
    echo "Install with: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Linux)"
    exit 1
fi

mkdir -p "$THUMBS_DIR"

echo "=== Generating video thumbnails ==="
thumb_created=0
thumb_skipped=0

for video in "$VIDEOS_DIR"/*.mp4; do
    [ -f "$video" ] || continue
    basename="$(basename "$video" .mp4)"
    thumb="$THUMBS_DIR/${basename}.jpg"

    if [ -f "$thumb" ]; then
        ((thumb_skipped++))
        continue
    fi

    echo "  Generating: ${basename}.jpg"
    ffmpeg -y -i "$video" -ss 00:00:02 -vframes 1 -vf "scale=720:-1" -q:v 3 "$thumb" 2>/dev/null
    ((thumb_created++))
done

echo "  Video thumbnails created: $thumb_created, skipped: $thumb_skipped"

echo ""
echo "=== Generating image thumbnails ==="
img_thumb_created=0
img_thumb_skipped=0

for image in "$IMAGES_DIR"/*.jpg; do
    [ -f "$image" ] || continue
    basename="$(basename "$image" .jpg)"
    thumb="$THUMBS_DIR/${basename}.jpg"

    if [ -f "$thumb" ]; then
        ((img_thumb_skipped++))
        continue
    fi

    echo "  Generating: ${basename}.jpg"
    ffmpeg -y -i "$image" -vf "scale=720:-1" -q:v 3 "$thumb" 2>/dev/null
    ((img_thumb_created++))
done

echo "  Image thumbnails created: $img_thumb_created, skipped: $img_thumb_skipped"

echo ""
echo "=== Updating wallpapers.json ==="

python3 - "$CATALOG" "$VIDEOS_DIR" "$IMAGES_DIR" "$VIDEO_METADATA" "$IMAGE_METADATA" "$GITHUB_PAGES_BASE" << 'PYTHON_SCRIPT'
import sys
import os
import json

catalog_path = sys.argv[1]
videos_dir = sys.argv[2]
images_dir = sys.argv[3]
video_metadata_path = sys.argv[4]
image_metadata_path = sys.argv[5]
pages_base = sys.argv[6]

if os.path.exists(catalog_path):
    with open(catalog_path) as f:
        catalog = json.load(f)
else:
    catalog = {
        "version": 1,
        "categories": ["All", "Nature", "City", "Space", "Abstract", "Seasonal"],
        "wallpapers": [],
    }

video_metadata = {}
if os.path.exists(video_metadata_path):
    with open(video_metadata_path) as f:
        video_metadata = json.load(f)

image_metadata = {}
if os.path.exists(image_metadata_path):
    with open(image_metadata_path) as f:
        image_metadata = json.load(f)

video_meta_by_filename = {}
for vid_id, info in video_metadata.items():
    video_meta_by_filename[info["filename"]] = info

image_meta_by_filename = {}
for img_id, info in image_metadata.items():
    image_meta_by_filename[info["filename"]] = info

existing_ids = {w["id"] for w in catalog["wallpapers"]}
max_sort = max((w.get("sort_order", 0) for w in catalog["wallpapers"]), default=0)

added = 0

# Add video entries
video_files = sorted(f for f in os.listdir(videos_dir) if f.endswith(".mp4"))
for filename in video_files:
    vid_id = os.path.splitext(filename)[0]
    if vid_id in existing_ids:
        continue

    pretty_name = vid_id.replace("_", " ").title()
    category = "Nature"
    if filename in video_meta_by_filename:
        category = video_meta_by_filename[filename].get("category", "Nature")

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
    print(f"  Added video: {vid_id} ({category})")

# Add image entries
if os.path.isdir(images_dir):
    image_files = sorted(f for f in os.listdir(images_dir) if f.endswith(".jpg") and not f.startswith("_"))
    for filename in image_files:
        img_id = os.path.splitext(filename)[0]
        if img_id in existing_ids:
            continue

        pretty_name = img_id.replace("_", " ").title()
        category = "Nature"
        if filename in image_meta_by_filename:
            category = image_meta_by_filename[filename].get("category", "Nature")

        max_sort += 1
        entry = {
            "id": img_id,
            "name": pretty_name,
            "category": category,
            "type": "image",
            "image_source": f"bundled:images/{filename}",
            "thumbnail_url": f"{pages_base}/thumbs/{img_id}.jpg",
            "is_premium": False,
            "sort_order": max_sort,
        }
        catalog["wallpapers"].append(entry)
        added += 1
        print(f"  Added image: {img_id} ({category})")

with open(catalog_path, "w") as f:
    json.dump(catalog, f, indent=2)
    f.write("\n")

total = len(catalog["wallpapers"])
print(f"\n  New entries added: {added}")
print(f"  Total wallpapers in catalog: {total}")
PYTHON_SCRIPT

echo ""
echo "=== Catalog generation complete ==="
