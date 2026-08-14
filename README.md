# Project WAKE — 太陽近傍の来訪統計アトラス

実測恒星運動学の下での到来統計・排除地図・フライバイ網統合。
来訪仮説検証プログラム 枝3(亜光速)。

- **規範**: [CLAUDE.md](CLAUDE.md)(憲法 1.1)> [PHASES.md](PHASES.md)(フェーズ指示書 1.1)
  > 裁定記録([docs/rulings/](docs/rulings/))
- **現況**: Phase 0 クローズ(2026-08-14)→ **Phase 1(伝播エンジン + G3 アンカー検証)**。
  冒頭裁定5点は付議準備中。恒常タスク: ESA ACT 監視(次回 2026-11)

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
src/wake_data/        データ層(スキーマ v0 / カタログ / 選択関数)
src/tests/            差替テスト
bench/                計算予算ベンチマーク
```

## 検証

```bash
python3 src/tests/test_swap.py        # データ層差替テスト
python3 bench/bench_propagation.py    # 計算予算実測(数分)
```
