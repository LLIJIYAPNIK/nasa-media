// Крупная вращающаяся 3D-Земля (вариант 4b) — SphereGeometry с текстурами
// вместо .blend/.obj/.3ds модели (её сложность Three.js не нужна, см.
// docs/tz/TZ-web.md). Основная сфера — обычный MeshPhongMaterial (карта
// высот + specular по океану), отдельный тонкий слой поверх — City-lights
// на тёмной стороне (простой шейдер: свечение только там, где сфера не
// освещена "солнцем", не полноценный день/ночь blend одним материалом).
import * as THREE from "three";

const TEXTURE_BASE = "/static/textures/";
const SUBSOLAR_REFRESH_MS = 5 * 60 * 1000;
const POINTER_TILT_MAX = 0.22;
const POINTER_LERP = 0.04;
const DESKTOP_BREAKPOINT_PX = 768;
// На больших экранах Земля должна выглядеть примерно вдвое крупнее и
// смещённой вправо настолько, чтобы целый шар не помещался в кадр (см.
// docs/tz/web-homepage-fixes-round4). На мобильных (тот же брейкпоинт, что
// и .earth-mount в earth.css) — прежний масштаб/центровка, там Земля и так
// приглушена и не должна расти вместе с десктопом.
const CAMERA_Z_DESKTOP = 1.8;
const CAMERA_Z_MOBILE = 3.2;
const EARTH_OFFSET_X_DESKTOP = 0.6;
const EARTH_OFFSET_X_MOBILE = 0;
// Подобрано визуально перебором 12 углов через 30° (docs/tz/
// web-homepage-fixes-round5) — вид на Южную/Юго-Восточную Азию (Индия,
// Индокитай, Малайский архипелаг) даёт заметно больше городских огней в
// кадре, чем соседние варианты (океан Тихого/Индийского, тёмная Африка).
const EARTH_ROTATION_Y = (150 * Math.PI) / 180;

function isDesktopViewport() {
  return window.innerWidth > DESKTOP_BREAKPOINT_PX;
}

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

function prefersFinePointer() {
  return window.matchMedia?.("(pointer: fine)").matches ?? false;
}

function showFallback() {
  const canvas = document.getElementById("earth-canvas");
  const fallback = document.getElementById("earth-fallback");
  if (canvas) canvas.hidden = true;
  if (fallback) fallback.hidden = false;
}

// Приближённое направление на Солнце по текущему UTC-времени (склонение по
// дню года + часовой угол по UTC-часу, стандартные упрощённые формулы
// положения Солнца — без библиотек астрономии). Точность —
// ориентировочная, не астрономическая: тот же принцип, что уже применяется
// для фазы Луны в domain/users/cosmic_facts.py (см. TZ-birthday-cosmic-facts.md,
// TZ-web-homepage-fixes.md, п. 2) — для декоративного дня/ночи на Земле
// точность в пределах часа-двух избыточна.
function getSubsolarDirection(date) {
  const dayOfYear = Math.floor(
    (Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) -
      Date.UTC(date.getUTCFullYear(), 0, 0)) /
      86400000
  );
  const declination = 23.44 * (Math.PI / 180) * Math.sin(((2 * Math.PI) / 365) * (dayOfYear - 81));

  const utcHours = date.getUTCHours() + date.getUTCMinutes() / 60;
  const hourAngle = ((utcHours - 12) / 24) * 2 * Math.PI;

  const x = Math.cos(declination) * Math.sin(hourAngle);
  const y = Math.sin(declination);
  const z = Math.cos(declination) * Math.cos(hourAngle);

  return new THREE.Vector3(x, y, z).normalize();
}

const NIGHT_LIGHTS_VERTEX_SHADER = `
  varying vec2 vUv;
  varying vec3 vWorldNormal;
  void main() {
    vUv = uv;
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const NIGHT_LIGHTS_FRAGMENT_SHADER = `
  uniform sampler2D nightTexture;
  uniform vec3 sunDirection;
  varying vec2 vUv;
  varying vec3 vWorldNormal;
  void main() {
    float lit = dot(normalize(vWorldNormal), normalize(sunDirection));
    float darkness = smoothstep(0.15, -0.05, lit);
    vec3 night = texture2D(nightTexture, vUv).rgb;
    float glow = (night.r + night.g + night.b) / 3.0;
    gl_FragColor = vec4(night, darkness * glow);
  }
