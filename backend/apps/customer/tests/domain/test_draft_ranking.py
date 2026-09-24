from customer.domain.services.draft_ranking import FamilyMatch, match_family, phone_digits
from customer.tests.helpers.fakes import FakeCustomers, FakePets, Journal


def _family(name="김민지", phone="01012345678", pet_names=("콩이",)):
    journal = Journal()
    customers = FakeCustomers(journal)
    customer = customers.seed(name=name, phone=phone)
    pets = FakePets(journal, customers)
    return customer, [pets.seed(customer.id, n) for n in pet_names]


def test_반려동물_이름이_맞으면_0등급이고_맞은_아이를_준다():
    customer, (kong, dubu) = _family(pet_names=("콩이", "두부"))
    assert match_family(customer, [kong, dubu], ("두부", "토요일")) == FamilyMatch(0, (dubu.id,))
    assert match_family(customer, [kong, dubu], ("두부",)).exact


def test_보호자_이름이_맞으면_1등급이다():
    customer, pets = _family()
    match = match_family(customer, pets, ("김민지",))
    assert (match.rank, match.matched_pet_ids, match.exact) == (1, (), True)


def test_전화는_8자리_이상_포함이거나_4자리_뒷자리다():
    customer, pets = _family(phone="01012345678")
    assert match_family(customer, pets, ("010-1234-5678",)).rank == 2
    assert match_family(customer, pets, ("12345678",)).rank == 2
    assert match_family(customer, pets, ("5678",)).rank == 2
    assert match_family(customer, pets, ("1234",)).rank == 3   # 앞자리 넷은 아니다
    assert match_family(customer, pets, ("567",)).rank == 3


def test_아무것도_맞지_않으면_3등급_부분_일치다():
    customer, pets = _family()
    match = match_family(customer, pets, ("콩",))
    assert (match.rank, match.exact) == (3, False)


def test_숫자_낱말만_전화로_본다():
    assert phone_digits(("010-1234-5678", "콩이", "3시", "5678")) == ["01012345678", "5678"]
