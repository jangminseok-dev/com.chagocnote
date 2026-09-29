# CLAUDE.md — 차곡노트 보호자 알림장 웹 (Next.js)

저장소 루트의 `CLAUDE.md` 를 먼저 읽는다. 여기는 웹에만 해당하는 규칙이다. 설계는 `docs/superpowers/specs/2026-09-28-report-design.md` 의 7·8절, 결정은 `_docs/decisions/008-report.md` 의 "⑤-2 웹에서 정한 것"이다.

보호자가 매장이 보낸 링크(`/r/<토큰>`)로 여는 알림장 한 장이다. 웹 서버가 백엔드 공개 API 를 부르고 HTML 과 미리보기 정보(OG 태그)를 만든다. 데이터를 저장하지 않는다.

## 꼭 지킬 것

- **App Router 만 쓴다.** 프록시(`proxy.ts`)·Pages Router·별도 오류 경로 핸들러를 만들지 않는다. 경로는 `app/r/[token]/page.tsx` 와 열람 신호 `app/r/[token]/viewed/route.ts`(POST) 둘이다. 루트(`/`)와 그 밖은 404 다.
- **페이지의 상태 코드는 200 과 404 뿐이다**(2026-09-29 사용자와 정함). App Router 페이지는 410·429·503 을 낼 수 없다. 백엔드 404·형식이 틀린 토큰 → `notFound()`(404), 410 → 닫힌 화면(200), 429·연결 실패·5xx → "잠시 후 다시 열어 주세요"(200). 열람 신호 경로는 경로 핸들러라 백엔드의 상태 코드(204·404·410·429, 그 밖 503)를 본문 없이 돌려준다.
- **알림장을 열 때 백엔드 조회는 한 번이다.** `generateMetadata` 와 본문이 `lib/report.ts` 의 `getReport`(= React `cache(fetchReport)`)를 나눠 쓴다. `cache` 를 빼면 조회가 두 번이 된다 — Next 는 같은 fetch 를 합치지 않는다. fetch 는 `cache: 'no-store'` 다.
- **토큰 형식은 웹이 먼저 본다**(`lib/token.ts`, `^[A-Za-z0-9_-]{43}$`). 아니면 백엔드를 부르지 않고 404 다.
- **설정 둘은 필수다**: `API_BASE_URL`, `REPORT_WEB_SECRET`. `process.env` 는 `lib/config.ts` 에서만 읽는다. `NEXT_PUBLIC_` 을 쓰지 않는다(브라우저로 나가는 값이 없다). 둘 중 하나라도 없으면 `instrumentation.ts` 의 `register()` 가 변수 이름을 담아 던진다. `next start` 는 떠 있되 모든 요청에 500 을 내고(`process.exit` 는 넣지 않았다), `next dev`(compose 의 web)는 그 오류를 찍고 종료 코드 1 로 끝난다.
- **응답 헤더 셋**(`X-Robots-Tag: noindex, nofollow`, `Cache-Control: private, no-store`, `Referrer-Policy: no-referrer`)은 `next.config.ts` 의 `headers()` 가 단다. `_next/static/`(글꼴 등)과 `/og-default.png` 는 뺀다 — 토큰과 상관없고, 미리보기 로봇이 캐시 금지 그림을 버릴 수 있다.
- **끈 항목은 칸이 없다**(`undefined`), 켰지만 값이 없으면 `null` 이다. 형(`lib/report.ts` 의 `Report`)에 그대로 담고 웹은 온 것만 그린다. 숨기는 것은 백엔드이지 웹이 아니다.
- 외부 스크립트·외부 글꼴·분석 도구를 넣지 않는다. 브라우저가 부르는 곳은 웹 자신과 미디어 서명 주소뿐이다. Pretendard 는 `next/font/local` 로 subset 셋(400·600·700)만 싣고, 세리프·명조는 시스템 글꼴 스택이다.
- **열람 신호는 브라우저 스크립트만 보낸다**(`components/ViewedSignal.tsx`, 설계 R12). 페이지를 서버에서 그릴 때 보내지 않는다 — 미리보기 로봇이 '열람'으로 찍힌다. 신호 경로는 `Sec-Fetch-Site` 가 있고 `same-origin` 이 아니면 403 이다.
- **뒤로 가기는 크게 보기만 닫는다**(`components/Lightbox.tsx`). 열 때 `history.pushState(null, '')` 로 한 칸을 쌓고(URL 인자를 넣지 않는다 — 토큰이 든 주소를 더 만들지 않는다) `popstate` 에 닫는다. 닫기 버튼·Esc 는 `history.back()` 으로 그 칸을 치운다. 넘기기는 칸을 쌓지 않는다.
- `og:url`·canonical 을 넣지 않는다. 토큰이 든 주소를 더 퍼뜨리지 않는다.
- **`next.config.ts` 의 `htmlLimitedBots` 에 `kakaotalk-scrap` 이 있다** — 빼지 않는다. 카카오 미리보기 로봇이 og 태그를 스트리밍으로 받지 않게 한다(Next 기본 목록에 이 로봇이 없다).
- **접속 주소는 `x-forwarded-for` 의 첫 값이다**(`lib/client-ip.ts`). Vercel 은 이 헤더를 플랫폼이 덮어써서 위조할 수 없다. 직접 노출한 `next start`·compose 개발 환경에서는 위조할 수 있다 — 운영은 Vercel 뒤에서만 둔다는 전제다. 값이 없으면 `X-Report-Client-IP` 를 보내지 않는다.
- 토큰·서명 주소·비밀값·요청 주소·응답 본문을 `console.*` 에 넣지 않는다. `next dev` 는 들어온 요청 주소(토큰이 든 `/r/…`)를 찍으므로 `logging.incomingRequests: false` 로 꺼 두었다.
- 보호자가 쓴 것이 아닌 글(케어 메모·이름·매장 정보)도 React 가 이스케이프하게 둔다. `dangerouslySetInnerHTML` 금지.
- 화면 문구는 설계 8.2·7.3 의 글자 그대로다. 보호자에게 보이는 글은 한국어, 영문 장식("Grooming Note", "Care note", "Today's care", "Shop", 영문 월·요일, 오류 화면의 "Not found"·"Closed"·"One moment")은 목업을 따른다. 오류 화면의 설명은 닫힌 화면에만 있다.
- `next.config.ts` 의 `agentRules: false` 를 빼지 않는다(빼면 `next dev` 가 이 파일에 Next 의 에이전트 규칙 묶음을 끼워 넣는다 — `node_modules/next/dist/server/lib/generate-agent-files.js`). `allowedDevOrigins: ['127.0.0.1']` 도 빼지 않는다 — 백엔드가 만드는 링크는 `http://127.0.0.1:3010/r/…` 이고, 빼면 `next dev` 가 브라우저 쪽 코드를 막아 크게 보기·열람 신호·404 화면 글자가 동작하지 않는다.

