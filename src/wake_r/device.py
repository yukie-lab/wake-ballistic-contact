"""wake_r — Phase R 数値反証装置 (交付文書 1.1 = 裁定ログ#7 §3.1 の装置)

役割: Phase R の主張 (補題・予想・閾値候補値・反例) を実測運動学下の
接触過程シミュレーションで数値反証する。数値と矛盾する主張は即棄却 (憲法第9条3項)。

## 過程の規約 (交付文書 §1.1 の実装規約 — 変更時は本 docstring を更新し R 記録に残す)

- 点: 位置 x_i [pc]、速度 v_i [pc/Myr]。伝播は線形 (既定) — Phase R の時間スケールが
  エピサイクル周期 (~167 Myr) に達する場合は epicyclic 伝播に切替可能 (要実装拡張)
- マーク伝播: マーク済み i の距離 R 内に**入った** (前ステップ外→今ステップ内) 未マーク j に
  対し、ペア (i,j) の**初回進入時に一度だけ**確率 p の伝播試行。成功時は t_entry + τ で
  j がマークされる (i がその間に死んでも着弾する — 探査機は発射済みという解釈)
- 死亡: マーク時に寿命 Exp(T_s) を付与。死亡後の再マークは可 (再入植 — CN19 準拠)。
  T_s=inf で不死
- 初期条件: 原点最近傍の1点をマーク (または indices 指定)

## 実カタログ

real_catalog_snapshot(): DR3 の 100 pc 6D 体積サンプル (169,741 星)。
**RV 選択の偏りに注意**: 6D 完備部分集合の密度 0.041 pc⁻³ は全恒星密度 (~0.08-0.10)
の約半分で、晩期 M が欠ける。理論主張の検証には synthetic_field() で密度・分散を
制御した場に実測楕円体を与える方が清潔な場合が多い (どちらを使うかは主張の性質による)。
"""

import pathlib

import numpy as np
from scipy.spatial import cKDTree

ROOT = pathlib.Path(__file__).resolve().parents[2]
PC_PER_MYR = 1.02271

# 太陽近傍の実測速度楕円体の代表値 (混合母集団の目安。装置の既定であり、
# 主張検証時は主張が指定する (σ, ρ) を明示的に渡すこと)
DEFAULT_SIGMAS = (35.0, 25.0, 18.0)   # km/s (U, V, W)
DEFAULT_DENSITY = 0.08                # pc^-3


def synthetic_field(density=DEFAULT_DENSITY, box_pc=200.0,
                    sigmas_kms=DEFAULT_SIGMAS, vertex_kms=(0., 0., 0.),
                    seed=0):
    """一様 Poisson 場 + ガウス速度楕円体。周期境界なし (有限箱)。"""
    rng = np.random.default_rng(seed)
    n = rng.poisson(density * box_pc ** 3)
    pos = rng.uniform(-box_pc / 2, box_pc / 2, (n, 3))
    vel = (rng.standard_normal((n, 3)) * np.asarray(sigmas_kms)
           + np.asarray(vertex_kms)) * PC_PER_MYR
    return pos, vel


def real_catalog_snapshot():
    """DR3 100 pc 6D 体積サンプルの (pos [pc], vel [pc/Myr])。太陽中心銀河軸。"""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    import pandas as pd
    from wake_data.icrs import icrs_to_helio_galactic
    df = pd.read_parquet(ROOT / "data" / "raw" / "dr3_100pc_6d.parquet")
    pos, vel = icrs_to_helio_galactic(
        df["ra"].to_numpy(float), df["dec"].to_numpy(float),
        df["parallax"].to_numpy(float), df["pmra"].to_numpy(float),
        df["pmdec"].to_numpy(float), df["radial_velocity"].to_numpy(float))
    return pos, vel * PC_PER_MYR


