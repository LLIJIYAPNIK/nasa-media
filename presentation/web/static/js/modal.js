// Модалка по клику на карточку статистики — нативный <dialog>, ленивая
// подгрузка через /api/homepage/details/{kind}, кэш на время жизни страницы
// (см. docs/tz/TZ-web.md, «Модалка по клику»).
const KIND_TITLES = {
  apod: "Картинка дня",
  asteroid: "Астероид сегодня",
  "space-weather": "Космическая погода",
  "earth-event": "Событие Земли",
};

const detailCache = new Map();

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderUnavailable(detail) {
  return `<h2 id="detail-modal-title">${escapeHtml(KIND_TITLES[detail.kind])}</h2><p>${escapeHtml(detail.message)}</p>`;
}

function renderApod(detail) {
  const notice = detail.message ? `<p class="detail-modal-notice">${escapeHtml(detail.message)}</p>` : "";
  const copyright = detail.apod_copyright ? `<p>© ${escapeHtml(detail.apod_copyright)}</p>` : "";
  return `
    <h2 id="detail-modal-title">${escapeHtml(detail.apod_title)}</h2>
    ${notice}
    <img src="${escapeHtml(detail.apod_image_url)}" alt="${escapeHtml(detail.apod_title)}">
    <p>${escapeHtml(detail.apod_description)}</p>
    ${copyright}
  `;
}

function renderAsteroid(detail) {
  return `
    <h2 id="detail-modal-title">${escapeHtml(detail.asteroid_name)}</h2>
    <dl>
      <dt>Диаметр</dt>
      <dd>${Math.round(detail.asteroid_diameter_min_m)}–${Math.round(detail.asteroid_diameter_max_m)} м
        (${escapeHtml(detail.asteroid_size_comparison)})</dd>
      <dt>Пролёт</dt>
      <dd>${detail.asteroid_miss_distance_lunar.toFixed(1)} лунных расстояний</dd>
      <dt>Опасность</dt>
      <dd>${detail.asteroid_is_hazardous ? "Потенциально опасен" : "Не опасен"}</dd>
    </dl>
  `;
}

function renderSpaceWeather(detail) {
  return `
    <h2 id="detail-modal-title">${escapeHtml(detail.space_weather_label)}</h2>
    <dl>
      <dt>Тип</dt>
      <dd>${escapeHtml(detail.space_weather_type)}</dd>
      <dt>Зафиксировано</dt>
      <dd>${escapeHtml(new Date(detail.space_weather_issued_at).toLocaleString("ru-RU"))}</dd>
    </dl>
  `;
}

function renderEarthEvent(detail) {
  return `
    <h2 id="detail-modal-title">${escapeHtml(detail.earth_event_title)}</h2>
    <dl>
      <dt>Категория</dt>
      <dd>${escapeHtml(detail.earth_event_category)}</dd>
      <dt>Дата</dt>
      <dd>${escapeHtml(new Date(detail.earth_event_date).toLocaleDateString("ru-RU"))}</dd>
    </dl>
  `;
}

const RENDERERS = {
  apod: renderApod,
  asteroid: renderAsteroid,
  "space-weather": renderSpaceWeather,
  "earth-event": renderEarthEvent,
};

function renderDetail(detail) {
  if (!detail.available) {
    return renderUnavailable(detail);
  }
  return RENDERERS[detail.kind](detail);
}

async function loadDetail(kind) {
  if (detailCache.has(kind)) {
    return detailCache.get(kind);
  }
  const response = await fetch(`/api/homepage/details/${kind}`);
  const detail = await response.json();
  detailCache.set(kind, detail);
  return detail;
}

function initModal() {
  const dialog = document.getElementById("detail-modal");
  const body = document.getElementById("detail-modal-body");
  if (!dialog || !body) {
    return;
  }

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

  document.querySelectorAll("[data-kind]").forEach((button) => {
    button.addEventListener("click", async () => {
      const kind = button.dataset.kind;
      body.innerHTML = "<p>Загрузка…</p>";
      dialog.showModal();
      try {
        const detail = await loadDetail(kind);
        body.innerHTML = renderDetail(detail);
      } catch {
        body.innerHTML = "<p>Не удалось загрузить данные — попробуйте ещё раз.</p>";
      }
    });
  });
}

initModal();
