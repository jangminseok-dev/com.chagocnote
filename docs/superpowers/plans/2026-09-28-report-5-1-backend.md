# 차곡노트 ⑤ 미용 알림장 — 계획 ⑤-1 백엔드: 링크·설정·미리보기·공개 조회 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장이 완료한 방문에서 알림장 링크를 만들고 끊고, 보호자가 로그인 없이 그 링크로 공개하기로 한 것만 읽게 한다 — 웹(⑤-2)과 앱(⑤-3)이 기댈 백엔드 API 전부다.

**Architecture:** 알림장은 새 스포크가 아니라 `visit` 위에 쌓인다. 링크는 `visit_reports` 한 줄이고 토큰은 저장하지 않고 `public_id + HMAC(서버 키)`로 그때마다 계산한다. 매장용 API 다섯(설정 둘, 미리보기·보내기·끊기)과 공개 API 둘(조회·열람 신호)이 같은 조립 함수 `describe_report` 로 알림장을 만든다. 공개 조회는 로그인한 사용자가 없으므로 허브 포트 `ShopProfilePort`(tenancy 구현)로 매장을 읽고, 횟수 제한은 Redis 고정 창이다. 모든 코드는 참조 작업 트리(`.superpowers/ref/wt-report-5-1-be`, 브랜치 `ref/report-5-1-be`, 커밋 f0d120c…7728526)에서 먼저 돌려 검증했고, 변이 179개로 판별력을 확인했다.

**Tech Stack:** Python 3.13 · FastAPI 0.141 · SQLAlchemy 2.0(asyncio) · Alembic · Redis · pytest · import-linter. 새 의존성은 없다.

**Spec:** `docs/superpowers/specs/2026-09-28-report-design.md` — 이 계획은 3절(구조)·4절(데이터 모델)·5절(토큰)·6절(API)·7절(보안과 오류 처리)·11.1(백엔드 테스트)·11.4 의 백엔드 문서다. 실행자는 설계 문서와 함께 `_docs/architecture.md`, `_docs/harness.md`, `backend/apps/{hub,visit,tenancy,media}/_docs/CLAUDE.md`, `_docs/decisions/002-hub-port-assembly.md`·`006-visit-reservation.md`·`007-record-media.md` 를 읽는다.

**계획의 위치:** ⑤의 구현 계획 셋 가운데 첫째다. **⑤-1 백엔드(이 문서)** → ⑤-2 웹(`web/`, Next.js) → ⑤-3 앱. ⑤-2·⑤-3 은 이 계획을 구현한 뒤 실제 코드를 보고 쓴다. 둘이 기댈 API 계약은 작업 10 의 결정 기록 008 에 있다. 작업은 열하나다 — 1~8 구현, 9 흐름 스크립트, 10 문서, 11 남은 경우의 테스트.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 백엔드 명령은 `infra/`에서 돌린다. 맥에 파이썬 환경을 만들지 않는다.
- 작업 브랜치는 `feat/report`다(main `d78bdc9`에서 땄고, 설계 문서와 이 계획서가 앞의 커밋이다). `main`에서 직접 작업하지 않는다.
- **작업 단위 커밋**: 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 사용자가 요청할 때만 한다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.**
- 계획서의 코드 블록은 그대로 옮긴다. 새 파일은 전문이고, 수정 파일은 diff 다. diff 가 적용되지 않으면 멈추고 보고한다 — 손으로 "비슷하게" 고치지 않는다.
- 볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다. 마이그레이션 0010 은 더하기만 한다.
- **비밀값·토큰·서명 URL·고객 개인정보를 로그·커밋·문서·보고에 남기지 않는다.** `.env*` 의 내용을 출력하지 않는다. 실패한 통합 테스트의 출력에는 테스트용 토큰과 서명 주소가 지역 변수로 찍히므로 옮겨 적지 않는다(`--tb=line`·`--tb=short` 로 돌린다).
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다. 요청받지 않은 기능·설정·추상화를 넣지 않는다.

구조 (`_docs/architecture.md`, 스포크 `CLAUDE.md` 그대로 — 이 계획이 문서에 더하는 규칙 포함)
- 스포크끼리 직접 import 하지 않는다. visit 은 tenancy·media·customer 를 허브 포트로만 만난다. 허브 포트 자리는 `visit/dependencies/hub_ports.py`, 꽂기는 `main.py`.
- 도메인(`*/domain`)은 표준 라이브러리만 import 한다. `app` 층은 fastapi·sqlalchemy·redis·`core.config` 를 import 하지 않는다 — 키와 주소는 프로바이더가 인자로 넣는다.
- 매장 범위의 경로는 `get_shop_context` 또는 `require_permission` 으로 `ShopContext` 를 받는다. **예외는 공개 경로 둘뿐이다** — `ShopContext` 를 가드 없이 만드는 곳은 `visit/app/services/public_context.py` 하나이고, `ShopContext` 를 받지 않는 저장소는 `PublicReportRepository` 하나다.
- **잠금 순서: 알림장 쓰기는 방문 쓰기와 같다** — `CustomerDirectoryPort.lock_family`(고객 행) → 방문 행 `FOR UPDATE` → 다시 읽어 판정(`visit_locking.lock_visits`). 링크를 보는 판정(되돌리기·기록 삭제)은 잠근 **뒤에** 링크를 읽는다. 공개 조회와 열람 신호는 잠그지 않는다.
- **로그인 없이 열리는 경로는 목록에 있는 것뿐이다** — `/v1/public/` 경로는 `tests/route_inspection.py` 의 `_PUBLIC_ROUTES`, 프로세스별 전체 목록은 `tests/test_hub_port_binding.py`·`tests/integration/test_route_wiring.py`.
- 공개 응답 스키마는 매장용을 상속하거나 다시 쓰지 않는다. 칸을 하나하나 적는다.
- 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC 를 상속한다. 포트에 메서드를 더하면 스텁에도 더한다.

입력 경계 (넘으면 422 — 500 이 아니다)
- 경로 ID·`hidden_media_ids` 의 원소는 1 ~ `2**63 - 1` · `hidden_media_ids` 는 33개까지(사진 30 + 영상 3), 중복 없음, 이 기록의 미디어만 · `link_days` 는 `7`·`30`·`null`(칸은 필수) · 켬·끔 넷은 엄격한 불리언(`"true"`·`1` 은 422) · 알림장 설정의 다섯 칸은 모두 필수.
- **공개 조회의 토큰은 예외다 — 어떤 입력에도 404 다**(헤더 없음, 빈 값, 42·44글자, 수천 글자, 한글, 공백, `=` 패딩, 다른 키의 서명). 422·500 이 아니다.

환경
- **작업 5 가 새 비밀값 `REPORT_LINK_KEY_B64` 를 더한다.** 없으면 API·인증 프로세스 둘 다 기동하지 않는다. 작업 5 의 '환경' 절차대로 `.env` 에 한 줄을 더하고 개발 스택의 `backend`·`auth` 를 다시 띄운다.
- 작업 2 의 마지막에 개발 DB 에 마이그레이션 0010 을 올린다(`docker compose run --rm backend alembic upgrade head`). 그 전까지 통합 테스트는 테스트 DB(`chagocnote_test`)만 쓴다.
- Redis: 개발 스택은 db 0, 테스트는 db 15 다. 테스트 픽스처가 db 15 만 비운다.

검증 명령 (`infra/`에서)
- 단위: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` — 시작 883 → 끝 1288
- 통합(실제 Postgres·Redis·MinIO): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` — 시작 300 → 끝 404
- 구조 계약: `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken
- 라우트 표: `docker compose run --rm --no-deps auth python scripts/print_routes.py` — 작업 1 전에 파일로 받아 두고 작업 9 뒤에 `diff` 한다. 늘어나는 줄은 일곱이다(설정 둘, 매장용 알림장 셋, 공개 둘)
- 파일 몇 개만: `docker compose run --rm --no-deps backend pytest <경로들> -q -p no:cacheprovider`(통합 표시가 있는 파일은 `--no-deps` 없이)
- **파일을 골라 돌릴 때 `tests/test_hub_port_binding.py` 는 맨 뒤에 두거나 따로 돌린다.** 통합 파일 사이에 두면 뒤쪽 통합 파일이 `fixture 'wired' not found` 로 실패한다(전체 실행에는 없다, 원인 미조사 — 결정 기록 008).
- **시각 의존 테스트 하나:** `tests/integration/test_visit_flow_wiring.py::test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다`는 밤 22시 반 이후(한국 시각) 실패한다. ③부터 있던 것이고 이 계획이 건드리지 않는다.
- 참조 브랜치와 대조(선택, 마지막에): `git diff ref/report-5-1-be -- backend _docs infra CLAUDE.md .env.example` 가 비어 있어야 한다.

## 이 계획에서 새로 정한 것

설계와 다른 것과 새로 정한 것은 결정 기록 008(작업 10)에 적는다. 요약:
- 429 의 오류 코드는 `TOO_MANY_ATTEMPTS` 다(기존 초대 코드 시도 제한과 같게).
- `PUT …/report` 의 `hidden_media_ids` 는 "뺄 것 전부"다. 목록에 없는 것은 앞서 뺐더라도 되살아난다.
- 공개 응답의 캐시·검색 금지 헤더는 200·204 에만 달린다. 보호자가 닿는 것은 웹 서버이고 웹(⑤-2)이 모든 응답에 단다.
- "로그인 없이 열리는 경로"의 목록은 `find_route_violations` 가 아니라 `routes_without_login` + 프로세스별 테스트가 못 박는다.
- 조회와 열람 신호는 같은 통에 센다(분당 60). 410 은 실패로 세지 않는다.
- 기존 `append_media` 를 고친다 — 있던 미디어는 순서만 바뀌고 다른 칸(뺀 표시)은 그대로다.
- 되돌리기가 아닌 전이도 링크를 읽는다(질의 하나, 분기를 두지 않는다).
- `report_sent` 는 `VisitView` 가 아니라 하루 목록·피드의 항목에 둔다.

## 위협 점검표 (설계 7.5 — 행마다 막는 코드와 테스트)

작업별 검토는 계획서와의 일치가 아니라 이 표를 기준으로 한다.

| # | 시나리오 | 막는 코드 | 테스트 |
|---|---|---|---|
| R1 | 토큰을 마구 넣어 본다 | 토큰 128비트 + 서명 128비트(작업 1), 분당 60·실패 10분 20 의 제한(작업 8) | `test_public_report_redis_limiter.py`, 배선 `test_1분에_61번째_요청부터_429_다`·`test_실패가_20번이면_…` |
| R2 | 다른 매장의 방문 ID 로 발급·끊기·미리보기 | `ShopContext` 로 방문을 찾는다 — 404(작업 2·5·6) | `test_다른_매장의_방문의_링크는_없는_것이다`, 배선 `test_다른_매장의_방문은_미리_볼_수_없고_…`, 작업 6 배선의 다른 매장 PUT·DELETE |
| R3 | 끊은 링크·기간 지난 링크를 연다 | `open_report` 의 `is_live`(작업 8) | `test_끊은_링크는_410_이다`·`test_기간이_지난_링크는_410_이다`, 배선 `test_보내고_열고_끊고_다시_보낸다` |
| R4 | 새 링크를 만들면 옛 링크가 되살아난다 | 줄이 다르고 `public_id` 가 다르다(작업 2·6) | `test_끊고_새로_만들면_다른_줄이고_옛_줄은_끊긴_채다`, `test_끊은_뒤_보내면_…` |
| R5 | 기록 저장으로 뺀 사진이 공개된다 | 전체 교체의 `carry_hidden`, `append_media` 의 `replace`(작업 6) | `test_알림장에서_뺀_사진은_기록을_다시_저장해도_빠져_있다`, `test_덧붙여도_알림장에서_뺀_표시는_남고_…`, 배선 `test_알림장에서_뺀_사진은_기록을_고치고_사진을_덧붙여도_빠져_있다` |
| R6 | 공개 응답에 내부 메모·결제 수단·전화번호·보호자 이름이 섞인다 | `ReportView`·공개 스키마에 칸이 없다(작업 5·8) | `test_내부_메모와_결제_수단과_예약_메모와_보호자_정보는_어디에도_없다`, 배선 `test_모든_항목을_켜도_공개하기로_한_것만_나간다` |
| R7 | 설정에서 끈 금액·몸무게가 응답에 남는다 | `describe_report` 가 조립 단계에서 비운다(작업 5), 공개 스키마가 칸을 뺀다(작업 8) | `test_넷_다_꺼도_…`·`test_메뉴와_금액은_따로_켜고_끈다`, `test_끈_항목은_칸이_아예_없다`, 배선 `test_설정에서_끈_항목은_응답에_칸이_없다` |
| R8 | 발급을 동시에 두 번 | `lock_visits` + 부분 유일 색인 `uq_visit_reports_live`(작업 2·6) | 경합 `test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고_링크는_하나다` |
| R9 | 발급과 되돌리기·기록 삭제가 동시에 | 같은 잠금, 잠근 뒤 링크를 읽는다(작업 7) | 경합 `test_보내는_동안_온_되돌리기와_기록_삭제는_기다렸다가_VISIT_REPORT_SENT_로_끝난다`, 단위 `test_알림장을_보냈는지는_잠근_뒤에_읽는다` |
| R10 | 열람 신호가 동시에 여러 번 | `first_viewed_at IS NULL` 조건부 UPDATE(작업 2) | `test_처음_연_시각은_한_번만_적는다`, `test_처음_연_시각을_남기고_다시_열어도_그대로다` , 두 세션 `test_두_세션이_동시에_처음_연_시각을_적어도_먼저_커밋한_것이_남는다`(작업 11) |
| R11 | 닫힌 링크에 열람 신호 | 열람도 `open_report` 를 거친다(작업 8) | `test_끊은_링크와_기간이_지난_링크에는_남기지_않는다` |
| R12 | 카카오톡 미리보기 로봇이 '열람'으로 찍힌다 | 열람 신호는 조회와 다른 경로다 — 브라우저 스크립트가 보낸다(웹 ⑤-2) | 조회만으로는 `first_viewed_at` 이 비어 있다 — 배선 `test_보내고_열고_끊고_다시_보낸다` |
| R13 | 이상한 토큰 | `read_token` 은 예외를 던지지 않는다(작업 1), 헤더는 선택 값으로 받아 직접 판정(작업 8) | `test_이상한_입력은_예외_없이_None_이다`, 라우터 `test_이상한_토큰은_…`, 배선 `test_패딩을_붙이거나_다른_키로_서명한_토큰은_404_다` |
| R14 | `hidden_media_ids` 에 남의 미디어 ID, 중복, 수천 개, 범위 밖 숫자 | 스키마의 `EntityId`·`max_length`(작업 6), 도메인 `check_hidden_ids`(작업 1) | 라우터 422 목록, `test_같은_미디어를_두_번_빼면_…`·`test_뺄_수_있는_미디어는_33개까지다` |
| R15 | 설정에 허용 밖의 기간, 문자열 불리언, 빠진 칸 | `Literal[7, 30] | None`·`StrictBool`·필수 칸(작업 3), DB CHECK(작업 2) | `test_고를_수_없는_기간과_불리언이_아닌_값과_빠진_칸은_422_다`, `test_링크_기간은_7일과_30일만_받는다` |
| R16 | 직원이 알림장 설정을 바꾼다 | `require_permission("shop:update")`(작업 3) | `test_직원은_알림장_설정을_바꾸지_못한다`, 배선 `test_사장이_바꾼_알림장_설정을_직원도_보지만_직원은_바꾸지_못한다` |
| R17 | 위조한 접속 주소 헤더로 횟수 제한을 피한다 | `get_public_client` 가 비밀값이 맞을 때만 헤더를 믿는다, 설정이 비면 늘 불일치(작업 8) | `test_public_client.py`, 배선 `test_실패가_20번이면_맞는_토큰도_429_이고_접속_주소_헤더를_바꿔도_피하지_못한다` |
| R18 | 토큰이 로그에 남는다 | 헤더로 받는다, 로그 코드가 없다(작업 8) | 배선 `test_공개_조회는_토큰을_로그에_남기지_않는다` |
| R19 | 익명화한 고객의 알림장이 계속 열린다 | `clear_customer_memos` 가 `revoke_for_customer` 를 부른다(작업 7) | `test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊고_…`, 배선 `test_고객을_삭제하면_그_고객의_알림장_링크가_끊긴다`·`test_고객을_삭제하면_그_고객의_알림장은_410_이다` |
| R20 | 기간이 지난 링크가 부분 유일 색인에 걸려 새 링크를 못 만든다 | 발급이 `close_expired` 를 먼저 부른다(작업 2·6) | `test_기간이_지난_줄을_닫으면_새로_만들_수_있다`, `test_기간이_지난_뒤_보내면_옛_줄을_닫고_새_링크를_만든다` |
| R21 | 정지·폐업한 매장의 알림장이 열린다 | `open_report` 가 `ShopProfile.open` 을 본다(작업 4·8) | `test_문을_닫았거나_없는_매장의_알림장은_410_이다`, 배선 `test_정지하거나_폐업한_매장의_알림장은_410_이고_풀리면_다시_열린다` |

## Review Focus

설계가 말하거나 함의하지만 작업 1~8 의 테스트가 다루지 않은 것 가운데, 사람이 쓰다 가장 먼저 부딪힐 다섯. 각 줄의 테스트는 **작업 11** 에 있다(참조 구현에서 돌려 통과했고 변이로 판별력을 확인했다).

1. **되돌리는 동안 보내기가 온다(R9 의 반대 방향)** — 사장님이 되돌리기를 누른 직후 직원이 알림장 보내기를 누른다. 보내기는 기다렸다가 409 `VISIT_NOT_COMPLETED` 로 끝나고 링크는 생기지 않는다 → `test_visit_report_locking.py::test_되돌리는_동안_온_보내기는_기다렸다가_VISIT_NOT_COMPLETED_로_끝난다`(두 세션, 결과로 판별).
2. **익명화한 고객의 방문에 다시 보낸다** — 고객을 삭제한 뒤에도 방문은 달력에 남아 있어 [알림장 보내기]를 누를 수 있다. 보내기·끊기·되돌리기·기록 삭제 모두 404 `CUSTOMER_NOT_FOUND` 이고 링크가 생기지 않는다(앱 ⑤-3 이 이 코드를 안내로 바꾼다) → `test_visit_report_wiring.py::test_익명화한_고객의_방문에는_다시_보내지_못한다`.
3. **보호자가 링크를 연 순간 열람 신호가 둘 온다(R10)** — 처음 연 시각은 하나이고 둘 다 204 다 → `test_report_pg_repository.py::test_두_세션이_동시에_처음_연_시각을_적어도_먼저_커밋한_것이_남는다`(판별), `test_public_report_wiring.py::test_열람_신호가_동시에_둘_와도_둘_다_204_이고_시각은_하나다`(상태 코드와 뒤에 온 신호).
4. **영상만 있는 알림장** — 대표는 영상의 포스터이고, `display_url` 은 재생할 원본이고, 내려받는 파일은 `.mp4` 다 → `test_public_report_wiring.py::test_영상만_있는_알림장은_포스터가_대표이고_원본으로_재생한다`.
5. **보낸 뒤 사진을 전부 빼고 메모를 비운다** — 막지 않기로 했다(설계 7.4). 공개 조회는 200 이고 이름과 날짜만 보인다. 500 도 422 도 아니다 → `test_public_report_wiring.py::test_보낸_뒤_전부_빼고_메모를_비워도_공개_조회는_200_이다`.

**여전히 돌려 보지 않은 것**(결정 기록 008 의 "남는 것"): 익명화와 보내기의 경합, 끊기를 동시에 두 번, 게이트웨이(Caddy)를 거친 흐름(작업 9 에서 처음 돌린다), 흐름 스크립트의 판별력(작업 9 에서 처음 확인한다), 실제 AWS S3·실제 브라우저의 저장·실제 Redis 장애.

---

### Task 1: 알림장의 도메인 — 서명 토큰, 링크의 살아 있음, 설정 값, 보내기 규칙, 보낸 방문의 되돌리기 금지

**Files:**
- Modify: `backend/apps/visit/domain/errors.py`
- Modify: `backend/apps/visit/adapter/inbound/api/error_map.py`
- Create: `backend/apps/visit/domain/services/report_token.py`
- Create: `backend/apps/visit/domain/entities/visit_report.py`
- Create: `backend/apps/visit/domain/value_objects/report_settings.py`
- Modify: `backend/apps/visit/domain/entities/visit_record.py`
- Modify: `backend/apps/visit/domain/entities/visit.py`
- Create: `backend/apps/visit/domain/services/report_rules.py`
- Modify: `backend/apps/visit/domain/state/visit_state.py`
- Create: `backend/apps/visit/tests/adapter/test_report_error_map.py`
- Create: `backend/apps/visit/tests/domain/test_report_rules.py`
- Create: `backend/apps/visit/tests/domain/test_report_token.py`
- Create: `backend/apps/visit/tests/domain/test_visit_report.py`
- Modify: `backend/apps/visit/tests/domain/test_visit_state.py`

**Interfaces:**
- Consumes: `visit.domain.entities.visit.Visit`, `visit.domain.entities.visit_record.VisitRecord`·`RecordMedia`, `visit.domain.errors`(기존 오류 모양과 `VisitNoRecordYetError`·`VisitInputError`), `visit.domain.services.visit_record_rules.cover_media_id`, `visit.domain.state.visit_state`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

`visit/domain/errors.py` (모두 `VisitError` 하위, 상태 코드는 `VISIT_ERROR_STATUS` 에 있다)

| 클래스 | code | 상태 |
|---|---|---|
| `ReportNotFoundError` | `REPORT_NOT_FOUND` | 404 |
| `ReportClosedError` | `REPORT_CLOSED` | 410 |
| `ReportEmptyError` | `REPORT_EMPTY` | 422 |
| `VisitNotCompletedError` | `VISIT_NOT_COMPLETED` | 409 |
| `VisitReportSentError` | `VISIT_REPORT_SENT` | 409 |

`visit/domain/services/report_token.py`
```python
TOKEN_LENGTH = 43
def new_public_id() -> bytes
def make_token(public_id: bytes, key: bytes) -> str
def read_token(token: str, key: bytes) -> bytes | None
```

`visit/domain/entities/visit_report.py`
```python
@dataclass(frozen=True)
class VisitReport:
    id: int
    visit_id: int
    public_id: bytes
    expires_at: datetime | None
    revoked_at: datetime | None
    first_viewed_at: datetime | None
    created_by_member_id: int
    created_at: datetime
    def is_live(self, now: datetime) -> bool
```

`visit/domain/value_objects/report_settings.py`
```python
LINK_DAYS = (7, 30)
@dataclass(frozen=True)
class ReportSettings:
    link_days: int | None
    show_menus: bool
    show_shop_info: bool
    show_weight: bool
    show_amount: bool
DEFAULT_REPORT_SETTINGS = ReportSettings(link_days=30, show_menus=True, show_shop_info=True, show_weight=False, show_amount=False)
```

`visit/domain/entities/visit_record.py` — `RecordMedia(media_id, kind, phase, sort_order, hidden: bool = False)`

`visit/domain/entities/visit.py` — `Visit(..., status_changed_by_member_id, has_live_report: bool = False)`

`visit/domain/services/report_rules.py`
```python
MAX_HIDDEN = 33
def expires_at_for(now: datetime, link_days: int | None) -> datetime | None
def check_settings(settings: ReportSettings) -> None                      # VisitInputError
def check_hidden_ids(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None   # VisitInputError
def hide(record: VisitRecord, hidden_ids: tuple[int, ...]) -> tuple[RecordMedia, ...]
def carry_hidden(previous: tuple[RecordMedia, ...], media: tuple[RecordMedia, ...]) -> tuple[RecordMedia, ...]
def visible_media(record: VisitRecord) -> tuple[RecordMedia, ...]
def report_cover_media_id(record: VisitRecord) -> int | None
def check_sendable(visit: Visit, record: VisitRecord | None, hidden_ids: tuple[int, ...]) -> None
    # VisitNotCompletedError → VisitNoRecordYetError → check_hidden_ids 순서. 빈 알림장은 보지 않는다
def check_not_empty(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None    # ReportEmptyError
```

`visit/domain/state/visit_state.py` — `CompletedState.revert(self, visit: Visit, request: TransitionRequest) -> StatusChange`. `visit.has_live_report` 면 `VisitReportSentError("알림장을 보낸 방문입니다. 링크를 먼저 끊어 주세요.")`.

뒤 작업이 알아 둘 동작
- `check_not_empty` 는 기록에 저장된 `hidden` 이 아니라 **인자 `hidden_ids`** 로 판단한다(저장 전에 부르므로).
- `hide` 는 표시를 통째로 다시 매긴다 — `hidden_ids` 에 없는 미디어는 앞서 뺐더라도 되살아난다(PUT 의 멱등성).
- `visible_media` 는 스스로 정렬한다. 저장소(`visit_record_pg_repository`)가 주는 순서는 전 → 후이므로 공개 응답은 저장소 순서를 그대로 쓰면 안 되고 이 함수를 거쳐야 한다.
- `check_settings` 는 `link_days` 만 본다. 켬·끔이 불리언인지는 스키마(`StrictBool`)의 일이다.

순수 도메인이다(표준 라이브러리만). 설계 4절·5절·6.1·6.2·7.4. 토큰은 저장하지 않고 `public_id` 와 서버 키로 그때마다 계산한다. `read_token` 은 어떤 입력에도 예외를 던지지 않는다(R13). `RecordMedia.hidden` 과 `Visit.has_live_report` 는 맨 끝 칸이고 기본값이 있어 기존 생성 코드가 그대로 돈다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_report_error_map.py`:

```python
import pytest

from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
from visit.domain.errors import (
    ReportClosedError,
    ReportEmptyError,
    ReportNotFoundError,
    VisitNotCompletedError,
    VisitReportSentError,
)


@pytest.mark.parametrize(("error", "code", "status"), [
    (ReportNotFoundError, "REPORT_NOT_FOUND", 404),
    (ReportClosedError, "REPORT_CLOSED", 410),
    (ReportEmptyError, "REPORT_EMPTY", 422),
    (VisitNotCompletedError, "VISIT_NOT_COMPLETED", 409),
    (VisitReportSentError, "VISIT_REPORT_SENT", 409),
])
def test_알림장_오류의_코드와_상태(error, code, status):
    assert error.code == code
    assert VISIT_ERROR_STATUS[error] == status
```

`backend/apps/visit/tests/domain/test_report_rules.py`:

```python
from datetime import timedelta

import pytest

from visit.domain.entities.visit_record import RecordMedia
from visit.domain.errors import ReportEmptyError, VisitInputError, VisitNoRecordYetError, VisitNotCompletedError
from visit.domain.services.report_rules import (
    MAX_HIDDEN,
    carry_hidden,
    check_hidden_ids,
    check_not_empty,
    check_sendable,
    check_settings,
    expires_at_for,
    hide,
    report_cover_media_id,
    visible_media,
)
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, LINK_DAYS, ReportSettings
from visit.tests.helpers.builders import but, kst, record, visit

NOW = kst(9, 28, 15)


def _m(media_id, kind="photo", phase="after", order=0, hidden=False):
    return RecordMedia(media_id=media_id, kind=kind, phase=phase, sort_order=order, hidden=hidden)


def _record(*media, care_note=None):
    return but(record(1, care_note=care_note), media=tuple(media))


# 저장소가 주는 순서(전 → 후, 그 안에서 sort_order)대로 둔다.
MIXED = (_m(1, phase="before", order=0), _m(2, "video", "before", 1), _m(3, order=0), _m(4, order=1))


def test_처음_설정은_30일이고_메뉴와_매장_정보만_보인다():
    assert DEFAULT_REPORT_SETTINGS == ReportSettings(
        link_days=30, show_menus=True, show_shop_info=True, show_weight=False, show_amount=False)
    assert LINK_DAYS == (7, 30)


@pytest.mark.parametrize("days", [7, 30])
def test_링크는_보낸_때부터_설정한_날수만큼_열린다(days):
    assert expires_at_for(NOW, days) == NOW + timedelta(days=days)


def test_기간이_없으면_무기한이다():
    assert expires_at_for(NOW, None) is None


@pytest.mark.parametrize("days", [7, 30, None])
def test_기간은_7일_30일_무기한_가운데_하나다(days):
    check_settings(but(DEFAULT_REPORT_SETTINGS, link_days=days))


@pytest.mark.parametrize("days", [0, 1, 8, 31, -7, 365])
def test_그_밖의_기간은_VALIDATION_ERROR_다(days):
    with pytest.raises(VisitInputError):
        check_settings(but(DEFAULT_REPORT_SETTINGS, link_days=days))


@pytest.mark.parametrize("hidden_ids", [(), (3,), (1, 2, 3, 4)])
def test_이_기록의_미디어는_뺄_수_있다(hidden_ids):
    check_hidden_ids(_record(*MIXED), hidden_ids)


def test_같은_미디어를_두_번_빼면_VALIDATION_ERROR_다():
    with pytest.raises(VisitInputError):
        check_hidden_ids(_record(*MIXED), (3, 3))


def test_이_기록의_것이_아닌_미디어를_빼면_VALIDATION_ERROR_다():
    with pytest.raises(VisitInputError):
        check_hidden_ids(_record(*MIXED), (3, 99))
    with pytest.raises(VisitInputError):
        check_hidden_ids(_record(), (3,))


def test_뺄_수_있는_미디어는_33개까지다():
    many = _record(*(_m(i, order=i) for i in range(1, MAX_HIDDEN + 2)))   # 미디어 34개
    assert MAX_HIDDEN == 33
    check_hidden_ids(many, tuple(range(1, MAX_HIDDEN + 1)))
    with pytest.raises(VisitInputError):
        check_hidden_ids(many, tuple(range(1, MAX_HIDDEN + 2)))


def test_빼면_고른_것만_hidden_이고_순서와_다른_값은_그대로다():
    assert hide(_record(*MIXED), (2, 3)) == (
        _m(1, phase="before", order=0), _m(2, "video", "before", 1, hidden=True), _m(3, order=0, hidden=True),
        _m(4, order=1))


def test_다시_빼면_앞서_뺀_것은_되살아난다():
    before = _record(_m(1, hidden=True), _m(2, order=1))
    assert hide(before, (2,)) == (_m(1), _m(2, order=1, hidden=True))
    assert hide(before, ()) == (_m(1), _m(2, order=1))


def test_기록을_다시_저장하면_뺀_표시를_미디어_ID_로_옮긴다():
    previous = (_m(1, hidden=True), _m(2, order=1), _m(3, order=2, hidden=True))
    # 3은 사라졌고, 1은 전 사진 칸으로 옮겼고, 9는 새로 붙었다.
    media = (_m(9, "video", "after", 0), _m(2, order=1), _m(1, phase="before", order=0))

    assert carry_hidden(previous, media) == (
        _m(9, "video", "after", 0), _m(2, order=1), _m(1, phase="before", order=0, hidden=True))


def test_앞선_기록이_없으면_모두_보인다():
    assert carry_hidden((), (_m(1), _m(2, order=1))) == (_m(1), _m(2, order=1))


def test_보이는_미디어는_후_먼저_전_나중이고_그_안에서_순서대로다():
    shuffled = _record(_m(2, "video", "before", 1), _m(4, order=1), _m(1, phase="before", order=0), _m(3, order=0))
    assert [m.media_id for m in visible_media(shuffled)] == [3, 4, 1, 2]


def test_뺀_미디어는_보이지_않는다():
    hidden = _record(*hide(_record(*MIXED), (3, 1)))
    assert visible_media(hidden) == (_m(4, order=1), _m(2, "video", "before", 1))


def test_대표는_빼지_않은_것_가운데_후_사진_전_사진_영상_순이다():
    assert report_cover_media_id(_record(*MIXED)) == 3
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (3,)))) == 4
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (3, 4)))) == 1
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (3, 4, 1)))) == 2


def test_전부_빼면_대표가_없다():
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (1, 2, 3, 4)))) is None
    assert report_cover_media_id(_record()) is None


def test_완료한_방문의_기록은_보낼_수_있다():
    check_sendable(visit(status="completed"), _record(*MIXED), (3,))


@pytest.mark.parametrize("status", ["reserved", "in_progress", "canceled", "no_show"])
def test_완료가_아닌_방문은_VISIT_NOT_COMPLETED(status):
    with pytest.raises(VisitNotCompletedError):
        check_sendable(visit(status=status), _record(*MIXED), ())


def test_완료가_아니면_기록이_없어도_VISIT_NOT_COMPLETED_가_먼저다():
    with pytest.raises(VisitNotCompletedError):
        check_sendable(visit(status="in_progress"), None, ())


def test_기록이_없는_완료_방문은_VISIT_NO_RECORD_YET():
    with pytest.raises(VisitNoRecordYetError):
        check_sendable(visit(status="completed"), None, ())


def test_보낼_때도_뺄_미디어를_검사한다():
    with pytest.raises(VisitInputError):
        check_sendable(visit(status="completed"), _record(*MIXED), (99,))


def test_보내기_검사는_빈_알림장을_보지_않는다():
    """빈 알림장은 링크를 새로 만들 때만 막는다 — 보낸 뒤 사진을 전부 빼는 것은 된다(설계 7.4)."""
    check_sendable(visit(status="completed"), _record(*MIXED), (1, 2, 3, 4))
    check_sendable(visit(status="completed"), _record(), ())


@pytest.mark.parametrize("care_note", [None, "", "   ", "\n\t "])
def test_보이는_미디어도_메모도_없으면_REPORT_EMPTY(care_note):
    with pytest.raises(ReportEmptyError):
        check_not_empty(_record(care_note=care_note), ())
    with pytest.raises(ReportEmptyError):
        check_not_empty(_record(*MIXED, care_note=care_note), (1, 2, 3, 4))


def test_메모만_있어도_보낼_수_있다():
    check_not_empty(_record(care_note="발톱을 짧게 다듬었어요"), ())
    check_not_empty(_record(*MIXED, care_note="발톱을 짧게 다듬었어요"), (1, 2, 3, 4))


@pytest.mark.parametrize("care_note", [None, "", "   "])
def test_미디어가_하나라도_남으면_보낼_수_있다(care_note):
    check_not_empty(_record(*MIXED, care_note=care_note), (1, 2, 3))


def test_빈_알림장은_이번에_보낸_목록으로_판단한다():
    """앞서 뺀 표시(hidden)가 아니라 이번 요청의 hidden_ids 가 기준이다 — 저장하기 전에 검사한다."""
    all_hidden = _record(_m(1, hidden=True))
    check_not_empty(all_hidden, ())
    with pytest.raises(ReportEmptyError):
        check_not_empty(_record(_m(1)), (1,))
```

`backend/apps/visit/tests/domain/test_report_token.py`:

```python
import base64
import string

import pytest

from visit.domain.services.report_token import TOKEN_LENGTH, make_token, new_public_id, read_token

KEY = b"k" * 32
OTHER_KEY = b"o" * 32
PUBLIC_ID = bytes(range(16))
ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-_"   # base64url 의 값 순서


def test_만들고_읽으면_같은_public_id_다():
    assert read_token(make_token(PUBLIC_ID, KEY), KEY) == PUBLIC_ID


def test_토큰은_43글자이고_주소에_그대로_쓸_수_있는_글자뿐이다():
    token = make_token(new_public_id(), KEY)
    assert TOKEN_LENGTH == 43
    assert len(token) == TOKEN_LENGTH
    assert set(token) <= set(ALPHABET)


def test_같은_public_id_와_키면_늘_같은_토큰이다():
    assert make_token(PUBLIC_ID, KEY) == make_token(PUBLIC_ID, KEY)


def test_다른_키로_만든_토큰은_읽지_않는다():
    assert read_token(make_token(PUBLIC_ID, OTHER_KEY), KEY) is None


@pytest.mark.parametrize("position", range(TOKEN_LENGTH))
def test_어느_자리든_한_글자를_바꾸면_읽지_않는다(position):
    token = make_token(PUBLIC_ID, KEY)
    for changed in ALPHABET:
        if changed != token[position]:
            assert read_token(token[:position] + changed + token[position + 1:], KEY) is None


def test_마지막_글자를_같은_바이트로_풀리는_다른_글자로_바꿔도_읽지_않는다():
    """43번째 글자는 6비트 가운데 앞 4비트만 쓴다 — 뒤 2비트만 다른 글자 셋은 같은 32바이트로 풀린다."""
    token = make_token(PUBLIC_ID, KEY)
    first = ALPHABET.index(token[-1]) // 4 * 4
    twins = [token[:-1] + ALPHABET[i] for i in range(first, first + 4) if ALPHABET[i] != token[-1]]

    assert len(twins) == 3
    for twin in twins:
        assert base64.urlsafe_b64decode(twin + "=") == base64.urlsafe_b64decode(token + "=")
        assert read_token(twin, KEY) is None


VALID = make_token(PUBLIC_ID, KEY)

STRANGE = [
    "",
    VALID[:-1],                 # 42글자
    VALID + "A",                # 44글자
    "A" * 5000,
    "가" * 43,
    "가" + VALID[1:],
    VALID + "가",                # 앞 43글자는 멀쩡하다
    " " + VALID[1:],
    VALID[:-1] + " ",
    VALID[:-1] + "\n",
    VALID + "\n",
    VALID[:20] + "\n" + VALID[21:],
    VALID[:-1] + "=",           # 패딩
    VALID + "=",
    "+" + VALID[1:],            # 주소용이 아닌 base64 글자
    "/" + VALID[1:],
    "١" * 43,                   # 아라비아 숫자(유니코드 숫자)
    None,
    43,
    VALID.encode(),
    bytearray(VALID.encode()),
    [VALID],
]


@pytest.mark.parametrize("token", STRANGE)
def test_이상한_입력은_예외_없이_None_이다(token):
    assert read_token(token, KEY) is None


def test_public_id_는_16바이트이고_만들_때마다_다르다():
    first, second = new_public_id(), new_public_id()
    assert (len(first), len(second)) == (16, 16)
    assert first != second
```

`backend/apps/visit/tests/domain/test_visit_report.py`:

```python
from datetime import timedelta

import pytest

from visit.domain.entities.visit_report import VisitReport
from visit.tests.helpers.builders import kst

NOW = kst(9, 28, 15)
SECOND = timedelta(seconds=1)


def _report(expires_at=None, revoked_at=None):
    return VisitReport(id=1, visit_id=1, public_id=b"p" * 16, expires_at=expires_at, revoked_at=revoked_at,
                       first_viewed_at=None, created_by_member_id=11, created_at=kst(9, 1))


def test_기간이_남은_링크는_살아_있다():
    assert _report(expires_at=NOW + SECOND).is_live(NOW)


def test_기간이_끝나는_바로_그_시각에는_닫혀_있다():
    assert not _report(expires_at=NOW).is_live(NOW)


def test_기간이_지난_링크는_닫혀_있다():
    assert not _report(expires_at=NOW - SECOND).is_live(NOW)


def test_무기한_링크는_살아_있다():
    assert _report(expires_at=None).is_live(NOW)


@pytest.mark.parametrize("expires_at", [None, NOW + SECOND])
def test_끊은_링크는_기간이_남았어도_닫혀_있다(expires_at):
    assert not _report(expires_at=expires_at, revoked_at=NOW - SECOND).is_live(NOW)
```

`backend/apps/visit/tests/domain/test_visit_state.py`:

```diff
@@ -1,6 +1,11 @@
 import pytest
 
-from visit.domain.errors import VisitInputError, VisitNotYetError, VisitStateConflictError
+from visit.domain.errors import (
+    VisitInputError,
+    VisitNotYetError,
+    VisitReportSentError,
+    VisitStateConflictError,
+)
 from visit.domain.state.visit_state import StatusChange, transition
 from visit.tests.helpers.builders import TZ, kst, visit
 
@@ -119,3 +124,12 @@ def test_되돌리기만_반려동물을_가족_확인에_넘긴다():
     visits = [visit(id=1, pet_id=102), visit(id=2, pet_id=101), visit(id=3, pet_id=None)]
     assert pets_to_confirm("revert", visits) == (101, 102)
     assert all(pets_to_confirm(action, visits) == () for action in ("start", "complete", "cancel", "no_show"))
+
+
+def test_알림장을_보내지_않은_완료_방문은_되돌린다():
+    assert _apply("completed", "revert", has_live_report=False) == StatusChange("reserved")
+
+
+def test_알림장을_보낸_완료_방문은_되돌릴_수_없다():
+    with pytest.raises(VisitReportSentError):
+        _apply("completed", "revert", has_live_report=True)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

명령(`infra/`):
`docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_report_token.py apps/visit/tests/domain/test_visit_report.py apps/visit/tests/domain/test_report_rules.py apps/visit/tests/domain/test_visit_state.py apps/visit/tests/adapter/test_report_error_map.py -q -p no:cacheprovider`

결과: `5 errors in 0.07s` — 다섯 파일 모두 수집 오류. 예:
`ImportError: cannot import name 'VisitReportSentError' from 'visit.domain.errors'`,
`ImportError: cannot import name 'ReportEmptyError' from 'visit.domain.errors'`.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/errors.py`:

```diff
@@ -98,3 +98,33 @@ class RecordSalesForbiddenError(VisitError):
     """돈 칸(총액·항목·결제 수단)을 적는데 sales:write 가 없다. 403."""
 
     code = "PERMISSION_DENIED"
+
+
+class ReportNotFoundError(VisitError):
+    """살아 있는 알림장 링크가 없다 — 끊을 링크가 없거나, 토큰이 틀렸거나, 그런 링크가 없다. 404."""
+
+    code = "REPORT_NOT_FOUND"
+
+
+class ReportClosedError(VisitError):
+    """끊었거나 기간이 지난 링크, 또는 정지·폐업한 매장의 링크다. 410."""
+
+    code = "REPORT_CLOSED"
+
+
+class ReportEmptyError(VisitError):
+    """보여 줄 사진·영상도 케어 메모도 없다. 링크를 새로 만들 때만 본다. 422."""
+
+    code = "REPORT_EMPTY"
+
+
+class VisitNotCompletedError(VisitError):
+    """알림장은 완료한 방문에서만 보낸다. 409."""
+
+    code = "VISIT_NOT_COMPLETED"
+
+
+class VisitReportSentError(VisitError):
+    """살아 있는 알림장 링크가 있는 방문은 되돌리거나 기록을 지울 수 없다 — 링크를 먼저 끊는다. 409."""
+
+    code = "VISIT_REPORT_SENT"
```

`backend/apps/visit/adapter/inbound/api/error_map.py`:

```diff
@@ -9,13 +9,18 @@ from visit.domain.errors import (
     RecordSalesForbiddenError,
     RecordVersionConflictError,
     RecordWeightWithoutPetError,
+    ReportClosedError,
+    ReportEmptyError,
+    ReportNotFoundError,
     VisitCrossesMidnightError,
     VisitDuplicateError,
     VisitGroupMismatchError,
     VisitInputError,
     VisitNoRecordYetError,
+    VisitNotCompletedError,
     VisitNotFoundError,
     VisitNotYetError,
+    VisitReportSentError,
     VisitStateConflictError,
 )
 
@@ -37,4 +42,9 @@ VISIT_ERROR_STATUS: dict[type[Exception], int] = {
     RecordWeightWithoutPetError: 422,
     RecordItemDuplicateError: 422,
     RecordMediaLimitError: 422,
+    ReportNotFoundError: 404,
+    ReportClosedError: 410,
+    ReportEmptyError: 422,
+    VisitNotCompletedError: 409,
+    VisitReportSentError: 409,
 }
```

`backend/apps/visit/domain/services/report_token.py`:

```python
"""알림장 링크의 토큰 — 만들기와 읽기(설계 5절). 키는 인자로 받는다.

    token = base64url( public_id(16) ‖ HMAC-SHA256(key, public_id)[:16] )   # 43글자, 패딩 없음

DB 에는 public_id 만 있고 토큰은 그때마다 다시 계산한다. 서명이 맞지 않는 토큰은 DB 를 읽기 전에 떨어진다.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

TOKEN_LENGTH = 43
_PUBLIC_ID_BYTES = 16
_SIGNATURE_BYTES = 16
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{%d}" % TOKEN_LENGTH)


def new_public_id() -> bytes:
    return secrets.token_bytes(_PUBLIC_ID_BYTES)


def make_token(public_id: bytes, key: bytes) -> str:
    return _encode(public_id + _sign(public_id, key))


def read_token(token: str, key: bytes) -> bytes | None:
    """토큰이 가리키는 public_id. 우리가 만든 토큰이 아니면 None — 어떤 입력에도 예외를 던지지 않는다."""
    if not isinstance(token, str) or _TOKEN_PATTERN.fullmatch(token) is None:
        return None
    raw = base64.urlsafe_b64decode(token + "=")
    # 마지막 글자는 뒤 2비트가 버려진다 — 같은 바이트로 풀리는 다른 글자열을 받지 않는다.
    if _encode(raw) != token:
        return None
    public_id, signature = raw[:_PUBLIC_ID_BYTES], raw[_PUBLIC_ID_BYTES:]
    if not hmac.compare_digest(signature, _sign(public_id, key)):
        return None
    return public_id


def _sign(public_id: bytes, key: bytes) -> bytes:
    return hmac.new(key, public_id, hashlib.sha256).digest()[:_SIGNATURE_BYTES]


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
```

`backend/apps/visit/domain/entities/visit_report.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VisitReport:
    """알림장 링크 하나(설계 4.1). 방문의 기록을 비추는 창이고 내용을 갖지 않는다.

    토큰은 저장하지 않는다 — public_id 와 서버 키로 그때마다 계산한다(domain/services/report_token.py).
    """

    id: int
    visit_id: int
    public_id: bytes
    expires_at: datetime | None       # None 이면 무기한
    revoked_at: datetime | None       # 끊은 시각
    first_viewed_at: datetime | None  # 보호자가 처음 연 시각
    created_by_member_id: int
    created_at: datetime              # 보낸 시각

    def is_live(self, now: datetime) -> bool:
        """끊지 않았고 기간이 지나지 않았다. 기간이 끝나는 바로 그 시각에는 닫힌 것이다."""
        return self.revoked_at is None and (self.expires_at is None or self.expires_at > now)
```

`backend/apps/visit/domain/value_objects/report_settings.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

LINK_DAYS = (7, 30)   # 고를 수 있는 링크 기간(일). 이 밖에는 무기한(None)뿐이다


@dataclass(frozen=True)
class ReportSettings:
    """매장의 알림장 설정 — 링크 기간과 보호자에게 함께 보여 줄 항목(설계 4.3)."""

    link_days: int | None     # None 이면 무기한
    show_menus: bool
    show_shop_info: bool
    show_weight: bool
    show_amount: bool


DEFAULT_REPORT_SETTINGS = ReportSettings(
    link_days=30, show_menus=True, show_shop_info=True, show_weight=False, show_amount=False,
)
```

`backend/apps/visit/domain/entities/visit_record.py`:

```diff
@@ -26,6 +26,7 @@ class RecordMedia:
     kind: str       # photo · video
     phase: str      # before · after
     sort_order: int
+    hidden: bool = False   # ⑤ 알림장에서 뺀 사진
 
 
 @dataclass(frozen=True)
```

`backend/apps/visit/domain/entities/visit.py`:

```diff
@@ -35,6 +35,8 @@ class Visit:
     menu_ids: tuple[int, ...]
     created_by_member_id: int
     status_changed_by_member_id: int | None
+    # 저장하는 값이 아니다 — 방문을 쓰는 유스케이스가 잠근 뒤 살아 있는 알림장 링크를 읽어 채운다.
+    has_live_report: bool = False
 
     @property
     def ends_at(self) -> datetime:
```

`backend/apps/visit/domain/services/report_rules.py`:

```python
"""알림장의 규칙 — 링크 기간, 뺄 사진, 보호자에게 보이는 미디어와 대표, 보낼 수 있는가(설계 4·6절).

판단은 잠근 뒤 다시 읽은 방문과 기록으로 한다.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from visit.domain.entities.visit import COMPLETED, Visit
from visit.domain.entities.visit_record import AFTER, BEFORE, RecordMedia, VisitRecord
from visit.domain.errors import (
    ReportEmptyError,
    VisitInputError,
    VisitNoRecordYetError,
    VisitNotCompletedError,
)
from visit.domain.services.visit_record_rules import cover_media_id
from visit.domain.value_objects.report_settings import LINK_DAYS, ReportSettings

MAX_HIDDEN = 33   # 방문당 사진 30 + 영상 3


def expires_at_for(now: datetime, link_days: int | None) -> datetime | None:
    return now + timedelta(days=link_days) if link_days is not None else None


def check_settings(settings: ReportSettings) -> None:
    if settings.link_days is not None and settings.link_days not in LINK_DAYS:
        raise VisitInputError("링크 기간은 7일, 30일, 계속 가운데 하나여야 합니다.")


def check_hidden_ids(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None:
    if len(hidden_ids) > MAX_HIDDEN or len(set(hidden_ids)) != len(hidden_ids):
        raise VisitInputError("뺄 사진·영상은 겹치지 않게 33개까지 고를 수 있습니다.")
    if not set(hidden_ids) <= {m.media_id for m in record.media}:
        raise VisitInputError("이 기록의 사진·영상만 뺄 수 있습니다.")


def hide(record: VisitRecord, hidden_ids: tuple[int, ...]) -> tuple[RecordMedia, ...]:
    """기록의 미디어 전부에 뺀 표시를 다시 매긴다 — 고른 것만 빠지고 나머지는 되살아난다."""
    return tuple(replace(m, hidden=m.media_id in hidden_ids) for m in record.media)


def carry_hidden(previous: tuple[RecordMedia, ...], media: tuple[RecordMedia, ...]) -> tuple[RecordMedia, ...]:
    """기록을 다시 저장할 때 앞선 뺀 표시를 미디어 ID 로 옮긴다. 새로 붙은 미디어는 보인다."""
    hidden = {m.media_id for m in previous if m.hidden}
    return tuple(replace(m, hidden=m.media_id in hidden) for m in media)


def visible_media(record: VisitRecord) -> tuple[RecordMedia, ...]:
    """보호자에게 보이는 미디어 — 빼지 않은 것. 후 → 전, 그 안에서 sort_order."""
    shown = (m for m in record.media if not m.hidden)
    return tuple(sorted(shown, key=lambda m: ({AFTER: 0, BEFORE: 1}[m.phase], m.sort_order)))


def report_cover_media_id(record: VisitRecord) -> int | None:
    return cover_media_id(visible_media(record))


def check_sendable(visit: Visit, record: VisitRecord | None, hidden_ids: tuple[int, ...]) -> None:
    if visit.status != COMPLETED:
        raise VisitNotCompletedError("완료한 방문에서만 알림장을 보낼 수 있습니다.")
    if record is None:
        raise VisitNoRecordYetError("기록을 먼저 남겨 주세요.")
    check_hidden_ids(record, hidden_ids)


def check_not_empty(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None:
    """링크를 새로 만들 때만 본다 — 보낸 뒤 사진을 전부 빼거나 메모를 비우는 것은 막지 않는다."""
    has_media = any(m.media_id not in hidden_ids for m in record.media)
    has_note = bool(record.care_note and record.care_note.strip())
    if not has_media and not has_note:
        raise ReportEmptyError("보낼 사진·영상이나 케어 메모가 없습니다.")
```

`backend/apps/visit/domain/state/visit_state.py`:

```diff
@@ -22,7 +22,12 @@ from visit.domain.entities.visit import (
     RESERVED,
     Visit,
 )
-from visit.domain.errors import VisitInputError, VisitNotYetError, VisitStateConflictError
+from visit.domain.errors import (
+    VisitInputError,
+    VisitNotYetError,
+    VisitReportSentError,
+    VisitStateConflictError,
+)
 from visit.domain.services.visit_schedule import local_date
 
 ACTIONS = frozenset({"start", "complete", "cancel", "no_show", "revert"})
@@ -67,7 +72,7 @@ class VisitState(ABC):
         raise self._refuse("노쇼 처리")
 
     def revert(self, visit: Visit, request: TransitionRequest) -> StatusChange:
-        # 알림장을 보낸 뒤에는 되돌릴 수 없다는 규칙이 ⑤에서 더해진다.
+        # 알림장을 보낸 완료 방문은 되돌릴 수 없다 — 그 규칙은 CompletedState 에 있다.
         return StatusChange(status=RESERVED)
 
     def _refuse(self, action: str) -> VisitStateConflictError:
@@ -112,6 +117,11 @@ class InProgressState(VisitState):
 class CompletedState(VisitState):
     status = COMPLETED
 
+    def revert(self, visit: Visit, request: TransitionRequest) -> StatusChange:
+        if visit.has_live_report:
+            raise VisitReportSentError("알림장을 보낸 방문입니다. 링크를 먼저 끊어 주세요.")
+        return super().revert(visit, request)
+
 
 class CanceledState(VisitState):
     status = CANCELED
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 테스트 다섯 파일 | 169 passed (test_visit_state.py 의 기존 테스트 40개 포함 — 새로 더한 것은 129개) |
| 단위 전체 | 1012 passed, 300 deselected (시작 883 → +129) |
| 통합 전체 | 300 passed, 1012 deselected (시작 300, 변화 없음) |
| 구조 계약 | 6 kept, 0 broken |

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `report_token.read_token` 의 `if not hmac.compare_digest(...)` → `if not True:` → 44 failed. `test_다른_키로_만든_토큰은_읽지_않는다`, `test_어느_자리든_한_글자를_바꾸면_읽지_않는다[0]`~`[42]`
- `if _encode(raw) != token:` → `if False:` → `test_마지막_글자를_같은_바이트로_풀리는_다른_글자로_바꿔도_읽지_않는다`, `test_어느_자리든_한_글자를_바꾸면_읽지_않는다[42]`
- `VisitReport.is_live` 의 `self.expires_at > now` → `>=` → `test_기간이_끝나는_바로_그_시각에는_닫혀_있다`
- `carry_hidden` 이 `hidden=False` 만 → `test_기록을_다시_저장하면_뺀_표시를_미디어_ID_로_옮긴다`
- `CompletedState.revert` 의 `if visit.has_live_report:` → `if False:` → `test_알림장을_보낸_완료_방문은_되돌릴_수_없다`
- `check_not_empty` 의 `bool(record.care_note and record.care_note.strip())` → `bool(record.care_note)` → `test_보이는_미디어도_메모도_없으면_REPORT_EMPTY[   ]`, `[\n\t ]`
- `visible_media` 가 뺀 것도 준다 → `test_뺀_미디어는_보이지_않는다`, `test_대표는_빼지_않은_것_가운데_후_사진_전_사진_영상_순이다`, `test_전부_빼면_대표가_없다`
- `visible_media` 정렬을 전 → 후로 → `test_보이는_미디어는_후_먼저_전_나중이고_그_안에서_순서대로다`, `test_뺀_미디어는_보이지_않는다`
- `_TOKEN_PATTERN.fullmatch` → `match` → **처음에는 살아남았다(70 passed).** 경우 `VALID + "가"` 를 더한 뒤 `test_이상한_입력은_예외_없이_None_이다[…가]` 가 실패(ValueError)
- `isinstance(token, str)` 검사 제거 → `test_이상한_입력은_예외_없이_None_이다` 의 `None`·`43`·바이트·bytearray·리스트 다섯
- `is_live` 가 `revoked_at` 을 안 본다 → `test_끊은_링크는_기간이_남았어도_닫혀_있다[None]`, `[expires_at1]`
- `check_sendable` 의 완료 검사 → `if False:` → `test_완료가_아닌_방문은_VISIT_NOT_COMPLETED[reserved·in_progress·canceled·no_show]`, `test_완료가_아니면_기록이_없어도_VISIT_NOT_COMPLETED_가_먼저다`
- `check_not_empty` 가 `hidden_ids` 를 안 본다 → `test_보이는_미디어도_메모도_없으면_REPORT_EMPTY` 넷, `test_빈_알림장은_이번에_보낸_목록으로_판단한다`
- `hide` 가 앞선 hidden 을 남긴다(`m.hidden or …`) → `test_다시_빼면_앞서_뺀_것은_되살아난다`
- `check_hidden_ids` 의 중복 검사 제거 → `test_같은_미디어를_두_번_빼면_VALIDATION_ERROR_다`
- `check_hidden_ids` 의 개수 검사 제거 → `test_뺄_수_있는_미디어는_33개까지다`
- 서명 키를 `b''` 로 고정 → `test_다른_키로_만든_토큰은_읽지_않는다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 알림장 도메인 — 서명 토큰, 링크의 살아 있음, 설정 값, 보내기 규칙, 보낸 방문의 되돌리기 금지

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 알림장의 표와 저장소 — `visit_reports`(0010), 뺀 사진 칸, 매장 설정 칸, 공개 조회용 저장소

**Files:**
- Create: `backend/alembic/versions/0010_visit_reports.py`
- Modify: `backend/apps/visit/adapter/outbound/orm/visit_orm.py`
- Create: `backend/apps/visit/app/ports/output/report_repository.py`
- Create: `backend/apps/visit/app/dtos/report_target_dto.py`
- Create: `backend/apps/visit/app/ports/output/public_report_repository.py`
- Modify: `backend/apps/visit/app/ports/output/visit_record_repository.py`
- Create: `backend/apps/visit/adapter/outbound/mappers/visit_report_mapper.py`
- Modify: `backend/apps/visit/adapter/outbound/mappers/visit_record_mapper.py`
- Create: `backend/apps/visit/adapter/outbound/pg/report_pg_repository.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`
- Modify: `backend/apps/visit/dependencies/visit_wiring.py`
- Create: `backend/apps/visit/tests/adapter/test_report_pg_repository.py`
- Modify: `backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Create: `backend/apps/visit/tests/test_fake_reports.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Create: `backend/tests/integration/test_visit_report_schema.py`

**Interfaces:**
- Consumes: 작업 1 의 `VisitReport`·`RecordMedia.hidden`; 마이그레이션 0009(`down_revision`); `visit.adapter.outbound.orm.visit_orm`; 기존 `VisitPgRepository` 의 매퍼.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

`visit/app/ports/output/report_repository.py`
```python
class ReportRepository(ABC):
    async def get_live(self, ctx: ShopContext, visit_id: int, now: datetime) -> VisitReport | None
    async def live_visit_ids(self, ctx: ShopContext, visit_ids: list[int], now: datetime) -> set[int]
    async def close_expired(self, ctx: ShopContext, visit_id: int, now: datetime) -> None
    async def create(self, ctx: ShopContext, visit_id: int, public_id: bytes,
                     expires_at: datetime | None, now: datetime) -> VisitReport
    async def revoke(self, ctx: ShopContext, visit_id: int, now: datetime) -> bool
    async def revoke_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None
```

`visit/app/dtos/report_target_dto.py`
```python
@dataclass(frozen=True)
class ReportTarget:
    report: VisitReport
    shop_id: int
    visit: Visit
```

`visit/app/ports/output/public_report_repository.py`
```python
class PublicReportRepository(ABC):
    async def find(self, public_id: bytes) -> ReportTarget | None
    async def mark_viewed(self, report_id: int, now: datetime) -> None
```

`visit/app/ports/output/visit_record_repository.py`
```python
async def set_hidden(self, ctx: ShopContext, visit_id: int, hidden_ids: tuple[int, ...]) -> None
```

`visit/adapter/outbound/pg/report_pg_repository.py` — `class ReportPgRepository(ReportRepository, PublicReportRepository)`, 생성자 `(session: AsyncSession)`

`visit/adapter/outbound/mappers/visit_report_mapper.py` — `def to_report(orm: VisitReportOrm) -> VisitReport`

`visit/dependencies/visit_wiring.py` — `def build_report_repository(db: AsyncSession) -> ReportPgRepository`

`visit/tests/helpers/fakes.py`
```python
class FakeReportRepository(ReportRepository, PublicReportRepository):
    def __init__(self, visits: FakeVisits, journal: Journal | None = None) -> None
    rows: list[VisitReport]      # 테스트가 바로 읽거나 채워도 된다
class FakeRecords:
    async def set_hidden(self, ctx, visit_id, hidden_ids)
```
스텁이 journal 에 남기는 이름: `("close_expired_reports", visit_id)`, `("create_report", visit_id)`, `("revoke_report", visit_id)`, `("revoke_reports_for_customer", customer_id)`, `("mark_report_viewed", report_id)`, `("set_hidden", visit_id, hidden_ids)`. 읽기(`get_live`·`live_visit_ids`·`find`)는 남기지 않는다.

ORM 칸 이름: `VisitReportOrm`(`id`, `visit_id`, `public_id`, `expires_at`, `revoked_at`, `first_viewed_at`, `created_by_member_id`, `created_at`), `VisitRecordMediaOrm.hidden_from_report`, `VisitShopSettingsOrm.report_link_days`·`report_show_menus`·`report_show_shop_info`·`report_show_weight`·`report_show_amount`.

제약 이름: `uq_visit_reports_live`, `visit_reports_public_id_key`, `ck_visit_reports_expires`, `ck_visit_reports_public_id`, `ck_visit_shop_settings_report_link_days`.

뒤 작업이 알아 둘 동작
- **`create` 는 유일 위반을 바꾸지 않고 `sqlalchemy.exc.IntegrityError` 를 그대로 던진다.** 세이브포인트도 없어서 위반 뒤 그 트랜잭션은 더 쓸 수 없다. 발급 인터랙터는 방문 행을 잠근 뒤 `close_expired` → `get_live` 확인 → `create` 순서로 불러 위반이 나지 않게 해야 한다.
- **`create`·`set_hidden` 은 매장을 확인하지 않는다**(기존 `save`·`delete` 와 같다). 방문이 이 매장의 것임은 앞선 `lock_visits` 가 확인한다는 전제다. `get_live`·`live_visit_ids`·`close_expired`·`revoke`·`revoke_for_customer` 는 매장으로 거른다.
- `revoke` 는 기간이 지난 줄을 끊지 않고 False 를 준다. `revoke_for_customer` 는 기간이 지났어도 끊지 않은 줄이면 끊는다. 이미 끊은 줄의 `revoked_at` 은 덮지 않는다.
- `find` 는 질의 둘(링크+방문, 메뉴)이다. `ReportTarget.visit.has_live_report` 는 채우지 않는다(기본값 False).
- `save` 는 넘긴 `hidden` 을 그대로 쓴다. 앞선 표시를 잇는 것(`carry_hidden`)은 인터랙터의 일이다 — 아직 아무 인터랙터도 하지 않으므로, 지금은 기록을 PUT 하면 뺀 표시가 사라진다(T1 보고서 7절 1번과 함께 뒤 작업의 몫).
- 스텁 `FakeRecords.set_hidden` 은 도메인의 `report_rules.hide` 를 쓴다. 기록이 없는 방문에 부르면 `KeyError` 다(pg 구현은 아무 일도 하지 않는다).
- 스텁 `create` 의 `AssertionError` 는 매장과 상관없이 그 방문에 끊지 않은 줄이 있으면 난다(DB 의 색인과 같다).
- 매장 설정 칸은 DB·ORM 에만 있다. `ScheduleRepository`·`ScheduleSettings` 는 아직 읽지도 쓰지도 않는다. `SchedulePgRepository.ensure` 가 넣는 새 행은 server_default 로 기본값을 받는다.

설계 4절. 마이그레이션은 더하기만 한다. **개발 DB 에는 이 작업의 마지막 단계에서만 올린다**(`docker compose run --rm backend alembic upgrade head`, `infra/`). 부분 유일 색인과 CHECK 는 `test_schema_drift` 가 보지 않으므로 실제 DB 대조 테스트가 본다. `PublicReportRepository` 는 `ShopContext` 를 받지 않는 유일한 저장소다 — 토큰이 범위다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_report_pg_repository.py`:

```python
from datetime import timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(9, 28, 15)
WEEK = NOW + timedelta(days=7)
FIRST, SECOND = b"\x01" * 16, b"\x02" * 16


async def _setup(session, **visit_fields):
    return ReportPgRepository(session), await insert_visit(session, kst(9, 28, 14), "completed", **visit_fields)


async def test_만들고_살아_있는_링크로_읽는다(db_session):
    repo, visit_id = await _setup(db_session)
    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert (created.visit_id, created.public_id, created.expires_at, created.created_at) == (
        visit_id, FIRST, WEEK, NOW)
    assert (created.revoked_at, created.first_viewed_at, created.created_by_member_id) == (None, None, 11)
    assert await repo.get_live(A, visit_id, NOW) == created


async def test_다른_매장의_방문의_링크는_없는_것이다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.get_live(B, visit_id, NOW) is None
    assert await repo.live_visit_ids(B, [visit_id], NOW) == set()
    assert await repo.revoke(B, visit_id, NOW) is False
    await repo.close_expired(B, visit_id, WEEK)
    await repo.revoke_for_customer(B, 1, NOW)
    assert (await repo.get_live(A, visit_id, NOW)).revoked_at is None


async def test_기간이_지나면_살아_있지_않지만_공개_조회는_줄을_준다(db_session):
    repo, visit_id = await _setup(db_session)
    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.get_live(A, visit_id, WEEK - timedelta(seconds=1)) == created
    assert await repo.get_live(A, visit_id, WEEK) is None   # 끝나는 바로 그 시각에는 닫혀 있다
    assert (await repo.find(FIRST)).report == created


async def test_기간이_없는_링크는_언제나_살아_있다(db_session):
    repo, visit_id = await _setup(db_session)
    created = await repo.create(A, visit_id, FIRST, None, NOW)
    assert await repo.get_live(A, visit_id, NOW + timedelta(days=3650)) == created


async def test_끊지_않은_줄이_있는데_또_만들면_유일_위반이다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    with pytest.raises(IntegrityError):
        await repo.create(A, visit_id, SECOND, WEEK, NOW)


async def test_기간이_지난_줄을_닫지_않으면_새로_만들_수_없다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    with pytest.raises(IntegrityError):
        await repo.create(A, visit_id, SECOND, None, WEEK)


async def test_기간이_지난_줄을_닫으면_새로_만들_수_있다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await repo.close_expired(A, visit_id, WEEK)
    created = await repo.create(A, visit_id, SECOND, None, WEEK)
    assert await repo.get_live(A, visit_id, WEEK) == created
    assert (await repo.find(FIRST)).report.revoked_at == WEEK


async def test_기간이_남은_줄은_닫지_않는다(db_session):
    repo, visit_id = await _setup(db_session)
    forever = await repo.create(A, visit_id, FIRST, None, NOW)
    await repo.close_expired(A, visit_id, WEEK)
    assert await repo.get_live(A, visit_id, WEEK) == forever
    other = await insert_visit(db_session, kst(9, 29, 14), "completed")
    dated = await repo.create(A, other, SECOND, WEEK, NOW)
    await repo.close_expired(A, other, WEEK - timedelta(seconds=1))
    assert await repo.get_live(A, other, NOW) == dated


async def test_끊고_새로_만들면_다른_줄이고_옛_줄은_끊긴_채다(db_session):
    repo, visit_id = await _setup(db_session)
    old = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    later = NOW + timedelta(hours=1)
    assert await repo.revoke(A, visit_id, later) is True
    new = await repo.create(A, visit_id, SECOND, WEEK, later)
    assert (new.id != old.id, new.public_id) == (True, SECOND)
    assert await repo.get_live(A, visit_id, later) == new
    assert (await repo.find(FIRST)).report.revoked_at == later


async def test_끊기는_살아_있는_것만_끊는다(db_session):
    repo, visit_id = await _setup(db_session)
    assert await repo.revoke(A, visit_id, NOW) is False   # 링크가 없다
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.revoke(A, visit_id, WEEK) is False   # 기간이 지났다
    assert (await repo.find(FIRST)).report.revoked_at is None
    assert await repo.revoke(A, visit_id, NOW) is True
    assert await repo.revoke(A, visit_id, NOW) is False   # 이미 끊었다
    assert await repo.get_live(A, visit_id, NOW) is None


async def test_끊기는_그_방문의_링크만_끊는다(db_session):
    repo, visit_id = await _setup(db_session)
    other = await insert_visit(db_session, kst(9, 29, 14), "completed")
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    kept = await repo.create(A, other, SECOND, WEEK, NOW)
    await repo.revoke(A, visit_id, NOW)
    assert await repo.get_live(A, other, NOW) == kept


async def test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊는다(db_session):
    repo, visit_id = await _setup(db_session)
    expired = await insert_visit(db_session, kst(9, 27, 14), "completed")
    revoked = await insert_visit(db_session, kst(9, 26, 14), "completed")
    theirs = await insert_visit(db_session, kst(9, 29, 14), "completed", customer_id=2)
    ids = {v: bytes([n]) * 16 for n, v in enumerate((visit_id, expired, revoked, theirs), start=1)}
    for v, public_id in ids.items():
        await repo.create(A, v, public_id, NOW + timedelta(hours=1) if v == expired else None, NOW)
    await repo.revoke(A, revoked, NOW)
    later = NOW + timedelta(days=1)
    await repo.revoke_for_customer(A, 1, later)
    assert {v: (await repo.find(p)).report.revoked_at for v, p in ids.items()} == {
        visit_id: later, expired: later, revoked: NOW, theirs: None}


async def test_살아_있는_링크가_있는_방문을_질의_하나로_읽는다(db_session, db_engine):
    repo, visit_id = await _setup(db_session)
    expired = await insert_visit(db_session, kst(9, 27, 14), "completed")
    revoked = await insert_visit(db_session, kst(9, 26, 14), "completed")
    forever = await insert_visit(db_session, kst(9, 25, 14), "completed")
    bare = await insert_visit(db_session, kst(9, 24, 14), "completed")
    await repo.create(A, visit_id, b"\x01" * 16, WEEK, NOW)
    await repo.create(A, expired, b"\x02" * 16, NOW + timedelta(minutes=1), NOW)
    await repo.create(A, revoked, b"\x03" * 16, WEEK, NOW)
    await repo.create(A, forever, b"\x04" * 16, None, NOW)
    await repo.revoke(A, revoked, NOW)
    statements = []
    event.listen(db_engine.sync_engine, "before_cursor_execute", lambda *args: statements.append(args[2]))
    found = await repo.live_visit_ids(A, [visit_id, expired, revoked, forever, bare], NOW + timedelta(minutes=1))
    assert found == {visit_id, forever}
    assert len(statements) == 1
    assert await repo.live_visit_ids(A, [], NOW) == set()
    assert len(statements) == 1   # 빈 목록은 묻지 않는다


async def test_공개_조회는_링크와_매장과_방문을_함께_준다(db_session):
    from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
    from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
    from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
    from visit.domain.value_objects.new_visit import NewVisit

    await SchedulePgRepository(db_session).ensure(B)
    bath, trim, *_ = [m.id for m in await MenuPgRepository(db_session).list(B, include_archived=False)]
    [visit] = await VisitPgRepository(db_session).create_many(B, [NewVisit(
        customer_id=1, pet_id=101, starts_at=kst(9, 28, 14), duration_minutes=90, status="reserved",
        started_at=None, menu_ids=(trim, bath), memo=None, created_by_member_id=11)])
    repo = ReportPgRepository(db_session)
    created = await repo.create(B, visit.id, FIRST, WEEK, NOW)
    found = await repo.find(FIRST)
    assert (found.report, found.shop_id, found.visit) == (created, 2, visit)
    assert found.visit.menu_ids == (bath, trim)


async def test_없는_링크는_None_이다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.find(SECOND) is None


async def test_처음_연_시각은_한_번만_적는다(db_session):
    repo, visit_id = await _setup(db_session)
    other = await insert_visit(db_session, kst(9, 29, 14), "completed")
    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await repo.create(A, other, SECOND, WEEK, NOW)
    opened = NOW + timedelta(minutes=5)
    await repo.mark_viewed(created.id, opened)
    await repo.mark_viewed(created.id, opened + timedelta(hours=1))
    assert (await repo.find(FIRST)).report.first_viewed_at == opened
    assert (await repo.find(SECOND)).report.first_viewed_at is None


async def test_방문을_지우면_링크도_함께_지워진다(db_session):
    from sqlalchemy import delete

    from visit.adapter.outbound.orm.visit_orm import VisitOrm

    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await db_session.execute(delete(VisitOrm).where(VisitOrm.id == visit_id))
    assert await repo.find(FIRST) is None
```

`backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`:

```diff
@@ -101,3 +101,42 @@ async def test_익명화는_그_보호자의_기록_메모만_비운다(db_sessi
     await repo.clear_notes(A, 1)
     cleared, kept = await repo.get(A, visit_id), await repo.get(A, other)
     assert (cleared.care_note, cleared.internal_note, len(cleared.media), kept.care_note) == (None, None, 1, "케어")
+
+
+async def test_뺀_표시가_저장되고_읽힌다(db_session):
+    repo, visit_id, _, _ = await _setup(db_session)
+    media = (RecordMedia(8, "photo", "before", 0, hidden=True), RecordMedia(7, "photo", "after", 0))
+    saved = await repo.save(A, _record(visit_id, media=media))
+    assert saved.media == media
+    assert (await repo.get(A, visit_id)).media == media
+    assert (await repo.list_many(A, [visit_id]))[visit_id].media == media
+
+
+async def test_통째로_바꿔도_넘긴_뺀_표시가_그대로다(db_session):
+    repo, visit_id, _, _ = await _setup(db_session)
+    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0, hidden=True),
+                                                RecordMedia(8, "photo", "after", 1)]))
+    media = (RecordMedia(8, "photo", "after", 0, hidden=True), RecordMedia(7, "photo", "after", 1),
+             RecordMedia(9, "video", "after", 2))
+    assert (await repo.save(A, _record(visit_id, version=2, media=media))).media == media
+
+
+async def test_뺀_표시를_다시_매겨도_버전은_오르지_않는다(db_session):
+    repo, visit_id, _, _ = await _setup(db_session)
+    other = await insert_visit(db_session, kst(9, 24, 14), "in_progress")
+    await repo.save(A, _record(visit_id, version=3, media=[
+        RecordMedia(6, "photo", "before", 0, hidden=True), RecordMedia(7, "photo", "after", 0),
+        RecordMedia(8, "video", "after", 1)]))
+    await repo.save(A, _record(other, media=[RecordMedia(9, "photo", "after", 0)]))
+    await repo.set_hidden(A, visit_id, (7, 8, 9))
+    found = await repo.get(A, visit_id)
+    assert ([(m.media_id, m.hidden) for m in found.media], found.version) == ([(6, False), (7, True), (8, True)], 3)
+    assert (await repo.get(A, other)).media == (RecordMedia(9, "photo", "after", 0),)   # 다른 기록은 그대로다
+
+
+async def test_빈_목록으로_매기면_전부_되살린다(db_session):
+    repo, visit_id, _, _ = await _setup(db_session)
+    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0, hidden=True),
+                                                RecordMedia(8, "photo", "after", 1, hidden=True)]))
+    await repo.set_hidden(A, visit_id, ())
+    assert [m.hidden for m in (await repo.get(A, visit_id)).media] == [False, False]
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -20,7 +20,10 @@ from hub.app.errors import (
 )
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
+from visit.app.dtos.report_target_dto import ReportTarget
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.public_report_repository import PublicReportRepository
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.ports.output.visit_feed_repository import FeedPage, VisitFeedRepository
@@ -31,12 +34,14 @@ from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.domain.entities.menu import Menu
 from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
 from visit.domain.entities.visit_record import VisitRecord
+from visit.domain.entities.visit_report import VisitReport
 from visit.domain.errors import (
     MenuNameTakenError,
     MenuNotFoundError,
     VisitDuplicateError,
     VisitNotFoundError,
 )
+from visit.domain.services.report_rules import hide
 from visit.domain.state.visit_status import STARTED_STATUSES
 from visit.domain.value_objects.closed_date import ClosedDate
 from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
@@ -383,11 +388,79 @@ class FakeRecords(VisitRecordRepository):
         self.journal.append(("save_record", record.visit_id, record.version))
         return record
 
+    async def set_hidden(self, ctx, visit_id, hidden_ids):
+        self.rows[visit_id] = replace(self.rows[visit_id], media=hide(self.rows[visit_id], hidden_ids))
+        self.journal.append(("set_hidden", visit_id, tuple(hidden_ids)))
+
     async def delete(self, ctx, visit_id):
         self.rows.pop(visit_id, None)
         self.journal.append(("delete_record", visit_id))
 
 
+class FakeReportRepository(ReportRepository, PublicReportRepository):
+    """visit_reports 스텁 — pg 구현처럼 두 포트를 한 객체가 낸다. 방문의 매장은 visits 스텁에서 본다.
+
+    끊지 않은 줄이 있는 방문에 또 만들면 AssertionError 다 — 인터랙터가 닫기(close_expired)나 끊기를 빠뜨린 것이다.
+    """
+
+    def __init__(self, visits: FakeVisits, journal: Journal | None = None) -> None:
+        self.visits = visits
+        self.journal = journal if journal is not None else Journal()
+        self.rows: list[VisitReport] = []
+
+    def _open(self, ctx, **visit_fields) -> list[VisitReport]:
+        """이 매장의, 조건에 맞는 방문에 달린 끊지 않은 줄."""
+        return [
+            r for r in self.rows
+            if r.revoked_at is None and self.visits.rows[r.visit_id].shop_id == ctx.shop_id
+            and all(getattr(self.visits.rows[r.visit_id], k) == v for k, v in visit_fields.items())
+        ]
+
+    def _revoke(self, reports, now) -> None:
+        self.rows = [replace(r, revoked_at=now) if r in reports else r for r in self.rows]
+
+    async def get_live(self, ctx, visit_id, now):
+        return next((r for r in self._open(ctx, id=visit_id) if r.is_live(now)), None)
+
+    async def live_visit_ids(self, ctx, visit_ids, now):
+        return {r.visit_id for r in self._open(ctx) if r.visit_id in visit_ids and r.is_live(now)}
+
+    async def close_expired(self, ctx, visit_id, now):
+        self._revoke([r for r in self._open(ctx, id=visit_id) if not r.is_live(now)], now)
+        self.journal.append(("close_expired_reports", visit_id))
+
+    async def create(self, ctx, visit_id, public_id, expires_at, now):
+        assert all(r.revoked_at is not None for r in self.rows if r.visit_id == visit_id), "끊지 않은 줄이 있다"
+        report = VisitReport(
+            id=len(self.rows) + 1, visit_id=visit_id, public_id=public_id, expires_at=expires_at, revoked_at=None,
+            first_viewed_at=None, created_by_member_id=ctx.member_id, created_at=now)
+        self.rows.append(report)
+        self.journal.append(("create_report", visit_id))
+        return report
+
+    async def revoke(self, ctx, visit_id, now):
+        live = [r for r in self._open(ctx, id=visit_id) if r.is_live(now)]
+        self._revoke(live, now)
+        self.journal.append(("revoke_report", visit_id))
+        return bool(live)
+
+    async def revoke_for_customer(self, ctx, customer_id, now):
+        self._revoke(self._open(ctx, customer_id=customer_id), now)
+        self.journal.append(("revoke_reports_for_customer", customer_id))
+
+    async def find(self, public_id):
+        report = next((r for r in self.rows if r.public_id == public_id), None)
+        if report is None:
+            return None
+        visit = self.visits.rows[report.visit_id]
+        return ReportTarget(report=report, shop_id=visit.shop_id, visit=visit)
+
+    async def mark_viewed(self, report_id, now):
+        self.rows = [replace(r, first_viewed_at=now) if r.id == report_id and r.first_viewed_at is None else r
+                     for r in self.rows]
+        self.journal.append(("mark_report_viewed", report_id))
+
+
 class FakeLibrary(MediaLibraryPort):
     """MediaLibraryPort 스텁 — 실제 구현(media)과 같은 허브 오류를 같은 조건에서 던진다.
```

`backend/apps/visit/tests/test_fake_reports.py`:

```python
"""알림장 링크 스텁이 pg 구현과 같은 규칙을 지키는지 — 뒤 작업의 인터랙터 테스트가 이 스텁에 기댄다."""
from datetime import timedelta

import pytest

from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeReportRepository, FakeVisits

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(9, 28, 15)
WEEK = NOW + timedelta(days=7)
FIRST, SECOND = b"\x01" * 16, b"\x02" * 16


def _reports(**visit_fields):
    visits = FakeVisits()
    return FakeReportRepository(visits), visits.seed(**visit_fields)


async def test_만든_링크는_그_매장에서만_살아_있다():
    reports, visit = _reports()
    created = await reports.create(A, visit.id, FIRST, WEEK, NOW)
    assert (created.created_by_member_id, created.created_at) == (11, NOW)
    assert await reports.get_live(A, visit.id, NOW) == created
    assert await reports.live_visit_ids(A, [visit.id, 99], NOW) == {visit.id}
    assert await reports.get_live(A, visit.id, WEEK) is None
    assert await reports.get_live(B, visit.id, NOW) is None
    assert await reports.revoke(B, visit.id, NOW) is False
    found = await reports.find(FIRST)
    assert (found.report, found.shop_id, found.visit) == (created, 1, visit)
    assert await reports.find(SECOND) is None


async def test_끊지_않은_줄이_있는데_또_만들면_테스트_실수다():
    reports, visit = _reports()
    await reports.create(A, visit.id, FIRST, WEEK, NOW)
    with pytest.raises(AssertionError):
        await reports.create(A, visit.id, SECOND, None, WEEK)
    await reports.close_expired(A, visit.id, WEEK)
    assert (await reports.create(A, visit.id, SECOND, None, WEEK)).public_id == SECOND
    assert (await reports.find(FIRST)).report.revoked_at == WEEK


async def test_끊기는_살아_있는_것만_익명화는_그_보호자의_끊지_않은_것_모두():
    reports, visit = _reports()
    theirs = reports.visits.seed(customer_id=2)
    await reports.create(A, visit.id, FIRST, NOW + timedelta(hours=1), NOW)
    await reports.create(A, theirs.id, SECOND, None, NOW)
    assert await reports.revoke(A, visit.id, WEEK) is False   # 기간이 지났다
    await reports.revoke_for_customer(A, 1, WEEK)
    assert [(await reports.find(p)).report.revoked_at for p in (FIRST, SECOND)] == [WEEK, None]
    assert await reports.revoke(A, theirs.id, NOW) is True
    assert await reports.revoke(A, theirs.id, NOW) is False


async def test_처음_연_시각은_한_번만_적는다():
    reports, visit = _reports()
    created = await reports.create(A, visit.id, FIRST, WEEK, NOW)
    await reports.mark_viewed(created.id, NOW)
    await reports.mark_viewed(created.id, WEEK)
    assert (await reports.find(FIRST)).report.first_viewed_at == NOW
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -2,6 +2,8 @@
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.public_report_repository import PublicReportRepository
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
@@ -15,6 +17,7 @@ from visit.tests.helpers.fakes import (
     FakeLibrary,
     FakeMenus,
     FakeRecords,
+    FakeReportRepository,
     FakeSchedule,
     FakeVisits,
 )
@@ -30,3 +33,5 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
                  VisitBoardRepository, VisitFeedRepository):
         assert isinstance(visits, port), port.__name__
     assert isinstance(FakeRecords(visits), VisitRecordRepository)
+    reports = FakeReportRepository(visits)
+    assert isinstance(reports, ReportRepository) and isinstance(reports, PublicReportRepository)
```

`backend/tests/integration/test_visit_report_schema.py`:

```python
"""알림장(0010)의 부분 유일 색인과 CHECK 가 실제 DB 에 있는지 — 실제 DB 에서 읽고 넣어 본다.

tests/test_schema_drift.py 의 compare_metadata 는 CHECK 와 부분 색인의 WHERE 를 비교하지 않는다. ORM 에만 적고
마이그레이션에서 빠뜨리면 여기서 걸린다.
"""
from datetime import timedelta

import pytest
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import IntegrityError

from visit.adapter.outbound.orm.visit_orm import VisitReportOrm, VisitShopSettingsOrm
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A = ctx(shop_id=1)
NOW = kst(9, 28, 15)


async def test_끊지_않은_줄의_부분_유일_색인이다(db_engine):
    async with db_engine.connect() as conn:
        unique, columns, predicate = (await conn.execute(text(
            "SELECT i.indisunique, pg_get_indexdef(i.indexrelid, 1, true), pg_get_expr(i.indpred, i.indrelid) "
            "FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid WHERE c.relname = 'uq_visit_reports_live'"
        ))).one()
    assert (unique, columns, predicate) == (True, "visit_id", "(revoked_at IS NULL)")


def _report(visit_id, **overrides):
    return insert(VisitReportOrm).values(**{
        "visit_id": visit_id, "public_id": b"\x01" * 16, "expires_at": None, "created_by_member_id": 11,
        "created_at": NOW, **overrides})


@pytest.mark.parametrize("expires_at", [NOW, NOW - timedelta(seconds=1)])
async def test_기간은_보낸_시각보다_뒤여야_한다(db_session, expires_at):
    visit_id = await insert_visit(db_session, kst(9, 28, 14), "completed")
    with pytest.raises(IntegrityError, match="ck_visit_reports_expires"):
        await db_session.execute(_report(visit_id, expires_at=expires_at))


@pytest.mark.parametrize("public_id", [b"", b"\x01" * 15, b"\x01" * 17])
async def test_public_id_는_16바이트여야_한다(db_session, public_id):
    visit_id = await insert_visit(db_session, kst(9, 28, 14), "completed")
    with pytest.raises(IntegrityError, match="ck_visit_reports_public_id"):
        await db_session.execute(_report(visit_id, public_id=public_id))


async def test_public_id_는_방문이_달라도_겹칠_수_없다(db_session):
    first = await insert_visit(db_session, kst(9, 28, 14), "completed")
    second = await insert_visit(db_session, kst(9, 29, 14), "completed")
    await db_session.execute(_report(first))
    with pytest.raises(IntegrityError, match="visit_reports_public_id_key"):
        await db_session.execute(_report(second))


async def test_새_칸의_기본값은_기간_30일_메뉴와_매장_정보만_보이기다(db_session):
    await SchedulePgRepository(db_session).ensure(A)
    row = (await db_session.execute(select(
        VisitShopSettingsOrm.report_link_days, VisitShopSettingsOrm.report_show_menus,
        VisitShopSettingsOrm.report_show_shop_info, VisitShopSettingsOrm.report_show_weight,
        VisitShopSettingsOrm.report_show_amount,
    ))).one()
    assert tuple(row) == (30, True, True, False, False)


def _set_link_days(days):
    return update(VisitShopSettingsOrm).where(VisitShopSettingsOrm.shop_id == 1).values(report_link_days=days)


@pytest.mark.parametrize("days", [1, 0, -1, 31, 8, 29])
async def test_링크_기간은_7일과_30일만_받는다(db_session, days):
    await SchedulePgRepository(db_session).ensure(A)
    with pytest.raises(IntegrityError, match="ck_visit_shop_settings_report_link_days"):
        await db_session.execute(_set_link_days(days))


@pytest.mark.parametrize("days", [7, 30, None])
async def test_링크_기간_7일_30일_무기한은_받는다(db_session, days):
    await SchedulePgRepository(db_session).ensure(A)
    await db_session.execute(_set_link_days(days))
    assert (await db_session.execute(select(VisitShopSettingsOrm.report_link_days))).scalar_one() == days
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

명령(`infra/`):
`docker compose run --rm backend pytest apps/visit/tests/adapter/test_report_pg_repository.py apps/visit/tests/adapter/test_visit_record_pg_repository.py tests/integration/test_visit_report_schema.py apps/visit/tests/test_fakes_are_ports.py apps/visit/tests/test_fake_reports.py tests/test_schema_drift.py -q -p no:cacheprovider`

결과: `4 errors in 0.29s` — 수집 오류 넷에서 멈췄다. 예:
`ImportError: cannot import name 'VisitReportOrm' from 'visit.adapter.outbound.orm.visit_orm'`,
`ModuleNotFoundError: No module named 'visit.app.ports.output.public_report_repository'`,
`ImportError: cannot import name 'FakeReportRepository' from 'visit.tests.helpers.fakes'`.

수집에서 멈췄기 때문에 기존 파일에 더한 기록 테스트 넷(`test_visit_record_pg_repository.py`)이 따로 실패하는 모습은 보지 못했다. 그 넷은 변이 4·13·21 로 실패를 확인했다(4절).

- [ ] **Step 3: 구현한다**

`backend/alembic/versions/0010_visit_reports.py`:

```python
"""미용 알림장 — 링크(visit_reports), 뺀 사진 칸, 매장 설정 칸

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_SHOWN = {"report_show_menus": "true", "report_show_shop_info": "true",
          "report_show_weight": "false", "report_show_amount": "false"}


def upgrade() -> None:
    op.create_table(
        "visit_reports",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_id", sa.LargeBinary(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),          # NULL 이면 무기한
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),   # tenancy 의 멤버 ID — 외래 키 없음
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("expires_at IS NULL OR expires_at > created_at", name="ck_visit_reports_expires"),
        sa.CheckConstraint("octet_length(public_id) = 16", name="ck_visit_reports_public_id"),
        sa.UniqueConstraint("public_id", name="visit_reports_public_id_key"),
    )
    # 방문당 끊지 않은 줄은 하나. 색인에 현재 시각을 넣을 수 없어 기간이 지난 줄은 발급이 먼저 닫는다.
    op.create_index(
        "uq_visit_reports_live", "visit_reports", ["visit_id"], unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.add_column(
        "visit_record_media",
        sa.Column("hidden_from_report", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )
    # NULL 은 무기한이다 — 이미 있는 매장 행은 server_default 로 30 을 받는다.
    op.add_column("visit_shop_settings", sa.Column("report_link_days", sa.SmallInteger, server_default=sa.text("30")))
    op.create_check_constraint(
        "ck_visit_shop_settings_report_link_days", "visit_shop_settings",
        "report_link_days IS NULL OR report_link_days IN (7, 30)",
    )
    for name, default in _SHOWN.items():
        op.add_column(
            "visit_shop_settings", sa.Column(name, sa.Boolean, server_default=sa.text(default), nullable=False)
        )


def downgrade() -> None:
    for name in reversed(_SHOWN):
        op.drop_column("visit_shop_settings", name)
    op.drop_constraint("ck_visit_shop_settings_report_link_days", "visit_shop_settings", type_="check")
    op.drop_column("visit_shop_settings", "report_link_days")
    op.drop_column("visit_record_media", "hidden_from_report")
    op.drop_index("uq_visit_reports_live", table_name="visit_reports")
    op.drop_table("visit_reports")
```

`backend/apps/visit/adapter/outbound/orm/visit_orm.py`:

```diff
@@ -5,12 +5,14 @@ from decimal import Decimal
 
 from sqlalchemy import (
     BigInteger,
+    Boolean,
     CheckConstraint,
     Date,
     DateTime,
     ForeignKey,
     Index,
     Integer,
+    LargeBinary,
     Numeric,
     SmallInteger,
     String,
@@ -47,6 +49,10 @@ class VisitShopSettingsOrm(Base):
             "default_duration_minutes " + _DURATION_RULE.format(col="default_duration_minutes"),
             name="ck_visit_shop_settings_duration",
         ),
+        CheckConstraint(
+            "report_link_days IS NULL OR report_link_days IN (7, 30)",
+            name="ck_visit_shop_settings_report_link_days",
+        ),
     )
 
     # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
@@ -54,6 +60,12 @@ class VisitShopSettingsOrm(Base):
     opens_at: Mapped[time] = mapped_column(Time)
     closes_at: Mapped[time] = mapped_column(Time)
     default_duration_minutes: Mapped[int] = mapped_column(SmallInteger)
+    # ⑤ 알림장 — 링크 기간(일, NULL 이면 무기한)과 보호자에게 보여 줄 항목.
+    report_link_days: Mapped[int | None] = mapped_column(SmallInteger, server_default=text("30"))
+    report_show_menus: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
+    report_show_shop_info: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
+    report_show_weight: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
+    report_show_amount: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
     updated_at: Mapped[datetime] = mapped_column(
         DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
@@ -245,3 +257,25 @@ class VisitRecordMediaOrm(Base):
     kind: Mapped[str] = mapped_column(String(10))
     phase: Mapped[str] = mapped_column(String(10))
     sort_order: Mapped[int] = mapped_column(SmallInteger)
+    hidden_from_report: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))   # ⑤ 알림장에서 뺀 사진
+
+
+class VisitReportOrm(Base):
+    """알림장 링크 하나(설계 4.1). 매장은 방문에서 읽는다. 토큰은 저장하지 않는다 — public_id 와 서버 키로 계산한다."""
+
+    __tablename__ = "visit_reports"
+    __table_args__ = (
+        CheckConstraint("expires_at IS NULL OR expires_at > created_at", name="ck_visit_reports_expires"),
+        CheckConstraint("octet_length(public_id) = 16", name="ck_visit_reports_public_id"),
+        # 방문당 끊지 않은 줄은 하나. 색인에 현재 시각을 넣을 수 없어 기간이 지난 줄은 발급이 먼저 닫는다.
+        Index("uq_visit_reports_live", "visit_id", unique=True, postgresql_where=text("revoked_at IS NULL")),
+    )
+
+    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
+    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"))
+    public_id: Mapped[bytes] = mapped_column(LargeBinary(16), unique=True)
+    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))   # NULL 이면 무기한
+    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+    first_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+    created_by_member_id: Mapped[int] = mapped_column(BigInteger)   # tenancy 의 멤버 ID
+    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`backend/apps/visit/app/ports/output/report_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit_report import VisitReport


class ReportRepository(ABC):
    """알림장 링크(visit_reports). 매장 범위 — 방문의 매장(ShopContext)으로 거른다.

    쓰기는 방문 행을 잠근 **뒤에만** 부른다. '살아 있다'는 끊지 않았고 기간이 지나지 않았다는 뜻이다.
    """

    @abstractmethod
    async def get_live(self, ctx: ShopContext, visit_id: int, now: datetime) -> VisitReport | None:
        """그 방문의 살아 있는 링크. 없거나 다른 매장의 방문이면 None."""

    @abstractmethod
    async def live_visit_ids(self, ctx: ShopContext, visit_ids: list[int], now: datetime) -> set[int]:
        """살아 있는 링크가 있는 방문의 ID — 목록의 '보냄' 표시를 방문 수와 상관없이 한 번에 읽는다."""

    @abstractmethod
    async def close_expired(self, ctx: ShopContext, visit_id: int, now: datetime) -> None:
        """끊지 않았는데 기간이 지난 줄을 끊는다(revoked_at = now). 새 줄을 넣기 전에 부른다 — 부분 유일 색인은
        기간을 모르므로 닫지 않으면 새 줄이 유일 위반이 된다."""

    @abstractmethod
    async def create(
        self, ctx: ShopContext, visit_id: int, public_id: bytes, expires_at: datetime | None, now: datetime
    ) -> VisitReport:
        """새 줄을 넣는다. 만든 사람은 ctx 의 멤버, 보낸 시각은 now."""

    @abstractmethod
    async def revoke(self, ctx: ShopContext, visit_id: int, now: datetime) -> bool:
        """그 방문의 살아 있는 줄을 끊는다. 끊은 것이 있으면 True."""

    @abstractmethod
    async def revoke_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        """그 보호자의 방문들의, 끊지 않은 줄을 모두 끊는다(익명화)."""
```

`backend/apps/visit/app/dtos/report_target_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_report import VisitReport


@dataclass(frozen=True)
class ReportTarget:
    """토큰이 가리키는 링크와 그 방문. shop_id 로 ShopContext 없이 시작한 공개 조회가 매장을 안다."""

    report: VisitReport
    shop_id: int
    visit: Visit
```

`backend/apps/visit/app/ports/output/public_report_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from visit.app.dtos.report_target_dto import ReportTarget


class PublicReportRepository(ABC):
    """로그인이 없는 공개 조회가 쓰는 알림장 링크.

    `ShopContext` 를 받지 않는 **유일한** 저장소다. 보호자는 멤버가 아니라 매장 컨텍스트가 없다 — 서명을 확인한
    토큰의 public_id 가 곧 범위이고, 매장은 찾은 방문에서 읽는다. 서명을 확인하지 않은 값을 넘기지 않는다.
    """

    @abstractmethod
    async def find(self, public_id: bytes) -> ReportTarget | None:
        """끊었든 기간이 지났든 줄이 있으면 준다 — 404 와 410 을 가르는 것은 부르는 쪽이다."""

    @abstractmethod
    async def mark_viewed(self, report_id: int, now: datetime) -> None:
        """처음 연 시각을 적는다. 이미 적혀 있으면 그대로 둔다 — 조건부 UPDATE 한 줄이라 잠금이 없다."""
```

`backend/apps/visit/app/ports/output/visit_record_repository.py`:

```diff
@@ -31,7 +31,15 @@ class VisitRecordRepository(ABC):
 
     @abstractmethod
     async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
-        """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다."""
+        """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다.
+        미디어의 뺀 표시(hidden)도 넘긴 그대로 쓴다 — 앞선 표시를 이어 붙이는 것은 부르는 쪽의 일이다."""
+
+    @abstractmethod
+    async def set_hidden(self, ctx: ShopContext, visit_id: int, hidden_ids: tuple[int, ...]) -> None:
+        """그 기록의 미디어 전부에 뺀 표시를 다시 매긴다 — hidden_ids 에 있으면 뺀 것, 없으면 보이는 것.
+
+        기록 버전은 올리지 않는다. 뺀 표시는 앱의 폼 저장(PUT)이 모르고 지울 값이 아니다 — 폼은 이 값을 보내지
+        않고 서버가 미디어 ID 로 이어 붙인다."""
 
     @abstractmethod
     async def delete(self, ctx: ShopContext, visit_id: int) -> None:
```

`backend/apps/visit/adapter/outbound/mappers/visit_report_mapper.py`:

```python
from __future__ import annotations

from visit.adapter.outbound.orm.visit_orm import VisitReportOrm
from visit.domain.entities.visit_report import VisitReport


def to_report(orm: VisitReportOrm) -> VisitReport:
    return VisitReport(
        id=orm.id, visit_id=orm.visit_id, public_id=orm.public_id, expires_at=orm.expires_at,
        revoked_at=orm.revoked_at, first_viewed_at=orm.first_viewed_at,
        created_by_member_id=orm.created_by_member_id, created_at=orm.created_at,
    )
```

`backend/apps/visit/adapter/outbound/mappers/visit_record_mapper.py`:

```diff
@@ -11,8 +11,8 @@ def to_record(
         visit_id=row.visit_id, weight_kg=row.weight_kg, care_note=row.care_note, internal_note=row.internal_note,
         payment_method=row.payment_method, total_amount=row.total_amount,
         items=tuple(RecordItem(menu_id=i.menu_id, amount=i.amount) for i in items),
-        media=tuple(RecordMedia(media_id=m.media_id, kind=m.kind, phase=m.phase, sort_order=m.sort_order)
-                    for m in media),
+        media=tuple(RecordMedia(media_id=m.media_id, kind=m.kind, phase=m.phase, sort_order=m.sort_order,
+                                hidden=m.hidden_from_report) for m in media),
         version=row.version, created_by_member_id=row.created_by_member_id,
         updated_by_member_id=row.updated_by_member_id,
     )
```

`backend/apps/visit/adapter/outbound/pg/report_pg_repository.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_visit
from visit.adapter.outbound.mappers.visit_report_mapper import to_report
from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm, VisitReportOrm
from visit.app.dtos.report_target_dto import ReportTarget
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.domain.entities.visit_report import VisitReport


def _live(now: datetime) -> tuple:
    """VisitReport.is_live 와 같은 조건 — 끊지 않았고 기간이 지나지 않았다."""
    return (
        VisitReportOrm.revoked_at.is_(None),
        or_(VisitReportOrm.expires_at.is_(None), VisitReportOrm.expires_at > now),
    )


def _of_shop(ctx: ShopContext, *conditions):
    """이 매장의 방문에 달린 줄만 — visit_reports 에는 매장 칸이 없다."""
    return VisitReportOrm.visit_id.in_(select(VisitOrm.id).where(VisitOrm.shop_id == ctx.shop_id, *conditions))


class ReportPgRepository(ReportRepository, PublicReportRepository):
    """visit_reports 표 하나를 두 포트로 내놓는다 — 매장 범위(앱)와 공개 조회(보호자 웹)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_live(self, ctx: ShopContext, visit_id: int, now: datetime) -> VisitReport | None:
        row = (
            await self._session.execute(
                select(VisitReportOrm)
                .where(VisitReportOrm.visit_id == visit_id, _of_shop(ctx), *_live(now))
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_report(row) if row is not None else None

    async def live_visit_ids(self, ctx: ShopContext, visit_ids: list[int], now: datetime) -> set[int]:
        if not visit_ids:
            return set()
        rows = await self._session.execute(
            select(VisitReportOrm.visit_id)
            .where(VisitReportOrm.visit_id.in_(visit_ids), _of_shop(ctx), *_live(now))
        )
        return set(rows.scalars())

    async def close_expired(self, ctx: ShopContext, visit_id: int, now: datetime) -> None:
        await self._session.execute(
            update(VisitReportOrm)
            .where(VisitReportOrm.visit_id == visit_id, _of_shop(ctx), VisitReportOrm.revoked_at.is_(None),
                   VisitReportOrm.expires_at <= now)
            .values(revoked_at=now)
        )

    async def create(
        self, ctx: ShopContext, visit_id: int, public_id: bytes, expires_at: datetime | None, now: datetime
    ) -> VisitReport:
        row = (
            await self._session.execute(
                insert(VisitReportOrm)
                .values(visit_id=visit_id, public_id=public_id, expires_at=expires_at,
                        created_by_member_id=ctx.member_id, created_at=now)
                .returning(VisitReportOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_report(row)

    async def revoke(self, ctx: ShopContext, visit_id: int, now: datetime) -> bool:
        revoked = await self._session.execute(
            update(VisitReportOrm)
            .where(VisitReportOrm.visit_id == visit_id, _of_shop(ctx), *_live(now))
            .values(revoked_at=now)
            .returning(VisitReportOrm.id)
        )
        return revoked.first() is not None

    async def revoke_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        await self._session.execute(
            update(VisitReportOrm)
            .where(_of_shop(ctx, VisitOrm.customer_id == customer_id), VisitReportOrm.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def find(self, public_id: bytes) -> ReportTarget | None:
        found = (
            await self._session.execute(
                select(VisitReportOrm, VisitOrm)
                .join(VisitOrm, VisitOrm.id == VisitReportOrm.visit_id)
                .where(VisitReportOrm.public_id == public_id)
                .execution_options(populate_existing=True)
            )
        ).first()
        if found is None:
            return None
        report, visit = found
        menu_ids = await self._session.execute(
            select(VisitMenuOrm.menu_id).where(VisitMenuOrm.visit_id == visit.id).order_by(VisitMenuOrm.menu_id)
        )
        return ReportTarget(
            report=to_report(report), shop_id=visit.shop_id, visit=to_visit(visit, list(menu_ids.scalars()))
        )

    async def mark_viewed(self, report_id: int, now: datetime) -> None:
        await self._session.execute(
            update(VisitReportOrm)
            .where(VisitReportOrm.id == report_id, VisitReportOrm.first_viewed_at.is_(None))
            .values(first_viewed_at=now)
        )
```

`backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`:

```diff
@@ -98,7 +98,7 @@ class VisitRecordPgRepository(VisitRecordRepository):
             await self._session.execute(
                 insert(VisitRecordMediaOrm),
                 [dict(visit_id=record.visit_id, media_id=m.media_id, kind=m.kind, phase=m.phase,
-                      sort_order=m.sort_order) for m in record.media],
+                      sort_order=m.sort_order, hidden_from_report=m.hidden) for m in record.media],
             )
         row = (
             await self._session.execute(
@@ -108,5 +108,12 @@ class VisitRecordPgRepository(VisitRecordRepository):
         ).scalar_one()
         return (await self._assemble([row]))[record.visit_id]
 
+    async def set_hidden(self, ctx: ShopContext, visit_id: int, hidden_ids: tuple[int, ...]) -> None:
+        await self._session.execute(
+            update(VisitRecordMediaOrm)
+            .where(VisitRecordMediaOrm.visit_id == visit_id)
+            .values(hidden_from_report=VisitRecordMediaOrm.media_id.in_(hidden_ids))
+        )
+
     async def delete(self, ctx: ShopContext, visit_id: int) -> None:
         await self._session.execute(delete(VisitRecordOrm).where(VisitRecordOrm.visit_id == visit_id))
```

`backend/apps/visit/dependencies/visit_wiring.py`:

```diff
@@ -4,6 +4,7 @@ from __future__ import annotations
 from sqlalchemy.ext.asyncio import AsyncSession
 
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
+from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
@@ -27,3 +28,8 @@ def build_visit_repository(db: AsyncSession) -> VisitPgRepository:
 
 def build_record_repository(db: AsyncSession) -> VisitRecordRepository:
     return VisitRecordPgRepository(db)
+
+
+def build_report_repository(db: AsyncSession) -> ReportPgRepository:
+    """visit_reports 표의 리포지토리 하나. 매장 범위 포트와 공개 조회 포트를 다 구현한다."""
+    return ReportPgRepository(db)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 테스트 여섯 파일 | 51 passed (새로 더한 것 42 — 링크 저장소 17, 기록 저장소 4, 실제 DB 대조 17, 스텁 4. 나머지 9는 기존 기록 테스트 7·스텁 포트 1·drift 1) |
| 단위 전체 | 1016 passed, 338 deselected (시작 1012 → +4) |
| 통합 전체 | 338 passed, 1016 deselected (시작 300 → +38) |
| 구조 계약 | 6 kept, 0 broken |
| `tests/test_schema_drift.py` | 통과(위 51 과 통합 전체에 포함) |


따로 돌려 본 것(커밋에 없는 일회용 스크립트, 테스트 DB `chagocnote_test` 에서만):
- `downgrade 0009` → `visit_reports` 표가 없고 `report_*`·`hidden_from_report` 칸이 0개.
- 0009 상태에서 `visit_shop_settings` 에 행 하나를 넣고 `upgrade head` → 그 기존 행이 `(30, true, true, false, false)` 를 받았다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `get_live` 의 `_of_shop(ctx)` 제거 → `test_다른_매장의_방문의_링크는_없는_것이다`
- `mark_viewed` 의 `first_viewed_at.is_(None)` 제거 → `test_처음_연_시각은_한_번만_적는다`
- `close_expired` 가 곧바로 `return` → `test_기간이_지난_줄을_닫으면_새로_만들_수_있다`
- `save` 가 `hidden_from_report` 를 쓰지 않는다 → `test_뺀_표시가_저장되고_읽힌다`, `test_통째로_바꿔도_넘긴_뺀_표시가_그대로다`
- 마이그레이션 색인의 `postgresql_where` 제거(전체 유일) → `test_끊고_새로_만들면_다른_줄이고_옛_줄은_끊긴_채다`, `test_기간이_지난_줄을_닫으면_새로_만들_수_있다`, `test_끊지_않은_줄의_부분_유일_색인이다`. `test_schema_drift.py` 는 통과했다(부분 색인 조건을 보지 않는다는 기존 설명 그대로)
- `revoke_for_customer` 의 `customer_id` 조건 제거 → `test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊는다`
- `_live` 의 `expires_at > now` → `>=` → `test_기간이_지나면_살아_있지_않지만_공개_조회는_줄을_준다`, `test_끊기는_살아_있는_것만_끊는다`, `test_살아_있는_링크가_있는_방문을_질의_하나로_읽는다`
- `close_expired` 의 `expires_at <= now` → `<` → `test_기간이_지난_줄을_닫으면_새로_만들_수_있다`
- `revoke` 가 기간을 안 본다(끊지 않은 것이면 끊는다) → `test_끊기는_살아_있는_것만_끊는다`
- `revoke` 의 `visit_id` 조건 제거 → `test_끊기는_그_방문의_링크만_끊는다` 외 둘
- `live_visit_ids` 의 매장 조건 제거 → `test_다른_매장의_방문의_링크는_없는_것이다`
- `close_expired` 의 매장 조건 제거 → `test_다른_매장의_방문의_링크는_없는_것이다`
- `set_hidden` 이 모든 기록의 미디어를 고친다 → `test_뺀_표시를_다시_매겨도_버전은_오르지_않는다`
- `revoke_for_customer` 가 이미 끊은 줄의 시각을 덮는다 → `test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊는다`
- `find` 가 메뉴를 못 읽는다 → `test_공개_조회는_링크와_매장과_방문을_함께_준다`
- 마이그레이션 `report_link_days` 의 `server_default` 제거 → `test_새_칸의_기본값은_기간_30일_메뉴와_매장_정보만_보이기다`
- 마이그레이션의 link_days CHECK 제거 → `test_링크_기간은_7일과_30일만_받는다[1·0·-1·31·8·29]`
- 마이그레이션의 public_id 길이 CHECK 제거 → `test_public_id_는_16바이트여야_한다` 셋
- 마이그레이션의 기간 CHECK 제거 → `test_기간은_보낸_시각보다_뒤여야_한다` 둘
- 스텁 `create` 의 assert 제거 → `test_끊지_않은_줄이_있는데_또_만들면_테스트_실수다`
- `set_hidden` 이 전부 뺀 것으로 매긴다 → `test_뺀_표시를_다시_매겨도_버전은_오르지_않는다`, `test_빈_목록으로_매기면_전부_되살린다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 알림장 표와 저장소 — visit_reports(0010), 뺀 사진 칸, 매장 설정 칸, 공개 조회용 저장소

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 알림장 설정 — 링크 기간과 보여 줄 항목을 매장이 정한다(`GET`·`PUT /report-settings`)

**Files:**
- Create: `backend/apps/visit/app/ports/output/report_settings_repository.py`
- Create: `backend/apps/visit/adapter/outbound/pg/report_settings_pg_repository.py`
- Modify: `backend/apps/visit/dependencies/visit_wiring.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/get_report_settings_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/update_report_settings_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/get_report_settings_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/update_report_settings_router.py`
- Create: `backend/apps/visit/app/dtos/get_report_settings_dto.py`
- Create: `backend/apps/visit/app/dtos/update_report_settings_dto.py`
- Create: `backend/apps/visit/app/ports/input/get_report_settings_use_case.py`
- Create: `backend/apps/visit/app/ports/input/update_report_settings_use_case.py`
- Create: `backend/apps/visit/app/use_cases/get_report_settings_interactor.py`
- Create: `backend/apps/visit/app/use_cases/update_report_settings_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/dependencies/get_report_settings_provider.py`
- Create: `backend/apps/visit/dependencies/update_report_settings_provider.py`
- Create: `backend/apps/visit/tests/adapter/test_get_report_settings_router.py`
- Create: `backend/apps/visit/tests/adapter/test_report_settings_pg_repository.py`
- Create: `backend/apps/visit/tests/adapter/test_update_report_settings_router.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_get_report_settings_interactor.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_update_report_settings_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_report_settings_wiring.py`

**Interfaces:**
- Consumes: 작업 1 의 `ReportSettings`·`DEFAULT_REPORT_SETTINGS`·`check_settings`; 작업 2 의 설정 칸; `ScheduleRepository.ensure`; `core.shop_guard.get_shop_context`·`require_permission`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

`visit/app/ports/output/report_settings_repository.py`
```python
class ReportSettingsRepository(ABC):
    async def get(self, ctx: ShopContext) -> ReportSettings
    async def update(self, ctx: ShopContext, settings: ReportSettings) -> ReportSettings
```

`visit/adapter/outbound/pg/report_settings_pg_repository.py` — `class ReportSettingsPgRepository(ReportSettingsRepository)`, 생성자 `(session: AsyncSession)`

`visit/dependencies/visit_wiring.py` — `def build_report_settings_repository(db: AsyncSession) -> ReportSettingsRepository`

`visit/tests/helpers/fakes.py`
```python
class FakeReportSettingsRepository(ReportSettingsRepository):
    def __init__(self, journal: Journal | None = None) -> None
    rows: dict[int, ReportSettings]    # 매장 ID → 설정. 테스트가 바로 채워도 된다. 없는 매장은 DEFAULT_REPORT_SETTINGS
```
journal 에 남기는 이름: `("update_report_settings", shop_id)`. `get` 은 남기지 않는다.

슬라이스
```python
# dtos
GetReportSettingsQuery(ctx: ShopContext)
UpdateReportSettingsCommand(ctx: ShopContext, settings: ReportSettings)
# 입력 포트
GetReportSettingsUseCase.get_report_settings(query) -> ReportSettings
UpdateReportSettingsUseCase.update_report_settings(command) -> ReportSettings
# 인터랙터
GetReportSettingsInteractor(settings: ReportSettingsRepository)
UpdateReportSettingsInteractor(schedule: ScheduleRepository, settings: ReportSettingsRepository)
# 프로바이더
get_get_report_settings_use_case(db: DbSession) -> GetReportSettingsUseCase
get_update_report_settings_use_case(db: DbSession) -> UpdateReportSettingsUseCase
# 스키마
ReportSettingsSchema(link_days: int | None, show_menus, show_shop_info, show_weight, show_amount: bool)  # .of(settings)
UpdateReportSettingsRequestSchema(link_days: Literal[7, 30] | None, 나머지 넷 StrictBool)               # .to_settings()
# 라우터
get_report_settings_router      GET /v1/shops/{shop_id}/report-settings   get_shop_context
update_report_settings_router   PUT /v1/shops/{shop_id}/report-settings   require_permission("shop:update")
```

뒤 작업이 알아 둘 동작
- **`get` 은 설정 행을 만들지 않는다.** 행이 없는 매장은 `DEFAULT_REPORT_SETTINGS` 를 받는다. 공개 조회·발급 인터랙터가 그대로 불러도 된다.
- **`get` 은 잠그지 않는다.** 칸 다섯만 읽는 SELECT 하나다(ORM 객체를 읽지 않으므로 세션의 identity map 과 상관없이 언제나 DB 의 값이다).
- **`update` 는 행이 없으면 `sqlalchemy.exc.NoResultFound` 다**(`UPDATE … RETURNING` 의 `.one()`). 반드시 `ScheduleRepository.ensure` 뒤에 부른다. `ensure` 는 처음이면 기본 메뉴 다섯도 함께 넣는다 — 알림장 설정을 처음 저장하는 매장에 일정 설정과 기본 메뉴가 생긴다.
- 스텁 `update` 는 행이 있는지 보지 않는다. "ensure 뒤"는 journal 의 순서로 확인한다(스텁 둘에 같은 `Journal` 을 넘긴다).
- 유스케이스는 뷰 DTO 없이 도메인의 `ReportSettings` 를 그대로 돌려준다(6절 1번).

설계 2절·4.3·6.1, R15·R16. 본보기는 기존 `get_visit_settings`·`update_visit_settings` 슬라이스다. 조회는 설정 행을 만들지 않는다. 수정은 `ensure` 로 행을 준비한 뒤 쓴다 — 알림장 설정을 처음 저장하는 매장에는 일정 설정 행과 기본 메뉴가 함께 생긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_get_report_settings_router.py`:

```python
from visit.adapter.inbound.api.v1.get_report_settings_router import get_report_settings_router
from visit.dependencies.get_report_settings_provider import get_get_report_settings_use_case
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS
from visit.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_직원도_알림장_설정을_본다():
    stub = Recorder(DEFAULT_REPORT_SETTINGS)
    async with client(build_app(get_report_settings_router, get_get_report_settings_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/report-settings")
    assert response.status_code == 200
    assert response.json() == {"link_days": 30, "show_menus": True, "show_shop_info": True,
                               "show_weight": False, "show_amount": False}
    assert stub.calls[0].ctx.shop_id == 3
```

`backend/apps/visit/tests/adapter/test_report_settings_pg_repository.py`:

```python
import pytest
from sqlalchemy import text

from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)
WEEK = ReportSettings(link_days=7, show_menus=False, show_shop_info=False, show_weight=True, show_amount=True)
FOREVER = ReportSettings(link_days=None, show_menus=True, show_shop_info=False, show_weight=False, show_amount=True)


async def _row_count(session) -> int:
    return (await session.execute(text("SELECT count(*) FROM visit_shop_settings"))).scalar_one()


async def test_설정_행이_없으면_기본값을_주고_행을_만들지_않는다(db_session):
    assert await ReportSettingsPgRepository(db_session).get(A) == DEFAULT_REPORT_SETTINGS
    assert await _row_count(db_session) == 0


async def test_일정_설정이_만든_행은_알림장_기본값을_갖는다(db_session):
    await SchedulePgRepository(db_session).ensure(A)
    assert await ReportSettingsPgRepository(db_session).get(A) == DEFAULT_REPORT_SETTINGS


@pytest.mark.parametrize("settings", [WEEK, FOREVER])
async def test_바꾼_설정을_돌려주고_다시_읽어도_같다(db_session, settings):
    repo = ReportSettingsPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    assert await repo.update(A, settings) == settings
    assert await repo.get(A) == settings


async def test_다시_바꾸면_나중_것이_남는다(db_session):
    repo = ReportSettingsPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    await repo.update(A, WEEK)
    await repo.update(A, FOREVER)
    assert await repo.get(A) == FOREVER


async def test_알림장_설정을_바꿔도_일정_설정은_그대로다(db_session):
    schedule = SchedulePgRepository(db_session)
    before = await schedule.ensure(A)
    await ReportSettingsPgRepository(db_session).update(A, WEEK)
    assert await schedule.ensure(A) == before


async def test_매장마다_따로다(db_session):
    repo = ReportSettingsPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    await repo.update(A, WEEK)
    assert await repo.get(B) == DEFAULT_REPORT_SETTINGS   # B 는 행이 없다
    await SchedulePgRepository(db_session).ensure(B)
    await repo.update(B, FOREVER)
    assert (await repo.get(A), await repo.get(B)) == (WEEK, FOREVER)
```

`backend/apps/visit/tests/adapter/test_update_report_settings_router.py`:

```python
import pytest

from visit.adapter.inbound.api.v1.update_report_settings_router import update_report_settings_router
from visit.dependencies.update_report_settings_provider import get_update_report_settings_use_case
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

BODY = {"link_days": 7, "show_menus": False, "show_shop_info": True, "show_weight": True, "show_amount": False}
FLAGS = ("show_menus", "show_shop_info", "show_weight", "show_amount")


def _without(key: str) -> dict:
    return {k: v for k, v in BODY.items() if k != key}


def _app(stub, access=None):
    return build_app(update_report_settings_router, get_update_report_settings_use_case, stub, access)


@pytest.mark.parametrize("link_days", [7, 30, None])
async def test_사장은_알림장_설정을_바꾼다(link_days):
    saved = ReportSettings(**{**BODY, "link_days": link_days})
    stub = Recorder(saved)
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/report-settings", json={**BODY, "link_days": link_days})
    assert (response.status_code, response.json()) == (200, {**BODY, "link_days": link_days})
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].settings) == (3, saved)


async def test_직원은_알림장_설정을_바꾸지_못한다():
    """R16 — 알림장 설정은 shop:update(사장만)."""
    stub = Recorder(ReportSettings(**BODY))
    async with client(_app(stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/report-settings", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "link_days": days} for days in (0, 1, 8, 31, -7, 365, "30", "7", 30.5, True, [30])),
    _without("link_days"),
    *({**BODY, flag: value} for flag in FLAGS for value in ("true", 1, 0, None)),
    *(_without(flag) for flag in FLAGS),
    [],
    [BODY],
    {},
    "문자열",
    None,
], ids=str)
async def test_고를_수_없는_기간과_불리언이_아닌_값과_빠진_칸은_422_다(bad):
    """R15"""
    stub = Recorder(ReportSettings(**BODY))
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/report-settings", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert stub.calls == []
```

`backend/apps/visit/tests/app/use_cases/test_get_report_settings_interactor.py`:

```python
from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.app.use_cases.get_report_settings_interactor import GetReportSettingsInteractor
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeReportSettingsRepository

WEEK = ReportSettings(link_days=7, show_menus=False, show_shop_info=True, show_weight=True, show_amount=False)


async def test_정한_적이_없는_매장은_기본값을_본다():
    settings = FakeReportSettingsRepository()
    found = await GetReportSettingsInteractor(settings).get_report_settings(GetReportSettingsQuery(ctx=ctx()))
    assert found == DEFAULT_REPORT_SETTINGS
    assert settings.journal == []   # 조회는 아무것도 쓰지 않는다


async def test_조회는_그_매장이_정한_설정을_준다():
    settings = FakeReportSettingsRepository()
    settings.rows[2] = WEEK
    interactor = GetReportSettingsInteractor(settings)
    assert await interactor.get_report_settings(GetReportSettingsQuery(ctx=ctx(shop_id=2))) == WEEK
    assert await interactor.get_report_settings(GetReportSettingsQuery(ctx=ctx(shop_id=1))) == DEFAULT_REPORT_SETTINGS
```

`backend/apps/visit/tests/app/use_cases/test_update_report_settings_interactor.py`:

```python
import pytest

from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.app.use_cases.update_report_settings_interactor import UpdateReportSettingsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeReportSettingsRepository, FakeSchedule, Journal


def _settings(link_days) -> ReportSettings:
    return ReportSettings(link_days=link_days, show_menus=False, show_shop_info=True, show_weight=True,
                          show_amount=False)


def _interactor(journal: Journal):
    settings = FakeReportSettingsRepository(journal)
    return UpdateReportSettingsInteractor(schedule=FakeSchedule(journal), settings=settings), settings


@pytest.mark.parametrize("link_days", [7, 30, None])
async def test_수정은_설정_행을_준비한_뒤_바꾼다(link_days):
    journal = Journal()
    interactor, settings = _interactor(journal)
    changed = await interactor.update_report_settings(
        UpdateReportSettingsCommand(ctx=ctx(), settings=_settings(link_days)))
    assert changed == _settings(link_days) == settings.rows[1]
    assert journal == [("ensure", 1), ("update_report_settings", 1)]


@pytest.mark.parametrize("link_days", [0, 1, 8, 31, -7, 365])
async def test_고를_수_없는_기간이면_쓰지_않는다(link_days):
    journal = Journal()
    interactor, _ = _interactor(journal)
    with pytest.raises(VisitInputError):
        await interactor.update_report_settings(
            UpdateReportSettingsCommand(ctx=ctx(), settings=_settings(link_days)))
    assert journal == []
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:

```diff
@@ -16,6 +16,6 @@ async def test_자기소개는_묶음의_경로와_권한을_적는다():
     assert (result.id, result.name) == (5, "방문 (visit)")
     for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위",
                   "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT",
-                  "POST /visits/{visit_id}/record/media", "record:delete"):
+                  "POST /visits/{visit_id}/record/media", "record:delete", "GET·PUT /report-settings"):
         assert words in result.introduction
     assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -24,6 +24,7 @@ from visit.app.dtos.report_target_dto import ReportTarget
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.public_report_repository import PublicReportRepository
 from visit.app.ports.output.report_repository import ReportRepository
+from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.ports.output.visit_feed_repository import FeedPage, VisitFeedRepository
@@ -44,6 +45,7 @@ from visit.domain.errors import (
 from visit.domain.services.report_rules import hide
 from visit.domain.state.visit_status import STARTED_STATUSES
 from visit.domain.value_objects.closed_date import ClosedDate
+from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
 from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
 from visit.tests.helpers.builders import kst
 
@@ -461,6 +463,22 @@ class FakeReportRepository(ReportRepository, PublicReportRepository):
         self.journal.append(("mark_report_viewed", report_id))
 
 
+class FakeReportSettingsRepository(ReportSettingsRepository):
+    """rows 는 매장 ID → 설정. 없는 매장은 기본값이다."""
+
+    def __init__(self, journal: Journal | None = None) -> None:
+        self.journal = journal if journal is not None else Journal()
+        self.rows: dict[int, ReportSettings] = {}
+
+    async def get(self, ctx):
+        return self.rows.get(ctx.shop_id, DEFAULT_REPORT_SETTINGS)
+
+    async def update(self, ctx, settings):
+        self.journal.append(("update_report_settings", ctx.shop_id))
+        self.rows[ctx.shop_id] = settings
+        return settings
+
+
 class FakeLibrary(MediaLibraryPort):
     """MediaLibraryPort 스텁 — 실제 구현(media)과 같은 허브 오류를 같은 조건에서 던진다.
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -4,6 +4,7 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.public_report_repository import PublicReportRepository
 from visit.app.ports.output.report_repository import ReportRepository
+from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
@@ -18,6 +19,7 @@ from visit.tests.helpers.fakes import (
     FakeMenus,
     FakeRecords,
     FakeReportRepository,
+    FakeReportSettingsRepository,
     FakeSchedule,
     FakeVisits,
 )
@@ -35,3 +37,4 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     assert isinstance(FakeRecords(visits), VisitRecordRepository)
     reports = FakeReportRepository(visits)
     assert isinstance(reports, ReportRepository) and isinstance(reports, PublicReportRepository)
+    assert isinstance(FakeReportSettingsRepository(), ReportSettingsRepository)
```

`backend/tests/integration/test_report_settings_wiring.py`:

```python
"""알림장 설정을 실제 배선(프로바이더·DB 커밋·매장 접근 확인)으로 확인한다."""
import pytest

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

DEFAULT = {"link_days": 30, "show_menus": True, "show_shop_info": True, "show_weight": False, "show_amount": False}
CHANGED = {"link_days": None, "show_menus": False, "show_shop_info": True, "show_weight": True, "show_amount": True}


async def test_사장이_바꾼_알림장_설정을_직원도_보지만_직원은_바꾸지_못한다(wired):
    """R16. 사장의 PUT 이 이 매장의 첫 요청이다 — 설정 행이 없는 매장에서도 바뀐다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    o, s = bearer(owner["access_token"]), bearer(staff["access_token"])
    path = f"/v1/shops/{shop_id}/report-settings"

    changed = await wired.api.put(path, json=CHANGED, headers=o)
    assert (changed.status_code, changed.json()) == (200, CHANGED)

    assert error_of(await wired.api.put(path, json=DEFAULT, headers=s)) == (403, "PERMISSION_DENIED")
    seen = await wired.api.get(path, headers=s)
    assert (seen.status_code, seen.json()) == (200, CHANGED)
    assert error_of(await wired.api.put(path, json={**CHANGED, "link_days": 8}, headers=o)) == (
        422, "VALIDATION_ERROR")
    assert (await wired.api.get(path, headers=o)).json() == CHANGED


async def test_다른_매장의_알림장_설정은_보지도_바꾸지도_못한다(wired):
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    assert (await wired.api.put(f"/v1/shops/{a_shop}/report-settings", json=CHANGED, headers=a)).status_code == 200

    their_shop = [
        await wired.api.get(f"/v1/shops/{b_shop}/report-settings", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/report-settings", json=CHANGED, headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * 2
    # 설정을 정한 적이 없는 B 매장은 기본값이고, 조회만으로는 설정 행이 생기지 않는다.
    assert (await wired.api.get(f"/v1/shops/{b_shop}/report-settings", headers=b)).json() == DEFAULT
    async with wired.engine.connect() as conn:
        shops = (await conn.exec_driver_sql("SELECT shop_id FROM visit_shop_settings")).scalars().all()
    assert shops == [a_shop]
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

명령(`infra/`):
`docker compose run --rm backend pytest apps/visit/tests/app/use_cases/test_get_report_settings_interactor.py apps/visit/tests/app/use_cases/test_update_report_settings_interactor.py apps/visit/tests/adapter/test_get_report_settings_router.py apps/visit/tests/adapter/test_update_report_settings_router.py apps/visit/tests/adapter/test_report_settings_pg_repository.py tests/integration/test_report_settings_wiring.py apps/visit/tests/test_fakes_are_ports.py apps/visit/tests/app/use_cases/test_visit_myself_interactor.py -q -p no:cacheprovider`

결과: `6 errors in 0.13s` — 수집 오류 여섯에서 멈췄다. 예:
`ModuleNotFoundError: No module named 'visit.adapter.outbound.pg.report_settings_pg_repository'`,
`ModuleNotFoundError: No module named 'visit.app.ports.output.report_settings_repository'`.

수집에서 멈췄기 때문에 배선 테스트 둘과 자기소개 테스트가 따로 실패하는 모습은 보지 못했다. 배선 테스트는 변이 12(라우터 미등록)로 실패를 확인했다. 자기소개 테스트는 변이로 확인하지 않았다(7절).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/ports/output/report_settings_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.report_settings import ReportSettings


class ReportSettingsRepository(ABC):
    """매장의 알림장 설정. 일정 설정과 같은 행(visit_shop_settings)의 다른 칸이다."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> ReportSettings:
        """설정 행이 없으면 기본값을 돌려준다. 행을 만들지 않는다(공개 조회도 이것을 부른다)."""

    @abstractmethod
    async def update(self, ctx: ShopContext, settings: ReportSettings) -> ReportSettings:
        """통째로 바꾼다. 설정 행이 이미 있어야 한다(ScheduleRepository.ensure 뒤에 부른다)."""
```

`backend/apps/visit/adapter/outbound/pg/report_settings_pg_repository.py`:

```python
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import VisitShopSettingsOrm
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings

# ReportSettings 의 필드 순서와 같다.
_COLUMNS = (
    VisitShopSettingsOrm.report_link_days,
    VisitShopSettingsOrm.report_show_menus,
    VisitShopSettingsOrm.report_show_shop_info,
    VisitShopSettingsOrm.report_show_weight,
    VisitShopSettingsOrm.report_show_amount,
)


class ReportSettingsPgRepository(ReportSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> ReportSettings:
        row = (
            await self._session.execute(
                select(*_COLUMNS).where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
            )
        ).one_or_none()
        return DEFAULT_REPORT_SETTINGS if row is None else ReportSettings(*row)

    async def update(self, ctx: ShopContext, settings: ReportSettings) -> ReportSettings:
        row = (
            await self._session.execute(
                update(VisitShopSettingsOrm)
                .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
                .values(
                    report_link_days=settings.link_days,
                    report_show_menus=settings.show_menus,
                    report_show_shop_info=settings.show_shop_info,
                    report_show_weight=settings.show_weight,
                    report_show_amount=settings.show_amount,
                )
                .returning(*_COLUMNS)
            )
        ).one()
        return ReportSettings(*row)
```

`backend/apps/visit/dependencies/visit_wiring.py`:

```diff
@@ -5,10 +5,12 @@ from sqlalchemy.ext.asyncio import AsyncSession
 
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
+from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 
@@ -33,3 +35,7 @@ def build_record_repository(db: AsyncSession) -> VisitRecordRepository:
 def build_report_repository(db: AsyncSession) -> ReportPgRepository:
     """visit_reports 표의 리포지토리 하나. 매장 범위 포트와 공개 조회 포트를 다 구현한다."""
     return ReportPgRepository(db)
+
+
+def build_report_settings_repository(db: AsyncSession) -> ReportSettingsRepository:
+    return ReportSettingsPgRepository(db)
```

`backend/apps/visit/adapter/inbound/api/schemas/get_report_settings_schema.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

from visit.domain.value_objects.report_settings import ReportSettings


class ReportSettingsSchema(BaseModel):
    link_days: int | None   # 7·30, null 이면 무기한
    show_menus: bool
    show_shop_info: bool
    show_weight: bool
    show_amount: bool

    @classmethod
    def of(cls, settings: ReportSettings) -> ReportSettingsSchema:
        return cls(link_days=settings.link_days, show_menus=settings.show_menus,
                   show_shop_info=settings.show_shop_info, show_weight=settings.show_weight,
                   show_amount=settings.show_amount)
```

`backend/apps/visit/adapter/inbound/api/schemas/update_report_settings_schema.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, StrictBool

from visit.domain.value_objects.report_settings import ReportSettings


class UpdateReportSettingsRequestSchema(BaseModel):
    """다섯 칸 모두 필수다(전체 교체). 무기한은 link_days 에 null 을 적어 보낸다."""

    link_days: Literal[7, 30] | None
    show_menus: StrictBool
    show_shop_info: StrictBool
    show_weight: StrictBool
    show_amount: StrictBool

    def to_settings(self) -> ReportSettings:
        return ReportSettings(
            link_days=self.link_days, show_menus=self.show_menus, show_shop_info=self.show_shop_info,
            show_weight=self.show_weight, show_amount=self.show_amount,
        )
```

`backend/apps/visit/adapter/inbound/api/v1/get_report_settings_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_report_settings_schema import ReportSettingsSchema
from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.app.ports.input.get_report_settings_use_case import GetReportSettingsUseCase
from visit.dependencies.get_report_settings_provider import get_get_report_settings_use_case

get_report_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_report_settings_router.get("/{shop_id}/report-settings", response_model=ReportSettingsSchema)
async def get_report_settings(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetReportSettingsUseCase = Depends(get_get_report_settings_use_case),
) -> ReportSettingsSchema:
    return ReportSettingsSchema.of(await use_case.get_report_settings(GetReportSettingsQuery(ctx=ctx)))
```

`backend/apps/visit/adapter/inbound/api/v1/update_report_settings_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_report_settings_schema import ReportSettingsSchema
from visit.adapter.inbound.api.schemas.update_report_settings_schema import (
    UpdateReportSettingsRequestSchema,
)
from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.app.ports.input.update_report_settings_use_case import UpdateReportSettingsUseCase
from visit.dependencies.update_report_settings_provider import get_update_report_settings_use_case

update_report_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_report_settings_router.put("/{shop_id}/report-settings", response_model=ReportSettingsSchema)
async def update_report_settings(
    body: UpdateReportSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateReportSettingsUseCase = Depends(get_update_report_settings_use_case),
) -> ReportSettingsSchema:
    settings = await use_case.update_report_settings(
        UpdateReportSettingsCommand(ctx=ctx, settings=body.to_settings())
    )
    return ReportSettingsSchema.of(settings)
```

`backend/apps/visit/app/dtos/get_report_settings_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetReportSettingsQuery:
    ctx: ShopContext
```

`backend/apps/visit/app/dtos/update_report_settings_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.report_settings import ReportSettings


@dataclass(frozen=True)
class UpdateReportSettingsCommand:
    """알림장 설정 전체를 바꾼다(PUT)."""

    ctx: ShopContext
    settings: ReportSettings
```

`backend/apps/visit/app/ports/input/get_report_settings_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.domain.value_objects.report_settings import ReportSettings


class GetReportSettingsUseCase(ABC):
    @abstractmethod
    async def get_report_settings(self, query: GetReportSettingsQuery) -> ReportSettings: ...
```

`backend/apps/visit/app/ports/input/update_report_settings_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.domain.value_objects.report_settings import ReportSettings


class UpdateReportSettingsUseCase(ABC):
    @abstractmethod
    async def update_report_settings(self, command: UpdateReportSettingsCommand) -> ReportSettings: ...
```

`backend/apps/visit/app/use_cases/get_report_settings_interactor.py`:

```python
from __future__ import annotations

from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.app.ports.input.get_report_settings_use_case import GetReportSettingsUseCase
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.domain.value_objects.report_settings import ReportSettings


class GetReportSettingsInteractor(GetReportSettingsUseCase):
    """정한 적이 없는 매장은 기본값을 본다. 조회는 설정 행을 만들지 않는다."""

    def __init__(self, settings: ReportSettingsRepository) -> None:
        self._settings = settings

    async def get_report_settings(self, query: GetReportSettingsQuery) -> ReportSettings:
        return await self._settings.get(query.ctx)
```

`backend/apps/visit/app/use_cases/update_report_settings_interactor.py`:

```python
from __future__ import annotations

from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.app.ports.input.update_report_settings_use_case import UpdateReportSettingsUseCase
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.services.report_rules import check_settings
from visit.domain.value_objects.report_settings import ReportSettings


class UpdateReportSettingsInteractor(UpdateReportSettingsUseCase):
    """링크 기간과 보여 줄 항목을 바꾼다. 이미 보낸 링크의 기간은 그대로고, 보여 줄 항목은 바로 적용된다."""

    def __init__(self, schedule: ScheduleRepository, settings: ReportSettingsRepository) -> None:
        self._schedule = schedule
        self._settings = settings

    async def update_report_settings(self, command: UpdateReportSettingsCommand) -> ReportSettings:
        check_settings(command.settings)
        await self._schedule.ensure(command.ctx)   # 설정 행은 일정 설정과 함께 쓴다 — 없으면 여기서 생긴다
        return await self._settings.update(command.ctx, command.settings)
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -44,7 +44,9 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}(이름·기본 소요·순서·정가 price, "
                 "원 단위, 비우면 가격 미정), "
                 "POST /menus/{menu_id}/archive(메뉴표 — 지우지 않고 보관)도 있습니다. "
-                "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴 수정은 shop:update(사장)가 필요합니다. "
+                "GET·PUT /report-settings 는 알림장 설정입니다(링크 기간 link_days 7·30·null(계속), 보호자에게 보여 줄 "
+                "항목 show_menus·show_shop_info·show_weight·show_amount — PUT 은 다섯 칸 전체 교체). "
+                "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴·알림장 설정 수정은 shop:update(사장)가 필요합니다. "
                 "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                 "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
                 "다른 매장의 방문·메뉴 ID 는 404 입니다."
```

`backend/apps/visit/dependencies/get_report_settings_provider.py`:

```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_report_settings_use_case import GetReportSettingsUseCase
from visit.app.use_cases.get_report_settings_interactor import GetReportSettingsInteractor
from visit.dependencies.visit_wiring import build_report_settings_repository


def get_get_report_settings_use_case(db: DbSession) -> GetReportSettingsUseCase:
    return GetReportSettingsInteractor(settings=build_report_settings_repository(db))
```

`backend/apps/visit/dependencies/update_report_settings_provider.py`:

```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_report_settings_use_case import UpdateReportSettingsUseCase
from visit.app.use_cases.update_report_settings_interactor import UpdateReportSettingsInteractor
from visit.dependencies.visit_wiring import build_report_settings_repository, build_schedule_repository


def get_update_report_settings_use_case(db: DbSession) -> UpdateReportSettingsUseCase:
    return UpdateReportSettingsInteractor(
        schedule=build_schedule_repository(db), settings=build_report_settings_repository(db)
    )
```

`backend/main.py`:

```diff
@@ -71,6 +71,7 @@ from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
 from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
 from visit.adapter.inbound.api.v1.delete_visit_record_router import delete_visit_record_router
 from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_visit_draft_router
+from visit.adapter.inbound.api.v1.get_report_settings_router import get_report_settings_router
 from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
 from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
 from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
@@ -86,6 +87,7 @@ from visit.adapter.inbound.api.v1.register_visit_router import register_visit_ro
 from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
 from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
 from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
+from visit.adapter.inbound.api.v1.update_report_settings_router import update_report_settings_router
 from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
@@ -138,6 +140,8 @@ app.include_router(delete_pet_router)
 # visit
 app.include_router(get_visit_settings_router)
 app.include_router(update_visit_settings_router)
+app.include_router(get_report_settings_router)
+app.include_router(update_report_settings_router)
 app.include_router(list_closed_dates_router)
 app.include_router(add_closed_date_router)
 app.include_router(delete_closed_date_router)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 테스트 여덟 파일 | 64 passed (새로 더한 것 62 — 인터랙터 11, 라우터 42, 저장소 7, 배선 2. 나머지 2는 기존 스텁 포트 1·자기소개 1) |
| 단위 전체 | 1069 passed, 347 deselected (시작 1016 → +53) |
| 통합 전체 | 347 passed, 1069 deselected (시작 338 → +9) |
| 구조 계약 | 6 kept, 0 broken |
| `tests/test_hub_port_binding.py`·`tests/integration/test_route_wiring.py`·`tests/test_schema_drift.py` | 9 passed |

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- PUT 라우터의 `require_permission("shop:update")` → `get_shop_context` → `test_직원은_알림장_설정을_바꾸지_못한다`(라우터), `test_사장이_바꾼_알림장_설정을_직원도_보지만_직원은_바꾸지_못한다`(배선)
- 요청 스키마의 `StrictBool` 넷 → `bool` → `test_고를_수_없는_기간과_불리언이_아닌_값과_빠진_칸은_422_다` 의 12개 — 네 칸 × (`"true"`, `1`, `0`). `null` 과 빠진 칸은 `bool` 로도 422 라 통과
- `ReportSettingsPgRepository.get` 의 매장 조건 제거 → `test_매장마다_따로다`(저장소), `test_다른_매장의_알림장_설정은_보지도_바꾸지도_못한다`(배선)
- `UpdateReportSettingsInteractor` 의 `schedule.ensure` 제거 → `test_수정은_설정_행을_준비한_뒤_바꾼다[7]`·`[30]`·`[None]`(인터랙터), 배선 테스트 둘(설정 행이 없는 매장의 PUT. 어떤 예외로 실패했는지는 출력을 줄여 돌려 보지 못했다)
- `update` 의 매장 조건 제거 → `test_매장마다_따로다`
- 인터랙터의 `check_settings` 제거 → `test_고를_수_없는_기간이면_쓰지_않는다[0·1·8·31·-7·365]`
- 스키마 `link_days` 에 기본값 `= None` → 422 테스트의 `link_days` 빠진 본문 하나
- 스키마 `link_days` 를 `int \ → None` 으로 | 422 테스트 9개 — `0·1·8·31·-7·365·"30"·"7"·True`
- GET 라우터의 가드를 `require_permission("shop:update")` 로 → `test_직원도_알림장_설정을_본다`, 배선 첫 테스트
- `update` 가 몸무게와 금액 칸을 바꿔 쓴다 → `test_바꾼_설정을_돌려주고_다시_읽어도_같다[settings1]`, `test_다시_바꾸면_나중_것이_남는다`, `test_매장마다_따로다`
- `to_settings` 가 메뉴와 매장 정보를 바꿔 담는다 → `test_사장은_알림장_설정을_바꾼다[7]`·`[30]`·`[None]`, 배선 첫 테스트
- `main.py` 에 라우터 둘을 등록하지 않는다 → 배선 테스트 둘
- `get` 이 언제나 기본값을 준다 → 저장소 테스트 넷, 배선 첫 테스트
- 조회 인터랙터가 `update` 를 부른다 → `test_정한_적이_없는_매장은_기본값을_본다`, `test_다른_매장의_알림장_설정은_보지도_바꾸지도_못한다`
- 응답 스키마가 몸무게와 금액을 바꿔 담는다 → `test_사장은_알림장_설정을_바꾼다[7]`·`[30]`·`[None]`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 알림장 설정 — 링크 기간과 보여 줄 항목을 매장이 정한다(GET·PUT report-settings)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 허브 포트 둘 — 매장 공개 정보(`ShopProfilePort`), 내려받기용 서명 주소(`MediaUrls.download_url`)

**Files:**
- Create: `backend/apps/hub/app/dtos/shop_profile.py`
- Create: `backend/apps/hub/app/ports/shop_profile_port.py`
- Modify: `backend/apps/hub/app/dtos/media_urls.py`
- Modify: `backend/apps/customer/tests/helpers/fakes.py`
- Modify: `backend/apps/media/adapter/outbound/s3/boto3_object_storage_adapter.py`
- Modify: `backend/apps/media/adapter/outbound/s3/sigv4_query.py`
- Modify: `backend/apps/media/app/ports/output/object_storage_port.py`
- Modify: `backend/apps/media/app/use_cases/media_library_interactor.py`
- Modify: `backend/apps/media/domain/services/media_rules.py`
- Modify: `backend/apps/media/tests/adapter/test_sigv4_query.py`
- Modify: `backend/apps/media/tests/app/use_cases/test_media_library_interactor.py`
- Modify: `backend/apps/media/tests/domain/test_media_rules.py`
- Modify: `backend/apps/media/tests/helpers/fakes.py`
- Modify: `backend/apps/tenancy/adapter/outbound/pg/shop_pg_repository.py`
- Modify: `backend/apps/tenancy/app/ports/output/shop_repository.py`
- Create: `backend/apps/tenancy/app/use_cases/get_shop_profile_interactor.py`
- Create: `backend/apps/tenancy/dependencies/get_shop_profile_provider.py`
- Create: `backend/apps/tenancy/tests/adapter/test_get_shop_profile_pg.py`
- Create: `backend/apps/tenancy/tests/app/use_cases/test_get_shop_profile_interactor.py`
- Modify: `backend/apps/visit/dependencies/hub_ports.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/integration/test_media_flow_wiring.py`
- Modify: `backend/tests/integration/test_visit_record_wiring.py`
- Modify: `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: `tenancy` 의 `ShopRepository`·`Shop`; `media` 의 `ObjectStoragePort`·`sigv4_query.presign_get_url`·`MediaLibraryInteractor.read_urls`; `hub.app.dtos.media_urls.MediaUrls`; `main.py` 의 자리 꽂기.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# hub/app/dtos/shop_profile.py
@dataclass(frozen=True)
class ShopProfile:
    shop_id: int
    name: str
    phone: str | None
    address: str | None
    timezone: str
    open: bool

# hub/app/ports/shop_profile_port.py
class ShopProfilePort(ABC):
    @abstractmethod
    async def public_profile(self, shop_id: int) -> ShopProfile | None

# visit/dependencies/hub_ports.py
def get_shop_profile() -> ShopProfilePort          # 부르면 RuntimeError. main.py 가 채운다

# tenancy/dependencies/get_shop_profile_provider.py
def get_shop_profile_use_case(db: DbSession) -> ShopProfilePort

# tenancy/app/use_cases/get_shop_profile_interactor.py
class GetShopProfileInteractor(ShopProfilePort):
    def __init__(self, shops: ShopRepository) -> None

# tenancy/app/ports/output/shop_repository.py (더한 메서드)
async def find_by_id(self, shop_id: int) -> Shop | None

# visit/tests/helpers/fakes.py
class FakeShopProfile(ShopProfilePort):
    def __init__(self, shops: dict[int, ShopProfile] | None = None) -> None    # self.shops 에 넣고 뺀다
    async def public_profile(self, shop_id)                                    # 없으면 None

# hub/app/dtos/media_urls.py — 칸 순서
MediaUrls(media_id, kind, original_url, download_url, display_url, thumb_url, width, height, duration_seconds)

# media/app/ports/output/object_storage_port.py
def presign_get(self, key: str, window: SigningWindow, download_as: str | None = None) -> str

# media/adapter/outbound/s3/sigv4_query.py
def presign_get_url(endpoint, bucket, key, region, access_key, secret_key,
                    signed_at: datetime, expires_in_seconds: int, content_disposition: str | None = None) -> str

# media/domain/services/media_rules.py
def download_name(media_id: int, kind: str) -> str      # "chagocnote-{media_id}.jpg" / ".mp4"
```

뒤 작업이 알아 둘 동작
- **`public_profile` 은 정지·폐업한 매장도 돌려준다.** `None` 은 없는 매장뿐이다. 410 을 낼지는 쓰는 쪽이 `open` 을 보고 정한다(R21).
- `public_profile` 은 잠그지 않고 권한도 보지 않는다. 매장 ID 만 알면 이름·전화·주소가 나오므로, 서명을 확인한 링크에서 읽은 매장 ID 로만 불러야 한다.
- `phone`·`address` 는 DB 의 null 이 그대로 `None` 이다. 빈 문자열은 매장 수정 라우터가 저장 전에 null 로 바꾸므로 DB 에 없다.
- **`MediaUrls` 는 위치 인자가 아니라 이름 인자로 만든다.** `download_url` 이 `original_url` 바로 뒤에 들어가서 위치로 만들던 코드는 칸이 밀린다(지금 저장소에는 그런 곳이 없다 — 세 곳 모두 이름 인자다).
- `download_url` 은 영상에도 있다(`.mp4`). 서명 창은 다른 주소와 같아 하루 동안 글자까지 같다.
- 스텁의 `download_url` 은 visit·customer 모두 `f"dl/{i}"` 다. media 의 `FakeStorage.presign_get` 은 이름을 주면 끝에 `&download={이름}` 을 붙인다.
- 내려받기 주소의 모양: 질의 문자열의 맨 앞에 `response-content-disposition=`(값은 퍼센트 인코딩), 그 뒤에 기존 `X-Amz-*` 다섯, 맨 끝에 `X-Amz-Signature`. 서명에 들어가므로 파일 이름만 바꿔 치면 저장소가 403 을 준다.
- 기존 API 응답(기록의 미디어)에는 `download_url` 이 없다. `test_visit_record_wiring.py` 의 한 줄이 이를 고정한다.

설계 3.4, R21. 스포크끼리 import 하지 않는다 — visit 은 허브의 포트와 DTO 만 알고 `main.py` 가 tenancy 의 구현을 꽂는다. 내려받기 서명은 같은 시각에 botocore 가 만든 URL 과 글자까지 같아야 한다. `MediaUrls` 는 이름 인자로 만든다(`download_url` 이 `original_url` 바로 뒤에 들어간다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/helpers/fakes.py`:

```diff
@@ -252,8 +252,9 @@ class FakeLibrary(MediaLibraryPort):
         raise AssertionError("customer 는 미디어를 놓지 않는다")
 
     async def read_urls(self, ctx, media_ids):
-        return {i: MediaUrls(media_id=i, kind="photo", original_url=f"o/{i}", display_url=f"d/{i}", thumb_url=f"t/{i}",
-                             width=3000, height=2000, duration_seconds=None) for i in media_ids if i in self.ready}
+        return {i: MediaUrls(media_id=i, kind="photo", original_url=f"o/{i}", download_url=f"dl/{i}",
+                             display_url=f"d/{i}", thumb_url=f"t/{i}", width=3000, height=2000,
+                             duration_seconds=None) for i in media_ids if i in self.ready}
 
 
 def family():
```

`backend/apps/media/tests/adapter/test_sigv4_query.py`:

```diff
@@ -10,18 +10,21 @@ from media.adapter.outbound.s3.sigv4_query import presign_get_url
 SIGNED_AT = datetime(2026, 9, 23, 19, 0, tzinfo=timezone.utc)   # 서울 04:00
 
 
-def _botocore_url(monkeypatch, endpoint, key):
+DOWNLOAD = 'attachment; filename="chagocnote-42.jpg"'
+
+
+def _botocore_url(monkeypatch, endpoint, key, **params):
     monkeypatch.setattr(botocore.auth, "get_current_datetime", lambda: SIGNED_AT)
     client = boto3.client("s3", endpoint_url=endpoint, region_name="ap-northeast-2", aws_access_key_id="AKIDEXAMPLE",
                           aws_secret_access_key="secret/key+value",
                           config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
-    return client.generate_presigned_url("get_object", Params={"Bucket": "chagocnote-media", "Key": key},
+    return client.generate_presigned_url("get_object", Params={"Bucket": "chagocnote-media", "Key": key, **params},
                                          ExpiresIn=172800)
 
 
-def _ours(endpoint, key):
+def _ours(endpoint, key, content_disposition=None):
     return presign_get_url(endpoint, "chagocnote-media", key, "ap-northeast-2", "AKIDEXAMPLE", "secret/key+value",
-                           SIGNED_AT, 172800)
+                           SIGNED_AT, 172800, content_disposition)
 
 
 def test_botocore_와_같은_URL_이다(monkeypatch):
@@ -32,3 +35,18 @@ def test_botocore_와_같은_URL_이다(monkeypatch):
 
 def test_같은_창이면_같은_URL_이다():
     assert _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg") == _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg")
+
+
+def test_내려받기_서명도_botocore_와_같은_URL_이다(monkeypatch):
+    for endpoint in ("https://s3.ap-northeast-2.amazonaws.com", "http://127.0.0.1:9010"):
+        ours = _ours(endpoint, "original/shops/1/42.jpg", DOWNLOAD)
+        assert ours == _botocore_url(monkeypatch, endpoint, "original/shops/1/42.jpg",
+                                     ResponseContentDisposition=DOWNLOAD), endpoint
+        # 공백은 %20, 세미콜론·등호·따옴표도 인코딩한다(RFC 3986).
+        assert "response-content-disposition=attachment%3B%20filename%3D%22chagocnote-42.jpg%22" in ours
+
+
+def test_내려받기_서명은_읽기_서명과_다르다():
+    plain = _ours("http://127.0.0.1:9010", "original/shops/1/42.jpg")
+    download = _ours("http://127.0.0.1:9010", "original/shops/1/42.jpg", DOWNLOAD)
+    assert plain.rsplit("=", 1)[1] != download.rsplit("=", 1)[1]
```

`backend/apps/media/tests/app/use_cases/test_media_library_interactor.py`:

```diff
@@ -68,6 +68,17 @@ async def test_읽기_URL_은_준비된_것만_매장_시간대의_하루_창으
     assert urls[video.id].original_url == f"get://original-video/shops/1/{video.id}.mp4?signed=20260923T1900"
 
 
+async def test_내려받기_URL_은_원본을_첨부_파일_이름과_함께_서명한다():
+    library, media = _library()
+    photo, video = media.seed(status="ready"), media.seed(kind="video", status="ready")
+    urls = await library.read_urls(ctx(), [photo.id, video.id])
+    assert urls[photo.id].download_url == (
+        f"get://original/shops/1/{photo.id}.jpg?signed=20260923T1900&download=chagocnote-{photo.id}.jpg")
+    assert urls[video.id].download_url == (
+        f"get://original-video/shops/1/{video.id}.mp4?signed=20260923T1900&download=chagocnote-{video.id}.mp4")
+    assert "download" not in urls[photo.id].original_url + urls[photo.id].display_url + urls[photo.id].thumb_url
+
+
 async def test_다른_매장의_미디어는_URL_이_없다():
     library, media = _library()
     photo = media.seed(shop_id=2, status="ready")
```

`backend/apps/media/tests/domain/test_media_rules.py`:

```diff
@@ -1,7 +1,7 @@
 import pytest
 
 from media.domain.errors import MediaInputError, MediaTooLargeError, MediaTypeUnsupportedError
-from media.domain.services.media_rules import MAX_BYTES, check_upload, object_keys
+from media.domain.services.media_rules import MAX_BYTES, check_upload, download_name, object_keys
 
 MB = 1024 * 1024
 
@@ -48,3 +48,8 @@ def test_가로세로와_길이의_경계(kind, width, height, duration):
     content_type = "image/jpeg" if kind == "photo" else "video/mp4"
     with pytest.raises(MediaInputError):
         check_upload(kind, content_type, 1000, width, height, duration)
+
+
+def test_내려받는_파일_이름은_서비스_이름과_ID_와_확장자뿐이다():
+    assert download_name(42, "photo") == "chagocnote-42.jpg"
+    assert download_name(9007199254740993, "video") == "chagocnote-9007199254740993.mp4"
```

`backend/apps/media/tests/helpers/fakes.py`:

```diff
@@ -90,8 +90,9 @@ class FakeStorage(ObjectStoragePort):
     def presign_put(self, key, content_type, expires_in_seconds):
         return f"put://{key}?type={content_type}&expires={expires_in_seconds}"
 
-    def presign_get(self, key, window):
-        return f"get://{key}?signed={window.signed_at:%Y%m%dT%H%M}"
+    def presign_get(self, key, window, download_as=None):
+        download = f"&download={download_as}" if download_as else ""
+        return f"get://{key}?signed={window.signed_at:%Y%m%dT%H%M}{download}"
 
     async def head(self, key):
         self.journal.append(("head", key))
```

`backend/apps/tenancy/tests/adapter/test_get_shop_profile_pg.py`:

```python
"""실제 리포지토리로 도는 매장 공개 정보 — 로그인한 사용자 없이 매장 ID 만으로 읽는다."""
import pytest
from sqlalchemy import text

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.use_cases.get_shop_profile_interactor import GetShopProfileInteractor

pytestmark = pytest.mark.integration


def _ctx(shop_id):
    return ShopContext(shop_id=shop_id, member_id=0, role="owner", permissions=frozenset())


async def test_매장의_공개_정보를_읽는다(db_session):
    shops = ShopPgRepository(db_session)
    bare = await shops.create("Hiss Haus", "pet_grooming")
    full = await shops.create("다른 매장", "pet_grooming")
    await shops.update(_ctx(full.id), "다른 매장", "02-000-0000", "서울")
    port = GetShopProfileInteractor(shops)
    assert await port.public_profile(bare.id) == ShopProfile(
        shop_id=bare.id, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
    assert await port.public_profile(full.id) == ShopProfile(
        shop_id=full.id, name="다른 매장", phone="02-000-0000", address="서울", timezone="Asia/Seoul", open=True)


async def test_없는_매장이면_None_이다(db_session):
    shop = await ShopPgRepository(db_session).create("Hiss Haus", "pet_grooming")
    assert await GetShopProfileInteractor(ShopPgRepository(db_session)).public_profile(shop.id + 1) is None


@pytest.mark.parametrize("column", ["suspended_at", "closed_at"])
async def test_정지했거나_폐업한_매장은_영업_중이_아니다(db_session, column):
    shops = ShopPgRepository(db_session)
    stopped = await shops.create("멈춘 매장", "pet_grooming")
    running = await shops.create("하는 매장", "pet_grooming")
    await db_session.execute(text(f"UPDATE shops SET {column} = now() WHERE id = :id"), {"id": stopped.id})
    db_session.expire_all()
    port = GetShopProfileInteractor(shops)
    assert [(await port.public_profile(s.id)).open for s in (stopped, running)] == [False, True]
```

`backend/apps/tenancy/tests/app/use_cases/test_get_shop_profile_interactor.py`:

```python
from datetime import datetime, timezone

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from tenancy.app.use_cases.get_shop_profile_interactor import GetShopProfileInteractor
from tenancy.domain.entities.shop import Shop

WHEN = datetime(2026, 9, 28, 3, 0, tzinfo=timezone.utc)


class _StubShops:
    def __init__(self, shop):
        self.shop = shop
        self.calls = []

    async def find_by_id(self, shop_id):
        self.calls.append(shop_id)
        return self.shop


def _shop(**overrides):
    base = dict(id=3, name="Hiss Haus", business_type="pet_grooming", phone="02-000-0000", address="서울",
                timezone="Asia/Tokyo", suspended_at=None, closed_at=None)
    return Shop(**{**base, **overrides})


async def test_매장의_공개_정보를_돌려준다():
    shops = _StubShops(_shop())
    profile = await GetShopProfileInteractor(shops).public_profile(3)
    assert profile == ShopProfile(shop_id=3, name="Hiss Haus", phone="02-000-0000", address="서울",
                                  timezone="Asia/Tokyo", open=True)
    assert shops.calls == [3]


async def test_없는_매장이면_None_이다():
    assert await GetShopProfileInteractor(_StubShops(None)).public_profile(3) is None


@pytest.mark.parametrize("stopped", [
    {"suspended_at": WHEN}, {"closed_at": WHEN}, {"suspended_at": WHEN, "closed_at": WHEN},
], ids=["suspended_at", "closed_at", "both"])
async def test_정지했거나_폐업한_매장은_영업_중이_아니다(stopped):
    profile = await GetShopProfileInteractor(_StubShops(_shop(**stopped))).public_profile(3)
    assert (profile.name, profile.open) == ("Hiss Haus", False)


async def test_전화와_주소가_비면_None_이다():
    profile = await GetShopProfileInteractor(_StubShops(_shop(phone=None, address=None))).public_profile(3)
    assert (profile.phone, profile.address) == (None, None)
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -10,6 +10,7 @@ from decimal import Decimal
 
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from hub.app.dtos.media_urls import MediaUrls
+from hub.app.dtos.shop_profile import ShopProfile
 from hub.app.errors import (
     FamilyNotFoundError,
     FamilyPetNotFoundError,
@@ -20,6 +21,7 @@ from hub.app.errors import (
 )
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
+from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.app.dtos.report_target_dto import ReportTarget
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.public_report_repository import PublicReportRepository
@@ -515,8 +517,18 @@ class FakeLibrary(MediaLibraryPort):
 
     async def read_urls(self, ctx, media_ids):
         return {
-            i: MediaUrls(media_id=i, kind=self.media[i][1], original_url=f"o/{i}",
+            i: MediaUrls(media_id=i, kind=self.media[i][1], original_url=f"o/{i}", download_url=f"dl/{i}",
                          display_url=f"d/{i}" if self.media[i][1] == "photo" else None, thumb_url=f"t/{i}",
                          width=3000, height=2000, duration_seconds=None if self.media[i][1] == "photo" else 30)
             for i in media_ids if i in self.media and self.media[i][0] == ctx.shop_id and self.media[i][2]
         }
+
+
+class FakeShopProfile(ShopProfilePort):
+    """ShopProfilePort 스텁 — 매장 ID → ShopProfile 사전. 없는 매장은 None."""
+
+    def __init__(self, shops: dict[int, ShopProfile] | None = None) -> None:
+        self.shops = shops if shops is not None else {}
+
+    async def public_profile(self, shop_id):
+        return self.shops.get(shop_id)
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -1,6 +1,8 @@
 """공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
+from hub.app.dtos.shop_profile import ShopProfile
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
+from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.public_report_repository import PublicReportRepository
 from visit.app.ports.output.report_repository import ReportRepository
@@ -21,6 +23,7 @@ from visit.tests.helpers.fakes import (
     FakeReportRepository,
     FakeReportSettingsRepository,
     FakeSchedule,
+    FakeShopProfile,
     FakeVisits,
 )
 
@@ -30,6 +33,7 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     assert isinstance(FakeMenus(), MenuRepository)
     assert isinstance(FakeDirectory(), CustomerDirectoryPort)
     assert isinstance(FakeLibrary(), MediaLibraryPort)
+    assert isinstance(FakeShopProfile(), ShopProfilePort)
     visits = FakeVisits()
     for port in (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
                  VisitBoardRepository, VisitFeedRepository):
@@ -38,3 +42,9 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     reports = FakeReportRepository(visits)
     assert isinstance(reports, ReportRepository) and isinstance(reports, PublicReportRepository)
     assert isinstance(FakeReportSettingsRepository(), ReportSettingsRepository)
+
+
+async def test_매장_공개_정보_스텁은_넣어_둔_매장만_돌려준다():
+    profile = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
+    shops = FakeShopProfile({1: profile})
+    assert (await shops.public_profile(1), await shops.public_profile(2)) == (profile, None)
```

`backend/tests/integration/test_media_flow_wiring.py`:

```diff
@@ -1,8 +1,12 @@
 """미디어 발급·확인을 실제 배선(프로바이더·DB 커밋·매장 접근 확인·MinIO)으로 확인한다. 첫 테스트는 테넌트 격리다."""
 import asyncio
 
+import httpx
 import pytest
+from sqlalchemy.ext.asyncio import AsyncSession
 
+from hub.app.dtos.shop_context import ShopContext
+from media.dependencies.media_library_provider import get_media_library_use_case
 from tests.integration.support import (
     PHOTO,
     accept_invite,
@@ -10,6 +14,7 @@ from tests.integration.support import (
     error_of,
     issue_media,
     make_operator,
+    ready_photo,
     shop_with_owner,
     staff_invite,
     upload_media,
@@ -63,3 +68,18 @@ async def test_동시에_두_번_확인해도_결과가_같다(wired, media_stor
     )
     assert [(r.status_code, r.json()["status"], r.json()["size_bytes"]) for r in (first, second)] == [
         (200, "ready", 3000)] * 2
+
+
+async def test_내려받기_URL_로_받으면_첨부_파일로_내려오고_원본_URL_은_그대로다(wired, media_storage):
+    operator = await make_operator(wired)
+    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
+    media_id = await ready_photo(wired, shop_id, bearer(owner["access_token"]))
+    ctx = ShopContext(shop_id=shop_id, member_id=0, role="owner", permissions=frozenset(), timezone="Asia/Seoul")
+    async with AsyncSession(wired.engine) as session:
+        urls = (await get_media_library_use_case(session, media_storage).read_urls(ctx, [media_id]))[media_id]
+
+    async with httpx.AsyncClient() as http:
+        download, original = await http.get(urls.download_url), await http.get(urls.original_url)
+    assert (download.status_code, len(download.content)) == (200, 3000)
+    assert download.headers["content-disposition"] == f'attachment; filename="chagocnote-{media_id}.jpg"'
+    assert original.status_code == 200 and "content-disposition" not in original.headers
```

`backend/tests/integration/test_visit_record_wiring.py`:

```diff
@@ -95,6 +95,7 @@ async def test_기록을_쓰고_고치면_버전이_오르고_빠진_사진은_
     assert (saved["version"], saved["total_amount"], [i["amount"] for i in saved["items"]]) == (1, 25000, [28000])
     assert [(m["media_id"], m["phase"]) for m in saved["media"]] == [(before, "before"), (after, "after")]
     assert all(m["thumb_url"].startswith("http") for m in saved["media"])
+    assert all("download_url" not in m for m in saved["media"])   # 내려받기 주소는 공개 알림장만 쓴다
     pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=o)).json()["pet"]
     assert pet["weight_kg"] == 3.4
```

`backend/tests/test_hub_port_binding.py`:

```diff
@@ -1,16 +1,26 @@
 """API 프로세스의 라우트를 훑어 조립·가드 실수를 잡는다. 손으로 관리하는 목록은 두지 않는다."""
+import pytest
 from fastapi import Depends, FastAPI
 
 import main
 from core.shop_guard import get_shop_access_port
 from tenancy.dependencies.hub_ports import get_user_directory
+from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
 from tests.route_inspection import find_route_violations
+from visit.dependencies.hub_ports import get_shop_profile
 
 
 def test_API_프로세스에는_빈_자리도_빠진_가드도_없다():
     assert find_route_violations(main.app) == []
 
 
+def test_매장_공개_정보_자리는_tenancy_의_구현으로_채운다():
+    """쓰는 라우트가 아직 없어 위의 검사에는 걸리지 않는다."""
+    assert main.app.dependency_overrides[get_shop_profile] is get_shop_profile_use_case
+    with pytest.raises(RuntimeError):
+        get_shop_profile()
+
+
 def _app_with(path, dependency=None):
     app = FastAPI()
     deps = [Depends(dependency)] if dependency else []
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

명령은 모두 `infra/` 에서 `docker compose run --rm backend pytest <경로들> -q -p no:cacheprovider`.

첫 실행(작업 테스트 여덟 파일): `5 errors in 0.64s` — 수집 오류.
- `ModuleNotFoundError: No module named 'hub.app.dtos.shop_profile'` (tenancy 테스트 둘, visit 스텁 테스트)
- `ModuleNotFoundError: No module named 'tenancy.dependencies.get_shop_profile_provider'` (`tests/test_hub_port_binding.py`)
- `ImportError: cannot import name 'download_name' from 'media.domain.services.media_rules'`

수집되는 파일만 따로(서명·인터랙터·통합 둘): `6 failed, 18 passed in 4.15s`.
- `test_sigv4_query.py` 넷(인자가 하나 늘어난 `presign_get_url` 호출이 TypeError), `test_내려받기_URL_은_원본을_첨부_파일_이름과_함께_서명한다`, `test_내려받기_URL_로_받으면_첨부_파일로_내려오고_원본_URL_은_그대로다`(`AttributeError: 'MediaUrls' object has no attribute 'download_url'`).

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/dtos/shop_profile.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopProfile:
    """매장이 밖에 보여 주는 정보. 로그인한 사용자가 없는 자리(공개 알림장)에서 읽는다."""

    shop_id: int
    name: str
    phone: str | None
    address: str | None
    timezone: str
    open: bool                    # 정지(suspended_at)도 폐업(closed_at)도 아니다
```

`backend/apps/hub/app/ports/shop_profile_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_profile import ShopProfile


class ShopProfilePort(ABC):
    """구현: tenancy. 사용: visit(공개 알림장). 로그인한 사용자가 없는 자리에서 매장의 공개 정보를 읽는다."""

    @abstractmethod
    async def public_profile(self, shop_id: int) -> ShopProfile | None:
        """없는 매장이면 None. 정지했거나 폐업한 매장도 돌려준다 — 열지 말지는 open 을 보고 쓰는 쪽이 정한다.
        잠그지 않는다."""
```

`backend/apps/hub/app/dtos/media_urls.py`:

```diff
@@ -6,7 +6,9 @@ from dataclasses import dataclass
 @dataclass(frozen=True)
 class MediaUrls:
     """사진·영상 하나의 읽기 URL 과 표시용 정보. 목록·달력·피드·미리보기는 thumb, 상세 넘기기는 display
-    (영상은 None — 포스터 thumb 를 쓴다), 크게 보기·원본 저장·영상 재생은 original 을 쓴다.
+    (영상은 None — 포스터 thumb 를 쓴다), 크게 보기·원본 저장·영상 재생은 original 을 쓴다. download 는 원본을
+    첨부 파일(`chagocnote-{media_id}.jpg`·`.mp4`)로 내려받는 주소다 — 브라우저의 download 속성은 다른 출처의
+    파일에 동작하지 않아서, 공개 알림장의 '저장'이 쓴다.
 
     URL 은 매장 시간대 04:00 기준으로 하루 동안 같고 최대 48시간 유효하다. 앱은 media_id 를 캐시 키로 쓴다.
     """
@@ -14,6 +16,7 @@ class MediaUrls:
     media_id: int
     kind: str                     # photo · video
     original_url: str
+    download_url: str
     display_url: str | None
     thumb_url: str
     width: int
```

`backend/apps/media/adapter/outbound/s3/boto3_object_storage_adapter.py`:

```diff
@@ -37,10 +37,11 @@ class Boto3ObjectStorageAdapter(ObjectStoragePort):
             ExpiresIn=expires_in_seconds,
         )
 
-    def presign_get(self, key: str, window: SigningWindow) -> str:
+    def presign_get(self, key: str, window: SigningWindow, download_as: str | None = None) -> str:
         return presign_get_url(
             self._public_endpoint, self._bucket, key, self._region, self._access_key, self._secret_key,
             window.signed_at, window.expires_in_seconds,
+            f'attachment; filename="{download_as}"' if download_as else None,
         )
 
     async def head(self, key: str) -> ObjectInfo | None:
```

`backend/apps/media/adapter/outbound/s3/sigv4_query.py`:

```diff
@@ -20,8 +20,9 @@ def _hmac(key: bytes, message: str) -> bytes:
 
 def presign_get_url(
     endpoint: str, bucket: str, key: str, region: str, access_key: str, secret_key: str,
-    signed_at: datetime, expires_in_seconds: int,
+    signed_at: datetime, expires_in_seconds: int, content_disposition: str | None = None,
 ) -> str:
+    """content_disposition 을 주면 저장소가 응답의 Content-Disposition 헤더로 돌려준다(내려받기용 주소)."""
     host = urlsplit(endpoint).netloc
     amz_date = signed_at.strftime("%Y%m%dT%H%M%SZ")
     day = signed_at.strftime("%Y%m%d")
@@ -34,8 +35,15 @@ def presign_get_url(
         f"&X-Amz-Expires={expires_in_seconds}"
         "&X-Amz-SignedHeaders=host"
     )
-    canonical = "\n".join(["GET", path, query, f"host:{host}", "", "host", "UNSIGNED-PAYLOAD"])
+    # 서명하는 질의 문자열은 키 순서다(대문자 X 가 소문자 r 보다 앞). URL 에서는 botocore 처럼 앞에 둔다.
+    # 값은 RFC 3986 대로 인코딩한다 — 공백은 %20, 세미콜론·등호·따옴표도 바꾼다.
+    disposition = (
+        f"response-content-disposition={quote(content_disposition, safe='')}" if content_disposition else ""
+    )
+    signed_query = f"{query}&{disposition}" if disposition else query
+    url_query = f"{disposition}&{query}" if disposition else query
+    canonical = "\n".join(["GET", path, signed_query, f"host:{host}", "", "host", "UNSIGNED-PAYLOAD"])
     string_to_sign = "\n".join([_ALGORITHM, amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
     signing_key = _hmac(_hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), day), region), "s3"), "aws4_request")
     signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
-    return f"{endpoint.rstrip('/')}{path}?{query}&X-Amz-Signature={signature}"
+    return f"{endpoint.rstrip('/')}{path}?{url_query}&X-Amz-Signature={signature}"
```

`backend/apps/media/app/ports/output/object_storage_port.py`:

```diff
@@ -14,8 +14,9 @@ class ObjectStoragePort(ABC):
         """앱이 인증 헤더 없이 PUT 할 URL. Content-Type 이 서명에 든다 — 다른 형식으로 올리면 저장소가 거절한다."""
 
     @abstractmethod
-    def presign_get(self, key: str, window: SigningWindow) -> str:
-        """읽기 URL. 같은 창이면 글자까지 같다(앱·CDN 캐시)."""
+    def presign_get(self, key: str, window: SigningWindow, download_as: str | None = None) -> str:
+        """읽기 URL. 같은 창이면 글자까지 같다(앱·CDN 캐시). download_as 를 주면 저장소가 그 이름의 첨부 파일로
+        내려 준다(Content-Disposition) — 이름은 ASCII 만 쓴다."""
 
     @abstractmethod
     async def head(self, key: str) -> ObjectInfo | None:
```

`backend/apps/media/app/use_cases/media_library_interactor.py`:

```diff
@@ -9,6 +9,7 @@ from hub.app.errors import MediaClaimAlreadyAttachedError, MediaClaimNotFoundErr
 from hub.app.ports.media_library_port import MediaLibraryPort
 from media.app.ports.output.media_repository import MediaRepository
 from media.app.ports.output.object_storage_port import ObjectStoragePort
+from media.domain.services.media_rules import download_name
 from media.domain.services.url_expiry import signing_window
 
 
@@ -46,6 +47,7 @@ class MediaLibraryInteractor(MediaLibraryPort):
         return {
             m.id: MediaUrls(
                 media_id=m.id, kind=m.kind, original_url=sign(m.keys.original, window),
+                download_url=sign(m.keys.original, window, download_name(m.id, m.kind)),
                 display_url=sign(m.keys.display, window) if m.keys.display else None,
                 thumb_url=sign(m.keys.thumb, window), width=m.width, height=m.height,
                 duration_seconds=m.duration_seconds,
```

`backend/apps/media/domain/services/media_rules.py`:

```diff
@@ -39,6 +39,11 @@ def object_keys(shop_id: int, media_id: int, kind: str) -> MediaKeys:
     return MediaKeys(original=f"original-video/{tail}.mp4", display=None, thumb=f"thumb/{tail}.jpg")
 
 
+def download_name(media_id: int, kind: str) -> str:
+    """내려받을 때의 파일 이름. 서명 URL 에 실려 밖으로 나가므로 고객·매장 이름을 넣지 않는다. ASCII 만 쓴다."""
+    return f"chagocnote-{media_id}.{'jpg' if kind == PHOTO else 'mp4'}"
+
+
 def check_upload(
     kind: str, content_type: str, byte_size: int, width: int, height: int, duration_seconds: int | None
 ) -> None:
```

`backend/apps/tenancy/adapter/outbound/pg/shop_pg_repository.py`:

```diff
@@ -24,6 +24,10 @@ class ShopPgRepository(ShopRepository):
     async def get_by_id(self, shop_id: int) -> Shop:
         return to_shop(await self._row(shop_id))
 
+    async def find_by_id(self, shop_id: int) -> Shop | None:
+        row = await self._session.get(ShopOrm, shop_id)
+        return to_shop(row) if row is not None else None
+
     async def get(self, ctx: ShopContext) -> Shop:
         return to_shop(await self._row(ctx.shop_id))
```

`backend/apps/tenancy/app/ports/output/shop_repository.py`:

```diff
@@ -14,6 +14,10 @@ class ShopRepository(ABC):
     async def get_by_id(self, shop_id: int) -> Shop:
         """컨텍스트가 아직 없는 경로(초대 수락)에서만 쓴다."""
 
+    @abstractmethod
+    async def find_by_id(self, shop_id: int) -> Shop | None:
+        """로그인한 사용자가 없는 경로(매장 공개 정보)에서만 쓴다. 없는 매장이면 None."""
+
     @abstractmethod
     async def get(self, ctx: ShopContext) -> Shop: ...
```

`backend/apps/tenancy/app/use_cases/get_shop_profile_interactor.py`:

```python
from __future__ import annotations

from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.shop_profile_port import ShopProfilePort
from tenancy.app.ports.output.shop_repository import ShopRepository


class GetShopProfileInteractor(ShopProfilePort):
    """허브의 ShopProfilePort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, shops: ShopRepository) -> None:
        self._shops = shops

    async def public_profile(self, shop_id: int) -> ShopProfile | None:
        shop = await self._shops.find_by_id(shop_id)
        if shop is None:
            return None
        return ShopProfile(
            shop_id=shop.id,
            name=shop.name,
            phone=shop.phone,
            address=shop.address,
            timezone=shop.timezone,
            open=shop.suspended_at is None and shop.closed_at is None,
        )
```

`backend/apps/tenancy/dependencies/get_shop_profile_provider.py`:

```python
from __future__ import annotations

from core.database import DbSession
from hub.app.ports.shop_profile_port import ShopProfilePort
from tenancy.app.use_cases.get_shop_profile_interactor import GetShopProfileInteractor
from tenancy.dependencies.tenancy_wiring import build_shop_repository


def get_shop_profile_use_case(db: DbSession) -> ShopProfilePort:
    return GetShopProfileInteractor(shops=build_shop_repository(db))
```

`backend/apps/visit/dependencies/hub_ports.py`:

```diff
@@ -6,6 +6,7 @@ from __future__ import annotations
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
+from hub.app.ports.shop_profile_port import ShopProfilePort
 
 
 def get_customer_directory() -> CustomerDirectoryPort:
@@ -14,3 +15,7 @@ def get_customer_directory() -> CustomerDirectoryPort:
 
 def get_media_library() -> MediaLibraryPort:
     raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
+
+
+def get_shop_profile() -> ShopProfilePort:
+    raise RuntimeError("ShopProfilePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/main.py`:

```diff
@@ -59,6 +59,7 @@ from tenancy.adapter.inbound.api.v1.list_members_router import list_members_rout
 from tenancy.adapter.inbound.api.v1.remove_member_router import remove_member_router
 from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router
 from tenancy.adapter.inbound.api.v1.update_shop_router import update_shop_router
+from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
 from tenancy.dependencies.hub_ports import get_active_user_guard, get_user_directory
 from tenancy.dependencies.list_memberships_provider import get_list_memberships_use_case
 from tenancy.dependencies.provision_shop_provider import get_provision_shop_use_case
@@ -93,6 +94,7 @@ from visit.adapter.inbound.api.v1.update_visit_settings_router import update_vis
 from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
 from visit.dependencies.hub_ports import get_customer_directory
 from visit.dependencies.hub_ports import get_media_library as get_visit_media_library
+from visit.dependencies.hub_ports import get_shop_profile
 from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
 
 
@@ -189,6 +191,7 @@ app.dependency_overrides[get_customer_directory] = get_customer_directory_use_ca
 app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
 app.dependency_overrides[get_visit_media_library] = get_media_library_use_case
 app.dependency_overrides[get_customer_media_library] = get_media_library_use_case
+app.dependency_overrides[get_shop_profile] = get_shop_profile_use_case
 
 
 @app.get("/health")
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 테스트(아래 열 파일) | 66 passed |
| 단위 전체 | 1081 passed, 352 deselected (시작 1069 → +12) |
| 통합 전체 | 352 passed, 1081 deselected (시작 347 → +5) |
| 구조 계약 | 6 kept, 0 broken (Analyzed 1060 files, 4508 dependencies) |

- 새 단위 12: tenancy 인터랙터 6, 매장 공개 정보 스텁 1, 자리 꽂기 1, 서명 2, 파일 이름 1, `read_urls` 1.
- 새 통합 5: tenancy pg 4, MinIO 내려받기 1.
- 커밋 직전에 긴 줄 둘(스텁·테스트의 줄 나눔)만 고쳐 커밋을 고쳤다. 그 뒤 단위 전체는 다시 돌렸고(1081 passed), **통합 전체와 구조 계약은 그 줄 나눔 뒤에는 다시 돌리지 않았다**(바뀐 두 파일은 단위 테스트에서만 쓰인다).
- `tests/route_inspection.py`: 새 자리를 쓰는 라우트가 없어 `test_API_프로세스에는_빈_자리도_빠진_가드도_없다` 는 그대로 통과한다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `GetShopProfileInteractor` 의 `open` 에서 `suspended_at` 을 뺀다(`open=shop.closed_at is None`) → `test_get_shop_profile_interactor.py::test_정지했거나_폐업한_매장은_영업_중이_아니다[suspended_at]`, `test_get_shop_profile_pg.py::test_정지했거나_폐업한_매장은_영업_중이_아니다[suspended_at]`
- `presign_get_url` 이 추가 매개변수를 서명에 넣지 않는다(`signed_query = query`, URL 에는 그대로 붙는다) → `test_sigv4_query.py::test_내려받기_서명도_botocore_와_같은_URL_이다`, `test_sigv4_query.py::test_내려받기_서명은_읽기_서명과_다르다`, `test_media_flow_wiring.py::test_내려받기_URL_로_받으면_첨부_파일로_내려오고_원본_URL_은_그대로다` — MinIO 응답이 **403** 임을 따로 확인했다(`assert (403, 473) == (200, 3000)`)
- 확장자를 늘 `.jpg` 로 → `test_media_library_interactor.py::test_내려받기_URL_은_원본을_첨부_파일_이름과_함께_서명한다`, `test_media_rules.py::test_내려받는_파일_이름은_서비스_이름과_ID_와_확장자뿐이다`
- `open` 에서 `closed_at` 을 뺀다 → 인터랙터·pg 의 `test_정지했거나_폐업한_매장은_영업_중이_아니다[closed_at]`
- 인터랙터가 `find_by_id` 대신 `get_by_id` 를 쓴다(없는 매장에서 터진다) → pg 의 `test_없는_매장이면_None_이다`(단위는 스텁에 그 메서드가 없어 여섯 모두 실패)
- 서명하는 질의에서 추가 매개변수를 앞에 둔다(키 정렬 어김) → `test_내려받기_서명도_botocore_와_같은_URL_이다`, MinIO `test_내려받기_URL_로_받으면_…`
- 값 인코딩에서 `;`·`=` 를 그대로 둔다(`safe=';='`) → 위와 같은 둘
- 공백을 `+` 로 인코딩한다 → 위와 같은 둘
- URL 에서 추가 매개변수를 뒤에 둔다(서명은 맞다) → `test_내려받기_서명도_botocore_와_같은_URL_이다` 하나 — 저장소는 순서를 가리지 않으므로 MinIO 테스트는 통과한다. 글자 대조만 잡는다
- 어댑터가 `download_as` 를 넘기지 않는다 → MinIO `test_내려받기_URL_로_받으면_…`
- 어댑터가 `attachment` 대신 `inline` → MinIO `test_내려받기_URL_로_받으면_…`
- 내려받기 주소를 썸네일 키로 서명한다 → `test_내려받기_URL_은_원본을_…`, MinIO `test_내려받기_URL_로_받으면_…`(크기 3000 이 아니다)
- 원본 주소에도 첨부 이름을 넣는다 → `test_읽기_URL_은_준비된_것만_…`, `test_내려받기_URL_은_원본을_…`, MinIO `test_내려받기_URL_로_받으면_…`
- `main.py` 가 자리를 채우지 않는다 → `tests/test_hub_port_binding.py::test_매장_공개_정보_자리는_tenancy_의_구현으로_채운다`
- 자리가 RuntimeError 를 던지지 않는다 → 위와 같다
- 파일 이름의 접두사를 바꾼다 → `test_내려받는_파일_이름은_…`, `test_내려받기_URL_은_원본을_…`, MinIO `test_내려받기_URL_로_받으면_…`
- 스텁이 없는 매장에 KeyError → `test_fakes_are_ports.py::test_매장_공개_정보_스텁은_넣어_둔_매장만_돌려준다`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(hub): 공개 알림장이 쓸 허브 포트 — 매장 공개 정보(ShopProfilePort), 내려받기용 서명 주소

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 알림장 조립과 미리보기 — 켠 항목과 빼지 않은 사진만 담는다(`GET visits/{id}/report`), 설정 상수

**Files:**
- Modify: `.env.example`
- Modify: `backend/core/config.py`
- Modify: `backend/scripts/generate_dev_env.py`
- Create: `backend/apps/visit/app/dtos/report_view_dto.py`
- Create: `backend/apps/visit/app/services/report_reader.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_report_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/report_view_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/get_visit_report_router.py`
- Create: `backend/apps/visit/app/dtos/get_visit_report_dto.py`
- Create: `backend/apps/visit/app/ports/input/get_visit_report_use_case.py`
- Create: `backend/apps/visit/app/use_cases/get_visit_report_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/dependencies/get_visit_report_provider.py`
- Create: `backend/apps/visit/tests/adapter/test_get_visit_report_router.py`
- Create: `backend/apps/visit/tests/app/services/test_report_reader.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_get_visit_report_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_visit_report_wiring.py`
- Modify: `backend/tests/test_config_defaults.py`

**Interfaces:**
- Consumes: 작업 1 의 `visible_media`·`report_cover_media_id`·`hide`·`make_token`; 작업 2 의 `ReportRepository.get_live`; 작업 3 의 `ReportSettingsRepository.get`; 작업 4 의 `ShopProfilePort`·`MediaUrls.download_url`·`visit.dependencies.hub_ports.get_shop_profile`; `CustomerDirectoryPort.briefs`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# visit/app/dtos/report_view_dto.py — 모두 @dataclass(frozen=True)
class ReportMediaView:
    media_id: int; kind: str; phase: str; hidden: bool; width: int; height: int
    duration_seconds: int | None; display_url: str; thumb_url: str; download_url: str
class ReportCoverView:  url: str; width: int; height: int
class ReportMenuView:   name: str; amount: int | None
class ReportShopView:   name: str; phone: str | None; address: str | None
class ReportView:
    pet_name: str | None; visit_date: date; care_note: str | None
    media: tuple[ReportMediaView, ...]; cover: ReportCoverView | None
    menus: tuple[ReportMenuView, ...] | None; total_amount: int | None
    weight_kg: Decimal | None; shop: ReportShopView | None; settings: ReportSettings
class ReportLinkView:
    status: str; url: str | None; expires_at: datetime | None
    first_viewed_at: datetime | None; created_at: datetime | None
    def in_zone(self, zone: ZoneInfo) -> ReportLinkView      # 시각 셋을 그 시간대로 바꾼 사본

# visit/app/services/report_reader.py
async def describe_report(
    ctx: ShopContext, visit: Visit, record: VisitRecord, settings: ReportSettings, shop: ShopProfile,
    menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort, *, include_hidden: bool,
) -> ReportView
def describe_link(report: VisitReport | None, key: bytes, base_url: str) -> ReportLinkView

# core/config.py
REPORT_LINK_KEY: bytes          # .env 의 REPORT_LINK_KEY_B64 를 푼 것. 32바이트 미만이면 import 때 RuntimeError
REPORT_WEB_BASE_URL: str        # 기본 "http://127.0.0.1:3010", 끝의 "/" 를 뗀 것
REPORT_WEB_SECRET: str          # 기본 ""

# 슬라이스
GetVisitReportQuery(ctx: ShopContext, visit_id: int)                       # visit/app/dtos/get_visit_report_dto.py
VisitReportPreview(report: ReportView, link: ReportLinkView)               # 같은 파일. 설정은 report.settings
GetVisitReportUseCase.get_visit_report(query) -> VisitReportPreview
GetVisitReportInteractor(visits: VisitLookupRepository, records: VisitRecordRepository,
    settings: ReportSettingsRepository, reports: ReportRepository, menus: MenuRepository,
    directory: CustomerDirectoryPort, library: MediaLibraryPort, shops: ShopProfilePort,
    now: Callable[[], datetime], link_key: bytes, web_base_url: str)
get_get_visit_report_use_case(db, directory, library, shops) -> GetVisitReportUseCase
get_visit_report_router     GET /v1/shops/{shop_id}/visits/{visit_id}/report   get_shop_context

# 스키마
# visit/adapter/inbound/api/schemas/report_view_schema.py
ReportMediaSchema, ReportCoverSchema, ReportMenuSchema, ReportShopSchema,
ReportSchema(pet_name, visit_date, care_note, media, cover, menus, total_amount, weight_kg: float | None, shop),
ReportLinkSchema(status, url, expires_at, first_viewed_at, created_at)
# visit/adapter/inbound/api/schemas/get_visit_report_schema.py
VisitReportSchema(report: ReportSchema, link: ReportLinkSchema, settings: ReportSettingsSchema)   # .of(view)

# visit/tests/helpers/fakes.py
FakeDirectory.pet_names: dict[int, str | None]     # 없는 아이는 "아이{ID}". None 을 넣으면 이름 없는 요약
```

뒤 작업이 알아 둘 동작
- **`describe_link` 의 시각은 UTC 그대로다.** 응답에 담기 전에 `.in_zone(ZoneInfo(ctx.timezone))` 을 부른다. T6(PUT 응답)·T7(방문 상세의 `report`)이 같은 방식으로 쓰면 된다. `ReportLinkSchema` 는 `model_validate(view, from_attributes=True)` 로 만든다.
- **`describe_link` 는 살아 있는지 판단하지 않는다.** 넘긴 링크가 있으면 `live` 다. `reports.get_live(ctx, visit_id, now)` 의 결과(또는 발급 직후의 링크)만 넘긴다.
- `describe_report` 는 `shop` 이 `None` 이면 매장 정보를 켠 매장에서 `AttributeError` 다. 미리보기는 `public_profile(ctx.shop_id)` 를 그대로 넘긴다(멤버가 확인된 매장이라 없을 수 없다). T8 은 `None` 을 404 로 거른 뒤 넘겨야 한다.
- `describe_report` 는 방문의 상태를 보지 않는다. 시간대는 `shop.timezone` 이 아니라 **`ctx.timezone`** 으로 센다 — T8 은 `public_profile` 의 시간대로 `ShopContext` 를 만든다(설계 3.4).
- 대표(`cover`)는 `include_hidden` 과 상관없이 언제나 빼지 않은 것 가운데서 고른다. 미리보기의 대표가 곧 보호자가 볼 대표다.
- `media` 는 `read_urls` 가 돌려주지 않은 미디어(준비 전·다른 매장)를 뺀다(기존 `describe_record` 와 같다).
- `menus` 는 예약 메뉴(`visit.menu_ids`)가 아니라 **기록의 항목**(`record.items`, 실제로 한 메뉴)이다. 켜져 있고 항목이 없으면 빈 튜플, 꺼져 있으면 `None`.
- `care_note` 는 비었거나 공백뿐이면 `None`, 아니면 적힌 그대로다(앞뒤 공백을 다듬지 않는다).
- 반려동물 이름은 `directory.briefs(ctx, [], [pet_id])` 로 읽는다. 고객 ID 를 넘기지 않아 보호자 요약은 읽지도 않는다. 무지개다리를 건넌 아이는 이름이 그대로 나온다.
- 질의 수(미리보기 한 번): 방문 2(방문+메뉴), 기록, 설정, 매장, 반려동물 요약, 미디어 주소, 메뉴 이름(켜져 있고 항목이 있을 때), 링크.
- 공개 응답의 "끈 칸은 아예 없음"은 T8 의 스키마가 `view.settings` 를 보고 만든다. 매장용 스키마는 `null` 로 준다.
- `tests/test_config_defaults.py` 의 `load_config(**값)` 픽스처로 설정 값을 바꿔 `core.config` 를 다시 읽을 수 있다. T8 이 `REPORT_WEB_SECRET` 을 바꿔야 하면 배선 테스트에서는 `monkeypatch.setattr` 가 더 간단하다.

설계 3.2·3.4·5절·6.1·6.3, R2·R6·R7. 공개 조회(작업 8)와 미리보기가 같은 함수 `describe_report` 로 알림장을 만든다. 끈 항목은 조립 단계에서 비운다 — 스키마나 웹이 숨기는 것이 아니다. `ReportView` 에는 내부 메모·결제 수단·보호자 이름·전화번호의 칸이 없다.

**이 작업은 새 비밀값을 더한다.** `REPORT_LINK_KEY_B64` 가 `.env` 에 없으면 API·인증 프로세스 둘 다 기동하지 않고 모든 테스트가 수집에서 멈춘다. `generate_dev_env.py` 는 `.env` 가 이미 있으면 아무것도 하지 않으므로 **Step 3 을 시작하기 전에** 아래 '환경' 의 명령으로 한 줄을 더한다(값을 출력하지 않는다). 더한 뒤 개발 스택을 다시 띄운다: `docker compose up -d --force-recreate backend auth`(`infra/`).

#### 환경 — `.env` 에 키를 더한다 (Step 3 을 시작하기 전에)

참조 구현에서 확인한 사실
- `secret_manager` 는 환경 변수 → 저장소 루트의 `.env` → 기본값 순서로 읽는다. 테스트는 conftest 가 환경을 채우지 않고 compose 가 넣어 준 `.env` 값에 기댄다 — 키가 없으면 `core.config` 를 import 하는 모든 테스트가 수집에서 멈춘다.
- `scripts/generate_dev_env.py` 는 `.env` 나 `.env.auth` 가 하나라도 있으면 아무것도 하지 않는다. 빠진 키를 더하지 않는다.
- 인증 프로세스(`auth_main`)도 `core.config` 를 import 한다. compose 의 auth 서비스는 `.env` 와 `.env.auth` 를 둘 다 읽으므로 `.env` 에 키가 있으면 기동한다.
- `REPORT_WEB_BASE_URL`(기본 `http://127.0.0.1:3010`)·`REPORT_WEB_SECRET`(기본 빈 문자열)은 기본값이 있어 더하지 않아도 돈다. 웹(⑤-2)을 붙일 때 `REPORT_WEB_SECRET` 을 정한다.

키를 더하는 명령(`infra/` 에서). 값을 출력하지 않는다. 이미 있으면 아무것도 하지 않는다. 파일이 줄바꿈으로 끝나지 않으면 줄바꿈을 먼저 넣는다(임시 파일 셋으로 확인했다 — 줄바꿈 없는 파일, 있는 파일, 키가 이미 있는 파일, 각각 두 번 실행).

```bash
docker compose run --rm --no-deps backend python -c "
import base64, secrets
from pathlib import Path
env = Path('/work/.env')
text = env.read_text()
if 'REPORT_LINK_KEY_B64=' not in text:
    with env.open('a') as f:
        f.write(('' if text.endswith('\n') or not text else '\n')
                + 'REPORT_LINK_KEY_B64=' + base64.b64encode(secrets.token_bytes(32)).decode() + '\n')
"
```

확인(값을 출력하지 않는다): `grep -c '^REPORT_LINK_KEY_B64=' ../.env` → `1`

그 뒤 개발 스택이 새 값을 읽게 한다: `docker compose up -d --force-recreate backend auth`. **운영과 다른 개발자의 환경에도 같은 키가 필요하다** — 없으면 API·인증 프로세스 둘 다 기동하지 않는다(README 의 "처음 띄우기", 작업 10).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_get_visit_report_router.py`:

```python
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from visit.adapter.inbound.api.v1.get_visit_report_router import get_visit_report_router
from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportLinkView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.dependencies.get_visit_report_provider import get_get_visit_report_use_case
from visit.domain.errors import VisitNoRecordYetError, VisitNotFoundError
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.api import READ_ONLY, Recorder, build_app, client, error_of

SEOUL = ZoneInfo("Asia/Seoul")
NO_LINK = ReportLinkView(status="none", url=None, expires_at=None, first_viewed_at=None, created_at=None)
SENT = VisitReportPreview(
    report=ReportView(
        pet_name="콩이", visit_date=date(2026, 9, 23), care_note="눈물 자국",
        media=(ReportMediaView(media_id=52, kind="photo", phase="after", hidden=True, width=3000, height=2000,
                               duration_seconds=None, display_url="d/52", thumb_url="t/52", download_url="dl/52"),),
        cover=ReportCoverView(url="d/52", width=3000, height=2000),
        menus=(ReportMenuView(name="목욕", amount=30000),), total_amount=30000, weight_kg=Decimal("3.4"),
        shop=ReportShopView(name="Hiss Haus", phone="02-123-4567", address=None),
        settings=ReportSettings(link_days=7, show_menus=True, show_shop_info=True, show_weight=True,
                                show_amount=True),
    ),
    link=ReportLinkView(status="live", url="https://r.example/r/token",
                        expires_at=datetime(2026, 9, 30, 15, tzinfo=SEOUL), first_viewed_at=None,
                        created_at=datetime(2026, 9, 23, 15, tzinfo=SEOUL)),
)
HIDDEN = VisitReportPreview(
    report=ReportView(
        pet_name=None, visit_date=date(2026, 9, 23), care_note=None, media=(), cover=None, menus=None,
        total_amount=None, weight_kg=None, shop=None,
        settings=ReportSettings(link_days=None, show_menus=False, show_shop_info=False, show_weight=False,
                                show_amount=False),
    ),
    link=NO_LINK,
)


async def _get(stub, path="/v1/shops/3/visits/1/report", access=None):
    async with client(build_app(get_visit_report_router, get_get_visit_report_use_case, stub, access)) as c:
        return await c.get(path)


async def test_권한이_없는_멤버도_알림장을_미리_본다():
    stub = Recorder(SENT)
    response = await _get(stub, access=READ_ONLY)
    assert response.status_code == 200
    assert response.json() == {
        "report": {
            "pet_name": "콩이", "visit_date": "2026-09-23", "care_note": "눈물 자국",
            "media": [{"media_id": 52, "kind": "photo", "phase": "after", "hidden": True, "width": 3000,
                       "height": 2000, "duration_seconds": None, "display_url": "d/52", "thumb_url": "t/52",
                       "download_url": "dl/52"}],
            "cover": {"url": "d/52", "width": 3000, "height": 2000},
            "menus": [{"name": "목욕", "amount": 30000}], "total_amount": 30000, "weight_kg": 3.4,
            "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": None},
        },
        "link": {"status": "live", "url": "https://r.example/r/token", "expires_at": "2026-09-30T15:00:00+09:00",
                 "first_viewed_at": None, "created_at": "2026-09-23T15:00:00+09:00"},
        "settings": {"link_days": 7, "show_menus": True, "show_shop_info": True, "show_weight": True,
                     "show_amount": True},
    }
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].visit_id) == (3, 1)


async def test_끈_항목의_칸은_null_이다():
    body = (await _get(Recorder(HIDDEN))).json()
    assert body["report"] == {
        "pet_name": None, "visit_date": "2026-09-23", "care_note": None, "media": [], "cover": None,
        "menus": None, "total_amount": None, "weight_kg": None, "shop": None,
    }
    assert body["link"] == {"status": "none", "url": None, "expires_at": None, "first_viewed_at": None,
                            "created_at": None}
    assert body["settings"] == {"link_days": None, "show_menus": False, "show_shop_info": False,
                                "show_weight": False, "show_amount": False}


async def test_없는_방문은_404_기록이_없으면_409_다():
    assert error_of(await _get(Recorder(error=VisitNotFoundError("없음")))) == (404, "VISIT_NOT_FOUND")
    assert error_of(await _get(Recorder(error=VisitNoRecordYetError("없음")))) == (409, "VISIT_NO_RECORD_YET")


@pytest.mark.parametrize("visit_id", ["9223372036854775808", "0", "-1", "1.5", "abc", "1" * 400])
async def test_방문_ID_가_범위_밖이거나_숫자가_아니면_422_다(visit_id):
    stub = Recorder(SENT)
    assert error_of(await _get(stub, f"/v1/shops/3/visits/{visit_id}/report")) == (422, "VALIDATION_ERROR")
    assert stub.calls == []
```

`backend/apps/visit/tests/app/services/test_report_reader.py`:

```python
"""알림장 조립 — 켠 항목과 빼지 않은 사진만 담는다(설계 6.3, 위협 점검표 R6·R7)."""
from dataclasses import fields, replace
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportLinkView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.app.services.report_reader import describe_link, describe_report
from visit.domain.entities.visit_record import RecordItem
from visit.domain.entities.visit_report import VisitReport
from visit.domain.services.report_rules import hide
from visit.domain.services.report_token import read_token
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.builders import ctx, kst, record, visit
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus

SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone="02-123-4567", address="서울 마포구", timezone="Asia/Seoul",
                   open=True)
KEY = bytes(range(32))


def _settings(menus=False, shop=False, weight=False, amount=False) -> ReportSettings:
    return ReportSettings(link_days=30, show_menus=menus, show_shop_info=shop, show_weight=weight,
                          show_amount=amount)


ALL_ON = _settings(menus=True, shop=True, weight=True, amount=True)
VISIT = visit(status="completed", starts_at=kst(9, 23, 14), memo="SECRET-예약메모", menu_ids=(1,))
# 보이는 순서는 후(52 → 53 → 61) → 전(51) 이다. 61 은 영상.
RECORD = record(
    1, media=((51, "photo", "before", 0), (52, "photo", "after", 0), (53, "photo", "after", 1),
              (61, "video", "after", 2)),
    weight_kg=Decimal("3.4"), care_note="눈물 자국을 닦았어요", internal_note="SECRET-내부메모",
    payment_method="SECRET-결제수단", total_amount=55000, items=(RecordItem(1, 30000), RecordItem(2, 25000)),
)


def _hiding(*media_ids):
    return replace(RECORD, media=hide(RECORD, media_ids))


async def _describe(settings=ALL_ON, a_visit=VISIT, a_record=RECORD, include_hidden=False, pet_names=None,
                    pets=(101,)):
    menus, directory, library = FakeMenus(), FakeDirectory(), FakeLibrary()
    menus.seed("목욕")
    menus.seed("가위컷")
    directory.family(1, pets=pets, name="SECRET-보호자")
    directory.pet_names = pet_names or {}
    for media in RECORD.media:
        library.add(media.media_id, kind=media.kind, attached=True)
    return await describe_report(ctx(), a_visit, a_record, settings, SHOP, menus, directory, library,
                                 include_hidden=include_hidden)


async def test_넷_다_켜면_메뉴와_금액과_몸무게와_매장_정보를_담는다():
    view = await _describe(ALL_ON)
    assert view.menus == (ReportMenuView(name="목욕", amount=30000), ReportMenuView(name="가위컷", amount=25000))
    assert (view.total_amount, view.weight_kg) == (55000, Decimal("3.4"))
    assert view.shop == ReportShopView(name="Hiss Haus", phone="02-123-4567", address="서울 마포구")
    assert view.settings == ALL_ON


async def test_넷_다_꺼도_이름과_날짜와_케어_메모와_사진은_담는다():
    view = await _describe(_settings())
    assert (view.menus, view.total_amount, view.weight_kg, view.shop) == (None, None, None, None)
    assert (view.pet_name, view.visit_date, view.care_note) == ("아이101", date(2026, 9, 23), "눈물 자국을 닦았어요")
    assert [m.media_id for m in view.media] == [52, 53, 61, 51]
    assert view.settings == _settings()


@pytest.mark.parametrize(("settings", "menus", "total"), [
    (_settings(amount=True), None, 55000),
    (_settings(menus=True), (ReportMenuView(name="목욕", amount=None), ReportMenuView(name="가위컷", amount=None)),
     None),
], ids=["메뉴_끔_금액_켬", "메뉴_켬_금액_끔"])
async def test_메뉴와_금액은_따로_켜고_끈다(settings, menus, total):
    view = await _describe(settings)
    assert (view.menus, view.total_amount) == (menus, total)


@pytest.mark.parametrize(("settings", "weight", "shop"), [
    (_settings(weight=True), Decimal("3.4"), None),
    (_settings(shop=True), None, ReportShopView(name="Hiss Haus", phone="02-123-4567", address="서울 마포구")),
], ids=["몸무게만", "매장_정보만"])
async def test_몸무게와_매장_정보도_따로_켜고_끈다(settings, weight, shop):
    view = await _describe(settings)
    assert (view.weight_kg, view.shop) == (weight, shop)


async def test_방문_날짜는_매장_시간대의_날짜다():
    view = await _describe(a_visit=replace(VISIT, starts_at=kst(9, 24, 0, 30)))   # UTC 로는 23일 15:30
    assert view.visit_date == date(2026, 9, 24)


async def test_뺀_사진은_담지_않는다():
    view = await _describe(a_record=_hiding(52, 61))
    assert [(m.media_id, m.hidden) for m in view.media] == [(53, False), (51, False)]


async def test_미리보기는_뺀_사진도_같은_순서에_표시와_함께_담는다():
    view = await _describe(a_record=_hiding(52, 61), include_hidden=True)
    assert [(m.media_id, m.hidden) for m in view.media] == [(52, True), (53, False), (61, True), (51, False)]


async def test_사진은_표시용_영상은_원본_주소를_준다():
    view = await _describe()
    assert view.media[0] == ReportMediaView(
        media_id=52, kind="photo", phase="after", hidden=False, width=3000, height=2000, duration_seconds=None,
        display_url="d/52", thumb_url="t/52", download_url="dl/52")
    assert view.media[2] == ReportMediaView(
        media_id=61, kind="video", phase="after", hidden=False, width=3000, height=2000, duration_seconds=30,
        display_url="o/61", thumb_url="t/61", download_url="dl/61")


@pytest.mark.parametrize("include_hidden", [False, True])
@pytest.mark.parametrize(("hidden", "cover"), [
    ((), "d/52"),
    ((52,), "d/53"),              # 뺀 후 사진을 건너뛴다
    ((52, 53), "d/51"),           # 후 사진이 없으면 전 사진
    ((51, 52, 53), "t/61"),       # 사진이 없으면 영상의 포스터
    ((51, 52, 53, 61), None),
])
async def test_대표는_빼지_않은_것_가운데서_고른다(hidden, cover, include_hidden):
    view = await _describe(a_record=_hiding(*hidden), include_hidden=include_hidden)
    assert view.cover == (ReportCoverView(url=cover, width=3000, height=2000) if cover else None)


async def test_보호자만의_방문은_반려동물_이름이_없다():
    """스텁에 ID 가 None 인 아이를 넣어 둔다 — 없는 ID 로 이름을 묻지 않는다."""
    view = await _describe(a_visit=replace(VISIT, pet_id=None), pets=(None,))
    assert view.pet_name is None


@pytest.mark.parametrize(("a_visit", "pet_names"), [
    (VISIT, {101: None}),                    # 익명화한 고객의 아이 — 틀은 오지만 이름이 없다
    (replace(VISIT, pet_id=999), None),      # 지워진 아이 — 틀도 오지 않는다
], ids=["익명화", "지워진_아이"])
async def test_이름을_얻지_못하면_반려동물_이름이_없다(a_visit, pet_names):
    view = await _describe(a_visit=a_visit, pet_names=pet_names)
    assert view.pet_name is None


@pytest.mark.parametrize("care_note", [None, "", "  \n "])
async def test_몸무게와_메모가_없으면_켜져_있어도_비어_있다(care_note):
    view = await _describe(a_record=replace(RECORD, weight_kg=None, care_note=care_note, items=(), media=()))
    assert (view.weight_kg, view.care_note, view.menus, view.media, view.cover) == (None, None, (), (), None)


@pytest.mark.parametrize("include_hidden", [False, True])
async def test_내부_메모와_결제_수단과_예약_메모와_보호자_정보는_어디에도_없다(include_hidden):
    """R6 — 스텁의 보호자 전화는 010-12··-5678 이다."""
    view = await _describe(ALL_ON, include_hidden=include_hidden)
    assert "SECRET" not in repr(view) and "010-12" not in repr(view)


def test_알림장에는_정해_둔_칸만_있다():
    assert [f.name for f in fields(ReportView)] == [
        "pet_name", "visit_date", "care_note", "media", "cover", "menus", "total_amount", "weight_kg", "shop",
        "settings"]


def _report(**overrides) -> VisitReport:
    found = dict(id=1, visit_id=1, public_id=bytes(range(16)), expires_at=kst(10, 23, 15), revoked_at=None,
                 first_viewed_at=kst(9, 23, 18), created_by_member_id=11, created_at=kst(9, 23, 15))
    return VisitReport(**{**found, **overrides})


def test_링크가_없으면_상태만_none_이다():
    assert describe_link(None, KEY, "https://r.example") == ReportLinkView(
        status="none", url=None, expires_at=None, first_viewed_at=None, created_at=None)


def test_링크의_주소는_웹_주소와_서명한_토큰_43글자다():
    link = describe_link(_report(), KEY, "https://r.example")
    token = link.url.removeprefix("https://r.example/r/")
    assert (len(token), read_token(token, KEY)) == (43, bytes(range(16)))
    assert read_token(token, bytes(32)) is None
    assert (link.status, link.expires_at, link.first_viewed_at, link.created_at) == (
        "live", kst(10, 23, 15), kst(9, 23, 18), kst(9, 23, 15))


def test_기간이_없고_아직_열지_않은_링크는_그_칸이_비어_있다():
    link = describe_link(_report(expires_at=None, first_viewed_at=None), KEY, "https://r.example")
    assert (link.status, link.expires_at, link.first_viewed_at) == ("live", None, None)


def test_링크의_시각을_매장_시간대로_바꾼다():
    seoul = ZoneInfo("Asia/Seoul")
    link = describe_link(_report(first_viewed_at=None), KEY, "https://r.example").in_zone(seoul)
    assert (link.expires_at.isoformat(), link.first_viewed_at, link.created_at.isoformat()) == (
        "2026-10-23T15:00:00+09:00", None, "2026-09-23T15:00:00+09:00")
    assert describe_link(None, KEY, "https://r.example").in_zone(seoul).expires_at is None
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_report_interactor.py`:

```python
from dataclasses import replace
from decimal import Decimal

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery
from visit.app.dtos.report_view_dto import ReportShopView
from visit.app.use_cases.get_visit_report_interactor import GetVisitReportInteractor
from visit.domain.errors import VisitNoRecordYetError, VisitNotFoundError
from visit.domain.services.report_rules import hide
from visit.domain.services.report_token import read_token
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeReportSettingsRepository,
    FakeShopProfile,
    FakeVisits,
)

KEY = bytes(range(32))
NOW = kst(9, 24, 10)
SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)


class _World:
    def __init__(self) -> None:
        self.visits, self.settings = FakeVisits(), FakeReportSettingsRepository()
        self.records, self.reports = FakeRecords(self.visits), FakeReportRepository(self.visits)
        directory, library = FakeDirectory(), FakeLibrary()
        directory.family(1, pets=(101,))
        for media_id in (51, 52):
            library.add(media_id, attached=True)
        self.interactor = GetVisitReportInteractor(
            visits=self.visits, records=self.records, settings=self.settings, reports=self.reports,
            menus=FakeMenus(), directory=directory, library=library, shops=FakeShopProfile({1: SHOP}),
            now=lambda: NOW, link_key=KEY, web_base_url="https://r.example",
        )

    def completed(self, status="completed", **fields):
        """사진 둘(전 51, 후 52)과 몸무게가 있는 기록이 달린 방문. 52 는 알림장에서 뺐다."""
        found = self.visits.seed(status=status, starts_at=kst(9, 23, 14), started_at=kst(9, 23, 14), **fields)
        written = record(found.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
                         weight_kg=Decimal("3.4"), care_note="눈물 자국")
        self.records.seed(replace(written, media=hide(written, (52,))))
        return found

    async def preview(self, visit_id, shop_id=1):
        return await self.interactor.get_visit_report(GetVisitReportQuery(ctx=ctx(shop_id=shop_id), visit_id=visit_id))


async def test_미리보기는_뺀_사진을_표시와_함께_주고_보낸_적이_없으면_링크가_없다():
    world = _World()
    found = await world.preview(world.completed().id)
    assert (found.report.pet_name, found.report.care_note) == ("아이101", "눈물 자국")
    assert [(m.media_id, m.hidden) for m in found.report.media] == [(52, True), (51, False)]
    assert found.report.cover.url == "d/51"
    assert (found.link.status, found.link.url) == ("none", None)


async def test_매장이_정한_설정대로_담는다():
    world = _World()
    assert (await world.preview(world.completed().id)).report.settings == DEFAULT_REPORT_SETTINGS
    chosen = ReportSettings(link_days=7, show_menus=False, show_shop_info=True, show_weight=True, show_amount=False)
    world.settings.rows[1] = chosen
    report = (await world.preview(1)).report
    assert (report.settings, report.menus, report.weight_kg) == (chosen, None, Decimal("3.4"))
    assert report.shop == ReportShopView(name="Hiss Haus", phone=None, address=None)


async def test_살아_있는_링크의_주소와_시각을_매장_시간대로_준다():
    world = _World()
    visit_id = world.completed().id
    await world.reports.create(ctx(), visit_id, bytes(range(16)), kst(10, 23, 15), kst(9, 23, 15))
    link = (await world.preview(visit_id)).link
    assert read_token(link.url.removeprefix("https://r.example/r/"), KEY) == bytes(range(16))
    assert (link.status, link.expires_at.isoformat(), link.first_viewed_at, link.created_at.isoformat()) == (
        "live", "2026-10-23T15:00:00+09:00", None, "2026-09-23T15:00:00+09:00")


async def test_기간이_지난_링크는_없는_것이다():
    world = _World()
    visit_id = world.completed().id
    await world.reports.create(ctx(), visit_id, bytes(range(16)), NOW, kst(9, 23, 15))   # 지금 끝난다
    assert (await world.preview(visit_id)).link.status == "none"


async def test_미용_중인_방문도_미리_본다():
    world = _World()
    found = await world.preview(world.completed(status="in_progress").id)
    assert found.report.care_note == "눈물 자국"


async def test_없는_방문과_다른_매장의_방문은_VISIT_NOT_FOUND_다():
    """R2"""
    world = _World()
    theirs = world.completed(shop_id=2)
    for visit_id in (theirs.id, 999):
        with pytest.raises(VisitNotFoundError):
            await world.preview(visit_id, shop_id=1)


async def test_기록이_없는_방문은_VISIT_NO_RECORD_YET_이다():
    world = _World()
    with pytest.raises(VisitNoRecordYetError):
        await world.preview(world.visits.seed(status="completed", started_at=kst(9, 23, 14)).id)
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:

```diff
@@ -16,6 +16,7 @@ async def test_자기소개는_묶음의_경로와_권한을_적는다():
     assert (result.id, result.name) == (5, "방문 (visit)")
     for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위",
                   "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT",
-                  "POST /visits/{visit_id}/record/media", "record:delete", "GET·PUT /report-settings"):
+                  "POST /visits/{visit_id}/record/media", "record:delete", "GET·PUT /report-settings",
+                  "GET /visits/{visit_id}/report"):
         assert words in result.introduction
     assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -149,6 +149,7 @@ class FakeDirectory(CustomerDirectoryPort):
         self.journal = journal if journal is not None else Journal()
         self.families: dict[int, tuple[int, dict[int, bool]]] = {}
         self.names: dict[int, str | None] = {}
+        self.pet_names: dict[int, str | None] = {}   # 없는 아이는 "아이{ID}". 익명화한 가족이면 None 을 넣는다
         self.candidates: list = []
 
     def family(self, customer_id=1, pets=(101,), shop_id=1, name="김민지", passed=()) -> None:
@@ -176,8 +177,9 @@ class FakeDirectory(CustomerDirectoryPort):
         for c, (shop, family) in self.families.items():
             for p in family:
                 if p in pet_ids and shop == ctx.shop_id:
-                    pets[p] = PetBrief(pet_id=p, customer_id=c, name=f"아이{p}", species="dog", breed="말티즈",
-                                       weight_kg=Decimal("3.2"), passed_away=family[p])
+                    pets[p] = PetBrief(pet_id=p, customer_id=c, name=self.pet_names.get(p, f"아이{p}"),
+                                       species="dog", breed="말티즈", weight_kg=Decimal("3.2"),
+                                       passed_away=family[p])
         return FamilyBriefs(customers=customers, pets=pets)
 
     async def set_last_visit(self, ctx, customer_id, at):
```

`backend/tests/integration/test_visit_report_wiring.py`:

```python
"""알림장을 실제 배선(프로바이더·허브 포트 조립·설정 상수·DB·MinIO)으로 확인한다."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    ready_photo,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}
NO_LINK = {"status": "none", "url": None, "expires_at": None, "first_viewed_at": None, "created_at": None}
YESTERDAY = datetime.now(SEOUL).date() - timedelta(days=1)


async def _shop(wired, operator, name, owner_name):
    shop_id, owner = await shop_with_owner(wired, operator, name, owner_name)
    return shop_id, owner, bearer(owner["access_token"])


async def _started_visit(wired, shop_id, headers) -> int:
    """어제 11시에 시작한 콩이의 방문(어제라 자정을 넘기지 않는다 — 시각과 상관없이 돈다)."""
    family = await wired.api.post(f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET},
                                  headers=headers)
    assert family.status_code == 201, family.text
    starts_at = datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 11, tzinfo=SEOUL).isoformat()
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": family.json()["customer"]["customer_id"],
              "pet_ids": [family.json()["pets"][0]["pet_id"]], "starts_at": starts_at})
    assert booked.status_code == 201, booked.text
    visit_id = booked.json()["visits"][0]["visit_id"]
    started = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                   json={"visit_ids": [visit_id], "action": "start"})
    assert started.status_code == 200, started.text
    return visit_id


async def test_직원이_알림장을_미리_보고_설정과_링크가_그대로_비친다(wired, media_storage):
    from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
    from visit.domain.services.report_token import read_token

    shop_id, owner, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    visit_id = await _started_visit(wired, shop_id, o)
    photo = await ready_photo(wired, shop_id, o)
    written = await wired.api.put(
        f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=o,
        json={"weight_kg": 3.4, "care_note": "눈물 자국을 닦았어요", "internal_note": "SECRET-내부메모",
              "media": [{"media_id": photo, "phase": "after", "sort_order": 0}]})
    assert written.status_code == 200, written.text
    path = f"/v1/shops/{shop_id}/visits/{visit_id}/report"

    seen = await wired.api.get(path, headers=bearer(staff["access_token"]))
    assert seen.status_code == 200, seen.text
    [media] = seen.json()["report"].pop("media")
    assert seen.json() == {
        "report": {
            "pet_name": "콩이", "visit_date": YESTERDAY.isoformat(), "care_note": "눈물 자국을 닦았어요",
            "media": [media], "cover": {"url": media["display_url"], "width": 3000, "height": 2000},
            "menus": [], "total_amount": None, "weight_kg": None,
            "shop": {"name": "Hiss Haus", "phone": None, "address": None},
        },
        "link": NO_LINK,
        "settings": {"link_days": 30, "show_menus": True, "show_shop_info": True, "show_weight": False,
                     "show_amount": False},
    }
    assert (media["media_id"], media["hidden"], media["kind"], media["phase"]) == (photo, False, "photo", "after")
    assert "response-content-disposition" in media["download_url"]
    assert "response-content-disposition" not in media["display_url"]
    assert "SECRET" not in seen.text and "김민지" not in seen.text and "1234" not in seen.text

    changed = await wired.api.put(
        f"/v1/shops/{shop_id}/report-settings", headers=o,
        json={"link_days": 7, "show_menus": False, "show_shop_info": False, "show_weight": True,
              "show_amount": False})
    assert changed.status_code == 200, changed.text
    await wired.execute(
        "UPDATE visit_record_media SET hidden_from_report = true WHERE media_id = :id", id=photo)
    await wired.execute(
        "INSERT INTO visit_reports (visit_id, public_id, expires_at, created_by_member_id, created_at)"
        " VALUES (:visit_id, :public_id, now() + interval '7 days', 1, now())",
        visit_id=visit_id, public_id=bytes(range(16)))

    body = (await wired.api.get(path, headers=o)).json()
    assert (body["report"]["menus"], body["report"]["shop"], body["report"]["weight_kg"]) == (None, None, 3.4)
    assert ([m["hidden"] for m in body["report"]["media"]], body["report"]["cover"]) == ([True], None)
    assert body["settings"]["show_weight"] is True
    assert body["link"]["status"] == "live"
    token = re.fullmatch(re.escape(REPORT_WEB_BASE_URL) + r"/r/([A-Za-z0-9_-]{43})", body["link"]["url"]).group(1)
    assert read_token(token, REPORT_LINK_KEY) == bytes(range(16))
    assert body["link"]["expires_at"].endswith("+09:00") and body["link"]["created_at"].endswith("+09:00")


async def test_다른_매장의_방문은_미리_볼_수_없고_기록이_없으면_409_다(wired):
    """R2"""
    operator = await make_operator(wired)
    a_shop, _, a = await _shop(wired, operator, "A 매장", "A사장")
    b_shop, _, b = await _shop(wired, operator, "B 매장", "B사장")
    b_visit = await _started_visit(wired, b_shop, b)
    assert (await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_visit}/record", headers=b,
                                json={"care_note": "B 매장의 메모"})).status_code == 200
    a_visit = await _started_visit(wired, a_shop, a)

    assert error_of(await wired.api.get(f"/v1/shops/{a_shop}/visits/{b_visit}/report", headers=a)) == (
        404, "VISIT_NOT_FOUND")
    assert error_of(await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_visit}/report", headers=a)) == (
        403, "NOT_A_MEMBER")
    assert error_of(await wired.api.get(f"/v1/shops/{a_shop}/visits/{a_visit}/report", headers=a)) == (
        409, "VISIT_NO_RECORD_YET")
    assert (await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_visit}/report", headers=b)).status_code == 200
```

`backend/tests/test_config_defaults.py`:

```diff
@@ -1,33 +1,60 @@
-"""core.config 기본값 — APP_ENV 를 명시하지 않으면 운영으로 간주해야 한다."""
+"""core.config 기본값 — APP_ENV 를 명시하지 않으면 운영으로 간주해야 한다. 알림장 링크의 키는 짧으면 기동하지 않는다."""
 from __future__ import annotations
 
 import base64
 import importlib
 
+import pytest
+
 import core.config
 
 
 class _StubSecretManager:
-    def __init__(self) -> None:
-        self._require_values = {
+    def __init__(self, **values: str) -> None:
+        self._values = {
             "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
             "JWT_PUBLIC_KEY_B64": base64.b64encode(b"test-public-key").decode(),
+            "REPORT_LINK_KEY_B64": base64.b64encode(bytes(32)).decode(),
+            **values,
         }
 
     def get(self, name: str, default: str | None = None) -> str | None:
-        return default
+        return self._values.get(name, default)
 
     def require(self, name: str) -> str:
-        return self._require_values[name]
-
-
-def test_APP_ENV_가_없으면_운영으로_간주한다(monkeypatch):
-    monkeypatch.setattr(
-        "core.singleton.secret_manager.get_secret_manager", lambda: _StubSecretManager()
-    )
-    try:
-        importlib.reload(core.config)
-        assert core.config.APP_ENV == "prod"
-    finally:
-        monkeypatch.undo()
-        importlib.reload(core.config)
+        return self._values[name]
+
+
+@pytest.fixture
+def load_config(monkeypatch):
+    """비밀값 관리자를 스텁으로 바꿔 core.config 를 다시 읽는다. 끝나면 원래 값으로 되돌린다."""
+    def load(**values: str):
+        monkeypatch.setattr(
+            "core.singleton.secret_manager.get_secret_manager", lambda: _StubSecretManager(**values)
+        )
+        return importlib.reload(core.config)
+
+    yield load
+    monkeypatch.undo()
+    importlib.reload(core.config)
+
+
+def test_APP_ENV_가_없으면_운영으로_간주한다(load_config):
+    assert load_config().APP_ENV == "prod"
+
+
+def test_알림장_링크의_키는_base64_를_푼_바이트다(load_config):
+    key = bytes(range(40))
+    assert load_config(REPORT_LINK_KEY_B64=base64.b64encode(key).decode()).REPORT_LINK_KEY == key
+
+
+@pytest.mark.parametrize("size", [0, 16, 31])
+def test_알림장_링크의_키가_32바이트보다_짧으면_기동하지_않는다(load_config, size):
+    with pytest.raises(RuntimeError, match="REPORT_LINK_KEY_B64"):
+        load_config(REPORT_LINK_KEY_B64=base64.b64encode(bytes(size)).decode())
+
+
+def test_알림장_웹_주소는_끝의_빗금을_떼고_비밀값은_없으면_빈_문자열이다(load_config):
+    assert (load_config().REPORT_WEB_BASE_URL, load_config().REPORT_WEB_SECRET) == ("http://127.0.0.1:3010", "")
+    config = load_config(REPORT_WEB_BASE_URL="https://r.chagocnote.com/", REPORT_WEB_SECRET="web-secret")
+    assert (config.REPORT_WEB_BASE_URL, config.REPORT_WEB_SECRET) == ("https://r.chagocnote.com", "web-secret")
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

명령(`infra/`)

`docker compose run --rm --no-deps backend pytest apps/visit/tests/app/services/test_report_reader.py apps/visit/tests/app/use_cases/test_get_visit_report_interactor.py apps/visit/tests/adapter/test_get_visit_report_router.py tests/test_config_defaults.py -q -p no:cacheprovider`
→ `3 errors in 0.10s` — 수집 오류. `ModuleNotFoundError: No module named 'visit.app.dtos.report_view_dto'`, `… 'visit.app.dtos.get_visit_report_dto'`, `… 'visit.adapter.inbound.api.v1.get_visit_report_router'`.

`… pytest tests/test_config_defaults.py …` 만 따로 → `5 failed, 1 passed` — 새 테스트 다섯(키 길이 셋, 키 디코딩, 웹 주소)이 실패, 기존 APP_ENV 테스트는 통과.

`docker compose run --rm backend pytest tests/integration/test_visit_report_wiring.py -q -p no:cacheprovider` → `2 failed` — `ImportError: cannot import name 'REPORT_WEB_BASE_URL' from 'core.config'`, `assert (404, 'NOT_FOUND') == (404, 'VISIT_NOT_FOUND')`(라우트가 없다).

- [ ] **Step 3: 구현한다**

`.env.example`:

```diff
@@ -21,3 +21,8 @@ S3_ENDPOINT_URL=
 S3_ACCESS_KEY=
 S3_SECRET_KEY=
 S3_BUCKET=
+# 미용 알림장 — 링크 서명 키(32바이트 이상을 base64 로. 없으면 API·인증 프로세스가 기동하지 않는다),
+# 보호자 웹의 주소(기본 http://127.0.0.1:3010), 웹 서버와 나누는 비밀값(비우면 웹 서버가 알려 준 접속 주소를 믿지 않는다)
+REPORT_LINK_KEY_B64=
+REPORT_WEB_BASE_URL=
+REPORT_WEB_SECRET=
```

`backend/core/config.py`:

```diff
@@ -16,6 +16,13 @@ def _b64_pem(name: str) -> str:
     return base64.b64decode(raw).decode() if raw else ""
 
 
+def _report_link_key() -> bytes:
+    key = base64.b64decode(_m.require("REPORT_LINK_KEY_B64"))
+    if len(key) < 32:
+        raise RuntimeError("REPORT_LINK_KEY_B64 는 32바이트 이상의 키를 base64 로 적은 값이어야 합니다.")
+    return key
+
+
 # 보안 게이트 기본값은 닫힘이어야 한다 — 운영 배포가 APP_ENV 설정을 빠뜨려도 dev 전용 로그인 제공자가 열리면 안 된다.
 APP_ENV: str = _m.get("APP_ENV", "prod") or "prod"
 DATABASE_URL: str = _m.require("DATABASE_URL")
@@ -42,3 +49,10 @@ S3_REGION: str = _m.get("S3_REGION", "us-east-1") or "us-east-1"
 S3_BUCKET: str = _m.get("S3_BUCKET", "chagocnote-media") or "chagocnote-media"
 S3_ACCESS_KEY: str = _m.get("S3_ACCESS_KEY", "") or ""
 S3_SECRET_KEY: str = _m.get("S3_SECRET_KEY", "") or ""
+
+# 미용 알림장(⑤). 링크의 토큰을 이 키로 서명한다 — 키를 바꾸면 보낸 링크가 모두 닫힌다.
+REPORT_LINK_KEY: bytes = _report_link_key()
+# 보호자가 여는 웹의 주소. 링크는 {REPORT_WEB_BASE_URL}/r/{토큰} 이다.
+REPORT_WEB_BASE_URL: str = (_m.get("REPORT_WEB_BASE_URL", "") or "http://127.0.0.1:3010").rstrip("/")
+# 웹 서버와 나누는 비밀값 — 맞을 때만 웹 서버가 알려 준 접속 주소로 횟수를 센다. 비어 있으면 믿지 않는다.
+REPORT_WEB_SECRET: str = _m.get("REPORT_WEB_SECRET", "") or ""
```

`backend/scripts/generate_dev_env.py`:

```diff
@@ -2,6 +2,7 @@
 from __future__ import annotations
 
 import base64
+import secrets
 from pathlib import Path
 
 from cryptography.fernet import Fernet
@@ -36,7 +37,10 @@ def main() -> None:
         "S3_REGION=us-east-1\n"
         "S3_ACCESS_KEY=chagoc\n"
         "S3_SECRET_KEY=chagoc_dev_minio\n"
-        "S3_BUCKET=chagocnote-dev\n",
+        "S3_BUCKET=chagocnote-dev\n"
+        f"REPORT_LINK_KEY_B64={base64.b64encode(secrets.token_bytes(32)).decode()}\n"
+        "REPORT_WEB_BASE_URL=http://127.0.0.1:3010\n"
+        f"REPORT_WEB_SECRET={secrets.token_urlsafe(32)}\n",
         encoding="utf-8",
     )
     auth_env.write_text(
```

`backend/apps/visit/app/dtos/report_view_dto.py`:

```python
"""알림장을 보여 줄 모양 — 공개 조회와 매장의 미리보기가 함께 쓴다.

보호자 이름·전화번호, 내부 메모, 결제 수단, 예약 메모의 칸은 없다(설계 7.5 R6).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from visit.domain.value_objects.report_settings import ReportSettings


@dataclass(frozen=True)
class ReportMediaView:
    media_id: int            # 매장용 응답에만 나간다. 공개 응답에는 칸이 없다
    kind: str                # photo · video
    phase: str               # before · after
    hidden: bool             # 알림장에서 뺀 것 — 미리보기에만 담긴다
    width: int
    height: int
    duration_seconds: int | None
    display_url: str         # 사진은 표시용, 영상은 원본(재생용)
    thumb_url: str           # 영상이면 포스터
    download_url: str


@dataclass(frozen=True)
class ReportCoverView:
    url: str                 # 사진이면 표시용, 영상이면 포스터
    width: int
    height: int


@dataclass(frozen=True)
class ReportMenuView:
    name: str
    amount: int | None       # 금액을 끄면 None


@dataclass(frozen=True)
class ReportShopView:
    name: str
    phone: str | None
    address: str | None


@dataclass(frozen=True)
class ReportView:
    """끈 항목은 조립할 때 비운다(None) — 받는 쪽이 숨기는 것이 아니다(설계 7.5 R7)."""

    pet_name: str | None                      # 보호자만의 방문이거나 이름을 얻지 못하면 None
    visit_date: date                          # 방문 시작 시각의, 매장 시간대의 날짜
    care_note: str | None
    media: tuple[ReportMediaView, ...]        # 후 → 전, 그 안에서 순서대로
    cover: ReportCoverView | None             # 빼지 않은 것 가운데 대표
    menus: tuple[ReportMenuView, ...] | None  # 메뉴를 끄면 None
    total_amount: int | None                  # 금액을 켰을 때만
    weight_kg: Decimal | None                 # 몸무게를 켰을 때만
    shop: ReportShopView | None               # 매장 정보를 켰을 때만
    settings: ReportSettings                  # 공개 응답이 끈 항목의 칸을 아예 빼는 데 쓴다


@dataclass(frozen=True)
class ReportLinkView:
    """링크의 상태. 살아 있는 링크가 없으면 status 만 none 이고 나머지는 None 이다."""

    status: str                # none · live
    url: str | None
    expires_at: datetime | None       # None 이면 기간이 없다
    first_viewed_at: datetime | None
    created_at: datetime | None       # 보낸 시각

    def in_zone(self, zone: ZoneInfo) -> ReportLinkView:
        """시각을 매장 시간대로 바꾼 것 — 응답으로 내보내기 전에 부른다."""
        def local(moment: datetime | None) -> datetime | None:
            return moment.astimezone(zone) if moment is not None else None

        return replace(self, expires_at=local(self.expires_at), first_viewed_at=local(self.first_viewed_at),
                       created_at=local(self.created_at))
```

`backend/apps/visit/app/services/report_reader.py`:

```python
"""알림장을 보여 줄 모양으로 조립한다 — 공개 조회와 매장의 미리보기가 같은 함수를 쓴다.

매장이 끈 항목과 뺀 사진은 여기서 뺀다. 반려동물 이름은 허브 포트로 읽고 보호자는 읽지 않는다(설계 6.3).
"""
from __future__ import annotations

from dataclasses import replace

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportLinkView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.entities.visit_report import VisitReport
from visit.domain.services.report_rules import hide, report_cover_media_id, visible_media
from visit.domain.services.report_token import make_token
from visit.domain.services.visit_schedule import local_date
from visit.domain.value_objects.report_settings import ReportSettings


async def describe_report(
    ctx: ShopContext, visit: Visit, record: VisitRecord, settings: ReportSettings, shop: ShopProfile,
    menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort, *, include_hidden: bool,
) -> ReportView:
    hidden = {m.media_id for m in record.media if m.hidden}
    # 미리보기는 뺀 것도 같은 순서로 보여 준다 — 표시를 모두 지운 기록에 보이는 순서 규칙을 그대로 쓴다.
    shown = visible_media(replace(record, media=hide(record, ())) if include_hidden else record)
    urls = await library.read_urls(ctx, [m.media_id for m in shown])
    cover = urls.get(report_cover_media_id(record))
    return ReportView(
        pet_name=await _pet_name(ctx, visit, directory),
        visit_date=local_date(visit.starts_at, ctx.timezone),
        care_note=record.care_note if record.care_note and record.care_note.strip() else None,
        media=tuple(
            ReportMediaView(
                media_id=m.media_id, kind=m.kind, phase=m.phase, hidden=m.media_id in hidden,
                width=urls[m.media_id].width, height=urls[m.media_id].height,
                duration_seconds=urls[m.media_id].duration_seconds,
                display_url=urls[m.media_id].display_url or urls[m.media_id].original_url,
                thumb_url=urls[m.media_id].thumb_url, download_url=urls[m.media_id].download_url,
            )
            for m in shown if m.media_id in urls
        ),
        cover=ReportCoverView(url=cover.display_url or cover.thumb_url, width=cover.width, height=cover.height)
        if cover else None,
        menus=await _menus(ctx, record, settings, menus) if settings.show_menus else None,
        total_amount=record.total_amount if settings.show_amount else None,
        weight_kg=record.weight_kg if settings.show_weight else None,
        shop=ReportShopView(name=shop.name, phone=shop.phone, address=shop.address)
        if settings.show_shop_info else None,
        settings=settings,
    )


async def _pet_name(ctx: ShopContext, visit: Visit, directory: CustomerDirectoryPort) -> str | None:
    """익명화한 고객의 아이는 이름이 없고 지워진 아이는 요약에 없다. 무지개다리를 건넌 아이는 이름이 남아 있다."""
    if visit.pet_id is None:
        return None
    pet = (await directory.briefs(ctx, [], [visit.pet_id])).pets.get(visit.pet_id)
    return pet.name if pet else None


async def _menus(
    ctx: ShopContext, record: VisitRecord, settings: ReportSettings, menus: MenuRepository
) -> tuple[ReportMenuView, ...]:
    """실제로 한 메뉴(기록의 항목). 이름은 메뉴표(보관한 것도)에서 읽는다."""
    if not record.items:
        return ()
    names = {m.id: m.name for m in await menus.list_by_ids(ctx, [i.menu_id for i in record.items])}
    return tuple(
        ReportMenuView(name=names[i.menu_id], amount=i.amount if settings.show_amount else None)
        for i in record.items
    )


def describe_link(report: VisitReport | None, key: bytes, base_url: str) -> ReportLinkView:
    """report 는 살아 있는 링크(없으면 None). 주소는 저장하지 않고 public_id 와 키로 그때마다 만든다."""
    if report is None:
        return ReportLinkView(status="none", url=None, expires_at=None, first_viewed_at=None, created_at=None)
    return ReportLinkView(
        status="live", url=f"{base_url}/r/{make_token(report.public_id, key)}", expires_at=report.expires_at,
        first_viewed_at=report.first_viewed_at, created_at=report.created_at,
    )
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_report_schema.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.get_report_settings_schema import ReportSettingsSchema
from visit.adapter.inbound.api.schemas.report_view_schema import ReportLinkSchema, ReportSchema
from visit.app.dtos.get_visit_report_dto import VisitReportPreview


class VisitReportSchema(BaseModel):
    report: ReportSchema
    link: ReportLinkSchema
    settings: ReportSettingsSchema   # 앱이 "함께 보이는 항목"을 이것으로 그린다

    @classmethod
    def of(cls, view: VisitReportPreview) -> VisitReportSchema:
        return cls(
            report=ReportSchema.model_validate(view.report, from_attributes=True),
            link=ReportLinkSchema.model_validate(view.link, from_attributes=True),
            settings=ReportSettingsSchema.of(view.report.settings),
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/report_view_schema.py`:

```python
"""매장용 알림장 응답 모양(app 의 report_view_dto 와 짝). 끈 항목의 칸은 null 이다.

공개 응답은 따로 둔다 — 거기에는 media_id·hidden 이 없고 끈 항목은 칸이 아예 없다.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ReportMediaSchema(BaseModel):
    media_id: int
    kind: str                 # photo · video
    phase: str                # before · after
    hidden: bool              # 알림장에서 뺀 것
    width: int
    height: int
    duration_seconds: int | None
    display_url: str          # 사진은 표시용, 영상은 원본(재생용)
    thumb_url: str            # 영상이면 포스터
    download_url: str


class ReportCoverSchema(BaseModel):
    url: str
    width: int
    height: int


class ReportMenuSchema(BaseModel):
    name: str
    amount: int | None


class ReportShopSchema(BaseModel):
    name: str
    phone: str | None
    address: str | None


class ReportSchema(BaseModel):
    pet_name: str | None
    visit_date: date
    care_note: str | None
    media: list[ReportMediaSchema]   # 후 → 전, 그 안에서 순서대로
    cover: ReportCoverSchema | None
    menus: list[ReportMenuSchema] | None
    total_amount: int | None
    weight_kg: float | None          # JSON 숫자로 내보낸다(기록 응답과 같은 관례)
    shop: ReportShopSchema | None


class ReportLinkSchema(BaseModel):
    status: str                      # none · live
    url: str | None
    expires_at: datetime | None      # null 이면 기간이 없다
    first_viewed_at: datetime | None
    created_at: datetime | None
```

`backend/apps/visit/adapter/inbound/api/v1/get_visit_report_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_visit_report_schema import VisitReportSchema
from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery
from visit.app.ports.input.get_visit_report_use_case import GetVisitReportUseCase
from visit.dependencies.get_visit_report_provider import get_get_visit_report_use_case

get_visit_report_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_report_router.get("/{shop_id}/visits/{visit_id}/report", response_model=VisitReportSchema)
async def get_visit_report(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitReportUseCase = Depends(get_get_visit_report_use_case),
) -> VisitReportSchema:
    return VisitReportSchema.of(await use_case.get_visit_report(GetVisitReportQuery(ctx=ctx, visit_id=visit_id)))
```

`backend/apps/visit/app/dtos/get_visit_report_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.report_view_dto import ReportLinkView, ReportView


@dataclass(frozen=True)
class GetVisitReportQuery:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class VisitReportPreview:
    report: ReportView     # 보호자가 볼 내용에 뺀 사진·영상(hidden)을 더한 것. 매장의 설정은 report.settings
    link: ReportLinkView   # 시각은 매장 시간대
```

`backend/apps/visit/app/ports/input/get_visit_report_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery, VisitReportPreview


class GetVisitReportUseCase(ABC):
    @abstractmethod
    async def get_visit_report(self, query: GetVisitReportQuery) -> VisitReportPreview: ...
```

`backend/apps/visit/app/use_cases/get_visit_report_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery, VisitReportPreview
from visit.app.ports.input.get_visit_report_use_case import GetVisitReportUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.report_reader import describe_link, describe_report
from visit.domain.errors import VisitNoRecordYetError


class GetVisitReportInteractor(GetVisitReportUseCase):
    """알림장 미리보기 — 보호자가 볼 내용과 링크의 상태. 읽기만 하므로 잠그지 않는다.
    보내기 전에 보는 화면이라 완료하지 않은 방문도 기록이 있으면 준다."""

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
        reports: ReportRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        library: MediaLibraryPort, shops: ShopProfilePort, now: Callable[[], datetime], link_key: bytes,
        web_base_url: str,
    ) -> None:
        self._visits = visits
        self._records = records
        self._settings = settings
        self._reports = reports
        self._menus = menus
        self._directory = directory
        self._library = library
        self._shops = shops
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def get_visit_report(self, query: GetVisitReportQuery) -> VisitReportPreview:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        record = await self._records.get(ctx, visit.id)
        if record is None:
            raise VisitNoRecordYetError("기록을 먼저 남겨 주세요.")
        report = await describe_report(
            ctx, visit, record, await self._settings.get(ctx), await self._shops.public_profile(ctx.shop_id),
            self._menus, self._directory, self._library, include_hidden=True,
        )
        live = await self._reports.get_live(ctx, visit.id, self._now())
        link = describe_link(live, self._link_key, self._web_base_url)
        return VisitReportPreview(report=report, link=link.in_zone(ZoneInfo(ctx.timezone)))
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -46,6 +46,8 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "POST /menus/{menu_id}/archive(메뉴표 — 지우지 않고 보관)도 있습니다. "
                 "GET·PUT /report-settings 는 알림장 설정입니다(링크 기간 link_days 7·30·null(계속), 보호자에게 보여 줄 "
                 "항목 show_menus·show_shop_info·show_weight·show_amount — PUT 은 다섯 칸 전체 교체). "
+                "GET /visits/{visit_id}/report 는 알림장 미리보기입니다(보호자가 볼 내용 report — 끈 항목은 null, "
+                "사진영상마다 뺀 것인지 hidden — 과 링크 상태 link, 설정 settings. 기록이 없으면 409). "
                 "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴·알림장 설정 수정은 shop:update(사장)가 필요합니다. "
                 "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                 "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
```

`backend/apps/visit/dependencies/get_visit_report_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.get_visit_report_use_case import GetVisitReportUseCase
from visit.app.use_cases.get_visit_report_interactor import GetVisitReportInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library, get_shop_profile
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_record_repository,
    build_report_repository,
    build_report_settings_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_get_visit_report_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> GetVisitReportUseCase:
    return GetVisitReportInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db),
        settings=build_report_settings_repository(db), reports=build_report_repository(db),
        menus=build_menu_repository(db), directory=directory, library=library, shops=shops, now=utc_now,
        link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
    )
```

`backend/main.py`:

```diff
@@ -75,6 +75,7 @@ from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_vi
 from visit.adapter.inbound.api.v1.get_report_settings_router import get_report_settings_router
 from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
 from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
+from visit.adapter.inbound.api.v1.get_visit_report_router import get_visit_report_router
 from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
 from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
 from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
@@ -168,6 +169,7 @@ app.include_router(get_next_visit_draft_router)
 app.include_router(put_visit_record_router)
 app.include_router(append_record_media_router)
 app.include_router(delete_visit_record_router)
+app.include_router(get_visit_report_router)
 # media
 app.include_router(media_myself_router)
 app.include_router(issue_upload_router)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 테스트 | 새로 더한 것 56 — 조립 33, 인터랙터 7, 라우터 9, 설정 5(파일 전체는 6), 배선 2. 자기소개·스텁 포트 테스트는 기존 것이 그대로 통과 |
| 단위 전체 | 1135 passed, 354 deselected (시작 1081 → +54) |
| 통합 전체 | 354 passed, 1135 deselected (시작 352 → +2) |
| 구조 계약 | 6 kept, 0 broken (Analyzed 1072 files, 4619 dependencies) |

- `docker compose run --rm --no-deps auth python scripts/print_routes.py` 를 돌렸다. `backend GET /v1/shops/{shop_id}/visits/{visit_id}/report get_visit_report` 가 나온다.
- `tests/test_hub_port_binding.py` 는 작업 테스트와 함께 돌릴 때 맨 뒤에 뒀다. 통과한다(새 라우트가 `get_shop_profile` 자리를 쓰므로 이제 `route_inspection` 도 그 꽂기를 본다).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `describe_report` 의 `total_amount=… if settings.show_amount else None` → 늘 준다 → `test_넷_다_꺼도_이름과_날짜와_케어_메모와_사진은_담는다`, `test_메뉴와_금액은_따로_켜고_끈다[메뉴_켬_금액_끔]`
- 메뉴의 `amount` 를 늘 준다 → `test_메뉴와_금액은_따로_켜고_끈다[메뉴_켬_금액_끔]`
- `include_hidden=False` 인데 거르지 않는다(`if True else record`) → `test_뺀_사진은_담지_않는다`
- 대표를 기존 `cover_media_id(record.media)` 로 고른다 → `test_대표는_빼지_않은_것_가운데서_고른다` 의 7개(`hidden1`~`hidden4`), 인터랙터 `test_미리보기는_뺀_사진을_표시와_함께_주고_보낸_적이_없으면_링크가_없다`, 배선 `test_직원이_알림장을_미리_보고_설정과_링크가_그대로_비친다`
- `ReportView` 에 `internal_note` 칸을 더해 채운다 → `test_내부_메모와_결제_수단과_예약_메모와_보호자_정보는_어디에도_없다[False]`·`[True]`, `test_알림장에는_정해_둔_칸만_있다`
- 인터랙터가 방문을 `ctx` 없이 읽는다(`self._visits.rows[query.visit_id]` — 스텁에서만 되는 변이) → 인터랙터 `test_없는_방문과_다른_매장의_방문은_VISIT_NOT_FOUND_다`(pg 에는 `rows` 가 없어 배선 둘도 실패)
- `VisitPgRepository._read` 의 매장 조건 제거 → 배선 `test_다른_매장의_방문은_미리_볼_수_없고_기록이_없으면_409_다`(404 대신 409 — 기록 저장소가 매장으로 걸러 기록이 없다고 본다), 기존 `test_visit_pg_repository.py` 다섯
- `show_weight` 검사 제거 → `test_넷_다_꺼도_…`, `test_몸무게와_매장_정보도_따로_켜고_끈다[매장_정보만]`, 배선 첫 테스트
- `show_shop_info` 검사 제거 → `test_넷_다_꺼도_…`, `test_몸무게와_매장_정보도_따로_켜고_끈다[몸무게만]`, 배선 첫 테스트
- `show_menus` 검사 제거 → `test_넷_다_꺼도_…`, `test_메뉴와_금액은_따로_켜고_끈다[메뉴_끔_금액_켬]`, 인터랙터 `test_매장이_정한_설정대로_담는다`, 배선 첫 테스트
- `_pet_name` 의 `pet_id is None` 검사 제거 → **처음에는 살아남았다(81 passed).** 스텁에 ID 가 None 인 아이를 넣게 고친 뒤 `test_보호자만의_방문은_반려동물_이름이_없다` 가 실패
- 인터랙터가 `include_hidden=False` 로 부른다 → 인터랙터 `test_미리보기는_뺀_사진을_…`, 배선 첫 테스트
- 인터랙터가 `in_zone` 을 부르지 않는다 → 인터랙터 `test_살아_있는_링크의_주소와_시각을_매장_시간대로_준다`, 배선 첫 테스트
- 기록 없음 검사 제거 → 인터랙터 `test_기록이_없는_방문은_VISIT_NO_RECORD_YET_이다`, 배선 둘째 테스트
- `main.py` 에 라우터를 등록하지 않는다 → 배선 테스트 둘
- 프로바이더가 `link_key=bytes(32)` 를 넘긴다 → 배선 첫 테스트(토큰이 `REPORT_LINK_KEY` 로 읽히지 않는다 — 이 확인은 변이를 보려고 더했다)
- 프로바이더가 `web_base_url=''` 을 넘긴다 → 배선 첫 테스트
- 키 길이 검사 `< 32` → `< 16` → `test_알림장_링크의_키가_32바이트보다_짧으면_기동하지_않는다[16]`·`[31]`
- `< 32` → `<= 32` → `core.config` 를 import 하는 파일 넷이 수집 오류(`.env` 의 키가 32바이트다)
- 웹 주소의 `rstrip("/")` 제거 → `test_알림장_웹_주소는_끝의_빗금을_떼고_비밀값은_없으면_빈_문자열이다`
- 빈 케어 메모를 그대로 준다 → `test_몸무게와_메모가_없으면_켜져_있어도_비어_있다[]`·`[  \n ]`
- 영상의 `display_url` 에 원본을 넣지 않는다 → `test_사진은_표시용_영상은_원본_주소를_준다`
- 대표의 주소를 늘 썸네일로 → `test_대표는_빼지_않은_것_가운데서_고른다` 의 6개, 인터랙터·배선 하나씩
- `hidden` 을 늘 False 로 → `test_미리보기는_뺀_사진도_같은_순서에_표시와_함께_담는다`, 인터랙터·배선 하나씩
- 라우터 가드를 `require_permission("record:write")` 로 → `test_권한이_없는_멤버도_알림장을_미리_본다`
- `get_live` 에 1년 전 시각을 넘긴다 → 인터랙터 `test_기간이_지난_링크는_없는_것이다`
- 방문 날짜를 UTC 날짜로 → `test_방문_날짜는_매장_시간대의_날짜다`
- 토큰을 뒤집은 키로 서명한다 → `test_링크의_주소는_웹_주소와_서명한_토큰_43글자다`, 인터랙터·배선 하나씩

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 알림장 조립과 미리보기 — 켠 항목과 빼지 않은 사진만 담는다(GET visits/{id}/report)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 알림장 보내기와 끊기 — 방문당 살아 있는 링크 하나, 기록을 저장해도 뺀 사진은 빠져 있다

**Files:**
- Create: `backend/apps/visit/adapter/inbound/api/schemas/send_visit_report_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/revoke_visit_report_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/send_visit_report_router.py`
- Create: `backend/apps/visit/app/dtos/revoke_visit_report_dto.py`
- Create: `backend/apps/visit/app/dtos/send_visit_report_dto.py`
- Create: `backend/apps/visit/app/ports/input/revoke_visit_report_use_case.py`
- Create: `backend/apps/visit/app/ports/input/send_visit_report_use_case.py`
- Modify: `backend/apps/visit/app/use_cases/put_visit_record_interactor.py`
- Create: `backend/apps/visit/app/use_cases/revoke_visit_report_interactor.py`
- Create: `backend/apps/visit/app/use_cases/send_visit_report_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/dependencies/revoke_visit_report_provider.py`
- Create: `backend/apps/visit/dependencies/send_visit_report_provider.py`
- Modify: `backend/apps/visit/domain/services/visit_record_rules.py`
- Create: `backend/apps/visit/tests/adapter/test_revoke_visit_report_router.py`
- Create: `backend/apps/visit/tests/adapter/test_send_visit_report_router.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_append_record_media_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_put_visit_record_interactor.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_revoke_visit_report_interactor.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_send_visit_report_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Modify: `backend/apps/visit/tests/domain/test_visit_record_rules.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_visit_report_locking.py`
- Modify: `backend/tests/integration/test_visit_report_wiring.py`

**Interfaces:**
- Consumes: 작업 1 의 `check_sendable`·`check_not_empty`·`expires_at_for`·`new_public_id`·`carry_hidden`; 작업 2 의 `ReportRepository`·`set_hidden`; 작업 5 의 `describe_report`·`describe_link`·`VisitReportPreview`·`VisitReportSchema`; `visit_locking.lock_visits`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# visit/app/dtos/send_visit_report_dto.py
@dataclass(frozen=True)
class SendVisitReportCommand:
    ctx: ShopContext
    visit_id: int
    hidden_media_ids: tuple[int, ...]      # 뺄 것 전부. 없는 것은 앞서 뺐더라도 되살아난다

# visit/app/dtos/revoke_visit_report_dto.py
@dataclass(frozen=True)
class RevokeVisitReportCommand:
    ctx: ShopContext
    visit_id: int

# 입력 포트
SendVisitReportUseCase.send_visit_report(command) -> VisitReportPreview      # T5 의 DTO 그대로
RevokeVisitReportUseCase.revoke_visit_report(command) -> None

# 인터랙터
SendVisitReportInteractor(visits: VisitLookupRepository, records: VisitRecordRepository,
    settings: ReportSettingsRepository, reports: ReportRepository, menus: MenuRepository,
    directory: CustomerDirectoryPort, library: MediaLibraryPort, shops: ShopProfilePort,
    now: Callable[[], datetime], link_key: bytes, web_base_url: str)       # GetVisitReportInteractor 와 같은 인자
RevokeVisitReportInteractor(visits: VisitLookupRepository, reports: ReportRepository,
    directory: CustomerDirectoryPort, now: Callable[[], datetime])

# 프로바이더
get_send_visit_report_use_case(db, directory, library, shops) -> SendVisitReportUseCase
get_revoke_visit_report_use_case(db, directory) -> RevokeVisitReportUseCase

# 스키마 — visit/adapter/inbound/api/schemas/send_visit_report_schema.py
SendVisitReportRequestSchema(hidden_media_ids: Annotated[list[EntityId], Field(max_length=MAX_HIDDEN)])   # 필수 칸
# 응답은 get_visit_report_schema.VisitReportSchema

# 라우터
send_visit_report_router     PUT    /v1/shops/{shop_id}/visits/{visit_id}/report   require_permission("record:write")   200
revoke_visit_report_router   DELETE /v1/shops/{shop_id}/visits/{visit_id}/report   require_permission("record:write")   204

# 고친 도메인 함수(시그니처는 그대로)
append_media(media, media_id, kind, phase) -> tuple[RecordMedia, ...]   # 있던 미디어는 sort_order 만 바뀐다
```

`SendVisitReportInteractor.send_visit_report` 의 순서

1. `lock_visits` (고객 행 → 방문 행)
2. `records.get` → `check_sendable(visit, record, hidden_ids)`
3. `settings.get`
4. `reports.close_expired` → `reports.get_live`
5. 없으면 `check_not_empty` → `reports.create(ctx, visit_id, new_public_id(), expires_at_for(now, link_days), now)`
6. `records.set_hidden`
7. `records.get` 을 다시 → `describe_report(include_hidden=True)`, `describe_link(live).in_zone(…)`

뒤 작업이 알아 둘 동작
- **`now` 는 요청 하나에서 한 번만 읽는다.** 닫기·살아 있음 판단·`created_at`·`expires_at` 이 같은 시각이다.
- **오류의 순서**: `VISIT_NOT_FOUND` → (가족 잠금의 허브 오류) → `VISIT_NOT_COMPLETED` → `VISIT_NO_RECORD_YET` → `VALIDATION_ERROR`(남의 미디어·중복) → `REPORT_EMPTY`.
- **링크의 기간은 만들 때 정해진다.** 그 뒤 매장이 설정을 바꿔도 살아 있는 링크의 `expires_at` 은 그대로다. 응답의 `settings` 는 지금 설정이다.
- **살아 있는 링크가 있으면 `REPORT_EMPTY` 를 보지 않는다.** 전부 빼도 되고, 응답의 `cover` 는 `null` 이다.
- **기간이 지난 줄을 닫을 때 `revoked_at` 에 지금 시각이 들어간다.** 끊은 줄과 기간이 지나 닫힌 줄은 `revoked_at` 만으로는 구분되지 않는다(`expires_at <= revoked_at` 이면 기간이 지나 닫힌 것).
- **거절된 요청의 `close_expired` 는 HTTP 경로에서는 되돌려진다**(예외면 세션이 롤백). 인터랙터만 놓고 보면 `REPORT_EMPTY` 로 거절되기 전에 기간이 지난 줄이 닫힌다 — 이미 살아 있지 않은 줄이라 보이는 결과는 같다.
- **끊기는 뺀 표시를 건드리지 않는다.** 끊은 뒤 미리보기(GET)는 앞서 뺀 사진을 여전히 `hidden: true` 로 준다.
- **끊기는 방문의 상태를 보지 않는다.** 방문이 이 매장의 것이고 살아 있는 링크가 있으면 끊는다.
- **기록 PUT·덧붙이기의 응답에는 `hidden` 이 없다**(`RecordMediaView` 에 칸이 없다). 앱은 뺀 표시를 미리보기(GET `…/report`)에서만 본다.
- T7 이 쓸 것: `reports.get_live`·`live_visit_ids` 는 그대로다. 되돌리기·기록 삭제가 링크를 볼 때는 같은 `lock_visits` 뒤에 읽어야 R9 가 성립한다.
- 스텁 journal 의 순서(처음 보내기): `lock_family`, `lock_visits`, `close_expired_reports`, `create_report`, `set_hidden`.

설계 3.2·6.1·7.4, R2·R4·R5·R8·R14·R20. 순서가 곧 규칙이다 — 잠금 → 검사 → 기간 지난 줄 닫기 → 살아 있는 줄 확인 → 없을 때만 만들기 → 뺀 표시 쓰기. `create` 는 유일 위반을 그대로 던지므로 이 순서를 어기면 트랜잭션이 깨진다. **기록 저장이 뺀 표시를 잇는 것(R5)이 이 작업에서 가장 중요하다** — 전체 교체는 `carry_hidden`, 덧붙이기는 `append_media` 가 있던 미디어의 순서만 바꾼다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_revoke_visit_report_router.py`:

```python
import pytest

from visit.adapter.inbound.api.v1.revoke_visit_report_router import revoke_visit_report_router
from visit.dependencies.revoke_visit_report_provider import get_revoke_visit_report_use_case
from visit.domain.errors import ReportNotFoundError, VisitNotFoundError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of


async def _delete(stub, path="/v1/shops/3/visits/4/report", access=None):
    async with client(build_app(revoke_visit_report_router, get_revoke_visit_report_use_case, stub, access)) as c:
        return await c.delete(path)


async def test_직원은_알림장_링크를_끊는다_204():
    stub = Recorder(None)
    response = await _delete(stub, access=STAFF)
    assert (response.status_code, response.content) == (204, b"")
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].visit_id) == (3, 4)


async def test_기록_권한이_없으면_끊지_못한다():
    stub = Recorder(None)
    assert error_of(await _delete(stub, access=READ_ONLY)) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


async def test_살아_있는_링크가_없으면_404_없는_방문도_404_다():
    assert error_of(await _delete(Recorder(error=ReportNotFoundError("없음")))) == (404, "REPORT_NOT_FOUND")
    assert error_of(await _delete(Recorder(error=VisitNotFoundError("없음")))) == (404, "VISIT_NOT_FOUND")


@pytest.mark.parametrize("visit_id", ["9223372036854775808", "0", "-1", "1.5", "abc", "1" * 400])
async def test_방문_ID_가_범위_밖이거나_숫자가_아니면_422_다(visit_id):
    stub = Recorder(None)
    assert error_of(await _delete(stub, f"/v1/shops/3/visits/{visit_id}/report")) == (422, "VALIDATION_ERROR")
    assert stub.calls == []
```

`backend/apps/visit/tests/adapter/test_send_visit_report_router.py`:

```python
from datetime import date

import pytest

from visit.adapter.inbound.api.v1.send_visit_report_router import send_visit_report_router
from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.report_view_dto import ReportLinkView, ReportMediaView, ReportView
from visit.dependencies.send_visit_report_provider import get_send_visit_report_use_case
from visit.domain.errors import (
    ReportEmptyError,
    VisitInputError,
    VisitNoRecordYetError,
    VisitNotCompletedError,
    VisitNotFoundError,
)
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.builders import kst

MAX_BIGINT = 9_223_372_036_854_775_807
SENT = VisitReportPreview(
    report=ReportView(
        pet_name="콩이", visit_date=date(2026, 9, 23), care_note="눈물 자국",
        media=(ReportMediaView(media_id=52, kind="photo", phase="after", hidden=True, width=3000, height=2000,
                               duration_seconds=None, display_url="d/52", thumb_url="t/52", download_url="dl/52"),),
        cover=None, menus=(), total_amount=None, weight_kg=None, shop=None, settings=DEFAULT_REPORT_SETTINGS,
    ),
    link=ReportLinkView(status="live", url="https://r.example/r/token", expires_at=kst(10, 23, 15),
                        first_viewed_at=None, created_at=kst(9, 23, 15)),
)


async def _put(stub, body, path="/v1/shops/3/visits/4/report", access=None):
    async with client(build_app(send_visit_report_router, get_send_visit_report_use_case, stub, access)) as c:
        return await c.put(path, json=body)


async def test_직원은_알림장을_보내고_미리보기와_같은_모양을_받는다():
    stub = Recorder(SENT)
    response = await _put(stub, {"hidden_media_ids": [52, MAX_BIGINT]}, access=STAFF)
    assert response.status_code == 200
    assert set(response.json()) == {"report", "link", "settings"}
    assert response.json()["link"]["url"] == "https://r.example/r/token"
    assert [(m["media_id"], m["hidden"]) for m in response.json()["report"]["media"]] == [(52, True)]
    assert response.json()["settings"]["link_days"] == 30
    call = stub.calls[0]
    assert (call.ctx.shop_id, call.visit_id, call.hidden_media_ids) == (3, 4, (52, MAX_BIGINT))


async def test_뺄_것이_없으면_빈_배열을_보내고_33개까지_받는다():
    stub = Recorder(SENT)
    assert (await _put(stub, {"hidden_media_ids": []})).status_code == 200
    assert (await _put(stub, {"hidden_media_ids": list(range(1, 34))})).status_code == 200
    assert [len(call.hidden_media_ids) for call in stub.calls] == [0, 33]


async def test_기록_권한이_없으면_보내지_못한다():
    stub = Recorder(SENT)
    assert error_of(await _put(stub, {"hidden_media_ids": []}, access=READ_ONLY)) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


@pytest.mark.parametrize("body", [
    {}, {"hidden_media_ids": None}, {"hidden_media_ids": 52}, {"hidden_media_ids": "52"},
    {"hidden_media_ids": {"52": True}}, {"hidden_media_ids": ["52"]}, {"hidden_media_ids": [52.0]},
    {"hidden_media_ids": [1.5]}, {"hidden_media_ids": [True]}, {"hidden_media_ids": [None]},
    {"hidden_media_ids": [[52]]}, {"hidden_media_ids": [0]}, {"hidden_media_ids": [-1]},
    {"hidden_media_ids": [MAX_BIGINT + 1]}, {"hidden_media_ids": [52, "가" * 5000]},
    {"hidden_media_ids": list(range(1, 35))}, {"hidden_media_ids": list(range(1, 5001))},
    [52], "52", None,
], ids=lambda body: str(body)[:40])
async def test_뺄_목록이_빠졌거나_정수가_아니거나_범위_밖이거나_33개를_넘으면_422_다(body):
    """R14"""
    stub = Recorder(SENT)
    assert error_of(await _put(stub, body)) == (422, "VALIDATION_ERROR")
    assert stub.calls == []


@pytest.mark.parametrize("visit_id", ["9223372036854775808", "0", "-1", "1.5", "abc", "1" * 400])
async def test_방문_ID_가_범위_밖이거나_숫자가_아니면_422_다(visit_id):
    stub = Recorder(SENT)
    response = await _put(stub, {"hidden_media_ids": []}, f"/v1/shops/3/visits/{visit_id}/report")
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (VisitNotFoundError("없음"), (404, "VISIT_NOT_FOUND")),
    (VisitNotCompletedError("완료 전"), (409, "VISIT_NOT_COMPLETED")),
    (VisitNoRecordYetError("기록 없음"), (409, "VISIT_NO_RECORD_YET")),
    (ReportEmptyError("빈 알림장"), (422, "REPORT_EMPTY")),
    (VisitInputError("남의 미디어"), (422, "VALIDATION_ERROR")),
])
async def test_도메인_거절은_코드로_나간다(error, expected):
    assert error_of(await _put(Recorder(error=error), {"hidden_media_ids": []})) == expected
```

`backend/apps/visit/tests/app/use_cases/test_append_record_media_interactor.py`:

```diff
@@ -83,3 +83,16 @@ async def test_영상은_세_편까지다():
     w.existing([RecordMedia(i, "video", "after", i - 61) for i in (61, 62, 63)])
     with pytest.raises(RecordMediaLimitError):
         await w.append(64)
+
+
+@pytest.mark.parametrize("phase", ["before", "after"])
+async def test_알림장에서_뺀_사진은_덧붙인_뒤에도_빠져_있고_새_사진은_보인다(phase):
+    """R5 — 새 사진이 뺀 사진과 같은 칸에 붙든 다른 칸에 붙든."""
+    w = _World(status="completed")
+    for i in (51, 52, 53):
+        w.library.add(i, attached=i != 53)
+    w.existing([RecordMedia(51, "photo", "before", 4, hidden=True), RecordMedia(52, "photo", "after", 0)])
+
+    await w.append(53, phase)
+
+    assert {m.media_id: m.hidden for m in w.records.rows[w.visit.id].media} == {51: True, 52: False, 53: False}
```

`backend/apps/visit/tests/app/use_cases/test_put_visit_record_interactor.py`:

```diff
@@ -158,3 +158,25 @@ async def test_익명화한_고객과_다른_매장의_방문은_쓸_수_없다(
         await w.put(record())
     with pytest.raises(VisitNotFoundError):
         await w.put(record(), context=ctx(shop_id=2))
+
+
+async def test_알림장에서_뺀_사진은_기록을_다시_저장해도_빠져_있다():
+    """R5 — 저장은 미디어 줄을 지우고 다시 넣는다. 뺀 표시는 자리가 아니라 미디어 ID 를 따라간다."""
+    w = _World(status="completed")
+    for i in (51, 52, 53):
+        w.library.add(i, attached=i != 53)
+    w.existing(media=[RecordMedia(51, "photo", "after", 0, hidden=True), RecordMedia(52, "photo", "after", 1)])
+
+    await w.put(record(media=[at(53, order=0), at(52, order=1), at(51, "before", 0)]), version=2)   # 자리를 바꿨다
+
+    assert {m.media_id: m.hidden for m in w.records.rows[w.visit.id].media} == {53: False, 52: False, 51: True}
+    await w.put(record(care="메모만 고침", media=[at(53, order=0), at(52, order=1), at(51, "before", 0)]), version=3)
+    assert {m.media_id: m.hidden for m in w.records.rows[w.visit.id].media} == {53: False, 52: False, 51: True}
+
+
+async def test_기록_응답에는_뺀_표시가_없다():
+    w = _World(status="completed")
+    w.library.add(51, attached=True)
+    w.existing(media=[RecordMedia(51, "photo", "after", 0, hidden=True)])
+    view = await w.put(record(media=[at(51)]), version=2)
+    assert not hasattr(view.media[0], "hidden")
```

`backend/apps/visit/tests/app/use_cases/test_revoke_visit_report_interactor.py`:

```python
from datetime import timedelta

import pytest

from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
from visit.domain.errors import ReportNotFoundError, VisitNotFoundError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeReportRepository, FakeVisits, Journal

NOW = kst(9, 24, 10)


class _World:
    def __init__(self) -> None:
        self.journal = Journal()
        self.visits = FakeVisits(self.journal)
        self.reports = FakeReportRepository(self.visits, self.journal)
        directory = FakeDirectory(self.journal)
        directory.family(1, pets=(101,))
        self.interactor = RevokeVisitReportInteractor(self.visits, self.reports, directory, now=lambda: NOW)

    async def sent(self, expires_at=None, **fields) -> int:
        """어제 보낸 링크가 달린 완료 방문."""
        found = self.visits.seed(status="completed", started_at=kst(9, 23, 14), **fields)
        await self.reports.create(ctx(shop_id=found.shop_id), found.id, bytes(16), expires_at, NOW - timedelta(days=1))
        self.journal.clear()
        return found.id

    async def revoke(self, visit_id, shop_id=1):
        await self.interactor.revoke_visit_report(RevokeVisitReportCommand(ctx=ctx(shop_id=shop_id), visit_id=visit_id))


async def test_잠근_뒤_살아_있는_링크를_끊는다():
    w = _World()
    visit_id = await w.sent(expires_at=NOW + timedelta(days=6))
    await w.revoke(visit_id)
    assert [r.revoked_at for r in w.reports.rows] == [NOW]
    assert await w.reports.get_live(ctx(), visit_id, NOW) is None
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "revoke_report"]


async def test_보낸_적이_없거나_이미_끊었으면_REPORT_NOT_FOUND_다():
    w = _World()
    with pytest.raises(ReportNotFoundError):
        await w.revoke(w.visits.seed(status="completed", started_at=kst(9, 23, 14)).id)
    visit_id = await w.sent()
    await w.revoke(visit_id)
    with pytest.raises(ReportNotFoundError):
        await w.revoke(visit_id)


async def test_기간이_지난_링크는_끊을_것이_없다():
    w = _World()
    visit_id = await w.sent(expires_at=NOW)   # 지금 끝난다
    with pytest.raises(ReportNotFoundError):
        await w.revoke(visit_id)
    assert [r.revoked_at for r in w.reports.rows] == [None]


async def test_없는_방문과_다른_매장의_방문은_끊을_수_없다():
    """R2"""
    w = _World()
    theirs = await w.sent(shop_id=2)
    for visit_id in (theirs, 999):
        with pytest.raises(VisitNotFoundError):
            await w.revoke(visit_id, shop_id=1)
    assert (w.journal, [r.revoked_at for r in w.reports.rows]) == ([], [None])
```

`backend/apps/visit/tests/app/use_cases/test_send_visit_report_interactor.py`:

```python
from dataclasses import replace
from datetime import timedelta

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
from visit.domain.errors import (
    ReportEmptyError,
    VisitInputError,
    VisitNoRecordYetError,
    VisitNotCompletedError,
    VisitNotFoundError,
)
from visit.domain.services.report_rules import hide
from visit.domain.services.report_token import read_token
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeReportSettingsRepository,
    FakeShopProfile,
    FakeVisits,
    Journal,
)

KEY = bytes(range(32))
NOW = kst(9, 24, 10)
SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)


class _World:
    def __init__(self) -> None:
        self.journal = Journal()
        self.now = NOW
        self.visits, self.settings = FakeVisits(self.journal), FakeReportSettingsRepository()
        self.records = FakeRecords(self.visits, self.journal)
        self.reports = FakeReportRepository(self.visits, self.journal)
        directory, library = FakeDirectory(self.journal), FakeLibrary()
        directory.family(1, pets=(101,))
        for media_id in (51, 52):
            library.add(media_id, attached=True)
        self.interactor = SendVisitReportInteractor(
            visits=self.visits, records=self.records, settings=self.settings, reports=self.reports,
            menus=FakeMenus(), directory=directory, library=library, shops=FakeShopProfile({1: SHOP}),
            now=lambda: self.now, link_key=KEY, web_base_url="https://r.example",
        )
        self.revoker = RevokeVisitReportInteractor(self.visits, self.reports, directory, now=lambda: self.now)

    def completed(self, status="completed", care_note="눈물 자국", hidden=(), **fields):
        """사진 둘(전 51, 후 52)이 있는 기록이 달린 방문."""
        found = self.visits.seed(status=status, starts_at=kst(9, 23, 14), started_at=kst(9, 23, 14), **fields)
        written = record(found.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
                         care_note=care_note)
        self.records.seed(replace(written, media=hide(written, hidden)))
        return found

    async def send(self, visit_id, hidden=(), shop_id=1):
        return await self.interactor.send_visit_report(
            SendVisitReportCommand(ctx=ctx(shop_id=shop_id), visit_id=visit_id, hidden_media_ids=tuple(hidden)))

    async def revoke(self, visit_id):
        await self.revoker.revoke_visit_report(RevokeVisitReportCommand(ctx=ctx(), visit_id=visit_id))

    def hidden(self, visit_id):
        return {m.media_id for m in self.records.rows[visit_id].media if m.hidden}

    def written(self):
        return [e[0] for e in self.journal if e[0] in ("create_report", "set_hidden")]


def _public_id(link):
    return read_token(link.url.removeprefix("https://r.example/r/"), KEY)


@pytest.mark.parametrize("link_days, expires_at", [
    (7, "2026-10-01T10:00:00+09:00"), (30, "2026-10-24T10:00:00+09:00"), (None, None),
])
async def test_처음_보내면_잠근_뒤_링크를_만들고_기간은_매장이_정한_대로다(link_days, expires_at):
    w = _World()
    w.settings.rows[1] = replace(DEFAULT_REPORT_SETTINGS, link_days=link_days)
    visit_id = w.completed().id

    sent = await w.send(visit_id, hidden=(52,))

    [row] = w.reports.rows
    assert (row.visit_id, row.created_by_member_id, row.created_at, len(row.public_id)) == (visit_id, 11, NOW, 16)
    assert (sent.link.status, _public_id(sent.link)) == ("live", row.public_id)
    assert sent.link.created_at.isoformat() == "2026-09-24T10:00:00+09:00"
    assert (sent.link.expires_at.isoformat() if sent.link.expires_at else None) == expires_at
    assert [(m.media_id, m.hidden) for m in sent.report.media] == [(52, True), (51, False)]
    assert (sent.report.cover.url, sent.report.settings.link_days) == ("d/51", link_days)
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "close_expired_reports", "create_report",
                                         "set_hidden"]


async def test_다시_보내면_같은_링크이고_뺀_사진만_바뀐다():
    w = _World()
    visit_id = w.completed().id
    first = await w.send(visit_id, hidden=(52,))
    w.settings.rows[1] = replace(DEFAULT_REPORT_SETTINGS, link_days=7)   # 기간은 만들 때 정해진다
    w.now = NOW + timedelta(days=1)

    again = await w.send(visit_id, hidden=(51,))

    assert again.link == first.link and len(w.reports.rows) == 1
    assert w.hidden(visit_id) == {51}   # 52 는 되살아났다
    assert [(m.media_id, m.hidden) for m in again.report.media] == [(52, False), (51, True)]
    assert await w.send(visit_id, hidden=(51,)) == again   # 같은 본문이면 결과가 같다


async def test_기간이_지난_뒤_보내면_옛_줄을_닫고_새_링크를_만든다():
    """R20·R4"""
    w = _World()
    w.settings.rows[1] = replace(DEFAULT_REPORT_SETTINGS, link_days=7)
    visit_id = w.completed().id
    first = await w.send(visit_id)
    w.now = NOW + timedelta(days=7)   # 끝나는 바로 그 시각

    second = await w.send(visit_id)

    old, new = w.reports.rows
    assert (old.revoked_at, new.revoked_at, new.created_at) == (w.now, None, w.now)
    assert _public_id(first.link) == old.public_id != new.public_id == _public_id(second.link)
    assert second.link.expires_at.isoformat() == "2026-10-08T10:00:00+09:00"


async def test_끊은_뒤_보내면_새_링크이고_뺀_사진은_끊어도_그대로다():
    """R4"""
    w = _World()
    visit_id = w.completed().id
    first = await w.send(visit_id, hidden=(52,))
    await w.revoke(visit_id)
    assert w.hidden(visit_id) == {52}

    second = await w.send(visit_id, hidden=(52,))

    assert [r.revoked_at for r in w.reports.rows] == [NOW, None]
    assert _public_id(first.link) != _public_id(second.link)


@pytest.mark.parametrize("status", ["reserved", "in_progress", "canceled", "no_show"])
async def test_완료하지_않은_방문은_VISIT_NOT_COMPLETED_다(status):
    w = _World()
    with pytest.raises(VisitNotCompletedError):
        await w.send(w.completed(status=status).id)
    assert w.written() == []


async def test_기록이_없는_방문은_VISIT_NO_RECORD_YET_이다():
    w = _World()
    with pytest.raises(VisitNoRecordYetError):
        await w.send(w.visits.seed(status="completed", started_at=kst(9, 23, 14)).id)
    assert w.written() == []


@pytest.mark.parametrize("care_note", [None, "", "  \n "])
async def test_전부_빼고_메모도_없으면_REPORT_EMPTY_이고_아무것도_바뀌지_않는다(care_note):
    w = _World()
    visit_id = w.completed(care_note=care_note, hidden=(52,)).id
    with pytest.raises(ReportEmptyError):
        await w.send(visit_id, hidden=(51, 52))
    assert (w.reports.rows, w.hidden(visit_id), w.written()) == ([], {52}, [])


async def test_메모가_있으면_사진을_전부_빼고도_처음_보낼_수_있다():
    w = _World()
    sent = await w.send(w.completed(care_note="눈물 자국").id, hidden=(51, 52))
    assert (sent.link.status, sent.report.cover) == ("live", None)


async def test_살아_있는_링크가_있으면_메모가_없어도_전부_뺄_수_있다():
    w = _World()
    visit_id = w.completed(care_note=None).id
    first = await w.send(visit_id)

    emptied = await w.send(visit_id, hidden=(51, 52))

    assert emptied.link == first.link and len(w.reports.rows) == 1
    assert (w.hidden(visit_id), emptied.report.cover) == ({51, 52}, None)


@pytest.mark.parametrize("hidden", [(99,), (52, 99), (52, 52)])
async def test_이_기록의_것이_아닌_미디어와_중복은_VALIDATION_ERROR_다(hidden):
    """R14"""
    w = _World()
    visit_id = w.completed().id
    with pytest.raises(VisitInputError):
        await w.send(visit_id, hidden=hidden)
    assert w.written() == []


async def test_없는_방문과_다른_매장의_방문에는_보낼_수_없다():
    """R2"""
    w = _World()
    theirs = w.completed(shop_id=2)
    for visit_id in (theirs.id, 999):
        with pytest.raises(VisitNotFoundError):
            await w.send(visit_id, shop_id=1)
    assert w.journal == []
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:

```diff
@@ -17,6 +17,7 @@ async def test_자기소개는_묶음의_경로와_권한을_적는다():
     for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위",
                   "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT",
                   "POST /visits/{visit_id}/record/media", "record:delete", "GET·PUT /report-settings",
-                  "GET /visits/{visit_id}/report"):
+                  "GET /visits/{visit_id}/report", "PUT /visits/{visit_id}/report",
+                  "DELETE /visits/{visit_id}/report", "REPORT_EMPTY"):
         assert words in result.introduction
     assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/domain/test_visit_record_rules.py`:

```diff
@@ -1,3 +1,4 @@
+from dataclasses import replace
 from decimal import Decimal
 
 import pytest
@@ -96,3 +97,11 @@ def test_덧붙이면_그_칸의_맨_뒤이고_그_칸은_순서를_지킨_채_0
         _m(3, phase="after", order=5), _m(1, phase="before", order=0), _m(2, phase="before", order=1),
         _m(9, "video", "before", 2))
     assert append_media([], 9, "photo", "after") == (_m(9, order=0),)
+
+
+def test_덧붙여도_알림장에서_뺀_표시는_남고_새_미디어는_보인다():
+    """R5 — 순서를 다시 매기는 칸이든 아니든 뺀 것은 뺀 채다."""
+    media = [replace(_m(1, phase="before", order=3), hidden=True), _m(2, phase="before", order=90),
+             replace(_m(3, phase="after", order=5), hidden=True)]
+    assert [(m.media_id, m.sort_order, m.hidden) for m in append_media(media, 9, "photo", "before")] == [
+        (3, 5, True), (1, 0, True), (2, 1, False), (9, 2, False)]
```

`backend/tests/integration/test_visit_report_locking.py`:

```python
"""알림장 보내기의 경합 — 실제 두 세션으로 확인한다(막힌 호출을 create_task 로 들고, 앞선 세션이 커밋한 뒤의 결과를 본다)."""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.tests.helpers.profiles import customer_profile, pet_profile
from hub.app.dtos.shop_profile import ShopProfile
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.tests.helpers.fakes import FakeStorage
from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeShopProfile
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
PROFILE = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
BLOCKED = 0.5


def _send(session):
    directory = CustomerDirectoryInteractor(CustomerPgRepository(session), PetPgRepository(session),
                                            FamilyBriefPgRepository(session), CustomerSearchPgAdapter(session))
    library = MediaLibraryInteractor(MediaPgRepository(session), FakeStorage(), now=lambda: kst(9, 24, 10))
    return SendVisitReportInteractor(
        visits=VisitPgRepository(session), records=VisitRecordPgRepository(session),
        settings=ReportSettingsPgRepository(session), reports=ReportPgRepository(session),
        menus=MenuPgRepository(session), directory=directory, library=library,
        shops=FakeShopProfile({1: PROFILE}), now=lambda: kst(9, 24, 10), link_key=bytes(range(32)),
        web_base_url="https://r.example",
    )


async def test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고_링크는_하나다(db_engine, db_session):
    """R8 — 고객 행 → 방문 행 잠금을 빼면 늦은 쪽도 '링크 없음'을 읽고 새 줄을 넣으려다 유일 색인에 걸린다."""
    customer = await CustomerPgRepository(db_session).create(SHOP, customer_profile())
    pet = await PetPgRepository(db_session).add(SHOP, customer.id, pet_profile())
    visit_id = await insert_visit(db_session, kst(9, 23, 14), "completed", customer_id=customer.id, pet_id=pet.id)
    await VisitRecordPgRepository(db_session).save(SHOP, record(visit_id, care_note="눈물 자국"))
    await db_session.commit()
    command = SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=())

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        early = await _send(first).send_visit_report(command)
        late = asyncio.create_task(_send(second).send_visit_report(command))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await first.commit()
        late_sent = await late
        await second.commit()

    assert early.link.status == "live" and late_sent.link == early.link
    rows = (await db_session.execute(
        text("SELECT revoked_at FROM visit_reports WHERE visit_id = :id"), {"id": visit_id})).all()
    assert rows == [(None,)]
```

`backend/tests/integration/test_visit_report_wiring.py`:

```diff
@@ -4,6 +4,7 @@ from datetime import datetime, timedelta
 from zoneinfo import ZoneInfo
 
 import pytest
+from sqlalchemy import text
 
 from tests.integration.support import (
     accept_invite,
@@ -48,6 +49,31 @@ async def _started_visit(wired, shop_id, headers) -> int:
     return visit_id
 
 
+async def _complete(wired, shop_id, headers, visit_id) -> None:
+    done = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
+                                json={"visit_ids": [visit_id], "action": "complete"})
+    assert done.status_code == 200, done.text
+
+
+async def _completed_visit(wired, shop_id, headers, photos=0):
+    """기록(케어 메모와 후 사진 photos 장)을 남기고 완료한 방문. (방문 ID, 사진 ID 목록)을 준다."""
+    visit_id = await _started_visit(wired, shop_id, headers)
+    media = [await ready_photo(wired, shop_id, headers) for _ in range(photos)]
+    written = await wired.api.put(
+        f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
+        json={"care_note": "눈물 자국을 닦았어요",
+              "media": [{"media_id": m, "phase": "after", "sort_order": i} for i, m in enumerate(media)]})
+    assert written.status_code == 200, written.text
+    await _complete(wired, shop_id, headers, visit_id)
+    return visit_id, media
+
+
+async def _staff(wired, shop_id, owner):
+    staff = await wired.login("직원")
+    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
+    return bearer(staff["access_token"])
+
+
 async def test_직원이_알림장을_미리_보고_설정과_링크가_그대로_비친다(wired, media_storage):
     from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
     from visit.domain.services.report_token import read_token
@@ -88,21 +114,21 @@ async def test_직원이_알림장을_미리_보고_설정과_링크가_그대
         json={"link_days": 7, "show_menus": False, "show_shop_info": False, "show_weight": True,
               "show_amount": False})
     assert changed.status_code == 200, changed.text
-    await wired.execute(
-        "UPDATE visit_record_media SET hidden_from_report = true WHERE media_id = :id", id=photo)
-    await wired.execute(
-        "INSERT INTO visit_reports (visit_id, public_id, expires_at, created_by_member_id, created_at)"
-        " VALUES (:visit_id, :public_id, now() + interval '7 days', 1, now())",
-        visit_id=visit_id, public_id=bytes(range(16)))
+    await _complete(wired, shop_id, o, visit_id)
+    sent = await wired.api.put(path, headers=o, json={"hidden_media_ids": [photo]})
+    assert sent.status_code == 200, sent.text
 
     body = (await wired.api.get(path, headers=o)).json()
+    assert body == sent.json()
     assert (body["report"]["menus"], body["report"]["shop"], body["report"]["weight_kg"]) == (None, None, 3.4)
     assert ([m["hidden"] for m in body["report"]["media"]], body["report"]["cover"]) == ([True], None)
     assert body["settings"]["show_weight"] is True
     assert body["link"]["status"] == "live"
     token = re.fullmatch(re.escape(REPORT_WEB_BASE_URL) + r"/r/([A-Za-z0-9_-]{43})", body["link"]["url"]).group(1)
-    assert read_token(token, REPORT_LINK_KEY) == bytes(range(16))
+    assert len(read_token(token, REPORT_LINK_KEY)) == 16
     assert body["link"]["expires_at"].endswith("+09:00") and body["link"]["created_at"].endswith("+09:00")
+    sent_at, expires_at = (datetime.fromisoformat(body["link"][k]) for k in ("created_at", "expires_at"))
+    assert expires_at - sent_at == timedelta(days=7)
 
 
 async def test_다른_매장의_방문은_미리_볼_수_없고_기록이_없으면_409_다(wired):
@@ -122,3 +148,96 @@ async def test_다른_매장의_방문은_미리_볼_수_없고_기록이_없으
     assert error_of(await wired.api.get(f"/v1/shops/{a_shop}/visits/{a_visit}/report", headers=a)) == (
         409, "VISIT_NO_RECORD_YET")
     assert (await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_visit}/report", headers=b)).status_code == 200
+
+
+async def test_사장과_직원이_보내면_같은_링크이고_끊은_뒤_다시_보내면_새_링크다(wired):
+    """R4 — 끊은 링크는 새 링크를 만들어도 되살아나지 않는다(줄이 다르다)."""
+    shop_id, owner, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    staff = await _staff(wired, shop_id, owner)
+    visit_id, _ = await _completed_visit(wired, shop_id, o)
+    path = f"/v1/shops/{shop_id}/visits/{visit_id}/report"
+
+    first = await wired.api.put(path, headers=o, json={"hidden_media_ids": []})
+    assert (first.status_code, first.json()["link"]["status"]) == (200, "live")
+    again = await wired.api.put(path, headers=staff, json={"hidden_media_ids": []})
+    assert (again.status_code, again.json()["link"]) == (200, first.json()["link"])
+
+    assert (await wired.api.delete(path, headers=staff)).status_code == 204
+    assert (await wired.api.get(path, headers=o)).json()["link"] == NO_LINK
+    assert error_of(await wired.api.delete(path, headers=o)) == (404, "REPORT_NOT_FOUND")
+
+    second = await wired.api.put(path, headers=staff, json={"hidden_media_ids": []})
+    assert (second.status_code, second.json()["link"]["status"]) == (200, "live")
+    assert second.json()["link"]["url"] != first.json()["link"]["url"]
+    async with wired.engine.connect() as conn:
+        rows = (await conn.execute(text(
+            "SELECT revoked_at IS NULL, created_by_member_id FROM visit_reports ORDER BY id"))).all()
+    assert [live for live, _ in rows] == [False, True]
+    assert rows[0][1] != rows[1][1]   # 사장이 만든 줄, 직원이 만든 줄
+
+
+async def test_완료_전이거나_보낼_것이_없으면_거절하고_링크를_만들지_않는다(wired):
+    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    visit_id = await _started_visit(wired, shop_id, o)
+    path = f"/v1/shops/{shop_id}/visits/{visit_id}/report"
+    assert (await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=o,
+                                json={"weight_kg": 3.4})).status_code == 200   # 메모도 사진도 없는 기록
+
+    assert error_of(await wired.api.put(path, headers=o, json={"hidden_media_ids": []})) == (
+        409, "VISIT_NOT_COMPLETED")
+    await _complete(wired, shop_id, o, visit_id)
+    assert error_of(await wired.api.put(path, headers=o, json={"hidden_media_ids": []})) == (422, "REPORT_EMPTY")
+    assert error_of(await wired.api.put(path, headers=o, json={"hidden_media_ids": [999]})) == (
+        422, "VALIDATION_ERROR")
+    async with wired.engine.connect() as conn:
+        assert (await conn.execute(text("SELECT count(*) FROM visit_reports"))).scalar_one() == 0
+
+
+async def test_다른_매장의_방문에는_보내지도_끊지도_못한다(wired):
+    """R2"""
+    operator = await make_operator(wired)
+    a_shop, _, a = await _shop(wired, operator, "A 매장", "A사장")
+    b_shop, _, b = await _shop(wired, operator, "B 매장", "B사장")
+    b_visit, _ = await _completed_visit(wired, b_shop, b)
+    sent = await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_visit}/report", headers=b,
+                               json={"hidden_media_ids": []})
+    assert sent.status_code == 200, sent.text
+
+    through_mine = f"/v1/shops/{a_shop}/visits/{b_visit}/report"
+    assert error_of(await wired.api.put(through_mine, headers=a, json={"hidden_media_ids": []})) == (
+        404, "VISIT_NOT_FOUND")
+    assert error_of(await wired.api.delete(through_mine, headers=a)) == (404, "VISIT_NOT_FOUND")
+    theirs = f"/v1/shops/{b_shop}/visits/{b_visit}/report"
+    assert error_of(await wired.api.put(theirs, headers=a, json={"hidden_media_ids": []})) == (403, "NOT_A_MEMBER")
+    assert error_of(await wired.api.delete(theirs, headers=a)) == (403, "NOT_A_MEMBER")
+
+    assert (await wired.api.get(theirs, headers=b)).json()["link"] == sent.json()["link"]   # 그대로 살아 있다
+
+
+async def test_알림장에서_뺀_사진은_기록을_고치고_사진을_덧붙여도_빠져_있다(wired, media_storage):
+    """R5"""
+    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    visit_id, [first, removed, last] = await _completed_visit(wired, shop_id, o, photos=3)
+    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
+    sent = await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": [removed]})
+    assert sent.status_code == 200, sent.text
+
+    async def hidden():
+        media = (await wired.api.get(f"{visit}/report", headers=o)).json()["report"]["media"]
+        return {m["media_id"]: m["hidden"] for m in media}
+
+    assert await hidden() == {first: False, removed: True, last: False}
+
+    rewritten = await wired.api.put(
+        f"{visit}/record", headers=o,
+        json={"version": 1, "care_note": "메모만 고쳤어요",
+              "media": [{"media_id": m, "phase": "after", "sort_order": i}
+                        for i, m in enumerate([last, removed, first])]})   # 자리도 바꿨다
+    assert rewritten.status_code == 200, rewritten.text
+    assert await hidden() == {first: False, removed: True, last: False}
+
+    added = await ready_photo(wired, shop_id, o)
+    appended = await wired.api.post(f"{visit}/record/media", headers=o, json={"media_id": added, "phase": "after"})
+    assert appended.status_code == 200, appended.text
+    assert await hidden() == {first: False, removed: True, last: False, added: False}
+    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"] == sent.json()["link"]
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

명령은 모두 `infra/` 에서 `docker compose run --rm backend pytest <경로들> -q -p no:cacheprovider`.

작업 테스트 아홉 파일: `5 errors in 0.36s` — 수집 오류. 예:
`ModuleNotFoundError: No module named 'visit.app.dtos.send_visit_report_dto'`,
`ModuleNotFoundError: No module named 'visit.adapter.inbound.api.v1.revoke_visit_report_router'`.

수집되는 파일만 따로(도메인·기록 인터랙터 둘·배선): `8 failed, 33 passed in 2.90s`.
- `test_덧붙여도_알림장에서_뺀_표시는_남고_새_미디어는_보인다`
- `test_알림장에서_뺀_사진은_기록을_다시_저장해도_빠져_있다`
- `test_알림장에서_뺀_사진은_덧붙인_뒤에도_빠져_있고_새_사진은_보인다[before]`
- 배선 다섯(`assert 405 == 200` — 경로에 PUT 이 없다)

경합 테스트와 새 인터랙터·라우터 테스트는 수집 오류라 따로 실패하는 모습을 보지 못했다. 변이로 실패를 확인했다(4절).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/adapter/inbound/api/schemas/send_visit_report_schema.py`:

```python
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId
from visit.domain.services.report_rules import MAX_HIDDEN


class SendVisitReportRequestSchema(BaseModel):
    """뺄 사진·영상 전부를 보낸다(없으면 빈 배열). 응답은 미리보기와 같은 모양(VisitReportSchema)이다.

    개수 상한은 요청 하나가 큰 일을 시키지 못하게 하는 입력 경계다. 이 기록의 것이 아닌 ID 와 중복은
    도메인이 거른다(422 VALIDATION_ERROR).
    """

    hidden_media_ids: Annotated[list[EntityId], Field(max_length=MAX_HIDDEN)]
```

`backend/apps/visit/adapter/inbound/api/v1/revoke_visit_report_router.py`:

```python
from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
from visit.dependencies.revoke_visit_report_provider import get_revoke_visit_report_use_case

revoke_visit_report_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 끊기는 보내기와 같은 권한이다(record:write, 사장·직원) — 잘못 보낸 링크를 보낸 사람이 바로 끊을 수 있게.
@revoke_visit_report_router.delete("/{shop_id}/visits/{visit_id}/report", status_code=204)
async def revoke_visit_report(
    visit_id: VisitId,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: RevokeVisitReportUseCase = Depends(get_revoke_visit_report_use_case),
) -> Response:
    await use_case.revoke_visit_report(RevokeVisitReportCommand(ctx=ctx, visit_id=visit_id))
    return Response(status_code=204)
```

`backend/apps/visit/adapter/inbound/api/v1/send_visit_report_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_visit_report_schema import VisitReportSchema
from visit.adapter.inbound.api.schemas.send_visit_report_schema import SendVisitReportRequestSchema
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.ports.input.send_visit_report_use_case import SendVisitReportUseCase
from visit.dependencies.send_visit_report_provider import get_send_visit_report_use_case

send_visit_report_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@send_visit_report_router.put("/{shop_id}/visits/{visit_id}/report", response_model=VisitReportSchema)
async def send_visit_report(
    visit_id: VisitId,
    body: SendVisitReportRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: SendVisitReportUseCase = Depends(get_send_visit_report_use_case),
) -> VisitReportSchema:
    view = await use_case.send_visit_report(
        SendVisitReportCommand(ctx=ctx, visit_id=visit_id, hidden_media_ids=tuple(body.hidden_media_ids))
    )
    return VisitReportSchema.of(view)
```

`backend/apps/visit/app/dtos/revoke_visit_report_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class RevokeVisitReportCommand:
    ctx: ShopContext
    visit_id: int
```

`backend/apps/visit/app/dtos/send_visit_report_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class SendVisitReportCommand:
    """알림장 보내기. hidden_media_ids 는 뺄 사진·영상 전부다 — 여기에 없는 것은 앞서 뺐더라도 다시 보인다."""

    ctx: ShopContext
    visit_id: int
    hidden_media_ids: tuple[int, ...]
```

`backend/apps/visit/app/ports/input/revoke_visit_report_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand


class RevokeVisitReportUseCase(ABC):
    @abstractmethod
    async def revoke_visit_report(self, command: RevokeVisitReportCommand) -> None: ...
```

`backend/apps/visit/app/ports/input/send_visit_report_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand


class SendVisitReportUseCase(ABC):
    @abstractmethod
    async def send_visit_report(self, command: SendVisitReportCommand) -> VisitReportPreview: ...
```

`backend/apps/visit/app/use_cases/put_visit_record_interactor.py`:

```diff
@@ -14,6 +14,7 @@ from visit.app.services.record_reader import describe_record
 from visit.app.services.visit_locking import lock_visits
 from visit.domain.entities.visit_record import RecordMedia, VisitRecord
 from visit.domain.errors import MenuNotAvailableError, RecordSalesForbiddenError
+from visit.domain.services.report_rules import carry_hidden
 from visit.domain.services.visit_record_rules import (
     check_input,
     check_media_limits,
@@ -28,6 +29,8 @@ class PutVisitRecordInteractor(PutVisitRecordUseCase):
 
     새로 든 미디어는 가져가고(claim), 빠진 미디어는 놓는다(release) — 놓인 미디어는 정리 스크립트가 지운다.
     둘 다 조건부 UPDATE 라 잠금 안에서 불러도 된다. 하나라도 안 되면 요청 전체가 되돌려진다.
+    저장은 미디어 줄을 지우고 다시 넣으므로, 알림장에서 뺀 표시를 미디어 ID 로 이어 붙인다 — 빠뜨리면 뺀 사진이
+    보호자에게 보인다.
     """
 
     def __init__(
@@ -64,8 +67,9 @@ class PutVisitRecordInteractor(PutVisitRecordUseCase):
             visit_id=visit.id, weight_kg=wanted.weight_kg, care_note=wanted.care_note,
             internal_note=wanted.internal_note, payment_method=wanted.payment_method,
             total_amount=wanted.total_amount, items=wanted.items,
-            media=tuple(RecordMedia(media_id=p.media_id, kind=kinds[p.media_id], phase=p.phase,
-                                    sort_order=p.sort_order) for p in wanted.media),
+            media=carry_hidden(current.media if current else (), tuple(
+                RecordMedia(media_id=p.media_id, kind=kinds[p.media_id], phase=p.phase, sort_order=p.sort_order)
+                for p in wanted.media)),
             version=next_version(current),
             created_by_member_id=current.created_by_member_id if current else ctx.member_id,
             updated_by_member_id=ctx.member_id,
```

`backend/apps/visit/app/use_cases/revoke_visit_report_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.services.visit_locking import lock_visits
from visit.domain.errors import ReportNotFoundError


class RevokeVisitReportInteractor(RevokeVisitReportUseCase):
    """알림장 링크 끊기 — 살아 있는 링크만 끊는다. 뺀 사진 표시는 그대로 둔다(다시 보낼 때 앱이 그대로 보여 준다).
    잠금은 보내기와 같다(고객 행 → 방문 행)."""

    def __init__(
        self, visits: VisitLookupRepository, reports: ReportRepository, directory: CustomerDirectoryPort,
        now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._reports = reports
        self._directory = directory
        self._now = now

    async def revoke_visit_report(self, command: RevokeVisitReportCommand) -> None:
        ctx = command.ctx
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        if not await self._reports.revoke(ctx, visit.id, self._now()):
            raise ReportNotFoundError("보낸 알림장이 없습니다.")
```

`backend/apps/visit/app/use_cases/send_visit_report_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.ports.input.send_visit_report_use_case import SendVisitReportUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.report_reader import describe_link, describe_report
from visit.app.services.visit_locking import lock_visits
from visit.domain.services.report_rules import check_not_empty, check_sendable, expires_at_for
from visit.domain.services.report_token import new_public_id


class SendVisitReportInteractor(SendVisitReportUseCase):
    """알림장 보내기 — 뺀 사진을 저장하고, 살아 있는 링크가 없으면 만든다(설계 6.1).

    처음 보내기·다시 공유·보낸 뒤 사진 빼기를 함께 맡는다. 같은 본문으로 다시 불러도 같은 링크다.
    고객 행 → 방문 행을 잠근 뒤에 링크를 읽으므로 동시에 두 번 보내도 링크는 하나다. 기간이 지난 줄은
    먼저 닫아야 새 줄을 만들 수 있다(끊지 않은 줄은 방문에 하나). 검사는 링크·뺀 표시를 쓰기 전에 끝낸다.
    """

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
        reports: ReportRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        library: MediaLibraryPort, shops: ShopProfilePort, now: Callable[[], datetime], link_key: bytes,
        web_base_url: str,
    ) -> None:
        self._visits = visits
        self._records = records
        self._settings = settings
        self._reports = reports
        self._menus = menus
        self._directory = directory
        self._library = library
        self._shops = shops
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def send_visit_report(self, command: SendVisitReportCommand) -> VisitReportPreview:
        ctx, hidden_ids, now = command.ctx, command.hidden_media_ids, self._now()
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        record = await self._records.get(ctx, visit.id)
        check_sendable(visit, record, hidden_ids)
        settings = await self._settings.get(ctx)

        await self._reports.close_expired(ctx, visit.id, now)
        live = await self._reports.get_live(ctx, visit.id, now)
        if live is None:
            check_not_empty(record, hidden_ids)
            live = await self._reports.create(
                ctx, visit.id, new_public_id(), expires_at_for(now, settings.link_days), now)
        await self._records.set_hidden(ctx, visit.id, hidden_ids)

        report = await describe_report(
            ctx, visit, await self._records.get(ctx, visit.id), settings,
            await self._shops.public_profile(ctx.shop_id), self._menus, self._directory, self._library,
            include_hidden=True,
        )
        link = describe_link(live, self._link_key, self._web_base_url)
        return VisitReportPreview(report=report, link=link.in_zone(ZoneInfo(ctx.timezone)))
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -48,6 +48,11 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "항목 show_menus·show_shop_info·show_weight·show_amount — PUT 은 다섯 칸 전체 교체). "
                 "GET /visits/{visit_id}/report 는 알림장 미리보기입니다(보호자가 볼 내용 report — 끈 항목은 null, "
                 "사진영상마다 뺀 것인지 hidden — 과 링크 상태 link, 설정 settings. 기록이 없으면 409). "
+                "PUT /visits/{visit_id}/report {hidden_media_ids} 는 알림장 보내기입니다(완료 방문만, record:write). "
+                "뺄 사진영상 전부를 받아 저장하고 살아 있는 링크가 없으면 만들며, 다시 불러도 같은 링크입니다"
+                "(응답은 미리보기와 같은 모양, 보낼 것이 없으면 422 REPORT_EMPTY). "
+                "DELETE /visits/{visit_id}/report 는 링크 끊기입니다(record:write, 없으면 404 REPORT_NOT_FOUND). "
+                "기록을 고치거나 사진을 덧붙여도 뺀 사진은 빠져 있습니다. "
                 "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴·알림장 설정 수정은 shop:update(사장)가 필요합니다. "
                 "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                 "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
```

`backend/apps/visit/dependencies/revoke_visit_report_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_report_repository, build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_revoke_visit_report_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> RevokeVisitReportUseCase:
    return RevokeVisitReportInteractor(
        visits=build_visit_repository(db), reports=build_report_repository(db), directory=directory, now=utc_now,
    )
```

`backend/apps/visit/dependencies/send_visit_report_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.send_visit_report_use_case import SendVisitReportUseCase
from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library, get_shop_profile
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_record_repository,
    build_report_repository,
    build_report_settings_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_send_visit_report_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> SendVisitReportUseCase:
    return SendVisitReportInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db),
        settings=build_report_settings_repository(db), reports=build_report_repository(db),
        menus=build_menu_repository(db), directory=directory, library=library, shops=shops, now=utc_now,
        link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
    )
```

`backend/apps/visit/domain/services/visit_record_rules.py`:

```diff
@@ -6,6 +6,7 @@ from __future__ import annotations
 
 from collections import Counter
 from collections.abc import Iterable
+from dataclasses import replace
 
 from visit.domain.entities.visit import Visit
 from visit.domain.entities.visit_record import AFTER, BEFORE, RecordMedia, VisitRecord
@@ -55,10 +56,10 @@ def next_version(current: VisitRecord | None) -> int:
 
 def append_media(media: Iterable[RecordMedia], media_id: int, kind: str, phase: str) -> tuple[RecordMedia, ...]:
     """그 칸(전/후)의 맨 뒤에 붙인다. 그 칸은 순서를 지킨 채 0부터 다시 매긴다 — 빼고 붙이기를 거듭해도
-    순서 값이 상한(99)에 닿지 않는다."""
+    순서 값이 상한(99)에 닿지 않는다. 있던 미디어는 순서만 바뀐다(알림장에서 뺀 표시가 남는다)."""
     media = list(media)
     same = sorted((m for m in media if m.phase == phase), key=lambda m: m.sort_order)
-    renumbered = [RecordMedia(m.media_id, m.kind, m.phase, order) for order, m in enumerate(same)]
+    renumbered = [replace(m, sort_order=order) for order, m in enumerate(same)]
     others = [m for m in media if m.phase != phase]
     return tuple(others + renumbered + [RecordMedia(media_id, kind, phase, len(same))])
```

`backend/main.py`:

```diff
@@ -87,6 +87,8 @@ from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_dr
 from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
 from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
 from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
+from visit.adapter.inbound.api.v1.revoke_visit_report_router import revoke_visit_report_router
+from visit.adapter.inbound.api.v1.send_visit_report_router import send_visit_report_router
 from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
 from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_report_settings_router import update_report_settings_router
@@ -170,6 +172,8 @@ app.include_router(put_visit_record_router)
 app.include_router(append_record_media_router)
 app.include_router(delete_visit_record_router)
 app.include_router(get_visit_report_router)
+app.include_router(send_visit_report_router)
+app.include_router(revoke_visit_report_router)
 # media
 app.include_router(media_myself_router)
 app.include_router(issue_upload_router)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 테스트(기존 파일 포함 열세 파일) | 125 passed |
| 단위 전체 | 1207 passed, 359 deselected (시작 1135 → +72) |
| 통합 전체 | 359 passed, 1207 deselected (시작 354 → +5) |
| 구조 계약 | 6 kept, 0 broken |

- 새 통합 5: 배선 넷, 경합 하나.
- `docker compose run --rm --no-deps auth python scripts/print_routes.py` 를 돌렸다. `backend PUT …/visits/{visit_id}/report send_visit_report`, `backend DELETE …/visits/{visit_id}/report revoke_visit_report` 가 나온다.
- `tests/test_hub_port_binding.py` 는 맨 뒤에 두고 돌렸다. 통과한다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `SendVisitReportInteractor` 의 `lock_visits` 를 `visit = await self._visits.get(ctx, …)` 로 → 경합 `test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고_링크는_하나다` — 늦은 쪽의 `await late` 에서 `IntegrityError`(`uq_visit_reports_live` 위반). 단위 `test_처음_보내면_잠근_뒤_링크를_만들고_기간은_매장이_정한_대로다` 셋(journal 순서)
- `close_expired` 호출 제거 → `test_기간이_지난_뒤_보내면_옛_줄을_닫고_새_링크를_만든다`(스텁의 "끊지 않은 줄이 있다"), `test_처음_보내면_…` 셋(journal)
- `set_hidden` 을 `close_expired` 앞으로(검사보다 쓰기가 먼저) → `test_전부_빼고_메모도_없으면_REPORT_EMPTY_이고_아무것도_바뀌지_않는다[None]`·`[]`·`[  \n ]`, `test_처음_보내면_…` 셋
- `PutVisitRecordInteractor` 의 `carry_hidden` 제거 → 단위 `test_알림장에서_뺀_사진은_기록을_다시_저장해도_빠져_있다`, 배선 `test_알림장에서_뺀_사진은_기록을_고치고_사진을_덧붙여도_빠져_있다`
- `if live is None:` → `if True:` → `test_다시_보내면_같은_링크이고_뺀_사진만_바뀐다`, `test_살아_있는_링크가_있으면_메모가_없어도_전부_뺄_수_있다`, 배선 `test_사장과_직원이_보내면_같은_링크이고_끊은_뒤_다시_보내면_새_링크다`, 경합 테스트
- DELETE 라우터의 가드를 `get_shop_context` 로 → `test_revoke_visit_report_router.py::test_기록_권한이_없으면_끊지_못한다`
- PUT 라우터의 가드를 `get_shop_context` 로 → `test_send_visit_report_router.py::test_기록_권한이_없으면_보내지_못한다`
- `append_media` 를 예전대로(`RecordMedia(…)` 로 다시 만든다) → 도메인 `test_덧붙여도_알림장에서_뺀_표시는_남고_새_미디어는_보인다`, 인터랙터 `test_알림장에서_뺀_사진은_덧붙인_뒤에도_…[before]`, 배선 R5
- `set_hidden` 호출 제거 → 단위 일곱(`test_다시_보내면_…`, `test_끊은_뒤_보내면_…` 등), 배선 둘
- `RevokeVisitReportInteractor` 의 `lock_visits` 를 `get` 으로 → `test_잠근_뒤_살아_있는_링크를_끊는다`(journal 순서)
- 끊기가 `revoke` 의 결과를 보지 않는다 → `test_보낸_적이_없거나_이미_끊었으면_REPORT_NOT_FOUND_다`, `test_기간이_지난_링크는_끊을_것이_없다`, 배선 하나
- 스키마의 `max_length` 제거 → 422 테스트의 34개·5000개 본문
- 스키마의 `EntityId` → `int` → 422 테스트 여섯 — `["52"]`·`[52.0]`·`[true]`·`[0]`·`[-1]`·`[2**63]`
- 스키마 칸에 기본값 `= []` → 422 테스트의 `{}`
- `in_zone` 을 부르지 않는다 → 단위 넷, 배선 셋
- 기간을 늘 30일로 → `test_처음_보내면_…[7-…]`·`[None-None]`, `test_기간이_지난_뒤_…`, 배선 첫 테스트
- `main.py` 에 라우터 둘을 등록하지 않는다 → 배선 다섯
- `include_hidden=False` → 단위 넷, 배선 첫 테스트
- `check_sendable` 제거 → 단위 여덟(상태 넷, 기록 없음, 입력 셋), 배선 하나
- 뺀 표시를 쓴 뒤 기록을 다시 읽지 않는다 → 단위 여섯, 배선 첫 테스트
- `check_not_empty` 제거 → `test_전부_빼고_메모도_없으면_…` 셋, 배선 하나
- `new_public_id()` → `bytes(16)` → `test_기간이_지난_뒤_…`, `test_끊은_뒤_보내면_…`, 배선 하나

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 알림장 보내기와 끊기 — 방문당 살아 있는 링크 하나, 기록을 저장해도 뺀 사진은 빠져 있다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 알림장을 보낸 방문은 되돌리거나 기록을 지울 수 없다 — 익명화는 링크를 끊고, 상세·목록·피드에 보냄 표시

**Files:**
- Modify: `backend/apps/hub/app/ports/visit_ledger_port.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/list_day_visits_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/list_visit_feed_schema.py`
- Modify: `backend/apps/visit/app/dtos/get_visit_dto.py`
- Modify: `backend/apps/visit/app/dtos/list_day_visits_dto.py`
- Modify: `backend/apps/visit/app/dtos/list_visit_feed_dto.py`
- Modify: `backend/apps/visit/app/use_cases/delete_visit_record_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/get_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/list_day_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/list_visit_feed_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/transition_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_ledger_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Modify: `backend/apps/visit/dependencies/delete_visit_record_provider.py`
- Modify: `backend/apps/visit/dependencies/get_visit_provider.py`
- Modify: `backend/apps/visit/dependencies/list_day_visits_provider.py`
- Modify: `backend/apps/visit/dependencies/list_visit_feed_provider.py`
- Modify: `backend/apps/visit/dependencies/transition_visits_provider.py`
- Modify: `backend/apps/visit/dependencies/visit_ledger_provider.py`
- Modify: `backend/apps/visit/tests/adapter/test_get_visit_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_list_day_visits_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_list_visit_feed_router.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_delete_visit_record_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_list_visit_feed_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_ledger_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/tests/integration/test_customer_locking.py`
- Modify: `backend/tests/integration/test_visit_locking.py`
- Modify: `backend/tests/integration/test_visit_report_locking.py`
- Modify: `backend/tests/integration/test_visit_report_wiring.py`

**Interfaces:**
- Consumes: 작업 1 의 `CompletedState.revert`·`Visit.has_live_report`·`VisitReportSentError`; 작업 2 의 `ReportRepository.get_live`·`live_visit_ids`·`revoke_for_customer`; 작업 5 의 `describe_link`·`ReportLinkView.in_zone`·`ReportLinkSchema`; 작업 6 의 보내기·끊기 인터랙터(경합 테스트).
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

응답에 더한 칸

```python
# GET /v1/shops/{shop_id}/visits/{visit_id}
"report": {"status": "none" | "live", "url": str | None, "expires_at": datetime | None,
           "first_viewed_at": datetime | None, "created_at": datetime | None}     # 늘 있다(null 이 아니다). 시각은 매장 시간대
# GET /v1/shops/{shop_id}/visits?date=      — items[] 마다
"report_sent": bool
# GET /v1/shops/{shop_id}/visits/feed       — items[] 마다
"report_sent": bool
```

오류가 나는 자리

```
POST   /v1/shops/{shop_id}/visits/transitions   action=revert   → 409 VISIT_REPORT_SENT   (도메인 CompletedState.revert 가 던진다)
DELETE /v1/shops/{shop_id}/visits/{visit_id}/record             → 409 VISIT_REPORT_SENT   (인터랙터가 던진다)
```
문구는 둘 다 "알림장을 보낸 방문입니다. 링크를 먼저 끊어 주세요."

DTO·스키마

```python
# visit/app/dtos/get_visit_dto.py
VisitDetailView(visit, group, previous_visit, no_show_count, record, cover, report: ReportLinkView)
# visit/app/dtos/list_day_visits_dto.py
DayVisitItemView(visit, group_key, overlapping, unresolved, has_record, cover, report_sent: bool)
# visit/app/dtos/list_visit_feed_dto.py
FeedItemView(visit_id, customer, pet, completed_at, cover, menus, care_note, media_count, report_sent: bool)
# 스키마 — 같은 이름의 칸. VisitDetailSchema.report: ReportLinkSchema(T5 의 것)
```

인터랙터의 생성자(타입을 적은 것이 더한 인자. 순서 그대로)

```python
TransitionVisitsInteractor(visits, history, menus, reports: ReportRepository, directory, now)
DeleteVisitRecordInteractor(visits, records, reports: ReportRepository, directory, library, now: Callable[[], datetime])
VisitLedgerInteractor(ledger, records, reports: ReportRepository, now)
GetVisitInteractor(visits, history, ledger, menus, directory, records, library,
                   reports: ReportRepository, now: Callable[[], datetime], link_key: bytes, web_base_url: str)
ListDayVisitsInteractor(board, menus, schedule, directory, records, library, reports: ReportRepository, now)
ListVisitFeedInteractor(feed, records, menus, reports: ReportRepository, directory, library,
                        now: Callable[[], datetime])
```
프로바이더 여섯의 이름과 인자는 그대로다(안에서 `build_report_repository(db)` 를 더 넣는다).

스텁

```python
FakeReportRepository.reads: list[str]     # "get_live"·"live_visit_ids" 가 부른 순서대로 남는다. journal 에는 여전히 쓰기만 남는다
```

허브 포트 — `VisitLedgerPort.clear_customer_memos(ctx, customer_id) -> None` 시그니처 그대로. 독스트링: 메모를 비우고 그 방문들의 알림장 링크를 끊는다, 부르는 쪽의 트랜잭션 안에서 한다.

뒤 작업이 알아 둘 동작
- **되돌리기는 행동과 상관없이 링크를 읽는다**(6절 2번). 전이 한 번에 질의 하나가 늘었다. `has_live_report` 를 보는 것은 `CompletedState.revert` 뿐이라 다른 행동의 결과는 바뀌지 않는다.
- **전이 인터랙터의 순서**: `get_many` → `lock_visits` → 반려동물 재확인 → `now` → `live_visit_ids` → `transition`(전부 판정) → `apply_changes`. 방문 둘을 함께 되돌리는데 하나에 링크가 있으면 `apply_changes` 를 부르지 않는다.
- **기록 삭제의 순서**: `lock_visits` → `records.get`(없으면 `RECORD_NOT_FOUND`) → `get_live`(있으면 `VISIT_REPORT_SENT`) → `release` → `delete`. 기록이 없는 방문은 링크가 있어도 404 가 먼저다(기록 없이는 보낼 수 없으니 실제로는 겹치지 않는다).
- **익명화는 기간이 지난 줄도 끊는다**(T2 의 `revoke_for_customer` 그대로). `revoked_at` 은 익명화한 시각이다. 다른 매장의 같은 번호 고객 것은 건드리지 않는다.
- **익명화한 고객의 방문에는 다시 보낼 수 없다.** 보내기의 `lock_family` 가 익명화한 고객을 거절해 404 `CUSTOMER_NOT_FOUND` 다(일회용 배선 테스트로 확인, 커밋에는 없다 — 7절 3번). 같은 이유로 그 방문의 되돌리기·기록 삭제·끊기도 404 일 것이다(이 셋은 돌려 보지 못함).
- 상세의 `report` 는 미리보기(`GET …/report`)의 `link` 와 글자까지 같다(배선 테스트가 보내기 응답의 `link` 와 비교한다).
- 달력 응답은 바꾸지 않았다.
- 자기소개에 더한 말: `VISIT_REPORT_SENT`, `report`, `report_sent`, 고객 삭제가 링크를 끊는다.

설계 6.2·7.4, R9·R19. 되돌리기와 기록 삭제는 링크를 **잠근 뒤에** 읽는다. 하루 목록·피드는 방문이 여럿이어도 링크를 한 번에 읽는다. 기존 인터랙터 여섯의 생성자 인자가 늘어난다 — 프로바이더와 테스트의 조립 도우미를 함께 고친다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_get_visit_router.py`:

```diff
@@ -3,6 +3,7 @@ from zoneinfo import ZoneInfo
 
 from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
 from visit.app.dtos.get_visit_dto import PreviousVisitView, VisitDetailView
+from visit.app.dtos.report_view_dto import ReportLinkView
 from visit.dependencies.get_visit_provider import get_get_visit_use_case
 from visit.domain.errors import VisitNotFoundError
 from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
@@ -13,6 +14,10 @@ DETAIL = VisitDetailView(
     previous_visit=PreviousVisitView(visit_id=7, starts_at=datetime(2026, 9, 2, 14, tzinfo=ZoneInfo("Asia/Seoul")),
                                      cover="t/70"),
     no_show_count=1, record=None, cover=None,
+    report=ReportLinkView(
+        status="live", url="https://r.example/r/abc",
+        expires_at=datetime(2026, 10, 9, 18, tzinfo=ZoneInfo("Asia/Seoul")), first_viewed_at=None,
+        created_at=datetime(2026, 9, 9, 18, tzinfo=ZoneInfo("Asia/Seoul"))),
 )
 
 
@@ -24,6 +29,9 @@ async def test_직원도_방문_상세를_본다():
     assert (body["visit"]["visit_id"], [v["visit_id"] for v in body["group"]], body["no_show_count"]) == (1, [2], 1)
     assert body["previous_visit"] == {"visit_id": 7, "starts_at": "2026-09-02T14:00:00+09:00", "cover": "t/70"}
     assert (body["record"], body["cover"]) == (None, None)
+    assert body["report"] == {
+        "status": "live", "url": "https://r.example/r/abc", "expires_at": "2026-10-09T18:00:00+09:00",
+        "first_viewed_at": None, "created_at": "2026-09-09T18:00:00+09:00"}
     assert stub.calls[0].visit_id == 1
```

`backend/apps/visit/tests/adapter/test_list_day_visits_router.py`:

```diff
@@ -11,7 +11,7 @@ DAY = DayVisitsView(
     counts=DayCountsView(visit_count=1, reserved=1, in_progress=0, completed=0, canceled=0, no_show=0,
                          unresolved=0),
     items=[DayVisitItemView(visit=visit_view(), group_key="1:2026-10-02T05:00:00+00:00", overlapping=True,
-                            unresolved=False, has_record=True, cover="t/51")],
+                            unresolved=False, has_record=True, cover="t/51", report_sent=True)],
 )
 
 
@@ -24,6 +24,7 @@ async def test_직원도_하루_목록을_본다():
     assert (body["date"], body["counts"]["visit_count"], body["items"][0]["overlapping"]) == (
         "2026-10-02", 1, True)
     assert (body["items"][0]["has_record"], body["items"][0]["cover"]) == (True, "t/51")
+    assert body["items"][0]["report_sent"] is True
     assert body["items"][0]["visit"]["starts_at"] == "2026-10-02T14:00:00+09:00"
     assert stub.calls[0].day == date(2026, 10, 2)
     assert error_of(missing) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_list_visit_feed_router.py`:

```diff
@@ -12,7 +12,7 @@ _V = visit_view()
 FEED = VisitFeedView(
     items=[FeedItemView(visit_id=4, customer=_V.customer, pet=_V.pet,
                         completed_at=datetime(2026, 9, 9, 12, tzinfo=ZoneInfo("Asia/Seoul")), cover="t/51",
-                        menus=["전체 미용"], care_note="눈물 자국", media_count=3)],
+                        menus=["전체 미용"], care_note="눈물 자국", media_count=3, report_sent=True)],
     next_cursor="abc",
 )
 
@@ -25,6 +25,7 @@ async def test_멤버는_피드를_본다_기본은_20개():
     body = response.json()
     assert (body["next_cursor"], body["items"][0]["cover"], body["items"][0]["pet"]["name"]) == ("abc", "t/51", "콩이")
     assert body["items"][0]["completed_at"] == "2026-09-09T12:00:00+09:00"
+    assert body["items"][0]["report_sent"] is True
     assert [(q.cursor, q.limit, q.pet_id) for q in stub.calls] == [(None, 20, None), ("abc", 50, 101)]
```

`backend/apps/visit/tests/app/use_cases/test_delete_visit_record_interactor.py`:

```diff
@@ -1,20 +1,38 @@
+from datetime import timedelta
+
 import pytest
 
 from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
 from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
 from visit.domain.entities.visit_record import RecordMedia, VisitRecord
-from visit.domain.errors import RecordNotFoundError
-from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeRecords, FakeVisits, Journal
+from visit.domain.errors import RecordNotFoundError, VisitReportSentError
+from visit.tests.helpers.builders import ctx, kst, record
+from visit.tests.helpers.fakes import (
+    FakeDirectory,
+    FakeLibrary,
+    FakeRecords,
+    FakeReportRepository,
+    FakeVisits,
+    Journal,
+)
 
+NOW = kst(9, 24, 10)
 
-def _world(status="completed"):
+
+def _with_reports(status="completed"):
     journal = Journal()
     visits, directory = FakeVisits(journal), FakeDirectory(journal)
     directory.family(1, pets=(101,))
     records, library = FakeRecords(visits, journal), FakeLibrary(journal)
+    reports = FakeReportRepository(visits, journal)
     visit = visits.seed(status=status, started_at=kst(9, 23, 14), completed_at=kst(9, 23, 16))
-    return journal, visit, records, DeleteVisitRecordInteractor(visits, records, directory, library)
+    interactor = DeleteVisitRecordInteractor(visits, records, reports, directory, library, now=lambda: NOW)
+    return journal, visit, records, reports, interactor
+
+
+def _world(status="completed"):
+    journal, visit, records, _, interactor = _with_reports(status)
+    return journal, visit, records, interactor
 
 
 async def test_잠근_뒤_미디어를_놓고_기록을_지운다():
@@ -33,3 +51,34 @@ async def test_기록이_없으면_RECORD_NOT_FOUND():
     journal, visit, _, interactor = _world()
     with pytest.raises(RecordNotFoundError):
         await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
+
+
+async def _sent(records, reports, visit, expires_at=NOW + timedelta(days=7)):
+    """사진 하나가 붙은 기록과 어제 보낸 링크."""
+    records.seed(record(visit.id, media=((51, "photo", "after", 0),)))
+    await reports.create(ctx(), visit.id, bytes(16), expires_at, NOW - timedelta(days=1))
+
+
+async def test_알림장을_보낸_방문의_기록은_지울_수_없고_미디어도_놓지_않는다():
+    journal, visit, records, reports, interactor = _with_reports()
+    await _sent(records, reports, visit)
+    journal.clear()
+    with pytest.raises(VisitReportSentError):
+        await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
+    assert visit.id in records.rows
+    assert journal == [("lock_family", 1, ()), ("lock_visits", [visit.id])]
+
+
+async def test_링크를_끊으면_기록을_지울_수_있다():
+    _, visit, records, reports, interactor = _with_reports()
+    await _sent(records, reports, visit)
+    await reports.revoke(ctx(), visit.id, NOW)
+    await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
+    assert visit.id not in records.rows
+
+
+async def test_링크의_기간이_지나면_기록을_지울_수_있다():
+    _, visit, records, reports, interactor = _with_reports()
+    await _sent(records, reports, visit, expires_at=NOW)   # 지금 끝난다
+    await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
+    assert visit.id not in records.rows
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`:

```diff
@@ -1,17 +1,36 @@
+from datetime import timedelta
+
 import pytest
 
 from visit.app.dtos.get_visit_dto import GetVisitQuery
 from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
 from visit.domain.errors import VisitNotFoundError
 from visit.tests.helpers.builders import ctx, kst, record
-from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits
+from visit.domain.services.report_token import read_token
+from visit.tests.helpers.fakes import (
+    FakeDirectory,
+    FakeLibrary,
+    FakeMenus,
+    FakeRecords,
+    FakeReportRepository,
+    FakeVisits,
+)
+
+NOW = kst(9, 24, 10)
+KEY = bytes(range(32))
+NO_LINK = ("none", None, None, None, None)
+
+
+def _interactor(visits, directory, records, library, reports=None):
+    return GetVisitInteractor(
+        visits, visits, visits, FakeMenus(), directory, records, library, reports or FakeReportRepository(visits),
+        now=lambda: NOW, link_key=KEY, web_base_url="https://r.example")
 
 
 def _setup():
     visits, directory = FakeVisits(), FakeDirectory()
     directory.family(1, pets=(101, 102))
-    return visits, GetVisitInteractor(visits, visits, visits, FakeMenus(), directory, FakeRecords(visits),
-                                      FakeLibrary())
+    return visits, _interactor(visits, directory, FakeRecords(visits), FakeLibrary())
 
 
 def _with_records():
@@ -20,7 +39,14 @@ def _with_records():
     records = FakeRecords(visits)
     for media_id in (51, 52, 61):
         library.add(media_id, kind="video" if media_id == 61 else "photo", attached=True)
-    return visits, records, GetVisitInteractor(visits, visits, visits, FakeMenus(), directory, records, library)
+    return visits, records, _interactor(visits, directory, records, library)
+
+
+def _with_reports():
+    visits, directory = FakeVisits(), FakeDirectory()
+    directory.family(1, pets=(101,))
+    reports = FakeReportRepository(visits)
+    return visits, reports, _interactor(visits, directory, FakeRecords(visits), FakeLibrary(), reports)
 
 
 async def test_묶음_지난_방문_노쇼_횟수를_함께_준다():
@@ -75,3 +101,42 @@ async def test_기록이_없으면_record_와_cover_가_비어_있다():
     kong = visits.seed(pet_id=101, starts_at=kst(9, 23, 14))
     detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
     assert (detail.record, detail.cover) == (None, None)
+
+
+def _link(detail):
+    link = detail.report
+    return link.status, link.url, link.expires_at, link.first_viewed_at, link.created_at
+
+
+async def test_보낸_적이_없으면_report_는_none_이다():
+    visits, _, interactor = _with_reports()
+    kong = visits.seed(pet_id=101, starts_at=kst(9, 23, 14))
+    assert _link(await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))) == NO_LINK
+
+
+async def test_살아_있는_링크의_주소와_시각을_매장_시간대로_준다():
+    visits, reports, interactor = _with_reports()
+    done = visits.seed(pet_id=101, starts_at=kst(9, 23, 14), status="completed", started_at=kst(9, 23, 14),
+                       completed_at=kst(9, 23, 16))
+    other = visits.seed(pet_id=101, starts_at=kst(9, 2, 14), status="completed", started_at=kst(9, 2, 14),
+                        completed_at=kst(9, 2, 16))
+    await reports.create(ctx(), done.id, bytes(range(16)), kst(10, 23, 18), kst(9, 23, 18))
+    await reports.mark_viewed(reports.rows[0].id, kst(9, 23, 19))
+    link = (await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=done.id))).report
+    assert (link.status, read_token(link.url.removeprefix("https://r.example/r/"), KEY)) == (
+        "live", bytes(range(16)))
+    assert [t.isoformat() for t in (link.created_at, link.first_viewed_at, link.expires_at)] == [
+        "2026-09-23T18:00:00+09:00", "2026-09-23T19:00:00+09:00", "2026-10-23T18:00:00+09:00"]
+    assert _link(await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=other.id))) == NO_LINK   # 그 방문의 것만
+
+
+async def test_끊었거나_기간이_지난_링크는_none_이다():
+    visits, reports, interactor = _with_reports()
+    done = dict(pet_id=101, status="completed", started_at=kst(9, 2, 14), completed_at=kst(9, 2, 16))
+    revoked = visits.seed(starts_at=kst(9, 2, 14), **done)
+    expired = visits.seed(starts_at=kst(9, 9, 14), **done)
+    await reports.create(ctx(), revoked.id, bytes(16), None, NOW - timedelta(days=8))
+    await reports.revoke(ctx(), revoked.id, NOW - timedelta(days=1))
+    await reports.create(ctx(), expired.id, bytes(16), NOW, NOW - timedelta(days=7))   # 지금 끝난다
+    for visit in (revoked, expired):
+        assert _link(await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=visit.id))) == NO_LINK
```

`backend/apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py`:

```diff
@@ -1,4 +1,4 @@
-from datetime import date, time
+from datetime import date, time, timedelta
 
 import pytest
 
@@ -7,7 +7,15 @@ from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteract
 from visit.domain.errors import VisitInputError
 from visit.domain.value_objects.schedule_settings import ScheduleSettings
 from visit.tests.helpers.builders import ctx, kst, record
-from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeSchedule, FakeVisits
+from visit.tests.helpers.fakes import (
+    FakeDirectory,
+    FakeLibrary,
+    FakeMenus,
+    FakeRecords,
+    FakeReportRepository,
+    FakeSchedule,
+    FakeVisits,
+)
 
 NOW = kst(9, 23, 15)
 
@@ -18,7 +26,7 @@ def _setup(settings=None):
     directory.family(2, pets=(201,), name=None)   # 익명화한 고객
     schedule = FakeSchedule() if settings is None else FakeSchedule(settings=settings)
     interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, FakeRecords(visits),
-                                         FakeLibrary(), now=lambda: NOW)
+                                         FakeLibrary(), FakeReportRepository(visits), now=lambda: NOW)
     return visits, interactor
 
 
@@ -80,7 +88,7 @@ async def test_범위_밖_날짜는_설정을_읽기_전에_거절한다():
     visits, directory = FakeVisits(), FakeDirectory()
     schedule = FakeSchedule()
     interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, FakeRecords(visits),
-                                         FakeLibrary(), now=lambda: NOW)
+                                         FakeLibrary(), FakeReportRepository(visits), now=lambda: NOW)
     for day in (date(1, 1, 1), date(9999, 12, 31)):
         with pytest.raises(VisitInputError):
             await interactor.list_day_visits(ListDayVisitsQuery(ctx=ctx(), day=day))
@@ -93,7 +101,7 @@ async def test_기록이_있는지와_대표_사진을_준다():
     records, library = FakeRecords(visits), FakeLibrary()
     library.add(51, attached=True)
     interactor = ListDayVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory, records, library,
-                                         now=lambda: NOW)
+                                         FakeReportRepository(visits), now=lambda: NOW)
     photographed = visits.seed(pet_id=101, starts_at=kst(9, 23, 10), status="in_progress", started_at=kst(9, 23, 10))
     noted = visits.seed(pet_id=102, starts_at=kst(9, 23, 11), status="in_progress", started_at=kst(9, 23, 11))
     visits.seed(pet_id=101, starts_at=kst(9, 23, 16))
@@ -101,3 +109,24 @@ async def test_기록이_있는지와_대표_사진을_준다():
     records.seed(record(noted.id, care_note="메모만"))
     view = await _day(interactor, date(2026, 9, 23))
     assert [(i.has_record, i.cover) for i in view.items] == [(True, "t/51"), (True, None), (False, None)]
+
+
+async def test_알림장을_보낸_방문을_알리고_링크는_한_번에_읽는다():
+    visits, directory = FakeVisits(), FakeDirectory()
+    directory.family(1, pets=(101,))
+    reports = FakeReportRepository(visits)
+    interactor = ListDayVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory, FakeRecords(visits),
+                                         FakeLibrary(), reports, now=lambda: NOW)
+    sent, expired, revoked, *_ = [
+        visits.seed(pet_id=101, starts_at=kst(9, 22, hour), status="completed", started_at=kst(9, 22, hour),
+                    completed_at=kst(9, 22, hour + 1))
+        for hour in (10, 12, 14, 16, 18)
+    ]
+    sent_at = NOW - timedelta(hours=3)
+    await reports.create(ctx(), sent.id, bytes(16), NOW + timedelta(days=7), sent_at)
+    await reports.create(ctx(), expired.id, bytes(16), NOW, sent_at)   # 지금 끝난다
+    await reports.create(ctx(), revoked.id, bytes(16), None, sent_at)
+    await reports.revoke(ctx(), revoked.id, NOW)
+    view = await _day(interactor, date(2026, 9, 22))
+    assert [i.report_sent for i in view.items] == [True, False, False, False, False]
+    assert reports.reads == ["live_visit_ids"]   # 방문이 다섯이어도 한 번
```

`backend/apps/visit/tests/app/use_cases/test_list_visit_feed_interactor.py`:

```diff
@@ -1,8 +1,19 @@
+from datetime import timedelta
+
 from visit.app.dtos.list_visit_feed_dto import ListVisitFeedQuery
 from visit.app.use_cases.list_visit_feed_interactor import ListVisitFeedInteractor
 from visit.domain.entities.visit_record import RecordItem
 from visit.tests.helpers.builders import ctx, kst, record
-from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits
+from visit.tests.helpers.fakes import (
+    FakeDirectory,
+    FakeLibrary,
+    FakeMenus,
+    FakeRecords,
+    FakeReportRepository,
+    FakeVisits,
+)
+
+NOW = kst(9, 24, 10)
 
 
 class _World:
@@ -11,7 +22,9 @@ class _World:
         self.directory.family(1, pets=(101, 102))
         self.records, self.library = FakeRecords(self.visits), FakeLibrary()
         self.bath, self.trim = self.menus.seed("목욕"), self.menus.seed("전체 미용")
-        self.interactor = ListVisitFeedInteractor(self.visits, self.records, self.menus, self.directory, self.library)
+        self.reports = FakeReportRepository(self.visits)
+        self.interactor = ListVisitFeedInteractor(self.visits, self.records, self.menus, self.reports,
+                                                  self.directory, self.library, now=lambda: NOW)
 
     def done(self, day, pet_id=101, menu_ids=(), shop_id=1):
         return self.visits.seed(pet_id=pet_id, starts_at=kst(9, day, 10), status="completed", shop_id=shop_id,
@@ -54,3 +67,17 @@ async def test_다른_매장의_방문은_나오지_않는다():
     w = _World()
     w.done(2, shop_id=2)
     assert (await w.feed()).items == []
+
+
+async def test_알림장을_보낸_방문을_알리고_링크는_한_번에_읽는다():
+    w = _World()
+    expired, revoked, never, sent = [w.done(day) for day in (1, 2, 3, 4)]
+    sent_at = NOW - timedelta(days=7)
+    await w.reports.create(ctx(), sent.id, bytes(16), None, sent_at)
+    await w.reports.create(ctx(), expired.id, bytes(16), NOW, sent_at)   # 지금 끝난다
+    await w.reports.create(ctx(), revoked.id, bytes(16), None, sent_at)
+    await w.reports.revoke(ctx(), revoked.id, NOW)
+    view = await w.feed()
+    assert [(i.visit_id, i.report_sent) for i in view.items] == [
+        (sent.id, True), (never.id, False), (revoked.id, False), (expired.id, False)]
+    assert w.reports.reads == ["live_visit_ids"]
```

`backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`:

```diff
@@ -1,4 +1,5 @@
 from dataclasses import replace
+from datetime import timedelta
 
 import pytest
 
@@ -9,21 +10,29 @@ from visit.domain.errors import (
     VisitGroupMismatchError,
     VisitInputError,
     VisitNotYetError,
+    VisitReportSentError,
     VisitStateConflictError,
 )
 from visit.tests.helpers.builders import ctx, kst
 from hub.app.errors import FamilyPetPassedAwayError
-from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits, Journal
+from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeReportRepository, FakeVisits, Journal
 
 NOW = kst(9, 23, 15)
 
 
-def _setup():
+def _with_reports(visits=None):
     journal = Journal()
-    visits, directory = FakeVisits(journal), FakeDirectory(journal)
+    visits, directory = visits or FakeVisits(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102, 103), passed=(103,))
     directory.family(2, pets=(201,))
-    return journal, visits, TransitionVisitsInteractor(visits, visits, FakeMenus(), directory, now=lambda: NOW)
+    reports = FakeReportRepository(visits)
+    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), reports, directory, now=lambda: NOW)
+    return journal, visits, reports, interactor
+
+
+def _setup():
+    journal, visits, _, interactor = _with_reports()
+    return journal, visits, interactor
 
 
 def _act(ids, action, reason=None, member_id=11):
@@ -137,6 +146,75 @@ async def test_되돌리기_잠그는_사이_반려동물이_바뀌면_다시_
     canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled",
                            canceled_at=NOW, cancel_reason="customer_request")
     visits._swap_visit_id = canceled.id
-    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), directory, now=lambda: NOW)
+    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), FakeReportRepository(visits), directory,
+                                            now=lambda: NOW)
     with pytest.raises(VisitStateConflictError):
         await interactor.transition_visits(_act([canceled.id], "revert"))
+
+
+def _done(visits, pet_id=101):
+    return visits.seed(customer_id=1, pet_id=pet_id, starts_at=kst(9, 23, 13), status="completed",
+                       started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))
+
+
+async def _send(reports, visit_id, expires_at=NOW + timedelta(days=7)):
+    """어제 보낸 링크."""
+    await reports.create(ctx(), visit_id, bytes(16), expires_at, NOW - timedelta(days=1))
+
+
+async def test_알림장을_보낸_완료_방문은_되돌릴_수_없다():
+    journal, visits, reports, interactor = _with_reports()
+    sent = _done(visits)
+    await _send(reports, sent.id)
+    with pytest.raises(VisitReportSentError):
+        await interactor.transition_visits(_act([sent.id], "revert"))
+    assert visits.rows[sent.id].status == "completed"
+    assert [entry[0] for entry in journal] == ["lock_family", "lock_visits"]
+
+
+async def test_링크를_끊으면_되돌려진다():
+    _, visits, reports, interactor = _with_reports()
+    sent = _done(visits)
+    await _send(reports, sent.id)
+    await reports.revoke(ctx(), sent.id, NOW)
+    await interactor.transition_visits(_act([sent.id], "revert"))
+    assert visits.rows[sent.id].status == "reserved"
+
+
+async def test_링크의_기간이_지나면_되돌려진다():
+    _, visits, reports, interactor = _with_reports()
+    sent = _done(visits)
+    await _send(reports, sent.id, expires_at=NOW)   # 지금 끝난다
+    await interactor.transition_visits(_act([sent.id], "revert"))
+    assert visits.rows[sent.id].status == "reserved"
+
+
+async def test_함께_되돌리는_방문_하나에_알림장이_있으면_둘_다_그대로다():
+    journal, visits, reports, interactor = _with_reports()
+    kong, bori = _done(visits), _done(visits, pet_id=102)
+    await _send(reports, bori.id)
+    with pytest.raises(VisitReportSentError):
+        await interactor.transition_visits(_act([kong.id, bori.id], "revert"))
+    assert (visits.rows[kong.id].status, visits.rows[bori.id].status) == ("completed", "completed")
+    assert "apply_changes" not in [entry[0] for entry in journal]
+
+
+class _SentWhileLocking(FakeVisits):
+    """잠금을 기다리는 사이 다른 요청이 알림장을 보낸 상황을 흉내 낸다 — 잠금을 얻었을 때는 링크가 있다."""
+
+    reports: FakeReportRepository
+
+    async def lock(self, ctx, visit_ids):
+        for visit_id in visit_ids:
+            await _send(self.reports, visit_id)
+        return await super().lock(ctx, visit_ids)
+
+
+async def test_알림장을_보냈는지는_잠근_뒤에_읽는다():
+    """R9 — 잠그기 전에 읽으면 '링크 없음'을 보고 되돌려 버린다."""
+    _, visits, reports, interactor = _with_reports(_SentWhileLocking())
+    visits.reports = reports
+    sent = _done(visits)
+    with pytest.raises(VisitReportSentError):
+        await interactor.transition_visits(_act([sent.id], "revert"))
+    assert visits.rows[sent.id].status == "completed"
```

`backend/apps/visit/tests/app/use_cases/test_visit_ledger_interactor.py`:

```diff
@@ -1,19 +1,26 @@
+from datetime import timedelta
+
 from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
 from visit.tests.helpers.builders import ctx, kst, record
-from visit.tests.helpers.fakes import FakeRecords, FakeVisits
+from visit.tests.helpers.fakes import FakeRecords, FakeReportRepository, FakeVisits
 
 NOW = kst(9, 23, 15)
 
 
-def _ledger():
+def _with_reports():
     visits = FakeVisits()
-    return visits, VisitLedgerInteractor(visits, FakeRecords(visits), now=lambda: NOW)
+    records, reports = FakeRecords(visits), FakeReportRepository(visits)
+    return visits, records, reports, VisitLedgerInteractor(visits, records, reports, now=lambda: NOW)
+
+
+def _ledger():
+    visits, _, _, ledger = _with_reports()
+    return visits, ledger
 
 
 def _with_records():
-    visits = FakeVisits()
-    records = FakeRecords(visits)
-    return visits, records, VisitLedgerInteractor(visits, records, now=lambda: NOW)
+    visits, records, _, ledger = _with_reports()
+    return visits, records, ledger
 
 
 async def test_반려동물의_방문과_앞으로의_예약():
@@ -79,3 +86,21 @@ async def test_반려동물마다_사진이_붙은_가장_최근_완료_방문
     records.seed(record(working.id, media=((54, "photo", "after", 0),)))
     records.seed(record(only_video.id, media=((61, "video", "after", 0),)))
     assert await ledger.latest_covers(ctx(), [101, 102, 103]) == {101: 53, 102: 61}
+
+
+async def test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊고_다른_보호자의_것은_그대로다():
+    """R19 — 기간이 지났지만 끊지 않은 줄도 끊는다."""
+    visits, _, reports, ledger = _with_reports()
+    done = dict(status="completed", started_at=kst(9, 2, 10), completed_at=kst(9, 2, 12))
+    live = visits.seed(customer_id=1, starts_at=kst(9, 2, 10), **done)
+    expired = visits.seed(customer_id=1, starts_at=kst(9, 9, 10), **done)
+    others = visits.seed(customer_id=2, **done)
+    theirs = visits.seed(customer_id=1, shop_id=2, **done)   # 다른 매장의 같은 번호 고객
+    sent_at = NOW - timedelta(days=8)
+    for visit, shop_id, expires_at in ((live, 1, None), (expired, 1, NOW - timedelta(days=1)), (others, 1, None),
+                                       (theirs, 2, None)):
+        await reports.create(ctx(shop_id=shop_id), visit.id, bytes(16), expires_at, sent_at)
+    await ledger.clear_customer_memos(ctx(), 1)
+    assert {r.visit_id: r.revoked_at for r in reports.rows} == {
+        live.id: NOW, expired.id: NOW, others.id: None, theirs.id: None}
+    assert await reports.live_visit_ids(ctx(), [live.id, expired.id, others.id], NOW) == {others.id}
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:

```diff
@@ -18,6 +18,6 @@ async def test_자기소개는_묶음의_경로와_권한을_적는다():
                   "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT",
                   "POST /visits/{visit_id}/record/media", "record:delete", "GET·PUT /report-settings",
                   "GET /visits/{visit_id}/report", "PUT /visits/{visit_id}/report",
-                  "DELETE /visits/{visit_id}/report", "REPORT_EMPTY"):
+                  "DELETE /visits/{visit_id}/report", "REPORT_EMPTY", "VISIT_REPORT_SENT", "report_sent"):
         assert words in result.introduction
     assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -407,12 +407,14 @@ class FakeReportRepository(ReportRepository, PublicReportRepository):
     """visit_reports 스텁 — pg 구현처럼 두 포트를 한 객체가 낸다. 방문의 매장은 visits 스텁에서 본다.
 
     끊지 않은 줄이 있는 방문에 또 만들면 AssertionError 다 — 인터랙터가 닫기(close_expired)나 끊기를 빠뜨린 것이다.
+    살아 있는 링크를 읽은 호출은 reads 에 이름으로 남는다(journal 에는 쓰기만 남긴다).
     """
 
     def __init__(self, visits: FakeVisits, journal: Journal | None = None) -> None:
         self.visits = visits
         self.journal = journal if journal is not None else Journal()
         self.rows: list[VisitReport] = []
+        self.reads: list[str] = []
 
     def _open(self, ctx, **visit_fields) -> list[VisitReport]:
         """이 매장의, 조건에 맞는 방문에 달린 끊지 않은 줄."""
@@ -426,9 +428,11 @@ class FakeReportRepository(ReportRepository, PublicReportRepository):
         self.rows = [replace(r, revoked_at=now) if r in reports else r for r in self.rows]
 
     async def get_live(self, ctx, visit_id, now):
+        self.reads.append("get_live")
         return next((r for r in self._open(ctx, id=visit_id) if r.is_live(now)), None)
 
     async def live_visit_ids(self, ctx, visit_ids, now):
+        self.reads.append("live_visit_ids")
         return {r.visit_id for r in self._open(ctx) if r.visit_id in visit_ids and r.is_live(now)}
 
     async def close_expired(self, ctx, visit_id, now):
```

`backend/tests/integration/test_customer_locking.py`:

```diff
@@ -26,6 +26,7 @@ from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenErro
 from customer.tests.helpers.fakes import today
 from customer.tests.helpers.inputs import customer_input, pet_input
 from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
+from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
 from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
@@ -44,7 +45,8 @@ def _repos(session):
 
 def _ledger(session):
     """customer 유스케이스가 묻는 방문 장부 — 진입점이 꽂는 것과 같은 실제 구현(visit)."""
-    return VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session), now=utc_now)
+    return VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session),
+                                 ReportPgRepository(session), now=utc_now)
 
 
 def _register(session, name):
```

`backend/tests/integration/test_visit_locking.py`:

```diff
@@ -20,6 +20,7 @@ from customer.domain.errors import CustomerHasUpcomingVisitsError
 from customer.tests.helpers.profiles import customer_profile, pet_profile
 from hub.app.errors import FamilyNotFoundError
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
+from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
@@ -60,7 +61,8 @@ def _register(session, customer_id, pet_ids, starts_at=kst(10, 2, 14)):
 def _transition(session, visit_ids, action, reason=None):
     visits = VisitPgRepository(session)
     interactor = TransitionVisitsInteractor(
-        visits, visits, MenuPgRepository(session), _directory(session), now=lambda: NOW
+        visits, visits, MenuPgRepository(session), ReportPgRepository(session), _directory(session),
+        now=lambda: NOW,
     )
     return interactor.transition_visits(TransitionVisitsCommand(
         ctx=SHOP, visit_ids=tuple(visit_ids), action=action, cancel_reason=reason,
@@ -68,7 +70,8 @@ def _transition(session, visit_ids, action, reason=None):
 
 
 def _anonymize(session, customer_id):
-    ledger = VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session), now=lambda: NOW)
+    ledger = VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session),
+                                   ReportPgRepository(session), now=lambda: NOW)
     return DeleteCustomerInteractor(CustomerPgRepository(session), CustomerSearchPgAdapter(session), ledger) \
         .delete_customer(DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id))
```

`backend/tests/integration/test_visit_report_locking.py`:

```diff
@@ -1,4 +1,4 @@
-"""알림장 보내기의 경합 — 실제 두 세션으로 확인한다(막힌 호출을 create_task 로 들고, 앞선 세션이 커밋한 뒤의 결과를 본다)."""
+"""알림장의 경합 — 실제 두 세션으로 확인한다(막힌 호출을 create_task 로 들고, 앞선 세션이 커밋한 뒤의 결과를 본다)."""
 import asyncio
 
 import pytest
@@ -20,8 +20,15 @@ from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
 from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
+from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
+from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
 from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
+from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
+from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
+from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
 from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
+from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
+from visit.domain.errors import VisitReportSentError
 from visit.tests.helpers.builders import ctx, kst, record
 from visit.tests.helpers.fakes import FakeShopProfile
 from visit.tests.helpers.rows import insert_visit
@@ -33,26 +40,71 @@ PROFILE = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, tim
 BLOCKED = 0.5
 
 
+def _now():
+    return kst(9, 24, 10)
+
+
+def _directory(session):
+    return CustomerDirectoryInteractor(CustomerPgRepository(session), PetPgRepository(session),
+                                       FamilyBriefPgRepository(session), CustomerSearchPgAdapter(session))
+
+
+def _library(session):
+    return MediaLibraryInteractor(MediaPgRepository(session), FakeStorage(), now=_now)
+
+
 def _send(session):
-    directory = CustomerDirectoryInteractor(CustomerPgRepository(session), PetPgRepository(session),
-                                            FamilyBriefPgRepository(session), CustomerSearchPgAdapter(session))
-    library = MediaLibraryInteractor(MediaPgRepository(session), FakeStorage(), now=lambda: kst(9, 24, 10))
     return SendVisitReportInteractor(
         visits=VisitPgRepository(session), records=VisitRecordPgRepository(session),
         settings=ReportSettingsPgRepository(session), reports=ReportPgRepository(session),
-        menus=MenuPgRepository(session), directory=directory, library=library,
-        shops=FakeShopProfile({1: PROFILE}), now=lambda: kst(9, 24, 10), link_key=bytes(range(32)),
+        menus=MenuPgRepository(session), directory=_directory(session), library=_library(session),
+        shops=FakeShopProfile({1: PROFILE}), now=_now, link_key=bytes(range(32)),
         web_base_url="https://r.example",
     )
 
 
-async def test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고_링크는_하나다(db_engine, db_session):
-    """R8 — 고객 행 → 방문 행 잠금을 빼면 늦은 쪽도 '링크 없음'을 읽고 새 줄을 넣으려다 유일 색인에 걸린다."""
+def _revert(session, visit_id):
+    visits = VisitPgRepository(session)
+    return TransitionVisitsInteractor(
+        visits, visits, MenuPgRepository(session), ReportPgRepository(session), _directory(session), now=_now,
+    ).transition_visits(TransitionVisitsCommand(ctx=SHOP, visit_ids=(visit_id,), action="revert",
+                                                cancel_reason=None))
+
+
+def _delete_record(session, visit_id):
+    return DeleteVisitRecordInteractor(
+        VisitPgRepository(session), VisitRecordPgRepository(session), ReportPgRepository(session),
+        _directory(session), _library(session), now=_now,
+    ).delete_visit_record(DeleteVisitRecordCommand(ctx=SHOP, visit_id=visit_id))
+
+
+def _revoke(session, visit_id):
+    return RevokeVisitReportInteractor(
+        VisitPgRepository(session), ReportPgRepository(session), _directory(session), now=_now,
+    ).revoke_visit_report(RevokeVisitReportCommand(ctx=SHOP, visit_id=visit_id))
+
+
+async def _recorded_visit(db_session) -> int:
+    """케어 메모를 적고 완료한 방문."""
     customer = await CustomerPgRepository(db_session).create(SHOP, customer_profile())
     pet = await PetPgRepository(db_session).add(SHOP, customer.id, pet_profile())
     visit_id = await insert_visit(db_session, kst(9, 23, 14), "completed", customer_id=customer.id, pet_id=pet.id)
     await VisitRecordPgRepository(db_session).save(SHOP, record(visit_id, care_note="눈물 자국"))
     await db_session.commit()
+    return visit_id
+
+
+async def _after(db_session, visit_id):
+    """(방문의 상태, 기록이 있는가, 링크마다 살아 있는가)"""
+    return (await db_session.execute(text(
+        "SELECT v.status, EXISTS (SELECT 1 FROM visit_records r WHERE r.visit_id = v.id),"
+        " ARRAY(SELECT l.revoked_at IS NULL FROM visit_reports l WHERE l.visit_id = v.id ORDER BY l.id)"
+        " FROM visits v WHERE v.id = :id"), {"id": visit_id})).one()
+
+
+async def test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고_링크는_하나다(db_engine, db_session):
+    """R8 — 고객 행 → 방문 행 잠금을 빼면 늦은 쪽도 '링크 없음'을 읽고 새 줄을 넣으려다 유일 색인에 걸린다."""
+    visit_id = await _recorded_visit(db_session)
     command = SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=())
 
     sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
@@ -69,3 +121,42 @@ async def test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고
     rows = (await db_session.execute(
         text("SELECT revoked_at FROM visit_reports WHERE visit_id = :id"), {"id": visit_id})).all()
     assert rows == [(None,)]
+
+
+@pytest.mark.parametrize("late_call", [_revert, _delete_record])
+async def test_보내는_동안_온_되돌리기와_기록_삭제는_기다렸다가_VISIT_REPORT_SENT_로_끝난다(
+        db_engine, db_session, late_call):
+    """R9 — 링크를 잠그기 전에 읽으면 '링크 없음'을 본 채 기다렸다가, 보낸 방문을 되돌리거나 기록을 지워 버린다."""
+    visit_id = await _recorded_visit(db_session)
+
+    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
+    async with sessions() as sending, sessions() as second:
+        await _send(sending).send_visit_report(
+            SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=()))
+        late = asyncio.create_task(late_call(second, visit_id))
+        await asyncio.sleep(BLOCKED)
+        assert not late.done()
+        await sending.commit()
+        with pytest.raises(VisitReportSentError):
+            await late
+        await second.rollback()
+
+    assert await _after(db_session, visit_id) == ("completed", True, [True])
+
+
+async def test_보내는_동안_온_끊기는_기다렸다가_그_링크를_끊는다(db_engine, db_session):
+    """끊기가 잠그지 않으면 아직 커밋되지 않은 링크를 보지 못해 REPORT_NOT_FOUND 로 끝나고 링크는 살아 있다."""
+    visit_id = await _recorded_visit(db_session)
+
+    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
+    async with sessions() as sending, sessions() as revoking:
+        await _send(sending).send_visit_report(
+            SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=()))
+        late = asyncio.create_task(_revoke(revoking, visit_id))
+        await asyncio.sleep(BLOCKED)
+        assert not late.done()
+        await sending.commit()
+        await late
+        await revoking.commit()
+
+    assert await _after(db_session, visit_id) == ("completed", True, [False])
```

`backend/tests/integration/test_visit_report_wiring.py`:

```diff
@@ -241,3 +241,70 @@ async def test_알림장에서_뺀_사진은_기록을_고치고_사진을_덧
     assert appended.status_code == 200, appended.text
     assert await hidden() == {first: False, removed: True, last: False, added: False}
     assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"] == sent.json()["link"]
+
+
+async def test_보낸_방문은_되돌리지_못하고_끊으면_되돌려진다(wired):
+    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    visit_id, _ = await _completed_visit(wired, shop_id, o)
+    report = f"/v1/shops/{shop_id}/visits/{visit_id}/report"
+    revert = {"visit_ids": [visit_id], "action": "revert"}
+    assert (await wired.api.put(report, headers=o, json={"hidden_media_ids": []})).status_code == 200
+
+    assert error_of(await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o, json=revert)) == (
+        409, "VISIT_REPORT_SENT")
+    detail = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=o)).json()
+    assert (detail["visit"]["status"], detail["report"]["status"]) == ("completed", "live")
+
+    assert (await wired.api.delete(report, headers=o)).status_code == 204
+    reverted = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o, json=revert)
+    assert (reverted.status_code, reverted.json()["visits"][0]["status"]) == (200, "reserved")
+
+
+async def test_보낸_방문의_기록은_지우지_못하고_끊으면_지워진다(wired, media_storage):
+    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    visit_id, [photo] = await _completed_visit(wired, shop_id, o, photos=1)
+    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
+    assert (await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})).status_code == 200
+
+    assert error_of(await wired.api.delete(f"{visit}/record", headers=o)) == (409, "VISIT_REPORT_SENT")
+    kept = (await wired.api.get(visit, headers=o)).json()["record"]
+    assert [m["media_id"] for m in kept["media"]] == [photo]
+
+    assert (await wired.api.delete(f"{visit}/report", headers=o)).status_code == 204
+    assert (await wired.api.delete(f"{visit}/record", headers=o)).status_code == 204
+    assert (await wired.api.get(visit, headers=o)).json()["record"] is None
+
+
+async def test_고객을_삭제하면_그_고객의_알림장_링크가_끊긴다(wired):
+    """R19"""
+    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    visit_id, _ = await _completed_visit(wired, shop_id, o)
+    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
+    assert (await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})).status_code == 200
+    customer_id = (await wired.api.get(visit, headers=o)).json()["visit"]["customer"]["customer_id"]
+
+    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204
+
+    assert (await wired.api.get(visit, headers=o)).json()["report"] == NO_LINK
+    async with wired.engine.connect() as conn:
+        rows = (await conn.execute(text("SELECT revoked_at IS NOT NULL FROM visit_reports"))).all()
+    assert rows == [(True,)]
+
+
+async def test_보낸_방문은_상세와_하루_목록과_피드에_보냄으로_나온다(wired):
+    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    visit_id, _ = await _completed_visit(wired, shop_id, o)
+    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
+
+    async def seen():
+        detail = (await wired.api.get(visit, headers=o)).json()
+        day = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={YESTERDAY.isoformat()}", headers=o)).json()
+        feed = (await wired.api.get(f"/v1/shops/{shop_id}/visits/feed", headers=o)).json()
+        return detail["report"], [i["report_sent"] for i in day["items"]], [i["report_sent"] for i in feed["items"]]
+
+    assert await seen() == (NO_LINK, [False], [False])
+    sent = await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})
+    assert sent.status_code == 200, sent.text
+    assert await seen() == (sent.json()["link"], [True], [True])
+    assert (await wired.api.delete(f"{visit}/report", headers=o)).status_code == 204
+    assert await seen() == (NO_LINK, [False], [False])
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

명령은 모두 `infra/` 에서 `docker compose run --rm backend pytest <경로들> -q -p no:cacheprovider`.

작업 테스트 열세 파일: `3 errors in 0.53s` — 라우터 테스트 셋이 수집 오류.
`TypeError: VisitDetailView.__init__() got an unexpected keyword argument 'report'`, `DayVisitItemView … 'report_sent'`, `FeedItemView … 'report_sent'`.

수집되는 열 파일만 따로: `56 failed, 11 passed in 8.07s`.
- 새 테스트는 모두 실패(단위 14, 배선 4, 경합 `[_revert]`·`[_delete_record]`). 기존 테스트도 생성자 인자가 늘어 `TypeError` 로 실패했다.
- **끊기 경합 테스트 하나는 RED 에서 통과했다** — 끊기 코드는 T6 에 이미 있다. 변이 9 로 실패를 확인했다.
- 자기소개 테스트는 RED 를 따로 보지 않았다. 변이 14 로 확인했다.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/ports/visit_ledger_port.py`:

```diff
@@ -33,8 +33,9 @@ class VisitLedgerPort(ABC):
 
     @abstractmethod
     async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
-        """그 고객 방문들의 메모와 미용 기록의 두 메모(케어·내부)를 비운다 — 익명화 때 메모에 남은 개인정보를
-        지운다(V11, 설계 6.4). 사진은 매장의 미용 기록이라 남긴다."""
+        """그 고객 방문들의 메모와 미용 기록의 두 메모(케어·내부)를 비우고, 그 방문들의 알림장 링크를 끊는다 —
+        익명화 때 메모에 남은 개인정보를 지우고(V11, 설계 6.4) 보호자에게 보낸 페이지를 닫는다. 사진은 매장의
+        미용 기록이라 남긴다. 부르는 쪽의 트랜잭션 안에서 한다."""
 
     @abstractmethod
     async def latest_covers(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_schema.py`:

```diff
@@ -5,6 +5,7 @@ from datetime import datetime
 from pydantic import BaseModel
 
 from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
+from visit.adapter.inbound.api.schemas.report_view_schema import ReportLinkSchema
 from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
 from visit.app.dtos.get_visit_dto import VisitDetailView
 
@@ -22,6 +23,7 @@ class VisitDetailSchema(BaseModel):
     no_show_count: int
     record: RecordSchema | None   # 미용 기록 — 없으면 null
     cover: str | None             # 대표 사진 썸네일 URL
+    report: ReportLinkSchema      # 알림장 링크의 상태
 
     @classmethod
     def of(cls, view: VisitDetailView) -> VisitDetailSchema:
```

`backend/apps/visit/adapter/inbound/api/schemas/list_day_visits_schema.py`:

```diff
@@ -25,6 +25,7 @@ class DayVisitItemSchema(BaseModel):
     unresolved: bool
     has_record: bool
     cover: str | None   # 대표 사진 썸네일 URL
+    report_sent: bool   # 살아 있는 알림장 링크가 있다
 
 
 class DayVisitsSchema(BaseModel):
```

`backend/apps/visit/adapter/inbound/api/schemas/list_visit_feed_schema.py`:

```diff
@@ -17,6 +17,7 @@ class FeedItemSchema(BaseModel):
     menus: list[str]            # 기록의 실제 메뉴, 없으면 예약 메뉴
     care_note: str | None       # 앞 80자
     media_count: int
+    report_sent: bool           # 살아 있는 알림장 링크가 있다
 
 
 class VisitFeedSchema(BaseModel):
```

`backend/apps/visit/app/dtos/get_visit_dto.py`:

```diff
@@ -5,6 +5,7 @@ from datetime import datetime
 
 from hub.app.dtos.shop_context import ShopContext
 from visit.app.dtos.record_view_dto import RecordView
+from visit.app.dtos.report_view_dto import ReportLinkView
 from visit.app.dtos.visit_view_dto import VisitView
 
 
@@ -29,3 +30,4 @@ class VisitDetailView:
     no_show_count: int                     # 이 보호자의 노쇼 횟수
     record: RecordView | None              # 미용 기록 — 없으면 None
     cover: str | None                      # 대표 사진 썸네일(후 → 전 → 영상 포스터)
+    report: ReportLinkView                 # 알림장 링크의 상태 — 보낸 적이 없거나 닫혔으면 none
```

`backend/apps/visit/app/dtos/list_day_visits_dto.py`:

```diff
@@ -46,6 +46,7 @@ class DayVisitItemView:
     unresolved: bool    # 지난 날인데 아직 예약됨
     has_record: bool    # 미용 기록이 있다
     cover: str | None   # 대표 사진 썸네일
+    report_sent: bool   # 살아 있는 알림장 링크가 있다
 
 
 @dataclass(frozen=True)
```

`backend/apps/visit/app/dtos/list_visit_feed_dto.py`:

```diff
@@ -27,6 +27,7 @@ class FeedItemView:
     menus: list[str]         # 기록의 실제 메뉴, 없으면 예약 메뉴
     care_note: str | None    # 앞 80자
     media_count: int
+    report_sent: bool        # 살아 있는 알림장 링크가 있다
 
 
 @dataclass(frozen=True)
```

`backend/apps/visit/app/use_cases/delete_visit_record_interactor.py`:

```diff
@@ -1,27 +1,33 @@
 from __future__ import annotations
 
+from collections.abc import Callable
+from datetime import datetime
+
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
 from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 from visit.app.services.visit_locking import lock_visits
-from visit.domain.errors import RecordNotFoundError
+from visit.domain.errors import RecordNotFoundError, VisitReportSentError
 
 
 class DeleteVisitRecordInteractor(DeleteVisitRecordUseCase):
     """기록을 지운다 — 방문은 남는다. 붙은 미디어는 놓고, 정리 스크립트가 지운다(설계 8절).
-    상태와 상관없이 지울 수 있다(되돌린 방문에 남은 기록도)."""
+    상태와 상관없이 지울 수 있다(되돌린 방문에 남은 기록도). 알림장을 보낸 방문의 기록은 링크를 끊어야 지울 수 있다."""
 
     def __init__(
-        self, visits: VisitLookupRepository, records: VisitRecordRepository, directory: CustomerDirectoryPort,
-        library: MediaLibraryPort,
+        self, visits: VisitLookupRepository, records: VisitRecordRepository, reports: ReportRepository,
+        directory: CustomerDirectoryPort, library: MediaLibraryPort, now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
         self._records = records
+        self._reports = reports
         self._directory = directory
         self._library = library
+        self._now = now
 
     async def delete_visit_record(self, command: DeleteVisitRecordCommand) -> None:
         ctx = command.ctx
@@ -29,5 +35,7 @@ class DeleteVisitRecordInteractor(DeleteVisitRecordUseCase):
         current = await self._records.get(ctx, visit.id)
         if current is None:
             raise RecordNotFoundError("기록이 없습니다.")
+        if await self._reports.get_live(ctx, visit.id, self._now()) is not None:
+            raise VisitReportSentError("알림장을 보낸 방문입니다. 링크를 먼저 끊어 주세요.")
         await self._library.release(ctx, [m.media_id for m in current.media])
         await self._records.delete(ctx, visit.id)
```

`backend/apps/visit/app/use_cases/get_visit_interactor.py`:

```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from collections.abc import Callable
+from datetime import datetime
 from zoneinfo import ZoneInfo
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
@@ -7,12 +9,14 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.dtos.get_visit_dto import GetVisitQuery, PreviousVisitView, VisitDetailView
 from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 from visit.app.services.cover_reader import cover_urls
 from visit.app.services.record_reader import describe_record
+from visit.app.services.report_reader import describe_link
 from visit.app.services.visit_reader import describe_visits
 
 
@@ -20,7 +24,8 @@ class GetVisitInteractor(GetVisitUseCase):
     def __init__(
         self, visits: VisitLookupRepository, history: VisitHistoryRepository, ledger: VisitLedgerRepository,
         menus: MenuRepository, directory: CustomerDirectoryPort, records: VisitRecordRepository,
-        library: MediaLibraryPort,
+        library: MediaLibraryPort, reports: ReportRepository, now: Callable[[], datetime], link_key: bytes,
+        web_base_url: str,
     ) -> None:
         self._visits = visits
         self._history = history
@@ -29,6 +34,10 @@ class GetVisitInteractor(GetVisitUseCase):
         self._directory = directory
         self._records = records
         self._library = library
+        self._reports = reports
+        self._now = now
+        self._link_key = link_key
+        self._web_base_url = web_base_url
 
     async def get_visit(self, query: GetVisitQuery) -> VisitDetailView:
         ctx = query.ctx
@@ -40,6 +49,7 @@ class GetVisitInteractor(GetVisitUseCase):
         records = await self._records.list_many(ctx, [visit.id] + ([previous.id] if previous else []))
         record = records.get(visit.id)
         covers = await cover_urls(ctx, records, self._library)
+        live = await self._reports.get_live(ctx, visit.id, self._now())
         return VisitDetailView(
             visit=view,
             group=group_views,
@@ -50,4 +60,5 @@ class GetVisitInteractor(GetVisitUseCase):
             no_show_count=await self._ledger.count_no_show(ctx, visit.customer_id),
             record=await describe_record(ctx, record, self._menus, self._library) if record else None,
             cover=covers.get(visit.id),
+            report=describe_link(live, self._link_key, self._web_base_url).in_zone(ZoneInfo(ctx.timezone)),
         )
```

`backend/apps/visit/app/use_cases/list_day_visits_interactor.py`:

```diff
@@ -13,6 +13,7 @@ from visit.app.dtos.list_day_visits_dto import (
 )
 from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
@@ -29,7 +30,7 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
     def __init__(
         self, board: VisitBoardRepository, menus: MenuRepository, schedule: ScheduleRepository,
         directory: CustomerDirectoryPort, records: VisitRecordRepository, library: MediaLibraryPort,
-        now: Callable[[], datetime],
+        reports: ReportRepository, now: Callable[[], datetime],
     ) -> None:
         self._board = board
         self._menus = menus
@@ -37,6 +38,7 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
         self._directory = directory
         self._records = records
         self._library = library
+        self._reports = reports
         self._now = now
 
     async def list_day_visits(self, query: ListDayVisitsQuery) -> DayVisitsView:
@@ -48,10 +50,12 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
         visits = await self._board.list_between(ctx, start, end)
         occupied = await self._board.list_occupied(ctx, start, end)   # 전날 밤에 시작한 방문도 겹칠 수 있다
         closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
-        today = local_date(self._now(), tz)
+        now = self._now()
+        today = local_date(now, tz)
         views = await describe_visits(ctx, visits, self._directory, self._menus)
         recorded = await self._records.list_many(ctx, [v.id for v in visits])
         covers = await cover_urls(ctx, recorded, self._library)
+        sent = await self._reports.live_visit_ids(ctx, [v.id for v in visits], now)
         items = [
             DayVisitItemView(
                 visit=view,
@@ -60,6 +64,7 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
                 unresolved=is_unresolved(visit, today, tz),
                 has_record=visit.id in recorded,
                 cover=covers.get(visit.id),
+                report_sent=visit.id in sent,
             )
             for visit, view in zip(visits, views)
         ]
```

`backend/apps/visit/app/use_cases/list_visit_feed_interactor.py`:

```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from collections.abc import Callable
+from datetime import datetime
 from zoneinfo import ZoneInfo
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
@@ -7,6 +9,7 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.dtos.list_visit_feed_dto import FeedItemView, ListVisitFeedQuery, VisitFeedView
 from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 from visit.app.services.cover_reader import cover_urls
@@ -20,13 +23,16 @@ class ListVisitFeedInteractor(ListVisitFeedUseCase):
 
     def __init__(
         self, feed: VisitFeedRepository, records: VisitRecordRepository, menus: MenuRepository,
-        directory: CustomerDirectoryPort, library: MediaLibraryPort,
+        reports: ReportRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort,
+        now: Callable[[], datetime],
     ) -> None:
         self._feed = feed
         self._records = records
         self._menus = menus
+        self._reports = reports
         self._directory = directory
         self._library = library
+        self._now = now
 
     async def list_visit_feed(self, query: ListVisitFeedQuery) -> VisitFeedView:
         ctx = query.ctx
@@ -34,6 +40,7 @@ class ListVisitFeedInteractor(ListVisitFeedUseCase):
         views = await describe_visits(ctx, page.visits, self._directory, self._menus)
         records = await self._records.list_many(ctx, [v.id for v in page.visits])
         covers = await cover_urls(ctx, records, self._library)
+        sent = await self._reports.live_visit_ids(ctx, [v.id for v in page.visits], self._now())
         item_ids = sorted({i.menu_id for r in records.values() for i in r.items})
         names = {m.id: m.name for m in await self._menus.list_by_ids(ctx, item_ids)} if item_ids else {}
         zone = ZoneInfo(ctx.timezone)
@@ -48,5 +55,6 @@ class ListVisitFeedInteractor(ListVisitFeedUseCase):
                 menus=actual or [m.name for m in view.menus],
                 care_note=note[:CARE_NOTE_PREVIEW] if note else None,
                 media_count=len(record.media) if record else 0,
+                report_sent=visit.id in sent,
             ))
         return VisitFeedView(items=items, next_cursor=page.next_cursor)
```

`backend/apps/visit/app/use_cases/transition_visits_interactor.py`:

```diff
@@ -1,12 +1,14 @@
 from __future__ import annotations
 
 from collections.abc import Callable
+from dataclasses import replace
 from datetime import datetime
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand
 from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.app.services.completion_effects import apply_completion_effects
@@ -21,11 +23,12 @@ class TransitionVisitsInteractor(TransitionVisitsUseCase):
 
     def __init__(
         self, visits: VisitWriteRepository, history: VisitHistoryRepository, menus: MenuRepository,
-        directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        reports: ReportRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
         self._history = history
         self._menus = menus
+        self._reports = reports
         self._directory = directory
         self._now = now
 
@@ -40,6 +43,9 @@ class TransitionVisitsInteractor(TransitionVisitsUseCase):
             raise VisitStateConflictError("다른 기기가 먼저 방문을 바꿨습니다. 다시 불러와 주세요.")
 
         now = self._now()
+        # 알림장을 보냈는지도 잠근 뒤에 읽는다 — 보내기가 같은 잠금을 쥐므로 판정과 쓰기 사이에 링크가 생기지 않는다.
+        sent = await self._reports.live_visit_ids(ctx, ids, now)
+        locked = [replace(v, has_live_report=v.id in sent) for v in locked]
         # 잠근 뒤 다시 읽은 상태로 모두 판정한 다음에 쓴다 — 하나라도 안 되면 아무것도 바꾸지 않는다.
         changes = [(v.id, transition(v, command.action, now, ctx.timezone, command.cancel_reason)) for v in locked]
         changed = await self._visits.apply_changes(ctx, changes, ctx.member_id)
```

`backend/apps/visit/app/use_cases/visit_ledger_interactor.py`:

```diff
@@ -6,6 +6,7 @@ from datetime import datetime
 from hub.app.dtos.shop_context import ShopContext
 from hub.app.dtos.upcoming_visit import UpcomingVisit
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
+from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 from visit.domain.services.visit_record_rules import cover_media_id
@@ -16,10 +17,12 @@ class VisitLedgerInteractor(VisitLedgerPort):
     """허브의 VisitLedgerPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""
 
     def __init__(
-        self, ledger: VisitLedgerRepository, records: VisitRecordRepository, now: Callable[[], datetime]
+        self, ledger: VisitLedgerRepository, records: VisitRecordRepository, reports: ReportRepository,
+        now: Callable[[], datetime],
     ) -> None:
         self._ledger = ledger
         self._records = records
+        self._reports = reports
         self._now = now
 
     async def pet_has_visits(self, ctx: ShopContext, pet_id: int) -> bool:
@@ -42,6 +45,7 @@ class VisitLedgerInteractor(VisitLedgerPort):
     async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
         await self._ledger.clear_memos(ctx, customer_id)
         await self._records.clear_notes(ctx, customer_id)
+        await self._reports.revoke_for_customer(ctx, customer_id, self._now())
 
     async def latest_covers(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
         latest = await self._records.latest_with_media(ctx, pet_ids)
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -53,6 +53,9 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "(응답은 미리보기와 같은 모양, 보낼 것이 없으면 422 REPORT_EMPTY). "
                 "DELETE /visits/{visit_id}/report 는 링크 끊기입니다(record:write, 없으면 404 REPORT_NOT_FOUND). "
                 "기록을 고치거나 사진을 덧붙여도 뺀 사진은 빠져 있습니다. "
+                "알림장을 보낸 방문은 되돌리거나 기록을 지울 수 없습니다(409 VISIT_REPORT_SENT — 링크를 먼저 끊습니다). "
+                "방문 상세는 report(링크 상태), 하루 목록과 피드는 항목마다 report_sent 를 주고, 고객을 삭제하면 "
+                "그 고객의 링크가 끊깁니다. "
                 "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴·알림장 설정 수정은 shop:update(사장)가 필요합니다. "
                 "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                 "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
```

`backend/apps/visit/dependencies/delete_visit_record_provider.py`:

```diff
@@ -8,7 +8,8 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
 from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
 from visit.dependencies.hub_ports import get_customer_directory, get_media_library
-from visit.dependencies.visit_wiring import build_record_repository, build_visit_repository
+from visit.dependencies.visit_wiring import build_record_repository, build_report_repository, build_visit_repository
+from visit.domain.services.visit_schedule import utc_now
 
 
 def get_delete_visit_record_use_case(
@@ -17,6 +18,6 @@ def get_delete_visit_record_use_case(
     library: MediaLibraryPort = Depends(get_media_library),
 ) -> DeleteVisitRecordUseCase:
     return DeleteVisitRecordInteractor(
-        visits=build_visit_repository(db), records=build_record_repository(db), directory=directory,
-        library=library,
+        visits=build_visit_repository(db), records=build_record_repository(db),
+        reports=build_report_repository(db), directory=directory, library=library, now=utc_now,
     )
```

`backend/apps/visit/dependencies/get_visit_provider.py`:

```diff
@@ -2,13 +2,20 @@ from __future__ import annotations
 
 from fastapi import Depends
 
+from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
 from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
 from visit.dependencies.hub_ports import get_customer_directory, get_media_library
-from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository
+from visit.dependencies.visit_wiring import (
+    build_menu_repository,
+    build_record_repository,
+    build_report_repository,
+    build_visit_repository,
+)
+from visit.domain.services.visit_schedule import utc_now
 
 
 def get_get_visit_use_case(
@@ -19,5 +26,6 @@ def get_get_visit_use_case(
     visits = build_visit_repository(db)
     return GetVisitInteractor(
         visits=visits, history=visits, ledger=visits, menus=build_menu_repository(db), directory=directory,
-        records=build_record_repository(db), library=library,
+        records=build_record_repository(db), library=library, reports=build_report_repository(db), now=utc_now,
+        link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
     )
```

`backend/apps/visit/dependencies/list_day_visits_provider.py`:

```diff
@@ -11,6 +11,7 @@ from visit.dependencies.hub_ports import get_customer_directory, get_media_libra
 from visit.dependencies.visit_wiring import (
     build_menu_repository,
     build_record_repository,
+    build_report_repository,
     build_schedule_repository,
     build_visit_repository,
 )
@@ -25,5 +26,5 @@ def get_list_day_visits_use_case(
     return ListDayVisitsInteractor(
         board=build_visit_repository(db), menus=build_menu_repository(db),
         schedule=build_schedule_repository(db), directory=directory, records=build_record_repository(db),
-        library=library, now=utc_now,
+        library=library, reports=build_report_repository(db), now=utc_now,
     )
```

`backend/apps/visit/dependencies/list_visit_feed_provider.py`:

```diff
@@ -8,7 +8,13 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
 from visit.app.use_cases.list_visit_feed_interactor import ListVisitFeedInteractor
 from visit.dependencies.hub_ports import get_customer_directory, get_media_library
-from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository
+from visit.dependencies.visit_wiring import (
+    build_menu_repository,
+    build_record_repository,
+    build_report_repository,
+    build_visit_repository,
+)
+from visit.domain.services.visit_schedule import utc_now
 
 
 def get_list_visit_feed_use_case(
@@ -18,5 +24,5 @@ def get_list_visit_feed_use_case(
 ) -> ListVisitFeedUseCase:
     return ListVisitFeedInteractor(
         feed=build_visit_repository(db), records=build_record_repository(db), menus=build_menu_repository(db),
-        directory=directory, library=library,
+        reports=build_report_repository(db), directory=directory, library=library, now=utc_now,
     )
```

`backend/apps/visit/dependencies/transition_visits_provider.py`:

```diff
@@ -7,7 +7,7 @@ from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
 from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
 from visit.dependencies.hub_ports import get_customer_directory
-from visit.dependencies.visit_wiring import build_menu_repository, build_visit_repository
+from visit.dependencies.visit_wiring import build_menu_repository, build_report_repository, build_visit_repository
 from visit.domain.services.visit_schedule import utc_now
 
 
@@ -16,5 +16,6 @@ def get_transition_visits_use_case(
 ) -> TransitionVisitsUseCase:
     visits = build_visit_repository(db)
     return TransitionVisitsInteractor(
-        visits=visits, history=visits, menus=build_menu_repository(db), directory=directory, now=utc_now
+        visits=visits, history=visits, menus=build_menu_repository(db), reports=build_report_repository(db),
+        directory=directory, now=utc_now,
     )
```

`backend/apps/visit/dependencies/visit_ledger_provider.py`:

```diff
@@ -3,9 +3,12 @@ from __future__ import annotations
 from core.database import DbSession
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
-from visit.dependencies.visit_wiring import build_record_repository, build_visit_repository
+from visit.dependencies.visit_wiring import build_record_repository, build_report_repository, build_visit_repository
 from visit.domain.services.visit_schedule import utc_now
 
 
 def get_visit_ledger_use_case(db: DbSession) -> VisitLedgerPort:
-    return VisitLedgerInteractor(ledger=build_visit_repository(db), records=build_record_repository(db), now=utc_now)
+    return VisitLedgerInteractor(
+        ledger=build_visit_repository(db), records=build_record_repository(db),
+        reports=build_report_repository(db), now=utc_now,
+    )
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 테스트(기존 파일 포함 열일곱 파일) | 90 passed |
| 단위 전체 | 1221 passed, 366 deselected (시작 1207 → +14) |
| 통합 전체 | 366 passed, 1221 deselected (시작 359 → +7) |
| 구조 계약 | 6 kept, 0 broken |

- 새 단위 14: 되돌리기 5, 기록 삭제 3, 익명화 1, 상세 3, 하루 목록 1, 피드 1. 새 통합 7: 배선 4, 경합 3.
- `docker compose run --rm --no-deps auth python scripts/print_routes.py` 를 돌렸다(backend 라우트 59줄, 오류 없음). 이 작업은 라우트를 더하지 않는다.
- `tests/test_hub_port_binding.py` 는 맨 뒤에 두고 돌렸다. 통과한다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `TransitionVisitsInteractor` 가 `live_visit_ids` 를 `lock_visits` 앞에서 읽는다 → 경합 `test_보내는_동안_온_되돌리기와_기록_삭제는_기다렸다가_VISIT_REPORT_SENT_로_끝난다[_revert]`, 단위 `test_알림장을_보냈는지는_잠근_뒤에_읽는다`
- `DeleteVisitRecordInteractor` 의 검사를 `release` 뒤로 → `test_알림장을_보낸_방문의_기록은_지울_수_없고_미디어도_놓지_않는다`
- `clear_customer_memos` 에서 `revoke_for_customer` 를 뺀다 → 단위 `test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊고_다른_보호자의_것은_그대로다`, 배선 `test_고객을_삭제하면_그_고객의_알림장_링크가_끊긴다`
- 하루 목록이 방문마다 `get_live` → `test_list_day_visits_interactor.py::test_알림장을_보낸_방문을_알리고_링크는_한_번에_읽는다`
- 하루 목록이 `now` 대신 2000년을 넘긴다 → 위와 같은 테스트(하루 목록)
- 피드가 2000년을 넘긴다 → `test_list_visit_feed_interactor.py::test_알림장을_보낸_방문을_알리고_링크는_한_번에_읽는다`
- 되돌리기가 2000년을 넘긴다 → `test_링크의_기간이_지나면_되돌려진다`
- 피드가 방문마다 `get_live` → 피드 `test_알림장을_보낸_방문을_알리고_링크는_한_번에_읽는다`
- 상세가 `get_live` 에 2000년을 넘긴다 → `test_끊었거나_기간이_지난_링크는_none_이다`
- 기록 삭제가 `get_live` 에 2000년을 넘긴다 → `test_링크의_기간이_지나면_기록을_지울_수_있다`
- 되돌리기가 `has_live_report` 를 채우지 않는다 → 단위 셋(`test_알림장을_보낸_완료_방문은_되돌릴_수_없다`, `test_알림장을_보냈는지는_잠근_뒤에_읽는다`, `test_함께_되돌리는_방문_하나에_알림장이_있으면_둘_다_그대로다`), 경합 `[_revert]`, 배선 `test_보낸_방문은_되돌리지_못하고_끊으면_되돌려진다`
- 기록 삭제가 `get_live` 를 `lock_visits` 앞에서 읽는다 → 경합 `…[_delete_record]` **하나뿐** — 단위 테스트는 이 변이를 잡지 못한다(7절 2번)
- 기록 삭제가 링크를 보지 않는다 → 단위 `test_알림장을_보낸_방문의_기록은_…`, 경합 `[_delete_record]`, 배선 `test_보낸_방문의_기록은_지우지_못하고_끊으면_지워진다`
- `RevokeVisitReportInteractor` 의 `lock_visits` 를 `get` 으로 → 경합 `test_보내는_동안_온_끊기는_기다렸다가_그_링크를_끊는다`, 단위 `test_잠근_뒤_살아_있는_링크를_끊는다`
- 상세가 `in_zone` 을 부르지 않는다 → 단위 `test_살아_있는_링크의_주소와_시각을_매장_시간대로_준다`, 배선 `test_보낸_방문은_상세와_하루_목록과_피드에_보냄으로_나온다`
- 상세 프로바이더가 `link_key=bytes(32)` → 배선 `test_보낸_방문은_상세와_…`
- 상세 프로바이더가 `web_base_url=''` → 배선 `test_보낸_방문은_상세와_…`
- 하루 목록의 `report_sent` 를 늘 False → 단위(하루 목록), 배선 `test_보낸_방문은_상세와_…`
- 피드의 `report_sent` 를 늘 False → 단위(피드), 배선 `test_보낸_방문은_상세와_…`
- 상세가 살아 있는지 보지 않고 그 방문의 아무 줄이나 넘긴다 → 단위 `test_끊었거나_기간이_지난_링크는_none_이다`, 배선 둘(pg 저장소에는 `rows` 가 없어 늘 none 이 된다)
- 자기소개에서 새 문장 셋을 뺀다 → `test_자기소개는_묶음의_경로와_권한을_적는다`
- 되돌리기가 링크를 읽지 않는다(`sent = set()`) → 변이 6 과 같은 다섯
- 하루 목록 스키마에서 `report_sent` 를 뺀다 → 라우터 `test_직원도_하루_목록을_본다`, 배선 `test_보낸_방문은_상세와_…`
- 피드 스키마에서 `report_sent` 를 뺀다 → 라우터 `test_멤버는_피드를_본다_기본은_20개`, 배선 `test_보낸_방문은_상세와_…`
- 상세 스키마에서 `report` 를 뺀다 → 라우터 `test_직원도_방문_상세를_본다`, 배선 셋

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 알림장을 보낸 방문은 되돌리거나 기록을 지울 수 없다 — 익명화는 링크를 끊고, 상세·목록·피드에 보냄 표시

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: 공개 알림장 — 헤더 토큰으로 읽고 처음 연 시각을 남긴다, 횟수 제한과 공개 경로 허용 목록

**Files:**
- Modify: `backend/apps/visit/adapter/inbound/api/error_map.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/public_report_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/mark_report_viewed_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/read_public_report_router.py`
- Create: `backend/apps/visit/adapter/outbound/redis/__init__.py`
- Create: `backend/apps/visit/adapter/outbound/redis/public_report_redis_limiter.py`
- Create: `backend/apps/visit/app/dtos/mark_report_viewed_dto.py`
- Create: `backend/apps/visit/app/dtos/read_public_report_dto.py`
- Create: `backend/apps/visit/app/ports/input/mark_report_viewed_use_case.py`
- Create: `backend/apps/visit/app/ports/input/read_public_report_use_case.py`
- Create: `backend/apps/visit/app/ports/output/public_report_limiter_port.py`
- Create: `backend/apps/visit/app/services/public_context.py`
- Create: `backend/apps/visit/app/services/public_report_gate.py`
- Create: `backend/apps/visit/app/use_cases/mark_report_viewed_interactor.py`
- Create: `backend/apps/visit/app/use_cases/read_public_report_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/dependencies/mark_report_viewed_provider.py`
- Create: `backend/apps/visit/dependencies/public_client.py`
- Create: `backend/apps/visit/dependencies/read_public_report_provider.py`
- Modify: `backend/apps/visit/dependencies/visit_wiring.py`
- Modify: `backend/apps/visit/domain/errors.py`
- Create: `backend/apps/visit/tests/adapter/test_mark_report_viewed_router.py`
- Create: `backend/apps/visit/tests/adapter/test_public_client.py`
- Create: `backend/apps/visit/tests/adapter/test_public_report_redis_limiter.py`
- Create: `backend/apps/visit/tests/adapter/test_read_public_report_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_report_error_map.py`
- Create: `backend/apps/visit/tests/app/services/test_public_context.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_mark_report_viewed_interactor.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_read_public_report_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Create: `backend/apps/visit/tests/helpers/public_world.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Modify: `backend/main.py`
- Create: `backend/tests/integration/test_public_report_wiring.py`
- Modify: `backend/tests/integration/test_route_wiring.py`
- Modify: `backend/tests/route_inspection.py`
- Modify: `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: 작업 1 의 `read_token`·`VisitReport.is_live`; 작업 2 의 `PublicReportRepository`; 작업 3 의 설정 저장소; 작업 4 의 `ShopProfilePort`; 작업 5 의 `describe_report`·`REPORT_LINK_KEY`·`REPORT_WEB_SECRET`; `core.redis.get_redis`; `tests/route_inspection.py`.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# 경로 (둘 다 로그인 없음, 헤더 X-Report-Token, 응답 헤더 Cache-Control: private, no-store / X-Robots-Tag: noindex, nofollow)
GET  /v1/public/report          200 / 404 REPORT_NOT_FOUND / 410 REPORT_CLOSED / 429 TOO_MANY_ATTEMPTS
POST /v1/public/report/viewed   204 / 404 / 410 / 429
read_public_report_router, mark_report_viewed_router        # prefix "/v1/public", tags ["public"]

# visit/domain/errors.py
class TooManyReportRequestsError(VisitError): code = "TOO_MANY_ATTEMPTS"     # 429

# visit/app/services/public_context.py
def public_context(shop: ShopProfile) -> ShopContext
    # ShopContext(shop_id=shop.shop_id, member_id=0, role="public", permissions=frozenset(), timezone=shop.timezone)

# visit/app/services/public_report_gate.py
async def open_report(token: str | None, client: str, now: datetime, *, link_key: bytes,
                      reports: PublicReportRepository, shops: ShopProfilePort,
                      limiter: PublicReportLimiterPort) -> tuple[ReportTarget, ShopProfile]

# visit/app/ports/output/public_report_limiter_port.py
class PublicReportLimiterPort(ABC):
    async def allow(self, client: str) -> bool        # 요청 하나를 세고, 받아도 되면 True
    async def note_miss(self, client: str) -> None    # 404 하나를 센다

# visit/adapter/outbound/redis/public_report_redis_limiter.py
class PublicReportRedisLimiter(PublicReportLimiterPort):   # 생성자 (redis: Redis)
# 키: visit:report-hits:{sha256(client) 앞 32글자} 60초, visit:report-misses:{같은 해시} 600초

# visit/dependencies
def get_public_client(request: Request) -> str                                   # public_client.py
def build_public_report_limiter() -> PublicReportLimiterPort                     # visit_wiring.py
def get_read_public_report_use_case(db, directory, library, shops) -> ReadPublicReportUseCase
def get_mark_report_viewed_use_case(db, shops) -> MarkReportViewedUseCase

# DTO
ReadPublicReportQuery(token: str | None, client: str)
PublicReportView(report: ReportView, expires_at: datetime | None)      # expires_at 은 매장 시간대
MarkReportViewedCommand(token: str | None, client: str)

# 입력 포트·인터랙터
ReadPublicReportUseCase.read_public_report(query) -> PublicReportView
MarkReportViewedUseCase.mark_report_viewed(command) -> None
ReadPublicReportInteractor(reports: PublicReportRepository, records, settings, menus, directory, library,
                           shops, limiter: PublicReportLimiterPort, now: Callable[[], datetime], link_key: bytes)
MarkReportViewedInteractor(reports: PublicReportRepository, shops, limiter, now, link_key)

# 스키마 — visit/adapter/inbound/api/schemas/public_report_schema.py
PUBLIC_REPORT_HEADERS: dict[str, str]
PublicMediaSchema(kind, phase, width, height, duration_seconds, display_url, thumb_url, download_url)
PublicCoverSchema(url, width, height); PublicMenuSchema(name, amount); PublicShopSchema(name, phone, address)
PublicReportSchema(pet_name, visit_date, care_note, media, cover, menus, total_amount, weight_kg, shop, expires_at)
PublicReportSchema.body(view: PublicReportView) -> dict      # 끈 칸을 뺀 JSON 본문

# tests/route_inspection.py
_PUBLIC_ROUTES = {"GET /v1/public/report", "POST /v1/public/report/viewed"}
def routes_without_login(app: FastAPI) -> set[str]           # "METHOD path"
# find_route_violations 가 더 내는 줄:
#   "{path}: 공개 경로인데 허용 목록에 없다"
#   "{path}: 공개 경로인데 로그인이나 매장 확인을 거친다"

# 스텁
FakePublicReportLimiter()      # .allowed(기본 True), .hits: list[str], .misses: list[str]
visit/tests/helpers/public_world.py — PublicWorld, KEY, NOW, CLIENT, SHOP
```

200 응답의 모양(모든 항목을 켰을 때)
```json
{"pet_name": "콩이", "visit_date": "2026-09-27", "care_note": "…",
 "media": [{"kind": "photo", "phase": "after", "width": 3000, "height": 2000, "duration_seconds": null,
            "display_url": "…", "thumb_url": "…", "download_url": "…"}],
 "cover": {"url": "…", "width": 3000, "height": 2000},
 "menus": [{"name": "목욕", "amount": 28000}], "total_amount": 25000, "weight_kg": 3.4,
 "shop": {"name": "…", "phone": "…", "address": "…"}, "expires_at": "2026-10-28T…+09:00"}
```

뒤 작업(T9·⑤-2 웹)이 알아 둘 동작
- **판정 순서**: 횟수 제한(429) → 토큰의 서명(404, DB 를 읽지 않는다) → 링크 찾기(404) → 살아 있음(410) → 매장(410) → 기록(410).
- **429 는 맞는 토큰에도 난다.** 같은 접속 주소의 실패가 10분에 20번이면 그 주소의 모든 요청이 막힌다. 막힌 요청도 1분 창의 요청 수에 들어간다. 410 은 실패로 세지 않는다.
- **조회와 열람 신호는 같은 통에 센다.** 페이지를 한 번 열면 요청이 둘이다(조회 + 열람) — 한 주소에서 1분에 30번쯤 열면 429 다.
- **비밀값이 없으면 모든 요청이 연결된 주소 하나로 세어진다.** 웹 서버가 `X-Report-Web-Secret` 을 보내지 않거나 백엔드의 `REPORT_WEB_SECRET` 이 비어 있으면 보호자 전체가 분당 60회를 나눠 쓴다. `.env` 에는 지금 `REPORT_WEB_SECRET` 이 비어 있다(설정됐는지만 확인했다).
- **끈 칸은 JSON 키가 없다.** 금액만 끄면 `menus` 의 항목은 `{"name": …}` 뿐이다. 켰지만 값이 없으면 `null`(`weight_kg`, `total_amount`, `menus[].amount`, `care_note`, `cover`, `pet_name`).
- **오류 응답(404·410·429)에는 `Cache-Control`·`X-Robots-Tag` 가 없다**(6절 5번). 본문은 `{code, message}` 뿐이다.
- **닫힌 이유는 가르지 않는다.** 끊음·기간 지남·매장 정지·익명화 모두 410 `REPORT_CLOSED`, 문구도 같다("닫힌 알림장입니다.").
- 열람 신호는 한 번 남으면 바뀌지 않는다. 끊고 다시 보낸 새 링크는 `first_viewed_at` 이 비어 있다.
- 공개 조회는 질의 문자열을 읽지 않는다. `?token=` 을 붙여도 무시된다(헤더가 없으면 404).

설계 3.3·6.3·7.1·7.3, R1·R3·R6·R7·R10~R13·R17·R18·R21. **이 저장소에서 로그인 없이 열리는 첫 API 다.** 검토 기준은 '공개하기로 한 것 말고는 아무것도 나가지 않는다'이다. 공개 스키마는 매장용을 다시 쓰지 않고 칸을 하나하나 적는다. 끈 항목은 JSON 키 자체가 없다. 토큰은 헤더로만 받고, 헤더가 없어도 404 다(422 가 아니다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_mark_report_viewed_router.py`:

```python
import pytest

from visit.adapter.inbound.api.v1.mark_report_viewed_router import mark_report_viewed_router
from visit.dependencies.mark_report_viewed_provider import get_mark_report_viewed_use_case
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.domain.services.report_token import make_token
from visit.tests.helpers.api import Recorder, build_app, client, error_of

TOKEN = make_token(bytes(range(16)), bytes(range(32)))


async def _post(stub, headers=None):
    async with client(build_app(mark_report_viewed_router, get_mark_report_viewed_use_case, stub)) as c:
        return await c.post("/v1/public/report/viewed", headers=headers)


async def test_열람_신호는_본문_없이_204_다():
    stub = Recorder()
    response = await _post(stub, {"X-Report-Token": TOKEN})
    assert (response.status_code, response.content) == (204, b"")
    assert response.headers["cache-control"] == "private, no-store"
    assert (stub.calls[0].token, stub.calls[0].client) == (TOKEN, "127.0.0.1")


@pytest.mark.parametrize("headers", [
    None, {"X-Report-Token": ""}, {"X-Report-Token": "a" * 5000}, {"X-Report-Token": "알림장".encode()},
], ids=["헤더 없음", "빈 값", "5000글자", "한글"])
async def test_이상한_토큰은_422_가_아니라_404_다(headers):
    """R13"""
    stub = Recorder(error=ReportNotFoundError("알림장을 찾을 수 없습니다."))
    assert error_of(await _post(stub, headers)) == (404, "REPORT_NOT_FOUND")
    assert len(stub.calls) == 1


async def test_닫힌_알림장은_410_너무_잦으면_429_다():
    assert error_of(await _post(Recorder(error=ReportClosedError("닫힘")), {"X-Report-Token": TOKEN})) == (
        410, "REPORT_CLOSED")
    assert error_of(await _post(Recorder(error=TooManyReportRequestsError("잦음")), {"X-Report-Token": TOKEN})) == (
        429, "TOO_MANY_ATTEMPTS")
```

`backend/apps/visit/tests/adapter/test_public_client.py`:

```python
"""R17 — 웹 서버가 알려 준 접속 주소는 비밀값이 맞을 때만 믿는다."""
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from visit.dependencies import public_client
from visit.dependencies.public_client import get_public_client

SECRET = "web-secret-for-test"


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(public_client, "REPORT_WEB_SECRET", SECRET)


async def _client_of(headers, peer=("198.51.100.9", 4321)) -> str:
    app = FastAPI()

    @app.get("/who")
    async def who(client: str = Depends(get_public_client)) -> dict:
        return {"client": client}

    async with AsyncClient(transport=ASGITransport(app=app, client=peer), base_url="http://t") as c:
        return (await c.get("/who", headers=headers)).json()["client"]


async def test_비밀값이_맞으면_웹_서버가_알려_준_주소다(secret):
    assert await _client_of({"X-Report-Web-Secret": SECRET, "X-Report-Client-IP": "203.0.113.7"}) == "203.0.113.7"


@pytest.mark.parametrize("headers", [
    {"X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": "", "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": SECRET + "x", "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": SECRET[:-1], "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": "비밀".encode(), "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": SECRET},
    {"X-Report-Web-Secret": SECRET, "X-Report-Client-IP": ""},
    {},
], ids=["비밀값 없음", "빈 비밀값", "긴 비밀값", "짧은 비밀값", "한글 비밀값", "주소 없음", "빈 주소", "헤더 없음"])
async def test_비밀값이_틀리거나_주소가_없으면_연결된_주소다(secret, headers):
    assert await _client_of(headers) == "198.51.100.9"


async def test_비밀값을_설정하지_않았으면_빈_비밀값을_보내도_믿지_않는다(monkeypatch):
    monkeypatch.setattr(public_client, "REPORT_WEB_SECRET", "")
    assert await _client_of({"X-Report-Web-Secret": "", "X-Report-Client-IP": "203.0.113.7"}) == "198.51.100.9"
    assert await _client_of({"X-Report-Client-IP": "203.0.113.7"}) == "198.51.100.9"


async def test_연결된_주소를_모르면_unknown_이다(secret):
    assert await _client_of({}, peer=None) == "unknown"
```

`backend/apps/visit/tests/adapter/test_public_report_redis_limiter.py`:

```python
import hashlib
import logging

import pytest
from redis.asyncio import from_url
from redis.exceptions import ConnectionError as RedisConnectionError

from core.config import REDIS_URL
from visit.adapter.outbound.redis.public_report_redis_limiter import PublicReportRedisLimiter

pytestmark = pytest.mark.integration

CLIENT = "203.0.113.7"


def _key(name: str, client: str = CLIENT) -> str:
    return f"visit:report-{name}:{hashlib.sha256(client.encode()).hexdigest()[:32]}"


@pytest.fixture
async def redis():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    client = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


async def test_1분에_60번까지_받고_61번째부터_막는다(redis):
    """R1"""
    limiter = PublicReportRedisLimiter(redis)
    assert [await limiter.allow(CLIENT) for _ in range(62)] == [True] * 60 + [False, False]


async def test_실패가_20번이_되면_21번째_요청부터_막는다(redis):
    """R1"""
    limiter = PublicReportRedisLimiter(redis)
    for _ in range(19):
        await limiter.note_miss(CLIENT)
    assert await limiter.allow(CLIENT) is True
    await limiter.note_miss(CLIENT)
    assert await limiter.allow(CLIENT) is False


async def test_접속_주소마다_따로_센다(redis):
    limiter = PublicReportRedisLimiter(redis)
    for _ in range(61):
        await limiter.allow(CLIENT)
    for _ in range(20):
        await limiter.note_miss("198.51.100.9")
    assert await limiter.allow("192.0.2.1") is True
    assert (await redis.get(_key("hits", "192.0.2.1")), await redis.get(_key("misses", "192.0.2.1"))) == ("1", None)


async def test_창은_처음_셀_때_잡히고_이후_요청이_늘리지_않는다(redis):
    limiter = PublicReportRedisLimiter(redis)
    await limiter.allow(CLIENT)
    await limiter.note_miss(CLIENT)
    assert 0 < await redis.ttl(_key("hits")) <= 60
    assert 60 < await redis.ttl(_key("misses")) <= 600
    await redis.expire(_key("hits"), 30)
    await redis.expire(_key("misses"), 30)
    await limiter.allow(CLIENT)
    await limiter.note_miss(CLIENT)
    assert 0 < await redis.ttl(_key("hits")) <= 30
    assert 0 < await redis.ttl(_key("misses")) <= 30


async def test_창이_지나면_다시_받는다(redis):
    """기다리지 않는다 — 창이 끝난 것은 키가 사라진 것이다."""
    limiter = PublicReportRedisLimiter(redis)
    for _ in range(61):
        await limiter.allow(CLIENT)
    for _ in range(20):
        await limiter.note_miss(CLIENT)
    await redis.delete(_key("hits"))
    assert await limiter.allow(CLIENT) is False      # 실패의 창은 아직 남아 있다
    await redis.delete(_key("misses"))
    assert await limiter.allow(CLIENT) is True


async def test_아주_긴_접속_주소도_키는_짧다(redis):
    limiter = PublicReportRedisLimiter(redis)
    await limiter.allow("1" * 5000)
    await limiter.note_miss("1" * 5000)
    keys = sorted(await redis.keys("*"))
    assert keys == [_key("hits", "1" * 5000), _key("misses", "1" * 5000)]
    assert all(len(k) < 64 and "1" * 40 not in k for k in keys)


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
    limiter = PublicReportRedisLimiter(_DeadRedis())
    with caplog.at_level(logging.WARNING):
        assert await limiter.allow(CLIENT) is True
        await limiter.note_miss(CLIENT)
    assert [r.levelname for r in caplog.records] == ["WARNING", "WARNING"]
    assert CLIENT not in caplog.text
```

`backend/apps/visit/tests/adapter/test_read_public_report_router.py`:

```python
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from visit.adapter.inbound.api.v1.read_public_report_router import read_public_report_router
from visit.app.dtos.read_public_report_dto import PublicReportView
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.dependencies.read_public_report_provider import get_read_public_report_use_case
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.domain.services.report_token import make_token
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.api import Recorder, build_app, client, error_of

TOKEN = make_token(bytes(range(16)), bytes(range(32)))
ALL_ON = ReportSettings(link_days=30, show_menus=True, show_shop_info=True, show_weight=True, show_amount=True)
REPORT = ReportView(
    pet_name="콩이", visit_date=date(2026, 9, 23), care_note="눈물 자국",
    media=(ReportMediaView(media_id=52, kind="video", phase="after", hidden=False, width=1920, height=1080,
                           duration_seconds=12, display_url="d/52", thumb_url="t/52", download_url="dl/52"),),
    cover=ReportCoverView(url="t/52", width=1920, height=1080),
    menus=(ReportMenuView(name="목욕", amount=30000), ReportMenuView(name="발톱", amount=None)),
    total_amount=30000, weight_kg=Decimal("3.4"),
    shop=ReportShopView(name="Hiss Haus", phone="02-123-4567", address=None), settings=ALL_ON,
)
EXPIRES_AT = datetime(2026, 10, 23, 15, tzinfo=ZoneInfo("Asia/Seoul"))
FULL = {
    "pet_name": "콩이", "visit_date": "2026-09-23", "care_note": "눈물 자국",
    "media": [{"kind": "video", "phase": "after", "width": 1920, "height": 1080, "duration_seconds": 12,
               "display_url": "d/52", "thumb_url": "t/52", "download_url": "dl/52"}],
    "cover": {"url": "t/52", "width": 1920, "height": 1080},
    "menus": [{"name": "목욕", "amount": 30000}, {"name": "발톱", "amount": None}],
    "total_amount": 30000, "weight_kg": 3.4,
    "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": None},
    "expires_at": "2026-10-23T15:00:00+09:00",
}


def _view(**settings) -> PublicReportView:
    """조립 함수가 하듯 끈 항목은 비워 둔 알림장."""
    chosen = ReportSettings(**{**vars(ALL_ON), **settings})
    menus = None if not chosen.show_menus else tuple(
        ReportMenuView(name=m.name, amount=m.amount if chosen.show_amount else None) for m in REPORT.menus)
    report = ReportView(**{
        **vars(REPORT), "settings": chosen, "menus": menus,
        "total_amount": REPORT.total_amount if chosen.show_amount else None,
        "weight_kg": REPORT.weight_kg if chosen.show_weight else None,
        "shop": REPORT.shop if chosen.show_shop_info else None,
    })
    return PublicReportView(report=report, expires_at=EXPIRES_AT)


async def _get(stub, headers=None):
    async with client(build_app(read_public_report_router, get_read_public_report_use_case, stub)) as c:
        return await c.get("/v1/public/report", headers=headers)


async def test_헤더의_토큰으로_알림장을_읽는다_로그인은_없다():
    stub = Recorder(_view())
    response = await _get(stub, {"X-Report-Token": TOKEN})
    assert (response.status_code, response.json()) == (200, FULL)
    assert (stub.calls[0].token, stub.calls[0].client) == (TOKEN, "127.0.0.1")


async def test_검색과_캐시를_막는_헤더를_단다():
    response = await _get(Recorder(_view()), {"X-Report-Token": TOKEN})
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


@pytest.mark.parametrize(("off", "missing"), [
    ({"show_menus": False}, {"menus"}),
    ({"show_amount": False}, {"total_amount"}),
    ({"show_weight": False}, {"weight_kg"}),
    ({"show_shop_info": False}, {"shop"}),
    ({"show_menus": False, "show_amount": False, "show_weight": False, "show_shop_info": False},
     {"menus", "total_amount", "weight_kg", "shop"}),
], ids=["메뉴", "금액", "몸무게", "매장 정보", "전부"])
async def test_끈_항목은_칸이_아예_없다(off, missing):
    """R7"""
    body = (await _get(Recorder(_view(**off)), {"X-Report-Token": TOKEN})).json()
    assert set(FULL) - set(body) == missing
    assert {k: v for k, v in body.items() if k != "menus"} == {
        k: v for k, v in FULL.items() if k not in missing | {"menus"}}


async def test_금액을_끄면_메뉴에는_이름만_있다():
    body = (await _get(Recorder(_view(show_amount=False)), {"X-Report-Token": TOKEN})).json()
    assert body["menus"] == [{"name": "목욕"}, {"name": "발톱"}]


async def test_켰지만_값이_없는_칸은_null_로_나간다():
    view = _view()
    empty = ReportView(**{**vars(view.report), "pet_name": None, "care_note": None, "media": (), "cover": None,
                          "menus": (), "total_amount": None, "weight_kg": None})
    body = (await _get(Recorder(PublicReportView(report=empty, expires_at=None)), {"X-Report-Token": TOKEN})).json()
    assert body == {
        "pet_name": None, "visit_date": "2026-09-23", "care_note": None, "media": [], "cover": None, "menus": [],
        "total_amount": None, "weight_kg": None,
        "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": None}, "expires_at": None,
    }


@pytest.mark.parametrize("headers", [
    None,
    {"X-Report-Token": ""},
    {"X-Report-Token": "a" * 42},
    {"X-Report-Token": "a" * 44},
    {"X-Report-Token": "a" * 5000},
    {"X-Report-Token": "알림장".encode()},
    {"X-Report-Token": " "},
    {"X-Report-Token": TOKEN + "="},
    {"X-Report-Token": make_token(bytes(range(16)), bytes(32))},
    {"Authorization": f"Bearer {TOKEN}"},
], ids=["헤더 없음", "빈 값", "42글자", "44글자", "5000글자", "한글", "공백", "패딩", "다른 키", "다른 헤더"])
async def test_이상한_토큰은_그대로_유스케이스에_넘기고_404_를_그대로_낸다(headers):
    """R13 — 형식 검증(422)을 두지 않는다. 판정은 유스케이스가 한다."""
    stub = Recorder(error=ReportNotFoundError("알림장을 찾을 수 없습니다."))
    response = await _get(stub, headers)
    assert error_of(response) == (404, "REPORT_NOT_FOUND")
    assert set(response.json()) == {"code", "message"}
    assert len(stub.calls) == 1


async def test_닫힌_알림장은_410_너무_잦으면_429_이고_본문은_코드와_문구뿐이다():
    for error, expected in ((ReportClosedError("닫힌 알림장입니다."), (410, "REPORT_CLOSED")),
                            (TooManyReportRequestsError("잠시 뒤에"), (429, "TOO_MANY_ATTEMPTS"))):
        response = await _get(Recorder(error=error), {"X-Report-Token": TOKEN})
        assert error_of(response) == expected
        assert set(response.json()) == {"code", "message"}


async def test_토큰을_경로나_질의로는_받지_않는다():
    stub = Recorder(_view())
    async with client(build_app(read_public_report_router, get_read_public_report_use_case, stub)) as c:
        assert (await c.get(f"/v1/public/report/{TOKEN}")).status_code == 404
        assert (await c.get(f"/v1/public/report?token={TOKEN}&x_report_token={TOKEN}")).status_code == 200
    assert [call.token for call in stub.calls] == [None]
```

`backend/apps/visit/tests/adapter/test_report_error_map.py`:

```diff
@@ -5,6 +5,7 @@ from visit.domain.errors import (
     ReportClosedError,
     ReportEmptyError,
     ReportNotFoundError,
+    TooManyReportRequestsError,
     VisitNotCompletedError,
     VisitReportSentError,
 )
@@ -16,6 +17,7 @@ from visit.domain.errors import (
     (ReportEmptyError, "REPORT_EMPTY", 422),
     (VisitNotCompletedError, "VISIT_NOT_COMPLETED", 409),
     (VisitReportSentError, "VISIT_REPORT_SENT", 409),
+    (TooManyReportRequestsError, "TOO_MANY_ATTEMPTS", 429),   # 초대 코드 시도 제한과 같은 코드
 ])
 def test_알림장_오류의_코드와_상태(error, code, status):
     assert error.code == code
```

`backend/apps/visit/tests/app/services/test_public_context.py`:

```python
from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from visit.app.services.public_context import public_context


def test_공개_조회의_컨텍스트는_권한이_비어_있고_매장의_시간대를_쓴다():
    shop = ShopProfile(shop_id=3, name="Hiss Haus", phone=None, address=None, timezone="Asia/Tokyo", open=True)
    assert public_context(shop) == ShopContext(
        shop_id=3, member_id=0, role="public", permissions=frozenset(), timezone="Asia/Tokyo")
```

`backend/apps/visit/tests/app/use_cases/test_mark_report_viewed_interactor.py`:

```python
from dataclasses import replace

import pytest

from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand
from visit.app.use_cases.mark_report_viewed_interactor import MarkReportViewedInteractor
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.tests.helpers.builders import kst
from visit.tests.helpers.public_world import CLIENT, KEY, NOW, SHOP, PublicWorld


async def _mark(world, token, now=NOW):
    interactor = MarkReportViewedInteractor(
        reports=world.reports, shops=world.shops, limiter=world.limiter, now=lambda: now, link_key=KEY)
    await interactor.mark_report_viewed(MarkReportViewedCommand(token=token, client=CLIENT))


def _viewed_at(world):
    return [r.first_viewed_at for r in world.reports.rows]


async def test_처음_연_시각을_남기고_다시_열어도_그대로다():
    """R10"""
    world = PublicWorld()
    token = await world.sent()
    await _mark(world, token)
    await _mark(world, token, now=kst(9, 25, 9))
    assert _viewed_at(world) == [NOW]


async def test_끊은_링크와_기간이_지난_링크에는_남기지_않는다():
    """R11"""
    world = PublicWorld()
    token = await world.sent(expires_at=kst(9, 24, 12))
    with pytest.raises(ReportClosedError):
        await _mark(world, token, now=kst(9, 24, 12))
    world.revoke()
    with pytest.raises(ReportClosedError):
        await _mark(world, token)
    assert (_viewed_at(world), world.reports.journal) == ([None], [("create_report", 1)])


@pytest.mark.parametrize("shop", [replace(SHOP, open=False), None], ids=["정지·폐업", "없는 매장"])
async def test_문을_닫은_매장의_알림장에는_남기지_않는다(shop):
    """R21"""
    world = PublicWorld()
    token = await world.sent()
    world.shops.shops = {1: shop} if shop else {}
    with pytest.raises(ReportClosedError):
        await _mark(world, token)
    assert _viewed_at(world) == [None]


async def test_우리가_만들지_않은_토큰은_저장소를_부르지_않고_404_다():
    world = PublicWorld()
    await world.sent()
    for token in (None, "a" * 43):
        with pytest.raises(ReportNotFoundError):
            await _mark(world, token)
    assert (world.reports.finds, _viewed_at(world), world.limiter.misses) == ([], [None], [CLIENT, CLIENT])


async def test_횟수_제한에_걸리면_남기지_않는다():
    world = PublicWorld()
    token = await world.sent()
    world.limiter.allowed = False
    with pytest.raises(TooManyReportRequestsError):
        await _mark(world, token)
    assert _viewed_at(world) == [None]
```

`backend/apps/visit/tests/app/use_cases/test_read_public_report_interactor.py`:

```python
from dataclasses import replace

import pytest

from visit.app.dtos.read_public_report_dto import ReadPublicReportQuery
from visit.app.dtos.report_view_dto import ReportShopView
from visit.app.use_cases.read_public_report_interactor import ReadPublicReportInteractor
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.domain.services.report_token import make_token
from visit.tests.helpers.public_world import CLIENT, KEY, NOW, SHOP, PublicWorld


async def _read(world, token, client=CLIENT):
    interactor = ReadPublicReportInteractor(
        reports=world.reports, records=world.records, settings=world.settings, menus=world.menus,
        directory=world.directory, library=world.library, shops=world.shops, limiter=world.limiter,
        now=lambda: NOW, link_key=KEY,
    )
    return await interactor.read_public_report(ReadPublicReportQuery(token=token, client=client))


async def test_토큰으로_알림장을_읽는다_뺀_사진은_없다():
    world = PublicWorld()
    found = await _read(world, await world.sent())
    assert (found.report.pet_name, found.report.care_note) == ("아이101", "눈물 자국")
    assert [(m.media_id, m.hidden) for m in found.report.media] == [(51, False)]
    assert found.report.shop == ReportShopView(name="Hiss Haus", phone="02-123-4567", address=None)
    assert found.expires_at.isoformat() == "2026-10-23T15:00:00+09:00"
    assert (world.limiter.hits, world.limiter.misses) == ([CLIENT], [])


async def test_날짜와_끝나는_시각은_매장_시간대로_센다():
    world = PublicWorld()
    world.shops.shops[1] = replace(SHOP, timezone="America/New_York")
    found = await _read(world, await world.sent())
    assert found.report.visit_date.isoformat() == "2026-09-23"     # 한국 14시는 뉴욕 같은 날 새벽 1시
    assert found.expires_at.isoformat() == "2026-10-23T02:00:00-04:00"


async def test_기간이_없는_링크는_끝나는_시각이_없다():
    world = PublicWorld()
    assert (await _read(world, await world.sent(expires_at=None))).expires_at is None


@pytest.mark.parametrize("token", [None, "", "a" * 43, make_token(bytes(range(16)), bytes(32))],
                         ids=["없음", "빈 값", "서명 없는 43글자", "다른 키로 서명"])
async def test_우리가_만들지_않은_토큰은_저장소를_부르지_않고_404_다(token):
    """R13 — 서명을 확인한 public_id 만 저장소에 넘긴다."""
    world = PublicWorld()
    await world.sent()
    with pytest.raises(ReportNotFoundError):
        await _read(world, token)
    assert world.reports.finds == []
    assert world.limiter.misses == [CLIENT]


async def test_서명은_맞지만_그런_링크가_없으면_404_다():
    world = PublicWorld()
    with pytest.raises(ReportNotFoundError):
        await _read(world, make_token(bytes(16), KEY))
    assert world.reports.finds == [bytes(16)]
    assert world.limiter.misses == [CLIENT]


async def test_끊은_링크는_410_이다():
    """R3"""
    world = PublicWorld()
    token = await world.sent()
    world.revoke()
    with pytest.raises(ReportClosedError):
        await _read(world, token)
    assert world.limiter.misses == []     # 닫힌 링크는 실패로 세지 않는다


async def test_기간이_지난_링크는_410_이다():
    """R3 — 끝나는 바로 그 시각에도 닫혀 있다."""
    world = PublicWorld()
    token = await world.sent(expires_at=NOW)
    with pytest.raises(ReportClosedError):
        await _read(world, token)


@pytest.mark.parametrize("shop", [replace(SHOP, open=False), None], ids=["정지·폐업", "없는 매장"])
async def test_문을_닫았거나_없는_매장의_알림장은_410_이다(shop):
    """R21"""
    world = PublicWorld()
    token = await world.sent()
    world.shops.shops = {1: shop} if shop else {}
    with pytest.raises(ReportClosedError):
        await _read(world, token)


async def test_기록이_없으면_410_이다():
    world = PublicWorld()
    token = await world.sent()
    world.records.rows.clear()
    with pytest.raises(ReportClosedError):
        await _read(world, token)


async def test_횟수_제한에_걸리면_토큰을_보지도_않고_429_다():
    """R1"""
    world = PublicWorld()
    token = await world.sent()
    world.limiter.allowed = False
    with pytest.raises(TooManyReportRequestsError):
        await _read(world, token)
    assert (world.reports.finds, world.limiter.misses) == ([], [])


async def test_알림장은_권한이_빈_컨텍스트로_읽는다():
    world = PublicWorld()
    seen = []

    async def read_urls(ctx, media_ids):
        seen.append(ctx)
        return {}

    world.library.read_urls = read_urls
    await _read(world, await world.sent())
    assert [(c.shop_id, c.member_id, c.role, c.permissions) for c in seen] == [(1, 0, "public", frozenset())]
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:

```diff
@@ -18,6 +18,7 @@ async def test_자기소개는_묶음의_경로와_권한을_적는다():
                   "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT",
                   "POST /visits/{visit_id}/record/media", "record:delete", "GET·PUT /report-settings",
                   "GET /visits/{visit_id}/report", "PUT /visits/{visit_id}/report",
-                  "DELETE /visits/{visit_id}/report", "REPORT_EMPTY", "VISIT_REPORT_SENT", "report_sent"):
+                  "DELETE /visits/{visit_id}/report", "REPORT_EMPTY", "VISIT_REPORT_SENT", "report_sent",
+                  "GET /v1/public/report", "POST /v1/public/report/viewed", "X-Report-Token"):
         assert words in result.introduction
     assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -24,6 +24,7 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.app.dtos.report_target_dto import ReportTarget
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
 from visit.app.ports.output.public_report_repository import PublicReportRepository
 from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
@@ -471,6 +472,22 @@ class FakeReportRepository(ReportRepository, PublicReportRepository):
         self.journal.append(("mark_report_viewed", report_id))
 
 
+class FakePublicReportLimiter(PublicReportLimiterPort):
+    """공개 조회 횟수 제한 스텁 — allowed 를 False 로 두면 막는다. 센 접속 주소가 hits·misses 에 남는다."""
+
+    def __init__(self) -> None:
+        self.allowed = True
+        self.hits: list[str] = []
+        self.misses: list[str] = []
+
+    async def allow(self, client):
+        self.hits.append(client)
+        return self.allowed
+
+    async def note_miss(self, client):
+        self.misses.append(client)
+
+
 class FakeReportSettingsRepository(ReportSettingsRepository):
     """rows 는 매장 ID → 설정. 없는 매장은 기본값이다."""
```

`backend/apps/visit/tests/helpers/public_world.py`:

```python
"""공개 조회 인터랙터 테스트가 함께 쓰는 무대 — 보낸 알림장 하나와 그 토큰."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hub.app.dtos.shop_profile import ShopProfile
from visit.domain.services.report_rules import hide
from visit.domain.services.report_token import make_token
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakePublicReportLimiter,
    FakeRecords,
    FakeReportRepository,
    FakeReportSettingsRepository,
    FakeShopProfile,
    FakeVisits,
)

KEY = bytes(range(32))
NOW = kst(9, 24, 10)
CLIENT = "203.0.113.7"
SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone="02-123-4567", address=None, timezone="Asia/Seoul",
                   open=True)


class _CountingReports(FakeReportRepository):
    """토큰으로 링크를 찾은 횟수를 센다 — 서명이 틀린 토큰으로는 저장소를 부르지 않는다."""

    def __init__(self, visits) -> None:
        super().__init__(visits)
        self.finds: list[bytes] = []

    async def find(self, public_id):
        self.finds.append(public_id)
        return await super().find(public_id)


class PublicWorld:
    def __init__(self) -> None:
        self.visits, self.settings = FakeVisits(), FakeReportSettingsRepository()
        self.records, self.reports = FakeRecords(self.visits), _CountingReports(self.visits)
        self.menus, self.directory, self.library = FakeMenus(), FakeDirectory(), FakeLibrary()
        self.shops, self.limiter = FakeShopProfile({1: SHOP}), FakePublicReportLimiter()
        self.directory.family(1, pets=(101,))
        for media_id in (51, 52):
            self.library.add(media_id, attached=True)

    async def sent(self, expires_at=kst(10, 23, 15)) -> str:
        """사진 둘(전 51, 후 52 — 52 는 뺐다)과 메모가 있는 완료 방문에 보낸 알림장의 토큰."""
        found = self.visits.seed(status="completed", starts_at=kst(9, 23, 14), started_at=kst(9, 23, 14))
        written = record(found.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
                         weight_kg=Decimal("3.4"), care_note="눈물 자국", internal_note="내부 메모")
        self.records.seed(replace(written, media=hide(written, (52,))))
        report = await self.reports.create(ctx(), found.id, bytes(range(16)), expires_at, kst(9, 23, 15))
        return make_token(report.public_id, KEY)

    def revoke(self) -> None:
        self.reports.rows = [replace(r, revoked_at=kst(9, 23, 16)) for r in self.reports.rows]
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -4,6 +4,7 @@ from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.shop_profile_port import ShopProfilePort
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
 from visit.app.ports.output.public_report_repository import PublicReportRepository
 from visit.app.ports.output.report_repository import ReportRepository
 from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
@@ -19,6 +20,7 @@ from visit.tests.helpers.fakes import (
     FakeDirectory,
     FakeLibrary,
     FakeMenus,
+    FakePublicReportLimiter,
     FakeRecords,
     FakeReportRepository,
     FakeReportSettingsRepository,
@@ -42,6 +44,7 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     reports = FakeReportRepository(visits)
     assert isinstance(reports, ReportRepository) and isinstance(reports, PublicReportRepository)
     assert isinstance(FakeReportSettingsRepository(), ReportSettingsRepository)
+    assert isinstance(FakePublicReportLimiter(), PublicReportLimiterPort)
 
 
 async def test_매장_공개_정보_스텁은_넣어_둔_매장만_돌려준다():
```

`backend/tests/integration/test_public_report_wiring.py`:

```python
"""로그인 없이 열리는 공개 알림장을 실제 배선(프로바이더·허브 포트 조립·DB·Redis·MinIO)으로 확인한다.

검토 기준은 하나다 — 공개하기로 한 것 말고는 아무것도 나가지 않는다.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.integration.support import bearer, error_of, make_operator, ready_photo, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
YESTERDAY = datetime.now(SEOUL).date() - timedelta(days=1)
# 어디에도 나가면 안 되는 칸에는 표식(SECRET)을 넣는다. 결제 수단은 고를 수 있는 값이 정해져 있어 그 값을 찾는다.
CUSTOMER = {"name": "SECRET보호자", "phone": "010-9876-5432", "marketing_consent": True, "memo": "SECRET-고객메모"}
PET = {"name": "콩이", "species": "dog", "breed": "SECRET품종", "sex": "female", "neutered": True,
       "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True, "memo": "SECRET-아이메모"}
LEAKS = ("SECRET", "9876", "5432", "transfer", "payment", "internal", "memo", "hidden",
         "media_id", "visit_id", "customer_id", "pet_id", "shop_id", "member")
ALL_ON = {"link_days": 30, "show_menus": True, "show_shop_info": True, "show_weight": True, "show_amount": True}
PUBLIC = "/v1/public/report"
VIEWED = "/v1/public/report/viewed"


def _token(link: dict) -> str:
    return link["url"].rsplit("/r/", 1)[1]


def _with(token: str) -> dict:
    return {"X-Report-Token": token}


async def _shop(wired, name="Hiss Haus", owner_name="사장님"):
    shop_id, owner = await shop_with_owner(wired, await make_operator(wired, f"{name} 운영자"), name, owner_name)
    return shop_id, bearer(owner["access_token"])


async def _completed_visit(wired, shop_id, headers, photos=0, phone=CUSTOMER["phone"]):
    """모든 칸을 채운 기록(후 사진 photos 장)을 남기고 완료한 콩이의 어제 방문. (방문 주소, 사진 ID 목록, 메뉴 이름)."""
    family = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                  json={"customer": {**CUSTOMER, "phone": phone}, "pet": PET})
    assert family.status_code == 201, family.text
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": family.json()["customer"]["customer_id"],
              "pet_ids": [family.json()["pets"][0]["pet_id"]], "memo": "SECRET-예약메모",
              "starts_at": datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 11, tzinfo=SEOUL).isoformat()})
    assert booked.status_code == 201, booked.text
    visit = f"/v1/shops/{shop_id}/visits/{booked.json()['visits'][0]['visit_id']}"
    media = [await ready_photo(wired, shop_id, headers) for _ in range(photos)]
    bath = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=headers)).json()["items"][0]
    for action, body in (
        ("start", None),
        ("record", {"weight_kg": 3.4, "care_note": "눈물 자국을 닦았어요", "internal_note": "SECRET-내부메모",
                    "payment_method": "transfer", "total_amount": 25000,
                    "items": [{"menu_id": bath["menu_id"], "amount": 28000}],
                    "media": [{"media_id": m, "phase": "after", "sort_order": i} for i, m in enumerate(media)]}),
        ("complete", None),
    ):
        if body is None:
            done = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                        json={"visit_ids": [booked.json()["visits"][0]["visit_id"]], "action": action})
        else:
            done = await wired.api.put(f"{visit}/record", headers=headers, json=body)
        assert done.status_code == 200, done.text
    return visit, media, bath["name"]


async def _settings(wired, shop_id, headers, **changes) -> None:
    changed = await wired.api.put(f"/v1/shops/{shop_id}/report-settings", headers=headers,
                                  json={**ALL_ON, **changes})
    assert changed.status_code == 200, changed.text


async def _send(wired, visit, headers, hidden=()) -> str:
    sent = await wired.api.put(f"{visit}/report", headers=headers, json={"hidden_media_ids": list(hidden)})
    assert sent.status_code == 200, sent.text
    return _token(sent.json()["link"])


async def test_모든_항목을_켜도_공개하기로_한_것만_나간다(wired, media_storage):
    """R6"""
    shop_id, o = await _shop(wired)
    assert (await wired.api.put(f"/v1/shops/{shop_id}/settings", headers=o,
                                json={"name": "Hiss Haus", "phone": "02-123-4567", "address": "서울 어딘가"})
            ).status_code == 200
    visit, [shown, removed], bath = await _completed_visit(wired, shop_id, o, photos=2)
    await _settings(wired, shop_id, o)
    token = await _send(wired, visit, o, hidden=[removed])
    preview = (await wired.api.get(f"{visit}/report", headers=o)).json()
    by_id = {m["media_id"]: m for m in preview["report"]["media"]}

    response = await wired.api.get(PUBLIC, headers=_with(token))

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    body = response.json()
    [media] = body.pop("media")
    assert body == {
        "pet_name": "콩이", "visit_date": YESTERDAY.isoformat(), "care_note": "눈물 자국을 닦았어요",
        "cover": {"url": media["display_url"], "width": 3000, "height": 2000},
        "menus": [{"name": bath, "amount": 28000}], "total_amount": 25000, "weight_kg": 3.4,
        "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": "서울 어딘가"},
        "expires_at": preview["link"]["expires_at"],
    }
    assert body["expires_at"].endswith("+09:00")
    assert media == {k: v for k, v in by_id[shown].items() if k not in ("media_id", "hidden")}
    assert set(media) == {"kind", "phase", "width", "height", "duration_seconds", "display_url", "thumb_url",
                          "download_url"}
    # 본문 글 전체에 — 칸 이름으로도 값으로도 — 없어야 한다.
    assert [word for word in LEAKS if word in response.text] == []
    assert token not in response.text
    # 뺀 사진은 어느 주소로도 나가지 않는다.
    for url in (by_id[removed][k] for k in ("display_url", "thumb_url", "download_url")):
        assert url.split("?")[0] not in response.text


@pytest.mark.parametrize(("off", "missing"), [
    ({"show_menus": False}, {"menus"}),
    ({"show_amount": False}, {"total_amount"}),
    ({"show_weight": False}, {"weight_kg"}),
    ({"show_shop_info": False}, {"shop"}),
], ids=["메뉴", "금액", "몸무게", "매장 정보"])
async def test_설정에서_끈_항목은_응답에_칸이_없다(wired, off, missing):
    """R7 — 이미 보낸 알림장에도 바로 적용된다."""
    shop_id, o = await _shop(wired)
    visit, _, bath = await _completed_visit(wired, shop_id, o)
    await _settings(wired, shop_id, o)
    token = await _send(wired, visit, o)
    full = (await wired.api.get(PUBLIC, headers=_with(token))).json()

    await _settings(wired, shop_id, o, **off)
    body = (await wired.api.get(PUBLIC, headers=_with(token))).json()

    assert set(full) - set(body) == missing
    if off == {"show_amount": False}:
        assert body["menus"] == [{"name": bath}]
        assert "28000" not in str(body) and "25000" not in str(body)


async def test_보내고_열고_끊고_다시_보낸다(wired):
    """R3·R4·R11"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    first = await _send(wired, visit, o)

    assert (await wired.api.get(PUBLIC, headers=_with(first))).status_code == 200
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None
    viewed = await wired.api.post(VIEWED, headers=_with(first))
    assert (viewed.status_code, viewed.content) == (204, b"")
    seen_at = (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"]
    assert seen_at is not None and seen_at.endswith("+09:00")
    assert (await wired.api.post(VIEWED, headers=_with(first))).status_code == 204
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] == seen_at

    assert (await wired.api.delete(f"{visit}/report", headers=o)).status_code == 204
    for closed in (await wired.api.get(PUBLIC, headers=_with(first)),
                   await wired.api.post(VIEWED, headers=_with(first))):
        assert error_of(closed) == (410, "REPORT_CLOSED")
        assert set(closed.json()) == {"code", "message"}
        assert [word for word in ("콩이", "Hiss", *LEAKS) if word in closed.text] == []

    second = await _send(wired, visit, o)
    assert second != first
    assert error_of(await wired.api.get(PUBLIC, headers=_with(first))) == (410, "REPORT_CLOSED")
    assert (await wired.api.get(PUBLIC, headers=_with(second))).status_code == 200
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None


async def test_기간이_지난_링크는_410_이고_열람을_남기지_않는다(wired):
    """R3·R11"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)
    await wired.execute("UPDATE visit_reports SET created_at = now() - interval '2 days', "
                        "expires_at = now() - interval '1 second'")

    assert error_of(await wired.api.get(PUBLIC, headers=_with(token))) == (410, "REPORT_CLOSED")
    assert error_of(await wired.api.post(VIEWED, headers=_with(token))) == (410, "REPORT_CLOSED")
    async with wired.engine.connect() as conn:
        assert (await conn.execute(text("SELECT first_viewed_at FROM visit_reports"))).all() == [(None,)]


@pytest.mark.parametrize("column", ["suspended_at", "closed_at"])
async def test_정지하거나_폐업한_매장의_알림장은_410_이고_풀리면_다시_열린다(wired, column):
    """R21"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    await wired.execute(f"UPDATE shops SET {column} = now() WHERE id = :id", id=shop_id)
    closed = await wired.api.get(PUBLIC, headers=_with(token))
    assert error_of(closed) == (410, "REPORT_CLOSED")
    assert "Hiss" not in closed.text
    assert error_of(await wired.api.post(VIEWED, headers=_with(token))) == (410, "REPORT_CLOSED")

    await wired.execute(f"UPDATE shops SET {column} = NULL WHERE id = :id", id=shop_id)
    assert (await wired.api.get(PUBLIC, headers=_with(token))).status_code == 200
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None


async def test_고객을_삭제하면_그_고객의_알림장은_410_이다(wired):
    """R19"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)
    customer_id = (await wired.api.get(visit, headers=o)).json()["visit"]["customer"]["customer_id"]
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204

    assert error_of(await wired.api.get(PUBLIC, headers=_with(token))) == (410, "REPORT_CLOSED")
    assert error_of(await wired.api.post(VIEWED, headers=_with(token))) == (410, "REPORT_CLOSED")


async def test_다른_매장의_알림장과_섞이지_않는다(wired):
    a_shop, a = await _shop(wired, "A 매장", "A사장")
    b_shop, b = await _shop(wired, "B 매장", "B사장")
    a_visit, _, _ = await _completed_visit(wired, a_shop, a)
    b_visit, _, _ = await _completed_visit(wired, b_shop, b)
    assert (await wired.api.put(f"{b_visit}/record", headers=b,
                                json={"version": 1, "care_note": "B 매장의 메모"})).status_code == 200
    a_token, b_token = await _send(wired, a_visit, a), await _send(wired, b_visit, b)

    seen = [(await wired.api.get(PUBLIC, headers=_with(t))).json() for t in (a_token, b_token)]
    assert [(s["shop"]["name"], s["care_note"]) for s in seen] == [
        ("A 매장", "눈물 자국을 닦았어요"), ("B 매장", "B 매장의 메모")]


@pytest.mark.parametrize("headers", [
    {}, {"X-Report-Token": ""}, {"X-Report-Token": "a" * 42}, {"X-Report-Token": "a" * 44},
    {"X-Report-Token": "a" * 5000}, {"X-Report-Token": "알림장".encode()}, {"X-Report-Token": " "},
    {"X-Report-Token": "a" * 43},
], ids=["헤더 없음", "빈 값", "42글자", "44글자", "5000글자", "한글", "공백", "서명 없는 43글자"])
async def test_이상한_토큰은_404_다(wired, headers):
    """R13"""
    for response in (await wired.api.get(PUBLIC, headers=headers), await wired.api.post(VIEWED, headers=headers)):
        assert error_of(response) == (404, "REPORT_NOT_FOUND")
        assert set(response.json()) == {"code", "message"}


async def test_패딩을_붙이거나_다른_키로_서명한_토큰은_404_다(wired):
    """R13"""
    from core.config import REPORT_LINK_KEY
    from visit.domain.services.report_token import make_token, read_token

    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)
    forged = make_token(read_token(token, REPORT_LINK_KEY), bytes(32))

    for wrong in (token + "=", forged, token[:-1], token.swapcase()):
        assert error_of(await wired.api.get(PUBLIC, headers=_with(wrong))) == (404, "REPORT_NOT_FOUND")
    assert (await wired.api.get(PUBLIC, headers=_with(token))).status_code == 200


async def test_로그인_토큰은_공개_조회에_아무_뜻이_없다(wired):
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    assert error_of(await wired.api.get(PUBLIC, headers=o)) == (404, "REPORT_NOT_FOUND")
    broken = {"Authorization": "Bearer 깨진토큰".encode(), "X-Report-Token": token}
    assert (await wired.api.get(PUBLIC, headers=broken)).status_code == 200


async def test_1분에_61번째_요청부터_429_다(wired):
    """R1"""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    codes = [(await wired.api.get(PUBLIC, headers=_with(token))).status_code for _ in range(61)]
    assert codes == [200] * 60 + [429]
    blocked = await wired.api.post(VIEWED, headers=_with(token))
    assert error_of(blocked) == (429, "TOO_MANY_ATTEMPTS")
    assert set(blocked.json()) == {"code", "message"}
    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] is None


async def test_실패가_20번이면_맞는_토큰도_429_이고_접속_주소_헤더를_바꿔도_피하지_못한다(wired, monkeypatch):
    """R1·R17 — 비밀값 없이 보낸 X-Report-Client-IP 는 믿지 않는다. 모두 연결된 주소 하나로 센다."""
    from visit.dependencies import public_client

    monkeypatch.setattr(public_client, "REPORT_WEB_SECRET", "web-secret-for-test")
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    token = await _send(wired, visit, o)

    async def guess(n, secret):
        return (await wired.api.get(PUBLIC, headers={
            "X-Report-Token": "a" * 43, "X-Report-Client-IP": f"203.0.113.{n}", "X-Report-Web-Secret": secret,
        })).status_code

    assert [await guess(n, "틀린-비밀값".encode()) for n in range(21)] == [404] * 20 + [429]
    assert error_of(await wired.api.get(PUBLIC, headers=_with(token))) == (429, "TOO_MANY_ATTEMPTS")
    # 비밀값이 맞으면 웹 서버가 알려 준 주소로 센다 — 막힌 것은 연결된 주소뿐이다.
    assert (await wired.api.get(PUBLIC, headers={
        **_with(token), "X-Report-Client-IP": "198.51.100.9", "X-Report-Web-Secret": "web-secret-for-test",
    })).status_code == 200
    assert [await guess(n, "web-secret-for-test") for n in range(21)] == [404] * 21


async def test_공개_조회는_토큰을_로그에_남기지_않는다(wired, caplog):
    """R18 — 성공·404·410·429 를 모두 지난 뒤 잡힌 로그 전체를 본다."""
    shop_id, o = await _shop(wired)
    visit, _, _ = await _completed_visit(wired, shop_id, o)
    live = await _send(wired, visit, o)
    closed_visit, _, _ = await _completed_visit(wired, shop_id, o, phone="010-2222-3333")
    closed = await _send(wired, closed_visit, o)
    assert (await wired.api.delete(f"{closed_visit}/report", headers=o)).status_code == 204
    wrong = live.swapcase()

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        seen = [(await wired.api.get(PUBLIC, headers=_with(t))).status_code for t in (live, wrong, closed)]
        seen += [(await wired.api.post(VIEWED, headers=_with(t))).status_code for t in (live, wrong, closed)]
        for _ in range(60):
            last = await wired.api.get(PUBLIC, headers=_with(live))
        logging.getLogger("tests.public_report").debug("로그가 잡히는지 확인하는 줄")

    assert (seen, last.status_code) == ([200, 404, 410, 204, 404, 410], 429)
    assert "로그가 잡히는지 확인하는 줄" in caplog.text
    logged = caplog.text + "".join(repr(r.args) for r in caplog.records)
    assert [t for t in (live, wrong, closed) if t in logged] == []
```

`backend/tests/integration/test_route_wiring.py`:

```diff
@@ -5,7 +5,7 @@ auth_main 은 import 시점에 JWT 개인키를 요구하므로 키를 넣어 
 import pytest
 
 from auth.dependencies.recent_login_guard import require_recent_login
-from tests.route_inspection import find_route_violations, routes_calling
+from tests.route_inspection import find_route_violations, routes_calling, routes_without_login
 
 pytestmark = pytest.mark.integration
 
@@ -25,3 +25,16 @@ async def test_연결_해제_탈퇴는_실제로_최근_로그인_가드를_거
         "DELETE /v1/auth/identities/{provider}",
         "DELETE /v1/auth/account",
     }
+
+
+async def test_인증_프로세스에서_로그인_없이_열리는_경로는_다섯뿐이다(wired):
+    """로그인 자체와 토큰 갱신·로그아웃(리프레시 토큰으로 확인한다), 상태 확인, 자기소개. 공개 경로는 없다."""
+    import auth_main
+
+    assert routes_without_login(auth_main.app) == {
+        "GET /v1/auth/health",
+        "GET /v1/auth/myself",
+        "POST /v1/auth/social",
+        "POST /v1/auth/refresh",
+        "POST /v1/auth/logout",
+    }
```

`backend/tests/route_inspection.py`:

```diff
@@ -13,11 +13,16 @@ from fastapi.dependencies.models import Dependant
 from fastapi.routing import APIRoute, iter_route_contexts
 
 from auth.dependencies.recent_login_guard import require_recent_login
+from core.security import get_access_claims, get_current_user_id
 from core.shop_guard import get_shop_access_port, get_shop_context
 from platform_admin.dependencies.operator_guard import require_operator
 
 # 계정을 빼앗는 데 쓰일 수 있는 경로. 새로 더하는 민감 경로도 여기에 적는다.
 _RECENT_LOGIN_PREFIXES = ("/v1/auth/identities", "/v1/auth/account")
+# 로그인 없이 여는 공개 표면(/v1/public/). 여기에 적지 않은 공개 경로는 위반이다.
+_PUBLIC_ROUTES = {"GET /v1/public/report", "POST /v1/public/report/viewed"}
+# 로그인한 사용자를 읽는 의존성. require_recent_login 도 get_access_claims 위에 선다.
+_LOGIN = {get_access_claims, get_current_user_id}
 
 
 def _is_slot(call: Any) -> bool:
@@ -42,6 +47,19 @@ def routes_calling(app: FastAPI, dependency: Any) -> set[str]:
     return found
 
 
+def _names(ctx) -> set[str]:
+    return {f"{method} {ctx.path}" for method in ctx.original_route.methods}
+
+
+def routes_without_login(app: FastAPI) -> set[str]:
+    """로그인 의존성을 거치지 않는 경로를 "METHOD path" 로 돌려준다. 프로세스마다 테스트가 목록을 못 박는다."""
+    found = set()
+    for ctx in iter_route_contexts(app.routes):
+        if isinstance(ctx.original_route, APIRoute) and not _LOGIN & set(_calls(ctx.dependant)):
+            found.update(_names(ctx))
+    return found
+
+
 def find_route_violations(app: FastAPI) -> list[str]:
     """위반을 사람이 읽을 수 있는 줄로 돌려준다. 빈 목록이면 문제가 없다."""
     violations = []
@@ -58,4 +76,9 @@ def find_route_violations(app: FastAPI) -> list[str]:
             violations.append(f"{path}: 운영자 표면인데 require_operator 를 거치지 않는다")
         if path.startswith(_RECENT_LOGIN_PREFIXES) and require_recent_login not in calls:
             violations.append(f"{path}: 민감한 계정 경로인데 require_recent_login 을 거치지 않는다")
+        if path.startswith("/v1/public/"):
+            if not _names(ctx) <= _PUBLIC_ROUTES:
+                violations.append(f"{path}: 공개 경로인데 허용 목록에 없다")
+            if calls & (_LOGIN | {get_shop_context}):
+                violations.append(f"{path}: 공개 경로인데 로그인이나 매장 확인을 거친다")
     return sorted(violations)
```

`backend/tests/test_hub_port_binding.py`:

```diff
@@ -6,7 +6,9 @@ import main
 from core.shop_guard import get_shop_access_port
 from tenancy.dependencies.hub_ports import get_user_directory
 from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
-from tests.route_inspection import find_route_violations
+from core.security import get_current_user_id
+from core.shop_guard import get_shop_context
+from tests.route_inspection import find_route_violations, routes_without_login
 from visit.dependencies.hub_ports import get_shop_profile
 
 
@@ -14,8 +16,17 @@ def test_API_프로세스에는_빈_자리도_빠진_가드도_없다():
     assert find_route_violations(main.app) == []
 
 
+def test_API_프로세스에서_로그인_없이_열리는_경로는_넷뿐이다():
+    """여기에 경로를 더하는 것은 로그인 없는 표면을 넓히는 일이다 — 공개 경로면 route_inspection 의 허용 목록에도 적는다."""
+    assert routes_without_login(main.app) == {
+        "GET /health",
+        "GET /v1/shops/myself",
+        "GET /v1/public/report",
+        "POST /v1/public/report/viewed",
+    }
+
+
 def test_매장_공개_정보_자리는_tenancy_의_구현으로_채운다():
-    """쓰는 라우트가 아직 없어 위의 검사에는 걸리지 않는다."""
     assert main.app.dependency_overrides[get_shop_profile] is get_shop_profile_use_case
     with pytest.raises(RuntimeError):
         get_shop_profile()
@@ -56,3 +67,35 @@ def test_get_shop_context_를_거치지_않는_매장_범위_경로를_잡는다
 def test_require_operator_를_거치지_않는_운영자_경로를_잡는다():
     violations = find_route_violations(_app_with("/v1/platform/thing"))
     assert violations == ["/v1/platform/thing: 운영자 표면인데 require_operator 를 거치지 않는다"]
+
+
+def test_허용_목록에_없는_공개_경로를_잡는다():
+    violations = find_route_violations(_app_with("/v1/public/thing"))
+    assert violations == ["/v1/public/thing: 공개 경로인데 허용 목록에 없다"]
+
+
+def test_허용_목록의_경로라도_메서드가_다르면_잡는다():
+    app = FastAPI()
+
+    @app.post("/v1/public/report")
+    async def route() -> dict:
+        return {}
+
+    assert find_route_violations(app) == ["/v1/public/report: 공개 경로인데 허용 목록에 없다"]
+
+
+@pytest.mark.parametrize("dependency", [get_current_user_id, get_shop_context])
+def test_로그인이나_매장_확인을_거치는_공개_경로를_잡는다(dependency):
+    app = _app_with("/v1/public/report", dependency)
+    app.dependency_overrides[get_shop_access_port] = lambda: None
+    assert find_route_violations(app) == ["/v1/public/report: 공개 경로인데 로그인이나 매장 확인을 거친다"]
+
+
+def test_로그인_없이_열리는_경로를_센다():
+    app = _app_with("/v1/thing", get_current_user_id)
+
+    @app.post("/v1/open")
+    async def route() -> dict:
+        return {}
+
+    assert routes_without_login(app) == {"POST /v1/open"}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

```
docker compose run --rm --no-deps backend pytest apps/visit/tests tests/test_hub_port_binding.py -q -p no:cacheprovider -m "not integration and not network"
!!!!!!!!!!!!!!!!!!! Interrupted: 46 errors during collection !!!!!!!!!!!!!!!!!!!
75 deselected, 46 errors in 1.59s
```
공용 스텁(`fakes.py`)이 아직 없는 포트 모듈을 import 해서 스텁을 쓰는 테스트 파일이 모두 수집에서 떨어졌다. 출력의 끝(파일 이름 목록)만 봤고 오류 줄(`ModuleNotFoundError`) 자체는 확인하지 않았다. 통합 테스트의 RED 는 따로 돌리지 않았다(구현 뒤에 썼다 — 7절 1번).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/adapter/inbound/api/error_map.py`:

```diff
@@ -12,6 +12,7 @@ from visit.domain.errors import (
     ReportClosedError,
     ReportEmptyError,
     ReportNotFoundError,
+    TooManyReportRequestsError,
     VisitCrossesMidnightError,
     VisitDuplicateError,
     VisitGroupMismatchError,
@@ -47,4 +48,5 @@ VISIT_ERROR_STATUS: dict[type[Exception], int] = {
     ReportEmptyError: 422,
     VisitNotCompletedError: 409,
     VisitReportSentError: 409,
+    TooManyReportRequestsError: 429,
 }
```

`backend/apps/visit/adapter/inbound/api/schemas/public_report_schema.py`:

```python
"""보호자에게 나가는 알림장 응답(설계 6.3). 매장용 스키마를 쓰지 않고 칸을 하나하나 적는다.

내부 메모·결제 수단·예약 메모·보호자 이름·전화번호와 방문·고객·반려동물·미디어·매장의 ID 는 칸이 없다.
새 칸을 더하는 것은 공개 범위를 넓히는 일이다.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from visit.app.dtos.read_public_report_dto import PublicReportView
from visit.domain.value_objects.report_settings import ReportSettings

# 끊은 링크가 중간 캐시에 남지 않게, 검색 로봇이 담아 가지 않게.
PUBLIC_REPORT_HEADERS = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow"}


class _Public(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PublicMediaSchema(_Public):
    kind: str                 # photo · video
    phase: str                # before · after
    width: int
    height: int
    duration_seconds: int | None
    display_url: str          # 사진은 표시용, 영상은 원본(재생용)
    thumb_url: str            # 영상이면 포스터
    download_url: str


class PublicCoverSchema(_Public):
    url: str
    width: int
    height: int


class PublicMenuSchema(_Public):
    name: str
    amount: int | None = None        # 금액을 켰을 때만 있다


class PublicShopSchema(_Public):
    name: str
    phone: str | None
    address: str | None


class PublicReportSchema(_Public):
    pet_name: str | None             # 보호자만의 방문이면 null
    visit_date: date                 # 매장 시간대의 날짜
    care_note: str | None
    media: list[PublicMediaSchema]   # 후 → 전, 그 안에서 순서대로. 뺀 것은 없다
    cover: PublicCoverSchema | None
    menus: list[PublicMenuSchema] | None = None     # 메뉴를 켰을 때만 있다
    total_amount: int | None = None                 # 금액을 켰을 때만 있다
    weight_kg: float | None = None                  # 몸무게를 켰을 때만 있다
    shop: PublicShopSchema | None = None            # 매장 정보를 켰을 때만 있다
    expires_at: datetime | None      # 매장 시간대. null 이면 기간이 없다

    @classmethod
    def body(cls, view: PublicReportView) -> dict:
        """응답 본문. 끈 항목은 null 이 아니라 칸이 없고, 켰지만 값이 없는 칸은 null 이다."""
        report = view.report
        schema = cls(
            pet_name=report.pet_name, visit_date=report.visit_date, care_note=report.care_note,
            media=list(report.media), cover=report.cover, menus=report.menus, total_amount=report.total_amount,
            weight_kg=report.weight_kg, shop=report.shop, expires_at=view.expires_at,
        )
        return schema.model_dump(mode="json", exclude=_turned_off(report.settings))


def _turned_off(settings: ReportSettings) -> dict:
    """매장이 끈 칸 — model_dump 의 exclude 모양."""
    off: dict = {}
    if not settings.show_menus:
        off["menus"] = True
    elif not settings.show_amount:
        off["menus"] = {"__all__": {"amount"}}
    if not settings.show_amount:
        off["total_amount"] = True
    if not settings.show_weight:
        off["weight_kg"] = True
    if not settings.show_shop_info:
        off["shop"] = True
    return off
```

`backend/apps/visit/adapter/inbound/api/v1/mark_report_viewed_router.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from visit.adapter.inbound.api.schemas.public_report_schema import PUBLIC_REPORT_HEADERS
from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand
from visit.app.ports.input.mark_report_viewed_use_case import MarkReportViewedUseCase
from visit.dependencies.mark_report_viewed_provider import get_mark_report_viewed_use_case
from visit.dependencies.public_client import get_public_client

mark_report_viewed_router = APIRouter(prefix="/v1/public", tags=["public"])


# 로그인이 없다. 보호자의 브라우저가 알림장을 열었을 때 웹 서버를 거쳐 온다(미리보기 로봇은 보내지 않는다).
@mark_report_viewed_router.post("/report/viewed", status_code=204)
async def mark_report_viewed(
    x_report_token: Annotated[str | None, Header()] = None,
    client: str = Depends(get_public_client),
    use_case: MarkReportViewedUseCase = Depends(get_mark_report_viewed_use_case),
) -> Response:
    await use_case.mark_report_viewed(MarkReportViewedCommand(token=x_report_token, client=client))
    return Response(status_code=204, headers=PUBLIC_REPORT_HEADERS)
```

`backend/apps/visit/adapter/inbound/api/v1/read_public_report_router.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from visit.adapter.inbound.api.schemas.public_report_schema import PUBLIC_REPORT_HEADERS, PublicReportSchema
from visit.app.dtos.read_public_report_dto import ReadPublicReportQuery
from visit.app.ports.input.read_public_report_use_case import ReadPublicReportUseCase
from visit.dependencies.public_client import get_public_client
from visit.dependencies.read_public_report_provider import get_read_public_report_use_case

read_public_report_router = APIRouter(prefix="/v1/public", tags=["public"])


# 로그인이 없다. 토큰은 헤더로만 받는다 — 경로·질의에 두면 접속 기록에 남는다.
# 헤더가 없거나 이상해도 422 가 아니라 404 다(유스케이스가 판정한다) — 그래서 선택 값으로 받는다.
@read_public_report_router.get("/report", response_model=PublicReportSchema)
async def read_public_report(
    x_report_token: Annotated[str | None, Header()] = None,
    client: str = Depends(get_public_client),
    use_case: ReadPublicReportUseCase = Depends(get_read_public_report_use_case),
) -> JSONResponse:
    view = await use_case.read_public_report(ReadPublicReportQuery(token=x_report_token, client=client))
    return JSONResponse(PublicReportSchema.body(view), headers=PUBLIC_REPORT_HEADERS)
```

`backend/apps/visit/adapter/outbound/redis/__init__.py`:

```python

```

`backend/apps/visit/adapter/outbound/redis/public_report_redis_limiter.py`:

```python
from __future__ import annotations

import hashlib
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort

_HITS_PER_WINDOW = 60
_HIT_WINDOW_SECONDS = 60
_MISSES_PER_WINDOW = 20
_MISS_WINDOW_SECONDS = 600

logger = logging.getLogger(__name__)


def _keys(client: str) -> tuple[str, str]:
    """접속 주소는 헤더로 들어온 값일 수 있어 그대로 키에 넣지 않는다 — 길이가 정해진 해시로 바꾼다."""
    digest = hashlib.sha256(client.encode()).hexdigest()[:32]
    return f"visit:report-hits:{digest}", f"visit:report-misses:{digest}"


class PublicReportRedisLimiter(PublicReportLimiterPort):
    """키: visit:report-hits:{주소 해시} → 이번 1분 창의 요청 수, visit:report-misses:{주소 해시} → 이번 10분 창의 실패 수."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, client: str) -> bool:
        hits, misses = _keys(client)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(hits)
                pipe.expire(hits, _HIT_WINDOW_SECONDS, nx=True)  # 창은 처음 셀 때만 잡는다
                pipe.get(misses)
                count, _, missed = await pipe.execute()
        except RedisError:
            logger.warning("알림장 횟수 제한을 건너뜁니다 — Redis 에 닿지 못했습니다.")
            return True
        return int(count) <= _HITS_PER_WINDOW and int(missed or 0) < _MISSES_PER_WINDOW

    async def note_miss(self, client: str) -> None:
        _, misses = _keys(client)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(misses)
                pipe.expire(misses, _MISS_WINDOW_SECONDS, nx=True)
                await pipe.execute()
        except RedisError:
            logger.warning("알림장 조회 실패를 세지 못했습니다 — Redis 에 닿지 못했습니다.")
```

`backend/apps/visit/app/dtos/mark_report_viewed_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkReportViewedCommand:
    token: str | None     # X-Report-Token 헤더 그대로
    client: str           # 횟수를 셀 접속 주소
```

`backend/apps/visit/app/dtos/read_public_report_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from visit.app.dtos.report_view_dto import ReportView


@dataclass(frozen=True)
class ReadPublicReportQuery:
    token: str | None     # X-Report-Token 헤더 그대로. 없거나 이상해도 받는다 — 판정은 유스케이스가 한다
    client: str           # 횟수를 셀 접속 주소


@dataclass(frozen=True)
class PublicReportView:
    report: ReportView              # 뺀 사진·영상은 없다
    expires_at: datetime | None     # 링크가 닫히는 시각(매장 시간대). None 이면 기간이 없다
```

`backend/apps/visit/app/ports/input/mark_report_viewed_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand


class MarkReportViewedUseCase(ABC):
    @abstractmethod
    async def mark_report_viewed(self, command: MarkReportViewedCommand) -> None: ...
```

`backend/apps/visit/app/ports/input/read_public_report_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.read_public_report_dto import PublicReportView, ReadPublicReportQuery


class ReadPublicReportUseCase(ABC):
    @abstractmethod
    async def read_public_report(self, query: ReadPublicReportQuery) -> PublicReportView: ...
```

`backend/apps/visit/app/ports/output/public_report_limiter_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class PublicReportLimiterPort(ABC):
    """공개 조회의 횟수 제한(설계 7.1). client 는 접속 주소다.

    저장소에 닿지 못하면 막지 않는다 — 1차 방어는 토큰의 크기다.
    """

    @abstractmethod
    async def allow(self, client: str) -> bool:
        """요청 하나를 세고 받아도 되는지 알려 준다. 1분에 60번을 넘었거나 10분 안의 실패가 20번이면 False."""

    @abstractmethod
    async def note_miss(self, client: str) -> None:
        """없는 알림장을 찾은 요청(404)을 하나 센다."""
```

`backend/apps/visit/app/services/public_context.py`:

```python
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile


def public_context(shop: ShopProfile) -> ShopContext:
    """로그인이 없는 공개 조회가 쓰는 매장 컨텍스트. 권한이 비어 있고 읽기에만 쓴다.

    멤버가 없어 member_id 는 0 이다. 매장은 서명을 확인한 토큰의 링크에서 읽은 것이어야 한다.
    """
    return ShopContext(
        shop_id=shop.shop_id, member_id=0, role="public", permissions=frozenset(), timezone=shop.timezone)
```

`backend/apps/visit/app/services/public_report_gate.py`:

```python
"""공개 조회의 관문 — 토큰이 가리키는 살아 있는 링크와 영업 중인 매장. 조회와 열람 신호가 함께 쓴다.

닫힌 이유(끊음·기간 지남·매장 정지)는 가르지 않고 오류에 방문·매장의 값을 싣지 않는다(설계 6.3).
"""
from __future__ import annotations

from datetime import datetime

from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.report_target_dto import ReportTarget
from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.domain.services.report_token import read_token


async def open_report(
    token: str | None, client: str, now: datetime, *, link_key: bytes, reports: PublicReportRepository,
    shops: ShopProfilePort, limiter: PublicReportLimiterPort,
) -> tuple[ReportTarget, ShopProfile]:
    if not await limiter.allow(client):
        raise TooManyReportRequestsError("요청이 너무 잦습니다. 잠시 뒤에 다시 열어 주세요.")
    # 서명을 확인한 public_id 로만 DB 를 읽는다.
    public_id = read_token(token, link_key)
    target = await reports.find(public_id) if public_id is not None else None
    if target is None:
        await limiter.note_miss(client)
        raise ReportNotFoundError("알림장을 찾을 수 없습니다.")
    if not target.report.is_live(now):
        raise ReportClosedError("닫힌 알림장입니다.")
    shop = await shops.public_profile(target.shop_id)
    if shop is None or not shop.open:
        raise ReportClosedError("닫힌 알림장입니다.")
    return target, shop
```

`backend/apps/visit/app/use_cases/mark_report_viewed_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand
from visit.app.ports.input.mark_report_viewed_use_case import MarkReportViewedUseCase
from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.services.public_report_gate import open_report


class MarkReportViewedInteractor(MarkReportViewedUseCase):
    """보호자가 알림장을 처음 연 시각을 남긴다. 닫힌 링크에는 남기지 않는다(설계 7.5 R11).

    잠그지 않는다 — 저장소의 조건부 UPDATE 한 줄이 처음 한 번만 적는다(R10).
    """

    def __init__(
        self, reports: PublicReportRepository, shops: ShopProfilePort, limiter: PublicReportLimiterPort,
        now: Callable[[], datetime], link_key: bytes,
    ) -> None:
        self._reports = reports
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._link_key = link_key

    async def mark_report_viewed(self, command: MarkReportViewedCommand) -> None:
        now = self._now()
        target, _ = await open_report(
            command.token, command.client, now, link_key=self._link_key, reports=self._reports,
            shops=self._shops, limiter=self._limiter,
        )
        await self._reports.mark_viewed(target.report.id, now)
```

`backend/apps/visit/app/use_cases/read_public_report_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.read_public_report_dto import PublicReportView, ReadPublicReportQuery
from visit.app.ports.input.read_public_report_use_case import ReadPublicReportUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.public_context import public_context
from visit.app.services.public_report_gate import open_report
from visit.app.services.report_reader import describe_report
from visit.domain.errors import ReportClosedError


class ReadPublicReportInteractor(ReadPublicReportUseCase):
    """보호자가 링크로 알림장을 읽는다. 로그인이 없다 — 토큰의 서명이 곧 범위다. 읽기만 하므로 잠그지 않는다."""

    def __init__(
        self, reports: PublicReportRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
        menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort, shops: ShopProfilePort,
        limiter: PublicReportLimiterPort, now: Callable[[], datetime], link_key: bytes,
    ) -> None:
        self._reports = reports
        self._records = records
        self._settings = settings
        self._menus = menus
        self._directory = directory
        self._library = library
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._link_key = link_key

    async def read_public_report(self, query: ReadPublicReportQuery) -> PublicReportView:
        target, shop = await open_report(
            query.token, query.client, self._now(), link_key=self._link_key, reports=self._reports,
            shops=self._shops, limiter=self._limiter,
        )
        ctx = public_context(shop)
        record = await self._records.get(ctx, target.visit.id)
        if record is None:
            raise ReportClosedError("닫힌 알림장입니다.")
        report = await describe_report(
            ctx, target.visit, record, await self._settings.get(ctx), shop, self._menus, self._directory,
            self._library, include_hidden=False,
        )
        expires_at = target.report.expires_at
        return PublicReportView(
            report=report, expires_at=expires_at.astimezone(ZoneInfo(ctx.timezone)) if expires_at else None)
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -56,6 +56,9 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "알림장을 보낸 방문은 되돌리거나 기록을 지울 수 없습니다(409 VISIT_REPORT_SENT — 링크를 먼저 끊습니다). "
                 "방문 상세는 report(링크 상태), 하루 목록과 피드는 항목마다 report_sent 를 주고, 고객을 삭제하면 "
                 "그 고객의 링크가 끊깁니다. "
+                "보호자는 로그인 없이 GET /v1/public/report 로 알림장을 읽고 POST /v1/public/report/viewed 로 처음 연 "
+                "시각을 남깁니다(토큰은 X-Report-Token 헤더, 끈 항목은 칸이 없음, 틀린 토큰 404 REPORT_NOT_FOUND, "
+                "닫힌 링크 410 REPORT_CLOSED, 너무 잦으면 429 TOO_MANY_ATTEMPTS). "
                 "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴·알림장 설정 수정은 shop:update(사장)가 필요합니다. "
                 "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                 "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
```

`backend/apps/visit/dependencies/mark_report_viewed_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY
from core.database import DbSession
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.mark_report_viewed_use_case import MarkReportViewedUseCase
from visit.app.use_cases.mark_report_viewed_interactor import MarkReportViewedInteractor
from visit.dependencies.hub_ports import get_shop_profile
from visit.dependencies.visit_wiring import build_public_report_limiter, build_report_repository
from visit.domain.services.visit_schedule import utc_now


def get_mark_report_viewed_use_case(
    db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile)
) -> MarkReportViewedUseCase:
    return MarkReportViewedInteractor(
        reports=build_report_repository(db), shops=shops, limiter=build_public_report_limiter(), now=utc_now,
        link_key=REPORT_LINK_KEY,
    )
```

`backend/apps/visit/dependencies/public_client.py`:

```python
"""공개 조회의 횟수를 셀 접속 주소(설계 7.1, 7.5 R17).

백엔드에 붙는 상대는 보호자가 아니라 웹 서버다. 웹 서버가 알려 준 보호자의 주소는 나눈 비밀값이 맞을 때만 믿는다.
비밀값이 없는 요청도 받는다 — 연결된 주소로 셀 뿐이다.
"""
from __future__ import annotations

import hmac

from fastapi import Request

from core.config import REPORT_WEB_SECRET


def get_public_client(request: Request) -> str:
    secret = request.headers.get("x-report-web-secret", "")
    forwarded = request.headers.get("x-report-client-ip", "")
    # 설정이 비어 있으면 빈 비밀값끼리 같아지지 않게 늘 믿지 않는다.
    if REPORT_WEB_SECRET and forwarded and hmac.compare_digest(secret.encode(), REPORT_WEB_SECRET.encode()):
        return forwarded
    return request.client.host if request.client else "unknown"
```

`backend/apps/visit/dependencies/read_public_report_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY
from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.read_public_report_use_case import ReadPublicReportUseCase
from visit.app.use_cases.read_public_report_interactor import ReadPublicReportInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library, get_shop_profile
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_public_report_limiter,
    build_record_repository,
    build_report_repository,
    build_report_settings_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_read_public_report_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> ReadPublicReportUseCase:
    return ReadPublicReportInteractor(
        reports=build_report_repository(db), records=build_record_repository(db),
        settings=build_report_settings_repository(db), menus=build_menu_repository(db), directory=directory,
        library=library, shops=shops, limiter=build_public_report_limiter(), now=utc_now,
        link_key=REPORT_LINK_KEY,
    )
```

`backend/apps/visit/dependencies/visit_wiring.py`:

```diff
@@ -3,13 +3,16 @@ from __future__ import annotations
 
 from sqlalchemy.ext.asyncio import AsyncSession
 
+from core.redis import get_redis
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
 from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
+from visit.adapter.outbound.redis.public_report_redis_limiter import PublicReportRedisLimiter
 from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
 from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
@@ -39,3 +42,7 @@ def build_report_repository(db: AsyncSession) -> ReportPgRepository:
 
 def build_report_settings_repository(db: AsyncSession) -> ReportSettingsRepository:
     return ReportSettingsPgRepository(db)
+
+
+def build_public_report_limiter() -> PublicReportLimiterPort:
+    return PublicReportRedisLimiter(get_redis())
```

`backend/apps/visit/domain/errors.py`:

```diff
@@ -128,3 +128,9 @@ class VisitReportSentError(VisitError):
     """살아 있는 알림장 링크가 있는 방문은 되돌리거나 기록을 지울 수 없다 — 링크를 먼저 끊는다. 409."""
 
     code = "VISIT_REPORT_SENT"
+
+
+class TooManyReportRequestsError(VisitError):
+    """공개 알림장 조회가 너무 잦다. 코드는 초대 코드 시도 제한(tenancy)과 같다. 429."""
+
+    code = "TOO_MANY_ATTEMPTS"
```

`backend/main.py`:

```diff
@@ -83,8 +83,10 @@ from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_
 from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
 from visit.adapter.inbound.api.v1.list_visit_feed_router import list_visit_feed_router
 from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
+from visit.adapter.inbound.api.v1.mark_report_viewed_router import mark_report_viewed_router
 from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
 from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
+from visit.adapter.inbound.api.v1.read_public_report_router import read_public_report_router
 from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
 from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
 from visit.adapter.inbound.api.v1.revoke_visit_report_router import revoke_visit_report_router
@@ -174,6 +176,9 @@ app.include_router(delete_visit_record_router)
 app.include_router(get_visit_report_router)
 app.include_router(send_visit_report_router)
 app.include_router(revoke_visit_report_router)
+# 로그인 없이 열리는 경로 — 더할 때는 tests/route_inspection.py 의 허용 목록에도 적는다.
+app.include_router(read_public_report_router)
+app.include_router(mark_report_viewed_router)
 # media
 app.include_router(media_myself_router)
 app.include_router(issue_upload_router)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 묶음 | 결과 |
|---|---|
| 이 작업의 단위(`apps/visit/tests` + `tests/test_hub_port_binding.py`) | 774 passed |
| 이 작업의 통합(`test_public_report_wiring.py` 24 + `test_public_report_redis_limiter.py` 7) | 31 passed |
| 단위 전체 (커밋 amend 뒤) | **1288 passed**, 398 deselected, 1 warning (시작 1221 → +67) |
| 통합 전체 (커밋 amend 뒤, 13:15 KST) | **398 passed**, 1288 deselected, 1 warning (시작 366 → +32) |
| 구조 계약 (커밋 amend 뒤) | **6 kept, 0 broken** |
| `print_routes.py` (auth 서비스에서) | 69줄(인증 8 + API 61). 공개 경로 둘이 `backend` 에 있다 |

통합 전체에서 다른 테스트가 429 에 걸리지 않았다(전부 통과). `wired` 픽스처와 제한기 테스트의 픽스처가 테스트마다 앞뒤로 Redis db 15 를 비운다(기존 방식 그대로).

### 로그인 없이 열리는 경로 — 실제로 센 것

| 프로세스 | 경로 | 수 |
|---|---|---|
| API (`main.app`, 61 가운데) | `GET /health`, `GET /v1/shops/myself`, `GET /v1/public/report`, `POST /v1/public/report/viewed` | 4 (이 작업 전 2) |
| 인증 (`auth_main.app`, 8 가운데) | `GET /v1/auth/health`, `GET /v1/auth/myself`, `POST /v1/auth/social`, `POST /v1/auth/refresh`, `POST /v1/auth/logout` | 5 (그대로) |

두 목록은 테스트에 그대로 적혀 있고 같아야(`==`) 통과한다. 인증 프로세스도 `find_route_violations` 와 `routes_without_login` 을 둘 다 거친다(`tests/integration/test_route_wiring.py`).
`GET /v1/shops/myself`(tenancy 자기소개)가 로그인 없이 열려 있다는 것은 이번에 세면서 알았다. 기존 동작이라 건드리지 않았다.

### Redis DB 번호

개발 스택의 `REDIS_URL` 은 db **0** 이다(값의 끝자리만 확인). 테스트는 db **15**(기존 `wired` 픽스처·초대 제한기 테스트와 같다). uvicorn 확인(아래)은 db 14 를 썼다. 개발 Redis 의 키를 지우지 않았고 `FLUSHALL` 을 쓰지 않았다. `FLUSHDB` 는 기존 테스트 픽스처가 db 15 에 하는 것뿐이다.

### uvicorn 접속 로그 — 실제로 돌려 봤다

일회용 컨테이너(`docker compose run --rm -T backend python -`) 안에서 uvicorn 을 127.0.0.1:8123 에 띄우고(테스트 DB `chagocnote_test`, Redis db 14, `--log-level debug`) 우리 키로 서명한 토큰을 헤더에 실어 세 번 요청했다.

```
상태: [404, 404, 404]
토큰이 출력에 있는가: False
| INFO:     127.0.0.1:56636 - "GET /v1/public/report HTTP/1.1" 404 Not Found
| INFO:     127.0.0.1:56640 - "POST /v1/public/report/viewed HTTP/1.1" 404 Not Found
| INFO:     127.0.0.1:56646 - "GET /v1/public/report?[가림] HTTP/1.1" 404 Not Found
```
접속 로그는 연결 주소·메서드·경로·상태만 찍는다. 질의 문자열은 기존 필터가 가린다. 200 응답으로는 돌려 보지 못함(테스트 DB 에 데이터가 없다) — 찍히는 칸은 상태와 상관없이 같다. 게이트웨이(Caddy)의 접속 로그는 돌려 보지 못함.
이 확인이 Redis db 14 에 키 둘(`visit:report-hits:*` 60초, `visit:report-misses:*` 600초)을 남겼다. 스스로 사라진다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `open_report` 에서 `is_live` 검사 삭제 → 단위 `test_끊은_링크는_410_이다`, `test_기간이_지난_링크는_410_이다`, `test_끊은_링크와_기간이_지난_링크에는_남기지_않는다` / 배선 `test_보내고_열고_끊고_다시_보낸다`, `test_기간이_지난_링크는_410_이고_열람을_남기지_않는다`, `test_고객을_삭제하면_그_고객의_알림장은_410_이다`, `test_공개_조회는_토큰을_로그에_남기지_않는다` (7)
- `ReportView`·`describe_report`·공개 스키마에 `internal_note` 를 더해 채움 → 배선 `test_모든_항목을_켜도_공개하기로_한_것만_나간다` + 라우터 단위 7(`test_헤더의_토큰으로_알림장을_읽는다_로그인은_없다`, `test_끈_항목은_칸이_아예_없다` 5, `test_켰지만_값이_없는_칸은_null_로_나간다`)
- 조회 인터랙터 `include_hidden=True` → 단위 `test_토큰으로_알림장을_읽는다_뺀_사진은_없다`, 배선 `test_모든_항목을_켜도_공개하기로_한_것만_나간다`
- `get_public_client` 가 비밀값을 보지 않고 헤더를 믿음 → `test_public_client.py` 6(`test_비밀값이_틀리거나_주소가_없으면_연결된_주소다` 5, `test_비밀값을_설정하지_않았으면_빈_비밀값을_보내도_믿지_않는다`), 배선 `test_실패가_20번이면_맞는_토큰도_429_이고_접속_주소_헤더를_바꿔도_피하지_못한다`
- 열람 인터랙터가 관문을 거치지 않고 토큰으로 바로 찾음(닫힘 판정 없음) → 단위 `test_끊은_링크와_기간이_지난_링크에는_남기지_않는다`, `test_문을_닫은_매장의_알림장에는_남기지_않는다` 2, `test_횟수_제한에_걸리면_남기지_않는다` / 배선 7 (합 11)
- `not shop.open` 검사 삭제 → 단위 `test_문을_닫았거나_없는_매장의_알림장은_410_이다[정지·폐업]`, `test_문을_닫은_매장의_알림장에는_남기지_않는다[정지·폐업]`, 배선 `test_정지하거나_폐업한_매장의_알림장은_410_이고_풀리면_다시_열린다[suspended_at]`·`[closed_at]`
- `shop is None` 검사 삭제 → 위 두 단위 테스트의 `[없는 매장]`
- `_PUBLIC_ROUTES` 에서 `POST /v1/public/report/viewed` 삭제 → `test_API_프로세스에는_빈_자리도_빠진_가드도_없다`
- 조회 인터랙터가 `logger.info("알림장 조회 %s", query.token)` → 배선 `test_공개_조회는_토큰을_로그에_남기지_않는다`
- 제한기 `allow` 의 `except RedisError` 를 다른 예외로 → `test_Redis_에_닿지_못하면_통과시키고_경고를_남긴다` (9b: `note_miss` 쪽도 같은 테스트)
- **T2 에서 넘어온 것** — `read_token` 대신 서명을 보지 않고 앞 16바이트를 풀어 저장소에 넘김 → 단위 `test_우리가_만들지_않은_토큰은_저장소를_부르지_않고_404_다[서명 없는 43글자]`·`[다른 키로 서명]`(조회), 같은 이름(열람), 배선 `test_패딩을_붙이거나_다른_키로_서명한_토큰은_404_다`
- 스키마가 끈 칸을 빼지 않음(`exclude` 삭제) → 라우터 `test_끈_항목은_칸이_아예_없다` 5, `test_금액을_끄면_메뉴에는_이름만_있다`, 배선 `test_설정에서_끈_항목은_응답에_칸이_없다` 4
- 관문의 `note_miss` 삭제 → 단위 6, 배선 `test_실패가_20번이면_…`
- 관문이 `allow` 의 결과를 무시 → 단위 `test_횟수_제한에_걸리면_토큰을_보지도_않고_429_다`, `test_횟수_제한에_걸리면_남기지_않는다`, 배선 3
- `public_context` 에 권한 하나를 넣음 → `test_공개_조회의_컨텍스트는_권한이_비어_있고_매장의_시간대를_쓴다`, `test_알림장은_권한이_빈_컨텍스트로_읽는다`
- `expires_at` 을 매장 시간대로 바꾸지 않음 → 단위 2, 배선 `test_모든_항목을_켜도_…`
- 제한기가 접속 주소를 해시하지 않고 키에 넣음 → `test_아주_긴_접속_주소도_키는_짧다` 등 4
- 실패 한도 `<` → `<=` → `test_실패가_20번이_되면_21번째_요청부터_막는다`, `test_창이_지나면_다시_받는다`, 배선 1
- 요청 한도 `<=` → `<` → `test_1분에_60번까지_받고_61번째부터_막는다`, 배선 `test_1분에_61번째_요청부터_429_다`
- `expire` 의 `nx=True` 삭제 → `test_창은_처음_셀_때_잡히고_이후_요청이_늘리지_않는다`
- 공개 라우터에 `Depends(get_current_user_id)` 추가 → `test_API_프로세스에는_빈_자리도_빠진_가드도_없다`, `test_API_프로세스에서_로그인_없이_열리는_경로는_넷뿐이다`
- "설정이 비어 있으면 믿지 않는다" 삭제 → `test_비밀값을_설정하지_않았으면_빈_비밀값을_보내도_믿지_않는다`
- 토큰 헤더를 필수로 → 라우터 `test_이상한_토큰은_…[헤더 없음]`·`[다른 헤더]`, `test_토큰을_경로나_질의로는_받지_않는다`, 배선 2
- 응답 헤더 삭제 → `test_검색과_캐시를_막는_헤더를_단다`, 배선 1
- 기록이 없을 때의 410 삭제 → `test_기록이_없으면_410_이다`
- `main.py` 에서 열람 라우터 등록 삭제 → `test_API_프로세스에서_로그인_없이_열리는_경로는_넷뿐이다`
- 열람 인터랙터의 `mark_viewed` 삭제 → `test_처음_연_시각을_남기고_다시_열어도_그대로다`, 배선 `test_보내고_열고_끊고_다시_보낸다`
- `compare_digest` 대신 `REPORT_WEB_SECRET.startswith(secret)` → `test_비밀값이_틀리거나_주소가_없으면_연결된_주소다[비밀값 없음]`·`[빈 비밀값]`·`[짧은 비밀값]`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 공개 알림장 — 헤더 토큰으로 읽고 처음 연 시각을 남긴다, 횟수 제한과 공개 경로 허용 목록

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: 알림장 흐름 스크립트 — 보내기부터 공개 조회·끊기까지(`check_report_flow.sh`)

**Files:**
- Create: `backend/scripts/check_report_flow.sh`

**Interfaces:**
- Consumes: 작업 3·5·6·7·8 의 경로 일곱과 오류 코드; 기존 `check_media_flow.sh`·`check_visit_flow.sh` 의 모양(`BASE`, `expect`, 운영자 지정, 서명 URL 로 저장소에 바로 PUT).
- Produces: `backend/scripts/check_report_flow.sh` — `cd infra && bash ../backend/scripts/check_report_flow.sh`, 환경 변수 `BASE`(기본 `http://127.0.0.1:8080`), 출력은 `통과  <단계> <이름>` 34줄과 `전체 흐름 확인 완료`, 실패하면 그 줄에서 exit 1.

게이트웨이를 거쳐 실제 두 프로세스·DB·Redis·MinIO 로 흐름 전체를 확인한다(설계 11.1). 스크립트는 토큰과 서명 URL 을 화면에 찍지 않는다 — 같은지는 `같다`/`다르다` 로 바꿔 비교한다. 공개 요청은 한 번 실행에 13번, 그 가운데 404 는 2번이라 횟수 제한(분당 60, 실패 10분 20)에 걸리지 않는다.

**참조 구현에서는 대역 서버(테스트 DB·Redis db 14·테스트 버킷)로 13단계가 통과했다. 게이트웨이 경유는 이 작업에서 처음 돌린다.** 돌리기 전에: 개발 DB 에 0010 이 올라가 있어야 하고(작업 2), `.env` 에 `REPORT_LINK_KEY_B64` 가 있어야 하고(작업 5), 개발 스택이 이 브랜치의 코드로 떠 있어야 한다(`docker compose up -d --force-recreate backend auth`, `--reload` 가 변경을 놓칠 수 있다). 돌리면 개발 DB·버킷에 확인용 매장·고객·방문과 살아 있는 알림장 링크 하나가 남는다(기존 흐름 스크립트와 같다).

- [ ] **Step 1: 문서를 쓴다**

`backend/scripts/check_report_flow.sh`:

```bash
#!/usr/bin/env bash
# 개발 환경에서 알림장 설정 → 미리보기 → 사진 하나 빼고 보내기 → 공개 조회 → 열람 신호 → 되돌리기 거절 → 끊기 → 다시 보내기
# → 위조 토큰 → 내려받기까지 게이트웨이와 MinIO 를 거쳐 확인한다. 공개 조회는 로그인 없이 헤더 X-Report-Token 으로 간다.
# 사용: cd infra && docker compose up -d && docker compose run --rm backend python scripts/ensure_media_bucket.py \
#       && bash ../backend/scripts/check_report_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 와 버킷에 확인용 매장·유저·고객·방문·사진·알림장 링크가 남는다.
# 토큰과 서명 URL 은 화면에 찍지 않는다 — 비교는 같다/다르다로 바꿔서 하고, 단계 이름과 상태 코드만 보인다.
# 공개 요청은 열 번 남짓, 그 가운데 404 는 둘이다(횟수 제한: 분당 60회, 404 는 10분에 20회).
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
MARK="내부표식$STAMP"                                 # 내부 메모에 넣는 표식. 공개 응답 어디에도 없어야 한다
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
# has <글자열> — JSON 응답 전체(키·값)에 그 글자열이 있는지. 한글이 \u 로 와도 풀어서 본다.
has() { python3 -c "import json,sys; print(sys.argv[1] in json.dumps(json.load(sys.stdin), ensure_ascii=False))" "$1"; }
same() { if [ "$1" = "$2" ]; then echo 같다; else echo 다르다; fi; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# open_report <토큰> — 공개 조회. 로그인이 없다. 토큰이 비면 헤더도 보내지 않는다.
open_report() { curl -s "$BASE/v1/public/report" ${1:+-H "X-Report-Token: $1"}; }
open_status() { curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/public/report" ${1:+-H "X-Report-Token: $1"}; }
viewed_status() { curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/public/report/viewed" ${1:+-H "X-Report-Token: $1"}; }
# put <URL> <형식> <바이트 수> — 서명 URL 로 저장소에 바로 올린다. 인증 헤더가 없다.
put() { head -c "$3" /dev/zero | curl -s -o /dev/null -w '%{http_code}' -X PUT "$1" -H "Content-Type: $2" --data-binary @-; }
# photo <토큰> — 사진 하나를 발급·올리기·확인까지 마치고 media_id 를 낸다.
photo() {
  local issued; issued=$(call POST "$S/media/uploads" "$1" \
    '{"kind":"photo","content_type":"image/jpeg","byte_size":3000,"width":3000,"height":2000}')
  [ "$(put "$(echo "$issued" | field "['puts']['original']")" image/jpeg 3000)" = 200 ]
  [ "$(put "$(echo "$issued" | field "['puts']['display']")" image/jpeg 800)" = 200 ]
  [ "$(put "$(echo "$issued" | field "['puts']['thumb']")" image/jpeg 200)" = 200 ]
  local id; id=$(echo "$issued" | field "['media_id']")
  [ "$(call POST "$S/media/$id/confirm" "$1" | field "['status']")" = ready ]
  echo "$id"
}
# send <뺄 미디어 ID 목록> — 알림장을 보내고(또는 다시 공유하고) 응답을 낸다.
send() { call PUT "$V/report" "$staff_token" "{\"hidden_media_ids\":[$1]}"; }
token_of() { local url; url=$(field "['link']['url']"); echo "${url##*/}"; }

# 1. 매장·고객·방문
op=$(login "rflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"알림장흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "rflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "rflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
echo "통과  1 매장 $shop_id 에 사장과 직원이 있다"

registered=$(call POST "$S/customers" "$staff_token" "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\
\"pet\":{\"name\":\"콩이\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\
\"weight_kg\":3.2,\"no_known_conditions\":true}}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
# 어제 11시 예약을 시작한다 — 실행 시각과 상관없이 자정을 넘기지 않는다.
visit=$(call POST "$S/visits" "$staff_token" "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at -1 11)\"}" \
  | field "['visits'][0]['visit_id']")
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"start\"}" >/dev/null
V="$S/visits/$visit"

# 2. 사진 둘과 기록
before=$(photo "$staff_token"); after=$(photo "$staff_token")
bath=$(call GET "$S/menus" "$staff_token" | field "['items'][0]['menu_id']")
saved=$(call PUT "$V/record" "$staff_token" "{\"weight_kg\":3.4,\"care_note\":\"눈물 자국 관리\",\"internal_note\":\"$MARK\",\
\"payment_method\":\"card\",\"total_amount\":25000,\"items\":[{\"menu_id\":$bath,\"amount\":28000}],\
\"media\":[{\"media_id\":$before,\"phase\":\"before\",\"sort_order\":0},{\"media_id\":$after,\"phase\":\"after\",\"sort_order\":0}]}")
expect "2 사진 둘과 두 메모를 기록에 적었다" "$(echo "$saved" | calc "(len(d['media']), d['internal_note'] == '$MARK')")" "(2, True)"
expect "2 완료 전에는 보내지 못한다" "$(send "" | field "['code']")" "VISIT_NOT_COMPLETED"
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"complete\"}" >/dev/null

# 3. 알림장 설정
expect "3 설정의 처음 값은 30일, 메뉴·매장 정보만 켬" "$(call GET "$S/report-settings" "$staff_token" \
  | calc "(d['link_days'], d['show_menus'], d['show_shop_info'], d['show_weight'], d['show_amount'])")" "(30, True, True, False, False)"
ALL_ON='{"link_days":30,"show_menus":true,"show_shop_info":true,"show_weight":true,"show_amount":true}'
expect "3 직원은 설정을 바꾸지 못한다" "$(status PUT "$S/report-settings" "$staff_token" "$ALL_ON")" "403"
expect "3 사장이 금액과 몸무게를 켠다" "$(call PUT "$S/report-settings" "$owner_token" "$ALL_ON" \
  | calc "(d['show_weight'], d['show_amount'])")" "(True, True)"

# 4. 미리보기 → 사진 하나를 빼고 보내기
expect "4 미리보기는 사진 둘을 주고 링크는 아직 없다" "$(call GET "$V/report" "$staff_token" \
  | calc "(len(d['report']['media']), d['link']['status'], d['link']['url'])")" "(2, 'none', None)"
sent=$(send "$before")
expect "4 전 사진을 빼고 보냈다" "$(echo "$sent" | calc "(d['link']['status'], sorted(m['media_id'] for m in d['report']['media'] if m['hidden']) == [$before])")" "('live', True)"
token=$(echo "$sent" | token_of)
expect "4 링크의 끝이 토큰 43글자다" "${#token}" "43"

# 5. 공개 조회
opened=$(open_report "$token")
expect "5 뺀 사진은 없고 후 사진 하나만 있다" "$(echo "$opened" | calc "[m['phase'] for m in d['media']]")" "['after']"
expect "5 내부 메모 표식이 없다" "$(echo "$opened" | has "$MARK")" "False"
expect "5 보호자 이름과 전화번호가 없다" "$(echo "$opened" | calc "('김민지' in json.dumps(d, ensure_ascii=False), '$PHONE' in json.dumps(d))")" "(False, False)"
expect "5 반려동물 이름과 케어 메모가 있다" "$(echo "$opened" | calc "(d['pet_name'], d['care_note'])")" "('콩이', '눈물 자국 관리')"
expect "5 금액과 몸무게 칸이 있다" "$(echo "$opened" | calc "(d['total_amount'], d['menus'][0]['amount'], d['weight_kg'])")" "(25000, 28000, 3.4)"
expect "5 검색과 캐시를 막는 헤더가 있다" "$(curl -s -o /dev/null -D - "$BASE/v1/public/report" -H "X-Report-Token: $token" \
  | tr -d '\r' | grep -ci -e '^cache-control: private, no-store$' -e '^x-robots-tag: noindex, nofollow$')" "2"

# 6. 금액을 끄면 칸이 없다
call PUT "$S/report-settings" "$owner_token" \
  '{"link_days":30,"show_menus":true,"show_shop_info":true,"show_weight":true,"show_amount":false}' >/dev/null
expect "6 금액을 끄면 금액 칸이 없고 몸무게는 남는다" "$(open_report "$token" \
  | calc "('total_amount' in d, 'amount' in d['menus'][0], 'weight_kg' in d)")" "(False, False, True)"

# 7. 열람 신호
expect "7 조회만으로는 열람이 남지 않는다" "$(call GET "$V" "$staff_token" | calc "d['report']['first_viewed_at']")" "None"
expect "7 열람 신호는 204" "$(viewed_status "$token")" "204"
expect "7 방문 상세에 처음 연 시각이 있다" "$(call GET "$V" "$staff_token" \
  | calc "(d['report']['status'], d['report']['first_viewed_at'] is not None)")" "('live', True)"
expect "7 하루 목록과 피드에 보냄 표시" "$(echo "$(call GET "$S/visits?date=$(at -1 11 | cut -c1-10)" "$staff_token" \
  | calc "[v['report_sent'] for v in d['items'] if v['visit']['visit_id'] == $visit]") $(call GET "$S/visits/feed?pet_id=$kong" "$staff_token" \
  | calc "d['items'][0]['report_sent']")")" "[True] True"

# 8. 보낸 방문은 되돌리거나 기록을 지울 수 없다
expect "8 되돌리기는 409" "$(call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"revert\"}" | field "['code']")" "VISIT_REPORT_SENT"
expect "8 기록 삭제도 409" "$(call DELETE "$V/record" "$owner_token" | field "['code']")" "VISIT_REPORT_SENT"

# 9. 다시 보내기 — 같은 링크
expect "9 다시 보내면 같은 링크다" "$(same "$(send "$before" | token_of)" "$token")" "같다"

# 10. 끊기
expect "10 끊기는 204" "$(status DELETE "$V/report" "$staff_token")" "204"
expect "10 끊은 링크의 공개 조회는 410" "$(open_report "$token" | field "['code']")" "REPORT_CLOSED"
expect "10 끊은 링크의 열람 신호도 410" "$(viewed_status "$token")" "410"
expect "10 방문은 안 보냄으로 돌아간다" "$(call GET "$V" "$staff_token" | calc "d['report']['status']")" "none"
expect "10 끊을 링크가 없으면 404" "$(call DELETE "$V/report" "$staff_token" | field "['code']")" "REPORT_NOT_FOUND"

# 11. 다시 보내기 — 새 링크
resent=$(send "$before")
new_token=$(echo "$resent" | token_of)
expect "11 끊은 뒤 보내면 다른 링크다" "$(same "$new_token" "$token")" "다르다"
expect "11 옛 토큰은 여전히 410, 새 토큰은 200" "$(open_status "$token") $(open_status "$new_token")" "410 200"
expect "11 새 링크는 아직 열지 않았고 뺀 사진은 빠져 있다" "$(echo "$resent" \
  | calc "(d['link']['first_viewed_at'], [m['media_id'] for m in d['report']['media'] if m['hidden']] == [$before])")" "(None, True)"

# 12. 우리가 만들지 않은 토큰
if [ "${new_token:0:1}" = A ]; then forged="B${new_token:1}"; else forged="A${new_token:1}"; fi
expect "12 위조한 토큰은 404" "$(open_report "$forged" | field "['code']")" "REPORT_NOT_FOUND"
expect "12 헤더가 없으면 404" "$(open_status "")" "404"

# 13. 내려받기
download=$(open_report "$new_token" | field "['media'][0]['download_url']")
expect "13 내려받기 주소는 첨부 파일로 내려온다" "$(curl -s -o /dev/null -D - "$download" | tr -d '\r' \
  | grep -ci '^content-disposition: attachment; filename="chagocnote-[0-9]*\.jpg"$')" "1"

echo "전체 흐름 확인 완료"
```

- [ ] **Step 2: 확인한다**

Run (`infra/`): `docker compose run --rm backend python scripts/ensure_media_bucket.py`

Run (`infra/`): `bash ../backend/scripts/check_report_flow.sh` → `통과` 34줄 뒤 `전체 흐름 확인 완료`, 종료 코드 0

판별력(한 번): 스크립트의 `expect "5 내부 메모 표식이 없다" … "False"` 의 기대를 `"True"` 로 바꿔 돌리면 `실패  5 내부 메모 표식이 없다 (기대 True, 실제 False)` 로 멈추고 그 뒤 줄이 나오지 않아야 한다. 확인한 뒤 편집으로 되돌리고 다시 돌려 전부 통과함을 본다. **참조 구현에서는 이 확인을 돌리지 못했다**(실행 권한 판정이 거부했다) — 이 작업에서 처음 확인한다. 거부되면 돌아가는 길을 찾지 말고 사용자에게 알린다.

Run (`infra/`): `docker compose run --rm --no-deps auth python scripts/print_routes.py` 를 받아 작업 1 전에 받아 둔 것과 `diff` → 늘어난 줄은 일곱뿐이다(`/v1/public/report`, `/v1/public/report/viewed`, `/report-settings` GET·PUT, `/visits/{visit_id}/report` GET·PUT·DELETE). 없어지거나 바뀐 줄은 없다.

- [ ] **Step 3: 커밋한다**

```bash
git add -A
git commit -m "test(visit): 알림장 흐름 스크립트 — 보내기부터 공개 조회·끊기까지

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: 문서 — 스포크 규칙, 검증 장치, 결정 기록 008(⑤-2 웹·⑤-3 앱이 기댈 API 계약)

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Create: `_docs/decisions/008-report.md`
- Modify: `_docs/harness.md`
- Modify: `backend/apps/customer/_docs/CLAUDE.md`
- Modify: `backend/apps/hub/_docs/CLAUDE.md`
- Modify: `backend/apps/media/_docs/CLAUDE.md`
- Modify: `backend/apps/tenancy/_docs/CLAUDE.md`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`

**Interfaces:**
- Consumes: 작업 1~9 의 결과 전부.
- Produces: `_docs/decisions/008-report.md` — 사용자 결정, 새로 정한 것, 설계와 다르게 간 것, 알려진 동작, 감수하는 것, 남는 것, **API 계약**(경로 표·본문·오류 코드 표·공개 조회의 판정 순서·헤더 표·설정 상수 표). ⑤-2·⑤-3 의 계획은 이 계약에 기댄다.

문서는 기존 글에 더한다. 사실과 어긋나게 된 기존 문장만 고친다. 비밀값·토큰의 실제 값을 예시로 쓰지 않는다. 결정 기록의 '흐름 확인' 절과 '남는 것'의 흐름 스크립트 줄은 작업 9 에서 게이트웨이로 돌린 실제 결과로 고쳐 적는다 — 아래 글은 참조 구현(대역 서버) 때의 것이다. 실행 중에 계획과 다르게 한 것이 있으면 '설계·브리프와 다르게 간 것'에 더한다.

- [ ] **Step 1: 문서를 쓴다**

`CLAUDE.md`:

```diff
@@ -23,6 +23,9 @@
 - 스포크끼리 직접 import하지 않는다. 교차 협력은 `apps/hub`의 포트를 거친다. 허브는 스포크를 모른다.
 - 스포크의 `dependencies/`도 다른 스포크를 import하지 않는다. 다른 스포크가 구현한 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
 - 매장 범위의 경로는 `core/shop_guard.py`의 `get_shop_context` 또는 `require_permission`으로 `ShopContext`를 받는다. 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.
+- 로그인 없이 열리는 경로는 `backend/tests/route_inspection.py`의 허용 목록과 프로세스별 목록 테스트에 있는 것뿐이다. 공개 응답 스키마는 매장용과 따로 쓰고 칸을 하나하나 적는다.
+- 알림장 토큰은 헤더(`X-Report-Token`)로 받고 로그·문서·커밋에 남기지 않는다.
+- `ShopContext`를 가드 없이 만드는 곳은 `visit/app/services/public_context.py` 하나다. 권한이 비어 있고 읽기에만 쓴다.
 - 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있고 인증 프로세스(`auth_main.py`)만 읽는다. 이 모듈은 함수 안에서만 import한다. API 프로세스 경로에서 import하지 않는다.
 - 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. 고객·방문 쪽은 고객 행 → 방문 행(ID 오름차순)이다 — 방문을 쓰는 유스케이스는 허브 포트 `CustomerDirectoryPort.lock_family`로 고객 행부터 잠근다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다.
 - `load_dotenv`·`os.getenv`·`os.environ`은 `core/singleton/secret_manager.py`에서만 쓴다.
```

`README.md`:

```diff
@@ -19,6 +19,20 @@
     bash ../backend/scripts/check_shop_flow.sh                                      # 매장 개설·합류 흐름 확인
     bash ../backend/scripts/check_account_flow.sh                                   # 회원 탈퇴 흐름 확인
     bash ../backend/scripts/check_customer_flow.sh                                  # 고객·반려동물 흐름 확인
+    bash ../backend/scripts/check_report_flow.sh                                    # 알림장 흐름 확인 (버킷 준비 뒤 — _docs/harness.md)
+
+`REPORT_LINK_KEY_B64`(알림장 링크의 서명 키, 32바이트 이상을 base64 로)는 필수다. 없으면 API 프로세스와 인증 프로세스가 둘 다 기동하지 않는다. `generate_dev_env.py`는 `.env`가 이미 있으면 아무것도 하지 않으므로, ⑤ 이전에 만든 개발 환경은 한 줄을 직접 더한다. 먼저 `.env`가 줄바꿈으로 끝나는지 본다(끝나지 않으면 앞 줄에 붙는다). 아래 명령은 값을 출력하지 않고, 이미 있으면 아무것도 하지 않는다. 키를 바꾸면 보낸 링크가 모두 닫힌다.
+
+    docker compose run --rm --no-deps backend python -c "
+    import base64, secrets
+    from pathlib import Path
+    env = Path('/work/.env')
+    if 'REPORT_LINK_KEY_B64=' not in env.read_text():
+        with env.open('a') as f:
+            f.write('REPORT_LINK_KEY_B64=' + base64.b64encode(secrets.token_bytes(32)).decode() + '\n')
+    "
+
+`REPORT_WEB_BASE_URL`(보호자 웹의 주소, 기본 `http://127.0.0.1:3010`)과 `REPORT_WEB_SECRET`(웹 서버와 나누는 비밀값, 기본은 빈 값)은 없어도 뜬다.
 
 개발 환경에서는 제공자 `dev`로 이름만 넣어 로그인한다. 운영자는 `docker compose run --rm backend python scripts/grant_operator.py <user_id>`로 지정한다.
```

`_docs/decisions/008-report.md`:

```markdown
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

visit 스포크에 알림장 링크(발급·끊기·미리보기), 알림장 설정, 공개 조회와 열람 신호, 횟수 제한. 허브 포트 `ShopProfilePort`(tenancy 구현)와 `MediaUrls.download_url`(media). 새 라우트 7개(설정 둘, 매장용 알림장 셋, 공개 둘 — 라우트 표의 나머지는 그대로), 마이그레이션 0010(`visit_reports`, `visit_record_media.hidden_from_report`, `visit_shop_settings`의 `report_*` 다섯 칸), 새 비밀값 `REPORT_LINK_KEY_B64`, 스크립트 `check_report_flow.sh`. 단위 883 → 1288, 통합 300 → 398, 구조 계약 6종. 새 의존성은 없다.

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
- **제한기 포트는 메서드 둘이다**(`allow`, `note_miss`). 요청 세기와 실패 수 읽기가 Redis 왕복 한 번이다. 한도 상수는 어댑터에 있다.
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
- 429 는 맞는 토큰에도 난다. 같은 접속 주소의 실패가 10분에 20번이면 그 주소의 모든 요청이 막힌다.
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
- 흐름 스크립트의 판별력(기대를 뒤집으면 그 단계에서 멈추는지)은 참조 구현에서 돌려 보지 못했다.
- `GET /v1/shops/myself`·`GET /v1/auth/myself`가 로그인 없이 열려 있다(기존 동작, 목록에 고정했다). 의도한 것인지 확인하지 않았다.
- 테스트 파일을 골라 돌릴 때 `tests/test_hub_port_binding.py`를 통합 파일 사이에 두면 `fixture 'wired' not found`다(전체 실행에는 없다, 원인 미조사).
- 확인하지 못한 것: 실제 AWS S3 에서의 내려받기 서명, 브라우저의 실제 저장, 영상의 내려받기·공개 조회, 메뉴 항목이 있는 기록의 배선, 게이트웨이(Caddy) 접속 기록, 게이트웨이를 거친 흐름 스크립트, 실제 Redis 장애와 연결 시간 초과 동안의 대기.
- 운영에서 OpenAPI 문서(`/docs`)에 공개 경로가 보이는지 정하지 않았다.
- 하루 목록·피드·상세·전이는 질의가 하나씩 늘었다. 실행 계획과 시간은 재지 않았다. `visit_reports.visit_id`에는 부분 유일 색인만 있다 — 끊은 줄까지 방문으로 찾는 질의가 생기면 색인을 더한다.
- 두 사장이 동시에 설정을 바꾸면 늦은 쪽이 덮는다.
- 미룬 것(설계 10절): 알림톡 자동 발송(⑥), 보호자 로그인과 지난 알림장 모아 보기(⑦), CloudFront 서명 URL, 서버 측 EXIF 검증, 실제 Vercel 배포와 도메인 리다이렉트, 링크 키 교체 절차, 랜딩 페이지·알림장 다국어·만족도 버튼.

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
| `TOO_MANY_ATTEMPTS` | 429 | 공개: 접속 주소별 분당 60회 초과, 또는 404 가 10분에 20회 |
| `VISIT_REPORT_SENT` | 409 | 살아 있는 링크가 있는 방문의 되돌리기·기록 삭제 |
| `PERMISSION_DENIED` | 403 | 직원의 설정 변경, `record:write` 없는 보내기·끊기 |

보내기의 오류 순서는 `VISIT_NOT_FOUND` → 가족 잠금의 오류 → `VISIT_NOT_COMPLETED` → `VISIT_NO_RECORD_YET` → `VALIDATION_ERROR` → `REPORT_EMPTY`다.

**공개 조회의 판정 순서.** 횟수 제한(429) → 토큰의 서명(404, DB 를 읽지 않는다) → 링크 찾기(404) → 살아 있음(410) → 매장(410) → 기록(410). 열람 신호는 기록을 보지 않는 것만 다르다. 열람 신호는 한 번 남으면 바뀌지 않고 닫힌 링크에는 남기지 않는다.

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

`backend/scripts/check_report_flow.sh`를 참조 작업 트리의 코드로 띄운 대역 서버(인증·API 앱을 한 포트에 묶음, 테스트 DB·테스트 버킷·Redis db 14)에 붙여 열세 단계(확인 34줄)가 통과했다. 게이트웨이(Caddy)를 거친 흐름은 실행 때 확인한다.
```

`_docs/harness.md`:

```diff
@@ -17,6 +17,7 @@
 | 예약·방문 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_visit_flow.sh` — 개발 DB에 확인용 매장·유저·고객·방문이 남는다 |
 | 미디어 버킷 준비 | `docker compose run --rm backend python scripts/ensure_media_bucket.py` (버킷 생성 + 원본 수명주기 규칙. MinIO 는 계층 이동을 받지 않아 규칙을 건너뛴다) |
 | 사진·기록 흐름 (게이트웨이·MinIO 경유) | `bash ../backend/scripts/check_media_flow.sh` — 버킷 준비 뒤. 서명 URL 로 저장소에 바로 올리고 읽는다. 개발 DB·버킷에 확인용 매장·사진이 남는다 |
+| 알림장 흐름 (게이트웨이·MinIO 경유) | `bash ../backend/scripts/check_report_flow.sh` — 버킷 준비 뒤. 설정 → 보내기 → 공개 조회(헤더 `X-Report-Token`) → 열람 신호 → 끊기 → 410 → 다시 보내기 → 내려받기. 토큰과 서명 URL 은 화면에 찍지 않는다. 개발 DB·버킷에 확인용 매장·사진·알림장 링크가 남는다 |
 | 미디어 정리 | `docker compose run --rm backend python scripts/purge_stale_media.py` (하루 넘게 어느 기록도 가져가지 않은 사진·영상 — 운영은 주기적으로) |
 | 최근 방문순 키 복구 | `docker compose run --rm backend python scripts/rebuild_last_visit.py` (고객 목록 '최근 방문순'이 방문 기록과 어긋났을 때) |
 | 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
@@ -42,3 +43,8 @@
 - 통합 테스트는 compose 의 MinIO 도 쓴다(`backend` 서비스가 `minio`에 기댄다). 미디어가 필요한 테스트는 `media_storage` 픽스처를 쓴다 — 테스트 버킷 `chagocnote-test`를 시작 때 비우고(테스트마다 DB ID 가 1부터라 키가 겹친다), 컨테이너 안에서 서명 URL 로 PUT 하도록 공개 주소를 내부 주소로 둔다. 사진 하나를 확인까지 마치는 도우미는 `tests/integration/support.py`의 `ready_photo`다.
 - 마이그레이션에 시드 표를 새로 만들면 루트 `conftest.py`의 `_KEEP_TABLES`에 더한다. 빠뜨리면 첫 테스트가 시드를 비워 그다음 테스트부터 실패한다.
 - 두 세션 경합 테스트는 막힌 호출을 `asyncio.create_task`로 들고 있다가 앞선 세션이 커밋한 뒤의 결과를 본다. "기다렸다"만으로 판별하지 않는다 — 외래 키의 암묵적 잠금이나 같은 행의 다른 잠금 때문에 잠금 코드가 없어도 기다릴 수 있다. 잠금 코드를 빼는 변이로 테스트가 실패하는지 확인한다.
+- 공개 경로(`/v1/public/`)는 `tests/route_inspection.py`의 허용 목록(`_PUBLIC_ROUTES`)에 더한다. 목록에 없는 공개 경로와 로그인·매장 확인을 거치는 공개 경로는 `find_route_violations`가 잡는다.
+- 로그인 없이 열리는 경로는 프로세스마다 목록 전체를 못 박는다(`routes_without_login`) — API 프로세스는 `tests/test_hub_port_binding.py`(넷), 인증 프로세스는 `tests/integration/test_route_wiring.py`(다섯). 경로를 열거나 로그인 의존성을 빼면 목록과 달라져 실패한다. 일부러 연 경로는 두 곳(허용 목록, 프로세스별 목록)에 함께 적는다.
+- 로그인 없는 경로의 응답은 표식 문자열로 본문 전체를 검사한다. 내부 메모·결제 수단·예약 메모·보호자 이름·전화번호·고객 메모에 표식을 넣고, 모든 항목을 켠 응답의 글자열 어디에도 없는지 본다(`tests/integration/test_public_report_wiring.py`). 칸 이름만 보는 검사로는 값이 다른 칸에 섞이는 것을 놓친다.
+- 토큰·서명 URL 이 든 응답을 다루는 통합 테스트가 실패하면 pytest 가 지역 변수를 찍는다. 출력을 옮겨 적을 일이 있으면 `--tb=line`·`--tb=no`로 돌린다.
+- 테스트 파일을 골라 돌릴 때 `tests/test_hub_port_binding.py`는 맨 뒤에 두거나 따로 돌린다. 통합 파일 사이에 두면 뒤쪽 통합 파일이 `fixture 'wired' not found`로 멈춘다(전체 실행에는 없다. 원인은 조사하지 않았다).
```

`backend/apps/customer/_docs/CLAUDE.md`:

```diff
@@ -15,5 +15,5 @@
 - 반려동물은 질병을 하나 이상 고르거나 "질병 없음"을 직접 확인해야 저장된다(두 표에 걸친 규칙이라 도메인이 확인한다). 질병 종류는 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다.
 - 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각·카톡 초안 후보). 초안 후보(`find_draft_candidates`)는 낱말 하나라도 걸리는 가족(`CustomerSearchPort.match_any`, OR)을 읽어 반려동물 이름 정확 일치 → 보호자 이름 → 전화 → 부분 일치 순으로 최대 5 가족만 돌려주고, 낱말을 저장하거나 로그에 남기지 않는다. `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
 - 반려동물 프로필 사진은 저장하지 않는다. 조회 셋(목록 `pets[].photo`, 고객 상세 `pets[].photo`, 반려동물 상세 `pet.photo`)이 읽을 때마다 `VisitLedgerPort.latest_covers`(대표 사진의 media_id)와 `MediaLibraryPort.read_urls`(썸네일 URL)로 한 번씩 묻는다(`app/services/pet_photos.py`, N+1 없음). 쓰기 응답에는 사진이 없다 — 쓰기 뒤 다시 읽는다. `MediaLibraryPort`는 `dependencies/hub_ports.py`의 자리로 받는다.
-- 익명화는 visit 이 방문 메모와 미용 기록의 두 메모(케어·내부)를 비우고, 사진은 매장의 기록이라 남긴다. 미용 기록의 몸무게는 visit 이 `CustomerDirectoryPort.set_pet_weight`로 알려 준다(가장 최근 기록일 때만) — 고객 행을 잠근 트랜잭션 안이다.
+- 익명화는 visit 이 방문 메모와 미용 기록의 두 메모(케어·내부)를 비우고 그 고객 방문의 알림장 링크를 끊는다(⑤). 사진은 매장의 기록이라 남긴다. 미용 기록의 몸무게는 visit 이 `CustomerDirectoryPort.set_pet_weight`로 알려 준다(가장 최근 기록일 때만) — 고객 행을 잠근 트랜잭션 안이다.
 - 검색 줄의 `last_visit_at`(최근 방문순)은 원본이 visits 다 — 검색 줄을 다시 만들 때 건드리지 않고, visit 이 `set_last_visit`로 알려 준다.
```

`backend/apps/hub/_docs/CLAUDE.md`:

```diff
@@ -18,5 +18,9 @@
 | `ActiveUserGuardPort.lock_active(user_id) → bool` | auth `guard_active_user` | tenancy `accept_invite` |
 | `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy `apply_withdrawal` | auth `withdraw` (인증 프로세스) |
 | `CustomerDirectoryPort.lock_family · briefs · set_last_visit · set_pet_weight · find_draft_candidates(ctx, words) → list[DraftCandidate]` | customer `customer_directory` | visit (방문 쓰기의 가족 잠금, 이름 표시, 최근 방문순, 기록의 몸무게, 카톡 초안 후보) |
-| `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기·`latest_covers`) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세, 반려동물 프로필 사진) |
-| `MediaLibraryPort.claim(ctx, ids) → {id: kind} · release · read_urls(ctx, ids) → {id: MediaUrls}` | media `media_library` | visit (기록의 사진·영상), customer (프로필 사진) |
+| `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기(`clear_customer_memos` — 알림장 링크도 끊는다)·`latest_covers`) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세, 반려동물 프로필 사진) |
+| `MediaLibraryPort.claim(ctx, ids) → {id: kind} · release · read_urls(ctx, ids) → {id: MediaUrls}` | media `media_library` | visit (기록의 사진·영상, 알림장), customer (프로필 사진) |
+| `ShopProfilePort.public_profile(shop_id) → ShopProfile \| None` (이름·전화·주소·시간대·영업 중 여부) | tenancy `get_shop_profile` | visit (알림장의 매장 정보, 공개 조회의 시간대와 정지·폐업 판정) |
+
+- `MediaUrls`에는 `download_url`이 있다 — 원본을 첨부 파일로 내려받는 서명 주소다. 칸이 `original_url` 바로 뒤라 `MediaUrls`는 이름 인자로 만든다.
+- `ShopProfilePort.public_profile`은 권한을 보지 않고 정지·폐업한 매장도 돌려준다(`None`은 없는 매장뿐). 로그인한 사용자가 없는 경로가 서명을 확인한 링크에서 읽은 매장 ID 로만 부른다.
```

`backend/apps/media/_docs/CLAUDE.md`:

```diff
@@ -10,3 +10,4 @@
 - 허브 포트 `MediaLibraryPort`를 구현한다(`app/use_cases/media_library_interactor.py`, HTTP 없음). visit 이 기록에 붙일 때 가져가고(`claim` — 준비됐고 이 매장의 것이고 아무도 안 가져간 것만, 전부 되거나 전부 안 됨, 세이브포인트) 뺄 때 놓는다(`release`). customer·visit 이 읽기 URL 을 받는다(`read_urls`). media 는 어느 기록이 가져갔는지 모른다 — `attached_at`만 안다.
 - 놓였거나 가져가지 않은 미디어는 바로 지우지 않는다. `scripts/purge_stale_media.py`가 하루 넘은 것(pending, 또는 ready 인데 미부착 — 놓기가 `ready_at`을 다시 찍으므로 놓인 미디어는 놓인 시각부터 하루)을 표시 → 저장소 삭제 → 행 삭제 순서로 지운다. 운영에서는 이 스크립트를 주기적으로 돌린다.
 - 이 스포크는 다른 스포크를 import 하지 않는다. 다른 스포크의 허브 포트도 쓰지 않는다.
+- `read_urls`는 내려받기용 주소(`download_url`)도 준다. 원본 키를 `response-content-disposition=attachment`와 함께 서명한 것이고 파일 이름은 `media_rules.download_name`(`chagocnote-{ID}.jpg`·`.mp4`)이 정한다. 서명에 들어가므로 파일 이름만 바꾸면 저장소가 403 을 준다. 서명 시각 규칙은 읽기 URL 과 같다. `sigv4_query.presign_get_url`이 더 받는 질의 매개변수는 이것 하나다 — 다른 것을 더하면 키 정렬을 다시 짠다.
```

`backend/apps/tenancy/_docs/CLAUDE.md`:

```diff
@@ -4,7 +4,7 @@
 
 - 사장·직원은 계정 종류가 아니라 `shop_members`의 행이다. 같은 유저가 여러 매장에 속할 수 있다.
 - `shop_members.user_id`는 auth의 유저 ID지만 외래 키를 걸지 않는다. 이름과 사진은 허브의 `UserDirectoryPort`로 받는다.
-- 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다. 컨텍스트가 없는 경로(소속 확인, 초대 수락, 매장 개설, 유저 기준 소속 목록)만 예외다.
+- 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다. 컨텍스트가 없는 경로(소속 확인, 초대 수락, 매장 개설, 유저 기준 소속 목록, 매장 공개 정보 `find_by_id`)만 예외다.
 - 역할과 권한은 마이그레이션 시드다. 코드에서 만들거나 고치지 않는다.
 - 매장에는 사장이 한 명 이상 있어야 한다. 멤버십을 바꾸는 유스케이스(역할 변경, 내보내기, 초대 수락, 탈퇴)는 맨 앞에서 `lock_membership_changes(shop_id)`로 매장 행을 잠근 뒤 대상을 읽는다. 사장을 낮추거나 내보내기 전에는 `count_owners`로 사장 행을 잠그고 센다.
 - 잠금 순서는 언제나 유저 행 → 매장 행 → 멤버 행 → 초대 행이다. 여러 매장을 잠글 때는 매장 ID 오름차순으로 잠근다. 순서를 어기면 다른 경로와 교착한다.
@@ -13,4 +13,5 @@
 - 내보내거나 사장에서 낮춘 멤버가 만든 미사용 초대는 같은 트랜잭션에서 `revoke_created_by`로 무효화한다.
 - **초대 생성·내보내기·역할 변경은 매장 행을 잠근 뒤 행위자를 다시 읽는다.** 매장 행을 잠근 뒤 `get_active(ctx, ctx.member_id)`로 행위자를 다시 읽고 `ensure_actor_unchanged`로 확인한다. 요청 가드가 권한을 확인한 뒤 잠금을 얻는 사이에 내보내지거나 낮춰졌으면 `NotAMemberError`다. 초대 생성에 이 잠금이 없으면 INSERT 가 외래 키의 암묵적 잠금으로 기다렸다가, 내보내기의 초대 무효화가 끝난 뒤에 살아 있는 초대를 남긴다. 초대 수락은 소속을 새로 만들기 전에 허브의 `ActiveUserGuardPort.lock_active`로 유저 행을 먼저 잠그고 다시 본다(위 항목). `update_shop`·`provision_shop`은 이 확인이 없다 — 매장 잠금을 기다리는 사이 내보내진 멤버가 낡은 `ShopContext`로 수정을 끝낼 수 있다(003의 "남는 것").
 - 초대 코드는 원문을 저장하지 않는다. 8자리(헷갈리는 글자 I·O·0·1 제외), SHA-256 해시 저장, 7일 만료, 1회 사용.
-- 허브 포트 구현은 HTTP 표면이 없는 슬라이스다: `resolve_shop_access`, `provision_shop`, `list_memberships`. 인터랙터가 허브 포트 ABC를 직접 상속한다.
+- 허브 포트 구현은 HTTP 표면이 없는 슬라이스다: `resolve_shop_access`, `provision_shop`, `list_memberships`, `get_shop_profile`. 인터랙터가 허브 포트 ABC를 직접 상속한다.
+- `get_shop_profile`(허브 포트 `ShopProfilePort`)은 공개 알림장이 쓴다. 매장의 이름·전화·주소·시간대와 영업 중 여부(정지도 폐업도 아님)를 주고, 잠그지 않으며 권한을 보지 않는다. 없는 매장은 `None`이다.
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -1,6 +1,6 @@
 # visit — 방문(예약부터 완료까지), 미용 기록, 매장 일정, 메뉴표
 
-소유 데이터: `visits`, `visit_menus`, `visit_records`, `visit_record_items`, `visit_record_media`, `visit_shop_settings`, `visit_weekly_closures`, `visit_closed_dates`, `service_menus`.
+소유 데이터: `visits`, `visit_menus`, `visit_records`, `visit_record_items`, `visit_record_media`, `visit_reports`, `visit_shop_settings`(일정 설정과 알림장 설정 칸), `visit_weekly_closures`, `visit_closed_dates`, `service_menus`, Redis의 공개 알림장 조회 횟수.
 
 - 방문 하나는 반려동물 한 마리의 방문이다. `pet_id`가 NULL 이면 보호자만의 방문이다. 두 마리를 한 번에 잡으면 방문이 둘이고, 같은 보호자 + 같은 시작 시각이 가족 묶음이다(저장하지 않고 계산한다).
 - `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
@@ -21,3 +21,17 @@
 - customer 에 `VisitLedgerPort.latest_covers`(사진이 붙은 가장 최근 완료 방문의 대표 — 반려동물 프로필 사진)를 준다. 익명화(`clear_customer_memos`)는 방문 메모와 기록의 두 메모를 비우고 사진은 남긴다.
 - 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
 - 카톡 예약 초안(`POST /visit-drafts`)은 **아무것도 저장하지 않는다.** 글은 `app/ports/output/visit_draft_parser_port.py` 뒤의 규칙 어댑터(`adapter/outbound/rule_draft_parser_adapter.py` → `domain/services/draft_parser.py`)가 날짜·시각·메뉴·낱말로 읽고, "누구"는 허브 포트 `CustomerDirectoryPort.find_draft_candidates`가 낱말로 찾는다(최대 5 가족). 글과 낱말을 로그·DB·오류 응답에 남기지 않는다(설계 10절 V9). ⑨ 이후 LLM 해석은 같은 포트 뒤에서 어댑터만 바꾼다.
+- **미용 알림장**(⑤)은 새 스포크가 아니라 방문 위에 쌓인다. 링크 하나가 `visit_reports`의 한 줄이고 매장은 방문에서 읽는다(`shop_id` 칸이 없다). '살아 있음'은 끊지 않았고 기간이 남은 것이다(`VisitReport.is_live`, 끝나는 바로 그 시각은 닫힘). '보냄'은 저장하지 않고 살아 있는 줄이 있는지로 계산한다.
+- **방문당 끊지 않은 줄은 하나다**(부분 유일 색인 `uq_visit_reports_live`). 색인에 지금 시각을 넣을 수 없으므로 **발급이 먼저 닫는다** — 보내기는 `lock_visits` → `close_expired` → `get_live` → 없을 때만 `create` 순서다. `create`는 유일 위반을 바꾸지 않고 그대로 던지므로 이 순서를 어기지 않는다. 기간이 지나 닫힌 줄도 `revoked_at`이 찍힌다.
+- **토큰은 저장하지 않고 계산한다.** DB 에는 `public_id`(16바이트)만 있고 토큰은 `public_id + HMAC`(43글자)을 요청마다 다시 만든다(`domain/services/report_token.py`, 키는 `core/config.py`의 `REPORT_LINK_KEY`). 키를 바꾸면 모든 링크가 닫힌다. 토큰을 로그·문서·커밋에 남기지 않는다.
+- `PUT …/report` 하나가 처음 보내기·다시 공유·보낸 뒤 사진 빼기를 맡는다. `hidden_media_ids`는 "뺄 것 전부"다 — 목록에 없는 것은 앞서 뺐더라도 되살아난다. 빈 알림장(`REPORT_EMPTY`)은 링크를 새로 만들 때만 본다. 링크의 기간은 만들 때 정해지고 그 뒤 설정을 바꿔도 그대로다.
+- **뺀 사진 표시는 링크가 아니라 사진 줄에 붙는다**(`visit_record_media.hidden_from_report`). 링크를 끊고 새로 보내도 빠져 있다. 기록 저장이 미디어 줄을 지우고 다시 넣으므로 **기록 저장이 표시를 이어 붙인다** — 전체 교체는 `carry_hidden`, 덧붙이기는 `append_media`가 있던 미디어의 순서만 바꾼다. 새로 붙인 미디어는 보인다.
+- 알림장의 내용은 `app/services/report_reader.py` 한 곳이 조립한다(미리보기·보내기 응답·공개 조회가 함께 쓴다). 보이는 미디어의 순서(후 → 전)와 대표는 `report_rules.visible_media`·`report_cover_media_id`가 정한다 — 저장소가 주는 순서를 그대로 쓰지 않는다.
+- 알림장 설정(`GET·PUT /report-settings`)은 `visit_shop_settings`의 칸 다섯이다. 조회는 행을 만들지 않고 없으면 기본값을 준다. 수정은 `ScheduleRepository.ensure` 뒤에 쓴다 — 알림장 설정을 처음 저장하는 매장에는 일정 설정 행과 기본 메뉴가 함께 생긴다. 보여 줄 항목은 조회할 때마다 읽어 이미 보낸 알림장에도 바로 적용된다.
+- **살아 있는 링크가 있는 방문은 되돌리거나 기록을 지울 수 없다**(409 `VISIT_REPORT_SENT`). 되돌리기는 `CompletedState.revert`가 `Visit.has_live_report`를 보고, 기록 삭제는 인터랙터가 본다. 둘 다 **잠근 뒤에** 링크를 읽는다. 전이는 행동과 상관없이 링크를 한 번 읽는다(`live_visit_ids`).
+- 방문 상세에는 `report`(링크 상태), 하루 목록·피드의 항목에는 `report_sent`가 있다. 방문 여러 개의 링크는 `live_visit_ids`로 한 번에 읽는다. 달력은 바꾸지 않았다.
+- **익명화가 링크를 끊는다.** `clear_customer_memos`가 같은 트랜잭션에서 그 고객 방문의 끊지 않은 링크를 모두 끊는다(기간이 지난 줄도). 익명화한 고객의 방문에는 다시 보낼 수 없다 — 가족 잠금이 404 `CUSTOMER_NOT_FOUND`로 거절한다.
+- **공개 조회**(`GET /v1/public/report`, `POST /v1/public/report/viewed`)는 로그인이 없고 토큰을 헤더 `X-Report-Token`으로 받는다. 판정은 `app/services/public_report_gate.py` 한 곳이고 순서는 횟수 제한(429) → 서명(404, DB 를 읽지 않는다) → 링크 찾기(404) → 살아 있음(410) → 매장(410) → 기록(410)이다. 닫힌 이유는 가르지 않는다.
+- **공개 저장소만 `ShopContext`를 받지 않는다**(`PublicReportRepository.find`·`mark_viewed`). 서명을 확인한 `public_id`로만 부른다. `ShopContext`를 가드 없이 만드는 곳은 `app/services/public_context.py` 하나다 — 권한이 비어 있고 읽기에만 쓴다.
+- **공개 스키마는 매장용과 따로다**(`schemas/public_report_schema.py`). 칸을 하나하나 적고 ID·내부 메모·결제 수단·보호자 정보의 칸이 없다. 매장이 끈 항목은 null 이 아니라 칸이 없고, 켰지만 값이 없으면 null 이다. 새 칸을 더하는 것은 공개 범위를 넓히는 일이다.
+- 횟수 제한은 접속 주소별 분당 60회, 404 는 10분에 20회다(`adapter/outbound/redis/public_report_redis_limiter.py`, 조회와 열람 신호를 같은 통에 센다). 웹 서버가 알려 준 주소(`X-Report-Client-IP`)는 `X-Report-Web-Secret`이 맞을 때만 믿는다. **Redis 에 닿지 못하면 통과시키고** 경고를 남긴다 — 토큰 크기가 1차 방어다.
```

- [ ] **Step 2: 확인한다**

Run: 커밋할 파일에 비밀 흔적이 없는지 본다 — `git diff --cached | grep -nE "eyJ[A-Za-z0-9_-]{20,}|X-Amz-Signature=|BEGIN [A-Z ]*KEY|_B64=[A-Za-z0-9+/]{20,}"` → 출력 없음

Run (`infra/`): 단위 전체·통합 전체·구조 계약(Global Constraints 의 명령) → 수가 작업 8 뒤와 같다(문서는 코드를 바꾸지 않는다)

Run: `_docs/decisions/008-report.md` 의 API 계약 표의 경로·오류 코드를 라우트 표와 `backend/apps/visit/adapter/inbound/api/error_map.py` 에 대조한다 → 어긋남 없음

- [ ] **Step 3: 커밋한다**

```bash
git add -A
git commit -m "docs: ⑤-1 알림장 백엔드 — 스포크 규칙, 검증 장치, 결정 기록 008

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: 남은 경우 다섯을 테스트로 고정 — 되돌리는 동안 온 보내기, 익명화 뒤 보내기, 동시 열람 신호, 영상만 있는 알림장, 보낸 뒤 전부 빼기

**Files:**
- Modify: `_docs/decisions/008-report.md`
- Modify: `backend/apps/visit/tests/adapter/test_report_pg_repository.py`
- Modify: `backend/tests/integration/support.py`
- Modify: `backend/tests/integration/test_public_report_wiring.py`
- Modify: `backend/tests/integration/test_visit_report_locking.py`
- Modify: `backend/tests/integration/test_visit_report_wiring.py`

**Interfaces:**
- Consumes: 작업 6 의 보내기·끊기, 작업 7 의 되돌리기·기록 삭제·익명화, 작업 8 의 공개 조회·열람 신호, `tests/integration/support.py` 의 `ready_photo`·`upload_media`, `media_storage` 픽스처.
- Produces: 아래 그대로다(참조 구현에서 확인한 실제 시그니처).

```python
# tests/integration/support.py
VIDEO = {"kind": "video", "content_type": "video/mp4", "byte_size": 3000, "width": 1920, "height": 1080,
         "duration_seconds": 12}
async def ready_video(wired: Wired, shop_id: int, headers: dict) -> int    # media_storage 픽스처가 필요하다

# tests/integration/test_public_report_wiring.py
async def _completed_visit(wired, shop_id, headers, photos=0, phone=CUSTOMER["phone"], videos=0)
    # (방문 주소, 미디어 ID 목록(사진 뒤에 영상), 메뉴 이름)
```

머리말 Review Focus 의 다섯 줄이다. **구현을 바꾸지 않는다** — 작업 1~8 의 테스트가 다루지 않은 경우를 테스트로 고정한다. 구현이 이미 있으므로 새 테스트는 처음부터 통과해야 한다. **하나라도 실패하면 구현의 결함이다 — 구현을 고치거나 테스트를 느슨하게 하지 말고 멈춰서 보고한다.** 판별력은 Step 5 의 변이로 본다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_report_pg_repository.py`:

```diff
@@ -1,8 +1,10 @@
+import asyncio
 from datetime import timedelta
 
 import pytest
 from sqlalchemy import event
 from sqlalchemy.exc import IntegrityError
+from sqlalchemy.ext.asyncio import async_sessionmaker
 
 from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
 from visit.tests.helpers.builders import ctx, kst
@@ -190,6 +192,26 @@ async def test_처음_연_시각은_한_번만_적는다(db_session):
     assert (await repo.find(SECOND)).report.first_viewed_at is None
 
 
+async def test_두_세션이_동시에_처음_연_시각을_적어도_먼저_커밋한_것이_남는다(db_engine, db_session):
+    """R10 — '아직 비어 있을 때만'이라는 조건이 없으면 기다리던 쪽이 앞선 시각을 덮어쓴다."""
+    repo, visit_id = await _setup(db_session)
+    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
+    await db_session.commit()
+    early, later = NOW + timedelta(minutes=5), NOW + timedelta(hours=1)
+
+    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
+    async with sessions() as first, sessions() as second:
+        await ReportPgRepository(first).mark_viewed(created.id, early)
+        late = asyncio.create_task(ReportPgRepository(second).mark_viewed(created.id, later))
+        await asyncio.sleep(0.5)
+        assert not late.done()
+        await first.commit()
+        await late
+        await second.commit()
+
+    assert (await repo.find(FIRST)).report.first_viewed_at == early
+
+
 async def test_방문을_지우면_링크도_함께_지워진다(db_session):
     from sqlalchemy import delete
```

`backend/tests/integration/support.py`:

```diff
@@ -90,6 +90,8 @@ class FakeKakaoStrategy(SocialProviderPort):
 
 
 PHOTO = {"kind": "photo", "content_type": "image/jpeg", "byte_size": 3000, "width": 3000, "height": 2000}
+VIDEO = {"kind": "video", "content_type": "video/mp4", "byte_size": 3000, "width": 1920, "height": 1080,
+         "duration_seconds": 12}
 
 
 async def issue_media(wired: Wired, shop_id: int, headers: dict, body: dict = PHOTO) -> dict:
@@ -117,3 +119,12 @@ async def ready_photo(wired: Wired, shop_id: int, headers: dict) -> int:
     confirmed = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=headers)
     assert confirmed.status_code == 200, confirmed.text
     return issued["media_id"]
+
+
+async def ready_video(wired: Wired, shop_id: int, headers: dict) -> int:
+    """발급 → 원본과 포스터 올리기 → 확인까지 마친 영상 하나의 ID. `media_storage` 픽스처가 필요하다."""
+    issued = await issue_media(wired, shop_id, headers, VIDEO)
+    await upload_media(issued)
+    confirmed = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=headers)
+    assert confirmed.status_code == 200, confirmed.text
+    return issued["media_id"]
```

`backend/tests/integration/test_public_report_wiring.py`:

```diff
@@ -2,14 +2,18 @@
 
 검토 기준은 하나다 — 공개하기로 한 것 말고는 아무것도 나가지 않는다.
 """
+import asyncio
 import logging
+import re
 from datetime import datetime, timedelta
+from urllib.parse import urlsplit
 from zoneinfo import ZoneInfo
 
+import httpx
 import pytest
 from sqlalchemy import text
 
-from tests.integration.support import bearer, error_of, make_operator, ready_photo, shop_with_owner
+from tests.integration.support import bearer, error_of, make_operator, ready_photo, ready_video, shop_with_owner
 
 pytestmark = pytest.mark.integration
 
@@ -39,8 +43,11 @@ async def _shop(wired, name="Hiss Haus", owner_name="사장님"):
     return shop_id, bearer(owner["access_token"])
 
 
-async def _completed_visit(wired, shop_id, headers, photos=0, phone=CUSTOMER["phone"]):
-    """모든 칸을 채운 기록(후 사진 photos 장)을 남기고 완료한 콩이의 어제 방문. (방문 주소, 사진 ID 목록, 메뉴 이름)."""
+async def _completed_visit(wired, shop_id, headers, photos=0, phone=CUSTOMER["phone"], videos=0):
+    """모든 칸을 채운 기록(후 사진 photos 장, 영상 videos 편)을 남기고 완료한 콩이의 어제 방문.
+
+    (방문 주소, 미디어 ID 목록, 메뉴 이름)을 준다.
+    """
     family = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                   json={"customer": {**CUSTOMER, "phone": phone}, "pet": PET})
     assert family.status_code == 201, family.text
@@ -52,6 +59,7 @@ async def _completed_visit(wired, shop_id, headers, photos=0, phone=CUSTOMER["ph
     assert booked.status_code == 201, booked.text
     visit = f"/v1/shops/{shop_id}/visits/{booked.json()['visits'][0]['visit_id']}"
     media = [await ready_photo(wired, shop_id, headers) for _ in range(photos)]
+    media += [await ready_video(wired, shop_id, headers) for _ in range(videos)]
     bath = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=headers)).json()["items"][0]
     for action, body in (
         ("start", None),
@@ -230,6 +238,71 @@ async def test_다른_매장의_알림장과_섞이지_않는다(wired):
         ("A 매장", "눈물 자국을 닦았어요"), ("B 매장", "B 매장의 메모")]
 
 
+async def test_열람_신호가_동시에_둘_와도_둘_다_204_이고_시각은_하나다(wired):
+    """R10 — 동시에 온 둘 가운데 어느 시각이 남는지는 여기서 가릴 수 없다. 그 판별은 저장소의 두 세션 테스트가 한다.
+
+    여기서는 둘의 상태 코드와, 그 뒤에 온 신호가 남은 시각을 바꾸지 않는 것을 고정한다.
+    """
+    shop_id, o = await _shop(wired)
+    visit, _, _ = await _completed_visit(wired, shop_id, o)
+    token = await _send(wired, visit, o)
+
+    both = await asyncio.gather(wired.api.post(VIEWED, headers=_with(token)),
+                                wired.api.post(VIEWED, headers=_with(token)))
+
+    assert [r.status_code for r in both] == [204, 204]
+    seen_at = (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"]
+    assert seen_at is not None
+    assert (await wired.api.post(VIEWED, headers=_with(token))).status_code == 204
+    assert (await wired.api.get(f"{visit}/report", headers=o)).json()["link"]["first_viewed_at"] == seen_at
+    async with wired.engine.connect() as conn:
+        rows = (await conn.execute(text("SELECT first_viewed_at IS NOT NULL FROM visit_reports"))).all()
+    assert rows == [(True,)]
+
+
+async def test_영상만_있는_알림장은_포스터가_대표이고_원본으로_재생한다(wired, media_storage):
+    """영상에는 표시용이 없다 — 재생은 원본(mp4), 대표와 썸네일은 포스터다."""
+    shop_id, o = await _shop(wired)
+    visit, _, _ = await _completed_visit(wired, shop_id, o, videos=1)
+    token = await _send(wired, visit, o)
+
+    response = await wired.api.get(PUBLIC, headers=_with(token))
+
+    assert response.status_code == 200, response.text
+    [media] = response.json()["media"]
+    assert (media["kind"], media["duration_seconds"], media["width"], media["height"]) == ("video", 12, 1920, 1080)
+    paths = {k: urlsplit(media[k]).path for k in ("display_url", "thumb_url", "download_url")}
+    assert "/original-video/" in paths["display_url"] and paths["display_url"].endswith(".mp4")
+    assert "/thumb/" in paths["thumb_url"] and paths["thumb_url"].endswith(".jpg")
+    assert paths["download_url"] == paths["display_url"]
+    assert response.json()["cover"] == {"url": media["thumb_url"], "width": 1920, "height": 1080}
+    async with httpx.AsyncClient() as http:
+        played, saved = await http.get(media["display_url"]), await http.get(media["download_url"])
+    assert (played.status_code, saved.status_code) == (200, 200)
+    assert "content-disposition" not in played.headers
+    assert re.fullmatch(r'attachment; filename="chagocnote-\d+\.mp4"', saved.headers["content-disposition"])
+    assert saved.headers["content-type"] == "video/mp4"
+
+
+async def test_보낸_뒤_전부_빼고_메모를_비워도_공개_조회는_200_이다(wired, media_storage):
+    """살아 있는 링크가 있으면 REPORT_EMPTY 를 보지 않는다 — 페이지에는 이름과 날짜만 남는다."""
+    shop_id, o = await _shop(wired)
+    visit, [photo], _ = await _completed_visit(wired, shop_id, o, photos=1)
+    token = await _send(wired, visit, o)
+    emptied = await wired.api.put(
+        f"{visit}/record", headers=o,
+        json={"version": 1, "care_note": None, "media": [{"media_id": photo, "phase": "after", "sort_order": 0}]})
+    assert emptied.status_code == 200, emptied.text
+
+    assert await _send(wired, visit, o, hidden=[photo]) == token
+
+    response = await wired.api.get(PUBLIC, headers=_with(token))
+    assert response.status_code == 200, response.text
+    body = response.json()
+    assert (body["media"], body["cover"], body["care_note"]) == ([], None, None)
+    assert (body["pet_name"], body["visit_date"]) == ("콩이", YESTERDAY.isoformat())
+
+
 @pytest.mark.parametrize("headers", [
     {}, {"X-Report-Token": ""}, {"X-Report-Token": "a" * 42}, {"X-Report-Token": "a" * 44},
     {"X-Report-Token": "a" * 5000}, {"X-Report-Token": "알림장".encode()}, {"X-Report-Token": " "},
```

`backend/tests/integration/test_visit_report_locking.py`:

```diff
@@ -28,7 +28,7 @@ from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecord
 from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
 from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
 from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
-from visit.domain.errors import VisitReportSentError
+from visit.domain.errors import VisitNotCompletedError, VisitReportSentError
 from visit.tests.helpers.builders import ctx, kst, record
 from visit.tests.helpers.fakes import FakeShopProfile
 from visit.tests.helpers.rows import insert_visit
@@ -144,6 +144,25 @@ async def test_보내는_동안_온_되돌리기와_기록_삭제는_기다렸
     assert await _after(db_session, visit_id) == ("completed", True, [True])
 
 
+async def test_되돌리는_동안_온_보내기는_기다렸다가_VISIT_NOT_COMPLETED_로_끝난다(db_engine, db_session):
+    """R9 의 반대 방향 — 잠그지 않거나 잠그기 전에 읽은 방문으로 판정하면 '완료'를 본 채 되돌린 방문에 링크를 만든다."""
+    visit_id = await _recorded_visit(db_session)
+
+    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
+    async with sessions() as reverting, sessions() as second:
+        await _revert(reverting, visit_id)
+        late = asyncio.create_task(_send(second).send_visit_report(
+            SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=())))
+        await asyncio.sleep(BLOCKED)
+        assert not late.done()
+        await reverting.commit()
+        with pytest.raises(VisitNotCompletedError):
+            await late
+        await second.rollback()
+
+    assert await _after(db_session, visit_id) == ("reserved", True, [])
+
+
 async def test_보내는_동안_온_끊기는_기다렸다가_그_링크를_끊는다(db_engine, db_session):
     """끊기가 잠그지 않으면 아직 커밋되지 않은 링크를 보지 못해 REPORT_NOT_FOUND 로 끝나고 링크는 살아 있다."""
     visit_id = await _recorded_visit(db_session)
```

`backend/tests/integration/test_visit_report_wiring.py`:

```diff
@@ -291,6 +291,32 @@ async def test_고객을_삭제하면_그_고객의_알림장_링크가_끊긴
     assert rows == [(True,)]
 
 
+async def test_익명화한_고객의_방문에는_다시_보내지_못한다(wired):
+    """가족 잠금이 익명화한 고객을 거절한다 — 오류 코드는 VISIT_… 가 아니라 CUSTOMER_NOT_FOUND 다."""
+    shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
+    visit_id, _ = await _completed_visit(wired, shop_id, o)
+    visit = f"/v1/shops/{shop_id}/visits/{visit_id}"
+    assert (await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})).status_code == 200
+    customer_id = (await wired.api.get(visit, headers=o)).json()["visit"]["customer"]["customer_id"]
+    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204
+
+    seen = [
+        error_of(await wired.api.put(f"{visit}/report", headers=o, json={"hidden_media_ids": []})),
+        error_of(await wired.api.delete(f"{visit}/report", headers=o)),
+        error_of(await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o,
+                                      json={"visit_ids": [visit_id], "action": "revert"})),
+        error_of(await wired.api.delete(f"{visit}/record", headers=o)),
+    ]
+
+    assert seen == [(404, "CUSTOMER_NOT_FOUND")] * 4
+    async with wired.engine.connect() as conn:
+        live = (await conn.execute(text(
+            "SELECT count(*) FROM visit_reports WHERE visit_id = :id AND revoked_at IS NULL"), {"id": visit_id}))
+        assert live.scalar_one() == 0
+    detail = (await wired.api.get(visit, headers=o)).json()
+    assert (detail["visit"]["status"], detail["record"] is None, detail["report"]) == ("completed", False, NO_LINK)
+
+
 async def test_보낸_방문은_상세와_하루_목록과_피드에_보냄으로_나온다(wired):
     shop_id, _, o = await _shop(wired, await make_operator(wired), "Hiss Haus", "사장님")
     visit_id, _ = await _completed_visit(wired, shop_id, o)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

이 작업에는 RED 가 없다. 아래로 새 테스트가 **처음부터 통과**하는지 본다(구현 코드는 작업 1~8 에 있다).

Run (`infra/`): `docker compose run --rm backend pytest tests/integration/test_visit_report_locking.py tests/integration/test_visit_report_wiring.py tests/integration/test_public_report_wiring.py apps/visit/tests/adapter/test_report_pg_repository.py -q -p no:cacheprovider --tb=line` → 61 passed

- [ ] **Step 3: 구현한다**

`_docs/decisions/008-report.md`:

```diff
@@ -25,7 +25,7 @@
 
 ## ⑤-1 백엔드에서 정한 것
 
-visit 스포크에 알림장 링크(발급·끊기·미리보기), 알림장 설정, 공개 조회와 열람 신호, 횟수 제한. 허브 포트 `ShopProfilePort`(tenancy 구현)와 `MediaUrls.download_url`(media). 새 라우트 7개(설정 둘, 매장용 알림장 셋, 공개 둘 — 라우트 표의 나머지는 그대로), 마이그레이션 0010(`visit_reports`, `visit_record_media.hidden_from_report`, `visit_shop_settings`의 `report_*` 다섯 칸), 새 비밀값 `REPORT_LINK_KEY_B64`, 스크립트 `check_report_flow.sh`. 단위 883 → 1288, 통합 300 → 398, 구조 계약 6종. 새 의존성은 없다.
+visit 스포크에 알림장 링크(발급·끊기·미리보기), 알림장 설정, 공개 조회와 열람 신호, 횟수 제한. 허브 포트 `ShopProfilePort`(tenancy 구현)와 `MediaUrls.download_url`(media). 새 라우트 7개(설정 둘, 매장용 알림장 셋, 공개 둘 — 라우트 표의 나머지는 그대로), 마이그레이션 0010(`visit_reports`, `visit_record_media.hidden_from_report`, `visit_shop_settings`의 `report_*` 다섯 칸), 새 비밀값 `REPORT_LINK_KEY_B64`, 스크립트 `check_report_flow.sh`. 단위 883 → 1288, 통합 300 → 404, 구조 계약 6종. 새 의존성은 없다.
 
 ### 이 계획에서 새로 정한 것
 
@@ -76,7 +76,7 @@ visit 스포크에 알림장 링크(발급·끊기·미리보기), 알림장 설
 - 뺀 사진을 기록에서 지웠다가 다시 붙이면 다시 보인다(새로 붙인 사진으로 본다).
 - 살아 있는 링크가 있는 방문에 사진을 덧붙이면 바로 보호자에게 보인다.
 - 살아 있는 링크가 있으면 사진을 전부 빼거나 메모를 비워도 막지 않는다. 페이지는 이름과 날짜만 보인다.
-- 익명화한 고객의 방문에 다시 보내면 404 `CUSTOMER_NOT_FOUND`다(기존 가족 잠금이 거절한다). 코드가 `VISIT_…`가 아니다.
+- 익명화한 고객의 방문에 다시 보내면 404 `CUSTOMER_NOT_FOUND`다(기존 가족 잠금이 거절한다). 코드가 `VISIT_…`가 아니다. 그 방문의 끊기·되돌리기·기록 삭제도 같은 404 `CUSTOMER_NOT_FOUND`다(배선 테스트로 고정했다).
 - 조회와 열람 신호는 같은 통에 센다 — 페이지를 한 번 열면 요청이 둘이다.
 - 429 는 맞는 토큰에도 난다. 같은 접속 주소의 실패가 10분에 20번이면 그 주소의 모든 요청이 막힌다.
 - 웹 서버의 비밀값이 없으면 모든 보호자가 연결 주소 하나로 세어진다.
@@ -102,12 +102,12 @@ visit 스포크에 알림장 링크(발급·끊기·미리보기), 알림장 설
 - 기존 `.env`에 `IDENTITY_TOKEN_ENC_KEY`가 있다(인증 프로세스 전용이라 `.env.auth`에 있어야 한다). `.env.example`도 파일을 나누지 않았다. 이 계획 전부터 있던 상태다 — 운영 배포 전에 정리한다.
 - `REPORT_LINK_KEY_B64`는 필수다. 없으면 API·인증 프로세스 둘 다 기동하지 않는다. `generate_dev_env.py`는 `.env`가 있으면 아무것도 하지 않으므로 기존 개발 환경은 한 줄을 직접 더한다(명령은 `README.md`). 키가 base64 가 아니면 `RuntimeError`가 아니라 `binascii.Error`로 멈춘다.
 - 개발 DB 에 마이그레이션 0010 을 올려야 새 경로가 동작한다(compose 의 backend 가 기동할 때 올린다).
-- 돌려 보지 않은 경합: 되돌리는 동안 온 보내기(R9 의 반대 방향), 익명화와 보내기, 끊기를 동시에 두 번, 열람 신호의 동시 요청(두 세션). 모두 같은 잠금이나 조건부 UPDATE 에 기대므로 성립할 것이나 테스트는 없다.
+- 돌려 보지 않은 경합: 익명화와 보내기, 끊기를 동시에 두 번. 둘 다 같은 잠금에 기대므로 성립할 것이나 테스트는 없다. 되돌리는 동안 온 보내기(R9 의 반대 방향)와 열람 신호의 동시 요청은 두 세션 테스트로 고정했다.
 - 기록 삭제가 링크를 잠금 뒤에 읽는지는 경합 통합 테스트 하나만 잡는다.
 - 흐름 스크립트의 판별력(기대를 뒤집으면 그 단계에서 멈추는지)은 참조 구현에서 돌려 보지 못했다.
 - `GET /v1/shops/myself`·`GET /v1/auth/myself`가 로그인 없이 열려 있다(기존 동작, 목록에 고정했다). 의도한 것인지 확인하지 않았다.
 - 테스트 파일을 골라 돌릴 때 `tests/test_hub_port_binding.py`를 통합 파일 사이에 두면 `fixture 'wired' not found`다(전체 실행에는 없다, 원인 미조사).
-- 확인하지 못한 것: 실제 AWS S3 에서의 내려받기 서명, 브라우저의 실제 저장, 영상의 내려받기·공개 조회, 메뉴 항목이 있는 기록의 배선, 게이트웨이(Caddy) 접속 기록, 게이트웨이를 거친 흐름 스크립트, 실제 Redis 장애와 연결 시간 초과 동안의 대기.
+- 확인하지 못한 것: 실제 AWS S3 에서의 내려받기 서명, 브라우저의 실제 저장, 메뉴 항목이 있는 기록의 배선, 게이트웨이(Caddy) 접속 기록, 게이트웨이를 거친 흐름 스크립트, 실제 Redis 장애와 연결 시간 초과 동안의 대기.
 - 운영에서 OpenAPI 문서(`/docs`)에 공개 경로가 보이는지 정하지 않았다.
 - 하루 목록·피드·상세·전이는 질의가 하나씩 늘었다. 실행 계획과 시간은 재지 않았다. `visit_reports.visit_id`에는 부분 유일 색인만 있다 — 끊은 줄까지 방문으로 찾는 질의가 생기면 색인을 더한다.
 - 두 사장이 동시에 설정을 바꾸면 늦은 쪽이 덮는다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

| 대상 | 결과 |
|---|---|
| 이 작업의 네 파일 | 61 passed (경합 5, 매장 배선 12, 공개 배선 27, 저장소 17) |
| 단위 전체 | 1288 passed, 404 deselected (시작 1288 → 그대로) |
| 통합 전체 | 404 passed, 1288 deselected (시작 398 → +6) |
| 구조 계약 | 6 kept, 0 broken |


더한 테스트
1. `test_visit_report_locking.py::test_되돌리는_동안_온_보내기는_기다렸다가_VISIT_NOT_COMPLETED_로_끝난다` — `VisitNotCompletedError`, 그 뒤 DB 는 `("reserved", 기록 있음, 링크 줄 없음)`.
2. `test_visit_report_wiring.py::test_익명화한_고객의_방문에는_다시_보내지_못한다`
3. `test_public_report_wiring.py::test_열람_신호가_동시에_둘_와도_둘_다_204_이고_시각은_하나다`, `test_report_pg_repository.py::test_두_세션이_동시에_처음_연_시각을_적어도_먼저_커밋한_것이_남는다`
4. `test_public_report_wiring.py::test_영상만_있는_알림장은_포스터가_대표이고_원본으로_재생한다`
5. `test_public_report_wiring.py::test_보낸_뒤_전부_빼고_메모를_비워도_공개_조회는_200_이다`

### 익명화한 고객의 방문 — 실제로 본 값

고객을 삭제한 뒤 같은 방문에 보낸 요청 넷이 모두 같다.

| 요청 | 상태 | 코드 |
|---|---|---|
| `PUT …/report` (보내기) | 404 | `CUSTOMER_NOT_FOUND` |
| `DELETE …/report` (끊기) | 404 | `CUSTOMER_NOT_FOUND` |
| `POST …/visits/transitions` `revert` (되돌리기) | 404 | `CUSTOMER_NOT_FOUND` |
| `DELETE …/record` (기록 삭제) | 404 | `CUSTOMER_NOT_FOUND` |

그 방문의 끊지 않은 줄은 0, 방문은 `completed` 그대로, 기록은 남아 있고, 상세의 `report` 는 `none` 이다. T7 의 짐작("404 일 것이다")이 맞았다.

### 영상 — 실제로 본 값

`media` 하나, `kind == "video"`, `duration_seconds == 12`, 가로·세로 1920×1080(선언한 값). `display_url` 의 경로는 `/original-video/` 아래 `.mp4`, `thumb_url` 은 `/thumb/` 아래 `.jpg`, `download_url` 의 경로는 `display_url` 과 같다. `cover` 는 `{url: thumb_url 과 같은 글자, width: 1920, height: 1080}`. 두 주소로 실제 GET: 둘 다 200, `display_url` 응답에는 `Content-Disposition` 이 없고 `download_url` 응답은 `attachment; filename="chagocnote-<숫자>.mp4"`, `Content-Type: video/mp4`(테스트 버킷 MinIO).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `SendVisitReportInteractor` 의 `lock_visits` 를 `self._visits.get_many` 로(잠그지 않는다) → `test_되돌리는_동안_온_보내기는_…` — `DID NOT RAISE VisitNotCompletedError`(`pytest.raises` 줄). 기존 `test_같은_방문에_동시에_두_번_보내도_…` 도 실패(유일 색인 위반)
- 잠그기 전에 읽은 방문으로 `check_sendable` 을 부른다(잠금은 그대로) → `test_되돌리는_동안_온_보내기는_…` 하나 — `DID NOT RAISE`
- `mark_viewed` 의 `first_viewed_at IS NULL` 조건 삭제 → 저장소 `test_두_세션이_동시에_…`(남은 값이 늦은 시각), 기존 `test_처음_연_시각은_한_번만_적는다`, 배선 `test_열람_신호가_동시에_둘_와도_…`, 기존 `test_보내고_열고_끊고_다시_보낸다`
- `report_reader` 의 영상 `display_url` 에서 `or original_url` 삭제 → `test_영상만_있는_알림장은_…` — 보내기(PUT)에서 응답 스키마 검증 오류
- 대표의 주소를 `display_url or original_url` 로 → `test_영상만_있는_알림장은_…` — `cover` 단언
- 살아 있는 링크가 있어도 `check_not_empty` 를 부른다 → `test_보낸_뒤_전부_빼고_…` — 두 번째 보내기가 422 `REPORT_EMPTY`

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "test(visit): 알림장의 남은 경우 다섯 — 되돌리는 동안 온 보내기, 익명화 뒤 보내기, 동시 열람 신호, 영상만 있는 알림장, 보낸 뒤 전부 빼기

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---
