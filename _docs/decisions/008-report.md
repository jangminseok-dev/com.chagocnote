# 008 — 미용 알림장(⑤)에서 내린 결정

설계: `docs/superpowers/specs/2026-09-28-report-design.md`. 이 기록은 계획마다 절을 더한다(⑤-1 백엔드 → ⑤-2 웹 → ⑤-3 앱).

## 사용자와 정한 것 (2026-09-28)

설계 2절 그대로다.

| 주제 | 결정 |
|---|---|
| 링크 기간 | 매장이 설정에서 고른다 — 7일·30일·계속(무기한). 기본 30일 |
| 실리는 사진·영상 | 기본은 전부. 보내기 전 미리보기에서 빼고 싶은 것만 뺀다 |
| 함께 보여 줄 항목 | 메뉴 이름·금액·몸무게·매장 정보를 모두 만들고 매장이 켜고 끈다. 한 번 정하면 바꿀 때까지 유지 |
| 항목의 처음 값 | 메뉴 이름·매장 정보 켬, 금액·몸무게 끔 |
| 보낸 뒤 기록 수정 | 같은 링크에 바로 반영. 알림장은 기록을 비추는 창이다 |
| '보냄' 판정 | 링크를 만든 시점. 공유 시트에서 실제로 보냈는지는 앱이 알 수 없다 |
| 끊기·재발급 | 끊거나 기간이 지나면 옛 링크는 영영 안 열리고 방문은 '안 보냄'으로 돌아간다. 다시 보내면 주소가 다른 새 링크. 살아 있는 동안 다시 공유하면 같은 링크 |
| 미리보기 카드 | 미용 후 대표 사진 + "○○의 미용 알림장" + 날짜·매장 이름 |
| 열람 확인 | 처음 연 시각만. 횟수·접속 주소·기기 정보는 저장하지 않는다 |
| 웹 방식 | Next.js 서버 렌더링, 저장소의 `web/`, Vercel |
| 토큰 저장소 | 링크는 Postgres. Redis 는 횟수 제한에만 쓴다. 조회 결과 캐시는 두지 않는다 |
| 권한 | 보내기·끊기는 `record:write`(직원 가능), 알림장 설정 변경은 `shop:update`(사장만) |
| 앱 화면 | 전부 네이티브. 웹뷰 패키지를 넣지 않는다 |
| 미루는 것 | CloudFront 서명 URL, 서버 측 EXIF 검증, 실제 Vercel 배포 |

## ⑤-1 백엔드에서 정한 것

visit 스포크에 알림장 링크(발급·끊기·미리보기), 알림장 설정, 공개 조회와 열람 신호, 횟수 제한. 허브 포트 `ShopProfilePort`(tenancy 구현)와 `MediaUrls.download_url`(media). 새 라우트 7개(설정 둘, 매장용 알림장 셋, 공개 둘 — 라우트 표의 나머지는 그대로), 마이그레이션 0010(`visit_reports`, `visit_record_media.hidden_from_report`, `visit_shop_settings`의 `report_*` 다섯 칸), 새 비밀값 `REPORT_LINK_KEY_B64`, 스크립트 `check_report_flow.sh`. 단위 883 → 1294, 통합 300 → 399, 구조 계약 6종. 새 의존성은 없다.

### 이 계획에서 새로 정한 것

