# ⑪-A2 전자 동의서 — 웹 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보호자가 매장이 보낸 링크(`/f/<토큰>`)를 열어 로그인·설치 없이 미용 동의서를 읽고 이름과 손가락 서명으로 보낸다.

**Architecture:** 알림장과 같은 틀이다 — 웹 서버가 백엔드의 공개 API(`GET /v1/public/form`, `POST /v1/public/form/consent`)를 헤더 `X-Form-Token` 으로 부르고 HTML 을 만든다. 서명 칸만 브라우저 코드이고, 제출은 브라우저가 웹 자신의 경로 핸들러에 보내면 웹 서버가 백엔드로 넘긴다. 보호자의 브라우저는 백엔드를 직접 부르지 않는다.

**Tech Stack:** Next.js 16(App Router) · TypeScript · Vitest · Playwright. `web/` 에서 맥의 node·pnpm 으로 돌린다.

**Spec:** `docs/superpowers/specs/2026-11-16-consent-intake-design.md`(3.6 의 웹 8·10·11), `docs/superpowers/specs/2026-11-16-next-designs-common.md`, 백엔드의 계약 `_docs/decisions/014-consent-intake.md`

## 이 계획의 범위

- **한다**: `/f/[token]` 의 동의서 화면(열림·보냈어요·닫힘·없음·잠시 후), 서명 칸, 제출 경로, 미리보기 정보, 세 층의 테스트, 문서.
- **하지 않는다**: 문진표와 그 끝의 동의서 구역(⑪-C), 매장이 고친 문안의 표시 차이(⑪-B — 웹은 백엔드가 준 글을 그대로 그린다), 로그인한 보호자의 `/me` 에서 서명한 동의서 보기(나중).

## Global Constraints

- `web/CLAUDE.md` 의 규칙 전부. 특히: App Router 만 · 페이지의 상태 코드는 200·404 뿐 · 열 때 백엔드 조회는 한 번(`cache`) · 토큰 형식은 웹이 먼저 본다 · `process.env` 는 `lib/config.ts` 에서만 · 응답 헤더 셋 · 외부 스크립트·글꼴 금지 · `dangerouslySetInnerHTML` 금지 · 상태를 바꾸는 경로는 다른 출처면 403 · 토큰·서명 그림·적은 이름·요청 본문을 `console.*` 에 넣지 않는다 · `og:url`·canonical 금지 · 새 폴더를 만들지 않는다.
- 화면에 "법적 효력"·"AI" 라는 말이 없다. 널리 쓰는 말은 그대로 쓴다.
- **미리보기(og)에 아이 이름·지병을 싣지 않는다** — `{매장 이름}` 과 "미용 동의서"뿐이다.
- **편의 기준(설계 4절)**: 보호자가 글자를 치는 칸은 이름 하나, 그리고 서명 + 누르기 둘(체크, [동의하고 보내기]). 설치·가입이 없다. e2e 가 칸 수를 고정한다.
- 서명 그림은 600×240 PNG, 65,536바이트 이하(넘으면 300×120 으로 다시 그린다).
- 주석·문서·테스트 이름·커밋 메시지는 한국어. 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·병합은 사용자가 말할 때만.
- 검증(`web/` 에서): `pnpm test` · `pnpm build` · `pnpm check:server` · `pnpm e2e:prepare && pnpm e2e`.

## Review Focus

1. **보호자가 읽는 사이 내용이 바뀌었다(409)** → `내용이 바뀌었어요. 다시 읽어 주세요` 가 뜨고 새 문안으로 다시 그려진다. 적은 이름은 남고 서명은 비워진다.
2. **서명을 하지 않았거나 체크를 하지 않고 보낸다** → 보내지 않고 무엇이 빠졌는지 그 자리에서 말한다. 백엔드를 부르지 않는다.
3. **같은 링크를 두 번 낸다 / 뒤로 가기 뒤 다시 낸다** → 두 번째는 `보냈어요` 화면이다(410 을 오류로 보이지 않는다).
4. **폭 320 의 화면** → 서명 칸과 글이 가로로 넘치지 않고, 서명 칸 위에서 손가락을 움직일 때 화면이 따라 구르지 않는다.
5. **자바스크립트가 꺼져 있다** → 문안은 읽히고 `서명하려면 자바스크립트를 켜 주세요` 가 보인다. 빈 서명이 나가지 않는다.

