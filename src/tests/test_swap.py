"""差替テスト (Phase 0 出口条件: ダミーカタログでの差し替えが通ること)

検証内容:
1. 上位層のコード (toy_rate_pipeline) を一切変えずにカタログを v1 → v2 に差替可能
2. 選択関数も同格に差替可能で、補正が配管を通って効く
3. スキーマ違反カタログは Provider 境界で検出される

toy_rate_pipeline は配管検証用のダミー統計であり、本番の到来統計ではない。
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from wake_data import (
    CatalogProvider, DummyCatalogProvider, SelectionFunction,
    UnitySelection, MagnitudeThresholdSelection, StarCatalog,
)


def toy_rate_pipeline(provider: CatalogProvider, sf: SelectionFunction) -> dict:
    """上位層の代役: 6D 完備星の生カウントと完備性補正カウントを返す。
    抽象インターフェースのみに依存し、実装型を一切参照しないこと。"""
    cat = provider.load()
    d = cat.data
    ok = ~np.isnan(d["radial_velocity"])
    w = sf.weights(d["phot_g_mean_mag"][ok], d["bp_rp"][ok],
                   d["ra"][ok], d["dec"][ok])
    return {
        "release": cat.release,
        "n_total": len(cat),
        "n_6d": int(ok.sum()),
        "raw_count": float(ok.sum()),
        "corrected_count": float(np.nansum(w)),
        "n_uncorrectable": int(np.isnan(w).sum()),
    }


def main():
    failures = []

    # 1. カタログ差替: 同一パイプラインで v1 / v2
    r1 = toy_rate_pipeline(DummyCatalogProvider(2000, "v1", seed=7), UnitySelection())
    r2 = toy_rate_pipeline(DummyCatalogProvider(2000, "v2", seed=7), UnitySelection())
    if r1["release"] == r2["release"]:
        failures.append("差替が反映されていない")
    if not (r2["n_6d"] > r1["n_6d"]):
        failures.append("v2 (DR4想定) で 6D 星が増えていない")
    print(f"[1] カタログ差替 OK: {r1['release']} (6D {r1['n_6d']}/{r1['n_total']}) → "
          f"{r2['release']} (6D {r2['n_6d']}/{r2['n_total']})")

    # 2. 選択関数差替: 補正カウント > 生カウント になること
    r3 = toy_rate_pipeline(DummyCatalogProvider(2000, "v1", seed=7),
                           MagnitudeThresholdSelection(g50=13.0))
    if not (r3["corrected_count"] > r3["raw_count"]):
        failures.append("完備性補正が効いていない")
    print(f"[2] 選択関数差替 OK: raw={r3['raw_count']:.0f} → "
          f"corrected={r3['corrected_count']:.0f} (補正不能 {r3['n_uncorrectable']} 星)")

    # 3. スキーマ違反の検出
    bad = DummyCatalogProvider(100, "v1", seed=1).load().data.copy()
    del bad["parallax"]
    try:
        StarCatalog(data=bad, release="broken", ref_epoch=2016.0)
        failures.append("スキーマ違反が検出されなかった")
    except ValueError as e:
        print(f"[3] スキーマ違反検出 OK: {e}")

    # 4. RV 欠損と出所フラグの整合違反の検出
    bad2 = DummyCatalogProvider(100, "v1", seed=1).load().data.copy()
    prov = bad2["rv_provenance"].copy()
    prov[np.isnan(bad2["radial_velocity"])] = 0  # 欠損なのに gaia_rvs を主張
    bad2["rv_provenance"] = prov
    try:
        StarCatalog(data=bad2, release="broken2", ref_epoch=2016.0)
        failures.append("RV出所フラグの不整合が検出されなかった")
    except ValueError as e:
        print(f"[4] 出所フラグ整合検査 OK: {e}")

    if failures:
        print("\nFAIL:", *failures, sep="\n  - ")
        return 1
    print("\n差替テスト: 全項目 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