- **토큰은 `public_id + HMAC`으로 매번 계산하고 저장하지 않는다.** DB 에는 `public_id`(16바이트)만 있다. 살아 있는 링크를 다시 공유할 수 있고, DB 만 유출되어서는 링크를 열 수 없다. 키를 바꾸면 모든 링크가 닫힌다.
- **공개 API 는 토큰을 헤더로 받는다**(`X-Report-Token`). 경로에 두면 백엔드와 게이트웨이의 접속 기록에 남는다. 질의 문자열로 보내도 읽지 않는다.
- **뺀 사진 표시는 링크가 아니라 사진 줄에 붙는다.** 링크를 끊고 새로 보내도 빠져 있다.
- **`PUT …/report`의 `hidden_media_ids`는 "뺄 것 전부"다.** 목록에 없는 것은 앞서 뺐더라도 되살아난다. 같은 본문으로 여러 번 불러도 결과가 같다.
- **살아 있는 링크가 있는 방문은 되돌리기·기록 삭제를 할 수 없다**(409 `VISIT_REPORT_SENT`). 링크를 먼저 끊는다.
- **Redis 장애 때 횟수 제한은 통과시킨다.** 경고 로그를 남긴다. 토큰 크기(무작위 128비트 + 서명 128비트)가 1차 방어다.
- **`report_sent`는 하루 목록·피드의 항목에, `report`는 방문 상세에 있다.** 달력은 날짜 칸이 방문 단위가 아니라 바꾸지 않는다.
- 발급은 기간이 지난 줄을 먼저 닫는다(`close_expired` → `get_live` → `create`). 기간이 지나 닫힌 줄과 끊은 줄은 `revoked_at`만으로는 구분되지 않는다(`expires_at <= revoked_at`이면 기간이 지나 닫힌 것).
- 요청 하나에서 지금 시각은 한 번만 읽는다. 닫기·살아 있음 판단·`created_at`·`expires_at`이 같은 시각이다.
- 링크의 기간은 만들 때 정해진다. 보여 줄 항목은 조회할 때마다 읽는다.
- 끊기는 뺀 표시를 건드리지 않고 방문의 상태도 보지 않는다.
- 공개 조회용 `ShopContext`는 `public_context` 한 곳이 만든다(멤버 ID 0, 역할 `public`, 권한 없음, 매장의 시간대).
- 횟수 제한의 접속 주소는 해시해서 Redis 키에 넣는다. 410 은 실패로 세지 않는다.
- 내려받는 파일 이름은 `chagocnote-{미디어 ID}.jpg`·`.mp4`다.

### 설계·브리프와 다르게 간 것

