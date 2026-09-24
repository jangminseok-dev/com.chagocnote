from media.app.dtos.media_myself_dto import MediaMyselfQuery
from media.app.use_cases.media_myself_interactor import MediaMyselfInteractor


class _Record:
    def __init__(self):
        self.calls = []

    async def record(self, subject, note):
        self.calls.append((subject, note))


async def test_자기소개는_묶음의_경로와_권한과_제약을_적는다():
    record = _Record()
    result = await MediaMyselfInteractor(record).introduce_myself(MediaMyselfQuery(id=6, name="미디어 (media)"))
    assert (result.id, result.name) == (6, "미디어 (media)")
    for words in ("POST /media/uploads", "POST /media/{media_id}/confirm", "record:write", "20MB", "200MB",
                  "MEDIA_NOT_UPLOADED", "48시간"):
        assert words in result.introduction
    assert record.calls == [("introduce_myself", "미디어 (media) 자기소개 조회")]
