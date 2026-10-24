# 009 — 알림톡 자동 발송(⑥)에서 내린 결정

설계: `docs/superpowers/specs/2026-10-14-notification-design.md`. 이 기록은 계획마다 절을 더한다(⑥-1 백엔드 → ⑥-2 앱).

## 사용자와 정한 것 (2026-10-14)

설계 2절 그대로다.

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

비용(설계 2.1): 알림톡 건당 13원(월 1만 건 이상 10원), 문자 대체 SMS 18원·LMS 45원, 매장당 월 약 240건·3,100원 추정. 무료 한도는 없고 충전식 선불이다. 첫 실제 발송부터 과금된다.

## ⑥-1 백엔드에서 정한 것

새 스포크 `notification`(도메인·포트·pg 저장소·구독자·디스패처·솔라피/가짜 게이트웨이·API 열하나·온보딩 횟수 제한), 허브 이벤트 포트 `DomainEventPort` 와 이벤트 DTO 다섯, 허브 포트 `CustomerDirectoryPort.contact`, `core/observer/`(같은 세션 동기 버스), visit 인터랙터 다섯의 이벤트 발행, 마이그레이션 0011(표 넷, CHECK 13, 유일 제약 1, 색인 5), 설정 키 넷(`SOLAPI_API_KEY`·`SOLAPI_API_SECRET`·`SOLAPI_BALANCE_WARN_KRW`·`NOTIFICATION_DAILY_CAP`), 스크립트 둘(`check_notification_flow.sh`·`reregister_templates.py`). 라우트 표 69 → 80(늘어난 열하나, 없어지거나 바뀐 줄 없음). 단위 1294 → 1854, 통합 405 → 478, 구조 계약 6종(`notification` 을 일곱 목록에 더했고 `tests/test_importlinter_lists_spokes.py` 가 빠뜨림을 잡는다). 새 의존성은 없다(httpx 는 이미 있었다).

### 이 계획에서 새로 정한 것

