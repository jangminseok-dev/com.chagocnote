# CLAUDE.md — 차곡노트 보호자 웹 (Next.js) — 알림장과 내 기록

저장소 루트의 `CLAUDE.md` 를 먼저 읽는다. 여기는 웹에만 해당하는 규칙이다. 알림장의 설계는 `docs/superpowers/specs/2026-09-28-report-design.md` 의 7·8절, 결정은 `_docs/decisions/008-report.md` 의 "⑤-2 웹에서 정한 것"이다. 로그인과 내 기록의 설계는 `docs/superpowers/specs/2026-11-13-guardian-design.md` 의 4.4절, 결정은 `_docs/decisions/010-guardian.md` 의 "⑦-2 웹에서 정한 것"이다.

셋이다. (1) 보호자가 매장이 보낸 링크(`/r/<토큰>`)로 여는 알림장 한 장 — 웹 서버가 백엔드 공개 API 를 부르고 HTML 과 미리보기 정보(OG 태그)를 만든다. (2) 로그인한 보호자의 내 기록(`/me`) — 받은 알림장으로 계정을 잇고 지난 알림장을 모아 보고, 사진을 모아 보고, 가족을 초대해 함께 본다(아래 "기록 모아 보기와 가족" 절). (3) 매장이 보낸 링크(`/f/<토큰>`)로 여는 서류 — 미용 동의서(로그인 없이 읽고 이름과 손가락 서명으로 보낸다)와 첫 방문 문진표(아이의 정보를 적어 낸다, 아래 "문진표" 절)(설계 `docs/superpowers/specs/2026-11-16-consent-intake-design.md`, 결정 `_docs/decisions/014-consent-intake.md` 의 "⑪-A2 웹에서 정한 것"). 데이터를 저장하지 않는다(세션은 쿠키에만 있다).

## 꼭 지킬 것

