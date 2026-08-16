/* データ層 — 供給仕様 v0 の3ファイル+MANIFEST のみから読む(ハードコード禁止) */
const WAKE = { data: {}, state: { t: 0, playing: false, departure: false,
  showSuspect: false, layer: "clean", selStar: null, v_kms: 10, L_myr: 10 } };

WAKE.loadAll = async function () {
  const base = "data/";
  const [cat, map, net, mani] = await Promise.all([
    fetch(base + "arrival_catalog_v1.json").then(r => r.json()),
    fetch(base + "exclusion_map_v1.json").then(r => r.json()),
    fetch(base + "flyby_network_v1.json").then(r => r.json()),
    fetch(base + "MANIFEST.json").then(r => r.json()),
  ]);
  WAKE.data = { cat, map, net, mani };
  // 派生: クリーン・ホライズン内エントリ(表示既定)
  cat.entries.forEach(e => {
    e._clean = !e.rv_faint_suspect_bit5 && !e.undecidable_S;
    e._inHorizon = e.within_horizon_default;
  });
  WAKE.famous = {};
  const famousIds = { "4270814637616488064": "GJ 710",
                      "510911618569239040": "HD 7977",
                      "5571232118090082816": "UCAC4 237-008148" };
  cat.entries.forEach(e => {
    const n = famousIds[e.source_id_str || String(e.source_id)];
    if (n) WAKE.famous[n] = e;
  });
  // λ(R) 補間(クリーン主 — JSON の lambda_R 表をそのまま使用)
  const rl = map.rate_layers.clean_primary;
  WAKE.lambdaR = function (R) {
    const Rs = map.axes.R_pc, L = rl.lambda_R, F = rl.flags;
    let best = -1, bd = 1e9;
    for (let i = 0; i < Rs.length; i++) {
      const d = Math.abs(Math.log(Rs[i] / R));
      if (d < bd) { bd = d; best = i; }
    }
    return { lam: L[best], flag: F[best] };
  };
  WAKE.fstar = function (R, v_kms) {
    const { lam, flag } = WAKE.lambdaR(R);
    if (flag === 2) return { fstar: null, flag };
    const tau = R / (v_kms * 1.02271);
    const Teff = Math.max(0, 10 - tau);
    if (Teff <= 0) return { fstar: null, flag: 3 };
    return { fstar: 3.0 / (lam * Teff), flag };
  };
  document.getElementById("maniLink").textContent =
    "MANIFEST: " + Object.keys(mani.files).length + " files (sha256 検証はハーネス)";
  return WAKE.data;
};

/* BP−RP → 黒体近似色(物理由来彩色 — 裁定3) */
WAKE.bpRpColor = function (bpRp) {
  const T = 4600 * (1 / (0.92 * bpRp + 1.7) + 1 / (0.92 * bpRp + 0.62)); // Ballesteros 近似
  const t = Math.max(2500, Math.min(12000, T)) / 100;
  let r, g, b;
  if (t <= 66) { r = 255; g = 99.47 * Math.log(t) - 161.1; }
  else { r = 329.7 * Math.pow(t - 60, -0.133); g = 288.1 * Math.pow(t - 60, -0.0755); }
  b = t >= 66 ? 255 : (t <= 19 ? 0 : 138.5 * Math.log(t - 10) - 305.0);
  const c = x => Math.max(0, Math.min(255, x)) / 255;
  return [c(r), c(g), c(b)];
};
