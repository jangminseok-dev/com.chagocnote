"""진입점이 허브 포트 자리를 빠짐없이 채웠는지 확인한다. 자리를 새로 만들면 여기에 더한다."""
import main
from core.shop_guard import get_shop_access_port

_API_SLOTS = [get_shop_access_port]


def test_API_프로세스는_허브_포트_자리를_모두_채운다():
    missing = [slot.__name__ for slot in _API_SLOTS if slot not in main.app.dependency_overrides]
    assert missing == []
