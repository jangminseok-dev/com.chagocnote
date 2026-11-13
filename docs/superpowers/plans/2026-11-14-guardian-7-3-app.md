# ⑦-3 보호자 회원 앱(매장) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장 앱의 반려동물 상세 [보호자] 탭에서 그 고객 카드가 보호자 계정에 이어져 있는지 보고, 끊을 수 있다.

**Architecture:** `customer` 기능 안에서만 끝난다 — `customer/api` 에 호출 둘(읽기·끊기), `customer/state` 에 읽기 프로바이더와 끊기 명령, `customer/screens` 에 한 줄짜리 위젯 `GuardianLinkRow` 를 더해 `_OwnerTab` 에 꽂는다. 연결은 고객 상세와 따로 읽고, 읽는 중·실패·연결 없음이면 줄이 없다(방문 상세의 알림톡 블록과 같은 방식).

**Tech Stack:** Flutter 3.41 · Riverpod · go_router · 기존 `design/widgets`(AppCard·AppSheet·AppSheetAction·AppButton·Pressable·AppSnackBar)

**Spec:** `docs/superpowers/specs/2026-11-13-guardian-design.md`(4.5 앱, 5 보안 G13·G14, 7 검증). API 계약은 `_docs/decisions/010-guardian.md` 의 "⑦-2 웹·⑦-3 앱이 기댈 API 계약 — 매장". 앱 규칙은 `app/CLAUDE.md`.

## Global Constraints

- 브랜치 `feat/guardian-7-3-app`(main 에서). 첫 커밋에 이 계획서를 넣는다. 커밋 메시지·주석·테스트 이름은 한국어, 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·main 병합은 사용자가 말할 때만.
- 과금·외부 연결 없음. 백엔드·웹 코드는 바꾸지 않는다.
- **다른 기능 폴더를 import 하지 않는다**(`test/design/feature_imports_test.dart`). 새 코드는 `lib/features/customer/{api,state,screens}` 와 `lib/l10n`, `lib/core/error` 뿐이다. 기능 폴더 안은 세 층만.
- API(둘 다 `/v1/shops/{shopId}/customers/{customerId}/guardian-link`):
  - `GET` → 200 `{"linked": bool, "linked_at": "<매장 시간대 ISO>" | null}`. 소속이면 읽는다.
  - `DELETE` → 204. 연결이 없으면 404 `GUARDIAN_LINK_NOT_FOUND`. 권한은 `customer:write`(직원도 한다).
  - **보호자가 누구인지는 응답에 없다.** 앱도 묻지 않고 그리지 않는다.
- 매장 범위 호출은 `runShopScoped` 를 거친다. 화면은 `selectedShopIdProvider` 만 watch 한다(세션 전체를 보지 않는다).
- 문구는 해요체이고 이 계획서의 글자 그대로다(`test/design/copy_tone_test.dart`). `AppStrings` 에 둔다.
- 서버 응답의 필드명은 변환하지 않는다. 모델은 `fromJson` 을 직접 쓴다. `print`·`debugPrint` 금지.
- 검증 명령(`app/` 에서): `flutter analyze`(경고 0) · `flutter test`(골든 포함). 골든을 새로 만들 때만 `flutter test --update-goldens <파일>`.

## Review Focus

