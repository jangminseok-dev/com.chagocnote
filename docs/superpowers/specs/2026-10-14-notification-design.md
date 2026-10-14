# 차곡노트 — ⑥ 알림톡 자동 발송 설계

- 작성일: 2026-10-14
- 상태: 승인(2026-10-14). 계획서 ⑥-1(백엔드)은 이 문서 뒤에 쓴다. ⑥-2(앱)는 ⑥-1 구현 뒤 실제 코드를 보고 쓴다.
- 범위: 백엔드(새 스포크 `notification`, 허브 이벤트 포트, `visit` 의 이벤트 발행), 앱(알림톡 설정·방문 상세 발송 내역·알림장 보내기 흐름). 웹(`web/`)은 바꾸지 않는다. 보호자 회원(⑦)·매출 통계(⑧)·홍보 메시지(⑩)는 하지 않는다.
- 앞선 문서: `docs/superpowers/specs/2026-09-20-foundation-design.md` 9절(스포크 구성·도메인 이벤트·사용량 기록), `docs/superpowers/specs/2026-09-28-report-design.md` 14절(알림장 링크를 알림톡에 싣는다), `_docs/architecture.md`(Observer·Strategy 자리), `_docs/decisions/008-report.md`(운영 배포 전 설정 분리).
- 외부 자료(2026-10-14 조사): 솔라피 가격 https://solapi.com/pricing · 구간 단가 https://solapi.com/guides/tiered-pricing · 채널 연동 토큰 https://docs.solapi.com/api-reference/kakao/requestplusfriendtoken · 채널 추가 https://docs.solapi.com/api-reference/kakao/putplusfriend · 발신번호 https://solapi.com/developers/api/senderid · 단일 발송 https://docs.solapi.com/api-reference/messages/sendsimplemessage · 상태 코드 https://solapi.com/guides/message-status-codes · 카카오 알림톡 심사 가이드 https://kakaobusiness.gitbook.io/main/ad/infotalk/audit

---

## 1. 목표

매장이 카카오톡 채널을 한 번 연동하면, 예약·일정 변경·취소·알림장·재방문 안내가 매장 채널 이름으로 보호자에게 알림톡으로 자동으로 간다. 사장님은 설정에서 종류를 켜고 끄고, 방문 상세에서 무엇이 언제 갔는지 본다.

지금 코드에는 외부 발송 어댑터, 시각에 맞춰 스스로 도는 장치, 허브 이벤트 포트, 매장별 사용량 기록이 없다. `notification` 스포크는 아키텍처 문서에 자리만 예정되어 있다.

이 문서가 끝나면:

1. 매장이 앱 안에서 카카오톡 채널을 연동하고(운영자 개입 없음) 템플릿이 자동으로 등록·심사된다.
2. 예약 접수·전날 리마인드·예약 변경·취소·알림장·다음 예약 제안 여섯 종류가 규칙대로 큐에 쌓이고 디스패처가 보낸다.
3. 보내기 전 검사(야간·쿨다운·마케팅 동의·익명화·앞으로의 예약·하루 상한)와 실패 처리(자동 재시도·원인별 버튼·문자 대체)가 있다.
4. 방문 상세에 발송 내역이 보이고, 알림장 보내기는 알림톡이 먼저 가고 공유 시트는 보조가 된다.
5. 발송 기록이 매장별로 남아 사용량 집계의 바탕이 된다. 전화번호·이름은 우리 표와 로그에 남지 않는다.

## 2. 사용자와 정한 것 (2026-10-14)

| 주제 | 결정 |
|---|---|
| 메시지 종류 | 예약 접수·전날 리마인드·알림장·예약 변경·취소·다음 예약 제안 전부 만든다. 다음 예약 제안은 기본 꺼짐이고 켤 때 템플릿을 등록·심사한다 |
| 발송 업체 | 솔라피. 차곡노트 계정 하나, 매장 채널(발신프로필)을 그 아래 연동. 온보딩은 앱 안에서 API 로 끝낸다. 포트 뒤에 두어 나중에 NHN Cloud 로 바꿀 수 있다 |
| 발신자 | 매장의 카카오톡 채널. 차곡노트 채널 하나로 전부 보내는 방식은 심사 기준(수신자가 신청한 곳의 프로필에서 발송)에 걸려 기각 |
| 템플릿 | 차곡노트가 문안을 정하고 매장 채널마다 자동 등록·심사. 그룹 템플릿은 업체명 고정 제약과 그룹 추가 3~4일 때문에 기각. 매장이 문안을 고르는 안은 과해서 기각 |
| 알림장 보내기 | 연동된 매장은 [보내기]가 알림톡 발송이고 공유 시트는 [다시 공유]로 남는다. 실패하면 스낵바 뒤 공유 시트. 보낼 때마다 고르는 안, 공유 시트를 없애는 안은 기각 |
| 발송 시점 | 접수·변경·취소는 즉시(시간 제한 없음). 리마인드는 전날 매장 설정 시각(기본 18:00, 08:00~21:00 안). 등록 시각이 이미 리마인드 시각을 지났으면 리마인드는 없다(접수 문안이 겸한다). 다음 예약 제안은 완료일 + N주 되는 날 리마인드 시각 |
| 야간 | 리마인드·다음 예약 제안은 매장 시간대로 08:00~21:00 밖이면 다음 날 08:00 으로 미룬다. 미룬 시각이 예약 1시간 전을 넘기면 보내지 않는다. 법적 제한(정보통신망법 21~08시)은 광고성에만 있고 알림톡은 정보성이라 해당 없지만 보호자 반발을 피한다 |
| 다음 예약 제안 | 고객에게 앞으로의 예약이 있으면 안 보냄. 고객 단위 쿨다운(기본 30일). 고객의 마케팅 수신 동의가 있을 때만(실질이 재방문 유도라 법 쪽 안전). 심사 반려 가능성이 있어 기본 꺼짐 |
| 취소 안내 | 사유가 `shop_reason` 일 때만. `customer_request` 는 보내지 않는다 |
| 문자 대체 | 기본 꺼짐. 매장이 설정에서 켜고 발신번호 본인인증을 마쳐야 한다. 종류마다 문자용 짧은 문안을 따로 두고 90바이트를 넘으면 LMS |
| 재발송 | 일시 실패는 자동 3회 뒤 [다시 보내기]. 영구 실패(카카오톡 미사용·채널 차단·번호 오류)는 [다른 방법으로 보내기] → 공유 시트에 문안 |
| 발송 내역 | 방문 상세의 알림톡 줄까지. 매장 전체 목록·월별 집계·과금은 ⑧ |
| 잔액 | 차곡노트 계정 하나라 매장이 볼 것은 없다. 운영자 경고는 로그만 |
| 권한 | 채널 연동·해제·설정·발신번호는 `shop:update`(사장). 재발송은 `reservation:write`(직원 가능). 역할이 `owner`·`staff` 둘뿐이라 "매니저"는 없다 |
| 큐와 실행 | DB 표가 큐, 백엔드 프로세스 안의 디스패처 루프. 별도 워커 프로세스·Redis 큐는 기각(5절) |