---

### Task 1: 백엔드 호출과 경로

**Files:**
- Create: `web/lib/form.ts`, `web/app/f/[token]/page.tsx`, `web/app/f/[token]/submit/route.ts`
- Modify: `web/components/ErrorScreen.tsx`(서류용 문구)
- Test: `web/tests/form.test.ts`, `web/tests/ErrorScreen.test.tsx`

**Interfaces:**
- Produces (`lib/form.ts`):
  - `type ConsentPart = 'basic' | 'senior' | 'condition'`
  - `type OpenForm = { kind: 'consent'; state: 'open'; shop: { name: string }; previous_consent_on: string | null; pets: { name: string; conditions: string[]; parts: ConsentPart[] }[]; texts: Partial<Record<ConsentPart, { body: string }>>; doc_digest: string }`
  - `type SubmittedForm = { kind: 'consent'; state: 'submitted'; shop: { name: string }; submitted_on: string | null }`
  - `type FormResult = { kind: 'ok'; form: OpenForm | SubmittedForm } | { kind: ErrorKind }`
  - `fetchForm(token, clientIp): Promise<FormResult>` · `getForm = cache(fetchForm)` — 헤더 `X-Form-Token`·`X-Report-Web-Secret`·(있으면)`X-Report-Client-IP`, `cache: 'no-store'`, 5초 시간 제한. 토큰 모양이 아니면 부르지 않고 `not_found`. 404 → `not_found`, 410 → `closed`, 429 → `busy`, 그 밖·연결 실패 → `unavailable`.
  - `submitConsent(token, clientIp, body: { doc_digest: string; signer_name: string; signature_png: string }): Promise<number>` — 웹이 낼 상태 코드. 204·404·409·410·413·422·429 는 그대로, 그 밖은 503.
- `POST /f/<토큰>/submit` (JSON 본문) — 다른 출처면 403. `Content-Length` 가 없거나 131,072 를 넘으면 413(본문을 읽지 않는다). 본문이 JSON 이 아니거나 세 칸이 글자열이 아니면 422. 그 밖은 `submitConsent` 의 상태 코드를 본문 없이.
- `ErrorScreen` 에 `what?: 'report' | 'form'`(기본 `report`). `form` 이면 `서류를 찾을 수 없어요` / `닫힌 서류예요` + `기간이 지났거나 매장에서 닫은 서류예요. 매장에 다시 요청해 주세요.` 이고 로그인 링크가 없다. `busy`·`unavailable` 은 같은 글이다.
- 페이지: `generateMetadata` 와 본문이 `getForm` 을 나눠 쓴다. 열림·보냈어요 모두 제목 `미용 동의서`, og 는 `title: '미용 동의서'`, `description: {매장 이름}`, 그림은 `/og-default.png`. 오류면 `{}`.

- [ ] **Step 1: 실패하는 테스트** — `tests/form.test.ts`(`tests/report.test.ts` 의 방식 그대로): 공개 주소·`no-store`·헤더 셋, 접속 주소가 null 이면 헤더가 없다, 토큰 모양이 아니면 부르지 않는다, 상태 코드별 결과(200 열림·200 보냈어요·404·410·429·500·연결 실패·깨진 JSON), `submitConsent` 가 본문을 JSON 으로 보내고 상태 코드를 옮긴다(204·409·410·413·422·429, 500 → 503, 연결 실패 → 503). `tests/ErrorScreen.test.tsx`: 서류용 문구와 로그인 링크 없음.
- [ ] **Step 2: 실패를 본다** — Run: `pnpm test` · Expected: FAIL(모듈 없음)
- [ ] **Step 3: 구현한다**
- [ ] **Step 4: 통과를 본다** — Run: `pnpm test` · Expected: PASS
- [ ] **Step 5: 커밋** — `feat(web): 동의서의 백엔드 호출과 경로`

