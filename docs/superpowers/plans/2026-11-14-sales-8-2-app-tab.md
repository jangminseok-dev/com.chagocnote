# ⑧-2 매출 통계 앱 — 매출 탭 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사장이 홈의 [매출] 탭에서 기간(일·주·월·연)의 매출을 큰 숫자와 그 매출을 만든 아이들의 사진으로 본다.

**Architecture:** 새 기능 폴더 `app/lib/features/sales/{api,state,screens}`. 요약 하나(`GET /sales/summary`)를 읽어 한 화면을 그린다. 문장·기간 이동·숫자 표기는 순수 함수(`state/sales_rules.dart`)에 두고 화면은 그것을 부른다. 차트는 직접 그린다(패키지 없음). `home` 이 탭으로 꽂고, 다른 기능 폴더는 import 하지 않는다 — 하루 화면으로는 라우터 경로로 간다.

**Tech Stack:** Flutter 3.41 · Riverpod · go_router · 기존 `design/widgets`

**Spec:** `docs/superpowers/specs/2026-11-14-sales-design.md`(3.1 낱말의 뜻, 3.2 매출 탭, 4.2 앱). API 계약은 `_docs/decisions/011-sales.md` 의 "⑧-2·⑧-3 앱이 기댈 API 계약". 기준 목업은 `.superpowers/brainstorm/50897-1794592195/content/sales-v2-photos.html` 의 ①·②. 앱 규칙은 `app/CLAUDE.md`.

## Global Constraints

- 브랜치 `feat/sales-8-2-app-tab`(main 에서). 첫 커밋에 이 계획서. 커밋·주석·테스트 이름은 한국어, 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·병합은 사용자가 말할 때만. 과금·외부 연결 없음. 백엔드·웹은 바꾸지 않는다.
- **`sales` 는 `auth` 만 import 한다**(`test/design/feature_imports_test.dart`). 하루 화면은 `context.push('/visits/day/YYYY-MM-DD')`.
- **톤**: 무채색, 검정 하나, 큰 세리프 숫자, 기울인 영문 라벨, 색은 사진에서만. **색 카드 격자·도넛·그라데이션·이모지·초록빨강 증감 표시를 쓰지 않는다.** 비교는 문장이다. 새 색·새 글꼴·차트 패키지를 들이지 않는다.
- 서버에서 읽는 본문은 `AsyncBody`(당겨서 새로고침 포함). 매장 범위 호출은 `runShopScoped`. 화면은 `selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider` 만 watch 한다.
- 직원에게는 API 를 부르지 않고 "매출은 사장님만 볼 수 있어요." 한 줄.
- 문구는 해요체, 이 계획서의 글자 그대로. `AppStrings` 에 둔다. 서버 필드명은 변환하지 않는다. `print` 금지.
- **이번 계획에서 누를 수 있는 것은 넷뿐이다**: 기간 세그먼트, ‹ ›, 막대(고르기), 고른 날 카드(하루 화면으로)·연 보기의 막대(그 달의 월 보기로). 메뉴·노쇼·취소·금액 빠진 방문·다시 올 때가 지난 아이의 목록, 목표 정하기, 요약 공유는 ⑧-3 이다 — 이번에는 줄만 보이고 `›` 를 그리지 않는다.
- 검증: `flutter analyze`(경고 0) · `flutter test`(골든 포함).

## Review Focus

1. **합이 어긋난 요약** — 결제 수단 합·칸의 합이 매출과 다르게 와도(읽는 도중 저장) 화면이 죽거나 음수 폭의 막대를 그리지 않는다. 조정이 음수여도 줄이 보인다.
2. **모든 칸이 0** — 완료 방문이 없는 기간, 최대값 0 으로 나누기 없음. 빈 문구가 보이고 예약·다시 올 때가 지난 아이는 그대로.
3. **기간 이동의 끝** — 이번 기간에서 › 는 눌리지 않는다. 1월 31일에서 월 → ‹ → 12월, 2월 29일의 연 → ‹, 해를 걸친 주. 일 보기에서 오늘 다음으로 못 간다.
4. **아주 큰 금액·긴 이름** — 99,999,999원이 큰 숫자 자리에서 넘치지 않는다(줄어든다). 긴 메뉴·아이 이름이 줄을 밀지 않는다.
5. **모르는 값** — `payments.method` 에 모르는 값, `buckets` 가 빈 목록(일 보기), `weekdays`·`report`·`goal`·`compare.*` 가 null, 사진 없는 아이. 어느 것도 화면을 죽이지 않는다.

