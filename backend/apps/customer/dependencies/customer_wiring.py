"""customer 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.public_redis_limiter import PublicRedisLimiter
from core.redis import get_redis

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.consent_form_pg_repository import ConsentFormPgRepository
from customer.adapter.outbound.pg.consent_signature_pg_repository import ConsentSignaturePgRepository
from customer.adapter.outbound.pg.consent_text_pg_repository import ConsentTextPgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.form_settings_pg_repository import FormSettingsPgRepository
from customer.adapter.outbound.pg.intake_answer_pg_repository import IntakeAnswerPgRepository
from customer.adapter.outbound.pg.intake_form_pg_repository import IntakeFormPgRepository
from customer.adapter.outbound.pg.intake_question_pg_repository import IntakeQuestionPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.consent_text_repository import ConsentTextRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.app.ports.output.intake_question_repository import IntakeQuestionRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_source import ConsentSource
from customer.app.services.intake_reader import IntakeReader
from hub.app.ports.public_limiter_port import PublicLimiterPort


def build_customer_repository(db: AsyncSession) -> CustomerRepository:
    return CustomerPgRepository(db)


def build_pet_repository(db: AsyncSession) -> PetRepository:
    return PetPgRepository(db)


def build_condition_type_repository(db: AsyncSession) -> ConditionTypeRepository:
    return ConditionTypePgRepository(db)


def build_customer_search(db: AsyncSession) -> CustomerSearchPort:
    return CustomerSearchPgAdapter(db)


def build_family_brief_repository(db: AsyncSession) -> FamilyBriefRepository:
    return FamilyBriefPgRepository(db)


def build_consent_form_repository(db: AsyncSession) -> ConsentFormRepository:
    return ConsentFormPgRepository(db)


def build_consent_signature_repository(db: AsyncSession) -> ConsentSignatureRepository:
    return ConsentSignaturePgRepository(db)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_form_settings_repository(db: AsyncSession) -> FormSettingsRepository:
    return FormSettingsPgRepository(db)


def build_intake_form_repository(db: AsyncSession) -> IntakeFormRepository:
    return IntakeFormPgRepository(db)


def build_intake_answer_repository(db: AsyncSession) -> IntakeAnswerRepository:
    return IntakeAnswerPgRepository(db)


def build_intake_reader(db: AsyncSession) -> IntakeReader:
    return IntakeReader(
        settings=build_form_settings_repository(db), questions=build_intake_question_repository(db),
        condition_types=build_condition_type_repository(db), pets=build_pet_repository(db),
        answers=build_intake_answer_repository(db), source=build_consent_source(db),
    )


def build_intake_question_repository(db: AsyncSession) -> IntakeQuestionRepository:
    return IntakeQuestionPgRepository(db)


def build_consent_text_repository(db: AsyncSession) -> ConsentTextRepository:
    return ConsentTextPgRepository(db)


def build_consent_source(db: AsyncSession) -> ConsentSource:
    """동의의 기준값과 글을 매장의 서류 설정에서 읽는다(⑪-B)."""
    return ConsentSource(settings=build_form_settings_repository(db), texts=build_consent_text_repository(db))


def build_public_form_limiter() -> PublicLimiterPort:
    """공개 서류 경로의 횟수 제한. 알림장과 규칙은 같고 이름 공간이 다르다 — 서로의 수를 세지 않는다."""
    return PublicRedisLimiter(get_redis(), "customer:form")

