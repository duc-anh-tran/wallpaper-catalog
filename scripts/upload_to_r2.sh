#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$REPO_ROOT/.env" ]; then
    export $(cat "$REPO_ROOT/.env" | grep -v '^#' | xargs)
fi

HQ_DIR="$REPO_ROOT/originals/videos_compressed_hq"
STD_DIR="$REPO_ROOT/originals/videos_compressed"
if [ -d "$HQ_DIR" ] && [ "$(ls -A "$HQ_DIR" 2>/dev/null)" ]; then
    VIDEOS_DIR="$HQ_DIR"
    echo "  Using HQ videos (1080p)"
else
    VIDEOS_DIR="$STD_DIR"
    echo "  Using standard videos (720p)"
fi
IMAGES_DIR="$REPO_ROOT/originals/images"
THUMBS_DIR="$REPO_ROOT/docs/thumbs"

RCLONE_REMOTE="${RCLONE_REMOTE:-r2}"
R2_BUCKET_NAME="${R2_BUCKET_NAME:-}"
R2_PUBLIC_URL="${R2_PUBLIC_URL:-}"

if [ -z "$R2_BUCKET_NAME" ]; then
    echo "Error: R2_BUCKET_NAME not set. Add it to .env or export it."
    exit 1
fi

if [ -z "$R2_PUBLIC_URL" ]; then
    echo "Error: R2_PUBLIC_URL not set. Add it to .env or export it."
    exit 1
fi

if ! command -v rclone &>/dev/null; then
    echo "Error: rclone is not installed."
    echo "Install with: brew install rclone"
    echo "Then configure: rclone config (create remote named 'r2' with S3/Cloudflare R2)"
    exit 1
fi

DEST="$RCLONE_REMOTE:$R2_BUCKET_NAME"

echo "=== Uploading to Cloudflare R2 ==="
echo "  Bucket: $R2_BUCKET_NAME"
echo "  Public URL: $R2_PUBLIC_URL"
echo ""

echo "--- Videos ---"
if [ -d "$VIDEOS_DIR" ] && [ "$(ls -A "$VIDEOS_DIR" 2>/dev/null)" ]; then
    rclone sync "$VIDEOS_DIR" "$DEST/videos/" \
        --progress \
        --no-update-modtime \
        --s3-no-check-bucket
    echo "  Videos synced."
else
    echo "  No videos to upload."
fi

echo ""
echo "--- Images ---"
if [ -d "$IMAGES_DIR" ] && [ "$(ls -A "$IMAGES_DIR" 2>/dev/null)" ]; then
    rclone sync "$IMAGES_DIR" "$DEST/images/" \
        --progress \
        --no-update-modtime \
        --s3-no-check-bucket \
        --exclude="_*"
    echo "  Images synced."
else
    echo "  No images to upload."
fi

echo ""
echo "--- Thumbnails ---"
if [ -d "$THUMBS_DIR" ] && [ "$(ls -A "$THUMBS_DIR" 2>/dev/null)" ]; then
    rclone sync "$THUMBS_DIR" "$DEST/thumbs/" \
        --progress \
        --no-update-modtime \
        --s3-no-check-bucket
    echo "  Thumbnails synced."
else
    echo "  No thumbnails to upload."
fi

echo ""
echo "=== Upload complete ==="
echo "  Videos URL:  $R2_PUBLIC_URL/videos/"
echo "  Images URL:  $R2_PUBLIC_URL/images/"
echo "  Thumbs URL:  $R2_PUBLIC_URL/thumbs/"
