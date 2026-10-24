# 차곡노트

반려동물 미용 매장과 보호자를 잇는 플랫폼이다. 매장은 예약·고객·미용 기록을 관리하고, 보호자는 매장이 보낸 미용 알림장을 받아 본다. 이름은 기록이 "차곡차곡" 쌓인다는 뜻이다.

| 영역 | 스택 | 위치 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic | `backend/` |
| 앱 | Flutter 3.41 이상 | `app/` |
| 웹 (보호자 알림장) | Next.js 16 (App Router) · TypeScript · pnpm | `web/` |
| 개발 환경 | Docker Compose (pgvector · redis · minio · backend · auth · gateway · web) | `infra/` |
| 설계·계획 | 서브 프로젝트별 문서 | `docs/superpowers/` |

## 처음 띄우기

    cd infra
    docker compose build backend
    docker compose run --rm --no-deps backend python scripts/generate_dev_env.py   # .env 와 .env.auth 를 만든다 (이미 있으면 건너뛴다)
    docker compose up -d                                                            # 게이트웨이 http://127.0.0.1:8080, 보호자 웹 http://127.0.0.1:3010
    bash ../backend/scripts/check_auth_flow.sh                                      # 로그인 흐름 확인
    bash ../backend/scripts/check_shop_flow.sh                                      # 매장 개설·합류 흐름 확인
    bash ../backend/scripts/check_account_flow.sh                                   # 회원 탈퇴 흐름 확인
    bash ../backend/scripts/check_customer_flow.sh                                  # 고객·반려동물 흐름 확인
    bash ../backend/scripts/check_report_flow.sh                                    # 알림장 흐름 확인 (버킷 준비 뒤 — _docs/harness.md)
    bash ../backend/scripts/check_notification_flow.sh                              # 알림톡 흐름 확인 (가짜 게이트웨이, 실제 발송 없음)

`REPORT_LINK_KEY_B64`(알림장 링크의 서명 키, 32바이트 이상을 base64 로)는 필수다. 없으면 API 프로세스와 인증 프로세스가 둘 다 기동하지 않는다. `generate_dev_env.py`는 `.env`가 이미 있으면 아무것도 하지 않으므로, ⑤ 이전에 만든 개발 환경은 한 줄을 직접 더한다. 먼저 `.env`가 줄바꿈으로 끝나는지 본다(끝나지 않으면 앞 줄에 붙는다). 아래 명령은 값을 출력하지 않고, 이미 있으면 아무것도 하지 않는다. 키를 바꾸면 보낸 링크가 모두 닫힌다.

    docker compose run --rm --no-deps backend python -c "
    import base64, secrets
    from pathlib import Path
    env = Path('/work/.env')
    if 'REPORT_LINK_KEY_B64=' not in env.read_text():
        with env.open('a') as f:
            f.write('REPORT_LINK_KEY_B64=' + base64.b64encode(secrets.token_bytes(32)).decode() + '\n')
    "

`REPORT_WEB_BASE_URL`(보호자 웹의 주소, 기본 `http://127.0.0.1:3010`)과 `REPORT_WEB_SECRET`(웹 서버와 나누는 비밀값, 기본은 빈 값)은 없어도 백엔드는 뜬다. 웹은 `REPORT_WEB_SECRET`이 없으면 뜨지 않는다 — compose 의 `web`(`next dev`)은 "환경 변수 REPORT_WEB_SECRET 이 없다." 를 찍고 끝난다. 새로 만든 개발 환경(`generate_dev_env.py`)에는 무작위 값이 들어가고, 기존 `.env`에 키 한 줄만 더한 환경에는 없다. 백엔드와 `web`은 같은 `.env`를 읽으므로 한 줄이면 두 쪽이 같은 값이 된다. 아래 명령은 값을 출력하지 않고, 값이 있으면 아무것도 하지 않는다(값이 빈 `REPORT_WEB_SECRET=` 줄만 있으면 그 줄을 지우고 새로 쓴다. `.env`가 줄바꿈으로 끝나지 않아도 된다). 이미 떠 있는 backend 는 다시 만들 때까지 새 값을 모른다 — 그동안에도 웹은 열리고, 백엔드가 웹이 알려 준 접속 주소를 믿지 않을 뿐이다.

    docker compose run --rm --no-deps backend python -c "
    import re, secrets
    from pathlib import Path
    env = Path('/work/.env')
    text = env.read_text()
    if not re.search(r'^REPORT_WEB_SECRET=.', text, re.M):
        text = re.sub(r'^REPORT_WEB_SECRET=$\n?', '', text, flags=re.M)
        if text and not text.endswith('\n'):
            text += '\n'
        env.write_text(text + 'REPORT_WEB_SECRET=' + secrets.token_urlsafe(32) + '\n')
    "

