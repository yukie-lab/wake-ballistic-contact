"""到来イベントカタログ v1(Phase 2 出口条件 — 完備性補正前後の両版・JSON)

仕様(憲法第11条2項: アプリ用エクスポートを最初から仕様に含める / 第5条6項:
窓外縁は判定不能 / 裁定ログ#4(5): rv_error>20 は個別イベント判定から除外
(率には寄与)・検疫ビットは判定不能会計に合流):

- 収録: |t|≤13 Myr・d_ph 中央値 < 5 pc の星(surrogate 中央値基準)
- 各星: source_id, t_ph/d_ph の中央値と CI90, P(d<1/2/5), 個別ホライズン
  (既定・感度), ホライズン内フラグ, S 完備性と IPW 重み(補正後版の材料),
  検疫ビット, rv_error 除外フラグ, edge 率
- 両版: (i) uncorrected = 生カウント統計, (ii) corrected = IPW 重み付き
  (S<floor は weight null = 判定不能扱い)。率サマリブロックに両版の
  λ@1/2/5pc(露出正規化 — G1 の主推定量と同定義)を記載
- スキーマ版: v1(schema_version フィールド)

実行: python3 src/wake_p2/event_catalog.py → data/p2/arrival_catalog_v1.json
"""
import glob
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = P2 / "arrival_catalog_v1.json"
T_ENV = 13.0
N_SURR = 2000
RV_ERR_MAX = 20.0


def _fin(x, nd):
    """有限値のみ丸めて返す。欠測(NaN/inf)は None = JSON null。"""
    x = float(x)
    return round(x, nd) if np.isfinite(x) else None