- **변경 안내(`change`)와 바뀐 일정의 `reminder` 는 바뀔 때마다 만든다.** 설계 5.2 의 "같은 종류를 두 번 보내지 않는다"는 `confirm`·`reminder`(예약 시점)·`cancel`·`next_visit`·`report`(같은 주소)에만 적용한다. 연달아 두 번 바꾸면 아직 안 나간 `change` 는 `rescheduled` 로 취소되고 마지막 한 통만 남는다.
- **`notification_messages.pet_id` 칸을 두었다**(설계 4.4 에 없다). 보내는 순간 `#{대상}` 의 반려동물 이름을 `CustomerDirectoryPort.briefs` 로 읽으려면 필요하다. 외래 키 없음.
- **취소 이유에 `shop_closed`·`template_rejected`·`report_revoked` 를 더했다**(설계 4.4 의 11개 → 14개). `shop_closed` 는 보내는 순간 매장이 없거나 정지·폐업, `template_rejected` 는 템플릿이 없거나 반려. `report_revoked` 는 값만 있고 아직 쓰는 곳이 없다 — 알림장 끊기를 이벤트로 만드는 작업 11 이 쓴다.
- **지난 방문 간격은 이벤트가 싣는다.** `VisitClosed.previous_completed_at`(같은 아이 — `pet_id` 가 없으면 보호자만 방문끼리 — 의 앞선 완료 방문 `starts_at`, `VisitHistoryRepository.latest_completed_start_excluding`)으로 구독자가 `interval_weeks` 를 센다. notification 이 방문 표를 읽지 않는다. **완료일은 전이 시각(`occurred_at`)이다** — 방문 `starts_at` 이 아니다. 어제 방문을 오늘 완료 처리하면 오늘 기준으로 센다.
- **다른 매장·없는 방문의 발송 내역은 빈 목록 200 이다**(설계 7.2·9.6 은 404). notification 은 방문 표를 모르고 허브 포트 없이는 방문의 매장을 알 수 없다. 재발송은 그 방문의 줄을 찾지 못해 404, 단건 조회는 `shop_id` 로 걸러 404.
- **수동 재발송은 설정과 무관하다.** 매장이 직접 누른 줄(`requested_by_member_id` 있음)은 설정이 꺼진 종류여도 보내고, 디스패처도 그 줄은 `setting_off` 검사를 건너뛴다. 그 밖의 검사(매장·채널·템플릿·익명화·번호·야간·동의·상한)는 그대로다. 끝난 줄(성공 포함)은 모두 다시 보낼 수 있어 `MessageNotRetryableError` 는 쓰지 않는다(오류 표에는 남아 있다).
- **원 시도 1 + 자동 재시도 3.** `retry_at` 은 `attempts` 를 올리기 **전** 값을 받아 0·1·2 → 1분·5분·30분, 네 번째 실패에서 `failed(transient)`. 영구 오류도 업체를 한 번 부른 것이라 `attempts` 를 올린다. 미룸(심사 중·야간·상한)은 올리지 않는다.
- **접수 뒤 상태 조회 간격**: 처음 1분은 5초마다, 그 뒤 1분마다. 조회가 실패하면(일시·영구 둘 다) 60초 뒤. 24시간 안에 최종 상태가 없으면 `failed(transient, TIMEOUT)`.
- `confirm`·`change`·`cancel`·`report` 는 밤에도 바로 간다. 야간 미룸(아침 8시)은 `reminder`·`next_visit` 에만 있고, `reminder` 는 미룬 시각이 예약 1시간 전을 넘기면 `too_late`(정확히 1시간 전은 간다).
- 쿨다운 비교는 `last > now - cooldown_days` — 정확히 경계면 간다.
- 하루 상한은 **매장 시간대 오늘 00:00 이후 만든 줄 가운데 업체가 접수한 수**(`count_sent_since`: `provider_message_id IS NOT NULL AND created_at >= since`)다. 어제 만들어 오늘 보낸 줄은 세지 않는다. 넘으면 취소가 아니라 1시간 뒤로 미루고 WARNING.
- 디스패처의 `now` 는 `run_once` 한 번에 한 번 읽는다(회수·집기·줄마다·조회에 같은 값). 첫 `run_once` 에서 템플릿 상태·잔액을 한 번 보고, 그 뒤 10분·24시간마다.
- `claim_due` 는 `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING` 한 문장이고 `updated_at` 을 디스패처의 시계로 적는다(`recover_stuck` 이 그 시각을 본다). 파이썬에서 `(scheduled_at, id)` 로 정렬한다.
- 부분 유일 색인 `(visit_id, kind) WHERE status IN ('scheduled','sending')` 에 `shop_id` 가 없다 — 방문 ID 는 전 매장에서 유일하다. 스텁과 테스트는 다른 매장에 다른 방문 ID 를 써야 한다.
- 이벤트 DTO 는 전부 키워드 인자로 만든다. `VisitClosed.previous_completed_at` 은 `outcome` 뒤.
- `variables` 의 시각은 `astimezone(timezone.utc).isoformat()`(`+00:00` 꼴), 정수는 문자열, 없는 값은 키가 없고 `expires_at` 만 무기한이면 `""`. `report` 의 주소 키는 `url` — `has_delivered(url=…)` 가 `variables->>'url'` 을 본다. 문안 변수(`#{매장명}` 꼴)와는 다른 사전이다.
- **업체에 넘기는 변수 사전은 이름만**(`{"매장명": …}`) — 솔라피 어댑터가 `#{}` 를 씌운다. `render` 의 200자 자르기는 업체에 넘기는 사전에는 적용되지 않는다.
- `system_context(shop_id, timezone="Asia/Seoul")` — 시간대 기본값을 둔다. 집은 줄을 검사하기 전·예외로 끝났을 때의 `save` 는 `shop_id` 만 쓴다.
- 상태 조회의 예외는 `GatewayError` 전부(일시·영구)를 잡아 60초 뒤로 미룬다 — 영구 오류가 올라가면 루프가 2초마다 같은 줄에서 실패를 반복한다.
- `refresh_templates` 는 `set_status`·`upsert` 마다 커밋한다 — upsert 가 쥔 행 잠금을 들고 다음 등록(HTTP)을 부르지 않기 위해.
- 로그 한 줄은 message_id·매장·종류·결과이고 결과에 취소 이유·오류 코드를 붙인다(`canceled(anonymized)`, `failed(3040)`). 번호·이름·주소·변수·업체 응답은 없다(테스트가 본다). httpx 로거는 WARNING 으로 올렸다 — INFO 로 요청 URL(발신번호 인증 경로에 번호가 든다)을 찍기 때문.
- **온보딩은 업체를 먼저 부르고 그 뒤 저장한다**(N14). 연동은 토큰 확인 → 템플릿 등록 다섯 → 채널·설정·템플릿 저장. 설정 PUT 의 `next_visit` 템플릿 등록도 저장 전이다. 요청 트랜잭션은 끝날 때 커밋되므로 거꾸로 하면 행 잠금을 쥔 채 HTTP 를 부르게 된다.
- 연동 때 이미 `linked` 면 409 `NOTIFICATION_CHANNEL_LINKED`, `none`·`unlinked` 면 409 `NOTIFICATION_CHANNEL_NOT_LINKED`("먼저 인증번호를 받아 주세요"). 둘 다 409 라 앱 쪽 분기만 다르다.
- 발신번호 인증 시작의 응답은 토큰 신청과 같은 꼴 `{"status": "verification_requested"}`(202).
- 설정 후속 ①은 "바뀐" 종류가 아니라 **지금 꺼진 종류 전부**를 `setting_off` 로 취소한다(멱등). `change_enabled` 를 끄면 `change`·`cancel` 둘. ②는 `reminder_time` 이 바뀌면 대기 중인 `reminder`·`next_visit` 의 시각을 다시 계산하고 지났으면 `too_late`. ③은 `next_visit` 을 처음 켤 때만 등록(이미 있으면 다시 등록하지 않는다). 끄면 대기 줄은 취소되지만 템플릿은 남는다.
- `unlinked_at` 은 토큰 재신청·재연동 때 비우지 않는다(마지막 해제 시각). 해제해도 발신번호·인증 시각·문자 대체 설정은 남고 다시 연동하면 그대로다.
- 온보딩 요청 칸: `search_id` 1~100자·`category_code` 1~20자(공백·제어 문자 없음), `admin_phone` `^01[0-9]{8,9}$`, 토큰·인증번호 `^[0-9]{6}$`, 발신번호 `^[0-9]{9,11}$`(유선도 된다). 업체 형식을 문서로 확인하지 못해 모양만 본다.
- 횟수 제한은 매장 단위 Redis: 토큰 신청·인증번호 요청 시간당 5회, 토큰·인증번호 입력 10분에 5회(맞든 틀리든 센다). Redis 장애면 통과시키고 WARNING. 한 매장의 사장 여럿이 같은 창을 나눠 쓴다.
- `MessageAlreadyPendingError` 가 `install_error_handlers` 에 등록되어 있어, `VisitReserved` 가 같은 방문에 두 번 와 구독자가 던지면 visit 경로에서도 500 이 아니라 409 `NOTIFICATION_ALREADY_PENDING` 이다. 방문 저장은 어느 쪽이든 롤백된다.
- `MessageRepository.create`·`ChannelRepository.save` 는 넘긴 엔티티의 `shop_id` 가 컨텍스트와 다르면 `ValueError`. `list_templates_for_shops` 는 넘긴 모든 매장을 키로 가진다(없으면 `[]`).
- 솔라피 발송은 단일 발송(`POST /messages/v4/send`)이 아니라 `POST /messages/v4/send-many/detail` 에 메시지 하나 — 응답의 `failedMessageList[].statusCode` 로 접수 거절을 바로 분류할 수 있다. 채널 연동·발신번호 인증의 4xx 는 401(키 틀림)만 빼고 전부 `TokenInvalidError` 로 접는다(실계정에서 좁힌다). 잔액은 `balance + point`.
- 설계 6.1 의 `template_status`·`message_status` 는 `template_state`·`delivery_state` 로, `register_template` 은 `kind` 대신 `TemplateText` 를 받는다. 템플릿 이름은 `차곡노트 {kind} v{text_version}`.
- `share_text` 는 `status == "failed"` 인 줄에만. 시간대는 `ctx.timezone`(매장 프로필은 매장 이름에만 쓴다). 익명화되어 `contact` 가 None 이면 실패 줄이라도 `null`.
- `is_mobile_number` 는 정규식 `010[0-9]{8}` — 유니코드 숫자를 받지 않는다. `variables_for` 의 "필요한 변수"는 종류별 목록이 아니라 문안의 `#{…}` 에서 뽑는다(문안과 목록이 어긋날 수 없게). `render` 는 한 번만 치환하고 값을 200자에서 자르되 `링크` 는 자르지 않는다.
- 알림장 문자 대체는 매장 이름 길이에 따라 90바이트 경계에 걸쳐 sms(18원)·lms(45원)가 갈린다 — 설계대로 "넘치면 LMS".
- `expiry_label` 은 `expires_at` 의 매장 시간대 날짜를 "N월 N일까지" 로 적는다 — 링크는 그 시각 정각에 닫히므로 밤늦게 보낸 알림장은 "3일까지"인데 3일 00:30 에 닫히는 식의 어긋남이 있다.
- 구독자 어댑터는 `dependencies/notification_wiring.py` 를 거치지 않고 pg 저장소를 직접 만든다 — 어댑터가 `dependencies/` 를 import 하는 방향을 피했다. 구독자는 `main.py` 가 import 시점에 `subscribe` 한다(통합 테스트는 `clear_subscribers` 대신 `unsubscribe(자기 것)`).
- `ResendNotificationInteractor` 는 `wake` 를 생성자 인자로 받는다(journal 로 `create` 뒤 `wake` 순서를 본다). 프로바이더가 `dispatcher_wakeup.wake` 를 넘긴다.
- 통합 테스트의 알림장은 사진 없이 케어 메모만 적은 기록으로 보낸다(MinIO 를 쓰지 않는다). 연동 매장은 템플릿 5종을 SQL 로 `approved` 로 둔다.
- `.env.example` 은 저장소 루트 하나뿐이라 거기에 키 넷을 더했다(`backend/.env.example` 은 없다).
- **흐름 스크립트는 열한 단계**(확인 53줄). 예약은 모레·글피로 잡는다(브리프의 "내일 14:00"으로는 18:00 뒤에 돌리면 리마인드가 생기지 않는다). 문자 대체를 켠 채 끝 `0000` 번호로 `fallback_sent`(sms)를 먼저 보고, 끈 뒤 다른 `0000` 번호로 `failed`·`share_text`·다시 보내기를 본다. 다음 예약 제안은 다른 보호자의 첫 완료로 본다(같은 아이의 두 번째 완료는 간격이 1주가 된다). `expect` 는 인자 수가 셋이 아니면 멈춘다 — 맥의 bash 3.2 가 `"$( … \" … )"` 안의 이스케이프를 잘못 갈라 빈 인자 둘로 만든 적이 있다(요청 본문은 변수·함수로 먼저 만든다).
- `reregister_templates.py` 는 없는 종류도 등록한다(디스패처의 10분 주기와 같은 일) — 판이 다르거나 반려된 것과 같은 조건식의 자연스러운 결과다. `--refresh` 는 등록을 부르지 않는다(단위 테스트가 분기 제거 변이를 잡는다).

