"""定常性速報 — 修正版 (裁定ログ#8 裁定3 / 憲法 1.2 G3-4)

検定域 = **完備性統制領域**: S≥s_floor かつ 個別ホライズン内 (|t_ph| ≤ t_h 既定)。
領域外は判定不能 (第5条6項の母集団版) として件数報告のみ。

- **主統計量: 過去/未来対称性** A = (F−P)/(F+P)。誤差は**星単位ブロック
  ブートストラップ** (同一星のサロゲートは強相関のため。旧版の誤り — 裁定ログ#8)
- 副統計量: 統制領域内の線形トレンド b (同じく星ブートストラップ誤差)
- 生カウント対称性も併記 (伝播バグの独立監視)

判定: |A|/σ_A < 3 (主)。副は参考表示。

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
N_BOOT = 2000


def collect(d_max):
    cat = np.load(P2 / "catalog_ingested.npz")
    from wake_data.horizon_eff import effective_horizons
    S = cat["s_completeness"]
    th, _ = effective_horizons(cat)   # 裁定ログ#11 裁定2: min(t_h, t_pot)
    files = sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz")))
    per_star = {}          # star_global_idx -> (w, past_n, future_n, t_list)
    n_stars = n_undecid_S = 0
    n_ev_out_horizon = n_edge = 0
    raw_p = raw_f = 0
    for f in files:
        z = np.load(f)
        idx = z["star_idx"]
        n_stars += len(idx)
        s_c, th_c = S[idx], th[idx]
        usable = np.isfinite(s_c) & (s_c >= S_FLOOR)
        n_undecid_S += int((~usable).sum())
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        base = (np.abs(t_ph) <= T_MAX) & (d_ph < d_max) & np.isfinite(t_ph)
        n_edge += int((base & edge).sum())
        base &= ~edge
        raw_p += int((base & (t_ph < 0)).sum())
        raw_f += int((base & (t_ph >= 0)).sum())
        dom = base & (np.abs(t_ph) <= th_c[:, None]) & usable[:, None]
        n_ev_out_horizon += int((base & ~dom).sum())
        rows = np.unique(np.nonzero(dom)[0])
        for r in rows:
            ts = t_ph[r][dom[r]].astype(float)
            per_star[int(idx[r])] = (1.0 / max(s_c[r], S_FLOOR),
                                     int((ts < 0).sum()), int((ts >= 0).sum()), ts)
    return per_star, dict(n_files=len(files), n_stars=n_stars,
                          n_undecid_S=n_undecid_S, n_edge=n_edge,
                          n_ev_out_horizon=n_ev_out_horizon,
                          raw_p=raw_p, raw_f=raw_f)


def main(d_max=5.0):
    per_star, meta = collect(d_max)
    stars = list(per_star.values())
    if not stars:
        print("統制領域内イベントなし")
        return 2
    w = np.array([s[0] for s in stars])
    p_n = np.array([s[1] for s in stars], dtype=float)
    f_n = np.array([s[2] for s in stars], dtype=float)
    P, F = float((w * p_n).sum()), float((w * f_n).sum())
    A = (F - P) / (F + P)

    # 星単位ブートストラップ
    rng = np.random.default_rng(88)
    n = len(stars)
    boot_A = np.empty(N_BOOT)
    boot_b = np.empty(N_BOOT)
    t_mean = np.array([float(np.mean(s[3])) for s in stars])   # 星の代表時刻
    ev_w = w * (p_n + f_n)                                     # 星の重み付イベント量
    for k in range(N_BOOT):
        pick = rng.integers(0, n, n)
        Pk = float((w[pick] * p_n[pick]).sum())
        Fk = float((w[pick] * f_n[pick]).sum())
        boot_A[k] = (Fk - Pk) / max(Fk + Pk, 1e-12)
        boot_b[k] = (np.average(t_mean[pick], weights=ev_w[pick])
                     if ev_w[pick].sum() > 0 else 0.0)
    sA = float(np.std(boot_A))
    # 副統計量: 重み付き平均時刻 (トレンドの一次代理。0 が対称)
    tbar = float(np.average(t_mean, weights=ev_w))
    s_tbar = float(np.std(boot_b))

    raw_asym = (meta["raw_f"] - meta["raw_p"]) / max(meta["raw_f"] + meta["raw_p"], 1)

    print(f"== 定常性速報・修正版 (d<{d_max} pc, 統制領域=S≥{S_FLOOR}∧ホライズン内) ==")
    print(f"処理: {meta['n_files']} チャンク / {meta['n_stars']:,} 星 / "
          f"統制領域内の寄与星 {n}")
    print(f"判定不能会計: S欠損/floor未満 {meta['n_undecid_S']} 星 / "
          f"ホライズン外イベント {meta['n_ev_out_horizon']:,} 件 / 窓端 {meta['n_edge']:,} 件")
    print(f"主統計量 対称性 A = (F−P)/(F+P) = {A:+.4f} ± {sA:.4f} "
          f"→ |A|/σ = {abs(A) / sA:.2f}")
    print(f"副統計量 重み付き平均時刻 = {tbar:+.3f} ± {s_tbar:.3f} Myr")
    print(f"生カウント対称性 (伝播監視): {raw_asym:+.4f} "
          f"(P={meta['raw_p']:,} / F={meta['raw_f']:,})")
    verdict = abs(A) / sA < 3
    print(f"判定: {'PASS' if verdict else 'ANOMALY — 即停止・報告'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 5.0))
