"""塊の寄与分解+既知移動群照合+接近超過の構造確認(裁定ログ#8 裁定5 本照合)

範囲ガード(02-clump-notes.md): 既知移動星団照合+λ(t) 寄与分解まで。
力学の深掘りは続編候補棚。

1. λ(t) 星単位寄与分解(統制領域・d<5・1 Myr ビン): 各ビンの上位寄与星と share。
   「真の塊」候補 = 上位2星以上が share≥10% かつ運動学的に共動
   (UVW 差 < 3 km/s ∧ 空間距離 < 30 pc)
2. 既知移動群照合: 主要近傍群の UVW 代表値との距離(< 3 km/s で候補)。
   ⚠ UVW 参照値は文献代表値(Gagné+2018 系)— 論文採録前に機械検証を通すこと
3. 接近超過(+2.1%: 28,434 vs 27,852)の構造確認: 太陽向点双極子との整合
   (向点方向の RV 符号の余弦依存 — 運動学起源なら構造ではない)

実行: python3 src/wake_p2/clump_analysis.py [--catalog-only]
出力: docs/phase2/08-clump-analysis.md
"""
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = ROOT / "docs" / "phase2" / "08-clump-analysis.md"
N_SURR = 2000

# 既知近傍移動群の UVW 代表値 [km/s](文献代表値 — 採録前に機械検証)
GROUPS = {
    "Hyades": (-42.0, -19.0, -1.0),
    "Coma Ber": (-2.3, -5.5, -1.8),
    "Ursa Major": (14.9, 1.0, -10.7),
    "Pleiades/LCC系": (-6.6, -24.4, -13.1),
    "beta Pic MG": (-10.9, -16.0, -9.2),
    "AB Dor MG": (-7.1, -27.2, -13.8),
    "TW Hya": (-9.9, -18.1, -4.5),
    "Carina-Near": (-25.2, -18.2, -2.2),
}


def catalog_level(cat, lines):
    """3. 接近超過の構造確認(カタログ水準 — MC 不要)"""
    from wake_data.icrs import icrs_to_helio_galactic
    ok = cat["parallax"] > 0
    pos, vel = icrs_to_helio_galactic(cat["ra"][ok], cat["dec"][ok],
                                      cat["parallax"][ok], cat["pmra"][ok],
                                      cat["pmdec"][ok], cat["radial_velocity"][ok])
    rv = cat["radial_velocity"][ok]
    n_app, n_rec = int((rv < 0).sum()), int((rv >= 0).sum())
    exc = (n_app - n_rec) / (n_app + n_rec)
    # 半径方向速度の運動学的期待: 太陽特異運動 (U,V,W)⊙ に対し、視線方向 r̂ の
    # 星の平均 RV = −(U,V,W)⊙·r̂(等方星場の反射運動)。符号超過の予測双極子:
    UVW_SUN = np.array([11.1, 12.24, 7.25])   # Schönrich+2010(代表値)
    rhat = pos / np.linalg.norm(pos, axis=1, keepdims=True)
    proj = rhat @ UVW_SUN
    # 向点半球(proj>0 = 太陽が向かう側)での接近割合
    ahead = proj > 0
    f_ahead = float((rv[ahead] < 0).mean())
    f_behind = float((rv[~ahead] < 0).mean())
    # 反射運動を差し引いた残差 RV での超過(2通り: 参照太陽運動 / 標本平均場)
    rv_res = rv + proj
    exc_res = float(((rv_res < 0).sum() - (rv_res >= 0).sum()) / len(rv_res))
    mean_uvw = vel.mean(axis=0)          # 標本平均(漸近ドリフト込みの実測平均場)
    proj_emp = rhat @ mean_uvw           # 星の平均 RV 予測 = r̂·(平均場)
    rv_res2 = rv - proj_emp
    exc_res2 = float(((rv_res2 < 0).sum() - (rv_res2 >= 0).sum()) / len(rv_res2))
    sig = 1.0 / np.sqrt(len(rv))         # 符号超過の二項 1σ
    lines += ["## 3. 接近超過(+2.1%)の構造確認(カタログ水準)", "",
              f"- 接近 {n_app:,} vs 後退 {n_rec:,}(超過 {exc:+.2%}、二項 1σ = "
              f"{sig:.2%})",
              f"- 向点半球の接近割合 {f_ahead:.1%} vs 反向点半球 {f_behind:.1%}"
              "(太陽運動の反射の教科書的双極子)",
              f"- 残差超過(参照太陽運動 Schönrich+10): {exc_res:+.2%}"
              f"({abs(exc_res)/sig:.1f}σ)",
              f"- 残差超過(**標本平均場** ({mean_uvw[0]:+.1f}, {mean_uvw[1]:+.1f}, "
              f"{mean_uvw[2]:+.1f}) km/s): **{exc_res2:+.2%}**"
              f"({abs(exc_res2)/sig:.1f}σ)", "",
              "判定: 標本平均場での残差が ~1σ 以内なら +2.1% は運動学的双極子"
              "(太陽運動+漸近ドリフト)で説明され空間構造ではない。"
              "有意に残るなら記録のみ(範囲ガード)。", ""]
    return pos, vel, ok


