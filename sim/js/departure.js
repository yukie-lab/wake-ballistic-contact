/* 出発モード — 「人類の次のバスはいつ来るか」。網 JSON の読み替えのみ */
WAKE.departure = (() => {
  function info() {
    const fut = WAKE.data.cat.entries
      .filter(e => e._clean && e._inHorizon && e.t_ph_myr.median > WAKE.state.t)
      .sort((a, b) => a.t_ph_myr.median - b.t_ph_myr.median);
    const next = fut.find(e => e.d_ph_pc.median < 0.1);   // 訪問距離規約 d_visit=0.1 pc(網 v1)
    const dv = WAKE.data.net.results["0.1"].best_transfer_dv_kms;
    let html = "<b>出発モード</b>(全て既存 JSON の読み替え — 新規軌道計算なし)<br>";
    html += "見送った便: ショルツ星(公刊値: 約7万年前・0.25 pc — DR3 外・G3 アンカー)<br>";
    if (next) html += `次発: ${next.source_id_str === "4270814637616488064" ? "GJ 710" : "star " + next.star_index}` +
      `(+${next.t_ph_myr.median.toFixed(2)} Myr, d=${next.d_ph_pc.median.toFixed(3)} pc)` +
      `<br>乗換 Δv 参考(網 v1 最小): ${dv} km/s`;
    return html;
  }
  return { info };
})();
