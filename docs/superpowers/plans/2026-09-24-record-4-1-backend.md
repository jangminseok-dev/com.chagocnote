# 차곡노트 ④ 미용 기록·피드 뷰 — 계획 ④-1 백엔드: media 스포크·미용 기록·피드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장이 미용 기록(사진·영상·몸무게·실제 메뉴와 금액·결제·메모)을 저장하고, 방문 상세·하루·달력·피드·반려동물 프로필에서 대표 사진과 함께 보게 한다 — 파일은 서버를 거치지 않고 앱이 저장소(S3·MinIO)에 바로 올린다.

**Architecture:** 새 스포크 `media`가 사진·영상 객체의 메타데이터(`media_objects`)를 갖고, 발급(서명 PUT URL)·확인(HEAD 대조)과 허브 포트 `MediaLibraryPort`(가져가기·놓기·읽기 URL)를 낸다. `visit`은 기록 표 셋(`visit_records`·항목·미디어 연결)을 갖고 전체 교체(버전)·덧붙이기·삭제와 읽기 넓히기(상세·하루·달력·피드)를 한다. `customer`는 허브 포트로 프로필 사진을 읽고, 기록의 몸무게를 현재 몸무게로 받는다. 스포크끼리는 허브 포트로만 만난다. 모든 코드는 참조 작업 트리(`.superpowers/ref/wt-record-4-1-be`, 브랜치 `ref/record-4-1-be`, 커밋 09fe19b…b6b2fc1)에서 먼저 돌려 검증했고, 변이 41개로 판별력을 확인했다.

**Tech Stack:** Python 3.13 · FastAPI 0.141 · SQLAlchemy 2.0(asyncio) · Alembic · pytest · import-linter · **boto3 1.43(새 의존성)** · MinIO(compose, 이미 있음).

**Spec:** `docs/superpowers/specs/2026-09-24-record-media-design.md` — 이 계획은 5절(백엔드 구조), 6절(데이터 모델), 7절(업로드 흐름), 8절(동작 규칙), 9절(API), 12절(위협 점검표), 13절의 "백엔드 ④-1", 14절의 "④-1 백엔드"다. 10.2절(업로드 대기열)이 요구하는 서버 쪽(덧붙이기·기록 버전)도 이 계획이 만든다. 실행자는 설계 문서와 함께 `_docs/architecture.md`, `_docs/harness.md`, `backend/apps/{hub,visit,customer}/_docs/CLAUDE.md`, `_docs/decisions/002-hub-port-assembly.md`·`006-visit-reservation.md`·`007-record-media.md`를 읽는다.

**계획의 위치:** ④의 구현 계획 다섯 가운데 셋째다. ④-0 백엔드·④-0 앱(완료, main) → **④-1 백엔드(이 문서)** → ④-2 앱(업로드 대기열·기록 화면·피드) → ④-3 영상·음성. ④-2 는 이 계획의 API(발급·확인·기록 PUT/덧붙이기/DELETE·피드·`cover`·`photo`)와 오류 코드에 기댄다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 백엔드 명령은 `infra/`에서 돌린다. 맥에 파이썬 환경을 만들지 않는다.
- 작업 브랜치는 `feat/record-4-1-backend`다(main `bb09052`에서 땄고, 설계 문서 고침과 이 계획서가 첫 커밋이다). `main`에서 직접 작업하지 않는다.
- **사용자가 작업 단위 커밋을 허용했다(2026-09-22 이후 계속).** 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.**
- 계획서의 코드 블록은 그대로 옮긴다. 새 파일은 전문이고, 수정 파일은 diff 다. diff 가 적용되지 않으면 멈추고 보고한다 — 손으로 "비슷하게" 고치지 않는다.
- **작업 2 가 `boto3`를 더한다 — 그 작업에서 이미지를 다시 빌드한다**(`docker compose build backend auth`). 그 뒤의 모든 명령은 새 이미지로 돈다.
- 통합 테스트는 compose 의 MinIO 를 쓴다(작업 2 가 `backend`의 `depends_on`에 `minio`를 더한다). 테스트 버킷은 `chagocnote-test`다 — 개발 버킷을 건드리지 않는다.
- 볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다. 마이그레이션 셋(0007~0009)은 모두 더하기만 한다.
- 비밀값·토큰·서명 URL·고객 개인정보를 로그에 남기지 않는다. 이 계획은 로그 코드를 더하지 않는다(자기소개 기록은 주제만 남긴다).
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (`_docs/architecture.md`, 스포크 `CLAUDE.md` 그대로 — 이 계획이 문서에 더하는 규칙 포함)
- 스포크끼리 직접 import 하지 않는다. `media`는 어떤 스포크도, 어떤 허브 포트도 쓰지 않는다. 허브 포트 자리는 소비 스포크의 `dependencies/hub_ports.py`에 두고 `main.py`가 꽂는다(visit·customer 가 각자 `get_media_library` 자리를 가진다 — `main.py`는 별칭으로 둘을 구분한다).
- 허브 포트가 던지는 오류는 `hub/app/errors.py`의 `HubPortError` 하위 타입뿐이다. 새 허브 오류는 `core/hub_errors.py`에 상태를 적는다.
- 도메인(`*/domain`)은 표준 라이브러리만 import 한다. `media.app`·`media.domain`도 framework-isolation 계약을 따른다(`boto3`·`sqlalchemy`는 어댑터에만).
- **잠금 순서: 기록 쓰기는 방문 쓰기와 같다** — `CustomerDirectoryPort.lock_family`(고객 행) → 방문 행 `FOR UPDATE` → 다시 읽어 판정(`visit_locking.lock_visits`). 미디어 가져가기·놓기는 조건부 UPDATE 라 잠금 안에서 부른다. 저장소(S3) 호출은 잠금을 쥔 채 하지 않는다.
- 방문 리포지토리 포트는 여섯 축이 된다(작업 9 가 `VisitFeedRepository`를 더한다). 유스케이스는 자기가 부르는 포트만 받는다.
- 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC 를 상속한다. 허브 포트 스텁은 실제 구현과 같은 허브 오류를 같은 조건에서 던진다.

입력 경계 (설계 9절 — 넘으면 422)
- 금액(`total_amount`·항목 `amount`·메뉴 `price`) 0 ~ 100,000,000 · 몸무게 0.1 ~ 999.9(소수 한 자리) · `sort_order` 0 ~ 99 · 메모 1000자 · 미디어 목록 33개 · 항목 30개 · 피드 `limit` 1 ~ 50 · 경로 ID 는 bigint 범위(`MediaId`·`VisitId`) · `phase`·`payment_method`·`kind`는 Literal · 발급의 가로세로 1 ~ 32,767(도메인은 10,000 까지) · 방문당 사진 30장·영상 3편(422 `MEDIA_LIMIT_EXCEEDED`).

검증 명령 (`infra/`에서)
- 단위: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` — 시작 767 → 끝 882
- 통합(실제 Postgres·Redis·MinIO): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` — 시작 264 → 끝 299
- 구조 계약: `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken(계약 수는 늘지 않는다 — 작업 1 이 모든 계약에 `media`를 더한다)
- 라우트 표: `docker compose run --rm --no-deps auth python scripts/print_routes.py` — 작업 1 전에 파일로 받아 두고 작업 12 뒤에 `diff` 한다. 늘어나는 줄은 일곱 뿐이다(media 셋, visit 넷)
- 파일 몇 개만: `docker compose run --rm --no-deps backend pytest <경로들> -q -p no:cacheprovider`(통합 표시가 있는 파일은 `--no-deps` 없이)
- **시각 의존 테스트 하나:** `tests/integration/test_visit_flow_wiring.py::test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다`는 밤 22시 반 이후(한국 시각) 실패한다 — 걷기 손님 기본 90분이 자정을 넘긴다. ③부터 있던 것이고 이 계획이 건드리지 않는다. 그 시간에 돌렸다면 그 하나를 빼고 수를 센다.
- 참조 브랜치와 대조(선택, 마지막에): `git diff ref/record-4-1-be -- backend _docs infra` 가 비어 있어야 한다.

## 이 계획에서 새로 정한 것

설계와 다른 것과 새로 정한 것은 결정 기록 007 의 ④-1 절(작업 12)에 적는다. 요약:
- 빠진 미디어는 놓기만 하고, 정리 스크립트가 하루 뒤 지운다 — `MediaLibraryPort`에 `discard`가 없다(설계 8절의 "커밋 뒤 discard" 대신).
- 객체 키는 렌디션이 앞이다(`original/shops/{매장}/{ID}.jpg` 등) — S3 수명주기가 접두사로만 거른다.
- 읽기 서명은 표준 라이브러리로 직접 만든다(서명 시각 = 매장 시간대 가장 최근 04:00, 48시간) — botocore 와 글자까지 같은지 테스트한다.
- 설정 이름은 기존 `.env`의 `S3_*` + `S3_PUBLIC_ENDPOINT_URL`·`S3_REGION`.
- `claim`이 `{id: kind}`를 돌려주고 visit 이 `visit_record_media.kind`에 적는다(대표 사진·한도를 visit 표만으로).
- `set_pet_weight(ctx, pet_id, weight_kg)` — `at` 없음.
- 기록 삭제는 `record:delete`(권한 시드를 따른다). 메뉴 정가 CHECK 는 0~1억, `PUT /menus/{id}`의 `price`는 빠지면 미정.
- 프로필 사진(`photo`)은 조회 응답 셋에만. "사진이 붙은 가장 최근 완료 방문의 대표"다.
- 기록 여러 개는 `list_many`가 질의 셋으로 읽는다. 피드는 방문 리포지토리의 여섯째 축.

## 위협 점검표 (설계 12절 — 행마다 막는 코드와 테스트)

작업별 검토는 계획서와의 일치가 아니라 이 표를 기준으로 한다.

| # | 시나리오 | 막는 코드 | 테스트 |
|---|---|---|---|
| M1 | 다른 매장의 미디어 ID 를 기록에 붙인다 | `MediaPgRepository.attach_all`의 `shop_id` 조건 + 개수 불일치 → `MediaClaimNotFoundError`(404) (작업 4) | `test_media_library_interactor.py::test_하나라도_안_되면…`[shop 2], `test_visit_record_wiring.py::test_다른_매장의_방문과_미디어로는…`(404 `MEDIA_NOT_FOUND`) |
| M2 | 서명 URL 로 다른 키·다른 형식을 쓴다 | 서명에 키와 Content-Type 이 든다 (작업 2) | `test_boto3_object_storage_adapter.py::test_서명과_다른_형식으로…`(403), `check_media_flow.sh` |
| M3 | 확인 안 한 객체를 붙인다 | `attach_all`은 `status='ready'`만 → `MediaClaimNotReadyError`(409) (작업 4) | `test_media_library_interactor.py`[pending], `test_append_record_media_interactor.py::test_시작하지_않은_방문이나_준비_전_미디어는…` |
| M4 | 같은 객체를 두 기록에 붙인다 | `attached_at IS NULL` 조건부 UPDATE(작업 4) + `visit_record_media.media_id` 유일(작업 6) | `test_media_library_pg.py::test_같은_미디어를_동시에_가져가면…`(두 세션), `test_visit_record_pg_repository.py::test_한_미디어는_한_기록에만…`, 통합 `MEDIA_ALREADY_ATTACHED` |
| M5 | 한도 넘는 파일을 올린다 | 확인의 HEAD 크기·형식 검사, 넘으면 객체 삭제 + 422 (작업 3) | `test_confirm_upload_interactor.py::test_한도를_넘거나_형식이_다르면…`·`test_썸네일도_JPEG…` |
| M6 | 발급만 하고 안 올린다·앱이 죽는다 | `purge_stale_media.py`의 ① pending 24시간 (작업 11) | `test_purge_stale_media.py::test_하루_넘은_pending_과…` |
| M7 | 기록 저장과 되돌리기·익명화·무지개다리가 겹친다 | 쓰기 셋 모두 `lock_visits`(고객 행 → 방문 행) 뒤 다시 읽은 상태로 판정 (작업 6·7) | `test_visit_record_locking.py::test_같은_버전으로_동시에_두_번…`(두 세션, 잠금을 빼면 실패), 인터랙터 `FamilyNotFoundError` 테스트 |
| M8 | `sales:write` 없는 멤버가 돈 칸을 보낸다 | `PutVisitRecordInteractor`가 잠그기 전에 403 (작업 6) | `test_put_visit_record_interactor.py::test_돈_칸은_sales_write_가_없으면…` |
| M9 | 내보내진 멤버가 쥔 토큰으로 올린다 | 새 경로 일곱 모두 `require_permission`/`get_shop_context`(매 요청 DB 조회, 기존) | `tests/test_hub_port_binding.py`(라우트 구조 검사), 통합 격리 테스트 셋 |
| M10 | 읽기 URL 이 유출된다 | 서명 URL, 최대 48시간 (작업 1·2) | `test_url_expiry.py::test_남은_유효_시간은_24시간에서_48시간이다` |
| M11 | EXIF 의 GPS 가 남는다 | 앱이 제거(④-2). 서버는 디코딩하지 않는다 | — (④-2·⑤) |
| M12 | 입력 경계(위 "입력 경계", 파이썬/DB 범위 끝) | 스키마 `Field`·Literal·bigint 경로·피드 커서 시간대 (작업 3·5·6·7·9) | 라우터 테스트의 422 목록(`test_issue_upload_router`·`test_update_menu_router`·`test_put_visit_record_router`·`test_append_record_media_router`·`test_list_visit_feed_router`), `test_피드_커서가_틀리면_VisitInputError` |
| M13 | 확인이 동시에 두 번 온다 | `mark_ready`의 `status='pending'` 조건부 UPDATE, 이미 ready 면 그대로 (작업 1·3) | `test_media_flow_wiring.py::test_동시에_두_번_확인해도…`, `test_준비는_한_번만_바뀐다` |
| M14 | 옛 방문의 기록 편집이 현재 몸무게를 덮는다 | `sync_pet_weight` — 가장 최근 시작한 방문일 때만, 고객 행 잠금 안 (작업 6) | `test_sync_pet_weight.py`, `test_옛_방문의_기록을_고치면…` |
| M15 | 저장소 삭제 실패로 고아가 남는다 | 정리 스크립트가 표시(pending) → 저장소 → 행 순서, 중단되면 다음 실행이 잡는다 (작업 11) | `test_purge_stale_media.py::test_저장소_삭제_중에_멈춰도…`, `test_고른_뒤_기록이_가져간_미디어는_건너뛴다` |
| M16 | 익명화한 고객의 기록 메모에 개인정보가 남는다 | `clear_customer_memos`가 `clear_notes`도 부른다 (작업 10) | `test_visit_ledger_interactor.py::test_익명화는_방문_메모와…`, 통합 `test_프로필_사진은…익명화하면…` |
| M17 | 기록 삭제와 크게 보기·저장이 겹친다 | 삭제 뒤 PUT 은 버전이 맞지 않아 409, 덧붙이기는 새 기록 — 무해 | `test_버전은_없을_때_보내지_않고…` |
| M18 | 업로드 중인 앱을 죽이고 다시 연다 | 덧붙이기 멱등(같은 미디어면 바꾸지 않음), 하루 지난 객체는 정리돼 claim 404 → 앱이 재발급 (작업 7·4) | `test_append_record_media_interactor.py::test_이미_붙은_미디어면…`, 통합 "다시 보내도 한 번" |
| M19 | 폼이 읽은 뒤 대기열이 사진을 붙이고 폼이 저장해 그 사진을 지운다 | 기록 버전 — 잠근 뒤 다시 읽은 버전으로 409 `RECORD_VERSION_CONFLICT` (작업 6·7) | `test_visit_record_wiring.py::test_덧붙이기는_기록을_만들고…`(stale PUT 409), `test_버전이_어긋나면_아무것도_가져가지_않는다` |

## Review Focus

설계가 말하지만 사람이 쓰다 가장 먼저 부딪힐 입력 다섯. 각 줄의 테스트를 해당 작업에 넣었다.
1. **대기열이 응답을 못 받고 같은 사진을 다시 덧붙인다** — 한 번만 붙고 버전도 그대로여야 한다 → 작업 7 `test_이미_붙은_미디어면_아무것도_바꾸지_않는다`, 통합 `test_덧붙이기는_기록을_만들고_다시_보내도_한_번이며…`.
2. **폼을 연 채로 대기열이 사진을 붙인 뒤 폼을 저장한다** — 사진이 사라지지 않고 409 로 알려야 한다 → 작업 7 통합(stale PUT 409), 작업 6 `test_버전이_어긋나면…`.
3. **지난 방문의 기록을 고친다(몸무게 오타)** — 현재 몸무게는 그대로여야 한다 → 작업 6 `test_옛_방문의_기록을_고치면_현재_몸무게는_그대로다`.
4. **사진 없는 완료 방문·기록 없는 방문** — 피드·달력·상세가 빈 대표 사진(null)으로 보여야 하고 오류가 나면 안 된다 → 작업 8 `test_기록이_없으면_record_와_cover_가_비어_있다`·`test_기록이_있는지와_대표_사진을_준다`, 작업 9 피드 카드(`cover` None, 예약 메뉴로 대신).
5. **하루 넘게 오프라인이던 기기의 사진** — 정리된 객체를 붙이면 404 `MEDIA_NOT_FOUND`로 알려 앱이 발급부터 다시 하게 한다 → 작업 4 `test_없는_ID_는_NOT_FOUND_다`, 작업 11 `test_하루_넘은_pending_과…`.

---
### Task 1: media 스포크의 도메인과 표 — 받는 형식·한도·키 규칙, 읽기 서명 창, `media_objects`(0007)와 저장소

**Files:**
- Create: `backend/apps/media/domain/errors.py`
- Create: `backend/apps/media/domain/services/media_rules.py`
- Create: `backend/apps/media/domain/services/url_expiry.py`
- Create: `backend/apps/media/domain/entities/media_object.py`
- Create: `backend/apps/media/domain/value_objects/new_media.py`
- Create: `backend/apps/media/adapter/outbound/orm/media_orm.py`
- Create: `backend/alembic/versions/0007_media_objects.py`
- Modify: `backend/orm_registry.py`
- Create: `backend/apps/media/app/ports/output/media_repository.py`
- Modify: `backend/.importlinter`
- Create: `backend/apps/media/__init__.py`
- Create: `backend/apps/media/adapter/__init__.py`
- Create: `backend/apps/media/adapter/inbound/__init__.py`
- Create: `backend/apps/media/adapter/inbound/api/__init__.py`
- Create: `backend/apps/media/adapter/inbound/api/schemas/__init__.py`
- Create: `backend/apps/media/adapter/inbound/api/v1/__init__.py`
- Create: `backend/apps/media/adapter/outbound/__init__.py`
- Create: `backend/apps/media/adapter/outbound/mappers/__init__.py`
- Create: `backend/apps/media/adapter/outbound/mappers/media_mapper.py`
- Create: `backend/apps/media/adapter/outbound/orm/__init__.py`
- Create: `backend/apps/media/adapter/outbound/pg/__init__.py`
- Create: `backend/apps/media/adapter/outbound/pg/media_pg_repository.py`
- Create: `backend/apps/media/app/__init__.py`
- Create: `backend/apps/media/app/dtos/__init__.py`
- Create: `backend/apps/media/app/ports/__init__.py`
- Create: `backend/apps/media/app/ports/input/__init__.py`
- Create: `backend/apps/media/app/ports/output/__init__.py`
- Create: `backend/apps/media/app/use_cases/__init__.py`
- Create: `backend/apps/media/dependencies/__init__.py`
- Create: `backend/apps/media/domain/__init__.py`
- Create: `backend/apps/media/domain/entities/__init__.py`
- Create: `backend/apps/media/domain/services/__init__.py`
- Create: `backend/apps/media/domain/value_objects/__init__.py`
- Create: `backend/apps/media/tests/__init__.py`
- Create: `backend/apps/media/tests/adapter/__init__.py`
- Create: `backend/apps/media/tests/adapter/test_media_pg_repository.py`
- Create: `backend/apps/media/tests/app/__init__.py`
- Create: `backend/apps/media/tests/app/use_cases/__init__.py`
- Create: `backend/apps/media/tests/domain/__init__.py`
- Create: `backend/apps/media/tests/domain/test_media_rules.py`
- Create: `backend/apps/media/tests/domain/test_url_expiry.py`
- Create: `backend/apps/media/tests/helpers/__init__.py`
- Create: `backend/apps/media/tests/helpers/builders.py`

**Interfaces:**
- Consumes: `hub.app.dtos.shop_context.ShopContext`, `core.database.Base`, 마이그레이션 0006(`down_revision`), `orm_registry.py`, `.importlinter`.
- Produces: `media.domain.errors` — `MediaError`와 하위 `MediaNotFoundError`(MEDIA_NOT_FOUND)·`MediaNotUploadedError`(MEDIA_NOT_UPLOADED)·`MediaTooLargeError`(MEDIA_TOO_LARGE)·`MediaTypeUnsupportedError`(MEDIA_TYPE_UNSUPPORTED)·`MediaInputError`(VALIDATION_ERROR); `media.domain.services.media_rules` — `PHOTO`·`VIDEO`·`CONTENT_TYPE`·`MAX_BYTES`·`MAX_VIDEO_SECONDS=60`, `MediaKeys(original, display, thumb).all()`, `object_keys(shop_id, media_id, kind) -> MediaKeys`, `check_upload(kind, content_type, byte_size, width, height, duration_seconds)`, `check_size(kind, byte_size)`; `media.domain.services.url_expiry` — `SigningWindow(signed_at, expires_in_seconds).expires_at`, `signing_window(now, tz) -> SigningWindow`; `media.domain.entities.media_object` — `PENDING`·`READY`, `MediaObject(… keys: MediaKeys …).ready`; `media.domain.value_objects.new_media.NewMedia`; `media.app.ports.output.media_repository.MediaRepository` — `create(ctx, new) -> MediaObject`, `get(ctx, media_id) -> MediaObject`(없으면 `MediaNotFoundError`), `mark_ready(ctx, media_id, size_bytes) -> bool`; `media.adapter.outbound.pg.media_pg_repository.MediaPgRepository`; 테스트 도우미 `media.tests.helpers.builders`(`ctx`, `new_photo`, `new_video`).

새 스포크 `media`의 뼈대다(설계 5.1·6.1·7.2·7.3). 폴더는 다른 스포크와 같다(`domain/{entities,services,value_objects}`, `app/{ports,use_cases,dtos}`, `adapter/{inbound,outbound}`, `dependencies`, `tests`) — 빈 `__init__.py`를 모든 폴더에 둔다(아래 목록의 `__init__.py`는 빈 파일이다). **설계와 다른 점**(결정 기록 007): 객체 키는 렌디션이 앞이다(`original/shops/{매장}/{ID}.jpg`·`original-video/…mp4`·`display/…`·`thumb/…`) — S3 수명주기 규칙이 접두사로만 거르므로(작업 2 의 버킷 준비 스크립트) 원본이 한 접두사 아래 모여야 한다. 키가 ID 를 품으므로 `create`는 시퀀스에서 ID 를 먼저 받는다. `.importlinter`의 모든 계약에 `media`를 더한다(`media.app`·`media.domain`은 프레임워크 격리, `media.domain`은 도메인 순수성).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/media/tests/__init__.py`:

```python

```

`backend/apps/media/tests/adapter/__init__.py`:

```python

```

`backend/apps/media/tests/adapter/test_media_pg_repository.py`:

```python
import pytest

from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.domain.errors import MediaNotFoundError
from media.tests.helpers.builders import ctx, new_photo, new_video

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def test_발급한_미디어는_pending_이고_키가_ID_를_품는다(db_session):
    photo = await MediaPgRepository(db_session).create(A, new_photo())
    video = await MediaPgRepository(db_session).create(A, new_video())
    assert (photo.status, photo.keys.original, photo.keys.display, photo.size_bytes, photo.ready_at) == (
        "pending", f"original/shops/1/{photo.id}.jpg", f"display/shops/1/{photo.id}.jpg", None, None)
    assert (video.keys.original, video.keys.display, video.duration_seconds) == (
        f"original-video/shops/1/{video.id}.mp4", None, 42)


async def test_다른_매장의_미디어는_없는_것이다(db_session):
    photo = await MediaPgRepository(db_session).create(A, new_photo())
    with pytest.raises(MediaNotFoundError):
        await MediaPgRepository(db_session).get(B, photo.id)
    assert await MediaPgRepository(db_session).mark_ready(B, photo.id, 100) is False


async def test_준비는_한_번만_바뀐다(db_session):
    repo = MediaPgRepository(db_session)
    photo = await repo.create(A, new_photo())
    assert await repo.mark_ready(A, photo.id, 1234) is True
    assert await repo.mark_ready(A, photo.id, 9999) is False
    ready = await repo.get(A, photo.id)
    assert (ready.status, ready.size_bytes, ready.ready_at is not None) == ("ready", 1234, True)
```

`backend/apps/media/tests/app/__init__.py`:

```python

```

`backend/apps/media/tests/app/use_cases/__init__.py`:

```python

```

`backend/apps/media/tests/domain/__init__.py`:

```python

```

`backend/apps/media/tests/domain/test_media_rules.py`:

```python
import pytest

from media.domain.errors import MediaInputError, MediaTooLargeError, MediaTypeUnsupportedError
from media.domain.services.media_rules import MAX_BYTES, check_upload, object_keys

MB = 1024 * 1024


def test_사진은_원본_표시용_썸네일_세_키를_갖는다():
    keys = object_keys(7, 42, "photo")
    assert keys.all() == ("original/shops/7/42.jpg", "display/shops/7/42.jpg", "thumb/shops/7/42.jpg")


def test_영상은_원본과_포스터_두_키를_갖는다():
    keys = object_keys(7, 43, "video")
    assert (keys.display, keys.all()) == (None, ("original-video/shops/7/43.mp4", "thumb/shops/7/43.jpg"))


def test_받는_선언값():
    check_upload("photo", "image/jpeg", 20 * MB, 3000, 2000, None)
    check_upload("video", "video/mp4", 200 * MB, 1920, 1080, 60)


@pytest.mark.parametrize("kind, content_type", [
    ("photo", "image/heic"), ("photo", "video/mp4"), ("video", "video/quicktime"), ("audio", "audio/mpeg"),
])
def test_종류와_형식이_맞지_않으면_MEDIA_TYPE_UNSUPPORTED(kind, content_type):
    with pytest.raises(MediaTypeUnsupportedError):
        check_upload(kind, content_type, MB, 100, 100, 10 if kind == "video" else None)


@pytest.mark.parametrize("kind, size", [("photo", 20 * MB + 1), ("video", 200 * MB + 1), ("photo", 0)])
def test_한도_밖의_크기는_MEDIA_TOO_LARGE(kind, size):
    content_type = "image/jpeg" if kind == "photo" else "video/mp4"
    with pytest.raises(MediaTooLargeError):
        check_upload(kind, content_type, size, 100, 100, 10 if kind == "video" else None)


def test_한도는_종류마다_다르다():
    assert MAX_BYTES == {"photo": 20 * MB, "video": 200 * MB}


@pytest.mark.parametrize("kind, width, height, duration", [
    ("photo", 0, 100, None), ("photo", 100, 10_001, None), ("photo", 100, 100, 5),
    ("video", 100, 100, None), ("video", 100, 100, 0), ("video", 100, 100, 61),
])
def test_가로세로와_길이의_경계(kind, width, height, duration):
    content_type = "image/jpeg" if kind == "photo" else "video/mp4"
    with pytest.raises(MediaInputError):
        check_upload(kind, content_type, 1000, width, height, duration)
```

`backend/apps/media/tests/domain/test_url_expiry.py`:

```python
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from media.domain.services.url_expiry import signing_window

SEOUL = ZoneInfo("Asia/Seoul")


def _kst(day, hour, minute=0):
    return datetime(2026, 9, day, hour, minute, tzinfo=SEOUL)


def test_하루_안에서는_서명_시각이_같다():
    morning, night = signing_window(_kst(24, 4), "Asia/Seoul"), signing_window(_kst(25, 3, 59), "Asia/Seoul")
    assert morning == night
    assert morning.signed_at == _kst(24, 4).astimezone(timezone.utc)


def test_04시_전은_전날_창이다():
    assert signing_window(_kst(24, 3, 59), "Asia/Seoul").signed_at == _kst(23, 4).astimezone(timezone.utc)


def test_남은_유효_시간은_24시간에서_48시간이다():
    for now in (_kst(24, 4), _kst(24, 15), _kst(25, 3, 59)):
        window = signing_window(now, "Asia/Seoul")
        assert timedelta(hours=24) < window.expires_at - now <= timedelta(hours=48)


def test_매장_시간대로_하루를_센다():
    now = datetime(2026, 9, 24, 3, 0, tzinfo=timezone.utc)   # 서울 12시, 뉴욕 전날 23시
    assert signing_window(now, "Asia/Seoul").signed_at == _kst(24, 4).astimezone(timezone.utc)
    ny = ZoneInfo("America/New_York")
    assert signing_window(now, "America/New_York").signed_at == datetime(2026, 9, 23, 4, tzinfo=ny).astimezone(timezone.utc)
```

`backend/apps/media/tests/helpers/__init__.py`:

```python

```

`backend/apps/media/tests/helpers/builders.py`:

```python
"""media 테스트가 함께 쓰는 값 — 매장 컨텍스트와 발급 선언값."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from media.domain.value_objects.new_media import NewMedia

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
TZ = "Asia/Seoul"


def ctx(shop_id: int = 1, member_id: int = 11) -> ShopContext:
    return ShopContext(shop_id=shop_id, member_id=member_id, role="staff", permissions=STAFF_PERMISSIONS,
                       timezone=TZ)


def new_photo(member_id: int = 11) -> NewMedia:
    return NewMedia(kind="photo", content_type="image/jpeg", width=3000, height=2000, duration_seconds=None,
                    uploaded_by_member_id=member_id)


def new_video(member_id: int = 11) -> NewMedia:
    return NewMedia(kind="video", content_type="video/mp4", width=1920, height=1080, duration_seconds=42,
                    uploaded_by_member_id=member_id)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/media -q -p no:cacheprovider`
Expected: 수집 단계 오류 3개 — `ModuleNotFoundError: No module named 'media.domain'`(`media.adapter`).

- [ ] **Step 3: 구현한다**

`backend/apps/media/domain/errors.py`:

```python
class MediaError(Exception):
    """media 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "MEDIA_ERROR"


class MediaNotFoundError(MediaError):
    """없거나 다른 매장의 미디어다. 404."""

    code = "MEDIA_NOT_FOUND"


class MediaNotUploadedError(MediaError):
    """발급한 객체가 저장소에 아직 다 올라오지 않았다. 409 — 올린 뒤 다시 확인하면 된다."""

    code = "MEDIA_NOT_UPLOADED"


class MediaTooLargeError(MediaError):
    """종류별 한도(사진 20MB·영상 200MB)를 넘는다. 422."""

    code = "MEDIA_TOO_LARGE"


class MediaTypeUnsupportedError(MediaError):
    """받지 않는 종류·형식이거나 선언과 다른 형식이 올라왔다. 422."""

    code = "MEDIA_TYPE_UNSUPPORTED"


class MediaInputError(MediaError):
    """형식은 맞지만 규칙에 어긋난 값(가로세로·길이). 422."""

    code = "VALIDATION_ERROR"
```

`backend/apps/media/domain/services/media_rules.py`:

```python
"""무엇을 받는가 — 종류·형식·크기·길이, 그리고 객체 키 규칙(설계 7.2).

서버는 파일을 디코딩하지 않는다. 가로·세로·길이는 앱이 선언한 값을 표시용으로 믿고 범위만 본다.
"""
from __future__ import annotations

from dataclasses import dataclass

from media.domain.errors import MediaInputError, MediaTooLargeError, MediaTypeUnsupportedError

PHOTO = "photo"
VIDEO = "video"
KINDS = (PHOTO, VIDEO)

CONTENT_TYPE = {PHOTO: "image/jpeg", VIDEO: "video/mp4"}
MAX_BYTES = {PHOTO: 20 * 1024 * 1024, VIDEO: 200 * 1024 * 1024}
MAX_VIDEO_SECONDS = 60
MAX_SIDE = 10_000   # 긴 변 3000px 로 줄여 올리지만, 선언값이 말이 되는지만 본다


@dataclass(frozen=True)
class MediaKeys:
    """객체 하나가 저장소에 남기는 키. 사진은 원본·표시용·썸네일 셋, 영상은 원본·포스터(썸네일) 둘."""

    original: str
    display: str | None
    thumb: str

    def all(self) -> tuple[str, ...]:
        return tuple(k for k in (self.original, self.display, self.thumb) if k is not None)


def object_keys(shop_id: int, media_id: int, kind: str) -> MediaKeys:
    """렌디션이 키의 **앞**에 온다 — S3 수명주기 규칙은 접두사로만 거를 수 있어서, 원본만 싼 저장 계층으로
    옮기려면(설계 7.4) 원본이 한 접두사 아래 모여야 한다. 영상 원본은 더 늦게 더 싼 계층으로 가므로 따로 둔다."""
    tail = f"shops/{shop_id}/{media_id}"
    if kind == PHOTO:
        return MediaKeys(original=f"original/{tail}.jpg", display=f"display/{tail}.jpg", thumb=f"thumb/{tail}.jpg")
    return MediaKeys(original=f"original-video/{tail}.mp4", display=None, thumb=f"thumb/{tail}.jpg")


def check_upload(
    kind: str, content_type: str, byte_size: int, width: int, height: int, duration_seconds: int | None
) -> None:
    """발급 전에 선언값을 본다. 크기는 확인(HEAD) 때 실제 값으로 한 번 더 본다."""
    if kind not in KINDS or CONTENT_TYPE[kind] != content_type:
        raise MediaTypeUnsupportedError("사진은 image/jpeg, 영상은 video/mp4 만 올릴 수 있습니다.")
    check_size(kind, byte_size)
    if not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE):
        raise MediaInputError("가로·세로가 올바르지 않습니다.")
    if kind == VIDEO and (duration_seconds is None or not 1 <= duration_seconds <= MAX_VIDEO_SECONDS):
        raise MediaInputError("영상은 1초에서 60초까지 올릴 수 있습니다.")
    if kind == PHOTO and duration_seconds is not None:
        raise MediaInputError("사진에는 길이가 없습니다.")


def check_size(kind: str, byte_size: int) -> None:
    if not 1 <= byte_size <= MAX_BYTES[kind]:
        raise MediaTooLargeError("사진은 20MB, 영상은 200MB 까지 올릴 수 있습니다.")
```

`backend/apps/media/domain/services/url_expiry.py`:

```python
"""읽기 서명 URL 의 시간 창(설계 7.3).

같은 객체는 하루 동안 같은 URL 이어야 앱 캐시와 ⑤의 CDN 캐시가 맞는다. 서명 시각을 매장 시간대의 가장 최근
04:00 으로 내리고 유효 기간을 48시간으로 두면, 하루 안에서는 서명이 글자까지 같고 남은 유효 시간은 언제나
24~48시간이다. 유출된 URL 이 살아 있는 시간은 최대 48시간이다(위협 M10).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DAY_STARTS_AT = time(4)
VALID_FOR = timedelta(hours=48)


@dataclass(frozen=True)
class SigningWindow:
    signed_at: datetime   # UTC
    expires_in_seconds: int

    @property
    def expires_at(self) -> datetime:
        return self.signed_at + timedelta(seconds=self.expires_in_seconds)


def signing_window(now: datetime, tz: str) -> SigningWindow:
    local = now.astimezone(ZoneInfo(tz))
    boundary = datetime.combine(local.date(), DAY_STARTS_AT, local.tzinfo)
    if local < boundary:
        boundary -= timedelta(days=1)
    return SigningWindow(signed_at=boundary.astimezone(timezone.utc), expires_in_seconds=int(VALID_FOR.total_seconds()))
```

`backend/apps/media/domain/entities/media_object.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from media.domain.services.media_rules import MediaKeys

PENDING = "pending"
READY = "ready"


@dataclass(frozen=True)
class MediaObject:
    """저장소에 올리는 사진·영상 하나. 발급 때 pending 으로 생기고, 객체가 다 올라온 것을 확인하면 ready 다.

    기록(visit)이 가져가면 attached_at 이 찍힌다. 어느 기록인지는 visit 이 안다(media 는 visit 을 모른다).
    """

    id: int
    shop_id: int
    kind: str
    status: str
    keys: MediaKeys
    content_type: str
    size_bytes: int | None
    width: int
    height: int
    duration_seconds: int | None
    uploaded_by_member_id: int
    attached_at: datetime | None
    created_at: datetime
    ready_at: datetime | None

    @property
    def ready(self) -> bool:
        return self.status == READY
```

`backend/apps/media/domain/value_objects/new_media.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewMedia:
    """발급할 미디어 하나 — 규칙(`media_rules.check_upload`)을 통과한 선언값."""

    kind: str
    content_type: str
    width: int
    height: int
    duration_seconds: int | None
    uploaded_by_member_id: int
```

`backend/apps/media/adapter/outbound/orm/media_orm.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class MediaObjectOrm(Base):
    """사진·영상 객체 하나(설계 6.1). 상태가 원본이고 크기·준비 시각은 ready 일 때만 있다(CHECK)."""

    __tablename__ = "media_objects"
    __table_args__ = (
        CheckConstraint("kind IN ('photo', 'video')", name="ck_media_objects_kind"),
        CheckConstraint("status IN ('pending', 'ready')", name="ck_media_objects_status"),
        CheckConstraint(
            "(status = 'ready') = (ready_at IS NOT NULL) AND (status = 'ready') = (size_bytes IS NOT NULL)",
            name="ck_media_objects_ready_fields",
        ),
        CheckConstraint("attached_at IS NULL OR status = 'ready'", name="ck_media_objects_attached_ready"),
        CheckConstraint("(kind = 'photo') = (display_key IS NOT NULL)", name="ck_media_objects_display"),
        CheckConstraint("(kind = 'video') = (duration_seconds IS NOT NULL)", name="ck_media_objects_duration"),
        CheckConstraint("width > 0 AND height > 0", name="ck_media_objects_size"),
        Index("ix_media_objects_shop_status_created", "shop_id", "status", "created_at"),
        # 정리 스크립트의 "준비됐지만 어느 기록도 가져가지 않은 것"(설계 7.5 ②).
        Index("ix_media_objects_unattached", "ready_at",
              postgresql_where=text("status = 'ready' AND attached_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    shop_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))
    object_key: Mapped[str] = mapped_column(String(100), unique=True)
    display_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    thumb_key: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(20))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(SmallInteger)
    height: Mapped[int] = mapped_column(SmallInteger)
    duration_seconds: Mapped[int | None] = mapped_column(SmallInteger)
    # tenancy 의 멤버 ID.
    uploaded_by_member_id: Mapped[int] = mapped_column(BigInteger)
    attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

`backend/alembic/versions/0007_media_objects.py`:

```python
"""미디어 객체 표(media 스포크)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_objects",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),   # tenancy 의 매장 ID — 외래 키 없음
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("object_key", sa.String(100), nullable=False),
        sa.Column("display_key", sa.String(100)),
        sa.Column("thumb_key", sa.String(100), nullable=False),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("width", sa.SmallInteger, nullable=False),
        sa.Column("height", sa.SmallInteger, nullable=False),
        sa.Column("duration_seconds", sa.SmallInteger),
        sa.Column("uploaded_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN ('photo', 'video')", name="ck_media_objects_kind"),
        sa.CheckConstraint("status IN ('pending', 'ready')", name="ck_media_objects_status"),
        sa.CheckConstraint(
            "(status = 'ready') = (ready_at IS NOT NULL) AND (status = 'ready') = (size_bytes IS NOT NULL)",
            name="ck_media_objects_ready_fields",
        ),
        sa.CheckConstraint("attached_at IS NULL OR status = 'ready'", name="ck_media_objects_attached_ready"),
        sa.CheckConstraint("(kind = 'photo') = (display_key IS NOT NULL)", name="ck_media_objects_display"),
        sa.CheckConstraint("(kind = 'video') = (duration_seconds IS NOT NULL)", name="ck_media_objects_duration"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_media_objects_size"),
        sa.UniqueConstraint("object_key", name="media_objects_object_key_key"),
        sa.UniqueConstraint("display_key", name="media_objects_display_key_key"),
        sa.UniqueConstraint("thumb_key", name="media_objects_thumb_key_key"),
    )
    op.create_index(
        "ix_media_objects_shop_status_created", "media_objects", ["shop_id", "status", "created_at"]
    )
    op.create_index(
        "ix_media_objects_unattached", "media_objects", ["ready_at"],
        postgresql_where=sa.text("status = 'ready' AND attached_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_media_objects_unattached", table_name="media_objects")
    op.drop_index("ix_media_objects_shop_status_created", table_name="media_objects")
    op.drop_table("media_objects")
```

`backend/orm_registry.py`:

```diff
@@ -8,3 +8,4 @@ import auth.adapter.outbound.orm.operator_orm  # noqa: F401
 import tenancy.adapter.outbound.orm.tenancy_orm  # noqa: F401
 import customer.adapter.outbound.orm.customer_orm  # noqa: F401
 import visit.adapter.outbound.orm.visit_orm  # noqa: F401
+import media.adapter.outbound.orm.media_orm  # noqa: F401
```

`backend/apps/media/app/ports/output/media_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from media.domain.entities.media_object import MediaObject
from media.domain.value_objects.new_media import NewMedia


class MediaRepository(ABC):
    """media_objects 표. 모든 메서드가 ShopContext 의 매장으로 거른다."""

    @abstractmethod
    async def create(self, ctx: ShopContext, new: NewMedia) -> MediaObject:
        """pending 으로 넣는다. 키는 ID 로 정해진다(`media_rules.object_keys`)."""

    @abstractmethod
    async def get(self, ctx: ShopContext, media_id: int) -> MediaObject:
        """없거나 다른 매장이면 MediaNotFoundError."""

    @abstractmethod
    async def mark_ready(self, ctx: ShopContext, media_id: int, size_bytes: int) -> bool:
        """pending 일 때만 ready 로 바꾼다(조건부 UPDATE). 바꿨으면 True — 동시에 두 번 확인해도 한 번만 바뀐다."""
```

`backend/.importlinter`:

```diff
@@ -19,6 +19,7 @@ root_packages =
     platform_admin
     customer
     visit
+    media
 include_external_packages = True
 
 [importlinter:contract:clean-architecture]
@@ -35,6 +36,7 @@ containers =
     platform_admin
     customer
     visit
+    media
 
 [importlinter:contract:spoke-independence]
 name = 스포크 상호 독립 (스포크끼리 import 하지 않는다)
@@ -45,6 +47,7 @@ modules =
     platform_admin
     customer
     visit
+    media
 
 [importlinter:contract:framework-isolation]
 name = 프레임워크 격리 (app·domain 은 웹·DB·외부 통신 라이브러리를 모른다)
@@ -61,6 +64,8 @@ source_modules =
     customer.domain
     visit.app
     visit.domain
+    media.app
+    media.domain
 forbidden_modules =
     fastapi
     sqlalchemy
@@ -78,6 +83,7 @@ source_modules =
     platform_admin.domain
     customer.domain
     visit.domain
+    media.domain
 forbidden_modules =
     pydantic
     core
@@ -93,6 +99,7 @@ forbidden_modules =
     platform_admin
     customer
     visit
+    media
 
 [importlinter:contract:core-isolation]
 name = core 격리 (core 는 스포크를 import 하지 않는다)
@@ -105,3 +112,4 @@ forbidden_modules =
     platform_admin
     customer
     visit
+    media
```

`backend/apps/media/__init__.py`:

```python

```

`backend/apps/media/adapter/__init__.py`:

```python

```

`backend/apps/media/adapter/inbound/__init__.py`:

```python

```

`backend/apps/media/adapter/inbound/api/__init__.py`:

```python

```

`backend/apps/media/adapter/inbound/api/schemas/__init__.py`:

```python

```

`backend/apps/media/adapter/inbound/api/v1/__init__.py`:

```python

```

`backend/apps/media/adapter/outbound/__init__.py`:

```python

```

`backend/apps/media/adapter/outbound/mappers/__init__.py`:

```python

```

`backend/apps/media/adapter/outbound/mappers/media_mapper.py`:

```python
from __future__ import annotations

from media.adapter.outbound.orm.media_orm import MediaObjectOrm
from media.domain.entities.media_object import MediaObject
from media.domain.services.media_rules import MediaKeys


def to_media(orm: MediaObjectOrm) -> MediaObject:
    return MediaObject(
        id=orm.id, shop_id=orm.shop_id, kind=orm.kind, status=orm.status,
        keys=MediaKeys(original=orm.object_key, display=orm.display_key, thumb=orm.thumb_key),
        content_type=orm.content_type, size_bytes=orm.size_bytes, width=orm.width, height=orm.height,
        duration_seconds=orm.duration_seconds, uploaded_by_member_id=orm.uploaded_by_member_id,
        attached_at=orm.attached_at, created_at=orm.created_at, ready_at=orm.ready_at,
    )
```

`backend/apps/media/adapter/outbound/orm/__init__.py`:

```python

```

`backend/apps/media/adapter/outbound/pg/__init__.py`:

```python

```

`backend/apps/media/adapter/outbound/pg/media_pg_repository.py`:

```python
from __future__ import annotations

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from media.adapter.outbound.mappers.media_mapper import to_media
from media.adapter.outbound.orm.media_orm import MediaObjectOrm
from media.app.ports.output.media_repository import MediaRepository
from media.domain.entities.media_object import PENDING, READY, MediaObject
from media.domain.errors import MediaNotFoundError
from media.domain.services.media_rules import object_keys
from media.domain.value_objects.new_media import NewMedia


class MediaPgRepository(MediaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, ctx: ShopContext, new: NewMedia) -> MediaObject:
        # 키가 ID 를 품으므로 ID 를 먼저 받는다.
        media_id = (await self._session.execute(text("SELECT nextval('media_objects_id_seq')"))).scalar_one()
        keys = object_keys(ctx.shop_id, media_id, new.kind)
        await self._session.execute(
            insert(MediaObjectOrm).values(
                id=media_id, shop_id=ctx.shop_id, kind=new.kind, status=PENDING,
                object_key=keys.original, display_key=keys.display, thumb_key=keys.thumb,
                content_type=new.content_type, width=new.width, height=new.height,
                duration_seconds=new.duration_seconds, uploaded_by_member_id=new.uploaded_by_member_id,
            )
        )
        return await self.get(ctx, media_id)

    async def get(self, ctx: ShopContext, media_id: int) -> MediaObject:
        row = (
            await self._session.execute(
                select(MediaObjectOrm)
                .where(MediaObjectOrm.id == media_id, MediaObjectOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise MediaNotFoundError("사진·영상을 찾을 수 없습니다.")
        return to_media(row)

    async def mark_ready(self, ctx: ShopContext, media_id: int, size_bytes: int) -> bool:
        result = await self._session.execute(
            update(MediaObjectOrm)
            .where(MediaObjectOrm.id == media_id, MediaObjectOrm.shop_id == ctx.shop_id,
                   MediaObjectOrm.status == PENDING)
            .values(status=READY, size_bytes=size_bytes, ready_at=func.now())
        )
        return result.rowcount == 1
```

`backend/apps/media/app/__init__.py`:

```python

```

`backend/apps/media/app/dtos/__init__.py`:

```python

```

`backend/apps/media/app/ports/__init__.py`:

```python

```

`backend/apps/media/app/ports/input/__init__.py`:

```python

```

`backend/apps/media/app/ports/output/__init__.py`:

```python

```

`backend/apps/media/app/use_cases/__init__.py`:

```python

```

`backend/apps/media/dependencies/__init__.py`:

```python

```

`backend/apps/media/domain/__init__.py`:

```python

```

`backend/apps/media/domain/entities/__init__.py`:

```python

```

`backend/apps/media/domain/services/__init__.py`:

```python

```

`backend/apps/media/domain/value_objects/__init__.py`:

```python

```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/media tests/test_schema_drift.py -q -p no:cacheprovider` → 25 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 788 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 267 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `MediaPgRepository.mark_ready`의 `MediaObjectOrm.status == PENDING` 조건을 뺀다 → `test_준비는_한_번만_바뀐다` 실패(두 번째 확인이 크기를 덮는다).
- `url_expiry.signing_window`의 `if local < boundary:`를 `if False:`로 → `test_04시_전은_전날_창이다` 등 3개 실패.
- `media_rules.check_upload`의 `if kind == PHOTO and duration_seconds is not None:`를 `if False:`로 → `test_가로세로와_길이의_경계[photo-100-100-5]` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(media): media 스포크의 도메인과 표 — 받는 형식·한도·키 규칙, 읽기 서명 창, media_objects(0007)와 저장소

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 객체 저장소 — boto3 어댑터(공개 주소로 서명·내부 주소로 HEAD·DELETE), 하루 창의 읽기 서명, S3 설정, 버킷 준비 스크립트

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `infra/docker-compose.yml`
- Modify: `backend/core/config.py`
- Modify: `backend/scripts/generate_dev_env.py`
- Create: `backend/apps/media/domain/value_objects/object_info.py`
- Create: `backend/apps/media/app/ports/output/object_storage_port.py`
- Create: `backend/apps/media/adapter/outbound/s3/sigv4_query.py`
- Create: `backend/apps/media/adapter/outbound/s3/__init__.py`
- Create: `backend/apps/media/adapter/outbound/s3/boto3_object_storage_adapter.py`
- Create: `backend/apps/media/tests/adapter/test_boto3_object_storage_adapter.py`
- Create: `backend/apps/media/tests/adapter/test_sigv4_query.py`
- Create: `backend/scripts/ensure_media_bucket.py`
- Create: `backend/tests/test_ensure_media_bucket.py`

**Interfaces:**
- Consumes: 작업 1 의 `SigningWindow`, `object_keys`; 개발 `.env`의 `S3_ENDPOINT_URL`·`S3_ACCESS_KEY`·`S3_SECRET_KEY`·`S3_BUCKET`(이미 있다); compose 의 `minio` 서비스(이미 있다).
- Produces: `media.domain.value_objects.object_info.ObjectInfo(size_bytes, content_type)`; `media.app.ports.output.object_storage_port.ObjectStoragePort` — `presign_put(key, content_type, expires_in_seconds) -> str`, `presign_get(key, window) -> str`, `async head(key) -> ObjectInfo | None`, `async delete(keys)`; `media.adapter.outbound.s3.sigv4_query.presign_get_url(endpoint, bucket, key, region, access_key, secret_key, signed_at, expires_in_seconds) -> str`; `media.adapter.outbound.s3.boto3_object_storage_adapter.Boto3ObjectStorageAdapter(endpoint, public_endpoint, bucket, region, access_key, secret_key)`(속성 `_internal`은 boto3 클라이언트 — 테스트·버킷 준비가 쓴다); `core.config` 상수 `S3_ENDPOINT_URL`·`S3_PUBLIC_ENDPOINT_URL`·`S3_REGION`·`S3_BUCKET`·`S3_ACCESS_KEY`·`S3_SECRET_KEY`; `scripts.ensure_media_bucket` — `lifecycle_rules()`, `ensure_bucket(client, bucket) -> list[str]`, `storage_client()`.

저장소 쪽 어댑터와 설정이다(설계 7.1·7.3·7.4). **새 의존성 `boto3`** — `backend/requirements.txt`를 고친 뒤 **이미지를 다시 빌드한다**: `docker compose build backend auth`(`infra/`). **설계와 다른 점**(결정 기록 007): ① 설정 이름은 기존 `.env`의 `S3_*`를 쓰고 `S3_PUBLIC_ENDPOINT_URL`(기본 `http://127.0.0.1:9010`)·`S3_REGION`(기본 `us-east-1`)을 더한다 — 개발자는 `.env`를 고치지 않아도 된다. ② 읽기 서명은 표준 라이브러리로 직접 만든다 — 하루 동안 같은 URL 이 되려면 서명 시각을 창의 시작으로 고정해야 하는데 botocore 는 늘 지금으로 찍는다. 같은 시각에 botocore 가 만드는 URL 과 글자까지 같은지 테스트가 본다. ③ MinIO 는 계층 이동 규칙을 `InvalidStorageClass`로 거절하므로 버킷 준비 스크립트가 규칙만 건너뛴다. compose 의 `backend`·`auth`가 `minio`에 기대게 한다 — 통합 테스트가 MinIO 를 쓴다(테스트 버킷 `chagocnote-test`, 키는 테스트마다 새 이름). 개발 환경에서 버킷을 한 번 만들어 둔다: `docker compose run --rm backend python scripts/ensure_media_bucket.py`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/media/tests/adapter/test_boto3_object_storage_adapter.py`:

```python
"""실제 MinIO(compose)에 올리고 확인하고 지운다. 컨테이너 안에서 PUT 하려고 공개 주소도 내부 주소로 둔다.

버킷은 테스트 사이에 비우지 않으므로 키마다 새 이름을 쓴다.
"""
import uuid
from datetime import datetime, timezone

import httpx
import pytest

from core.config import S3_ACCESS_KEY, S3_ENDPOINT_URL, S3_REGION, S3_SECRET_KEY
from media.adapter.outbound.s3.boto3_object_storage_adapter import Boto3ObjectStorageAdapter
from media.domain.services.url_expiry import signing_window
from media.domain.value_objects.object_info import ObjectInfo
from scripts.ensure_media_bucket import ensure_bucket

pytestmark = pytest.mark.integration

BUCKET = "chagocnote-test"


@pytest.fixture
def storage():
    adapter = Boto3ObjectStorageAdapter(S3_ENDPOINT_URL, S3_ENDPOINT_URL, BUCKET, S3_REGION, S3_ACCESS_KEY,
                                        S3_SECRET_KEY)
    ensure_bucket(adapter._internal, BUCKET)
    return adapter


def _key() -> str:
    return f"thumb/shops/1/{uuid.uuid4().hex}.jpg"


async def test_서명한_URL_로_올리고_HEAD_로_확인하고_읽는다(storage):
    key = _key()
    async with httpx.AsyncClient() as http:
        put = await http.put(storage.presign_put(key, "image/jpeg", 900), content=b"\xff\xd8jpeg",
                             headers={"Content-Type": "image/jpeg"})
        assert put.status_code == 200, put.text
        assert await storage.head(key) == ObjectInfo(size_bytes=6, content_type="image/jpeg")
        got = await http.get(storage.presign_get(key, signing_window(datetime.now(timezone.utc), "Asia/Seoul")))
        assert (got.status_code, got.content) == (200, b"\xff\xd8jpeg")
    await storage.delete([key, _key()])   # 없는 키는 조용히 넘어간다
    assert await storage.head(key) is None


async def test_서명과_다른_형식으로_올리면_저장소가_거절한다(storage):
    key = _key()
    async with httpx.AsyncClient() as http:
        put = await http.put(storage.presign_put(key, "image/jpeg", 900), content=b"x",
                             headers={"Content-Type": "image/png"})
    assert put.status_code == 403
    assert await storage.head(key) is None


async def test_지운_객체는_읽기_URL_도_실패한다(storage):
    key = _key()
    async with httpx.AsyncClient() as http:
        await http.put(storage.presign_put(key, "image/jpeg", 900), content=b"x", headers={"Content-Type": "image/jpeg"})
        await storage.delete([key])
        got = await http.get(storage.presign_get(key, signing_window(datetime.now(timezone.utc), "Asia/Seoul")))
    assert got.status_code == 404
```

`backend/apps/media/tests/adapter/test_sigv4_query.py`:

```python
"""직접 만든 읽기 서명이 botocore 가 같은 시각에 만드는 URL 과 글자까지 같은지."""
from datetime import datetime, timezone

import boto3
import botocore.auth
from botocore.config import Config

from media.adapter.outbound.s3.sigv4_query import presign_get_url

SIGNED_AT = datetime(2026, 9, 23, 19, 0, tzinfo=timezone.utc)   # 서울 04:00


def _botocore_url(monkeypatch, endpoint, key):
    monkeypatch.setattr(botocore.auth, "get_current_datetime", lambda: SIGNED_AT)
    client = boto3.client("s3", endpoint_url=endpoint, region_name="ap-northeast-2", aws_access_key_id="AKIDEXAMPLE",
                          aws_secret_access_key="secret/key+value",
                          config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
    return client.generate_presigned_url("get_object", Params={"Bucket": "chagocnote-media", "Key": key},
                                         ExpiresIn=172800)


def _ours(endpoint, key):
    return presign_get_url(endpoint, "chagocnote-media", key, "ap-northeast-2", "AKIDEXAMPLE", "secret/key+value",
                           SIGNED_AT, 172800)


def test_botocore_와_같은_URL_이다(monkeypatch):
    for endpoint in ("https://s3.ap-northeast-2.amazonaws.com", "http://127.0.0.1:9010"):
        for key in ("thumb/shops/1/42.jpg", "original-video/shops/12/9007199254740993.mp4"):
            assert _ours(endpoint, key) == _botocore_url(monkeypatch, endpoint, key), (endpoint, key)


def test_같은_창이면_같은_URL_이다():
    assert _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg") == _ours("http://127.0.0.1:9010", "thumb/shops/1/42.jpg")
```

`backend/tests/test_ensure_media_bucket.py`:

```python
"""미디어 버킷 준비 스크립트 — 원본만 계층을 옮기는 규칙, 여러 번 돌려도 같은 결과."""
import pytest

from scripts.ensure_media_bucket import ensure_bucket, lifecycle_rules, storage_client


def test_원본만_접두사로_골라_옮긴다():
    rules = {r["Filter"]["Prefix"]: [(t["Days"], t["StorageClass"]) for t in r["Transitions"]]
             for r in lifecycle_rules()}
    assert rules == {"original/": [(30, "STANDARD_IA")],
                     "original-video/": [(30, "STANDARD_IA"), (90, "GLACIER_IR")]}


@pytest.mark.integration
def test_두_번_돌려도_된다_MinIO_는_규칙을_건너뛴다():
    client = storage_client()
    first = ensure_bucket(client, "chagocnote-test-ensure")
    second = ensure_bucket(client, "chagocnote-test-ensure")
    assert second[0] == "버킷 chagocnote-test-ensure 이(가) 이미 있습니다."
    assert first[-1] == second[-1] == "이 저장소는 계층 이동을 받지 않아 수명주기 규칙을 건너뜁니다(개발용 MinIO)."
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/media/tests/adapter/test_sigv4_query.py apps/media/tests/adapter/test_boto3_object_storage_adapter.py tests/test_ensure_media_bucket.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 3개 — `ImportError: cannot import name 'S3_ACCESS_KEY' from 'core.config'`, `ModuleNotFoundError: No module named 'media.adapter.outbound.s3'`, `No module named 'scripts.ensure_media_bucket'`(이미지를 다시 빌드하기 전이면 `No module named 'boto3'`가 먼저 난다 — 빌드는 Step 4 에서 한다).

- [ ] **Step 3: 구현한다**

`backend/requirements.txt`:

```diff
@@ -8,6 +8,7 @@ redis>=5.0
 python-jose[cryptography]>=3.4
 cryptography>=43
 httpx>=0.27
+boto3>=1.43
 python-dotenv>=1.0
 import-linter>=2.0
 pytest>=8.0
```

`infra/docker-compose.yml`:

```diff
@@ -15,6 +15,8 @@ x-backend-base: &backend-base
       condition: service_healthy
     redis:
       condition: service_started
+    minio:
+      condition: service_started
 
 services:
   pgvector:
```

`backend/core/config.py`:

```diff
@@ -33,3 +33,12 @@ APPLE_BUNDLE_ID: str = _m.get("APPLE_BUNDLE_ID", "") or ""
 APPLE_TEAM_ID: str = _m.get("APPLE_TEAM_ID", "") or ""
 APPLE_KEY_ID: str = _m.get("APPLE_KEY_ID", "") or ""
 APPLE_PRIVATE_KEY: str = _b64_pem("APPLE_PRIVATE_KEY_B64")
+
+# 미디어 객체 저장소(S3 호환 — 개발은 compose 의 MinIO). 서버는 내부 주소로 HEAD·DELETE 하고, 앱에 줄 URL 은
+# 공개 주소로 서명한다(서명에 호스트가 들어간다). 운영은 S3 서울 리전 주소와 ap-northeast-2 를 넣는다.
+S3_ENDPOINT_URL: str = _m.get("S3_ENDPOINT_URL", "http://minio:9000") or "http://minio:9000"
+S3_PUBLIC_ENDPOINT_URL: str = _m.get("S3_PUBLIC_ENDPOINT_URL", "http://127.0.0.1:9010") or "http://127.0.0.1:9010"
+S3_REGION: str = _m.get("S3_REGION", "us-east-1") or "us-east-1"
+S3_BUCKET: str = _m.get("S3_BUCKET", "chagocnote-media") or "chagocnote-media"
+S3_ACCESS_KEY: str = _m.get("S3_ACCESS_KEY", "") or ""
+S3_SECRET_KEY: str = _m.get("S3_SECRET_KEY", "") or ""
```

`backend/scripts/generate_dev_env.py`:

```diff
@@ -32,6 +32,8 @@ def main() -> None:
         "REDIS_URL=redis://redis:6379/0\n"
         f"JWT_PUBLIC_KEY_B64={base64.b64encode(public_pem).decode()}\n"
         "S3_ENDPOINT_URL=http://minio:9000\n"
+        "S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:9010\n"
+        "S3_REGION=us-east-1\n"
         "S3_ACCESS_KEY=chagoc\n"
         "S3_SECRET_KEY=chagoc_dev_minio\n"
         "S3_BUCKET=chagocnote-dev\n",
```

`backend/apps/media/domain/value_objects/object_info.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectInfo:
    """저장소가 HEAD 로 알려 주는 객체의 실제 크기와 형식."""

    size_bytes: int
    content_type: str
```

`backend/apps/media/app/ports/output/object_storage_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from media.domain.services.url_expiry import SigningWindow
from media.domain.value_objects.object_info import ObjectInfo


class ObjectStoragePort(ABC):
    """객체 저장소(S3·MinIO). 올리기·내려받기는 앱이 서명 URL 로 직접 하고, 서버는 서명·확인·삭제만 한다(설계 7.4)."""

    @abstractmethod
    def presign_put(self, key: str, content_type: str, expires_in_seconds: int) -> str:
        """앱이 인증 헤더 없이 PUT 할 URL. Content-Type 이 서명에 든다 — 다른 형식으로 올리면 저장소가 거절한다."""

    @abstractmethod
    def presign_get(self, key: str, window: SigningWindow) -> str:
        """읽기 URL. 같은 창이면 글자까지 같다(앱·CDN 캐시)."""

    @abstractmethod
    async def head(self, key: str) -> ObjectInfo | None:
        """없으면 None. 잠금을 쥔 채 부르지 않는다(외부 네트워크)."""

    @abstractmethod
    async def delete(self, keys: list[str]) -> None:
        """없는 키는 조용히 넘어간다. 잠금을 쥔 채 부르지 않는다."""
```

`backend/apps/media/adapter/outbound/s3/sigv4_query.py`:

```python
"""S3 읽기 URL 의 SigV4 쿼리 서명 — 서명 시각을 직접 정한다.

botocore 는 서명 시각을 늘 '지금'으로 찍어서 같은 객체의 URL 이 호출마다 바뀐다. 하루 동안 같은 URL 을 주려면
(설계 7.3) 서명 시각을 창의 시작으로 고정해야 해서 GET 서명만 여기서 만든다. 결과는 botocore 가 같은 시각에
만드는 URL 과 글자까지 같다(`test_sigv4_query.py`). 경로 방식 주소(https://호스트/버킷/키)를 쓴다.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from urllib.parse import quote, urlsplit

_ALGORITHM = "AWS4-HMAC-SHA256"


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def presign_get_url(
    endpoint: str, bucket: str, key: str, region: str, access_key: str, secret_key: str,
    signed_at: datetime, expires_in_seconds: int,
) -> str:
    host = urlsplit(endpoint).netloc
    amz_date = signed_at.strftime("%Y%m%dT%H%M%SZ")
    day = signed_at.strftime("%Y%m%d")
    scope = f"{day}/{region}/s3/aws4_request"
    path = "/" + quote(bucket, safe="") + "/" + quote(key, safe="/~")
    query = (
        f"X-Amz-Algorithm={_ALGORITHM}"
        f"&X-Amz-Credential={quote(f'{access_key}/{scope}', safe='')}"
        f"&X-Amz-Date={amz_date}"
        f"&X-Amz-Expires={expires_in_seconds}"
        "&X-Amz-SignedHeaders=host"
    )
    canonical = "\n".join(["GET", path, query, f"host:{host}", "", "host", "UNSIGNED-PAYLOAD"])
    string_to_sign = "\n".join([_ALGORITHM, amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    signing_key = _hmac(_hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), day), region), "s3"), "aws4_request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return f"{endpoint.rstrip('/')}{path}?{query}&X-Amz-Signature={signature}"
```

`backend/apps/media/adapter/outbound/s3/__init__.py`:

```python

```

`backend/apps/media/adapter/outbound/s3/boto3_object_storage_adapter.py`:

```python
from __future__ import annotations

import asyncio

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from media.adapter.outbound.s3.sigv4_query import presign_get_url
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.services.url_expiry import SigningWindow
from media.domain.value_objects.object_info import ObjectInfo

_PATH_STYLE = Config(signature_version="s3v4", s3={"addressing_style": "path"})


class Boto3ObjectStorageAdapter(ObjectStoragePort):
    """boto3(동기)를 스레드로 감싼다. 서명은 앱이 닿는 공개 주소로, HEAD·DELETE 는 서버가 닿는 내부 주소로 한다 —
    서명에 호스트가 들어가므로 앱에 줄 URL 은 공개 주소로 서명해야 한다(설계 7.4)."""

    def __init__(
        self, endpoint: str, public_endpoint: str, bucket: str, region: str, access_key: str, secret_key: str
    ) -> None:
        self._bucket = bucket
        self._public_endpoint = public_endpoint
        self._region = region
        self._access_key = access_key
        self._secret_key = secret_key
        credentials = dict(region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                           config=_PATH_STYLE)
        self._internal = boto3.client("s3", endpoint_url=endpoint, **credentials)
        self._public = boto3.client("s3", endpoint_url=public_endpoint, **credentials)

    def presign_put(self, key: str, content_type: str, expires_in_seconds: int) -> str:
        return self._public.generate_presigned_url(
            "put_object", Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in_seconds,
        )

    def presign_get(self, key: str, window: SigningWindow) -> str:
        return presign_get_url(
            self._public_endpoint, self._bucket, key, self._region, self._access_key, self._secret_key,
            window.signed_at, window.expires_in_seconds,
        )

    async def head(self, key: str) -> ObjectInfo | None:
        try:
            found = await asyncio.to_thread(self._internal.head_object, Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return ObjectInfo(size_bytes=found["ContentLength"], content_type=found.get("ContentType", ""))

    async def delete(self, keys: list[str]) -> None:
        if keys:
            await asyncio.to_thread(
                self._internal.delete_objects, Bucket=self._bucket,
                Delete={"Objects": [{"Key": k} for k in keys], "Quiet": True},
            )
```

`backend/scripts/ensure_media_bucket.py`:

```python
"""미디어 버킷을 만들고 수명주기 규칙을 건다(설계 7.4). 여러 번 돌려도 결과가 같다.

원본만 싼 저장 계층으로 옮긴다 — 사진·영상 원본은 30일 뒤 Standard-IA, 영상 원본은 90일 뒤 Glacier Instant
Retrieval. 표시용·썸네일은 자주 읽으므로 Standard 에 둔다. 규칙은 키 접두사로 거른다(`media_rules.object_keys`).
MinIO(개발)는 계층 이동을 받지 않아(InvalidStorageClass) 버킷만 만들고 규칙은 건너뛴다.
사용: cd infra && docker compose run --rm backend python scripts/ensure_media_bucket.py
"""
from __future__ import annotations

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from core.config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT_URL, S3_REGION, S3_SECRET_KEY


def lifecycle_rules() -> list[dict]:
    return [
        {"ID": "photo-originals-to-ia", "Status": "Enabled", "Filter": {"Prefix": "original/"},
         "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}]},
        {"ID": "video-originals-to-ia-then-glacier-ir", "Status": "Enabled", "Filter": {"Prefix": "original-video/"},
         "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"},
                         {"Days": 90, "StorageClass": "GLACIER_IR"}]},
    ]


def ensure_bucket(client, bucket: str) -> list[str]:
    """버킷이 없으면 만들고 규칙을 건다. 한 일을 문장으로 돌려준다."""
    done = []
    try:
        client.head_bucket(Bucket=bucket)
        done.append(f"버킷 {bucket} 이(가) 이미 있습니다.")
    except ClientError:
        client.create_bucket(Bucket=bucket)
        done.append(f"버킷 {bucket} 을(를) 만들었습니다.")
    try:
        client.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={"Rules": lifecycle_rules()})
        done.append("수명주기 규칙을 걸었습니다(원본 30일 IA, 영상 원본 90일 Glacier IR).")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "InvalidStorageClass":
            raise
        done.append("이 저장소는 계층 이동을 받지 않아 수명주기 규칙을 건너뜁니다(개발용 MinIO).")
    return done


def storage_client():
    return boto3.client(
        "s3", endpoint_url=S3_ENDPOINT_URL, region_name=S3_REGION, aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def main() -> None:
    for line in ensure_bucket(storage_client(), S3_BUCKET):
        print(line)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose build backend auth` → 끝까지 빌드된다(`boto3` 설치)

Run (`infra/`): `docker compose run --rm backend pytest apps/media tests/test_ensure_media_bucket.py -q -p no:cacheprovider` → 31 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 791 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 271 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `sigv4_query.presign_get_url`의 `host = urlsplit(endpoint).netloc`을 `.hostname`으로 → `test_botocore_와_같은_URL_이다` 실패(포트가 서명에서 빠진다).
- `Boto3ObjectStorageAdapter.presign_put`의 `"ContentType": content_type`을 뺀다 → `test_서명과_다른_형식으로_올리면_저장소가_거절한다` 실패.
- `ensure_media_bucket.lifecycle_rules`의 첫 규칙 `"Prefix": "original/"`을 `""`로 → `test_원본만_접두사로_골라_옮긴다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(media): 객체 저장소 — boto3 어댑터(공개 주소로 서명·내부 주소로 HEAD·DELETE), 하루 창의 읽기 서명, S3 설정, 버킷 준비 스크립트

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 발급·확인·자기소개 슬라이스 — `POST /media/uploads`(렌디션마다 PUT URL), `POST /media/{id}/confirm`(HEAD 대조 뒤 ready), main 연결

**Files:**
- Create: `backend/apps/media/app/dtos/issue_upload_dto.py`
- Create: `backend/apps/media/app/dtos/media_view_dto.py`
- Create: `backend/apps/media/app/use_cases/issue_upload_interactor.py`
- Create: `backend/apps/media/app/use_cases/confirm_upload_interactor.py`
- Create: `backend/apps/media/dependencies/media_wiring.py`
- Modify: `backend/main.py`
- Create: `backend/apps/media/adapter/inbound/api/error_map.py`
- Create: `backend/apps/media/adapter/inbound/api/path_params.py`
- Create: `backend/apps/media/adapter/inbound/api/schemas/issue_upload_schema.py`
- Create: `backend/apps/media/adapter/inbound/api/schemas/media_myself_schema.py`
- Create: `backend/apps/media/adapter/inbound/api/schemas/media_schema.py`
- Create: `backend/apps/media/adapter/inbound/api/v1/confirm_upload_router.py`
- Create: `backend/apps/media/adapter/inbound/api/v1/issue_upload_router.py`
- Create: `backend/apps/media/adapter/inbound/api/v1/media_myself_router.py`
- Create: `backend/apps/media/adapter/outbound/log_media_myself_record_adapter.py`
- Create: `backend/apps/media/app/dtos/confirm_upload_dto.py`
- Create: `backend/apps/media/app/dtos/media_myself_dto.py`
- Create: `backend/apps/media/app/ports/input/confirm_upload_use_case.py`
- Create: `backend/apps/media/app/ports/input/issue_upload_use_case.py`
- Create: `backend/apps/media/app/ports/input/media_myself_use_case.py`
- Create: `backend/apps/media/app/ports/output/media_myself_record_port.py`
- Create: `backend/apps/media/app/use_cases/media_myself_interactor.py`
- Create: `backend/apps/media/dependencies/confirm_upload_provider.py`
- Create: `backend/apps/media/dependencies/issue_upload_provider.py`
- Create: `backend/apps/media/dependencies/media_myself_provider.py`
- Create: `backend/apps/media/tests/adapter/test_confirm_upload_router.py`
- Create: `backend/apps/media/tests/adapter/test_issue_upload_router.py`
- Create: `backend/apps/media/tests/adapter/test_media_myself_router.py`
- Create: `backend/apps/media/tests/app/use_cases/test_confirm_upload_interactor.py`
- Create: `backend/apps/media/tests/app/use_cases/test_issue_upload_interactor.py`
- Create: `backend/apps/media/tests/app/use_cases/test_media_myself_interactor.py`
- Create: `backend/apps/media/tests/helpers/api.py`
- Create: `backend/apps/media/tests/helpers/fakes.py`
- Create: `backend/apps/media/tests/test_fakes_are_ports.py`
- Modify: `backend/tests/integration/conftest.py`
- Create: `backend/tests/integration/test_media_flow_wiring.py`

**Interfaces:**
- Consumes: 작업 1 의 `MediaRepository`·`check_upload`·`check_size`·`CONTENT_TYPE`·도메인 오류, 작업 2 의 `ObjectStoragePort`·`Boto3ObjectStorageAdapter`·`S3_*` 상수·`ensure_bucket`; `core.shop_guard.require_permission`·`get_shop_context`; `core.database.DbSession`.
- Produces: `IssueUploadInteractor(media, storage, now)`(`PUT_VALID_FOR = 15분`), `ConfirmUploadInteractor(media, storage)`, `MediaMyselfInteractor(record)`; DTO `IssueUploadCommand`·`IssuedUploadView(media_id, puts: UploadTargetsView(original, display, thumb), expires_at)`·`ConfirmUploadCommand`·`MediaView`; `media.adapter.inbound.api.error_map.MEDIA_ERROR_STATUS`, `path_params.MediaId`; `media.dependencies.media_wiring` — `utc_now()`, `build_media_repository(db)`, `get_object_storage()`(프로세스에 하나, `lru_cache` — 테스트가 이 의존성을 바꿔 끼운다); 라우터 `issue_upload_router`·`confirm_upload_router`·`media_myself_router`; 통합 픽스처 `media_storage`(테스트 버킷, 시작 때 비움). 새 경로 셋: `POST /v1/shops/{shop_id}/media/uploads`(201, record:write), `POST /v1/shops/{shop_id}/media/{media_id}/confirm`(record:write), `GET /v1/shops/{shop_id}/media/myself`(멤버).

앱이 파일을 저장소에 바로 올리는 3단계 가운데 서버가 맡는 둘이다(설계 7.1). 발급은 행을 pending 으로 넣고 렌디션마다 PUT URL 을 서명한다(계산이라 네트워크가 없다). 확인은 행을 잠그지 않은 채 객체마다 HEAD 로 존재·크기·형식을 보고 `mark_ready`(조건부 UPDATE)로 바꾼다 — 이미 ready 면 저장소를 보지 않고 그대로 준다(M13). 한도를 넘거나 형식이 다르면 객체를 지우고 422 다(M5). 같은 매장 멤버면 발급자가 아니어도 확인할 수 있다. 통합 테스트의 `media_storage` 픽스처는 컨테이너 안에서 서명 URL 로 PUT 하도록 공개 주소를 내부 주소로 두고, 테스트마다 DB ID 가 1부터라 키가 겹치므로 버킷을 비우고 시작한다. 첫 통합 테스트는 테넌트 격리다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/media/tests/adapter/test_confirm_upload_router.py`:

```python
from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_router
from media.app.dtos.media_view_dto import MediaView
from media.dependencies.confirm_upload_provider import get_confirm_upload_use_case
from media.domain.errors import MediaNotFoundError, MediaNotUploadedError
from media.tests.helpers.api import NO_RECORD, Recorder, build_app, client, error_of

READY = MediaView(media_id=7, kind="photo", status="ready", size_bytes=3_000_000, width=3000, height=2000,
                  duration_seconds=None)


async def test_확인하면_ready_객체를_준다():
    stub = Recorder(READY)
    async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/media/7/confirm")
    assert (response.status_code, response.json()["status"], response.json()["size_bytes"]) == (200, "ready", 3_000_000)
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].media_id) == (3, 7)


async def test_오류는_코드로_나간다():
    for error, expected in ((MediaNotUploadedError("아직"), (409, "MEDIA_NOT_UPLOADED")),
                            (MediaNotFoundError("없음"), (404, "MEDIA_NOT_FOUND"))):
        async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, Recorder(error=error))) as c:
            assert error_of(await c.post("/v1/shops/3/media/7/confirm")) == expected


async def test_기록_권한이_없거나_ID_가_bigint_를_넘으면_거절한다():
    async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, Recorder(READY), NO_RECORD)) as c:
        assert error_of(await c.post("/v1/shops/3/media/7/confirm")) == (403, "PERMISSION_DENIED")
    async with client(build_app(confirm_upload_router, get_confirm_upload_use_case, Recorder(READY))) as c:
        assert error_of(await c.post(f"/v1/shops/3/media/{2**63}/confirm")) == (422, "VALIDATION_ERROR")
```

`backend/apps/media/tests/adapter/test_issue_upload_router.py`:

```python
from datetime import datetime, timezone

from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
from media.app.dtos.issue_upload_dto import IssuedUploadView, UploadTargetsView
from media.dependencies.issue_upload_provider import get_issue_upload_use_case
from media.domain.errors import MediaTooLargeError
from media.tests.helpers.api import NO_RECORD, Recorder, build_app, client, error_of

ISSUED = IssuedUploadView(
    media_id=7, puts=UploadTargetsView(original="put://o", display=None, thumb="put://t"),
    expires_at=datetime(2026, 9, 24, 3, 15, tzinfo=timezone.utc),
)
BODY = {"kind": "video", "content_type": "video/mp4", "byte_size": 150_000_000, "width": 1920, "height": 1080,
        "duration_seconds": 42}


async def test_직원은_발급받는다_201():
    stub = Recorder(ISSUED)
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/media/uploads", json=BODY)
    assert (response.status_code, response.json()) == (201, {
        "media_id": 7, "puts": {"original": "put://o", "display": None, "thumb": "put://t"},
        "expires_at": "2026-09-24T03:15:00Z"})
    call = stub.calls[0]
    assert (call.ctx.shop_id, call.kind, call.byte_size, call.duration_seconds) == (3, "video", 150_000_000, 42)


async def test_기록_권한이_없으면_403():
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, Recorder(ISSUED), NO_RECORD)) as c:
        response = await c.post("/v1/shops/3/media/uploads", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_칸의_범위를_넘으면_422_다():
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, Recorder(ISSUED))) as c:
        for bad in ({**BODY, "kind": "audio"}, {**BODY, "width": 40_000}, {**BODY, "byte_size": "150"},
                    {**BODY, "byte_size": 0}, {k: v for k, v in BODY.items() if k != "height"}):
            assert error_of(await c.post("/v1/shops/3/media/uploads", json=bad)) == (422, "VALIDATION_ERROR")


async def test_도메인_거절은_코드로_나간다():
    stub = Recorder(error=MediaTooLargeError("큼"))
    async with client(build_app(issue_upload_router, get_issue_upload_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/media/uploads", json=BODY)
    assert error_of(response) == (422, "MEDIA_TOO_LARGE")
```

`backend/apps/media/tests/adapter/test_media_myself_router.py`:

```python
from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
from media.app.dtos.media_myself_dto import MediaMyselfResponse
from media.dependencies.media_myself_provider import get_media_myself_use_case
from media.tests.helpers.api import NO_RECORD, Recorder, build_app, client


async def test_멤버는_자기소개를_본다():
    stub = Recorder(MediaMyselfResponse(id=6, name="미디어 (media)", introduction="소개"))
    async with client(build_app(media_myself_router, get_media_myself_use_case, stub, NO_RECORD)) as c:
        response = await c.get("/v1/shops/3/media/myself")
    assert response.json() == {"id": 6, "name": "미디어 (media)", "introduction": "소개"}
```

`backend/apps/media/tests/app/use_cases/test_confirm_upload_interactor.py`:

```python
import pytest

from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.use_cases.confirm_upload_interactor import ConfirmUploadInteractor
from media.domain.errors import (
    MediaNotFoundError,
    MediaNotUploadedError,
    MediaTooLargeError,
    MediaTypeUnsupportedError,
)
from media.tests.helpers.builders import ctx
from media.tests.helpers.fakes import FakeMedia, FakeStorage, Journal

MB = 1024 * 1024


def _setup(kind="photo"):
    journal = Journal()
    media, storage = FakeMedia(journal), FakeStorage(journal)
    row = media.seed(kind=kind)
    return ConfirmUploadInteractor(media, storage), media, storage, row, journal


def _upload_all(storage, row, original_size=3 * MB, original_type=None):
    storage.put(row.keys.original, original_size, original_type or row.content_type)
    for key in row.keys.all()[1:]:
        storage.put(key, 200_000)


async def test_객체가_다_있으면_원본_크기로_ready_가_된다():
    interactor, media, storage, row, journal = _setup()
    _upload_all(storage, row)
    view = await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(member_id=99), media_id=row.id))
    assert (view.status, view.size_bytes) == ("ready", 3 * MB)
    assert [e[0] for e in journal] == ["head", "head", "head", "mark_ready"]


async def test_하나라도_없으면_409_MEDIA_NOT_UPLOADED_이고_아무것도_바꾸지_않는다():
    interactor, media, storage, row, journal = _setup()
    storage.put(row.keys.original, MB)
    with pytest.raises(MediaNotUploadedError):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=row.id))
    assert media.rows[row.id].status == "pending"
    assert not [e for e in journal if e[0] in ("mark_ready", "delete")]


@pytest.mark.parametrize("kind, size, content_type, error", [
    ("photo", 20 * MB + 1, None, MediaTooLargeError),
    ("video", 200 * MB + 1, None, MediaTooLargeError),
    ("photo", MB, "image/png", MediaTypeUnsupportedError),
])
async def test_한도를_넘거나_형식이_다르면_객체를_지우고_거절한다(kind, size, content_type, error):
    interactor, media, storage, row, journal = _setup(kind)
    _upload_all(storage, row, size, content_type)
    with pytest.raises(error):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=row.id))
    assert storage.objects == {}
    assert ("delete", row.keys.all()) in journal
    assert media.rows[row.id].status == "pending"


async def test_썸네일도_JPEG_이고_사진_한도_안이어야_한다():
    interactor, media, storage, row, _ = _setup("video")
    _upload_all(storage, row)
    storage.put(row.keys.thumb, 21 * MB)
    with pytest.raises(MediaTooLargeError):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=row.id))


async def test_이미_ready_면_저장소를_보지_않고_그대로_준다():
    interactor, media, storage, _, journal = _setup()
    ready = media.seed(status="ready")
    view = await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(), media_id=ready.id))
    assert (view.status, journal) == ("ready", [])


async def test_다른_매장의_미디어는_404_다():
    interactor, _, _, row, _ = _setup()
    with pytest.raises(MediaNotFoundError):
        await interactor.confirm_upload(ConfirmUploadCommand(ctx=ctx(shop_id=2), media_id=row.id))
```

`backend/apps/media/tests/app/use_cases/test_issue_upload_interactor.py`:

```python
from datetime import timedelta

import pytest

from media.app.dtos.issue_upload_dto import IssueUploadCommand
from media.app.use_cases.issue_upload_interactor import IssueUploadInteractor
from media.domain.errors import MediaTooLargeError, MediaTypeUnsupportedError
from media.tests.helpers.builders import ctx
from media.tests.helpers.fakes import NOW, FakeMedia, FakeStorage, Journal


def _command(kind="photo", content_type="image/jpeg", byte_size=4_000_000, duration=None):
    return IssueUploadCommand(ctx=ctx(member_id=12), kind=kind, content_type=content_type, byte_size=byte_size,
                              width=3000, height=2000, duration_seconds=duration)


def _interactor(journal=None):
    media = FakeMedia(journal)
    return IssueUploadInteractor(media, FakeStorage(journal), now=lambda: NOW), media


async def test_사진은_렌디션_셋의_PUT_URL_을_15분_동안_준다():
    interactor, media = _interactor()
    view = await interactor.issue_upload(_command())
    row = media.rows[view.media_id]
    assert (row.status, row.uploaded_by_member_id, row.shop_id) == ("pending", 12, 1)
    assert view.puts.original == f"put://original/shops/1/{view.media_id}.jpg?type=image/jpeg&expires=900"
    assert view.puts.display == f"put://display/shops/1/{view.media_id}.jpg?type=image/jpeg&expires=900"
    assert view.puts.thumb == f"put://thumb/shops/1/{view.media_id}.jpg?type=image/jpeg&expires=900"
    assert view.expires_at == NOW + timedelta(minutes=15)


async def test_영상은_원본과_JPEG_포스터_둘이다():
    interactor, _ = _interactor()
    view = await interactor.issue_upload(_command("video", "video/mp4", 150_000_000, duration=42))
    assert view.puts.original.endswith(".mp4?type=video/mp4&expires=900")
    assert (view.puts.display, view.puts.thumb.endswith(".jpg?type=image/jpeg&expires=900")) == (None, True)


@pytest.mark.parametrize("command, error", [
    (_command(content_type="image/heic"), MediaTypeUnsupportedError),
    (_command(byte_size=20 * 1024 * 1024 + 1), MediaTooLargeError),
])
async def test_규칙에_어긋나면_행을_만들지_않는다(command, error):
    journal = Journal()
    interactor, _ = _interactor(journal)
    with pytest.raises(error):
        await interactor.issue_upload(command)
    assert journal == []
```

`backend/apps/media/tests/app/use_cases/test_media_myself_interactor.py`:

```python
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
```

`backend/apps/media/tests/helpers/api.py`:

```python
"""media 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from hub.app.dtos.shop_context import ShopContext
from media.adapter.inbound.api.error_map import MEDIA_ERROR_STATUS
from media.tests.helpers.builders import STAFF_PERMISSIONS, TZ


class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=STAFF_PERMISSIONS, role="staff"):
        self.permissions = frozenset(permissions)
        self.role = role

    async def resolve(self, user_id, shop_id):
        return ShopContext(shop_id=shop_id, member_id=11, role=self.role, permissions=self.permissions,
                           timezone=TZ)


STAFF = StubShopAccess()
NO_RECORD = StubShopAccess(frozenset({"reservation:write", "customer:write"}))   # record:write 없음


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None) -> FastAPI:
    """access=None 이면 직원 권한(record:write 있음)으로 통과시킨다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, MEDIA_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_current_user_id] = lambda: 5
    app.dependency_overrides[get_shop_access_port] = lambda: access or STAFF
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

`backend/apps/media/tests/helpers/fakes.py`:

```python
"""media 인터랙터 테스트용 메모리 스텁. 스텁은 포트 ABC 를 상속한다(`apps/media/tests/test_fakes_are_ports.py`)."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.entities.media_object import PENDING, READY, MediaObject
from media.domain.errors import MediaNotFoundError
from media.domain.services.media_rules import object_keys
from media.domain.value_objects.object_info import ObjectInfo

NOW = datetime(2026, 9, 24, 3, 0, tzinfo=timezone.utc)


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeMedia(MediaRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, MediaObject] = {}
        self._next = 1

    def seed(self, shop_id=1, kind="photo", status=PENDING, **fields) -> MediaObject:
        media = MediaObject(
            id=self._next, shop_id=shop_id, kind=kind, status=status, keys=object_keys(shop_id, self._next, kind),
            content_type="image/jpeg" if kind == "photo" else "video/mp4",
            size_bytes=1000 if status == READY else None, width=3000, height=2000,
            duration_seconds=None if kind == "photo" else 30, uploaded_by_member_id=11, attached_at=None,
            created_at=NOW, ready_at=NOW if status == READY else None,
        )
        media = replace(media, **fields)
        self.rows[media.id] = media
        self._next += 1
        return media

    async def create(self, ctx, new):
        media = self.seed(shop_id=ctx.shop_id, kind=new.kind, content_type=new.content_type, width=new.width,
                          height=new.height, duration_seconds=new.duration_seconds,
                          uploaded_by_member_id=new.uploaded_by_member_id)
        self.journal.append(("create_media", media.id))
        return media

    async def get(self, ctx, media_id):
        media = self.rows.get(media_id)
        if media is None or media.shop_id != ctx.shop_id:
            raise MediaNotFoundError("사진·영상을 찾을 수 없습니다.")
        return media

    async def mark_ready(self, ctx, media_id, size_bytes):
        media = await self.get(ctx, media_id)
        if media.status != PENDING:
            return False
        self.rows[media_id] = replace(media, status=READY, size_bytes=size_bytes, ready_at=NOW)
        self.journal.append(("mark_ready", media_id, size_bytes))
        return True


class FakeStorage(ObjectStoragePort):
    """객체는 {키: ObjectInfo}. 서명 URL 은 키와 형식이 보이는 가짜 문자열이다."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.objects: dict[str, ObjectInfo] = {}

    def put(self, key: str, size_bytes: int = 1000, content_type: str = "image/jpeg") -> None:
        self.objects[key] = ObjectInfo(size_bytes=size_bytes, content_type=content_type)

    def presign_put(self, key, content_type, expires_in_seconds):
        return f"put://{key}?type={content_type}&expires={expires_in_seconds}"

    def presign_get(self, key, window):
        return f"get://{key}?signed={window.signed_at:%Y%m%dT%H%M}"

    async def head(self, key):
        self.journal.append(("head", key))
        return self.objects.get(key)

    async def delete(self, keys):
        self.journal.append(("delete", tuple(keys)))
        for key in keys:
            self.objects.pop(key, None)
```

`backend/apps/media/tests/test_fakes_are_ports.py`:

```python
"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.tests.helpers.fakes import FakeMedia, FakeStorage


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    assert isinstance(FakeMedia(), MediaRepository)
    assert isinstance(FakeStorage(), ObjectStoragePort)
```

`backend/tests/integration/conftest.py`:

```diff
@@ -72,3 +72,25 @@ async def fake_kakao(wired, monkeypatch):
         SocialProviderFactory({Provider.DEV: DevIdentityStrategy(), Provider.KAKAO: fake}),
     )
     return fake
+
+
+@pytest.fixture
+async def media_storage(wired):
+    """미디어 저장소를 테스트 버킷으로 바꾼다. 컨테이너 안에서 서명 URL 로 PUT 하려고 공개 주소도 내부 주소로 둔다.
+
+    테스트마다 DB ID 가 1부터 다시 시작해 객체 키가 겹치므로, 버킷을 비우고 시작한다.
+    """
+    import main
+    from core.config import S3_ACCESS_KEY, S3_ENDPOINT_URL, S3_REGION, S3_SECRET_KEY
+    from media.adapter.outbound.s3.boto3_object_storage_adapter import Boto3ObjectStorageAdapter
+    from media.dependencies.media_wiring import get_object_storage
+    from scripts.ensure_media_bucket import ensure_bucket
+
+    storage = Boto3ObjectStorageAdapter(S3_ENDPOINT_URL, S3_ENDPOINT_URL, "chagocnote-test", S3_REGION,
+                                        S3_ACCESS_KEY, S3_SECRET_KEY)
+    ensure_bucket(storage._internal, "chagocnote-test")
+    for page in storage._internal.get_paginator("list_objects_v2").paginate(Bucket="chagocnote-test"):
+        await storage.delete([item["Key"] for item in page.get("Contents", [])])
+    main.app.dependency_overrides[get_object_storage] = lambda: storage
+    yield storage
+    del main.app.dependency_overrides[get_object_storage]
```

`backend/tests/integration/test_media_flow_wiring.py`:

```python
"""미디어 발급·확인을 실제 배선(프로바이더·DB 커밋·매장 접근 확인·MinIO)으로 확인한다. 첫 테스트는 테넌트 격리다."""
import asyncio

import httpx
import pytest

from tests.integration.support import accept_invite, bearer, error_of, make_operator, shop_with_owner, staff_invite

pytestmark = pytest.mark.integration

PHOTO = {"kind": "photo", "content_type": "image/jpeg", "byte_size": 3000, "width": 3000, "height": 2000}


async def issue(wired, shop_id, headers, body=PHOTO):
    response = await wired.api.post(f"/v1/shops/{shop_id}/media/uploads", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def upload(issued, sizes=(3000, 800, 200)):
    """렌디션마다 서명 URL 로 서명한 형식 그대로 PUT 한다. 영상이면 표시용이 없다."""
    puts = issued["puts"]
    async with httpx.AsyncClient() as http:
        for name, size in zip(("original", "display", "thumb"), sizes):
            if puts[name] is None:
                continue
            content_type = "video/mp4" if name == "original" and ".mp4" in puts[name] else "image/jpeg"
            put = await http.put(puts[name], content=b"\x00" * size, headers={"Content-Type": content_type})
            assert put.status_code == 200, put.text


async def test_다른_매장의_미디어에는_손댈_수_없다(wired, media_storage):
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    b_media = (await issue(wired, b_shop, b))["media_id"]

    their_shop = [
        await wired.api.post(f"/v1/shops/{b_shop}/media/uploads", json=PHOTO, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/media/{b_media}/confirm", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/media/myself", headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * 3
    own_shop = await wired.api.post(f"/v1/shops/{a_shop}/media/{b_media}/confirm", headers=a)
    assert error_of(own_shop) == (404, "MEDIA_NOT_FOUND")


async def test_직원이_발급받아_올리고_확인하면_ready_다(wired, media_storage):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])

    issued = await issue(wired, shop_id, s)
    early = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=s)
    assert error_of(early) == (409, "MEDIA_NOT_UPLOADED")
    await upload(issued)
    confirmed = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm",
                                     headers=bearer(owner["access_token"]))   # 발급자가 아니어도 된다
    assert (confirmed.status_code, confirmed.json()["status"], confirmed.json()["size_bytes"]) == (200, "ready", 3000)


async def test_동시에_두_번_확인해도_결과가_같다(wired, media_storage):
    """M13 — 두 요청 모두 200 ready, 크기는 원본의 것 하나."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    o = bearer(owner["access_token"])
    issued = await issue(wired, shop_id, o)
    await upload(issued)
    first, second = await asyncio.gather(
        wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=o),
        wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=o),
    )
    assert [(r.status_code, r.json()["status"], r.json()["size_bytes"]) for r in (first, second)] == [
        (200, "ready", 3000)] * 2
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/media tests/integration/test_media_flow_wiring.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 6개 — `ModuleNotFoundError: No module named 'media.app.dtos.issue_upload_dto'`(`confirm_upload_dto`·`media_myself_dto`·라우터 셋).

- [ ] **Step 3: 구현한다**

`backend/apps/media/app/dtos/issue_upload_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class IssueUploadCommand:
    ctx: ShopContext
    kind: str
    content_type: str
    byte_size: int          # 원본 크기(앱 선언). 확인 때 실제 크기로 한 번 더 본다
    width: int
    height: int
    duration_seconds: int | None


@dataclass(frozen=True)
class UploadTargetsView:
    """렌디션마다 PUT 할 URL. 영상은 표시용이 없다."""

    original: str
    display: str | None
    thumb: str


@dataclass(frozen=True)
class IssuedUploadView:
    media_id: int
    puts: UploadTargetsView
    expires_at: datetime
```

`backend/apps/media/app/dtos/media_view_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from media.domain.entities.media_object import MediaObject


@dataclass(frozen=True)
class MediaView:
    media_id: int
    kind: str
    status: str
    size_bytes: int | None
    width: int
    height: int
    duration_seconds: int | None

    @classmethod
    def of(cls, media: MediaObject) -> MediaView:
        return cls(media_id=media.id, kind=media.kind, status=media.status, size_bytes=media.size_bytes,
                   width=media.width, height=media.height, duration_seconds=media.duration_seconds)
```

`backend/apps/media/app/use_cases/issue_upload_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from media.app.dtos.issue_upload_dto import IssuedUploadView, IssueUploadCommand, UploadTargetsView
from media.app.ports.input.issue_upload_use_case import IssueUploadUseCase
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.services.media_rules import CONTENT_TYPE, check_upload
from media.domain.value_objects.new_media import NewMedia

PUT_VALID_FOR = timedelta(minutes=15)
_THUMB_TYPE = CONTENT_TYPE["photo"]   # 표시용·썸네일·영상 포스터는 모두 JPEG 다


class IssueUploadInteractor(IssueUploadUseCase):
    """행을 pending 으로 넣고 렌디션마다 PUT URL 을 서명한다. 서명은 계산이라 네트워크가 없다(설계 7.1)."""

    def __init__(self, media: MediaRepository, storage: ObjectStoragePort, now: Callable[[], datetime]) -> None:
        self._media = media
        self._storage = storage
        self._now = now

    async def issue_upload(self, command: IssueUploadCommand) -> IssuedUploadView:
        check_upload(command.kind, command.content_type, command.byte_size, command.width, command.height,
                     command.duration_seconds)
        media = await self._media.create(command.ctx, NewMedia(
            kind=command.kind, content_type=command.content_type, width=command.width, height=command.height,
            duration_seconds=command.duration_seconds, uploaded_by_member_id=command.ctx.member_id,
        ))
        seconds = int(PUT_VALID_FOR.total_seconds())
        keys = media.keys
        return IssuedUploadView(
            media_id=media.id,
            puts=UploadTargetsView(
                original=self._storage.presign_put(keys.original, command.content_type, seconds),
                display=self._storage.presign_put(keys.display, _THUMB_TYPE, seconds) if keys.display else None,
                thumb=self._storage.presign_put(keys.thumb, _THUMB_TYPE, seconds),
            ),
            expires_at=self._now() + PUT_VALID_FOR,
        )
```

`backend/apps/media/app/use_cases/confirm_upload_interactor.py`:

```python
from __future__ import annotations

from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.dtos.media_view_dto import MediaView
from media.app.ports.input.confirm_upload_use_case import ConfirmUploadUseCase
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.errors import MediaNotUploadedError, MediaTooLargeError, MediaTypeUnsupportedError
from media.domain.services.media_rules import CONTENT_TYPE, PHOTO, check_size


class ConfirmUploadInteractor(ConfirmUploadUseCase):
    """객체마다 HEAD 로 존재·크기·형식을 대조하고 pending → ready 로 바꾼다(설계 7.1).

    HEAD 는 행을 잠그지 않은 채 한다(외부 네트워크). 같은 매장 멤버면 발급자가 아니어도 확인할 수 있다.
    이미 ready 면 그대로 돌려준다 — 앱이 응답을 못 받고 다시 불러도, 두 기기가 동시에 불러도 결과가 같다(M13).
    """

    def __init__(self, media: MediaRepository, storage: ObjectStoragePort) -> None:
        self._media = media
        self._storage = storage

    async def confirm_upload(self, command: ConfirmUploadCommand) -> MediaView:
        ctx = command.ctx
        media = await self._media.get(ctx, command.media_id)
        if media.ready:
            return MediaView.of(media)
        keys = media.keys
        found = {key: await self._storage.head(key) for key in keys.all()}
        if any(info is None for info in found.values()):
            raise MediaNotUploadedError("아직 다 올라오지 않았습니다. 올린 뒤 다시 확인해 주세요.")
        expected = {key: CONTENT_TYPE[PHOTO] for key in keys.all()} | {keys.original: media.content_type}
        try:
            for key, info in found.items():
                if info.content_type != expected[key]:
                    raise MediaTypeUnsupportedError("선언한 형식과 다른 파일이 올라왔습니다.")
                check_size(media.kind if key == keys.original else PHOTO, info.size_bytes)
        except (MediaTypeUnsupportedError, MediaTooLargeError):
            await self._storage.delete(list(keys.all()))   # 받지 않는 파일은 남기지 않는다
            raise
        await self._media.mark_ready(ctx, media.id, found[keys.original].size_bytes)
        return MediaView.of(await self._media.get(ctx, media.id))
```

`backend/apps/media/dependencies/media_wiring.py`:

```python
"""media 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import (
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_PUBLIC_ENDPOINT_URL,
    S3_REGION,
    S3_SECRET_KEY,
)
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.adapter.outbound.s3.boto3_object_storage_adapter import Boto3ObjectStorageAdapter
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_media_repository(db: AsyncSession) -> MediaRepository:
    return MediaPgRepository(db)


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStoragePort:
    """프로세스에 하나 — boto3 클라이언트는 만들기 비싸고 스레드 사이에 나눠 써도 된다. 테스트는 이 의존성을 바꿔 끼운다."""
    return Boto3ObjectStorageAdapter(S3_ENDPOINT_URL, S3_PUBLIC_ENDPOINT_URL, S3_BUCKET, S3_REGION, S3_ACCESS_KEY,
                                     S3_SECRET_KEY)
```

`backend/main.py`:

```diff
@@ -40,6 +40,10 @@ from customer.adapter.inbound.api.v1.update_customer_router import update_custom
 from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
 from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
 from customer.dependencies.hub_ports import get_visit_ledger
+from media.adapter.inbound.api.error_map import MEDIA_ERROR_STATUS
+from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_router
+from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
+from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
 from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
@@ -147,11 +151,15 @@ app.include_router(parse_visit_draft_router)
 app.include_router(get_visit_router)
 app.include_router(update_visit_router)
 app.include_router(get_next_visit_draft_router)
+# media
+app.include_router(media_myself_router)
+app.include_router(issue_upload_router)
+app.include_router(confirm_upload_router)
 install_error_handlers(
     app,
     {
         **AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS,
-        **CUSTOMER_ERROR_STATUS, **VISIT_ERROR_STATUS,
+        **CUSTOMER_ERROR_STATUS, **VISIT_ERROR_STATUS, **MEDIA_ERROR_STATUS,
     },
 )
```

`backend/apps/media/adapter/inbound/api/error_map.py`:

```python
"""media 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from media.domain.errors import (
    MediaInputError,
    MediaNotFoundError,
    MediaNotUploadedError,
    MediaTooLargeError,
    MediaTypeUnsupportedError,
)

MEDIA_ERROR_STATUS: dict[type[Exception], int] = {
    MediaNotFoundError: 404,
    MediaNotUploadedError: 409,
    MediaTooLargeError: 422,
    MediaTypeUnsupportedError: 422,
    MediaInputError: 422,
}
```

`backend/apps/media/adapter/inbound/api/path_params.py`:

```python
"""media 경로 변수. bigint 를 넘는 값은 DB 에 닿기 전에 422 로 막는다(닿으면 asyncpg 오류로 500 이 된다)."""
from typing import Annotated

from fastapi import Path

MediaId = Annotated[int, Path(ge=1, le=9_223_372_036_854_775_807)]
```

`backend/apps/media/adapter/inbound/api/schemas/issue_upload_schema.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt

from media.app.dtos.issue_upload_dto import IssuedUploadView

Side = Annotated[StrictInt, Field(ge=1, le=32_767)]


class IssueUploadRequestSchema(BaseModel):
    """형식·크기·길이의 규칙은 도메인(`media_rules`)이 본다. 여기서는 DB 칸에 들어갈 수 있는 범위만."""

    kind: Literal["photo", "video"]
    content_type: Annotated[str, Field(min_length=1, max_length=50)]
    byte_size: Annotated[StrictInt, Field(ge=1, le=2**40)]
    width: Side
    height: Side
    duration_seconds: Annotated[StrictInt, Field(ge=0, le=32_767)] | None = None


class UploadTargetsSchema(BaseModel):
    original: str
    display: str | None   # 영상이면 None
    thumb: str


class IssuedUploadSchema(BaseModel):
    media_id: int
    puts: UploadTargetsSchema
    expires_at: datetime

    @classmethod
    def of(cls, view: IssuedUploadView) -> IssuedUploadSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/media/adapter/inbound/api/schemas/media_myself_schema.py`:

```python
from pydantic import BaseModel


class MediaMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
```

`backend/apps/media/adapter/inbound/api/schemas/media_schema.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

from media.app.dtos.media_view_dto import MediaView


class MediaSchema(BaseModel):
    media_id: int
    kind: str
    status: str
    size_bytes: int | None
    width: int
    height: int
    duration_seconds: int | None

    @classmethod
    def of(cls, view: MediaView) -> MediaSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/media/adapter/inbound/api/v1/confirm_upload_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from media.adapter.inbound.api.path_params import MediaId
from media.adapter.inbound.api.schemas.media_schema import MediaSchema
from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.ports.input.confirm_upload_use_case import ConfirmUploadUseCase
from media.dependencies.confirm_upload_provider import get_confirm_upload_use_case

confirm_upload_router = APIRouter(prefix="/v1/shops", tags=["media"])


@confirm_upload_router.post("/{shop_id}/media/{media_id}/confirm", response_model=MediaSchema)
async def confirm_upload(
    media_id: MediaId,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: ConfirmUploadUseCase = Depends(get_confirm_upload_use_case),
) -> MediaSchema:
    return MediaSchema.of(await use_case.confirm_upload(ConfirmUploadCommand(ctx=ctx, media_id=media_id)))
```

`backend/apps/media/adapter/inbound/api/v1/issue_upload_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from media.adapter.inbound.api.schemas.issue_upload_schema import IssuedUploadSchema, IssueUploadRequestSchema
from media.app.dtos.issue_upload_dto import IssueUploadCommand
from media.app.ports.input.issue_upload_use_case import IssueUploadUseCase
from media.dependencies.issue_upload_provider import get_issue_upload_use_case

issue_upload_router = APIRouter(prefix="/v1/shops", tags=["media"])


@issue_upload_router.post("/{shop_id}/media/uploads", response_model=IssuedUploadSchema, status_code=201)
async def issue_upload(
    body: IssueUploadRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: IssueUploadUseCase = Depends(get_issue_upload_use_case),
) -> IssuedUploadSchema:
    view = await use_case.issue_upload(IssueUploadCommand(
        ctx=ctx, kind=body.kind, content_type=body.content_type, byte_size=body.byte_size, width=body.width,
        height=body.height, duration_seconds=body.duration_seconds,
    ))
    return IssuedUploadSchema.of(view)
```

`backend/apps/media/adapter/inbound/api/v1/media_myself_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from media.adapter.inbound.api.schemas.media_myself_schema import MediaMyselfResponseSchema
from media.app.dtos.media_myself_dto import MediaMyselfQuery
from media.app.ports.input.media_myself_use_case import MediaMyselfUseCase
from media.dependencies.media_myself_provider import get_media_myself_use_case

media_myself_router = APIRouter(prefix="/v1/shops", tags=["media"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@media_myself_router.get(
    "/{shop_id}/media/myself", response_model=MediaMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: MediaMyselfUseCase = Depends(get_media_myself_use_case),
) -> MediaMyselfResponseSchema:
    result = await use_case.introduce_myself(MediaMyselfQuery(id=6, name="미디어 (media)"))
    return MediaMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
```

`backend/apps/media/adapter/outbound/log_media_myself_record_adapter.py`:

```python
from __future__ import annotations

import logging

from media.app.ports.output.media_myself_record_port import MediaMyselfRecordPort

logger = logging.getLogger(__name__)


class LogMediaMyselfRecordAdapter(MediaMyselfRecordPort):
    """기록을 로그로 남기는 구현. 객체 키·URL 은 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[media-myself-record] %s | %s", subject, note)
```

`backend/apps/media/app/dtos/confirm_upload_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ConfirmUploadCommand:
    ctx: ShopContext
    media_id: int
```

`backend/apps/media/app/dtos/media_myself_dto.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MediaMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class MediaMyselfResponse:
    id: int
    name: str
    introduction: str
```

`backend/apps/media/app/ports/input/confirm_upload_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from media.app.dtos.confirm_upload_dto import ConfirmUploadCommand
from media.app.dtos.media_view_dto import MediaView


class ConfirmUploadUseCase(ABC):
    @abstractmethod
    async def confirm_upload(self, command: ConfirmUploadCommand) -> MediaView: ...
```

`backend/apps/media/app/ports/input/issue_upload_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from media.app.dtos.issue_upload_dto import IssuedUploadView, IssueUploadCommand


class IssueUploadUseCase(ABC):
    @abstractmethod
    async def issue_upload(self, command: IssueUploadCommand) -> IssuedUploadView: ...
```

`backend/apps/media/app/ports/input/media_myself_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from media.app.dtos.media_myself_dto import MediaMyselfQuery, MediaMyselfResponse


class MediaMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: MediaMyselfQuery) -> MediaMyselfResponse: ...
```

`backend/apps/media/app/ports/output/media_myself_record_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class MediaMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
```

`backend/apps/media/app/use_cases/media_myself_interactor.py`:

```python
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
```

`backend/apps/media/dependencies/confirm_upload_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from media.app.ports.input.confirm_upload_use_case import ConfirmUploadUseCase
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.app.use_cases.confirm_upload_interactor import ConfirmUploadInteractor
from media.dependencies.media_wiring import build_media_repository, get_object_storage


def get_confirm_upload_use_case(
    db: DbSession, storage: ObjectStoragePort = Depends(get_object_storage)
) -> ConfirmUploadUseCase:
    return ConfirmUploadInteractor(media=build_media_repository(db), storage=storage)
```

`backend/apps/media/dependencies/issue_upload_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from media.app.ports.input.issue_upload_use_case import IssueUploadUseCase
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.app.use_cases.issue_upload_interactor import IssueUploadInteractor
from media.dependencies.media_wiring import build_media_repository, get_object_storage, utc_now


def get_issue_upload_use_case(
    db: DbSession, storage: ObjectStoragePort = Depends(get_object_storage)
) -> IssueUploadUseCase:
    return IssueUploadInteractor(media=build_media_repository(db), storage=storage, now=utc_now)
```

`backend/apps/media/dependencies/media_myself_provider.py`:

```python
from __future__ import annotations

from media.adapter.outbound.log_media_myself_record_adapter import LogMediaMyselfRecordAdapter
from media.app.ports.input.media_myself_use_case import MediaMyselfUseCase
from media.app.use_cases.media_myself_interactor import MediaMyselfInteractor


def get_media_myself_use_case() -> MediaMyselfUseCase:
    return MediaMyselfInteractor(record=LogMediaMyselfRecordAdapter())
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/media tests/integration/test_media_flow_wiring.py tests/test_hub_port_binding.py -q -p no:cacheprovider` → 60 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 813 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 274 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `ConfirmUploadInteractor`의 `if media.ready: return MediaView.of(media)` 두 줄을 뺀다 → `test_이미_ready_면_저장소를_보지_않고_그대로_준다` 실패.
- `ConfirmUploadInteractor`의 `except` 안 `await self._storage.delete(list(keys.all()))`를 뺀다 → `test_한도를_넘거나_형식이_다르면_객체를_지우고_거절한다` 3개 실패.
- `IssueUploadInteractor`의 `check_upload(...)` 호출을 뺀다 → `test_규칙에_어긋나면_행을_만들지_않는다` 2개 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(media): 발급·확인·자기소개 슬라이스 — POST /media/uploads(렌디션마다 PUT URL), POST /media/{id}/confirm(HEAD 대조 뒤 ready), main 연결

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 허브 포트 `MediaLibraryPort` — 기록이 미디어를 가져가고(`claim`, 전부 되거나 전부 안 됨) 놓고 읽기 URL 을 받는다, media 가 구현한다

**Files:**
- Create: `backend/apps/hub/app/dtos/media_urls.py`
- Create: `backend/apps/hub/app/ports/media_library_port.py`
- Modify: `backend/apps/hub/app/errors.py`
- Modify: `backend/core/hub_errors.py`
- Modify: `backend/apps/media/app/ports/output/media_repository.py`
- Modify: `backend/apps/media/adapter/outbound/pg/media_pg_repository.py`
- Create: `backend/apps/media/app/use_cases/media_library_interactor.py`
- Create: `backend/apps/media/dependencies/media_library_provider.py`
- Create: `backend/apps/media/tests/adapter/test_media_library_pg.py`
- Create: `backend/apps/media/tests/app/use_cases/test_media_library_interactor.py`
- Modify: `backend/apps/media/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: 작업 1 의 `MediaRepository`·`MediaPgRepository`·`signing_window`, 작업 2 의 `ObjectStoragePort.presign_get`, 작업 3 의 `media_wiring.utc_now`·`get_object_storage`; `hub.app.errors.HubPortError`; `core/hub_errors.py`.
- Produces: `hub.app.dtos.media_urls.MediaUrls(media_id, kind, original_url, display_url, thumb_url, width, height, duration_seconds)`; `hub.app.ports.media_library_port.MediaLibraryPort` — `async claim(ctx, media_ids) -> dict[int, str]`(id → kind), `async release(ctx, media_ids)`, `async read_urls(ctx, media_ids) -> dict[int, MediaUrls]`; 허브 오류 `MediaClaimNotFoundError`(MEDIA_NOT_FOUND, 404)·`MediaClaimNotReadyError`(MEDIA_NOT_READY, 409)·`MediaClaimAlreadyAttachedError`(MEDIA_ALREADY_ATTACHED, 409); `MediaRepository`에 `attach_all(ctx, ids) -> dict[int, str] | None`(세이브포인트)·`detach(ctx, ids)`·`list(ctx, ids)`; `media.app.use_cases.media_library_interactor.MediaLibraryInteractor(media, storage, now)`; `media.dependencies.media_library_provider.get_media_library_use_case(db, storage)`. 작업 6 부터 visit 이, 작업 10 에서 customer 가 소비한다. 스텁 `FakeMedia`에 세 메서드를 더한다.

스포크를 넘어 미디어를 쓰는 유일한 길이다(설계 5.1). media 는 어느 기록이 가져갔는지 모르고 `attached_at`만 안다. `claim`은 조건부 UPDATE(이 매장·ready·미부착)를 세이브포인트 안에서 하고, 개수가 모자라면 되돌린 뒤 이유를 가려 허브 오류를 던진다(없는 것 → 준비 전 → 이미 붙음 순서). 같은 미디어를 두 요청이 동시에 가져가면 늦은 쪽은 앞선 쪽의 커밋을 기다렸다가 조건을 다시 보고 못 가져간다(M4, 두 세션 테스트). **설계와 다른 점**(결정 기록 007): ① `claim`이 종류를 돌려준다 — visit 이 연결 표에 적어 대표 사진·한도를 자기 표만으로 계산한다. ② `discard`가 없다 — 놓인 미디어는 정리 스크립트(작업 11)가 하루 뒤 지운다. 허브 오류 이름은 media 도메인 오류와 겹치지 않게 `MediaClaim…`이다. `tests/test_hub_errors.py`가 새 허브 오류 셋이 `core/hub_errors.py`에 있는지 자동으로 본다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/media/tests/adapter/test_media_library_pg.py`:

```python
"""가져가기의 원자성과 경합 — 실제 Postgres, 두 세션."""
import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.tests.helpers.builders import ctx, new_photo

pytestmark = pytest.mark.integration

A = ctx(shop_id=1)
BLOCKED = 0.5


async def _ready(session, count=1):
    repo = MediaPgRepository(session)
    ids = []
    for _ in range(count):
        media = await repo.create(A, new_photo())
        await repo.mark_ready(A, media.id, 100)
        ids.append(media.id)
    await session.commit()
    return ids


async def test_하나라도_못_가져가면_세이브포인트로_되돌리고_세션은_계속_쓴다(db_session):
    repo = MediaPgRepository(db_session)
    ready, = await _ready(db_session)
    pending = (await repo.create(A, new_photo())).id
    assert await repo.attach_all(A, [ready, pending]) is None
    assert (await repo.get(A, ready)).attached_at is None
    assert await repo.attach_all(A, [ready]) == {ready: "photo"}


async def test_같은_미디어를_동시에_가져가면_늦은_쪽은_못_가져간다(db_engine, db_session):
    """조건부 UPDATE 의 attached_at IS NULL 을 빼면 늦은 쪽도 가져가 한 객체가 두 기록에 붙는다."""
    media_id, = await _ready(db_session)
    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        assert await MediaPgRepository(first).attach_all(A, [media_id]) == {media_id: "photo"}
        late = asyncio.create_task(MediaPgRepository(second).attach_all(A, [media_id]))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await first.commit()
        assert await late is None
```

`backend/apps/media/tests/app/use_cases/test_media_library_interactor.py`:

```python
from datetime import datetime, timezone

import pytest

from hub.app.errors import MediaClaimAlreadyAttachedError, MediaClaimNotFoundError, MediaClaimNotReadyError
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.tests.helpers.builders import ctx
from media.tests.helpers.fakes import NOW, FakeMedia, FakeStorage


def _library():
    media = FakeMedia()
    return MediaLibraryInteractor(media, FakeStorage(), now=lambda: NOW), media


async def test_준비된_미디어를_가져가고_종류를_돌려준다():
    library, media = _library()
    photo, video = media.seed(status="ready"), media.seed(kind="video", status="ready")
    assert await library.claim(ctx(), [photo.id, video.id]) == {photo.id: "photo", video.id: "video"}
    assert media.rows[photo.id].attached_at == media.rows[video.id].attached_at == NOW


@pytest.mark.parametrize("make, error", [
    (lambda m: m.seed(shop_id=2, status="ready"), MediaClaimNotFoundError),
    (lambda m: m.seed(status="pending"), MediaClaimNotReadyError),
    (lambda m: m.seed(status="ready", attached_at=NOW), MediaClaimAlreadyAttachedError),
])
async def test_하나라도_안_되면_아무것도_가져가지_않는다(make, error):
    library, media = _library()
    good = media.seed(status="ready")
    bad = make(media)
    with pytest.raises(error):
        await library.claim(ctx(), [good.id, bad.id])
    assert media.rows[good.id].attached_at is None


async def test_없는_ID_는_NOT_FOUND_다():
    library, media = _library()
    good = media.seed(status="ready")
    with pytest.raises(MediaClaimNotFoundError):
        await library.claim(ctx(), [good.id, 999])


async def test_놓으면_다시_가져갈_수_있다():
    library, media = _library()
    photo = media.seed(status="ready")
    await library.claim(ctx(), [photo.id])
    await library.release(ctx(), [photo.id])
    assert await library.claim(ctx(), [photo.id]) == {photo.id: "photo"}


async def test_빈_목록은_저장소를_부르지_않는다():
    library, media = _library()
    assert (await library.claim(ctx(), []), await library.read_urls(ctx(), [])) == ({}, {})
    await library.release(ctx(), [])
    assert media.journal == []


async def test_읽기_URL_은_준비된_것만_매장_시간대의_하루_창으로_서명한다():
    library, media = _library()
    photo, video, pending = media.seed(status="ready"), media.seed(kind="video", status="ready"), media.seed()
    urls = await library.read_urls(ctx(), [photo.id, video.id, pending.id])
    assert set(urls) == {photo.id, video.id}
    # NOW 는 서울 12:00 → 창은 그날 04:00(UTC 전날 19:00).
    assert urls[photo.id].thumb_url == f"get://thumb/shops/1/{photo.id}.jpg?signed=20260923T1900"
    assert urls[photo.id].display_url == f"get://display/shops/1/{photo.id}.jpg?signed=20260923T1900"
    assert (urls[video.id].kind, urls[video.id].display_url, urls[video.id].duration_seconds) == ("video", None, 30)
    assert urls[video.id].original_url == f"get://original-video/shops/1/{video.id}.mp4?signed=20260923T1900"


async def test_다른_매장의_미디어는_URL_이_없다():
    library, media = _library()
    photo = media.seed(shop_id=2, status="ready")
    assert await library.read_urls(ctx(), [photo.id]) == {}
```

`backend/apps/media/tests/helpers/fakes.py`:

```diff
@@ -58,6 +58,24 @@ class FakeMedia(MediaRepository):
         self.journal.append(("mark_ready", media_id, size_bytes))
         return True
 
+    async def attach_all(self, ctx, media_ids):
+        mine = [self.rows.get(i) for i in set(media_ids)]
+        if any(m is None or m.shop_id != ctx.shop_id or not m.ready or m.attached_at for m in mine):
+            return None
+        for m in mine:
+            self.rows[m.id] = replace(m, attached_at=NOW)
+        self.journal.append(("attach", sorted(media_ids)))
+        return {m.id: m.kind for m in mine}
+
+    async def detach(self, ctx, media_ids):
+        for i in media_ids:
+            if i in self.rows and self.rows[i].shop_id == ctx.shop_id:
+                self.rows[i] = replace(self.rows[i], attached_at=None)
+        self.journal.append(("detach", sorted(media_ids)))
+
+    async def list(self, ctx, media_ids):
+        return [m for i, m in sorted(self.rows.items()) if i in media_ids and m.shop_id == ctx.shop_id]
+
 
 class FakeStorage(ObjectStoragePort):
     """객체는 {키: ObjectInfo}. 서명 URL 은 키와 형식이 보이는 가짜 문자열이다."""
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/media -q -p no:cacheprovider`
Expected: 수집 단계 오류 — `ImportError: cannot import name 'MediaClaimAlreadyAttachedError' from 'hub.app.errors'`.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/dtos/media_urls.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediaUrls:
    """사진·영상 하나의 읽기 URL 과 표시용 정보. 목록·달력·피드·미리보기는 thumb, 상세 넘기기는 display
    (영상은 None — 포스터 thumb 를 쓴다), 크게 보기·원본 저장·영상 재생은 original 을 쓴다.

    URL 은 매장 시간대 04:00 기준으로 하루 동안 같고 최대 48시간 유효하다. 앱은 media_id 를 캐시 키로 쓴다.
    """

    media_id: int
    kind: str                     # photo · video
    original_url: str
    display_url: str | None
    thumb_url: str
    width: int
    height: int
    duration_seconds: int | None
```

`backend/apps/hub/app/ports/media_library_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.media_urls import MediaUrls
from hub.app.dtos.shop_context import ShopContext


class MediaLibraryPort(ABC):
    """구현: media. 사용: visit(기록의 사진·영상), customer(반려동물 프로필 사진).

    media 는 어느 기록이 미디어를 가져갔는지 모른다 — 가져갔다는 사실(attached_at)만 안다. 연결은 가져간 쪽이
    자기 표에 적는다. 가져가지 않은 채 하루가 지난 미디어는 정리 스크립트가 지운다(설계 7.5).
    """

    @abstractmethod
    async def claim(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str]:
        """미디어를 가져간다(attached_at 을 찍는다). 돌려주는 값은 {media_id: kind(photo·video)}.

        전부 되거나 전부 안 된다 — 하나라도 안 되면 아무것도 바꾸지 않고 허브 오류를 던진다:
        MediaClaimNotFoundError(없거나 다른 매장), MediaClaimNotReadyError(아직 확인 전),
        MediaClaimAlreadyAttachedError(이미 다른 기록이 가져갔다). 조건부 UPDATE 라 네트워크가 없고,
        방문 행을 잠근 채 불러도 된다. 두 요청이 같은 미디어를 동시에 가져가면 늦은 쪽이 AlreadyAttached 다.
        """

    @abstractmethod
    async def release(self, ctx: ShopContext, media_ids: list[int]) -> None:
        """가져간 것을 놓는다. 놓인 미디어는 다시 가져갈 수 있고, 아무도 가져가지 않으면 정리 스크립트가 지운다."""

    @abstractmethod
    async def read_urls(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, MediaUrls]:
        """준비된 이 매장의 미디어의 읽기 URL. 없거나 준비 전인 ID 는 빠진다. 서명은 계산이라 네트워크가 없다."""
```

`backend/apps/hub/app/errors.py`:

```diff
@@ -62,3 +62,23 @@ class WithdrawalShopCloseConfirmRequiredError(HubPortError):
     """탈퇴하면 혼자 운영하던 매장이 닫힌다 — 확인을 받아야 한다."""
 
     code = "SHOP_CLOSE_CONFIRM_REQUIRED"
+
+
+# --- MediaLibraryPort.claim (구현: media, 소비: visit) -------------------------------------------
+
+class MediaClaimNotFoundError(HubPortError):
+    """없거나 다른 매장의 미디어다."""
+
+    code = "MEDIA_NOT_FOUND"
+
+
+class MediaClaimNotReadyError(HubPortError):
+    """아직 확인(confirm) 전이다 — 다 올리고 확인한 뒤에 기록에 붙일 수 있다."""
+
+    code = "MEDIA_NOT_READY"
+
+
+class MediaClaimAlreadyAttachedError(HubPortError):
+    """이미 다른 기록이 가져간 미디어다. 한 객체는 한 기록에만 붙는다."""
+
+    code = "MEDIA_ALREADY_ATTACHED"
```

`backend/core/hub_errors.py`:

```diff
@@ -10,6 +10,9 @@ from hub.app.errors import (
     FamilyNotFoundError,
     FamilyPetNotFoundError,
     FamilyPetPassedAwayError,
+    MediaClaimAlreadyAttachedError,
+    MediaClaimNotFoundError,
+    MediaClaimNotReadyError,
     ShopAccessClosedError,
     ShopAccessDeniedError,
     ShopAccessSuspendedError,
@@ -26,4 +29,7 @@ HUB_ERROR_STATUS: dict[type[Exception], int] = {
     ShopAccessSuspendedError: 403,
     WithdrawalOwnershipTransferRequiredError: 409,
     WithdrawalShopCloseConfirmRequiredError: 409,
+    MediaClaimNotFoundError: 404,
+    MediaClaimNotReadyError: 409,
+    MediaClaimAlreadyAttachedError: 409,
 }
```

`backend/apps/media/app/ports/output/media_repository.py`:

```diff
@@ -21,3 +21,15 @@ class MediaRepository(ABC):
     @abstractmethod
     async def mark_ready(self, ctx: ShopContext, media_id: int, size_bytes: int) -> bool:
         """pending 일 때만 ready 로 바꾼다(조건부 UPDATE). 바꿨으면 True — 동시에 두 번 확인해도 한 번만 바뀐다."""
+
+    @abstractmethod
+    async def attach_all(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str] | None:
+        """준비됐고 아무도 가져가지 않은 이 매장의 미디어에 attached_at 을 찍는다. 전부 찍었으면 {id: kind},
+        하나라도 못 찍었으면 아무것도 바꾸지 않고 None(세이브포인트)."""
+
+    @abstractmethod
+    async def detach(self, ctx: ShopContext, media_ids: list[int]) -> None: ...
+
+    @abstractmethod
+    async def list(self, ctx: ShopContext, media_ids: list[int]) -> list[MediaObject]:
+        """이 매장의 것만, 상태와 상관없이."""
```

`backend/apps/media/adapter/outbound/pg/media_pg_repository.py`:

```diff
@@ -51,3 +51,41 @@ class MediaPgRepository(MediaRepository):
             .values(status=READY, size_bytes=size_bytes, ready_at=func.now())
         )
         return result.rowcount == 1
+
+    async def attach_all(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str] | None:
+        wanted = set(media_ids)
+        savepoint = await self._session.begin_nested()
+        # 조건부 UPDATE — 같은 미디어를 동시에 가져가는 두 요청 가운데 늦은 쪽은 앞선 쪽이 커밋할 때까지 행에서
+        # 기다렸다가 조건(attached_at IS NULL)을 다시 보고 0행이 된다.
+        rows = (
+            await self._session.execute(
+                update(MediaObjectOrm)
+                .where(MediaObjectOrm.id.in_(wanted), MediaObjectOrm.shop_id == ctx.shop_id,
+                       MediaObjectOrm.status == READY, MediaObjectOrm.attached_at.is_(None))
+                .values(attached_at=func.now())
+                .returning(MediaObjectOrm.id, MediaObjectOrm.kind)
+            )
+        ).all()
+        if len(rows) != len(wanted):
+            await savepoint.rollback()
+            return None
+        await savepoint.commit()
+        return {media_id: kind for media_id, kind in rows}
+
+    async def detach(self, ctx: ShopContext, media_ids: list[int]) -> None:
+        await self._session.execute(
+            update(MediaObjectOrm)
+            .where(MediaObjectOrm.id.in_(media_ids), MediaObjectOrm.shop_id == ctx.shop_id)
+            .values(attached_at=None)
+        )
+
+    async def list(self, ctx: ShopContext, media_ids: list[int]) -> list[MediaObject]:
+        rows = (
+            await self._session.execute(
+                select(MediaObjectOrm)
+                .where(MediaObjectOrm.id.in_(media_ids), MediaObjectOrm.shop_id == ctx.shop_id)
+                .order_by(MediaObjectOrm.id)
+                .execution_options(populate_existing=True)
+            )
+        ).scalars()
+        return [to_media(row) for row in rows]
```

`backend/apps/media/app/use_cases/media_library_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.media_urls import MediaUrls
from hub.app.dtos.shop_context import ShopContext
from hub.app.errors import MediaClaimAlreadyAttachedError, MediaClaimNotFoundError, MediaClaimNotReadyError
from hub.app.ports.media_library_port import MediaLibraryPort
from media.app.ports.output.media_repository import MediaRepository
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.domain.services.url_expiry import signing_window


class MediaLibraryInteractor(MediaLibraryPort):
    """허브의 MediaLibraryPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""

    def __init__(self, media: MediaRepository, storage: ObjectStoragePort, now: Callable[[], datetime]) -> None:
        self._media = media
        self._storage = storage
        self._now = now

    async def claim(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str]:
        if not media_ids:
            return {}
        claimed = await self._media.attach_all(ctx, media_ids)
        if claimed is not None:
            return claimed
        # 왜 못 가져갔는지는 가져가기를 되돌린 뒤 읽어서 가린다 — 없는 것 → 준비 전 → 이미 붙음 순서.
        found = {m.id: m for m in await self._media.list(ctx, media_ids)}
        if any(media_id not in found for media_id in media_ids):
            raise MediaClaimNotFoundError("사진·영상을 찾을 수 없습니다.")
        if any(not m.ready for m in found.values()):
            raise MediaClaimNotReadyError("아직 올리는 중인 사진·영상입니다.")
        raise MediaClaimAlreadyAttachedError("이미 다른 기록에 붙은 사진·영상입니다.")

    async def release(self, ctx: ShopContext, media_ids: list[int]) -> None:
        if media_ids:
            await self._media.detach(ctx, media_ids)

    async def read_urls(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, MediaUrls]:
        if not media_ids:
            return {}
        window = signing_window(self._now(), ctx.timezone)
        sign = self._storage.presign_get
        return {
            m.id: MediaUrls(
                media_id=m.id, kind=m.kind, original_url=sign(m.keys.original, window),
                display_url=sign(m.keys.display, window) if m.keys.display else None,
                thumb_url=sign(m.keys.thumb, window), width=m.width, height=m.height,
                duration_seconds=m.duration_seconds,
            )
            for m in await self._media.list(ctx, media_ids) if m.ready
        }
```

`backend/apps/media/dependencies/media_library_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.media_library_port import MediaLibraryPort
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.dependencies.media_wiring import build_media_repository, get_object_storage, utc_now


def get_media_library_use_case(
    db: DbSession, storage: ObjectStoragePort = Depends(get_object_storage)
) -> MediaLibraryPort:
    return MediaLibraryInteractor(media=build_media_repository(db), storage=storage, now=utc_now)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/media tests/test_hub_errors.py -q -p no:cacheprovider` → 67 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 822 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 276 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `MediaPgRepository.attach_all`의 `MediaObjectOrm.attached_at.is_(None)` 조건을 뺀다 → `test_같은_미디어를_동시에_가져가면_늦은_쪽은_못_가져간다` 실패.
- `MediaLibraryInteractor.read_urls`의 `if m.ready`를 뺀다 → `test_읽기_URL_은_준비된_것만…` 실패.
- `MediaLibraryInteractor.claim`의 `if any(media_id not in found …)`를 `if False:`로 → `test_하나라도_안_되면…`[shop 2]·`test_없는_ID_는_NOT_FOUND_다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(hub): MediaLibraryPort — 기록이 미디어를 가져가고(claim, 전부 되거나 전부 안 됨) 놓고 읽기 URL 을 받는다, media 가 구현한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 메뉴 정가 — `service_menus.price`(0008, NULL 이면 가격 미정), 메뉴 만들기·고치기·목록이 정가를 주고받는다

**Files:**
- Modify: `backend/apps/visit/domain/entities/menu.py`
- Modify: `backend/apps/visit/adapter/outbound/orm/visit_orm.py`
- Create: `backend/alembic/versions/0008_service_menu_price.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/create_menu_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/list_menus_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/update_menu_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/v1/create_menu_router.py`
- Modify: `backend/apps/visit/adapter/inbound/api/v1/update_menu_router.py`
- Modify: `backend/apps/visit/adapter/outbound/mappers/visit_mapper.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py`
- Modify: `backend/apps/visit/app/dtos/create_menu_dto.py`
- Modify: `backend/apps/visit/app/dtos/menu_view_dto.py`
- Modify: `backend/apps/visit/app/dtos/update_menu_dto.py`
- Modify: `backend/apps/visit/app/ports/output/menu_repository.py`
- Modify: `backend/apps/visit/app/use_cases/create_menu_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/update_menu_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Modify: `backend/apps/visit/tests/adapter/test_archive_menu_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_create_menu_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_list_menus_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_menu_pg_repository.py`
- Modify: `backend/apps/visit/tests/adapter/test_update_menu_router.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_create_menu_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_update_menu_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/builders.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: 기존 메뉴 슬라이스 넷(목록·만들기·고치기·보관), `Menu`, `MenuView`, `MenuRepository.create/update`, `FakeMenus`, `visit.tests.helpers.builders.menu`.
- Produces: `Menu.price: int | None`(마지막 필드), `MenuView.price`, `CreateMenuCommand.price`·`UpdateMenuCommand.price`; `MenuRepository.create(ctx, name, default_duration_minutes, price)`, `update(ctx, menu_id, name, default_duration_minutes, sort_order, price)`; 스키마 `create_menu_schema.Price`(0~100,000,000) — 요청의 `price`는 두 스키마 모두 기본값 None; 응답 `MenuSchema.price`; `FakeMenus.seed(…, price=None)`, `builders.menu(…, price=None)`. 작업 6 이 정가를 기록 항목 금액을 미리 채우는 값으로 쓴다(앱). CHECK `ck_service_menus_price`.

기록 화면이 실제 메뉴의 금액을 미리 채우려면 메뉴에 정가가 있어야 한다(설계 6.1·10.1 ⑥). 정가가 없으면 가격 미정이다. `PUT /menus/{id}`는 전체 교체라 `price`를 보내지 않으면 미정이 된다 — ④ 이전 앱이 그대로 불러도 422 가 나지 않게 기본값을 둔다. **설계와 다른 점**: CHECK 는 ≥0 이 아니라 0~1억(기록 금액의 입력 경계와 같다). 기존 메뉴 테스트는 새 인자·칸만 더한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_archive_menu_router.py`:

```diff
@@ -3,7 +3,7 @@ from visit.app.dtos.menu_view_dto import MenuView
 from visit.dependencies.archive_menu_provider import get_archive_menu_use_case
 from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
 
-ARCHIVED = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=True)
+ARCHIVED = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=True, price=None)
 
 
 async def test_사장은_메뉴를_보관한다():
```

`backend/apps/visit/tests/adapter/test_create_menu_router.py`:

```diff
@@ -4,7 +4,7 @@ from visit.dependencies.create_menu_provider import get_create_menu_use_case
 from visit.domain.errors import MenuNameTakenError
 from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
 
-NAIL = MenuView(menu_id=6, name="발톱", default_duration_minutes=None, sort_order=6, archived=False)
+NAIL = MenuView(menu_id=6, name="발톱", default_duration_minutes=None, sort_order=6, archived=False, price=None)
 
 
 async def test_사장은_메뉴를_만든다_201():
@@ -12,7 +12,7 @@ async def test_사장은_메뉴를_만든다_201():
     async with client(build_app(create_menu_router, get_create_menu_use_case, stub)) as c:
         response = await c.post("/v1/shops/3/menus", json={"name": " 발톱 "})
     assert (response.status_code, response.json()["menu_id"]) == (201, 6)
-    assert (stub.calls[0].name, stub.calls[0].default_duration_minutes) == ("발톱", None)
+    assert (stub.calls[0].name, stub.calls[0].default_duration_minutes, stub.calls[0].price) == ("발톱", None, None)
 
 
 async def test_직원은_메뉴를_만들지_못한다():
@@ -24,7 +24,7 @@ async def test_직원은_메뉴를_만들지_못한다():
 async def test_이름이_비었거나_길거나_소요가_문자열이면_422_다():
     async with client(build_app(create_menu_router, get_create_menu_use_case, Recorder(NAIL))) as c:
         for bad in ({"name": " "}, {"name": "가" * 31}, {"name": "발톱", "default_duration_minutes": "60"},
-                    {"name": "발\x00톱"}):
+                    {"name": "발\x00톱"}, {"name": "발톱", "price": -1}, {"name": "발톱", "price": 100_000_001}):
             assert error_of(await c.post("/v1/shops/3/menus", json=bad)) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_list_menus_router.py`:

```diff
@@ -3,14 +3,14 @@ from visit.app.dtos.menu_view_dto import MenuView
 from visit.dependencies.list_menus_provider import get_list_menus_use_case
 from visit.tests.helpers.api import STAFF, Recorder, build_app, client
 
-BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False)
+BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False, price=30000)
 
 
-async def test_직원도_메뉴표를_본다():
+async def test_직원도_정가가_든_메뉴표를_본다():
     stub = Recorder([BATH])
     async with client(build_app(list_menus_router, get_list_menus_use_case, stub, STAFF)) as c:
         response = await c.get("/v1/shops/3/menus")
         await c.get("/v1/shops/3/menus?include_archived=true")
     assert response.json() == {"items": [{"menu_id": 1, "name": "목욕", "default_duration_minutes": 60,
-                                          "sort_order": 1, "archived": False}]}
+                                          "sort_order": 1, "archived": False, "price": 30000}]}
     assert [q.include_archived for q in stub.calls] == [False, True]
```

`backend/apps/visit/tests/adapter/test_menu_pg_repository.py`:

```diff
@@ -18,7 +18,7 @@ async def _prepared(session, *shops):
 
 async def test_새_메뉴는_맨_뒤_순서다(db_session):
     menus = await _prepared(db_session, A)
-    nail = await menus.create(A, "발톱", None)
+    nail = await menus.create(A, "발톱", None, None)
     assert (nail.sort_order, nail.default_duration_minutes, nail.archived) == (6, None, False)
     assert [m.name for m in await menus.list(A, include_archived=False)][-1] == "발톱"
 
@@ -26,20 +26,20 @@ async def test_새_메뉴는_맨_뒤_순서다(db_session):
 async def test_순서값이_상한에_닿아도_새_메뉴_추가는_된다(db_session):
     menus = await _prepared(db_session, A)
     [bath, *_] = await menus.list(A, include_archived=False)
-    await menus.update(A, bath.id, bath.name, bath.default_duration_minutes, 32_767)
-    nail = await menus.create(A, "발톱", None)
+    await menus.update(A, bath.id, bath.name, bath.default_duration_minutes, 32_767, None)
+    nail = await menus.create(A, "발톱", None, None)
     assert nail.sort_order <= 32_767
 
 
 async def test_보관하지_않은_메뉴끼리_이름이_겹치면_MENU_NAME_TAKEN_이고_세션은_계속_쓴다(db_session):
     menus = await _prepared(db_session, A)
     with pytest.raises(MenuNameTakenError):
-        await menus.create(A, "목욕", 60)
+        await menus.create(A, "목욕", 60, None)
     [bath] = [m for m in await menus.list(A, include_archived=False) if m.name == "목욕"]
     await menus.archive(A, bath.id)
-    again = await menus.create(A, "목욕", 70)   # 보관한 이름은 다시 쓸 수 있다
+    again = await menus.create(A, "목욕", 70, None)   # 보관한 이름은 다시 쓸 수 있다
     with pytest.raises(MenuNameTakenError):
-        await menus.update(A, again.id, "위생", 60, 1)
+        await menus.update(A, again.id, "위생", 60, 1, None)
 
 
 async def test_보관은_처음_시각을_지키고_목록에서_빠진다(db_session):
@@ -57,8 +57,17 @@ async def test_다른_매장의_메뉴는_고치거나_보관하지_못한다(db
     menus = await _prepared(db_session, A, B)
     [theirs, *_] = await menus.list(B, include_archived=False)
     with pytest.raises(MenuNotFoundError):
-        await menus.update(A, theirs.id, "침입", 10, 1)
+        await menus.update(A, theirs.id, "침입", 10, 1, None)
     with pytest.raises(MenuNotFoundError):
         await menus.archive(A, theirs.id)
     [still, *_] = await menus.list(B, include_archived=False)
     assert (still.name, still.archived) == (theirs.name, False)
+
+
+async def test_정가를_넣고_바꾸고_비운다(db_session):
+    await SchedulePgRepository(db_session).ensure(A)
+    menus = MenuPgRepository(db_session)
+    nail = await menus.create(A, "발톱", None, 10_000)
+    assert nail.price == 10_000
+    assert (await menus.update(A, nail.id, "발톱", None, nail.sort_order, 12_000)).price == 12_000
+    assert (await menus.update(A, nail.id, "발톱", None, nail.sort_order, None)).price is None
```

`backend/apps/visit/tests/adapter/test_update_menu_router.py`:

```diff
@@ -4,7 +4,7 @@ from visit.dependencies.update_menu_provider import get_update_menu_use_case
 from visit.domain.errors import MenuNotFoundError
 from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
 
-BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False)
+BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False, price=None)
 BODY = {"name": "목욕", "default_duration_minutes": 60, "sort_order": 2}
 
 
@@ -12,7 +12,15 @@ async def test_사장은_메뉴를_고친다():
     stub = Recorder(BATH)
     async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
         assert (await c.put("/v1/shops/3/menus/1", json=BODY)).status_code == 200
-    assert (stub.calls[0].menu_id, stub.calls[0].sort_order) == (1, 2)
+    assert (stub.calls[0].menu_id, stub.calls[0].sort_order, stub.calls[0].price) == (1, 2, None)
+
+
+async def test_정가를_보내면_넘기고_보내지_않으면_미정이다():
+    stub = Recorder(BATH)
+    async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
+        await c.put("/v1/shops/3/menus/1", json={**BODY, "price": 35_000})
+        await c.put("/v1/shops/3/menus/1", json=BODY)
+    assert [call.price for call in stub.calls] == [35_000, None]
 
 
 async def test_직원은_메뉴를_고치지_못한다():
@@ -20,11 +28,12 @@ async def test_직원은_메뉴를_고치지_못한다():
         assert error_of(await c.put("/v1/shops/3/menus/1", json=BODY)) == (403, "PERMISSION_DENIED")
 
 
-async def test_순서값이_상한을_넘으면_422_다():
+async def test_순서값이나_정가가_범위를_넘으면_422_다():
     stub = Recorder(BATH)
     async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
-        body = {**BODY, "sort_order": 10000}
-        assert error_of(await c.put("/v1/shops/3/menus/1", json=body)) == (422, "VALIDATION_ERROR")
+        for body in ({**BODY, "sort_order": 10000}, {**BODY, "price": -1}, {**BODY, "price": 100_000_001},
+                     {**BODY, "price": "30000"}):
+            assert error_of(await c.put("/v1/shops/3/menus/1", json=body)) == (422, "VALIDATION_ERROR")
 
 
 async def test_없는_메뉴는_404_범위를_넘는_ID_는_422_다():
```

`backend/apps/visit/tests/app/use_cases/test_create_menu_interactor.py`:

```diff
@@ -10,7 +10,7 @@ from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, Journal
 async def test_설정을_준비한_뒤_만든다():
     journal = Journal()
     view = await CreateMenuInteractor(FakeSchedule(journal), FakeMenus(journal)).create_menu(
-        CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=None))
+        CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=None, price=None))
     assert (view.name, view.default_duration_minutes, view.archived) == ("발톱", None, False)
     assert journal == [("ensure", 1), ("create_menu", "발톱")]
 
@@ -19,7 +19,7 @@ async def test_소요_규칙에_어긋나면_쓰지_않는다():
     journal = Journal()
     with pytest.raises(VisitInputError):
         await CreateMenuInteractor(FakeSchedule(journal), FakeMenus(journal)).create_menu(
-            CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=15))
+            CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=15, price=None))
     assert journal == []
 
 
@@ -28,4 +28,10 @@ async def test_보관하지_않은_메뉴와_이름이_겹치면_MENU_NAME_TAKEN
     menus.seed("목욕")
     with pytest.raises(MenuNameTakenError):
         await CreateMenuInteractor(FakeSchedule(), menus).create_menu(
-            CreateMenuCommand(ctx=ctx(), name="목욕", default_duration_minutes=60))
+            CreateMenuCommand(ctx=ctx(), name="목욕", default_duration_minutes=60, price=None))
+
+
+async def test_정가를_함께_넣는다():
+    view = await CreateMenuInteractor(FakeSchedule(), FakeMenus()).create_menu(
+        CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=None, price=10_000))
+    assert view.price == 10_000
```

`backend/apps/visit/tests/app/use_cases/test_update_menu_interactor.py`:

```diff
@@ -7,13 +7,13 @@ from visit.tests.helpers.builders import ctx
 from visit.tests.helpers.fakes import FakeMenus
 
 
-async def test_이름_소요_순서를_바꾼다():
+async def test_이름_소요_순서_정가를_바꾼다():
     menus = FakeMenus()
-    bath = menus.seed("목욕")
+    bath = menus.seed("목욕", price=30_000)
     view = await UpdateMenuInteractor(menus).update_menu(
         UpdateMenuCommand(ctx=ctx(), menu_id=bath.id, name="목욕(대형견)", default_duration_minutes=90,
-                          sort_order=9))
-    assert (view.name, view.default_duration_minutes, view.sort_order) == ("목욕(대형견)", 90, 9)
+                          sort_order=9, price=45_000))
+    assert (view.name, view.default_duration_minutes, view.sort_order, view.price) == ("목욕(대형견)", 90, 9, 45_000)
 
 
 async def test_소요_규칙에_어긋나면_쓰지_않는다():
@@ -22,7 +22,7 @@ async def test_소요_규칙에_어긋나면_쓰지_않는다():
     with pytest.raises(VisitInputError):
         await UpdateMenuInteractor(menus).update_menu(
             UpdateMenuCommand(ctx=ctx(), menu_id=bath.id, name="목욕", default_duration_minutes=700,
-                              sort_order=1))
+                              sort_order=1, price=None))
     assert menus.journal == []
 
 
@@ -32,4 +32,4 @@ async def test_다른_매장의_메뉴는_MENU_NOT_FOUND_다():
     with pytest.raises(MenuNotFoundError):
         await UpdateMenuInteractor(menus).update_menu(
             UpdateMenuCommand(ctx=ctx(shop_id=1), menu_id=theirs.id, name="침입", default_duration_minutes=None,
-                              sort_order=1))
+                              sort_order=1, price=None))
```

`backend/apps/visit/tests/helpers/builders.py`:

```diff
@@ -39,9 +39,9 @@ def visit(**overrides) -> Visit:
 
 
 def menu(menu_id: int = 1, name: str = "목욕", minutes: int | None = 60, shop_id: int = 1,
-         archived: bool = False) -> Menu:
+         archived: bool = False, price: int | None = None) -> Menu:
     return Menu(id=menu_id, shop_id=shop_id, name=name, default_duration_minutes=minutes,
-                sort_order=menu_id, archived_at=kst(9, 1) if archived else None)
+                sort_order=menu_id, archived_at=kst(9, 1) if archived else None, price=price)
 
 
 def but(entity, **changes):
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -70,9 +70,9 @@ class FakeMenus(MenuRepository):
         self.rows: dict[int, Menu] = {}
         self._next = 1
 
-    def seed(self, name="목욕", minutes=60, shop_id=1, archived=False) -> Menu:
+    def seed(self, name="목욕", minutes=60, shop_id=1, archived=False, price=None) -> Menu:
         menu = Menu(id=self._next, shop_id=shop_id, name=name, default_duration_minutes=minutes,
-                    sort_order=self._next, archived_at=kst(9, 1) if archived else None)
+                    sort_order=self._next, archived_at=kst(9, 1) if archived else None, price=price)
         self.rows[menu.id] = menu
         self._next += 1
         return menu
@@ -96,17 +96,17 @@ class FakeMenus(MenuRepository):
         return [m for m in self.rows.values() if m.id in menu_ids and m.shop_id == ctx.shop_id
                 and not m.archived]
 
-    async def create(self, ctx, name, default_duration_minutes):
+    async def create(self, ctx, name, default_duration_minutes, price):
         self._check_name(ctx, name)
-        menu = self.seed(name=name, minutes=default_duration_minutes, shop_id=ctx.shop_id)
+        menu = self.seed(name=name, minutes=default_duration_minutes, shop_id=ctx.shop_id, price=price)
         self.journal.append(("create_menu", name))
         return menu
 
-    async def update(self, ctx, menu_id, name, default_duration_minutes, sort_order):
+    async def update(self, ctx, menu_id, name, default_duration_minutes, sort_order, price):
         current = self._find(ctx, menu_id)
         self._check_name(ctx, name, menu_id)
         self.rows[menu_id] = replace(current, name=name, default_duration_minutes=default_duration_minutes,
-                                     sort_order=sort_order)
+                                     sort_order=sort_order, price=price)
         self.journal.append(("update_menu", menu_id))
         return self.rows[menu_id]
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit -q -p no:cacheprovider`
Expected: 수집 단계 오류 4개 — `TypeError: MenuView.__init__() got an unexpected keyword argument 'price'`.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/entities/menu.py`:

```diff
@@ -14,6 +14,7 @@ class Menu:
     default_duration_minutes: int | None   # None 이면 매장 기본 소요
     sort_order: int
     archived_at: datetime | None
+    price: int | None   # 정가(원). None 이면 가격 미정 — 기록의 금액을 미리 채울 때만 쓴다
 
     @property
     def archived(self) -> bool:
```

`backend/apps/visit/adapter/outbound/orm/visit_orm.py`:

```diff
@@ -9,6 +9,7 @@ from sqlalchemy import (
     DateTime,
     ForeignKey,
     Index,
+    Integer,
     SmallInteger,
     String,
     Time,
@@ -95,6 +96,7 @@ class ServiceMenuOrm(Base):
             + _DURATION_RULE.format(col="default_duration_minutes"),
             name="ck_service_menus_duration",
         ),
+        CheckConstraint("price IS NULL OR price BETWEEN 0 AND 100000000", name="ck_service_menus_price"),
     )
 
     id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
@@ -103,6 +105,7 @@ class ServiceMenuOrm(Base):
     default_duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
     sort_order: Mapped[int] = mapped_column(SmallInteger)
     archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+    price: Mapped[int | None] = mapped_column(Integer)   # 정가(원). NULL 이면 가격 미정
     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`backend/alembic/versions/0008_service_menu_price.py`:

```python
"""메뉴 정가

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_menus", sa.Column("price", sa.Integer))   # NULL 이면 가격 미정
    op.create_check_constraint(
        "ck_service_menus_price", "service_menus", "price IS NULL OR price BETWEEN 0 AND 100000000"
    )


def downgrade() -> None:
    op.drop_constraint("ck_service_menus_price", "service_menus", type_="check")
    op.drop_column("service_menus", "price")
```

`backend/apps/visit/adapter/inbound/api/schemas/create_menu_schema.py`:

```diff
@@ -2,7 +2,7 @@ from __future__ import annotations
 
 from typing import Annotated
 
-from pydantic import AfterValidator, BaseModel, StrictInt, StringConstraints
+from pydantic import AfterValidator, BaseModel, Field, StrictInt, StringConstraints
 
 from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
 
@@ -10,10 +10,13 @@ MenuName = Annotated[
     str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
     AfterValidator(reject_control_chars),
 ]
+# 정가(원). 기록의 금액과 같은 상한이다(설계 9절 입력 경계).
+Price = Annotated[StrictInt, Field(ge=0, le=100_000_000)]
 
 
 class CreateMenuRequestSchema(BaseModel):
-    """기본 소요를 비우면 매장 기본 소요를 쓴다."""
+    """기본 소요를 비우면 매장 기본 소요를 쓴다. 정가를 비우면 가격 미정이다."""
 
     name: MenuName
     default_duration_minutes: StrictInt | None = None
+    price: Price | None = None
```

`backend/apps/visit/adapter/inbound/api/schemas/list_menus_schema.py`:

```diff
@@ -11,12 +11,13 @@ class MenuSchema(BaseModel):
     default_duration_minutes: int | None   # None 이면 매장 기본 소요
     sort_order: int
     archived: bool
+    price: int | None   # None 이면 가격 미정
 
     @classmethod
     def of(cls, view: MenuView) -> MenuSchema:
         return cls(menu_id=view.menu_id, name=view.name,
                    default_duration_minutes=view.default_duration_minutes, sort_order=view.sort_order,
-                   archived=view.archived)
+                   archived=view.archived, price=view.price)
 
 
 class MenuListSchema(BaseModel):
```

`backend/apps/visit/adapter/inbound/api/schemas/update_menu_schema.py`:

```diff
@@ -4,10 +4,13 @@ from typing import Annotated
 
 from pydantic import BaseModel, Field, StrictInt
 
-from visit.adapter.inbound.api.schemas.create_menu_schema import MenuName
+from visit.adapter.inbound.api.schemas.create_menu_schema import MenuName, Price
 
 
 class UpdateMenuRequestSchema(BaseModel):
+    """전체 교체다. 정가를 보내지 않으면 가격 미정(None)이 된다 — ④ 이전 앱도 그대로 부를 수 있게 기본값을 둔다."""
+
     name: MenuName
     default_duration_minutes: StrictInt | None
     sort_order: Annotated[StrictInt, Field(ge=0, le=9_999)]
+    price: Price | None = None
```

`backend/apps/visit/adapter/inbound/api/v1/create_menu_router.py`:

```diff
@@ -18,6 +18,7 @@ async def create_menu(
     use_case: CreateMenuUseCase = Depends(get_create_menu_use_case),
 ) -> MenuSchema:
     view = await use_case.create_menu(
-        CreateMenuCommand(ctx=ctx, name=body.name, default_duration_minutes=body.default_duration_minutes)
+        CreateMenuCommand(ctx=ctx, name=body.name, default_duration_minutes=body.default_duration_minutes,
+                          price=body.price)
     )
     return MenuSchema.of(view)
```

`backend/apps/visit/adapter/inbound/api/v1/update_menu_router.py`:

```diff
@@ -21,6 +21,7 @@ async def update_menu(
 ) -> MenuSchema:
     view = await use_case.update_menu(
         UpdateMenuCommand(ctx=ctx, menu_id=menu_id, name=body.name,
-                          default_duration_minutes=body.default_duration_minutes, sort_order=body.sort_order)
+                          default_duration_minutes=body.default_duration_minutes, sort_order=body.sort_order,
+                          price=body.price)
     )
     return MenuSchema.of(view)
```

`backend/apps/visit/adapter/outbound/mappers/visit_mapper.py`:

```diff
@@ -9,7 +9,7 @@ def to_menu(orm: ServiceMenuOrm) -> Menu:
     return Menu(
         id=orm.id, shop_id=orm.shop_id, name=orm.name,
         default_duration_minutes=orm.default_duration_minutes, sort_order=orm.sort_order,
-        archived_at=orm.archived_at,
+        archived_at=orm.archived_at, price=orm.price,
     )
```

`backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py`:

```diff
@@ -43,7 +43,9 @@ class MenuPgRepository(MenuRepository):
         ).scalars()
         return [to_menu(row) for row in rows]
 
-    async def create(self, ctx: ShopContext, name: str, default_duration_minutes: int | None) -> Menu:
+    async def create(
+        self, ctx: ShopContext, name: str, default_duration_minutes: int | None, price: int | None
+    ) -> Menu:
         next_order = (
             select(func.least(func.coalesce(func.max(ServiceMenuOrm.sort_order), 0) + 1, 32_767))
             .where(ServiceMenuOrm.shop_id == ctx.shop_id)
@@ -54,7 +56,7 @@ class MenuPgRepository(MenuRepository):
                 await self._session.execute(
                     insert(ServiceMenuOrm)
                     .values(shop_id=ctx.shop_id, name=name,
-                            default_duration_minutes=default_duration_minutes, sort_order=next_order)
+                            default_duration_minutes=default_duration_minutes, sort_order=next_order, price=price)
                     .returning(ServiceMenuOrm.id)
                 )
             ).scalar_one()
@@ -62,13 +64,14 @@ class MenuPgRepository(MenuRepository):
 
     async def update(
         self, ctx: ShopContext, menu_id: int, name: str, default_duration_minutes: int | None,
-        sort_order: int,
+        sort_order: int, price: int | None,
     ) -> Menu:
         async with self._name_guard():
             await self._session.execute(
                 update(ServiceMenuOrm)
                 .where(ServiceMenuOrm.id == menu_id, ServiceMenuOrm.shop_id == ctx.shop_id)
-                .values(name=name, default_duration_minutes=default_duration_minutes, sort_order=sort_order)
+                .values(name=name, default_duration_minutes=default_duration_minutes, sort_order=sort_order,
+                        price=price)
             )
         return await self._get(ctx, menu_id)
```

`backend/apps/visit/app/dtos/create_menu_dto.py`:

```diff
@@ -10,3 +10,4 @@ class CreateMenuCommand:
     ctx: ShopContext
     name: str
     default_duration_minutes: int | None
+    price: int | None
```

`backend/apps/visit/app/dtos/menu_view_dto.py`:

```diff
@@ -12,8 +12,9 @@ class MenuView:
     default_duration_minutes: int | None
     sort_order: int
     archived: bool
+    price: int | None
 
     @classmethod
     def of(cls, menu: Menu) -> MenuView:
         return cls(menu_id=menu.id, name=menu.name, default_duration_minutes=menu.default_duration_minutes,
-                   sort_order=menu.sort_order, archived=menu.archived)
+                   sort_order=menu.sort_order, archived=menu.archived, price=menu.price)
```

`backend/apps/visit/app/dtos/update_menu_dto.py`:

```diff
@@ -12,3 +12,4 @@ class UpdateMenuCommand:
     name: str
     default_duration_minutes: int | None
     sort_order: int
+    price: int | None
```

`backend/apps/visit/app/ports/output/menu_repository.py`:

```diff
@@ -18,13 +18,15 @@ class MenuRepository(ABC):
         """요청 본문이 고른 메뉴 가운데 이 매장의 보관하지 않은 것만."""
 
     @abstractmethod
-    async def create(self, ctx: ShopContext, name: str, default_duration_minutes: int | None) -> Menu:
+    async def create(
+        self, ctx: ShopContext, name: str, default_duration_minutes: int | None, price: int | None
+    ) -> Menu:
         """맨 뒤 순서로 넣는다. 보관하지 않은 메뉴와 이름이 겹치면 MenuNameTakenError."""
 
     @abstractmethod
     async def update(
         self, ctx: ShopContext, menu_id: int, name: str, default_duration_minutes: int | None,
-        sort_order: int,
+        sort_order: int, price: int | None,
     ) -> Menu:
         """없거나 다른 매장이면 MenuNotFoundError. 이름이 겹치면 MenuNameTakenError."""
```

`backend/apps/visit/app/use_cases/create_menu_interactor.py`:

```diff
@@ -18,5 +18,5 @@ class CreateMenuInteractor(CreateMenuUseCase):
             check_duration(command.default_duration_minutes)
         await self._schedule.ensure(command.ctx)   # 메뉴는 설정 행을 가리킨다(외래 키)
         return MenuView.of(
-            await self._menus.create(command.ctx, command.name, command.default_duration_minutes)
+            await self._menus.create(command.ctx, command.name, command.default_duration_minutes, command.price)
         )
```

`backend/apps/visit/app/use_cases/update_menu_interactor.py`:

```diff
@@ -8,7 +8,7 @@ from visit.domain.services.visit_schedule import check_duration
 
 
 class UpdateMenuInteractor(UpdateMenuUseCase):
-    """이름·기본 소요·순서를 바꾼다. 이미 잡힌 예약의 소요는 그대로다(방문이 자기 소요를 가진다)."""
+    """이름·기본 소요·순서·정가를 바꾼다. 이미 잡힌 예약의 소요와 이미 쓴 기록의 금액은 그대로다(자기 값을 가진다)."""
 
     def __init__(self, menus: MenuRepository) -> None:
         self._menus = menus
@@ -18,6 +18,6 @@ class UpdateMenuInteractor(UpdateMenuUseCase):
             check_duration(command.default_duration_minutes)
         menu = await self._menus.update(
             command.ctx, command.menu_id, command.name, command.default_duration_minutes,
-            command.sort_order,
+            command.sort_order, command.price,
         )
         return MenuView.of(menu)
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -30,7 +30,8 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "POST /visit-drafts 는 카톡 글을 규칙으로 읽어 날짜·시각·보호자 후보·메뉴를 짐작한 초안입니다"
                 "(저장하지 않고, 글을 남기지 않습니다). "
                 "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
-                "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}, "
+                "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}(이름·기본 소요·순서·정가 price, "
+                "원 단위, 비우면 가격 미정), "
                 "POST /menus/{menu_id}/archive(메뉴표 — 지우지 않고 보관)도 있습니다. "
                 "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴 수정은 shop:update(사장)가 필요합니다. "
                 "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit tests/test_schema_drift.py -q -p no:cacheprovider` → 361 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 824 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 277 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `MenuPgRepository.update`의 `.values(…, price=price)`에서 `price=price`를 뺀다 → `test_정가를_넣고_바꾸고_비운다` 실패.
- `create_menu_schema.Price`를 `StrictInt`로(경계 없이) → `test_순서값이나_정가가_범위를_넘으면_422_다`·`test_이름이_비었거나…` 실패.
- `update_menu_router`에서 `price=body.price`를 `price=None`으로 → `test_정가를_보내면_넘기고_보내지_않으면_미정이다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 메뉴 정가 — service_menus.price(0008, NULL 이면 가격 미정), 메뉴 만들기·고치기·목록이 정가를 주고받는다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 미용 기록 쓰기 — `PUT /visits/{id}/record`(전체 교체·버전), 기록 표 셋(0009), 미디어 가져가기·놓기, 최근 방문이면 현재 몸무게(`set_pet_weight`)

**Files:**
- Modify: `backend/apps/hub/app/ports/customer_directory_port.py`
- Create: `backend/apps/visit/domain/entities/visit_record.py`
- Create: `backend/apps/visit/domain/value_objects/record_input.py`
- Modify: `backend/apps/visit/domain/errors.py`
- Create: `backend/apps/visit/domain/services/visit_record_rules.py`
- Modify: `backend/apps/visit/adapter/outbound/orm/visit_orm.py`
- Create: `backend/alembic/versions/0009_visit_records.py`
- Create: `backend/apps/visit/app/ports/output/visit_record_repository.py`
- Modify: `backend/apps/customer/adapter/outbound/pg/pet_pg_repository.py`
- Modify: `backend/apps/customer/app/ports/output/pet_repository.py`
- Modify: `backend/apps/customer/app/use_cases/customer_directory_interactor.py`
- Modify: `backend/apps/customer/tests/adapter/test_pet_pg_repository.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`
- Modify: `backend/apps/customer/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/adapter/inbound/api/error_map.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/put_visit_record_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/record_view_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/put_visit_record_router.py`
- Create: `backend/apps/visit/adapter/outbound/mappers/visit_record_mapper.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Create: `backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`
- Create: `backend/apps/visit/app/dtos/put_visit_record_dto.py`
- Create: `backend/apps/visit/app/dtos/record_view_dto.py`
- Create: `backend/apps/visit/app/ports/input/put_visit_record_use_case.py`
- Modify: `backend/apps/visit/app/ports/output/menu_repository.py`
- Modify: `backend/apps/visit/app/ports/output/visit_history_repository.py`
- Modify: `backend/apps/visit/app/services/completion_effects.py`
- Create: `backend/apps/visit/app/services/record_reader.py`
- Create: `backend/apps/visit/app/use_cases/put_visit_record_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Modify: `backend/apps/visit/dependencies/hub_ports.py`
- Create: `backend/apps/visit/dependencies/put_visit_record_provider.py`
- Modify: `backend/apps/visit/dependencies/visit_wiring.py`
- Create: `backend/apps/visit/tests/adapter/test_put_visit_record_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Create: `backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`
- Create: `backend/apps/visit/tests/app/services/test_sync_pet_weight.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_put_visit_record_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Create: `backend/apps/visit/tests/domain/test_visit_record_rules.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/integration/support.py`
- Modify: `backend/tests/integration/test_media_flow_wiring.py`
- Create: `backend/tests/integration/test_visit_record_locking.py`
- Create: `backend/tests/integration/test_visit_record_wiring.py`

**Interfaces:**
- Consumes: 작업 4 의 `MediaLibraryPort`·허브 오류·`get_media_library_use_case`, 작업 5 의 `Menu`·`MenuRepository`; `visit_locking.lock_visits`, `completion_effects`, `VisitHistoryRepository`, `VisitPgRepository`, `CustomerDirectoryPort`, `STARTED_STATUSES`.
- Produces: 도메인 `visit.domain.entities.visit_record` — `BEFORE`·`AFTER`·`PHASES`·`PAYMENT_METHODS`, `RecordItem(menu_id, amount)`, `RecordMedia(media_id, kind, phase, sort_order)`, `VisitRecord(visit_id, weight_kg, care_note, internal_note, payment_method, total_amount, items, media, version, created_by_member_id, updated_by_member_id)`; `visit.domain.value_objects.record_input` — `MediaPlacement(media_id, phase, sort_order)`, `RecordInput(…).has_money`; `visit.domain.services.visit_record_rules` — `MEDIA_LIMITS`, `check_recordable(visit)`, `check_input(visit, record)`, `check_media_limits(kinds)`, `check_version(current, requested)`, `next_version(current)`, `cover_media_id(media) -> int | None`; 오류 `VisitNoRecordYetError`(409)·`RecordNotFoundError`(404)·`RecordVersionConflictError`(409)·`RecordWeightWithoutPetError`(422)·`RecordItemDuplicateError`(422)·`RecordMediaLimitError`(MEDIA_LIMIT_EXCEEDED, 422)·`RecordSalesForbiddenError`(PERMISSION_DENIED, 403); `VisitRecordRepository` — `get(ctx, visit_id) -> VisitRecord | None`, `save(ctx, record) -> VisitRecord`; `VisitRecordPgRepository`; `visit_wiring.build_record_repository(db)`; `VisitHistoryRepository.latest_started_of_pet(ctx, pet_id) -> int | None`; `MenuRepository.list_by_ids(ctx, ids)`(보관한 것도); `completion_effects.sync_pet_weight(ctx, visit, weight_kg, history, directory)`; `CustomerDirectoryPort.set_pet_weight(ctx, pet_id, weight_kg)` + customer `PetRepository.set_weight`; `record_reader.describe_record(ctx, record, menus, library) -> RecordView`; DTO `RecordView`·`RecordItemView`·`RecordMediaView`·`PutVisitRecordCommand(ctx, visit_id, version, record)`; `PutVisitRecordInteractor(visits, history, records, menus, directory, library)`; 스키마 `RecordSchema`·`PutVisitRecordRequestSchema.to_input()`; 자리 `visit.dependencies.hub_ports.get_media_library`; 스텁 `FakeRecords(visits)`·`FakeLibrary`(허브 오류를 같은 조건에서), `FakeDirectory.set_pet_weight`, customer `FakePets.set_weight`; 통합 도우미 `tests/integration/support.py`의 `PHOTO`·`issue_media`·`upload_media`·`ready_photo`.

④의 중심이다(설계 6.1·8·9). 기록 쓰기는 방문 쓰기와 같은 잠금(고객 행 → 방문 행)을 거치고, 다시 읽은 방문·기록으로 판정한다: 미용 중·완료만(409), 돈 칸은 sales:write(잠그기 전에 403), 보호자만의 방문은 몸무게 없음(422), 같은 메뉴 두 번(422), 버전 불일치(409 — 업로드 대기열이 덧붙인 사진을 모르고 지우지 않게, 설계 8절·M19). 새로 든 미디어만 가져가고(`claim`, 종류를 받는다) 빠진 미디어는 놓는다(`release`) — 한도 검사는 가져간 뒤에 해서, 넘으면 요청 전체가 되돌려진다. 몸무게는 그 방문이 그 아이의 가장 최근 시작한 방문일 때만 현재 몸무게가 된다(M14). **설계와 다른 점**(결정 기록 007): `visit_record_media.kind`를 둔다, `set_pet_weight`에 `at`이 없다, 빠진 미디어를 바로 지우지 않는다(정리 스크립트), 보관한 메뉴도 항목에 쓸 수 있다, 같은 칸·같은 순서는 유일 색인이 막는다. 통합 테스트는 어제 11시 예약을 시작해 쓴다 — 실행 시각과 상관없이 돈다. 사진 올리기 도우미가 둘째 사용처를 만나 `test_media_flow_wiring.py`에서 `support.py`로 옮긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/adapter/test_pet_pg_repository.py`:

```diff
@@ -132,3 +132,12 @@ async def test_질병_종류는_칩_순서대로다(db_session):
     types = await ConditionTypePgRepository(db_session).list_all()
     assert [t.code for t in types][:2] == ["patella_luxation", "heart_disease"]
     assert (types[-1].code, types[-1].label) == ("other", "기타")
+
+
+async def test_현재_몸무게만_바꾸고_다른_매장의_아이는_건드리지_않는다(db_session):
+    repo = PetPgRepository(db_session)
+    pet = await repo.add(A, await _family(db_session), pet_profile())
+    await repo.set_weight(A, pet.id, Decimal("4.1"))
+    await repo.set_weight(B, pet.id, Decimal("9.9"))
+    got = await repo.get(A, pet.id)
+    assert (got.weight_kg, got.name) == (Decimal("4.1"), pet.name)
```

`backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`:

```diff
@@ -169,3 +169,11 @@ async def test_익명화한_고객과_다른_매장의_ID_는_후보가_아니
     await customers.anonymize(ctx(), gone.id)
     search.matches = [gone.id, other.id]
     assert await directory.find_draft_candidates(ctx(), ("김민지",)) == []
+
+
+async def test_몸무게는_반려동물_저장소로_넘긴다():
+    journal, customers, pets, _, directory = _directory()
+    customer = customers.seed()
+    pet = pets.seed(customer.id)
+    await directory.set_pet_weight(ctx(), pet.id, Decimal("4.1"))
+    assert (pets.rows[pet.id].weight_kg, journal[-1]) == (Decimal("4.1"), ("set_weight", pet.id, Decimal("4.1")))
```

`backend/apps/customer/tests/helpers/fakes.py`:

```diff
@@ -147,6 +147,10 @@ class FakePets(PetRepository):
         self.journal.append(("set_passed_away", pet_id, passed_away))
         return self.rows[pet_id]
 
+    async def set_weight(self, ctx, pet_id, weight_kg):
+        self.rows[pet_id] = replace(self._owned(ctx, pet_id), weight_kg=weight_kg)
+        self.journal.append(("set_weight", pet_id, weight_kg))
+
     async def count_for_customer(self, ctx, customer_id):
         return len([p for p in self.rows.values() if p.customer_id == customer_id])
```

`backend/apps/visit/tests/adapter/test_put_visit_record_router.py`:

```python
from decimal import Decimal

from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
from visit.app.dtos.record_view_dto import RecordItemView, RecordMediaView, RecordView
from visit.dependencies.put_visit_record_provider import get_put_visit_record_use_case
from visit.domain.errors import (
    RecordItemDuplicateError,
    RecordSalesForbiddenError,
    RecordVersionConflictError,
    VisitNoRecordYetError,
)
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of

VIEW = RecordView(
    visit_id=4, weight_kg=Decimal("3.4"), care_note="케어", internal_note=None, payment_method="card",
    total_amount=28_000, items=[RecordItemView(menu_id=1, name="목욕", amount=28_000)],
    media=[RecordMediaView(media_id=51, kind="photo", phase="after", sort_order=0, original_url="o", display_url="d",
                           thumb_url="t", width=3000, height=2000, duration_seconds=None)],
    version=2,
)
BODY = {"version": 1, "weight_kg": 3.4, "care_note": " 케어 ", "payment_method": "card", "total_amount": 28000,
        "items": [{"menu_id": 1, "amount": 28000}], "media": [{"media_id": 51, "phase": "after", "sort_order": 0}]}


async def test_직원은_기록을_쓰고_기록_전체를_받는다():
    stub = Recorder(VIEW)
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/visits/4/record", json=BODY)
    assert (response.status_code, response.json()["version"], response.json()["weight_kg"]) == (200, 2, 3.4)
    call = stub.calls[0]
    assert (call.visit_id, call.version, call.record.weight_kg, call.record.care_note) == (4, 1, Decimal("3.4"), "케어")
    assert (call.record.items[0].amount, call.record.media[0].phase) == (28000, "after")


async def test_빈_몸통은_모든_칸을_비운_첫_기록이다():
    stub = Recorder(VIEW)
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, stub)) as c:
        await c.put("/v1/shops/3/visits/4/record", json={})
    wanted = stub.calls[0].record
    assert (stub.calls[0].version, wanted.items, wanted.media, wanted.has_money) == (None, (), (), False)


async def test_기록_권한이_없으면_403():
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, Recorder(VIEW), READ_ONLY)) as c:
        assert error_of(await c.put("/v1/shops/3/visits/4/record", json=BODY)) == (403, "PERMISSION_DENIED")


async def test_입력_경계를_넘으면_422_다():
    placement = {"media_id": 51, "phase": "after", "sort_order": 0}
    bad_bodies = [
        {"weight_kg": 0}, {"weight_kg": 1000}, {"weight_kg": 3.25}, {"total_amount": -1},
        {"total_amount": 100_000_001}, {"items": [{"menu_id": 1, "amount": 100_000_001}]},
        {"payment_method": "point"}, {"care_note": "가" * 1001}, {"internal_note": "a\x00b"},
        {"media": [placement, placement]},
        {"media": [placement, {**placement, "media_id": 52}]},              # 같은 자리
        {"media": [{**placement, "sort_order": 100}]}, {"media": [{**placement, "phase": "during"}]},
        {"media": [{**placement, "media_id": 60 + i, "sort_order": i} for i in range(34)]},
        {"version": 0}, {"version": "1"},
    ]
    async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, Recorder(VIEW))) as c:
        for body in bad_bodies:
            assert error_of(await c.put("/v1/shops/3/visits/4/record", json=body)) == (422, "VALIDATION_ERROR"), body


async def test_도메인_거절은_코드로_나간다():
    cases = [(VisitNoRecordYetError("아직"), (409, "VISIT_NO_RECORD_YET")),
             (RecordVersionConflictError("버전"), (409, "RECORD_VERSION_CONFLICT")),
             (RecordItemDuplicateError("중복"), (422, "RECORD_ITEM_DUPLICATE")),
             (RecordSalesForbiddenError("돈"), (403, "PERMISSION_DENIED"))]
    for error, expected in cases:
        async with client(build_app(put_visit_record_router, get_put_visit_record_use_case, Recorder(error=error))) as c:
            assert error_of(await c.put("/v1/shops/3/visits/4/record", json=BODY)) == expected
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py`:

```diff
@@ -189,3 +189,14 @@ async def test_장부_질문들(db_session):
     await repo.clear_memos(A, 1)
     assert {v.memo for v in await repo.list_between(A, kst(9, 1), kst(11, 1))} == {None}
     assert [v.memo for v in await repo.list_between(B, kst(9, 1), kst(11, 1))] == ["남의"]
+
+
+async def test_그_아이의_가장_최근_시작한_방문(db_session):
+    repo = VisitPgRepository(db_session)
+    assert await repo.latest_started_of_pet(A, 101) is None
+    await insert_visit(db_session, kst(9, 1, 14), "completed")
+    latest = await insert_visit(db_session, kst(9, 20, 14), "in_progress")
+    await insert_visit(db_session, kst(9, 25, 14), "reserved")
+    await insert_visit(db_session, kst(9, 22, 14), "canceled")
+    await insert_visit(db_session, kst(9, 21, 14), "completed", shop_id=2)
+    assert await repo.latest_started_of_pet(A, 101) == latest
```

`backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`:

```python
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


def _record(visit_id, version=1, items=(), media=(), weight=None, member=11):
    return VisitRecord(visit_id=visit_id, weight_kg=weight, care_note="케어", internal_note=None,
                       payment_method="cash", total_amount=30_000, items=tuple(items), media=tuple(media),
                       version=version, created_by_member_id=member, updated_by_member_id=member)


async def _setup(session):
    await SchedulePgRepository(session).ensure(A)
    bath, trim, *_ = [m.id for m in await MenuPgRepository(session).list(A, include_archived=False)]
    visit_id = await insert_visit(session, kst(9, 23, 14), "in_progress")
    return VisitRecordPgRepository(session), visit_id, bath, trim


async def test_없으면_넣고_있으면_바꾸고_항목과_미디어는_통째로_바꾼다(db_session):
    repo, visit_id, bath, trim = await _setup(db_session)
    assert await repo.get(A, visit_id) is None
    first = await repo.save(A, _record(visit_id, items=[RecordItem(bath, 30_000)], weight=Decimal("3.2"),
                                       media=[RecordMedia(7, "photo", "after", 0), RecordMedia(8, "photo", "before", 0)]))
    assert (first.version, first.weight_kg, [m.media_id for m in first.media]) == (1, Decimal("3.2"), [8, 7])
    second = await repo.save(A, _record(visit_id, version=2, items=[RecordItem(trim, 50_000)],
                                        media=[RecordMedia(9, "video", "after", 0)], member=12))
    assert (second.version, second.items, second.media) == (2, (RecordItem(trim, 50_000),),
                                                            (RecordMedia(9, "video", "after", 0),))
    assert (second.created_by_member_id, second.updated_by_member_id) == (11, 12)


async def test_다른_매장의_방문의_기록은_없는_것이다(db_session):
    repo, visit_id, _, _ = await _setup(db_session)
    await repo.save(A, _record(visit_id))
    assert await repo.get(B, visit_id) is None


async def test_한_미디어는_한_기록에만_붙는다(db_session):
    repo, visit_id, _, _ = await _setup(db_session)
    other = await insert_visit(db_session, kst(9, 24, 14), "in_progress")
    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))
    with pytest.raises(IntegrityError):
        await repo.save(A, _record(other, media=[RecordMedia(7, "photo", "after", 0)]))
```

`backend/apps/visit/tests/app/services/test_sync_pet_weight.py`:

```python
from decimal import Decimal

from visit.app.services.completion_effects import sync_pet_weight
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeVisits, Journal


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    old = visits.seed(status="completed", starts_at=kst(9, 1, 14))
    latest = visits.seed(status="in_progress", starts_at=kst(9, 23, 14))
    visits.seed(status="reserved", starts_at=kst(10, 1, 14))   # 앞으로의 예약은 세지 않는다
    return journal, visits, directory, old, latest


async def test_가장_최근_시작한_방문의_몸무게만_현재_몸무게가_된다():
    journal, visits, directory, old, latest = _setup()
    await sync_pet_weight(ctx(), old, Decimal("3.0"), visits, directory)
    await sync_pet_weight(ctx(), latest, Decimal("3.4"), visits, directory)
    assert journal == [("set_pet_weight", 101, Decimal("3.4"))]


async def test_몸무게가_없거나_보호자만의_방문이면_부르지_않는다():
    journal, visits, directory, _, latest = _setup()
    await sync_pet_weight(ctx(), latest, None, visits, directory)
    alone = visits.seed(pet_id=None, status="in_progress", starts_at=kst(9, 24, 10))
    await sync_pet_weight(ctx(), alone, Decimal("3.4"), visits, directory)
    assert journal == []
```

`backend/apps/visit/tests/app/use_cases/test_put_visit_record_interactor.py`:

```python
from dataclasses import replace
from decimal import Decimal

import pytest

from hub.app.errors import FamilyNotFoundError, MediaClaimAlreadyAttachedError
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.use_cases.put_visit_record_interactor import PutVisitRecordInteractor
from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord
from visit.domain.errors import (
    MenuNotAvailableError,
    RecordMediaLimitError,
    RecordSalesForbiddenError,
    RecordVersionConflictError,
    VisitNoRecordYetError,
    VisitNotFoundError,
)
from visit.domain.value_objects.record_input import MediaPlacement, RecordInput
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits, Journal


class _World:
    def __init__(self, status="in_progress"):
        self.journal = Journal()
        self.visits = FakeVisits(self.journal)
        self.directory = FakeDirectory(self.journal)
        self.directory.family(1, pets=(101,))
        self.records = FakeRecords(self.visits, self.journal)
        self.menus = FakeMenus(self.journal)
        self.library = FakeLibrary(self.journal)
        self.visit = self.visits.seed(status=status, started_at=kst(9, 23, 14) if status != "reserved" else None)
        self.bath = self.menus.seed("목욕", price=30_000)
        self.interactor = PutVisitRecordInteractor(self.visits, self.visits, self.records, self.menus,
                                                   self.directory, self.library)

    async def put(self, record, version=None, context=None):
        return await self.interactor.put_visit_record(
            PutVisitRecordCommand(ctx=context or ctx(), visit_id=self.visit.id, version=version, record=record))

    def existing(self, media=(), version=2, **fields):
        return self.records.seed(VisitRecord(
            visit_id=self.visit.id, weight_kg=None, care_note="옛 메모", internal_note=None, payment_method=None,
            total_amount=None, items=(), media=tuple(media), version=version, created_by_member_id=7,
            updated_by_member_id=7, **fields))


def record(weight=None, items=(), media=(), total=None, payment=None, care="눈물 자국 관리"):
    return RecordInput(weight_kg=weight, care_note=care, internal_note="예민함", payment_method=payment,
                       total_amount=total, items=tuple(items), media=tuple(media))


def at(media_id, phase="after", order=0):
    return MediaPlacement(media_id=media_id, phase=phase, sort_order=order)


async def test_처음_쓰면_버전_1_이고_잠근_뒤_가져가고_저장하고_몸무게를_넘긴다():
    w = _World()
    w.library.add(51)
    w.library.add(52, kind="video")
    view = await w.put(record(Decimal("3.4"), [RecordItem(w.bath.id, 28_000)], [at(51), at(52, "before")],
                              total=28_000, payment="card"))
    assert (view.version, view.total_amount, view.payment_method, view.weight_kg) == (1, 28_000, "card", Decimal("3.4"))
    assert [(i.name, i.amount) for i in view.items] == [("목욕", 28_000)]
    assert [(m.media_id, m.kind, m.phase, m.thumb_url) for m in view.media] == [
        (51, "photo", "after", "t/51"), (52, "video", "before", "t/52")]
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "claim", "release", "save_record",
                                         "set_pet_weight"]
    assert w.records.rows[w.visit.id].created_by_member_id == 11


async def test_다시_쓰면_버전이_오르고_남은_사진은_다시_가져가지_않고_빠진_사진은_놓는다():
    w = _World()
    for i in (51, 52, 53):
        w.library.add(i, attached=i in (51, 52))
    w.existing(media=[RecordMedia(51, "photo", "after", 0), RecordMedia(52, "photo", "after", 1)])
    view = await w.put(record(media=[at(52, order=0), at(53, order=1)]), version=2)
    assert view.version == 3
    assert ("claim", [53]) in w.journal and ("release", [51]) in w.journal
    assert w.records.rows[w.visit.id].created_by_member_id == 7   # 처음 쓴 사람은 그대로


async def test_돈_칸은_sales_write_가_없으면_잠그기_전에_403():
    w = _World()
    no_sales = replace(ctx(role="staff"), permissions=frozenset({"record:write"}))
    for wanted in (record(total=0), record(items=[RecordItem(1, 0)]), record(payment="cash")):
        with pytest.raises(RecordSalesForbiddenError):
            await w.put(wanted, context=no_sales)
    assert w.journal == []
    assert (await w.put(record(Decimal("3.1")), context=no_sales)).version == 1   # 돈 칸이 없으면 된다


@pytest.mark.parametrize("status", ["reserved", "canceled", "no_show"])
async def test_시작하지_않은_방문은_VISIT_NO_RECORD_YET(status):
    w = _World(status="reserved")
    w.visits.rows[w.visit.id] = replace(w.visit, status=status)
    with pytest.raises(VisitNoRecordYetError):
        await w.put(record())
    assert "save_record" not in [e[0] for e in w.journal]


async def test_버전이_어긋나면_아무것도_가져가지_않는다():
    w = _World()
    w.library.add(51)
    w.existing(version=4)
    for version in (None, 3):
        with pytest.raises(RecordVersionConflictError):
            await w.put(record(media=[at(51)]), version=version)
    assert "claim" not in [e[0] for e in w.journal]


async def test_다른_매장의_메뉴는_422_MENU_NOT_FOUND_보관한_메뉴는_된다():
    w = _World()
    theirs = w.menus.seed("남의 메뉴", shop_id=2)
    with pytest.raises(MenuNotAvailableError):
        await w.put(record(items=[RecordItem(theirs.id, 1000)]))
    old = w.menus.seed("옛 메뉴", archived=True)
    assert [i.name for i in (await w.put(record(items=[RecordItem(old.id, 1000)]))).items] == ["옛 메뉴"]


async def test_한도를_넘으면_거절한다():
    w = _World()
    for i in range(1, 32):
        w.library.add(i)
    with pytest.raises(RecordMediaLimitError):
        await w.put(record(media=[at(i, order=i) for i in range(1, 32)]))
    assert "save_record" not in [e[0] for e in w.journal]


async def test_다른_기록에_붙은_미디어는_허브_오류가_그대로_나간다():
    w = _World()
    w.library.add(51, attached=True)
    with pytest.raises(MediaClaimAlreadyAttachedError):
        await w.put(record(media=[at(51)]))


async def test_옛_방문의_기록을_고치면_현재_몸무게는_그대로다():
    w = _World(status="completed")
    w.visits.seed(status="completed", starts_at=kst(9, 30, 14))   # 더 최근에 미용한 방문
    await w.put(record(Decimal("2.9")))
    assert "set_pet_weight" not in [e[0] for e in w.journal]


async def test_익명화한_고객과_다른_매장의_방문은_쓸_수_없다():
    w = _World()
    w.directory.families.clear()
    with pytest.raises(FamilyNotFoundError):
        await w.put(record())
    with pytest.raises(VisitNotFoundError):
        await w.put(record(), context=ctx(shop_id=2))
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:

```diff
@@ -14,6 +14,7 @@ async def test_자기소개는_묶음의_경로와_권한을_적는다():
     record = _Record()
     result = await VisitMyselfInteractor(record).introduce_myself(VisitMyselfQuery(id=5, name="방문 (visit)"))
     assert (result.id, result.name) == (5, "방문 (visit)")
-    for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위"):
+    for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위",
+                  "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT"):
         assert words in result.introduction
     assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/domain/test_visit_record_rules.py`:

```python
from decimal import Decimal

import pytest

from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord
from visit.domain.errors import (
    RecordItemDuplicateError,
    RecordMediaLimitError,
    RecordVersionConflictError,
    RecordWeightWithoutPetError,
    VisitNoRecordYetError,
)
from visit.domain.services.visit_record_rules import (
    check_input,
    check_media_limits,
    check_recordable,
    check_version,
    cover_media_id,
    next_version,
)
from visit.domain.value_objects.record_input import RecordInput
from visit.tests.helpers.builders import visit


def _input(weight=None, items=(), **fields):
    return RecordInput(weight_kg=weight, care_note=None, internal_note=None, payment_method=None,
                       total_amount=None, items=tuple(items), media=(), **fields)


def _record(version=1, media=()):
    return VisitRecord(visit_id=1, weight_kg=None, care_note=None, internal_note=None, payment_method=None,
                       total_amount=None, items=(), media=tuple(media), version=version, created_by_member_id=11,
                       updated_by_member_id=11)


def _m(media_id, kind="photo", phase="after", order=0):
    return RecordMedia(media_id=media_id, kind=kind, phase=phase, sort_order=order)


@pytest.mark.parametrize("status", ["in_progress", "completed"])
def test_미용을_시작한_방문에는_기록을_쓴다(status):
    check_recordable(visit(status=status))


@pytest.mark.parametrize("status", ["reserved", "canceled", "no_show"])
def test_시작하지_않은_방문에는_VISIT_NO_RECORD_YET(status):
    with pytest.raises(VisitNoRecordYetError):
        check_recordable(visit(status=status))


def test_보호자만의_방문에는_몸무게가_없다():
    check_input(visit(pet_id=None), _input())
    with pytest.raises(RecordWeightWithoutPetError):
        check_input(visit(pet_id=None), _input(weight=Decimal("3.2")))


def test_같은_메뉴를_두_번_적으면_RECORD_ITEM_DUPLICATE():
    with pytest.raises(RecordItemDuplicateError):
        check_input(visit(), _input(items=[RecordItem(1, 30000), RecordItem(1, 5000)]))


def test_돈_칸은_총액_항목_결제_수단이다():
    assert not _input().has_money
    assert _input(items=[RecordItem(1, 0)]).has_money
    assert RecordInput(None, None, None, "cash", None, (), ()).has_money
    assert RecordInput(None, None, None, None, 0, (), ()).has_money


def test_사진_30장_영상_3편까지():
    check_media_limits(["photo"] * 30 + ["video"] * 3)
    for kinds in (["photo"] * 31, ["video"] * 4):
        with pytest.raises(RecordMediaLimitError):
            check_media_limits(kinds)


def test_버전은_없을_때_보내지_않고_있을_때_지금_값을_보낸다():
    check_version(None, None)
    check_version(_record(3), 3)
    for current, requested in ((None, 1), (_record(3), None), (_record(3), 2)):
        with pytest.raises(RecordVersionConflictError):
            check_version(current, requested)
    assert (next_version(None), next_version(_record(3))) == (1, 4)


def test_대표_사진은_후_사진_첫_장_그다음_전_사진_그다음_영상이다():
    assert cover_media_id([_m(1, phase="before"), _m(2, order=3), _m(3, order=1), _m(9, "video", order=0)]) == 3
    assert cover_media_id([_m(1, phase="before", order=2), _m(4, phase="before", order=0), _m(9, "video")]) == 4
    assert cover_media_id([_m(8, "video", "before", 0), _m(9, "video", "after", 5)]) == 9
    assert cover_media_id([]) is None
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -9,22 +9,34 @@ from dataclasses import replace
 from decimal import Decimal
 
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
-from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
+from hub.app.dtos.media_urls import MediaUrls
+from hub.app.errors import (
+    FamilyNotFoundError,
+    FamilyPetNotFoundError,
+    FamilyPetPassedAwayError,
+    MediaClaimAlreadyAttachedError,
+    MediaClaimNotFoundError,
+    MediaClaimNotReadyError,
+)
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
+from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.domain.entities.menu import Menu
 from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
+from visit.domain.entities.visit_record import VisitRecord
 from visit.domain.errors import (
     MenuNameTakenError,
     MenuNotFoundError,
     VisitDuplicateError,
     VisitNotFoundError,
 )
+from visit.domain.state.visit_status import STARTED_STATUSES
 from visit.domain.value_objects.closed_date import ClosedDate
 from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
 from visit.tests.helpers.builders import kst
@@ -96,6 +108,9 @@ class FakeMenus(MenuRepository):
         return [m for m in self.rows.values() if m.id in menu_ids and m.shop_id == ctx.shop_id
                 and not m.archived]
 
+    async def list_by_ids(self, ctx, menu_ids):
+        return [m for m in self.rows.values() if m.id in menu_ids and m.shop_id == ctx.shop_id]
+
     async def create(self, ctx, name, default_duration_minutes, price):
         self._check_name(ctx, name)
         menu = self.seed(name=name, minutes=default_duration_minutes, shop_id=ctx.shop_id, price=price)
@@ -158,6 +173,9 @@ class FakeDirectory(CustomerDirectoryPort):
     async def set_last_visit(self, ctx, customer_id, at):
         self.journal.append(("set_last_visit", customer_id, at))
 
+    async def set_pet_weight(self, ctx, pet_id, weight_kg):
+        self.journal.append(("set_pet_weight", pet_id, weight_kg))
+
     async def find_draft_candidates(self, ctx, words):
         """카톡 초안 후보 — 미리 넣어 둔 후보(self.candidates)를 그대로 준다."""
         self.journal.append(("find_draft_candidates", tuple(words)))
@@ -266,6 +284,10 @@ class FakeVisits(VisitWriteRepository, VisitHistoryRepository, VisitLedgerReposi
         done = [v for v in self._mine(ctx) if v.pet_id == pet_id and v.status == "completed"]
         return done[-1] if done else None
 
+    async def latest_started_of_pet(self, ctx, pet_id):
+        started = [v for v in self._mine(ctx) if v.pet_id == pet_id and v.status in STARTED_STATUSES]
+        return max(started, key=lambda v: (v.starts_at, v.id)).id if started else None
+
     async def completed_starts(self, ctx, customer_id, pet_id, limit):
         done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
                 and v.status == "completed"]
@@ -303,3 +325,70 @@ class FakeVisits(VisitWriteRepository, VisitHistoryRepository, VisitLedgerReposi
     async def list_occupied(self, ctx, start, end):
         return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id and v.is_active
                        and v.starts_at < end and v.ends_at > start), key=lambda v: (v.starts_at, v.id))
+
+
+class FakeRecords(VisitRecordRepository):
+    """visit_records 스텁. 방문의 매장은 visits 스텁에서 본다(pg 구현이 visits 와 조인하는 것처럼)."""
+
+    def __init__(self, visits: FakeVisits, journal: Journal | None = None) -> None:
+        self.visits = visits
+        self.journal = journal if journal is not None else Journal()
+        self.rows: dict[int, VisitRecord] = {}
+
+    def seed(self, record: VisitRecord) -> VisitRecord:
+        self.rows[record.visit_id] = record
+        return record
+
+    async def get(self, ctx, visit_id):
+        visit = self.visits.rows.get(visit_id)
+        if visit is None or visit.shop_id != ctx.shop_id:
+            return None
+        return self.rows.get(visit_id)
+
+    async def save(self, ctx, record):
+        self.rows[record.visit_id] = record
+        self.journal.append(("save_record", record.visit_id, record.version))
+        return record
+
+
+class FakeLibrary(MediaLibraryPort):
+    """MediaLibraryPort 스텁 — 실제 구현(media)과 같은 허브 오류를 같은 조건에서 던진다.
+
+    media 는 {media_id: (매장 ID, kind, 준비됨)}. 가져간 것은 attached 에 있다.
+    """
+
+    def __init__(self, journal: Journal | None = None) -> None:
+        self.journal = journal if journal is not None else Journal()
+        self.media: dict[int, tuple[int, str, bool]] = {}
+        self.attached: set[int] = set()
+
+    def add(self, media_id, kind="photo", shop_id=1, ready=True, attached=False) -> int:
+        self.media[media_id] = (shop_id, kind, ready)
+        if attached:
+            self.attached.add(media_id)
+        return media_id
+
+    async def claim(self, ctx, media_ids):
+        self.journal.append(("claim", sorted(media_ids)))
+        for media_id in media_ids:
+            shop, _, _ = self.media.get(media_id, (None, None, None))
+            if shop != ctx.shop_id:
+                raise MediaClaimNotFoundError("사진·영상을 찾을 수 없습니다.")
+        if any(not self.media[i][2] for i in media_ids):
+            raise MediaClaimNotReadyError("아직 올리는 중인 사진·영상입니다.")
+        if any(i in self.attached for i in media_ids):
+            raise MediaClaimAlreadyAttachedError("이미 다른 기록에 붙은 사진·영상입니다.")
+        self.attached |= set(media_ids)
+        return {i: self.media[i][1] for i in media_ids}
+
+    async def release(self, ctx, media_ids):
+        self.journal.append(("release", sorted(media_ids)))
+        self.attached -= set(media_ids)
+
+    async def read_urls(self, ctx, media_ids):
+        return {
+            i: MediaUrls(media_id=i, kind=self.media[i][1], original_url=f"o/{i}",
+                         display_url=f"d/{i}" if self.media[i][1] == "photo" else None, thumb_url=f"t/{i}",
+                         width=3000, height=2000, duration_seconds=None if self.media[i][1] == "photo" else 30)
+            for i in media_ids if i in self.media and self.media[i][0] == ctx.shop_id and self.media[i][2]
+        }
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -1,20 +1,31 @@
 """공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
+from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 from visit.app.ports.output.visit_write_repository import VisitWriteRepository
-from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, FakeVisits
+from visit.tests.helpers.fakes import (
+    FakeDirectory,
+    FakeLibrary,
+    FakeMenus,
+    FakeRecords,
+    FakeSchedule,
+    FakeVisits,
+)
 
 
 def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
     assert isinstance(FakeSchedule(), ScheduleRepository)
     assert isinstance(FakeMenus(), MenuRepository)
     assert isinstance(FakeDirectory(), CustomerDirectoryPort)
+    assert isinstance(FakeLibrary(), MediaLibraryPort)
     visits = FakeVisits()
     for port in (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
                  VisitBoardRepository):
         assert isinstance(visits, port), port.__name__
+    assert isinstance(FakeRecords(visits), VisitRecordRepository)
```

`backend/tests/integration/support.py`:

```diff
@@ -3,6 +3,7 @@ from __future__ import annotations
 
 from dataclasses import dataclass
 
+import httpx
 from httpx import AsyncClient
 from sqlalchemy import text
 from sqlalchemy.ext.asyncio import AsyncEngine
@@ -86,3 +87,33 @@ class FakeKakaoStrategy(SocialProviderPort):
 
     async def revoke(self, identity) -> None:
         self.revoked.append(identity.provider_user_id)
+
+
+PHOTO = {"kind": "photo", "content_type": "image/jpeg", "byte_size": 3000, "width": 3000, "height": 2000}
+
+
+async def issue_media(wired: Wired, shop_id: int, headers: dict, body: dict = PHOTO) -> dict:
+    response = await wired.api.post(f"/v1/shops/{shop_id}/media/uploads", json=body, headers=headers)
+    assert response.status_code == 201, response.text
+    return response.json()
+
+
+async def upload_media(issued: dict, sizes=(3000, 800, 200)) -> None:
+    """렌디션마다 서명 URL 로 서명한 형식 그대로 PUT 한다. 영상이면 표시용이 없다."""
+    puts = issued["puts"]
+    async with httpx.AsyncClient() as http:
+        for name, size in zip(("original", "display", "thumb"), sizes):
+            if puts[name] is None:
+                continue
+            content_type = "video/mp4" if name == "original" and ".mp4" in puts[name] else "image/jpeg"
+            put = await http.put(puts[name], content=b"\x00" * size, headers={"Content-Type": content_type})
+            assert put.status_code == 200, put.text
+
+
+async def ready_photo(wired: Wired, shop_id: int, headers: dict) -> int:
+    """발급 → 올리기 → 확인까지 마친 사진 하나의 ID. `media_storage` 픽스처가 필요하다."""
+    issued = await issue_media(wired, shop_id, headers)
+    await upload_media(issued)
+    confirmed = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=headers)
+    assert confirmed.status_code == 200, confirmed.text
+    return issued["media_id"]
```

`backend/tests/integration/test_media_flow_wiring.py`:

```diff
@@ -1,40 +1,28 @@
 """미디어 발급·확인을 실제 배선(프로바이더·DB 커밋·매장 접근 확인·MinIO)으로 확인한다. 첫 테스트는 테넌트 격리다."""
 import asyncio
 
-import httpx
 import pytest
 
-from tests.integration.support import accept_invite, bearer, error_of, make_operator, shop_with_owner, staff_invite
+from tests.integration.support import (
+    PHOTO,
+    accept_invite,
+    bearer,
+    error_of,
+    issue_media,
+    make_operator,
+    shop_with_owner,
+    staff_invite,
+    upload_media,
+)
 
 pytestmark = pytest.mark.integration
 
-PHOTO = {"kind": "photo", "content_type": "image/jpeg", "byte_size": 3000, "width": 3000, "height": 2000}
-
-
-async def issue(wired, shop_id, headers, body=PHOTO):
-    response = await wired.api.post(f"/v1/shops/{shop_id}/media/uploads", json=body, headers=headers)
-    assert response.status_code == 201, response.text
-    return response.json()
-
-
-async def upload(issued, sizes=(3000, 800, 200)):
-    """렌디션마다 서명 URL 로 서명한 형식 그대로 PUT 한다. 영상이면 표시용이 없다."""
-    puts = issued["puts"]
-    async with httpx.AsyncClient() as http:
-        for name, size in zip(("original", "display", "thumb"), sizes):
-            if puts[name] is None:
-                continue
-            content_type = "video/mp4" if name == "original" and ".mp4" in puts[name] else "image/jpeg"
-            put = await http.put(puts[name], content=b"\x00" * size, headers={"Content-Type": content_type})
-            assert put.status_code == 200, put.text
-
-
 async def test_다른_매장의_미디어에는_손댈_수_없다(wired, media_storage):
     operator = await make_operator(wired)
     a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
     b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
     a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
-    b_media = (await issue(wired, b_shop, b))["media_id"]
+    b_media = (await issue_media(wired, b_shop, b))["media_id"]
 
     their_shop = [
         await wired.api.post(f"/v1/shops/{b_shop}/media/uploads", json=PHOTO, headers=a),
@@ -53,10 +41,10 @@ async def test_직원이_발급받아_올리고_확인하면_ready_다(wired, me
     assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
     s = bearer(staff["access_token"])
 
-    issued = await issue(wired, shop_id, s)
+    issued = await issue_media(wired, shop_id, s)
     early = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=s)
     assert error_of(early) == (409, "MEDIA_NOT_UPLOADED")
-    await upload(issued)
+    await upload_media(issued)
     confirmed = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm",
                                      headers=bearer(owner["access_token"]))   # 발급자가 아니어도 된다
     assert (confirmed.status_code, confirmed.json()["status"], confirmed.json()["size_bytes"]) == (200, "ready", 3000)
@@ -67,8 +55,8 @@ async def test_동시에_두_번_확인해도_결과가_같다(wired, media_stor
     operator = await make_operator(wired)
     shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
     o = bearer(owner["access_token"])
-    issued = await issue(wired, shop_id, o)
-    await upload(issued)
+    issued = await issue_media(wired, shop_id, o)
+    await upload_media(issued)
     first, second = await asyncio.gather(
         wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=o),
         wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=o),
```

`backend/tests/integration/test_visit_record_locking.py`:

```python
"""기록 쓰기의 경합 — 실제 두 세션으로 확인한다(막힌 호출을 create_task 로 들고, 앞선 세션이 커밋한 뒤의 결과를 본다)."""
import asyncio
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.tests.helpers.profiles import customer_profile, pet_profile
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.tests.helpers.fakes import FakeStorage
from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.use_cases.put_visit_record_interactor import PutVisitRecordInteractor
from visit.domain.errors import RecordVersionConflictError
from visit.domain.value_objects.record_input import RecordInput
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
BLOCKED = 0.5


def _put(session):
    visits = VisitPgRepository(session)
    directory = CustomerDirectoryInteractor(CustomerPgRepository(session), PetPgRepository(session),
                                            FamilyBriefPgRepository(session), CustomerSearchPgAdapter(session))
    library = MediaLibraryInteractor(MediaPgRepository(session), FakeStorage(), now=lambda: kst(9, 23, 15))
    return PutVisitRecordInteractor(visits, visits, VisitRecordPgRepository(session), MenuPgRepository(session),
                                    directory, library)


def _record(note):
    return RecordInput(weight_kg=Decimal("3.4"), care_note=note, internal_note=None, payment_method=None,
                       total_amount=None, items=(), media=())


async def test_같은_버전으로_동시에_두_번_쓰면_늦은_쪽은_RECORD_VERSION_CONFLICT(db_engine, db_session):
    """고객 행 → 방문 행 잠금을 빼면 늦은 쪽도 '기록 없음'을 읽고 덮어써 앞선 쪽의 기록이 사라진다."""
    customer = await CustomerPgRepository(db_session).create(SHOP, customer_profile())
    pet = await PetPgRepository(db_session).add(SHOP, customer.id, pet_profile())
    visit_id = await insert_visit(db_session, kst(9, 23, 14), "in_progress", customer_id=customer.id, pet_id=pet.id)
    await db_session.commit()

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        saved = await _put(first).put_visit_record(
            PutVisitRecordCommand(ctx=SHOP, visit_id=visit_id, version=None, record=_record("앞선 기기")))
        late = asyncio.create_task(_put(second).put_visit_record(
            PutVisitRecordCommand(ctx=SHOP, visit_id=visit_id, version=None, record=_record("늦은 기기"))))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await first.commit()
        with pytest.raises(RecordVersionConflictError):
            await late
    assert (saved.version, saved.care_note) == (1, "앞선 기기")
```

`backend/tests/integration/test_visit_record_wiring.py`:

```python
"""미용 기록을 실제 배선(프로바이더·허브 포트 조립·DB 커밋·MinIO)으로 확인한다. 첫 테스트는 테넌트 격리다."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.integration.support import bearer, error_of, make_operator, ready_photo, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _at(days: int, hour: int) -> str:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


async def _family(wired, shop_id, headers):
    response = await wired.api.post(f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET},
                                    headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["customer"]["customer_id"], response.json()["pets"][0]["pet_id"]


async def _visit(wired, shop_id, headers, customer_id, pet_id, days=-1, start=True):
    """days 날 뒤 11시 예약. start 면 미용을 시작한다(어제 방문이라 자정을 넘기지 않는다 — 시각과 상관없이 돈다)."""
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
                                  json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(days, 11)})
    assert booked.status_code == 201, booked.text
    visit_id = booked.json()["visits"][0]["visit_id"]
    if start:
        started = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                       json={"visit_ids": [visit_id], "action": "start"})
        assert started.status_code == 200, started.text
    return visit_id


async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
    operator = operator or await make_operator(wired)
    shop_id, login = await shop_with_owner(wired, operator, name, owner)
    return shop_id, bearer(login["access_token"]), operator


async def test_다른_매장의_방문과_미디어로는_기록을_쓸_수_없다(wired, media_storage):
    a_shop, a, operator = await _shop(wired, "A 매장", "A사장")
    b_shop, b, _ = await _shop(wired, "B 매장", "B사장", operator)
    a_visit = await _visit(wired, a_shop, a, *await _family(wired, a_shop, a))
    b_visit = await _visit(wired, b_shop, b, *await _family(wired, b_shop, b))
    b_photo = await ready_photo(wired, b_shop, b)

    assert error_of(await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_visit}/record", json={}, headers=a)) == (
        403, "NOT_A_MEMBER")
    assert error_of(await wired.api.put(f"/v1/shops/{a_shop}/visits/{b_visit}/record", json={}, headers=a)) == (
        404, "VISIT_NOT_FOUND")
    theirs = await wired.api.put(f"/v1/shops/{a_shop}/visits/{a_visit}/record", headers=a,
                                 json={"media": [{"media_id": b_photo, "phase": "after", "sort_order": 0}]})
    assert error_of(theirs) == (404, "MEDIA_NOT_FOUND")


async def test_기록을_쓰고_고치면_버전이_오르고_빠진_사진은_놓이고_몸무게가_현재_몸무게가_된다(wired, media_storage):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)
    visit_id = await _visit(wired, shop_id, o, customer_id, pet_id)
    bath = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=o)).json()["items"][0]["menu_id"]
    before, after = await ready_photo(wired, shop_id, o), await ready_photo(wired, shop_id, o)
    body = {"weight_kg": 3.4, "care_note": "눈물 자국 관리", "internal_note": "발 만지면 예민", "payment_method": "card",
            "total_amount": 25000, "items": [{"menu_id": bath, "amount": 28000}],
            "media": [{"media_id": before, "phase": "before", "sort_order": 0},
                      {"media_id": after, "phase": "after", "sort_order": 0}]}
    path = f"/v1/shops/{shop_id}/visits/{visit_id}/record"

    first = await wired.api.put(path, json=body, headers=o)
    assert first.status_code == 200, first.text
    saved = first.json()
    assert (saved["version"], saved["total_amount"], [i["amount"] for i in saved["items"]]) == (1, 25000, [28000])
    assert [(m["media_id"], m["phase"]) for m in saved["media"]] == [(before, "before"), (after, "after")]
    assert all(m["thumb_url"].startswith("http") for m in saved["media"])
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=o)).json()["pet"]
    assert pet["weight_kg"] == 3.4

    assert error_of(await wired.api.put(path, json=body, headers=o)) == (409, "RECORD_VERSION_CONFLICT")
    second = await wired.api.put(path, headers=o, json={**body, "version": 1, "media": body["media"][1:]})
    assert (second.status_code, second.json()["version"]) == (200, 2)
    async with wired.engine.connect() as conn:
        attached = dict((await conn.execute(text("SELECT id, attached_at IS NOT NULL FROM media_objects"))).all())
    assert attached == {before: False, after: True}

    other_visit = await _visit(wired, shop_id, o, customer_id, pet_id, days=-2)
    taken = await wired.api.put(f"/v1/shops/{shop_id}/visits/{other_visit}/record", headers=o,
                                json={"media": [{"media_id": after, "phase": "after", "sort_order": 0}]})
    assert error_of(taken) == (409, "MEDIA_ALREADY_ATTACHED")


async def test_예약만_된_방문에는_기록을_쓸_수_없다(wired, media_storage):
    shop_id, o, _ = await _shop(wired)
    visit_id = await _visit(wired, shop_id, o, *await _family(wired, shop_id, o), days=1, start=False)
    response = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", json={}, headers=o)
    assert error_of(response) == (409, "VISIT_NO_RECORD_YET")
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit apps/customer tests/integration/test_visit_record_wiring.py tests/integration/test_visit_record_locking.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 7개 — `ModuleNotFoundError: No module named 'visit.domain.entities.visit_record'`(`visit_record_repository`·`visit_record_pg_repository`·`put_visit_record_dto`·라우터), `ImportError: cannot import name 'sync_pet_weight'`.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/ports/customer_directory_port.py`:

```diff
@@ -2,6 +2,7 @@ from __future__ import annotations
 
 from abc import ABC, abstractmethod
 from datetime import datetime
+from decimal import Decimal
 
 from hub.app.dtos.draft_candidate import DraftCandidate
 from hub.app.dtos.family_brief import FamilyBriefs
@@ -9,7 +10,8 @@ from hub.app.dtos.shop_context import ShopContext
 
 
 class CustomerDirectoryPort(ABC):
-    """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순, 카톡 초안 후보)."""
+    """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순, 카톡 초안 후보,
+    미용 기록의 몸무게)."""
 
     @abstractmethod
     async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
@@ -31,6 +33,14 @@ class CustomerDirectoryPort(ABC):
     async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
         """고객 목록 '최근 방문순'의 키를 바꾼다. 원본(visits)에서 다시 계산한 값을 같은 트랜잭션에서 넘긴다."""
 
+    @abstractmethod
+    async def set_pet_weight(self, ctx: ShopContext, pet_id: int, weight_kg: Decimal) -> None:
+        """반려동물의 현재 몸무게를 바꾼다 — 그 아이의 가장 최근 미용 기록에 적은 몸무게다(설계 8절).
+
+        visit 이 lock_family 로 고객 행을 잠근 **뒤에** 같은 트랜잭션에서 부른다. 살아 있는 이 매장의 아이가
+        아니면 아무것도 바꾸지 않는다(잠근 가족이라 일어나지 않는다).
+        """
+
     @abstractmethod
     async def find_draft_candidates(self, ctx: ShopContext, words: tuple[str, ...]) -> list[DraftCandidate]:
         """카톡 예약 초안의 "누구" 후보. 낱말 하나라도 걸리는 이 매장의 가족을 최대 5 가족 돌려준다.
```

`backend/apps/visit/domain/entities/visit_record.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

BEFORE = "before"
AFTER = "after"
PHASES = (BEFORE, AFTER)
PAYMENT_METHODS = ("card", "cash", "transfer")


@dataclass(frozen=True)
class RecordItem:
    """실제로 한 메뉴 하나와 그 금액(원). 예약 메뉴(visit_menus)는 계획이고 이것은 실적이다."""

    menu_id: int
    amount: int


@dataclass(frozen=True)
class RecordMedia:
    """기록에 붙은 사진·영상 하나. kind 는 media 가 가져가기(claim) 때 알려 준 값이다 — 바뀌지 않는 사실이라
    옮겨 적어 두고 대표 사진·한도를 이 표만으로 계산한다."""

    media_id: int
    kind: str       # photo · video
    phase: str      # before · after
    sort_order: int


@dataclass(frozen=True)
class VisitRecord:
    """방문 하나의 미용 기록(설계 6.1). 총액은 항목 합에서 나오지 않는 별개 사실(받은 돈)이다.

    version 은 기록을 바꿀 때마다 1씩 오른다 — 전체 교체(PUT)가 모르는 사이 붙은 사진을 지우지 않게 한다.
    """

    visit_id: int
    weight_kg: Decimal | None
    care_note: str | None       # 공개 — ⑤ 알림장에 실린다
    internal_note: str | None   # 매장 안에서만
    payment_method: str | None
    total_amount: int | None
    items: tuple[RecordItem, ...]
    media: tuple[RecordMedia, ...]
    version: int
    created_by_member_id: int
    updated_by_member_id: int
```

`backend/apps/visit/domain/value_objects/record_input.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from visit.domain.entities.visit_record import RecordItem


@dataclass(frozen=True)
class MediaPlacement:
    """요청이 정한 미디어의 자리. 종류는 아직 모른다 — 가져가기(claim) 뒤에 안다."""

    media_id: int
    phase: str
    sort_order: int


@dataclass(frozen=True)
class RecordInput:
    """기록 전체 교체(PUT)의 내용. 비운 칸은 지운다."""

    weight_kg: Decimal | None
    care_note: str | None
    internal_note: str | None
    payment_method: str | None
    total_amount: int | None
    items: tuple[RecordItem, ...]
    media: tuple[MediaPlacement, ...]

    @property
    def has_money(self) -> bool:
        """돈 칸 — 총액·항목·결제 수단. 하나라도 있으면 sales:write 가 필요하다(설계 8절)."""
        return self.total_amount is not None or bool(self.items) or self.payment_method is not None
```

`backend/apps/visit/domain/errors.py`:

```diff
@@ -56,3 +56,45 @@ class MenuNotAvailableError(VisitError):
 
 class MenuNameTakenError(VisitError):
     code = "MENU_NAME_TAKEN"
+
+
+class VisitNoRecordYetError(VisitError):
+    """예약됨·취소·노쇼 방문에는 기록을 쓸 수 없다 — 미용을 시작해야 한다. 409."""
+
+    code = "VISIT_NO_RECORD_YET"
+
+
+class RecordNotFoundError(VisitError):
+    """그 방문에 기록이 없다. 404."""
+
+    code = "RECORD_NOT_FOUND"
+
+
+class RecordVersionConflictError(VisitError):
+    """보낸 버전이 지금 기록의 버전과 다르다 — 그 사이 다른 기기나 업로드 대기열이 기록을 바꿨다. 409."""
+
+    code = "RECORD_VERSION_CONFLICT"
+
+
+class RecordWeightWithoutPetError(VisitError):
+    """보호자만의 방문에 몸무게를 적었다. 422."""
+
+    code = "RECORD_WEIGHT_WITHOUT_PET"
+
+
+class RecordItemDuplicateError(VisitError):
+    """같은 메뉴를 두 번 적었다. 422."""
+
+    code = "RECORD_ITEM_DUPLICATE"
+
+
+class RecordMediaLimitError(VisitError):
+    """방문 하나의 사진 30장·영상 3편을 넘는다. 422."""
+
+    code = "MEDIA_LIMIT_EXCEEDED"
+
+
+class RecordSalesForbiddenError(VisitError):
+    """돈 칸(총액·항목·결제 수단)을 적는데 sales:write 가 없다. 403."""
+
+    code = "PERMISSION_DENIED"
```

`backend/apps/visit/domain/services/visit_record_rules.py`:

```python
"""미용 기록의 규칙 — 누가 언제 쓰는가, 입력의 모양, 한도, 버전, 대표 사진(설계 6.2·8절).

기록은 미용 중·완료 방문에만 쓴다. 판단은 잠근 뒤 다시 읽은 방문으로 한다. 상태 클래스에 행동을 더하지 않는다.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_record import AFTER, BEFORE, RecordMedia, VisitRecord
from visit.domain.errors import (
    RecordItemDuplicateError,
    RecordMediaLimitError,
    RecordVersionConflictError,
    RecordWeightWithoutPetError,
    VisitNoRecordYetError,
)
from visit.domain.state.visit_status import STARTED_STATUSES
from visit.domain.value_objects.record_input import RecordInput

MEDIA_LIMITS = {"photo": 30, "video": 3}   # 방문 하나에
MAX_SORT_ORDER = 99


def check_recordable(visit: Visit) -> None:
    if visit.status not in STARTED_STATUSES:
        raise VisitNoRecordYetError("미용을 시작한 방문에만 기록을 쓸 수 있습니다.")


def check_input(visit: Visit, record: RecordInput) -> None:
    if record.weight_kg is not None and visit.pet_id is None:
        raise RecordWeightWithoutPetError("보호자만의 방문에는 몸무게를 적을 수 없습니다.")
    menu_ids = [item.menu_id for item in record.items]
    if len(menu_ids) != len(set(menu_ids)):
        raise RecordItemDuplicateError("같은 메뉴를 두 번 적을 수 없습니다.")


def check_media_limits(kinds: Iterable[str]) -> None:
    counts = Counter(kinds)
    if any(counts[kind] > limit for kind, limit in MEDIA_LIMITS.items()):
        raise RecordMediaLimitError("방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있습니다.")


def check_version(current: VisitRecord | None, requested: int | None) -> None:
    """기록이 없으면 버전을 보내지 않고, 있으면 지금 버전을 보내야 한다. 다르면 그 사이 누가 바꾼 것이다."""
    expected = current.version if current is not None else None
    if requested != expected:
        raise RecordVersionConflictError("다른 기기가 먼저 기록을 바꿨습니다. 다시 불러와 주세요.")


def next_version(current: VisitRecord | None) -> int:
    return current.version + 1 if current is not None else 1


def cover_media_id(media: Iterable[RecordMedia]) -> int | None:
    """대표 사진 — 후 사진 첫 장 → 전 사진 첫 장 → 영상 포스터(후 먼저) → 없음(설계 6.2)."""
    ranked = sorted(
        media,
        key=lambda m: (m.kind != "photo", {AFTER: 0, BEFORE: 1}[m.phase], m.sort_order),
    )
    return ranked[0].media_id if ranked else None
```

`backend/apps/visit/adapter/outbound/orm/visit_orm.py`:

```diff
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 from datetime import date, datetime, time
+from decimal import Decimal
 
 from sqlalchemy import (
     BigInteger,
@@ -10,6 +11,7 @@ from sqlalchemy import (
     ForeignKey,
     Index,
     Integer,
+    Numeric,
     SmallInteger,
     String,
     Time,
@@ -175,3 +177,71 @@ class VisitMenuOrm(Base):
         ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True
     )
     menu_id: Mapped[int] = mapped_column(ForeignKey("service_menus.id"), primary_key=True)
+
+
+class VisitRecordOrm(Base):
+    """방문 하나의 미용 기록(설계 6.1). 행이 있다는 것이 곧 '기록이 있다'이다."""
+
+    __tablename__ = "visit_records"
+    __table_args__ = (
+        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_visit_records_weight"),
+        CheckConstraint(
+            "payment_method IS NULL OR payment_method IN ('card', 'cash', 'transfer')",
+            name="ck_visit_records_payment_method",
+        ),
+        CheckConstraint(
+            "total_amount IS NULL OR total_amount BETWEEN 0 AND 100000000", name="ck_visit_records_total_amount"
+        ),
+        CheckConstraint("version >= 1", name="ck_visit_records_version"),
+    )
+
+    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True)
+    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
+    care_note: Mapped[str | None] = mapped_column(String(1000))       # 공개 — ⑤ 알림장
+    internal_note: Mapped[str | None] = mapped_column(String(1000))   # 매장 안에서만
+    payment_method: Mapped[str | None] = mapped_column(String(10))
+    total_amount: Mapped[int | None] = mapped_column(Integer)         # 받은 돈. 항목 합과 다를 수 있다(할인)
+    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
+    # tenancy 의 멤버 ID.
+    created_by_member_id: Mapped[int] = mapped_column(BigInteger)
+    updated_by_member_id: Mapped[int] = mapped_column(BigInteger)
+    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
+    updated_at: Mapped[datetime] = mapped_column(
+        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
+    )
+
+
+class VisitRecordItemOrm(Base):
+    """실제로 한 메뉴와 금액. 예약 메뉴(visit_menus)와 다른 사실이다."""
+
+    __tablename__ = "visit_record_items"
+    __table_args__ = (
+        CheckConstraint("amount BETWEEN 0 AND 100000000", name="ck_visit_record_items_amount"),
+    )
+
+    visit_id: Mapped[int] = mapped_column(
+        ForeignKey("visit_records.visit_id", ondelete="CASCADE"), primary_key=True
+    )
+    menu_id: Mapped[int] = mapped_column(ForeignKey("service_menus.id"), primary_key=True)
+    amount: Mapped[int] = mapped_column(Integer)
+
+
+class VisitRecordMediaOrm(Base):
+    """기록에 붙은 사진·영상. media_id 는 media 스포크의 ID 라 외래 키가 없다 — 정합성은 가져가기(claim)가 지킨다."""
+
+    __tablename__ = "visit_record_media"
+    __table_args__ = (
+        CheckConstraint("kind IN ('photo', 'video')", name="ck_visit_record_media_kind"),
+        CheckConstraint("phase IN ('before', 'after')", name="ck_visit_record_media_phase"),
+        CheckConstraint("sort_order BETWEEN 0 AND 99", name="ck_visit_record_media_sort_order"),
+        Index("uq_visit_record_media_order", "visit_id", "phase", "sort_order", unique=True),
+    )
+
+    visit_id: Mapped[int] = mapped_column(
+        ForeignKey("visit_records.visit_id", ondelete="CASCADE"), primary_key=True
+    )
+    # 한 객체는 한 기록에만 붙는다.
+    media_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True, autoincrement=False)
+    kind: Mapped[str] = mapped_column(String(10))
+    phase: Mapped[str] = mapped_column(String(10))
+    sort_order: Mapped[int] = mapped_column(SmallInteger)
```

`backend/alembic/versions/0009_visit_records.py`:

```python
"""미용 기록 — 기록·실제 메뉴와 금액·붙은 사진영상

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _now(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "visit_records",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("weight_kg", sa.Numeric(4, 1)),
        sa.Column("care_note", sa.String(1000)),
        sa.Column("internal_note", sa.String(1000)),
        sa.Column("payment_method", sa.String(10)),
        sa.Column("total_amount", sa.Integer),
        sa.Column("version", sa.Integer, server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("updated_by_member_id", sa.BigInteger, nullable=False),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_visit_records_weight"),
        sa.CheckConstraint(
            "payment_method IS NULL OR payment_method IN ('card', 'cash', 'transfer')",
            name="ck_visit_records_payment_method",
        ),
        sa.CheckConstraint(
            "total_amount IS NULL OR total_amount BETWEEN 0 AND 100000000", name="ck_visit_records_total_amount"
        ),
        sa.CheckConstraint("version >= 1", name="ck_visit_records_version"),
    )
    op.create_table(
        "visit_record_items",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visit_records.visit_id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("menu_id", sa.BigInteger, sa.ForeignKey("service_menus.id"), primary_key=True),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.CheckConstraint("amount BETWEEN 0 AND 100000000", name="ck_visit_record_items_amount"),
    )
    op.create_table(
        "visit_record_media",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visit_records.visit_id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("media_id", sa.BigInteger, primary_key=True, autoincrement=False),   # media 의 ID — 외래 키 없음
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("phase", sa.String(10), nullable=False),
        sa.Column("sort_order", sa.SmallInteger, nullable=False),
        sa.CheckConstraint("kind IN ('photo', 'video')", name="ck_visit_record_media_kind"),
        sa.CheckConstraint("phase IN ('before', 'after')", name="ck_visit_record_media_phase"),
        sa.CheckConstraint("sort_order BETWEEN 0 AND 99", name="ck_visit_record_media_sort_order"),
        sa.UniqueConstraint("media_id", name="visit_record_media_media_id_key"),
    )
    op.create_index(
        "uq_visit_record_media_order", "visit_record_media", ["visit_id", "phase", "sort_order"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_visit_record_media_order", table_name="visit_record_media")
    op.drop_table("visit_record_media")
    op.drop_table("visit_record_items")
    op.drop_table("visit_records")
```

`backend/apps/visit/app/ports/output/visit_record_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit_record import VisitRecord


class VisitRecordRepository(ABC):
    """미용 기록(visit_records 와 항목·미디어 두 하위 표). 읽기는 방문의 매장(ShopContext)으로 거른다.

    쓰기는 방문 행을 잠근 **뒤에만** 부른다 — 방문이 이 매장의 것임은 잠금(`lock_visits`)이 이미 확인했다.
    """

    @abstractmethod
    async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
        """없거나 다른 매장의 방문이면 None."""

    @abstractmethod
    async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
        """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다."""
```

`backend/apps/customer/adapter/outbound/pg/pet_pg_repository.py`:

```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from decimal import Decimal
+
 from sqlalchemy import delete, func, insert, select, update
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -118,6 +120,13 @@ class PetPgRepository(PetRepository):
         )
         return await self.get(ctx, pet_id)
 
+    async def set_weight(self, ctx: ShopContext, pet_id: int, weight_kg: Decimal) -> None:
+        await self._session.execute(
+            update(PetOrm)
+            .where(PetOrm.id == pet_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
+            .values(weight_kg=weight_kg, updated_at=func.now())
+        )
+
     async def count_for_customer(self, ctx: ShopContext, customer_id: int) -> int:
         return (
             await self._session.execute(
```

`backend/apps/customer/app/ports/output/pet_repository.py`:

```diff
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 from abc import ABC, abstractmethod
+from decimal import Decimal
 
 from customer.domain.entities.pet import Pet
 from customer.domain.value_objects.pet_profile import PetProfile
@@ -32,6 +33,10 @@ class PetRepository(ABC):
     @abstractmethod
     async def set_passed_away(self, ctx: ShopContext, pet_id: int, passed_away: bool) -> Pet: ...
 
+    @abstractmethod
+    async def set_weight(self, ctx: ShopContext, pet_id: int, weight_kg: Decimal) -> None:
+        """현재 몸무게만 바꾼다(미용 기록이 알려 준 값). 소속이 아니면 아무것도 바꾸지 않는다."""
+
     @abstractmethod
     async def count_for_customer(self, ctx: ShopContext, customer_id: int) -> int: ...
```

`backend/apps/customer/app/use_cases/customer_directory_interactor.py`:

```diff
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 from datetime import datetime
+from decimal import Decimal
 
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
@@ -58,6 +59,9 @@ class CustomerDirectoryInteractor(CustomerDirectoryPort):
     async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
         await self._search.set_last_visit(ctx, customer_id, at)
 
+    async def set_pet_weight(self, ctx: ShopContext, pet_id: int, weight_kg: Decimal) -> None:
+        await self._pets.set_weight(ctx, pet_id, weight_kg)
+
     async def find_draft_candidates(self, ctx: ShopContext, words: tuple[str, ...]) -> list[DraftCandidate]:
         if not words:
             return []
```

`backend/apps/visit/adapter/inbound/api/error_map.py`:

```diff
@@ -3,10 +3,17 @@ from visit.domain.errors import (
     MenuNameTakenError,
     MenuNotAvailableError,
     MenuNotFoundError,
+    RecordItemDuplicateError,
+    RecordMediaLimitError,
+    RecordNotFoundError,
+    RecordSalesForbiddenError,
+    RecordVersionConflictError,
+    RecordWeightWithoutPetError,
     VisitCrossesMidnightError,
     VisitDuplicateError,
     VisitGroupMismatchError,
     VisitInputError,
+    VisitNoRecordYetError,
     VisitNotFoundError,
     VisitNotYetError,
     VisitStateConflictError,
@@ -23,4 +30,11 @@ VISIT_ERROR_STATUS: dict[type[Exception], int] = {
     VisitCrossesMidnightError: 422,
     VisitGroupMismatchError: 422,
     MenuNotAvailableError: 422,
+    RecordNotFoundError: 404,
+    RecordSalesForbiddenError: 403,
+    VisitNoRecordYetError: 409,
+    RecordVersionConflictError: 409,
+    RecordWeightWithoutPetError: 422,
+    RecordItemDuplicateError: 422,
+    RecordMediaLimitError: 422,
 }
```

`backend/apps/visit/adapter/inbound/api/schemas/put_visit_record_schema.py`:

```python
from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StrictInt, StringConstraints, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId
from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
from visit.domain.entities.visit_record import RecordItem
from visit.domain.value_objects.record_input import MediaPlacement, RecordInput

Amount = Annotated[StrictInt, Field(ge=0, le=100_000_000)]
Note = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=1000),
    AfterValidator(lambda v: reject_control_chars(v, allow_newline=True)),
] | None


class RecordItemInput(BaseModel):
    menu_id: EntityId
    amount: Amount


class MediaPlacementInput(BaseModel):
    media_id: EntityId
    phase: Literal["before", "after"]
    sort_order: Annotated[StrictInt, Field(ge=0, le=99)]


class PutVisitRecordRequestSchema(BaseModel):
    """기록 전체 교체. 비운 칸은 지운다. version 은 기록이 없으면 보내지 않고, 있으면 읽은 버전을 보낸다.

    같은 메뉴를 두 번 적으면 422 RECORD_ITEM_DUPLICATE(도메인), 같은 미디어·같은 자리를 두 번 보내면 422 VALIDATION_ERROR.
    """

    version: Annotated[StrictInt, Field(ge=1, le=2_147_483_647)] | None = None
    weight_kg: Annotated[Decimal, Field(ge=Decimal("0.1"), le=Decimal("999.9"), max_digits=4, decimal_places=1)] | None = None
    care_note: Note = None
    internal_note: Note = None
    payment_method: Literal["card", "cash", "transfer"] | None = None
    total_amount: Amount | None = None
    items: Annotated[list[RecordItemInput], Field(max_length=30)] = []
    media: Annotated[list[MediaPlacementInput], Field(max_length=33)] = []

    @field_validator("media")
    @classmethod
    def _media_unique(cls, media: list[MediaPlacementInput]) -> list[MediaPlacementInput]:
        if len({m.media_id for m in media}) != len(media):
            raise ValueError("같은 사진·영상을 두 번 보낼 수 없습니다.")
        if len({(m.phase, m.sort_order) for m in media}) != len(media):
            raise ValueError("같은 자리(전/후·순서)에 둘을 둘 수 없습니다.")
        return media

    def to_input(self) -> RecordInput:
        return RecordInput(
            weight_kg=self.weight_kg, care_note=self.care_note, internal_note=self.internal_note,
            payment_method=self.payment_method, total_amount=self.total_amount,
            items=tuple(RecordItem(menu_id=i.menu_id, amount=i.amount) for i in self.items),
            media=tuple(MediaPlacement(media_id=m.media_id, phase=m.phase, sort_order=m.sort_order)
                        for m in self.media),
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/record_view_schema.py`:

```python
"""기록 응답 모양 — 기록 쓰기·덧붙이기·방문 상세가 함께 쓴다(app 의 record_view_dto 와 짝)."""
from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.record_view_dto import RecordView


class RecordItemSchema(BaseModel):
    menu_id: int
    name: str
    amount: int


class RecordMediaSchema(BaseModel):
    media_id: int
    kind: str                 # photo · video
    phase: str                # before · after
    sort_order: int
    original_url: str
    display_url: str | None   # 영상이면 None
    thumb_url: str            # 영상이면 포스터
    width: int
    height: int
    duration_seconds: int | None


class RecordSchema(BaseModel):
    visit_id: int
    weight_kg: float | None   # JSON 숫자로 내보낸다(customer 와 같은 관례)
    care_note: str | None
    internal_note: str | None
    payment_method: str | None
    total_amount: int | None
    items: list[RecordItemSchema]
    media: list[RecordMediaSchema]
    version: int              # 다음 PUT 에 그대로 보낸다

    @classmethod
    def of(cls, view: RecordView) -> RecordSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/v1/put_visit_record_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.put_visit_record_schema import PutVisitRecordRequestSchema
from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.ports.input.put_visit_record_use_case import PutVisitRecordUseCase
from visit.dependencies.put_visit_record_provider import get_put_visit_record_use_case

put_visit_record_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@put_visit_record_router.put("/{shop_id}/visits/{visit_id}/record", response_model=RecordSchema)
async def put_visit_record(
    visit_id: VisitId,
    body: PutVisitRecordRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: PutVisitRecordUseCase = Depends(get_put_visit_record_use_case),
) -> RecordSchema:
    view = await use_case.put_visit_record(
        PutVisitRecordCommand(ctx=ctx, visit_id=visit_id, version=body.version, record=body.to_input())
    )
    return RecordSchema.of(view)
```

`backend/apps/visit/adapter/outbound/mappers/visit_record_mapper.py`:

```python
from __future__ import annotations

from visit.adapter.outbound.orm.visit_orm import VisitRecordItemOrm, VisitRecordMediaOrm, VisitRecordOrm
from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord


def to_record(
    row: VisitRecordOrm, items: list[VisitRecordItemOrm], media: list[VisitRecordMediaOrm]
) -> VisitRecord:
    return VisitRecord(
        visit_id=row.visit_id, weight_kg=row.weight_kg, care_note=row.care_note, internal_note=row.internal_note,
        payment_method=row.payment_method, total_amount=row.total_amount,
        items=tuple(RecordItem(menu_id=i.menu_id, amount=i.amount) for i in items),
        media=tuple(RecordMedia(media_id=m.media_id, kind=m.kind, phase=m.phase, sort_order=m.sort_order)
                    for m in media),
        version=row.version, created_by_member_id=row.created_by_member_id,
        updated_by_member_id=row.updated_by_member_id,
    )
```

`backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py`:

```diff
@@ -43,6 +43,14 @@ class MenuPgRepository(MenuRepository):
         ).scalars()
         return [to_menu(row) for row in rows]
 
+    async def list_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
+        rows = (
+            await self._session.execute(
+                select(ServiceMenuOrm).where(ServiceMenuOrm.id.in_(menu_ids), ServiceMenuOrm.shop_id == ctx.shop_id)
+            )
+        ).scalars()
+        return [to_menu(row) for row in rows]
+
     async def create(
         self, ctx: ShopContext, name: str, default_duration_minutes: int | None, price: int | None
     ) -> Menu:
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`:

```diff
@@ -18,6 +18,7 @@ from visit.domain.entities.visit import ACTIVE_STATUSES, COMPLETED, NO_SHOW, RES
 from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
 from visit.domain.services.visit_schedule import MAX_DURATION
 from visit.domain.state.visit_state import StatusChange
+from visit.domain.state.visit_status import STARTED_STATUSES
 from visit.domain.value_objects.new_visit import NewVisit
 
 _DUPLICATE = {"uq_visits_pet_start_active", "uq_visits_customer_start_active"}
@@ -159,6 +160,17 @@ class VisitPgRepository(VisitWriteRepository, VisitHistoryRepository, VisitLedge
         )
         return found[0] if found else None
 
+    async def latest_started_of_pet(self, ctx: ShopContext, pet_id: int) -> int | None:
+        return (
+            await self._session.execute(
+                select(VisitOrm.id)
+                .where(VisitOrm.shop_id == ctx.shop_id, VisitOrm.pet_id == pet_id,
+                       VisitOrm.status.in_(STARTED_STATUSES))
+                .order_by(VisitOrm.starts_at.desc(), VisitOrm.id.desc())
+                .limit(1)
+            )
+        ).scalar_one_or_none()
+
     async def completed_starts(
         self, ctx: ShopContext, customer_id: int, pet_id: int | None, limit: int
     ) -> list[datetime]:
```

`backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`:

```python
from __future__ import annotations

from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_record_mapper import to_record
from visit.adapter.outbound.orm.visit_orm import VisitOrm, VisitRecordItemOrm, VisitRecordMediaOrm, VisitRecordOrm
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.domain.entities.visit_record import VisitRecord


class VisitRecordPgRepository(VisitRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
        row = (
            await self._session.execute(
                select(VisitRecordOrm)
                .join(VisitOrm, VisitOrm.id == VisitRecordOrm.visit_id)
                .where(VisitRecordOrm.visit_id == visit_id, VisitOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return await self._assemble(row) if row is not None else None

    async def _assemble(self, row: VisitRecordOrm) -> VisitRecord:
        visit_id = row.visit_id
        items = (
            await self._session.execute(
                select(VisitRecordItemOrm).where(VisitRecordItemOrm.visit_id == visit_id)
                .order_by(VisitRecordItemOrm.menu_id).execution_options(populate_existing=True)
            )
        ).scalars().all()
        media = (
            await self._session.execute(
                select(VisitRecordMediaOrm).where(VisitRecordMediaOrm.visit_id == visit_id)
                .order_by(VisitRecordMediaOrm.phase.desc(), VisitRecordMediaOrm.sort_order)   # before → after
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        return to_record(row, list(items), list(media))

    async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
        fields = dict(
            weight_kg=record.weight_kg, care_note=record.care_note, internal_note=record.internal_note,
            payment_method=record.payment_method, total_amount=record.total_amount, version=record.version,
            updated_by_member_id=record.updated_by_member_id,
        )
        await self._session.execute(
            pg_insert(VisitRecordOrm)
            .values(visit_id=record.visit_id, created_by_member_id=record.created_by_member_id, **fields)
            .on_conflict_do_update(index_elements=[VisitRecordOrm.visit_id], set_={**fields, "updated_at": func.now()})
        )
        await self._session.execute(delete(VisitRecordItemOrm).where(VisitRecordItemOrm.visit_id == record.visit_id))
        await self._session.execute(delete(VisitRecordMediaOrm).where(VisitRecordMediaOrm.visit_id == record.visit_id))
        if record.items:
            await self._session.execute(
                insert(VisitRecordItemOrm),
                [dict(visit_id=record.visit_id, menu_id=i.menu_id, amount=i.amount) for i in record.items],
            )
        if record.media:
            await self._session.execute(
                insert(VisitRecordMediaOrm),
                [dict(visit_id=record.visit_id, media_id=m.media_id, kind=m.kind, phase=m.phase,
                      sort_order=m.sort_order) for m in record.media],
            )
        row = (
            await self._session.execute(
                select(VisitRecordOrm).where(VisitRecordOrm.visit_id == record.visit_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return await self._assemble(row)
```

`backend/apps/visit/app/dtos/put_visit_record_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.record_input import RecordInput


@dataclass(frozen=True)
class PutVisitRecordCommand:
    """기록 전체 교체. version 은 기록이 없으면 None, 있으면 읽었을 때의 버전이다."""

    ctx: ShopContext
    visit_id: int
    version: int | None
    record: RecordInput
```

`backend/apps/visit/app/dtos/record_view_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RecordItemView:
    menu_id: int
    name: str
    amount: int


@dataclass(frozen=True)
class RecordMediaView:
    """붙은 사진·영상 하나와 그 읽기 URL. 영상은 display_url 이 없고 thumb_url 이 포스터다."""

    media_id: int
    kind: str
    phase: str
    sort_order: int
    original_url: str
    display_url: str | None
    thumb_url: str
    width: int
    height: int
    duration_seconds: int | None


@dataclass(frozen=True)
class RecordView:
    """방문 상세의 '오늘의 케어'와 기록 화면이 쓰는 기록 전체. version 은 다음 PUT 에 그대로 돌려보낸다."""

    visit_id: int
    weight_kg: Decimal | None
    care_note: str | None
    internal_note: str | None
    payment_method: str | None
    total_amount: int | None
    items: list[RecordItemView]
    media: list[RecordMediaView]   # 전 → 후, 각각 순서대로
    version: int
```

`backend/apps/visit/app/ports/input/put_visit_record_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.dtos.record_view_dto import RecordView


class PutVisitRecordUseCase(ABC):
    @abstractmethod
    async def put_visit_record(self, command: PutVisitRecordCommand) -> RecordView: ...
```

`backend/apps/visit/app/ports/output/menu_repository.py`:

```diff
@@ -17,6 +17,10 @@ class MenuRepository(ABC):
     async def list_active_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
         """요청 본문이 고른 메뉴 가운데 이 매장의 보관하지 않은 것만."""
 
+    @abstractmethod
+    async def list_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
+        """이 매장의 메뉴만, 보관한 것도 — 지난 기록이 보관한 메뉴를 가리키고 있을 수 있다."""
+
     @abstractmethod
     async def create(
         self, ctx: ShopContext, name: str, default_duration_minutes: int | None, price: int | None
```

`backend/apps/visit/app/ports/output/visit_history_repository.py`:

```diff
@@ -31,6 +31,11 @@ class VisitHistoryRepository(ABC):
     async def last_completed_of_pet(self, ctx: ShopContext, pet_id: int) -> Visit | None:
         """그 아이의 마지막 완료 방문('지난번처럼'의 원본)."""
 
+    @abstractmethod
+    async def latest_started_of_pet(self, ctx: ShopContext, pet_id: int) -> int | None:
+        """그 아이의 가장 최근 방문 가운데 미용을 시작한 것(미용 중·완료)의 ID — 시작 시각, 같으면 ID 가 큰 쪽.
+        기록의 몸무게를 현재 몸무게로 넘길지 정한다(설계 8절)."""
+
     @abstractmethod
     async def completed_starts(
         self, ctx: ShopContext, customer_id: int, pet_id: int | None, limit: int
```

`backend/apps/visit/app/services/completion_effects.py`:

```diff
@@ -1,11 +1,13 @@
-"""완료가 생기거나 풀린 뒤의 후속 처리 — 같은 트랜잭션 안에서, 방문 행을 잠근 채로.
+"""방문의 사실이 바뀐 뒤 customer 에 알리는 후속 처리 — 같은 트랜잭션 안에서, 방문 행을 잠근 채로.
 
-지금은 하나다: 그 보호자의 마지막 완료 방문 시작 시각을 customer 에 넘긴다(고객 목록 '최근 방문순').
-④ 기록 슬라이스는 몸무게 동기화를 여기에 더한다 — 전이·기록 두 유스케이스가 같은 함수를 부르므로 후속 처리가
-한 곳에 남는다(단일 책임: 전이 인터랙터는 잠금·전이·후속 호출만 한다).
+둘이다. ① 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각(고객 목록 '최근 방문순'). 전이가 부른다.
+② 기록에 몸무게를 적으면, 그 방문이 그 아이의 가장 최근 시작한 방문일 때 현재 몸무게. 기록 쓰기가 부른다.
+유스케이스는 잠금·쓰기·후속 호출만 하고, 무엇을 언제 알릴지는 여기 한 곳에 둔다.
 """
 from __future__ import annotations
 
+from decimal import Decimal
+
 from hub.app.dtos.shop_context import ShopContext
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
@@ -28,3 +30,15 @@ async def apply_completion_effects(
     customer_id = after[0].customer_id
     latest = await history.latest_completed_start(ctx, customer_id)
     await directory.set_last_visit(ctx, customer_id, latest)
+
+
+async def sync_pet_weight(
+    ctx: ShopContext, visit: Visit, weight_kg: Decimal | None,
+    history: VisitHistoryRepository, directory: CustomerDirectoryPort,
+) -> None:
+    """기록의 몸무게를 현재 몸무게로 넘긴다 — 그 아이의 가장 최근 시작한 방문의 기록일 때만.
+    옛 기록을 고쳐도 현재 값은 바뀌지 않는다(설계 8절). 고객 행은 부르는 쪽이 이미 잠갔다."""
+    if weight_kg is None or visit.pet_id is None:
+        return
+    if await history.latest_started_of_pet(ctx, visit.pet_id) == visit.id:
+        await directory.set_pet_weight(ctx, visit.pet_id, weight_kg)
```

`backend/apps/visit/app/services/record_reader.py`:

```python
"""기록을 보여 줄 모양으로 조립한다 — 메뉴 이름은 메뉴표(보관한 것도)에서, 사진 URL 은 허브 포트로.

기록 쓰기·덧붙이기가 쓰기를 마친 뒤, 방문 상세가 읽을 때 같은 모양으로 돌려준다.
"""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.record_view_dto import RecordItemView, RecordMediaView, RecordView
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.visit_record import VisitRecord


async def describe_record(
    ctx: ShopContext, record: VisitRecord, menus: MenuRepository, library: MediaLibraryPort
) -> RecordView:
    names = {m.id: m.name for m in await menus.list_by_ids(ctx, [i.menu_id for i in record.items])} \
        if record.items else {}
    urls = await library.read_urls(ctx, [m.media_id for m in record.media])
    return RecordView(
        visit_id=record.visit_id, weight_kg=record.weight_kg, care_note=record.care_note,
        internal_note=record.internal_note, payment_method=record.payment_method,
        total_amount=record.total_amount,
        items=[RecordItemView(menu_id=i.menu_id, name=names[i.menu_id], amount=i.amount) for i in record.items],
        media=[
            RecordMediaView(
                media_id=m.media_id, kind=m.kind, phase=m.phase, sort_order=m.sort_order,
                original_url=urls[m.media_id].original_url, display_url=urls[m.media_id].display_url,
                thumb_url=urls[m.media_id].thumb_url, width=urls[m.media_id].width,
                height=urls[m.media_id].height, duration_seconds=urls[m.media_id].duration_seconds,
            )
            for m in record.media if m.media_id in urls
        ],
        version=record.version,
    )
```

`backend/apps/visit/app/use_cases/put_visit_record_interactor.py`:

```python
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.dtos.record_view_dto import RecordView
from visit.app.ports.input.put_visit_record_use_case import PutVisitRecordUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.completion_effects import sync_pet_weight
from visit.app.services.record_reader import describe_record
from visit.app.services.visit_locking import lock_visits
from visit.domain.entities.visit_record import RecordMedia, VisitRecord
from visit.domain.errors import MenuNotAvailableError, RecordSalesForbiddenError
from visit.domain.services.visit_record_rules import (
    check_input,
    check_media_limits,
    check_recordable,
    check_version,
    next_version,
)


class PutVisitRecordInteractor(PutVisitRecordUseCase):
    """기록 전체 교체(설계 8절). 고객 행 → 방문 행을 잠그고, 다시 읽은 방문·기록으로 판정한 뒤 쓴다.

    새로 든 미디어는 가져가고(claim), 빠진 미디어는 놓는다(release) — 놓인 미디어는 정리 스크립트가 지운다.
    둘 다 조건부 UPDATE 라 잠금 안에서 불러도 된다. 하나라도 안 되면 요청 전체가 되돌려진다.
    """

    def __init__(
        self, visits: VisitLookupRepository, history: VisitHistoryRepository, records: VisitRecordRepository,
        menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort,
    ) -> None:
        self._visits = visits
        self._history = history
        self._records = records
        self._menus = menus
        self._directory = directory
        self._library = library

    async def put_visit_record(self, command: PutVisitRecordCommand) -> RecordView:
        ctx, wanted = command.ctx, command.record
        if wanted.has_money and "sales:write" not in ctx.permissions:
            raise RecordSalesForbiddenError("금액을 적을 권한이 없습니다.")
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        check_recordable(visit)
        check_input(visit, wanted)
        current = await self._records.get(ctx, visit.id)
        check_version(current, command.version)
        menu_ids = [item.menu_id for item in wanted.items]
        if menu_ids and len(await self._menus.list_by_ids(ctx, menu_ids)) != len(menu_ids):
            raise MenuNotAvailableError("메뉴를 찾을 수 없습니다.")

        had = {m.media_id: m.kind for m in current.media} if current else {}
        wanted_ids = [p.media_id for p in wanted.media]
        kinds = had | await self._library.claim(ctx, [i for i in wanted_ids if i not in had])
        check_media_limits(kinds[i] for i in wanted_ids)
        await self._library.release(ctx, [i for i in had if i not in wanted_ids])

        saved = await self._records.save(ctx, VisitRecord(
            visit_id=visit.id, weight_kg=wanted.weight_kg, care_note=wanted.care_note,
            internal_note=wanted.internal_note, payment_method=wanted.payment_method,
            total_amount=wanted.total_amount, items=wanted.items,
            media=tuple(RecordMedia(media_id=p.media_id, kind=kinds[p.media_id], phase=p.phase,
                                    sort_order=p.sort_order) for p in wanted.media),
            version=next_version(current),
            created_by_member_id=current.created_by_member_id if current else ctx.member_id,
            updated_by_member_id=ctx.member_id,
        ))
        await sync_pet_weight(ctx, visit, saved.weight_kg, self._history, self._directory)
        return await describe_record(ctx, saved, self._menus, self._library)
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -29,6 +29,10 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "전부 안 됨), GET /visits/{visit_id}/next-draft 는 다음 예약 초안입니다(취소·노쇼한 방문은 409). "
                 "POST /visit-drafts 는 카톡 글을 규칙으로 읽어 날짜·시각·보호자 후보·메뉴를 짐작한 초안입니다"
                 "(저장하지 않고, 글을 남기지 않습니다). "
+                "PUT /visits/{visit_id}/record 는 미용 기록의 전체 교체입니다(미용 중·완료 방문만, record:write). "
+                "몸무게·케어 메모(공개)·내부 메모·결제 수단·총액(받은 돈)·실제 메뉴와 금액·사진영상(media 에서 확인한 "
+                "것, 전/후와 순서)을 담고, 돈 칸은 sales:write 가 필요합니다. 기록이 있으면 읽은 version 을 보내야 하고 "
+                "다르면 409 RECORD_VERSION_CONFLICT 입니다. 몸무게는 그 아이의 가장 최근 방문이면 현재 몸무게가 됩니다. "
                 "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                 "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}(이름·기본 소요·순서·정가 price, "
                 "원 단위, 비우면 가격 미정), "
```

`backend/apps/visit/dependencies/hub_ports.py`:

```diff
@@ -5,7 +5,12 @@
 from __future__ import annotations
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.media_library_port import MediaLibraryPort
 
 
 def get_customer_directory() -> CustomerDirectoryPort:
     raise RuntimeError("CustomerDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
+
+
+def get_media_library() -> MediaLibraryPort:
+    raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/visit/dependencies/put_visit_record_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.put_visit_record_use_case import PutVisitRecordUseCase
from visit.app.use_cases.put_visit_record_interactor import PutVisitRecordInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository


def get_put_visit_record_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> PutVisitRecordUseCase:
    visits = build_visit_repository(db)
    return PutVisitRecordInteractor(
        visits=visits, history=visits, records=build_record_repository(db), menus=build_menu_repository(db),
        directory=directory, library=library,
    )
```

`backend/apps/visit/dependencies/visit_wiring.py`:

```diff
@@ -5,9 +5,11 @@ from sqlalchemy.ext.asyncio import AsyncSession
 
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
+from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
+from visit.app.ports.output.visit_record_repository import VisitRecordRepository
 
 
 def build_schedule_repository(db: AsyncSession) -> ScheduleRepository:
@@ -21,3 +23,7 @@ def build_menu_repository(db: AsyncSession) -> MenuRepository:
 def build_visit_repository(db: AsyncSession) -> VisitPgRepository:
     """visits 표의 리포지토리 하나. 다섯 포트를 다 구현하므로 프로바이더가 같은 인스턴스를 포트 인자마다 넘긴다."""
     return VisitPgRepository(db)
+
+
+def build_record_repository(db: AsyncSession) -> VisitRecordRepository:
+    return VisitRecordPgRepository(db)
```

`backend/main.py`:

```diff
@@ -44,6 +44,7 @@ from media.adapter.inbound.api.error_map import MEDIA_ERROR_STATUS
 from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_router
 from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
 from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
+from media.dependencies.media_library_provider import get_media_library_use_case
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
 from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
@@ -76,6 +77,7 @@ from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_
 from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
 from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
 from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
+from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
 from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
 from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
 from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
@@ -83,7 +85,7 @@ from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_media_library
 from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
 
 
@@ -151,6 +153,7 @@ app.include_router(parse_visit_draft_router)
 app.include_router(get_visit_router)
 app.include_router(update_visit_router)
 app.include_router(get_next_visit_draft_router)
+app.include_router(put_visit_record_router)
 # media
 app.include_router(media_myself_router)
 app.include_router(issue_upload_router)
@@ -172,6 +175,7 @@ app.dependency_overrides[get_membership_directory] = get_list_memberships_use_ca
 app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case
 app.dependency_overrides[get_customer_directory] = get_customer_directory_use_case
 app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
+app.dependency_overrides[get_media_library] = get_media_library_use_case
 
 
 @app.get("/health")
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit apps/customer tests/integration/test_visit_record_wiring.py tests/integration/test_visit_record_locking.py tests/integration/test_media_flow_wiring.py tests/test_hub_port_binding.py tests/test_schema_drift.py -q -p no:cacheprovider` → 전부 통과

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 855 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 286 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `PutVisitRecordInteractor`의 `[visit] = await lock_visits(…)`를 `visit = await self._visits.get(ctx, command.visit_id)`로 → `test_같은_버전으로_동시에_두_번_쓰면…` 실패(늦은 쪽도 '기록 없음'을 읽고 덮어쓴다).
- 돈 칸 검사 `if wanted.has_money and "sales:write" not in ctx.permissions:`를 `if False:`로 → `test_돈_칸은_sales_write_가_없으면_잠그기_전에_403` 실패.
- `await self._library.release(…)` 줄을 뺀다 → `test_다시_쓰면_버전이_오르고…` 등 2개 실패.
- `sync_pet_weight`의 `if await history.latest_started_of_pet(…) == visit.id:`를 `if True:`로 → `test_가장_최근_시작한_방문의_몸무게만…`·`test_옛_방문의_기록을_고치면…` 실패.
- `cover_media_id` 정렬 키에서 `m.kind != "photo"`를 뺀다 → `test_대표_사진은_후_사진_첫_장_그다음_전_사진_그다음_영상이다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 미용 기록 쓰기 — PUT /visits/{id}/record(전체 교체·버전), visit_records·항목·미디어(0009), 미디어 가져가기·놓기, 최근 방문이면 현재 몸무게(set_pet_weight)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 사진 하나 덧붙이기와 기록 삭제 — `POST /visits/{id}/record/media`(맨 뒤·빈 기록 생성·같은 미디어 멱등·버전 올림), `DELETE /visits/{id}/record`(record:delete)

**Files:**
- Modify: `backend/apps/visit/domain/services/visit_record_rules.py`
- Modify: `backend/apps/visit/app/ports/output/visit_record_repository.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/append_record_media_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/append_record_media_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/delete_visit_record_router.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`
- Create: `backend/apps/visit/app/dtos/append_record_media_dto.py`
- Create: `backend/apps/visit/app/dtos/delete_visit_record_dto.py`
- Create: `backend/apps/visit/app/ports/input/append_record_media_use_case.py`
- Create: `backend/apps/visit/app/ports/input/delete_visit_record_use_case.py`
- Create: `backend/apps/visit/app/use_cases/append_record_media_interactor.py`
- Create: `backend/apps/visit/app/use_cases/delete_visit_record_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/dependencies/append_record_media_provider.py`
- Create: `backend/apps/visit/dependencies/delete_visit_record_provider.py`
- Create: `backend/apps/visit/tests/adapter/test_append_record_media_router.py`
- Create: `backend/apps/visit/tests/adapter/test_delete_visit_record_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_append_record_media_interactor.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_delete_visit_record_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Modify: `backend/apps/visit/tests/domain/test_visit_record_rules.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/integration/test_visit_record_wiring.py`

**Interfaces:**
- Consumes: 작업 6 의 `VisitRecord`·`RecordMedia`·`visit_record_rules`·`VisitRecordRepository`·`describe_record`·`RecordSchema`·`FakeRecords`·`FakeLibrary`·`get_media_library` 자리, `lock_visits`.
- Produces: `visit_record_rules.append_media(media, media_id, kind, phase) -> tuple[RecordMedia, ...]`; `VisitRecordRepository.delete(ctx, visit_id)`; `AppendRecordMediaInteractor(visits, records, menus, directory, library)`·`AppendRecordMediaCommand(ctx, visit_id, media_id, phase)`; `DeleteVisitRecordInteractor(visits, records, directory, library)`·`DeleteVisitRecordCommand(ctx, visit_id)`; 새 경로 `POST /v1/shops/{shop_id}/visits/{visit_id}/record/media`(record:write, 응답 `RecordSchema`), `DELETE /v1/shops/{shop_id}/visits/{visit_id}/record`(record:delete, 204).

앱의 업로드 대기열(설계 10.2)과 방문 상세의 [사진 추가]가 쓰는 덧붙이기, 그리고 기록 삭제다(설계 8절). 덧붙이기는 버전을 받지 않고 올리며, 기록이 없으면 빈 기록을 만든다. 같은 미디어가 이미 이 기록에 있으면 아무것도 바꾸지 않는다 — 대기열이 응답을 못 받고 다시 보내도 안전하다(M18). 그 칸은 순서를 지킨 채 0부터 다시 매기고 맨 뒤에 붙인다 — 빼고 붙이기를 거듭해도 순서 상한(99)에 닿지 않는다. 삭제는 붙은 미디어를 놓고 행을 지운다(항목·연결은 CASCADE). 방문은 남는다. **설계와 다른 점**(결정 기록 007): 삭제 권한은 `record:delete`(사장) — 권한 시드(0002)가 '기록 삭제'를 그렇게 뒀다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_append_record_media_router.py`:

```python
from visit.adapter.inbound.api.v1.append_record_media_router import append_record_media_router
from visit.app.dtos.record_view_dto import RecordView
from visit.dependencies.append_record_media_provider import get_append_record_media_use_case
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of

VIEW = RecordView(visit_id=4, weight_kg=None, care_note=None, internal_note=None, payment_method=None,
                  total_amount=None, items=[], media=[], version=1)


async def test_직원은_사진을_덧붙인다():
    stub = Recorder(VIEW)
    async with client(build_app(append_record_media_router, get_append_record_media_use_case, stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/visits/4/record/media", json={"media_id": 51, "phase": "before"})
    assert (response.status_code, response.json()["version"]) == (200, 1)
    assert (stub.calls[0].visit_id, stub.calls[0].media_id, stub.calls[0].phase) == (4, 51, "before")


async def test_권한이_없거나_몸통이_틀리면_거절한다():
    async with client(build_app(append_record_media_router, get_append_record_media_use_case, Recorder(VIEW),
                                READ_ONLY)) as c:
        assert error_of(await c.post("/v1/shops/3/visits/4/record/media", json={"media_id": 51, "phase": "after"})) == (
            403, "PERMISSION_DENIED")
    async with client(build_app(append_record_media_router, get_append_record_media_use_case, Recorder(VIEW))) as c:
        for body in ({"media_id": 51}, {"media_id": 0, "phase": "after"}, {"media_id": 51, "phase": "during"}):
            assert error_of(await c.post("/v1/shops/3/visits/4/record/media", json=body)) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_delete_visit_record_router.py`:

```python
from visit.adapter.inbound.api.v1.delete_visit_record_router import delete_visit_record_router
from visit.dependencies.delete_visit_record_provider import get_delete_visit_record_use_case
from visit.domain.errors import RecordNotFoundError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


async def test_사장은_기록을_지운다_204():
    stub = Recorder(None)
    async with client(build_app(delete_visit_record_router, get_delete_visit_record_use_case, stub)) as c:
        response = await c.delete("/v1/shops/3/visits/4/record")
    assert (response.status_code, stub.calls[0].visit_id) == (204, 4)


async def test_직원은_기록을_지우지_못한다():
    """기록 삭제는 record:delete(사장만) — 시드의 권한 표를 따른다."""
    async with client(build_app(delete_visit_record_router, get_delete_visit_record_use_case, Recorder(None),
                                STAFF)) as c:
        assert error_of(await c.delete("/v1/shops/3/visits/4/record")) == (403, "PERMISSION_DENIED")


async def test_기록이_없으면_404():
    stub = Recorder(error=RecordNotFoundError("없음"))
    async with client(build_app(delete_visit_record_router, get_delete_visit_record_use_case, stub)) as c:
        assert error_of(await c.delete("/v1/shops/3/visits/4/record")) == (404, "RECORD_NOT_FOUND")
```

`backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`:

```diff
@@ -53,3 +53,11 @@ async def test_한_미디어는_한_기록에만_붙는다(db_session):
     await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))
     with pytest.raises(IntegrityError):
         await repo.save(A, _record(other, media=[RecordMedia(7, "photo", "after", 0)]))
+
+
+async def test_지우면_항목과_미디어_연결도_함께_지워진다(db_session):
+    repo, visit_id, bath, _ = await _setup(db_session)
+    await repo.save(A, _record(visit_id, items=[RecordItem(bath, 1)], media=[RecordMedia(7, "photo", "after", 0)]))
+    await repo.delete(A, visit_id)
+    assert await repo.get(A, visit_id) is None
+    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))   # 연결이 남았으면 유일 위반
```

`backend/apps/visit/tests/app/use_cases/test_append_record_media_interactor.py`:

```python
from dataclasses import replace
from decimal import Decimal

import pytest

from hub.app.errors import MediaClaimNotReadyError
from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.use_cases.append_record_media_interactor import AppendRecordMediaInteractor
from visit.domain.entities.visit_record import RecordMedia, VisitRecord
from visit.domain.errors import RecordMediaLimitError, VisitNoRecordYetError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits, Journal


class _World:
    def __init__(self, status="in_progress"):
        self.journal = Journal()
        self.visits = FakeVisits(self.journal)
        self.directory = FakeDirectory(self.journal)
        self.directory.family(1, pets=(101,))
        self.records = FakeRecords(self.visits, self.journal)
        self.library = FakeLibrary(self.journal)
        self.visit = self.visits.seed(status=status, started_at=kst(9, 23, 14))
        self.interactor = AppendRecordMediaInteractor(self.visits, self.records, FakeMenus(), self.directory,
                                                      self.library)

    async def append(self, media_id, phase="before"):
        return await self.interactor.append_record_media(
            AppendRecordMediaCommand(ctx=ctx(member_id=12), visit_id=self.visit.id, media_id=media_id, phase=phase))

    def existing(self, media, version=3):
        return self.records.seed(VisitRecord(
            visit_id=self.visit.id, weight_kg=Decimal("3.4"), care_note="케어", internal_note=None,
            payment_method="cash", total_amount=30_000, items=(), media=tuple(media), version=version,
            created_by_member_id=7, updated_by_member_id=7))


async def test_기록이_없으면_빈_기록을_버전_1_로_만들며_붙인다():
    w = _World()
    w.library.add(51)
    view = await w.append(51)
    assert (view.version, [(m.media_id, m.phase, m.sort_order) for m in view.media]) == (1, [(51, "before", 0)])
    assert (view.total_amount, w.records.rows[w.visit.id].created_by_member_id) == (None, 12)
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "claim", "save_record"]


async def test_있는_기록은_다른_칸을_그대로_두고_버전을_올린다():
    w = _World()
    w.library.add(51, attached=True)
    w.library.add(52, kind="video")
    w.existing([RecordMedia(51, "photo", "after", 0)])
    view = await w.append(52, "after")
    assert view.version == 4
    assert [(m.media_id, m.sort_order) for m in view.media] == [(51, 0), (52, 1)]
    kept = w.records.rows[w.visit.id]
    assert (kept.total_amount, kept.weight_kg, kept.created_by_member_id) == (30_000, Decimal("3.4"), 7)


async def test_이미_붙은_미디어면_아무것도_바꾸지_않는다():
    w = _World()
    w.library.add(51, attached=True)
    w.existing([RecordMedia(51, "photo", "before", 0)])
    view = await w.append(51)
    assert view.version == 3
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits"]


async def test_시작하지_않은_방문이나_준비_전_미디어는_거절한다():
    w = _World()
    w.visits.rows[w.visit.id] = replace(w.visit, status="reserved")
    with pytest.raises(VisitNoRecordYetError):
        await w.append(51)
    w = _World()
    w.library.add(51, ready=False)
    with pytest.raises(MediaClaimNotReadyError):
        await w.append(51)


async def test_영상은_세_편까지다():
    w = _World()
    for i in (61, 62, 63, 64):
        w.library.add(i, kind="video", attached=i != 64)
    w.existing([RecordMedia(i, "video", "after", i - 61) for i in (61, 62, 63)])
    with pytest.raises(RecordMediaLimitError):
        await w.append(64)
```

`backend/apps/visit/tests/app/use_cases/test_delete_visit_record_interactor.py`:

```python
import pytest

from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
from visit.domain.entities.visit_record import RecordMedia, VisitRecord
from visit.domain.errors import RecordNotFoundError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeRecords, FakeVisits, Journal


def _world(status="completed"):
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101,))
    records, library = FakeRecords(visits, journal), FakeLibrary(journal)
    visit = visits.seed(status=status, started_at=kst(9, 23, 14), completed_at=kst(9, 23, 16))
    return journal, visit, records, DeleteVisitRecordInteractor(visits, records, directory, library)


async def test_잠근_뒤_미디어를_놓고_기록을_지운다():
    journal, visit, records, interactor = _world()
    records.seed(VisitRecord(visit_id=visit.id, weight_kg=None, care_note=None, internal_note=None,
                             payment_method=None, total_amount=None, items=(),
                             media=(RecordMedia(51, "photo", "after", 0), RecordMedia(52, "video", "before", 0)),
                             version=2, created_by_member_id=11, updated_by_member_id=11))
    await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
    assert visit.id not in records.rows
    assert journal == [("lock_family", 1, ()), ("lock_visits", [visit.id]), ("release", [51, 52]),
                       ("delete_record", visit.id)]


async def test_기록이_없으면_RECORD_NOT_FOUND():
    journal, visit, _, interactor = _world()
    with pytest.raises(RecordNotFoundError):
        await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:

```diff
@@ -15,6 +15,7 @@ async def test_자기소개는_묶음의_경로와_권한을_적는다():
     result = await VisitMyselfInteractor(record).introduce_myself(VisitMyselfQuery(id=5, name="방문 (visit)"))
     assert (result.id, result.name) == (5, "방문 (visit)")
     for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위",
-                  "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT"):
+                  "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT",
+                  "POST /visits/{visit_id}/record/media", "record:delete"):
         assert words in result.introduction
     assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/domain/test_visit_record_rules.py`:

```diff
@@ -11,6 +11,7 @@ from visit.domain.errors import (
     VisitNoRecordYetError,
 )
 from visit.domain.services.visit_record_rules import (
+    append_media,
     check_input,
     check_media_limits,
     check_recordable,
@@ -87,3 +88,11 @@ def test_대표_사진은_후_사진_첫_장_그다음_전_사진_그다음_영
     assert cover_media_id([_m(1, phase="before", order=2), _m(4, phase="before", order=0), _m(9, "video")]) == 4
     assert cover_media_id([_m(8, "video", "before", 0), _m(9, "video", "after", 5)]) == 9
     assert cover_media_id([]) is None
+
+
+def test_덧붙이면_그_칸의_맨_뒤이고_그_칸은_순서를_지킨_채_0부터_다시_매긴다():
+    media = [_m(1, phase="before", order=3), _m(2, phase="before", order=90), _m(3, phase="after", order=5)]
+    assert append_media(media, 9, "video", "before") == (
+        _m(3, phase="after", order=5), _m(1, phase="before", order=0), _m(2, phase="before", order=1),
+        _m(9, "video", "before", 2))
+    assert append_media([], 9, "photo", "after") == (_m(9, order=0),)
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -350,6 +350,10 @@ class FakeRecords(VisitRecordRepository):
         self.journal.append(("save_record", record.visit_id, record.version))
         return record
 
+    async def delete(self, ctx, visit_id):
+        self.rows.pop(visit_id, None)
+        self.journal.append(("delete_record", visit_id))
+
 
 class FakeLibrary(MediaLibraryPort):
     """MediaLibraryPort 스텁 — 실제 구현(media)과 같은 허브 오류를 같은 조건에서 던진다.
```

`backend/tests/integration/test_visit_record_wiring.py`:

```diff
@@ -5,7 +5,14 @@ from zoneinfo import ZoneInfo
 import pytest
 from sqlalchemy import text
 
-from tests.integration.support import bearer, error_of, make_operator, ready_photo, shop_with_owner
+from tests.integration.support import (
+    accept_invite,
+    bearer,
+    error_of,
+    make_operator,
+    ready_photo,
+    shop_with_owner,
+)
 
 pytestmark = pytest.mark.integration
 
@@ -46,6 +53,13 @@ async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
     return shop_id, bearer(login["access_token"]), operator
 
 
+async def _staff(wired, shop_id, owner_headers):
+    staff = await wired.login("직원")
+    code = (await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=owner_headers)).json()["code"]
+    assert (await accept_invite(wired, staff, code)).status_code == 200
+    return bearer(staff["access_token"])
+
+
 async def test_다른_매장의_방문과_미디어로는_기록을_쓸_수_없다(wired, media_storage):
     a_shop, a, operator = await _shop(wired, "A 매장", "A사장")
     b_shop, b, _ = await _shop(wired, "B 매장", "B사장", operator)
@@ -101,3 +115,28 @@ async def test_예약만_된_방문에는_기록을_쓸_수_없다(wired, media_
     visit_id = await _visit(wired, shop_id, o, *await _family(wired, shop_id, o), days=1, start=False)
     response = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", json={}, headers=o)
     assert error_of(response) == (409, "VISIT_NO_RECORD_YET")
+
+
+async def test_덧붙이기는_기록을_만들고_다시_보내도_한_번이며_기록은_사장만_지운다(wired, media_storage):
+    shop_id, o, _ = await _shop(wired)
+    s = await _staff(wired, shop_id, o)
+    customer_id, pet_id = await _family(wired, shop_id, o)
+    visit_id = await _visit(wired, shop_id, o, customer_id, pet_id)
+    first, second = await ready_photo(wired, shop_id, s), await ready_photo(wired, shop_id, s)
+    path = f"/v1/shops/{shop_id}/visits/{visit_id}/record"
+
+    appended = await wired.api.post(f"{path}/media", json={"media_id": first, "phase": "before"}, headers=s)
+    again = await wired.api.post(f"{path}/media", json={"media_id": first, "phase": "before"}, headers=s)
+    assert [(r.status_code, r.json()["version"], len(r.json()["media"])) for r in (appended, again)] == [(200, 1, 1)] * 2
+    # 폼이 읽은 버전으로 저장하는 사이 대기열이 한 장을 더 붙이면, 폼의 저장은 409 가 된다.
+    await wired.api.post(f"{path}/media", json={"media_id": second, "phase": "after"}, headers=s)
+    stale = await wired.api.put(path, headers=s, json={"version": 1, "weight_kg": 3.1,
+                                                         "media": [{"media_id": first, "phase": "before", "sort_order": 0}]})
+    assert error_of(stale) == (409, "RECORD_VERSION_CONFLICT")
+
+    assert error_of(await wired.api.delete(path, headers=s)) == (403, "PERMISSION_DENIED")
+    assert (await wired.api.delete(path, headers=o)).status_code == 204
+    assert error_of(await wired.api.delete(path, headers=o)) == (404, "RECORD_NOT_FOUND")
+    async with wired.engine.connect() as conn:
+        attached = (await conn.execute(text("SELECT count(*) FROM media_objects WHERE attached_at IS NOT NULL"))).scalar()
+    assert attached == 0
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit tests/integration/test_visit_record_wiring.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 5개 — `ImportError: cannot import name 'append_media' from 'visit.domain.services.visit_record_rules'`, `ModuleNotFoundError: No module named 'visit.app.dtos.append_record_media_dto'`(`delete_visit_record_dto`·라우터 둘).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/services/visit_record_rules.py`:

```diff
@@ -53,6 +53,16 @@ def next_version(current: VisitRecord | None) -> int:
     return current.version + 1 if current is not None else 1
 
 
+def append_media(media: Iterable[RecordMedia], media_id: int, kind: str, phase: str) -> tuple[RecordMedia, ...]:
+    """그 칸(전/후)의 맨 뒤에 붙인다. 그 칸은 순서를 지킨 채 0부터 다시 매긴다 — 빼고 붙이기를 거듭해도
+    순서 값이 상한(99)에 닿지 않는다."""
+    media = list(media)
+    same = sorted((m for m in media if m.phase == phase), key=lambda m: m.sort_order)
+    renumbered = [RecordMedia(m.media_id, m.kind, m.phase, order) for order, m in enumerate(same)]
+    others = [m for m in media if m.phase != phase]
+    return tuple(others + renumbered + [RecordMedia(media_id, kind, phase, len(same))])
+
+
 def cover_media_id(media: Iterable[RecordMedia]) -> int | None:
     """대표 사진 — 후 사진 첫 장 → 전 사진 첫 장 → 영상 포스터(후 먼저) → 없음(설계 6.2)."""
     ranked = sorted(
```

`backend/apps/visit/app/ports/output/visit_record_repository.py`:

```diff
@@ -19,3 +19,7 @@ class VisitRecordRepository(ABC):
     @abstractmethod
     async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
         """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다."""
+
+    @abstractmethod
+    async def delete(self, ctx: ShopContext, visit_id: int) -> None:
+        """기록 행을 지운다. 항목·미디어 연결은 외래 키의 ON DELETE CASCADE 로 함께 지워진다."""
```

`backend/apps/visit/adapter/inbound/api/schemas/append_record_media_schema.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId


class AppendRecordMediaRequestSchema(BaseModel):
    media_id: EntityId
    phase: Literal["before", "after"]
```

`backend/apps/visit/adapter/inbound/api/v1/append_record_media_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.append_record_media_schema import AppendRecordMediaRequestSchema
from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.ports.input.append_record_media_use_case import AppendRecordMediaUseCase
from visit.dependencies.append_record_media_provider import get_append_record_media_use_case

append_record_media_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@append_record_media_router.post("/{shop_id}/visits/{visit_id}/record/media", response_model=RecordSchema)
async def append_record_media(
    visit_id: VisitId,
    body: AppendRecordMediaRequestSchema,
    ctx: ShopContext = Depends(require_permission("record:write")),
    use_case: AppendRecordMediaUseCase = Depends(get_append_record_media_use_case),
) -> RecordSchema:
    view = await use_case.append_record_media(
        AppendRecordMediaCommand(ctx=ctx, visit_id=visit_id, media_id=body.media_id, phase=body.phase)
    )
    return RecordSchema.of(view)
```

`backend/apps/visit/adapter/inbound/api/v1/delete_visit_record_router.py`:

```python
from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
from visit.dependencies.delete_visit_record_provider import get_delete_visit_record_use_case

delete_visit_record_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 기록 삭제는 record:delete(사장)다 — 사진 한 장 빼기는 전체 교체(record:write)로 한다.
@delete_visit_record_router.delete("/{shop_id}/visits/{visit_id}/record", status_code=204)
async def delete_visit_record(
    visit_id: VisitId,
    ctx: ShopContext = Depends(require_permission("record:delete")),
    use_case: DeleteVisitRecordUseCase = Depends(get_delete_visit_record_use_case),
) -> Response:
    await use_case.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx, visit_id=visit_id))
    return Response(status_code=204)
```

`backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`:

```diff
@@ -74,3 +74,6 @@ class VisitRecordPgRepository(VisitRecordRepository):
             )
         ).scalar_one()
         return await self._assemble(row)
+
+    async def delete(self, ctx: ShopContext, visit_id: int) -> None:
+        await self._session.execute(delete(VisitRecordOrm).where(VisitRecordOrm.visit_id == visit_id))
```

`backend/apps/visit/app/dtos/append_record_media_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class AppendRecordMediaCommand:
    """사진·영상 하나를 기록의 그 칸(전/후) 맨 뒤에 붙인다. 앱의 업로드 대기열과 방문 상세의 [사진 추가]가 쓴다."""

    ctx: ShopContext
    visit_id: int
    media_id: int
    phase: str
```

`backend/apps/visit/app/dtos/delete_visit_record_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class DeleteVisitRecordCommand:
    ctx: ShopContext
    visit_id: int
```

`backend/apps/visit/app/ports/input/append_record_media_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.dtos.record_view_dto import RecordView


class AppendRecordMediaUseCase(ABC):
    @abstractmethod
    async def append_record_media(self, command: AppendRecordMediaCommand) -> RecordView: ...
```

`backend/apps/visit/app/ports/input/delete_visit_record_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand


class DeleteVisitRecordUseCase(ABC):
    @abstractmethod
    async def delete_visit_record(self, command: DeleteVisitRecordCommand) -> None: ...
```

`backend/apps/visit/app/use_cases/append_record_media_interactor.py`:

```python
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.dtos.record_view_dto import RecordView
from visit.app.ports.input.append_record_media_use_case import AppendRecordMediaUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.record_reader import describe_record
from visit.app.services.visit_locking import lock_visits
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.services.visit_record_rules import (
    append_media,
    check_media_limits,
    check_recordable,
    next_version,
)


class AppendRecordMediaInteractor(AppendRecordMediaUseCase):
    """사진·영상 하나를 덧붙인다(설계 8절). 기록이 없으면 빈 기록을 만든다. 버전은 받지 않고 올린다.

    같은 미디어가 이미 이 기록에 있으면 아무것도 바꾸지 않는다 — 대기열이 응답을 못 받고 다시 보내도 안전하다.
    잠금·상태 규칙은 전체 교체와 같다(고객 행 → 방문 행, 미용 중·완료만).
    """

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, menus: MenuRepository,
        directory: CustomerDirectoryPort, library: MediaLibraryPort,
    ) -> None:
        self._visits = visits
        self._records = records
        self._menus = menus
        self._directory = directory
        self._library = library

    async def append_record_media(self, command: AppendRecordMediaCommand) -> RecordView:
        ctx = command.ctx
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        check_recordable(visit)
        current = await self._records.get(ctx, visit.id)
        if current is not None and any(m.media_id == command.media_id for m in current.media):
            return await describe_record(ctx, current, self._menus, self._library)
        kinds = await self._library.claim(ctx, [command.media_id])
        media = append_media(current.media if current else (), command.media_id, kinds[command.media_id],
                             command.phase)
        check_media_limits(m.kind for m in media)
        saved = await self._records.save(ctx, VisitRecord(
            visit_id=visit.id,
            weight_kg=current.weight_kg if current else None,
            care_note=current.care_note if current else None,
            internal_note=current.internal_note if current else None,
            payment_method=current.payment_method if current else None,
            total_amount=current.total_amount if current else None,
            items=current.items if current else (),
            media=media,
            version=next_version(current),
            created_by_member_id=current.created_by_member_id if current else ctx.member_id,
            updated_by_member_id=ctx.member_id,
        ))
        return await describe_record(ctx, saved, self._menus, self._library)
```

`backend/apps/visit/app/use_cases/delete_visit_record_interactor.py`:

```python
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.visit_locking import lock_visits
from visit.domain.errors import RecordNotFoundError


class DeleteVisitRecordInteractor(DeleteVisitRecordUseCase):
    """기록을 지운다 — 방문은 남는다. 붙은 미디어는 놓고, 정리 스크립트가 지운다(설계 8절).
    상태와 상관없이 지울 수 있다(되돌린 방문에 남은 기록도)."""

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, directory: CustomerDirectoryPort,
        library: MediaLibraryPort,
    ) -> None:
        self._visits = visits
        self._records = records
        self._directory = directory
        self._library = library

    async def delete_visit_record(self, command: DeleteVisitRecordCommand) -> None:
        ctx = command.ctx
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        current = await self._records.get(ctx, visit.id)
        if current is None:
            raise RecordNotFoundError("기록이 없습니다.")
        await self._library.release(ctx, [m.media_id for m in current.media])
        await self._records.delete(ctx, visit.id)
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -33,6 +33,9 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "몸무게·케어 메모(공개)·내부 메모·결제 수단·총액(받은 돈)·실제 메뉴와 금액·사진영상(media 에서 확인한 "
                 "것, 전/후와 순서)을 담고, 돈 칸은 sales:write 가 필요합니다. 기록이 있으면 읽은 version 을 보내야 하고 "
                 "다르면 409 RECORD_VERSION_CONFLICT 입니다. 몸무게는 그 아이의 가장 최근 방문이면 현재 몸무게가 됩니다. "
+                "POST /visits/{visit_id}/record/media {media_id, phase} 는 사진·영상 하나를 그 칸 맨 뒤에 덧붙입니다"
+                "(기록이 없으면 만들고, 같은 미디어를 다시 보내도 한 번이며, 버전이 오릅니다). "
+                "DELETE /visits/{visit_id}/record 는 기록 삭제입니다(record:delete, 방문은 남습니다). "
                 "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                 "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}(이름·기본 소요·순서·정가 price, "
                 "원 단위, 비우면 가격 미정), "
```

`backend/apps/visit/dependencies/append_record_media_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.append_record_media_use_case import AppendRecordMediaUseCase
from visit.app.use_cases.append_record_media_interactor import AppendRecordMediaInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository


def get_append_record_media_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> AppendRecordMediaUseCase:
    return AppendRecordMediaInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db), menus=build_menu_repository(db),
        directory=directory, library=library,
    )
```

`backend/apps/visit/dependencies/delete_visit_record_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_record_repository, build_visit_repository


def get_delete_visit_record_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> DeleteVisitRecordUseCase:
    return DeleteVisitRecordInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db), directory=directory,
        library=library,
    )
```

`backend/main.py`:

```diff
@@ -64,9 +64,11 @@ from tenancy.dependencies.provision_shop_provider import get_provision_shop_use_
 from tenancy.dependencies.resolve_shop_access_provider import get_resolve_shop_access_use_case
 from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
 from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_router
+from visit.adapter.inbound.api.v1.append_record_media_router import append_record_media_router
 from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
 from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
 from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
+from visit.adapter.inbound.api.v1.delete_visit_record_router import delete_visit_record_router
 from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_visit_draft_router
 from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
 from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
@@ -154,6 +156,8 @@ app.include_router(get_visit_router)
 app.include_router(update_visit_router)
 app.include_router(get_next_visit_draft_router)
 app.include_router(put_visit_record_router)
+app.include_router(append_record_media_router)
+app.include_router(delete_visit_record_router)
 # media
 app.include_router(media_myself_router)
 app.include_router(issue_upload_router)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit tests/integration/test_visit_record_wiring.py -q -p no:cacheprovider` → 전부 통과

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 868 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 288 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 덧붙이기의 `if current is not None and any(m.media_id == command.media_id …)`를 `if False:`로 → `test_이미_붙은_미디어면_아무것도_바꾸지_않는다` 실패.
- 덧붙이기의 `weight_kg=current.weight_kg if current else None`을 `weight_kg=None`으로 → `test_있는_기록은_다른_칸을_그대로_두고_버전을_올린다` 실패.
- 삭제의 `await self._library.release(…)` 줄을 뺀다 → `test_잠근_뒤_미디어를_놓고_기록을_지운다` 실패.
- 삭제 라우터의 `require_permission("record:delete")`를 `"record:write"`로 → `test_직원은_기록을_지우지_못한다` 실패.
- `append_media`의 다시 매기기(`renumbered = [RecordMedia(…, order) …]`)를 `renumbered = same`으로 → `test_덧붙이면_그_칸의_맨_뒤이고…` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 사진 하나 덧붙이기와 기록 삭제 — POST /visits/{id}/record/media(맨 뒤·빈 기록 생성·같은 미디어 멱등·버전 올림), DELETE /visits/{id}/record(record:delete)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: 읽기에 기록과 대표 사진 — 상세의 `record`·`cover`·지난 방문 `cover`, 하루 목록의 `has_record`·`cover`, 달력의 `cover`·`covers`(완료 방문, 최대 4장)

**Files:**
- Modify: `backend/apps/visit/app/ports/output/visit_record_repository.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`
- Create: `backend/apps/visit/app/services/cover_reader.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_calendar_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/list_day_visits_schema.py`
- Modify: `backend/apps/visit/app/dtos/get_visit_calendar_dto.py`
- Modify: `backend/apps/visit/app/dtos/get_visit_dto.py`
- Modify: `backend/apps/visit/app/dtos/list_day_visits_dto.py`
- Modify: `backend/apps/visit/app/use_cases/get_visit_calendar_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/get_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/list_day_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Modify: `backend/apps/visit/dependencies/get_visit_calendar_provider.py`
- Modify: `backend/apps/visit/dependencies/get_visit_provider.py`
- Modify: `backend/apps/visit/dependencies/list_day_visits_provider.py`
- Modify: `backend/apps/visit/tests/adapter/test_get_visit_calendar_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_get_visit_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_list_day_visits_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_get_visit_calendar_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/builders.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/tests/integration/test_visit_record_wiring.py`

**Interfaces:**
- Consumes: 작업 6 의 `VisitRecordRepository.get`·`cover_media_id`·`describe_record`·`RecordSchema`·`FakeRecords`·`FakeLibrary`, 기존 상세·하루·달력 슬라이스.
- Produces: `VisitRecordRepository.list_many(ctx, visit_ids) -> dict[int, VisitRecord]`(기록 없는 방문은 키가 없다, 질의 셋 — `get`도 이 길로); `visit.app.services.cover_reader.cover_urls(ctx, records, library) -> dict[int, str]`; `VisitDetailView.record`·`.cover`, `PreviousVisitView.cover`; `DayVisitItemView.has_record`·`.cover`; `CalendarDayView.cover`·`.covers`; `get_visit_calendar_interactor.COVERS_PER_DAY = 4`; 생성자 — `GetVisitInteractor(visits, history, ledger, menus, directory, records, library)`, `ListDayVisitsInteractor(board, menus, schedule, directory, records, library, now)`, `GetVisitCalendarInteractor(board, schedule, records, library, now)`; 테스트 빌더 `visit.tests.helpers.builders.record(visit_id, media=((id, kind, phase, order), …), **fields)`.

기록을 기존 화면들의 응답에 싣는다(설계 9절 '기존 응답에 더하는 것'). 사진은 읽기 DTO 에만 붙이고 `VisitView`는 건드리지 않는다. 대표 사진은 후 사진 첫 장 → 전 사진 첫 장 → 영상 포스터다(도메인 `cover_media_id`). 하루 목록은 상태와 상관없이(미용 중의 전 사진도), 달력은 완료 방문만 시작 순으로 센다. 기록 여러 개는 `list_many`가 방문 수와 상관없이 질의 셋(기록·항목·미디어)으로 읽고, URL 은 `read_urls` 한 번으로 받는다. 기존 테스트는 생성자 인자와 새 칸만 더한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_get_visit_calendar_router.py`:

```diff
@@ -8,7 +8,7 @@ from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
 CALENDAR = VisitCalendarView(
     year=2026, month=9,
     days=[CalendarDayView(date=date(2026, 9, 1), visit_count=3, completed_count=1, open_count=2,
-                          unresolved_count=1, closed_day=False)],
+                          unresolved_count=1, closed_day=False, cover="t/1", covers=["t/1", "t/2"])],
     unresolved_total=4, oldest_unresolved_date=date(2026, 7, 14),
 )
 
@@ -23,5 +23,6 @@ async def test_달은_YYYY_MM_으로_받는다():
     assert (body["month"], body["unresolved_total"], body["oldest_unresolved_date"]) == (
         "2026-09", 4, "2026-07-14")
     assert body["days"][0] == {"date": "2026-09-01", "visit_count": 3, "completed_count": 1, "open_count": 2,
-                               "unresolved_count": 1, "closed_day": False}
+                               "unresolved_count": 1, "closed_day": False, "cover": "t/1",
+                               "covers": ["t/1", "t/2"]}
     assert (stub.calls[0].year, stub.calls[0].month) == (2026, 9)
```

`backend/apps/visit/tests/adapter/test_get_visit_router.py`:

```diff
@@ -10,8 +10,9 @@ from visit.tests.helpers.views import visit_view
 
 DETAIL = VisitDetailView(
     visit=visit_view(1), group=[visit_view(2)],
-    previous_visit=PreviousVisitView(visit_id=7, starts_at=datetime(2026, 9, 2, 14, tzinfo=ZoneInfo("Asia/Seoul"))),
-    no_show_count=1,
+    previous_visit=PreviousVisitView(visit_id=7, starts_at=datetime(2026, 9, 2, 14, tzinfo=ZoneInfo("Asia/Seoul")),
+                                     cover="t/70"),
+    no_show_count=1, record=None, cover=None,
 )
 
 
@@ -21,7 +22,8 @@ async def test_직원도_방문_상세를_본다():
         response = await c.get("/v1/shops/3/visits/1")
     body = response.json()
     assert (body["visit"]["visit_id"], [v["visit_id"] for v in body["group"]], body["no_show_count"]) == (1, [2], 1)
-    assert body["previous_visit"] == {"visit_id": 7, "starts_at": "2026-09-02T14:00:00+09:00"}
+    assert body["previous_visit"] == {"visit_id": 7, "starts_at": "2026-09-02T14:00:00+09:00", "cover": "t/70"}
+    assert (body["record"], body["cover"]) == (None, None)
     assert stub.calls[0].visit_id == 1
```

`backend/apps/visit/tests/adapter/test_list_day_visits_router.py`:

```diff
@@ -11,7 +11,7 @@ DAY = DayVisitsView(
     counts=DayCountsView(visit_count=1, reserved=1, in_progress=0, completed=0, canceled=0, no_show=0,
                          unresolved=0),
     items=[DayVisitItemView(visit=visit_view(), group_key="1:2026-10-02T05:00:00+00:00", overlapping=True,
-                            unresolved=False)],
+                            unresolved=False, has_record=True, cover="t/51")],
 )
 
 
@@ -23,6 +23,7 @@ async def test_직원도_하루_목록을_본다():
     body = response.json()
     assert (body["date"], body["counts"]["visit_count"], body["items"][0]["overlapping"]) == (
         "2026-10-02", 1, True)
+    assert (body["items"][0]["has_record"], body["items"][0]["cover"]) == (True, "t/51")
     assert body["items"][0]["visit"]["starts_at"] == "2026-10-02T14:00:00+09:00"
     assert stub.calls[0].day == date(2026, 10, 2)
     assert error_of(missing) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`:

```diff
@@ -61,3 +61,18 @@ async def test_지우면_항목과_미디어_연결도_함께_지워진다(db_se
     await repo.delete(A, visit_id)
     assert await repo.get(A, visit_id) is None
     await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))   # 연결이 남았으면 유일 위반
+
+
+async def test_기록이_있는_방문마다_기록_전체를_한_번에_읽는다(db_session):
+    repo, visit_id, bath, _ = await _setup(db_session)
+    bare = await insert_visit(db_session, kst(9, 24, 14), "in_progress")
+    none = await insert_visit(db_session, kst(9, 25, 14), "in_progress")
+    await repo.save(A, _record(visit_id, items=[RecordItem(bath, 1)],
+                               media=[RecordMedia(7, "photo", "after", 0), RecordMedia(8, "photo", "before", 0)]))
+    await repo.save(A, _record(bare))
+    found = await repo.list_many(A, [visit_id, bare, none])
+    assert set(found) == {visit_id, bare}
+    assert (found[visit_id].media, found[visit_id].items, found[bare].media) == (
+        (RecordMedia(8, "photo", "before", 0), RecordMedia(7, "photo", "after", 0)), (RecordItem(bath, 1),), ())
+    assert await repo.list_many(B, [visit_id]) == {}
+    assert await repo.list_many(A, []) == {}
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_calendar_interactor.py`:

```diff
@@ -7,8 +7,8 @@ from visit.app.use_cases.get_visit_calendar_interactor import GetVisitCalendarIn
 from visit.domain.errors import VisitInputError
 from visit.domain.value_objects.closed_date import ClosedDate
 from visit.domain.value_objects.schedule_settings import ScheduleSettings
-from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeSchedule, FakeVisits
+from visit.tests.helpers.builders import ctx, kst, record
+from visit.tests.helpers.fakes import FakeLibrary, FakeRecords, FakeSchedule, FakeVisits
 
 NOW = kst(9, 23, 15)
 
@@ -16,7 +16,8 @@ NOW = kst(9, 23, 15)
 def _setup():
     visits = FakeVisits()
     schedule = FakeSchedule(settings=ScheduleSettings(time(10), time(19), 120, frozenset({0})))
-    return visits, schedule, GetVisitCalendarInteractor(visits, schedule, now=lambda: NOW)
+    return visits, schedule, GetVisitCalendarInteractor(visits, schedule, FakeRecords(visits), FakeLibrary(),
+                                                        now=lambda: NOW)
 
 
 async def test_날마다_마릿수_완료_예약_정리_안_됨_휴무():
@@ -59,3 +60,21 @@ async def test_달이_이상하면_VALIDATION_ERROR_다(year, month):
     _, _, interactor = _setup()
     with pytest.raises(VisitInputError):
         await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=year, month=month))
+
+
+async def test_완료_방문의_대표_사진을_시작_순으로_최대_네_장():
+    visits = FakeVisits()
+    records, library = FakeRecords(visits), FakeLibrary()
+    interactor = GetVisitCalendarInteractor(visits, FakeSchedule(), records, library, now=lambda: NOW)
+    done = dict(status="completed", started_at=kst(9, 2, 9), completed_at=kst(9, 2, 18))
+    for hour, pet in ((15, 105), (10, 101), (11, 102), (12, 103), (13, 104)):
+        v = visits.seed(pet_id=pet, starts_at=kst(9, 2, hour), **done)
+        library.add(pet, attached=True)
+        records.seed(record(v.id, media=((pet, "photo", "after", 0),)))
+    working = visits.seed(pet_id=106, starts_at=kst(9, 2, 9), status="in_progress", started_at=kst(9, 2, 9))
+    library.add(106, attached=True)
+    records.seed(record(working.id, media=((106, "photo", "after", 0),)))   # 미용 중은 달력에 없다
+    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=9))
+    second = view.days[1]
+    assert (second.cover, second.covers) == ("t/101", ["t/101", "t/102", "t/103", "t/104"])
+    assert (view.days[2].cover, view.days[2].covers) == (None, [])
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`:

```diff
@@ -3,14 +3,24 @@ import pytest
 from visit.app.dtos.get_visit_dto import GetVisitQuery
 from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
 from visit.domain.errors import VisitNotFoundError
-from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits
+from visit.tests.helpers.builders import ctx, kst, record
+from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits
 
 
 def _setup():
     visits, directory = FakeVisits(), FakeDirectory()
     directory.family(1, pets=(101, 102))
-    return visits, GetVisitInteractor(visits, visits, visits, FakeMenus(), directory)
+    return visits, GetVisitInteractor(visits, visits, visits, FakeMenus(), directory, FakeRecords(visits),
+                                      FakeLibrary())
+
+
+def _with_records():
+    visits, directory, library = FakeVisits(), FakeDirectory(), FakeLibrary()
+    directory.family(1, pets=(101,))
+    records = FakeRecords(visits)
+    for media_id in (51, 52, 61):
+        library.add(media_id, kind="video" if media_id == 61 else "photo", attached=True)
+    return visits, records, GetVisitInteractor(visits, visits, visits, FakeMenus(), directory, records, library)
 
 
 async def test_묶음_지난_방문_노쇼_횟수를_함께_준다():
@@ -44,3 +54,24 @@ async def test_다른_매장의_방문은_VISIT_NOT_FOUND_다():
     theirs = visits.seed(shop_id=2)
     with pytest.raises(VisitNotFoundError):
         await interactor.get_visit(GetVisitQuery(ctx=ctx(shop_id=1), visit_id=theirs.id))
+
+
+async def test_기록과_대표_사진_지난_방문의_대표_사진을_함께_준다():
+    visits, records, interactor = _with_records()
+    last = visits.seed(pet_id=101, starts_at=kst(9, 2, 14), status="completed", started_at=kst(9, 2, 14),
+                       completed_at=kst(9, 2, 15))
+    today = visits.seed(pet_id=101, starts_at=kst(9, 23, 14), status="in_progress", started_at=kst(9, 23, 14))
+    records.seed(record(last.id, media=((61, "video", "after", 0),)))
+    records.seed(record(today.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
+                        care_note="눈물 자국", version=3))
+    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=today.id))
+    assert (detail.record.care_note, detail.record.version, [m.media_id for m in detail.record.media]) == (
+        "눈물 자국", 3, [51, 52])
+    assert (detail.cover, detail.previous_visit.cover) == ("t/52", "t/61")
+
+
+async def test_기록이_없으면_record_와_cover_가_비어_있다():
+    visits, _, interactor = _with_records()
+    kong = visits.seed(pet_id=101, starts_at=kst(9, 23, 14))
+    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
+    assert (detail.record, detail.cover) == (None, None)
```

`backend/apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py`:

```diff
@@ -6,8 +6,8 @@ from visit.app.dtos.list_day_visits_dto import ListDayVisitsQuery
 from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteractor
 from visit.domain.errors import VisitInputError
 from visit.domain.value_objects.schedule_settings import ScheduleSettings
-from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, FakeVisits
+from visit.tests.helpers.builders import ctx, kst, record
+from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeSchedule, FakeVisits
 
 NOW = kst(9, 23, 15)
 
@@ -17,7 +17,8 @@ def _setup(settings=None):
     directory.family(1, pets=(101, 102))
     directory.family(2, pets=(201,), name=None)   # 익명화한 고객
     schedule = FakeSchedule() if settings is None else FakeSchedule(settings=settings)
-    interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, now=lambda: NOW)
+    interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, FakeRecords(visits),
+                                         FakeLibrary(), now=lambda: NOW)
     return visits, interactor
 
 
@@ -78,8 +79,25 @@ async def test_휴무일을_알린다():
 async def test_범위_밖_날짜는_설정을_읽기_전에_거절한다():
     visits, directory = FakeVisits(), FakeDirectory()
     schedule = FakeSchedule()
-    interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, now=lambda: NOW)
+    interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, FakeRecords(visits),
+                                         FakeLibrary(), now=lambda: NOW)
     for day in (date(1, 1, 1), date(9999, 12, 31)):
         with pytest.raises(VisitInputError):
             await interactor.list_day_visits(ListDayVisitsQuery(ctx=ctx(), day=day))
     assert schedule.journal == []
+
+
+async def test_기록이_있는지와_대표_사진을_준다():
+    visits, directory = FakeVisits(), FakeDirectory()
+    directory.family(1, pets=(101, 102))
+    records, library = FakeRecords(visits), FakeLibrary()
+    library.add(51, attached=True)
+    interactor = ListDayVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory, records, library,
+                                         now=lambda: NOW)
+    photographed = visits.seed(pet_id=101, starts_at=kst(9, 23, 10), status="in_progress", started_at=kst(9, 23, 10))
+    noted = visits.seed(pet_id=102, starts_at=kst(9, 23, 11), status="in_progress", started_at=kst(9, 23, 11))
+    visits.seed(pet_id=101, starts_at=kst(9, 23, 16))
+    records.seed(record(photographed.id, media=((51, "photo", "before", 0),)))
+    records.seed(record(noted.id, care_note="메모만"))
+    view = await _day(interactor, date(2026, 9, 23))
+    assert [(i.has_record, i.cover) for i in view.items] == [(True, "t/51"), (True, None), (False, None)]
```

`backend/apps/visit/tests/helpers/builders.py`:

```diff
@@ -7,6 +7,7 @@ from datetime import datetime, timezone
 from hub.app.dtos.shop_context import ShopContext
 from visit.domain.entities.menu import Menu
 from visit.domain.entities.visit import RESERVED, Visit
+from visit.domain.entities.visit_record import RecordMedia, VisitRecord
 
 STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
 OWNER_PERMISSIONS = STAFF_PERMISSIONS | frozenset(
@@ -46,3 +47,14 @@ def menu(menu_id: int = 1, name: str = "목욕", minutes: int | None = 60, shop_
 
 def but(entity, **changes):
     return replace(entity, **changes)
+
+
+def record(visit_id: int, media: tuple[tuple[int, str, str, int], ...] = (), **overrides) -> VisitRecord:
+    """media 는 (media_id, kind, phase, sort_order) 묶음들."""
+    fields = dict(
+        visit_id=visit_id, weight_kg=None, care_note=None, internal_note=None, payment_method=None,
+        total_amount=None, items=(), media=tuple(RecordMedia(*m) for m in media), version=1,
+        created_by_member_id=11, updated_by_member_id=11,
+    )
+    fields.update(overrides)
+    return VisitRecord(**fields)
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -345,6 +345,9 @@ class FakeRecords(VisitRecordRepository):
             return None
         return self.rows.get(visit_id)
 
+    async def list_many(self, ctx, visit_ids):
+        return {i: self.rows[i] for i in visit_ids if i in self.rows and self.visits.rows[i].shop_id == ctx.shop_id}
+
     async def save(self, ctx, record):
         self.rows[record.visit_id] = record
         self.journal.append(("save_record", record.visit_id, record.version))
```

`backend/tests/integration/test_visit_record_wiring.py`:

```diff
@@ -140,3 +140,26 @@ async def test_덧붙이기는_기록을_만들고_다시_보내도_한_번이
     async with wired.engine.connect() as conn:
         attached = (await conn.execute(text("SELECT count(*) FROM media_objects WHERE attached_at IS NOT NULL"))).scalar()
     assert attached == 0
+
+
+async def test_상세_하루_달력이_기록과_대표_사진을_보여_준다(wired, media_storage):
+    shop_id, o, _ = await _shop(wired)
+    customer_id, pet_id = await _family(wired, shop_id, o)
+    visit_id = await _visit(wired, shop_id, o, customer_id, pet_id)
+    before, after = await ready_photo(wired, shop_id, o), await ready_photo(wired, shop_id, o)
+    await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=o, json={
+        "care_note": "눈물 자국 관리", "media": [{"media_id": before, "phase": "before", "sort_order": 0},
+                                              {"media_id": after, "phase": "after", "sort_order": 0}]})
+    done = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o,
+                                json={"visit_ids": [visit_id], "action": "complete"})
+    assert done.status_code == 200, done.text
+
+    detail = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=o)).json()
+    after_thumb = next(m["thumb_url"] for m in detail["record"]["media"] if m["media_id"] == after)
+    assert (detail["record"]["care_note"], detail["cover"]) == ("눈물 자국 관리", after_thumb)
+    day = _at(-1, 11)[:10]
+    item = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={day}", headers=o)).json()["items"][0]
+    assert (item["has_record"], item["cover"]) == (True, after_thumb)
+    calendar = (await wired.api.get(f"/v1/shops/{shop_id}/visits/calendar?month={day[:7]}", headers=o)).json()
+    that_day = next(d for d in calendar["days"] if d["date"] == day)
+    assert (that_day["cover"], that_day["covers"]) == (after_thumb, [after_thumb])
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit tests/integration/test_visit_record_wiring.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 3개 — `TypeError: CalendarDayView.__init__() got an unexpected keyword argument 'cover'`(`PreviousVisitView`의 `cover`, `DayVisitItemView`의 `has_record`).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/ports/output/visit_record_repository.py`:

```diff
@@ -16,6 +16,11 @@ class VisitRecordRepository(ABC):
     async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
         """없거나 다른 매장의 방문이면 None."""
 
+    @abstractmethod
+    async def list_many(self, ctx: ShopContext, visit_ids: list[int]) -> dict[int, VisitRecord]:
+        """기록이 있는 방문마다 기록 전체. 기록이 없는 방문은 키가 없다 — 상세·목록·달력의 '기록 있음'과
+        대표 사진을 방문 수와 상관없이 한 번에 읽는다."""
+
     @abstractmethod
     async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
         """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다."""
```

`backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`:

```diff
@@ -16,32 +16,41 @@ class VisitRecordPgRepository(VisitRecordRepository):
         self._session = session
 
     async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
-        row = (
+        return (await self.list_many(ctx, [visit_id])).get(visit_id)
+
+    async def list_many(self, ctx: ShopContext, visit_ids: list[int]) -> dict[int, VisitRecord]:
+        if not visit_ids:
+            return {}
+        rows = (
             await self._session.execute(
                 select(VisitRecordOrm)
                 .join(VisitOrm, VisitOrm.id == VisitRecordOrm.visit_id)
-                .where(VisitRecordOrm.visit_id == visit_id, VisitOrm.shop_id == ctx.shop_id)
+                .where(VisitRecordOrm.visit_id.in_(visit_ids), VisitOrm.shop_id == ctx.shop_id)
                 .execution_options(populate_existing=True)
             )
-        ).scalar_one_or_none()
-        return await self._assemble(row) if row is not None else None
-
-    async def _assemble(self, row: VisitRecordOrm) -> VisitRecord:
-        visit_id = row.visit_id
-        items = (
-            await self._session.execute(
-                select(VisitRecordItemOrm).where(VisitRecordItemOrm.visit_id == visit_id)
-                .order_by(VisitRecordItemOrm.menu_id).execution_options(populate_existing=True)
-            )
         ).scalars().all()
-        media = (
-            await self._session.execute(
-                select(VisitRecordMediaOrm).where(VisitRecordMediaOrm.visit_id == visit_id)
-                .order_by(VisitRecordMediaOrm.phase.desc(), VisitRecordMediaOrm.sort_order)   # before → after
+        return await self._assemble(rows)
+
+    async def _assemble(self, rows) -> dict[int, VisitRecord]:
+        """기록 행들에 항목·미디어를 한 번씩 읽어 붙인다(방문 수만큼 묻지 않는다)."""
+        ids = [row.visit_id for row in rows]
+        items: dict[int, list[VisitRecordItemOrm]] = {i: [] for i in ids}
+        media: dict[int, list[VisitRecordMediaOrm]] = {i: [] for i in ids}
+        if ids:
+            for item in (await self._session.execute(
+                select(VisitRecordItemOrm).where(VisitRecordItemOrm.visit_id.in_(ids))
+                .order_by(VisitRecordItemOrm.visit_id, VisitRecordItemOrm.menu_id)
                 .execution_options(populate_existing=True)
-            )
-        ).scalars().all()
-        return to_record(row, list(items), list(media))
+            )).scalars():
+                items[item.visit_id].append(item)
+            for m in (await self._session.execute(
+                select(VisitRecordMediaOrm).where(VisitRecordMediaOrm.visit_id.in_(ids))
+                .order_by(VisitRecordMediaOrm.visit_id, VisitRecordMediaOrm.phase.desc(),   # before → after
+                          VisitRecordMediaOrm.sort_order)
+                .execution_options(populate_existing=True)
+            )).scalars():
+                media[m.visit_id].append(m)
+        return {row.visit_id: to_record(row, items[row.visit_id], media[row.visit_id]) for row in rows}
 
     async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
         fields = dict(
@@ -73,7 +82,7 @@ class VisitRecordPgRepository(VisitRecordRepository):
                 .execution_options(populate_existing=True)
             )
         ).scalar_one()
-        return await self._assemble(row)
+        return (await self._assemble([row]))[record.visit_id]
 
     async def delete(self, ctx: ShopContext, visit_id: int) -> None:
         await self._session.execute(delete(VisitRecordOrm).where(VisitRecordOrm.visit_id == visit_id))
```

`backend/apps/visit/app/services/cover_reader.py`:

```python
"""대표 사진의 썸네일 URL — 방문마다 대표를 도메인 규칙(`cover_media_id`)으로 고르고 URL 은 허브 포트로 한 번에 받는다."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.services.visit_record_rules import cover_media_id


async def cover_urls(
    ctx: ShopContext, records: dict[int, VisitRecord], library: MediaLibraryPort
) -> dict[int, str]:
    """{방문 ID: 대표 사진의 썸네일 URL}. 사진·영상이 없는 방문은 빠진다."""
    covers = {visit_id: cover_media_id(record.media) for visit_id, record in records.items()}
    urls = await library.read_urls(ctx, sorted({m for m in covers.values() if m is not None}))
    return {visit_id: urls[m].thumb_url for visit_id, m in covers.items() if m in urls}
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_calendar_schema.py`:

```diff
@@ -14,6 +14,8 @@ class CalendarDaySchema(BaseModel):
     open_count: int
     unresolved_count: int
     closed_day: bool
+    cover: str | None   # 그날 완료 방문의 첫 대표 사진 썸네일 URL
+    covers: list[str]   # 미리보기 카드 — 최대 4장
 
 
 class VisitCalendarSchema(BaseModel):
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_schema.py`:

```diff
@@ -4,6 +4,7 @@ from datetime import datetime
 
 from pydantic import BaseModel
 
+from visit.adapter.inbound.api.schemas.record_view_schema import RecordSchema
 from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
 from visit.app.dtos.get_visit_dto import VisitDetailView
 
@@ -11,6 +12,7 @@ from visit.app.dtos.get_visit_dto import VisitDetailView
 class PreviousVisitSchema(BaseModel):
     visit_id: int
     starts_at: datetime
+    cover: str | None
 
 
 class VisitDetailSchema(BaseModel):
@@ -18,6 +20,8 @@ class VisitDetailSchema(BaseModel):
     group: list[VisitSchema]
     previous_visit: PreviousVisitSchema | None
     no_show_count: int
+    record: RecordSchema | None   # 미용 기록 — 없으면 null
+    cover: str | None             # 대표 사진 썸네일 URL
 
     @classmethod
     def of(cls, view: VisitDetailView) -> VisitDetailSchema:
```

`backend/apps/visit/adapter/inbound/api/schemas/list_day_visits_schema.py`:

```diff
@@ -23,6 +23,8 @@ class DayVisitItemSchema(BaseModel):
     group_key: str
     overlapping: bool
     unresolved: bool
+    has_record: bool
+    cover: str | None   # 대표 사진 썸네일 URL
 
 
 class DayVisitsSchema(BaseModel):
```

`backend/apps/visit/app/dtos/get_visit_calendar_dto.py`:

```diff
@@ -21,6 +21,8 @@ class CalendarDayView:
     open_count: int        # 예약됨·미용 중
     unresolved_count: int  # 지난 날인데 아직 예약됨
     closed_day: bool
+    cover: str | None      # 그날 완료 방문 가운데 시작 순 첫 대표 사진의 썸네일
+    covers: list[str]      # 미리보기 카드용 — 같은 순서로 최대 4장
 
 
 @dataclass(frozen=True)
```

`backend/apps/visit/app/dtos/get_visit_dto.py`:

```diff
@@ -4,6 +4,7 @@ from dataclasses import dataclass
 from datetime import datetime
 
 from hub.app.dtos.shop_context import ShopContext
+from visit.app.dtos.record_view_dto import RecordView
 from visit.app.dtos.visit_view_dto import VisitView
 
 
@@ -17,6 +18,7 @@ class GetVisitQuery:
 class PreviousVisitView:
     visit_id: int
     starts_at: datetime   # 매장 시간대
+    cover: str | None     # 그 방문 기록의 대표 사진 썸네일
 
 
 @dataclass(frozen=True)
@@ -25,3 +27,5 @@ class VisitDetailView:
     group: list[VisitView]                 # 같은 묶음의 다른 방문(같은 보호자 + 같은 시작 시각)
     previous_visit: PreviousVisitView | None   # 그 아이(보호자만이면 보호자)의 지난 완료 방문
     no_show_count: int                     # 이 보호자의 노쇼 횟수
+    record: RecordView | None              # 미용 기록 — 없으면 None
+    cover: str | None                      # 대표 사진 썸네일(후 → 전 → 영상 포스터)
```

`backend/apps/visit/app/dtos/list_day_visits_dto.py`:

```diff
@@ -44,6 +44,8 @@ class DayVisitItemView:
     group_key: str      # 가족 묶음 — 같은 값끼리 한 카드로 묶는다
     overlapping: bool   # 다른 묶음과 시간이 겹친다
     unresolved: bool    # 지난 날인데 아직 예약됨
+    has_record: bool    # 미용 기록이 있다
+    cover: str | None   # 대표 사진 썸네일
 
 
 @dataclass(frozen=True)
```

`backend/apps/visit/app/use_cases/get_visit_calendar_interactor.py`:

```diff
@@ -5,6 +5,7 @@ from collections import defaultdict
 from collections.abc import Callable
 from datetime import date, datetime
 
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.dtos.get_visit_calendar_dto import (
     CalendarDayView,
     GetVisitCalendarQuery,
@@ -13,20 +14,27 @@ from visit.app.dtos.get_visit_calendar_dto import (
 from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_record_repository import VisitRecordRepository
+from visit.app.services.cover_reader import cover_urls
 from visit.domain.entities.visit import COMPLETED
 from visit.domain.errors import VisitInputError
 from visit.domain.services.visit_board import COUNTED, is_unresolved
 from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date
 
+COVERS_PER_DAY = 4   # 미리보기 카드에 겹쳐 보이는 썸네일 수
+
 
 class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
-    """월 달력 — 날마다 마릿수·완료·예약·정리 안 됨, 휴무. 위쪽 '정리 안 된 예약 N건'은 매장 전체다."""
+    """월 달력 — 날마다 마릿수·완료·예약·정리 안 됨, 휴무, 대표 사진. 위쪽 '정리 안 된 예약 N건'은 매장 전체다."""
 
     def __init__(
-        self, board: VisitBoardRepository, schedule: ScheduleRepository, now: Callable[[], datetime]
+        self, board: VisitBoardRepository, schedule: ScheduleRepository, records: VisitRecordRepository,
+        library: MediaLibraryPort, now: Callable[[], datetime],
     ) -> None:
         self._board = board
         self._schedule = schedule
+        self._records = records
+        self._library = library
         self._now = now
 
     async def get_visit_calendar(self, query: GetVisitCalendarQuery) -> VisitCalendarView:
@@ -41,13 +49,17 @@ class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
         today = local_date(self._now(), tz)
 
         by_day = defaultdict(list)
-        for visit in await self._board.list_between(ctx, start, end):
+        month_visits = await self._board.list_between(ctx, start, end)   # 시작 순
+        for visit in month_visits:
             by_day[local_date(visit.starts_at, tz)].append(visit)
+        completed_ids = [v.id for v in month_visits if v.status == COMPLETED]
+        covers = await cover_urls(ctx, await self._records.list_many(ctx, completed_ids), self._library)
         closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, first_day, last_day))
         days = []
         for number in range(1, last + 1):
             day = date(query.year, query.month, number)
             visits = by_day[day]
+            day_covers = [covers[v.id] for v in visits if v.id in covers]   # 완료 방문만 covers 에 있다
             days.append(CalendarDayView(
                 date=day,
                 visit_count=sum(v.status in COUNTED for v in visits),
@@ -55,6 +67,8 @@ class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
                 open_count=sum(v.is_active for v in visits),
                 unresolved_count=sum(is_unresolved(v, today, tz) for v in visits),
                 closed_day=is_closed_day(day, settings, closed),
+                cover=day_covers[0] if day_covers else None,
+                covers=day_covers[:COVERS_PER_DAY],
             ))
         today_start, _ = day_bounds(today, tz)
         total, oldest = await self._board.unresolved_before(ctx, today_start)
```

`backend/apps/visit/app/use_cases/get_visit_interactor.py`:

```diff
@@ -3,25 +3,32 @@ from __future__ import annotations
 from zoneinfo import ZoneInfo
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.dtos.get_visit_dto import GetVisitQuery, PreviousVisitView, VisitDetailView
 from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
+from visit.app.ports.output.visit_record_repository import VisitRecordRepository
+from visit.app.services.cover_reader import cover_urls
+from visit.app.services.record_reader import describe_record
 from visit.app.services.visit_reader import describe_visits
 
 
 class GetVisitInteractor(GetVisitUseCase):
     def __init__(
         self, visits: VisitLookupRepository, history: VisitHistoryRepository, ledger: VisitLedgerRepository,
-        menus: MenuRepository, directory: CustomerDirectoryPort,
+        menus: MenuRepository, directory: CustomerDirectoryPort, records: VisitRecordRepository,
+        library: MediaLibraryPort,
     ) -> None:
         self._visits = visits
         self._history = history
         self._ledger = ledger
         self._menus = menus
         self._directory = directory
+        self._records = records
+        self._library = library
 
     async def get_visit(self, query: GetVisitQuery) -> VisitDetailView:
         ctx = query.ctx
@@ -30,11 +37,17 @@ class GetVisitInteractor(GetVisitUseCase):
                  if v.id != visit.id]
         previous = await self._history.last_completed_before(ctx, visit.customer_id, visit.pet_id, visit.starts_at)
         [view, *group_views] = await describe_visits(ctx, [visit, *group], self._directory, self._menus)
+        records = await self._records.list_many(ctx, [visit.id] + ([previous.id] if previous else []))
+        record = records.get(visit.id)
+        covers = await cover_urls(ctx, records, self._library)
         return VisitDetailView(
             visit=view,
             group=group_views,
             previous_visit=PreviousVisitView(
-                visit_id=previous.id, starts_at=previous.starts_at.astimezone(ZoneInfo(ctx.timezone))
+                visit_id=previous.id, starts_at=previous.starts_at.astimezone(ZoneInfo(ctx.timezone)),
+                cover=covers.get(previous.id),
             ) if previous else None,
             no_show_count=await self._ledger.count_no_show(ctx, visit.customer_id),
+            record=await describe_record(ctx, record, self._menus, self._library) if record else None,
+            cover=covers.get(visit.id),
         )
```

`backend/apps/visit/app/use_cases/list_day_visits_interactor.py`:

```diff
@@ -4,6 +4,7 @@ from collections.abc import Callable
 from datetime import datetime
 
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.dtos.list_day_visits_dto import (
     DayCountsView,
     DayVisitItemView,
@@ -14,6 +15,8 @@ from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_record_repository import VisitRecordRepository
+from visit.app.services.cover_reader import cover_urls
 from visit.app.services.visit_reader import describe_visits
 from visit.domain.errors import VisitInputError
 from visit.domain.services.visit_board import is_unresolved, overlaps_other_group, status_counts
@@ -25,12 +28,15 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
 
     def __init__(
         self, board: VisitBoardRepository, menus: MenuRepository, schedule: ScheduleRepository,
-        directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        directory: CustomerDirectoryPort, records: VisitRecordRepository, library: MediaLibraryPort,
+        now: Callable[[], datetime],
     ) -> None:
         self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
+        self._records = records
+        self._library = library
         self._now = now
 
     async def list_day_visits(self, query: ListDayVisitsQuery) -> DayVisitsView:
@@ -44,12 +50,16 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
         closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
         today = local_date(self._now(), tz)
         views = await describe_visits(ctx, visits, self._directory, self._menus)
+        recorded = await self._records.list_many(ctx, [v.id for v in visits])
+        covers = await cover_urls(ctx, recorded, self._library)
         items = [
             DayVisitItemView(
                 visit=view,
                 group_key=f"{visit.customer_id}:{visit.starts_at.isoformat()}",
                 overlapping=overlaps_other_group(visit, occupied),
                 unresolved=is_unresolved(visit, today, tz),
+                has_record=visit.id in recorded,
+                cover=covers.get(visit.id),
             )
             for visit, view in zip(visits, views)
         ]
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -36,6 +36,8 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "POST /visits/{visit_id}/record/media {media_id, phase} 는 사진·영상 하나를 그 칸 맨 뒤에 덧붙입니다"
                 "(기록이 없으면 만들고, 같은 미디어를 다시 보내도 한 번이며, 버전이 오릅니다). "
                 "DELETE /visits/{visit_id}/record 는 기록 삭제입니다(record:delete, 방문은 남습니다). "
+                "방문 상세는 record(기록 전체, 사진 URL 포함)와 cover(대표 사진 썸네일 — 후 → 전 → 영상 포스터), "
+                "하루 목록은 항목마다 has_record·cover, 달력은 날마다 완료 방문의 cover·covers(최대 4장)를 줍니다. "
                 "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                 "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}(이름·기본 소요·순서·정가 price, "
                 "원 단위, 비우면 가격 미정), "
```

`backend/apps/visit/dependencies/get_visit_calendar_provider.py`:

```diff
@@ -1,13 +1,20 @@
 from __future__ import annotations
 
+from fastapi import Depends
+
 from core.database import DbSession
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
 from visit.app.use_cases.get_visit_calendar_interactor import GetVisitCalendarInteractor
-from visit.dependencies.visit_wiring import build_schedule_repository, build_visit_repository
+from visit.dependencies.hub_ports import get_media_library
+from visit.dependencies.visit_wiring import build_record_repository, build_schedule_repository, build_visit_repository
 from visit.domain.services.visit_schedule import utc_now
 
 
-def get_get_visit_calendar_use_case(db: DbSession) -> GetVisitCalendarUseCase:
+def get_get_visit_calendar_use_case(
+    db: DbSession, library: MediaLibraryPort = Depends(get_media_library)
+) -> GetVisitCalendarUseCase:
     return GetVisitCalendarInteractor(
-        board=build_visit_repository(db), schedule=build_schedule_repository(db), now=utc_now
+        board=build_visit_repository(db), schedule=build_schedule_repository(db),
+        records=build_record_repository(db), library=library, now=utc_now,
     )
```

`backend/apps/visit/dependencies/get_visit_provider.py`:

```diff
@@ -4,16 +4,20 @@ from fastapi import Depends
 
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
 from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
-from visit.dependencies.hub_ports import get_customer_directory
-from visit.dependencies.visit_wiring import build_menu_repository, build_visit_repository
+from visit.dependencies.hub_ports import get_customer_directory, get_media_library
+from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository
 
 
 def get_get_visit_use_case(
-    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
+    db: DbSession,
+    directory: CustomerDirectoryPort = Depends(get_customer_directory),
+    library: MediaLibraryPort = Depends(get_media_library),
 ) -> GetVisitUseCase:
     visits = build_visit_repository(db)
     return GetVisitInteractor(
-        visits=visits, history=visits, ledger=visits, menus=build_menu_repository(db), directory=directory
+        visits=visits, history=visits, ledger=visits, menus=build_menu_repository(db), directory=directory,
+        records=build_record_repository(db), library=library,
     )
```

`backend/apps/visit/dependencies/list_day_visits_provider.py`:

```diff
@@ -4,11 +4,13 @@ from fastapi import Depends
 
 from core.database import DbSession
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
 from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteractor
-from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_customer_directory, get_media_library
 from visit.dependencies.visit_wiring import (
     build_menu_repository,
+    build_record_repository,
     build_schedule_repository,
     build_visit_repository,
 )
@@ -16,9 +18,12 @@ from visit.domain.services.visit_schedule import utc_now
 
 
 def get_list_day_visits_use_case(
-    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
+    db: DbSession,
+    directory: CustomerDirectoryPort = Depends(get_customer_directory),
+    library: MediaLibraryPort = Depends(get_media_library),
 ) -> ListDayVisitsUseCase:
     return ListDayVisitsInteractor(
         board=build_visit_repository(db), menus=build_menu_repository(db),
-        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
+        schedule=build_schedule_repository(db), directory=directory, records=build_record_repository(db),
+        library=library, now=utc_now,
     )
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit tests/integration/test_visit_record_wiring.py -q -p no:cacheprovider` → 전부 통과

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 872 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 290 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 달력의 `completed_ids = [v.id for v in month_visits if v.status == COMPLETED]`에서 조건을 뺀다 → `test_완료_방문의_대표_사진을_시작_순으로_최대_네_장` 실패(미용 중 방문이 끼어든다).
- 달력의 `covers=day_covers[:COVERS_PER_DAY]`를 `covers=day_covers`로 → 같은 테스트 실패.
- 하루 목록의 `has_record=visit.id in recorded`를 `visit.id in covers`로 → `test_기록이_있는지와_대표_사진을_준다` 실패(사진 없는 기록).
- 상세의 지난 방문 `cover=covers.get(previous.id)`를 `cover=None`으로 → `test_기록과_대표_사진_지난_방문의_대표_사진을_함께_준다` 실패.
- `VisitRecordPgRepository.list_many`의 `VisitOrm.shop_id == ctx.shop_id`를 뺀다 → `test_기록이_있는_방문마다_기록_전체를_한_번에_읽는다`·`test_다른_매장의_방문의_기록은_없는_것이다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 읽기에 기록과 대표 사진 — 상세의 record·cover·지난 방문 cover, 하루 목록의 has_record·cover, 달력의 cover·covers(완료 방문, 최대 4장)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: 피드 — `GET /visits/feed`(완료 시각 역순·커서·`pet_id`), 방문 리포지토리의 여섯째 축 `VisitFeedRepository`

**Files:**
- Create: `backend/apps/visit/app/ports/output/visit_feed_repository.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/list_visit_feed_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/list_visit_feed_router.py`
- Create: `backend/apps/visit/app/dtos/list_visit_feed_dto.py`
- Create: `backend/apps/visit/app/ports/input/list_visit_feed_use_case.py`
- Create: `backend/apps/visit/app/use_cases/list_visit_feed_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/dependencies/list_visit_feed_provider.py`
- Create: `backend/apps/visit/tests/adapter/test_list_visit_feed_router.py`
- Modify: `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Modify: `backend/apps/visit/tests/app/test_visit_port_segregation.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_list_visit_feed_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/integration/test_visit_record_wiring.py`

**Interfaces:**
- Consumes: 작업 8 의 `list_many`·`cover_urls`, 작업 6 의 `MenuRepository.list_by_ids`·`FakeRecords`·`FakeLibrary`, `describe_visits`(보호자·아이 요약과 예약 메뉴), `VisitPgRepository.get_many`.
- Produces: `visit.app.ports.output.visit_feed_repository` — `FeedPage(visits, next_cursor)`, `VisitFeedRepository.list_completed(ctx, cursor, limit, pet_id) -> FeedPage`(커서가 틀리면 `VisitInputError`); `VisitPgRepository`·`FakeVisits`가 여섯 포트를 낸다(커서는 pg 에서 base64 JSON `[완료 시각, 방문 ID]`, 스텁에서는 마지막 방문 ID 글자 — 부르는 쪽은 열어 보지 않는다); `ListVisitFeedInteractor(feed, records, menus, directory, library)`(`CARE_NOTE_PREVIEW = 80`), `ListVisitFeedQuery(ctx, cursor, limit, pet_id)`, `FeedItemView`, `VisitFeedView(items, next_cursor)`; 새 경로 `GET /v1/shops/{shop_id}/visits/feed?cursor=&limit=&pet_id=`(멤버, `limit` 1~50 기본 20) — `main.py`에서 `/visits/{visit_id}`보다 먼저 붙인다. `test_visit_port_segregation.py`의 포트 목록에 `VisitFeedRepository`를 더한다(여섯).

캘린더 탭의 [피드]와 반려동물 상세의 [기록] 탭(`pet_id`)이 쓰는 목록이다(설계 9절·10.1 ②·⑦). 게시판(시작 시각 범위)과 읽는 축이 달라 포트를 새로 만든다(④-0 규칙: 새 축이면 새 포트). 카드마다 보호자·아이 요약, 대표 사진(없으면 null — 앱의 회색 자리), 메뉴 이름(기록의 실제 메뉴, 없으면 예약 메뉴), 케어 메모 앞 80자, 사진 수를 준다. 같은 완료 시각은 방문 ID 역순으로 나눠 커서가 줄을 건너뛰지 않는다. 한 쪽을 읽는 질의 수는 카드 수와 상관없다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_list_visit_feed_router.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.list_visit_feed_router import list_visit_feed_router
from visit.app.dtos.list_visit_feed_dto import FeedItemView, VisitFeedView
from visit.dependencies.list_visit_feed_provider import get_list_visit_feed_use_case
from visit.domain.errors import VisitInputError
from visit.tests.helpers.api import READ_ONLY, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

_V = visit_view()
FEED = VisitFeedView(
    items=[FeedItemView(visit_id=4, customer=_V.customer, pet=_V.pet,
                        completed_at=datetime(2026, 9, 9, 12, tzinfo=ZoneInfo("Asia/Seoul")), cover="t/51",
                        menus=["전체 미용"], care_note="눈물 자국", media_count=3)],
    next_cursor="abc",
)


async def test_멤버는_피드를_본다_기본은_20개():
    stub = Recorder(FEED)
    async with client(build_app(list_visit_feed_router, get_list_visit_feed_use_case, stub, READ_ONLY)) as c:
        response = await c.get("/v1/shops/3/visits/feed")
        await c.get("/v1/shops/3/visits/feed?cursor=abc&limit=50&pet_id=101")
    body = response.json()
    assert (body["next_cursor"], body["items"][0]["cover"], body["items"][0]["pet"]["name"]) == ("abc", "t/51", "콩이")
    assert body["items"][0]["completed_at"] == "2026-09-09T12:00:00+09:00"
    assert [(q.cursor, q.limit, q.pet_id) for q in stub.calls] == [(None, 20, None), ("abc", 50, 101)]


async def test_쪽_크기와_반려동물_ID_의_범위_잘못된_커서():
    async with client(build_app(list_visit_feed_router, get_list_visit_feed_use_case, Recorder(FEED))) as c:
        for query in ("limit=0", "limit=51", "pet_id=0", "cursor=" + "a" * 201):
            assert error_of(await c.get(f"/v1/shops/3/visits/feed?{query}")) == (422, "VALIDATION_ERROR")
    stub = Recorder(error=VisitInputError("목록 위치(cursor)가 올바르지 않습니다."))
    async with client(build_app(list_visit_feed_router, get_list_visit_feed_use_case, stub)) as c:
        assert error_of(await c.get("/v1/shops/3/visits/feed?cursor=zz")) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py`:

```diff
@@ -5,7 +5,7 @@ import pytest
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
-from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
+from visit.domain.errors import VisitDuplicateError, VisitInputError, VisitNotFoundError
 from visit.domain.state.visit_state import StatusChange
 from visit.domain.value_objects.new_visit import NewVisit
 from visit.tests.helpers.builders import ctx, kst
@@ -200,3 +200,23 @@ async def test_그_아이의_가장_최근_시작한_방문(db_session):
     await insert_visit(db_session, kst(9, 22, 14), "canceled")
     await insert_visit(db_session, kst(9, 21, 14), "completed", shop_id=2)
     assert await repo.latest_started_of_pet(A, 101) == latest
+
+
+async def test_피드는_완료_시각_역순이고_커서로_이어_읽는다(db_session):
+    repo = VisitPgRepository(db_session)
+    first = await insert_visit(db_session, kst(9, 1, 14), "completed")
+    tie_low = await insert_visit(db_session, kst(9, 2, 14), "completed")
+    tie_high = await insert_visit(db_session, kst(9, 2, 14), "completed", pet_id=102)   # 같은 완료 시각
+    await insert_visit(db_session, kst(9, 3, 14), "in_progress")
+    await insert_visit(db_session, kst(9, 4, 14), "completed", shop_id=2)
+    page = await repo.list_completed(A, None, 2, None)
+    rest = await repo.list_completed(A, page.next_cursor, 2, None)
+    assert ([v.id for v in page.visits], [v.id for v in rest.visits], rest.next_cursor) == (
+        [tie_high, tie_low], [first], None)
+    assert [v.id for v in (await repo.list_completed(A, None, 5, 102)).visits] == [tie_high]
+
+
+async def test_피드_커서가_틀리면_VisitInputError(db_session):
+    for bad in ("zz", "W10", "WyIyMDI2LTA5LTAxVDA1OjAwOjAwIiwgMV0"):   # 깨진 값, 빈 목록, 시간대 없는 시각
+        with pytest.raises(VisitInputError):
+            await VisitPgRepository(db_session).list_completed(A, bad, 5, None)
```

`backend/apps/visit/tests/app/test_visit_port_segregation.py`:

```diff
@@ -1,4 +1,4 @@
-"""visits 표의 리포지토리 포트 다섯 — 인터페이스 분리를 구조로 고정한다.
+"""visits 표의 리포지토리 포트 여섯 — 인터페이스 분리를 구조로 고정한다.
 
 손으로 관리하는 목록 대신 인터랙터 생성자의 타입 힌트를 읽는다. 조회 유스케이스가 쓰기 포트를 받게 되거나,
 한 메서드가 두 포트에 들어가면 여기서 걸린다.
@@ -13,6 +13,7 @@ from typing import get_type_hints
 import visit.app.use_cases as use_cases
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
@@ -20,7 +21,7 @@ from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.tests.helpers.fakes import FakeVisits
 
 PORTS = (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
-         VisitBoardRepository)
+         VisitBoardRepository, VisitFeedRepository)
 
 
 def _interactors():
@@ -37,13 +38,13 @@ def _ports_taken(cls) -> list[type]:
     return [hint for name, hint in hints.items() if name != "return" and hint in PORTS]
 
 
-def test_pg_구현은_다섯_포트를_다_낸다():
+def test_pg_구현은_여섯_포트를_다_낸다():
     assert all(issubclass(VisitPgRepository, port) for port in PORTS)
     missing = sorted(set(VisitPgRepository.__abstractmethods__))
     assert missing == []
 
 
-def test_스텁도_다섯_포트의_메서드를_다_가진다():
+def test_스텁도_여섯_포트의_메서드를_다_가진다():
     for port in PORTS:
         for name in port.__abstractmethods__:
             assert callable(getattr(FakeVisits, name, None)), f"FakeVisits 에 {port.__name__}.{name} 이 없다"
```

`backend/apps/visit/tests/app/use_cases/test_list_visit_feed_interactor.py`:

```python
from visit.app.dtos.list_visit_feed_dto import ListVisitFeedQuery
from visit.app.use_cases.list_visit_feed_interactor import ListVisitFeedInteractor
from visit.domain.entities.visit_record import RecordItem
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits


class _World:
    def __init__(self):
        self.visits, self.directory, self.menus = FakeVisits(), FakeDirectory(), FakeMenus()
        self.directory.family(1, pets=(101, 102))
        self.records, self.library = FakeRecords(self.visits), FakeLibrary()
        self.bath, self.trim = self.menus.seed("목욕"), self.menus.seed("전체 미용")
        self.interactor = ListVisitFeedInteractor(self.visits, self.records, self.menus, self.directory, self.library)

    def done(self, day, pet_id=101, menu_ids=(), shop_id=1):
        return self.visits.seed(pet_id=pet_id, starts_at=kst(9, day, 10), status="completed", shop_id=shop_id,
                                started_at=kst(9, day, 10), completed_at=kst(9, day, 12), menu_ids=menu_ids)

    async def feed(self, cursor=None, limit=20, pet_id=None, shop_id=1):
        return await self.interactor.list_visit_feed(
            ListVisitFeedQuery(ctx=ctx(shop_id=shop_id), cursor=cursor, limit=limit, pet_id=pet_id))


async def test_완료_방문을_완료_시각_역순으로_카드로_준다():
    w = _World()
    older = w.done(2, menu_ids=(w.bath.id,))
    newer = w.done(9, pet_id=102)
    w.visits.seed(pet_id=101, starts_at=kst(9, 10, 10))   # 예약됨은 나오지 않는다
    w.library.add(51, attached=True)
    w.records.seed(record(newer.id, media=((51, "photo", "after", 0),), care_note="가" * 100,
                          items=(RecordItem(w.trim.id, 50_000),)))
    view = await w.feed()
    assert [i.visit_id for i in view.items] == [newer.id, older.id]
    first, second = view.items
    assert (first.cover, first.media_count, first.menus, len(first.care_note)) == ("t/51", 1, ["전체 미용"], 80)
    assert (second.cover, second.media_count, second.menus, second.care_note) == (None, 0, ["목욕"], None)
    assert (first.pet.name, first.customer.name, first.completed_at.isoformat()) == (
        "아이102", "김민지", "2026-09-09T12:00:00+09:00")
    assert view.next_cursor is None


async def test_커서로_이어_읽고_그_아이만_거를_수_있다():
    w = _World()
    ids = [w.done(day).id for day in (1, 2, 3)]
    w.done(4, pet_id=102)
    first = await w.feed(limit=2, pet_id=101)
    rest = await w.feed(cursor=first.next_cursor, limit=2, pet_id=101)
    assert ([i.visit_id for i in first.items], [i.visit_id for i in rest.items], rest.next_cursor) == (
        [ids[2], ids[1]], [ids[0]], None)


async def test_다른_매장의_방문은_나오지_않는다():
    w = _World()
    w.done(2, shop_id=2)
    assert (await w.feed()).items == []
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -23,6 +23,7 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_feed_repository import FeedPage, VisitFeedRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
@@ -182,8 +183,13 @@ class FakeDirectory(CustomerDirectoryPort):
         return list(self.candidates)
 
 
-class FakeVisits(VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository):
-    """visits 표 스텁 — pg 구현처럼 다섯 포트(찾기·잠금, 쓰기, 이력, 원장, 게시판)를 한 객체가 다 낸다."""
+class FakeVisits(
+    VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository, VisitFeedRepository,
+):
+    """visits 표 스텁 — pg 구현처럼 여섯 포트(찾기·잠금, 쓰기, 이력, 원장, 게시판, 피드)를 한 객체가 다 낸다.
+
+    피드 커서는 마지막으로 준 방문 ID 를 글자로 쓴다(pg 구현의 모양과 다르다 — 부르는 쪽은 커서를 열어 보지 않는다).
+    """
 
     def __init__(self, journal: Journal | None = None) -> None:
         self.journal = journal if journal is not None else Journal()
@@ -322,6 +328,15 @@ class FakeVisits(VisitWriteRepository, VisitHistoryRepository, VisitLedgerReposi
         found = [v for v in self._mine(ctx) if v.status == "reserved" and v.starts_at < before]
         return len(found), (found[0].starts_at if found else None)
 
+    async def list_completed(self, ctx, cursor, limit, pet_id):
+        done = sorted((v for v in self._mine(ctx) if v.status == "completed" and (pet_id is None or v.pet_id == pet_id)),
+                      key=lambda v: (v.completed_at, v.id), reverse=True)
+        if cursor is not None:
+            after = self.rows[int(cursor)]
+            done = [v for v in done if (v.completed_at, v.id) < (after.completed_at, after.id)]
+        page = done[:limit]
+        return FeedPage(visits=page, next_cursor=str(page[-1].id) if len(done) > limit else None)
+
     async def list_occupied(self, ctx, start, end):
         return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id and v.is_active
                        and v.starts_at < end and v.ends_at > start), key=lambda v: (v.starts_at, v.id))
```

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```diff
@@ -4,6 +4,7 @@ from hub.app.ports.media_library_port import MediaLibraryPort
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
@@ -26,6 +27,6 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     assert isinstance(FakeLibrary(), MediaLibraryPort)
     visits = FakeVisits()
     for port in (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
-                 VisitBoardRepository):
+                 VisitBoardRepository, VisitFeedRepository):
         assert isinstance(visits, port), port.__name__
     assert isinstance(FakeRecords(visits), VisitRecordRepository)
```

`backend/tests/integration/test_visit_record_wiring.py`:

```diff
@@ -69,6 +69,7 @@ async def test_다른_매장의_방문과_미디어로는_기록을_쓸_수_없
 
     assert error_of(await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_visit}/record", json={}, headers=a)) == (
         403, "NOT_A_MEMBER")
+    assert error_of(await wired.api.get(f"/v1/shops/{b_shop}/visits/feed", headers=a)) == (403, "NOT_A_MEMBER")
     assert error_of(await wired.api.put(f"/v1/shops/{a_shop}/visits/{b_visit}/record", json={}, headers=a)) == (
         404, "VISIT_NOT_FOUND")
     theirs = await wired.api.put(f"/v1/shops/{a_shop}/visits/{a_visit}/record", headers=a,
@@ -142,7 +143,7 @@ async def test_덧붙이기는_기록을_만들고_다시_보내도_한_번이
     assert attached == 0
 
 
-async def test_상세_하루_달력이_기록과_대표_사진을_보여_준다(wired, media_storage):
+async def test_상세_하루_달력_피드가_기록과_대표_사진을_보여_준다(wired, media_storage):
     shop_id, o, _ = await _shop(wired)
     customer_id, pet_id = await _family(wired, shop_id, o)
     visit_id = await _visit(wired, shop_id, o, customer_id, pet_id)
@@ -163,3 +164,6 @@ async def test_상세_하루_달력이_기록과_대표_사진을_보여_준다(
     calendar = (await wired.api.get(f"/v1/shops/{shop_id}/visits/calendar?month={day[:7]}", headers=o)).json()
     that_day = next(d for d in calendar["days"] if d["date"] == day)
     assert (that_day["cover"], that_day["covers"]) == (after_thumb, [after_thumb])
+    feed = (await wired.api.get(f"/v1/shops/{shop_id}/visits/feed?pet_id={pet_id}", headers=o)).json()
+    assert [(i["visit_id"], i["cover"], i["care_note"], i["media_count"]) for i in feed["items"]] == [
+        (visit_id, after_thumb, "눈물 자국 관리", 2)]
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit tests/integration/test_visit_record_wiring.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 4개 — `ModuleNotFoundError: No module named 'visit.app.ports.output.visit_feed_repository'`(`list_visit_feed_dto`·라우터).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/ports/output/visit_feed_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


@dataclass(frozen=True)
class FeedPage:
    visits: list[Visit]
    next_cursor: str | None   # 없으면 마지막 쪽이다


class VisitFeedRepository(ABC):
    """완료 방문을 완료 시각 역순으로 이어 읽는다(피드). 모든 메서드가 ShopContext 의 매장으로 거른다.

    방문 리포지토리의 여섯째 축 — 하루·달력(게시판)은 시작 시각 범위로, 피드는 완료 시각 순서로 읽는다.
    """

    @abstractmethod
    async def list_completed(
        self, ctx: ShopContext, cursor: str | None, limit: int, pet_id: int | None
    ) -> FeedPage:
        """완료 시각, 같으면 방문 ID 역순. pet_id 가 있으면 그 아이의 방문만. 커서가 틀리면 VisitInputError."""
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`:

```diff
@@ -1,9 +1,12 @@
 from __future__ import annotations
 
+import base64
+import binascii
+import json
 from contextlib import asynccontextmanager
 from datetime import datetime, timedelta
 
-from sqlalchemy import delete, func, insert, select, update
+from sqlalchemy import delete, func, insert, select, tuple_, update
 from sqlalchemy.exc import IntegrityError
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -11,11 +14,12 @@ from hub.app.dtos.shop_context import ShopContext
 from visit.adapter.outbound.mappers.visit_mapper import to_visit
 from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_feed_repository import FeedPage, VisitFeedRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.domain.entities.visit import ACTIVE_STATUSES, COMPLETED, NO_SHOW, RESERVED, Visit
-from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
+from visit.domain.errors import VisitDuplicateError, VisitInputError, VisitNotFoundError
 from visit.domain.services.visit_schedule import MAX_DURATION
 from visit.domain.state.visit_state import StatusChange
 from visit.domain.state.visit_status import STARTED_STATUSES
@@ -24,8 +28,26 @@ from visit.domain.value_objects.new_visit import NewVisit
 _DUPLICATE = {"uq_visits_pet_start_active", "uq_visits_customer_start_active"}
 
 
-class VisitPgRepository(VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository):
-    """visits 표 하나를 다섯 포트로 내놓는다 — 유스케이스는 자기가 쓰는 포트만 받는다(ISP)."""
+def _encode_feed_cursor(completed_at: datetime, visit_id: int) -> str:
+    raw = json.dumps([completed_at.isoformat(), visit_id]).encode()
+    return base64.urlsafe_b64encode(raw).decode().rstrip("=")
+
+
+def _decode_feed_cursor(cursor: str) -> tuple[datetime, int]:
+    try:
+        completed_at, visit_id = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
+        moment = datetime.fromisoformat(completed_at)
+        if moment.tzinfo is None or type(visit_id) is not int or not 1 <= visit_id <= 2**63 - 1:
+            raise ValueError
+        return moment, visit_id
+    except (ValueError, TypeError, OverflowError, binascii.Error, UnicodeDecodeError):
+        raise VisitInputError("목록 위치(cursor)가 올바르지 않습니다.") from None
+
+
+class VisitPgRepository(
+    VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository, VisitFeedRepository,
+):
+    """visits 표 하나를 여섯 포트로 내놓는다 — 유스케이스는 자기가 쓰는 포트만 받는다(ISP)."""
 
     def __init__(self, session: AsyncSession) -> None:
         self._session = session
@@ -257,6 +279,26 @@ class VisitPgRepository(VisitWriteRepository, VisitHistoryRepository, VisitLedge
         )
         return [v for v in rows if v.ends_at > start]
 
+    async def list_completed(
+        self, ctx: ShopContext, cursor: str | None, limit: int, pet_id: int | None
+    ) -> FeedPage:
+        stmt = select(VisitOrm.id, VisitOrm.completed_at).where(
+            VisitOrm.shop_id == ctx.shop_id, VisitOrm.status == COMPLETED
+        )
+        if pet_id is not None:
+            stmt = stmt.where(VisitOrm.pet_id == pet_id)
+        if cursor is not None:
+            stmt = stmt.where(tuple_(VisitOrm.completed_at, VisitOrm.id) < tuple_(*_decode_feed_cursor(cursor)))
+        rows = (
+            await self._session.execute(
+                stmt.order_by(VisitOrm.completed_at.desc(), VisitOrm.id.desc()).limit(limit + 1)
+            )
+        ).all()
+        page = rows[:limit]
+        found = {v.id: v for v in await self.get_many(ctx, [visit_id for visit_id, _ in page])}
+        next_cursor = _encode_feed_cursor(page[-1][1], page[-1][0]) if len(rows) > limit else None
+        return FeedPage(visits=[found[visit_id] for visit_id, _ in page], next_cursor=next_cursor)
+
     async def _read(self, ctx: ShopContext, stmt) -> list[Visit]:
         rows = (
             await self._session.execute(
```

`backend/apps/visit/adapter/inbound/api/schemas/list_visit_feed_schema.py`:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import CustomerBriefSchema, PetBriefSchema
from visit.app.dtos.list_visit_feed_dto import VisitFeedView


class FeedItemSchema(BaseModel):
    visit_id: int
    customer: CustomerBriefSchema
    pet: PetBriefSchema | None
    completed_at: datetime      # 매장 시간대
    cover: str | None           # 대표 사진 썸네일 URL — 없으면 회색 자리
    menus: list[str]            # 기록의 실제 메뉴, 없으면 예약 메뉴
    care_note: str | None       # 앞 80자
    media_count: int


class VisitFeedSchema(BaseModel):
    items: list[FeedItemSchema]
    next_cursor: str | None     # 없으면 마지막 쪽

    @classmethod
    def of(cls, view: VisitFeedView) -> VisitFeedSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/v1/list_visit_feed_router.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_visit_feed_schema import VisitFeedSchema
from visit.app.dtos.list_visit_feed_dto import ListVisitFeedQuery
from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
from visit.dependencies.list_visit_feed_provider import get_list_visit_feed_use_case

list_visit_feed_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_visit_feed_router.get("/{shop_id}/visits/feed", response_model=VisitFeedSchema)
async def list_visit_feed(
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    pet_id: Annotated[int | None, Query(ge=1, le=9_223_372_036_854_775_807)] = None,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListVisitFeedUseCase = Depends(get_list_visit_feed_use_case),
) -> VisitFeedSchema:
    view = await use_case.list_visit_feed(ListVisitFeedQuery(ctx=ctx, cursor=cursor, limit=limit, pet_id=pet_id))
    return VisitFeedSchema.of(view)
```

`backend/apps/visit/app/dtos/list_visit_feed_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import CustomerBriefView, PetBriefView


@dataclass(frozen=True)
class ListVisitFeedQuery:
    ctx: ShopContext
    cursor: str | None
    limit: int
    pet_id: int | None   # 있으면 그 아이의 기록만(반려동물 상세의 [기록] 탭)


@dataclass(frozen=True)
class FeedItemView:
    """피드 카드 하나 — 완료 방문. 사진 없는 완료 방문도 나온다(cover 가 None — 앱은 회색 자리)."""

    visit_id: int
    customer: CustomerBriefView
    pet: PetBriefView | None
    completed_at: datetime   # 매장 시간대
    cover: str | None
    menus: list[str]         # 기록의 실제 메뉴, 없으면 예약 메뉴
    care_note: str | None    # 앞 80자
    media_count: int


@dataclass(frozen=True)
class VisitFeedView:
    items: list[FeedItemView]
    next_cursor: str | None
```

`backend/apps/visit/app/ports/input/list_visit_feed_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_visit_feed_dto import ListVisitFeedQuery, VisitFeedView


class ListVisitFeedUseCase(ABC):
    @abstractmethod
    async def list_visit_feed(self, query: ListVisitFeedQuery) -> VisitFeedView: ...
```

`backend/apps/visit/app/use_cases/list_visit_feed_interactor.py`:

```python
from __future__ import annotations

from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.list_visit_feed_dto import FeedItemView, ListVisitFeedQuery, VisitFeedView
from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.cover_reader import cover_urls
from visit.app.services.visit_reader import describe_visits

CARE_NOTE_PREVIEW = 80


class ListVisitFeedInteractor(ListVisitFeedUseCase):
    """피드 — 완료 방문을 완료 시각 역순으로 이어 읽는다(설계 9절). 한 쪽을 읽는 데 질의 수가 방문 수와 상관없다."""

    def __init__(
        self, feed: VisitFeedRepository, records: VisitRecordRepository, menus: MenuRepository,
        directory: CustomerDirectoryPort, library: MediaLibraryPort,
    ) -> None:
        self._feed = feed
        self._records = records
        self._menus = menus
        self._directory = directory
        self._library = library

    async def list_visit_feed(self, query: ListVisitFeedQuery) -> VisitFeedView:
        ctx = query.ctx
        page = await self._feed.list_completed(ctx, query.cursor, query.limit, query.pet_id)
        views = await describe_visits(ctx, page.visits, self._directory, self._menus)
        records = await self._records.list_many(ctx, [v.id for v in page.visits])
        covers = await cover_urls(ctx, records, self._library)
        item_ids = sorted({i.menu_id for r in records.values() for i in r.items})
        names = {m.id: m.name for m in await self._menus.list_by_ids(ctx, item_ids)} if item_ids else {}
        zone = ZoneInfo(ctx.timezone)
        items = []
        for visit, view in zip(page.visits, views):
            record = records.get(visit.id)
            actual = [names[i.menu_id] for i in record.items] if record else []
            note = record.care_note if record else None
            items.append(FeedItemView(
                visit_id=visit.id, customer=view.customer, pet=view.pet,
                completed_at=visit.completed_at.astimezone(zone), cover=covers.get(visit.id),
                menus=actual or [m.name for m in view.menus],
                care_note=note[:CARE_NOTE_PREVIEW] if note else None,
                media_count=len(record.media) if record else 0,
            ))
        return VisitFeedView(items=items, next_cursor=page.next_cursor)
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -38,6 +38,8 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "DELETE /visits/{visit_id}/record 는 기록 삭제입니다(record:delete, 방문은 남습니다). "
                 "방문 상세는 record(기록 전체, 사진 URL 포함)와 cover(대표 사진 썸네일 — 후 → 전 → 영상 포스터), "
                 "하루 목록은 항목마다 has_record·cover, 달력은 날마다 완료 방문의 cover·covers(최대 4장)를 줍니다. "
+                "GET /visits/feed?cursor=&limit=&pet_id= 는 완료 방문을 완료 시각 역순으로 이어 읽는 피드입니다"
+                "(카드마다 보호자·아이 요약, cover, 메뉴, 케어 메모 앞 80자, 사진 수, next_cursor 로 다음 쪽). "
                 "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                 "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}(이름·기본 소요·순서·정가 price, "
                 "원 단위, 비우면 가격 미정), "
```

`backend/apps/visit/dependencies/list_visit_feed_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
from visit.app.use_cases.list_visit_feed_interactor import ListVisitFeedInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository


def get_list_visit_feed_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> ListVisitFeedUseCase:
    return ListVisitFeedInteractor(
        feed=build_visit_repository(db), records=build_record_repository(db), menus=build_menu_repository(db),
        directory=directory, library=library,
    )
```

`backend/main.py`:

```diff
@@ -77,6 +77,7 @@ from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_set
 from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
 from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
 from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
+from visit.adapter.inbound.api.v1.list_visit_feed_router import list_visit_feed_router
 from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
 from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
 from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
@@ -142,9 +143,10 @@ app.include_router(list_menus_router)
 app.include_router(create_menu_router)
 app.include_router(update_menu_router)
 app.include_router(archive_menu_router)
-# /visits/myself·calendar·slots·defaults 는 /visits/{visit_id} 보다 먼저 붙인다(정수 변환 실패 422 를 피한다).
+# /visits/myself·calendar·slots·defaults·feed 는 /visits/{visit_id} 보다 먼저 붙인다(정수 변환 실패 422 를 피한다).
 app.include_router(visit_myself_router)
 app.include_router(get_visit_calendar_router)
+app.include_router(list_visit_feed_router)
 app.include_router(list_visit_slots_router)
 app.include_router(get_visit_defaults_router)
 app.include_router(list_day_visits_router)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit tests/integration/test_visit_record_wiring.py tests/test_hub_port_binding.py -q -p no:cacheprovider` → 전부 통과

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 877 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 292 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `list_completed`의 `.order_by(VisitOrm.completed_at.desc(), VisitOrm.id.desc())`에서 `VisitOrm.id.desc()`를 뺀다 → `test_피드는_완료_시각_역순이고_커서로_이어_읽는다` 실패.
- 피드 인터랙터의 `menus=actual or [m.name for m in view.menus]`를 `menus=actual`로 → `test_완료_방문을_완료_시각_역순으로_카드로_준다` 실패.
- `care_note=note[:CARE_NOTE_PREVIEW] if note else None`을 `care_note=note`로 → 같은 테스트 실패.
- `_decode_feed_cursor`의 `moment.tzinfo is None or`를 뺀다 → `test_피드_커서가_틀리면_VisitInputError` 실패(시간대 없는 시각).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 피드 — GET /visits/feed(완료 시각 역순·커서·pet_id), 방문 리포지토리의 여섯째 축 VisitFeedRepository

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: 반려동물 프로필 사진과 익명화 — 사진이 붙은 가장 최근 완료 기록의 대표(`VisitLedgerPort.latest_covers`)를 목록·고객 상세·반려동물 상세에, 익명화는 기록의 두 메모도 비운다

**Files:**
- Modify: `backend/apps/hub/app/ports/visit_ledger_port.py`
- Modify: `backend/apps/visit/app/ports/output/visit_record_repository.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`
- Modify: `backend/apps/visit/app/use_cases/visit_ledger_interactor.py`
- Create: `backend/apps/customer/app/services/pet_photos.py`
- Modify: `backend/apps/customer/adapter/inbound/api/schemas/get_customer_schema.py`
- Modify: `backend/apps/customer/adapter/inbound/api/schemas/get_pet_schema.py`
- Modify: `backend/apps/customer/adapter/inbound/api/schemas/list_customers_schema.py`
- Modify: `backend/apps/customer/adapter/inbound/api/v1/get_pet_router.py`
- Modify: `backend/apps/customer/app/dtos/customer_view_dto.py`
- Modify: `backend/apps/customer/app/dtos/list_customers_dto.py`
- Modify: `backend/apps/customer/app/ports/input/get_pet_use_case.py`
- Modify: `backend/apps/customer/app/use_cases/customer_myself_interactor.py`
- Modify: `backend/apps/customer/app/use_cases/get_customer_interactor.py`
- Modify: `backend/apps/customer/app/use_cases/get_pet_interactor.py`
- Modify: `backend/apps/customer/app/use_cases/list_customers_interactor.py`
- Modify: `backend/apps/customer/dependencies/get_customer_provider.py`
- Modify: `backend/apps/customer/dependencies/get_pet_provider.py`
- Modify: `backend/apps/customer/dependencies/hub_ports.py`
- Modify: `backend/apps/customer/dependencies/list_customers_provider.py`
- Modify: `backend/apps/customer/tests/adapter/test_get_customer_router.py`
- Modify: `backend/apps/customer/tests/adapter/test_get_pet_router.py`
- Modify: `backend/apps/customer/tests/adapter/test_list_customers_router.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_customer_myself_interactor.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_get_customer_interactor.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_get_pet_interactor.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_list_customers_interactor.py`
- Modify: `backend/apps/customer/tests/helpers/fakes.py`
- Modify: `backend/apps/customer/tests/test_fakes_are_ports.py`
- Modify: `backend/apps/visit/dependencies/visit_ledger_provider.py`
- Modify: `backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_visit_ledger_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/integration/test_customer_locking.py`
- Modify: `backend/tests/integration/test_visit_locking.py`
- Modify: `backend/tests/integration/test_visit_record_wiring.py`

**Interfaces:**
- Consumes: 작업 4 의 `MediaLibraryPort`·`MediaUrls`·`get_media_library_use_case`, 작업 6~8 의 `VisitRecordRepository`·`cover_media_id`·`list_many`·`builders.record`, 기존 `VisitLedgerPort`·`VisitLedgerInteractor`·customer 조회 슬라이스 셋.
- Produces: `VisitLedgerPort.latest_covers(ctx, pet_ids) -> dict[int, int]`(`clear_customer_memos`는 기록 메모도 비운다); `VisitRecordRepository.latest_with_media(ctx, pet_ids) -> dict[int, int]`·`clear_notes(ctx, customer_id)`; `VisitLedgerInteractor(ledger, records, now)`; customer — 자리 `customer.dependencies.hub_ports.get_media_library`, `customer.app.services.pet_photos.pet_photos(ctx, pet_ids, ledger, library) -> dict[int, str]`, `PetSummaryView.photo`, `CustomerOverviewView.photos`, `PetOverviewView(detail, photo)`, `GetPetUseCase.get_pet -> PetOverviewView`; 생성자 `GetPetInteractor(customers, pets, ledger, library, today)`, `GetCustomerInteractor(customers, pets, ledger, library, today)`, `ListCustomersInteractor(customers, pets, search, ledger, library, today)`; 스키마 `PetWithPhotoSchema(PetSchema).with_photo(view, photo)`, `PetOverviewSchema(PetDetailSchema).of_overview(view)`, `PetSummarySchema.photo`; `main.py`는 두 자리를 별칭(`get_visit_media_library`·`get_customer_media_library`)으로 채운다; 스텁 `FakeLedger.covers`·`latest_covers`, customer `FakeLibrary`(읽기만).

고객 탭의 회색 자리를 프로필 사진으로 바꾼다(설계 8절 '프로필 사진', 6.4 익명화). 사진은 customer 에 복사하지 않고 읽을 때마다 두 허브 포트에 한 번씩 묻는다(N+1 없음). 프로필 사진은 사진이 붙은 가장 최근 **완료** 방문의 대표다 — 가장 최근 완료 기록에 사진이 없으면 그 전 것, 미용 중인 방문은 아직 아니다. **설계와 다른 점**(결정 기록 007): `photo`는 조회 응답 셋(목록 `pets[].photo`, 고객 상세 `pets[].photo`, 반려동물 상세 `pet.photo`)에만 있다 — 쓰기 응답은 그대로이고 앱은 쓰기 뒤 다시 읽는다(③ 규칙). 익명화는 방문 메모에 더해 기록의 케어·내부 메모를 비우고 사진은 남긴다(M16). 잠금 통합 테스트 둘이 `VisitLedgerInteractor`를 만들므로 새 인자를 더한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/adapter/test_get_customer_router.py`:

```diff
@@ -32,6 +32,7 @@ class _StubUseCase:
         return CustomerOverviewView(
             customer=detail.customer, pets=detail.pets, no_show_count=2,
             upcoming_visits=[UpcomingVisitView(visit_id=7, pet_id=101, pet_name="콩이", starts_at=NOW)],
+            photos={101: "t/51"},
         )
 
 
@@ -49,6 +50,7 @@ async def test_멤버는_전체_번호가_든_고객_상세를_본다():
     assert response.json()["no_show_count"] == 2
     assert response.json()["upcoming_visits"] == [
         {"visit_id": 7, "pet_id": 101, "pet_name": "콩이", "starts_at": "2026-09-22T01:00:00Z"}]
+    assert [(p["pet_id"], p["photo"]) for p in response.json()["pets"]] == [(101, "t/51")]
     assert (stub.queries[0].ctx.shop_id, stub.queries[0].customer_id) == (3, 1)
```

`backend/apps/customer/tests/adapter/test_get_pet_router.py`:

```diff
@@ -2,6 +2,7 @@ from httpx import ASGITransport, AsyncClient
 
 from customer.adapter.inbound.api.v1.get_pet_router import get_pet_router
 from customer.dependencies.get_pet_provider import get_get_pet_use_case
+from customer.app.dtos.customer_view_dto import PetOverviewView
 from customer.tests.helpers.api import NO_WRITE, build_app, pet_detail_view
 
 
@@ -11,7 +12,7 @@ class _StubUseCase:
 
     async def get_pet(self, query):
         self.queries.append(query)
-        return pet_detail_view()
+        return PetOverviewView(detail=pet_detail_view(), photo="t/51")
 
 
 async def test_멤버는_반려동물_상세를_보고_보호자_번호는_가려져_있다():
@@ -21,4 +22,5 @@ async def test_멤버는_반려동물_상세를_보고_보호자_번호는_가
         response = await client.get("/v1/shops/3/pets/101")
     assert response.status_code == 200
     assert response.json()["owner"] == {"customer_id": 1, "name": "김민지", "phone_masked": "010-12··-5678"}
+    assert (response.json()["pet"]["pet_id"], response.json()["pet"]["photo"]) == (101, "t/51")
     assert (stub.queries[0].ctx.shop_id, stub.queries[0].pet_id) == (3, 101)
```

`backend/apps/customer/tests/adapter/test_list_customers_router.py`:

```diff
@@ -13,7 +13,7 @@ class _StubUseCase:
     async def list_customers(self, query):
         self.queries.append(query)
         pet = PetSummaryView(pet_id=101, name="콩이", species="dog", breed="말티즈", age_label="5살",
-                             has_conditions=True, passed_away=False)
+                             has_conditions=True, passed_away=False, photo="t/51")
         card = FamilyCardView(customer_id=1, name="김민지", phone_masked="010-12··-5678", pets=[pet])
         return CustomerListView(items=[card], next_cursor="next", pet_count=1)
 
@@ -32,6 +32,7 @@ async def test_멤버는_기본값으로_목록을_본다():
     assert (body["pet_count"], body["next_cursor"]) == (1, "next")
     assert body["items"][0]["phone_masked"] == "010-12··-5678"
     assert "phone" not in body["items"][0]   # 목록에는 전체 번호 칸이 없다
+    assert body["items"][0]["pets"][0]["photo"] == "t/51"
     query = stub.queries[0]
     assert (query.q, query.sort, query.include_passed, query.cursor) == (None, "recent", False, None)
```

`backend/apps/customer/tests/app/use_cases/test_customer_myself_interactor.py`:

```diff
@@ -20,4 +20,5 @@ async def test_자기소개는_실제_엔드포인트와_제약을_말하고_기
                  "/pets/{pet_id}/passed-away", "/pet-condition-types"):
         assert path in result.introduction
     assert "customer:delete" in result.introduction and "익명화" in result.introduction
+    assert "photo" in result.introduction and "미용 기록의 두 메모" in result.introduction
     assert record.records[0][0] == "introduce_myself"
```

`backend/apps/customer/tests/app/use_cases/test_get_customer_interactor.py`:

```diff
@@ -5,7 +5,7 @@ import pytest
 from customer.app.dtos.get_customer_dto import GetCustomerQuery
 from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
 from customer.domain.errors import CustomerNotFoundError
-from customer.tests.helpers.fakes import FakeLedger, family, today
+from customer.tests.helpers.fakes import FakeLedger, FakeLibrary, family, today
 from customer.tests.helpers.profiles import ctx
 from hub.app.dtos.upcoming_visit import UpcomingVisit
 
@@ -15,12 +15,12 @@ async def test_보호자_전체와_반려동물_전체를_돌려준다():
     customer = customers.seed()
     pets.seed(customer.id, "콩이")
     pets.seed(customer.id, "별이", passed_away=True)
-    view = await GetCustomerInteractor(customers, pets, FakeLedger(journal), today).get_customer(
+    view = await GetCustomerInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_customer(
         GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
     )
     assert view.customer.phone == "01012345678"   # 상세는 전체 번호다
     assert [(p.name, p.passed_away_at is not None) for p in view.pets] == [("콩이", False), ("별이", True)]
-    assert (view.no_show_count, view.upcoming_visits) == (0, [])
+    assert (view.no_show_count, view.upcoming_visits, view.photos) == (0, [], {})
 
 
 async def test_노쇼_횟수와_다가오는_예약을_아이_이름과_함께_매장_시간대로():
@@ -33,7 +33,7 @@ async def test_노쇼_횟수와_다가오는_예약을_아이_이름과_함께_
         UpcomingVisit(visit_id=7, pet_id=kong.id, starts_at=datetime(2026, 10, 2, 5, tzinfo=timezone.utc)),
         UpcomingVisit(visit_id=8, pet_id=None, starts_at=datetime(2026, 10, 3, 5, tzinfo=timezone.utc)),
     ]
-    view = await GetCustomerInteractor(customers, pets, ledger, today).get_customer(
+    view = await GetCustomerInteractor(customers, pets, ledger, FakeLibrary(), today).get_customer(
         GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
     )
     assert view.no_show_count == 2
@@ -45,6 +45,19 @@ async def test_다른_매장의_고객은_404_다():
     journal, customers, pets, _, _ = family()
     customer = customers.seed(shop_id=2)
     with pytest.raises(CustomerNotFoundError):
-        await GetCustomerInteractor(customers, pets, FakeLedger(journal), today).get_customer(
+        await GetCustomerInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_customer(
             GetCustomerQuery(ctx=ctx(shop_id=1), customer_id=customer.id)
         )
+
+
+async def test_반려동물마다_프로필_사진을_한_번에_묻는다():
+    journal, customers, pets, _, _ = family()
+    customer = customers.seed()
+    kong, byeol = pets.seed(customer.id, "콩이"), pets.seed(customer.id, "별이")
+    ledger, library = FakeLedger(journal), FakeLibrary()
+    ledger.covers = {kong.id: 51, byeol.id: 52}
+    library.ready = {51}   # 52 는 URL 을 줄 수 없다(정리됐다) — 빠진다
+    view = await GetCustomerInteractor(customers, pets, ledger, library, today).get_customer(
+        GetCustomerQuery(ctx=ctx(), customer_id=customer.id))
+    assert view.photos == {kong.id: "t/51"}
+    assert journal.count(("latest_covers", sorted([kong.id, byeol.id]))) == 1
```

`backend/apps/customer/tests/app/use_cases/test_get_pet_interactor.py`:

```diff
@@ -3,23 +3,34 @@ import pytest
 from customer.app.dtos.get_pet_dto import GetPetQuery
 from customer.app.use_cases.get_pet_interactor import GetPetInteractor
 from customer.domain.errors import PetNotFoundError
-from customer.tests.helpers.fakes import family, today
+from customer.tests.helpers.fakes import FakeLedger, FakeLibrary, family, today
 from customer.tests.helpers.profiles import ctx
 
 
 async def test_반려동물과_보호자_요약과_같은_보호자의_다른_아이를_돌려준다():
-    _, customers, pets, _, _ = family()
+    journal, customers, pets, _, _ = family()
     customer = customers.seed()
     kong = pets.seed(customer.id, "콩이")
     pets.seed(customer.id, "별이", passed_away=True)
-    view = await GetPetInteractor(customers, pets, today).get_pet(GetPetQuery(ctx=ctx(), pet_id=kong.id))
-    assert view.pet.name == "콩이"
-    assert (view.owner.name, view.owner.phone_masked) == ("김민지", "010-12··-5678")
-    assert [(s.name, s.passed_away) for s in view.siblings] == [("별이", True)]
+    view = await GetPetInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_pet(
+        GetPetQuery(ctx=ctx(), pet_id=kong.id))
+    assert (view.detail.pet.name, view.photo) == ("콩이", None)
+    assert (view.detail.owner.name, view.detail.owner.phone_masked) == ("김민지", "010-12··-5678")
+    assert [(s.name, s.passed_away) for s in view.detail.siblings] == [("별이", True)]
 
 
 async def test_다른_매장의_반려동물은_404_다():
-    _, customers, pets, _, _ = family()
+    journal, customers, pets, _, _ = family()
     pet = pets.seed(customers.seed(shop_id=2).id)
     with pytest.raises(PetNotFoundError):
-        await GetPetInteractor(customers, pets, today).get_pet(GetPetQuery(ctx=ctx(shop_id=1), pet_id=pet.id))
+        await GetPetInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_pet(
+            GetPetQuery(ctx=ctx(shop_id=1), pet_id=pet.id))
+
+
+async def test_가장_최근_완료_기록의_대표_사진이_프로필_사진이다():
+    journal, customers, pets, _, _ = family()
+    kong = pets.seed(customers.seed().id, "콩이")
+    ledger, library = FakeLedger(journal), FakeLibrary()
+    ledger.covers, library.ready = {kong.id: 51}, {51}
+    view = await GetPetInteractor(customers, pets, ledger, library, today).get_pet(GetPetQuery(ctx=ctx(), pet_id=kong.id))
+    assert view.photo == "t/51"
```

`backend/apps/customer/tests/app/use_cases/test_list_customers_interactor.py`:

```diff
@@ -3,7 +3,7 @@ from customer.app.dtos.list_customers_dto import ListCustomersQuery
 from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
 from customer.domain.entities.pet import PetCondition
 from customer.domain.services.search_terms import SearchWord
-from customer.tests.helpers.fakes import FakeSearch, family, today
+from customer.tests.helpers.fakes import FakeLedger, FakeLibrary, FakeSearch, family, today
 from customer.tests.helpers.profiles import ctx
 
 
@@ -21,7 +21,7 @@ def _setup():
     pets.seed(kim.id, "별이", passed_away=True)
     pets.seed(park.id, "보리")
     search = FakeSearch(journal, SearchPage(customer_ids=[park.id, kim.id], next_cursor="next"), pet_count=2)
-    return kim, park, search, ListCustomersInteractor(customers, pets, search, today)
+    return kim, park, search, ListCustomersInteractor(customers, pets, search, FakeLedger(journal), FakeLibrary(), today)
 
 
 async def test_검색_순서대로_가족_카드를_만들고_번호는_가린다():
@@ -49,5 +49,18 @@ async def test_검색_줄에_있어도_원본에_없는_가족은_빼고_원본
     kim = customers.seed()
     pets.seed(kim.id)
     search = FakeSearch(journal, SearchPage(customer_ids=[999, kim.id], next_cursor=None))
-    view = await ListCustomersInteractor(customers, pets, search, today).list_customers(_query())
+    view = await ListCustomersInteractor(customers, pets, search, FakeLedger(journal), FakeLibrary(),
+                                         today).list_customers(_query())
     assert [c.customer_id for c in view.items] == [kim.id]
+
+
+async def test_반려동물_줄마다_프로필_사진을_페이지_한_번에_묻는다():
+    journal, customers, pets, _, _ = family()
+    kim, park = customers.seed(), customers.seed(name="박서준", phone="0212345678")
+    kong, bori = pets.seed(kim.id, "콩이"), pets.seed(park.id, "보리")
+    ledger, library = FakeLedger(journal), FakeLibrary()
+    ledger.covers, library.ready = {kong.id: 51}, {51}
+    search = FakeSearch(journal, SearchPage(customer_ids=[kim.id, park.id], next_cursor=None))
+    view = await ListCustomersInteractor(customers, pets, search, ledger, library, today).list_customers(_query())
+    assert [(p.name, p.photo) for c in view.items for p in c.pets] == [("콩이", "t/51"), ("보리", None)]
+    assert [e for e in journal if e[0] == "latest_covers"] == [("latest_covers", sorted([kong.id, bori.id]))]
```

`backend/apps/customer/tests/helpers/fakes.py`:

```diff
@@ -18,6 +18,8 @@ from customer.domain.entities.condition_type import ConditionType
 from customer.domain.entities.customer import Customer
 from customer.domain.entities.pet import Pet, PetCondition
 from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError, PetNotFoundError
+from hub.app.dtos.media_urls import MediaUrls
+from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 TODAY = date(2026, 9, 22)
@@ -212,6 +214,7 @@ class FakeLedger(VisitLedgerPort):
         self.customers_with_upcoming: set[int] = set()
         self.no_shows: dict[int, int] = {}
         self.upcoming: dict[int, list] = {}
+        self.covers: dict[int, int] = {}   # 반려동물 ID → 대표 사진 media_id
 
     async def pet_has_visits(self, ctx, pet_id):
         return pet_id in self.pets_with_visits | self.pets_with_upcoming
@@ -231,6 +234,27 @@ class FakeLedger(VisitLedgerPort):
     async def clear_customer_memos(self, ctx, customer_id):
         self.journal.append(("clear_visit_memos", customer_id))
 
+    async def latest_covers(self, ctx, pet_ids):
+        self.journal.append(("latest_covers", sorted(pet_ids)))
+        return {p: self.covers[p] for p in pet_ids if p in self.covers}
+
+
+class FakeLibrary(MediaLibraryPort):
+    """MediaLibraryPort 스텁 — customer 는 읽기 URL 만 쓴다. ready 는 URL 을 줄 수 있는 media_id 들이다."""
+
+    def __init__(self) -> None:
+        self.ready: set[int] = set()
+
+    async def claim(self, ctx, media_ids):
+        raise AssertionError("customer 는 미디어를 가져가지 않는다")
+
+    async def release(self, ctx, media_ids):
+        raise AssertionError("customer 는 미디어를 놓지 않는다")
+
+    async def read_urls(self, ctx, media_ids):
+        return {i: MediaUrls(media_id=i, kind="photo", original_url=f"o/{i}", display_url=f"d/{i}", thumb_url=f"t/{i}",
+                             width=3000, height=2000, duration_seconds=None) for i in media_ids if i in self.ready}
+
 
 def family():
     """스텁 한 벌을 같은 호출 기록으로 묶어 만든다."""
```

`backend/apps/customer/tests/test_fakes_are_ports.py`:

```diff
@@ -7,10 +7,12 @@ from customer.tests.helpers.fakes import (
     FakeConditionTypes,
     FakeCustomers,
     FakeLedger,
+    FakeLibrary,
     FakePets,
     FakeSearch,
     Journal,
 )
+from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
@@ -22,3 +24,4 @@ def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않
     assert isinstance(FakePets(journal, customers), PetRepository)
     assert isinstance(FakeSearch(journal), CustomerSearchPort)
     assert isinstance(FakeLedger(journal), VisitLedgerPort)
+    assert isinstance(FakeLibrary(), MediaLibraryPort)
```

`backend/apps/visit/tests/adapter/test_visit_record_pg_repository.py`:

```diff
@@ -76,3 +76,28 @@ async def test_기록이_있는_방문마다_기록_전체를_한_번에_읽는
         (RecordMedia(8, "photo", "before", 0), RecordMedia(7, "photo", "after", 0)), (RecordItem(bath, 1),), ())
     assert await repo.list_many(B, [visit_id]) == {}
     assert await repo.list_many(A, []) == {}
+
+
+async def test_사진이_붙은_가장_최근_완료_방문을_아이마다_한_번에(db_session):
+    repo, _, _, _ = await _setup(db_session)
+    old = await insert_visit(db_session, kst(9, 1, 14), "completed")
+    latest = await insert_visit(db_session, kst(9, 10, 14), "completed")
+    no_photo = await insert_visit(db_session, kst(9, 20, 14), "completed")
+    working = await insert_visit(db_session, kst(9, 22, 14), "in_progress")
+    theirs = await insert_visit(db_session, kst(9, 21, 14), "completed", shop_id=2)
+    other_pet = await insert_visit(db_session, kst(9, 5, 14), "completed", pet_id=102)
+    for visit_id, media_id in ((old, 1), (latest, 2), (working, 3), (theirs, 4), (other_pet, 5)):
+        await repo.save(A, _record(visit_id, media=[RecordMedia(media_id, "photo", "after", 0)]))
+    await repo.save(A, _record(no_photo))
+    assert await repo.latest_with_media(A, [101, 102, 103]) == {101: latest, 102: other_pet}
+    assert await repo.latest_with_media(A, []) == {}
+
+
+async def test_익명화는_그_보호자의_기록_메모만_비운다(db_session):
+    repo, visit_id, _, _ = await _setup(db_session)
+    other = await insert_visit(db_session, kst(9, 24, 14), "in_progress", customer_id=2)
+    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))
+    await repo.save(A, _record(other))
+    await repo.clear_notes(A, 1)
+    cleared, kept = await repo.get(A, visit_id), await repo.get(A, other)
+    assert (cleared.care_note, cleared.internal_note, len(cleared.media), kept.care_note) == (None, None, 1, "케어")
```

`backend/apps/visit/tests/app/use_cases/test_visit_ledger_interactor.py`:

```diff
@@ -1,13 +1,19 @@
 from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
-from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeVisits
+from visit.tests.helpers.builders import ctx, kst, record
+from visit.tests.helpers.fakes import FakeRecords, FakeVisits
 
 NOW = kst(9, 23, 15)
 
 
 def _ledger():
     visits = FakeVisits()
-    return visits, VisitLedgerInteractor(visits, now=lambda: NOW)
+    return visits, VisitLedgerInteractor(visits, FakeRecords(visits), now=lambda: NOW)
+
+
+def _with_records():
+    visits = FakeVisits()
+    records = FakeRecords(visits)
+    return visits, records, VisitLedgerInteractor(visits, records, now=lambda: NOW)
 
 
 async def test_반려동물의_방문과_앞으로의_예약():
@@ -44,3 +50,32 @@ async def test_메모를_비운다():
     other = visits.seed(customer_id=2, memo="남의 메모")
     await ledger.clear_customer_memos(ctx(), 1)
     assert (visits.rows[mine.id].memo, visits.rows[other.id].memo) == (None, "남의 메모")
+
+
+async def test_익명화는_방문_메모와_기록의_두_메모를_비우고_사진은_남긴다():
+    visits, records, ledger = _with_records()
+    mine = visits.seed(customer_id=1, memo="010-1234-5678 로 연락", status="completed", started_at=kst(9, 2, 10),
+                       completed_at=kst(9, 2, 12))
+    other = visits.seed(customer_id=2, status="completed", started_at=kst(9, 2, 10), completed_at=kst(9, 2, 12))
+    records.seed(record(mine.id, media=((51, "photo", "after", 0),), care_note="보호자 이름", internal_note="번호"))
+    records.seed(record(other.id, care_note="남의 기록"))
+    await ledger.clear_customer_memos(ctx(), 1)
+    kept = records.rows[mine.id]
+    assert (visits.rows[mine.id].memo, kept.care_note, kept.internal_note, len(kept.media)) == (None, None, None, 1)
+    assert records.rows[other.id].care_note == "남의 기록"
+
+
+async def test_반려동물마다_사진이_붙은_가장_최근_완료_방문의_대표():
+    visits, records, ledger = _with_records()
+    done = dict(status="completed", started_at=kst(9, 1, 10), completed_at=kst(9, 1, 12))
+    old = visits.seed(pet_id=101, starts_at=kst(9, 1, 10), **done)
+    latest = visits.seed(pet_id=101, starts_at=kst(9, 10, 10), **done)
+    newest_no_photo = visits.seed(pet_id=101, starts_at=kst(9, 20, 10), **done)
+    working = visits.seed(pet_id=101, starts_at=kst(9, 23, 10), status="in_progress", started_at=kst(9, 23, 10))
+    only_video = visits.seed(pet_id=102, starts_at=kst(9, 5, 10), **done)
+    records.seed(record(old.id, media=((51, "photo", "after", 0),)))
+    records.seed(record(latest.id, media=((52, "photo", "before", 0), (53, "photo", "after", 0))))
+    records.seed(record(newest_no_photo.id, care_note="사진 없음"))
+    records.seed(record(working.id, media=((54, "photo", "after", 0),)))
+    records.seed(record(only_video.id, media=((61, "video", "after", 0),)))
+    assert await ledger.latest_covers(ctx(), [101, 102, 103]) == {101: 53, 102: 61}
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -363,6 +363,21 @@ class FakeRecords(VisitRecordRepository):
     async def list_many(self, ctx, visit_ids):
         return {i: self.rows[i] for i in visit_ids if i in self.rows and self.visits.rows[i].shop_id == ctx.shop_id}
 
+    async def latest_with_media(self, ctx, pet_ids):
+        found = {}
+        for visit in sorted(self.visits._mine(ctx), key=lambda v: (v.starts_at, v.id)):
+            if visit.pet_id in pet_ids and visit.status == "completed" and visit.id in self.rows \
+                    and self.rows[visit.id].media:
+                found[visit.pet_id] = visit.id
+        return found
+
+    async def clear_notes(self, ctx, customer_id):
+        for visit_id, record in self.rows.items():
+            visit = self.visits.rows[visit_id]
+            if visit.shop_id == ctx.shop_id and visit.customer_id == customer_id:
+                self.rows[visit_id] = replace(record, care_note=None, internal_note=None)
+        self.journal.append(("clear_record_notes", customer_id))
+
     async def save(self, ctx, record):
         self.rows[record.visit_id] = record
         self.journal.append(("save_record", record.visit_id, record.version))
```

`backend/tests/integration/test_customer_locking.py`:

```diff
@@ -27,6 +27,7 @@ from customer.tests.helpers.fakes import today
 from customer.tests.helpers.inputs import customer_input, pet_input
 from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
+from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
 from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
 from visit.domain.services.visit_schedule import utc_now
 
@@ -43,7 +44,7 @@ def _repos(session):
 
 def _ledger(session):
     """customer 유스케이스가 묻는 방문 장부 — 진입점이 꽂는 것과 같은 실제 구현(visit)."""
-    return VisitLedgerInteractor(VisitPgRepository(session), now=utc_now)
+    return VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session), now=utc_now)
 
 
 def _register(session, name):
```

`backend/tests/integration/test_visit_locking.py`:

```diff
@@ -22,6 +22,7 @@ from hub.app.errors import FamilyNotFoundError
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
+from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
 from visit.app.dtos.register_visit_dto import RegisterVisitCommand
 from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
 from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
@@ -67,7 +68,7 @@ def _transition(session, visit_ids, action, reason=None):
 
 
 def _anonymize(session, customer_id):
-    ledger = VisitLedgerInteractor(VisitPgRepository(session), now=lambda: NOW)
+    ledger = VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session), now=lambda: NOW)
     return DeleteCustomerInteractor(CustomerPgRepository(session), CustomerSearchPgAdapter(session), ledger) \
         .delete_customer(DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id))
```

`backend/tests/integration/test_visit_record_wiring.py`:

```diff
@@ -167,3 +167,28 @@ async def test_상세_하루_달력_피드가_기록과_대표_사진을_보여_
     feed = (await wired.api.get(f"/v1/shops/{shop_id}/visits/feed?pet_id={pet_id}", headers=o)).json()
     assert [(i["visit_id"], i["cover"], i["care_note"], i["media_count"]) for i in feed["items"]] == [
         (visit_id, after_thumb, "눈물 자국 관리", 2)]
+
+
+async def test_프로필_사진은_최근_완료_기록의_대표이고_익명화하면_기록_메모만_비운다(wired, media_storage):
+    shop_id, o, _ = await _shop(wired)
+    customer_id, pet_id = await _family(wired, shop_id, o)
+    visit_id = await _visit(wired, shop_id, o, customer_id, pet_id)
+    photo = await ready_photo(wired, shop_id, o)
+    await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=o, json={
+        "care_note": "보호자 010-1234-5678", "internal_note": "김민지 님",
+        "media": [{"media_id": photo, "phase": "after", "sort_order": 0}]})
+    no_photo_yet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=o)).json()["pet"]["photo"]
+    await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o,
+                         json={"visit_ids": [visit_id], "action": "complete"})
+
+    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=o)).json()["pet"]
+    customer = (await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).json()
+    listed = (await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=o)).json()
+    assert no_photo_yet is None   # 미용 중인 방문은 아직 프로필이 아니다
+    assert pet["photo"] and pet["photo"] == customer["pets"][0]["photo"] == listed["items"][0]["pets"][0]["photo"]
+
+    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204
+    async with wired.engine.connect() as conn:
+        notes = (await conn.execute(text("SELECT care_note, internal_note FROM visit_records"))).one()
+        attached = (await conn.execute(text("SELECT attached_at IS NOT NULL FROM media_objects"))).scalar()
+    assert (tuple(notes), attached) == ((None, None), True)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit apps/customer tests/integration/test_visit_record_wiring.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 — `ImportError: cannot import name 'PetOverviewView' from 'customer.app.dtos.customer_view_dto'`.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/ports/visit_ledger_port.py`:

```diff
@@ -7,7 +7,7 @@ from hub.app.dtos.upcoming_visit import UpcomingVisit
 
 
 class VisitLedgerPort(ABC):
-    """구현: visit. 사용: customer (반려동물 삭제·무지개다리·고객 익명화의 규칙, 고객 상세).
+    """구현: visit. 사용: customer (반려동물 삭제·무지개다리·고객 익명화의 규칙, 고객 상세, 반려동물 프로필 사진).
 
     '앞으로의 예약'은 예약됨·미용 중인 방문이다 — 날짜가 지났어도 정리하지 않았으면 여기에 든다.
     customer 는 고객 행을 잠근 **뒤에** 부른다(잠금 순서: 고객 행 → 방문 행). 방문을 쓰는 visit 유스케이스도
@@ -33,4 +33,10 @@ class VisitLedgerPort(ABC):
 
     @abstractmethod
     async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
-        """그 고객 방문들의 메모를 비운다 — 익명화 때 방문 메모에 남은 개인정보를 지운다(V11)."""
+        """그 고객 방문들의 메모와 미용 기록의 두 메모(케어·내부)를 비운다 — 익명화 때 메모에 남은 개인정보를
+        지운다(V11, 설계 6.4). 사진은 매장의 미용 기록이라 남긴다."""
+
+    @abstractmethod
+    async def latest_covers(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
+        """{반려동물 ID: 대표 사진의 media_id} — 사진·영상이 붙은 가장 최근 완료 방문의 대표(후 → 전 → 영상).
+        그런 방문이 없는 아이는 빠진다. 반려동물 프로필 사진의 원본이다(설계 8절). 한 번에 묻는다(N+1 없음)."""
```

`backend/apps/visit/app/ports/output/visit_record_repository.py`:

```diff
@@ -21,6 +21,14 @@ class VisitRecordRepository(ABC):
         """기록이 있는 방문마다 기록 전체. 기록이 없는 방문은 키가 없다 — 상세·목록·달력의 '기록 있음'과
         대표 사진을 방문 수와 상관없이 한 번에 읽는다."""
 
+    @abstractmethod
+    async def latest_with_media(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
+        """{반려동물 ID: 방문 ID} — 사진·영상이 붙은 기록이 있는 가장 최근(시작 시각) 완료 방문."""
+
+    @abstractmethod
+    async def clear_notes(self, ctx: ShopContext, customer_id: int) -> None:
+        """그 보호자의 방문 기록들의 케어 메모·내부 메모를 비운다(익명화)."""
+
     @abstractmethod
     async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
         """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다."""
```

`backend/apps/visit/adapter/outbound/pg/visit_record_pg_repository.py`:

```diff
@@ -1,6 +1,6 @@
 from __future__ import annotations
 
-from sqlalchemy import delete, func, insert, select
+from sqlalchemy import delete, func, insert, select, update
 from sqlalchemy.dialects.postgresql import insert as pg_insert
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -8,6 +8,7 @@ from hub.app.dtos.shop_context import ShopContext
 from visit.adapter.outbound.mappers.visit_record_mapper import to_record
 from visit.adapter.outbound.orm.visit_orm import VisitOrm, VisitRecordItemOrm, VisitRecordMediaOrm, VisitRecordOrm
 from visit.app.ports.output.visit_record_repository import VisitRecordRepository
+from visit.domain.entities.visit import COMPLETED
 from visit.domain.entities.visit_record import VisitRecord
 
 
@@ -52,6 +53,29 @@ class VisitRecordPgRepository(VisitRecordRepository):
                 media[m.visit_id].append(m)
         return {row.visit_id: to_record(row, items[row.visit_id], media[row.visit_id]) for row in rows}
 
+    async def latest_with_media(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
+        if not pet_ids:
+            return {}
+        rows = await self._session.execute(
+            select(VisitOrm.pet_id, VisitOrm.id)
+            .distinct(VisitOrm.pet_id)
+            .where(
+                VisitOrm.shop_id == ctx.shop_id, VisitOrm.pet_id.in_(pet_ids), VisitOrm.status == COMPLETED,
+                VisitOrm.id.in_(select(VisitRecordMediaOrm.visit_id)),
+            )
+            .order_by(VisitOrm.pet_id, VisitOrm.starts_at.desc(), VisitOrm.id.desc())
+        )
+        return dict(rows.all())
+
+    async def clear_notes(self, ctx: ShopContext, customer_id: int) -> None:
+        await self._session.execute(
+            update(VisitRecordOrm)
+            .where(VisitRecordOrm.visit_id.in_(
+                select(VisitOrm.id).where(VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id)
+            ))
+            .values(care_note=None, internal_note=None)
+        )
+
     async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
         fields = dict(
             weight_kg=record.weight_kg, care_note=record.care_note, internal_note=record.internal_note,
```

`backend/apps/visit/app/use_cases/visit_ledger_interactor.py`:

```diff
@@ -7,14 +7,19 @@ from hub.app.dtos.shop_context import ShopContext
 from hub.app.dtos.upcoming_visit import UpcomingVisit
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
+from visit.app.ports.output.visit_record_repository import VisitRecordRepository
+from visit.domain.services.visit_record_rules import cover_media_id
 from visit.domain.services.visit_schedule import day_bounds, local_date
 
 
 class VisitLedgerInteractor(VisitLedgerPort):
     """허브의 VisitLedgerPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""
 
-    def __init__(self, ledger: VisitLedgerRepository, now: Callable[[], datetime]) -> None:
+    def __init__(
+        self, ledger: VisitLedgerRepository, records: VisitRecordRepository, now: Callable[[], datetime]
+    ) -> None:
         self._ledger = ledger
+        self._records = records
         self._now = now
 
     async def pet_has_visits(self, ctx: ShopContext, pet_id: int) -> bool:
@@ -36,3 +41,9 @@ class VisitLedgerInteractor(VisitLedgerPort):
 
     async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
         await self._ledger.clear_memos(ctx, customer_id)
+        await self._records.clear_notes(ctx, customer_id)
+
+    async def latest_covers(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
+        latest = await self._records.latest_with_media(ctx, pet_ids)
+        records = await self._records.list_many(ctx, list(latest.values()))
+        return {pet_id: cover_media_id(records[visit_id].media) for pet_id, visit_id in latest.items()}
```

`backend/apps/customer/app/services/pet_photos.py`:

```python
"""반려동물 프로필 사진 — 가장 최근 완료 기록의 대표 사진(visit)을 썸네일 URL(media)로 바꾼다(설계 8절).

사진을 customer 에 복사해 두지 않는다. 목록·상세가 읽을 때마다 허브 포트 둘로 한 번씩 묻는다(N+1 없음).
"""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


async def pet_photos(
    ctx: ShopContext, pet_ids: list[int], ledger: VisitLedgerPort, library: MediaLibraryPort
) -> dict[int, str]:
    """{반려동물 ID: 썸네일 URL}. 사진이 없는 아이는 빠진다."""
    if not pet_ids:
        return {}
    covers = await ledger.latest_covers(ctx, pet_ids)
    urls = await library.read_urls(ctx, sorted(set(covers.values())))
    return {pet_id: urls[media_id].thumb_url for pet_id, media_id in covers.items() if media_id in urls}
```

`backend/apps/customer/adapter/inbound/api/schemas/get_customer_schema.py`:

```diff
@@ -54,6 +54,16 @@ class PetSchema(BaseModel):
         )
 
 
+class PetWithPhotoSchema(PetSchema):
+    """조회 응답(고객 상세·반려동물 상세)의 반려동물 — 프로필 사진을 더한다."""
+
+    photo: str | None   # 가장 최근 완료 기록의 대표 사진 썸네일 URL
+
+    @classmethod
+    def with_photo(cls, view: PetView, photo: str | None) -> PetWithPhotoSchema:
+        return cls(**PetSchema.of(view).model_dump(), photo=photo)
+
+
 class CustomerSchema(BaseModel):
     customer_id: int
     name: str
@@ -91,15 +101,17 @@ class UpcomingVisitSchema(BaseModel):
 
 
 class CustomerOverviewSchema(CustomerDetailSchema):
-    """고객 상세(GET) — 방문 요약을 더한다. 등록·수정 응답은 방문 요약 없는 CustomerDetailSchema 다."""
+    """고객 상세(GET) — 방문 요약과 반려동물 프로필 사진을 더한다. 등록·수정 응답은 둘 다 없는 CustomerDetailSchema 다."""
 
+    pets: list[PetWithPhotoSchema]
     no_show_count: int
     upcoming_visits: list[UpcomingVisitSchema]
 
     @classmethod
     def of(cls, view: CustomerOverviewView) -> CustomerOverviewSchema:
         return cls(
-            customer=CustomerSchema.of(view.customer), pets=[PetSchema.of(p) for p in view.pets],
+            customer=CustomerSchema.of(view.customer),
+            pets=[PetWithPhotoSchema.with_photo(p, view.photos.get(p.pet_id)) for p in view.pets],
             no_show_count=view.no_show_count,
             upcoming_visits=[UpcomingVisitSchema.model_validate(u, from_attributes=True) for u in view.upcoming_visits],
         )
```

`backend/apps/customer/adapter/inbound/api/schemas/get_pet_schema.py`:

```diff
@@ -2,8 +2,8 @@ from __future__ import annotations
 
 from pydantic import BaseModel
 
-from customer.adapter.inbound.api.schemas.get_customer_schema import PetSchema
-from customer.app.dtos.customer_view_dto import PetDetailView
+from customer.adapter.inbound.api.schemas.get_customer_schema import PetSchema, PetWithPhotoSchema
+from customer.app.dtos.customer_view_dto import PetDetailView, PetOverviewView
 
 
 class OwnerSummarySchema(BaseModel):
@@ -38,3 +38,15 @@ class PetDetailSchema(BaseModel):
                 for s in view.siblings
             ],
         )
+
+
+class PetOverviewSchema(PetDetailSchema):
+    """반려동물 상세(GET) — pet 에 프로필 사진을 더한다. 쓰기 응답은 사진 없는 PetDetailSchema 다."""
+
+    pet: PetWithPhotoSchema
+
+    @classmethod
+    def of_overview(cls, view: PetOverviewView) -> PetOverviewSchema:
+        detail = PetDetailSchema.of(view.detail)
+        return cls(pet=PetWithPhotoSchema.with_photo(view.detail.pet, view.photo), owner=detail.owner,
+                   siblings=detail.siblings)
```

`backend/apps/customer/adapter/inbound/api/schemas/list_customers_schema.py`:

```diff
@@ -13,6 +13,7 @@ class PetSummarySchema(BaseModel):
     age_label: str
     has_conditions: bool
     passed_away: bool
+    photo: str | None   # 프로필 사진 썸네일 URL
 
 
 class FamilyCardSchema(BaseModel):
@@ -39,7 +40,7 @@ class CustomerListSchema(BaseModel):
                         PetSummarySchema(
                             pet_id=p.pet_id, name=p.name, species=p.species, breed=p.breed,
                             age_label=p.age_label, has_conditions=p.has_conditions,
-                            passed_away=p.passed_away,
+                            passed_away=p.passed_away, photo=p.photo,
                         )
                         for p in card.pets
                     ],
```

`backend/apps/customer/adapter/inbound/api/v1/get_pet_router.py`:

```diff
@@ -2,7 +2,7 @@ from fastapi import APIRouter, Depends
 
 from core.shop_guard import get_shop_context
 from customer.adapter.inbound.api.path_params import PetId
-from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
+from customer.adapter.inbound.api.schemas.get_pet_schema import PetOverviewSchema
 from customer.app.dtos.get_pet_dto import GetPetQuery
 from customer.app.ports.input.get_pet_use_case import GetPetUseCase
 from customer.dependencies.get_pet_provider import get_get_pet_use_case
@@ -11,10 +11,10 @@ from hub.app.dtos.shop_context import ShopContext
 get_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])
 
 
-@get_pet_router.get("/{shop_id}/pets/{pet_id}", response_model=PetDetailSchema)
+@get_pet_router.get("/{shop_id}/pets/{pet_id}", response_model=PetOverviewSchema)
 async def get_pet(
     pet_id: PetId,
     ctx: ShopContext = Depends(get_shop_context),
     use_case: GetPetUseCase = Depends(get_get_pet_use_case),
-) -> PetDetailSchema:
-    return PetDetailSchema.of(await use_case.get_pet(GetPetQuery(ctx=ctx, pet_id=pet_id)))
+) -> PetOverviewSchema:
+    return PetOverviewSchema.of_overview(await use_case.get_pet(GetPetQuery(ctx=ctx, pet_id=pet_id)))
```

`backend/apps/customer/app/dtos/customer_view_dto.py`:

```diff
@@ -97,6 +97,7 @@ class CustomerOverviewView:
     pets: list[PetView]
     no_show_count: int
     upcoming_visits: list[UpcomingVisitView]
+    photos: dict[int, str]   # 반려동물 ID → 프로필 사진 썸네일 URL(사진이 없는 아이는 빠진다)
 
 
 @dataclass(frozen=True)
@@ -125,3 +126,11 @@ class PetDetailView:
     pet: PetView
     owner: OwnerSummaryView
     siblings: list[SiblingView]
+
+
+@dataclass(frozen=True)
+class PetOverviewView:
+    """반려동물 상세 화면(GET) — 상세에 프로필 사진을 더한다. 쓰기 응답은 사진 없는 PetDetailView 다."""
+
+    detail: PetDetailView
+    photo: str | None
```

`backend/apps/customer/app/dtos/list_customers_dto.py`:

```diff
@@ -24,6 +24,7 @@ class PetSummaryView:
     age_label: str
     has_conditions: bool
     passed_away: bool
+    photo: str | None   # 프로필 사진 썸네일 URL
 
 
 @dataclass(frozen=True)
```

`backend/apps/customer/app/ports/input/get_pet_use_case.py`:

```diff
@@ -2,10 +2,10 @@ from __future__ import annotations
 
 from abc import ABC, abstractmethod
 
-from customer.app.dtos.customer_view_dto import PetDetailView
+from customer.app.dtos.customer_view_dto import PetOverviewView
 from customer.app.dtos.get_pet_dto import GetPetQuery
 
 
 class GetPetUseCase(ABC):
     @abstractmethod
-    async def get_pet(self, query: GetPetQuery) -> PetDetailView: ...
+    async def get_pet(self, query: GetPetQuery) -> PetOverviewView: ...
```

`backend/apps/customer/app/use_cases/customer_myself_interactor.py`:

```diff
@@ -28,10 +28,13 @@ class CustomerMyselfInteractor(CustomerMyselfUseCase):
                 "등록·수정은 customer:write(사장·직원), 고객 삭제는 customer:delete(사장)가 필요합니다. "
                 "전화번호는 숫자만 저장하고 매장 안에서 살아 있는 고객끼리 겹치지 않습니다(겹치면 409). "
                 "목록과 반려동물 상세의 번호는 가리고, 전체 번호는 고객 상세에서만 줍니다. "
-                "고객 삭제는 이름·전화·메모와 반려동물 이름·메모·질병을 지우는 익명화이고, "
+                "고객 삭제는 이름·전화·메모와 반려동물 이름·메모·질병, 미용 기록의 두 메모를 지우는 익명화이고"
+                "(사진은 매장의 기록이라 남깁니다), "
                 "삭제한 고객은 조회·검색·번호 조회에서 없는 것으로 봅니다. "
                 "반려동물은 질병을 하나 이상 고르거나 '질병 없음'을 직접 확인해야 저장됩니다. "
                 "고객 상세는 노쇼 횟수와 다가오는 예약(최대 3건)도 줍니다. "
+                "목록·고객 상세·반려동물 상세(GET)의 반려동물에는 photo(사진이 붙은 가장 최근 완료 기록의 대표 사진 "
+                "썸네일, 없으면 null)가 있습니다. "
                 "방문 기록이 있는 반려동물은 지우지 않고(409 PET_HAS_VISITS), 앞으로의 예약이 남은 아이의 "
                 "무지개다리와 고객 삭제는 막습니다(409 PET_HAS_UPCOMING_VISITS·CUSTOMER_HAS_UPCOMING_VISITS). "
                 "다른 매장의 고객·반려동물 ID 는 404 입니다."
```

`backend/apps/customer/app/use_cases/get_customer_interactor.py`:

```diff
@@ -10,6 +10,8 @@ from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.pet_repository import PetRepository
 from customer.app.services.detail_reader import read_customer_detail
+from customer.app.services.pet_photos import pet_photos
+from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 UPCOMING_LIMIT = 3
@@ -18,11 +20,12 @@ UPCOMING_LIMIT = 3
 class GetCustomerInteractor(GetCustomerUseCase):
     def __init__(
         self, customers: CustomerRepository, pets: PetRepository, ledger: VisitLedgerPort,
-        today: Callable[[], date],
+        library: MediaLibraryPort, today: Callable[[], date],
     ) -> None:
         self._customers = customers
         self._pets = pets
         self._ledger = ledger
+        self._library = library
         self._today = today
 
     async def get_customer(self, query: GetCustomerQuery) -> CustomerOverviewView:
@@ -40,4 +43,5 @@ class GetCustomerInteractor(GetCustomerUseCase):
                                   starts_at=u.starts_at.astimezone(zone))
                 for u in upcoming
             ],
+            photos=await pet_photos(ctx, [pet.pet_id for pet in detail.pets], self._ledger, self._library),
         )
```

`backend/apps/customer/app/use_cases/get_pet_interactor.py`:

```diff
@@ -3,21 +3,29 @@ from __future__ import annotations
 from collections.abc import Callable
 from datetime import date
 
-from customer.app.dtos.customer_view_dto import PetDetailView
+from customer.app.dtos.customer_view_dto import PetOverviewView
 from customer.app.dtos.get_pet_dto import GetPetQuery
 from customer.app.ports.input.get_pet_use_case import GetPetUseCase
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.pet_repository import PetRepository
 from customer.app.services.detail_reader import read_pet_detail
+from customer.app.services.pet_photos import pet_photos
+from hub.app.ports.media_library_port import MediaLibraryPort
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
 class GetPetInteractor(GetPetUseCase):
     def __init__(
-        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
+        self, customers: CustomerRepository, pets: PetRepository, ledger: VisitLedgerPort,
+        library: MediaLibraryPort, today: Callable[[], date],
     ) -> None:
         self._customers = customers
         self._pets = pets
+        self._ledger = ledger
+        self._library = library
         self._today = today
 
-    async def get_pet(self, query: GetPetQuery) -> PetDetailView:
-        return await read_pet_detail(query.ctx, query.pet_id, self._customers, self._pets, self._today())
+    async def get_pet(self, query: GetPetQuery) -> PetOverviewView:
+        detail = await read_pet_detail(query.ctx, query.pet_id, self._customers, self._pets, self._today())
+        photos = await pet_photos(query.ctx, [query.pet_id], self._ledger, self._library)
+        return PetOverviewView(detail=detail, photo=photos.get(query.pet_id))
```

`backend/apps/customer/app/use_cases/list_customers_interactor.py`:

```diff
@@ -16,7 +16,10 @@ from customer.app.ports.output.customer_search_port import CustomerSearchPort
 from customer.app.ports.output.pet_repository import PetRepository
 from customer.domain.services.pet_age import age_label
 from customer.domain.services.phone_number import mask_phone
+from customer.app.services.pet_photos import pet_photos
 from customer.domain.services.search_terms import parse_query
+from hub.app.ports.media_library_port import MediaLibraryPort
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
 class ListCustomersInteractor(ListCustomersUseCase):
@@ -24,11 +27,13 @@ class ListCustomersInteractor(ListCustomersUseCase):
 
     def __init__(
         self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
-        today: Callable[[], date],
+        ledger: VisitLedgerPort, library: MediaLibraryPort, today: Callable[[], date],
     ) -> None:
         self._customers = customers
         self._pets = pets
         self._search = search
+        self._ledger = ledger
+        self._library = library
         self._today = today
 
     async def list_customers(self, query: ListCustomersQuery) -> CustomerListView:
@@ -45,6 +50,9 @@ class ListCustomersInteractor(ListCustomersUseCase):
                 pets_by_customer.setdefault(pet.customer_id, []).append(pet)
 
         today = self._today()
+        photos = await pet_photos(
+            query.ctx, [p.id for family in pets_by_customer.values() for p in family], self._ledger, self._library
+        )
         items = [
             FamilyCardView(
                 customer_id=customer_id,
@@ -54,7 +62,7 @@ class ListCustomersInteractor(ListCustomersUseCase):
                     PetSummaryView(
                         pet_id=p.id, name=p.name, species=p.species, breed=p.breed,
                         age_label=age_label(p.birth_date, p.birth_year, today),
-                        has_conditions=p.has_conditions, passed_away=p.passed_away,
+                        has_conditions=p.has_conditions, passed_away=p.passed_away, photo=photos.get(p.id),
                     )
                     for p in pets_by_customer.get(customer_id, [])
                 ],
```

`backend/apps/customer/dependencies/get_customer_provider.py`:

```diff
@@ -9,15 +9,18 @@ from customer.dependencies.customer_wiring import (
     build_customer_repository,
     build_pet_repository,
 )
-from customer.dependencies.hub_ports import get_visit_ledger
+from customer.dependencies.hub_ports import get_media_library, get_visit_ledger
 from customer.domain.services.pet_age import seoul_today
+from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
 def get_get_customer_use_case(
-    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger)
+    db: DbSession,
+    ledger: VisitLedgerPort = Depends(get_visit_ledger),
+    library: MediaLibraryPort = Depends(get_media_library),
 ) -> GetCustomerUseCase:
     return GetCustomerInteractor(
-        customers=build_customer_repository(db), pets=build_pet_repository(db), ledger=ledger,
+        customers=build_customer_repository(db), pets=build_pet_repository(db), ledger=ledger, library=library,
         today=seoul_today,
     )
```

`backend/apps/customer/dependencies/get_pet_provider.py`:

```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from fastapi import Depends
+
 from core.database import DbSession
 from customer.app.ports.input.get_pet_use_case import GetPetUseCase
 from customer.app.use_cases.get_pet_interactor import GetPetInteractor
@@ -7,10 +9,18 @@ from customer.dependencies.customer_wiring import (
     build_customer_repository,
     build_pet_repository,
 )
+from customer.dependencies.hub_ports import get_media_library, get_visit_ledger
 from customer.domain.services.pet_age import seoul_today
+from hub.app.ports.media_library_port import MediaLibraryPort
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
-def get_get_pet_use_case(db: DbSession) -> GetPetUseCase:
+def get_get_pet_use_case(
+    db: DbSession,
+    ledger: VisitLedgerPort = Depends(get_visit_ledger),
+    library: MediaLibraryPort = Depends(get_media_library),
+) -> GetPetUseCase:
     return GetPetInteractor(
-        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
+        customers=build_customer_repository(db), pets=build_pet_repository(db), ledger=ledger, library=library,
+        today=seoul_today,
     )
```

`backend/apps/customer/dependencies/hub_ports.py`:

```diff
@@ -4,8 +4,13 @@
 """
 from __future__ import annotations
 
+from hub.app.ports.media_library_port import MediaLibraryPort
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
 def get_visit_ledger() -> VisitLedgerPort:
     raise RuntimeError("VisitLedgerPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
+
+
+def get_media_library() -> MediaLibraryPort:
+    raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/customer/dependencies/list_customers_provider.py`:

```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from fastapi import Depends
+
 from core.database import DbSession
 from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
 from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
@@ -8,11 +10,18 @@ from customer.dependencies.customer_wiring import (
     build_customer_search,
     build_pet_repository,
 )
+from customer.dependencies.hub_ports import get_media_library, get_visit_ledger
 from customer.domain.services.pet_age import seoul_today
+from hub.app.ports.media_library_port import MediaLibraryPort
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
-def get_list_customers_use_case(db: DbSession) -> ListCustomersUseCase:
+def get_list_customers_use_case(
+    db: DbSession,
+    ledger: VisitLedgerPort = Depends(get_visit_ledger),
+    library: MediaLibraryPort = Depends(get_media_library),
+) -> ListCustomersUseCase:
     return ListCustomersInteractor(
         customers=build_customer_repository(db), pets=build_pet_repository(db),
-        search=build_customer_search(db), today=seoul_today,
+        search=build_customer_search(db), ledger=ledger, library=library, today=seoul_today,
     )
```

`backend/apps/visit/dependencies/visit_ledger_provider.py`:

```diff
@@ -3,9 +3,9 @@ from __future__ import annotations
 from core.database import DbSession
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
 from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
-from visit.dependencies.visit_wiring import build_visit_repository
+from visit.dependencies.visit_wiring import build_record_repository, build_visit_repository
 from visit.domain.services.visit_schedule import utc_now
 
 
 def get_visit_ledger_use_case(db: DbSession) -> VisitLedgerPort:
-    return VisitLedgerInteractor(ledger=build_visit_repository(db), now=utc_now)
+    return VisitLedgerInteractor(ledger=build_visit_repository(db), records=build_record_repository(db), now=utc_now)
```

`backend/main.py`:

```diff
@@ -39,6 +39,7 @@ from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
 from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
 from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
 from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
+from customer.dependencies.hub_ports import get_media_library as get_customer_media_library
 from customer.dependencies.hub_ports import get_visit_ledger
 from media.adapter.inbound.api.error_map import MEDIA_ERROR_STATUS
 from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_router
@@ -88,7 +89,8 @@ from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
-from visit.dependencies.hub_ports import get_customer_directory, get_media_library
+from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.hub_ports import get_media_library as get_visit_media_library
 from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
 
 
@@ -181,7 +183,8 @@ app.dependency_overrides[get_membership_directory] = get_list_memberships_use_ca
 app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case
 app.dependency_overrides[get_customer_directory] = get_customer_directory_use_case
 app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
-app.dependency_overrides[get_media_library] = get_media_library_use_case
+app.dependency_overrides[get_visit_media_library] = get_media_library_use_case
+app.dependency_overrides[get_customer_media_library] = get_media_library_use_case
 
 
 @app.get("/health")
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps/visit apps/customer tests/integration/test_visit_record_wiring.py tests/integration/test_visit_locking.py tests/integration/test_customer_locking.py tests/test_hub_port_binding.py -q -p no:cacheprovider` → 전부 통과

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 882 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 295 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `VisitLedgerInteractor.clear_customer_memos`의 `await self._records.clear_notes(…)`를 뺀다 → `test_익명화는_방문_메모와_기록의_두_메모를_비우고_사진은_남긴다` 실패.
- `latest_with_media`의 `VisitOrm.status == COMPLETED`를 뺀다 → `test_사진이_붙은_가장_최근_완료_방문을_아이마다_한_번에` 실패(미용 중 방문이 끼어든다).
- `latest_with_media`의 `VisitOrm.id.in_(select(VisitRecordMediaOrm.visit_id))`를 뺀다 → 같은 테스트 실패(사진 없는 최근 기록을 고른다).
- `pet_photos`의 `if media_id in urls`를 뺀다 → `test_반려동물마다_프로필_사진을_한_번에_묻는다` 실패(정리된 사진).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(customer): 반려동물 프로필 사진 — 사진이 붙은 가장 최근 완료 기록의 대표(VisitLedgerPort.latest_covers)를 목록·고객 상세·반려동물 상세에, 익명화는 기록의 두 메모도 비운다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: 정리 스크립트와 흐름 확인 — `purge_stale_media`(하루 넘게 가져가지 않은 것, 표시 → 저장소 → 행 순서로 다시 돌려도 같다), `check_media_flow.sh`(게이트웨이·MinIO)

**Files:**
- Create: `backend/scripts/purge_stale_media.py`
- Create: `backend/scripts/check_media_flow.sh`
- Create: `backend/tests/test_purge_stale_media.py`

**Interfaces:**
- Consumes: 작업 1 의 `MediaObjectOrm`·`MediaPgRepository`, 작업 3 의 `get_object_storage`, 작업 3~10 의 경로 전부(흐름 스크립트), `media.tests.helpers.fakes.FakeStorage`.
- Produces: `scripts.purge_stale_media` — `KEEP_FOR = 24시간`, `purge(session, storage, now) -> int`, `_run()`, `main()`; `backend/scripts/check_media_flow.sh`.

놓였거나 가져가지 않은 미디어를 지운다(설계 7.5, M6·M15). ① 발급만 하고 하루 넘게 확인하지 않은 것 ② 확인했지만 하루 넘게 어느 기록도 가져가지 않은 것(기록에서 빼거나 기록을 지워 놓인 것도). 객체마다 행을 pending 으로 되돌려 커밋하고(그사이 기록이 가져가지 못한다 — 조건을 다시 봐서 고른 뒤 가져간 것은 건너뛴다), 저장소에서 지우고, 행을 지워 커밋한다. 저장소 호출은 잠금을 쥔 채 하지 않는다. 중간에 멈추면 행이 오래된 pending 으로 남아 다음 실행이 잡는다. 운영에서는 주기적으로 돌린다. 흐름 스크립트는 게이트웨이와 MinIO 를 거쳐 발급 → 서명 URL 로 바로 PUT → 확인 → 기록 쓰기·덧붙이기 → 완료 → 상세·달력·피드·프로필 → 삭제까지 본다(서명 URL 로 대표 사진을 바로 GET 한다). 먼저 버킷을 준비한다(작업 2 의 스크립트).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_purge_stale_media.py`:

```python
"""미디어 정리 스크립트 — 하루 넘게 어느 기록도 가져가지 않은 것만 지운다."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

import scripts.purge_stale_media as purge_stale_media
from media.adapter.outbound.orm.media_orm import MediaObjectOrm
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.tests.helpers.builders import ctx, new_photo, new_video
from media.tests.helpers.fakes import FakeStorage
from scripts.purge_stale_media import purge

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 24, 3, 0, tzinfo=timezone.utc)
OLD, FRESH = NOW - timedelta(hours=25), NOW - timedelta(hours=23)


async def _media(session, kind="photo", status="pending", at=OLD, attached=False):
    repo = MediaPgRepository(session)
    media = await repo.create(ctx(), new_photo() if kind == "photo" else new_video())
    if status == "ready":
        await repo.mark_ready(ctx(), media.id, 100)
    await session.execute(
        update(MediaObjectOrm).where(MediaObjectOrm.id == media.id)
        .values(created_at=at, ready_at=at if status == "ready" else None, attached_at=at if attached else None)
    )
    await session.commit()
    return media


async def test_하루_넘은_pending_과_놓인_ready_만_저장소와_표에서_지운다(db_session):
    old_pending = await _media(db_session)
    old_loose = await _media(db_session, kind="video", status="ready")
    kept = [await _media(db_session, at=FRESH), await _media(db_session, status="ready", at=FRESH),
            await _media(db_session, status="ready", attached=True)]
    storage = FakeStorage()
    assert await purge(db_session, storage, NOW) == 2
    remaining = set((await db_session.execute(select(MediaObjectOrm.id))).scalars())
    assert remaining == {m.id for m in kept}
    assert [e for e in storage.journal if e[0] == "delete"] == [
        ("delete", old_pending.keys.all()), ("delete", old_loose.keys.all())]


async def test_저장소_삭제_중에_멈춰도_다시_돌리면_지운다(db_session):
    media = await _media(db_session, status="ready")

    class _Broken(FakeStorage):
        async def delete(self, keys):
            raise ConnectionError("저장소가 응답하지 않는다")

    with pytest.raises(ConnectionError):
        await purge(db_session, _Broken(), NOW)
    await db_session.rollback()
    row = (await db_session.execute(select(MediaObjectOrm).where(MediaObjectOrm.id == media.id))).scalar_one()
    assert (row.status, row.ready_at) == ("pending", None)   # 가져갈 수 없게 표시된 채 남았다
    assert await purge(db_session, FakeStorage(), NOW) == 1


async def test_고른_뒤_기록이_가져간_미디어는_건너뛴다(db_session):
    first = await _media(db_session, status="ready")
    second = await _media(db_session, status="ready")

    class _Racing(FakeStorage):
        """첫 객체를 지우는 사이 다른 요청이 둘째를 기록에 붙인다."""

        async def delete(self, keys):
            await super().delete(keys)
            if keys == list(first.keys.all()):
                await db_session.execute(update(MediaObjectOrm).where(MediaObjectOrm.id == second.id)
                                         .values(attached_at=NOW))
                await db_session.commit()

    assert await purge(db_session, _Racing(), NOW) == 1
    assert set((await db_session.execute(select(MediaObjectOrm.id))).scalars()) == {second.id}


async def test_정리_스크립트의_엔진도_hide_parameters를_켠다(migrated_test_db, monkeypatch):
    captured = {}
    original = purge_stale_media.create_async_engine

    def _spy(url, **kwargs):
        captured.update(kwargs)
        return original(url, **kwargs)

    monkeypatch.setattr(purge_stale_media, "create_async_engine", _spy)
    monkeypatch.setattr(purge_stale_media, "DATABASE_URL", migrated_test_db)
    monkeypatch.setattr(purge_stale_media, "get_object_storage", FakeStorage)
    await purge_stale_media._run()
    assert captured.get("hide_parameters") is True
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest tests/test_purge_stale_media.py -q -p no:cacheprovider`
Expected: 수집 단계 오류 — `ModuleNotFoundError: No module named 'scripts.purge_stale_media'`.

- [ ] **Step 3: 구현한다**

`backend/scripts/purge_stale_media.py`:

```python
"""하루 넘게 어느 기록도 가져가지 않은 미디어를 저장소와 표에서 지운다(설계 7.5). 여러 번 돌려도 결과가 같다.

지우는 것: ① 발급만 하고 하루 넘게 확인하지 않은 것(pending) ② 확인했지만 하루 넘게 어느 기록도 가져가지 않은 것 —
기록에서 뺐거나 기록을 지워 놓인 사진도 여기로 온다(놓인 뒤 바로 지우지 않는다 — 되돌리기·대기열 재시도의 여유).
한 객체씩 ① 행을 pending 으로 되돌려 커밋하고(그사이 기록이 가져가지 못한다) ② 저장소에서 지우고 ③ 행을 지워 커밋한다.
②에서 멈추면 행이 오래된 pending 으로 남아 다음 실행이 ①로 다시 잡는다. 잠금을 쥔 채 저장소를 부르지 않는다.
사용: cd infra && docker compose run --rm backend python scripts/purge_stale_media.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from media.adapter.outbound.orm.media_orm import MediaObjectOrm as Media
from media.app.ports.output.object_storage_port import ObjectStoragePort
from media.dependencies.media_wiring import get_object_storage

KEEP_FOR = timedelta(hours=24)


def _stale(cutoff: datetime):
    return or_(
        and_(Media.status == "pending", Media.created_at < cutoff),
        and_(Media.status == "ready", Media.attached_at.is_(None), Media.ready_at < cutoff),
    )


async def purge(session: AsyncSession, storage: ObjectStoragePort, now: datetime) -> int:
    """지운 미디어 수를 돌려준다. 객체마다 짧게 커밋한다."""
    cutoff = now - KEEP_FOR
    found = (
        await session.execute(
            select(Media.id, Media.object_key, Media.display_key, Media.thumb_key).where(_stale(cutoff)).order_by(Media.id)
        )
    ).all()
    purged = 0
    for media_id, *keys in found:
        # 조건을 다시 본다 — 고른 뒤 기록이 가져갔으면 건너뛴다. pending 으로 되돌리면 이제 가져갈 수 없다.
        marked = await session.execute(
            update(Media).where(Media.id == media_id, _stale(cutoff))
            .values(status="pending", ready_at=None, size_bytes=None)
        )
        await session.commit()
        if marked.rowcount != 1:
            continue
        await storage.delete([key for key in keys if key is not None])
        await session.execute(delete(Media).where(Media.id == media_id, Media.status == "pending"))
        await session.commit()
        purged += 1
    return purged


async def _run() -> int:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            return await purge(session, get_object_storage(), datetime.now(timezone.utc))
    finally:
        await engine.dispose()


def main() -> None:
    print(f"미디어 {asyncio.run(_run())}개를 지웠습니다.")


if __name__ == "__main__":
    main()
```

`backend/scripts/check_media_flow.sh`:

```bash
#!/usr/bin/env bash
# 개발 환경에서 사진 발급 → 저장소에 직접 올리기 → 확인 → 기록 쓰기·덧붙이기 → 완료 → 상세·달력·피드·프로필 사진 → 삭제까지
# 게이트웨이와 MinIO 를 거쳐 확인한다. 올리기(PUT)와 읽기(GET)는 서명 URL 로 저장소에 바로 간다.
# 사용: cd infra && docker compose up -d && docker compose run --rm backend python scripts/ensure_media_bucket.py \
#       && bash ../backend/scripts/check_media_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 와 버킷에 확인용 매장·유저·고객·방문·사진이 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }
YESTERDAY="$(at -1 11 | cut -c1-10)"

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
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

op=$(login "mflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"사진흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "mflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "mflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
echo "통과  매장 $shop_id 에 사장과 직원이 있다"

registered=$(call POST "$S/customers" "$staff_token" "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\
\"pet\":{\"name\":\"콩이\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\
\"weight_kg\":3.2,\"no_known_conditions\":true}}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
# 어제 11시 예약을 시작한다 — 실행 시각과 상관없이 자정을 넘기지 않는다.
visit=$(call POST "$S/visits" "$staff_token" "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at -1 11)\"}" \
  | field "['visits'][0]['visit_id']")
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"start\"}" >/dev/null
R="$S/visits/$visit/record"

early=$(call POST "$S/media/uploads" "$staff_token" '{"kind":"photo","content_type":"image/jpeg","byte_size":3000,"width":3000,"height":2000}')
expect "올리기 전에 확인하면 409" "$(call POST "$S/media/$(echo "$early" | field "['media_id']")/confirm" "$staff_token" | field "['code']")" "MEDIA_NOT_UPLOADED"
expect "서명과 다른 형식은 저장소가 거절" "$(put "$(echo "$early" | field "['puts']['original']")" image/png 10)" "403"
before=$(photo "$staff_token"); after=$(photo "$staff_token")
echo "통과  사진 $before, $after 를 저장소에 바로 올리고 확인했다"

bath=$(call GET "$S/menus" "$staff_token" | field "['items'][0]['menu_id']")
saved=$(call PUT "$R" "$staff_token" "{\"weight_kg\":3.4,\"care_note\":\"눈물 자국 관리\",\"payment_method\":\"card\",\
\"total_amount\":25000,\"items\":[{\"menu_id\":$bath,\"amount\":28000}],\
\"media\":[{\"media_id\":$before,\"phase\":\"before\",\"sort_order\":0}]}")
expect "기록을 처음 쓰면 버전 1" "$(echo "$saved" | field "['version']")" "1"
expect "몸무게가 현재 몸무게가 된다" "$(call GET "$S/pets/$kong" "$staff_token" | field "['pet']['weight_kg']")" "3.4"
appended=$(call POST "$R/media" "$staff_token" "{\"media_id\":$after,\"phase\":\"after\"}")
expect "덧붙이면 버전 2" "$(echo "$appended" | calc "(d['version'], len(d['media']))")" "(2, 2)"
expect "옛 버전으로 저장하면 409" "$(status PUT "$R" "$staff_token" '{"version":1}')" "409"
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"complete\"}" >/dev/null

cover=$(call GET "$S/visits/$visit" "$staff_token" | field "['cover']")
expect "대표 사진은 후 사진" "$(call GET "$S/visits/$visit" "$staff_token" | calc "d['cover'] == [m for m in d['record']['media'] if m['phase'] == 'after'][0]['thumb_url']")" "True"
expect "대표 사진 URL 을 저장소에서 바로 읽는다" "$(curl -s -o /dev/null -w '%{http_code}' "$cover")" "200"
expect "달력 칸의 대표 사진" "$(call GET "$S/visits/calendar?month=${YESTERDAY:0:7}" "$staff_token" \
  | calc "[x['cover'] for x in d['days'] if x['date'] == '$YESTERDAY'][0] == '$cover'")" "True"
expect "피드 카드" "$(call GET "$S/visits/feed?pet_id=$kong" "$staff_token" | calc "(d['items'][0]['visit_id'], d['items'][0]['media_count'])")" "($visit, 2)"
expect "반려동물 프로필 사진" "$(call GET "$S/pets/$kong" "$staff_token" | calc "d['pet']['photo'] == '$cover'")" "True"

expect "직원은 기록을 지우지 못한다" "$(status DELETE "$R" "$staff_token")" "403"
expect "사장은 기록을 지운다" "$(status DELETE "$R" "$owner_token")" "204"
expect "기록이 없으면 대표 사진도 없다" "$(call GET "$S/visits/$visit" "$staff_token" | calc "(d['record'], d['cover'])")" "(None, None)"

echo "전체 흐름 확인 완료"
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest tests/test_purge_stale_media.py -q -p no:cacheprovider` → 4 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 882 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 299 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

Run (`infra/`): `docker compose up -d && docker compose run --rm backend python scripts/ensure_media_bucket.py && bash ../backend/scripts/check_media_flow.sh` → `통과` 17줄 뒤 `전체 흐름 확인 완료`(개발 DB·버킷에 확인용 매장·사진이 남는다)

Run (`infra/`): `docker compose run --rm backend python scripts/purge_stale_media.py` → `미디어 N개를 지웠습니다.`(방금 만든 것은 하루가 안 돼 0개일 수 있다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `purge`의 표시 UPDATE `where(Media.id == media_id, _stale(cutoff))`에서 `_stale(cutoff)`를 뺀다 → `test_고른_뒤_기록이_가져간_미디어는_건너뛴다` 실패.
- `_stale`의 ② 에서 `Media.attached_at.is_(None)`을 뺀다 → 3개 실패(붙어 있는 사진까지 지운다).
- 표시의 `.values(status="pending", ready_at=None, size_bytes=None)`을 `.values(ready_at=Media.ready_at)`로 → 3개 실패(행 삭제 조건 `status='pending'`에 걸리지 않는다).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(media): 정리 스크립트와 흐름 확인 — purge_stale_media(하루 넘게 가져가지 않은 것, 표시 → 저장소 → 행 순서로 다시 돌려도 같음), check_media_flow.sh(게이트웨이·MinIO)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: 문서 — media 스포크 문서, visit·customer·hub 문서, 하네스(버킷·흐름·정리·MinIO 통합 테스트), 결정 기록 007(④-1 절)

**Files:**
- Create: `backend/apps/media/_docs/CLAUDE.md`
- Create: `backend/apps/media/CLAUDE.md`
- Modify: `_docs/decisions/007-record-media.md`
- Modify: `_docs/harness.md`
- Modify: `backend/apps/customer/_docs/CLAUDE.md`
- Modify: `backend/apps/hub/_docs/CLAUDE.md`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`

**Interfaces:**
- Consumes: 작업 1~11 의 결과와 검증 수치(단위 882·통합 299·계약 6·새 라우트 일곱).
- Produces: `backend/apps/media/_docs/CLAUDE.md`(+ `CLAUDE.md` 심볼릭 링크), 스포크 문서 셋의 새 규칙, 하네스 표 세 줄과 MinIO 통합 테스트 규칙, 결정 기록 007 의 ④-1 절. ④-2 앱 계획이 이 문서들과 007 에 기댄다.

문서 작업이라 테스트가 없다. 수치가 실제 실행 결과와 다르면 문서가 아니라 코드를 의심한다(작업 1~11 의 diff 가 그대로 적용됐는지).

- [ ] **Step 1: 문서를 쓴다**

`backend/apps/media/_docs/CLAUDE.md`:

```markdown
# media — 사진·영상 객체

소유 데이터: `media_objects`(메타데이터). 파일은 객체 저장소(S3 호환 — 개발은 compose 의 MinIO)에 있다.

- 파일은 서버를 거치지 않는다. 앱이 발급(`POST /media/uploads`)으로 받은 서명 URL 로 저장소에 바로 PUT 하고, 확인(`POST /media/{media_id}/confirm`)이 저장소를 HEAD 로 대조해 pending → ready 로 바꾼다(조건부 UPDATE — 동시에 두 번 확인해도 한 번). 서버는 파일을 디코딩하지 않는다. 가로·세로·길이는 앱 선언값이고 범위만 본다.
- 받는 것과 한도는 `domain/services/media_rules.py` 한 곳이다: 사진 `image/jpeg` 20MB(원본·표시용·썸네일 셋), 영상 `video/mp4` 200MB·60초(원본·포스터 둘). 확인 때 한도를 넘거나 형식이 다르면 객체를 지우고 422 다.
- **객체 키는 렌디션이 앞이다** — `original/shops/{매장}/{ID}.jpg`, `original-video/…mp4`, `display/…`, `thumb/…`. S3 수명주기 규칙은 접두사로만 거르므로 원본만 싼 계층으로 옮기려면(`scripts/ensure_media_bucket.py`) 이 모양이어야 한다.
- 읽기 URL 은 매장 시간대의 가장 최근 04:00 을 서명 시각으로, 48시간 유효로 만든다(`domain/services/url_expiry.py`) — 하루 동안 글자까지 같아 앱·CDN 캐시가 맞고, 남은 유효 시간은 24~48시간이다. botocore 는 서명 시각을 늘 '지금'으로 찍어서 GET 서명만 `adapter/outbound/s3/sigv4_query.py`가 직접 만든다(botocore 와 글자까지 같은지 테스트가 본다). PUT 서명은 boto3 가 한다.
- 서명은 앱이 닿는 **공개 주소**(`S3_PUBLIC_ENDPOINT_URL`)로, HEAD·DELETE 는 서버가 닿는 **내부 주소**(`S3_ENDPOINT_URL`)로 한다 — 서명에 호스트가 들어간다. 저장소 호출(HEAD·DELETE)은 잠금을 쥔 채 하지 않는다.
- 허브 포트 `MediaLibraryPort`를 구현한다(`app/use_cases/media_library_interactor.py`, HTTP 없음). visit 이 기록에 붙일 때 가져가고(`claim` — 준비됐고 이 매장의 것이고 아무도 안 가져간 것만, 전부 되거나 전부 안 됨, 세이브포인트) 뺄 때 놓는다(`release`). customer·visit 이 읽기 URL 을 받는다(`read_urls`). media 는 어느 기록이 가져갔는지 모른다 — `attached_at`만 안다.
- 놓였거나 가져가지 않은 미디어는 바로 지우지 않는다. `scripts/purge_stale_media.py`가 하루 넘은 것(pending, 또는 ready 인데 미부착)을 표시 → 저장소 삭제 → 행 삭제 순서로 지운다. 운영에서는 이 스크립트를 주기적으로 돌린다.
- 이 스포크는 다른 스포크를 import 하지 않는다. 다른 스포크의 허브 포트도 쓰지 않는다.
```

`backend/apps/media/CLAUDE.md`: `_docs/CLAUDE.md`를 가리키는 심볼릭 링크다(다른 스포크와 같다) — `ln -s _docs/CLAUDE.md backend/apps/media/CLAUDE.md`

`_docs/decisions/007-record-media.md`:

```diff
@@ -62,3 +62,36 @@
 - 폼 위임의 작은 정정(작업 8): `VisitFormValue.startsAt`의 주석을 옛 문구("지금 시작이면 null")로 되돌렸고, `_prefill`은 `applyPrefill`이 false(옛 응답·손댄 뒤)면 `setState`를 부르지 않아 옛 동작과 정확히 같다. `timelineHours`의 "끝이 정각이면 올리지 않는다" 분기에 테스트를 더했다. 커밋 739c98e.
 - `UploadClient`의 취소(작업 10, 남는 것): `cancelToken`으로 취소하면 `DioExceptionType.cancel`이 응답 없는 오류라 `ApiException.network`(NETWORK)로 보인다. ④-2 에서 업로드 UI 를 붙이기 전에 `CANCELLED` 코드를 두거나 호출자가 `cancelToken.isCancelled`를 먼저 보는 규칙을 정한다. `receiveTimeout` 30초를 확인하는 단언도 없다.
 - 테스트 수: 계획서는 542 였으나 작업 8(739c98e)의 정각 끝 테스트 하나가 더해져 543 이다.
+
+## ④-1 백엔드에서 정한 것
+
+새 스포크 media(발급·확인·`MediaLibraryPort`), visit 의 미용 기록(쓰기·덧붙이기·삭제·읽기 넓히기·피드), 메뉴 정가, customer 의 프로필 사진·익명화, 스크립트 셋(버킷 준비·정리·흐름 확인). 새 라우트 7개(media 셋, visit 넷 — 라우트 표의 나머지는 그대로), 마이그레이션 셋(0007 미디어 · 0008 메뉴 정가 · 0009 기록), 새 의존성 `boto3`. 단위 767 → 882, 통합 264 → 299, 구조 계약 6종(media 를 모든 계약에 더했다).
+
+### 설계와 다르게 간 것
+
+- **빠진 미디어를 바로 지우지 않는다.** 설계 8절은 "빠진 미디어는 release + 커밋 뒤 discard"였다. 커밋 뒤 백그라운드 삭제는 요청 세션이 닫힌 뒤 자기 세션을 여는 장치가 따로 필요하고, 사진을 뺐다가 되돌리거나 업로드 대기열이 다시 보내는 여유도 없앤다. 그래서 `MediaLibraryPort`에 `discard`를 두지 않고, 놓인 미디어는 정리 스크립트가 하루 뒤 지운다(가져가지 않은 미디어와 같은 규칙). 앱에는 빼는 즉시 보이지 않는다. 운영에서는 정리 스크립트를 주기적으로 돌려야 한다.
+- **객체 키는 렌디션이 앞이다**(`original/shops/{매장}/{ID}.jpg` 등, 설계 6.1 은 `shops/{매장}/media/{ID}/original.jpg`). S3 수명주기 규칙은 접두사로만 거르기 때문에, 원본만 싼 계층으로 옮기려면 원본이 한 접두사 아래 모여야 한다. 영상 원본은 `original-video/`로 따로 둔다.
+- **읽기 서명은 직접 만든다.** 하루 동안 같은 URL(설계 7.3)은 서명 시각을 고정해야 하는데 botocore 는 늘 지금으로 찍는다. 서명 시각을 매장 시간대 가장 최근 04:00, 유효 48시간으로 두는 SigV4 쿼리 서명을 표준 라이브러리로 만들었고(`media/adapter/outbound/s3/sigv4_query.py`), 같은 시각의 botocore URL 과 글자까지 같은지 테스트한다. 경로 방식 주소를 쓴다.
+- **설정 이름은 `S3_*`.** 설계는 `MEDIA_S3_*`였지만 개발 `.env`에 이미 `S3_ENDPOINT_URL`·`S3_ACCESS_KEY`·`S3_SECRET_KEY`·`S3_BUCKET`이 있어 그대로 쓰고 `S3_PUBLIC_ENDPOINT_URL`(기본 `http://127.0.0.1:9010`)·`S3_REGION`(기본 `us-east-1`)을 더했다. 운영은 S3 서울 리전 주소와 `ap-northeast-2`를 넣는다.
+- **`claim`이 종류를 돌려주고, visit 이 연결 표에 적는다**(`visit_record_media.kind`). 대표 사진(후 → 전 → 영상 포스터)과 방문당 한도를 visit 표만으로 계산하려는 것이다. 종류는 바뀌지 않는 사실이라 옮겨 적어도 어긋나지 않는다. 허브 오류는 `MediaClaimNotFoundError`·`MediaClaimNotReadyError`·`MediaClaimAlreadyAttachedError`(media 도메인 오류와 이름을 나눴다).
+- **`set_pet_weight(ctx, pet_id, weight_kg)`** — 설계의 `at` 인자는 쓸 곳이 없어 뺐다.
+- **기록 삭제는 `record:delete`(사장).** 설계 9절은 `record:write`였지만 권한 시드(0002)가 `record:delete`를 "기록 삭제"로 두고 사장에게만 줬다. 사진 한 장 빼기는 전체 교체(`record:write`)로 한다.
+- **메뉴 정가의 CHECK 는 0~1억**(설계는 ≥0) — 기록 금액의 입력 경계와 맞췄다. `PUT /menus/{id}`의 `price`는 빠지면 가격 미정이다(④ 이전 앱이 그대로 불러도 된다).
+- **프로필 사진은 조회 응답 셋에만.** 목록·고객 상세·반려동물 상세(GET)에 `photo`가 있고 쓰기 응답(`PetDetailSchema`·`CustomerDetailSchema`)에는 없다 — 쓰기 뒤 다시 읽는 규칙(③)이라 쓰기 인터랙터 일곱에 포트를 더하지 않았다. 프로필 사진은 "사진이 붙은 가장 최근 완료 방문의 대표"다(가장 최근 완료 기록에 사진이 없으면 그 전 것).
+
+### 이 계획에서 새로 정한 것
+
+- 기록 버전(`visit_records.version`)과 409 `RECORD_VERSION_CONFLICT`, 덧붙이기 API — 업로드 대기열 결정(2026-09-24)에 따라 설계 문서에 먼저 더했다.
+- 덧붙이기는 그 칸을 순서대로 0부터 다시 매기고 맨 뒤에 붙인다 — 빼고 붙이기를 거듭해도 순서 상한(99)에 닿지 않는다. 같은 칸·같은 순서는 유일 색인(`uq_visit_record_media_order`)이 막는다.
+- 보관한 메뉴도 기록 항목에 적을 수 있다(`MenuRepository.list_by_ids`) — 옛 기록을 고칠 때 막히지 않게.
+- 돈 칸의 403 은 잠그기 전에 판정한다(권한은 방문과 상관없다).
+- 기록 여러 개는 `VisitRecordRepository.list_many`가 방문 수와 상관없이 질의 셋으로 읽는다(상세·하루·달력·피드·프로필 사진). 피드는 방문 리포지토리의 여섯째 축 `VisitFeedRepository`다(`test_visit_port_segregation.py`의 포트 목록에 더했다).
+- 정리 스크립트는 객체마다 행을 pending 으로 되돌려 커밋한 뒤(그사이 기록이 가져가지 못한다) 저장소에서 지우고 행을 지운다. 중간에 멈추면 행이 오래된 pending 으로 남아 다음 실행이 잡는다.
+- 통합 테스트는 MinIO 를 쓴다(compose `backend`가 `minio`에 기댄다, 픽스처 `media_storage`).
+
+### 남는 것 — 알고 미룬다
+
+- 확인(confirm)과 정리가 같은 오래된 pending 객체에 동시에 닿으면, 정리가 저장소에서 지운 뒤 확인이 ready 로 바꿀 수 있다(하루 넘게 확인하지 않은 객체를 그 순간 다시 확인하는 경우뿐). 앱의 대기열은 URL 이 만료되면 발급부터 다시 하므로 부딪힐 일이 드물다.
+- 서명 URL 은 경로 방식이다. 운영 S3 에서 가상 호스트 방식이 필요해지면 `sigv4_query`와 boto3 설정을 함께 바꾼다.
+- 밤 22시 반 이후에는 `test_visit_flow_wiring.py::test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다`가 실패한다(걷기 손님 기본 90분이 자정을 넘긴다). ③부터 있던 시각 의존 테스트이고 이 계획이 건드리지 않았다. 새 기록 테스트는 어제 11시 예약을 시작해 시각과 상관없이 돈다.
+
```

`_docs/harness.md`:

```diff
@@ -15,6 +15,9 @@
 | 고객·반려동물 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_customer_flow.sh` — 개발 DB에 확인용 매장·유저와 익명화한 고객이 남는다 |
 | 고객 검색 줄 재생성 | `docker compose run --rm backend python scripts/rebuild_customer_search.py` (검색 줄이 원본과 어긋났을 때) |
 | 예약·방문 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_visit_flow.sh` — 개발 DB에 확인용 매장·유저·고객·방문이 남는다 |
+| 미디어 버킷 준비 | `docker compose run --rm backend python scripts/ensure_media_bucket.py` (버킷 생성 + 원본 수명주기 규칙. MinIO 는 계층 이동을 받지 않아 규칙을 건너뛴다) |
+| 사진·기록 흐름 (게이트웨이·MinIO 경유) | `bash ../backend/scripts/check_media_flow.sh` — 버킷 준비 뒤. 서명 URL 로 저장소에 바로 올리고 읽는다. 개발 DB·버킷에 확인용 매장·사진이 남는다 |
+| 미디어 정리 | `docker compose run --rm backend python scripts/purge_stale_media.py` (하루 넘게 어느 기록도 가져가지 않은 사진·영상 — 운영은 주기적으로) |
 | 최근 방문순 키 복구 | `docker compose run --rm backend python scripts/rebuild_last_visit.py` (고객 목록 '최근 방문순'이 방문 기록과 어긋났을 때) |
 | 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
 | 앱 정적 분석 | `flutter analyze` (`app/`에서, 경고 0) |
@@ -36,5 +39,6 @@
 - 허브 포트 자리를 새로 만들어도 더할 목록은 없다. `tests/route_inspection.py`가 두 앱의 라우트 의존성 트리를 훑어 ① 채우지 않은 허브 포트 자리 ② `{shop_id}` 경로인데 `get_shop_context`를 거치지 않는 라우트 ③ `/v1/platform/` 경로인데 `require_operator`를 거치지 않는 라우트를 잡는다. API 프로세스는 `tests/test_hub_port_binding.py`가, 인증 프로세스는 `tests/integration/test_route_wiring.py`가 돌린다.
 - 권한이나 불변식이 걸린 슬라이스를 계획할 때는 악의적이거나 운 나쁜 시나리오(내보내진 사람이 쥔 것, 같은 요청이 동시에 두 번, 읽기와 쓰기 사이)를 먼저 표로 적고, 각각을 막는 코드와 테스트를 작업에 넣는다. 작업별 검토는 계획서와의 일치가 아니라 그 표를 기준으로 한다.
 - 통합 테스트에서 두 번째 로그인 수단이 필요하면 `fake_kakao` 픽스처를 쓴다.
+- 통합 테스트는 compose 의 MinIO 도 쓴다(`backend` 서비스가 `minio`에 기댄다). 미디어가 필요한 테스트는 `media_storage` 픽스처를 쓴다 — 테스트 버킷 `chagocnote-test`를 시작 때 비우고(테스트마다 DB ID 가 1부터라 키가 겹친다), 컨테이너 안에서 서명 URL 로 PUT 하도록 공개 주소를 내부 주소로 둔다. 사진 하나를 확인까지 마치는 도우미는 `tests/integration/support.py`의 `ready_photo`다.
 - 마이그레이션에 시드 표를 새로 만들면 루트 `conftest.py`의 `_KEEP_TABLES`에 더한다. 빠뜨리면 첫 테스트가 시드를 비워 그다음 테스트부터 실패한다.
 - 두 세션 경합 테스트는 막힌 호출을 `asyncio.create_task`로 들고 있다가 앞선 세션이 커밋한 뒤의 결과를 본다. "기다렸다"만으로 판별하지 않는다 — 외래 키의 암묵적 잠금이나 같은 행의 다른 잠금 때문에 잠금 코드가 없어도 기다릴 수 있다. 잠금 코드를 빼는 변이로 테스트가 실패하는지 확인한다.
```

`backend/apps/customer/_docs/CLAUDE.md`:

```diff
@@ -14,4 +14,6 @@
 - 고객 삭제는 익명화다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행을 지우고 `deleted_at`을 찍는다. 행과 틀(종류·품종·성별 등)은 남긴다. 익명화한 고객은 모든 조회·검색·번호 조회에서 없는 것으로 본다.
 - 반려동물은 질병을 하나 이상 고르거나 "질병 없음"을 직접 확인해야 저장된다(두 표에 걸친 규칙이라 도메인이 확인한다). 질병 종류는 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다.
 - 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각·카톡 초안 후보). 초안 후보(`find_draft_candidates`)는 낱말 하나라도 걸리는 가족(`CustomerSearchPort.match_any`, OR)을 읽어 반려동물 이름 정확 일치 → 보호자 이름 → 전화 → 부분 일치 순으로 최대 5 가족만 돌려주고, 낱말을 저장하거나 로그에 남기지 않는다. `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
+- 반려동물 프로필 사진은 저장하지 않는다. 조회 셋(목록 `pets[].photo`, 고객 상세 `pets[].photo`, 반려동물 상세 `pet.photo`)이 읽을 때마다 `VisitLedgerPort.latest_covers`(대표 사진의 media_id)와 `MediaLibraryPort.read_urls`(썸네일 URL)로 한 번씩 묻는다(`app/services/pet_photos.py`, N+1 없음). 쓰기 응답에는 사진이 없다 — 쓰기 뒤 다시 읽는다. `MediaLibraryPort`는 `dependencies/hub_ports.py`의 자리로 받는다.
+- 익명화는 visit 이 방문 메모와 미용 기록의 두 메모(케어·내부)를 비우고, 사진은 매장의 기록이라 남긴다. 미용 기록의 몸무게는 visit 이 `CustomerDirectoryPort.set_pet_weight`로 알려 준다(가장 최근 기록일 때만) — 고객 행을 잠근 트랜잭션 안이다.
 - 검색 줄의 `last_visit_at`(최근 방문순)은 원본이 visits 다 — 검색 줄을 다시 만들 때 건드리지 않고, visit 이 `set_last_visit`로 알려 준다.
```

`backend/apps/hub/_docs/CLAUDE.md`:

```diff
@@ -17,5 +17,6 @@
 | `UserDirectoryPort.get_profiles(user_ids) → dict[int, UserProfile]` | auth `get_user_profiles` | tenancy `list_members` |
 | `ActiveUserGuardPort.lock_active(user_id) → bool` | auth `guard_active_user` | tenancy `accept_invite` |
 | `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy `apply_withdrawal` | auth `withdraw` (인증 프로세스) |
-| `CustomerDirectoryPort.lock_family · briefs · set_last_visit · find_draft_candidates(ctx, words) → list[DraftCandidate]` | customer `customer_directory` | visit (방문 쓰기의 가족 잠금, 이름 표시, 최근 방문순, 카톡 초안 후보) |
-| `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세) |
+| `CustomerDirectoryPort.lock_family · briefs · set_last_visit · set_pet_weight · find_draft_candidates(ctx, words) → list[DraftCandidate]` | customer `customer_directory` | visit (방문 쓰기의 가족 잠금, 이름 표시, 최근 방문순, 기록의 몸무게, 카톡 초안 후보) |
+| `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기·`latest_covers`) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세, 반려동물 프로필 사진) |
+| `MediaLibraryPort.claim(ctx, ids) → {id: kind} · release · read_urls(ctx, ids) → {id: MediaUrls}` | media `media_library` | visit (기록의 사진·영상), customer (프로필 사진) |
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -1,17 +1,23 @@
-# visit — 방문(예약부터 완료까지), 매장 일정, 메뉴표
+# visit — 방문(예약부터 완료까지), 미용 기록, 매장 일정, 메뉴표
 
-소유 데이터: `visits`, `visit_menus`, `visit_shop_settings`, `visit_weekly_closures`, `visit_closed_dates`, `service_menus`.
+소유 데이터: `visits`, `visit_menus`, `visit_records`, `visit_record_items`, `visit_record_media`, `visit_shop_settings`, `visit_weekly_closures`, `visit_closed_dates`, `service_menus`.
 
 - 방문 하나는 반려동물 한 마리의 방문이다. `pet_id`가 NULL 이면 보호자만의 방문이다. 두 마리를 한 번에 잡으면 방문이 둘이고, 같은 보호자 + 같은 시작 시각이 가족 묶음이다(저장하지 않고 계산한다).
 - `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
 - 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK). **상태 이름과 성질(살아 있음·마릿수·시작 시각)의 단일 원천은 `domain/state/visit_status.py`의 표다** — `ACTIVE_STATUSES`·`COUNTED_STATUSES`·ORM CHECK·부분 색인·하루 집계 칸이 거기서 파생한다. 상태를 더하면 표에 한 줄, `visit_state.py`에 상태 클래스 하나, `DayCountsView`에 칸 하나, 그리고 새 마이그레이션이다(`test_schema_drift`는 CHECK·부분 색인을 보지 않는다 — `tests/integration/test_visit_status_schema.py`가 실제 DB 와 표를 대조해 알려 준다).
 - 행동(시작·완료·취소·노쇼·되돌리기)은 `visit_state.ACTIONS`와 바탕 상태 클래스의 같은 이름 메서드가 정한다. `transition()`은 행동 이름으로 메서드를 찾으므로 행동을 더할 때 if 체인을 늘리지 않는다. 시간을 다시 차지하는 행동(`SLOT_RECLAIMING_ACTIONS`)만 가족 확인에 반려동물을 넘긴다(`pets_to_confirm`). 완료가 생기거나 풀린 뒤의 후속 처리는 `app/services/completion_effects.py` 한 곳이다 — 전이·기록(④) 유스케이스가 같은 함수를 부른다.
 - **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
-- `visits` 표의 리포지토리는 포트 다섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository`), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
+- `visits` 표의 리포지토리는 포트 여섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository`), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`), 피드(`VisitFeedRepository` — 완료 시각 순). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
 - customer 는 반대 방향 허브 포트 `VisitLedgerPort`(이 스포크 구현, `app/use_cases/visit_ledger_interactor.py`)로 방문을 묻는다. '앞으로의 예약'은 예약됨·미용 중인 방문이다(날짜가 지났어도).
 - 같은 아이(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약은 하나다(부분 유일 색인 — 409 `VISIT_DUPLICATE`, 세이브포인트라 트랜잭션은 계속 쓴다).
 - 겹침·휴무·영업시간 밖은 **막지 않는 경고**다. 판단은 `domain/services/visit_schedule.warnings_for` 한 곳에만 있다.
 - "오늘"과 하루의 경계는 매장 시간대(`ShopContext.timezone`)로 센다. 요청 시각은 시간대가 붙어 와야 하고, 응답 시각은 매장 시간대로 나간다.
 - 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각을 `CustomerDirectoryPort.set_last_visit`로 같은 트랜잭션에서 넘긴다(고객 목록 '최근 방문순'). 어긋나면 `scripts/rebuild_last_visit.py`로 복구한다.
+- **미용 기록**(④)은 방문 하나에 하나다(`visit_records` — 몸무게·케어 메모(공개, ⑤ 알림장)·내부 메모·결제 수단·총액(받은 돈, 항목 합과 별개)·실제 메뉴와 금액·사진영상). 미용 중·완료 방문에만 쓴다(409 `VISIT_NO_RECORD_YET`, 판정은 `domain/services/visit_record_rules.py`). 쓰기 셋 — 전체 교체(`PUT …/record`), 사진 하나 덧붙이기(`POST …/record/media`, 그 칸 맨 뒤·빈 기록 생성·같은 미디어 멱등), 삭제(`DELETE …/record`, record:delete) — 모두 방문 쓰기와 같은 잠금(고객 행 → 방문 행)을 거친다. 돈 칸(총액·항목·결제 수단)은 sales:write 다.
+- **기록 버전.** 기록을 바꿀 때마다 `version`이 오른다. 전체 교체는 읽은 버전을 보내야 하고(없으면 보내지 않는다) 다르면 409 `RECORD_VERSION_CONFLICT` — 앱의 업로드 대기열이 덧붙인 사진을 폼 저장이 모르고 지우지 않게 한다. 덧붙이기는 버전을 받지 않고 올린다.
+- 기록의 사진·영상은 media 의 허브 포트 `MediaLibraryPort`로 가져가고(claim) 놓는다(release) — 둘 다 조건부 UPDATE 라 잠금 안에서 부른다. 놓인 미디어는 media 의 정리 스크립트가 하루 뒤 지운다. `visit_record_media.kind`는 가져가기가 알려 준 값(바뀌지 않는 사실)이다 — 대표 사진(후 → 전 → 영상 포스터, `cover_media_id`)과 한도(사진 30·영상 3)를 이 표만으로 계산한다. 읽기 URL 은 `read_urls`로 받는다(`app/services/record_reader.py`·`cover_reader.py`).
+- 기록에 몸무게를 적으면 그 방문이 그 아이의 가장 최근 시작한 방문일 때만 `CustomerDirectoryPort.set_pet_weight`로 현재 몸무게를 넘긴다(`completion_effects.sync_pet_weight`). 옛 기록을 고쳐도 현재 값은 그대로다.
+- 방문 상세는 기록 전체와 대표 사진, 하루 목록은 `has_record`·`cover`, 달력은 날마다 완료 방문의 `cover`·`covers`(최대 4), 피드(`GET /visits/feed`)는 완료 방문을 완료 시각 역순 커서로 준다. 기록 여러 개는 `VisitRecordRepository.list_many`로 방문 수와 상관없이 한 번에 읽는다.
+- customer 에 `VisitLedgerPort.latest_covers`(사진이 붙은 가장 최근 완료 방문의 대표 — 반려동물 프로필 사진)를 준다. 익명화(`clear_customer_memos`)는 방문 메모와 기록의 두 메모를 비우고 사진은 남긴다.
 - 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
 - 카톡 예약 초안(`POST /visit-drafts`)은 **아무것도 저장하지 않는다.** 글은 `app/ports/output/visit_draft_parser_port.py` 뒤의 규칙 어댑터(`adapter/outbound/rule_draft_parser_adapter.py` → `domain/services/draft_parser.py`)가 날짜·시각·메뉴·낱말로 읽고, "누구"는 허브 포트 `CustomerDirectoryPort.find_draft_candidates`가 낱말로 찾는다(최대 5 가족). 글과 낱말을 로그·DB·오류 응답에 남기지 않는다(설계 10절 V9). ⑨ 이후 LLM 해석은 같은 포트 뒤에서 어댑터만 바꾼다.
```

- [ ] **Step 2: 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 882 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 299 passed (밤 22시 반 이후면 기존 시각 의존 테스트 하나가 더 실패한다 — Global Constraints)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

Run (`infra/`): `docker compose run --rm --no-deps auth python scripts/print_routes.py` → 작업 1 전에 받아 둔 표와 `diff` 해서 늘어난 줄이 일곱뿐이다(`GET …/media/myself`, `POST …/media/uploads`, `POST …/media/{media_id}/confirm`, `GET …/visits/feed`, `PUT`·`DELETE …/visits/{visit_id}/record`, `POST …/visits/{visit_id}/record/media`)

Run: `ls -l backend/apps/media/CLAUDE.md` → `_docs/CLAUDE.md`를 가리킨다

- [ ] **Step 3: 커밋한다**

```bash
git add -A
git commit -m "docs: ④-1 백엔드의 규칙과 결정 — media 스포크 문서, visit·customer·hub 문서, 하네스(버킷·흐름·정리·MinIO 통합 테스트), 결정 기록 007(④-1 절)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---
