"""
Generates v2-space/index.html from the contents of images/.
Re-runnable: deletes existing index.html and rebuilds.
"""

from pathlib import Path
import html
import json

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
METADATA_PATH = ROOT / "metadata.json"


def _load_metadata() -> tuple[dict, dict]:
    """Load metadata.json once at import; return (display_map, tags_map)
    keyed by (folder, filename)."""
    display_map: dict[tuple[str, str], str] = {}
    tags_map: dict[tuple[str, str], str] = {}
    if not METADATA_PATH.exists():
        return display_map, tags_map
    try:
        records = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return display_map, tags_map
    for rec in records:
        folder = rec.get("folder")
        filename = rec.get("filename")
        if not folder or not filename:
            continue
        key = (folder, filename)
        display = rec.get("display_name")
        if display:
            display_map[key] = display
        tags = rec.get("tags") or []
        if tags:
            tags_map[key] = " ".join(str(t).lower() for t in tags)
    return display_map, tags_map


_DISPLAY_MAP, _TAGS_MAP = _load_metadata()


def display_title(filename: str, folder: str = "") -> str:
    name = _DISPLAY_MAP.get((folder, filename))
    if name:
        return name
    base = filename.rsplit(".", 1)[0]
    return base.replace("-", " ")


def list_images(folder: Path) -> list[str]:
    files = [p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".gif"}]
    return sorted(files, key=str.lower)


def list_logo_basenames(folder: Path) -> list[tuple[str, list[str]]]:
    """Group brand logo files by basename, returning (display_title, [extensions...])."""
    groups: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    for p in sorted(folder.iterdir()):
        if not p.is_file():
            continue
        ext = p.suffix.lower().lstrip(".")
        if ext not in {"png", "svg", "ai"}:
            continue
        stem = p.stem
        groups.setdefault(stem, []).append(ext)
        titles.setdefault(stem, stem)
    # Manual title overrides for nicer display
    nice = {
        "Hugging Face": "HF Logo",
        "hf-logo": "HF Logo",
        "hf-logo-with-title": "HF logo + title",
        "hf-logo-with-text": "HF logo + text",
        "hf-logo-with-white-title": "HF logo + white title",
        "Rainbow Hugging Face": "Rainbow Hugging Face",
    }
    return [(stem, nice.get(stem, stem), exts) for stem, exts in sorted(groups.items())]


def card_logo(stem: str, title: str, exts: list[str], dark: bool = False) -> str:
    bg = "bg-black" if dark else "bg-white"
    primary_ext = "png" if "png" in exts else exts[0]
    img = f"images/Brand Logos/{stem}.{primary_ext}"
    buttons = []
    order = [e for e in ("png", "svg", "ai") if e in exts]
    for i, ext in enumerate(order):
        if i > 0:
            buttons.append(
                '                <hr class="mx-3 h-3 rounded-sm border-r border-IconBorder xl:mx-2.5">'
            )
        buttons.append(
            f"""                <button x-data="{{ filename: '{stem}.{ext}', imageUrl: 'images/Brand Logos/{stem}.{ext}' }}" x-on:click="downloadImage(imageUrl, filename)" class="flex items-center space-x-1 download-button">
                  <img src="images/download icon.svg" class="w-4 h-4" alt="">
                  <p class="text-gray-500 font-mono">.{ext}</p>
                </button>"""
        )
    buttons_html = "\n".join(buttons)
    return f"""          <div class="w-full flex flex-col">
            <img src="{html.escape(img)}" alt="{html.escape(title)}" class="w-full h-full {bg} shadow-DropShadow md:p-14 p-7 rounded-3xl object-contain">
            <div class="pl-3 pt-3">
              <h5 class="text-lg font-sans text-BluishDark">{html.escape(title)}</h5>
              <div class="flex flex-wrap gap-y-1 items-center mt-2 text-sm">
{buttons_html}
              </div>
            </div>
          </div>"""