1. **`linked: true` 인데 `linked_at` 이 null 이거나 깨진 글자** — 줄은 "보호자 계정 연결됨"만 보이고(날짜 없이) 화면이 죽지 않는다. → 작업 1 의 모델 테스트, 작업 2 의 위젯 테스트.
2. **이미 끊긴 연결을 끊는다**(보호자가 먼저 끊었다 — 404 `GUARDIAN_LINK_NOT_FOUND`) — "이미 끊긴 연결이에요."를 알리고 줄이 사라진다(다시 읽는다). → 작업 1 의 명령 테스트, 작업 2 의 위젯 테스트.
3. **연타** — 확인 시트의 [연결 끊기]를 빠르게 두 번 눌러도, 끊는 동안 `···` 를 다시 눌러도 DELETE 는 한 번이다. → 작업 2.
4. **연결 읽기가 실패한다**(503·403) — 줄만 없고 보호자 탭의 나머지(이름·번호·예약·버튼)는 그대로다. 당겨서 새로고침하면 다시 읽는다. → 작업 2.
5. **끊는 도중 화면을 떠난다** — 응답이 온 뒤 예외(`setState` after dispose, 닫힌 context 의 스낵바)가 없다. → 작업 2.

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `lib/features/customer/api/customer_models.dart` (수정) | `GuardianLink` 모델 |
| `lib/features/customer/api/customer_api.dart` (수정) | `guardianLink`, `endGuardianLink` |
| `lib/features/customer/state/customer_providers.dart` (수정) | `guardianLinkProvider` |
| `lib/features/customer/state/customer_commands.dart` (수정) | `endGuardianLink` |
| `lib/features/customer/screens/guardian_link_row.dart` (새로) | 연결 한 줄, `···` 시트, 확인, 끊기 |
| `lib/features/customer/screens/pet_detail_screen.dart` (수정) | `_OwnerTab` 에 줄을 꽂고, 당겨서 새로고침에 연결도 |
| `lib/l10n/app_strings.dart`, `lib/core/error/error_messages.dart` (수정) | 문구, `GUARDIAN_LINK_NOT_FOUND` |
| `test/support/customer_fixtures.dart` (수정) | `guardianLinkJson` |
| `tool/prepare_guardian_flow.sh`, `integration_test/guardian_link_flow_test.dart` (새로) | 시뮬레이터 흐름 |

---

### Task 1: 호출·모델·프로바이더·명령

**Files:**
- Modify: `app/lib/features/customer/api/customer_models.dart`, `customer_api.dart`, `app/lib/features/customer/state/customer_providers.dart`, `customer_commands.dart`, `app/lib/core/error/error_messages.dart`, `app/test/support/customer_fixtures.dart`
- Test: `app/test/features/customer/api/customer_api_test.dart`, `app/test/features/customer/state/customer_commands_test.dart`

**Interfaces:**
- Produces:

```dart
// customer_models.dart
/// 고객 카드와 보호자 계정의 연결. 매장에는 여부와 이은 날만 온다 — 보호자가 누구인지는 없다.
class GuardianLink {
  const GuardianLink({required this.linked, required this.linkedAt});
  final bool linked;
  /// 이은 시각(매장 시간대 ISO). 연결이 없으면 null.
  final String? linkedAt;
  factory GuardianLink.fromJson(Map<String, dynamic> json);   // linked 가 true 가 아니면 false, linked_at 이 String 이 아니면 null
}

// customer_api.dart
Future<GuardianLink> guardianLink(int shopId, int customerId);      // GET  …/customers/$customerId/guardian-link
Future<void> endGuardianLink(int shopId, int customerId);           // DELETE 같은 경로

// customer_providers.dart
final guardianLinkProvider = FutureProvider.autoDispose.family<GuardianLink, CustomerKey>(…);   // runShopScoped

// customer_commands.dart
/// 매장이 보호자 연결을 끊는다. 성공하든 실패하든 그 고객의 연결을 다시 읽게 한다(이미 끊겼을 수 있다).
Future<void> endGuardianLink(int shopId, int customerId);

// test/support/customer_fixtures.dart
Map<String, dynamic> guardianLinkJson({bool linked = true, String? linkedAt = '2026-11-13T10:30:00+09:00'});
// linked 가 false 면 linked_at 은 null 로 낸다
```

- `error_messages.dart` 에 `'GUARDIAN_LINK_NOT_FOUND': '이미 끊긴 연결이에요.'`
- `endGuardianLink` 는 기존 `_write` 를 쓰지 않는다(목록·상세를 다시 부를 일이 아니다) — `runShopScoped` 로 부르고 `finally` 에서 `guardianLinkProvider((shopId:, customerId:))` 만 무효화한다.

