"""本体論文の図生成(5図 — 骨格 v0.1 対応)

再現: python3 src/wake_p5/paper_figs_main.py
出力: docs/phase5/paper/figs/fig{1..5}.pdf
"""
import glob
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from wake_data.config import S_FLOOR
from wake_data.horizon_eff import effective_horizons

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
P3 = ROOT / "data" / "p3"
P4 = ROOT / "data" / "p4"
PR = ROOT / "data" / "phase_r"
FIGS = ROOT / "docs" / "phase5" / "paper" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})
N_SURR = 2000


def fig1_lambda_t():
    """λ(t) 露出正規化(クリーン)+判定不能の影 = 証拠の地平線"""
    cat = np.load(P2 / "catalog_ingested.npz")
    b5 = np.load(P2 / "quarantine_bit5.npz")["mask"]
    S = cat["s_completeness"]
    th, _ = effective_horizons(cat)
    bins = np.arange(-10, 10 + 1e-9, 1.0)
    lam_b = np.zeros(len(bins) - 1)
    shadow = np.zeros(len(bins) - 1)
    for f in sorted(glob.glob(str(P2 / "mc" / "chunk_*.npz"))):
        z = np.load(f)
        idx = z["star_idx"]
        t_ph, d_ph, edge = z["t_ph"], z["d_ph"], z["edge"]
        s_c, th_c = S[idx], th[idx]
        usable = np.isfinite(s_c) & (s_c >= S_FLOOR) & ~b5[idx]
        w = np.where(usable, 1.0 / np.maximum(s_c, S_FLOOR), 0.0)
        base = np.isfinite(t_ph) & ~edge & (d_ph < 5.0) & (np.abs(t_ph) <= 10.0)
        dom = base & (np.abs(t_ph) <= th_c[:, None])
        r, c = np.nonzero(dom)
        b = np.clip(np.digitize(t_ph[r, c], bins) - 1, 0, len(bins) - 2)
        np.add.at(lam_b, b, w[r])
        r2, c2 = np.nonzero(base & ~dom)
        b2 = np.clip(np.digitize(t_ph[r2, c2], bins) - 1, 0, len(bins) - 2)
        np.add.at(shadow, b2, 1.0)
    lam_b /= N_SURR
    shadow /= N_SURR
    mid = 0.5 * (bins[:-1] + bins[1:])
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.bar(mid, lam_b, width=0.92, color="#2c3e50",
           label="control region (clean, IPW)")
    ax2 = ax.twinx()
    ax2.fill_between(mid, shadow, color="#bdc3c7", alpha=0.5, step="mid",
                     label="beyond individual horizons (undecidable)")
    ax2.set_ylabel("undecidable events per Myr (raw)", color="#7f8c8d")
    ax.set_xlabel(r"perihelion time $t_{\rm ph}$ [Myr]")
    ax.set_ylabel(r"$\lambda(t)$ [Myr$^{-1}$], $d<5$ pc")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGS / "fig1_lambda_t.pdf")
    plt.close(fig)


def fig2_exclusion_map():
    """R–f 平面の f* 境界+三値定理レイヤ+判定不能"""
    doc = json.loads((P3 / "exclusion_map_v1.json").read_text())
    R = np.array(doc["axes"]["R_pc"])
    lam = np.array(doc["rate_layers"]["clean_primary"]["lambda_R"], float)
    flags = np.array(doc["rate_layers"]["clean_primary"]["flags"])
    Tef = np.array(doc["visit_layer"]["T_eff_matrix_RxV"])[:, 1]   # v=10 km/s
    ok = flags < 2
    fstar = 3.0 / (lam[ok] * np.maximum(Tef[ok], 1e-9))
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    ax.plot(R[ok], fstar, color="#c0392b", lw=2,
            label=r"$f^*$ (clean primary, 95%)")
    ax.plot(R[ok], fstar / 5.3, color="#c0392b", lw=1.2, ls="--",
            label=r"$f^*/5.3$ (population-bridge reference)")
    ax.fill_between(R[ok], fstar, 1.0, color="#e74c3c", alpha=0.15)
    ax.text(1.5, 0.2, "should have\nbeen visited", fontsize=8, color="#c0392b")
    ax.text(0.35, 3e-4, "consistent with silence", fontsize=8, color="#2c3e50")
    ax.axvspan(5.0, 10.0, color="#95a5a6", alpha=0.35)
    ax.text(6.2, 3e-3, "undecidable\n(R > 5 pc)", fontsize=7.5)
    ax.axvspan(0.1, 1.0, color="#f1c40f", alpha=0.12)
    ax.text(0.13, 3e-3, r"$d^2$ extrapolation", fontsize=7, rotation=90)
    ax.axvline(3.07, color="k", lw=0.7, ls=":")
    ax.text(3.15, 2e-4, "CN19 standard", fontsize=7, rotation=90)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.1, 10)
    ax.set_ylim(1e-4, 1)
    ax.set_xlabel(r"probe range $R = d_p$ [pc]")
    ax.set_ylabel(r"settled fraction $f$")
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIGS / "fig2_exclusion_map.pdf")
    plt.close(fig)


