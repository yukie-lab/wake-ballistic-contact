"""WAKE 数学論文 — Zenodo v1 公開(デポジット案の手順を一括実行)

前提: ~/.zenodo_token(chmod 600、トークンのみ1行)。トークンは
Authorization ヘッダのみで送信し、出力・ログ・コミットに残さない(TESSERA 規律)。

実行: python3 scripts/zenodo_publish.py            # 本番
      python3 scripts/zenodo_publish.py --dry-run  # API 呼び出しなしで手順確認
再開: ZENODO_DEPOSIT_ID=<id> python3 scripts/zenodo_publish.py(既存ドラフトに対して
      題箋追記以降を再実行。bucket PUT は同名上書きで冪等)

手順(裁定ログ#10 デポジット案+公開承認裁定):
 1. デポジット作成 → DOI 予約
 2. paper.tex 題箋に DOI 追記 → tectonic 再コンパイル
 3. リリースコミット
 4. git archive → wake-repo-v1.tar.gz + sha256
 5. メタデータ PUT(ORCID 0009-0005-3401-9230 / CC BY 4.0 + コード MIT 併記)
 6. bucket へ paper.pdf + tar.gz を PUT(md5 即時照合)
 7. publish → DOI・レコード URL を表示
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
PAPER = ROOT / "docs" / "phase-r" / "paper"
DRY = "--dry-run" in sys.argv


def token():
    p = Path.home() / ".zenodo_token"
    if not p.exists():
        sys.exit("~/.zenodo_token がありません。Terminal で:\n"
                 "  read -s ZT && printf '%s' \"$ZT\" > ~/.zenodo_token && "
                 "chmod 600 ~/.zenodo_token && unset ZT")
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


def build_description():
    txt = (PAPER / "abstracts.md").read_text()
    en = txt.split("## English", 1)[1].split("## 日本語", 1)[0].strip()
    ja = txt.split("## 日本語", 1)[1].strip()
    def para(t):
        return "".join(f"<p>{p.strip()}</p>" for p in t.split("\n\n") if p.strip())
    extra_en = ("<p><b>Bundle.</b> The complete artifact repository (verifier, "
                "certification logs, falsification device, experiment archive, "
                "review records) is included as wake-repo-v1.tar.gz. Code files "
                "in the archive are additionally licensed under MIT (see LICENSE "
                "in the archive); the record as a whole is CC BY 4.0.</p>")
    extra_ja = ("<p><b>同梱物</b>: 検証器・認証ログ・数値反証装置・実験 archive・"
                "審査記録の全量を wake-repo-v1.tar.gz として同梱。アーカイブ内の"
                "コードは MIT を併用宣言(LICENSE 参照)、レコード全体は CC BY 4.0。</p>")
    return ("<p><b>Abstract (English)</b></p>" + para(en) + extra_en +
            "<p><b>要旨(日本語)</b></p>" + para(ja) + extra_ja)


METADATA = {
    "metadata": {
        "upload_type": "publication",
        "publication_type": "preprint",
        "publication_date": "2026-08-16",
        "title": ("Contact processes on ballistic Poisson particles: "
                  "criticality, fronts, and when motion helps colonization"),
        "creators": [{"name": "Maeda, Yukie",
                      "orcid": "0009-0005-3401-9230"}],
        "license": "cc-by-4.0",
        "version": "v1",
        "language": "eng",
        "keywords": ["contact process", "percolation", "Poisson point process",
                     "interacting particle systems", "ballistic motion",
                     "mobile agents", "epidemics on moving populations",
                     "Fermi paradox"],
    }
}


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

    # 2. 題箋に DOI 追記(冪等)→ 再コンパイル
    tex = PAPER / "paper.tex"
    s = tex.read_text()
    if doi not in s:
        old = r"\large (Preprint --- Zenodo v1)"
        assert old in s, "題箋パターンが見つからない"
        s = s.replace(old, rf"\large (Preprint --- Zenodo v1, doi:{doi})")
        tex.write_text(s)
        print(f"[2] 題箋に doi:{doi} を追記")
    if not DRY:
        sh("tectonic", "paper.tex", cwd=PAPER)

    # 3. リリースコミット
    if not DRY:
        sh("git", "add", "-A")
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if r.returncode != 0:
            sh("git", "commit", "-q", "-m",
               f"release: Zenodo v1 (doi:{doi})\n\n"
               "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
        rel = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
        print(f"[3] リリースコミット: {rel}")

    # 4. アーカイブ生成 + sha256
    tar = PAPER / "wake-repo-v1.tar.gz"
    if not DRY:
        sh("git", "archive", "--format=tar.gz", "-o", str(tar), "HEAD")
    sha = hashlib.sha256(tar.read_bytes()).hexdigest() if tar.exists() else "-"
    print(f"[4] wake-repo-v1.tar.gz: {tar.stat().st_size if tar.exists() else 0} bytes / sha256 {sha}")

    # 5. メタデータ
    md = dict(METADATA)
    md["metadata"]["description"] = build_description()
    if DRY:
        print("[5] (dry) metadata:", json.dumps(md["metadata"], ensure_ascii=False)[:200], "...")
    else:
        req("PUT", f"{API}/deposit/depositions/{dep_id}", tok, md)
        print("[5] メタデータ設定完了(ORCID・CC BY 4.0・日英説明文)")

    # 6. ファイルアップロード(md5 照合)
    for f in (PAPER / "paper.pdf", tar):
        if DRY:
            print(f"[6] (dry) upload {f.name}")
            continue
        data = f.read_bytes()
        res = req("PUT", f"{bucket}/{f.name}", tok, data,
                  ctype="application/octet-stream", raw=True)
        local_md5 = hashlib.md5(data).hexdigest()
        remote = res.get("checksum", "").replace("md5:", "")
        ok = remote == local_md5 and res.get("size") == len(data)
        print(f"[6] {f.name}: {len(data)} bytes md5 {'一致' if ok else '不一致!'}")
        if not ok:
            sys.exit(f"チェックサム不一致: {f.name} — 中断(publish していない)")

    # 7. publish
    if DRY:
        print("[7] (dry) publish")
        return
    pub = req("POST", f"{API}/deposit/depositions/{dep_id}/actions/publish", tok)
    print("\n=== 公開完了 ===")
    print("DOI:", pub.get("doi"))
    print("Record:", pub.get("links", {}).get("record_html"))
    print("sha256(wake-repo-v1.tar.gz):", sha)


if __name__ == "__main__":
    main()
