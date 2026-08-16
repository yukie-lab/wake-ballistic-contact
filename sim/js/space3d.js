/* フライバイ網 3D — 誤差束(16本)・実測色/等級・時間再生・最小乗換ハイライト */
WAKE.space = (() => {
  const cv = document.getElementById("glCanvas");
  const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true });
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(55, 2, 0.05, 4000);
  let az = 0.6, el = 0.35, dist = 60, target = new THREE.Vector3(0, 0, 0);
  let bundlePts, nomPts, trailSeg, pathLine, labelSprites = [];
  let N, B = 16, pos0, vel, colors, entries;

  function camUpdate() {
    cam.position.set(target.x + dist * Math.cos(el) * Math.cos(az),
                     target.y + dist * Math.cos(el) * Math.sin(az),
                     target.z + dist * Math.sin(el));
    cam.up.set(0, 0, 1); cam.lookAt(target);
  }
  let drag = null;
  cv.addEventListener("pointerdown", e => drag = { x: e.clientX, y: e.clientY, b: e.button });
  addEventListener("pointerup", () => drag = null);
  addEventListener("pointermove", e => {
    if (!drag) return;
    az -= (e.clientX - drag.x) * 0.005; el = Math.max(-1.4, Math.min(1.4, el + (e.clientY - drag.y) * 0.005));
    drag.x = e.clientX; drag.y = e.clientY; camUpdate();
  });
  cv.addEventListener("wheel", e => { dist = Math.max(3, Math.min(600, dist * (1 + e.deltaY * 0.001))); camUpdate(); e.preventDefault(); }, { passive: false });

  function makeLabel(text, color) {
    const c = document.createElement("canvas"); c.width = 512; c.height = 64;
    const x = c.getContext("2d"); x.font = "28px sans-serif"; x.fillStyle = color; x.fillText(text, 4, 40);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthTest: false }));
    sp.scale.set(16, 2, 1); scene.add(sp); return sp;
  }

  function init() {
    entries = WAKE.data.cat.entries.filter(e => e.display_bundle);
    N = entries.length;
    pos0 = new Float32Array(N * B * 3); vel = new Float32Array(N * B * 3);
    colors = new Float32Array(N * B * 3);
    const sizes = [];
    entries.forEach((e, i) => {
      const [r, g, b] = WAKE.bpRpColor(e.astrometry.bp_rp || 1.0);
      const bright = Math.max(0.3, Math.min(1.6, (14 - (e.astrometry.g_mag || 12)) / 6));
      for (let k = 0; k < B; k++) {
        const p = e.display_bundle.pos_pc[Math.min(k, e.display_bundle.pos_pc.length - 1)];
        const v = e.display_bundle.vel_pc_myr[Math.min(k, e.display_bundle.vel_pc_myr.length - 1)];
        const j = (i * B + k) * 3;
        pos0[j] = p[0]; pos0[j + 1] = p[1]; pos0[j + 2] = p[2];
        vel[j] = v[0]; vel[j + 1] = v[1]; vel[j + 2] = v[2];
        colors[j] = r * bright; colors[j + 1] = g * bright; colors[j + 2] = b * bright;
      }
      sizes.push(bright);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos0.slice(), 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    bundlePts = new THREE.Points(geo, new THREE.PointsMaterial({
      size: 0.55, vertexColors: true, transparent: true, opacity: 0.5, sizeAttenuation: true }));
    scene.add(bundlePts);
    // 太陽
    const sunG = new THREE.BufferGeometry();
    sunG.setAttribute("position", new THREE.BufferAttribute(new Float32Array([0, 0, 0]), 3));
    scene.add(new THREE.Points(sunG, new THREE.PointsMaterial({ size: 2.2, color: 0xffd977 })));
    labelSprites.push([makeLabel("Sun", "#ffd977"), () => new THREE.Vector3(0, 0, 0)]);
    for (const [name, e] of Object.entries(WAKE.famous)) {
      const idx = entries.indexOf(e);
      if (idx >= 0) labelSprites.push([makeLabel(name, "#d9a441"), () => {
        const j = idx * B * 3, t = WAKE.state.t;
        return new THREE.Vector3(pos0[j] + vel[j] * t, pos0[j + 1] + vel[j + 1] * t, pos0[j + 2] + vel[j + 2] * t);
      }]);
    }
    // 最小乗換経路(網 v1 の best_pair — 全計算は JSON 読み替えのみ)
    drawBestPath();
    camUpdate();
  }

  function drawBestPath() {
    if (pathLine) { scene.remove(pathLine); pathLine = null; }
    const bp = WAKE.data.net.results["0.1"];
    if (!bp || !bp.best_pair) return;
    const [gi, gj] = bp.best_pair;
    const ei = entries.find(e => e.star_index === gi), ej = entries.find(e => e.star_index === gj);
    if (!ei || !ej) return;
    const pAt = (e, t) => {
      const p = e.display_bundle.pos_pc[0], v = e.display_bundle.vel_pc_myr[0];
      return new THREE.Vector3(p[0] + v[0] * t, p[1] + v[1] * t, p[2] + v[2] * t);
    };
    const a = pAt(ei, ei.t_ph_myr.median), b = pAt(ej, ej.t_ph_myr.median);
    const g = new THREE.BufferGeometry().setFromPoints([a, b]);
    pathLine = new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xd9a441 }));
    scene.add(pathLine);
    const info = document.getElementById("starInfo");
    info.style.display = "block";
    info.innerHTML = `<b>${WAKE.t("siTitle")}</b><br>` +
      `${WAKE.t("siDv")}${bp.best_transfer_dv_kms}${WAKE.t("siDvTail")}<br>` +
      `<span style="color:var(--dim)">${WAKE.t("siNote")}</span>`;
  }

  function frame() {
    const t = WAKE.state.t;
    const attr = bundlePts.geometry.getAttribute("position");
    for (let j = 0; j < N * B * 3; j++) attr.array[j] = pos0[j] + vel[j] * t;
    attr.needsUpdate = true;
    labelSprites.forEach(([sp, fn]) => { const p = fn(); sp.position.set(p.x, p.y + 1.2, p.z); });
    const w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== w * devicePixelRatio) { renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); }
    renderer.render(scene, cam);
  }
  return { init, frame, refreshInfo: () => { if (entries) drawBestPath(); } };
})();
