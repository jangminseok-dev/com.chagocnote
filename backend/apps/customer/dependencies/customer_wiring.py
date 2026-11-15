"""customer 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.consent_form_pg_repository import ConsentFormPgRepository
from customer.adapter.outbound.pg.consent_signature_pg_repository import ConsentSignaturePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.app.ports.output.pet_repository import PetRepository


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
