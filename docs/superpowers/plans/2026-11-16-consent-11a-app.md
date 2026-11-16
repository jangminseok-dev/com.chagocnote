# ⑪-A3 전자 동의서 — 앱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사장이 방문 상세에서 동의서 링크를 공유 한 번으로 보내거나 그 자리에서 폰을 건네 서명받고, 받은 서명을 다시 볼 수 있고, 잘못 보낸 링크를 끊을 수 있다.

**Architecture:** 서류는 `features/customer` 가 갖는다(API·쓰기·화면). 방문 상세의 "확인할 것" 블록(`features/visit`)은 동의 줄에 버튼 셋을 달고 customer 의 쓰기와 화면을 부른다(`visit → customer` 는 허용된 방향). 현장 서명은 네이티브 화면이다 — `CustomPainter` 로 그리고 `dart:ui` 로 600×240 PNG 를 만든다. 웹뷰가 없다.

**Tech Stack:** Flutter(Riverpod 3, go_router) · 지금의 `ApiClient`·`ShareSheet`·`AsyncBody`·`AppSheet`. 새 패키지가 없다. 전부 `app/` 에서 돌린다.

**Spec:** `docs/superpowers/specs/2026-11-16-consent-intake-design.md`(3.3 의 현장 서명, 3.6 의 앱 2·3·5·7, 4절), `docs/superpowers/specs/2026-11-16-next-designs-common.md`(1·2·3·8절), 백엔드의 계약 `_docs/decisions/014-consent-intake.md`

## 이 계획의 범위

- **한다**: 확인할 것의 동의 줄(상태 글 셋과 버튼 셋), 동의서 보내기(공유 시트)·다시 공유, 현장 서명 화면, 반려동물 상세의 동의 줄(서명 받음·[서명 보기]), 서명 보기, 보낸 서류와 [링크 끊기], 시뮬레이터 흐름, 문서.
- **하지 않는다**: 예약 저장 뒤의 "보낼 것 시트"와 서류 설정(⑪-B), 받은 문진표(⑪-C), 달력·하루 줄의 표시(⑬).

## Global Constraints

- `app/CLAUDE.md` 의 규칙 전부. 특히: 웹뷰 금지 · 기능 폴더 안은 `screens`·`state`·`api` 세 층 · import 방향(`visit → customer` 만) · 서버에서 읽는 본문은 `AsyncBody` · 플러그인은 `core/proxy` 의 프로바이더로 · 서버의 상태 문자열은 `fromJson` 에서 enum 으로 한 번, `switch` 는 완전 열거 · 문구는 `AppStrings` 에(해요체) · `print` 금지 · 글래스는 떠 있는 조작 계층에만 · 누르는 것은 `Pressable(semanticLabel:)`·`AppButton`.
- **링크 주소에는 토큰이 들어 있다 — 로그·테스트 출력·스크린샷 설명에 남기지 않는다.** 테스트의 주소는 가짜다. 서명 그림·적은 이름도 남기지 않는다.
- 화면에 "법적 효력"·"AI" 라는 말이 없다. 널리 쓰는 말은 그대로 쓴다.
- **편의 기준(설계 4절)**: 동의서 보내기는 방문 상세에서 누르기 2번([동의서 보내기] → 공유 대상). 현장 서명 화면까지 누르기 1번([여기서 서명]). 링크를 다시 만들지 않는다(같은 링크). 설정을 열지 않고 된다. 시뮬레이터 흐름이 누른 수를 센다.
- **예약 날을 넘긴다**: 방문 상세에서 보내거나 서명받을 때 `for_date` 는 그 방문의 날(매장 시간대)이다.
- 서명 그림은 600×240 PNG, 흰 바탕, 검은 선. 65,536바이트를 넘으면 300×120 으로 다시 만든다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어. 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·병합은 사용자가 말할 때만.
- 검증(`app/` 에서): `flutter analyze`(경고 0) · `flutter test`(골든 포함 — 골든을 다시 찍으면 눈으로 본다) · 시뮬레이터 흐름 iOS·안드로이드.

## Review Focus