- [ ] **Step 1:** `git checkout -b feat/guardian-7-3-app`, 계획서 커밋(`docs: ⑦-3 보호자 회원 앱 계획`).
- [ ] **Step 2: 실패하는 테스트**

```dart
// customer_api_test.dart
test('보호자 연결을 읽는다 — 경로와 응답', () async {
  // GET /v1/shops/3/customers/7/guardian-link → guardianLinkJson()
  // link.linked == true, link.linkedAt == '2026-11-13T10:30:00+09:00', 요청은 하나이고 본문이 없다
});
test('연결이 없으면 linked 가 false 이고 날짜가 null 이다', …);                       // guardianLinkJson(linked: false)
test.each 대신 for: {'linked': true}, {'linked': true, 'linked_at': 5}, {'linked': true, 'linked_at': null}
  → '이은 날이 없거나 글자가 아니어도 연결됨으로 읽고 날짜는 null 이다';
test('linked 가 true 가 아니면(없음·글자·null) 연결 없음이다', …);                   // {}, {'linked': 'true'}, {'linked': null}
test('모르는 칸이 더 와도 읽는다', …);                                               // {...guardianLinkJson(), 'guardian_name': 'x'} → 모델에 그런 칸이 없다
test('보호자 연결을 끊는다 — DELETE 이고 본문이 없다', …);                           // 204
test('없는 연결을 끊으면 GUARDIAN_LINK_NOT_FOUND 를 던진다', …);                     // 404 {code, message} → ApiException.code

// customer_commands_test.dart (기존 파일의 준비 방식을 그대로 쓴다)
test('연결을 끊으면 그 고객의 연결만 다시 읽고 목록·상세는 다시 읽지 않는다', …);
  // guardianLinkProvider 를 먼저 읽어 둔다 → endGuardianLink → GET guardian-link 가 한 번 더, 고객 목록·상세 GET 은 늘지 않는다
test('끊기가 실패해도(404) 연결을 다시 읽고 예외는 그대로 던진다', …);
test('끊기가 NOT_A_MEMBER 면 내 정보를 다시 불러온다', …);                           // gateway.refreshMeCallCount == 1
test('messageFor 는 GUARDIAN_LINK_NOT_FOUND 를 "이미 끊긴 연결이에요." 로 바꾼다', …);
```

- [ ] **Step 3:** `flutter test test/features/customer/api/customer_api_test.dart test/features/customer/state/customer_commands_test.dart` → 실패(없는 이름).
- [ ] **Step 4:** 모델·호출·프로바이더·명령·문구·픽스처를 구현한다.
- [ ] **Step 5:** 같은 명령 → 통과. `flutter analyze` 경고 0.
- [ ] **Step 6:** 커밋 `feat(customer): 보호자 연결 읽기와 끊기 — API, 프로바이더, 명령`.

---

### Task 2: 보호자 탭의 연결 줄과 끊기

**Files:**
- Create: `app/lib/features/customer/screens/guardian_link_row.dart`
- Modify: `app/lib/features/customer/screens/pet_detail_screen.dart`(`_OwnerTab`, `onRefresh`), `app/lib/l10n/app_strings.dart`
- Test: `app/test/features/customer/screens/guardian_link_row_test.dart`(새로), `app/test/features/customer/screens/pet_detail_screen_test.dart`(수정 + 골든 `goldens/pet_owner_tab_linked.png`)

**Interfaces:**
- Consumes: `guardianLinkProvider`, `CustomerCommands.endGuardianLink`, `GuardianLink`, `ShopTime.parse(…).wall`, `messageFor`, `AppSnackBar.show`, `AppSheet.show`, `AppSheetAction`.
- Produces: `class GuardianLinkRow extends ConsumerStatefulWidget { const GuardianLinkRow({super.key, required this.customerId}); }`

