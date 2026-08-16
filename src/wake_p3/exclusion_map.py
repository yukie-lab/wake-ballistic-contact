"""排除地図 v1 生成器(Phase 3 — 裁定ログ#13 の三条件を実装)

構成:
- 物理率レイヤ: クリーン λ(R) 主計算(**下界 = 安全側**: 探査機は Gaia 選択関数に
  従わないため λ 過小 →「訪問済みのはず」領域が縮む)+ 橋 ×5.3 のモデル明示
  参考レイヤ + suspect 込み両建て
- λ(R): 実測アンカー {1,2,5} pc の区分冪補間。R<1 は d² 外挿(フラグ)、
  R>5 は判定不能。λ は**太陽の実測到来率**(星平均ではない — 条件文注記)
- 訪問数: N_vis(f,R,L,v) = f · λ(R) · ⟨p̂⟩/f · T_eff、T_eff = max(0, 10 − τ)、
  τ = R/(v·1.02271)。τ ≥ 10 は判定不能(支持窓内に到達不能)
- マーク場: 依存性注入(wake_mark インターフェースのみ)。(b) 前線族は
  到来寄与星の実運動学で ⟨p_settled⟩ を評価(K(v;n̂) 相関を実データで)
- 定理レイヤ: 三値(C2 保証 / 定理沈黙 / 絶滅側は全域定理なし)—
  theorem_domain.npz(等方化近似の明示)
- 塗り分け: N_vis > 3 →「訪問済みのはず」(沈黙なら 95% で棄却)/
  N_vis ≤ 3 →「沈黙と整合」/ 判定不能(R>5・τ≥10・対象母集団=S≥floor)
- 感度(裁定3): 前線方向 48 点 × 事前分布2種(一様球/銀河中心バイアス)。
  >10% は「方向依存性の発見」として報告(不合格ではない)

実行: python3 src/wake_p3/exclusion_map.py
出力: data/p3/exclusion_map_v1.json + docs/phase3/02-exclusion-map-v1.md
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_mark import make_field

ROOT = pathlib.Path(__file__).resolve().parents[2]
P3 = ROOT / "data" / "p3"
OUT_JSON = P3 / "exclusion_map_v1.json"
OUT_MD = ROOT / "docs" / "phase3" / "02-exclusion-map-v1.md"
PC_PER_MYR = 1.02271
T_SUPP = 10.0
N_CRIT = 3.0          # 沈黙棄却の閾値(P(0|N)=e^-3 < 5%)
BRIDGE = 5.3          # 二帳簿の橋(母集団: S≥floor → 全恒星の実測係数)


def lam_model(R, anchors):
    """区分冪補間。R<1: d² 外挿(flag=1)、R>5: NaN(判定不能)"""
    Rs = np.array([1.0, 2.0, 5.0])
    Ls = np.array(anchors)
    R = np.asarray(R, float)
    out = np.full_like(R, np.nan)
    flag = np.zeros_like(R, int)
    m12 = np.log(Ls[1] / Ls[0]) / np.log(2.0)
    m25 = np.log(Ls[2] / Ls[1]) / np.log(2.5)
    lo = R < 1.0
    out[lo] = Ls[0] * R[lo] ** 2.0
    flag[lo] = 1
    a = (R >= 1.0) & (R < 2.0)
    out[a] = Ls[0] * R[a] ** m12
    b = (R >= 2.0) & (R <= 5.0)
    out[b] = Ls[1] * (R[b] / 2.0) ** m25
    flag[R > 5.0] = 2
    return out, flag


def fib_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.sin(phi) * np.cos(theta),
                     np.sin(phi) * np.sin(theta), np.cos(phi)], axis=1)


def main():
    ak = np.load(P3 / "arrival_kinematics.npz")
    td = np.load(P3 / "theorem_domain.npz")
    anchors_clean = [float(ak["lam1"]), float(ak["lam2"]), float(ak["lam5"])]
    anchors_susp = [32.75, 128.92, 433.10]     # カタログ v1 両建てブロック
    ci1 = ak["ci1"]

    R_grid = np.logspace(-1, 1, 41)
    v_grid = np.array([3.0, 10.0, 30.0, 100.0, 300.0])   # km/s(探査機速度軸)
    lamR, flagR = lam_model(R_grid, anchors_clean)
    lamR_s, _ = lam_model(R_grid, anchors_susp)
    tau = R_grid[:, None] / (v_grid[None, :] * PC_PER_MYR)     # Myr
    T_eff = np.maximum(0.0, T_SUPP - tau)

    # (b) 前線族: 方向感度(48 点 × 事前2種)— 到来寄与星の実運動学で ⟨p⟩/f
    vel = ak["vel_kms"]
    w5 = ak["c5"]                    # λ@5pc への寄与重み(到来の代表)
    dirs = fib_sphere(48)
    ratios = []
    for n_hat in dirs:
        fld = make_field("front", f=1.0, n_hat=n_hat, t0_myr=0.0,
                         v_front_pc_myr=10.0, delta_pc=10.0, beta=2.5,
                         sigma_v_kms=30.0)
        p = fld.p_settled(np.zeros((len(vel), 3)), vel, 0.0)
        ratios.append(float(np.average(p, weights=w5)))
    ratios = np.array(ratios)        # s₀=0(前線が太陽位置)での ⟨p⟩/f
    # 事前分布: 一様球 / 銀河中心バイアス(GC 方向 = +x、重み ∝ 1+2·max(0,n̂·x̂))
    w_uni = np.ones(48) / 48
    gc = np.array([1.0, 0.0, 0.0])
    w_gc = 1.0 + 2.0 * np.maximum(0.0, dirs @ gc)
    w_gc = w_gc / w_gc.sum()
    mean_uni = float(ratios @ w_uni)
    mean_gc = float(ratios @ w_gc)
    spread = float((ratios.max() - ratios.min()) / max(ratios.mean(), 1e-9))
    prior_shift = abs(mean_gc - mean_uni) / max(mean_uni, 1e-9)

    # 定理レイヤ(f ≡ p — 裁定#12/#13 の写像)
    thm = dict(R=td["R"].tolist(), T=td["T"].tolist(),
               assumptions_ok=td["assumptions_ok"].astype(int).tolist(),
               m1_over_p=np.round(td["m1_over_p"], 4).tolist())

    doc = {
        "schema_version": "exclusion-map-v1",
        "generated": "2026-08-17",
        "conditional_statement_template": (
            "FGK+早中期M(S≥0.05)の完備性補正後・太陽の実測到来率(星平均では"
            "ない)の下で: 入植割合 f・航続 R・寿命 L・探査機速度 v の領域が"
            "N_vis = f·⟨p̂⟩/f·λ(R)·max(0, 10−R/v) > 3 を満たすなら、過去 10 Myr に"
            "太陽系は訪問済みのはず(沈黙は 95% で棄却)。N_vis ≤ 3 は沈黙と整合。"
            "R > 5 pc・τ ≥ 10 Myr・晩期 M 等 S<floor の寄与は判定不能。"),
        "conditional_statement_template_en": (
            "Under the completeness-corrected arrival rate of the FGK + "
            "early-to-mid M population (S≥0.05), measured for the Sun (not a "
            "stellar average): if the region of settled fraction f, probe "
            "range R, lifetime L, and probe speed v satisfies "
            "N_vis = f·⟨p̂⟩/f·λ(R)·max(0, 10−R/v) > 3, the solar system "
            "should have been visited within the past 10 Myr (silence "
            "rejected at 95%). N_vis ≤ 3 is consistent with silence. "
            "Contributions from R > 5 pc, τ ≥ 10 Myr, and S<floor "
            "populations (late M, etc.) are undecidable."),
        "safety_note": "クリーン λ は物理的遭遇率の下界(探査機は Gaia 選択関数に"
                       "従わない)→「訪問済みのはず」領域が縮む = 主張は安全側",
        "safety_note_en": ("The clean λ is a lower bound on the physical "
                           "encounter rate (probes do not obey the Gaia "
                           "selection function) → the 'should have been "
                           "visited' region shrinks = claims are "
                           "conservative"),
        "n_crit_convention": "N_vis = f·⟨p̂⟩/f·λ(R)·T_eff ≥ 3 ⇔ "
                             "P(≥1 訪問) = 1−e^{−N} ≥ 95%(Poisson 規約 — "
                             "裁定ログ#14 付帯1)",
        "axes": {"R_pc": R_grid.tolist(), "v_kms": v_grid.tolist(),
                 "f": "連続(N_vis 線形 — f* 境界で表現)",
                 "L_myr": "定理レイヤの T_s 軸(訪問数 v1 は L 非依存 — 支持窓 10 Myr)"},
        "rate_layers": {
            "clean_primary": {"anchors_1_2_5_pc": anchors_clean,
                              "lam1_ci95": [float(ci1[0]), float(ci1[1])],
                              "lambda_R": [None if not np.isfinite(x) else x
                                           for x in np.round(lamR, 4)],  # flag=2 域は null(NaN 禁止)
                              "flags": flagR.tolist(),
                              "flag_legend": {"0": "実測支持", "1": "d²外挿",
                                              "2": "判定不能(R>5)"}},
            "bridge_reference": {"factor": BRIDGE,
                                 "model_note": "全恒星母集団への実測橋(モデル明示・"
                                               "参考レイヤ — 06-ctd-reference)"},
            "with_suspect_dual": {"anchors_1_2_5_pc": anchors_susp,
                                  "note": "bit5 込み両建て(裁定#11)"}},
        "visit_layer": {"T_eff_matrix_RxV": np.round(T_eff, 3).tolist(),
                        "N_crit": N_CRIT,
                        "f_star_boundary": "f* = N_crit/(⟨p̂⟩/f·λ(R)·T_eff) — "
                                           "f > f* が『訪問済みのはず』"},
        "map_version": "1.0.1",
        "changelog": ["1.0.1 (2026-08-17): E9 実測較正の (c) 族許容域レイヤへの"
                      "波及(裁定ログ#15 付帯1)— C2 保証の数値閾値を等方較正 1.3 "
                      "から実測 ν 較正帯の保守端 2.0 へ(保証域が縮む = 保守方向)",
                      "1.0.0 (2026-08-17): 初版"],
        "theorem_layer": {"legend": ["C2保証(仮定充足∧p·(m1/p)>2.0 — E9 実測"
                                     "較正帯 1.5–2.0 の保守端)",
                                     "定理沈黙(仮定域外 — 判定材料は数値閾値のみ)",
                                     "絶滅側は全域で定理なし(数値・平均場のみ)"],
                          "numeric_threshold_note": "数値閾値帯: 等方較正 m≈1.0–1.3"
                              "(E1)/ **実測 ν では m≈1.5–2.0 に上方シフト**"
                              "(E9 — 非等方性・重い裾は入植を困難にする方向。"
                              "裁定ログ#14 付帯2)",
                          "isotropization_note": "等方化近似の下での判定(実測 ν は非等方)",
                          "legend_en": ["C2-guaranteed (assumptions satisfied "
                                        "∧ p·(m1/p)>2.0 — conservative end of "
                                        "the E9 measured-ν band 1.5–2.0)",
                                        "Theorem-silent (outside the "
                                        "assumption domain — only numerical "
                                        "thresholds inform)",
                                        "No extinction-side theorem anywhere "
                                        "(numerics and mean-field only)"],
                          "numeric_threshold_note_en": (
                              "Numerical threshold band: isotropic "
                              "calibration m≈1.0–1.3 (E1) / shifts upward to "
                              "m≈1.5–2.0 under the measured ν (E9 — "
                              "anisotropy and heavy tails hinder settlement; "
                              "ruling #14 rider 2)"),
                          "isotropization_note_en": (
                              "Judged under the isotropization approximation "
                              "(the measured ν is anisotropic)"),
                          "domain": thm},
        "front_direction_sensitivity": {
            "beta": 2.5, "s0": 0.0, "n_dirs": 48,
            "mean_ratio_uniform": round(mean_uni, 4),
            "mean_ratio_gc_bias": round(mean_gc, 4),
            "direction_spread": round(spread, 4),
            "prior_shift": round(prior_shift, 4),
            "verdict": ("事前分布に頑健(<10%)" if prior_shift < 0.10
                        else "方向依存性の発見(>10% — Wright+21 接続の科学的報告)")},
        "boundary_mc_convergence": {
            "lam1_ci95": [float(ci1[0]), float(ci1[1])],
            "f_star_shift_at_1pc": "境界 f* は λ に反比例 — CI95 で "
                                   f"×{anchors_clean[0]/float(ci1[1]):.2f}〜"
                                   f"×{anchors_clean[0]/float(ci1[0]):.2f}",
        },
    }
    P3.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1,
                                   allow_nan=False))  # NaN 混入は生成時に即エラー

    # 代表点の f* 表(md)
    lines = ["# 排除地図 v1(裁定ログ#13 三条件実装)", "",
             "> JSON: `data/p3/exclusion_map_v1.json` / 実行: "
             "`python3 src/wake_p3/exclusion_map.py`", "",
             f"- 条件文テンプレート・安全側注記・太陽λ注記は JSON メタデータに収録",
             f"- 前線方向感度: 一様球 ⟨p⟩/f = {mean_uni:.3f} / GC バイアス "
             f"{mean_gc:.3f} / 事前分布シフト {prior_shift:.1%} → "
             f"{doc['front_direction_sensitivity']['verdict']}",
             f"- 方向スプレッド(48点): {spread:.1%}(K(v;n̂) β=2.5 前線レジーム)", "",
             "## 代表点の f* 境界(クリーン主計算、(a) 定数場)", "",
             "| R [pc] | v [km/s] | λ(R) | T_eff | f*(N=3) | 判定 |",
             "|---|---|---|---|---|---|"]
    for R in (0.5, 1.0, 3.07, 4.7):
        i = int(np.argmin(np.abs(R_grid - R)))
        for v in (10.0, 100.0):
            j = int(np.argmin(np.abs(v_grid - v)))
            lam = lamR[i]
            te = T_eff[i, j]
            if flagR[i] == 2 or te <= 0:
                lines.append(f"| {R} | {v:.0f} | — | {te:.1f} | — | 判定不能 |")
                continue
            fstar = N_CRIT / (lam * te)
            note = "(d²外挿)" if flagR[i] == 1 else ""
            lines.append(f"| {R} | {v:.0f} | {lam:.1f} | {te:.1f} | "
                         f"{fstar:.2e}{note} | f>f* で訪問済みのはず |")
    lines += ["", "橋 ×5.3 参考レイヤでは f* が 1/5.3。suspect 込み両建ては JSON 参照。",
              "定理レイヤ: 01-kmix-charter-map.md(CN19 標準域は定理沈黙)。", ""]
    OUT_MD.write_text("\n".join(lines))
    print(f"→ {OUT_JSON.name} / {OUT_MD.name}")
    print(f"感度: 一様 {mean_uni:.3f} / GC {mean_gc:.3f} / シフト {prior_shift:.1%} / "
          f"方向スプレッド {spread:.1%}")


if __name__ == "__main__":
    main()
