#!/usr/bin/env python3
"""Reorder wallpapers.json for visual variety and good first impressions.

Strategy:
- Premium items first within each category (most visually striking)
- Greedy placement ensures no more than 3 consecutive items from the same category
- Videos spread throughout, not front-loaded
"""

import json
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
CATALOG_PATH = os.path.join(REPO_ROOT, "docs", "wallpapers.json")

MAX_CONSECUTIVE = 3

CATEGORY_ORDER = [
    "Nature", "City", "Space", "Abstract", "Aesthetic",
    "Animals", "Floral", "Minimal", "Fantasy", "Cars",
    "Seasonal", "Pet"
]


def reorder():
    with open(CATALOG_PATH) as f:
        data = json.load(f)

    wallpapers = data.get("wallpapers", [])
    if not wallpapers:
        print("No wallpapers found.")
        return

    # Group by category, premium first within each group
    groups = defaultdict(list)
    for w in wallpapers:
        groups[w["category"]].append(w)
    for cat in groups:
        groups[cat].sort(key=lambda w: (0 if w.get("is_premium") else 1))

    # Build candidate pool: round-robin by category so items are pre-mixed
    ordered_cats = [c for c in CATEGORY_ORDER if c in groups]
    for c in groups:
        if c not in ordered_cats:
            ordered_cats.append(c)

    pool = []
    indices = {cat: 0 for cat in ordered_cats}
    total = sum(len(v) for v in groups.values())
    while len(pool) < total:
        active = [c for c in ordered_cats if indices[c] < len(groups[c])]
        if not active:
            break
        for cat in active:
            pool.append(groups[cat][indices[cat]])
            indices[cat] += 1

    # Greedy placement: pick items from pool maintaining max-consecutive constraint
    # Use a deque-like approach: try each candidate, skip if it would violate
    placed = []
    skipped = []

    for item in pool:
        if len(placed) >= MAX_CONSECUTIVE:
            tail_cats = [w["category"] for w in placed[-MAX_CONSECUTIVE:]]
            if all(c == item["category"] for c in tail_cats):
                skipped.append(item)
                continue
        # Before placing, check if any skipped items can go first
        inserted_from_skipped = True
        while inserted_from_skipped:
            inserted_from_skipped = False
            for si, sk_item in enumerate(skipped):
                if len(placed) >= MAX_CONSECUTIVE:
                    tail_cats = [w["category"] for w in placed[-MAX_CONSECUTIVE:]]
                    if all(c == sk_item["category"] for c in tail_cats):
                        continue
                placed.append(skipped.pop(si))
                inserted_from_skipped = True
                break
        # Now place current item
        if len(placed) >= MAX_CONSECUTIVE:
            tail_cats = [w["category"] for w in placed[-MAX_CONSECUTIVE:]]
            if all(c == item["category"] for c in tail_cats):
                skipped.append(item)
                continue
        placed.append(item)

    # Place remaining skipped items using greedy insertion
    for item in skipped:
        # Find best position to insert (where it won't create a long run)
        inserted = False
        for pos in range(len(placed), 0, -1):
            before = [w["category"] for w in placed[max(0, pos - MAX_CONSECUTIVE):pos]]
            after = [w["category"] for w in placed[pos:pos + MAX_CONSECUTIVE]]
            cat = item["category"]
            # Check: would inserting here create a run > MAX_CONSECUTIVE?
            run_before = sum(1 for c in reversed(before) if c == cat)
            run_after = sum(1 for c in after if c == cat)
            if run_before + 1 + run_after <= MAX_CONSECUTIVE:
                placed.insert(pos, item)
                inserted = True
                break
        if not inserted:
            placed.append(item)

    # Spread videos: ensure they're not clumped
    # Extract videos and images, then re-interleave
    videos = [w for w in placed if w["type"] == "video"]
    images = [w for w in placed if w["type"] == "image"]

    if videos and images:
        interval = max(1, len(images) // len(videos))
        final = []
        vid_idx = 0
        img_idx = 0

        while img_idx < len(images) or vid_idx < len(videos):
            if vid_idx < len(videos):
                final.append(videos[vid_idx])
                vid_idx += 1
            for _ in range(interval):
                if img_idx < len(images):
                    final.append(images[img_idx])
                    img_idx += 1
        while vid_idx < len(videos):
            final.append(videos[vid_idx])
            vid_idx += 1
        while img_idx < len(images):
            final.append(images[img_idx])
            img_idx += 1
    else:
        final = placed

    # Final pass: fix any runs created by video insertion
    for _ in range(20):
        fixed = False
        for i in range(MAX_CONSECUTIVE, len(final)):
            tail_cats = [final[j]["category"] for j in range(i - MAX_CONSECUTIVE, i + 1)]
            if len(set(tail_cats)) == 1:
                # Swap final[i] with the nearest different-category item ahead
                for j in range(i + 1, len(final)):
                    if final[j]["category"] != final[i]["category"]:
                        final[i], final[j] = final[j], final[i]
                        fixed = True
                        break
                else:
                    # Look behind (past the run)
                    for j in range(i - MAX_CONSECUTIVE - 1, -1, -1):
                        if final[j]["category"] != final[i]["category"]:
                            final[i], final[j] = final[j], final[i]
                            fixed = True
                            break
                if fixed:
                    break
        if not fixed:
            break

    # Assign sort_order
    for i, w in enumerate(final):
        w["sort_order"] = i + 1

    data["wallpapers"] = final
    with open(CATALOG_PATH, "w") as f:
        json.dump(data, f, indent=2)

    # Stats
    max_run = 1
    current_run = 1
    for i in range(1, len(final)):
        if final[i]["category"] == final[i - 1]["category"]:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1

    print(f"Reordered {len(final)} wallpapers.")
    print(f"  Max consecutive same-category: {max_run}")
    print(f"  Videos spread every ~{len(images) // max(len(videos), 1)} images")
    print(f"\nFirst 15 items:")
    for w in final[:15]:
        premium = " [P]" if w.get("is_premium") else ""
        print(f"  {w['sort_order']:3d} | {w['category']:10s} | {w['type']:5s} | {w['name']}{premium}")


if __name__ == "__main__":
    reorder()
