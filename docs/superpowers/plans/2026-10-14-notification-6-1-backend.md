# 차곡노트 ⑥ 알림톡 자동 발송 — 계획 ⑥-1 백엔드: 이벤트·큐·디스패처·솔라피 온보딩·발송 내역 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장이 자기 카카오 채널을 앱 안에서 연동하면, 예약·변경·취소·완료·알림장이 보호자에게 알림톡(문자 대체 선택)으로 자동 나가고, 방문 상세에서 발송 내역을 보고 다시 보낼 수 있다 — 앱(⑥-2)이 기댈 백엔드 API 전부다.

**Architecture:** 새 스포크 `notification` 이다. visit 은 방문을 쓴 뒤 같은 트랜잭션에서 허브 이벤트(`VisitReserved`·`VisitRescheduled`·`VisitCanceled`·`VisitClosed`·`VisitReportIssued`·`VisitReportRevoked`)를 발행하고, `core/observer` 의 동기 버스가 notification 구독자를 불러 `notification_messages` 에 줄을 만든다 — 이 표가 큐다. 백엔드 프로세스 안의 디스패처가 때가 된 줄을 `FOR UPDATE SKIP LOCKED` 로 집어 커밋한 뒤 검사(해제·설정·템플릿·익명화·동의·야간·상한)하고 업체 포트 `MessageGatewayPort` 로 보낸다. 업체는 솔라피(HMAC 어댑터, 운영)와 가짜 어댑터(dev·테스트) 둘이고 실제 업체 API 는 이 계획의 어디서도 부르지 않는다. 온보딩(채널 토큰·연동·템플릿 등록·발신번호 인증)은 요청 안에서 업체를 먼저 부르고 그 뒤 저장한다. 모든 코드는 참조 작업 트리(`.superpowers/ref/wt-notification-6-1-be`, 브랜치 `ref/notification-6-1-be`, 커밋 a04d6b1…c8636a8)에서 먼저 돌려 검증했고, 변이 116개로 판별력을 확인했다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic · Redis · httpx(`MockTransport`) · pytest · import-linter. 새 의존성은 없다.

**Spec:** `docs/superpowers/specs/2026-10-14-notification-design.md` — 이 계획은 3절(구조)·4절(데이터 모델)·5절(이벤트·메시지 규칙)·6절(솔라피 어댑터·온보딩·문안)·7절(API)·9절(오류·보안)·11.1(백엔드 테스트)·12절(계획 나누기) 의 백엔드 문서다. 실행자는 설계 문서와 함께 `_docs/architecture.md`, `_docs/harness.md`, `backend/apps/{hub,visit,customer,tenancy}/_docs/CLAUDE.md`, `_docs/decisions/002-hub-port-assembly.md`·`006-visit-reservation.md`·`008-report.md` 를 읽는다.

**계획의 위치:** ⑥의 구현 계획 둘 가운데 첫째다. **⑥-1 백엔드(이 문서)** → ⑥-2 앱(`app/`, visit 폴더 안). ⑥-2 는 이 계획을 구현·병합한 뒤 실제 코드를 보고 쓴다. 앱이 기댈 API 계약은 작업 11 의 결정 기록 009 에 있다. 작업은 열셋이다 — 1~2 허브·발행, 3~9 notification 스포크(도메인·저장·구독자·게이트웨이·디스패처·온보딩 API·내역 API), 10 흐름 스크립트, 11 문서, 12 가족 묶음·링크 끊기(Review Focus 1·2 의 구현), 13 남은 경우의 테스트(Review Focus 3·4·5).

**비용(설계 2.1):** 솔라피 알림톡 13원/건(월 1만 건 넘으면 10원), SMS 18원, LMS 45원. 충전식이고 무료 한도가 없다. 매장당 월 240건이면 약 3,100원. dev 와 CI 는 가짜 게이트웨이라 비용이 없고, 운영 키(`SOLAPI_API_KEY`·`SOLAPI_API_SECRET`)를 넣는 순간부터 과금된다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 백엔드 명령은 `infra/`에서 돌린다. 맥에 파이썬 환경을 만들지 않는다.
- 작업 브랜치는 `feat/notification`이다(main `a639247`에서 땄고, 설계 문서와 이 계획서가 앞의 커밋이다). `main`에서 직접 작업하지 않는다.
- **작업 단위 커밋**: 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 사용자가 요청할 때만 한다. CI 는 푸시마다 단위·통합·import-linter 를 돌지만 흐름 스크립트·라우트 표는 보지 않는다 — 로컬에서 확인한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.**
- 계획서의 코드 블록은 그대로 옮긴다. 새 파일은 전문이고, 수정 파일은 diff 다. diff 가 적용되지 않으면 멈추고 보고한다 — 손으로 "비슷하게" 고치지 않는다.
- 볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다. 마이그레이션 0011 은 더하기만 한다.
- **실제 업체 API(`api.solapi.com`)를 부르지 않는다.** 어댑터 테스트는 `httpx.MockTransport`, 나머지는 가짜 게이트웨이·스텁이다. 운영 키를 `.env` 에 넣지 않는다 — dev 는 키가 비어 있으면 가짜 게이트웨이로 돈다.
- **비밀값·업체 API 키·전화번호·보호자 이름·알림장 주소(`variables`)·업체 응답 본문을 로그·오류 메시지·API 응답·커밋·문서·보고에 남기지 않는다.** `.env*` 의 내용을 출력하지 않는다. 실패한 통합 테스트의 출력에는 테스트용 번호·주소가 지역 변수로 찍힐 수 있으므로 옮겨 적지 않는다(`--tb=line`·`--tb=short` 로 돌린다). 이벤트·`NewMessage`·`NotificationMessage` 의 `repr` 에 주소가 들어 있으니 `%r` 로 로그에 찍지 않는다.
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다. 요청받지 않은 기능·설정·추상화를 넣지 않는다.

구조 (`_docs/architecture.md`, 스포크 `CLAUDE.md` 그대로 — 이 계획이 문서에 더하는 규칙 포함)
- 스포크끼리 직접 import 하지 않는다. notification 은 tenancy·customer·visit 을 허브 포트(`ShopProfilePort`·`CustomerDirectoryPort`·`VisitLedgerPort`)로만 만난다. 허브 포트 자리는 `notification/dependencies/hub_ports.py`(요청 안)와 `notification/dependencies/dispatcher_ports.py`(요청 밖, 세 공장), 꽂기는 `main.py`. visit 의 발행 포트 자리는 `visit/dependencies/hub_ports.get_domain_events`.
- 허브는 스포크를 모른다. `core` 는 허브의 추상을 import 할 수 있고(`core/observer`) 스포크는 `core` 의 구현을 import 하지 않는다.
- 도메인(`*/domain`)은 표준 라이브러리만 import 한다. `app` 층은 fastapi·sqlalchemy·redis·httpx·`core.config` 를 import 하지 않는다 — 키·상한·주소는 프로바이더가 인자로 넣는다. 구조 계약(`.importlinter`)의 일곱 목록에 `notification` 이 들어 있고 `tests/test_importlinter_lists_spokes.py` 가 빠짐을 잡는다.
- GoF 폴더 작명: 실제로 그 패턴일 때만 패턴 이름 — `core/observer/`(버스), `notification/adapter/inbound/observer/`(구독자), `notification/adapter/outbound/strategy/`(업체 어댑터 둘). 통상 폴더(`orm`·`pg`·`mappers`·`redis`·`schemas`·`v1`)는 그대로.
- 매장 범위의 경로는 `get_shop_context` 또는 `require_permission` 으로 `ShopContext` 를 받는다. 온보딩·설정은 `shop:update`(사장), 재발송은 `reservation:write`(직원도), 내역·단건 읽기는 소속. **가드 없이 `ShopContext` 를 만드는 곳은 둘뿐이다** — 로그인 없는 요청 경로의 `visit/app/services/public_context.py` 와 요청 밖(디스패처·운영자 스크립트)의 `notification/app/services/system_context.py`(권한 빔). `ShopContext` 를 받지 않는 저장소는 `PublicReportRepository` 와 `NotificationQueueRepository`(디스패처 전용) 둘이다.
- **잠금 순서: 고객 행 → 방문 행(ID 오름차순) → 알림 행.** 방문을 쓰는 인터랙터가 잠금을 쥔 트랜잭션 안에서 이벤트를 발행하고, 구독자가 그 끝에 알림 줄을 쓴다. 구독자는 업체를 부르지 않는다. 디스패처는 줄을 `sending` 으로 바꿔 **커밋한 뒤** 포트를 읽고 업체를 부른다. 온보딩은 업체를 먼저 부르고 그 뒤 저장한다. 잠금을 쥔 채 외부 HTTP 를 부르는 코드는 없다.
- 로그인 없이 열리는 경로는 늘지 않는다 — 열하나 전부 로그인 + 매장 소속이다. `tests/route_inspection.py`·`tests/test_hub_port_binding.py`·`tests/integration/test_route_wiring.py` 의 목록은 그대로다.
- 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC 를 상속한다. 포트에 메서드를 더하면 스텁에도 더한다(`test_fakes_are_ports.py` 가 잡는다). mock 프레임워크 대신 스텁. 두 세션 경합 테스트는 막힌 호출을 `asyncio.create_task` 로 들고 있다가 결과를 본다.
- 디스패처는 테스트에서 `run_once()` 로 한 번씩 돌린다(`build_dispatcher(session, gateway=…, now=…)` 로 시각과 게이트웨이를 준다). `dispatcher_wakeup` 의 `wait` 를 부르는 테스트는 파일마다 autouse 픽스처로 새 `asyncio.Event` 를 넣는다(이벤트가 처음 기다린 루프에 묶인다).

입력 경계 (넘으면 422 — 500 이 아니다)
- 경로 ID(`shop_id`·`visit_id`·`message_id`)는 1 ~ `2**63 - 1` · 재발송의 `kind` 는 여섯(`confirm`·`reminder`·`report`·`change`·`cancel`·`next_visit`) 밖이면 422 · 온보딩 칸: `search_id` 1~100자·`category_code` 1~20자(공백·제어 문자 없음), `admin_phone` `^01[0-9]{8,9}$`, 토큰·인증번호 `^[0-9]{6}$`, 발신번호 `^[0-9]{9,11}$` · 설정 PUT 은 전체 교체라 여섯 칸이 모두 필수이고 켬·끔은 엄격한 불리언, `reminder_time` 은 `HH:MM` 꼴(스키마) + 08:00~21:00(도메인 `check_settings` → 422 `VALIDATION_ERROR`, DB CHECK 도 같다), `next_visit_after_weeks` 는 1~52 또는 `null`, `next_visit_cooldown_days` 는 1~365(같은 도메인 검사).
- 업체 호출의 실패는 두 종류뿐이다 — `GatewayTransientError`(시간 초과·연결 실패·5xx·429·잔액 부족 → 재시도)와 `GatewayPermanentError`(그 밖 → `failed`). 토큰·인증번호 틀림은 도메인의 `TokenInvalidError`(400 `NOTIFICATION_TOKEN_INVALID`).

환경
- `.env` 에 더할 비밀값은 없다. `SOLAPI_API_KEY`·`SOLAPI_API_SECRET` 는 비워 두면 `APP_ENV=dev` 에서 가짜 게이트웨이로 돌고, dev 가 아니면서 비어 있으면 기동에서 `RuntimeError` 다(작업 6 — 운영은 필수). `SOLAPI_BALANCE_WARN_KRW`(기본 30000)·`NOTIFICATION_DAILY_CAP`(기본 300)은 기본값이 있다. `.env.example` 에 네 줄이 빈 값으로 들어간다.
- 작업 4 의 마지막에 개발 DB 에 마이그레이션 0011 을 올린다(`docker compose run --rm backend alembic upgrade head`). 그 전까지 통합 테스트는 테스트 DB(`chagocnote_test`)만 쓴다.
- Redis: 개발 스택은 db 0, 테스트는 db 15 다. 온보딩 횟수 제한 키가 db 에 생긴다(기한 1시간·10분). 테스트 픽스처가 db 15 만 비운다.
- 디스패처 루프는 lifespan 이 띄운다 — 개발 스택의 `backend` 컨테이너가 이 브랜치의 코드로 떠 있으면 줄이 생길 때마다 바로 돈다(dev 는 가짜 게이트웨이라 실제 발송 없음).

검증 명령 (`infra/`에서)
- 단위: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` — 시작 1294 → 끝 1867
- 통합(실제 Postgres·Redis·MinIO): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` — 시작 405 → 끝 485. **통합 두 세션을 동시에 돌리지 않는다**(같은 테스트 DB 를 TRUNCATE 해 서로 깨진다).
- 구조 계약: `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken
- 라우트 표: `docker compose run --rm --no-deps auth python scripts/print_routes.py` — 작업 1 전에 파일로 받아 두고(69줄) 작업 10 뒤에 `diff` 한다. 늘어나는 줄은 열하나다(온보딩·설정 여덟, 내역·재발송·단건 셋) → 80줄
- 파일 몇 개만: `docker compose run --rm --no-deps backend pytest <경로들> -q -p no:cacheprovider`(통합 표시가 있는 파일은 `--no-deps` 없이)
- **파일을 골라 돌릴 때 `tests/test_hub_port_binding.py` 는 맨 뒤에 두거나 따로 돌린다.** 통합 파일 사이에 두면 뒤쪽 통합 파일이 `fixture 'wired' not found` 로 실패한다(⑤-1 때부터, 원인 미조사).
- **시각 의존 테스트 하나:** `tests/integration/test_visit_flow_wiring.py::test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다`는 밤 22시 반 이후(한국 시각) 실패한다. ③부터 있던 것이고 이 계획이 건드리지 않는다.
- 참조 브랜치와 대조(선택, 마지막에): `git diff ref/notification-6-1-be -- backend _docs infra CLAUDE.md README.md .env.example` 가 비어 있어야 한다.

## 이 계획에서 새로 정한 것

설계와 다른 것과 새로 정한 것은 결정 기록 009(작업 11·12)에 전부 적는다. 사용자에게 보고한 큰 것만 요약한다:
- **변경 안내와 바뀐 일정의 리마인드는 바뀔 때마다 간다**(연달아 바꾸면 안 나간 것은 취소되고 마지막 한 통). 나머지 종류(접수·예약 시점 리마인드·취소·다음 예약 제안·같은 주소의 알림장)는 한 번만.
- **가족 묶음(같은 보호자·같은 시작 시각)은 한 통**이고 `#{대상}` 에 아이 이름을 "콩이·두부" 로 잇는다. 한 마리만 취소하면 그 아이 이름으로 취소 안내가 간다(작업 12).
- **알림장 링크를 끊으면 아직 안 나간 알림장 알림톡을 취소한다**(`VisitReportRevoked`, 사유 `report_revoked`, 작업 12). 익명화가 끊는 것은 이벤트 없이 디스패처의 `anonymized` 검사가 막는다.
- `notification_messages.pet_id` 칸, 취소 이유 `shop_closed`·`template_rejected`·`report_revoked`(설계 11개 → 14개).
- 지난 방문 간격은 이벤트(`VisitClosed.previous_completed_at`)가 싣고 "완료일"은 전이 시각이다 — notification 은 방문 표를 읽지 않는다.
- 다른 매장·없는 방문의 발송 내역은 빈 목록 200(설계는 404). 재발송·단건은 404.
- 수동 재발송은 설정과 무관하다(디스패처가 `requested_by_member_id` 줄은 `setting_off` 를 건너뛴다). 끝난 줄은 성공 포함 모두 다시 보낼 수 있다.
- 원 시도 1 + 자동 재시도 3(1·5·30분, `retry_at` 은 올리기 전 `attempts`). 접수 뒤 상태 조회는 처음 1분 5초마다, 그 뒤 1분마다, 24시간 넘으면 `failed(TIMEOUT)`.
- 온보딩은 업체를 먼저 부르고 그 뒤 저장한다. 솔라피 발송은 `send-many/detail` 에 한 통(접수 거절 코드를 바로 분류). 설계 6.1 의 `template_status`·`message_status` 는 `template_state`·`delivery_state`.

## 위협 점검표 (설계 9.7 — 행마다 막는 코드와 테스트)

작업별 검토는 계획서와의 일치가 아니라 이 표를 기준으로 한다.

| # | 시나리오 | 막는 코드 | 테스트 |
|---|---|---|---|
| N1 | 다른 매장의 visit_id·message_id 로 조회·재발송 | `ShopContext` 로 찾는다 — 단건·재발송 404, 목록은 빈 목록(작업 9) | `test_없거나_다른_매장의_줄이면_404_다`, `test_다른_매장의_방문이거나_없는_방문이면_빈_목록이다`, 배선 `test_다른_매장의_세_경로는_403_이고_다른_매장의_message_id_는_404_visit_id_는_빈_목록이다` |
| N2 | 내보내진 멤버가 쥔 토큰으로 재발송 | 소속 확인(기존 가드 `get_shop_context`·`require_permission`), 온보딩 여덟은 `shop:update`(작업 8·9) | 배선 `test_다른_매장의_여덟_경로는_전부_403_NOT_A_MEMBER_다`, `test_예약_권한이_없는_멤버는_403_이다` |
| N3 | 토큰 신청·인증번호 요청 난사 | `OnboardingRedisLimiter` — 매장당 시간당 5회(작업 8) | `test_동작마다_5번까지_받고_6번째부터_막는다`, `test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다`, 배선 `test_횟수_제한_토큰_신청_6번째와_틀린_토큰_6번째는_429_다` |
| N4 | 6자리 추측 | 토큰·인증번호 입력 10분에 5회(맞든 틀리든) + 업체 쪽 만료(작업 8) | `test_동작마다_5번까지_받고_6번째부터_막는다`, 배선 `test_횟수_제한_토큰_신청_6번째와_틀린_토큰_6번째는_429_다` |
| N5 | 재발송을 동시에 두 번 | 부분 유일 색인 `uq_notification_messages_pending` + 인터랙터의 대기 검사(작업 4·9) | `test_대기_줄_부분_유일_색인은_대기_상태만_담는다`, `test_가장_최근_줄이_대기_중이면_409_이고_만들지_않는다`, 배선 `test_영구_실패_줄은_share_text_가_있고_직원이_다시_보내면_새_줄이_생기며_두_번째는_409_다` |
| N6 | 두 디스패처가 같은 줄을 집는다 | `claim_due` 의 `FOR UPDATE SKIP LOCKED`(작업 4) | 두 세션 `test_두_세션이_동시에_집어도_같은_줄을_둘이_집지_않는다` |
| N7 | 집은 뒤 죽어 영영 `sending` | `recover_stuck` 5분 회수(작업 4·7) | `test_5분_넘게_sending_인_줄은_되돌려_다시_보낸다`, `test_5분_넘게_sending_인_줄은_되돌리고_시도를_세고_같은_루프에서_다시_보낸다` |
| N8 | 익명화 직후 발송 | 발송 시각에 `contact` 가 None → `anonymized`(작업 1·7) | `test_익명화한_고객의_연락처는_None_이다`, `test_보내는_순간_고객이_익명화되어_있으면_anonymized_로_취소한다`, `test_익명화된_고객의_실패_줄은_share_text_가_없다` |
| N9 | 마케팅 동의 없는 고객에게 다음 예약 제안 | 발송 시각 검사 `no_consent`(작업 7) | `test_다음_예약_제안은_마케팅_동의가_없으면_no_consent`, `test_동의_없음이_앞으로의_예약_검사보다_먼저다` |
| N10 | 버그로 대량 생성 → 대량 과금 | 하루 상한(`NOTIFICATION_DAILY_CAP`, 넘으면 1시간 미룸 + WARNING), 문자 대체 기본 꺼짐(작업 3·7) | `test_하루_상한에_닿으면_나머지는_1시간_뒤로_미룬다`, `test_하루_상한은_업체에_넘긴_줄만_만든_시각으로_센다`, 배선 `test_매장의_오늘_발송이_하루_상한에_닿으면_1시간_뒤로_미루고_경고만_남긴다` |
| N11 | 발신번호 없이 문자 대체 켜기 | 인터랙터 409 + DB CHECK(작업 4·8) | `test_발신번호_인증_없이_문자_대체를_켜면_409_이고_아무것도_바꾸지_않는다`, `test_발신번호_인증_없이_문자_대체를_켜면_DB_가_거절한다`, `test_문자_대체는_켜져_있고_발신번호_인증까지_마쳐야_한다` |
| N12 | `variables`(주소)·번호가 응답·로그에 샌다 | 응답 스키마에 칸 없음, `share_text` 만, 로그는 ID·매장·종류·결과만, httpx 로거 WARNING(작업 6·7·9) | `test_로그에는_메시지_ID_매장_종류_결과만_있고_번호_이름_주소는_없다`, 배선 `test_응답에_variables_업체_ID_오류_코드_고객_ID_칸이_없다`, `test_직원도_목록을_보고_시각은_매장_시간대이며_실패_줄에만_share_text_가_있다` |
| N13 | 구독자 예외가 방문 저장을 막는다 | 의도(같은 트랜잭션) — 구독자는 업체를 부르지 않는다(작업 1·2·5) | `test_구독자가_던지면_그대로_올라가고_뒤_구독자는_불리지_않는다`, 배선 `test_구독자가_던지면_500_이고_방문은_생기지_않는다`, `test_같은_예약을_두_번_등록하면_둘째는_409_이고_메시지_줄은_그대로다` |
| N14 | 잠금 쥔 채 업체 호출 | 디스패처는 집어 커밋한 뒤 호출, 온보딩은 업체 먼저 저장 뒤(작업 7·8) | `test_업체_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다`, `test_템플릿_등록_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다`, 디스패처 통합의 `run_once` 순서 |
| N15 | 야간에 리마인드 | `deferred_for_daytime` + `reminder_time` CHECK(작업 3·4·7) | `test_야간이면_아침_8시로_미룬다`, `test_리마인드와_다음_예약_제안은_매장_시간대의_밤이면_아침_8시로_미룬다`, `test_즉시_보내는_종류는_밤에도_바로_간다` |
| N16 | 일정을 바꿨는데 옛 시각 리마인드가 간다 | `VisitRescheduled` 가 대기 줄을 `rescheduled` 로 취소하고 다시 만든다(작업 2·5) | `test_일정을_바꾸면_옛_reminder_는_rescheduled_로_취소되고_새_reminder_와_change_가_생긴다`, 배선 `test_일정이_바뀌면_옛_reminder_는_rescheduled_로_취소되고_새_시각의_reminder_와_change_가_생긴다` |
| N17 | 취소한 방문의 리마인드가 간다 | `VisitCanceled`·`VisitClosed(no_show)` 가 대기 줄 취소(작업 5) | `test_매장_사정_취소는_대기_줄을_전부_취소하고_cancel_줄을_만든다`, `test_고객_요청_취소는_대기_줄만_취소하고_cancel_줄은_없다`, `test_노쇼는_대기_줄을_no_show_로_취소만_한다` |
| N18 | 직원이 설정·채널을 바꾼다 | `require_permission("shop:update")`(작업 8) | `test_직원은_설정을_바꾸지_못한다`, `test_직원은_신청하지_못한다`·`…연동하지_못한다`·`…해제하지_못한다`·`…시작하지_못한다`·`…확인하지_못한다`, 배선 `test_온보딩_흐름_토큰_신청_틀린_토큰_연동_직원은_읽기만` |

## Review Focus

설계가 말하거나 함의하지만 작업 1~11 의 테스트가 다루지 않은 것 가운데, 사람이 쓰다 가장 먼저 부딪힐 다섯. 1·2 는 설계가 빠뜨린 것이라 **작업 12** 가 구현까지 더하고, 3·4·5 는 **작업 13** 이 구현을 바꾸지 않고 테스트로 고정한다(참조 구현에서 돌려 통과했고 변이로 판별력을 확인했다).

1. **두 마리를 한 번에 예약하면 알림톡이 두 통 간다** — 방문이 둘이라 접수·리마인드·변경·취소가 마리 수만큼 나간다. 같은 보호자·같은 시작 시각은 한 통이고 `#{대상}` 은 "콩이·두부" 다 → 작업 12: `test_notification_review_focus_wiring.py::test_두_마리_예약은_confirm_reminder_change_가_한_통이고_대상은_두_이름이며_한_마리만_취소하면_그_아이_이름이다`, 단위 `test_handle_visit_event_interactor.py::test_가족_묶음은_둘째_이벤트에_줄을_만들지_않고_pet_ids_에_아이들을_싣는다`, `test_dispatcher.py::test_가족_묶음은_pet_ids_의_아이_이름을_가운뎃점으로_잇고_이름_없는_아이는_뺀다`.
2. **알림장 링크를 끊었는데 알림장 알림톡이 나간다** — 디스패처가 돌기 전에 끊으면 보호자는 닫힌 링크를 받는다. 끊기 이벤트가 안 나간 알림장 줄을 `report_revoked` 로 취소한다 → 작업 12: `test_notification_review_focus_wiring.py::test_디스패처가_돌기_전에_링크를_끊으면_report_는_report_revoked_로_취소되고_다시_보내면_새_줄만_나간다`, 단위 `test_send_visit_report_interactor.py::test_끊으면_VisitReportRevoked_를_끊은_뒤에_발행한다`, `test_handle_visit_event_interactor.py::test_링크를_끊으면_아직_안_나간_report_줄만_report_revoked_로_취소한다`.
3. **보호자 번호를 바꿨는데 옛 번호로 간다** — 줄은 번호를 저장하지 않고 보내는 순간 `contact` 로 읽는다 → 작업 13: `test_notification_review_focus_wiring.py::test_예약_뒤에_보호자_번호를_바꾸면_접수_안내는_바뀐_번호로_간다`.
4. **서버가 멈췄다 돌아오면 지난 리마인드가 한꺼번에 나간다** — 예약 1시간 전을 넘긴 것은 `too_late`, 야간에 깨어나면 다음 날 08:00 으로, 때가 안 된 제안은 그대로 → 작업 13: `test_notification_review_focus_wiring.py::test_멈췄다가_예약_1시간_전을_넘겨_돌아오면_reminder_는_too_late_다`, `::test_멈췄다가_밤에_돌아오면_reminder_는_다음_날_08시로_미루고_next_visit_은_그대로이며_아침에_나간다`.
5. **예약을 연달아 두 번 바꾸면 변경 안내가 두 통 간다** — 첫 안내는 `rescheduled` 로 취소되고 마지막 한 통만 나가며 리마인드는 마지막 시각이다 → 작업 13: `test_notification_review_focus_wiring.py::test_연달아_두_번_바꾸면_change_는_마지막_한_통만_대기하고_이전_시각은_첫_변경_뒤_시각이다`.

**여전히 돌려 보지 않은 것**(결정 기록 009 의 "남는 것"): 실제 솔라피 계정(발신번호 인증 API 경로·템플릿 카테고리 코드·토큰 틀림 오류 코드는 SDK 소스로만 맞췄다), 게이트웨이(Caddy)를 거친 흐름(작업 10 에서 처음 돌린다), `SolapiGateway` 의 `httpx.AsyncClient` 를 닫지 않음, 디스패처의 DB 오류 뒤 세션, 연동 성공 뒤 DB 쓰기 실패의 틈, at-least-once(보낸 뒤 커밋 전에 죽으면 한 통 더), 실제 Redis 장애.

---
### Task 1: 허브 — 방문 이벤트 DTO 다섯, `DomainEventPort`, 같은 세션의 동기 버스(`core/observer`), 고객 연락처 포트 `contact`

**Files:**
- Create: `backend/apps/hub/app/dtos/visit_events.py`
- Create: `backend/apps/hub/app/dtos/customer_contact.py`
- Create: `backend/apps/hub/app/ports/domain_event_port.py`
- Create: `backend/core/observer/in_process_event_bus.py`
- Modify: `backend/apps/customer/app/use_cases/customer_directory_interactor.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`
- Modify: `backend/apps/hub/app/ports/customer_directory_port.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Create: `backend/core/observer/__init__.py`
- Create: `backend/tests/test_in_process_event_bus.py`

**Interfaces:**
- Consumes: `hub.app.ports.customer_directory_port.CustomerDirectoryPort`(기존 `lock_family`·`briefs`), `core.database.DbSession`, `customer.app.use_cases.customer_directory_interactor`(`get_active` 의 익명화·다른 매장 거절은 `CustomerNotFoundError`), `visit/tests/helpers/fakes.FakeDirectory`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# hub.app.dtos.visit_events
@dataclass(frozen=True)
class VisitEvent:
    ctx: ShopContext
    visit_id: int
    customer_id: int
    pet_id: int | None
    starts_at: datetime       # UTC
    occurred_at: datetime     # UTC

@dataclass(frozen=True)
class VisitReserved(VisitEvent):
    revived: bool = False

@dataclass(frozen=True)
class VisitRescheduled(VisitEvent):
    previous_starts_at: datetime

@dataclass(frozen=True)
class VisitCanceled(VisitEvent):
    reason: str               # "customer_request" | "shop_reason"

@dataclass(frozen=True)
class VisitClosed(VisitEvent):
    outcome: str              # "completed" | "no_show"

@dataclass(frozen=True)
class VisitReportIssued(VisitEvent):
    url: str
    expires_at: datetime | None

# hub.app.ports.domain_event_port
class DomainEventPort(ABC):
    async def publish(self, event: VisitEvent) -> None: ...

# core.observer.in_process_event_bus
Subscriber = Callable[[AsyncSession, VisitEvent], Awaitable[None]]
def subscribe(handler: Subscriber) -> None
def subscribers() -> tuple[Subscriber, ...]
def clear_subscribers() -> None
class InProcessEventBus(DomainEventPort):
    def __init__(self, session: AsyncSession, handlers: Sequence[Subscriber]) -> None
    async def publish(self, event: VisitEvent) -> None
def get_event_bus(db: DbSession) -> DomainEventPort

# hub.app.dtos.customer_contact
@dataclass(frozen=True)
class CustomerContact:
    customer_id: int
    name: str
    phone: str                # 숫자만, customers.phone 저장 형식 그대로
    marketing_consent: bool

# hub.app.ports.customer_directory_port.CustomerDirectoryPort
async def contact(self, ctx: ShopContext, customer_id: int) -> CustomerContact | None

# visit.tests.helpers.fakes.FakeDirectory
contacts: dict[int, CustomerContact]                    # family() 가 (customer_id, name, "01012345678", True) 로 채운다
async def contact(self, ctx, customer_id) -> CustomerContact | None   # families 의 매장이 ctx.shop_id 와 다르면 None, 아니면 contacts.get()
```

이벤트는 전부 키워드 인자로 만든다(테스트: `VisitReserved(ctx=…, visit_id=…, customer_id=…, pet_id=…, starts_at=…, occurred_at=…)`).

알림톡의 바탕이다. visit 이 발행하고 notification 이 구독할 이벤트의 모양(허브 DTO)과 발행 포트, 그 구현인 `core/observer/in_process_event_bus.py`(요청의 세션 안에서 구독자를 등록 순서대로 동기로 부르고, 구독자가 던지면 그대로 올라가 요청이 실패한다 — 큐가 아니다), 그리고 디스패처가 보호자 번호·동의를 읽을 `CustomerDirectoryPort.contact`(익명화·다른 매장이면 None, 잠그지 않는다). 이 작업은 아무 경로도 바꾸지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`:

```diff
@@ -6,6 +6,7 @@ import pytest
 from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
 from customer.tests.helpers.fakes import family
 from customer.tests.helpers.profiles import ctx
+from hub.app.dtos.customer_contact import CustomerContact
 from hub.app.dtos.family_brief import CustomerBrief, PetBrief
 from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
 
@@ -177,3 +178,29 @@ async def test_몸무게는_반려동물_저장소로_넘긴다():
     pet = pets.seed(customer.id)
     await directory.set_pet_weight(ctx(), pet.id, Decimal("4.1"))
     assert (pets.rows[pet.id].weight_kg, journal[-1]) == (Decimal("4.1"), ("set_weight", pet.id, Decimal("4.1")))
+
+
+# --- 보호자 연락처(contact) — notification 만 부른다 ---
+
+
+async def test_연락처는_살아_있는_고객의_이름_번호_동의를_그대로_주고_잠그지_않는다():
+    journal, customers, _, _, directory = _directory()
+    customer = customers.seed(name="박서준", phone="01098765432", consent=True)
+    assert await directory.contact(ctx(), customer.id) == CustomerContact(
+        customer_id=customer.id, name="박서준", phone="01098765432", marketing_consent=True,
+    )
+    assert journal == []
+
+
+async def test_익명화한_고객의_연락처는_None_이다():
+    """N8 — 보내는 순간 연락처가 None 이면 notification 이 취소한다."""
+    _, customers, _, _, directory = _directory()
+    customer = customers.seed()
+    await customers.anonymize(ctx(), customer.id)
+    assert await directory.contact(ctx(), customer.id) is None
+
+
+async def test_다른_매장_고객의_연락처는_None_이다():
+    _, customers, _, _, directory = _directory()
+    customer = customers.seed(shop_id=2)
+    assert await directory.contact(ctx(shop_id=1), customer.id) is None
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -8,6 +8,7 @@ from __future__ import annotations
 from dataclasses import replace
 from decimal import Decimal
 
+from hub.app.dtos.customer_contact import CustomerContact
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from hub.app.dtos.media_urls import MediaUrls
 from hub.app.dtos.shop_profile import ShopProfile
@@ -152,10 +153,13 @@ class FakeDirectory(CustomerDirectoryPort):
         self.names: dict[int, str | None] = {}
         self.pet_names: dict[int, str | None] = {}   # 없는 아이는 "아이{ID}". 익명화한 가족이면 None 을 넣는다
         self.candidates: list = []
+        self.contacts: dict[int, CustomerContact] = {}   # family() 가 기본값을 넣는다. 익명화를 흉내 내려면 뺀다
 
     def family(self, customer_id=1, pets=(101,), shop_id=1, name="김민지", passed=()) -> None:
         self.families[customer_id] = (shop_id, {p: p in passed for p in pets})
         self.names[customer_id] = name
+        self.contacts[customer_id] = CustomerContact(customer_id=customer_id, name=name, phone="01012345678",
+                                                     marketing_consent=True)
 
     async def lock_family(self, ctx, customer_id, pet_ids):
         """실제 구현(customer)과 같은 허브 오류를 같은 조건에서 던진다 — 포트 계약이 곧 스텁의 계약이다."""
@@ -194,6 +198,11 @@ class FakeDirectory(CustomerDirectoryPort):
         self.journal.append(("find_draft_candidates", tuple(words)))
         return list(self.candidates)
 
+    async def contact(self, ctx, customer_id):
+        if self.families.get(customer_id, (None,))[0] != ctx.shop_id:
+            return None
+        return self.contacts.get(customer_id)
+
 
 class FakeVisits(
     VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository, VisitFeedRepository,
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -3,6 +3,7 @@ from hub.app.dtos.shop_profile import ShopProfile
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
+from visit.tests.helpers.builders import ctx
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
 from visit.app.ports.output.public_report_repository import PublicReportRepository
@@ -51,3 +52,13 @@ async def test_매장_공개_정보_스텁은_넣어_둔_매장만_돌려준다(
     profile = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
     shops = FakeShopProfile({1: profile})
     assert (await shops.public_profile(1), await shops.public_profile(2)) == (profile, None)
+
+
+async def test_고객_연락처_스텁은_넣어_둔_가족의_것만_준다():
+    directory = FakeDirectory()
+    directory.family(customer_id=1, shop_id=1, name="박서준")
+    contact = await directory.contact(ctx(), 1)
+    assert (contact.customer_id, contact.name, contact.phone, contact.marketing_consent) == (
+        1, "박서준", "01012345678", True,
+    )
+    assert (await directory.contact(ctx(shop_id=2), 1), await directory.contact(ctx(), 2)) == (None, None)
```

`backend/tests/test_in_process_event_bus.py`:

```python
"""core/observer 의 동기 버스 — 등록 순서, 같은 세션, 예외 전파, 중복 등록, 프로바이더."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.observer.in_process_event_bus import (
    InProcessEventBus,
    clear_subscribers,
    get_event_bus,
    subscribe,
    subscribers,
)
from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.visit_events import VisitReserved
from hub.app.ports.domain_event_port import DomainEventPort

NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clean_subscribers():
    clear_subscribers()
    yield
    clear_subscribers()


def _event() -> VisitReserved:
    ctx = ShopContext(shop_id=1, member_id=11, role="owner", permissions=frozenset())
    return VisitReserved(ctx=ctx, visit_id=7, customer_id=1, pet_id=101, starts_at=NOW, occurred_at=NOW)


def _recorder(name, log):
    async def handler(session, event):
        log.append((name, session, event))
    return handler


async def test_구독자는_등록_순서대로_같은_세션과_이벤트를_받는다():
    log, session, event = [], object(), _event()
    bus = InProcessEventBus(session, [_recorder("first", log), _recorder("second", log)])
    await bus.publish(event)
    assert log == [("first", session, event), ("second", session, event)]


async def test_구독자가_없으면_publish_는_아무_일도_하지_않는다():
    await InProcessEventBus(object(), []).publish(_event())


async def test_구독자가_던지면_그대로_올라가고_뒤_구독자는_불리지_않는다():
    """N13 — 구독자 예외는 발행한 유스케이스의 트랜잭션을 함께 실패시킨다(의도)."""
    log = []

    async def failing(session, event):
        raise RuntimeError("구독자 실패")

    bus = InProcessEventBus(object(), [failing, _recorder("after", log)])
    with pytest.raises(RuntimeError):
        await bus.publish(_event())
    assert log == []


async def test_같은_함수를_두_번_subscribe_해도_한_번만_등록된다():
    handler = _recorder("once", [])
    subscribe(handler)
    subscribe(handler)
    assert subscribers() == (handler,)


async def test_get_event_bus_는_넘긴_세션에_묶인_버스를_준다():
    log, session, event = [], object(), _event()
    subscribe(_recorder("registered", log))
    bus = get_event_bus(session)
    assert isinstance(bus, DomainEventPort)
    await bus.publish(event)
    assert log == [("registered", session, event)]
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

`docker compose run --rm --no-deps backend pytest tests/test_in_process_event_bus.py apps/customer/tests/app/use_cases/test_customer_directory_interactor.py apps/visit/tests/test_fakes_are_ports.py -q -p no:cacheprovider`
→ 수집 오류 2건(`ModuleNotFoundError: core.observer…`, `hub.app.dtos.customer_contact`), `Interrupted: 2 errors during collection`. (visit 의 `test_fakes_are_ports` 는 포트에 `contact` 를 더한 뒤 스텁을 채우기 전까지 TypeError 로 실패하는 단계가 있다 — 스텁까지 한 번에 구현해 같은 실행으로 통과를 확인했다.)

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/dtos/visit_events.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class VisitEvent:
    """visit 이 발행하는 사실. 구독자는 같은 트랜잭션에서 돈다(설계 5.1)."""

    ctx: ShopContext          # 발행한 요청의 매장 컨텍스트 — 구독자가 포트를 부를 때 그대로 쓴다
    visit_id: int
    customer_id: int
    pet_id: int | None
    starts_at: datetime       # UTC
    occurred_at: datetime     # UTC, 발행 시각(인터랙터의 now)


@dataclass(frozen=True)
class VisitReserved(VisitEvent):
    revived: bool = False     # 되돌리기로 다시 예약됨이 된 경우 True(접수 안내는 보내지 않고 리마인드만 다시 만든다)


@dataclass(frozen=True)
class VisitRescheduled(VisitEvent):
    previous_starts_at: datetime


@dataclass(frozen=True)
class VisitCanceled(VisitEvent):
    reason: str               # "customer_request" | "shop_reason" (visit.domain.entities.visit.CANCEL_REASONS 와 같은 값)


@dataclass(frozen=True)
class VisitClosed(VisitEvent):
    outcome: str              # "completed" | "no_show"


@dataclass(frozen=True)
class VisitReportIssued(VisitEvent):
    url: str                  # 알림장 주소(토큰이 들어 있다 — 로그에 찍지 않는다)
    expires_at: datetime | None
```

`backend/apps/hub/app/dtos/customer_contact.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerContact:
    """알림을 보낼 때만 읽는 보호자 연락처. 익명화한 고객은 이 값이 없다(None)."""

    customer_id: int
    name: str
    phone: str              # 숫자만, 예: "01012345678"(customers.phone 의 저장 형식 그대로)
    marketing_consent: bool
```

`backend/apps/hub/app/ports/domain_event_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.visit_events import VisitEvent


class DomainEventPort(ABC):
    """구현: core/observer(같은 프로세스·같은 세션의 동기 버스). 발행: visit. 구독: notification.
    구독자가 던지면 그대로 올라간다 — 발행한 유스케이스의 트랜잭션이 함께 실패한다(설계 5.1, N13)."""

    @abstractmethod
    async def publish(self, event: VisitEvent) -> None: ...
```

`backend/core/observer/in_process_event_bus.py`:

```python
"""Observer — 도메인 이벤트의 같은 프로세스·같은 세션 동기 버스(설계 3.1·5.1).

구독자 목록은 프로세스에 하나이고 진입점(main.py)이 기동 때 채운다. 이 모듈은 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import DbSession
from hub.app.dtos.visit_events import VisitEvent
from hub.app.ports.domain_event_port import DomainEventPort

Subscriber = Callable[[AsyncSession, VisitEvent], Awaitable[None]]

_subscribers: list[Subscriber] = []          # 진입점(main.py)이 기동 때 채운다


def subscribe(handler: Subscriber) -> None:
    """같은 함수를 두 번 넣지 않는다(이미 있으면 무시)."""
    if handler not in _subscribers:
        _subscribers.append(handler)


def subscribers() -> tuple[Subscriber, ...]:
    return tuple(_subscribers)


def clear_subscribers() -> None:
    """테스트용."""
    _subscribers.clear()


class InProcessEventBus(DomainEventPort):
    """등록된 순서대로, 같은 세션을 넘겨 동기로 부른다. 구독자가 없으면 아무 일도 없다."""

    def __init__(self, session: AsyncSession, handlers: Sequence[Subscriber]) -> None:
        self._session = session
        self._handlers = tuple(handlers)

    async def publish(self, event: VisitEvent) -> None:
        for handler in self._handlers:
            await handler(self._session, event)


def get_event_bus(db: DbSession) -> DomainEventPort:
    """FastAPI 프로바이더 — 요청의 세션에 묶인 버스. main.py 가 visit 의 자리에 꽂는다(작업 2)."""
    return InProcessEventBus(db, subscribers())
```

`backend/apps/customer/app/use_cases/customer_directory_interactor.py`:

```diff
@@ -11,6 +11,7 @@ from customer.domain.errors import CustomerNotFoundError
 from customer.domain.services.draft_ranking import match_family
 from customer.domain.services.phone_number import mask_phone
 from customer.domain.services.search_terms import parse_query
+from hub.app.dtos.customer_contact import CustomerContact
 from hub.app.dtos.draft_candidate import DraftCandidate
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from hub.app.dtos.shop_context import ShopContext
@@ -91,3 +92,12 @@ class CustomerDirectoryInteractor(CustomerDirectoryPort):
             )
             for match, c in ranked[:DRAFT_CANDIDATE_LIMIT]
         ]
+
+    async def contact(self, ctx: ShopContext, customer_id: int) -> CustomerContact | None:
+        # 익명화한 고객과 다른 매장의 고객은 저장소가 "없음"으로 본다 — 둘 다 None 이다(N8).
+        try:
+            customer = await self._customers.get_active(ctx, customer_id)
+        except CustomerNotFoundError:
+            return None
+        return CustomerContact(customer_id=customer.id, name=customer.name, phone=customer.phone,
+                               marketing_consent=customer.marketing_consent)
```

`backend/apps/hub/app/ports/customer_directory_port.py`:

```diff
@@ -4,6 +4,7 @@ from abc import ABC, abstractmethod
 from datetime import datetime
 from decimal import Decimal
 
+from hub.app.dtos.customer_contact import CustomerContact
 from hub.app.dtos.draft_candidate import DraftCandidate
 from hub.app.dtos.family_brief import FamilyBriefs
 from hub.app.dtos.shop_context import ShopContext
@@ -11,7 +12,7 @@ from hub.app.dtos.shop_context import ShopContext
 
 class CustomerDirectoryPort(ABC):
     """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순, 카톡 초안 후보,
-    미용 기록의 몸무게)."""
+    미용 기록의 몸무게), notification (보낼 때의 연락처)."""
 
     @abstractmethod
     async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
@@ -49,3 +50,8 @@ class CustomerDirectoryPort(ABC):
         같은 순위면 고객 ID 오름차순. 익명화한 고객은 후보가 아니고, 무지개다리를 건넌 아이는 pets 에서 뺀다.
         낱말은 저장하지도 로그에 남기지도 않는다(설계 10절 V9).
         """
+
+    @abstractmethod
+    async def contact(self, ctx: ShopContext, customer_id: int) -> CustomerContact | None:
+        """이 매장의 살아 있는 고객이면 연락처. 익명화했거나 다른 매장이면 None. 잠그지 않는다.
+        가린 번호가 아니라 실제 번호다 — notification 만 부른다. 로그에 남기지 않는다."""
```

`backend/core/observer/__init__.py`:

```python

```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 테스트(세 파일) | 27 passed (새로 더한 것 9: 버스 5, `contact` 3, 스텁 1) |
| 단위 전체 (`-m "not integration and not network"`) | 1303 passed (시작 1294 + 9) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken |

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `InProcessEventBus.publish` 가 `reversed(self._handlers)` 로 역순 호출 → `tests/test_in_process_event_bus.py::test_구독자는_등록_순서대로_같은_세션과_이벤트를_받는다` (그리고 `test_구독자가_던지면_그대로_올라가고_뒤_구독자는_불리지_않는다` — 역순이면 뒤 구독자가 먼저 불린다)
- `publish` 가 `try/except Exception: pass` 로 구독자 예외를 삼킴 → `tests/test_in_process_event_bus.py::test_구독자가_던지면_그대로_올라가고_뒤_구독자는_불리지_않는다`
- `subscribe` 가 `not in` 검사 없이 append → `tests/test_in_process_event_bus.py::test_같은_함수를_두_번_subscribe_해도_한_번만_등록된다`
- `contact` 가 `CustomerNotFoundError` 를 잡지 않음 → `…/test_customer_directory_interactor.py::test_익명화한_고객의_연락처는_None_이다`, `::test_다른_매장_고객의_연락처는_None_이다`
- `contact` 가 `phone=mask_phone(customer.phone)` 로 가린 번호를 줌 → `…/test_customer_directory_interactor.py::test_연락처는_살아_있는_고객의_이름_번호_동의를_그대로_주고_잠그지_않는다`
- `get_event_bus` 가 `subscribers()` 대신 빈 튜플을 넘김 → `tests/test_in_process_event_bus.py::test_get_event_bus_는_넘긴_세션에_묶인_버스를_준다`
- `FakeDirectory.contact` 가 `ctx.shop_id` 를 보지 않음 → `apps/visit/tests/test_fakes_are_ports.py::test_고객_연락처_스텁은_넣어_둔_가족의_것만_준다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(hub): 도메인 이벤트 포트와 같은 세션의 동기 버스(core/observer), 고객 연락처 포트 contact

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: visit — 예약·수정·일정 변경·전이(취소·완료·노쇼·되돌리기)·알림장 발급을 허브 이벤트로 발행한다

**Files:**
- Modify: `backend/apps/hub/app/dtos/visit_events.py`
- Modify: `backend/apps/visit/dependencies/hub_ports.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Modify: `backend/apps/visit/app/ports/output/visit_history_repository.py`
- Modify: `backend/apps/visit/app/use_cases/register_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/send_visit_report_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/transition_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/update_visit_interactor.py`
- Modify: `backend/apps/visit/dependencies/register_visit_provider.py`
- Modify: `backend/apps/visit/dependencies/reschedule_visits_provider.py`
- Modify: `backend/apps/visit/dependencies/send_visit_report_provider.py`
- Modify: `backend/apps/visit/dependencies/transition_visits_provider.py`
- Modify: `backend/apps/visit/dependencies/update_visit_provider.py`
- Modify: `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_send_visit_report_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_visit_events_wiring.py`
- Modify: `backend/tests/integration/test_visit_locking.py`
- Modify: `backend/tests/integration/test_visit_report_locking.py`
- Modify: `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: 작업 1 의 `VisitReserved`·`VisitRescheduled`·`VisitCanceled`·`VisitClosed`·`VisitReportIssued`, `DomainEventPort`, `core.observer.in_process_event_bus.get_event_bus`; 기존 visit 인터랙터 다섯(`register_visit`·`update_visit`·`reschedule_visits`·`transition_visits`·`send_visit_report`)과 프로바이더, `VisitHistoryRepository`, `FakeVisits`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# visit.dependencies.hub_ports
def get_domain_events() -> DomainEventPort      # 호출하면 RuntimeError("DomainEventPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")

# main.py
app.dependency_overrides[get_domain_events] = get_event_bus     # core.observer.in_process_event_bus.get_event_bus

# 인터랙터 다섯 — 생성자 (키워드 이름 events, now 바로 앞)
RegisterVisitInteractor(visits, board, menus, schedule, directory, events: DomainEventPort, now)
UpdateVisitInteractor(visits, board, menus, schedule, directory, events: DomainEventPort, now)
RescheduleVisitsInteractor(visits, board, menus, schedule, directory, events: DomainEventPort, now)
TransitionVisitsInteractor(visits, history, menus, reports, directory, events: DomainEventPort, now)
SendVisitReportInteractor(visits, records, settings, reports, menus, directory, library, shops,
                          events: DomainEventPort, now, link_key, web_base_url)

# hub.app.dtos.visit_events (T1 에서 바뀐 것)
@dataclass(frozen=True)
class VisitClosed(VisitEvent):
    outcome: str                              # "completed" | "no_show"
    previous_completed_at: datetime | None    # 완료일 때 같은 아이(pet_id 없으면 보호자만 방문끼리)의 앞선 완료 방문 starts_at, 노쇼는 None

# visit.app.ports.output.visit_history_repository.VisitHistoryRepository
async def latest_completed_start_excluding(
    self, ctx: ShopContext, customer_id: int, pet_id: int | None, exclude_visit_id: int
) -> datetime | None
# pg: VisitPgRepository 에 구현(shop_id·customer_id·pet_id(None 이면 IS NULL)·status=completed·id != exclude 의 max(starts_at))
# 스텁: FakeVisits 에 같은 이름

# visit.tests.helpers.fakes
class FakeEvents(DomainEventPort):
    def __init__(self, journal: Journal | None = None) -> None
    published: list[VisitEvent]                       # 발행 순서대로
    async def publish(self, event) -> None            # published 에 더하고 journal 에 ("publish", type(event).__name__, event.visit_id)
```

발행 규칙(브리프 2절 표 그대로 — 다르게 한 것 없음):

| 인터랙터 | 발행 | 위치 |
|---|---|---|
| `RegisterVisitInteractor` | 만든 방문마다 `VisitReserved(revived=False)` — `status == RESERVED` 일 때만(`walk_in` 은 없음) | `create_many` 뒤, 경고 계산 앞 |
| `UpdateVisitInteractor` | `updated.starts_at != current.starts_at` 이면 `VisitRescheduled(previous_starts_at=current.starts_at, starts_at=updated.starts_at)` | `update_details` 뒤, 경고 계산 앞 |
| `RescheduleVisitsInteractor` | 옮긴 방문마다 `VisitRescheduled(previous_starts_at=잠근 행의 starts_at)` | `reschedule` 뒤, `ensure`·경고 앞 |
| `TransitionVisitsInteractor` | `cancel`→`VisitCanceled(reason=command.cancel_reason)`, `complete`→`VisitClosed("completed", previous_completed_at=latest_completed_start_excluding(…))`, `no_show`→`VisitClosed("no_show", None)`, `revert`→`VisitReserved(revived=True)`, `start`→없음 | `apply_changes`·`apply_completion_effects` 뒤, 응답 앞 |
| `SendVisitReportInteractor` | 새 링크를 만들었을 때만(`live is None` 이었던 경로) `VisitReportIssued(url=link.url, expires_at=live.expires_at)` | `set_hidden`·`describe_report`·`describe_link` 뒤, 응답 앞 |

공통 칸: `ctx=command.ctx`, `visit_id`·`customer_id`·`pet_id`·`starts_at` 은 쓰기 뒤 행의 값, `occurred_at` 은 인터랙터가 한 번 부른 `self._now()`.

발행 쪽이다. 인터랙터 다섯이 생성자 `events: DomainEventPort`(`now` 앞 키워드)를 받고 쓰기가 끝난 **뒤, 같은 트랜잭션 안에서** 발행한다. 규칙: 등록은 방문마다 `VisitReserved(revived=False)`, 되돌리기는 `revived=True`, 수정은 `starts_at` 이 바뀔 때만 `VisitRescheduled`(pet 만 바뀌면 발행 없음), 일정 변경은 옮긴 방문마다, 취소는 사유를 싣고, 완료·노쇼는 `VisitClosed(outcome, previous_completed_at)` — 앞선 완료 방문의 시작 시각은 새 저장소 메서드 `latest_completed_start_excluding` 로 읽는다. 알림장은 **새 링크를 만들 때만** `VisitReportIssued(url, expires_at)` (같은 링크 다시 보내기는 발행 없음). 허브 포트 자리는 `visit/dependencies/hub_ports.get_domain_events`, `main.py` 가 `get_event_bus` 를 꽂는다. 아직 구독자가 없어 발행은 아무 일도 하지 않는다(작업 5 가 꽂는다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py`:

```diff
@@ -176,6 +176,23 @@ async def test_아이의_지난_완료와_완료_시각들(db_session):
     assert await repo.completed_starts(A, 1, None, limit=2) == [kst(9, 4, 14)]
 
 
+async def test_자기를_뺀_같은_아이의_가장_최근_완료_시작_시각(db_session):
+    repo = VisitPgRepository(db_session)
+    earlier = await insert_visit(db_session, kst(8, 1, 14), "completed")
+    latest = await insert_visit(db_session, kst(9, 2, 14), "completed")
+    await insert_visit(db_session, kst(9, 9, 14), "canceled")
+    await insert_visit(db_session, kst(9, 10, 14), "no_show")
+    await insert_visit(db_session, kst(9, 11, 14), "completed", pet_id=102)
+    await insert_visit(db_session, kst(9, 12, 14), "completed", shop_id=2)
+    alone = await insert_visit(db_session, kst(9, 4, 14), "completed", pet_id=None)
+    assert await repo.latest_completed_start_excluding(A, 1, 101, latest) == kst(8, 1, 14)
+    assert await repo.latest_completed_start_excluding(A, 1, 101, earlier) == kst(9, 2, 14)
+    assert await repo.latest_completed_start_excluding(A, 1, 102, latest) == kst(9, 11, 14)
+    assert await repo.latest_completed_start_excluding(A, 1, None, latest) == kst(9, 4, 14)
+    assert await repo.latest_completed_start_excluding(A, 1, None, alone) is None
+    assert await repo.latest_completed_start_excluding(B, 1, 101, latest) == kst(9, 12, 14)   # 매장별로
+
+
 async def test_장부_질문들(db_session):
     repo = VisitPgRepository(db_session)
     await insert_visit(db_session, kst(9, 1, 14), "canceled", pet_id=101)
```

`backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`:

```diff
@@ -2,6 +2,7 @@ from datetime import date, time
 
 import pytest
 
+from hub.app.dtos.visit_events import VisitReserved
 from hub.app.errors import FamilyPetNotFoundError
 from visit.app.dtos.register_visit_dto import RegisterVisitCommand
 from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
@@ -16,6 +17,7 @@ from visit.domain.value_objects.schedule_settings import ScheduleSettings
 from visit.tests.helpers.builders import ctx, kst
 from visit.tests.helpers.fakes import (
     FakeDirectory,
+    FakeEvents,
     FakeMenus,
     FakeSchedule,
     FakeVisits,
@@ -30,8 +32,9 @@ def _setup(settings=None):
     schedule = FakeSchedule(journal) if settings is None else FakeSchedule(journal, settings)
     menus, visits, directory = FakeMenus(journal), FakeVisits(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102))
-    interactor = RegisterVisitInteractor(visits, visits, menus, schedule, directory, now=lambda: NOW)
-    return journal, schedule, menus, visits, directory, interactor
+    events = FakeEvents(journal)
+    interactor = RegisterVisitInteractor(visits, visits, menus, schedule, directory, events=events, now=lambda: NOW)
+    return journal, schedule, menus, visits, directory, interactor, events
 
 
 def _command(**overrides):
@@ -42,7 +45,7 @@ def _command(**overrides):
 
 
 async def test_두_마리면_방문이_둘이고_가족을_잠근_뒤_넣는다():
-    journal, _, menus, _, _, interactor = _setup()
+    journal, _, menus, _, _, interactor, _ = _setup()
     bath = menus.seed("목욕", minutes=60)
     nails = menus.seed("발톱", minutes=None)   # 기본 소요가 없으면 매장 기본(120)으로 센다
     result = await interactor.register_visit(_command(pet_ids=(101, 102), menu_ids=(bath.id, nails.id)))
@@ -56,7 +59,7 @@ async def test_두_마리면_방문이_둘이고_가족을_잠근_뒤_넣는다(
 
 
 async def test_시각은_매장_시간대로_내보낸다():
-    *_, interactor = _setup()
+    *_, interactor, _ = _setup()
     [visit] = (await interactor.register_visit(_command())).visits
     assert (visit.starts_at.isoformat(), visit.ends_at.isoformat()) == (
         "2026-10-02T14:00:00+09:00", "2026-10-02T16:00:00+09:00")
@@ -64,26 +67,26 @@ async def test_시각은_매장_시간대로_내보낸다():
 
 
 async def test_반려동물_없이_보호자만의_방문_하나():
-    *_, visits, _, interactor = _setup()
+    *_, visits, _, interactor, _ = _setup()
     [visit] = (await interactor.register_visit(_command(pet_ids=()))).visits
     assert visit.pet is None
     assert visits.rows[visit.visit_id].pet_id is None
 
 
 async def test_메뉴도_소요도_없으면_매장_기본_소요다():
-    *_, interactor = _setup(ScheduleSettings(time(10), time(19), 90, frozenset()))
+    *_, interactor, _ = _setup(ScheduleSettings(time(10), time(19), 90, frozenset()))
     [visit] = (await interactor.register_visit(_command())).visits
     assert visit.duration_minutes == 90
 
 
 async def test_소요를_보내면_그_값이다():
-    *_, interactor = _setup()
+    *_, interactor, _ = _setup()
     [visit] = (await interactor.register_visit(_command(duration_minutes=150))).visits
     assert visit.duration_minutes == 150
 
 
 async def test_지금_시작한_손님은_10분_단위로_내린_시각에_미용_중이다():
-    *_, visits, _, interactor = _setup()
+    *_, visits, _, interactor, _ = _setup()
     [visit] = (await interactor.register_visit(_command(starts_at=None, walk_in=True))).visits
     row = visits.rows[visit.visit_id]
     assert (row.starts_at, row.status, row.started_at, row.status_changed_by_member_id) == (
@@ -92,7 +95,7 @@ async def test_지금_시작한_손님은_10분_단위로_내린_시각에_미
 
 @pytest.mark.parametrize("fields", [dict(walk_in=True), dict(starts_at=None)])
 async def test_예약_시각과_지금_시작은_하나만(fields):
-    journal, *_, interactor = _setup()
+    journal, *_, interactor, _ = _setup()
     with pytest.raises(VisitInputError):
         await interactor.register_visit(_command(**fields))
     assert journal == []
@@ -100,7 +103,7 @@ async def test_예약_시각과_지금_시작은_하나만(fields):
 
 async def test_고를_수_없는_메뉴면_잠그지도_않는다():
     """V1 — 다른 매장 메뉴와 보관한 메뉴는 이 매장에 없는 메뉴다."""
-    journal, _, menus, *_, interactor = _setup()
+    journal, _, menus, *_, interactor, _ = _setup()
     theirs = menus.seed("남의 메뉴", shop_id=2)
     archived = menus.seed("옛 메뉴", archived=True)
     for menu_id in (theirs.id, archived.id, 999):
@@ -115,7 +118,7 @@ async def test_고를_수_없는_메뉴면_잠그지도_않는다():
     (dict(duration_minutes=95), VisitInputError),
 ])
 async def test_시각_규칙에_어긋나면_잠그지도_않는다(fields, error):
-    journal, *_, interactor = _setup()
+    journal, *_, interactor, _ = _setup()
     with pytest.raises(error):
         await interactor.register_visit(_command(**fields))
     assert "lock_family" not in [entry[0] for entry in journal]
@@ -123,21 +126,21 @@ async def test_시각_규칙에_어긋나면_잠그지도_않는다(fields, erro
 
 async def test_가족_확인에서_거절되면_넣지_않는다():
     """V2 — 다른 가족·다른 매장의 반려동물, 무지개다리 아이는 customer 가 거절한다."""
-    journal, *_, interactor = _setup()
+    journal, *_, interactor, _ = _setup()
     with pytest.raises(FamilyPetNotFoundError):
         await interactor.register_visit(_command(pet_ids=(999,)))
     assert "create_visits" not in [entry[0] for entry in journal]
 
 
 async def test_같은_시각에_이미_있으면_VISIT_DUPLICATE_다():
-    *_, interactor = _setup()
+    *_, interactor, _ = _setup()
     await interactor.register_visit(_command())
     with pytest.raises(VisitDuplicateError):
         await interactor.register_visit(_command())
 
 
 async def test_경고는_막지_않고_함께_돌려준다():
-    _, _, _, visits, directory, interactor = _setup(
+    _, _, _, visits, directory, interactor, _ = _setup(
         ScheduleSettings(time(10), time(19), 120, frozenset({4})))   # 금요일 휴무
     directory.family(2, pets=(201,))
     visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 13), duration_minutes=120)
@@ -148,6 +151,30 @@ async def test_경고는_막지_않고_함께_돌려준다():
 
 
 async def test_임시_휴무일도_closed_day():
-    _, schedule, *_, interactor = _setup()
+    _, schedule, *_, interactor, _ = _setup()
     schedule.closed[(1, date(2026, 10, 2))] = ClosedDate(day=date(2026, 10, 2), note=None)
     assert (await interactor.register_visit(_command())).warnings == ["closed_day"]
+
+
+async def test_예약마다_VisitReserved_를_넣은_뒤에_발행한다():
+    journal, _, _, _, _, interactor, events = _setup()
+    result = await interactor.register_visit(_command(pet_ids=(101, 102)))
+    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.starts_at, e.occurred_at, e.revived)
+            for e in events.published] == [
+        (VisitReserved, ctx(), v.visit_id, 1, pet_id, kst(10, 2, 14), NOW, False)
+        for v, pet_id in zip(result.visits, (101, 102))]
+    names = [entry[0] for entry in journal]
+    assert names.index("create_visits") < names.index("publish")
+
+
+async def test_지금_시작한_손님은_예약이_아니라_발행하지_않는다():
+    *_, interactor, events = _setup()
+    await interactor.register_visit(_command(starts_at=None, walk_in=True))
+    assert events.published == []
+
+
+async def test_등록이_실패하면_발행하지_않는다():
+    *_, interactor, events = _setup()
+    with pytest.raises(MenuNotAvailableError):
+        await interactor.register_visit(_command(menu_ids=(999,)))
+    assert events.published == []
```

`backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`:

```diff
@@ -1,5 +1,6 @@
 import pytest
 
+from hub.app.dtos.visit_events import VisitRescheduled
 from visit.app.dtos.reschedule_visits_dto import RescheduleVisitsCommand
 from visit.app.use_cases.reschedule_visits_interactor import RescheduleVisitsInteractor
 from visit.domain.errors import (
@@ -11,7 +12,7 @@ from visit.domain.errors import (
     VisitStateConflictError,
 )
 from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, FakeVisits, Journal
+from visit.tests.helpers.fakes import FakeDirectory, FakeEvents, FakeMenus, FakeSchedule, FakeVisits, Journal
 
 NOW = kst(9, 23, 15)
 
@@ -21,8 +22,10 @@ def _setup():
     visits, directory = FakeVisits(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102))
     directory.family(2, pets=(201,))
-    return journal, visits, RescheduleVisitsInteractor(visits, visits, FakeMenus(), FakeSchedule(), directory,
-                                                       now=lambda: NOW)
+    events = FakeEvents(journal)
+    interactor = RescheduleVisitsInteractor(visits, visits, FakeMenus(), FakeSchedule(), directory, events=events,
+                                            now=lambda: NOW)
+    return journal, visits, interactor, events
 
 
 def _move(ids, starts_at=kst(10, 3, 15), shop_id=1):
@@ -30,7 +33,7 @@ def _move(ids, starts_at=kst(10, 3, 15), shop_id=1):
 
 
 async def test_가족_묶음을_함께_옮긴다():
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=90)
     bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=120)
     result = await interactor.reschedule_visits(_move([bori.id, kong.id]))
@@ -43,7 +46,7 @@ async def test_가족_묶음을_함께_옮긴다():
 
 async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
     """V14"""
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
     other = visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 14))
     with pytest.raises(VisitGroupMismatchError):
@@ -52,17 +55,18 @@ async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다(
 
 
 async def test_예약됨이_아닌_방문이_있으면_하나도_옮기지_않는다():
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, events = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 14))
     bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 14), status="in_progress",
                        started_at=kst(9, 23, 14))
     with pytest.raises(VisitStateConflictError):
         await interactor.reschedule_visits(_move([kong.id, bori.id]))
     assert "reschedule" not in [entry[0] for entry in journal]
+    assert events.published == []
 
 
 async def test_가장_긴_소요로_자정_넘김을_본다():
-    _, visits, interactor = _setup()
+    _, visits, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=60)
     bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=180)
     with pytest.raises(VisitCrossesMidnightError):
@@ -70,7 +74,7 @@ async def test_가장_긴_소요로_자정_넘김을_본다():
 
 
 async def test_없는_방문_범위_밖_시각_중복():
-    _, visits, interactor = _setup()
+    _, visits, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
     visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 3, 15))
     with pytest.raises(VisitNotFoundError):
@@ -82,3 +86,16 @@ async def test_없는_방문_범위_밖_시각_중복():
     theirs = visits.seed(customer_id=9, shop_id=2)
     with pytest.raises(VisitNotFoundError):
         await interactor.reschedule_visits(_move([theirs.id]))
+
+
+async def test_옮긴_방문마다_VisitRescheduled_를_옮긴_뒤에_발행한다():
+    journal, visits, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
+    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
+    await interactor.reschedule_visits(_move([bori.id, kong.id]))
+    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.previous_starts_at, e.starts_at, e.occurred_at)
+            for e in events.published] == [
+        (VisitRescheduled, ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 15), NOW),
+        (VisitRescheduled, ctx(), bori.id, 1, 102, kst(10, 2, 14), kst(10, 3, 15), NOW)]
+    names = [entry[0] for entry in journal]
+    assert names.index("reschedule") < names.index("publish")
```

`backend/apps/visit/tests/app/use_cases/test_send_visit_report_interactor.py`:

```diff
@@ -4,6 +4,7 @@ from datetime import timedelta
 import pytest
 
 from hub.app.dtos.shop_profile import ShopProfile
+from hub.app.dtos.visit_events import VisitReportIssued
 from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
 from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
 from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
@@ -21,6 +22,7 @@ from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS
 from visit.tests.helpers.builders import ctx, kst, record
 from visit.tests.helpers.fakes import (
     FakeDirectory,
+    FakeEvents,
     FakeLibrary,
     FakeMenus,
     FakeRecords,
@@ -43,6 +45,7 @@ class _World:
         self.visits, self.settings = FakeVisits(self.journal), FakeReportSettingsRepository()
         self.records = FakeRecords(self.visits, self.journal)
         self.reports = FakeReportRepository(self.visits, self.journal)
+        self.events = FakeEvents(self.journal)
         directory, library = FakeDirectory(self.journal), FakeLibrary()
         directory.family(1, pets=(101,))
         for media_id in (51, 52):
@@ -50,7 +53,7 @@ class _World:
         self.interactor = SendVisitReportInteractor(
             visits=self.visits, records=self.records, settings=self.settings, reports=self.reports,
             menus=FakeMenus(), directory=directory, library=library, shops=FakeShopProfile({1: SHOP}),
-            now=lambda: self.now, link_key=KEY, web_base_url="https://r.example",
+            events=self.events, now=lambda: self.now, link_key=KEY, web_base_url="https://r.example",
         )
         self.revoker = RevokeVisitReportInteractor(self.visits, self.reports, directory, now=lambda: self.now)
 
@@ -98,7 +101,7 @@ async def test_처음_보내면_잠근_뒤_링크를_만들고_기간은_매장
     assert [(m.media_id, m.hidden) for m in sent.report.media] == [(52, True), (51, False)]
     assert (sent.report.cover.url, sent.report.settings.link_days) == ("d/51", link_days)
     assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "close_expired_reports", "create_report",
-                                         "set_hidden"]
+                                         "set_hidden", "publish"]
 
 
 async def test_다시_보내면_같은_링크이고_뺀_사진만_바뀐다():
@@ -205,3 +208,34 @@ async def test_없는_방문과_다른_매장의_방문에는_보낼_수_없다(
         with pytest.raises(VisitNotFoundError):
             await w.send(visit_id, shop_id=1)
     assert w.journal == []
+
+
+async def test_처음_보내면_주소와_기간을_실은_VisitReportIssued_를_발행한다():
+    w = _World()
+    visit = w.completed()
+    sent = await w.send(visit.id)
+    [event] = w.events.published
+    assert isinstance(event, VisitReportIssued)
+    assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.starts_at, event.occurred_at) == (
+        ctx(), visit.id, 1, 101, kst(9, 23, 14), NOW)
+    assert (event.url, event.expires_at) == (sent.link.url, w.reports.rows[0].expires_at)
+
+
+async def test_살아_있는_링크로_다시_보내면_발행하지_않고_끊은_뒤_보내면_다시_발행한다():
+    """알림톡은 링크마다 한 번이다."""
+    w = _World()
+    visit_id = w.completed().id
+    first = await w.send(visit_id)
+    await w.send(visit_id, hidden=(52,))
+    assert [e.url for e in w.events.published] == [first.link.url]
+    await w.revoke(visit_id)
+    second = await w.send(visit_id)
+    assert [e.url for e in w.events.published] == [first.link.url, second.link.url]
+
+
+async def test_빈_알림장이면_발행하지_않는다():
+    w = _World()
+    visit_id = w.completed(care_note=None, hidden=(52,)).id
+    with pytest.raises(ReportEmptyError):
+        await w.send(visit_id, hidden=(51, 52))
+    assert w.events.published == []
```

`backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`:

```diff
@@ -3,6 +3,7 @@ from datetime import timedelta
 
 import pytest
 
+from hub.app.dtos.visit_events import VisitCanceled, VisitClosed, VisitReserved
 from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
 from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
 from visit.domain.errors import (
@@ -15,7 +16,14 @@ from visit.domain.errors import (
 )
 from visit.tests.helpers.builders import ctx, kst
 from hub.app.errors import FamilyPetPassedAwayError
-from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeReportRepository, FakeVisits, Journal
+from visit.tests.helpers.fakes import (
+    FakeDirectory,
+    FakeEvents,
+    FakeMenus,
+    FakeReportRepository,
+    FakeVisits,
+    Journal,
+)
 
 NOW = kst(9, 23, 15)
 
@@ -26,13 +34,15 @@ def _with_reports(visits=None):
     directory.family(1, pets=(101, 102, 103), passed=(103,))
     directory.family(2, pets=(201,))
     reports = FakeReportRepository(visits)
-    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), reports, directory, now=lambda: NOW)
-    return journal, visits, reports, interactor
+    events = FakeEvents(journal)
+    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), reports, directory, events=events,
+                                            now=lambda: NOW)
+    return journal, visits, reports, interactor, events
 
 
 def _setup():
-    journal, visits, _, interactor = _with_reports()
-    return journal, visits, interactor
+    journal, visits, _, interactor, events = _with_reports()
+    return journal, visits, interactor, events
 
 
 def _act(ids, action, reason=None, member_id=11):
@@ -41,20 +51,21 @@ def _act(ids, action, reason=None, member_id=11):
 
 
 async def test_가족_묶음을_한_번에_완료하고_최근_방문을_알린다():
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
     bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
     result = await interactor.transition_visits(_act([kong.id, bori.id], "complete", member_id=12))
     assert [(v.status, v.status_changed_by_member_id) for v in result.visits] == [("completed", 12)] * 2
     assert visits.rows[kong.id].completed_at == NOW
     names = [entry[0] for entry in journal]
-    assert names == ["lock_family", "lock_visits", "apply_changes", "set_last_visit"]
+    assert names == ["lock_family", "lock_visits", "apply_changes", "set_last_visit", "publish", "publish"]
     assert journal[0] == ("lock_family", 1, ())   # 되돌리기가 아니면 보호자만 잠근다
-    assert journal[-1] == ("set_last_visit", 1, kst(9, 23, 13))
+    assert journal[3:] == [("set_last_visit", 1, kst(9, 23, 13)), ("publish", "VisitClosed", kong.id),
+                           ("publish", "VisitClosed", bori.id)]
 
 
 async def test_완료를_되돌리면_최근_방문을_다시_계산한다():
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, _ = _setup()
     visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                 started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
     today = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13), status="completed",
@@ -62,11 +73,11 @@ async def test_완료를_되돌리면_최근_방문을_다시_계산한다():
     await interactor.transition_visits(_act([today.id], "revert"))
     assert visits.rows[today.id].status == "reserved"
     assert journal[0] == ("lock_family", 1, (101,))   # 되돌리기는 아이도 확인한다
-    assert journal[-1] == ("set_last_visit", 1, kst(9, 2, 14))
+    assert journal[-2:] == [("set_last_visit", 1, kst(9, 2, 14)), ("publish", "VisitReserved", today.id)]
 
 
 async def test_완료와_상관없는_전이는_최근_방문을_건드리지_않는다():
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
     await interactor.transition_visits(_act([kong.id], "cancel", "customer_request"))
     assert "set_last_visit" not in [entry[0] for entry in journal]
@@ -75,7 +86,7 @@ async def test_완료와_상관없는_전이는_최근_방문을_건드리지_
 
 async def test_하나라도_안_되면_아무것도_바꾸지_않는다():
     """V6 — 미용 중과 예약됨이 섞인 묶음에 '시작'을 누르면 둘 다 그대로다."""
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, events = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
     bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13), status="in_progress",
                        started_at=kst(9, 23, 13))
@@ -83,10 +94,11 @@ async def test_하나라도_안_되면_아무것도_바꾸지_않는다():
         await interactor.transition_visits(_act([kong.id, bori.id], "start"))
     assert (visits.rows[kong.id].status, visits.rows[bori.id].status) == ("reserved", "in_progress")
     assert "apply_changes" not in [entry[0] for entry in journal]
+    assert events.published == []
 
 
 async def test_상태_규칙은_도메인이_정한다():
-    _, visits, interactor = _setup()
+    _, visits, interactor, _ = _setup()
     tomorrow = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 24, 10))
     with pytest.raises(VisitNotYetError):
         await interactor.transition_visits(_act([tomorrow.id], "start"))
@@ -99,7 +111,7 @@ async def test_상태_규칙은_도메인이_정한다():
 
 async def test_무지개다리_아이의_방문은_되돌리지_못한다():
     """V7 — 되돌리면 다시 앞으로의 예약이 된다."""
-    _, visits, interactor = _setup()
+    _, visits, interactor, _ = _setup()
     canceled = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 30, 14), status="canceled",
                            canceled_at=NOW, cancel_reason="shop_reason")
     with pytest.raises(FamilyPetPassedAwayError):
@@ -107,7 +119,7 @@ async def test_무지개다리_아이의_방문은_되돌리지_못한다():
 
 
 async def test_되돌린_자리에_이미_새_예약이_있으면_VISIT_DUPLICATE_다():
-    _, visits, interactor = _setup()
+    _, visits, interactor, _ = _setup()
     canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled",
                            canceled_at=NOW, cancel_reason="customer_request")
     visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14))
@@ -116,7 +128,7 @@ async def test_되돌린_자리에_이미_새_예약이_있으면_VISIT_DUPLICAT
 
 
 async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
-    journal, visits, interactor = _setup()
+    journal, visits, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
     other = visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 13))
     with pytest.raises(VisitGroupMismatchError):
@@ -147,7 +159,7 @@ async def test_되돌리기_잠그는_사이_반려동물이_바뀌면_다시_
                            canceled_at=NOW, cancel_reason="customer_request")
     visits._swap_visit_id = canceled.id
     interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), FakeReportRepository(visits), directory,
-                                            now=lambda: NOW)
+                                            events=FakeEvents(journal), now=lambda: NOW)
     with pytest.raises(VisitStateConflictError):
         await interactor.transition_visits(_act([canceled.id], "revert"))
 
@@ -163,7 +175,7 @@ async def _send(reports, visit_id, expires_at=NOW + timedelta(days=7)):
 
 
 async def test_알림장을_보낸_완료_방문은_되돌릴_수_없다():
-    journal, visits, reports, interactor = _with_reports()
+    journal, visits, reports, interactor, _ = _with_reports()
     sent = _done(visits)
     await _send(reports, sent.id)
     with pytest.raises(VisitReportSentError):
@@ -173,7 +185,7 @@ async def test_알림장을_보낸_완료_방문은_되돌릴_수_없다():
 
 
 async def test_링크를_끊으면_되돌려진다():
-    _, visits, reports, interactor = _with_reports()
+    _, visits, reports, interactor, _ = _with_reports()
     sent = _done(visits)
     await _send(reports, sent.id)
     await reports.revoke(ctx(), sent.id, NOW)
@@ -182,7 +194,7 @@ async def test_링크를_끊으면_되돌려진다():
 
 
 async def test_링크의_기간이_지나면_되돌려진다():
-    _, visits, reports, interactor = _with_reports()
+    _, visits, reports, interactor, _ = _with_reports()
     sent = _done(visits)
     await _send(reports, sent.id, expires_at=NOW)   # 지금 끝난다
     await interactor.transition_visits(_act([sent.id], "revert"))
@@ -190,7 +202,7 @@ async def test_링크의_기간이_지나면_되돌려진다():
 
 
 async def test_함께_되돌리는_방문_하나에_알림장이_있으면_둘_다_그대로다():
-    journal, visits, reports, interactor = _with_reports()
+    journal, visits, reports, interactor, _ = _with_reports()
     kong, bori = _done(visits), _done(visits, pet_id=102)
     await _send(reports, bori.id)
     with pytest.raises(VisitReportSentError):
@@ -212,9 +224,68 @@ class _SentWhileLocking(FakeVisits):
 
 async def test_알림장을_보냈는지는_잠근_뒤에_읽는다():
     """R9 — 잠그기 전에 읽으면 '링크 없음'을 보고 되돌려 버린다."""
-    _, visits, reports, interactor = _with_reports(_SentWhileLocking())
+    _, visits, reports, interactor, _ = _with_reports(_SentWhileLocking())
     visits.reports = reports
     sent = _done(visits)
     with pytest.raises(VisitReportSentError):
         await interactor.transition_visits(_act([sent.id], "revert"))
     assert visits.rows[sent.id].status == "completed"
+
+
+def _completed(visits, pet_id, month, day, customer_id=1):
+    return visits.seed(customer_id=customer_id, pet_id=pet_id, starts_at=kst(month, day, 14), status="completed",
+                       started_at=kst(month, day, 14), completed_at=kst(month, day, 15))
+
+
+async def test_취소는_사유를_실은_VisitCanceled_를_발행한다():
+    _, visits, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
+    await interactor.transition_visits(_act([kong.id], "cancel", "shop_reason"))
+    [event] = events.published
+    assert isinstance(event, VisitCanceled)
+    assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.starts_at, event.occurred_at,
+            event.reason) == (ctx(), kong.id, 1, 101, kst(9, 23, 13), NOW, "shop_reason")
+
+
+async def test_완료는_같은_아이의_앞선_완료_시작_시각을_실은_VisitClosed_를_발행한다():
+    """자기 자신은 빼고, 다른 아이·취소는 세지 않고, 보호자만 방문은 보호자만 방문끼리."""
+    _, visits, interactor, events = _setup()
+    _completed(visits, 101, 8, 1)
+    _completed(visits, 101, 9, 2)
+    _completed(visits, 102, 9, 10)
+    _completed(visits, None, 9, 12)
+    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 20, 14), status="canceled", canceled_at=NOW,
+                cancel_reason="shop_reason")
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
+    alone = visits.seed(customer_id=1, pet_id=None, starts_at=kst(9, 23, 13))
+    first = visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 13))
+    await interactor.transition_visits(_act([kong.id, alone.id], "complete"))
+    await interactor.transition_visits(_act([first.id], "complete"))
+    assert [(type(e), e.visit_id, e.customer_id, e.pet_id, e.outcome, e.previous_completed_at, e.occurred_at)
+            for e in events.published] == [
+        (VisitClosed, kong.id, 1, 101, "completed", kst(9, 2, 14), NOW),
+        (VisitClosed, alone.id, 1, None, "completed", kst(9, 12, 14), NOW),
+        (VisitClosed, first.id, 2, 201, "completed", None, NOW)]
+
+
+async def test_노쇼는_앞선_완료_없이_VisitClosed_를_발행한다():
+    _, visits, interactor, events = _setup()
+    _completed(visits, 101, 9, 2)
+    past = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 10))
+    await interactor.transition_visits(_act([past.id], "no_show"))
+    [event] = events.published
+    assert (type(event), event.visit_id, event.outcome, event.previous_completed_at) == (
+        VisitClosed, past.id, "no_show", None)
+
+
+async def test_되돌리기는_revived_인_VisitReserved_를_발행하고_시작은_발행하지_않는다():
+    _, visits, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
+    await interactor.transition_visits(_act([kong.id], "start"))
+    assert events.published == []
+    canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled", canceled_at=NOW,
+                           cancel_reason="customer_request")
+    await interactor.transition_visits(_act([canceled.id], "revert"))
+    [event] = events.published
+    assert (type(event), event.visit_id, event.starts_at, event.revived) == (
+        VisitReserved, canceled.id, kst(9, 30, 14), True)
```

`backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`:

```diff
@@ -1,5 +1,6 @@
 import pytest
 
+from hub.app.dtos.visit_events import VisitRescheduled
 from hub.app.errors import FamilyPetNotFoundError
 from visit.app.dtos.update_visit_dto import UpdateVisitCommand
 from visit.app.use_cases.update_visit_interactor import UpdateVisitInteractor
@@ -13,6 +14,7 @@ from visit.domain.errors import (
 from visit.tests.helpers.builders import ctx, kst
 from visit.tests.helpers.fakes import (
     FakeDirectory,
+    FakeEvents,
     FakeMenus,
     FakeSchedule,
     FakeVisits,
@@ -27,8 +29,10 @@ def _setup():
     visits, menus, directory = FakeVisits(journal), FakeMenus(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102, 103), passed=(103,))
     directory.family(2, pets=(201,))
-    interactor = UpdateVisitInteractor(visits, visits, menus, FakeSchedule(), directory, now=lambda: NOW)
-    return journal, visits, menus, interactor
+    events = FakeEvents(journal)
+    interactor = UpdateVisitInteractor(visits, visits, menus, FakeSchedule(), directory, events=events,
+                                       now=lambda: NOW)
+    return journal, visits, menus, interactor, events
 
 
 def _command(visit, **overrides):
@@ -39,7 +43,7 @@ def _command(visit, **overrides):
 
 
 async def test_예약은_시간과_아이와_메뉴를_바꾼다():
-    journal, visits, menus, interactor = _setup()
+    journal, visits, menus, interactor, _ = _setup()
     bath = menus.seed("목욕")
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
     result = await interactor.update_visit(_command(
@@ -55,7 +59,7 @@ async def test_예약은_시간과_아이와_메뉴를_바꾼다():
 
 async def test_다른_보호자의_아이로는_바꾸지_못한다():
     """V13 — 반려동물은 같은 보호자의 아이로만. 가족 확인이 거절한다."""
-    journal, visits, _, interactor = _setup()
+    journal, visits, _, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
     with pytest.raises(FamilyPetNotFoundError):
         await interactor.update_visit(_command(kong, pet_id=201))
@@ -63,7 +67,7 @@ async def test_다른_보호자의_아이로는_바꾸지_못한다():
 
 
 async def test_완료한_방문은_메모와_메뉴만_고친다():
-    _, visits, menus, interactor = _setup()
+    _, visits, menus, interactor, _ = _setup()
     bath = menus.seed("목욕")
     done = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 2, 14), status="completed",
                        started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))   # 그 뒤 무지개다리를 건넌 아이
@@ -75,7 +79,7 @@ async def test_완료한_방문은_메모와_메뉴만_고친다():
 
 
 async def test_이미_붙은_메뉴는_보관됐어도_둘_수_있다():
-    _, visits, menus, interactor = _setup()
+    _, visits, menus, interactor, _ = _setup()
     old = menus.seed("옛 메뉴", archived=True)
     other_old = menus.seed("다른 옛 메뉴", archived=True)
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), menu_ids=(old.id,))
@@ -85,7 +89,7 @@ async def test_이미_붙은_메뉴는_보관됐어도_둘_수_있다():
 
 
 async def test_시각_규칙과_중복():
-    _, visits, _, interactor = _setup()
+    _, visits, _, interactor, _ = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
     visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 9, 14))
     with pytest.raises(VisitCrossesMidnightError):
@@ -95,15 +99,43 @@ async def test_시각_규칙과_중복():
 
 
 async def test_다른_매장의_방문은_VISIT_NOT_FOUND_다():
-    _, visits, _, interactor = _setup()
+    _, visits, _, interactor, _ = _setup()
     theirs = visits.seed(shop_id=2)
     with pytest.raises(VisitNotFoundError):
         await interactor.update_visit(_command(theirs))
 
 
 async def test_경고를_함께_돌려준다():
-    _, visits, _, interactor = _setup()
+    _, visits, _, interactor, _ = _setup()
     visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 11))
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
     result = await interactor.update_visit(_command(kong, starts_at=kst(10, 2, 11)))
     assert result.warnings == ["overlap"]
+
+
+async def test_시각을_바꾸면_전후_시각을_실은_VisitRescheduled_를_쓴_뒤에_발행한다():
+    journal, visits, _, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
+    await interactor.update_visit(_command(kong, starts_at=kst(10, 3, 11)))
+    [event] = events.published
+    assert isinstance(event, VisitRescheduled)
+    assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.previous_starts_at, event.starts_at,
+            event.occurred_at) == (ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 11), NOW)
+    names = [entry[0] for entry in journal]
+    assert names.index("update_visit") < names.index("publish")
+
+
+async def test_메모만_바꾸면_발행하지_않는다():
+    _, visits, _, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
+    await interactor.update_visit(_command(kong, pet_id=102, memo="발톱"))
+    assert events.published == []
+
+
+async def test_수정이_실패하면_발행하지_않는다():
+    _, visits, _, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
+    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 9, 14))
+    with pytest.raises(VisitDuplicateError):
+        await interactor.update_visit(_command(kong, starts_at=kst(10, 9, 14)))
+    assert events.published == []
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -12,6 +12,7 @@ from hub.app.dtos.customer_contact import CustomerContact
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from hub.app.dtos.media_urls import MediaUrls
 from hub.app.dtos.shop_profile import ShopProfile
+from hub.app.dtos.visit_events import VisitEvent
 from hub.app.errors import (
     FamilyNotFoundError,
     FamilyPetNotFoundError,
@@ -21,6 +22,7 @@ from hub.app.errors import (
     MediaClaimNotReadyError,
 )
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.app.dtos.report_target_dto import ReportTarget
@@ -299,6 +301,11 @@ class FakeVisits(
         done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.status == "completed"]
         return max(done) if done else None
 
+    async def latest_completed_start_excluding(self, ctx, customer_id, pet_id, exclude_visit_id):
+        done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
+                and v.status == "completed" and v.id != exclude_visit_id]
+        return max(done) if done else None
+
     async def list_group(self, ctx, customer_id, starts_at):
         return [v for v in self._mine(ctx) if v.customer_id == customer_id and v.starts_at == starts_at]
 
@@ -573,3 +580,15 @@ class FakeShopProfile(ShopProfilePort):
 
     async def public_profile(self, shop_id):
         return self.shops.get(shop_id)
+
+
+class FakeEvents(DomainEventPort):
+    """DomainEventPort 스텁 — 발행한 이벤트를 published 에 순서대로 모은다. journal 에는 ("publish", 종류, 방문 ID)."""
+
+    def __init__(self, journal: Journal | None = None) -> None:
+        self.journal = journal if journal is not None else Journal()
+        self.published: list[VisitEvent] = []
+
+    async def publish(self, event):
+        self.published.append(event)
+        self.journal.append(("publish", type(event).__name__, event.visit_id))
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -1,6 +1,7 @@
 """공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
 from hub.app.dtos.shop_profile import ShopProfile
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.tests.helpers.builders import ctx
@@ -19,6 +20,7 @@ from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.tests.helpers.fakes import (
     FakeDirectory,
+    FakeEvents,
     FakeLibrary,
     FakeMenus,
     FakePublicReportLimiter,
@@ -37,6 +39,7 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     assert isinstance(FakeDirectory(), CustomerDirectoryPort)
     assert isinstance(FakeLibrary(), MediaLibraryPort)
     assert isinstance(FakeShopProfile(), ShopProfilePort)
+    assert isinstance(FakeEvents(), DomainEventPort)
     visits = FakeVisits()
     for port in (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
                  VisitBoardRepository, VisitFeedRepository):
```

`backend/tests/integration/test_visit_events_wiring.py`:

```python
"""visit 이 발행한 이벤트가 실제 배선(main.py 의 버스 꽂기, 요청의 세션)으로 구독자에 닿는지 확인한다.

구독자가 던지면 요청은 500 이고 방문 저장도 롤백된다(설계 5.1, N13).
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.observer.in_process_event_bus import clear_subscribers, subscribe
from hub.app.dtos.visit_events import VisitCanceled, VisitRescheduled, VisitReserved
from tests.integration.support import bearer, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _at(days: int, hour: int) -> str:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


@pytest.fixture
def received():
    """구독자 하나를 실제 버스에 등록해 받은 (세션, 이벤트)를 모은다. 끝나면 구독자 목록을 비운다."""
    events = []

    async def collect(session, event):
        await session.execute(text("SELECT 1"))   # 요청의 세션이 그대로 넘어온다
        events.append(event)

    subscribe(collect)
    yield events
    clear_subscribers()


async def _shop(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    return shop_id, headers, body["customer"]["customer_id"], body["pets"][0]["pet_id"]


def _booking(customer_id, pet_id, starts_at):
    return {"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": starts_at}


async def test_등록_수정_취소가_순서대로_이벤트로_닿는다(wired, received):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", json=_booking(customer_id, pet_id, _at(3, 14)),
                                  headers=headers)
    assert booked.status_code == 201, booked.text
    visit = booked.json()["visits"][0]
    visit_id = visit["visit_id"]
    moved = await wired.api.put(
        f"/v1/shops/{shop_id}/visits/{visit_id}",
        json={"starts_at": _at(3, 16), "pet_id": pet_id, "duration_minutes": visit["duration_minutes"],
              "menu_ids": [], "memo": None},
        headers=headers,
    )
    assert moved.status_code == 200, moved.text
    canceled = await wired.api.post(
        f"/v1/shops/{shop_id}/visits/transitions",
        json={"visit_ids": [visit_id], "action": "cancel", "cancel_reason": "shop_reason"}, headers=headers)
    assert canceled.status_code == 200, canceled.text

    assert [type(e) for e in received] == [VisitReserved, VisitRescheduled, VisitCanceled]
    assert {(e.ctx.shop_id, e.visit_id, e.customer_id, e.pet_id) for e in received} == {
        (shop_id, visit_id, customer_id, pet_id)}
    assert received[1].previous_starts_at == received[0].starts_at
    assert received[1].starts_at == received[2].starts_at == datetime.fromisoformat(_at(3, 16))
    assert received[2].reason == "shop_reason"


async def test_구독자가_던지면_500_이고_방문은_생기지_않는다(wired):
    """N13 — 구독자는 발행한 요청과 같은 트랜잭션이다. 실패하면 방문 저장도 롤백된다."""
    import main

    async def explode(session, event):
        raise RuntimeError("구독자 실패")

    subscribe(explode)
    try:
        shop_id, headers, customer_id, pet_id = await _shop(wired)
        async with AsyncClient(transport=ASGITransport(app=main.app, raise_app_exceptions=False),
                               base_url="http://api") as api:
            booked = await api.post(f"/v1/shops/{shop_id}/visits", json=_booking(customer_id, pet_id, _at(3, 14)),
                                    headers=headers)
        assert booked.status_code == 500
    finally:
        clear_subscribers()
    day = (datetime.now(SEOUL).date() + timedelta(days=3)).isoformat()
    listed = await wired.api.get(f"/v1/shops/{shop_id}/visits?date={day}", headers=headers)
    assert listed.status_code == 200 and listed.json()["items"] == []
```

`backend/tests/integration/test_visit_locking.py`:

```diff
@@ -28,6 +28,7 @@ from visit.app.dtos.register_visit_dto import RegisterVisitCommand
 from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
 from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
 from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
+from visit.tests.helpers.fakes import FakeEvents
 from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
 from visit.domain.errors import VisitDuplicateError, VisitStateConflictError
 from visit.tests.helpers.builders import ctx, kst
@@ -50,7 +51,7 @@ def _register(session, customer_id, pet_ids, starts_at=kst(10, 2, 14)):
     visits = VisitPgRepository(session)
     interactor = RegisterVisitInteractor(
         visits, visits, MenuPgRepository(session), SchedulePgRepository(session),
-        _directory(session), now=lambda: NOW,
+        _directory(session), events=FakeEvents(), now=lambda: NOW,
     )
     return interactor.register_visit(RegisterVisitCommand(
         ctx=SHOP, customer_id=customer_id, pet_ids=tuple(pet_ids), starts_at=starts_at, duration_minutes=None,
@@ -62,7 +63,7 @@ def _transition(session, visit_ids, action, reason=None):
     visits = VisitPgRepository(session)
     interactor = TransitionVisitsInteractor(
         visits, visits, MenuPgRepository(session), ReportPgRepository(session), _directory(session),
-        now=lambda: NOW,
+        events=FakeEvents(), now=lambda: NOW,
     )
     return interactor.transition_visits(TransitionVisitsCommand(
         ctx=SHOP, visit_ids=tuple(visit_ids), action=action, cancel_reason=reason,
```

`backend/tests/integration/test_visit_report_locking.py`:

```diff
@@ -30,7 +30,7 @@ from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInte
 from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
 from visit.domain.errors import VisitNotCompletedError, VisitReportSentError
 from visit.tests.helpers.builders import ctx, kst, record
-from visit.tests.helpers.fakes import FakeShopProfile
+from visit.tests.helpers.fakes import FakeEvents, FakeShopProfile
 from visit.tests.helpers.rows import insert_visit
 
 pytestmark = pytest.mark.integration
@@ -58,7 +58,7 @@ def _send(session):
         visits=VisitPgRepository(session), records=VisitRecordPgRepository(session),
         settings=ReportSettingsPgRepository(session), reports=ReportPgRepository(session),
         menus=MenuPgRepository(session), directory=_directory(session), library=_library(session),
-        shops=FakeShopProfile({1: PROFILE}), now=_now, link_key=bytes(range(32)),
+        shops=FakeShopProfile({1: PROFILE}), events=FakeEvents(), now=_now, link_key=bytes(range(32)),
         web_base_url="https://r.example",
     )
 
@@ -66,7 +66,8 @@ def _send(session):
 def _revert(session, visit_id):
     visits = VisitPgRepository(session)
     return TransitionVisitsInteractor(
-        visits, visits, MenuPgRepository(session), ReportPgRepository(session), _directory(session), now=_now,
+        visits, visits, MenuPgRepository(session), ReportPgRepository(session), _directory(session),
+        events=FakeEvents(), now=_now,
     ).transition_visits(TransitionVisitsCommand(ctx=SHOP, visit_ids=(visit_id,), action="revert",
                                                 cancel_reason=None))
```

`backend/tests/test_hub_port_binding.py`:

```diff
@@ -3,13 +3,14 @@ import pytest
 from fastapi import Depends, FastAPI
 
 import main
+from core.observer.in_process_event_bus import get_event_bus
 from core.shop_guard import get_shop_access_port
 from tenancy.dependencies.hub_ports import get_user_directory
 from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
 from core.security import get_current_user_id
 from core.shop_guard import get_shop_context
 from tests.route_inspection import find_route_violations, routes_without_login
-from visit.dependencies.hub_ports import get_shop_profile
+from visit.dependencies.hub_ports import get_domain_events, get_shop_profile
 
 
 def test_API_프로세스에는_빈_자리도_빠진_가드도_없다():
@@ -32,6 +33,12 @@ def test_매장_공개_정보_자리는_tenancy_의_구현으로_채운다():
         get_shop_profile()
 
 
+def test_도메인_이벤트_자리는_core_의_버스로_채운다():
+    assert main.app.dependency_overrides[get_domain_events] is get_event_bus
+    with pytest.raises(RuntimeError):
+        get_domain_events()
+
+
 def _app_with(path, dependency=None):
     app = FastAPI()
     deps = [Depends(dependency)] if dependency else []
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

단위(`--no-deps`, 인터랙터 테스트 다섯 + `test_fakes_are_ports` + `test_hub_port_binding`):
→ `test_hub_port_binding.py` 수집 오류 `ImportError: cannot import name 'get_domain_events'`; 나머지 76 failed, 3 passed — `TypeError: …Interactor.__init__() got an unexpected keyword argument 'events'` (다섯 인터랙터 모두).

통합(`test_visit_pg_repository.py` + `test_visit_events_wiring.py`): 3 failed, 17 passed — `AttributeError: 'VisitPgRepository' object has no attribute 'latest_completed_start_excluding'`, `assert [] == [VisitReserved, VisitRescheduled, VisitCanceled]`(이벤트가 안 닿음), `assert 201 == 500`(구독자가 던져도 방문이 생김).

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/dtos/visit_events.py`:

```diff
@@ -36,6 +36,7 @@ class VisitCanceled(VisitEvent):
 @dataclass(frozen=True)
 class VisitClosed(VisitEvent):
     outcome: str              # "completed" | "no_show"
+    previous_completed_at: datetime | None   # 완료일 때 같은 아이(보호자만이면 보호자만 방문)의 앞선 완료 방문 시작 시각. 노쇼는 None
 
 
 @dataclass(frozen=True)
```

`backend/apps/visit/dependencies/hub_ports.py`:

```diff
@@ -5,6 +5,7 @@
 from __future__ import annotations
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
 
@@ -13,6 +14,10 @@ def get_customer_directory() -> CustomerDirectoryPort:
     raise RuntimeError("CustomerDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
 
 
+def get_domain_events() -> DomainEventPort:
+    raise RuntimeError("DomainEventPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
+
+
 def get_media_library() -> MediaLibraryPort:
     raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`:

```diff
@@ -153,6 +153,19 @@ class VisitPgRepository(
             )
         ).scalar_one()
 
+    async def latest_completed_start_excluding(
+        self, ctx: ShopContext, customer_id: int, pet_id: int | None, exclude_visit_id: int
+    ) -> datetime | None:
+        whose = VisitOrm.pet_id == pet_id if pet_id is not None else VisitOrm.pet_id.is_(None)
+        return (
+            await self._session.execute(
+                select(func.max(VisitOrm.starts_at)).where(
+                    VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id, whose,
+                    VisitOrm.status == COMPLETED, VisitOrm.id != exclude_visit_id,
+                )
+            )
+        ).scalar_one()
+
     async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
         return await self._read(
             ctx, select(VisitOrm).where(VisitOrm.customer_id == customer_id, VisitOrm.starts_at == starts_at)
```

`backend/apps/visit/app/ports/output/visit_history_repository.py`:

```diff
@@ -17,6 +17,13 @@ class VisitHistoryRepository(ABC):
     async def latest_completed_start(self, ctx: ShopContext, customer_id: int) -> datetime | None:
         """그 보호자의 마지막 완료 방문의 시작 시각 — 고객 목록 '최근 방문순'의 원본."""
 
+    @abstractmethod
+    async def latest_completed_start_excluding(
+        self, ctx: ShopContext, customer_id: int, pet_id: int | None, exclude_visit_id: int
+    ) -> datetime | None:
+        """exclude_visit_id 를 뺀, 그 아이(pet_id 가 None 이면 보호자만의 방문)의 가장 최근 완료 방문 시작 시각 —
+        완료 이벤트의 '지난 방문 간격'의 원본."""
+
     @abstractmethod
     async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
         """같은 가족 묶음(같은 보호자 + 같은 시작 시각)의 방문 — 상태와 상관없이."""
```

`backend/apps/visit/app/use_cases/register_visit_interactor.py`:

```diff
@@ -3,7 +3,9 @@ from __future__ import annotations
 from collections.abc import Callable
 from datetime import datetime
 
+from hub.app.dtos.visit_events import VisitReserved
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.dtos.register_visit_dto import RegisteredVisitsView, RegisterVisitCommand
 from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
@@ -27,13 +29,15 @@ from visit.domain.value_objects.new_visit import NewVisit
 class RegisterVisitInteractor(RegisterVisitUseCase):
     def __init__(
         self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
-        schedule: ScheduleRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        schedule: ScheduleRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
+        now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
         self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
+        self._events = events
         self._now = now
 
     async def register_visit(self, command: RegisterVisitCommand) -> RegisteredVisitsView:
@@ -66,6 +70,12 @@ class RegisterVisitInteractor(RegisterVisitUseCase):
                 for pet_id in (command.pet_ids or (None,))
             ],
         )
+        # 예약만 알린다 — '지금 시작'은 미용 중으로 시작하니 예약이 아니다.
+        if status == RESERVED:
+            for visit in created:
+                await self._events.publish(VisitReserved(
+                    ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
+                    starts_at=visit.starts_at, occurred_at=now))
 
         warnings = await warnings_after_save(
             ctx, command.customer_id, starts_at, duration, settings, self._board, self._schedule
```

`backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`:

```diff
@@ -3,7 +3,9 @@ from __future__ import annotations
 from collections.abc import Callable
 from datetime import datetime
 
+from hub.app.dtos.visit_events import VisitRescheduled
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, RescheduleVisitsCommand
 from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
@@ -21,24 +23,31 @@ from visit.domain.services.visit_schedule import check_same_day, check_start
 class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
     def __init__(
         self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
-        schedule: ScheduleRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        schedule: ScheduleRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
+        now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
         self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
+        self._events = events
         self._now = now
 
     async def reschedule_visits(self, command: RescheduleVisitsCommand) -> RescheduledVisitsView:
-        ctx, tz = command.ctx, command.ctx.timezone
-        check_start(command.starts_at, self._now(), tz)
+        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
+        check_start(command.starts_at, now, tz)
         locked = await lock_visits(ctx, list(command.visit_ids), self._visits, self._directory)
         if any(v.status != RESERVED for v in locked):
             raise VisitStateConflictError("예약됨인 방문만 옮길 수 있습니다.")
         longest = max(v.duration_minutes for v in locked)
         check_same_day(command.starts_at, longest, tz)
         moved = await self._visits.reschedule(ctx, [v.id for v in locked], command.starts_at)
+        previous = {v.id: v.starts_at for v in locked}
+        for visit in moved:
+            await self._events.publish(VisitRescheduled(
+                ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
+                starts_at=visit.starts_at, occurred_at=now, previous_starts_at=previous[visit.id]))
         settings = await self._schedule.ensure(ctx)
         warnings = await warnings_after_save(
             ctx, locked[0].customer_id, command.starts_at, longest, settings, self._board, self._schedule
```

`backend/apps/visit/app/use_cases/send_visit_report_interactor.py`:

```diff
@@ -4,7 +4,9 @@ from collections.abc import Callable
 from datetime import datetime
 from zoneinfo import ZoneInfo
 
+from hub.app.dtos.visit_events import VisitReportIssued
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.app.dtos.get_visit_report_dto import VisitReportPreview
@@ -27,13 +29,14 @@ class SendVisitReportInteractor(SendVisitReportUseCase):
     처음 보내기·다시 공유·보낸 뒤 사진 빼기를 함께 맡는다. 같은 본문으로 다시 불러도 같은 링크다.
     고객 행 → 방문 행을 잠근 뒤에 링크를 읽으므로 동시에 두 번 보내도 링크는 하나다. 기간이 지난 줄은
     먼저 닫아야 새 줄을 만들 수 있다(끊지 않은 줄은 방문에 하나). 검사는 링크·뺀 표시를 쓰기 전에 끝낸다.
+    새 링크를 만들었을 때만 알린다 — 알림톡은 링크마다 한 번이다(설계 5.2).
     """
 
     def __init__(
         self, visits: VisitLookupRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
         reports: ReportRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
-        library: MediaLibraryPort, shops: ShopProfilePort, now: Callable[[], datetime], link_key: bytes,
-        web_base_url: str,
+        library: MediaLibraryPort, shops: ShopProfilePort, events: DomainEventPort, now: Callable[[], datetime],
+        link_key: bytes, web_base_url: str,
     ) -> None:
         self._visits = visits
         self._records = records
@@ -43,6 +46,7 @@ class SendVisitReportInteractor(SendVisitReportUseCase):
         self._directory = directory
         self._library = library
         self._shops = shops
+        self._events = events
         self._now = now
         self._link_key = link_key
         self._web_base_url = web_base_url
@@ -56,7 +60,8 @@ class SendVisitReportInteractor(SendVisitReportUseCase):
 
         await self._reports.close_expired(ctx, visit.id, now)
         live = await self._reports.get_live(ctx, visit.id, now)
-        if live is None:
+        issued = live is None
+        if issued:
             check_not_empty(record, hidden_ids)
             live = await self._reports.create(
                 ctx, visit.id, new_public_id(), expires_at_for(now, settings.link_days), now)
@@ -68,4 +73,8 @@ class SendVisitReportInteractor(SendVisitReportUseCase):
             include_hidden=True,
         )
         link = describe_link(live, self._link_key, self._web_base_url)
+        if issued:
+            await self._events.publish(VisitReportIssued(
+                ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
+                starts_at=visit.starts_at, occurred_at=now, url=link.url, expires_at=live.expires_at))
         return VisitReportPreview(report=report, link=link.in_zone(ZoneInfo(ctx.timezone)))
```

`backend/apps/visit/app/use_cases/transition_visits_interactor.py`:

```diff
@@ -4,7 +4,10 @@ from collections.abc import Callable
 from dataclasses import replace
 from datetime import datetime
 
+from hub.app.dtos.shop_context import ShopContext
+from hub.app.dtos.visit_events import VisitCanceled, VisitClosed, VisitEvent, VisitReserved
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand
 from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
@@ -14,22 +17,25 @@ from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.app.services.completion_effects import apply_completion_effects
 from visit.app.services.visit_locking import lock_visits
 from visit.app.services.visit_reader import describe_visits
+from visit.domain.entities.visit import Visit
 from visit.domain.errors import VisitStateConflictError
 from visit.domain.state.visit_state import pets_to_confirm, transition
 
 
 class TransitionVisitsInteractor(TransitionVisitsUseCase):
-    """잠그고 → 전이하고 → 후속 처리를 부른다. 어느 행동이 무엇을 확인하는지는 도메인(`visit_state`)이 정한다."""
+    """잠그고 → 전이하고 → 후속 처리를 부르고 → 이벤트를 발행한다. 어느 행동이 무엇을 확인하는지는 도메인(`visit_state`)이 정한다."""
 
     def __init__(
         self, visits: VisitWriteRepository, history: VisitHistoryRepository, menus: MenuRepository,
-        reports: ReportRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        reports: ReportRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
+        now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
         self._history = history
         self._menus = menus
         self._reports = reports
         self._directory = directory
+        self._events = events
         self._now = now
 
     async def transition_visits(self, command: TransitionVisitsCommand) -> TransitionedVisitsView:
@@ -50,6 +56,29 @@ class TransitionVisitsInteractor(TransitionVisitsUseCase):
         changes = [(v.id, transition(v, command.action, now, ctx.timezone, command.cancel_reason)) for v in locked]
         changed = await self._visits.apply_changes(ctx, changes, ctx.member_id)
         await apply_completion_effects(ctx, locked, changed, self._history, self._directory)
+        # 쓰기가 다 끝난 뒤에 알린다 — 구독자가 던지면 전이도 함께 롤백된다(설계 5.1, N13).
+        for visit in changed:
+            event = await self._event_for(ctx, command.action, command.cancel_reason, visit, now)
+            if event is not None:
+                await self._events.publish(event)
         return TransitionedVisitsView(
             visits=await describe_visits(ctx, changed, self._directory, self._menus)
         )
+
+    async def _event_for(
+        self, ctx: ShopContext, action: str, cancel_reason: str | None, visit: Visit, now: datetime
+    ) -> VisitEvent | None:
+        """행동마다 알릴 사실. 시작은 알릴 것이 없다. 되돌리기의 결과는 늘 예약됨이다(`VisitState.revert`)."""
+        common = dict(ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
+                      starts_at=visit.starts_at, occurred_at=now)
+        if action == "cancel":
+            return VisitCanceled(**common, reason=cancel_reason)
+        if action == "complete":
+            previous = await self._history.latest_completed_start_excluding(
+                ctx, visit.customer_id, visit.pet_id, visit.id)
+            return VisitClosed(**common, outcome="completed", previous_completed_at=previous)
+        if action == "no_show":
+            return VisitClosed(**common, outcome="no_show", previous_completed_at=None)
+        if action == "revert":
+            return VisitReserved(**common, revived=True)
+        return None
```

`backend/apps/visit/app/use_cases/update_visit_interactor.py`:

```diff
@@ -3,7 +3,9 @@ from __future__ import annotations
 from collections.abc import Callable
 from datetime import datetime
 
+from hub.app.dtos.visit_events import VisitRescheduled
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.dtos.update_visit_dto import UpdatedVisitView, UpdateVisitCommand
 from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
@@ -21,17 +23,19 @@ from visit.domain.services.visit_schedule import check_duration, check_same_day,
 class UpdateVisitInteractor(UpdateVisitUseCase):
     def __init__(
         self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
-        schedule: ScheduleRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        schedule: ScheduleRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
+        now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
         self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
+        self._events = events
         self._now = now
 
     async def update_visit(self, command: UpdateVisitCommand) -> UpdatedVisitView:
-        ctx, tz = command.ctx, command.ctx.timezone
+        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
         check_duration(command.duration_minutes)
         # 새로 고른 아이만 가족 확인에 넘긴다(같은 보호자의 아이인지, 무지개다리가 아닌지 — V13).
         # 그대로인 아이는 넘기지 않는다 — 완료한 방문의 아이가 나중에 무지개다리를 건넜어도 메모는 고친다.
@@ -46,7 +50,7 @@ class UpdateVisitInteractor(UpdateVisitUseCase):
         if moved and current.status != RESERVED:
             raise VisitStateConflictError("날짜·시간·반려동물은 예약됨일 때만 바꿀 수 있습니다.")
         if command.starts_at != current.starts_at:
-            check_start(command.starts_at, self._now(), tz)
+            check_start(command.starts_at, now, tz)
         check_same_day(command.starts_at, command.duration_minutes, tz)
         # 지금 붙어 있는 메뉴는 보관됐어도 그대로 둘 수 있다(완료한 방문의 메모만 고치는 경우).
         chosen = set(command.menu_ids)
@@ -58,6 +62,11 @@ class UpdateVisitInteractor(UpdateVisitUseCase):
             ctx, current.id, command.starts_at, command.pet_id, command.duration_minutes, command.menu_ids,
             command.memo,
         )
+        # 시각이 바뀌었을 때만 알린다 — 반려동물·메뉴·메모만 바뀐 것은 보호자에게 알릴 일이 아니다.
+        if updated.starts_at != current.starts_at:
+            await self._events.publish(VisitRescheduled(
+                ctx=ctx, visit_id=updated.id, customer_id=updated.customer_id, pet_id=updated.pet_id,
+                starts_at=updated.starts_at, occurred_at=now, previous_starts_at=current.starts_at))
         warnings = []
         if updated.is_active:
             settings = await self._schedule.ensure(ctx)
```

`backend/apps/visit/dependencies/register_visit_provider.py`:

```diff
@@ -4,9 +4,10 @@ from fastapi import Depends
 
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
 from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
 from visit.dependencies.visit_wiring import (
     build_menu_repository,
     build_schedule_repository,
@@ -16,10 +17,11 @@ from visit.domain.services.visit_schedule import utc_now
 
 
 def get_register_visit_use_case(
-    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
+    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
+    events: DomainEventPort = Depends(get_domain_events),
 ) -> RegisterVisitUseCase:
     visits = build_visit_repository(db)
     return RegisterVisitInteractor(
         visits=visits, board=visits, menus=build_menu_repository(db),
-        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
+        schedule=build_schedule_repository(db), directory=directory, events=events, now=utc_now,
     )
```

`backend/apps/visit/dependencies/reschedule_visits_provider.py`:

```diff
@@ -4,9 +4,10 @@ from fastapi import Depends
 
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
 from visit.app.use_cases.reschedule_visits_interactor import RescheduleVisitsInteractor
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
 from visit.dependencies.visit_wiring import (
     build_menu_repository,
     build_schedule_repository,
@@ -16,10 +17,11 @@ from visit.domain.services.visit_schedule import utc_now
 
 
 def get_reschedule_visits_use_case(
-    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
+    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
+    events: DomainEventPort = Depends(get_domain_events),
 ) -> RescheduleVisitsUseCase:
     visits = build_visit_repository(db)
     return RescheduleVisitsInteractor(
         visits=visits, board=visits, menus=build_menu_repository(db),
-        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
+        schedule=build_schedule_repository(db), directory=directory, events=events, now=utc_now,
     )
```

`backend/apps/visit/dependencies/send_visit_report_provider.py`:

```diff
@@ -5,11 +5,17 @@ from fastapi import Depends
 from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.app.ports.input.send_visit_report_use_case import SendVisitReportUseCase
 from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
-from visit.dependencies.hub_ports import get_customer_directory, get_media_library, get_shop_profile
+from visit.dependencies.hub_ports import (
+    get_customer_directory,
+    get_domain_events,
+    get_media_library,
+    get_shop_profile,
+)
 from visit.dependencies.visit_wiring import (
     build_menu_repository,
     build_record_repository,
@@ -25,10 +31,11 @@ def get_send_visit_report_use_case(
     directory: CustomerDirectoryPort = Depends(get_customer_directory),
     library: MediaLibraryPort = Depends(get_media_library),
     shops: ShopProfilePort = Depends(get_shop_profile),
+    events: DomainEventPort = Depends(get_domain_events),
 ) -> SendVisitReportUseCase:
     return SendVisitReportInteractor(
         visits=build_visit_repository(db), records=build_record_repository(db),
         settings=build_report_settings_repository(db), reports=build_report_repository(db),
-        menus=build_menu_repository(db), directory=directory, library=library, shops=shops, now=utc_now,
-        link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
+        menus=build_menu_repository(db), directory=directory, library=library, shops=shops, events=events,
+        now=utc_now, link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
     )
```

`backend/apps/visit/dependencies/transition_visits_provider.py`:

```diff
@@ -4,18 +4,20 @@ from fastapi import Depends
 
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
 from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
 from visit.dependencies.visit_wiring import build_menu_repository, build_report_repository, build_visit_repository
 from visit.domain.services.visit_schedule import utc_now
 
 
 def get_transition_visits_use_case(
-    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
+    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
+    events: DomainEventPort = Depends(get_domain_events),
 ) -> TransitionVisitsUseCase:
     visits = build_visit_repository(db)
     return TransitionVisitsInteractor(
         visits=visits, history=visits, menus=build_menu_repository(db), reports=build_report_repository(db),
-        directory=directory, now=utc_now,
+        directory=directory, events=events, now=utc_now,
     )
```

`backend/apps/visit/dependencies/update_visit_provider.py`:

```diff
@@ -4,9 +4,10 @@ from fastapi import Depends
 
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
 from visit.app.use_cases.update_visit_interactor import UpdateVisitInteractor
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
 from visit.dependencies.visit_wiring import (
     build_menu_repository,
     build_schedule_repository,
@@ -16,10 +17,11 @@ from visit.domain.services.visit_schedule import utc_now
 
 
 def get_update_visit_use_case(
-    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
+    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
+    events: DomainEventPort = Depends(get_domain_events),
 ) -> UpdateVisitUseCase:
     visits = build_visit_repository(db)
     return UpdateVisitInteractor(
         visits=visits, board=visits, menus=build_menu_repository(db),
-        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
+        schedule=build_schedule_repository(db), directory=directory, events=events, now=utc_now,
     )
```

`backend/main.py`:

```diff
@@ -9,6 +9,7 @@ from fastapi import FastAPI
 
 from core.access_log import redact_access_log_queries
 from core.database import dispose_engine, init_engine
+from core.observer.in_process_event_bus import get_event_bus
 from core.redis import dispose_redis
 
 from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
@@ -97,7 +98,7 @@ from visit.adapter.inbound.api.v1.update_report_settings_router import update_re
 from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
 from visit.dependencies.hub_ports import get_media_library as get_visit_media_library
 from visit.dependencies.hub_ports import get_shop_profile
 from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
@@ -203,6 +204,8 @@ app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
 app.dependency_overrides[get_visit_media_library] = get_media_library_use_case
 app.dependency_overrides[get_customer_media_library] = get_media_library_use_case
 app.dependency_overrides[get_shop_profile] = get_shop_profile_use_case
+# 도메인 이벤트 — visit 이 발행하고 core 의 같은 세션 동기 버스가 구독자(main.py 가 기동 때 subscribe 로 꽂는다)에 넘긴다.
+app.dependency_overrides[get_domain_events] = get_event_bus
 
 
 @app.get("/health")
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 테스트(인터랙터 다섯 + 스텁 + 바인딩 파일) | 93 passed (새로 더한 것 15: 등록 3, 수정 3, 일정 변경 1, 전이 4, 알림장 3, 바인딩 1) |
| 이 작업의 통합(pg 저장소 파일 + 배선 새 파일) | 20 passed (새로 더한 것 3: pg 1, 배선 2) |
| 단위 전체 (`-m "not integration and not network"`) | 1318 passed (시작 1303 + 15) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken |

(단위의 warning 1은 기존 `starlette.testclient` 사용 중단 경고다.)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 등록에서 `if status == RESERVED:` → `if True:` → `test_register_visit_interactor.py::test_지금_시작한_손님은_예약이_아니라_발행하지_않는다`
- 수정에서 `if updated.starts_at != current.starts_at:` → `if True:` → `test_update_visit_interactor.py::test_메모만_바꾸면_발행하지_않는다`
- 전이에서 발행 루프를 `apply_changes` 앞으로(`locked` 기준) → `test_transition_visits_interactor.py::test_가족_묶음을_한_번에_완료하고_최근_방문을_알린다`(journal 순서), `::test_완료를_되돌리면_최근_방문을_다시_계산한다`(journal 끝 두 항목)
- 알림장에서 `if issued:` → `if True:` 로 늘 발행 → `test_send_visit_report_interactor.py::test_살아_있는_링크로_다시_보내면_발행하지_않고_끊은_뒤_보내면_다시_발행한다`
- `main.py` 의 `dependency_overrides[get_domain_events]` 줄 제거 → `tests/test_hub_port_binding.py::test_API_프로세스에는_빈_자리도_빠진_가드도_없다`, `::test_도메인_이벤트_자리는_core_의_버스로_채운다` (그리고 배선 `test_등록_수정_취소가_순서대로_이벤트로_닿는다` — 자리가 비어 등록이 500)
- `core/observer` 의 `InProcessEventBus.publish` 가 `try/except Exception: pass` 로 삼킴 (5 를 되돌린 뒤 단독으로) → `tests/integration/test_visit_events_wiring.py::test_구독자가_던지면_500_이고_방문은_생기지_않는다`
- pg `latest_completed_start_excluding` 에서 `VisitOrm.id != exclude_visit_id` 제거 → `test_visit_pg_repository.py::test_자기를_뺀_같은_아이의_가장_최근_완료_시작_시각`
- 전이 완료에서 `exclude_visit_id` 에 `visit.id` 대신 `0` (3 을 되돌린 뒤 단독으로 — 3 과 같이 넣으면 발행 시점에 아직 완료 전이라 가려진다) → `test_transition_visits_interactor.py::test_완료는_같은_아이의_앞선_완료_시작_시각을_실은_VisitClosed_를_발행한다`
- 일정 변경에서 `previous_starts_at=visit.starts_at`(새 시각) → `test_reschedule_visits_interactor.py::test_옮긴_방문마다_VisitRescheduled_를_옮긴_뒤에_발행한다`
- 전이 취소에서 `reason="customer_request"` 상수 → `test_transition_visits_interactor.py::test_취소는_사유를_실은_VisitCanceled_를_발행한다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 예약·일정 변경·취소·완료·노쇼·되돌리기·알림장 발급을 허브 이벤트로 발행한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: notification 도메인 — 채널·설정·템플릿·메시지 엔티티, 시각 규칙(전날 리마인드·야간 미룸·재시도), 문안 6종과 변수, 오류 11

**Files:**
- Create: `backend/apps/notification/domain/value_objects/message_kind.py`
- Create: `backend/apps/notification/domain/value_objects/message_status.py`
- Create: `backend/apps/notification/domain/entities/notification_message.py`
- Create: `backend/apps/notification/domain/services/schedule_rules.py`
- Create: `backend/apps/notification/domain/services/templates.py`
- Create: `backend/apps/notification/domain/errors.py`
- Create: `backend/apps/notification/CLAUDE.md`
- Create: `backend/apps/notification/__init__.py`
- Create: `backend/apps/notification/_docs/CLAUDE.md`
- Create: `backend/apps/notification/adapter/__init__.py`
- Create: `backend/apps/notification/adapter/inbound/__init__.py`
- Create: `backend/apps/notification/adapter/inbound/api/__init__.py`
- Create: `backend/apps/notification/adapter/inbound/api/error_map.py`
- Create: `backend/apps/notification/domain/__init__.py`
- Create: `backend/apps/notification/domain/entities/__init__.py`
- Create: `backend/apps/notification/domain/entities/notification_channel.py`
- Create: `backend/apps/notification/domain/entities/notification_settings.py`
- Create: `backend/apps/notification/domain/entities/notification_template.py`
- Create: `backend/apps/notification/domain/services/__init__.py`
- Create: `backend/apps/notification/domain/value_objects/__init__.py`
- Create: `backend/apps/notification/domain/value_objects/channel_status.py`
- Create: `backend/apps/notification/domain/value_objects/new_message.py`
- Create: `backend/apps/notification/domain/value_objects/template_status.py`
- Create: `backend/apps/notification/tests/__init__.py`
- Create: `backend/apps/notification/tests/adapter/__init__.py`
- Create: `backend/apps/notification/tests/adapter/test_notification_error_map.py`
- Create: `backend/apps/notification/tests/domain/__init__.py`
- Create: `backend/apps/notification/tests/domain/test_entities.py`
- Create: `backend/apps/notification/tests/domain/test_schedule_rules.py`
- Create: `backend/apps/notification/tests/domain/test_templates.py`
- Create: `backend/apps/notification/tests/helpers/__init__.py`
- Create: `backend/apps/notification/tests/helpers/builders.py`

**Interfaces:**
- Consumes: 표준 라이브러리만(`datetime`·`zoneinfo`·`re`·`dataclasses`). 설계 5절(규칙)·6.3(문안)·7.4(오류 코드).
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# notification.domain.value_objects.message_kind
CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT = "confirm", "reminder", "report", "change", "cancel", "next_visit"
KINDS: tuple[str, ...] = (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT)   # ORM CHECK 의 순서
DEFAULT_KINDS: tuple[str, ...] = (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL)
SCHEDULED_KINDS = frozenset({REMINDER, NEXT_VISIT})

# notification.domain.value_objects.message_status
SCHEDULED, SENDING, ACCEPTED, SENT, FALLBACK_SENT, FAILED, CANCELED = "scheduled", "sending", "accepted", "sent", "fallback_sent", "failed", "canceled"
STATUSES: tuple[str, ...]                 # 위 순서
PENDING_STATUSES = frozenset({SCHEDULED, SENDING})
DELIVERED_STATUSES = frozenset({SENT, FALLBACK_SENT})
CANCEL_REASONS: tuple[str, ...]           # 브리프의 14개 그대로(shop_closed·template_rejected·report_revoked 포함)
ERROR_KINDS: tuple[str, ...] = ("transient", "permanent")
CHANNELS_USED: tuple[str, ...] = ("alimtalk", "sms", "lms")

# notification.domain.value_objects.channel_status / template_status
TOKEN_REQUESTED, LINKED, UNLINKED = "token_requested", "linked", "unlinked";  CHANNEL_STATUSES: tuple[str, ...]
PENDING, APPROVED, REJECTED = "pending", "approved", "rejected";              TEMPLATE_STATUSES: tuple[str, ...]

# notification.domain.value_objects.new_message
@dataclass(frozen=True)
class NewMessage:
    shop_id: int; visit_id: int; customer_id: int; kind: str
    scheduled_at: datetime                       # UTC
    variables: Mapping[str, str]
    requested_by_member_id: int | None = None

# notification.domain.entities.notification_channel
@dataclass(frozen=True)
class NotificationChannel:
    shop_id: int; status: str; provider: str; provider_channel_id: str | None
    linked_at: datetime | None; unlinked_at: datetime | None
    sender_number: str | None; sender_number_verified_at: datetime | None; sms_fallback_enabled: bool
    is_linked: bool          # property — status == LINKED
    can_fallback: bool       # property — sms_fallback_enabled and sender_number_verified_at is not None

# notification.domain.entities.notification_settings
@dataclass(frozen=True)
class NotificationSettings:
    confirm_enabled: bool; reminder_enabled: bool; report_enabled: bool; change_enabled: bool; next_visit_enabled: bool
    reminder_time: time; next_visit_after_weeks: int | None; next_visit_cooldown_days: int
    def enabled_for(self, kind: str) -> bool     # change·cancel 은 change_enabled. 모르는 kind 는 KeyError
DEFAULT_NOTIFICATION_SETTINGS = NotificationSettings(True, True, True, True, False, time(18, 0), None, 30)

# notification.domain.entities.notification_template
@dataclass(frozen=True)
class NotificationTemplate:
    id: int; shop_id: int; kind: str; text_version: int; provider_template_id: str
    status: str; rejected_reason: str | None; requested_at: datetime; decided_at: datetime | None

# notification.domain.entities.notification_message
@dataclass(frozen=True)
class NotificationMessage:
    id: int; shop_id: int; visit_id: int; customer_id: int; kind: str
    scheduled_at: datetime; status: str; attempts: int; next_attempt_at: datetime | None
    channel_used: str | None; provider_message_id: str | None; error_code: str | None; error_kind: str | None
    variables: Mapping[str, str]
    requested_by_member_id: int | None; created_at: datetime; sent_at: datetime | None; canceled_reason: str | None

# notification.domain.services.schedule_rules
DAY_START, DAY_END = time(8, 0), time(21, 0)
REMINDER_TIME_MIN, REMINDER_TIME_MAX = time(8, 0), time(21, 0)
NEXT_VISIT_WEEKS_MIN, NEXT_VISIT_WEEKS_MAX = 1, 52
COOLDOWN_DAYS_MIN, COOLDOWN_DAYS_MAX = 1, 365
MAX_ATTEMPTS = 3
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))
STUCK_AFTER = timedelta(minutes=5)
ACCEPTED_TIMEOUT = timedelta(hours=24)
TOO_LATE_MARGIN = timedelta(hours=1)
DEFAULT_INTERVAL_WEEKS = 4
def reminder_at(starts_at: datetime, reminder_time: time, tz: str, now: datetime) -> datetime | None   # at > now 일 때만
def interval_weeks(previous_completed_at: datetime | None, completed_at: datetime, tz: str) -> int   # max(1, round(days/7)); None → 4
def next_visit_at(completed_at: datetime, weeks: int, reminder_time: time, tz: str) -> datetime
def deferred_for_daytime(at: datetime, tz: str) -> datetime        # 안이면 at 그대로(객체 그대로), 전이면 같은 날 08:00, 뒤면 다음 날 08:00 (UTC)
def is_too_late(send_at: datetime, starts_at: datetime) -> bool   # send_at > starts_at - 1h
def retry_at(attempts: int, now: datetime) -> datetime | None     # attempts = 이번 실패를 세기 전까지의 실패 횟수. 0·1·2 → +1분·+5분·+30분, >= 3 → None
def check_settings(settings: NotificationSettings) -> None        # 범위 밖 → NotificationInputError
def is_mobile_number(phone: str) -> bool                          # re.fullmatch(r"010[0-9]{8}")

# notification.domain.services.templates
TEXT_VERSION = 1
MAX_VARIABLE_CHARS = 200
SMS_MAX_BYTES = 90
URL_VARIABLE = "링크"
@dataclass(frozen=True)
class TemplateText: kind: str; name: str; body: str; sms_body: str; button_label: str | None
TEMPLATES: dict[str, TemplateText]      # 키 순서 = KINDS 순서. name: "예약 접수 안내"·"내일 예약 안내"·"미용 알림장"·"예약 변경 안내"·"예약 취소 안내"·"미용 주기 안내"
@dataclass(frozen=True)
class RenderedMessage: text: str; sms_text: str; button_url: str | None; variables: Mapping[str, str]   # variables 키는 "#{매장명}" 꼴
def target_label(pet_name: str | None, customer_name: str) -> str
def format_when(at: datetime, tz: str) -> str      # "10월 15일(목) 14:00"
def format_time(at: datetime, tz: str) -> str      # "14:00"
def format_date(at: datetime, tz: str) -> str      # "10월 15일(목)"
def expiry_label(expires_at: datetime | None, tz: str) -> str   # "11월 2일까지 열려요." / "언제든 열 수 있어요."
def variables_for(kind: str, *, shop_name: str, target: str, starts_at: datetime, tz: str,
                  previous_starts_at: datetime | None = None, url: str | None = None, expires_at: datetime | None = None,
                  last_visit_at: datetime | None = None, interval_weeks: int | None = None) -> dict[str, str]
    # 그 종류의 문안(본문·문자용·버튼)이 쓰는 변수만. 빠지면 ValueError
    # confirm·cancel: 매장명·대상·일시 / reminder: +시각 / change: +이전일시 / report: 매장명·대상·기간안내·링크 / next_visit: 매장명·대상·지난일·간격
def render(kind: str, variables: Mapping[str, str]) -> RenderedMessage   # 한 번만 치환. 값은 200자에서 자름(링크 예외). 변수 없으면 ValueError
def sms_channel(sms_text: str) -> str              # "sms" | "lms"
def euc_kr_bytes(text: str) -> int

# notification.domain.errors — 바탕 NotificationError(code="NOTIFICATION_ERROR") + 11개(브리프 표 그대로)
# notification.adapter.inbound.api.error_map
NOTIFICATION_ERROR_STATUS: dict[type[Exception], int]   # 브리프 표의 상태 그대로

# notification.tests.helpers.builders
TZ = "Asia/Seoul"; STAFF_PERMISSIONS; OWNER_PERMISSIONS     # visit 과 같은 값
def kst(month, day, hour=0, minute=0) -> datetime           # 2026년 KST → UTC
def ctx(shop_id=1, member_id=11, role="owner") -> ShopContext
def settings(**overrides) -> NotificationSettings          # 기본 = DEFAULT_NOTIFICATION_SETTINGS 와 같은 값
def channel(**overrides) -> NotificationChannel            # 기본: shop 1, linked, solapi, "KA01PF0001", 문자 대체 꺼짐
def template(**overrides) -> NotificationTemplate          # 기본: id 1, confirm, 판 1, "KA01TP0001", approved
def message(**overrides) -> NotificationMessage            # 기본: id 1, visit 1, customer 1, confirm, scheduled, attempts 0, variables {}
```

새 스포크 `notification` 의 첫 커밋이다 — 순수 도메인만(DB·HTTP 없음, `--no-deps` 로 돈다). `schedule_rules` 가 "전날 18:00"·"08:00~21:00 밖이면 다음 날 08:00"·"예약 1시간 전을 넘기면 안 보냄"·"4주 뒤 제안"·"1·5·30분 재시도" 를 매장 시간대로 계산하고, `templates` 가 문안 6종(`TEXT_VERSION=1`)과 변수 치환·문자 대체 종류(90바이트 넘으면 LMS)를 정한다. **`retry_at(attempts)` 는 올리기 전 값을 받는다**(0·1·2 → 1·5·30분, 3 이상 None) — 디스패처(작업 7)가 이렇게 넘긴다. 알림장 주소는 `variables` 에 들어가므로 이 스포크의 어떤 코드도 `%r` 로 로그에 남기지 않는다(N12).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/__init__.py`:

```python

```

`backend/apps/notification/tests/adapter/__init__.py`:

```python

```

`backend/apps/notification/tests/adapter/test_notification_error_map.py`:

```python
"""notification 오류의 계약 — 모든 오류가 HTTP 상태를 갖고 code 가 서로 다르다(tests/test_hub_errors.py 방식)."""
import pytest

from notification.adapter.inbound.api.error_map import NOTIFICATION_ERROR_STATUS
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    MessageNotRetryableError,
    NotificationError,
    NotificationInputError,
    ProviderUnavailableError,
    SenderNotVerifiedError,
    TemplateNotApprovedError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)


def _all_errors(base=NotificationError) -> set[type]:
    found = set()
    for sub in base.__subclasses__():
        found.add(sub)
        found |= _all_errors(sub)
    return found


def test_모든_notification_오류가_HTTP_상태를_갖는다():
    missing = sorted(e.__name__ for e in _all_errors() if e not in NOTIFICATION_ERROR_STATUS)
    assert missing == [], f"{missing} 가 error_map.py 의 NOTIFICATION_ERROR_STATUS 에 없다"


def test_맵에는_notification_오류만_있다():
    stray = sorted(e.__name__ for e in NOTIFICATION_ERROR_STATUS if not issubclass(e, NotificationError))
    assert stray == []


def test_오류_코드는_서로_다르다():
    codes = [e.code for e in _all_errors()]
    assert len(codes) == len(set(codes)), "같은 code 를 가진 오류가 둘 이상이다"


@pytest.mark.parametrize(("error", "code", "status"), [
    (NotificationInputError, "VALIDATION_ERROR", 422),
    (ChannelNotLinkedError, "NOTIFICATION_CHANNEL_NOT_LINKED", 409),
    (ChannelAlreadyLinkedError, "NOTIFICATION_CHANNEL_LINKED", 409),
    (TokenInvalidError, "NOTIFICATION_TOKEN_INVALID", 400),
    (SenderNotVerifiedError, "NOTIFICATION_SENDER_NOT_VERIFIED", 409),
    (TemplateNotApprovedError, "NOTIFICATION_TEMPLATE_NOT_APPROVED", 409),
    (MessageAlreadyPendingError, "NOTIFICATION_ALREADY_PENDING", 409),
    (MessageNotFoundError, "NOTIFICATION_MESSAGE_NOT_FOUND", 404),
    (MessageNotRetryableError, "NOTIFICATION_NOT_RETRYABLE", 409),
    (TooManyNotificationRequestsError, "NOTIFICATION_RATE_LIMITED", 429),
    (ProviderUnavailableError, "NOTIFICATION_PROVIDER_UNAVAILABLE", 502),
])
def test_오류의_코드와_상태(error, code, status):
    assert error.code == code
    assert NOTIFICATION_ERROR_STATUS[error] == status
```

`backend/apps/notification/tests/domain/__init__.py`:

```python

```

`backend/apps/notification/tests/domain/test_entities.py`:

```python
from datetime import time

import pytest

from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS, NotificationSettings
from notification.domain.value_objects.channel_status import LINKED, TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    DEFAULT_KINDS,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
    SCHEDULED_KINDS,
)
from notification.domain.value_objects.message_status import (
    DELIVERED_STATUSES,
    FALLBACK_SENT,
    PENDING_STATUSES,
    SCHEDULED,
    SENDING,
    SENT,
)
from notification.tests.helpers.builders import channel, kst, settings


def test_종류의_순서와_집합():
    assert KINDS == (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT)
    assert DEFAULT_KINDS == (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL)
    assert SCHEDULED_KINDS == frozenset({REMINDER, NEXT_VISIT})
    assert PENDING_STATUSES == frozenset({SCHEDULED, SENDING})
    assert DELIVERED_STATUSES == frozenset({SENT, FALLBACK_SENT})


@pytest.mark.parametrize(("status", "linked"), [(TOKEN_REQUESTED, False), (LINKED, True), (UNLINKED, False)])
def test_연동됨은_상태가_linked_일_때뿐이다(status, linked):
    assert channel(status=status).is_linked is linked


def test_문자_대체는_켜져_있고_발신번호_인증까지_마쳐야_한다():
    assert channel(sms_fallback_enabled=False).can_fallback is False
    assert channel(sms_fallback_enabled=True, sender_number="0212345678",
                   sender_number_verified_at=None).can_fallback is False
    assert channel(sms_fallback_enabled=True, sender_number="0212345678",
                   sender_number_verified_at=kst(10, 3, 10)).can_fallback is True


def test_처음_설정은_다음_예약_제안만_꺼져_있고_18시_30일이다():
    assert DEFAULT_NOTIFICATION_SETTINGS == NotificationSettings(
        confirm_enabled=True, reminder_enabled=True, report_enabled=True, change_enabled=True,
        next_visit_enabled=False, reminder_time=time(18, 0), next_visit_after_weeks=None,
        next_visit_cooldown_days=30,
    )


@pytest.mark.parametrize(("kind", "field"), [
    (CONFIRM, "confirm_enabled"), (REMINDER, "reminder_enabled"), (REPORT, "report_enabled"),
    (CHANGE, "change_enabled"), (CANCEL, "change_enabled"), (NEXT_VISIT, "next_visit_enabled"),
])
def test_종류마다_켜짐을_정하는_칸이_있고_취소는_변경_칸을_따른다(kind, field):
    everything_on = {f: True for f in (
        "confirm_enabled", "reminder_enabled", "report_enabled", "change_enabled", "next_visit_enabled")}
    assert settings(**everything_on).enabled_for(kind) is True
    assert settings(**{**everything_on, field: False}).enabled_for(kind) is False
```

`backend/apps/notification/tests/domain/test_schedule_rules.py`:

```python
from datetime import time, timedelta

import pytest

from notification.domain.errors import NotificationInputError
from notification.domain.services.schedule_rules import (
    DEFAULT_INTERVAL_WEEKS,
    MAX_ATTEMPTS,
    RETRY_DELAYS,
    check_settings,
    deferred_for_daytime,
    interval_weeks,
    is_mobile_number,
    is_too_late,
    next_visit_at,
    reminder_at,
    retry_at,
)
from notification.tests.helpers.builders import TZ, kst, settings

SIX_PM = time(18, 0)


# 리마인드 시각 — 예약 전날 매장 설정 시각


def test_리마인드는_예약_전날_설정_시각이다():
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 13, 9)) == kst(10, 14, 18)


def test_전날은_매장_시간대의_날짜로_센다():
    """KST 00:30 예약은 UTC 로는 그 전날 15:30 이다. 전날은 KST 기준 14일이어야 한다."""
    assert reminder_at(kst(10, 15, 0, 30), SIX_PM, TZ, now=kst(10, 13, 9)) == kst(10, 14, 18)


def test_리마인드_시각이_지금이거나_지났으면_없다():
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 14, 18)) is None
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 14, 18, 1)) is None


def test_리마인드_시각_1분_전이면_있다():
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 14, 17, 59)) == kst(10, 14, 18)


# 지난 방문 간격 — 매장 시간대 날짜 차를 주로 반올림, 최소 1


@pytest.mark.parametrize(("days", "weeks"), [(14, 2), (10, 1), (11, 2), (8, 1), (25, 4), (3, 1), (0, 1), (7, 1), (28, 4)])
def test_간격은_날짜_차를_주로_반올림한다(days, weeks):
    completed = kst(10, 1, 14) + timedelta(days=days)
    assert interval_weeks(kst(10, 1, 14), completed, TZ) == weeks


def test_간격의_날짜_차는_매장_시간대로_센다():
    """KST 5일 00:30 → 15일 23:30 은 KST 로 10일(1주), UTC 로 세면 11일(2주)이다."""
    assert interval_weeks(kst(10, 5, 0, 30), kst(10, 15, 23, 30), TZ) == 1


def test_앞선_완료가_없으면_기본_4주다():
    assert DEFAULT_INTERVAL_WEEKS == 4
    assert interval_weeks(None, kst(10, 15, 14), TZ) == 4


# 다음 예약 제안 시각 — 완료일 + N주 되는 날 리마인드 시각


def test_다음_예약_제안은_완료일에_주를_더한_날의_리마인드_시각이다():
    assert next_visit_at(kst(10, 15, 14), 4, SIX_PM, TZ) == kst(11, 12, 18)


def test_다음_예약_제안의_완료일은_매장_시간대로_센다():
    assert next_visit_at(kst(10, 15, 0, 30), 1, time(8, 0), TZ) == kst(10, 22, 8)


# 야간 미룸 — 매장 시간대 08:00~21:00


@pytest.mark.parametrize(("at", "expected"), [
    (kst(10, 15, 7, 59), kst(10, 15, 8)),         # 아침 전 → 같은 날 08:00
    (kst(10, 15, 8, 0), kst(10, 15, 8, 0)),       # 경계 08:00 은 그대로
    (kst(10, 15, 14), kst(10, 15, 14)),           # 낮은 그대로
    (kst(10, 15, 21, 0), kst(10, 15, 21, 0)),     # 경계 21:00 은 그대로
    (kst(10, 15, 23, 30), kst(10, 16, 8)),        # 밤 → 다음 날 08:00
    (kst(10, 15, 0, 10), kst(10, 15, 8)),         # KST 자정 직후(UTC 전날) → 같은 KST 날 08:00
])
def test_야간이면_아침_8시로_미룬다(at, expected):
    assert deferred_for_daytime(at, TZ) == expected


def test_21시_1초_뒤는_다음_날_아침이다():
    assert deferred_for_daytime(kst(10, 15, 21) + timedelta(seconds=1), TZ) == kst(10, 16, 8)


# 너무 늦음 — 예약 1시간 전을 넘기면 보내지 않는다


def test_정확히_1시간_전은_늦지_않고_59분_전은_늦다():
    starts = kst(10, 15, 14)
    assert is_too_late(kst(10, 15, 13), starts) is False
    assert is_too_late(kst(10, 15, 13, 1), starts) is True


# 재시도 — 1분·5분·30분 뒤, 세 번 뒤 없음


def test_재시도_간격과_상한():
    assert MAX_ATTEMPTS == 3
    assert RETRY_DELAYS == (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))
    now = kst(10, 15, 14)
    assert retry_at(0, now) == now + timedelta(minutes=1)
    assert retry_at(1, now) == now + timedelta(minutes=5)
    assert retry_at(2, now) == now + timedelta(minutes=30)
    assert retry_at(3, now) is None
    assert retry_at(4, now) is None


# 설정 검사


@pytest.mark.parametrize("overrides", [
    dict(reminder_time=time(8, 0)), dict(reminder_time=time(21, 0)),
    dict(next_visit_after_weeks=None), dict(next_visit_after_weeks=1), dict(next_visit_after_weeks=52),
    dict(next_visit_cooldown_days=1), dict(next_visit_cooldown_days=365),
])
def test_경계_안의_설정은_받는다(overrides):
    check_settings(settings(**overrides))


@pytest.mark.parametrize("overrides", [
    dict(reminder_time=time(7, 59)), dict(reminder_time=time(21, 1)), dict(reminder_time=time(22, 0)),
    dict(next_visit_after_weeks=0), dict(next_visit_after_weeks=53),
    dict(next_visit_cooldown_days=0), dict(next_visit_cooldown_days=366),
])
def test_경계_밖의_설정은_거절한다(overrides):
    with pytest.raises(NotificationInputError):
        check_settings(settings(**overrides))


# 휴대폰 번호


@pytest.mark.parametrize(("phone", "expected"), [
    ("01012345678", True),
    ("0212345678", False),
    ("010-1234-5678", False),
    ("0101234567", False),
    ("010123456789", False),
    ("", False),
])
def test_휴대폰_번호는_010_으로_시작하는_숫자_11자리다(phone, expected):
    assert is_mobile_number(phone) is expected
```

`backend/apps/notification/tests/domain/test_templates.py`:

```python
import pytest

from notification.domain.services.templates import (
    TEMPLATES,
    TEXT_VERSION,
    euc_kr_bytes,
    expiry_label,
    format_date,
    format_time,
    format_when,
    render,
    sms_channel,
    target_label,
    variables_for,
)
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
)
from notification.tests.helpers.builders import TZ, kst

STARTS = kst(10, 15, 14)          # 10월 15일(목) 14:00
PREVIOUS = kst(10, 14, 11)        # 10월 14일(수) 11:00
URL = "https://chagocnote.com/r/" + "a" * 43     # 알림장 토큰은 32바이트 base64 — 43자

# 설계 6.3 표 그대로 — 알림톡 문안은 줄 단위, 문자용은 한 줄
DESIGN = {
    CONFIRM: (
        ["[#{매장명}] 예약 접수 안내", "#{대상}의 예약이 접수되었어요.", "일시: #{일시}", "변경·취소는 매장으로 연락해 주세요."],
        "[#{매장명}] #{일시} 예약이 접수되었어요.", None,
    ),
    REMINDER: (
        ["[#{매장명}] 내일 예약 안내", "#{대상}의 예약이 내일이에요.", "일시: #{일시}", "늦거나 못 오시면 미리 연락해 주세요."],
        "[#{매장명}] 내일 #{시각} 예약을 잊지 마세요.", None,
    ),
    CHANGE: (
        ["[#{매장명}] 예약 변경 안내", "#{대상}의 예약 일시가 바뀌었어요.", "변경 전: #{이전일시}", "변경 후: #{일시}"],
        "[#{매장명}] 예약이 #{일시}로 바뀌었어요.", None,
    ),
    CANCEL: (
        ["[#{매장명}] 예약 취소 안내", "매장 사정으로 #{대상}의 #{일시} 예약이 취소되었어요. 죄송합니다.",
         "다시 예약하시려면 매장으로 연락해 주세요."],
        "[#{매장명}] #{일시} 예약이 매장 사정으로 취소되었어요.", None,
    ),
    REPORT: (
        ["[#{매장명}] 미용 알림장", "#{대상}의 오늘 미용 알림장이 도착했어요.", "#{기간안내}"],
        "[#{매장명}] 알림장 #{링크}", "알림장 보기",
    ),
    NEXT_VISIT: (
        ["[#{매장명}] 미용 주기 안내", "#{대상}의 지난 미용이 #{지난일}이었어요.", "#{간격}주 정도마다 미용하면 좋아요.",
         "예약은 매장으로 연락해 주세요."],
        "[#{매장명}] #{대상} 미용한 지 #{간격}주가 지났어요.", None,
    ),
}


def _all_variables(kind: str) -> dict[str, str]:
    return variables_for(kind, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         previous_starts_at=PREVIOUS, url=URL, expires_at=kst(11, 2, 14),
                         last_visit_at=STARTS, interval_weeks=4)


def test_문안은_여섯_종류이고_판은_1이다():
    assert TEXT_VERSION == 1
    assert tuple(TEMPLATES) == KINDS


@pytest.mark.parametrize("kind", KINDS)
def test_문안은_설계_6_3_과_글자까지_같다(kind):
    lines, sms_body, button = DESIGN[kind]
    text = TEMPLATES[kind]
    assert text.kind == kind
    assert text.body == "\n".join(lines)
    assert text.sms_body == sms_body
    assert text.button_label == button


def test_알림톡_본문에는_링크_변수가_없고_문자용에만_있다():
    assert "#{링크}" not in TEMPLATES[REPORT].body
    assert "#{링크}" in TEMPLATES[REPORT].sms_body


# 변수


def test_변수는_종류마다_필요한_것만_준다():
    assert variables_for(CONFIRM, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00",
    }
    assert variables_for(REMINDER, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00", "시각": "14:00",
    }
    assert variables_for(CHANGE, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         previous_starts_at=PREVIOUS) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00", "이전일시": "10월 14일(수) 11:00",
    }
    assert variables_for(CANCEL, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00",
    }
    assert variables_for(REPORT, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         url=URL, expires_at=kst(11, 2, 14)) == {
        "매장명": "두부네 미용실", "대상": "두부", "기간안내": "11월 2일까지 열려요.", "링크": URL,
    }
    assert variables_for(NEXT_VISIT, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         last_visit_at=STARTS, interval_weeks=4) == {
        "매장명": "두부네 미용실", "대상": "두부", "지난일": "10월 15일(목)", "간격": "4",
    }


@pytest.mark.parametrize(("kind", "missing"), [
    (CHANGE, "previous_starts_at"), (REPORT, "url"), (NEXT_VISIT, "last_visit_at"), (NEXT_VISIT, "interval_weeks"),
])
def test_필요한_값이_빠지면_프로그래밍_오류다(kind, missing):
    kwargs = dict(previous_starts_at=PREVIOUS, url=URL, last_visit_at=STARTS, interval_weeks=4)
    kwargs.pop(missing)
    with pytest.raises(ValueError):
        variables_for(kind, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ, **kwargs)


def test_알림장의_기간이_없으면_언제든_열_수_있다고_한다():
    variables = variables_for(REPORT, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ, url=URL)
    assert variables["기간안내"] == "언제든 열 수 있어요."


# 치환


@pytest.mark.parametrize("kind", KINDS)
def test_치환하면_남는_변수_자리가_없다(kind):
    rendered = render(kind, _all_variables(kind))
    assert "#{" not in rendered.text
    assert "#{" not in rendered.sms_text


def test_접수_문안을_채운_모습():
    rendered = render(CONFIRM, _all_variables(CONFIRM))
    assert rendered.text == (
        "[두부네 미용실] 예약 접수 안내\n두부의 예약이 접수되었어요.\n일시: 10월 15일(목) 14:00\n변경·취소는 매장으로 연락해 주세요."
    )
    assert rendered.sms_text == "[두부네 미용실] 10월 15일(목) 14:00 예약이 접수되었어요."
    assert rendered.button_url is None
    assert rendered.variables == {"#{매장명}": "두부네 미용실", "#{대상}": "두부", "#{일시}": "10월 15일(목) 14:00"}


def test_알림장은_버튼_주소가_있고_본문에는_주소가_없다():
    rendered = render(REPORT, _all_variables(REPORT))
    assert rendered.button_url == URL
    assert URL not in rendered.text
    assert rendered.sms_text == f"[두부네 미용실] 알림장 {URL}"


def test_값에_든_변수_모양은_글자로_남는다():
    """이름이 '#{매장명}' 이어도 한 번만 치환한다 — 업체도 값을 글자 그대로 넣는다."""
    variables = variables_for(CONFIRM, shop_name="두부네 미용실", target="#{매장명}", starts_at=STARTS, tz=TZ)
    rendered = render(CONFIRM, variables)
    assert rendered.text.startswith("[두부네 미용실] 예약 접수 안내\n#{매장명}의 예약이 접수되었어요.")
    assert rendered.variables["#{대상}"] == "#{매장명}"


def test_긴_값은_200자에서_자르고_주소는_자르지_않는다():
    long_url = "https://chagocnote.com/r/" + "a" * 300
    variables = variables_for(REPORT, shop_name="가" * 250, target="두부", starts_at=STARTS, tz=TZ, url=long_url)
    rendered = render(REPORT, variables)
    assert rendered.variables["#{매장명}"] == "가" * 200
    assert rendered.text.startswith("[" + "가" * 200 + "] 미용 알림장")
    assert rendered.button_url == long_url
    assert rendered.sms_text.endswith(long_url)


# 문자 길이 — EUC-KR 90바이트


def test_한글_45자는_sms_46자는_lms():
    assert euc_kr_bytes("가" * 45) == 90
    assert sms_channel("가" * 45) == "sms"
    assert sms_channel("가" * 46) == "lms"


def test_알림장_문자는_실제_길이의_주소를_넣으면_lms_다():
    rendered = render(REPORT, _all_variables(REPORT))
    assert sms_channel(rendered.sms_text) == "lms"
    rendered = render(CONFIRM, _all_variables(CONFIRM))
    assert sms_channel(rendered.sms_text) == "sms"


# 표기


def test_대상은_반려동물_이름_없으면_보호자_이름에_님():
    assert target_label("두부", "김차곡") == "두부"
    assert target_label(None, "김차곡") == "김차곡님"


def test_일시_표기는_월_일_한글_요일_시각():
    assert format_when(kst(10, 15, 14), TZ) == "10월 15일(목) 14:00"
    assert format_when(kst(10, 18, 9, 5), TZ) == "10월 18일(일) 09:05"
    assert format_when(kst(11, 2, 0, 30), TZ) == "11월 2일(월) 00:30"     # UTC 로는 전날 — 매장 시간대로
    assert format_time(kst(10, 15, 14), TZ) == "14:00"
    assert format_date(kst(10, 15, 14), TZ) == "10월 15일(목)"


def test_기간_안내_둘():
    assert expiry_label(kst(11, 2, 14), TZ) == "11월 2일까지 열려요."
    assert expiry_label(None, TZ) == "언제든 열 수 있어요."
```

`backend/apps/notification/tests/helpers/__init__.py`:

```python

```

`backend/apps/notification/tests/helpers/builders.py`:

```python
"""notification 테스트가 함께 쓰는 값 — 매장 컨텍스트와 채널·설정·템플릿·메시지 엔티티를 짧게 만든다."""
from __future__ import annotations

from datetime import datetime, time, timezone

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.value_objects.channel_status import LINKED
from notification.domain.value_objects.message_kind import CONFIRM
from notification.domain.value_objects.message_status import SCHEDULED
from notification.domain.value_objects.template_status import APPROVED

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
OWNER_PERMISSIONS = STAFF_PERMISSIONS | frozenset(
    {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}
)
TZ = "Asia/Seoul"


def kst(month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """2026년 한국 시각을 UTC 로. 테스트의 모든 시각은 이것으로 만든다."""
    from zoneinfo import ZoneInfo

    return datetime(2026, month, day, hour, minute, tzinfo=ZoneInfo(TZ)).astimezone(timezone.utc)


def ctx(shop_id: int = 1, member_id: int = 11, role: str = "owner") -> ShopContext:
    permissions = OWNER_PERMISSIONS if role == "owner" else STAFF_PERMISSIONS
    return ShopContext(shop_id=shop_id, member_id=member_id, role=role, permissions=permissions,
                       timezone=TZ)


def settings(**overrides) -> NotificationSettings:
    fields = dict(
        confirm_enabled=True, reminder_enabled=True, report_enabled=True, change_enabled=True,
        next_visit_enabled=False, reminder_time=time(18, 0), next_visit_after_weeks=None,
        next_visit_cooldown_days=30,
    )
    fields.update(overrides)
    return NotificationSettings(**fields)


def channel(**overrides) -> NotificationChannel:
    fields = dict(
        shop_id=1, status=LINKED, provider="solapi", provider_channel_id="KA01PF0001",
        linked_at=kst(10, 1, 10), unlinked_at=None, sender_number=None,
        sender_number_verified_at=None, sms_fallback_enabled=False,
    )
    fields.update(overrides)
    return NotificationChannel(**fields)


def template(**overrides) -> NotificationTemplate:
    fields = dict(
        id=1, shop_id=1, kind=CONFIRM, text_version=1, provider_template_id="KA01TP0001",
        status=APPROVED, rejected_reason=None, requested_at=kst(10, 1, 10), decided_at=kst(10, 2, 10),
    )
    fields.update(overrides)
    return NotificationTemplate(**fields)


def message(**overrides) -> NotificationMessage:
    fields = dict(
        id=1, shop_id=1, visit_id=1, customer_id=1, kind=CONFIRM, scheduled_at=kst(10, 14, 11),
        status=SCHEDULED, attempts=0, next_attempt_at=None, channel_used=None, provider_message_id=None,
        error_code=None, error_kind=None, variables={}, requested_by_member_id=None,
        created_at=kst(10, 14, 11), sent_at=None, canceled_reason=None,
    )
    fields.update(overrides)
    return NotificationMessage(**fields)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

`docker compose run --rm --no-deps backend pytest apps/notification -q -p no:cacheprovider`
→ 수집 오류 4건(`ModuleNotFoundError: No module named 'notification.domain.services.templates'` 등 네 테스트 파일 전부), `Interrupted: 4 errors during collection`.

구현 뒤 첫 실행에서 `test_알림장_문자는_주소_때문에_보통_lms` 하나가 실패했다 — 테스트의 주소가 64자라 87바이트(sms)였다. 실제 알림장 토큰은 32바이트 base64 = 43자(`visit/domain/services/report_token.py`)라 테스트 주소를 `"https://chagocnote.com/r/" + "a" * 43`(68자)로 고치고 이름을 `test_알림장_문자는_실제_길이의_주소를_넣으면_lms_다` 로 바꿨다(구현은 그대로).

- [ ] **Step 3: 구현한다**

`backend/apps/notification/domain/value_objects/message_kind.py`:

```python
"""메시지 종류(설계 4.3·6.3). KINDS 의 순서가 ORM CHECK 의 순서다."""
CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT = (
    "confirm", "reminder", "report", "change", "cancel", "next_visit",
)
KINDS: tuple[str, ...] = (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT)
DEFAULT_KINDS: tuple[str, ...] = tuple(k for k in KINDS if k != NEXT_VISIT)   # 연동 때 자동 등록하는 템플릿
SCHEDULED_KINDS = frozenset({REMINDER, NEXT_VISIT})                            # 시각이 있는 것 — 야간 미룸 대상
```

`backend/apps/notification/domain/value_objects/message_status.py`:

```python
"""메시지 상태와 취소 이유·오류 종류·나간 길(설계 4.4). STATUSES 의 순서가 ORM CHECK 의 순서다."""
SCHEDULED, SENDING, ACCEPTED, SENT, FALLBACK_SENT, FAILED, CANCELED = (
    "scheduled", "sending", "accepted", "sent", "fallback_sent", "failed", "canceled",
)
STATUSES: tuple[str, ...] = (SCHEDULED, SENDING, ACCEPTED, SENT, FALLBACK_SENT, FAILED, CANCELED)
PENDING_STATUSES = frozenset({SCHEDULED, SENDING})      # 부분 유일 색인의 조건 — 같은 방문·종류의 대기 줄은 하나
DELIVERED_STATUSES = frozenset({SENT, FALLBACK_SENT})   # "이미 보냈다"
CANCEL_REASONS: tuple[str, ...] = (
    "rescheduled", "visit_canceled", "no_show", "setting_off", "channel_unlinked",
    "shop_closed", "template_rejected", "report_revoked", "too_late", "anonymized",
    "has_upcoming", "cooldown", "no_consent", "bad_phone",
)
ERROR_KINDS: tuple[str, ...] = ("transient", "permanent")
CHANNELS_USED: tuple[str, ...] = ("alimtalk", "sms", "lms")
```

`backend/apps/notification/domain/entities/notification_message.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NotificationMessage:
    """알림 줄 하나 — 큐이자 발송 기록(설계 4.4). 전화번호·이름은 저장하지 않고 보내는 순간 포트로 읽는다."""

    id: int
    shop_id: int
    visit_id: int
    customer_id: int
    kind: str
    scheduled_at: datetime            # UTC. 즉시면 만든 시각
    status: str
    attempts: int
    next_attempt_at: datetime | None
    channel_used: str | None          # 실제로 나간 길
    provider_message_id: str | None
    error_code: str | None
    error_kind: str | None            # transient / permanent
    variables: Mapping[str, str]      # 이벤트에서만 알 수 있는 값(url, expires_at ISO, previous_starts_at ISO …)
    requested_by_member_id: int | None
    created_at: datetime
    sent_at: datetime | None
    canceled_reason: str | None
```

`backend/apps/notification/domain/services/schedule_rules.py`:

```python
"""보내는 시각의 규칙 — 전날 리마인드, 다음 예약 제안, 야간 미룸, 너무 늦음, 재시도, 설정 범위(설계 2·5.2~5.4).

전부 순수 함수다. 시각은 UTC 로 받고 주며, "전날"·"08:00~21:00" 같은 날짜·벽시계 판단만 매장 시간대로 한다.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.errors import NotificationInputError

DAY_START, DAY_END = time(8, 0), time(21, 0)                  # 리마인드·다음 예약 제안을 보내는 시간
REMINDER_TIME_MIN, REMINDER_TIME_MAX = time(8, 0), time(21, 0)
NEXT_VISIT_WEEKS_MIN, NEXT_VISIT_WEEKS_MAX = 1, 52
COOLDOWN_DAYS_MIN, COOLDOWN_DAYS_MAX = 1, 365
MAX_ATTEMPTS = 3
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))   # 실패 0·1·2회 뒤
STUCK_AFTER = timedelta(minutes=5)          # 이보다 오래 sending 이면 다음 루프가 되돌린다
ACCEPTED_TIMEOUT = timedelta(hours=24)      # accepted 의 최종 상태를 기다리는 최대 시간
TOO_LATE_MARGIN = timedelta(hours=1)        # 예약 이 시간 전을 넘기면 보내지 않는다
DEFAULT_INTERVAL_WEEKS = 4
MOBILE_NUMBER = re.compile(r"010[0-9]{8}")


def _local_date(at: datetime, tz: str) -> date:
    return at.astimezone(ZoneInfo(tz)).date()


def _at(day: date, wall_time: time, tz: str) -> datetime:
    """매장 시간대의 날짜 + 벽시계 시각을 UTC 로."""
    return datetime.combine(day, wall_time, tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def reminder_at(starts_at: datetime, reminder_time: time, tz: str, now: datetime) -> datetime | None:
    """예약 전날(매장 시간대 날짜 - 1일) reminder_time. 그 시각이 now 이하이면 None — 접수 문안이 겸한다."""
    at = _at(_local_date(starts_at, tz) - timedelta(days=1), reminder_time, tz)
    return at if at > now else None


def interval_weeks(previous_completed_at: datetime | None, completed_at: datetime, tz: str) -> int:
    """두 완료일(매장 시간대 날짜)의 차를 주로 반올림, 최소 1. 앞선 완료가 없으면 기본 4주."""
    if previous_completed_at is None:
        return DEFAULT_INTERVAL_WEEKS
    days = (_local_date(completed_at, tz) - _local_date(previous_completed_at, tz)).days
    return max(1, round(days / 7))


def next_visit_at(completed_at: datetime, weeks: int, reminder_time: time, tz: str) -> datetime:
    """완료일 + weeks 주 되는 날 reminder_time."""
    return _at(_local_date(completed_at, tz) + timedelta(weeks=weeks), reminder_time, tz)


def deferred_for_daytime(at: datetime, tz: str) -> datetime:
    """매장 시간대로 DAY_START~DAY_END 안이면 그대로. 그 전이면 같은 날 DAY_START, 그 뒤면 다음 날 DAY_START."""
    local = at.astimezone(ZoneInfo(tz))
    if local.time() < DAY_START:
        return _at(local.date(), DAY_START, tz)
    if local.time() > DAY_END:
        return _at(local.date() + timedelta(days=1), DAY_START, tz)
    return at


def is_too_late(send_at: datetime, starts_at: datetime) -> bool:
    return send_at > starts_at - TOO_LATE_MARGIN


def retry_at(attempts: int, now: datetime) -> datetime | None:
    """attempts 는 지금까지 실패한 횟수(이번 실패를 세기 전). 0·1·2 면 1분·5분·30분 뒤, MAX_ATTEMPTS 이상이면 None."""
    if attempts >= MAX_ATTEMPTS:
        return None
    return now + RETRY_DELAYS[attempts]


def check_settings(settings: NotificationSettings) -> None:
    if not REMINDER_TIME_MIN <= settings.reminder_time <= REMINDER_TIME_MAX:
        raise NotificationInputError("리마인드 시각은 08:00 부터 21:00 사이여야 합니다.")
    weeks = settings.next_visit_after_weeks
    if weeks is not None and not NEXT_VISIT_WEEKS_MIN <= weeks <= NEXT_VISIT_WEEKS_MAX:
        raise NotificationInputError("다음 예약 제안 주기는 1주부터 52주 사이여야 합니다.")
    if not COOLDOWN_DAYS_MIN <= settings.next_visit_cooldown_days <= COOLDOWN_DAYS_MAX:
        raise NotificationInputError("다음 예약 제안 간격은 1일부터 365일 사이여야 합니다.")


def is_mobile_number(phone: str) -> bool:
    """010 으로 시작하는 숫자 11자리(customers.phone 저장 형식)."""
    return MOBILE_NUMBER.fullmatch(phone) is not None
```

`backend/apps/notification/domain/services/templates.py`:

```python
"""문안 6종과 변수(설계 6.3). 문안은 코드에 고정이고 변수만 채운다 — 바꾸면 TEXT_VERSION 을 올려 전 매장에 다시 등록한다.

변수 이름은 한글 그대로(`#{매장명}` …). 알림톡 본문의 알림장 주소는 버튼에만 있고(`#{링크}` 는 sms_body 에만), 업체는
변수 값을 글자 그대로 넣으므로 이름에 `#{` 가 있어도 문안이 깨지지 않는다 — render 도 한 번만 치환한다.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT

TEXT_VERSION = 1
MAX_VARIABLE_CHARS = 200     # 업체의 변수 길이 한도 안에서 자른다. 주소(#{링크})는 자르지 않는다
SMS_MAX_BYTES = 90           # EUC-KR 바이트. 넘으면 LMS
URL_VARIABLE = "링크"
WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")
PLACEHOLDER = re.compile(r"#\{([^}]+)\}")


@dataclass(frozen=True)
class TemplateText:
    kind: str
    name: str
    body: str                    # 알림톡 본문. 줄바꿈은 "\n"
    sms_body: str                # 문자 대체용 짧은 문안
    button_label: str | None     # 버튼은 report 만 — 주소는 #{링크} 변수


TEMPLATES: dict[str, TemplateText] = {
    CONFIRM: TemplateText(
        kind=CONFIRM, name="예약 접수 안내",
        body="[#{매장명}] 예약 접수 안내\n#{대상}의 예약이 접수되었어요.\n일시: #{일시}\n변경·취소는 매장으로 연락해 주세요.",
        sms_body="[#{매장명}] #{일시} 예약이 접수되었어요.", button_label=None,
    ),
    REMINDER: TemplateText(
        kind=REMINDER, name="내일 예약 안내",
        body="[#{매장명}] 내일 예약 안내\n#{대상}의 예약이 내일이에요.\n일시: #{일시}\n늦거나 못 오시면 미리 연락해 주세요.",
        sms_body="[#{매장명}] 내일 #{시각} 예약을 잊지 마세요.", button_label=None,
    ),
    REPORT: TemplateText(
        kind=REPORT, name="미용 알림장",
        body="[#{매장명}] 미용 알림장\n#{대상}의 오늘 미용 알림장이 도착했어요.\n#{기간안내}",
        sms_body="[#{매장명}] 알림장 #{링크}", button_label="알림장 보기",
    ),
    CHANGE: TemplateText(
        kind=CHANGE, name="예약 변경 안내",
        body="[#{매장명}] 예약 변경 안내\n#{대상}의 예약 일시가 바뀌었어요.\n변경 전: #{이전일시}\n변경 후: #{일시}",
        sms_body="[#{매장명}] 예약이 #{일시}로 바뀌었어요.", button_label=None,
    ),
    CANCEL: TemplateText(
        kind=CANCEL, name="예약 취소 안내",
        body="[#{매장명}] 예약 취소 안내\n매장 사정으로 #{대상}의 #{일시} 예약이 취소되었어요. 죄송합니다.\n"
             "다시 예약하시려면 매장으로 연락해 주세요.",
        sms_body="[#{매장명}] #{일시} 예약이 매장 사정으로 취소되었어요.", button_label=None,
    ),
    NEXT_VISIT: TemplateText(
        kind=NEXT_VISIT, name="미용 주기 안내",
        body="[#{매장명}] 미용 주기 안내\n#{대상}의 지난 미용이 #{지난일}이었어요.\n#{간격}주 정도마다 미용하면 좋아요.\n"
             "예약은 매장으로 연락해 주세요.",
        sms_body="[#{매장명}] #{대상} 미용한 지 #{간격}주가 지났어요.", button_label=None,
    ),
}


@dataclass(frozen=True)
class RenderedMessage:
    text: str
    sms_text: str
    button_url: str | None
    variables: Mapping[str, str]     # 업체에 넘길 #{이름}: 값


def target_label(pet_name: str | None, customer_name: str) -> str:
    """반려동물 이름이 있으면 그대로, 없으면 보호자 이름 뒤에 '님'."""
    return pet_name if pet_name else f"{customer_name}님"


def _local(at: datetime, tz: str) -> datetime:
    return at.astimezone(ZoneInfo(tz))


def format_date(at: datetime, tz: str) -> str:
    local = _local(at, tz)
    return f"{local.month}월 {local.day}일({WEEKDAYS[local.weekday()]})"


def format_time(at: datetime, tz: str) -> str:
    return _local(at, tz).strftime("%H:%M")


def format_when(at: datetime, tz: str) -> str:
    return f"{format_date(at, tz)} {format_time(at, tz)}"


def expiry_label(expires_at: datetime | None, tz: str) -> str:
    if expires_at is None:
        return "언제든 열 수 있어요."
    local = _local(expires_at, tz)
    return f"{local.month}월 {local.day}일까지 열려요."


def _placeholders(text: TemplateText) -> list[str]:
    """문안(본문·문자용·버튼)이 쓰는 변수 이름, 나온 순서대로 한 번씩."""
    names = PLACEHOLDER.findall(text.body) + PLACEHOLDER.findall(text.sms_body)
    if text.button_label is not None:
        names.append(URL_VARIABLE)
    return list(dict.fromkeys(names))


def variables_for(kind: str, *, shop_name: str, target: str, starts_at: datetime, tz: str,
                  previous_starts_at: datetime | None = None, url: str | None = None,
                  expires_at: datetime | None = None, last_visit_at: datetime | None = None,
                  interval_weeks: int | None = None) -> dict[str, str]:
    """종류의 문안이 쓰는 변수만 돌려준다. 그 종류에 필요한 값이 빠져 있으면 ValueError(프로그래밍 오류)."""
    known: dict[str, str] = {
        "매장명": shop_name,
        "대상": target,
        "일시": format_when(starts_at, tz),
        "시각": format_time(starts_at, tz),
        "기간안내": expiry_label(expires_at, tz),
    }
    if previous_starts_at is not None:
        known["이전일시"] = format_when(previous_starts_at, tz)
    if url is not None:
        known[URL_VARIABLE] = url
    if last_visit_at is not None:
        known["지난일"] = format_date(last_visit_at, tz)
    if interval_weeks is not None:
        known["간격"] = str(interval_weeks)
    variables = {}
    for name in _placeholders(TEMPLATES[kind]):
        if name not in known:
            raise ValueError(f"{kind} 문안의 변수 {name} 에 넣을 값이 없습니다.")
        variables[name] = known[name]
    return variables


def _clip(name: str, value: str) -> str:
    return value if name == URL_VARIABLE else value[:MAX_VARIABLE_CHARS]


def render(kind: str, variables: Mapping[str, str]) -> RenderedMessage:
    """#{x} 를 값으로 치환한다. 한 번만 — 값에 '#{' 가 있어도 다시 치환하지 않는다."""
    text = TEMPLATES[kind]
    values = {name: _clip(name, value) for name, value in variables.items()}

    def fill(match: re.Match) -> str:
        name = match.group(1)
        if name not in values:
            raise ValueError(f"{kind} 문안의 변수 {name} 이 비어 있습니다.")
        return values[name]

    return RenderedMessage(
        text=PLACEHOLDER.sub(fill, text.body),
        sms_text=PLACEHOLDER.sub(fill, text.sms_body),
        button_url=values[URL_VARIABLE] if text.button_label is not None else None,
        variables={f"#{{{name}}}": value for name, value in values.items()},
    )


def euc_kr_bytes(text: str) -> int:
    return len(text.encode("euc-kr", errors="replace"))


def sms_channel(sms_text: str) -> str:
    """EUC-KR 바이트 90 이하면 sms, 넘으면 lms."""
    return "sms" if euc_kr_bytes(sms_text) <= SMS_MAX_BYTES else "lms"
```

`backend/apps/notification/domain/errors.py`:

```python
class NotificationError(Exception):
    """notification 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "NOTIFICATION_ERROR"


class NotificationInputError(NotificationError):
    """형식은 맞지만 규칙에 어긋난 입력(리마인드 시각 범위 밖, 주·일수 범위 밖). 422 다."""

    code = "VALIDATION_ERROR"


class ChannelNotLinkedError(NotificationError):
    """연동 전에 설정·재발송. 409."""

    code = "NOTIFICATION_CHANNEL_NOT_LINKED"


class ChannelAlreadyLinkedError(NotificationError):
    """이미 연동된 매장에 다시 연동. 409."""

    code = "NOTIFICATION_CHANNEL_LINKED"


class TokenInvalidError(NotificationError):
    """6자리가 틀렸거나 만료됐다. 400."""

    code = "NOTIFICATION_TOKEN_INVALID"


class SenderNotVerifiedError(NotificationError):
    """발신번호 인증 없이 문자 대체를 켠다. 409."""

    code = "NOTIFICATION_SENDER_NOT_VERIFIED"


class TemplateNotApprovedError(NotificationError):
    """미승인 종류를 다시 보내려 한다. 409."""

    code = "NOTIFICATION_TEMPLATE_NOT_APPROVED"


class MessageAlreadyPendingError(NotificationError):
    """같은 방문·종류의 줄이 대기 중인데 다시 보낸다. 409."""

    code = "NOTIFICATION_ALREADY_PENDING"


class MessageNotFoundError(NotificationError):
    """그 메시지가 없거나 다른 매장의 것이다. 404."""

    code = "NOTIFICATION_MESSAGE_NOT_FOUND"


class MessageNotRetryableError(NotificationError):
    """영구 실패가 아닌 줄에 [다시 보내기]. 409."""

    code = "NOTIFICATION_NOT_RETRYABLE"


class TooManyNotificationRequestsError(NotificationError):
    """토큰·인증번호 요청이 너무 잦다. 429."""

    code = "NOTIFICATION_RATE_LIMITED"


class ProviderUnavailableError(NotificationError):
    """온보딩 요청 중 업체 오류·시간 초과. 502."""

    code = "NOTIFICATION_PROVIDER_UNAVAILABLE"
```

`backend/apps/notification/CLAUDE.md`: `_docs/CLAUDE.md`를 가리키는 심볼릭 링크다(다른 스포크와 같다) — `ln -s _docs/CLAUDE.md backend/apps/notification/CLAUDE.md`

`backend/apps/notification/__init__.py`:

```python

```

`backend/apps/notification/_docs/CLAUDE.md`:

```markdown
# notification — 알림톡 자동 발송(예약 접수·전날 리마인드·알림장·변경·취소·다음 예약 제안), 매장 채널 연동, 문자 대체

소유 데이터: `notification_channels`, `notification_settings`, `notification_templates`, `notification_messages`(큐이자 발송 기록).
```

`backend/apps/notification/adapter/__init__.py`:

```python

```

`backend/apps/notification/adapter/inbound/__init__.py`:

```python

```

`backend/apps/notification/adapter/inbound/api/__init__.py`:

```python

```

`backend/apps/notification/adapter/inbound/api/error_map.py`:

```python
"""notification 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    MessageNotRetryableError,
    NotificationInputError,
    ProviderUnavailableError,
    SenderNotVerifiedError,
    TemplateNotApprovedError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)

NOTIFICATION_ERROR_STATUS: dict[type[Exception], int] = {
    NotificationInputError: 422,
    ChannelNotLinkedError: 409,
    ChannelAlreadyLinkedError: 409,
    TokenInvalidError: 400,
    SenderNotVerifiedError: 409,
    TemplateNotApprovedError: 409,
    MessageAlreadyPendingError: 409,
    MessageNotFoundError: 404,
    MessageNotRetryableError: 409,
    TooManyNotificationRequestsError: 429,
    ProviderUnavailableError: 502,
}
```

`backend/apps/notification/domain/__init__.py`:

```python

```

`backend/apps/notification/domain/entities/__init__.py`:

```python

```

`backend/apps/notification/domain/entities/notification_channel.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from notification.domain.value_objects.channel_status import LINKED


@dataclass(frozen=True)
class NotificationChannel:
    """매장의 카카오톡 채널(발신프로필) 연동 한 줄(설계 4.1). 매장당 하나다."""

    shop_id: int
    status: str
    provider: str
    provider_channel_id: str | None
    linked_at: datetime | None
    unlinked_at: datetime | None
    sender_number: str | None                     # 문자 대체용 발신번호
    sender_number_verified_at: datetime | None    # 본인인증 전엔 None
    sms_fallback_enabled: bool

    @property
    def is_linked(self) -> bool:
        return self.status == LINKED

    @property
    def can_fallback(self) -> bool:
        """문자 대체는 켜져 있고 발신번호 인증을 마쳤을 때만(N11)."""
        return self.sms_fallback_enabled and self.sender_number_verified_at is not None
```

`backend/apps/notification/domain/entities/notification_settings.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT


@dataclass(frozen=True)
class NotificationSettings:
    """매장의 알림톡 설정(설계 4.2). 값 객체 성격이지만 매장당 한 줄이라 엔티티 자리에 둔다."""

    confirm_enabled: bool
    reminder_enabled: bool
    report_enabled: bool
    change_enabled: bool                 # change·cancel 둘을 켠다
    next_visit_enabled: bool
    reminder_time: time                  # 매장 시간대의 벽시계 시각
    next_visit_after_weeks: int | None   # None = 지난 방문 간격(없으면 4주)
    next_visit_cooldown_days: int

    def enabled_for(self, kind: str) -> bool:
        return {
            CONFIRM: self.confirm_enabled,
            REMINDER: self.reminder_enabled,
            REPORT: self.report_enabled,
            CHANGE: self.change_enabled,
            CANCEL: self.change_enabled,
            NEXT_VISIT: self.next_visit_enabled,
        }[kind]


DEFAULT_NOTIFICATION_SETTINGS = NotificationSettings(
    confirm_enabled=True, reminder_enabled=True, report_enabled=True, change_enabled=True,
    next_visit_enabled=False, reminder_time=time(18, 0), next_visit_after_weeks=None,
    next_visit_cooldown_days=30,
)
```

`backend/apps/notification/domain/entities/notification_template.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NotificationTemplate:
    """매장 채널에 등록한 종류별 템플릿 한 줄(설계 4.3). 문안은 코드에 있고(text_version) 여기엔 심사 상태만 있다."""

    id: int
    shop_id: int
    kind: str
    text_version: int
    provider_template_id: str
    status: str
    rejected_reason: str | None
    requested_at: datetime
    decided_at: datetime | None
```

`backend/apps/notification/domain/services/__init__.py`:

```python

```

`backend/apps/notification/domain/value_objects/__init__.py`:

```python

```

`backend/apps/notification/domain/value_objects/channel_status.py`:

```python
"""매장 채널(발신프로필) 연동 상태(설계 4.1)."""
TOKEN_REQUESTED, LINKED, UNLINKED = "token_requested", "linked", "unlinked"
CHANNEL_STATUSES: tuple[str, ...] = (TOKEN_REQUESTED, LINKED, UNLINKED)
```

`backend/apps/notification/domain/value_objects/new_message.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewMessage:
    """새로 넣을 알림 줄 하나 — 저장소 create 의 입력. 즉시 보낼 것은 scheduled_at 이 만든 시각이다."""

    shop_id: int
    visit_id: int
    customer_id: int
    kind: str
    scheduled_at: datetime            # UTC
    variables: Mapping[str, str]      # 이벤트에서만 알 수 있는 값(알림장 주소·기간, 바뀌기 전 시각 …)
    requested_by_member_id: int | None = None   # 매장이 [다시 보내기]로 만든 줄이면 멤버 ID
```

`backend/apps/notification/domain/value_objects/template_status.py`:

```python
"""템플릿 심사 상태(설계 4.3)."""
PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
TEMPLATE_STATUSES: tuple[str, ...] = (PENDING, APPROVED, REJECTED)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 테스트(`apps/notification`, 네 파일) | 101 passed (변이 검사 중 간격 경우 2개를 더해 99 → 101) |
| 단위 전체 (`-m "not integration and not network"`) | 1419 passed (시작 1318 + 101) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken (`notification` 은 아직 계약에 없음 — 작업 4) |

(단위의 warning 1은 기존 `starlette.testclient` 사용 중단 경고다.)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `deferred_for_daytime` 의 `local.time() > DAY_END` → `>=` → `test_schedule_rules.py::test_야간이면_아침_8시로_미룬다[at3-expected3]` (21:00 경계)
- `reminder_at` 이 `starts_at.date()`(UTC 날짜)로 전날을 셈 → `test_schedule_rules.py::test_전날은_매장_시간대의_날짜로_센다`
- `render` 의 본문 치환을 두 번(`PLACEHOLDER.sub(fill, PLACEHOLDER.sub(fill, body))`) → `test_templates.py::test_값에_든_변수_모양은_글자로_남는다`
- `sms_channel` 이 `len(sms_text)` 로 셈 → `test_templates.py::test_한글_45자는_sms_46자는_lms`, `::test_알림장_문자는_실제_길이의_주소를_넣으면_lms_다`
- `interval_weeks` 가 `days // 7`(내림) → `test_schedule_rules.py::test_간격은_날짜_차를_주로_반올림한다[25-4]` — 브리프의 10일은 내림에서도 1 이라 잡지 못해 `[11-2]`(내림 1)·`[8-1]`(올림 2) 경우를 더했다. 다시 돌려 `[11-2]`·`[25-4]` 둘이 실패
- `enabled_for` 의 `CANCEL: self.change_enabled` → `CANCEL: True` → `test_entities.py::test_종류마다_켜짐을_정하는_칸이_있고_취소는_변경_칸을_따른다[cancel-change_enabled]`
- `error_map.py` 에서 `MessageNotRetryableError: 409,` 줄 제거 → `test_notification_error_map.py::test_모든_notification_오류가_HTTP_상태를_갖는다`, `::test_오류의_코드와_상태[MessageNotRetryableError-NOTIFICATION_NOT_RETRYABLE-409]`
- `is_too_late` 의 `>` → `>=` → `test_schedule_rules.py::test_정확히_1시간_전은_늦지_않고_59분_전은_늦다`
- `retry_at` 의 `attempts >= MAX_ATTEMPTS` → `>` → `test_schedule_rules.py::test_재시도_간격과_상한`
- `_clip` 이 주소(`링크`)도 200자에서 자름 → `test_templates.py::test_긴_값은_200자에서_자르고_주소는_자르지_않는다`
- `reminder_at` 의 `at > now` → `at >= now`(지금과 같으면 값) → `test_schedule_rules.py::test_리마인드_시각이_지금이거나_지났으면_없다`
- `can_fallback` 이 `sender_number_verified_at` 을 보지 않음 → `test_entities.py::test_문자_대체는_켜져_있고_발신번호_인증까지_마쳐야_한다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 도메인 — 채널·설정·템플릿·메시지, 시각 규칙(전날 리마인드·야간 미룸·재시도), 문안 6종과 변수, 오류

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 표 넷(마이그레이션 0011)·ORM·매퍼·저장소 포트 다섯과 pg 구현 — 큐는 SKIP LOCKED 로 집고, 같은 방문·종류의 대기 줄은 하나

**Files:**
- Create: `backend/alembic/versions/0011_notification.py`
- Create: `backend/apps/notification/adapter/outbound/orm/notification_orm.py`
- Create: `backend/apps/notification/app/ports/output/notification_queue_repository.py`
- Create: `backend/apps/notification/app/ports/output/message_repository.py`
- Modify: `backend/.importlinter`
- Create: `backend/apps/notification/adapter/outbound/__init__.py`
- Create: `backend/apps/notification/adapter/outbound/mappers/__init__.py`
- Create: `backend/apps/notification/adapter/outbound/mappers/notification_mapper.py`
- Create: `backend/apps/notification/adapter/outbound/orm/__init__.py`
- Create: `backend/apps/notification/adapter/outbound/pg/__init__.py`
- Create: `backend/apps/notification/adapter/outbound/pg/channel_pg_repository.py`
- Create: `backend/apps/notification/adapter/outbound/pg/message_pg_repository.py`
- Create: `backend/apps/notification/adapter/outbound/pg/settings_pg_repository.py`
- Create: `backend/apps/notification/adapter/outbound/pg/template_pg_repository.py`
- Create: `backend/apps/notification/app/__init__.py`
- Create: `backend/apps/notification/app/ports/__init__.py`
- Create: `backend/apps/notification/app/ports/output/__init__.py`
- Create: `backend/apps/notification/app/ports/output/channel_repository.py`
- Create: `backend/apps/notification/app/ports/output/settings_repository.py`
- Create: `backend/apps/notification/app/ports/output/template_repository.py`
- Create: `backend/apps/notification/dependencies/__init__.py`
- Create: `backend/apps/notification/dependencies/notification_wiring.py`
- Modify: `backend/apps/notification/domain/entities/notification_message.py`
- Modify: `backend/apps/notification/domain/value_objects/new_message.py`
- Create: `backend/apps/notification/tests/adapter/test_notification_pg_repositories.py`
- Modify: `backend/apps/notification/tests/helpers/builders.py`
- Create: `backend/apps/notification/tests/helpers/fakes.py`
- Create: `backend/apps/notification/tests/test_fakes.py`
- Create: `backend/apps/notification/tests/test_fakes_are_ports.py`
- Modify: `backend/orm_registry.py`
- Create: `backend/tests/integration/test_notification_schema.py`
- Create: `backend/tests/test_importlinter_lists_spokes.py`

**Interfaces:**
- Consumes: 작업 3 의 엔티티·값 객체·`KINDS`·`STATUSES`·`CANCEL_REASONS`; 기존 `core.database`, `orm_registry`, `.importlinter`, `tests/test_schema_drift.py`, visit 의 pg 저장소·매퍼 모양, `ShopContext`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# alembic: revision "0011", down_revision "0010". 표 notification_channels · notification_settings · notification_templates · notification_messages
# CHECK 이름(ck_<표>_<칸>): ck_notification_channels_status · ck_notification_channels_fallback ·
#   ck_notification_settings_reminder_time · _next_visit_after_weeks · _next_visit_cooldown_days ·
#   ck_notification_templates_kind · _status · ck_notification_messages_kind · _status · _channel_used · _error_kind ·
#   _canceled_reason · ck_notification_messages_canceled (canceled_reason IS NULL OR status = 'canceled')
# UNIQUE uq_notification_templates_shop_kind(shop_id, kind)
# 색인: uq_notification_messages_pending(visit_id, kind) WHERE status IN ('scheduled','sending') ·
#   ix_notification_messages_due(status, scheduled_at) · _cooldown(customer_id, kind, sent_at) · _shop_day(shop_id, created_at) · _visit(visit_id)

# notification.domain (T3 에서 바뀐 것)
class NotificationMessage: ...; customer_id: int; pet_id: int | None; kind: str; ...     # pet_id 가 customer_id 뒤
class NewMessage: shop_id: int; visit_id: int; customer_id: int; pet_id: int | None; kind: str; scheduled_at: datetime
                  variables: Mapping[str, str]; requested_by_member_id: int | None = None

# notification.adapter.outbound.orm.notification_orm
class NotificationChannelOrm(Base)   # notification_channels
class NotificationSettingsOrm(Base)  # notification_settings
class NotificationTemplateOrm(Base)  # notification_templates
class NotificationMessageOrm(Base)   # notification_messages — variables: JSONB(dict)

# notification.adapter.outbound.mappers.notification_mapper
def to_channel(orm) -> NotificationChannel;  def channel_values(channel) -> dict      # 키를 뺀 칸(upsert 용)
def to_settings(orm) -> NotificationSettings; def settings_values(settings) -> dict
def to_template(orm) -> NotificationTemplate; def to_message(orm) -> NotificationMessage   # variables=dict(orm.variables)

# notification.app.ports.output.channel_repository
class ChannelRepository(ABC):
    async def get(self, ctx: ShopContext) -> NotificationChannel | None
    async def save(self, ctx: ShopContext, channel: NotificationChannel) -> NotificationChannel   # shop_id upsert. channel.shop_id != ctx.shop_id → ValueError

# notification.app.ports.output.settings_repository
class SettingsRepository(ABC):
    async def get(self, ctx) -> NotificationSettings | None            # 행 없으면 None
    async def ensure(self, ctx) -> NotificationSettings                # 없으면 DEFAULT_NOTIFICATION_SETTINGS 로 INSERT … ON CONFLICT DO NOTHING 뒤 읽기
    async def update(self, ctx, settings: NotificationSettings) -> NotificationSettings   # 행이 없으면 NoResultFound(ensure 뒤에만)

# notification.app.ports.output.template_repository
class TemplateRepository(ABC):
    async def list_for_shop(self, ctx) -> list[NotificationTemplate]   # KINDS 순
    async def get(self, ctx, kind: str) -> NotificationTemplate | None
    async def upsert(self, ctx, kind: str, text_version: int, provider_template_id: str, requested_at: datetime) -> NotificationTemplate
        # ON CONFLICT (shop_id, kind) → text_version·provider_template_id·requested_at 새로, status=pending, rejected_reason=None, decided_at=None. id 유지
    async def set_status(self, ctx, kind: str, status: str, rejected_reason: str | None, decided_at: datetime) -> None   # 줄 없으면 무시
    async def delete_all(self, ctx) -> int

# notification.app.ports.output.message_repository
class MessageRepository(ABC):
    async def create(self, ctx, new: NewMessage) -> NotificationMessage
        # shop_id=ctx.shop_id 로 INSERT(new.shop_id 가 다르면 ValueError). 부분 유일 색인 위반 → MessageAlreadyPendingError(세이브포인트)
        # status·attempts·variables 기본은 DB 가(server_default), created_at 은 DB now()
    async def cancel_pending(self, ctx, reason: str, visit_id: int | None = None, kinds: Iterable[str] | None = None) -> int
    async def list_pending(self, ctx, kind: str) -> list[NotificationMessage]        # status == scheduled, scheduled_at·id 순
    async def has_delivered(self, ctx, visit_id: int, kind: str, url: str | None = None) -> bool   # url → variables->>'url' == url
    async def last_delivered_at(self, ctx, customer_id: int, kind: str) -> datetime | None       # max(sent_at), DELIVERED_STATUSES
    async def count_sent_since(self, ctx, since: datetime) -> int                   # provider_message_id IS NOT NULL AND created_at >= since
    async def list_for_visit(self, ctx, visit_id: int) -> list[NotificationMessage]   # created_at desc, id desc
    async def get(self, ctx, message_id: int) -> NotificationMessage | None
    async def save(self, ctx, message: NotificationMessage) -> None
        # WHERE shop_id = ctx.shop_id AND id. SET status, attempts, next_attempt_at, scheduled_at, channel_used, provider_message_id, error_code, error_kind, sent_at, canceled_reason

# notification.app.ports.output.notification_queue_repository  (ShopContext 없음 — 디스패처 전용)
class NotificationQueueRepository(ABC):
    async def claim_due(self, now: datetime, limit: int) -> list[NotificationMessage]
        # UPDATE … SET status='sending', updated_at=now WHERE id IN (SELECT id … status='scheduled' AND scheduled_at <= now ORDER BY scheduled_at, id LIMIT limit FOR UPDATE SKIP LOCKED) RETURNING — 한 문장. 반환은 (scheduled_at, id) 순. 커밋은 부르는 쪽
    async def recover_stuck(self, before: datetime) -> int       # status='sending' AND updated_at < before → scheduled, attempts+1
    async def list_accepted(self, now: datetime) -> list[NotificationMessage]   # status='accepted' AND next_attempt_at <= now, next_attempt_at·id 순
    async def list_pending_templates(self) -> list[NotificationTemplate]        # status=pending, id 순
    async def list_linked_channels(self) -> list[NotificationChannel]           # status=linked, shop_id 순
    async def list_templates_for_shops(self, shop_ids: list[int]) -> dict[int, list[NotificationTemplate]]   # 넘긴 매장마다 키가 있고(없으면 []), KINDS 순. [] → {}

# notification.adapter.outbound.pg
class ChannelPgRepository(ChannelRepository)(session: AsyncSession)
class SettingsPgRepository(SettingsRepository)(session)
class TemplatePgRepository(TemplateRepository)(session);  def by_kind(templates) -> list   # KINDS 순 정렬(모듈 함수, message 저장소도 씀)
class MessagePgRepository(MessageRepository, NotificationQueueRepository)(session)

# notification.dependencies.notification_wiring
def build_channel_repository(db: AsyncSession) -> ChannelRepository
def build_settings_repository(db: AsyncSession) -> SettingsRepository
def build_template_repository(db: AsyncSession) -> TemplateRepository
def build_message_repository(db: AsyncSession) -> MessagePgRepository

# notification.tests.helpers.fakes
class Journal(list)
class FakeChannels(ChannelRepository):   __init__(journal: Journal | None = None); rows: dict[int, NotificationChannel]
class FakeSettings(SettingsRepository):  __init__(journal=None); rows: dict[int, NotificationSettings]
class FakeTemplates(TemplateRepository): __init__(journal=None); rows: dict[tuple[int, str], NotificationTemplate]
class FakeMessages(MessageRepository, NotificationQueueRepository):
    __init__(journal: Journal | None = None, templates: FakeTemplates | None = None, channels: FakeChannels | None = None)
    rows: dict[int, NotificationMessage]; claimed_at: dict[int, datetime]; templates; channels
    # create: 매장 불문 (visit_id, kind) 에 PENDING 줄이 있으면 MessageAlreadyPendingError. created_at = new.scheduled_at
    # claim_due: 집은 줄을 sending 으로, claimed_at[id] = now. recover_stuck: claimed_at < before 인 sending 만
    # list_pending_templates·list_linked_channels·list_templates_for_shops: 넘긴 templates·channels 스텁의 rows 를 본다
    # journal 항목: ("create_message", visit_id, kind) · ("cancel_pending", visit_id, reason) · ("save_message", id, status) ·
    #   ("claim_due", [ids]) · ("recover_stuck", [ids]) · ("save_channel", shop_id, status) · ("ensure_settings", shop_id) ·
    #   ("update_settings", shop_id) · ("upsert_template", shop_id, kind) · ("set_template_status", shop_id, kind, status) · ("delete_templates", shop_id)

# notification.tests.helpers.builders (더한 것)
def new_message(**overrides) -> NewMessage   # 기본: shop 1, visit 1, customer 1, pet None, confirm, kst(10,14,11), variables {}, requested_by None
```

저장 계층이다. `notification_channels`·`notification_settings`·`notification_templates`·`notification_messages` 넷과 CHECK 13개, 부분 유일 색인 `uq_notification_messages_pending`(`(visit_id, kind)` WHERE status IN (scheduled, sending) — 같은 방문·종류의 대기 줄은 하나), 색인 다섯. 포트 다섯 가운데 넷은 `ShopContext` 가 첫 인자이고 **`NotificationQueueRepository` 만 ctx 없이** 전 매장을 본다(디스패처 전용 — `claim_due` 는 `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING` 한 문장). `.importlinter` 의 일곱 목록에 `notification` 을 더하고, 빠뜨리면 잡는 `tests/test_importlinter_lists_spokes.py` 를 둔다. 이 작업이 `NotificationMessage`·`NewMessage` 에 `pet_id` 칸을 더한다(`#{대상}` 에 아이 이름을 넣으려고).

**마이그레이션은 이 작업 끝에 개발 DB 에 올린다**(`docker compose run --rm backend alembic upgrade head`). 그 전까지 통합 테스트는 테스트 DB(`chagocnote_test`)만 쓴다. `downgrade` 는 돌리지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/adapter/test_notification_pg_repositories.py`:

```python
"""notification 저장소 넷을 실제 DB 로 본다 — 매장 범위, DB CHECK, 같은 방문·종류의 대기 줄 하나, 큐의 SKIP LOCKED."""
import asyncio
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED, UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    FAILED,
    FALLBACK_SENT,
    SCHEDULED,
    SENDING,
    SENT,
)
from notification.domain.value_objects.template_status import APPROVED, PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, new_message, settings

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(10, 14, 11)
HOUR, MINUTE = timedelta(hours=1), timedelta(minutes=1)
BLOCKED = 0.5


# --- 채널 -------------------------------------------------------------------------------------------------------

async def test_채널은_매장당_한_줄이고_다시_저장하면_덮는다(db_session):
    repo = ChannelPgRepository(db_session)
    assert await repo.get(A) is None
    saved = await repo.save(A, channel())
    assert saved == channel() and await repo.get(A) == saved
    again = await repo.save(A, channel(status=UNLINKED, unlinked_at=NOW, sender_number="01012345678"))
    assert (again.status, again.unlinked_at, again.sender_number) == (UNLINKED, NOW, "01012345678")
    assert await repo.get(A) == again
    assert await repo.get(B) is None


async def test_채널의_매장이_컨텍스트와_다르면_ValueError_다(db_session):
    with pytest.raises(ValueError):
        await ChannelPgRepository(db_session).save(A, channel(shop_id=2))


async def test_발신번호_인증_없이_문자_대체를_켜면_DB_가_거절한다(db_session):
    repo = ChannelPgRepository(db_session)
    verified = await repo.save(A, channel(sender_number="01012345678", sender_number_verified_at=NOW,
                                          sms_fallback_enabled=True))
    assert verified.can_fallback is True
    with pytest.raises(IntegrityError):
        await repo.save(B, channel(shop_id=2, sms_fallback_enabled=True))


# --- 설정 -------------------------------------------------------------------------------------------------------

async def test_설정은_연동_전엔_없고_ensure_가_기본값으로_만든다(db_session):
    repo = SettingsPgRepository(db_session)
    assert await repo.get(A) is None
    assert await repo.ensure(A) == DEFAULT_NOTIFICATION_SETTINGS
    assert await repo.ensure(A) == DEFAULT_NOTIFICATION_SETTINGS
    changed = settings(reminder_time=time(9, 0), next_visit_enabled=True, next_visit_after_weeks=6,
                       next_visit_cooldown_days=45, confirm_enabled=False)
    assert await repo.update(A, changed) == changed
    assert await repo.get(A) == changed
    assert await repo.ensure(A) == changed   # 있는 행은 기본값으로 덮지 않는다
    assert await repo.get(B) is None
    assert await repo.ensure(B) == DEFAULT_NOTIFICATION_SETTINGS
    assert await repo.get(A) == changed


async def test_리마인드_시각_22시는_DB_가_거절한다(db_session):
    repo = SettingsPgRepository(db_session)
    await repo.ensure(A)
    with pytest.raises(IntegrityError):
        await repo.update(A, settings(reminder_time=time(22, 0)))


# --- 템플릿 -----------------------------------------------------------------------------------------------------

async def test_템플릿_upsert_는_같은_종류를_한_줄로_두고_pending_으로_되돌린다(db_session):
    repo = TemplatePgRepository(db_session)
    first = await repo.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    assert (first.shop_id, first.kind, first.text_version, first.provider_template_id) == (1, CONFIRM, 1, "KA01TP0001")
    assert (first.status, first.rejected_reason, first.requested_at, first.decided_at) == (PENDING, None, NOW, None)
    await repo.set_status(A, CONFIRM, REJECTED, "변수 이름이 맞지 않음", NOW + HOUR)
    rejected = await repo.get(A, CONFIRM)
    assert (rejected.status, rejected.rejected_reason, rejected.decided_at) == (REJECTED, "변수 이름이 맞지 않음", NOW + HOUR)
    again = await repo.upsert(A, CONFIRM, 2, "KA01TP0002", NOW + 2 * HOUR)
    assert again == replace(first, text_version=2, provider_template_id="KA01TP0002", requested_at=NOW + 2 * HOUR)
    assert await repo.list_for_shop(A) == [again]
    await repo.set_status(A, CONFIRM, APPROVED, None, NOW + 3 * HOUR)
    assert (await repo.get(A, CONFIRM)).status == APPROVED


async def test_템플릿_목록은_종류_순이고_매장을_거르며_delete_all_은_그_매장만_지운다(db_session):
    repo = TemplatePgRepository(db_session)
    for kind, provider_id in ((NEXT_VISIT, "KA01TP0006"), (CONFIRM, "KA01TP0001"), (REPORT, "KA01TP0003")):
        await repo.upsert(A, kind, 1, provider_id, NOW)
    theirs = await repo.upsert(B, CONFIRM, 1, "KA01TP0009", NOW)
    assert [t.kind for t in await repo.list_for_shop(A)] == [CONFIRM, REPORT, NEXT_VISIT]
    assert await repo.get(B, REPORT) is None
    assert await repo.get(A, REMINDER) is None
    await repo.set_status(B, REPORT, APPROVED, None, NOW)   # 없는 줄 — 아무것도 바꾸지 않는다
    assert await repo.delete_all(A) == 3
    assert await repo.list_for_shop(A) == []
    assert await repo.list_for_shop(B) == [theirs]
    assert await repo.delete_all(A) == 0


# --- 메시지 -----------------------------------------------------------------------------------------------------

async def test_메시지를_만들고_방문별로_최신순으로_읽는다(db_session):
    repo = MessagePgRepository(db_session)
    confirm = await repo.create(A, new_message(pet_id=101, variables={"url": "https://a/1"}, requested_by_member_id=11))
    assert (confirm.shop_id, confirm.visit_id, confirm.customer_id, confirm.pet_id, confirm.kind) == (1, 1, 1, 101, CONFIRM)
    assert (confirm.status, confirm.attempts, confirm.scheduled_at, confirm.variables) == (
        SCHEDULED, 0, NOW, {"url": "https://a/1"})
    assert (confirm.requested_by_member_id, confirm.sent_at, confirm.canceled_reason) == (11, None, None)
    assert confirm.created_at.tzinfo is not None
    reminder = await repo.create(A, new_message(kind=REMINDER, scheduled_at=NOW + HOUR))
    other = await repo.create(A, new_message(visit_id=2, kind=REMINDER))
    assert await repo.list_for_visit(A, 1) == [reminder, confirm]
    assert await repo.list_for_visit(A, 2) == [other]
    assert await repo.get(A, reminder.id) == reminder


async def test_같은_방문_같은_종류의_대기_줄은_하나이고_트랜잭션은_계속_쓸_수_있다(db_session):
    repo = MessagePgRepository(db_session)
    confirm = await repo.create(A, new_message())
    with pytest.raises(MessageAlreadyPendingError):
        await repo.create(A, new_message())
    reminder = await repo.create(A, new_message(kind=REMINDER))   # 같은 트랜잭션에서 다른 INSERT 가 된다
    assert [m.id for m in await repo.list_for_visit(A, 1)] == [reminder.id, confirm.id]


async def test_취소되거나_보낸_줄이_있으면_새_대기_줄을_만들_수_있다(db_session):
    repo = MessagePgRepository(db_session)
    await repo.create(A, new_message())
    assert await repo.cancel_pending(A, "rescheduled", visit_id=1, kinds=[CONFIRM]) == 1
    second = await repo.create(A, new_message())
    await repo.save(A, replace(second, status=SENT, sent_at=NOW, channel_used="alimtalk", provider_message_id="M2"))
    third = await repo.create(A, new_message())
    await repo.save(A, replace(third, status=SENDING))
    with pytest.raises(MessageAlreadyPendingError):   # sending 도 대기다
        await repo.create(A, new_message())
    assert [m.status for m in await repo.list_for_visit(A, 1)] == [SENDING, SENT, CANCELED]


async def test_대기_줄_취소의_세_범위_방문_종류_전체(db_session):
    repo = MessagePgRepository(db_session)
    v1_confirm = await repo.create(A, new_message(visit_id=1, kind=CONFIRM))
    v1_reminder = await repo.create(A, new_message(visit_id=1, kind=REMINDER))
    v2_confirm = await repo.create(A, new_message(visit_id=2, kind=CONFIRM))
    v2_reminder = await repo.create(A, new_message(visit_id=2, kind=REMINDER))
    v3_confirm = await repo.create(A, new_message(visit_id=3, kind=CONFIRM))
    theirs = await repo.create(B, new_message(shop_id=2, visit_id=9, kind=CONFIRM))   # 방문 ID 는 전 매장에서 유일하다
    assert await repo.cancel_pending(A, "no_show", visit_id=3) == 1
    assert await repo.cancel_pending(A, "rescheduled", visit_id=1, kinds=[REMINDER]) == 1
    assert await repo.cancel_pending(A, "visit_canceled", visit_id=2) == 2
    assert await repo.cancel_pending(A, "channel_unlinked") == 1   # 남은 대기 줄은 v1_confirm 뿐
    reasons = {m.id: (await repo.get(A, m.id)).canceled_reason
               for m in (v1_confirm, v1_reminder, v2_confirm, v2_reminder, v3_confirm)}
    assert reasons == {v1_confirm.id: "channel_unlinked", v1_reminder.id: "rescheduled",
                       v2_confirm.id: "visit_canceled", v2_reminder.id: "visit_canceled", v3_confirm.id: "no_show"}
    assert (await repo.get(B, theirs.id)).status == SCHEDULED


async def test_보낸_줄_판정은_보낸_상태만_세고_주소를_주면_같은_주소만_본다(db_session):
    repo = MessagePgRepository(db_session)
    assert await repo.has_delivered(A, 1, REPORT) is False
    report = await repo.create(A, new_message(kind=REPORT, variables={"url": "https://a/1"}))
    assert await repo.has_delivered(A, 1, REPORT) is False   # scheduled 는 보낸 게 아니다
    await repo.save(A, replace(report, status=SENT, sent_at=NOW, channel_used="alimtalk", provider_message_id="M1"))
    assert await repo.has_delivered(A, 1, REPORT) is True
    assert await repo.has_delivered(A, 1, REPORT, url="https://a/1") is True
    assert await repo.has_delivered(A, 1, REPORT, url="https://a/2") is False
    assert await repo.has_delivered(B, 1, REPORT) is False
    assert await repo.has_delivered(A, 1, CONFIRM) is False
    failed = await repo.create(A, new_message(kind=CONFIRM))
    await repo.save(A, replace(failed, status=FAILED, error_code="3000", error_kind="permanent"))
    assert await repo.has_delivered(A, 1, CONFIRM) is False
    fallback = await repo.create(A, new_message(visit_id=2, kind=CONFIRM))
    await repo.save(A, replace(fallback, status=FALLBACK_SENT, sent_at=NOW, channel_used="sms"))
    assert await repo.has_delivered(A, 2, CONFIRM) is True


async def test_마지막으로_보낸_시각은_고객_종류별로_가장_최근이다(db_session):
    repo = MessagePgRepository(db_session)
    assert await repo.last_delivered_at(A, 1, NEXT_VISIT) is None
    older = await repo.create(A, new_message(visit_id=1, kind=NEXT_VISIT))
    await repo.save(A, replace(older, status=SENT, sent_at=NOW - timedelta(days=10)))
    newer = await repo.create(A, new_message(visit_id=2, kind=NEXT_VISIT))
    await repo.save(A, replace(newer, status=FALLBACK_SENT, sent_at=NOW - timedelta(days=3)))
    unsent = await repo.create(A, new_message(visit_id=3, kind=NEXT_VISIT))
    await repo.save(A, replace(unsent, status=FAILED, sent_at=None))
    assert await repo.last_delivered_at(A, 1, NEXT_VISIT) == NOW - timedelta(days=3)
    assert await repo.last_delivered_at(A, 1, CONFIRM) is None
    assert await repo.last_delivered_at(A, 2, NEXT_VISIT) is None
    assert await repo.last_delivered_at(B, 1, NEXT_VISIT) is None


async def test_하루_상한은_업체에_넘긴_줄만_만든_시각으로_센다(db_session):
    repo = MessagePgRepository(db_session)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    assert await repo.count_sent_since(A, since) == 0
    rows = [await repo.create(A, new_message(visit_id=v)) for v in (1, 2, 3)]
    await repo.save(A, replace(rows[0], status=SENT, sent_at=NOW, provider_message_id="M1"))
    await repo.save(A, replace(rows[1], status=ACCEPTED, provider_message_id="M2"))
    await repo.save(A, replace(rows[2], status=FAILED, error_code="timeout", error_kind="transient"))
    assert await repo.count_sent_since(A, since) == 2
    assert await repo.count_sent_since(A, since + timedelta(days=2)) == 0
    assert await repo.count_sent_since(B, since) == 0


async def test_save_는_바뀔_수_있는_칸만_바꾼다(db_session):
    repo = MessagePgRepository(db_session)
    created = await repo.create(A, new_message(variables={"url": "https://a/1"}))
    changed = replace(
        created, status=ACCEPTED, attempts=1, next_attempt_at=NOW + MINUTE, scheduled_at=NOW + 2 * MINUTE,
        channel_used="alimtalk", provider_message_id="M1", error_code="x", error_kind="transient", sent_at=NOW,
        # 아래는 바뀌지 않아야 하는 칸
        kind=REPORT, visit_id=99, customer_id=99, pet_id=7, variables={"url": "https://a/2"},
        requested_by_member_id=11,
    )
    await repo.save(A, changed)
    saved = await repo.get(A, created.id)
    assert saved == replace(
        created, status=ACCEPTED, attempts=1, next_attempt_at=NOW + MINUTE, scheduled_at=NOW + 2 * MINUTE,
        channel_used="alimtalk", provider_message_id="M1", error_code="x", error_kind="transient", sent_at=NOW,
    )
    await repo.save(A, replace(saved, status=CANCELED, canceled_reason="too_late"))
    assert ((await repo.get(A, created.id)).status, (await repo.get(A, created.id)).canceled_reason) == (
        CANCELED, "too_late")


async def test_다른_매장_컨텍스트로는_메시지가_없는_것이다(db_session):
    repo = MessagePgRepository(db_session)
    created = await repo.create(A, new_message(kind=REPORT, variables={"url": "https://a/1"}))
    assert await repo.get(B, created.id) is None
    assert await repo.list_for_visit(B, 1) == []
    assert await repo.list_pending(B, REPORT) == []
    await repo.save(B, replace(created, status=FAILED))
    assert await repo.cancel_pending(B, "channel_unlinked") == 0
    assert (await repo.get(A, created.id)).status == SCHEDULED
    with pytest.raises(ValueError):
        await repo.create(B, new_message(shop_id=1, visit_id=2))


async def test_설정을_바꿀_때_다시_계산할_대기_줄은_scheduled_뿐이다(db_session):
    repo = MessagePgRepository(db_session)
    late = await repo.create(A, new_message(visit_id=1, kind=REMINDER, scheduled_at=NOW + 2 * HOUR))
    early = await repo.create(A, new_message(visit_id=2, kind=REMINDER, scheduled_at=NOW + HOUR))
    sending = await repo.create(A, new_message(visit_id=3, kind=REMINDER, scheduled_at=NOW))
    await repo.save(A, replace(sending, status=SENDING))
    await repo.create(A, new_message(visit_id=4, kind=CONFIRM))
    assert await repo.list_pending(A, REMINDER) == [early, late]


# --- 큐 ---------------------------------------------------------------------------------------------------------

async def _due_rows(repo):
    """scheduled_at 순서가 id 순서와 다르게 — 집는 순서가 id 가 아니라 시각임을 본다."""
    later = await repo.create(A, new_message(visit_id=1, scheduled_at=NOW - HOUR))
    earliest = await repo.create(A, new_message(visit_id=2, scheduled_at=NOW - 2 * HOUR))
    exact = await repo.create(A, new_message(visit_id=3, scheduled_at=NOW))
    await repo.create(A, new_message(visit_id=4, scheduled_at=NOW + MINUTE))              # 아직
    canceled = await repo.create(A, new_message(visit_id=5, scheduled_at=NOW - HOUR))
    await repo.cancel_pending(A, "visit_canceled", visit_id=5)
    return earliest, later, exact, canceled


async def test_큐는_시각이_된_scheduled_줄만_시각_순으로_limit_만큼_집어_sending_으로_바꾼다(db_session):
    repo = MessagePgRepository(db_session)
    earliest, later, exact, _ = await _due_rows(repo)
    claimed = await repo.claim_due(NOW, 2)
    assert [(m.id, m.status) for m in claimed] == [(earliest.id, SENDING), (later.id, SENDING)]
    assert (await repo.get(A, earliest.id)).status == SENDING
    assert [m.id for m in await repo.claim_due(NOW, 10)] == [exact.id]
    assert await repo.claim_due(NOW, 10) == []
    assert [m.id for m in await repo.claim_due(NOW + MINUTE, 10)] == [exact.id + 1]


async def test_두_세션이_동시에_집어도_같은_줄을_둘이_집지_않는다(db_engine, db_session):
    """N6 — 잠긴 줄을 건너뛰어야(SKIP LOCKED) 둘째 세션이 기다리지 않고 남은 줄만 받는다."""
    repo = MessagePgRepository(db_session)
    earliest, later, exact, _ = await _due_rows(repo)
    await db_session.commit()

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        mine = await MessagePgRepository(first).claim_due(NOW, 2)
        late = asyncio.create_task(MessagePgRepository(second).claim_due(NOW, 2))
        await asyncio.sleep(BLOCKED)
        returned_without_waiting = late.done()
        await first.commit()
        theirs = await late
        await second.commit()

    assert returned_without_waiting
    assert [m.id for m in mine] == [earliest.id, later.id]
    assert [m.id for m in theirs] == [exact.id]
    assert {m.status for m in await repo.list_for_visit(A, 3)} == {SENDING}


async def test_멈춘_sending_줄은_시간이_지난_것만_되돌리고_시도를_센다(db_session):
    repo = MessagePgRepository(db_session)
    earliest, later, exact, _ = await _due_rows(repo)
    await repo.claim_due(NOW, 2)                       # earliest, later 를 NOW 에 집었다
    await repo.claim_due(NOW + 3 * MINUTE, 1)          # exact 를 3분 뒤에 집었다
    assert await repo.recover_stuck(NOW) == 0          # 막 집은 것은 멈춘 게 아니다
    assert await repo.recover_stuck(NOW + 2 * MINUTE) == 2
    recovered = [await repo.get(A, m.id) for m in (earliest, later)]
    assert [(m.status, m.attempts) for m in recovered] == [(SCHEDULED, 1), (SCHEDULED, 1)]
    kept = await repo.get(A, exact.id)
    assert (kept.status, kept.attempts) == (SENDING, 0)
    assert [m.id for m in await repo.claim_due(NOW, 10)] == [earliest.id, later.id]   # 다시 집힌다
    assert await repo.recover_stuck(NOW + 10 * MINUTE) == 3


async def test_accepted_줄은_다음_확인_시각이_지난_것만_모은다(db_session):
    repo = MessagePgRepository(db_session)
    due = await repo.create(A, new_message(visit_id=1))
    later = await repo.create(A, new_message(visit_id=2))
    exact = await repo.create(A, new_message(visit_id=3))
    sent = await repo.create(A, new_message(visit_id=4))
    await repo.save(A, replace(due, status=ACCEPTED, provider_message_id="M1", next_attempt_at=NOW - MINUTE))
    await repo.save(A, replace(later, status=ACCEPTED, provider_message_id="M2", next_attempt_at=NOW + MINUTE))
    await repo.save(A, replace(exact, status=ACCEPTED, provider_message_id="M3", next_attempt_at=NOW))
    await repo.save(A, replace(sent, status=SENT, provider_message_id="M4", sent_at=NOW, next_attempt_at=NOW - MINUTE))
    assert [m.id for m in await repo.list_accepted(NOW)] == [due.id, exact.id]


async def test_큐의_전_매장_조회는_매장을_가리지_않고_모은다(db_session):
    channels, templates, repo = ChannelPgRepository(db_session), TemplatePgRepository(db_session), MessagePgRepository(db_session)
    await channels.save(A, channel(shop_id=1, status=LINKED))
    await channels.save(B, channel(shop_id=2, status=UNLINKED, unlinked_at=NOW))
    await channels.save(ctx(shop_id=3), channel(shop_id=3, status=LINKED))
    a_next = await templates.upsert(A, NEXT_VISIT, 1, "KA01TP0006", NOW)
    a_confirm = await templates.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    b_confirm = await templates.upsert(B, CONFIRM, 1, "KA01TP0009", NOW)
    await templates.set_status(A, CONFIRM, APPROVED, None, NOW)
    a_confirm = await templates.get(A, CONFIRM)
    assert [c.shop_id for c in await repo.list_linked_channels()] == [1, 3]
    assert await repo.list_pending_templates() == [a_next, b_confirm]
    assert await repo.list_templates_for_shops([1, 2, 4]) == {1: [a_confirm, a_next], 2: [b_confirm], 4: []}
    assert await repo.list_templates_for_shops([]) == {}
```

`backend/apps/notification/tests/helpers/builders.py`:

```diff
@@ -11,6 +11,7 @@ from notification.domain.entities.notification_template import NotificationTempl
 from notification.domain.value_objects.channel_status import LINKED
 from notification.domain.value_objects.message_kind import CONFIRM
 from notification.domain.value_objects.message_status import SCHEDULED
+from notification.domain.value_objects.new_message import NewMessage
 from notification.domain.value_objects.template_status import APPROVED
 
 STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
@@ -64,10 +65,19 @@ def template(**overrides) -> NotificationTemplate:
 
 def message(**overrides) -> NotificationMessage:
     fields = dict(
-        id=1, shop_id=1, visit_id=1, customer_id=1, kind=CONFIRM, scheduled_at=kst(10, 14, 11),
+        id=1, shop_id=1, visit_id=1, customer_id=1, pet_id=None, kind=CONFIRM, scheduled_at=kst(10, 14, 11),
         status=SCHEDULED, attempts=0, next_attempt_at=None, channel_used=None, provider_message_id=None,
         error_code=None, error_kind=None, variables={}, requested_by_member_id=None,
         created_at=kst(10, 14, 11), sent_at=None, canceled_reason=None,
     )
     fields.update(overrides)
     return NotificationMessage(**fields)
+
+
+def new_message(**overrides) -> NewMessage:
+    fields = dict(
+        shop_id=1, visit_id=1, customer_id=1, pet_id=None, kind=CONFIRM, scheduled_at=kst(10, 14, 11), variables={},
+        requested_by_member_id=None,
+    )
+    fields.update(overrides)
+    return NewMessage(**fields)
```

`backend/apps/notification/tests/helpers/fakes.py`:

```python
"""notification 구독자·디스패처·인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남긴다.

스텁은 포트 ABC 를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간(TypeError) 잡힌다.
`apps/notification/tests/test_fakes_are_ports.py`가 이를 확인한다. 매장 범위 메서드는 ctx.shop_id 로 거른다.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS, NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    DELIVERED_STATUSES,
    PENDING_STATUSES,
    SCHEDULED,
    SENDING,
)
from notification.domain.value_objects.template_status import PENDING


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeChannels(ChannelRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, NotificationChannel] = {}

    async def get(self, ctx):
        return self.rows.get(ctx.shop_id)

    async def save(self, ctx, channel):
        if channel.shop_id != ctx.shop_id:
            raise ValueError("채널의 매장이 컨텍스트의 매장과 다릅니다.")
        self.rows[ctx.shop_id] = channel
        self.journal.append(("save_channel", ctx.shop_id, channel.status))
        return channel


class FakeSettings(SettingsRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, NotificationSettings] = {}

    async def get(self, ctx):
        return self.rows.get(ctx.shop_id)

    async def ensure(self, ctx):
        self.journal.append(("ensure_settings", ctx.shop_id))
        return self.rows.setdefault(ctx.shop_id, DEFAULT_NOTIFICATION_SETTINGS)

    async def update(self, ctx, settings):
        self.rows[ctx.shop_id] = settings
        self.journal.append(("update_settings", ctx.shop_id))
        return settings


class FakeTemplates(TemplateRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[tuple[int, str], NotificationTemplate] = {}

    async def list_for_shop(self, ctx):
        return sorted((t for t in self.rows.values() if t.shop_id == ctx.shop_id), key=lambda t: KINDS.index(t.kind))

    async def get(self, ctx, kind):
        return self.rows.get((ctx.shop_id, kind))

    async def upsert(self, ctx, kind, text_version, provider_template_id, requested_at):
        current = self.rows.get((ctx.shop_id, kind))
        template = NotificationTemplate(
            id=current.id if current is not None else len(self.rows) + 1, shop_id=ctx.shop_id, kind=kind,
            text_version=text_version, provider_template_id=provider_template_id, status=PENDING,
            rejected_reason=None, requested_at=requested_at, decided_at=None,
        )
        self.rows[(ctx.shop_id, kind)] = template
        self.journal.append(("upsert_template", ctx.shop_id, kind))
        return template

    async def set_status(self, ctx, kind, status, rejected_reason, decided_at):
        current = self.rows.get((ctx.shop_id, kind))
        if current is not None:
            self.rows[(ctx.shop_id, kind)] = replace(
                current, status=status, rejected_reason=rejected_reason, decided_at=decided_at)
        self.journal.append(("set_template_status", ctx.shop_id, kind, status))

    async def delete_all(self, ctx):
        mine = [key for key in self.rows if key[0] == ctx.shop_id]
        for key in mine:
            del self.rows[key]
        self.journal.append(("delete_templates", ctx.shop_id))
        return len(mine)


class FakeMessages(MessageRepository, NotificationQueueRepository):
    """notification_messages 스텁 — pg 구현처럼 두 포트를 한 객체가 낸다.

    같은 방문·종류의 대기 줄이 있으면 MessageAlreadyPendingError(부분 유일 색인). created_at 은 scheduled_at 으로 둔다
    (즉시 보낼 줄은 둘이 같다). 전 매장 조회는 함께 넘긴 templates·channels 스텁을 본다. recover_stuck 은 claim_due 로
    집은 줄만 되돌린다(집은 시각을 claimed_at 에 적는다).
    """

    def __init__(
        self, journal: Journal | None = None, templates: FakeTemplates | None = None,
        channels: FakeChannels | None = None,
    ) -> None:
        self.journal = journal if journal is not None else Journal()
        self.templates = templates if templates is not None else FakeTemplates(self.journal)
        self.channels = channels if channels is not None else FakeChannels(self.journal)
        self.rows: dict[int, NotificationMessage] = {}
        self.claimed_at: dict[int, datetime] = {}

    def _mine(self, ctx, **fields) -> list[NotificationMessage]:
        return [m for m in self.rows.values()
                if m.shop_id == ctx.shop_id and all(getattr(m, k) == v for k, v in fields.items())]

    def _put(self, message: NotificationMessage) -> None:
        self.rows[message.id] = message

    # --- 매장 범위 ----------------------------------------------------------------------------------------------

    async def create(self, ctx, new):
        if new.shop_id != ctx.shop_id:
            raise ValueError("메시지의 매장이 컨텍스트의 매장과 다릅니다.")
        # 부분 유일 색인은 (visit_id, kind) 라 매장을 가리지 않는다 — 방문 ID 는 전 매장에서 유일하다.
        if any(m.status in PENDING_STATUSES and (m.visit_id, m.kind) == (new.visit_id, new.kind)
               for m in self.rows.values()):
            raise MessageAlreadyPendingError("같은 방문·종류의 알림이 이미 대기 중입니다.")
        message = NotificationMessage(
            id=len(self.rows) + 1, shop_id=ctx.shop_id, visit_id=new.visit_id, customer_id=new.customer_id,
            pet_id=new.pet_id, kind=new.kind, scheduled_at=new.scheduled_at, status=SCHEDULED, attempts=0,
            next_attempt_at=None, channel_used=None, provider_message_id=None, error_code=None, error_kind=None,
            variables=dict(new.variables), requested_by_member_id=new.requested_by_member_id,
            created_at=new.scheduled_at, sent_at=None, canceled_reason=None,
        )
        self._put(message)
        self.journal.append(("create_message", new.visit_id, new.kind))
        return message

    async def cancel_pending(self, ctx, reason, visit_id=None, kinds=None):
        kinds = None if kinds is None else set(kinds)
        targets = [
            m for m in self._mine(ctx)
            if m.status in PENDING_STATUSES and (visit_id is None or m.visit_id == visit_id)
            and (kinds is None or m.kind in kinds)
        ]
        for m in targets:
            self._put(replace(m, status=CANCELED, canceled_reason=reason))
        self.journal.append(("cancel_pending", visit_id, reason))
        return len(targets)

    async def list_pending(self, ctx, kind):
        return sorted(self._mine(ctx, kind=kind, status=SCHEDULED), key=lambda m: (m.scheduled_at, m.id))

    async def has_delivered(self, ctx, visit_id, kind, url=None):
        return any(
            m.status in DELIVERED_STATUSES and (url is None or m.variables.get("url") == url)
            for m in self._mine(ctx, visit_id=visit_id, kind=kind)
        )

    async def last_delivered_at(self, ctx, customer_id, kind):
        sent = [m.sent_at for m in self._mine(ctx, customer_id=customer_id, kind=kind)
                if m.status in DELIVERED_STATUSES and m.sent_at is not None]
        return max(sent) if sent else None

    async def count_sent_since(self, ctx, since):
        return sum(1 for m in self._mine(ctx) if m.provider_message_id is not None and m.created_at >= since)

    async def list_for_visit(self, ctx, visit_id):
        return sorted(self._mine(ctx, visit_id=visit_id), key=lambda m: (m.created_at, m.id), reverse=True)

    async def get(self, ctx, message_id):
        current = self.rows.get(message_id)
        return current if current is not None and current.shop_id == ctx.shop_id else None

    async def save(self, ctx, message):
        current = await self.get(ctx, message.id)
        if current is None:
            return
        self._put(replace(
            current, status=message.status, attempts=message.attempts, next_attempt_at=message.next_attempt_at,
            scheduled_at=message.scheduled_at, channel_used=message.channel_used,
            provider_message_id=message.provider_message_id, error_code=message.error_code,
            error_kind=message.error_kind, sent_at=message.sent_at, canceled_reason=message.canceled_reason,
        ))
        self.journal.append(("save_message", message.id, message.status))

    # --- 전 매장(디스패처) ---------------------------------------------------------------------------------------

    async def claim_due(self, now, limit):
        due = sorted((m for m in self.rows.values() if m.status == SCHEDULED and m.scheduled_at <= now),
                     key=lambda m: (m.scheduled_at, m.id))[:limit]
        claimed = [replace(m, status=SENDING) for m in due]
        for m in claimed:
            self._put(m)
            self.claimed_at[m.id] = now
        self.journal.append(("claim_due", [m.id for m in claimed]))
        return claimed

    async def recover_stuck(self, before):
        stuck = [m for m in self.rows.values()
                 if m.status == SENDING and m.id in self.claimed_at and self.claimed_at[m.id] < before]
        for m in stuck:
            self._put(replace(m, status=SCHEDULED, attempts=m.attempts + 1))
            del self.claimed_at[m.id]
        self.journal.append(("recover_stuck", [m.id for m in stuck]))
        return len(stuck)

    async def list_accepted(self, now):
        return sorted((m for m in self.rows.values()
                       if m.status == ACCEPTED and m.next_attempt_at is not None and m.next_attempt_at <= now),
                      key=lambda m: (m.next_attempt_at, m.id))

    async def list_pending_templates(self):
        return sorted((t for t in self.templates.rows.values() if t.status == PENDING), key=lambda t: t.id)

    async def list_linked_channels(self):
        return sorted((c for c in self.channels.rows.values() if c.status == LINKED), key=lambda c: c.shop_id)

    async def list_templates_for_shops(self, shop_ids):
        return {
            shop_id: sorted((t for t in self.templates.rows.values() if t.shop_id == shop_id),
                            key=lambda t: KINDS.index(t.kind))
            for shop_id in shop_ids
        }
```

`backend/apps/notification/tests/test_fakes.py`:

```python
"""알림 저장소 스텁이 pg 구현과 같은 규칙을 지키는지 — 뒤 작업의 구독자·디스패처 테스트가 이 스텁에 기댄다."""
from dataclasses import replace
from datetime import timedelta

import pytest

from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED, UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED, SENDING, SENT
from notification.domain.value_objects.template_status import PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, new_message, settings
from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(10, 14, 11)


async def test_같은_방문_같은_종류의_대기_줄이_둘이면_예외다():
    messages = FakeMessages()
    first = await messages.create(A, new_message())
    with pytest.raises(MessageAlreadyPendingError):
        await messages.create(A, new_message())
    assert await messages.cancel_pending(A, "rescheduled", visit_id=1, kinds=[CONFIRM]) == 1
    assert (await messages.get(A, first.id)).canceled_reason == "rescheduled"
    second = await messages.create(A, new_message())
    await messages.save(A, replace(second, status=SENDING))
    with pytest.raises(MessageAlreadyPendingError):
        await messages.create(A, new_message())
    assert [m.id for m in await messages.list_for_visit(A, 1)] == [second.id, first.id]
    assert await messages.list_for_visit(B, 1) == []


async def test_큐는_시각이_된_줄만_순서대로_집어_sending_으로_바꾸고_멈춘_것은_되돌린다():
    messages = FakeMessages()
    late = await messages.create(A, new_message(visit_id=1, scheduled_at=NOW - timedelta(hours=1)))
    early = await messages.create(A, new_message(visit_id=2, scheduled_at=NOW - timedelta(hours=2)))
    await messages.create(A, new_message(visit_id=3, scheduled_at=NOW + timedelta(hours=1)))
    assert [m.id for m in await messages.claim_due(NOW, 1)] == [early.id]
    assert (await messages.get(A, early.id)).status == SENDING
    assert [m.id for m in await messages.claim_due(NOW, 5)] == [late.id]
    assert await messages.claim_due(NOW, 5) == []
    assert await messages.recover_stuck(NOW) == 0
    assert await messages.recover_stuck(NOW + timedelta(minutes=5)) == 2
    recovered = await messages.get(A, early.id)
    assert (recovered.status, recovered.attempts) == (SCHEDULED, 1)


async def test_보낸_줄_판정은_상태와_주소로_하고_매장을_거른다():
    messages = FakeMessages()
    report = await messages.create(A, new_message(kind=REPORT, variables={"url": "https://a/1"}))
    assert await messages.has_delivered(A, 1, REPORT) is False
    await messages.save(A, replace(report, status=SENT, sent_at=NOW))
    assert await messages.has_delivered(A, 1, REPORT) is True
    assert await messages.has_delivered(A, 1, REPORT, url="https://a/1") is True
    assert await messages.has_delivered(A, 1, REPORT, url="https://a/2") is False
    assert await messages.has_delivered(B, 1, REPORT) is False
    assert await messages.last_delivered_at(A, 1, REPORT) == NOW
    assert await messages.last_delivered_at(A, 1, NEXT_VISIT) is None


async def test_취소는_대기_줄만_범위대로_덮는다():
    messages = FakeMessages()
    await messages.create(A, new_message(visit_id=1, kind=CONFIRM))
    await messages.create(A, new_message(visit_id=1, kind=REMINDER))
    await messages.create(A, new_message(visit_id=2, kind=CONFIRM))
    await messages.create(B, new_message(shop_id=2, visit_id=9, kind=CONFIRM))
    assert await messages.cancel_pending(A, "rescheduled", visit_id=1, kinds=[REMINDER]) == 1
    assert await messages.cancel_pending(A, "channel_unlinked") == 2
    assert await messages.cancel_pending(A, "channel_unlinked") == 0
    assert [m.status for m in await messages.list_for_visit(B, 9)] == [SCHEDULED]
    assert {m.canceled_reason for m in await messages.list_for_visit(A, 1)} == {"rescheduled", "channel_unlinked"}
    assert all(m.status == CANCELED for m in await messages.list_for_visit(A, 1))


async def test_채널_설정_템플릿_스텁은_매장당_한_줄이고_컨텍스트의_매장만_본다():
    channels, store, templates = FakeChannels(), FakeSettings(), FakeTemplates()
    assert await channels.save(A, channel()) == channel()
    assert (await channels.save(A, channel(status=UNLINKED))).status == UNLINKED
    assert (await channels.get(A)).status == UNLINKED and await channels.get(B) is None
    with pytest.raises(ValueError):
        await channels.save(A, channel(shop_id=2))

    assert await store.get(A) is None
    assert await store.ensure(A) == DEFAULT_NOTIFICATION_SETTINGS
    changed = await store.update(A, settings(next_visit_enabled=True))
    assert await store.ensure(A) == changed and await store.get(B) is None

    first = await templates.upsert(A, NEXT_VISIT, 1, "KA01TP0002", NOW)
    await templates.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    await templates.set_status(A, NEXT_VISIT, REJECTED, "사유", NOW)
    again = await templates.upsert(A, NEXT_VISIT, 2, "KA01TP0003", NOW)
    assert (again.id, again.status, again.rejected_reason, again.text_version) == (first.id, PENDING, None, 2)
    assert [t.kind for t in await templates.list_for_shop(A)] == [CONFIRM, NEXT_VISIT]
    assert await templates.get(B, CONFIRM) is None and await templates.list_for_shop(B) == []
    assert await templates.delete_all(A) == 2 and await templates.list_for_shop(A) == []


async def test_큐의_전_매장_조회는_같이_넘긴_채널_템플릿_스텁을_본다():
    channels, templates = FakeChannels(), FakeTemplates()
    messages = FakeMessages(templates=templates, channels=channels)
    await channels.save(A, channel(shop_id=1, status=LINKED))
    await channels.save(B, channel(shop_id=2, status=UNLINKED))
    pending = await templates.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    await templates.upsert(B, CONFIRM, 1, "KA01TP0009", NOW)
    await templates.set_status(B, CONFIRM, "approved", None, NOW)
    assert [c.shop_id for c in await messages.list_linked_channels()] == [1]
    assert await messages.list_pending_templates() == [pending]
    assert {s: [t.kind for t in ts] for s, ts in (await messages.list_templates_for_shops([1, 2, 3])).items()} == {
        1: [CONFIRM], 2: [CONFIRM], 3: []}
```

`backend/apps/notification/tests/test_fakes_are_ports.py`:

```python
"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    assert isinstance(FakeChannels(), ChannelRepository)
    assert isinstance(FakeSettings(), SettingsRepository)
    assert isinstance(FakeTemplates(), TemplateRepository)
    messages = FakeMessages()
    assert isinstance(messages, MessageRepository) and isinstance(messages, NotificationQueueRepository)
```

`backend/tests/integration/test_notification_schema.py`:

```python
"""notification 네 표의 실제 CHECK·부분 색인이 도메인 튜플과 같은 값을 같은 순서로 말하는지 — 실제 DB 에서 읽는다.

마이그레이션 0011 은 상태 목록을 글자로 적는다. tests/test_schema_drift.py 는 CHECK 와 부분 색인의 WHERE 를 비교하지
않으므로, 도메인에 값을 더하고 마이그레이션을 잊으면 여기서 걸린다.
"""
import re

import pytest
from sqlalchemy import text

from notification.domain.value_objects.channel_status import CHANNEL_STATUSES
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.value_objects.message_status import (
    CANCEL_REASONS,
    CHANNELS_USED,
    ERROR_KINDS,
    PENDING_STATUSES,
    STATUSES,
)
from notification.domain.value_objects.template_status import TEMPLATE_STATUSES

pytestmark = pytest.mark.integration

_QUOTED = re.compile(r"'([a-z_]+)'")


async def _constraint_def(engine, name: str) -> str:
    async with engine.connect() as conn:
        return (await conn.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"), {"name": name}
        )).scalar_one()


async def _index_predicate(engine, name: str) -> str:
    async with engine.connect() as conn:
        return (await conn.execute(text(
            "SELECT pg_get_expr(i.indpred, i.indrelid) FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
            "WHERE c.relname = :name"), {"name": name}
        )).scalar_one()


@pytest.mark.parametrize(("name", "values"), [
    ("ck_notification_channels_status", CHANNEL_STATUSES),
    ("ck_notification_templates_kind", KINDS),
    ("ck_notification_templates_status", TEMPLATE_STATUSES),
    ("ck_notification_messages_kind", KINDS),
    ("ck_notification_messages_status", STATUSES),
    ("ck_notification_messages_canceled_reason", CANCEL_REASONS),
    ("ck_notification_messages_channel_used", CHANNELS_USED),
    ("ck_notification_messages_error_kind", ERROR_KINDS),
])
async def test_CHECK_는_도메인_튜플의_값을_같은_순서로_담는다(db_engine, name, values):
    assert _QUOTED.findall(await _constraint_def(db_engine, name)) == list(values)


async def test_대기_줄_부분_유일_색인은_대기_상태만_담는다(db_engine):
    predicate = await _index_predicate(db_engine, "uq_notification_messages_pending")
    assert _QUOTED.findall(predicate) == [s for s in STATUSES if s in PENDING_STATUSES]


async def test_취소_이유는_취소_상태에만_있다(db_engine):
    assert _QUOTED.findall(await _constraint_def(db_engine, "ck_notification_messages_canceled")) == ["canceled"]


async def test_문자_대체는_발신번호_인증이_있어야_켤_수_있다(db_engine):
    definition = await _constraint_def(db_engine, "ck_notification_channels_fallback")
    assert "sms_fallback_enabled" in definition and "sender_number_verified_at IS NOT NULL" in definition
```

`backend/tests/test_importlinter_lists_spokes.py`:

```python
"""구조 계약(.importlinter)이 apps/ 의 모든 스포크를 나열하는지 — 빠진 스포크는 계약이 보지 않은 채 통과한다."""
import configparser
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
_SPOKES = sorted(
    p.name for p in (_BACKEND / "apps").iterdir() if (p / "__init__.py").exists() and p.name != "hub"
)
_CONTRACT = "importlinter:contract:"


def _listed(section: str, key: str) -> set[str]:
    config = configparser.ConfigParser()
    config.read(_BACKEND / ".importlinter", encoding="utf-8")
    return set(config[section][key].split())


@pytest.mark.parametrize(("section", "key", "expected"), [
    ("importlinter", "root_packages", {"hub", "core", *_SPOKES}),
    (_CONTRACT + "clean-architecture", "containers", {"hub", *_SPOKES}),
    (_CONTRACT + "spoke-independence", "modules", set(_SPOKES)),
    (_CONTRACT + "framework-isolation", "source_modules",
     {"hub.app", *(f"{s}.app" for s in _SPOKES), *(f"{s}.domain" for s in _SPOKES)}),
    (_CONTRACT + "domain-purity", "source_modules", {f"{s}.domain" for s in _SPOKES}),
    (_CONTRACT + "hub-isolation", "forbidden_modules", set(_SPOKES)),
    (_CONTRACT + "core-isolation", "forbidden_modules", set(_SPOKES)),
])
def test_구조_계약은_모든_스포크를_나열한다(section, key, expected):
    assert _listed(section, key) == expected
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

- `docker compose run --rm --no-deps backend pytest apps/notification/tests/test_fakes_are_ports.py apps/notification/tests/test_fakes.py tests/test_importlinter_lists_spokes.py -q -p no:cacheprovider` → 수집 오류 2(`No module named 'notification.app'`, `'notification.tests.helpers.fakes'`); 따로 돌린 `tests/test_importlinter_lists_spokes.py` 는 7 failed(일곱 목록 모두 `notification` 없음).
- `docker compose run --rm backend pytest apps/notification/tests/adapter/test_notification_pg_repositories.py tests/integration/test_notification_schema.py -q -p no:cacheprovider` → 수집 오류 1(`No module named 'notification.adapter.outbound'`); 따로 돌린 스키마 대조는 11 failed(`NoResultFound` — 제약·색인 없음).

구현 뒤 첫 실행에서 테스트 쪽 실수 둘을 고쳤다(구현은 그대로): ① 세이브포인트 테스트가 `reminder.id - 1` 로 앞 줄 ID 를 셌는데 실패한 INSERT 도 시퀀스를 소비해 ID 가 건너뛴다 → 만든 줄의 `id` 를 들고 비교. ② 취소 범위 테스트가 B 매장에도 `visit_id=1` 을 썼는데 부분 유일 색인은 `(visit_id, kind)` 라 매장을 가리지 않는다(방문 ID 는 전 매장에서 유일하므로 현실에 없는 데이터) → B 는 `visit_id=9`. 스텁의 `create` 도 같은 규칙(매장 불문 `(visit_id, kind)`)으로 맞췄다.

- [ ] **Step 3: 구현한다**

`backend/alembic/versions/0011_notification.py`:

```python
"""알림톡 — 매장 채널(notification_channels), 설정, 템플릿 심사 상태, 메시지 큐이자 발송 기록

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

# 상태 목록은 글자로 적는다 — tests/integration/test_notification_schema.py 가 도메인 튜플과 같은 순서인지 실제 DB 로 본다.
_KINDS = "('confirm', 'reminder', 'report', 'change', 'cancel', 'next_visit')"
_STATUSES = "('scheduled', 'sending', 'accepted', 'sent', 'fallback_sent', 'failed', 'canceled')"
_CANCEL_REASONS = (
    "('rescheduled', 'visit_canceled', 'no_show', 'setting_off', 'channel_unlinked', 'shop_closed', "
    "'template_rejected', 'report_revoked', 'too_late', 'anonymized', 'has_upcoming', 'cooldown', "
    "'no_consent', 'bad_phone')"
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # 매장당 한 줄. shop_id 는 tenancy 의 ID — 스포크를 넘는 외래 키는 걸지 않는다.
    op.create_table(
        "notification_channels",
        sa.Column("shop_id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_channel_id", sa.String(100)),
        sa.Column("linked_at", sa.DateTime(timezone=True)),
        sa.Column("unlinked_at", sa.DateTime(timezone=True)),
        sa.Column("sender_number", sa.String(11)),
        sa.Column("sender_number_verified_at", sa.DateTime(timezone=True)),
        sa.Column("sms_fallback_enabled", sa.Boolean, server_default=sa.text("false"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('token_requested', 'linked', 'unlinked')", name="ck_notification_channels_status"
        ),
        # 문자 대체는 발신번호 인증을 마쳐야 켤 수 있다(N11).
        sa.CheckConstraint(
            "NOT sms_fallback_enabled OR sender_number_verified_at IS NOT NULL",
            name="ck_notification_channels_fallback",
        ),
    )
    op.create_table(
        "notification_settings",
        sa.Column("shop_id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("confirm_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("reminder_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("report_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("change_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("next_visit_enabled", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("reminder_time", sa.Time, server_default=sa.text("'18:00'"), nullable=False),
        sa.Column("next_visit_after_weeks", sa.SmallInteger),
        sa.Column("next_visit_cooldown_days", sa.SmallInteger, server_default=sa.text("30"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "reminder_time BETWEEN '08:00' AND '21:00'", name="ck_notification_settings_reminder_time"
        ),
        sa.CheckConstraint(
            "next_visit_after_weeks IS NULL OR next_visit_after_weeks BETWEEN 1 AND 52",
            name="ck_notification_settings_next_visit_after_weeks",
        ),
        sa.CheckConstraint(
            "next_visit_cooldown_days BETWEEN 1 AND 365", name="ck_notification_settings_next_visit_cooldown_days"
        ),
    )
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("text_version", sa.SmallInteger, nullable=False),
        sa.Column("provider_template_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rejected_reason", sa.String(500)),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN " + _KINDS, name="ck_notification_templates_kind"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_notification_templates_status"
        ),
        sa.UniqueConstraint("shop_id", "kind", name="uq_notification_templates_shop_kind"),
    )
    # 큐이자 발송 기록. 전화번호·이름은 저장하지 않는다(설계 4.5). variables 에는 알림장 주소가 든다 — 응답·로그에 싣지 않는다.
    op.create_table(
        "notification_messages",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("visit_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, nullable=False),
        sa.Column("pet_id", sa.BigInteger),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("attempts", sa.SmallInteger, server_default=sa.text("0"), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("channel_used", sa.String(10)),
        sa.Column("provider_message_id", sa.String(100)),
        sa.Column("error_code", sa.String(20)),
        sa.Column("error_kind", sa.String(10)),
        sa.Column("variables", postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("requested_by_member_id", sa.BigInteger),
        sa.Column("canceled_reason", sa.String(20)),
        *_timestamps(),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN " + _KINDS, name="ck_notification_messages_kind"),
        sa.CheckConstraint("status IN " + _STATUSES, name="ck_notification_messages_status"),
        sa.CheckConstraint(
            "channel_used IS NULL OR channel_used IN ('alimtalk', 'sms', 'lms')",
            name="ck_notification_messages_channel_used",
        ),
        sa.CheckConstraint(
            "error_kind IS NULL OR error_kind IN ('transient', 'permanent')",
            name="ck_notification_messages_error_kind",
        ),
        sa.CheckConstraint(
            "canceled_reason IS NULL OR canceled_reason IN " + _CANCEL_REASONS,
            name="ck_notification_messages_canceled_reason",
        ),
        sa.CheckConstraint(
            "canceled_reason IS NULL OR status = 'canceled'", name="ck_notification_messages_canceled"
        ),
    )
    # 같은 방문·같은 종류의 대기 줄은 하나(N5). 디스패처가 집는 질의, 쿨다운, 하루 상한, 방문별 내역의 색인.
    op.create_index(
        "uq_notification_messages_pending", "notification_messages", ["visit_id", "kind"], unique=True,
        postgresql_where=sa.text("status IN ('scheduled', 'sending')"),
    )
    op.create_index("ix_notification_messages_due", "notification_messages", ["status", "scheduled_at"])
    op.create_index("ix_notification_messages_cooldown", "notification_messages", ["customer_id", "kind", "sent_at"])
    op.create_index("ix_notification_messages_shop_day", "notification_messages", ["shop_id", "created_at"])
    op.create_index("ix_notification_messages_visit", "notification_messages", ["visit_id"])


def downgrade() -> None:
    op.drop_table("notification_messages")
    op.drop_table("notification_templates")
    op.drop_table("notification_settings")
    op.drop_table("notification_channels")
```

`backend/apps/notification/adapter/outbound/orm/notification_orm.py`:

```python
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from notification.domain.value_objects.channel_status import CHANNEL_STATUSES
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.value_objects.message_status import (
    CANCEL_REASONS,
    CHANNELS_USED,
    ERROR_KINDS,
    PENDING_STATUSES,
    STATUSES,
)
from notification.domain.value_objects.template_status import TEMPLATE_STATUSES


def _in(column: str, values: tuple[str, ...]) -> str:
    """CHECK 의 목록은 도메인 튜플에서 만든다. 마이그레이션 0011 은 글자로 적었으므로 값을 더하면 새 마이그레이션이다 —
    tests/integration/test_notification_schema.py 가 실제 DB 와 튜플을 대조한다."""
    return f"{column} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


_PENDING_IN = _in("status", tuple(s for s in STATUSES if s in PENDING_STATUSES))


class NotificationChannelOrm(Base):
    """매장의 카카오톡 채널 연동 한 줄(설계 4.1). shop_id 는 tenancy 의 ID — 외래 키 없음."""

    __tablename__ = "notification_channels"
    __table_args__ = (
        CheckConstraint(_in("status", CHANNEL_STATUSES), name="ck_notification_channels_status"),
        # 문자 대체는 발신번호 인증을 마쳐야 켤 수 있다(N11).
        CheckConstraint(
            "NOT sms_fallback_enabled OR sender_number_verified_at IS NOT NULL",
            name="ck_notification_channels_fallback",
        ),
    )

    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(20))
    provider_channel_id: Mapped[str | None] = mapped_column(String(100))
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sender_number: Mapped[str | None] = mapped_column(String(11))
    sender_number_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sms_fallback_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationSettingsOrm(Base):
    """매장의 알림톡 설정(설계 4.2). 연동할 때 기본값으로 생긴다."""

    __tablename__ = "notification_settings"
    __table_args__ = (
        CheckConstraint("reminder_time BETWEEN '08:00' AND '21:00'", name="ck_notification_settings_reminder_time"),
        CheckConstraint(
            "next_visit_after_weeks IS NULL OR next_visit_after_weeks BETWEEN 1 AND 52",
            name="ck_notification_settings_next_visit_after_weeks",
        ),
        CheckConstraint(
            "next_visit_cooldown_days BETWEEN 1 AND 365", name="ck_notification_settings_next_visit_cooldown_days"
        ),
    )

    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    confirm_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    report_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    change_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))   # change·cancel 둘
    next_visit_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reminder_time: Mapped[time] = mapped_column(Time, server_default=text("'18:00'"))   # 매장 시간대의 벽시계 시각
    next_visit_after_weeks: Mapped[int | None] = mapped_column(SmallInteger)   # NULL = 지난 방문 간격
    next_visit_cooldown_days: Mapped[int] = mapped_column(SmallInteger, server_default=text("30"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationTemplateOrm(Base):
    """매장 채널에 등록한 종류별 템플릿의 심사 상태(설계 4.3). 문안은 코드에 있다(text_version)."""

    __tablename__ = "notification_templates"
    __table_args__ = (
        CheckConstraint(_in("kind", KINDS), name="ck_notification_templates_kind"),
        CheckConstraint(_in("status", TEMPLATE_STATUSES), name="ck_notification_templates_status"),
        UniqueConstraint("shop_id", "kind", name="uq_notification_templates_shop_kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(20))
    text_version: Mapped[int] = mapped_column(SmallInteger)
    provider_template_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    rejected_reason: Mapped[str | None] = mapped_column(String(500))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationMessageOrm(Base):
    """알림 줄 하나 — 큐이자 발송 기록(설계 4.4). 전화번호·이름은 저장하지 않는다. variables 에는 알림장 주소가 든다."""

    __tablename__ = "notification_messages"
    __table_args__ = (
        CheckConstraint(_in("kind", KINDS), name="ck_notification_messages_kind"),
        CheckConstraint(_in("status", STATUSES), name="ck_notification_messages_status"),
        CheckConstraint(
            "channel_used IS NULL OR " + _in("channel_used", CHANNELS_USED), name="ck_notification_messages_channel_used"
        ),
        CheckConstraint(
            "error_kind IS NULL OR " + _in("error_kind", ERROR_KINDS), name="ck_notification_messages_error_kind"
        ),
        CheckConstraint(
            "canceled_reason IS NULL OR " + _in("canceled_reason", CANCEL_REASONS),
            name="ck_notification_messages_canceled_reason",
        ),
        CheckConstraint("canceled_reason IS NULL OR status = 'canceled'", name="ck_notification_messages_canceled"),
        # 같은 방문·같은 종류의 대기 줄은 하나(N5).
        Index(
            "uq_notification_messages_pending", "visit_id", "kind", unique=True,
            postgresql_where=text(_PENDING_IN),
        ),
        Index("ix_notification_messages_due", "status", "scheduled_at"),          # 디스패처가 집는 질의
        Index("ix_notification_messages_cooldown", "customer_id", "kind", "sent_at"),
        Index("ix_notification_messages_shop_day", "shop_id", "created_at"),       # 하루 상한
        Index("ix_notification_messages_visit", "visit_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 다른 스포크(tenancy·visit·customer)의 ID — 외래 키 없이 색인만.
    shop_id: Mapped[int] = mapped_column(BigInteger)
    visit_id: Mapped[int] = mapped_column(BigInteger)
    customer_id: Mapped[int] = mapped_column(BigInteger)
    pet_id: Mapped[int | None] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(20))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'scheduled'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    channel_used: Mapped[str | None] = mapped_column(String(10))
    provider_message_id: Mapped[str | None] = mapped_column(String(100))
    error_code: Mapped[str | None] = mapped_column(String(20))
    error_kind: Mapped[str | None] = mapped_column(String(10))
    variables: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    requested_by_member_id: Mapped[int | None] = mapped_column(BigInteger)   # tenancy 의 멤버 ID
    canceled_reason: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

`backend/apps/notification/app/ports/output/notification_queue_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_template import NotificationTemplate


class NotificationQueueRepository(ABC):
    """요청 밖에서 도는 디스패처가 쓰는 전 매장 질의.

    `ShopContext` 를 받지 않는 저장소다 — 공개 알림장의 `PublicReportRepository` 와 같은 예외. 디스패처는 매장이 아니라
    "시각이 된 줄 전부"를 집고, 매장별 읽기는 집은 줄의 shop_id 로 `system_context` 를 만들어 매장 범위 포트로 한다.
    """

    @abstractmethod
    async def claim_due(self, now: datetime, limit: int) -> list[NotificationMessage]:
        """status='scheduled' AND scheduled_at <= now 인 줄을 scheduled_at·id 순으로 limit 만큼 FOR UPDATE SKIP LOCKED 로
        집어 sending 으로 바꾸고(updated_at = now) 바뀐 줄을 돌려준다. 커밋은 부르는 쪽 — 커밋한 뒤 업체를 부른다(N6·N14)."""

    @abstractmethod
    async def recover_stuck(self, before: datetime) -> int:
        """집은 뒤 죽어 남은 sending(updated_at < before)을 scheduled 로 되돌리고 attempts 를 하나 올린다(N7). 바꾼 수."""

    @abstractmethod
    async def list_accepted(self, now: datetime) -> list[NotificationMessage]:
        """status='accepted' AND next_attempt_at <= now — next_attempt_at 을 '다음에 상태를 물을 시각'으로 쓴다."""

    @abstractmethod
    async def list_pending_templates(self) -> list[NotificationTemplate]:
        """심사 중인 템플릿 전부(매장 불문), id 순."""

    @abstractmethod
    async def list_linked_channels(self) -> list[NotificationChannel]:
        """연동된 채널 전부, shop_id 순."""

    @abstractmethod
    async def list_templates_for_shops(self, shop_ids: list[int]) -> dict[int, list[NotificationTemplate]]:
        """넘긴 매장마다 템플릿 목록(KINDS 순). 템플릿이 없는 매장은 빈 목록."""
```

`backend/apps/notification/app/ports/output/message_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.value_objects.new_message import NewMessage


class MessageRepository(ABC):
    """알림 줄(notification_messages)의 매장 범위 포트 — 구독자·설정·방문별 내역·재발송이 쓴다.

    쓰기는 고객 행 → 방문 행을 잠근 트랜잭션 안에서 부른다(잠금 순서의 끝 "→ 알림 행").
    """

    @abstractmethod
    async def create(self, ctx: ShopContext, new: NewMessage) -> NotificationMessage:
        """새 줄을 넣는다. 같은 방문·같은 종류의 대기 줄(scheduled·sending)이 있으면 MessageAlreadyPendingError —
        세이브포인트 안에서 넣으므로 트랜잭션은 계속 쓸 수 있다. new.shop_id 가 ctx 의 매장과 다르면 ValueError."""

    @abstractmethod
    async def cancel_pending(
        self, ctx: ShopContext, reason: str, visit_id: int | None = None, kinds: Iterable[str] | None = None
    ) -> int:
        """대기 줄(scheduled·sending)을 canceled 로. visit_id 가 없으면 매장 전체, kinds 가 없으면 전 종류. 바꾼 수."""

    @abstractmethod
    async def list_pending(self, ctx: ShopContext, kind: str) -> list[NotificationMessage]:
        """scheduled 인 줄만, scheduled_at 순 — 설정을 바꿀 때 다시 계산할 것."""

    @abstractmethod
    async def has_delivered(self, ctx: ShopContext, visit_id: int, kind: str, url: str | None = None) -> bool:
        """보낸 줄(sent·fallback_sent)이 있는가. url 을 주면 variables 의 url 이 같은 줄만(알림장)."""

    @abstractmethod
    async def last_delivered_at(self, ctx: ShopContext, customer_id: int, kind: str) -> datetime | None:
        """그 고객에게 그 종류를 마지막으로 보낸 시각(쿨다운)."""

    @abstractmethod
    async def count_sent_since(self, ctx: ShopContext, since: datetime) -> int:
        """업체에 넘긴 줄(provider_message_id 가 있는)의 수, created_at >= since — 하루 상한."""

    @abstractmethod
    async def list_for_visit(self, ctx: ShopContext, visit_id: int) -> list[NotificationMessage]:
        """created_at 역순, id 역순."""

    @abstractmethod
    async def get(self, ctx: ShopContext, message_id: int) -> NotificationMessage | None:
        """없거나 다른 매장의 것이면 None."""

    @abstractmethod
    async def save(self, ctx: ShopContext, message: NotificationMessage) -> None:
        """id 로 찾아 바뀔 수 있는 칸만 UPDATE — status, attempts, next_attempt_at, scheduled_at, channel_used,
        provider_message_id, error_code, error_kind, sent_at, canceled_reason. 다른 매장의 줄은 건드리지 않는다."""
```

`backend/.importlinter`:

```diff
@@ -20,6 +20,7 @@ root_packages =
     customer
     visit
     media
+    notification
 include_external_packages = True
 
 [importlinter:contract:clean-architecture]
@@ -37,6 +38,7 @@ containers =
     customer
     visit
     media
+    notification
 
 [importlinter:contract:spoke-independence]
 name = 스포크 상호 독립 (스포크끼리 import 하지 않는다)
@@ -48,6 +50,7 @@ modules =
     customer
     visit
     media
+    notification
 
 [importlinter:contract:framework-isolation]
 name = 프레임워크 격리 (app·domain 은 웹·DB·외부 통신 라이브러리를 모른다)
@@ -66,6 +69,8 @@ source_modules =
     visit.domain
     media.app
     media.domain
+    notification.app
+    notification.domain
 forbidden_modules =
     fastapi
     sqlalchemy
@@ -84,6 +89,7 @@ source_modules =
     customer.domain
     visit.domain
     media.domain
+    notification.domain
 forbidden_modules =
     pydantic
     core
@@ -100,6 +106,7 @@ forbidden_modules =
     customer
     visit
     media
+    notification
 
 [importlinter:contract:core-isolation]
 name = core 격리 (core 는 스포크를 import 하지 않는다)
@@ -113,3 +120,4 @@ forbidden_modules =
     customer
     visit
     media
+    notification
```

`backend/apps/notification/adapter/outbound/__init__.py`:

```python

```

`backend/apps/notification/adapter/outbound/mappers/__init__.py`:

```python

```

`backend/apps/notification/adapter/outbound/mappers/notification_mapper.py`:

```python
"""네 엔티티 ↔ ORM. 채널은 upsert 의 값 사전도 여기서 만든다."""
from __future__ import annotations

from notification.adapter.outbound.orm.notification_orm import (
    NotificationChannelOrm,
    NotificationMessageOrm,
    NotificationSettingsOrm,
    NotificationTemplateOrm,
)
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate


def to_channel(orm: NotificationChannelOrm) -> NotificationChannel:
    return NotificationChannel(
        shop_id=orm.shop_id, status=orm.status, provider=orm.provider, provider_channel_id=orm.provider_channel_id,
        linked_at=orm.linked_at, unlinked_at=orm.unlinked_at, sender_number=orm.sender_number,
        sender_number_verified_at=orm.sender_number_verified_at, sms_fallback_enabled=orm.sms_fallback_enabled,
    )


def channel_values(channel: NotificationChannel) -> dict:
    """INSERT 와 ON CONFLICT UPDATE 가 함께 쓰는, 키(shop_id)를 뺀 칸."""
    return dict(
        status=channel.status, provider=channel.provider, provider_channel_id=channel.provider_channel_id,
        linked_at=channel.linked_at, unlinked_at=channel.unlinked_at, sender_number=channel.sender_number,
        sender_number_verified_at=channel.sender_number_verified_at, sms_fallback_enabled=channel.sms_fallback_enabled,
    )


def to_settings(orm: NotificationSettingsOrm) -> NotificationSettings:
    return NotificationSettings(
        confirm_enabled=orm.confirm_enabled, reminder_enabled=orm.reminder_enabled, report_enabled=orm.report_enabled,
        change_enabled=orm.change_enabled, next_visit_enabled=orm.next_visit_enabled, reminder_time=orm.reminder_time,
        next_visit_after_weeks=orm.next_visit_after_weeks, next_visit_cooldown_days=orm.next_visit_cooldown_days,
    )


def settings_values(settings: NotificationSettings) -> dict:
    return dict(
        confirm_enabled=settings.confirm_enabled, reminder_enabled=settings.reminder_enabled,
        report_enabled=settings.report_enabled, change_enabled=settings.change_enabled,
        next_visit_enabled=settings.next_visit_enabled, reminder_time=settings.reminder_time,
        next_visit_after_weeks=settings.next_visit_after_weeks,
        next_visit_cooldown_days=settings.next_visit_cooldown_days,
    )


def to_template(orm: NotificationTemplateOrm) -> NotificationTemplate:
    return NotificationTemplate(
        id=orm.id, shop_id=orm.shop_id, kind=orm.kind, text_version=orm.text_version,
        provider_template_id=orm.provider_template_id, status=orm.status, rejected_reason=orm.rejected_reason,
        requested_at=orm.requested_at, decided_at=orm.decided_at,
    )


def to_message(orm: NotificationMessageOrm) -> NotificationMessage:
    return NotificationMessage(
        id=orm.id, shop_id=orm.shop_id, visit_id=orm.visit_id, customer_id=orm.customer_id, pet_id=orm.pet_id,
        kind=orm.kind, scheduled_at=orm.scheduled_at, status=orm.status, attempts=orm.attempts,
        next_attempt_at=orm.next_attempt_at, channel_used=orm.channel_used,
        provider_message_id=orm.provider_message_id, error_code=orm.error_code, error_kind=orm.error_kind,
        variables=dict(orm.variables), requested_by_member_id=orm.requested_by_member_id,
        created_at=orm.created_at, sent_at=orm.sent_at, canceled_reason=orm.canceled_reason,
    )
```

`backend/apps/notification/adapter/outbound/orm/__init__.py`:

```python

```

`backend/apps/notification/adapter/outbound/pg/__init__.py`:

```python

```

`backend/apps/notification/adapter/outbound/pg/channel_pg_repository.py`:

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import channel_values, to_channel
from notification.adapter.outbound.orm.notification_orm import NotificationChannelOrm
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.domain.entities.notification_channel import NotificationChannel


class ChannelPgRepository(ChannelRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> NotificationChannel | None:
        row = (
            await self._session.execute(
                select(NotificationChannelOrm)
                .where(NotificationChannelOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_channel(row) if row is not None else None

    async def save(self, ctx: ShopContext, channel: NotificationChannel) -> NotificationChannel:
        if channel.shop_id != ctx.shop_id:
            raise ValueError("채널의 매장이 컨텍스트의 매장과 다릅니다.")
        values = channel_values(channel)
        row = (
            await self._session.execute(
                pg_insert(NotificationChannelOrm)
                .values(shop_id=ctx.shop_id, **values)
                .on_conflict_do_update(index_elements=[NotificationChannelOrm.shop_id], set_=values)
                .returning(NotificationChannelOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_channel(row)
```

`backend/apps/notification/adapter/outbound/pg/message_pg_repository.py`:

```python
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import to_channel, to_message, to_template
from notification.adapter.outbound.orm.notification_orm import (
    NotificationChannelOrm,
    NotificationMessageOrm,
    NotificationTemplateOrm,
)
from notification.adapter.outbound.pg.template_pg_repository import by_kind
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    DELIVERED_STATUSES,
    PENDING_STATUSES,
    SCHEDULED,
    SENDING,
)
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import PENDING

_PENDING_INDEX = "uq_notification_messages_pending"
_M = NotificationMessageOrm


class MessagePgRepository(MessageRepository, NotificationQueueRepository):
    """notification_messages 표 하나를 두 포트로 내놓는다 — 매장 범위(구독자·API)와 전 매장(디스패처)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _rows(self, statement) -> list[NotificationMessage]:
        rows = await self._session.execute(statement.execution_options(populate_existing=True))
        return [to_message(row) for row in rows.scalars()]

    # --- 매장 범위 ----------------------------------------------------------------------------------------------

    async def create(self, ctx: ShopContext, new: NewMessage) -> NotificationMessage:
        if new.shop_id != ctx.shop_id:
            raise ValueError("메시지의 매장이 컨텍스트의 매장과 다릅니다.")
        statement = (
            insert(_M)
            .values(
                shop_id=ctx.shop_id, visit_id=new.visit_id, customer_id=new.customer_id, pet_id=new.pet_id,
                kind=new.kind, scheduled_at=new.scheduled_at, variables=dict(new.variables),
                requested_by_member_id=new.requested_by_member_id,
            )
            .returning(_M)
            .execution_options(populate_existing=True)
        )
        # 세이브포인트 — 유일 위반이 트랜잭션 전체를 버리지 않게. 늦은 쪽은 앞선 쪽의 커밋까지 색인에서 기다렸다가 여기서 걸린다.
        try:
            async with self._session.begin_nested():
                row = (await self._session.execute(statement)).scalar_one()
        except IntegrityError as exc:
            if getattr(exc.orig.__cause__, "constraint_name", None) == _PENDING_INDEX:
                raise MessageAlreadyPendingError("같은 방문·종류의 알림이 이미 대기 중입니다.") from exc
            raise
        return to_message(row)

    async def cancel_pending(
        self, ctx: ShopContext, reason: str, visit_id: int | None = None, kinds: Iterable[str] | None = None
    ) -> int:
        conditions = [_M.shop_id == ctx.shop_id, _M.status.in_(PENDING_STATUSES)]
        if visit_id is not None:
            conditions.append(_M.visit_id == visit_id)
        if kinds is not None:
            conditions.append(_M.kind.in_(list(kinds)))
        canceled = await self._session.execute(
            update(_M).where(*conditions).values(status=CANCELED, canceled_reason=reason)
        )
        return canceled.rowcount

    async def list_pending(self, ctx: ShopContext, kind: str) -> list[NotificationMessage]:
        return await self._rows(
            select(_M)
            .where(_M.shop_id == ctx.shop_id, _M.kind == kind, _M.status == SCHEDULED)
            .order_by(_M.scheduled_at, _M.id)
        )

    async def has_delivered(self, ctx: ShopContext, visit_id: int, kind: str, url: str | None = None) -> bool:
        conditions = [_M.shop_id == ctx.shop_id, _M.visit_id == visit_id, _M.kind == kind,
                      _M.status.in_(DELIVERED_STATUSES)]
        if url is not None:
            conditions.append(_M.variables["url"].astext == url)
        found = await self._session.execute(select(_M.id).where(*conditions).limit(1))
        return found.first() is not None

    async def last_delivered_at(self, ctx: ShopContext, customer_id: int, kind: str) -> datetime | None:
        return (
            await self._session.execute(
                select(func.max(_M.sent_at)).where(
                    _M.shop_id == ctx.shop_id, _M.customer_id == customer_id, _M.kind == kind,
                    _M.status.in_(DELIVERED_STATUSES),
                )
            )
        ).scalar_one()

    async def count_sent_since(self, ctx: ShopContext, since: datetime) -> int:
        return (
            await self._session.execute(
                select(func.count()).select_from(_M).where(
                    _M.shop_id == ctx.shop_id, _M.provider_message_id.is_not(None), _M.created_at >= since
                )
            )
        ).scalar_one()

    async def list_for_visit(self, ctx: ShopContext, visit_id: int) -> list[NotificationMessage]:
        return await self._rows(
            select(_M)
            .where(_M.shop_id == ctx.shop_id, _M.visit_id == visit_id)
            .order_by(_M.created_at.desc(), _M.id.desc())
        )

    async def get(self, ctx: ShopContext, message_id: int) -> NotificationMessage | None:
        found = await self._rows(select(_M).where(_M.shop_id == ctx.shop_id, _M.id == message_id))
        return found[0] if found else None

    async def save(self, ctx: ShopContext, message: NotificationMessage) -> None:
        await self._session.execute(
            update(_M)
            .where(_M.shop_id == ctx.shop_id, _M.id == message.id)
            .values(
                status=message.status, attempts=message.attempts, next_attempt_at=message.next_attempt_at,
                scheduled_at=message.scheduled_at, channel_used=message.channel_used,
                provider_message_id=message.provider_message_id, error_code=message.error_code,
                error_kind=message.error_kind, sent_at=message.sent_at, canceled_reason=message.canceled_reason,
            )
        )

    # --- 전 매장(디스패처) ---------------------------------------------------------------------------------------

    async def claim_due(self, now: datetime, limit: int) -> list[NotificationMessage]:
        due = (
            select(_M.id)
            .where(_M.status == SCHEDULED, _M.scheduled_at <= now)
            .order_by(_M.scheduled_at, _M.id)
            .limit(limit)
            .with_for_update(skip_locked=True)   # 다른 디스패처가 쥔 줄은 건너뛴다(N6)
        )
        claimed = await self._rows(
            update(_M).where(_M.id.in_(due)).values(status=SENDING, updated_at=now).returning(_M)
        )
        return sorted(claimed, key=lambda m: (m.scheduled_at, m.id))

    async def recover_stuck(self, before: datetime) -> int:
        recovered = await self._session.execute(
            update(_M)
            .where(_M.status == SENDING, _M.updated_at < before)
            .values(status=SCHEDULED, attempts=_M.attempts + 1)
        )
        return recovered.rowcount

    async def list_accepted(self, now: datetime) -> list[NotificationMessage]:
        return await self._rows(
            select(_M).where(_M.status == ACCEPTED, _M.next_attempt_at <= now).order_by(_M.next_attempt_at, _M.id)
        )

    async def list_pending_templates(self) -> list[NotificationTemplate]:
        rows = await self._session.execute(
            select(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.status == PENDING)
            .order_by(NotificationTemplateOrm.id)
            .execution_options(populate_existing=True)
        )
        return [to_template(row) for row in rows.scalars()]

    async def list_linked_channels(self) -> list[NotificationChannel]:
        rows = await self._session.execute(
            select(NotificationChannelOrm)
            .where(NotificationChannelOrm.status == LINKED)
            .order_by(NotificationChannelOrm.shop_id)
            .execution_options(populate_existing=True)
        )
        return [to_channel(row) for row in rows.scalars()]

    async def list_templates_for_shops(self, shop_ids: list[int]) -> dict[int, list[NotificationTemplate]]:
        grouped: dict[int, list[NotificationTemplate]] = {shop_id: [] for shop_id in shop_ids}
        if not shop_ids:
            return grouped
        rows = await self._session.execute(
            select(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.shop_id.in_(shop_ids))
            .execution_options(populate_existing=True)
        )
        for row in rows.scalars():
            grouped[row.shop_id].append(to_template(row))
        return {shop_id: by_kind(templates) for shop_id, templates in grouped.items()}
```

`backend/apps/notification/adapter/outbound/pg/settings_pg_repository.py`:

```python
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import settings_values, to_settings
from notification.adapter.outbound.orm.notification_orm import NotificationSettingsOrm
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS, NotificationSettings


class SettingsPgRepository(SettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> NotificationSettings | None:
        row = (
            await self._session.execute(
                select(NotificationSettingsOrm)
                .where(NotificationSettingsOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_settings(row) if row is not None else None

    async def ensure(self, ctx: ShopContext) -> NotificationSettings:
        # 동시에 처음 쓰는 두 요청 중 늦은 쪽은 앞선 쪽의 커밋까지 기다렸다가 DO NOTHING 이 된다.
        await self._session.execute(
            pg_insert(NotificationSettingsOrm)
            .values(shop_id=ctx.shop_id, **settings_values(DEFAULT_NOTIFICATION_SETTINGS))
            .on_conflict_do_nothing(index_elements=[NotificationSettingsOrm.shop_id])
        )
        return await self.get(ctx)

    async def update(self, ctx: ShopContext, settings: NotificationSettings) -> NotificationSettings:
        row = (
            await self._session.execute(
                update(NotificationSettingsOrm)
                .where(NotificationSettingsOrm.shop_id == ctx.shop_id)
                .values(**settings_values(settings))
                .returning(NotificationSettingsOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_settings(row)
```

`backend/apps/notification/adapter/outbound/pg/template_pg_repository.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import to_template
from notification.adapter.outbound.orm.notification_orm import NotificationTemplateOrm
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.value_objects.template_status import PENDING


def by_kind(templates: list[NotificationTemplate]) -> list[NotificationTemplate]:
    """KINDS 의 순서로."""
    return sorted(templates, key=lambda t: KINDS.index(t.kind))


class TemplatePgRepository(TemplateRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_shop(self, ctx: ShopContext) -> list[NotificationTemplate]:
        rows = await self._session.execute(
            select(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.shop_id == ctx.shop_id)
            .execution_options(populate_existing=True)
        )
        return by_kind([to_template(row) for row in rows.scalars()])

    async def get(self, ctx: ShopContext, kind: str) -> NotificationTemplate | None:
        row = (
            await self._session.execute(
                select(NotificationTemplateOrm)
                .where(NotificationTemplateOrm.shop_id == ctx.shop_id, NotificationTemplateOrm.kind == kind)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_template(row) if row is not None else None

    async def upsert(
        self, ctx: ShopContext, kind: str, text_version: int, provider_template_id: str, requested_at: datetime
    ) -> NotificationTemplate:
        fresh = dict(
            text_version=text_version, provider_template_id=provider_template_id, status=PENDING,
            rejected_reason=None, requested_at=requested_at, decided_at=None,
        )
        row = (
            await self._session.execute(
                pg_insert(NotificationTemplateOrm)
                .values(shop_id=ctx.shop_id, kind=kind, **fresh)
                .on_conflict_do_update(constraint="uq_notification_templates_shop_kind", set_=fresh)
                .returning(NotificationTemplateOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_template(row)

    async def set_status(
        self, ctx: ShopContext, kind: str, status: str, rejected_reason: str | None, decided_at: datetime
    ) -> None:
        await self._session.execute(
            update(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.shop_id == ctx.shop_id, NotificationTemplateOrm.kind == kind)
            .values(status=status, rejected_reason=rejected_reason, decided_at=decided_at)
        )

    async def delete_all(self, ctx: ShopContext) -> int:
        deleted = await self._session.execute(
            delete(NotificationTemplateOrm).where(NotificationTemplateOrm.shop_id == ctx.shop_id)
        )
        return deleted.rowcount
```

`backend/apps/notification/app/__init__.py`:

```python

```

`backend/apps/notification/app/ports/__init__.py`:

```python

```

`backend/apps/notification/app/ports/output/__init__.py`:

```python

```

`backend/apps/notification/app/ports/output/channel_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_channel import NotificationChannel


class ChannelRepository(ABC):
    """매장의 채널 연동 한 줄(notification_channels). 매장 범위 — ShopContext 의 매장만 본다."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> NotificationChannel | None:
        """이 매장의 채널. 연동을 시작한 적이 없으면 None."""

    @abstractmethod
    async def save(self, ctx: ShopContext, channel: NotificationChannel) -> NotificationChannel:
        """shop_id 로 upsert 한다. channel.shop_id 가 ctx 의 매장과 다르면 ValueError."""
```

`backend/apps/notification/app/ports/output/settings_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_settings import NotificationSettings


class SettingsRepository(ABC):
    """매장의 알림톡 설정 한 줄(notification_settings). 매장 범위."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> NotificationSettings | None:
        """연동 전(행이 없으면) None."""

    @abstractmethod
    async def ensure(self, ctx: ShopContext) -> NotificationSettings:
        """없으면 DEFAULT_NOTIFICATION_SETTINGS 로 만든다. 있으면 그대로 돌려준다."""

    @abstractmethod
    async def update(self, ctx: ShopContext, settings: NotificationSettings) -> NotificationSettings:
        """행이 있어야 한다(ensure 뒤). 범위 검사는 도메인(check_settings)과 DB CHECK 가 한다."""
```

`backend/apps/notification/app/ports/output/template_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_template import NotificationTemplate


class TemplateRepository(ABC):
    """매장 채널에 등록한 종류별 템플릿의 심사 상태(notification_templates). 매장 범위, (shop, kind) 유일."""

    @abstractmethod
    async def list_for_shop(self, ctx: ShopContext) -> list[NotificationTemplate]:
        """종류 순(KINDS 의 순서)."""

    @abstractmethod
    async def get(self, ctx: ShopContext, kind: str) -> NotificationTemplate | None: ...

    @abstractmethod
    async def upsert(
        self, ctx: ShopContext, kind: str, text_version: int, provider_template_id: str, requested_at: datetime
    ) -> NotificationTemplate:
        """(shop, kind) 가 있으면 그 줄을 pending·새 판·새 업체 ID 로 덮고 rejected_reason·decided_at 을 비운다."""

    @abstractmethod
    async def set_status(
        self, ctx: ShopContext, kind: str, status: str, rejected_reason: str | None, decided_at: datetime
    ) -> None:
        """심사 결과를 적는다. 그 종류의 줄이 없으면 아무것도 하지 않는다."""

    @abstractmethod
    async def delete_all(self, ctx: ShopContext) -> int:
        """연동 해제 — 이 매장의 줄을 모두 지우고 지운 수를 돌려준다."""
```

`backend/apps/notification/dependencies/__init__.py`:

```python

```

`backend/apps/notification/dependencies/notification_wiring.py`:

```python
"""notification 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository


def build_channel_repository(db: AsyncSession) -> ChannelRepository:
    return ChannelPgRepository(db)


def build_settings_repository(db: AsyncSession) -> SettingsRepository:
    return SettingsPgRepository(db)


def build_template_repository(db: AsyncSession) -> TemplateRepository:
    return TemplatePgRepository(db)


def build_message_repository(db: AsyncSession) -> MessagePgRepository:
    """notification_messages 표의 리포지토리 하나. 매장 범위 포트와 디스패처의 전 매장 포트를 다 구현한다."""
    return MessagePgRepository(db)
```

`backend/apps/notification/domain/entities/notification_message.py`:

```diff
@@ -13,6 +13,7 @@ class NotificationMessage:
     shop_id: int
     visit_id: int
     customer_id: int
+    pet_id: int | None              # 보내는 순간 반려동물 이름(#{대상})을 읽는 데 쓴다. 보호자만의 방문이면 None
     kind: str
     scheduled_at: datetime            # UTC. 즉시면 만든 시각
     status: str
```

`backend/apps/notification/domain/value_objects/new_message.py`:

```diff
@@ -12,6 +12,7 @@ class NewMessage:
     shop_id: int
     visit_id: int
     customer_id: int
+    pet_id: int | None
     kind: str
     scheduled_at: datetime            # UTC
     variables: Mapping[str, str]      # 이벤트에서만 알 수 있는 값(알림장 주소·기간, 바뀌기 전 시각 …)
```

`backend/orm_registry.py`:

```diff
@@ -9,3 +9,4 @@ import tenancy.adapter.outbound.orm.tenancy_orm  # noqa: F401
 import customer.adapter.outbound.orm.customer_orm  # noqa: F401
 import visit.adapter.outbound.orm.visit_orm  # noqa: F401
 import media.adapter.outbound.orm.media_orm  # noqa: F401
+import notification.adapter.outbound.orm.notification_orm  # noqa: F401
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 테스트(저장소 22 + 스키마 대조 11 + 드리프트 1 + 스텁 6 + 스텁 포트 1 + 계약 목록 7) | 48 passed |
| 단위 전체 (`-m "not integration and not network"`) | 1433 passed (시작 1419 + 14) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken (1171 파일 — `notification` 포함) |

`tests/test_schema_drift.py` 통과(ORM 네 클래스 ↔ 0011). 통합 세션은 테스트 DB(`chagocnote_test`)에만 올렸다 — 개발 DB 에 `alembic upgrade` 를 하지 않았다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `claim_due` 의 `with_for_update(skip_locked=True)` → `with_for_update()` → `test_notification_pg_repositories.py::test_두_세션이_동시에_집어도_같은_줄을_둘이_집지_않는다`
- `claim_due` 가 `scheduled_at <= now` 를 안 봄 → `::test_큐는_시각이_된_scheduled_줄만_시각_순으로_limit_만큼_집어_sending_으로_바꾼다`, `::test_두_세션이_…`, `::test_멈춘_sending_줄은_시간이_지난_것만_되돌리고_시도를_센다`
- `create` 의 `begin_nested()` 제거 → `::test_같은_방문_같은_종류의_대기_줄은_하나이고_트랜잭션은_계속_쓸_수_있다`, `::test_취소되거나_보낸_줄이_있으면_새_대기_줄을_만들_수_있다`
- 마이그레이션의 부분 유일 색인에서 `postgresql_where` 제거(통합 세션이 테스트 DB 를 다시 만듦) → `::test_취소되거나_보낸_줄이_있으면_새_대기_줄을_만들_수_있다`, `test_notification_schema.py::test_대기_줄_부분_유일_색인은_대기_상태만_담는다`
- `cancel_pending` 의 `status IN PENDING` 조건 제거 → `::test_대기_줄_취소의_세_범위_방문_종류_전체`
- `.importlinter` `root_packages` 에서 `notification` 제거 (구조 계약은 6 kept 로 통과해 버린다) → `test_importlinter_lists_spokes.py::test_구조_계약은_모든_스포크를_나열한다[importlinter-root_packages-expected0]`
- `MessagePgRepository.get` 에서 `shop_id` 조건 제거 → `::test_다른_매장_컨텍스트로는_메시지가_없는_것이다`
- `recover_stuck` 이 `updated_at < before` 를 안 봄 → `::test_멈춘_sending_줄은_시간이_지난_것만_되돌리고_시도를_센다`
- `has_delivered` 가 `url` 을 무시 → `::test_보낸_줄_판정은_보낸_상태만_세고_주소를_주면_같은_주소만_본다`
- `list_accepted` 가 `next_attempt_at <= now` 를 안 봄 → `::test_accepted_줄은_다음_확인_시각이_지난_것만_모은다`
- `ChannelPgRepository.save` 의 `shop_id` 불일치 `ValueError` 제거 → `::test_채널의_매장이_컨텍스트와_다르면_ValueError_다`
- `FakeMessages.create` 의 대기 줄 검사 제거 → `test_fakes.py::test_같은_방문_같은_종류의_대기_줄이_둘이면_예외다`
- `save` 가 `kind` 도 덮어씀 → `::test_save_는_바뀔_수_있는_칸만_바꾼다`
- 템플릿 `upsert` 가 `status`·`rejected_reason`·`decided_at` 을 되돌리지 않음 → `::test_템플릿_upsert_는_같은_종류를_한_줄로_두고_pending_으로_되돌린다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 표 넷(0011)·ORM·저장소 — 큐는 SKIP LOCKED 로 집고, 같은 방문·종류의 대기 줄은 하나

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 구독자 — 예약·변경·취소·완료·알림장 이벤트를 같은 트랜잭션에서 메시지 줄로(`HandleVisitEventInteractor`)

**Files:**
- Create: `backend/apps/notification/app/use_cases/handle_visit_event_interactor.py`
- Create: `backend/apps/notification/adapter/inbound/observer/visit_event_subscriber.py`
- Create: `backend/apps/notification/adapter/inbound/observer/__init__.py`
- Create: `backend/apps/notification/app/dtos/__init__.py`
- Create: `backend/apps/notification/app/dtos/handle_visit_event_dto.py`
- Create: `backend/apps/notification/app/ports/input/__init__.py`
- Create: `backend/apps/notification/app/ports/input/handle_visit_event_use_case.py`
- Create: `backend/apps/notification/app/use_cases/__init__.py`
- Create: `backend/apps/notification/domain/services/clock.py`
- Create: `backend/apps/notification/tests/app/__init__.py`
- Create: `backend/apps/notification/tests/app/use_cases/__init__.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_handle_visit_event_interactor.py`
- Modify: `backend/core/observer/in_process_event_bus.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_notification_subscriber_wiring.py`
- Modify: `backend/tests/integration/test_visit_events_wiring.py`
- Modify: `backend/tests/test_hub_port_binding.py`
- Modify: `backend/tests/test_in_process_event_bus.py`

**Interfaces:**
- Consumes: 작업 1 의 이벤트 DTO 와 `subscribe`, 작업 3 의 `schedule_rules`(`reminder_at`·`next_visit_at`·`interval_weeks`)·`NewMessage`·`MessageAlreadyPendingError`, 작업 4 의 저장소 포트 넷과 pg 구현·스텁(`FakeChannels`·`FakeSettings`·`FakeTemplates`·`FakeMessages`).
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# notification.domain.services.clock
def utc_now() -> datetime            # datetime.now(timezone.utc)

# notification.app.dtos.handle_visit_event_dto
@dataclass(frozen=True)
class HandleVisitEventCommand:
    event: VisitEvent                # 매장 컨텍스트는 event.ctx

# notification.app.ports.input.handle_visit_event_use_case
class HandleVisitEventUseCase(ABC):
    async def handle_visit_event(self, command: HandleVisitEventCommand) -> None

# notification.app.use_cases.handle_visit_event_interactor
class HandleVisitEventInteractor(HandleVisitEventUseCase):
    def __init__(self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
                 messages: MessageRepository, now: Callable[[], datetime]) -> None
    async def handle_visit_event(self, command: HandleVisitEventCommand) -> None
    # 포트 호출: channels.get · settings.get · templates.get(ctx, kind) · messages.create / cancel_pending / has_delivered

# notification.adapter.inbound.observer.visit_event_subscriber
async def handle_visit_event(session: AsyncSession, event: VisitEvent) -> None
    # ChannelPgRepository·SettingsPgRepository·TemplatePgRepository·MessagePgRepository(session) + utc_now 로 인터랙터를 만들어 부른다

# core.observer.in_process_event_bus (더한 것)
def unsubscribe(handler: Subscriber) -> None     # 없으면 무시

# main.py
subscribe(handle_visit_event)                    # dependency_overrides 줄들 바로 뒤, import 시점
```

줄을 만드는 규칙(브리프 5.2 표 그대로). 모든 `create` 는 `NewMessage(shop_id=ctx.shop_id, visit_id, customer_id, pet_id=event.pet_id, kind, scheduled_at, variables, requested_by_member_id=None)`.

| 이벤트 | 취소 | 만드는 줄(설정 켜짐 + 템플릿 approved 가 공통 조건) |
|---|---|---|
| `VisitReserved(revived=False)` | — | `confirm`(now, 보낸 적 없을 때) · `reminder`(`reminder_at(starts_at, reminder_time, tz, now)` 가 있고 보낸 적 없을 때) |
| `VisitReserved(revived=True)` | — | `reminder` 만 |
| `VisitRescheduled` | `cancel_pending("rescheduled", visit_id, kinds=(reminder, change))` | `reminder`(새 시각, 보낸 적 검사 없음) · `change`(now, 보낸 적 검사 없음, `previous_starts_at`) |
| `VisitCanceled` | `cancel_pending("visit_canceled", visit_id)` 전 종류 | `reason == "shop_reason"` 이면 `cancel`(now, 보낸 적 없을 때) |
| `VisitClosed("no_show")` | `cancel_pending("no_show", visit_id)` 전 종류 | — |
| `VisitClosed("completed")` | — | `next_visit`(`next_visit_at(occurred_at, weeks, reminder_time, tz)`, 보낸 적 없을 때). weeks = `settings.next_visit_after_weeks` 또는 `interval_weeks(previous_completed_at, occurred_at, tz)` |
| `VisitReportIssued` | — | `report`(now, `has_delivered(visit, report, url=url)` 아닐 때) |

variables 키(값은 전부 `str`): 모든 종류 `starts_at`; `change` +`previous_starts_at`; `next_visit` +`completed_at`(= `occurred_at`)·`interval_weeks`(정수를 문자열로); `report` +`url`·`expires_at`(무기한이면 `""`). 시각은 `at.astimezone(timezone.utc).isoformat()` — 예 `2026-10-16T05:00:00+00:00`. 없는 값은 키가 없다(`expires_at` 만 `""`).

소비 쪽이다. 구독자 어댑터 `adapter/inbound/observer/visit_event_subscriber.handle_visit_event(session, event)` 가 요청의 세션으로 pg 저장소를 만들어 인터랙터를 부르고, `main.py` 가 import 시점에 `subscribe` 한다. 문지기: 채널이 `linked` 가 아니면 **아무것도 하지 않는다**(취소도). 규칙은 설계 5.2 표 그대로이되 이 계획이 새로 정한 것 둘 — **변경 안내와 바뀐 일정의 리마인드는 바뀔 때마다 간다**(연달아 바꾸면 안 나간 변경 안내는 `rescheduled` 로 취소되고 마지막 한 통), 나머지 종류(confirm·reminder·cancel·next_visit·report 의 같은 주소)는 한 번만. `variables` 에는 `starts_at`(전부)·`previous_starts_at`·`completed_at`·`interval_weeks`·`url`·`expires_at`(무기한이면 "") 를 UTC ISO(`+00:00`)로 넣는다 — 디스패처·재발송·설정 재계산이 이 키를 믿는다. "완료일"은 전이 시각(`occurred_at`)이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/app/__init__.py`:

```python

```

`backend/apps/notification/tests/app/use_cases/__init__.py`:

```python

```

`backend/apps/notification/tests/app/use_cases/test_handle_visit_event_interactor.py`:

```python
"""구독자 인터랙터 — visit 이벤트마다 설계 5.2 표의 줄을 만들고 취소한다(스텁). 시각은 모두 kst() 로 만든다."""
from datetime import datetime

import pytest

from hub.app.dtos.visit_events import (
    VisitCanceled,
    VisitClosed,
    VisitReportIssued,
    VisitRescheduled,
    VisitReserved,
)
from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand
from notification.app.use_cases.handle_visit_event_interactor import HandleVisitEventInteractor
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
)
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED, SENT
from notification.domain.value_objects.template_status import PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, message, settings, template
from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates, Journal

NOW = kst(10, 14, 11)          # 14일(수) 11:00
STARTS = kst(10, 16, 14)       # 16일(금) 14:00 → 리마인드는 15일 18:00
MOVED = kst(10, 20, 14)        # 20일(화) 14:00 → 리마인드는 19일 18:00
URL, OTHER_URL = "https://a/1", "https://a/2"


def _iso(at: datetime) -> str:
    return at.isoformat()


def _event(cls, **overrides):
    fields = dict(ctx=ctx(), visit_id=7, customer_id=1, pet_id=101, starts_at=STARTS, occurred_at=NOW)
    fields.update(overrides)
    return cls(**fields)


class _World:
    """연동된 매장(채널 linked, 설정 있음, 템플릿 6종 approved). 테스트가 필요한 것만 끈다."""

    def __init__(self, **settings_overrides) -> None:
        self.journal = Journal()
        self.channels, self.settings = FakeChannels(self.journal), FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.channels.rows[1] = channel()
        self.settings.rows[1] = settings(**{"next_visit_enabled": True, **settings_overrides})
        for i, kind in enumerate(KINDS, start=1):
            self.templates.rows[(1, kind)] = template(id=i, kind=kind)
        self.interactor = HandleVisitEventInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, messages=self.messages,
            now=lambda: NOW,
        )

    async def handle(self, event) -> None:
        await self.interactor.handle_visit_event(HandleVisitEventCommand(event=event))

    def rows(self, visit_id=7):
        return [(m.kind, m.status, m.scheduled_at, m.canceled_reason)
                for m in self.messages.rows.values() if m.visit_id == visit_id]

    def pending(self, visit_id=7):
        return [(m.kind, m.scheduled_at) for m in self.messages.rows.values()
                if m.visit_id == visit_id and m.status == SCHEDULED]

    def only(self, kind, status=SCHEDULED):
        [found] = [m for m in self.messages.rows.values() if m.kind == kind and m.status == status]
        return found

    def delivered(self, kind, **variables):
        """같은 방문·종류를 이미 보낸 줄."""
        self.messages.rows[90 + KINDS.index(kind)] = message(
            id=90 + KINDS.index(kind), visit_id=7, kind=kind, status=SENT, sent_at=kst(10, 13, 9),
            variables=variables)


# --- 공통 문지기 ---------------------------------------------------------------------------------------------------

async def test_채널이_없으면_아무_줄도_만들지_않는다():
    world = _World()
    del world.channels.rows[1]
    await world.handle(_event(VisitReserved))
    assert world.rows() == []


@pytest.mark.parametrize("status", [UNLINKED, TOKEN_REQUESTED])
async def test_채널이_linked_가_아니면_아무_줄도_만들지_않는다(status):
    world = _World()
    world.channels.rows[1] = channel(status=status)
    await world.handle(_event(VisitReserved))
    assert world.rows() == []


async def test_연동_안_된_매장은_취소도_하지_않는다():
    world = _World()
    await world.handle(_event(VisitReserved))
    world.channels.rows[1] = channel(status=UNLINKED)
    await world.handle(_event(VisitCanceled, reason="shop_reason"))
    assert [r[1] for r in world.rows()] == [SCHEDULED, SCHEDULED]
    assert ("cancel_pending", 7, "visit_canceled") not in world.journal


async def test_설정이_없으면_아무_줄도_만들지_않는다():
    world = _World()
    del world.settings.rows[1]
    await world.handle(_event(VisitReserved))
    assert world.rows() == []


# --- 예약됨 ---------------------------------------------------------------------------------------------------------

async def test_예약되면_confirm_은_지금_reminder_는_전날_설정_시각의_줄이_생긴다():
    world = _World()
    await world.handle(_event(VisitReserved))
    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 15, 18))]
    confirm = world.only(CONFIRM)
    assert (confirm.shop_id, confirm.visit_id, confirm.customer_id, confirm.pet_id) == (1, 7, 1, 101)
    assert confirm.requested_by_member_id is None
    assert confirm.variables == {"starts_at": _iso(STARTS)}
    assert world.only(REMINDER).variables == {"starts_at": _iso(STARTS)}


async def test_매장의_리마인드_시각을_따른다():
    from datetime import time

    world = _World(reminder_time=time(9, 30))
    await world.handle(_event(VisitReserved))
    assert world.only(REMINDER).scheduled_at == kst(10, 15, 9, 30)


async def test_전날은_매장_시간대의_날짜로_센다():
    world = _World()
    await world.handle(_event(VisitReserved, starts_at=kst(10, 17, 0, 30)))   # UTC 로는 16일 15:30
    assert world.only(REMINDER).scheduled_at == kst(10, 16, 18)


async def test_리마인드_시각이_이미_지났으면_confirm_만_생긴다():
    world = _World()
    await world.handle(_event(VisitReserved, starts_at=kst(10, 14, 15)))   # 오늘 15:00 — 전날 18:00 은 지났다
    assert world.pending() == [(CONFIRM, NOW)]


@pytest.mark.parametrize("flag, left", [("confirm_enabled", REMINDER), ("reminder_enabled", CONFIRM)])
async def test_설정이_꺼진_종류만_빠진다(flag, left):
    world = _World(**{flag: False})
    await world.handle(_event(VisitReserved))
    assert [k for k, _ in world.pending()] == [left]


@pytest.mark.parametrize("status", [PENDING, REJECTED, None])
async def test_템플릿이_approved_가_아니면_그_종류만_빠진다(status):
    world = _World()
    if status is None:
        del world.templates.rows[(1, CONFIRM)]
    else:
        world.templates.rows[(1, CONFIRM)] = template(kind=CONFIRM, status=status)
    await world.handle(_event(VisitReserved))
    assert [k for k, _ in world.pending()] == [REMINDER]


@pytest.mark.parametrize("kind, left", [(CONFIRM, REMINDER), (REMINDER, CONFIRM)])
async def test_이미_보낸_종류는_다시_만들지_않는다(kind, left):
    world = _World()
    world.delivered(kind)
    await world.handle(_event(VisitReserved))
    assert [k for k, _ in world.pending()] == [left]


async def test_되돌린_예약은_reminder_만_만든다():
    world = _World()
    await world.handle(_event(VisitReserved, revived=True))
    assert world.pending() == [(REMINDER, kst(10, 15, 18))]


async def test_같은_예약이_두_번_오면_MessageAlreadyPendingError_가_그대로_올라온다():
    world = _World()
    await world.handle(_event(VisitReserved))
    with pytest.raises(MessageAlreadyPendingError):
        await world.handle(_event(VisitReserved))


# --- 일정 바뀜 ------------------------------------------------------------------------------------------------------

async def _reserved_then_moved(world, **overrides):
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitRescheduled, previous_starts_at=STARTS, starts_at=MOVED, **overrides))


async def test_일정이_바뀌면_옛_reminder_는_rescheduled_로_취소되고_새_시각의_reminder_와_change_가_생긴다():
    world = _World()
    await _reserved_then_moved(world)
    assert world.rows() == [
        (CONFIRM, SCHEDULED, NOW, None),
        (REMINDER, CANCELED, kst(10, 15, 18), "rescheduled"),
        (REMINDER, SCHEDULED, kst(10, 19, 18), None),
        (CHANGE, SCHEDULED, NOW, None),
    ]
    assert world.only(CHANGE).variables == {"starts_at": _iso(MOVED), "previous_starts_at": _iso(STARTS)}
    assert world.only(REMINDER).variables == {"starts_at": _iso(MOVED)}
    assert ("cancel_pending", 7, "rescheduled") in world.journal


async def test_연달아_두_번_바꾸면_아직_안_나간_change_는_취소되고_마지막_한_통만_남는다():
    world = _World()
    await _reserved_then_moved(world)
    await world.handle(_event(VisitRescheduled, previous_starts_at=MOVED, starts_at=kst(10, 22, 10)))
    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 21, 18)), (CHANGE, NOW)]
    assert world.only(CHANGE).variables["previous_starts_at"] == _iso(MOVED)


async def test_바뀐_일정의_reminder_와_change_는_이미_보냈어도_다시_간다():
    world = _World()
    world.delivered(REMINDER)
    world.delivered(CHANGE)
    await world.handle(_event(VisitRescheduled, previous_starts_at=STARTS, starts_at=MOVED))
    assert world.pending() == [(REMINDER, kst(10, 19, 18)), (CHANGE, NOW)]


async def test_바뀐_일정의_리마인드_시각이_지났으면_change_만_생긴다():
    world = _World()
    await world.handle(_event(VisitRescheduled, previous_starts_at=STARTS, starts_at=kst(10, 14, 16)))
    assert world.pending() == [(CHANGE, NOW)]


@pytest.mark.parametrize("how", ["setting_off", "template_pending"])
async def test_변경_안내가_꺼졌거나_템플릿이_미승인이면_reminder_만_다시_만든다(how):
    world = _World(change_enabled=False) if how == "setting_off" else _World()
    if how == "template_pending":
        world.templates.rows[(1, CHANGE)] = template(kind=CHANGE, status=PENDING)
    await _reserved_then_moved(world)
    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 19, 18))]


# --- 취소됨·노쇼 ----------------------------------------------------------------------------------------------------

async def test_매장_사정_취소는_대기_줄을_전부_취소하고_cancel_줄을_만든다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitCanceled, reason="shop_reason"))
    assert world.rows() == [
        (CONFIRM, CANCELED, NOW, "visit_canceled"),
        (REMINDER, CANCELED, kst(10, 15, 18), "visit_canceled"),
        (CANCEL, SCHEDULED, NOW, None),
    ]
    assert world.only(CANCEL).variables == {"starts_at": _iso(STARTS)}


async def test_고객_요청_취소는_대기_줄만_취소하고_cancel_줄은_없다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitCanceled, reason="customer_request"))
    assert [r[1] for r in world.rows()] == [CANCELED, CANCELED]


@pytest.mark.parametrize("how", ["setting_off", "template_rejected", "delivered"])
async def test_취소_안내는_변경_설정_템플릿_보낸_적을_본다(how):
    world = _World(change_enabled=False) if how == "setting_off" else _World()
    if how == "template_rejected":
        world.templates.rows[(1, CANCEL)] = template(kind=CANCEL, status=REJECTED)
    if how == "delivered":
        world.delivered(CANCEL)
    await world.handle(_event(VisitCanceled, reason="shop_reason"))
    assert world.pending() == []


async def test_노쇼는_대기_줄을_no_show_로_취소만_한다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitClosed, outcome="no_show", previous_completed_at=None))
    assert [(r[1], r[3]) for r in world.rows()] == [(CANCELED, "no_show"), (CANCELED, "no_show")]


# --- 완료 -----------------------------------------------------------------------------------------------------------

def _completed(previous=None, **overrides):
    return _event(VisitClosed, outcome="completed", previous_completed_at=previous, starts_at=kst(10, 14, 9),
                  **overrides)


async def test_완료는_대기_줄을_건드리지_않고_앞선_완료가_없으면_4주_뒤_설정_시각에_next_visit_을_만든다():
    world = _World()
    await world.handle(_event(VisitReserved, starts_at=kst(10, 14, 9)))
    await world.handle(_completed())
    assert world.pending() == [(CONFIRM, NOW), (NEXT_VISIT, kst(11, 11, 18))]
    assert world.only(NEXT_VISIT).variables == {
        "starts_at": _iso(kst(10, 14, 9)), "completed_at": _iso(NOW), "interval_weeks": "4"}


async def test_앞선_완료가_있으면_그_간격을_주로_반올림한_뒤다():
    world = _World()
    await world.handle(_completed(previous=kst(9, 23, 11)))   # 21일 전 → 3주
    assert world.pending() == [(NEXT_VISIT, kst(11, 4, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "3"


async def test_설정의_주_수가_있으면_간격보다_우선한다():
    world = _World(next_visit_after_weeks=6)
    await world.handle(_completed(previous=kst(9, 23, 11)))
    assert world.pending() == [(NEXT_VISIT, kst(11, 25, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "6"


@pytest.mark.parametrize("how", ["setting_off", "template_pending", "delivered"])
async def test_다음_예약_제안은_설정_템플릿_보낸_적을_본다(how):
    world = _World(next_visit_enabled=False) if how == "setting_off" else _World()
    if how == "template_pending":
        world.templates.rows[(1, NEXT_VISIT)] = template(kind=NEXT_VISIT, status=PENDING)
    if how == "delivered":
        world.delivered(NEXT_VISIT)
    await world.handle(_completed())
    assert world.pending() == []


# --- 알림장 발급 ----------------------------------------------------------------------------------------------------

async def test_알림장을_보내면_report_줄에_주소와_기간이_든다():
    world = _World()
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=kst(11, 13, 0)))
    assert world.pending() == [(REPORT, NOW)]
    assert world.only(REPORT).variables == {"starts_at": _iso(STARTS), "url": URL, "expires_at": _iso(kst(11, 13, 0))}


async def test_무기한_링크의_expires_at_은_빈_문자열이다():
    world = _World()
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    assert world.only(REPORT).variables["expires_at"] == ""


async def test_같은_주소를_이미_보냈으면_만들지_않고_다른_주소면_다시_만든다():
    world = _World()
    world.delivered(REPORT, url=URL)
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    assert world.pending() == []
    await world.handle(_event(VisitReportIssued, url=OTHER_URL, expires_at=None))
    assert world.pending() == [(REPORT, NOW)]
    assert world.only(REPORT).variables["url"] == OTHER_URL


@pytest.mark.parametrize("how", ["setting_off", "template_pending"])
async def test_알림장_안내는_설정과_템플릿을_본다(how):
    world = _World(report_enabled=False) if how == "setting_off" else _World()
    if how == "template_pending":
        world.templates.rows[(1, REPORT)] = template(kind=REPORT, status=PENDING)
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    assert world.pending() == []
```

`backend/tests/integration/test_notification_subscriber_wiring.py`:

```python
"""visit 의 요청이 실제 배선(main.py 의 subscribe, 요청의 세션)으로 notification_messages 에 줄을 남기는지 본다.

채널·설정·템플릿 줄은 SQL 로 직접 넣는다(온보딩 API 는 작업 8). 알림장 주소는 응답·로그에 찍지 않는다 — 비어 있지
않은지만 본다.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from notification.domain.value_objects.message_kind import KINDS
from tests.integration.support import bearer, error_of, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


def _utc_iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


async def _link(wired, shop_id: int) -> None:
    """연동을 마친 매장 — 채널 linked, 설정 기본값, 템플릿 6종 approved."""
    await wired.execute(
        "INSERT INTO notification_channels (shop_id, status, provider, provider_channel_id, linked_at) "
        "VALUES (:shop_id, 'linked', 'solapi', 'KA01PF0001', now())", shop_id=shop_id)
    await wired.execute("INSERT INTO notification_settings (shop_id) VALUES (:shop_id)", shop_id=shop_id)
    for i, kind in enumerate(KINDS, start=1):
        await wired.execute(
            "INSERT INTO notification_templates (shop_id, kind, text_version, provider_template_id, status, "
            "requested_at) VALUES (:shop_id, :kind, 1, :template_id, 'approved', now())",
            shop_id=shop_id, kind=kind, template_id=f"KA01TP000{i}")


async def _shop(wired, linked=True):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    if linked:
        await _link(wired, shop_id)
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    return shop_id, headers, body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _book(wired, shop_id, headers, customer_id, pet_id, starts_at: datetime):
    return await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": starts_at.isoformat()})


async def _booked(wired, shop_id, headers, customer_id, pet_id, starts_at: datetime) -> dict:
    booked = await _book(wired, shop_id, headers, customer_id, pet_id, starts_at)
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]


async def _transition(wired, shop_id, headers, visit_id, action, **extra) -> None:
    response = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                    json={"visit_ids": [visit_id], "action": action, **extra})
    assert response.status_code == 200, response.text


async def _messages(wired, visit_id: int) -> list[dict]:
    """id 순. 주소는 고르지 않는다 — 있는지(has_url)만."""
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, scheduled_at, canceled_reason, requested_by_member_id, "
            "variables->>'starts_at' AS starts_at, variables->>'previous_starts_at' AS previous_starts_at, "
            "length(variables->>'url') > 0 AS has_url "
            "FROM notification_messages WHERE visit_id = :visit_id ORDER BY id"), {"visit_id": visit_id})
        return [dict(row._mapping) for row in rows]


def _brief(rows: list[dict]) -> list[tuple]:
    return [(r["kind"], r["status"], r["canceled_reason"]) for r in rows]


def _near_now(at: datetime) -> bool:
    return abs(datetime.now(timezone.utc) - at) < timedelta(minutes=1)


async def test_예약을_등록하면_confirm_은_지금_reminder_는_전날_18시_KST_의_줄이_생긴다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    starts_at = _at(3, 14)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, starts_at)

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [("confirm", "scheduled", None), ("reminder", "scheduled", None)]
    assert _near_now(rows[0]["scheduled_at"])
    assert rows[1]["scheduled_at"] == _at(2, 18)
    assert all(r["starts_at"] == _utc_iso(starts_at) and r["requested_by_member_id"] is None for r in rows)


async def test_일정을_바꾸면_옛_reminder_는_rescheduled_로_취소되고_새_reminder_와_change_가_생긴다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    moved = await wired.api.put(
        f"/v1/shops/{shop_id}/visits/{visit['visit_id']}", headers=headers,
        json={"starts_at": _at(5, 16).isoformat(), "pet_id": pet_id, "duration_minutes": visit["duration_minutes"],
              "menu_ids": [], "memo": None})
    assert moved.status_code == 200, moved.text

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [
        ("confirm", "scheduled", None), ("reminder", "canceled", "rescheduled"),
        ("reminder", "scheduled", None), ("change", "scheduled", None),
    ]
    assert rows[2]["scheduled_at"] == _at(4, 18)
    assert (rows[3]["previous_starts_at"], rows[3]["starts_at"]) == (_utc_iso(_at(3, 14)), _utc_iso(_at(5, 16)))
    assert _near_now(rows[3]["scheduled_at"])


async def test_매장_사정으로_취소하면_대기_줄이_전부_취소되고_cancel_줄이_생긴다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    await _transition(wired, shop_id, headers, visit["visit_id"], "cancel", cancel_reason="shop_reason")

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [
        ("confirm", "canceled", "visit_canceled"), ("reminder", "canceled", "visit_canceled"),
        ("cancel", "scheduled", None),
    ]


async def test_같은_예약을_두_번_등록하면_둘째는_409_이고_메시지_줄은_그대로다(wired):
    """방문 저장이 롤백되면 구독자가 쓴 줄도 함께 사라진다(설계 3.2)."""
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    again = await _book(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    assert error_of(again) == (409, "VISIT_DUPLICATE")

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [("confirm", "scheduled", None), ("reminder", "scheduled", None)]
    async with wired.engine.connect() as conn:
        total = (await conn.execute(text("SELECT count(*) FROM notification_messages"))).scalar_one()
    assert total == 2


async def test_연동하지_않은_매장은_줄이_없다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired, linked=False)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    await _transition(wired, shop_id, headers, visit["visit_id"], "cancel", cancel_reason="shop_reason")
    assert await _messages(wired, visit["visit_id"]) == []


async def test_알림장을_보내면_report_줄에_주소가_있고_같은_링크로_다시_보내면_줄이_늘지_않는다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(-1, 11))   # 어제 — 리마인드는 지났다
    visit_id = visit["visit_id"]
    await _transition(wired, shop_id, headers, visit_id, "start")
    written = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                  json={"care_note": "눈물 자국을 닦았어요", "media": []})
    assert written.status_code == 200, written.text
    await _transition(wired, shop_id, headers, visit_id, "complete")
    report = f"/v1/shops/{shop_id}/visits/{visit_id}/report"
    sent = await wired.api.put(report, headers=headers, json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text

    rows = await _messages(wired, visit_id)
    assert _brief(rows) == [("confirm", "scheduled", None), ("report", "scheduled", None)]
    assert rows[1]["has_url"] is True and _near_now(rows[1]["scheduled_at"])

    again = await wired.api.put(report, headers=headers, json={"hidden_media_ids": []})
    assert again.status_code == 200, again.text
    assert _brief(await _messages(wired, visit_id)) == _brief(rows)
```

`backend/tests/integration/test_visit_events_wiring.py`:

```diff
@@ -9,7 +9,7 @@ import pytest
 from httpx import ASGITransport, AsyncClient
 from sqlalchemy import text
 
-from core.observer.in_process_event_bus import clear_subscribers, subscribe
+from core.observer.in_process_event_bus import subscribe, unsubscribe
 from hub.app.dtos.visit_events import VisitCanceled, VisitRescheduled, VisitReserved
 from tests.integration.support import bearer, make_operator, shop_with_owner
 
@@ -28,7 +28,7 @@ def _at(days: int, hour: int) -> str:
 
 @pytest.fixture
 def received():
-    """구독자 하나를 실제 버스에 등록해 받은 (세션, 이벤트)를 모은다. 끝나면 구독자 목록을 비운다."""
+    """구독자 하나를 실제 버스에 등록해 받은 (세션, 이벤트)를 모은다. 끝나면 자기 구독자만 뺀다(실제 구독자는 남긴다)."""
     events = []
 
     async def collect(session, event):
@@ -37,7 +37,7 @@ def received():
 
     subscribe(collect)
     yield events
-    clear_subscribers()
+    unsubscribe(collect)
 
 
 async def _shop(wired):
@@ -98,7 +98,7 @@ async def test_구독자가_던지면_500_이고_방문은_생기지_않는다(w
                                     headers=headers)
         assert booked.status_code == 500
     finally:
-        clear_subscribers()
+        unsubscribe(explode)
     day = (datetime.now(SEOUL).date() + timedelta(days=3)).isoformat()
     listed = await wired.api.get(f"/v1/shops/{shop_id}/visits?date={day}", headers=headers)
     assert listed.status_code == 200 and listed.json()["items"] == []
```

`backend/tests/test_hub_port_binding.py`:

```diff
@@ -3,8 +3,9 @@ import pytest
 from fastapi import Depends, FastAPI
 
 import main
-from core.observer.in_process_event_bus import get_event_bus
+from core.observer.in_process_event_bus import get_event_bus, subscribers
 from core.shop_guard import get_shop_access_port
+from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
 from tenancy.dependencies.hub_ports import get_user_directory
 from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
 from core.security import get_current_user_id
@@ -39,6 +40,10 @@ def test_도메인_이벤트_자리는_core_의_버스로_채운다():
         get_domain_events()
 
 
+def test_notification_구독자가_버스에_등록되어_있다():
+    assert handle_visit_event in subscribers()
+
+
 def _app_with(path, dependency=None):
     app = FastAPI()
     deps = [Depends(dependency)] if dependency else []
```

`backend/tests/test_in_process_event_bus.py`:

```diff
@@ -11,6 +11,7 @@ from core.observer.in_process_event_bus import (
     get_event_bus,
     subscribe,
     subscribers,
+    unsubscribe,
 )
 from hub.app.dtos.shop_context import ShopContext
 from hub.app.dtos.visit_events import VisitReserved
@@ -21,9 +22,13 @@ NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)
 
 @pytest.fixture(autouse=True)
 def _clean_subscribers():
+    """비우고 돌린 뒤 실제 구독자(main.py 가 import 때 꽂은 것)를 되살린다 — 같은 프로세스의 뒤 테스트가 잃지 않게."""
+    kept = subscribers()
     clear_subscribers()
     yield
     clear_subscribers()
+    for handler in kept:
+        subscribe(handler)
 
 
 def _event() -> VisitReserved:
@@ -68,6 +73,15 @@ async def test_같은_함수를_두_번_subscribe_해도_한_번만_등록된다
     assert subscribers() == (handler,)
 
 
+async def test_unsubscribe_는_그_구독자만_빼고_없는_것은_무시한다():
+    first, second = _recorder("first", []), _recorder("second", [])
+    subscribe(first)
+    subscribe(second)
+    unsubscribe(first)
+    unsubscribe(first)
+    assert subscribers() == (second,)
+
+
 async def test_get_event_bus_는_넘긴_세션에_묶인_버스를_준다():
     log, session, event = [], object(), _event()
     subscribe(_recorder("registered", log))
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

- 단위 `docker compose run --rm --no-deps backend pytest apps/notification/tests/app/use_cases/test_handle_visit_event_interactor.py tests/test_in_process_event_bus.py tests/test_hub_port_binding.py -q -p no:cacheprovider` → 수집 오류 3(`ModuleNotFoundError: No module named 'notification.adapter.inbound.observer'`, `cannot import name 'unsubscribe'`, 인터랙터 모듈 없음), `Interrupted: 3 errors during collection`.
- 통합 `… run --rm backend pytest tests/integration/test_notification_subscriber_wiring.py tests/integration/test_visit_events_wiring.py …` → `test_visit_events_wiring.py` 수집 오류(`unsubscribe` 없음). 새 파일만 따로: 5 failed(`assert [] == [('confirm', 'scheduled', None), …]` — 줄이 안 생김), 1 passed(연동 안 된 매장은 당연히 비어 있음).

구현 뒤 첫 실행에서 테스트 쪽 실수 하나를 고쳤다(구현은 그대로): `_World(**settings_overrides)` 가 `settings(next_visit_enabled=True, **overrides)` 로 같은 키를 두 번 넘겨 `TypeError` → 사전을 합쳐 넘김.

- [ ] **Step 3: 구현한다**

`backend/apps/notification/app/use_cases/handle_visit_event_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.visit_events import (
    VisitCanceled,
    VisitClosed,
    VisitEvent,
    VisitReportIssued,
    VisitRescheduled,
    VisitReserved,
)
from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand
from notification.app.ports.input.handle_visit_event_use_case import HandleVisitEventUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.services.schedule_rules import interval_weeks, next_visit_at, reminder_at
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import APPROVED


def _iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


class HandleVisitEventInteractor(HandleVisitEventUseCase):
    """visit 이벤트를 받아 같은 트랜잭션에서 알림 줄을 만들고 취소한다(설계 5.2 표).

    연동되지 않은 매장(채널이 linked 가 아니거나 설정이 없음)은 아무것도 하지 않는다 — 취소도 하지 않는다, 줄이 없다.
    업체를 부르지 않으므로 외부 장애로 방문 저장이 막히지 않는다(N13·N14). 같은 방문·종류의 대기 줄이 이미 있으면
    저장소의 MessageAlreadyPendingError 를 그대로 올린다 — 발행 쪽의 중복 호출이 500 으로 드러나게 둔다.
    """

    def __init__(
        self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
        messages: MessageRepository, now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._messages = messages
        self._now = now

    async def handle_visit_event(self, command: HandleVisitEventCommand) -> None:
        event, ctx = command.event, command.event.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            return
        settings = await self._settings.get(ctx)
        if settings is None:
            return
        now = self._now()
        if isinstance(event, VisitReserved):
            await self._reserved(ctx, settings, event, now)
        elif isinstance(event, VisitRescheduled):
            await self._rescheduled(ctx, settings, event, now)
        elif isinstance(event, VisitCanceled):
            await self._canceled(ctx, settings, event, now)
        elif isinstance(event, VisitClosed):
            await self._closed(ctx, settings, event)
        elif isinstance(event, VisitReportIssued):
            await self._report_issued(ctx, settings, event, now)

    async def _reserved(self, ctx: ShopContext, settings: NotificationSettings, event: VisitReserved, now: datetime):
        # 되돌린 예약은 접수 안내를 다시 보내지 않는다 — 리마인드만.
        if not event.revived and await self._allowed(ctx, settings, CONFIRM, event.visit_id):
            await self._create(ctx, event, CONFIRM, now)
        at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
        if at is not None and await self._allowed(ctx, settings, REMINDER, event.visit_id):
            await self._create(ctx, event, REMINDER, at)

    async def _rescheduled(
        self, ctx: ShopContext, settings: NotificationSettings, event: VisitRescheduled, now: datetime
    ) -> None:
        # 옛 시각의 리마인드와 아직 안 나간 변경 안내를 거둔다(N16). 바뀐 일정의 리마인드·변경 안내는 앞서 보냈어도
        # 다시 간다 — 보호자에게 마지막 시각이 가야 한다. 연달아 바꾸면 마지막 변경 안내 한 통만 남는다.
        await self._messages.cancel_pending(ctx, "rescheduled", event.visit_id, kinds=(REMINDER, CHANGE))
        at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
        if at is not None and await self._allowed(ctx, settings, REMINDER):
            await self._create(ctx, event, REMINDER, at)
        if await self._allowed(ctx, settings, CHANGE):
            await self._create(ctx, event, CHANGE, now, previous_starts_at=_iso(event.previous_starts_at))

    async def _canceled(self, ctx: ShopContext, settings: NotificationSettings, event: VisitCanceled, now: datetime):
        await self._messages.cancel_pending(ctx, "visit_canceled", event.visit_id)   # N17
        if event.reason == "shop_reason" and await self._allowed(ctx, settings, CANCEL, event.visit_id):
            await self._create(ctx, event, CANCEL, now)

    async def _closed(self, ctx: ShopContext, settings: NotificationSettings, event: VisitClosed) -> None:
        if event.outcome == "no_show":
            await self._messages.cancel_pending(ctx, "no_show", event.visit_id)   # N17
            return
        # 완료는 대기 줄을 건드리지 않는다. 주 수는 설정값, 없으면 앞선 완료와의 간격(없으면 4주).
        if not await self._allowed(ctx, settings, NEXT_VISIT, event.visit_id):
            return
        weeks = settings.next_visit_after_weeks
        if weeks is None:
            weeks = interval_weeks(event.previous_completed_at, event.occurred_at, ctx.timezone)
        at = next_visit_at(event.occurred_at, weeks, settings.reminder_time, ctx.timezone)
        await self._create(ctx, event, NEXT_VISIT, at, completed_at=_iso(event.occurred_at), interval_weeks=str(weeks))

    async def _report_issued(
        self, ctx: ShopContext, settings: NotificationSettings, event: VisitReportIssued, now: datetime
    ) -> None:
        # 같은 주소를 이미 보냈으면 다시 보내지 않는다. 끊고 새로 보낸 링크(주소가 다름)는 다시 간다.
        if await self._allowed(ctx, settings, REPORT, event.visit_id, url=event.url):
            expires_at = _iso(event.expires_at) if event.expires_at is not None else ""
            await self._create(ctx, event, REPORT, now, url=event.url, expires_at=expires_at)

    async def _allowed(
        self, ctx: ShopContext, settings: NotificationSettings, kind: str, delivered_visit_id: int | None = None,
        url: str | None = None,
    ) -> bool:
        """설정이 켜져 있고 템플릿이 approved 이고, delivered_visit_id 를 주면 그 방문에 같은 종류를 보낸 적이 없다."""
        if not settings.enabled_for(kind):
            return False
        template = await self._templates.get(ctx, kind)
        if template is None or template.status != APPROVED:
            return False
        if delivered_visit_id is None:
            return True
        return not await self._messages.has_delivered(ctx, delivered_visit_id, kind, url=url)

    async def _create(
        self, ctx: ShopContext, event: VisitEvent, kind: str, scheduled_at: datetime, **variables: str
    ) -> None:
        # starts_at 은 모든 종류에 넣는다 — 디스패처가 #{일시} 와 too_late 판정에 쓴다.
        await self._messages.create(ctx, NewMessage(
            shop_id=ctx.shop_id, visit_id=event.visit_id, customer_id=event.customer_id, pet_id=event.pet_id,
            kind=kind, scheduled_at=scheduled_at, variables={"starts_at": _iso(event.starts_at), **variables},
        ))
```

`backend/apps/notification/adapter/inbound/observer/visit_event_subscriber.py`:

```python
"""Observer — core/observer 버스에 등록되는 구독자. main.py 가 import 때 subscribe 로 꽂는다(설계 3.1·3.3).

발행한 visit 인터랙터와 같은 세션·같은 트랜잭션에서 돈다 — 구독자가 던지면 방문 저장도 롤백된다(N13).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.visit_events import VisitEvent
from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand
from notification.app.use_cases.handle_visit_event_interactor import HandleVisitEventInteractor
from notification.domain.services.clock import utc_now


async def handle_visit_event(session: AsyncSession, event: VisitEvent) -> None:
    """요청의 세션으로 저장소를 만들어 인터랙터를 부른다. 이벤트를 로그에 남기지 않는다(알림장 주소가 든다, N12)."""
    use_case = HandleVisitEventInteractor(
        channels=ChannelPgRepository(session), settings=SettingsPgRepository(session),
        templates=TemplatePgRepository(session), messages=MessagePgRepository(session), now=utc_now,
    )
    await use_case.handle_visit_event(HandleVisitEventCommand(event=event))
```

`backend/apps/notification/adapter/inbound/observer/__init__.py`:

```python

```

`backend/apps/notification/app/dtos/__init__.py`:

```python

```

`backend/apps/notification/app/dtos/handle_visit_event_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.visit_events import VisitEvent


@dataclass(frozen=True)
class HandleVisitEventCommand:
    """visit 이 발행한 이벤트 하나. 매장 컨텍스트는 이벤트 안(event.ctx)에 있다."""

    event: VisitEvent
```

`backend/apps/notification/app/ports/input/__init__.py`:

```python

```

`backend/apps/notification/app/ports/input/handle_visit_event_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand


class HandleVisitEventUseCase(ABC):
    @abstractmethod
    async def handle_visit_event(self, command: HandleVisitEventCommand) -> None: ...
```

`backend/apps/notification/app/use_cases/__init__.py`:

```python

```

`backend/apps/notification/domain/services/clock.py`:

```python
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

`backend/core/observer/in_process_event_bus.py`:

```diff
@@ -23,12 +23,18 @@ def subscribe(handler: Subscriber) -> None:
         _subscribers.append(handler)
 
 
+def unsubscribe(handler: Subscriber) -> None:
+    """그 구독자만 뺀다(없으면 무시). 통합 테스트가 자기 구독자를 빼고 실제 구독자는 남기는 데 쓴다."""
+    if handler in _subscribers:
+        _subscribers.remove(handler)
+
+
 def subscribers() -> tuple[Subscriber, ...]:
     return tuple(_subscribers)
 
 
 def clear_subscribers() -> None:
-    """테스트용."""
+    """단위 테스트용 — 실제 구독자까지 비우므로 통합 테스트는 unsubscribe 를 쓴다."""
     _subscribers.clear()
```

`backend/main.py`:

```diff
@@ -9,7 +9,7 @@ from fastapi import FastAPI
 
 from core.access_log import redact_access_log_queries
 from core.database import dispose_engine, init_engine
-from core.observer.in_process_event_bus import get_event_bus
+from core.observer.in_process_event_bus import get_event_bus, subscribe
 from core.redis import dispose_redis
 
 from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
@@ -47,6 +47,7 @@ from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_ro
 from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
 from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
 from media.dependencies.media_library_provider import get_media_library_use_case
+from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
 from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
@@ -204,8 +205,9 @@ app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
 app.dependency_overrides[get_visit_media_library] = get_media_library_use_case
 app.dependency_overrides[get_customer_media_library] = get_media_library_use_case
 app.dependency_overrides[get_shop_profile] = get_shop_profile_use_case
-# 도메인 이벤트 — visit 이 발행하고 core 의 같은 세션 동기 버스가 구독자(main.py 가 기동 때 subscribe 로 꽂는다)에 넘긴다.
+# 도메인 이벤트 — visit 이 발행하고 core 의 같은 세션 동기 버스가 구독자에 넘긴다. 구독자는 여기서 꽂는다.
 app.dependency_overrides[get_domain_events] = get_event_bus
+subscribe(handle_visit_event)
 
 
 @app.get("/health")
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 단위(인터랙터 41 + 버스 6 + 바인딩 15) | 62 passed (새로 더한 것 43: 인터랙터 41, 버스 `unsubscribe` 1, 바인딩 1) |
| 이 작업의 통합(새 파일 6 + 기존 배선 2) | 8 passed (새로 더한 것 6) |
| 단위 전체 (`-m "not integration and not network"`) | 1476 passed (시작 1433 + 43) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken (1183 파일) |

(단위의 warning 1은 기존 `starlette.testclient` 사용 중단 경고, 통합의 28은 기존 SQLAlchemy 경고다.) 통합 세션은 테스트 DB(`chagocnote_test`)에만 붙었다 — 개발 DB 에 마이그레이션을 올리지 않았다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 문지기 `if channel is None or not channel.is_linked:` → `if channel is None:` → `test_handle_visit_event_interactor.py::test_채널이_linked_가_아니면_아무_줄도_만들지_않는다[unlinked]`, `[token_requested]`, `::test_연동_안_된_매장은_취소도_하지_않는다`
- `_rescheduled` 의 `cancel_pending(…, "rescheduled", …)` 줄 제거 → 단위 `::test_일정이_바뀌면_옛_reminder_는_rescheduled_로_취소되고_새_시각의_reminder_와_change_가_생긴다`, `::test_연달아_두_번_바꾸면_…`, `::test_변경_안내가_꺼졌거나_템플릿이_미승인이면_reminder_만_다시_만든다[setting_off]`, `[template_pending]`(모두 `MessageAlreadyPendingError`); 통합 `test_notification_subscriber_wiring.py::test_일정을_바꾸면_옛_reminder_는_rescheduled_로_취소되고_새_reminder_와_change_가_생긴다`
- `_canceled` 에서 `event.reason == "shop_reason" and` 제거 → `::test_고객_요청_취소는_대기_줄만_취소하고_cancel_줄은_없다`
- `_allowed` 의 `has_delivered(…, url=url)` → `url=None` → `::test_같은_주소를_이미_보냈으면_만들지_않고_다른_주소면_다시_만든다`
- `_reserved` 에서 `not event.revived and` 제거 → `::test_되돌린_예약은_reminder_만_만든다`
- `main.py` 의 `subscribe(handle_visit_event)` 제거 → `tests/test_hub_port_binding.py::test_notification_구독자가_버스에_등록되어_있다`; 통합 새 파일 6 중 5(연동 안 된 매장 제외)
- `_closed` 의 `interval_weeks(event.previous_completed_at, …)` → `interval_weeks(None, …)`(늘 4주) → `::test_앞선_완료가_있으면_그_간격을_주로_반올림한_뒤다`
- `_rescheduled` 의 취소 범위 `kinds=(REMINDER, CHANGE)` → `(REMINDER,)` → `::test_연달아_두_번_바꾸면_아직_안_나간_change_는_취소되고_마지막_한_통만_남는다`
- `_reserved` 의 confirm 에서 보낸 적 검사 제거(`_allowed(ctx, settings, CONFIRM)`) → `::test_이미_보낸_종류는_다시_만들지_않는다[confirm-reminder]`
- `_canceled` 의 취소 사유 `"visit_canceled"` → `"no_show"` → 단위 `::test_매장_사정_취소는_대기_줄을_전부_취소하고_cancel_줄을_만든다`; 통합 `::test_매장_사정으로_취소하면_대기_줄이_전부_취소되고_cancel_줄이_생긴다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 구독자 — 예약·변경·취소·완료·알림장 이벤트를 같은 트랜잭션에서 메시지 줄로

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 발송 게이트웨이 — 포트·DTO·오류, 솔라피 어댑터(HMAC·접수·상태 조회·온보딩, MockTransport 로만 검증), dev 가짜 어댑터, 설정 키

**Files:**
- Create: `backend/apps/notification/app/ports/output/message_gateway_port.py`
- Create: `backend/apps/notification/adapter/outbound/strategy/solapi_gateway.py`
- Create: `backend/apps/notification/adapter/outbound/strategy/fake_gateway.py`
- Modify: `backend/apps/notification/dependencies/notification_wiring.py`
- Modify: `.env.example`
- Create: `backend/apps/notification/adapter/outbound/strategy/__init__.py`
- Create: `backend/apps/notification/tests/adapter/test_fake_gateway.py`
- Create: `backend/apps/notification/tests/adapter/test_solapi_gateway.py`
- Create: `backend/apps/notification/tests/dependencies/__init__.py`
- Create: `backend/apps/notification/tests/dependencies/test_notification_wiring.py`
- Modify: `backend/core/config.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/test_config_defaults.py`

**Interfaces:**
- Consumes: 작업 3 의 `TemplateText`·`TEMPLATES`; 기존 `core/config.py`·`secret_manager`, `main.py` 의 lifespan, `tests/test_config_defaults.py`. 새 의존성 없음(httpx 는 이미 있다).
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# notification.app.ports.output.message_gateway_port
@dataclass(frozen=True)
class FallbackText: from_number: str; text: str; channel: str                # "sms" | "lms"
@dataclass(frozen=True)
class OutgoingMessage:
    to: str; provider_channel_id: str; provider_template_id: str
    variables: Mapping[str, str]            # {"매장명": "…"} — 어댑터가 "#{매장명}" 으로 바꾼다
    button_url: str | None; fallback: FallbackText | None
@dataclass(frozen=True)
class Accepted: provider_message_id: str
@dataclass(frozen=True)
class DeliveryState: status: str; channel_used: str | None; error_code: str | None; error_kind: str | None
    # status "pending" | "sent" | "failed"; channel_used 는 sent 일 때 "alimtalk" | "sms" | "lms"; error_* 는 failed 일 때
@dataclass(frozen=True)
class TemplateState: status: str; rejected_reason: str | None                  # "pending" | "approved" | "rejected"

class GatewayError(Exception):                 # .code: str, .kind: str
    def __init__(self, code: str, kind: str, message: str = "") -> None       # message 기본 f"업체 호출 실패 ({code})"
class GatewayTransientError(GatewayError):     # __init__(code, message="") → kind "transient"
class GatewayPermanentError(GatewayError):     # __init__(code, message="") → kind "permanent"

class MessageGatewayPort(ABC):
    async def request_channel_token(self, search_id: str, admin_phone: str, category_code: str) -> None
    async def link_channel(self, search_id: str, admin_phone: str, category_code: str, token: str) -> str   # TokenInvalidError
    async def register_template(self, provider_channel_id: str, template: TemplateText, text_version: int) -> str
    async def template_state(self, provider_template_id: str) -> TemplateState
    async def request_sender_verification(self, phone: str) -> None
    async def confirm_sender_verification(self, phone: str, code: str) -> None     # TokenInvalidError
    async def send(self, message: OutgoingMessage) -> Accepted                     # GatewayTransientError | GatewayPermanentError
    async def delivery_state(self, provider_message_id: str) -> DeliveryState
    async def balance(self) -> int                                                  # 원 (balance + point)

# notification.adapter.outbound.strategy.solapi_gateway
TEMPLATE_CATEGORY_CODE = "003001"
_DELIVERY: dict[str, tuple[str, str | None, str | None]]      # 업체 4자리 코드 → (status, channel_used, error_kind); 없는 코드 → failed/transient
class SolapiGateway(MessageGatewayPort):
    def __init__(self, api_key: str, api_secret: str, *, base_url: str = "https://api.solapi.com",
                 transport: httpx.AsyncBaseTransport | None = None, timeout: float = 10.0,
                 now: Callable[[], datetime] = _utc_now, salt: Callable[[], str] = _salt) -> None

# notification.adapter.outbound.strategy.fake_gateway
FAKE_TOKEN = "000000"; PERMANENT_CODE, TRANSIENT_CODE = "3104", "3040"
class FakeGateway(MessageGatewayPort):
    def __init__(self, *, reject_next_visit: bool = False, balance: int = 100000) -> None
    sent_messages: list[OutgoingMessage]; calls: list[tuple]
    # link_channel: token == "000000" → f"pf-{search_id}", 아니면 TokenInvalidError
    # register_template → f"tpl-{provider_channel_id}-{template.kind}-v{text_version}"; template_state 늘 approved
    #   (reject_next_visit 이고 ID 에 "-next_visit-" 가 들면 rejected "가짜 반려")
    # confirm_sender_verification: code == "000000" 만 통과
    # send → Accepted(f"fake-{n}") (n 은 호출 순서, 1부터). delivery_state: 번호 끝 네 자리
    #   "0000" → failed/permanent "3104" (fallback 이 있으면 sent, channel_used=fallback.channel)
    #   "9999" → failed/transient "3040" · "8888" → pending 두 번 뒤 sent/alimtalk · 그 밖 → sent/alimtalk
    # calls 항목: ("request_channel_token", search_id, admin_phone, category_code) · ("link_channel", search_id, admin_phone, category_code)
    #   · ("register_template", channel_id, kind, text_version) · ("template_state", template_id) · ("request_sender_verification", phone)
    #   · ("confirm_sender_verification", phone) · ("send", to, template_id) · ("delivery_state", message_id) · ("balance",)

# core.config
SOLAPI_API_KEY: str = ""; SOLAPI_API_SECRET: str = ""; SOLAPI_BALANCE_WARN_KRW: int = 30000; NOTIFICATION_DAILY_CAP: int = 300

# notification.dependencies.notification_wiring
def build_message_gateway(api_key: str, api_secret: str, app_env: str) -> MessageGatewayPort
    # 둘 다 있으면 SolapiGateway(api_key, api_secret); 둘 다 비고 app_env == "dev" 면 FakeGateway(); 그 밖 RuntimeError(메시지에 "SOLAPI_API_KEY")
def get_message_gateway() -> MessageGatewayPort     # 프로세스에 하나. 모듈 이름 SOLAPI_API_KEY·SOLAPI_API_SECRET·APP_ENV 를 monkeypatch 하고 reset 하면 바꿀 수 있다
def reset_message_gateway() -> None

# main.py lifespan
get_message_gateway()                                # init_engine() 바로 뒤
```

외부 업체 경계다. `MessageGatewayPort` 아홉 메서드(채널 토큰 신청·연동, 템플릿 등록·상태, 발신번호 인증 시작·확인, 발송·전달 상태·잔액)와 두 오류(`GatewayTransientError`·`GatewayPermanentError`; 토큰·인증번호 틀림은 도메인의 `TokenInvalidError` 를 던진다)를 정하고, `strategy/solapi_gateway.py` 가 HMAC-SHA256 인증 헤더·`send-many/detail` 접수·업체 상태 코드 표 `_DELIVERY` 로 구현한다. **실제 `api.solapi.com` 은 어디서도 부르지 않는다** — 테스트는 `httpx.MockTransport`. `strategy/fake_gateway.py` 는 dev·테스트용(토큰 `000000`, 번호 끝 `0000` 영구 실패·`9999` 일시 실패·`8888` 은 상태 조회 두 번 pending). `build_message_gateway(api_key, api_secret, app_env)` 는 키가 비면 dev 에서만 가짜를 주고 그 밖에서는 `RuntimeError` — lifespan 이 한 번 불러 운영은 첫 발송이 아니라 기동에서 멈춘다. 발신번호 인증 경로와 템플릿 카테고리 코드는 공식 문서를 읽지 못해 SDK 소스로만 맞췄다(결정 기록 009 "남는 것" 의 실계정 검증 항목).

**환경**: `.env` 에 `SOLAPI_API_KEY`·`SOLAPI_API_SECRET` 를 더하지 않아도 dev 는 가짜 게이트웨이로 돈다(`.env.example` 의 네 줄은 빈 값 예시다). 운영은 두 키가 필수다(README, 작업 11).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/adapter/test_fake_gateway.py`:

```python
"""dev·흐름 테스트용 가짜 게이트웨이 — 번호 끝 네 자리와 토큰 000000 규칙이 결정적인지 본다."""
from __future__ import annotations

import pytest

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.ports.output.message_gateway_port import FallbackText, MessageGatewayPort, OutgoingMessage
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import TEMPLATES
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT


def _message(to: str, fallback: FallbackText | None = None) -> OutgoingMessage:
    return OutgoingMessage(to=to, provider_channel_id="pf-@dubu", provider_template_id="tpl-1",
                           variables={"매장명": "두부네"}, button_url=None, fallback=fallback)


def test_가짜_게이트웨이는_포트를_구현한다():
    assert isinstance(FakeGateway(), MessageGatewayPort)


async def test_토큰_000000_만_연동되고_채널_ID_는_검색_아이디에서_나온다():
    gateway = FakeGateway()
    await gateway.request_channel_token("@dubu", "01055550000", "001")
    assert await gateway.link_channel("@dubu", "01055550000", "001", "000000") == "pf-@dubu"
    with pytest.raises(TokenInvalidError):
        await gateway.link_channel("@dubu", "01055550000", "001", "123456")


async def test_템플릿은_즉시_승인되고_ID_에_채널_종류_판이_든다():
    gateway = FakeGateway()
    template_id = await gateway.register_template("pf-@dubu", TEMPLATES[CONFIRM], 2)
    assert template_id == "tpl-pf-@dubu-confirm-v2"
    state = await gateway.template_state(template_id)
    assert (state.status, state.rejected_reason) == ("approved", None)


async def test_반려_옵션을_켜면_다음_예약_제안_템플릿만_반려된다():
    gateway = FakeGateway(reject_next_visit=True)
    rejected = await gateway.template_state(await gateway.register_template("pf-1", TEMPLATES[NEXT_VISIT], 1))
    approved = await gateway.template_state(await gateway.register_template("pf-1", TEMPLATES[CONFIRM], 1))
    assert (rejected.status, rejected.rejected_reason) == ("rejected", "가짜 반려")
    assert approved.status == "approved"


async def test_발신번호_인증은_000000_만_통과한다():
    gateway = FakeGateway()
    await gateway.request_sender_verification("0215550000")
    await gateway.confirm_sender_verification("0215550000", "000000")
    with pytest.raises(TokenInvalidError):
        await gateway.confirm_sender_verification("0215550000", "123456")


async def test_발송은_늘_접수되고_호출_순서로_ID_가_붙는다():
    gateway = FakeGateway()
    first = await gateway.send(_message("01055551234"))
    second = await gateway.send(_message("01055550000"))
    assert (first.provider_message_id, second.provider_message_id) == ("fake-1", "fake-2")
    assert [m.to for m in gateway.sent_messages] == ["01055551234", "01055550000"]


async def test_번호_끝_네_자리로_결과를_가른다():
    gateway = FakeGateway()
    plain = await gateway.send(_message("01055551234"))
    permanent = await gateway.send(_message("01055550000"))
    transient = await gateway.send(_message("01055559999"))
    sent = await gateway.delivery_state(plain.provider_message_id)
    assert (sent.status, sent.channel_used, sent.error_code, sent.error_kind) == ("sent", "alimtalk", None, None)
    failed = await gateway.delivery_state(permanent.provider_message_id)
    assert (failed.status, failed.error_code, failed.error_kind) == ("failed", "3104", "permanent")
    retry = await gateway.delivery_state(transient.provider_message_id)
    assert (retry.status, retry.error_code, retry.error_kind) == ("failed", "3040", "transient")


async def test_끝이_8888_이면_두_번_대기한_뒤_성공한다():
    gateway = FakeGateway()
    accepted = await gateway.send(_message("01055558888"))
    states = [(await gateway.delivery_state(accepted.provider_message_id)).status for _ in range(3)]
    assert states == ["pending", "pending", "sent"]


async def test_끝이_0000_인데_대체_문자가_있으면_문자로_간_것으로_친다():
    gateway = FakeGateway()
    fallback = FallbackText(from_number="0215550000", text="[두부네] 알림장", channel="lms")
    accepted = await gateway.send(_message("01055550000", fallback))
    state = await gateway.delivery_state(accepted.provider_message_id)
    assert (state.status, state.channel_used, state.error_code) == ("sent", "lms", None)


async def test_잔액은_기본_십만_원이고_생성_인자로_바꾼다():
    assert await FakeGateway().balance() == 100000
    assert await FakeGateway(balance=500).balance() == 500


async def test_호출_기록을_남긴다():
    gateway = FakeGateway()
    await gateway.request_channel_token("@dubu", "01055550000", "001")
    await gateway.send(_message("01055551234"))
    assert gateway.calls[0] == ("request_channel_token", "@dubu", "01055550000", "001")
    assert gateway.calls[1][0] == "send"
```

`backend/apps/notification/tests/adapter/test_solapi_gateway.py`:

```python
"""솔라피 어댑터 — 실제 API 를 부르지 않고 httpx.MockTransport 로 경로·본문·헤더·오류 분류를 본다.

번호·주소는 테스트 안에서도 가짜 값만 쓴다. 기록(caplog)과 예외 메시지에 번호가 없어야 한다(N12).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx
import pytest

from notification.adapter.outbound.strategy.solapi_gateway import SolapiGateway
from notification.app.ports.output.message_gateway_port import (
    FallbackText,
    GatewayPermanentError,
    GatewayTransientError,
    OutgoingMessage,
)
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import TEMPLATES
from notification.domain.value_objects.message_kind import CONFIRM, REPORT

API_KEY, API_SECRET = "NCS-KEY", "secret-value"
PHONE = "01055550101"
FIXED_NOW = datetime(2026, 10, 14, 1, 2, 3, tzinfo=timezone.utc)
FIXED_SALT = "0123456789abcdef0123456789abcdef"


class _Recorder:
    """받은 요청을 쌓고, 등록한 응답(또는 예외)을 돌려주는 가짜 서버."""

    def __init__(self, *responses) -> None:
        self.requests: list[httpx.Request] = []
        self._responses = list(responses)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def body(self, index: int = 0) -> dict:
        return json.loads(self.requests[index].content)


def _gateway(recorder: _Recorder) -> SolapiGateway:
    return SolapiGateway(
        API_KEY, API_SECRET, transport=httpx.MockTransport(recorder), now=lambda: FIXED_NOW, salt=lambda: FIXED_SALT,
    )


def _ok(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)


def _message(**overrides) -> OutgoingMessage:
    fields = dict(
        to=PHONE, provider_channel_id="KA01PF0001", provider_template_id="KA01TP0001",
        variables={"매장명": "두부네", "대상": "두부", "일시": "10월 15일(목) 14:00"}, button_url=None, fallback=None,
    )
    fields.update(overrides)
    return OutgoingMessage(**fields)


_SEND_OK = {"groupInfo": {"groupId": "G1"}, "failedMessageList": [],
            "messageList": [{"messageId": "M1", "statusCode": "2000", "statusMessage": "정상 접수"}]}


# --- 인증 헤더 ---------------------------------------------------------------------------------

async def test_인증_헤더는_HMAC_SHA256_으로_date_와_salt_를_이어_서명한다():
    recorder = _Recorder(_ok({"balance": 1, "point": 0}))
    await _gateway(recorder).balance()
    date = FIXED_NOW.isoformat()
    expected = hmac.new(API_SECRET.encode(), (date + FIXED_SALT).encode(), hashlib.sha256).hexdigest()
    assert recorder.requests[0].headers["Authorization"] == (
        f"HMAC-SHA256 apiKey={API_KEY}, date={date}, salt={FIXED_SALT}, signature={expected}"
    )


async def test_요청마다_새_salt_로_서명하고_기본_주소는_솔라피다():
    recorder = _Recorder(_ok({"balance": 1, "point": 0}), _ok({"balance": 1, "point": 0}))
    gateway = SolapiGateway(API_KEY, API_SECRET, transport=httpx.MockTransport(recorder))
    await gateway.balance()
    await gateway.balance()
    first, second = (r.headers["Authorization"] for r in recorder.requests)
    assert first != second
    assert str(recorder.requests[0].url).startswith("https://api.solapi.com/")


# --- 온보딩 ------------------------------------------------------------------------------------

async def test_토큰_신청은_채널_검색_아이디와_관리자_번호를_보낸다():
    recorder = _Recorder(_ok({"success": True}))
    await _gateway(recorder).request_channel_token("@dubu", PHONE, "001")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("POST", "/kakao/v2/channels/token")
    assert recorder.body() == {"searchId": "@dubu", "phoneNumber": PHONE}


async def test_채널_연동은_토큰까지_보내고_채널_ID_를_돌려준다():
    recorder = _Recorder(_ok({"channelId": "KA01PF0001", "searchId": "@dubu"}))
    channel_id = await _gateway(recorder).link_channel("@dubu", PHONE, "001", "123456")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("POST", "/kakao/v2/channels")
    assert recorder.body() == {"searchId": "@dubu", "phoneNumber": PHONE, "categoryCode": "001", "token": "123456"}
    assert channel_id == "KA01PF0001"


async def test_채널_연동에서_업체가_거절하면_토큰_오류다():
    recorder = _Recorder(httpx.Response(400, json={"errorCode": "ValidationError", "errorMessage": "토큰이 틀립니다"}))
    with pytest.raises(TokenInvalidError):
        await _gateway(recorder).link_channel("@dubu", PHONE, "001", "000000")


async def test_템플릿_등록은_추가한_뒤_검수를_요청하고_템플릿_ID_를_돌려준다():
    recorder = _Recorder(_ok({"templateId": "KA01TP0009", "status": "PENDING"}), _ok({"templateId": "KA01TP0009"}))
    template_id = await _gateway(recorder).register_template("KA01PF0001", TEMPLATES[CONFIRM], 3)
    create, inspect = recorder.requests
    assert (create.method, create.url.path) == ("POST", "/kakao/v2/templates")
    body = recorder.body()
    assert body["channelId"] == "KA01PF0001"
    assert body["name"] == "차곡노트 confirm v3"
    assert body["content"] == TEMPLATES[CONFIRM].body
    assert body["messageType"] == "BA" and body["emphasizeType"] == "NONE" and body["securityFlag"] is False
    assert body["categoryCode"]
    assert "buttons" not in body
    assert (inspect.method, inspect.url.path) == ("PUT", "/kakao/v2/templates/KA01TP0009/inspection")
    assert template_id == "KA01TP0009"


async def test_버튼이_있는_문안은_링크_변수를_쓰는_웹링크_버튼_하나로_등록한다():
    recorder = _Recorder(_ok({"templateId": "KA01TP0010"}), _ok({}))
    await _gateway(recorder).register_template("KA01PF0001", TEMPLATES[REPORT], 1)
    assert recorder.body()["buttons"] == [
        {"buttonType": "WL", "buttonName": "알림장 보기", "linkMo": "#{링크}", "linkPc": "#{링크}"},
    ]


@pytest.mark.parametrize("provider_status, expected", [
    ("PENDING", "pending"), ("INSPECTING", "pending"), ("APPROVED", "approved"),
])
async def test_템플릿_상태를_조회해_셋으로_접는다(provider_status, expected):
    recorder = _Recorder(_ok({"templateId": "KA01TP0001", "status": provider_status, "comments": []}))
    state = await _gateway(recorder).template_state("KA01TP0001")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("GET", "/kakao/v2/templates/KA01TP0001")
    assert (state.status, state.rejected_reason) == (expected, None)


async def test_반려된_템플릿은_마지막_관리자_의견을_사유로_돌려준다():
    recorder = _Recorder(_ok({"status": "REJECTED", "comments": [
        {"isAdmin": False, "memberId": "m", "content": "검수 부탁드려요", "dateCreated": "2026-10-01T00:00:00Z"},
        {"isAdmin": True, "memberId": "a", "content": "변수 비중이 큽니다", "dateCreated": "2026-10-02T00:00:00Z"},
    ]}))
    state = await _gateway(recorder).template_state("KA01TP0001")
    assert (state.status, state.rejected_reason) == ("rejected", "변수 비중이 큽니다")


async def test_발신번호_인증_요청은_번호를_등록하고_인증을_건다():
    recorder = _Recorder(_ok({"phoneNumber": PHONE, "status": "PENDING"}), _ok({"mfa": {"transactionId": "tx-1"}}))
    await _gateway(recorder).request_sender_verification(PHONE)
    register, authenticate = recorder.requests
    assert (register.method, register.url.path) == ("POST", "/senderid/v1/numbers")
    assert recorder.body() == {"phoneNumber": PHONE}
    assert (authenticate.method, authenticate.url.path) == ("PUT", f"/senderid/v1/numbers/{PHONE}/authenticate")
    assert json.loads(authenticate.headers["x-mfa-data"]) == {"authType": "ARS", "extras": {"phoneNumber": PHONE}}


async def test_발신번호_인증_확인은_같은_경로에_거래_ID_와_인증번호를_보낸다():
    recorder = _Recorder(_ok({}), _ok({"mfa": {"transactionId": "tx-1"}}), _ok({"status": "ACTIVE"}))
    gateway = _gateway(recorder)
    await gateway.request_sender_verification(PHONE)
    await gateway.confirm_sender_verification(PHONE, "654321")
    confirm = recorder.requests[2]
    assert (confirm.method, confirm.url.path) == ("PUT", f"/senderid/v1/numbers/{PHONE}/authenticate")
    assert json.loads(confirm.headers["x-mfa-data"]) == {
        "authType": "ARS", "extras": {"phoneNumber": PHONE}, "transactionId": "tx-1", "token": "654321",
    }


async def test_인증번호가_틀리면_토큰_오류다():
    recorder = _Recorder(httpx.Response(400, json={"errorCode": "InvalidToken", "errorMessage": "틀렸습니다"}))
    with pytest.raises(TokenInvalidError):
        await _gateway(recorder).confirm_sender_verification(PHONE, "000000")


# --- 발송 ---------------------------------------------------------------------------------------

async def test_발송은_알림톡_옵션으로_접수하고_변수_키를_업체_형식으로_바꾼다():
    recorder = _Recorder(_ok(_SEND_OK))
    accepted = await _gateway(recorder).send(_message())
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("POST", "/messages/v4/send-many/detail")
    body = recorder.body()
    assert body["showMessageList"] is True
    [message] = body["messages"]
    assert message["to"] == PHONE and message["type"] == "ATA"
    assert message["kakaoOptions"]["pfId"] == "KA01PF0001"
    assert message["kakaoOptions"]["templateId"] == "KA01TP0001"
    assert message["kakaoOptions"]["variables"] == {
        "#{매장명}": "두부네", "#{대상}": "두부", "#{일시}": "10월 15일(목) 14:00",
    }
    assert accepted.provider_message_id == "M1"


async def test_대체_문자가_없으면_disableSms_이고_발신번호와_문구가_없다():
    recorder = _Recorder(_ok(_SEND_OK))
    await _gateway(recorder).send(_message(fallback=None))
    [message] = recorder.body()["messages"]
    assert message["kakaoOptions"]["disableSms"] is True
    assert "from" not in message and "text" not in message


async def test_대체_문자가_있으면_발신번호와_문구를_싣고_disableSms_가_꺼진다():
    recorder = _Recorder(_ok(_SEND_OK))
    fallback = FallbackText(from_number="0215550000", text="[두부네] 10월 15일(목) 14:00 예약이 접수되었어요.", channel="sms")
    await _gateway(recorder).send(_message(fallback=fallback))
    [message] = recorder.body()["messages"]
    assert message["kakaoOptions"]["disableSms"] is False
    assert (message["from"], message["text"]) == (fallback.from_number, fallback.text)


async def test_버튼_주소는_링크_변수로_넘긴다():
    recorder = _Recorder(_ok(_SEND_OK))
    await _gateway(recorder).send(_message(variables={"매장명": "두부네"}, button_url="https://r.example/abc"))
    assert recorder.body()["messages"][0]["kakaoOptions"]["variables"]["#{링크}"] == "https://r.example/abc"


async def test_접수가_거절된_메시지는_업체_상태_코드로_분류한다():
    rejected = {"groupInfo": {"groupId": "G1"}, "messageList": [], "failedMessageList": [
        {"messageId": "M9", "statusCode": "1062", "statusMessage": "발신번호 미등록"}]}
    with pytest.raises(GatewayPermanentError) as permanent:
        await _gateway(_Recorder(_ok(rejected))).send(_message())
    assert permanent.value.code == "1062"
    low_balance = {**rejected, "failedMessageList": [{"messageId": "M9", "statusCode": "1030", "statusMessage": "잔액 부족"}]}
    with pytest.raises(GatewayTransientError) as transient:
        await _gateway(_Recorder(_ok(low_balance))).send(_message())
    assert transient.value.code == "1030"


# --- 상태 조회 ----------------------------------------------------------------------------------

def _listed(status_code: str, message_type: str = "ATA") -> httpx.Response:
    return _ok({"limit": 20, "messageList": {"M1": {"messageId": "M1", "type": message_type, "statusCode": status_code}}})


async def test_상태_조회는_메시지_ID_로_목록을_조회한다():
    recorder = _Recorder(_listed("4000"))
    await _gateway(recorder).delivery_state("M1")
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("GET", "/messages/v4/list")
    assert request.url.params["messageId"] == "M1"


@pytest.mark.parametrize("status_code, message_type, expected", [
    ("2000", "ATA", ("pending", None, None, None)),
    ("3000", "ATA", ("pending", None, None, None)),
    ("4000", "ATA", ("sent", "alimtalk", None, None)),
    ("4000", "SMS", ("sent", "sms", None, None)),
    ("4000", "LMS", ("sent", "lms", None, None)),
    ("3104", "ATA", ("failed", None, "3104", "permanent")),   # 카카오톡 미사용자
    ("3107", "ATA", ("failed", None, "3107", "permanent")),   # 알림톡 차단
    ("3010", "ATA", ("failed", None, "3010", "permanent")),   # 수신번호 형식 오류
    ("3103", "ATA", ("failed", None, "3103", "permanent")),   # 템플릿 불일치
    ("3040", "ATA", ("failed", None, "3040", "transient")),   # 전송시간 초과
    ("3041", "ATA", ("failed", None, "3041", "transient")),   # 단말기 busy
    ("3042", "ATA", ("failed", None, "3042", "transient")),   # 음영지역
    ("3024", "ATA", ("failed", None, "3024", "transient")),   # 서버 오류
    ("1030", "ATA", ("failed", None, "1030", "transient")),   # 잔액 부족
    ("9999", "ATA", ("failed", None, "9999", "transient")),   # 표에 없는 코드
])
async def test_업체_상태_코드를_대기_성공_실패로_접는다(status_code, message_type, expected):
    state = await _gateway(_Recorder(_listed(status_code, message_type))).delivery_state("M1")
    assert (state.status, state.channel_used, state.error_code, state.error_kind) == expected


async def test_목록에_아직_없는_메시지는_대기다():
    state = await _gateway(_Recorder(_ok({"limit": 20, "messageList": {}}))).delivery_state("M1")
    assert state.status == "pending"


async def test_잔액은_잔액과_포인트를_더한_원_단위_정수다():
    recorder = _Recorder(_ok({"balance": 12345.5, "point": 100}))
    assert await _gateway(recorder).balance() == 12445
    request = recorder.requests[0]
    assert (request.method, request.url.path) == ("GET", "/cash/v1/balance")


# --- 오류 분류 ----------------------------------------------------------------------------------

@pytest.mark.parametrize("failure, code", [
    (httpx.ReadTimeout("timeout"), "NETWORK"),
    (httpx.ConnectError("refused"), "NETWORK"),
    (httpx.Response(500, json={"errorCode": "InternalServerError", "errorMessage": "x"}), "500"),
    (httpx.Response(503, text="bad gateway"), "503"),
    (httpx.Response(429, json={"errorCode": "TooManyRequests", "message": "잦은 호출"}), "429"),
])
async def test_시간_초과_연결_실패_5xx_429_는_일시_오류다(failure, code):
    with pytest.raises(GatewayTransientError) as info:
        await _gateway(_Recorder(failure)).send(_message())
    assert (info.value.code, info.value.kind) == (code, "transient")


async def test_그_밖의_4xx_는_업체_오류_코드를_단_영구_오류다():
    recorder = _Recorder(httpx.Response(400, json={"errorCode": "ValidationError", "errorMessage": "잘못된 요청"}))
    with pytest.raises(GatewayPermanentError) as info:
        await _gateway(recorder).send(_message())
    assert (info.value.code, info.value.kind) == ("ValidationError", "permanent")
    with pytest.raises(GatewayPermanentError) as no_body:
        await _gateway(_Recorder(httpx.Response(403, text="forbidden"))).balance()
    assert no_body.value.code == "403"


async def test_번호는_예외_메시지와_기록에_남지_않는다(caplog):
    """N12 — 요청 본문·경로에 번호가 있어도 예외 메시지와 로그 레코드에는 없다."""
    caplog.set_level(logging.DEBUG)
    recorder = _Recorder(
        httpx.Response(400, json={"errorCode": "ValidationError", "errorMessage": f"수신번호 {PHONE} 오류"}),
        _ok({}), httpx.Response(400, json={"errorCode": "InvalidToken", "errorMessage": PHONE}),
    )
    gateway = _gateway(recorder)
    with pytest.raises(GatewayPermanentError) as send_error:
        await gateway.send(_message())
    with pytest.raises(TokenInvalidError) as token_error:
        await gateway.request_sender_verification(PHONE)
    assert PHONE not in str(send_error.value) and PHONE not in repr(send_error.value)
    assert PHONE not in str(token_error.value)
    assert PHONE in str(recorder.requests[2].url)     # 경로에는 번호가 있다 — 그래서 기록을 본다
    assert all(PHONE not in record.getMessage() for record in caplog.records)
```

`backend/apps/notification/tests/dependencies/__init__.py`:

```python

```

`backend/apps/notification/tests/dependencies/test_notification_wiring.py`:

```python
"""발송 게이트웨이 조립 — 키가 둘 다 있으면 솔라피, 둘 다 비고 dev 면 가짜, 그 밖은 기동 실패(설계 6.1)."""
from __future__ import annotations

import pytest

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.adapter.outbound.strategy.solapi_gateway import SolapiGateway
from notification.dependencies import notification_wiring as wiring


def test_키가_둘_다_있으면_솔라피_어댑터다():
    assert isinstance(wiring.build_message_gateway("key", "secret", "prod"), SolapiGateway)
    assert isinstance(wiring.build_message_gateway("key", "secret", "dev"), SolapiGateway)


def test_키가_둘_다_비고_dev_면_가짜_어댑터다():
    assert isinstance(wiring.build_message_gateway("", "", "dev"), FakeGateway)


def test_운영에서_키가_비면_기동하지_않는다():
    with pytest.raises(RuntimeError, match="SOLAPI_API_KEY"):
        wiring.build_message_gateway("", "", "prod")


@pytest.mark.parametrize("api_key, api_secret", [("key", ""), ("", "secret")])
def test_키가_하나만_있으면_환경과_상관없이_기동하지_않는다(api_key, api_secret):
    with pytest.raises(RuntimeError, match="SOLAPI_API_KEY"):
        wiring.build_message_gateway(api_key, api_secret, "dev")


def test_프로세스에_하나만_만들고_되돌리면_새로_만든다(monkeypatch):
    monkeypatch.setattr(wiring, "SOLAPI_API_KEY", "")
    monkeypatch.setattr(wiring, "SOLAPI_API_SECRET", "")
    monkeypatch.setattr(wiring, "APP_ENV", "dev")
    wiring.reset_message_gateway()
    first = wiring.get_message_gateway()
    assert first is wiring.get_message_gateway()
    wiring.reset_message_gateway()
    assert wiring.get_message_gateway() is not first
    wiring.reset_message_gateway()
```

`backend/tests/test_config_defaults.py`:

```diff
@@ -58,3 +58,13 @@ def test_알림장_웹_주소는_끝의_빗금을_떼고_비밀값은_없으면_
     assert (load_config().REPORT_WEB_BASE_URL, load_config().REPORT_WEB_SECRET) == ("http://127.0.0.1:3010", "")
     config = load_config(REPORT_WEB_BASE_URL="https://r.chagocnote.com/", REPORT_WEB_SECRET="web-secret")
     assert (config.REPORT_WEB_BASE_URL, config.REPORT_WEB_SECRET) == ("https://r.chagocnote.com", "web-secret")
+
+
+def test_솔라피_키는_없으면_빈_문자열이고_잔액_경고와_하루_상한은_정수_기본값이다(load_config):
+    config = load_config()
+    assert (config.SOLAPI_API_KEY, config.SOLAPI_API_SECRET) == ("", "")
+    assert (config.SOLAPI_BALANCE_WARN_KRW, config.NOTIFICATION_DAILY_CAP) == (30000, 300)
+    config = load_config(SOLAPI_API_KEY="k", SOLAPI_API_SECRET="s", SOLAPI_BALANCE_WARN_KRW="5000",
+                         NOTIFICATION_DAILY_CAP="10")
+    assert (config.SOLAPI_API_KEY, config.SOLAPI_API_SECRET) == ("k", "s")
+    assert (config.SOLAPI_BALANCE_WARN_KRW, config.NOTIFICATION_DAILY_CAP) == (5000, 10)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

이어받음: 테스트가 먼저 있었고, 구현 뒤 통과. 내가 새로 더한 테스트는 없다(브리프의 테스트 항목이 전부 있었다). 대신 변이 7개(4절)로 각 테스트가 실제로 실패할 수 있음을 확인했다.

- [ ] **Step 3: 구현한다**

`backend/apps/notification/app/ports/output/message_gateway_port.py`:

```python
"""발송 게이트웨이 포트(설계 6.1) — 업체가 바뀌어도 이 포트만 다시 구현한다.

온보딩(채널 연동·템플릿 등록·발신번호 인증)과 발송·상태 조회·잔액을 한 포트가 낸다. 발송은 접수만 돌려주고
결과는 뒤에 delivery_state 로 본다(웹훅은 첫 판에서 쓰지 않는다).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from notification.domain.services.templates import TemplateText


@dataclass(frozen=True)
class FallbackText:
    """알림톡이 실패했을 때 업체가 보낼 문자. channel 은 "sms" | "lms"."""

    from_number: str
    text: str
    channel: str


@dataclass(frozen=True)
class OutgoingMessage:
    to: str
    provider_channel_id: str
    provider_template_id: str
    variables: Mapping[str, str]       # {"매장명": "…"} — 어댑터가 업체 형식(#{매장명})으로 바꾼다
    button_url: str | None
    fallback: FallbackText | None


@dataclass(frozen=True)
class Accepted:
    provider_message_id: str


@dataclass(frozen=True)
class DeliveryState:
    status: str                        # "pending" | "sent" | "failed"
    channel_used: str | None           # sent 일 때 "alimtalk" | "sms" | "lms"
    error_code: str | None             # failed 일 때 업체 코드
    error_kind: str | None             # failed 일 때 "transient" | "permanent"


@dataclass(frozen=True)
class TemplateState:
    status: str                        # "pending" | "approved" | "rejected"
    rejected_reason: str | None


class GatewayError(Exception):
    """업체 호출 실패의 바탕. code 는 업체 오류 코드 또는 HTTP 상태, kind 는 "transient" | "permanent"."""

    def __init__(self, code: str, kind: str, message: str = "") -> None:
        super().__init__(message or f"업체 호출 실패 ({code})")
        self.code = code
        self.kind = kind


class GatewayTransientError(GatewayError):
    """네트워크·시간 초과·업체 5xx·429·잔액 부족 — 다시 시도한다."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code, "transient", message)


class GatewayPermanentError(GatewayError):
    """그 밖의 4xx — 다시 시도해도 같다."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code, "permanent", message)


class MessageGatewayPort(ABC):
    @abstractmethod
    async def request_channel_token(self, search_id: str, admin_phone: str, category_code: str) -> None: ...

    @abstractmethod
    async def link_channel(self, search_id: str, admin_phone: str, category_code: str, token: str) -> str:
        """provider_channel_id 를 돌려준다. 토큰이 틀리거나 만료됐으면 TokenInvalidError."""

    @abstractmethod
    async def register_template(self, provider_channel_id: str, template: TemplateText, text_version: int) -> str:
        """등록 + 검수 요청. provider_template_id 를 돌려준다."""

    @abstractmethod
    async def template_state(self, provider_template_id: str) -> TemplateState: ...

    @abstractmethod
    async def request_sender_verification(self, phone: str) -> None: ...

    @abstractmethod
    async def confirm_sender_verification(self, phone: str, code: str) -> None:
        """인증번호가 틀리면 TokenInvalidError."""

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> Accepted: ...

    @abstractmethod
    async def delivery_state(self, provider_message_id: str) -> DeliveryState: ...

    @abstractmethod
    async def balance(self) -> int:
        """원."""
```

`backend/apps/notification/adapter/outbound/strategy/solapi_gateway.py`:

```python
"""솔라피(api.solapi.com) 어댑터 — HMAC-SHA256 서명, 알림톡 접수, 상태 조회, 채널·템플릿·발신번호 온보딩.

경로·본문 키는 공식 SDK(solapi-nodejs·solapi-kotlin·solapi-php)와 개발자 문서에서 읽은 것이다(T6 보고서 7절).
요청 본문(번호·변수)·헤더·응답 본문은 로그에 찍지 않고, 예외 메시지에는 업체 코드만 넣는다(N12).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from notification.app.ports.output.message_gateway_port import (
    Accepted,
    DeliveryState,
    GatewayPermanentError,
    GatewayTransientError,
    MessageGatewayPort,
    OutgoingMessage,
    TemplateState,
)
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import URL_VARIABLE, TemplateText

# httpx 는 요청 URL 을 INFO 로 기록한다 — 발신번호 인증 경로에 번호가 들어 있어 끈다(N12).
logging.getLogger("httpx").setLevel(logging.WARNING)

# 알림톡 템플릿 카테고리 코드 — 실계정에서 GET /kakao/v2/templates/categories 로 확인해 맞춘다(T6 보고서 7절).
TEMPLATE_CATEGORY_CODE = "003001"

# 업체 4자리 상태 코드 → (status, channel_used, error_kind). sent 의 channel_used 는 메시지 type 으로 정한다.
# 표에 없는 실패 코드는 transient(다시 시도하는 쪽이 싸다 — 3회 뒤 멈춘다). 출처: solapi.com/guides/message-status-codes
_PENDING = ("pending", None, None)
_SENT = ("sent", None, None)
_PERMANENT = ("failed", None, "permanent")
_TRANSIENT = ("failed", None, "transient")
_DELIVERY: dict[str, tuple[str, str | None, str | None]] = {
    "2000": _PENDING, "3000": _PENDING,
    "4000": _SENT,
    # 입력·설정 오류, 수신 거부, 수신번호 오류, 카카오톡 미사용·차단, 템플릿 불일치
    "1010": _PERMANENT, "1011": _PERMANENT, "1026": _PERMANENT, "1041": _PERMANENT, "1042": _PERMANENT,
    "1043": _PERMANENT, "1057": _PERMANENT, "1060": _PERMANENT, "1061": _PERMANENT, "1062": _PERMANENT,
    "1065": _PERMANENT, "2061": _PERMANENT, "2062": _PERMANENT, "2065": _PERMANENT, "3010": _PERMANENT,
    "3013": _PERMANENT, "3031": _PERMANENT, "3032": _PERMANENT, "3047": _PERMANENT, "3052": _PERMANENT,
    "3061": _PERMANENT, "3101": _PERMANENT, "3102": _PERMANENT, "3103": _PERMANENT, "3104": _PERMANENT,
    "3105": _PERMANENT, "3106": _PERMANENT, "3107": _PERMANENT, "3117": _PERMANENT,
    # 잔액 부족, 서버 오류, 전송시간 초과, 단말기 사정, 음영지역, 발송 가능 시간 아님
    "1024": _TRANSIENT, "1030": _TRANSIENT, "2024": _TRANSIENT, "2025": _TRANSIENT, "2230": _TRANSIENT,
    "3012": _TRANSIENT, "3024": _TRANSIENT, "3040": _TRANSIENT, "3041": _TRANSIENT, "3042": _TRANSIENT,
    "3043": _TRANSIENT, "3044": _TRANSIENT, "3045": _TRANSIENT, "3046": _TRANSIENT, "3053": _TRANSIENT,
    "3056": _TRANSIENT, "3057": _TRANSIENT, "3108": _TRANSIENT,
}
_CHANNEL_BY_TYPE = {"ATA": "alimtalk", "SMS": "sms", "LMS": "lms"}
_TEMPLATE_STATUS = {"PENDING": "pending", "INSPECTING": "pending", "APPROVED": "approved", "REJECTED": "rejected"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _salt() -> str:
    return secrets.token_hex(16)


class SolapiGateway(MessageGatewayPort):
    """transport·now·salt 는 테스트 주입용이다(httpx.MockTransport, 고정 시각·솔트로 서명을 검증한다)."""

    def __init__(
        self, api_key: str, api_secret: str, *, base_url: str = "https://api.solapi.com",
        transport: httpx.AsyncBaseTransport | None = None, timeout: float = 10.0,
        now: Callable[[], datetime] = _utc_now, salt: Callable[[], str] = _salt,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._now = now
        self._salt = salt
        self._http = httpx.AsyncClient(base_url=base_url, transport=transport, timeout=timeout)
        self._mfa_transactions: dict[str, str] = {}     # 발신번호 → 인증 거래 ID (요청과 확인 사이에만 든다)

    # --- 인증 -----------------------------------------------------------------------------------

    def _authorization(self) -> str:
        date = self._now().isoformat()
        salt = self._salt()
        signature = hmac.new(self._api_secret.encode(), (date + salt).encode(), hashlib.sha256).hexdigest()
        return f"HMAC-SHA256 apiKey={self._api_key}, date={date}, salt={salt}, signature={signature}"

    async def _call(self, method: str, path: str, *, json_body: dict | None = None, params: dict | None = None,
                    headers: dict[str, str] | None = None, token_errors: bool = False) -> dict:
        """호출하고 JSON 을 돌려준다. 실패는 GatewayError 로, token_errors 면 4xx 를 TokenInvalidError 로 바꾼다."""
        request_headers = {"Authorization": self._authorization(), **(headers or {})}
        try:
            response = await self._http.request(method, path, json=json_body, params=params, headers=request_headers)
        except httpx.TimeoutException as exc:
            raise GatewayTransientError("NETWORK", "업체 응답 시간 초과") from exc
        except httpx.TransportError as exc:
            raise GatewayTransientError("NETWORK", "업체에 연결할 수 없습니다.") from exc
        status = response.status_code
        if status == 429 or status >= 500:
            raise GatewayTransientError(str(status))
        if status >= 400:
            code = _error_code(response) or str(status)
            if token_errors and status != 401:
                raise TokenInvalidError(f"업체가 토큰을 거절했습니다 ({code}).")
            raise GatewayPermanentError(code)
        return response.json() if response.content else {}

    # --- 온보딩 ---------------------------------------------------------------------------------

    async def request_channel_token(self, search_id: str, admin_phone: str, category_code: str) -> None:
        await self._call("POST", "/kakao/v2/channels/token", json_body={"searchId": search_id, "phoneNumber": admin_phone})

    async def link_channel(self, search_id: str, admin_phone: str, category_code: str, token: str) -> str:
        body = {"searchId": search_id, "phoneNumber": admin_phone, "categoryCode": category_code, "token": token}
        created = await self._call("POST", "/kakao/v2/channels", json_body=body, token_errors=True)
        return created["channelId"]

    async def register_template(self, provider_channel_id: str, template: TemplateText, text_version: int) -> str:
        body: dict = {
            "channelId": provider_channel_id,
            "name": f"차곡노트 {template.kind} v{text_version}",
            "content": template.body,
            "categoryCode": TEMPLATE_CATEGORY_CODE,
            "messageType": "BA",
            "emphasizeType": "NONE",
            "securityFlag": False,
        }
        if template.button_label is not None:
            link = f"#{{{URL_VARIABLE}}}"
            body["buttons"] = [{"buttonType": "WL", "buttonName": template.button_label, "linkMo": link, "linkPc": link}]
        created = await self._call("POST", "/kakao/v2/templates", json_body=body)
        template_id = created["templateId"]
        await self._call("PUT", f"/kakao/v2/templates/{template_id}/inspection", json_body={})
        return template_id

    async def template_state(self, provider_template_id: str) -> TemplateState:
        found = await self._call("GET", f"/kakao/v2/templates/{provider_template_id}")
        status = _TEMPLATE_STATUS[found["status"]]
        reason = None
        if status == "rejected":
            admin_comments = [c.get("content") for c in found.get("comments") or [] if c.get("isAdmin")]
            reason = admin_comments[-1] if admin_comments else "반려됨"
        return TemplateState(status=status, rejected_reason=reason)

    async def request_sender_verification(self, phone: str) -> None:
        await self._call("POST", "/senderid/v1/numbers", json_body={"phoneNumber": phone}, token_errors=True)
        mfa = {"authType": "ARS", "extras": {"phoneNumber": phone}}
        started = await self._call("PUT", f"/senderid/v1/numbers/{phone}/authenticate",
                                   headers={"x-mfa-data": json.dumps(mfa)}, token_errors=True)
        transaction_id = (started.get("mfa") or {}).get("transactionId")
        if transaction_id:
            self._mfa_transactions[phone] = transaction_id

    async def confirm_sender_verification(self, phone: str, code: str) -> None:
        mfa: dict = {"authType": "ARS", "extras": {"phoneNumber": phone}}
        if phone in self._mfa_transactions:
            mfa["transactionId"] = self._mfa_transactions[phone]
        mfa["token"] = code
        await self._call("PUT", f"/senderid/v1/numbers/{phone}/authenticate",
                         headers={"x-mfa-data": json.dumps(mfa)}, token_errors=True)
        self._mfa_transactions.pop(phone, None)

    # --- 발송·상태·잔액 -------------------------------------------------------------------------

    async def send(self, message: OutgoingMessage) -> Accepted:
        variables = {f"#{{{name}}}": value for name, value in message.variables.items()}
        if message.button_url is not None:
            variables[f"#{{{URL_VARIABLE}}}"] = message.button_url
        kakao: dict = {
            "pfId": message.provider_channel_id,
            "templateId": message.provider_template_id,
            "variables": variables,
            "disableSms": message.fallback is None,
        }
        item: dict = {"to": message.to, "type": "ATA", "kakaoOptions": kakao}
        if message.fallback is not None:
            item["from"] = message.fallback.from_number
            item["text"] = message.fallback.text
        result = await self._call("POST", "/messages/v4/send-many/detail",
                                  json_body={"messages": [item], "showMessageList": True})
        failed = result.get("failedMessageList") or []
        if failed:
            code = str(failed[0].get("statusCode") or "")
            if _DELIVERY.get(code, _TRANSIENT)[2] == "transient":
                raise GatewayTransientError(code)
            raise GatewayPermanentError(code)
        return Accepted(provider_message_id=result["messageList"][0]["messageId"])

    async def delivery_state(self, provider_message_id: str) -> DeliveryState:
        listed = await self._call("GET", "/messages/v4/list", params={"messageId": provider_message_id})
        found = (listed.get("messageList") or {}).get(provider_message_id)
        if found is None:
            return DeliveryState(status="pending", channel_used=None, error_code=None, error_kind=None)
        code = str(found.get("statusCode") or "")
        status, channel_used, error_kind = _DELIVERY.get(code, _TRANSIENT)
        if status == "sent":
            message_type = str(found.get("type") or "")
            channel_used = _CHANNEL_BY_TYPE.get(message_type, message_type.lower())
        return DeliveryState(status=status, channel_used=channel_used,
                             error_code=code if status == "failed" else None, error_kind=error_kind)

    async def balance(self) -> int:
        found = await self._call("GET", "/cash/v1/balance")
        return int((found.get("balance") or 0) + (found.get("point") or 0))


def _error_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    code = body.get("errorCode") if isinstance(body, dict) else None
    return str(code) if code else None
```

`backend/apps/notification/adapter/outbound/strategy/fake_gateway.py`:

```python
"""dev 와 흐름 테스트용 가짜 게이트웨이 — 외부를 부르지 않고 결정적으로 동작한다.

토큰·인증번호는 000000 만 통과한다. 발송은 늘 접수되고 결과는 번호 끝 네 자리로 가른다 — 0000 영구 실패,
9999 일시 실패, 8888 두 번 대기 뒤 성공, 그 밖은 성공. 끝이 0000 인데 대체 문자가 있으면 문자로 간 것으로 친다.
"""
from __future__ import annotations

from notification.app.ports.output.message_gateway_port import (
    Accepted,
    DeliveryState,
    MessageGatewayPort,
    OutgoingMessage,
    TemplateState,
)
from notification.domain.errors import TokenInvalidError
from notification.domain.services.templates import TemplateText
from notification.domain.value_objects.message_kind import NEXT_VISIT

FAKE_TOKEN = "000000"
PERMANENT_CODE, TRANSIENT_CODE = "3104", "3040"     # 카카오톡 미사용자, 전송시간 초과


class FakeGateway(MessageGatewayPort):
    def __init__(self, *, reject_next_visit: bool = False, balance: int = 100000) -> None:
        self._reject_next_visit = reject_next_visit
        self._balance = balance
        self.sent_messages: list[OutgoingMessage] = []
        self.calls: list[tuple] = []
        self._polls: dict[str, int] = {}

    async def request_channel_token(self, search_id: str, admin_phone: str, category_code: str) -> None:
        self.calls.append(("request_channel_token", search_id, admin_phone, category_code))

    async def link_channel(self, search_id: str, admin_phone: str, category_code: str, token: str) -> str:
        self.calls.append(("link_channel", search_id, admin_phone, category_code))
        if token != FAKE_TOKEN:
            raise TokenInvalidError("토큰이 틀렸거나 만료되었습니다.")
        return f"pf-{search_id}"

    async def register_template(self, provider_channel_id: str, template: TemplateText, text_version: int) -> str:
        self.calls.append(("register_template", provider_channel_id, template.kind, text_version))
        return f"tpl-{provider_channel_id}-{template.kind}-v{text_version}"

    async def template_state(self, provider_template_id: str) -> TemplateState:
        self.calls.append(("template_state", provider_template_id))
        if self._reject_next_visit and f"-{NEXT_VISIT}-" in provider_template_id:
            return TemplateState(status="rejected", rejected_reason="가짜 반려")
        return TemplateState(status="approved", rejected_reason=None)

    async def request_sender_verification(self, phone: str) -> None:
        self.calls.append(("request_sender_verification", phone))

    async def confirm_sender_verification(self, phone: str, code: str) -> None:
        self.calls.append(("confirm_sender_verification", phone))
        if code != FAKE_TOKEN:
            raise TokenInvalidError("인증번호가 틀렸거나 만료되었습니다.")

    async def send(self, message: OutgoingMessage) -> Accepted:
        self.sent_messages.append(message)
        self.calls.append(("send", message.to, message.provider_template_id))
        return Accepted(provider_message_id=f"fake-{len(self.sent_messages)}")

    async def delivery_state(self, provider_message_id: str) -> DeliveryState:
        self.calls.append(("delivery_state", provider_message_id))
        message = self.sent_messages[int(provider_message_id.removeprefix("fake-")) - 1]
        tail = message.to[-4:]
        if tail == "0000":
            if message.fallback is not None:
                return DeliveryState(status="sent", channel_used=message.fallback.channel, error_code=None,
                                     error_kind=None)
            return DeliveryState(status="failed", channel_used=None, error_code=PERMANENT_CODE, error_kind="permanent")
        if tail == "9999":
            return DeliveryState(status="failed", channel_used=None, error_code=TRANSIENT_CODE, error_kind="transient")
        if tail == "8888":
            self._polls[provider_message_id] = self._polls.get(provider_message_id, 0) + 1
            if self._polls[provider_message_id] <= 2:
                return DeliveryState(status="pending", channel_used=None, error_code=None, error_kind=None)
        return DeliveryState(status="sent", channel_used="alimtalk", error_code=None, error_kind=None)

    async def balance(self) -> int:
        self.calls.append(("balance",))
        return self._balance
```

`backend/apps/notification/dependencies/notification_wiring.py`:

```diff
@@ -3,11 +3,15 @@ from __future__ import annotations
 
 from sqlalchemy.ext.asyncio import AsyncSession
 
+from core.config import APP_ENV, SOLAPI_API_KEY, SOLAPI_API_SECRET
 from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
 from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
 from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
 from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
+from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
+from notification.adapter.outbound.strategy.solapi_gateway import SolapiGateway
 from notification.app.ports.output.channel_repository import ChannelRepository
+from notification.app.ports.output.message_gateway_port import MessageGatewayPort
 from notification.app.ports.output.settings_repository import SettingsRepository
 from notification.app.ports.output.template_repository import TemplateRepository
 
@@ -27,3 +31,29 @@ def build_template_repository(db: AsyncSession) -> TemplateRepository:
 def build_message_repository(db: AsyncSession) -> MessagePgRepository:
     """notification_messages 표의 리포지토리 하나. 매장 범위 포트와 디스패처의 전 매장 포트를 다 구현한다."""
     return MessagePgRepository(db)
+
+
+def build_message_gateway(api_key: str, api_secret: str, app_env: str) -> MessageGatewayPort:
+    """키가 둘 다 있으면 솔라피, 둘 다 비고 dev 면 가짜. 그 밖(하나만 있거나 운영에서 빔)은 기동 실패(설계 6.1)."""
+    if api_key and api_secret:
+        return SolapiGateway(api_key, api_secret)
+    if not api_key and not api_secret and app_env == "dev":
+        return FakeGateway()
+    raise RuntimeError("SOLAPI_API_KEY 와 SOLAPI_API_SECRET 을 둘 다 넣거나(운영) 둘 다 비워야(dev) 합니다.")
+
+
+_gateway: MessageGatewayPort | None = None
+
+
+def get_message_gateway() -> MessageGatewayPort:
+    """프로세스에 하나 — HTTP 클라이언트를 나눠 쓴다. 테스트는 monkeypatch 로 바꾼다."""
+    global _gateway
+    if _gateway is None:
+        _gateway = build_message_gateway(SOLAPI_API_KEY, SOLAPI_API_SECRET, APP_ENV)
+    return _gateway
+
+
+def reset_message_gateway() -> None:
+    """테스트용."""
+    global _gateway
+    _gateway = None
```

`.env.example`:

```diff
@@ -28,3 +28,9 @@ S3_BUCKET=
 REPORT_LINK_KEY_B64=
 REPORT_WEB_BASE_URL=
 REPORT_WEB_SECRET=
+# 알림톡 — 솔라피 API 키(둘 다 비우면 dev 는 가짜 어댑터, 운영은 API 프로세스가 기동하지 않는다),
+# 잔액 경고 기준(원, 기본 30000), 매장별 하루 발송 상한(기본 300)
+SOLAPI_API_KEY=
+SOLAPI_API_SECRET=
+SOLAPI_BALANCE_WARN_KRW=
+NOTIFICATION_DAILY_CAP=
```

`backend/apps/notification/adapter/outbound/strategy/__init__.py`:

```python

```

`backend/core/config.py`:

```diff
@@ -56,3 +56,10 @@ REPORT_LINK_KEY: bytes = _report_link_key()
 REPORT_WEB_BASE_URL: str = (_m.get("REPORT_WEB_BASE_URL", "") or "http://127.0.0.1:3010").rstrip("/")
 # 웹 서버와 나누는 비밀값 — 맞을 때만 웹 서버가 알려 준 접속 주소로 횟수를 센다. 비어 있으면 믿지 않는다.
 REPORT_WEB_SECRET: str = _m.get("REPORT_WEB_SECRET", "") or ""
+
+# 알림톡(⑥). 솔라피 API 키 — 둘 다 비면 dev 에서는 가짜 어댑터, 운영에서는 API 프로세스가 기동하지 않는다.
+SOLAPI_API_KEY: str = _m.get("SOLAPI_API_KEY", "") or ""
+SOLAPI_API_SECRET: str = _m.get("SOLAPI_API_SECRET", "") or ""
+# 잔액이 이 아래로 내려가면 경고 로그. 매장별 하루 발송 상한 — 넘으면 보내지 않고 대기에 둔다(설계 9.4).
+SOLAPI_BALANCE_WARN_KRW: int = int(_m.get("SOLAPI_BALANCE_WARN_KRW", "") or 30000)
+NOTIFICATION_DAILY_CAP: int = int(_m.get("NOTIFICATION_DAILY_CAP", "") or 300)
```

`backend/main.py`:

```diff
@@ -48,6 +48,7 @@ from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
 from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
 from media.dependencies.media_library_provider import get_media_library_use_case
 from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
+from notification.dependencies.notification_wiring import get_message_gateway
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
 from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
@@ -108,6 +109,8 @@ from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
 @asynccontextmanager
 async def lifespan(app: FastAPI):
     init_engine()
+    # 발송 게이트웨이를 기동 때 만든다 — 운영에서 솔라피 키가 비면 첫 발송이 아니라 여기서 멈춘다(설계 6.1).
+    get_message_gateway()
     try:
         yield
     finally:
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 범위 | 명령 | 결과 |
|---|---|---|
| 이 작업 | `pytest apps/notification/tests/adapter/test_solapi_gateway.py apps/notification/tests/adapter/test_fake_gateway.py apps/notification/tests/dependencies tests/test_config_defaults.py` | 44 + 10 + 6 + 1(config) 통과 |
| 단위 전체 | `pytest apps tests -q -m "not integration and not network"` (`--no-deps`) | **1538 passed**, 447 deselected (작업 5 뒤 1476 → +62) |
| 통합 | `pytest tests/integration/test_notification_subscriber_wiring.py -m integration` (앱 기동 → lifespan 의 `get_message_gateway()` 경유) | 6 passed |
| 구조 계약 | `lint-imports --config .importlinter` | **6 kept, 0 broken** |

통합 전체는 돌리지 않았다(이 작업은 main.py 의 lifespan 한 줄 외에 DB 를 건드리지 않는다 — 과제 지시대로 앱 기동 파일 하나만).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 서명을 `date` 만으로(`(date + salt).encode()` → `date.encode()`) → `test_인증_헤더는_HMAC_SHA256_으로_date_와_salt_를_이어_서명한다`
- `kakaoOptions` 에서 `"disableSms": message.fallback is None` 줄 삭제 → `test_대체_문자가_없으면_disableSms_이고_발신번호와_문구가_없다`, `test_대체_문자가_있으면_발신번호와_문구를_싣고_disableSms_가_꺼진다`
- `if status == 429 or status >= 500` → `if status == 429`(5xx 를 permanent 로) → `test_시간_초과_연결_실패_5xx_429_는_일시_오류다[failure2-500]`, `[failure3-503]`
- 변수 키를 `#{}` 없이(`{name: value …}`) → `test_발송은_알림톡_옵션으로_접수하고_변수_키를_업체_형식으로_바꾼다`
- `build_message_gateway` 의 조건에서 `and app_env == "dev"` 삭제(prod 에서 빈 키로 Fake) → `test_운영에서_키가_비면_기동하지_않는다`
- `_call` 의 `GatewayPermanentError(code)` 메시지에 `json_body`(번호 포함)를 넣음 → `test_번호는_예외_메시지와_기록에_남지_않는다`
- `delivery_state` 에서 표에 없는 코드의 기본값을 `_TRANSIENT` → `_PERMANENT` → `test_업체_상태_코드를_대기_성공_실패로_접는다[9999-ATA-expected14]`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 발송 게이트웨이 — 포트, 솔라피(HMAC·접수·상태·온보딩) 어댑터, dev 가짜 어댑터, 설정 키

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 디스패처 — 집고·검사하고·보내고·결과를 적는다, 템플릿 상태와 잔액 주기 확인, 기동 때 도는 루프와 깨우기

**Files:**
- Create: `backend/apps/notification/app/services/system_context.py`
- Create: `backend/apps/notification/app/services/dispatcher.py`
- Create: `backend/apps/notification/app/services/dispatcher_wakeup.py`
- Create: `backend/apps/notification/app/services/message_text.py`
- Create: `backend/apps/notification/dependencies/dispatcher_ports.py`
- Create: `backend/apps/notification/dependencies/dispatcher_provider.py`
- Modify: `backend/apps/notification/adapter/inbound/observer/visit_event_subscriber.py`
- Create: `backend/apps/notification/app/services/__init__.py`
- Create: `backend/apps/notification/tests/app/services/__init__.py`
- Create: `backend/apps/notification/tests/app/services/test_dispatcher.py`
- Create: `backend/apps/notification/tests/app/services/test_dispatcher_wakeup.py`
- Create: `backend/apps/notification/tests/dependencies/test_dispatcher_provider.py`
- Modify: `backend/apps/notification/tests/helpers/fakes.py`
- Modify: `backend/apps/notification/tests/test_fakes_are_ports.py`
- Modify: `backend/core/database.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_notification_dispatcher_wiring.py`
- Create: `backend/tests/test_app_lifespan.py`
- Modify: `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: 작업 3 의 `schedule_rules`(`deferred_for_daytime`·`is_too_late`·`retry_at`)·`templates.render`·`sms_channel`, 작업 4 의 `NotificationQueueRepository`·`MessageRepository`·`SettingsRepository`·`TemplateRepository`, 작업 5 의 `variables` 키, 작업 6 의 `MessageGatewayPort`·`get_message_gateway`; 허브 포트 `ShopProfilePort`·`CustomerDirectoryPort.contact`·`briefs`·`VisitLedgerPort`(앞으로의 예약 유무), `core.database`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# notification.app.services.system_context
def system_context(shop_id: int, timezone: str = "Asia/Seoul") -> ShopContext
    # ShopContext(shop_id, member_id=0, role="system", permissions=frozenset(), timezone). 요청 밖에서 ShopContext 를 만드는 유일한 곳.
    # 시각 계산이 있는 읽기는 ShopProfile.timezone 을 넣는다. 기본값은 status 만 바꾸는 save 에만 쓴다.

# notification.app.services.message_text  — 저장된 variables(T5 의 ISO 문자열 사전)로 문안을 만든다. T9 의 share_text 도 여기서
def message_variables(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> dict[str, str]
    # {"매장명": …, "대상": …, "일시": …} — 이름에 #{} 없음. OutgoingMessage.variables 에 그대로 넘기고(어댑터가 #{} 를 씌운다) render 의 입력
    # 읽는 키: starts_at(필수) · previous_starts_at · url · expires_at("" 이면 None) · completed_at(→ last_visit_at) · interval_weeks(int)
def message_text(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> RenderedMessage
    # render(kind, message_variables(...)) — .text(알림톡 본문) · .sms_text · .button_url

# notification.app.services.dispatcher
logger = logging.getLogger("notification.dispatcher")
TEMPLATE_REFRESH_EVERY = timedelta(minutes=10); BALANCE_CHECK_EVERY = timedelta(hours=24)
PENDING_TEMPLATE_DEFER = timedelta(minutes=10); DAILY_CAP_DEFER = timedelta(hours=1)
POLL_SOON, POLL_LATER, POLL_SOON_WINDOW = 5초, 60초, 1분
@dataclass
class DispatchReport: recovered: int = 0; claimed: int = 0; sent: int = 0; deferred: int = 0; canceled: int = 0; failed: int = 0; polled: int = 0
    # sent = 업체가 접수한 줄, deferred = scheduled 로 되돌린 줄(검수 중·야간·상한·일시 오류 재시도), failed 는 보내기 실패 + 상태 조회의 failed/TIMEOUT
class Dispatcher:
    def __init__(self, *, queue: NotificationQueueRepository, channels: ChannelRepository, settings: SettingsRepository,
                 templates: TemplateRepository, messages: MessageRepository, gateway: MessageGatewayPort,
                 shops: ShopProfilePort, directory: CustomerDirectoryPort, ledger: VisitLedgerPort,
                 commit: Callable[[], Awaitable[None]], now: Callable[[], datetime], daily_cap: int,
                 balance_warn_krw: int, claim_limit: int = 50) -> None
    async def run_once(self) -> DispatchReport      # recover_stuck → commit → claim_due → commit → 줄마다 _process → save → commit → accepted 조회 → 주기 작업
    async def refresh_templates(self) -> int        # 바꾼 수(set_status + upsert). 첫 run_once 와 10분마다
    async def check_balance(self) -> int            # 잔액(원). 첫 run_once 와 24시간마다. 기준 아래면 WARNING(금액만)
    # 내부(테스트가 봄): _gateway · _now · _commit · _daily_cap · _balance_warn_krw

# notification.app.services.dispatcher_wakeup
_event: asyncio.Event          # 처음 wait 한 루프에 묶인다 — 테스트는 monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())
def wake() -> None
async def wait(timeout: float) -> None            # 깨우거나 timeout 뒤 돌아오고 이벤트를 지운다

# notification.dependencies.dispatcher_ports
@dataclass(frozen=True)
class DispatcherPorts:
    shop_profile: Callable[[AsyncSession], ShopProfilePort]
    customer_directory: Callable[[AsyncSession], CustomerDirectoryPort]
    visit_ledger: Callable[[AsyncSession], VisitLedgerPort]
def configure_dispatcher_ports(ports: DispatcherPorts) -> None
def dispatcher_ports() -> DispatcherPorts          # 비어 있으면 RuntimeError("디스패처의 허브 포트 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
# 테스트에서 비우기: monkeypatch.setattr(dispatcher_ports 모듈, "_ports", None)

# notification.dependencies.dispatcher_provider
WAKE_SETTLE_SECONDS = 0.5
def build_dispatcher(db: AsyncSession, *, gateway: MessageGatewayPort | None = None,
                     now: Callable[[], datetime] | None = None) -> Dispatcher
    # 저장소 넷은 notification_wiring 의 build_* 로, 허브 포트는 dispatcher_ports() 의 공장에 db 를 넘겨, commit=db.commit,
    # gateway 기본 get_message_gateway(), now 기본 utc_now, daily_cap=NOTIFICATION_DAILY_CAP, balance_warn_krw=SOLAPI_BALANCE_WARN_KRW
    # 테스트: build_dispatcher(session, gateway=FakeGateway(), now=lambda: fixed).run_once(); 상한은 monkeypatch.setattr(provider, "NOTIFICATION_DAILY_CAP", 1)
async def run_once() -> DispatchReport             # core.database.session_scope() 로 세션 하나 → build_dispatcher(db).run_once()
async def run_forever(stop: asyncio.Event, interval: float = 2.0) -> None
    # stop 까지: wait(interval) → stop 확인 → 0.5초 → stop 확인 → run_once(). 예외는 WARNING(종류만) 뒤 계속
def start_dispatcher() -> tuple[asyncio.Task, asyncio.Event]   # Task 이름 "notification-dispatcher". 끝낼 때 stop.set(); wake(); await task

# core.database
@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]   # _session_factory(없으면 init_engine) 로 세션 하나. 커밋은 부르는 쪽

# main.py
task, stop = start_dispatcher()                    # lifespan — get_message_gateway() 바로 뒤. finally: stop.set(); wake(); await task; dispose…
configure_dispatcher_ports(DispatcherPorts(shop_profile=get_shop_profile_use_case,
                                           customer_directory=get_customer_directory_use_case,
                                           visit_ledger=get_visit_ledger_use_case))   # subscribe(handle_visit_event) 바로 뒤, import 시점

# notification.adapter.inbound.observer.visit_event_subscriber.handle_visit_event — 끝에 wake()

# notification.tests.helpers.fakes (더한 것)
class FakeShopProfile(ShopProfilePort):   __init__(shops: dict[int, ShopProfile] | None = None); shops
class FakeDirectory(CustomerDirectoryPort):
    __init__(shop_id: int = 1); contacts: dict[int, CustomerContact]; pets: dict[int, PetBrief]
    def family(customer_id=1, pet_id=101, name="김민지", phone="01012345678", pet_name="콩이", marketing_consent=True) -> None
    # contact: ctx.shop_id 가 다르면 None, 아니면 contacts.get(). briefs: pets 에서. 나머지 메서드는 빈 값
class FakeLedger(VisitLedgerPort):        upcoming: set[int]   # customer_has_upcoming 만 뜻이 있다
class SpyGateway(FakeGateway):
    __init__(journal: Journal | None = None, **FakeGateway kwargs)
    send_error · state_error · register_error: Exception | None   # 있으면 그 메서드가 던진다
    states: dict[str, DeliveryState]                              # 업체 메시지 ID → 정해 둔 상태(없으면 번호 끝자리 규칙)
    # journal 항목: ("send", template_id) · ("delivery_state", message_id) · ("template_state", template_id) ·
    #   ("register_template", channel_id, kind) · ("balance",)   — 번호는 남기지 않는다
```

보내기 전 검사 순서와 결과(설계 5.3 — 브리프 2절 그대로): `shop_closed` → `channel_unlinked` → `setting_off` → `template_rejected` / pending 이면 +10분 미룸 → `anonymized` → `bad_phone` → (reminder·next_visit) `deferred_for_daytime` 으로 보낼 시각을 정하고 reminder 는 그 시각으로 `too_late` 검사 → 미룬 시각이 뒤면 그 시각으로 미룸 → (next_visit) `no_consent` → `has_upcoming` → `cooldown`(`last > now - cooldown_days`, 정확히 경계면 감) → 하루 상한(`count_sent_since(매장 시간대 오늘 00:00) >= cap` → +1시간 미룸, WARNING) → 변수·문안 → 보내기. 미룸은 `attempts` 를 올리지 않는다. 접수·일시 오류·영구 오류는 모두 `attempts + 1`.

보내는 쪽이다. `Dispatcher.run_once()` 는(시각은 생성자의 `now` 로 한 루프에 한 번 읽는다) ① 5분 넘게 `sending` 인 줄을 회수하고 ② 때가 된 줄을 `claim_due` 로 집어 `sending` 으로 **커밋한 뒤** ③ 줄마다 검사(채널 해제·설정 꺼짐·템플릿 미승인·보호자 익명화·동의 없음·앞으로의 예약 있음·쿨다운·야간 미룸·너무 늦음·하루 상한)를 거쳐 ④ 문안을 조립해 보내고 ⑤ 접수·실패·재시도(`retry_at` 에 올리기 전 `attempts`)·문자 대체를 적고 ⑥ 접수된 줄의 전달 상태를 묻는다. 잠금을 쥔 채 업체를 부르지 않는다. 요청 밖의 `ShopContext` 는 `app/services/system_context.py` 하나(권한 빔). 허브 포트는 `dispatcher_ports.py` 의 세 공장으로 받고 `main.py` 가 tenancy·customer·visit 의 프로바이더를 꽂는다. lifespan 이 `start_dispatcher()` 로 루프(2초, 구독자의 `wake()` 로 바로)를 띄우고 끝낼 때 `stop.set(); wake()` 한다. 템플릿 상태는 첫 루프와 10분마다, 잔액은 첫 루프와 24시간마다(경고는 로그뿐). 문안 조립은 `app/services/message_text.py` — 작업 9 의 공유 문안이 같이 쓴다. 로그는 상태·이유·코드만(`canceled(anonymized)`, `failed(3040)`), 번호·이름·주소·변수는 없다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/app/services/__init__.py`:

```python

```

`backend/apps/notification/tests/app/services/test_dispatcher.py`:

```python
"""디스패처 — 집은 줄을 검사하고(설계 5.3) 보내고 결과를 적는다(스텁). 시각은 모두 kst() 로 만든다.

journal 에 저장소·게이트웨이·commit 호출이 순서대로 남는다 — "집고 → 커밋 → 보내기"(N14)를 그 순서로 본다.
"""
import logging
from dataclasses import replace
from datetime import timedelta

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from notification.app.ports.output.message_gateway_port import (
    DeliveryState,
    FallbackText,
    GatewayPermanentError,
    GatewayTransientError,
)
from notification.app.services.dispatcher import DispatchReport, Dispatcher
from notification.domain.value_objects.channel_status import UNLINKED
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    DEFAULT_KINDS,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
)
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    FAILED,
    FALLBACK_SENT,
    SCHEDULED,
    SENDING,
    SENT,
)
from notification.domain.value_objects.template_status import APPROVED, PENDING, REJECTED
from notification.tests.helpers.builders import TZ, channel, kst, message, settings, template
from notification.tests.helpers.fakes import (
    FakeChannels,
    FakeDirectory,
    FakeLedger,
    FakeMessages,
    FakeSettings,
    FakeShopProfile,
    FakeTemplates,
    Journal,
    SpyGateway,
)

NOW = kst(10, 14, 11)          # 14일(수) 11:00
STARTS = kst(10, 16, 14)       # 16일(금) 14:00
URL = "https://a/" + "t" * 43
SEC, MIN, HOUR, DAY = timedelta(seconds=1), timedelta(minutes=1), timedelta(hours=1), timedelta(days=1)
PHONE, NAME = "01012345678", "김민지"


def _iso(at):
    return at.isoformat()


def _profile(shop_id=1, name="두부네", tz=TZ, open=True):
    return ShopProfile(shop_id=shop_id, name=name, phone=None, address=None, timezone=tz, open=open)


class _World:
    """연동된 매장 1(채널 linked, 설정 next_visit 켜짐, 템플릿 6종 approved)과 고객 1·반려동물 101. 테스트가 필요한 것만 바꾼다."""

    def __init__(self, now=NOW, daily_cap=300, balance=100000, **settings_overrides) -> None:
        self.now = now
        self.journal = Journal()
        self.channels, self.settings = FakeChannels(self.journal), FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.gateway = SpyGateway(self.journal, balance=balance)
        self.shops = FakeShopProfile({1: _profile()})
        self.directory = FakeDirectory()
        self.directory.family()
        self.ledger = FakeLedger()
        self.channels.rows[1] = channel()
        self.settings.rows[1] = settings(**{"next_visit_enabled": True, **settings_overrides})
        for i, kind in enumerate(KINDS, start=1):
            self.templates.rows[(1, kind)] = template(id=i, kind=kind, provider_template_id=f"KA01TP000{i}")
        self.dispatcher = Dispatcher(
            queue=self.messages, channels=self.channels, settings=self.settings, templates=self.templates,
            messages=self.messages, gateway=self.gateway, shops=self.shops, directory=self.directory,
            ledger=self.ledger, commit=self._commit, now=lambda: self.now, daily_cap=daily_cap,
            balance_warn_krw=30000,
        )

    async def _commit(self) -> None:
        self.journal.append(("commit",))

    def queue(self, kind=CONFIRM, scheduled_at=NOW, starts_at=STARTS, **overrides):
        """시각이 된 줄 하나. variables 는 구독자(T5)가 넣는 모양 그대로."""
        variables = {"starts_at": _iso(starts_at)}
        if kind == CHANGE:
            variables["previous_starts_at"] = _iso(kst(10, 15, 14))
        if kind == REPORT:
            variables.update(url=URL, expires_at=_iso(kst(11, 2, 0)))
        if kind == NEXT_VISIT:
            variables.update(completed_at=_iso(kst(9, 16, 14)), interval_weeks="4")
        fields = dict(id=len(self.messages.rows) + 1, kind=kind, scheduled_at=scheduled_at, pet_id=101,
                      variables=variables)
        fields.update(overrides)
        row = message(**fields)
        self.messages.rows[row.id] = row
        return row

    def row(self, message_id=1):
        return self.messages.rows[message_id]

    async def run(self) -> DispatchReport:
        return await self.dispatcher.run_once()

    async def run_at(self, at) -> DispatchReport:
        self.now = at
        return await self.dispatcher.run_once()

    def sent(self):
        return self.gateway.sent_messages


# --- 보내기 ----------------------------------------------------------------------------------------------------

async def test_시각이_된_줄을_집어_보내면_accepted_가_되고_업체_ID_와_다음_확인_시각이_적힌다():
    world = _World()
    world.queue()
    world.queue(kind=REMINDER, scheduled_at=NOW + HOUR)      # 아직 아니다

    report = await world.run()

    assert report == DispatchReport(recovered=0, claimed=1, sent=1, deferred=0, canceled=0, failed=0, polled=0)
    row = world.row()
    assert (row.status, row.provider_message_id, row.attempts, row.next_attempt_at) == (ACCEPTED, "fake-1", 1, NOW + 5 * SEC)
    assert world.row(2).status == SCHEDULED
    [outgoing] = world.sent()
    assert (outgoing.to, outgoing.provider_channel_id, outgoing.provider_template_id) == (PHONE, "KA01PF0001", "KA01TP0001")


async def test_집고_커밋한_뒤에_보내고_결과를_적은_뒤_다시_커밋한다():
    """N14 — 잠금(집기)을 쥔 채 업체를 부르지 않는다. 회수 → 커밋 → 집기 → 커밋 → 보내기 → 저장 → 커밋."""
    world = _World()
    world.queue()

    await world.run()

    names = [entry[0] for entry in world.journal]
    assert names[:7] == ["recover_stuck", "commit", "claim_due", "commit", "send", "save_message", "commit"]


async def test_변수는_반려동물_이름과_매장_시간대의_일시로_채우고_문안_변수_이름_그대로_넘긴다():
    world = _World()
    world.queue()

    await world.run()

    [outgoing] = world.sent()
    assert outgoing.variables == {"매장명": "두부네", "대상": "콩이", "일시": "10월 16일(금) 14:00"}
    assert outgoing.button_url is None


async def test_반려동물이_없거나_이름이_없으면_보호자_이름님이다():
    world = _World()
    world.queue(pet_id=None)
    world.queue(kind=CANCEL, pet_id=999)

    await world.run()

    assert [m.variables["대상"] for m in world.sent()] == [f"{NAME}님", f"{NAME}님"]


async def test_알림장은_주소가_버튼에_가고_다음_예약_제안은_지난일과_간격을_넣는다():
    world = _World()
    world.queue(kind=REPORT)
    world.queue(kind=NEXT_VISIT, id=2)
    world.queue(kind=CHANGE, id=3)

    await world.run()

    report, next_visit, change = world.sent()
    assert report.button_url == URL
    assert report.variables == {"매장명": "두부네", "대상": "콩이", "기간안내": "11월 2일까지 열려요.", "링크": URL}
    assert next_visit.variables == {"매장명": "두부네", "대상": "콩이", "지난일": "9월 16일(수)", "간격": "4"}
    assert change.variables["이전일시"] == "10월 15일(목) 14:00"


async def test_문자_대체는_발신번호_인증까지_마친_매장만_붙인다():
    world = _World()
    world.queue()
    await world.run()
    assert world.sent()[0].fallback is None

    world.channels.rows[1] = channel(sender_number="01099990000", sender_number_verified_at=NOW,
                                     sms_fallback_enabled=True)
    world.queue(id=2)
    await world.run()
    assert world.sent()[1].fallback == FallbackText(
        from_number="01099990000", text="[두부네] 10월 16일(금) 14:00 예약이 접수되었어요.", channel="sms")


# --- 보내기 전 검사(설계 5.3) ---------------------------------------------------------------------------------------

async def test_매장이_없거나_열려_있지_않으면_shop_closed():
    world = _World()
    world.shops.shops[1] = _profile(open=False)
    world.queue()
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "shop_closed")

    del world.shops.shops[1]
    world.queue(id=2)
    await world.run()
    assert world.row(2).canceled_reason == "shop_closed"
    assert world.sent() == []


@pytest.mark.parametrize("break_world, reason", [
    (lambda w: w.channels.rows.pop(1), "channel_unlinked"),
    (lambda w: w.channels.rows.__setitem__(1, channel(status=UNLINKED, unlinked_at=NOW)), "channel_unlinked"),
    (lambda w: w.settings.rows.pop(1), "setting_off"),
    (lambda w: w.settings.rows.__setitem__(1, settings(confirm_enabled=False)), "setting_off"),
    (lambda w: w.templates.rows.pop((1, CONFIRM)), "template_rejected"),
    (lambda w: w.templates.rows.__setitem__((1, CONFIRM), template(status=REJECTED, rejected_reason="x")),
     "template_rejected"),
    (lambda w: w.directory.contacts.pop(1), "anonymized"),
    (lambda w: w.directory.family(phone="0212345678"), "bad_phone"),
], ids=["채널 없음", "채널 끊김", "설정 없음", "설정 꺼짐", "템플릿 없음", "템플릿 반려", "익명화", "휴대폰 번호 아님"])
async def test_보내기_전_검사에_걸리면_이유를_적고_취소한다(break_world, reason):
    world = _World()
    break_world(world)
    world.queue()

    report = await world.run()

    assert (world.row().status, world.row().canceled_reason, world.row().attempts) == (CANCELED, reason, 0)
    assert report.canceled == 1 and world.sent() == []


async def test_템플릿이_검수_중이면_10분_뒤로_미룬다():
    world = _World()
    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)
    world.queue()

    report = await world.run()

    row = world.row()
    assert (row.status, row.scheduled_at, row.attempts, row.canceled_reason) == (SCHEDULED, NOW + 10 * MIN, 0, None)
    assert report.deferred == 1 and world.sent() == []


@pytest.mark.parametrize("now, deferred_to", [
    (kst(10, 15, 22), kst(10, 16, 8)),       # 밤 10시 → 다음 날 아침 8시
    (kst(10, 16, 6), kst(10, 16, 8)),        # 새벽 6시 → 같은 날 아침 8시
], ids=["22시", "06시"])
async def test_리마인드와_다음_예약_제안은_매장_시간대의_밤이면_아침_8시로_미룬다(now, deferred_to):
    world = _World(now=now)
    world.queue(kind=REMINDER, scheduled_at=now - HOUR)
    world.queue(kind=NEXT_VISIT, scheduled_at=now - HOUR, id=2)

    await world.run()

    for row in (world.row(), world.row(2)):
        assert (row.status, row.scheduled_at, row.attempts) == (SCHEDULED, deferred_to, 0)
    assert world.sent() == []


async def test_즉시_보내는_종류는_밤에도_바로_간다():
    world = _World(now=kst(10, 15, 22))
    world.queue(kind=CONFIRM, scheduled_at=kst(10, 15, 22))
    await world.run()
    assert world.row().status == ACCEPTED


@pytest.mark.parametrize("now, starts_at", [
    (kst(10, 15, 22), kst(10, 16, 8, 30)),   # 미룬 아침 8시가 예약 1시간 전(7:30)을 넘긴다
    (kst(10, 16, 13, 30), kst(10, 16, 14)),  # 지금이 이미 1시간 전을 넘겼다
], ids=["미룬 시각이 늦다", "지금이 늦다"])
async def test_리마인드는_보낼_시각이_예약_1시간_전을_넘기면_too_late(now, starts_at):
    world = _World(now=now)
    world.queue(kind=REMINDER, scheduled_at=now - HOUR, starts_at=starts_at)

    await world.run()

    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "too_late")


async def test_정확히_1시간_전이면_리마인드가_간다():
    world = _World(now=kst(10, 16, 13))
    world.queue(kind=REMINDER, scheduled_at=kst(10, 16, 13), starts_at=kst(10, 16, 14))
    await world.run()
    assert world.row().status == ACCEPTED


async def test_다음_예약_제안은_마케팅_동의가_없으면_no_consent():
    world = _World()
    world.directory.family(marketing_consent=False)
    world.queue(kind=NEXT_VISIT)
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "no_consent")


async def test_다음_예약_제안은_앞으로의_예약이_있으면_has_upcoming():
    world = _World()
    world.ledger.upcoming.add(1)
    world.queue(kind=NEXT_VISIT)
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "has_upcoming")


async def test_다음_예약_제안은_쿨다운_안에_같은_종류를_받았으면_cooldown_이고_정확히_30일이면_간다():
    world = _World()
    world.queue(kind=NEXT_VISIT)
    world.queue(kind=NEXT_VISIT, id=10, status=SENT, sent_at=NOW - 30 * DAY + SEC, visit_id=90)
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "cooldown")

    world.messages.rows[10] = replace(world.row(10), sent_at=NOW - 30 * DAY)
    world.queue(kind=NEXT_VISIT, id=2, visit_id=2)
    await world.run()
    assert world.row(2).status == ACCEPTED


async def test_동의_없음이_앞으로의_예약_검사보다_먼저다():
    world = _World()
    world.directory.family(marketing_consent=False)
    world.ledger.upcoming.add(1)
    world.queue(kind=NEXT_VISIT)
    await world.run()
    assert world.row().canceled_reason == "no_consent"


async def test_매장의_오늘_발송이_하루_상한에_닿으면_1시간_뒤로_미루고_경고만_남긴다(caplog):
    world = _World(daily_cap=2)
    world.queue()
    for i in (10, 11):      # 오늘(매장 시간대) 업체에 넘긴 둘
        world.queue(id=i, visit_id=i, status=SENT, provider_message_id=f"old-{i}", created_at=kst(10, 14, 0, 30))
    world.queue(id=12, visit_id=12, status=SENT, provider_message_id="old-12", created_at=kst(10, 13, 23, 30))   # 어제

    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        report = await world.run()

    row = world.row()
    assert (row.status, row.scheduled_at, row.attempts) == (SCHEDULED, NOW + HOUR, 0)
    assert report.deferred == 1 and world.sent() == []
    [record] = caplog.records
    assert record.levelno == logging.WARNING and "2" in record.getMessage()
    assert PHONE not in caplog.text and NAME not in caplog.text


async def test_하루_상한_아래면_보낸다():
    world = _World(daily_cap=2)
    world.queue()
    world.queue(id=10, visit_id=10, status=SENT, provider_message_id="old-10", created_at=kst(10, 14, 0, 30))
    await world.run()
    assert world.row().status == ACCEPTED


# --- 보내기 실패 ------------------------------------------------------------------------------------------------

async def test_일시_오류는_1분_5분_30분_뒤로_미루고_네_번째_실패에서_failed_다():
    world = _World()
    world.gateway.send_error = GatewayTransientError("3040")
    world.queue()

    await world.run()
    assert (world.row().status, world.row().scheduled_at, world.row().attempts, world.row().error_code) == (
        SCHEDULED, NOW + MIN, 1, "3040")
    await world.run_at(NOW + MIN)
    assert (world.row().status, world.row().scheduled_at, world.row().attempts) == (SCHEDULED, NOW + 6 * MIN, 2)
    await world.run_at(NOW + 6 * MIN)
    assert (world.row().status, world.row().scheduled_at, world.row().attempts) == (SCHEDULED, NOW + 36 * MIN, 3)
    report = await world.run_at(NOW + 36 * MIN)
    assert (world.row().status, world.row().attempts, world.row().error_kind, world.row().error_code) == (
        FAILED, 4, "transient", "3040")
    assert report.failed == 1 and len([e for e in world.journal if e[0] == "send"]) == 4


async def test_영구_오류는_바로_failed_다():
    world = _World()
    world.gateway.send_error = GatewayPermanentError("1062")
    world.queue()

    report = await world.run()

    row = world.row()
    assert (row.status, row.error_kind, row.error_code, row.attempts) == (FAILED, "permanent", "1062", 1)
    assert report.failed == 1


async def test_한_줄의_예외는_그_줄만_일시_실패로_적고_다음_줄을_막지_않는다(monkeypatch, caplog):
    world = _World()
    world.queue()
    world.queue(id=2, visit_id=2)
    original = world.directory.contact

    async def contact(ctx, customer_id):
        if world.row().status == SENDING and not world.sent():
            raise RuntimeError("포트가 죽었다")
        return await original(ctx, customer_id)

    monkeypatch.setattr(world.directory, "contact", contact)

    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        report = await world.run()

    first, second = world.row(), world.row(2)
    assert (first.status, first.scheduled_at, first.attempts, first.error_kind, first.error_code) == (
        SCHEDULED, NOW + MIN, 1, "transient", "RuntimeError")
    assert second.status == ACCEPTED
    assert (report.deferred, report.sent) == (1, 1)
    [record] = caplog.records
    assert "RuntimeError" in record.getMessage() and "1" in record.getMessage() and CONFIRM in record.getMessage()
    assert "포트가 죽었다" not in caplog.text


# --- 접수 뒤 상태 조회 ------------------------------------------------------------------------------------------

async def test_접수된_줄은_다음_확인_시각이_지나면_조회해_sent_와_나간_길과_보낸_시각을_적는다():
    world = _World()
    world.queue()
    await world.run()

    report = await world.run_at(NOW + 5 * SEC)

    row = world.row()
    assert (row.status, row.channel_used, row.sent_at) == (SENT, "alimtalk", NOW + 5 * SEC)
    assert report == DispatchReport(polled=1)


async def test_문자로_대체되어_나갔으면_fallback_sent_다():
    world = _World()
    world.directory.family(phone="01012340000")
    world.channels.rows[1] = channel(sender_number="01099990000", sender_number_verified_at=NOW,
                                     sms_fallback_enabled=True)
    world.queue()
    await world.run()

    await world.run_at(NOW + 5 * SEC)

    assert (world.row().status, world.row().channel_used) == (FALLBACK_SENT, "sms")


async def test_업체가_실패로_답하면_failed_와_업체의_분류를_적는다():
    world = _World()
    world.directory.family(phone="01012349999")
    world.queue()
    await world.run()

    report = await world.run_at(NOW + 5 * SEC)

    row = world.row()
    assert (row.status, row.error_code, row.error_kind) == (FAILED, "3040", "transient")
    assert (report.polled, report.failed) == (1, 1)


async def test_아직_대기면_처음_1분은_5초마다_그_뒤는_1분마다_다시_묻는다():
    world = _World()
    world.directory.family(phone="01012348888")      # 두 번 대기 뒤 성공
    world.queue()
    await world.run()

    await world.run_at(NOW + 5 * SEC)
    assert (world.row().status, world.row().next_attempt_at) == (ACCEPTED, NOW + 10 * SEC)
    await world.run_at(NOW + 2 * MIN)
    assert (world.row().status, world.row().next_attempt_at) == (ACCEPTED, NOW + 3 * MIN)
    await world.run_at(NOW + 3 * MIN)
    assert world.row().status == SENT


async def test_다음_확인_시각이_아직이면_묻지_않는다():
    world = _World()
    world.queue()
    await world.run()
    await world.run_at(NOW + 4 * SEC)
    assert world.row().status == ACCEPTED and [e for e in world.journal if e[0] == "delivery_state"] == []


async def test_접수_뒤_24시간_안에_최종_상태가_없으면_일시_실패다():
    world = _World()
    world.queue(status=ACCEPTED, scheduled_at=NOW - 25 * HOUR, next_attempt_at=NOW - MIN, provider_message_id="late")
    world.gateway.states["late"] = DeliveryState(status="pending", channel_used=None, error_code=None, error_kind=None)

    await world.run()

    row = world.row()
    assert (row.status, row.error_kind, row.error_code) == (FAILED, "transient", "TIMEOUT")


async def test_상태_조회가_실패하면_1분_뒤에_다시_묻는다():
    world = _World()
    world.queue()
    await world.run()
    world.gateway.state_error = GatewayTransientError("504")

    await world.run_at(NOW + 5 * SEC)

    assert (world.row().status, world.row().next_attempt_at) == (ACCEPTED, NOW + 65 * SEC)


# --- 회수·주기 작업 ----------------------------------------------------------------------------------------------

async def test_5분_넘게_sending_인_줄은_되돌리고_시도를_세고_같은_루프에서_다시_보낸다():
    world = _World()
    world.queue(status=SENDING)
    world.messages.claimed_at[1] = NOW - 6 * MIN
    world.queue(id=2, visit_id=2, status=SENDING)
    world.messages.claimed_at[2] = NOW - 4 * MIN

    report = await world.run()

    assert (report.recovered, report.claimed, report.sent) == (1, 1, 1)
    assert (world.row().status, world.row().attempts) == (ACCEPTED, 2)
    assert world.row(2).status == SENDING


async def test_템플릿_상태와_잔액은_첫_루프와_10분_24시간_뒤에만_다시_본다():
    world = _World()
    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)

    await world.run()
    await world.run_at(NOW + 9 * MIN)
    assert [e for e in world.journal if e[0] in ("template_state", "balance")] == [("template_state", "KA01TP0001"), ("balance",)]
    assert world.templates.rows[(1, CONFIRM)].status == APPROVED

    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)
    await world.run_at(NOW + 10 * MIN)
    await world.run_at(NOW + 24 * HOUR)
    assert [e for e in world.journal if e[0] in ("template_state", "balance")] == [
        ("template_state", "KA01TP0001"), ("balance",), ("template_state", "KA01TP0001"), ("balance",)]


async def test_검수_중인_템플릿은_업체_상태대로_approved_나_rejected_가_된다():
    world = _World()
    world.gateway = SpyGateway(world.journal, reject_next_visit=True)
    world.dispatcher._gateway = world.gateway
    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)
    world.templates.rows[(1, NEXT_VISIT)] = template(id=6, kind=NEXT_VISIT, status=PENDING, decided_at=None,
                                                     provider_template_id="tpl-KA01PF0001-next_visit-v1")

    changed = await world.dispatcher.refresh_templates()

    confirm, next_visit = world.templates.rows[(1, CONFIRM)], world.templates.rows[(1, NEXT_VISIT)]
    assert (confirm.status, confirm.decided_at) == (APPROVED, NOW)
    assert (next_visit.status, next_visit.rejected_reason, next_visit.decided_at) == (REJECTED, "가짜 반려", NOW)
    assert changed == 2


async def test_연동한_매장의_빠진_종류를_다시_등록하고_다음_예약_제안은_켜진_매장만():
    world = _World(next_visit_enabled=False)
    for kind in KINDS[1:]:
        del world.templates.rows[(1, kind)]                 # 매장 1 은 confirm 만 남았다
    world.shops.shops[2] = _profile(shop_id=2)
    world.channels.rows[2] = channel(shop_id=2, provider_channel_id="KA01PF0002")
    world.settings.rows[2] = settings(next_visit_enabled=True)
    world.shops.shops[3] = _profile(shop_id=3)
    world.channels.rows[3] = channel(shop_id=3, status=UNLINKED, unlinked_at=NOW)   # 끊긴 매장은 건너뛴다
    world.channels.rows[4] = channel(shop_id=4)                                      # 프로필이 없는 매장도

    changed = await world.dispatcher.refresh_templates()

    assert [(e[1], e[2]) for e in world.journal if e[0] == "register_template"] == (
        [("KA01PF0001", kind) for kind in DEFAULT_KINDS[1:]] + [("KA01PF0002", kind) for kind in KINDS])
    registered = world.templates.rows[(1, REMINDER)]
    assert (registered.status, registered.provider_template_id, registered.requested_at) == (
        PENDING, "tpl-KA01PF0001-reminder-v1", NOW)
    assert (1, NEXT_VISIT) not in world.templates.rows and (2, NEXT_VISIT) in world.templates.rows
    assert changed == 4 + 6


async def test_템플릿_등록이_실패하면_그_종류만_건너뛰고_다음_주기에_다시_한다(caplog):
    world = _World()
    del world.templates.rows[(1, REMINDER)]
    world.gateway.register_error = GatewayTransientError("503")

    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        changed = await world.dispatcher.refresh_templates()

    assert changed == 0 and (1, REMINDER) not in world.templates.rows
    assert len(caplog.records) == 1


async def test_잔액이_기준_아래면_금액만_경고한다(caplog):
    world = _World(balance=1000)
    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        assert await world.dispatcher.check_balance() == 1000
    [record] = caplog.records
    assert record.levelno == logging.WARNING and "1000" in record.getMessage() and "30000" in record.getMessage()

    caplog.clear()
    world = _World(balance=30000)
    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        await world.dispatcher.check_balance()
    assert caplog.records == []


# --- 로그 -----------------------------------------------------------------------------------------------------

async def test_로그에는_메시지_ID_매장_종류_결과만_있고_번호_이름_주소는_없다(caplog):
    world = _World()
    world.queue(kind=REPORT)
    world.queue(id=2, visit_id=2)
    world.directory.contacts.pop(1)
    world.directory.family(customer_id=1, phone="01012349999")
    world.queue(id=3, visit_id=3, customer_id=2)        # 익명화된 고객

    with caplog.at_level(logging.INFO, logger="notification.dispatcher"):
        await world.run()
        await world.run_at(NOW + 5 * SEC)

    assert any("report" in r.getMessage() and "accepted" in r.getMessage() for r in caplog.records)
    assert any("canceled(anonymized)" in r.getMessage() for r in caplog.records)
    assert any("failed(3040)" in r.getMessage() for r in caplog.records)
    for secret in (PHONE, "01012349999", NAME, URL, "t" * 43, "콩이"):
        assert secret not in caplog.text
```

`backend/apps/notification/tests/app/services/test_dispatcher_wakeup.py`:

```python
"""깨우기 — 같은 프로세스에서 줄이 생기면 루프가 기다림을 끊고 바로 돈다(설계 5.3-1)."""
import asyncio
import time

import pytest

from notification.app.services import dispatcher_wakeup


@pytest.fixture(autouse=True)
def fresh_event(monkeypatch):
    """asyncio.Event 는 처음 기다린 루프에 묶인다 — 테스트마다 루프가 새로 생기니 이벤트도 새로 둔다."""
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())


async def test_깨우면_기다림이_바로_끝나고_이벤트는_지워진다():
    dispatcher_wakeup.wake()
    started = time.monotonic()
    await dispatcher_wakeup.wait(5.0)
    assert time.monotonic() - started < 1.0
    assert not dispatcher_wakeup._event.is_set()


async def test_깨우지_않으면_시간이_지나야_끝난다():
    started = time.monotonic()
    await dispatcher_wakeup.wait(0.2)
    assert time.monotonic() - started >= 0.2


async def test_기다리는_중에_깨우면_그때_끝난다():
    waiter = asyncio.create_task(dispatcher_wakeup.wait(5.0))
    await asyncio.sleep(0.05)
    assert not waiter.done()
    dispatcher_wakeup.wake()
    await asyncio.wait_for(waiter, 1.0)
```

`backend/apps/notification/tests/dependencies/test_dispatcher_provider.py`:

```python
"""디스패처 조립과 루프 — 허브 포트 공장 자리, build_dispatcher 의 게이트웨이·시계 주입, run_forever 의 깨우기·정지·예외."""
import asyncio
import logging

import pytest

from notification.app.services import dispatcher_wakeup
from notification.app.services.dispatcher import DispatchReport, Dispatcher
from notification.dependencies import dispatcher_ports as ports_module
from notification.dependencies import dispatcher_provider as provider
from notification.dependencies.dispatcher_ports import DispatcherPorts, configure_dispatcher_ports, dispatcher_ports
from notification.tests.helpers.builders import kst
from notification.tests.helpers.fakes import FakeDirectory, FakeLedger, FakeShopProfile, SpyGateway

NOW = kst(10, 14, 11)


@pytest.fixture(autouse=True)
def fresh_event(monkeypatch):
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())


@pytest.fixture
def stub_ports(monkeypatch):
    """main.py 가 꽂은 실제 프로바이더 대신 스텁 공장 — 세션 없이 조립만 본다."""
    monkeypatch.setattr(ports_module, "_ports", None)
    ports = DispatcherPorts(shop_profile=lambda db: FakeShopProfile(), customer_directory=lambda db: FakeDirectory(),
                            visit_ledger=lambda db: FakeLedger())
    configure_dispatcher_ports(ports)
    return ports


def test_허브_포트_자리가_비어_있으면_RuntimeError(monkeypatch):
    monkeypatch.setattr(ports_module, "_ports", None)
    with pytest.raises(RuntimeError, match="진입점에서 조립"):
        dispatcher_ports()


def test_꽂은_공장을_돌려준다(stub_ports):
    assert dispatcher_ports() is stub_ports


class _Session:
    """저장소가 세션을 들고만 있으니 commit 만 있으면 된다."""

    async def commit(self) -> None:
        return None


def test_build_dispatcher_는_넘긴_게이트웨이와_시계를_쓰고_저장소는_세션으로_만든다(stub_ports):
    gateway, session = SpyGateway(), _Session()
    dispatcher = provider.build_dispatcher(session, gateway=gateway, now=lambda: NOW)
    assert isinstance(dispatcher, Dispatcher)
    assert dispatcher._gateway is gateway and dispatcher._now() == NOW
    assert dispatcher._commit == session.commit
    assert (dispatcher._daily_cap, dispatcher._balance_warn_krw) == (provider.NOTIFICATION_DAILY_CAP,
                                                                     provider.SOLAPI_BALANCE_WARN_KRW)


def test_build_dispatcher_는_기본으로_프로세스의_게이트웨이를_쓴다(stub_ports, monkeypatch):
    gateway = SpyGateway()
    monkeypatch.setattr(provider, "get_message_gateway", lambda: gateway)
    assert provider.build_dispatcher(_Session())._gateway is gateway


async def test_루프는_깨우면_반_초_뒤에_한_번_돌고_정지하면_끝난다(monkeypatch):
    runs: list[float] = []
    loop = asyncio.get_running_loop()

    async def run_once() -> DispatchReport:
        runs.append(loop.time())
        return DispatchReport()

    monkeypatch.setattr(provider, "run_once", run_once)
    stop = asyncio.Event()
    task = asyncio.create_task(provider.run_forever(stop, interval=30.0))
    await asyncio.sleep(0.1)
    assert runs == []
    woke = loop.time()
    dispatcher_wakeup.wake()
    await asyncio.sleep(0.8)
    assert len(runs) == 1 and 0.4 <= runs[0] - woke < 0.8

    stop.set()
    dispatcher_wakeup.wake()
    await asyncio.wait_for(task, 1.0)
    assert len(runs) == 1


async def test_루프는_run_once_의_예외를_로그에_남기고_계속_돈다(monkeypatch, caplog):
    calls = 0

    async def run_once() -> DispatchReport:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("DB 가 잠깐 죽었다")
        return DispatchReport()

    monkeypatch.setattr(provider, "run_once", run_once)
    stop = asyncio.Event()
    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        task = asyncio.create_task(provider.run_forever(stop, interval=0.05))
        await asyncio.sleep(1.4)
        stop.set()
        dispatcher_wakeup.wake()
        await asyncio.wait_for(task, 1.0)

    assert calls >= 2
    assert any("RuntimeError" in record.getMessage() for record in caplog.records)


async def test_start_dispatcher_는_이름_있는_작업과_정지_이벤트를_돌려준다(monkeypatch):
    async def run_once() -> DispatchReport:
        return DispatchReport()

    monkeypatch.setattr(provider, "run_once", run_once)
    task, stop = provider.start_dispatcher()
    assert task.get_name() == "notification-dispatcher" and not task.done()
    stop.set()
    dispatcher_wakeup.wake()
    await asyncio.wait_for(task, 1.0)
```

`backend/apps/notification/tests/helpers/fakes.py`:

```diff
@@ -7,8 +7,17 @@ from __future__ import annotations
 
 from dataclasses import replace
 from datetime import datetime
-
+from decimal import Decimal
+
+from hub.app.dtos.customer_contact import CustomerContact
+from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
+from hub.app.dtos.shop_profile import ShopProfile
+from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.shop_profile_port import ShopProfilePort
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
+from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
 from notification.app.ports.output.channel_repository import ChannelRepository
+from notification.app.ports.output.message_gateway_port import DeliveryState
 from notification.app.ports.output.message_repository import MessageRepository
 from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
 from notification.app.ports.output.settings_repository import SettingsRepository
@@ -237,3 +246,124 @@ class FakeMessages(MessageRepository, NotificationQueueRepository):
                             key=lambda t: KINDS.index(t.kind))
             for shop_id in shop_ids
         }
+
+
+# --- 디스패처가 읽는 허브 포트 스텁 --------------------------------------------------------------------------------
+
+class FakeShopProfile(ShopProfilePort):
+    """ShopProfilePort 스텁 — 매장 ID → ShopProfile 사전. 없는 매장은 None."""
+
+    def __init__(self, shops: dict[int, ShopProfile] | None = None) -> None:
+        self.shops = shops if shops is not None else {}
+
+    async def public_profile(self, shop_id):
+        return self.shops.get(shop_id)
+
+
+class FakeDirectory(CustomerDirectoryPort):
+    """CustomerDirectoryPort 스텁 — 디스패처가 쓰는 contact·briefs 만 값을 낸다. 매장이 다르면 없는 것으로 본다.
+
+    contacts 는 {고객 ID: CustomerContact}(익명화를 흉내 내려면 뺀다), pets 는 {반려동물 ID: PetBrief}.
+    """
+
+    def __init__(self, shop_id: int = 1) -> None:
+        self.shop_id = shop_id
+        self.contacts: dict[int, CustomerContact] = {}
+        self.pets: dict[int, PetBrief] = {}
+
+    def family(self, customer_id=1, pet_id=101, name="김민지", phone="01012345678", pet_name="콩이",
+               marketing_consent=True) -> None:
+        self.contacts[customer_id] = CustomerContact(customer_id=customer_id, name=name, phone=phone,
+                                                     marketing_consent=marketing_consent)
+        self.pets[pet_id] = PetBrief(pet_id=pet_id, customer_id=customer_id, name=pet_name, species="dog",
+                                     breed="말티즈", weight_kg=Decimal("3.2"), passed_away=False)
+
+    async def lock_family(self, ctx, customer_id, pet_ids):
+        return None
+
+    async def briefs(self, ctx, customer_ids, pet_ids):
+        if ctx.shop_id != self.shop_id:
+            return FamilyBriefs(customers={}, pets={})
+        customers = {c: CustomerBrief(customer_id=c, name=self.contacts[c].name, phone_masked=None)
+                     for c in customer_ids if c in self.contacts}
+        return FamilyBriefs(customers=customers, pets={p: self.pets[p] for p in pet_ids if p in self.pets})
+
+    async def set_last_visit(self, ctx, customer_id, at):
+        return None
+
+    async def set_pet_weight(self, ctx, pet_id, weight_kg):
+        return None
+
+    async def find_draft_candidates(self, ctx, words):
+        return []
+
+    async def contact(self, ctx, customer_id):
+        return self.contacts.get(customer_id) if ctx.shop_id == self.shop_id else None
+
+
+class FakeLedger(VisitLedgerPort):
+    """VisitLedgerPort 스텁 — 디스패처는 customer_has_upcoming 만 쓴다. upcoming 은 앞으로의 예약이 있는 고객 ID."""
+
+    def __init__(self) -> None:
+        self.upcoming: set[int] = set()
+
+    async def pet_has_visits(self, ctx, pet_id):
+        return False
+
+    async def pet_has_upcoming(self, ctx, pet_id):
+        return False
+
+    async def customer_has_upcoming(self, ctx, customer_id):
+        return customer_id in self.upcoming
+
+    async def no_show_count(self, ctx, customer_id):
+        return 0
+
+    async def upcoming_for_customer(self, ctx, customer_id, limit):
+        return []
+
+    async def clear_customer_memos(self, ctx, customer_id):
+        return None
+
+    async def latest_covers(self, ctx, pet_ids):
+        return {}
+
+
+class SpyGateway(FakeGateway):
+    """FakeGateway 에 journal 과 '던질 예외'·'정해 둔 상태'를 더한 것. journal 에 번호는 남기지 않는다."""
+
+    def __init__(self, journal: Journal | None = None, **kwargs) -> None:
+        super().__init__(**kwargs)
+        self.journal = journal if journal is not None else Journal()
+        self.send_error: Exception | None = None            # 있으면 send 가 던진다
+        self.state_error: Exception | None = None           # 있으면 delivery_state 가 던진다
+        self.register_error: Exception | None = None        # 있으면 register_template 이 던진다
+        self.states: dict[str, DeliveryState] = {}          # 업체 메시지 ID → 정해 둔 상태(없으면 번호 규칙)
+
+    async def register_template(self, provider_channel_id, template, text_version):
+        self.journal.append(("register_template", provider_channel_id, template.kind))
+        if self.register_error is not None:
+            raise self.register_error
+        return await super().register_template(provider_channel_id, template, text_version)
+
+    async def template_state(self, provider_template_id):
+        self.journal.append(("template_state", provider_template_id))
+        return await super().template_state(provider_template_id)
+
+    async def send(self, message):
+        self.journal.append(("send", message.provider_template_id))
+        if self.send_error is not None:
+            raise self.send_error
+        return await super().send(message)
+
+    async def delivery_state(self, provider_message_id):
+        self.journal.append(("delivery_state", provider_message_id))
+        if self.state_error is not None:
+            raise self.state_error
+        if provider_message_id in self.states:
+            return self.states[provider_message_id]
+        return await super().delivery_state(provider_message_id)
+
+    async def balance(self):
+        self.journal.append(("balance",))
+        return await super().balance()
```

`backend/apps/notification/tests/test_fakes_are_ports.py`:

```diff
@@ -1,10 +1,23 @@
 """공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
+from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.shop_profile_port import ShopProfilePort
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 from notification.app.ports.output.channel_repository import ChannelRepository
+from notification.app.ports.output.message_gateway_port import MessageGatewayPort
 from notification.app.ports.output.message_repository import MessageRepository
 from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
 from notification.app.ports.output.settings_repository import SettingsRepository
 from notification.app.ports.output.template_repository import TemplateRepository
-from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates
+from notification.tests.helpers.fakes import (
+    FakeChannels,
+    FakeDirectory,
+    FakeLedger,
+    FakeMessages,
+    FakeSettings,
+    FakeShopProfile,
+    FakeTemplates,
+    SpyGateway,
+)
 
 
 def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
@@ -13,3 +26,10 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     assert isinstance(FakeTemplates(), TemplateRepository)
     messages = FakeMessages()
     assert isinstance(messages, MessageRepository) and isinstance(messages, NotificationQueueRepository)
+
+
+def test_디스패처가_쓰는_허브_포트_스텁과_게이트웨이_스텁도_포트를_상속한다():
+    assert isinstance(FakeShopProfile(), ShopProfilePort)
+    assert isinstance(FakeDirectory(), CustomerDirectoryPort)
+    assert isinstance(FakeLedger(), VisitLedgerPort)
+    assert isinstance(SpyGateway(), MessageGatewayPort)
```

`backend/tests/integration/test_notification_dispatcher_wiring.py`:

```python
"""디스패처를 실제 저장소·실제 허브 포트(main.py 가 꽂은 것)·테스트 DB 로 돌린다. 게이트웨이는 Fake.

매장·고객·반려동물·방문은 API 로, 채널·설정·템플릿과 직접 넣는 메시지 줄은 SQL 로. 번호·이름·주소는 로그에 없어야 한다.
"""
import asyncio
import logging
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.services import dispatcher_wakeup
from notification.dependencies import dispatcher_provider as provider
from notification.dependencies.dispatcher_provider import build_dispatcher
from notification.domain.value_objects.message_kind import KINDS
from tests.integration.support import bearer, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
NAME, PHONE = "김민지", "01012345678"
CUSTOMER = {"name": NAME, "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


async def _link(wired, shop_id: int) -> None:
    await wired.execute(
        "INSERT INTO notification_channels (shop_id, status, provider, provider_channel_id, linked_at) "
        "VALUES (:shop_id, 'linked', 'solapi', 'KA01PF0001', now())", shop_id=shop_id)
    await wired.execute("INSERT INTO notification_settings (shop_id) VALUES (:shop_id)", shop_id=shop_id)
    for i, kind in enumerate(KINDS, start=1):
        await wired.execute(
            "INSERT INTO notification_templates (shop_id, kind, text_version, provider_template_id, status, "
            "requested_at) VALUES (:shop_id, :kind, 1, :template_id, 'approved', now())",
            shop_id=shop_id, kind=kind, template_id=f"KA01TP000{i}")


async def _shop(wired, customer=CUSTOMER):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    await _link(wired, shop_id)
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": customer, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    return shop_id, headers, body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _booked(wired, shop_id, headers, customer_id, pet_id, starts_at: datetime) -> int:
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _insert(wired, shop_id, customer_id, visit_id, kind="confirm", status="scheduled", **columns) -> None:
    """줄을 직접 넣는다. starts_at 은 내일 14시."""
    values = {"shop_id": shop_id, "customer_id": customer_id, "visit_id": visit_id, "kind": kind, "status": status,
              "scheduled_at": _now() - timedelta(seconds=1), "starts_at": _at(1, 14).isoformat(), **columns}
    columns_sql = ", ".join(k for k in values if k != "starts_at")
    params_sql = ", ".join(f":{k}" for k in values if k != "starts_at")
    await wired.execute(
        f"INSERT INTO notification_messages ({columns_sql}, variables) "
        f"VALUES ({params_sql}, jsonb_build_object('starts_at', CAST(:starts_at AS text)))", **values)


async def _rows(wired, shop_id: int) -> list[SimpleNamespace]:
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT id, kind, status, attempts, canceled_reason, provider_message_id, channel_used, error_code, "
            "error_kind, scheduled_at FROM notification_messages WHERE shop_id = :shop_id ORDER BY id"),
            {"shop_id": shop_id})
        return [SimpleNamespace(**row._mapping) for row in rows]


def _sessions(wired):
    return async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)


async def _run_once(wired, gateway: FakeGateway, now: datetime):
    async with _sessions(wired)() as session:
        return await build_dispatcher(session, gateway=gateway, now=lambda: now).run_once()


async def test_예약_접수_줄은_accepted_가_되고_다음_루프에서_sent_가_된다(wired, caplog):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit_id = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    gateway = FakeGateway()

    with caplog.at_level(logging.INFO, logger="notification.dispatcher"):
        first = await _run_once(wired, gateway, _now())
        confirm, reminder = await _rows(wired, shop_id)
        assert (first.claimed, first.sent) == (1, 1)
        assert (confirm.kind, confirm.status, confirm.provider_message_id, confirm.attempts) == (
            "confirm", "accepted", "fake-1", 1)
        assert (reminder.kind, reminder.status) == ("reminder", "scheduled")

        second = await _run_once(wired, gateway, _now() + timedelta(seconds=6))
        confirm, _ = await _rows(wired, shop_id)
        assert (second.polled, confirm.status, confirm.channel_used) == (1, "sent", "alimtalk")

    [outgoing] = gateway.sent_messages
    assert (outgoing.to, outgoing.provider_channel_id, outgoing.provider_template_id) == (PHONE, "KA01PF0001", "KA01TP0001")
    assert outgoing.variables["대상"] == "콩이" and outgoing.variables["매장명"] == "Hiss Haus"
    assert outgoing.fallback is None
    assert any("accepted" in r.getMessage() for r in caplog.records)
    for secret in (PHONE, "1234-5678", NAME, "콩이"):
        assert secret not in caplog.text


async def test_번호_끝이_0000_이면_업체가_영구_실패로_답한다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired, {**CUSTOMER, "phone": "010-1234-0000"})
    await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    gateway = FakeGateway()

    await _run_once(wired, gateway, _now())
    await _run_once(wired, gateway, _now() + timedelta(seconds=6))

    confirm, _ = await _rows(wired, shop_id)
    assert (confirm.status, confirm.error_code, confirm.error_kind) == ("failed", "3104", "permanent")


async def test_보내는_순간_고객이_익명화되어_있으면_anonymized_로_취소한다(wired):
    shop_id, headers, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1)
    deleted = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    gateway = FakeGateway()

    await _run_once(wired, gateway, _now())

    [row] = await _rows(wired, shop_id)
    assert (row.status, row.canceled_reason) == ("canceled", "anonymized")
    assert gateway.sent_messages == []


async def test_두_디스패처가_동시에_돌아도_한_줄을_둘이_보내지_않는다(wired):
    shop_id, _, customer_id, _ = await _shop(wired)
    for visit_id in (1, 2, 3):
        await _insert(wired, shop_id, customer_id, visit_id)
    gateway = FakeGateway()
    now = _now()

    async with _sessions(wired)() as first, _sessions(wired)() as second:
        reports = await asyncio.gather(
            build_dispatcher(first, gateway=gateway, now=lambda: now).run_once(),
            build_dispatcher(second, gateway=gateway, now=lambda: now).run_once(),
        )

    assert sum(r.sent for r in reports) == 3 and len(gateway.sent_messages) == 3
    assert [r.status for r in await _rows(wired, shop_id)] == ["accepted"] * 3


async def test_5분_넘게_sending_인_줄은_되돌려_다시_보낸다(wired):
    shop_id, _, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1, status="sending", updated_at=_now() - timedelta(minutes=6))
    await _insert(wired, shop_id, customer_id, visit_id=2, status="sending", updated_at=_now() - timedelta(minutes=4))
    gateway = FakeGateway()

    report = await _run_once(wired, gateway, _now())

    stuck, fresh = await _rows(wired, shop_id)
    assert (report.recovered, report.claimed) == (1, 1)
    assert (stuck.status, stuck.attempts) == ("accepted", 2)
    assert (fresh.status, fresh.attempts) == ("sending", 0)


async def test_하루_상한에_닿으면_나머지는_1시간_뒤로_미룬다(wired, monkeypatch):
    monkeypatch.setattr(provider, "NOTIFICATION_DAILY_CAP", 1)
    shop_id, _, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1)
    await _insert(wired, shop_id, customer_id, visit_id=2)
    gateway = FakeGateway()
    now = _now()

    report = await _run_once(wired, gateway, now)

    first, second = await _rows(wired, shop_id)
    assert (report.sent, report.deferred) == (1, 1)
    assert first.status == "accepted"
    assert (second.status, second.scheduled_at) == ("scheduled", now + timedelta(hours=1))


async def test_예약을_등록하면_구독자가_디스패처를_깨운다(wired, monkeypatch):
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    assert not dispatcher_wakeup._event.is_set()

    await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))

    assert dispatcher_wakeup._event.is_set()


async def test_루프가_부르는_run_once_는_세션을_열어_조립하고_한_번_돈다(wired, monkeypatch):
    """core.database.session_scope 로 연 세션 + 프로세스의 게이트웨이(여기선 Fake 로 바꿈)."""
    gateway = FakeGateway()
    monkeypatch.setattr(provider, "get_message_gateway", lambda: gateway)
    shop_id, _, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1)

    report = await provider.run_once()

    [row] = await _rows(wired, shop_id)
    assert (report.sent, row.status, row.provider_message_id) == (1, "accepted", "fake-1")
```

`backend/tests/test_app_lifespan.py`:

```python
"""API 프로세스의 lifespan — 기동하면 디스패처 작업이 돌고, 끝나면 멈춘다. DB 엔진·Redis 는 가짜, 게이트웨이는 Fake."""
import asyncio

import pytest

import main
from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.services import dispatcher_wakeup
from notification.app.services.dispatcher import DispatchReport
from notification.dependencies import dispatcher_provider as provider


@pytest.fixture(autouse=True)
def fresh_event(monkeypatch):
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())


def _dispatcher_tasks() -> list[asyncio.Task]:
    return [t for t in asyncio.all_tasks() if t.get_name() == "notification-dispatcher"]


async def test_lifespan_은_디스패처를_시작하고_끝나면_멈춘다(monkeypatch):
    runs = 0

    async def run_once() -> DispatchReport:
        nonlocal runs
        runs += 1
        return DispatchReport()

    async def nothing() -> None:
        return None

    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "dispose_engine", nothing)
    monkeypatch.setattr(main, "dispose_redis", nothing)
    monkeypatch.setattr(main, "get_message_gateway", FakeGateway)
    monkeypatch.setattr(provider, "run_once", run_once)

    async with main.lifespan(main.app):
        [task] = _dispatcher_tasks()
        dispatcher_wakeup.wake()
        await asyncio.sleep(0.8)
        assert runs == 1
    assert task.done() and _dispatcher_tasks() == []
```

`backend/tests/test_hub_port_binding.py`:

```diff
@@ -5,13 +5,16 @@ from fastapi import Depends, FastAPI
 import main
 from core.observer.in_process_event_bus import get_event_bus, subscribers
 from core.shop_guard import get_shop_access_port
+from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
 from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
+from notification.dependencies.dispatcher_ports import dispatcher_ports
 from tenancy.dependencies.hub_ports import get_user_directory
 from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
 from core.security import get_current_user_id
 from core.shop_guard import get_shop_context
 from tests.route_inspection import find_route_violations, routes_without_login
 from visit.dependencies.hub_ports import get_domain_events, get_shop_profile
+from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
 
 
 def test_API_프로세스에는_빈_자리도_빠진_가드도_없다():
@@ -44,6 +47,13 @@ def test_notification_구독자가_버스에_등록되어_있다():
     assert handle_visit_event in subscribers()
 
 
+def test_디스패처의_허브_포트_공장은_tenancy_customer_visit_의_프로바이더다():
+    ports = dispatcher_ports()
+    assert ports.shop_profile is get_shop_profile_use_case
+    assert ports.customer_directory is get_customer_directory_use_case
+    assert ports.visit_ledger is get_visit_ledger_use_case
+
+
 def _app_with(path, dependency=None):
     app = FastAPI()
     deps = [Depends(dependency)] if dependency else []
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

- 단위 `docker compose run --rm --no-deps backend pytest apps/notification tests/test_app_lifespan.py tests/test_hub_port_binding.py -q -p no:cacheprovider -m "not integration"` → 수집 오류 5(`No module named 'notification.app.services'`, `'notification.dependencies.dispatcher_ports'` 등), `Interrupted: 5 errors during collection`.
- 통합 `… run --rm backend pytest tests/integration/test_notification_dispatcher_wiring.py …` → 수집 오류 1(같은 이유).

구현 뒤 첫 실행에서 실패 5 — 테스트 쪽 셋(스텁 `created_at` 이 빌더 기본값이라 하루 상한 셈이 어긋남 → `created_at` 명시; 줄 ID 순서), 구현 쪽 둘(상태 조회가 실패하면 브리프대로 60초 — 처음엔 5초 규칙을 탔다; 로그에 취소 이유·오류 코드를 안 적었다 → `canceled(anonymized)`·`failed(3040)` 꼴로). 통합은 `jsonb_build_object('starts_at', :p)` 의 파라미터 형을 asyncpg 가 못 정해 `CAST(:p AS text)` 로(테스트 SQL).

- [ ] **Step 3: 구현한다**

`backend/apps/notification/app/services/system_context.py`:

```python
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext


def system_context(shop_id: int, timezone: str = "Asia/Seoul") -> ShopContext:
    """요청 밖(디스패처)에서 ShopContext 를 만드는 유일한 곳. 권한이 비어 있고 포트 읽기와 알림 표 쓰기에만 쓴다.

    멤버가 없어 member_id 는 0 이다. 시간대는 ShopProfilePort 에서 읽은 매장 값을 넣는다 — 시각 계산이 없는
    저장(status 바꾸기)만이면 기본값으로 둔다.
    """
    return ShopContext(shop_id=shop_id, member_id=0, role="system", permissions=frozenset(), timezone=timezone)
```

`backend/apps/notification/app/services/dispatcher.py`:

```python
"""디스패처 — 시각이 된 줄을 집어 검사하고(설계 5.3) 게이트웨이로 보내고 결과를 적는다. 템플릿 상태·잔액도 주기적으로 본다.

집고 → 커밋 → 검사 → 보내기 → 접수 기록. 잠금(집기)을 쥔 채 업체를 부르지 않는다(N14). 요청 밖이라 ShopContext 는
system_context 로 만든다. 로그에는 message_id·shop_id·종류·결과만 — 번호·이름·주소·변수·업체 응답은 찍지 않는다(N12).
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import (
    DeliveryState,
    FallbackText,
    GatewayError,
    GatewayPermanentError,
    GatewayTransientError,
    MessageGatewayPort,
    OutgoingMessage,
)
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.message_text import message_variables
from notification.app.services.system_context import system_context
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.services.schedule_rules import (
    ACCEPTED_TIMEOUT,
    STUCK_AFTER,
    deferred_for_daytime,
    is_mobile_number,
    is_too_late,
    retry_at,
)
from notification.domain.services.templates import TEMPLATES, TEXT_VERSION, render, sms_channel, target_label
from notification.domain.value_objects.message_kind import DEFAULT_KINDS, NEXT_VISIT, REMINDER, SCHEDULED_KINDS
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    FAILED,
    FALLBACK_SENT,
    SCHEDULED,
    SENT,
)
from notification.domain.value_objects.template_status import APPROVED, PENDING, REJECTED

logger = logging.getLogger("notification.dispatcher")

TEMPLATE_REFRESH_EVERY = timedelta(minutes=10)
BALANCE_CHECK_EVERY = timedelta(hours=24)
PENDING_TEMPLATE_DEFER = timedelta(minutes=10)
DAILY_CAP_DEFER = timedelta(hours=1)
POLL_SOON, POLL_LATER, POLL_SOON_WINDOW = timedelta(seconds=5), timedelta(seconds=60), timedelta(minutes=1)
ALIMTALK = "alimtalk"


@dataclass
class DispatchReport:
    recovered: int = 0
    claimed: int = 0
    sent: int = 0        # 업체가 접수한 줄
    deferred: int = 0    # scheduled 로 되돌린 줄(검수 중·야간·상한·일시 오류 재시도)
    canceled: int = 0
    failed: int = 0
    polled: int = 0      # 상태를 물은 accepted 줄


class Dispatcher:
    def __init__(
        self, *, queue: NotificationQueueRepository, channels: ChannelRepository, settings: SettingsRepository,
        templates: TemplateRepository, messages: MessageRepository, gateway: MessageGatewayPort,
        shops: ShopProfilePort, directory: CustomerDirectoryPort, ledger: VisitLedgerPort,
        commit: Callable[[], Awaitable[None]], now: Callable[[], datetime], daily_cap: int,
        balance_warn_krw: int, claim_limit: int = 50,
    ) -> None:
        self._queue = queue
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._messages = messages
        self._gateway = gateway
        self._shops = shops
        self._directory = directory
        self._ledger = ledger
        self._commit = commit
        self._now = now
        self._daily_cap = daily_cap
        self._balance_warn_krw = balance_warn_krw
        self._claim_limit = claim_limit
        self._templates_refreshed_at: datetime | None = None
        self._balance_checked_at: datetime | None = None

    async def run_once(self) -> DispatchReport:
        report = DispatchReport()
        now = self._now()
        report.recovered = await self._queue.recover_stuck(now - STUCK_AFTER)
        await self._commit()
        claimed = await self._queue.claim_due(now, self._claim_limit)
        await self._commit()      # 여기서 잠금이 풀린다 — 업체는 이 뒤에 부른다(N14)
        report.claimed = len(claimed)
        for m in claimed:
            try:
                updated = await self._process(m, now)
            except Exception as exc:   # 한 줄의 문제가 다음 줄을 막지 않는다
                logger.warning("알림 %s(매장 %s, %s) 처리 실패 %s — 일시 오류로 적습니다.",
                               m.id, m.shop_id, m.kind, type(exc).__name__)
                updated = self._retry(m, now, type(exc).__name__[:20])
            await self._messages.save(system_context(m.shop_id), updated)
            await self._commit()
            logger.info("알림 %s(매장 %s, %s) → %s", m.id, m.shop_id, m.kind, _outcome(updated))
            self._count(report, updated)
        for m in await self._queue.list_accepted(now):
            try:
                state = await self._gateway.delivery_state(m.provider_message_id)
            except GatewayError:
                updated = self._still_pending(m, now, POLL_LATER)
            else:
                updated = self._polled(m, state, now)
            await self._messages.save(system_context(m.shop_id), updated)
            await self._commit()
            logger.info("알림 %s(매장 %s, %s) 상태 → %s", m.id, m.shop_id, m.kind, _outcome(updated))
            report.polled += 1
            if updated.status == FAILED:
                report.failed += 1
        if self._templates_refreshed_at is None or now - self._templates_refreshed_at >= TEMPLATE_REFRESH_EVERY:
            await self.refresh_templates()
        if self._balance_checked_at is None or now - self._balance_checked_at >= BALANCE_CHECK_EVERY:
            self._balance_checked_at = now
            await self.check_balance()
        return report

    @staticmethod
    def _count(report: DispatchReport, updated: NotificationMessage) -> None:
        if updated.status == ACCEPTED:
            report.sent += 1
        elif updated.status == SCHEDULED:
            report.deferred += 1
        elif updated.status == CANCELED:
            report.canceled += 1
        elif updated.status == FAILED:
            report.failed += 1

    # --- 집은 줄 하나 ---------------------------------------------------------------------------------------------

    async def _process(self, m: NotificationMessage, now: datetime) -> NotificationMessage:
        """검사(설계 5.3 순서)를 다 지나면 보낸다. 걸리면 취소하거나 미룬 줄을 돌려준다."""
        profile = await self._shops.public_profile(m.shop_id)
        if profile is None or not profile.open:
            return self._cancel(m, "shop_closed")
        ctx, tz = system_context(m.shop_id, profile.timezone), profile.timezone
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            return self._cancel(m, "channel_unlinked")
        settings = await self._settings.get(ctx)
        if settings is None or not settings.enabled_for(m.kind):
            return self._cancel(m, "setting_off")
        template = await self._templates.get(ctx, m.kind)
        if template is None or template.status == REJECTED:
            return self._cancel(m, "template_rejected")
        if template.status == PENDING:
            return replace(m, status=SCHEDULED, scheduled_at=now + PENDING_TEMPLATE_DEFER)   # 재등록 중이다
        contact = await self._directory.contact(ctx, m.customer_id)
        if contact is None:
            return self._cancel(m, "anonymized")
        if not is_mobile_number(contact.phone):
            return self._cancel(m, "bad_phone")
        if m.kind in SCHEDULED_KINDS:
            send_at = deferred_for_daytime(now, tz)
            if m.kind == REMINDER and is_too_late(send_at, datetime.fromisoformat(m.variables["starts_at"])):
                return self._cancel(m, "too_late")
            if send_at > now:
                return replace(m, status=SCHEDULED, scheduled_at=send_at)
        if m.kind == NEXT_VISIT:
            if not contact.marketing_consent:
                return self._cancel(m, "no_consent")
            if await self._ledger.customer_has_upcoming(ctx, m.customer_id):
                return self._cancel(m, "has_upcoming")
            last = await self._messages.last_delivered_at(ctx, m.customer_id, NEXT_VISIT)
            if last is not None and last > now - timedelta(days=settings.next_visit_cooldown_days):
                return self._cancel(m, "cooldown")
        sent_today = await self._messages.count_sent_since(ctx, _day_start(now, tz))
        if sent_today >= self._daily_cap:
            logger.warning("매장 %s 의 오늘 발송 %s건이 하루 상한 %s에 닿아 1시간 미룹니다.",
                           m.shop_id, sent_today, self._daily_cap)
            return replace(m, status=SCHEDULED, scheduled_at=now + DAILY_CAP_DEFER)

        pet_name = None
        if m.pet_id is not None:
            pet = (await self._directory.briefs(ctx, [], [m.pet_id])).pets.get(m.pet_id)
            pet_name = pet.name if pet is not None else None
        variables = message_variables(m.kind, shop_name=profile.name, target=target_label(pet_name, contact.name),
                                      tz=tz, variables=m.variables)
        rendered = render(m.kind, variables)
        fallback = None
        if channel.can_fallback:
            fallback = FallbackText(channel.sender_number, rendered.sms_text, sms_channel(rendered.sms_text))
        outgoing = OutgoingMessage(
            to=contact.phone, provider_channel_id=channel.provider_channel_id,
            provider_template_id=template.provider_template_id, variables=variables,
            button_url=rendered.button_url, fallback=fallback,
        )
        try:
            accepted = await self._gateway.send(outgoing)
        except GatewayTransientError as exc:
            return self._retry(m, now, exc.code)
        except GatewayPermanentError as exc:
            return replace(m, status=FAILED, attempts=m.attempts + 1, error_kind="permanent", error_code=exc.code)
        return replace(m, status=ACCEPTED, attempts=m.attempts + 1, provider_message_id=accepted.provider_message_id,
                       next_attempt_at=now + POLL_SOON, error_code=None, error_kind=None)

    @staticmethod
    def _cancel(m: NotificationMessage, reason: str) -> NotificationMessage:
        return replace(m, status=CANCELED, canceled_reason=reason)

    @staticmethod
    def _retry(m: NotificationMessage, now: datetime, code: str) -> NotificationMessage:
        """일시 오류 — attempts 를 올리기 전 값으로 다음 시각을 정한다(0·1·2 → 1·5·30분). 네 번째 실패에서 멈춘다."""
        at = retry_at(m.attempts, now)
        if at is None:
            return replace(m, status=FAILED, attempts=m.attempts + 1, error_kind="transient", error_code=code)
        return replace(m, status=SCHEDULED, scheduled_at=at, attempts=m.attempts + 1, error_kind="transient",
                       error_code=code)

    # --- 접수 뒤 상태 조회 -----------------------------------------------------------------------------------------

    def _polled(self, m: NotificationMessage, state: DeliveryState, now: datetime) -> NotificationMessage:
        if state.status == "sent":
            status = SENT if state.channel_used == ALIMTALK else FALLBACK_SENT
            return replace(m, status=status, channel_used=state.channel_used, sent_at=now)
        if state.status == "failed":
            return replace(m, status=FAILED, error_code=state.error_code, error_kind=state.error_kind)
        return self._still_pending(m, now)

    @staticmethod
    def _still_pending(m: NotificationMessage, now: datetime, wait: timedelta | None = None) -> NotificationMessage:
        """처음 1분은 5초마다, 그 뒤 1분마다(조회가 실패했으면 1분). 24시간이 지나면 일시 실패."""
        if now - m.scheduled_at > ACCEPTED_TIMEOUT:
            return replace(m, status=FAILED, error_kind="transient", error_code="TIMEOUT")
        if wait is None:
            wait = POLL_SOON if now - m.scheduled_at < POLL_SOON_WINDOW else POLL_LATER
        return replace(m, next_attempt_at=now + wait)

    # --- 주기 작업 -------------------------------------------------------------------------------------------------

    async def refresh_templates(self) -> int:
        """검수 중인 템플릿의 업체 상태를 적고, 연동한 매장의 빠진 종류를 다시 등록한다(설계 9.5). 바꾼 수."""
        now = self._now()
        profiles: dict[int, ShopProfile | None] = {}
        changed = 0
        for t in await self._queue.list_pending_templates():
            profile = await self._profile(t.shop_id, profiles)
            if profile is None:
                continue
            try:
                state = await self._gateway.template_state(t.provider_template_id)
            except GatewayError as exc:
                logger.warning("매장 %s 의 %s 템플릿 상태 조회 실패 (%s)", t.shop_id, t.kind, exc.code)
                continue
            if state.status in (APPROVED, REJECTED):
                await self._templates.set_status(system_context(t.shop_id, profile.timezone), t.kind, state.status,
                                                 state.rejected_reason, now)
                await self._commit()
                changed += 1
        channels = await self._queue.list_linked_channels()
        existing = await self._queue.list_templates_for_shops([c.shop_id for c in channels])
        for c in channels:
            profile = await self._profile(c.shop_id, profiles)
            if profile is None:
                continue
            ctx = system_context(c.shop_id, profile.timezone)
            settings = await self._settings.get(ctx)
            wanted = list(DEFAULT_KINDS)
            if settings is not None and settings.next_visit_enabled:
                wanted.append(NEXT_VISIT)
            have = {t.kind for t in existing[c.shop_id]}
            for kind in wanted:
                if kind in have:
                    continue
                try:
                    provider_id = await self._gateway.register_template(c.provider_channel_id, TEMPLATES[kind],
                                                                        TEXT_VERSION)
                except GatewayError as exc:
                    logger.warning("매장 %s 의 %s 템플릿 등록 실패 (%s) — 다음 주기에 다시 합니다.", c.shop_id, kind, exc.code)
                    continue
                await self._templates.upsert(ctx, kind, TEXT_VERSION, provider_id, now)
                await self._commit()
                changed += 1
        self._templates_refreshed_at = now
        return changed

    async def _profile(self, shop_id: int, cache: dict[int, ShopProfile | None]) -> ShopProfile | None:
        if shop_id not in cache:
            cache[shop_id] = await self._shops.public_profile(shop_id)
        return cache[shop_id]

    async def check_balance(self) -> int:
        """잔액(원). 기준 아래면 WARNING — 금액만 적는다."""
        balance = await self._gateway.balance()
        if balance < self._balance_warn_krw:
            logger.warning("발송 잔액 %s원이 기준 %s원 아래입니다. 충전이 필요합니다.", balance, self._balance_warn_krw)
        return balance


def _outcome(m: NotificationMessage) -> str:
    """로그용 — 상태와 취소 이유·오류 코드만."""
    detail = m.canceled_reason or m.error_code
    return f"{m.status}({detail})" if detail else m.status


def _day_start(now: datetime, tz: str) -> datetime:
    """매장 시간대의 오늘 00:00 을 UTC 로."""
    return datetime.combine(now.astimezone(ZoneInfo(tz)).date(), time(0), tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
```

`backend/apps/notification/app/services/dispatcher_wakeup.py`:

```python
"""같은 프로세스에서 줄이 생기면 디스패처 루프를 바로 깨운다(설계 5.3-1). 구독자가 wake, 루프가 wait."""
from __future__ import annotations

import asyncio

_event = asyncio.Event()


def wake() -> None:
    _event.set()


async def wait(timeout: float) -> None:
    """깨우거나 timeout 초가 지나면 돌아온다. 깨어나면 이벤트를 지운다."""
    try:
        await asyncio.wait_for(_event.wait(), timeout)
    except TimeoutError:
        pass
    _event.clear()
```

`backend/apps/notification/app/services/message_text.py`:

```python
"""저장된 variables(구독자가 넣은 ISO 문자열)로 문안 변수와 문안을 만든다. 디스패처(보낼 때)와 API(share_text)가 같이 쓴다."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from notification.domain.services.templates import RenderedMessage, render, variables_for


def _at(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def message_variables(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> dict[str, str]:
    """문안 변수(이름: 값, `#{}` 없음). 업체에 넘기는 사전이자 render 의 입력이다."""
    interval = variables.get("interval_weeks")
    return variables_for(
        kind, shop_name=shop_name, target=target, starts_at=datetime.fromisoformat(variables["starts_at"]), tz=tz,
        previous_starts_at=_at(variables.get("previous_starts_at")), url=variables.get("url"),
        expires_at=_at(variables.get("expires_at")), last_visit_at=_at(variables.get("completed_at")),
        interval_weeks=int(interval) if interval is not None else None,
    )


def message_text(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> RenderedMessage:
    return render(kind, message_variables(kind, shop_name=shop_name, target=target, tz=tz, variables=variables))
```

`backend/apps/notification/dependencies/dispatcher_ports.py`:

```python
"""디스패처가 쓰는 허브 포트 구현의 공장 자리 — 요청 밖이라 FastAPI 의 DI 자리(dependency_overrides)를 못 쓴다.

main.py 가 configure_dispatcher_ports 로 tenancy·customer·visit 의 프로바이더를 꽂는다. 이 모듈은 다른 스포크를 모른다.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


@dataclass(frozen=True)
class DispatcherPorts:
    shop_profile: Callable[[AsyncSession], ShopProfilePort]
    customer_directory: Callable[[AsyncSession], CustomerDirectoryPort]
    visit_ledger: Callable[[AsyncSession], VisitLedgerPort]


_ports: DispatcherPorts | None = None


def configure_dispatcher_ports(ports: DispatcherPorts) -> None:
    global _ports
    _ports = ports


def dispatcher_ports() -> DispatcherPorts:
    if _ports is None:
        raise RuntimeError("디스패처의 허브 포트 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
    return _ports
```

`backend/apps/notification/dependencies/dispatcher_provider.py`:

```python
"""디스패처 조립과 루프 — 기동 때 asyncio 작업 하나가 돈다(설계 3.2). 테스트는 루프 대신 build_dispatcher(...).run_once()."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import NOTIFICATION_DAILY_CAP, SOLAPI_BALANCE_WARN_KRW
from core.database import session_scope
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.services.dispatcher import Dispatcher, DispatchReport
from notification.app.services.dispatcher_wakeup import wait
from notification.dependencies.dispatcher_ports import dispatcher_ports
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.clock import utc_now

logger = logging.getLogger("notification.dispatcher")

WAKE_SETTLE_SECONDS = 0.5      # 깨운 쪽(구독자)의 커밋이 먼저 닿게


def build_dispatcher(
    db: AsyncSession, *, gateway: MessageGatewayPort | None = None, now: Callable[[], datetime] | None = None
) -> Dispatcher:
    ports = dispatcher_ports()
    messages = build_message_repository(db)
    return Dispatcher(
        queue=messages, channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db), messages=messages,
        gateway=gateway if gateway is not None else get_message_gateway(),
        shops=ports.shop_profile(db), directory=ports.customer_directory(db), ledger=ports.visit_ledger(db),
        commit=db.commit, now=now if now is not None else utc_now,
        daily_cap=NOTIFICATION_DAILY_CAP, balance_warn_krw=SOLAPI_BALANCE_WARN_KRW,
    )


async def run_once() -> DispatchReport:
    async with session_scope() as db:
        return await build_dispatcher(db).run_once()


async def run_forever(stop: asyncio.Event, interval: float = 2.0) -> None:
    """stop 까지: interval 초마다 또는 깨우면 한 번 돈다. 한 번의 예외는 로그 뒤 다음 번으로."""
    while not stop.is_set():
        await wait(interval)
        if stop.is_set():
            return
        await asyncio.sleep(WAKE_SETTLE_SECONDS)
        if stop.is_set():
            return
        try:
            await run_once()
        except Exception as exc:
            logger.warning("디스패처 루프 한 번이 실패했습니다 (%s). 다음 번에 다시 돕니다.", type(exc).__name__)


def start_dispatcher() -> tuple[asyncio.Task, asyncio.Event]:
    """main.py 의 lifespan 이 부른다. 끝낼 때 stop.set() 과 wake() 뒤 task 를 기다린다."""
    stop = asyncio.Event()
    task = asyncio.create_task(run_forever(stop), name="notification-dispatcher")
    return task, stop
```

`backend/apps/notification/adapter/inbound/observer/visit_event_subscriber.py`:

```diff
@@ -12,6 +12,7 @@ from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepo
 from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
 from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
 from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand
+from notification.app.services.dispatcher_wakeup import wake
 from notification.app.use_cases.handle_visit_event_interactor import HandleVisitEventInteractor
 from notification.domain.services.clock import utc_now
 
@@ -23,3 +24,4 @@ async def handle_visit_event(session: AsyncSession, event: VisitEvent) -> None:
         templates=TemplatePgRepository(session), messages=MessagePgRepository(session), now=utc_now,
     )
     await use_case.handle_visit_event(HandleVisitEventCommand(event=event))
+    wake()   # 줄을 만들었든 아니든 — 루프가 반 초 뒤(요청의 커밋 뒤) 돈다(설계 5.3-1)
```

`backend/apps/notification/app/services/__init__.py`:

```python

```

`backend/core/database.py`:

```diff
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 from collections.abc import AsyncGenerator
+from contextlib import asynccontextmanager
 from typing import Annotated
 
 from fastapi import Depends
@@ -54,6 +55,16 @@ async def get_db() -> AsyncGenerator[AsyncSession, None]:
             raise
 
 
+@asynccontextmanager
+async def session_scope() -> AsyncGenerator[AsyncSession, None]:
+    """요청 밖(디스패처)에서 세션 하나를 연다. 커밋은 부르는 쪽이 단계마다 한다 — 닫힐 때 남은 것은 롤백된다."""
+    if _session_factory is None:
+        init_engine()
+    assert _session_factory is not None
+    async with _session_factory() as session:
+        yield session
+
+
 # 요청 함수가 끝나는 즉시(응답을 보내기 전에) 커밋되도록 function 스코프로 정리한다.
 # 기본 스코프는 응답 본문을 보낸 뒤에 정리되어, 클라이언트가 커밋 전 데이터를 보지 못한 채 200을 받는다.
 DbSession = Annotated[AsyncSession, Depends(get_db, scope="function")]
```

`backend/main.py`:

```diff
@@ -48,6 +48,9 @@ from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
 from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
 from media.dependencies.media_library_provider import get_media_library_use_case
 from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
+from notification.app.services.dispatcher_wakeup import wake
+from notification.dependencies.dispatcher_ports import DispatcherPorts, configure_dispatcher_ports
+from notification.dependencies.dispatcher_provider import start_dispatcher
 from notification.dependencies.notification_wiring import get_message_gateway
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
@@ -111,9 +114,14 @@ async def lifespan(app: FastAPI):
     init_engine()
     # 발송 게이트웨이를 기동 때 만든다 — 운영에서 솔라피 키가 비면 첫 발송이 아니라 여기서 멈춘다(설계 6.1).
     get_message_gateway()
+    # 디스패처 — 프로세스에 asyncio 작업 하나(설계 3.2). 끝낼 때 정지를 알리고 깨워서 기다림을 끊는다.
+    task, stop = start_dispatcher()
     try:
         yield
     finally:
+        stop.set()
+        wake()
+        await task
         await dispose_engine()
         await dispose_redis()
 
@@ -211,6 +219,11 @@ app.dependency_overrides[get_shop_profile] = get_shop_profile_use_case
 # 도메인 이벤트 — visit 이 발행하고 core 의 같은 세션 동기 버스가 구독자에 넘긴다. 구독자는 여기서 꽂는다.
 app.dependency_overrides[get_domain_events] = get_event_bus
 subscribe(handle_visit_event)
+# 디스패처는 요청 밖이라 Depends 자리를 못 쓴다 — 같은 세 프로바이더를 세션을 받는 공장으로 꽂는다.
+configure_dispatcher_ports(DispatcherPorts(
+    shop_profile=get_shop_profile_use_case, customer_directory=get_customer_directory_use_case,
+    visit_ledger=get_visit_ledger_use_case,
+))
 
 
 @app.get("/health")
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 단위(디스패처 45 + 깨우기 3 + 프로바이더 7 + lifespan 1 + 바인딩 1 + 스텁 포트 1) | 58 passed |
| 이 작업의 통합(`test_notification_dispatcher_wiring.py`) | 8 passed |
| 단위 전체 (`-m "not integration and not network"`, `--no-deps`) | 1596 passed (시작 1538 + 58) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken |

통합 세션은 테스트 DB(`chagocnote_test`)에만 붙었다 — 개발 DB 에 마이그레이션을 올리지 않았다. 실제 `api.solapi.com` 은 부르지 않았다(게이트웨이는 전부 `FakeGateway`/`SpyGateway`).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `claim_due` 뒤의 `commit` 제거(send 뒤 한 번만) → `test_dispatcher.py::test_집고_커밋한_뒤에_보내고_결과를_적은_뒤_다시_커밋한다`
- `send_at = deferred_for_daytime(now, tz)` → `send_at = now` → `::test_리마인드와_다음_예약_제안은_매장_시간대의_밤이면_아침_8시로_미룬다[22시]`, `[06시]`, `::test_리마인드는_보낼_시각이_예약_1시간_전을_넘기면_too_late[미룬 시각이 늦다]`
- 쿨다운 비교 `last > now - cooldown` → `>=` → `::test_다음_예약_제안은_쿨다운_안에_같은_종류를_받았으면_cooldown_이고_정확히_30일이면_간다`
- 상태 조회의 `SENT if channel_used == "alimtalk" else FALLBACK_SENT` → 늘 `SENT` → `::test_문자로_대체되어_나갔으면_fallback_sent_다`
- 하루 상한 검사 `if sent_today >= cap` → `if False` → `::test_매장의_오늘_발송이_하루_상한에_닿으면_1시간_뒤로_미루고_경고만_남긴다`
- `_process` 의 예외를 `raise` 로 밖에 던짐 → `::test_한_줄의_예외는_그_줄만_일시_실패로_적고_다음_줄을_막지_않는다`
- 접수 직전 `logger.info("보냄 %s", contact.phone)` 추가 → `::test_로그에는_메시지_ID_매장_종류_결과만_있고_번호_이름_주소는_없다`
- `is_too_late` 검사 제거 → `::test_리마인드는_보낼_시각이_예약_1시간_전을_넘기면_too_late[미룬 시각이 늦다]`, `[지금이 늦다]`
- `recover_stuck` 호출 제거 → `::test_집고_커밋한_뒤에_…`, `::test_5분_넘게_sending_인_줄은_되돌리고_시도를_세고_같은_루프에서_다시_보낸다`
- 24시간 타임아웃 검사 제거 → `::test_접수_뒤_24시간_안에_최종_상태가_없으면_일시_실패다`
- `retry_at(m.attempts, now)` → `retry_at(m.attempts + 1, now)`(올린 뒤 값) → `::test_일시_오류는_1분_5분_30분_뒤로_미루고_네_번째_실패에서_failed_다`, `::test_한_줄의_예외는_…`
- 재등록 목록에 `next_visit` 을 설정과 상관없이 넣음 → `::test_연동한_매장의_빠진_종류를_다시_등록하고_다음_예약_제안은_켜진_매장만`
- `main.py` 의 `configure_dispatcher_ports(...)` 제거 → `tests/test_hub_port_binding.py::test_디스패처의_허브_포트_공장은_tenancy_customer_visit_의_프로바이더다`
- `main.py` lifespan 의 `start_dispatcher`/정지 제거 → `tests/test_app_lifespan.py::test_lifespan_은_디스패처를_시작하고_끝나면_멈춘다`
- `run_forever` 의 깨어난 뒤 0.5초 대기 제거 → `test_dispatcher_provider.py::test_루프는_깨우면_반_초_뒤에_한_번_돌고_정지하면_끝난다`
- 구독자 끝의 `wake()` 제거 → `test_notification_dispatcher_wiring.py::test_예약을_등록하면_구독자가_디스패처를_깨운다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 디스패처 — 집고·검사하고·보내고·결과를 적는다, 템플릿 상태와 잔액, 기동 때 도는 루프

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: 설정·온보딩 API 여덟 — 개요, 채널 토큰 신청·연동·해제, 설정 전체 교체와 후속, 발신번호 인증 시작·확인, 횟수 제한

**Files:**
- Create: `backend/apps/notification/app/ports/output/onboarding_limiter_port.py`
- Create: `backend/apps/notification/adapter/outbound/redis/onboarding_redis_limiter.py`
- Create: `backend/apps/notification/app/use_cases/link_channel_interactor.py`
- Create: `backend/apps/notification/app/use_cases/update_notification_settings_interactor.py`
- Create: `backend/apps/notification/app/services/overview.py`
- Create: `backend/apps/notification/app/services/template_registration.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/__init__.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/confirm_sender_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/link_channel_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/notification_myself_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/notification_overview_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/onboarding_fields.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/request_channel_token_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/request_sender_verification_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/update_notification_settings_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/__init__.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/confirm_sender_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/get_notification_overview_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/link_channel_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/notification_myself_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/request_channel_token_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/request_sender_verification_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/unlink_channel_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/update_notification_settings_router.py`
- Create: `backend/apps/notification/adapter/outbound/log_notification_myself_record_adapter.py`
- Create: `backend/apps/notification/adapter/outbound/redis/__init__.py`
- Create: `backend/apps/notification/app/dtos/confirm_sender_dto.py`
- Create: `backend/apps/notification/app/dtos/get_notification_overview_dto.py`
- Create: `backend/apps/notification/app/dtos/link_channel_dto.py`
- Create: `backend/apps/notification/app/dtos/notification_myself_dto.py`
- Create: `backend/apps/notification/app/dtos/notification_overview_dto.py`
- Create: `backend/apps/notification/app/dtos/request_channel_token_dto.py`
- Create: `backend/apps/notification/app/dtos/request_sender_verification_dto.py`
- Create: `backend/apps/notification/app/dtos/unlink_channel_dto.py`
- Create: `backend/apps/notification/app/dtos/update_notification_settings_dto.py`
- Create: `backend/apps/notification/app/ports/input/confirm_sender_use_case.py`
- Create: `backend/apps/notification/app/ports/input/get_notification_overview_use_case.py`
- Create: `backend/apps/notification/app/ports/input/link_channel_use_case.py`
- Create: `backend/apps/notification/app/ports/input/notification_myself_use_case.py`
- Create: `backend/apps/notification/app/ports/input/request_channel_token_use_case.py`
- Create: `backend/apps/notification/app/ports/input/request_sender_verification_use_case.py`
- Create: `backend/apps/notification/app/ports/input/unlink_channel_use_case.py`
- Create: `backend/apps/notification/app/ports/input/update_notification_settings_use_case.py`
- Create: `backend/apps/notification/app/ports/output/notification_myself_record_port.py`
- Create: `backend/apps/notification/app/use_cases/confirm_sender_interactor.py`
- Create: `backend/apps/notification/app/use_cases/get_notification_overview_interactor.py`
- Create: `backend/apps/notification/app/use_cases/notification_myself_interactor.py`
- Create: `backend/apps/notification/app/use_cases/request_channel_token_interactor.py`
- Create: `backend/apps/notification/app/use_cases/request_sender_verification_interactor.py`
- Create: `backend/apps/notification/app/use_cases/unlink_channel_interactor.py`
- Create: `backend/apps/notification/dependencies/confirm_sender_provider.py`
- Create: `backend/apps/notification/dependencies/get_notification_overview_provider.py`
- Create: `backend/apps/notification/dependencies/link_channel_provider.py`
- Create: `backend/apps/notification/dependencies/notification_myself_provider.py`
- Modify: `backend/apps/notification/dependencies/notification_wiring.py`
- Create: `backend/apps/notification/dependencies/request_channel_token_provider.py`
- Create: `backend/apps/notification/dependencies/request_sender_verification_provider.py`
- Create: `backend/apps/notification/dependencies/unlink_channel_provider.py`
- Create: `backend/apps/notification/dependencies/update_notification_settings_provider.py`
- Create: `backend/apps/notification/tests/adapter/test_confirm_sender_router.py`
- Create: `backend/apps/notification/tests/adapter/test_get_notification_overview_router.py`
- Create: `backend/apps/notification/tests/adapter/test_link_channel_router.py`
- Create: `backend/apps/notification/tests/adapter/test_notification_myself_router.py`
- Create: `backend/apps/notification/tests/adapter/test_onboarding_redis_limiter.py`
- Create: `backend/apps/notification/tests/adapter/test_request_channel_token_router.py`
- Create: `backend/apps/notification/tests/adapter/test_request_sender_verification_router.py`
- Create: `backend/apps/notification/tests/adapter/test_unlink_channel_router.py`
- Create: `backend/apps/notification/tests/adapter/test_update_notification_settings_router.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_confirm_sender_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_get_notification_overview_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_link_channel_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_request_channel_token_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_request_sender_verification_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_unlink_channel_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_update_notification_settings_interactor.py`
- Create: `backend/apps/notification/tests/helpers/api.py`
- Modify: `backend/apps/notification/tests/helpers/fakes.py`
- Create: `backend/apps/notification/tests/helpers/onboarding_world.py`
- Modify: `backend/apps/notification/tests/test_fakes_are_ports.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_notification_onboarding_wiring.py`

**Interfaces:**
- Consumes: 작업 3 의 오류·`DEFAULT_NOTIFICATION_SETTINGS`·`KINDS`, 작업 4 의 저장소 넷, 작업 6 의 게이트웨이 온보딩 메서드, 작업 7 의 `dispatcher_wakeup.wake`·`message_text`; 기존 `core/shop_guard.require_permission("shop:update")`, `core.redis.get_redis`, visit 의 라우터·스키마·프로바이더·`/myself` 모양, `install_error_handlers`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

### 5.1 API 계약 (⑥-2 앱이 기대는 것 — T10 결정 기록 009 가 이 절을 옮긴다)

접두 `/v1/shops/{shop_id}/notification`, 태그 `notifications`, 전부 로그인 + 매장 소속. 읽기 둘은 소속이면 되고 명령 여섯은 `shop:update`(사장). 오류 응답은 공통 `{"code", "message"}`.

| 메서드·경로 | 권한 | 요청 본문 | 성공 | 오류 |
|---|---|---|---|---|
| GET `/myself` | 소속 | — | 200 `{id: 7, name: "알림 (notification)", introduction}` | |
| GET `` | 소속 | — | 200 overview | |
| POST `/channel/token` | shop:update | `{search_id, admin_phone, category_code}` | 202 `{"status": "token_requested"}` | 409 `NOTIFICATION_CHANNEL_LINKED`(이미 linked) · 429 `NOTIFICATION_RATE_LIMITED` · 502 `NOTIFICATION_PROVIDER_UNAVAILABLE` |
| POST `/channel` | shop:update | `{search_id, admin_phone, category_code, token}` | 200 overview | 400 `NOTIFICATION_TOKEN_INVALID` · 409 `NOTIFICATION_CHANNEL_NOT_LINKED`(토큰을 받은 적 없음 — none·unlinked) · 409 `NOTIFICATION_CHANNEL_LINKED`(이미 linked) · 429 · 502 |
| DELETE `/channel` | shop:update | — | 204 빈 본문 | 409 `NOTIFICATION_CHANNEL_NOT_LINKED` |
| PUT `/settings` | shop:update | 아홉 칸 전체(아래) | 200 overview | 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 409 `NOTIFICATION_SENDER_NOT_VERIFIED` · 422 `VALIDATION_ERROR`(형식·범위) |
| POST `/sender/verification` | shop:update | `{phone}` | 202 `{"status": "verification_requested"}` | 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 429 · 502 |
| POST `/sender` | shop:update | `{phone, code}` | 200 overview | 400 `NOTIFICATION_TOKEN_INVALID` · 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 429 · 502 |

공통: 다른 매장 → 403 `NOT_A_MEMBER`, 직원이 명령 → 403 `PERMISSION_DENIED`, 본문 형식 → 422 `VALIDATION_ERROR`, `shop_id` 가 int32 밖 → 422.

요청 칸의 형식(`adapter/inbound/api/schemas/onboarding_fields.py`, 어긋나면 422)
```
search_id      : 1~100자, 공백·제어 문자 없음              (업체에만 넘기고 저장하지 않는다)
admin_phone    : ^01[0-9]{8,9}$  (휴대폰, 하이픈 없이)      (저장하지 않는다)
category_code  : 1~20자, 공백·제어 문자 없음
token · code   : ^[0-9]{6}$
phone          : ^[0-9]{9,11}$  (발신번호 — 유선도 된다, 하이픈 없이)
```
PUT `/settings` 본문(아홉 칸 모두 필수, `StrictBool`/`StrictInt` — 문자열 "true"·숫자 1 은 422)
```
confirm_enabled, reminder_enabled, report_enabled, change_enabled, next_visit_enabled, sms_fallback_enabled : bool
reminder_time            : "HH:MM" (정규식 ^([01][0-9]|2[0-3]):[0-5][0-9]$; 08:00~21:00 밖은 도메인이 422)
next_visit_after_weeks   : int(0 이상) | null   (1~52 밖은 도메인이 422; null = 지난 방문 간격)
next_visit_cooldown_days : int(0 이상)          (1~365 밖은 도메인이 422)
```
overview 응답(`NotificationOverviewSchema`) — 시각은 매장 시간대(`+09:00`), 업체 ID 는 없다
```
channel:   {status: "none"|"token_requested"|"linked"|"unlinked", linked_at: datetime|null,
            sender_number: str|null, sender_verified: bool, sms_fallback_enabled: bool}
           (채널 줄이 없으면 status "none" 에 나머지 null/false)
settings:  {confirm_enabled, reminder_enabled, report_enabled, change_enabled, next_visit_enabled: bool,
            reminder_time: "HH:MM", next_visit_after_weeks: int|null, next_visit_cooldown_days: int} | null (연동 전)
templates: [{kind, status: "pending"|"approved"|"rejected", rejected_reason: str|null,
             requested_at: datetime, decided_at: datetime|null}]   — KINDS 순, 연동 전·해제 뒤엔 []
```
연동 직후 overview: `channel.status "linked"`, `settings` 기본값(`true,true,true,true,false,"18:00",null,30`), `templates` 다섯 `pending`(confirm·reminder·report·change·cancel — `next_visit` 은 설정에서 켤 때 등록). 등록 하나가 업체 오류로 빠지면 그 종류만 없고 디스패처가 10분 안에 채운다.

### 5.2 코드 시그니처

```python
# notification.app.ports.output.onboarding_limiter_port
class OnboardingLimiterPort(ABC):
    async def allow(self, shop_id: int, action: str) -> bool     # action: "token" | "link" | "sender_verification" | "sender_confirm"
        # 요청 하나를 세고(맞든 틀리든) 창 안의 횟수가 한도 안이면 True

# notification.adapter.outbound.redis.onboarding_redis_limiter
_LIMITS = {"token": (5, 3600), "sender_verification": (5, 3600), "link": (5, 600), "sender_confirm": (5, 600)}   # (한도, 창 초)
class OnboardingRedisLimiter(OnboardingLimiterPort):   __init__(redis: Redis)
    # 키 notification:onboarding:{action}:{shop_id} → INCR + EXPIRE nx(창은 처음 셀 때만). count <= 한도.
    # RedisError 면 WARNING 뒤 True(통과). 모르는 action 은 KeyError(호출자는 네 값만 넘긴다)

# notification.dependencies.notification_wiring (더한 것)
def build_onboarding_limiter() -> OnboardingLimiterPort          # OnboardingRedisLimiter(get_redis())

# notification.adapter.inbound.api.error_map — 바뀌지 않음. main.py 의 install_error_handlers 에 등록됨:
NOTIFICATION_ERROR_STATUS = {NotificationInputError: 422, ChannelNotLinkedError: 409, ChannelAlreadyLinkedError: 409,
    TokenInvalidError: 400, SenderNotVerifiedError: 409, TemplateNotApprovedError: 409, MessageAlreadyPendingError: 409,
    MessageNotFoundError: 404, MessageNotRetryableError: 409, TooManyNotificationRequestsError: 429, ProviderUnavailableError: 502}

# notification.app.dtos
@dataclass(frozen=True) class NotificationOverviewView: channel: NotificationChannel | None; settings: NotificationSettings | None; templates: list[NotificationTemplate]
@dataclass(frozen=True) class NotificationMyselfQuery: id: int; name: str
@dataclass(frozen=True) class NotificationMyselfResponse: id: int; name: str; introduction: str
@dataclass(frozen=True) class GetNotificationOverviewQuery: ctx: ShopContext
@dataclass(frozen=True) class RequestChannelTokenCommand: ctx; search_id: str; admin_phone: str; category_code: str
@dataclass(frozen=True) class LinkChannelCommand: ctx; search_id: str; admin_phone: str; category_code: str; token: str
@dataclass(frozen=True) class UnlinkChannelCommand: ctx
@dataclass(frozen=True) class UpdateNotificationSettingsCommand: ctx; settings: NotificationSettings; sms_fallback_enabled: bool
@dataclass(frozen=True) class RequestSenderVerificationCommand: ctx; phone: str
@dataclass(frozen=True) class ConfirmSenderCommand: ctx; phone: str; code: str

# notification.app.ports.input — 슬라이스마다 하나, 메서드 이름 = 슬라이스 이름
class NotificationMyselfUseCase:          async def introduce_myself(query: NotificationMyselfQuery) -> NotificationMyselfResponse
class GetNotificationOverviewUseCase:     async def get_notification_overview(query) -> NotificationOverviewView
class RequestChannelTokenUseCase:         async def request_channel_token(command) -> None
class LinkChannelUseCase:                 async def link_channel(command) -> NotificationOverviewView
class UnlinkChannelUseCase:               async def unlink_channel(command) -> None
class UpdateNotificationSettingsUseCase:  async def update_notification_settings(command) -> NotificationOverviewView
class RequestSenderVerificationUseCase:   async def request_sender_verification(command) -> None
class ConfirmSenderUseCase:               async def confirm_sender(command) -> NotificationOverviewView

# notification.app.use_cases — 인터랙터 일곱 + myself
NotificationMyselfInteractor(record: NotificationMyselfRecordPort)                       # id 7, "알림 (notification)"
GetNotificationOverviewInteractor(channels, settings, templates)
RequestChannelTokenInteractor(channels, gateway, limiter)
    # linked → ChannelAlreadyLinkedError → allow("token") → gateway.request_channel_token(GatewayError → ProviderUnavailableError)
    # → channels.save(없으면 새 줄 / 있으면 status=token_requested, provider="solapi", provider_channel_id=None, linked_at=None; 발신번호·인증 시각·sms_fallback_enabled 그대로)
LinkChannelInteractor(channels, settings, templates, gateway, limiter, now)
    # linked → ChannelAlreadyLinkedError; token_requested 아님 → ChannelNotLinkedError("먼저 인증번호를 받아 주세요.") → allow("link")
    # → gateway.link_channel(TokenInvalidError 그대로, GatewayError → ProviderUnavailableError) → DEFAULT_KINDS 마다 register_template(실패는 건너뜀)
    # → channels.save(linked, provider_channel_id, linked_at=now) → settings.ensure → templates.upsert(kind, TEXT_VERSION, id, now) → load_overview
UnlinkChannelInteractor(channels, templates, messages, now)
    # linked 아님 → ChannelNotLinkedError → save(unlinked, unlinked_at=now, provider_channel_id=None) → templates.delete_all → messages.cancel_pending("channel_unlinked")
UpdateNotificationSettingsInteractor(channels, settings, templates, messages, gateway, now)
    # check_settings → linked 아님 → ChannelNotLinkedError → sms_fallback_enabled and 인증 없음 → SenderNotVerifiedError → current = settings.ensure
    # → (next_visit_enabled 이고 템플릿 없으면) register_template(HTTP, 저장 전) → settings.update
    # → ① 꺼진 종류(KINDS 중 enabled_for 가 False, change 가 꺼지면 cancel 도) cancel_pending("setting_off", kinds=…)
    # → ② reminder_time 이 바뀌면 list_pending(reminder) 마다 reminder_at(variables["starts_at"], new, tz, now) — None 이면 cancel_pending("too_late", visit_id, (reminder,)), 아니면 save(scheduled_at)
    #      list_pending(next_visit) 마다 next_visit_at(variables["completed_at"], int(variables["interval_weeks"]), new, tz) 로 save
    # → ③ 등록했으면 templates.upsert(next_visit, …) → ④ 바뀌었으면 channels.save(sms_fallback_enabled) → load_overview
RequestSenderVerificationInteractor(channels, gateway, limiter)      # linked 필요 → allow("sender_verification") → gateway(…) ; 저장 없음
ConfirmSenderInteractor(channels, settings, templates, gateway, limiter, now)
    # linked 필요 → allow("sender_confirm") → gateway.confirm_sender_verification(TokenInvalidError 그대로) → save(sender_number=phone, sender_number_verified_at=now) → load_overview

# notification.app.services
async def load_overview(ctx, channels, settings, templates) -> NotificationOverviewView        # overview.py
async def register_template(gateway, provider_channel_id: str, kind: str) -> str | None       # template_registration.py — GatewayError 면 WARNING("notification.onboarding") 뒤 None

# notification.adapter.inbound.api.schemas
class NotificationOverviewSchema(BaseModel):  channel: NotificationChannelSchema; settings: NotificationSettingsSchema | None; templates: list[NotificationTemplateSchema]
    @classmethod def of(cls, view: NotificationOverviewView, tz: str) -> NotificationOverviewSchema   # 라우터가 ctx.timezone 을 넘긴다
class RequestChannelTokenRequestSchema / ChannelTokenRequestedSchema(status: Literal["token_requested"])
class LinkChannelRequestSchema / UpdateNotificationSettingsRequestSchema(.to_settings() -> NotificationSettings)
class RequestSenderVerificationRequestSchema / SenderVerificationRequestedSchema(status: Literal["verification_requested"]) / ConfirmSenderRequestSchema

# notification.adapter.inbound.api.v1 — APIRouter(prefix="/v1/shops", tags=["notifications"])
notification_myself_router · get_notification_overview_router · request_channel_token_router · link_channel_router
unlink_channel_router · update_notification_settings_router · request_sender_verification_router · confirm_sender_router

# notification.dependencies — 프로바이더 여덟. 업체·Redis 가 필요한 것은 Depends(get_message_gateway)·build_onboarding_limiter()
get_notification_myself_use_case() · get_get_notification_overview_use_case(db) · get_request_channel_token_use_case(db, gateway)
get_link_channel_use_case(db, gateway) · get_unlink_channel_use_case(db) · get_update_notification_settings_use_case(db, gateway)
get_request_sender_verification_use_case(db, gateway) · get_confirm_sender_use_case(db, gateway)
# 테스트에서 게이트웨이 바꾸기: main.app.dependency_overrides[get_message_gateway] = lambda: fake  (끝나면 pop)

# notification.tests.helpers
class FakeOnboardingLimiter(OnboardingLimiterPort):  __init__(allowed=True); allowed; calls: list[tuple[int, str]]   # fakes.py
api.py: StubShopAccess · OWNER · STAFF · build_app(router, provider, stub, access=None) · client(app) · error_of · Recorder   # visit 과 같다
onboarding_world.py: NOW = kst(10, 14, 11); class OnboardingWorld(linked=True, now=NOW)
    # .channels .settings .templates .messages .gateway(SpyGateway) .limiter(FakeOnboardingLimiter) .journal
    # 인터랙터: .overview .token .link .unlink .update_settings .sender_verification .confirm_sender ; .template_ids() -> [(kind, status)]
```

매장이 연동하는 화면의 백엔드 전부다(설계 6.2·7.1). 경로 여덟이 전부 `shop:update`(사장). 연동은 토큰 신청 → 연동 (업체 연동 + 템플릿 다섯 등록 → 그 뒤 저장 — **업체 호출을 저장 전에 해 행 잠금을 쥔 채 HTTP 를 부르지 않는다**, N14) → 디스패처가 10분마다 승인 여부를 당겨 온다. 설정 PUT 은 전체 교체이고 후속 셋 — 꺼진 종류의 대기 줄 `setting_off` 취소, 리마인드 시각이 바뀌면 대기 리마인드 재계산(지났으면 `too_late`), 다음 예약 제안을 켜면 템플릿 여섯째 등록. 문자 대체는 발신번호 인증 뒤에만 켤 수 있다(409). 횟수 제한은 Redis 고정 창(토큰·인증 시작 매장당 5/시간, 연동·인증 확인 5/10분, Redis 장애 때 통과). 첫 통합 테스트는 테넌트 격리(다른 매장의 사장은 403). `MessageAlreadyPendingError` 가 오류 표에 등록되어 발행 쪽 중복 호출이 500 이 아니라 409 로 드러난다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/adapter/test_confirm_sender_router.py`:

```python
import pytest

from notification.adapter.inbound.api.v1.confirm_sender_router import confirm_sender_router
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.confirm_sender_provider import get_confirm_sender_use_case
from notification.domain.errors import TokenInvalidError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import channel, kst, settings

PATH = "/v1/shops/3/notification/sender"
BODY = {"phone": "0212345678", "code": "000000"}
VIEW = NotificationOverviewView(
    channel=channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9)), settings=settings(),
    templates=[])


def _app(stub, access=None):
    return build_app(confirm_sender_router, get_confirm_sender_use_case, stub, access)


async def test_사장은_인증번호로_발신번호를_확인하고_overview_를_받는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json=BODY)
    assert response.status_code == 200
    assert (response.json()["channel"]["sender_number"], response.json()["channel"]["sender_verified"]) == (
        "0212345678", True)
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].phone, stub.calls[0].code) == (3, "0212345678", "000000")


async def test_직원은_확인하지_못한다():
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post(PATH, json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "code": v} for v in ("00000", "0000000", "abcdef", "", 0, None)),
    *({**BODY, "phone": v} for v in ("12345678", "010-1234-5678", "")),
    {"phone": "0212345678"}, {"code": "000000"}, {}, None,
], ids=str)
async def test_여섯_자리가_아닌_인증번호와_잘못된_번호는_422_다(bad):
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


async def test_틀린_인증번호는_400_이다():
    async with client(_app(Recorder(error=TokenInvalidError("틀림")))) as c:
        response = await c.post(PATH, json=BODY)
    assert error_of(response) == (400, "NOTIFICATION_TOKEN_INVALID")
```

`backend/apps/notification/tests/adapter/test_get_notification_overview_router.py`:

```python
"""한눈에 보기 — 소속이면 읽는다. 시각은 매장 시간대, 업체 ID 는 내보내지 않는다(N12)."""
from notification.adapter.inbound.api.v1.get_notification_overview_router import get_notification_overview_router
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.get_notification_overview_provider import get_get_notification_overview_use_case
from notification.domain.value_objects.template_status import REJECTED
from notification.tests.helpers.api import STAFF, Recorder, build_app, client
from notification.tests.helpers.builders import channel, kst, settings, template

CHANNEL = {"status": "linked", "linked_at": "2026-10-01T10:00:00+09:00", "sender_number": None,
           "sender_verified": False, "sms_fallback_enabled": False}
SETTINGS = {"confirm_enabled": True, "reminder_enabled": True, "report_enabled": True, "change_enabled": True,
            "next_visit_enabled": False, "reminder_time": "18:00", "next_visit_after_weeks": None,
            "next_visit_cooldown_days": 30}
TEMPLATES = [
    {"kind": "confirm", "status": "approved", "rejected_reason": None, "requested_at": "2026-10-01T10:00:00+09:00",
     "decided_at": "2026-10-02T10:00:00+09:00"},
    {"kind": "reminder", "status": "rejected", "rejected_reason": "변수 비중", "requested_at": "2026-10-01T10:00:00+09:00",
     "decided_at": "2026-10-02T10:00:00+09:00"},
]


def _app(view, access=None):
    return build_app(get_notification_overview_router, get_get_notification_overview_use_case, Recorder(view), access)


async def test_직원도_한눈에_보기를_보고_시각은_매장_시간대다():
    view = NotificationOverviewView(
        channel=channel(), settings=settings(),
        templates=[template(), template(id=2, kind="reminder", provider_template_id="KA01TP0002", status=REJECTED,
                                        rejected_reason="변수 비중")])
    async with client(_app(view, STAFF)) as c:
        response = await c.get("/v1/shops/3/notification")
    assert response.status_code == 200
    assert response.json() == {"channel": CHANNEL, "settings": SETTINGS, "templates": TEMPLATES}
    for secret in ("provider_channel_id", "provider_template_id", "KA01PF0001", "KA01TP0001"):
        assert secret not in response.text


async def test_연동_전엔_채널_none_설정_null_템플릿_빈_목록이다():
    async with client(_app(NotificationOverviewView(channel=None, settings=None, templates=[]))) as c:
        response = await c.get("/v1/shops/3/notification")
    assert response.json() == {
        "channel": {"status": "none", "linked_at": None, "sender_number": None, "sender_verified": False,
                    "sms_fallback_enabled": False},
        "settings": None, "templates": []}


async def test_발신번호를_인증했으면_번호와_인증_여부가_보인다():
    view = NotificationOverviewView(
        channel=channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9), sms_fallback_enabled=True),
        settings=settings(), templates=[])
    async with client(_app(view)) as c:
        body = (await c.get("/v1/shops/3/notification")).json()
    assert body["channel"] == {**CHANNEL, "sender_number": "0212345678", "sender_verified": True,
                               "sms_fallback_enabled": True}
```

`backend/apps/notification/tests/adapter/test_link_channel_router.py`:

```python
import pytest

from notification.adapter.inbound.api.v1.link_channel_router import link_channel_router
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.link_channel_provider import get_link_channel_use_case
from notification.domain.errors import ChannelNotLinkedError, TokenInvalidError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import channel, settings, template

BODY = {"search_id": "hisshaus", "admin_phone": "01012345678", "category_code": "003001", "token": "000000"}
VIEW = NotificationOverviewView(channel=channel(), settings=settings(), templates=[template(status="pending",
                                                                                            decided_at=None)])


def _app(stub, access=None):
    return build_app(link_channel_router, get_link_channel_use_case, stub, access)


async def test_사장은_토큰으로_연동하고_overview_를_받는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=BODY)
    body = response.json()
    assert response.status_code == 200
    assert (body["channel"]["status"], body["settings"]["reminder_time"], body["templates"][0]["status"]) == (
        "linked", "18:00", "pending")
    [command] = stub.calls
    assert (command.ctx.shop_id, command.search_id, command.admin_phone, command.category_code, command.token) == (
        3, "hisshaus", "01012345678", "003001", "000000")
    assert "KA01PF0001" not in response.text and "KA01TP0001" not in response.text


async def test_직원은_연동하지_못한다():
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "token": v} for v in ("00000", "0000000", "abcdef", "00000a", "", 0, None)),
    {k: v for k, v in BODY.items() if k != "token"},
    {**BODY, "admin_phone": "010-1234-5678"},
    {**BODY, "search_id": ""},
], ids=str)
async def test_여섯_자리가_아닌_토큰과_잘못된_칸은_422_다(bad):
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (TokenInvalidError("틀림"), (400, "NOTIFICATION_TOKEN_INVALID")),
    (ChannelNotLinkedError("먼저 인증번호를 받아 주세요"), (409, "NOTIFICATION_CHANNEL_NOT_LINKED")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=BODY)
    assert error_of(response) == expected
```

`backend/apps/notification/tests/adapter/test_notification_myself_router.py`:

```python
from notification.adapter.inbound.api.v1.notification_myself_router import notification_myself_router
from notification.app.dtos.notification_myself_dto import NotificationMyselfResponse
from notification.dependencies.notification_myself_provider import get_notification_myself_use_case
from notification.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_멤버는_자기소개를_본다():
    stub = Recorder(NotificationMyselfResponse(id=7, name="알림 (notification)", introduction="소개"))
    async with client(build_app(notification_myself_router, get_notification_myself_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/notification/myself")
    assert response.json() == {"id": 7, "name": "알림 (notification)", "introduction": "소개"}
    assert stub.calls[0].id == 7
```

`backend/apps/notification/tests/adapter/test_onboarding_redis_limiter.py`:

```python
"""온보딩 횟수 제한(설계 9.4, N3·N4) — 동작마다 창과 한도가 따로다. Redis 에 닿지 못하면 통과시키고 경고만 남긴다."""
import logging

import pytest
from redis.asyncio import from_url
from redis.exceptions import ConnectionError as RedisConnectionError

from core.config import REDIS_URL
from notification.adapter.outbound.redis.onboarding_redis_limiter import OnboardingRedisLimiter

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    client = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest.mark.parametrize("action", ["token", "link", "sender_verification", "sender_confirm"])
async def test_동작마다_5번까지_받고_6번째부터_막는다(redis, action):
    limiter = OnboardingRedisLimiter(redis)
    assert [await limiter.allow(7, action) for _ in range(7)] == [True] * 5 + [False, False]


@pytest.mark.parametrize("action, window", [
    ("token", 3600), ("sender_verification", 3600), ("link", 600), ("sender_confirm", 600),
])
async def test_키는_동작과_매장으로_나뉘고_창은_처음_셀_때만_잡힌다(redis, action, window):
    limiter = OnboardingRedisLimiter(redis)
    await limiter.allow(7, action)
    key = f"notification:onboarding:{action}:7"
    assert await redis.get(key) == "1" and window - 5 < await redis.ttl(key) <= window
    await redis.expire(key, 30)
    await limiter.allow(7, action)
    assert await redis.get(key) == "2" and 0 < await redis.ttl(key) <= 30


async def test_매장마다_동작마다_따로_센다(redis):
    limiter = OnboardingRedisLimiter(redis)
    for _ in range(6):
        await limiter.allow(7, "token")
    assert await limiter.allow(8, "token") is True
    assert await limiter.allow(7, "link") is True
    assert await limiter.allow(7, "token") is False


async def test_창이_지나면_다시_받는다(redis):
    """기다리지 않는다 — 창이 끝난 것은 키가 사라진 것이다."""
    limiter = OnboardingRedisLimiter(redis)
    for _ in range(6):
        await limiter.allow(7, "link")
    assert await limiter.allow(7, "link") is False
    await redis.delete("notification:onboarding:link:7")
    assert await limiter.allow(7, "link") is True


class _DeadRedis:
    """닿지 않는 Redis — 명령을 실행하는 순간 연결 오류가 난다."""

    def pipeline(self, transaction=True):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __getattr__(self, name):
        return lambda *args, **kwargs: None

    async def execute(self):
        raise RedisConnectionError("Error connecting to redis:6379")


async def test_Redis_에_닿지_못하면_통과시키고_경고를_남긴다(caplog):
    limiter = OnboardingRedisLimiter(_DeadRedis())
    with caplog.at_level(logging.WARNING):
        assert await limiter.allow(7, "token") is True
    assert [r.levelname for r in caplog.records] == ["WARNING"]
```

`backend/apps/notification/tests/adapter/test_request_channel_token_router.py`:

```python
import pytest

from notification.adapter.inbound.api.v1.request_channel_token_router import request_channel_token_router
from notification.dependencies.request_channel_token_provider import get_request_channel_token_use_case
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

BODY = {"search_id": "hisshaus", "admin_phone": "01012345678", "category_code": "003001"}


def _without(key: str) -> dict:
    return {k: v for k, v in BODY.items() if k != key}


def _app(stub, access=None):
    return build_app(request_channel_token_router, get_request_channel_token_use_case, stub, access)


async def test_사장은_토큰을_신청한다_202():
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=BODY)
    assert (response.status_code, response.json()) == (202, {"status": "token_requested"})
    [command] = stub.calls
    assert (command.ctx.shop_id, command.search_id, command.admin_phone, command.category_code) == (
        3, "hisshaus", "01012345678", "003001")


async def test_직원은_신청하지_못한다():
    """N18"""
    stub = Recorder(None)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "search_id": v} for v in ("", "a" * 101, "a b", "a\x00b", 12, None)),
    *({**BODY, "admin_phone": v} for v in ("010-1234-5678", "0212345678", "", "0101234567a", 1012345678, None)),
    *({**BODY, "category_code": v} for v in ("", "a" * 21, None)),
    _without("search_id"), _without("admin_phone"), _without("category_code"),
    {}, [], "문자열", None,
], ids=str)
async def test_빈_값_너무_긴_값_번호_형식_빠진_칸은_422_다(bad):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (ChannelAlreadyLinkedError("이미 연동"), (409, "NOTIFICATION_CHANNEL_LINKED")),
    (TooManyNotificationRequestsError("너무 잦음"), (429, "NOTIFICATION_RATE_LIMITED")),
    (ProviderUnavailableError("업체 오류"), (502, "NOTIFICATION_PROVIDER_UNAVAILABLE")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=BODY)
    assert error_of(response) == expected
```

`backend/apps/notification/tests/adapter/test_request_sender_verification_router.py`:

```python
import pytest

from notification.adapter.inbound.api.v1.request_sender_verification_router import (
    request_sender_verification_router,
)
from notification.dependencies.request_sender_verification_provider import (
    get_request_sender_verification_use_case,
)
from notification.domain.errors import TooManyNotificationRequestsError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

PATH = "/v1/shops/3/notification/sender/verification"


def _app(stub, access=None):
    return build_app(request_sender_verification_router, get_request_sender_verification_use_case, stub, access)


@pytest.mark.parametrize("phone", ["0212345678", "01012345678", "021234567"])
async def test_사장은_휴대폰이든_유선이든_발신번호_인증을_시작한다_202(phone):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json={"phone": phone})
    assert (response.status_code, response.json()) == (202, {"status": "verification_requested"})
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].phone) == (3, phone)


async def test_직원은_시작하지_못한다():
    stub = Recorder(None)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post(PATH, json={"phone": "0212345678"})
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({"phone": v} for v in ("12345678", "010123456789", "010-1234-5678", "", "0212345678a", 212345678, None)),
    {}, [], None,
], ids=str)
async def test_8자리_12자리_하이픈_빈_값은_422_다(bad):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


async def test_횟수_제한은_429_다():
    async with client(_app(Recorder(error=TooManyNotificationRequestsError("너무 잦음")))) as c:
        response = await c.post(PATH, json={"phone": "0212345678"})
    assert error_of(response) == (429, "NOTIFICATION_RATE_LIMITED")
```

`backend/apps/notification/tests/adapter/test_unlink_channel_router.py`:

```python
from notification.adapter.inbound.api.v1.unlink_channel_router import unlink_channel_router
from notification.dependencies.unlink_channel_provider import get_unlink_channel_use_case
from notification.domain.errors import ChannelNotLinkedError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


def _app(stub, access=None):
    return build_app(unlink_channel_router, get_unlink_channel_use_case, stub, access)


async def test_사장은_연동을_해제한다_204():
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.delete("/v1/shops/3/notification/channel")
    assert (response.status_code, response.content) == (204, b"")
    assert stub.calls[0].ctx.shop_id == 3


async def test_직원은_해제하지_못한다():
    stub = Recorder(None)
    async with client(_app(stub, STAFF)) as c:
        response = await c.delete("/v1/shops/3/notification/channel")
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


async def test_연동되지_않았으면_409_다():
    async with client(_app(Recorder(error=ChannelNotLinkedError("연동 전")))) as c:
        response = await c.delete("/v1/shops/3/notification/channel")
    assert error_of(response) == (409, "NOTIFICATION_CHANNEL_NOT_LINKED")
```

`backend/apps/notification/tests/adapter/test_update_notification_settings_router.py`:

```python
from datetime import time

import pytest

from notification.adapter.inbound.api.v1.update_notification_settings_router import (
    update_notification_settings_router,
)
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.update_notification_settings_provider import (
    get_update_notification_settings_use_case,
)
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.errors import ChannelNotLinkedError, NotificationInputError, SenderNotVerifiedError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import channel, settings

BODY = {"confirm_enabled": True, "reminder_enabled": False, "report_enabled": True, "change_enabled": True,
        "next_visit_enabled": True, "reminder_time": "09:30", "next_visit_after_weeks": 6,
        "next_visit_cooldown_days": 45, "sms_fallback_enabled": False}
FLAGS = ("confirm_enabled", "reminder_enabled", "report_enabled", "change_enabled", "next_visit_enabled",
         "sms_fallback_enabled")
VIEW = NotificationOverviewView(channel=channel(), settings=settings(), templates=[])


def _without(key: str) -> dict:
    return {k: v for k, v in BODY.items() if k != key}


def _app(stub, access=None):
    return build_app(update_notification_settings_router, get_update_notification_settings_use_case, stub, access)


async def test_사장은_설정_전체를_바꾸고_overview_를_받는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=BODY)
    assert response.status_code == 200 and response.json()["settings"]["reminder_time"] == "18:00"
    [command] = stub.calls
    assert command.ctx.shop_id == 3 and command.sms_fallback_enabled is False
    assert command.settings == NotificationSettings(
        confirm_enabled=True, reminder_enabled=False, report_enabled=True, change_enabled=True,
        next_visit_enabled=True, reminder_time=time(9, 30), next_visit_after_weeks=6, next_visit_cooldown_days=45)


async def test_주기를_비우면_None_이고_문자_대체를_켤_수_있다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        await c.put("/v1/shops/3/notification/settings",
                    json={**BODY, "next_visit_after_weeks": None, "sms_fallback_enabled": True})
    assert stub.calls[0].settings.next_visit_after_weeks is None and stub.calls[0].sms_fallback_enabled is True


async def test_직원은_설정을_바꾸지_못한다():
    """N18"""
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, flag: value} for flag in FLAGS for value in ("true", 1, 0, None)),
    *(_without(flag) for flag in FLAGS),
    *({**BODY, "reminder_time": v} for v in ("18:00:00", "25:00", "18:60", "9:00", "", "18시", None, 1800)),
    _without("reminder_time"),
    *({**BODY, "next_visit_after_weeks": v} for v in ("4", -1, 4.5, True)),
    _without("next_visit_after_weeks"),
    *({**BODY, "next_visit_cooldown_days": v} for v in ("30", -1, 30.5, None, True)),
    _without("next_visit_cooldown_days"),
    {}, [], "문자열", None,
], ids=str)
async def test_불리언_문자열_시각_형식_정수_아닌_값_빠진_칸은_422_다(bad):
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (NotificationInputError("범위 밖"), (422, "VALIDATION_ERROR")),
    (SenderNotVerifiedError("인증 먼저"), (409, "NOTIFICATION_SENDER_NOT_VERIFIED")),
    (ChannelNotLinkedError("연동 먼저"), (409, "NOTIFICATION_CHANNEL_NOT_LINKED")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=BODY)
    assert error_of(response) == expected
```

`backend/apps/notification/tests/app/use_cases/test_confirm_sender_interactor.py`:

```python
"""발신번호 확인 — 맞으면 번호와 인증 시각을 적고 overview, 틀리면 400, 횟수 제한 429."""
import pytest

from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import UNLINKED
from notification.tests.helpers.builders import channel, ctx
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld

COMMAND = ConfirmSenderCommand(ctx=ctx(), phone="0212345678", code="000000")


async def test_맞는_인증번호면_발신번호와_인증_시각을_적고_overview_를_돌려준다():
    world = OnboardingWorld()
    view = await world.confirm_sender.confirm_sender(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.sender_number, saved.sender_number_verified_at, saved.status) == ("0212345678", NOW, "linked")
    assert (view.channel.sender_number, view.settings is not None, len(view.templates)) == ("0212345678", True, 5)
    assert world.gateway.calls == [("confirm_sender_verification", "0212345678")]
    assert world.limiter.calls == [(1, "sender_confirm")]


async def test_틀린_인증번호면_400_이고_아무것도_적지_않는다():
    world = OnboardingWorld()
    with pytest.raises(TokenInvalidError):
        await world.confirm_sender.confirm_sender(ConfirmSenderCommand(ctx=ctx(), phone="0212345678", code="111111"))
    assert world.channels.rows[1].sender_number is None and world.limiter.calls == [(1, "sender_confirm")]


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = OnboardingWorld()
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.confirm_sender.confirm_sender(COMMAND)
    assert world.gateway.calls == []


@pytest.mark.parametrize("status", [None, UNLINKED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.confirm_sender.confirm_sender(COMMAND)


async def test_업체_오류는_502_다():
    world = OnboardingWorld()

    async def failing(phone, code):
        raise GatewayTransientError("timeout")

    world.gateway.confirm_sender_verification = failing
    with pytest.raises(ProviderUnavailableError):
        await world.confirm_sender.confirm_sender(COMMAND)
    assert world.channels.rows[1].sender_number is None
```

`backend/apps/notification/tests/app/use_cases/test_get_notification_overview_interactor.py`:

```python
"""한눈에 보기 — 채널·설정·템플릿(종류 순)을 읽기만 한다. 연동 전엔 채널 None·설정 None·템플릿 빈 목록."""
from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.domain.value_objects.message_kind import DEFAULT_KINDS
from notification.tests.helpers.builders import ctx
from notification.tests.helpers.onboarding_world import OnboardingWorld


async def test_연동된_매장은_채널_설정_템플릿을_종류_순으로_본다():
    world = OnboardingWorld()
    view = await world.overview.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx()))
    assert view.channel == world.channels.rows[1] and view.settings == world.settings.rows[1]
    assert [t.kind for t in view.templates] == list(DEFAULT_KINDS)


async def test_연동_전엔_전부_비어_있고_아무것도_쓰지_않는다():
    world = OnboardingWorld(linked=False)
    view = await world.overview.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx()))
    assert (view.channel, view.settings, view.templates) == (None, None, [])
    assert world.journal == []


async def test_다른_매장의_것은_보지_않는다():
    world = OnboardingWorld()
    view = await world.overview.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx(shop_id=2)))
    assert (view.channel, view.settings, view.templates) == (None, None, [])
```

`backend/apps/notification/tests/app/use_cases/test_link_channel_interactor.py`:

```python
"""연동 — token_requested 에서만, 틀린 토큰 400, 성공하면 linked·설정 기본값·기본 5종 템플릿 등록(하나 실패해도 계속)."""
import logging

import pytest

from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.ports.output.message_gateway_port import GatewayPermanentError, GatewayTransientError
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TokenInvalidError,
    TooManyNotificationRequestsError,
)
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.channel_status import LINKED, TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, DEFAULT_KINDS, REMINDER, REPORT
from notification.domain.value_objects.template_status import PENDING
from notification.tests.helpers.builders import channel, ctx, kst
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld

COMMAND = LinkChannelCommand(ctx=ctx(), search_id="hisshaus", admin_phone="01012345678", category_code="003001",
                             token="000000")


def _requested() -> OnboardingWorld:
    world = OnboardingWorld(linked=False)
    world.channels.rows[1] = channel(status=TOKEN_REQUESTED, provider_channel_id=None, linked_at=None)
    return world


async def test_맞는_토큰이면_linked_가_되고_설정_기본값과_기본_5종_템플릿이_pending_으로_생긴다():
    world = _requested()
    view = await world.link.link_channel(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.status, saved.provider_channel_id, saved.linked_at) == (LINKED, "pf-hisshaus", NOW)
    assert world.settings.rows[1].reminder_time.strftime("%H:%M") == "18:00"
    assert world.template_ids() == [(kind, PENDING) for kind in DEFAULT_KINDS]
    assert world.templates.rows[(1, CONFIRM)].provider_template_id == f"tpl-pf-hisshaus-{CONFIRM}-v{TEXT_VERSION}"
    assert world.templates.rows[(1, CONFIRM)].text_version == TEXT_VERSION
    assert all(t.requested_at == NOW for t in world.templates.rows.values())
    assert (view.channel.status, view.settings is not None, [t.kind for t in view.templates]) == (
        LINKED, True, list(DEFAULT_KINDS))
    assert ("link_channel", "hisshaus", "01012345678", "003001") in world.gateway.calls
    assert world.limiter.calls == [(1, "link")]


async def test_업체_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다():
    world = _requested()
    await world.link.link_channel(COMMAND)
    names = [entry[0] for entry in world.journal]
    assert names.index("register_template") < names.index("save_channel")
    assert names.index("save_channel") < names.index("ensure_settings") < names.index("upsert_template")


async def test_틀린_토큰이면_400_이고_채널은_token_requested_그대로다():
    world = _requested()
    with pytest.raises(TokenInvalidError):
        await world.link.link_channel(LinkChannelCommand(**{**COMMAND.__dict__, "token": "123456"}))
    assert world.channels.rows[1].status == TOKEN_REQUESTED
    assert world.template_ids() == [] and 1 not in world.settings.rows
    assert world.limiter.calls == [(1, "link")]


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = _requested()
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.link.link_channel(COMMAND)
    assert world.gateway.calls == []


@pytest.mark.parametrize("status", [None, UNLINKED])
async def test_토큰을_받지_않은_매장은_409_NOT_LINKED_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status, provider_channel_id=None, linked_at=None)
    with pytest.raises(ChannelNotLinkedError):
        await world.link.link_channel(COMMAND)
    assert world.gateway.calls == []


async def test_이미_연동된_매장은_409_LINKED_다():
    world = OnboardingWorld()
    with pytest.raises(ChannelAlreadyLinkedError):
        await world.link.link_channel(COMMAND)
    assert world.gateway.calls == []


async def test_연동_호출의_업체_오류는_502_다():
    world = _requested()

    async def failing(*args):
        raise GatewayTransientError("timeout")

    world.gateway.link_channel = failing
    with pytest.raises(ProviderUnavailableError):
        await world.link.link_channel(COMMAND)
    assert world.channels.rows[1].status == TOKEN_REQUESTED


async def test_템플릿_등록_하나가_실패하면_그_종류만_빼고_넷을_등록하고_경고만_남긴다(caplog):
    world = _requested()
    original = world.gateway.register_template

    async def flaky(provider_channel_id, template, text_version):
        if template.kind == REPORT:
            raise GatewayPermanentError("400")
        return await original(provider_channel_id, template, text_version)

    world.gateway.register_template = flaky
    with caplog.at_level(logging.WARNING):
        view = await world.link.link_channel(COMMAND)
    assert world.channels.rows[1].status == LINKED
    assert world.template_ids() == [(k, PENDING) for k in (CONFIRM, REMINDER, CHANGE, CANCEL)]
    assert [t.kind for t in view.templates] == [CONFIRM, REMINDER, CHANGE, CANCEL]
    assert [r.levelname for r in caplog.records] == ["WARNING"] and REPORT in caplog.text
```

`backend/apps/notification/tests/app/use_cases/test_request_channel_token_interactor.py`:

```python
"""토큰 신청 — 연동된 매장은 409, 횟수 제한 429, 업체 오류 502, 성공하면 채널 줄을 token_requested 로 upsert."""
import pytest

from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand
from notification.app.ports.output.message_gateway_port import GatewayPermanentError, GatewayTransientError
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED, UNLINKED
from notification.tests.helpers.builders import channel, ctx, kst
from notification.tests.helpers.onboarding_world import OnboardingWorld

COMMAND = RequestChannelTokenCommand(ctx=ctx(), search_id="hisshaus", admin_phone="01012345678",
                                     category_code="003001")


async def test_처음_신청하면_채널_줄이_token_requested_로_생기고_업체에_토큰을_신청한다():
    world = OnboardingWorld(linked=False)
    await world.token.request_channel_token(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.shop_id, saved.status, saved.provider, saved.provider_channel_id, saved.linked_at) == (
        1, TOKEN_REQUESTED, "solapi", None, None)
    assert saved.sms_fallback_enabled is False and saved.sender_number is None
    assert world.gateway.calls == [("request_channel_token", "hisshaus", "01012345678", "003001")]
    assert world.limiter.calls == [(1, "token")]


async def test_해제된_매장이_다시_신청하면_되살린다_발신번호와_문자_대체는_남는다():
    world = OnboardingWorld(linked=False)
    world.channels.rows[1] = channel(status=UNLINKED, provider_channel_id=None, linked_at=None,
                                     unlinked_at=kst(10, 10, 9), sender_number="0212345678",
                                     sender_number_verified_at=kst(10, 5, 9), sms_fallback_enabled=True)
    await world.token.request_channel_token(COMMAND)
    saved = world.channels.rows[1]
    assert (saved.status, saved.provider_channel_id, saved.linked_at) == (TOKEN_REQUESTED, None, None)
    assert (saved.sender_number, saved.sender_number_verified_at, saved.sms_fallback_enabled) == (
        "0212345678", kst(10, 5, 9), True)


async def test_연동된_매장이_다시_신청하면_409_이고_업체를_부르지_않는다():
    world = OnboardingWorld()
    with pytest.raises(ChannelAlreadyLinkedError):
        await world.token.request_channel_token(COMMAND)
    assert world.gateway.calls == [] and world.limiter.calls == []
    assert world.channels.rows[1].status == "linked"


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = OnboardingWorld(linked=False)
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.token.request_channel_token(COMMAND)
    assert world.gateway.calls == [] and 1 not in world.channels.rows


@pytest.mark.parametrize("error", [GatewayTransientError("timeout"), GatewayPermanentError("401")])
async def test_업체_오류는_502_이고_채널_줄을_만들지_않는다(error):
    world = OnboardingWorld(linked=False)

    async def failing(*args):
        raise error

    world.gateway.request_channel_token = failing
    with pytest.raises(ProviderUnavailableError):
        await world.token.request_channel_token(COMMAND)
    assert 1 not in world.channels.rows


async def test_관리자_번호와_검색_아이디는_저장하지_않는다():
    world = OnboardingWorld(linked=False)
    await world.token.request_channel_token(COMMAND)
    assert "01012345678" not in repr(world.channels.rows[1]) and "hisshaus" not in repr(world.channels.rows[1])
```

`backend/apps/notification/tests/app/use_cases/test_request_sender_verification_interactor.py`:

```python
"""발신번호 인증 시작 — linked 필요, 횟수 제한, 업체 오류 502. 아무것도 저장하지 않는다."""
import pytest

from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED
from notification.tests.helpers.builders import channel, ctx
from notification.tests.helpers.onboarding_world import OnboardingWorld

COMMAND = RequestSenderVerificationCommand(ctx=ctx(), phone="0212345678")


async def test_업체에_인증을_요청하고_저장은_하지_않는다():
    world = OnboardingWorld()
    before = world.channels.rows[1]
    await world.sender_verification.request_sender_verification(COMMAND)
    assert world.gateway.calls == [("request_sender_verification", "0212345678")]
    assert world.channels.rows[1] == before and ("save_channel", 1, "linked") not in world.journal
    assert world.limiter.calls == [(1, "sender_verification")]


@pytest.mark.parametrize("status", [None, TOKEN_REQUESTED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.sender_verification.request_sender_verification(COMMAND)
    assert world.gateway.calls == []


async def test_횟수_제한에_걸리면_429_이고_업체를_부르지_않는다():
    world = OnboardingWorld()
    world.limiter.allowed = False
    with pytest.raises(TooManyNotificationRequestsError):
        await world.sender_verification.request_sender_verification(COMMAND)
    assert world.gateway.calls == []


async def test_업체_오류는_502_다():
    world = OnboardingWorld()

    async def failing(phone):
        raise GatewayTransientError("timeout")

    world.gateway.request_sender_verification = failing
    with pytest.raises(ProviderUnavailableError):
        await world.sender_verification.request_sender_verification(COMMAND)
```

`backend/apps/notification/tests/app/use_cases/test_unlink_channel_interactor.py`:

```python
"""해제 — linked 에서만. unlinked·업체 ID 비움, 템플릿 삭제, 대기 줄 전부 channel_unlinked. 발신번호는 남는다."""
import pytest

from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand
from notification.domain.errors import ChannelNotLinkedError
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, REMINDER
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED, SENT
from notification.tests.helpers.builders import channel, ctx, kst, message
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld

COMMAND = UnlinkChannelCommand(ctx=ctx())


async def test_해제하면_unlinked_가_되고_템플릿은_지우고_대기_줄은_channel_unlinked_로_취소한다():
    world = OnboardingWorld()
    world.channels.rows[1] = channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9),
                                     sms_fallback_enabled=True)
    world.messages.rows[1] = message(id=1, visit_id=1, kind=CONFIRM, status=SCHEDULED)
    world.messages.rows[2] = message(id=2, visit_id=1, kind=REMINDER, status=SCHEDULED)
    world.messages.rows[3] = message(id=3, visit_id=2, kind=CONFIRM, status=SENT)
    world.messages.rows[4] = message(id=4, shop_id=2, visit_id=9, kind=CONFIRM, status=SCHEDULED)

    await world.unlink.unlink_channel(COMMAND)

    saved = world.channels.rows[1]
    assert (saved.status, saved.unlinked_at, saved.provider_channel_id) == (UNLINKED, NOW, None)
    assert (saved.sender_number, saved.sender_number_verified_at, saved.sms_fallback_enabled) == (
        "0212345678", kst(10, 5, 9), True)
    assert world.template_ids() == []
    assert [(m.status, m.canceled_reason) for m in world.messages.rows.values()] == [
        (CANCELED, "channel_unlinked"), (CANCELED, "channel_unlinked"), (SENT, None), (SCHEDULED, None)]
    assert world.gateway.calls == []


@pytest.mark.parametrize("status", [None, TOKEN_REQUESTED, UNLINKED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.unlink.unlink_channel(COMMAND)
    assert ("delete_templates", 1) not in world.journal
```

`backend/apps/notification/tests/app/use_cases/test_update_notification_settings_interactor.py`:

```python
"""설정 전체 교체 — linked 필요, 범위 검사, 문자 대체는 인증 뒤에만. 후속 ① 꺼진 종류 취소 ② 리마인드 시각 재계산
③ 다음 예약 제안 템플릿 등록 ④ 채널의 sms_fallback_enabled."""
from datetime import time, timezone

import pytest

from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.domain.errors import ChannelNotLinkedError, NotificationInputError, SenderNotVerifiedError
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED
from notification.domain.value_objects.template_status import PENDING
from notification.tests.helpers.builders import channel, ctx, kst, message, settings, template
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld


def _iso(at) -> str:
    return at.astimezone(timezone.utc).isoformat()


def _command(sms_fallback_enabled=False, **overrides) -> UpdateNotificationSettingsCommand:
    return UpdateNotificationSettingsCommand(ctx=ctx(), settings=settings(**overrides),
                                             sms_fallback_enabled=sms_fallback_enabled)


async def test_설정을_저장하고_overview_를_돌려준다():
    world = OnboardingWorld()
    view = await world.update_settings.update_notification_settings(_command(reminder_enabled=False))
    assert world.settings.rows[1].reminder_enabled is False
    assert view.settings.reminder_enabled is False and view.channel.status == "linked"


@pytest.mark.parametrize("status", [None, TOKEN_REQUESTED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.update_settings.update_notification_settings(_command())


@pytest.mark.parametrize("overrides", [
    {"reminder_time": time(7, 59)}, {"reminder_time": time(21, 1)}, {"next_visit_after_weeks": 0},
    {"next_visit_after_weeks": 53}, {"next_visit_cooldown_days": 0}, {"next_visit_cooldown_days": 366},
])
async def test_범위_밖_값은_422_이고_저장하지_않는다(overrides):
    world = OnboardingWorld()
    with pytest.raises(NotificationInputError):
        await world.update_settings.update_notification_settings(_command(**overrides))
    assert ("update_settings", 1) not in world.journal


async def test_발신번호_인증_없이_문자_대체를_켜면_409_이고_아무것도_바꾸지_않는다():
    """N11 — DB CHECK 에 닿기 전에 막는다."""
    world = OnboardingWorld()
    with pytest.raises(SenderNotVerifiedError):
        await world.update_settings.update_notification_settings(_command(sms_fallback_enabled=True))
    assert world.channels.rows[1].sms_fallback_enabled is False and ("update_settings", 1) not in world.journal


async def test_인증을_마쳤으면_문자_대체를_켜고_끌_수_있다():
    """④"""
    world = OnboardingWorld()
    world.channels.rows[1] = channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9))
    await world.update_settings.update_notification_settings(_command(sms_fallback_enabled=True))
    assert world.channels.rows[1].sms_fallback_enabled is True
    await world.update_settings.update_notification_settings(_command(sms_fallback_enabled=False))
    assert world.channels.rows[1].sms_fallback_enabled is False


async def test_끈_종류의_대기_줄은_setting_off_로_취소되고_변경을_끄면_change_와_cancel_둘이_취소된다():
    """①"""
    world = OnboardingWorld()
    world.messages.rows[1] = message(id=1, visit_id=1, kind=CONFIRM)
    world.messages.rows[2] = message(id=2, visit_id=1, kind=CHANGE)
    world.messages.rows[3] = message(id=3, visit_id=1, kind=CANCEL)
    world.messages.rows[4] = message(id=4, visit_id=1, kind=REMINDER)
    await world.update_settings.update_notification_settings(_command(change_enabled=False))
    assert [(m.kind, m.status, m.canceled_reason) for m in world.messages.rows.values()] == [
        (CONFIRM, SCHEDULED, None), (CHANGE, CANCELED, "setting_off"), (CANCEL, CANCELED, "setting_off"),
        (REMINDER, SCHEDULED, None)]


async def test_리마인드_시각을_바꾸면_대기_중인_reminder_와_next_visit_의_시각을_다시_계산한다():
    """② — 10월 16일 14시 예약의 리마인드는 15일 18시 → 15일 10시. 완료 10월 1일·4주의 제안은 29일 18시 → 29일 10시."""
    world = OnboardingWorld()
    world.settings.rows[1] = settings(next_visit_enabled=True)
    world.templates.rows[(1, NEXT_VISIT)] = template(id=6, kind=NEXT_VISIT, provider_template_id="KA01TP0006")
    world.messages.rows[1] = message(id=1, visit_id=1, kind=REMINDER, scheduled_at=kst(10, 15, 18),
                                     variables={"starts_at": _iso(kst(10, 16, 14))})
    world.messages.rows[2] = message(id=2, visit_id=2, kind=NEXT_VISIT, scheduled_at=kst(10, 29, 18),
                                     variables={"starts_at": _iso(kst(10, 1, 11)), "completed_at": _iso(kst(10, 1, 12)),
                                                "interval_weeks": "4"})
    await world.update_settings.update_notification_settings(
        _command(reminder_time=time(10, 0), next_visit_enabled=True))
    assert world.messages.rows[1].scheduled_at == kst(10, 15, 10)
    assert world.messages.rows[2].scheduled_at == kst(10, 29, 10)
    assert all(m.status == SCHEDULED for m in world.messages.rows.values())


async def test_새_리마인드_시각이_이미_지났으면_too_late_로_취소한다():
    """② — 지금이 14일 11시인데 14일 15시 예약의 리마인드를 13일 10시로 옮기면 이미 지났다."""
    world = OnboardingWorld()
    world.messages.rows[1] = message(id=1, visit_id=1, kind=REMINDER, scheduled_at=kst(10, 13, 18),
                                     variables={"starts_at": _iso(kst(10, 14, 15))})
    await world.update_settings.update_notification_settings(_command(reminder_time=time(10, 0)))
    assert (world.messages.rows[1].status, world.messages.rows[1].canceled_reason) == (CANCELED, "too_late")


async def test_리마인드_시각이_그대로면_대기_줄을_건드리지_않는다():
    world = OnboardingWorld()
    world.messages.rows[1] = message(id=1, visit_id=1, kind=REMINDER, scheduled_at=kst(10, 15, 18),
                                     variables={"starts_at": _iso(kst(10, 16, 14))})
    await world.update_settings.update_notification_settings(_command(confirm_enabled=False))
    assert world.messages.rows[1].scheduled_at == kst(10, 15, 18)
    assert not any(entry[0] == "save_message" for entry in world.journal)


async def test_다음_예약_제안을_처음_켜면_그_템플릿을_등록하고_이미_있으면_다시_등록하지_않는다():
    """③"""
    world = OnboardingWorld()
    await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    registered = world.templates.rows[(1, NEXT_VISIT)]
    assert (registered.status, registered.provider_template_id, registered.requested_at) == (
        PENDING, f"tpl-KA01PF0001-{NEXT_VISIT}-v{TEXT_VERSION}", NOW)
    assert world.journal.count(("register_template", "KA01PF0001", NEXT_VISIT)) == 1

    await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    assert world.journal.count(("register_template", "KA01PF0001", NEXT_VISIT)) == 1


async def test_다음_예약_제안_템플릿_등록이_실패해도_설정은_저장되고_템플릿만_없다():
    """③ — 디스패처의 10분 주기가 다시 등록한다(설계 9.5)."""
    world = OnboardingWorld()
    world.gateway.register_error = GatewayTransientError("timeout")
    view = await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    assert world.settings.rows[1].next_visit_enabled is True
    assert (1, NEXT_VISIT) not in world.templates.rows and len(view.templates) == 5


async def test_템플릿_등록_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다():
    world = OnboardingWorld()
    await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    names = [entry[0] for entry in world.journal]
    assert names.index("register_template") < names.index("update_settings")


async def test_다음_예약_제안을_끄면_그_대기_줄은_취소되지만_템플릿은_남는다():
    world = OnboardingWorld()
    world.templates.rows[(1, NEXT_VISIT)] = template(id=6, kind=NEXT_VISIT, provider_template_id="KA01TP0006")
    world.settings.rows[1] = settings(next_visit_enabled=True)
    world.messages.rows[1] = message(id=1, visit_id=2, kind=NEXT_VISIT, scheduled_at=kst(10, 29, 18))
    await world.update_settings.update_notification_settings(_command(next_visit_enabled=False))
    assert (world.messages.rows[1].status, world.messages.rows[1].canceled_reason) == (CANCELED, "setting_off")
    assert (1, NEXT_VISIT) in world.templates.rows
```

`backend/apps/notification/tests/helpers/api.py`:

```python
"""notification 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다(visit 과 같다)."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.error_map import NOTIFICATION_ERROR_STATUS
from notification.tests.helpers.builders import OWNER_PERMISSIONS, STAFF_PERMISSIONS, TZ


class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=OWNER_PERMISSIONS, role="owner"):
        self.permissions = frozenset(permissions)
        self.role = role

    async def resolve(self, user_id, shop_id):
        return ShopContext(shop_id=shop_id, member_id=11, role=self.role, permissions=self.permissions,
                           timezone=TZ)


OWNER = StubShopAccess()
STAFF = StubShopAccess(STAFF_PERMISSIONS, role="staff")


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None) -> FastAPI:
    """access=None 이면 사장 권한으로 통과시킨다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, NOTIFICATION_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_current_user_id] = lambda: 5
    app.dependency_overrides[get_shop_access_port] = lambda: access or OWNER
    return app


def client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def error_of(response) -> tuple[int, str]:
    return (response.status_code, response.json()["code"])


class Recorder:
    """유스케이스 스텁 — 받은 명령을 남기고, 정해 둔 값을 돌려주거나 오류를 던진다."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def __getattr__(self, name):
        async def call(command):
            self.calls.append(command)
            if self.error:
                raise self.error
            return self.result

        return call
```

`backend/apps/notification/tests/helpers/fakes.py`:

```diff
@@ -20,6 +20,7 @@ from notification.app.ports.output.channel_repository import ChannelRepository
 from notification.app.ports.output.message_gateway_port import DeliveryState
 from notification.app.ports.output.message_repository import MessageRepository
 from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
+from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
 from notification.app.ports.output.settings_repository import SettingsRepository
 from notification.app.ports.output.template_repository import TemplateRepository
 from notification.domain.entities.notification_channel import NotificationChannel
@@ -367,3 +368,15 @@ class SpyGateway(FakeGateway):
     async def balance(self):
         self.journal.append(("balance",))
         return await super().balance()
+
+
+class FakeOnboardingLimiter(OnboardingLimiterPort):
+    """온보딩 횟수 제한 스텁 — allowed 를 False 로 두면 한도가 찬 것으로 친다. 센 (매장, 동작)이 calls 에 남는다."""
+
+    def __init__(self, allowed: bool = True) -> None:
+        self.allowed = allowed
+        self.calls: list[tuple[int, str]] = []
+
+    async def allow(self, shop_id, action):
+        self.calls.append((shop_id, action))
+        return self.allowed
```

`backend/apps/notification/tests/helpers/onboarding_world.py`:

```python
"""온보딩·설정 인터랙터 테스트의 세계 — 스텁 저장소·SpyGateway·스텁 제한기로 인터랙터 일곱을 만든다."""
from __future__ import annotations

from notification.app.use_cases.confirm_sender_interactor import ConfirmSenderInteractor
from notification.app.use_cases.get_notification_overview_interactor import GetNotificationOverviewInteractor
from notification.app.use_cases.link_channel_interactor import LinkChannelInteractor
from notification.app.use_cases.request_channel_token_interactor import RequestChannelTokenInteractor
from notification.app.use_cases.request_sender_verification_interactor import (
    RequestSenderVerificationInteractor,
)
from notification.app.use_cases.unlink_channel_interactor import UnlinkChannelInteractor
from notification.app.use_cases.update_notification_settings_interactor import (
    UpdateNotificationSettingsInteractor,
)
from notification.domain.value_objects.message_kind import DEFAULT_KINDS
from notification.tests.helpers.builders import channel, kst, settings, template
from notification.tests.helpers.fakes import (
    FakeChannels,
    FakeMessages,
    FakeOnboardingLimiter,
    FakeSettings,
    FakeTemplates,
    Journal,
    SpyGateway,
)

NOW = kst(10, 14, 11)


class OnboardingWorld:
    """linked=True 면 매장 1 이 연동되어 있고(채널 linked·설정 기본값·기본 5종 approved), False 면 채널이 없다."""

    def __init__(self, *, linked: bool = True, now=NOW) -> None:
        self.journal = Journal()
        self.channels = FakeChannels(self.journal)
        self.settings = FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.gateway = SpyGateway(self.journal)
        self.limiter = FakeOnboardingLimiter()
        self.now = now
        if linked:
            self.channels.rows[1] = channel()
            self.settings.rows[1] = settings()
            for i, kind in enumerate(DEFAULT_KINDS, start=1):
                self.templates.rows[(1, kind)] = template(id=i, kind=kind, provider_template_id=f"KA01TP000{i}")

    @property
    def overview(self) -> GetNotificationOverviewInteractor:
        return GetNotificationOverviewInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates)

    @property
    def token(self) -> RequestChannelTokenInteractor:
        return RequestChannelTokenInteractor(channels=self.channels, gateway=self.gateway, limiter=self.limiter)

    @property
    def link(self) -> LinkChannelInteractor:
        return LinkChannelInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, gateway=self.gateway,
            limiter=self.limiter, now=lambda: self.now)

    @property
    def unlink(self) -> UnlinkChannelInteractor:
        return UnlinkChannelInteractor(
            channels=self.channels, templates=self.templates, messages=self.messages, now=lambda: self.now)

    @property
    def update_settings(self) -> UpdateNotificationSettingsInteractor:
        return UpdateNotificationSettingsInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, messages=self.messages,
            gateway=self.gateway, now=lambda: self.now)

    @property
    def sender_verification(self) -> RequestSenderVerificationInteractor:
        return RequestSenderVerificationInteractor(channels=self.channels, gateway=self.gateway, limiter=self.limiter)

    @property
    def confirm_sender(self) -> ConfirmSenderInteractor:
        return ConfirmSenderInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, gateway=self.gateway,
            limiter=self.limiter, now=lambda: self.now)

    def template_ids(self) -> list[tuple[str, str]]:
        return [(t.kind, t.status) for t in sorted(self.templates.rows.values(), key=lambda t: t.id)
                if t.shop_id == 1]
```

`backend/apps/notification/tests/test_fakes_are_ports.py`:

```diff
@@ -6,6 +6,7 @@ from notification.app.ports.output.channel_repository import ChannelRepository
 from notification.app.ports.output.message_gateway_port import MessageGatewayPort
 from notification.app.ports.output.message_repository import MessageRepository
 from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
+from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
 from notification.app.ports.output.settings_repository import SettingsRepository
 from notification.app.ports.output.template_repository import TemplateRepository
 from notification.tests.helpers.fakes import (
@@ -13,6 +14,7 @@ from notification.tests.helpers.fakes import (
     FakeDirectory,
     FakeLedger,
     FakeMessages,
+    FakeOnboardingLimiter,
     FakeSettings,
     FakeShopProfile,
     FakeTemplates,
@@ -33,3 +35,7 @@ def test_디스패처가_쓰는_허브_포트_스텁과_게이트웨이_스텁
     assert isinstance(FakeDirectory(), CustomerDirectoryPort)
     assert isinstance(FakeLedger(), VisitLedgerPort)
     assert isinstance(SpyGateway(), MessageGatewayPort)
+
+
+def test_온보딩_제한기_스텁도_포트를_상속한다():
+    assert isinstance(FakeOnboardingLimiter(), OnboardingLimiterPort)
```

`backend/tests/integration/test_notification_onboarding_wiring.py`:

```python
"""온보딩·설정 API 를 실제 배선(프로바이더·DB 커밋·Redis db 15·매장 접근 확인)으로 돌린다. 게이트웨이는 FakeGateway 를 꽂는다.

첫 테스트는 테넌트 격리다(하네스 규칙). 응답 어디에도 업체 ID·관리자 번호가 없어야 한다(N12).
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.dependencies.notification_wiring import get_message_gateway
from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
ADMIN_PHONE, SENDER = "01012345678", "0212345678"
TOKEN = {"search_id": "hisshaus", "admin_phone": ADMIN_PHONE, "category_code": "003001"}
LINK = {**TOKEN, "token": "000000"}
SETTINGS = {"confirm_enabled": True, "reminder_enabled": True, "report_enabled": True, "change_enabled": True,
            "next_visit_enabled": False, "reminder_time": "18:00", "next_visit_after_weeks": None,
            "next_visit_cooldown_days": 30, "sms_fallback_enabled": False}
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _install(fake: FakeGateway) -> FakeGateway:
    import main

    main.app.dependency_overrides[get_message_gateway] = lambda: fake
    return fake


@pytest.fixture
def gateway(wired):
    import main

    yield _install(FakeGateway())
    main.app.dependency_overrides.pop(get_message_gateway, None)


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


def _path(shop_id: int, tail: str = "") -> str:
    return f"/v1/shops/{shop_id}/notification{tail}"


async def _owner_shop(wired, name="Hiss Haus", owner_name="사장님"):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, name, owner_name)
    return shop_id, owner, bearer(owner["access_token"])


async def _linked_shop(wired):
    shop_id, owner, headers = await _owner_shop(wired)
    assert (await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=headers)).status_code == 202
    linked = await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=headers)
    assert linked.status_code == 200, linked.text
    return shop_id, owner, headers


async def _verify_sender(wired, shop_id, headers) -> None:
    assert (await wired.api.post(_path(shop_id, "/sender/verification"), json={"phone": SENDER},
                                 headers=headers)).status_code == 202
    confirmed = await wired.api.post(_path(shop_id, "/sender"), json={"phone": SENDER, "code": "000000"},
                                     headers=headers)
    assert confirmed.status_code == 200, confirmed.text


async def _approve_templates(wired, shop_id) -> None:
    await wired.execute("UPDATE notification_templates SET status = 'approved' WHERE shop_id = :shop_id",
                        shop_id=shop_id)


async def _booked_reminder(wired, shop_id, headers, starts_at: datetime) -> int:
    """고객·반려동물을 만들고 예약해 reminder 줄을 만든다(템플릿은 approved 여야 한다). 방문 ID."""
    customer = await wired.api.post(f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET},
                                    headers=headers)
    assert customer.status_code == 201, customer.text
    body = customer.json()
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": body["customer"]["customer_id"], "pet_ids": [body["pets"][0]["pet_id"]],
              "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _messages(wired, shop_id: int) -> list[tuple]:
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, canceled_reason, scheduled_at FROM notification_messages "
            "WHERE shop_id = :shop_id ORDER BY id"), {"shop_id": shop_id})
        return [tuple(row) for row in rows]


async def _channel_row(wired, shop_id: int):
    async with wired.engine.connect() as conn:
        return (await conn.execute(text(
            "SELECT status, provider_channel_id, sender_number, sms_fallback_enabled FROM notification_channels "
            "WHERE shop_id = :shop_id"), {"shop_id": shop_id})).one_or_none()


async def test_다른_매장의_여덟_경로는_전부_403_NOT_A_MEMBER_다(wired, gateway):
    """N1·N2 — A 매장 사장이 B 매장의 경로를 부른다. 업체에도 DB 에도 닿지 않는다."""
    a_shop, _, a = await _owner_shop(wired, "A 매장", "A사장")
    operator = await make_operator(wired, "운영자2")
    b_shop, _ = await shop_with_owner(wired, operator, "B 매장", "B사장")

    calls = [
        ("GET", "", None), ("GET", "/myself", None), ("POST", "/channel/token", TOKEN), ("POST", "/channel", LINK),
        ("DELETE", "/channel", None), ("PUT", "/settings", SETTINGS),
        ("POST", "/sender/verification", {"phone": SENDER}), ("POST", "/sender", {"phone": SENDER, "code": "000000"}),
    ]
    responses = [await wired.api.request(method, _path(b_shop, tail), json=body, headers=a)
                 for method, tail, body in calls]
    assert [error_of(r) for r in responses] == [(403, "NOT_A_MEMBER")] * 8
    assert gateway.calls == [] and await _channel_row(wired, b_shop) is None
    assert (await wired.api.get(_path(a_shop), headers=a)).status_code == 200


async def test_온보딩_흐름_토큰_신청_틀린_토큰_연동_직원은_읽기만(wired, gateway):
    shop_id, owner, o = await _owner_shop(wired)
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])

    before = await wired.api.get(_path(shop_id), headers=o)
    assert before.status_code == 200
    assert (before.json()["channel"]["status"], before.json()["settings"], before.json()["templates"]) == (
        "none", None, [])

    requested = await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)
    assert (requested.status_code, requested.json()) == (202, {"status": "token_requested"})
    assert (await wired.api.get(_path(shop_id), headers=o)).json()["channel"]["status"] == "token_requested"

    wrong = await wired.api.post(_path(shop_id, "/channel"), json={**TOKEN, "token": "123456"}, headers=o)
    assert error_of(wrong) == (400, "NOTIFICATION_TOKEN_INVALID")

    linked = await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=o)
    assert linked.status_code == 200, linked.text
    body = linked.json()
    assert body["channel"]["status"] == "linked" and body["channel"]["linked_at"].endswith("+09:00")
    assert body["settings"] == {k: v for k, v in SETTINGS.items() if k != "sms_fallback_enabled"}
    assert [(t["kind"], t["status"]) for t in body["templates"]] == [
        (k, "pending") for k in ("confirm", "reminder", "report", "change", "cancel")]
    assert gateway.calls[-5:][0][0] == "register_template"

    assert (await wired.api.get(_path(shop_id), headers=s)).json() == body
    assert error_of(await wired.api.put(_path(shop_id, "/settings"), json=SETTINGS, headers=s)) == (
        403, "PERMISSION_DENIED")
    assert error_of(await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)) == (
        409, "NOTIFICATION_CHANNEL_LINKED")


async def test_설정_문자_대체는_인증_뒤에만_다음_예약_제안은_템플릿_등록_리마인드_시각은_재계산(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    path = _path(shop_id, "/settings")

    assert error_of(await wired.api.put(path, json={**SETTINGS, "sms_fallback_enabled": True}, headers=o)) == (
        409, "NOTIFICATION_SENDER_NOT_VERIFIED")
    await _verify_sender(wired, shop_id, o)
    enabled = await wired.api.put(path, json={**SETTINGS, "sms_fallback_enabled": True}, headers=o)
    assert enabled.status_code == 200, enabled.text
    assert (enabled.json()["channel"]["sender_verified"], enabled.json()["channel"]["sms_fallback_enabled"]) == (
        True, True)
    assert (await _channel_row(wired, shop_id)).sms_fallback_enabled is True

    with_next = await wired.api.put(path, json={**SETTINGS, "next_visit_enabled": True}, headers=o)
    assert [t["kind"] for t in with_next.json()["templates"]] == [
        "confirm", "reminder", "report", "change", "cancel", "next_visit"]
    assert with_next.json()["channel"]["sms_fallback_enabled"] is False

    await _approve_templates(wired, shop_id)
    await _booked_reminder(wired, shop_id, o, _at(3, 14))
    assert [(k, s, at) for k, s, _, at in await _messages(wired, shop_id)][1] == ("reminder", "scheduled", _at(2, 18))

    moved = await wired.api.put(path, json={**SETTINGS, "reminder_time": "10:00"}, headers=o)
    assert moved.status_code == 200 and moved.json()["settings"]["reminder_time"] == "10:00"
    assert [(k, s, at) for k, s, _, at in await _messages(wired, shop_id)][1] == ("reminder", "scheduled", _at(2, 10))

    off = await wired.api.put(path, json={**SETTINGS, "reminder_time": "10:00", "reminder_enabled": False}, headers=o)
    assert off.status_code == 200
    assert [(k, s, r) for k, s, r, _ in await _messages(wired, shop_id)] == [
        ("confirm", "scheduled", None), ("reminder", "canceled", "setting_off")]
    assert error_of(await wired.api.put(path, json={**SETTINGS, "next_visit_after_weeks": 53}, headers=o)) == (
        422, "VALIDATION_ERROR")


async def test_횟수_제한_토큰_신청_6번째와_틀린_토큰_6번째는_429_다(wired, gateway):
    """N3·N4"""
    shop_id, _, o = await _owner_shop(wired)
    assert (await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)).status_code == 202

    wrong = [await wired.api.post(_path(shop_id, "/channel"), json={**TOKEN, "token": "123456"}, headers=o)
             for _ in range(6)]
    assert [error_of(r) for r in wrong] == [(400, "NOTIFICATION_TOKEN_INVALID")] * 5 + [
        (429, "NOTIFICATION_RATE_LIMITED")]
    assert error_of(await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=o)) == (
        429, "NOTIFICATION_RATE_LIMITED")

    more = [await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o) for _ in range(5)]
    assert [r.status_code for r in more[:4]] == [202] * 4
    assert error_of(more[4]) == (429, "NOTIFICATION_RATE_LIMITED")
    assert sum(1 for c in gateway.calls if c[0] == "request_channel_token") == 5


async def test_해제하면_템플릿은_비고_대기_줄은_취소되며_다시_연동해도_발신번호가_남는다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    await _verify_sender(wired, shop_id, o)
    await _approve_templates(wired, shop_id)
    await _booked_reminder(wired, shop_id, o, _at(3, 14))

    unlinked = await wired.api.delete(_path(shop_id, "/channel"), headers=o)
    assert (unlinked.status_code, unlinked.content) == (204, b"")
    after = (await wired.api.get(_path(shop_id), headers=o)).json()
    assert (after["channel"]["status"], after["channel"]["sender_number"], after["templates"]) == (
        "unlinked", SENDER, [])
    assert [(k, s, r) for k, s, r, _ in await _messages(wired, shop_id)] == [
        ("confirm", "canceled", "channel_unlinked"), ("reminder", "canceled", "channel_unlinked")]
    assert error_of(await wired.api.delete(_path(shop_id, "/channel"), headers=o)) == (
        409, "NOTIFICATION_CHANNEL_NOT_LINKED")
    assert error_of(await wired.api.put(_path(shop_id, "/settings"), json=SETTINGS, headers=o)) == (
        409, "NOTIFICATION_CHANNEL_NOT_LINKED")

    assert (await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)).status_code == 202
    relinked = await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=o)
    assert relinked.status_code == 200, relinked.text
    channel = relinked.json()["channel"]
    assert (channel["status"], channel["sender_number"], channel["sender_verified"]) == ("linked", SENDER, True)
    assert len(relinked.json()["templates"]) == 5


class _DownGateway(FakeGateway):
    async def request_channel_token(self, search_id, admin_phone, category_code):
        raise GatewayTransientError("timeout")


async def test_업체_장애면_502_이고_채널_줄이_생기지_않는다(wired, gateway):
    _install(_DownGateway())
    shop_id, _, o = await _owner_shop(wired)
    response = await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)
    assert error_of(response) == (502, "NOTIFICATION_PROVIDER_UNAVAILABLE")
    assert await _channel_row(wired, shop_id) is None
    assert (await wired.api.get(_path(shop_id), headers=o)).json()["channel"]["status"] == "none"


async def test_응답_어디에도_업체_ID_와_관리자_번호가_없다(wired, gateway):
    """N12"""
    shop_id, _, o = await _linked_shop(wired)
    await _verify_sender(wired, shop_id, o)
    texts = [
        (await wired.api.get(_path(shop_id), headers=o)).text,
        (await wired.api.put(_path(shop_id, "/settings"), json={**SETTINGS, "next_visit_enabled": True},
                             headers=o)).text,
    ]
    assert all(SENDER in t for t in texts)
    for secret in ("provider_channel_id", "provider_template_id", "admin_phone", "pf-", "tpl-", ADMIN_PHONE,
                   "search_id", "hisshaus"):
        assert all(secret not in t for t in texts), secret
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

- 단위 `docker compose run --rm --no-deps backend pytest apps/notification -q -p no:cacheprovider -m "not integration"` → 수집 오류 21(`No module named 'notification.app.ports.output.onboarding_limiter_port'` 를 `fakes.py` 가 import 해 기존 파일까지), `Interrupted: 21 errors during collection`.
- 통합 `… run --rm backend pytest apps/notification/tests/adapter/test_onboarding_redis_limiter.py tests/integration/test_notification_onboarding_wiring.py -m integration` → 수집 오류 1(`No module named 'notification.adapter.outbound.redis'`).

구현 뒤 첫 실행에서 테스트 쪽 실수 하나를 고쳤다(구현은 그대로): 재계산 테스트의 세계가 기본 설정(`next_visit_enabled=False`)이라 후속 ①이 `next_visit` 줄을 먼저 `setting_off` 로 끄고 있었다 → 설정·명령에 `next_visit_enabled=True` 와 그 템플릿 줄을 넣었다.

- [ ] **Step 3: 구현한다**

`backend/apps/notification/app/ports/output/onboarding_limiter_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class OnboardingLimiterPort(ABC):
    """온보딩 요청의 횟수 제한(설계 9.4, N3·N4). 맞든 틀리든 시도마다 센다.

    저장소에 닿지 못하면 막지 않는다 — 업체 쪽 토큰 만료가 2차 방어다.
    """

    @abstractmethod
    async def allow(self, shop_id: int, action: str) -> bool:
        """요청 하나를 세고 창 안의 횟수가 한도 안이면 True. action 은 token·link·sender_verification·sender_confirm."""
```

`backend/apps/notification/adapter/outbound/redis/onboarding_redis_limiter.py`:

```python
from __future__ import annotations

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort

# 동작 → (한도, 창 초). 토큰·인증번호 요청은 시간당 5회, 토큰·인증번호 입력은 10분에 5회(설계 9.4).
_LIMITS: dict[str, tuple[int, int]] = {
    "token": (5, 3600),
    "sender_verification": (5, 3600),
    "link": (5, 600),
    "sender_confirm": (5, 600),
}

logger = logging.getLogger(__name__)


class OnboardingRedisLimiter(OnboardingLimiterPort):
    """키: notification:onboarding:{동작}:{shop_id} → 이번 창의 시도 횟수."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, shop_id: int, action: str) -> bool:
        limit, window = _LIMITS[action]
        key = f"notification:onboarding:{action}:{shop_id}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window, nx=True)  # 창은 처음 셀 때만 잡는다
                count, _ = await pipe.execute()
        except RedisError:
            logger.warning("온보딩 횟수 제한을 건너뜁니다 — Redis 에 닿지 못했습니다.")
            return True
        return int(count) <= limit
```

`backend/apps/notification/app/use_cases/link_channel_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.input.link_channel_use_case import LinkChannelUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview
from notification.app.services.template_registration import register_template
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.channel_status import LINKED, TOKEN_REQUESTED
from notification.domain.value_objects.message_kind import DEFAULT_KINDS


class LinkChannelInteractor(LinkChannelUseCase):
    """6자리 토큰으로 채널을 연동한다(설계 6.2-2). 같은 요청에서 설정 기본값을 만들고 기본 5종 템플릿을 등록·검수 요청한다.

    업체 호출(연동·템플릿 등록)을 전부 마친 뒤에 저장한다 — 잠금을 쥔 채 업체를 부르지 않는다(N14). 템플릿 등록 하나가
    업체 오류로 실패하면 그 종류만 빠지고 디스패처의 10분 주기가 다시 등록한다(설계 9.5). 틀린 토큰은 TokenInvalidError
    그대로(400) — 시도는 맞든 틀리든 센다(N4).
    """

    def __init__(
        self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
        gateway: MessageGatewayPort, limiter: OnboardingLimiterPort, now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._gateway = gateway
        self._limiter = limiter
        self._now = now

    async def link_channel(self, command: LinkChannelCommand) -> NotificationOverviewView:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is not None and channel.is_linked:
            raise ChannelAlreadyLinkedError("이미 연동된 채널입니다.")
        if channel is None or channel.status != TOKEN_REQUESTED:
            raise ChannelNotLinkedError("먼저 인증번호를 받아 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "link"):
            raise TooManyNotificationRequestsError("인증번호 입력이 너무 잦습니다. 토큰을 다시 받아 주세요.")
        try:
            provider_channel_id = await self._gateway.link_channel(
                command.search_id, command.admin_phone, command.category_code, command.token)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
        registered = {}
        for kind in DEFAULT_KINDS:
            template_id = await register_template(self._gateway, provider_channel_id, kind)
            if template_id is not None:
                registered[kind] = template_id

        now = self._now()
        await self._channels.save(ctx, replace(channel, status=LINKED, provider_channel_id=provider_channel_id,
                                               linked_at=now))
        await self._settings.ensure(ctx)
        for kind, template_id in registered.items():
            await self._templates.upsert(ctx, kind, TEXT_VERSION, template_id, now)
        return await load_overview(ctx, self._channels, self._settings, self._templates)
```

`backend/apps/notification/app/use_cases/update_notification_settings_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.ports.input.update_notification_settings_use_case import UpdateNotificationSettingsUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview
from notification.app.services.template_registration import register_template
from notification.domain.errors import ChannelNotLinkedError, SenderNotVerifiedError
from notification.domain.services.schedule_rules import check_settings, next_visit_at, reminder_at
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.message_kind import KINDS, NEXT_VISIT, REMINDER


class UpdateNotificationSettingsInteractor(UpdateNotificationSettingsUseCase):
    """설정 전체 교체(설계 7.1). 저장한 뒤 후속 — ① 꺼진 종류의 대기 줄 취소(setting_off) ② reminder_time 이 바뀌면
    대기 중인 리마인드·다음 예약 제안의 시각 재계산(지난 리마인드는 too_late) ③ 다음 예약 제안을 처음 켜면 템플릿 등록
    ④ 채널의 문자 대체 칸.

    문자 대체는 발신번호 인증 뒤에만(N11 — DB CHECK 전에 409). 템플릿 등록(업체 호출)은 저장 전에 한다(N14).
    """

    def __init__(
        self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
        messages: MessageRepository, gateway: MessageGatewayPort, now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._messages = messages
        self._gateway = gateway
        self._now = now

    async def update_notification_settings(self, command: UpdateNotificationSettingsCommand) -> NotificationOverviewView:
        ctx, new = command.ctx, command.settings
        check_settings(new)
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("먼저 카카오톡 채널을 연동해 주세요.")
        if command.sms_fallback_enabled and channel.sender_number_verified_at is None:
            raise SenderNotVerifiedError("문자 대체를 켜려면 발신번호 인증을 먼저 해 주세요.")
        current = await self._settings.ensure(ctx)

        next_visit_template_id = None
        if new.next_visit_enabled and await self._templates.get(ctx, NEXT_VISIT) is None:
            next_visit_template_id = await register_template(self._gateway, channel.provider_channel_id, NEXT_VISIT)

        now = self._now()
        await self._settings.update(ctx, new)
        off = [kind for kind in KINDS if not new.enabled_for(kind)]
        if off:
            await self._messages.cancel_pending(ctx, "setting_off", kinds=off)
        if new.reminder_time != current.reminder_time:
            await self._reschedule(ctx, new.reminder_time, now)
        if next_visit_template_id is not None:
            await self._templates.upsert(ctx, NEXT_VISIT, TEXT_VERSION, next_visit_template_id, now)
        if command.sms_fallback_enabled != channel.sms_fallback_enabled:
            await self._channels.save(ctx, replace(channel, sms_fallback_enabled=command.sms_fallback_enabled))
        return await load_overview(ctx, self._channels, self._settings, self._templates)

    async def _reschedule(self, ctx, reminder_time, now: datetime) -> None:
        tz = ctx.timezone
        for m in await self._messages.list_pending(ctx, REMINDER):
            at = reminder_at(datetime.fromisoformat(m.variables["starts_at"]), reminder_time, tz, now)
            if at is None:
                await self._messages.cancel_pending(ctx, "too_late", visit_id=m.visit_id, kinds=(REMINDER,))
            else:
                await self._messages.save(ctx, replace(m, scheduled_at=at))
        for m in await self._messages.list_pending(ctx, NEXT_VISIT):
            at = next_visit_at(datetime.fromisoformat(m.variables["completed_at"]), int(m.variables["interval_weeks"]),
                               reminder_time, tz)
            await self._messages.save(ctx, replace(m, scheduled_at=at))
```

`backend/apps/notification/app/services/overview.py`:

```python
"""한눈에 보기 읽기 — 조회와 연동·설정·발신번호 확인 명령이 같은 모양을 돌려준다."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository


async def load_overview(
    ctx: ShopContext, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
) -> NotificationOverviewView:
    return NotificationOverviewView(
        channel=await channels.get(ctx), settings=await settings.get(ctx), templates=await templates.list_for_shop(ctx),
    )
```

`backend/apps/notification/app/services/template_registration.py`:

```python
"""템플릿 등록·검수 요청 — 연동(기본 5종)과 설정(다음 예약 제안을 처음 켤 때)이 함께 쓴다."""
from __future__ import annotations

import logging

from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.domain.services.templates import TEMPLATES, TEXT_VERSION

logger = logging.getLogger("notification.onboarding")


async def register_template(gateway: MessageGatewayPort, provider_channel_id: str, kind: str) -> str | None:
    """업체에 등록하고 업체 템플릿 ID 를 돌려준다. 업체 오류면 WARNING 만 남기고 None — 디스패처의 10분 주기가 다시
    등록한다(설계 9.5). 잠금을 쥐기 전에 부른다(N14)."""
    try:
        return await gateway.register_template(provider_channel_id, TEMPLATES[kind], TEXT_VERSION)
    except GatewayError as exc:
        logger.warning("%s 템플릿 등록 실패 (%s) — 디스패처가 다시 등록합니다", kind, exc.code)
        return None
```

`backend/apps/notification/adapter/inbound/api/schemas/__init__.py`:

```python

```

`backend/apps/notification/adapter/inbound/api/schemas/confirm_sender_schema.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import SenderPhone, SixDigits


class ConfirmSenderRequestSchema(BaseModel):
    phone: SenderPhone
    code: SixDigits
```

`backend/apps/notification/adapter/inbound/api/schemas/link_channel_schema.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import AdminPhone, CategoryCode, SearchId, SixDigits


class LinkChannelRequestSchema(BaseModel):
    """토큰 신청 때와 같은 셋 + 관리자 카카오톡으로 온 6자리."""

    search_id: SearchId
    admin_phone: AdminPhone
    category_code: CategoryCode
    token: SixDigits
```

`backend/apps/notification/adapter/inbound/api/schemas/notification_myself_schema.py`:

```python
from pydantic import BaseModel


class NotificationMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
```

`backend/apps/notification/adapter/inbound/api/schemas/notification_overview_schema.py`:

```python
"""한눈에 보기 응답 — 칸을 하나하나 적는다. 업체 쪽 ID(provider_channel_id·provider_template_id)는 내보내지 않는다(N12)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate

CHANNEL_NONE = "none"


def _local(at: datetime | None, zone: ZoneInfo) -> datetime | None:
    return at.astimezone(zone) if at is not None else None


class NotificationChannelSchema(BaseModel):
    status: str                    # none · token_requested · linked · unlinked
    linked_at: datetime | None     # 매장 시간대
    sender_number: str | None
    sender_verified: bool
    sms_fallback_enabled: bool

    @classmethod
    def of(cls, channel: NotificationChannel | None, zone: ZoneInfo) -> NotificationChannelSchema:
        if channel is None:
            return cls(status=CHANNEL_NONE, linked_at=None, sender_number=None, sender_verified=False,
                       sms_fallback_enabled=False)
        return cls(status=channel.status, linked_at=_local(channel.linked_at, zone),
                   sender_number=channel.sender_number,
                   sender_verified=channel.sender_number_verified_at is not None,
                   sms_fallback_enabled=channel.sms_fallback_enabled)


class NotificationSettingsSchema(BaseModel):
    confirm_enabled: bool
    reminder_enabled: bool
    report_enabled: bool
    change_enabled: bool
    next_visit_enabled: bool
    reminder_time: str             # "HH:MM"
    next_visit_after_weeks: int | None
    next_visit_cooldown_days: int

    @classmethod
    def of(cls, settings: NotificationSettings) -> NotificationSettingsSchema:
        return cls(confirm_enabled=settings.confirm_enabled, reminder_enabled=settings.reminder_enabled,
                   report_enabled=settings.report_enabled, change_enabled=settings.change_enabled,
                   next_visit_enabled=settings.next_visit_enabled,
                   reminder_time=settings.reminder_time.strftime("%H:%M"),
                   next_visit_after_weeks=settings.next_visit_after_weeks,
                   next_visit_cooldown_days=settings.next_visit_cooldown_days)


class NotificationTemplateSchema(BaseModel):
    kind: str
    status: str                    # pending · approved · rejected
    rejected_reason: str | None
    requested_at: datetime         # 매장 시간대
    decided_at: datetime | None

    @classmethod
    def of(cls, template: NotificationTemplate, zone: ZoneInfo) -> NotificationTemplateSchema:
        return cls(kind=template.kind, status=template.status, rejected_reason=template.rejected_reason,
                   requested_at=template.requested_at.astimezone(zone), decided_at=_local(template.decided_at, zone))


class NotificationOverviewSchema(BaseModel):
    channel: NotificationChannelSchema
    settings: NotificationSettingsSchema | None   # 연동 전엔 null
    templates: list[NotificationTemplateSchema]   # 종류 순

    @classmethod
    def of(cls, view: NotificationOverviewView, tz: str) -> NotificationOverviewSchema:
        zone = ZoneInfo(tz)
        return cls(
            channel=NotificationChannelSchema.of(view.channel, zone),
            settings=NotificationSettingsSchema.of(view.settings) if view.settings is not None else None,
            templates=[NotificationTemplateSchema.of(t, zone) for t in view.templates],
        )
```

`backend/apps/notification/adapter/inbound/api/schemas/onboarding_fields.py`:

```python
"""온보딩 요청의 칸 — 업체에만 넘기고 저장하지 않는 값이라 모양만 본다. 어긋나면 422(500 이 아니다)."""
from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

_PLAIN = r"^[^\s\x00-\x1f\x7f]+$"   # 공백·제어 문자 없는 글자열

SearchId = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=_PLAIN)]
AdminPhone = Annotated[str, StringConstraints(pattern=r"^01[0-9]{8,9}$")]    # 휴대폰, 하이픈 없이
CategoryCode = Annotated[str, StringConstraints(min_length=1, max_length=20, pattern=_PLAIN)]
SixDigits = Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]          # 토큰·인증번호
SenderPhone = Annotated[str, StringConstraints(pattern=r"^[0-9]{9,11}$")]     # 발신번호 — 유선도 된다
```

`backend/apps/notification/adapter/inbound/api/schemas/request_channel_token_schema.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import AdminPhone, CategoryCode, SearchId


class RequestChannelTokenRequestSchema(BaseModel):
    """채널 검색 아이디·관리자 휴대폰·업종 카테고리. 다음 단계(연동)까지 앱이 든다 — 서버는 저장하지 않는다."""

    search_id: SearchId
    admin_phone: AdminPhone
    category_code: CategoryCode


class ChannelTokenRequestedSchema(BaseModel):
    status: Literal["token_requested"] = "token_requested"
```

`backend/apps/notification/adapter/inbound/api/schemas/request_sender_verification_schema.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import SenderPhone


class RequestSenderVerificationRequestSchema(BaseModel):
    phone: SenderPhone


class SenderVerificationRequestedSchema(BaseModel):
    status: Literal["verification_requested"] = "verification_requested"
```

`backend/apps/notification/adapter/inbound/api/schemas/update_notification_settings_schema.py`:

```python
from __future__ import annotations

from datetime import time
from typing import Annotated

from pydantic import BaseModel, Field, StrictBool, StrictInt, StringConstraints

from notification.domain.entities.notification_settings import NotificationSettings

# 분까지만 — "18:00". 범위(08:00~21:00)는 도메인 check_settings 가 본다.
ReminderTime = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
# 0 이상 정수만 — 1~52·1~365 는 도메인이 본다.
Count = Annotated[StrictInt, Field(ge=0)]


class UpdateNotificationSettingsRequestSchema(BaseModel):
    """아홉 칸 모두 필수다(전체 교체). 주기를 비우면(null) 지난 방문 간격을 쓴다."""

    confirm_enabled: StrictBool
    reminder_enabled: StrictBool
    report_enabled: StrictBool
    change_enabled: StrictBool
    next_visit_enabled: StrictBool
    reminder_time: ReminderTime
    next_visit_after_weeks: Count | None
    next_visit_cooldown_days: Count
    sms_fallback_enabled: StrictBool

    def to_settings(self) -> NotificationSettings:
        hour, minute = self.reminder_time.split(":")
        return NotificationSettings(
            confirm_enabled=self.confirm_enabled, reminder_enabled=self.reminder_enabled,
            report_enabled=self.report_enabled, change_enabled=self.change_enabled,
            next_visit_enabled=self.next_visit_enabled, reminder_time=time(int(hour), int(minute)),
            next_visit_after_weeks=self.next_visit_after_weeks, next_visit_cooldown_days=self.next_visit_cooldown_days,
        )
```

`backend/apps/notification/adapter/inbound/api/v1/__init__.py`:

```python

```

`backend/apps/notification/adapter/inbound/api/v1/confirm_sender_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.confirm_sender_schema import ConfirmSenderRequestSchema
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.ports.input.confirm_sender_use_case import ConfirmSenderUseCase
from notification.dependencies.confirm_sender_provider import get_confirm_sender_use_case

confirm_sender_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@confirm_sender_router.post("/{shop_id}/notification/sender", response_model=NotificationOverviewSchema)
async def confirm_sender(
    body: ConfirmSenderRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: ConfirmSenderUseCase = Depends(get_confirm_sender_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.confirm_sender(ConfirmSenderCommand(ctx=ctx, phone=body.phone, code=body.code))
    return NotificationOverviewSchema.of(view, ctx.timezone)
```

`backend/apps/notification/adapter/inbound/api/v1/get_notification_overview_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.app.ports.input.get_notification_overview_use_case import GetNotificationOverviewUseCase
from notification.dependencies.get_notification_overview_provider import get_get_notification_overview_use_case

get_notification_overview_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@get_notification_overview_router.get("/{shop_id}/notification", response_model=NotificationOverviewSchema)
async def get_notification_overview(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetNotificationOverviewUseCase = Depends(get_get_notification_overview_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx))
    return NotificationOverviewSchema.of(view, ctx.timezone)
```

`backend/apps/notification/adapter/inbound/api/v1/link_channel_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.link_channel_schema import LinkChannelRequestSchema
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.ports.input.link_channel_use_case import LinkChannelUseCase
from notification.dependencies.link_channel_provider import get_link_channel_use_case

link_channel_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@link_channel_router.post("/{shop_id}/notification/channel", response_model=NotificationOverviewSchema)
async def link_channel(
    body: LinkChannelRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: LinkChannelUseCase = Depends(get_link_channel_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.link_channel(LinkChannelCommand(
        ctx=ctx, search_id=body.search_id, admin_phone=body.admin_phone, category_code=body.category_code,
        token=body.token))
    return NotificationOverviewSchema.of(view, ctx.timezone)
```

`backend/apps/notification/adapter/inbound/api/v1/notification_myself_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from notification.adapter.inbound.api.schemas.notification_myself_schema import NotificationMyselfResponseSchema
from notification.app.dtos.notification_myself_dto import NotificationMyselfQuery
from notification.app.ports.input.notification_myself_use_case import NotificationMyselfUseCase
from notification.dependencies.notification_myself_provider import get_notification_myself_use_case

notification_myself_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@notification_myself_router.get(
    "/{shop_id}/notification/myself", response_model=NotificationMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: NotificationMyselfUseCase = Depends(get_notification_myself_use_case),
) -> NotificationMyselfResponseSchema:
    result = await use_case.introduce_myself(NotificationMyselfQuery(id=7, name="알림 (notification)"))
    return NotificationMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
```

`backend/apps/notification/adapter/inbound/api/v1/request_channel_token_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.request_channel_token_schema import (
    ChannelTokenRequestedSchema,
    RequestChannelTokenRequestSchema,
)
from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand
from notification.app.ports.input.request_channel_token_use_case import RequestChannelTokenUseCase
from notification.dependencies.request_channel_token_provider import get_request_channel_token_use_case

request_channel_token_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@request_channel_token_router.post(
    "/{shop_id}/notification/channel/token", status_code=202, response_model=ChannelTokenRequestedSchema,
)
async def request_channel_token(
    body: RequestChannelTokenRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: RequestChannelTokenUseCase = Depends(get_request_channel_token_use_case),
) -> ChannelTokenRequestedSchema:
    await use_case.request_channel_token(RequestChannelTokenCommand(
        ctx=ctx, search_id=body.search_id, admin_phone=body.admin_phone, category_code=body.category_code))
    return ChannelTokenRequestedSchema()
```

`backend/apps/notification/adapter/inbound/api/v1/request_sender_verification_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.request_sender_verification_schema import (
    RequestSenderVerificationRequestSchema,
    SenderVerificationRequestedSchema,
)
from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand
from notification.app.ports.input.request_sender_verification_use_case import RequestSenderVerificationUseCase
from notification.dependencies.request_sender_verification_provider import (
    get_request_sender_verification_use_case,
)

request_sender_verification_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@request_sender_verification_router.post(
    "/{shop_id}/notification/sender/verification", status_code=202,
    response_model=SenderVerificationRequestedSchema,
)
async def request_sender_verification(
    body: RequestSenderVerificationRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: RequestSenderVerificationUseCase = Depends(get_request_sender_verification_use_case),
) -> SenderVerificationRequestedSchema:
    await use_case.request_sender_verification(RequestSenderVerificationCommand(ctx=ctx, phone=body.phone))
    return SenderVerificationRequestedSchema()
```

`backend/apps/notification/adapter/inbound/api/v1/unlink_channel_router.py`:

```python
from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand
from notification.app.ports.input.unlink_channel_use_case import UnlinkChannelUseCase
from notification.dependencies.unlink_channel_provider import get_unlink_channel_use_case

unlink_channel_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@unlink_channel_router.delete("/{shop_id}/notification/channel", status_code=204)
async def unlink_channel(
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UnlinkChannelUseCase = Depends(get_unlink_channel_use_case),
) -> Response:
    await use_case.unlink_channel(UnlinkChannelCommand(ctx=ctx))
    return Response(status_code=204)
```

`backend/apps/notification/adapter/inbound/api/v1/update_notification_settings_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.adapter.inbound.api.schemas.update_notification_settings_schema import (
    UpdateNotificationSettingsRequestSchema,
)
from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.ports.input.update_notification_settings_use_case import UpdateNotificationSettingsUseCase
from notification.dependencies.update_notification_settings_provider import (
    get_update_notification_settings_use_case,
)

update_notification_settings_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@update_notification_settings_router.put("/{shop_id}/notification/settings", response_model=NotificationOverviewSchema)
async def update_notification_settings(
    body: UpdateNotificationSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateNotificationSettingsUseCase = Depends(get_update_notification_settings_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.update_notification_settings(UpdateNotificationSettingsCommand(
        ctx=ctx, settings=body.to_settings(), sms_fallback_enabled=body.sms_fallback_enabled))
    return NotificationOverviewSchema.of(view, ctx.timezone)
```

`backend/apps/notification/adapter/outbound/log_notification_myself_record_adapter.py`:

```python
from __future__ import annotations

import logging

from notification.app.ports.output.notification_myself_record_port import NotificationMyselfRecordPort

logger = logging.getLogger(__name__)


class LogNotificationMyselfRecordAdapter(NotificationMyselfRecordPort):
    """기록을 로그로 남기는 구현. 매장·고객 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[notification-myself-record] %s | %s", subject, note)
```

`backend/apps/notification/adapter/outbound/redis/__init__.py`:

```python

```

`backend/apps/notification/app/dtos/confirm_sender_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ConfirmSenderCommand:
    ctx: ShopContext
    phone: str
    code: str
```

`backend/apps/notification/app/dtos/get_notification_overview_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetNotificationOverviewQuery:
    ctx: ShopContext
```

`backend/apps/notification/app/dtos/link_channel_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class LinkChannelCommand:
    """토큰 신청 때와 같은 세 값 + 관리자 카카오톡으로 온 6자리."""

    ctx: ShopContext
    search_id: str
    admin_phone: str
    category_code: str
    token: str
```

`backend/apps/notification/app/dtos/notification_myself_dto.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class NotificationMyselfResponse:
    id: int
    name: str
    introduction: str
```

`backend/apps/notification/app/dtos/notification_overview_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate


@dataclass(frozen=True)
class NotificationOverviewView:
    """설정 화면의 한눈에 보기 — 연동·설정·발신번호 인증의 명령도 이것을 돌려준다."""

    channel: NotificationChannel | None       # 연동을 시작한 적이 없으면 None
    settings: NotificationSettings | None     # 연동 전엔 None
    templates: list[NotificationTemplate]     # 종류 순
```

`backend/apps/notification/app/dtos/request_channel_token_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class RequestChannelTokenCommand:
    """카카오톡 채널 연동 토큰 신청. 세 값은 업체에만 넘기고 저장하지 않는다(설계 6.2)."""

    ctx: ShopContext
    search_id: str
    admin_phone: str
    category_code: str
```

`backend/apps/notification/app/dtos/request_sender_verification_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class RequestSenderVerificationCommand:
    ctx: ShopContext
    phone: str
```

`backend/apps/notification/app/dtos/unlink_channel_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UnlinkChannelCommand:
    ctx: ShopContext
```

`backend/apps/notification/app/dtos/update_notification_settings_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_settings import NotificationSettings


@dataclass(frozen=True)
class UpdateNotificationSettingsCommand:
    """알림톡 설정 전체를 바꾼다(PUT). 문자 대체는 채널 줄의 칸이라 따로 든다."""

    ctx: ShopContext
    settings: NotificationSettings
    sms_fallback_enabled: bool
```

`backend/apps/notification/app/ports/input/confirm_sender_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class ConfirmSenderUseCase(ABC):
    @abstractmethod
    async def confirm_sender(self, command: ConfirmSenderCommand) -> NotificationOverviewView: ...
```

`backend/apps/notification/app/ports/input/get_notification_overview_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class GetNotificationOverviewUseCase(ABC):
    @abstractmethod
    async def get_notification_overview(self, query: GetNotificationOverviewQuery) -> NotificationOverviewView: ...
```

`backend/apps/notification/app/ports/input/link_channel_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class LinkChannelUseCase(ABC):
    @abstractmethod
    async def link_channel(self, command: LinkChannelCommand) -> NotificationOverviewView: ...
```

`backend/apps/notification/app/ports/input/notification_myself_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.notification_myself_dto import NotificationMyselfQuery, NotificationMyselfResponse


class NotificationMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: NotificationMyselfQuery) -> NotificationMyselfResponse: ...
```

`backend/apps/notification/app/ports/input/request_channel_token_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand


class RequestChannelTokenUseCase(ABC):
    @abstractmethod
    async def request_channel_token(self, command: RequestChannelTokenCommand) -> None: ...
```

`backend/apps/notification/app/ports/input/request_sender_verification_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand


class RequestSenderVerificationUseCase(ABC):
    @abstractmethod
    async def request_sender_verification(self, command: RequestSenderVerificationCommand) -> None: ...
```

`backend/apps/notification/app/ports/input/unlink_channel_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand


class UnlinkChannelUseCase(ABC):
    @abstractmethod
    async def unlink_channel(self, command: UnlinkChannelCommand) -> None: ...
```

`backend/apps/notification/app/ports/input/update_notification_settings_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class UpdateNotificationSettingsUseCase(ABC):
    @abstractmethod
    async def update_notification_settings(self, command: UpdateNotificationSettingsCommand) -> NotificationOverviewView: ...
```

`backend/apps/notification/app/ports/output/notification_myself_record_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class NotificationMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
```

`backend/apps/notification/app/use_cases/confirm_sender_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.input.confirm_sender_use_case import ConfirmSenderUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)


class ConfirmSenderInteractor(ConfirmSenderUseCase):
    """인증번호를 확인하고 발신번호와 인증 시각을 적는다. 틀리면 TokenInvalidError 그대로(400), 시도는 맞든 틀리든 센다."""

    def __init__(
        self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
        gateway: MessageGatewayPort, limiter: OnboardingLimiterPort, now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._gateway = gateway
        self._limiter = limiter
        self._now = now

    async def confirm_sender(self, command: ConfirmSenderCommand) -> NotificationOverviewView:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("먼저 카카오톡 채널을 연동해 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "sender_confirm"):
            raise TooManyNotificationRequestsError("인증번호 입력이 너무 잦습니다. 인증을 다시 요청해 주세요.")
        try:
            await self._gateway.confirm_sender_verification(command.phone, command.code)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
        await self._channels.save(ctx, replace(channel, sender_number=command.phone,
                                               sender_number_verified_at=self._now()))
        return await load_overview(ctx, self._channels, self._settings, self._templates)
```

`backend/apps/notification/app/use_cases/get_notification_overview_interactor.py`:

```python
from __future__ import annotations

from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.input.get_notification_overview_use_case import GetNotificationOverviewUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview


class GetNotificationOverviewInteractor(GetNotificationOverviewUseCase):
    """읽기만 한다 — 연동 전 매장은 채널 None·설정 None·템플릿 빈 목록이고 아무 줄도 만들지 않는다."""

    def __init__(self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates

    async def get_notification_overview(self, query: GetNotificationOverviewQuery) -> NotificationOverviewView:
        return await load_overview(query.ctx, self._channels, self._settings, self._templates)
```

`backend/apps/notification/app/use_cases/notification_myself_interactor.py`:

```python
from __future__ import annotations

from notification.app.dtos.notification_myself_dto import NotificationMyselfQuery, NotificationMyselfResponse
from notification.app.ports.input.notification_myself_use_case import NotificationMyselfUseCase
from notification.app.ports.output.notification_myself_record_port import NotificationMyselfRecordPort


class NotificationMyselfInteractor(NotificationMyselfUseCase):
    def __init__(self, record: NotificationMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: NotificationMyselfQuery) -> NotificationMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return NotificationMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장의 카카오톡 알림톡 자동 발송(예약 접수·전날 리마인드·미용 알림장·예약 변경·취소·다음 예약 제안)과 "
                "채널 연동·설정을 관리합니다. 경로는 모두 /v1/shops/{shop_id}/notification 아래이고 매 요청마다 매장 "
                "소속을 확인합니다. 메시지 줄은 방문 이벤트가 만들고 디스패처가 보내므로 발송 API 는 없습니다. "
                "GET /notification 은 한눈에 보기입니다(channel — status none·token_requested·linked·unlinked, "
                "linked_at, sender_number, sender_verified, sms_fallback_enabled / settings — 연동 전엔 null / "
                "templates — 종류별 심사 상태와 반려 사유). "
                "온보딩은 POST /notification/channel/token {search_id, admin_phone, category_code} 로 관리자 카카오톡에 "
                "6자리 토큰을 받고(202), POST /notification/channel 에 같은 셋과 token 을 보내 연동합니다(200, 설정 기본값과 "
                "기본 5종 템플릿 등록). 틀린 토큰은 400 NOTIFICATION_TOKEN_INVALID, 먼저 토큰을 받지 않았으면 409 "
                "NOTIFICATION_CHANNEL_NOT_LINKED, 이미 연동됐으면 409 NOTIFICATION_CHANNEL_LINKED 입니다. "
                "DELETE /notification/channel 은 해제입니다(204, 템플릿 삭제·대기 줄 전부 취소, 발신번호는 남습니다). "
                "PUT /notification/settings 는 아홉 칸 전체 교체입니다(다섯 불리언, reminder_time HH:MM 08:00~21:00, "
                "next_visit_after_weeks 1~52 또는 null, next_visit_cooldown_days 1~365, sms_fallback_enabled). 끈 종류의 "
                "대기 줄은 취소되고 reminder_time 을 바꾸면 대기 중인 리마인드·다음 예약 제안의 시각을 다시 계산하며 "
                "next_visit_enabled 를 처음 켜면 그 템플릿을 등록합니다. 문자 대체는 발신번호 인증 뒤에만 켤 수 있습니다"
                "(409 NOTIFICATION_SENDER_NOT_VERIFIED). "
                "발신번호 인증은 POST /notification/sender/verification {phone}(202) 뒤 POST /notification/sender "
                "{phone, code}(200) 입니다. 토큰·인증번호 요청은 매장당 시간당 5회, 토큰·인증번호 입력은 10분에 5회까지이고 "
                "넘으면 429 NOTIFICATION_RATE_LIMITED, 업체 장애는 502 NOTIFICATION_PROVIDER_UNAVAILABLE 입니다. "
                "읽기는 소속이면 되고 연동·해제·설정·발신번호는 shop:update(사장)가 필요합니다. 시각은 매장 시간대로 "
                "돌려주고 업체 쪽 ID 와 관리자 번호는 응답에 싣지 않습니다."
            ),
        )
```

`backend/apps/notification/app/use_cases/request_channel_token_interactor.py`:

```python
from __future__ import annotations

from dataclasses import replace

from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand
from notification.app.ports.input.request_channel_token_use_case import RequestChannelTokenUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED

PROVIDER = "solapi"


class RequestChannelTokenInteractor(RequestChannelTokenUseCase):
    """관리자 카카오톡으로 6자리 토큰을 보내 달라고 업체에 요청하고 채널 줄을 token_requested 로 둔다(설계 6.2-1).

    업체 호출이 먼저, 저장이 뒤다 — 잠금을 쥔 채 업체를 부르지 않는다(N14). 검색 아이디·관리자 번호는 저장하지 않는다.
    """

    def __init__(self, channels: ChannelRepository, gateway: MessageGatewayPort, limiter: OnboardingLimiterPort) -> None:
        self._channels = channels
        self._gateway = gateway
        self._limiter = limiter

    async def request_channel_token(self, command: RequestChannelTokenCommand) -> None:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is not None and channel.is_linked:
            raise ChannelAlreadyLinkedError("이미 연동된 채널입니다. 다시 연동하려면 먼저 해제해 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "token"):
            raise TooManyNotificationRequestsError("토큰 신청이 너무 잦습니다. 잠시 뒤 다시 시도해 주세요.")
        try:
            await self._gateway.request_channel_token(command.search_id, command.admin_phone, command.category_code)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
        if channel is None:
            channel = NotificationChannel(
                shop_id=ctx.shop_id, status=TOKEN_REQUESTED, provider=PROVIDER, provider_channel_id=None,
                linked_at=None, unlinked_at=None, sender_number=None, sender_number_verified_at=None,
                sms_fallback_enabled=False,
            )
        else:
            # 해제했던 매장을 되살린다 — 발신번호·인증 시각·문자 대체는 그대로 둔다.
            channel = replace(channel, status=TOKEN_REQUESTED, provider=PROVIDER, provider_channel_id=None,
                              linked_at=None)
        await self._channels.save(ctx, channel)
```

`backend/apps/notification/app/use_cases/request_sender_verification_interactor.py`:

```python
from __future__ import annotations

from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand
from notification.app.ports.input.request_sender_verification_use_case import RequestSenderVerificationUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)


class RequestSenderVerificationInteractor(RequestSenderVerificationUseCase):
    """문자 대체용 발신번호의 본인인증을 시작한다(설계 6.2-4). 아무것도 저장하지 않는다."""

    def __init__(self, channels: ChannelRepository, gateway: MessageGatewayPort, limiter: OnboardingLimiterPort) -> None:
        self._channels = channels
        self._gateway = gateway
        self._limiter = limiter

    async def request_sender_verification(self, command: RequestSenderVerificationCommand) -> None:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("먼저 카카오톡 채널을 연동해 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "sender_verification"):
            raise TooManyNotificationRequestsError("인증 요청이 너무 잦습니다. 잠시 뒤 다시 시도해 주세요.")
        try:
            await self._gateway.request_sender_verification(command.phone)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
```

`backend/apps/notification/app/use_cases/unlink_channel_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand
from notification.app.ports.input.unlink_channel_use_case import UnlinkChannelUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.errors import ChannelNotLinkedError
from notification.domain.value_objects.channel_status import UNLINKED


class UnlinkChannelInteractor(UnlinkChannelUseCase):
    """연동을 푼다(설계 6.2-5) — unlinked, 템플릿 삭제, 대기 줄 전부 channel_unlinked. 업체에는 아무것도 보내지 않는다.

    발신번호·인증 시각·문자 대체는 남긴다 — 다시 연동하면 그대로 쓴다.
    """

    def __init__(
        self, channels: ChannelRepository, templates: TemplateRepository, messages: MessageRepository,
        now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._templates = templates
        self._messages = messages
        self._now = now

    async def unlink_channel(self, command: UnlinkChannelCommand) -> None:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("연동된 채널이 없습니다.")
        await self._channels.save(ctx, replace(channel, status=UNLINKED, unlinked_at=self._now(),
                                               provider_channel_id=None))
        await self._templates.delete_all(ctx)
        await self._messages.cancel_pending(ctx, "channel_unlinked")
```

`backend/apps/notification/dependencies/confirm_sender_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.confirm_sender_use_case import ConfirmSenderUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.confirm_sender_interactor import ConfirmSenderInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_onboarding_limiter,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.clock import utc_now


def get_confirm_sender_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> ConfirmSenderUseCase:
    return ConfirmSenderInteractor(
        channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db), gateway=gateway, limiter=build_onboarding_limiter(), now=utc_now,
    )
```

`backend/apps/notification/dependencies/get_notification_overview_provider.py`:

```python
from __future__ import annotations

from core.database import DbSession
from notification.app.ports.input.get_notification_overview_use_case import GetNotificationOverviewUseCase
from notification.app.use_cases.get_notification_overview_interactor import GetNotificationOverviewInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_settings_repository,
    build_template_repository,
)


def get_get_notification_overview_use_case(db: DbSession) -> GetNotificationOverviewUseCase:
    return GetNotificationOverviewInteractor(
        channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db),
    )
```

`backend/apps/notification/dependencies/link_channel_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.link_channel_use_case import LinkChannelUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.link_channel_interactor import LinkChannelInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_onboarding_limiter,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.clock import utc_now


def get_link_channel_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> LinkChannelUseCase:
    return LinkChannelInteractor(
        channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db), gateway=gateway, limiter=build_onboarding_limiter(), now=utc_now,
    )
```

`backend/apps/notification/dependencies/notification_myself_provider.py`:

```python
from __future__ import annotations

from notification.adapter.outbound.log_notification_myself_record_adapter import (
    LogNotificationMyselfRecordAdapter,
)
from notification.app.ports.input.notification_myself_use_case import NotificationMyselfUseCase
from notification.app.use_cases.notification_myself_interactor import NotificationMyselfInteractor


def get_notification_myself_use_case() -> NotificationMyselfUseCase:
    return NotificationMyselfInteractor(record=LogNotificationMyselfRecordAdapter())
```

`backend/apps/notification/dependencies/notification_wiring.py`:

```diff
@@ -4,14 +4,17 @@ from __future__ import annotations
 from sqlalchemy.ext.asyncio import AsyncSession
 
 from core.config import APP_ENV, SOLAPI_API_KEY, SOLAPI_API_SECRET
+from core.redis import get_redis
 from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
 from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
 from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
 from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
+from notification.adapter.outbound.redis.onboarding_redis_limiter import OnboardingRedisLimiter
 from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
 from notification.adapter.outbound.strategy.solapi_gateway import SolapiGateway
 from notification.app.ports.output.channel_repository import ChannelRepository
 from notification.app.ports.output.message_gateway_port import MessageGatewayPort
+from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
 from notification.app.ports.output.settings_repository import SettingsRepository
 from notification.app.ports.output.template_repository import TemplateRepository
 
@@ -33,6 +36,10 @@ def build_message_repository(db: AsyncSession) -> MessagePgRepository:
     return MessagePgRepository(db)
 
 
+def build_onboarding_limiter() -> OnboardingLimiterPort:
+    return OnboardingRedisLimiter(get_redis())
+
+
 def build_message_gateway(api_key: str, api_secret: str, app_env: str) -> MessageGatewayPort:
     """키가 둘 다 있으면 솔라피, 둘 다 비고 dev 면 가짜. 그 밖(하나만 있거나 운영에서 빔)은 기동 실패(설계 6.1)."""
     if api_key and api_secret:
```

`backend/apps/notification/dependencies/request_channel_token_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.request_channel_token_use_case import RequestChannelTokenUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.request_channel_token_interactor import RequestChannelTokenInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_onboarding_limiter,
    get_message_gateway,
)


def get_request_channel_token_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> RequestChannelTokenUseCase:
    return RequestChannelTokenInteractor(
        channels=build_channel_repository(db), gateway=gateway, limiter=build_onboarding_limiter())
```

`backend/apps/notification/dependencies/request_sender_verification_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.request_sender_verification_use_case import RequestSenderVerificationUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.request_sender_verification_interactor import (
    RequestSenderVerificationInteractor,
)
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_onboarding_limiter,
    get_message_gateway,
)


def get_request_sender_verification_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> RequestSenderVerificationUseCase:
    return RequestSenderVerificationInteractor(
        channels=build_channel_repository(db), gateway=gateway, limiter=build_onboarding_limiter())
```

`backend/apps/notification/dependencies/unlink_channel_provider.py`:

```python
from __future__ import annotations

from core.database import DbSession
from notification.app.ports.input.unlink_channel_use_case import UnlinkChannelUseCase
from notification.app.use_cases.unlink_channel_interactor import UnlinkChannelInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_template_repository,
)
from notification.domain.services.clock import utc_now


def get_unlink_channel_use_case(db: DbSession) -> UnlinkChannelUseCase:
    return UnlinkChannelInteractor(
        channels=build_channel_repository(db), templates=build_template_repository(db),
        messages=build_message_repository(db), now=utc_now,
    )
```

`backend/apps/notification/dependencies/update_notification_settings_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.update_notification_settings_use_case import UpdateNotificationSettingsUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.update_notification_settings_interactor import (
    UpdateNotificationSettingsInteractor,
)
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.clock import utc_now


def get_update_notification_settings_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> UpdateNotificationSettingsUseCase:
    return UpdateNotificationSettingsInteractor(
        channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db), messages=build_message_repository(db), gateway=gateway, now=utc_now,
    )
```

`backend/main.py`:

```diff
@@ -47,6 +47,19 @@ from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_ro
 from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
 from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
 from media.dependencies.media_library_provider import get_media_library_use_case
+from notification.adapter.inbound.api.error_map import NOTIFICATION_ERROR_STATUS
+from notification.adapter.inbound.api.v1.confirm_sender_router import confirm_sender_router
+from notification.adapter.inbound.api.v1.get_notification_overview_router import get_notification_overview_router
+from notification.adapter.inbound.api.v1.link_channel_router import link_channel_router
+from notification.adapter.inbound.api.v1.notification_myself_router import notification_myself_router
+from notification.adapter.inbound.api.v1.request_channel_token_router import request_channel_token_router
+from notification.adapter.inbound.api.v1.request_sender_verification_router import (
+    request_sender_verification_router,
+)
+from notification.adapter.inbound.api.v1.unlink_channel_router import unlink_channel_router
+from notification.adapter.inbound.api.v1.update_notification_settings_router import (
+    update_notification_settings_router,
+)
 from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
 from notification.app.services.dispatcher_wakeup import wake
 from notification.dependencies.dispatcher_ports import DispatcherPorts, configure_dispatcher_ports
@@ -192,6 +205,15 @@ app.include_router(revoke_visit_report_router)
 # 로그인 없이 열리는 경로 — 더할 때는 tests/route_inspection.py 의 허용 목록에도 적는다.
 app.include_router(read_public_report_router)
 app.include_router(mark_report_viewed_router)
+# notification
+app.include_router(notification_myself_router)
+app.include_router(get_notification_overview_router)
+app.include_router(request_channel_token_router)
+app.include_router(link_channel_router)
+app.include_router(unlink_channel_router)
+app.include_router(update_notification_settings_router)
+app.include_router(request_sender_verification_router)
+app.include_router(confirm_sender_router)
 # media
 app.include_router(media_myself_router)
 app.include_router(issue_upload_router)
@@ -200,7 +222,7 @@ install_error_handlers(
     app,
     {
         **AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS,
-        **CUSTOMER_ERROR_STATUS, **VISIT_ERROR_STATUS, **MEDIA_ERROR_STATUS,
+        **CUSTOMER_ERROR_STATUS, **VISIT_ERROR_STATUS, **MEDIA_ERROR_STATUS, **NOTIFICATION_ERROR_STATUS,
     },
 )
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 단위(인터랙터 7 파일 + 라우터 8 파일 + 스텁 포트 1) | 193 passed (notification 단위 전체 475 + 바인딩) |
| 이 작업의 통합(제한기 11 + 온보딩 배선 7) | 18 passed |
| 단위 전체 (`-m "not integration and not network"`, `--no-deps`) | 1789 passed (시작 1596 + 193) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken |

라우트 표: `print_routes.py` 를 기준(69줄)과 diff → 77줄, 늘어난 여덟 줄이 전부 이 작업의 경로다(경로·메서드만).
```
> backend GET    /v1/shops/{shop_id}/notification
> backend DELETE /v1/shops/{shop_id}/notification/channel
> backend POST   /v1/shops/{shop_id}/notification/channel
> backend POST   /v1/shops/{shop_id}/notification/channel/token
> backend GET    /v1/shops/{shop_id}/notification/myself
> backend POST   /v1/shops/{shop_id}/notification/sender
> backend POST   /v1/shops/{shop_id}/notification/sender/verification
> backend PUT    /v1/shops/{shop_id}/notification/settings
```
`tests/test_hub_port_binding.py` 의 "로그인 없이 열리는 경로" 목록은 그대로다(넷). 통합 세션은 테스트 DB·Redis db 15 에만 붙었고 실제 `api.solapi.com` 은 부르지 않았다(게이트웨이는 전부 `FakeGateway`/`SpyGateway`).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 연동에서 `settings.ensure` 제거 → 단위 `test_link_channel_interactor.py::test_맞는_토큰이면_linked_가_되고_설정_기본값과_기본_5종_템플릿이_pending_으로_생긴다`, `::test_업체_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다`; 통합 `test_notification_onboarding_wiring.py::test_온보딩_흐름_토큰_신청_틀린_토큰_연동_직원은_읽기만`(설정 null), `::test_해제하면_템플릿은_비고_대기_줄은_취소되며_다시_연동해도_발신번호가_남는다`
- 설정 후속 ②(재계산) 제거 → 단위 `test_update_notification_settings_interactor.py::test_리마인드_시각을_바꾸면_대기_중인_reminder_와_next_visit_의_시각을_다시_계산한다`, `::test_새_리마인드_시각이_이미_지났으면_too_late_로_취소한다`; 통합 `::test_설정_문자_대체는_인증_뒤에만_다음_예약_제안은_템플릿_등록_리마인드_시각은_재계산`
- `SenderNotVerifiedError` 검사 제거 → 단위 `::test_발신번호_인증_없이_문자_대체를_켜면_409_이고_아무것도_바꾸지_않는다`; 통합 `::test_설정_문자_대체는_…`(DB CHECK 로 500)
- 해제에서 `cancel_pending` 제거 → 단위 `test_unlink_channel_interactor.py::test_해제하면_unlinked_가_되고_템플릿은_지우고_대기_줄은_channel_unlinked_로_취소한다`; 통합 `::test_해제하면_템플릿은_비고_…`
- 제한기 `allow` 를 늘 `True` 로 → 통합 `::test_횟수_제한_토큰_신청_6번째와_틀린_토큰_6번째는_429_다`, `test_onboarding_redis_limiter.py::test_동작마다_5번까지_받고_6번째부터_막는다[token·link·sender_verification·sender_confirm]`, `::test_매장마다_동작마다_따로_센다`, `::test_창이_지나면_다시_받는다`(단위는 스텁이라 영향 없음)
- 토큰 신청의 `ChannelAlreadyLinkedError` 검사 제거 → 단위 `test_request_channel_token_interactor.py::test_연동된_매장이_다시_신청하면_409_이고_업체를_부르지_않는다`; 통합 `::test_온보딩_흐름_…`(연동된 매장의 재신청 409)
- 설정 라우터의 `require_permission("shop:update")` → `get_shop_context`(import 포함) → 단위 `test_update_notification_settings_router.py::test_직원은_설정을_바꾸지_못한다`; 통합 `::test_온보딩_흐름_…`(직원 PUT 403). 첫 시도는 import 를 안 바꿔 수집 오류(NameError)로 잡혔고, import 까지 바꿔 다시 돌린 결과가 이것이다
- 연동에서 `status != TOKEN_REQUESTED` 검사 제거(None 만 검사) → 단위 `test_link_channel_interactor.py::test_토큰을_받지_않은_매장은_409_NOT_LINKED_다[unlinked]`
- 설정 후속 ①(꺼진 종류 `setting_off`) 제거 → 단위 `::test_끈_종류의_대기_줄은_setting_off_로_취소되고_변경을_끄면_change_와_cancel_둘이_취소된다`, `::test_다음_예약_제안을_끄면_그_대기_줄은_취소되지만_템플릿은_남는다`; 통합 `::test_설정_문자_대체는_…`
- 설정 후속 ③(`next_visit` 템플릿 `upsert`) 제거 → 단위 `::test_다음_예약_제안을_처음_켜면_그_템플릿을_등록하고_이미_있으면_다시_등록하지_않는다`; 통합 `::test_설정_문자_대체는_…`(템플릿 여섯)
- 발신번호 확인이 `sender_number_verified_at` 을 적지 않음 → 단위 `test_confirm_sender_interactor.py::test_맞는_인증번호면_발신번호와_인증_시각을_적고_overview_를_돌려준다`; 통합 `::test_설정_문자_대체는_…`, `::test_해제하면_…`
- overview 의 `linked_at` 을 매장 시간대로 바꾸지 않음 → 단위 `test_get_notification_overview_router.py::test_직원도_한눈에_보기를_보고_시각은_매장_시간대다`, `::test_발신번호를_인증했으면_번호와_인증_여부가_보인다`
- 연동이 템플릿 등록(업체 호출) 전에 채널을 저장(잠금 쥔 채 HTTP) → 단위 `test_link_channel_interactor.py::test_업체_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다`
- `reminder_time` 정규식을 `^[0-9]{1,2}:[0-9]{2}$` 로 느슨하게 → 단위 `test_update_notification_settings_router.py::test_불리언_문자열_시각_형식_정수_아닌_값_빠진_칸은_422_다` 의 `"25:00"`·`"18:60"`·`"9:00"` 경우 셋
- `main.py` 에서 `**NOTIFICATION_ERROR_STATUS` 등록 제거 → 통합 `::test_온보딩_흐름_…`, `::test_설정_문자_대체는_…`, `::test_횟수_제한_…`, `::test_해제하면_…`, `::test_업체_장애면_502_이고_채널_줄이_생기지_않는다`(도메인 오류가 전부 500)

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 설정·온보딩 API — 채널 토큰·연동·해제, 설정 전체 교체와 후속, 발신번호 인증, 횟수 제한

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: 방문별 발송 내역·다시 보내기·단건 조회 — 실패 줄에는 공유용 문안(`share_text`)

**Files:**
- Create: `backend/apps/notification/dependencies/hub_ports.py`
- Create: `backend/apps/notification/app/use_cases/resend_notification_interactor.py`
- Modify: `backend/apps/notification/app/services/message_text.py`
- Create: `backend/apps/notification/adapter/inbound/api/path_params.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/notification_message_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/schemas/resend_notification_schema.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/get_notification_message_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/list_visit_notifications_router.py`
- Create: `backend/apps/notification/adapter/inbound/api/v1/resend_notification_router.py`
- Create: `backend/apps/notification/app/dtos/get_notification_message_dto.py`
- Create: `backend/apps/notification/app/dtos/list_visit_notifications_dto.py`
- Create: `backend/apps/notification/app/dtos/notification_message_dto.py`
- Create: `backend/apps/notification/app/dtos/resend_notification_dto.py`
- Create: `backend/apps/notification/app/ports/input/get_notification_message_use_case.py`
- Create: `backend/apps/notification/app/ports/input/list_visit_notifications_use_case.py`
- Create: `backend/apps/notification/app/ports/input/resend_notification_use_case.py`
- Modify: `backend/apps/notification/app/services/dispatcher.py`
- Create: `backend/apps/notification/app/use_cases/get_notification_message_interactor.py`
- Create: `backend/apps/notification/app/use_cases/list_visit_notifications_interactor.py`
- Create: `backend/apps/notification/dependencies/get_notification_message_provider.py`
- Create: `backend/apps/notification/dependencies/list_visit_notifications_provider.py`
- Create: `backend/apps/notification/dependencies/resend_notification_provider.py`
- Create: `backend/apps/notification/tests/adapter/test_get_notification_message_router.py`
- Create: `backend/apps/notification/tests/adapter/test_list_visit_notifications_router.py`
- Create: `backend/apps/notification/tests/adapter/test_resend_notification_router.py`
- Modify: `backend/apps/notification/tests/app/services/test_dispatcher.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_get_notification_message_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_list_visit_notifications_interactor.py`
- Create: `backend/apps/notification/tests/app/use_cases/test_resend_notification_interactor.py`
- Create: `backend/apps/notification/tests/helpers/message_world.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_notification_messages_wiring.py`
- Modify: `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: 작업 4 의 `MessageRepository.list_for_visit`·`get`·`create`, 작업 5 의 `variables` 키, 작업 7 의 `message_text.message_variables`·`message_text`·`dispatcher_wakeup.wake`, 작업 8 의 라우터·스키마·프로바이더 모양과 `NOTIFICATION_ERROR_STATUS`; 허브 포트 `ShopProfilePort`(매장 이름)·`CustomerDirectoryPort.contact`·`briefs`; `require_permission("reservation:write")`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

### 5.1 API 계약 (⑥-2 앱이 기대는 것 — T10 결정 기록 009 가 이 절을 옮긴다)

접두 `/v1/shops/{shop_id}`, 태그 `notifications`, 전부 로그인 + 매장 소속. 읽기 둘은 소속이면 되고 재발송은 `reservation:write`(직원도). 오류 응답은 공통 `{"code", "message"}`.

| 메서드·경로 | 권한 | 요청 본문 | 성공 | 오류 |
|---|---|---|---|---|
| GET `/visits/{visit_id}/notifications` | 소속 | — | 200 `{"items": [MessageItem]}` 최신순(`created_at desc, id desc`). **방문이 이 매장 것이 아니거나 없으면 빈 목록 200**(404 가 아니다 — 6절) | 422 `VALIDATION_ERROR`(`visit_id` 가 1~bigint 밖·정수 아님) |
| POST `/visits/{visit_id}/notifications/{kind}/resend` | reservation:write | — | 201 `{"message_id": int}` — 새 줄(`scheduled`, `scheduled_at` = 지금, `requested_by_member_id` = 누른 멤버) | 404 `NOTIFICATION_MESSAGE_NOT_FOUND`(이 매장·방문·종류의 줄이 없음 — 다른 매장 방문 포함) · 409 `NOTIFICATION_ALREADY_PENDING`(가장 최근 줄이 scheduled·sending·accepted, 또는 동시에 두 번 눌러 둘째) · 409 `NOTIFICATION_CHANNEL_NOT_LINKED` · 409 `NOTIFICATION_TEMPLATE_NOT_APPROVED`(템플릿 없음·pending·rejected) · 422 `VALIDATION_ERROR`(`kind` 가 여섯 밖, `visit_id` 범위 밖) |
| GET `/notifications/{message_id}` | 소속 | — | 200 `MessageItem` | 404 `NOTIFICATION_MESSAGE_NOT_FOUND`(없거나 다른 매장) · 422(`message_id` 범위 밖) |

공통: 다른 매장 → 403 `NOT_A_MEMBER`, 권한 없는 멤버의 재발송 → 403 `PERMISSION_DENIED`, `shop_id` 가 int32 밖 → 422.

`kind` ∈ `confirm | reminder | report | change | cancel | next_visit`(대소문자 그대로, 정규식 `^(confirm|reminder|report|change|cancel|next_visit)$`).

재발송 규칙: 채널 `linked` → 템플릿 `approved` → 가장 최근 줄(목록의 그 종류 첫 줄)이 `canceled`·`sent`·`fallback_sent`·`failed` 면 진행(성공한 것도 다시 보낼 수 있다). **설정이 꺼진 종류도 보낸다** — 디스패처도 `requested_by_member_id` 가 있는 줄은 `setting_off` 검사를 건너뛴다(그 밖의 검사 — 매장 열림·채널·템플릿·익명화·번호·야간 미룸·동의·상한 — 는 그대로). 새 줄의 `variables`·`pet_id`·`customer_id` 는 가장 최근 줄 그대로(알림장이면 같은 주소). 요청이 디스패처를 깨우므로 보통 1초 안에 `accepted` 가 된다.

`MessageItem`(`MessageItemSchema`) — 칸 열 개, 이것뿐. 시각은 매장 시간대(`+09:00`)
```
message_id             : int
kind                   : "confirm" | "reminder" | "report" | "change" | "cancel" | "next_visit"
status                 : "scheduled" | "sending" | "accepted" | "sent" | "fallback_sent" | "failed" | "canceled"
channel_used           : "alimtalk" | "sms" | "lms" | null     (sent·fallback_sent 일 때)
scheduled_at           : datetime                              (즉시 줄은 만든 시각)
sent_at                : datetime | null
error_kind             : "transient" | "permanent" | null       (failed 일 때)
canceled_reason        : str | null                            (canceled 일 때 — rescheduled · visit_canceled · no_show · setting_off ·
                                                                channel_unlinked · shop_closed · template_rejected · report_revoked · too_late ·
                                                                anonymized · has_upcoming · cooldown · no_consent · bad_phone)
requested_by_member_id : int | null                            (있으면 [다시 보내기]로 만든 줄)
share_text             : str | null
```
없는 칸(N12): `variables`·`provider_message_id`·`error_code`·`customer_id`·`pet_id`·`attempts`·`next_attempt_at`·`created_at`.

`share_text` 규칙: **`status == "failed"` 인 줄에만.** 디스패처가 보낼 때와 같은 재료로 만든 **문자용 문안**(`TEMPLATES[kind].sms_body` 를 채운 것, `RenderedMessage.sms_text`) — 매장 이름은 `ShopProfilePort.public_profile(shop_id).name`, `#{대상}` 은 `CustomerDirectoryPort.briefs` 의 반려동물 이름(없으면 `contact` 의 보호자 이름 + "님"), 시각은 저장된 `variables` 를 매장 시간대로, 알림장이면 `variables["url"]`(`…/r/<토큰>`)이 문안에 든다. 보호자가 익명화되어 `contact` 가 None 이면 `null`(실패 줄이라도). 종류별 모양:
```
confirm     [매장명] 10월 16일(금) 14:00 예약이 접수되었어요.
reminder    [매장명] 내일 14:00 예약을 잊지 마세요.
report      [매장명] 알림장 https://…/r/<토큰>
change      [매장명] 예약이 10월 16일(금) 14:00로 바뀌었어요.
cancel      [매장명] 10월 16일(금) 14:00 예약이 매장 사정으로 취소되었어요.
next_visit  [매장명] 콩이 미용한 지 4주가 지났어요.
```
앱(설계 8.2·8.3): 실패 + `error_kind == "transient"` 면 [다시 보내기], `"permanent"` 면 [다른 방법으로 보내기](`share_text` 를 공유 시트에). 알림장 보내기 뒤 폴링은 목록에서 `kind == "report"` 의 첫 줄(최신)을 보거나, 재발송 응답의 `message_id` 로 단건 조회.

### 5.2 코드 시그니처

```python
# notification.dependencies.hub_ports — 요청 안의 허브 포트 자리. main.py 가 꽂는다
def get_customer_directory() -> CustomerDirectoryPort     # RuntimeError
def get_shop_profile() -> ShopProfilePort                  # RuntimeError
# main.py: from notification.dependencies.hub_ports import get_customer_directory as get_notification_customer_directory,
#          get_shop_profile as get_notification_shop_profile
#          app.dependency_overrides[get_notification_shop_profile] = get_shop_profile_use_case
#          app.dependency_overrides[get_notification_customer_directory] = get_customer_directory_use_case

# notification.adapter.inbound.api.path_params
VisitId = Annotated[int, Path(ge=1, le=9_223_372_036_854_775_807)]; MessageId = 같음
MessageKind = Annotated[str, Path(pattern=f"^({'|'.join(KINDS)})$")]

# notification.app.dtos
@dataclass(frozen=True) class NotificationMessageView: message: NotificationMessage; share_text: str | None
@dataclass(frozen=True) class ListVisitNotificationsQuery: ctx: ShopContext; visit_id: int
@dataclass(frozen=True) class ResendNotificationCommand: ctx: ShopContext; visit_id: int; kind: str
@dataclass(frozen=True) class GetNotificationMessageQuery: ctx: ShopContext; message_id: int

# notification.app.ports.input
class ListVisitNotificationsUseCase:  async def list_visit_notifications(query) -> list[NotificationMessageView]
class ResendNotificationUseCase:      async def resend_notification(command) -> int        # 새 줄의 message_id
class GetNotificationMessageUseCase:  async def get_notification_message(query) -> NotificationMessageView

# notification.app.use_cases
ListVisitNotificationsInteractor(messages: MessageRepository, shops: ShopProfilePort, directory: CustomerDirectoryPort)
    # messages.list_for_visit(ctx, visit_id) → message_views
GetNotificationMessageInteractor(messages, shops, directory)
    # messages.get(ctx, id) 가 None → MessageNotFoundError → message_views([row])
ResendNotificationInteractor(channels: ChannelRepository, templates: TemplateRepository, messages: MessageRepository,
                             now: Callable[[], datetime], wake: Callable[[], None])
    # channels.get → linked 아님 ChannelNotLinkedError → templates.get(ctx, kind) → None/≠approved TemplateNotApprovedError
    # → list_for_visit 에서 kind 의 첫 줄 → 없음 MessageNotFoundError → status ∈ {scheduled, sending, accepted} MessageAlreadyPendingError
    # → messages.create(ctx, NewMessage(shop_id=ctx.shop_id, visit_id, customer_id=latest.customer_id, pet_id=latest.pet_id, kind,
    #      scheduled_at=now(), variables=latest.variables, requested_by_member_id=ctx.member_id))  (색인 위반 → MessageAlreadyPendingError)
    # → wake() → created.id

# notification.app.services.message_text (더한 것)
async def message_target(ctx: ShopContext, directory: CustomerDirectoryPort, message: NotificationMessage,
                         contact: CustomerContact) -> str
    # pet_id 가 있으면 directory.briefs(ctx, [], [pet_id]).pets 의 이름, 아니면 contact.name → target_label. 디스패처도 이것을 쓴다
async def message_views(ctx: ShopContext, messages: list[NotificationMessage], shops: ShopProfilePort,
                        directory: CustomerDirectoryPort) -> list[NotificationMessageView]
    # FAILED 줄마다: public_profile(ctx.shop_id)(한 번) → directory.contact(ctx, customer_id)(None 이면 share_text None)
    # → message_text(kind, shop_name=profile.name, target=message_target(...), tz=ctx.timezone, variables=m.variables).sms_text

# notification.app.services.dispatcher._process (바뀐 줄)
if settings is None or (not settings.enabled_for(m.kind) and m.requested_by_member_id is None): → setting_off
target = await message_target(ctx, self._directory, m, contact)

# notification.adapter.inbound.api.schemas
class MessageItemSchema(BaseModel):  (5.1 의 칸 열 개)   @classmethod def of(cls, view: NotificationMessageView, tz: str)
class MessageListSchema(BaseModel):  items: list[MessageItemSchema]   @classmethod def of(cls, views, tz)
class MessageCreatedSchema(BaseModel): message_id: int

# notification.adapter.inbound.api.v1 — APIRouter(prefix="/v1/shops", tags=["notifications"])
list_visit_notifications_router · resend_notification_router · get_notification_message_router

# notification.dependencies — 프로바이더 셋
get_list_visit_notifications_use_case(db, shops=Depends(get_shop_profile), directory=Depends(get_customer_directory))
get_get_notification_message_use_case(db, shops=Depends(get_shop_profile), directory=Depends(get_customer_directory))
get_resend_notification_use_case(db)        # now=utc_now, wake=dispatcher_wakeup.wake

# notification.tests.helpers.message_world
NOW = kst(10, 14, 11); SHOP_NAME = "두부네"
class MessageWorld(now=NOW)   # .channels .settings .templates .messages .shops(FakeShopProfile {1: 두부네}) .directory(FakeDirectory, family()) .journal
    # 인터랙터: .list .get .resend ; .wake() 는 journal 에 ("wake",)
```

앱의 방문 상세가 쓰는 셋이다(설계 7.2·8.2). 목록·단건은 매장 소속이면 되고(`get_shop_context`), 재발송은 `reservation:write`(직원도). **다른 매장·없는 방문의 목록은 빈 목록 200**(notification 은 방문 표를 모른다 — 이 계획이 정한 것), 재발송·단건은 404. 재발송은 가장 최근 줄의 재료(`variables`)로 새 줄을 `requested_by_member_id` 와 함께 `scheduled=now` 로 만들고 `wake()` 한다 — 대기 줄이 있으면 409, **설정이 꺼진 종류여도 보낸다**(디스패처가 `requested_by_member_id` 줄은 `setting_off` 를 건너뛴다). `share_text` 는 실패한 줄에만 — 문자용 짧은 문안을 보호자 이름·아이 이름·매장 이름으로 채운 것이고 응답의 다른 칸에는 번호·`variables`·업체 ID 가 없다(N12). 허브 포트 자리 둘은 `notification/dependencies/hub_ports.py`, 꽂기는 `main.py`. `#{대상}` 조립은 `message_target` 로 빼서 디스패처와 공유 문안이 같은 함수를 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/adapter/test_get_notification_message_router.py`:

```python
"""줄 하나의 상태 — 소속이면 읽는다. 목록의 항목과 같은 MessageItem 이다. 없거나 다른 매장이면 404."""
import pytest

from notification.adapter.inbound.api.v1.get_notification_message_router import get_notification_message_router
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.dependencies.get_notification_message_provider import get_get_notification_message_use_case
from notification.domain.errors import MessageNotFoundError
from notification.domain.value_objects.message_status import ACCEPTED
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import kst, message

VARIABLES = {"starts_at": kst(10, 16, 14).isoformat()}
ITEM = {"message_id": 5, "kind": "confirm", "status": "accepted", "channel_used": None,
        "scheduled_at": "2026-10-14T11:00:00+09:00", "sent_at": None, "error_kind": None, "canceled_reason": None,
        "requested_by_member_id": None, "share_text": None}


def _app(stub, access=None):
    return build_app(get_notification_message_router, get_get_notification_message_use_case, stub, access)


async def test_직원도_줄_하나를_읽는다():
    view = NotificationMessageView(
        message=message(id=5, status=ACCEPTED, provider_message_id="M4V-0005", variables=VARIABLES), share_text=None)
    stub = Recorder(view)
    async with client(_app(stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/notifications/5")
    assert (response.status_code, response.json()) == (200, ITEM)
    assert "M4V-" not in response.text and "variables" not in response.text
    [query] = stub.calls
    assert (query.ctx.shop_id, query.message_id) == (3, 5)


async def test_없거나_다른_매장이면_404_다():
    """N1"""
    async with client(_app(Recorder(error=MessageNotFoundError("없음")))) as c:
        response = await c.get("/v1/shops/3/notifications/5")
    assert error_of(response) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")


@pytest.mark.parametrize("message_id", ["0", "9223372036854775808", "abc"])
async def test_메시지_ID_가_범위_밖이거나_정수가_아니면_422_다(message_id):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.get(f"/v1/shops/3/notifications/{message_id}")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []
```

`backend/apps/notification/tests/adapter/test_list_visit_notifications_router.py`:

```python
"""방문별 발송 내역 — 소속이면 읽는다. 칸은 MessageItem 열 개뿐이고 variables·업체 ID·오류 코드·고객 ID 는 없다(N12)."""
import pytest

from notification.adapter.inbound.api.v1.list_visit_notifications_router import list_visit_notifications_router
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.dependencies.list_visit_notifications_provider import get_list_visit_notifications_use_case
from notification.domain.value_objects.message_kind import REPORT
from notification.domain.value_objects.message_status import FAILED, SENT
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import kst, message

URL = "https://a/" + "t" * 43
VARIABLES = {"starts_at": kst(10, 16, 14).isoformat(), "url": URL, "expires_at": ""}
FAILED_ITEM = {"message_id": 2, "kind": "report", "status": "failed", "channel_used": None,
               "scheduled_at": "2026-10-14T11:00:00+09:00", "sent_at": None, "error_kind": "permanent",
               "canceled_reason": None, "requested_by_member_id": None, "share_text": f"[두부네] 알림장 {URL}"}
SENT_ITEM = {"message_id": 1, "kind": "confirm", "status": "sent", "channel_used": "alimtalk",
             "scheduled_at": "2026-10-14T11:00:00+09:00", "sent_at": "2026-10-14T11:00:05+09:00", "error_kind": None,
             "canceled_reason": None, "requested_by_member_id": 11, "share_text": None}


def _views() -> list[NotificationMessageView]:
    failed = message(id=2, kind=REPORT, status=FAILED, error_kind="permanent", error_code="3104", pet_id=101,
                     customer_id=7, provider_message_id="M4V-0002", variables=VARIABLES)
    sent = message(id=1, status=SENT, channel_used="alimtalk", sent_at=kst(10, 14, 11, 0).replace(second=5),
                   provider_message_id="M4V-0001", requested_by_member_id=11, variables=VARIABLES)
    return [NotificationMessageView(message=failed, share_text=f"[두부네] 알림장 {URL}"),
            NotificationMessageView(message=sent, share_text=None)]


def _app(stub, access=None):
    return build_app(list_visit_notifications_router, get_list_visit_notifications_use_case, stub, access)


async def test_직원도_목록을_보고_시각은_매장_시간대이며_실패_줄에만_share_text_가_있다():
    stub = Recorder(_views())
    async with client(_app(stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/12/notifications")
    assert response.status_code == 200
    assert response.json() == {"items": [FAILED_ITEM, SENT_ITEM]}
    [query] = stub.calls
    assert (query.ctx.shop_id, query.visit_id) == (3, 12)


async def test_응답에_variables_업체_ID_오류_코드_고객_ID_칸이_없다():
    """N12 — share_text 의 주소는 실패 줄의 문안으로만 나간다."""
    async with client(_app(Recorder(_views()))) as c:
        text = (await c.get("/v1/shops/3/visits/12/notifications")).text
    assert text.count(URL) == 1
    for secret in ("variables", "provider_message_id", "M4V-", "error_code", "3104", "customer_id", "pet_id",
                   "starts_at", "expires_at"):
        assert secret not in text, secret


async def test_빈_목록이면_items_가_빈다():
    async with client(_app(Recorder([]))) as c:
        response = await c.get("/v1/shops/3/visits/12/notifications")
    assert (response.status_code, response.json()) == (200, {"items": []})


@pytest.mark.parametrize("visit_id", ["0", "-1", "9223372036854775808", "abc", "1.5"])
async def test_방문_ID_가_범위_밖이거나_정수가_아니면_422_다(visit_id):
    stub = Recorder([])
    async with client(_app(stub)) as c:
        response = await c.get(f"/v1/shops/3/visits/{visit_id}/notifications")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []
```

`backend/apps/notification/tests/adapter/test_resend_notification_router.py`:

```python
"""다시 보내기 — reservation:write(직원도). 201 {message_id}. 종류는 여섯 중 하나여야 하고(422) 도메인 오류는 표대로."""
import pytest

from notification.adapter.inbound.api.v1.resend_notification_router import resend_notification_router
from notification.dependencies.resend_notification_provider import get_resend_notification_use_case
from notification.domain.errors import (
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    TemplateNotApprovedError,
)
from notification.domain.value_objects.message_kind import KINDS
from notification.tests.helpers.api import STAFF, Recorder, StubShopAccess, build_app, client, error_of

PATH = "/v1/shops/3/visits/12/notifications/confirm/resend"


def _app(stub, access=None):
    return build_app(resend_notification_router, get_resend_notification_use_case, stub, access)


@pytest.mark.parametrize("kind", KINDS)
async def test_직원도_다시_보내고_201_에_새_줄의_ID_를_받는다(kind):
    stub = Recorder(42)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post(f"/v1/shops/3/visits/12/notifications/{kind}/resend")
    assert (response.status_code, response.json()) == (201, {"message_id": 42})
    [command] = stub.calls
    assert (command.ctx.shop_id, command.ctx.member_id, command.visit_id, command.kind) == (3, 11, 12, kind)


async def test_예약_권한이_없는_멤버는_403_이다():
    """N2·설계 9.6"""
    stub = Recorder(42)
    async with client(_app(stub, StubShopAccess(frozenset({"record:write"}), role="staff"))) as c:
        response = await c.post(PATH)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("kind", ["CONFIRM", "sms", "confirm ", "confirm%0A", "0"])
async def test_없는_종류는_422_다(kind):
    stub = Recorder(42)
    async with client(_app(stub)) as c:
        response = await c.post(f"/v1/shops/3/visits/12/notifications/{kind}/resend")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("visit_id", ["0", "9223372036854775808", "abc"])
async def test_방문_ID_가_범위_밖이거나_정수가_아니면_422_다(visit_id):
    stub = Recorder(42)
    async with client(_app(stub)) as c:
        response = await c.post(f"/v1/shops/3/visits/{visit_id}/notifications/confirm/resend")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (ChannelNotLinkedError("연동 먼저"), (409, "NOTIFICATION_CHANNEL_NOT_LINKED")),
    (TemplateNotApprovedError("미승인"), (409, "NOTIFICATION_TEMPLATE_NOT_APPROVED")),
    (MessageNotFoundError("없음"), (404, "NOTIFICATION_MESSAGE_NOT_FOUND")),
    (MessageAlreadyPendingError("대기 중"), (409, "NOTIFICATION_ALREADY_PENDING")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.post(PATH)
    assert error_of(response) == expected
```

`backend/apps/notification/tests/app/services/test_dispatcher.py`:

```diff
@@ -239,6 +239,18 @@ async def test_보내기_전_검사에_걸리면_이유를_적고_취소한다(b
     assert report.canceled == 1 and world.sent() == []
 
 
+async def test_매장이_직접_누른_재발송은_설정이_꺼진_종류여도_보낸다():
+    """[다시 보내기]로 만든 줄(requested_by_member_id)은 setting_off 검사를 건너뛴다. 자동 줄은 그대로 취소."""
+    world = _World(confirm_enabled=False)
+    world.queue(id=1, requested_by_member_id=11)
+    world.queue(id=2, visit_id=2)
+
+    report = await world.run()
+
+    assert (world.row(1).status, world.row(2).canceled_reason) == (ACCEPTED, "setting_off")
+    assert (report.sent, report.canceled) == (1, 1)
+
+
 async def test_템플릿이_검수_중이면_10분_뒤로_미룬다():
     world = _World()
     world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)
```

`backend/apps/notification/tests/app/use_cases/test_get_notification_message_interactor.py`:

```python
"""줄 하나의 상태(알림장 보내기 직후 폴링용) — 없거나 다른 매장이면 404. 실패 줄이면 share_text 가 함께 온다."""
import pytest

from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.domain.errors import MessageNotFoundError
from notification.domain.value_objects.message_status import ACCEPTED, FAILED
from notification.tests.helpers.builders import ctx, kst, message
from notification.tests.helpers.message_world import MessageWorld

VARIABLES = {"starts_at": kst(10, 16, 14).isoformat()}


async def test_있으면_줄을_돌려주고_실패_줄에만_share_text_가_있다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=ACCEPTED, variables=VARIABLES)
    world.messages.rows[2] = message(id=2, status=FAILED, variables=VARIABLES)

    accepted = await world.get.get_notification_message(GetNotificationMessageQuery(ctx=ctx(), message_id=1))
    failed = await world.get.get_notification_message(GetNotificationMessageQuery(ctx=ctx(), message_id=2))

    assert (accepted.message.id, accepted.share_text) == (1, None)
    assert (failed.message.id, failed.share_text) == (2, "[두부네] 10월 16일(금) 14:00 예약이 접수되었어요.")


@pytest.mark.parametrize("message_id, shop_id", [(9, 1), (1, 2)], ids=["없는 줄", "다른 매장"])
async def test_없거나_다른_매장의_줄이면_404_다(message_id, shop_id):
    """N1"""
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=FAILED, variables=VARIABLES)

    with pytest.raises(MessageNotFoundError):
        await world.get.get_notification_message(GetNotificationMessageQuery(ctx=ctx(shop_id=shop_id),
                                                                             message_id=message_id))
```

`backend/apps/notification/tests/app/use_cases/test_list_visit_notifications_interactor.py`:

```python
"""방문별 발송 내역 — 최신순, 실패 줄에만 share_text(문자용 문안). 익명화된 고객이면 null. 다른 매장의 방문은 빈 목록."""
from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT, REPORT
from notification.domain.value_objects.message_status import CANCELED, FAILED, SCHEDULED, SENT
from notification.tests.helpers.builders import ctx, kst, message
from notification.tests.helpers.message_world import MessageWorld

STARTS = kst(10, 16, 14)       # 16일(금) 14:00
URL = "https://a/" + "t" * 43
VARIABLES = {"starts_at": STARTS.isoformat()}


def _query(visit_id=1, shop_id=1) -> ListVisitNotificationsQuery:
    return ListVisitNotificationsQuery(ctx=ctx(shop_id=shop_id), visit_id=visit_id)


async def test_최신순이고_실패_줄에만_share_text_가_있다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=SENT, created_at=kst(10, 14, 11), variables=VARIABLES)
    world.messages.rows[2] = message(id=2, status=FAILED, error_kind="permanent", created_at=kst(10, 14, 12),
                                     variables=VARIABLES, pet_id=101)
    world.messages.rows[3] = message(id=3, status=CANCELED, canceled_reason="setting_off", created_at=kst(10, 14, 12),
                                     variables=VARIABLES)
    world.messages.rows[4] = message(id=4, status=SCHEDULED, created_at=kst(10, 14, 10), variables=VARIABLES)
    world.messages.rows[5] = message(id=5, visit_id=2, status=FAILED, created_at=kst(10, 14, 13), variables=VARIABLES)

    views = await world.list.list_visit_notifications(_query())

    assert [(v.message.id, v.share_text) for v in views] == [
        (3, None), (2, "[두부네] 10월 16일(금) 14:00 예약이 접수되었어요."), (1, None), (4, None)]


async def test_대상은_반려동물_이름이고_없으면_보호자_이름에_님이다():
    world = MessageWorld()
    variables = {**VARIABLES, "completed_at": kst(9, 16, 14).isoformat(), "interval_weeks": "4"}
    world.messages.rows[1] = message(id=1, kind=NEXT_VISIT, status=FAILED, pet_id=101, variables=variables)
    world.messages.rows[2] = message(id=2, kind=NEXT_VISIT, status=FAILED, pet_id=None, variables=variables,
                                     created_at=kst(10, 14, 12))

    views = await world.list.list_visit_notifications(_query())

    assert [v.share_text for v in views] == ["[두부네] 김민지님 미용한 지 4주가 지났어요.", "[두부네] 콩이 미용한 지 4주가 지났어요."]


async def test_알림장의_share_text_에는_주소가_든다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, kind=REPORT, status=FAILED, pet_id=101,
                                     variables={**VARIABLES, "url": URL, "expires_at": ""})

    [view] = await world.list.list_visit_notifications(_query())

    assert view.share_text == f"[두부네] 알림장 {URL}"


async def test_익명화된_고객의_실패_줄은_share_text_가_없다():
    world = MessageWorld()
    world.directory.contacts.pop(1)
    world.messages.rows[1] = message(id=1, kind=CONFIRM, status=FAILED, variables=VARIABLES)

    [view] = await world.list.list_visit_notifications(_query())

    assert view.message.status == FAILED and view.share_text is None


async def test_다른_매장의_방문이거나_없는_방문이면_빈_목록이다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=FAILED, variables=VARIABLES)

    assert await world.list.list_visit_notifications(_query(visit_id=1, shop_id=2)) == []
    assert await world.list.list_visit_notifications(_query(visit_id=9)) == []
```

`backend/apps/notification/tests/app/use_cases/test_resend_notification_interactor.py`:

```python
"""다시 보내기 — 채널 linked·템플릿 approved 여야 하고 설정은 보지 않는다. 가장 최근 줄이 없으면 404, 대기 중이면 409,
끝난 줄(취소·성공·실패)이면 그 줄의 variables·pet_id 로 지금 보낼 새 줄을 만들고 디스패처를 깨운다."""
import pytest

from notification.app.dtos.resend_notification_dto import ResendNotificationCommand
from notification.domain.errors import (
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    TemplateNotApprovedError,
)
from notification.domain.value_objects.channel_status import UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, REMINDER
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    FAILED,
    FALLBACK_SENT,
    SCHEDULED,
    SENDING,
    SENT,
)
from notification.domain.value_objects.template_status import PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, message, settings, template
from notification.tests.helpers.message_world import NOW, MessageWorld

VARIABLES = {"starts_at": kst(10, 16, 14).isoformat()}
COMMAND = ResendNotificationCommand(ctx=ctx(member_id=11), visit_id=1, kind=CONFIRM)


def _failed(**overrides):
    fields = dict(id=1, status=FAILED, error_kind="permanent", error_code="3104", pet_id=101, variables=VARIABLES)
    fields.update(overrides)
    return message(**fields)


@pytest.mark.parametrize("status", [FAILED, SENT, FALLBACK_SENT, CANCELED])
async def test_끝난_줄이면_같은_재료로_지금_보낼_새_줄을_만들고_깨운다(status):
    world = MessageWorld()
    world.messages.rows[1] = _failed(status=status)

    message_id = await world.resend.resend_notification(COMMAND)

    created = world.messages.rows[message_id]
    assert message_id == 2
    assert (created.visit_id, created.customer_id, created.pet_id, created.kind, created.status) == (
        1, 1, 101, CONFIRM, SCHEDULED)
    assert (created.scheduled_at, created.variables, created.requested_by_member_id) == (NOW, VARIABLES, 11)
    assert world.journal[-2:] == [("create_message", 1, CONFIRM), ("wake",)]


async def test_설정이_꺼진_종류여도_매장이_직접_누른_것이니_보낸다():
    world = MessageWorld()
    world.settings.rows[1] = settings(confirm_enabled=False)
    world.messages.rows[1] = _failed(status=CANCELED, canceled_reason="setting_off")

    assert await world.resend.resend_notification(COMMAND) == 2


@pytest.mark.parametrize("status", [SCHEDULED, SENDING, ACCEPTED])
async def test_가장_최근_줄이_대기_중이면_409_이고_만들지_않는다(status):
    """N5"""
    world = MessageWorld()
    world.messages.rows[1] = _failed(id=1, created_at=kst(10, 14, 10))
    world.messages.rows[2] = _failed(id=2, status=status, created_at=kst(10, 14, 11))

    with pytest.raises(MessageAlreadyPendingError):
        await world.resend.resend_notification(COMMAND)
    assert len(world.messages.rows) == 2 and ("wake",) not in world.journal


async def test_가장_최근_줄의_재료를_쓴다():
    world = MessageWorld()
    old = {"starts_at": kst(10, 15, 14).isoformat()}
    world.messages.rows[1] = _failed(id=1, status=SENT, variables=old, created_at=kst(10, 14, 10))
    world.messages.rows[2] = _failed(id=2, status=FAILED, variables=VARIABLES, pet_id=None, created_at=kst(10, 14, 11))

    message_id = await world.resend.resend_notification(COMMAND)

    assert (world.messages.rows[message_id].variables, world.messages.rows[message_id].pet_id) == (VARIABLES, None)


@pytest.mark.parametrize("rows", [
    {}, {1: _failed(kind=REMINDER)}, {1: _failed(visit_id=2)}, {1: _failed(shop_id=2, visit_id=1)},
], ids=["줄 없음", "다른 종류", "다른 방문", "다른 매장"])
async def test_이_매장_방문_종류의_줄이_없으면_404_다(rows):
    """N1"""
    world = MessageWorld()
    world.messages.rows.update(rows)

    with pytest.raises(MessageNotFoundError):
        await world.resend.resend_notification(COMMAND)
    assert ("wake",) not in world.journal


@pytest.mark.parametrize("status", [None, UNLINKED])
async def test_채널이_linked_가_아니면_409_NOT_LINKED_다(status):
    world = MessageWorld()
    world.channels.rows.pop(1)
    if status is not None:
        world.channels.rows[1] = channel(status=status, unlinked_at=NOW)
    world.messages.rows[1] = _failed()

    with pytest.raises(ChannelNotLinkedError):
        await world.resend.resend_notification(COMMAND)


@pytest.mark.parametrize("break_world", [
    lambda w: w.templates.rows.pop((1, CONFIRM)),
    lambda w: w.templates.rows.__setitem__((1, CONFIRM), template(status=PENDING, decided_at=None)),
    lambda w: w.templates.rows.__setitem__((1, CONFIRM), template(status=REJECTED, rejected_reason="x")),
], ids=["템플릿 없음", "검수 중", "반려"])
async def test_템플릿이_approved_가_아니면_409_TEMPLATE_NOT_APPROVED_다(break_world):
    world = MessageWorld()
    break_world(world)
    world.messages.rows[1] = _failed()

    with pytest.raises(TemplateNotApprovedError):
        await world.resend.resend_notification(COMMAND)
    assert len(world.messages.rows) == 1
```

`backend/apps/notification/tests/helpers/message_world.py`:

```python
"""발송 내역·다시 보내기·단건 조회 인터랙터 테스트의 세계 — 연동된 매장 1(채널 linked·설정 기본값·템플릿 6종 approved)과
고객 1·반려동물 101. wake 는 journal 에 ("wake",) 로 남는다."""
from __future__ import annotations

from hub.app.dtos.shop_profile import ShopProfile
from notification.app.use_cases.get_notification_message_interactor import GetNotificationMessageInteractor
from notification.app.use_cases.list_visit_notifications_interactor import ListVisitNotificationsInteractor
from notification.app.use_cases.resend_notification_interactor import ResendNotificationInteractor
from notification.domain.value_objects.message_kind import KINDS
from notification.tests.helpers.builders import TZ, channel, kst, settings, template
from notification.tests.helpers.fakes import (
    FakeChannels,
    FakeDirectory,
    FakeMessages,
    FakeSettings,
    FakeShopProfile,
    FakeTemplates,
    Journal,
)

NOW = kst(10, 14, 11)
SHOP_NAME = "두부네"


class MessageWorld:
    def __init__(self, *, now=NOW) -> None:
        self.journal = Journal()
        self.channels = FakeChannels(self.journal)
        self.settings = FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.shops = FakeShopProfile({1: ShopProfile(shop_id=1, name=SHOP_NAME, phone=None, address=None,
                                                     timezone=TZ, open=True)})
        self.directory = FakeDirectory()
        self.directory.family()
        self.now = now
        self.channels.rows[1] = channel()
        self.settings.rows[1] = settings()
        for i, kind in enumerate(KINDS, start=1):
            self.templates.rows[(1, kind)] = template(id=i, kind=kind, provider_template_id=f"KA01TP000{i}")

    def wake(self) -> None:
        self.journal.append(("wake",))

    @property
    def list(self) -> ListVisitNotificationsInteractor:
        return ListVisitNotificationsInteractor(messages=self.messages, shops=self.shops, directory=self.directory)

    @property
    def get(self) -> GetNotificationMessageInteractor:
        return GetNotificationMessageInteractor(messages=self.messages, shops=self.shops, directory=self.directory)

    @property
    def resend(self) -> ResendNotificationInteractor:
        return ResendNotificationInteractor(
            channels=self.channels, templates=self.templates, messages=self.messages, now=lambda: self.now,
            wake=self.wake)
```

`backend/tests/integration/test_notification_messages_wiring.py`:

```python
"""방문별 발송 내역·다시 보내기·단건 조회를 실제 배선(프로바이더·DB·매장 접근 확인·main.py 가 꽂은 허브 포트)으로 돌린다.

채널·설정·템플릿은 온보딩 API 로 만들고 템플릿만 SQL 로 approved. 디스패처는 FakeGateway 로 run_once 를 직접 돈다.
첫 테스트는 테넌트 격리다(하네스 규칙). 응답 어디에도 번호·variables·업체 메시지 ID 가 없어야 한다(N12).
알림장 주소는 변수로 들지 않는다 — share_text 에 "/r/" 가 있는지만 본다.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.dependencies.dispatcher_provider import build_dispatcher
from notification.dependencies.notification_wiring import get_message_gateway
from notification.domain.services.templates import format_when
from tests.integration.support import accept_invite, bearer, error_of, make_operator, shop_with_owner, staff_invite

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
SHOP_NAME = "Hiss Haus"
TOKEN = {"search_id": "hisshaus", "admin_phone": "01012345678", "category_code": "003001"}
LINK = {**TOKEN, "token": "000000"}
PHONE_OK, PHONE_BAD = "010-1234-5678", "010-1234-0000"     # 끝 0000 은 FakeGateway 가 영구 실패로 답한다
CUSTOMER = {"name": "김민지", "phone": PHONE_OK, "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}
SECRETS = ("variables", "provider_message_id", "fake-", "starts_at", "error_code", "3104", "customer_id", "pet_id",
           "01012340000", "1234-0000", "01012345678", "1234-5678")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


@pytest.fixture
def gateway(wired):
    import main

    fake = FakeGateway()
    main.app.dependency_overrides[get_message_gateway] = lambda: fake
    yield fake
    main.app.dependency_overrides.pop(get_message_gateway, None)


async def _linked_shop(wired, name=SHOP_NAME, owner_name="사장님"):
    """연동을 마치고 기본 5종 템플릿을 approved 로 둔 매장. (shop_id, owner 로그인, 헤더)"""
    operator = await make_operator(wired, f"운영자-{name}")
    shop_id, owner = await shop_with_owner(wired, operator, name, owner_name)
    headers = bearer(owner["access_token"])
    assert (await wired.api.post(f"/v1/shops/{shop_id}/notification/channel/token", json=TOKEN,
                                 headers=headers)).status_code == 202
    linked = await wired.api.post(f"/v1/shops/{shop_id}/notification/channel", json=LINK, headers=headers)
    assert linked.status_code == 200, linked.text
    await wired.execute("UPDATE notification_templates SET status = 'approved' WHERE shop_id = :shop_id",
                        shop_id=shop_id)
    return shop_id, owner, headers


async def _family(wired, shop_id, headers, phone=PHONE_OK) -> tuple[int, int]:
    response = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                    json={"customer": {**CUSTOMER, "phone": phone}, "pet": PET})
    assert response.status_code == 201, response.text
    body = response.json()
    return body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _booked(wired, shop_id, headers, starts_at: datetime, phone=PHONE_OK) -> int:
    customer_id, pet_id = await _family(wired, shop_id, headers, phone)
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
                                  json={"customer_id": customer_id, "pet_ids": [pet_id],
                                        "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _reported(wired, shop_id, headers, phone=PHONE_OK) -> int:
    """어제 방문을 시작·기록·완료하고 알림장을 보낸다 — report 줄이 생긴다. 방문 ID."""
    visit_id = await _booked(wired, shop_id, headers, _at(-1, 11), phone)
    await _transition(wired, shop_id, headers, visit_id, "start")
    written = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                  json={"care_note": "눈물 자국을 닦았어요", "media": []})
    assert written.status_code == 200, written.text
    await _transition(wired, shop_id, headers, visit_id, "complete")
    sent = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/report", headers=headers,
                               json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text
    return visit_id


async def _transition(wired, shop_id, headers, visit_id, action) -> None:
    response = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                    json={"visit_ids": [visit_id], "action": action})
    assert response.status_code == 200, response.text


async def _run_twice(wired, gateway: FakeGateway) -> None:
    """집어 보내고(accepted) 6초 뒤 상태를 물어 최종 상태로."""
    sessions = async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)
    for now in (_now(), _now() + timedelta(seconds=6)):
        async with sessions() as session:
            await build_dispatcher(session, gateway=gateway, now=lambda: now).run_once()


async def _items(wired, shop_id, visit_id, headers) -> list[dict]:
    response = await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}/notifications", headers=headers)
    assert response.status_code == 200, response.text
    for secret in SECRETS:
        assert secret not in response.text, secret
    return response.json()["items"]


def _brief(items: list[dict]) -> list[tuple]:
    return [(i["kind"], i["status"]) for i in items]


async def test_다른_매장의_세_경로는_403_이고_다른_매장의_message_id_는_404_visit_id_는_빈_목록이다(wired, gateway):
    """N1·N2"""
    a_shop, _, a = await _linked_shop(wired, "A 매장", "A사장")
    b_shop, _, b = await _linked_shop(wired, "B 매장", "B사장")
    b_visit = await _booked(wired, b_shop, b, _at(3, 14))
    [_, b_confirm] = await _items(wired, b_shop, b_visit, b)

    responses = [
        await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_visit}/notifications", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits/{b_visit}/notifications/confirm/resend", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/notifications/{b_confirm['message_id']}", headers=a),
    ]
    assert [error_of(r) for r in responses] == [(403, "NOT_A_MEMBER")] * 3

    assert error_of(await wired.api.get(f"/v1/shops/{a_shop}/notifications/{b_confirm['message_id']}",
                                        headers=a)) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")
    assert await _items(wired, a_shop, b_visit, a) == []
    assert error_of(await wired.api.post(f"/v1/shops/{a_shop}/visits/{b_visit}/notifications/confirm/resend",
                                         headers=a)) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")
    assert _brief(await _items(wired, b_shop, b_visit, b)) == [("reminder", "scheduled"), ("confirm", "scheduled")]


async def test_예약하면_confirm_reminder_가_보이고_디스패처가_돌면_confirm_은_sent_이며_단건_조회와_같다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    visit_id = await _booked(wired, shop_id, o, _at(3, 14))

    before = await _items(wired, shop_id, visit_id, o)
    assert _brief(before) == [("reminder", "scheduled"), ("confirm", "scheduled")]
    reminder, confirm = before
    assert reminder["scheduled_at"] == _at(2, 18).isoformat()
    assert all(i["share_text"] is None and i["sent_at"] is None for i in before)

    await _run_twice(wired, gateway)

    after = await _items(wired, shop_id, visit_id, o)
    assert _brief(after) == [("reminder", "scheduled"), ("confirm", "sent")]
    assert (after[1]["channel_used"], after[1]["share_text"]) == ("alimtalk", None)
    assert after[1]["sent_at"].endswith("+09:00")
    single = await wired.api.get(f"/v1/shops/{shop_id}/notifications/{confirm['message_id']}", headers=o)
    assert single.status_code == 200 and single.json() == after[1]


async def test_영구_실패_줄은_share_text_가_있고_직원이_다시_보내면_새_줄이_생기며_두_번째는_409_다(wired, gateway):
    """N5·N12"""
    shop_id, owner, o = await _linked_shop(wired)
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])
    starts_at = _at(3, 14)
    visit_id = await _booked(wired, shop_id, o, starts_at, PHONE_BAD)
    await _run_twice(wired, gateway)

    [reminder, failed] = await _items(wired, shop_id, visit_id, s)
    assert (failed["kind"], failed["status"], failed["error_kind"]) == ("confirm", "failed", "permanent")
    assert failed["share_text"] == f"[{SHOP_NAME}] {format_when(starts_at, 'Asia/Seoul')} 예약이 접수되었어요."
    assert reminder["share_text"] is None

    resent = await wired.api.post(f"/v1/shops/{shop_id}/visits/{visit_id}/notifications/confirm/resend", headers=s)
    assert resent.status_code == 201, resent.text
    message_id = resent.json()["message_id"]
    items = await _items(wired, shop_id, visit_id, s)
    assert _brief(items) == [("confirm", "scheduled"), ("reminder", "scheduled"), ("confirm", "failed")]
    new = items[0]
    assert (new["message_id"], new["requested_by_member_id"] is not None, new["share_text"]) == (message_id, True, None)
    assert error_of(await wired.api.post(f"/v1/shops/{shop_id}/visits/{visit_id}/notifications/confirm/resend",
                                         headers=s)) == (409, "NOTIFICATION_ALREADY_PENDING")
    assert len(await _items(wired, shop_id, visit_id, s)) == 3


async def test_알림장은_보내면_report_줄이_생겨_sent_가_되고_실패_줄의_share_text_에는_주소가_있다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    ok_visit = await _reported(wired, shop_id, o)
    bad_visit = await _reported(wired, shop_id, o, PHONE_BAD)
    assert _brief(await _items(wired, shop_id, ok_visit, o))[0] == ("report", "scheduled")

    await _run_twice(wired, gateway)

    ok = await _items(wired, shop_id, ok_visit, o)
    assert _brief(ok) == [("report", "sent"), ("confirm", "sent")]
    assert all(i["share_text"] is None for i in ok)
    bad = await _items(wired, shop_id, bad_visit, o)
    assert _brief(bad) == [("report", "failed"), ("confirm", "failed")]
    assert bad[0]["share_text"].startswith(f"[{SHOP_NAME}] 알림장 ") and "/r/" in bad[0]["share_text"]
    assert "/r/" not in bad[1]["share_text"]


async def test_없는_종류는_422_이고_줄이_없는_종류는_404_다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    visit_id = await _booked(wired, shop_id, o, _at(3, 14))
    base = f"/v1/shops/{shop_id}/visits/{visit_id}/notifications"

    assert error_of(await wired.api.post(f"{base}/sms/resend", headers=o)) == (422, "VALIDATION_ERROR")
    assert error_of(await wired.api.post(f"{base}/cancel/resend", headers=o)) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")
    assert error_of(await wired.api.post(f"{base}/confirm/resend", headers=o)) == (409, "NOTIFICATION_ALREADY_PENDING")
    assert len(await _items(wired, shop_id, visit_id, o)) == 2
```

`backend/tests/test_hub_port_binding.py`:

```diff
@@ -8,6 +8,8 @@ from core.shop_guard import get_shop_access_port
 from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
 from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
 from notification.dependencies.dispatcher_ports import dispatcher_ports
+from notification.dependencies.hub_ports import get_customer_directory as get_notification_customer_directory
+from notification.dependencies.hub_ports import get_shop_profile as get_notification_shop_profile
 from tenancy.dependencies.hub_ports import get_user_directory
 from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
 from core.security import get_current_user_id
@@ -47,6 +49,15 @@ def test_notification_구독자가_버스에_등록되어_있다():
     assert handle_visit_event in subscribers()
 
 
+def test_notification_의_매장_공개_정보와_고객_연락처_자리는_tenancy_customer_의_구현으로_채운다():
+    """share_text 가 매장 이름·보호자 이름을 읽는 요청 안의 자리 — 디스패처의 공장과 같은 프로바이더다."""
+    assert main.app.dependency_overrides[get_notification_shop_profile] is get_shop_profile_use_case
+    assert main.app.dependency_overrides[get_notification_customer_directory] is get_customer_directory_use_case
+    for slot in (get_notification_shop_profile, get_notification_customer_directory):
+        with pytest.raises(RuntimeError):
+            slot()
+
+
 def test_디스패처의_허브_포트_공장은_tenancy_customer_visit_의_프로바이더다():
     ports = dispatcher_ports()
     assert ports.shop_profile is get_shop_profile_use_case
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

- 단위 `docker compose run --rm --no-deps backend pytest apps/notification tests/test_hub_port_binding.py -q -p no:cacheprovider -m "not integration"` → 수집 오류 7(`No module named 'notification.dependencies.hub_ports'` 등), `Interrupted: 7 errors during collection`.
- 디스패처 `-k 직접_누른` → 1 failed(`setting_off` 로 취소됨).
- 통합 `… run --rm backend pytest tests/integration/test_notification_messages_wiring.py -m integration` → 5 failed(경로 없음).

구현 뒤 첫 실행에서 전부 통과했다(테스트 쪽 수정 없음).

- [ ] **Step 3: 구현한다**

`backend/apps/notification/dependencies/hub_ports.py`:

```python
"""허브 포트 자리 — notification 이 요청 안에서 쓰는, 다른 스포크가 구현한 포트(share_text 의 매장 이름·보호자 이름).

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
요청 밖(디스패처)의 같은 포트는 dispatcher_ports.py 의 공장 자리다.
"""
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort


def get_customer_directory() -> CustomerDirectoryPort:
    raise RuntimeError("CustomerDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_shop_profile() -> ShopProfilePort:
    raise RuntimeError("ShopProfilePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/notification/app/use_cases/resend_notification_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from notification.app.dtos.resend_notification_dto import ResendNotificationCommand
from notification.app.ports.input.resend_notification_use_case import ResendNotificationUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.errors import (
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    TemplateNotApprovedError,
)
from notification.domain.value_objects.message_status import ACCEPTED, PENDING_STATUSES
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import APPROVED


class ResendNotificationInteractor(ResendNotificationUseCase):
    """[다시 보내기] — 매장이 직접 누른 것이니 설정은 보지 않는다(디스패처도 requested_by_member_id 가 있는 줄은 setting_off 를
    건너뛴다). 이 매장·방문·종류의 가장 최근 줄이 끝나 있어야 하고(취소·성공·실패), 그 줄의 재료로 지금 보낼 새 줄을 만든다.
    같은 방문·종류의 대기 줄은 하나(부분 유일 색인)라 동시에 두 번 눌러도 둘째는 409 다(N5)."""

    def __init__(
        self, channels: ChannelRepository, templates: TemplateRepository, messages: MessageRepository,
        now: Callable[[], datetime], wake: Callable[[], None],
    ) -> None:
        self._channels = channels
        self._templates = templates
        self._messages = messages
        self._now = now
        self._wake = wake

    async def resend_notification(self, command: ResendNotificationCommand) -> int:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("연동된 채널이 없습니다.")
        template = await self._templates.get(ctx, command.kind)
        if template is None or template.status != APPROVED:
            raise TemplateNotApprovedError("아직 승인되지 않은 종류입니다.")
        rows = await self._messages.list_for_visit(ctx, command.visit_id)
        latest = next((m for m in rows if m.kind == command.kind), None)
        if latest is None:
            raise MessageNotFoundError("다시 보낼 알림이 없습니다.")
        if latest.status in PENDING_STATUSES or latest.status == ACCEPTED:
            raise MessageAlreadyPendingError("같은 종류의 알림이 이미 보내는 중입니다.")
        created = await self._messages.create(ctx, NewMessage(
            shop_id=ctx.shop_id, visit_id=command.visit_id, customer_id=latest.customer_id, pet_id=latest.pet_id,
            kind=command.kind, scheduled_at=self._now(), variables=latest.variables,
            requested_by_member_id=ctx.member_id,
        ))
        self._wake()
        return created.id
```

`backend/apps/notification/app/services/message_text.py`:

```diff
@@ -4,7 +4,14 @@ from __future__ import annotations
 from collections.abc import Mapping
 from datetime import datetime
 
-from notification.domain.services.templates import RenderedMessage, render, variables_for
+from hub.app.dtos.customer_contact import CustomerContact
+from hub.app.dtos.shop_context import ShopContext
+from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.shop_profile_port import ShopProfilePort
+from notification.app.dtos.notification_message_dto import NotificationMessageView
+from notification.domain.entities.notification_message import NotificationMessage
+from notification.domain.services.templates import RenderedMessage, render, target_label, variables_for
+from notification.domain.value_objects.message_status import FAILED
 
 
 def _at(value: str | None) -> datetime | None:
@@ -24,3 +31,34 @@ def message_variables(kind: str, *, shop_name: str, target: str, tz: str, variab
 
 def message_text(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> RenderedMessage:
     return render(kind, message_variables(kind, shop_name=shop_name, target=target, tz=tz, variables=variables))
+
+
+async def message_target(
+    ctx: ShopContext, directory: CustomerDirectoryPort, message: NotificationMessage, contact: CustomerContact,
+) -> str:
+    """`#{대상}` — 반려동물 이름이 있으면 그것, 없으면 보호자 이름에 '님'. 보낼 때와 share_text 가 같은 재료로 만든다."""
+    pet_name = None
+    if message.pet_id is not None:
+        pet = (await directory.briefs(ctx, [], [message.pet_id])).pets.get(message.pet_id)
+        pet_name = pet.name if pet is not None else None
+    return target_label(pet_name, contact.name)
+
+
+async def message_views(
+    ctx: ShopContext, messages: list[NotificationMessage], shops: ShopProfilePort, directory: CustomerDirectoryPort,
+) -> list[NotificationMessageView]:
+    """실패 줄에만 문자용 문안(share_text)을 붙인다 — 매장 이름·보호자·반려동물 이름은 지금 포트로 읽는다. 익명화됐으면 None."""
+    profile = None
+    views = []
+    for m in messages:
+        text = None
+        if m.status == FAILED:
+            if profile is None:
+                profile = await shops.public_profile(ctx.shop_id)
+            contact = await directory.contact(ctx, m.customer_id)
+            if contact is not None:
+                target = await message_target(ctx, directory, m, contact)
+                text = message_text(m.kind, shop_name=profile.name, target=target, tz=ctx.timezone,
+                                    variables=m.variables).sms_text
+        views.append(NotificationMessageView(message=m, share_text=text))
+    return views
```

`backend/apps/notification/adapter/inbound/api/path_params.py`:

```python
"""notification 경로 변수. bigint 를 넘는 값은 DB 에 닿기 전에 422 로 막고, 종류는 여섯 중 하나여야 한다."""
from typing import Annotated

from fastapi import Path

from notification.domain.value_objects.message_kind import KINDS

_MAX_BIGINT = 9_223_372_036_854_775_807

VisitId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
MessageId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
MessageKind = Annotated[str, Path(pattern=f"^({'|'.join(KINDS)})$")]
```

`backend/apps/notification/adapter/inbound/api/schemas/notification_message_schema.py`:

```python
"""발송 내역의 줄 하나(MessageItem) — 칸을 하나하나 적는다. variables(주소)·업체 메시지 ID·오류 코드·고객·반려동물 ID 는
내보내지 않는다(N12). 주소는 실패 줄의 share_text 문안에만 든다(설계 7.2)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from notification.app.dtos.notification_message_dto import NotificationMessageView


class MessageItemSchema(BaseModel):
    message_id: int
    kind: str
    status: str                    # scheduled · sending · accepted · sent · fallback_sent · failed · canceled
    channel_used: str | None       # alimtalk · sms · lms
    scheduled_at: datetime         # 매장 시간대
    sent_at: datetime | None
    error_kind: str | None         # transient · permanent
    canceled_reason: str | None
    requested_by_member_id: int | None
    share_text: str | None         # 실패 줄에만 — 문자용 문안

    @classmethod
    def of(cls, view: NotificationMessageView, tz: str) -> MessageItemSchema:
        m, zone = view.message, ZoneInfo(tz)
        return cls(
            message_id=m.id, kind=m.kind, status=m.status, channel_used=m.channel_used,
            scheduled_at=m.scheduled_at.astimezone(zone),
            sent_at=m.sent_at.astimezone(zone) if m.sent_at is not None else None,
            error_kind=m.error_kind, canceled_reason=m.canceled_reason,
            requested_by_member_id=m.requested_by_member_id, share_text=view.share_text,
        )


class MessageListSchema(BaseModel):
    items: list[MessageItemSchema]   # 최신순

    @classmethod
    def of(cls, views: list[NotificationMessageView], tz: str) -> MessageListSchema:
        return cls(items=[MessageItemSchema.of(v, tz) for v in views])
```

`backend/apps/notification/adapter/inbound/api/schemas/resend_notification_schema.py`:

```python
from pydantic import BaseModel


class MessageCreatedSchema(BaseModel):
    message_id: int
```

`backend/apps/notification/adapter/inbound/api/v1/get_notification_message_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.path_params import MessageId
from notification.adapter.inbound.api.schemas.notification_message_schema import MessageItemSchema
from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.app.ports.input.get_notification_message_use_case import GetNotificationMessageUseCase
from notification.dependencies.get_notification_message_provider import get_get_notification_message_use_case

get_notification_message_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@get_notification_message_router.get("/{shop_id}/notifications/{message_id}", response_model=MessageItemSchema)
async def get_notification_message(
    message_id: MessageId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetNotificationMessageUseCase = Depends(get_get_notification_message_use_case),
) -> MessageItemSchema:
    view = await use_case.get_notification_message(GetNotificationMessageQuery(ctx=ctx, message_id=message_id))
    return MessageItemSchema.of(view, ctx.timezone)
```

`backend/apps/notification/adapter/inbound/api/v1/list_visit_notifications_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.path_params import VisitId
from notification.adapter.inbound.api.schemas.notification_message_schema import MessageListSchema
from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.app.ports.input.list_visit_notifications_use_case import ListVisitNotificationsUseCase
from notification.dependencies.list_visit_notifications_provider import get_list_visit_notifications_use_case

list_visit_notifications_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@list_visit_notifications_router.get("/{shop_id}/visits/{visit_id}/notifications", response_model=MessageListSchema)
async def list_visit_notifications(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListVisitNotificationsUseCase = Depends(get_list_visit_notifications_use_case),
) -> MessageListSchema:
    views = await use_case.list_visit_notifications(ListVisitNotificationsQuery(ctx=ctx, visit_id=visit_id))
    return MessageListSchema.of(views, ctx.timezone)
```

`backend/apps/notification/adapter/inbound/api/v1/resend_notification_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.path_params import MessageKind, VisitId
from notification.adapter.inbound.api.schemas.resend_notification_schema import MessageCreatedSchema
from notification.app.dtos.resend_notification_dto import ResendNotificationCommand
from notification.app.ports.input.resend_notification_use_case import ResendNotificationUseCase
from notification.dependencies.resend_notification_provider import get_resend_notification_use_case

resend_notification_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@resend_notification_router.post(
    "/{shop_id}/visits/{visit_id}/notifications/{kind}/resend", response_model=MessageCreatedSchema, status_code=201,
)
async def resend_notification(
    visit_id: VisitId,
    kind: MessageKind,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: ResendNotificationUseCase = Depends(get_resend_notification_use_case),
) -> MessageCreatedSchema:
    message_id = await use_case.resend_notification(ResendNotificationCommand(ctx=ctx, visit_id=visit_id, kind=kind))
    return MessageCreatedSchema(message_id=message_id)
```

`backend/apps/notification/app/dtos/get_notification_message_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetNotificationMessageQuery:
    ctx: ShopContext
    message_id: int
```

`backend/apps/notification/app/dtos/list_visit_notifications_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListVisitNotificationsQuery:
    ctx: ShopContext
    visit_id: int
```

`backend/apps/notification/app/dtos/notification_message_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from notification.domain.entities.notification_message import NotificationMessage


@dataclass(frozen=True)
class NotificationMessageView:
    """발송 내역의 줄 하나. share_text 는 실패 줄의 문자용 문안(설계 7.2) — 그 밖은 None."""

    message: NotificationMessage
    share_text: str | None
```

`backend/apps/notification/app/dtos/resend_notification_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ResendNotificationCommand:
    ctx: ShopContext
    visit_id: int
    kind: str
```

`backend/apps/notification/app/ports/input/get_notification_message_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView


class GetNotificationMessageUseCase(ABC):
    @abstractmethod
    async def get_notification_message(self, query: GetNotificationMessageQuery) -> NotificationMessageView: ...
```

`backend/apps/notification/app/ports/input/list_visit_notifications_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView


class ListVisitNotificationsUseCase(ABC):
    @abstractmethod
    async def list_visit_notifications(self, query: ListVisitNotificationsQuery) -> list[NotificationMessageView]: ...
```

`backend/apps/notification/app/ports/input/resend_notification_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.resend_notification_dto import ResendNotificationCommand


class ResendNotificationUseCase(ABC):
    @abstractmethod
    async def resend_notification(self, command: ResendNotificationCommand) -> int:
        """새 줄의 message_id."""
```

`backend/apps/notification/app/services/dispatcher.py`:

```diff
@@ -29,7 +29,7 @@ from notification.app.ports.output.message_repository import MessageRepository
 from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
 from notification.app.ports.output.settings_repository import SettingsRepository
 from notification.app.ports.output.template_repository import TemplateRepository
-from notification.app.services.message_text import message_variables
+from notification.app.services.message_text import message_target, message_variables
 from notification.app.services.system_context import system_context
 from notification.domain.entities.notification_message import NotificationMessage
 from notification.domain.services.schedule_rules import (
@@ -40,7 +40,7 @@ from notification.domain.services.schedule_rules import (
     is_too_late,
     retry_at,
 )
-from notification.domain.services.templates import TEMPLATES, TEXT_VERSION, render, sms_channel, target_label
+from notification.domain.services.templates import TEMPLATES, TEXT_VERSION, render, sms_channel
 from notification.domain.value_objects.message_kind import DEFAULT_KINDS, NEXT_VISIT, REMINDER, SCHEDULED_KINDS
 from notification.domain.value_objects.message_status import (
     ACCEPTED,
@@ -160,8 +160,8 @@ class Dispatcher:
         if channel is None or not channel.is_linked:
             return self._cancel(m, "channel_unlinked")
         settings = await self._settings.get(ctx)
-        if settings is None or not settings.enabled_for(m.kind):
-            return self._cancel(m, "setting_off")
+        if settings is None or (not settings.enabled_for(m.kind) and m.requested_by_member_id is None):
+            return self._cancel(m, "setting_off")   # 매장이 직접 누른 재발송은 설정과 무관하게 간다
         template = await self._templates.get(ctx, m.kind)
         if template is None or template.status == REJECTED:
             return self._cancel(m, "template_rejected")
@@ -192,12 +192,8 @@ class Dispatcher:
                            m.shop_id, sent_today, self._daily_cap)
             return replace(m, status=SCHEDULED, scheduled_at=now + DAILY_CAP_DEFER)
 
-        pet_name = None
-        if m.pet_id is not None:
-            pet = (await self._directory.briefs(ctx, [], [m.pet_id])).pets.get(m.pet_id)
-            pet_name = pet.name if pet is not None else None
-        variables = message_variables(m.kind, shop_name=profile.name, target=target_label(pet_name, contact.name),
-                                      tz=tz, variables=m.variables)
+        target = await message_target(ctx, self._directory, m, contact)
+        variables = message_variables(m.kind, shop_name=profile.name, target=target, tz=tz, variables=m.variables)
         rendered = render(m.kind, variables)
         fallback = None
         if channel.can_fallback:
```

`backend/apps/notification/app/use_cases/get_notification_message_interactor.py`:

```python
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.app.ports.input.get_notification_message_use_case import GetNotificationMessageUseCase
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.services.message_text import message_views
from notification.domain.errors import MessageNotFoundError


class GetNotificationMessageInteractor(GetNotificationMessageUseCase):
    """줄 하나(알림장 보내기 직후 폴링용, 설계 8.3). 없거나 다른 매장이면 404(N1)."""

    def __init__(self, messages: MessageRepository, shops: ShopProfilePort, directory: CustomerDirectoryPort) -> None:
        self._messages = messages
        self._shops = shops
        self._directory = directory

    async def get_notification_message(self, query: GetNotificationMessageQuery) -> NotificationMessageView:
        row = await self._messages.get(query.ctx, query.message_id)
        if row is None:
            raise MessageNotFoundError("그 알림이 없습니다.")
        [view] = await message_views(query.ctx, [row], self._shops, self._directory)
        return view
```

`backend/apps/notification/app/use_cases/list_visit_notifications_interactor.py`:

```python
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.app.ports.input.list_visit_notifications_use_case import ListVisitNotificationsUseCase
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.services.message_text import message_views


class ListVisitNotificationsInteractor(ListVisitNotificationsUseCase):
    """그 방문의 줄 전부, 최신순(설계 7.2). notification 은 방문 표를 모르므로 다른 매장의 방문이나 없는 방문은 빈 목록이다."""

    def __init__(self, messages: MessageRepository, shops: ShopProfilePort, directory: CustomerDirectoryPort) -> None:
        self._messages = messages
        self._shops = shops
        self._directory = directory

    async def list_visit_notifications(self, query: ListVisitNotificationsQuery) -> list[NotificationMessageView]:
        rows = await self._messages.list_for_visit(query.ctx, query.visit_id)
        return await message_views(query.ctx, rows, self._shops, self._directory)
```

`backend/apps/notification/dependencies/get_notification_message_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.ports.input.get_notification_message_use_case import GetNotificationMessageUseCase
from notification.app.use_cases.get_notification_message_interactor import GetNotificationMessageInteractor
from notification.dependencies.hub_ports import get_customer_directory, get_shop_profile
from notification.dependencies.notification_wiring import build_message_repository


def get_get_notification_message_use_case(
    db: DbSession,
    shops: ShopProfilePort = Depends(get_shop_profile),
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> GetNotificationMessageUseCase:
    return GetNotificationMessageInteractor(messages=build_message_repository(db), shops=shops, directory=directory)
```

`backend/apps/notification/dependencies/list_visit_notifications_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.ports.input.list_visit_notifications_use_case import ListVisitNotificationsUseCase
from notification.app.use_cases.list_visit_notifications_interactor import ListVisitNotificationsInteractor
from notification.dependencies.hub_ports import get_customer_directory, get_shop_profile
from notification.dependencies.notification_wiring import build_message_repository


def get_list_visit_notifications_use_case(
    db: DbSession,
    shops: ShopProfilePort = Depends(get_shop_profile),
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> ListVisitNotificationsUseCase:
    return ListVisitNotificationsInteractor(messages=build_message_repository(db), shops=shops, directory=directory)
```

`backend/apps/notification/dependencies/resend_notification_provider.py`:

```python
from __future__ import annotations

from core.database import DbSession
from notification.app.ports.input.resend_notification_use_case import ResendNotificationUseCase
from notification.app.services.dispatcher_wakeup import wake
from notification.app.use_cases.resend_notification_interactor import ResendNotificationInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_template_repository,
)
from notification.domain.services.clock import utc_now


def get_resend_notification_use_case(db: DbSession) -> ResendNotificationUseCase:
    return ResendNotificationInteractor(
        channels=build_channel_repository(db), templates=build_template_repository(db),
        messages=build_message_repository(db), now=utc_now, wake=wake,
    )
```

`backend/main.py`:

```diff
@@ -49,13 +49,16 @@ from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
 from media.dependencies.media_library_provider import get_media_library_use_case
 from notification.adapter.inbound.api.error_map import NOTIFICATION_ERROR_STATUS
 from notification.adapter.inbound.api.v1.confirm_sender_router import confirm_sender_router
+from notification.adapter.inbound.api.v1.get_notification_message_router import get_notification_message_router
 from notification.adapter.inbound.api.v1.get_notification_overview_router import get_notification_overview_router
 from notification.adapter.inbound.api.v1.link_channel_router import link_channel_router
+from notification.adapter.inbound.api.v1.list_visit_notifications_router import list_visit_notifications_router
 from notification.adapter.inbound.api.v1.notification_myself_router import notification_myself_router
 from notification.adapter.inbound.api.v1.request_channel_token_router import request_channel_token_router
 from notification.adapter.inbound.api.v1.request_sender_verification_router import (
     request_sender_verification_router,
 )
+from notification.adapter.inbound.api.v1.resend_notification_router import resend_notification_router
 from notification.adapter.inbound.api.v1.unlink_channel_router import unlink_channel_router
 from notification.adapter.inbound.api.v1.update_notification_settings_router import (
     update_notification_settings_router,
@@ -64,6 +67,8 @@ from notification.adapter.inbound.observer.visit_event_subscriber import handle_
 from notification.app.services.dispatcher_wakeup import wake
 from notification.dependencies.dispatcher_ports import DispatcherPorts, configure_dispatcher_ports
 from notification.dependencies.dispatcher_provider import start_dispatcher
+from notification.dependencies.hub_ports import get_customer_directory as get_notification_customer_directory
+from notification.dependencies.hub_ports import get_shop_profile as get_notification_shop_profile
 from notification.dependencies.notification_wiring import get_message_gateway
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
@@ -214,6 +219,10 @@ app.include_router(unlink_channel_router)
 app.include_router(update_notification_settings_router)
 app.include_router(request_sender_verification_router)
 app.include_router(confirm_sender_router)
+# /visits/{visit_id}/notifications 는 visit 의 /visits/{visit_id} 경로들과 겹치지 않는다(뒤에 붙여도 된다).
+app.include_router(list_visit_notifications_router)
+app.include_router(resend_notification_router)
+app.include_router(get_notification_message_router)
 # media
 app.include_router(media_myself_router)
 app.include_router(issue_upload_router)
@@ -238,6 +247,8 @@ app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
 app.dependency_overrides[get_visit_media_library] = get_media_library_use_case
 app.dependency_overrides[get_customer_media_library] = get_media_library_use_case
 app.dependency_overrides[get_shop_profile] = get_shop_profile_use_case
+app.dependency_overrides[get_notification_shop_profile] = get_shop_profile_use_case
+app.dependency_overrides[get_notification_customer_directory] = get_customer_directory_use_case
 # 도메인 이벤트 — visit 이 발행하고 core 의 같은 세션 동기 버스가 구독자에 넘긴다. 구독자는 여기서 꽂는다.
 app.dependency_overrides[get_domain_events] = get_event_bus
 subscribe(handle_visit_event)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 수 |
|---|---|
| 이 작업의 단위(인터랙터 28 + 라우터 32 + 디스패처 1 + 바인딩 1) | 62 passed (notification 단위 + 바인딩 파일 535) |
| 이 작업의 통합(`test_notification_messages_wiring.py`) | 5 passed |
| 단위 전체 (`-m "not integration and not network"`, `--no-deps`) | 1849 passed (시작 1789 + 60) |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken |

이 작업이 더한 테스트는 62 인데 단위 전체는 60 늘었다. 기준 1789 가 T8 보고서 시점의 측정값이라 생긴 차이로 보이며 추적하지 않았다(T7 보고서의 같은 현상).

라우트 표: `print_routes.py` 를 기준(69줄)과 diff → 80줄. T8 의 여덟에 이 작업의 셋을 더해 **열하나**가 늘었다(경로·메서드만, 전부 notification). T8 뒤 표(77줄)와의 diff 가 이 셋이다.
```
> backend GET    /v1/shops/{shop_id}/notifications/{message_id}                      get_notification_message
> backend GET    /v1/shops/{shop_id}/visits/{visit_id}/notifications                 list_visit_notifications
> backend POST   /v1/shops/{shop_id}/visits/{visit_id}/notifications/{kind}/resend   resend_notification
```
`tests/test_hub_port_binding.py` 의 "로그인 없이 열리는 경로" 목록은 그대로다(넷). 통합 세션은 테스트 DB·Redis db 15 에만 붙었고 실제 `api.solapi.com` 은 부르지 않았다(게이트웨이는 전부 `FakeGateway`).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `message_views` 의 `if m.status == FAILED` → `if True`(모든 줄에 share_text) → 단위 `test_list_visit_notifications_interactor.py::test_최신순이고_실패_줄에만_share_text_가_있다`, `test_get_notification_message_interactor.py::test_있으면_줄을_돌려주고_실패_줄에만_share_text_가_있다`; 통합 `::test_예약하면_confirm_reminder_가_보이고_…`, `::test_영구_실패_줄은_share_text_가_있고_…`, `::test_알림장은_보내면_…`
- 재발송의 최근 줄 상태 검사 제거(`if False`) → 단위 `test_resend_notification_interactor.py::test_가장_최근_줄이_대기_중이면_409_이고_만들지_않는다[accepted]` (scheduled·sending 은 스텁 `create` 의 부분 유일 색인 흉내가 같은 409 를 내서 통과하고, `accepted` 가 판별한다; 통합은 scheduled 만 보므로 5 passed)
- `MessageItemSchema` 에 `variables: dict` 추가 → 단위 `test_list_visit_notifications_router.py::test_직원도_목록을_보고_…`, `::test_응답에_variables_업체_ID_오류_코드_고객_ID_칸이_없다`, `test_get_notification_message_router.py::test_직원도_줄_하나를_읽는다`; 통합 5 전부(`_items` 의 N12 검사·스키마 검증 오류)
- pg `MessagePgRepository.get` 의 `shop_id` 조건 제거 → 통합 `::test_다른_매장의_세_경로는_403_이고_다른_매장의_message_id_는_404_visit_id_는_빈_목록이다`(단위는 스텁이라 영향 없음)
- 디스패처의 `requested_by_member_id is None` 예외 제거 → 단위 `test_dispatcher.py::test_매장이_직접_누른_재발송은_설정이_꺼진_종류여도_보낸다`
- 재발송이 `pet_id=None`·`variables` 를 `starts_at` 만 복사 → 단위 `test_resend_notification_interactor.py::test_끝난_줄이면_같은_재료로_지금_보낼_새_줄을_만들고_깨운다[failed·sent·fallback_sent·canceled]`
- 재발송의 `self._wake()` 제거 → 단위 `::test_끝난_줄이면_…` 넷(journal 끝의 `("wake",)`)
- 재발송이 `requested_by_member_id` 를 적지 않음 → 단위 `::test_끝난_줄이면_…` 넷; 통합 `::test_영구_실패_줄은_share_text_가_있고_직원이_다시_보내면_…`
- 재발송 라우터의 `require_permission("reservation:write")` → `get_shop_context`(import 포함) → 단위 `test_resend_notification_router.py::test_예약_권한이_없는_멤버는_403_이다`. 첫 시도는 import 를 안 바꿔 수집 오류(NameError)로 잡혔고, import 까지 바꿔 다시 돌린 결과가 이것이다
- `message_views` 의 `contact is not None` 검사 제거(익명화도 문안을 만듦) → 단위 `test_list_visit_notifications_interactor.py::test_익명화된_고객의_실패_줄은_share_text_가_없다`
- `scheduled_at` 을 매장 시간대로 바꾸지 않음 → 단위 `test_list_visit_notifications_router.py::test_직원도_목록을_보고_시각은_매장_시간대이며_…`, `test_get_notification_message_router.py::test_직원도_줄_하나를_읽는다`
- `main.py` 의 `get_notification_shop_profile` override 제거 → 단위 `tests/test_hub_port_binding.py::test_API_프로세스에는_빈_자리도_빠진_가드도_없다`, `::test_notification_의_매장_공개_정보와_고객_연락처_자리는_tenancy_customer_의_구현으로_채운다`
- `MessageKind` 경로 변수의 패턴 제거 → 단위 `test_resend_notification_router.py::test_없는_종류는_422_다[CONFIRM·sms·"confirm "·confirm%0A·0]`; 통합 `::test_없는_종류는_422_이고_줄이_없는_종류는_404_다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 방문별 발송 내역·다시 보내기·상태 조회 — 실패 줄에는 공유용 문안

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: 알림톡 흐름 스크립트(`check_notification_flow.sh`)와 운영자 재등록 스크립트(`reregister_templates.py`)

**Files:**
- Create: `backend/scripts/check_notification_flow.sh`
- Create: `backend/scripts/reregister_templates.py`
- Create: `backend/tests/test_reregister_templates.py`

**Interfaces:**
- Consumes: 작업 8·9 의 경로 열하나와 오류 코드; 작업 6 의 가짜 게이트웨이 규칙(토큰 `000000`, 번호 끝 `0000`); 작업 7 의 `refresh_templates` 와 같은 저장소·게이트웨이 호출; 기존 `check_report_flow.sh`·`check_visit_flow.sh` 의 모양(`BASE`, `expect`, 운영자 지정)과 `scripts/purge_stale_media.py` 의 모양(자체 엔진·세션).
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```
backend/scripts/check_notification_flow.sh
  사용: cd infra && docker compose up -d && bash ../backend/scripts/check_notification_flow.sh
  환경 변수: BASE (기본 http://127.0.0.1:8080)
  필요한 것: 호스트의 bash·curl·python3, infra/ 에서 실행(운영자 지정과 템플릿 상태 조회를 docker compose run 으로 한다)
  출력: "통과  <단계> <이름>" 53줄 + "전체 흐름 확인 완료". 실패하면 그 줄에서 exit 1 (expect 는 인자가 셋이 아니어도 exit 1)
  도우미: wait_status <message_id> <상태> (1초 간격 최대 15초), lines/line/line_id <visit_id> [<kind>], put_settings <next_visit> <sms_fallback>, approve_templates

backend/scripts/reregister_templates.py
  사용: cd infra && docker compose run --rm backend python scripts/reregister_templates.py [--shop <id>] [--refresh]
  출력: "매장 <id> <kind> <결과>" 줄들 + "재등록 N건." / "상태 조회 N건."  (결과: registered · approved · rejected · pending · failed(<코드>))
```

```python
# scripts.reregister_templates
Commit = Callable[[], Awaitable[None]]
Result = tuple[int, str, str]                       # (shop_id, kind, 결과)
async def reregister(queue: NotificationQueueRepository, settings: SettingsRepository, templates: TemplateRepository,
                     gateway: MessageGatewayPort, commit: Commit, now: datetime, shop_id: int | None = None) -> list[Result]
    # 연동된 채널마다(또는 shop_id 하나) DEFAULT_KINDS(+ 설정이 켜진 매장의 NEXT_VISIT) 가운데
    # 템플릿이 없거나 text_version != TEXT_VERSION 이거나 rejected 인 종류를 register_template → upsert(pending) → commit
    # GatewayError 는 그 종류만 "failed(<code>)" 로 적고 계속
async def refresh_pending(queue, templates, gateway, commit, now, shop_id=None) -> list[Result]
    # list_pending_templates 마다 template_state → approved/rejected 면 set_status + commit. 등록은 하지 않는다
async def run(*, queue, settings, templates, gateway, commit, now, shop_id: int | None, refresh: bool) -> list[Result]
async def _run(shop_id, refresh) -> list[Result]  # 자체 엔진(hide_parameters=True)·세션, get_message_gateway(), commit=session.commit
def main() -> None                                 # argparse --shop int, --refresh flag
```

문서 아홉(브리프의 "여덟" + customer 한 줄)과 결정 기록 009 의 절:

```
# 009 — 알림톡 자동 발송(⑥)에서 내린 결정
## 사용자와 정한 것 (2026-10-14)              ← 설계 2절 표 그대로 + 2.1 비용 한 문단
## ⑥-1 백엔드에서 정한 것                     ← 범위와 수(라우트 69→80, 0011, 단위 1294→1854, 통합 405→478, 계약 6)
### 이 계획에서 새로 정한 것                   ← 지정된 목록 전부(변경 안내 매번, pet_id, 취소 이유 셋, 지난 방문 간격은 이벤트·완료일은 전이 시각,
                                                  다른 매장 방문은 빈 목록, 수동 재발송은 설정 무관, 원 시도 1+재시도 3, 상태 조회 간격) + T1~T9 6절 전부
### 설계·브리프와 다르게 간 것                 ← 설계 7.2/5.2/4.4/5.3/6.1/9.5 와 다르게 한 것, 브리프와 다르게 한 것
### 알려진 동작 — 막지 않기로 했다
### 막지 못하고 감수하는 것                    ← 설계 9.8 + 9.3 의 at-least-once, variables 의 주소
### 남는 것 — 알고 미룬다                      ← T1~T9 7절 전부(AsyncClient 미닫힘, CI APP_ENV=dev(확인함), _event 루프 묶임, DB 오류 뒤 세션,
                                                  link_channel 뒤 쓰기 실패 틈, 솔라피 실계정 검증 항목 표 …) + 설계 11.3 + 10절 + 008 에서 넘어온 것
### ⑥-2 앱이 기댈 API 계약                    ← 경로 열하나 표, 요청 본문·칸 형식, overview·MessageItem 칸, share_text 모양, 오류 코드 표,
                                                  폴링 규칙, 가짜 게이트웨이 규칙, 작업 11 이 더할 것 한 줄
### 흐름 확인 (2026-10-23)                     ← 대역 서버 11단계·53줄, 판별력 확인, 게이트웨이는 실행 때, 라우트 69→80
```

문서마다 더한 것:

| 파일 | 더한 것 |
|---|---|
| `backend/apps/notification/_docs/CLAUDE.md` | 소유 데이터 네 표 + Redis. 글머리 16줄 — 이벤트로만 줄이 생김(같은 트랜잭션, 잠금 순서 끝), 공통 조건과 "변경 안내는 매번", 대기 줄 하나·`pet_id`, 디스패처 순서(집고 → 커밋 → 검사 → 보내기 → 접수 → 상태 조회), `system_context` 하나, `NotificationQueueRepository` 만 ctx 없음, 검사 순서와 취소 이유 14개, 야간·재계산, 재시도·회수·조회 간격, 문자 대체 조건, 템플릿(코드 문안·판·매장마다·재등록 스크립트), 변수·주소·번호를 로그와 응답에 안 싣는다, 재발송 규칙, 빈 목록, 횟수 제한과 Redis 장애 통과, 업체 먼저·저장 뒤, 게이트웨이 선택과 가짜 규칙, 스텁·테넌트 격리 |
| `backend/apps/hub/_docs/CLAUDE.md` | 포트 표에 `CustomerDirectoryPort.contact`(notification 만)·`DomainEventPort`(구현 core/observer, 발행 visit, 구독 notification) 두 줄, `ShopProfilePort` 사용처에 notification. 글머리 셋 — 디스패처의 `public_profile`, 이벤트 DTO 다섯과 "구독자가 던지면 발행한 요청이 실패한다"·`url` 의 토큰, notification 의 요청 안/밖 허브 포트 자리 |
| `backend/apps/visit/_docs/CLAUDE.md` | `VisitHistoryRepository` 줄에 `latest_completed_start_excluding`. 글머리 하나 + 발행 규칙 표(인터랙터 다섯 × 발행 × 위치, T2 보고서) |
| `backend/apps/customer/_docs/CLAUDE.md` | 허브 포트 문장에 `contact` 한 줄(살아 있는 이 매장 고객만, 익명화·다른 매장은 None, 저장하지 않는다) |
| `_docs/architecture.md` | GoF 표의 `core/observer/`·`<app>/adapter/inbound/observer/` 를 실제 경로(notification)와 내용으로, `notification/adapter/outbound/strategy/` 를 실제 내용으로 — "(예정)" 둘을 뺐다. "도메인 이벤트 도입 계획" 절을 "도메인 이벤트"(같은 세션 동기 버스, 큐가 아웃박스 역할, 자리·꽂기·구독 위치, 구독자는 외부를 안 부름, `system_context`·전 매장 포트)로 고쳤다 |
| `_docs/harness.md` | 검증 표에 알림톡 흐름·`reregister_templates.py`·알림 표 스키마 대조 세 줄. 글머리 — 테넌트 격리 줄에 notification 예, 요청 밖 `ShopContext` 는 `system_context` 하나, 디스패처는 `run_once` 로(상한·게이트웨이 바꾸기·`_event` 픽스처), 통합 두 세션 동시 실행 금지(대역 서버 포함), 실제 업체는 안 부른다 |
| `CLAUDE.md`(루트) | "꼭 지킬 것"에 — `ShopContext` 문장을 둘(`public_context`·`system_context`)로 넓힘, 잠금 순서에 "→ 알림 행"과 디스패처의 커밋 뒤 호출, 업체 키·번호·주소·`variables` 로그 금지 한 줄. 명령어 절에 흐름 스크립트와 재등록 스크립트 |
| `README.md` | "처음 띄우기"에 흐름 스크립트 한 줄과 `SOLAPI_API_KEY`·`SOLAPI_API_SECRET`(dev 는 비움 → 가짜, 운영 필수, 하나만 있으면 기동 안 함)·`SOLAPI_BALANCE_WARN_KRW`·`NOTIFICATION_DAILY_CAP`·과금 한 문단 |

기존 글을 고쳐 쓴 것은 사실과 어긋나게 된 문장뿐이다(루트 `CLAUDE.md` 의 `ShopContext`·잠금 순서 두 문장, 아키텍처의 GoF 두 줄과 이벤트 절, visit 의 포트 여섯 문장 한 군데, customer 의 허브 포트 문장, hub 의 `ShopProfilePort` 줄).

게이트웨이를 거쳐 실제 두 프로세스·DB·Redis 로 연동부터 발송·실패·재발송·알림장·해제까지 11단계를 확인한다(설계 11.1). 디스패처는 서버 안에서 돌므로 스크립트는 `wait_status` 로 최대 15초 기다린다. 템플릿 승인은 디스패처의 10분 주기를 기다릴 수 없어 `reregister_templates.py --refresh --shop` 으로 바로 당긴다. 스크립트는 번호·알림장 주소·업체 ID 를 찍지 않는다.

**참조 구현에서는 대역 서버(테스트 DB·Redis db 14)로 11단계(확인 53줄)가 통과했고 판별력(5단계 기대 뒤집기 → 그 줄에서 멈춤)도 확인했다. 게이트웨이 경유는 이 작업에서 처음 돌린다.** 돌리기 전에: 개발 DB 에 0011 이 올라가 있어야 하고(작업 4), 개발 스택이 이 브랜치의 코드로 떠 있어야 한다(`docker compose up -d --force-recreate backend auth`). 돌리면 개발 DB 에 확인용 매장·고객·방문·알림 줄이 남는다(기존 흐름 스크립트와 같다). 예약은 모레·글피라 18:00 뒤에 돌려도 리마인드가 생긴다; 자정 직전은 피한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_reregister_templates.py`:

```python
"""템플릿 재등록 스크립트 — 판이 다르거나 반려된 종류만 새 판으로, --refresh 는 pending 의 상태만."""
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.domain.value_objects.channel_status import LINKED, UNLINKED
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.template_status import APPROVED, PENDING, REJECTED
from notification.tests.helpers.builders import channel, kst, settings, template
from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates, Journal, SpyGateway
from scripts.reregister_templates import run

NOW = kst(10, 20, 9)


class _World:
    def __init__(self, **gateway_kwargs) -> None:
        self.journal = Journal()
        self.channels = FakeChannels(self.journal)
        self.settings = FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, templates=self.templates, channels=self.channels)
        self.gateway = SpyGateway(self.journal, **gateway_kwargs)

    def shop(self, shop_id: int, *, linked=True, next_visit=False, templates=()) -> None:
        self.channels.rows[shop_id] = channel(shop_id=shop_id, provider_channel_id=f"pf-{shop_id}",
                                              status=LINKED if linked else UNLINKED)
        self.settings.rows[shop_id] = settings(next_visit_enabled=next_visit)
        for t in templates:
            self.templates.rows[(shop_id, t.kind)] = t

    async def commit(self) -> None:
        self.journal.append(("commit",))

    async def run(self, *, shop_id=None, refresh=False):
        return await run(queue=self.messages, settings=self.settings, templates=self.templates, gateway=self.gateway,
                         commit=self.commit, now=NOW, shop_id=shop_id, refresh=refresh)

    def rows(self, shop_id: int) -> dict[str, tuple[int, str]]:
        return {t.kind: (t.text_version, t.status) for (s, _), t in self.templates.rows.items() if s == shop_id}


def _mixed_world() -> _World:
    world = _World()
    world.shop(1, templates=[
        template(id=1, kind=CONFIRM),                                                   # 판 같고 승인 — 그대로
        template(id=2, kind=REMINDER, text_version=0),                                  # 옛 판 — 새로
        template(id=3, kind=REPORT, status=REJECTED, rejected_reason="변수가 많아요"),   # 반려 — 새로
        template(id=4, kind=CHANGE, status=PENDING, decided_at=None),                   # 심사 중 — 그대로
    ])                                                                                   # cancel 없음 — 새로
    world.shop(2, next_visit=True, templates=[template(id=10 + i, shop_id=2, kind=k) for i, k in enumerate(
        (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL))])                                  # next_visit 만 없음
    world.shop(3, linked=False, templates=[template(id=20, shop_id=3, kind=CONFIRM, status=REJECTED)])
    return world


async def test_판이_다르거나_반려됐거나_없는_종류만_새_판으로_등록하고_next_visit_은_켠_매장만():
    world = _mixed_world()

    results = await world.run()

    assert results == [(1, REMINDER, "registered"), (1, REPORT, "registered"), (1, CANCEL, "registered"),
                       (2, NEXT_VISIT, "registered")]
    assert world.rows(1) == {CONFIRM: (1, APPROVED), REMINDER: (1, PENDING), REPORT: (1, PENDING),
                             CHANGE: (1, PENDING), CANCEL: (1, PENDING)}
    assert world.rows(2)[NEXT_VISIT] == (1, PENDING)
    assert world.rows(3) == {CONFIRM: (1, REJECTED)}      # 해제한 매장은 건드리지 않는다
    assert world.templates.rows[(1, REPORT)].rejected_reason is None


async def test_종류마다_업체를_먼저_부르고_저장한_뒤_커밋한다():
    world = _mixed_world()

    await world.run(shop_id=1)

    assert [e for e in world.journal if e[0] != "ensure_settings"] == [
        ("register_template", "pf-1", REMINDER), ("upsert_template", 1, REMINDER), ("commit",),
        ("register_template", "pf-1", REPORT), ("upsert_template", 1, REPORT), ("commit",),
        ("register_template", "pf-1", CANCEL), ("upsert_template", 1, CANCEL), ("commit",),
    ]


async def test_shop_을_주면_그_매장만_본다():
    world = _mixed_world()

    assert await world.run(shop_id=2) == [(2, NEXT_VISIT, "registered")]
    assert world.rows(1)[REMINDER] == (0, APPROVED)


async def test_업체_오류는_그_종류만_건너뛰고_저장하지_않는다():
    world = _mixed_world()
    world.gateway.register_error = GatewayTransientError("3040")

    results = await world.run(shop_id=1)

    assert results == [(1, REMINDER, "failed(3040)"), (1, REPORT, "failed(3040)"), (1, CANCEL, "failed(3040)")]
    assert world.rows(1)[REMINDER] == (0, APPROVED)
    assert not [e for e in world.journal if e[0] in ("upsert_template", "commit")]


async def test_refresh_는_등록하지_않고_pending_의_업체_상태만_적는다():
    world = _World(reject_next_visit=True)
    world.shop(1, next_visit=True, templates=[
        template(id=1, kind=CONFIRM, status=PENDING, decided_at=None, provider_template_id="tpl-pf-1-confirm-v1"),
        template(id=2, kind=NEXT_VISIT, status=PENDING, decided_at=None,
                 provider_template_id="tpl-pf-1-next_visit-v1"),
        template(id=3, kind=REMINDER, text_version=0),                   # 옛 판 — refresh 는 손대지 않는다
        template(id=4, kind=REPORT, status=REJECTED, rejected_reason="반려"),
    ])
    world.shop(2, templates=[template(id=5, shop_id=2, kind=CONFIRM, status=PENDING, decided_at=None)])

    results = await world.run(shop_id=1, refresh=True)

    assert results == [(1, CONFIRM, APPROVED), (1, NEXT_VISIT, REJECTED)]
    assert world.rows(1) == {CONFIRM: (1, APPROVED), NEXT_VISIT: (1, REJECTED), REMINDER: (0, APPROVED),
                             REPORT: (1, REJECTED)}
    assert world.templates.rows[(1, NEXT_VISIT)].rejected_reason == "가짜 반려"
    assert world.templates.rows[(1, CONFIRM)].decided_at == NOW
    assert world.rows(2)[CONFIRM] == (1, PENDING)
    assert not [e for e in world.journal if e[0] in ("register_template", "upsert_template")]
    assert world.journal.count(("commit",)) == 2
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest tests/test_reregister_templates.py -q -p no:cacheprovider`
Expected: 수집 오류 `ModuleNotFoundError: No module named 'scripts.reregister_templates'`

- [ ] **Step 3: 구현한다**

`backend/scripts/check_notification_flow.sh`:

```bash
#!/usr/bin/env bash
# 개발 환경에서 알림톡 채널 연동 → 템플릿 승인 → 발신번호 인증·문자 대체 → 예약 접수·리마인드 → 일정 변경 → 실패와 다시 보내기
# → 취소 → 완료와 다음 예약 제안 → 알림장 → 연동 해제까지 게이트웨이를 거쳐 확인한다.
# dev 의 게이트웨이는 가짜(FakeGateway)다 — 토큰·인증번호는 000000, 번호 끝 0000 은 영구 실패(문자 대체가 켜져 있으면 문자로 간다).
# 디스패처는 서버 안에서 돈다 — 줄의 상태는 wait_status 로 몇 초 기다려 본다. 템플릿 승인은 10분 주기라 운영자 스크립트
# (reregister_templates.py --refresh)로 바로 당긴다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_notification_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정과 템플릿 상태 조회를 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문·알림 줄이 남는다.
# 번호·알림장 주소·업체 ID 는 화면에 찍지 않는다 — 단계 이름과 상태만 보인다.
# 요청 본문은 변수·함수로 먼저 만든다 — 맥의 bash 3.2 는 "$( … \" … )" 안의 따옴표 이스케이프를 잘못 가르기도 한다(expect 가 인자 수로 잡는다).
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
SEED="$(printf '%04d' $((STAMP % 10000)))"
PHONE="010${SEED}1234"                                          # 실행마다 다른 번호. 끝이 1234 라 가짜 업체가 성공으로 답한다
PHONE_B="010$(printf '%04d' $(((STAMP + 1) % 10000)))1234"      # 두 번째 보호자
PHONE_BAD="010${SEED}0000"                                      # 끝 0000 — 가짜 업체가 영구 실패로 답한다
PHONE_BAD_B="010$(printf '%04d' $(((STAMP + 1) % 10000)))0000"
ADMIN_PHONE="010$(printf '%08d' $((STAMP % 100000000)))"        # 채널 관리자 번호(업체에만 넘기고 저장하지 않는다)
SENDER="02$(printf '%08d' $((STAMP % 100000000)))"              # 발신번호(유선)
TOKEN_REQ="{\"search_id\":\"nflow-$STAMP\",\"admin_phone\":\"$ADMIN_PHONE\",\"category_code\":\"003001\"}"
LINK_REQ="${TOKEN_REQ%\}},\"token\":\"000000\"}"
WRONG_LINK_REQ="${TOKEN_REQ%\}},\"token\":\"123456\"}"
VERIFY_REQ="{\"phone\":\"$SENDER\"}"
RIGHT_CODE_REQ="{\"phone\":\"$SENDER\",\"code\":\"000000\"}"
WRONG_CODE_REQ="{\"phone\":\"$SENDER\",\"code\":\"111111\"}"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
expect() {
  if [ $# -ne 3 ]; then echo "실패  $1 (인자 $# 개 — 따옴표가 깨졌다)"; exit 1; fi
  if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi
}
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
pet() { echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}"; }
# family <보호자 이름> <번호> <아이 이름> — 고객과 반려동물을 만들고 "customer_id pet_id" 를 낸다.
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":$(pet "$3")}"
  call POST "$S/customers" "$staff_token" "$body" | calc "f\"{d['customer']['customer_id']} {d['pets'][0]['pet_id']}\""
}
book() { call POST "$S/visits" "$staff_token" "{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$3\"}" | field "['visits'][0]['visit_id']"; }
act() { call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$1],\"action\":\"$2\"${3:+,\"cancel_reason\":\"$3\"}}"; }
# notes <방문> — 그 방문의 알림 줄 목록 응답. lines <방문> — 최신순 (종류, 상태) 목록. latest <종류> — 목록 응답에서 그 종류의 가장 최근 줄.
notes() { call GET "$S/visits/$1/notifications" "$staff_token"; }
lines() { notes "$1" | calc "[(i['kind'], i['status']) for i in d['items']]"; }
latest() { python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(next(i for i in d['items'] if i['kind']==sys.argv[1]), ensure_ascii=False))" "$1"; }
line() { notes "$1" | latest "$2"; }
line_id() { line "$1" "$2" | field "['message_id']"; }
# wait_status <message_id> <상태> — 1초 간격으로 최대 15초 기다리고 마지막 상태를 낸다. 디스패처가 서버 안에서 돈다.
wait_status() {
  local s=""; for _ in $(seq 15); do
    s=$(call GET "$S/notifications/$1" "$staff_token" | field "['status']"); [ "$s" = "$2" ] && break; sleep 1
  done; echo "$s"
}
overview() { call GET "$S/notification" "$owner_token"; }
# settings_body <next_visit_enabled> <sms_fallback_enabled> — 설정 전체 교체 본문(아홉 칸 모두).
settings_body() { echo "{\"confirm_enabled\":true,\"reminder_enabled\":true,\"report_enabled\":true,\"change_enabled\":true,\"next_visit_enabled\":$1,\"reminder_time\":\"18:00\",\"next_visit_after_weeks\":null,\"next_visit_cooldown_days\":30,\"sms_fallback_enabled\":$2}"; }
put_settings() { call PUT "$S/notification/settings" "$owner_token" "$(settings_body "$1" "$2")"; }
approve_templates() { docker compose run --rm backend python scripts/reregister_templates.py --refresh --shop "$shop_id" >/dev/null; }
send_report() { call PUT "$S/visits/$1/report" "$staff_token" '{"hidden_media_ids":[]}' >/dev/null; }

# 1. 매장·사장·직원·고객·반려동물
op=$(login "nflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"알림톡흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "nflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "nflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
read -r customer_id kong < <(family 김민지 "$PHONE" 콩이)
echo "통과  1 매장 $shop_id 에 사장·직원·고객 $customer_id 과 반려동물 $kong 이 있다"
expect "1 연동 전 한눈에 보기는 채널 none, 설정 없음, 템플릿 없음" "$(overview | calc "(d['channel']['status'], d['settings'], d['templates'])")" "('none', None, [])"

# 2. 채널 연동 — 토큰 신청 → 틀린 토큰 → 맞는 토큰
expect "2 직원은 토큰을 신청하지 못한다" "$(status POST "$S/notification/channel/token" "$staff_token" "$TOKEN_REQ")" "403"
expect "2 사장의 토큰 신청은 202" "$(call POST "$S/notification/channel/token" "$owner_token" "$TOKEN_REQ" | field "['status']")" "token_requested"
expect "2 틀린 토큰은 400" "$(call POST "$S/notification/channel" "$owner_token" "$WRONG_LINK_REQ" | field "['code']")" "NOTIFICATION_TOKEN_INVALID"
linked=$(call POST "$S/notification/channel" "$owner_token" "$LINK_REQ")
expect "2 맞는 토큰이면 linked 이고 설정은 기본값" "$(echo "$linked" | calc "(d['channel']['status'], d['settings']['reminder_time'], d['settings']['next_visit_enabled'])")" "('linked', '18:00', False)"
expect "2 기본 5종 템플릿이 심사 중" "$(echo "$linked" | calc "[(t['kind'], t['status']) for t in d['templates']]")" \
  "[('confirm', 'pending'), ('reminder', 'pending'), ('report', 'pending'), ('change', 'pending'), ('cancel', 'pending')]"
expect "2 응답에 업체 ID 가 없다" "$(echo "$linked" | calc "'pf-' in json.dumps(d) or 'tpl-' in json.dumps(d)")" "False"

# 3. 템플릿 승인 — 디스패처의 10분 주기 대신 운영자 스크립트로 당긴다
approve_templates
expect "3 다섯 종류가 승인됐다" "$(overview | calc "[t['status'] for t in d['templates']]")" "['approved', 'approved', 'approved', 'approved', 'approved']"

# 4. 문자 대체 — 발신번호 인증 뒤에만
expect "4 인증 없이 문자 대체를 켜면 409" "$(put_settings false true | field "['code']")" "NOTIFICATION_SENDER_NOT_VERIFIED"
expect "4 발신번호 인증 시작은 202" "$(call POST "$S/notification/sender/verification" "$owner_token" "$VERIFY_REQ" | field "['status']")" "verification_requested"
expect "4 틀린 인증번호는 400" "$(call POST "$S/notification/sender" "$owner_token" "$WRONG_CODE_REQ" | field "['code']")" "NOTIFICATION_TOKEN_INVALID"
verified=$(call POST "$S/notification/sender" "$owner_token" "$RIGHT_CODE_REQ")
expect "4 맞는 인증번호면 발신번호가 인증된다" "$(echo "$verified" | calc "(d['channel']['sender_verified'], d['channel']['sms_fallback_enabled'])")" "(True, False)"
expect "4 직원은 설정을 바꾸지 못한다" "$(status PUT "$S/notification/settings" "$staff_token" "$(settings_body false true)")" "403"
expect "4 인증 뒤에는 문자 대체를 켤 수 있다" "$(put_settings false true | field "['channel']['sms_fallback_enabled']")" "True"

# 5. 예약 접수 — 접수 안내는 바로, 리마인드는 전날 18:00
visit=$(book "$customer_id" "$kong" "$(at 2 14)")
expect "5 예약하면 접수 안내와 리마인드 줄이 생긴다" "$(lines "$visit")" "[('reminder', 'scheduled'), ('confirm', 'scheduled')]"
expect "5 접수 안내가 보내진다" "$(wait_status "$(line_id "$visit" confirm)" sent)" "sent"
expect "5 알림톡으로 갔고 보낸 시각이 있다" "$(line "$visit" confirm | calc "(d['channel_used'], d['sent_at'] is not None, d['share_text'])")" "('alimtalk', True, None)"
expect "5 리마인드는 전날 18:00 예정" "$(line "$visit" reminder | calc "(d['status'], d['scheduled_at'])")" "('scheduled', '$(at 1 18)')"
items=$(notes "$visit")
expect "5 응답에 번호·변수·업체 메시지 ID 가 없다" "$(echo "$items" | calc "any(s in json.dumps(d) for s in ('$PHONE', 'variables', 'fake-', 'starts_at', 'customer_id'))")" "False"

# 6. 일정 변경 — 옛 리마인드는 취소, 새 리마인드와 변경 안내
call POST "$S/visits/reschedule" "$staff_token" "{\"visit_ids\":[$visit],\"starts_at\":\"$(at 3 15)\"}" >/dev/null
expect "6 변경 안내가 보내진다" "$(wait_status "$(line_id "$visit" change)" sent)" "sent"
expect "6 옛 리마인드는 취소되고 새 리마인드가 생긴다" "$(lines "$visit")" "[('change', 'sent'), ('reminder', 'scheduled'), ('reminder', 'canceled'), ('confirm', 'sent')]"
items=$(notes "$visit")
expect "6 취소 이유는 rescheduled, 새 리마인드는 바뀐 전날 18:00" "$(echo "$items" | calc "([i['canceled_reason'] for i in d['items'] if i['kind'] == 'reminder'], d['items'][1]['scheduled_at'])")" "([None, 'rescheduled'], '$(at 2 18)')"

# 7. 실패 — 끝 0000 번호는 영구 실패. 문자 대체가 켜져 있으면 문자로 가고, 끄면 실패 줄에 공유용 문안이 생긴다
read -r bad_customer bad_pet < <(family 이서연 "$PHONE_BAD" 두부)
bad_visit=$(book "$bad_customer" "$bad_pet" "$(at 2 11)")
expect "7 문자 대체가 켜져 있으면 문자로 간다" "$(wait_status "$(line_id "$bad_visit" confirm)" fallback_sent)" "fallback_sent"
expect "7 실제로 나간 길은 sms" "$(line "$bad_visit" confirm | calc "(d['channel_used'], d['share_text'])")" "('sms', None)"
put_settings false false >/dev/null
read -r bad_customer_b bad_pet_b < <(family 최지우 "$PHONE_BAD_B" 보리)
bad_visit_b=$(book "$bad_customer_b" "$bad_pet_b" "$(at 2 12)")
expect "7 문자 대체를 끄면 영구 실패" "$(wait_status "$(line_id "$bad_visit_b" confirm)" failed)" "failed"
failed_line=$(line "$bad_visit_b" confirm)
expect "7 실패 줄에는 공유용 문안이 있고 번호·이름은 없다" "$(echo "$failed_line" | calc "(d['error_kind'], d['share_text'] is not None, '$PHONE_BAD_B' in d['share_text'], '최지우' in d['share_text'])")" "('permanent', True, False, False)"
expect "7 공유용 문안은 매장 이름과 일시가 든 접수 문안이다" "$(echo "$failed_line" | calc "d['share_text'].startswith('[알림톡흐름-$STAMP] ') and '예약이 접수되었어요.' in d['share_text']")" "True"
resent=$(call POST "$S/visits/$bad_visit_b/notifications/confirm/resend" "$staff_token")
resent_id=$(echo "$resent" | calc "d.get('message_id', d.get('code'))")
expect "7 직원이 다시 보내면 201 과 새 줄" "$(echo "$resent" | calc "'message_id' in d")" "True"
expect "7 대기 중에 또 누르면 409" "$(call POST "$S/visits/$bad_visit_b/notifications/confirm/resend" "$staff_token" | field "['code']")" "NOTIFICATION_ALREADY_PENDING"
expect "7 다시 보낸 줄이 맨 앞이고 누른 멤버가 남는다" "$(line "$bad_visit_b" confirm | calc "(d['message_id'] == $resent_id, d['requested_by_member_id'] is not None)")" "(True, True)"
expect "7 다시 보낸 줄도 영구 실패로 끝난다" "$(wait_status "$resent_id" failed)" "failed"

# 8. 취소 — 매장 사정이면 취소 안내, 보호자 요청이면 대기 줄만 취소
shop_cancel=$(book "$customer_id" "$kong" "$(at 4 11)")
expect "8 접수 안내가 먼저 나간다" "$(wait_status "$(line_id "$shop_cancel" confirm)" sent)" "sent"
act "$shop_cancel" cancel shop_reason >/dev/null
expect "8 매장 사정 취소는 취소 안내가 보내진다" "$(wait_status "$(line_id "$shop_cancel" cancel)" sent)" "sent"
expect "8 리마인드는 visit_canceled 로 취소된다" "$(line "$shop_cancel" reminder | calc "(d['status'], d['canceled_reason'])")" "('canceled', 'visit_canceled')"
customer_cancel=$(book "$customer_id" "$kong" "$(at 5 11)")
expect "8 접수 안내가 먼저 나간다" "$(wait_status "$(line_id "$customer_cancel" confirm)" sent)" "sent"
act "$customer_cancel" cancel customer_request >/dev/null
expect "8 보호자 요청 취소는 취소 안내가 없다" "$(lines "$customer_cancel")" "[('reminder', 'canceled'), ('confirm', 'sent')]"

# 9. 완료 — 다음 예약 제안은 켠 뒤부터, 4주 뒤 18:00
done_visit=$(book "$customer_id" "$kong" "$(at 0 13)")
act "$done_visit" start >/dev/null; act "$done_visit" complete >/dev/null
expect "9 다음 예약 제안이 꺼져 있으면 줄이 없다" "$(notes "$done_visit" | calc "[i['kind'] for i in d['items']]")" "['confirm']"
expect "9 다음 예약 제안을 켜면 템플릿이 여섯" "$(put_settings true false | calc "[(t['kind'], t['status']) for t in d['templates']][-1]")" "('next_visit', 'pending')"
approve_templates
expect "9 여섯 종류가 승인됐다" "$(overview | calc "[t['status'] for t in d['templates']]")" "['approved', 'approved', 'approved', 'approved', 'approved', 'approved']"
read -r customer_b pet_b < <(family 박서준 "$PHONE_B" 몽이)
done_visit_b=$(book "$customer_b" "$pet_b" "$(at 0 15)")
act "$done_visit_b" start >/dev/null; act "$done_visit_b" complete >/dev/null
expect "9 완료하면 다음 예약 제안이 4주 뒤 18:00 에 예정된다" "$(line "$done_visit_b" next_visit | calc "(d['status'], d['scheduled_at'])")" "('scheduled', '$(at 28 18)')"

# 10. 알림장 — 보내면 알림장 줄, 같은 링크는 줄이 늘지 않고, 끊고 새로 보내면 새 줄
call PUT "$S/visits/$done_visit/record" "$staff_token" '{"care_note":"눈물 자국 관리","media":[]}' >/dev/null
expect "10 알림장을 보내면 200" "$(status PUT "$S/visits/$done_visit/report" "$staff_token" '{"hidden_media_ids":[]}')" "200"
expect "10 알림장 줄이 보내진다" "$(wait_status "$(line_id "$done_visit" report)" sent)" "sent"
expect "10 응답에 알림장 주소가 없다" "$(notes "$done_visit" | calc "'/r/' in json.dumps(d)")" "False"
send_report "$done_visit"
expect "10 같은 링크를 다시 공유하면 줄이 늘지 않는다" "$(lines "$done_visit")" "[('report', 'sent'), ('confirm', 'sent')]"
expect "10 끊기는 204" "$(status DELETE "$S/visits/$done_visit/report" "$staff_token")" "204"
send_report "$done_visit"
expect "10 새 링크로 보내면 새 알림장 줄" "$(wait_status "$(line_id "$done_visit" report)" sent)" "sent"
expect "10 알림장 줄이 둘" "$(lines "$done_visit")" "[('report', 'sent'), ('report', 'sent'), ('confirm', 'sent')]"

# 11. 연동 해제 — 대기 줄은 전부 취소, 다시 연동할 수 있다
expect "11 해제는 204" "$(status DELETE "$S/notification/channel" "$owner_token")" "204"
reminder_after=$(line "$visit" reminder | calc "(d['status'], d['canceled_reason'])")
next_after=$(line "$done_visit_b" next_visit | calc "(d['status'], d['canceled_reason'])")
expect "11 예정된 리마인드와 다음 예약 제안이 channel_unlinked 로 취소된다" "$reminder_after $next_after" "('canceled', 'channel_unlinked') ('canceled', 'channel_unlinked')"
expect "11 해제 뒤 설정 변경은 409" "$(put_settings false false | field "['code']")" "NOTIFICATION_CHANNEL_NOT_LINKED"
expect "11 다시 토큰을 신청할 수 있다" "$(status POST "$S/notification/channel/token" "$owner_token" "$TOKEN_REQ")" "202"
relinked=$(call POST "$S/notification/channel" "$owner_token" "$LINK_REQ")
expect "11 다시 연동하면 linked 이고 발신번호는 남아 있다" "$(echo "$relinked" | calc "(d['channel']['status'], d['channel']['sender_verified'], len(d['templates']))")" "('linked', True, 5)"

echo "전체 흐름 확인 완료"
```

`backend/scripts/reregister_templates.py`:

```python
"""반려됐거나 문안 판이 바뀐 템플릿을 연동된 매장마다 새 판으로 등록·검수 요청한다(설계 6.2·7.4). 여러 번 돌려도 결과가 같다.

기본: 연동된 모든 매장(또는 --shop 하나)에서 코드의 TEXT_VERSION 과 DB 의 text_version 이 다르거나 rejected 인 종류를
새 판으로 등록한다(없는 종류도 등록한다 — 디스패처의 10분 주기와 같은 일). next_visit 은 설정에서 켠 매장만.
--refresh: 등록 대신 pending 템플릿의 업체 상태만 조회해 적는다(디스패처의 10분 주기를 바로 당긴다 — 흐름 스크립트가 쓴다).
종류마다 업체를 먼저 부르고 그 뒤 저장·커밋한다 — 잠금을 쥔 채 업체를 부르지 않는다(N14).
출력은 매장 ID·종류·결과만이다. 업체 ID·오류 본문·번호는 찍지 않는다(N12).
사용: cd infra && docker compose run --rm backend python scripts/reregister_templates.py [--shop <id>] [--refresh]
"""
from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.system_context import system_context
from notification.dependencies.notification_wiring import (
    build_message_repository,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.templates import TEMPLATES, TEXT_VERSION
from notification.domain.value_objects.message_kind import DEFAULT_KINDS, NEXT_VISIT
from notification.domain.value_objects.template_status import APPROVED, REJECTED

Commit = Callable[[], Awaitable[None]]
Result = tuple[int, str, str]      # (매장 ID, 종류, 결과) — "registered" · "approved" · "rejected" · "pending" · "failed(<코드>)"


async def reregister(
    queue: NotificationQueueRepository, settings: SettingsRepository, templates: TemplateRepository,
    gateway: MessageGatewayPort, commit: Commit, now: datetime, shop_id: int | None = None,
) -> list[Result]:
    """새 판이 필요한 종류를 등록·검수 요청하고 pending 으로 적는다. 업체 오류는 그 종류만 건너뛴다."""
    results: list[Result] = []
    channels = [c for c in await queue.list_linked_channels() if shop_id is None or c.shop_id == shop_id]
    existing = await queue.list_templates_for_shops([c.shop_id for c in channels])
    for channel in channels:
        ctx = system_context(channel.shop_id)
        current = await settings.get(ctx)
        wanted = list(DEFAULT_KINDS)
        if current is not None and current.next_visit_enabled:
            wanted.append(NEXT_VISIT)
        have = {t.kind: t for t in existing[channel.shop_id]}
        for kind in wanted:
            template = have.get(kind)
            if template is not None and template.text_version == TEXT_VERSION and template.status != REJECTED:
                continue
            try:
                provider_id = await gateway.register_template(channel.provider_channel_id, TEMPLATES[kind], TEXT_VERSION)
            except GatewayError as exc:
                results.append((channel.shop_id, kind, f"failed({exc.code})"))
                continue
            await templates.upsert(ctx, kind, TEXT_VERSION, provider_id, now)
            await commit()
            results.append((channel.shop_id, kind, "registered"))
    return results


async def refresh_pending(
    queue: NotificationQueueRepository, templates: TemplateRepository, gateway: MessageGatewayPort, commit: Commit,
    now: datetime, shop_id: int | None = None,
) -> list[Result]:
    """pending 템플릿의 업체 상태를 물어 approved·rejected 면 적는다. 등록은 하지 않는다."""
    results: list[Result] = []
    for template in await queue.list_pending_templates():
        if shop_id is not None and template.shop_id != shop_id:
            continue
        try:
            state = await gateway.template_state(template.provider_template_id)
        except GatewayError as exc:
            results.append((template.shop_id, template.kind, f"failed({exc.code})"))
            continue
        if state.status in (APPROVED, REJECTED):
            await templates.set_status(system_context(template.shop_id), template.kind, state.status,
                                       state.rejected_reason, now)
            await commit()
        results.append((template.shop_id, template.kind, state.status))
    return results


async def run(
    *, queue: NotificationQueueRepository, settings: SettingsRepository, templates: TemplateRepository,
    gateway: MessageGatewayPort, commit: Commit, now: datetime, shop_id: int | None, refresh: bool,
) -> list[Result]:
    if refresh:
        return await refresh_pending(queue, templates, gateway, commit, now, shop_id)
    return await reregister(queue, settings, templates, gateway, commit, now, shop_id)


async def _run(shop_id: int | None, refresh: bool) -> list[Result]:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            messages = build_message_repository(session)
            return await run(
                queue=messages, settings=build_settings_repository(session), templates=build_template_repository(session),
                gateway=get_message_gateway(), commit=session.commit, now=datetime.now(timezone.utc),
                shop_id=shop_id, refresh=refresh,
            )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="알림톡 템플릿 재등록(기본) 또는 심사 상태 조회(--refresh)")
    parser.add_argument("--shop", type=int, default=None, help="이 매장만(기본: 연동된 모든 매장)")
    parser.add_argument("--refresh", action="store_true", help="등록 대신 pending 템플릿의 업체 상태만 조회해 적는다")
    args = parser.parse_args()
    results = asyncio.run(_run(args.shop, args.refresh))
    for shop_id, kind, result in results:
        print(f"매장 {shop_id} {kind} {result}")
    print(f"{'상태 조회' if args.refresh else '재등록'} {len(results)}건.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest tests/test_reregister_templates.py -q -p no:cacheprovider` → 5 passed

Run (`infra/`): `docker compose up -d --force-recreate backend auth` 뒤 `bash ../backend/scripts/check_notification_flow.sh` → `통과` 53줄 뒤 `전체 흐름 확인 완료`, 종료 코드 0

판별력(한 번): 스크립트 5단계 `expect "5 응답에 번호·변수·업체 메시지 ID 가 없다" … "False"` 의 기대를 `"True"` 로 바꿔 돌리면 `실패  5 응답에 번호·변수·업체 메시지 ID 가 없다 (기대 True, 실제 False)` 로 멈추고 그 뒤 줄이 나오지 않아야 한다(종료 코드 1). 편집으로 되돌리고 다시 돌려 전부 통과함을 본다.

Run (`infra/`): `docker compose run --rm --no-deps auth python scripts/print_routes.py` 를 받아 작업 1 전에 받아 둔 것과 `diff` → 늘어난 줄은 열하나뿐이다(작업 8 의 여덟 `/v1/shops/{shop_id}/notification…`, 작업 9 의 `GET …/visits/{visit_id}/notifications`·`POST …/visits/{visit_id}/notifications/{kind}/resend`·`GET …/notifications/{message_id}`). 없어지거나 바뀐 줄은 없다.

Run (`infra/`): 단위 전체 → 1854 passed(작업 9 뒤 1849 + 5), 통합 전체 → 478 passed, 구조 계약 6 kept

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `reregister_templates.run` 의 `if refresh: return await refresh_pending(…)` 분기 제거(늘 등록) → `tests/test_reregister_templates.py::test_refresh_는_등록하지_않고_pending_의_업체_상태만_적는다` (4 passed, 1 failed)
- 흐름 스크립트 5단계 "응답에 번호·변수·업체 메시지 ID 가 없다"의 기대 `False` → `True` → 대역 서버에서 실행: `실패  5 응답에 번호·변수·업체 메시지 ID 가 없다 (기대 True, 실제 False)` 로 멈추고 6단계 이후 없음, 종료 코드 1. **실행 권한 거부 없이 돌았다**

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "test(notification): 알림톡 흐름 스크립트 — 연동부터 발송·실패·재발송·알림장까지

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: 문서 — 스포크 규칙, 아키텍처 표(GoF 의 "예정" 을 실제로), 검증 장치, README, 결정 기록 009(⑥-2 앱이 기댈 API 계약)

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `_docs/architecture.md`
- Create: `_docs/decisions/009-notification.md`
- Modify: `_docs/harness.md`
- Modify: `backend/apps/customer/_docs/CLAUDE.md`
- Modify: `backend/apps/hub/_docs/CLAUDE.md`
- Modify: `backend/apps/notification/_docs/CLAUDE.md`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`

**Interfaces:**
- Consumes: 작업 1~10 의 결과 전부.
- Produces: `_docs/decisions/009-notification.md` — 사용자 결정, 이 계획에서 새로 정한 것, 설계와 다르게 간 것, 알려진 동작, 감수하는 것, 남는 것, **API 계약**(경로 열하나의 표·본문·응답 칸·오류 코드 표·폴링 규칙·가짜 게이트웨이 규칙). ⑥-2 앱 계획은 이 계약에 기댄다. 작업 13 이 가족 묶음·링크 끊기를 이 문서에 더한다.

문서는 기존 글에 더한다. 사실과 어긋나게 된 기존 문장만 고친다. 비밀값·번호·알림장 주소의 실제 값을 예시로 쓰지 않는다(번호 예시는 `010-0000-0000` 식). 결정 기록의 '흐름 확인' 절은 작업 10 에서 게이트웨이로 돌린 실제 결과로 고쳐 적는다 — 아래 글은 참조 구현(대역 서버) 때의 것이다. 실행 중에 계획과 다르게 한 것이 있으면 '설계·브리프와 다르게 간 것'에 더한다.

- [ ] **Step 1: 문서를 쓴다**

`CLAUDE.md`:

```diff
@@ -27,9 +27,10 @@
 - 로그인 없이 열리는 경로는 `backend/tests/route_inspection.py`의 허용 목록과 프로세스별 목록 테스트에 있는 것뿐이다. 공개 응답 스키마는 매장용과 따로 쓰고 칸을 하나하나 적는다.
 - 알림장 토큰은 헤더(`X-Report-Token`)로 받고 로그·문서·커밋에 남기지 않는다.
 - 웹(`web/`)은 토큰·서명 주소·비밀값을 로그에 찍지 않는다. 보호자의 브라우저는 백엔드를 직접 부르지 않는다 — 웹 서버가 부른다.
-- 로그인 없는 요청 경로에서 `ShopContext`를 가드 없이 만드는 곳은 `visit/app/services/public_context.py` 하나다. 권한이 비어 있고 읽기에만 쓴다.
+- 가드 없이 `ShopContext`를 만드는 곳은 둘뿐이다. 로그인 없는 요청 경로에서는 `visit/app/services/public_context.py` 하나, 요청 밖(디스패처·운영자 스크립트)에서는 `notification/app/services/system_context.py` 하나(권한 빔). 둘 다 권한이 비어 있고 포트 읽기(와 알림 표 쓰기)에만 쓴다.
 - 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있고 인증 프로세스(`auth_main.py`)만 읽는다. 이 모듈은 함수 안에서만 import한다. API 프로세스 경로에서 import하지 않는다.
-- 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. 고객·방문 쪽은 고객 행 → 방문 행(ID 오름차순)이다 — 방문을 쓰는 유스케이스는 허브 포트 `CustomerDirectoryPort.lock_family`로 고객 행부터 잠근다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다.
+- 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. 고객·방문 쪽은 고객 행 → 방문 행(ID 오름차순) → 알림 행이다 — 방문을 쓰는 유스케이스는 허브 포트 `CustomerDirectoryPort.lock_family`로 고객 행부터 잠그고, 알림 줄은 그 트랜잭션 안의 이벤트 구독자가 끝에 쓴다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다(디스패처는 줄을 집어 커밋한 뒤 업체를 부른다).
+- 발송 업체 API 키(`SOLAPI_*`)·전화번호·알림장 주소·`variables`·업체 응답 본문을 로그·오류 메시지·API 응답에 남기지 않는다. 로그는 message_id·매장·종류·결과만이다.
 - `load_dotenv`·`os.getenv`·`os.environ`은 `core/singleton/secret_manager.py`에서만 쓴다.
 - 비밀값을 로그·커밋·문서에 남기지 않는다. `.env*` 파일 내용을 그대로 출력하지 않는다.
 - 커밋과 푸시는 사용자가 요청할 때만 한다. CI(GitHub Actions, `.github/workflows/`)는 푸시마다 바뀐 영역의 테스트·import-linter·analyze·빌드를 돈다. 골든·e2e·흐름·라우트 표는 CI가 보지 않으니 로컬에서 확인한다.
@@ -45,6 +46,8 @@
     docker compose run --rm --no-deps backend lint-imports --config .importlinter
     docker compose run --rm --no-deps auth python scripts/print_routes.py      # 개인키가 필요해서 auth 서비스에서 돌린다
     docker compose run --rm backend python scripts/grant_operator.py <user_id>   # 플랫폼 운영자 지정 (user_id 는 GET /v1/me 의 id)
+    bash ../backend/scripts/check_notification_flow.sh                           # 알림톡 흐름 확인 (dev 는 가짜 게이트웨이, 실제 발송 없음)
+    docker compose run --rm backend python scripts/reregister_templates.py [--shop <id>] [--refresh]   # 알림톡 템플릿 재등록 / 심사 상태 조회
 
 앱은 전부 `app/`에서 실행한다.
```

`README.md`:

```diff
@@ -21,6 +21,7 @@
     bash ../backend/scripts/check_account_flow.sh                                   # 회원 탈퇴 흐름 확인
     bash ../backend/scripts/check_customer_flow.sh                                  # 고객·반려동물 흐름 확인
     bash ../backend/scripts/check_report_flow.sh                                    # 알림장 흐름 확인 (버킷 준비 뒤 — _docs/harness.md)
+    bash ../backend/scripts/check_notification_flow.sh                              # 알림톡 흐름 확인 (가짜 게이트웨이, 실제 발송 없음)
 
 `REPORT_LINK_KEY_B64`(알림장 링크의 서명 키, 32바이트 이상을 base64 로)는 필수다. 없으면 API 프로세스와 인증 프로세스가 둘 다 기동하지 않는다. `generate_dev_env.py`는 `.env`가 이미 있으면 아무것도 하지 않으므로, ⑤ 이전에 만든 개발 환경은 한 줄을 직접 더한다. 먼저 `.env`가 줄바꿈으로 끝나는지 본다(끝나지 않으면 앞 줄에 붙는다). 아래 명령은 값을 출력하지 않고, 이미 있으면 아무것도 하지 않는다. 키를 바꾸면 보낸 링크가 모두 닫힌다.
 
@@ -47,6 +48,8 @@
         env.write_text(text + 'REPORT_WEB_SECRET=' + secrets.token_urlsafe(32) + '\n')
     "
 
+`SOLAPI_API_KEY`·`SOLAPI_API_SECRET`(알림톡 발송 업체 솔라피의 API 키)은 개발 환경에서 비워 둔다 — 둘 다 비어 있고 `APP_ENV=dev`면 가짜 게이트웨이가 붙어 실제 발송 없이 흐름을 확인할 수 있다(토큰·인증번호 `000000`, 번호 끝 `0000`은 실패). 운영은 둘 다 필수이고, 하나만 있거나 비어 있으면 API 프로세스가 기동하지 않는다. 함께 쓰는 키 둘은 없어도 된다 — `SOLAPI_BALANCE_WARN_KRW`(잔액 경고 기준, 기본 30000원 — 디스패처가 하루 한 번 잔액을 보고 아래면 WARNING 로그)와 `NOTIFICATION_DAILY_CAP`(매장별 하루 발송 상한, 기본 300 — 넘으면 보내지 않고 1시간 뒤로 미룬다). 알림톡은 건당 과금(솔라피 13원, 문자 대체 18~45원)이라 실제 키는 운영에만 둔다.
+
 개발 환경에서는 제공자 `dev`로 이름만 넣어 로그인한다. 운영자는 `docker compose run --rm backend python scripts/grant_operator.py <user_id>`로 지정한다.
 
 백엔드가 떠 있으면 `app/tool/run_dev.sh`로 앱을 켠다(iOS 시뮬레이터 기준, `app/CLAUDE.md` 참고).
```

`_docs/architecture.md`:

```diff
@@ -61,17 +61,21 @@
 | `auth/adapter/outbound/strategy/` | Strategy | 제공자별 `SocialProviderPort` 구현 |
 | `auth/adapter/outbound/factory/` | Factory | 설정에 따라 제공자 구현을 만들어 담아 두고 이름으로 골라 준다 |
 | `visit/domain/state/` | State | 방문 상태 전이(예약됨·미용 중·완료·취소·노쇼) |
-| `core/observer/`, `<app>/adapter/inbound/observer/` (예정) | Observer | 도메인 이벤트 발행과 구독 |
+| `core/observer/`, `notification/adapter/inbound/observer/` | Observer | 도메인 이벤트 발행과 구독 — `core/observer/in_process_event_bus.py`가 허브 포트 `DomainEventPort`의 구현(같은 프로세스·같은 세션의 동기 버스, 구독자 목록은 `main.py`가 기동 때 채운다), notification 의 `visit_event_subscriber.py`가 구독자 |
 | `visit/domain/chain/` (예정) | Chain of Responsibility | 예약 체크리스트 규칙 |
 | `search/adapter/outbound/decorator/` (예정) | Decorator | LLM 포트를 감싼 개인정보 마스킹 |
 | `visit/app/template/` (예정) | Template Method | 말로 기록하기 절차의 뼈대 |
 | `search/app/facade/` (예정) | Facade | RAG 단일 입구 |
-| `notification/adapter/outbound/strategy/` (예정) | Strategy | 알림 발송 수단 |
+| `notification/adapter/outbound/strategy/` | Strategy | 발송 업체별 `MessageGatewayPort` 구현 — `solapi_gateway.py`(실제), `fake_gateway.py`(dev·흐름 확인). 키 유무와 `APP_ENV`로 하나를 고른다 |
 | `app/lib/core/proxy/` (예정) | Proxy | 토큰 자동 첨부·갱신 API 클라이언트 |
 | `app/lib/design/bridge/` (예정) | Bridge | 글래스 구현 교체 지점 |
 
 새 패턴 폴더를 만들면 이 표에 한 줄을 더한다.
 
-## 도메인 이벤트 도입 계획
+## 도메인 이벤트
 
-이벤트 발행 포트는 첫 구독자가 생길 때(미용 완료 → 통계·검색·알림) 허브에 도입한다. 처음에는 같은 프로세스 안의 단순한 구현으로 시작하고, 신뢰성이 필요해지면 아웃박스 방식으로 어댑터만 바꾼다. 그 전에는 포트를 만들지 않는다.
+첫 구독자(⑥ 알림톡)가 생기면서 허브에 `DomainEventPort`(`hub/app/ports/domain_event_port.py`)와 이벤트 DTO(`hub/app/dtos/visit_events.py`)를 두었다. 구현은 `core/observer/`의 **같은 프로세스·같은 세션의 동기 버스**다 — 발행한 인터랙터의 트랜잭션 안에서 구독자가 차례로 돌고, 구독자가 던지면 발행한 요청이 실패한다. 별도 이벤트 저장소는 없다. 구독자(notification)가 같은 트랜잭션에 쓰는 `notification_messages` 큐가 아웃박스 역할을 하고, 요청 밖의 디스패처가 그 큐를 집어 외부를 부른다. 메시지 브로커·다른 프로세스로 나갈 일이 생기면 버스 어댑터만 바꾼다.
+
+- 발행은 `dependencies/hub_ports.py`의 자리(`get_domain_events`)로 받고 `main.py`가 `get_event_bus`를 꽂는다. 구독은 `main.py`가 기동 때 `subscribe(handler)`로 등록한다 — 구독자는 `(AsyncSession, VisitEvent)`를 받는 어댑터(`<app>/adapter/inbound/observer/`)이고 `app` 층에 두지 않는다(프레임워크 격리).
+- 구독자는 외부(HTTP)를 부르지 않는다. 외부 호출은 요청 밖(디스패처)에서 잠금 없이 한다.
+- 요청 밖에서 `ShopContext`가 필요하면 `notification/app/services/system_context.py` 하나로 만든다(권한 빔). 전 매장 질의는 `ShopContext`를 받지 않는 별도 포트(`NotificationQueueRepository`)에 둔다.
```

`_docs/decisions/009-notification.md`:

````markdown
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
- 흐름 스크립트는 게이트웨이(Caddy) 경유로 돌려 보지 못했다 — 개발 스택은 원 저장소 코드라 새 경로가 없다. 병합하고 0011 을 올린 뒤 `BASE` 없이 돌린다. 흐름 스크립트는 호스트의 `python3`·`curl`·bash 에 기댄다(기존 스크립트와 같다).
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

### 흐름 확인 (2026-10-23)

`backend/scripts/check_notification_flow.sh` 를 참조 트리의 대역 서버(인증 앱과 API 앱을 한 포트에 묶고 테스트 DB·Redis db 14·테스트 버킷만 쓴다. lifespan 은 API 앱 것이라 디스패처가 함께 돈다)에서 `BASE=http://127.0.0.1:18080` 으로 돌려 **열한 단계·확인 53줄 모두 통과**했다(종료 코드 0, 두 번). 판별력: 5단계 "응답에 번호·변수·업체 메시지 ID 가 없다"의 기대를 `True` 로 뒤집으면 그 줄에서 `실패 … (기대 True, 실제 False)` 로 멈추고 6단계 이후가 나오지 않는 것을 확인했다(종료 코드 1). 운영자 지정과 템플릿 상태 조회는 `PATH` 맨 앞의 대역 `docker` 가 테스트 DB 로 보냈다 — 커밋된 스크립트에는 이 장치가 없다. **게이트웨이(Caddy) 경유는 병합 뒤 실행 때 확인한다.** 라우트 표는 69줄에서 80줄이 됐다(늘어난 경로 정확히 열하나, 없어지거나 바뀐 줄 없음).
````

`_docs/harness.md`:

```diff
@@ -18,6 +18,9 @@
 | 미디어 버킷 준비 | `docker compose run --rm backend python scripts/ensure_media_bucket.py` (버킷 생성 + 원본 수명주기 규칙. MinIO 는 계층 이동을 받지 않아 규칙을 건너뛴다) |
 | 사진·기록 흐름 (게이트웨이·MinIO 경유) | `bash ../backend/scripts/check_media_flow.sh` — 버킷 준비 뒤. 서명 URL 로 저장소에 바로 올리고 읽는다. 개발 DB·버킷에 확인용 매장·사진이 남는다 |
 | 알림장 흐름 (게이트웨이·MinIO 경유) | `bash ../backend/scripts/check_report_flow.sh` — 버킷 준비 뒤. 설정 → 보내기 → 공개 조회(헤더 `X-Report-Token`) → 열람 신호 → 끊기 → 410 → 다시 보내기 → 내려받기. 토큰과 서명 URL 은 화면에 찍지 않는다. 개발 DB·버킷에 확인용 매장·사진·알림장 링크가 남는다 |
+| 알림톡 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_notification_flow.sh` — 채널 연동(토큰 `000000`) → 템플릿 승인(`reregister_templates.py --refresh`) → 발신번호 인증·문자 대체 → 예약 접수·리마인드 → 일정 변경 → 끝 `0000` 번호의 실패와 다시 보내기 → 취소 → 완료와 다음 예약 제안 → 알림장 → 연동 해제. dev 는 가짜 게이트웨이라 실제 발송이 없다. 디스패처가 서버 안에서 돌므로 상태를 몇 초 기다린다(`wait_status`). 번호·알림장 주소·업체 ID 는 화면에 찍지 않는다. 개발 DB 에 확인용 매장·유저·고객·방문·알림 줄이 남는다 |
+| 알림톡 템플릿 재등록·심사 상태 조회 | `docker compose run --rm backend python scripts/reregister_templates.py [--shop <id>] [--refresh]` — 기본은 연동된 매장(또는 하나)에서 코드의 `TEXT_VERSION` 과 다르거나 반려된 종류(없는 종류 포함, `next_visit` 은 켠 매장만)를 새 판으로 등록·검수 요청. `--refresh` 는 등록 없이 `pending` 템플릿의 업체 상태만 적는다(디스패처의 10분 주기를 바로 당긴다). 출력은 매장 ID·종류·결과만 |
+| 알림 표 ↔ DB CHECK·부분 색인·유일 제약 대조 | 통합 테스트 안(`tests/integration/test_notification_schema.py`) — 0011 의 CHECK 13개·유일 제약·부분 유일 색인(`uq_notification_messages_pending`)을 실제 DB 와 대조한다 |
 | 미디어 정리 | `docker compose run --rm backend python scripts/purge_stale_media.py` (하루 넘게 어느 기록도 가져가지 않은 사진·영상 — 운영은 주기적으로) |
 | 최근 방문순 키 복구 | `docker compose run --rm backend python scripts/rebuild_last_visit.py` (고객 목록 '최근 방문순'이 방문 기록과 어긋났을 때) |
 | 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
@@ -45,7 +48,11 @@
 - 앱의 구조 위반은 `test/design/feature_imports_test.dart`(기능 폴더 사이 import 는 `auth` 공용·`home` 껍데기·`visit → customer`만)와 `test/core/router/app_router_test.dart`(열린 경로 목록 밖의 모든 경로는 매장 선택이 없으면 막힌다)가 잡는다. 기능 폴더나 경로를 더한 변경은 이 둘을 돌린다.
 - 유스케이스는 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다. 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간 잡힌다(`apps/*/tests/test_fakes_are_ports.py`). 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 상속하지 않는다.
 - `tests/integration/`은 두 프로세스의 실제 앱 객체에 붙어 프로바이더·DB 커밋·Redis까지 통과한다. 인증 프로세스의 개인키는 테스트마다 새로 만든 키로 바꿔 넣는다.
-- 스포크를 새로 만들면 첫 통합 테스트로 "A매장 멤버가 B매장의 경로를 부르면 403"(테넌트 격리)을 둔다.
+- 스포크를 새로 만들면 첫 통합 테스트로 "A매장 멤버가 B매장의 경로를 부르면 403"(테넌트 격리)을 둔다. notification 도 그렇게 시작했다(`tests/integration/test_notification_onboarding_wiring.py`·`test_notification_messages_wiring.py`의 첫 테스트).
+- 요청 밖(디스패처·운영자 스크립트)에서 `ShopContext`를 만드는 곳은 `notification/app/services/system_context.py` 하나다(권한 빔). 테스트가 요청 밖 코드를 돌릴 때도 이것을 쓴다 — 가드를 흉내 내는 다른 생성자를 만들지 않는다.
+- 디스패처는 테스트에서 루프를 띄우지 않고 `build_dispatcher(session, gateway=FakeGateway(), now=lambda: fixed).run_once()`로 한 번씩 돌린다(`tests/integration/test_notification_dispatcher_wiring.py`). 상한은 `monkeypatch.setattr(dispatcher_provider, "NOTIFICATION_DAILY_CAP", 1)`, 요청 쪽 게이트웨이는 `main.app.dependency_overrides[get_message_gateway] = lambda: fake`(끝나면 pop). `dispatcher_wakeup._event`는 처음 `wait()`한 이벤트 루프에 묶이므로 `wait`를 부르는 테스트 파일은 autouse 픽스처로 새 `asyncio.Event`를 넣는다.
+- 통합 테스트 두 세션을 **동시에** 돌리면(전체 + 파일 하나) 같은 테스트 DB 를 TRUNCATE 해 서로 깨진다 — 차례로 돌린다. 대역 서버(테스트 DB 로 흐름 스크립트를 돌리는 임시 서버)도 통합 테스트와 같이 띄우지 않는다.
+- 실제 발송 업체(`api.solapi.com`)는 테스트에서 부르지 않는다 — 어댑터 테스트는 `httpx.MockTransport`, 나머지는 `FakeGateway`/`SpyGateway`(`notification/tests/helpers/fakes.py`)다. `.env`의 `SOLAPI_*`가 비어 있으면 dev 는 가짜 게이트웨이다.
 - 허브 포트 자리를 새로 만들어도 더할 목록은 없다. `tests/route_inspection.py`가 두 앱의 라우트 의존성 트리를 훑어 ① 채우지 않은 허브 포트 자리 ② `{shop_id}` 경로인데 `get_shop_context`를 거치지 않는 라우트 ③ `/v1/platform/` 경로인데 `require_operator`를 거치지 않는 라우트를 잡는다. API 프로세스는 `tests/test_hub_port_binding.py`가, 인증 프로세스는 `tests/integration/test_route_wiring.py`가 돌린다.
 - 권한이나 불변식이 걸린 슬라이스를 계획할 때는 악의적이거나 운 나쁜 시나리오(내보내진 사람이 쥔 것, 같은 요청이 동시에 두 번, 읽기와 쓰기 사이)를 먼저 표로 적고, 각각을 막는 코드와 테스트를 작업에 넣는다. 작업별 검토는 계획서와의 일치가 아니라 그 표를 기준으로 한다.
 - 통합 테스트에서 두 번째 로그인 수단이 필요하면 `fake_kakao` 픽스처를 쓴다.
```

`backend/apps/customer/_docs/CLAUDE.md`:

```diff
@@ -13,7 +13,7 @@
 - 목록과 반려동물 상세의 번호는 가린다(`010-12··-5678`). 전체 번호는 고객 상세에서만 준다. 전화번호·이름을 로그에 남기지 않는다. 검색어와 번호 조회는 쿼리 문자열로 오므로 API 프로세스가 접근 로그의 쿼리를 가린다(`core/access_log.py`).
 - 고객 삭제는 익명화다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행을 지우고 `deleted_at`을 찍는다. 행과 틀(종류·품종·성별 등)은 남긴다. 익명화한 고객은 모든 조회·검색·번호 조회에서 없는 것으로 본다.
 - 반려동물은 질병을 하나 이상 고르거나 "질병 없음"을 직접 확인해야 저장된다(두 표에 걸친 규칙이라 도메인이 확인한다). 질병 종류는 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다.
-- 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각·카톡 초안 후보). 초안 후보(`find_draft_candidates`)는 낱말 하나라도 걸리는 가족(`CustomerSearchPort.match_any`, OR)을 읽어 반려동물 이름 정확 일치 → 보호자 이름 → 전화 → 부분 일치 순으로 최대 5 가족만 돌려주고, 낱말을 저장하거나 로그에 남기지 않는다. `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
+- 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각·카톡 초안 후보, notification 의 연락처). `contact(ctx, customer_id)`는 살아 있는 이 매장의 고객만 이름·전체 번호(숫자만)·마케팅 동의를 돌려주고 익명화·다른 매장이면 None 이다 — 알림을 보내는 순간에만 읽고(notification), 저장하지 않는다. 초안 후보(`find_draft_candidates`)는 낱말 하나라도 걸리는 가족(`CustomerSearchPort.match_any`, OR)을 읽어 반려동물 이름 정확 일치 → 보호자 이름 → 전화 → 부분 일치 순으로 최대 5 가족만 돌려주고, 낱말을 저장하거나 로그에 남기지 않는다. `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
 - 반려동물 프로필 사진은 저장하지 않는다. 조회 셋(목록 `pets[].photo`, 고객 상세 `pets[].photo`, 반려동물 상세 `pet.photo`)이 읽을 때마다 `VisitLedgerPort.latest_covers`(대표 사진의 media_id)와 `MediaLibraryPort.read_urls`(썸네일 URL)로 한 번씩 묻는다(`app/services/pet_photos.py`, N+1 없음). 쓰기 응답에는 사진이 없다 — 쓰기 뒤 다시 읽는다. `MediaLibraryPort`는 `dependencies/hub_ports.py`의 자리로 받는다.
 - 익명화는 visit 이 방문 메모와 미용 기록의 두 메모(케어·내부)를 비우고 그 고객 방문의 알림장 링크를 끊는다(⑤). 사진은 매장의 기록이라 남긴다. 미용 기록의 몸무게는 visit 이 `CustomerDirectoryPort.set_pet_weight`로 알려 준다(가장 최근 기록일 때만) — 고객 행을 잠근 트랜잭션 안이다.
 - 검색 줄의 `last_visit_at`(최근 방문순)은 원본이 visits 다 — 검색 줄을 다시 만들 때 건드리지 않고, visit 이 `set_last_visit`로 알려 준다.
```

`backend/apps/hub/_docs/CLAUDE.md`:

```diff
@@ -18,9 +18,13 @@
 | `ActiveUserGuardPort.lock_active(user_id) → bool` | auth `guard_active_user` | tenancy `accept_invite` |
 | `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy `apply_withdrawal` | auth `withdraw` (인증 프로세스) |
 | `CustomerDirectoryPort.lock_family · briefs · set_last_visit · set_pet_weight · find_draft_candidates(ctx, words) → list[DraftCandidate]` | customer `customer_directory` | visit (방문 쓰기의 가족 잠금, 이름 표시, 최근 방문순, 기록의 몸무게, 카톡 초안 후보) |
+| `CustomerDirectoryPort.contact(ctx, customer_id) → CustomerContact \| None` (이름·번호(숫자만)·마케팅 동의, 익명화면 None) | customer `customer_directory` | notification 만 (보내는 순간의 연락처 — `briefs` 는 가린 번호라 못 쓴다) |
+| `DomainEventPort.publish(event)` | core `observer/in_process_event_bus.py` (같은 프로세스·같은 세션의 동기 버스, 구독자 목록은 `main.py` 가 기동 때 채운다) | 발행 visit (등록·수정·일정 변경·전이·알림장 보내기), 구독 notification (`adapter/inbound/observer/`) |
 | `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기(`clear_customer_memos` — 알림장 링크도 끊는다)·`latest_covers`) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세, 반려동물 프로필 사진) |
 | `MediaLibraryPort.claim(ctx, ids) → {id: kind} · release · read_urls(ctx, ids) → {id: MediaUrls}` | media `media_library` | visit (기록의 사진·영상, 알림장), customer (프로필 사진) |
-| `ShopProfilePort.public_profile(shop_id) → ShopProfile \| None` (이름·전화·주소·시간대·영업 중 여부) | tenancy `get_shop_profile` | visit (알림장의 매장 정보, 공개 조회의 시간대와 정지·폐업 판정) |
+| `ShopProfilePort.public_profile(shop_id) → ShopProfile \| None` (이름·전화·주소·시간대·영업 중 여부) | tenancy `get_shop_profile` | visit (알림장의 매장 정보, 공개 조회의 시간대와 정지·폐업 판정), notification (보낼 때의 매장 이름·시간대·`shop_closed` 판정, 실패 줄의 `share_text`) |
 
 - `MediaUrls`에는 `download_url`이 있다 — 원본을 첨부 파일로 내려받는 서명 주소다. 칸이 `original_url` 바로 뒤라 `MediaUrls`는 이름 인자로 만든다.
-- `ShopProfilePort.public_profile`은 권한을 보지 않고 정지·폐업한 매장도 돌려준다(`None`은 없는 매장뿐). 로그인한 사용자가 없는 경로가 서명을 확인한 링크에서 읽은 매장 ID 로만 부른다.
+- `ShopProfilePort.public_profile`은 권한을 보지 않고 정지·폐업한 매장도 돌려준다(`None`은 없는 매장뿐). 로그인한 사용자가 없는 경로가 서명을 확인한 링크에서 읽은 매장 ID 로만 부른다. notification 의 디스패처도 요청 밖에서 집은 줄의 매장 ID 로 부른다.
+- 이벤트 DTO 는 `app/dtos/visit_events.py`의 다섯 — `VisitReserved(revived)`, `VisitRescheduled(previous_starts_at)`, `VisitCanceled(reason)`, `VisitClosed(outcome, previous_completed_at)`, `VisitReportIssued(url, expires_at)`. 공통 칸은 `ctx`(발행한 요청의 `ShopContext`)·`visit_id`·`customer_id`·`pet_id`·`starts_at`·`occurred_at`(UTC). 구독자는 발행한 인터랙터와 같은 세션·같은 트랜잭션에서 돌고, **구독자가 던지면 발행한 요청이 실패한다**(의도 — 둘이 어긋나지 않게). `VisitReportIssued.url` 에는 토큰이 든다 — 이벤트를 `%r` 로 로그에 찍지 않는다.
+- notification 은 요청 안에서도 `ShopProfilePort`·`CustomerDirectoryPort` 를 쓴다(`dependencies/hub_ports.py` 의 자리, `share_text`). 요청 밖의 디스패처는 `Depends` 자리를 못 쓰므로 같은 세 프로바이더(tenancy·customer·visit)를 `dependencies/dispatcher_ports.py` 의 공장 자리로 받고 `main.py` 가 꽂는다.
```

`backend/apps/notification/_docs/CLAUDE.md`:

```diff
@@ -1,3 +1,22 @@
 # notification — 알림톡 자동 발송(예약 접수·전날 리마인드·알림장·변경·취소·다음 예약 제안), 매장 채널 연동, 문자 대체
 
-소유 데이터: `notification_channels`, `notification_settings`, `notification_templates`, `notification_messages`(큐이자 발송 기록).
+소유 데이터: `notification_channels`(매장당 한 줄 — 연동 상태·발신번호·문자 대체), `notification_settings`(연동할 때 기본값으로 생김), `notification_templates`((shop_id, kind) 유일 — 업체 템플릿 ID·판 번호·심사 상태), `notification_messages`(큐이자 발송 기록), Redis 의 온보딩 횟수 제한.
+
+- **알림 줄은 visit 의 이벤트로만 생긴다.** `adapter/inbound/observer/visit_event_subscriber.py`가 허브 이벤트(`VisitReserved`·`VisitRescheduled`·`VisitCanceled`·`VisitClosed`·`VisitReportIssued`)를 받아 **발행한 요청과 같은 세션·같은 트랜잭션**에서 줄을 만들거나 취소한다(`app/use_cases/handle_visit_event_interactor.py`). 방문 저장이 롤백되면 줄도 사라지고, 구독자가 던지면 방문 저장도 실패한다(N13). 구독자는 업체를 부르지 않는다(N14). 잠금 순서의 끝이다 — 고객 행 → 방문 행 → **알림 행**.
+- 채널이 `linked` 가 아니거나 설정이 없는 매장은 구독자가 아무것도 하지 않는다(취소도 하지 않는다 — 줄이 없다). 줄을 만드는 공통 조건은 설정 켜짐 + 템플릿 `approved`. `confirm`·`reminder`(예약 시점)·`cancel`·`next_visit`·`report`(같은 주소)는 보낸 적이 있으면 다시 만들지 않고, **변경 안내(`change`)와 바뀐 일정의 `reminder` 는 바뀔 때마다** 만든다(연달아 바꾸면 아직 안 나간 `change` 는 `rescheduled` 로 취소되고 마지막 한 통만 남는다).
+- **같은 방문·같은 종류의 대기 줄은 하나다**(부분 유일 색인 `uq_notification_messages_pending(visit_id, kind) WHERE status IN ('scheduled','sending')`, 세이브포인트라 트랜잭션은 계속 쓴다 — 위반은 `MessageAlreadyPendingError` 409). 색인에 `shop_id` 가 없다 — 방문 ID 가 전 매장에서 유일하다. 줄에는 `pet_id` 가 있다(보내는 순간 `#{대상}` 의 반려동물 이름을 읽는다).
+- **디스패처**(`app/services/dispatcher.py`)는 기동 때 프로세스에 하나 도는 asyncio 작업이다(`dependencies/dispatcher_provider.py`, `main.py` 의 lifespan). 순서는 **집고(`claim_due`, `FOR UPDATE SKIP LOCKED`, `sending`) → 커밋 → 검사 → 보내기 → 접수(`accepted`) 기록·커밋 → 상태 조회**. 잠금을 쥔 채 업체를 부르지 않는다. 2초마다 또는 깨우면(`app/services/dispatcher_wakeup.wake` — 구독자와 재발송이 부른다) 0.5초 뒤 한 번 돈다. 테스트는 루프를 띄우지 않고 `build_dispatcher(session, gateway=…, now=…).run_once()` 를 부른다.
+- **요청 밖에서 `ShopContext` 를 만드는 곳은 `app/services/system_context.py` 하나다**(디스패처·운영자 스크립트, 멤버 0·역할 `system`·권한 빔). 포트 읽기와 알림 표 쓰기에만 쓴다. 시각 계산이 있으면 `ShopProfilePort` 에서 읽은 매장 시간대를 넣는다.
+- **`ShopContext` 를 받지 않는 포트는 `NotificationQueueRepository` 하나다**(전 매장 질의 — 시각이 된 줄 집기, 멈춘 줄 회수, `accepted` 줄, 심사 중 템플릿, 연동된 채널). 공개 알림장의 `PublicReportRepository` 와 같은 예외다. 나머지 매장 범위 포트(`ChannelRepository`·`SettingsRepository`·`TemplateRepository`·`MessageRepository`)는 `ShopContext` 가 첫 인자다. pg 구현은 `MessagePgRepository` 하나가 메시지 포트와 큐 포트를 함께 낸다.
+- **보내기 전 검사 순서와 취소 이유**(설계 5.3): 매장 없음·정지·폐업 `shop_closed` → 채널 `channel_unlinked` → 설정 `setting_off`(매장이 직접 누른 재발송은 건너뛴다) → 템플릿 없음·반려 `template_rejected`(심사 중이면 10분 뒤로 미룸) → 익명화 `anonymized` → 휴대폰 형식 아님 `bad_phone` → (`reminder`·`next_visit`) 매장 시간대 08:00~21:00 밖이면 아침 8시로 미룸, `reminder` 는 미룬 시각이 예약 1시간 전을 넘기면 `too_late` → (`next_visit`) 마케팅 동의 `no_consent` → 앞으로의 예약 `has_upcoming` → 쿨다운 `cooldown` → 하루 상한(`NOTIFICATION_DAILY_CAP`, 기본 300 — 넘으면 취소가 아니라 1시간 뒤로 미루고 WARNING). 이벤트 쪽 취소 이유는 `rescheduled`·`visit_canceled`·`no_show`, 설정·해제 쪽은 `setting_off`·`too_late`·`channel_unlinked`. `report_revoked` 는 값만 있고 아직 쓰는 곳이 없다(알림장 끊기 이벤트가 생기면 쓴다).
+- 야간 미룸은 `reminder`·`next_visit` 에만 있다 — 접수·변경·취소·알림장은 밤에도 바로 간다. 다음 예약 제안은 완료 전이 시각 + N주(설정값, 없으면 이벤트가 실은 앞선 완료 방문과의 간격을 주로 반올림, 그것도 없으면 4주)의 `reminder_time`. 매장이 `reminder_time` 을 바꾸면 설정 인터랙터가 대기 중인 `reminder`·`next_visit` 의 시각을 다시 계산한다(지났으면 `too_late`).
+- **재시도**: 원 시도 1 + 자동 재시도 3. 일시 오류(네트워크·5xx·429·잔액)는 1분·5분·30분 뒤로 `scheduled` 복귀하고 네 번째 실패에서 `failed(transient)`, 영구 오류는 바로 `failed(permanent)`. 둘 다 `attempts` 를 올린다(미룸은 올리지 않는다). 5분 넘은 `sending` 은 다음 루프가 되돌리고 `attempts` 를 올린다. 접수 뒤 상태 조회는 처음 1분은 5초마다, 그 뒤 1분마다(조회가 실패하면 1분), 24시간 안에 최종 상태가 없으면 `failed(transient, TIMEOUT)`.
+- **문자 대체**는 채널의 `sms_fallback_enabled` 와 `sender_number_verified_at` 이 둘 다 있을 때만(`NotificationChannel.can_fallback`, DB CHECK 도 같다). 켜려면 발신번호 본인인증을 먼저 마쳐야 한다(409 `NOTIFICATION_SENDER_NOT_VERIFIED`). 문자용 문안은 EUC-KR 90바이트를 넘으면 LMS. 실제로 나간 길은 `channel_used`(`alimtalk`·`sms`·`lms`)에 적고 상태는 `sent`/`fallback_sent` 로 가른다.
+- **템플릿은 코드의 문안**(`domain/services/templates.py` 의 `TEMPLATES` 여섯, 판 번호 `TEXT_VERSION`)을 **매장 채널마다 등록·검수 요청**한다. 연동 때 기본 5종, `next_visit` 은 설정에서 처음 켤 때. 문안을 고치면 `TEXT_VERSION` 을 올리고 `scripts/reregister_templates.py` 로 전 매장에 새 판을 등록한다(반려된 것도 같은 스크립트). 디스패처가 10분마다 심사 상태를 적고 빠진 종류를 다시 등록한다 — 바로 당기려면 `--refresh`. 변수는 업체가 글자 그대로 넣으므로 이름에 `#{` 가 있어도 문안이 깨지지 않는다(render 도 한 번만 치환).
+- **전화번호·고객 이름·반려동물 이름·매장 이름·주소를 저장하지 않는다** — 보내는 순간 허브 포트로 읽는다(`ShopProfilePort.public_profile`, `CustomerDirectoryPort.contact`(notification 만 쓴다)·`briefs`, `VisitLedgerPort.customer_has_upcoming`). `variables` 에는 이벤트에서만 알 수 있는 값(시각 ISO 문자열, 알림장 주소, 간격)만 든다. **`variables`·번호·주소·업체 ID·업체 응답은 로그와 API 응답에 싣지 않는다**(N12) — 응답 스키마는 칸을 하나하나 적고, 실패 줄에만 문자용 문안 `share_text` 를 만들어 준다. 로그는 message_id·매장·종류·결과(취소 이유·오류 코드)만.
+- **다시 보내기**(`POST …/visits/{visit_id}/notifications/{kind}/resend`, `reservation:write`)는 가장 최근 줄이 끝나 있어야(`canceled`·`sent`·`fallback_sent`·`failed`) 하고 그 줄의 재료로 지금 보낼 새 줄을 만들어 `requested_by_member_id` 를 적는다. **설정이 꺼진 종류도 보낸다**(디스패처도 그 줄은 `setting_off` 를 건너뛴다). 대기 중이면 409 `NOTIFICATION_ALREADY_PENDING`.
+- 방문별 내역(`GET …/visits/{visit_id}/notifications`)은 이 스포크가 방문 표를 모르므로 **다른 매장·없는 방문이면 404 가 아니라 빈 목록**이다. 단건 조회와 재발송은 `shop_id` 로 걸러 404.
+- **온보딩 횟수 제한**은 매장 단위 Redis(`adapter/outbound/redis/onboarding_redis_limiter.py`): 토큰 신청·인증번호 요청은 시간당 5회, 토큰·인증번호 입력은 10분에 5회(맞든 틀리든 센다). 넘으면 429 `NOTIFICATION_RATE_LIMITED`. **Redis 에 닿지 못하면 통과시키고** 경고를 남긴다. 온보딩 호출은 요청 안이라 업체 오류·시간 초과(10초)는 502 `NOTIFICATION_PROVIDER_UNAVAILABLE`. 검색 아이디·관리자 번호는 업체에만 넘기고 저장하지 않는다.
+- 온보딩 인터랙터도 **업체를 먼저 부르고 그 뒤 저장**한다(연동: 토큰 확인 → 템플릿 등록 다섯 → 채널·설정·템플릿 저장). 요청 트랜잭션은 끝날 때 커밋되므로 거꾸로 하면 행 잠금을 쥔 채 HTTP 를 부르게 된다.
+- **게이트웨이**는 `MessageGatewayPort` 하나(`adapter/outbound/strategy/` — Strategy). `SOLAPI_API_KEY`·`SOLAPI_API_SECRET` 이 둘 다 있으면 솔라피, 둘 다 비고 `APP_ENV=dev` 면 가짜, 그 밖은 기동 실패(`dependencies/notification_wiring.get_message_gateway`, lifespan 에서 한 번 만든다). **가짜 게이트웨이의 규칙**: 토큰·인증번호는 `000000` 만 통과, 발송은 늘 접수되고 결과는 번호 끝 네 자리로 — `0000` 영구 실패(문자 대체가 켜져 있으면 문자로 간 것으로), `9999` 일시 실패, `8888` 두 번 대기 뒤 성공, 그 밖은 성공. 템플릿은 바로 승인. 실제 `api.solapi.com` 은 테스트에서 부르지 않는다(`httpx.MockTransport`).
+- 스텁(`tests/helpers/fakes.py`)은 포트 ABC 를 상속하고(`tests/test_fakes_are_ports.py`), `FakeMessages` 가 pg 처럼 메시지·큐 두 포트를 함께 낸다. 시각은 `tests/helpers/builders.kst()` 로 만든다. 통합 테스트의 첫 줄은 테넌트 격리(다른 매장 → 403)다.
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -7,7 +7,7 @@
 - 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK). **상태 이름과 성질(살아 있음·마릿수·시작 시각)의 단일 원천은 `domain/state/visit_status.py`의 표다** — `ACTIVE_STATUSES`·`COUNTED_STATUSES`·ORM CHECK·부분 색인·하루 집계 칸이 거기서 파생한다. 상태를 더하면 표에 한 줄, `visit_state.py`에 상태 클래스 하나, `DayCountsView`에 칸 하나, 그리고 새 마이그레이션이다(`test_schema_drift`는 CHECK·부분 색인을 보지 않는다 — `tests/integration/test_visit_status_schema.py`가 실제 DB 와 표를 대조해 알려 준다).
 - 행동(시작·완료·취소·노쇼·되돌리기)은 `visit_state.ACTIONS`와 바탕 상태 클래스의 같은 이름 메서드가 정한다. `transition()`은 행동 이름으로 메서드를 찾으므로 행동을 더할 때 if 체인을 늘리지 않는다. 시간을 다시 차지하는 행동(`SLOT_RECLAIMING_ACTIONS`)만 가족 확인에 반려동물을 넘긴다(`pets_to_confirm`). 방문의 사실이 바뀐 뒤 customer 에 알리는 후속 처리는 `app/services/completion_effects.py` 한 곳이다 — 전이는 최근 방문 갱신(`apply_completion_effects`)만, 기록 쓰기는 몸무게 동기화(`sync_pet_weight`)만 부른다.
 - **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
-- `visits` 표의 리포지토리는 포트 여섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository`), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`), 피드(`VisitFeedRepository` — 완료 시각 순). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
+- `visits` 표의 리포지토리는 포트 여섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository` — 완료 때 같은 아이의 앞선 완료 방문 시작 시각을 주는 `latest_completed_start_excluding` 포함), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`), 피드(`VisitFeedRepository` — 완료 시각 순). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
 - customer 는 반대 방향 허브 포트 `VisitLedgerPort`(이 스포크 구현, `app/use_cases/visit_ledger_interactor.py`)로 방문을 묻는다. '앞으로의 예약'은 예약됨·미용 중인 방문이다(날짜가 지났어도).
 - 같은 아이(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약은 하나다(부분 유일 색인 — 409 `VISIT_DUPLICATE`, 세이브포인트라 트랜잭션은 계속 쓴다).
 - 겹침·휴무·영업시간 밖은 **막지 않는 경고**다. 판단은 `domain/services/visit_schedule.warnings_for` 한 곳에만 있다.
@@ -18,6 +18,16 @@
 - 기록의 사진·영상은 media 의 허브 포트 `MediaLibraryPort`로 가져가고(claim) 놓는다(release) — 둘 다 조건부 UPDATE 라 잠금 안에서 부른다. 놓인 미디어는 media 의 정리 스크립트가 하루 뒤 지운다. `visit_record_media.kind`는 가져가기가 알려 준 값(바뀌지 않는 사실)이다 — 대표 사진(후 → 전 → 영상 포스터, `cover_media_id`)과 한도(사진 30·영상 3)를 이 표만으로 계산한다. 읽기 URL 은 `read_urls`로 받는다(`app/services/record_reader.py`·`cover_reader.py`).
 - 기록에 몸무게를 처음 적거나 바꾸면 그 방문이 그 아이의 가장 최근 시작한 방문일 때만 `CustomerDirectoryPort.set_pet_weight`로 현재 몸무게를 넘긴다(`completion_effects.sync_pet_weight`). 같은 몸무게로 메모만 고쳐 저장하거나 옛 기록을 고쳐도 현재 값은 그대로다. 전이는 몸무게를 넘기지 않는다.
 - 방문 상세는 기록 전체와 대표 사진, 하루 목록은 `has_record`·`cover`, 달력은 날마다 완료 방문의 `cover`·`covers`(최대 4), 피드(`GET /visits/feed`)는 완료 방문을 완료 시각 역순 커서로 준다. 기록 여러 개는 `VisitRecordRepository.list_many`로 방문 수와 상관없이 한 번에 읽는다.
+- **도메인 이벤트를 발행한다**(⑥). 허브 포트 `DomainEventPort`(`dependencies/hub_ports.get_domain_events` 자리, `main.py` 가 core 의 같은 세션 동기 버스를 꽂는다)로 방문의 사실을 알리고 notification 을 모른다. 구독자는 같은 트랜잭션에서 돌고 던지면 요청이 실패한다. 발행 규칙은 아래 표이고, 공통 칸(`ctx`·`visit_id`·`customer_id`·`pet_id`·`starts_at`)은 쓰기 뒤 행의 값, `occurred_at` 은 인터랙터가 한 번 읽은 `now` 다. 되돌리기는 `VisitReserved(revived=True)`(접수 안내 없이 리마인드만), `start` 는 발행하지 않는다. `pet_id` 만 바뀐 수정도 발행하지 않는다.
+
+| 인터랙터 | 발행 | 위치 |
+|---|---|---|
+| `RegisterVisitInteractor` | 만든 방문마다 `VisitReserved(revived=False)` — `status == reserved` 일 때만(`walk_in` 은 없음) | `create_many` 뒤, 경고 계산 앞 |
+| `UpdateVisitInteractor` | `starts_at` 이 바뀌었을 때만 `VisitRescheduled(previous_starts_at)` | `update_details` 뒤 |
+| `RescheduleVisitsInteractor` | 옮긴 방문마다 `VisitRescheduled(previous_starts_at=잠근 행의 starts_at)` | `reschedule` 뒤, `ensure`·경고 앞 |
+| `TransitionVisitsInteractor` | `cancel` → `VisitCanceled(reason)`, `complete` → `VisitClosed("completed", previous_completed_at=latest_completed_start_excluding(…))`, `no_show` → `VisitClosed("no_show", None)`, `revert` → `VisitReserved(revived=True)` | `apply_changes`·`apply_completion_effects` 뒤, 응답 앞 |
+| `SendVisitReportInteractor` | 새 링크를 만들었을 때만 `VisitReportIssued(url, expires_at)` — 살아 있는 링크의 다시 공유는 발행하지 않는다 | `describe_link` 뒤, 응답 앞 |
+
 - customer 에 `VisitLedgerPort.latest_covers`(사진이 붙은 가장 최근 완료 방문의 대표 — 반려동물 프로필 사진)를 준다. 익명화(`clear_customer_memos`)는 방문 메모와 기록의 두 메모를 비우고 사진은 남긴다.
 - 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
 - 카톡 예약 초안(`POST /visit-drafts`)은 **아무것도 저장하지 않는다.** 글은 `app/ports/output/visit_draft_parser_port.py` 뒤의 규칙 어댑터(`adapter/outbound/rule_draft_parser_adapter.py` → `domain/services/draft_parser.py`)가 날짜·시각·메뉴·낱말로 읽고, "누구"는 허브 포트 `CustomerDirectoryPort.find_draft_candidates`가 낱말로 찾는다(최대 5 가족). 글과 낱말을 로그·DB·오류 응답에 남기지 않는다(설계 10절 V9). ⑨ 이후 LLM 해석은 같은 포트 뒤에서 어댑터만 바꾼다.
```

- [ ] **Step 2: 확인한다**

Run: 커밋할 파일에 비밀 흔적이 없는지 본다 — `git diff --cached | grep -nE "eyJ[A-Za-z0-9_-]{20,}|X-Amz-Signature=|BEGIN [A-Z ]*KEY|_B64=[A-Za-z0-9+/]{20,}|010[0-9]{8}"` → 출력 없음

Run (`infra/`): 단위 전체·구조 계약(Global Constraints 의 명령) → 수가 작업 10 뒤와 같다(1854, 6 kept — 문서는 코드를 바꾸지 않는다)

Run: `_docs/decisions/009-notification.md` 의 API 계약 표의 경로 열하나를 라우트 표와, 오류 코드 표를 `backend/apps/notification/domain/errors.py` 의 `code` 와 `adapter/inbound/api/error_map.py` 의 상태에 대조한다 → 어긋남 없음

- [ ] **Step 3: 커밋한다**

```bash
git add -A
git commit -m "docs: ⑥-1 알림톡 백엔드 — 스포크 규칙, 아키텍처 표, 검증 장치, 결정 기록 009

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: 가족 묶음 예약은 알림톡 한 통(`#{대상}` 에 "콩이·두부"), 링크를 끊으면 아직 안 나간 알림장 알림톡을 취소(`VisitReportRevoked`)

**Files:**
- Modify: `backend/apps/hub/app/dtos/visit_events.py`
- Modify: `backend/apps/notification/app/ports/output/message_repository.py`
- Modify: `backend/apps/notification/app/use_cases/handle_visit_event_interactor.py`
- Modify: `backend/apps/notification/app/services/message_text.py`
- Modify: `_docs/decisions/009-notification.md`
- Modify: `backend/apps/hub/_docs/CLAUDE.md`
- Modify: `backend/apps/notification/_docs/CLAUDE.md`
- Modify: `backend/apps/notification/adapter/outbound/pg/message_pg_repository.py`
- Modify: `backend/apps/notification/tests/adapter/test_notification_pg_repositories.py`
- Modify: `backend/apps/notification/tests/app/services/test_dispatcher.py`
- Modify: `backend/apps/notification/tests/app/use_cases/test_handle_visit_event_interactor.py`
- Modify: `backend/apps/notification/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`
- Modify: `backend/apps/visit/app/use_cases/register_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/revoke_visit_report_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/send_visit_report_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/transition_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/update_visit_interactor.py`
- Modify: `backend/apps/visit/dependencies/revoke_visit_report_provider.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_revoke_visit_report_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_send_visit_report_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`
- Create: `backend/tests/integration/test_notification_review_focus_wiring.py`
- Modify: `backend/tests/integration/test_visit_report_locking.py`

**Interfaces:**
- Consumes: 작업 1 의 이벤트 DTO(frozen dataclass — 기본값 칸은 하위 클래스 맨 끝), 작업 2 의 발행 다섯 곳과 `RevokeVisitReportInteractor`(아직 발행하지 않는다), 작업 4 의 `MessageRepository`·`FakeMessages`, 작업 5 의 구독자 규칙, 작업 7·9 의 `message_text.message_target`(`briefs` 로 이름을 읽는다), 작업 11 의 결정 기록 009 와 `_docs/CLAUDE.md` 셋.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# hub.app.dtos.visit_events — 하위 클래스 다섯의 맨 끝에 (바탕 VisitEvent 에는 없다)
    family_pet_ids: tuple[int, ...] = ()
    # 이 명령이 함께 다룬 같은 보호자·같은 starts_at 방문들의 pet_id(None 제외, 자기 것 포함, 오름차순)
    # 등록·일정 변경: 명령의 방문 전부 / 전이: changed 가운데 같은 starts_at 끼리 / 수정·알림장 보내기·끊기: 자기 pet_id 만((pet_id,) 또는 ())

@dataclass(frozen=True)
class VisitReportRevoked(VisitEvent):
    family_pet_ids: tuple[int, ...] = ()       # 칸 없음

# visit.app.use_cases.revoke_visit_report_interactor
RevokeVisitReportInteractor(visits, reports, directory, events: DomainEventPort, now)
    # revoke 가 True 일 때만 VisitReportRevoked(ctx, visit_id, customer_id, pet_id, starts_at, occurred_at=now, family_pet_ids) 발행
# visit.dependencies.revoke_visit_report_provider — events: DomainEventPort = Depends(get_domain_events)

# notification.app.ports.output.message_repository.MessageRepository (더한 것)
async def has_pending_for_group(self, ctx: ShopContext, customer_id: int, kind: str, starts_at_iso: str) -> bool
    # shop_id·customer_id·kind·status IN (scheduled, sending)·variables->>'starts_at' == starts_at_iso 인 줄이 있는가
    # pg: MessagePgRepository / 스텁: FakeMessages(같은 조건, variables.get("starts_at"))

# notification.app.use_cases.handle_visit_event_interactor (바뀐 규칙)
# confirm·reminder·change·cancel 은 _create_for_group — has_pending_for_group(ctx, event.customer_id, kind, _iso(event.starts_at)) 면 만들지 않는다
# 모든 종류의 variables 에 "pet_ids": ",".join(family_pet_ids or (pet_id,) or ())   → "101,102" · "101" · ""
# VisitReportRevoked → messages.cancel_pending(ctx, "report_revoked", event.visit_id, kinds=(REPORT,))

# notification.app.services.message_text.message_target (바뀐 규칙)
# variables["pet_ids"] 의 아이들을 briefs(ctx, [], pet_ids) 로 읽어 이름(None 제외)을 "·" 로 잇는다. 하나도 없으면 contact.name + "님".
# "pet_ids" 키가 없는 줄(이 칸이 생기기 전 것·그런 줄을 복사한 재발송)은 message.pet_id 로.
```

통합 테스트 도우미(`tests/integration/test_notification_review_focus_wiring.py`): `_shop(wired) -> (shop_id, headers, customer_id, [콩이, 두부])`, `_booked(…, pet_ids, starts_at) -> [visit_id]`, `_rows(wired, visit_id) -> [(kind, status, canceled_reason, pet_ids)]`, `_run_once(wired, gateway, now=None)`, `_targets(gateway, kind) -> ["콩이·두부", …]`, `_insert(…)`(variables jsonb), `_status(wired, shop_id)`, `_paused_queue(wired)`.

머리말 Review Focus 의 1·2 다 — 설계가 빠뜨린 것이라 **구현이 더해진다**(결정 기록 009 "이 계획에서 새로 정한 것"). ① 두 마리를 한 번에 예약하면 방문이 둘이라 접수·리마인드·변경·취소가 두 통 나가던 것을, 같은 보호자·같은 `starts_at`·같은 종류의 대기 줄이 이미 있으면 만들지 않는 규칙(`MessageRepository.has_pending_for_group`)으로 한 통으로 줄이고, 이벤트의 새 칸 `family_pet_ids` 를 `variables["pet_ids"]` 에 실어 `#{대상}` 을 "콩이·두부" 로 잇는다. 줄은 이벤트가 먼저 온 방문에 달리고 취소는 방문 ID 로 하므로 한 마리만 취소하면 그 방문의 줄만 거둔다(009 "알려진 동작" 에 묶음 `reminder` 의 경우를 적었다). ② 알림장 링크를 끊으면 `RevokeVisitReportInteractor` 가 `VisitReportRevoked` 를 발행하고 구독자가 아직 안 나간 `report` 줄을 `report_revoked` 로 취소한다(익명화가 끊는 것은 이벤트 없이 디스패처의 `anonymized` 검사가 막는다). 자연스러운 결과 하나: 같은 방문의 `VisitReserved` 가 두 번 오면 둘째는 묶음 검사에 걸려 조용히 건너뛴다(409 로 드러나는 것은 `report`·`next_visit` 만). 문서 수정(009·hub·visit·notification `_docs/CLAUDE.md`)은 이 커밋에 들어 있다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/notification/tests/adapter/test_notification_pg_repositories.py`:

```diff
@@ -195,6 +195,22 @@ async def test_보낸_줄_판정은_보낸_상태만_세고_주소를_주면_같
     assert await repo.has_delivered(A, 2, CONFIRM) is True
 
 
+async def test_묶음_대기_줄_판정은_같은_고객_종류_시작_시각의_대기_줄만_본다(db_session):
+    repo = MessagePgRepository(db_session)
+    starts = "2026-10-16T05:00:00+00:00"
+    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is False
+    confirm = await repo.create(A, new_message(customer_id=1, variables={"starts_at": starts, "pet_ids": "101,102"}))
+    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is True
+    assert await repo.has_pending_for_group(A, 1, CONFIRM, "2026-10-17T05:00:00+00:00") is False
+    assert await repo.has_pending_for_group(A, 1, REMINDER, starts) is False
+    assert await repo.has_pending_for_group(A, 2, CONFIRM, starts) is False
+    assert await repo.has_pending_for_group(B, 1, CONFIRM, starts) is False
+    await repo.save(A, replace(confirm, status=SENDING))
+    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is True   # sending 도 대기다
+    await repo.save(A, replace(confirm, status=CANCELED, canceled_reason="rescheduled"))
+    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is False
+
+
 async def test_마지막으로_보낸_시각은_고객_종류별로_가장_최근이다(db_session):
     repo = MessagePgRepository(db_session)
     assert await repo.last_delivered_at(A, 1, NEXT_VISIT) is None
```

`backend/apps/notification/tests/app/services/test_dispatcher.py`:

```diff
@@ -172,6 +172,17 @@ async def test_반려동물이_없거나_이름이_없으면_보호자_이름님
     assert [m.variables["대상"] for m in world.sent()] == [f"{NAME}님", f"{NAME}님"]
 
 
+async def test_가족_묶음은_pet_ids_의_아이_이름을_가운뎃점으로_잇고_이름_없는_아이는_뺀다():
+    world = _World()
+    world.directory.family(pet_id=102, pet_name="두부")
+    for pet_ids in ("101,102", "102,101", "101,999", "999", ""):
+        world.queue(id=len(world.messages.rows) + 1, variables={"starts_at": _iso(STARTS), "pet_ids": pet_ids})
+
+    await world.run()
+
+    assert [m.variables["대상"] for m in world.sent()] == ["콩이·두부", "두부·콩이", "콩이", f"{NAME}님", f"{NAME}님"]
+
+
 async def test_알림장은_주소가_버튼에_가고_다음_예약_제안은_지난일과_간격을_넣는다():
     world = _World()
     world.queue(kind=REPORT)
```

`backend/apps/notification/tests/app/use_cases/test_handle_visit_event_interactor.py`:

```diff
@@ -7,6 +7,7 @@ from hub.app.dtos.visit_events import (
     VisitCanceled,
     VisitClosed,
     VisitReportIssued,
+    VisitReportRevoked,
     VisitRescheduled,
     VisitReserved,
 )
@@ -125,8 +126,8 @@ async def test_예약되면_confirm_은_지금_reminder_는_전날_설정_시각
     confirm = world.only(CONFIRM)
     assert (confirm.shop_id, confirm.visit_id, confirm.customer_id, confirm.pet_id) == (1, 7, 1, 101)
     assert confirm.requested_by_member_id is None
-    assert confirm.variables == {"starts_at": _iso(STARTS)}
-    assert world.only(REMINDER).variables == {"starts_at": _iso(STARTS)}
+    assert confirm.variables == {"starts_at": _iso(STARTS), "pet_ids": "101"}
+    assert world.only(REMINDER).variables == {"starts_at": _iso(STARTS), "pet_ids": "101"}
 
 
 async def test_매장의_리마인드_시각을_따른다():
@@ -181,11 +182,19 @@ async def test_되돌린_예약은_reminder_만_만든다():
     assert world.pending() == [(REMINDER, kst(10, 15, 18))]
 
 
-async def test_같은_예약이_두_번_오면_MessageAlreadyPendingError_가_그대로_올라온다():
+async def test_같은_예약이_두_번_오면_둘째는_묶음의_줄로_보아_아무것도_만들지_않는다():
+    """같은 보호자·같은 시각·같은 종류의 대기 줄이 있으면 만들지 않는 묶음 규칙이 중복 발행도 삼킨다 — 색인 위반까지 가지 않는다."""
     world = _World()
     await world.handle(_event(VisitReserved))
+    await world.handle(_event(VisitReserved))
+    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 15, 18))]
+
+
+async def test_같은_알림장이_두_번_오면_MessageAlreadyPendingError_가_그대로_올라온다():
+    world = _World()
+    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
     with pytest.raises(MessageAlreadyPendingError):
-        await world.handle(_event(VisitReserved))
+        await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
 
 
 # --- 일정 바뀜 ------------------------------------------------------------------------------------------------------
@@ -204,8 +213,9 @@ async def test_일정이_바뀌면_옛_reminder_는_rescheduled_로_취소되고
         (REMINDER, SCHEDULED, kst(10, 19, 18), None),
         (CHANGE, SCHEDULED, NOW, None),
     ]
-    assert world.only(CHANGE).variables == {"starts_at": _iso(MOVED), "previous_starts_at": _iso(STARTS)}
-    assert world.only(REMINDER).variables == {"starts_at": _iso(MOVED)}
+    assert world.only(CHANGE).variables == {"starts_at": _iso(MOVED), "previous_starts_at": _iso(STARTS),
+                                            "pet_ids": "101"}
+    assert world.only(REMINDER).variables == {"starts_at": _iso(MOVED), "pet_ids": "101"}
     assert ("cancel_pending", 7, "rescheduled") in world.journal
 
 
@@ -251,7 +261,7 @@ async def test_매장_사정_취소는_대기_줄을_전부_취소하고_cancel_
         (REMINDER, CANCELED, kst(10, 15, 18), "visit_canceled"),
         (CANCEL, SCHEDULED, NOW, None),
     ]
-    assert world.only(CANCEL).variables == {"starts_at": _iso(STARTS)}
+    assert world.only(CANCEL).variables == {"starts_at": _iso(STARTS), "pet_ids": "101"}
 
 
 async def test_고객_요청_취소는_대기_줄만_취소하고_cancel_줄은_없다():
@@ -292,7 +302,7 @@ async def test_완료는_대기_줄을_건드리지_않고_앞선_완료가_없
     await world.handle(_completed())
     assert world.pending() == [(CONFIRM, NOW), (NEXT_VISIT, kst(11, 11, 18))]
     assert world.only(NEXT_VISIT).variables == {
-        "starts_at": _iso(kst(10, 14, 9)), "completed_at": _iso(NOW), "interval_weeks": "4"}
+        "starts_at": _iso(kst(10, 14, 9)), "completed_at": _iso(NOW), "interval_weeks": "4", "pet_ids": "101"}
 
 
 async def test_앞선_완료가_있으면_그_간격을_주로_반올림한_뒤다():
@@ -320,13 +330,65 @@ async def test_다음_예약_제안은_설정_템플릿_보낸_적을_본다(how
     assert world.pending() == []
 
 
+# --- 가족 묶음 ------------------------------------------------------------------------------------------------------
+
+FAMILY = (101, 102)
+
+
+def _pair(cls, **overrides):
+    """두 마리를 한 번에 다룬 명령이 낸 이벤트 둘 — 방문 7(101)·8(102), 같은 보호자·같은 시각."""
+    return (_event(cls, visit_id=7, pet_id=101, family_pet_ids=FAMILY, **overrides),
+            _event(cls, visit_id=8, pet_id=102, family_pet_ids=FAMILY, **overrides))
+
+
+@pytest.mark.parametrize("cls, extra, kinds", [
+    (VisitReserved, {}, [CONFIRM, REMINDER]),
+    (VisitRescheduled, {"previous_starts_at": kst(10, 15, 14)}, [REMINDER, CHANGE]),
+    (VisitCanceled, {"reason": "shop_reason"}, [CANCEL]),
+])
+async def test_가족_묶음은_둘째_이벤트에_줄을_만들지_않고_pet_ids_에_아이들을_싣는다(cls, extra, kinds):
+    world = _World()
+    for event in _pair(cls, **extra):
+        await world.handle(event)
+    assert [k for k, _ in world.pending(7)] == kinds and world.pending(8) == []
+    assert all(world.only(kind).variables["pet_ids"] == "101,102" for kind in kinds)
+
+
+async def test_묶음_가운데_한_마리만_취소하면_cancel_은_그_아이_이름으로_가고_묶음의_줄은_남는다():
+    world = _World()
+    for event in _pair(VisitReserved):
+        await world.handle(event)
+    await world.handle(_event(VisitCanceled, visit_id=8, pet_id=102, family_pet_ids=(102,), reason="shop_reason"))
+    assert [k for k, _ in world.pending(7)] == [CONFIRM, REMINDER]
+    assert world.pending(8) == [(CANCEL, NOW)]
+    assert world.only(CANCEL).variables["pet_ids"] == "102"
+
+
+async def test_pet_ids_는_묶음이_비면_자기_아이_아이가_없으면_빈_문자열이다():
+    world = _World()
+    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
+    await world.handle(_event(VisitReserved, visit_id=8, pet_id=None, starts_at=MOVED))
+    by_visit = {}
+    for m in world.messages.rows.values():
+        by_visit.setdefault(m.visit_id, []).append(m.variables["pet_ids"])
+    assert by_visit == {7: ["101", "101"], 8: ["", ""]}
+
+
+async def test_같은_보호자라도_시각이_다르면_따로_만든다():
+    world = _World()
+    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
+    await world.handle(_event(VisitReserved, visit_id=8, pet_id=102, starts_at=MOVED))
+    assert [k for k, _ in world.pending(7)] == [CONFIRM, REMINDER] == [k for k, _ in world.pending(8)]
+
+
 # --- 알림장 발급 ----------------------------------------------------------------------------------------------------
 
 async def test_알림장을_보내면_report_줄에_주소와_기간이_든다():
     world = _World()
     await world.handle(_event(VisitReportIssued, url=URL, expires_at=kst(11, 13, 0)))
     assert world.pending() == [(REPORT, NOW)]
-    assert world.only(REPORT).variables == {"starts_at": _iso(STARTS), "url": URL, "expires_at": _iso(kst(11, 13, 0))}
+    assert world.only(REPORT).variables == {"starts_at": _iso(STARTS), "url": URL, "expires_at": _iso(kst(11, 13, 0)),
+                                            "pet_ids": "101"}
 
 
 async def test_무기한_링크의_expires_at_은_빈_문자열이다():
@@ -345,6 +407,26 @@ async def test_같은_주소를_이미_보냈으면_만들지_않고_다른_주
     assert world.only(REPORT).variables["url"] == OTHER_URL
 
 
+async def test_링크를_끊으면_아직_안_나간_report_줄만_report_revoked_로_취소한다():
+    world = _World()
+    await world.handle(_event(VisitReserved))
+    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
+    await world.handle(_event(VisitReportRevoked))
+    assert world.rows() == [
+        (CONFIRM, SCHEDULED, NOW, None), (REMINDER, SCHEDULED, kst(10, 15, 18), None),
+        (REPORT, CANCELED, NOW, "report_revoked"),
+    ]
+    assert ("cancel_pending", 7, "report_revoked") in world.journal
+
+
+async def test_끊기는_연동_안_된_매장에서는_아무것도_하지_않는다():
+    world = _World()
+    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
+    world.channels.rows[1] = channel(status=UNLINKED)
+    await world.handle(_event(VisitReportRevoked))
+    assert world.pending() == [(REPORT, NOW)]
+
+
 @pytest.mark.parametrize("how", ["setting_off", "template_pending"])
 async def test_알림장_안내는_설정과_템플릿을_본다(how):
     world = _World(report_enabled=False) if how == "setting_off" else _World()
```

`backend/apps/notification/tests/helpers/fakes.py`:

```diff
@@ -182,6 +182,10 @@ class FakeMessages(MessageRepository, NotificationQueueRepository):
             for m in self._mine(ctx, visit_id=visit_id, kind=kind)
         )
 
+    async def has_pending_for_group(self, ctx, customer_id, kind, starts_at_iso):
+        return any(m.status in PENDING_STATUSES and m.variables.get("starts_at") == starts_at_iso
+                   for m in self._mine(ctx, customer_id=customer_id, kind=kind))
+
     async def last_delivered_at(self, ctx, customer_id, kind):
         sent = [m.sent_at for m in self._mine(ctx, customer_id=customer_id, kind=kind)
                 if m.status in DELIVERED_STATUSES and m.sent_at is not None]
```

`backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`:

```diff
@@ -159,14 +159,22 @@ async def test_임시_휴무일도_closed_day():
 async def test_예약마다_VisitReserved_를_넣은_뒤에_발행한다():
     journal, _, _, _, _, interactor, events = _setup()
     result = await interactor.register_visit(_command(pet_ids=(101, 102)))
-    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.starts_at, e.occurred_at, e.revived)
+    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.starts_at, e.occurred_at, e.revived,
+             e.family_pet_ids)
             for e in events.published] == [
-        (VisitReserved, ctx(), v.visit_id, 1, pet_id, kst(10, 2, 14), NOW, False)
+        (VisitReserved, ctx(), v.visit_id, 1, pet_id, kst(10, 2, 14), NOW, False, (101, 102))
         for v, pet_id in zip(result.visits, (101, 102))]
     names = [entry[0] for entry in journal]
     assert names.index("create_visits") < names.index("publish")
 
 
+async def test_보호자만의_방문은_가족_묶음이_비어_있다():
+    *_, interactor, events = _setup()
+    await interactor.register_visit(_command(pet_ids=()))
+    [event] = events.published
+    assert (event.pet_id, event.family_pet_ids) == (None, ())
+
+
 async def test_지금_시작한_손님은_예약이_아니라_발행하지_않는다():
     *_, interactor, events = _setup()
     await interactor.register_visit(_command(starts_at=None, walk_in=True))
```

`backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`:

```diff
@@ -93,9 +93,10 @@ async def test_옮긴_방문마다_VisitRescheduled_를_옮긴_뒤에_발행한
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
     bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
     await interactor.reschedule_visits(_move([bori.id, kong.id]))
-    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.previous_starts_at, e.starts_at, e.occurred_at)
+    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.previous_starts_at, e.starts_at, e.occurred_at,
+             e.family_pet_ids)
             for e in events.published] == [
-        (VisitRescheduled, ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 15), NOW),
-        (VisitRescheduled, ctx(), bori.id, 1, 102, kst(10, 2, 14), kst(10, 3, 15), NOW)]
+        (VisitRescheduled, ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 15), NOW, (101, 102)),
+        (VisitRescheduled, ctx(), bori.id, 1, 102, kst(10, 2, 14), kst(10, 3, 15), NOW, (101, 102))]
     names = [entry[0] for entry in journal]
     assert names.index("reschedule") < names.index("publish")
```

`backend/apps/visit/tests/app/use_cases/test_revoke_visit_report_interactor.py`:

```diff
@@ -6,7 +6,7 @@ from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
 from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
 from visit.domain.errors import ReportNotFoundError, VisitNotFoundError
 from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeDirectory, FakeReportRepository, FakeVisits, Journal
+from visit.tests.helpers.fakes import FakeDirectory, FakeEvents, FakeReportRepository, FakeVisits, Journal
 
 NOW = kst(9, 24, 10)
 
@@ -18,7 +18,9 @@ class _World:
         self.reports = FakeReportRepository(self.visits, self.journal)
         directory = FakeDirectory(self.journal)
         directory.family(1, pets=(101,))
-        self.interactor = RevokeVisitReportInteractor(self.visits, self.reports, directory, now=lambda: NOW)
+        self.events = FakeEvents(self.journal)
+        self.interactor = RevokeVisitReportInteractor(self.visits, self.reports, directory, events=self.events,
+                                                      now=lambda: NOW)
 
     async def sent(self, expires_at=None, **fields) -> int:
         """어제 보낸 링크가 달린 완료 방문."""
@@ -37,7 +39,8 @@ async def test_잠근_뒤_살아_있는_링크를_끊는다():
     await w.revoke(visit_id)
     assert [r.revoked_at for r in w.reports.rows] == [NOW]
     assert await w.reports.get_live(ctx(), visit_id, NOW) is None
-    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "revoke_report"]
+    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "revoke_report", "publish"]
+    assert [(type(e).__name__, e.visit_id) for e in w.events.published] == [("VisitReportRevoked", visit_id)]
 
 
 async def test_보낸_적이_없거나_이미_끊었으면_REPORT_NOT_FOUND_다():
@@ -48,6 +51,7 @@ async def test_보낸_적이_없거나_이미_끊었으면_REPORT_NOT_FOUND_다(
     await w.revoke(visit_id)
     with pytest.raises(ReportNotFoundError):
         await w.revoke(visit_id)
+    assert len(w.events.published) == 1   # 끊지 못하면 발행하지 않는다
 
 
 async def test_기간이_지난_링크는_끊을_것이_없다():
```

`backend/apps/visit/tests/app/use_cases/test_send_visit_report_interactor.py`:

```diff
@@ -4,7 +4,7 @@ from datetime import timedelta
 import pytest
 
 from hub.app.dtos.shop_profile import ShopProfile
-from hub.app.dtos.visit_events import VisitReportIssued
+from hub.app.dtos.visit_events import VisitReportIssued, VisitReportRevoked
 from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
 from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
 from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
@@ -55,7 +55,8 @@ class _World:
             menus=FakeMenus(), directory=directory, library=library, shops=FakeShopProfile({1: SHOP}),
             events=self.events, now=lambda: self.now, link_key=KEY, web_base_url="https://r.example",
         )
-        self.revoker = RevokeVisitReportInteractor(self.visits, self.reports, directory, now=lambda: self.now)
+        self.revoker = RevokeVisitReportInteractor(self.visits, self.reports, directory, events=self.events,
+                                                   now=lambda: self.now)
 
     def completed(self, status="completed", care_note="눈물 자국", hidden=(), **fields):
         """사진 둘(전 51, 후 52)이 있는 기록이 달린 방문."""
@@ -216,11 +217,24 @@ async def test_처음_보내면_주소와_기간을_실은_VisitReportIssued_를
     sent = await w.send(visit.id)
     [event] = w.events.published
     assert isinstance(event, VisitReportIssued)
-    assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.starts_at, event.occurred_at) == (
-        ctx(), visit.id, 1, 101, kst(9, 23, 14), NOW)
+    assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.starts_at, event.occurred_at,
+            event.family_pet_ids) == (ctx(), visit.id, 1, 101, kst(9, 23, 14), NOW, (101,))
     assert (event.url, event.expires_at) == (sent.link.url, w.reports.rows[0].expires_at)
 
 
+async def test_끊으면_VisitReportRevoked_를_끊은_뒤에_발행한다():
+    w = _World()
+    visit = w.completed()
+    await w.send(visit.id)
+    await w.revoke(visit.id)
+    issued, revoked = w.events.published
+    assert isinstance(revoked, VisitReportRevoked)
+    assert (revoked.ctx, revoked.visit_id, revoked.customer_id, revoked.pet_id, revoked.starts_at, revoked.occurred_at,
+            revoked.family_pet_ids) == (ctx(), visit.id, 1, 101, kst(9, 23, 14), NOW, (101,))
+    names = [e[0] for e in w.journal]
+    assert names.index("revoke_report") < len(names) - 1 == names.index("publish", names.index("revoke_report"))
+
+
 async def test_살아_있는_링크로_다시_보내면_발행하지_않고_끊은_뒤_보내면_다시_발행한다():
     """알림톡은 링크마다 한 번이다."""
     w = _World()
@@ -230,7 +244,8 @@ async def test_살아_있는_링크로_다시_보내면_발행하지_않고_끊
     assert [e.url for e in w.events.published] == [first.link.url]
     await w.revoke(visit_id)
     second = await w.send(visit_id)
-    assert [e.url for e in w.events.published] == [first.link.url, second.link.url]
+    assert [(type(e).__name__, getattr(e, "url", None)) for e in w.events.published] == [
+        ("VisitReportIssued", first.link.url), ("VisitReportRevoked", None), ("VisitReportIssued", second.link.url)]
 
 
 async def test_빈_알림장이면_발행하지_않는다():
```

`backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`:

```diff
@@ -268,6 +268,22 @@ async def test_완료는_같은_아이의_앞선_완료_시작_시각을_실은_
         (VisitClosed, first.id, 2, 201, "completed", None, NOW)]
 
 
+async def test_가족_묶음은_같은_시작_시각끼리_pet_id_를_함께_싣고_한_마리만_취소하면_그_아이뿐이다():
+    _, visits, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
+    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
+    later = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 23, 16))   # 같은 명령이지만 다른 시각
+    await interactor.transition_visits(_act([kong.id, bori.id, later.id], "cancel", "shop_reason"))
+    assert [(e.visit_id, e.family_pet_ids) for e in events.published] == [
+        (kong.id, (101, 102)), (bori.id, (101, 102)), (later.id, (103,))]
+
+    _, visits, interactor, events = _setup()
+    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
+    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
+    await interactor.transition_visits(_act([kong.id], "cancel", "shop_reason"))
+    assert [(e.visit_id, e.family_pet_ids) for e in events.published] == [(kong.id, (101,))]
+
+
 async def test_노쇼는_앞선_완료_없이_VisitClosed_를_발행한다():
     _, visits, interactor, events = _setup()
     _completed(visits, 101, 9, 2)
```

`backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`:

```diff
@@ -120,7 +120,8 @@ async def test_시각을_바꾸면_전후_시각을_실은_VisitRescheduled_를_
     [event] = events.published
     assert isinstance(event, VisitRescheduled)
     assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.previous_starts_at, event.starts_at,
-            event.occurred_at) == (ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 11), NOW)
+            event.occurred_at, event.family_pet_ids) == (ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 11), NOW,
+                                                         (101,))
     names = [entry[0] for entry in journal]
     assert names.index("update_visit") < names.index("publish")
```

`backend/tests/integration/test_notification_review_focus_wiring.py`:

```python
"""사람이 먼저 부딪힐 다섯을 실제 배선(구독자·디스패처·테스트 DB)으로 고정한다 — 가족 묶음은 한 통, 링크를 끊으면
알림장 알림톡 취소, 바뀐 번호로 간다, 멈췄다 돌아온 디스패처, 연달아 두 번 바꾼 예약.

채널·설정·템플릿은 SQL 로 넣고 디스패처는 FakeGateway 로 run_once 를 직접 돈다. 번호는 끝 네 자리만 비교하고 찍지 않는다.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.dependencies.dispatcher_provider import build_dispatcher
from notification.domain.value_objects.message_kind import KINDS
from tests.integration.support import bearer, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}
TEMPLATE = {kind: f"KA01TP000{i}" for i, kind in enumerate(KINDS, start=1)}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


def _utc_iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


async def _link(wired, shop_id: int) -> None:
    await wired.execute(
        "INSERT INTO notification_channels (shop_id, status, provider, provider_channel_id, linked_at) "
        "VALUES (:shop_id, 'linked', 'solapi', 'KA01PF0001', now())", shop_id=shop_id)
    await wired.execute("INSERT INTO notification_settings (shop_id) VALUES (:shop_id)", shop_id=shop_id)
    for kind, template_id in TEMPLATE.items():
        await wired.execute(
            "INSERT INTO notification_templates (shop_id, kind, text_version, provider_template_id, status, "
            "requested_at) VALUES (:shop_id, :kind, 1, :template_id, 'approved', now())",
            shop_id=shop_id, kind=kind, template_id=template_id)


async def _shop(wired):
    """연동한 매장과 두 마리(콩이·두부)를 둔 보호자. (shop_id, headers, customer_id, [pet_ids])"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    await _link(wired, shop_id)
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    customer_id, kong = body["customer"]["customer_id"], body["pets"][0]["pet_id"]
    added = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers,
                                 json={**PET, "name": "두부"})
    assert added.status_code == 201, added.text
    return shop_id, headers, customer_id, [kong, added.json()["pet"]["pet_id"]]


async def _booked(wired, shop_id, headers, customer_id, pet_ids, starts_at: datetime) -> list[int]:
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": customer_id, "pet_ids": pet_ids, "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return [v["visit_id"] for v in booked.json()["visits"]]


async def _transition(wired, shop_id, headers, visit_ids, action, **extra) -> None:
    response = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                    json={"visit_ids": visit_ids, "action": action, **extra})
    assert response.status_code == 200, response.text


async def _rows(wired, visit_id: int) -> list[tuple]:
    """(종류, 상태, 취소 이유, pet_ids 변수) — id 순. 주소는 고르지 않는다."""
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, canceled_reason, variables->>'pet_ids' AS pet_ids "
            "FROM notification_messages WHERE visit_id = :visit_id ORDER BY id"), {"visit_id": visit_id})
        return [tuple(row) for row in rows]


async def _run_once(wired, gateway: FakeGateway, now: datetime | None = None):
    sessions = async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)
    at = now if now is not None else _now()
    async with sessions() as session:
        return await build_dispatcher(session, gateway=gateway, now=lambda: at).run_once()


def _targets(gateway: FakeGateway, kind: str) -> list[str]:
    return [m.variables["대상"] for m in gateway.sent_messages if m.provider_template_id == TEMPLATE[kind]]


# --- 1. 가족 묶음은 한 통 ----------------------------------------------------------------------------------------------

async def test_두_마리_예약은_confirm_reminder_change_가_한_통이고_대상은_두_이름이며_한_마리만_취소하면_그_아이_이름이다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    kong, dubu = await _booked(wired, shop_id, headers, customer_id, pet_ids, _at(3, 14))
    gateway = FakeGateway()
    both = ",".join(str(p) for p in sorted(pet_ids))

    assert await _rows(wired, kong) == [("confirm", "scheduled", None, both), ("reminder", "scheduled", None, both)]
    assert await _rows(wired, dubu) == []
    await _run_once(wired, gateway)
    assert _targets(gateway, "confirm") == ["콩이·두부"]

    moved = await wired.api.post(f"/v1/shops/{shop_id}/visits/reschedule", headers=headers,
                                 json={"visit_ids": [kong, dubu], "starts_at": _at(4, 15).isoformat()})
    assert moved.status_code == 200, moved.text
    changes = [r for v in (kong, dubu) for r in await _rows(wired, v) if r[0] == "change"]
    assert changes == [("change", "scheduled", None, both)]
    await _run_once(wired, gateway)
    assert _targets(gateway, "change") == ["콩이·두부"]

    await _transition(wired, shop_id, headers, [dubu], "cancel", cancel_reason="shop_reason")
    assert [r for r in await _rows(wired, dubu) if r[0] == "cancel"] == [("cancel", "scheduled", None, str(pet_ids[1]))]
    await _run_once(wired, gateway)
    assert _targets(gateway, "cancel") == ["두부"]
    assert len(gateway.sent_messages) == 3


# --- 2. 링크를 끊으면 아직 안 나간 알림장 알림톡을 취소한다 ------------------------------------------------------------

async def _reported(wired, shop_id, headers, customer_id, pet_ids) -> int:
    """어제 방문(한 마리)을 시작·기록·완료하고 알림장을 보낸다 — report 줄이 생긴다. 방문 ID."""
    [visit_id] = await _booked(wired, shop_id, headers, customer_id, pet_ids[:1], _at(-1, 11))
    await _transition(wired, shop_id, headers, [visit_id], "start")
    written = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                  json={"care_note": "눈물 자국을 닦았어요", "media": []})
    assert written.status_code == 200, written.text
    await _transition(wired, shop_id, headers, [visit_id], "complete")
    sent = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/report", headers=headers,
                               json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text
    return visit_id


async def test_디스패처가_돌기_전에_링크를_끊으면_report_는_report_revoked_로_취소되고_다시_보내면_새_줄만_나간다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    visit_id = await _reported(wired, shop_id, headers, customer_id, pet_ids)
    gateway = FakeGateway()
    report = f"/v1/shops/{shop_id}/visits/{visit_id}/report"

    revoked = await wired.api.delete(report, headers=headers)
    assert revoked.status_code == 204, revoked.text
    assert [r[:3] for r in await _rows(wired, visit_id)] == [
        ("confirm", "scheduled", None), ("report", "canceled", "report_revoked")]
    await _run_once(wired, gateway)
    assert _targets(gateway, "report") == []

    again = await wired.api.put(report, headers=headers, json={"hidden_media_ids": []})
    assert again.status_code == 200, again.text
    assert [r[:3] for r in await _rows(wired, visit_id) if r[0] == "report"] == [
        ("report", "canceled", "report_revoked"), ("report", "scheduled", None)]
    await _run_once(wired, gateway)
    assert _targets(gateway, "report") == ["콩이"]
```

`backend/tests/integration/test_visit_report_locking.py`:

```diff
@@ -81,7 +81,7 @@ def _delete_record(session, visit_id):
 
 def _revoke(session, visit_id):
     return RevokeVisitReportInteractor(
-        VisitPgRepository(session), ReportPgRepository(session), _directory(session), now=_now,
+        VisitPgRepository(session), ReportPgRepository(session), _directory(session), events=FakeEvents(), now=_now,
     ).revoke_visit_report(RevokeVisitReportCommand(ctx=SHOP, visit_id=visit_id))
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

### ① (구현 전)
- 단위 `docker compose run --rm --no-deps backend pytest <visit 인터랙터 테스트 6 + notification 구독자·디스패처 테스트> -q -p no:cacheprovider` → 수집 오류 2(`cannot import name 'VisitReportRevoked'` — 알림장·구독자 테스트), `--continue-on-collection-errors` 로 나머지 **10 failed, 96 passed**: `family_pet_ids` 없음(등록 2·일정 변경 1·수정 1·전이 1), `RevokeVisitReportInteractor.__init__() got an unexpected keyword argument 'events'`(끊기 4), "콩이·두부" 가 "콩이"(디스패처 1).
- 통합 `… run --rm backend pytest apps/notification/tests/adapter/test_notification_pg_repositories.py tests/integration/test_notification_review_focus_wiring.py tests/integration/test_visit_report_locking.py -m integration` → **4 failed, 26 passed**: `AttributeError: 'MessagePgRepository' object has no attribute 'has_pending_for_group'`, 새 통합 둘(`KeyError: 'pet_id'` — 반려동물 추가 응답의 키는 `pet.pet_id`, 테스트 쪽 실수라 구현과 함께 고침), 잠금 테스트의 `events` TypeError.
- 구현 뒤 첫 실행에서 테스트 쪽 셋을 고쳤다(구현은 그대로): 기존 알림장 재발행 테스트가 이제 셋째 이벤트(`VisitReportRevoked`)를 봐야 함, 새 `pet_ids` 테스트의 `only(CONFIRM)` 이 두 방문의 confirm 을 집음, 통합 끊기 테스트가 run_once 뒤 confirm 을 `scheduled` 로 기대함. 그리고 규칙의 결과 하나(맨 위 4·6절): "같은 예약이 두 번 오면 `MessageAlreadyPendingError`" 테스트를 "둘째는 묶음의 줄로 보아 아무것도 만들지 않는다"로 바꾸고 색인 위반 테스트는 `report` 로 옮겼다.

### ② — RED 없음, 처음부터 통과
`docker compose run --rm backend pytest tests/integration/test_notification_review_focus_wiring.py -q -p no:cacheprovider -m integration` → **6 passed**(①의 2 + ②의 4). 구현을 바꾸지 않았다.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/dtos/visit_events.py`:

```diff
@@ -8,7 +8,12 @@ from hub.app.dtos.shop_context import ShopContext
 
 @dataclass(frozen=True)
 class VisitEvent:
-    """visit 이 발행하는 사실. 구독자는 같은 트랜잭션에서 돈다(설계 5.1)."""
+    """visit 이 발행하는 사실. 구독자는 같은 트랜잭션에서 돈다(설계 5.1).
+
+    하위 클래스마다 맨 끝에 `family_pet_ids: tuple[int, ...] = ()` 가 있다 — 이 명령이 함께 다룬 같은 보호자·같은
+    시작 시각 방문들의 pet_id(None 은 뺀다, 자기 것 포함, 오름차순). 가족 묶음을 알림톡 한 통으로 묶는 데 쓴다.
+    frozen dataclass 상속에서 기본값 칸은 필수 칸 뒤에 와야 해서 바탕 클래스가 아니라 하위 클래스 끝에 둔다.
+    """
 
     ctx: ShopContext          # 발행한 요청의 매장 컨텍스트 — 구독자가 포트를 부를 때 그대로 쓴다
     visit_id: int
@@ -21,25 +26,38 @@ class VisitEvent:
 @dataclass(frozen=True)
 class VisitReserved(VisitEvent):
     revived: bool = False     # 되돌리기로 다시 예약됨이 된 경우 True(접수 안내는 보내지 않고 리마인드만 다시 만든다)
+    family_pet_ids: tuple[int, ...] = ()
 
 
 @dataclass(frozen=True)
 class VisitRescheduled(VisitEvent):
     previous_starts_at: datetime
+    family_pet_ids: tuple[int, ...] = ()
 
 
 @dataclass(frozen=True)
 class VisitCanceled(VisitEvent):
     reason: str               # "customer_request" | "shop_reason" (visit.domain.entities.visit.CANCEL_REASONS 와 같은 값)
+    family_pet_ids: tuple[int, ...] = ()
 
 
 @dataclass(frozen=True)
 class VisitClosed(VisitEvent):
     outcome: str              # "completed" | "no_show"
     previous_completed_at: datetime | None   # 완료일 때 같은 아이(보호자만이면 보호자만 방문)의 앞선 완료 방문 시작 시각. 노쇼는 None
+    family_pet_ids: tuple[int, ...] = ()
 
 
 @dataclass(frozen=True)
 class VisitReportIssued(VisitEvent):
     url: str                  # 알림장 주소(토큰이 들어 있다 — 로그에 찍지 않는다)
     expires_at: datetime | None
+    family_pet_ids: tuple[int, ...] = ()
+
+
+@dataclass(frozen=True)
+class VisitReportRevoked(VisitEvent):
+    """알림장 링크를 끊었다 — 아직 안 나간 알림장 알림톡을 거둔다. 익명화가 끊는 링크는 이벤트가 없다(디스패처의
+    anonymized 검사가 막는다)."""
+
+    family_pet_ids: tuple[int, ...] = ()
```

`backend/apps/notification/app/ports/output/message_repository.py`:

```diff
@@ -34,6 +34,11 @@ class MessageRepository(ABC):
     async def has_delivered(self, ctx: ShopContext, visit_id: int, kind: str, url: str | None = None) -> bool:
         """보낸 줄(sent·fallback_sent)이 있는가. url 을 주면 variables 의 url 이 같은 줄만(알림장)."""
 
+    @abstractmethod
+    async def has_pending_for_group(self, ctx: ShopContext, customer_id: int, kind: str, starts_at_iso: str) -> bool:
+        """같은 보호자·같은 종류·같은 시작 시각(variables 의 starts_at)의 대기 줄(scheduled·sending)이 있는가 —
+        가족 묶음(두 마리)을 한 통으로 보내려고 둘째 방문의 줄을 만들지 않는 데 쓴다."""
+
     @abstractmethod
     async def last_delivered_at(self, ctx: ShopContext, customer_id: int, kind: str) -> datetime | None:
         """그 고객에게 그 종류를 마지막으로 보낸 시각(쿨다운)."""
```

`backend/apps/notification/app/use_cases/handle_visit_event_interactor.py`:

```diff
@@ -9,6 +9,7 @@ from hub.app.dtos.visit_events import (
     VisitClosed,
     VisitEvent,
     VisitReportIssued,
+    VisitReportRevoked,
     VisitRescheduled,
     VisitReserved,
 )
@@ -34,7 +35,11 @@ class HandleVisitEventInteractor(HandleVisitEventUseCase):
 
     연동되지 않은 매장(채널이 linked 가 아니거나 설정이 없음)은 아무것도 하지 않는다 — 취소도 하지 않는다, 줄이 없다.
     업체를 부르지 않으므로 외부 장애로 방문 저장이 막히지 않는다(N13·N14). 같은 방문·종류의 대기 줄이 이미 있으면
-    저장소의 MessageAlreadyPendingError 를 그대로 올린다 — 발행 쪽의 중복 호출이 500 으로 드러나게 둔다.
+    저장소의 MessageAlreadyPendingError 를 그대로 올린다(report·next_visit) — 발행 쪽의 중복 호출이 드러나게 둔다.
+
+    가족 묶음(같은 보호자·같은 시작 시각의 방문들)은 한 통이다 — confirm·reminder·change·cancel 은 같은 보호자·시각·종류의
+    대기 줄이 이미 있으면 만들지 않고, 만들 때 variables 의 pet_ids 에 묶음의 아이들을 싣는다(디스패처가 `#{대상}` 에
+    이름을 나열한다). 취소는 방문 ID 로 하므로 한 마리만 취소하면 그 방문의 줄만 거둔다.
     """
 
     def __init__(
@@ -66,14 +71,16 @@ class HandleVisitEventInteractor(HandleVisitEventUseCase):
             await self._closed(ctx, settings, event)
         elif isinstance(event, VisitReportIssued):
             await self._report_issued(ctx, settings, event, now)
+        elif isinstance(event, VisitReportRevoked):
+            await self._messages.cancel_pending(ctx, "report_revoked", event.visit_id, kinds=(REPORT,))
 
     async def _reserved(self, ctx: ShopContext, settings: NotificationSettings, event: VisitReserved, now: datetime):
         # 되돌린 예약은 접수 안내를 다시 보내지 않는다 — 리마인드만.
         if not event.revived and await self._allowed(ctx, settings, CONFIRM, event.visit_id):
-            await self._create(ctx, event, CONFIRM, now)
+            await self._create_for_group(ctx, event, CONFIRM, now)
         at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
         if at is not None and await self._allowed(ctx, settings, REMINDER, event.visit_id):
-            await self._create(ctx, event, REMINDER, at)
+            await self._create_for_group(ctx, event, REMINDER, at)
 
     async def _rescheduled(
         self, ctx: ShopContext, settings: NotificationSettings, event: VisitRescheduled, now: datetime
@@ -83,14 +90,14 @@ class HandleVisitEventInteractor(HandleVisitEventUseCase):
         await self._messages.cancel_pending(ctx, "rescheduled", event.visit_id, kinds=(REMINDER, CHANGE))
         at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
         if at is not None and await self._allowed(ctx, settings, REMINDER):
-            await self._create(ctx, event, REMINDER, at)
+            await self._create_for_group(ctx, event, REMINDER, at)
         if await self._allowed(ctx, settings, CHANGE):
-            await self._create(ctx, event, CHANGE, now, previous_starts_at=_iso(event.previous_starts_at))
+            await self._create_for_group(ctx, event, CHANGE, now, previous_starts_at=_iso(event.previous_starts_at))
 
     async def _canceled(self, ctx: ShopContext, settings: NotificationSettings, event: VisitCanceled, now: datetime):
         await self._messages.cancel_pending(ctx, "visit_canceled", event.visit_id)   # N17
         if event.reason == "shop_reason" and await self._allowed(ctx, settings, CANCEL, event.visit_id):
-            await self._create(ctx, event, CANCEL, now)
+            await self._create_for_group(ctx, event, CANCEL, now)
 
     async def _closed(self, ctx: ShopContext, settings: NotificationSettings, event: VisitClosed) -> None:
         if event.outcome == "no_show":
@@ -127,11 +134,22 @@ class HandleVisitEventInteractor(HandleVisitEventUseCase):
             return True
         return not await self._messages.has_delivered(ctx, delivered_visit_id, kind, url=url)
 
+    async def _create_for_group(
+        self, ctx: ShopContext, event: VisitEvent, kind: str, scheduled_at: datetime, **variables: str
+    ) -> None:
+        """가족 묶음의 둘째 방문이면 만들지 않는다 — 같은 보호자·같은 시작 시각·같은 종류의 대기 줄이 한 통을 맡는다."""
+        if await self._messages.has_pending_for_group(ctx, event.customer_id, kind, _iso(event.starts_at)):
+            return
+        await self._create(ctx, event, kind, scheduled_at, **variables)
+
     async def _create(
         self, ctx: ShopContext, event: VisitEvent, kind: str, scheduled_at: datetime, **variables: str
     ) -> None:
-        # starts_at 은 모든 종류에 넣는다 — 디스패처가 #{일시} 와 too_late 판정에 쓴다.
+        # starts_at 은 모든 종류에 넣는다 — 디스패처가 #{일시} 와 too_late 판정에 쓴다. pet_ids 는 #{대상} 의 아이들
+        # (묶음이 비면 자기 아이, 보호자만의 방문이면 빈 문자열).
+        pet_ids = event.family_pet_ids or ((event.pet_id,) if event.pet_id is not None else ())
         await self._messages.create(ctx, NewMessage(
             shop_id=ctx.shop_id, visit_id=event.visit_id, customer_id=event.customer_id, pet_id=event.pet_id,
-            kind=kind, scheduled_at=scheduled_at, variables={"starts_at": _iso(event.starts_at), **variables},
+            kind=kind, scheduled_at=scheduled_at,
+            variables={"starts_at": _iso(event.starts_at), **variables, "pet_ids": ",".join(map(str, pet_ids))},
         ))
```

`backend/apps/notification/app/services/message_text.py`:

```diff
@@ -36,12 +36,16 @@ def message_text(kind: str, *, shop_name: str, target: str, tz: str, variables:
 async def message_target(
     ctx: ShopContext, directory: CustomerDirectoryPort, message: NotificationMessage, contact: CustomerContact,
 ) -> str:
-    """`#{대상}` — 반려동물 이름이 있으면 그것, 없으면 보호자 이름에 '님'. 보낼 때와 share_text 가 같은 재료로 만든다."""
-    pet_name = None
-    if message.pet_id is not None:
-        pet = (await directory.briefs(ctx, [], [message.pet_id])).pets.get(message.pet_id)
-        pet_name = pet.name if pet is not None else None
-    return target_label(pet_name, contact.name)
+    """`#{대상}` — variables 의 pet_ids(가족 묶음)의 아이 이름을 '·' 로 잇는다(이름 없는 아이는 뺀다). 하나도 없으면
+    보호자 이름에 '님'. pet_ids 가 없는 줄(이 칸이 생기기 전 것)은 자기 pet_id 로. 보낼 때와 share_text 가 같은 재료다."""
+    listed = message.variables.get("pet_ids")
+    if listed is None:
+        pet_ids = [message.pet_id] if message.pet_id is not None else []
+    else:
+        pet_ids = [int(p) for p in listed.split(",") if p]
+    pets = (await directory.briefs(ctx, [], pet_ids)).pets if pet_ids else {}
+    names = [pets[p].name for p in pet_ids if p in pets and pets[p].name]
+    return target_label("·".join(names), contact.name)
 
 
 async def message_views(
```

`_docs/decisions/009-notification.md`:

```diff
@@ -28,13 +28,13 @@
 
 ## ⑥-1 백엔드에서 정한 것
 
-새 스포크 `notification`(도메인·포트·pg 저장소·구독자·디스패처·솔라피/가짜 게이트웨이·API 열하나·온보딩 횟수 제한), 허브 이벤트 포트 `DomainEventPort` 와 이벤트 DTO 다섯, 허브 포트 `CustomerDirectoryPort.contact`, `core/observer/`(같은 세션 동기 버스), visit 인터랙터 다섯의 이벤트 발행, 마이그레이션 0011(표 넷, CHECK 13, 유일 제약 1, 색인 5), 설정 키 넷(`SOLAPI_API_KEY`·`SOLAPI_API_SECRET`·`SOLAPI_BALANCE_WARN_KRW`·`NOTIFICATION_DAILY_CAP`), 스크립트 둘(`check_notification_flow.sh`·`reregister_templates.py`). 라우트 표 69 → 80(늘어난 열하나, 없어지거나 바뀐 줄 없음). 단위 1294 → 1854, 통합 405 → 478, 구조 계약 6종(`notification` 을 일곱 목록에 더했고 `tests/test_importlinter_lists_spokes.py` 가 빠뜨림을 잡는다). 새 의존성은 없다(httpx 는 이미 있었다).
+새 스포크 `notification`(도메인·포트·pg 저장소·구독자·디스패처·솔라피/가짜 게이트웨이·API 열하나·온보딩 횟수 제한), 허브 이벤트 포트 `DomainEventPort` 와 이벤트 DTO 여섯, 허브 포트 `CustomerDirectoryPort.contact`, `core/observer/`(같은 세션 동기 버스), visit 인터랙터 여섯의 이벤트 발행, 마이그레이션 0011(표 넷, CHECK 13, 유일 제약 1, 색인 5), 설정 키 넷(`SOLAPI_API_KEY`·`SOLAPI_API_SECRET`·`SOLAPI_BALANCE_WARN_KRW`·`NOTIFICATION_DAILY_CAP`), 스크립트 둘(`check_notification_flow.sh`·`reregister_templates.py`). 라우트 표 69 → 80(늘어난 열하나, 없어지거나 바뀐 줄 없음). 단위 1294 → 1867, 통합 405 → 481, 구조 계약 6종(`notification` 을 일곱 목록에 더했고 `tests/test_importlinter_lists_spokes.py` 가 빠뜨림을 잡는다). 새 의존성은 없다(httpx 는 이미 있었다).
 
 ### 이 계획에서 새로 정한 것
 
 - **변경 안내(`change`)와 바뀐 일정의 `reminder` 는 바뀔 때마다 만든다.** 설계 5.2 의 "같은 종류를 두 번 보내지 않는다"는 `confirm`·`reminder`(예약 시점)·`cancel`·`next_visit`·`report`(같은 주소)에만 적용한다. 연달아 두 번 바꾸면 아직 안 나간 `change` 는 `rescheduled` 로 취소되고 마지막 한 통만 남는다.
 - **`notification_messages.pet_id` 칸을 두었다**(설계 4.4 에 없다). 보내는 순간 `#{대상}` 의 반려동물 이름을 `CustomerDirectoryPort.briefs` 로 읽으려면 필요하다. 외래 키 없음.
-- **취소 이유에 `shop_closed`·`template_rejected`·`report_revoked` 를 더했다**(설계 4.4 의 11개 → 14개). `shop_closed` 는 보내는 순간 매장이 없거나 정지·폐업, `template_rejected` 는 템플릿이 없거나 반려. `report_revoked` 는 값만 있고 아직 쓰는 곳이 없다 — 알림장 끊기를 이벤트로 만드는 작업 11 이 쓴다.
+- **취소 이유에 `shop_closed`·`template_rejected`·`report_revoked` 를 더했다**(설계 4.4 의 11개 → 14개). `shop_closed` 는 보내는 순간 매장이 없거나 정지·폐업, `template_rejected` 는 템플릿이 없거나 반려. `report_revoked` 는 알림장 링크를 끊을 때(`VisitReportRevoked`) 아직 안 나간 `report` 줄에 적는다(작업 11).
 - **지난 방문 간격은 이벤트가 싣는다.** `VisitClosed.previous_completed_at`(같은 아이 — `pet_id` 가 없으면 보호자만 방문끼리 — 의 앞선 완료 방문 `starts_at`, `VisitHistoryRepository.latest_completed_start_excluding`)으로 구독자가 `interval_weeks` 를 센다. notification 이 방문 표를 읽지 않는다. **완료일은 전이 시각(`occurred_at`)이다** — 방문 `starts_at` 이 아니다. 어제 방문을 오늘 완료 처리하면 오늘 기준으로 센다.
 - **다른 매장·없는 방문의 발송 내역은 빈 목록 200 이다**(설계 7.2·9.6 은 404). notification 은 방문 표를 모르고 허브 포트 없이는 방문의 매장을 알 수 없다. 재발송은 그 방문의 줄을 찾지 못해 404, 단건 조회는 `shop_id` 로 걸러 404.
 - **수동 재발송은 설정과 무관하다.** 매장이 직접 누른 줄(`requested_by_member_id` 있음)은 설정이 꺼진 종류여도 보내고, 디스패처도 그 줄은 `setting_off` 검사를 건너뛴다. 그 밖의 검사(매장·채널·템플릿·익명화·번호·야간·동의·상한)는 그대로다. 끝난 줄(성공 포함)은 모두 다시 보낼 수 있어 `MessageNotRetryableError` 는 쓰지 않는다(오류 표에는 남아 있다).
@@ -74,6 +74,8 @@
 - `.env.example` 은 저장소 루트 하나뿐이라 거기에 키 넷을 더했다(`backend/.env.example` 은 없다).
 - **흐름 스크립트는 열한 단계**(확인 53줄). 예약은 모레·글피로 잡는다(브리프의 "내일 14:00"으로는 18:00 뒤에 돌리면 리마인드가 생기지 않는다). 문자 대체를 켠 채 끝 `0000` 번호로 `fallback_sent`(sms)를 먼저 보고, 끈 뒤 다른 `0000` 번호로 `failed`·`share_text`·다시 보내기를 본다. 다음 예약 제안은 다른 보호자의 첫 완료로 본다(같은 아이의 두 번째 완료는 간격이 1주가 된다). `expect` 는 인자 수가 셋이 아니면 멈춘다 — 맥의 bash 3.2 가 `"$( … \" … )"` 안의 이스케이프를 잘못 갈라 빈 인자 둘로 만든 적이 있다(요청 본문은 변수·함수로 먼저 만든다).
 - `reregister_templates.py` 는 없는 종류도 등록한다(디스패처의 10분 주기와 같은 일) — 판이 다르거나 반려된 것과 같은 조건식의 자연스러운 결과다. `--refresh` 는 등록을 부르지 않는다(단위 테스트가 분기 제거 변이를 잡는다).
+- **가족 묶음은 알림톡 한 통이다**(작업 11, 설계 5.2 가 빠뜨린 것). 두 마리를 한 번에 예약하면 방문이 둘이지만 `confirm`·`reminder`·`change`·`cancel` 은 한 통이고 `#{대상}` 은 "콩이·두부"다. 이벤트 DTO 의 하위 클래스마다 맨 끝에 `family_pet_ids: tuple[int, ...] = ()` — 그 명령이 함께 다룬 같은 보호자·같은 시작 시각 방문들의 `pet_id`(None 제외, 자기 것 포함, 오름차순). 등록·일정 변경은 명령의 방문 전부, 전이는 같은 `starts_at` 끼리, 수정·알림장 보내기·끊기는 방문 하나라 자기 아이뿐. 구독자는 네 종류를 만들 때 **같은 보호자·같은 `starts_at`(`variables->>'starts_at'`)·같은 종류의 대기 줄이 있으면 만들지 않는다**(`MessageRepository.has_pending_for_group`) — 묶음의 첫 방문(이벤트가 먼저 온 것)에만 줄이 생긴다. 모든 종류의 `variables` 에 `pet_ids`(`"101,102"`, 묶음이 비면 자기 아이, 보호자만의 방문이면 `""`)를 넣고, 디스패처와 `share_text` 의 `#{대상}` 은 `pet_ids` 의 아이 이름을 `briefs` 로 읽어 "·" 로 잇는다(이름 없는 아이는 빼고, 하나도 없으면 보호자 이름 + "님"; `pet_ids` 가 없는 옛 줄은 자기 `pet_id`). 취소는 방문 ID 로 하므로 한 마리만 취소하면 그 방문의 줄만 거두고 `cancel` 안내는 그 아이 이름으로 간다. 같은 방문의 `VisitReserved` 가 두 번 오면 둘째는 묶음의 줄로 보아 조용히 건너뛴다(색인 위반까지 가지 않는다 — `report`·`next_visit` 만 `MessageAlreadyPendingError`).
+- **링크를 끊으면 아직 안 나간 알림장 알림톡을 취소한다**(작업 11). 허브 이벤트 `VisitReportRevoked`(칸 없음)를 `RevokeVisitReportInteractor` 가 끊은 뒤 발행하고, 구독자가 `cancel_pending(ctx, "report_revoked", visit_id, kinds=(report,))` 한다. 익명화(`clear_customer_memos`)가 끊는 링크는 이벤트 없이 디스패처의 `anonymized` 검사가 막는다.
 
 ### 설계·브리프와 다르게 간 것
 
@@ -97,7 +99,7 @@
 
 ### 알려진 동작 — 막지 않기로 했다
 
-- 가족 묶음(두 마리) 등록은 방문마다 `VisitReserved` 가 따로 오므로 `confirm`·`reminder` 가 마리 수만큼 생긴다. 묶음당 한 통으로 합치는 규칙은 설계 5.2 에 없다.
+- 가족 묶음의 줄은 이벤트가 먼저 온 방문(보통 첫 아이)에 달린다. 그 방문 하나만 취소하면 묶음의 `reminder` 도 함께 거둬져 남은 아이의 리마인드가 없고, 다른 아이 하나만 취소하면 묶음의 `reminder` 는 두 이름 그대로 간다 — 묶음의 줄을 남은 아이로 다시 쓰는 규칙은 두지 않았다. 묶음을 통째로 취소·변경하는 명령이 보통이다.
 - `UpdateVisitInteractor` 는 `pet_id` 만 바뀐 경우 발행하지 않는다 — 보호자에게 "아이가 바뀜"을 알리지 않는다.
 - 예약 등록 한 번에 템플릿 질의가 둘(confirm·reminder)이고, `share_text` 는 요청마다 `public_profile`·`contact`·`briefs` 를 읽는다(실패 줄이 있을 때만).
 - 재발송의 `wake()` 는 커밋 전에 불린다(구독자와 같다). 루프가 0.5초 뒤에 돌므로 보통 그 안에 커밋되지만, 늦으면 다음 주기(2초)에 집는다.
@@ -141,7 +143,6 @@
 - 하루 상한의 뜻(오늘 만든 줄 가운데 접수된 수)이 설계 9.4 의 "오늘 발송"과 조금 다르다(위).
 - 마이그레이션 0011 의 `downgrade` 는 돌려 보지 않았다(개발 DB 에 올리지 않는 규칙). 개발 DB 에 0011 을 올려야 새 경로가 동작한다(compose 의 backend 가 기동할 때 올린다).
 - `MessageNotRetryableError`(409 `NOTIFICATION_NOT_RETRYABLE`)는 오류 표에만 있고 던지는 곳이 없다.
-- `report_revoked` 취소 이유는 작업 11(알림장 끊기 이벤트)이 쓴다. 가족 묶음 한 통 합치기, 알림장 끊기 때 대기 중인 `report` 취소도 작업 11 몫이다.
 - 통합 테스트 두 세션을 동시에 돌리면 같은 테스트 DB 를 TRUNCATE 해 서로 깨진다(하네스 문서에 적었다).
 - 흐름 스크립트는 게이트웨이(Caddy) 경유로 돌려 보지 못했다 — 개발 스택은 원 저장소 코드라 새 경로가 없다. 병합하고 0011 을 올린 뒤 `BASE` 없이 돌린다. 흐름 스크립트는 호스트의 `python3`·`curl`·bash 에 기댄다(기존 스크립트와 같다).
 - `reregister_templates.py` 의 엔진이 `hide_parameters=True` 인지는 `purge_stale_media.py` 처럼 통합 테스트로 못 박지 않았다(단위 테스트만 있다).
@@ -252,7 +253,7 @@ next_visit  [매장명] 콩이 미용한 지 4주가 지났어요.
 
 **가짜 게이트웨이 규칙**(dev, `SOLAPI_*` 가 비었을 때 — 앱 흐름 테스트가 기댄다): 토큰·인증번호는 `000000` 만 통과(다른 값은 400). 템플릿은 디스패처의 다음 조회에서 바로 `approved`. 발송은 늘 접수되고 결과는 보호자 번호 끝 네 자리로 — `0000` 영구 실패(문자 대체가 켜져 있으면 `fallback_sent`), `9999` 일시 실패(1분·5분·30분 재시도 뒤 `failed`), `8888` 두 번 대기 뒤 성공, 그 밖은 `sent`(알림톡). 실제 발송은 없다.
 
-가족 묶음(두 마리) 한 통 합치기와 알림장 끊기 때 대기 중인 `report` 취소(`report_revoked`)는 작업 11 이 더한다 — 그때 이 절에 줄을 더한다.
+가족 묶음(두 마리, 작업 11): 한 번에 예약한 두 방문의 `confirm`·`reminder`·`change`·`cancel` 은 **첫 방문의 내역에만** 한 줄씩 있고 둘째 방문의 `GET /visits/{visit_id}/notifications` 는 그 종류가 비어 있다(한 통이다). 문안의 `#{대상}` 은 "콩이·두부". 한 마리만 취소하면 그 방문에 `cancel` 줄이 생기고 그 아이 이름으로 간다. 알림장 링크를 끊으면(`DELETE /visits/{visit_id}/report`) 아직 안 나간 `report` 줄이 `canceled`/`report_revoked` 가 되고, 다시 보내면 새 `report` 줄이 생긴다.
 
 ### 흐름 확인 (2026-10-23)
```

`backend/apps/hub/_docs/CLAUDE.md`:

```diff
@@ -26,5 +26,5 @@
 
 - `MediaUrls`에는 `download_url`이 있다 — 원본을 첨부 파일로 내려받는 서명 주소다. 칸이 `original_url` 바로 뒤라 `MediaUrls`는 이름 인자로 만든다.
 - `ShopProfilePort.public_profile`은 권한을 보지 않고 정지·폐업한 매장도 돌려준다(`None`은 없는 매장뿐). 로그인한 사용자가 없는 경로가 서명을 확인한 링크에서 읽은 매장 ID 로만 부른다. notification 의 디스패처도 요청 밖에서 집은 줄의 매장 ID 로 부른다.
-- 이벤트 DTO 는 `app/dtos/visit_events.py`의 다섯 — `VisitReserved(revived)`, `VisitRescheduled(previous_starts_at)`, `VisitCanceled(reason)`, `VisitClosed(outcome, previous_completed_at)`, `VisitReportIssued(url, expires_at)`. 공통 칸은 `ctx`(발행한 요청의 `ShopContext`)·`visit_id`·`customer_id`·`pet_id`·`starts_at`·`occurred_at`(UTC). 구독자는 발행한 인터랙터와 같은 세션·같은 트랜잭션에서 돌고, **구독자가 던지면 발행한 요청이 실패한다**(의도 — 둘이 어긋나지 않게). `VisitReportIssued.url` 에는 토큰이 든다 — 이벤트를 `%r` 로 로그에 찍지 않는다.
+- 이벤트 DTO 는 `app/dtos/visit_events.py`의 여섯 — `VisitReserved(revived)`, `VisitRescheduled(previous_starts_at)`, `VisitCanceled(reason)`, `VisitClosed(outcome, previous_completed_at)`, `VisitReportIssued(url, expires_at)`, `VisitReportRevoked`(칸 없음). 공통 칸은 `ctx`(발행한 요청의 `ShopContext`)·`visit_id`·`customer_id`·`pet_id`·`starts_at`·`occurred_at`(UTC), 그리고 하위 클래스마다 맨 끝의 `family_pet_ids: tuple[int, ...] = ()`(그 명령이 함께 다룬 같은 보호자·같은 시작 시각 방문들의 `pet_id`, 오름차순 — 가족 묶음을 알림톡 한 통으로 묶는 데 쓴다. frozen dataclass 상속 때문에 바탕 클래스가 아니라 하위 클래스 끝에 둔다). 구독자는 발행한 인터랙터와 같은 세션·같은 트랜잭션에서 돌고, **구독자가 던지면 발행한 요청이 실패한다**(의도 — 둘이 어긋나지 않게). `VisitReportIssued.url` 에는 토큰이 든다 — 이벤트를 `%r` 로 로그에 찍지 않는다.
 - notification 은 요청 안에서도 `ShopProfilePort`·`CustomerDirectoryPort` 를 쓴다(`dependencies/hub_ports.py` 의 자리, `share_text`). 요청 밖의 디스패처는 `Depends` 자리를 못 쓰므로 같은 세 프로바이더(tenancy·customer·visit)를 `dependencies/dispatcher_ports.py` 의 공장 자리로 받고 `main.py` 가 꽂는다.
```

`backend/apps/notification/_docs/CLAUDE.md`:

```diff
@@ -2,13 +2,14 @@
 
 소유 데이터: `notification_channels`(매장당 한 줄 — 연동 상태·발신번호·문자 대체), `notification_settings`(연동할 때 기본값으로 생김), `notification_templates`((shop_id, kind) 유일 — 업체 템플릿 ID·판 번호·심사 상태), `notification_messages`(큐이자 발송 기록), Redis 의 온보딩 횟수 제한.
 
-- **알림 줄은 visit 의 이벤트로만 생긴다.** `adapter/inbound/observer/visit_event_subscriber.py`가 허브 이벤트(`VisitReserved`·`VisitRescheduled`·`VisitCanceled`·`VisitClosed`·`VisitReportIssued`)를 받아 **발행한 요청과 같은 세션·같은 트랜잭션**에서 줄을 만들거나 취소한다(`app/use_cases/handle_visit_event_interactor.py`). 방문 저장이 롤백되면 줄도 사라지고, 구독자가 던지면 방문 저장도 실패한다(N13). 구독자는 업체를 부르지 않는다(N14). 잠금 순서의 끝이다 — 고객 행 → 방문 행 → **알림 행**.
+- **알림 줄은 visit 의 이벤트로만 생긴다.** `adapter/inbound/observer/visit_event_subscriber.py`가 허브 이벤트(`VisitReserved`·`VisitRescheduled`·`VisitCanceled`·`VisitClosed`·`VisitReportIssued`·`VisitReportRevoked`)를 받아 **발행한 요청과 같은 세션·같은 트랜잭션**에서 줄을 만들거나 취소한다(`app/use_cases/handle_visit_event_interactor.py`). 방문 저장이 롤백되면 줄도 사라지고, 구독자가 던지면 방문 저장도 실패한다(N13). 구독자는 업체를 부르지 않는다(N14). 잠금 순서의 끝이다 — 고객 행 → 방문 행 → **알림 행**.
+- **가족 묶음(같은 보호자·같은 시작 시각의 방문들)은 한 통이다.** `confirm`·`reminder`·`change`·`cancel` 은 같은 보호자·같은 `starts_at`·같은 종류의 대기 줄이 있으면 만들지 않는다(`MessageRepository.has_pending_for_group` — `variables->>'starts_at'` 비교). 줄은 이벤트가 먼저 온 방문에 달리고 `variables.pet_ids`(`"101,102"`, 이벤트의 `family_pet_ids`, 비면 자기 아이, 없으면 `""`)에 묶음의 아이들이 든다. `#{대상}` 은 `message_target` 이 `pet_ids` 의 이름을 `briefs` 로 읽어 "·" 로 잇는다(이름 없는 아이는 빼고, 하나도 없으면 보호자 이름 + "님"). 취소는 방문 ID 로 하니 한 마리만 취소하면 그 방문의 줄만 거둔다.
 - 채널이 `linked` 가 아니거나 설정이 없는 매장은 구독자가 아무것도 하지 않는다(취소도 하지 않는다 — 줄이 없다). 줄을 만드는 공통 조건은 설정 켜짐 + 템플릿 `approved`. `confirm`·`reminder`(예약 시점)·`cancel`·`next_visit`·`report`(같은 주소)는 보낸 적이 있으면 다시 만들지 않고, **변경 안내(`change`)와 바뀐 일정의 `reminder` 는 바뀔 때마다** 만든다(연달아 바꾸면 아직 안 나간 `change` 는 `rescheduled` 로 취소되고 마지막 한 통만 남는다).
 - **같은 방문·같은 종류의 대기 줄은 하나다**(부분 유일 색인 `uq_notification_messages_pending(visit_id, kind) WHERE status IN ('scheduled','sending')`, 세이브포인트라 트랜잭션은 계속 쓴다 — 위반은 `MessageAlreadyPendingError` 409). 색인에 `shop_id` 가 없다 — 방문 ID 가 전 매장에서 유일하다. 줄에는 `pet_id` 가 있다(보내는 순간 `#{대상}` 의 반려동물 이름을 읽는다).
 - **디스패처**(`app/services/dispatcher.py`)는 기동 때 프로세스에 하나 도는 asyncio 작업이다(`dependencies/dispatcher_provider.py`, `main.py` 의 lifespan). 순서는 **집고(`claim_due`, `FOR UPDATE SKIP LOCKED`, `sending`) → 커밋 → 검사 → 보내기 → 접수(`accepted`) 기록·커밋 → 상태 조회**. 잠금을 쥔 채 업체를 부르지 않는다. 2초마다 또는 깨우면(`app/services/dispatcher_wakeup.wake` — 구독자와 재발송이 부른다) 0.5초 뒤 한 번 돈다. 테스트는 루프를 띄우지 않고 `build_dispatcher(session, gateway=…, now=…).run_once()` 를 부른다.
 - **요청 밖에서 `ShopContext` 를 만드는 곳은 `app/services/system_context.py` 하나다**(디스패처·운영자 스크립트, 멤버 0·역할 `system`·권한 빔). 포트 읽기와 알림 표 쓰기에만 쓴다. 시각 계산이 있으면 `ShopProfilePort` 에서 읽은 매장 시간대를 넣는다.
 - **`ShopContext` 를 받지 않는 포트는 `NotificationQueueRepository` 하나다**(전 매장 질의 — 시각이 된 줄 집기, 멈춘 줄 회수, `accepted` 줄, 심사 중 템플릿, 연동된 채널). 공개 알림장의 `PublicReportRepository` 와 같은 예외다. 나머지 매장 범위 포트(`ChannelRepository`·`SettingsRepository`·`TemplateRepository`·`MessageRepository`)는 `ShopContext` 가 첫 인자다. pg 구현은 `MessagePgRepository` 하나가 메시지 포트와 큐 포트를 함께 낸다.
-- **보내기 전 검사 순서와 취소 이유**(설계 5.3): 매장 없음·정지·폐업 `shop_closed` → 채널 `channel_unlinked` → 설정 `setting_off`(매장이 직접 누른 재발송은 건너뛴다) → 템플릿 없음·반려 `template_rejected`(심사 중이면 10분 뒤로 미룸) → 익명화 `anonymized` → 휴대폰 형식 아님 `bad_phone` → (`reminder`·`next_visit`) 매장 시간대 08:00~21:00 밖이면 아침 8시로 미룸, `reminder` 는 미룬 시각이 예약 1시간 전을 넘기면 `too_late` → (`next_visit`) 마케팅 동의 `no_consent` → 앞으로의 예약 `has_upcoming` → 쿨다운 `cooldown` → 하루 상한(`NOTIFICATION_DAILY_CAP`, 기본 300 — 넘으면 취소가 아니라 1시간 뒤로 미루고 WARNING). 이벤트 쪽 취소 이유는 `rescheduled`·`visit_canceled`·`no_show`, 설정·해제 쪽은 `setting_off`·`too_late`·`channel_unlinked`. `report_revoked` 는 값만 있고 아직 쓰는 곳이 없다(알림장 끊기 이벤트가 생기면 쓴다).
+- **보내기 전 검사 순서와 취소 이유**(설계 5.3): 매장 없음·정지·폐업 `shop_closed` → 채널 `channel_unlinked` → 설정 `setting_off`(매장이 직접 누른 재발송은 건너뛴다) → 템플릿 없음·반려 `template_rejected`(심사 중이면 10분 뒤로 미룸) → 익명화 `anonymized` → 휴대폰 형식 아님 `bad_phone` → (`reminder`·`next_visit`) 매장 시간대 08:00~21:00 밖이면 아침 8시로 미룸, `reminder` 는 미룬 시각이 예약 1시간 전을 넘기면 `too_late` → (`next_visit`) 마케팅 동의 `no_consent` → 앞으로의 예약 `has_upcoming` → 쿨다운 `cooldown` → 하루 상한(`NOTIFICATION_DAILY_CAP`, 기본 300 — 넘으면 취소가 아니라 1시간 뒤로 미루고 WARNING). 이벤트 쪽 취소 이유는 `rescheduled`·`visit_canceled`·`no_show`, 설정·해제 쪽은 `setting_off`·`too_late`·`channel_unlinked`. `report_revoked` 는 알림장 링크를 끊을 때(`VisitReportRevoked`) 아직 안 나간 `report` 줄에 적는다.
 - 야간 미룸은 `reminder`·`next_visit` 에만 있다 — 접수·변경·취소·알림장은 밤에도 바로 간다. 다음 예약 제안은 완료 전이 시각 + N주(설정값, 없으면 이벤트가 실은 앞선 완료 방문과의 간격을 주로 반올림, 그것도 없으면 4주)의 `reminder_time`. 매장이 `reminder_time` 을 바꾸면 설정 인터랙터가 대기 중인 `reminder`·`next_visit` 의 시각을 다시 계산한다(지났으면 `too_late`).
 - **재시도**: 원 시도 1 + 자동 재시도 3. 일시 오류(네트워크·5xx·429·잔액)는 1분·5분·30분 뒤로 `scheduled` 복귀하고 네 번째 실패에서 `failed(transient)`, 영구 오류는 바로 `failed(permanent)`. 둘 다 `attempts` 를 올린다(미룸은 올리지 않는다). 5분 넘은 `sending` 은 다음 루프가 되돌리고 `attempts` 를 올린다. 접수 뒤 상태 조회는 처음 1분은 5초마다, 그 뒤 1분마다(조회가 실패하면 1분), 24시간 안에 최종 상태가 없으면 `failed(transient, TIMEOUT)`.
 - **문자 대체**는 채널의 `sms_fallback_enabled` 와 `sender_number_verified_at` 이 둘 다 있을 때만(`NotificationChannel.can_fallback`, DB CHECK 도 같다). 켜려면 발신번호 본인인증을 먼저 마쳐야 한다(409 `NOTIFICATION_SENDER_NOT_VERIFIED`). 문자용 문안은 EUC-KR 90바이트를 넘으면 LMS. 실제로 나간 길은 `channel_used`(`alimtalk`·`sms`·`lms`)에 적고 상태는 `sent`/`fallback_sent` 로 가른다.
```

`backend/apps/notification/adapter/outbound/pg/message_pg_repository.py`:

```diff
@@ -100,6 +100,15 @@ class MessagePgRepository(MessageRepository, NotificationQueueRepository):
         found = await self._session.execute(select(_M.id).where(*conditions).limit(1))
         return found.first() is not None
 
+    async def has_pending_for_group(self, ctx: ShopContext, customer_id: int, kind: str, starts_at_iso: str) -> bool:
+        found = await self._session.execute(
+            select(_M.id).where(
+                _M.shop_id == ctx.shop_id, _M.customer_id == customer_id, _M.kind == kind,
+                _M.status.in_(PENDING_STATUSES), _M.variables["starts_at"].astext == starts_at_iso,
+            ).limit(1)
+        )
+        return found.first() is not None
+
     async def last_delivered_at(self, ctx: ShopContext, customer_id: int, kind: str) -> datetime | None:
         return (
             await self._session.execute(
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -18,7 +18,7 @@
 - 기록의 사진·영상은 media 의 허브 포트 `MediaLibraryPort`로 가져가고(claim) 놓는다(release) — 둘 다 조건부 UPDATE 라 잠금 안에서 부른다. 놓인 미디어는 media 의 정리 스크립트가 하루 뒤 지운다. `visit_record_media.kind`는 가져가기가 알려 준 값(바뀌지 않는 사실)이다 — 대표 사진(후 → 전 → 영상 포스터, `cover_media_id`)과 한도(사진 30·영상 3)를 이 표만으로 계산한다. 읽기 URL 은 `read_urls`로 받는다(`app/services/record_reader.py`·`cover_reader.py`).
 - 기록에 몸무게를 처음 적거나 바꾸면 그 방문이 그 아이의 가장 최근 시작한 방문일 때만 `CustomerDirectoryPort.set_pet_weight`로 현재 몸무게를 넘긴다(`completion_effects.sync_pet_weight`). 같은 몸무게로 메모만 고쳐 저장하거나 옛 기록을 고쳐도 현재 값은 그대로다. 전이는 몸무게를 넘기지 않는다.
 - 방문 상세는 기록 전체와 대표 사진, 하루 목록은 `has_record`·`cover`, 달력은 날마다 완료 방문의 `cover`·`covers`(최대 4), 피드(`GET /visits/feed`)는 완료 방문을 완료 시각 역순 커서로 준다. 기록 여러 개는 `VisitRecordRepository.list_many`로 방문 수와 상관없이 한 번에 읽는다.
-- **도메인 이벤트를 발행한다**(⑥). 허브 포트 `DomainEventPort`(`dependencies/hub_ports.get_domain_events` 자리, `main.py` 가 core 의 같은 세션 동기 버스를 꽂는다)로 방문의 사실을 알리고 notification 을 모른다. 구독자는 같은 트랜잭션에서 돌고 던지면 요청이 실패한다. 발행 규칙은 아래 표이고, 공통 칸(`ctx`·`visit_id`·`customer_id`·`pet_id`·`starts_at`)은 쓰기 뒤 행의 값, `occurred_at` 은 인터랙터가 한 번 읽은 `now` 다. 되돌리기는 `VisitReserved(revived=True)`(접수 안내 없이 리마인드만), `start` 는 발행하지 않는다. `pet_id` 만 바뀐 수정도 발행하지 않는다.
+- **도메인 이벤트를 발행한다**(⑥). 허브 포트 `DomainEventPort`(`dependencies/hub_ports.get_domain_events` 자리, `main.py` 가 core 의 같은 세션 동기 버스를 꽂는다)로 방문의 사실을 알리고 notification 을 모른다. 구독자는 같은 트랜잭션에서 돌고 던지면 요청이 실패한다. 발행 규칙은 아래 표이고, 공통 칸(`ctx`·`visit_id`·`customer_id`·`pet_id`·`starts_at`)은 쓰기 뒤 행의 값, `occurred_at` 은 인터랙터가 한 번 읽은 `now` 다. 되돌리기는 `VisitReserved(revived=True)`(접수 안내 없이 리마인드만), `start` 는 발행하지 않는다. `pet_id` 만 바뀐 수정도 발행하지 않는다. `family_pet_ids` 는 그 명령이 함께 다룬 같은 보호자·같은 `starts_at` 방문들의 `pet_id`(None 제외, 오름차순) — 등록·일정 변경은 명령의 방문 전부, 전이는 같은 `starts_at` 끼리, 수정·알림장은 방문 하나라 자기 아이뿐이다.
 
 | 인터랙터 | 발행 | 위치 |
 |---|---|---|
@@ -27,6 +27,7 @@
 | `RescheduleVisitsInteractor` | 옮긴 방문마다 `VisitRescheduled(previous_starts_at=잠근 행의 starts_at)` | `reschedule` 뒤, `ensure`·경고 앞 |
 | `TransitionVisitsInteractor` | `cancel` → `VisitCanceled(reason)`, `complete` → `VisitClosed("completed", previous_completed_at=latest_completed_start_excluding(…))`, `no_show` → `VisitClosed("no_show", None)`, `revert` → `VisitReserved(revived=True)` | `apply_changes`·`apply_completion_effects` 뒤, 응답 앞 |
 | `SendVisitReportInteractor` | 새 링크를 만들었을 때만 `VisitReportIssued(url, expires_at)` — 살아 있는 링크의 다시 공유는 발행하지 않는다 | `describe_link` 뒤, 응답 앞 |
+| `RevokeVisitReportInteractor` | 살아 있는 링크를 끊었을 때 `VisitReportRevoked` — 끊을 것이 없으면(404) 발행하지 않는다. 익명화가 끊는 링크는 이벤트 없음 | `revoke` 뒤 |
 
 - customer 에 `VisitLedgerPort.latest_covers`(사진이 붙은 가장 최근 완료 방문의 대표 — 반려동물 프로필 사진)를 준다. 익명화(`clear_customer_memos`)는 방문 메모와 기록의 두 메모를 비우고 사진은 남긴다.
 - 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
```

`backend/apps/visit/app/use_cases/register_visit_interactor.py`:

```diff
@@ -70,12 +70,13 @@ class RegisterVisitInteractor(RegisterVisitUseCase):
                 for pet_id in (command.pet_ids or (None,))
             ],
         )
-        # 예약만 알린다 — '지금 시작'은 미용 중으로 시작하니 예약이 아니다.
+        # 예약만 알린다 — '지금 시작'은 미용 중으로 시작하니 예약이 아니다. 한 명령의 방문은 전부 같은 가족 묶음이다.
         if status == RESERVED:
+            family = tuple(sorted(v.pet_id for v in created if v.pet_id is not None))
             for visit in created:
                 await self._events.publish(VisitReserved(
                     ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
-                    starts_at=visit.starts_at, occurred_at=now))
+                    starts_at=visit.starts_at, occurred_at=now, family_pet_ids=family))
 
         warnings = await warnings_after_save(
             ctx, command.customer_id, starts_at, duration, settings, self._board, self._schedule
```

`backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`:

```diff
@@ -44,10 +44,12 @@ class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
         check_same_day(command.starts_at, longest, tz)
         moved = await self._visits.reschedule(ctx, [v.id for v in locked], command.starts_at)
         previous = {v.id: v.starts_at for v in locked}
+        family = tuple(sorted(v.pet_id for v in moved if v.pet_id is not None))   # 한 시각으로 옮긴 같은 보호자의 묶음
         for visit in moved:
             await self._events.publish(VisitRescheduled(
                 ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
-                starts_at=visit.starts_at, occurred_at=now, previous_starts_at=previous[visit.id]))
+                starts_at=visit.starts_at, occurred_at=now, previous_starts_at=previous[visit.id],
+                family_pet_ids=family))
         settings = await self._schedule.ensure(ctx)
         warnings = await warnings_after_save(
             ctx, locked[0].customer_id, command.starts_at, longest, settings, self._board, self._schedule
```

`backend/apps/visit/app/use_cases/revoke_visit_report_interactor.py`:

```diff
@@ -3,7 +3,9 @@ from __future__ import annotations
 from collections.abc import Callable
 from datetime import datetime
 
+from hub.app.dtos.visit_events import VisitReportRevoked
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
 from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
 from visit.app.ports.output.report_repository import ReportRepository
@@ -14,19 +16,24 @@ from visit.domain.errors import ReportNotFoundError
 
 class RevokeVisitReportInteractor(RevokeVisitReportUseCase):
     """알림장 링크 끊기 — 살아 있는 링크만 끊는다. 뺀 사진 표시는 그대로 둔다(다시 보낼 때 앱이 그대로 보여 준다).
-    잠금은 보내기와 같다(고객 행 → 방문 행)."""
+    잠금은 보내기와 같다(고객 행 → 방문 행). 끊은 뒤 알린다 — 아직 안 나간 알림장 알림톡이 거둬진다(설계 5.2)."""
 
     def __init__(
         self, visits: VisitLookupRepository, reports: ReportRepository, directory: CustomerDirectoryPort,
-        now: Callable[[], datetime],
+        events: DomainEventPort, now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
         self._reports = reports
         self._directory = directory
+        self._events = events
         self._now = now
 
     async def revoke_visit_report(self, command: RevokeVisitReportCommand) -> None:
-        ctx = command.ctx
+        ctx, now = command.ctx, self._now()
         [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
-        if not await self._reports.revoke(ctx, visit.id, self._now()):
+        if not await self._reports.revoke(ctx, visit.id, now):
             raise ReportNotFoundError("보낸 알림장이 없습니다.")
+        await self._events.publish(VisitReportRevoked(
+            ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
+            starts_at=visit.starts_at, occurred_at=now,
+            family_pet_ids=(visit.pet_id,) if visit.pet_id is not None else ()))
```

`backend/apps/visit/app/use_cases/send_visit_report_interactor.py`:

```diff
@@ -76,5 +76,6 @@ class SendVisitReportInteractor(SendVisitReportUseCase):
         if issued:
             await self._events.publish(VisitReportIssued(
                 ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
-                starts_at=visit.starts_at, occurred_at=now, url=link.url, expires_at=live.expires_at))
+                starts_at=visit.starts_at, occurred_at=now, url=link.url, expires_at=live.expires_at,
+                family_pet_ids=(visit.pet_id,) if visit.pet_id is not None else ()))
         return VisitReportPreview(report=report, link=link.in_zone(ZoneInfo(ctx.timezone)))
```

`backend/apps/visit/app/use_cases/transition_visits_interactor.py`:

```diff
@@ -57,8 +57,10 @@ class TransitionVisitsInteractor(TransitionVisitsUseCase):
         changed = await self._visits.apply_changes(ctx, changes, ctx.member_id)
         await apply_completion_effects(ctx, locked, changed, self._history, self._directory)
         # 쓰기가 다 끝난 뒤에 알린다 — 구독자가 던지면 전이도 함께 롤백된다(설계 5.1, N13).
+        # 가족 묶음은 같은 보호자(잠금이 보장)·같은 시작 시각인 것끼리다.
         for visit in changed:
-            event = await self._event_for(ctx, command.action, command.cancel_reason, visit, now)
+            family = tuple(sorted(v.pet_id for v in changed if v.starts_at == visit.starts_at and v.pet_id is not None))
+            event = await self._event_for(ctx, command.action, command.cancel_reason, visit, now, family)
             if event is not None:
                 await self._events.publish(event)
         return TransitionedVisitsView(
@@ -66,11 +68,12 @@ class TransitionVisitsInteractor(TransitionVisitsUseCase):
         )
 
     async def _event_for(
-        self, ctx: ShopContext, action: str, cancel_reason: str | None, visit: Visit, now: datetime
+        self, ctx: ShopContext, action: str, cancel_reason: str | None, visit: Visit, now: datetime,
+        family: tuple[int, ...],
     ) -> VisitEvent | None:
         """행동마다 알릴 사실. 시작은 알릴 것이 없다. 되돌리기의 결과는 늘 예약됨이다(`VisitState.revert`)."""
         common = dict(ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
-                      starts_at=visit.starts_at, occurred_at=now)
+                      starts_at=visit.starts_at, occurred_at=now, family_pet_ids=family)
         if action == "cancel":
             return VisitCanceled(**common, reason=cancel_reason)
         if action == "complete":
```

`backend/apps/visit/app/use_cases/update_visit_interactor.py`:

```diff
@@ -66,7 +66,8 @@ class UpdateVisitInteractor(UpdateVisitUseCase):
         if updated.starts_at != current.starts_at:
             await self._events.publish(VisitRescheduled(
                 ctx=ctx, visit_id=updated.id, customer_id=updated.customer_id, pet_id=updated.pet_id,
-                starts_at=updated.starts_at, occurred_at=now, previous_starts_at=current.starts_at))
+                starts_at=updated.starts_at, occurred_at=now, previous_starts_at=current.starts_at,
+                family_pet_ids=(updated.pet_id,) if updated.pet_id is not None else ()))
         warnings = []
         if updated.is_active:
             settings = await self._schedule.ensure(ctx)
```

`backend/apps/visit/dependencies/revoke_visit_report_provider.py`:

```diff
@@ -4,9 +4,10 @@ from fastapi import Depends
 
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.domain_event_port import DomainEventPort
 from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
 from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
 from visit.dependencies.visit_wiring import build_report_repository, build_visit_repository
 from visit.domain.services.visit_schedule import utc_now
 
@@ -14,7 +15,9 @@ from visit.domain.services.visit_schedule import utc_now
 def get_revoke_visit_report_use_case(
     db: DbSession,
     directory: CustomerDirectoryPort = Depends(get_customer_directory),
+    events: DomainEventPort = Depends(get_domain_events),
 ) -> RevokeVisitReportUseCase:
     return RevokeVisitReportInteractor(
-        visits=build_visit_repository(db), reports=build_report_repository(db), directory=directory, now=utc_now,
+        visits=build_visit_repository(db), reports=build_report_repository(db), directory=directory, events=events,
+        now=utc_now,
     )
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 무엇 | 커밋 ① 뒤 | 커밋 ② 뒤 |
|---|---|---|
| 이 작업의 단위(visit 인터랙터 6 + 구독자 + 디스패처 + 스텁 포트 2 + 바인딩) | 202 passed(새로 더한 것 13) | 같음 |
| 이 작업의 통합(pg 저장소 + 새 파일 + 잠금 + 구독자·디스패처 배선) | 44 passed(새로 더한 것 3) | 새 파일 6 passed(+4) |
| 단위 전체 (`-m "not integration and not network"`, `--no-deps`) | **1867 passed**(시작 1854 + 13) | 1867 passed |
| 구조 계약 (`lint-imports`) | 6 kept, 0 broken | 6 kept, 0 broken |
| 라우트 표 (`print_routes.py`) | **80줄**, notification 11줄, 알림장 끊기 경로 그대로 — 변화 없음 | (경로 변화 없음) |

통합 세션은 테스트 DB(`chagocnote_test`)에만 붙었고 한 번에 하나만 돌렸다. 실제 `api.solapi.com` 은 부르지 않았다(게이트웨이는 전부 `FakeGateway`). 비밀 흔적: 두 커밋의 diff 를 `eyJ…|BEGIN … KEY|_B64=|010[0-9]{8}` 로 검사 → 0건(테스트의 번호는 `010-1234-4321` 처럼 하이픈이 있고 비교는 끝 네 자리만, 로그·출력에 찍지 않는다).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_create_for_group` 의 `has_pending_for_group` 검사 제거(두 줄 생김) → `test_handle_visit_event_interactor.py::test_가족_묶음은_둘째_이벤트에_줄을_만들지_않고_pet_ids_에_아이들을_싣는다[VisitReserved·VisitRescheduled·VisitCanceled]`, `::test_같은_예약이_두_번_오면_둘째는_묶음의_줄로_보아_아무것도_만들지_않는다` (4 failed)
- `RevokeVisitReportInteractor` 의 발행 제거(`return` 앞에) → 통합 `test_notification_review_focus_wiring.py::test_디스패처가_돌기_전에_링크를_끊으면_report_는_report_revoked_로_취소되고_다시_보내면_새_줄만_나간다`; 단위 `test_revoke_visit_report_interactor.py::test_잠근_뒤_살아_있는_링크를_끊는다`, `::test_보낸_적이_없거나_이미_끊었으면_REPORT_NOT_FOUND_다`, `test_send_visit_report_interactor.py::test_끊으면_VisitReportRevoked_를_끊은_뒤에_발행한다`, `::test_살아_있는_링크로_다시_보내면_발행하지_않고_끊은_뒤_보내면_다시_발행한다`
- `message_target` 이 첫 아이만(`names[0] if names else None`) → `test_dispatcher.py::test_가족_묶음은_pet_ids_의_아이_이름을_가운뎃점으로_잇고_이름_없는_아이는_뺀다`
- 전이의 묶음을 `starts_at` 으로 가르지 않고 명령의 방문 전부로 → `test_transition_visits_interactor.py::test_가족_묶음은_같은_시작_시각끼리_pet_id_를_함께_싣고_한_마리만_취소하면_그_아이뿐이다`
- 등록의 묶음을 자기 아이만 → `test_register_visit_interactor.py::test_예약마다_VisitReserved_를_넣은_뒤에_발행한다`
- 구독자의 `VisitReportRevoked` 분기 제거 → 통합 `::test_디스패처가_돌기_전에_링크를_끊으면_…`; 단위 `test_handle_visit_event_interactor.py::test_링크를_끊으면_아직_안_나간_report_줄만_report_revoked_로_취소한다`
- pg `has_pending_for_group` 의 `customer_id` 조건 제거 → `test_notification_pg_repositories.py::test_묶음_대기_줄_판정은_같은_고객_종류_시작_시각의_대기_줄만_본다`
- `_create` 의 `pet_ids` 를 자기 아이만(`family_pet_ids` 무시) → `::test_가족_묶음은_둘째_이벤트에_줄을_만들지_않고_pet_ids_에_아이들을_싣는다` 셋

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(notification): 가족 묶음 예약은 알림톡 한 통, 링크를 끊으면 아직 안 나간 알림장 알림톡을 취소

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 13: 남은 경우 셋을 테스트로 고정 — 바뀐 번호로 간다, 멈췄다 돌아온 디스패처, 연달아 두 번 바꾼 예약

**Files:**
- Modify: `backend/tests/integration/test_notification_review_focus_wiring.py`

**Interfaces:**
- Consumes: 작업 7 의 `build_dispatcher(session, gateway=…, now=…)`·`FakeGateway.sent_messages`, 작업 8·9 의 경로, 작업 12 의 통합 파일 `tests/integration/test_notification_review_focus_wiring.py` 와 그 도우미(`_shop`·`_booked`·`_rows`·`_run_once`·`_targets`), 기존 `PUT /customers/{id}`·`PUT /visits/{id}`.
- Produces: 없음(테스트만). 이 작업 뒤 단위 1867·통합 485·구조 계약 6 kept 가 이 계획의 끝 수다.

머리말 Review Focus 의 3·4·5 다. **구현을 바꾸지 않는다** — 작업 1~12 의 테스트가 다루지 않은 경우를 작업 12 의 통합 파일에 더한다. 구현이 이미 있으므로 새 테스트는 처음부터 통과해야 한다. **하나라도 실패하면 구현의 결함이다 — 구현을 고치거나 테스트를 느슨하게 하지 말고 멈춰서 보고한다.** 3 은 번호를 끝 네 자리만 비교하고 찍지 않는다. 4 는 줄을 구독자 없이 SQL 로 넣고(18:00 뒤에 돌려도 리마인드가 있게) `now` 를 `build_dispatcher(…, now=lambda: …)` 로 준다 — 둘로 나뉜다(예약 1시간 전을 넘겨 돌아오면 `too_late` / 밤에 돌아오면 다음 날 08:00 으로 미루고 아침에 나간다, 제안은 그대로). 5 는 `PUT /visits/{id}` 둘로 시각을 연달아 바꾼다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/integration/test_notification_review_focus_wiring.py`:

```diff
@@ -3,6 +3,7 @@
 
 채널·설정·템플릿은 SQL 로 넣고 디스패처는 FakeGateway 로 run_once 를 직접 돈다. 번호는 끝 네 자리만 비교하고 찍지 않는다.
 """
+import json
 from datetime import datetime, timedelta, timezone
 from zoneinfo import ZoneInfo
 
@@ -12,6 +13,7 @@ from sqlalchemy.ext.asyncio import async_sessionmaker
 
 from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
 from notification.dependencies.dispatcher_provider import build_dispatcher
+from notification.domain.services.templates import format_when
 from notification.domain.value_objects.message_kind import KINDS
 from tests.integration.support import bearer, make_operator, shop_with_owner
 
@@ -28,9 +30,9 @@ def _now() -> datetime:
     return datetime.now(timezone.utc)
 
 
-def _at(days: int, hour: int) -> datetime:
+def _at(days: int, hour: int, minute: int = 0) -> datetime:
     day = datetime.now(SEOUL).date() + timedelta(days=days)
-    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)
+    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SEOUL)
 
 
 def _utc_iso(at: datetime) -> str:
@@ -163,3 +165,115 @@ async def test_디스패처가_돌기_전에_링크를_끊으면_report_는_repo
         ("report", "canceled", "report_revoked"), ("report", "scheduled", None)]
     await _run_once(wired, gateway)
     assert _targets(gateway, "report") == ["콩이"]
+
+
+# --- 3. 바뀐 번호로 간다 ------------------------------------------------------------------------------------------------
+
+async def test_예약_뒤에_보호자_번호를_바꾸면_접수_안내는_바뀐_번호로_간다(wired):
+    shop_id, headers, customer_id, pet_ids = await _shop(wired)
+    await _booked(wired, shop_id, headers, customer_id, pet_ids[:1], _at(3, 14))
+    changed = await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers,
+                                  json={**CUSTOMER, "phone": "010-1234-4321"})
+    assert changed.status_code == 200, changed.text
+    gateway = FakeGateway()
+
+    report = await _run_once(wired, gateway)
+
+    assert report.sent == 1
+    assert gateway.sent_messages[-1].to[-4:] == "4321"   # 끝 네 자리만 비교한다 — 번호를 찍지 않는다
+
+
+# --- 4. 멈췄다 돌아온 디스패처 -----------------------------------------------------------------------------------------
+
+async def _insert(wired, shop_id, customer_id, pet_id, visit_id, kind, scheduled_at, **variables) -> None:
+    """줄을 직접 넣는다 — 시각을 마음대로 두려고 구독자를 거치지 않는다."""
+    await wired.execute(
+        "INSERT INTO notification_messages (shop_id, customer_id, pet_id, visit_id, kind, status, scheduled_at, variables) "
+        "VALUES (:shop_id, :customer_id, :pet_id, :visit_id, :kind, 'scheduled', :scheduled_at, CAST(:variables AS jsonb))",
+        shop_id=shop_id, customer_id=customer_id, pet_id=pet_id, visit_id=visit_id, kind=kind, scheduled_at=scheduled_at,
+        variables=json.dumps({"pet_ids": str(pet_id), **variables}))
+
+
+async def _status(wired, shop_id: int) -> list[tuple]:
+    """(종류, 상태, 취소 이유, scheduled_at) — id 순."""
+    async with wired.engine.connect() as conn:
+        rows = await conn.execute(text(
+            "SELECT kind, status, canceled_reason, scheduled_at FROM notification_messages "
+            "WHERE shop_id = :shop_id ORDER BY id"), {"shop_id": shop_id})
+        return [tuple(row) for row in rows]
+
+
+async def _paused_queue(wired):
+    """내일 14:00 예약의 reminder(오늘 18:00)와 완료 방문의 next_visit(4주 뒤 18:00)이 대기 중인 매장."""
+    shop_id, _, customer_id, pet_ids = await _shop(wired)
+    await _insert(wired, shop_id, customer_id, pet_ids[0], 1, "reminder", _at(0, 18), starts_at=_utc_iso(_at(1, 14)))
+    await _insert(wired, shop_id, customer_id, pet_ids[0], 2, "next_visit", _at(28, 18),
+                  starts_at=_utc_iso(_at(-1, 14)), completed_at=_utc_iso(_at(0, 11)), interval_weeks="4")
+    return shop_id
+
+
+async def test_멈췄다가_예약_1시간_전을_넘겨_돌아오면_reminder_는_too_late_다(wired):
+    shop_id = await _paused_queue(wired)
+    gateway = FakeGateway()
+
+    await _run_once(wired, gateway, _at(1, 13, 30))
+
+    assert await _status(wired, shop_id) == [
+        ("reminder", "canceled", "too_late", _at(0, 18)), ("next_visit", "scheduled", None, _at(28, 18))]
+    assert gateway.sent_messages == []
+
+
+async def test_멈췄다가_밤에_돌아오면_reminder_는_다음_날_08시로_미루고_next_visit_은_그대로이며_아침에_나간다(wired):
+    shop_id = await _paused_queue(wired)
+    gateway = FakeGateway()
+
+    night = await _run_once(wired, gateway, _at(0, 23))
+    assert (night.claimed, night.deferred) == (1, 1)
+    assert await _status(wired, shop_id) == [
+        ("reminder", "scheduled", None, _at(1, 8)), ("next_visit", "scheduled", None, _at(28, 18))]
+
+    morning = await _run_once(wired, gateway, _at(1, 8))
+    assert (morning.claimed, morning.sent) == (1, 1)
+    assert [r[:2] for r in await _status(wired, shop_id)] == [("reminder", "accepted"), ("next_visit", "scheduled")]
+    [outgoing] = gateway.sent_messages
+    assert (outgoing.provider_template_id, outgoing.variables["대상"], outgoing.variables["시각"]) == (
+        TEMPLATE["reminder"], "콩이", "14:00")
+
+
+# --- 5. 연달아 두 번 바꾼 예약 -----------------------------------------------------------------------------------------
+
+async def test_연달아_두_번_바꾸면_change_는_마지막_한_통만_대기하고_이전_시각은_첫_변경_뒤_시각이다(wired):
+    shop_id, headers, customer_id, pet_ids = await _shop(wired)
+    first, second, third = _at(3, 14), _at(4, 15), _at(5, 16)
+    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
+                                  json={"customer_id": customer_id, "pet_ids": pet_ids[:1], "starts_at": first.isoformat()})
+    assert booked.status_code == 201, booked.text
+    visit = booked.json()["visits"][0]
+    for starts_at in (second, third):
+        moved = await wired.api.put(
+            f"/v1/shops/{shop_id}/visits/{visit['visit_id']}", headers=headers,
+            json={"starts_at": starts_at.isoformat(), "pet_id": pet_ids[0], "duration_minutes": visit["duration_minutes"],
+                  "menu_ids": [], "memo": None})
+        assert moved.status_code == 200, moved.text
+
+    async with wired.engine.connect() as conn:
+        rows = await conn.execute(text(
+            "SELECT kind, status, canceled_reason, scheduled_at, variables->>'starts_at' AS starts_at, "
+            "variables->>'previous_starts_at' AS previous_starts_at "
+            "FROM notification_messages WHERE visit_id = :visit_id ORDER BY id"), {"visit_id": visit["visit_id"]})
+        rows = [dict(r._mapping) for r in rows]
+    assert [(r["kind"], r["status"], r["canceled_reason"]) for r in rows] == [
+        ("confirm", "scheduled", None),
+        ("reminder", "canceled", "rescheduled"), ("reminder", "canceled", "rescheduled"), ("change", "canceled", "rescheduled"),
+        ("reminder", "scheduled", None), ("change", "scheduled", None),
+    ]
+    reminder, change = rows[4], rows[5]
+    assert (reminder["scheduled_at"], reminder["starts_at"]) == (_at(4, 18), _utc_iso(third))
+    assert (change["previous_starts_at"], change["starts_at"]) == (_utc_iso(second), _utc_iso(third))
+
+    gateway = FakeGateway()
+    await _run_once(wired, gateway)
+
+    [change_sent] = [m for m in gateway.sent_messages if m.provider_template_id == TEMPLATE["change"]]
+    assert (change_sent.variables["이전일시"], change_sent.variables["일시"]) == (
+        format_when(second, "Asia/Seoul"), format_when(third, "Asia/Seoul"))
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

이 작업에는 RED 가 없다. 아래로 새 테스트가 **처음부터 통과**하는지 본다(구현 코드는 작업 1~12 에 있다).

Run (`infra/`): `docker compose run --rm backend pytest tests/integration/test_notification_review_focus_wiring.py -q -p no:cacheprovider -m integration` → 6 passed(작업 12 의 2 + 이 작업의 4)

- [ ] **Step 3: 구현한다**

이 작업에는 구현 파일이 없다 — 테스트만 더한다. 구현 코드는 손대지 않는다.

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest tests/integration/test_notification_review_focus_wiring.py -q -p no:cacheprovider -m integration` → 6 passed

Run (`infra/`): 통합 전체 → 485 passed(작업 12 뒤 481 + 4), 단위 전체 → 1867 passed(변화 없음), 구조 계약 6 kept

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 구현을 바꾸지 않으므로 변이는 테스트 쪽에 넣는다 — 4 의 둘째 테스트에서 첫 `_run_once` 의 `now` 를 밤 `_at(0, 23)` 대신 낮 `_at(0, 15)` 로 → 리마인드가 미뤄지지 않고 바로 나가 `("reminder", "scheduled", None, _at(1, 8))` 단언이 실패한다. 확인한 뒤 편집으로 되돌린다
- 3 의 테스트에서 번호 변경 PUT 을 지우면 → `to[-4:] == "4321"` 단언이 실패한다(옛 번호로 간다 — 줄이 번호를 저장하지 않음을 보여 준다). 확인한 뒤 되돌린다

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "test(notification): 바뀐 번호·멈췄다 돌아온 디스패처·연달아 바꾼 예약을 고정

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---
