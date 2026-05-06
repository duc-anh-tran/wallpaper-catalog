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

## Pipeline Overview

All scripts are run from the `wallpaper-catalog/` directory.

### Bundled pipeline (content goes into APK)

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. python3 scripts/download_from_pixabay.py                         │
│  2. bash scripts/compress_videos.sh                                  │
│  3. bash scripts/generate_catalog.sh                                 │
│  4. bash scripts/sync_to_app.sh                                      │
│  5. git add docs/ && git commit -m "update" && git push              │
│  6. cd ../live-wallpaper && ./gradlew assembleDebug                  │
└──────────────────────────────────────────────────────────────────────┘
```

### Remote pipeline (content goes to Cloudflare R2)

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. python3 scripts/download_from_pixabay.py                         │
│  2. bash scripts/compress_videos.sh                                  │
│  3. bash scripts/generate_catalog.sh --remote                        │
│  4. bash scripts/upload_to_r2.sh                                     │
│  5. git add docs/wallpapers.json && git commit -m "update" && git push│
│  6. Clear app cache on device to see new wallpapers                  │
└──────────────────────────────────────────────────────────────────────┘
```

### Or use the all-in-one script

```bash
cd wallpaper-catalog
bash scripts/run_all.sh            # bundled pipeline (steps 1-5)
bash scripts/run_all.sh --remote   # remote pipeline (steps 1-5)
```

## Quick Start

### Bundled wallpapers (packaged in APK)

```bash
cd wallpaper-catalog
bash scripts/run_all.sh
cd ../live-wallpaper && ./gradlew assembleDebug
```

Increases APK size. Best for the core set of wallpapers you want available offline.

### Remote wallpapers (hosted on Cloudflare R2)

```bash
cd wallpaper-catalog
bash scripts/run_all.sh --remote
```

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
- Only adds NEW entries — existing entries (bundled or remote) are never overwritten

### 4. Upload to Cloudflare R2

```bash
bash scripts/upload_to_r2.sh
```

- Uploads compressed videos, images, and thumbnails to R2
- Uses rclone for S3-compatible transfer
- Syncs entire folders — safe to run multiple times

### 5. Push catalog to GitHub Pages

```bash
git add docs/wallpapers.json
git commit -m "Add remote wallpapers"
git push
```

No app rebuild needed — the app fetches the updated catalog from GitHub Pages.

### 6. See changes on device

The app caches the catalog for **24 hours**. After pushing, users (and you) won't see new wallpapers until:

- **Option A**: Wait 24 hours for the cache to expire naturally
- **Option B**: Force-close the app AND clear its cache (Settings → Apps → Live Wallpaper → Clear Cache)
- **Option C**: Uninstall and reinstall the app

This is by design — avoids hammering the server on every app open. For development/testing, use Option B.

## Important Gotchas

### Cache behavior
- The app caches `wallpapers.json` in SharedPreferences for 24 hours
- After adding new remote wallpapers and pushing, you must clear app cache to see them immediately
- The fallback JSON (`wallpapers_fallback.json`) in the APK is only updated when you run `sync_to_app.sh` and rebuild — it does NOT include remote-only entries unless you explicitly sync

### generate_catalog.sh only adds NEW entries
- It checks existing IDs in `wallpapers.json` and skips anything already there
- If you want to convert a bundled entry to remote, you must manually edit `wallpapers.json`
- If you want to re-generate an entry (e.g., change category), delete it from `wallpapers.json` first, then re-run

### Scripts load .env automatically
- All scripts (`run_all.sh`, `generate_catalog.sh`, `upload_to_r2.sh`) load `.env` from the repo root
- You can also run them from `run_all.sh` which loads `.env` once at the top
- The `.env` file must be in the `wallpaper-catalog/` root directory (not in `scripts/`)

### rclone endpoint vs public URL
- `R2_PUBLIC_URL` (in `.env`): the public read URL for browsers/app (e.g., `https://pub-xxxxxxxx.r2.dev`)
- rclone endpoint (in `rclone config`): the S3 API URL for uploads (e.g., `https://<account_id>.r2.cloudflarestorage.com`)
- These are DIFFERENT URLs — don't mix them up