### 2.1 비용 (먼저 밝힌다)

| 항목 | 내용 |
|---|---|
| 알림톡 | 솔라피 13원/건(월 1만 건 이상 10원), VAT 별도. NHN Cloud 는 5~7.9원 |
| 문자 대체 | SMS 18원, LMS 45원(솔라피) |
| 매장당 추정 | 월 120방문에 방문마다 2건이면 약 240건, 약 3,100원/월 |
| 무료 한도 | 없음. 충전식 선불. 잔액이 바닥나면 발송이 멈춘다 |
| 카카오 요건 | 매장마다 비즈니스 인증된 카카오톡 채널. 템플릿 심사 영업일 1~3일, 승인 뒤 문구 수정 불가 |
| 유료 전환 지점 | 솔라피 가입·API 연동은 무료. 첫 실제 발송부터 건당 과금 |

## 3. 구조

### 3.1 구성 요소

| 요소 | 위치 | 하는 일 |
|---|---|---|
| 허브 이벤트 | `hub/app/ports/domain_event_port.py`, `hub/app/dtos/visit_events.py` | 발행 포트와 이벤트 DTO. 구현은 같은 프로세스·같은 세션의 동기 버스(`core/observer/`) |
| visit 발행 | 기존 인터랙터 다섯(등록·수정·일정 변경·전이·알림장 보내기) | 끝부분에서 이벤트 한 줄씩 발행 |
| notification 구독자 | `notification/adapter/inbound/observer/visit_event_subscriber.py` | 이벤트를 받아 같은 트랜잭션에서 메시지 줄을 만들거나 취소 |
| notification 디스패처 | `notification/app/services/dispatcher.py` | 시각이 된 줄을 집어 검사하고 게이트웨이로 보내고 결과를 적는다. 템플릿 상태·잔액도 주기적으로 본다 |
| 게이트웨이 | `notification/adapter/outbound/strategy/solapi_gateway.py`, `fake_gateway.py` | 업체 API. 포트는 `notification/app/ports/output/message_gateway_port.py` |
| API | `notification/adapter/inbound/api/v1/` | 설정·온보딩·방문별 내역·재발송 |
| 앱 | `app/lib/features/visit/` | 알림톡 설정 화면, 방문 상세 블록, 알림장 흐름 변화 |

### 3.2 큐와 디스패처

이벤트 구독자가 `notification_messages` 에 줄을 쓴다(즉시 보낼 것은 지금 시각, 리마인드는 계산한 시각). 방문 저장이 롤백되면 메시지 줄도 사라진다. 백엔드 프로세스가 기동할 때 asyncio 작업 하나가 돌며 몇 초마다 "시각이 된 줄"을 `FOR UPDATE SKIP LOCKED` 로 집어 `sending` 으로 바꾸고 커밋한 뒤, 잠금 밖에서 포트를 읽고 업체를 부른다. 인스턴스가 둘이어도 두 번 보내지 않는다. 아키텍처 문서의 "처음엔 같은 프로세스, 나중에 아웃박스"를 처음부터 아웃박스 모양으로 가되 프로세스만 하나인 셈이다.

기각한 안: ① 디스패처만 별도 프로세스(compose `worker`) — 프로세스·컨테이너가 늘고 CI·개발 기동이 복잡해진다. 루프 진입점만 떼면 나중에 갈 수 있다. ② Redis 큐(arq) — 새 의존성이 생기고 하루 뒤 예약된 작업은 결국 DB 에도 적어야 해 상태가 두 군데가 된다.

### 3.3 스포크 경계

- visit 는 이벤트만 발행하고 notification 을 모른다. `main.py` 가 구독자를 꽂는다.
- notification 은 보낼 때 필요한 것을 허브 포트로 읽는다 — 매장 이름·시간대는 `ShopProfilePort.public_profile`, 고객 이름·전화번호·마케팅 동의는 새 메서드 `CustomerDirectoryPort.contact(ctx, customer_id)`(익명화면 None), 반려동물 이름은 `CustomerDirectoryPort.briefs`, 앞으로의 예약 유무는 `VisitLedgerPort.customer_has_upcoming`(이미 있음).
- 기존 `briefs` 는 가린 번호만 주므로 알림톡에 못 쓴다. `contact` 는 notification 만 쓴다.
- 고객 익명화는 이벤트가 없다. 보내는 순간 `contact` 가 None 이면 취소한다.

## 4. 데이터 모델 (3NF, 마이그레이션 0011, 전부 notification 소유)

### 4.1 `notification_channels` — 매장당 한 줄