- 문구(`AppStrings`):

| 이름 | 글자 |
|---|---|
| `guardianLinked` | `보호자 계정 연결됨` |
| `guardianLinkedOn(int month, int day)` | `보호자 계정 연결됨 · {month}월 {day}일` |
| `guardianLinkMore` | `보호자 연결 더 보기` (`···` 의 semanticLabel) |
| `endGuardianLink` | `연결 끊기` |
| `endGuardianLinkConfirm` | `보호자가 지난 기록을 더는 볼 수 없어요. 알림장을 다시 보내면 다시 이을 수 있어요.` |
| `guardianLinkEnded` | `보호자 연결을 끊었어요.` |

- 동작:
  - `shopId` 가 없거나, 읽는 중이거나, 읽기가 실패했거나, `linked` 가 false 면 `SizedBox.shrink()` — **줄이 없다**. 실패를 알리지 않는다(보호자 탭의 본문이 아니다).
  - 이어져 있으면 `AppCard` 한 줄: 왼쪽 글자(`linkedAt` 을 `ShopTime.parse` 로 읽어 `guardianLinkedOn`, null 이거나 읽지 못하면 `guardianLinked`), 오른쪽 `Pressable(semanticLabel: guardianLinkMore)` 안의 `Icons.more_horiz`. 기존 `_InfoCard` 와 같은 아래 여백(`AppSpacing.sm`).
  - `···` → `AppSheet` 에 `AppSheetAction(label: endGuardianLink)` 하나 → 누르면 확인 시트(글 `endGuardianLinkConfirm`, 채운 버튼 `endGuardianLink`, 버튼 `AppStrings.cancel` — `pet_detail_screen.dart` 의 `_confirm` 과 같은 모양) → 확인하면 `endGuardianLink`.
  - 끊는 동안(`_busy`) `···` 는 눌리지 않는다. 성공하면 `AppSnackBar.show(guardianLinkEnded)`, 실패하면 `AppSnackBar.show(messageFor(e))`. 둘 다 `mounted` 일 때만. 명령이 연결을 다시 읽게 하므로 줄은 스스로 사라진다(또는 남는다).
  - 사장·직원 모두 같다(권한은 서버가 본다 — `customer:write`).
- 자리: `_OwnerTab` 의 노쇼 횟수 카드 아래, `_UpcomingVisits` 위.
- `PetDetailScreen` 의 `onRefresh` 에 `ref.invalidate(guardianLinkProvider)` 를 더한다.
- 기존 테스트: 보호자 탭을 여는 테스트의 가짜 핸들러에 `GET /v1/shops/3/customers/7/guardian-link` → `guardianLinkJson(linked: false)` 를 더한다(없으면 `fail` 로 떨어진다). 요청 수를 세는 기대가 있으면 맞춘다.

- [ ] **Step 1: 실패하는 테스트** — `guardian_link_row_test.dart`. `CustomerTestSetup` 과 `customerRouterApp` 로 반려동물 상세를 열고 보호자 탭을 누르는 도우미 `_openOwnerTab(tester, setup)` 를 둔다(가짜 핸들러는 pets/11·customers/7·guardian-link 를 답한다).