---

### Task 2: 화면과 서명 칸

**Files:**
- Create: `web/components/ConsentView.tsx`, `ConsentSubmit.tsx`('use client'), `SignaturePad.tsx`('use client'), `FormSubmitted.tsx`, `Consent.module.css`
- Modify: `web/app/f/[token]/page.tsx`
- Test: `web/tests/ConsentView.test.tsx`, `ConsentSubmit.test.tsx`, `SignaturePad.test.tsx`

**Interfaces:**
- `ConsentView({ form: OpenForm, token: string })` — 구역(`data-section`): `head`(영문 장식 `Consent` + 제목 `미용 동의서` + 매장 이름), `partial`(`previous_consent_on` 이 있을 때만: `지난번({YYYY년 M월 D일})에 동의하신 내용에 더해 바뀐 부분만 확인해 주세요`), `pets`(아이마다 이름과 `알려 주신 지병: 심장 질환 · 피부` — 지병이 없으면 그 줄이 없다), `part`(토막마다 — 제목 `미용 안내`·`나이가 많은 아이`·`지병이 있는 아이`, 아이가 둘 이상이면 `해당: 콩이 · 보리`, 글은 줄바꿈으로 문단을 나눈다), `sign`(`ConsentSubmit`), `foot`. 토막의 순서는 `basic`·`senior`·`condition`.
- `ConsentSubmit({ token, digest })` — 이름 칸(`name="signer_name"`, `maxLength=50`, `autoComplete="name"`), `SignaturePad`, 체크 `위 내용을 읽었고 동의합니다`, 버튼 `동의하고 보내기`. 보내기 전에 본다: 이름이 비었으면 `이름을 적어 주세요`, 서명이 없으면 `서명해 주세요`, 체크가 없으면 `동의에 체크해 주세요`(백엔드를 부르지 않는다). 보내는 동안 버튼은 `보내는 중…` 이고 눌리지 않는다. 결과: 204·410 → `router.refresh()`(보냈어요 화면이 된다) · 409 → `내용이 바뀌었어요. 다시 읽어 주세요` + `router.refresh()` + 서명 비우기(이름은 남는다) · 413·422 → `서명을 조금 간단하게 다시 적어 주세요` · 404 → `router.refresh()` · 그 밖 → `잠시 후 다시 보내 주세요`. `<noscript>` 에 `서명하려면 자바스크립트를 켜 주세요`.
- `SignaturePad({ onChange: (png: string | null) => void, resetKey })` — `<canvas width=600 height=240>`(CSS 로 폭 100%·비율 5:2), 포인터 이벤트로 검은 선(굵기 3)을 그린다, `touch-action: none`, [다시 쓰기]. 선을 뗄 때마다 `onChange(base64)` — `toDataURL('image/png')` 의 base64 가 87,380글자를 넘으면 300×120 캔버스에 줄여 그린 것을 준다. 비어 있으면 `null`. `aria-label="서명하는 곳"`.
- `FormSubmitted({ shopName, submittedOn })` — `보냈어요. {매장 이름}에서 확인할게요.` 와 (`submittedOn` 이 있으면) `{YYYY년 M월 D일}에 보냈어요`.