| 칸 | 뜻 |
|---|---|
| shop_id (PK) | 매장 |
| status | `token_requested` → `linked` → `unlinked` |
| provider, provider_channel_id | `solapi`, 업체가 준 채널(발신프로필) ID |
| linked_at, unlinked_at | 시각 |
| sender_number, sender_number_verified_at | 문자 대체용 발신번호. 인증 전엔 NULL |
| sms_fallback_enabled | 기본 false. CHECK: true 면 `sender_number_verified_at IS NOT NULL` |
| created_at, updated_at | |

연동 중인 채널의 검색 아이디·관리자 번호는 토큰 확인 때만 쓰고 저장하지 않는다.

### 4.2 `notification_settings` — 연동할 때 기본값으로 생김

| 칸 | 기본 |
|---|---|
| shop_id (PK) | |
| confirm_enabled, reminder_enabled, report_enabled, change_enabled | true. `change_enabled` 하나가 `change`·`cancel` 둘을 켠다 |
| next_visit_enabled | false |
| reminder_time | 18:00, CHECK 08:00~21:00 |
| next_visit_after_weeks | NULL = 지난 방문 간격(없으면 4주) |
| next_visit_cooldown_days | 30 |
| created_at, updated_at | |

### 4.3 `notification_templates` — (shop_id, kind) 유일

| 칸 | 뜻 |
|---|---|
| id, shop_id, kind | kind: `confirm` `reminder` `report` `change` `cancel` `next_visit` |
| text_version | 코드에 있는 문안의 판 번호. 문안을 고치면 새 판을 등록하고 승인되면 바꿔 끼운다 |
| provider_template_id | 업체 템플릿 ID |
| status, rejected_reason | `pending` `approved` `rejected` |
| requested_at, decided_at | |

### 4.4 `notification_messages` — 큐이자 발송 기록

| 칸 | 뜻 |
|---|---|
| id, shop_id, visit_id, customer_id, kind | 대상 |
| scheduled_at | 보낼 시각(UTC). 즉시면 만든 시각 |
| status | `scheduled` → `sending` → `accepted` → `sent` / `fallback_sent` / `failed` / `canceled` |
| attempts, next_attempt_at | 자동 재시도 |
| channel_used | `alimtalk` `sms` `lms` — 실제로 나간 길 |
| provider_message_id, error_code, error_kind | 업체 응답. error_kind 는 `transient` / `permanent` |
| variables (JSONB) | 이벤트에서만 알 수 있는 값만 — 알림장 주소, 바뀌기 전 시각 |
| requested_by_member_id | 매장이 [다시 보내기]로 만든 줄이면 멤버 ID, 자동이면 NULL |
| created_at, sent_at, canceled_reason | 취소 이유: `rescheduled` `visit_canceled` `no_show` `setting_off` `channel_unlinked` `too_late` `anonymized` `has_upcoming` `cooldown` `no_consent` `bad_phone` |

색인: 부분 유일 (visit_id, kind) WHERE status IN ('scheduled','sending') — 같은 방문·같은 종류는 대기 줄이 하나. (status, scheduled_at) — 디스패처가 집는 질의. (customer_id, kind, sent_at) — 쿨다운. (shop_id, created_at) — 하루 상한·사용량.

### 4.5 저장하지 않는 것

전화번호·고객 이름·반려동물 이름·매장 이름. 보내는 순간 포트로 읽는다. 그사이 익명화된 고객에게는 안 가고, 매장 이름을 바꾸면 바뀐 이름으로 간다. 발송 기록에 번호가 남지 않는다.

### 4.6 3NF 점검

네 표 모두 키가 아닌 칸이 키에만 의존한다. `channels` 와 `settings` 는 둘 다 shop_id 가 키지만 생명주기(연동 상태 vs 선호)가 달라 나눈다. 사용량은 `messages` 에서 세고 따로 표를 두지 않는다.

## 5. 이벤트와 메시지 규칙

### 5.1 이벤트

`VisitReserved`, `VisitRescheduled`(전·후 시각), `VisitCanceled`(사유), `VisitClosed`(완료·노쇼), `VisitReportIssued`(알림장 주소·기간). 전부 shop_id·visit_id·customer_id·pet_id·starts_at 을 싣는다. 구독자는 발행한 인터랙터와 같은 세션·같은 트랜잭션에서 돈다. 구독자가 던지면 방문 저장도 실패한다(의도 — 둘이 어긋나지 않게).

### 5.2 줄을 만드는 규칙 (구독자, 이벤트 시점)

| 이벤트 | 하는 일 |
|---|---|
| 예약됨 | `confirm` 즉시. `reminder` 를 예약 전날 `reminder_time`(매장 시간대)에. 그 시각이 이미 지났으면 리마인드는 안 만든다 |
| 일정 바뀜 | 대기 중인 `reminder` 취소(`rescheduled`) → 새 시각으로 다시 만든다. `change` 즉시(전·후 시각을 variables 에) |
| 취소됨 | 이 방문의 대기 줄 전부 취소(`visit_canceled`). 사유가 `shop_reason` 이면 `cancel` 즉시. `customer_request` 면 안 보낸다 |
| 완료 | `next_visit` 을 완료일 + N주 되는 날 `reminder_time` 에. N 은 설정값, 없으면 지난 방문 간격(완료된 직전 방문과의 날짜 차를 주 단위로 반올림), 그것도 없으면 4주 |
| 노쇼 | 대기 줄 전부 취소(`no_show`) |
| 알림장 발급 | `report` 즉시, variables 에 주소와 기간 안내 |

공통: 채널이 `linked` 가 아니거나 설정이 꺼져 있거나 템플릿이 `approved` 가 아니면 줄을 만들지 않는다. 자동 경로는 (visit, kind) 에 `sent`/`fallback_sent` 줄이 이미 있으면 만들지 않는다. [다시 보내기]는 새 줄을 즉시로 만들고 `requested_by_member_id` 를 적는다.

### 5.3 보내는 규칙 (디스패처, 발송 시점)

