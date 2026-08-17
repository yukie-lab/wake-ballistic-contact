"""数学論文 付録C完成の品質ゲート検査(起草指示書 v1.1 §8 の G 翻訳)

対象: docs/phase-r/paper/paper.tex(arXiv 自己完結版 = Zenodo v2)
ゲート:
  1  G1: 付録C内のリポジトリ参照プレースホルダ残存ゼロ
  2  フォーク6改称+C系列脚注の反映(強度記述の不変込み)
  3  G2: 定数追跡(指示書指定9定数の転写一致)
  4  G3: 認証数値の照合(付録A表 vs C.3 参照値/スポット審査独立再現値)
  5  コンパイル成果物の存在(tectonic は別途実行 — 本スクリプトは検査のみ)
終了コード: 全ゲート PASS で 0
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "docs/phase-r/paper/paper.tex"
src = TEX.read_text(encoding="utf-8")

# 付録Cの領域 = \section{Proof details} から \bibliographystyle まで
m = re.search(r"\\section\{Proof details\}.*?(?=\\bibliographystyle)", src, re.S)
assert m, "付録C領域が特定できない"
appc = m.group(0)

fails = []


def check(gate, name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(f"gate{gate}: {name}")


print("## ゲート1: G1 — 付録C内リポジトリ参照プレースホルダ")
for phrase in ["bundled repository", "wake-repo-v1.tar.gz",
               "c2-proof-final.md", "claims.md"]:
    n = appc.count(phrase)
    check(1, f"'{phrase}' 付録C内 0件", n == 0, f"{n} 件")

print("## ゲート2: フォーク6改称+脚注(裁定 2026-08-18)")
check(2, "namedprop 'Proposition' 残存ゼロ",
      "namedprop}{Proposition" not in src)
check(2, "§1 Claim 改称(numerically certified, experiment E8c)",
      "Claim (the SIR bound does not extend --- numerically certified, experiment E8c" in src)
check(2, "§4 Claim 改称(reverse channel)",
      "Claim (reverse channel --- numerically certified, experiment E8c)" in src)
check(2, "強度記述不変: certified violation of the expectation bound",
      "certified\nviolation of the \\emph{expectation bound}" in src
      or "certified violation of the \\emph{expectation bound}" in src)
check(2, "強度記述不変: does not by itself prove survival",
      "does not by itself prove survival" in src)
check(2, "C系列番号脚注(Theorem labels retain ...)",
      "Theorem labels retain" in src and "Gaps in the numbering are deliberate" in src)
check(2, "裁定#22-(2): 打切超過の Chernoff 余裕吸収の明示",
      "also absorbs the\ntruncation overflow" in appc
      or "also absorbs the truncation overflow" in appc)

print("## ゲート3: G2 — 定数追跡(付録C転写)")
constants = [
    (r"\\Ta:=\\Ts/32", "T_a = T_s/32"),
    (r"\\Tg:=64\(\\tau\+\\Ts\)", "T_g = 64(τ+T_s)"),
    (r"Split \$\[w_1,2w_1\]\$ into \$200\$", "200 分割"),
    (r"\\bar u_x:=\\wbar/\\sqrt\{17/16\}", "ū_x = w̄/√(17/16)"),
    (r"a:=\\bar u_x\\Tg/32", "a = ū_x T_g/32"),
    (r"\\ell_y:=8a", "ℓ_y = 8a"),
    (r"\\theta\^\*:=s\^\*/\(1\.05\\,\\wbar\)", "θ* = s*/(1.05w̄)"),
    (r"N_h\\?\s*:=\\?\s*\\lceil\\beta\\mu/16\\rceil", "N_h = ⌈βμ/16⌉"),
    (r"M=\\lceil2\\mu\\rceil", "M = ⌈2μ⌉"),
]
for pat, name in constants:
    check(3, name, re.search(pat, appc) is not None)

print("## ゲート4: G3 — 認証数値の照合")
appa = src[src.index("\\section{Machine certification bundle}"):
           src.index("\\section{Method record")]
for val, where, blob in [
    ("7.82", "付録A表", appa), ("0.00483", "付録A表", appa),
    ("1.688\\times10^{-9}", "付録A表", appa),
    ("2.640\\times10^{-8}", "付録A表", appa),
    ("s^*=0.0048", "C.3 幾何契約", appc),
    ("\\relL_{\\max}=7.8", "C.3 橋", appc),
    ("66.5", "C.3 スポット再現", appc), ("1.569", "C.3 スポット再現", appc),
    ("2.645\\times10^{-8}", "C.3 スポット再現", appc),
    ("7.79", "C.3 スポット再現", appc),
    ("app:certtable", "表ラベル参照", appc),
]:
    check(4, f"{where}: {val}", val in blob)

print("## ゲート6: 裁定#22 — C6a 等方性の全所在一致+生存定義")
check(6, "§1 定理文: isotropic with unbounded support",
      "$\\nu$ is isotropic with unbounded support" in src)
check(6, "§8 言及: isotropic unbounded ν",
      "and isotropic unbounded $\\nu$" in src)
check(6, "C.4 定理文再掲: isotropic with unbounded speed support",
      "is isotropic with unbounded\nspeed support" in appc
      or "is isotropic with unbounded speed support" in appc)
check(6, "非等方の残存文言なし(unbounded support 単独の定理文)",
      "and $\\nu$ has unbounded support" not in src)
check(6, "任意注記: 等方性除去の可否は不明",
      "Whether the isotropy hypothesis can be removed is unknown" in appc)
check(6, "生存定義: at arbitrarily large times(§1)",
      "non-empty at arbitrarily large\ntimes" in src
      or "non-empty at arbitrarily large times" in src)
check(6, "旧定義の残存なし(non-empty for all times)",
      "non-empty for all times" not in src)
check(6, "C.3 注記: 被覆条項による全時刻非空は定義より強い",
      "stronger than the definition of survival" in appc)

print("## ゲート5: コンパイル成果物")
pdf = TEX.parent / "paper.pdf"
ok = pdf.exists() and pdf.stat().st_mtime >= TEX.stat().st_mtime
check(5, "paper.pdf が paper.tex より新しい", ok,
      f"{pdf.stat().st_size} bytes" if pdf.exists() else "missing")

print()
if fails:
    print("結果: FAIL — " + "; ".join(fails))
    sys.exit(1)
print("結果: 全ゲート PASS")
