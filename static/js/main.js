document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm") || "确认执行该操作吗？";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll("input[data-check-all]").forEach((master) => {
    const name = master.getAttribute("data-check-all");
    master.addEventListener("change", () => {
      document
        .querySelectorAll(`input[type="checkbox"][name="${name}"]`)
        .forEach((box) => {
          box.checked = master.checked;
        });
    });
  });
});
