# ⑧-3 매출 통계 앱 — 이어지는 화면 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매출 탭의 숫자를 누르면 그 방문들·아이들로 이어지고, 사장이 월 목표를 정하고 요약을 글로 공유한다.

**Architecture:** `app/lib/features/sales` 안에서만 끝난다. API 셋(`/sales/visits`·`/sales/due-pets`·`PUT /sales/goal`)과 쪽 나눔 컨트롤러 하나(`SalesPagedController`), 목록 화면 둘(방문 목록·다시 올 때가 지난 아이), 목표 시트, 공유 글 규칙을 더하고 매출 탭의 줄을 누를 수 있게 한다. 방문 상세·반려동물 상세로는 라우터 경로로 간다.

**Tech Stack:** Flutter 3.41 · Riverpod · go_router · 기존 `design/widgets`·`shareSheetProvider`

**Spec:** `docs/superpowers/specs/2026-11-14-sales-design.md`(3.2 의 4·9·11·12·15·16, 3.3, 3.4, 3.5). API 계약과 ⑧-2 의 "남는 것"은 `_docs/decisions/011-sales.md`. 앱 규칙은 `app/CLAUDE.md`.

## Global Constraints

- 브랜치 `feat/sales-8-3-app-follow`(main 에서). 첫 커밋에 이 계획서. 커밋·주석·테스트 이름은 한국어, 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·병합은 사용자가 말할 때만. 과금·외부 연결 없음. 백엔드·웹은 바꾸지 않는다.
- `sales` 는 `auth` 만 import 한다. 방문 상세는 `/visits/{id}`, 반려동물 상세는 `/pets/{id}`. 화면 등록은 `core/router/app_router.dart`, 화면 키는 `ScreenKeys`.
- 톤은 ⑧-2 그대로(색은 사진에서만, 문장, 선과 여백). 서버에서 읽는 본문은 `AsyncBody`. 쓰기는 `runShopScoped`, 성공하든 실패하든 요약을 무효화한다.
- **공유 글에 아이·보호자의 이름과 번호를 넣지 않는다**(설계 3.4). 글의 모양은 설계 3.4 그대로다.
- 목표: 0~100,000,000원. 빈 칸·0 은 "목표 없음". **이번 달의 월 보기에서만** 정하고 보인다.
- 문구는 해요체, `AppStrings`. `print` 금지.
- 검증: `flutter analyze`(경고 0) · `flutter test` · 시뮬레이터 흐름 iOS·안드로이드.

## Review Focus

1. **목록의 끝과 실패** — 다음 쪽이 실패하면 이미 보인 줄은 그대로이고 [다시 시도]가 뜬다. 다시 불러오는 사이 끝난 옛 쪽이 새 목록에 붙지 않는다. 빈 목록은 안내 한 줄.
2. **목표 입력의 끝** — 빈 칸·0(지우기), 100,000,000(통과), 100,000,001(막힘), 붙여넣은 글자·쉼표, 연타(요청 한 번), 실패하면 시트가 남고 원인 문구.
3. **공유 글** — 조정 줄·미선택·기타 수단이 든 요약, 메뉴가 없는 요약, 진행 중·지난 기간·일·주·연의 머리. 이름·번호가 한 글자도 없다. 공유 시트가 실패하면 스낵바.
4. **이름을 보일 수 없는 방문** — `pet: null`(보호자만의 방문·익명화)인 줄도 보이고 눌러서 방문으로 간다. 금액 없는 줄에는 금액 자리에 아무것도 없다.
5. **지난 기간에서 누르기** — 지난 달의 노쇼 목록은 그 달의 것이다(span·anchor 가 그대로 넘어간다). 다시 올 때가 지난 아이는 기간과 상관없다.

---

### Task 1: API·쪽 나눔·명령·공유 글

**Files:** Modify `lib/features/sales/api/sales_models.dart`·`sales_api.dart`, `state/sales_providers.dart`·`sales_rules.dart`, `lib/l10n/app_strings.dart`, `test/support/sales_fixtures.dart`; Create `state/sales_paged.dart`·`sales_commands.dart`; Test `test/features/sales/api/sales_api_test.dart`, `state/sales_paged_test.dart`·`sales_commands_test.dart`·`sales_rules_test.dart`

**Interfaces — Produces:**

```dart
// models
enum SalesVisitFilter { unrecorded, noShow, canceled, menu }      // wire: unrecorded · no_show · canceled · menu
class SalesVisitItem { visitId, date(DateTime), pet(PetCard?), amount(int?) }
class DuePetItem { pet(PetCard), lastVisitDate(DateTime) }
class SalesPage<T> { items, nextCursor }
// api
Future<SalesPage<SalesVisitItem>> visits(int shopId, SalesSpan span, DateTime anchor, SalesVisitFilter filter, {int? menuId, String? cursor})
Future<SalesPage<DuePetItem>> duePets(int shopId, {String? cursor})
Future<int?> setGoal(int shopId, int? monthlyAmount)              // PUT /sales/goal → 저장된 값
// state/sales_paged.dart — 피드와 같은 규칙의 쪽 나눔(세대 번호로 옛 쪽을 버린다)
class SalesPagedState<T> { items, nextCursor, loadingMore, loadMoreError; bool get hasMore }
typedef SalesVisitsKey = ({int shopId, SalesSpan span, String anchor, SalesVisitFilter filter, int? menuId});
final salesVisitsProvider  (AsyncNotifierProvider.autoDispose.family<…, SalesPagedState<SalesVisitItem>, SalesVisitsKey>)  — notifier.loadMore()
final duePetsProvider      (… family<…, SalesPagedState<DuePetItem>, int shopId>)
// state/sales_commands.dart
class SalesCommands { Future<int?> setGoal(int shopId, int? amount) }   // finally: ref.invalidate(salesSummaryProvider)
final salesCommandsProvider
// state/sales_rules.dart
String shareText(String shopName, SalesSummary s)                 // 설계 3.4 의 네 줄(없는 줄은 뺀다)
String sinceLabel(DateTime lastVisit, DateTime today)             // '9주 전' — 7일 미만 'N일 전', 그 밖은 주(버림)
int? parseGoal(String text)                                       // 숫자만 읽는다. 빈 칸·0 → null. 100,000,000 초과 → throw FormatException
String visitsTitle(SalesVisitFilter f, {String? menuName})        // '금액을 적지 않은 방문' · '노쇼한 방문' · '취소한 방문' · '{메뉴} 한 방문'
```

