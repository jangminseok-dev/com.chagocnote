from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.domain.errors import CustomerHasUpcomingVisitsError
from hub.app.ports.guardian_lifecycle_port import GuardianLifecyclePort
from hub.app.ports.search_index_port import SearchIndexPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


class DeleteCustomerInteractor(DeleteCustomerUseCase):
    """고객 삭제는 익명화다. 개인정보만 지우고 행은 남긴다(③·④의 기록이 가리킬 틀)."""

    def __init__(
        self, customers: CustomerRepository, search: CustomerSearchPort, ledger: VisitLedgerPort,
        guardians: GuardianLifecyclePort, index: SearchIndexPort,
        forms: ConsentFormRepository, signatures: ConsentSignatureRepository, now: Callable[[], datetime],
        intakes: IntakeFormRepository | None = None, answers: IntakeAnswerRepository | None = None,
    ) -> None:
        self._customers = customers
        self._search = search
        self._ledger = ledger
        self._guardians = guardians
        self._index = index
        self._forms = forms
        self._signatures = signatures
        self._now = now
        self._intakes = intakes
        self._answers = answers

    async def delete_customer(self, command: DeleteCustomerCommand) -> None:
        # 번호는 익명화하면 지워진다 — 그 번호로 낸 문진표의 답을 찾으려고 먼저 읽어 둔다.
        before = await self._customers.lock_active(command.ctx, command.customer_id)
        phones = tuple(phone for phone in (before.phone, before.phone_alt) if phone)
        if await self._ledger.customer_has_upcoming(command.ctx, command.customer_id):
            raise CustomerHasUpcomingVisitsError("앞으로의 예약이 남아 있습니다. 예약을 먼저 취소해 주세요.")
        await self._customers.anonymize(command.ctx, command.customer_id)
        # 서류(⑪) — 링크를 전부 닫고(이미 낸 것도) 서명(그림·적은 이름·보인 사실)을 지운다. 고객 행 → 서류 요청 행.
        await self._forms.close_for_customer(command.ctx, command.customer_id, self._now())
        await self._signatures.delete_for_customer(command.ctx, command.customer_id)
        if self._intakes is not None:
            await self._intakes.close_for_customer(command.ctx, command.customer_id, self._now())
        # 받은 문진표 — 이 고객에 이어 둔 답, 이 고객에게 보낸 링크의 답, 이 고객의 번호로 낸 답(이름·번호·적은 글)을 지운다.
        if self._answers is not None:
            await self._answers.delete_for_customer(command.ctx, command.customer_id, phones)
        # 보호자 계정과의 연결을 끝낸다 — 익명화한 고객의 기록이 보호자 쪽에 남지 않게(⑦ 설계 G9).
        await self._guardians.end_for_customer(command.ctx.shop_id, command.customer_id)
        await self._ledger.clear_customer_memos(command.ctx, command.customer_id)   # 방문 메모의 개인정보(V11)
        # 기록 검색의 글 사본을 이 트랜잭션에서 곧바로 지운다 — 색인기를 기다리지 않는다(⑨ 설계 3.5).
        await self._index.forget_customer(command.ctx, command.customer_id)
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)   # 익명화한 고객이라 줄이 지워진다
