# 015 — ⑫ 보호자 기록 모아 보기 · 가족 · 리뷰 주소

2026-11-16. 설계 `docs/superpowers/specs/2026-11-16-guardian-archive-design.md`(8절의 답이 앞선다), 계획 `docs/superpowers/plans/2026-11-16-guardian-12-backend.md`. 마이그레이션 0024.

## 사용자가 정한 것 (2026-11-16)

- **가족 수는 매장이 정한다** — 기본 3, 0~10(0 이면 초대가 없다). 초대의 24시간·한 번만은 고정이다(답은 수에 대한 것이었다 — 기간·횟수도 매장이 정하게 하려면 사용자가 말한다).
- **리뷰 줄은 알림장마다 뺄 수 있다** — 보내기 전 미리보기의 스위치(기본 넣음).

## ⑫-1 백엔드에서 정한 것

- 리뷰 주소·문구는 `visit_shop_settings` 두 칸, 알림장마다의 빼기는 `visit_reports.show_review`. 공개·보호자 한 장은 주소가 없거나 뺐으면 칸째 없다(끈 항목과 같은 규칙). 문구가 비면 서버가 기본 문구를 채워 보낸다 — 웹은 기본 문구를 따로 갖지 않는다.
- 가족 연결은 `guardian_links` 의 줄이다(`parent_link_id`). 새 표 `guardian_family_invites`(가족 초대 행 — 매장 초대의 "초대 행"과 이름을 가른다)·`guardian_shop_settings`(가족 수 — `guardian` 스포크가 가진다, `visit` 의 알림장 설정을 import 하지 않는다).
- 모아 보기·몸무게는 `visit` 의 보호자용 읽기 옆이다. `guardian` 스포크는 여전히 고객·반려동물을 읽지 않는다.

### 실행하면서 정한 것 (Ruling)

- **설정 PUT 의 리뷰 두 칸은 빠지면 지금 값을 둔다** — 설계는 "둘 다 필수"였다. ⑫-1 을 병합하고 ⑫-3(앱)이 따라오기 전까지 지금 앱이 다섯 칸만 보내도 지워지지 않게. 틀리면: 앱이 칸을 보내지 않는 실수를 서버가 잡지 못한다.
- **모아 보기의 쪽 표시는 (방문 시각, 방문 ID, 전후, 순서)** — 설계의 "(방문 날짜, 미디어 ID)" 대신, 한 장과 같은 순서(후 → 전, 순서대로)를 지키려고. 틀리면: 커서 모양만 바뀐다(불투명한 글자다).
- **정지·폐업한 매장의 모아 보기·몸무게는 빈 목록이다**(404 가 아니다) — 지난 알림장 목록과 같은 동작. 틀리면: 웹이 빈 화면과 닫힘을 가르지 못한다.
- 받은 적 없는 아이의 몸무게는 404 `REPORT_NOT_FOUND`(visit 의 기존 코드).
- 가족 잇기에서 **기본 보호자 자신이거나 이미 그 가족이면 초대를 쓰지 않고 200** — 같은 사람이 초대 주소를 다시 눌러도 "끝났대"가 뜨지 않게. 쓴 초대라도 이미 가족이면 200 이다.
- 가족 목록을 읽으면(GET) 새 줄의 `seen_by_primary_at` 이 찬다 — 읽기가 쓴다.

### ⑫-1 — 최종 검토에서 고친 것

- 리뷰 주소의 호스트에 대괄호가 짝이 안 맞으면(`https://naver.me]`) `urlsplit` 이 `ValueError` 를 던져 **500** 이었다 → 422. 같은 검사에서 숫자가 아닌 포트, 눈에 안 보이는 문자(제어·형식·방향 뒤집기·줄 나눔 — 유니코드 범주 Cc·Cf·Zl·Zp)도 주소·문구 둘 다 422 로 막는다. `HTTPS://` 는 받되 스킴을 소문자로 바꿔 저장한다(웹이 다시 볼 때 어긋나지 않게).
- 계획에 있던 겹침 테스트를 더했다 — 모두 끊기 vs 잇기, 기본의 끊기 vs 가족의 스스로 끊기(각 세 번), 탈퇴 vs 잇기, **다른 매장의 가족이기도 한 계정의 탈퇴**(그 가족 줄만 끝나고 그 매장의 기본·다른 가족은 그대로), 한 방문의 후·전 사이에 걸린 쪽, 정지한 매장의 빈 목록. 코드는 맞았다 — 회귀를 잡는 장치다.