### 설계·브리프와 다르게 간 것

- 설계 7.2·9.6 의 "다른 매장의 ID 는 404" 가운데 방문별 목록만 빈 목록 200 이다(위).
- 설계 5.2 "같은 종류를 두 번 보내지 않는다"에서 `change` 와 바뀐 일정의 `reminder` 를 뺐다(위).
- 설계 4.4 의 취소 이유 11개에 셋을 더했고, 설계에 없는 `pet_id` 칸이 있다(위).
- 설계 5.3-3 의 검사 순서 앞에 `shop_closed`·`channel_unlinked`·`setting_off`·`template_rejected` 를 두었다(채널·설정은 설계가 "그사이 꺼졌으면" 으로 뒤에 적은 것을 앞으로).
- 설계 6.1 포트 메서드 이름 둘과 `register_template` 의 인자(위). 설계의 단일 발송 대신 `send-many/detail`(위).
- 설계 9.5 "토큰·인증번호 틀림의 업체 오류 코드 → `TokenInvalidError`" 는 문서를 못 읽어 "401 을 뺀 4xx 전부" 로 넓혔다.
- 브리프의 `_World` 식 도우미 대신 기존 `_setup()` 튜플 끝에 `events` 를 더했다(visit 인터랙터 테스트). 잠금 통합 테스트 2파일이 인터랙터를 직접 만들어 `events=FakeEvents()` 를 넣었다.
- 브리프의 `contact` 배선 통합 테스트는 더하지 않았다 — pg 저장소 통합 테스트가 `get_active` 의 익명화·다른 매장 거절을 이미 실제 DB 로 확인한다.
- `FakeDirectory`(notification)는 visit 것과 다르게 작다(`contacts`·`pets` 사전, `family()`). `FakeMessages` 는 `FakeTemplates`·`FakeChannels` 를 생성자로 받아 전 매장 조회를 흉내 낸다.
- 수정·일정 변경 인터랙터는 `self._now()` 를 메서드 맨 위에서 한 번 부르도록 옮겼다(동작은 같다).
- `retry_at` 의 인자 뜻은 브리프 문장("이번 실패까지 센 수")이 아니라 브리프의 테스트 값(0→1분)을 따랐다(위).
- `deferred_for_daytime` 은 낮이면 넘긴 객체를 그대로 돌려준다(UTC 로 바꾸지 않는다). 미룬 경우만 UTC.
- 매퍼에 `channel_values`·`settings_values` 를 두었고(INSERT 와 ON CONFLICT UPDATE 가 같은 사전), `TemplatePgRepository.by_kind` 는 모듈 함수다.
- 스키마 이름은 `MessageItemSchema`·`MessageListSchema`·`MessageCreatedSchema`(브리프의 `MessageItem`).
- 솔라피 어댑터는 모듈 import 때 httpx 로거를 WARNING 으로 올린다(브리프에 없는 줄, 로그 금지 테스트 때문).
- `tests/test_app_lifespan.py` 는 새 파일이다(기존 lifespan 테스트가 없었다).
- 흐름 스크립트의 12단계(라우트 표 diff)는 스크립트 안이 아니라 검증 절차다 — 아래 "흐름 확인".