- 공유 글: 1줄 `{매장} · {기간}` — 월 `2026년 11월`(진행 중이면 ` (14일까지)`), 연 `2026년`(진행 중이면 ` (11월 14일까지)`), 주 `2026년 11월 9일~15일`, 일 `2026년 11월 14일`. 2줄 `매출 3,250,000원 · 방문 48건`. 3줄 결제 수단을 ` / ` 로(`카드 2,400,000원`). 4줄 메뉴를 ` · ` 로(`전체 미용 2,100,000원(30건)`, 조정은 `조정 -10,000원`). 결제 수단·메뉴가 없으면 그 줄이 없다.
- [ ] 테스트 → 구현 → `flutter analyze`·`flutter test test/features/sales`. 커밋 `feat(sales): 방문 목록·다시 올 때가 지난 아이·목표의 API 와 쪽 나눔, 공유 글`.

---

### Task 2: 화면 — 목록 둘, 목표 시트, 누를 수 있는 줄, 공유

**Files:** Create `lib/features/sales/screens/sales_visits_screen.dart`·`due_pets_screen.dart`·`sales_goal_sheet.dart`; Modify `sales_tab.dart`·`sales_hero.dart`·`sales_sections.dart`·`sales_chart.dart`, `lib/core/router/app_router.dart`·`screen_keys.dart`, `lib/features/home/screens/home_shell.dart`; Test `test/features/sales/screens/sales_follow_test.dart`(+ 골든 `sales_visits.png`·`due_pets.png`), 기존 `sales_tab_test.dart` 수정

- 경로: `/sales/visits?span=&anchor=&filter=&menu_id=&menu=`(`ScreenKeys.salesVisits`), `/sales/due-pets`(`ScreenKeys.duePets`). 깨진 질의는 기본값(이번 달·`unrecorded`)으로 읽는다.
- 매출 탭에서 누를 수 있게 되는 것: 메뉴 줄(조정 제외) → 그 메뉴의 방문, 메뉴가 다섯을 넘으면 `모두 보기`(그 자리에서 펼친다), 노쇼·취소 숫자(0 이면 안 눌림) → 목록, `다시 올 때가 지난 아이 N마리 ›`, `금액을 적지 않은 완료 방문 N건 ›`, 목표 줄(이번 달) → 목표 시트, 목표가 없으면 `이번 달 목표 정하기`, 맨 아래 `요약 공유`.
- 목록 화면: 머리(뒤로 + 제목), `AsyncBody`, 줄마다 사진 34px·이름(없으면 `보호자만`은 쓰지 않고 날짜만)·날짜·금액, [더 보기]/다음 쪽 실패 [다시 시도], 빈 목록 `해당하는 방문이 없어요`·`다시 올 때가 지난 아이가 없어요`. 다시 올 때 줄: 사진·이름·`9주 전`.
- 목표 시트: 숫자 칸(원, 쉼표 없이 9자리까지), [저장]·[목표 지우기](목표가 있을 때). 저장 중 연타 막기, 실패는 시트 안 문구.
- ⑧-2 에서 미룬 것 가운데 함께 고치는 것: 오늘의 일 보기는 "어제보다"(진행 중인 날), 매출 탭의 `+` 는 오늘로 예약 등록, 주·연 보기의 축 글자를 막대 아래에 맞춘다, 요일 막대의 높이를 글자 크기에 맡긴다, 고른 날 카드의 읽기 이름에 금액, 단위 문구 상수, 연 막대 key 방어.
- [ ] 위젯 테스트(Review Focus 다섯 + 위 목록) → 구현 → 전체 `flutter test`·골든 눈으로 → 변이 둘(공유 글에 이름 넣기, 목표 연타 문지기 제거). 커밋 `feat(sales): 매출 탭에서 이어지는 화면 — 방문 목록, 다시 올 때가 지난 아이, 목표, 요약 공유`.

---

### Task 3: 시뮬레이터 흐름과 문서

- [ ] `integration_test/sales_tab_flow_test.dart` 를 넓힌다 — 금액 빠진 방문 목록 → 방문 상세, 노쇼 목록, 메뉴의 방문, 목표를 정하면 문장이 바뀜·지우면 사라짐, 요약 공유(공유 시트 대역이 받은 글에 매출이 있고 아이 이름이 없다). 준비 스크립트는 다시 올 때가 지난 아이 하나(60일 전 완료 방문)를 더하고, 1월 1일에도 돌게 올해 매출이 0 이면 연 단계를 건너뛴다.
- [ ] iOS 시뮬레이터와 안드로이드 에뮬레이터에서 통과, 스크린샷 확인.
- [ ] `app/CLAUDE.md`·`_docs/harness.md`·`_docs/decisions/011-sales.md`("⑧-3 에서 정한 것" + 검증 숫자). 커밋.
