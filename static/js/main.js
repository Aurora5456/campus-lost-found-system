document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm") || "确认执行该操作吗？";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-announce-id]").forEach((banner) => {
    const id = banner.getAttribute("data-announce-id");
    const storeKey = "dismissedAnnouncement";
    if (localStorage.getItem(storeKey) === id) {
      banner.style.display = "none";
      return;
    }
    const closeBtn = banner.querySelector(".announce-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        banner.style.display = "none";
        localStorage.setItem(storeKey, id);
      });
    }
  });

  const unreadLink = document.querySelector(".nav-badge-link[data-unread-url]");
  if (unreadLink) {
    const refreshUnread = async () => {
      try {
        const res = await fetch(unreadLink.dataset.unreadUrl);
        if (!res.ok) {
          return;
        }
        const data = await res.json();
        const count = data.unread || 0;
        let badge = unreadLink.querySelector(".nav-badge");
        if (count > 0) {
          if (!badge) {
            badge = document.createElement("span");
            badge.className = "nav-badge";
            unreadLink.appendChild(badge);
          }
          badge.textContent = count;
          badge.style.display = "";
        } else if (badge) {
          badge.style.display = "none";
        }
      } catch (err) {
        /* 忽略网络抖动 */
      }
    };
    setInterval(refreshUnread, 10000);
  }

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
