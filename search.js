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

  // ---------- Synonym dictionary (query word -> related concepts) ----------
  // Curated query->name-word bridges. Every expansion target is a word that
  // actually appears in an asset NAME, so synonym matches stay relevant.
  var SYN = {
    // music / audio
    music: ["headphones", "dj", "karaoke", "violinist", "dancing", "vibing", "whistle", "baguette"],
    audio: ["headphones", "dj"],
    dj: ["headphones", "karaoke"],
    song: ["karaoke", "whistle", "violinist"],
    sing: ["karaoke", "whistle"],
    dance: ["dancing", "vibing"],
    party: ["dancing", "vibing", "karaoke"],
    violin: ["violinist", "baguette"],
    // tech / ai / ml
    code: ["transformer", "agent", "robot", "gpu", "lab"],
    coding: ["transformer", "agent", "robot", "gpu"],
    developer: ["transformer", "agent", "robot"],
    programming: ["transformer", "agent", "robot"],
    dev: ["transformer", "agent", "robot"],
    ai: ["transformer", "agent", "assistant", "model", "lora", "gpu"],
    ml: ["model", "transformer", "lora", "gpu", "dataset"],
    model: ["growing", "lora", "transformer"],
    llm: ["transformer", "text", "generation", "agent"],
    chip: ["gpu", "optimum"],
    hardware: ["gpu", "optimum", "robot"],
    compute: ["gpu", "optimum"],
    data: ["dataset", "discover", "discovery", "scan"],
    dataset: ["discover", "discovery"],
    optimize: ["optimum"],
    bot: ["robot", "agent", "assistant"],
    // roles / jobs
    doctor: ["medic"],
    nurse: ["medic"],
    medical: ["medic", "scan", "ray"],
    health: ["medic"],
    cook: ["chef", "baguette"],
    cooking: ["chef"],
    kitchen: ["chef"],
    lawyer: ["judge"],
    law: ["lawyer", "judge"],
    agent: ["assistant", "transformer"],
    assistant: ["agent"],
    // food
    food: ["baguette", "wine", "yolk", "chef"],
    bread: ["baguette"],
    drink: ["wine"],
    egg: ["yolk"],
    // characters / costumes / animals
    magic: ["wizard", "secret"],
    wizard: ["magic", "secret"],
    king: ["judge", "viking", "cowboy"],
    animal: ["snake", "horse", "dragon"],
    // activities
    play: ["gaming", "game", "video"],
    gaming: ["game", "video"],
    game: ["gaming", "jam", "video"],
    sport: ["athlete", "running", "rushing"],
    run: ["running", "rushing"],
    running: ["rushing", "athlete"],
    exercise: ["athlete", "running"],
    fish: ["fishing"],
    catch: ["catching", "fishing"],
    space: ["rocket", "global"],
    world: ["global"],
    // study / science
    study: ["acedemic", "learning", "paper", "guide", "measure"],
    learn: ["learning", "acedemic", "paper"],
    academic: ["acedemic", "paper", "learning"],
    school: ["acedemic", "learning"],
    student: ["acedemic", "learning"],
    research: ["paper", "lab", "scan"],
    science: ["lab", "vision", "scan", "ray", "medic"],
    // greetings / reactions / emotions -> expressive named assets
    hello: ["hi", "greeting", "sunny"],
    hi: ["hello", "greeting"],
    wave: ["greeting", "hi", "hello"],
    greeting: ["hi", "hello"],
    ok: ["okay", "approved", "thumbs"],
    approve: ["approved", "thumbs", "okay"],
    respect: ["approved"],
    thumbs: ["approved", "okay", "double"],
    like: ["approved", "thumbs"],
    happy: ["sunny", "excited", "super", "vibing", "cool", "pop", "okay"],
    excited: ["super", "learning", "starry"],
    sad: ["nervous", "frustrated"],
    angry: ["frustrated", "chad"],
    cool: ["smug", "chad"],
    sneaky: ["peeking", "tiptoe", "secret"],
    peek: ["peeking"],
    // brand / logos / style
    logo: ["brand", "mark", "icon", "hf", "hugging"],
    brand: ["logo", "mark", "hf"],
    rainbow: ["colorful"],
    outline: ["outlined"],
    outlined: ["outline"],
    sketch: ["doodle"],
  };

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
    var out = [{ t: tok, f: 1 }];
    var syns = SYN[tok];
    if (syns) for (var i = 0; i < syns.length; i++) out.push({ t: syns[i], f: 0.82 });
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

  function scoreRecord(rec, qtokens, rawQuery) {
    var total = 0;
    for (var i = 0; i < qtokens.length; i++) {
      var variants = expand(qtokens[i]);
      var best = 0;
      for (var v = 0; v < variants.length; v++) {
        var vt = variants[v];
        for (var fi = 0; fi < rec.fields.length; fi++) {
          var s = vt.f * fieldScore(vt.t, rec.fields[fi]);
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
  var header = document.getElementById("search-header");
  function syncCondensed() {
    var y = window.pageYOffset || document.documentElement.scrollTop || 0;
    header.classList.toggle("condensed", y > 12);
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
