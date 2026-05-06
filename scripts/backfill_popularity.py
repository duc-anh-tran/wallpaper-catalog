#!/usr/bin/env python3
"""Backfill popularity stats (downloads, likes, views) for existing metadata entries."""

import json
import os
import sys
import time
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
VIDEO_METADATA = os.path.join(REPO_ROOT, "originals", "videos", "_download_metadata.json")
IMAGE_METADATA = os.path.join(REPO_ROOT, "originals", "images", "_download_metadata.json")

PIXABAY_VIDEOS_URL = "https://pixabay.com/api/videos/"
PIXABAY_IMAGES_URL = "https://pixabay.com/api/"


def backfill(metadata_path, api_url, api_key, media_type):
    with open(metadata_path) as f:
        metadata = json.load(f)

    needs_update = {k: v for k, v in metadata.items() if "downloads" not in v}
    print(f"\n{media_type}: {len(needs_update)}/{len(metadata)} entries need popularity data")

    updated = 0
    for pixabay_id, info in needs_update.items():
        url = f"{api_url}?key={api_key}&id={pixabay_id}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"  Skip {info['filename']}: API {resp.status_code}")
                continue
            hits = resp.json().get("hits", [])
            if not hits:
                print(f"  Skip {info['filename']}: not found")
                continue
            hit = hits[0]
            info["downloads"] = hit.get("downloads", 0)
            info["likes"] = hit.get("likes", 0)
            info["views"] = hit.get("views", 0)
            updated += 1
            if updated % 10 == 0:
                print(f"  Updated {updated}/{len(needs_update)}...")
        except Exception as e:
            print(f"  Error {info['filename']}: {e}")
        time.sleep(0.2)

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Done: {updated} entries updated")


def main():
    api_key = os.environ.get("PIXABAY_API_KEY")
    if not api_key:
        env_file = os.path.join(REPO_ROOT, ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("PIXABAY_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
        if not api_key:
            print("Error: PIXABAY_API_KEY not set")
            sys.exit(1)

    backfill(VIDEO_METADATA, PIXABAY_VIDEOS_URL, api_key, "Videos")
    backfill(IMAGE_METADATA, PIXABAY_IMAGES_URL, api_key, "Images")
    print("\nBackfill complete. Now run: python3 scripts/mark_premium.py")


if __name__ == "__main__":
    main()