1. 몇 초마다 `scheduled_at <= now` 인 `scheduled` 줄을 `SKIP LOCKED` 로 집어 `sending` 으로 바꾸고 커밋한다. 같은 프로세스에서 줄이 만들어지면 루프를 바로 깨워 즉시 메시지는 1~2초 안에 나간다.
2. 잠금을 놓은 뒤 포트로 읽는다 — 매장 프로필, 고객 `contact`, 반려동물 이름.
3. 보내기 전 검사. 하나라도 걸리면 `canceled` 에 이유를 적는다.
   - 고객이 익명화됐거나(`anonymized`) 번호가 휴대폰 형식이 아님(`bad_phone`).
   - `reminder`·`next_visit`: 매장 시간대로 08:00~21:00 밖이면 다음 날 08:00 으로 미룸(`scheduled` 복귀). 미룬 시각이 예약 1시간 전을 넘기면 `too_late`.
   - `next_visit`: 마케팅 동의 없음(`no_consent`), 앞으로의 예약 있음(`has_upcoming`), 최근 쿨다운 일수 안에 같은 종류를 받음(`cooldown`).
   - 설정이 그사이 꺼졌거나(`setting_off`) 채널이 끊김(`channel_unlinked`).
   - 매장의 오늘 발송이 하루 상한에 닿음 → `scheduled` 에 둔 채 WARNING 로그(취소 아님).
4. 게이트웨이를 부른다. 문자 대체가 켜진 매장은 발신번호와 문자용 문안을 같이 보내고 업체가 알림톡 실패 시 문자로 대체한다. 접수되면 `accepted` 와 업체 메시지 ID.
5. `accepted` 줄의 최종 상태를 처음 1분은 5초마다, 그 뒤 1분마다 조회한다(최대 24시간). 성공 → `sent` 또는 `fallback_sent`(실제 나간 길을 `channel_used` 에). 일시 실패(네트워크·업체 5xx·잔액·시간 초과) → `attempts` 를 올리고 1분·5분·30분 뒤로 `scheduled` 복귀, 3회 뒤 `failed`(transient). 영구 실패(미사용·차단·번호 오류·템플릿 불일치) → 바로 `failed`(permanent).
6. 5분 넘은 `sending` 은 다음 루프가 `scheduled` 로 되돌리고 `attempts` 를 올린다.

### 5.4 시각과 시간대

`scheduled_at` 은 UTC 로 저장하고 "전날 18:00"·"08:00~21:00"은 매장 시간대(`ShopProfile.timezone`, zoneinfo)로 계산한다. 매장이 `reminder_time` 을 바꾸면 설정 저장 인터랙터가 대기 중인 `reminder`·`next_visit` 의 시각을 다시 계산한다. 매장 시간대가 바뀌는 경우는 다시 계산하지 않는다(사실상 없음).

## 6. 솔라피 어댑터·온보딩·템플릿

### 6.1 포트

`MessageGatewayPort` 하나. 업체가 바뀌어도 이 포트만 다시 구현한다.

| 메서드 | 하는 일 |
|---|---|
| request_channel_token(search_id, admin_phone, category_code) | 토큰 신청(관리자 카카오톡으로 6자리) |
| link_channel(search_id, admin_phone, category_code, token) → provider_channel_id | 연동 완료 |
| register_template(provider_channel_id, kind, text_version) → provider_template_id | 등록 + 검수 요청 |
| template_status(provider_template_id) → pending / approved / rejected(사유) | |
| request_sender_verification(phone), confirm_sender_verification(phone, code) | 발신번호 본인인증(SELF-CERT) |
| send(request) → provider_message_id | 알림톡 1건 접수(대체 문자 옵션 포함) |
| message_status(provider_message_id) → pending / sent(channel) / failed(code, kind) | 최종 상태 |
| balance() → KRW | 잔액 |

구현: `solapi_gateway.py`(httpx, HMAC-SHA256 서명 헤더, 타임아웃 10초, 업체 4자리 상태 코드를 `transient`/`permanent` 로 분류하는 표), `fake_gateway.py`(dev·흐름 테스트: 즉시 접수·즉시 성공, 번호 끝자리 규칙으로 영구/일시 실패 흉내, 템플릿은 바로 승인, 토큰은 `000000`). `SOLAPI_API_KEY`·`SOLAPI_API_SECRET` 은 `core/config.py` 에서 읽는다. prod 에서 비어 있으면 API 프로세스 기동 실패, dev 에서는 가짜 어댑터.

발송 결과는 비동기다. 발송 API 는 접수만 돌려주고 카카오톡 미사용·차단 같은 결과는 뒤에 온다. 웹훅은 로그인 없는 경로가 하나 생기므로 첫 판에서는 쓰지 않고 폴링한다.

### 6.2 온보딩 (사장, 앱 설정 화면)

매장이 미리 해 둘 것(앱 안내문): 카카오톡 채널 개설, 비즈니스 인증(며칠), 채널 관리자센터의 "관리자 추가 인증" 끄기.

1. 채널 검색 아이디(@…)·관리자 휴대폰·업종 카테고리 입력 → 토큰 신청 → `token_requested`. 입력값은 저장하지 않고 다음 단계까지 앱이 든다.
2. 관리자 카카오톡으로 온 6자리 입력 → 채널 추가 → `linked`. 같은 요청에서 설정 줄 기본값 생성, 기본 5종(`next_visit` 제외) 템플릿 등록·검수 요청 → `pending`.
3. 디스패처가 10분마다 `pending` 템플릿 상태를 조회해 `approved`/`rejected` 로 갱신하고, 연동된 매장에 빠진 종류(등록 중 실패)가 있으면 다시 등록한다. 승인된 종류부터 발송이 시작된다. 반려되면 설정 화면에 "반려됐어요 · 운영자가 확인 중"으로 보이고 운영자가 문안을 고쳐 새 판으로 재등록한다(`scripts/reregister_templates.py`, 전 매장).
4. 문자 대체는 설정에서 켤 때 발신번호 입력 → 본인인증 번호 확인 → `sender_number_verified_at` → 그때부터 켤 수 있다.
5. 연동 해제 → `unlinked`, 대기 줄 전부 취소(`channel_unlinked`). 다시 연동하면 템플릿도 다시 등록한다.

