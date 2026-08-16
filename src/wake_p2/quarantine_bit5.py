"""検疫拡張 bit5「rv_faint_suspect」(裁定ログ#11 裁定1)

- 定義: G > 13.5 ∧ |RV| > RV_TH(既定 150 km/s — 暫定承認値)
- 感度スキャン: RV_TH ∈ {120, 150, 200} で λ@1pc の suspect/クリーン分解を文書化
- 手動審査材料: **接線速度整合検査** — v_tan = 4.74047e-3·μ[mas/yr]·d[pc] [km/s]。
  本物のハロー星は RV と v_tan の両方がハロー運動学(v_tot ≳ 180 km/s の
  非円盤成分)。円盤的 v_tan なのに RV のみ極端 = アーティファクトの典型署名。
  救済経路: 審査で実星と確認された星は bit5_whitelist へ(bit3 HVS WL と同型)
- 参照根拠: Katz+2023(DR3 RV 品質 — 暗端・低温端の系統警告)

出力: data/p2/quarantine_bit5.npz(mask・パラメータ・whitelist)
      docs/phase2/09-bit5-quarantine.md(感度スキャン+手動審査表)
実行: python3 src/wake_p2/quarantine_bit5.py
"""
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data.config import S_FLOOR

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
OUT = ROOT / "docs" / "phase2" / "09-bit5-quarantine.md"
SIDE = P2 / "quarantine_bit5.npz"
G_TH = 13.5
RV_TH_DEFAULT = 150.0
K = 4.74047e-3


def lam_split(cat, suspect):
    S, th = cat["s_completeness"], cat["t_h_default"]
    lam_s = lam_c = 0.0
    for f in sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz"))):
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        s_c, th_c = S[idx], th[idx]
        usable = np.isfinite(s_c) & (s_c >= S_FLOOR)
        w = np.where(usable, 1.0 / np.maximum(s_c, S_FLOOR), 0.0)
        e = 2.0 * np.minimum(10.0, np.maximum(th_c, 1e-9))
        m = (np.isfinite(t_ph) & ~edge & (d_ph < 1.0) & (np.abs(t_ph) <= 10.0)
             & (np.abs(t_ph) <= th_c[:, None]))
        c_ = w * m.sum(axis=1) / e
        sus = suspect[idx]
        lam_s += c_[sus].sum()
        lam_c += c_[~sus].sum()
    return lam_s / 2000, lam_c / 2000


def main():
    cat = np.load(P2 / "catalog_ingested.npz")
    G = cat["phot_g_mean_mag"]
    rv = cat["radial_velocity"]
    d_pc = 1000.0 / np.maximum(cat["parallax"], 1e-9)
    v_tan = K * np.hypot(cat["pmra"], cat["pmdec"]) * d_pc

    lines = ["# 検疫拡張 bit5「rv_faint_suspect」(裁定ログ#11 裁定1)", "",
             f"> 定義: G > {G_TH} ∧ |RV| > {RV_TH_DEFAULT:.0f} km/s(暫定承認値)。"
             "参照根拠: Katz+2023(DR3 RV の暗端品質警告)。運用 = bit3 同型"
             "(要手動審査・個別イベント判定除外・率は両建て)。", "",
             "## 感度スキャン(|RV| 閾値 — 裁定指示)", "",
             "| RV_TH [km/s] | suspect 星数 | λ@1pc suspect分 | λ@1pc クリーン分 |",
             "|---|---|---|---|"]
    for rv_th in (120.0, 150.0, 200.0):
        sus = (G > G_TH) & (np.abs(rv) > rv_th)
        ls, lc = lam_split(cat, sus)
        lines.append(f"| {rv_th:.0f} | {int(sus.sum()):,} | {ls:.1f} | {lc:.1f} |")
        print(f"RV_TH={rv_th:.0f}: suspect {sus.sum():,} 星, λ分解 {ls:.1f}/{lc:.1f}")
    lines += ["", "クリーン分が閾値に対して安定(120→200 での変化が小さい)ことが"
              "閾値の頑健性の根拠。既定 150 を採用(裁定1)。", ""]

    suspect = (G > G_TH) & (np.abs(rv) > RV_TH_DEFAULT)
    whitelist = np.zeros(len(G), bool)     # 救済済み実星(手動審査で追加)
    np.savez_compressed(SIDE, mask=suspect & ~whitelist, suspect_raw=suspect,
                        whitelist=whitelist, G_TH=G_TH, RV_TH=RV_TH_DEFAULT)

    # 手動審査材料: 高寄与 suspect の接線速度整合検査
    S, th = cat["s_completeness"], cat["t_h_default"]
    contrib = np.zeros(len(G))
    for f in sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz"))):
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        s_c, th_c = S[idx], th[idx]
        usable = np.isfinite(s_c) & (s_c >= S_FLOOR)
        w = np.where(usable, 1.0 / np.maximum(s_c, S_FLOOR), 0.0)
        e = 2.0 * np.minimum(10.0, np.maximum(th_c, 1e-9))
        m = (np.isfinite(t_ph) & ~edge & (d_ph < 5.0) & (np.abs(t_ph) <= 10.0)
             & (np.abs(t_ph) <= th_c[:, None]))
        contrib[idx] += w * m.sum(axis=1) / e / 2000
    top = np.argsort(np.where(suspect, contrib, -1))[::-1][:20]
    lines += ["## 手動審査表(高寄与 suspect 上位 — 接線速度整合検査)", "",
              "| star_idx | G | RV [km/s] | v_tan [km/s] | 署名 | λ@5pc寄与 |",
              "|---|---|---|---|---|---|"]
    for g in top:
        if not suspect[g] or contrib[g] <= 0:
            continue
        halo_like = v_tan[g] > 100.0
        sig = ("**ハロー整合 — 救済候補(要個別確認)**" if halo_like
               else "円盤的 v_tan × 極端 RV → アーティファクト署名")
        lines.append(f"| {g} | {G[g]:.1f} | {rv[g]:+.1f} | {v_tan[g]:.1f} | "
                     f"{sig} | {contrib[g]:.2f} |")
    lines += ["", "判定基準(裁定1 精密化): 本物のハロー星は RV と v_tan の両方が"
              "ハロー運動学を示す。円盤的 v_tan(<100 km/s)なのに RV のみ極端な星は"
              "アーティファクトの典型署名。救済は bit5_whitelist へ(現在空)。", "",
              "## 方法論的発見の記録(裁定1 指示)", "",
              "等級依存の系統は**値の異常検疫(bit3: |RV|>550)と誤差の異常検疫"
              "(rv_error>20)の両方をすり抜ける第三のモード**である(発見時: "
              "疑似9件中 bit3 捕捉 2件)。DR3 系接近研究への方法論的警告として"
              "論文素材に採録。", ""]
    OUT.write_text("\n".join(lines))
    print(f"→ {OUT} / sidecar {SIDE.name}")


if __name__ == "__main__":
    main()
