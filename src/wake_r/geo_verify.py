"""C2 証明の幾何+正規化橋 検証器 v5 — 証明級(区間演算・橋の認証統合)

来歴:
  v1  モンテカルロ min(審査役7: 最悪ケース証明の形式を満たさない → 破棄)
  v2  摂動角点列挙+Lipschitz(審査役9: ‖w‖ の非凸性で角点列挙は反保守 → 破棄)
  v4  区間演算(成分区間の直積包含+厳密ノルム min/max 閉形式)+ T_a=T_s/16。
      幾何余裕 +0.0029w̄ @K₀=5 を認証(インライン実行、本ファイル未反映だった)
  v5  本版。サイクル10 の残項目1(控除/受理の正規化橋)を同一測度で認証する
      橋計算を統合。受理パッチは消去(erosion)補題 θ* = slack/|w_c| で評価し、
      控除はサイト数精密化(√3/8·j + 1 + diam𝒦/8a)+正直な Minkowski 体積
      (平行四辺形⊕球の Steiner 公式・厳密)+方向広がり(sector)込みで評価。
      T_a = T_s/32 に再短縮。K₀ を走査し、橋が閉じる最小 K₀ と許容 Λ̃ を出力。

幾何設計(v8 と同一): y,z 大域アンカー / x 親相対化 / 丸め Λ=(a/8)ℤ³(誤差 a/16)/
コア着地(半幅 a/2)/ 副殻 200 分割(帯半幅 w̄/400)/ T_g = 64(τ+T_s) /
錐 D_±(w_x/|w| ≥ 0.8, w_y/w_x ∈ ±[1/8,1/2])/ 親速度カバー ±0.05w̄ 箱。

橋(サイクル10 残項目1): 同一測度 = 正規化殻測度 ν̂。
  受理: ν̂(パッチ×I*帯) ≥ (1/200)·(1−cosθ*)/2,  θ* = slack/(1.05w̄)
  控除: ν̂(∪bad) ≤ Λ̃·[vol(𝒦)·Σ_j n_j/j³ / T_g³] / vol(殻),  vol(殻)=(28π/3)w₁³
  認証: 控除 ≤ (1/2)·受理  ⇔  Λ̃ ≤ Λ̃_max(K₀, τ)

実行: python3 src/wake_r/geo_verify.py
"""
import math

ZETA2 = 1.6449340668482264
ZETA3 = 1.2020569031595943
EPS = 1e-12  # 浮動小数の防護(余裕から常に差し引く)


# ---------- 区間演算(成分ごと [lo, hi]) ----------

def iv(lo, hi):
    return (min(lo, hi), max(lo, hi))

def iadd(a, b):
    return (a[0] + b[0], a[1] + b[1])

def isub(a, b):
    return (a[0] - b[1], a[1] - b[0])

def iscale(a, c):
    return iv(a[0] * c, a[1] * c)

def norm2_bounds(box):
    """box = [(lo,hi)]*3 の ‖·‖₂ の厳密 min/max(閉形式)"""
    d2min = 0.0
    d2max = 0.0
    for lo, hi in box:
        d2max += max(lo * lo, hi * hi)
        if lo <= 0.0 <= hi:
            pass  # min 距離 0
        else:
            d2min += min(abs(lo), abs(hi)) ** 2
    return math.sqrt(d2min), math.sqrt(d2max)


# ---------- 幾何(着地余裕 slack)の区間検証 ----------

