"""wake_r — Phase R 数値反証装置の API (準備区画)

【状態】Phase R は起動宣言済み (裁定ログ#6)。ただし**スプリント本体は交付文書
(問題文確定版・声がけプロトコル等、次回設計セッションで作成) の受領まで開始しない**。
本モジュールは裁定ログ#6 が着手可とした「R 向け API 整備」の骨格である。

役割 (憲法第9条3項): Phase R が主張する臨界条件 (p, R, τ, σ, ρ) やレジーム分類を、
WAKE 本体の実カタログ機構で数値的に反証する。

提供予定の装置 (交付文書で確定):
1. real_catalog_snapshot(): DR3 候補カタログの 6D 状態 (検疫適用済み) を返す
2. contact_process_run(pos, vel, p, R_pc, tau_myr, t_max_myr, seed):
   実運動学下の接触過程 (星 i → 航続 R 内の星 j へ確率 p・遅延 τ で伝播) を
   前進シミュレートし、占有率 X(t)・前線位置・持続性指標を返す
3. front_persistence_metric(...): 主張された閾値の判定量

実装は骨格のみ。パラメータ化・境界条件・観測量は交付文書に従属するため、
ここで先に固めない (期待値管理 — 憲法第9条6項)。
"""


def real_catalog_snapshot():
    """DR3 候補カタログ (data/raw/dr3_candidates_lma25.parquet) の 6D 状態。
    交付文書受領後に検疫・座標変換込みで実装する。"""
    raise NotImplementedError("Phase R 交付文書の受領後に実装 (裁定ログ#6)")


def contact_process_run(pos, vel, p, R_pc, tau_myr, t_max_myr, seed=0):
    """実運動学下の接触過程シミュレータ。交付文書受領後に実装。"""
    raise NotImplementedError("Phase R 交付文書の受領後に実装 (裁定ログ#6)")
