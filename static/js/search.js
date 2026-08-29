(function () {
  "use strict";

  var container = document.querySelector(".search-page");
  if (!container) return;

  var indexUrl = container.getAttribute("data-search-index-url");
  var input = document.getElementById("search-input");
  var status = document.getElementById("search-status");
  var results = document.getElementById("search-results");
  var categorySelect = document.getElementById("filter-category");
  var tagSelect = document.getElementById("filter-tag");
  var yearSelect = document.getElementById("filter-year");
  var sortSelect = document.getElementById("filter-sort");

  var posts = [];
  var loaded = false;

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function populateFilters() {
    var categories = new Set();
    var tags = new Set();
    var years = new Set();
    posts.forEach(function (post) {
      categories.add(post.category);
      (post.tags || []).forEach(function (t) { tags.add(t); });
      years.add(post.year);
    });

    function fill(select, values) {
      Array.from(values).sort().forEach(function (value) {
        var option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
    }
    fill(categorySelect, categories);
    fill(tagSelect, tags);
    fill(yearSelect, Array.from(years).sort().reverse());
  }

  function tokenize(query) {
    return query
      .toLowerCase()
      .split(/\s+/)
      .map(function (t) { return t.trim(); })
      .filter(Boolean);
  }

  function scorePost(post, tokens) {
    if (tokens.length === 0) return 0;
    var title = (post.title || "").toLowerCase();
    var content = (post.content || "").toLowerCase();
    var category = (post.category || "").toLowerCase();
    var author = (post.author || "").toLowerCase();
    var tags = (post.tags || []).join(" ").toLowerCase();

    var score = 0;
    for (var i = 0; i < tokens.length; i++) {
      var t = tokens[i];
      var matched = false;
      if (title.indexOf(t) !== -1) { score += 5; matched = true; }
      if (tags.indexOf(t) !== -1) { score += 4; matched = true; }
      if (category.indexOf(t) !== -1) { score += 3; matched = true; }
      if (author.indexOf(t) !== -1) { score += 2; matched = true; }
      if (content.indexOf(t) !== -1) { score += 1; matched = true; }
      if (!matched) return -1; // require every token to match somewhere (AND search)
    }
    return score;
  }

  function highlightSnippet(post, tokens) {
    var content = post.content || post.excerpt || "";
    if (tokens.length === 0) return escapeHtml((post.excerpt || content).slice(0, 180));
    var lower = content.toLowerCase();
    var idx = -1;
    for (var i = 0; i < tokens.length && idx === -1; i++) {
      idx = lower.indexOf(tokens[i]);
    }
    if (idx === -1) return escapeHtml((post.excerpt || content).slice(0, 180));
    var start = Math.max(0, idx - 60);
    var end = Math.min(content.length, idx + 120);
    var snippet = content.slice(start, end);
    var escaped = escapeHtml(snippet);
    tokens.forEach(function (t) {
      if (!t) return;
      var re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
      escaped = escaped.replace(re, "<mark>$1</mark>");
    });
    return (start > 0 ? "…" : "") + escaped + (end < content.length ? "…" : "");
  }

  function render(tokens) {
    var category = categorySelect.value;
    var tag = tagSelect.value;
    var year = yearSelect.value;
    var sort = sortSelect.value;

    var scored = posts
      .filter(function (post) {
        if (category && post.category !== category) return false;
        if (tag && (post.tags || []).indexOf(tag) === -1) return false;
        if (year && String(post.year) !== year) return false;
        return true;
      })
      .map(function (post) { return { post: post, score: scorePost(post, tokens) }; })
      .filter(function (entry) { return tokens.length === 0 || entry.score >= 0; });

    if (sort === "date") {
      scored.sort(function (a, b) { return b.post.date.localeCompare(a.post.date); });
    } else {
      scored.sort(function (a, b) {
        return b.score - a.score || b.post.date.localeCompare(a.post.date);
      });
    }

    results.innerHTML = "";
    scored.slice(0, 100).forEach(function (entry) {
      var post = entry.post;
      var li = document.createElement("li");
      li.className = "search-result";
      li.innerHTML =
        '<h3><a href="' + post.url + '">' + escapeHtml(post.title || "Untitled") + "</a></h3>" +
        '<div class="search-result-meta">' +
        escapeHtml(post.date) + " · " + escapeHtml(post.category) +
        (post.author ? " · " + escapeHtml(post.author) : "") +
        "</div>" +
        "<p>" + highlightSnippet(post, tokens) + "</p>";
      results.appendChild(li);
    });

    if (tokens.length === 0 && !category && !tag && !year) {
      status.textContent = "Type to search " + posts.length + " posts.";
    } else {
      status.textContent = scored.length + " result" + (scored.length === 1 ? "" : "s") + " found.";
    }
  }

  var debounceTimer = null;
  function scheduleRender() {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(function () {
      render(tokenize(input.value));
    }, 80);
  }

  fetch(indexUrl)
    .then(function (response) { return response.json(); })
    .then(function (data) {
      posts = data.posts || [];
      loaded = true;
      populateFilters();
      render([]);
    })
    .catch(function () {
      status.textContent = "Search index failed to load.";
    });

  [input, categorySelect, tagSelect, yearSelect, sortSelect].forEach(function (el) {
    if (!el) return;
    el.addEventListener("input", scheduleRender);
    el.addEventListener("change", scheduleRender);
  });

  var params = new URLSearchParams(window.location.search);
  var initialQuery = params.get("q");
  if (initialQuery) input.value = initialQuery;
})();