`SOLAPI_API_KEY`·`SOLAPI_API_SECRET`(알림톡 발송 업체 솔라피의 API 키)은 개발 환경에서 비워 둔다 — 둘 다 비어 있고 `APP_ENV=dev`면 가짜 게이트웨이가 붙어 실제 발송 없이 흐름을 확인할 수 있다(토큰·인증번호 `000000`, 번호 끝 `0000`은 실패). 운영은 둘 다 필수이고, 하나만 있거나 비어 있으면 API 프로세스가 기동하지 않는다. 함께 쓰는 키 둘은 없어도 된다 — `SOLAPI_BALANCE_WARN_KRW`(잔액 경고 기준, 기본 30000원 — 디스패처가 하루 한 번 잔액을 보고 아래면 WARNING 로그)와 `NOTIFICATION_DAILY_CAP`(매장별 하루 발송 상한, 기본 300 — 넘으면 보내지 않고 1시간 뒤로 미룬다). 알림톡은 건당 과금(솔라피 13원, 문자 대체 18~45원)이라 실제 키는 운영에만 둔다.

개발 환경에서는 제공자 `dev`로 이름만 넣어 로그인한다. 운영자는 `docker compose run --rm backend python scripts/grant_operator.py <user_id>`로 지정한다.

백엔드가 떠 있으면 `app/tool/run_dev.sh`로 앱을 켠다(iOS 시뮬레이터 기준, `app/CLAUDE.md` 참고).

## 보호자 웹

`web/`은 보호자가 매장이 보낸 링크(`/r/<토큰>`)로 여는 알림장 한 장이다. Next.js 서버가 백엔드 공개 API 를 부르고, 보호자의 브라우저는 백엔드를 직접 부르지 않는다. 개발 서버는 compose 의 `web` 서비스(`next dev`, http://127.0.0.1:3010)이고 `docker compose up -d`가 함께 띄운다. 첫 기동 때 컨테이너 안에서 `pnpm install`을 한다(볼륨 `web_node_modules`). 앱에서 보낸 알림장 링크를 맥 브라우저로 열면 이 서버가 그린다.

테스트와 빌드는 맥에서 `web/`에 들어가 돌린다(node·pnpm 필요, `pnpm install` 먼저).

    pnpm test                    # 컴포넌트·단위
    pnpm build                   # 빌드와 형 검사
    pnpm check:server            # 빌드 뒤. 가짜 백엔드로 서버 응답 검사
    pnpm e2e:prepare && pnpm e2e # 실제 브라우저 (개발 스택과 web 이 떠 있어야 한다)

운영은 Vercel 에 둘 예정이다(아직 배포하지 않았다). 설정은 `API_BASE_URL`(백엔드 주소)과 `REPORT_WEB_SECRET` 둘이고 둘 다 필수다. 규칙은 `web/CLAUDE.md`.

## 더 읽을 것

- `CLAUDE.md` — 꼭 지킬 규칙과 명령어
- `app/CLAUDE.md` — 앱에만 해당하는 규칙과 명령어
- `web/CLAUDE.md` — 웹에만 해당하는 규칙과 명령어
- `_docs/architecture.md` — 계층, 수직 슬라이스, 허브-스포크, 허브 포트 조립, 폴더 작명 규칙
- `_docs/harness.md` — 검증 명령
- `_docs/decisions/` — 결정 기록
- `docs/superpowers/specs/` · `docs/superpowers/plans/` — 설계 문서와 구현 계획