### Thumbnail URLs for remote entries
- Remote entries get thumbnail URLs pointing to R2 (e.g., `https://pub-xxx.r2.dev/thumbs/file.jpg`)
- Bundled entries keep GitHub Pages thumbnail URLs (e.g., `https://duc-anh-tran.github.io/wallpaper-catalog/thumbs/file.jpg`)
- Both work fine — the app loads any HTTPS thumbnail URL via Coil

### APK size
- Bundled wallpapers are in `app/src/main/assets/` and increase APK size
- Remote wallpapers are NOT in the APK — zero size impact
- The `wallpapers_fallback.json` includes ALL entries (bundled + remote) but that's just a small JSON file

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
- Endpoint: `https://<account_id>.r2.cloudflarestorage.com` (NOT the pub-xxx.r2.dev URL!)
- Leave other options as default

To verify: `rclone config show r2`

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
- Convert bundled entries to remote (change `bundled:videos/x.mp4` to `https://r2-url/videos/x.mp4`)

After manual edits, push to GitHub Pages:
```bash
git add docs/wallpapers.json && git commit -m "Update catalog" && git push
```

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

1. App launches → fetches `wallpapers.json` from GitHub Pages
2. If fetch succeeds → caches in SharedPreferences (24-hour TTL)
3. If fetch fails (offline/error) → uses SharedPreferences cache, or bundled `wallpapers_fallback.json` as last resort
4. For each wallpaper displayed:
   - **Thumbnail**: loaded from URL (GitHub Pages or R2) via Coil image loader
   - **Bundled video** (`bundled:` prefix): copied from APK assets to cache, played locally
   - **Remote video** (HTTPS URL): downloaded to cache on demand, then played
   - **Bundled image** (`bundled:` prefix): loaded from APK assets
   - **Remote image** (HTTPS URL): downloaded to cache on demand
5. Downloaded remote content is cached in `app_cache/wallpapers/` (500MB LRU eviction)
6. Users can apply effects (rain, snow, fireflies, leaves, aurora) to any image wallpaper

## Adding a New Category

1. Add the category name to the `"categories"` array in `docs/wallpapers.json`
2. Use that category name in new wallpaper entries
3. Push to GitHub Pages
4. Clear app cache on device to see it immediately (or wait 24 hours)

## Removing Wallpapers

1. Delete the entry from `docs/wallpapers.json`
2. Optionally delete the source file from `originals/` and the thumb from `docs/thumbs/`
3. If bundled: also delete the asset from `live-wallpaper/app/src/main/assets/`
4. If remote: optionally delete from R2 (`rclone delete r2:bucket-name/path/file`)
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

Note: The download script skips based on **Pixabay ID in metadata**, not just file existence. This means:
- Increasing the count for an existing query will only download new results
- If you delete a file you don't want, it will NOT be re-downloaded (metadata remembers it)
- To force re-download a deleted file, remove its entry from `originals/images/_download_metadata.json` or `originals/videos/_download_metadata.json`

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| New wallpapers don't appear on device | 24-hour catalog cache | Clear app cache, reopen |
| `R2_PUBLIC_URL not set` error | Script can't find `.env` | Make sure `.env` is in `wallpaper-catalog/` root |
| rclone 401 Unauthorized | Wrong endpoint in rclone config | Use `https://<account_id>.r2.cloudflarestorage.com`, NOT the `pub-xxx.r2.dev` URL |
| Thumbnails not loading | GitHub Pages not deployed yet | Wait 1-2 min after push for Pages to rebuild |
| `generate_catalog.sh --remote` adds 0 entries | All files already have entries | Only NEW files get entries; delete old entries from JSON to regenerate |
| Video won't play (remote) | R2 bucket not public | Enable public access in Cloudflare R2 settings |
| App shows old catalog after push | SharedPreferences cache | Clear app storage or wait 24h |
| Deleted file keeps getting re-downloaded | Won't happen — metadata tracks by Pixabay ID | To force re-download, delete entry from `_download_metadata.json` |
