"""マーク場インターフェース(憲法第4条 — カタログ層はここだけを見る)

カタログ層が参照してよいのは MarkField.p_settled(x, v, t) のみ(仕様 3.3)。
実装詳細((a)(b)(c) の内部)への依存はインターフェース不可知性テストで検査される。
"""
from .fields import MarkField, make_field

__all__ = ["MarkField", "make_field"]
