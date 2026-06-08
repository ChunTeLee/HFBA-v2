"""
Generate downscaled JPEG thumbnails (max 1024px on longest side) for every PNG/GIF
in the three Huggy folders, into _thumbs/<folder>/<originalstem>.jpg.

Used so the metadata-inspector agent can read images without hitting the 2000px Read limit.
Filename mapping: thumbnail stem matches original file stem (extension changes to .jpg),
so the agent can map back trivially.
"""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
SRC = ROOT / "images"
DST = ROOT / "_thumbs"

FOLDERS = ["modern Huggies", "Outlined Huggies", "Huggy Collection 2026"]
MAX_DIM = 1024


def main() -> None:
    DST.mkdir(exist_ok=True)
    total = 0
    skipped = 0
    for folder in FOLDERS:
        src_dir = SRC / folder
        dst_dir = DST / folder
        dst_dir.mkdir(exist_ok=True)
        for src_path in sorted(src_dir.iterdir()):
            if not src_path.is_file():
                continue
            if src_path.suffix.lower() not in {".png", ".gif"}:
                continue
            if src_path.stem == "":  # the stray ".png" file in Outlined Huggies
                skipped += 1
                continue
            dst_path = dst_dir / (src_path.stem + ".jpg")
            try:
                with Image.open(src_path) as im:
                    if im.mode in ("RGBA", "LA", "P"):
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        if im.mode == "P":
                            im = im.convert("RGBA")
                        bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
                        im = bg
                    elif im.mode != "RGB":
                        im = im.convert("RGB")
                    im.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
                    im.save(dst_path, "JPEG", quality=82, optimize=True)
                total += 1
            except Exception as e:
                print(f"FAILED {src_path}: {e}")
                skipped += 1
    print(f"Wrote {total} thumbnails, skipped {skipped}, into {DST}")


if __name__ == "__main__":
    main()
