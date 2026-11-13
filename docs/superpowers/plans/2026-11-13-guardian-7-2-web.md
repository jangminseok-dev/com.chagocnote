# ⑦-2 보호자 회원 웹 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보호자가 받은 알림장에서 로그인해 계정을 잇고, `/me` 에서 우리 아이의 지난 미용 알림장을 모아 본다.

**Architecture:** 웹 서버(Next.js App Router)가 인증 프로세스에서 30분짜리 웹 세션 토큰을 받아 암호화한 httpOnly 쿠키에 두고, 그 토큰으로 백엔드의 `/v1/me/guardian/…` 를 부른다. 쿠키를 쓰는 일(로그인·로그아웃·잇기·끊기)은 전부 경로 핸들러(폼 POST → 303)이고, 페이지는 쿠키를 읽기만 한다. 브라우저는 백엔드를 부르지 않는다.

**Tech Stack:** Next.js 16.3(App Router) · React 19 · TypeScript · Web Crypto(AES-256-GCM, 새 의존성 없음) · Vitest · Playwright · pnpm

**Spec:** `docs/superpowers/specs/2026-11-13-guardian-design.md`(4.4 웹, 5 보안, 7 검증). API 계약은 `_docs/decisions/010-guardian.md` 의 "⑦-2 웹·⑦-3 앱이 기댈 API 계약". 웹 규칙은 `web/CLAUDE.md`.

## Global Constraints

- 브랜치 `feat/guardian-7-2-web`(main 에서). 첫 커밋에 이 계획서를 넣는다. 커밋 메시지·주석·테스트 이름은 한국어, 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·main 병합은 사용자가 말할 때만.
- **과금·외부 연결 없음.** 카카오·애플 버튼은 만들지 않는다(설정이 없다). 로그인은 개발용(`DEV_LOGIN`)뿐이다. 배포하지 않는다.
- 새 의존성을 더하지 않는다. 폴더는 `app`·`components`·`lib`·`public`·`tests` 뿐이다. 프록시(`proxy.ts`)·Pages Router 를 만들지 않는다.
- `process.env` 는 `lib/config.ts` 에서만 읽는다. `NEXT_PUBLIC_` 금지.
- 토큰(알림장·세션)·서명 주소·비밀값·요청 주소·응답 본문을 `console.*` 에 넣지 않는다. 알림장 토큰은 백엔드에 헤더 `X-Report-Token` 으로만 넘긴다.
- **웹 세션은 30분, 연장 없음.** 세션 쿠키 `cn_session`: httpOnly · SameSite=Lax · Path=/ · Max-Age = 백엔드의 `expires_in`(1800) · 운영(`NODE_ENV=production`)이면 Secure. 잇기 쿠키 `cn_claim`: 같은 속성에 Max-Age 600, 쓰면 지운다. 둘 다 암호화한다.
- **웹 서버는 `/v1/auth/social` 외의 `/v1/auth/*` 를 부르지 않는다.** 요청 본문은 늘 `"session": "web"` 이다.
- 상태를 바꾸는 경로(POST)는 `Sec-Fetch-Site` 가 있고 `same-origin` 이 아니면 403 이다.
- 응답 헤더 셋(`X-Robots-Tag: noindex, nofollow`, `Cache-Control: private, no-store`, `Referrer-Policy: no-referrer`)은 새 경로에도 있다. 루트(`/`)는 404 다.
- 백엔드 호출은 `cache: 'no-store'`, 시간 제한 5초(`AbortSignal.timeout(5000)`).
- 화면은 알림장의 글꼴·색·여백(`ReportView.module.css`·`ErrorScreen.module.css`의 변수와 톤)을 쓴다. 문구는 해요체이고 이 계획서의 글자 그대로다. `dangerouslySetInnerHTML` 금지.
- 검증 명령(`web/` 에서): `pnpm test` · `pnpm build` · `pnpm check:server` · `pnpm e2e:prepare && pnpm e2e`(compose 스택이 떠 있어야 한다).

## Review Focus

1. **`next` 로 밖으로 내보내기** — `/login?next=//evil.example`, `/\evil`, `https://…`, `/r/…` 를 넣어도 로그인 뒤 `/me` 로 간다. → 작업 1 의 `safeNext` 테스트, 작업 3 의 서버 검사.
2. **깨지거나 남이 만든 세션 쿠키** — 아무 글자·잘린 값·다른 용도(`claim`)로 봉한 값은 500 이 아니라 "로그인 안 됨"이다. → 작업 1 의 `open` 테스트, 작업 5 의 서버 검사(`/me` 가 `/login` 으로).
3. **로그인이 실패했을 때의 잇기 쿠키** — 인증이 내려가 로그인이 실패하면 잇기 쿠키는 남고(다시 시도하면 이어진다), 로그인이 되면 잇기 결과와 상관없이 지워진다. → 작업 4 의 서버 검사.
4. **매달린 백엔드** — `/me`·목록·한 장이 5초 뒤 "잠시 후 다시 열어 주세요"를 그리고 끝없이 돌지 않는다. → 작업 5 의 서버 검사(`timed`).
5. **이름 없는 아이·보호자만의 방문·빈 연결** — `pets[].name` 이 null 이면 "우리 아이", 목록의 `pet_name` 이 null 이면 날짜만, 아이가 없는 연결은 "아직 받은 알림장이 없어요". 숫자가 아닌 `linkId`·`reportId` 는 백엔드를 부르지 않고 404. → 작업 5·6 의 컴포넌트 테스트와 서버 검사.

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `lib/config.ts` (수정) | `authBaseUrl()`, `sessionSecret()`, `devLogin()`, `secureCookies()` 추가 |
| `lib/seal.ts` | 문자열을 용도별 키로 봉하고 연다(AES-256-GCM) |
| `lib/session.ts` | 세션·잇기 쿠키 읽기·쓰기·지우기 |
| `lib/next-path.ts` | 로그인 뒤 돌아갈 경로 검증, 경로 숫자 검증 |
| `lib/origin.ts` | `Sec-Fetch-Site` 검사, 303 응답 |
| `lib/auth.ts` | 웹 세션 로그인(`/v1/auth/social`) |
| `lib/guardian.ts` | 보호자 API 여섯 호출 |
| `lib/me.ts` | 페이지 공통 — 세션 요구, 실패를 이동·404·오류 화면으로 |
| `app/login/page.tsx`, `app/login/dev/route.ts`, `app/logout/route.ts` | 로그인 화면, 개발용 로그인, 로그아웃 |
| `app/r/[token]/claim/route.ts` | 잇기 |
| `app/me/page.tsx`, `app/me/[linkId]/page.tsx`, `app/me/[linkId]/[reportId]/page.tsx`, `app/me/[linkId]/unlink/route.ts` | 내 기록, 지난 알림장, 한 장, 끊기 |
| `components/LoginScreen.tsx`, `MyPets.tsx`, `UnlinkButton.tsx`, `ReportList.tsx`, `Member.module.css` | 화면 |
| `components/ReportView.tsx`·`ReportFoot.tsx`·`ErrorScreen.tsx` (수정) | 꼬리의 버튼, 닫힌 화면의 링크, `forbidden` 화면 |
| `tests/server/fake-backend.mjs`·`check.mjs` (수정), `tests/e2e/prepare.mjs` (수정), `tests/e2e/guardian.spec.ts` | 서버 검사·실제 브라우저 |

