# Zenodo v2 デポジット実施記録(裁定ログ#22 完結指示)

> 2026-08-17 起票 / 実行: Claude Code (Fable 5) / 状態: **トークン待ちで停止中**
> (§0 トークン確認: ~/.zenodo_token 不在 → 指示どおり停止し前田さんに再設置を依頼)

## 【特記 — 台帳記録指示による】停止条項が指示者側にも機能した初の実例

裁定#22-(6) "eight-branch premise" の展開において、実行系は指示書の停止条項
(「ソースに定義の実体がなければ発明せず、停止して裁定に上げる」)を発動した。
指示書側の補足(「±y 枝 × 丸め等」)は実体と不一致であり、実行系が認証器
geo_verify.py から実体(2³=8 の枝符号組合せ: 候補の子枝 × 新親の枝 × 旧親の枝)
を証拠つきで上申 → 前田さん承認(2026-08-18)。**停止条項が実行系の暴走防止
だけでなく、指示者側の誤りの検出としても機能した初の実例**(裁定#22 完結指示
特記の転記)。承認文案はコミット 4e616fe で反映済み(F4: em-dash 置換込み)。

## 実施状態

| 手順 | 状態 |
|---|---|
| 1. (6) 反映+ゲート再走+コミット | **完了**(4e616fe、全ゲート PASS) |
| 2. Zenodo v2 New version | **停止中** — ~/.zenodo_token 不在。再設置後に `python3 scripts/zenodo_publish_v2.py` で一括実行(dry-run 検証済み) |
| 3. GitHub タグ v2.0-zenodo / Release / README 更新 | 待機(リリースコミット確定後) |
| 4. arXiv 投稿稿凍結(docs/phase-r/arxiv-submission/) | 待機(v2 PDF 確定後) |
| 5. トークン削除+台帳転記+完了報告 | 待機 |

## v2 レコード構成(publish 時に確定値を転記)

- ファイル2点: `paper.pdf`(25p、付録C自己完結版)+ `wake-repo-v2.tar.gz`
- 改版理由(メタデータ Version note): "Appendix C made self-contained; label
  precision (Section 4 claim); C-series footnote; hypothesis precision (C6a
  isotropy, survival definition). No change to mathematical content."
- version: v2 / creators(ORCID 0009-0005-3401-9230)・related identifiers は
  v1 から継承維持 / concept DOI 維持(新規レコード禁止)
- **v2 版 DOI**: (publish 後転記)
- **リリースコミット**: (転記)
- **wake-repo-v2.tar.gz sha256**: (転記)

## arXiv Comments 欄案(投稿時に前田さん最終確認)

> 25 pages. v2 of the Zenodo preprint (doi:10.5281/zenodo.21955413).
> Companion observational paper: doi:10.5281/zenodo.21966305

## トークン再設置手順(前田さん — read -s 方式)

```
read -s ZT && printf '%s' "$ZT" > ~/.zenodo_token && chmod 600 ~/.zenodo_token && unset ZT
```

作業完了後に ~/.zenodo_token を削除し、削除を完了報告に含める(消し忘れ防止の固定項目)。
