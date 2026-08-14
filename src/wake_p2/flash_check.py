"""冒頭 5% 定常性速報 (裁定ログ#6 運用条項 / G3-4 の予防的チェック)

完了チャンクから完備性補正後の接近イベント発生率 λ(t) を構成し、
窓 ±10 Myr 内での時間対称性・無ドリフトを検査する。

- 補正: IPW (案A)。w = 1/S (S≥s_floor)。S<floor / NaN は判定不能会計 (率から分離報告)
- 窓端 (at_edge) サロゲートは除外し件数報告
- 判定 (速報基準): 線形トレンド |b|/σ_b < 3 かつ 過去/未来 非対称度 < 3σ。
  正式な G3-4 検定方式の確定は別途裁定 (PHASES 1.2 Phase 2 作業項目5)

実行: ~/miniforge3/envs/wake/bin/python src/wake_p2/flash_check.py [d_max_pc]
"""

import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
N_SURR = 2000
T_MAX = 10.0
BIN = 1.0


def main(d_max=5.0):
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    if not files:
        print("チャンクなし")
        return 2
    cat = np.load(P2 / "catalog_ingested.npz")
    S = cat["s_completeness"]
    n_total = len(S)

    t_all, w_all = [], []
    n_stars = n_edge = n_undecidable_stars = 0
    for f in files:
        z = np.load(f)
        idx = z["star_idx"]
        s_chunk = S[idx]
        usable = np.isfinite(s_chunk) & (s_chunk >= S_FLOOR)
        n_undecidable_stars += int((~usable).sum())
        n_stars += len(idx)
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        sel = (np.abs(t_ph) <= T_MAX) & (d_ph < d_max) & np.isfinite(t_ph)
        n_edge += int((sel & edge).sum())
        sel &= ~edge
        w_star = np.where(usable, 1.0 / np.maximum(s_chunk, S_FLOOR), 0.0)
        rows, cols = np.nonzero(sel)
        t_all.append(t_ph[rows, cols].astype(float))
        w_all.append(w_star[rows])
    t = np.concatenate(t_all)
    w = np.concatenate(w_all)
    frac = n_stars / n_total

    edges = np.arange(-T_MAX, T_MAX + 1e-9, BIN)
    mid = 0.5 * (edges[:-1] + edges[1:])
    lam, _ = np.histogram(t, bins=edges, weights=w)
    lam2, _ = np.histogram(t, bins=edges, weights=w ** 2)
    lam /= N_SURR * BIN
    sig = np.sqrt(lam2) / (N_SURR * BIN)
    ok = sig > 0

    # 加重最小二乗の線形トレンド
    W = 1.0 / sig[ok] ** 2
    xm = np.average(mid[ok], weights=W)
    ym = np.average(lam[ok], weights=W)
    b = np.sum(W * (mid[ok] - xm) * (lam[ok] - ym)) / np.sum(W * (mid[ok] - xm) ** 2)
    sb = np.sqrt(1.0 / np.sum(W * (mid[ok] - xm) ** 2))
    # 過去/未来の非対称
    past = mid < 0
    lp, lf = lam[past].sum(), lam[~past].sum()
    sp = np.sqrt((sig[past] ** 2).sum())
    sf_ = np.sqrt((sig[~past] ** 2).sum())
    asym = (lf - lp) / (lf + lp)
    asym_sig = abs(lf - lp) / np.sqrt(sp ** 2 + sf_ ** 2)

    print(f"== 冒頭定常性速報 (d<{d_max} pc, ±{T_MAX} Myr, 補正=IPW floor={S_FLOOR}) ==")
    print(f"処理済み: {len(files)} チャンク / {n_stars:,} 星 ({frac:.1%} of {n_total:,})")
    print(f"判定不能会計: S欠損/floor未満 {n_undecidable_stars} 星 / 窓端サロゲート {n_edge:,} 件")
    print(f"λ 全窓平均 (全カタログ換算): {lam.sum() / (2 * T_MAX) / frac:.1f} /Myr")
    print(f"線形トレンド b = {b:+.3f} ± {sb:.3f} /Myr² → |b|/σ = {abs(b) / sb:.2f}")
    print(f"過去/未来 非対称度 = {asym:+.3f} ({asym_sig:.2f}σ)")
    verdict = (abs(b) / sb < 3) and (asym_sig < 3)
    print(f"速報判定: {'PASS (ドリフト・非対称の異常なし)' if verdict else 'ANOMALY — 即停止・報告 (裁定ログ#6)'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 5.0))
