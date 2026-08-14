"""選択関数層 (憲法第8条2項: カタログ本体と同格の差替可能部品)

インターフェース: completeness(g, bp_rp, ra, dec) → [0,1]
「G 等級・色・天域の星が、6D 完備 (RV あり) でカタログに載る確率」を返す。

到来率の条件部 (第7条2項) はこの completeness を通してのみ補正される。
具体モデルの選定はフォーク3 (人間裁定) — ここは差替の枠のみを固定する。
"""

from abc import ABC, abstractmethod

import numpy as np


# s_floor はフォーク3裁定3 (2026-08-14) により暫定 0.05 (最大重み 20)。
# floor は数値下限ではなく分散管理パラメータ (HT 推定量の分散は重みの二乗で膨張)。
# 最終値は注入回収テストのバイアス–分散曲線で二段裁定する。
DEFAULT_S_FLOOR = 0.05


class SelectionFunction(ABC):
    name: str = "abstract"

    def __init__(self, s_floor: float = DEFAULT_S_FLOOR):
        self.s_floor = s_floor

    @abstractmethod
    def completeness(self, g_mag, bp_rp, ra, dec) -> np.ndarray:
        """要素ごとの完備性確率 [0, 1]。floor 未満の領域は weights() 側で
        「判定不能」(NaN) に落ちる。"""
        ...

    def weights(self, g_mag, bp_rp, ra, dec) -> np.ndarray:
        """逆確率重み 1/S。s_floor 未満は NaN (= 補正不能、判定不能域)。"""
        s = self.completeness(g_mag, bp_rp, ra, dec)
        return np.where(s >= self.s_floor, 1.0 / np.maximum(s, self.s_floor), np.nan)


class UnitySelection(SelectionFunction):
    """完備性 = 1 (補正なし)。ベースラインおよび差替テスト用。"""
    name = "unity"

    def completeness(self, g_mag, bp_rp, ra, dec):
        return np.ones_like(np.asarray(g_mag, dtype=float))


class MagnitudeThresholdSelection(SelectionFunction):
    """等級シグモイドのトイモデル。差替テストと注入回収試験用であり物理ではない。
    本番 (gaiaunlimited DR3RVSSelectionFunction) はフォーク3裁定1に基づき
    Phase 2 導入時に同じ枠で実装する。"""
    name = "mag-threshold-toy"

    def __init__(self, g50: float = 13.0, width: float = 0.8, **kw):
        super().__init__(**kw)
        self.g50 = g50
        self.width = width

    def completeness(self, g_mag, bp_rp, ra, dec):
        g = np.asarray(g_mag, dtype=float)
        return 1.0 / (1.0 + np.exp((g - self.g50) / self.width))


class PatchySkySelection(SelectionFunction):
    """天域依存の斑状選択関数 (スキャン則パターン模擬)。フォーク3裁定4の
    追加要件: 空間構造は IPW の偽陰性バイアスの主因であり、注入回収試験は
    等級依存だけでは試験にならない。

    実装: 等緯度リング × 経度セルの等面積近似ピクセル化 (自前・依存なし)。
    セルごとの完備性はシードから決定論的に [s_lo, s_hi] を割当。
    本番の HEALPix (healpy) とはピクセル形状が異なるが、注入試験の目的
    (空間斑の下での IPW 回復) には十分。healpy 導入後に差替可能。"""
    name = "patchy-sky-toy"

    def __init__(self, n_rings: int = 12, s_lo: float = 0.02, s_hi: float = 1.0,
                 seed: int = 0, **kw):
        super().__init__(**kw)
        self.n_rings = n_rings
        self.s_lo, self.s_hi = s_lo, s_hi
        self.seed = seed

    def _cell_index(self, ra, dec):
        ra = np.asarray(ra, dtype=float)
        dec = np.asarray(dec, dtype=float)
        ring = np.clip(((np.sin(np.radians(dec)) + 1) / 2 * self.n_rings).astype(int),
                       0, self.n_rings - 1)
        # 等面積近似: リングあたりのセル数を cos(dec_center) に比例させる
        ring_dec = np.degrees(np.arcsin((ring + 0.5) / self.n_rings * 2 - 1))
        n_cells = np.maximum(1, (2 * self.n_rings *
                                 np.cos(np.radians(ring_dec))).astype(int))
        cell = (ra / 360.0 * n_cells).astype(int) % n_cells
        return ring * (2 * self.n_rings + 1) + cell

    def completeness(self, g_mag, bp_rp, ra, dec):
        idx = self._cell_index(ra, dec)
        # セル値はシード+セル番号から決定論的に生成 (呼び出し間で不変)
        rng = np.random.default_rng(self.seed)
        table = rng.uniform(self.s_lo, self.s_hi,
                            self.n_rings * (2 * self.n_rings + 1))
        return table[idx]


class ProductSelection(SelectionFunction):
    """選択関数の積 (例: 等級シグモイド × 空間斑)。s_floor は自身の値を使う。"""
    name = "product"

    def __init__(self, components, **kw):
        super().__init__(**kw)
        self.components = list(components)

    def completeness(self, g_mag, bp_rp, ra, dec):
        s = np.ones_like(np.asarray(g_mag, dtype=float))
        for c in self.components:
            s = s * c.completeness(g_mag, bp_rp, ra, dec)
        return s
