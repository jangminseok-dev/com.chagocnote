from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand
from customer.app.use_cases.unmark_pet_passed_away_interactor import UnmarkPetPassedAwayInteractor
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_고객을_잠근_뒤_무지개다리를_되돌린다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed().id, passed_away=True)
    view = await UnmarkPetPassedAwayInteractor(customers, pets, search, today).unmark_pet_passed_away(
        UnmarkPetPassedAwayCommand(ctx=ctx(), pet_id=pet.id)
    )
    assert view.pet.passed_away_at is None
    assert journal == [("lock_customer", pet.customer_id), ("set_passed_away", pet.id, False),
                       ("rebuild", pet.customer_id)]