### ⑫-1 — 남는 것 (미룬 Minor)

- 가족 목록을 읽을 때 SELECT 와 "봤음" UPDATE 사이에 이어진 줄도 봤음이 된다(밀리초의 틈) — 새 가족 알림 한 번을 놓칠 수 있다. 보여 준 줄의 ID 로 범위를 묶으면 된다.
- 끝내기 유스케이스의 `invites` 인자가 선택이다 — 새 진입점이 빠뜨리면 가족이 함께 끝나지 않는다(지금 조립은 셋 다 넘긴다). `resolve` 가 가족 줄의 부모가 살아 있는지 보지 않는다.
- 설정 PUT 에서 빠진 칸을 지킬 때 잠그지 않고 읽어 일곱 칸을 다 쓴다 — 예전 앱과 새 앱이 동시에 저장하면 리뷰 주소가 덮일 수 있다.
- 이미 가족인 계정이 받은 알림장 링크로 잇기를 누르면 409 다(가족 잇기는 같은 상황에서 200).
- `describe_report(show_review=True)` 의 기본값, 모아 보기의 `years` 는 URL 준비 여부를 보지 않는다, 다시 보내기 테스트가 개수만 본다, 스키마 테스트가 `uq_guardian_links_live` 의 새 조건을 보지 않는다, import 순서.

## ⑫-2 웹에서 정한 것

계획 `docs/superpowers/plans/2026-11-16-guardian-12-web.md`. 화면은 설계 3.1~3.6·5.3 의 글자 그대로다.

- **리뷰 줄**은 매장 카드 아래·잇기 버튼 위의 링크 하나다(`components/ReviewLine.tsx`). https 가 아니면 그리지 않고(`safeReviewUrl`), 새 창(`target="_blank"`)·`rel="noopener noreferrer nofollow"` — 응답 헤더 `Referrer-Policy: no-referrer` 와 함께 알림장 주소(토큰)를 리뷰 사이트에 넘기지 않는다. 문구는 백엔드가 채워 준 것을 그대로 쓴다.
- **사진 모아 보기**(`/me/[linkId]/photos?pet=&year=&phase=&cursor=`)는 지난 알림장 목록과 같은 규칙이다 — 다음 쪽은 넘어가는 링크(쌓아 붙이지 않는다), 다시 로그인하면 거르기는 지키고 쪽 표시는 버린다, 모양이 틀린 인자는 없는 것으로 친다. 몸무게는 아이를 골랐을 때만 읽고, 읽지 못하면 그 구역만 없다(본문은 그린다).
- **크게 보기의 확대**: 두 번 누르면 2.5배, 손가락 둘로 4배까지. 확대한 채로는 넘기기 대신 끌어 옮긴다. 아래에 그 날의 알림장으로 가는 링크.

### 실행하면서 정한 것 (Ruling)