- **429 의 코드는 `TOO_MANY_ATTEMPTS`다.** 기존 초대 코드 시도 제한(tenancy)이 쓰는 이름에 맞췄다.
- **"로그인 없이 열리는 경로" 목록은 `find_route_violations`가 아니라 `routes_without_login` + 프로세스별 테스트다.** `find_route_violations`에 넣으면 기존 테스트의 가짜 앱(로그인 의존성이 없는 경로)이 새 위반을 낸다. 프로세스마다 목록 전체를 `==`로 못 박는다(API 넷, 인증 다섯). `/v1/public/` 규칙 둘(허용 목록, 로그인·매장 확인 금지)은 `find_route_violations` 안에 있다.
- **공개 응답의 캐시·검색 금지 헤더는 200·204 에만 달린다.** 오류 응답은 앱 전체의 오류 처리기가 만들어 헤더가 없다. 보호자가 닿는 것은 웹 서버이고 웹(⑤-2)이 모든 응답에 단다.
- **보내기는 설정을 링크를 읽기 전에 한 번만 읽는다.** 설계의 순서("링크가 없으면 설정을 읽어")대로면 새 링크일 때 두 번 읽는다. 검사 → 쓰기의 순서는 그대로다.
- **`append_media`를 고쳤다.** 있던 미디어를 다시 만들어 뺀 표시를 잃던 것을 순서만 바꾸게 했다(`replace(m, sort_order=…)`). 전체 교체는 설계대로 `carry_hidden`이다.
- **되돌리기가 아닌 전이도 링크를 읽는다**(질의 하나). 행동을 가리면 인터랙터가 "어느 행동이 링크를 보는가"를 알게 된다 — 그것은 상태 클래스의 일이다.
- **`report_sent`는 `VisitView`가 아니라 항목에 있다**(`DayVisitItemView`·`FeedItemView`). `VisitView`에 두면 등록·수정·전이 응답에도 칸이 생기고 그때마다 링크를 읽어야 한다.
- **뷰 DTO 를 만들지 않은 곳.** 알림장 설정 유스케이스는 도메인의 `ReportSettings`를 그대로 돌려준다(칸이 똑같다). 보내기는 미리보기의 `VisitReportPreview`·`VisitReportSchema`를 함께 쓴다.
- **`ReportLinkView.in_zone(zone)`을 더했다.** `describe_link`는 시간대를 받지 않고 UTC 를 담는다. 응답으로 내보내는 쪽이 매장 시간대로 바꾼다.
- **공개 인터랙터는 DTO(`token`, `client`)를 받고 `PublicReportView(report, expires_at)`를 돌려준다.** 횟수 제한에 접속 주소가 필요하고 `ReportView`에는 `expires_at`이 없다.
- **공개 라우터는 `JSONResponse`를 직접 돌려준다.** `response_model_exclude`는 요청마다 바꿀 수 없다. 스키마는 OpenAPI 문서에만 쓰이고 본문은 `PublicReportSchema.body()`가 만든다.
- **제한기 포트는 메서드 셋이다**(`allow`, `note_miss`, `missed_too_much`). 요청 세기(`allow`)와 실패 세기(`note_miss`)와 실패 수 읽기(`missed_too_much`)가 각각 다른 Redis 호출이다. 한도 상수는 어댑터에 있다.
- 설계 7.1 은 "실패는 10분에 20회, 넘으면 429"라고만 했다. 계획서의 코드는 이를 그 주소의 모든 요청에 걸었는데, 작업 검토가 "한 통을 나눠 쓰는 보호자 전체를 익명 요청 20번으로 막을 수 있다"고 짚어 서명이 틀린 요청에만 걸도록 고쳤다. 실패 수 차단은 억지력이지 추측 속도 제한이 아니다 — 추측을 막는 것은 토큰의 크기다.
- **`read_token`에 "32바이트가 아니면 None" 검사가 없다.** 43글자는 언제나 32바이트로 풀려 닿을 수 없는 가지다. 길이와 문자 집합은 정규식 하나가 본다.
- **매장 범위 저장소는 조인이 아니라 하위 질의로 거른다**(`visit_id IN (SELECT id FROM visits WHERE shop_id = …)`). UPDATE 는 조인을 못 쓴다. 공개 조회의 `find`만 조인이다.
- **`visit_reports.created_at`에 `server_default now()`가 있다.** 기존 표들의 모양을 따랐고 저장소는 언제나 시각을 넘긴다.
- **tenancy 저장소에 `find_by_id`를 더했다.** 기존 `get_by_id`는 없는 매장에서 터진다.
- **`presign_get_url`이 더 받는 것은 `content_disposition` 하나다.** 일반 질의 매개변수로 넓히지 않았다. `attachment; filename="…"` 글자열은 어댑터가 만들고 포트는 파일 이름만 받는다.
- **보내기·끊기의 스키마 상한은 도메인의 `MAX_HIDDEN`을 가져다 쓴다**(33).
- **`.env.example`·`generate_dev_env.py`에 `REPORT_WEB_SECRET`도 넣었다.**
- **통합 테스트에 "권한 없는 역할의 403"이 없다.** 시드의 역할 둘(사장·직원)이 모두 `record:write`를 가진다. 라우터 단위 테스트가 권한을 줄인 스텁으로 본다.
- 자기소개(`visit/myself`)에 새 경로와 규칙을 더했다.
- 흐름 스크립트는 설계 11.1 의 다섯 단계에 설정·미리보기·되돌리기 거절·다시 보내기·위조 토큰·내려받기를 더해 열셋이다. 토큰과 서명 URL 은 화면에 찍지 않는다.

### 알려진 동작 — 막지 않기로 했다

