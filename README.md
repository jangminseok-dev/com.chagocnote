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
    bash ../backend/scripts/check_report_flow.sh                                    # 알림장 흐름 확인 (버킷 준비 뒤 — _docs/harness.md)

`REPORT_LINK_KEY_B64`(알림장 링크의 서명 키, 32바이트 이상을 base64 로)는 필수다. 없으면 API 프로세스와 인증 프로세스가 둘 다 기동하지 않는다. `generate_dev_env.py`는 `.env`가 이미 있으면 아무것도 하지 않으므로, ⑤ 이전에 만든 개발 환경은 한 줄을 직접 더한다. 먼저 `.env`가 줄바꿈으로 끝나는지 본다(끝나지 않으면 앞 줄에 붙는다). 아래 명령은 값을 출력하지 않고, 이미 있으면 아무것도 하지 않는다. 키를 바꾸면 보낸 링크가 모두 닫힌다.

    docker compose run --rm --no-deps backend python -c "
    import base64, secrets
    from pathlib import Path
    env = Path('/work/.env')
    if 'REPORT_LINK_KEY_B64=' not in env.read_text():
        with env.open('a') as f:
            f.write('REPORT_LINK_KEY_B64=' + base64.b64encode(secrets.token_bytes(32)).decode() + '\n')
    "

`REPORT_WEB_BASE_URL`(보호자 웹의 주소, 기본 `http://127.0.0.1:3010`)과 `REPORT_WEB_SECRET`(웹 서버와 나누는 비밀값, 기본은 빈 값)은 없어도 뜬다. 새로 만든 개발 환경(`generate_dev_env.py`)에는 `REPORT_WEB_SECRET`이 무작위 값으로 들어가고, 기존 `.env`에 키 한 줄만 더한 환경에는 비어 있다. 웹(⑤-2)을 붙일 때 두 쪽에 같은 값을 넣는다.

개발 환경에서는 제공자 `dev`로 이름만 넣어 로그인한다. 운영자는 `docker compose run --rm backend python scripts/grant_operator.py <user_id>`로 지정한다.

백엔드가 떠 있으면 `app/tool/run_dev.sh`로 앱을 켠다(iOS 시뮬레이터 기준, `app/CLAUDE.md` 참고).

## 더 읽을 것

- `CLAUDE.md` — 꼭 지킬 규칙과 명령어
- `app/CLAUDE.md` — 앱에만 해당하는 규칙과 명령어
- `_docs/architecture.md` — 계층, 수직 슬라이스, 허브-스포크, 허브 포트 조립, 폴더 작명 규칙
- `_docs/harness.md` — 검증 명령
- `_docs/decisions/` — 결정 기록
- `docs/superpowers/specs/` · `docs/superpowers/plans/` — 설계 문서와 구현 계획
