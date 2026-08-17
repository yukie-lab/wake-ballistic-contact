# Zenodo v2 デポジット実施記録(裁定ログ#22 完結指示)

> 2026-08-17 起票・**同日公開完了** / 実行: Claude Code (Fable 5)
> (経緯: §0 トークン確認で ~/.zenodo_token 不在 → 指示どおり停止・前田さんが
> read -s 方式で再設置 → 疎通 OK → 一括実行・publish・読み戻し検証まで完了)

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
| 2. Zenodo v2 New version → publish | **完了**(2026-08-17、`zenodo_publish_v2.py` 一括実行。md5 全一致・公開 API 読み戻し検証 OK) |
| 3. GitHub タグ v2.0-zenodo / Release / README 更新 | **完了**(タグ=a382355、Release に v2 tar.gz+sha256 全文、README を concept DOI バッジ+v2 系引用に更新) |
| 4. arXiv 投稿稿凍結(docs/phase-r/arxiv-submission/) | **完了**(TeX ソース一式+paper.pdf+FROZEN.md) |
| 5. トークン削除+台帳転記+完了報告 | **完了**(PHASES 台帳 #21・#22 転記、~/.zenodo_token 削除) |

## v2 レコード構成(publish 時に確定値を転記)

- ファイル2点: `paper.pdf`(25p、付録C自己完結版)+ `wake-repo-v2.tar.gz`
- 改版理由(メタデータ Version note): "Appendix C made self-contained; label
  precision (Section 4 claim); C-series footnote; hypothesis precision (C6a
  isotropy, survival definition). No change to mathematical content."
- version: v2 / creators(ORCID 0009-0005-3401-9230)・related identifiers は
  v1 から継承維持 / concept DOI 維持(新規レコード禁止)
- **v2 版 DOI**: **10.5281/zenodo.21979354** — https://zenodo.org/record/21979354
- **concept DOI**: 10.5281/zenodo.21955412(全版を指す)
- **リリースコミット**: **a382355**
- **ファイル**: paper.pdf(360,577B・25頁、sha256
  45b1e54b2c703824395547f9dd0f0d4d74545db6597e1c72b3b976400a93cd45)+
  wake-repo-v2.tar.gz(1,652,320B)
- **wake-repo-v2.tar.gz sha256**:
  `70038d4b0e06af162766465f05424aa9525e1c3b2dcdeb715a8931bb944aa70f`
- 公開 API 読み戻し: version=v2 / 改版理由表示 OK / files 2点 確認済み

## arXiv Comments 欄案(投稿時に前田さん最終確認)

> 25 pages. v2 of the Zenodo preprint (doi:10.5281/zenodo.21955413).
> Companion observational paper: doi:10.5281/zenodo.21966305

## トークン再設置手順(前田さん — read -s 方式)

```
read -s ZT && printf '%s' "$ZT" > ~/.zenodo_token && chmod 600 ~/.zenodo_token && unset ZT
```

作業完了後に ~/.zenodo_token を削除し、削除を完了報告に含める(消し忘れ防止の固定項目)。
