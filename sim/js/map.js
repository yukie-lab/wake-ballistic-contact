/* 排除地図 — R–f ヒートマップ+スライダー+動的条件文+三値定理レイヤ */
WAKE.map = (() => {
  const cv = document.getElementById("mapCanvas");
  const ctx = cv.getContext("2d");
  let W, H, lastKey = "";
  // 下端は条件文バー(複数行)の上に出す
  const RX = R => 70 + (Math.log10(R) + 1) / 2 * (W - 120);
  const FY = f => H - 240 - (Math.log10(f) + 4) / 4 * (H - 290);
  // ヒートはオフスクリーン ImageData(セル毎 fillRect は 1fps 級に落ちる)
  const CW = 240, CH = 160;
  const off = document.createElement("canvas");
  off.width = CW; off.height = CH;
  const octx = off.getContext("2d");

  function layerAnchors() {
    const m = WAKE.data.map.rate_layers;
    if (WAKE.state.layer === "bridge")
      return { mul: m.bridge_reference.factor, name: WAKE.t("layerBridge") };
    if (WAKE.state.layer === "suspect")
      return { mul: null, name: WAKE.t("layerSuspect") };
    return { mul: 1, name: WAKE.t("layerClean") };
  }

  function lambdaFor(R) {
    const base = WAKE.lambdaR(R);
    const L = layerAnchors();
    if (L.mul) return { lam: base.lam * L.mul, flag: base.flag };
    // suspect 込み: アンカー比で近似(1pc 比)
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

  function draw(force) {
    const w = cv.clientWidth * devicePixelRatio, h = cv.clientHeight * devicePixelRatio;
    const s = WAKE.state;
    const key = [w, h, s.v_kms, s.L_myr, s.layer, s.lang].join("|");
    if (!force && key === lastKey) return;   // 入力が変わった時だけ再描画
    lastKey = key;
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    W = w; H = h;
    ctx.clearRect(0, 0, W, H);
    ctx.font = `${11 * devicePixelRatio}px sans-serif`;
    const v = s.v_kms;
    // ヒート(セル格子 → ImageData → 拡大転写)
    const img = octx.createImageData(CW, CH);
    for (let cx = 0; cx < CW; cx++) {
      const R = Math.pow(10, cx / (CW - 1) * 2 - 1);
      const { lam, flag } = lambdaFor(R);
      const tau = R / (v * 1.02271), Teff = Math.max(0, 10 - tau);
      for (let cy = 0; cy < CH; cy++) {
        const f = Math.pow(10, (1 - cy / (CH - 1)) * 4 - 4);
        let r, g, b, a;
        if (flag === 2 || Teff <= 0) { r = 57; g = 64; b = 74; a = 255; }        // 判定不能
        else {
          const N = f * lam * Teff;
          if (N >= 3) {
            if (theoremState(R, f) === 0) { r = 240; g = 200; b = 120; a = 242; } // C2 保証域
            else { const al = Math.min(1, 0.35 + 0.3 * Math.log10(N / 3 + 1)); r = 217; g = 164; b = 65; a = Math.round(255 * al); }
          } else { r = 30; g = 45; b = 72; a = 140; }                             // 沈黙と整合
        }
        const i4 = (cy * CW + cx) * 4;
        img.data[i4] = r; img.data[i4 + 1] = g; img.data[i4 + 2] = b; img.data[i4 + 3] = a;
      }
    }
    octx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(off, 70, 50, W - 120, H - 290);
    // d² 外挿域(flag=1 ⇔ R<1)の帯
    ctx.fillStyle = "rgba(241,196,64,0.10)";
    ctx.fillRect(RX(0.1), 50, RX(1.0) - RX(0.1), H - 290);
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
    [0.1, 0.3, 1, 3.07, 5, 10].forEach(R => {
      const lbl = R + " pc";
      // 右端ラベルの見切れ防止(美学レビュー指摘)
      const lx = Math.min(RX(R) - 10, W - ctx.measureText(lbl).width - 4 * devicePixelRatio);
      ctx.fillText(lbl, lx, H - 220);
    });
    [1e-4, 1e-3, 1e-2, 1e-1, 1].forEach(f => ctx.fillText(f.toExponential(0), 12, FY(f) + 4));
    // 凡例は f* ミニ表示・判定不能パネル(DOM, css 高 ~225px)の下に出す
    const lx = W - 450 * devicePixelRatio, ly = 245 * devicePixelRatio,
          lh = 15 * devicePixelRatio;
    ctx.fillStyle = "#d9a441"; ctx.fillText(WAKE.t("mapVisited"), lx, ly);
    ctx.fillStyle = "#9fb6d0"; ctx.fillText(WAKE.t("mapSilent"), lx, ly + lh);
    ctx.fillStyle = "#aab"; ctx.fillText(WAKE.t("mapTheorem"), lx, ly + 2 * lh);
    ctx.fillStyle = "#39404a"; ctx.fillRect(lx - 18, ly + 2 * lh + 8, 12, 12);
    ctx.fillStyle = "#7f8ea3"; ctx.fillText(WAKE.t("mapUndec"), lx, ly + 3 * lh + 3);
    const dash = RX(3.07);
    ctx.strokeStyle = "#d8dee9"; ctx.setLineDash([4, 4]); ctx.beginPath();
    ctx.moveTo(dash, 50); ctx.lineTo(dash, H - 240); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#d8dee9"; ctx.fillText(WAKE.t("mapCN19"), dash + 4, 62);
  }

  function sentence() {
    const v = WAKE.state.v_kms, L = WAKE.state.L_myr;
    const fs = WAKE.fstar(3.07, v);
    const layer = layerAnchors();
    const th = WAKE.data.map.theorem_layer;
    const t = WAKE.t;
    return t("sentPrefix") +
      WAKE.jsonText(WAKE.data.map, "conditional_statement_template") +
      `${t("sentNow")}${layer.name} / R=3.07 pc / v=${v} km/s${t("sentFs")}` +
      `${fs.fstar ? fs.fstar.toExponential(1) : "—"}${t("sentSafe")}` +
      `${t("sentTheorem")}${L}${t("sentTheoremTail")}` +
      `${WAKE.jsonText(th, "isotropization_note")} ${WAKE.jsonText(th, "numeric_threshold_note")}`;
  }
  return { draw, sentence };
})();
