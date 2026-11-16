# ⑫-2 웹 — 사진 모아 보기 · 몸무게 · 가족 · 리뷰 줄 · 보던 자리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 로그인한 보호자가 아이의 사진·영상을 날짜를 넘어 모아 보고(확대·한 쪽 모두 저장), 몸무게 변화를 보고, 가족을 초대해 함께 본다. 알림장 끝에 리뷰 줄이 나오고, 한 장에서 [지난 알림장]으로 돌아오면 보던 자리다.

**Architecture:** 백엔드 ⑫-1 의 계약(`_docs/decisions/015-guardian-archive.md`)을 웹 서버가 부른다 — 보호자의 브라우저는 백엔드를 부르지 않는다. 새 경로 `/me/[linkId]/photos`, `/me/[linkId]/family-invite`(JSON), `/me/[linkId]/family-unlink`, `/j/[code]`, `/j/[code]/join`. 폴더 다섯 그대로.

**Tech Stack:** Next.js 16 App Router · TypeScript · Vitest · Playwright.

**Spec:** `docs/superpowers/specs/2026-11-16-guardian-archive-design.md` 3.1~3.6·5.3(8절의 답이 앞선다). 웹 규칙 `web/CLAUDE.md`.

## Global Constraints

- 페이지 상태 코드는 200·404·307 뿐, 쿠키는 경로 핸들러만, 상태를 바꾸는 POST 는 다른 출처 403, `console.*` 에 토큰·쿠키·서명 주소·초대 코드·요청 주소를 넣지 않는다, 외부 스크립트·`dangerouslySetInnerHTML` 없음.
- **리뷰 줄**: 매장 카드 아래·잇기·꼬리 위. 주소가 `https:` 일 때만(`new URL` 로 본다), `rel="noopener noreferrer nofollow"`, `target="_blank"`, 문구는 글자로만.
- **모두 저장**: 받는 것은 `download_url`(원본). 공유 시트는 **사진만이고 10개 이하일 때만**, 그 밖은 차례 내려받기. 진행 `저장하는 중… n / N`, 실패는 끝에 `N개를 받지 못했어요` 와 [다시 받기]. 모아 보기에서는 `이 쪽의 N개를 받아요. 다음 쪽은 넘어가서 한 번 더 눌러 주세요`. 화면을 연 지 하루가 넘었으면 받기 전에 새로 고치라고 알린다.
- **확대**: 사진만, 두 번 누르기 1↔2.5배, 두 손가락 벌리기 4배까지, 확대 중 끌어 옮기기, 넘기기·아래로 닫기는 1배일 때만. 라이브러리 없음.
- **보던 자리**: 목록에서 한 장으로 갈 때 목록 주소(경로·질의만 — 토큰·서명 주소 아님)와 스크롤을 `sessionStorage` 에, [지난 알림장]이 그 주소로 가서 그 자리(`#r<report_id>` 줄)로 내린다. 스크립트가 없으면 첫 쪽.
- **가족**: 초대 주소 `/j/<코드>` — 코드는 백엔드로 헤더로만, 웹 기록에 찍지 않는다(`check:server` 가 서버 출력에서 찾는다). `/j/<코드>` 는 백엔드를 부르지 않는다. 잇기 쿠키 `cn_join`(10분, 봉함 용도 `join`), 로그아웃이 지운다. 실패는 `/me?notice=invite` 한 가지 안내.
- 화면 문구에 "AI"·"법적 효력" 없음. 몸무게에 풀이·색 구분 없음.

## Review Focus

1. 초대 코드·`cn_join` 이 기록·주소·`next` 로 새는 길(로그인 왕복 포함).
2. 모두 저장에서 공유 시트가 영상·많은 장수로 메모리를 터뜨리거나, 한 파일 실패가 나머지를 멈춘다.
3. 확대 중 넘기기·닫기·뒤로 가기가 엉킨다(확대 상태에서 Esc·뒤로).
4. 보던 자리 키가 다른 연결·다른 아이 목록으로 잘못 돌아간다.
5. 리뷰 주소가 `javascript:`·대문자 스킴으로 와도 그리지 않거나(앞) 소리 없이 빠진다(뒤).

---

### Task 1: 리뷰 줄 · 보던 자리 · 모두 저장 규칙

`lib/report.ts`(`review_url?`·`review_text?`), `components/ReviewLine.tsx`, `ReportView` 순서, `ReportList` 의 `id="r<id>"`와 자리 적기(`components/ListPlace.tsx` 'use client'), 한 장의 [지난 알림장](`components/BackToList.tsx`), `SaveAllButton`(공유 조건·진행·실패·[다시 받기]·`note` prop). 테스트(RED 먼저): ReviewLine(https 만·rel·없으면 없음·대문자 스킴), ReportView 구역 순서, SaveAllButton(영상 섞임·11장이면 차례 내려받기, 진행, 실패 수와 다시 받기), 보던 자리(같은 연결만).

### Task 2: 사진 모아 보기 · 몸무게 · 확대

`lib/guardian.ts`(`getMedia`·`getWeights`, `GuardianLink` 의 `role`·`family_count`·`family_max`), `app/me/[linkId]/photos/page.tsx`, `components/PhotoArchive.tsx`(날짜 묶음 격자·거르기 링크·더 보기·크게 보기), `WeightChart.tsx`(SVG 선), `ReportList` 머리의 [알림장]·[사진], `next-path`(photos·year·phase), `Lightbox` 확대. 테스트: 격자·거르기·빈 화면·몸무게(점 하나면 목록만)·확대(두 번 누르기·1배에서만 넘기기)·safeNext.

### Task 3: 가족

`lib/guardian.ts`(`createInvite`·`getFamily`·`endFamily`·`joinFamily`), `app/me/[linkId]/family-invite/route.ts`(JSON `{url}`·no-store), `family-unlink/route.ts`, `components/FamilySection.tsx`(기본: [가족과 함께 보기]·한 줄 설명·한 사람 한 줄·[끊기]·[가족 모두 끊기]·새로 이었다는 한 번의 알림, 가족: `가족으로 함께 보는 기록이에요`), `app/j/[code]/page.tsx`, `app/j/[code]/join/route.ts`, `lib/session.ts`(`cn_join`), `/login/dev` 가 맡긴 초대를 쓴다, `/logout` 이 지운다, `/me?notice=invite`. 테스트: 컴포넌트·세션·경로.

### Task 4: 서버 확인 · e2e · 문서

`tests/server/fake-backend.mjs`(media·weights·family·family-links·연결의 role), `check.mjs`(새 경로의 상태 코드·헤더·`cn_join` 쓰고 지움·다른 출처 403·기록에 코드·`/j/` 없음), e2e(모아 보기·확대·한 쪽 저장의 내려받기 수·보던 자리·초대 → 다른 계정 잇기 → 그 한 명만 끊기·리뷰 줄), `web/CLAUDE.md`, 015 에 웹에서 정한 것. `pnpm test`·`build`·`check:server`·`e2e`.
