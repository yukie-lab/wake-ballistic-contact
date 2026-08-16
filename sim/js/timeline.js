/* 航跡タイムライン(入口)— t×d 帯、CI90 リボン、ホライズン=判定不能、有名星ラベル */
WAKE.timeline = (() => {
  const cv = document.getElementById("tlCanvas");
  const ctx = cv.getContext("2d");
  let W, H;
  const X = t => (t + 10) / 20 * (W - 90) + 60;
  const Y = d => H - 60 - (Math.log10(Math.max(d, 0.02)) - Math.log10(0.02)) /
                 (Math.log10(6) - Math.log10(0.02)) * (H - 110);

  function draw() {
    W = cv.width = cv.clientWidth * devicePixelRatio;
    H = cv.height = cv.clientHeight * devicePixelRatio;
    ctx.clearRect(0, 0, W, H);
    ctx.font = `${11 * devicePixelRatio}px sans-serif`;
    // 軸
    ctx.strokeStyle = "#243040"; ctx.fillStyle = "#7f8ea3";
    for (let t = -10; t <= 10; t += 2) {
      ctx.beginPath(); ctx.moveTo(X(t), H - 60); ctx.lineTo(X(t), 50); ctx.globalAlpha = .25; ctx.stroke(); ctx.globalAlpha = 1;
      ctx.fillText((t > 0 ? "+" : "") + t + " Myr", X(t) - 14, H - 40);
    }
    [0.05, 0.1, 0.5, 1, 2, 5].forEach(d => {
      ctx.fillText(d + " pc", 8, Y(d) + 4);
      ctx.beginPath(); ctx.moveTo(60, Y(d)); ctx.lineTo(W - 30, Y(d)); ctx.globalAlpha = .15; ctx.stroke(); ctx.globalAlpha = 1;
    });
    // 現在線
    ctx.strokeStyle = "#d9a441"; ctx.globalAlpha = .6;
    ctx.beginPath(); ctx.moveTo(X(WAKE.state.t), H - 60); ctx.lineTo(X(WAKE.state.t), 50); ctx.stroke(); ctx.globalAlpha = 1;
    // エントリ
    const dep = WAKE.state.departure;
    WAKE.data.cat.entries.forEach(e => {
      const sus = e.rv_faint_suspect_bit5;
      if (sus && !WAKE.state.showSuspect) return;
      const t = e.t_ph_myr.median, d = e.d_ph_pc.median;
      if (Math.abs(t) > 10 || d > 5.5) return;
      const inH = e._inHorizon;
      let col = dep ? (t < WAKE.state.t ? "#8a5a44" : "#6fbf73") : "#9fb6d0";
      if (sus) col = "#e06c75";
      ctx.globalAlpha = (inH ? 0.85 : 0.25) * (sus ? 0.5 : 1);
      // CI90 リボン
      ctx.strokeStyle = col;
      ctx.beginPath(); ctx.moveTo(X(e.t_ph_myr.ci90[0]), Y(d)); ctx.lineTo(X(e.t_ph_myr.ci90[1]), Y(d)); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(X(t), Y(e.d_ph_pc.ci90[0])); ctx.lineTo(X(t), Y(e.d_ph_pc.ci90[1])); ctx.stroke();
      ctx.fillStyle = col;
      if (inH) { ctx.beginPath(); ctx.arc(X(t), Y(d), 2.4 * devicePixelRatio, 0, 7); ctx.fill(); }
      else { ctx.strokeRect(X(t) - 2, Y(d) - 2, 4, 4); }   // 判定不能=中抜き
      ctx.globalAlpha = 1;
    });
    // 有名星
    ctx.fillStyle = "#d9a441";
    for (const [name, e] of Object.entries(WAKE.famous)) {
      ctx.fillText(name, X(e.t_ph_myr.median) + 6, Y(e.d_ph_pc.median) - 6);
    }
    // ショルツ星(カタログ外・G3公刊アンカー — 実装指示書#18 裁定2の注記値)
    ctx.fillStyle = dep ? "#8a5a44" : "#7f8ea3";
    ctx.fillText(WAKE.t("tlScholz") + (dep ? WAKE.t("tlScholzDep") : ""),
      X(-0.07) + 6, Y(0.25) + 14);
    ctx.strokeStyle = ctx.fillStyle;
    ctx.strokeRect(X(-0.07) - 3, Y(0.25) - 3, 6, 6);
    // 凡例
    ctx.fillStyle = "#7f8ea3";
    ctx.fillText(WAKE.t("tlLegend"), 60, 30);
    if (dep) ctx.fillText(WAKE.t("tlDepLegend"), 60, 30 + 16 * devicePixelRatio);
  }
  cv.addEventListener("click", ev => {
    const r = cv.getBoundingClientRect();
    const px = (ev.clientX - r.left) * devicePixelRatio, py = (ev.clientY - r.top) * devicePixelRatio;
    let best = null, bd = 20 * devicePixelRatio;
    WAKE.data.cat.entries.forEach(e => {
      const dx = X(e.t_ph_myr.median) - px, dy = Y(e.d_ph_pc.median) - py;
      const dd = Math.hypot(dx, dy);
      if (dd < bd) { bd = dd; best = e; }
    });
    if (best) { WAKE.state.selStar = best; WAKE.showView("space"); }
  });
  return { draw };
})();
