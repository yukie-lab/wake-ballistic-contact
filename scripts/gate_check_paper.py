"""本体論文 品質ゲート検査(裁定#16/#17 の7ゲート+通読指摘 F4 の em-dash 検査)

実行: python3 scripts/gate_check_paper.py [--skip-refs] [--skip-compile]
出力: 標準出力(ログへの追記は手動 — 走行記録として docs/phase5/paper/gate-check-main.log)
終了コード: 全ゲート PASS で 0
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAP = ROOT / "docs" / "phase5" / "paper"
EN = (PAP / "wake_en.tex").read_text()
JA = (PAP / "wake_ja.tex").read_text()
REL = ROOT / "data" / "release"
FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def strip_comments(s):
    return "\n".join(l for l in s.split("\n") if not l.lstrip().startswith("%"))


print("## ゲート1: 文言統一+em-dash 削減(F4)")
for pat in ["truly differ", "真に異なる", "証明した", "proves that visitation",
            "照会予定", "we will inquire", "確実に", "certainly", ", matching"]:
    n = strip_comments(EN).count(pat) + strip_comments(JA).count(pat)
    check(f"禁止語 {pat!r} = 0", n == 0, f"{n} 件")
# EN: 1段落 em-dash 1個まで(目安を機械規則化)/ JA: 全廃
bad = [i for i, p in enumerate(strip_comments(EN).split("\n\n"))
       if p.count("---") + p.count("—") > 1]
check("EN em-dash ≤1/段落", not bad, f"超過段落 {bad}")
nj = strip_comments(JA).count("---") + strip_comments(JA).count("—")
check("JA em-dash 全廃", nj == 0, f"{nj} 件")

print("## ゲート2: 引用機械検証")
if "--skip-refs" in sys.argv:
    log = (PAP / "refs-verification.log").read_text()
    check("verify_refs ログ ALL RESOLVED(前走)", "ALL RESOLVED" in log)
else:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_refs.py"),
                        str(PAP / "wake_refs.bib")], capture_output=True, text=True)
    check("verify_refs ALL RESOLVED", "ALL RESOLVED" in r.stdout + r.stderr,
          (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else "")

print("## ゲート3: 数値一貫性(本文 vs JSON)")
cat = json.loads((REL / "arrival_catalog_v1.json").read_text())
mp = json.loads((REL / "exclusion_map_v1.json").read_text())
net = json.loads((REL / "flyby_network_v1.json").read_text())
check("カタログ clean IPW 1pc = 4.485(本文 4.49/4.5)",
      abs(cat["rates_per_myr"]["clean"]["ipw_corrected"]["1pc"] - 4.485) < 1e-9)
check("網 Δv(0.1pc) = 5.93", abs(net["results"]["0.1"]["best_transfer_dv_kms"] - 5.93) < 0.005)
Rs = mp["axes"]["R_pc"]
lam = mp["rate_layers"]["clean_primary"]["lambda_R"]
i = min(range(len(Rs)), key=lambda k: abs(Rs[k] - 3.07))
fstar = 3.0 / (lam[i] * (10 - 3.07 / (10 * 1.02271)))
check("f*(3.07,10) ≈ 5.0e-3(JSON 再計算)", 4.5e-3 < fstar < 5.6e-3, f"{fstar:.3e}")
for pat in ["4.49", "137.3", "5.0\\times10^{-3}", "23.7", "21.3", "1{,}323",
            "646", "2{,}197", "56{,}286", "697", "5.8", "0.19"]:
    ne = EN.count(pat)
    nja = JA.count(pat)
    check(f"'{pat}' EN={ne} JA={nja}", ne > 0 and nja > 0)

print("## ゲート4: f* 定義規約の両所在(補強3)")
norm = lambda t: re.sub(r"\s+", "", t)
key = norm(r"N_{\rm vis} \ge3")
pen = norm(EN).count(key)
pja = norm(JA).count(key)
check("f* 規約 本文(EN/JA)+JSON", pen > 0 and pja > 0 and "n_crit_convention" in mp,
      f"EN={pen} JA={pja} JSON={'n_crit_convention' in mp}")

print("## ゲート5: 解釈規律")
for pat, mn in [(r"FGK", 1), (r"undecidable|判定不能", 1),
                (r"surveying, not proof|測量であって証明ではない", 1),
                (r"conditional probability|条件付き確率文", 1)]:
    ne = len(re.findall(pat, EN))
    nja = len(re.findall(pat, JA))
    check(f"'{pat}' EN={ne} JA={nja}(>0)", ne >= mn and nja >= mn)

print("## ゲート6: コンパイル")
if "--skip-compile" in sys.argv:
    check("PDF 存在(前走)", (PAP / "wake_en.pdf").exists() and (PAP / "wake_ja.pdf").exists())
else:
    for tex in ["wake_en.tex", "wake_ja.tex"]:
        r = subprocess.run(["tectonic", tex], cwd=PAP, capture_output=True, text=True)
        pdf = PAP / tex.replace(".tex", ".pdf")
        check(f"tectonic {tex}", r.returncode == 0 and pdf.exists(),
              f"{pdf.stat().st_size}B" if pdf.exists() else r.stderr[-200:])

print("## ゲート7: 日英数値集合の完全一致(小数抽出)")
NUM = re.compile(r"(?<![\d.])\d+\.\d+(?![\d.])")
sen = set(NUM.findall(strip_comments(EN)))
sja = set(NUM.findall(strip_comments(JA)))
only_en, only_ja = sorted(sen - sja), sorted(sja - sen)
check(f"数値集合 EN {len(sen)} / JA {len(sja)}", not only_en and not only_ja,
      f"ENのみ {only_en} / JAのみ {only_ja}")

print()
if FAIL:
    print(f"結果: {len(FAIL)} 件 FAIL → {FAIL}")
    sys.exit(1)
print("結果: 全ゲート PASS")
