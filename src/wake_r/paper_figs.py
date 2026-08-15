"""論文図の生成(裁定ログ#10 組立仕様4 — 優先3図、各実験1図まで)

再現: python3 src/wake_r/paper_figs.py
入力: data/phase_r/{E5_front,E4c_dip,E7_dwell,E8c_counterexample}.json(archive 済み)
出力: docs/phase-r/paper/figs/fig{1,2,3}.pdf
"""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "phase_r"
OUT = ROOT / "docs" / "phase-r" / "paper" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 9, "figure.dpi": 150})


def fig1_front():
    """E5: 前線の二分 — 非有界(ガウス)= 加速、有界 = 線形"""
    runs = json.load(open(DATA / "E5_front.json"))
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    style = {"gauss": dict(color="#c0392b", label="unbounded (Gaussian)"),
             "fixed": dict(color="#2c3e50", label="bounded speed")}
    seen = set()
    for r in runs:
        k = r["kind"]
        ax.plot(r["t"], r["extent"], color=style[k]["color"], alpha=0.6, lw=1.0,
                label=style[k]["label"] if k not in seen else None)
        seen.add(k)
    ax.set_xlabel(r"$t$")
    ax.set_ylabel(r"front extent $R(t)$")
    ax.legend(frameon=False, loc="upper left")
    ax.annotate(r"fitted growth exponent $1.34\pm0.14$", xy=(0.45, 0.62),
                xycoords="axes fraction", color="#c0392b", fontsize=8)
    ax.annotate(r"$0.98\pm0.01$ (linear)", xy=(0.60, 0.28),
                xycoords="axes fraction", color="#2c3e50", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_front_dichotomy.pdf")
    plt.close(fig)


def _survival_curve(path):
    agg = {}
    for r in json.load(open(path)):
        agg.setdefault(r["sigma"], []).append(bool(r["grew"]))
    xs = sorted(agg)
    ps, errs = [], []
    for s in xs:
        g = agg[s]
        p = sum(g) / len(g)
        ps.append(p)
        errs.append(math.sqrt(max(p * (1 - p), 1e-9) / len(g)))
    return xs, ps, errs


def fig2_dichotomy():
    """E4c + E7: 規約二分法 — 進入駆動は単調、滞在要求型は最適速度"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.7))
    xs, ps, es = _survival_curve(DATA / "E4c_dip.json")
    ax1.errorbar(xs, ps, yerr=es, fmt="o-", color="#2c3e50", ms=3.5, lw=1.2)
    ax1.set_title("entry-driven (fire-and-forget)", fontsize=9)
    ax1.set_xlabel(r"velocity scale $\sigma$")
    ax1.set_ylabel("survival probability")
    ax1.set_ylim(0, 1)
    xs, ps, es = _survival_curve(DATA / "E7_dwell.json")
    ax2.errorbar(xs, ps, yerr=es, fmt="s-", color="#c0392b", ms=3.5, lw=1.2)
    ax2.set_xscale("log")
    ax2.set_title("dwell-time requirement", fontsize=9)
    ax2.set_xlabel(r"velocity scale $\sigma$")
    ax2.set_ylim(0, 0.45)
    ax2.annotate(r"optimal $\sigma^*\!\approx\!0.4$", xy=(0.4, 5 / 16),
                 xytext=(0.8, 0.38), fontsize=8,
                 arrowprops=dict(arrowstyle="->", lw=0.8))
    fig.tight_layout()
    fig.savefig(OUT / "fig2_convention_dichotomy.pdf")
    plt.close(fig)


def fig3_reverse():
    """E8c: 逆向きチャネル — E[N] が分枝上界を 4.4σ 超過"""
    rows = json.load(open(DATA / "E8c_counterexample.json"))
    totals = [sum(r) if isinstance(r, list) else int(r) for r in rows]
    n = len(totals)
    mean = sum(totals) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in totals) / (n - 1))
    sem = sd / math.sqrt(n)
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    mx = max(totals)
    ax.hist(totals, bins=range(1, mx + 2), align="left", rwidth=0.85,
            color="#7f8c8d", log=True)
    ax.axvline(1.1111, color="#2c3e50", ls="--", lw=1.2,
               label=r"branching bound $1/(1-\bar m)=1.1111$")
    ax.axvline(mean, color="#c0392b", lw=1.2,
               label=rf"measured $\mathbb{{E}}[N]={mean:.4f}\pm{sem:.4f}$")
    ax.set_xlabel(r"total transmission events $N$ per realization")
    ax.set_ylabel("count (log)")
    ax.legend(frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_reverse_channel.pdf")
    plt.close(fig)
    return mean, sem, (mean - 1.1111) / sem


if __name__ == "__main__":
    fig1_front()
    fig2_dichotomy()
    m, s, z = fig3_reverse()
    print(f"figs written to {OUT}")
    print(f"E8c: mean={m:.4f} sem={s:.4f} z={z:.1f}σ vs 1.1111")
