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


def _load_records() -> list:
    if not METADATA_PATH.exists():
        return []
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


_RECORDS = _load_records()
_ID_MAP = {(r.get("folder"), r.get("filename")): r.get("id") for r in _RECORDS}


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


def card_logo(stem: str, title: str, exts: list[str], dark: bool = False, data_id: str = "") -> str:
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
    id_attr = f' data-id="{html.escape(data_id)}"' if data_id else ""
    return f"""          <div class="w-full flex flex-col"{id_attr}>
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
    asset_id = _ID_MAP.get(key)
    id_attr = f' data-id="{html.escape(asset_id)}"' if asset_id else ""
    return f"""          <div class="w-full flex flex-col{span_class}"{id_attr}{data_attrs}>
            <img src="{html.escape(img_path)}" alt="{html.escape(title)}" class="w-full h-full bg-white shadow-DropShadow {pad_class} rounded-3xl object-contain">
            <div class="px-3 pt-3 flex flex-col gap-1 md:flex-row md:justify-between md:items-center">
              <h5 class="text-lg font-sans text-BluishDark">{html.escape(title)}</h5>
              <button x-data="{{ filename: '{html.escape(filename)}', imageUrl: '{html.escape(img_path)}' }}" x-on:click="downloadImage(imageUrl, filename)" class="flex items-center space-x-1 download-button">
                <img src="images/download icon.svg" class="w-4 h-4 hidden md:inline-block" alt="">
                <p class="text-gray-500 font-mono hidden md:inline-block">.{ext}</p>
              </button>
            </div>
          </div>"""


def tiled_cards(folder: str, files: list[str], hero_set: set) -> list[str]:
    """Render cards with 2x2 'hero' tiles spread evenly through the singles.

    Mirrors the original Modern Huggies cadence: one large feature tile roughly
    every (singles // heroes) cards. Combined with `grid-auto-flow: dense` on the
    container, every cell beside a hero is backfilled by the next single card, so
    the grid never shows skipped/empty cells at any column count.
    """
    heroes = [f for f in files if f in hero_set]
    singles = [f for f in files if f not in hero_set]
    if not heroes:
        return [card_huggy(folder, f) for f in singles]

    per = max(1, len(singles) // len(heroes))  # singles to trail each hero
    cards: list[str] = []
    si = 0
    for hero in heroes:
        cards.append(card_huggy(folder, hero, "col-span-2 row-span-2"))
        chunk = singles[si:si + per]
        si += len(chunk)
        cards.extend(card_huggy(folder, s) for s in chunk)
    cards.extend(card_huggy(folder, s) for s in singles[si:])
    return cards


def section_header(title: str, link_html: str = "") -> str:
    right = f"""<div class="text-BluishDark transform hover:text-gray-900">{link_html}</div>""" if link_html else ""
    return f"""        <div class="flex flex-row items-center justify-between mb-5">
          <div class="font-mono max-w-fit text-3xl bg-blue-500 text-white py-3 px-6 rounded-full">{html.escape(title)}</div>
          {right}
        </div>"""


def build_search_index() -> str:
    """Compact JSON search index over every card (Huggies + logos), embedded inline.
    Each entry holds the fields the client search engine scores against."""
    entries = []
    for r in _RECORDS:
        section = "Outlined Huggies" if r.get("category") == "outlined" else "Modern Huggies"
        entries.append({
            "id": r.get("id"),
            "name": r.get("display_name", ""),
            "section": section,
            "tags": [str(t).lower() for t in (r.get("tags") or [])],
            "syn": [str(t).lower() for t in (r.get("synonyms") or [])],
            "attr": [str(x).lower() for x in (
                [r.get("expression"), r.get("pose"), r.get("hands")]
                + (r.get("mood") or []) + (r.get("theme") or []) + (r.get("colors") or [])
                + (r.get("headwear") or []) + (r.get("outfit") or [])
                + (r.get("face_accessories") or []) + (r.get("held_objects") or [])
                + (r.get("effects") or [])
            ) if x],
            "desc": r.get("description", ""),
            "file": r.get("filename", ""),
        })

    # HF logos (no metadata record — describe them for search)
    logos = [
        ("logo__hf-logo", "HF Logo", ["logo", "brand", "hugging face", "hf", "mark", "icon", "emoji"]),
        ("logo__rainbow", "Rainbow Hugging Face", ["logo", "brand", "rainbow", "colorful", "gradient", "pride", "hf"]),
        ("logo__title", "HF logo + title", ["logo", "brand", "wordmark", "title", "text", "hugging face", "hf"]),
        ("logo__white-title", "HF logo + white title", ["logo", "brand", "wordmark", "title", "white", "dark", "hugging face", "hf"]),
    ]
    for lid, name, tags in logos:
        entries.append({
            "id": lid, "name": name, "section": "Logos",
            "tags": tags, "syn": [], "attr": [], "desc": "official hugging face brand logo", "file": name,
        })

    return json.dumps(entries, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


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
    hf_logo_card = """          <div class="w-full flex flex-col" data-id="logo__hf-logo">
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
    logos_html_cards.append(card_logo("Rainbow Hugging Face", "Rainbow Hugging Face", ["png", "svg"], data_id="logo__rainbow"))
    logos_html_cards.append(card_logo("hf-logo-with-title", "HF logo + title", ["png", "svg", "ai"], data_id="logo__title"))
    logos_html_cards.append(card_logo("hf-logo-with-white-title", "HF logo + white title", ["png", "svg", "ai"], dark=True, data_id="logo__white-title"))

    logos_section = f"""      <section id="HFlogos" class="mb-28">
        <div class="flex flex-row items-center justify-between">
          <div class="font-mono max-w-fit text-3xl bg-blue-500 text-white mb-5 py-3 px-6 rounded-full">HF Logos</div>
          <div class="text-BluishDark transform hover:text-gray-900">
            <a href="https://huggingface.co/brand" target="_blank">View official HF branding guideline <svg xmlns="http://www.w3.org/2000/svg" class="inline w-6 h-6" width="32" height="32" viewBox="0 0 20 20"><path fill="currentColor" d="M9.516 6a.5.5 0 0 0 0 1h2.777l-4.147 4.146a.5.5 0 0 0 .708.708L13 7.707v2.777a.5.5 0 0 0 1 0V6.5a.5.5 0 0 0-.5-.5zm3.25 11a2.5 2.5 0 0 0 2.47-2.11A2.501 2.501 0 0 0 17 12.5v-7A2.5 2.5 0 0 0 14.5 3h-7a2.501 2.501 0 0 0-2.4 1.797A2.5 2.5 0 0 0 3 7.266V13.5A3.5 3.5 0 0 0 6.5 17zM4 7.266A1.5 1.5 0 0 1 5 5.85v6.65A2.5 2.5 0 0 0 7.5 15h6.68a1.5 1.5 0 0 1-1.414 1H6.5A2.5 2.5 0 0 1 4 13.5zM7.5 4h7A1.5 1.5 0 0 1 16 5.5v7a1.5 1.5 0 0 1-1.5 1.5h-7A1.5 1.5 0 0 1 6 12.5v-7A1.5 1.5 0 0 1 7.5 4"/></svg></a>
          </div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-10 card-grid">
{chr(10).join(logos_html_cards)}
        </div>
      </section>"""

    # ---- Modern Huggies ----
    # New 2026 batch (physically in images/Huggy Collection 2026/) renders on TOP with
    # feature tiles spread evenly; the original modern set follows below, untouched.
    # `grid-auto-flow: dense` guarantees no skipped cells around the 2x2 heroes.
    modern_cards = []

    # New 2026 batch first. Feature 2x2 tiles: the 3 GIFs + standout statics, spread evenly.
    new_files = list_images(IMAGES / "Huggy Collection 2026")
    new_wide = {
        "Doodle Huggy.gif",
        "Huggy Pop.gif",
        "Vibing Huggy.gif",
        "Super Huggy.png",
        "Dragon Huggy.png",
        "Viking Huggy.png",
    }
    modern_cards.extend(tiled_cards("Huggy Collection 2026", new_files, new_wide))

    # Existing modern set below, left in its current order; heroes marked in place.
    modern_files = list_images(IMAGES / "modern Huggies")
    modern_wide = {"Huggy Pop.gif", "Doodle Huggy.gif", "Vibing Huggy.gif", "Super Huggy.png"}
    for f in modern_files:
        span = "col-span-2 row-span-2" if f in modern_wide else ""
        modern_cards.append(card_huggy("modern Huggies", f, span))

    modern_section = f"""      <section id="ModernHuggies" class="mb-28">
        <div class="flex items-center mb-5">
          <div class="font-mono max-w-fit text-3xl bg-blue-500 text-white py-3 px-6 rounded-full">Modern Huggies</div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-10 card-grid" style="grid-auto-flow: dense">
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
        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-10 card-grid">
{chr(10).join(outlined_cards)}
        </div>
      </section>"""

    search_index_json = build_search_index()
    chips = ["happy", "sad", "headphones", "coding", "gpu", "wizard", "dancing", "chef", "logo", "outlined"]
    chips_html = "\n".join(
        f'          <button class="chip" data-q="{c}">{c}</button>' for c in chips
    )

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

      /* ---- Search ---- */
      #search-header {{ position: sticky; top: 0; z-index: 30; background: rgba(243,247,250,.9); backdrop-filter: blur(8px); border-bottom: 1px solid #E2E8EF; }}
      /* .search-inner reuses the page `container mx-auto px-5` so its edges align
         with the gallery grid at every breakpoint; only vertical padding is custom. */
      .search-inner {{ padding-top: 14px; padding-bottom: 14px; }}
      .search-wrap {{ display: flex; align-items: center; gap: 10px; background: #fff; border: 1px solid #D2DAE1; border-radius: 999px; padding: 10px 16px; box-shadow: 0 8.5px 28.4px rgba(192,198,204,.25); transition: border-color .15s, box-shadow .15s; }}
      .search-wrap:focus-within {{ border-color: #3B82F6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }}
      .search-wrap svg {{ flex: 0 0 auto; color: #9aa6b1; }}
      #q {{ flex: 1 1 auto; border: none; outline: none; background: transparent; font-family: 'Source Sans 3', sans-serif; font-size: 16px; color: #4D5862; }}
      #q::placeholder {{ color: #9aa6b1; }}
      #q-clear {{ flex: 0 0 auto; border: none; background: #EEF2F6; color: #6b7280; width: 24px; height: 24px; border-radius: 999px; cursor: pointer; font-size: 15px; line-height: 1; display: none; }}
      #q-clear.show {{ display: inline-flex; align-items: center; justify-content: center; }}
      .kbd {{ flex: 0 0 auto; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #9aa6b1; border: 1px solid #D2DAE1; border-radius: 6px; padding: 2px 6px; }}
      #chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; max-height: 240px; overflow: hidden; transition: max-height .28s ease, opacity .2s ease, margin-top .28s ease; }}
      #search-header.condensed #chips {{ max-height: 0; opacity: 0; margin-top: 0; pointer-events: none; }}
      .chip {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #4D5862; background: #fff; border: 1px solid #D2DAE1; border-radius: 999px; padding: 5px 12px; cursor: pointer; transition: background .12s, color .12s, border-color .12s; }}
      .chip:hover {{ background: #3B82F6; color: #fff; border-color: #3B82F6; }}
      #results-bar {{ display: none; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 18px; }}
      #results-bar.show {{ display: flex; }}
      #results-count {{ font-family: 'IBM Plex Mono', monospace; font-size: 15px; color: #4D5862; }}
      #results-count b {{ color: #3B82F6; }}
      #results-clear {{ font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: #6b7280; background: #fff; border: 1px solid #D2DAE1; border-radius: 999px; padding: 7px 14px; cursor: pointer; }}
      #searchResults {{ display: none; }}
      #searchResults.show {{ display: grid; }}
      /* results render uniform (no 2x2 heroes) */
      #searchResults > * {{ grid-column: auto !important; grid-row: auto !important; }}
      #no-results {{ display: none; text-align: center; padding: 60px 20px; color: #6b7280; }}
      #no-results.show {{ display: block; }}
      #no-results .big {{ font-family: 'IBM Plex Mono', monospace; font-size: 20px; color: #4D5862; margin-bottom: 8px; }}
      mark {{ background: #FEF08A; color: inherit; border-radius: 3px; padding: 0 1px; }}
    </style>
    <link rel="stylesheet" href="css/style.css" />
    <title>HFBA v2</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  </head>
  <body class="bg-BluishWhite">
    <header id="search-header">
      <div class="container mx-auto px-5 search-inner">
        <div class="search-wrap" role="search">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <input id="q" type="text" autocomplete="off" spellcheck="false" aria-label="Search assets"
                 placeholder="Search Huggies &mdash; try &ldquo;happy&rdquo;, &ldquo;headphones&rdquo;, &ldquo;coding&rdquo;, &ldquo;logo&rdquo;&hellip;">
          <button id="q-clear" aria-label="Clear search">&times;</button>
          <span class="kbd">/</span>
        </div>
        <div id="chips">
{chips_html}
        </div>
      </div>
    </header>

    <div class="container px-5 py-10 mx-auto">
      <div id="results-bar">
        <span id="results-count"></span>
        <button id="results-clear">Clear search</button>
      </div>
      <div id="searchResults" class="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-10"></div>
      <div id="no-results">
        <div class="big">No Huggies match that</div>
        <div>Try a simpler word, an emotion, an object, or pick a chip above.</div>
      </div>

      <div id="browse">
{logos_section}

{modern_section}

{outlined_section}
      </div>
    </div>

    <script id="search-index" type="application/json">{search_index_json}</script>
    <script src="search.js" defer></script>
  </body>
</html>
"""

    out = ROOT / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out} ({len(page):,} chars)")
    print(f"Sections: HF Logos (4), Modern Huggies ({len(new_files)} new 2026 on top + {len(modern_files)} existing = {len(new_files) + len(modern_files)}), Outlined ({len(outlined_files)})")


if __name__ == "__main__":
    main()
