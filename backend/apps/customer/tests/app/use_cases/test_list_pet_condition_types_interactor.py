from customer.app.dtos.list_pet_condition_types_dto import ListPetConditionTypesQuery
from customer.app.use_cases.list_pet_condition_types_interactor import ListPetConditionTypesInteractor
from customer.tests.helpers.fakes import FakeConditionTypes
from customer.tests.helpers.profiles import ctx


async def test_질병_종류를_순서대로_돌려준다():
    views = await ListPetConditionTypesInteractor(FakeConditionTypes()).list_pet_condition_types(
        ListPetConditionTypesQuery(ctx=ctx())
    )
    assert [(v.code, v.label) for v in views][-1] == ("other", "기타")
    assert [v.sort_order for v in views] == sorted(v.sort_order for v in views)
