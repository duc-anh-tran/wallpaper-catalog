#!/usr/bin/env python3
"""Download wallpaper videos from Pixabay."""

import os
import re
import sys
import json
import time
from urllib.parse import quote
import requests

SEARCH_QUERIES = [
    {"query": "rain window", "category": "Nature", "count": 3},
    {"query": "ocean waves", "category": "Nature", "count": 3},
    {"query": "snow", "category": "Seasonal", "count": 2},
    {"query": "fireplace", "category": "Nature", "count": 2},
    {"query": "city night neon", "category": "City", "count": 3},
    {"query": "traffic", "category": "City", "count": 2},
    {"query": "aurora", "category": "Space", "count": 2},
    {"query": "galaxy", "category": "Space", "count": 2},
    {"query": "abstract", "category": "Abstract", "count": 2},
    {"query": "underwater", "category": "Nature", "count": 2},
    {"query": "waterfall", "category": "Nature", "count": 2},
    {"query": "clouds sky", "category": "Nature", "count": 2},
    {"query": "forest", "category": "Nature", "count": 2},
    {"query": "sunset", "category": "Nature", "count": 2},
]

PIXABAY_API_URL = "https://pixabay.com/api/videos/"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
VIDEOS_DIR = os.path.join(REPO_ROOT, "originals", "videos")
METADATA_FILE = os.path.join(VIDEOS_DIR, "_download_metadata.json")


def sanitize_name(tags: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", tags.lower()).split()
    return "_".join(words[:3])


def load_metadata() -> dict:
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as f:
            return json.load(f)
    return {}


def save_metadata(metadata: dict):
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def download_video(url: str, dest: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def main():
    api_key = os.environ.get("PIXABAY_API_KEY")
    if not api_key:
        print("Error: PIXABAY_API_KEY environment variable not set.")
        print("Set it with: export PIXABAY_API_KEY=your_key_here")
        sys.exit(1)

    os.makedirs(VIDEOS_DIR, exist_ok=True)
    metadata = load_metadata()

    total_expected = sum(q["count"] for q in SEARCH_QUERIES)
    downloaded = 0
    skipped = 0
    errors = 0
    current = 0

    for entry in SEARCH_QUERIES:
        query = entry["query"]
        category = entry["category"]
        count = entry["count"]

        print(f"\nSearching: \"{query}\" (category: {category}, count: {count})")

        url = f"{PIXABAY_API_URL}?key={api_key}&q={quote(query)}&per_page={max(count, 3)}&safesearch=true"

        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  API error ({resp.status_code}): {resp.text[:200]}")
                if resp.status_code == 400 and " " in query:
                    fallback = query.split()[0]
                    print(f"  Retrying with \"{fallback}\"...")
                    url = f"{PIXABAY_API_URL}?key={api_key}&q={quote(fallback)}&per_page={max(count, 3)}&safesearch=true"
                    resp = requests.get(url, timeout=30)
                    if resp.status_code != 200:
                        print(f"  Retry also failed ({resp.status_code}): {resp.text[:200]}")
                        errors += count
                        current += count
                        continue
                else:
                    errors += count
                    current += count
                    continue
            data = resp.json()
        except requests.RequestException as e:
            print(f"  API error for \"{query}\": {e}")
            errors += count
            current += count
            continue

        hits = data.get("hits", [])
        if not hits:
            print(f"  No results for \"{query}\"")
            current += count
            continue

        for video in hits[:count]:
            current += 1
            video_id = video["id"]
            tags = video.get("tags", f"video_{video_id}")
            name = sanitize_name(tags)

            if not name:
                name = f"video_{video_id}"

            existing_names = {v["name"] for v in metadata.values()}
            original_name = name
            suffix = 2
            while name in existing_names and str(video_id) not in metadata:
                name = f"{original_name}_{suffix}"
                suffix += 1

            filename = f"{name}.mp4"
            dest = os.path.join(VIDEOS_DIR, filename)

            if os.path.exists(dest):
                print(f"  Skipping {current}/{total_expected}: {filename} (exists)")
                skipped += 1
                continue

            medium = video.get("videos", {}).get("medium", {})
            video_url = medium.get("url")
            if not video_url:
                print(f"  No medium URL for {filename}, skipping")
                errors += 1
                continue

            print(f"  Downloading {current}/{total_expected}: {filename}...")
            try:
                download_video(video_url, dest)
                metadata[str(video_id)] = {
                    "name": name,
                    "filename": filename,
                    "query": query,
                    "category": category,
                    "tags": tags,
                    "pixabay_id": video_id,
                }
                save_metadata(metadata)
                downloaded += 1
            except Exception as e:
                print(f"  Error downloading {filename}: {e}")
                if os.path.exists(dest):
                    os.remove(dest)
                errors += 1

        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Download complete!")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped:    {skipped}")
    print(f"  Errors:     {errors}")
    print(f"  Total:      {current}")
    print(f"  Videos dir: {VIDEOS_DIR}")


if __name__ == "__main__":
    main()