### 6.3 템플릿 문안 (코드에 고정, 변수만 채움)

카카오 심사는 변수 비중이 큰 문안을 꺼린다. 변경과 취소를 한 문안에 합치지 않고 종류를 여섯으로 둔다. `#{대상}` 은 반려동물이 있으면 이름("두부"), 없으면 고객 이름 뒤에 "님". `#{일시}` 는 "10월 15일(수) 14:00". `#{기간안내}` 는 "11월 2일까지 열려요." 또는 "언제든 열 수 있어요.".

| 종류 | 알림톡 문안 | 문자용(90바이트 안) |
|---|---|---|
| confirm | `[#{매장명}] 예약 접수 안내` / `#{대상}의 예약이 접수되었어요.` / `일시: #{일시}` / `변경·취소는 매장으로 연락해 주세요.` | `[#{매장명}] #{일시} 예약이 접수되었어요.` |
| reminder | `[#{매장명}] 내일 예약 안내` / `#{대상}의 예약이 내일이에요.` / `일시: #{일시}` / `늦거나 못 오시면 미리 연락해 주세요.` | `[#{매장명}] 내일 #{시각} 예약을 잊지 마세요.` |
| change | `[#{매장명}] 예약 변경 안내` / `#{대상}의 예약 일시가 바뀌었어요.` / `변경 전: #{이전일시}` / `변경 후: #{일시}` | `[#{매장명}] 예약이 #{일시}로 바뀌었어요.` |
| cancel | `[#{매장명}] 예약 취소 안내` / `매장 사정으로 #{대상}의 #{일시} 예약이 취소되었어요. 죄송합니다.` / `다시 예약하시려면 매장으로 연락해 주세요.` | `[#{매장명}] #{일시} 예약이 매장 사정으로 취소되었어요.` |
| report | `[#{매장명}] 미용 알림장` / `#{대상}의 오늘 미용 알림장이 도착했어요.` / `#{기간안내}` / 버튼 [알림장 보기] → 링크 | `[#{매장명}] 알림장 #{링크}` (넘치면 LMS) |
| next_visit | `[#{매장명}] 미용 주기 안내` / `#{대상}의 지난 미용이 #{지난일}이었어요.` / `#{간격}주 정도마다 미용하면 좋아요.` / `예약은 매장으로 연락해 주세요.` | `[#{매장명}] #{대상} 미용한 지 #{간격}주가 지났어요.` |

문자용 문안은 보내기 전에 EUC-KR 바이트를 세어 90을 넘으면 LMS 로 보내고 `channel_used` 에 적는다. 문안의 판 번호는 코드에 있고(`text_version`) 문안을 바꾸면 모든 연동 매장에 새 판을 등록·심사한다. 그사이에는 옛 판으로 계속 보낸다. 변수 값은 업체가 글자 그대로 넣으므로 이름에 `#{` 가 있어도 문안이 깨지지 않는다. 변수 길이는 업체 한도 안에서 자른다.

## 7. API (전부 로그인 필요, `/v1/shops` 접두, notification 소유)

visit 스포크의 API 는 바뀌지 않는다(이벤트 발행만 더함).

### 7.1 설정·온보딩 — `shop:update`

| 경로 | 하는 일 |
|---|---|
| GET `/{shop_id}/notification` | 채널 상태(`none`/`token_requested`/`linked`), 설정 전부, 종류별 템플릿 상태(+반려 사유), 발신번호 인증 여부 |
| POST `/{shop_id}/notification/channel/token` | {search_id, admin_phone, category_code} → `token_requested` |
| POST `/{shop_id}/notification/channel` | 위 셋 + {token} → `linked`, 설정 기본값, 템플릿 5종 등록 |
| DELETE `/{shop_id}/notification/channel` | 해제, 대기 줄 전부 취소 |
| PUT `/{shop_id}/notification/settings` | 설정 전체 교체. `next_visit_enabled` 를 처음 켜면 그 템플릿 등록. `reminder_time` 이 바뀌면 대기 중인 시각 재계산. `sms_fallback_enabled` 도 여기서 |
| POST `/{shop_id}/notification/sender/verification` | {phone} → 본인인증 시작 |
| POST `/{shop_id}/notification/sender` | {phone, code} → 인증 완료 |

### 7.2 방문별 발송 내역

| 경로 | 권한 | 하는 일 |
|---|---|---|
| GET `/{shop_id}/visits/{visit_id}/notifications` | 소속 | 그 방문의 줄 목록(최신순). message_id, kind, status, channel_used, scheduled_at, sent_at, error_kind, canceled_reason, `share_text`(실패 줄에만 — 문자용 문안을 변수 채운 글, 알림장이면 주소 포함) |
| POST `/{shop_id}/visits/{visit_id}/notifications/{kind}/resend` | `reservation:write` | 새 줄을 즉시로 만들고 `requested_by_member_id` → 201 {message_id}. 같은 종류가 대기 중이면 409 |
| GET `/{shop_id}/notifications/{message_id}` | 소속 | 줄 하나의 상태(알림장 보내기 직후 폴링용) |

방문 상세 응답(visit 소유)에는 끼워 넣지 않는다. 끼우려면 허브 포트가 하나 더 필요한데 앱이 요청 하나를 더 보내는 쪽이 경계를 덜 건드린다.

### 7.3 오류 코드