## 폴더

`app`(경로) · `components`(화면) · `lib`(설정·토큰·접속 주소·백엔드 호출·표시 형식) · `public` · `tests` 만 쓴다. Next 의 통상 이름이고 새 폴더를 더 만들지 않는다.

- 데이터 가져오기는 `lib/` 와 `page.tsx` 에, 화면은 props 를 받는 컴포넌트에 둔다 — Vitest 는 async 서버 컴포넌트를 렌더링하지 못한다.
- 브라우저 동작이 필요한 것만 `'use client'` 다(`MediaGallery`·`Lightbox`·`SaveAllButton`·`KakaoNotice`·`ViewedSignal`).
- 구역마다 `data-section` 이 있다(`head`·`date`·`title`·`hero`·`strip`·`note`·`care`·`save-all`·`shop`·`foot`). 테스트가 이것으로 구역을 찾는다.

## 테스트 세 층

| 층 | 위치 | 명령 | 보는 것 |
|---|---|---|---|
| 컴포넌트·단위 | `tests/*.test.ts(x)` | `pnpm test` | 끈 항목의 구역, 오류 화면, 크게 보기·저장·카카오톡 안내·열람 신호, 설정·토큰·접속 주소·호출·형식 |
| 서버 응답 | `tests/server/` | `pnpm check:server` | 가짜 백엔드 + `next start` — 상태 코드, 헤더 셋, 첫 HTML 의 미리보기 정보, 백엔드 호출 수, 기록에 토큰·비밀값이 없는지 |
| 실제 브라우저 | `tests/e2e/` | `pnpm e2e:prepare && pnpm e2e` | compose 의 web 과 개발 스택 — 열기, 여러 번 새로 고침, 크게 보기, 뒤로 가기, 긴 글의 가로 넘침(폭 320·390), 저장, 열람 신호, 닫힌 링크, 404, 자바스크립트 끔 |

- 매달린 백엔드(5초 뒤 "잠시 후 다시 열어 주세요"·열람 신호 503)와 영상만 있는 알림장의 미리보기 그림(포스터)은 `check:server` 가 본다(가짜 백엔드 앞머리 `slow`·`vid`).
- **헤더 검사는 `next start` 로 한다**(`check:server`). `next dev` 는 페이지의 `Cache-Control` 을 덮지 못한다.
- `check:server` 는 `.next` 의 빌드를 쓴다. 코드를 고쳤으면 `pnpm build` 뒤에 돌린다.
- `next build` 의 형 검사는 `tests/**` 도 본다. 테스트도 형에 맞게 쓴다.
- 없는 경로의 404 는 Next 가 `Cache-Control` 을 자기 값으로 바꾸므로 검사는 `private`·`no-store` 의 포함 여부로 한다.
- `notFound()` 의 404 는 첫 HTML 에 화면 글자가 없다(Next 의 구조 — 글자는 스크립트 안에 있다). 404 글자는 실제 브라우저(e2e)로 본다.
- 주석·테스트 이름은 한국어 문장이다.

## 명령어 (`web/` 에서)

    pnpm install
    pnpm test                           # Vitest
    pnpm build                          # 빌드와 형 검사
    pnpm check:server                   # 빌드 뒤
    pnpm e2e:prepare                    # e2e 를 돌릴 때마다 먼저 (개발 DB 에 확인용 매장·방문을 만든다)
    pnpm e2e                            # Playwright. 브라우저가 없으면 pnpm exec playwright install chromium

개발 서버는 compose 의 `web`(`next dev`, http://127.0.0.1:3010)이다. `API_BASE_URL` 은 compose 가 넣고(`http://backend:8000`), `REPORT_WEB_SECRET` 은 저장소 루트의 `.env` 에서 백엔드와 같은 값을 읽는다.