1. **손으로 [받았어요]를 적은 아이에게 [동의서 보내기]를 누른다**(409 `CONSENT_UP_TO_DATE`) → 무엇을 해야 하는지 말한다(`이미 받은 동의예요. 다시 받으려면 반려동물 화면에서 받은 기록을 지워 주세요.`). 조용히 실패하지 않는다.
2. **현장 서명 중에 내용이 바뀐다**(409 `CONSENT_DOCUMENT_CHANGED`) → 알리고 문서를 다시 읽고, 이름은 남기고 서명은 비운다.
3. **현장 서명 화면에서 보호자가 뒤로 간다** → 매장의 다른 화면이 보이지 않는다(뒤로 가기는 묻는다). 낸 뒤 [닫기]는 사장이 누른다.
4. **공유 시트가 실패한다 / 주소를 만드는 요청이 실패한다** → 스낵바로 알리고 버튼이 다시 눌린다. 링크는 서버에 만들어져 있을 수 있다 — 다시 누르면 같은 링크다.
5. **아이패드·가로·큰 글자** → 서명 칸이 화면 밖으로 나가지 않고, 공유 시트의 말풍선이 누른 버튼에 붙는다.

---

### Task 1: 모델·API·쓰기

**Files:**
- Create: `app/lib/features/customer/api/consent_models.dart`, `consent_api.dart`, `app/lib/features/customer/state/consent_commands.dart`, `consent_providers.dart`
- Modify: `app/lib/features/visit/api/check_models.dart`·`state/check_rules.dart`, `app/lib/features/customer/api/customer_models.dart`(`Pet.groomingConsentVia`), `app/lib/l10n/app_strings.dart`
- Test: `app/test/features/customer/api/consent_api_test.dart`, `state/consent_commands_test.dart`, `app/test/features/visit/api/check_models_test.dart`·`state/check_rules_test.dart`, `app/test/support/consent_fixtures.dart`

**Interfaces:**
- `enum ConsentPart { basic, senior, condition }` · `enum ConsentVia { signature, manual }` · `enum SignatureChannel { link('link'), inShop('in_shop') }`
- `FormLink { formId, url, expiresOn, sentOn }` · `SentForm { formId, customerId, customerName, pets: [(petId, name)], sentOn, expiresOn, url }` · `ConsentDocument { pets: [DocumentPet(petId, name, conditions, parts)], texts: Map<ConsentPart, String>, previousConsentOn, digest }` · `SignatureBrief { signatureId, signedAt, channel, signerName, parts }` · `SignatureDetail { …, pets: [SignaturePet(petId?, shownName, conditions, parts: [(part, body)])] }`. 모르는 토막·채널은 그 항목을 버린다.
- `ConsentApi`: `issue(shopId, petIds, {forDate}) → FormLink` · `forms(shopId) → List<SentForm>` · `revoke(shopId, formId)` · `document(shopId, petIds, {forDate}) → ConsentDocument` · `signInShop(shopId, {petIds, digest, signerName, png, forDate}) → int` · `signatures(shopId, petId) → List<SignatureBrief>` · `signature(shopId, signatureId) → SignatureDetail` · `signatureImage(shopId, signatureId) → Uint8List`.
- `ConsentCommands`: `send(shopId, petIds, {forDate}) → FormLink`, `revoke`, `signInShop` — 성공하든 실패하든 `sentFormsProvider`·`petDetailProvider`·`customerDetailProvider` 를 무효화하고 `careMarksChangedPlugProvider` 를 부른다(방문의 확인할 것이 낡는다).
- 프로바이더: `sentFormsProvider(shopId)`, `consentDocumentProvider((shopId, petIdsKey, forDate))`, `petSignaturesProvider((shopId, petId))`, `signatureDetailProvider((shopId, signatureId))`, `signatureImageProvider(…)`.
- `VisitCheck`: `ConsentState` 에 `partial`, `consentParts: List<ConsentPart>`, `formSentOn: DateTime?`. `checkLine`: `partial` 이면 `바뀐 부분만 다시 받아요 (노령·지병)`, 보낸 날이 있으면 뒤에 ` · 동의서를 보냈어요`.

