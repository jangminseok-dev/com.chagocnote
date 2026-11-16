from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import CustomerNotFoundError
from customer.domain.services.care_marks import caution_active
from customer.domain.services.draft_ranking import match_family
from customer.domain.services.phone_number import mask_phone
from customer.domain.services.search_terms import parse_query
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.domain.value_objects.form_settings import DEFAULT_FORM_SETTINGS
from hub.app.dtos.care_facts import CareFacts, CautionFact, ConditionFact, ConsentCover, PetCareFact
from hub.app.dtos.customer_contact import CustomerContact
from hub.app.dtos.draft_candidate import DraftCandidate
from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
from hub.app.dtos.shop_context import ShopContext
from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
from hub.app.ports.customer_directory_port import CustomerDirectoryPort

DRAFT_CANDIDATE_LIMIT = 5
_MATCH_LIMIT = 20   # 순위를 매기기 전에 읽는 가족 수 — 낱말 하나에 수십 가족이 걸려도 여기서 자른다


class CustomerDirectoryInteractor(CustomerDirectoryPort):
    """허브의 CustomerDirectoryPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, briefs: FamilyBriefRepository,
        search: CustomerSearchPort, signatures: ConsentSignatureRepository | None = None,
        forms: ConsentFormRepository | None = None, now: Callable[[], datetime] | None = None,
        settings: FormSettingsRepository | None = None,
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._briefs = briefs
        self._search = search
        # 서류(⑪)의 저장소 — care_facts 만 쓴다. 주지 않으면 서명·보낸 날을 싣지 않는다.
        self._signatures = signatures
        self._forms = forms
        self._now = now
        # 매장의 서류 설정(⑪-B) — 노령 나이와 동의 기한. 주지 않으면 기본값이다.
        self._settings = settings

    async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
        # 가족을 바꾸는 customer 유스케이스와 같은 잠금이다 — 익명화와 예약 생성이 서로를 기다린다.
        # 스포크 경계를 넘는 오류는 허브 오류로 바꿔 던진다 — 부르는 쪽은 customer 의 도메인 오류를 모른다.
        try:
            await self._customers.lock_active(ctx, customer_id)
        except CustomerNotFoundError as exc:
            raise FamilyNotFoundError(str(exc)) from exc
        if not pet_ids:
            return
        family = {pet.id: pet for pet in await self._pets.list_for_customers(ctx, [customer_id])}
        for pet_id in pet_ids:
            if pet_id not in family:
                raise FamilyPetNotFoundError("반려동물을 찾을 수 없습니다.")
            if family[pet_id].passed_away:
                raise FamilyPetPassedAwayError("무지개다리를 건넌 아이에게는 예약을 잡을 수 없습니다.")

    async def briefs(self, ctx: ShopContext, customer_ids: list[int], pet_ids: list[int]) -> FamilyBriefs:
        customers = await self._briefs.list_customer_briefs(ctx, customer_ids) if customer_ids else []
        pets = await self._briefs.list_pet_briefs(ctx, pet_ids) if pet_ids else []
        return FamilyBriefs(
            customers={c.customer_id: c for c in customers}, pets={p.pet_id: p for p in pets}
        )

    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
        await self._search.set_last_visit(ctx, customer_id, at)

    async def set_pet_weight(self, ctx: ShopContext, pet_id: int, weight_kg: Decimal) -> None:
        await self._pets.set_weight(ctx, pet_id, weight_kg)

    async def find_draft_candidates(self, ctx: ShopContext, words: tuple[str, ...]) -> list[DraftCandidate]:
        if not words:
            return []
        customer_ids = await self._search.match_any(ctx, parse_query(" ".join(words)), limit=_MATCH_LIMIT)
        if not customer_ids:
            return []
        customers = await self._customers.list_active(ctx, customer_ids)   # 익명화한 고객은 여기서 빠진다
        pets_of = {c.id: [] for c in customers}
        for pet in await self._pets.list_for_customers(ctx, [c.id for c in customers]):
            if not pet.passed_away:
                pets_of[pet.customer_id].append(pet)
        # 등급은 도메인(draft_ranking)이 매기고, 같은 등급 안에서는 고객 ID 오름차순이다.
        ranked = sorted(
            ((match_family(c, pets_of[c.id], words), c) for c in customers),
            key=lambda pair: (pair[0].rank, pair[1].id),
        )
        return [
            DraftCandidate(
                customer=CustomerBrief(customer_id=c.id, name=c.name, phone_masked=mask_phone(c.phone)),
                pets=tuple(
                    PetBrief(pet_id=p.id, customer_id=c.id, name=p.name, species=p.species, breed=p.breed,
                             weight_kg=p.weight_kg, passed_away=False)
                    for p in pets_of[c.id]
                ),
                matched_pet_ids=match.matched_pet_ids,
                exact=match.exact,
            )
            for match, c in ranked[:DRAFT_CANDIDATE_LIMIT]
        ]

    async def care_facts(
        self, ctx: ShopContext, customer_ids: tuple[int, ...], pet_ids: tuple[int, ...], today: date
    ) -> CareFacts:
        if not customer_ids:
            return CareFacts(known_customers=frozenset(), cautions={}, pets={})
        customers = await self._customers.list_active(ctx, list(customer_ids))   # 익명화·다른 매장은 여기서 빠진다
        known = frozenset(c.id for c in customers)
        cautions = {
            c.id: CautionFact(reason=c.caution_reason, until=c.caution_until)
            for c in customers
            if c.caution_reason is not None and caution_active(c.caution_until, today)
        }
        wanted = set(pet_ids)
        pets: dict[int, PetCareFact] = {}
        if wanted and known:
            found = [p for p in await self._pets.list_for_customers(ctx, sorted(known)) if p.id in wanted]
            covers, sent = await self._consent_marks(ctx, found)
            for pet in found:
                if pet.id in wanted:
                    pets[pet.id] = PetCareFact(
                        pet_id=pet.id, customer_id=pet.customer_id, birth_date=pet.birth_date,
                        birth_year=pet.birth_year,
                        conditions=tuple(
                            ConditionFact(label=c.custom_label or c.label, note=c.note)
                            for c in pet.conditions
                        ),
                        consent_on=pet.grooming_consent_on, passed_away=pet.passed_away,
                        consent_cover=covers.get(pet.id), consent_form_sent_on=sent.get(pet.id),
                    )
        policy = DEFAULT_FORM_SETTINGS if self._settings is None else await self._settings.get(ctx)
        return CareFacts(
            known_customers=known, cautions=cautions, pets=pets,
            senior_age=policy.senior_age, consent_days=policy.consent_days,
        )

    async def _consent_marks(self, ctx: ShopContext, pets) -> tuple[dict[int, ConsentCover], dict[int, date]]:
        """아이 → 서명이 덮는 것, 아이 → 살아 있는 동의서 링크를 보낸 날. 아이가 몇이든 질의는 둘이다."""
        if self._signatures is None or self._forms is None or self._now is None or not pets:
            return {}, {}
        signed = {p.id: p.grooming_consent_signature_id for p in pets
                  if p.grooming_consent_on is not None and p.grooming_consent_signature_id is not None}
        found = await self._signatures.covers(ctx, signed)
        covers = {
            pet_id: ConsentCover(
                senior=any("senior" in c.parts for c in found.get(pet_id, ())),
                condition_labels=frozenset().union(*(c.condition_labels for c in found.get(pet_id, ()))),
            )
            for pet_id in signed
        }
        zone = ZoneInfo(ctx.timezone)
        sent = await self._forms.sent_on(ctx, tuple(p.id for p in pets), self._now())
        return covers, {pet_id: at.astimezone(zone).date() for pet_id, at in sent.items()}

    async def contact(self, ctx: ShopContext, customer_id: int) -> CustomerContact | None:
        # 익명화한 고객과 다른 매장의 고객은 저장소가 "없음"으로 본다 — 둘 다 None 이다(N8).
        try:
            customer = await self._customers.get_active(ctx, customer_id)
        except CustomerNotFoundError:
            return None
        return CustomerContact(customer_id=customer.id, name=customer.name, phone=customer.phone,
                               marketing_consent=customer.marketing_consent)

    async def first_pets(self, ctx: ShopContext, customer_ids: tuple[int, ...]) -> dict[int, int]:
        if not customer_ids:
            return {}
        known = [c.id for c in await self._customers.list_active(ctx, list(customer_ids))]   # 익명화·다른 매장은 빠진다
        if not known:
            return {}
        first: dict[int, int] = {}
        alive: dict[int, int] = {}
        for pet in sorted(await self._pets.list_for_customers(ctx, known), key=lambda p: p.id):   # ID 가 등록 순서다
            first.setdefault(pet.customer_id, pet.id)
            if not pet.passed_away:
                alive.setdefault(pet.customer_id, pet.id)
        return first | alive
