from visit.domain.services.visit_duration import default_duration
from visit.tests.helpers.fakes import FakeMenus


def _menus(*minutes):
    fake = FakeMenus()
    return [fake.seed(name=f"메뉴{i}", minutes=m) for i, m in enumerate(minutes)]


def test_메뉴의_기본_소요를_더한다():
    assert default_duration(_menus(60, 30), shop_default_minutes=120) == 90


def test_기본_소요가_없는_메뉴는_매장_기본으로_센다():
    assert default_duration(_menus(60, None), shop_default_minutes=120) == 180


def test_메뉴가_없으면_매장_기본_소요다():
    assert default_duration([], shop_default_minutes=90) == 90