---

### Task 0: 브랜치와 설정

**Files:**
- Modify: `web/lib/config.ts`, `web/instrumentation.ts`, `web/tests/config.test.ts`, `infra/docker-compose.yml`(web 서비스), `.env.example`, `web/tests/server/check.mjs`(`startWeb` 의 env)
- 로컬만: 저장소 루트 `.env` 에 `WEB_SESSION_SECRET` 한 줄(커밋되지 않는다)

**Interfaces:**
- Produces:
  - `authBaseUrl(): string` — `AUTH_BASE_URL`, 끝의 `/` 를 뗀다. 필수.
  - `sessionSecret(): string` — `WEB_SESSION_SECRET`. 필수, **32글자 미만이면 변수 이름을 담아 던진다**(값은 메시지에 없다).
  - `devLogin(): boolean` — `DEV_LOGIN === '1'` 일 때만 true.
  - `secureCookies(): boolean` — `NODE_ENV === 'production'`.

- [ ] **Step 1:** `git checkout -b feat/guardian-7-2-web`, 이 계획서를 커밋(`docs: ⑦-2 보호자 회원 웹 계획`).
- [ ] **Step 2: 실패하는 테스트** — `tests/config.test.ts` 에 더한다.

```ts
test('AUTH_BASE_URL 끝의 / 를 뗀다', () => {
  vi.stubEnv('AUTH_BASE_URL', 'http://auth:9000/')
  expect(authBaseUrl()).toBe('http://auth:9000')
})
test.each([['없으면', undefined], ['비어 있으면', ''], ['32글자보다 짧으면', 'a'.repeat(31)]])(
  'WEB_SESSION_SECRET 이 %s 변수 이름을 말하며 던지고 값은 말하지 않는다', (_n, value) => {
    vi.stubEnv('WEB_SESSION_SECRET', value)
    expect(() => sessionSecret()).toThrow('WEB_SESSION_SECRET')
    if (value) expect(() => sessionSecret()).not.toThrow(value)
  })
test.each([['1', true], ['0', false], ['true', false], [undefined, false]])('DEV_LOGIN 이 %s 이면 %s', (value, expected) => {
  vi.stubEnv('DEV_LOGIN', value)
  expect(devLogin()).toBe(expected)
})
```
(`AUTH_BASE_URL` 없음·빔도 기존 `test.each` 모양으로 하나.)

- [ ] **Step 3:** `pnpm test tests/config.test.ts` → 실패(함수 없음).
- [ ] **Step 4:** 네 함수를 구현하고 `instrumentation.ts` 의 `register()` 가 `authBaseUrl()`·`sessionSecret()` 도 부르게 한다.
- [ ] **Step 5:** compose 의 `web.environment` 에 `AUTH_BASE_URL: http://auth:9000`, `DEV_LOGIN: "1"` 을 더하고 `depends_on` 에 `auth`. `.env.example` 에 `WEB_SESSION_SECRET=`(빈 값과 "32글자 이상, `openssl rand -base64 48`" 주석). 루트 `.env` 에 값이 없으면 `openssl rand -base64 48` 의 결과를 **화면에 찍지 않고** 한 줄 더한다. `check.mjs` 의 `startWeb` env 에 `AUTH_BASE_URL`(가짜 백엔드와 같은 주소), `WEB_SESSION_SECRET: 'check-server-session-secret-0123456789'`, `DEV_LOGIN: '1'`.
- [ ] **Step 6:** `pnpm test` 전체 통과, `cd ../infra && docker compose up -d web` 뒤 `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3010/nothing` → `404`(설정이 없으면 500 이다).
- [ ] **Step 7:** 커밋 `feat(web): 보호자 로그인 설정 — AUTH_BASE_URL, WEB_SESSION_SECRET, DEV_LOGIN`.

---

### Task 1: 봉하기·세션 쿠키·경로 검증

**Files:**
- Create: `web/lib/seal.ts`, `web/lib/session.ts`, `web/lib/next-path.ts`, `web/lib/origin.ts`
- Test: `web/tests/seal.test.ts`, `web/tests/session.test.ts`, `web/tests/next-path.test.ts`, `web/tests/origin.test.ts`

**Interfaces:**
- Consumes: `sessionSecret()`, `secureCookies()`.
- Produces:

```ts
// lib/seal.ts — 키 = SHA-256(`${purpose}:${sessionSecret()}`), 값 = base64url(iv 12바이트 ‖ 암호문+태그)
export type Purpose = 'session' | 'claim'
export function seal(purpose: Purpose, value: string): Promise<string>
export function open(purpose: Purpose, sealed: string): Promise<string | null> // 어떤 입력에도 던지지 않는다

// lib/session.ts — next/headers 의 cookies() 를 쓴다
export const SESSION_COOKIE = 'cn_session'
export const CLAIM_COOKIE = 'cn_claim'
export const CLAIM_TTL_SECONDS = 600
export type Session = { accessToken: string; expiresAt: number } // expiresAt 은 초(epoch)
export function readSession(): Promise<Session | null>            // 없음·못 엶·지남 → null
export function writeSession(accessToken: string, expiresIn: number): Promise<void>
export function clearSession(): Promise<void>
export function writeClaim(reportToken: string): Promise<void>
export function takeClaim(): Promise<string | null>               // 읽고 지운다. 토큰 모양이 아니면 null

// lib/next-path.ts
export function safeNext(value: string | null | undefined): string // 기본 '/me'
export function idFrom(value: string | undefined): number | null   // ^[1-9]\d{0,17}$ 만
export function cursorFrom(value: string | undefined): string | null // ^[A-Za-z0-9_=-]{1,300}$ 만

// lib/origin.ts
export function isCrossSite(request: Request): boolean // sec-fetch-site 가 있고 same-origin 이 아니면 true
export function seeOther(path: string): Response       // 303, Location 은 상대 경로 그대로
```

- `safeNext` 가 받는 모양은 `^/me(/[1-9]\d{0,17}){0,2}(\?pet=[1-9]\d{0,17})?$` 뿐이다.
- 세션 쿠키에 봉하는 값은 `JSON.stringify({ t: accessToken, e: expiresAt })`.

- [ ] **Step 1: 실패하는 테스트**

