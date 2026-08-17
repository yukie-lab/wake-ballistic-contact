"""WAKE 数学論文 — Zenodo v2 公開(New version フロー・裁定ログ#22 完結指示 §2)

前提: ~/.zenodo_token(chmod 600、トークンのみ1行)。トークンは Authorization
ヘッダのみで送信し、出力・ログ・コミットに残さない(TESSERA 規律)。

実行: python3 scripts/zenodo_publish_v2.py            # 本番
      python3 scripts/zenodo_publish_v2.py --dry-run  # API 呼び出しなしで手順確認
再開: ZENODO_DEPOSIT_ID=<draft id> python3 scripts/zenodo_publish_v2.py
      (既存 v2 ドラフトに対して題箋追記以降を再実行。bucket PUT は同名上書きで冪等)

手順(v1 = zenodo_publish.py と同一の確立手順の New version 版):
 0. トークン疎通確認(GET /deposit/depositions — 死んでいれば即停止)
 1. レコード 21955413 の newversion 作成 → v2 版 DOI 予約値の取得
 2. paper.tex 題箋を「Zenodo v2, doi:<v2DOI>; v1: doi:10.5281/zenodo.21955413」
    形式に更新(冪等)→ tectonic 再コンパイル
 3. リリースコミット
 4. git archive → wake-repo-v2.tar.gz + sha256
 5. 継承ファイルの削除(v2 は paper.pdf + v2 tar.gz の2点構成)
 6. メタデータ更新: v1 から継承した全メタデータ(related identifiers 含む)を
    保持し、version=v2 / publication_date=今日 / description に改版理由段落を
    追記、同梱物の文言を v2 に更新。Creator ORCID は継承で維持
 7. bucket へ paper.pdf + wake-repo-v2.tar.gz を PUT(md5 即時照合)
 8. publish → 公開 API(GET /api/records/<id>)で読み戻し検証
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

API = "https://zenodo.org/api"
V1_RECID = "21955413"
V1_DOI = "10.5281/zenodo.21955413"
ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "docs" / "phase-r" / "paper"
DRY = "--dry-run" in sys.argv

VERSION_REASON_EN = (
    "Appendix C made self-contained; label precision (Section 4 claim); "
    "C-series footnote; hypothesis precision (C6a isotropy, survival "
    "definition). No change to mathematical content.")


def token():
    p = Path.home() / ".zenodo_token"
    if not p.exists():
        sys.exit("~/.zenodo_token がありません。前田さんに再設置を依頼:\n"
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


def main():
    tok = None if DRY else token()

    # 0. 疎通確認(指示: 死んでいれば停止)
    if not DRY:
        try:
            req("GET", f"{API}/deposit/depositions?size=1", tok)
            print("[0] トークン疎通 OK")
        except Exception as e:
            sys.exit(f"[0] トークン疎通失敗 — 停止。前田さんに再設置を依頼。({e})")

    # 1. New version → v2 ドラフト取得 + 版 DOI 予約値
    dep_id = os.environ.get("ZENODO_DEPOSIT_ID")
    if DRY:
        doi, dep_id, bucket, dep = f"10.5281/zenodo.DRYRUN", "DRYRUN", None, None
        concept = "(dry)"
    elif dep_id:
        dep = req("GET", f"{API}/deposit/depositions/{dep_id}", tok)
        doi = dep["metadata"]["prereserve_doi"]["doi"]
        bucket = dep["links"]["bucket"]
        concept = dep.get("conceptdoi", "?")
        print(f"[1] 既存 v2 ドラフト {dep_id} を再開: 版DOI {doi} / concept {concept}")
    else:
        nv = req("POST",
                 f"{API}/deposit/depositions/{V1_RECID}/actions/newversion",
                 tok)
        draft_url = nv["links"]["latest_draft"]
        dep = req("GET", draft_url, tok)
        dep_id = dep["id"]
        doi = dep["metadata"]["prereserve_doi"]["doi"]
        bucket = dep["links"]["bucket"]
        concept = dep.get("conceptdoi", "?")
        print(f"[1] New version ドラフト {dep_id}: 版DOI予約 {doi} / concept {concept}")

    # 2. 題箋更新(冪等)→ 再コンパイル
    tex = PAPER / "paper.tex"
    s = tex.read_text()
    new_line = (rf"\large (Preprint --- Zenodo v2, doi:{doi}; "
                rf"v1: doi:{V1_DOI})")
    if DRY:
        print(f"[2] (dry) 題箋: {new_line}")
    elif new_line not in s:
        old = rf"\large (Preprint --- Zenodo v2; v1: doi:{V1_DOI})"
        assert old in s, "題箋パターンが見つからない(手動確認要)"
        tex.write_text(s.replace(old, new_line))
        print(f"[2] 題箋に v2 版 DOI を挿入: {doi}")
    if not DRY:
        sh("tectonic", "paper.tex", cwd=PAPER)
        sh("python3", "scripts/gate_check_mathpaper_c.py")

    # 3. リリースコミット
    if not DRY:
        sh("git", "add", "-A")
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if r.returncode != 0:
            sh("git", "commit", "-q", "-m",
               f"release: Zenodo v2 (doi:{doi})\n\n"
               "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
        rel = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
        print(f"[3] リリースコミット: {rel}")

    # 4. アーカイブ生成 + sha256
    tar = PAPER / "wake-repo-v2.tar.gz"
    if not DRY:
        sh("git", "archive", "--format=tar.gz", "-o", str(tar), "HEAD")
    sha = hashlib.sha256(tar.read_bytes()).hexdigest() if tar.exists() else "-"
    size = tar.stat().st_size if tar.exists() else 0
    print(f"[4] wake-repo-v2.tar.gz: {size} bytes / sha256 {sha}")

    # 5. 継承ファイル削除(v2 構成 = paper.pdf + wake-repo-v2.tar.gz)
    if not DRY:
        for f in req("GET", f"{API}/deposit/depositions/{dep_id}/files", tok):
            if f["filename"] not in ("paper.pdf", "wake-repo-v2.tar.gz"):
                req("DELETE",
                    f"{API}/deposit/depositions/{dep_id}/files/{f['id']}", tok)
                print(f"[5] 継承ファイル削除: {f['filename']}")

    # 6. メタデータ: 継承分を保持しつつ v2 差分のみ更新
    if DRY:
        print("[6] (dry) metadata: version=v2, date=today, 改版理由段落を追記")
    else:
        md = dep["metadata"]
        md.pop("prereserve_doi", None)
        md.pop("doi", None)  # 予約版DOIは publish で確定(継承 v1 DOI の残置を防ぐ)
        md["version"] = "v2"
        md["publication_date"] = date.today().isoformat()
        desc = md.get("description", "")
        note = (f"<p><b>Version note (v2).</b> {VERSION_REASON_EN}</p>")
        if "Version note (v2)" not in desc:
            desc = note + desc
        md["description"] = desc.replace("wake-repo-v1.tar.gz",
                                         "wake-repo-v2.tar.gz")
        req("PUT", f"{API}/deposit/depositions/{dep_id}", tok,
            {"metadata": md})
        print("[6] メタデータ更新(version=v2 / 改版理由 / 同梱物 v2 文言。"
              "creators・related identifiers は継承維持)")

    # 7. アップロード(md5 照合)
    for f in (PAPER / "paper.pdf", tar):
        if DRY:
            print(f"[7] (dry) upload {f.name}")
            continue
        data = f.read_bytes()
        res = req("PUT", f"{bucket}/{f.name}", tok, data,
                  ctype="application/octet-stream", raw=True)
        local_md5 = hashlib.md5(data).hexdigest()
        remote = res.get("checksum", "").replace("md5:", "")
        ok = remote == local_md5 and res.get("size") == len(data)
        print(f"[7] {f.name}: {len(data)} bytes md5 {'一致' if ok else '不一致!'}")
        if not ok:
            sys.exit(f"チェックサム不一致: {f.name} — 中断(publish していない)")

    # 8. publish → 公開 API 読み戻し
    if DRY:
        print("[8] (dry) publish → 読み戻し検証")
        return
    pub = req("POST", f"{API}/deposit/depositions/{dep_id}/actions/publish",
              tok)
    rec_id = pub.get("record_id") or pub.get("id")
    public = req("GET", f"{API}/records/{rec_id}", tok)
    files = sorted(f["key"] for f in public.get("files", []))
    print("\n=== 公開完了(読み戻し検証済み)===")
    print("v2 DOI:", pub.get("doi"))
    print("concept DOI:", pub.get("conceptdoi"))
    print("Record:", pub.get("links", {}).get("record_html"))
    print("files:", files)
    print("version:", public.get("metadata", {}).get("version"))
    print("改版理由表示:",
          "OK" if "Version note (v2)" in
          public.get("metadata", {}).get("description", "") else "要確認")
    print("sha256(wake-repo-v2.tar.gz):", sha)


if __name__ == "__main__":
    main()
