/* ============================================================
   SceneBoard — Feed Filter Interactions
   No-page-reload genre + date filtering via fetch + pushState
   ============================================================ */

(function () {
  "use strict";

  const form = document.getElementById("filters-form");
  const container = document.getElementById("event-list-container");
  const countEl = document.getElementById("feed-count");
  const filterToggle = document.getElementById("filter-toggle");
  const sidebar = document.getElementById("feed-filters");

  if (!form || !container) return;

  /* ── Mobile filter drawer ──────────────────────────────── */

  if (filterToggle && sidebar) {
    filterToggle.addEventListener("click", function () {
      const isOpen = sidebar.classList.toggle("is-open");
      filterToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  /* ── Build query string from current filter state ──────── */

  function buildParams() {
    const params = new URLSearchParams();

    // Date preset
    const dateInput = document.getElementById("date-range-input");
    if (dateInput && dateInput.value) {
      params.set("date_range", dateInput.value);
    }

    // Checked genres
    const checked = form.querySelectorAll('input[name="genres"]:checked');
    checked.forEach(function (cb) {
      params.append("genres", cb.value);
    });

    return params;
  }

  /* ── Fetch the event list partial and swap it in ────────── */

  function applyFilters() {
    const params = buildParams();
    params.set("partial", "1");

    const url = window.location.pathname + "?" + params.toString();

    // Update browser URL (without partial=1)
    const displayParams = buildParams();
    const displayUrl =
      window.location.pathname +
      (displayParams.toString() ? "?" + displayParams.toString() : "");
    history.pushState(null, "", displayUrl);

    // Show loading state
    container.classList.add("is-loading");

    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        if (!res.ok) throw new Error("Network error");
        return res.text();
      })
      .then(function (html) {
        container.innerHTML = html;
        container.classList.remove("is-loading");
        updateCount();
        bindGenreChipLinks();
      })
      .catch(function () {
        container.classList.remove("is-loading");
      });
  }

  /* ── Count events and update toolbar label ─────────────── */

  function updateCount() {
    if (!countEl) return;
    const cards = container.querySelectorAll(".event-card");
    const n = cards.length;
    countEl.textContent = n + " event" + (n === 1 ? "" : "s");
  }

  /* ── Genre chip links inside event cards ───────────────── */

  function bindGenreChipLinks() {
    container.querySelectorAll(".genre-chip--link[data-genre]").forEach(function (chip) {
      chip.addEventListener("click", function (e) {
        e.preventDefault();
        const slug = chip.dataset.genre;
        const cb = form.querySelector('input[name="genres"][value="' + slug + '"]');
        if (cb) {
          cb.checked = true;
          applyFilters();
          // Scroll sidebar into view on mobile
          if (sidebar && !sidebar.classList.contains("is-open") && window.innerWidth <= 900) {
            sidebar.classList.add("is-open");
            if (filterToggle) filterToggle.setAttribute("aria-expanded", "true");
          }
        }
      });
    });
  }

  /* ── Date preset buttons ───────────────────────────────── */

  document.querySelectorAll(".date-preset").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const preset = btn.dataset.preset;
      const dateInput = document.getElementById("date-range-input");
      if (dateInput) dateInput.value = preset;

      // Update active state
      document.querySelectorAll(".date-preset").forEach(function (b) {
        b.classList.remove("date-preset--active");
      });
      btn.classList.add("date-preset--active");

      applyFilters();
    });
  });

  /* ── Genre checkboxes ──────────────────────────────────── */

  form.querySelectorAll('input[name="genres"]').forEach(function (cb) {
    cb.addEventListener("change", applyFilters);
  });

  /* ── Clear genres button ───────────────────────────────── */

  const clearBtn = document.getElementById("clear-genres");
  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      form.querySelectorAll('input[name="genres"]').forEach(function (cb) {
        cb.checked = false;
      });
      applyFilters();
    });
  }

  /* ── Handle browser back/forward ───────────────────────── */

  window.addEventListener("popstate", function () {
    const params = new URLSearchParams(window.location.search);

    // Sync date preset UI
    const dr = params.get("date_range") || "";
    const dateInput = document.getElementById("date-range-input");
    if (dateInput) dateInput.value = dr;
    document.querySelectorAll(".date-preset").forEach(function (b) {
      b.classList.toggle("date-preset--active", b.dataset.preset === dr);
    });

    // Sync genre checkboxes
    const selectedGenres = params.getAll("genres");
    form.querySelectorAll('input[name="genres"]').forEach(function (cb) {
      cb.checked = selectedGenres.includes(cb.value);
    });

    applyFilters();
  });

  /* ── Init: bind genre chips on first load ──────────────── */

  bindGenreChipLinks();
})();
