// Крупная вращающаяся 3D-Земля (вариант 4b) — SphereGeometry с текстурами
// вместо .blend/.obj/.3ds модели (её сложность Three.js не нужна, см.
// docs/tz/TZ-web.md). Основная сфера — обычный MeshPhongMaterial (карта
// высот + specular по океану), отдельный тонкий слой поверх — City-lights
// на тёмной стороне (простой шейдер: свечение только там, где сфера не
// освещена "солнцем", не полноценный день/ночь blend одним материалом).
import * as THREE from "three";

const TEXTURE_BASE = "/static/textures/";
const ROTATION_SPEED = 0.0009;

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

function showFallback() {
  const canvas = document.getElementById("earth-canvas");
  const fallback = document.getElementById("earth-fallback");
  if (canvas) canvas.hidden = true;
  if (fallback) fallback.hidden = false;
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
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.z = 3.2;

  const textureLoader = new THREE.TextureLoader();
  const colorMap = textureLoader.load(`${TEXTURE_BASE}color.jpg`);
  const nightMap = textureLoader.load(`${TEXTURE_BASE}night.jpg`);
  const bumpMap = textureLoader.load(`${TEXTURE_BASE}bump.jpg`);
  const specMap = textureLoader.load(`${TEXTURE_BASE}spec.png`);
  const cloudsMap = textureLoader.load(`${TEXTURE_BASE}clouds.png`);

  const sunDirection = new THREE.Vector3(-4, 1, 2).normalize();

  const earth = new THREE.Group();

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
  scene.add(new THREE.AmbientLight(0x334466, 0.5));
  const sun = new THREE.DirectionalLight(0xffffff, 1.3);
  sun.position.copy(sunDirection);
  scene.add(sun);

  function resize() {
    const size = Math.max(mount.clientWidth, mount.clientHeight, 300);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(size, size, false);
  }

  window.addEventListener("resize", resize);
  resize();

  function animate() {
    earth.rotation.y += ROTATION_SPEED;
    clouds.rotation.y += ROTATION_SPEED * 0.4;
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}

initEarth();