def main():
    cat = dict(np.load(P2 / "catalog_ingested.npz"))
    from wake_data.horizon_eff import effective_horizons
    eff_d, eff_s = effective_horizons(cat)      # 裁定ログ#11 裁定2
    cat["t_h_default"], cat["t_h_sens"] = eff_d, eff_s
    S = cat["s_completeness"]
    b5 = np.load(P2 / "quarantine_bit5.npz")    # 裁定ログ#11 裁定1
    suspect = b5["mask"]
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    entries = []
    n_total = 0
    for f in files:
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        n_total += len(idx)
        d_med = np.nanmedian(np.where(np.abs(t_ph) <= T_ENV, d_ph, np.nan), axis=1)
        for r in np.flatnonzero(d_med < 5.0):
            g = int(idx[r])
            m = np.isfinite(t_ph[r]) & (np.abs(t_ph[r]) <= T_ENV)
            tt, dd, ee = t_ph[r][m], d_ph[r][m], edge[r][m]
            if not len(tt):
                continue
            s_val = float(S[g]) if np.isfinite(S[g]) else None
            usable = s_val is not None and s_val >= S_FLOOR
            th_d = float(cat["t_h_default"][g])
            rv_err = float(cat["rv_error"][g]) if "rv_error" in cat else None
            q = int(cat["quarantine_flags"][g]) if "quarantine_flags" in cat else 0
            entries.append({
                "source_id": int(cat["source_id"][g]),
                # JS の JSON.parse は 2^53 超を丸めるため、正確な ID は文字列でも供給
                "source_id_str": str(int(cat["source_id"][g])),
                "star_index": g,
                "t_ph_myr": {"median": round(float(np.median(tt)), 4),
                             "ci90": [round(float(np.quantile(tt, 0.05)), 4),
                                      round(float(np.quantile(tt, 0.95)), 4)]},
                "d_ph_pc": {"median": round(float(np.median(dd)), 4),
                            "ci90": [round(float(np.quantile(dd, 0.05)), 4),
                                     round(float(np.quantile(dd, 0.95)), 4)]},
                "p_within": {"1pc": round(float((dd < 1).mean()), 4),
                             "2pc": round(float((dd < 2).mean()), 4),
                             "5pc": round(float((dd < 5).mean()), 4)},
                "horizon_myr": {"default": round(th_d, 3),
                                "sens": round(float(cat["t_h_sens"][g]), 3)},
                "within_horizon_default": bool(abs(float(np.median(tt))) <= th_d),
                "completeness_S": None if s_val is None else round(s_val, 4),
                "ipw_weight": (round(1.0 / max(s_val, S_FLOOR), 3)
                               if usable else None),
                "undecidable_S": not usable,
                "rv_error_kms": None if rv_err is None else round(rv_err, 2),
                "excluded_from_event_judgement": bool(
                    (rv_err is not None and rv_err > RV_ERR_MAX)
                    or suspect[g]),
                "quarantine_bits": q,
                "rv_faint_suspect_bit5": bool(suspect[g]),
                "edge_fraction": round(float(ee.mean()), 4),
                "n_surrogates_in_window": int(len(tt)),
                # v1.1 追加列(シミュレータ表示用 — 裁定ログ#18 裁定1/3)
                "astrometry": {
                    "ra": round(float(cat["ra"][g]), 6),
                    "dec": round(float(cat["dec"][g]), 6),
                    "parallax": round(float(cat["parallax"][g]), 4),
                    "pmra": round(float(cat["pmra"][g]), 4),
                    "pmdec": round(float(cat["pmdec"][g]), 4),
                    "rv": round(float(cat["radial_velocity"][g]), 2),
                    "g_mag": _fin(cat["phot_g_mean_mag"][g], 3),
                    "bp_rp": _fin(cat["bp_rp"][g], 3),  # 欠測は null(JSON に NaN 禁止)
                },
            })
    entries.sort(key=lambda e: e["d_ph_pc"]["median"])

    # 率サマリ(G1 と同定義の露出正規化、uncorrected = w≡1)
    def rates(weighted, clean):
        th = cat["t_h_default"]
        lam = {}
        for dmax in (1.0, 2.0, 5.0):
            tot = 0.0
            for f in files:
                z = np.load(f)
                idx = z["star_idx"]
                t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
                s_c = S[idx]
                usable = np.isfinite(s_c) & (s_c >= S_FLOOR)
                if clean:
                    usable &= ~suspect[idx]
                w = np.where(usable, 1.0 / np.maximum(s_c, S_FLOOR), 0.0) \
                    if weighted else usable.astype(float)
                e = 2.0 * np.minimum(10.0, np.maximum(th[idx], 1e-9))
                mask = (np.isfinite(t_ph) & ~edge & (d_ph < dmax)
                        & (np.abs(t_ph) <= 10.0)
                        & (np.abs(t_ph) <= th[idx][:, None]))
                n = mask.sum(axis=1)
                tot += float((w * n / e).sum())
            lam[f"{dmax:.0f}pc"] = round(tot / N_SURR, 3)
        return lam

    # 表示用誤差束(16 サロゲートの太陽中心 6D — 実共分散から生成、裁定#18 裁定1)
    from wake_p2.run_mc import _surrogates
    from wake_data.icrs import icrs_to_helio_galactic
    rngb = np.random.default_rng(20260817)
    entry_idx = np.array([e["star_index"] for e in entries])
    N_B = 16
    # _surrogates は N_SURR 列生成なので、対象星のみ小規模再生成
    import wake_p2.run_mc as rm
    saved = rm.N_SURR
    rm.N_SURR = N_B
    ra_b, dec_b, plx_b, pmra_b, pmdec_b, rv_b = _surrogates(
        {k: cat[k] for k in cat}, entry_idx, rngb)
    rm.N_SURR = saved
    for i, e in enumerate(entries):
        okb = plx_b[i] > 0
        pos_b, vel_b = icrs_to_helio_galactic(
            ra_b[i][okb], dec_b[i][okb], plx_b[i][okb],
            pmra_b[i][okb], pmdec_b[i][okb], rv_b[i][okb])
        e["display_bundle"] = {
            "note": "16 surrogates, real covariance; linear display propagation",
            "pos_pc": np.round(pos_b, 3).tolist(),
            "vel_pc_myr": np.round(vel_b * 1.02271, 4).tolist(),
        }
    doc = {
        "schema_version": "v1.1",
        "generated": "2026-08-17 (v1.1: +astrometry, +display_bundles)",
        "definition": {
            "window_myr": T_ENV, "n_surrogates": N_SURR,
            "inclusion": "median d_ph < 5 pc within |t|<=13 Myr",
            "rate_estimator": "exposure-normalized (2*min(10, t_h) per star), "
                              "control region S>=floor & in-horizon",
            "notes": ["露出規約 = 星ごとの有効露出 2·min(10 Myr, t_h_eff)、"
                      "t_h_eff = min(測定ホライズン, t_pot) — 裁定ログ#11 裁定2"
                      "(追加指示 §5 の明記要件)",
                      "bit5 rv_faint_suspect(G>13.5 ∧ |RV|>150)は個別イベント"
                      "判定から除外・率は両建て報告 — 裁定ログ#11 裁定1",
                      "スケーリング注記(裁定ログ#12): クリーン母集団 λ の距離"
                      "スケーリング(1→2pc 6.1×・2→5pc 5.0×)は厳密な d² から"
                      "偏差する — 少数星支配(重い裾)と IPW 重みの距離構造の反映。"
                      "G3-3 の n=2.0±0.3 は BJ 規約側の検定であり別物",
                      "窓外縁・S<floor は判定不能(憲法第5条6項)",
                      "rv_error>20 km/s は個別イベント判定から除外・率には寄与"
                      "(裁定ログ#4(5))",
                      "corrected 版は IPW(gaiaunlimited DR3 RVS 選択関数、"
                      "s_floor=0.05 — 裁定ログ#8)"],
        },
        "rates_per_myr": {
            "clean": {"uncorrected": rates(False, True),
                      "ipw_corrected": rates(True, True)},
            "including_rv_faint_suspect": {"uncorrected": rates(False, False),
                                           "ipw_corrected": rates(True, False)}},
        "n_catalog": n_total,
        "n_entries": len(entries),
        "entries": entries,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1,
                              allow_nan=False))  # NaN 混入は生成時に即エラー
    print(f"カタログ v1: {len(entries)} 星 → {OUT}")
    print("率 [/Myr]:", doc["rates_per_myr"])
    for e in entries[:5]:
        print(f"  {e['source_id']}: d={e['d_ph_pc']['median']} pc "
              f"t={e['t_ph_myr']['median']} Myr")


if __name__ == "__main__":
    main()
