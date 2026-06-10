/* HFBA v2 — client-side smart search.
   No backend, no dependencies. Weighted multi-field scoring with synonym
   expansion, prefix + typo-tolerant fuzzy matching, AND-semantics across terms,
   and relevance ranking. Operates by relocating existing card nodes into a ranked
   results grid (keeps the working download buttons), restoring them on clear. */
(function () {
  "use strict";

  var indexEl = document.getElementById("search-index");
  if (!indexEl) return;
  var INDEX = JSON.parse(indexEl.textContent);

  // ---------- Synonym clusters ----------
  // Each cluster groups related terms; every member expands to all the others
  // (bidirectional). Expansion targets that aren't asset-name words simply match
  // nothing, and because metadata is name-only, expansion can't flood results —
  // it only surfaces assets whose NAME contains a related word. So "headphones"
  // reaches "dj" and vice-versa, "music" reaches the whole audio family, etc.
  var CLUSTERS = [
    // music / audio
    ["music", "audio", "sound", "headphones", "headphone", "dj", "earphones", "beats"],
    ["music", "song", "sing", "singing", "karaoke", "whistle", "violin", "violinist", "baguette", "melody", "tune"],
    ["music", "dance", "dancing", "vibing", "vibe", "party", "groove", "disco"],
    // tech / ai / ml
    ["code", "coding", "developer", "programming", "dev", "software", "engineer", "transformer", "agent", "robot", "terminal"],
    ["ai", "ml", "model", "intelligence", "neural", "transformer", "agent", "assistant", "lora", "growing", "training"],
    ["gpu", "chip", "hardware", "compute", "graphics", "processor", "optimum", "card"],
    ["data", "dataset", "discover", "discovery", "scan", "database", "analytics"],
    ["robot", "bot", "android", "optimum", "machine", "cyborg"],
    ["text", "generation", "llm", "transformer", "prompt", "writing"],
    // roles / jobs
    ["doctor", "medic", "nurse", "medical", "health", "hospital", "clinic"],
    ["cook", "cooking", "kitchen", "chef", "baguette", "meal", "recipe"],
    ["law", "lawyer", "judge", "legal", "court", "justice", "attorney"],
    ["manage", "manager", "management", "boss", "lead"],
    ["assistant", "agent", "helper", "support", "butler"],
    ["guide", "diffusor", "tutorial", "howto"],
    // food
    ["food", "baguette", "wine", "yolk", "egg", "bread", "drink", "meal", "snack"],
    // characters / costumes / animals
    ["magic", "magical", "wizard", "spell", "sorcerer", "secret", "mystery", "hidden"],
    ["royal", "king", "crown", "judge", "viking", "cowboy", "warrior", "hero"],
    ["animal", "snake", "horse", "dragon", "creature", "beast", "reptile", "mascot"],
    // activities
    ["game", "gaming", "gamejam", "jam", "play", "controller", "console", "video", "esports", "arcade"],
    ["sport", "sports", "athlete", "running", "run", "rushing", "rush", "jog", "fitness", "exercise", "gym", "race"],
    ["fish", "fishing", "catch", "catching", "rod"],
    ["space", "rocket", "launch", "moon", "global", "world", "earth", "planet", "orbit"],
    ["grow", "growing", "sprout", "sprouting", "plant", "seed", "leaf", "bloom"],
    // study / science
    ["study", "learn", "learning", "education", "school", "academic", "acedemic", "student", "paper", "research", "measure", "guide", "knowledge"],
    ["science", "lab", "laboratory", "research", "experiment", "vision", "scan", "ray", "xray", "microscope"],
    ["vision", "sight", "eye", "computer", "see", "scan", "view", "look"],
    // greetings / reactions / emotions -> expressive named assets
    ["greeting", "greet", "hi", "hello", "hey", "wave", "waving", "sunny", "welcome"],
    ["ok", "okay", "approve", "approved", "thumbs", "like", "yes", "respect", "nod", "double", "props", "good"],
    ["happy", "joy", "smile", "smiling", "cheerful", "sunny", "excited", "super", "vibing", "cool", "pop", "glad", "okay"],
    ["excited", "exciting", "thrilled", "amazed", "starry", "super", "learning", "wow"],
    ["sad", "unhappy", "down", "nervous", "frustrated", "upset", "worried", "cry"],
    ["angry", "mad", "frustrated", "rage", "chad", "yell", "furious"],
    ["cool", "chill", "smug", "chad", "swag", "confident", "calm"],
    ["sneaky", "sneak", "peek", "peeking", "tiptoe", "secret", "hidden", "quiet"],
    ["curious", "wonder", "peeking", "question", "interested", "inquisitive"],
    ["love", "loving", "heart", "hug", "hugging", "like", "adore", "family"],
    ["family", "together", "group", "parents", "home", "loving"],
    // brand / logos / style
    ["logo", "brand", "mark", "icon", "wordmark", "hf", "hugging", "emblem", "identity"],
    ["rainbow", "colorful", "gradient", "pride", "color"],
    ["outline", "outlined", "lineart", "line", "sketch", "doodle", "drawing"],
    ["doodle", "sketch", "draw", "drawing", "scribble", "comic"],
    ["comic", "cartoon", "manga", "strip"],
    ["paper", "document", "report", "article", "read", "research"],
    ["wine", "drink", "glass", "celebrate", "cheers"],
    ["lean", "leaning", "tilt", "tilting", "side"],
  ];

  // Build a bidirectional synonym map from the clusters (deduped).
  var SYN = (function () {
    var acc = {};
    CLUSTERS.forEach(function (cl) {
      cl.forEach(function (w) {
        var set = acc[w] || (acc[w] = {});
        cl.forEach(function (o) { if (o !== w) set[o] = true; });
      });
    });
    var out = {};
    Object.keys(acc).forEach(function (k) { out[k] = Object.keys(acc[k]); });
    return out;
  })();

  // ---------- helpers ----------
  function tokenize(s) {
    if (!s) return [];
    return String(s)
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter(function (t) { return t.length > 0; });
  }

  function lev(a, b) {
    var m = a.length, n = b.length;
    if (Math.abs(m - n) > 2) return 3;
    var prev = new Array(n + 1), cur = new Array(n + 1), i, j;
    for (j = 0; j <= n; j++) prev[j] = j;
    for (i = 1; i <= m; i++) {
      cur[0] = i;
      for (j = 1; j <= n; j++) {
        var cost = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
      }
      var t = prev; prev = cur; cur = t;
    }
    return prev[n];
  }

  // Field weights
  var W = { name: 10, tags: 7, syn: 6, section: 4, attr: 3, desc: 2, file: 1 };

  // Precompute per-record weighted fields
  var RECS = INDEX.map(function (e) {
    function field(w, str, extraTokens) {
      var toks = tokenize(str);
      if (extraTokens) toks = toks.concat(extraTokens);
      return { w: w, set: new Set(toks), text: " " + toks.join(" ") + " " };
    }
    var attrStr = (e.attr || []).join(" ");
    return {
      id: e.id,
      nameLower: (e.name || "").toLowerCase(),
      fields: [
        field(W.name, e.name),
        field(W.tags, (e.tags || []).join(" ")),
        field(W.syn, (e.syn || []).join(" ")),
        field(W.section, e.section),
        field(W.attr, attrStr),
        field(W.desc, e.desc),
        field(W.file, (e.file || "").replace(/\.[^.]+$/, "")),
      ],
    };
  });

  function expand(tok) {
    // The typed token gets full matching (prefix/substring/fuzzy for typo tolerance).
    // Synonym expansions are matched EXACTLY — they're controlled vocab that maps to
    // real name words, so fuzzy/prefix on them would create cross-noise.
    var out = [{ t: tok, f: 1, syn: false }];
    var syns = SYN[tok];
    if (syns) for (var i = 0; i < syns.length; i++) out.push({ t: syns[i], f: 0.8, syn: true });
    return out;
  }

  function fieldScore(t, f) {
    if (f.set.has(t)) return f.w * 3;
    if (t.length >= 2) {
      for (var ft of f.set) { if (ft.length > t.length && ft.indexOf(t) === 0) return f.w * 2; }
    }
    if (t.length >= 3 && f.text.indexOf(t) !== -1) return f.w * 1.5;
    var maxD = t.length >= 7 ? 2 : t.length >= 4 ? 1 : 0;
    if (maxD > 0) {
      for (var ft2 of f.set) {
        if (Math.abs(ft2.length - t.length) <= maxD && lev(ft2, t) <= maxD) return f.w * 1;
      }
    }
    return 0;
  }

  // Synonym expansions only count on an exact token hit (no prefix/substring/fuzzy).
  function fieldScoreExact(t, f) { return f.set.has(t) ? f.w * 3 : 0; }

  function scoreRecord(rec, qtokens, rawQuery) {
    var total = 0;
    for (var i = 0; i < qtokens.length; i++) {
      var variants = expand(qtokens[i]);
      var best = 0;
      for (var v = 0; v < variants.length; v++) {
        var vt = variants[v];
        for (var fi = 0; fi < rec.fields.length; fi++) {
          var s = vt.syn
            ? vt.f * fieldScoreExact(vt.t, rec.fields[fi])
            : vt.f * fieldScore(vt.t, rec.fields[fi]);
          if (s > best) best = s;
        }
      }
      if (best <= 0) return 0; // AND: every term must match somewhere
      total += best;
    }
    if (rawQuery.length >= 2 && rec.nameLower.indexOf(rawQuery) !== -1) total *= 1.2; // phrase boost
    return total;
  }

  function search(query) {
    var raw = query.trim().toLowerCase();
    var qtokens = tokenize(raw);
    if (!qtokens.length) return null;
    var hits = [];
    for (var i = 0; i < RECS.length; i++) {
      var sc = scoreRecord(RECS[i], qtokens, raw);
      if (sc > 0) hits.push({ id: RECS[i].id, score: sc, name: RECS[i].nameLower });
    }
    hits.sort(function (a, b) { return b.score - a.score || a.name.localeCompare(b.name); });
    // Relevance floor: drop the long tail that scores far below the best match.
    // Keeps precise, ranked results and trims weak fuzzy/synonym noise.
    if (hits.length) {
      var floor = hits[0].score * 0.28;
      hits = hits.filter(function (h) { return h.score >= floor; });
    }
    return { tokens: qtokens, hits: hits };
  }

  // ---------- DOM wiring ----------
  var byId = {};
  document.querySelectorAll("[data-id]").forEach(function (el) { byId[el.dataset.id] = el; });

  // remember original layout to restore on clear
  var grids = [].slice.call(document.querySelectorAll(".card-grid"));
  var originalOrder = grids.map(function (g) {
    return { grid: g, ids: [].slice.call(g.children).filter(function (c) { return c.dataset.id; }).map(function (c) { return c.dataset.id; }) };
  });
  var allIdsInOrder = originalOrder.reduce(function (acc, o) { return acc.concat(o.ids); }, []);
  // store original heading text per card title (for un-highlighting)
  var titleEls = {};
  Object.keys(byId).forEach(function (id) {
    var h5 = byId[id].querySelector("h5");
    if (h5) titleEls[id] = { el: h5, text: h5.textContent };
  });

  var input = document.getElementById("q");
  var clearBtn = document.getElementById("q-clear");
  var browse = document.getElementById("browse");
  var results = document.getElementById("searchResults");
  var bar = document.getElementById("results-bar");
  var countEl = document.getElementById("results-count");
  var noRes = document.getElementById("no-results");
  var resultsClear = document.getElementById("results-clear");
  var moreSection = document.getElementById("more-section");
  var more = document.getElementById("moreResults");
  var moreHeading = document.getElementById("more-heading");

  function highlight(id, tokens) {
    var t = titleEls[id];
    if (!t) return;
    var text = t.text;
    var html = "";
    var lower = text.toLowerCase();
    // greedily mark earliest token occurrences
    var marks = [];
    tokens.forEach(function (tok) {
      if (tok.length < 2) return;
      var from = 0, idx;
      while ((idx = lower.indexOf(tok, from)) !== -1) { marks.push([idx, idx + tok.length]); from = idx + tok.length; }
    });
    if (!marks.length) { t.el.textContent = text; return; }
    marks.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [marks[0]];
    for (var i = 1; i < marks.length; i++) {
      var last = merged[merged.length - 1];
      if (marks[i][0] <= last[1]) last[1] = Math.max(last[1], marks[i][1]);
      else merged.push(marks[i]);
    }
    var pos = 0;
    merged.forEach(function (m) {
      html += escapeHtml(text.slice(pos, m[0])) + "<mark>" + escapeHtml(text.slice(m[0], m[1])) + "</mark>";
      pos = m[1];
    });
    html += escapeHtml(text.slice(pos));
    t.el.innerHTML = html;
  }
  function escapeHtml(s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function clearHighlights() { Object.keys(titleEls).forEach(function (id) { titleEls[id].el.textContent = titleEls[id].text; }); }

  function enterBrowse() {
    results.classList.remove("show");
    bar.classList.remove("show");
    noRes.classList.remove("show");
    moreSection.classList.remove("show");
    browse.style.display = "";
    // move every card back to its home grid in original order
    originalOrder.forEach(function (o) {
      o.ids.forEach(function (id) { if (byId[id]) o.grid.appendChild(byId[id]); });
    });
    clearHighlights();
  }

  function runSearch(query) {
    var res = search(query);
    if (!res) { enterBrowse(); return; }
    browse.style.display = "none";
    clearHighlights();
    results.innerHTML = "";
    more.innerHTML = "";
    // ranked matches into the results grid (highlighted)
    var matched = {};
    res.hits.forEach(function (h) {
      matched[h.id] = true;
      var el = byId[h.id];
      if (el) { results.appendChild(el); highlight(h.id, res.tokens); }
    });
    // every non-matching asset below, in original browse order — seamless browsing
    allIdsInOrder.forEach(function (id) {
      if (!matched[id]) { var el = byId[id]; if (el) more.appendChild(el); }
    });
    var n = res.hits.length;
    if (n > 0) {
      countEl.innerHTML = "<b>" + n + "</b> " + (n === 1 ? "result" : "results") + " for &ldquo;" + escapeHtml(query.trim()) + "&rdquo;";
    } else {
      countEl.innerHTML = "No matches for &ldquo;" + escapeHtml(query.trim()) + "&rdquo; &mdash; browse everything below";
    }
    bar.classList.add("show");
    results.classList.toggle("show", n > 0);
    noRes.classList.remove("show"); // soft no-results: the bar message + full browse list below
    moreHeading.textContent = n > 0 ? "More to explore" : "All Huggies";
    moreSection.classList.toggle("show", more.children.length > 0);
  }

  var debounce;
  function onInput() {
    var v = input.value;
    clearBtn.classList.toggle("show", v.length > 0);
    clearTimeout(debounce);
    debounce = setTimeout(function () {
      if (v.trim()) runSearch(v); else enterBrowse();
    }, 90);
  }
  input.addEventListener("input", onInput);

  function clearSearch(focus) {
    input.value = "";
    clearBtn.classList.remove("show");
    enterBrowse();
    if (focus) input.focus();
  }
  clearBtn.addEventListener("click", function () { clearSearch(true); });
  resultsClear.addEventListener("click", function () { clearSearch(true); });

  // quick-filter chips
  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      input.value = chip.dataset.q;
      clearBtn.classList.add("show");
      runSearch(chip.dataset.q);
      input.focus();
    });
  });

  // collapse the quick-filter chips once scrolled away from the top;
  // they reappear when back near the top. Keeps the search field always visible.
  // Hysteresis: collapse once scrolled past COLLAPSE_AT, re-expand only below
  // EXPAND_AT. The dead zone between them stops jitter near a single threshold
  // (trackpad/momentum) from rapidly toggling the class and flickering the chips.
  var header = document.getElementById("search-header");
  var COLLAPSE_AT = 56, EXPAND_AT = 6;
  var condensed = false;
  function syncCondensed() {
    var y = window.pageYOffset || document.documentElement.scrollTop || 0;
    if (!condensed && y > COLLAPSE_AT) {
      condensed = true;
      header.classList.add("condensed");
    } else if (condensed && y < EXPAND_AT) {
      condensed = false;
      header.classList.remove("condensed");
    }
  }
  window.addEventListener("scroll", syncCondensed, { passive: true });
  syncCondensed();

  // keyboard: "/" or Cmd/Ctrl+K focuses; Esc clears
  document.addEventListener("keydown", function (e) {
    if ((e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) &&
        document.activeElement !== input) {
      e.preventDefault();
      input.focus();
      input.select();
    } else if (e.key === "Escape" && document.activeElement === input) {
      clearSearch(false);
      input.blur();
    }
  });
})();