def mc_level(cat, pos, vel, ok, lines):
    """1–2. λ(t) 寄与分解と共動判定+既知群照合(新 MC 必要)"""
    from wake_data.horizon_eff import effective_horizons
    S = cat["s_completeness"]
    th, _ = effective_horizons(cat)             # 裁定ログ#11 裁定2
    gi_map = np.flatnonzero(ok)
    inv = -np.ones(len(ok), int)
    inv[gi_map] = np.arange(len(gi_map))
    bins = np.arange(-13, 13 + 1e-9, 1.0)
    hist = np.zeros(len(bins) - 1)
    contrib = {}      # (bin, star) -> w·n
    for f in sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz"))):
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        s_c, th_c = S[idx], th[idx]
        usable = np.isfinite(s_c) & (s_c >= S_FLOOR)
        w = np.where(usable, 1.0 / np.maximum(s_c, S_FLOOR), 0.0)
        m = (np.isfinite(t_ph) & ~edge & (d_ph < 5.0)
             & (np.abs(t_ph) <= th_c[:, None]) & (np.abs(t_ph) <= 13.0))
        r, c = np.nonzero(m)
        b = np.clip(np.digitize(t_ph[r, c], bins) - 1, 0, len(bins) - 2)
        for bi, ri in zip(b, r):
            key = (int(bi), int(idx[ri]))
            contrib[key] = contrib.get(key, 0.0) + w[ri]
        np.add.at(hist, b, w[r])
    hist /= N_SURR
    lines += ["## 1. λ(t) 星単位寄与分解(統制領域・d<5・1 Myr ビン)", "",
              "| ビン [Myr] | λ [/Myr] | top1 share | top2 share | 共動判定 |",
              "|---|---|---|---|---|"]
    clump_cands = []
    for bi in range(len(bins) - 1):
        tot = hist[bi] * N_SURR
        if tot <= 0:
            continue
        stars = sorted(((v, g) for (b_, g), v in contrib.items() if b_ == bi),
                       reverse=True)[:5]
        s1 = stars[0][0] / tot if stars else 0
        s2 = stars[1][0] / tot if len(stars) > 1 else 0
        comove = ""
        if len(stars) >= 2 and s2 >= 0.10:
            g1, g2 = inv[stars[0][1]], inv[stars[1][1]]
            if g1 >= 0 and g2 >= 0:
                dv = np.linalg.norm(vel[g1] - vel[g2])
                dx = np.linalg.norm(pos[g1] - pos[g2])
                comove = (f"ΔUVW={dv:.1f} km/s, Δx={dx:.0f} pc → "
                          + ("**共動候補**" if dv < 3 and dx < 30 else "独立"))
                if dv < 3 and dx < 30:
                    clump_cands.append((bins[bi], stars[0][1], stars[1][1]))
        lines.append(f"| [{bins[bi]:+.0f},{bins[bi+1]:+.0f}) | "
                     f"{hist[bi]:.1f} | {s1:.0%} | {s2:.0%} | {comove} |")
    lines.append("")
    # 2. 既知群照合(高寄与星の UVW)
    lines += ["## 2. 既知移動群照合(ビン top1 星の UVW — 文献代表値との距離)", "",
              "| star_idx | UVW [km/s] | 最近接群 | 距離 [km/s] |", "|---|---|---|---|"]
    tops = {}
    for (b_, g), v in contrib.items():
        if g not in tops or v > tops[g]:
            tops[g] = v
    top_stars = sorted(tops, key=lambda g: -tops[g])[:15]
    for g in top_stars:
        r_ = inv[g]
        if r_ < 0:
            continue
        uvw = vel[r_]
        dists = {k: float(np.linalg.norm(uvw - np.array(c))) for k, c in GROUPS.items()}
        best = min(dists, key=dists.get)
        mark = "**" if dists[best] < 3 else ""
        lines.append(f"| {g} | ({uvw[0]:+.1f}, {uvw[1]:+.1f}, {uvw[2]:+.1f}) | "
                     f"{mark}{best}{mark} | {dists[best]:.1f} |")
    lines += ["", "判定基準: 距離 < 3 km/s で群候補(→ 個別確認)。"
              "UVW 参照値は文献代表値のため、候補が出た場合は採録前に"
              "参照値の機械検証を通す。", ""]


def main():
    cat = np.load(P2 / "catalog_ingested.npz")
    lines = ["# 塊の寄与分解+既知移動群照合+接近超過(裁定ログ#8 裁定5 本照合)",
             "", "> 範囲ガード: 照合と分解まで(力学深掘りは続編棚)。実行: "
             "`python3 src/wake_p2/clump_analysis.py`", ""]
    pos, vel, ok = catalog_level(cat, lines)
    if "--catalog-only" not in sys.argv:
        mc_level(cat, pos, vel, ok, lines)
    OUT.write_text("\n".join(lines))
    print("\n".join(lines[:20]))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