def geometry(K, tau, ta_frac, ns=4096):
    """最悪 slack(w̄ 単位)と候補速度包 W(w̄ 単位、全摂動・全 s の合併)を返す。

    w̄ = K(最悪 = 最遅副殻、進入オフセット R/w̄ が相対的に最大)。
    """
    Ts = 1.0
    w = float(K)               # w̄(絶対単位: R/Ts)
    Tg = 64.0 * (tau + Ts)
    Ta = Ts * ta_frac
    ux = w / math.sqrt(17.0 / 16.0)
    a = ux * Tg / 32.0
    core = a / 2.0
    Ih = w / 400.0
    pv = 0.05 * w              # 親速度カバー半幅
    eps_pos = core + a / 16.0  # 親位置 y,z 広がり(コア+丸め誤差)
    rnd = a / 16.0             # 標的丸め誤差(Λ=(a/8)ℤ³)

    # |v_p| の摂動込み sup(Lipschitz 用)
    vp_sup = math.sqrt((ux + pv) ** 2 + (ux / 4.0 + pv) ** 2 + pv ** 2)

    worst = float("inf")
    hull = [[float("inf"), float("-inf")] for _ in range(3)]
    cone_ok = True
    cover_ok = True

    for bp in (+1.0, -1.0):        # 親の到着枝
        for bc in (+1.0, -1.0):    # 子の出発枝
            for i in range(ns):
                s0 = Ta * i / ns
                s1 = Ta * (i + 1) / ns
                T0 = Tg - s0       # 残時間(セル内最小は Tg−s1 だが分母には s0 側、
                                   # h0 は増加関数なので h0(s0) 採用が保守的)
                # y0 = pos_p + vp·s0 + e(成分区間)
                y0 = []
                vpc = (ux, bp * ux / 4.0, 0.0)
                pos = ((0.0, 0.0), (-eps_pos, eps_pos), (-eps_pos, eps_pos))
                for c in range(3):
                    vp_iv = iv(vpc[c] - pv, vpc[c] + pv)
                    y0c = iadd(iadd(pos[c], iscale(vp_iv, s0)), (-1.0, 1.0))
                    y0.append(y0c)
                # tgt(丸め誤差込み)
                tgt = (iv(ux * Tg - rnd, ux * Tg + rnd),
                       iv(bc * 8.0 * a - rnd, bc * 8.0 * a + rnd),
                       iv(-rnd, rnd))
                # w_req = (tgt − y0)/(Tg − s0)
                wr = [iscale(isub(tgt[c], y0[c]), 1.0 / T0) for c in range(3)]
                nmin, nmax = norm2_bounds(wr)
                dev = max(nmax - w, w - nmin, 0.0)
                h0 = core / T0
                lip = ((vp_sup + nmax) / (Tg - Ta) + h0 / (Tg - Ta)) * (s1 - s0)
                worst = min(worst, h0 - dev - Ih - lip - EPS)
                # 包(窓箱 = w_req ⊕ [−h0,h0]³、Lipschitz 幅込み)— 橋・錐・カバー用
                for c in range(3):
                    lo = wr[c][0] - h0 - lip
                    hi = wr[c][1] + h0 + lip
                    hull[c][0] = min(hull[c][0], lo)
                    hull[c][1] = max(hull[c][1], hi)

    # 錐 D_± 包含(+枝の包で検査; 対称性で −枝も同じ)
    # 包は ±枝合併なので +枝のみ再計算して検査する
    hull_pos = _hull_one_branch(K, tau, ta_frac, ns=min(ns, 512))
    (xl, xh), (yl, yh), (zl, zh) = hull_pos
    nmax_h = math.sqrt(max(xl * xl, xh * xh) + max(yl * yl, yh * yh)
                       + max(zl * zl, zh * zh))
    cone_ok = (xl > 0) and (xl / nmax_h >= 0.8) and (yl > 0) \
        and (yl / xh >= 1.0 / 8.0) and (yh / xl <= 1.0 / 2.0)
    # 親速度カバー ±0.05w̄ の包含(次世代の親 = 受理候補)
    cover_ok = (abs(xl - ux) <= pv and abs(xh - ux) <= pv
                and abs(yl - ux / 4.0) <= pv and abs(yh - ux / 4.0) <= pv
                and abs(zl) <= pv and abs(zh) <= pv)

    return worst / w, hull_pos, cone_ok, cover_ok, dict(
        w=w, Tg=Tg, Ta=Ta, ux=ux, a=a, core=core, Ih=Ih, pv=pv)


