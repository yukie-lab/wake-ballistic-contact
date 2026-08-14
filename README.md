# Project WAKE — 太陽近傍の来訪統計アトラス

実測恒星運動学の下での到来統計・排除地図・フライバイ網統合。
来訪仮説検証プログラム 枝3(亜光速)。

- **規範**: [CLAUDE.md](CLAUDE.md)(憲法 1.1)> [PHASES.md](PHASES.md)(フェーズ指示書 1.1)
  > 裁定記録([docs/rulings/](docs/rulings/))
- **現況**: Phase 0 クローズ(2026-08-14)→ **Phase 1(伝播エンジン + G3 アンカー検証)**。
  冒頭裁定5点は付議中(`docs/phase1/00-opening-ruling-materials.md`)。
  恒常タスク: ESA ACT 監視(次回 2026-11)

## 構成

```
docs/phase0/          Phase 0 成果物
  01-cn19-boundary-interface.md   CN19 境界条件インターフェース仕様
  02-propagation-methods.md       伝播手法比較(G2 対経路・G3 合格帯案)
  03-fork3-selection-function.md  フォーク3裁定材料(Gaia 選択関数)
  04-data-layer.md                データ層設計
  05-mc-budget.md                 誤差MC設計・計算予算実測
  06-novelty-scan.md              新規性スキャン(停止条件判定)
  exit-checklist.md               出口条件チェックリスト
docs/phase1/          Phase 1 冒頭裁定付議材料
docs/rulings/         裁定記録(正文)
src/wake_data/        データ層(スキーマ v1 / カタログ / 選択関数)
src/wake_engine/      数値経路(軌道積分・ポテンシャル差替)
src/wake_epicyclic/   G2 対経路(エピサイクル解析伝播。engine とコード非共有)
src/wake_g3/          G3 不変量指紋スイート(帯は裁定ログで固定)
src/tests/            差替 / G2 スモーク / 注入回収テスト
bench/                計算予算・ホライズン感度ベンチマーク
```

## 検証

```bash
python3 src/tests/test_swap.py                  # データ層差替テスト
python3 src/tests/test_g2_smoke.py              # G2 数値 vs 解析スモーク
python3 src/tests/test_injection_recovery.py    # 注入回収 (--scan で floor 曲線)
python3 src/wake_g3/suite.py                    # G3 台帳の状態報告
python3 bench/bench_propagation.py              # 計算予算実測(数分)
python3 bench/horizon_sensitivity.py            # ホライズン感度予備測定
```