---

### Task 1: 모델·API·프로바이더

**Files:** Create `lib/features/sales/api/sales_models.dart`·`sales_api.dart`, `lib/features/sales/state/sales_providers.dart`, `test/support/sales_fixtures.dart`, `test/features/sales/api/sales_api_test.dart`

**Interfaces — Produces:**

```dart
enum SalesSpan { day, week, month, year }            // wire 이름은 enum 이름 그대로
class PetCard { petId, name, photoUrl? }
class SalesSummary {
  span, start, end, elapsedEnd?(DateTime 날짜), revenue, visitCount, pricedCount, average?,
  previous?: CompareWindow{start,end,revenue}, yearAgo?, goalAmount?(int),
  petCount, newPetCount, returningPetCount, faces/newPets/returningPets: List<PetCard>,
  buckets: List<SalesBucket{key, revenue, visitCount, future, pets}>,
  payments: List<SalesPayment{method(String), amount}>,
  menus: List<SalesMenu{menuId?, name, amount, count, pet?}>,
  regulars: List<SalesRegular{pet, visitCount}>,
  remaining?, expectedAmount?, noShow, canceled, weekdays?: List<int>,
  report?: SalesReport{completed, sent, opened}, unrecordedCount, duePetCount
}
class SalesApi { Future<SalesSummary> summary(int shopId, SalesSpan span, DateTime anchor) }   // GET /v1/shops/$shopId/sales/summary?span=&anchor=YYYY-MM-DD
typedef SalesKey = ({int shopId, SalesSpan span, String anchor});                               // anchor 는 isoDay
final salesApiProvider, salesSummaryProvider (FutureProvider.autoDispose.family<SalesSummary, SalesKey>, runShopScoped)
// test/support/sales_fixtures.dart
Map<String, dynamic> salesSummaryJson({...})   // 11월(14일까지) 3,250,000원 — 목업의 숫자 그대로. 칸은 30개.
Map<String, dynamic> petCardJson(int id, String name, {String? photo})
```

- 날짜 문자열은 `parseDay` 로 읽는다. 모르는 `span` 이 오면 요청한 span 을 쓴다(서버 값을 믿지 않아도 화면이 죽지 않게). 목록이 없으면 빈 목록.
- [ ] 테스트: 경로·질의(`span=month&anchor=2026-11-14`) / 목업 픽스처 전체 해석 / null 들(`average`·`compare.*`·`goal`·`weekdays`·`report`·`remaining`·`expected_amount`·`photo_url`) / 조정 줄(`menu_id` null, 음수 금액) / 모르는 칸·모르는 `method` 를 그대로 읽는다. → 구현 → `flutter analyze`. 커밋 `feat(sales): 매출 요약 모델과 API`.

---

### Task 2: 문장과 기간 규칙 (순수 함수)

**Files:** Create `lib/features/sales/state/sales_rules.dart`, `test/features/sales/state/sales_rules_test.dart`; Modify `lib/l10n/app_strings.dart`

**Interfaces — Produces:**