```dart
testWidgets('이어진 고객은 "보호자 계정 연결됨 · 11월 13일" 한 줄이 노쇼 횟수와 다가오는 예약 사이에 있다', …);
  // 글자 하나, 세로 자리: 노쇼 카드 < 줄 < 다가오는 예약
testWidgets('이어지지 않은 고객은 줄이 없고 연결 더 보기도 없다', …);
testWidgets('이은 날이 없거나 깨졌으면 "보호자 계정 연결됨" 만 보인다', …);        // linked_at: null, 'x'   (Review Focus 1)
testWidgets('연결을 읽지 못하면(503·403) 줄만 없고 이름·번호·예약·버튼은 그대로다', …);   // (Review Focus 4)
testWidgets('연결을 읽는 중에는 줄이 없다', …);                                    // Completer 로 응답을 붙들어 둔다
testWidgets('··· 를 누르면 [연결 끊기] 가 있는 시트가 뜬다', …);
testWidgets('확인 시트의 글은 설계의 글자 그대로이고, 취소하면 DELETE 를 보내지 않고 줄이 남는다', …);
testWidgets('확인하면 DELETE 를 한 번 보내고 "보호자 연결을 끊었어요." 를 알리고 줄이 사라진다', …);
  // DELETE 뒤의 GET 은 linked: false 를 답한다. calls 에서 DELETE 가 하나
testWidgets('이미 끊긴 연결이면(404) "이미 끊긴 연결이에요." 를 알리고 줄이 사라진다', …);   // (Review Focus 2)
testWidgets('끊기가 실패하면(503) 원인 문구를 알리고 줄이 남는다', …);
testWidgets('권한이 없으면(403 PERMISSION_DENIED) "이 작업을 할 권한이 없어요." 를 알리고 줄이 남는다', …);
testWidgets('끊는 동안 ··· 는 눌리지 않고, 확인을 빠르게 두 번 눌러도 DELETE 는 한 번이다', …);   // (Review Focus 3) DELETE 응답을 Completer 로 붙든다
testWidgets('끊는 도중 화면을 떠나도 예외가 없다', …);                              // (Review Focus 5) 뒤로 간 뒤 응답을 풀고 tester.takeException() == null
testWidgets('직원에게도 줄과 연결 끊기가 있다', …);                                // CustomerTestSetup(role: 'staff')
testWidgets('당겨서 새로고침하면 연결을 다시 읽는다', …);                           // GET guardian-link 가 한 번 더
testWidgets('다른 아이(같은 보호자)의 상세에서도 같은 고객의 줄이 보인다', …);         // /pets/12 → customers/7

// pet_detail_screen_test.dart
testWidgets('반려동물 상세 골든 — 보호자 탭, 보호자 계정 연결됨', …);                // goldens/pet_owner_tab_linked.png (390×844)
```

- [ ] **Step 2:** `flutter test test/features/customer/screens/guardian_link_row_test.dart` → 실패(위젯 없음).
- [ ] **Step 3:** 문구, `GuardianLinkRow`, `_OwnerTab`·`onRefresh` 를 구현한다. 기존 테스트의 핸들러에 연결 조회를 더한다.
- [ ] **Step 4:** 골든을 만든다 — `flutter test --update-goldens test/features/customer/screens/pet_detail_screen_test.dart --plain-name '보호자 계정 연결됨'` → 만들어진 그림을 눈으로 본다(줄이 카드 모양이고 글자가 잘리지 않는다). 기존 골든 `pet_detail.png` 는 바뀌지 않아야 한다(`git status` 로 확인).
- [ ] **Step 5:** `flutter analyze` 경고 0, `flutter test` 전체 통과(구조 테스트 — 기능 import·문구 말투·AsyncBody 사용 — 포함).
- [ ] **Step 6:** 변이 한 번 — `_busy` 문지기를 빼면 "DELETE 는 한 번" 테스트가 떨어지는 것을 보고 되돌린다.
- [ ] **Step 7:** 커밋 `feat(customer): 보호자 탭에 보호자 계정 연결 표시와 끊기`.

---

### Task 3: 시뮬레이터 흐름

**Files:**
- Create: `app/tool/prepare_guardian_flow.sh`, `app/integration_test/guardian_link_flow_test.dart`

