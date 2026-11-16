# CLAUDE.md — 차곡노트

반려동물 미용 매장과 보호자를 잇는 플랫폼이다. 에이전트는 코드·설정·명령을 제안하거나 실행하기 전에 이 문서를 먼저 읽는다.

## 언어

- 항상 한국어로 응답한다. 주석·문서·테스트 이름·커밋 메시지도 한국어다.

## 저장소

| 영역 | 스택 | 위치 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic | `backend/` |
| 앱 | Flutter 3.41 이상 | `app/` |
| 웹 (보호자 알림장·내 기록) | Next.js 16 (App Router) · TypeScript · pnpm | `web/` |
| 임베딩 프로세스 (기록 검색의 뜻 검색) | Python · ONNX 런타임(CPU) · multilingual-e5-small | `embed/` |
| 개발 환경 | Docker Compose (pgvector · redis · minio · backend · auth · embed · gateway · web) | `infra/` |
| 설계·계획 | 서브 프로젝트별 문서 | `docs/superpowers/` |

먼저 읽을 문서: `_docs/architecture.md`(계층·슬라이스·폴더 작명 규칙), `_docs/harness.md`(검증 명령). 앱 폴더에서 작업할 때는 그 앱의 `CLAUDE.md`도 읽는다. 웹 폴더에서 작업할 때는 `web/CLAUDE.md`를 읽는다.

## 꼭 지킬 것

- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 코드·패키지명·문서에서 플랫폼 이름으로 쓰지 않는다.
- 스포크끼리 직접 import하지 않는다. 교차 협력은 `apps/hub`의 포트를 거친다. 허브는 스포크를 모른다.
- 스포크의 `dependencies/`도 다른 스포크를 import하지 않는다. 다른 스포크가 구현한 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
- 매장 범위의 경로는 `core/shop_guard.py`의 `get_shop_context` 또는 `require_permission`으로 `ShopContext`를 받는다. 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.
- 로그인 없이 열리는 경로는 `backend/tests/route_inspection.py`의 허용 목록과 프로세스별 목록 테스트에 있는 것뿐이다. 공개 응답 스키마는 매장용과 따로 쓰고 칸을 하나하나 적는다.
- 알림장 토큰은 헤더(`X-Report-Token`)로, 서류(동의서) 토큰은 헤더(`X-Form-Token`)로 받고 로그·문서·커밋에 남기지 않는다. 두 토큰은 서로의 경로에서 읽히지 않는다(`core/link_token.py`의 purpose).
- 웹(`web/`)은 토큰(알림장·세션)·쿠키 값·서명 주소·비밀값을 로그에 찍지 않는다. 보호자의 브라우저는 백엔드를 직접 부르지 않는다 — 웹 서버가 부른다.
- 가드 없이 `ShopContext`를 만드는 곳은 `hub/app/dtos/shop_context.py`의 둘뿐이다. 매장 멤버가 아닌 요청 경로(로그인 없는 공개 알림장·공개 서류, 로그인한 보호자의 읽기)에서는 `public_context`, 요청 밖(알림 디스패처·검색 색인기·서류 청소·운영자 스크립트)에서는 `system_context`. 둘 다 권한이 비어 있다. `public_context`는 포트 읽기와 **공개 서류 제출이 쓰는 표**(`customer_forms`·`consent_signatures`와 그 아래 표, 서명이 찍는 `pets`의 동의 칸 셋, 받은 문진표 `intake_answers`와 그 아래 표)에만 쓰고 고객·반려동물의 다른 칸은 쓰지 않는다. `system_context`는 포트 읽기(와 자기 스포크의 표 — 알림 표·검색 표·기한이 지난 받은 문진표 — 쓰기)에만 쓴다.
- 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있고 인증 프로세스(`auth_main.py`)만 읽는다. 이 모듈은 함수 안에서만 import한다. API 프로세스 경로에서 import하지 않는다.
- 보호자 경로(`/v1/me/guardian/…`)는 `core/guardian_guard.py`의 `get_guardian_context`로 `GuardianContext`를 받는다. `guardian` 스포크는 `ShopContext`를 만들지 않고 고객·반려동물을 읽지 않는다. 보호자용 응답은 공개 알림장과 같은 스키마를 쓰고, 매장용 응답에 보호자가 누구인지 싣지 않는다.
- 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행 → 보호자 연결 행이다(잇기·탈퇴). 고객 익명화는 고객 행 → 보호자 연결 행이다. 서류 쪽은 고객 행 → 서류 요청 행이다. 고객·방문 쪽은 고객 행 → 방문 행(ID 오름차순) → 알림 행이다 — 방문을 쓰는 유스케이스는 허브 포트 `CustomerDirectoryPort.lock_family`로 고객 행부터 잠그고, 알림 줄은 그 트랜잭션 안의 이벤트 구독자가 끝에 쓴다. 검색 쪽은 고객 행 → 검색 표다 — 색인기는 `lock_family`로 고객 행을 잠근 뒤 원본을 다시 읽어 같을 때만 검색 문서를 쓴다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다(디스패처는 줄을 집어 커밋한 뒤 업체를 부르고, 색인기는 트랜잭션을 닫은 뒤 임베딩 프로세스를 부른다).
- 발송 업체 API 키(`SOLAPI_*`)·전화번호·알림장 주소·`variables`·업체 응답 본문을 로그·오류 메시지·API 응답에 남기지 않는다. 로그는 message_id·매장·종류·결과만이다.
- **검색어·걸린 문장(snippet)·검색 문서의 글·벡터를 로그·오류 메시지·예외 문자열·API 오류 응답에 남기지 않는다.** 로그는 shop_id·대상(scope·ref_id)·건수·걸린 시간·예외의 형 이름뿐이다. 임베딩 프로세스(`embed`)는 게이트웨이에 싣지 않고 compose 내부망에서만 부른다. 매장의 글을 밖(외부 API)으로 보내지 않는다.
- 검색되는 글에 닿는 쓰기(기록 저장·삭제, 방문 등록·수정·옮기기, 고객·반려동물 등록·수정·삭제)는 허브 이벤트 `SearchSourceChanged`를 낸다. 고객 익명화는 이벤트 대신 `SearchIndexPort.forget_customer`를 그 트랜잭션에서 부른다. 그런 글을 쓰는 유스케이스를 새로 만들면 둘 중 하나를 한다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `core/singleton/secret_manager.py`에서만 쓴다.
- 비밀값을 로그·커밋·문서에 남기지 않는다. `.env*` 파일 내용을 그대로 출력하지 않는다.
- 커밋과 푸시는 사용자가 요청할 때만 한다. CI(GitHub Actions, `.github/workflows/`)는 푸시마다 바뀐 영역의 테스트·import-linter·analyze·빌드를 돈다. 골든·e2e·흐름·라우트 표는 CI가 보지 않으니 로컬에서 확인한다.
- 볼륨 삭제, `docker compose down -v`, 스키마를 파괴하는 명령은 사용자 확인 없이 실행하지 않는다.

