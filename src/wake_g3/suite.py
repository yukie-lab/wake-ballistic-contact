"""G3 スイートランナー (骨組み)

現状はアンカー台帳の状態報告のみ。各アンカーの実行体 (runner) は
Phase 1 で配線する: G3-1/2 は固定入力 → wake_engine 積分 → 帯判定、
G3-3 は BJ+18 再現パイプライン、G3-4 は Phase 2 の率時系列に接続。

運用規約 (憲法第6条・裁定記録):
- strict_band が None のアンカーは「PENDING_RULING」であり合否を出さない
- 帯確定後に不合格が出た場合は即停止。帯の事後拡大による救済は禁止
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from wake_g3.anchors import G3_ANCHORS


def run() -> int:
    print("=" * 72)
    print("G3 不変量指紋スイート — 状態報告")
    print("=" * 72)
    any_fail = False
    for a in G3_ANCHORS:
        if a.strict_band is None:
            status = "PENDING_RULING (合格帯未固定 — Phase 1 冒頭裁定待ち)"
        elif a.fixed_inputs is None and "固定入力" in a.test_design:
            status = "NOT_WIRED (公刊入力の転記待ち)"
        else:
            status = "READY (実行体の配線待ち)"
        print(f"\n[{a.id}] {a.name}")
        print(f"  設計   : {a.test_design}")
        print(f"  状態   : {status}")
        if a.notes:
            print(f"  注記   : {a.notes}")
    print("\n" + "=" * 72)
    print("総合: 全アンカー登録済み。合否判定は帯固定後 (裁定ログ参照)。")
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(run())
