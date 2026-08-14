"""G3 不変量指紋アンカーの台帳 (憲法第6条 G3、1.1 改正対応)

憲法 1.1 G3-5: 参照値・合格帯は条文に直書きせず Phase 1 冒頭裁定で
裁定ログに固定する。本モジュールは:
- reference: 公刊値 (出典付き、変更しない事実)
- proposed_strict / proposed_loose: メモ2 §6 の提案帯 (裁定材料)
- strict_band / loose_band: 裁定で固定される公式帯。**裁定前は None**
を区別して保持する。裁定前に strict_band を埋めてはならない。

【公式帯固定済み】Phase 1 冒頭裁定 (2026-08-14, 裁定ログ#4,
docs/rulings/裁定記録_Phase1冒頭裁定.md 裁定2) により固定。
以後の帯変更は憲法第10条の改正手続きによる。

G3-6 (役割分界): G3 は実装検証。合格帯の事後拡大による救済は禁止 (裁定記録)。
"""

RULING_REF = "Phase1冒頭裁定 裁定2 (2026-08-14, 裁定ログ#4)"

from dataclasses import dataclass, field


@dataclass
class Anchor:
    id: str
    name: str
    test_design: str                 # 固定入力再現 / カタログ再現 / 構造検査
    reference: dict                  # 公刊値と出典 (事実)
    proposed_strict: dict            # 裁定材料 (メモ2 §6)
    proposed_loose: dict
    strict_band: dict | None = None  # 裁定後に固定 (裁定ログ参照を明記)
    loose_band: dict | None = None
    fixed_inputs: dict | None = None # 固定入力再現テスト用の公刊入力 (Phase 1 で収集)
    notes: str = ""


G3_ANCHORS = [
    Anchor(
        id="G3-1",
        name="ショルツ星 (WISE J072003.20-084651.2) 過去接近",
        test_design="固定入力再現 (憲法 1.1 G3-1: 対象星は RVS 6D サンプル外)",
        reference={
            "DR3系: t_ph": "-79.9 kyr (CI90 -81.1〜-78.6) [dlFM 2022, RNAAS ac842b]",
            "DR3系: d_ph": "0.330 pc (CI90 0.317-0.345) [同上]",
            "Mamajek15: t_ph": "-70 (+15/-10) kyr [arXiv:1502.04655]",
            "Mamajek15: d_ph": "0.25 (+0.11/-0.07) pc [同上]",
        },
        proposed_strict={"t_ph_kyr": (-82, -78), "d_ph_pc": (0.31, 0.35),
                         "基準": "DR3 入力で固定 (裁定記録第三部2)"},
        proposed_loose={"t_ph_kyr": (-85, -60), "d_ph_pc": (0.18, 0.36)},
        strict_band={"t_ph_kyr": (-82, -78), "d_ph_pc": (0.31, 0.35),
                     "基準": "DR3 系入力で固定", "ruling": RULING_REF},
        loose_band={"t_ph_kyr": (-85, -60), "d_ph_pc": (0.18, 0.36),
                    "ruling": RULING_REF},
        fixed_inputs=None,  # TODO(Phase 1): dlFM 2022 の入力アストロメトリ+RV を転記
        notes="Mamajek15 系は緩和帯へ (裁定記録第三部2)",
    ),
    Anchor(
        id="G3-2",
        name="グリーゼ710 (GJ 710) 将来接近",
        test_design="固定入力再現 + カタログ再現の両方",
        reference={
            "BJ22 (DR3): d_ph": "0.0636 pc (CI90 0.0595-0.0678) [arXiv:2207.06258]",
            "B&B22 (DR3): t_ph, d_ph": "1.324±0.026 Myr, 0.052±0.002 pc [arXiv:2206.14443]",
            "FP26 (DR3+RV補正): t_ph, d_ph": "1344.6±2.2 kyr, 0.0621±0.0023 pc [arXiv:2605.16496]",
        },
        proposed_strict={"基準": "採用 RV を固定し該当系の CI90 内",
                         "t_ph_Myr": (1.27, 1.38)},
        proposed_loose={"t_ph_Myr": (1.24, 1.40), "d_ph_pc": (0.045, 0.070)},
        strict_band={"基準": "採用 RV を固定し該当系の CI90 内",
                     "t_ph_Myr": (1.27, 1.38), "ruling": RULING_REF},
        loose_band={"t_ph_Myr": (1.24, 1.40), "d_ph_pc": (0.045, 0.070),
                    "ruling": RULING_REF},
        fixed_inputs=None,  # TODO(Phase 1): 参照論文の採用 RV 別に入力セットを転記
        notes="0.052 系と 0.062 系の差は採用 RV (実装バグではない)。入力固定が必須",
    ),
    Anchor(
        id="G3-3",
        name="接近頻度 (完備性補正後)",
        test_design="カタログ再現 (BJ+18 DR2 同一手法・同一入力)",
        reference={
            "BJ+18 (DR2) @1pc": "19.7±2.2 /Myr (±5 Myr 窓) [arXiv:1805.07581]",
            "BJ+18 (DR2) @2pc/@5pc": "78.6±8.7 / 491±54 /Myr [同上]",
            "FP26 (DR3, 25pc体積) @1pc": "10.6±4.5 /Myr [arXiv:2605.16496]",
            "スケーリング": "N(<d) ∝ d² (5 pc まで) [arXiv:1805.07581]",
        },
        proposed_strict={"@1pc": (15.3, 24.1), "@2pc": (61, 96), "@5pc": (383, 599),
                         "scaling_n": (1.7, 2.3), "基準": "BJ+18 同一手法再現"},
        proposed_loose={"@1pc": (6, 25), "備考": "桁の防護柵。公刊間緊張 (19.7 vs 10.6) の"
                        "科学的裁定は Phase 2 の結果で行う (憲法 1.1 G3-6)"},
        strict_band={"@1pc": (15.3, 24.1), "@2pc": (61, 96), "@5pc": (383, 599),
                     "scaling_n": (1.7, 2.3), "基準": "BJ+18 同一手法再現",
                     "ruling": RULING_REF},
        loose_band={"@1pc": (6, 25), "ruling": RULING_REF},
        notes="G3 では科学的裁定をしない (実装検証に限定)",
    ),
    Anchor(
        id="G3-4",
        name="定常性アンカー",
        test_design="構造検査 (補正後接近率の窓内時間対称性・無ドリフト)",
        reference={"定義": "率が |t| とともにドリフトしたら伝播または補正のバグ (憲法第6条)"},
        proposed_strict={"検定": "率 λ(t) の線形トレンドがゼロと整合 (検定方式は Phase 2 で具体化)"},
        proposed_loose={},
        strict_band={"検定": "λ(t) 線形トレンドがゼロと整合 (方式具体化は Phase 2 接続時)",
                     "ruling": RULING_REF},
        loose_band={"ruling": RULING_REF},
        notes="崩れたら即停止 (憲法第6条)。即停止条項としての地位は不変 (裁定2)",
    ),
]
