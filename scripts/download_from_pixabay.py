#!/usr/bin/env python3
"""Download wallpaper videos and images from Pixabay."""

import os
import re
import sys
import json
import time
from urllib.parse import quote
import requests

VIDEO_SEARCH_QUERIES = [
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

IMAGE_SEARCH_QUERIES = [
    {"query": "mountain landscape", "category": "Nature", "count": 10},
    {"query": "night city", "category": "City", "count": 10},
    {"query": "aurora borealis", "category": "Space", "count": 10},
    {"query": "galaxy stars", "category": "Space", "count": 10},
    {"query": "abstract colorful", "category": "Abstract", "count": 10},
    {"query": "ocean beach", "category": "Nature", "count": 10},
    {"query": "forest rain", "category": "Nature", "count": 10},
    {"query": "cherry blossom", "category": "Seasonal", "count": 2},
    {"query": "snow winter", "category": "Seasonal", "count": 10},
    {"query": "nebula space", "category": "Space", "count": 10},
    {"query": "sunset clouds", "category": "Nature", "count": 5},
    {"query": "summer", "category": "Nature", "count": 10},
    {"query": "neon lights", "category": "City", "count": 10},
    {"query": "pet", "category": "Pet", "count": 10},
    {"query": "sunset", "category": "Nature", "count": 10},
]

PIXABAY_VIDEOS_URL = "https://pixabay.com/api/videos/"
PIXABAY_IMAGES_URL = "https://pixabay.com/api/"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
VIDEOS_DIR = os.path.join(REPO_ROOT, "originals", "videos")
IMAGES_DIR = os.path.join(REPO_ROOT, "originals", "images")
VIDEO_METADATA_FILE = os.path.join(VIDEOS_DIR, "_download_metadata.json")
IMAGE_METADATA_FILE = os.path.join(IMAGES_DIR, "_download_metadata.json")


def sanitize_name(tags: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", tags.lower()).split()
    return "_".join(words[:3])


def load_metadata(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_metadata(metadata: dict, path: str):
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)


def download_file(url: str, dest: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def fetch_api(api_url: str, api_key: str, query: str, count: int, editors_choice: bool = True):
    ec_param = "&editors_choice=true" if editors_choice else ""
    url = f"{api_url}?key={api_key}&q={quote(query)}&per_page={max(count, 3)}&safesearch=true{ec_param}"
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        print(f"  API error ({resp.status_code}): {resp.text[:200]}")
        if resp.status_code == 400 and " " in query:
            fallback = query.split()[0]
            print(f"  Retrying with \"{fallback}\"...")
            url = f"{api_url}?key={api_key}&q={quote(fallback)}&per_page={max(count, 3)}&safesearch=true{ec_param}"
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  Retry failed ({resp.status_code}): {resp.text[:200]}")
                return None
        else:
            return None

    data = resp.json()
    if editors_choice and not data.get("hits"):
        print(f"  No editor's choice results, retrying without filter...")
        url = f"{api_url}?key={api_key}&q={quote(query)}&per_page={max(count, 3)}&safesearch=true"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return None

    return data


def download_videos(api_key: str):
    print("\n" + "=" * 50)
    print("  DOWNLOADING VIDEOS")
    print("=" * 50)

    os.makedirs(VIDEOS_DIR, exist_ok=True)
    metadata = load_metadata(VIDEO_METADATA_FILE)

    total_expected = sum(q["count"] for q in VIDEO_SEARCH_QUERIES)
    downloaded = 0
    skipped = 0
    errors = 0
    current = 0

    for entry in VIDEO_SEARCH_QUERIES:
        query = entry["query"]
        category = entry["category"]
        count = entry["count"]

        print(f"\nSearching videos: \"{query}\" (category: {category}, count: {count})")

        data = fetch_api(PIXABAY_VIDEOS_URL, api_key, query, count)
        if data is None:
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

            if str(video_id) in metadata:
                print(f"  Skipping {current}/{total_expected}: {metadata[str(video_id)]['filename']} (already processed)")
                skipped += 1
                continue

            tags = video.get("tags", f"video_{video_id}")
            name = sanitize_name(tags)

            if not name:
                name = f"video_{video_id}"

            existing_names = {v["name"] for v in metadata.values()}
            original_name = name
            suffix = 2
            while name in existing_names:
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
                download_file(video_url, dest)
                metadata[str(video_id)] = {
                    "name": name,
                    "filename": filename,
                    "query": query,
                    "category": category,
                    "tags": tags,
                    "pixabay_id": video_id,
                }
                save_metadata(metadata, VIDEO_METADATA_FILE)
                downloaded += 1
            except Exception as e:
                print(f"  Error downloading {filename}: {e}")
                if os.path.exists(dest):
                    os.remove(dest)
                errors += 1

        time.sleep(0.5)

    print(f"\n  Videos — Downloaded: {downloaded}, Skipped: {skipped}, Errors: {errors}")


def download_images(api_key: str):
    print("\n" + "=" * 50)
    print("  DOWNLOADING IMAGES")
    print("=" * 50)

    os.makedirs(IMAGES_DIR, exist_ok=True)
    metadata = load_metadata(IMAGE_METADATA_FILE)

    total_expected = sum(q["count"] for q in IMAGE_SEARCH_QUERIES)
    downloaded = 0
    skipped = 0
    errors = 0
    current = 0

    for entry in IMAGE_SEARCH_QUERIES:
        query = entry["query"]
        category = entry["category"]
        count = entry["count"]

        print(f"\nSearching images: \"{query}\" (category: {category}, count: {count})")

        params = f"&image_type=photo&orientation=vertical&min_height=1920&editors_choice=true"
        url = f"{PIXABAY_IMAGES_URL}?key={api_key}&q={quote(query)}&per_page={max(count, 3)}&safesearch=true{params}"

        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  API error ({resp.status_code}): {resp.text[:200]}")
                if resp.status_code == 400 and " " in query:
                    fallback = query.split()[0]
                    print(f"  Retrying with \"{fallback}\"...")
                    url = f"{PIXABAY_IMAGES_URL}?key={api_key}&q={quote(fallback)}&per_page={max(count, 3)}&safesearch=true{params}"
                    resp = requests.get(url, timeout=30)
                    if resp.status_code != 200:
                        print(f"  Retry failed ({resp.status_code}): {resp.text[:200]}")
                        errors += count
                        current += count
                        continue
                else:
                    errors += count
                    current += count
                    continue
            data = resp.json()

            if not data.get("hits"):
                print(f"  No editor's choice results, retrying without filter...")
                params_no_ec = f"&image_type=photo&orientation=vertical&min_height=1920"
                url = f"{PIXABAY_IMAGES_URL}?key={api_key}&q={quote(query)}&per_page={max(count, 3)}&safesearch=true{params_no_ec}"
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                else:
                    errors += count
                    current += count
                    continue

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

        for image in hits[:count]:
            current += 1
            image_id = image["id"]

            if str(image_id) in metadata:
                print(f"  Skipping {current}/{total_expected}: {metadata[str(image_id)]['filename']} (already processed)")
                skipped += 1
                continue

            tags = image.get("tags", f"image_{image_id}")
            name = sanitize_name(tags)

            if not name:
                name = f"image_{image_id}"

            existing_names = {v["name"] for v in metadata.values()}
            original_name = name
            suffix = 2
            while name in existing_names:
                name = f"{original_name}_{suffix}"
                suffix += 1

            filename = f"{name}.jpg"
            dest = os.path.join(IMAGES_DIR, filename)

            if os.path.exists(dest):
                print(f"  Skipping {current}/{total_expected}: {filename} (exists)")
                skipped += 1
                continue

            image_url = image.get("largeImageURL")
            if not image_url:
                print(f"  No largeImageURL for {filename}, skipping")
                errors += 1
                continue

            print(f"  Downloading {current}/{total_expected}: {filename}...")
            try:
                download_file(image_url, dest)
                metadata[str(image_id)] = {
                    "name": name,
                    "filename": filename,
                    "query": query,
                    "category": category,
                    "tags": tags,
                    "pixabay_id": image_id,
                }
                save_metadata(metadata, IMAGE_METADATA_FILE)
                downloaded += 1
            except Exception as e:
                print(f"  Error downloading {filename}: {e}")
                if os.path.exists(dest):
                    os.remove(dest)
                errors += 1

        time.sleep(0.5)

    print(f"\n  Images — Downloaded: {downloaded}, Skipped: {skipped}, Errors: {errors}")


def main():
    api_key = os.environ.get("PIXABAY_API_KEY")
    if not api_key:
        print("Error: PIXABAY_API_KEY environment variable not set.")
        print("Set it with: export PIXABAY_API_KEY=your_key_here")
        sys.exit(1)

    download_videos(api_key)
    download_images(api_key)

    print(f"\n{'='*50}")
    print("All downloads complete!")
    print(f"  Videos dir: {VIDEOS_DIR}")
    print(f"  Images dir: {IMAGES_DIR}")


if __name__ == "__main__":
    main()