- **App Router 만 쓴다.** 프록시(`proxy.ts`)·Pages Router·별도 오류 경로 핸들러를 만들지 않는다. 경로는 알림장 `app/r/[token]/page.tsx`·열람 신호 `…/viewed/route.ts`(POST)·잇기 `…/claim/route.ts`(POST), 로그인 `app/login/page.tsx`·`app/login/dev/route.ts`(POST)·`app/logout/route.ts`(POST), 내 기록 `app/me/page.tsx`·`app/me/[linkId]/page.tsx`·`app/me/[linkId]/[reportId]/page.tsx`·`app/me/[linkId]/unlink/route.ts`(POST), 사진 모아 보기 `app/me/[linkId]/photos/page.tsx`, 가족 `app/me/[linkId]/family-invite/route.ts`(POST, JSON)·`app/me/[linkId]/family-unlink/route.ts`(POST)·`app/j/[code]/page.tsx`·`app/j/[code]/join/route.ts`(POST)다. 루트(`/`)와 그 밖은 404 다.
- **페이지의 상태 코드는 200 과 404, 그리고 로그인이 필요한 곳의 307 뿐이다**(2026-09-29 사용자와 정함, 307 은 ⑦-2). App Router 페이지는 410·429·503 을 낼 수 없다. 백엔드 404·형식이 틀린 토큰 → `notFound()`(404), 410 → 닫힌 화면(200), 429·연결 실패·5xx → "잠시 후 다시 열어 주세요"(200). 열람 신호 경로는 경로 핸들러라 백엔드의 상태 코드(204·404·410·429, 그 밖 503)를 본문 없이 돌려준다.
- **알림장을 열 때 백엔드 조회는 한 번이다.** `generateMetadata` 와 본문이 `lib/report.ts` 의 `getReport`(= React `cache(fetchReport)`)를 나눠 쓴다. `cache` 를 빼면 조회가 두 번이 된다 — Next 는 같은 fetch 를 합치지 않는다. fetch 는 `cache: 'no-store'` 다.
- **토큰 형식은 웹이 먼저 본다**(`lib/token.ts`, `^[A-Za-z0-9_-]{43}$`). 아니면 백엔드를 부르지 않고 404 다.
- **설정 넷은 필수다**: `API_BASE_URL`, `REPORT_WEB_SECRET`, `AUTH_BASE_URL`(인증 프로세스), `WEB_SESSION_SECRET`(쿠키를 봉하는 값, 32글자 이상). `DEV_LOGIN=1` 은 개발용 로그인을 켠다(기본 꺼짐 — 운영에 두지 않는다). `process.env` 는 `lib/config.ts` 에서만 읽는다. `NEXT_PUBLIC_` 을 쓰지 않는다(브라우저로 나가는 값이 없다). 넷 중 하나라도 없으면 `instrumentation.ts` 의 `register()` 가 변수 이름을 담아 던진다. `next start` 는 떠 있되 모든 요청에 500 을 내고(`process.exit` 는 넣지 않았다), `next dev`(compose 의 web)는 그 오류를 찍고 종료 코드 1 로 끝난다.
- **응답 헤더 셋**(`X-Robots-Tag: noindex, nofollow`, `Cache-Control: private, no-store`, `Referrer-Policy: no-referrer`)은 `next.config.ts` 의 `headers()` 가 단다. `_next/static/`(글꼴 등)과 `/og-default.png` 는 뺀다 — 토큰과 상관없고, 미리보기 로봇이 캐시 금지 그림을 버릴 수 있다.
- **끈 항목은 칸이 없다**(`undefined`), 켰지만 값이 없으면 `null` 이다. 형(`lib/report.ts` 의 `Report`)에 그대로 담고 웹은 온 것만 그린다. 숨기는 것은 백엔드이지 웹이 아니다.
- 외부 스크립트·외부 글꼴·분석 도구를 넣지 않는다. 브라우저가 부르는 곳은 웹 자신과 미디어 서명 주소뿐이다. Pretendard 는 `next/font/local` 로 subset 셋(400·600·700)만 싣고, 세리프·명조는 시스템 글꼴 스택이다.
- **열람 신호는 브라우저 스크립트만 보낸다**(`components/ViewedSignal.tsx`, 설계 R12). 페이지를 서버에서 그릴 때 보내지 않는다 — 미리보기 로봇이 '열람'으로 찍힌다. 신호 경로는 `Sec-Fetch-Site` 가 있고 `same-origin` 이 아니면 403 이다.
- **뒤로 가기는 크게 보기만 닫는다**(`components/Lightbox.tsx`). 열 때 `history.pushState(null, '')` 로 한 칸을 쌓고(URL 인자를 넣지 않는다 — 토큰이 든 주소를 더 만들지 않는다) `popstate` 에 닫는다. 닫기 버튼·Esc 는 `history.back()` 으로 그 칸을 치운다. 넘기기는 칸을 쌓지 않는다.
- **웹 세션은 30분이고 연장하지 않는다**(2026-11-13 사용자 결정). 로그인 때 인증 프로세스에서 30분짜리 액세스 토큰 하나를 받아(`lib/auth.ts`, 본문에 늘 `session: "web"`) 봉한 쿠키 `cn_session` 에 둔다 — httpOnly·SameSite=Lax·Path=/·Max-Age 는 토큰의 수명·운영 빌드에서만 Secure(`lib/session.ts`, 봉하기는 `lib/seal.ts` 의 AES-256-GCM). 리프레시 토큰이 든 응답은 버린다. **웹 서버는 `/v1/auth/social` 외의 `/v1/auth/*` 를 부르지 않는다.**
- **쿠키를 쓰는 곳은 경로 핸들러뿐이다**(로그인·로그아웃·잇기·끊기·가족 잇기·가족 끊기 — 폼 POST 를 받고 303 으로 보낸다, `lib/origin.ts` 의 `seeOther`. 초대 만들기는 스크립트가 부르고 JSON 을 받는다). 페이지는 쿠키를 읽기만 한다 — App Router 의 페이지는 쿠키를 쓰지 못한다. 그래서 끝난 세션의 쿠키를 페이지가 지우지 않고(쿠키가 토큰과 함께 끝난다) `/login?next=…` 로 보낸다(`lib/me.ts` 의 `requireSession`·`screenFor`).
- **`/login` 은 세션이 있어도 다른 곳으로 보내지 않는다** — 끝난 토큰으로 `/me` 와 서로 돌지 않게.
- **로그인 뒤 돌아갈 경로(`next`)는 `lib/next-path.ts` 의 `safeNext` 가 받는 모양뿐이다**(`/me`, `/me/<숫자>`, `/me/<숫자>/<숫자>`, `?pet=<숫자>`, 사진 모아 보기 `/me/<숫자>/photos` 와 `?pet=&year=&phase=` 이 순서). 그 밖은 `/me` 다 — 다른 사이트로 내보내지 않는다. 경로의 숫자는 `idFrom`(양의 정수 15자리까지)으로 보고, 아니면 백엔드를 부르지 않고 404 다.
- **상태를 바꾸는 경로(POST)는 `Sec-Fetch-Site` 가 있고 `same-origin` 이 아니면 403 이다**(`lib/origin.ts` 의 `isCrossSite`). 열람 신호와 같은 규칙이다.
- **잇기**: 알림장 꼬리 앞의 폼 버튼 [로그인하고 지난 기록 보기]가 `POST /r/<토큰>/claim` 을 부른다. 로그인돼 있으면 바로 잇고, 아니면 토큰을 봉한 쿠키 `cn_claim`(10분)에 맡기고 `/login` 으로 보낸다 — 토큰이 든 주소를 새로 만들지 않는다. 로그인이 되면 그 쿠키를 꺼내 잇고 지운다(로그인이 실패하면 건드리지 않는다). 잇기가 안 됐을 때 알리는 것은 "이미 다른 계정에 이어져 있어요"(409 → `/me?notice=taken`) 하나뿐이고 닫힘·없음·횟수 초과는 말없이 `/me` 다. **닫힌 알림장 화면의 같은 글자는 폼이 아니라 `/me` 로 가는 링크다** — 닫힌 링크로는 잇지 않는다. **로그인할 수단이 없으면(`DEV_LOGIN` 꺼짐) 버튼도 링크도 그리지 않고 잇기 경로는 404 다.** 로그아웃은 잇기 쿠키도 지운다.
- **토큰이 화면에 있는 곳은 잇기 폼의 주소 하나다**(스크립트 없이 폼을 보내려면 필요하다). 숨은 칸·링크·다른 속성에 더 싣지 않는다.
- **로그인한 보호자의 한 장은 `ReportView` 에 `token` 을 넘기지 않는다** — 열람 신호·잇기 버튼이 없고, 백엔드가 기간을 null 로 줘 기간 문구도 없다. 미리보기(og) 정보를 넣지 않는다.
- 지난 알림장의 [더 보기]는 다음 쪽으로 넘어가는 링크다(쌓아 붙이지 않는다 — 대표 사진의 서명 주소가 짧게 산다). 다시 로그인해 돌아올 때는 첫 쪽이다.
- `/me` 아래에 `loading.tsx`·Suspense 경계를 두지 않는다 — 307·404 가 200 으로 바뀐다.
- `og:url`·canonical 을 넣지 않는다. 토큰이 든 주소를 더 퍼뜨리지 않는다.
- **`next.config.ts` 의 `htmlLimitedBots` 에 `kakaotalk-scrap` 이 있다** — 빼지 않는다. 카카오 미리보기 로봇이 og 태그를 스트리밍으로 받지 않게 한다(Next 기본 목록에 이 로봇이 없다).
- **접속 주소는 `x-forwarded-for` 의 첫 값이다**(`lib/client-ip.ts`). Vercel 은 이 헤더를 플랫폼이 덮어써서 위조할 수 없다. 직접 노출한 `next start`·compose 개발 환경에서는 위조할 수 있다 — 운영은 Vercel 뒤에서만 둔다는 전제다. 값이 없으면 `X-Report-Client-IP` 를 보내지 않는다.
- 토큰(알림장·액세스)·쿠키 값·서명 주소·비밀값·요청 주소·응답 본문을 `console.*` 에 넣지 않는다. `next dev` 는 들어온 요청 주소(토큰이 든 `/r/…`)를 찍으므로 `logging.incomingRequests: false` 로 꺼 두었다.
- 보호자가 쓴 것이 아닌 글(케어 메모·이름·매장 정보)도 React 가 이스케이프하게 둔다. `dangerouslySetInnerHTML` 금지.
- 화면 문구는 설계 8.2·7.3 의 글자 그대로다. 보호자에게 보이는 글은 한국어, 영문 장식("Grooming Note", "Care note", "Today's care", "Shop", 영문 월·요일, 오류 화면의 "Not found"·"Closed"·"One moment", 로그인·내 기록의 "Sign in"·"My notes"·"Notes")은 목업을 따른다. 오류 화면의 설명은 닫힌 화면에만 있다.
- `next.config.ts` 의 `agentRules: false` 를 빼지 않는다(빼면 `next dev` 가 이 파일에 Next 의 에이전트 규칙 묶음을 끼워 넣는다 — `node_modules/next/dist/server/lib/generate-agent-files.js`). `allowedDevOrigins: ['127.0.0.1']` 도 빼지 않는다 — 백엔드가 만드는 링크는 `http://127.0.0.1:3010/r/…` 이고, 빼면 `next dev` 가 브라우저 쪽 코드를 막아 크게 보기·열람 신호·404 화면 글자가 동작하지 않는다.

