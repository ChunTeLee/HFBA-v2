"""
Rework metadata so search is driven ONLY by each asset's name (no image inspection).

For every record:
- tags        = cleaned, de-duplicated words from the display name
- synonyms    = []                       (query-side synonyms live in search.js)
- description = display_name             (name only)
- expression/pose/hands = "unknown"
- all attribute arrays (mood, theme, colors, headwear, outfit, ...) = []

Preserved: id, filename, folder, display_name, category, batch.
Run `python _build_index.py` afterwards to regenerate the index + search index.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
META = ROOT / "metadata.json"

STOP = {"huggy", "the", "a", "an", "of", "and", "to", "with", "for", "on", "in"}


def name_tags(name: str) -> list:
    toks = re.split(r"[^a-z0-9]+", name.lower())
    out = []
    for t in toks:
        if not t or t in STOP or t.isdigit() or len(t) < 2:
            continue
        if t not in out:
            out.append(t)
    return out


def main() -> None:
    meta = json.loads(META.read_text(encoding="utf-8"))
    for r in meta:
        r["tags"] = name_tags(r.get("display_name", ""))
        r["synonyms"] = []
        r["description"] = r.get("display_name", "")
        r["expression"] = "unknown"
        r["pose"] = "unknown"
        r["hands"] = "unknown"
        for k in ("headwear", "outfit", "face_accessories", "held_objects",
                  "effects", "colors", "mood", "theme"):
            r[k] = []
    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Reworked {len(meta)} records to name-only metadata.")
    print("Sample tags:")
    for r in meta[:12]:
        print(f"   {r['display_name']!r:40} -> {r['tags']}")


if __name__ == "__main__":
    main()