### 알려진 동작 — 막지 않기로 했다

- 가족 묶음(두 마리) 등록은 방문마다 `VisitReserved` 가 따로 오므로 `confirm`·`reminder` 가 마리 수만큼 생긴다. 묶음당 한 통으로 합치는 규칙은 설계 5.2 에 없다.
- `UpdateVisitInteractor` 는 `pet_id` 만 바뀐 경우 발행하지 않는다 — 보호자에게 "아이가 바뀜"을 알리지 않는다.
- 예약 등록 한 번에 템플릿 질의가 둘(confirm·reminder)이고, `share_text` 는 요청마다 `public_profile`·`contact`·`briefs` 를 읽는다(실패 줄이 있을 때만).
- 재발송의 `wake()` 는 커밋 전에 불린다(구독자와 같다). 루프가 0.5초 뒤에 돌므로 보통 그 안에 커밋되지만, 늦으면 다음 주기(2초)에 집는다.
- `list_pending` 은 `scheduled` 만 돌려주므로 `reminder_time` 재계산은 디스패처가 막 집은 `sending` 줄을 건드리지 않는다 — 어차피 지금 나가는 줄이다.
- 같은 방문·종류의 줄이 여러 개일 때 "가장 최근"은 `created_at desc, id desc` 의 첫 줄이다. 같은 트랜잭션의 줄은 `created_at` 이 같아 id 로 갈린다.
- 응답의 `sender_number` 는 매장 자기 번호라 내보낸다(설정 화면에 보여야 한다). 로그에는 찍지 않는다.
- 설정 PUT 이 `register_template`(최대 10초)을 부른 뒤 저장하므로 요청이 그만큼 길어질 수 있다.
- 연동 요청에서 `gateway.link_channel` 은 성공했는데 그 뒤 DB 쓰기가 실패하면 업체에는 연동됐고 우리 쪽은 `token_requested` 로 남는다(아래 "남는 것").
- `SettingsRepository.update` 는 행이 없으면 `NoResultFound` 다 — 인터랙터는 `ensure` 로 읽는다.
- `_process` 가 DB 오류로 끝나면 그다음 `save` 가 다시 던져 `run_once` 가 끝나고(루프는 로그 뒤 다음 번) 그 줄은 `sending` 으로 남았다가 5분 뒤 회수된다. 방어 코드를 넣지 않았다.
- `run_forever` 의 예외 로그는 종류만(트레이스백 없음) — N12 를 우선했다.
- `claim_due` 의 ORM-enabled UPDATE 는 `synchronize_session` 기본값이다. 디스패처는 요청 밖 새 세션이라 같은 줄의 ORM 객체가 세션에 있는 경우가 없다.
- `updated_at` 시계가 둘이다 — `claim_due` 는 앱 시계, 나머지 UPDATE 는 DB 시계. 같은 호스트라 실제로는 문제 없다.
- `enabled_for` 에 모르는 `kind` 를 넘기면 `KeyError` — 호출자는 `KINDS` 의 값만 넘긴다. 제한기의 모르는 `action` 도 `KeyError`.
- `SolapiGateway` 는 `httpx.AsyncClient` 를 만들고 닫지 않는다(프로세스에 하나).
- `build_message_gateway` 는 키가 하나만 있어도 기동 실패다 — 반쯤 적힌 설정을 조용히 가짜로 바꾸지 않는다.
- 흐름 스크립트를 게이트웨이로 돌리면 개발 DB 에 확인용 행(매장·유저·고객·방문·알림 줄)이 남는다(기존 흐름 스크립트와 같다).

