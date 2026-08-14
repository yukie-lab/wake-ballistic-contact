"""個別ホライズン閾値 d_threshold の感度予備測定 (裁定記録第三部・冒頭裁定3の準備)

モデル (憲法第5条5項の根拠則):
  σ_pos(t) ≈ sqrt(σ_x0² + (σ_v t)²),  σ_v ≈ rv_error (1 km/s ≈ 1.02 pc/Myr)
  横断方向 σ_vt = 4.74 σ_pm d は太陽近傍 (<100 pc, σ_pm~0.05 mas/yr) で
  ~10⁻³ km/s 級であり無視できる (含めても結果は不変)。
  個別ホライズン t_h(i) = d_threshold / σ_v(i)

rv_error は【実 DR3 分布】(gaiadr3.gaia_source の random_index 一様サンプル
約100万星、data/raw/dr3_rv_error_sample.parquet — 裁定3の差替条件を充足)。
サンプルが無い環境では合成分布 (中央値1.3 km/s) にフォールバックし警告する。
"""

import pathlib

import numpy as np

PC_PER_MYR = 1.02271

_sample = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw" / "dr3_rv_error_sample.parquet"
if _sample.exists():
    import pandas as pd
    rv_error = pd.read_parquet(_sample)["radial_velocity_error"].to_numpy(float)
    rv_error = rv_error[np.isfinite(rv_error)]
    print(f"実 DR3 分布を使用 ({len(rv_error):,} 星)")
else:
    print("警告: 実 DR3 サンプルなし — 合成分布にフォールバック")
    rng = np.random.default_rng(2)
    rv_error = rng.lognormal(np.log(1.3), 0.8, 200_000)
sigma_v = rv_error * PC_PER_MYR                     # pc/Myr

print("rv_error 分布: 中央値 %.2f km/s / 10%%点 %.2f / 90%%点 %.2f" % (
    np.median(rv_error), *np.percentile(rv_error, [10, 90])))
print()
print("d_threshold ごとの個別ホライズン t_h = d_th/σ_v の分布と、")
print("「t_h ≥ T」を満たす星の割合 (= 窓 T で個別判定可能な星の割合):")
print()
hdr = f"{'d_th [pc]':>10} {'t_h中央値':>10} " + " ".join(
    f"{'≥'+str(T)+'Myr':>8}" for T in (2, 6, 10))
print(hdr)
for d_th, label in [(0.5, "R=1 の 0.5倍"), (1.0, "R=1 の 1倍"),
                    (1.0, "R=2 の 0.5倍"), (2.0, "R=2 の 1倍"),
                    (2.5, "R=5 の 0.5倍"), (5.0, "R=5 の 1倍")]:
    t_h = d_th / sigma_v
    fr = [np.mean(t_h >= T) for T in (2, 6, 10)]
    print(f"{d_th:10.1f} {np.median(t_h):10.2f} "
          + " ".join(f"{f:8.1%}" for f in fr) + f"   ({label})")

print("""
読み方: 例えば R=1 pc の接近判定を閾値 d_th=1 pc で守る場合、±6 Myr で
個別判定可能なのは rv_error ≤ 0.16 km/s の星に限られる。個別ホライズンは
「星ごとの窓」であって全カタログの窓ではない — 窓外縁の星は誤差 MC の
アンサンブルとしては到来統計に寄与し続け、個別イベントとしては「判定不能」
に落ちる (憲法第5条6項)。d_th の選択は「個別イベントカタログの純度」と
「判定可能星の数」のトレードオフである。""")
