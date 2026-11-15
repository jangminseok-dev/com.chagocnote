"""customer 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다.

스텁은 포트 ABC 를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간 잡힌다.
`apps/customer/tests/test_fakes_are_ports.py`가 이를 확인한다.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

from customer.app.dtos.customer_search_dto import SearchPage
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.entities.condition_type import ConditionType
from customer.domain.entities.consent import SignedCover
from customer.domain.entities.consent_form import (
    ConsentForm, SignatureBrief, SignatureDetail, SignaturePetDetail,
)
from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet, PetCondition
from customer.domain.errors import (
    CustomerNotFoundError, CustomerPhoneTakenError, FormNotFoundError, PetNotFoundError, SignatureNotFoundError,
)
from hub.app.dtos.media_urls import MediaUrls
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.search_index_port import SearchIndexPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort

TODAY = date(2026, 9, 22)
NOW = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)
LABELS = {"patella_luxation": "슬개골 탈구", "heart_disease": "심장 질환", "allergy": "알레르기",
          "other": "기타"}


def today() -> date:
    return TODAY


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeConditionTypes(ConditionTypeRepository):
    async def list_all(self):
        return [ConditionType(code=c, label=l, sort_order=i) for i, (c, l) in enumerate(LABELS.items())]


class FakeCustomers(CustomerRepository):
    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.rows: dict[int, Customer] = {}
        self._next = 1

    def seed(self, shop_id=1, name="김민지", phone="01012345678", consent=False) -> Customer:
        customer = Customer(id=self._next, shop_id=shop_id, name=name, phone=phone, phone_alt=None,
                            marketing_consent=consent, marketing_consent_changed_at=NOW, memo=None)
        self.rows[customer.id] = customer
        self._next += 1
        return customer

    def _find(self, ctx, customer_id) -> Customer:
        customer = self.rows.get(customer_id)
        if customer is None or customer.shop_id != ctx.shop_id:
            raise CustomerNotFoundError("고객을 찾을 수 없습니다.")
        return customer

    async def find_active_by_phone(self, ctx, phone):
        return next((c for c in self.rows.values() if c.shop_id == ctx.shop_id and c.phone == phone), None)

    async def get_active(self, ctx, customer_id):
        return self._find(ctx, customer_id)

    async def lock_active(self, ctx, customer_id):
        self.journal.append(("lock_customer", customer_id))
        return self._find(ctx, customer_id)

    async def list_active(self, ctx, customer_ids):
        return [c for i, c in self.rows.items() if i in customer_ids and c.shop_id == ctx.shop_id]

    async def create(self, ctx, profile):
        if await self.find_active_by_phone(ctx, profile.phone):
            raise CustomerPhoneTakenError("이미 등록된 전화번호입니다.")
        customer = self.seed(shop_id=ctx.shop_id, name=profile.name, phone=profile.phone,
                             consent=profile.marketing_consent)
        self.rows[customer.id] = replace(customer, phone_alt=profile.phone_alt, memo=profile.memo)
        self.journal.append(("create_customer", customer.id))
        return self.rows[customer.id]

    async def update(self, ctx, customer_id, profile, consent_changed):
        current = self._find(ctx, customer_id)
        self.rows[customer_id] = replace(
            current, name=profile.name, phone=profile.phone, phone_alt=profile.phone_alt,
            marketing_consent=profile.marketing_consent, memo=profile.memo,
        )
        self.journal.append(("update_customer", customer_id, consent_changed))
        return self.rows[customer_id]

    async def set_caution(self, ctx, customer_id, reason, until, member_id):
        self.rows[customer_id] = replace(
            self._find(ctx, customer_id), caution_reason=reason, caution_until=until
        )
        self.journal.append(("set_caution", customer_id, reason, until, member_id))
        return self.rows[customer_id]

    async def anonymize(self, ctx, customer_id):
        self._find(ctx, customer_id)
        del self.rows[customer_id]
        self.journal.append(("anonymize", customer_id))


class FakePets(PetRepository):
    def __init__(self, journal: Journal, customers: FakeCustomers) -> None:
        self.journal = journal
        self.customers = customers
        self.rows: dict[int, Pet] = {}
        self._next = 101

    def seed(self, customer_id, name="콩이", passed_away=False, conditions=()) -> Pet:
        pet = Pet(id=self._next, customer_id=customer_id, name=name, species="dog", breed="말티즈",
                  sex="female", neutered=True, birth_date=None, birth_year=2021,
                  weight_kg=Decimal("3.2"), no_known_conditions=not conditions,
                  memo=None, passed_away_at=NOW if passed_away else None, conditions=tuple(conditions))
        self.rows[pet.id] = pet
        self._next += 1
        return pet

    def _owned(self, ctx, pet_id) -> Pet:
        pet = self.rows.get(pet_id)
        owner = self.customers.rows.get(pet.customer_id) if pet else None
        if owner is None or owner.shop_id != ctx.shop_id:
            raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
        return pet

    async def get(self, ctx, pet_id):
        return self._owned(ctx, pet_id)

    async def lock_owner(self, ctx, pet_id):
        customer_id = self._owned(ctx, pet_id).customer_id
        self.journal.append(("lock_customer", customer_id))
        return customer_id

    async def list_for_customers(self, ctx, customer_ids):
        return [p for p in self.rows.values() if p.customer_id in customer_ids
                and self.customers.rows.get(p.customer_id) is not None
                and self.customers.rows[p.customer_id].shop_id == ctx.shop_id]

    async def add(self, ctx, customer_id, profile):
        pet = self.seed(customer_id, name=profile.name)
        self.rows[pet.id] = self._apply(pet, profile)
        self.journal.append(("add_pet", customer_id))
        return self.rows[pet.id]

    async def update(self, ctx, pet_id, profile):
        self.rows[pet_id] = self._apply(self._owned(ctx, pet_id), profile)
        self.journal.append(("update_pet", pet_id))
        return self.rows[pet_id]

    async def set_passed_away(self, ctx, pet_id, passed_away):
        self.rows[pet_id] = replace(self._owned(ctx, pet_id), passed_away_at=NOW if passed_away else None)
        self.journal.append(("set_passed_away", pet_id, passed_away))
        return self.rows[pet_id]

    async def set_weight(self, ctx, pet_id, weight_kg):
        self.rows[pet_id] = replace(self._owned(ctx, pet_id), weight_kg=weight_kg)
        self.journal.append(("set_weight", pet_id, weight_kg))

    async def set_grooming_consent(self, ctx, pet_id, received_on, member_id, signature_id=None):
        self.rows[pet_id] = replace(
            self._owned(ctx, pet_id), grooming_consent_on=received_on, grooming_consent_signature_id=signature_id)
        self.journal.append(("set_grooming_consent", pet_id, received_on, member_id))
        return self.rows[pet_id]

    async def count_for_customer(self, ctx, customer_id):
        return len([p for p in self.rows.values() if p.customer_id == customer_id])

    async def delete(self, ctx, pet_id):
        self._owned(ctx, pet_id)
        del self.rows[pet_id]
        self.journal.append(("delete_pet", pet_id))

    @staticmethod
    def _apply(pet: Pet, profile) -> Pet:
        return replace(
            pet, name=profile.name, species=profile.species, breed=profile.breed, sex=profile.sex,
            neutered=profile.neutered, birth_date=profile.birth_date, birth_year=profile.birth_year,
            weight_kg=profile.weight_kg, no_known_conditions=profile.no_known_conditions,
            memo=profile.memo,
            conditions=tuple(
                PetCondition(type_code=c.type_code, label=LABELS[c.type_code],
                             custom_label=c.custom_label, note=c.note)
                for c in profile.conditions
            ),
        )


class FakeSearch(CustomerSearchPort):
    def __init__(self, journal: Journal, page: SearchPage | None = None, pet_count: int = 0) -> None:
        self.journal = journal
        self.page = page or SearchPage(customer_ids=[], next_cursor=None)
        self.pet_count = pet_count
        self.requests = []
        self.matches: list[int] = []

    async def rebuild_search_entry(self, ctx, customer_id):
        self.journal.append(("rebuild", customer_id))

    async def set_last_visit(self, ctx, customer_id, at):
        self.journal.append(("set_last_visit", customer_id, at))

    async def search(self, ctx, request):
        self.requests.append((ctx, request))
        return self.page

    async def count_pets(self, ctx, words, include_passed):
        self.requests.append((ctx, words, include_passed))
        return self.pet_count

    async def match_any(self, ctx, words, limit):
        """낱말 하나라도 걸리는 가족 — 스텁은 미리 넣어 둔 ID 를 그대로 준다(순위는 인터랙터 몫)."""
        self.journal.append(("match_any", tuple(w.value for w in words), limit))
        return self.matches[:limit]


class FakeLedger(VisitLedgerPort):
    """VisitLedgerPort 스텁. 반려동물·고객마다 방문이 있는지, 앞으로의 예약이 있는지를 정해 둔다."""

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.pets_with_visits: set[int] = set()
        self.pets_with_upcoming: set[int] = set()
        self.customers_with_upcoming: set[int] = set()
        self.no_shows: dict[int, int] = {}
        self.upcoming: dict[int, list] = {}
        self.covers: dict[int, int] = {}   # 반려동물 ID → 대표 사진 media_id

    async def pet_has_visits(self, ctx, pet_id):
        return pet_id in self.pets_with_visits | self.pets_with_upcoming

    async def pet_has_upcoming(self, ctx, pet_id):
        return pet_id in self.pets_with_upcoming

    async def customer_has_upcoming(self, ctx, customer_id):
        return customer_id in self.customers_with_upcoming

    async def no_show_count(self, ctx, customer_id):
        return self.no_shows.get(customer_id, 0)

    async def upcoming_for_customer(self, ctx, customer_id, limit):
        return self.upcoming.get(customer_id, [])[:limit]

    async def clear_customer_memos(self, ctx, customer_id):
        self.journal.append(("clear_visit_memos", customer_id))

    async def latest_covers(self, ctx, pet_ids):
        self.journal.append(("latest_covers", sorted(pet_ids)))
        return {p: self.covers[p] for p in pet_ids if p in self.covers}


class FakeLibrary(MediaLibraryPort):
    """MediaLibraryPort 스텁 — customer 는 읽기 URL 만 쓴다. ready 는 URL 을 줄 수 있는 media_id 들이다."""

    def __init__(self) -> None:
        self.ready: set[int] = set()

    async def claim(self, ctx, media_ids):
        raise AssertionError("customer 는 미디어를 가져가지 않는다")

    async def release(self, ctx, media_ids):
        raise AssertionError("customer 는 미디어를 놓지 않는다")

    async def read_urls(self, ctx, media_ids):
        return {i: MediaUrls(media_id=i, kind="photo", original_url=f"o/{i}", download_url=f"dl/{i}",
                             display_url=f"d/{i}", thumb_url=f"t/{i}", width=3000, height=2000,
                             duration_seconds=None) for i in media_ids if i in self.ready}


def family():
    """스텁 한 벌을 같은 호출 기록으로 묶어 만든다."""
    journal = Journal()
    customers = FakeCustomers(journal)
    pets = FakePets(journal, customers)
    return journal, customers, pets, FakeConditionTypes(), FakeSearch(journal)


class FakeEvents(DomainEventPort):
    """DomainEventPort 스텁 — 검색 이벤트의 (scope, ref_id) 를 changed 에 모은다."""

    def __init__(self) -> None:
        self.changed: list[tuple[str, int]] = []

    async def publish(self, event):
        self.changed.append((event.scope, event.ref_id))


class FakeSearchIndex(SearchIndexPort):
    """SearchIndexPort 스텁 — 부른 것을 journal 에 남긴다."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()

    async def forget_customer(self, ctx, customer_id):
        self.journal.append(("forget_search", customer_id))


