"""
Rename every file in `images/Huggy Collection 2026/` to match its display_name
from metadata.json. Also rename the corresponding thumbnail in `_thumbs/Huggy Collection 2026/`.
Then rewrite metadata.json with the new filenames.

Idempotent: if filename already matches `<display_name>.<ext>`, no action taken.
Collisions are resolved by appending ` 2`, ` 3` etc to the new stem.
After running, execute `python _build_index.py` to regenerate index.html.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "images" / "Huggy Collection 2026"
THUMBS_DIR = ROOT / "_thumbs" / "Huggy Collection 2026"
METADATA = ROOT / "metadata.json"

# Characters that are invalid in Windows filenames
INVALID_CHARS = '<>:"/\\|?*'


def safe_stem(name: str) -> str:
    """Sanitize a display name for use as a filename stem."""
    out = "".join("_" if c in INVALID_CHARS else c for c in name).strip()
    # Collapse internal whitespace, strip leading/trailing dots/spaces
    out = " ".join(out.split())
    out = out.rstrip(". ")
    return out or "Untitled"


def main() -> None:
    records = json.loads(METADATA.read_text(encoding="utf-8"))

    # Build target rename plan (filter to Collection 2026 only)
    plan = []
    used_stems: dict[str, int] = {}  # stem (lowercase) → count assigned

    for rec in records:
        if rec.get("folder") != "Huggy Collection 2026":
            continue
        old_name = rec["filename"]
        old_path = IMAGES_DIR / old_name
        ext = old_path.suffix  # includes the dot
        display = rec["display_name"]
        target_stem = safe_stem(display)

        # Collision handling: case-insensitive on Windows
        key = target_stem.lower()
        used_stems[key] = used_stems.get(key, 0) + 1
        if used_stems[key] > 1:
            target_stem = f"{target_stem} {used_stems[key]}"

        new_name = target_stem + ext
        plan.append((rec, old_name, new_name))

    # Phase 1: rename via temp suffix to avoid name swaps clashing
    print(f"Renaming {len(plan)} files in {IMAGES_DIR.name}...")
    temp_renames = []  # (rec, temp_path, final_name)
    no_op = 0
    for rec, old_name, new_name in plan:
        if old_name == new_name:
            no_op += 1
            continue
        old_path = IMAGES_DIR / old_name
        old_thumb = THUMBS_DIR / (old_path.stem + ".jpg")
        # Two-phase via .__rename_tmp suffix to dodge case-only renames + cycles
        tmp_path = IMAGES_DIR / (old_name + ".__rename_tmp")
        old_path.rename(tmp_path)
        tmp_thumb = None
        if old_thumb.exists():
            tmp_thumb = THUMBS_DIR / (old_thumb.name + ".__rename_tmp")
            old_thumb.rename(tmp_thumb)
        temp_renames.append((rec, tmp_path, tmp_thumb, new_name))

    # Phase 2: from .__rename_tmp to final names
    for rec, tmp_path, tmp_thumb, new_name in temp_renames:
        final_path = IMAGES_DIR / new_name
        if final_path.exists():
            raise RuntimeError(f"Collision unresolved: {final_path} already exists")
        tmp_path.rename(final_path)
        if tmp_thumb is not None:
            new_stem = Path(new_name).stem
            final_thumb = THUMBS_DIR / (new_stem + ".jpg")
            tmp_thumb.rename(final_thumb)
        rec["filename"] = new_name
        # Refresh id slug from new display_name (already done by agent, but recompute)
        # Leave id alone — it's based on display_name, unaffected by filename change.

    # Save updated metadata
    METADATA.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Renamed: {len(temp_renames)}, already correct: {no_op}, total Collection 2026 records: {len(plan)}")
    print(f"Updated {METADATA}")


if __name__ == "__main__":
    main()