def _hull_one_branch(K, tau, ta_frac, ns=512):
    """+枝(bc=+1、bp 両方)の候補速度包(絶対単位)"""
    Ts = 1.0
    w = float(K)
    Tg = 64.0 * (tau + Ts)
    Ta = Ts * ta_frac
    ux = w / math.sqrt(17.0 / 16.0)
    a = ux * Tg / 32.0
    core = a / 2.0
    pv = 0.05 * w
    eps_pos = core + a / 16.0
    rnd = a / 16.0
    vp_sup = math.sqrt((ux + pv) ** 2 + (ux / 4.0 + pv) ** 2 + pv ** 2)
    hull = [[float("inf"), float("-inf")] for _ in range(3)]
    for bp in (+1.0, -1.0):
        for i in range(ns):
            s0 = Ta * i / ns
            s1 = Ta * (i + 1) / ns
            T0 = Tg - s0
            vpc = (ux, bp * ux / 4.0, 0.0)
            pos = ((0.0, 0.0), (-eps_pos, eps_pos), (-eps_pos, eps_pos))
            wr = []
            for c in range(3):
                vp_iv = iv(vpc[c] - pv, vpc[c] + pv)
                y0c = iadd(iadd(pos[c], iscale(vp_iv, s0)), (-1.0, 1.0))
                tg = (iv(ux * Tg - rnd, ux * Tg + rnd),
                      iv(8.0 * a - rnd, 8.0 * a + rnd),
                      iv(-rnd, rnd))[c]
                wr.append(iscale(isub(tg, y0c), 1.0 / T0))
            nmax = norm2_bounds(wr)[1]
            h0 = core / T0
            lip = ((vp_sup + nmax) / (Tg - Ta) + h0 / (Tg - Ta)) * (s1 - s0)
            for c in range(3):
                hull[c][0] = min(hull[c][0], wr[c][0] - h0 - lip)
                hull[c][1] = max(hull[c][1], wr[c][1] + h0 + lip)
    return [tuple(h) for h in hull]


# ---------- 橋(控除 ν̂-質量 ≤ ½·受理 ν̂-質量)の認証 ----------

def parallelepiped_ball_volume(r, L1, L2, sin_t=1.0):
    """(球 B(r)) ⊕ seg(L1) ⊕ seg(L2) の Steiner 体積(凸・厳密):
    2·A·r + πr²(L1+L2) + (4π/3)r³,  A = L1·L2·sinθ ≤ L1·L2"""
    return 2.0 * L1 * L2 * sin_t * r + math.pi * r * r * (L1 + L2) \
        + (4.0 * math.pi / 3.0) * r ** 3