```ts
// seal.test.ts — beforeEach: vi.stubEnv('WEB_SESSION_SECRET', 's'.repeat(40))
test('봉한 값을 같은 용도로 열면 원래 글자다', async () => {
  expect(await open('session', await seal('session', '값'))).toBe('값')
})
test('같은 값을 두 번 봉하면 글자가 다르다', async () => {
  expect(await seal('session', 'x')).not.toBe(await seal('session', 'x'))
})
test('봉한 값에 원래 글자가 보이지 않는다', async () => {
  expect(await seal('session', 'access-token-글자')).not.toContain('access-token')
})
test.each(['', 'abc', '!!!!', 'A'.repeat(500)])('아무 글자(%s)는 null 이다', async (v) => {
  expect(await open('session', v)).toBeNull()
})
test('한 글자를 바꾸면 null 이다', async () => { /* 마지막 글자를 다른 base64url 글자로 */ })
test('다른 용도로 봉한 값은 null 이다', async () => {
  expect(await open('session', await seal('claim', 'x'))).toBeNull()
})
test('비밀값이 바뀌면 null 이다', async () => { /* seal 뒤 stubEnv 로 바꾸고 open */ })

// next-path.test.ts
test.each(['/me', '/me/12', '/me/12/345', '/me/12?pet=7'])('%s 는 그대로다', (v) => expect(safeNext(v)).toBe(v))
test.each([null, undefined, '', '//evil.example', '/\\evil.example', 'https://evil.example/me', '/r/abc', '/me/../r',
  '/me/0', '/me/12/345/6', '/me/12?pet=7&x=1', '/me/12?cursor=a', '/me\n', '/login'])('%s 는 /me 다', (v) => expect(safeNext(v)).toBe('/me'))
test.each([['12', 12], ['0', null], ['-1', null], ['1e3', null], ['12a', null], [undefined, null], ['9'.repeat(19), null]])(
  'idFrom(%s) 는 %s', (v, expected) => expect(idFrom(v)).toBe(expected))

// origin.test.ts
test.each([[null, false], ['same-origin', false], ['cross-site', true], ['same-site', true], ['none', true]])(
  'sec-fetch-site 가 %s 이면 isCrossSite 는 %s', …)
test('seeOther 는 303 이고 Location 이 상대 경로다', …)

// session.test.ts — vi.mock('next/headers') 로 Map 기반의 가짜 cookies()(get·set·delete, set 의 옵션을 기록)
test('세션을 쓰면 httpOnly·lax·path / ·maxAge 1800 이고 값에 토큰이 보이지 않는다', …)
test('NODE_ENV 가 production 이면 secure 다', …)          // vi.stubEnv('NODE_ENV','production')
test('쓴 세션을 읽으면 토큰과 끝나는 시각이 온다', …)
test('끝나는 시각이 지난 세션은 null 이다', …)             // vi.useFakeTimers 로 1801초 뒤
test('깨진 쿠키는 null 이다', …)
test('잇기 쿠키는 maxAge 600 이고 takeClaim 은 값을 주고 쿠키를 지운다', …)
test('takeClaim 은 토큰 모양이 아닌 값이면 null 이고 쿠키를 지운다', …)
```

- [ ] **Step 2:** `pnpm test tests/seal.test.ts tests/session.test.ts tests/next-path.test.ts tests/origin.test.ts` → 실패.
- [ ] **Step 3:** 네 파일을 구현한다. `seal` 은 `crypto.subtle`(전역)과 `crypto.getRandomValues` 를 쓴다. `open` 은 본문 전체를 try 로 감싼다.
- [ ] **Step 4:** 같은 명령 → 통과. `pnpm test` 전체 통과.
- [ ] **Step 5:** 커밋 `feat(web): 세션·잇기 쿠키 — 봉하기, 돌아갈 경로 검증, 같은 출처 검사`.

---

### Task 2: 백엔드 호출과 가짜 백엔드

**Files:**
- Create: `web/lib/auth.ts`, `web/lib/guardian.ts`
- Modify: `web/tests/server/fake-backend.mjs`
- Test: `web/tests/auth.test.ts`, `web/tests/guardian.test.ts`(`tests/report.test.ts` 처럼 `fetch` 를 `vi.stubGlobal` 로 대신한다)

**Interfaces:**
- Consumes: `apiBaseUrl()`, `authBaseUrl()`, `Report`·`Cover`(`lib/report.ts`).
- Produces:

```ts
// lib/auth.ts
export type LoginResult = { kind: 'ok'; accessToken: string; expiresIn: number } | { kind: 'rejected' | 'unavailable' }
/** POST {AUTH_BASE_URL}/v1/auth/social {provider, token, session: 'web'}. 200 이고 refresh_token 이 null 일 때만 ok. 4xx → rejected, 그 밖·예외 → unavailable. */
export function webLogin(provider: 'dev', token: string): Promise<LoginResult>

// lib/guardian.ts
export type Failure = { kind: 'unauthenticated' | 'forbidden' | 'not_found' | 'unavailable' } // 401 | 403 | 404·422 | 그 밖·예외
export type GuardianLink = { link_id: number; shop_name: string; linked_at: string }
export type GuardianPet = { pet_id: number; name: string | null }
export type ReportItem = { report_id: number; visit_date: string; pet_id: number | null; pet_name: string | null; cover: Cover | null; media_count: number }
export type ReportPage = { items: ReportItem[]; next_cursor: string | null }
export function getLinks(accessToken: string): Promise<{ kind: 'ok'; links: GuardianLink[] } | Failure>
export function getPets(accessToken: string, linkId: number): Promise<{ kind: 'ok'; pets: GuardianPet[] } | Failure>
export function getReports(accessToken: string, linkId: number, query: { petId: number | null; cursor: string | null }): Promise<{ kind: 'ok'; page: ReportPage } | Failure>
export function getGuardianReport(accessToken: string, linkId: number, reportId: number): Promise<{ kind: 'ok'; report: Report } | Failure>
export type ClaimResult = 'linked' | 'closed' | 'taken' | 'not_found' | 'busy' | 'unauthenticated' | 'unavailable' // 200·201 | 410 | 409 | 404 | 429 | 401 | 그 밖
export function claimLink(accessToken: string, reportToken: string): Promise<ClaimResult>
export function endLink(accessToken: string, linkId: number): Promise<'ended' | 'not_found' | 'unauthenticated' | 'unavailable'> // 204 | 404·422 | 401 | 그 밖
```

