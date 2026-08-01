(() => {
  if (window.lucide) {
    window.lucide.createIcons();
  }

  const sidebar = document.getElementById("primary-navigation");
  const sidebarToggle = document.querySelector(".sidebar-toggle");
  const sidebarBackdrop = document.querySelector(".sidebar-backdrop");

  const closeSidebar = () => {
    // Reset all three pieces of mobile navigation state together.
    if (!sidebar || !sidebarToggle || !sidebarBackdrop) return;
    sidebar.classList.remove("is-open");
    sidebarBackdrop.classList.remove("is-visible");
    sidebarToggle.setAttribute("aria-expanded", "false");
    sidebarToggle.setAttribute("aria-label", "Open navigation menu");
  };

  if (sidebar && sidebarToggle && sidebarBackdrop) {
    // The same close helper is used for the backdrop, links, and Escape key.
    sidebarToggle.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("is-open");
      sidebarBackdrop.classList.toggle("is-visible", isOpen);
      sidebarToggle.setAttribute("aria-expanded", String(isOpen));
      sidebarToggle.setAttribute(
        "aria-label",
        isOpen ? "Close navigation menu" : "Open navigation menu"
      );
    });
    sidebarBackdrop.addEventListener("click", closeSidebar);
    sidebar.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", closeSidebar);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSidebar();
    });
  }

  // Keep destructive-action confirmation reusable and out of template markup.
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-confirm-message]");
    if (!form) return;
    if (!window.confirm(form.dataset.confirmMessage)) {
      event.preventDefault();
    }
  });
})();