def bridge(K, tau, ta_frac, slack_w, geo):
    """橋の認証。w̄ = 2K(控除分子の最悪)で絶対量を評価し、
    殻体積 (28π/3)K³ で正規化。受理パッチは slack(w̄ 単位・K で最悪)を使用。
    戻り値: (bad_frac, acc_frac, lambda_max)"""
    Ts = 1.0
    Tg = 64.0 * (tau + Ts)
    Ta = Ts * ta_frac
    w_hi = 2.0 * float(K)          # 分子側最悪の w̄
    ux = w_hi / math.sqrt(17.0 / 16.0)
    a = ux * Tg / 32.0
    pv = 0.05 * w_hi
    # 候補速度包(w̄=K の包を w̄ 比でスケール — 幾何は w̄ 単位で相似、
    # 進入オフセット項 R/T_g のみ非相似だが w̄ 大で縮むため K の包が保守的)
    scale = w_hi / geo["w"]
    hull = [(lo * scale, hi * scale) for lo, hi in
            _hull_one_branch(K, tau, ta_frac, ns=512)]

    # 相対速度区間: v ∈ hull(枝 ±)、v_P ∈ 親箱(枝 ±)
    def rel_bounds(v_branch, p_branch):
        vpc = (ux, p_branch * ux / 4.0, 0.0)
        diffs = []
        for c in range(3):
            vl, vh = hull[c]
            if v_branch < 0 and c == 1:
                vl, vh = -vh, -vl
            pl, ph = vpc[c] - pv, vpc[c] + pv
            diffs.append((vl - ph, vh - pl))
        return norm2_bounds(diffs)

    vol_K = 0.0
    diam_K = 0.0
    for vb in (+1.0, -1.0):
        for pb1 in (+1.0, -1.0):       # 新親の枝
            for pb2 in (+1.0, -1.0):   # 旧親の枝
                r1min, r1max = rel_bounds(vb, pb1)
                r2min, r2max = rel_bounds(vb, pb2)
                L1, L2 = r1max * Ta, r2max * Ta
                # 方向広がり: sinβ ≤ 半径方向直径/最小距離(0 近傍は球膨張で処理)
                def eff(rmin, rmax, L):
                    if rmin <= 0.25 * rmax:   # 方向拘束が弱い → 球膨張
                        return None
                    beta = min(1.0, (rmax - rmin) / rmin)  # sinβ の保守上界
                    return L * beta
                e1, e2 = eff(r1min, r1max, L1), eff(r2min, r2max, L2)
                if e1 is None or e2 is None:
                    v = (4.0 * math.pi / 3.0) * (2.0 + L1 + L2) ** 3
                    d = 2.0 * (2.0 + L1 + L2)
                else:
                    r_e = 2.0 + e1 + e2
                    v = parallelepiped_ball_volume(r_e, L1, L2, 1.0)
                    d = 2.0 * r_e + L1 + L2
                vol_K = max(vol_K, v)
                diam_K = max(diam_K, d)

    # サイト数: n_j ≤ (√3/8)·j + 1 + diam𝒦/(8a)  (z 単一トラック、x は世代=k で一意)
    c1 = math.sqrt(3.0) / 8.0
    c0 = 1.0 + diam_K / (8.0 * a)
    series = c1 * ZETA2 + c0 * ZETA3
    bad_leb = vol_K * series / Tg ** 3          # (R/Ts)³ 単位
    shell_vol = (28.0 * math.pi / 3.0) * float(K) ** 3
    bad_frac = bad_leb / shell_vol              # Λ̃=1 での ν̂-質量上界(/q)

    # 受理: パッチ角半径 θ* = slack/(1.05)(w̄ 単位; |w_c| ≤ 1.05w̄ の保守除数)
    theta = slack_w / 1.05
    acc_frac = (1.0 - math.cos(theta)) / 2.0 / 200.0   # ν̂-質量下界(/q)

    lam_max = (acc_frac / 2.0) / bad_frac if bad_frac > 0 else float("inf")
    return bad_frac, acc_frac, lam_max


# ---------- 走査 ----------

def run(K, tau, ta_frac, ns=4096):
    slack, hull, cone_ok, cover_ok, geo = geometry(K, tau, ta_frac, ns=ns)
    bad, acc, lam = bridge(K, tau, ta_frac, slack, geo)
    return dict(K=K, tau=tau, ta=ta_frac, slack=slack, cone=cone_ok,
                cover=cover_ok, bad=bad, acc=acc, lam=lam)


if __name__ == "__main__":
    ta_frac = 1.0 / 32.0
    print(f"T_a = T_s/32, T_g = 64(τ+T_s), 副殻200分割, 丸め Λ=(a/8)ℤ³")
    print(f"{'K₀':>4} {'τ/Ts':>5} {'slack/w̄':>10} {'錐':>3} {'カバー':>4} "
          f"{'控除ν̂(Λ̃=1)':>12} {'受理ν̂':>10} {'Λ̃_max':>8}")
    ok_all = True
    for K in (5, 8, 10, 12, 16, 20, 24):
        for tau in (0.0, 1.0, 3.0):
            r = run(K, tau, ta_frac)
            flag = "PASS" if (r["slack"] > 0 and r["cone"] and r["cover"]
                              and r["lam"] >= 4.0) else "----"
            print(f"{K:>4} {tau:>5.1f} {r['slack']:>+10.5f} "
                  f"{'✓' if r['cone'] else '✗':>3} "
                  f"{'✓' if r['cover'] else '✗':>4} "
                  f"{r['bad']:>12.3e} {r['acc']:>10.3e} {r['lam']:>8.2f} {flag}")
    # 認証判定: K₀=20 で全 τ、slack>0・錐・カバー・Λ̃_max ≥ 4
    print()
    final = [run(20, t, ta_frac) for t in (0.0, 1.0, 3.0)]
    ok = all(r["slack"] > 0 and r["cone"] and r["cover"] and r["lam"] >= 4.0
             for r in final)
    print("K₀=20, Λ̃ ≤ 4, T_a=T_s/32:", "PASS(橋認証+幾何認証)" if ok else "FAIL")