- `webLogin` 이 `refresh_token` 이 null 이 아닌 200 을 받으면 `unavailable` 이다(웹에 리프레시가 오면 안 된다 — 쿠키에 넣지 않는다).
- 가짜 백엔드에 더하는 것(한 포트가 API 와 인증을 함께 맡는다):
  - `POST /v1/auth/social`: 본문의 `token`(이름) 앞머리 — `down` 소켓 끊기, `bad` 401, `refresh` 200 인데 `refresh_token: "r"`, 그 밖 200 `{access_token: "tok-<이름>", refresh_token: null, token_type: "Bearer", expires_in: 1800, user_id: 1, is_new_user: false}`. `session` 이 `"web"` 이 아니면 422.
  - `/v1/me/guardian/…`: `Authorization` 의 토큰(`tok-<이름>`) 앞머리 — `tok-expired` 401, `tok-susp` 403 `ACCOUNT_SUSPENDED`, `tok-slow` 매달림, `tok-empty` 연결 없음, 그 밖은 표준 자료: 연결 `{link_id: 11, shop_name: 'Hiss Haus', linked_at: '2026-11-01T10:00:00+09:00'}`와 `{link_id: 12, shop_name: '둘째 매장', …}`; 11 의 아이들 `[{pet_id: 7, name: '두부'}, {pet_id: 8, name: null}]`, 12 의 아이들 `[]`; 11 의 알림장 — 첫 쪽 둘(`report_id` 501 두부 대표 있음 `media_count` 4, 502 `pet_id`·`pet_name`·`cover` null `media_count` 0)과 `next_cursor: 'c2'`, `cursor=c2` 면 하나(503)와 `next_cursor: null`, `pet_id=7` 이면 501 만; 한 장 501 → `FULL` 에 `expires_at: null`, 그 밖의 `report_id` 404 `REPORT_NOT_FOUND`; 다른 `link_id` 404 `GUARDIAN_LINK_NOT_FOUND`.
  - `POST /v1/me/guardian/links`: `X-Report-Token` 앞머리 — `ok` 201 `{link_id: 11}`, `gone` 410, `taken` 409 `GUARDIAN_ALREADY_LINKED`, `rate` 429, 그 밖 404. `DELETE /links/11` 204, 그 밖 404.
  - `/__stats` 에 `auth`(로그인 수), `claims`(잇기 수), `guardian`(그 밖의 보호자 호출 수), `last.session`(로그인 본문의 `session`), `last.bearer`(Authorization 이 있었는가 — 값은 적지 않는다), `last.report_token`(헤더가 있었는가)을 더한다. `/__reset` 이 함께 0 으로.

- [ ] **Step 1: 실패하는 테스트** — 호출마다 (a) 주소·메서드·헤더(`Authorization: Bearer …`, 잇기는 `X-Report-Token`)·`cache: 'no-store'`, (b) 상태 코드 → 결과의 표를 `test.each` 로.

```ts
test('웹 로그인은 인증 주소에 session: web 을 넣어 보낸다', async () => {
  // fetch 가 받은 url === 'http://auth:9000/v1/auth/social', JSON.parse(init.body) === {provider:'dev', token:'이름', session:'web'}
})
test('리프레시 토큰이 온 200 은 unavailable 이다', …)
test.each([[401, 'rejected'], [422, 'rejected'], [500, 'unavailable'], [503, 'unavailable']])('로그인 %s → %s', …)
test.each([[401, 'unauthenticated'], [403, 'forbidden'], [404, 'not_found'], [422, 'not_found'], [500, 'unavailable']])('getLinks %s → %s', …)
test('fetch 가 던지면 unavailable 이다', …)   // 여섯 호출 각각
test('getReports 는 pet_id 와 cursor 가 있을 때만 질의에 넣는다', …)
test.each([[201, 'linked'], [200, 'linked'], [410, 'closed'], [409, 'taken'], [404, 'not_found'], [429, 'busy'], [401, 'unauthenticated'], [500, 'unavailable']])('claimLink %s → %s', …)
test('claimLink 는 알림장 토큰을 헤더로만 보내고 주소·본문에 넣지 않는다', …)
test.each([[204, 'ended'], [404, 'not_found'], [422, 'not_found'], [401, 'unauthenticated'], [500, 'unavailable']])('endLink %s → %s', …)
```

- [ ] **Step 2:** `pnpm test tests/auth.test.ts tests/guardian.test.ts` → 실패.
- [ ] **Step 3:** 두 파일을 구현한다(`lib/report.ts` 의 `call` 과 같은 모양의 내부 함수 하나씩). 가짜 백엔드를 위 목록대로 넓힌다.
- [ ] **Step 4:** 통과 확인, `pnpm build && pnpm check:server` 가 기존 검사 전부 통과(가짜 백엔드 변경이 기존 것을 깨지 않았다).
- [ ] **Step 5:** 커밋 `feat(web): 보호자 API 와 웹 세션 로그인 호출, 가짜 백엔드 넓히기`.

---

### Task 3: 로그인과 로그아웃

**Files:**
- Create: `web/app/login/page.tsx`, `web/app/login/dev/route.ts`, `web/app/logout/route.ts`, `web/components/LoginScreen.tsx`, `web/components/Member.module.css`
- Modify: `web/tests/server/check.mjs`
- Test: `web/tests/LoginScreen.test.tsx`

**Interfaces:**
- Consumes: `webLogin`, `writeSession`, `clearSession`, `safeNext`, `isCrossSite`, `seeOther`, `devLogin`.
- Produces:
  - `LoginScreen({ dev, next, failed }: { dev: boolean; next: string; failed: boolean })`
  - `GET /login?next=&error=1` — 늘 화면을 그린다(세션이 있어도 이동하지 않는다 — `/me` 와 서로 돌지 않게).
  - `POST /login/dev`(폼: `name`, `next`) — `devLogin()` 이 꺼져 있으면 404. 다른 출처 403. 이름은 앞뒤 공백을 떼고 1~50글자가 아니면 `/login?error=1`. 성공 → 세션 쿠키 + 303 `safeNext(next)`. 실패(`rejected`·`unavailable`) → 303 `/login?error=1`(`next` 가 `/me` 가 아니면 `&next=` 로 이어 붙인다, `encodeURIComponent`).
  - `POST /logout` — 다른 출처 403. 세션 쿠키를 지우고 303 `/login`.
- 문구: 장식 `Sign in`, 제목 `로그인`, 설명 `로그인하면 우리 아이의 지난 미용 알림장을 모아 볼 수 있어요.`, 입력 라벨 `개발용 로그인 이름`, 버튼 `로그인`, 실패 `로그인하지 못했어요. 다시 시도해 주세요.`, 수단 없음(`dev` false) `로그인은 준비 중이에요.`
- `LoginScreen` 의 폼: `method="post" action="/login/dev"`, 숨은 칸 `next`. `data-section="login"`.
- 페이지 `metadata.title`: `로그인 — 차곡노트`.

- [ ] **Step 1: 실패하는 컴포넌트 테스트**

```tsx
test('개발용 로그인이 켜져 있으면 이름 칸과 /login/dev 로 가는 폼이 있다', …)   // form.action 끝이 /login/dev, method post, hidden next 값
test('꺼져 있으면 폼이 없고 "로그인은 준비 중이에요." 가 보인다', …)
test('실패했으면 "로그인하지 못했어요. 다시 시도해 주세요." 가 보인다', …)        // role="alert"
test('돌아갈 경로가 숨은 칸에 담긴다', …)                                        // next="/me/12"
```

