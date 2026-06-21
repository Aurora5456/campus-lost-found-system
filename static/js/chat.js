// 私信聊天页：定时轮询新消息并追加，无需手动刷新。
document.addEventListener("DOMContentLoaded", () => {
  const list = document.getElementById("chatList");
  if (!list) {
    return;
  }
  const pollUrl = list.dataset.pollUrl;
  let lastId = Number(list.dataset.lastId || 0);

  function appendMessage(msg) {
    const empty = list.querySelector(".empty-state");
    if (empty) {
      empty.remove();
    }
    const bubble = document.createElement("div");
    bubble.className = "bubble " + (msg.mine ? "mine" : "theirs");
    bubble.dataset.id = msg.id;
    const body = document.createElement("p");
    body.textContent = msg.content;
    const meta = document.createElement("small");
    meta.textContent = msg.sender_name + " · " + msg.created_at;
    bubble.appendChild(body);
    bubble.appendChild(meta);
    list.appendChild(bubble);
  }

  async function poll() {
    try {
      const res = await fetch(pollUrl + "?after=" + lastId, {
        headers: { "X-Requested-With": "fetch" },
      });
      if (!res.ok) {
        return;
      }
      const data = await res.json();
      if (!data.messages || data.messages.length === 0) {
        return;
      }
      const nearBottom =
        window.innerHeight + window.scrollY >= document.body.offsetHeight - 150;
      data.messages.forEach((msg) => {
        appendMessage(msg);
        if (msg.id > lastId) {
          lastId = msg.id;
        }
      });
      if (nearBottom) {
        window.scrollTo(0, document.body.scrollHeight);
      }
    } catch (err) {
      /* 网络抖动忽略，下次轮询再试 */
    }
  }

  setInterval(poll, 4000);
});
