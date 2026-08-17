# arXiv 投稿稿 凍結記録

> 2026-08-17 凍結 / 裁定ログ#22 完結指示 §4 / Zenodo v2 と同一内容
> 追補 2026-08-17(前田さん指示): **arXiv 投稿には `en-only/` 構成を使用**
> (和文要旨を除いた英語完結版・CJK 非依存)。本ディレクトリ直下の一式は
> Zenodo v2 同一の照合用として維持。

- **ソース**: リリースコミット **a382355**(release: Zenodo v2)
- **内容**: paper.tex / refs.bib / figs/(fig1〜fig3 PDF)/ paper.pdf(25頁)
- **paper.pdf sha256**: `45b1e54b2c703824395547f9dd0f0d4d74545db6597e1c72b3b976400a93cd45`
  (Zenodo v2 レコード掲載の paper.pdf と同一バイト列)
- **Zenodo v2**: doi:10.5281/zenodo.21979354(concept doi:10.5281/zenodo.21955412)
- **投稿カテゴリ案**: math.PR 主 / cond-mat.stat-mech 副(裁定ログ#10)
- **投稿条件**: math.PR エンドースメント成立後。**投稿直前に arXiv AI ポリシー
  (著者資格・開示要件・未検証AI生成物の1年BAN制度)を最終再確認**し、
  付録Bの開示文と整合させる(従前どおり)

## Comments 欄案(最終文言は投稿時に前田さん確認)

> 25 pages. v2 of the Zenodo preprint (doi:10.5281/zenodo.21955413).
> Companion observational paper: doi:10.5281/zenodo.21966305

## en-only 構成(arXiv 投稿用 — 2026-08-17 追加凍結)

- **場所**: `en-only/`(paper.tex / refs.bib / figs/ / paper.pdf)
- **Zenodo v2 との差分は和文要旨の有無のみ**。paper.tex の diff は正確に
  次の2ハンクで、それ以外は 1 バイトも違わない(diff 検証済み):
  1. preamble の CJK 2行(`\usepackage{xeCJK}` と
     `\setCJKmainfont{Hiragino Mincho ProN}`)の除去 — 和文要旨の組版のみの
     ために存在した行
  2. abstract 環境内の和文要旨ブロック(「和文要旨.」段落と、二言語併記用の
     `\medskip`+`\textbf{Abstract.}` ラベル)の除去 — 英語要旨本文は不変
  数学的内容・本文・付録・参考文献は完全同一。
- **コンパイル検証(TeXLive 標準相当・Hiragino 非依存の確認)**:
  Tectonic(XeTeX 系・TeXLive バンドル自己完結、システム TeX 非使用)で
  クリーンコンパイル成功。**システムフォントへのアクセス 0 件**
  (二言語版で出ていた `accessing absolute path …ヒラギノ明朝 ProN.ttc`
  警告が消滅し、全フォントが TeXLive バンドルの Computer Modern から取得
  されたことをビルドログで確認)。使用パッケージは geometry / amsmath /
  amssymb / amsthm / graphicx / booktabs / hyperref のみ(全て TeXLive 標準)。
- **en-only paper.pdf**: **25頁**(二言語版と同頁数 — Comments 欄案の
  "25 pages" は有効)、292,570 bytes、sha256
  `ce54abd5a48515b8e146f42b82f2f3a43365dd2ac71a62fd791d312aedf90461`

## 注意

- arXiv は TeX ソース投稿が原則: **`en-only/` の paper.tex + refs.bib +
  figs/ を投稿**し、`en-only/paper.pdf` は照合用。二言語版(本ディレクトリ
  直下)は Zenodo v2 との同一性照合用に保全
- 本ディレクトリは凍結。以後の編集は新たな裁定によってのみ行う
