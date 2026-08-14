"""ICRS 観測量 → 太陽中心銀河座標 (位置 + UVW 速度) の変換

データ層の共有入力部品 (数値経路・解析経路の両方が使う「入力カタログ」の一部。
憲法の経路独立規律はコード共有を禁じるが、入力カタログの共有は許す)。

規約:
- 出力位置: 太陽中心・銀河軸 (x: 銀河中心向き, y: 回転方向 l=90°, z: 北銀極) [pc]
- 出力速度: U (銀河中心向き正), V (回転方向正), W (北向き正) [km/s] — 太陽相対
- ICRS→銀河の回転行列は Gaia DR3 ドキュメント (ESA) の標準値。
  z_sun による微小ロール補正は含めない (局所 ±10 Myr 窓では無視できる。
  G3 再現でも参照論文と同じ簡易変換系)。

v_tan [km/s] = K_PM × μ [mas/yr] × d [pc]、K_PM = 4.74047×10⁻³
"""

import numpy as np

# ICRS→銀河 回転行列 (行 = 銀河軸)。Gaia DR3 documentation / Hipparcos Vol.1 §1.5
A_G = np.array([
    [-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
    [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],
    [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669],
])

K_PM = 4.74047e-3  # km/s per (mas/yr · pc)


def icrs_to_helio_galactic(ra_deg, dec_deg, parallax_mas, pmra_masyr,
                           pmdec_masyr, rv_kms):
    """観測量 → (pos_pc (N,3), vel_kms (N,3))。すべて配列可。

    pmra は μ_α* (cos δ 込み、Gaia 標準)。distance = 1000/parallax (単純逆数;
    G3 固定入力再現では参照論文の距離採用法に合わせること)。"""
    ra = np.radians(np.asarray(ra_deg, dtype=float))
    dec = np.radians(np.asarray(dec_deg, dtype=float))
    plx = np.asarray(parallax_mas, dtype=float)
    d_pc = 1000.0 / plx
    sa, ca = np.sin(ra), np.cos(ra)
    sd, cd = np.sin(dec), np.cos(dec)
    e_r = np.stack([cd * ca, cd * sa, sd], axis=-1)
    e_ra = np.stack([-sa, ca, np.zeros_like(sa)], axis=-1)
    e_dec = np.stack([-sd * ca, -sd * sa, cd], axis=-1)
    pos_icrs = d_pc[..., None] * e_r
    v_icrs = (np.asarray(rv_kms, dtype=float)[..., None] * e_r
              + (K_PM * np.asarray(pmra_masyr, dtype=float) * d_pc)[..., None] * e_ra
              + (K_PM * np.asarray(pmdec_masyr, dtype=float) * d_pc)[..., None] * e_dec)
    pos_gal = pos_icrs @ A_G.T
    vel_uvw = v_icrs @ A_G.T
    return pos_gal, vel_uvw