### 막지 못하고 감수하는 것

설계 9.8 과 9.3 그대로다.

1. 보호자가 알림톡을 거부할 방법은 카카오 채널 차단뿐(알림톡엔 수신거부 체계가 없다). 차단은 영구 실패로 돌아오고 문자 대체가 켜져 있으면 문자로 간다. 문자까지 막는 차단 플래그는 ⑦.
2. 발송된 알림톡은 회수할 수 없다. 보낸 직후 예약을 바꾸면 변경 안내가 한 통 더 간다.
3. 매장 시간대 변경 시 재계산하지 않는다.
4. 업체 콘솔에 남는 수신번호·내용(처리위탁). 스토어 제출 전 처리위탁 고지에 솔라피·카카오를 더한다.
5. HTTP 는 성공했는데 결과 커밋 전에 죽으면 한 번 더 갈 수 있다(at-least-once). 업체에 멱등 키가 없어 막을 수 없고 13원이라 감수한다. 놓치는 것은 없다.
6. 알림장 주소(토큰)가 `variables` 에 남는다. 링크를 끊으면 주소가 죽으므로 감수하고, 응답·로그에는 싣지 않는다.

### 남는 것 — 알고 미룬다

- **솔라피 실계정으로만 확인할 수 있는 것**(설계 11.3): 실제 채널 연동·템플릿 심사·발송·대체 발송·상태 코드(첫 대상은 Hiss Haus 의 실제 카카오톡 채널, 비즈니스 인증 선행, 테스트 발송 비용 몇백 원). 카카오 심사의 실제 반려(특히 `next_visit`)와 문안 수정 왕복. 실기기에서 공유 시트에 `share_text` 가 그대로 가는지(⑤의 미확인과 묶음). 운영에서 인스턴스가 둘 이상일 때 디스패처 둘(통합 테스트는 같은 프로세스의 두 세션으로만 본다).
- **업체 API 형식 대조표** — `docs.solapi.com` 은 참조 구현 환경에서 DNS 가 풀리지 않아 공식 SDK 소스(nodejs·kotlin)와 solapi.com 상태 코드 안내로 맞췄다. 일치 확인: 인증 헤더(HMAC-SHA256, date+salt), 발송 경로·본문·응답, 메시지 항목 키, 알림톡 옵션(`pfId`·`templateId`·`variables`·`disableSms`), 상태 조회 경로, 잔액, 채널 토큰·연동 경로, 템플릿 등록·검수 요청·상태, 상태 코드 표. **미확인**: 상태 조회 항목의 `statusCode`·`type` 키, 채널 연동 응답의 `channelId` 키, **발신번호 등록·인증 API 전체**(`POST /senderid/v1/numbers`, `PUT …/authenticate` + `x-mfa-data` — 어느 SDK 에도 없다), 템플릿 카테고리 코드 `003001`(`GET /kakao/v2/templates/categories` 로 맞춘다), 토큰·인증번호 틀림의 오류 코드, `search_id`·`category_code` 의 실제 모양과 토큰·인증번호가 6자리인지. 실계정에서 다르면 어댑터·스키마 정규식만 고친다.
- `SolapiGateway` 의 `httpx.AsyncClient` 를 종료 때 닫지 않는다 — 포트에 `aclose` 가 없다. 필요하면 lifespan 에 더한다.
- CI 의 `APP_ENV=dev` — `backend.yml` 이 실행마다 `generate_dev_env.py` 로 `.env` 를 만들고 그 파일이 `APP_ENV=dev` 를 넣는다(확인했다). 키 없는 앱 기동 테스트는 그래서 통과한다. 운영 배포가 `APP_ENV` 를 빠뜨리면 기본값 `prod` 라 키 없이는 기동하지 않는다(의도).
- `dispatcher_wakeup._event` 는 처음 `wait()` 한 이벤트 루프에 묶인다 — 운영은 루프가 하나라 괜찮고, `wait` 를 부르는 테스트 파일은 autouse 픽스처로 새 `Event` 를 넣는다.
- `_process` 의 DB 오류 뒤 세션 상태(위 "알려진 동작")는 테스트로 보지 않았다. at-least-once(보낸 뒤 커밋 전에 죽음)도 테스트로 보지 않았다.
- `link_channel` 뒤 DB 쓰기 실패 틈: 업체에는 연동됐고 우리 쪽은 `token_requested`. 다시 연동하면 업체가 어떻게 답하는지(이미 연동된 채널의 토큰 신청·연동) 실계정에서만 알 수 있다. 설계 9.5 의 "채널은 linked 로 두고" 는 템플릿 단계의 실패이고 이 틈은 더 앞이다.
- 두 세션 동시 `run_once` 통합 테스트는 "둘이 합쳐 세 줄을 한 번씩 보냈다"만 본다 — `SKIP LOCKED` 의 판별은 `claim_due` 두 세션 테스트(둘째가 기다리지 않고 남은 줄을 받았다)가 책임진다.
- 재발송 상태 검사의 변이 판별은 `accepted` 하나뿐 — 스텁이 scheduled·sending 대기 줄에 부분 유일 색인처럼 409 를 내서다. 실제 DB 도 색인이 scheduled·sending 만이라 이 검사가 없으면 접수 중인 줄 위에 새 줄이 생긴다. 통합 테스트는 scheduled 만 본다.
- 하루 상한의 뜻(오늘 만든 줄 가운데 접수된 수)이 설계 9.4 의 "오늘 발송"과 조금 다르다(위).
- 마이그레이션 0011 의 `downgrade` 는 돌려 보지 않았다(개발 DB 에 올리지 않는 규칙). 개발 DB 에 0011 을 올려야 새 경로가 동작한다(compose 의 backend 가 기동할 때 올린다).
- `MessageNotRetryableError`(409 `NOTIFICATION_NOT_RETRYABLE`)는 오류 표에만 있고 던지는 곳이 없다.
- `report_revoked` 취소 이유는 작업 11(알림장 끊기 이벤트)이 쓴다. 가족 묶음 한 통 합치기, 알림장 끊기 때 대기 중인 `report` 취소도 작업 11 몫이다.
- 통합 테스트 두 세션을 동시에 돌리면 같은 테스트 DB 를 TRUNCATE 해 서로 깨진다(하네스 문서에 적었다).
- 흐름 스크립트는 호스트의 `python3`·`curl`·bash 에 기댄다(기존 스크립트와 같다). 게이트웨이 경유는 2026-10-24 실행에서 확인했다(아래 '흐름 확인').
- `reregister_templates.py` 의 엔진이 `hide_parameters=True` 인지는 `purge_stale_media.py` 처럼 통합 테스트로 못 박지 않았다(단위 테스트만 있다).
- 지난 기록(008)에서 넘어온 것 그대로: `.env`·`.env.example` 의 인증 전용 비밀값 분리, `REPORT_LINK_KEY`·`SOLAPI_*` 를 API 프로세스에만 두기(인증 프로세스도 `core/config.py` 를 읽는다), `core/redis.py` 소켓 타임아웃 없음, 운영 OpenAPI 문서 노출.
- 미룬 것(설계 10절): 발송 결과 웹훅(공개 경로), 매장 전체 발송 목록·월별 집계·과금(⑧), 보호자 차단 플래그·수신 설정(⑦), 직원에게 설정 열기, 브랜드 메시지·홍보(⑩), NHN Cloud 어댑터, 운영자 잔액 API(⑧), 매장 시간대 변경 시 재계산.

