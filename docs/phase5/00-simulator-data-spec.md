# シミュレータ データ供給仕様 v0(裁定ログ#14 裁定3)

## 確定2ファイル+予約1ファイル

| ファイル | スキーマ | 状態 |
|---|---|---|
| `data/p2/arrival_catalog_v1.json` | schema_version="v1" | 確定 |
| `data/p3/exclusion_map_v1.json` | schema_version="exclusion-map-v1" | 確定 |
| `data/p4/flyby_network_v1.json` | schema_version="flyby-network-v1" | Phase 4 出口で確定 |

## 読み取り仕様(追加互換の原則 — 列追加のみ・削除/改名禁止)

1. **航跡タイムライン**: catalog `entries[]` — t_ph/d_ph の median+ci90、
   p_within、判定フラグ群(rv_faint_suspect_bit5・excluded_from_event_judgement・
   undecidable_S)。表示側は suspect をトグル可能に(両建て運用)
2. **排除地図スライダー**: map の `rate_layers`(clean/bridge/suspect の3層切替)、
   `visit_layer.f_star_boundary` 式+`T_eff_matrix_RxV`、`theorem_layer.domain`
   (三値凡例+等方化注記+数値閾値注記を必ず併記表示)
3. **フライバイ網レイヤ**: network `results` の直接通過数・最小乗換 Δv。
   v1.1 で辺リスト(時間拡大グラフ)追加予定 — 列追加で対応
4. **必須表示**: 条件付き確率文テンプレート(map metadata)・判定不能領域の
   明示・安全側注記。「測量であって証明ではない」を全画面フッタに(憲法第7条)

仲裁ルール(物理→美学)の設計セッションは Phase 4 出口後(前田さん+参謀)。