## 기록 모아 보기와 가족 (⑫)

설계 `docs/superpowers/specs/2026-11-16-guardian-archive-design.md` 3절·5.3, 결정 `_docs/decisions/015-guardian-archive.md` 의 "⑫-2 웹에서 정한 것".

- **리뷰 줄**(`components/ReviewLine.tsx`)은 알림장의 매장 카드 아래·잇기 버튼 위다. 백엔드가 `review_url`·`review_text` 를 줄 때만(주소가 없거나 그 알림장만 뺐으면 칸째 없다), 그리고 https 일 때만(`safeReviewUrl`) 그린다. 새 창·`rel="noopener noreferrer nofollow"` 를 빼지 않는다 — 알림장 주소(토큰)를 리뷰 사이트에 넘기지 않는다. 공개·로그인한 한 장 둘 다다.
- **사진 모아 보기**(`app/me/[linkId]/photos/page.tsx` → `components/PhotoArchive.tsx`)는 지난 알림장 목록과 같은 규칙이다: 한 쪽 60개, [더 보기]는 다음 쪽 링크, 다시 로그인하면 거르기(`pet`·`year`·`phase`)는 지키고 쪽 표시는 버린다, 모양이 틀린 인자는 없는 것으로 친다. 날짜(알림장)마다 묶은 격자(`PhotoGrid` — 묶음의 `id` 는 `r<알림장>`), 연도·전후 거르기, **이 쪽 모두 저장**(`SaveAllButton` 에 `label`·`note`), 아이를 골랐을 때 몸무게(`WeightChart` — 라이브러리 없는 SVG, 풀이 문구 없음). 몸무게를 읽지 못하면 그 구역만 없다.
- **모두 저장**: 사진만이고 열 장 이하이며 파일 공유가 되면 공유 시트, 아니면 원본 주소를 600ms 간격으로 차례로 내려받는다(`저장하는 중… n / N`). 일부 실패 표시는 공유 경로뿐이다(내려받기는 실패를 알 수 없다). 화면을 연 지 24시간이 지났으면 받지 않고 새로 고치라고 한다(서명 주소가 끝났다).
- **크게 보기**는 두 번 누르면 2.5배, 손가락 둘로 4배까지(`data-scale`). 확대 중에도 거의 움직이지 않은(10px 안) 손가락은 누르기라 두 번 눌러 1배로 돌아온다. 손가락의 두 번 누르기 뒤 600ms 안의 `dblclick`(브라우저가 터치로 만든 것)은 거른다 — 두 번 바뀌지 않게. 사진 모아 보기에서는 아래에 그 날의 알림장 링크가 붙고(`footer`), 그 링크는 크게 보기가 쌓은 방문 기록 칸을 `location.replace` 로 바꿔 끼운다(한 장에서 뒤로 가기 한 번이면 사진).
- 사진 모아 보기에서 **거른 결과가 비어도 거르기와 몸무게는 남는다**(빈 글은 `이 조건의 사진이 없어요`). 몸무게는 사진과 따로다.
- 연결 끊기의 확인 글은 연결마다 다르다(`UnlinkButton` 의 `role`·`familyCount`) — 가족이 있는 기본 연결은 가족도 끊긴다고, 가족 연결은 다시 보려면 새 초대가 필요하다고 말한다.
- **보던 자리**(`components/BackToList.tsx`): 목록(지난 알림장·사진)을 열면 경로와 질의만 `sessionStorage` 의 `cn-list:<연결>` 에 적고, 한 장의 돌아가기가 그 경로의 `#r<알림장>` 으로 간다. 같은 연결의 목록 모양만 따른다. 서버는 첫 쪽으로 그린다.
- **가족 초대**: [가족과 함께 보기](`FamilyInviteButton`)가 `POST /me/<연결>/family-invite` 를 부르면 웹 서버가 백엔드에 초대를 만들고 **경로(`/j/<코드>`)만** JSON 으로 준다(`no-store`) — 버튼이 origin 을 붙여 공유 시트·복사로 넘기고, 둘 다 안 되면 화면에 보인다. 코드를 페이지 주소·쿠키·기록에 싣지 않는다. 409 → `함께 볼 수 있는 가족이 다 찼어요`, 401 → 로그인.
- **초대 받은 화면**(`/j/<코드>`)은 백엔드를 부르지 않는다 — 코드 모양(43글자)만 보고 아니면 404, 미리보기(og) 정보 없음. [로그인하고 함께 보기]는 `POST /j/<코드>/join` — 로그인돼 있으면 바로 잇고(`X-Family-Invite` 헤더), 아니면 코드를 봉한 쿠키 `cn_join`(10분)에 맡기고 `/login`. 로그인이 `cn_claim`·`cn_join` 을 둘 다 꺼내 쓰고 지운다. 잇지 못하면(없음·씀·가득·잦음) `/me?notice=invite` 한 가지 안내. 로그아웃은 `cn_join` 도 지운다. `DEV_LOGIN` 이 꺼져 있으면 버튼이 없고 잇기 경로는 404 다.
- **함께 보는 가족**(`FamilySection`)은 기본 보호자에게만, 매장이 가족 수를 0 으로 두었고 가족도 없으면 그리지 않는다. 한 사람 한 줄(`가족 N · 날짜에 이음`, 이름·계정 없음)·[끊기]·[가족 모두 끊기](`POST /me/<연결>/family-unlink`, `family_id` 가 있으면 한 명)·새로 이은 가족 알림(백엔드가 한 번만 `unseen`). 가족으로 이은 연결에는 `가족으로 함께 보는 기록이에요` 한 줄이고 초대·가족 구역이 없다. `/me` 는 기본 연결마다 가족을 한 번 더 읽는다(읽지 못하면 그 구역만 없다).
- 구역: 알림장 `review`, 내 기록 `family`, 목록·사진의 `tabs`, 사진 `photos-head`·`filter`·`save-all`·`weights`·`grid`·`more`·`empty`, 초대 받은 화면 `join`.
- 가짜 백엔드: 연결 11 은 기본(가족 한 명 21·최대 3), 12 는 가족 연결. 초대 만들기는 `tok-full` 이면 409, 가족 잇기는 `X-Family-Invite` 의 앞머리 `fam`·`ok` 201·`full` 409·`rate` 429·그 밖(`used`) 404. 사진은 첫 쪽 넷(다음 쪽 `m2`), 몸무게는 아이 7 둘·8 빈 목록·그 밖 404. `/__stats` 의 `paths` 에 받은 요청의 메서드와 경로가 순서대로 있다.
- e2e(`archive.spec.ts`)는 준비 스크립트가 만든 셋째 고객(콩이)을 쓴다 — 리뷰 줄 있는 알림장·뺀 알림장, 로그인 이름 셋(기본·가족 둘). 준비 스크립트가 그 매장의 몸무게를 켜고 리뷰 주소를 넣는다. **서버가 그린 단추(모두 저장·초대·격자)는 스크립트가 붙기 전에 누르면 아무 일이 없다** — 누르기 전에 `networkidle` 을 기다린다.