- `link_days`에 `30.0`·`7.0`을 보내면 받아들인다(저장은 정수). `30.5`·`"30"`·`true`는 422 다.
- 알림장 설정을 처음 저장하는 매장에는 일정 설정 행과 기본 메뉴가 함께 생긴다.
- 뺀 사진을 기록에서 지웠다가 다시 붙이면 다시 보인다(새로 붙인 사진으로 본다).
- 살아 있는 링크가 있는 방문에 사진을 덧붙이면 바로 보호자에게 보인다.
- 살아 있는 링크가 있으면 사진을 전부 빼거나 메모를 비워도 막지 않는다. 페이지는 이름과 날짜만 보인다.
- 익명화한 고객의 방문에 다시 보내면 404 `CUSTOMER_NOT_FOUND`다(기존 가족 잠금이 거절한다). 코드가 `VISIT_…`가 아니다.
- 조회와 열람 신호는 같은 통에 센다 — 페이지를 한 번 열면 요청이 둘이다.
- 429 는 맞는 토큰에는 나지 않는다 — **실패 수 차단은 서명이 틀린 요청에만 건다.** 같은 접속 주소의 서명이 틀린 요청이 10분에 20번을 넘으면 그 주소의 다음 틀린 요청부터 429(세지 않는다). 서명이 맞는 토큰은 실패가 몇 번 쌓였든 막히지 않는다 — 분당 60회의 전체 한도만 받는다.
- 웹 서버의 비밀값이 없으면 모든 보호자가 연결 주소 하나로 세어진다.
- `X-Report-Client-IP`의 형식은 검사하지 않는다. 비밀값이 새면 제한을 피할 수 있다.
- 서명 주소(객체 키)와 내려받는 파일 이름에 매장 ID·미디어 ID 숫자가 들어 있다. 응답에 ID 칸은 없다. 감추려면 객체 키 규칙을 바꿔야 한다 — 하지 않는다.
- 대표 사진의 가로·세로는 원본의 크기다(비율은 같다).
- 닫힌 이유(끊음·기간·정지·익명화)는 가르지 않고 모두 410 `REPORT_CLOSED`다.
- 미리보기(GET)는 잠그지 않는다. 기록 쓰기와 겹치면 앞뒤가 섞인 모습을 볼 수 있다.
- 기록 PUT·덧붙이기의 응답에는 `hidden`이 없다. 앱은 뺀 표시를 미리보기에서만 본다.

### 막지 못하고 감수하는 것

설계 7.6 그대로다.

1. 링크를 끊거나 사진을 빼도, 그 전에 미디어 서명 주소를 복사해 둔 사람은 최대 48시간 그 파일을 열 수 있다.
2. 카카오톡 대화방에 이미 뜬 미리보기 카드의 사진과 이름은 카카오 서버에 남는다.
3. 사장님이 링크를 직접 열어도 '확인함'으로 찍힌다.
4. 보호자가 링크를 남에게 넘기면 그 사람도 본다.
5. 앱을 거치지 않고 올린 사진의 EXIF 는 서버가 확인하지 않는다.

### 남는 것 — 알고 미룬다

