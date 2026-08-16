/* 配線 — ビュー切替・時間再生・fps・言語切替・憲法制約の常時表示 */
(async () => {
  await WAKE.loadAll();
  let harnessOK = await WAKE.runHarness();
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
    renderDepTgl();
    renderCtrl();
  });
  document.getElementById("langTgl").addEventListener("click", async () => {
    WAKE.state.lang = WAKE.state.lang === "en" ? "ja" : "en";
    await applyLang();
  });
  document.getElementById("fstarMini").addEventListener("click", () => WAKE.showView("map"));
  const fs0 = WAKE.fstar(3.07, 10);

  function renderDepTgl() {
    document.getElementById("depTgl").textContent =
      WAKE.t("dep") + ": " + (WAKE.state.departure ? "ON" : "OFF");
  }

  function renderCtrl() {
    const c = document.getElementById("ctrl");
    const s = WAKE.state, t = WAKE.t;
    // ハーネス画面は数値監査専用 — 操作パネル・条件文を出さない(錨の被り防止)
    const onHarness = s.view === "harness";
    c.style.display = onHarness ? "none" : "block";
    document.getElementById("sentence").style.display = onHarness ? "none" : "block";
    if (onHarness) return;
    let html = `<label><input type="checkbox" id="cSus" ${s.showSuspect ? "checked" : ""}> ${t("cSuspect")}</label>`;
    if (s.view !== "map") html += `
      <label>${t("cTime")}<b id="tVal">${s.t.toFixed(2)}</b> Myr</label>
      <input type="range" id="cT" min="-10" max="10" step="0.02" value="${s.t}">
      <button class="tgl" id="cPlay">${s.playing ? t("cPause") : t("cPlay")}</button>`;
    if (s.view === "map") html += `
      <label>${t("cV")}<b>${s.v_kms}</b> km/s</label>
      <input type="range" id="cV" min="0.5" max="2.5" step="0.05" value="${Math.log10(s.v_kms)}">
      <label>${t("cL")}<b>${s.L_myr}</b>${t("cLTail")}</label>
      <input type="range" id="cL" min="-2" max="2" step="0.1" value="${Math.log10(s.L_myr)}">
      <label>${t("cLayer")}<select id="cLayer">
        <option value="clean" ${s.layer === "clean" ? "selected" : ""}>${t("layerClean")}</option>
        <option value="bridge" ${s.layer === "bridge" ? "selected" : ""}>${t("layerBridge")}</option>
        <option value="suspect" ${s.layer === "suspect" ? "selected" : ""}>${t("layerSuspect")}</option>
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

  // 判定不能パネル(常時 — 憲法。数値は全て JSON 由来のカウント)
  function renderUndec() {
    const cat = WAKE.data.cat, t = WAKE.t;
    const nSus = cat.entries.filter(e => e.rv_faint_suspect_bit5).length;
    const nOut = cat.entries.filter(e => !e._inHorizon).length;
    const nSfl = cat.entries.filter(e => e.undecidable_S).length;
    const nExc = cat.entries.filter(e => e.excluded_from_event_judgement).length;
    document.getElementById("undec").innerHTML =
      `<b>${t("undTitle")}${cat.n_entries}${t("undTitleTail")}</b>` +
      `<br>${t("undSfloor")}${nSfl}<br>${t("undHorizon")}${nOut}` +
      `<br>${t("undBit5")}${nSus}${t("undBit5Tail")}<br>${t("undExcluded")}${nExc}` +
      `<br>${t("undGray")}`;
  }

  async function applyLang() {
    const t = WAKE.t;
    document.documentElement.lang = WAKE.state.lang;
    document.title = t("title");
    document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.getElementById("langTgl").textContent = t("langBtn");
    document.getElementById("fstarMini").title = t("fstarTip");
    document.getElementById("maniLink").textContent =
      t("maniPrefix") + WAKE._maniCount + t("maniNote");
    renderDepTgl();
    renderCtrl();
    renderUndec();
    WAKE.space.refreshInfo();
    harnessOK = await WAKE.runHarness();   // 表の文言を現言語で再構築(数値検査も再実行)
  }
  WAKE.applyLang = applyLang;

  document.querySelector("#fstarMini .v").textContent = fs0.fstar.toExponential(1);
  await applyLang();

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
    else document.getElementById("sentence").textContent = WAKE.t("sentPointer");
    frames++;
    if (now - fpsAt > 1000) {
      document.getElementById("fps").textContent =
        `${frames} fps / ${WAKE.t("navHarness")}: ${harnessOK ? WAKE.t("pass") : WAKE.t("fail")}`;
      WAKE._fps = frames; frames = 0; fpsAt = now;
    }
    requestAnimationFrame(loop);
  }
  WAKE.showView("harness");   // 最初の成果物 = 検証ハーネスを入口確認
  requestAnimationFrame(loop);
})();
