/* 排除地図 — R–f ヒートマップ+スライダー+動的条件文+三値定理レイヤ */
WAKE.map = (() => {
  const cv = document.getElementById("mapCanvas");
  const ctx = cv.getContext("2d");
  let W, H;
  const RX = R => 70 + (Math.log10(R) + 1) / 2 * (W - 120);
  const FY = f => H - 70 - (Math.log10(f) + 4) / 4 * (H - 120);

  function layerAnchors() {
    const m = WAKE.data.map.rate_layers;
    if (WAKE.state.layer === "bridge")
      return { mul: m.bridge_reference.factor, name: "橋 ×5.3 参考(モデル明示)" };
    if (WAKE.state.layer === "suspect")
      return { mul: null, name: "suspect 込み(両建て)" };
    return { mul: 1, name: "クリーン主計算(下界=安全側)" };
  }

  function lambdaFor(R) {
    const base = WAKE.lambdaR(R);
    const L = layerAnchors();
    if (L.mul) return { lam: base.lam * L.mul, flag: base.flag };
    // suspect 込み: アンカー比で近似(1pc 比 32.75/4.485)
    const cs = WAKE.data.map.rate_layers.with_suspect_dual.anchors_1_2_5_pc;
    const cl = WAKE.data.map.rate_layers.clean_primary.anchors_1_2_5_pc;
    return { lam: base.lam * (cs[0] / cl[0]), flag: base.flag };
  }

  function theoremState(R, f) {
    const th = WAKE.data.map.theorem_layer.domain;
    const Ts = WAKE.state.L_myr;
    let bi = 0, bj = 0, bd = 1e9, be = 1e9;
    th.R.forEach((r, i) => { const d = Math.abs(Math.log(r / R)); if (d < bd) { bd = d; bi = i; } });
    th.T.forEach((t, j) => { const d = Math.abs(Math.log(t / Ts)); if (d < be) { be = d; bj = j; } });
    if (!th.assumptions_ok[bi][bj]) return 1;                 // 定理沈黙
    return (f * th.m1_over_p[bi][bj] > 2.0) ? 0 : 1;          // 0=C2保証(E9 保守端)
  }

  function draw() {
    W = cv.width = cv.clientWidth * devicePixelRatio;
    H = cv.height = cv.clientHeight * devicePixelRatio;
    ctx.clearRect(0, 0, W, H);
    ctx.font = `${11 * devicePixelRatio}px sans-serif`;
    const v = WAKE.state.v_kms;
    // ヒート
    for (let px = 70; px < W - 50; px += 4) {
      const R = Math.pow(10, (px - 70) / (W - 120) * 2 - 1);
      const { lam, flag } = lambdaFor(R);
      const tau = R / (v * 1.02271), Teff = Math.max(0, 10 - tau);
      for (let py = 50; py < H - 70; py += 4) {
        const f = Math.pow(10, (H - 70 - py) / (H - 120) * 4 - 4);
        if (flag === 2 || Teff <= 0) { ctx.fillStyle = "#39404a"; }
        else {
          const N = f * lam * Teff;
          if (N >= 3) { const a = Math.min(1, 0.35 + 0.1 * Math.log10(N / 3 + 1) * 3); ctx.fillStyle = `rgba(217,164,65,${a})`; }
          else ctx.fillStyle = `rgba(30,45,72,${0.55})`;
          if (theoremState(R, f) === 0 && N >= 3) ctx.fillStyle = "rgba(240,200,120,0.95)";
        }
        ctx.fillRect(px, py, 4, 4);
      }
      if (flag === 1) { ctx.fillStyle = "rgba(241,196,64,0.12)"; ctx.fillRect(px, 50, 4, H - 120); }
    }
    // f* 線
    ctx.strokeStyle = "#ff8c66"; ctx.lineWidth = 2 * devicePixelRatio; ctx.beginPath();
    let started = false;
    for (let px = 70; px < W - 50; px += 2) {
      const R = Math.pow(10, (px - 70) / (W - 120) * 2 - 1);
      const { lam, flag } = lambdaFor(R);
      const tau = R / (v * 1.02271), Teff = Math.max(0, 10 - tau);
      if (flag === 2 || Teff <= 0) { started = false; continue; }
      const fs = 3 / (lam * Teff);
      if (fs > 1 || fs < 1e-4) { started = false; continue; }
      const y = FY(fs);
      if (!started) { ctx.moveTo(px, y); started = true; } else ctx.lineTo(px, y);
    }
    ctx.stroke(); ctx.lineWidth = 1;
    // 軸・注記
    ctx.fillStyle = "#7f8ea3";
    [0.1, 0.3, 1, 3.07, 5, 10].forEach(R => ctx.fillText(R + " pc", RX(R) - 10, H - 50));
    [1e-4, 1e-3, 1e-2, 1e-1, 1].forEach(f => ctx.fillText(f.toExponential(0), 12, FY(f) + 4));
    ctx.fillStyle = "#d9a441"; ctx.fillText("訪問済みのはず(琥珀)", W - 260, 70);
    ctx.fillStyle = "#9fb6d0"; ctx.fillText("沈黙と整合(夜空)", W - 260, 90);
    ctx.fillStyle = "#aab"; ctx.fillText("明琥珀=C2 定理保証域(等方化近似・E9 閾値 m>2.0)", W - 420, 110);
    ctx.fillStyle = "#39404a"; ctx.fillRect(W - 280, 122, 12, 12);
    ctx.fillStyle = "#7f8ea3"; ctx.fillText("判定不能(R>5 / τ≥10)", W - 260, 132);
    const dash = RX(3.07);
    ctx.strokeStyle = "#d8dee9"; ctx.setLineDash([4, 4]); ctx.beginPath();
    ctx.moveTo(dash, 50); ctx.lineTo(dash, H - 70); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#d8dee9"; ctx.fillText("CN19 標準 R=3.07", dash + 4, 62);
  }

  function sentence() {
    const v = WAKE.state.v_kms, L = WAKE.state.L_myr;
    const fs = WAKE.fstar(3.07, v);
    const layer = layerAnchors();
    const th = WAKE.data.map.theorem_layer;
    return `【条件付き確率文(JSON テンプレート)】` +
      WAKE.data.map.conditional_statement_template +
      ` — 現在値: ${layer.name}・R=3.07 pc・v=${v} km/s → f* = ` +
      `${fs.fstar ? fs.fstar.toExponential(1) : "—"}(クリーン λ は下界=安全側)。` +
      `L=${L} Myr の定理判定は三値凡例。${th.isotropization_note} ${th.numeric_threshold_note}`;
  }
  return { draw, sentence };
})();
