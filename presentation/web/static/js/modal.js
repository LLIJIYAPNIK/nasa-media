// Модалка по клику на карточку статистики — нативный <dialog>, ленивая
// подгрузка через /api/homepage/details/{kind}, кэш на время жизни страницы
// (см. docs/tz/TZ-web.md, «Модалка по клику»).
const KIND_TITLES = {
  apod: "Картинка дня",
  asteroid: "Астероид сегодня",
  "space-weather": "Космическая погода",
  "earth-event": "Событие Земли",
};

// Дистанция пролёта доступна у NASA сразу в 4 единицах — переключатель
// вместо четырёх плоских строк (см. docs/tz/TZ-asteroid-modal-details.md).
// "До Солнца" — тот же а.е., просто astronomical * 100 и с другой подписью.
const DISTANCE_UNITS = [
  {
    key: "lunar",
    icon: "🌙",
    chipLabel: "Луны",
    valueLabel: "лунных расстояний",
    decimals: 1,
    getValue: (detail) => detail.asteroid_miss_distance_lunar,
  },
  {
    key: "km",
    icon: "📏",
    chipLabel: "км",
    valueLabel: "километров",
    decimals: 0,
    getValue: (detail) => detail.asteroid_miss_distance_km,
  },
  {
    key: "sun",
    icon: "☀️",
    chipLabel: "До Солнца",
    valueLabel: "% пути отсюда до Солнца",
    decimals: 2,
    getValue: (detail) => detail.asteroid_miss_distance_au * 100,
  },
  {
    key: "miles",
    icon: "🛣",
    chipLabel: "Мили",
    valueLabel: "миль",
    decimals: 0,
    getValue: (detail) => detail.asteroid_miss_distance_miles,
  },
];

const DEFAULT_DISTANCE_UNIT_KEY = "lunar";
const COUNT_UP_DURATION_MS = 350;

const detailCache = new Map();

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function animateUnitValue(element, from, to, decimals) {
  const start = performance.now();
  function step(now) {
    const progress = Math.min((now - start) / COUNT_UP_DURATION_MS, 1);
    element.textContent = (from + (to - from) * progress).toFixed(decimals);
    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }
  requestAnimationFrame(step);
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
  const defaultUnit = DISTANCE_UNITS.find((unit) => unit.key === DEFAULT_DISTANCE_UNIT_KEY);
  const defaultValue = defaultUnit.getValue(detail);
  const chips = DISTANCE_UNITS.map(
    (unit) => `
      <button type="button" class="unit-chip${unit.key === DEFAULT_DISTANCE_UNIT_KEY ? " unit-chip--active" : ""}"
        data-unit="${unit.key}">${unit.icon} ${escapeHtml(unit.chipLabel)}</button>
    `
  ).join("");
  const hazardPill = detail.asteroid_is_hazardous
    ? `<span class="hazard-pill hazard-pill--danger">Потенциально опасен</span>`
    : `<span class="hazard-pill hazard-pill--safe">Не опасен</span>`;
  const sentryCallout = detail.asteroid_is_sentry_object
    ? `<div class="sentry-callout">🛰 Находится под наблюдением <strong>JPL Sentry</strong> —
        потенциальные сближения отслеживаются на десятилетия вперёд.</div>`
    : "";

  const html = `
    <h2 id="detail-modal-title">${escapeHtml(detail.asteroid_name)}</h2>
    <dl>
      <dt>Диаметр</dt>
      <dd>${Math.round(detail.asteroid_diameter_min_m)}–${Math.round(detail.asteroid_diameter_max_m)} м
        (${escapeHtml(detail.asteroid_size_comparison)})</dd>
      <dt>Скорость</dt>
      <dd>${detail.asteroid_velocity_km_s.toFixed(1)} км/с —
        ${escapeHtml(detail.asteroid_speed_comparison)}</dd>
      <dt>Когда пролетит</dt>
      <dd>${escapeHtml(new Date(detail.asteroid_close_approach_time).toLocaleString("ru-RU"))}</dd>
    </dl>
    <p class="unit-value" id="asteroid-distance-value">${defaultValue.toFixed(defaultUnit.decimals)}</p>
    <p class="unit-value-label" id="asteroid-distance-label">${escapeHtml(defaultUnit.valueLabel)}</p>
    <div class="unit-toggle">${chips}</div>
    <p>${hazardPill}</p>
    ${sentryCallout}
    <a class="jpl-link" href="${escapeHtml(detail.asteroid_jpl_url)}" target="_blank" rel="noopener">Подробнее на JPL →</a>
  `;

  function afterRender(body) {
    const valueEl = body.querySelector("#asteroid-distance-value");
    const labelEl = body.querySelector("#asteroid-distance-label");
    let activeUnit = defaultUnit;
    let currentValue = defaultValue;

    body.querySelectorAll(".unit-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const unit = DISTANCE_UNITS.find((candidate) => candidate.key === chip.dataset.unit);
        if (!unit || unit === activeUnit) {
          return;
        }
        body.querySelectorAll(".unit-chip").forEach((candidate) => candidate.classList.remove("unit-chip--active"));
        chip.classList.add("unit-chip--active");

        const newValue = unit.getValue(detail);
        animateUnitValue(valueEl, currentValue, newValue, unit.decimals);
        labelEl.textContent = unit.valueLabel;

        activeUnit = unit;
        currentValue = newValue;
      });
    });
  }

  return { html, afterRender };
}

