"""보낼 것 묶음의 조립(⑪ 설계 3.5) — 자리를 채우고, 빈칸이 든 글을 내보내지 않는다."""
from datetime import datetime
from zoneinfo import ZoneInfo

from visit.domain.services.send_bundle import build_bundle, fill

SEOUL = ZoneInfo("Asia/Seoul")
AT = datetime(2026, 11, 17, 14, 30, tzinfo=SEOUL)     # 화요일
RESERVATION = "[{매장}] 예약이 접수됐어요.\n{날짜} {시간}\n{아이}\n{메뉴}"
CONSENT = "미용 전에 동의서를 읽고 서명해 주세요.\n{링크}"
URL = "https://web.test/f/FAKE"


def bundle(**change):
    values = dict(shop_name="차곡 살롱", pet_names=["초코"], starts_at=AT, menu_names=["목욕", "위생미용"],
                  reservation_text=RESERVATION, consent_text=CONSENT, consent_pet_names=["초코"], consent_url=URL)
    return build_bundle(**(values | change))


def test_예약_안내와_동의서_토막이_차례로_나온다():
    parts = bundle()

    assert [p.kind for p in parts] == ["reservation", "consent"]
    assert parts[0].text == "[차곡 살롱] 예약이 접수됐어요.\n11월 17일(화) 오후 2:30\n초코\n목욕 · 위생미용"
    assert parts[1].text == "미용 전에 동의서를 읽고 서명해 주세요.\nhttps://web.test/f/FAKE"


def test_링크가_없으면_동의서_토막이_없다():
    assert [p.kind for p in bundle(consent_url=None, consent_pet_names=[])] == ["reservation"]


def test_메뉴가_없는_예약에는_메뉴_줄이_없다():
    assert bundle(menu_names=[])[0].text == "[차곡 살롱] 예약이 접수됐어요.\n11월 17일(화) 오후 2:30\n초코"


def test_보호자만의_예약에는_아이_줄이_없다():
    assert bundle(pet_names=[], menu_names=[])[0].text == "[차곡 살롱] 예약이 접수됐어요.\n11월 17일(화) 오후 2:30"


def test_가족이_함께_오면_아이_이름을_나란히_적는다():
    assert "초코 · 라떼" in bundle(pet_names=["초코", "라떼"])[0].text


def test_오전과_정오와_자정():
    at = lambda hour, minute=0: bundle(starts_at=AT.replace(hour=hour, minute=minute))[0].text   # noqa: E731
    assert "오전 9:05" in at(9, 5) and "오후 12:00" in at(12) and "오전 12:00" in at(0)


def test_매장이_고친_글을_쓰고_한_줄에_섞인_빈_자리는_흔적_없이_지운다():
    parts = bundle(reservation_text="{아이} · {메뉴} / {날짜} {시간}에 봬요", menu_names=[],
                   consent_text="{아이} 동의서예요 {링크}")
    assert parts[0].text == "초코 / 11월 17일(화) 오후 2:30에 봬요"
    assert parts[1].text == "초코 동의서예요 https://web.test/f/FAKE"


def test_모르는_자리와_중괄호는_글자_그대로_둔다():
    assert fill("{이름} { } {매장}", {"{매장}": "차곡"}) == "{이름} { } 차곡"


def test_채우고_나서_글이_비면_토막이_없다():
    assert [p.kind for p in bundle(reservation_text="{메뉴}", menu_names=[])] == ["consent"]
