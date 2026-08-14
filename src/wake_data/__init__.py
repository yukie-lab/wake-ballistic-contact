"""wake_data — Project WAKE データ層 (憲法第8条)

設計原則:
- カタログ差替可能 (第8条1項): CatalogProvider を差し替えても上位層は不変
- 選択関数も同格の差替部品 (第8条2項): SelectionFunction は Provider と同じ階級
- 上位層 (到来統計・排除地図) はこのパッケージの公開インターフェースのみに依存する
"""

from .schema import (STAR_CATALOG_SCHEMA_V0, STAR_CATALOG_SCHEMA_V1,
                     validate_catalog)
from .catalog import CatalogProvider, DummyCatalogProvider, StarCatalog
from .selection import (DEFAULT_S_FLOOR, SelectionFunction, UnitySelection,
                        MagnitudeThresholdSelection, PatchySkySelection,
                        ProductSelection)

__all__ = [
    "STAR_CATALOG_SCHEMA_V0", "STAR_CATALOG_SCHEMA_V1", "validate_catalog",
    "CatalogProvider", "DummyCatalogProvider", "StarCatalog",
    "DEFAULT_S_FLOOR", "SelectionFunction", "UnitySelection",
    "MagnitudeThresholdSelection", "PatchySkySelection", "ProductSelection",
]
