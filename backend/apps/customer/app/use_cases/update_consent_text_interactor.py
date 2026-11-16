from __future__ import annotations

from customer.app.dtos.consent_text_view_dto import ConsentTextView
from customer.app.dtos.update_consent_text_dto import UpdateConsentTextCommand
from customer.app.ports.input.update_consent_text_use_case import UpdateConsentTextUseCase
from customer.app.ports.output.consent_text_repository import ConsentTextRepository
from customer.app.use_cases.list_consent_texts_interactor import text_view
from customer.domain.errors import CustomerInputError
from customer.domain.services.consent_text import PARTS, check_body


class UpdateConsentTextInteractor(UpdateConsentTextUseCase):
    """동의서 토막의 글을 고친다(⑪ 설계 3.2). 새 판이 쌓이고 **그 뒤의 서명부터** 새 글이다.

    옛 판은 지우지 않는다 — 옛 서명을 그 글자로 다시 보인다. 이미 받은 동의를 다시 받게 하지 않는다.
    """

    def __init__(self, texts: ConsentTextRepository) -> None:
        self._texts = texts

    async def update_consent_text(self, command: UpdateConsentTextCommand) -> ConsentTextView:
        if command.part not in PARTS:
            raise CustomerInputError("동의서에 없는 토막입니다.")
        if command.body is not None:
            check_body(command.body)
        current = (await self._texts.latest(command.ctx)).get(command.part, (0, None))[1]
        # 지금 글과 같으면 판을 쌓지 않는다 — 저장을 두 번 눌러도 지문이 바뀌지 않는다.
        if command.body != current:
            await self._texts.append(command.ctx, command.part, command.body)
        return text_view(command.part, command.body)
