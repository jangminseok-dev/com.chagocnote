from datetime import date

import pytest

from customer.app.dtos.clear_pet_grooming_consent_dto import ClearPetGroomingConsentCommand
from customer.app.dtos.set_pet_grooming_consent_dto import SetPetGroomingConsentCommand
from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.use_cases.clear_pet_grooming_consent_interactor import ClearPetGroomingConsentInteractor
from customer.app.use_cases.set_pet_grooming_consent_interactor import SetPetGroomingConsentInteractor
from customer.app.use_cases.update_pet_interactor import UpdatePetInteractor
from customer.domain.entities.pet import PetCondition
from customer.domain.errors import CustomerInputError, PetNotFoundError
from customer.domain.value_objects.condition_entry import ConditionEntry
from customer.tests.helpers.fakes import FakeEvents, TODAY, family, today
from customer.tests.helpers.inputs import pet_input
from customer.tests.helpers.profiles import ctx


def _set(customers, pets):
    return SetPetGroomingConsentInteractor(customers, pets, today)


async def test_받은_날을_주지_않으면_오늘로_적고_적은_멤버를_남긴다():
    journal, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed().id)

    view = await _set(customers, pets).set_pet_grooming_consent(
        SetPetGroomingConsentCommand(ctx=ctx(member_id=42), pet_id=pet.id, received_on=None)
    )

    assert view.pet.grooming_consent_on == TODAY
    assert journal == [("lock_customer", pet.customer_id), ("set_grooming_consent", pet.id, TODAY, 42)]


async def test_지난_날로_적을_수_있고_다시_적으면_덮는다():
    _, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed().id)
    use_case = _set(customers, pets)

    await use_case.set_pet_grooming_consent(
        SetPetGroomingConsentCommand(ctx=ctx(), pet_id=pet.id, received_on=date(2026, 3, 1))
    )
    assert pets.rows[pet.id].grooming_consent_on == date(2026, 3, 1)
    view = await use_case.set_pet_grooming_consent(
        SetPetGroomingConsentCommand(ctx=ctx(), pet_id=pet.id, received_on=None)
    )
    assert view.pet.grooming_consent_on == TODAY


async def test_앞날은_잠그기_전에_거절한다():
    journal, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed().id)
    with pytest.raises(CustomerInputError):
        await _set(customers, pets).set_pet_grooming_consent(
            SetPetGroomingConsentCommand(ctx=ctx(), pet_id=pet.id, received_on=date(2026, 9, 23))
        )
    assert journal == []
    assert pets.rows[pet.id].grooming_consent_on is None


async def test_다른_매장의_아이에게는_적지_못한다():
    journal, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await _set(customers, pets).set_pet_grooming_consent(
            SetPetGroomingConsentCommand(ctx=ctx(shop_id=1), pet_id=pet.id, received_on=None)
        )
    assert journal == []


async def test_직원도_적고_무지개다리_아이에게도_적는다():
    _, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed().id, passed_away=True)
    view = await _set(customers, pets).set_pet_grooming_consent(
        SetPetGroomingConsentCommand(ctx=ctx(role="staff"), pet_id=pet.id, received_on=None)
    )
    assert view.pet.grooming_consent_on == TODAY


async def test_지우면_없고_없던_것을_지워도_된다():
    journal, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed().id)
    clear = ClearPetGroomingConsentInteractor(customers, pets, today)
    await _set(customers, pets).set_pet_grooming_consent(
        SetPetGroomingConsentCommand(ctx=ctx(), pet_id=pet.id, received_on=None)
    )

    view = await clear.clear_pet_grooming_consent(ClearPetGroomingConsentCommand(ctx=ctx(), pet_id=pet.id))
    assert view.pet.grooming_consent_on is None
    again = await clear.clear_pet_grooming_consent(ClearPetGroomingConsentCommand(ctx=ctx(), pet_id=pet.id))
    assert again.pet.grooming_consent_on is None
    assert journal[-2:] == [("lock_customer", pet.customer_id), ("set_grooming_consent", pet.id, None, None)]


def _allergy():
    return PetCondition(type_code="allergy", label="알레르기", custom_label=None, note=None)


async def _update(customers, pets, types, search, pet_id, conditions):
    return await UpdatePetInteractor(customers, pets, types, search, today, events=FakeEvents()).update_pet(
        UpdatePetCommand(
            ctx=ctx(), pet_id=pet_id,
            pet=pet_input(no_known_conditions=not conditions, conditions=tuple(conditions)),
        )
    )


async def test_지병을_더하면_받아_둔_동의가_비워진다():
    journal, customers, pets, types, search = family()
    pet = pets.seed(customers.seed().id, conditions=[_allergy()])
    await pets.set_grooming_consent(ctx(), pet.id, date(2026, 3, 1), 11)
    journal.clear()

    view = await _update(customers, pets, types, search, pet.id, [
        ConditionEntry(type_code="allergy", custom_label=None, note=None),
        ConditionEntry(type_code="heart_disease", custom_label=None, note=None),
    ])

    assert view.pet.grooming_consent_on is None
    assert ("set_grooming_consent", pet.id, None, None) in journal
    assert journal[0] == ("lock_customer", pet.customer_id)   # 잠근 뒤에 읽고 쓴다


@pytest.mark.parametrize("conditions", [
    [],                                                                   # 뺐다
    [ConditionEntry(type_code="allergy", custom_label=None, note="닭고기")],   # 메모만 고쳤다
])
async def test_지병을_빼거나_메모만_고치면_동의는_그대로다(conditions):
    journal, customers, pets, types, search = family()
    pet = pets.seed(customers.seed().id, conditions=[_allergy()])
    await pets.set_grooming_consent(ctx(), pet.id, date(2026, 3, 1), 11)
    journal.clear()

    view = await _update(customers, pets, types, search, pet.id, conditions)

    assert view.pet.grooming_consent_on == date(2026, 3, 1)
    assert not [entry for entry in journal if entry[0] == "set_grooming_consent"]


async def test_동의가_없던_아이는_지병을_더해도_동의를_건드리지_않는다():
    journal, customers, pets, types, search = family()
    pet = pets.seed(customers.seed().id)
    await _update(customers, pets, types, search, pet.id,
                  [ConditionEntry(type_code="allergy", custom_label=None, note=None)])
    assert not [entry for entry in journal if entry[0] == "set_grooming_consent"]