def contact_process_run(pos, vel, p, R_pc, tau_myr, Ts_myr=np.inf,
                        t_max_myr=50.0, dt_myr=0.1, seed=0,
                        seed_indices=None):
    """接触過程を前進シミュレート。

    戻り値 dict:
      t: 時刻格子 / X: マーク占有率 (生存マーク/全点) / n_alive: 生存マーク数
      extent: 生存マーク集合の初期シードからの最大距離 [pc]
      survived: 終端で生存マークが残ったか / extinction_time: 絶滅時刻 (生存なら nan)
      n_attempts, n_transmissions: 試行・成功数 (装置の稼働記録)
    """
    rng = np.random.default_rng(seed)
    pos = np.asarray(pos, dtype=float)
    vel = np.asarray(vel, dtype=float)
    n = len(pos)
    if seed_indices is None:
        seed_indices = [int(np.argmin(np.linalg.norm(pos, axis=1)))]
    origin = pos[seed_indices[0]].copy()

    mark_time = np.full(n, np.inf)     # マーク成立時刻
    death_time = np.full(n, np.inf)
    pending_t = []                     # 着弾予定 (t_arrive, j)
    tried_pairs = set()                # 初回進入試行済みペア

    for j in seed_indices:
        mark_time[j] = 0.0
        death_time[j] = rng.exponential(Ts_myr) if np.isfinite(Ts_myr) else np.inf

    steps = int(round(t_max_myr / dt_myr))
    t_grid = np.zeros(steps + 1)
    X = np.zeros(steps + 1)
    n_alive_arr = np.zeros(steps + 1, dtype=int)
    extent = np.zeros(steps + 1)
    n_att = n_tx = 0
    # 進入検出は格子間の線形 CPA (最接近) 解析で行う — dt に依存しない。
    # 探索半径: R + 2 v_cap dt (v_cap は速度ノルムの99%点; 超過星は per-pair で補足不能の
    # ため v_cap を超える星が候補に入るよう max も併用)
    v_cap = float(np.percentile(np.linalg.norm(vel, axis=1), 99))
    v_max = float(np.max(np.linalg.norm(vel, axis=1)))

    for k in range(steps + 1):
        t = k * dt_myr
        t_grid[k] = t
        # 着弾処理
        if pending_t:
            due = [(ta, j) for (ta, j) in pending_t if ta <= t]
            pending_t = [(ta, j) for (ta, j) in pending_t if ta > t]
            for ta, j in due:
                if not (mark_time[j] <= ta and death_time[j] > ta):
                    mark_time[j] = ta
                    death_time[j] = ta + (rng.exponential(Ts_myr)
                                          if np.isfinite(Ts_myr) else np.inf)
        # 死亡処理 (再マーク可)
        expired = (mark_time <= t) & (death_time <= t)
        mark_time[expired] = np.inf
        death_time[expired] = np.inf
        alive = (mark_time <= t) & (death_time > t)
        n_alive = int(alive.sum())
        n_alive_arr[k] = n_alive
        X[k] = n_alive / n
        P = pos + vel * t
        if n_alive:
            extent[k] = float(np.max(np.linalg.norm(P[alive] - origin, axis=1)))
        if n_alive == 0 and not pending_t:
            t_grid, X, n_alive_arr, extent = (a[:k + 1] for a in
                                              (t_grid, X, n_alive_arr, extent))
            return dict(t=t_grid, X=X, n_alive=n_alive_arr, extent=extent,
                        survived=False, extinction_time=t,
                        n_attempts=n_att, n_transmissions=n_tx)
        if k == steps or n_alive == 0:
            continue
        # 区間 (t, t+dt] の進入検出: 線形 CPA
        r_search = R_pc + (v_cap + v_max) * dt_myr
        tree = cKDTree(P)
        src_idx = np.flatnonzero(alive)
        neigh = tree.query_ball_point(P[src_idx], r=r_search)
        for si, js in zip(src_idx, neigh):
            for j in js:
                if j == si or (si, j) in tried_pairs:
                    continue
                if mark_time[j] <= t and death_time[j] > t:
                    continue  # マーク済み
                dp = P[j] - P[si]
                d0 = float(np.linalg.norm(dp))
                if d0 <= R_pc:
                    # 既に R 内 (進入は過去に処理済みのはずだが、シード直後の
                    # 初期近傍はここで初回試行になる)
                    t_entry = t
                else:
                    dv = vel[j] - vel[si]
                    vv = float(dv @ dv)
                    if vv <= 0:
                        continue
                    t_star = -float(dp @ dv) / vv
                    if not (0 < t_star <= dt_myr):
                        continue
                    d_min = float(np.linalg.norm(dp + dv * t_star))
                    if d_min > R_pc:
                        continue
                    t_entry = t + t_star
                tried_pairs.add((si, j))
                n_att += 1
                if rng.random() < p:
                    n_tx += 1
                    pending_t.append((t_entry + tau_myr, j))
    return dict(t=t_grid, X=X, n_alive=n_alive_arr, extent=extent,
                survived=True, extinction_time=np.nan,
                n_attempts=n_att, n_transmissions=n_tx)
