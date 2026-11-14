from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext

# 다시 색인할 대상의 종류 — 방문(케어 노트·내부 메모·예약 메모), 반려동물(특이사항·지병), 고객(보호자 메모).
SEARCH_SCOPES = ("visit", "pet", "customer")


@dataclass(frozen=True)
class SearchSourceChanged:
    """검색되는 글에 닿는 쓰기가 있었다 — visit·customer 가 그 쓰기와 같은 트랜잭션에서 낸다(⑨ 설계 3.4).

    글을 싣지 않는다(무엇이 바뀌었는지만 알린다). 구독자(search)는 다시 색인할 줄 하나를 넣을 뿐이고,
    글은 요청 밖의 색인기가 허브 포트 `SearchSourcePort` 로 읽는다.
    """

    ctx: ShopContext      # 발행한 요청의 매장 컨텍스트
    scope: str            # SEARCH_SCOPES 가운데 하나
    ref_id: int           # 그 대상의 ID (방문·반려동물·고객)