`;

function initEarth() {
  const mount = document.getElementById("earth-mount");
  const canvas = document.getElementById("earth-canvas");
  if (!mount || !canvas) {
    return;
  }

  if (prefersReducedMotion()) {
    showFallback();
    return;
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch {
    showFallback();
    return;
  }

  const scene = new THREE.Scene();
  // z/x ниже — временные значения до первого resize() (см. ниже), который
  // выставляет их по реальной ширине viewport и пересчитывает при переходе
  // через мобильный брейкпоинт.
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.z = CAMERA_Z_MOBILE;

  const textureLoader = new THREE.TextureLoader();
  const colorMap = textureLoader.load(`${TEXTURE_BASE}color.jpg`);
  const nightMap = textureLoader.load(`${TEXTURE_BASE}night.jpg`);
  const bumpMap = textureLoader.load(`${TEXTURE_BASE}bump.jpg`);
  const specMap = textureLoader.load(`${TEXTURE_BASE}spec.png`);
  const cloudsMap = textureLoader.load(`${TEXTURE_BASE}clouds.png`);

  const sunDirection = getSubsolarDirection(new Date());

  const earth = new THREE.Group();
  // Фиксированный поворот на плотный по городским огням регион (см.
  // EARTH_ROTATION_Y выше) вместо прежнего расчёта от реального положения
  // Солнца (текущая полуночная долгота к камере) — астрономически честно,
  // но полночная долгота половину суток приходится на Тихий океан, и Земля
  // показывала просто воду (см. docs/tz/web-homepage-fixes-round5). День/
  // ночь на самой сфере (терминатор, свечение городов ниже) по-прежнему
  // считается от настоящего sunDirection и не зависит от поворота — вид
  // остаётся физически осмысленным, камера просто больше не гонится за
  // полночью по всему земному шару.
  earth.rotation.y = EARTH_ROTATION_Y;

  const globe = new THREE.Mesh(
    new THREE.SphereGeometry(1, 64, 64),
    new THREE.MeshPhongMaterial({
      map: colorMap,
      bumpMap,
      bumpScale: 0.015,
      specularMap: specMap,
      specular: new THREE.Color(0x333333),
      shininess: 12,
    })
  );
  earth.add(globe);

  const nightLights = new THREE.Mesh(
    new THREE.SphereGeometry(1.001, 64, 64),
    new THREE.ShaderMaterial({
      uniforms: {
        nightTexture: { value: nightMap },
        sunDirection: { value: sunDirection },
      },
      vertexShader: NIGHT_LIGHTS_VERTEX_SHADER,
      fragmentShader: NIGHT_LIGHTS_FRAGMENT_SHADER,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
  );
  earth.add(nightLights);

  const clouds = new THREE.Mesh(
    new THREE.SphereGeometry(1.02, 64, 64),
    new THREE.MeshLambertMaterial({ map: cloudsMap, transparent: true, opacity: 0.35, depthWrite: false })
  );
  earth.add(clouds);

  scene.add(earth);
  // Яркость поднята (docs/tz/web-homepage-fixes-round4) — на фоне
  // насыщенного вихря round 3 тёмная (ночная) сторона Земли читалась почти
  // чёрным пятном рядом со светлым небом. AmbientLight светлее заливает
  // тени, не отменяя сам эффект ночной стороны (свечение городов — отдельный
  // ShaderMaterial выше, от сцены не зависит).
  scene.add(new THREE.AmbientLight(0x5a72a8, 1.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.9);
  sun.position.copy(sunDirection);
  scene.add(sun);

  function resize() {
    const width = mount.clientWidth;
    const height = mount.clientHeight;
    if (width === 0 || height === 0) {
      return;
    }
    camera.aspect = width / height;
    camera.position.z = isDesktopViewport() ? CAMERA_Z_DESKTOP : CAMERA_Z_MOBILE;
    earth.position.x = isDesktopViewport() ? EARTH_OFFSET_X_DESKTOP : EARTH_OFFSET_X_MOBILE;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);
  }

  new ResizeObserver(resize).observe(mount);
  resize();

  // Направление на Солнце меняется медленно — пересчитывать раз в несколько
  // минут, не на каждый кадр.
  window.setInterval(() => {
    sunDirection.copy(getSubsolarDirection(new Date()));
    sun.position.copy(sunDirection);
  }, SUBSOLAR_REFRESH_MS);

  // Земля статична — единственное движение модели это лёгкий доворот за
  // курсором на устройствах с мышью (pointer: fine), по аналогии с
  // курсор-реактивным spotlight в hero на a-kulebyakin.ru. На тач-устройствах
  // модель остаётся полностью неподвижной, без автономного дрейфа.
  let targetTiltX = 0;
  let targetTiltY = 0;
  let tiltX = 0;
  let tiltY = 0;

  if (prefersFinePointer()) {
    window.addEventListener("pointermove", (event) => {
      const normalizedX = (event.clientX / window.innerWidth) * 2 - 1;
      const normalizedY = (event.clientY / window.innerHeight) * 2 - 1;
      targetTiltY = normalizedX * POINTER_TILT_MAX;
      targetTiltX = normalizedY * POINTER_TILT_MAX;
    });
  }

  function animate() {
    tiltX += (targetTiltX - tiltX) * POINTER_LERP;
    tiltY += (targetTiltY - tiltY) * POINTER_LERP;
    earth.rotation.x = tiltX;
    earth.rotation.z = -tiltY * 0.15;

    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}

initEarth();
