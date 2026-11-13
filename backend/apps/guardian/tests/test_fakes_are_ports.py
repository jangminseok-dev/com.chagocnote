from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.tests.helpers.fakes import FakeLinks


def test_스텁은_포트를_상속한다():
    assert issubclass(FakeLinks, GuardianLinkRepository)
    FakeLinks()   # 추상 메서드가 남아 있으면 여기서 TypeError
