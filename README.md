---
title: HFBA v2
emoji: 🤗
colorFrom: blue
colorTo: pink
sdk: static
pinned: false
short_description: Hugging Face Brand Assets v2 — logos and Huggy collection
---

# HFBA v2

Refreshed gallery of Hugging Face brand assets — logos plus the curated Huggy collection.

## Sections

- **HF Logos** — official Hugging Face logos in PNG / SVG / AI
- **Modern Huggies** — the original modern Huggy set (29 assets, carried over from v1)
- **Outlined Huggies** — outlined Huggy set (18 assets)
- **Huggy Collection 2026** — new additions including expression and pose variants (73 assets)

## Local development

```bash
npm install
npm run watch     # rebuild css/style.css on input.css changes
```

To regenerate `index.html` from the contents of `images/`:

```bash
python _build_index.py
```

## Deploy

This is a static Space. Push the folder to a Hugging Face Space repo and the platform will serve `index.html` at the root.
