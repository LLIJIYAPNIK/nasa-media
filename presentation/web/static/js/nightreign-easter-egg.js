// Пасхалка: 7 кликов по логотипу в нав-рейле (.nav-logo) в течение 3 секунд
// переключает body.sky--nightreign — отсылка к Elden Ring Nightreign, только
// настроение/палитра (см. docs/tz/web-homepage-fixes/TZ-web-homepage-fixes.md,
// п. 7). Повторный клик по логотипу выключает эффект. Состояние не
// сохраняется между визитами — просто класс на <body>.
//
// Логотип — обычная ссылка на "/", поэтому обычный клик должен продолжать
// туда вести. Навигация откладывается на NAVIGATE_DELAY_MS и отменяется,
// если за это время пришёл следующий клик — иначе браузер перешёл бы по
// ссылке уже после первого клика, не дав досчитать серию до 7.
const CLICKS_REQUIRED = 7;
const CLICK_WINDOW_MS = 3000;
const NAVIGATE_DELAY_MS = 900;

function initNightreignEasterEgg() {
  const logo = document.querySelector(".nav-logo");
  if (!logo) {
    return;
  }

  let clickTimestamps = [];
  let navigateTimer = null;

  logo.addEventListener("click", (event) => {
    event.preventDefault();
    window.clearTimeout(navigateTimer);

    if (document.body.classList.contains("sky--nightreign")) {
      document.body.classList.remove("sky--nightreign");
      clickTimestamps = [];
      return;
    }

    const now = Date.now();
    clickTimestamps.push(now);
    clickTimestamps = clickTimestamps.filter((timestamp) => now - timestamp <= CLICK_WINDOW_MS);

    if (clickTimestamps.length >= CLICKS_REQUIRED) {
      document.body.classList.add("sky--nightreign");
      clickTimestamps = [];
      return;
    }

    navigateTimer = window.setTimeout(() => {
      window.location.href = logo.href;
    }, NAVIGATE_DELAY_MS);
  });
}

initNightreignEasterEgg();