```dart
String won(int amount)                                   // 3250000 → '3,250,000' , -5000 → '-5,000'
String amountPhrase(int amount)                          // 만 원으로 나누어떨어지면 '42만 원', 아니면 '425,000원'
DateTime shiftAnchor(SalesSpan span, DateTime anchor, int step)   // step ±1. 월은 그 달 1일로, 연은 그 해 1월 1일로
bool canGoNext(SalesSpan span, DateTime anchor, DateTime today)   // 다음 기간의 첫날이 오늘 뒤면 false
({String en, String? small, String? ko}) periodTitle(SalesSummary s)
    // 월: en 'November', small '2026' · 연: en '2026' · 주: ko '11월 9일 – 15일'(달이 다르면 '12월 28일 – 1월 3일') · 일: ko '11월 14일 토요일'
String? compareSentence(SalesSummary s)                  // 앞 기간. previous 가 null 이거나 그 매출이 0 이면 null
String? yearAgoSentence(SalesSummary s)                  // yearAgo 가 null 이면 null
String? goalSentence(SalesSummary s)                     // '이번 달 목표 500만 원의 65%' — goalAmount 가 null 이면 null. 퍼센트는 버림, 100 을 넘어도 그대로
double goalProgress(SalesSummary s)                      // 0.0~1.0 으로 자른다
String facesLine(SalesSummary s)                         // '41마리가 48번 다녀갔어요' / 아이가 0 이면 '48번 다녀갔어요'
String? selectedBucketKey(SalesSummary s, DateTime today) // 처음 고를 칸 — 오늘 칸이 있으면 그것, 없으면 방문이 있는 마지막 칸, 없으면 null
String paymentLabel(String method)                       // card 카드 · cash 현금 · transfer 이체 · none 미선택 · 그 밖 '기타'
```

- 비교 문장: `{앞 창의 이름}보다 {차이} 많아요.` / `적어요.` / 같으면 `{앞 창의 이름}{와|과} 같아요.`(받침에 따라).
  - 앞 창의 이름 — 진행 중(`elapsedEnd` 가 `end` 보다 앞): 일 `어제`, 주 `지난주 같은 요일까지`, 월 `지난달 {d}일까지`(d 는 견준 창의 끝날), 연 `작년 {m}월 {d}일까지`. 지난 기간: 일 `그 전날`, 주 `그 전 주`, 월 `그 전 달`, 연 `그 전 해`.
  - 작년 줄: `작년 같은 때보다 {차이} 많아요.` 등.
- 새 문구(`AppStrings`): `salesOwnerOnly` '매출은 사장님만 볼 수 있어요.' · `salesEmptyTitle` '아직 기록한 매출이 없어요' · `salesEmptyText` '방문을 완료하고 기록에 금액을 적으면 여기에 쌓여요.' · `salesAverage(String)` '한 번에 평균 {…}원' · `salesPayment` '결제 수단' · `salesMenu` '메뉴' · `salesGuests` '손님' · `salesBookings` '예약' · `salesWeekday` '요일' · `salesReport` '알림장' · `salesNewPets` '처음 온 아이' · `salesReturningPets` '다시 온 아이' · `salesRegulars` '단골' · `salesTimes(int)` '{n}번' · `salesCount(int)` '{n}건' · `salesHeads(int)` '{n}마리' · `salesRemaining` '남은 예약' · `salesExpected(String)` '정가로 약 {…}' · `salesNoShow` '노쇼' · `salesCanceled` '취소' · `salesDuePets(int)` '다시 올 때가 지난 아이 {n}마리' · `salesUnrecorded(int)` '금액을 적지 않은 완료 방문 {n}건' · `salesReportLine(c,s,o)` '완료한 {c}건 가운데 {s}건에 알림장을 보냈고, 보호자가 {o}건을 열어 봤어요.' · `salesSpanDay/Week/Month/Year` '일'·'주'·'월'·'연' · `salesPrev` '이전 기간' · `salesNext` '다음 기간' · `salesAdjustment` 는 서버가 준 이름을 그대로 쓴다.
- [ ] 테스트(값은 손으로): `won`·`amountPhrase`(420000 → '42만 원', 425000 → '425,000원', 0 → '0원', 100000000 → '1억 원' 은 하지 않는다 — '10000만 원') / `shiftAnchor`(1/31 월 −1 → 12/1, 3/31 월 −1 → 2/1, 2028-02-29 연 −1 → 2027-01-01, 주 ±7일) / `canGoNext` 넷 / `periodTitle` 넷과 달을 걸친 주 / 비교 문장의 표(많다·적다·같다·null·0, 진행 중과 지난 기간, 받침 와/과) / 목표(65%, 0%, 130%, null) / `selectedBucketKey` 셋 / `paymentLabel`. → 구현 → 커밋 `feat(sales): 매출 탭의 문장과 기간 규칙`.

