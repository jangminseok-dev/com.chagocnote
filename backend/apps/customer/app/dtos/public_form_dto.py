from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from customer.app.dtos.consent_view_dto import ConsentDocumentView
from customer.domain.entities.intake import IntakeQuestion
from customer.domain.services.intake_rules import IntakeEntry


@dataclass(frozen=True)
class ReadPublicFormQuery:
    token: str | None      # 헤더로 받은 값 — 로그에 남기지 않는다
    client: str            # 접속 주소(횟수 제한용)


@dataclass(frozen=True)
class SubmitPublicConsentCommand:
    token: str | None
    client: str
    doc_digest: str
    signer_name: str
    signature_png: bytes


@dataclass(frozen=True)
class PublicIntakeConsent:
    """문진표 끝의 동의서 구역을 그릴 것(⑪-C1b). 어느 토막이 붙는지는 웹이 답으로 정하고 제출이 다시 본다."""

    all: bool                  # 매장이 `모든 아이에게` 를 켰다
    senior_age: int            # 이 나이부터 노령 토막
    texts: dict[str, str]      # 토막 → 지금 글
    digest: str                # 낼 때 그대로 돌려보낸다 — 연 뒤 글·기준이 바뀌었으면 409


@dataclass(frozen=True)
class IntakeConsentEntry:
    """문진표와 함께 낸 서명. 그림과 적은 이름은 로그에 남기지 않는다."""

    digest: str
    parts: tuple[str, ...]     # 보호자가 읽은 토막
    signer_name: str
    signature_png: bytes


@dataclass(frozen=True)
class PublicIntakeView:
    """보호자가 여는 문진표의 구성. 지금 값(품종·몸무게·지병)은 싣지 않는다 — 링크를 주운 사람이 본다."""

    mode: str                                  # new | add_pet | update
    pet_name: str | None                       # 다시 받기일 때만 — 누구의 문진표인지
    fields: tuple[str, ...]                    # 켜진 칸의 코드, 화면의 순서
    questions: tuple[IntakeQuestion, ...]      # 매장이 더한 질문
    condition_types: tuple[tuple[str, str], ...]   # (코드, 이름)
    answered: int                              # 이 링크로 이미 낸 답의 수
    keep_days: int = 30                        # 확인하지 않은 답을 지우는 날 수 — 개인정보 안내에 적는다
    guardian_needed: bool = False              # 보호자 이름·번호를 적어야 하나 — 새 손님의 첫 답(또는 첫 답을 매장이 이미 썼을 때)
    consent: PublicIntakeConsent | None = None   # 끝의 동의서 구역(⑪-C1b)


@dataclass(frozen=True)
class PublicFormView:
    """보호자가 보는 서류. document(동의서)나 intake(문진표)가 있으면 열려 있고, 없으면 낸(또는 매장에서 이미 받은) 것이다."""

    shop_name: str
    document: ConsentDocumentView | None
    submitted_on: date | None
    kind: str = "consent"
    intake: PublicIntakeView | None = None


@dataclass(frozen=True)
class SubmitPublicIntakeCommand:
    token: str | None
    client: str
    entry: IntakeEntry
    done: bool          # 다 적었어요 — 이 답을 끝으로 링크를 닫는다
    consent: IntakeConsentEntry | None = None   # 끝의 동의서 구역에서 한 서명(⑪-C1b)
