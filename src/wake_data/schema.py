"""WAKE 星カタログスキーマ v1 (フォーク3裁定 2026-08-14 で確定)

v0 → v1: 裁定1・3 に伴う追加列のみ (後方互換)。
  - rvs_teff_flag:    RVS テンプレート有効温度範囲の内外 (晩期 M = 選択関数の穴の判定根拠)
  - quarantine_flags: データ検疫ビットマスク (メモ2 §5; 仕様確定は Phase 1 冒頭裁定)
  - s_completeness:   選択確率 S のキャッシュ (floor 判定の根拠列)

方針:
- 列は Gaia アーキタイプに合わせる。DR3 → DR4 の差し替えは Provider 側の写像で吸収し、
  このスキーマは変えない (第8条1項)。
- 視線速度の出所を rv_provenance で明示する。外部サーベイ補完・事前分布サンプルを
  混ぜる場合に、選択関数補正の対象を区別するため (第7条2項)。
- 5×5 アストロメトリ共分散は相関係数の上三角 10 個で持つ (Gaia 配布形式と同じ)。
  誤差 MC の全共分散サンプリング (第8条3項) に必要。
"""

import numpy as np

# 検疫ビット (quarantine_flags)。0 = クリーン
QUARANTINE_WD_RV = 1        # 白色矮星の DR3 RV (テンプレート欠如によるスプリアス)
QUARANTINE_RUWE = 2         # RUWE >= 1.4
QUARANTINE_PM_SN = 4        # 固有運動 S/N 低 (未解決連星の疑い)
QUARANTINE_RV_OUTLIER = 8   # RV 外れ値

# (列名, dtype, 単位, 必須か)
STAR_CATALOG_SCHEMA_V1 = [
    ("source_id",        np.int64,   "",        True),
    ("ra",               np.float64, "deg",     True),
    ("dec",              np.float64, "deg",     True),
    ("parallax",         np.float64, "mas",     True),
    ("pmra",             np.float64, "mas/yr",  True),
    ("pmdec",            np.float64, "mas/yr",  True),
    ("radial_velocity",  np.float64, "km/s",    True),   # 欠損は NaN
    ("ra_error",         np.float64, "mas",     True),
    ("dec_error",        np.float64, "mas",     True),
    ("parallax_error",   np.float64, "mas",     True),
    ("pmra_error",       np.float64, "mas/yr",  True),
    ("pmdec_error",      np.float64, "mas/yr",  True),
    ("rv_error",         np.float64, "km/s",    True),   # 欠損は NaN
    # 5x5 アストロメトリ相関 (上三角)
    ("corr_ra_dec",          np.float64, "", False),
    ("corr_ra_parallax",     np.float64, "", False),
    ("corr_ra_pmra",         np.float64, "", False),
    ("corr_ra_pmdec",        np.float64, "", False),
    ("corr_dec_parallax",    np.float64, "", False),
    ("corr_dec_pmra",        np.float64, "", False),
    ("corr_dec_pmdec",       np.float64, "", False),
    ("corr_parallax_pmra",   np.float64, "", False),
    ("corr_parallax_pmdec",  np.float64, "", False),
    ("corr_pmra_pmdec",      np.float64, "", False),
    # 測光・品質 (選択関数の引数になるため必須)
    ("phot_g_mean_mag",  np.float64, "mag",     True),
    ("bp_rp",            np.float64, "mag",     True),
    ("ruwe",             np.float64, "",        False),
    # 出所フラグ: 0=gaia_rvs, 1=external_survey, 2=imputed_prior, -1=missing
    ("rv_provenance",    np.int8,    "",        True),
    # --- v1 追加列 (フォーク3裁定・後方互換のため必須にしない) ---
    # RVS 有効温度範囲: 1=範囲内, 0=範囲外(晩期M等・選択関数の穴), -1=不明
    ("rvs_teff_flag",    np.int8,    "",        False),
    # 検疫ビットマスク (QUARANTINE_* の OR)。0=クリーン
    ("quarantine_flags", np.int16,   "",        False),
    # 選択確率 S のキャッシュ。NaN=未計算。floor 判定の根拠列
    ("s_completeness",   np.float64, "",        False),
]

# 後方互換: v0 = v1 から追加列を除いたもの
_V1_ADDED = {"rvs_teff_flag", "quarantine_flags", "s_completeness"}
STAR_CATALOG_SCHEMA_V0 = [r for r in STAR_CATALOG_SCHEMA_V1 if r[0] not in _V1_ADDED]

REQUIRED_COLUMNS = [c for c, _, _, req in STAR_CATALOG_SCHEMA_V1 if req]


def validate_catalog(data: dict) -> list[str]:
    """スキーマ違反のリストを返す (空なら合格)。"""
    problems = []
    n = None
    for col in REQUIRED_COLUMNS:
        if col not in data:
            problems.append(f"必須列がない: {col}")
    for col, arr in data.items():
        arr = np.asarray(arr)
        if n is None:
            n = len(arr)
        elif len(arr) != n:
            problems.append(f"列長不一致: {col} ({len(arr)} != {n})")
    if "rv_provenance" in data:
        prov = np.asarray(data["rv_provenance"])
        bad = ~np.isin(prov, [-1, 0, 1, 2])
        if bad.any():
            problems.append(f"rv_provenance に不正値 {np.unique(prov[bad])}")
        if "radial_velocity" in data:
            rv = np.asarray(data["radial_velocity"])
            # 出所フラグと RV 欠損の整合
            if np.any(np.isnan(rv) & (prov != -1)):
                problems.append("RV が NaN なのに rv_provenance が missing でない行がある")
    if "s_completeness" in data:
        s = np.asarray(data["s_completeness"], dtype=float)
        finite = s[~np.isnan(s)]
        if finite.size and (np.any(finite < 0) or np.any(finite > 1)):
            problems.append("s_completeness に [0,1] 外の値がある")
    return problems
