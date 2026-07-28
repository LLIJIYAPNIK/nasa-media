// Процедурное звёздное поле на <canvas class="stars"> — заменяет 12
// захардкоженных radial-gradient (см. docs/tz/web-homepage-fixes/
// TZ-web-homepage-fixes.md, п. 4). Обычный 2D-контекст, не WebGL — дёшево
// даже для ~700 точек (round 6, docs/tz/web-homepage-fixes-round6 — автору
// показалось мало), перерисовывается по ResizeObserver (дебаунс).
const STAR_COUNT_FAR = 460;
const STAR_COUNT_NEAR = 220;
const TWINKLE_EVERY = 8;
const RESIZE_DEBOUNCE_MS = 200;

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

function randomStars(count, { minRadius, maxRadius, minAlpha, maxAlpha }) {
  const stars = [];
  for (let i = 0; i < count; i += 1) {
    stars.push({
      x: Math.random(),
      y: Math.random(),
      radius: minRadius + Math.random() * (maxRadius - minRadius),
      alpha: minAlpha + Math.random() * (maxAlpha - minAlpha),
      twinkle: i % TWINKLE_EVERY === 0,
      delay: Math.random() * 4,
    });
  }
  return stars;
}

function drawStars(ctx, width, height, stars, reducedMotion, elapsedSeconds) {
  ctx.clearRect(0, 0, width, height);
  for (const star of stars) {
    let alpha = star.alpha;
    if (star.twinkle && !reducedMotion) {
      alpha *= 0.55 + 0.45 * Math.sin((elapsedSeconds + star.delay) * 1.6);
    }
    ctx.beginPath();
    ctx.fillStyle = `rgba(255, 255, 255, ${Math.max(0, alpha).toFixed(3)})`;
    ctx.arc(star.x * width, star.y * height, star.radius, 0, Math.PI * 2);
    ctx.fill();
  }
}

function initStarfield() {
  const canvas = document.querySelector("canvas.stars");
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const farStars = randomStars(STAR_COUNT_FAR, { minRadius: 0.5, maxRadius: 1, minAlpha: 0.25, maxAlpha: 0.55 });
  const nearStars = randomStars(STAR_COUNT_NEAR, { minRadius: 1, maxRadius: 2, minAlpha: 0.55, maxAlpha: 0.95 });
  const stars = [...farStars, ...nearStars];
  const reducedMotion = prefersReducedMotion();

  let width = 0;
  let height = 0;

  function render() {
    const elapsedSeconds = performance.now() / 1000;
    drawStars(ctx, width, height, stars, reducedMotion, elapsedSeconds);
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    render();
  }

  let resizeTimer = null;
  new ResizeObserver(() => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(resize, RESIZE_DEBOUNCE_MS);
  }).observe(document.body);

  resize();

  if (!reducedMotion) {
    (function animate() {
      render();
      requestAnimationFrame(animate);
    })();
  }
}

initStarfield();
