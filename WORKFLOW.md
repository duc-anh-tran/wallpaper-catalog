# Wallpaper Catalog — Content Workflow

How to add new wallpapers (videos or images) to the catalog and deploy them to the app.

## Prerequisites

- Python 3 installed
- ffmpeg installed (`brew install ffmpeg`)
- Pixabay API key in `wallpaper-catalog/.env`:
  ```
  PIXABAY_API_KEY=your_key_here
  ```

## Quick Start (All-in-One)

```bash
cd wallpaper-catalog
bash scripts/run_all.sh
```

This runs download → compress → generate catalog → sync to app → optional git push.

## Step-by-Step

### 1. Download content from Pixabay

```bash
cd wallpaper-catalog
python3 scripts/download_from_pixabay.py
```

- Edit `VIDEO_SEARCH_QUERIES` and `IMAGE_SEARCH_QUERIES` at the top of the script to change what gets downloaded
- Videos go to `originals/videos/`
- Images go to `originals/images/`
- Metadata saved to `_download_metadata.json` in each folder

### 2. Compress videos

```bash
bash scripts/compress_videos.sh
```

- Compresses videos to 720x1280, 15s max, CRF 28, no audio
- Output goes to `originals/videos_compressed/`
- Skips already-compressed files

### 3. Generate catalog

```bash
bash scripts/generate_catalog.sh
```

- Creates thumbnails in `docs/thumbs/` (video frame extracts + scaled images)
- Adds new entries to `docs/wallpapers.json`
- Does NOT remove existing entries — only adds new ones

### 4. Sync to Android app

```bash
bash scripts/sync_to_app.sh
```

- Copies compressed videos to `live-wallpaper/app/src/main/assets/videos/`
- Copies images to `live-wallpaper/app/src/main/assets/images/`
- Copies `wallpapers.json` → `wallpapers_fallback.json` (offline fallback)

### 5. Push catalog to GitHub Pages

```bash
cd wallpaper-catalog
git add docs/
git commit -m "Update catalog"
git push
```

The app fetches `wallpapers.json` from: https://duc-anh-tran.github.io/wallpaper-catalog/wallpapers.json

### 6. Build the app

```bash
cd live-wallpaper
./gradlew assembleDebug
```

## Editing the Catalog Manually

The catalog lives at `docs/wallpapers.json`. You can edit it directly to:

- Change wallpaper names, categories, sort order
- Mark wallpapers as premium (`"is_premium": true`)
- Remove entries you don't want
- Reorder categories in the `"categories"` array

### Entry format — Video

```json
{
  "id": "mountain_stream",
  "name": "Mountain Stream",
  "category": "Nature",
  "type": "video",
  "video_source": "bundled:videos/mountain_stream.mp4",
  "thumbnail_url": "https://duc-anh-tran.github.io/wallpaper-catalog/thumbs/mountain_stream.jpg",
  "is_premium": false,
  "sort_order": 1
}
```

### Entry format — Image

```json
{
  "id": "autumn_forest",
  "name": "Autumn Forest",
  "category": "Nature",
  "type": "image",
  "image_source": "bundled:images/autumn_forest.jpg",
  "thumbnail_url": "https://duc-anh-tran.github.io/wallpaper-catalog/thumbs/autumn_forest.jpg",
  "is_premium": false,
  "sort_order": 34
}
```

## How It Works in the App

1. App fetches `wallpapers.json` from GitHub Pages (cached 24 hours)
2. Falls back to bundled `wallpapers_fallback.json` if offline
3. For bundled content (`bundled:videos/...` or `bundled:images/...`), assets are loaded from APK
4. Thumbnails are extracted locally from bundled assets on first load
5. Users can apply effects (rain, snow, fireflies, leaves, aurora) to any image wallpaper

## Adding a New Category

1. Add the category name to the `"categories"` array in `docs/wallpapers.json`
2. Use that category name in new wallpaper entries
3. Push to GitHub Pages

## Removing Wallpapers

1. Delete the entry from `docs/wallpapers.json`
2. Optionally delete the source file from `originals/` and the thumb from `docs/thumbs/`
3. Delete the asset from `live-wallpaper/app/src/main/assets/` if bundled
4. Push and rebuild