- 기존 `.env`에 `IDENTITY_TOKEN_ENC_KEY`가 있다(인증 프로세스 전용이라 `.env.auth`에 있어야 한다). `.env.example`도 파일을 나누지 않았다. 이 계획 전부터 있던 상태다 — 운영 배포 전에 정리한다.
- `REPORT_LINK_KEY_B64`는 필수다. 없으면 API·인증 프로세스 둘 다 기동하지 않는다. `generate_dev_env.py`는 `.env`가 있으면 아무것도 하지 않으므로 기존 개발 환경은 한 줄을 직접 더한다(명령은 `README.md`). 키가 base64 가 아니면 `RuntimeError`가 아니라 `binascii.Error`로 멈춘다.
- 개발 DB 에 마이그레이션 0010 을 올려야 새 경로가 동작한다(compose 의 backend 가 기동할 때 올린다).
- 돌려 보지 않은 경합: 되돌리는 동안 온 보내기(R9 의 반대 방향), 익명화와 보내기, 끊기를 동시에 두 번, 열람 신호의 동시 요청(두 세션). 모두 같은 잠금이나 조건부 UPDATE 에 기대므로 성립할 것이나 테스트는 없다.
- 기록 삭제가 링크를 잠금 뒤에 읽는지는 경합 통합 테스트 하나만 잡는다.
- `GET /v1/shops/myself`·`GET /v1/auth/myself`가 로그인 없이 열려 있다(기존 동작, 목록에 고정했다). 의도한 것인지 확인하지 않았다.
- 테스트 파일을 골라 돌릴 때 `tests/test_hub_port_binding.py`를 통합 파일 사이에 두면 `fixture 'wired' not found`다(전체 실행에는 없다, 원인 미조사).
- 확인하지 못한 것: 실제 AWS S3 에서의 내려받기 서명, 브라우저의 실제 저장, 영상의 내려받기·공개 조회, 메뉴 항목이 있는 기록의 배선, 게이트웨이(Caddy) 접속 기록, 실제 Redis 장애와 연결 시간 초과 동안의 대기.
- 운영에서 OpenAPI 문서(`/docs`)에 공개 경로가 보이는지 정하지 않았다.
- 하루 목록·피드·상세·전이는 질의가 하나씩 늘었다. 실행 계획과 시간은 재지 않았다. `visit_reports.visit_id`에는 부분 유일 색인만 있다 — 끊은 줄까지 방문으로 찾는 질의가 생기면 색인을 더한다.
- 두 사장이 동시에 설정을 바꾸면 늦은 쪽이 덮는다.
- 미룬 것(설계 10절): 알림톡 자동 발송(⑥), 보호자 로그인과 지난 알림장 모아 보기(⑦), CloudFront 서명 URL, 서버 측 EXIF 검증, 실제 Vercel 배포와 도메인 리다이렉트, 링크 키 교체 절차, 랜딩 페이지·알림장 다국어·만족도 버튼.
- 웹(⑤-2)이 지킬 것: `X-Report-Client-IP`에는 플랫폼이 확인한 주소를 넣는다. 요청에 실려 온 `X-Forwarded-For`의 첫 값을 그대로 넘기면 비밀값이 맞아도 횟수 제한을 피할 수 있다.
- `REPORT_WEB_SECRET`은 운영에서 꼭 정한다. 비어 있으면 모든 보호자가 연결 주소 하나로 세어져 분당 60회를 나눠 쓴다. 기동 때 강제하지는 않는다(웹이 아직 없다) — ⑤-2 에서 다시 정한다.
- 인증 프로세스도 `REPORT_LINK_KEY_B64`를 읽는다(`core/config.py`를 함께 쓴다). 설계 5절은 API 프로세스의 비밀값이라고 했다 — 운영 배포 때 설정을 나눌지 정한다.
- `core/config.py`가 키를 느슨하게 푼다(`b64decode`의 `validate` 없음) — 글자가 섞인 키가 조용히 다른 키가 될 수 있다.
- `core/redis.py`의 클라이언트에 소켓 타임아웃이 없다 — Redis 가 응답 없이 멈추면 통과가 아니라 공개 요청이 매달린다.
- 열람 기록의 UPDATE 에 살아 있음 조건이 없다 — 끊기와 열람 신호가 겹치면 끊긴 줄에 시각이 적힐 수 있다(새 링크는 다른 줄이라 보이는 해는 없다).
- 보내기 인터랙터가 지금 시각을 잠금 앞에서 읽는다(끊기는 뒤에서 읽는다).
- `Visit.has_live_report`의 기본값은 False 다 — `transition()`을 부르는 경로가 새로 생기면 잠근 뒤 이 값을 채워야 한다(지금 부르는 곳은 전이 인터랙터 하나).
- `visit_reports.visit_id`에는 부분 유일 색인뿐이다 — 방문을 지우는 경로가 생기면 전체 색인을 검토한다.
- `revoke_for_customer`는 기간이 지난 줄도 끊는다(설계 7.4 의 "살아 있는 링크"보다 넓다).
- 계획서의 diff 는 `git apply`로 적용되지 않는다(마크다운에 실린 diff) — 덩어리마다 손으로 옮겼고 참조 브랜치와 글자 단위로 대조했다.
- 실행 환경의 권한 판정이 보안 검사를 약하게 만드는 변이 몇 개의 실행을 거부했다(토큰 서명 비교 우회, 설정 PUT 의 권한 완화, 방문 조회의 매장 조건 제거, 보내기·끊기의 잠금 제거와 라우터 가드 완화, 공개 조회의 살아 있음 검사 제거). 우회하지 않았다. 같은 변이는 참조 구현에서 모두 테스트가 잡았고, 작업 검토가 코드를 읽어 판별력을 확인했다.