| 코드 | 상태 | 때 |
|---|---|---|
| NOTIFICATION_CHANNEL_NOT_LINKED | 409 | 연동 전에 설정·재발송 |
| NOTIFICATION_TOKEN_INVALID | 400 | 6자리 틀림·만료 |
| NOTIFICATION_SENDER_NOT_VERIFIED | 409 | 발신번호 인증 없이 문자 대체 켜기 |
| NOTIFICATION_TEMPLATE_NOT_APPROVED | 409 | 미승인 종류 재발송 |
| NOTIFICATION_ALREADY_PENDING | 409 | 대기 중인데 재발송 |
| NOTIFICATION_RATE_LIMITED | 429 | 토큰·인증번호 요청 초과 |
| NOTIFICATION_PROVIDER_UNAVAILABLE | 502 | 온보딩 요청 중 업체 오류·시간 초과 |

### 7.4 운영자

운영자 API 는 두지 않는다. 디스패처가 하루 한 번 잔액을 조회해 `SOLAPI_BALANCE_WARN_KRW`(기본 30,000) 아래면 WARNING 로그. 반려 템플릿 재등록은 `scripts/reregister_templates.py`.

## 8. 앱

알림톡 화면은 새 기능 폴더가 아니라 `visit` 안에 둔다 — 매장 설정(알림장 설정과 나란히)과 방문 상세에만 붙고, 새 폴더는 import 방향이 하나 더 필요하다. 자리: `visit/screens/settings/notification_settings_screen.dart`, `visit/state/notification_providers.dart`·`notification_commands.dart`, `visit/api/notification_api.dart`·`notification_models.dart`.

### 8.1 알림톡 설정 화면 (설정 목록의 "알림톡")

사장만 바꾸고 직원은 읽기 전용(`isOwnerProvider`). 본문은 `AsyncBody`, 데이터는 GET `/notification` 하나.

연동 전 — 안내 세 줄(채널 개설 → 비즈니스 인증 → "관리자 추가 인증" 끄기)과 입력 세 칸, [인증번호 받기] → 6자리 칸과 [연동하기]. 입력값은 화면 상태에만. 직원에게는 "사장님이 연동할 수 있어요".

연동 후 — 채널 줄("연동됨 · 10월 14일", `···` 에 [연동 해제] — 예정된 알림톡이 모두 취소된다고 확인), 종류별 스위치 다섯(예약 접수 / 전날 리마인드 + 시각 / 예약 변경·취소 / 알림장 / 다음 예약 제안 + N주 + 쿨다운 일수)과 스위치 아래 템플릿 상태 문구("심사 중이에요(보통 1~3일)" · "승인됨" · "반려됐어요 · 운영자가 확인 중"), 문자 대체 스위치(미인증이면 켤 때 발신번호 인증 시트, 단가 안내 한 줄).

저장 버튼 없이 누르면 바로 PUT 전체. 낙관적으로 그리지 않고 다시 읽은 값으로 그리며 보내는 중엔 누름을 받지 않는다. 고르기는 닫을 때 한 번 PUT.

### 8.2 방문 상세

정보 카드에 "알림톡" 블록. 알림장 확인 카드 아래, 최신순, 취소된 줄은 보이지 않는다.

- 예정: "전날 리마인드 · 내일 18:00 예정"
- 보내는 중: "알림장 · 보내는 중"
- 보냄: "예약 접수 · 보냄 · 10월 14일 14:02", 문자 대체면 "문자로 보냄"
- 실패: "리마인드 · 못 보냈어요 · 카카오톡을 쓰지 않는 번호예요" + 일시 실패면 [다시 보내기], 영구 실패면 [다른 방법으로 보내기](`share_text` 를 공유 시트에)

블록은 GET `/visits/{id}/notifications` 를 따로 읽는다. 당겨 새로고침하면 둘 다. 연동 안 된 매장은 블록이 없다. [다시 보내기]는 직원도 누르고, 누르면 "보내는 중"으로 바꿔 몇 초 폴링한다.

### 8.3 알림장 보내기 흐름

`ReportCommands.send` 는 그대로다. 그 뒤 `NotificationCommands.awaitReport(visitId)` 가 GET `/notifications` 에서 `report` 줄을 찾아 1초 간격 최대 10초 폴링한다.

- 줄 없음(미연동·꺼짐·미승인) → 지금처럼 공유 시트.
- `sent`/`fallback_sent` → 미리보기 닫고 "알림톡으로 보냈어요".
- `failed` → "알림톡을 못 보내서 다른 방법으로 보내요" + 공유 시트.
- 10초 지나도 `accepted` → 닫고 "알림톡을 보내는 중이에요". 상세 블록이 나중에 갱신.

폴링 중 진행 표시를 띄우고 뒤로 가기를 막지 않는다. [다시 공유]는 그대로 `report.url` 을 공유 시트에.

### 8.4 나머지

문구는 `l10n/app_strings.dart`, 해요체. 새 플러그인 없음. 모델은 `fromJson` 직접, `NotificationKind`·`NotificationStatus` enum 과 완전 열거 `switch`. 하루 목록·피드·달력은 바꾸지 않는다.

## 9. 오류·보안·경계

### 9.1 개인정보

- 전화번호·이름은 보내는 순간 포트로 읽어 업체에 넘기고 우리 표·로그에 남기지 않는다. 발송 기록은 customer_id 만.
- 업체 콘솔에는 수신번호와 내용이 남는다. 기반 설계의 "스토어 제출 전 필수"에 알림 발송 처리위탁(솔라피·카카오)을 더한다.
- 알림장 주소(토큰 포함)가 `variables` 에 남는다. `visit_reports` 가 이미 public_id 를 갖고 링크를 끊으면 주소가 죽으므로 감수한다. `variables` 는 로그·오류·API 응답에 그대로 싣지 않고 `share_text` 만 만들어 준다.
- 로그에 번호·토큰·주소·인증번호를 찍지 않는다. 업체 응답은 상태 코드와 메시지 ID 만.

### 9.2 비밀값