- [ ] **Step 2:** `pnpm test tests/LoginScreen.test.tsx` → 실패.
- [ ] **Step 3:** 화면·페이지·두 경로를 구현한다. 페이지는 `searchParams` 의 `next` 를 `safeNext` 로, `error` 는 `'1'` 인지만 본다.
- [ ] **Step 4: 서버 검사를 더한다**(`check.mjs` 의 `checks`). 쿠키는 `res.headers.getSetCookie()` 로 읽고 다음 요청의 `cookie` 헤더로 넘기는 도우미 `cookieFrom(res, name)` 를 둔다.

```
- /login 은 200 이고 헤더 셋이 있고 폼이 /login/dev 로 간다
- POST /login/dev(name=ok) 는 303 /me 이고 cn_session 쿠키가 HttpOnly·Secure·SameSite=lax·Path=/·Max-Age=1800 이다   (check 는 next start = production)
- 그 쿠키 값에 tok-ok 가 보이지 않는다
- 로그인은 인증을 한 번 부르고 session 은 web 이다                       (stats.auth === 1, last.session === 'web')
- next=/me/11 이면 303 /me/11, next=//evil.example·https://evil.example·/r/x 는 303 /me       (Review Focus 1)
- 이름이 비었거나 51글자면 303 /login?error=1 이고 인증을 부르지 않는다
- 인증이 401(bad)·끊김(down)·리프레시를 줌(refresh)이면 303 /login?error=1 이고 Set-Cookie 에 cn_session 이 없다
- sec-fetch-site: cross-site 의 POST /login/dev·/logout 은 403 이고 인증을 부르지 않는다
- POST /logout 은 303 /login 이고 cn_session 을 지운다(Max-Age=0 또는 지난 Expires)
- DEV_LOGIN 없이 띄운 서버에서 POST /login/dev 는 404 이고 /login 에 폼이 없다     (둘째 next start 를 DEV_LOGIN 없이 띄운다 — startWeb 에 env 덮어쓰기 인자)
- 기록(log())에 로그인 이름으로 만든 tok-… 과 쿠키 값이 없다
```

- [ ] **Step 5:** `pnpm test && pnpm build && pnpm check:server` → 전부 통과. 새 검사 하나를 골라 구현을 잠깐 뒤집어(예: `safeNext` 를 빼고 `next` 그대로) 그 검사가 떨어지는 것을 본 뒤 되돌린다.
- [ ] **Step 6:** 커밋 `feat(web): 로그인 화면, 개발용 로그인, 로그아웃`.

---

### Task 4: 잇기

**Files:**
- Create: `web/app/r/[token]/claim/route.ts`
- Modify: `web/components/ReportView.tsx`, `web/components/ReportFoot.tsx`, `web/components/ErrorScreen.tsx`(+ css), `web/app/login/dev/route.ts`, `web/tests/server/check.mjs`, `web/tests/ReportView.test.tsx`, `web/tests/ErrorScreen.test.tsx`

**Interfaces:**
- Consumes: `claimLink`, `readSession`, `clearSession`, `writeClaim`, `takeClaim`, `isTokenShaped`, `isCrossSite`, `seeOther`.
- Produces:
  - `ReportView({ report, token }: { report: Report; token?: string })` — `token` 이 있을 때만 `ViewedSignal` 과 꼬리의 버튼이 있다(없으면 로그인한 보호자의 한 장이다).
  - `ReportFoot({ expiresAt, claimAction }: { expiresAt: string | null; claimAction?: string })` — `claimAction` 이 있으면 `<form method="post" action={claimAction}>` 과 버튼 `로그인하고 지난 기록 보기`(`data-section="claim"`). `ReportView` 는 `/r/${token}/claim` 을 넘긴다.
  - `ErrorScreen` — `closed` 화면에 링크 `로그인하고 지난 기록 보기`(`href="/me"`). 닫힌 링크로는 잇지 않으므로 폼이 아니라 링크다(설계 G3). 새 종류 `forbidden`: 장식 `Closed`, 제목 `이 계정으로는 볼 수 없어요`(설명·링크 없음). `ErrorKind` 에 `'forbidden'` 을 더한다.
  - `POST /r/[token]/claim`:
    1. 다른 출처 → 403. 토큰 모양이 아니면 404(백엔드를 부르지 않는다).
    2. 세션이 없으면 → `writeClaim(token)` + 303 `/login`.
    3. 세션이 있으면 `claimLink` → `linked`·`closed`·`not_found`·`busy`·`unavailable` 은 303 `/me`, `taken` 은 303 `/me?notice=taken`, `unauthenticated` 는 `clearSession()` + `writeClaim(token)` + 303 `/login`.
  - `POST /login/dev` 의 성공 뒤: `takeClaim()` 이 토큰을 주면 `claimLink` 를 부르고 `taken` 이면 303 `/me?notice=taken`, 그 밖은 303 `/me`(이때 `next` 는 쓰지 않는다). 잇기 쿠키가 없으면 지금처럼 `safeNext(next)`. **로그인이 실패하면 `takeClaim` 을 부르지 않는다**(쿠키가 남는다).

- [ ] **Step 1: 실패하는 컴포넌트 테스트**

```tsx
// ReportView.test.tsx
test('토큰이 있으면 꼬리에 /r/<토큰>/claim 으로 가는 폼 버튼 "로그인하고 지난 기록 보기" 가 있다', …)
test('토큰이 없으면 버튼도 열람 신호도 없다', …)     // fetch 스파이가 불리지 않는다, [data-section="claim"] 없음
// ErrorScreen.test.tsx
test('닫힌 화면에 /me 로 가는 링크 "로그인하고 지난 기록 보기" 가 있다', …)
test.each(['not_found', 'busy', 'unavailable', 'forbidden'])('%s 화면에는 그 링크가 없다', …)
test('forbidden 화면의 제목은 "이 계정으로는 볼 수 없어요" 다', …)
```

- [ ] **Step 2:** → 실패 확인.
- [ ] **Step 3:** 컴포넌트 셋과 경로를 구현하고 `/login/dev` 를 고친다. 기존 `ReportView` 테스트의 `token` 인자는 그대로 둔다.
- [ ] **Step 4: 서버 검사**

