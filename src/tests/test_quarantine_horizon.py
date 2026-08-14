"""検疫 (裁定5) と個別ホライズン (裁定3) の適用テスト

検証内容:
1. 各検疫ビットの発火と WD の DR3 RV 不採用処理
2. bit3 は「要手動審査」であって個別イベント判定から除外されないこと
3. HVS ホワイトリストによる bit3 解除
4. rv_error > 20 km/s は個別イベント判定から除外・率には寄与 (裁定5 追加基準)
5. 検疫会計 (QuarantineReport) がメタデータに常時添付されること (承認条件)
6. ホライズンが既定 R×0.5 と感度 R×1 の両方を常時出力し凡例配管を持つこと (裁定3)
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data import DummyCatalogProvider
from wake_data.quarantine import apply_quarantine
from wake_data.horizon import horizons, event_eligibility, LEGEND_NOTE
from wake_data.schema import (QUARANTINE_WD_RV, QUARANTINE_RUWE,
                              QUARANTINE_PM_SN, QUARANTINE_RV_OUTLIER)


def main():
    failures = []
    cat = DummyCatalogProvider(1000, "v1", seed=5).load()
    d = cat.data
    d["ruwe"] = np.full(1000, 1.0)

    # 注入: 事例を作る
    rv_ok = np.flatnonzero(~np.isnan(d["radial_velocity"]))
    i_wd, i_ruwe, i_pmsn, i_hvs, i_hvs_wl, i_bigerr = rv_ok[:6]
    is_wd = np.zeros(1000, dtype=bool)
    is_wd[i_wd] = True
    d["ruwe"][i_ruwe] = 2.0
    d["pmra"][i_pmsn], d["pmdec"][i_pmsn] = 0.1, 0.1          # S/N << 5
    d["radial_velocity"][i_hvs] = 600.0                        # 外れ値 (未確認)
    d["radial_velocity"][i_hvs_wl] = -700.0                    # 確認済み HVS
    d["rv_error"][i_bigerr] = 25.0                             # > 20 km/s
    wl = {int(d["source_id"][i_hvs_wl])}

    qcat, rep = apply_quarantine(cat, is_wd=is_wd, whitelist_ids=wl)
    f = qcat.data["quarantine_flags"]

    # 1. ビット発火と WD RV 不採用
    if not (f[i_wd] & QUARANTINE_WD_RV) or not np.isnan(qcat.data["radial_velocity"][i_wd]):
        failures.append("bit0: WD の DR3 RV が不採用になっていない")
    if not (f[i_ruwe] & QUARANTINE_RUWE):
        failures.append("bit1: RUWE ≥ 1.4 が発火しない")
    if not (f[i_pmsn] & QUARANTINE_PM_SN):
        failures.append("bit2: PM S/N < 5 が発火しない")
    if not (f[i_hvs] & QUARANTINE_RV_OUTLIER):
        failures.append("bit3: RV 外れ値が発火しない")
    print(f"[1] ビット発火 OK (bit0/1/2/3 = {rep.n_bit_wd_rv}/{rep.n_bit_ruwe}/"
          f"{rep.n_bit_pm_sn}/{rep.n_bit_rv_outlier} 星)")

    # 2-3. bit3 は除外でない / ホワイトリスト解除
    if f[i_hvs_wl] & QUARANTINE_RV_OUTLIER:
        failures.append("ホワイトリストが bit3 を解除していない")
    hz = horizons(qcat.data, R_pc=5.0)
    elig = event_eligibility(qcat.data, f, t_abs_myr=0.5, hz=hz)
    if not elig[i_hvs]:
        failures.append("bit3 (要手動審査) の星が個別イベント判定から除外されている")
    if elig[i_ruwe] or elig[i_pmsn]:
        failures.append("bit1/bit2 の星が個別イベント判定に残っている")
    print(f"[2-3] bit3=非除外・ホワイトリスト解除 OK (解除 {rep.n_whitelisted} 星)")

    # 4. rv_error > 20 km/s
    if elig[i_bigerr]:
        failures.append("rv_error > 20 km/s の星が個別イベント判定に残っている")
    rate_mask = ~np.isnan(qcat.data["radial_velocity"])   # 率への寄与は RV 保有星全体
    if not rate_mask[i_bigerr]:
        failures.append("rv_error > 20 km/s の星が率からも消えている")
    print("[4] rv_error>20: 個別イベント除外・率には寄与 OK")

    # 5. 会計のメタデータ添付
    q = qcat.meta.get("quarantine", {})
    if not q or "legend_note" not in q or q["counts"]["bit2_pm_sn"] != rep.n_bit_pm_sn:
        failures.append("検疫会計がメタデータに正しく添付されていない")
    print(f"[5] 検疫会計メタデータ OK (個別判定不能に合流 {rep.n_event_ineligible} 星)")

    # 6. ホライズン両方出力 + 凡例
    if hz["d_th_default_pc"] != 2.5 or hz["d_th_sensitivity_pc"] != 5.0:
        failures.append("ホライズンの既定 R×0.5 / 感度 R×1 が正しくない")
    if hz["legend_note"] != LEGEND_NOTE:
        failures.append("ホライズンの凡例配管がない")
    if not np.all(hz["t_h_default_myr"] <= hz["t_h_sensitivity_myr"]):
        failures.append("既定ホライズンが感度ホライズンより長い星がある")
    print("[6] ホライズン両方出力・凡例配管 OK")

    if failures:
        print("\nFAIL:", *failures, sep="\n  - ")
        return 1
    print("\n検疫・ホライズンテスト: 全項目 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
