/* 配線 — ビュー切替・時間再生・fps・憲法制約の常時表示 */
(async () => {
  await WAKE.loadAll();
  const harnessOK = await WAKE.runHarness();
  WAKE.space.init();

  const views = ["timeline", "space", "map", "harness"];
  WAKE.showView = name => {
    views.forEach(v => document.getElementById("view-" + v).classList.toggle("active", v === name));
    document.querySelectorAll("nav button[data-view]").forEach(b =>
      b.classList.toggle("active", b.dataset.view === name));
    WAKE.state.view = name;
    renderCtrl();
  };
  document.querySelectorAll("nav button[data-view]").forEach(b =>
    b.addEventListener("click", () => WAKE.showView(b.dataset.view)));
  document.getElementById("depTgl").addEventListener("click", () => {
    WAKE.state.departure = !WAKE.state.departure;
    document.getElementById("depTgl").textContent = "出発モード: " + (WAKE.state.departure ? "ON" : "OFF");
    renderCtrl();
  });
  document.getElementById("fstarMini").addEventListener("click", () => WAKE.showView("map"));
  const fs0 = WAKE.fstar(3.07, 10);
  document.querySelector("#fstarMini .v").textContent = fs0.fstar.toExponential(1);

  function renderCtrl() {
    const c = document.getElementById("ctrl");
    const s = WAKE.state;
    let html = `<label><input type="checkbox" id="cSus" ${s.showSuspect ? "checked" : ""}> bit5 suspect を表示(両建て)</label>`;
    if (s.view !== "map") html += `
      <label>時刻 t = <b id="tVal">${s.t.toFixed(2)}</b> Myr</label>
      <input type="range" id="cT" min="-10" max="10" step="0.02" value="${s.t}">
      <button class="tgl" id="cPlay">${s.playing ? "⏸ 停止" : "▶ 再生"}</button>`;
    if (s.view === "map") html += `
      <label>探査機速度 v = <b>${s.v_kms}</b> km/s</label>
      <input type="range" id="cV" min="0.5" max="2.5" step="0.05" value="${Math.log10(s.v_kms)}">
      <label>寿命 L = <b>${s.L_myr}</b> Myr(定理レイヤ)</label>
      <input type="range" id="cL" min="-2" max="2" step="0.1" value="${Math.log10(s.L_myr)}">
      <label>レイヤ: <select id="cLayer">
        <option value="clean" ${s.layer === "clean" ? "selected" : ""}>クリーン主計算</option>
        <option value="bridge" ${s.layer === "bridge" ? "selected" : ""}>橋 ×5.3 参考</option>
        <option value="suspect" ${s.layer === "suspect" ? "selected" : ""}>suspect 込み</option>
      </select></label>`;
    if (s.departure) html += `<div style="margin-top:6px;border-top:1px solid var(--line);padding-top:6px">${WAKE.departure.info()}</div>`;
    c.innerHTML = html;
    const bind = (id, fn) => { const el = document.getElementById(id); if (el) el.addEventListener("input", fn); };
    bind("cT", e => { s.t = +e.target.value; document.getElementById("tVal").textContent = s.t.toFixed(2); });
    bind("cV", e => { s.v_kms = +Math.pow(10, +e.target.value).toFixed(1); renderCtrl(); });
    bind("cL", e => { s.L_myr = +Math.pow(10, +e.target.value).toFixed(2); renderCtrl(); });
    bind("cLayer", e => { s.layer = e.target.value; });
    bind("cSus", e => { s.showSuspect = e.target.checked; });
    const pl = document.getElementById("cPlay");
    if (pl) pl.addEventListener("click", () => { s.playing = !s.playing; renderCtrl(); });
  }

  // 判定不能パネル(常時 — 憲法)
  const cat = WAKE.data.cat;
  const nSus = cat.entries.filter(e => e.rv_faint_suspect_bit5).length;
  const nOut = cat.entries.filter(e => !e._inHorizon).length;
  const nSfl = cat.entries.filter(e => e.undecidable_S).length;
  const nExc = cat.entries.filter(e => e.excluded_from_event_judgement).length;
  document.getElementById("undec").innerHTML =
    `<b>判定不能の会計(常時表示・全数 ${cat.n_entries} エントリ)</b>` +
    `<br>S&lt;floor(判定不能): ${nSfl}<br>ホライズン外: ${nOut}` +
    `<br>bit5 suspect: ${nSus}(両建て)<br>個別判定除外(rv_error等): ${nExc}` +
    `<br>R&gt;5 pc・τ≥10 Myr: 地図で灰色`;

  // ループ
  let last = performance.now(), frames = 0, fpsAt = last;
  function loop(now) {
    if (WAKE.state.playing) {
      WAKE.state.t += (now - last) / 1000 * 1.2;
      if (WAKE.state.t > 10) WAKE.state.t = -10;
      const tv = document.getElementById("tVal"), tr = document.getElementById("cT");
      if (tv) tv.textContent = WAKE.state.t.toFixed(2);
      if (tr) tr.value = WAKE.state.t;
    }
    last = now;
    const v = WAKE.state.view || "timeline";
    if (v === "timeline") WAKE.timeline.draw();
    if (v === "space") WAKE.space.frame();
    if (v === "map") { WAKE.map.draw(); document.getElementById("sentence").textContent = WAKE.map.sentence(); }
    else document.getElementById("sentence").textContent =
      "条件付き確率文は排除地図ビューでスライダー値から動的に組み立てられます。";
    frames++;
    if (now - fpsAt > 1000) {
      document.getElementById("fps").textContent =
        `${frames} fps / ハーネス: ${harnessOK ? "PASS" : "FAIL"}`;
      WAKE._fps = frames; frames = 0; fpsAt = now;
    }
    requestAnimationFrame(loop);
  }
  WAKE.showView("harness");   // 最初の成果物 = 検証ハーネスを入口確認
  requestAnimationFrame(loop);
})();