def fig3_flyby():
    """通過ノードの (t, d) + 最小乗換"""
    idxs = json.loads((P4 / "flyby_network_v1.json").read_text())
    sys.path.insert(0, str(ROOT / "src"))
    from wake_p4.flyby_network import nominal_perihelia, min_transfer
    gi, tmed, x_peri, vel = nominal_perihelia()
    d = np.linalg.norm(x_peri, axis=1)
    best, pair = min_transfer(tmed, x_peri, vel, d, 0.1)
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.scatter(tmed, d, s=8, color="#7f8c8d", alpha=0.6, label="clean passages")
    if pair:
        i, j = pair
        ax.plot([tmed[i], tmed[j]], [d[i], d[j]], color="#c0392b", lw=1.5)
        ax.scatter([tmed[i], tmed[j]], [d[i], d[j]], s=30, color="#c0392b",
                   zorder=5, label=fr"min transfer $\Delta v={best:.1f}$ km/s")
    ax.axhline(0.1, color="#2c3e50", lw=0.7, ls="--")
    ax.text(-9.7, 0.115, r"$d_{\rm visit}=0.1$ pc", fontsize=7)
    ax.set_yscale("log")
    ax.set_xlabel(r"$t_{\rm ph}$ [Myr]")
    ax.set_ylabel(r"perihelion distance $d$ [pc]")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIGS / "fig3_flyby.pdf")
    plt.close(fig)


def fig4_binwidth():
    """付録C: ビン幅=隠れ正則化(非単調走査)"""
    widths = [0.5, 1.0, 1.5, 2.0, 3.0]
    rates = [46.5, 23.7, 20.4, 27.1, 20.7]
    errs = [5.1, 2.6, 2.2, 3.0, 2.2]
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    ax.errorbar(widths, rates, yerr=errs, fmt="o-", color="#2c3e50", ms=4)
    ax.axhspan(19.7 - 2.2, 19.7 + 2.2, color="#27ae60", alpha=0.15,
               label=r"BJ+18: $19.7\pm2.2$")
    ax.axvline(1.5, color="#c0392b", lw=0.8, ls=":")
    ax.text(1.55, 40, "adopted default\n(±15% grid syst.)", fontsize=7,
            color="#c0392b")
    ax.set_xlabel(r"completeness-map bin width $\Delta t$ [Myr]")
    ax.set_ylabel(r"rate@1pc [Myr$^{-1}$] (BJ-convention, $G\leq12.5$)")
    ax.legend(frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIGS / "fig4_binwidth.pdf")
    plt.close(fig)


def fig5_e9():
    """E9: 実測運動学の m 閾値"""
    res = json.loads((PR / "E9_real_kinematics.json").read_text())
    ps = sorted({r["p"] for r in res})
    ms = [np.mean([r["m"] for r in res if r["p"] == p]) for p in ps]
    sv = [np.mean([r["grew"] for r in res if r["p"] == p]) for p in ps]
    n = [len([r for r in res if r["p"] == p]) for p in ps]
    err = [np.sqrt(max(s * (1 - s), 1e-9) / k) for s, k in zip(sv, n)]
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    ax.errorbar(ms, sv, yerr=err, fmt="s-", color="#c0392b", ms=4,
                label=r"measured $\nu$ (DR3, scale-matched)")
    ax.axvspan(1.0, 1.3, color="#2c3e50", alpha=0.15,
               label="isotropic calibration (E1)")
    ax.axvspan(1.5, 2.0, color="#c0392b", alpha=0.12,
               label=r"measured-$\nu$ band (E9)")
    ax.set_xlabel(r"$m = p(\deg + \lambda T_s)$")
    ax.set_ylabel("survival fraction")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "fig5_e9.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig1_lambda_t()
    print("fig1 done")
    fig2_exclusion_map()
    print("fig2 done")
    fig3_flyby()
    print("fig3 done")
    fig4_binwidth()
    print("fig4 done")
    fig5_e9()
    print("fig5 done")
    print(f"→ {FIGS}")