class FakeConsentForms(ConsentFormRepository):
    """동의서 요청의 메모리 스텁. 호출이 journal 에 남는다."""

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.rows: dict[int, ConsentForm] = {}
        self._next = 1

    async def create(self, ctx, customer_id, pet_ids, public_id, expires_at):
        form = ConsentForm(
            id=self._next, shop_id=ctx.shop_id, public_id=public_id, customer_id=customer_id,
            pet_ids=tuple(sorted(set(pet_ids))), expires_at=expires_at, revoked_at=None, submitted_at=None,
            created_by_member_id=ctx.member_id, created_at=NOW)
        self.rows[form.id] = form
        self._next += 1
        self.journal.append(("create_form", form.id, form.pet_ids))
        return form

    async def live_for_customer(self, ctx, customer_id, now):
        self.journal.append(("lock_forms", customer_id))
        return [f for f in self.rows.values()
                if f.shop_id == ctx.shop_id and f.customer_id == customer_id and f.is_live(now)]

    async def list_live(self, ctx, now):
        return sorted((f for f in self.rows.values() if f.shop_id == ctx.shop_id and f.is_live(now)),
                      key=lambda f: f.id, reverse=True)

    async def get(self, ctx, form_id):
        form = self.rows.get(form_id)
        if form is None or form.shop_id != ctx.shop_id:
            raise FormNotFoundError("서류를 찾을 수 없습니다.")
        return form

    async def revoke(self, ctx, form_id, now):
        form = self.rows.get(form_id)
        if form is not None and form.shop_id == ctx.shop_id and form.revoked_at is None and form.submitted_at is None:
            self.rows[form_id] = replace(form, revoked_at=now)
            self.journal.append(("revoke_form", form_id))

    async def set_pets(self, ctx, form_id, pet_ids):
        form = self.rows.get(form_id)
        if form is not None and form.shop_id == ctx.shop_id:
            self.rows[form_id] = replace(form, pet_ids=tuple(sorted(set(pet_ids))))
            self.journal.append(("set_form_pets", form_id, tuple(sorted(set(pet_ids)))))

    async def sent_on(self, ctx, pet_ids, now):
        found = {}
        for form in self.rows.values():
            if form.shop_id == ctx.shop_id and form.is_live(now):
                for pet_id in form.pet_ids:
                    if pet_id in pet_ids:
                        found[pet_id] = form.created_at
        return found

    async def find_public(self, public_id):
        return next((f for f in self.rows.values() if f.public_id == public_id), None)

    async def lock(self, form_id):
        self.journal.append(("lock_form", form_id))
        return self.rows.get(form_id)

    async def mark_submitted(self, form_id, now):
        form = self.rows.get(form_id)
        if form is not None and form.submitted_at is None:
            self.rows[form_id] = replace(form, submitted_at=now)
            self.journal.append(("submit_form", form_id))