## 동의서 (`/f/<토큰>`)

- 경로는 `app/f/[token]/page.tsx` 와 제출 `app/f/[token]/submit/route.ts`(POST) 둘이다. 알림장과 같은 규칙을 따른다 — 토큰 형식은 웹이 먼저 보고, 열 때 백엔드 조회는 한 번(`lib/form.ts` 의 `getForm` = `cache(fetchForm)`), 페이지의 상태 코드는 200·404 뿐이다(410 → 닫힌 화면, 429·5xx·연결 실패 → 잠시 후).
- **토큰은 헤더 `X-Form-Token` 으로 보낸다**(알림장의 `X-Report-Token` 이 아니다 — 두 토큰은 서로의 경로에서 읽히지 않는다).
- **웹은 온 문안을 그대로 그린다.** 어느 토막이 필요한지, 글이 무엇인지는 백엔드가 아이의 지금 사실로 조립한다. 아이의 이름과 지병의 이름은 문안 밖에서 늘 따로 그린다.
- **제출은 브라우저의 fetch → 웹의 경로 핸들러 → 백엔드다.** 폼 POST·303 이 아니다 — 서명에 스크립트가 어차피 필요하고, 결과를 303 으로 알리려면 토큰이 든 주소에 질의를 붙여야 한다. 경로 핸들러는 상태 코드만 본문 없이 돌려준다(204·404·409·410·413·422·429, 그 밖 503). 다른 출처면 403, `Content-Length` 가 없거나 131,072 를 넘으면 본문을 읽지 않고 413, JSON 이 아니거나 세 칸(`doc_digest`·`signer_name`·`signature_png`)이 글자열이 아니면 422 — 이때 백엔드를 부르지 않는다. 세 칸 밖의 것은 넘기지 않는다.
- **서명 칸**(`components/SignaturePad.tsx`)은 600×240 캔버스를 CSS 로 늘린다(화면 배율을 곱하지 않는다 — PNG 가 작게 남는다). base64 가 87,380글자를 넘으면 300×120 으로 줄여 그린 것을 보낸다. `touch-action: none` 을 빼지 않는다 — 서명하는 손가락을 따라 화면이 구른다.
- **서버가 그린 보내기 버튼은 잠겨 있고 폼은 `method="post"` 다** — 스크립트가 오기 전에 누르면 브라우저가 폼을 그대로 내 적은 이름이 주소에 실린다. `disabled={!ready || sending}` 의 `ready` 를 빼지 않는다. 스크립트가 오기 전에 친 이름은 올 때 한 번 상태로 옮긴다.
- **서명 칸은 한 번에 포인터 하나만 받는다**(`pointerId`) — 둘째 손가락·손바닥은 선을 긋지 않는다. 그림의 바탕은 희다.
- **보내기 전에 빠진 것을 그 자리에서 말한다**(`components/ConsentSubmit.tsx` — 이름·서명·체크 순). 204·410 은 다시 읽기를 기다리지 않고 곧바로 `보냈어요` 를 보이고(`role="status"`, 포커스) 화면을 다시 읽는다 — 410 은 이미 낸 것이라 오류로 보이지 않는다. 409 는 `내용이 바뀌었어요. 다시 읽어 주세요` 와 함께 다시 읽고, 이름은 남기고 서명과 체크를 비운다.
- **미리보기(og)에는 매장 이름과 "미용 동의서"뿐이다.** 아이 이름·지병을 싣지 않는다.
- 이름·서명·요청 본문을 `console.*` 에 넣지 않는다.
- 닫힌 서류의 화면에는 로그인 링크가 없다(`ErrorScreen` 의 `what="form"`) — 서류는 계정에 잇지 않는다.
- 구역: `head`·`partial`·`pets`·`part`·`sign`·`foot`, 낸 뒤 `submitted`.
- 가짜 백엔드의 서류 앞머리: 읽기 `ok`(아이 둘·토막 셋)·`part`(바뀐 부분만)·`sent`(보냈어요)·`gone`·`rate`·`boom`·`slow`·`down`, 제출 `ok` 204·`chg` 409·`gone` 410·`big` 413·`bad` 422·`rate` 429.
- **e2e 에서 `getByRole('alert')` 은 구역 안에서 찾는다** — `next dev` 의 경로 알림도 `role="alert"` 다. 스크립트를 끈 브라우저 테스트는 `<noscript>` 가 보이는지가 아니라 문서에 실려 왔는지를 본다(Playwright 가 스크립트를 끄는 방식으로는 크롬이 `<noscript>` 를 그리지 않는다).