```
- 알림장(ok)의 첫 HTML 에 action="/r/<토큰>/claim" 폼이 있고, 닫힌 알림장(gone)에는 폼이 없고 href="/me" 가 있다
- 세션 없이 POST /r/<ok>/claim 은 303 /login 이고 cn_claim 이 HttpOnly·Max-Age=600 이며 값에 토큰이 보이지 않고 백엔드를 부르지 않는다
- 그 쿠키를 들고 로그인하면 303 /me 이고 잇기를 한 번 부르고(stats.claims === 1, last.report_token === true, last.bearer === true) cn_claim 을 지운다
- taken 토큰의 잇기 쿠키로 로그인하면 303 /me?notice=taken
- gone·rate·nf 토큰의 잇기 쿠키로 로그인하면 303 /me 이고 cn_claim 을 지운다
- 잇기 쿠키를 들고 로그인이 실패하면(bad) 잇기를 부르지 않고 Set-Cookie 에 cn_claim 삭제가 없다          (Review Focus 3)
- 세션이 있는 POST /r/<ok>/claim 은 303 /me 이고 잇기를 한 번 부르며 Set-Cookie 에 cn_claim 이 없다
- 세션(tok-expired)의 POST /r/<ok>/claim 은 303 /login 이고 cn_session 을 지우고 cn_claim 을 쓴다
- 형식이 틀린 토큰의 claim 은 404 이고 백엔드를 부르지 않는다          (MALFORMED_TOKENS 재사용)
- sec-fetch-site: cross-site 의 claim 은 403 이고 쿠키를 쓰지 않는다
- GET /r/<ok>/claim 은 405 다
- 기록에 토큰·쿠키 값이 없다           (USED_TOKENS 에 taken 을 더한다)
```

- [ ] **Step 5:** `pnpm test && pnpm build && pnpm check:server` 통과. 변이 — `/login/dev` 에서 `takeClaim` 뒤의 잇기 호출을 빼면 "잇기를 한 번 부르고"가 떨어진다 — 확인 뒤 되돌린다.
- [ ] **Step 6:** 커밋 `feat(web): 받은 알림장으로 잇기 — 꼬리의 버튼, 잇기 쿠키, 닫힌 화면의 로그인 링크`.

---

### Task 5: 내 기록(`/me`)과 끊기

**Files:**
- Create: `web/lib/me.ts`, `web/app/me/page.tsx`, `web/app/me/[linkId]/unlink/route.ts`, `web/components/MyPets.tsx`, `web/components/UnlinkButton.tsx`
- Modify: `web/components/Member.module.css`, `web/lib/format.ts`, `web/tests/format.test.ts`, `web/tests/server/check.mjs`
- Test: `web/tests/MyPets.test.tsx`, `web/tests/UnlinkButton.test.tsx`

**Interfaces:**
- Consumes: `readSession`, `getLinks`, `getPets`, `endLink`, `Failure`, `idFrom`, `isCrossSite`, `seeOther`, `clearSession`.
- Produces:

```ts
// lib/me.ts
/** 세션이 없으면 /login?next=<here> 로 보낸다(redirect 는 던진다). here 는 safeNext 를 통과하는 경로여야 한다. */
export function requireSession(here: string): Promise<Session>
/** unauthenticated → /login?next=<here> 로, not_found → notFound(), forbidden → 'forbidden', unavailable → 'unavailable'. */
export function screenFor(failure: Failure, here: string): 'forbidden' | 'unavailable'
// lib/format.ts
export function koreanFullDate(iso: string): string // '2026-11-01T10:00:00+09:00' → '2026년 11월 1일'
// components
export type ShopPets = { link: GuardianLink; pets: GuardianPet[] }
export function MyPets({ shops, notice }: { shops: ShopPets[]; notice: 'taken' | null })
export function UnlinkButton({ linkId, shopName }: { linkId: number; shopName: string }) // 'use client'
```

- `/me`: `requireSession('/me')` → `getLinks` → 연결마다 `getPets` 를 함께(`Promise.all`) → `MyPets`. 어느 호출이든 실패하면 `screenFor` 의 화면(`ErrorScreen`). `?notice=taken` 일 때만 `notice`. `metadata.title`: `내 기록 — 차곡노트`.
- `MyPets` 문구·구조(`data-section` — `me-head`·`notice`·`shop`·`empty`·`logout`):
  - 장식 `My notes`, 제목 `내 기록`.
  - `notice === 'taken'`: `이 알림장은 이미 다른 계정에 이어져 있어요. 매장에 문의해 주세요.`(`role="status"`)
  - 연결이 없으면: 제목 `아직 이어진 기록이 없어요`, 설명 `매장에서 받은 미용 알림장을 열고 [로그인하고 지난 기록 보기]를 눌러 주세요. 알림장이 닫혔다면 매장에 다시 보내 달라고 요청해 주세요.`
  - 매장마다: 매장 이름, `{koreanFullDate(linked_at)}부터`, 아이마다 링크(`/me/{link_id}?pet={pet_id}`, 글자는 `name ?? '우리 아이'`), 링크 `전체 기록 보기`(`/me/{link_id}`), `UnlinkButton`. 아이가 없으면 `아직 받은 알림장이 없어요`(전체 기록 링크는 그대로 둔다 — 보호자만의 방문이 있을 수 있다).
  - 맨 아래: `<form method="post" action="/logout">` 버튼 `로그아웃`.
- `UnlinkButton`: `<form method="post" action="/me/{linkId}/unlink">` 버튼 `연결 끊기`. `onSubmit` 에서 `confirm('{shopName}의 지난 기록을 더는 볼 수 없어요. 알림장을 다시 받으면 다시 이을 수 있어요. 연결을 끊을까요?')` 가 false 면 `preventDefault`. 자바스크립트가 꺼져 있으면 확인 없이 끊긴다.
- `POST /me/[linkId]/unlink`: 다른 출처 403 → `idFrom` 이 null 이면 404 → 세션 없으면 303 `/login` → `endLink` → `ended`·`not_found`·`unavailable` 은 303 `/me`, `unauthenticated` 는 `clearSession()` + 303 `/login`.

- [ ] **Step 1: 실패하는 테스트**

```tsx
// MyPets.test.tsx
test('매장마다 이름·이은 날·아이들 링크·전체 기록 링크·연결 끊기 폼이 있다', …)   // href="/me/11?pet=7", "/me/11", form action 끝 /me/11/unlink
test('이름이 없는 아이는 "우리 아이" 다', …)
test('아이가 없는 연결은 "아직 받은 알림장이 없어요" 이고 전체 기록 링크는 있다', …)
test('연결이 없으면 "아직 이어진 기록이 없어요" 와 안내가 보이고 매장 구역이 없다', …)
test('notice 가 taken 이면 안내가 보이고 null 이면 없다', …)
test('로그아웃 폼이 /logout 으로 간다', …)
test('매장 이름의 <script> 는 글자로 보인다', …)
// UnlinkButton.test.tsx
test('확인을 거절하면 제출되지 않는다', …)    // vi.spyOn(window, 'confirm').mockReturnValue(false) → submit 이벤트의 defaultPrevented
test('확인하면 제출되고 확인 글에 매장 이름이 있다', …)
// format.test.ts
test("koreanFullDate('2026-11-01T10:00:00+09:00') 은 '2026년 11월 1일' 이다", …)
```