---

### Task 3: 매출 탭 화면

**Files:** Create `lib/features/sales/screens/sales_tab.dart`·`sales_hero.dart`·`sales_chart.dart`·`sales_sections.dart`; Modify `lib/features/home/screens/home_shell.dart`, `lib/l10n/app_strings.dart`(쓰지 않게 된 `comingSoon*` 삭제), `test/features/home/screens/home_shell_test.dart`; Test `test/features/sales/screens/sales_tab_test.dart`(+ 골든 `goldens/sales_month_top.png`·`sales_month_bottom.png`·`sales_empty.png`)

**Interfaces:**
- `class SalesTab extends ConsumerStatefulWidget` — 상태: `SalesSpan _span = month`, `DateTime _anchor = 오늘`, `String? _picked`(고른 칸, 기간을 바꾸면 비운다).
- 홈 셸: 매출 탭을 `body: const SalesTab(), ownsHeader: true`, `+` 는 캘린더와 같은 예약 등록(`_reserve`)으로 바꾼다 — "다음 업데이트에서 만나요" 시트와 `_EmptyState` 는 없앤다(모든 탭에 `fab` 이 있다).
- 화면(위에서 아래로 — `Key`/`semanticLabel` 은 테스트가 찾는다):
  1. 머리: 매장 이름(`AppTypography.titleEn`) + 설정 톱니(`settingsLabel`).
  2. 기간: `AppSegment`(일·주·월·연) + ‹(`salesPrev`) ›(`salesNext`, `canGoNext` 가 아니면 `onTap: null`).
  3. 히어로: 기간 제목, 큰 숫자(`bigNumeral` 을 56px·자간 −2.5 로, `FittedBox(scaleDown)`) + '원', 비교 문장, 작년 문장, 목표 문장과 진행선(높이 2, 검정).
  4. 얼굴: 겹친 `AppPhotoTile`(34px, 여섯까지) + `facesLine` + 평균.
  5. 차트(`SalesChart`): 일 보기에는 없다. 칸마다 `Expanded` 막대(높이 = revenue / max, max 가 0 이면 전부 바닥선), 고른 칸은 검정·나머지 `AppColors.line`·future 는 점선 한 줄. 누르면 `onPick(key)`. 연 보기에서는 `onPick` 대신 `onOpenMonth(key)`.
  6. 고른 날 카드(주·월, 고른 칸이 있을 때): `AppGlassCard` — `dayHeading` + 금액, 사진이 있는 아이의 `AppPhotoFan`, 이름들. 누르면 `/visits/day/{key}`.
  7. 구역들(`sales_sections.dart`, 가는 선으로 나눈다): 결제 수단(이름·가는 막대·금액·비율 — 비율은 매출이 0 이면 그리지 않는다) / 메뉴(사진 26px·이름·건수·금액, 다섯 줄까지 — 여섯째부터는 이번에 숨긴다) / 손님(처음·다시 — 큰 숫자와 사진들, 단골 셋) / 다시 올 때가 지난 아이(0 이면 없음) / 예약(남은 예약 + 예상 금액, 노쇼, 취소) / 요일(월·연, 가장 높은 요일만 검정) / 알림장(문장) / 금액 빠진 방문(0 이면 없음).
- 빈 기간(`revenue == 0 && visitCount == 0`): 큰 숫자·얼굴·차트·결제·메뉴·손님·요일·알림장 대신 `salesEmptyTitle`·`salesEmptyText`. 예약·다시 올 때가 지난 아이는 그대로.

