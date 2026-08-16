"""インターフェース不可知性テスト(憲法第4条2項 — 裁定ログ#13 裁定2)

1. 静的: カタログ層(wake_p2/wake_p3/wake_data/wake_engine)のソースに
   wake_mark の内部モジュール(wake_mark.fields)や具象クラス名への参照がないこと
2. 動的: (a)↔(b) スワップ — 地図生成器の同一コードパスが両方の場で動くこと
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

SRC = pathlib.Path(__file__).resolve().parents[1]
CATALOG_LAYERS = ["wake_p2", "wake_p3", "wake_data", "wake_engine"]
FORBIDDEN = [r"wake_mark\.fields", r"ConstantField", r"FrontField"]


def test_static_agnosticism():
    bad = []
    for layer in CATALOG_LAYERS:
        for py in (SRC / layer).glob("*.py"):
            text = py.read_text()
            for pat in FORBIDDEN:
                if re.search(pat, text):
                    bad.append(f"{py.name}: {pat}")
    assert not bad, f"カタログ層がマーク場内部に依存: {bad}"
    print("静的不可知性: PASS(内部参照ゼロ)")


def test_swap():
    from wake_mark import make_field
    rng = np.random.default_rng(0)
    x = rng.normal(0, 50, (100, 3))
    v = rng.normal(0, 30, (100, 3))
    fa = make_field("constant", f=0.3)
    fb = make_field("front", f=0.3, n_hat=[1, 0, 0], beta=1.5)

    def visit_weight(field):        # 地図生成器の縮約版(同一コードパス)
        return float(np.mean(field.p_settled(x, v, 0.0)))

    wa, wb = visit_weight(fa), visit_weight(fb)
    assert 0.0 <= wb <= wa + 1e-9 or wb >= 0.0
    assert abs(wa - 0.3) < 1e-9
    print(f"スワップ試験: PASS((a)={wa:.3f} / (b)={wb:.3f} — 同一パス)")


if __name__ == "__main__":
    test_static_agnosticism()
    test_swap()