def card_huggy(folder: str, filename: str, span: str = "") -> str:
    title = display_title(filename, folder)
    ext = filename.rsplit(".", 1)[1].lower()
    img_path = f"images/{folder}/{filename}"
    span_class = f" {span}" if span else ""
    pad_class = "md:p-7 p-3"
    key = (folder, filename)
    data_attrs = ""
    if key in _DISPLAY_MAP and key in _TAGS_MAP:
        data_attrs = (
            f' data-display-name="{html.escape(_DISPLAY_MAP[key])}"'
            f' data-tags="{html.escape(_TAGS_MAP[key])}"'
        )
    return f"""          <div class="w-full flex flex-col{span_class}"{data_attrs}>
            <img src="{html.escape(img_path)}" alt="{html.escape(title)}" class="w-full h-full bg-white shadow-DropShadow {pad_class} rounded-3xl object-contain">
            <div class="px-3 pt-3 flex flex-col gap-1 md:flex-row md:justify-between md:items-center">
              <h5 class="text-lg font-sans text-BluishDark">{html.escape(title)}</h5>
              <button x-data="{{ filename: '{html.escape(filename)}', imageUrl: '{html.escape(img_path)}' }}" x-on:click="downloadImage(imageUrl, filename)" class="flex items-center space-x-1 download-button">
                <img src="images/download icon.svg" class="w-4 h-4 hidden md:inline-block" alt="">
                <p class="text-gray-500 font-mono hidden md:inline-block">.{ext}</p>
              </button>
            </div>
          </div>"""


def section_header(title: str, link_html: str = "") -> str:
    right = f"""<div class="text-BluishDark transform hover:text-gray-900">{link_html}</div>""" if link_html else ""
    return f"""        <div class="flex flex-row items-center justify-between mb-5">
          <div class="font-mono max-w-fit text-3xl bg-blue-500 text-white py-3 px-6 rounded-full">{html.escape(title)}</div>
          {right}
        </div>"""


