"""三点セット監査 — 論文・公開 JSON・シミュレータの数値相互照合(裁定#20 手順1)

錨: シミュレータ側 = ハーネス16項目 / 論文側 = ゲート3。
本監査は第三の独立照合として、三者の看板数値を突き合わせる。

実行: python3 scripts/audit_three_artifacts.py
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REL = ROOT / "data" / "release"
SIM = ROOT / "sim"
EN = (ROOT / "docs/phase5/paper/wake_en.tex").read_text()
FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


cat = json.loads((REL / "arrival_catalog_v1.json").read_text())
mp = json.loads((REL / "exclusion_map_v1.json").read_text())
net = json.loads((REL / "flyby_network_v1.json").read_text())
mani = json.loads((REL / "MANIFEST.json").read_text())

print("## A. 論文 ⇄ JSON(看板数値は全て JSON から再導出できるか)")
lam1 = cat["rates_per_myr"]["clean"]["ipw_corrected"]["1pc"]
lam2 = cat["rates_per_myr"]["clean"]["ipw_corrected"]["2pc"]
lam5 = cat["rates_per_myr"]["clean"]["ipw_corrected"]["5pc"]
check("λ(1pc): 論文 4.49/4.5 = JSON 4.485(丸め)", round(lam1, 2) == 4.49 or round(lam1, 1) == 4.5, f"{lam1}")
check("λ(2pc): 論文 27.5 = JSON", round(lam2, 1) == 27.5, f"{lam2}")
check("λ(5pc): 論文 137.3 = JSON", round(lam5, 1) == 137.3, f"{lam5}")
ci = mp["rate_layers"]["clean_primary"]["lam1_ci95"]
check("CI95 [1.78, 8.50]: 論文 = 地図 JSON", abs(ci[0] - 1.78) < 0.005 and abs(ci[1] - 8.50) < 0.005, f"{ci}")
check("論文本文に [1.78,8.50]", "[1.78,8.50]" in EN.replace(" ", ""))
Rs = mp["axes"]["R_pc"]
lamR = mp["rate_layers"]["clean_primary"]["lambda_R"]
i307 = min(range(len(Rs)), key=lambda k: abs(Rs[k] - 3.07))
f307 = 3.0 / (lamR[i307] * (10 - 3.07 / (10 * 1.02271)))
i1 = min(range(len(Rs)), key=lambda k: abs(Rs[k] - 1.0))
f1 = 3.0 / (lamR[i1] * (10 - 1.0 / (10 * 1.02271)))
check("f*(3.07): 論文 5.0e-3 = JSON 再計算", round(f307, 3) == 0.005, f"{f307:.4e}")
check("f*(1pc): 論文 6.8e-2 = JSON 再計算", round(f1, 3) == 0.068, f"{f1:.4e}")
check("橋係数: 論文 5.3 = JSON", mp["rate_layers"]["bridge_reference"]["factor"] == 5.3)
dv01 = net["results"]["0.1"]["best_transfer_dv_kms"]
dv10 = net["results"]["1.0"]["best_transfer_dv_kms"]
check("Δv: 論文 5.93/5.85(看板 5.8)= 網 JSON", dv01 == 5.93 and dv10 == 5.85, f"{dv01}/{dv10}")
check("ノード数: 論文 646 = 網 JSON", net["n_nodes"] == 646)
check("カタログ数: 論文 2,197 = JSON", cat["n_entries"] == 2197)
gj = next(e for e in cat["entries"] if e.get("source_id_str") == "4270814637616488064")
check("GJ710: 論文 +1.294 Myr = カタログ中央値", abs(gj["t_ph_myr"]["median"] - 1.294) < 0.001, f"{gj['t_ph_myr']['median']}")
check("GJ710: 論文 0.0519(MW2014 主経路)= カタログ", abs(gj["d_ph_pc"]["median"] - 0.0519) < 0.0005, f"{gj['d_ph_pc']['median']}")
hd = next(e for e in cat["entries"] if e.get("source_id_str") == "510911618569239040")
check("HD7977: 論文 0.037 pc / −2.76 Myr = カタログ",
      abs(hd["d_ph_pc"]["median"] - 0.037) < 0.001 and abs(hd["t_ph_myr"]["median"] + 2.76) < 0.005,
      f"{hd['d_ph_pc']['median']}/{hd['t_ph_myr']['median']}")
check("地図版: 論文 1.0.1 = JSON", mp["map_version"] == "1.0.1")
tl = mp["theorem_layer"]
check("三値凡例(日英 3+3)", len(tl["legend"]) == 3 and len(tl["legend_en"]) == 3)
check("E9 帯 1.5–2.0(日英注記)", all("1.5–2.0" in tl[k] for k in ("numeric_threshold_note", "numeric_threshold_note_en")))
check("直接通過 d≤0.1pc = 2 件(HD7977+GJ710)", net["results"]["0.1"]["n_direct_passages"] == 2,
      f"{net['results']['0.1']['n_direct_passages']}")

print("## B. シミュレータ ⇄ 論文(ハーネス期待値 = 論文数値)")
hjs = (SIM / "js/harness.js").read_text()
for name, pat in [("4.49", r"4\.49"), ("137.3", r"137\.3"), ("2197", "2197"),
                  ("1.0.1", r"1\.0\.1"), ("5.93", r"5\.93"), ("0.0519", r"0\.0519"),
                  ("1.2943", r"1\.2943"), ("646", "646"),
                  ("f* 帯 4.5e-3–5.6e-3", r"4\.5e-3.*5\.6e-3")]:
    check(f"ハーネス期待値 {name}", re.search(pat, hjs) is not None)
n_named = len(re.findall(r't\("hk', hjs))
check("ハーネス検査数 16(名前付き13+sha256×3)", n_named == 13 and len(mani["files"]) == 3,
      f"名前付き {n_named} + sha256 {len(mani['files'])}")

print("## C. シミュレータ ⇄ JSON(供給同一性 — sha256)")
for name, meta in mani["files"].items():
    h_rel = hashlib.sha256((REL / name).read_bytes()).hexdigest()
    h_sim = hashlib.sha256((SIM / "data" / name).read_bytes()).hexdigest()
    check(f"{name}: release = sim = MANIFEST", h_rel == h_sim == meta["sha256"], h_rel[:12])
h_manir = hashlib.sha256((REL / "MANIFEST.json").read_bytes()).hexdigest()
h_manis = hashlib.sha256((SIM / "data/MANIFEST.json").read_bytes()).hexdigest()
check("MANIFEST.json: release = sim", h_manir == h_manis)

print()
if FAIL:
    print(f"三点セット監査: {len(FAIL)} 件 FAIL → {FAIL}")
    sys.exit(1)
print("三点セット監査: 全項目 PASS")
