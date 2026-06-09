"""
Apply a rename plan from the in-browser name editor.

Entries whose new_name ends with '- remove' are DELETED (file + thumbnail + metadata).
All other entries are RENAMED on disk and in metadata (filename + display_name).

Safety:
- Deletions run first, so a name freed by a deletion can be reused by a rename
  (e.g. old 'Athlete Huggy' deleted, 'Athlete Frowning Huggy' -> 'Athlete Huggy').
- Renames use a two-phase temp pass so swaps/cycles can't collide
  (e.g. 'Growing model Huggy' -> 'Discovery Huggy' while
   'Growing model Huggy 3' -> 'Growing model Huggy').
- Aborts before touching disk if the plan has structural problems
  (missing source file, duplicate target within a folder, target collides with an
   untouched file).

Run `python _build_index.py` afterwards to regenerate index.html.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
THUMBS = ROOT / "_thumbs"
META = ROOT / "metadata.json"
PLAN = ROOT / "_rename_plan.json"

REMOVE_RE = re.compile(r"\s*-\s*remove\s*$", re.I)


def thumb_path(folder: str, filename: str) -> Path:
    return THUMBS / folder / (Path(filename).stem + ".jpg")


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))["renames"]
    removes = [p for p in plan if REMOVE_RE.search(p["new_name"])]
    renames = [p for p in plan if not REMOVE_RE.search(p["new_name"])]

    meta = json.loads(META.read_text(encoding="utf-8"))
    have = {(r["folder"], r["filename"]) for r in meta}

    # ---- validate ----
    errors = []
    for p in plan:
        if (p["folder"], p["old_filename"]) not in have:
            errors.append(f"source not found in metadata: {p['folder']}/{p['old_filename']}")
        if not (IMAGES / p["folder"] / p["old_filename"]).exists():
            errors.append(f"source file missing on disk: {p['folder']}/{p['old_filename']}")

    removed_keys = {(p["folder"], p["old_filename"]) for p in removes}
    renamed_sources = {(p["folder"], p["old_filename"]) for p in renames}

    # final filename per rename
    finals = {}
    per_folder_targets = {}
    for p in renames:
        folder = p["folder"]
        ext = p["ext"] or Path(p["old_filename"]).suffix
        new_fn = p["new_name"].strip() + ext
        finals[(folder, p["old_filename"])] = new_fn
        per_folder_targets.setdefault(folder, []).append(new_fn)

    # duplicate targets within a folder
    for folder, targets in per_folder_targets.items():
        seen = {}
        for t in targets:
            k = t.lower()
            seen[k] = seen.get(k, 0) + 1
        for k, n in seen.items():
            if n > 1:
                errors.append(f"duplicate rename target in '{folder}': {k} (x{n})")

    # target collides with an untouched file (not removed, not itself renamed away)
    for (folder, old), new_fn in finals.items():
        key = (folder, new_fn)
        if key in have and key not in removed_keys and key not in renamed_sources:
            errors.append(f"target '{folder}/{new_fn}' collides with an existing untouched file")

    if errors:
        print("ABORTED — plan has problems:")
        for e in errors:
            print("   !", e)
        return

    # ---- 1) deletions ----
    print(f"Deleting {len(removes)} assets:")
    for p in removes:
        folder, fn = p["folder"], p["old_filename"]
        print(f"   - {folder}/{fn}")
        (IMAGES / folder / fn).unlink(missing_ok=True)
        thumb_path(folder, fn).unlink(missing_ok=True)
    meta = [r for r in meta if (r["folder"], r["filename"]) not in removed_keys]

    # ---- 2) renames, two-phase ----
    idx = {(r["folder"], r["filename"]): r for r in meta}
    staged = []  # (folder, old, new_fn, new_name, tmp_img, tmp_thumb)
    for p in renames:
        folder, old = p["folder"], p["old_filename"]
        new_fn = finals[(folder, old)]
        src = IMAGES / folder / old
        tmp = IMAGES / folder / (old + ".__tmp")
        src.rename(tmp)
        th = thumb_path(folder, old)
        tmp_th = None
        if th.exists():
            tmp_th = th.with_suffix(".jpg.__tmp")
            th.rename(tmp_th)
        staged.append((folder, old, new_fn, p["new_name"].strip(), tmp, tmp_th))

    print(f"\nRenaming {len(staged)} assets:")
    for folder, old, new_fn, new_name, tmp, tmp_th in staged:
        (IMAGES / folder / new_fn)  # target path
        tmp.rename(IMAGES / folder / new_fn)
        if tmp_th is not None:
            tmp_th.rename(THUMBS / folder / (Path(new_fn).stem + ".jpg"))
        rec = idx.get((folder, old))
        if rec is not None:
            rec["filename"] = new_fn
            rec["display_name"] = new_name
        print(f"   {old}  ->  {new_fn}   (display: {new_name!r})")

    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- summary ----
    from collections import Counter
    print("\nMetadata records now:", len(meta))
    print("Per folder:", dict(Counter(r["folder"] for r in meta)))


if __name__ == "__main__":
    main()