`SOLAPI_API_KEY`·`SOLAPI_API_SECRET`·`SOLAPI_BALANCE_WARN_KRW`·`NOTIFICATION_DAILY_CAP` 은 `core/config.py` 가 `secret_manager` 로 읽는다. 인증 프로세스도 `core/config.py` 를 읽어 값을 들게 되는데 `REPORT_LINK_KEY` 와 같은 문제라 결정 기록 008 의 "운영 배포 때 설정을 나눈다"에 함께 묶는다.

### 9.3 잠금과 중복

- 구독자는 visit 트랜잭션 안에서 넣는다. 그 시점엔 고객 행·방문 행이 잠겨 있으니 잠금 순서에 "→ 알림 행"을 끝에 더한다(루트 CLAUDE.md).
- 디스패처는 집은 뒤 커밋하고 잠금 밖에서 읽고 부른다.
- HTTP 는 성공했는데 결과 커밋 전에 죽으면 한 번 더 갈 수 있다(at-least-once). 업체에 멱등 키가 없어 막을 수 없고 드물고 13원이라 감수한다. 놓치는 것은 없다.
- 개발의 `--reload` 는 작업 프로세스 하나에서만 루프가 돈다. 테스트에서는 루프를 띄우지 않고 `run_once()` 를 부른다.

### 9.4 비용 사고 방지

- 문자 대체 기본 꺼짐, 발신번호 인증 없이는 못 켬(CHECK).
- 매장별 하루 발송 상한 `NOTIFICATION_DAILY_CAP`(기본 300). 넘으면 `scheduled` 에 둔 채 WARNING.
- 토큰 신청·인증번호 요청은 매장당 시간당 5회(Redis 제한, 공개 알림장 제한기와 같은 방식). 6자리 틀림 5회면 처음부터.
- 잔액 경고 로그.

### 9.5 업체·카카오 장애

온보딩 호출은 요청 안이라 10초 뒤 502. 연동 뒤 템플릿 등록이 중간에 실패하면 채널은 `linked` 로 두고 디스패처의 10분 주기가 빠진 종류를 다시 등록한다. 발송은 요청 밖이라 재시도로 처리된다. `accepted` 뒤 24시간 안에 최종 상태가 안 오면 transient `failed`. 반려된 종류만 멈추고 나머지는 간다.

### 9.6 권한과 범위

설정·채널·발신번호 `shop:update`, 재발송 `reservation:write`, 읽기 소속. 모든 조회·명령은 `ShopContext` 를 첫 인자로 받고 다른 매장의 ID 는 404.

### 9.7 위협 점검표

계획 ⑥-1 은 이 표의 줄마다 막는 코드와 테스트를 작업에 짝짓는다.

| # | 시나리오 | 막는 것 |
|---|---|---|
| N1 | 다른 매장의 visit_id·message_id 로 조회·재발송 | `ShopContext` 로 찾는다 — 404 |
| N2 | 내보내진 멤버가 쥔 토큰으로 재발송 | 소속 확인(기존 가드) |
| N3 | 토큰 신청·인증번호 요청 난사(업체 비용·관리자 괴롭힘) | 매장당 시간당 5회 |
| N4 | 6자리 추측 | 5회 뒤 처음부터 + 업체 쪽 만료 |
| N5 | 재발송을 동시에 두 번 | 부분 유일 색인 — 둘째는 409 |
| N6 | 두 디스패처가 같은 줄을 집는다 | `SKIP LOCKED` |
| N7 | 집은 뒤 죽어 영영 `sending` | 5분 회수 |
| N8 | 익명화 직후 발송 | 발송 시각에 `contact` 가 None → `anonymized` |
| N9 | 마케팅 동의 없는 고객에게 다음 예약 제안 | 발송 시각 검사 `no_consent` |
| N10 | 버그로 대량 생성 → 대량 과금 | 하루 상한, 문자 대체 기본 꺼짐 |
| N11 | 발신번호 없이 문자 대체 켜기 | 409 + DB CHECK |
| N12 | `variables`(주소)가 응답·로그에 샌다 | 응답 스키마에 칸 없음, `share_text` 만, 로그 금지 테스트 |
| N13 | 구독자 예외가 방문 저장을 막는다 | 의도(같은 트랜잭션). 구독자는 업체를 부르지 않아 외부 장애로는 안 막힌다 |
| N14 | 잠금 쥔 채 업체 호출 | 디스패처는 커밋 뒤 호출. 구독자는 호출하지 않음 |
| N15 | 야간에 리마인드 | 발송 시각 검사 + `reminder_time` CHECK |
| N16 | 일정을 바꿨는데 옛 시각 리마인드가 간다 | 이벤트가 대기 줄을 취소하고 다시 만든다 |
| N17 | 취소한 방문의 리마인드가 간다 | 취소·노쇼 이벤트가 대기 줄 취소 |
| N18 | 직원이 설정·채널을 바꾼다 | `shop:update` |

### 9.8 감수하는 것

- 보호자가 알림톡을 거부할 방법은 카카오 채널 차단뿐(알림톡엔 수신거부 체계가 없다). 차단은 영구 실패로 돌아오고 문자 대체가 켜져 있으면 문자로 간다. 문자까지 막는 차단 플래그는 ⑦.
- 발송된 알림톡은 회수할 수 없다. 보낸 직후 예약을 바꾸면 변경 안내가 한 통 더 간다.
- 매장 시간대 변경 시 재계산하지 않는다.
- 업체 콘솔에 남는 수신번호·내용(처리위탁).

## 10. 이번에 하지 않는 것

| 항목 | 때 |
|---|---|
| 발송 결과 웹훅(공개 경로) | 폴링이 부족해지면 |
| 매장 전체 발송 목록·월별 집계·과금 | ⑧ |
| 보호자 차단 플래그, 보호자 측 수신 설정 | ⑦ |
| 직원에게 설정 열기(권한 추가) | 요청 시 |
| 브랜드 메시지·홍보 | ⑩ |
| NHN Cloud 어댑터 | 발송량이 커지면 |
| 운영자 잔액 API | ⑧ |
| 매장 시간대 변경 시 재계산 | 필요 시 |