- [ ] **Step 1: 실패하는 테스트** — API 의 경로·본문·질의(`for_date` 의 유무, `pet_ids` 반복), 모델의 읽기(모르는 토막을 버림, 날짜), 409 의 code 가 `ApiException.code` 로 온다, 쓰기가 실패해도 무효화한다, `check_models`: `partial`·`parts`·`form_sent_on` 읽기와 옛 응답(칸 없음), `check_rules`: 새 글 셋.
- [ ] **Step 2: 실패를 본다** — Run: `flutter test test/features/customer test/features/visit/api test/features/visit/state` · Expected: FAIL
- [ ] **Step 3: 구현한다**
- [ ] **Step 4: 통과를 본다** — Run: `flutter analyze && flutter test` · Expected: 경고 0, PASS
- [ ] **Step 5: 커밋** — `feat(consent): 앱의 동의서 모델·API·쓰기`

---

### Task 2: 동의 줄의 버튼 셋과 현장 서명

**Files:**
- Create: `app/lib/features/customer/screens/consent_sign_screen.dart`, `signature_pad.dart`, `app/lib/features/customer/state/signature_png.dart`
- Modify: `app/lib/features/visit/screens/visit_checks_block.dart`·`visit_detail_screen.dart`, `app/lib/core/router/app_router.dart`·`screen_keys.dart`, `app_strings.dart`
- Test: `app/test/features/customer/screens/consent_sign_screen_test.dart`(+골든), `signature_pad_test.dart`, `state/signature_png_test.dart`, `app/test/features/visit/screens/visit_checks_block_test.dart`·`visit_detail_screen_test.dart`

**Interfaces:**
- 동의 줄(방문 상세에만): 상태 글 아래에 `[동의서 보내기]`(보낸 날이 있으면 `[다시 공유]`)·`[여기서 서명]`·`[받았어요]`. `VisitChecksBlock` 은 `onSend(petId, origin)`·`onSignHere(petId)`·`onConsent(petId)` 를 받는다 — 주지 않은 것은 그리지 않는다(예약 등록의 미리 보기에는 버튼이 없다).
- 보내기: `ConsentCommands.send(shopId, [petId], forDate: 방문의 날)` → `shareSheetProvider.shareText(AppStrings.consentShareText(shopName, url), origin: 버튼의 사각형)`. 409 `CONSENT_UP_TO_DATE` 면 Review Focus 1 의 글.
- 경로 `/consent/sign?pet_ids=1,2&for_date=YYYY-MM-DD` → `ConsentSignScreen(petIds, forDate)`.
- `ConsentSignScreen`: `AsyncBody` 로 문서를 읽는다 → 아이·지병·토막(웹과 같은 제목 `미용 안내`·`나이가 많은 아이`·`지병이 있는 아이`, 가족이면 `해당:`), `바뀐 부분만` 줄 → 이름 칸 → `SignaturePad` → 체크 `위 내용을 읽었고 동의해요` → `[동의하고 보내기]`. 빠진 것은 그 자리에서 말한다(웹과 같은 글 셋). 성공하면 `보냈어요` 한 장과 `[닫기]`. 409 변경 → `내용이 바뀌었어요. 다시 읽어 주세요` + 다시 읽기 + 서명 비우기. 409 `CONSENT_UP_TO_DATE` → `이미 받은 동의예요` 와 [닫기]. 뒤로 가기는 `PopScope` 가 받아 `서명을 그만둘까요?` 를 묻는다.
- `SignaturePad({onChanged, controller})` — `SignatureController { strokes: List<List<Offset>>(0~1 로 정규화), isEmpty, clear() }`. 한 번에 포인터 하나만(`Listener` 의 `pointer` ID). 빈 칸에는 `여기에 서명해 주세요`. 비율 5:2, [다시 쓰기].
- `signaturePng(strokes) → Future<Uint8List>` — `PictureRecorder` 로 600×240 흰 바탕에 검은 선(굵기 3, 둥근 끝) → `toByteData(png)`. 65,536 을 넘으면 300×120.

