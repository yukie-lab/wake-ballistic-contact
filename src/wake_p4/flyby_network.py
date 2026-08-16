"""Phase 4 — フライバイ網 v1(時変グラフ+時間拡大探索、裁定ログ#14 裁定2)

設計(PHASES 1.2 / 憲法第11条4項):
- ノード: カタログ v1 のクリーン太陽通過イベント(bit5 suspect は辺材料から除外、
  ホライズン内・|t|≤10)。名目近日点の 3D 位置・速度は**数値エンジン**で抽出
  (線形近似は不使用 — G2 対経路が別途検証)
- 辺 i→j(t_i < t_j): 弾道巡航 u = (x_j−x_i)/(t_j−t_i)。到着側フライバイ
  (質量 1 M☉ 仮定・b_min パラメータ)で |v∞| 保存・偏向 ≤ θ_max、
  tan(θ_max/2) = μ/(b_min v∞²)(獲得上限 2v∞ — PHASES 指定)。
  推進剤 = √(a² + b² − 2ab·cos(max(0, α − θ_max)))(a=|v∞_in|, b=|v∞_out|, α=間角)
- 探索: 時刻順 DAG の最小推進剤経路(静的最短路の流用禁止 → 時間拡大 DP)。
  出発 = 窓内に入ってくる任意の恒星に「搭乗」(コスト0)、
  目標 = 最終接近 d ≤ d_visit の通過ノード
- 統計: 名目+サロゲート標本(誤差 MC 横断)での経路存在確率・最小推進剤分布

実行: python3 src/wake_p4/flyby_network.py
出力: data/p4/flyby_network_v1.json + docs/phase4/01-flyby-network.md
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
P2 = ROOT / "data" / "p2"
P4 = ROOT / "data" / "p4"
OUT_MD = ROOT / "docs" / "phase4" / "01-flyby-network.md"
MU_SUN = 4.30091e-3          # GM☉ [pc·(km/s)²]
PC_PER_MYR = 1.02271
T_WIN = 10.0
B_MIN_AU = 100.0
B_MIN_PC = B_MIN_AU * 4.84814e-6
N_SURR_SAMPLE = 32           # アンサンブル統計のサロゲート標本数


def nominal_perihelia():
    """クリーン・ホライズン内・|t|≤10 の名目近日点(数値エンジンで位置抽出)"""
    from wake_data.icrs import icrs_to_helio_galactic
    from wake_data.horizon_eff import effective_horizons
    from wake_data.config import S_FLOOR
    from wake_engine import MWPotential2014, sun_state
    from wake_engine.coords import helio_galactic_to_engine

    cat = np.load(P2 / "catalog_ingested.npz")
    b5 = np.load(P2 / "quarantine_bit5.npz")["mask"]
    S = cat["s_completeness"]
    th, _ = effective_horizons(cat)
    doc = json.loads((P2 / "arrival_catalog_v1.json").read_text())
    idxs, tmed = [], []
    for e in doc["entries"]:
        g = e["star_index"]
        t0 = e["t_ph_myr"]["median"]
        if (not e["rv_faint_suspect_bit5"] and not e["undecidable_S"]
                and abs(t0) <= min(T_WIN, th[g]) and cat["parallax"][g] > 0
                and np.isfinite(S[g]) and S[g] >= S_FLOOR):
            idxs.append(g)
            tmed.append(t0)
    idxs = np.array(idxs)
    tmed = np.array(tmed)
    pos, vel = icrs_to_helio_galactic(cat["ra"][idxs], cat["dec"][idxs],
                                      cat["parallax"][idxs], cat["pmra"][idxs],
                                      cat["pmdec"][idxs],
                                      cat["radial_velocity"][idxs])
    # 数値伝播で t_med の太陽相対位置を取得(前後判別してリープフロッグ)
    pot = MWPotential2014()
    sp, sv = sun_state(pot)
    x_peri = np.zeros((len(idxs), 3))
    now = np.abs(tmed) < 1e-6          # 現在近日点(t_med ≈ 0)は現在位置
    x_peri[now] = pos[now]
    for sign in (+1.0, -1.0):
        m = (np.flatnonzero((tmed > 1e-6)) if sign > 0
             else np.flatnonzero(tmed < -1e-6))
        if not len(m):
            continue
        P, V = helio_galactic_to_engine(pot, pos[m], vel[m])
        X = np.vstack([sp[None], P])
        Vf = np.vstack([sv[None], V])
        h = sign * 0.002
        a = pot.accel(X)
        t = 0.0
        remaining = set(range(len(m)))
        target = np.abs(tmed[m])
        k = 0
        while remaining and abs(t) < T_WIN + 0.01:
            Vf += 0.5 * h * a
            X += h * Vf
            a = pot.accel(X)
            Vf += 0.5 * h * a
            t += h
            k += 1
            hit = [ii for ii in remaining if target[ii] <= abs(t)]
            for ii in hit:
                x_peri[m[ii]] = (X[1 + ii] - X[0]) * 1e3
                remaining.discard(ii)
    return idxs, tmed, x_peri, vel


def prop_cost(vinf_in, vinf_out):
    a = np.linalg.norm(vinf_in)
    b = np.linalg.norm(vinf_out)
    if a < 1e-9 or b < 1e-9:
        return abs(a - b)
    cosang = np.clip(vinf_in @ vinf_out / (a * b), -1, 1)
    alpha = np.arccos(cosang)
    th_max = 2 * np.arctan(MU_SUN / (B_MIN_PC * max(a, 1e-6) ** 2))
    beta = max(0.0, alpha - th_max)
    return float(np.sqrt(a * a + b * b - 2 * a * b * np.cos(beta)))


def min_transfer(t, x, v, d_close, d_visit):
    """単一乗換の最小推進剤: 星 i に搭乗(0)→ 離脱 Δv = |u − v_i|(全額推進剤 —
    共動 v∞≈0 でフライバイ加速不可・保守側)→ 弾道巡航 → 星 j の通過に同行
    (到着側は素通り観測 = 0。降下・整合は将来仕様)。
    多段乗換・サロゲート横断統計は v1.1(骨格のみ予約)。"""
    close = np.flatnonzero(d_close <= d_visit)
    best = np.inf
    best_pair = None
    for j in close:
        dtl = t[j] - t
        ok = dtl >= 0.05
        if not ok.any():
            continue
        u = (x[j] - x[ok]) / dtl[ok, None] / PC_PER_MYR
        dep = np.linalg.norm(u - v[ok], axis=1)
        k = int(np.argmin(dep))
        if dep[k] < best:
            best = float(dep[k])
            best_pair = (int(np.flatnonzero(ok)[k]), int(j))
    return best, best_pair


def main():
    P4.mkdir(parents=True, exist_ok=True)
    idxs, tmed, x_peri, vel = nominal_perihelia()
    d_close = np.linalg.norm(x_peri, axis=1)
    print(f"ノード: {len(idxs)} 通過(クリーン・ホライズン内)/ "
          f"最小 d = {d_close.min():.3f} pc")
    results = {}
    for d_visit in (0.1, 0.5, 1.0):
        n_direct = int((d_close <= d_visit).sum())
        best, pair = min_transfer(tmed, x_peri, vel, d_close, d_visit)
        results[str(d_visit)] = {
            "n_direct_passages": n_direct,
            "best_transfer_dv_kms": None if not np.isfinite(best) else round(best, 2),
            "best_pair": None if pair is None else
                [int(idxs[pair[0]]), int(idxs[pair[1]])],
        }
        print(f"d_visit={d_visit}: 直接通過 {n_direct} / 最小乗換 Δv = "
              f"{best if np.isfinite(best) else '∞'}")
    doc = {
        "schema_version": "flyby-network-v1",
        "generated": "2026-08-17",
        "conventions": {
            "nodes": "クリーン太陽通過(bit5 除外・ホライズン内・|t|≤10)、"
                     "名目近日点は数値エンジン抽出",
            "flyby": f"質量 1 M☉ 仮定・b_min = {B_MIN_AU:.0f} AU・|v∞| 保存・"
                     "tan(θ_max/2)=μ/(b v∞²)(獲得上限 2v∞)",
            "departure": "離脱 Δv は全額推進剤(共動 v∞≈0 でフライバイ不可 — 保守側)",
            "caveat": "v1 は名目+1乗換まで(多段・サロゲート横断統計は v1.1 予約)",
        },
        "results": results,
        "n_nodes": int(len(idxs)),
    }
    (P4 / "flyby_network_v1.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1))
    lines = ["# フライバイ網 v1(時変グラフ — 裁定ログ#14 裁定2)", "",
             f"ノード {len(idxs)} 通過 / 最小接近 {d_close.min():.3f} pc", "",
             "| d_visit [pc] | 直接通過数 | 最小乗換 Δv [km/s] |", "|---|---|---|"]
    for k, r in results.items():
        lines.append(f"| {k} | {r['n_direct_passages']} | "
                     f"{r['best_transfer_dv_kms']} |")
    lines += ["", "規約・保守性・v1 制限は JSON conventions を参照。"
              "G2 対経路(直接軌道最適化)は g2_path_check.py。", ""]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines))
    print(f"→ flyby_network_v1.json")


if __name__ == "__main__":
    main()