### ⑥-2 앱이 기댈 API 계약

**경로.** 전부 로그인 + 매장 소속, 접두 `/v1/shops/{shop_id}`, 태그 `notifications`. 새 경로 열하나이고 visit 의 경로는 바뀌지 않았다(이벤트 발행만 더함). 오류 본문은 `{code, message}`뿐이다.

| 메서드·경로 | 권한 | 요청 본문 | 성공 | 오류 |
|---|---|---|---|---|
| GET `/notification/myself` | 소속 | — | 200 `{id: 7, name: "알림 (notification)", introduction}` | |
| GET `/notification` | 소속 | — | 200 overview | |
| POST `/notification/channel/token` | `shop:update` | `{search_id, admin_phone, category_code}` | 202 `{"status": "token_requested"}` | 409 `NOTIFICATION_CHANNEL_LINKED` · 429 · 502 |
| POST `/notification/channel` | `shop:update` | `{search_id, admin_phone, category_code, token}` | 200 overview | 400 `NOTIFICATION_TOKEN_INVALID` · 409 `NOTIFICATION_CHANNEL_NOT_LINKED`(토큰을 받은 적 없음) · 409 `NOTIFICATION_CHANNEL_LINKED` · 429 · 502 |
| DELETE `/notification/channel` | `shop:update` | — | 204 빈 본문 | 409 `NOTIFICATION_CHANNEL_NOT_LINKED` |
| PUT `/notification/settings` | `shop:update` | 아홉 칸 전체(아래) | 200 overview | 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 409 `NOTIFICATION_SENDER_NOT_VERIFIED` · 422 |
| POST `/notification/sender/verification` | `shop:update` | `{phone}` | 202 `{"status": "verification_requested"}` | 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 429 · 502 |
| POST `/notification/sender` | `shop:update` | `{phone, code}` | 200 overview | 400 `NOTIFICATION_TOKEN_INVALID` · 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 429 · 502 |
| GET `/visits/{visit_id}/notifications` | 소속 | — | 200 `{"items": [MessageItem]}` 최신순. **방문이 이 매장 것이 아니거나 없으면 빈 목록 200** | 422(`visit_id` 범위 밖) |
| POST `/visits/{visit_id}/notifications/{kind}/resend` | `reservation:write` | — | 201 `{"message_id": int}` | 404 `NOTIFICATION_MESSAGE_NOT_FOUND` · 409 `NOTIFICATION_ALREADY_PENDING` · 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 409 `NOTIFICATION_TEMPLATE_NOT_APPROVED` · 422(`kind` 가 여섯 밖) |
| GET `/notifications/{message_id}` | 소속 | — | 200 MessageItem | 404 `NOTIFICATION_MESSAGE_NOT_FOUND`(없거나 다른 매장) · 422 |

공통: 다른 매장 → 403 `NOT_A_MEMBER`, 권한 없는 멤버의 명령 → 403 `PERMISSION_DENIED`, 본문 형식 → 422 `VALIDATION_ERROR`, `shop_id` 가 int32 밖 → 422.