## 문진표 (`/f/<토큰>`)

- 동의서와 **같은 주소·같은 토큰·같은 헤더**(`X-Form-Token`)다. `app/f/[token]/page.tsx` 가 백엔드가 준 `kind`(`consent`·`intake`)로 가른다 — 열 때 백엔드 조회는 여전히 한 번이다. 제출 경로는 따로다: `app/f/[token]/intake/route.ts`(POST). 설계는 `docs/superpowers/specs/2026-11-16-consent-intake-design.md` 3.4절, 결정은 `_docs/decisions/014-consent-intake.md` 의 "⑪-C2 웹에서 정한 것".
- **웹은 온 구성만 그린다**(`lib/form.ts` 의 `OpenIntake`): 켜진 칸(`fields`), 매장이 더한 질문, 지병 종류, 보호자 칸을 물을지(`guardian_needed`), 보관 기간(`keep_days`). 매장이 끈 칸은 그리지도 보내지도 않는다. 지금 값(품종·몸무게·지병)은 오지 않는다 — 다시 받기(`mode: "update"`)에서도 아이 이름뿐이다.
- **칸의 규칙과 보낼 본문은 순수 함수다**(`lib/intake.ts` 의 `problemOf`·`bodyOf`) — 화면(`components/IntakeForm.tsx`)은 그것을 쓴다. 규칙은 백엔드와 같다: 켜진 칸은 필수, 다시 받기는 전부 선택이고 적은 칸만 싣는다. 한 줄 칸에 붙여넣은 줄바꿈은 빈칸으로 바꾼다.
- **필수로 글자를 치는 칸은 넷 이하다**(보호자 이름·번호·아이 이름 — `data-required-text="true"`, 품종은 목록에서 고르면 치지 않는다). 나머지는 칩이다. 테스트가 수를 고정한다.
- **낼 때는 둘이다**: [보내기](`done: true` — 다 적었어요, 링크가 닫힌다)와 [보내고 다른 아이도 적기](`done: false` — 아이 칸만 비우고 방금 낸 아이의 이름을 알린 뒤 다시 읽는다. 둘째부터 보호자 칸이 없다). 다시 받기에는 [보내기]뿐이다. **[보내기] 곁에 `보내면 이 링크는 닫혀요…` 한 줄이 있고 글자 칸의 엔터로는 보내지 않는다** — 닫힌 링크는 되돌릴 수 없다.
- 빠진 칸은 보내지 않고 그 칸의 이름으로 말한다(화면의 위에서부터 처음 걸리는 것 하나). 204 → `보냈어요`(`role="status"`, 포커스)와 다시 읽기, **410·404 → 오류 글 없이 다시 읽는다**(그 사이 닫혔다 — 다시 읽은 화면이 말한다), 413·422 → `적은 내용을 다시 확인해 주세요` 와 함께 **다시 읽는다**(매장이 그 사이 칸을 켜거나 질문을 더했을 수 있다 — 적은 것은 남는다), 그 밖 → `잠시 후 다시 보내 주세요`. 걸린 칸에는 `aria-invalid` 와 포커스를 주고, 안내 글은 화면 아래에 붙어 따라온다(`.notice` 가 sticky). **브라우저의 규칙은 서버가 422 로 막는 것을 먼저 짚는다** — 전화번호의 모양(나라 번호 `+82` 는 0 으로 바꿔 보낸다), 생일·태어난 해의 범위(1990년~오늘, 로컬 날짜 — `localDay`), 제어 문자.
- 제출 경로는 동의서와 같은 관문이다 — 다른 출처 403, `Content-Length` 가 없거나 131,072 를 넘으면 413, JSON 객체가 아니거나 `pet` 이 객체가 아니거나 `privacy_agreed` 가 불리언이 아니면 422(이때 백엔드를 부르지 않는다). **본문은 그대로 넘긴다** — 칸의 규칙은 백엔드가 본다. 상태 코드만 본문 없이 돌려준다(204·404·409·410·413·422·429, 그 밖 503).
- **문진표 끝의 동의서**(⑪-C1b): 적은 답으로 보아 노령(매장의 `consent.senior_age` 이상 — 생일·태어난 해로, 나이 칸이 꺼졌거나 모르면 아니다)이거나 지병을 골랐으면(매장이 `consent.all` 을 켰으면 늘) 개인정보 안내 위에 `미용 동의서` 구역이 나타난다 — 토막은 `lib/intake.ts` 의 `consentPartsOf`(백엔드 `intake_consent.consent_parts` 와 같은 규칙, 단위 테스트가 경계를 고정한다). 토막의 글, **글 밖의 `알려 주신 지병: …`**, `서명하는 분의 이름`(고치기 전까지 보호자 이름을 따라간다), 서명 칸(`SignaturePad`), `위 내용을 읽었고 동의해요`. 셋이 빠지면 보내지 않는다. 본문의 `consent` 에 `digest`(연 구성의 지문)·`parts`·이름·서명을 싣는다. **409 → `내용이 바뀌었어요. 다시 읽어 주세요` 와 다시 읽기 — 적은 답과 이름은 남고 서명·체크만 비운다.** [보내고 다른 아이도 적기] 뒤에는 서명을 아이마다 새로 받는다(이름은 남는다). **서명한 뒤 토막이나 보인 지병 이름이 바뀌면(구역이 사라졌다 나타나도) 서명을 다시 받는다** — 보지 않은 토막에 서명한 것으로 남지 않게. 서명 칸을 비우는 `onChange(null)` 은 안내를 지우지 않는다(409 의 안내가 남게). `consent.all` 은 그 링크에 맞춘 값이다(다시 받기면 늘 꺼짐).
- **개인정보 수집·이용 안내**(받는 것·쓰는 곳·지우는 때 — `keep_days`)와 동의 체크가 폼의 끝에 있다. 빼지 않는다.
- 서버가 그린 버튼은 잠겨 있고 폼은 `method="post"` 다(동의서와 같은 까닭). 미리보기(og)에는 매장 이름과 "문진표"뿐이다.
- 이름·전화번호·적은 글·요청 본문을 `console.*` 에 넣지 않는다.
- 구역: `guardian`·`pet`·`health`·`more`·`consent`(붙을 때만)·`privacy`, 낸 뒤 `submitted`.
- 가짜 백엔드의 문진표 앞머리: 읽기 `iok`(새 손님)·`iupd`(다시 받기 — 두부)·`isent`(보냈어요)·`ibad`, 제출 `iok` 204·`ichg` 409(동의서 글이 바뀜)·`ibad` 422(`gone`·`rate`·`boom`·`down` 은 동의서와 같다). 문진표 읽기에는 `consent`(글·노령 나이·지문)가 있다.
- **compose 의 `next dev` 는 새로 생긴 경로 폴더를 알아채지 못할 때가 있다** — 새 `route.ts` 가 404 면 `docker compose restart web`.
- e2e 준비 스크립트는 공개 서류의 제출 횟수(접속 주소당 10분에 10번)를 비운다 — 동의서와 문진표 흐름을 이어 돌리면 넘는다.

