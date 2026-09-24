from __future__ import annotations

from media.app.dtos.media_myself_dto import MediaMyselfQuery, MediaMyselfResponse
from media.app.ports.input.media_myself_use_case import MediaMyselfUseCase
from media.app.ports.output.media_myself_record_port import MediaMyselfRecordPort


class MediaMyselfInteractor(MediaMyselfUseCase):
    def __init__(self, record: MediaMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: MediaMyselfQuery) -> MediaMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return MediaMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장의 사진·영상 객체를 관리합니다. 경로는 모두 /v1/shops/{shop_id} 아래이고 매 요청마다 매장 소속을 "
                "확인합니다. 파일은 서버를 거치지 않고 앱이 저장소(S3)에 직접 올립니다. "
                "POST /media/uploads 는 발급입니다: {kind: photo|video, content_type, byte_size, width, height, "
                "duration_seconds} 를 받아 pending 객체를 만들고 렌디션마다 PUT URL 을 줍니다(사진은 original·"
                "display·thumb 셋, 영상은 original·thumb 둘, 15분 유효, 인증 헤더 없이 Content-Type 을 서명대로 "
                "보내야 합니다). 사진은 image/jpeg 20MB, 영상은 video/mp4 200MB·60초까지입니다(HEIC 는 앱이 변환). "
                "POST /media/{media_id}/confirm 은 확인입니다: 저장소에 객체가 다 있는지·크기·형식을 보고 ready 로 "
                "바꿉니다(없으면 409 MEDIA_NOT_UPLOADED, 한도를 넘거나 형식이 다르면 객체를 지우고 422). "
                "이미 ready 면 그대로 돌려줍니다. 둘 다 record:write(사장·직원)가 필요하고, 같은 매장 멤버면 발급자가 "
                "아니어도 확인할 수 있습니다. 기록이 가져가지 않은 객체는 하루 뒤 정리 스크립트가 지웁니다. "
                "읽기 URL 은 기록·피드·고객 응답에 실려 나가고 매장 시간대 04:00 기준으로 하루 동안 같으며 최대 "
                "48시간 유효합니다. 다른 매장의 미디어 ID 는 404 입니다."
            ),
        )
