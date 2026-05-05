# Wallpaper Catalog — Content Workflow

How to add new wallpapers (videos or images) to the catalog and deploy them to the app.

## Prerequisites

- Python 3 installed
- ffmpeg installed (`brew install ffmpeg`)
- Pixabay API key in `wallpaper-catalog/.env`:
  ```
  PIXABAY_API_KEY=your_key_here
  ```
- For remote hosting (optional): rclone installed + Cloudflare R2 configured (see [R2 Setup](#cloudflare-r2-setup))

## Quick Start

### Bundled wallpapers (packaged in APK)

```bash
cd wallpaper-catalog
bash scripts/run_all.sh
cd ../live-wallpaper && ./gradlew assembleDebug
```

Downloads → compresses → generates catalog → syncs to app assets → optional git push.
Increases APK size. Best for the core set of wallpapers you want available offline.

### Remote wallpapers (hosted on Cloudflare R2)

```bash
cd wallpaper-catalog
bash scripts/run_all.sh --remote
```

Downloads → compresses → generates catalog → uploads to R2 → optional git push.
No APK size increase. App downloads content on demand. Requires R2 setup.

## Step-by-Step (Bundled)

### 1. Download content from Pixabay

```bash
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
- Adds new entries to `docs/wallpapers.json` with `bundled:` prefix
- Does NOT remove existing entries — only adds new ones

### 4. Sync to Android app

```bash
bash scripts/sync_to_app.sh
```

- Copies compressed videos to `live-wallpaper/app/src/main/assets/videos/`
- Copies images to `live-wallpaper/app/src/main/assets/images/`
- Copies `wallpapers.json` → `wallpapers_fallback.json` (offline fallback)
- Only copies files with `bundled:` prefix — remote entries are skipped

### 5. Push catalog to GitHub Pages

```bash
git add docs/
git commit -m "Update catalog"
git push
```

The app fetches `wallpapers.json` from: https://duc-anh-tran.github.io/wallpaper-catalog/wallpapers.json

### 6. Build the app

```bash
cd ../live-wallpaper
./gradlew assembleDebug
```

## Step-by-Step (Remote / Cloudflare R2)

### 1. Download content from Pixabay

Same as bundled — edit search queries, run:
```bash
python3 scripts/download_from_pixabay.py
```

### 2. Compress videos

```bash
bash scripts/compress_videos.sh
```

### 3. Generate catalog (remote mode)

```bash
bash scripts/generate_catalog.sh --remote
```

- Creates thumbnails locally (same as bundled)
- Adds new entries to `docs/wallpapers.json` with R2 URLs instead of `bundled:` prefix
- Example: `"video_source": "https://pub-xxx.r2.dev/videos/file.mp4"`

### 4. Upload to Cloudflare R2

```bash
bash scripts/upload_to_r2.sh
```

- Uploads compressed videos, images, and thumbnails to R2
- Uses rclone for S3-compatible transfer

### 5. Push catalog to GitHub Pages

```bash
git add docs/wallpapers.json
git commit -m "Add remote wallpapers"
git push
```

No app rebuild needed — the app fetches the updated catalog automatically (within 24 hours or on fresh launch).

## Cloudflare R2 Setup

One-time setup for remote wallpaper hosting:

### 1. Create R2 bucket

1. Go to Cloudflare dashboard → R2
2. Create a bucket (e.g., `wallpaper-assets`)
3. Enable public access (Settings → Public Access → Allow Access)
4. Note the public URL (e.g., `https://pub-xxxxxxxx.r2.dev`)

### 2. Create API token

1. Cloudflare dashboard → R2 → Manage R2 API Tokens
2. Create token with read/write permissions to your bucket
3. Note the Access Key ID and Secret Access Key

### 3. Install and configure rclone

```bash
brew install rclone
rclone config
```

When prompted:
- Name: `r2`
- Storage type: `s3`
- Provider: `Cloudflare`
- Access Key ID: (from step 2)
- Secret Access Key: (from step 2)
- Endpoint: `https://<account_id>.r2.cloudflarestorage.com`
- Leave other options as default

### 4. Update .env

Add to `wallpaper-catalog/.env`:
```
R2_BUCKET_NAME=wallpaper-assets
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_PUBLIC_URL=https://pub-xxxxxxxx.r2.dev
RCLONE_REMOTE=r2
```

### 5. Test

```bash
bash scripts/upload_to_r2.sh
curl -I https://pub-xxxxxxxx.r2.dev/thumbs/some_image.jpg  # should return 200
```

## Editing the Catalog Manually

The catalog lives at `docs/wallpapers.json`. You can edit it directly to:

- Change wallpaper names, categories, sort order
- Mark wallpapers as premium (`"is_premium": true`)
- Remove entries you don't want
- Reorder categories in the `"categories"` array

### Entry format — Bundled video

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

### Entry format — Bundled image

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

### Entry format — Remote video (R2)

```json
{
  "id": "city_rain",
  "name": "City Rain",
  "category": "City",
  "type": "video",
  "video_source": "https://pub-xxx.r2.dev/videos/city_rain.mp4",
  "thumbnail_url": "https://pub-xxx.r2.dev/thumbs/city_rain.jpg",
  "is_premium": false,
  "sort_order": 70
}
```

### Entry format — Remote image (R2)

```json
{
  "id": "galaxy_nebula",
  "name": "Galaxy Nebula",
  "category": "Space",
  "type": "image",
  "image_source": "https://pub-xxx.r2.dev/images/galaxy_nebula.jpg",
  "thumbnail_url": "https://pub-xxx.r2.dev/thumbs/galaxy_nebula.jpg",
  "is_premium": false,
  "sort_order": 71
}
```

## How It Works in the App

1. App fetches `wallpapers.json` from GitHub Pages (cached 24 hours)
2. Falls back to bundled `wallpapers_fallback.json` if offline
3. For bundled content (`bundled:` prefix), assets are loaded from APK instantly
4. For remote content (HTTPS URLs), app downloads on demand and caches locally
5. Thumbnails load from their URL (GitHub Pages or R2)
6. Users can apply effects (rain, snow, fireflies, leaves, aurora) to any image wallpaper

## Adding a New Category

1. Add the category name to the `"categories"` array in `docs/wallpapers.json`
2. Use that category name in new wallpaper entries
3. Push to GitHub Pages

## Removing Wallpapers

1. Delete the entry from `docs/wallpapers.json`
2. Optionally delete the source file from `originals/` and the thumb from `docs/thumbs/`
3. If bundled: delete the asset from `live-wallpaper/app/src/main/assets/`
4. If remote: optionally delete from R2 (`rclone delete r2:bucket/path/file`)
5. Push and rebuild (if bundled) or just push (if remote)

## Adding More Content to Existing Categories

Edit `scripts/download_from_pixabay.py`:

```python
VIDEO_SEARCH_QUERIES = [
    ("rain window", "Nature", 3),      # (query, category, count)
    ("ocean waves", "Nature", 3),
    ("your new query", "Category", 2),  # ← add here
]

IMAGE_SEARCH_QUERIES = [
    ("mountain landscape", "Nature", 3),
    ("your new query", "Category", 2),  # ← add here
]
```

Then run the appropriate pipeline (bundled or remote).
