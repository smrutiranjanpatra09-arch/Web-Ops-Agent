// Cosmetic client-side interactivity only. The extraction pipeline reads
// static server-rendered HTML (Playwright captures the DOM after network-idle,
// before any of this runs against user input), so nothing here can change
// what the agent observes - it only makes the fixture feel like a live site
// for anyone browsing it directly.
(function () {
  function openModal(title, body) {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal-box">
        <div class="modal-title">${title}</div>
        <div class="modal-body">${body}</div>
        <button class="modal-close">Close</button>
      </div>`;
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay || e.target.classList.contains("modal-close")) {
        overlay.remove();
      }
    });
    document.body.appendChild(overlay);
  }

  function wireBookingButtons() {
    document.querySelectorAll("[data-action='book']").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const card = btn.closest("[data-hotel-name]");
        const name = card ? card.getAttribute("data-hotel-name") : "this property";
        openModal("Booking request received", `
          <p><strong>${name}</strong> has been added to a demo booking request.</p>
          <p class="modal-note">This is a disclosed test fixture - no real reservation is made.</p>
        `);
      });
    });

    document.querySelectorAll("[data-action='cta']").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openModal("Offer noted", `
          <p>This demo offer has been noted for follow-up.</p>
          <p class="modal-note">This is a disclosed test fixture - no real offer is redeemed.</p>
        `);
      });
    });
  }

  function wireFilterChips() {
    const bar = document.querySelector(".filter-bar");
    if (!bar) return;
    const chips = Array.from(bar.querySelectorAll(".filter-chip"));
    const cards = Array.from(document.querySelectorAll(".hotel-card"));

    function applyFilter(filter) {
      cards.forEach((card) => {
        const available = card.querySelector(".unavailable") === null;
        const rating = parseFloat(card.querySelector(".rating")?.textContent.replace(/[^\d.]/g, "") || "0");
        const hasPromo = card.querySelector(".promo") !== null;

        let visible = true;
        if (filter === "available") visible = available;
        else if (filter === "rating") visible = rating >= 4;
        else if (filter === "offers") visible = hasPromo;

        card.style.display = visible ? "" : "none";
      });
    }

    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        chips.forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        applyFilter(chip.dataset.filter || "all");
      });
    });
  }

  function wireSort() {
    const select = document.querySelector("[data-sort]");
    const grid = document.querySelector(".hotel-grid");
    if (!select || !grid) return;

    select.addEventListener("change", () => {
      const cards = Array.from(grid.querySelectorAll(".hotel-card"));
      const mode = select.value;
      cards.sort((a, b) => {
        if (mode === "price_asc" || mode === "price_desc") {
          const pa = parseFloat(a.querySelector(".price")?.dataset.price || "999999");
          const pb = parseFloat(b.querySelector(".price")?.dataset.price || "999999");
          return mode === "price_asc" ? pa - pb : pb - pa;
        }
        if (mode === "rating_desc") {
          const ra = parseFloat(a.querySelector(".rating")?.textContent.replace(/[^\d.]/g, "") || "0");
          const rb = parseFloat(b.querySelector(".rating")?.textContent.replace(/[^\d.]/g, "") || "0");
          return rb - ra;
        }
        return 0;
      });
      cards.forEach((card) => grid.appendChild(card));
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireBookingButtons();
    wireFilterChips();
    wireSort();
  });
})();