- [ ] **Step 1: 실패하는 위젯 테스트**(`CustomerTestSetup` + 요약을 주는 가짜 핸들러, `todayProvider` 는 2026-11-14)

```
직원에게는 "매출은 사장님만 볼 수 있어요." 만 보이고 요약을 부르지 않는다
사장은 이번 달의 매출·비교 문장·얼굴 줄·평균을 본다(목업 픽스처 — '3,250,000', '지난달 14일까지보다 42만 원 많아요.', '41마리가 48번 다녀갔어요')
기간을 [주]로 바꾸면 span=week 로 다시 읽고, ‹ 를 누르면 anchor 가 7일 앞이다 / 이번 기간에서 › 는 눌리지 않는다          (Review Focus 3)
칸을 누르면 그날의 카드가 뜨고(날짜·금액·이름), 카드를 누르면 하루 화면으로 간다
연 보기에서 막대를 누르면 그 달의 월 보기로 바뀐다
일 보기에는 차트가 없다
목표가 있으면 문장과 진행선이 있고 없으면 없다 / 작년 줄은 yearAgo 가 있을 때만
조정·미선택 줄이 온 그대로 보이고(음수 조정 포함) 모르는 결제 수단은 '기타' 다                                   (Review Focus 1·5)
빈 기간은 빈 문구이고 예약·다시 올 때가 지난 아이는 보인다                                                      (Review Focus 2)
0 인 줄(다시 올 때가 지난 아이·금액 빠진 방문)은 없다 / 사진 없는 아이는 빈 사진 칸
99,999,999원과 서른 글자 메뉴 이름에도 넘치지 않는다(tester.takeException() == null, 폭 320)                     (Review Focus 4)
읽기에 실패하면 원인 문구와 [다시 시도], 당겨서 새로고침하면 다시 읽는다
이번에는 메뉴·노쇼·다시 올 때가 지난 아이 줄에 누를 것이 없다(› 없음)
홈 셸: 매출 탭 머리에 매장 이름이 있고 + 는 예약 등록을 연다
골든: 월 보기 위, 아래로 내린 것, 빈 기간 (390×844)
```

- [ ] **Step 2~4:** 실패 확인 → 구현 → `flutter analyze` 0 · `flutter test` 전체(구조 테스트 포함 — 글래스 경계에 걸리면 캘린더의 미리보기 카드와 같은 자리로 허용 목록을 맞춘다). 골든 셋은 눈으로 본다.
- [ ] **Step 5:** 변이 — 직원 문지기 제거, `canGoNext` 제거 — 각각 해당 테스트가 떨어진다.
- [ ] **Step 6:** 커밋 `feat(sales): 매출 탭 — 큰 숫자와 그 매출을 만든 아이들`.

---

### Task 4: 실제 서버 확인과 문서

- [ ] iOS 시뮬레이터에서 `tool/run_dev.sh` 대신 짧은 흐름으로 본다 — `infra/` 에서 `bash ../backend/scripts/check_sales_flow.sh` 가 만든 매장(사장 `sflow-owner-<STAMP>`)으로 로그인해 매출 탭을 열고 스크린샷 둘(위·아래). 흐름 파일을 새로 만들지 않고 기존 `flow_kit` 을 쓰는 일회용 흐름 `integration_test/sales_tab_flow_test.dart`(월 보기의 매출 숫자가 흐름 스크립트의 숫자와 같다, 주 보기로 바꾸기, 직원 안내)를 둔다 — ⑧-3 이 이어서 넓힌다.
- [ ] `app/CLAUDE.md`(매출 탭 단락 — 톤 규칙, 누를 수 있는 것, 규칙 함수의 자리), `_docs/harness.md`(흐름 한 줄), `_docs/decisions/011-sales.md`("⑧-2 앱에서 정한 것" + 검증 숫자).
- [ ] 커밋 `test(sales): 매출 탭 흐름`·`docs: ⑧-2 매출 탭`.