**요청 본문.**

- 온보딩 칸(어긋나면 422): `search_id` 1~100자·`category_code` 1~20자(공백·제어 문자 없음), `admin_phone` `^01[0-9]{8,9}$`(하이픈 없이), `token`·`code` `^[0-9]{6}$`, `phone`(발신번호) `^[0-9]{9,11}$`. `search_id`·`admin_phone` 은 업체에만 넘기고 저장하지 않는다 — 앱이 토큰 신청부터 연동까지 들고 있다가 둘 다 보낸다.
- PUT `/notification/settings`(아홉 칸 모두 필수, 불리언·정수는 엄격 — `"true"`·`1` 은 422):

```
confirm_enabled, reminder_enabled, report_enabled, change_enabled, next_visit_enabled, sms_fallback_enabled : bool
reminder_time            : "HH:MM"  (^([01][0-9]|2[0-3]):[0-5][0-9]$ — 08:00~21:00 밖은 422)
next_visit_after_weeks   : int(0 이상) | null  (1~52 밖은 422, null = 지난 방문 간격)
next_visit_cooldown_days : int(0 이상)         (1~365 밖은 422)
```

`change_enabled` 하나가 `change`·`cancel` 둘을 켠다. `sms_fallback_enabled` 는 설정 행이 아니라 채널에 저장되고 overview 의 `channel` 에 보인다.

**overview 응답**(`NotificationOverviewSchema`) — 시각은 매장 시간대(`+09:00`), 업체 ID 는 없다.

```
channel:   {status: "none"|"token_requested"|"linked"|"unlinked", linked_at: datetime|null,
            sender_number: str|null, sender_verified: bool, sms_fallback_enabled: bool}
           (채널 줄이 없으면 status "none" 에 나머지 null/false)
settings:  {confirm_enabled, reminder_enabled, report_enabled, change_enabled, next_visit_enabled: bool,
            reminder_time: "HH:MM", next_visit_after_weeks: int|null, next_visit_cooldown_days: int} | null (연동 전)
templates: [{kind, status: "pending"|"approved"|"rejected", rejected_reason: str|null,
             requested_at: datetime, decided_at: datetime|null}]   — 종류 순, 연동 전·해제 뒤엔 []
```

연동 직후: `channel.status "linked"`, `settings` 기본값(`true,true,true,true,false,"18:00",null,30`), `templates` 다섯 `pending`(`next_visit` 은 설정에서 켤 때 등록). 심사는 영업일 1~3일 — 앱은 "심사 중이에요(보통 1~3일)"·"승인됨"·"반려됐어요 · 운영자가 확인 중" 으로 보인다. dev(가짜 게이트웨이)에서는 디스패처가 기동 뒤 10분 안에 승인으로 바꾸고, 바로 보려면 `reregister_templates.py --refresh`.

**MessageItem**(`MessageItemSchema`) — 칸 열 개, 이것뿐. 시각은 매장 시간대.

```
message_id             : int
kind                   : "confirm" | "reminder" | "report" | "change" | "cancel" | "next_visit"
status                 : "scheduled" | "sending" | "accepted" | "sent" | "fallback_sent" | "failed" | "canceled"
channel_used           : "alimtalk" | "sms" | "lms" | null     (sent·fallback_sent 일 때)
scheduled_at           : datetime                              (즉시 줄은 만든 시각)
sent_at                : datetime | null
error_kind             : "transient" | "permanent" | null       (failed 일 때)
canceled_reason        : str | null  (canceled 일 때 — rescheduled · visit_canceled · no_show · setting_off · channel_unlinked ·
                                      shop_closed · template_rejected · report_revoked · too_late · anonymized · has_upcoming ·
                                      cooldown · no_consent · bad_phone)
requested_by_member_id : int | null                            (있으면 [다시 보내기]로 만든 줄)
share_text             : str | null                            (failed 줄에만 — 문자용 문안)
```

없는 칸(N12): `variables`·`provider_message_id`·`error_code`·`customer_id`·`pet_id`·`attempts`·`next_attempt_at`·`created_at`. 목록은 `created_at desc, id desc`(같은 트랜잭션에서 만든 줄은 id 로 갈린다). 취소된 줄도 목록에 온다 — 설계 8.2 대로 앱이 가린다.

`share_text` 모양(종류별, 매장 이름과 시각은 저장된 값, `#{대상}` 은 반려동물 이름 또는 "보호자 이름님"):

```
confirm     [매장명] 10월 16일(금) 14:00 예약이 접수되었어요.
reminder    [매장명] 내일 14:00 예약을 잊지 마세요.
report      [매장명] 알림장 https://…/r/<토큰>
change      [매장명] 예약이 10월 16일(금) 14:00로 바뀌었어요.
cancel      [매장명] 10월 16일(금) 14:00 예약이 매장 사정으로 취소되었어요.
next_visit  [매장명] 콩이 미용한 지 4주가 지났어요.
```

**오류 코드**(`notification/adapter/inbound/api/error_map.py` 와 라우트 표에 대조했다).

