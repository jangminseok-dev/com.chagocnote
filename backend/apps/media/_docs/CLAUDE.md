# media — 사진·영상 객체

소유 데이터: `media_objects`(메타데이터). 파일은 객체 저장소(S3 호환 — 개발은 compose 의 MinIO)에 있다.

- 파일은 서버를 거치지 않는다. 앱이 발급(`POST /media/uploads`)으로 받은 서명 URL 로 저장소에 바로 PUT 하고, 확인(`POST /media/{media_id}/confirm`)이 저장소를 HEAD 로 대조해 pending → ready 로 바꾼다(조건부 UPDATE — 동시에 두 번 확인해도 한 번). 서버는 파일을 디코딩하지 않는다. 가로·세로·길이는 앱 선언값이고 범위만 본다.
- 받는 것과 한도는 `domain/services/media_rules.py` 한 곳이다: 사진 `image/jpeg` 20MB(원본·표시용·썸네일 셋), 영상 `video/mp4` 200MB·60초(원본·포스터 둘). 확인 때 한도를 넘거나 형식이 다르면 객체를 지우고 422 다.
- **객체 키는 렌디션이 앞이다** — `original/shops/{매장}/{ID}.jpg`, `original-video/…mp4`, `display/…`, `thumb/…`. S3 수명주기 규칙은 접두사로만 거르므로 원본만 싼 계층으로 옮기려면(`scripts/ensure_media_bucket.py`) 이 모양이어야 한다.
- 읽기 URL 은 매장 시간대의 가장 최근 04:00 을 서명 시각으로, 48시간 유효로 만든다(`domain/services/url_expiry.py`) — 하루 동안 글자까지 같아 앱·CDN 캐시가 맞고, 남은 유효 시간은 24~48시간이다. botocore 는 서명 시각을 늘 '지금'으로 찍어서 GET 서명만 `adapter/outbound/s3/sigv4_query.py`가 직접 만든다(botocore 와 글자까지 같은지 테스트가 본다). PUT 서명은 boto3 가 한다.
- 서명은 앱이 닿는 **공개 주소**(`S3_PUBLIC_ENDPOINT_URL`)로, HEAD·DELETE 는 서버가 닿는 **내부 주소**(`S3_ENDPOINT_URL`)로 한다 — 서명에 호스트가 들어간다. 저장소 호출(HEAD·DELETE)은 잠금을 쥔 채 하지 않는다.
- 허브 포트 `MediaLibraryPort`를 구현한다(`app/use_cases/media_library_interactor.py`, HTTP 없음). visit 이 기록에 붙일 때 가져가고(`claim` — 준비됐고 이 매장의 것이고 아무도 안 가져간 것만, 전부 되거나 전부 안 됨, 세이브포인트) 뺄 때 놓는다(`release`). customer·visit 이 읽기 URL 을 받는다(`read_urls`). media 는 어느 기록이 가져갔는지 모른다 — `attached_at`만 안다.
- 놓였거나 가져가지 않은 미디어는 바로 지우지 않는다. `scripts/purge_stale_media.py`가 하루 넘은 것(pending, 또는 ready 인데 미부착 — 놓기가 `ready_at`을 다시 찍으므로 놓인 미디어는 놓인 시각부터 하루)을 표시 → 저장소 삭제 → 행 삭제 순서로 지운다. 운영에서는 이 스크립트를 주기적으로 돌린다.
- 이 스포크는 다른 스포크를 import 하지 않는다. 다른 스포크의 허브 포트도 쓰지 않는다.