## 폴더

`app`(경로) · `components`(화면) · `lib`(설정·토큰·접속 주소·백엔드 호출·세션·경로 검증·표시 형식) · `public` · `tests` 만 쓴다. Next 의 통상 이름이고 새 폴더를 더 만들지 않는다.

- 데이터 가져오기는 `lib/` 와 `page.tsx` 에, 화면은 props 를 받는 컴포넌트에 둔다 — Vitest 는 async 서버 컴포넌트를 렌더링하지 못한다.
- 브라우저 동작이 필요한 것만 `'use client'` 다(`MediaGallery`·`Lightbox`·`SaveAllButton`·`KakaoNotice`·`ViewedSignal`·`UnlinkButton`·`ConsentSubmit`·`SignaturePad`·`IntakeForm`·`PhotoGrid`·`BackToList`·`FamilyInviteButton`).
- 구역마다 `data-section` 이 있다(알림장 `head`·`date`·`title`·`hero`·`strip`·`note`·`care`·`save-all`·`shop`·`review`·`claim`·`foot`, 로그인 `login`, 내 기록 `me-head`·`notice`·`shop`·`family`·`empty`·`logout`, 목록 `list-head`·`tabs`·`item`·`more`·`empty`, 한 장 위의 `back`, 사진 모아 보기와 초대 받은 화면은 위 "기록 모아 보기와 가족" 절). 테스트가 이것으로 구역을 찾는다.