- [ ] **Step 1: 실패하는 테스트** — `ConsentView`: 토막 셋의 순서와 제목, `partial` 줄의 유무와 날짜 글자, 지병 줄의 유무, 가족 둘이면 `해당:` 줄, 글의 줄바꿈이 문단이 된다, 화면에 `법적`·`AI` 가 없다. `ConsentSubmit`(서명 칸은 가짜로 갈아 끼운다): 빠진 것 셋의 안내와 fetch 가 불리지 않음, 보낼 때의 주소·본문, 상태 코드별 동작(204·409·410·413·422·429·503), 보내는 동안 버튼 잠김, 409 뒤 이름이 남는다. `SignaturePad`: 선을 그리기 전에는 null, 그린 뒤에는 base64, [다시 쓰기]는 null(jsdom 에는 캔버스가 없으니 `getContext`·`toDataURL` 을 스텁으로 둔다), 큰 그림은 줄인 캔버스의 값을 준다. `FormSubmitted`: 글자와 날짜의 유무.
- [ ] **Step 2: 실패를 본다** — Expected: FAIL
- [ ] **Step 3: 구현한다.** 톤은 알림장과 같다(무채색, 잉크색 글자, 가는 선, 명조 제목). 폭 320 에서 넘치지 않는다.
- [ ] **Step 4: 통과를 본다** — Run: `pnpm test && pnpm build` · Expected: PASS, 빌드와 형 검사 통과
- [ ] **Step 5: 커밋** — `feat(web): 동의서 화면과 서명 칸`

---

### Task 3: 서버 응답·실제 브라우저·문서

**Files:**
- Modify: `web/tests/server/fake-backend.mjs`·`check.mjs`, `web/tests/e2e/prepare.mjs`, `web/CLAUDE.md`, `_docs/harness.md`, `_docs/decisions/014-consent-intake.md`
- Create: `web/tests/e2e/consent.spec.ts`

- [ ] **Step 1: 가짜 백엔드와 서버 검사** — 가짜 백엔드: `GET /v1/public/form` 은 `X-Form-Token` 의 앞머리로(`ok` 열림 — 아이 둘·토막 셋, `part` 부분 서명, `sent` 보냈어요, `gone` 410, `rate` 429, `boom` 500, `slow` 매달림, 그 밖 404), `POST /v1/public/form/consent` 는 `ok` 204·`chg` 409·`gone` 410·`big` 413·`bad` 422·`rate` 429. 서버 검사: 열림 200 과 헤더 셋, 첫 HTML 에 매장 이름·토막 제목·지병 이름이 있고 **백엔드 주소·`doc_digest` 밖의 ID 가 없다**, 미리보기 정보에 아이 이름·지병이 없다, 백엔드 호출 한 번, 보냈어요 200, 닫힘 200·없음 404·잠시 후 200, 모양이 틀린 토큰은 백엔드를 부르지 않는다, 제출의 상태 코드 옮기기, 다른 출처 POST 403, 큰 본문 413(백엔드를 부르지 않는다), 기록에 토큰·적은 이름·서명이 없다.
- [ ] **Step 2: 돌린다** — Run: `pnpm build && pnpm check:server` · Expected: 전부 통과
- [ ] **Step 3: e2e** — 준비 스크립트가 노령·지병 아이의 동의서 링크 둘을 만든다(서명용, 끊은 것). `consent.spec.ts`: 열기 → 글자를 치는 칸이 하나뿐이다 → 빠진 것의 안내 셋 → 이름·서명(마우스로 선)·체크 → 보내기 → `보냈어요` → 새로 고침해도 `보냈어요` → 끊은 링크는 닫힌 화면 → 지어낸 토큰 404 → 폭 320 에서 가로 넘침 없음 → 자바스크립트를 끄면 안내가 보이고 문안이 읽힌다 → 서명 뒤 매장 API 로 그 아이의 동의가 `signature` 인지 본다.
- [ ] **Step 4: 돌린다** — Run: `pnpm e2e:prepare && pnpm e2e` · Expected: 새 스펙과 기존 스펙 전부 통과
- [ ] **Step 5: 문서와 커밋** — `web/CLAUDE.md`(경로·구역·규칙·가짜 백엔드의 앞머리), `_docs/harness.md`, 결정 기록 014 에 "⑪-A2 웹에서 정한 것". `test(web): 동의서의 서버 검사와 e2e. docs: 웹 규칙, 014`
