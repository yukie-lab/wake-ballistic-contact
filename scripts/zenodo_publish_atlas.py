"""WAKE 本体論文 — Zenodo v1 公開(裁定#20 手順3の一括実行)

前提: ~/.zenodo_token(chmod 600、トークンのみ1行)。トークンは
Authorization ヘッダのみで送信し、出力・ログ・コミットに残さない(従来規律)。

実行: python3 scripts/zenodo_publish_atlas.py            # 本番
      python3 scripts/zenodo_publish_atlas.py --dry-run  # API なしで手順確認
再開: ZENODO_DEPOSIT_ID=<id> python3 scripts/zenodo_publish_atlas.py

手順: 1 デポジット作成+DOI予約 → 2 題箋追記(両版)+README バッジ →
      3 ゲート再走+再コンパイル → 4 リリースコミット → 5 アーカイブ+sha256 →
      6 メタデータ → 7 アップロード(md5照合)→ 8 publish
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

API = "https://zenodo.org/api"
ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "docs" / "phase5" / "paper"
REL = ROOT / "data" / "release"
SCRATCH = Path(os.environ.get("WAKE_SCRATCH",
    "/private/tmp/claude-501/-Users-yukie-Desktop-test/1cee2057-daf0-469b-83fd-d3a387dd35d4/scratchpad"))
DRY = "--dry-run" in sys.argv
PAGES = "https://yukie-lab.github.io/wake-atlas/"


def token():
    p = Path.home() / ".zenodo_token"
    if not p.exists():
        sys.exit("~/.zenodo_token がありません")
    return p.read_text().strip()


def req(method, url, tok, data=None, ctype="application/json", raw=False):
    headers = {"Authorization": f"Bearer {tok}"}
    body = None
    if data is not None:
        body = data if raw else json.dumps(data).encode()
        headers["Content-Type"] = ctype
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=600) as resp:
        return json.loads(resp.read().decode() or "{}")


def sh(*cmd, cwd=ROOT):
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def detex(s):
    """アブストラクトの TeX → プレーンテキスト(Zenodo 説明欄用の軽量変換)"""
    s = s.replace(r"\noindent", "")
    s = re.sub(r"\\(emph|textbf|text)\{([^{}]*)\}", r"\2", s)
    s = re.sub(r"\\cite\{[^}]*\}", "", s)
    s = s.replace(r"\lam", "λ").replace(r"\Myr", " Myr").replace(r"\pc", " pc")
    s = s.replace(r"\kms", " km/s").replace(r"\;", " ").replace(r"\,", " ")
    s = s.replace("^{-1}", "⁻¹").replace(r"\times10^{-3}", "×10⁻³")
    s = s.replace("$", "").replace(r"\simeq", "≈").replace(r"\Delta", "Δ")
    s = s.replace("4.5^{+4.0}_{-2.7}", "4.5 (+4.0/−2.7)")
    s = s.replace("f^*", "f*").replace(r"\%", "%").replace("---", "—")
    s = s.replace("~", " ").replace("{,}", ",").replace(r"\(", "(").replace(r"\)", ")")
    return re.sub(r"[ \t]+", " ", s).strip()


def abstract_of(tex):
    s = tex.read_text()
    return detex(s.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0])


def build_description():
    en = abstract_of(PAPER / "wake_en.tex")
    ja = abstract_of(PAPER / "wake_ja.tex")
    extra_en = (
        "<p><b>Bundle.</b> This record carries the bilingual paper "
        "(wake_en.pdf authoritative; wake_ja.pdf translation), the released "
        "data set (arrival_catalog_v1.json, exclusion_map_v1.json, "
        "flyby_network_v1.json with a SHA-256 MANIFEST.json), and the "
        "complete repository archive wake-atlas-v1.tar.gz (code, phase "
        "documents, ruling records — the reference target of Appendices B "
        "and C). Code files are additionally licensed under MIT (LICENSE in "
        "the archive); the record as a whole is CC BY 4.0.</p>"
        f"<p><b>Interactive simulator</b>: <a href='{PAGES}'>{PAGES}</a> — "
        "reads exactly the released JSONs; its verification harness "
        "(16 checks incl. SHA-256) is displayed before any visualization.</p>"
        "<p><b>AI disclosure</b>: all computations and drafts were executed "
        "by an AI system (Claude Code, model Claude Fable 5) under the "
        "direction and arbitration of the human author (paper Appendix B); "
        "the internal verification protocol is not a substitute for human "
        "peer review.</p>")
    extra_ja = (
        "<p><b>同梱物</b>: 日英二版 PDF(英語版が正文)・公開データ3 JSON+"
        "SHA-256 マニフェスト・リポジトリ全量 wake-atlas-v1.tar.gz(付録B/C の"
        "参照先)。コードは MIT 併用宣言、レコード全体は CC BY 4.0。"
        f"シミュレータ: {PAGES}</p>")
    return ("<p><b>Abstract (English)</b></p><p>" + en + "</p>" + extra_en +
            "<p><b>要旨(日本語)</b></p><p>" + ja + "</p>" + extra_ja)


METADATA = {
    "metadata": {
        "upload_type": "publication",
        "publication_type": "preprint",
        "title": ("WAKE: a visitation-statistics atlas of the solar "
                  "neighbourhood — arrival statistics, an exclusion map, and "
                  "a flyby network on Gaia DR3 kinematics"),
        "creators": [{"name": "Maeda, Yukie",
                      "affiliation": "Independent Researcher, Tokyo",
                      "orcid": "0009-0005-3401-9230"}],
        "license": "cc-by-4.0",
        "version": "v1",
        "language": "eng",
        "keywords": ["stellar encounters", "Gaia DR3", "solar neighbourhood",
                     "exclusion map", "settlement dynamics", "Fermi paradox",
                     "flyby network", "selection function", "completeness",
                     "visitation statistics"],
        "related_identifiers": [
            {"identifier": "10.5281/zenodo.21955413", "relation": "cites",
             "resource_type": "publication-preprint"},
        ],
    }
}

FILES = ["wake_en.pdf", "wake_ja.pdf"]
DATA_FILES = ["arrival_catalog_v1.json", "exclusion_map_v1.json",
              "flyby_network_v1.json", "MANIFEST.json"]


def main():
    tok = None if DRY else token()

    # 1. デポジット作成(or 再開)+ DOI 予約
    dep_id = os.environ.get("ZENODO_DEPOSIT_ID")
    if DRY:
        doi, dep_id, bucket = "10.5281/zenodo.DRYRUN", "DRYRUN", None
    elif dep_id:
        dep = req("GET", f"{API}/deposit/depositions/{dep_id}", tok)
        doi = dep["metadata"]["prereserve_doi"]["doi"]
        bucket = dep["links"]["bucket"]
        print(f"[1] 既存ドラフト {dep_id} を再開: DOI {doi}")
    else:
        dep = req("POST", f"{API}/deposit/depositions", tok, {})
        dep_id = dep["id"]
        doi = dep["metadata"]["prereserve_doi"]["doi"]
        bucket = dep["links"]["bucket"]
        print(f"[1] デポジット {dep_id} 作成・DOI 予約: {doi}")

    # 2. 題箋追記(両版・冪等)+ README バッジ
    en = PAPER / "wake_en.tex"
    ja = PAPER / "wake_ja.tex"
    rd = ROOT / "README.md"
    if not DRY:
        s = en.read_text()
        if doi not in s:
            old = "(Preprint, English version; a Japanese version accompanies this record)"
            assert old in s
            s = s.replace(old, f"(Preprint, English version; a Japanese version accompanies this record; doi:{doi})")
            en.write_text(s)
        s = ja.read_text()
        if doi not in s:
            old = "(プレプリント・和文版。英語版が正文であり、本版は訳出である)"
            assert old in s
            s = s.replace(old, f"(プレプリント・和文版、doi:{doi}。英語版が正文であり、本版は訳出である)")
            ja.write_text(s)
        s = rd.read_text()
        if doi not in s:
            badge = (f"[![DOI](https://zenodo.org/badge/DOI/{doi}.svg)]"
                     f"(https://doi.org/{doi})")
            s = s.replace("<!-- DOI badge inserted at the Zenodo release commit -->", badge)
            rd.write_text(s)
        print(f"[2] 題箋(両版)+README に doi:{doi}")

    # 3. ゲート再走(コンパイル込み — 題箋追記後の最終確認)
    if not DRY:
        sh(sys.executable, ROOT / "scripts" / "gate_check_paper.py", "--skip-refs")

    # 4. リリースコミット
    if not DRY:
        sh("git", "add", "-A")
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if r.returncode != 0:
            sh("git", "commit", "-q", "-m",
               f"release: WAKE atlas Zenodo v1 (doi:{doi})\n\n"
               "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
    rel = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    print(f"[4] リリースコミット: {rel}")

    # 5. アーカイブ生成 + sha256(リポジトリ外に生成)
    tar = SCRATCH / "wake-atlas-v1.tar.gz"
    if not DRY:
        sh("git", "archive", "--format=tar.gz", "-o", str(tar), "HEAD")
    sha = hashlib.sha256(tar.read_bytes()).hexdigest() if tar.exists() else "-"
    print(f"[5] wake-atlas-v1.tar.gz: {tar.stat().st_size if tar.exists() else 0} bytes\n    sha256 {sha}")

    # 6. メタデータ
    md = dict(METADATA)
    md["metadata"]["description"] = build_description()
    if DRY:
        print("[6] (dry) metadata:", json.dumps(md["metadata"], ensure_ascii=False)[:300], "…")
    else:
        req("PUT", f"{API}/deposit/depositions/{dep_id}", tok, md)
        print("[6] メタデータ設定(ORCID・CC BY 4.0・related=数学論文DOI・日英説明)")

    # 7. アップロード(md5 照合)
    ups = [PAPER / f for f in FILES] + [REL / f for f in DATA_FILES] + [tar]
    for f in ups:
        if DRY:
            print(f"[7] (dry) upload {f.name}")
            continue
        data = f.read_bytes()
        res = req("PUT", f"{bucket}/{f.name}", tok, data,
                  ctype="application/octet-stream", raw=True)
        ok = (res.get("checksum", "").replace("md5:", "") ==
              hashlib.md5(data).hexdigest() and res.get("size") == len(data))
        print(f"[7] {f.name}: {len(data)} bytes md5 {'一致' if ok else '不一致!'}")
        if not ok:
            sys.exit(f"チェックサム不一致: {f.name} — 中断(publish していない)")

    # 8. publish
    if DRY:
        print("[8] (dry) publish")
        return
    pub = req("POST", f"{API}/deposit/depositions/{dep_id}/actions/publish", tok)
    print("\n=== 公開完了 ===")
    print("DOI:", pub.get("doi"))
    print("Record:", pub.get("links", {}).get("record_html"))
    print("release commit:", rel)
    print("sha256(wake-atlas-v1.tar.gz):", sha)


if __name__ == "__main__":
    main()
