# 本体論文 Zenodo 入稿計画(公開承認後に実施 — 数学論文の手順流用)

> 状態: **公開承認待ち**。本書は承認後の作業仕様の事前固定であり、承認前の
> アップロードは行わない(憲法第2条5項・従来手順)。

## Creator メタデータ(通読指摘 F5)

```json
"creators": [{
  "name": "Maeda, Yukie",
  "affiliation": "Independent Researcher, Tokyo",
  "orcid": "0009-0005-3401-9230"
}]
```

- ORCID は著者ブロック(両版)と同一値で紐付けること。
- AI 開示は論文付録B(脚注参照)— Zenodo 説明欄にも1行注記(数学論文と同様)。

## 同梱物(承認時に確定)

- wake_en.pdf(正文)+ wake_ja.pdf(訳出)
- データ 3 JSON + MANIFEST.json(公開版 sha256 を凍結 — 付録Dの記載と整合させる)
- リポジトリ全量 tar.gz(sha256 併記 — 数学論文方式)
- シミュレータ(公開先は承認時裁定: Zenodo 同梱 and/or GitHub Pages)

## 手順(数学論文で確立済み)

1. 前田さん公開承認(ライセンス・公開先・Jxiv 和文版の扱いを同時裁定)
2. トークン設置(~/.zenodo_token)→ DOI 予約 → 題箋追記(必要なら)→
   リリースコミット → アーカイブ再生成 → publish → 公開 API で読み戻し検証
3. GitHub 公開(タグ・Release・README バッジ)→ Zenodo related_identifiers 相互参照
4. トークン削除・台帳転記
