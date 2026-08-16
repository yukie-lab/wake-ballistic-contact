"""解釈規律の機械監査(憲法第7条 — Phase 3 出口条件)

排除地図 JSON の全言明が条件付き確率文の規律を満たすことを機械検査:
(i) 条件文テンプレートに対象母集団の明記(第7条3項)
(ii) 完備性補正への明示的言及(第7条2項)
(iii) 判定不能の明示(第5条6項)
(iv) 無条件断定の禁止 — 「証明」「確実」等の断定語がないこと
(v) 安全側の向きの明記(裁定ログ#13 条件(ii))
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
JSON_PATH = ROOT / "data" / "p3" / "exclusion_map_v1.json"


def main():
    doc = json.loads(JSON_PATH.read_text())
    tmpl = doc["conditional_statement_template"]
    checks = {
        "母集団明記(第7条3項)": "FGK+早中期M" in tmpl and "S≥0.05" in tmpl,
        "完備性言及(第7条2項)": "完備性補正後" in tmpl,
        "判定不能明示(第5条6項)": "判定不能" in tmpl,
        "太陽λ規約注記(裁定#13(iii))": "星平均ではない" in tmpl,
        "安全側の向き(裁定#13(ii))": "安全側" in doc.get("safety_note", ""),
        "定理レイヤ三値凡例": len(doc["theorem_layer"]["legend"]) == 3,
        "等方化近似の明示": "等方化" in doc["theorem_layer"]["isotropization_note"],
        "無条件断定の不在": not any(w in tmpl for w in ("証明", "確実に", "必ず")),
    }
    bad = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    assert not bad, f"解釈規律違反: {bad}"
    print("解釈規律監査: PASS")


if __name__ == "__main__":
    main()
