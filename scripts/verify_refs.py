"""引用の機械検証(裁定ログ#10 組立仕様5)

refs.bib の全エントリについて doi / eprint(arXiv ID)を抽出し、
- DOI: https://doi.org/<doi> への HEAD/GET が 200/302 で解決すること
- arXiv: export.arxiv.org API がメタデータ(タイトル)を返すこと
を機械確認する。**どちらも持たないエントリ、または解決不能はエラー**
(削除ではなく停止・報告 — 指示書どおり)。

実行: python3 scripts/verify_refs.py docs/phase-r/paper/refs.bib
出力: docs/phase-r/paper/refs-verification.log
"""
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "wake-refs-verify/1.0 (mailto:greatreset@gmail.com)"}


def entries(bib_text):
    for m in re.finditer(r"@\w+\{([^,]+),(.*?)\n\}", bib_text, re.S):
        key, body = m.group(1).strip(), m.group(2)
        def field(name):
            fm = re.search(name + r"\s*=\s*[{\"]([^}\"]+)[}\"]", body, re.I)
            return fm.group(1).strip() if fm else None
        yield key, field("doi"), field("eprint"), field("title")


def check_doi(doi):
    req = urllib.request.Request(f"https://doi.org/{doi}", headers=UA, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return 200 <= r.status < 400, f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303):
            return True, f"HTTP {e.code}"
        # 出版社の bot 対策(403 等)は DOI 不在の証拠でない — Crossref 登録簿で確認
        return check_crossref(doi, e.code)
    except Exception as e:
        return False, str(e)


def check_crossref(doi, first_code):
    import json as _json
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=30) as r:
            meta = _json.load(r)
        title = (meta.get("message", {}).get("title") or ["?"])[0]
        return True, f"doi.org HTTP {first_code}; Crossref OK: {title[:60]}"
    except Exception as e:
        return False, f"doi.org HTTP {first_code}; Crossref FAIL: {e}"


def check_arxiv(eid):
    url = f"https://export.arxiv.org/api/query?id_list={eid}&max_results=1"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=30) as r:
            text = r.read().decode()
        m = re.search(r"<title>([^<]+)</title>\s*", text)
        titles = re.findall(r"<title>([^<]+)</title>", text)
        title = titles[1].strip() if len(titles) > 1 else None
        ok = title is not None and "Error" not in (title or "")
        return ok, title or "no entry"
    except Exception as e:
        return False, str(e)


def main(bib_path):
    bib = Path(bib_path).read_text()
    log = []
    n_fail = 0
    for key, doi, eprint, title in entries(bib):
        marks = []
        ok_any = False
        if doi:
            ok, msg = check_doi(doi)
            marks.append(f"doi:{doi} -> {'OK' if ok else 'FAIL'} ({msg})")
            ok_any |= ok
            time.sleep(1.0)
        if eprint:
            ok, msg = check_arxiv(eprint)
            marks.append(f"arXiv:{eprint} -> {'OK' if ok else 'FAIL'} ({msg[:80]})")
            ok_any |= ok
            time.sleep(1.0)
        if not doi and not eprint:
            marks.append("NO doi/eprint — VIOLATION of assembly spec 5")
            ok_any = False
        status = "RESOLVED" if ok_any else "UNRESOLVED"
        if not ok_any:
            n_fail += 1
        log.append(f"[{status}] {key}: " + " | ".join(marks))
        print(log[-1])
    out = Path(bib_path).parent / "refs-verification.log"
    header = (f"# 引用機械検証ログ({time.strftime('%Y-%m-%d %H:%M')} JST)\n"
              f"# 対象: {bib_path} / 全 {len(log)} 件 / 未解決 {n_fail} 件\n")
    out.write_text(header + "\n".join(log) + "\n")
    print(f"\n{'ALL RESOLVED' if n_fail == 0 else f'{n_fail} UNRESOLVED — STOP'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else
                  "docs/phase-r/paper/refs.bib"))
