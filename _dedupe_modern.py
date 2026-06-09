"""
Remove repeated Huggies from the existing 'modern Huggies' folder — any file that
also appears in the new 'Huggy Collection 2026' batch (matched by byte-identical
content OR by normalized display name). The new 2026 versions (rendered on top) are
kept; the older duplicate copies are deleted from disk, their thumbnails removed,
and their metadata records pruned.

Files unique to the existing set are preserved.
Re-run `python _build_index.py` afterwards to regenerate index.html.
"""

import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
THUMBS = ROOT / "_thumbs"
META = ROOT / "metadata.json"

NEW_FOLDER = "Huggy Collection 2026"
OLD_FOLDER = "modern Huggies"


def norm(s: str) -> str:
    s = s.lower().rsplit(".", 1)[0]
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> None:
    meta = json.loads(META.read_text(encoding="utf-8"))
    disp = {(r["folder"], r["filename"]): r["display_name"] for r in meta}

    newdir = IMAGES / NEW_FOLDER
    olddir = IMAGES / OLD_FOLDER
    img_exts = {".png", ".gif"}

    new_files = [f.name for f in newdir.iterdir() if f.suffix.lower() in img_exts]
    old_files = sorted(f.name for f in olddir.iterdir() if f.suffix.lower() in img_exts)

    new_norms = {norm(disp.get((NEW_FOLDER, f), f)) for f in new_files}
    new_hashes = {md5(newdir / f) for f in new_files}

    to_remove = []
    for f in old_files:
        d = disp.get((OLD_FOLDER, f), f)
        if md5(olddir / f) in new_hashes or norm(d) in new_norms:
            to_remove.append(f)

    print(f"Removing {len(to_remove)} repeated files from '{OLD_FOLDER}':")
    for f in to_remove:
        print("   -", f)
        (olddir / f).unlink()
        thumb = THUMBS / OLD_FOLDER / (Path(f).stem + ".jpg")
        if thumb.exists():
            thumb.unlink()

    remove_set = {(OLD_FOLDER, f) for f in to_remove}
    before = len(meta)
    meta = [r for r in meta if (r["folder"], r["filename"]) not in remove_set]
    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    kept_old = sorted(f.name for f in olddir.iterdir() if f.suffix.lower() in img_exts)
    print(f"\nMetadata records: {before} -> {len(meta)}")
    print(f"Remaining in '{OLD_FOLDER}' ({len(kept_old)}):")
    for f in kept_old:
        print("   ", f)


if __name__ == "__main__":
    main()
