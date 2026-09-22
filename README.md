# 차곡노트

반려동물 미용 매장과 보호자를 잇는 플랫폼이다. 매장은 예약·고객·미용 기록을 관리하고, 보호자는 매장이 보낸 미용 알림장을 받아 본다. 이름은 기록이 "차곡차곡" 쌓인다는 뜻이다.

| 영역 | 스택 | 위치 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic | `backend/` |
| 앱 | Flutter 3.41 이상 | `app/` |
| 개발 환경 | Docker Compose (pgvector · redis · minio · backend · auth · gateway) | `infra/` |
| 설계·계획 | 서브 프로젝트별 문서 | `docs/superpowers/` |

## 처음 띄우기

    cd infra
    docker compose build backend
    docker compose run --rm --no-deps backend python scripts/generate_dev_env.py   # .env 와 .env.auth 를 만든다 (이미 있으면 건너뛴다)
    docker compose up -d                                                            # 게이트웨이 http://127.0.0.1:8080
    bash ../backend/scripts/check_auth_flow.sh                                      # 로그인 흐름 확인
    bash ../backend/scripts/check_shop_flow.sh                                      # 매장 개설·합류 흐름 확인
    bash ../backend/scripts/check_account_flow.sh                                   # 회원 탈퇴 흐름 확인
    bash ../backend/scripts/check_customer_flow.sh                                  # 고객·반려동물 흐름 확인

개발 환경에서는 제공자 `dev`로 이름만 넣어 로그인한다. 운영자는 `docker compose run --rm backend python scripts/grant_operator.py <user_id>`로 지정한다.

백엔드가 떠 있으면 `app/tool/run_dev.sh`로 앱을 켠다(iOS 시뮬레이터 기준, `app/CLAUDE.md` 참고).

## 더 읽을 것

- `CLAUDE.md` — 꼭 지킬 규칙과 명령어
- `app/CLAUDE.md` — 앱에만 해당하는 규칙과 명령어
- `_docs/architecture.md` — 계층, 수직 슬라이스, 허브-스포크, 허브 포트 조립, 폴더 작명 규칙
- `_docs/harness.md` — 검증 명령
- `_docs/decisions/` — 결정 기록
- `docs/superpowers/specs/` · `docs/superpowers/plans/` — 설계 문서와 구현 계획