function renderSpaceWeather(detail) {
  const events = detail.space_weather_events ?? [];
  const list = events
    .map(
      (event) => `
        <li>
          <span class="event-list-label">${escapeHtml(event.label)}</span>
          <span class="event-list-time">${escapeHtml(new Date(event.issued_at).toLocaleString("ru-RU"))}</span>
        </li>
      `
    )
    .join("");
  const summaryTime = detail.space_weather_summary_issued_at
    ? ` · ${escapeHtml(new Date(detail.space_weather_summary_issued_at).toLocaleString("ru-RU"))}`
    : "";

  return `
    <h2 id="detail-modal-title">${escapeHtml(KIND_TITLES["space-weather"])}</h2>
    <ul class="detail-modal-event-list">${list}</ul>
    <p class="detail-modal-summary">${escapeHtml(detail.space_weather_summary_label)}${summaryTime}</p>
  `;
}

function renderEarthEvent(detail) {
  const categories = detail.earth_event_categories && detail.earth_event_categories.length
    ? detail.earth_event_categories
    : [detail.earth_event_category].filter(Boolean);
  const pills = categories
    .map((category) => `<a class="event-pill" href="/earth-events?category=${encodeURIComponent(category)}">${escapeHtml(category)}</a>`)
    .join("");

  const status = detail.earth_event_closed_at
    ? `Завершено · ${escapeHtml(new Date(detail.earth_event_closed_at).toLocaleDateString("ru-RU"))}`
    : "Активно";

  const description = detail.earth_event_description
    ? `<p>${escapeHtml(detail.earth_event_description)}</p>`
    : `<p class="detail-modal-notice">Описание отсутствует.</p>`;

  const map = detail.earth_event_map_url
    ? `
      <img src="${escapeHtml(detail.earth_event_map_url)}" alt="Карта: ${escapeHtml(detail.earth_event_title)}">
      <p class="event-map-credit">© OpenStreetMap contributors</p>
    `
    : "";

  const magnitude = detail.earth_event_magnitude_value != null
    ? `
      <dl class="event-magnitude">
        <dt>Магнитуда</dt>
        <dd>${detail.earth_event_magnitude_value} ${escapeHtml(detail.earth_event_magnitude_unit ?? "")}${
          detail.earth_event_magnitude_description ? " · " + escapeHtml(detail.earth_event_magnitude_description) : ""
        }</dd>
      </dl>
    `
    : "";

  const sources = detail.earth_event_sources ?? [];
  const sourcesList = sources.length
    ? `
      <h3>Источники</h3>
      <ul class="event-sources">
        ${sources
          .map(
            (source) =>
              `<li><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.label || source.url)}</a></li>`
          )
          .join("")}
      </ul>
    `
    : "";

  const link = detail.earth_event_link
    ? `<p><a href="${escapeHtml(detail.earth_event_link)}" target="_blank" rel="noopener noreferrer">Открыть на EONET →</a></p>`
    : "";

  return `
    <div class="event-pills">${pills}</div>
    <h2 id="detail-modal-title">${escapeHtml(detail.earth_event_title)}</h2>
    <p class="event-status">${status} · ${escapeHtml(new Date(detail.earth_event_date).toLocaleDateString("ru-RU"))}</p>
    ${description}
    ${map}
    ${magnitude}
    ${sourcesList}
    ${link}
  `;
}

const RENDERERS = {
  apod: (detail) => ({ html: renderApod(detail) }),
  asteroid: renderAsteroid,
  "space-weather": (detail) => ({ html: renderSpaceWeather(detail) }),
  "earth-event": (detail) => ({ html: renderEarthEvent(detail) }),
};

function renderDetail(detail) {
  if (!detail.available) {
    return { html: renderUnavailable(detail) };
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
        const rendered = renderDetail(detail);
        body.innerHTML = rendered.html;
        rendered.afterRender?.(body);
      } catch {
        body.innerHTML = "<p>Не удалось загрузить данные — попробуйте ещё раз.</p>";
      }
    });
  });
}

initModal();
