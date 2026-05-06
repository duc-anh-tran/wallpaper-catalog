#!/usr/bin/env python3
"""Mark the top 30% of wallpapers as premium based on Pixabay popularity (downloads)."""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
CATALOG = os.path.join(REPO_ROOT, "docs", "wallpapers.json")
VIDEO_METADATA = os.path.join(REPO_ROOT, "originals", "videos", "_download_metadata.json")
IMAGE_METADATA = os.path.join(REPO_ROOT, "originals", "images", "_download_metadata.json")

PREMIUM_PERCENTAGE = 0.30


def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def main():
    catalog = load_json(CATALOG)
    if not catalog:
        print("Error: wallpapers.json not found")
        sys.exit(1)

    video_meta = load_json(VIDEO_METADATA)
    image_meta = load_json(IMAGE_METADATA)

    # Build lookup: filename (without extension) → downloads
    popularity = {}
    for info in video_meta.values():
        name = info["filename"].rsplit(".", 1)[0]
        popularity[name] = info.get("downloads", 0)
    for info in image_meta.values():
        name = info["filename"].rsplit(".", 1)[0]
        popularity[name] = info.get("downloads", 0)

    wallpapers = catalog["wallpapers"]

    # Score each wallpaper
    scored = []
    no_data = 0
    for w in wallpapers:
        downloads = popularity.get(w["id"], 0)
        if downloads == 0:
            no_data += 1
        scored.append((w, downloads))

    # Sort by popularity descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Top 30% are premium
    premium_count = max(1, int(len(scored) * PREMIUM_PERCENTAGE))
    premium_ids = set()
    for w, downloads in scored[:premium_count]:
        premium_ids.add(w["id"])

    # Apply to catalog
    changed = 0
    for w in wallpapers:
        should_be_premium = w["id"] in premium_ids
        if w.get("is_premium", False) != should_be_premium:
            changed += 1
        w["is_premium"] = should_be_premium

    with open(CATALOG, "w") as f:
        json.dump(catalog, f, indent=2)
        f.write("\n")

    total_premium = sum(1 for w in wallpapers if w["is_premium"])
    total = len(wallpapers)

    print(f"Premium marking complete:")
    print(f"  Total wallpapers: {total}")
    print(f"  Marked premium:   {total_premium} ({total_premium*100//total}%)")
    print(f"  Marked free:      {total - total_premium}")
    print(f"  Changed:          {changed}")
    if no_data > 0:
        print(f"  No popularity data: {no_data} (scored as 0 — re-run download script to fetch stats)")


if __name__ == "__main__":
    main()