### ⑤-2 웹·⑤-3 앱이 기댈 API 계약

**경로.** 새 경로 일곱과 칸이 늘어난 기존 경로 셋이다. 오류가 더해진 기존 경로가 둘 있다.

| 경로 | 권한 | 응답 |
|---|---|---|
| `GET /v1/shops/{shop_id}/report-settings` | 멤버 | 200 설정 |
| `PUT /v1/shops/{shop_id}/report-settings` | `shop:update` | 200 설정 |
| `GET /v1/shops/{shop_id}/visits/{visit_id}/report` | 멤버 | 200 미리보기 |
| `PUT /v1/shops/{shop_id}/visits/{visit_id}/report` | `record:write` | 200 미리보기(링크 포함) |
| `DELETE /v1/shops/{shop_id}/visits/{visit_id}/report` | `record:write` | 204 |
| `GET /v1/public/report` | 없음(헤더 토큰) | 200 공개 알림장 |
| `POST /v1/public/report/viewed` | 없음(헤더 토큰) | 204 |
| `GET /v1/shops/{shop_id}/visits/{visit_id}` | 멤버 | 기존 + `report`(링크 상태, 늘 있다) |
| `GET /v1/shops/{shop_id}/visits?date=` | 멤버 | 기존 + `items[].report_sent` |
| `GET /v1/shops/{shop_id}/visits/feed` | 멤버 | 기존 + `items[].report_sent` |
| `POST /v1/shops/{shop_id}/visits/transitions`(`revert`) | 기존 | 기존 + 409 `VISIT_REPORT_SENT` |
| `DELETE /v1/shops/{shop_id}/visits/{visit_id}/record` | 기존 | 기존 + 409 `VISIT_REPORT_SENT` |

**본문.**

- 설정(요청·응답 같다): `{link_days: 7 | 30 | null, show_menus, show_shop_info, show_weight, show_amount}`. 요청은 다섯 칸 모두 필수이고 불리언은 엄격하다(`"true"`·`1`은 422).
- 보내기 요청: `{hidden_media_ids: [int]}`. 필수 칸이고 33개까지다. 뺄 것이 없으면 빈 배열.
- 미리보기(GET·PUT 응답): `{report, link, settings}`.
  - `report`: `pet_name`, `visit_date`, `care_note`, `media[]`(`media_id`, `kind`, `phase`, `hidden`, `width`, `height`, `duration_seconds`, `display_url`, `thumb_url`, `download_url`), `cover`(`url`, `width`, `height`), `menus[]`(`name`, `amount`), `total_amount`, `weight_kg`, `shop`(`name`, `phone`, `address`). 뺀 미디어도 `hidden: true`로 함께 온다. 끈 항목은 `null`이다(공개 응답과 다르다). 대표는 빼지 않은 것 가운데서 고른다.
  - `link`(방문 상세의 `report`와 같다): `{status: "none" | "live", url, expires_at, first_viewed_at, created_at}`. `none`이면 나머지는 null. 시각은 매장 시간대. `url`은 `{REPORT_WEB_BASE_URL}/r/{토큰}`이다.
  - `settings`: 지금 매장 설정.
- 공개 알림장: `pet_name`, `visit_date`, `care_note`, `media[]`(`kind`, `phase`, `width`, `height`, `duration_seconds`, `display_url`, `thumb_url`, `download_url`), `cover`, `expires_at`은 늘 있다. `menus`·`menus[].amount`·`total_amount`·`weight_kg`·`shop`은 매장이 켰을 때만 **칸이 있다.** 켰지만 값이 없으면 `null`이다. `media`는 후 → 전, 그 안에서 순서대로이고 뺀 것은 없다. 사진의 `display_url`은 표시용, 영상은 원본이다. `menus`는 예약 메뉴가 아니라 기록의 항목이다. ID 칸은 없다.
- 오류 본문은 `{code, message}`뿐이다.

**오류 코드.**

