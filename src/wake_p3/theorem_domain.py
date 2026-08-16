"""定理 C2 の仮定充足マップ(裁定ログ#13 裁定1 条件(i) — K_mix 憲章)

(R, T_s) 格子上で C2 の仮定(K_mix ≥ 20・Λ̄ ≤ 4・殻質量 q > 0)の充足を判定し、
三値定理レイヤ(C2 保証 / 定理沈黙 / 絶滅側定理なし)の土台を作る。

- 速度分布: クリーン母集団(bit5 除外・S≥floor)の太陽中心速さ分布を
  **等方化近似**で使用(C2 は等方 ν を仮定 — 実測は非等方(円盤運動学)であり、
  本マップは等方化の下での判定である旨を凡例に明記【近似の明示】)
- 殻選択: w₁ ≥ 20R/T_s(K_mix 条件)を満たす滑走殻 [w₁, 2w₁] から
  m₁ ∝ q·w₁ 最大の殻を選ぶ(∃殻 で判定)
- Λ̄(等方化): 密度(速さ) f(w)/(4πw²) の殻上 max を殻平均 q/V_shell で割った比
- m₁/p 係数: ρ_clean(IPW 重み付き数密度)· q · πR² · w₁ · T_s —
  最終地図で p(=f_set)を掛けて数値閾値帯 m ∈ [1.0, 1.3](E1)と比較する

実行: python3 src/wake_p3/theorem_domain.py
出力: data/p3/theorem_domain.npz + docs/phase3/01-kmix-charter-map.md
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
P3 = ROOT / "data" / "p3"
OUT = ROOT / "docs" / "phase3" / "01-kmix-charter-map.md"
K = 4.74047e-3
PC_PER_MYR = 1.02271
K0 = 20.0
LAM_BAR_MAX = 4.0


def clean_speed_distribution():
    from wake_data.icrs import icrs_to_helio_galactic
    cat = np.load(P2 / "catalog_ingested.npz")
    b5 = np.load(P2 / "quarantine_bit5.npz")["mask"]
    S = cat["s_completeness"]
    ok = (cat["parallax"] > 0) & ~b5 & np.isfinite(S) & (S >= S_FLOOR)
    pos, vel = icrs_to_helio_galactic(cat["ra"][ok], cat["dec"][ok],
                                      cat["parallax"][ok], cat["pmra"][ok],
                                      cat["pmdec"][ok], cat["radial_velocity"][ok])
    w = 1.0 / np.maximum(S[ok], S_FLOOR)
    speed = np.linalg.norm(vel, axis=1) * PC_PER_MYR   # pc/Myr
    # IPW 重み付き数密度 [pc^-3](100 pc 球 — カタログ枠)
    rho = w.sum() / (4.0 / 3.0 * np.pi * 100.0 ** 3)
    return speed, w, rho


def shell_stats(speed, wts, w1):
    """殻 [w1, 2w1] の質量比 q と等方化 Λ̄"""
    tot = wts.sum()
    m = (speed >= w1) & (speed < 2 * w1)
    q = wts[m].sum() / tot
    if q <= 0:
        return 0.0, np.inf
    # 等方化 Λ̄: 密度 f(w)/(4πw²) の殻上 max / 殻平均
    edges = np.linspace(w1, 2 * w1, 21)
    h, _ = np.histogram(speed[m], bins=edges, weights=wts[m])
    h = h / tot
    wmid = 0.5 * (edges[:-1] + edges[1:])
    dens = h / (4 * np.pi * wmid ** 2 * np.diff(edges))
    v_shell = 4.0 / 3.0 * np.pi * ((2 * w1) ** 3 - w1 ** 3)
    lam_bar = float(dens.max() / (q / v_shell)) if q > 0 else np.inf
    return float(q), lam_bar


def main():
    P3.mkdir(parents=True, exist_ok=True)
    speed, wts, rho = clean_speed_distribution()
    print(f"クリーン母集団: {len(speed):,} 星 / IPW密度 ρ = {rho:.4f} pc⁻³ / "
          f"速さ中央値 {np.median(speed):.1f} pc/Myr")

    R_grid = np.logspace(-1, 1, 41)         # 0.1–10 pc
    T_grid = np.logspace(-2, 2, 49)         # 0.01–100 Myr
    ok_map = np.zeros((len(R_grid), len(T_grid)), bool)
    m1_over_p = np.zeros_like(ok_map, float)
    best_w1 = np.zeros_like(ok_map, float)
    lam_bar_map = np.full_like(ok_map, np.nan, float)
    w_max = np.percentile(speed, 99.5)
    for i, R in enumerate(R_grid):
        for j, Ts in enumerate(T_grid):
            w1_min = K0 * R / Ts
            if w1_min > w_max / 2:
                continue
            w1_cands = np.geomspace(max(w1_min, 1.0), w_max / 2, 24)
            best = None
            for w1 in w1_cands:
                q, lb = shell_stats(speed, wts, w1)
                if q <= 1e-4 or lb > LAM_BAR_MAX:
                    continue
                m1p = rho * q * np.pi * R ** 2 * w1 * Ts
                if best is None or m1p > best[0]:
                    best = (m1p, w1, lb)
            if best:
                ok_map[i, j] = True
                m1_over_p[i, j], best_w1[i, j], lam_bar_map[i, j] = best
    np.savez_compressed(P3 / "theorem_domain.npz", R=R_grid, T=T_grid,
                        assumptions_ok=ok_map, m1_over_p=m1_over_p,
                        best_w1=best_w1, lam_bar=lam_bar_map, rho=rho)

    lines = ["# K_mix・Λ̄ 充足マップ(裁定ログ#13 条件(i) — 三値定理レイヤの土台)",
             "",
             "> C2 の仮定充足を (R, T_s) 格子で判定。**等方化近似**(C2 は等方 ν を"
             "仮定・実測は非等方)の下での判定である。実行: "
             "`python3 src/wake_p3/theorem_domain.py`", "",
             f"クリーン母集団: {len(speed):,} 星 / IPW 密度 ρ = {rho:.4f} pc⁻³ / "
             f"速さ中央値 {np.median(speed):.1f} pc/Myr "
             f"({np.median(speed)/PC_PER_MYR:.1f} km/s)", "",
             "## CN19 ランドマーク点の判定", "",
             "| R=d_p [pc] | T_s [Myr] | 仮定充足 | 最良 w₁ [pc/Myr] | Λ̄ | "
             "m₁/p | 判定(p=1 で m 帯 1.0–1.3 と比較) |", "|---|---|---|---|---|---|---|"]
    landmarks = [(3.07, 0.1), (3.07, 0.3), (3.07, 1.0), (3.07, 3.0), (3.07, 10.0),
                 (1.0, 0.3), (1.0, 1.0), (1.0, 3.0), (0.5, 1.0), (0.5, 3.0),
                 (10.0, 10.0)]
    for R, Ts in landmarks:
        i = int(np.argmin(np.abs(R_grid - R)))
        j = int(np.argmin(np.abs(T_grid - Ts)))
        if ok_map[i, j]:
            m1p = m1_over_p[i, j]
            verdict = ("**C2 保証域**(m₁/p > 1.3)" if m1p > 1.3
                       else "仮定充足・m 不足(数値閾値下 — 定理は生存を保証せず)")
            lines.append(f"| {R:.2f} | {Ts:.1f} | ✓ | {best_w1[i,j]:.0f} | "
                         f"{lam_bar_map[i,j]:.1f} | {m1p:.2g} | {verdict} |")
        else:
            lines.append(f"| {R:.2f} | {Ts:.1f} | ✗ | — | — | — | "
                         f"**定理沈黙**(K_mix/Λ̄ 域外) |")
    frac = ok_map.mean()
    # CN19 L 軸走査域 (T_s 0.1–1, R=3.07) の充足率
    jr = int(np.argmin(np.abs(R_grid - 3.07)))
    jt = (T_grid >= 0.1) & (T_grid <= 1.0)
    cn19_frac = ok_map[jr, jt].mean()
    lines += ["",
              f"格子全体の仮定充足率: {frac:.1%} / **CN19 標準域(R=3.07 pc, "
              f"T_s ∈ [0.1, 1] Myr)の充足率: {cn19_frac:.1%}**"
              "(裁定#13 の認定どおり狭い/ゼロであることの定量確認)", "",
              "## 三値定理レイヤの凡例(裁定ログ#13 指定)", "",
              "1. **C2 保証(生存可能)**: 仮定充足(K_mix≥20 ∧ Λ̄≤4 ∧ q>0 —"
              " 等方化近似の下)∧ m = p·λT_s 系が数値閾値帯 m ≈ 1.0–1.3(E1)超",
              "2. **定理沈黙(仮定域外)**: 上記不成立 — 判定材料は数値閾値のみ"
              "である旨を凡例に明記",
              "3. **絶滅側は全域で定理なし**: 定理 A は SIR 変種のみ・完全モデルの"
              "絶滅閾値は開放問題(本プロジェクト自身の反証命題)。「生存不能」を"
              "定理で支えることは全域で不可能 — 数値・平均場のみ", "",
              "注: C₀ は非明示定数(存在定理)であり、保証域の m 境界は数値閾値"
              "(E1: 1.0–1.3)を運用値として使う。等方化近似は凡例に常時表示。", ""]
    OUT.write_text("\n".join(lines))
    print(f"充足率: 全体 {frac:.1%} / CN19 標準域 {cn19_frac:.1%}")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