| 코드 | 상태 | 언제 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 본문 형식, 리마인드 시각·주·일수 범위 밖, `kind` 가 여섯 밖, ID 범위 밖 |
| `NOTIFICATION_CHANNEL_NOT_LINKED` | 409 | 연동 전의 설정·해제·발신번호·재발송, 토큰을 받은 적 없는 연동 |
| `NOTIFICATION_CHANNEL_LINKED` | 409 | 이미 연동된 매장의 토큰 신청·연동 |
| `NOTIFICATION_TOKEN_INVALID` | 400 | 토큰·인증번호 틀림·만료 |
| `NOTIFICATION_SENDER_NOT_VERIFIED` | 409 | 발신번호 인증 없이 문자 대체 켜기 |
| `NOTIFICATION_TEMPLATE_NOT_APPROVED` | 409 | 템플릿 없음·심사 중·반려된 종류의 재발송 |
| `NOTIFICATION_ALREADY_PENDING` | 409 | 가장 최근 줄이 scheduled·sending·accepted 인데 재발송, 동시에 두 번 눌러 둘째 |
| `NOTIFICATION_MESSAGE_NOT_FOUND` | 404 | 없거나 다른 매장의 message_id, 재발송할 줄이 없는 방문·종류 |
| `NOTIFICATION_NOT_RETRYABLE` | 409 | (표에만 있고 던지는 곳이 없다) |
| `NOTIFICATION_RATE_LIMITED` | 429 | 토큰 신청·인증번호 요청 시간당 5회, 토큰·인증번호 입력 10분에 5회 초과 |
| `NOTIFICATION_PROVIDER_UNAVAILABLE` | 502 | 온보딩 요청 중 업체 오류·시간 초과(10초) |
| `NOT_A_MEMBER` / `PERMISSION_DENIED` | 403 | 다른 매장 / 직원의 설정·채널·발신번호, `reservation:write` 없는 재발송 |

**폴링 규칙.**

- 알림장 보내기 뒤(설계 8.3): `GET /visits/{visit_id}/notifications` 에서 `kind == "report"` 의 첫 줄(최신)을 1초 간격 최대 10초. 줄 없음 → 미연동·꺼짐·미승인이니 지금처럼 공유 시트. `sent`/`fallback_sent` → "알림톡으로 보냈어요". `failed` → 스낵바 뒤 `share_text` 공유 시트. 10초 지나도 `accepted`·`scheduled`·`sending` → "보내는 중" 닫고 상세 블록이 나중에 갱신. 같은 링크를 다시 공유하면 새 줄이 생기지 않는다(끊고 새로 보내면 새 줄).
- 재발송 뒤: 응답의 `message_id` 로 `GET /notifications/{message_id}` 를 몇 초 폴링(요청이 디스패처를 깨우므로 보통 1초 안에 `accepted`, 5초쯤 뒤 최종 상태).
- 버튼: `failed` + `error_kind == "transient"` 면 [다시 보내기], `"permanent"` 면 [다른 방법으로 보내기](`share_text` 를 공유 시트에). 재발송은 성공한 줄에도 된다(가장 최근 줄이 끝나 있으면).
- 설정 PUT 뒤에는 응답의 overview 를 그대로 그린다(낙관적 갱신 없음). `next_visit_enabled` 를 켜면 응답의 `templates` 가 여섯이고 마지막이 `pending` 이다.

**가짜 게이트웨이 규칙**(dev, `SOLAPI_*` 가 비었을 때 — 앱 흐름 테스트가 기댄다): 토큰·인증번호는 `000000` 만 통과(다른 값은 400). 템플릿은 디스패처의 다음 조회에서 바로 `approved`. 발송은 늘 접수되고 결과는 보호자 번호 끝 네 자리로 — `0000` 영구 실패(문자 대체가 켜져 있으면 `fallback_sent`), `9999` 일시 실패(1분·5분·30분 재시도 뒤 `failed`), `8888` 두 번 대기 뒤 성공, 그 밖은 `sent`(알림톡). 실제 발송은 없다.

가족 묶음(두 마리) 한 통 합치기와 알림장 끊기 때 대기 중인 `report` 취소(`report_revoked`)는 작업 11 이 더한다 — 그때 이 절에 줄을 더한다.

### 흐름 확인 (2026-10-24, 게이트웨이 경유)

`backend/scripts/check_notification_flow.sh` 를 개발 스택(게이트웨이 `http://127.0.0.1:8080` → 인증·API 두 프로세스, 개발 DB·Redis db 0, 0011 올린 뒤, `backend`·`auth` 를 이 브랜치 코드로 다시 띄움)에서 `BASE` 없이 돌려 **열한 단계·확인 53줄 모두 통과**했다(종료 코드 0, 변이 전후 두 번). 판별력: 5단계 "응답에 번호·변수·업체 메시지 ID 가 없다"의 기대를 `True` 로 뒤집으면 그 줄에서 `실패 … (기대 True, 실제 False)` 로 멈추고 6단계 이후가 나오지 않는 것을 확인했다(종료 코드 1). 개발 DB 에 확인용 매장·유저·고객·방문·알림 줄이 남았다. 라우트 표는 69줄에서 80줄이 됐다(늘어난 경로 정확히 열하나, 없어지거나 바뀐 줄 없음).

참조 구현 때(2026-10-23)는 참조 트리의 대역 서버(인증 앱과 API 앱을 한 포트에 묶고 테스트 DB·Redis db 14·테스트 버킷만 쓴다. lifespan 은 API 앱 것이라 디스패처가 함께 돈다)에서 `BASE=http://127.0.0.1:18080` 으로 같은 결과(53줄·판별력)를 먼저 봤다. 운영자 지정과 템플릿 상태 조회는 `PATH` 맨 앞의 대역 `docker` 가 테스트 DB 로 보냈다 — 커밋된 스크립트에는 이 장치가 없다.
