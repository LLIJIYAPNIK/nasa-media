// Обновляет 4 карточки ежедневной статистики раз в 60 секунд — бейдж
// "обновляются каждую минуту" не декорация (см. docs/tz/TZ-web.md).
const POLL_INTERVAL_MS = 60_000;

function renderSnapshot(snapshot) {
  const apodField = document.querySelector('[data-field="apod"]');
  if (apodField) {
    apodField.textContent = "Картинка дня";
  }

  const asteroidField = document.querySelector('[data-field="asteroid"]');
  if (asteroidField) {
    asteroidField.textContent = snapshot.asteroid_name
      ? `${snapshot.asteroid_name} · ${snapshot.asteroid_miss_distance_lunar.toFixed(1)} л.р.`
      : "Нет данных";
  }

  const spaceWeatherField = document.querySelector('[data-field="space-weather"]');
  if (spaceWeatherField) {
    spaceWeatherField.textContent = snapshot.space_weather_label || "Спокойно";
  }

  const earthEventField = document.querySelector('[data-field="earth-event"]');
  if (earthEventField) {
    earthEventField.textContent = snapshot.earth_event_title || "Нет данных";
  }
}

async function pollSnapshot() {
  const statsCard = document.getElementById("stats");
  if (!statsCard) {
    return;
  }
  const url = statsCard.dataset.snapshotUrl;
  try {
    const response = await fetch(url);
    if (!response.ok) {
      return;
    }
    renderSnapshot(await response.json());
  } catch {
    // Сеть недоступна — оставляем последний отрисованный снапшот как есть.
  }
}

setInterval(pollSnapshot, POLL_INTERVAL_MS);
