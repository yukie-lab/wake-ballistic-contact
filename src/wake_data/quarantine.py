"""データ検疫 (Phase 1 冒頭裁定・裁定5、2026-08-14 固定)

ビット定義 (schema.QUARANTINE_*):
- bit0 WD_RV:      白色矮星の DR3 RV は不採用 (RV パイプラインに WD テンプレートなし)
- bit1 RUWE:       RUWE ≥ 1.4
- bit2 PM_SN:      固有運動 S/N < 5 (HD 7977 型の未解決連星疑いを捕捉)
- bit3 RV_OUTLIER: |RV| > 550 km/s (太陽近傍の銀河脱出速度水準) —
                   **要手動審査フラグであって除外ではない** (裁定5)。
                   確認済み超高速度星 (HVS) はホワイトリストで bit3 を解除する。
                   本物の HVS を無言で捨てると「速い来訪者ほど検疫される」
                   最悪の選択バイアスになるため。

構造的承認条件 (裁定5): 検疫された星は無言で消さず「判定不能」会計に合流させる。
除外数・ビット別内訳を地図とカタログのメタデータに常時報告する (QuarantineReport)。
憲法第5条6項の規律は検疫にも適用される。

追加基準 rv_error > 20 km/s (個別イベント判定から除外・率には寄与) は
horizon.event_eligibility() が受け持つ。
"""

from dataclasses import dataclass, field

import numpy as np

from .catalog import StarCatalog
from .schema import (QUARANTINE_WD_RV, QUARANTINE_RUWE, QUARANTINE_PM_SN,
                     QUARANTINE_RV_OUTLIER)

RUWE_MAX = 1.4          # 裁定5 bit1
PM_SN_MIN = 5.0         # 裁定5 bit2
RV_ABS_MAX = 550.0      # km/s。裁定5 bit3 (要手動審査、除外ではない)
RULING_REF = "Phase1冒頭裁定 裁定5 (2026-08-14, 裁定ログ#4)"

LEGEND_NOTE = (
    "検疫された星は除外ではなく『判定不能』会計に合流する。bit3 (|RV|>550 km/s) は"
    "要手動審査フラグであり、確認済み超高速度星はホワイトリストにより解除される。"
    "検疫の除外数・内訳は本メタデータで常時報告される (Phase 1 冒頭裁定・裁定5)。"
)


@dataclass
class QuarantineReport:
    n_total: int
    n_bit_wd_rv: int
    n_bit_ruwe: int
    n_bit_pm_sn: int
    n_bit_rv_outlier: int      # 手動審査待ち (ホワイトリスト解除後の残数)
    n_whitelisted: int         # bit3 をホワイトリストで解除した数
    n_event_ineligible: int    # bit0-2 により個別イベント判定不能に合流した数
    ruwe_available: bool
    legend_note: str = LEGEND_NOTE
    ruling: str = RULING_REF

    def as_metadata(self) -> dict:
        """地図・カタログ出力のメタデータに常時添付する辞書 (裁定5 承認条件)。"""
        return {
            "quarantine": {
                "n_total": self.n_total,
                "counts": {
                    "bit0_wd_rv": self.n_bit_wd_rv,
                    "bit1_ruwe": self.n_bit_ruwe,
                    "bit2_pm_sn": self.n_bit_pm_sn,
                    "bit3_rv_outlier_manual_review": self.n_bit_rv_outlier,
                },
                "n_whitelisted_hvs": self.n_whitelisted,
                "n_event_ineligible": self.n_event_ineligible,
                "ruwe_available": self.ruwe_available,
                "legend_note": self.legend_note,
                "ruling": self.ruling,
            }
        }


def apply_quarantine(cat: StarCatalog, is_wd=None,
                     whitelist_ids=frozenset()) -> tuple[StarCatalog, QuarantineReport]:
    """検疫を適用し、(更新カタログ, 会計報告) を返す。

    - is_wd: 白色矮星ブール配列 (外部クロスマッチ由来。None なら bit0 は不適用)
    - whitelist_ids: 確認済み HVS の source_id 集合 (bit3 を解除)
    - bit0 該当星は DR3 RV を不採用: radial_velocity/rv_error → NaN,
      rv_provenance → -1 (外部 RV があれば取込側で上書きされる)
    """
    d = {k: np.array(v, copy=True) for k, v in cat.data.items()}
    n = len(d["source_id"])
    flags = np.zeros(n, dtype=np.int16)

    # bit0: WD の DR3 RV
    n_wd = 0
    if is_wd is not None:
        wd_with_gaia_rv = np.asarray(is_wd, dtype=bool) & (d["rv_provenance"] == 0)
        flags[wd_with_gaia_rv] |= QUARANTINE_WD_RV
        d["radial_velocity"][wd_with_gaia_rv] = np.nan
        d["rv_error"][wd_with_gaia_rv] = np.nan
        d["rv_provenance"][wd_with_gaia_rv] = -1
        n_wd = int(wd_with_gaia_rv.sum())

    # bit1: RUWE
    ruwe_available = "ruwe" in d
    n_ruwe = 0
    if ruwe_available:
        bad = np.asarray(d["ruwe"], dtype=float) >= RUWE_MAX
        flags[bad] |= QUARANTINE_RUWE
        n_ruwe = int(bad.sum())

    # bit2: PM S/N
    pm = np.hypot(d["pmra"], d["pmdec"])
    pm_err = np.hypot(d["pmra_error"], d["pmdec_error"])
    low_sn = pm / np.maximum(pm_err, 1e-12) < PM_SN_MIN
    flags[low_sn] |= QUARANTINE_PM_SN
    n_pm = int(low_sn.sum())

    # bit3: RV 外れ値 (要手動審査。除外ではない)
    with np.errstate(invalid="ignore"):
        outlier = np.abs(d["radial_velocity"]) > RV_ABS_MAX
    outlier &= ~np.isnan(d["radial_velocity"])
    whitelisted = outlier & np.isin(d["source_id"], list(whitelist_ids))
    flags[outlier & ~whitelisted] |= QUARANTINE_RV_OUTLIER
    n_out = int((outlier & ~whitelisted).sum())
    n_wl = int(whitelisted.sum())

    d["quarantine_flags"] = flags
    excl = QUARANTINE_WD_RV | QUARANTINE_RUWE | QUARANTINE_PM_SN
    report = QuarantineReport(
        n_total=n, n_bit_wd_rv=n_wd, n_bit_ruwe=n_ruwe, n_bit_pm_sn=n_pm,
        n_bit_rv_outlier=n_out, n_whitelisted=n_wl,
        n_event_ineligible=int(((flags & excl) != 0).sum()),
        ruwe_available=ruwe_available,
    )
    new_cat = StarCatalog(data=d, release=cat.release, ref_epoch=cat.ref_epoch,
                          frame=cat.frame,
                          meta={**cat.meta, **report.as_metadata()})
    return new_cat, report