- [ ] **Step 2:** → 실패 확인.
- [ ] **Step 3:** 구현.
- [ ] **Step 4: 서버 검사** — 로그인해 쿠키를 얻는 도우미 `loginAs(get, name)` 를 둔다.

```
- 세션 없는 /me 는 307 /login?next=%2Fme 이고 백엔드를 부르지 않는다
- 아무 글자·잘린 값·claim 용도로 봉한 값(= 잇기 쿠키 값을 cn_session 이름으로)의 cn_session 은 /login 으로 간다(500 이 아니다)   (Review Focus 2)
- 로그인한 /me 는 200 이고 헤더 셋이 있고 첫 HTML 에 Hiss Haus·두부·우리 아이·둘째 매장·"아직 받은 알림장이 없어요" 가 있다
- /me 는 연결 목록 한 번과 연결 수만큼의 아이들 조회를 부른다          (stats.guardian === 3)
- 연결이 없는 계정(empty)의 /me 는 "아직 이어진 기록이 없어요"
- /me?notice=taken 에 안내가 있고 /me?notice=<script> 에는 없다
- 끝난 토큰(expired)의 /me 는 307 /login?next=%2Fme
- 정지된 계정(susp)의 /me 는 200 "이 계정으로는 볼 수 없어요"
- 매달린 백엔드(slow)의 /me 는 5초 뒤 200 "잠시 후 다시 열어 주세요"    (timed, Review Focus 4)
- 첫 HTML 에 백엔드 주소와 tok- 이 없다
- POST /me/11/unlink 는 303 /me 이고 DELETE 를 한 번 부른다. /me/99/unlink 도 303 /me
- /me/abc/unlink·/me/0/unlink 는 404 이고 백엔드를 부르지 않는다
- 세션 없는 unlink 는 303 /login, cross-site 는 403 이고 백엔드를 부르지 않는다
- / 는 여전히 404 다                                                     (기존 검사 그대로 통과)
```

- [ ] **Step 5:** `pnpm test && pnpm build && pnpm check:server` 통과. 변이 — `requireSession` 을 빼면 "세션 없는 /me" 가 떨어진다.
- [ ] **Step 6:** 커밋 `feat(web): 내 기록 — 매장별 아이들, 연결 끊기, 로그아웃`.

---

### Task 6: 지난 알림장 목록과 한 장

**Files:**
- Create: `web/app/me/[linkId]/page.tsx`, `web/app/me/[linkId]/[reportId]/page.tsx`, `web/components/ReportList.tsx`
- Modify: `web/components/Member.module.css`, `web/tests/server/check.mjs`
- Test: `web/tests/ReportList.test.tsx`

**Interfaces:**
- Consumes: `requireSession`, `screenFor`, `getReports`, `getGuardianReport`, `idFrom`, `cursorFrom`, `ReportView`(토큰 없이), `koreanFullDate`.
- Produces:
  - `ReportList({ linkId, petId, page }: { linkId: number; petId: number | null; page: ReportPage })`
  - `/me/[linkId]?pet=&cursor=` — `idFrom(linkId)` 가 null 이면 `notFound()`(백엔드를 부르지 않는다). `pet`·`cursor` 는 모양이 틀리면 없는 것으로 친다. 돌아올 경로(`here`)는 `/me/{linkId}` 에 `pet` 이 있으면 `?pet=` 만 붙인다(`cursor` 는 싣지 않는다 — 다시 로그인하면 첫 쪽이다). `metadata.title`: `지난 알림장 — 차곡노트`.
  - `/me/[linkId]/[reportId]` — 둘 다 `idFrom`. `ReportView report={report}`(토큰 없음) 위에 링크 `지난 알림장`(`/me/{linkId}`, `data-section="back"`). 제목은 `reportTitle(report.pet_name)`. 미리보기(og) 정보는 넣지 않는다.
- `ReportList` 문구·구조(`data-section` — `list-head`·`item`·`more`·`empty`):
  - 위 링크 `내 기록`(`/me`), 장식 `Notes`, 제목 `지난 알림장`.
  - 항목마다 링크(`/me/{linkId}/{report_id}`): 대표가 있으면 `<img src={cover.url} width height alt="" loading="lazy">`, 없으면 빈 자리(같은 비율의 칸); `koreanFullDate(visit_date)`; `pet_name` 이 있으면 이름; `media_count > 0` 이면 `사진·영상 {n}`.
  - `next_cursor` 가 있으면 링크 `더 보기` — `/me/{linkId}?` + (`pet=…&`) + `cursor=…`(`encodeURIComponent`). 다음 쪽으로 넘어가는 링크다(쌓아 붙이지 않는다 — 서명 주소가 짧게 살아서 쪽마다 새로 받는다).
  - 항목이 없으면 `아직 받은 알림장이 없어요`.

- [ ] **Step 1: 실패하는 테스트**

```tsx
test('항목마다 한 장으로 가는 링크·날짜·이름·사진 수가 있다', …)        // href="/me/11/501", '2026년 9월 28일', '두부', '사진·영상 4'
test('이름·대표·사진이 없는 항목은 날짜만 있고 그림이 없다', …)          // 502: img 없음, '사진·영상' 없음
test('다음 쪽이 있으면 "더 보기" 가 cursor 를 담고, pet 이 있으면 함께 담는다', …)   // '/me/11?pet=7&cursor=c2'
test('다음 쪽이 없으면 "더 보기" 가 없다', …)
test('항목이 없으면 "아직 받은 알림장이 없어요" 다', …)
test('cursor 의 글자는 주소에 맞게 바뀐다', …)                           // 'a=b' → 'a%3Db'
```

- [ ] **Step 2:** → 실패 확인.
- [ ] **Step 3:** 구현.
- [ ] **Step 4: 서버 검사**

```
- 세션 없는 /me/11 은 307 /login?next=%2Fme%2F11, /me/11?pet=7 은 next=%2Fme%2F11%3Fpet%3D7, /me/11/501 은 next=%2Fme%2F11%2F501
- /me/11 은 200 이고 501·502 의 링크와 "더 보기"(cursor=c2)가 있고 목록 조회 한 번이다
- /me/11?cursor=c2 는 503 만 있고 "더 보기" 가 없다. /me/11?pet=7 은 501 만 있다
- /me/11?pet=abc·?cursor=<script> 는 그 인자 없이 조회한다(200, 첫 쪽)
- /me/12 는 200 "아직 받은 알림장이 없어요", /me/99 는 404, /me/abc·/me/0·/me/11/abc 는 404 이고 백엔드를 부르지 않는다   (Review Focus 5)
- /me/11/501 은 200 이고 케어 메모가 있고, "까지 열려요"·claim 폼·og:image 가 없고, 백엔드 조회 한 번이며 열람 신호 경로가 불리지 않는다
- /me/11/999 는 404
- 끝난 토큰의 /me/11·/me/11/501 은 /login 으로, 매달린 백엔드는 5초 뒤 "잠시 후 다시 열어 주세요"
- 새 경로 전부에 헤더 셋이 있다
- 기록에 tok-·쿠키 값·서명 주소(X-Amz-Signature)가 없다
```

