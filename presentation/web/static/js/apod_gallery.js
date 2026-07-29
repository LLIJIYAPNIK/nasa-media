// Pinterest-сетка APOD с бесконечной подгрузкой (docs/tz/TZ-web-apod.md).
// Отдельный модуль, не правка modal.js: тот заточен под ленивую подгрузку
// по сети для 4 карточек статистики, здесь данные тайла уже в памяти к
// моменту клика — второй поход на сервер не нужен.

// Тот же однострочный экранирующий хелпер, что в modal.js — выносить в общий
// utils-модуль ради одной функции преждевременно (см. CLAUDE.md, «не
// усложнять раньше времени»).
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function tileFromDataset(button) {
  return {
    date: button.dataset.date,
    title: button.querySelector(".apod-tile-image")?.alt ?? "",
    image_url: button.querySelector(".apod-tile-image")?.src ?? "",
    hdurl: button.dataset.hdurl || null,
    copyright: button.querySelector(".apod-tile-copyright")?.textContent.replace(/^©\s*/, "") || null,
    explanation: button.querySelector(".apod-tile-excerpt")?.textContent ?? "",
  };
}

function renderTile(item) {
  const copyright = item.copyright
    ? `<span class="apod-tile-copyright">© ${escapeHtml(item.copyright)}</span>`
    : "";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "apod-tile";
  button.dataset.date = item.date;
  button.dataset.hdurl = item.hdurl || "";
  button.innerHTML = `
    <img class="apod-tile-image" src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.title)}" loading="lazy">
    <span class="apod-tile-overlay">
      ${copyright}
      <span class="apod-tile-date">${escapeHtml(item.date)}</span>
      <span class="apod-tile-excerpt">${escapeHtml(item.explanation)}</span>
      <span class="btn btn-glass apod-tile-more">Читать больше</span>
    </span>
  `;
  return button;
}

function renderModalBody(item) {
  const copyright = item.copyright ? `<p>© ${escapeHtml(item.copyright)}</p>` : "";
  const imageUrl = item.hdurl || item.image_url;
  return `
    <h2 id="apod-detail-modal-title">${escapeHtml(item.title)}</h2>
    <p class="detail-modal-notice">${escapeHtml(item.date)}</p>
    <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(item.title)}">
    <p>${escapeHtml(item.explanation)}</p>
    ${copyright}
  `;
}

function initApodGallery() {
  const grid = document.getElementById("apod-grid");
  const sentinel = document.getElementById("apod-grid-sentinel");
  const dialog = document.getElementById("apod-detail-modal");
  const body = document.getElementById("apod-detail-modal-body");
  if (!grid || !sentinel || !dialog || !body) {
    return;
  }

  const limit = grid.dataset.limit;
  let nextCursor = grid.dataset.nextCursor || null;
  const tiles = new Map();

  function openModal(item) {
    body.innerHTML = renderModalBody(item);
    dialog.showModal();
  }

  function attachTileHandler(button, item) {
    tiles.set(item.date, item);
    button.addEventListener("click", () => openModal(tiles.get(button.dataset.date)));
  }

  grid.querySelectorAll(".apod-tile").forEach((button) => {
    attachTileHandler(button, tileFromDataset(button));
  });

  dialog.addEventListener("click", (event) => {
    const rect = dialog.getBoundingClientRect();
    const inside =
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom &&
      event.clientX >= rect.left &&
      event.clientX <= rect.right;
    if (!inside) {
      dialog.close();
    }
  });

  if (!nextCursor) {
    return;
  }

  const observer = new IntersectionObserver(async (entries) => {
    if (!entries.some((entry) => entry.isIntersecting) || !nextCursor) {
      return;
    }
    observer.unobserve(sentinel);

    const response = await fetch(`/api/apod/entries?before=${nextCursor}&limit=${limit}`);
    const page = await response.json();

    for (const item of page.items) {
      const button = renderTile(item);
      grid.appendChild(button);
      attachTileHandler(button, item);
    }

    nextCursor = page.next_cursor;
    if (!nextCursor) {
      observer.disconnect();
      return;
    }
    observer.observe(sentinel);
  });

  observer.observe(sentinel);
}

initApodGallery();
