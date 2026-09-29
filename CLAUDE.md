# CLAUDE.md — 차곡노트

반려동물 미용 매장과 보호자를 잇는 플랫폼이다. 에이전트는 코드·설정·명령을 제안하거나 실행하기 전에 이 문서를 먼저 읽는다.

## 언어

- 항상 한국어로 응답한다. 주석·문서·테스트 이름·커밋 메시지도 한국어다.

## 저장소

| 영역 | 스택 | 위치 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic | `backend/` |
| 앱 | Flutter 3.41 이상 | `app/` |
| 웹 (보호자 알림장) | Next.js 16 (App Router) · TypeScript · pnpm | `web/` |
| 개발 환경 | Docker Compose (pgvector · redis · minio · backend · auth · gateway · web) | `infra/` |
| 설계·계획 | 서브 프로젝트별 문서 | `docs/superpowers/` |

먼저 읽을 문서: `_docs/architecture.md`(계층·슬라이스·폴더 작명 규칙), `_docs/harness.md`(검증 명령). 앱 폴더에서 작업할 때는 그 앱의 `CLAUDE.md`도 읽는다. 웹 폴더에서 작업할 때는 `web/CLAUDE.md`를 읽는다.

## 꼭 지킬 것

- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 코드·패키지명·문서에서 플랫폼 이름으로 쓰지 않는다.
- 스포크끼리 직접 import하지 않는다. 교차 협력은 `apps/hub`의 포트를 거친다. 허브는 스포크를 모른다.
- 스포크의 `dependencies/`도 다른 스포크를 import하지 않는다. 다른 스포크가 구현한 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
- 매장 범위의 경로는 `core/shop_guard.py`의 `get_shop_context` 또는 `require_permission`으로 `ShopContext`를 받는다. 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.
- 로그인 없이 열리는 경로는 `backend/tests/route_inspection.py`의 허용 목록과 프로세스별 목록 테스트에 있는 것뿐이다. 공개 응답 스키마는 매장용과 따로 쓰고 칸을 하나하나 적는다.
- 알림장 토큰은 헤더(`X-Report-Token`)로 받고 로그·문서·커밋에 남기지 않는다.
- 웹(`web/`)은 토큰·서명 주소·비밀값을 로그에 찍지 않는다. 보호자의 브라우저는 백엔드를 직접 부르지 않는다 — 웹 서버가 부른다.
- 로그인 없는 요청 경로에서 `ShopContext`를 가드 없이 만드는 곳은 `visit/app/services/public_context.py` 하나다. 권한이 비어 있고 읽기에만 쓴다.
- 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있고 인증 프로세스(`auth_main.py`)만 읽는다. 이 모듈은 함수 안에서만 import한다. API 프로세스 경로에서 import하지 않는다.
- 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. 고객·방문 쪽은 고객 행 → 방문 행(ID 오름차순)이다 — 방문을 쓰는 유스케이스는 허브 포트 `CustomerDirectoryPort.lock_family`로 고객 행부터 잠근다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `core/singleton/secret_manager.py`에서만 쓴다.
- 비밀값을 로그·커밋·문서에 남기지 않는다. `.env*` 파일 내용을 그대로 출력하지 않는다.
- 커밋과 푸시는 사용자가 요청할 때만 한다. CI는 없다. 검증은 로컬에서 한다.
- 볼륨 삭제, `docker compose down -v`, 스키마를 파괴하는 명령은 사용자 확인 없이 실행하지 않는다.

## 명령어

백엔드는 전부 `infra/`에서 실행한다. 맥에 파이썬 환경을 만들지 않는다.

    docker compose up -d                          # 전체 기동 (게이트웨이 http://127.0.0.1:8080)
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
    docker compose run --rm --no-deps backend lint-imports --config .importlinter
    docker compose run --rm --no-deps auth python scripts/print_routes.py      # 개인키가 필요해서 auth 서비스에서 돌린다
    docker compose run --rm backend python scripts/grant_operator.py <user_id>   # 플랫폼 운영자 지정 (user_id 는 GET /v1/me 의 id)

앱은 전부 `app/`에서 실행한다.

    flutter analyze                               # 경고 0
    flutter test                                  # 골든 포함
    app/tool/run_dev.sh                           # 개발용 실행 (APP_ENV=dev, 게이트웨이 http://127.0.0.1:8080)

웹은 `web/`에서 맥의 node·pnpm 으로 실행한다(`pnpm install` 먼저). 개발 서버는 compose 의 `web` 서비스다(`infra/`의 `docker compose up -d`가 함께 띄운다, http://127.0.0.1:3010).

    pnpm test                                     # 컴포넌트·단위 (Vitest)
    pnpm build                                    # 빌드와 형 검사
    pnpm check:server                             # 빌드 뒤. 가짜 백엔드 + next start 로 상태 코드·헤더·첫 HTML·백엔드 호출 수
    pnpm e2e:prepare && pnpm e2e                  # 실제 브라우저 (compose 의 개발 스택과 web 이 떠 있어야 한다)
