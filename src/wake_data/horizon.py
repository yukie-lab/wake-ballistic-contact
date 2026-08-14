"""個別ホライズン (憲法第5条5項 / Phase 1 冒頭裁定・裁定3)

裁定3 (2026-08-14, 裁定ログ#4):
- 既定 d_th = R×0.5、感度 d_th = R×1、**両方常時出力**
- 本地図は既定で塗り、R×1 帯は付録・監査用
- 凡例配管 (承認条件): LEGEND_NOTE を地図・カタログの全出力メタデータに含めること
- rv_error は実 DR3 ヒストグラムへ差し替え (取込時に本モジュールは変更不要)

根拠則: σ_pos(t) ≈ σ_v·t、σ_v ≈ rv_error (1 km/s ≈ 1.02 pc/Myr)。
横断方向 (固有運動誤差) の寄与も式には含める (太陽近傍では ~10⁻³ km/s 級)。
"""

import numpy as np

PC_PER_MYR = 1.02271          # 1 km/s = 1.02271 pc/Myr
HORIZON_DEFAULT_FACTOR = 0.5  # 裁定3: 既定 R×0.5
HORIZON_SENS_FACTOR = 1.0     # 裁定3: 感度 R×1 (付録・監査用)
RV_ERROR_MAX_FOR_EVENTS = 20.0  # km/s。裁定5追加基準: 超過は個別イベント判定から除外
RULING_REF = "Phase1冒頭裁定 裁定3/裁定5 (2026-08-14, 裁定ログ#4)"

LEGEND_NOTE = (
    "個別ホライズン外・窓外の星も、到来『率』には誤差モンテカルロの"
    "アンサンブルとして寄与し続ける。『判定不能』となるのは個別イベントの"
    "同定のみである (憲法第5条5-6項、Phase 1 冒頭裁定・裁定3)。"
)


def sigma_v_pc_per_myr(data: dict) -> np.ndarray:
    """星ごとの速度不確かさ [pc/Myr]。RV 欠損は inf (個別判定不能)。"""
    rv_err = np.asarray(data["rv_error"], dtype=float)
    # 横断成分: σ_vt [km/s] = 4.74e-3 × σ_pm [mas/yr] × d [pc]
    d_pc = 1000.0 / np.maximum(np.asarray(data["parallax"], dtype=float), 1e-6)
    pm_err = np.hypot(np.asarray(data["pmra_error"], dtype=float),
                      np.asarray(data["pmdec_error"], dtype=float))
    sig_t = 4.74e-3 * pm_err * d_pc
    sig_kms = np.sqrt(np.where(np.isnan(rv_err), np.inf, rv_err) ** 2 + sig_t ** 2)
    return sig_kms * PC_PER_MYR


def horizons(data: dict, R_pc: float) -> dict:
    """接近半径 R に対する個別ホライズン t_h = d_th/σ_v [Myr] を
    既定 (R×0.5) と感度 (R×1) の両方で返す (裁定3: 両方常時出力)。"""
    sv = sigma_v_pc_per_myr(data)
    out = {
        "R_pc": R_pc,
        "d_th_default_pc": R_pc * HORIZON_DEFAULT_FACTOR,
        "t_h_default_myr": R_pc * HORIZON_DEFAULT_FACTOR / sv,
        "d_th_sensitivity_pc": R_pc * HORIZON_SENS_FACTOR,
        "t_h_sensitivity_myr": R_pc * HORIZON_SENS_FACTOR / sv,
        "legend_note": LEGEND_NOTE,
        "ruling": RULING_REF,
    }
    return out


def event_eligibility(data: dict, quarantine_flags: np.ndarray,
                      t_abs_myr, hz: dict, band: str = "default") -> np.ndarray:
    """時刻 |t| の個別イベント判定に使える星のマスク。

    条件: (i) 個別ホライズン内、(ii) rv_error ≤ 20 km/s (裁定5追加基準)、
    (iii) 検疫 bit0-2 が立っていない (bit3 要手動審査は除外**しない** — 裁定5)。
    落ちた星は「判定不能」会計に合流する (率への寄与は落とさない)。
    """
    from .schema import QUARANTINE_WD_RV, QUARANTINE_RUWE, QUARANTINE_PM_SN
    t_h = hz[f"t_h_{band}_myr"]
    rv_err = np.asarray(data["rv_error"], dtype=float)
    excl_bits = QUARANTINE_WD_RV | QUARANTINE_RUWE | QUARANTINE_PM_SN
    return ((t_h >= np.abs(t_abs_myr))
            & ~np.isnan(rv_err) & (rv_err <= RV_ERROR_MAX_FOR_EVENTS)
            & ((np.asarray(quarantine_flags) & excl_bits) == 0))