## 명령어

백엔드는 전부 `infra/`에서 실행한다. 맥에 파이썬 환경을 만들지 않는다.

    docker compose up -d                          # 전체 기동 (게이트웨이 http://127.0.0.1:8080)
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
    docker compose run --rm --no-deps backend lint-imports --config .importlinter
    docker compose run --rm --no-deps auth python scripts/print_routes.py      # 개인키가 필요해서 auth 서비스에서 돌린다
    docker compose run --rm backend python scripts/grant_operator.py <user_id>   # 플랫폼 운영자 지정 (user_id 는 GET /v1/me 의 id)
    bash ../backend/scripts/check_notification_flow.sh                           # 알림톡 흐름 확인 (dev 는 가짜 게이트웨이, 실제 발송 없음)
    bash ../backend/scripts/check_guardian_flow.sh                               # 보호자 회원 흐름 확인 (웹 세션 로그인 → 잇기 → 지난 알림장 → 끊기)
    bash ../backend/scripts/check_sales_flow.sh                                  # 매출 통계 흐름 확인 (방문 몇 개 → 요약의 숫자를 손계산과 견준다 → 목록 → 목표)
    bash ../backend/scripts/check_consent_flow.sh                                # 전자 동의서 흐름 확인 (보내기 → 로그인 없이 읽고 서명 → 지병 더하기 → 바뀐 토막만 → 현장 서명 → 끊기 → 서류 설정·글 고치기·보낼 것 묶음 → 익명화)
    bash ../backend/scripts/check_visit_checks_flow.sh                           # 확인할 것 흐름 확인 (노령·지병 아이 예약 → 동의 → 지병 더하기 → 노쇼·주의 → 미리 보기 → 막지 않음)
    docker compose run --rm backend python scripts/reregister_templates.py [--shop <id>] [--refresh]   # 알림톡 템플릿 재등록 / 심사 상태 조회
    bash ../backend/scripts/check_intake_flow.sh                                 # 첫 방문 문진표 흐름 확인 (보내기 → 로그인 없이 적어 내기 → 받은 문진표 → 등록 → 새 아이 → 다시 받기 → 칸 끄기·질문 → 끊기 → 익명화)
    bash ../backend/scripts/check_intake_consent_flow.sh                         # 문진표 끝의 동의서 흐름 확인 (서명 없이 422 → 글이 바뀌면 409 → 서명과 함께 냄 → 지병을 더해 등록 → 지병 토막만 남음 → 모든 아이에게)
    bash ../backend/scripts/check_search_flow.sh                                 # 기록 검색 흐름 확인 (적기 → 글자·뜻으로 찾기 → 지우기 → 익명화 → 다른 매장 → embed 멈춤)
    docker compose run --rm backend python scripts/check_search_quality.py [--verbose]            # 기록 검색 품질 확인 (실제 모델, 질문 30개 중 24개 이상)
    docker compose run --rm backend python scripts/reindex_search.py [--shop <id>] [--purge-orphans]   # 검색 문서를 원본에 다시 맞춘다 (처음 채우기·모델 교체·어긋남)
    docker compose run --rm --no-deps embed pytest -q                            # 임베딩 프로세스의 테스트 (이미지에 든 실제 모델)

앱은 전부 `app/`에서 실행한다.

    flutter analyze                               # 경고 0
    flutter test                                  # 골든 포함
    app/tool/run_dev.sh                           # 개발용 실행 (APP_ENV=dev, 게이트웨이 http://127.0.0.1:8080)

웹은 `web/`에서 맥의 node·pnpm 으로 실행한다(`pnpm install` 먼저). 개발 서버는 compose 의 `web` 서비스다(`infra/`의 `docker compose up -d`가 함께 띄운다, http://127.0.0.1:3010).

    pnpm test                                     # 컴포넌트·단위 (Vitest)
    pnpm build                                    # 빌드와 형 검사
    pnpm check:server                             # 빌드 뒤. 가짜 백엔드 + next start 로 상태 코드·헤더·첫 HTML·백엔드 호출 수
    pnpm e2e:prepare && pnpm e2e                  # 실제 브라우저 (compose 의 개발 스택과 web 이 떠 있어야 한다)