| 코드 | 상태 | 언제 |
|---|---|---|
| `VISIT_NOT_FOUND` | 404 | 없는 방문, 다른 매장의 방문 |
| `CUSTOMER_NOT_FOUND` | 404 | 익명화한 고객의 방문에 보내기(가족 잠금) |
| `VISIT_NOT_COMPLETED` | 409 | 완료가 아닌 방문에 보내기 |
| `VISIT_NO_RECORD_YET` | 409 | 기록이 없는 방문의 미리보기·보내기 |
| `VALIDATION_ERROR` | 422 | `hidden_media_ids`에 이 기록의 것이 아닌 ID·중복·33개 초과·범위 밖 숫자, 설정의 허용 밖 기간·불리언이 아닌 값·빠진 칸 |
| `REPORT_EMPTY` | 422 | 새 링크를 만드는데 빼지 않은 미디어도 케어 메모도 없다 |
| `REPORT_NOT_FOUND` | 404 | 끊을 살아 있는 링크가 없다. 공개: 토큰이 없거나 우리가 만든 것이 아니다 |
| `REPORT_CLOSED` | 410 | 공개: 끊음, 기간 지남, 매장 정지·폐업, 익명화, 기록 없음 |
| `TOO_MANY_ATTEMPTS` | 429 | 공개: 접속 주소별 분당 60회 초과, 또는 서명이 틀린 요청의 실패가 10분에 20회 |
| `VISIT_REPORT_SENT` | 409 | 살아 있는 링크가 있는 방문의 되돌리기·기록 삭제 |
| `PERMISSION_DENIED` | 403 | 직원의 설정 변경, `record:write` 없는 보내기·끊기 |

보내기의 오류 순서는 `VISIT_NOT_FOUND` → 가족 잠금의 오류 → `VISIT_NOT_COMPLETED` → `VISIT_NO_RECORD_YET` → `VALIDATION_ERROR` → `REPORT_EMPTY`다.

**공개 조회의 판정 순서.** 분당 한도(429) → 서명 확인 → (틀리면) 실패가 찼으면 429, 아니면 세고 404 → (맞으면) 링크 찾기(없으면 세고 404) → 살아 있음(410) → 매장(410) → 기록(410). 열람 신호는 기록을 보지 않는 것만 다르다. 열람 신호는 한 번 남으면 바뀌지 않고 닫힌 링크에는 남기지 않는다.

**헤더.**

| 헤더 | 방향 | 뜻 |
|---|---|---|
| `X-Report-Token` | 요청 | 토큰 43글자. 없으면 404 |
| `X-Report-Web-Secret` | 요청 | 웹 서버와 나눈 비밀값. 맞을 때만 아래 주소를 믿는다 |
| `X-Report-Client-IP` | 요청 | 보호자의 접속 주소. 횟수를 이 주소로 센다 |
| `Cache-Control: private, no-store`, `X-Robots-Tag: noindex, nofollow` | 응답 | 200·204 에만 있다. 오류 응답에는 웹이 단다 |

**설정 상수.**

| 이름 | 필수 | 뜻 |
|---|---|---|
| `REPORT_LINK_KEY_B64` | 필수 | 토큰 서명 키. 32바이트 이상을 base64 로 |
| `REPORT_WEB_BASE_URL` | 기본 `http://127.0.0.1:3010` | 보호자 웹의 주소. 끝의 `/`는 뗀다 |
| `REPORT_WEB_SECRET` | 기본 빈 값 | 웹 서버와 나누는 비밀값. 비어 있으면 웹 서버가 알려 준 주소를 믿지 않는다 |

### 흐름 확인 (2026-09-28)

`backend/scripts/check_report_flow.sh`를 개발 스택의 게이트웨이(Caddy) 경유로 돌려 34줄 모두 통과했다(첫 실행). 판별력: 5단계("내부 메모 표식이 없다")의 기대를 `True`로 뒤집으면 그 줄에서 멈추는지 확인했다 — 확인했다(종료 코드 1). 라우트 표는 62줄에서 69줄이 됐다(늘어난 경로 정확히 일곱, 없어지거나 바뀐 줄 없음).
