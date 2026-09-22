import pytest

from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
from customer.app.use_cases.mark_pet_passed_away_interactor import MarkPetPassedAwayInteractor
from customer.domain.errors import PetNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_고객을_잠근_뒤_무지개다리를_표시한다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed().id)
    view = await MarkPetPassedAwayInteractor(customers, pets, search, today).mark_pet_passed_away(
        MarkPetPassedAwayCommand(ctx=ctx(), pet_id=pet.id)
    )
    assert view.pet.passed_away_at is not None
    assert journal == [("lock_customer", pet.customer_id), ("set_passed_away", pet.id, True),
                       ("rebuild", pet.customer_id)]


async def test_다른_매장의_반려동물은_404_다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await MarkPetPassedAwayInteractor(customers, pets, search, today).mark_pet_passed_away(
            MarkPetPassedAwayCommand(ctx=ctx(shop_id=1), pet_id=pet.id)
        )
    assert journal == []