**Interfaces:**
- 준비 스크립트(`infra/` 에서 `bash ../app/tool/prepare_guardian_flow.sh`, `prepare_report_flow.sh` 와 같은 틀 — `set -euo pipefail`, 본문은 변수로): 매장·사장·직원·고객(반려동물 모카)·어제 완료한 방문과 기록(사진 없음) → 알림장 보내기(`PUT …/report`, 받은 주소의 마지막 마디가 토큰) → 보호자 웹 세션 로그인(`"session":"web"`) → 잇기(`POST /v1/me/guardian/links`, 헤더 `X-Report-Token`) → 매장에서 `GET …/guardian-link` 가 `linked: true` 인지 확인. **토큰·주소는 찍지 않는다.** 마지막 줄: `--dart-define=SHOP=… --dart-define=PET=… --dart-define=OWNER=… --dart-define=STAFF=…`
- 흐름(`flow_kit.dart` 의 `step`·`login`·`logout`·`tap`·`waitFor`·`shot`·`btn`·`p`):

| 단계 | 하는 일 | 확인 |
|---|---|---|
| G1 | 사장 로그인 → `/pets/$PET` → [보호자] 탭 | "보호자 계정 연결됨 · {오늘 월}월 {오늘 일}일"(서울 날짜) 이 보인다. 스크린샷 |
| G2 | `···` → [연결 끊기] → 확인 시트에서 [취소] | 줄이 남아 있다 |
| G3 | 로그아웃 → 직원 로그인 → 같은 화면 → `···` → [연결 끊기] → 확인 | "보호자 연결을 끊었어요." 가 뜨고 줄이 사라진다. 스크린샷 |
| G4 | 당겨서 새로고침(또는 화면을 다시 연다) | 줄이 여전히 없다(서버에서 끊겼다) |

- [ ] **Step 1:** 준비 스크립트를 쓰고 `cd infra && D=$(bash ../app/tool/prepare_guardian_flow.sh | tail -1)` 로 돌려 본다(개발 스택이 떠 있어야 한다).
- [ ] **Step 2:** 흐름을 쓴다(파일 머리 주석에 준비·실행 명령).
- [ ] **Step 3:** iOS 시뮬레이터에서 — `SHOTS_DIR=<scratchpad> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/guardian_link_flow_test.dart -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 ${=D}` → 네 단계 통과. 스크린샷 둘을 눈으로 본다.
- [ ] **Step 4:** 안드로이드 에뮬레이터에서 준비를 새로 하고(`adb reverse tcp:8080 tcp:8080`) 같은 흐름 → 통과. 에뮬레이터를 띄울 수 없으면 그 사실을 기록에 적고 넘어간다.
- [ ] **Step 5:** 띄운 시뮬레이터·에뮬레이터를 끄고 커밋 `test(customer): 보호자 연결 흐름 — 연결 표시, 직원의 끊기`.

---

### Task 4: 문서

**Files:**
- Modify: `app/CLAUDE.md`, `_docs/harness.md`, `_docs/decisions/010-guardian.md`

- [ ] **Step 1:** `app/CLAUDE.md` "꼭 지킬 것"에 한 줄 — 보호자 연결(⑦-3): 자리(`customer/screens/guardian_link_row.dart`, 보호자 탭), 고객 상세와 따로 읽고 읽는 중·실패·없음이면 줄이 없다, 끊기는 `CustomerCommands.endGuardianLink`(성공·실패 모두 연결을 다시 읽는다), 직원도 끊는다, **보호자가 누구인지는 받지도 그리지도 않는다.**
- [ ] **Step 2:** `_docs/harness.md` 의 앱 흐름 목록에 `guardian_link_flow_test.dart`(준비 스크립트, 무엇을 보는지).
- [ ] **Step 3:** `010-guardian.md` 에 "⑦-3 앱에서 정한 것" — 줄의 자리와 없을 때, 실패를 알리지 않는 까닭, 이은 날의 표시(월·일, 해는 싣지 않는다), 404 의 문구, 미룬 것, 검증 숫자(`flutter test` 수, 흐름 단계 수와 기기).
- [ ] **Step 4:** `flutter analyze` · `flutter test` 마지막으로 한 번, 숫자를 문서에 적는다.
- [ ] **Step 5:** 커밋 `docs: ⑦-3 보호자 회원 앱 — 앱 규칙, 결정 기록 010`.
