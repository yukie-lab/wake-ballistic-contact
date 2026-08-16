/* 出発モード — 「人類の次のバスはいつ来るか」。網 JSON の読み替えのみ */
WAKE.departure = (() => {
  function info() {
    const t = WAKE.t;
    const fut = WAKE.data.cat.entries
      .filter(e => e._clean && e._inHorizon && e.t_ph_myr.median > WAKE.state.t)
      .sort((a, b) => a.t_ph_myr.median - b.t_ph_myr.median);
    const next = fut.find(e => e.d_ph_pc.median < 0.1);   // 訪問距離規約 d_visit=0.1 pc(網 v1)
    const dv = WAKE.data.net.results["0.1"].best_transfer_dv_kms;
    let html = `<b>${t("depTitle")}</b>${t("depNote")}<br>`;
    html += t("depMissed") + "<br>";
    if (next) html += t("depNext") +
      `${next.source_id_str === "4270814637616488064" ? "GJ 710" : t("star") + next.star_index}` +
      `(+${next.t_ph_myr.median.toFixed(2)} Myr, d=${next.d_ph_pc.median.toFixed(3)} pc)` +
      `<br>${t("depDv")}${dv} km/s`;
    return html;
  }
  return { info };
})();
