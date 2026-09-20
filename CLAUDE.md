# CLAUDE.md — 차곡노트

반려동물 미용 매장과 보호자를 잇는 플랫폼이다. 에이전트는 코드·설정·명령을 제안하거나 실행하기 전에 이 문서를 먼저 읽는다.

## 언어

- 항상 한국어로 응답한다. 주석·문서·테스트 이름·커밋 메시지도 한국어다.

## 저장소

| 영역 | 스택 | 위치 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic | `backend/` |
| 앱 | Flutter 3.41 이상 | `app/` |
| 개발 환경 | Docker Compose (pgvector · redis · minio · backend · auth · gateway) | `infra/` |
| 설계·계획 | 서브 프로젝트별 문서 | `docs/superpowers/` |

먼저 읽을 문서: `_docs/architecture.md`(계층·슬라이스·폴더 작명 규칙), `_docs/harness.md`(검증 명령). 앱 폴더에서 작업할 때는 그 앱의 `CLAUDE.md`도 읽는다.

## 꼭 지킬 것

- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 코드·패키지명·문서에서 플랫폼 이름으로 쓰지 않는다.
- 스포크끼리 직접 import하지 않는다. 교차 협력은 `apps/hub`의 포트를 거친다. 허브는 스포크를 모른다.
- JWT 개인키는 인증 프로세스(`auth_main.py`)만 가진다. `core/auth_config.py`를 API 프로세스 경로에서 import하지 않는다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `core/singleton/secret_manager.py`에서만 쓴다.
- 비밀값을 로그·커밋·문서에 남기지 않는다. `.env*` 파일 내용을 그대로 출력하지 않는다.
- 커밋과 푸시는 사용자가 요청할 때만 한다. CI는 없다. 검증은 로컬에서 한다.
- 볼륨 삭제, `docker compose down -v`, 스키마를 파괴하는 명령은 사용자 확인 없이 실행하지 않는다.

## 명령어

전부 `infra/`에서 실행한다. 맥에 파이썬 환경을 만들지 않는다.

    docker compose up -d                          # 전체 기동 (게이트웨이 http://127.0.0.1:8080)
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
    docker compose run --rm --no-deps backend lint-imports --config .importlinter
    docker compose run --rm --no-deps auth python scripts/print_routes.py      # 개인키가 필요해서 auth 서비스에서 돌린다
