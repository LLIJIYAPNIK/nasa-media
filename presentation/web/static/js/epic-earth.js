// Полноэкранная 3D-модель Земли из настоящего кадра EPIC — см.
// docs/tz/TZ-web-epic.md. В отличие от декоративной Земли на главной
// (earth.js, статичные текстуры Maps/*), здесь один реальный кадр
// проецируется на видимое (сфотографированное EPIC) полушарие через
// кастомный шейдер; обратная сторона — сплошной тёмный цвет, потому что
// EPIC её физически не снимал (это не приближение "для красоты", а
// честное отражение того, что реально есть в данных).
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const MIN_DISTANCE = 1.4;
const MAX_DISTANCE = 6;
const INITIAL_DISTANCE = 2.2;
// Плавное затухание в тёмный цвет у терминатора (границы видимого EPIC
// полушария) вместо резкого края — cos(угла) от referenceAxis, где
// начинается/заканчивается переход.
const EDGE_FADE_START = 0.02;
const EDGE_FADE_END = 0.25;
const FAR_SIDE_COLOR = new THREE.Color(0x030509);

// Сфера никогда не вращается и не масштабируется (identity model matrix,
// см. initEpicEarth — крутится только камера через OrbitControls), поэтому
// object-space нормаль совпадает с world-space: передаём "normal" как есть,
// без normalMatrix, и сравниваем с referenceAxis (тоже в world-space) без
// дополнительных преобразований.
const SPHERE_VERTEX_SHADER = `
  varying vec3 vNormal;
  void main() {
    vNormal = normal;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const SPHERE_FRAGMENT_SHADER = `
  uniform sampler2D frameTexture;
  uniform vec3 referenceAxis;
  uniform vec3 tangentU;
  uniform vec3 tangentV;
  uniform vec3 farSideColor;
  varying vec3 vNormal;

  void main() {
    vec3 normal = normalize(vNormal);
    float visibility = dot(normal, referenceAxis);

    if (visibility < ${EDGE_FADE_START.toFixed(3)}) {
      gl_FragColor = vec4(farSideColor, 1.0);
      return;
    }

    // Приближённая ортографическая проекция: координаты кадра — это
    // компоненты нормали вдоль касательных к референс-оси (не точная
    // картографическая репроекция с учётом кривизны у края диска, см.
    // "Решения" в TZ-web-epic.md).
    vec2 uv = vec2(dot(normal, tangentU), dot(normal, tangentV)) * 0.5 + 0.5;
    vec3 color = texture2D(frameTexture, uv).rgb;

    float edgeFade = smoothstep(${EDGE_FADE_START.toFixed(3)}, ${EDGE_FADE_END.toFixed(3)}, visibility);
    gl_FragColor = vec4(mix(farSideColor, color, edgeFade), 1.0);
  }
`;

function latLonToVector3(latDeg, lonDeg) {
  const lat = THREE.MathUtils.degToRad(latDeg);
  const lon = THREE.MathUtils.degToRad(lonDeg);
  return new THREE.Vector3(Math.cos(lat) * Math.cos(lon), Math.sin(lat), Math.cos(lat) * Math.sin(lon)).normalize();
}

// Два вектора, перпендикулярных referenceAxis, задают "право"/"верх"
// исходного кадра — конкретный выбор worldUp произволен (на сфере больше
// нет других ориентиров, с которыми нужно совпасть), важна только
// внутренняя согласованность между tangentU/tangentV и текстурой.
function buildTangentBasis(referenceAxis) {
  const worldUp = Math.abs(referenceAxis.y) > 0.99 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
  const tangentU = new THREE.Vector3().crossVectors(worldUp, referenceAxis).normalize();
  const tangentV = new THREE.Vector3().crossVectors(referenceAxis, tangentU).normalize();
  return { tangentU, tangentV };
}

function showFallback() {
  const canvas = document.getElementById("epic-canvas");
  const fallback = document.getElementById("epic-fallback");
  if (canvas) canvas.hidden = true;
  if (fallback) fallback.hidden = false;
}

function initEpicEarth() {
  const mount = document.getElementById("epic-mount");
  const canvas = document.getElementById("epic-canvas");
  if (!mount || !canvas) {
    return;
  }

  const centroidLat = Number.parseFloat(mount.dataset.centroidLat);
  const centroidLon = Number.parseFloat(mount.dataset.centroidLon);
  const textureUrl = mount.dataset.textureUrl;
  if (!Number.isFinite(centroidLat) || !Number.isFinite(centroidLon) || !textureUrl) {
    showFallback();
    return;
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  } catch {
    showFallback();
    return;
  }

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);

  const referenceAxis = latLonToVector3(centroidLat, centroidLon);
  const { tangentU, tangentV } = buildTangentBasis(referenceAxis);

  const frameTexture = new THREE.TextureLoader().load(textureUrl);
  frameTexture.colorSpace = THREE.SRGBColorSpace;

  const globe = new THREE.Mesh(
    new THREE.SphereGeometry(1, 96, 96),
    new THREE.ShaderMaterial({
      uniforms: {
        frameTexture: { value: frameTexture },
        referenceAxis: { value: referenceAxis },
        tangentU: { value: tangentU },
        tangentV: { value: tangentV },
        farSideColor: { value: FAR_SIDE_COLOR },
      },
      vertexShader: SPHERE_VERTEX_SHADER,
      fragmentShader: SPHERE_FRAGMENT_SHADER,
    })
  );
  scene.add(globe);

  // Сфера сама не вращается — вращается камера вокруг неё (OrbitControls).
  // Uniform'ы referenceAxis/tangentU/tangentV заданы в мировых координатах
  // и не меняются между кадрами (вершинный шейдер передаёт нормаль как
  // есть, без нормал-матрицы, — см. SPHERE_VERTEX_SHADER), поэтому
  // проекция остаётся корректной при любом положении камеры без
  // пересчёта uniform'ов на JS-стороне каждый кадр.
  camera.position.copy(referenceAxis).multiplyScalar(INITIAL_DISTANCE);
  camera.lookAt(0, 0, 0);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0, 0);
  controls.enablePan = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = MIN_DISTANCE;
  controls.maxDistance = MAX_DISTANCE;
  controls.autoRotate = false;
  controls.update();

  function resize() {
    const width = mount.clientWidth;
    const height = mount.clientHeight;
    if (width === 0 || height === 0) {
      return;
    }
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);
  }

  new ResizeObserver(resize).observe(mount);
  resize();

  function animate() {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}

initEpicEarth();
