"""동의서 유스케이스의 순서와 규칙 — 메모리 스텁으로(⑪-A). 실제 배선은 tests/integration/test_consent_wiring.py."""
import struct
from datetime import datetime, timedelta, timezone

import pytest

from customer.app.dtos.issue_consent_form_dto import IssueConsentFormCommand
from customer.app.dtos.revoke_form_dto import RevokeFormCommand
from customer.app.dtos.sign_consent_in_shop_dto import SignConsentInShopCommand
from customer.app.use_cases.issue_consent_form_interactor import IssueConsentFormInteractor
from customer.app.use_cases.revoke_form_interactor import RevokeFormInteractor
from customer.app.use_cases.sign_consent_in_shop_interactor import SignConsentInShopInteractor
from customer.app.services.consent_reader import read_document
from customer.domain.entities.consent import ConsentPolicy
from customer.domain.errors import ConsentDocumentChangedError, FormNotFoundError
from customer.tests.helpers.fakes import TODAY, FakeConsentForms, FakeConsentSignatures, family, today
from customer.tests.helpers.profiles import ctx

NOW = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)
POLICY = ConsentPolicy()


class _Source:
    """정해 둔 기준값을 주는 가짜 — 매장의 서류 설정 대신."""

    def __init__(self, policy=POLICY):
        self._policy = policy

    async def policy(self, ctx):
        return self._policy
KEY = b"k" * 32
PNG = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 600, 240) + b"\x00" * 20


def _world():
    journal, customers, pets, _, _ = family()
    forms, signatures = FakeConsentForms(journal), FakeConsentSignatures(journal)
    pet = pets.seed(customers.seed().id)
    return journal, customers, pets, forms, signatures, pet


def _issue(pets, signatures, forms):
    return IssueConsentFormInteractor(
        pets, signatures, forms, today, lambda: NOW, _Source(), link_key=KEY, web_base_url="https://web.test")


def _sign(pets, signatures, forms):
    return SignConsentInShopInteractor(pets, signatures, forms, today, lambda: NOW, _Source())


async def _digest(pets, signatures, pet_id):
    return (await read_document(ctx(), (pet_id,), TODAY, POLICY, pets=pets, signatures=signatures)).digest


async def test_보낼_때_고객_행을_먼저_잠그고_요청을_만든다():
    journal, _, pets, forms, signatures, pet = _world()

    view = await _issue(pets, signatures, forms).issue_consent_form(
        IssueConsentFormCommand(ctx=ctx(member_id=42), pet_ids=(pet.id,)))

    assert [entry[0] for entry in journal] == ["lock_customer", "lock_forms", "lock_forms", "create_form"]
    assert view.created and view.url.startswith("https://web.test/f/") and len(view.url.rsplit("/", 1)[1]) == 43
    assert view.expires_on == (NOW + timedelta(days=14)).date()
    assert forms.rows[view.form_id].created_by_member_id == 42


async def test_링크의_기간은_기준값을_따른다():
    _, _, pets, forms, signatures, pet = _world()
    use_case = IssueConsentFormInteractor(
        pets, signatures, forms, today, lambda: NOW, _Source(ConsentPolicy(link_days=3)), link_key=KEY, web_base_url="https://w")

    view = await use_case.issue_consent_form(IssueConsentFormCommand(ctx=ctx(), pet_ids=(pet.id,)))

    assert forms.rows[view.form_id].expires_at == NOW + timedelta(days=3)


async def test_현장_서명은_잠근_뒤에_쓰고_받은_날과_서명을_함께_찍는다():
    journal, _, pets, forms, signatures, pet = _world()

    signature_id = await _sign(pets, signatures, forms).sign_consent_in_shop(SignConsentInShopCommand(
        ctx=ctx(member_id=42), pet_ids=(pet.id,), doc_digest=await _digest(pets, signatures, pet.id),
        signer_name="  김민지  ", signature_png=PNG))

    assert [entry[0] for entry in journal] == [
        "lock_customer", "add_signature", "set_grooming_consent", "lock_forms"]
    assert pets.rows[pet.id].grooming_consent_on == TODAY
    assert pets.rows[pet.id].grooming_consent_signature_id == signature_id
    stored = signatures.rows[signature_id][1]
    assert (stored.signer_name, stored.channel, stored.form_id, stored.by_member_id) == ("김민지", "in_shop", None, 42)
    assert [p.part for p in stored.pets[0].parts] == ["basic"]


async def test_지문이_다르면_아무것도_쓰지_않는다():
    journal, _, pets, forms, signatures, pet = _world()

    with pytest.raises(ConsentDocumentChangedError):
        await _sign(pets, signatures, forms).sign_consent_in_shop(SignConsentInShopCommand(
            ctx=ctx(), pet_ids=(pet.id,), doc_digest="0" * 64, signer_name="김민지", signature_png=PNG))

    assert [entry[0] for entry in journal] == ["lock_customer"]


async def test_끊을_때_고객_행을_먼저_잠그고_다른_매장의_요청은_404(): 
    journal, customers, pets, forms, signatures, pet = _world()
    view = await _issue(pets, signatures, forms).issue_consent_form(IssueConsentFormCommand(ctx=ctx(), pet_ids=(pet.id,)))
    journal.clear()
    use_case = RevokeFormInteractor(forms, customers, lambda: NOW)

    with pytest.raises(FormNotFoundError):
        await use_case.revoke_form(RevokeFormCommand(ctx=ctx(shop_id=2), form_id=view.form_id))
    await use_case.revoke_form(RevokeFormCommand(ctx=ctx(), form_id=view.form_id))

    assert [entry[0] for entry in journal] == ["lock_customer", "revoke_form"]
    assert forms.rows[view.form_id].revoked_at == NOW
