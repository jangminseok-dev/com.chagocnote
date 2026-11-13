from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal

from hub.app.dtos.care_facts import CareFacts
from hub.app.dtos.customer_contact import CustomerContact
from hub.app.dtos.draft_candidate import DraftCandidate
from hub.app.dtos.family_brief import FamilyBriefs
from hub.app.dtos.shop_context import ShopContext


class CustomerDirectoryPort(ABC):
    """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순, 카톡 초안 후보,
    미용 기록의 몸무게), notification (보낼 때의 연락처)."""

    @abstractmethod
    async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
        """고객 행을 FOR UPDATE 로 잠그고 확인한다: 살아 있는 이 매장의 고객인가, 반려동물이 모두 그 보호자의
        아이이고 무지개다리가 아닌가. 통과하지 못하면 허브 오류를 던진다: FamilyNotFoundError(익명화됐거나
        다른 매장), FamilyPetNotFoundError(그 보호자의 아이가 아님), FamilyPetPassedAwayError(무지개다리).

        잠금은 부르는 쪽 트랜잭션이 끝날 때 풀린다. 방문을 쓰는 유스케이스는 방문 행을 잠그기 **전에** 부른다
        (잠금 순서: 고객 행 → 방문 행). 익명화·무지개다리·반려동물 삭제와 겹치지 않게 하려는 것이다.
        """

    @abstractmethod
    async def briefs(
        self, ctx: ShopContext, customer_ids: list[int], pet_ids: list[int]
    ) -> FamilyBriefs:
        """보여 줄 요약. 익명화한 고객과 그 반려동물도 틀은 돌려준다(이름은 None)."""

    @abstractmethod
    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
        """고객 목록 '최근 방문순'의 키를 바꾼다. 원본(visits)에서 다시 계산한 값을 같은 트랜잭션에서 넘긴다."""

    @abstractmethod
    async def set_pet_weight(self, ctx: ShopContext, pet_id: int, weight_kg: Decimal) -> None:
        """반려동물의 현재 몸무게를 바꾼다 — 그 아이의 가장 최근 미용 기록에 적은 몸무게다(설계 8절).

        visit 이 lock_family 로 고객 행을 잠근 **뒤에** 같은 트랜잭션에서 부른다. 살아 있는 이 매장의 아이가
        아니면 아무것도 바꾸지 않는다(잠근 가족이라 일어나지 않는다).
        """

    @abstractmethod
    async def find_draft_candidates(self, ctx: ShopContext, words: tuple[str, ...]) -> list[DraftCandidate]:
        """카톡 예약 초안의 "누구" 후보. 낱말 하나라도 걸리는 이 매장의 가족을 최대 5 가족 돌려준다.

        순서는 반려동물 이름 정확 일치 → 보호자 이름 정확 일치 → 전화(8자리 이상 포함 / 4자리 뒷자리) → 부분 일치,
        같은 순위면 고객 ID 오름차순. 익명화한 고객은 후보가 아니고, 무지개다리를 건넌 아이는 pets 에서 뺀다.
        낱말은 저장하지도 로그에 남기지도 않는다(설계 10절 V9).
        """

    @abstractmethod
    async def care_facts(
        self, ctx: ShopContext, customer_ids: tuple[int, ...], pet_ids: tuple[int, ...], today: date
    ) -> CareFacts:
        """예약 앞에서 확인할 것의 재료(③-B) — 고객의 살아 있는 주의 표시([today] 기준), 아이의 나이·지병·
        미용 동의·무지개다리. 잠그지 않는다. 고객이 몇이든 읽는 횟수가 같다.

        [pet_ids] 의 아이는 그 보호자가 [customer_ids] 에 있어야 나온다. 익명화한 고객과 그 아이, 다른 매장의
        것은 빠진다(briefs 와 달리 틀도 주지 않는다). 주의 사유와 지병 메모는 로그에 남기지 않는다.
        """

    @abstractmethod
    async def contact(self, ctx: ShopContext, customer_id: int) -> CustomerContact | None:
        """이 매장의 살아 있는 고객이면 연락처. 익명화했거나 다른 매장이면 None. 잠그지 않는다.
        가린 번호가 아니라 실제 번호다 — notification 만 부른다. 로그에 남기지 않는다."""