- [ ] **Step 5:** `pnpm test && pnpm build && pnpm check:server` 통과. 변이 — 한 장 페이지에 `token` 을 넘기면 "claim 폼이 없고"가 떨어진다.
- [ ] **Step 6:** 커밋 `feat(web): 지난 알림장 목록과 한 장`.

---

### Task 7: 실제 브라우저 흐름

**Files:**
- Modify: `web/tests/e2e/prepare.mjs`
- Create: `web/tests/e2e/guardian.spec.ts`

**Interfaces:**
- `prepare.mjs` 가 `test-results/e2e-links.json` 에 더하는 것: `guardianLive`, `guardianClosed`(주소), `guardianLogin`(`e2e-guardian-<STAMP>`), `guardianOther`(`e2e-guardian-other-<STAMP>`), `guardianShop`(매장 이름). **기존 `live` 링크는 쓰지 않는다**(`report.spec.ts` 의 첫 테스트가 "아직 아무도 열지 않은 링크"를 본다) — 같은 매장에 둘째 고객(`김기록`, 반려동물 `모카`)과 완료한 방문 둘을 만든다: 방문 A 는 사진 하나·알림장 보냄(`guardianLive`), 방문 B 는 보낸 뒤 끊음(`guardianClosed`).

- [ ] **Step 1:** `prepare.mjs` 를 넓히고 `pnpm e2e:prepare` 가 끝나는지 본다(링크는 찍지 않는다).
- [ ] **Step 2: 흐름을 쓴다**(적힌 순서대로, `workers: 1`)

```ts
test('알림장의 버튼 → 개발용 로그인 → 내 기록에 매장과 아이가 보인다', …)
  // guardianLive 를 연다 → [로그인하고 지난 기록 보기] → /login → 이름 넣고 로그인 → URL 이 /me → 매장 이름·모카
  // 주소 창에 토큰이 든 새 주소가 생기지 않았다: page.url() 이 /login·/me 일 때 토큰 글자가 없다
test('아이를 누르면 지난 알림장이 한 장 있고, 누르면 알림장이 열린다(로그인 버튼과 기간 문구 없음)', …)
test('한 장에서 사진을 크게 보고 뒤로 가면 크게 보기만 닫힌다', …)
test('세션 쿠키가 사라진 뒤(30분 지남) 목록을 열면 로그인으로 가고, 로그인하면 보던 목록으로 돌아온다', …)
  // context.clearCookies({ name: 'cn_session' }) → /me/<id>?pet=<id> → /login?next=… → 로그인 → 같은 주소
test('다른 계정이 같은 알림장으로 이으려 하면 "이미 다른 계정에 이어져 있어요" 안내가 보이고 기록은 비어 있다', …)   // 새 context, guardianOther
test('닫힌 알림장의 [로그인하고 지난 기록 보기]는 로그인만 시키고, 이어진 계정이면 기록이 보인다', …)             // 새 context, guardianLogin
test('자바스크립트를 꺼도 로그인하고 내 기록과 목록을 본다', …)                                              // javaScriptEnabled: false
test('폭 320 에서 내 기록·목록이 옆으로 밀리지 않는다', …)       // report.spec 의 넘침 검사와 같은 식(scrollWidth <= clientWidth)
test('연결 끊기를 확인하면 내 기록이 비고, 그 연결의 목록 주소는 404 다', …)                                   // page.on('dialog', d => d.accept())
test('로그아웃하면 /me 는 로그인으로 간다', …)
```

- [ ] **Step 3:** `cd ../infra && docker compose up -d`(web 포함) 뒤 `pnpm e2e:prepare && pnpm e2e` → 기존 `report.spec.ts` 와 새 흐름 전부 통과.
- [ ] **Step 4:** 백엔드 쪽이 그대로인지 — `cd ../infra && bash ../backend/scripts/check_guardian_flow.sh` 30줄 통과.
- [ ] **Step 5:** 커밋 `test(web): 보호자 흐름 — 잇기, 내 기록, 다시 로그인, 끊기`.

---

### Task 8: 문서

**Files:**
- Modify: `web/CLAUDE.md`, `CLAUDE.md`(루트), `_docs/harness.md`, `_docs/decisions/010-guardian.md`

- [ ] **Step 1:** `web/CLAUDE.md` — 머리말을 "알림장 한 장과 보호자의 내 기록"으로, 고칠 규칙:
  - 경로 목록(알림장 둘 + `/login`·`/login/dev`·`/logout`·`/r/[token]/claim`·`/me`·`/me/[linkId]`·`/me/[linkId]/[reportId]`·`/me/[linkId]/unlink`). 루트는 여전히 404.
  - "페이지의 상태 코드는 200·404, 그리고 로그인이 필요한 곳의 307" · 쿠키를 쓰는 일은 경로 핸들러(303)만 — 페이지는 쿠키를 쓰지 못한다.
  - 세션 규칙(30분·연장 없음·봉한 쿠키 둘·`Secure` 는 운영에서), `/login` 은 세션이 있어도 이동하지 않는다, `next` 는 `safeNext` 만, 웹 서버는 `/v1/auth/social` 만 부른다, 리프레시가 오면 버린다.
  - 설정 넷 필수 + `DEV_LOGIN`.
  - 로그인한 한 장은 `ReportView` 에 토큰을 넘기지 않는다(열람 신호·버튼·기간 없음).
  - 테스트 세 층의 표에 새 검사, `data-section` 새 이름.
- [ ] **Step 2:** 루트 `CLAUDE.md` 의 웹 줄("보호자 알림장")을 "보호자 알림장·내 기록"으로, 웹 규칙 한 줄에 "세션 토큰도 로그에 찍지 않는다"를 더한다. `_docs/harness.md` 의 웹 검증 줄을 맞춘다.
- [ ] **Step 3:** `010-guardian.md` 에 "⑦-2 웹에서 정한 것" — 쿠키 둘과 봉하기 방식, 닫힌 화면은 링크(잇기 쿠키를 만들지 않는다), 잇기 결과의 갈래(409 만 안내, 410·404·429 는 조용히 `/me`), [더 보기]는 다음 쪽 링크, 끊기 확인은 스크립트(꺼져 있으면 확인 없음), 정지 계정 화면, 미룬 것(카카오·애플 버튼, 쌓아 붙이는 더 보기, 웹 탈퇴) 그리고 검증 숫자(`pnpm test` 수, `check:server` 검사 수, e2e 수).
- [ ] **Step 4:** `pnpm test && pnpm build && pnpm check:server` 마지막으로 한 번, 숫자를 문서에 적는다.
- [ ] **Step 5:** 커밋 `docs: ⑦-2 보호자 회원 웹 — 웹 규칙, 결정 기록 010`.
