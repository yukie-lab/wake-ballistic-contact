"""G3-1/2 固定入力セット (一次資料転記 2026-08-14)

転記の要点 (調査エージェント報告・一次資料 PDF/TAP で確認済み):
- ショルツ星 (WISE J072003.20-084651.2, Gaia DR3 3048443305671969152) は
  **DR3 にアストロメトリ解がない (2パラメータ解のみ)**。dlFM22 (RNAAS 6, 152,
  DOI 10.3847/2515-5172/ac842b) の入力は Dupuy et al. 2019 (arXiv:1908.06994) の
  地上アストロメトリ (軌道運動補正済) + DE440/441。
  → 裁定2 の厳格帯 (−82〜−78 kyr / 0.31〜0.35 pc) の数値は dlFM22 出力のまま不変。
    出所ラベルは「DR3 系」でなく「dlFM22 (Dupuy+2019 入力) 系」が正 (帯の変更ではない)。
- GJ 710 = Gaia DR3 4270814637616488064 (TAP 実測)。文献の RV 系統:
  BB22/dlFM22 = −14.42 (DR3 素値) / BJ22 = −14.4 (DR3 素値, 視差ゼロ点補正あり) /
  FP26 = −13.905 (CARMENES 実測 + 重力赤方偏移・対流青方偏移補正)。
- 位置 (ra/dec) の µas 級の違いは接近幾何に影響しないため、ショルツ星は DR3
  2パラメータ解の位置、GJ 710 は DR3 位置を全セット共通で使う。

誤差は対称ガウス近似 (非対称誤差は大きい側を採用)。相関は対角近似
(GJ 710 の DR3 相関は微小。BJ22 は全共分散 — CI 幅の比較時に注意)。
"""

# ショルツ星
SCHOLZ_RA, SCHOLZ_DEC = 110.01336163991223, -8.781073273280922  # DR3 2p解 (ep2016)

SCHOLZ_DLFM22 = dict(
    label="scholz_dlfm22 (Dupuy+2019 入力)",
    ra=SCHOLZ_RA, dec=SCHOLZ_DEC,
    parallax=147.1, parallax_err=1.15,     # +1.1/-1.2 → 1.15
    pmra=-46.0, pmra_err=3.5,              # +4/-3 → 3.5
    pmdec=-116.5, pmdec_err=2.1,           # +2.2/-2.0 → 2.1
    rv=82.4, rv_err=0.3,                   # Dupuy+2019 系重心 (軌道補正済)
    window=0.2, dt=1e-4,
    target="d_ph 0.330±0.008 pc (CI90 0.317-0.345) / t_ph -79.9±0.8 kyr (CI90 -81.1〜-78.6)",
)

SCHOLZ_MAMAJEK15 = dict(
    label="scholz_mamajek15 (Burgasser+15 入力)",
    ra=110.013375, dec=-8.781064,          # 07:20:03.21 -08:46:51.83 (ep2014)
    parallax=166.0, parallax_err=28.0,
    pmra=-40.3, pmra_err=0.2,
    pmdec=-114.8, pmdec_err=0.4,
    rv=83.1, rv_err=0.4,                   # Burgasser et al. 2015, AJ 149, 104
    window=0.2, dt=1e-4,
    target="d_ph 0.25 +0.11/-0.07 pc / t_ph -70 +15/-10 kyr",
)

# グリーゼ710 (Gaia DR3 4270814637616488064, ep2016)
GJ710_RA, GJ710_DEC = 274.96183629691126, -1.938612759804832

GJ710_BB22 = dict(
    label="gj710_bb22 (=dlFM22 系, DR3 素値 RV)",
    ra=GJ710_RA, dec=GJ710_DEC,
    parallax=52.39, parallax_err=0.02,
    pmra=-0.414, pmra_err=0.019,
    pmdec=-0.108, pmdec_err=0.017,
    rv=-14.42, rv_err=0.26,
    window=2.0, dt=0.002,
    target="BB22 積分: t_ph 1.324±0.026 Myr / d_ph 0.052±0.002 pc "
           "(dlFM22: median 0.052, CI90 0.048-0.056 / t 1.29, CI90 1.26-1.33)",
)

GJ710_BJ22 = dict(
    label="gj710_bj22 (視差ゼロ点補正済, DR3 素値 RV)",
    ra=GJ710_RA, dec=GJ710_DEC,
    parallax=52.43, parallax_err=0.02,     # Lindegren+2021a 補正込み
    pmra=-0.414, pmra_err=0.019,           # BJ22 は合成 0.42±0.02 のみ掲載 → DR3 成分を使用
    pmdec=-0.108, pmdec_err=0.017,
    rv=-14.4, rv_err=0.3,
    window=2.0, dt=0.002,
    target="BJ22: t_ph 1292 kyr (CI90 1257-1334) / d_ph 0.0636 pc (CI90 0.0595-0.0678)",
)

GJ710_FP26 = dict(
    label="gj710_fp26 (CARMENES 補正後 RV)",
    ra=GJ710_RA, dec=GJ710_DEC,
    parallax=52.396, parallax_err=0.0171,
    pmra=-0.414, pmra_err=0.019,
    pmdec=-0.108, pmdec_err=0.017,
    rv=-13.905, rv_err=0.022,
    window=2.0, dt=0.002,
    target="FP26: t_ph 1344.6±2.2 kyr / d_ph 0.0621±0.0023 pc",
)