def main() -> None:
    # ---- HF Logos ----
    logo_groups = list_logo_basenames(IMAGES / "Brand Logos")
    # Hide variants we don't want as primary cards (text-only)
    primary_logos = [
        ("Hugging Face", "HF Logo", ["png"]),
        ("Rainbow Hugging Face", "Rainbow Hugging Face", ["png", "svg"]),
        ("hf-logo-with-title", "HF logo + title", ["png", "svg", "ai"]),
        ("hf-logo-with-white-title", "HF logo + white title", ["png", "svg", "ai"]),
    ]
    # Sanity check: confirm files exist; substitute hf-logo svg/ai as alternates for HF Logo
    have = {p.name for p in (IMAGES / "Brand Logos").iterdir()}
    if "hf-logo.svg" in have:
        # add svg/ai to HF Logo card via manual substitution
        primary_logos[0] = ("Hugging Face", "HF Logo", ["png"])
    logos_html_cards = []
    # Custom-build the HF Logo card so it pulls .svg/.ai from hf-logo.* but the .png from Hugging Face.png
    hf_logo_card = """          <div class="w-full flex flex-col">
            <img src="images/Brand Logos/Hugging Face.png" alt="HF Logo" class="w-full h-full bg-white shadow-DropShadow md:p-14 p-7 rounded-3xl object-contain">
            <div class="pl-3 pt-3">
              <h5 class="text-lg font-sans text-BluishDark">HF Logo</h5>
              <div class="flex flex-wrap gap-y-1 items-center mt-2 text-sm">
                <button x-data="{ filename: 'Hugging Face.png', imageUrl: 'images/Brand Logos/Hugging Face.png' }" x-on:click="downloadImage(imageUrl, filename)" class="flex items-center space-x-1 download-button">
                  <img src="images/download icon.svg" class="w-4 h-4" alt="">
                  <p class="text-gray-500 font-mono">.png</p>
                </button>
                <hr class="mx-3 h-3 rounded-sm border-r border-IconBorder xl:mx-2.5">
                <button x-data="{ filename: 'hf-logo.svg', imageUrl: 'images/Brand Logos/hf-logo.svg' }" x-on:click="downloadImage(imageUrl, filename)" class="flex items-center space-x-1 download-button">
                  <img src="images/download icon.svg" class="w-4 h-4" alt="">
                  <p class="text-gray-500 font-mono">.svg</p>
                </button>
                <hr class="mx-3 h-3 rounded-sm border-r border-IconBorder xl:mx-2.5">
                <button x-data="{ filename: 'hf-logo.ai', imageUrl: 'images/Brand Logos/hf-logo.ai' }" x-on:click="downloadImage(imageUrl, filename)" class="flex items-center space-x-1 download-button">
                  <img src="images/download icon.svg" class="w-4 h-4" alt="">
                  <p class="text-gray-500 font-mono">.ai</p>
                </button>
              </div>
            </div>
          </div>"""
    logos_html_cards.append(hf_logo_card)
    logos_html_cards.append(card_logo("Rainbow Hugging Face", "Rainbow Hugging Face", ["png", "svg"]))
    logos_html_cards.append(card_logo("hf-logo-with-title", "HF logo + title", ["png", "svg", "ai"]))
    logos_html_cards.append(card_logo("hf-logo-with-white-title", "HF logo + white title", ["png", "svg", "ai"], dark=True))

    logos_section = f"""      <section id="HFlogos" class="mb-28">
        <div class="flex flex-row items-center justify-between">
          <div class="font-mono max-w-fit text-3xl bg-blue-500 text-white mb-5 py-3 px-6 rounded-full">HF Logos</div>
          <div class="text-BluishDark transform hover:text-gray-900">
            <a href="https://huggingface.co/brand" target="_blank">View official HF branding guideline <svg xmlns="http://www.w3.org/2000/svg" class="inline w-6 h-6" width="32" height="32" viewBox="0 0 20 20"><path fill="currentColor" d="M9.516 6a.5.5 0 0 0 0 1h2.777l-4.147 4.146a.5.5 0 0 0 .708.708L13 7.707v2.777a.5.5 0 0 0 1 0V6.5a.5.5 0 0 0-.5-.5zm3.25 11a2.5 2.5 0 0 0 2.47-2.11A2.501 2.501 0 0 0 17 12.5v-7A2.5 2.5 0 0 0 14.5 3h-7a2.501 2.501 0 0 0-2.4 1.797A2.5 2.5 0 0 0 3 7.266V13.5A3.5 3.5 0 0 0 6.5 17zM4 7.266A1.5 1.5 0 0 1 5 5.85v6.65A2.5 2.5 0 0 0 7.5 15h6.68a1.5 1.5 0 0 1-1.414 1H6.5A2.5 2.5 0 0 1 4 13.5zM7.5 4h7A1.5 1.5 0 0 1 16 5.5v7a1.5 1.5 0 0 1-1.5 1.5h-7A1.5 1.5 0 0 1 6 12.5v-7A1.5 1.5 0 0 1 7.5 4"/></svg></a>
          </div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-10">
{chr(10).join(logos_html_cards)}
        </div>
      </section>"""

    # ---- Modern Huggies ----
    # New 2026 batch (physically in images/Huggy Collection 2026/) is rendered on TOP,
    # followed by the original modern set (images/modern Huggies/) untouched, in order.
    modern_cards = []

    # New 2026 batch first. Featured 2x2 hero cards: the 3 GIFs + two standout statics.
    new_files = list_images(IMAGES / "Huggy Collection 2026")
    new_wide = {
        "Doodle Huggy.gif",
        "Huggy Pop.gif",
        "Vibing Huggy.gif",
        "Super Huggy.png",
        "Dragon Huggy.png",
    }
    for f in new_files:
        span = "col-span-2 row-span-2" if f in new_wide else ""
        modern_cards.append(card_huggy("Huggy Collection 2026", f, span))

    # Existing modern set below, unchanged.
    modern_files = list_images(IMAGES / "modern Huggies")
    modern_wide = {"Huggy Pop.gif", "Doodle Huggy.gif", "Vibing Huggy.gif", "Super Huggy.png"}
    for f in modern_files:
        span = "col-span-2 row-span-2" if f in modern_wide else ""
        modern_cards.append(card_huggy("modern Huggies", f, span))

    modern_section = f"""      <section id="ModernHuggies" class="mb-28">
        <div class="flex items-center mb-5">
          <div class="font-mono max-w-fit text-3xl bg-blue-500 text-white py-3 px-6 rounded-full">Modern Huggies</div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-10">
{chr(10).join(modern_cards)}
        </div>
      </section>"""

    # ---- Outlined Huggies ----
    outlined_files = list_images(IMAGES / "Outlined Huggies")
    outlined_cards = [card_huggy("Outlined Huggies", f) for f in outlined_files]
    outlined_section = f"""      <section id="OutlinedHuggies" class="mb-28">
        <div class="flex items-center mb-5">
          <div class="font-mono max-w-fit text-3xl bg-blue-500 text-white py-3 px-6 rounded-full">Outlined Huggies</div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-10">
{chr(10).join(outlined_cards)}
        </div>
      </section>"""

    page = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@2.8.2/dist/alpine.min.js" defer></script>
    <script>
      function downloadImage(url, filename) {{
        var link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }}
    </script>
    <style>
      .download-button {{ transition: transform 0.2s; }}
      .download-button:active {{ transform: scale(0.80); }}
    </style>
    <link rel="stylesheet" href="css/style.css" />
    <title>HFBA v2</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  </head>
  <body class="bg-BluishWhite">
    <div class="container px-5 py-10 mx-auto">
{logos_section}

{modern_section}

{outlined_section}
    </div>
  </body>
</html>
"""

    out = ROOT / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out} ({len(page):,} chars)")
    print(f"Sections: HF Logos (4), Modern Huggies ({len(new_files)} new 2026 on top + {len(modern_files)} existing = {len(new_files) + len(modern_files)}), Outlined ({len(outlined_files)})")


if __name__ == "__main__":
    main()