- [ ] **Step 1: 실패하는 테스트** — 블록: 버튼 셋의 유무(콜백을 준 것만), `다시 공유` 로 바뀜, 미리 보기에는 없음. 상세: 보내기가 방문의 날을 넘기고 공유 시트에 주소를 준다, 409 의 글, 실패 뒤 다시 눌림. 서명 화면: 토막의 순서·`해당:`·`바뀐 부분만`, 빠진 것 셋, 보내는 본문(이름을 다듬음·지문·기준일), 성공 → `보냈어요`·[닫기], 변경 409, 뒤로 가기를 묻는다. 서명 칸: 그리기 전 빈 칸, 그린 뒤 `onChanged`, 둘째 포인터 무시, [다시 쓰기]. PNG: 머리 8바이트·폭 600·높이 240, 선이 있으면 가운데 점이 검다.
- [ ] **Step 2: 실패를 본다** — Expected: FAIL
- [ ] **Step 3: 구현한다**
- [ ] **Step 4: 통과를 본다** — Run: `flutter analyze && flutter test`(골든은 `--update-goldens` 뒤 눈으로 본다) · Expected: 경고 0, PASS
- [ ] **Step 5: 커밋** — `feat(consent): 동의 줄의 버튼 셋과 현장 서명 화면`

---

### Task 3: 서명 보기와 보낸 서류

**Files:**
- Create: `app/lib/features/customer/screens/consent_signatures_screen.dart`, `sent_forms_screen.dart`
- Modify: `grooming_consent_row.dart`, `customer_list_tab.dart`, `app_router.dart`, `app_strings.dart`
- Test: 두 화면과 두 줄의 위젯 테스트(+골든 하나)

**Interfaces:**
- 반려동물 상세의 동의 줄: `via == signature` 면 `2026년 11월 16일에 서명 받음` 과 `[서명 보기]`(→ `/pets/:petId/signatures`), `manual` 이면 지금 글(`…에 받았어요`). `···` 의 메뉴에 `동의서 보내기`·`여기서 서명`(기준일 없음)이 더해진다. 받은 것이 없으면 `[받았어요]` 옆에 `···` 로 같은 둘.
- `ConsentSignaturesScreen(petId)`: 목록(날짜·`링크로`/`매장에서`·적은 이름) → 한 장(그때의 글자·보인 지병·이름·서명 그림·시각, `링크를 받은 분이 적은 서명이에요`/`매장에서 받은 서명이에요`). 그림은 받은 바이트를 `Image.memory` 로 흰 바탕 위에 그린다.
- 고객 탭: 살아 있는 요청이 있을 때만 목록 위에 `보낸 서류 N`(→ `/forms`). 읽는 중·실패면 줄이 없다.
- `SentFormsScreen`: 줄마다 아이 이름들·보호자 이름·`11월 16일에 보냄 · 11월 30일까지`, `[다시 공유]`·`[링크 끊기]`(확인 시트). 끊으면 줄이 사라진다. 비면 `보낸 서류가 없어요`.

- [ ] **Step 1: 실패하는 테스트** / **Step 2: 실패를 본다** / **Step 3: 구현한다** / **Step 4: 통과를 본다**(`flutter analyze && flutter test`)
- [ ] **Step 5: 커밋** — `feat(consent): 서명 보기와 보낸 서류`

---

### Task 4: 시뮬레이터 흐름과 문서

**Files:**
- Create: `app/tool/prepare_consent_flow.sh`, `app/integration_test/consent_flow_test.dart`
- Modify: `app/CLAUDE.md`, `_docs/harness.md`, `_docs/decisions/014-consent-intake.md`

- [ ] **Step 1: 준비 스크립트와 흐름** — 준비: 매장·사장, 노령·지병 아이의 내일 예약 하나(와 define). 흐름: 방문 상세 → 동의 줄의 글 → [여기서 서명](누르기 1번) → 빠진 것 안내 → 이름·서명(끌기)·체크 → 보내기 → `보냈어요` → [닫기] → 동의 줄이 사라짐 → 반려동물 상세 `서명 받음` → [서명 보기] → 그림이 보인다 → (준비 스크립트가 지병을 더한 둘째 아이) `바뀐 부분만` → [동의서 보내기](누르기 수) → 고객 탭 `보낸 서류 1` → [링크 끊기] → 줄이 사라짐. 주소는 화면에 찍지 않는다.
- [ ] **Step 2: 돌린다** — iOS 시뮬레이터와 안드로이드 에뮬레이터 · Expected: 전부 통과
- [ ] **Step 3: 문서와 커밋** — `app/CLAUDE.md`(동의서 단락), `_docs/harness.md`, 014 에 "⑪-A3 앱에서 정한 것". `test(consent): 동의서 시뮬레이터 흐름. docs: 앱 규칙, 014`
