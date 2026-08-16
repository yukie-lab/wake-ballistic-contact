/* 検証ハーネス — 最初の成果物(裁定#18 §4)。論文数値と JSON の一致を自動検査 */
WAKE.runHarness = async function () {
  const { cat, map, net, mani } = WAKE.data;
  const checks = [];
  const add = (name, got, exp, ok) => checks.push({ name, got, exp, ok });

  // 論文参照値(期待側 — 監査の照合対象)
  const r1 = cat.rates_per_myr.clean.ipw_corrected["1pc"];
  add("クリーン λ@1pc(論文 4.49)", r1, "4.49±丸め", Math.abs(r1 - 4.49) < 0.02);
  const r5 = cat.rates_per_myr.clean.ipw_corrected["5pc"];
  add("クリーン λ@5pc(論文 137.3)", r5, "137.3", Math.abs(r5 - 137.3) < 0.2);
  add("カタログ星数(論文 2,197)", cat.n_entries, 2197, cat.n_entries === 2197);
  add("地図版(v1.0.1 = E9 波及)", map.map_version, "1.0.1", map.map_version === "1.0.1");
  const fs = WAKE.fstar(3.07, 10);
  add("f*(R=3.07, v=10)(論文 5.0e-3)", fs.fstar && fs.fstar.toExponential(2),
      "≈5.0e-3", fs.fstar > 4.5e-3 && fs.fstar < 5.6e-3);
  const dv = net.results["0.1"].best_transfer_dv_kms;
  add("最小乗換 Δv d≤0.1pc(論文 5.93)", dv, 5.93, Math.abs(dv - 5.93) < 0.02);
  const gj = WAKE.famous["GJ 710"];
  add("GJ710 d_ph(論文 0.0519 pc)", gj && gj.d_ph_pc.median, 0.0519,
      gj && Math.abs(gj.d_ph_pc.median - 0.0519) < 0.001);
  add("GJ710 t_ph(論文 +1.294 Myr)", gj && gj.t_ph_myr.median, 1.2943,
      gj && Math.abs(gj.t_ph_myr.median - 1.2943) < 0.005);
  add("f* 定義規約(N≥3⇔95%)が JSON に存在", !!map.n_crit_convention, true,
      !!map.n_crit_convention);
  add("定理レイヤ三値凡例", map.theorem_layer.legend.length, 3,
      map.theorem_layer.legend.length === 3);
  add("E9 数値閾値注記(1.5–2.0)", /1\.5[–-]2\.0/.test(
      map.theorem_layer.numeric_threshold_note || ""), true,
      /1\.5[–-]2\.0/.test(map.theorem_layer.numeric_threshold_note || ""));
  add("ネットワークノード数(論文 646)", net.n_nodes, 646, net.n_nodes === 646);

  // MANIFEST sha256(SubtleCrypto)
  for (const [name, meta] of Object.entries(mani.files)) {
    try {
      const buf = await fetch("data/" + name).then(r => r.arrayBuffer());
      const h = await crypto.subtle.digest("SHA-256", buf);
      const hex = [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, "0")).join("");
      add("sha256 " + name, hex.slice(0, 12) + "…", meta.sha256.slice(0, 12) + "…",
          hex === meta.sha256);
    } catch (e) { add("sha256 " + name, "計算不可(" + e + ")", meta.sha256.slice(0, 12), false); }
  }
  const nPass = checks.filter(c => c.ok).length;
  const html = ["<p>判定: <b class='" + (nPass === checks.length ? "pass'>全 " : "fail'>") +
    nPass + "/" + checks.length + " PASS</b></p><table><tr><th>項目</th><th>JSON 値</th><th>期待(論文)</th><th>判定</th></tr>"];
  checks.forEach(c => html.push(`<tr><td>${c.name}</td><td>${c.got}</td><td>${c.exp}</td>` +
    `<td class="${c.ok ? "pass" : "fail"}">${c.ok ? "PASS" : "FAIL"}</td></tr>`));
  html.push("</table><p style='color:var(--dim);font-size:11px;margin-top:8px'>" +
    "ハードコード禁止則: 表示値は全て JSON 由来。本表の「期待」列のみが論文参照値。</p>");
  document.getElementById("harnessBody").innerHTML = html.join("");
  return nPass === checks.length;
};