## 11. 테스트와 검증

### 11.1 백엔드

- 단위(스텁 포트): 5.2 규칙 표 한 줄씩(이벤트 × 설정 × 템플릿 상태 → 생기는 줄·취소되는 줄). 5.3 검사(야간 미룸·`too_late`·쿨다운·마케팅 동의·익명화·앞으로의 예약·하루 상한·재시도 간격·영구/일시 분류·5분 회수). 문자용 문안 바이트와 SMS/LMS 분기. 변수 채우기(`#{대상}`·`#{기간안내}`). 시간대 계산(전날 18:00, 08:00~21:00 경계).
- 가짜 게이트웨이는 포트 ABC 를 상속한 스텁(`notification/tests/helpers/fakes.py`). dev 용 `fake_gateway.py` 와는 별개다.
- 통합: 테넌트 격리(A매장 멤버가 B매장 경로 → 403, 새 스포크의 첫 테스트). 온보딩 흐름(토큰 → 연동 → 템플릿 5종 `pending` → 승인 뒤 발송). 예약 등록 → 같은 트랜잭션에 `confirm`·`reminder` → `run_once` → 가짜 게이트웨이 호출 기록 → `accepted` → 상태 조회 → `sent`. 일정 변경·취소(두 사유)·노쇼·완료·알림장 발급 각각. 롤백 시 줄도 없음. 두 `run_once` 동시 → 한 줄을 한 번만. 재발송 409. 설정 변경 시 재계산. 문자 대체 409 와 CHECK. 토큰 요청 429. `variables` 가 응답에 없음.
- 구조: `.importlinter` 에 `notification` 추가(root_packages·layers containers·independence·framework-isolation·domain-purity), `orm_registry.py` 등록, 라우트 표 전후 비교, `route_inspection`(새 라우트 전부 `get_shop_context` 경유, 공개 경로 없음), `test_hub_port_binding` 에 새 포트 자리(`DomainEventPort`, `contact`) 채워짐, `test_schema_drift`, `test_visit_status_schema` 같은 방식으로 새 CHECK·부분 색인 대조.
- 문서: 마이그레이션 0011, 루트 CLAUDE.md 잠금 순서, `_docs/architecture.md` 패턴 표(`core/observer/`·`notification/adapter/outbound/strategy/` "예정" → 실제), `_docs/harness.md`, 결정 기록 009.

### 11.2 앱

- 위젯·골든: 설정 화면 세 상태(연동 전·심사 중·전부 승인), 발신번호 인증 시트, 방문 상세 블록의 줄 다섯 상태, 직원 읽기 전용.
- 상태 단위: `awaitReport` 결과 셋 + 10초 초과, 설정 PUT 뒤 다시 읽기, 실패 줄의 `share_text` → 가짜 공유 시트.
- 흐름(`integration_test/notification_flow_test.dart`, 시뮬레이터, 백엔드 dev 가짜 게이트웨이): 연동 → 설정 → 예약 등록 → 상세 "예약 접수 · 보냄" → 완료 → 알림장 보내기 → "알림톡으로 보냈어요" → 실패 번호로 [다른 방법으로 보내기] → 공유 시트. iOS·Android 각 한 번.
- `feature_imports_test`·`async_body_usage_test`·`copy_tone_test`·`glass_boundary_test`·`app_router_test`, analyze 0.

### 11.3 실제 환경에서만 확인할 수 있는 것 (알고 미룬다)

1. 솔라피 실계정으로 실제 채널 연동·템플릿 심사·발송·대체 발송·상태 코드. 첫 대상은 Hiss Haus 의 실제 카카오톡 채널(비즈니스 인증 선행). 테스트 발송 비용은 몇백 원.
2. 카카오 심사의 실제 반려 여부(특히 `next_visit`)와 문안 수정 왕복.
3. 업체 API 의 실제 요청·응답 형식 — 참조 구현이 실계정으로 먼저 맞춰 보고 계획서에 고정한다.
4. 실기기에서 공유 시트에 `share_text` 가 그대로 가는지(⑤의 미확인 항목과 묶음).
5. 운영에서 인스턴스가 둘 이상일 때 디스패처 둘의 동작(통합 테스트는 같은 프로세스의 두 세션으로만 본다).

## 12. 구현 계획 나누기

| 계획 | 범위 | 선행 |
|---|---|---|
| ⑥-1 백엔드 | 0011, 허브 이벤트 포트·`contact`, visit 발행 5곳, notification 스포크 전부(구독자·디스패처·솔라피/가짜 게이트웨이·API·스크립트), 구조 계약·문서 | 솔라피 계정 생성(무료, API 키 발급) — 참조 구현 검증용 |
| ⑥-2 앱 | 설정 화면·방문 상세 블록·알림장 흐름 변화·흐름 테스트 | ⑥-1 병합 |

⑥-2 계획서는 ⑥-1 구현 뒤 실제 코드를 보고 쓴다. 각 계획은 참조 트리에서 먼저 검증하고 변이 검사까지 돌린다. 작업별 검토는 9.7 의 표를 기준으로 한다.

## 13. 이후 서브 프로젝트로 넘기는 것

- **⑦ 보호자 회원**: 보호자 측 수신 설정·차단 플래그. 알림톡 버튼 링크가 로그인 진입점을 겸할 수 있다.
- **⑧ 매출 통계**: `notification_messages` 에서 매장별 월 건수·채널별 비용을 센다. 과금 모델.
- **⑩ 홍보 메시지**: 브랜드 메시지(옛 친구톡)는 채널 친구에게만, 광고 표기·야간 제한·수신거부 번호가 붙는다. 알림톡과 다른 포트 메서드.
- **배포**: `SOLAPI_*` 를 API 프로세스에만 두기(008 과 함께), 웹훅 도입 시 공개 경로 허용 목록.
