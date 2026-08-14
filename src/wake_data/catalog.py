"""カタログ Provider 層 (憲法第8条1項)

上位層は StarCatalog (スキーマ v0 準拠のデータ + メタデータ) だけを見る。
DR3 / DR4 / ダミーの違いは Provider の load() 内部で吸収する。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from .schema import validate_catalog


@dataclass
class StarCatalog:
    """スキーマ v0 準拠のカタログ。data は列名 → np.ndarray。"""
    data: dict
    release: str          # 例 "GaiaDR3", "GaiaDR4", "dummy-v1"
    ref_epoch: float      # 例 2016.0 (Julian year)
    frame: str = "ICRS"
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        problems = validate_catalog(self.data)
        if problems:
            raise ValueError(f"スキーマ違反 ({self.release}): {problems}")

    def __len__(self):
        return len(self.data["source_id"])


class CatalogProvider(ABC):
    """データ層の差替単位。上位層はこの抽象にのみ依存すること。"""

    @abstractmethod
    def load(self) -> StarCatalog:
        ...


class DummyCatalogProvider(CatalogProvider):
    """差替テスト・パイプライン開発用の合成カタログ。

    version="v1": DR3 想定 (RV 完備性 ~60%, G<14 に集中)
    version="v2": DR4 想定 (増員 + RV 限界等級が深い) — 差し替えで上位層が
                  無変更のまま動くことを検証するための「別リリース」役。
    """

    def __init__(self, n: int = 1000, version: str = "v1", seed: int = 0):
        self.n = n
        self.version = version
        self.seed = seed

    def load(self) -> StarCatalog:
        rng = np.random.default_rng(self.seed)
        n = self.n if self.version == "v1" else int(self.n * 1.5)
        g = rng.uniform(6.0, 18.0, n)
        rv_limit = 14.0 if self.version == "v1" else 16.0
        bp_rp = rng.uniform(0.0, 4.5, n)
        has_rv = (g < rv_limit) & (rng.random(n) < 0.9) & (bp_rp <= 3.7)
        rv = np.where(has_rv, rng.normal(0, 30, n), np.nan)
        data = {
            "source_id": np.arange(n, dtype=np.int64),
            "ra": rng.uniform(0, 360, n),
            "dec": np.degrees(np.arcsin(rng.uniform(-1, 1, n))),
            "parallax": np.abs(rng.normal(20, 15, n)) + 1.0,
            "pmra": rng.normal(0, 50, n),
            "pmdec": rng.normal(0, 50, n),
            "radial_velocity": rv,
            "ra_error": np.full(n, 0.03),
            "dec_error": np.full(n, 0.03),
            "parallax_error": np.full(n, 0.03),
            "pmra_error": np.full(n, 0.05),
            "pmdec_error": np.full(n, 0.05),
            "rv_error": np.where(has_rv, 1.0, np.nan),
            "phot_g_mean_mag": g,
            "bp_rp": bp_rp,
            "rv_provenance": np.where(has_rv, 0, -1).astype(np.int8),
            # v1 追加列 (フォーク3裁定): 晩期M相当 (RVS 温度範囲外) を bp_rp > 3.7 で模擬
            "rvs_teff_flag": np.where(bp_rp > 3.7, 0, 1).astype(np.int8),
            "quarantine_flags": np.zeros(n, dtype=np.int16),
            "s_completeness": np.full(n, np.nan),
        }
        return StarCatalog(
            data=data,
            release=f"dummy-{self.version}",
            ref_epoch=2016.0,
            meta={"rv_limit_mag": rv_limit},
        )


class GaiaDR3Provider(CatalogProvider):
    """本番 DR3。Phase 1 以降で実装 (ADQL / ローカル parquet)。"""

    def load(self) -> StarCatalog:
        raise NotImplementedError("Phase 1 で実装")


class GaiaDR4Provider(CatalogProvider):
    """DR4 (2026年末予定) 差し替え先の区画確保。"""

    def load(self) -> StarCatalog:
        raise NotImplementedError("DR4 公開後に実装")