class FakeConsentSignatures(ConsentSignatureRepository):
    """서명의 메모리 스텁. rows 는 서명 ID → (매장, NewSignature)."""

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.rows: dict[int, tuple[int, object]] = {}
        self._next = 1

    async def add(self, ctx, signature):
        self.rows[self._next] = (ctx.shop_id, signature)
        self.journal.append(("add_signature", self._next, tuple(p.pet_id for p in signature.pets)))
        self._next += 1
        return self._next - 1

    async def covers(self, ctx, since):
        found: dict[int, list[SignedCover]] = {}
        for shop_id, signature in self.rows.values():
            if shop_id != ctx.shop_id:
                continue
            for pet in signature.pets:
                if pet.pet_id in since and signature.signed_at.date() >= since[pet.pet_id]:
                    found.setdefault(pet.pet_id, []).append(SignedCover(
                        frozenset(p.part for p in pet.parts), frozenset(pet.condition_labels)))
        return {pet_id: tuple(covers) for pet_id, covers in found.items()}

    async def list_for_pet(self, ctx, pet_id):
        return [
            SignatureBrief(signature_id=sid, signed_at=sig.signed_at, channel=sig.channel,
                           signer_name=sig.signer_name, parts=tuple(p.part for p in pet.parts))
            for sid, (shop_id, sig) in sorted(self.rows.items(), reverse=True) if shop_id == ctx.shop_id
            for pet in sig.pets if pet.pet_id == pet_id
        ]

    def _owned(self, ctx, signature_id):
        found = self.rows.get(signature_id)
        if found is None or found[0] != ctx.shop_id:
            raise SignatureNotFoundError("서명을 찾을 수 없습니다.")
        return found[1]

    async def get(self, ctx, signature_id):
        sig = self._owned(ctx, signature_id)
        return SignatureDetail(
            signature_id=signature_id, signed_at=sig.signed_at, channel=sig.channel, signer_name=sig.signer_name,
            by_member_id=sig.by_member_id,
            pets=tuple(SignaturePetDetail(pet_id=p.pet_id, shown_pet_name=p.shown_pet_name,
                                          condition_labels=p.condition_labels, parts=p.parts) for p in sig.pets))

    async def image(self, ctx, signature_id):
        return self._owned(ctx, signature_id).signature_png

    async def delete_for_customer(self, ctx, customer_id):
        gone = [sid for sid, (shop_id, sig) in self.rows.items()
                if shop_id == ctx.shop_id and sig.customer_id == customer_id]
        for sid in gone:
            del self.rows[sid]
        self.journal.append(("delete_signatures_of_customer", customer_id))
        return len(gone)

    async def delete_for_pet(self, ctx, pet_id):
        count = 0
        for sid, (shop_id, sig) in list(self.rows.items()):
            if shop_id != ctx.shop_id or all(p.pet_id != pet_id for p in sig.pets):
                continue
            left = tuple(p for p in sig.pets if p.pet_id != pet_id)
            count += len(sig.pets) - len(left)
            if left:
                self.rows[sid] = (shop_id, replace(sig, pets=left))
            else:
                del self.rows[sid]
        self.journal.append(("delete_signatures_of_pet", pet_id))
        return count


def consent_stores(journal: Journal) -> dict:
    """서류(⑪)의 스텁 한 벌 — 인터랙터에 **로 넘긴다."""
    return dict(forms=FakeConsentForms(journal), signatures=FakeConsentSignatures(journal), now=lambda: NOW)