## 테스트 세 층

| 층 | 위치 | 명령 | 보는 것 |
|---|---|---|---|
| 컴포넌트·단위 | `tests/*.test.ts(x)` | `pnpm test` | 끈 항목의 구역, 오류 화면, 크게 보기·저장·카카오톡 안내·열람 신호, 설정·토큰·접속 주소·호출·형식, 봉하기·세션 쿠키·돌아갈 경로·같은 출처, 로그인·내 기록·목록·연결 끊기 화면 |
| 서버 응답 | `tests/server/` | `pnpm check:server` | 가짜 백엔드(API 와 인증을 함께 맡는다) + `next start` — 상태 코드, 헤더 셋, 첫 HTML 의 미리보기 정보, 백엔드 호출 수, 쿠키의 속성과 쓰고 지우는 때, 로그인이 필요한 곳의 이동, 다른 출처의 POST 403, 기록에 토큰·쿠키 값·비밀값이 없는지 |
| 실제 브라우저 | `tests/e2e/` | `pnpm e2e:prepare && pnpm e2e` | compose 의 web 과 개발 스택 — 열기, 여러 번 새로 고침, 크게 보기, 뒤로 가기, 긴 글의 가로 넘침(폭 320·390), 저장, 열람 신호, 닫힌 링크, 404, 자바스크립트 끔. 보호자 흐름(`guardian.spec.ts`) — 알림장의 버튼 → 개발용 로그인 → 내 기록 → 목록 → 한 장, 세션이 끝난 뒤 다시 로그인해 보던 곳으로, 다른 계정의 안내, 닫힌 알림장에서의 로그인, 끊기와 다시 잇기, 로그아웃. 기록 모아 보기(`archive.spec.ts`) — 리뷰 줄, 사진 모아 보기의 묶음·거르기·몸무게·확대, 보던 자리, 한 쪽 저장의 내려받기 수, 가족 초대 → 다른 계정이 잇기 → 쓴 초대 → 한 명만 끊기 |

- 가짜 백엔드의 로그인은 이름의 앞머리로(`bad`·`down`·`refresh`), 보호자 API 는 그 이름으로 만든 토큰의 앞머리로(`expired`·`susp`·`slow`·`empty`) 응답을 고른다. 첫 HTML 의 글자를 볼 때는 React 가 이어 붙인 글자 사이에 넣는 `<!-- -->` 를 걷어 낸다.
- 보호자 e2e 는 준비 스크립트가 만든 둘째 고객(모카)의 링크를 쓴다 — 알림장 e2e 의 살아 있는 링크("아직 아무도 열지 않았다")와 나눠 쓰지 않는다.
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

개발 서버는 compose 의 `web`(`next dev`, http://127.0.0.1:3010)이다. `API_BASE_URL`(`http://backend:8000`)·`AUTH_BASE_URL`(`http://auth:9000`)·`DEV_LOGIN` 은 compose 가 넣고, `REPORT_WEB_SECRET`(백엔드와 같은 값)과 `WEB_SESSION_SECRET` 은 저장소 루트의 `.env` 에서 읽는다.
