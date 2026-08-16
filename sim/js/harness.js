/* 検証ハーネス — 最初の成果物(裁定#18 §4)。論文数値と JSON の一致を自動検査 */
WAKE.runHarness = async function () {
  const { cat, map, net, mani } = WAKE.data;
  const t = WAKE.t;
  const checks = [];
  const add = (name, got, exp, ok) => checks.push({ name, got, exp, ok });

  // 論文参照値(期待側 — 監査の照合対象)
  const r1 = cat.rates_per_myr.clean.ipw_corrected["1pc"];
  add(t("hkLam1"), r1, "4.49", Math.abs(r1 - 4.49) < 0.02);
  const r5 = cat.rates_per_myr.clean.ipw_corrected["5pc"];
  add(t("hkLam5"), r5, "137.3", Math.abs(r5 - 137.3) < 0.2);
  add(t("hkN"), cat.n_entries, 2197, cat.n_entries === 2197);
  add(t("hkMapVer"), map.map_version, "1.0.1", map.map_version === "1.0.1");
  const fs = WAKE.fstar(3.07, 10);
  add(t("hkFstar"), fs.fstar && fs.fstar.toExponential(2),
      "≈5.0e-3", fs.fstar > 4.5e-3 && fs.fstar < 5.6e-3);
  const dv = net.results["0.1"].best_transfer_dv_kms;
  add(t("hkDv"), dv, 5.93, Math.abs(dv - 5.93) < 0.02);
  const gj = WAKE.famous["GJ 710"];
  add(t("hkGJd"), gj && gj.d_ph_pc.median, 0.0519,
      gj && Math.abs(gj.d_ph_pc.median - 0.0519) < 0.001);
  add(t("hkGJt"), gj && gj.t_ph_myr.median, 1.2943,
      gj && Math.abs(gj.t_ph_myr.median - 1.2943) < 0.005);
  add(t("hkConv"), !!map.n_crit_convention, true, !!map.n_crit_convention);
  const tl = map.theorem_layer;
  add(t("hkLegend"), `${(tl.legend || []).length}+${(tl.legend_en || []).length}`, "3+3",
      (tl.legend || []).length === 3 && (tl.legend_en || []).length === 3);
  const e9ok = /1\.5[–-]2\.0/.test(tl.numeric_threshold_note || "") &&
               /1\.5[–-]2\.0/.test(tl.numeric_threshold_note_en || "");
  add(t("hkE9"), e9ok, true, e9ok);
  add(t("hkNodes"), net.n_nodes, 646, net.n_nodes === 646);
  const tplOk = !!map.conditional_statement_template && !!map.conditional_statement_template_en;
  add(t("hkTplEn"), tplOk, true, tplOk);

  // MANIFEST sha256(SubtleCrypto)
  for (const [name, meta] of Object.entries(mani.files)) {
    try {
      const buf = await fetch("data/" + name).then(r => r.arrayBuffer());
      const h = await crypto.subtle.digest("SHA-256", buf);
      const hex = [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, "0")).join("");
      add("sha256 " + name, hex.slice(0, 12) + "…", meta.sha256.slice(0, 12) + "…",
          hex === meta.sha256);
    } catch (e) { add("sha256 " + name, "n/a (" + e + ")", meta.sha256.slice(0, 12), false); }
  }
  const nPass = checks.filter(c => c.ok).length;
  const allOk = nPass === checks.length;
  const html = ["<p>" + t("verdictLabel") + "<b class='" + (allOk ? "pass'>" + t("allPass") : "fail'>") +
    nPass + "/" + checks.length + " " + t("pass") + "</b></p><table><tr><th>" +
    [t("thItem"), t("thJson"), t("thExpect"), t("thVerdict")].join("</th><th>") + "</th></tr>"];
  checks.forEach(c => html.push(`<tr><td>${c.name}</td><td>${c.got}</td><td>${c.exp}</td>` +
    `<td class="${c.ok ? "pass" : "fail"}">${c.ok ? t("pass") : t("fail")}</td></tr>`));
  html.push("</table><p style='color:var(--dim);font-size:11px;margin-top:8px'>" +
    t("hardcodeNote") + "</p>");
  document.getElementById("harnessBody").innerHTML = html.join("");
  return allOk;
};
