# Zenodo v1 デポジット案(F2)— **公開完了 2026-08-16**

> **DOI: 10.5281/zenodo.21955413** / https://zenodo.org/record/21955413
> リリースコミット 3dc9b58 / wake-repo-v1.tar.gz sha256
> 8c1bfca5114c98a0a751ab695569e9583694833998fde407f73a61307371b8fa
> (以下は付議時の案 — 実施記録として保存)

## レコード構成(ファイル2点)

| ファイル | 内容 |
|---|---|
| `paper.pdf` | 本文(英語・和文要旨付き・15p)。F1/F2 反映済み・品質ゲート v2 全PASS |
| `wake-repo-v1.tar.gz` | **リポジトリ全量スナップショット**(git 追跡ファイル全量、公開承認時点のリリースコミット)。検証器 v6・認証ログ・数値反証装置・実験 archive(E1–E8c)・審査記録(claims.md ほか)・付録原本・図生成/引用検証スクリプトを含む |

生成コマンド(再現可能): `git archive --format=tar.gz -o wake-repo-v1.tar.gz <リリースコミット>`

**付議時点のドラフトアーカイブ**(公開時は DOI 追記後のリリースコミットで再生成):
- コミット: 82ee9b4 / サイズ: 505,431 bytes
- sha256: `77be412ddd79132a8a9e60ada8e15cab44da1fd21ad460b75b61885a3610a95c`

## メタデータ案

- **Upload type**: Publication → Preprint
- **Publication date**: 2026-08-16
- **Title**: Contact processes on ballistic Poisson particles: criticality,
  fronts, and when motion helps colonization
- **Creators**: Maeda, Yukie(所属なし・独立研究者、ORCID iD: 0009-0005-3401-9230)【承認裁定で確定】
- **Description**: abstracts.md の英語+日本語を併記し、末尾に1行:
  "The complete artifact repository (verifier, certification logs,
  falsification device, experiment archive, review records) is bundled as
  wake-repo-v1.tar.gz." / 「検証器・認証ログ・数値反証装置・実験 archive・
  審査記録の全量を wake-repo-v1.tar.gz として同梱する。」
- **Version**: v1(**プレプリント**と明記 — 裁定ログ#10)
- **Language**: eng(説明文は日英併記)
- **License(承認裁定で確定)**: **CC BY 4.0(レコード)+コードは MIT を
  アーカイブ内 LICENSE で宣言**する併用構成(リポジトリ直下 LICENSE に実装済み。
  説明文にも併用の1行を追加する)
- **Keywords**: contact process; percolation; Poisson point process;
  interacting particle systems; ballistic motion; mobile agents;
  epidemics on moving populations; Fermi paradox

## 承認後の実行手順(実行系)

1. Zenodo 新規デポジット作成 → **DOI を予約**(publish 前に取得可能)
2. 予約 DOI を paper.tex の題箋に追記("(Preprint --- Zenodo v1, doi:...)")→
   再コンパイル → リリースコミット確定
3. `git archive` でリリースコミットから wake-repo-v1.tar.gz 生成・sha256 記録
4. paper.pdf + tar.gz をアップロード、メタデータ入力(本案どおり)、publish
5. PHASES 台帳・memory に DOI を記録。GitHub 相互参照は公開リポジトリ整備後
   (別途裁定 — 裁定ログ#9 の「従来どおり GitHub と相互参照」の具体化)

## 禁止事項の再確認

- 承認前の Zenodo アップロード・外部送付(エンドーサー依頼含む)は行わない
- 本案の変更が必要な場合は停止・報告(実装で解決しない)