- **모두 저장의 일부 실패 표시(`N개를 받지 못했어요` + [다시 받기])는 공유 시트 경로에서만 나온다** — 차례 내려받기는 링크를 누르는 것이라 브라우저가 실패를 알려 주지 않는다. 공유 시트는 사진만·열 장 이하일 때만(파일을 메모리에 올린다). 틀리면: 내려받기 경로의 실패는 보호자가 파일을 세어 봐야 안다.
- **보던 자리는 목록을 열 때 그 경로(경로와 질의뿐)를 `sessionStorage` 의 `cn-list:<연결>` 에 적고, 한 장의 돌아가기가 그 경로의 `#r<알림장>` 으로 간다** — 같은 연결의 목록 모양만 따라간다. 스크립트가 없거나 저장이 막히면 첫 쪽이다. 사진에서 왔으면 글자가 `사진 모아 보기` 다. 틀리면: 다른 탭에서 연 목록과 섞일 수 있다(탭마다 따로라 드물다).
- **초대 만들기 경로(`POST /me/[linkId]/family-invite`)는 주소 전체가 아니라 경로(`/j/<코드>`)만 JSON 으로 준다** — 브라우저가 자기 origin 을 붙인다. 웹 서버가 자기 주소를 설정으로 가질 필요가 없다. 응답은 `no-store`, 세션이 끝났으면 세션 쿠키를 지우고 401 → 버튼이 로그인으로 보낸다. 틀리면: 프록시 뒤에서 origin 이 다르면 주소가 틀린다(Vercel 뒤에서는 같다).
- **초대 받은 화면(`/j/<코드>`)은 백엔드를 부르지 않는다** — 코드의 모양만 보고 아니면 404, 미리보기(og) 정보가 없다. 연 것만으로는 어느 매장·아이의 초대인지 드러나지 않는다. 잇기는 알림장의 잇기와 같은 방식이다(세션이 없으면 봉한 쿠키 `cn_join` 10분 → 로그인).
- **로그인은 `cn_claim`·`cn_join` 둘 다 꺼내 쓴다** — 남겨 두면 다음 로그인에 엉뚱하게 쓰인다. 알림장 잇기가 409 면 `?notice=taken` 이 앞서고, 가족 잇기가 안 되면(없음·씀·가득·잦음) `?notice=invite` 한 가지 안내다. 로그아웃은 `cn_join` 도 지운다.
- **가족 끊기는 확인 창 없이 폼 하나다**(설계 3.5 의 [끊기]·[가족 모두 끊기]) — 끊긴 가족은 새 초대로 다시 이을 수 있다. 틀리면: 잘못 누른 기본 보호자가 초대를 다시 보내야 한다.

## API 계약 (웹·앱이 기댄다)

- 알림장 설정 `GET` 에 `review_url`·`review_text`(null 이면 기본 문구)·`review_text_default`, `PUT` 에 선택 `review_url`·`review_text`(빠지면 지금 값, null 이면 지움). 422 `VALIDATION_ERROR`.
- 보내기 `PUT …/visits/{id}/report` 에 선택 `show_review`(기본 true). 미리보기·보내기 응답의 `report.review_url`·`review_text`(주소가 있으면 — 뺐어도), `link.show_review`(링크가 없으면 null).
- 공개·보호자 한 장 `PublicReportSchema` 에 `review_url`·`review_text` — 주소가 있고 그 알림장이 빼지 않았을 때만 칸이 있다.
- `GET /v1/me/guardian/links/{id}/media?pet_id=&year=&phase=after|before&cursor=` → `{items: [{report_id, visit_date, kind, phase, width, height, duration_seconds, display_url, thumb_url, download_url}], next_cursor, years}` — 깨진 커서·모르는 phase 422.
- `GET /v1/me/guardian/links/{id}/pets/{pet_id}/weights` → `{items: [{visit_date, weight_kg}]}`(오래된 것부터 24개, 몸무게를 끄면 빈 목록, 받은 적 없는 아이 404).
- `POST /v1/me/guardian/links/{id}/family-invites` → 201 `{code, expires_at}`(`Cache-Control: no-store`) / 404(가족·남의 연결) / 409 `GUARDIAN_FAMILY_FULL` / 429.
- `POST /v1/me/guardian/family-links`(헤더 `X-Family-Invite`) → 201·200 `{link_id}` / 404 `GUARDIAN_INVITE_NOT_FOUND` / 409 / 429.
- `GET /v1/me/guardian/links/{id}/family` → `{items: [{family_id, linked_at, unseen}]}`(기본 연결만). `DELETE …/family/{family_id}`·`DELETE …/family` → 204.
- `GET /v1/me/guardian/links` 의 항목에 `role`(primary·family)·`family_count`·`family_max`.
- 매장 `GET …/customers/{id}/guardian-link` 에 `family_count`. `DELETE` 는 가족까지 끊는다.
- `GET·PUT /v1/shops/{id}/guardian-settings` → `{family_max, defaults: {family_max}}`, PUT `{family_max}`(0~10, 사장).
