from guardian.domain.entities.guardian_link import ENDED_BY, VERIFIED_BY
from guardian.tests.helpers.builders import kst, link


def test_끝난_시각이_없으면_살아_있는_연결이다():
    assert link().is_live is True
    assert link(ended_at=kst(11, 14), ended_by="shop").is_live is False


def test_확인_수단과_끝낸_쪽의_값():
    assert VERIFIED_BY == ("report_link", "family_invite")              # 가족 초대(⑫)
    assert ENDED_BY == ("guardian", "shop", "withdrawn", "anonymized", "primary")   # 기본 보호자가 가족을 끊음(⑫)
