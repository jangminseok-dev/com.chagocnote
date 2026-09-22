# 차곡노트 ② 고객·반려동물 — 계획 ②-2: 앱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈의 "고객" 탭을 채운다 — 가족 카드 목록(목록·격자, 정렬, 검색, 다음 페이지), 등록 3단계(전화번호 → 보호자 → 반려동물, 이미 있는 번호면 반려동물 추가로 건너뛰기), 반려동물 상세(탭 [기본 / 질병 / 보호자], 형제 이동, 무지개다리, 삭제), 반려동물 추가·수정, 보호자 수정, 고객 삭제(사장만). 끝에 시뮬레이터에서 사용자와 흐름을 확인하고 결정 기록 005 에 앱 몫을 더한다.

**Architecture:** 기능 폴더 `app/lib/features/customer/{api,state,screens}` 세 층. `api/`는 ②-1 의 API 14개를 부르는 `CustomerApi`와 평범한 모델 클래스(`fromJson` 직접). `state/`는 Riverpod — 조회는 `autoDispose.family`(목록은 조회 조건 레코드가 키라 늦게 온 옛 검색 결과가 새 결과를 덮지 않는다), 쓰기는 `CustomerCommands` 한 곳에서 `runShopScoped`를 거쳐 보내고 끝나면 목록·상세를 다시 부르게 한다. `screens/`는 `design/widgets`만 쓰고, 새 위젯 두 개(`AppChoiceChip`·`AppIconToggle`)를 `design/widgets`에 더한다. 라우트는 `/customers/new`·`/customers/:id/edit`·`/customers/:id/pets/new`·`/pets/:id`·`/pets/:id/edit` 다섯 개를 더하고, 모두 매장이 선택되어 있어야 열린다.

**Tech Stack:** Flutter 3.44.8 · Dart 3.12 · flutter_riverpod 3.4 · go_router 18 · dio 5 · flutter_test(골든) — 새 의존성 없음. 백엔드는 바꾸지 않는다(Task 11 의 흐름 확인에서 `infra/`의 개발 환경을 띄운다).

**Spec:** `docs/superpowers/specs/2026-09-22-customer-pet-design.md` — 이 계획은 11절의 "②-2 앱"이다: 2절 표의 앱 몫(검색·목록·정렬·등록 흐름·상세·입력 지연), 8절 전부, 9절 위협 점검표의 앱 몫(C4·C5·C7·C8·C12), 10절의 앱 테스트와 완료 기준. 실행자는 설계 문서와 함께 `_docs/decisions/005-customer-pet.md`(②-2 가 기댈 API 계약 — **요청·응답 모양, 오류 코드, 커서, 번호 형식, 나이 표시**), `_docs/decisions/004-flutter-app-and-reauth.md`(앱 골격의 규칙과 검토 교훈), `app/CLAUDE.md`를 읽는다. 목업은 `.superpowers/brainstorm/94815-1790061769/content/`의 `customer-list-v2.html`(A안), `customer-detail.html`(A안), `register-flow.html`(A안)이다.

**계획의 위치:** ②의 구현 계획 두 개 가운데 두 번째다. ②-1(백엔드, `main`에 들어가 있다) → **②-2(이 문서, 앱)**. 이 계획이 끝나면 설계 10절의 완료 기준(시뮬레이터에서 등록부터 고객 삭제까지)을 사용자와 확인한다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 앱 명령은 `app/`에서, 백엔드 명령은 `infra/`에서 돌린다.
- 작업 브랜치는 `feat/customer-2b-app`다(`main` `81283dc`에서 땄고, 이 계획서 커밋이 첫 커밋이다). `main`에서 직접 작업하지 않는다.
- **사용자가 작업 단위 커밋을 허용했다(2026-09-22).** 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 테스트의 매장 이름으로 쓰는 것은 괜찮다. 앱 이름은 "차곡노트"다.
- 이 계획은 새 의존성을 추가하지 않는다(`pubspec.yaml`을 건드리지 않는다). 날짜 선택기를 쓰려고 `flutter_localizations`를 넣지 않는다(Task 3 참고).
- **`dart format`은 이 계획이 새로 만든 파일에만 돌린다.** 기존 파일은 저장소의 형식이 지금 포매터와 달라, 디렉터리째 돌리면 수십 개 파일이 바뀐다(참조 구현에서 한 번 겪었다). 수정하는 기존 파일은 diff 그대로만 바꾼다.
- 볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다.
- 비밀값·토큰·**고객의 전화번호와 이름**을 로그에 남기지 않는다. `print`·`debugPrint`·dio `LogInterceptor`를 쓰지 않는다(`avoid_print`는 오류다). 모델에 필드를 나열하는 `toString`을 두지 않는다(설계 8.2, C7).
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (`app/CLAUDE.md`, 결정 기록 004 그대로)
- 기능 폴더 `lib/features/customer/` 안은 `api/` · `state/` · `screens/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
- 서버 응답의 필드명은 바꾸지 않는다. 모델은 평범한 클래스에 `fromJson`을 직접 쓴다. 코드 생성기를 쓰지 않는다.
- 화면은 `lib/design/widgets`만 쓴다. 새 위젯이 필요하면 `design/widgets`에 더한다. `liquid_glass_widgets`는 `lib/design/bridge/` 밖에서 import 하지 않는다.
- **스크롤 목록·폼·시트는 불투명 `AppCard`, 글래스는 떠 있는 층(탭바)에만**(결정 기록 004 최종 검토 D). 새 화면 파일은 `test/design/glass_boundary_test.dart`의 목록에 더한다.
- 사용자에게 보이는 문구는 `lib/l10n/app_strings.dart`의 상수만 쓴다. 오류 문구는 `messageFor`(`core/error/error_messages.dart`)가 코드로 고른다.
- 매장 범위 조회는 `autoDispose` + `runShopScoped`(`NOT_A_MEMBER` → 내 정보 재조회). 오류 화면에는 [다시 시도]와 뒤로 가기가 있고, 모든 하위 화면 머리에 `AppBackButton`을 둔다.
- 저장·쓰기 버튼은 요청 중 비활성(연타 방지).

검증 명령 (`app/`에서)
- **정적 분석**: `flutter analyze` → `No issues found!`
- **전체 테스트**: `flutter test` → 작업마다 적은 개수
- 파일 몇 개만: `flutter test <test 경로들>`
- 골든 만들기: `flutter test --update-goldens <골든 테스트 경로>` — 이 계획의 골든 테스트에만 쓴다. 기존 골든이 바뀌면 멈추고 보고한다.

## 이 계획에서 새로 정한 것

설계와 모순되는 것은 없다. 설계의 빈틈을 가장 작게 메운 것과, 참조 구현을 만들며 정한 것이다. Task 11 에서 결정 기록 005 에 옮긴다.

1. **고객 탭은 홈 셸의 큰 날짜 머리 대신 자기 머리를 쓴다** — "고객" + "N마리" + 보기 전환(목업 A안). 그래서 **설정(톱니) 버튼은 캘린더·매출 탭 머리에만 있다.** "N마리"는 목록 응답의 `pet_count`다.
2. **목록에 "무지개다리 포함" 칩을 더한다** — 설계 8.1 의 목록 조작(보기 전환·정렬·검색)에 없다. 반려동물이 모두 무지개다리인 가족은 기본 목록과 검색에서 빠지므로, 칩이 없으면 그 고객을 찾아 삭제(익명화)할 길이 없다. 서버의 `include_passed=true`를 켠다.
3. **가족 카드 머리의 번호는 가린 번호의 뒷자리를 `··5678`로 줄여 보인다**(목업). 목록에는 가린 번호만 온다.
4. **생일은 날짜 선택기 대신 `YYYY.MM.DD` 글자 입력이다** — 앱에 `flutter_localizations`가 없어 Material 날짜 선택기가 영어로 뜬다. 새 의존성을 넣지 않는다. `2021-03-04`·`20210304`도 받는다. 오늘보다 늦거나 40년보다 이른 날은 막는다(서버 규칙).
5. **등록 1단계의 번호 조회는 번호가 형식에 맞게 완성되는 순간 보낸다**(목업 "번호를 치는 순간"). 형식이 안 맞으면 보내지 않는다 — 서버는 형식이 틀린 번호에 422 를 준다(결정 기록 005).
6. **반려동물 상세의 "보호자" 탭은 고객 상세(`GET /customers/{id}`)를 따로 불러** 전체 번호·보조 연락처·수신 동의(값과 날짜)·메모를 보인다 — 반려동물 상세 응답의 보호자 번호는 가려져 있고, 설계 8.2 는 전체 번호를 상세에서 보인다고 했다. [보호자 수정]·[반려동물 추가] 버튼도 이 탭에 있다.
7. **고객 삭제 버튼은 보호자 수정 화면 맨 아래에 사장에게만 보인다.** 확인 시트를 거쳐 익명화하고 홈(고객 탭)으로 간다.
8. **반려동물 상세의 머리는 [수정]과 더 보기(⋯).** 더 보기 시트에 무지개다리 표시/되돌리기와 반려동물 삭제가 있다. 무지개다리 표시와 삭제는 확인 시트를 거치고, 되돌리기(잘못 누른 것을 되돌리는 동작)는 바로 보낸다.
9. **형제로 옮길 때, 등록·추가가 끝나 새 아이로 갈 때는 화면을 바꿔 끼운다**(`pushReplacement`) — 뒤로 가면 목록이다. 수정이 끝나면 뒤로(`pop`) 간다.
10. **쓰기가 끝나면 목록·반려동물 상세·고객 상세를 모두 다시 부르게 한다**(보고 있는 것만 실제로 부른다). 지운 대상의 상세는 다시 부르지 않는다 — 부르면 404 가 화면에 잠깐 보인다.
11. **다음 페이지는 목록 끝에서 400px 안으로 내려오면 부른다.** 실패하면 스크롤로는 다시 부르지 않고 목록 끝의 [다시 시도]로만 — 오류 중에 스크롤마다 요청이 나가지 않게.
12. **목록 보기 방식은 기기 설정(보안 저장소 `customer_view_mode`)이다.** 로그아웃·탈퇴의 정리(`PrefsStore.clear()`)로 지우지 않는다.
13. **등록 3단계는 한 화면의 `IndexedStack`에서 오간다** — 앞 단계로 돌아가도 적은 값이 남는다. 머리의 뒤로 가기와 시스템 뒤로 가기 모두 앞 단계로 간다.
14. **품종 추천**(설계 6.1 "앱이 자주 쓰는 품종을 추천") — 강아지 8개(말티즈·푸들·포메라니안·비숑·시츄·요크셔테리어·치와와·믹스), 고양이 6개(코리안 숏헤어·러시안 블루·페르시안·브리티시 숏헤어·스코티시 폴드·믹스). 누르면 품종 칸을 채운다.
15. **`Pressable`에 `selected` 인자를 더한다** — 선택 칩·아이콘 토글이 스크린리더에 "선택됨"으로 읽힌다.
16. **입력 길이는 서버 한도를 입력 제한으로 막는다** — 이름·품종 50, 기타 질병 이름 30, 질병 메모 100, 메모 500, 전화 칸 20.

## 이 계획의 코드는 어떻게 검증했나

②-1 과 같은 방식이다. **이 계획서의 코드는 저장소 안의 임시 작업 트리에서 실제로 만들어 돌린 것을 그대로 옮겼다.**

- 작업 트리 두 개(git 무시 대상): `.superpowers/ref/wt-customer-2b`(브랜치 `ref/customer-2b` — 처음 구현한 것, 버리는 브랜치), `.superpowers/ref/wt-customer-2b-plan`(브랜치 `ref/customer-2b-plan` — **이 계획서의 작업 순서대로 다시 쌓은 것**). 두 브랜치의 최종 코드는 `app_strings.dart`·`screen_keys.dart`·`app_router.dart`·`glass_boundary_test.dart`의 줄 순서만 다르고, 골든 6장은 바이트까지 같다. 계획서의 코드 블록과 diff 는 `ref/customer-2b-plan`의 작업별 커밋에서 기계적으로 뽑았다.
- 작업마다 `flutter analyze`와 `flutter test`를 돌리고 커밋했다.

  | 작업 | 그 작업의 테스트 파일 | `flutter test` 전체 | `flutter analyze` |
  |---|---|---|---|
  | 기준(`main` `81283dc`) | — | 240 | 0건 |
  | 1 | 5 | 245 | 0건 |
  | 2 | 16 | 255 | 0건 |
  | 3 | 9 | 264 | 0건 |
  | 4 | 6 | 270 | 0건 |
  | 5 | 16 | 284 | 0건 |
  | 6 | 12 | 295 | 0건 |
  | 7 | 30 | 306 | 0건 |
  | 8 | 9 | 314 | 0건 |
  | 9 | 7 | 320 | 0건 |
  | 10 | 8 | 327 | 0건 |
- **변이로 판별력을 확인했다.** 각 작업의 "판별력 확인" 단계가 그 변이들이다 — 방어 코드를 하나씩 빼면 적힌 테스트가 실패한다. 하나만 예외다: 반려동물 폼·등록 화면의 `_busy` 가드는 저장 버튼 비활성과 겹쳐, 빼도 테스트가 통과한다(Task 8 에 적었다).
- 참조 구현이 계획을 바꾼 것: 선택 칩이 `Wrap` 안에서 가로 폭을 다 채우는 결함(등록 3단계 골든에서 발견 → `Align(widthFactor: 1)`), Riverpod 3.4 의 `invalidate` 뒤에도 노티파이어가 살아 있어 `ref.mounted`만으로는 옛 페이지를 못 거르는 것(→ `_generation`), 다음 페이지 오류 뒤 스크롤마다 재요청이 나가는 것(→ 스크롤 재요청 막기), 번호 조회 입력 칸의 커서 이동이 같은 번호로 조회를 또 보내는 것(→ `_lastDigits`).
- **검증하지 않은 것 — Task 11 에서 실행자가 사용자와 확인한다:** 실제 백엔드·게이트웨이에 붙은 앱(참조 구현은 가짜 HTTP 어댑터로만 돌렸다), iOS 한글 입력기가 조합 구간(`composing`)을 알리는 방식(조합이 끝나지 않은 것으로 보이면 검색이 나가지 않는다 — 설계 8.2 의 입력 지연이 실기기에서 성립하는지), 시뮬레이터에서의 화면 모양과 키보드.

그래도 규칙은 같다. **검토자는 이 계획서의 코드를 검토되지 않은 것으로 본다.** 작업 트리는 "컴파일되고 자기 테스트를 통과한다"까지만 보장한다. 테스트가 옳은 것을 확인하는지, 빠진 시나리오가 없는지는 아래 위협 점검표와 설계를 기준으로 판단한다.

수정하는 기존 파일은 `diff` 블록으로 보인다 — `-` 줄을 지우고 `+` 줄을 더한다. 줄 번호(`@@`)는 앞 작업이 끝난 상태 기준이다.

## 위협 점검표

설계 9절의 C1~C12 가운데 앱 몫과, 참조 구현을 만들며 찾은 A1~A7 이다. **구현자와 검토자는 이 표를 코드와 대조한다. 표에 없는 시나리오를 찾으면 보고한다.**

| # | 시나리오 | 막는 것 | 확인하는 테스트 |
|---|---|---|---|
| C2 | 두 기기가 같은 번호로 동시에 등록한다 — 늦은 쪽 | 서버 409 `CUSTOMER_PHONE_TAKEN` → 등록 3단계에 문구, 화면에 남는다 | Task 10 `그사이 같은 번호가 등록됐으면(CUSTOMER_PHONE_TAKEN) 문구를 보이고 남는다(C2)` |
| C4 | 직원이 고객을 삭제한다 | 보안 경계는 서버 403. 앱은 직원에게 버튼을 보이지 않고, 403 이 와도 문구로 보인다 | Task 9 `직원에게는 고객 삭제가 보이지 않는다`·`서버가 삭제를 거절하면(PERMISSION_DENIED) 문구를 보이고 남는다` |
| C5 | 내보내진 직원이 목록·상세를 계속 본다 | 모든 조회·쓰기가 `runShopScoped` → `NOT_A_MEMBER`면 내 정보 재조회(라우터가 내보낸다) | Task 4 `NOT_A_MEMBER 면 내 정보를 다시 불러온다(C5)`, Task 5 `쓰기가 NOT_A_MEMBER 면…`, Task 6 `NOT_A_MEMBER 면…` |
| C7 | 목록·로그에 전체 번호가 노출된다 | 목록 모델(`FamilyCard`)에는 가린 번호 칸만 있고, 전체 번호는 `Customer`(고객 상세)에만. 모델에 `toString` 없음, `print` 금지(분석 오류) | Task 7 `가족 카드를 목록으로 보인다 — 보호자와 가린 뒷자리…`, Task 6 보호자 탭(전체 번호는 고객 상세에서) |
| C8 | 질병과 "질병 없음"을 함께 보내거나 둘 다 비운다 | 폼이 서로 풀고, 둘 다 없으면 요청 없이 알린다. 서버 422 문구도 매핑 | Task 8 `질병 없음과 질병은 함께 설 수 없다`·`빈 폼으로 저장하면…`·`서버가 거절하면 그 문구를 보이고 폼에 남는다`, Task 2 오류 문구 테스트 |
| C12 | 늦게 온 옛 검색 결과가 새 결과를 덮는다 | 조회 조건마다 컨트롤러가 따로 생긴다(family 키 = 조건). 화면은 새 조건만 본다 | Task 7 `검색은 0.3초 쉰 뒤 보내고, 새 검색을 보내면 늦게 온 옛 결과는 버린다(C12)` |
| A1 | 다음 페이지를 기다리는 사이 쓰기가 목록을 다시 불러오면, 늦게 온 페이지가 새 목록에 옛 페이지를 붙인다 | `build()`마다 느는 `_generation`을 비교해 버린다 | Task 4 `다음 페이지를 기다리는 사이 다시 불러오면 옛 목록에 이어 붙이지 않는다` |
| A2 | 번호를 바꾸는 사이 늦게 온 옛 번호의 조회 결과가 "이미 등록된 번호예요"를 띄운다 | 조회 순번(`_lookupSeq`) | Task 10 `번호를 바꾸면 늦게 온 옛 번호의 조회 결과를 버린다` |
| A3 | 저장·무지개다리·삭제를 연타해 같은 요청이 두 번 나간다 | 요청 중 버튼 비활성, 상세는 [수정]·⋯도 막는다 | Task 6 `쓰기가 도는 동안 수정·더 보기를 막는다(연타 방지)`, Task 8 `저장 중에는 버튼을 막아 요청을 한 번만 보낸다` |
| A4 | 반려동물·고객을 지운 뒤 그 상세를 다시 불러 404 가 화면에 보인다 | `CustomerCommands`가 지운 대상의 상세 family 를 무효화하지 않는다 | Task 5 `반려동물을 지우면 그 아이의 상세는 다시 부르지 않는다`·`고객을 지우면 목록만 다시 부른다`, Task 6 `삭제는 확인을 거쳐 보내고…` |
| A5 | 마지막 반려동물을 지우려 한다 | 서버 409 `LAST_PET` → "고객 삭제를 이용해 주세요" 문구, 상세에 남는다 | Task 6 `마지막 반려동물이면(LAST_PET) 문구를 보이고 화면에 남는다` |
| A6 | 다음 페이지가 실패한 뒤 스크롤할 때마다 요청이 나간다 | 오류가 있으면 스크롤로는 부르지 않고 [다시 시도]로만 | Task 7 `끝까지 내리면 다음 페이지를 붙이고, 실패하면 그 자리에서 다시 시도한다` |
| A7 | 입력 도중(형식이 안 맞는) 번호로 조회해 422 를 받는다 | 번호가 형식에 맞게 완성될 때만 조회 | Task 10 `번호가 완성되기 전에는 조회하지 않는다`, Task 3 `서버와 같은 형식만 받는다` |

**이 계획으로도 남는 것 (Task 11 에서 결정 기록에 적는다):**
- iOS 한글 입력기가 조합 구간을 늦게 닫으면(마지막 글자를 조합 중으로 남기면) 검색이 나가지 않을 수 있다 — Task 11 에서 확인하고, 문제가 있으면 멈추고 사용자에게 묻는다(설계 8.2 를 바꾸는 일이다).
- 폼 화면의 `_busy` 가드는 저장 버튼 비활성과 겹쳐 테스트로 따로 판별되지 않는다.
- 무지개다리 아이의 이름으로 찾으면 그 가족 카드가 나오지만, 기본 목록에서는 그 아이가 카드에 보이지 않는다(결정 기록 005 의 "남는 것" 그대로 — 앱은 손대지 않는다).
- 오프라인·목록 캐시가 없다(설계 3.2).

## 시작 전 기준선

`feat/customer-2b-app`(이 계획서 커밋)의 상태다. 시작 전에 한 번 확인한다.

- `app/`에서 `flutter analyze` 0건, `flutter test` 240개 통과.
- 백엔드는 이 계획이 바꾸지 않는다. Task 11 전까지 띄울 필요가 없다.

## 파일 지도

```
app/lib/design/widgets/app_choice_chip.dart · app_icon_toggle.dart · pressable.dart(수정)        # Task 1
app/lib/core/error/error_messages.dart(수정)                                                       # Task 2
app/lib/core/storage/prefs_store.dart(수정)                                                        # Task 5
app/lib/core/router/app_router.dart · screen_keys.dart(수정)                                       # Task 6·8·9·10
app/lib/l10n/app_strings.dart(수정)                                                                # Task 3·6·7·8·9·10
app/lib/features/home/screens/home_shell.dart(수정)                                                # Task 7·10
app/lib/features/customer/
├── api/customer_models.dart · customer_api.dart                                                  # Task 2
├── state/customer_input.dart                                                                     # Task 3
├── state/customer_providers.dart · customer_list_controller.dart                                 # Task 4
├── state/customer_commands.dart · customer_view_mode.dart · search_debouncer.dart               # Task 5
├── screens/customer_labels.dart · pet_detail_screen.dart                                        # Task 6
├── screens/customer_list_tab.dart · family_card_view.dart                                       # Task 7
├── screens/pet_form.dart · pet_form_screen.dart                                                 # Task 8
├── screens/customer_form.dart · customer_edit_screen.dart                                       # Task 9
└── screens/register_customer_screen.dart                                                         # Task 10
app/test/support/customer_fixtures.dart(Task 2) · customer_test_app.dart(Task 4)
app/test/features/customer/{api,state,screens}/…_test.dart · screens/goldens/*.png
app/test/design/app_choice_chip_test.dart · app_icon_toggle_test.dart · goldens/*.png · glass_boundary_test.dart(수정)
app/test/core/error/error_messages_test.dart · storage/stores_test.dart · router/app_router_test.dart(수정)
app/test/features/home/screens/home_shell_test.dart(수정)
_docs/decisions/005-customer-pet.md(수정)                                                          # Task 11
```

---

### Task 1: 선택 칩과 아이콘 토글 위젯, Pressable 의 선택 상태

**Files:**
- Create: `app/lib/design/widgets/app_choice_chip.dart`
- Create: `app/lib/design/widgets/app_icon_toggle.dart`
- Modify: `app/lib/design/widgets/pressable.dart`
- Create: `app/test/design/app_choice_chip_test.dart`
- Create: `app/test/design/app_icon_toggle_test.dart`
- Create (골든, 명령으로 만든다): `app/test/design/goldens/app_choice_chip.png`
- Create (골든, 명령으로 만든다): `app/test/design/goldens/app_icon_toggle.png`

**Interfaces:**
- Consumes: `Pressable`(기존, `lib/design/widgets/pressable.dart`), 토큰 `AppColors`·`AppRadius`·`AppSpacing`·`AppTypography`
- Produces: `AppChoiceChip({required String label, required bool selected, required VoidCallback? onTap})` — 높이 44(`Pressable` 최소), 가로는 글자 폭만큼. `AppIconToggle({required List<IconData> icons, required List<String> labels, required int currentIndex, required ValueChanged<int> onChanged})` — 칸마다 탭 영역 44×44. `Pressable`에 `bool? selected` 인자(선택 여부를 의미 노드에 싣는다).

**알아 둘 것:**
- `AppChoiceChip`의 `Container`에 `alignment`를 주지 않는다 — 주면 `Wrap`·`Column` 안에서 가로 폭을 다 채운다(참조 구현의 등록 3단계 골든에서 칩이 한 줄씩 늘어난 것을 보고 고쳤다). `Align(widthFactor: 1)`로 가로는 글자 폭, 세로는 `Pressable`의 최소 44 안에서 가운데다.
- 칩 글자는 `ExcludeSemantics`로 감싼다 — 이름표는 `Pressable`이 읽는다(두 번 읽지 않게).

**막는 위협:** — (화면 부품)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/design/app_choice_chip_test.dart` (새 파일):

```dart
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

BoxDecoration _decorationOf(WidgetTester tester, String label) {
  return tester
      .widgetList<Container>(
        find.descendant(
          of: find.widgetWithText(AppChoiceChip, label),
          matching: find.byType(Container),
        ),
      )
      .map((c) => c.decoration)
      .whereType<BoxDecoration>()
      .single;
}

void main() {
  testWidgets('누르면 onTap 이 불리고, 고른 칩만 잉크로 칠하고 선택됨으로 읽힌다', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Row(
            children: [
              AppChoiceChip(label: '강아지', selected: true, onTap: () {}),
              AppChoiceChip(label: '고양이', selected: false, onTap: () => taps++),
            ],
          ),
        ),
      ),
    );

    await tester.tap(find.text('고양이'));
    await tester.pumpAndSettle();

    expect(taps, 1);
    expect(_decorationOf(tester, '강아지').color, AppColors.ink);
    expect(_decorationOf(tester, '고양이').color, AppColors.white);
    expect(
      tester.getSemantics(find.bySemanticsLabel('강아지')),
      matchesSemantics(
        label: '강아지',
        isButton: true,
        hasTapAction: true,
        hasSelectedState: true,
        isSelected: true,
      ),
    );
  });

  testWidgets('Wrap 안에서도 글자 폭만큼만 차지하고, 높이는 누르기 좋은 44다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 390,
            child: Wrap(
              children: [
                AppChoiceChip(label: '강아지', selected: false, onTap: () {}),
              ],
            ),
          ),
        ),
      ),
    );

    final size = tester.getSize(find.byType(AppChoiceChip));
    expect(size.width, lessThan(120));
    expect(size.height, 44);
  });

  testWidgets('AppChoiceChip 골든 — 고른 칩과 안 고른 칩', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppChoiceChip(label: '강아지', selected: true, onTap: () {}),
          const SizedBox(width: 8),
          AppChoiceChip(label: '고양이', selected: false, onTap: () {}),
        ],
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_choice_chip.png'));
  });
}
```

`app/test/design/app_icon_toggle_test.dart` (새 파일):

```dart
import 'package:chagocnote/design/widgets/app_icon_toggle.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('아이콘을 누르면 그 인덱스로 onChanged 가 불리고, 탭 영역은 44×44 다', (tester) async {
    int? changed;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: AppIconToggle(
              icons: const [Icons.view_list, Icons.grid_view],
              labels: const ['목록', '격자'],
              currentIndex: 0,
              onChanged: (i) => changed = i,
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.bySemanticsLabel('격자'));
    await tester.pumpAndSettle();

    expect(changed, 1);
    expect(tester.getSize(find.bySemanticsLabel('격자')), const Size(44, 44));
    expect(
      tester.getSemantics(find.bySemanticsLabel('목록')),
      matchesSemantics(
        label: '목록',
        isButton: true,
        hasTapAction: true,
        hasSelectedState: true,
        isSelected: true,
      ),
    );
  });

  testWidgets('AppIconToggle 골든 — 목록 선택', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      AppIconToggle(
        icons: const [Icons.view_list, Icons.grid_view],
        labels: const ['목록', '격자'],
        currentIndex: 0,
        onChanged: (_) {},
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_icon_toggle.png'));
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/design/app_choice_chip_test.dart test/design/app_icon_toggle_test.dart`

Expected: 컴파일 오류 — `app_choice_chip.dart`·`app_icon_toggle.dart`가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/design/widgets/app_choice_chip.dart` (새 파일):

```dart
import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 고를 수 있는 알약 칩("강아지 / 고양이", 질병 칩 등).
///
/// 고른 칩은 잉크 채움 + 흰 글자, 안 고른 칩은 흰 면 + 구분선 테두리다.
/// 여러 개를 묶을 때는 화면이 `Wrap`으로 늘어놓는다 — 하나만 고를지 여럿을
/// 고를지는 화면이 정한다.
class AppChoiceChip extends StatelessWidget {
  const AppChoiceChip({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      selected: selected,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        decoration: BoxDecoration(
          color: selected ? AppColors.ink : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(
            color: selected ? AppColors.ink : AppColors.line,
            width: 1,
          ),
        ),
        // 높이(Pressable 의 최소 44)는 채우되 가로는 글자 폭만큼만 — `alignment`를
        // 주면 Wrap·Column 안에서 가로 폭을 다 채워 버린다.
        child: Align(
          widthFactor: 1,
          // 이름표는 Pressable 이 읽는다 — 글자를 한 번 더 읽지 않게 뺀다.
          child: ExcludeSemantics(
            child: Text(
              label,
              style: AppTypography.body.copyWith(
                color: selected ? AppColors.white : AppColors.ink,
                fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
```

`app/lib/design/widgets/app_icon_toggle.dart` (새 파일):

```dart
import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import 'pressable.dart';

/// 아이콘 두세 개 중 하나를 고르는 토글(목록 ☰ / 격자 ▦).
///
/// 고른 쪽은 잉크 바탕 + 흰 아이콘, 나머지는 보조 색 아이콘이다.
/// [labels]는 스크린리더가 읽는 이름으로 [icons]와 같은 순서다.
class AppIconToggle extends StatelessWidget {
  const AppIconToggle({
    super.key,
    required this.icons,
    required this.labels,
    required this.currentIndex,
    required this.onChanged,
  }) : assert(icons.length == labels.length);

  final List<IconData> icons;
  final List<String> labels;
  final int currentIndex;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.line, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < icons.length; i++)
            Pressable(
              onTap: () => onChanged(i),
              semanticLabel: labels[i],
              selected: i == currentIndex,
              // 탭 영역은 44×44, 칠하는 면은 그 안의 36×30 이다.
              child: SizedBox(
                width: 44,
                height: 44,
                child: Center(
                  child: Container(
                    width: 36,
                    height: 30,
                    decoration: BoxDecoration(
                      color: i == currentIndex
                          ? AppColors.ink
                          : const Color(0x00000000),
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    alignment: Alignment.center,
                    child: Icon(
                      icons[i],
                      size: 18,
                      color: i == currentIndex
                          ? AppColors.white
                          : AppColors.secondary,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
```

`app/lib/design/widgets/pressable.dart` (수정):

```diff
@@ -11,6 +11,7 @@ import '../tokens/app_springs.dart';
 ///   스프링 스케일 대신 옅은 페이드로 대체한다.
 /// - `semanticLabel`을 주면 버튼으로 접근성에 노출한다. 의미 노드는 자기
 ///   크기(최소 44×44)로 따로 잡힌다 — 행 안에 두어도 행 전체로 번지지 않는다.
+/// - `selected`를 주면 고를 수 있는 항목(칩·토글)으로 읽히고 선택 여부를 알린다.
 /// - 시각적 크기가 44×44보다 작아도 탭 영역은 `minSize`(기본 44) 이상을
 ///   보장한다.
 class Pressable extends StatefulWidget {
@@ -19,12 +20,14 @@ class Pressable extends StatefulWidget {
     required this.child,
     this.onTap,
     this.semanticLabel,
+    this.selected,
     this.minSize = 44,
   });
 
   final Widget child;
   final VoidCallback? onTap;
   final String? semanticLabel;
+  final bool? selected;
   final double minSize;
 
   @override
@@ -90,6 +93,7 @@ class _PressableState extends State<Pressable>
     return Semantics(
       container: true,
       button: widget.onTap != null,
+      selected: widget.selected,
       label: widget.semanticLabel,
       child: GestureDetector(
         behavior: HitTestBehavior.opaque,
```

- [ ] **Step 4: 골든을 만들고 눈으로 확인한다**

Run: `flutter test --update-goldens test/design/app_choice_chip_test.dart test/design/app_icon_toggle_test.dart`

만들어지는 파일: `app/test/design/goldens/app_choice_chip.png`, `app/test/design/goldens/app_icon_toggle.png`

Read 도구로 이미지를 열어 확인한다: `app_choice_chip.png`는 검은 알약 '강아지'와 흰 알약 '고양이'가 나란하다. `app_icon_toggle.png`는 흰 테두리 상자 안 왼쪽 목록 아이콘만 검은 바탕이다.

- [ ] **Step 5: 통과를 확인한다**

Run: `flutter test test/design/app_choice_chip_test.dart test/design/app_icon_toggle_test.dart` → Expected: `+5: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+245: All tests passed!`

- [ ] **Step 6: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `app_choice_chip.dart`의 `widthFactor: 1,`을 지운다 → `Wrap 안에서도 글자 폭만큼만 차지하고, 높이는 누르기 좋은 44다` 실패
- `pressable.dart`의 `selected: widget.selected,`를 지운다 → 두 파일의 선택 상태 의미 테스트 실패

- [ ] **Step 7: 커밋한다**

```bash
git add app/lib/design/widgets/app_choice_chip.dart app/lib/design/widgets/app_icon_toggle.dart app/lib/design/widgets/pressable.dart app/test/design/app_choice_chip_test.dart app/test/design/app_icon_toggle_test.dart app/test/design/goldens/app_choice_chip.png app/test/design/goldens/app_icon_toggle.png
git commit -m "feat(app): 선택 칩과 아이콘 토글 위젯, Pressable 의 선택 상태

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 고객·반려동물 API 와 모델, 오류 문구

**Files:**
- Modify: `app/lib/core/error/error_messages.dart`
- Create: `app/lib/features/customer/api/customer_api.dart`
- Create: `app/lib/features/customer/api/customer_models.dart`
- Modify: `app/test/core/error/error_messages_test.dart`
- Create: `app/test/features/customer/api/customer_api_test.dart`
- Create: `app/test/support/customer_fixtures.dart`

**Interfaces:**
- Consumes: `ApiClient`(`lib/core/proxy/api_client.dart` — `get(path, {queryParameters})`·`post`·`put`·`delete`, `ApiException`을 던진다)
- Produces: `lib/features/customer/api/customer_models.dart`: `PetSummary`·`FamilyCard`·`CustomerPage{items, nextCursor, petCount}`·`CustomerLookup{customerId, name, petNames}`·`PetCondition{typeCode, label, customLabel, note, displayLabel}`·`Pet{…, weightKg: double, passedAway}`·`Customer{…, phone(숫자만)}`·`CustomerDetail{customer, pets}`·`OwnerSummary`·`Sibling`·`PetDetail{pet, owner, siblings}`·`ConditionType{code, label, sortOrder; otherCode = 'other'}`·요청 모델 `CustomerFields{name, phone, phoneAlt, marketingConsent, memo}.toJson()`·`ConditionEntry{typeCode, customLabel, note}`·`PetFields{…, birthDate: DateTime?, birthYear: int?, weightKg: double, noKnownConditions, conditions, memo}.toJson()`. `lib/features/customer/api/customer_api.dart`: `CustomerApi(ApiClient)`의 `list(shopId, {q, sort = 'recent', includePassed = false, cursor}) → CustomerPage`, `lookup(shopId, phoneDigits) → CustomerLookup?`(404 `CUSTOMER_NOT_FOUND`면 null), `register(shopId, {customer, pet}) → CustomerDetail`, `customer`, `updateCustomer`, `deleteCustomer`, `addPet → PetDetail`, `pet`, `updatePet`, `markPassedAway`, `unmarkPassedAway`, `deletePet`, `conditionTypes → List<ConditionType>`. 테스트 준비물 `test/support/customer_fixtures.dart`(`petSummaryJson`·`familyJson`·`pageJson`·`conditionJson`·`petJson`·`customerJson`·`customerDetailJson`·`petDetailJson`·`siblingJson`·`conditionTypesJson`).

**알아 둘 것:**
- 요청·응답 모양은 결정 기록 005 "계획에서 새로 정한 것"과 백엔드 스키마(`backend/apps/customer/adapter/inbound/api/schemas/`) 그대로다. 필드 이름을 바꾸지 않는다(앱 CLAUDE.md).
- 모델에 `toString`을 두지 않는다 — 전화번호·이름이 로그에 찍히지 않게(C7).
- `list`의 빈 검색어와 null 커서는 쿼리에 싣지 않는다. `include_passed`는 bool 그대로 넘기고 dio 가 `false`/`true`로 보낸다.

**막는 위협:** C7(목록 모델에는 가린 번호 칸만 있다 — 전체 번호 `phone`은 `Customer`에만)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/core/error/error_messages_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -45,4 +45,15 @@ void main() {
       expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
     }
   });
+
+  test('고객·반려동물 코드(설계 5절)는 모두 앱의 문구가 있다', () {
+    const codes = [
+      'CUSTOMER_NOT_FOUND', 'PET_NOT_FOUND', 'CUSTOMER_PHONE_TAKEN', 'LAST_PET',
+      'PET_HEALTH_REQUIRED', 'PET_HEALTH_CONFLICT',
+    ];
+    for (final code in codes) {
+      expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
+    }
+    expect(messageFor(_error('LAST_PET', status: 409)), contains('고객 삭제'));
+  });
 }
```

`app/test/features/customer/api/customer_api_test.dart` (새 파일):

```dart
// CustomerApi 를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로,
// 쿼리, 본문 모양, 응답 해석.
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/customer/api/customer_api.dart';
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/fake_http_client_adapter.dart';

({CustomerApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: CustomerApi(client), adapter: adapter);
}

Map<String, dynamic> _json(List<int>? body) =>
    jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

const _petFields = PetFields(
  name: '콩이',
  species: 'dog',
  breed: '말티즈',
  sex: 'female',
  neutered: true,
  birthDate: null,
  birthYear: 2021,
  weightKg: 3.2,
  noKnownConditions: false,
  conditions: [
    ConditionEntry(typeCode: 'patella_luxation', note: '2기'),
    ConditionEntry(typeCode: 'other', customLabel: '눈물 자국'),
  ],
  memo: null,
);

const _customerFields = CustomerFields(
  name: '김민지',
  phone: '01012345678',
  phoneAlt: null,
  marketingConsent: false,
  memo: '오후 방문 선호',
);

void main() {
  group('list', () {
    test(
      '기본 쿼리는 sort=recent·include_passed=false 이고 빈 검색어와 커서는 보내지 않는다',
      () async {
        final s = _build((options, body) {
          return FakeResponse(
            statusCode: 200,
            data: pageJson(nextCursor: 'c1'),
          );
        });

        final page = await s.api.list(3, q: '');

        final request = s.adapter.requests.single;
        expect(request.method, 'GET');
        expect(request.path, '/v1/shops/3/customers');
        expect(request.queryParameters, {
          'sort': 'recent',
          'include_passed': false,
        });
        expect(page.nextCursor, 'c1');
        expect(page.petCount, 1);
        final card = page.items.single;
        expect(card.name, '김민지');
        expect(card.phoneMasked, '010-12··-5678');
        expect(card.pets.single.name, '콩이');
        expect(card.pets.single.ageLabel, '5살');
      },
    );

    test('검색어·정렬·무지개다리 포함·커서를 쿼리로 보낸다', () async {
      final s = _build((options, body) {
        return FakeResponse(statusCode: 200, data: pageJson(items: []));
      });

      await s.api.list(
        3,
        q: '5678 콩',
        sort: 'name',
        includePassed: true,
        cursor: 'c1',
      );

      expect(s.adapter.requests.single.queryParameters, {
        'q': '5678 콩',
        'sort': 'name',
        'include_passed': true,
        'cursor': 'c1',
      });
    });
  });

  group('lookup', () {
    test('있으면 보호자 이름과 반려동물 이름을 돌려준다', () async {
      final s = _build((options, body) {
        expect(options.path, '/v1/shops/3/customers/lookup');
        expect(options.queryParameters, {'phone': '01012345678'});
        return const FakeResponse(
          statusCode: 200,
          data: {
            'customer_id': 7,
            'name': '김민지',
            'pet_names': ['콩이', '두부'],
          },
        );
      });

      final found = await s.api.lookup(3, '01012345678');

      expect(found!.customerId, 7);
      expect(found.petNames, ['콩이', '두부']);
    });

    test('404 CUSTOMER_NOT_FOUND 면 null 이다', () async {
      final s = _build((options, body) {
        return const FakeResponse(
          statusCode: 404,
          data: {'code': 'CUSTOMER_NOT_FOUND', 'message': '없음'},
        );
      });

      expect(await s.api.lookup(3, '01012345678'), isNull);
    });

    test('다른 오류는 그대로 던진다', () async {
      final s = _build((options, body) {
        return const FakeResponse(
          statusCode: 422,
          data: {'code': 'VALIDATION_ERROR', 'message': '형식'},
        );
      });

      await expectLater(
        s.api.lookup(3, '0101'),
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'VALIDATION_ERROR'),
        ),
      );
    });
  });

  test('register 는 {customer, pet} 본문을 보내고 고객 상세를 돌려준다', () async {
    final s = _build((options, body) {
      expect(options.method, 'POST');
      expect(options.path, '/v1/shops/3/customers');
      return FakeResponse(statusCode: 201, data: customerDetailJson());
    });

    final detail = await s.api.register(
      3,
      customer: _customerFields,
      pet: _petFields,
    );

    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/customers']), {
      'customer': {
        'name': '김민지',
        'phone': '01012345678',
        'phone_alt': null,
        'marketing_consent': false,
        'memo': '오후 방문 선호',
      },
      'pet': {
        'name': '콩이',
        'species': 'dog',
        'breed': '말티즈',
        'sex': 'female',
        'neutered': true,
        'birth_date': null,
        'birth_year': 2021,
        'weight_kg': 3.2,
        'no_known_conditions': false,
        'conditions': [
          {'type_code': 'patella_luxation', 'custom_label': null, 'note': '2기'},
          {'type_code': 'other', 'custom_label': '눈물 자국', 'note': null},
        ],
        'memo': null,
      },
    });
    expect(detail.customer.phone, '01012345678');
    expect(
      detail.customer.marketingConsentChangedAt,
      DateTime.utc(2026, 9, 20, 1),
    );
    expect(detail.pets.single.conditions.single.displayLabel, '슬개골 탈구');
  });

  test('생일은 YYYY-MM-DD 로 보낸다', () async {
    final s = _build((options, body) {
      return FakeResponse(statusCode: 200, data: petDetailJson());
    });

    await s.api.updatePet(
      3,
      11,
      PetFields(
        name: '콩이',
        species: 'cat',
        breed: '코숏',
        sex: 'male',
        neutered: false,
        birthDate: DateTime(2021, 3, 4),
        birthYear: null,
        weightKg: 4,
        noKnownConditions: true,
        conditions: const [],
        memo: null,
      ),
    );

    final sent = _json(s.adapter.lastBodyByPath['/v1/shops/3/pets/11']);
    expect(s.adapter.requests.single.method, 'PUT');
    expect(sent['birth_date'], '2021-03-04');
    expect(sent['birth_year'], isNull);
    expect(sent['no_known_conditions'], isTrue);
    expect(sent['conditions'], isEmpty);
  });

  test('반려동물 상세를 해석한다 — 몸무게 정수, 기타 질병 이름, 무지개다리, 보호자 가린 번호', () async {
    final s = _build((options, body) {
      expect(options.path, '/v1/shops/3/pets/11');
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(
          pet: petJson(
            weightKg: 4,
            birthDate: null,
            birthYear: 2020,
            conditions: [
              conditionJson(
                typeCode: 'other',
                label: '기타',
                customLabel: '눈물 자국',
                note: null,
              ),
            ],
            passedAwayAt: '2026-09-21T03:00:00Z',
          ),
          siblings: [siblingJson()],
        ),
      );
    });

    final detail = await s.api.pet(3, 11);

    expect(detail.pet.weightKg, 4.0);
    expect(detail.pet.birthDate, isNull);
    expect(detail.pet.birthYear, 2020);
    expect(detail.pet.conditions.single.displayLabel, '눈물 자국');
    expect(detail.pet.passedAway, isTrue);
    expect(detail.owner.phoneMasked, '010-12··-5678');
    expect(detail.siblings.single.name, '두부');
  });

  test('나머지 경로와 메서드', () async {
    final s = _build((options, body) {
      final key = '${options.method} ${options.path}';
      switch (key) {
        case 'GET /v1/shops/3/customers/7':
        case 'PUT /v1/shops/3/customers/7':
          return FakeResponse(statusCode: 200, data: customerDetailJson());
        case 'POST /v1/shops/3/customers/7/pets':
        case 'POST /v1/shops/3/pets/11/passed-away':
        case 'DELETE /v1/shops/3/pets/11/passed-away':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'DELETE /v1/shops/3/customers/7':
        case 'DELETE /v1/shops/3/pets/11':
          return const FakeResponse(statusCode: 204);
        case 'GET /v1/shops/3/pet-condition-types':
          return const FakeResponse(statusCode: 200, data: conditionTypesJson);
      }
      fail('예상하지 못한 요청: $key');
    });

    await s.api.customer(3, 7);
    await s.api.updateCustomer(3, 7, _customerFields);
    await s.api.addPet(3, 7, _petFields);
    await s.api.markPassedAway(3, 11);
    await s.api.unmarkPassedAway(3, 11);
    await s.api.deleteCustomer(3, 7);
    await s.api.deletePet(3, 11);
    final types = await s.api.conditionTypes(3);

    expect(types.map((t) => t.code), [
      'patella_luxation',
      'heart_disease',
      'skin_disease',
      'other',
    ]);
    expect(s.adapter.requests.map((r) => '${r.method} ${r.path}'), [
      'GET /v1/shops/3/customers/7',
      'PUT /v1/shops/3/customers/7',
      'POST /v1/shops/3/customers/7/pets',
      'POST /v1/shops/3/pets/11/passed-away',
      'DELETE /v1/shops/3/pets/11/passed-away',
      'DELETE /v1/shops/3/customers/7',
      'DELETE /v1/shops/3/pets/11',
      'GET /v1/shops/3/pet-condition-types',
    ]);
  });
}
```

`app/test/support/customer_fixtures.dart` (새 파일):

```dart
/// 고객·반려동물 API 응답의 JSON 모양(백엔드 `customer` 스포크의 스키마 그대로).
///
/// 테스트가 필요한 칸만 바꿔 쓴다. 번호·이름은 가짜 값이다.
library;

Map<String, dynamic> petSummaryJson({
  int petId = 11,
  String name = '콩이',
  String species = 'dog',
  String breed = '말티즈',
  String ageLabel = '5살',
  bool hasConditions = false,
  bool passedAway = false,
}) => {
  'pet_id': petId,
  'name': name,
  'species': species,
  'breed': breed,
  'age_label': ageLabel,
  'has_conditions': hasConditions,
  'passed_away': passedAway,
};

Map<String, dynamic> familyJson({
  int customerId = 7,
  String name = '김민지',
  String phoneMasked = '010-12··-5678',
  List<Map<String, dynamic>>? pets,
}) => {
  'customer_id': customerId,
  'name': name,
  'phone_masked': phoneMasked,
  'pets': pets ?? [petSummaryJson()],
};

Map<String, dynamic> pageJson({
  List<Map<String, dynamic>>? items,
  String? nextCursor,
  int? petCount,
}) {
  final list = items ?? [familyJson()];
  return {
    'items': list,
    'next_cursor': nextCursor,
    'pet_count':
        petCount ??
        list.fold<int>(0, (sum, f) => sum + (f['pets'] as List).length),
  };
}

Map<String, dynamic> conditionJson({
  String typeCode = 'patella_luxation',
  String label = '슬개골 탈구',
  String? customLabel,
  String? note = '2기',
}) => {
  'type_code': typeCode,
  'label': label,
  'custom_label': customLabel,
  'note': note,
};

Map<String, dynamic> petJson({
  int petId = 11,
  int customerId = 7,
  String name = '콩이',
  String species = 'dog',
  String breed = '말티즈',
  String sex = 'female',
  bool neutered = true,
  String? birthDate = '2021-03-04',
  int? birthYear,
  String ageLabel = '5살',
  num weightKg = 3.2,
  bool noKnownConditions = false,
  List<Map<String, dynamic>>? conditions,
  String? memo = '귀 만지면 싫어함',
  String? passedAwayAt,
}) {
  final list = conditions ?? (noKnownConditions ? const [] : [conditionJson()]);
  return {
    'pet_id': petId,
    'customer_id': customerId,
    'name': name,
    'species': species,
    'breed': breed,
    'sex': sex,
    'neutered': neutered,
    'birth_date': birthDate,
    'birth_year': birthYear,
    'age_label': ageLabel,
    'weight_kg': weightKg,
    'no_known_conditions': noKnownConditions,
    'has_conditions': list.isNotEmpty,
    'conditions': list,
    'memo': memo,
    'passed_away_at': passedAwayAt,
  };
}

Map<String, dynamic> customerJson({
  int customerId = 7,
  String name = '김민지',
  String phone = '01012345678',
  String? phoneAlt,
  bool marketingConsent = true,
  String marketingConsentChangedAt = '2026-09-20T01:00:00Z',
  String? memo = '오후 방문 선호',
}) => {
  'customer_id': customerId,
  'name': name,
  'phone': phone,
  'phone_alt': phoneAlt,
  'marketing_consent': marketingConsent,
  'marketing_consent_changed_at': marketingConsentChangedAt,
  'memo': memo,
};

Map<String, dynamic> customerDetailJson({
  Map<String, dynamic>? customer,
  List<Map<String, dynamic>>? pets,
}) => {
  'customer': customer ?? customerJson(),
  'pets': pets ?? [petJson()],
};

Map<String, dynamic> petDetailJson({
  Map<String, dynamic>? pet,
  int customerId = 7,
  String ownerName = '김민지',
  String phoneMasked = '010-12··-5678',
  List<Map<String, dynamic>> siblings = const [],
}) => {
  'pet': pet ?? petJson(customerId: customerId),
  'owner': {
    'customer_id': customerId,
    'name': ownerName,
    'phone_masked': phoneMasked,
  },
  'siblings': siblings,
};

Map<String, dynamic> siblingJson({
  int petId = 12,
  String name = '두부',
  String species = 'dog',
  bool passedAway = false,
}) => {
  'pet_id': petId,
  'name': name,
  'species': species,
  'passed_away': passedAway,
};

const conditionTypesJson = [
  {'code': 'patella_luxation', 'label': '슬개골 탈구', 'sort_order': 1},
  {'code': 'heart_disease', 'label': '심장 질환', 'sort_order': 2},
  {'code': 'skin_disease', 'label': '피부병', 'sort_order': 3},
  {'code': 'other', 'label': '기타', 'sort_order': 10},
];
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/core/error/error_messages_test.dart test/features/customer/api/customer_api_test.dart test/support/customer_fixtures.dart`

Expected: 컴파일 오류 — `customer_api.dart`·`customer_models.dart`가 없다. `error_messages_test.dart`의 새 테스트는 컴파일되지만 서버 문구가 그대로 나와 실패한다.

- [ ] **Step 3: 구현한다**

`app/lib/core/error/error_messages.dart` (수정):

```diff
@@ -28,6 +28,12 @@ const Map<String, String> _messages = {
   'SHOP_CLOSE_CONFIRM_REQUIRED': '탈퇴하면 혼자 운영하는 매장도 함께 닫힙니다.',
   'VALIDATION_ERROR': '입력한 내용을 확인해 주세요.',
   'TOO_MANY_ATTEMPTS': '시도가 너무 잦습니다. 잠시 뒤에 다시 해 주세요.',
+  'CUSTOMER_NOT_FOUND': '고객을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다.',
+  'PET_NOT_FOUND': '반려동물을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다.',
+  'CUSTOMER_PHONE_TAKEN': '이미 등록된 전화번호입니다.',
+  'LAST_PET': '마지막 반려동물은 삭제할 수 없습니다. 고객 삭제를 이용해 주세요.',
+  'PET_HEALTH_REQUIRED': '질병을 고르거나 "질병 없음"을 눌러 주세요.',
+  'PET_HEALTH_CONFLICT': '질병과 "질병 없음"을 함께 고를 수 없습니다.',
 };
 
 const String _fallback = '문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.';
```

`app/lib/features/customer/api/customer_api.dart` (새 파일):

```dart
import '../../../core/error/api_exception.dart';
import '../../../core/proxy/api_client.dart';
import 'customer_models.dart';

/// 고객·반려동물 API. 경로는 모두 `/v1/shops/{shopId}` 아래다.
class CustomerApi {
  CustomerApi(this._client);

  final ApiClient _client;

  /// 가족 카드 목록 한 페이지. [q]가 비어 있으면 보내지 않는다.
  Future<CustomerPage> list(
    int shopId, {
    String? q,
    String sort = 'recent',
    bool includePassed = false,
    String? cursor,
  }) async {
    final data =
        await _client.get(
              '/v1/shops/$shopId/customers',
              queryParameters: {
                if (q != null && q.isNotEmpty) 'q': q,
                'sort': sort,
                'include_passed': includePassed,
                'cursor': ?cursor,
              },
            )
            as Map<String, dynamic>;
    return CustomerPage.fromJson(data);
  }

  /// 등록 1단계. 이 번호의 고객이 없으면(404 `CUSTOMER_NOT_FOUND`) null.
  Future<CustomerLookup?> lookup(int shopId, String phoneDigits) async {
    try {
      final data =
          await _client.get(
                '/v1/shops/$shopId/customers/lookup',
                queryParameters: {'phone': phoneDigits},
              )
              as Map<String, dynamic>;
      return CustomerLookup.fromJson(data);
    } on ApiException catch (e) {
      if (e.code == 'CUSTOMER_NOT_FOUND') return null;
      rethrow;
    }
  }

  /// 보호자와 첫 반려동물을 한 번에 등록한다.
  Future<CustomerDetail> register(
    int shopId, {
    required CustomerFields customer,
    required PetFields pet,
  }) async {
    final data =
        await _client.post(
              '/v1/shops/$shopId/customers',
              data: {'customer': customer.toJson(), 'pet': pet.toJson()},
            )
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  Future<CustomerDetail> customer(int shopId, int customerId) async {
    final data =
        await _client.get('/v1/shops/$shopId/customers/$customerId')
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  Future<CustomerDetail> updateCustomer(
    int shopId,
    int customerId,
    CustomerFields fields,
  ) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/customers/$customerId',
              data: fields.toJson(),
            )
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  /// 익명화 삭제(사장만).
  Future<void> deleteCustomer(int shopId, int customerId) async {
    await _client.delete('/v1/shops/$shopId/customers/$customerId');
  }

  Future<PetDetail> addPet(int shopId, int customerId, PetFields fields) async {
    final data =
        await _client.post(
              '/v1/shops/$shopId/customers/$customerId/pets',
              data: fields.toJson(),
            )
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> pet(int shopId, int petId) async {
    final data =
        await _client.get('/v1/shops/$shopId/pets/$petId')
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> updatePet(int shopId, int petId, PetFields fields) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/pets/$petId',
              data: fields.toJson(),
            )
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> markPassedAway(int shopId, int petId) async {
    final data =
        await _client.post('/v1/shops/$shopId/pets/$petId/passed-away')
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> unmarkPassedAway(int shopId, int petId) async {
    final data =
        await _client.delete('/v1/shops/$shopId/pets/$petId/passed-away')
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  /// 잘못 등록한 반려동물 삭제. 마지막 한 마리면 409 `LAST_PET`.
  Future<void> deletePet(int shopId, int petId) async {
    await _client.delete('/v1/shops/$shopId/pets/$petId');
  }

  /// 정해진 질병 종류(칩 순서대로).
  Future<List<ConditionType>> conditionTypes(int shopId) async {
    final data =
        await _client.get('/v1/shops/$shopId/pet-condition-types') as List;
    return data
        .map((e) => ConditionType.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
```

`app/lib/features/customer/api/customer_models.dart` (새 파일):

```dart
/// 고객·반려동물 API 의 응답·요청 모델.
///
/// `fromJson`은 서버의 스네이크케이스 키를 그대로 읽는다. 전화번호·이름이
/// 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
library;

/// 목록의 반려동물 한 줄.
class PetSummary {
  const PetSummary({
    required this.petId,
    required this.name,
    required this.species,
    required this.breed,
    required this.ageLabel,
    required this.hasConditions,
    required this.passedAway,
  });

  factory PetSummary.fromJson(Map<String, dynamic> json) => PetSummary(
    petId: json['pet_id'] as int,
    name: json['name'] as String,
    species: json['species'] as String,
    breed: json['breed'] as String,
    ageLabel: json['age_label'] as String,
    hasConditions: json['has_conditions'] as bool,
    passedAway: json['passed_away'] as bool,
  );

  final int petId;
  final String name;

  /// 'dog' | 'cat'
  final String species;
  final String breed;
  final String ageLabel;
  final bool hasConditions;
  final bool passedAway;
}

/// 목록의 가족 카드 하나(보호자 한 명과 그 아이들). 번호는 가린 값만 있다.
class FamilyCard {
  const FamilyCard({
    required this.customerId,
    required this.name,
    required this.phoneMasked,
    required this.pets,
  });

  factory FamilyCard.fromJson(Map<String, dynamic> json) => FamilyCard(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    phoneMasked: json['phone_masked'] as String,
    pets: (json['pets'] as List)
        .map((e) => PetSummary.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final int customerId;
  final String name;

  /// `010-12··-5678` 모양.
  final String phoneMasked;
  final List<PetSummary> pets;
}

/// 목록 한 페이지.
class CustomerPage {
  const CustomerPage({
    required this.items,
    required this.nextCursor,
    required this.petCount,
  });

  factory CustomerPage.fromJson(Map<String, dynamic> json) => CustomerPage(
    items: (json['items'] as List)
        .map((e) => FamilyCard.fromJson(e as Map<String, dynamic>))
        .toList(),
    nextCursor: json['next_cursor'] as String?,
    petCount: json['pet_count'] as int,
  );

  final List<FamilyCard> items;

  /// 다음 페이지 커서. 해석하지 않고 그대로 돌려보낸다. 없으면 마지막 페이지.
  final String? nextCursor;

  /// 검색·무지개다리 조건에 맞는 반려동물 수("고객 N마리").
  final int petCount;
}

/// 등록 1단계의 번호 조회 결과.
class CustomerLookup {
  const CustomerLookup({
    required this.customerId,
    required this.name,
    required this.petNames,
  });

  factory CustomerLookup.fromJson(Map<String, dynamic> json) => CustomerLookup(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    petNames: (json['pet_names'] as List).cast<String>(),
  );

  final int customerId;
  final String name;

  /// 무지개다리 아이는 들어 있지 않다.
  final List<String> petNames;
}

/// 반려동물의 질병 한 항목.
class PetCondition {
  const PetCondition({
    required this.typeCode,
    required this.label,
    required this.customLabel,
    required this.note,
  });

  factory PetCondition.fromJson(Map<String, dynamic> json) => PetCondition(
    typeCode: json['type_code'] as String,
    label: json['label'] as String,
    customLabel: json['custom_label'] as String?,
    note: json['note'] as String?,
  );

  final String typeCode;

  /// 정해진 질병의 이름(기타면 "기타").
  final String label;

  /// 기타일 때만 있는 직접 입력 이름.
  final String? customLabel;
  final String? note;

  /// 화면에 보일 이름 — 기타면 직접 입력한 이름.
  String get displayLabel => customLabel ?? label;
}

/// 반려동물 전체.
class Pet {
  const Pet({
    required this.petId,
    required this.customerId,
    required this.name,
    required this.species,
    required this.breed,
    required this.sex,
    required this.neutered,
    required this.birthDate,
    required this.birthYear,
    required this.ageLabel,
    required this.weightKg,
    required this.noKnownConditions,
    required this.hasConditions,
    required this.conditions,
    required this.memo,
    required this.passedAwayAt,
  });

  factory Pet.fromJson(Map<String, dynamic> json) => Pet(
    petId: json['pet_id'] as int,
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    species: json['species'] as String,
    breed: json['breed'] as String,
    sex: json['sex'] as String,
    neutered: json['neutered'] as bool,
    birthDate: json['birth_date'] == null
        ? null
        : DateTime.parse(json['birth_date'] as String),
    birthYear: json['birth_year'] as int?,
    ageLabel: json['age_label'] as String,
    weightKg: (json['weight_kg'] as num).toDouble(),
    noKnownConditions: json['no_known_conditions'] as bool,
    hasConditions: json['has_conditions'] as bool,
    conditions: (json['conditions'] as List)
        .map((e) => PetCondition.fromJson(e as Map<String, dynamic>))
        .toList(),
    memo: json['memo'] as String?,
    passedAwayAt: json['passed_away_at'] == null
        ? null
        : DateTime.parse(json['passed_away_at'] as String),
  );

  final int petId;
  final int customerId;
  final String name;

  /// 'dog' | 'cat'
  final String species;
  final String breed;

  /// 'female' | 'male'
  final String sex;
  final bool neutered;

  /// 날짜만 쓴다(시각은 자정).
  final DateTime? birthDate;
  final int? birthYear;
  final String ageLabel;
  final double weightKg;
  final bool noKnownConditions;
  final bool hasConditions;
  final List<PetCondition> conditions;
  final String? memo;
  final DateTime? passedAwayAt;

  bool get passedAway => passedAwayAt != null;
}

/// 보호자 전체. 전체 번호가 들어 있는 유일한 모델이다.
class Customer {
  const Customer({
    required this.customerId,
    required this.name,
    required this.phone,
    required this.phoneAlt,
    required this.marketingConsent,
    required this.marketingConsentChangedAt,
    required this.memo,
  });

  factory Customer.fromJson(Map<String, dynamic> json) => Customer(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    phone: json['phone'] as String,
    phoneAlt: json['phone_alt'] as String?,
    marketingConsent: json['marketing_consent'] as bool,
    marketingConsentChangedAt: DateTime.parse(
      json['marketing_consent_changed_at'] as String,
    ),
    memo: json['memo'] as String?,
  );

  final int customerId;
  final String name;

  /// 숫자만(`01012345678`).
  final String phone;
  final String? phoneAlt;
  final bool marketingConsent;
  final DateTime marketingConsentChangedAt;
  final String? memo;
}

/// 고객 상세 — 보호자 전체와 반려동물 전체.
class CustomerDetail {
  const CustomerDetail({required this.customer, required this.pets});

  factory CustomerDetail.fromJson(Map<String, dynamic> json) => CustomerDetail(
    customer: Customer.fromJson(json['customer'] as Map<String, dynamic>),
    pets: (json['pets'] as List)
        .map((e) => Pet.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final Customer customer;
  final List<Pet> pets;
}

/// 반려동물 상세의 보호자 요약. 번호는 가린 값이다.
class OwnerSummary {
  const OwnerSummary({
    required this.customerId,
    required this.name,
    required this.phoneMasked,
  });

  factory OwnerSummary.fromJson(Map<String, dynamic> json) => OwnerSummary(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    phoneMasked: json['phone_masked'] as String,
  );

  final int customerId;
  final String name;
  final String phoneMasked;
}

/// 같은 보호자의 다른 아이.
class Sibling {
  const Sibling({
    required this.petId,
    required this.name,
    required this.species,
    required this.passedAway,
  });

  factory Sibling.fromJson(Map<String, dynamic> json) => Sibling(
    petId: json['pet_id'] as int,
    name: json['name'] as String,
    species: json['species'] as String,
    passedAway: json['passed_away'] as bool,
  );

  final int petId;
  final String name;
  final String species;
  final bool passedAway;
}

/// 반려동물 상세 — 반려동물 전체, 보호자 요약, 같은 보호자의 다른 아이.
class PetDetail {
  const PetDetail({
    required this.pet,
    required this.owner,
    required this.siblings,
  });

  factory PetDetail.fromJson(Map<String, dynamic> json) => PetDetail(
    pet: Pet.fromJson(json['pet'] as Map<String, dynamic>),
    owner: OwnerSummary.fromJson(json['owner'] as Map<String, dynamic>),
    siblings: (json['siblings'] as List)
        .map((e) => Sibling.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final Pet pet;
  final OwnerSummary owner;
  final List<Sibling> siblings;
}

/// 정해진 질병 종류 하나.
class ConditionType {
  const ConditionType({
    required this.code,
    required this.label,
    required this.sortOrder,
  });

  factory ConditionType.fromJson(Map<String, dynamic> json) => ConditionType(
    code: json['code'] as String,
    label: json['label'] as String,
    sortOrder: json['sort_order'] as int,
  );

  static const otherCode = 'other';

  final String code;
  final String label;
  final int sortOrder;
}

/// 보호자 폼(등록 2단계·보호자 수정). 전화번호는 숫자만 보낸다.
class CustomerFields {
  const CustomerFields({
    required this.name,
    required this.phone,
    required this.phoneAlt,
    required this.marketingConsent,
    required this.memo,
  });

  final String name;
  final String phone;
  final String? phoneAlt;
  final bool marketingConsent;
  final String? memo;

  Map<String, dynamic> toJson() => {
    'name': name,
    'phone': phone,
    'phone_alt': phoneAlt,
    'marketing_consent': marketingConsent,
    'memo': memo,
  };
}

/// 반려동물 폼에 넣는 질병 한 항목.
class ConditionEntry {
  const ConditionEntry({required this.typeCode, this.customLabel, this.note});

  final String typeCode;
  final String? customLabel;
  final String? note;

  Map<String, dynamic> toJson() => {
    'type_code': typeCode,
    'custom_label': customLabel,
    'note': note,
  };
}

/// 반려동물 폼(등록 3단계·반려동물 추가·수정). 생일과 태어난 해는 하나만,
/// 둘 다 없으면 "나이 모름"이다. 질병은 목록 전체를 보낸다.
class PetFields {
  const PetFields({
    required this.name,
    required this.species,
    required this.breed,
    required this.sex,
    required this.neutered,
    required this.birthDate,
    required this.birthYear,
    required this.weightKg,
    required this.noKnownConditions,
    required this.conditions,
    required this.memo,
  });

  final String name;
  final String species;
  final String breed;
  final String sex;
  final bool neutered;
  final DateTime? birthDate;
  final int? birthYear;
  final double weightKg;
  final bool noKnownConditions;
  final List<ConditionEntry> conditions;
  final String? memo;

  Map<String, dynamic> toJson() => {
    'name': name,
    'species': species,
    'breed': breed,
    'sex': sex,
    'neutered': neutered,
    'birth_date': birthDate == null ? null : _isoDate(birthDate!),
    'birth_year': birthYear,
    'weight_kg': weightKg,
    'no_known_conditions': noKnownConditions,
    'conditions': [for (final c in conditions) c.toJson()],
    'memo': memo,
  };

  static String _isoDate(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/core/error/error_messages_test.dart test/features/customer/api/customer_api_test.dart test/support/customer_fixtures.dart` → Expected: `+16: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+255: All tests passed!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `customer_api.dart`의 `lookup`에서 `if (e.code == 'CUSTOMER_NOT_FOUND') return null;`을 지운다 → `404 CUSTOMER_NOT_FOUND 면 null 이다` 실패

- [ ] **Step 6: 커밋한다**

```bash
git add app/lib/core/error/error_messages.dart app/lib/features/customer/api/customer_api.dart app/lib/features/customer/api/customer_models.dart app/test/core/error/error_messages_test.dart app/test/features/customer/api/customer_api_test.dart app/test/support/customer_fixtures.dart
git commit -m "feat(app): 고객·반려동물 API 와 모델, 오류 문구

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 고객 폼의 입력 규칙과 표시 형식

**Files:**
- Create: `app/lib/features/customer/state/customer_input.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Create: `app/test/features/customer/state/customer_input_test.dart`

**Interfaces:**
- Consumes: 없음(표준 라이브러리만)
- Produces: `lib/features/customer/state/customer_input.dart`: `phoneDigits(String) → String`, `isValidPhone(String digits) → bool`(백엔드 `_VALID`와 같은 정규식), `formatPhone(String digits) → String`, `maskedTail(String phoneMasked) → '··5678'`, `parseWeight(String) → double?`, `weightText(double) → '3.2' | '4'`, `formatWeight(double) → '3.2kg'`, `isValidBirthYear(int, DateTime today)`, `earliestBirthDate(DateTime today)`, `optionalText(String) → String?`, `parseBirthDate(String, DateTime today) → DateTime?`. `AppStrings`에 `speciesDog`·`speciesCat`·`sexFemale`·`sexMale`·`neutered`, `speciesLabel(String)`, `sexLabel(String)`.

**알아 둘 것:**
- 규칙은 결정 기록 005 의 서버 규칙을 앱에서 먼저 보는 것이다(요청 없이 바로 알림). 최종 판단은 서버다.
- 생일은 날짜 선택기 대신 글자 입력(`YYYY.MM.DD`, `YYYY-MM-DD`, `YYYYMMDD`)이다 — 앱에 `flutter_localizations`가 없어 Material 날짜 선택기가 영어로 뜬다. 이 계획은 새 의존성을 넣지 않는다.

**막는 위협:** A7(형식이 안 맞는 번호로 조회하면 서버는 422 다 — 앱이 먼저 거른다)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/features/customer/state/customer_input_test.dart` (새 파일):

```dart
import 'package:chagocnote/features/customer/state/customer_input.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('전화번호', () {
    test('숫자만 남긴다 — 하이픈·공백·전각 숫자는 버린다', () {
      expect(phoneDigits('010-1234 5678'), '01012345678');
      expect(phoneDigits('０１０'), '');
    });

    test('서버와 같은 형식만 받는다', () {
      for (final ok in [
        '01012345678',
        '0111234567',
        '0212345678',
        '021234567',
        '0311234567',
        '07012345678',
      ]) {
        expect(isValidPhone(ok), isTrue, reason: ok);
      }
      for (final bad in [
        '',
        '0101234',
        '01212345678',
        '0701234567',
        '0661234567',
        '821012345678',
      ]) {
        expect(isValidPhone(bad), isFalse, reason: bad);
      }
    });

    test('하이픈을 넣어 보인다 — 서울은 두 자리 국번', () {
      expect(formatPhone('01012345678'), '010-1234-5678');
      expect(formatPhone('0212345678'), '02-1234-5678');
      expect(formatPhone('021234567'), '02-123-4567');
      expect(formatPhone('0311234567'), '031-123-4567');
      expect(formatPhone('123'), '123');
    });

    test('가린 번호의 뒷자리를 줄여 보인다', () {
      expect(maskedTail('010-12··-5678'), '··5678');
    });
  });

  group('몸무게', () {
    test('0 초과, 세 자리 정수와 소수 한 자리까지', () {
      expect(parseWeight('3.2'), 3.2);
      expect(parseWeight(' 12 '), 12);
      expect(parseWeight('999.9'), 999.9);
      for (final bad in ['', '0', '0.0', '-1', '3.25', '1000', 'abc', '3.']) {
        expect(parseWeight(bad), isNull, reason: bad);
      }
    });

    test('정수면 소수점을 빼고 보인다', () {
      expect(formatWeight(3.2), '3.2kg');
      expect(formatWeight(4), '4kg');
      expect(weightText(3.2), '3.2');
    });
  });

  test('태어난 해는 올해부터 40년 전까지', () {
    final today = DateTime(2026, 9, 22);
    expect(isValidBirthYear(2026, today), isTrue);
    expect(isValidBirthYear(1986, today), isTrue);
    expect(isValidBirthYear(1985, today), isFalse);
    expect(isValidBirthYear(2027, today), isFalse);
    expect(earliestBirthDate(today), DateTime(1986, 9, 22));
  });

  test('빈 선택 입력은 null', () {
    expect(optionalText('  '), isNull);
    expect(optionalText(' 메모 '), '메모');
  });

  test('생일은 여러 모양으로 받고, 없는 날·미래·40년 전보다 이른 날은 거절한다', () {
    final today = DateTime(2026, 9, 22);
    expect(parseBirthDate('2021.03.04', today), DateTime(2021, 3, 4));
    expect(parseBirthDate('2021-03-04', today), DateTime(2021, 3, 4));
    expect(parseBirthDate('20210304', today), DateTime(2021, 3, 4));
    expect(parseBirthDate('2026.09.22', today), DateTime(2026, 9, 22));
    expect(parseBirthDate('1986.09.22', today), DateTime(1986, 9, 22));
    for (final bad in ['', '2021.02.30', '2026.09.23', '1986.09.21', '21.03.04', 'abcd']) {
      expect(parseBirthDate(bad, today), isNull, reason: bad);
    }
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/features/customer/state/customer_input_test.dart`

Expected: 컴파일 오류 — `customer_input.dart`가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/features/customer/state/customer_input.dart` (새 파일):

```dart
/// 고객·반려동물 폼의 입력 규칙과 표시 형식. 서버 규칙(결정 기록 005)을
/// 앱에서 먼저 확인해 요청 없이 바로 알려 주려는 것이다 — 최종 판단은 서버다.
library;

/// 휴대전화(010·011·016~019), 서울(02), 지역 번호(031~065 범위의 세 자리),
/// 인터넷 전화(070). 백엔드 `phone_number.py` 의 `_VALID` 와 같다.
final _validPhone = RegExp(
  r'^(01[016789]\d{7,8}|02\d{7,8}|0[3-6][1-5]\d{7,8}|070\d{8})$',
);

/// 숫자만 남긴다(하이픈·공백 제거). 전각 숫자는 버린다 — 서버도 받지 않는다.
String phoneDigits(String raw) => raw.replaceAll(RegExp(r'[^0-9]'), '');

bool isValidPhone(String digits) => _validPhone.hasMatch(digits);

/// 숫자만 저장된 번호를 `010-1234-5678` 모양으로 보인다.
String formatPhone(String digits) {
  if (!isValidPhone(digits)) return digits;
  final area = digits.startsWith('02')
      ? digits.substring(0, 2)
      : digits.substring(0, 3);
  final rest = digits.substring(area.length);
  final middle = rest.substring(0, rest.length - 4);
  final last = rest.substring(rest.length - 4);
  return '$area-$middle-$last';
}

/// 가린 번호(`010-12··-5678`)의 뒷자리를 `··5678` 로 줄인다(가족 카드 머리).
String maskedTail(String phoneMasked) {
  final last = phoneMasked.length >= 4
      ? phoneMasked.substring(phoneMasked.length - 4)
      : phoneMasked;
  return '··$last';
}

/// 몸무게(kg). 0 초과, 999.9 이하, 소수 한 자리까지. 아니면 null.
double? parseWeight(String raw) {
  final text = raw.trim();
  if (!RegExp(r'^\d{1,3}(\.\d)?$').hasMatch(text)) return null;
  final value = double.parse(text);
  return value > 0 ? value : null;
}

/// 몸무게 입력 칸에 넣을 글자 — `3.2`, `4`.
String weightText(double kg) =>
    kg == kg.roundToDouble() ? kg.toStringAsFixed(0) : kg.toStringAsFixed(1);

/// `3.2kg`, `4kg`.
String formatWeight(double kg) => '${weightText(kg)}kg';

/// 서버는 생일·태어난 해를 40년 전까지 받는다. 태어난 해는 올해까지.
bool isValidBirthYear(int year, DateTime today) =>
    year <= today.year && year >= today.year - 40;

/// 생일로 고를 수 있는 가장 이른 날(40년 전 오늘).
DateTime earliestBirthDate(DateTime today) =>
    DateTime(today.year - 40, today.month, today.day);

/// 앞뒤 공백을 없애고, 비었으면 null.
String? optionalText(String raw) {
  final text = raw.trim();
  return text.isEmpty ? null : text;
}

/// 생일 입력(`2021.03.04`, `2021-03-04`, `20210304`)을 날짜로 바꾼다. 없는 날짜,
/// 오늘보다 늦은 날, 40년보다 이른 날은 null.
DateTime? parseBirthDate(String raw, DateTime today) {
  final digits = raw.replaceAll(RegExp(r'[.\-/\s]'), '');
  if (!RegExp(r'^\d{8}$').hasMatch(digits)) return null;
  final year = int.parse(digits.substring(0, 4));
  final month = int.parse(digits.substring(4, 6));
  final day = int.parse(digits.substring(6, 8));
  final date = DateTime(year, month, day);
  if (date.year != year || date.month != month || date.day != day) return null;
  final todayDate = DateTime(today.year, today.month, today.day);
  if (date.isAfter(todayDate) || date.isBefore(earliestBirthDate(today))) {
    return null;
  }
  return date;
}
```

`app/lib/l10n/app_strings.dart` (수정):

```diff
@@ -95,6 +95,25 @@ class AppStrings {
   static const withdrawShopCloseConfirm = '매장을 닫고 탈퇴';
   static const goToMembers = '멤버 관리로 이동';
 
+  // 고객·반려동물
+  static const speciesDog = '강아지';
+  static const speciesCat = '고양이';
+  static const sexFemale = '여아';
+  static const sexMale = '남아';
+  static const neutered = '중성화';
+
+  static String speciesLabel(String species) => switch (species) {
+        'dog' => speciesDog,
+        'cat' => speciesCat,
+        _ => species,
+      };
+
+  static String sexLabel(String sex) => switch (sex) {
+        'female' => sexFemale,
+        'male' => sexMale,
+        _ => sex,
+      };
+
   /// 로그인 수단 제공자 코드를 화면에 보여줄 라벨로 바꾼다. 계정 화면과
   /// 재인증 시트(Task 16)가 함께 쓴다.
   static String providerLabel(String provider) => switch (provider) {
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/features/customer/state/customer_input_test.dart` → Expected: `+9: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+264: All tests passed!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `customer_input.dart`의 정규식에서 `070\d{8}`을 `070\d{7,8}`로 바꾼다 → `서버와 같은 형식만 받는다` 실패

- [ ] **Step 6: 커밋한다**

```bash
git add app/lib/features/customer/state/customer_input.dart app/lib/l10n/app_strings.dart app/test/features/customer/state/customer_input_test.dart
git commit -m "feat(app): 고객 폼의 입력 규칙과 표시 형식

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 고객 목록 컨트롤러와 상세 프로바이더

**Files:**
- Create: `app/lib/features/customer/state/customer_list_controller.dart`
- Create: `app/lib/features/customer/state/customer_providers.dart`
- Create: `app/test/features/customer/state/customer_list_controller_test.dart`
- Create: `app/test/support/customer_test_app.dart`

**Interfaces:**
- Consumes: `CustomerApi`(Task 2), `apiClientProvider`(`core/proxy/providers.dart`), `runShopScoped(Ref, action)`(`features/shop/state/shop_errors.dart` — `NOT_A_MEMBER`면 `reloadMe()` 뒤 다시 던진다)
- Produces: `lib/features/customer/state/customer_providers.dart`: `customerApiProvider`, `typedef PetKey = ({int shopId, int petId})`, `typedef CustomerKey = ({int shopId, int customerId})`, `petDetailProvider`(`FutureProvider.autoDispose.family<PetDetail, PetKey>`), `customerDetailProvider`(`…<CustomerDetail, CustomerKey>`), `conditionTypesProvider`(`…<List<ConditionType>, int>`). `lib/features/customer/state/customer_list_controller.dart`: `typedef CustomerListQuery = ({int shopId, String q, String sort, bool includePassed})`, `CustomerListState{items, nextCursor, petCount, loadingMore, loadMoreError, hasMore}`, `CustomerListController.loadMore()`, `customerListControllerProvider`(`AsyncNotifierProvider.autoDispose.family<…, CustomerListQuery>`). 테스트 준비물 `test/support/customer_test_app.dart`: `CustomerTestSetup(FakeHandler, {role = 'owner', overrides})`(가짜 세션·가짜 어댑터를 문 진짜 `ApiClient`·`MemoryPrefsStore`, `.calls`), `customerRouterApp(container)`, `customerTestShopId = 3`.

**알아 둘 것:**
- 조회 조건마다 컨트롤러가 따로 생긴다(family 키가 조건 레코드). 검색어가 바뀌면 화면은 새 조건의 컨트롤러를 보고, 앞선 것은 autoDispose 로 버려진다 — 늦게 온 옛 검색 결과가 새 결과를 덮지 않는다(C12).
- **Riverpod 3.4 에서는 `invalidate` 뒤에도 같은 노티파이어 인스턴스가 다시 `build()`를 돈다 — `ref.mounted`가 참으로 남는다.** 그래서 `build()`마다 느는 `_generation`을 비교해 다시 불러오는 사이 끝난 다음 페이지 요청을 버린다. 참조 구현에서 `ref.mounted`만 봤을 때 `다음 페이지를 기다리는 사이 다시 불러오면 옛 목록에 이어 붙이지 않는다`가 실패한 것을 보고 넣었다.
- `runShopScoped`는 `features/shop/state/`에 있다. 기존 `members_controller`처럼 다른 기능의 state 를 import 한다(옮기지 않는다).

**막는 위협:** C5(`NOT_A_MEMBER` → 내 정보 재조회), C12(조건별 컨트롤러), A1(다시 불러오는 사이 끝난 다음 페이지를 붙이지 않는다)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/features/customer/state/customer_list_controller_test.dart` (새 파일):

```dart
import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/customer/state/customer_list_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

const _query = (
  shopId: customerTestShopId,
  q: '',
  sort: 'recent',
  includePassed: false,
);

/// 컨트롤러를 붙잡아 두는 구독(autoDispose 가 중간에 버리지 않게).
ProviderSubscription<AsyncValue<CustomerListState>> _listen(
  ProviderContainer container,
  CustomerListQuery query,
) => container.listen(customerListControllerProvider(query), (_, _) {});

void main() {
  test('첫 페이지를 불러오고, 다음 페이지를 이어 붙인다', () async {
    final setup = CustomerTestSetup((options, body) {
      final cursor = options.queryParameters['cursor'];
      if (cursor == null) {
        return FakeResponse(
          statusCode: 200,
          data: pageJson(
            items: [familyJson(customerId: 1)],
            nextCursor: 'c1',
            petCount: 2,
          ),
        );
      }
      expect(cursor, 'c1');
      return FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 2)], petCount: 2),
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);

    final first = await setup.container.read(
      customerListControllerProvider(_query).future,
    );
    expect(first.items.map((c) => c.customerId), [1]);
    expect(first.hasMore, isTrue);
    expect(first.petCount, 2);

    await setup.container
        .read(customerListControllerProvider(_query).notifier)
        .loadMore();

    final state = setup.container
        .read(customerListControllerProvider(_query))
        .value!;
    expect(state.items.map((c) => c.customerId), [1, 2]);
    expect(state.hasMore, isFalse);
    expect(state.loadingMore, isFalse);
  });

  test('다음 페이지를 불러오는 중에 또 부르면 요청을 하나만 보낸다', () async {
    final gate = Completer<FakeResponse>();
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(statusCode: 200, data: pageJson(nextCursor: 'c1'));
      }
      return gate.future;
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);
    await setup.container.read(customerListControllerProvider(_query).future);
    final notifier = setup.container.read(
      customerListControllerProvider(_query).notifier,
    );

    final first = notifier.loadMore();
    await notifier.loadMore();
    expect(
      setup.container
          .read(customerListControllerProvider(_query))
          .value!
          .loadingMore,
      isTrue,
    );
    gate.complete(
      FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 9)]),
      ),
    );
    await first;

    expect(
      setup.adapter.requests.where((r) => r.queryParameters['cursor'] == 'c1'),
      hasLength(1),
    );
  });

  test('다음 페이지가 실패하면 이미 보인 목록을 두고 오류만 기억한다', () async {
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(statusCode: 200, data: pageJson(nextCursor: 'c1'));
      }
      return const FakeResponse(
        statusCode: 500,
        data: {'code': 'INTERNAL', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);
    await setup.container.read(customerListControllerProvider(_query).future);

    await setup.container
        .read(customerListControllerProvider(_query).notifier)
        .loadMore();

    final state = setup.container
        .read(customerListControllerProvider(_query))
        .value!;
    expect(state.items, hasLength(1));
    expect(state.hasMore, isTrue);
    expect(state.loadMoreError, isA<ApiException>());
  });

  test('다음 페이지를 기다리는 사이 다시 불러오면 옛 목록에 이어 붙이지 않는다', () async {
    final gate = Completer<FakeResponse>();
    var firstPages = 0;
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        firstPages++;
        return FakeResponse(
          statusCode: 200,
          data: pageJson(
            items: [familyJson(customerId: firstPages)],
            nextCursor: 'c1',
          ),
        );
      }
      return gate.future;
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);
    await setup.container.read(customerListControllerProvider(_query).future);

    final pending = setup.container
        .read(customerListControllerProvider(_query).notifier)
        .loadMore();
    setup.container.invalidate(customerListControllerProvider);
    final reloaded = await setup.container.read(
      customerListControllerProvider(_query).future,
    );
    gate.complete(
      FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 99)]),
      ),
    );
    await pending;

    expect(reloaded.items.map((c) => c.customerId), [2]);
    expect(
      setup.container
          .read(customerListControllerProvider(_query))
          .value!
          .items
          .map((c) => c.customerId),
      [2],
    );
  });

  test('조건마다 따로 불러온다 — 검색어·정렬·무지개다리 포함이 쿼리에 실린다', () async {
    final setup = CustomerTestSetup((options, body) {
      return FakeResponse(statusCode: 200, data: pageJson(items: []));
    });
    addTearDown(setup.container.dispose);
    const query = (
      shopId: customerTestShopId,
      q: 'ㅋㅇ',
      sort: 'name',
      includePassed: true,
    );
    _listen(setup.container, query);

    await setup.container.read(customerListControllerProvider(query).future);

    expect(setup.adapter.requests.single.queryParameters, {
      'q': 'ㅋㅇ',
      'sort': 'name',
      'include_passed': true,
    });
  });

  test('NOT_A_MEMBER 면 내 정보를 다시 불러온다(C5)', () async {
    final setup = CustomerTestSetup((options, body) {
      return const FakeResponse(
        statusCode: 403,
        data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);
    _listen(setup.container, _query);

    await expectLater(
      setup.container.read(customerListControllerProvider(_query).future),
      throwsA(isA<ApiException>()),
    );
    expect(setup.gateway.refreshMeCallCount, 1);
  });
}
```

`app/test/support/customer_test_app.dart` (새 파일):

```dart
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;

import 'fake_http_client_adapter.dart';
import 'fake_session_gateway.dart';

/// 고객 기능 테스트의 매장(3번, 첫 입점 매장 이름).
const customerTestShopId = 3;

Me customerTestMe({String role = 'owner'}) => Me(
  id: 1,
  displayName: '민석',
  profileImageUrl: null,
  identities: const ['apple'],
  shops: [
    ShopMembership(
      shopId: customerTestShopId,
      shopName: 'Hiss Haus',
      role: role,
    ),
  ],
);

/// 고객 기능 테스트의 준비물 — 가짜 세션(3번 매장의 [role]), 가짜 HTTP 어댑터를
/// 문 진짜 `ApiClient`, 메모리 설정 저장소.
class CustomerTestSetup {
  CustomerTestSetup(
    FakeHandler handle, {
    String role = 'owner',
    List<Override> overrides = const [],
  }) : adapter = FakeHttpClientAdapter(handle),
       gateway = FakeSessionGateway()
         ..meOnRestore = customerTestMe(role: role)
         ..meOnRefresh = customerTestMe(role: role),
       prefs = MemoryPrefsStore() {
    // 원 요청과 갱신은 같은 가짜 어댑터를 문 별도 Dio 두 개로 나눈다(ApiClient 문서).
    final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
    final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
    container = ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [
        sessionGatewayProvider.overrideWithValue(gateway),
        prefsStoreProvider.overrideWithValue(prefs),
        apiClientProvider.overrideWith(
          (ref) => ApiClient(
            tokenStore: MemoryTokenStore(),
            dio: dio,
            refreshDio: refreshDio,
            onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
          ),
        ),
        ...overrides,
      ],
    );
  }

  final FakeHttpClientAdapter adapter;
  final FakeSessionGateway gateway;
  final MemoryPrefsStore prefs;
  late final ProviderContainer container;

  /// 어댑터를 거쳐 간 요청을 `METHOD path` 로 줄인 것.
  List<String> get calls => [
    for (final r in adapter.requests) '${r.method} ${r.path}',
  ];
}

/// 실제 라우터로 앱을 띄운다. 글래스는 불투명 대체 면으로 그린다.
Widget customerRouterApp(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) =>
              GlassBridge(factory: const OpaqueSurfaceFactory(), child: child!),
        );
      },
    ),
  );
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/features/customer/state/customer_list_controller_test.dart test/support/customer_test_app.dart`

Expected: 컴파일 오류 — `customer_list_controller.dart`·`customer_test_app.dart`가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/features/customer/state/customer_list_controller.dart` (새 파일):

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shop/state/shop_errors.dart';
import '../api/customer_api.dart';
import '../api/customer_models.dart';
import 'customer_providers.dart';

/// 목록 조회 조건. 조건마다 컨트롤러가 따로 생긴다 — 검색어가 바뀌면 화면은
/// 새 조건의 컨트롤러를 보고, 앞선 조건의 컨트롤러는 버려진다(autoDispose).
/// 그래서 늦게 도착한 옛 검색 결과가 새 결과를 덮지 않는다(C12).
typedef CustomerListQuery = ({
  int shopId,
  String q,
  String sort,
  bool includePassed,
});

/// 지금까지 불러온 가족 카드와 다음 페이지 상태.
class CustomerListState {
  const CustomerListState({
    required this.items,
    required this.nextCursor,
    required this.petCount,
    this.loadingMore = false,
    this.loadMoreError,
  });

  final List<FamilyCard> items;
  final String? nextCursor;
  final int petCount;

  /// 다음 페이지를 불러오는 중.
  final bool loadingMore;

  /// 마지막 다음 페이지 요청의 오류. 이미 보인 목록은 그대로 둔다.
  final Object? loadMoreError;

  bool get hasMore => nextCursor != null;
}

class CustomerListController extends AsyncNotifier<CustomerListState> {
  CustomerListController(this.query);

  final CustomerListQuery query;

  CustomerApi get _api => ref.read(customerApiProvider);

  /// build() 가 돌 때마다 하나씩 는다. 다시 불러오는 사이(쓰기 뒤 invalidate)
  /// 끝난 다음 페이지 요청이 새 목록에 옛 페이지를 붙이지 않게 비교한다 —
  /// 다시 불러와도 컨트롤러 인스턴스는 그대로라 `ref.mounted`만으로는 모른다.
  int _generation = 0;

  Future<CustomerPage> _fetch(String? cursor) => _api.list(
    query.shopId,
    q: query.q,
    sort: query.sort,
    includePassed: query.includePassed,
    cursor: cursor,
  );

  @override
  Future<CustomerListState> build() async {
    _generation++;
    final page = await runShopScoped(ref, () => _fetch(null));
    return CustomerListState(
      items: page.items,
      nextCursor: page.nextCursor,
      petCount: page.petCount,
    );
  }

  /// 다음 페이지를 붙인다. 첫 페이지를 불러오는 중이거나, 이미 다음 페이지를
  /// 불러오는 중이거나, 마지막 페이지면 아무것도 하지 않는다.
  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading ||
        current == null ||
        !current.hasMore ||
        current.loadingMore) {
      return;
    }
    final generation = _generation;
    bool stale() => !ref.mounted || generation != _generation;
    state = AsyncData(
      CustomerListState(
        items: current.items,
        nextCursor: current.nextCursor,
        petCount: current.petCount,
        loadingMore: true,
      ),
    );
    try {
      final page = await runShopScoped(ref, () => _fetch(current.nextCursor));
      // 그사이 다시 불러왔으면(쓰기 뒤 invalidate) 옛 목록에 이어 붙이지 않는다.
      if (stale()) return;
      state = AsyncData(
        CustomerListState(
          items: [...current.items, ...page.items],
          nextCursor: page.nextCursor,
          petCount: page.petCount,
        ),
      );
    } catch (e) {
      if (stale()) return;
      state = AsyncData(
        CustomerListState(
          items: current.items,
          nextCursor: current.nextCursor,
          petCount: current.petCount,
          loadMoreError: e,
        ),
      );
    }
  }
}

final customerListControllerProvider = AsyncNotifierProvider.autoDispose
    .family<CustomerListController, CustomerListState, CustomerListQuery>(
      CustomerListController.new,
    );
```

`app/lib/features/customer/state/customer_providers.dart` (새 파일):

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../shop/state/shop_errors.dart';
import '../api/customer_api.dart';
import '../api/customer_models.dart';

final customerApiProvider = Provider<CustomerApi>(
  (ref) => CustomerApi(ref.watch(apiClientProvider)),
);

typedef PetKey = ({int shopId, int petId});
typedef CustomerKey = ({int shopId, int customerId});

/// 반려동물 상세. 화면을 떠나면 버린다(autoDispose) — 오류에 갇히지 않게 한다.
/// 쓰기가 끝나면 `CustomerCommands`가 다시 불러오게 한다.
final petDetailProvider = FutureProvider.autoDispose.family<PetDetail, PetKey>(
  (ref, key) => runShopScoped(
    ref,
    () => ref.read(customerApiProvider).pet(key.shopId, key.petId),
  ),
);

/// 고객 상세(전체 번호가 들어 있는 유일한 조회). 반려동물 상세의 보호자 탭과
/// 보호자 수정 화면이 쓴다.
final customerDetailProvider = FutureProvider.autoDispose
    .family<CustomerDetail, CustomerKey>(
      (ref, key) => runShopScoped(
        ref,
        () =>
            ref.read(customerApiProvider).customer(key.shopId, key.customerId),
      ),
    );

/// 정해진 질병 종류(칩 순서대로).
final conditionTypesProvider = FutureProvider.autoDispose
    .family<List<ConditionType>, int>(
      (ref, shopId) => runShopScoped(
        ref,
        () => ref.read(customerApiProvider).conditionTypes(shopId),
      ),
    );
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/features/customer/state/customer_list_controller_test.dart test/support/customer_test_app.dart` → Expected: `+6: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+270: All tests passed!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `customer_list_controller.dart`의 `bool stale() => !ref.mounted || generation != _generation;`을 `bool stale() => !ref.mounted;`로 바꾼다 → `다음 페이지를 기다리는 사이 다시 불러오면 옛 목록에 이어 붙이지 않는다` 실패
- `loadMore()`의 `current.loadingMore` 조건을 지운다 → `다음 페이지를 불러오는 중에 또 부르면 요청을 하나만 보낸다` 실패

- [ ] **Step 6: 커밋한다**

```bash
git add app/lib/features/customer/state/customer_list_controller.dart app/lib/features/customer/state/customer_providers.dart app/test/features/customer/state/customer_list_controller_test.dart app/test/support/customer_test_app.dart
git commit -m "feat(app): 고객 목록 컨트롤러와 상세 프로바이더

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 고객 쓰기 명령, 목록 보기 방식 기억, 검색 입력 지연

**Files:**
- Modify: `app/lib/core/storage/prefs_store.dart`
- Create: `app/lib/features/customer/state/customer_commands.dart`
- Create: `app/lib/features/customer/state/customer_view_mode.dart`
- Create: `app/lib/features/customer/state/search_debouncer.dart`
- Modify: `app/test/core/storage/stores_test.dart`
- Create: `app/test/features/customer/state/customer_commands_test.dart`
- Create: `app/test/features/customer/state/customer_view_mode_test.dart`
- Create: `app/test/features/customer/state/search_debouncer_test.dart`

**Interfaces:**
- Consumes: `customerApiProvider`·`petDetailProvider`·`customerDetailProvider`·`customerListControllerProvider`(Task 4), `prefsStoreProvider`(`core/proxy/providers.dart`), `runShopScoped`
- Produces: `PrefsStore.readCustomerViewMode() → Future<String?>`·`writeCustomerViewMode(String)`(보안 저장소 키 `customer_view_mode`, `clear()`가 지우지 않는다). `lib/features/customer/state/customer_view_mode.dart`: `enum CustomerViewMode { list, grid }`, `customerViewModeProvider`(`select(mode)`). `lib/features/customer/state/search_debouncer.dart`: `SearchDebouncer({required onSearch, delay = 300ms})`의 `onChanged(TextEditingValue)`·`dispose()`. `lib/features/customer/state/customer_commands.dart`: `customerCommandsProvider`의 `CustomerCommands` — `lookup`, `register`, `updateCustomer`, `addPet`, `updatePet`, `markPassedAway`, `unmarkPassedAway`, `deletePet`, `deleteCustomer`.

**알아 둘 것:**
- 쓰기가 성공하면 목록 family 전체와 상세 두 family 를 `invalidate`한다(보고 있는 것만 다시 부른다). 반려동물 삭제는 반려동물 상세를, 고객 삭제는 두 상세를 다시 부르지 않는다 — 지운 대상을 다시 부르면 404 가 화면에 잠깐 보인다.
- 검색 지연은 설계 8.2 "한글 조합 중에는 기다리고, 조합이 끝난 뒤 0.3초"다. `TextEditingValue.composing`이 비어 있지 않으면 조합 중으로 본다. **iOS 한글 입력기가 조합 구간을 어떻게 알리는지는 Task 11 의 시뮬레이터 흐름에서 확인한다.**
- 보기 방식은 기기 설정이다 — 로그아웃·탈퇴의 `clear()`로 지우지 않는다.

**막는 위협:** C5, A4(지운 대상의 상세를 다시 불러 404 가 보이지 않게)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/core/storage/stores_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -20,4 +20,12 @@ void main() {
     await prefs.clear();
     expect(await prefs.readLastShopId(), isNull);
   });
+
+  test('고객 목록 보기 방식은 기억하고, 로그아웃 정리(clear)로 지워지지 않는다', () async {
+    final prefs = MemoryPrefsStore();
+    expect(await prefs.readCustomerViewMode(), isNull);
+    await prefs.writeCustomerViewMode('grid');
+    await prefs.clear();
+    expect(await prefs.readCustomerViewMode(), 'grid');
+  });
 }
```

`app/test/features/customer/state/customer_commands_test.dart` (새 파일):

```dart
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:chagocnote/features/customer/state/customer_commands.dart';
import 'package:chagocnote/features/customer/state/customer_list_controller.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

const _shop = customerTestShopId;
const _query = (shopId: _shop, q: '', sort: 'recent', includePassed: false);
const _petKey = (shopId: _shop, petId: 11);
const _customerKey = (shopId: _shop, customerId: 7);

/// 목록·반려동물 상세·고객 상세를 모두 보고 있는 상태를 만든다.
Future<CustomerTestSetup> _watchingEverything(FakeHandler writes) async {
  final setup = CustomerTestSetup((options, body) {
    final key = '${options.method} ${options.path}';
    switch (key) {
      case 'GET /v1/shops/3/customers':
        return FakeResponse(statusCode: 200, data: pageJson());
      case 'GET /v1/shops/3/pets/11':
        return FakeResponse(statusCode: 200, data: petDetailJson());
      case 'GET /v1/shops/3/customers/7':
        return FakeResponse(statusCode: 200, data: customerDetailJson());
    }
    return writes(options, body);
  });
  final c = setup.container;
  c.listen(customerListControllerProvider(_query), (_, _) {});
  c.listen(petDetailProvider(_petKey), (_, _) {});
  c.listen(customerDetailProvider(_customerKey), (_, _) {});
  await c.read(customerListControllerProvider(_query).future);
  await c.read(petDetailProvider(_petKey).future);
  await c.read(customerDetailProvider(_customerKey).future);
  setup.adapter.requests.clear();
  return setup;
}

/// 다시 불러오기가 끝날 때까지 기다린다.
Future<void> _settle(CustomerTestSetup setup) async {
  final c = setup.container;
  await c.read(customerListControllerProvider(_query).future);
  await c.read(petDetailProvider(_petKey).future);
  await c.read(customerDetailProvider(_customerKey).future);
}

const _fields = PetFields(
  name: '콩이',
  species: 'dog',
  breed: '말티즈',
  sex: 'female',
  neutered: true,
  birthDate: null,
  birthYear: null,
  weightKg: 3.2,
  noKnownConditions: true,
  conditions: [],
  memo: null,
);

void main() {
  test('반려동물을 고치면 목록·반려동물 상세·고객 상세를 다시 불러온다', () async {
    final setup = await _watchingEverything((options, body) {
      expect('${options.method} ${options.path}', 'PUT /v1/shops/3/pets/11');
      return FakeResponse(statusCode: 200, data: petDetailJson());
    });
    addTearDown(setup.container.dispose);

    await setup.container
        .read(customerCommandsProvider)
        .updatePet(_shop, 11, _fields);
    await _settle(setup);

    expect(
      setup.calls,
      unorderedEquals([
        'PUT /v1/shops/3/pets/11',
        'GET /v1/shops/3/customers',
        'GET /v1/shops/3/pets/11',
        'GET /v1/shops/3/customers/7',
      ]),
    );
  });

  test('반려동물을 지우면 그 아이의 상세는 다시 부르지 않는다', () async {
    final setup = await _watchingEverything((options, body) {
      expect('${options.method} ${options.path}', 'DELETE /v1/shops/3/pets/11');
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await setup.container.read(customerCommandsProvider).deletePet(_shop, 11);
    await _settle(setup);

    expect(
      setup.calls,
      unorderedEquals([
        'DELETE /v1/shops/3/pets/11',
        'GET /v1/shops/3/customers',
        'GET /v1/shops/3/customers/7',
      ]),
    );
  });

  test('고객을 지우면 목록만 다시 부른다', () async {
    final setup = await _watchingEverything((options, body) {
      expect(
        '${options.method} ${options.path}',
        'DELETE /v1/shops/3/customers/7',
      );
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await setup.container
        .read(customerCommandsProvider)
        .deleteCustomer(_shop, 7);
    await _settle(setup);

    expect(setup.calls, [
      'DELETE /v1/shops/3/customers/7',
      'GET /v1/shops/3/customers',
    ]);
  });

  test('실패한 쓰기는 아무것도 다시 부르지 않고 오류를 그대로 던진다', () async {
    final setup = await _watchingEverything((options, body) {
      return const FakeResponse(
        statusCode: 409,
        data: {'code': 'LAST_PET', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);

    await expectLater(
      setup.container.read(customerCommandsProvider).deletePet(_shop, 11),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'LAST_PET')),
    );
    await _settle(setup);

    expect(setup.calls, ['DELETE /v1/shops/3/pets/11']);
  });

  test('쓰기가 NOT_A_MEMBER 면 내 정보를 다시 불러온다(C5)', () async {
    final setup = await _watchingEverything((options, body) {
      return const FakeResponse(
        statusCode: 403,
        data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await expectLater(
      setup.container.read(customerCommandsProvider).markPassedAway(_shop, 11),
      throwsA(isA<ApiException>()),
    );
    expect(setup.gateway.refreshMeCallCount, 1);
  });

  test('번호 조회 — 없으면 null', () async {
    final setup = CustomerTestSetup((options, body) {
      return const FakeResponse(
        statusCode: 404,
        data: {'code': 'CUSTOMER_NOT_FOUND', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);

    expect(
      await setup.container
          .read(customerCommandsProvider)
          .lookup(_shop, '01012345678'),
      isNull,
    );
  });
}
```

`app/test/features/customer/state/customer_view_mode_test.dart` (새 파일):

```dart
import 'package:chagocnote/features/customer/state/customer_view_mode.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

void main() {
  test('기본은 목록이고, 고른 것을 기기에 기억한다', () async {
    final setup = CustomerTestSetup(
      (options, body) => const FakeResponse(statusCode: 500),
    );
    addTearDown(setup.container.dispose);

    expect(
      await setup.container.read(customerViewModeProvider.future),
      CustomerViewMode.list,
    );
    await setup.container
        .read(customerViewModeProvider.notifier)
        .select(CustomerViewMode.grid);

    expect(
      setup.container.read(customerViewModeProvider).value,
      CustomerViewMode.grid,
    );
    expect(await setup.prefs.readCustomerViewMode(), 'grid');
  });

  test('기억한 것이 격자면 격자로 시작한다', () async {
    final setup = CustomerTestSetup(
      (options, body) => const FakeResponse(statusCode: 500),
    );
    addTearDown(setup.container.dispose);
    await setup.prefs.writeCustomerViewMode('grid');

    expect(
      await setup.container.read(customerViewModeProvider.future),
      CustomerViewMode.grid,
    );
  });
}
```

`app/test/features/customer/state/search_debouncer_test.dart` (새 파일):

```dart
import 'package:chagocnote/features/customer/state/search_debouncer.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

TextEditingValue _typed(String text) => TextEditingValue(
  text: text,
  selection: TextSelection.collapsed(offset: text.length),
);

/// 마지막 글자가 아직 조합 중인 입력(한글 입력기가 주는 모양).
TextEditingValue _composing(String text) => TextEditingValue(
  text: text,
  selection: TextSelection.collapsed(offset: text.length),
  composing: TextRange(start: text.length - 1, end: text.length),
);

void main() {
  // testWidgets 는 가짜 시계로 돈다 — pump(시간)으로 타이머를 앞당긴다.
  testWidgets('조합이 끝난 뒤 0.3초 쉬면 한 번 보낸다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_composing('ㅋ'));
    debouncer.onChanged(_composing('코'));
    debouncer.onChanged(_composing('콩'));
    await tester.pump(const Duration(seconds: 1));
    expect(sent, isEmpty, reason: '조합 중에는 보내지 않는다');

    debouncer.onChanged(_typed('콩'));
    await tester.pump(const Duration(milliseconds: 299));
    expect(sent, isEmpty);
    await tester.pump(const Duration(milliseconds: 1));
    expect(sent, ['콩']);
  });

  testWidgets('0.3초 안에 이어 치면 마지막 것 하나만 보낸다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_typed('5'));
    await tester.pump(const Duration(milliseconds: 200));
    debouncer.onChanged(_typed('56'));
    await tester.pump(const Duration(milliseconds: 200));
    debouncer.onChanged(_typed('567'));
    await tester.pump(const Duration(milliseconds: 300));

    expect(sent, ['567']);
  });

  testWidgets('다시 조합을 시작하면 기다리던 요청을 취소한다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_typed('콩'));
    await tester.pump(const Duration(milliseconds: 200));
    debouncer.onChanged(_composing('콩ㅇ'));
    await tester.pump(const Duration(seconds: 1));

    expect(sent, isEmpty);
  });

  testWidgets('앞뒤 공백을 없앤 검색어가 마지막으로 보낸 것과 같으면 보내지 않는다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_typed('콩'));
    await tester.pump(const Duration(milliseconds: 300));
    debouncer.onChanged(_typed('콩 '));
    await tester.pump(const Duration(milliseconds: 300));
    debouncer.onChanged(_typed(''));
    await tester.pump(const Duration(milliseconds: 300));

    expect(sent, ['콩', '']);
  });

  testWidgets('dispose 하면 기다리던 요청을 보내지 않는다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);

    debouncer.onChanged(_typed('콩'));
    debouncer.dispose();
    await tester.pump(const Duration(seconds: 1));

    expect(sent, isEmpty);
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/core/storage/stores_test.dart test/features/customer/state/customer_commands_test.dart test/features/customer/state/customer_view_mode_test.dart test/features/customer/state/search_debouncer_test.dart`

Expected: 컴파일 오류 — `customer_commands.dart`·`customer_view_mode.dart`·`search_debouncer.dart`와 `PrefsStore`의 새 메서드가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/storage/prefs_store.dart` (수정):

```diff
@@ -1,11 +1,17 @@
 import 'package:flutter_secure_storage/flutter_secure_storage.dart';
 
-/// 기기에 남기는 작은 설정. 지금은 "마지막으로 고른 매장" 하나다.
+/// 기기에 남기는 작은 설정. "마지막으로 고른 매장"과 "고객 목록 보기 방식"이다.
 ///
 /// 저장소 패키지를 늘리지 않으려고 보안 저장소를 같이 쓴다.
 abstract class PrefsStore {
   Future<int?> readLastShopId();
   Future<void> writeLastShopId(int shopId);
+
+  /// 고객 목록 보기 방식('list' | 'grid'). 기기 설정이라 [clear]가 지우지 않는다.
+  Future<String?> readCustomerViewMode();
+  Future<void> writeCustomerViewMode(String mode);
+
+  /// 마지막으로 고른 매장을 지운다(로그아웃·탈퇴).
   Future<void> clear();
 }
 
@@ -14,6 +20,7 @@ class SecurePrefsStore implements PrefsStore {
       : _storage = storage ?? const FlutterSecureStorage();
 
   static const _lastShopKey = 'last_shop_id';
+  static const _customerViewModeKey = 'customer_view_mode';
   final FlutterSecureStorage _storage;
 
   @override
@@ -22,12 +29,20 @@ class SecurePrefsStore implements PrefsStore {
   @override
   Future<void> writeLastShopId(int shopId) => _storage.write(key: _lastShopKey, value: '$shopId');
 
+  @override
+  Future<String?> readCustomerViewMode() => _storage.read(key: _customerViewModeKey);
+
+  @override
+  Future<void> writeCustomerViewMode(String mode) =>
+      _storage.write(key: _customerViewModeKey, value: mode);
+
   @override
   Future<void> clear() => _storage.delete(key: _lastShopKey);
 }
 
 class MemoryPrefsStore implements PrefsStore {
   int? _lastShopId;
+  String? _customerViewMode;
 
   @override
   Future<int?> readLastShopId() async => _lastShopId;
@@ -35,6 +50,12 @@ class MemoryPrefsStore implements PrefsStore {
   @override
   Future<void> writeLastShopId(int shopId) async => _lastShopId = shopId;
 
+  @override
+  Future<String?> readCustomerViewMode() async => _customerViewMode;
+
+  @override
+  Future<void> writeCustomerViewMode(String mode) async => _customerViewMode = mode;
+
   @override
   Future<void> clear() async => _lastShopId = null;
 }
```

`app/lib/features/customer/state/customer_commands.dart` (새 파일):

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shop/state/shop_errors.dart';
import '../api/customer_api.dart';
import '../api/customer_models.dart';
import 'customer_list_controller.dart';
import 'customer_providers.dart';

/// 고객·반려동물 쓰기와 번호 조회. 모든 호출은 매장 범위 공통 처리
/// (`NOT_A_MEMBER` → 내 정보 재조회)를 거친다.
///
/// 쓰기가 끝나면 보고 있는 목록과 상세를 다시 불러오게 한다. 지운 대상의
/// 상세는 다시 부르지 않는다 — 부르면 404 가 화면에 잠깐 보인다.
class CustomerCommands {
  CustomerCommands(this._ref);

  final Ref _ref;

  CustomerApi get _api => _ref.read(customerApiProvider);

  Future<CustomerLookup?> lookup(int shopId, String phoneDigits) =>
      runShopScoped(_ref, () => _api.lookup(shopId, phoneDigits));

  Future<CustomerDetail> register(
    int shopId, {
    required CustomerFields customer,
    required PetFields pet,
  }) => _write(() => _api.register(shopId, customer: customer, pet: pet));

  Future<CustomerDetail> updateCustomer(
    int shopId,
    int customerId,
    CustomerFields fields,
  ) => _write(() => _api.updateCustomer(shopId, customerId, fields));

  Future<PetDetail> addPet(int shopId, int customerId, PetFields fields) =>
      _write(() => _api.addPet(shopId, customerId, fields));

  Future<PetDetail> updatePet(int shopId, int petId, PetFields fields) =>
      _write(() => _api.updatePet(shopId, petId, fields));

  Future<PetDetail> markPassedAway(int shopId, int petId) =>
      _write(() => _api.markPassedAway(shopId, petId));

  Future<PetDetail> unmarkPassedAway(int shopId, int petId) =>
      _write(() => _api.unmarkPassedAway(shopId, petId));

  /// 반려동물 삭제. 지운 아이의 상세는 다시 부르지 않고, 보호자 상세는 다시 부른다.
  Future<void> deletePet(int shopId, int petId) =>
      _write(() => _api.deletePet(shopId, petId), refreshPets: false);

  /// 고객 익명화 삭제. 그 고객의 상세는 모두 사라지므로 목록만 다시 부른다.
  Future<void> deleteCustomer(int shopId, int customerId) => _write(
    () => _api.deleteCustomer(shopId, customerId),
    refreshPets: false,
    refreshCustomers: false,
  );

  Future<T> _write<T>(
    Future<T> Function() action, {
    bool refreshPets = true,
    bool refreshCustomers = true,
  }) async {
    final result = await runShopScoped(_ref, action);
    _ref.invalidate(customerListControllerProvider);
    if (refreshPets) _ref.invalidate(petDetailProvider);
    if (refreshCustomers) _ref.invalidate(customerDetailProvider);
    return result;
  }
}

final customerCommandsProvider = Provider<CustomerCommands>(
  (ref) => CustomerCommands(ref),
);
```

`app/lib/features/customer/state/customer_view_mode.dart` (새 파일):

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';

enum CustomerViewMode { list, grid }

/// 고객 목록의 보기 방식. 기본은 목록이고, 마지막으로 고른 것을 기기에
/// 기억한다(설계 2절).
class CustomerViewModeController extends AsyncNotifier<CustomerViewMode> {
  @override
  Future<CustomerViewMode> build() async {
    final saved = await ref.read(prefsStoreProvider).readCustomerViewMode();
    return saved == CustomerViewMode.grid.name
        ? CustomerViewMode.grid
        : CustomerViewMode.list;
  }

  Future<void> select(CustomerViewMode mode) async {
    state = AsyncData(mode);
    await ref.read(prefsStoreProvider).writeCustomerViewMode(mode.name);
  }
}

final customerViewModeProvider =
    AsyncNotifierProvider<CustomerViewModeController, CustomerViewMode>(
      CustomerViewModeController.new,
    );
```

`app/lib/features/customer/state/search_debouncer.dart` (새 파일):

```dart
import 'dart:async';

import 'package:flutter/services.dart';

/// 검색창 입력을 받아, 한글 조합이 끝난 뒤 [delay] 동안 입력이 없으면
/// [onSearch]를 부른다(설계 8.2).
///
/// - 조합 중(`composing` 구간이 있음)에는 기다린다 — 'ㅋ'·'코'·'콩' 을 하나씩
///   보내지 않는다.
/// - 앞뒤 공백을 없앤 검색어가 마지막으로 보낸 것과 같으면 보내지 않는다
///   (커서만 옮기거나 공백만 친 경우).
class SearchDebouncer {
  SearchDebouncer({
    required this.onSearch,
    this.delay = const Duration(milliseconds: 300),
  });

  final void Function(String query) onSearch;
  final Duration delay;

  Timer? _timer;
  String _sent = '';

  void onChanged(TextEditingValue value) {
    _timer?.cancel();
    final composing = value.composing;
    if (composing.isValid && !composing.isCollapsed) return;
    final query = value.text.trim();
    _timer = Timer(delay, () {
      if (query == _sent) return;
      _sent = query;
      onSearch(query);
    });
  }

  void dispose() => _timer?.cancel();
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/core/storage/stores_test.dart test/features/customer/state/customer_commands_test.dart test/features/customer/state/customer_view_mode_test.dart test/features/customer/state/search_debouncer_test.dart` → Expected: `+16: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+284: All tests passed!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `customer_commands.dart`의 `deletePet`에서 `, refreshPets: false`를 지운다 → `반려동물을 지우면 그 아이의 상세는 다시 부르지 않는다` 실패
- `deleteCustomer`에서 `refreshCustomers: false,` 줄을 지운다 → `고객을 지우면 목록만 다시 부른다` 실패
- `search_debouncer.dart`의 `if (composing.isValid && !composing.isCollapsed) return;`을 지운다 → `조합이 끝난 뒤 0.3초 쉬면 한 번 보낸다` 실패

- [ ] **Step 6: 커밋한다**

```bash
git add app/lib/core/storage/prefs_store.dart app/lib/features/customer/state/customer_commands.dart app/lib/features/customer/state/customer_view_mode.dart app/lib/features/customer/state/search_debouncer.dart app/test/core/storage/stores_test.dart app/test/features/customer/state/customer_commands_test.dart app/test/features/customer/state/customer_view_mode_test.dart app/test/features/customer/state/search_debouncer_test.dart
git commit -m "feat(app): 고객 쓰기 명령, 목록 보기 방식 기억, 검색 입력 지연

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: 반려동물 상세 — 탭 세 개, 형제 이동, 무지개다리, 삭제

**Files:**
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/lib/core/router/screen_keys.dart`
- Create: `app/lib/features/customer/screens/customer_labels.dart`
- Create: `app/lib/features/customer/screens/pet_detail_screen.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/test/design/glass_boundary_test.dart`
- Create: `app/test/features/customer/screens/pet_detail_screen_test.dart`
- Create (골든, 명령으로 만든다): `app/test/features/customer/screens/goldens/pet_detail.png`

**Interfaces:**
- Consumes: `petDetailProvider`·`customerDetailProvider`(Task 4), `customerCommandsProvider`(Task 5), `formatPhone`·`formatWeight`(Task 3), `AppChip`·`AppSegment`·`AppSheet`·`AppPhotoTile`·`AppCard`·`AppButton`·`AppBackButton`·`Pressable`(기존)
- Produces: 라우트 `/pets/:petId` → `PetDetailScreen(petId)`(`ScreenKeys.petDetail`). `_isShopScoped(location)`: `/customers/…`·`/pets/…`도 매장이 선택되어 있어야 열린다. `lib/features/customer/screens/customer_labels.dart`: `petSummaryLine(Pet) → '강아지 · 말티즈 · 여아(중성화) · 5살 · 3.2kg'`, `formatDate(DateTime) → '2021.03.04'`(UTC 시각은 기기 시각으로). `AppStrings`의 상세 문구(`edit`·`delete`·`more`·`petTab*`·`passedAwayBadge`·`markPassedAway`·…·`conditionCount(int)`·`birthYearText(int)`).

**알아 둘 것:**
- 머리에 [수정] 버튼과 더 보기(⋯) — 더 보기 시트에 무지개다리 표시/되돌리기와 반려동물 삭제. 무지개다리 표시·삭제는 확인 시트를 거치고, 되돌리기는 바로 보낸다.
- "보호자" 탭은 고객 상세(`GET /customers/{id}`)를 따로 불러 전체 번호·보조 연락처·수신 동의·메모를 보인다(설계 8.2 — 전체 번호는 상세에서만). 탭을 열 때만 부른다.
- 형제로 옮길 때는 `pushReplacement` — 뒤로 가면 목록(홈)이다.
- [수정]·[보호자 수정]·[반려동물 추가]가 여는 `/pets/:id/edit`·`/customers/:id/edit`·`/customers/:id/pets/new`는 Task 8·9 가 만든다. 이 작업의 테스트는 그 버튼을 누르지 않는다.
- 쓰기가 도는 동안(`_busy`) [수정]과 더 보기를 막는다(연타 방지).

**막는 위협:** C5, A3(연타), A4(삭제 뒤 404 없음 — Task 5 의 `refreshPets: false`를 화면에서 확인), LAST_PET 문구

- [ ] **Step 1: 테스트를 쓴다**

`app/test/design/glass_boundary_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -10,6 +10,7 @@ void main() {
       'lib/features/shop/screens/members_screen.dart',
       'lib/features/auth/screens/shop_select_screen.dart',
       'lib/features/account/screens/account_screen.dart',
+      'lib/features/customer/screens/pet_detail_screen.dart',
     ];
     final violations = [
       for (final path in scrollScreens)
```

`app/test/features/customer/screens/pet_detail_screen_test.dart` (새 파일):

```dart
import 'dart:async';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

/// 홈에서 반려동물 상세를 쌓아 연다(뒤로 가면 홈).
Future<void> _openPet(
  WidgetTester tester,
  CustomerTestSetup setup,
  int petId,
) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/pets/$petId');
  await tester.pumpAndSettle();
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Future<void> _chooseAction(WidgetTester tester, String label) async {
  await tester.tap(find.bySemanticsLabel(AppStrings.more));
  await tester.pumpAndSettle();
  await tester.tap(find.text(label));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('이름·질병 수·요약과 탭 세 개를 보이고, 보호자 탭은 전체 번호를 고객 상세에서 받는다', (
    tester,
  ) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'GET /v1/shops/3/customers/7':
          return FakeResponse(statusCode: 200, data: customerDetailJson());
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await _openPet(tester, setup, 11);

    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    expect(find.text('콩이'), findsOneWidget);
    expect(find.text(AppStrings.conditionCount(1)), findsOneWidget);
    expect(find.text('강아지 · 말티즈 · 여아(중성화) · 5살 · 3.2kg'), findsOneWidget);
    expect(find.text('2021.03.04'), findsOneWidget);
    expect(find.text('귀 만지면 싫어함'), findsOneWidget);
    expect(setup.calls, isNot(contains('GET /v1/shops/3/customers/7')));

    await tester.tap(find.text(AppStrings.petTabConditions));
    await tester.pumpAndSettle();
    expect(find.text('슬개골 탈구'), findsOneWidget);
    expect(find.text('2기'), findsOneWidget);

    await tester.tap(find.text(AppStrings.petTabOwner));
    await tester.pumpAndSettle();
    expect(find.text('010-1234-5678'), findsOneWidget);
    expect(
      find.text('${AppStrings.marketingAgreed} · 2026.09.20'),
      findsOneWidget,
    );
    expect(find.text('오후 방문 선호'), findsOneWidget);
  });

  testWidgets('질병 없음을 확인한 아이는 질병 탭에 그렇게 보인다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(
          pet: petJson(noKnownConditions: true, birthDate: null),
        ),
      );
    });
    addTearDown(setup.container.dispose);

    await _openPet(tester, setup, 11);
    expect(find.text(AppStrings.conditionCount(0)), findsNothing);
    expect(find.text(AppStrings.ageUnknown), findsOneWidget);

    await tester.tap(find.text(AppStrings.petTabConditions));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.noKnownConditionsConfirmed), findsOneWidget);
  });

  testWidgets('무지개다리는 확인을 거쳐 표시하고, 다시 불러온 상세에 표시가 보인다', (tester) async {
    var passed = false;
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(
                passedAwayAt: passed ? '2026-09-22T01:00:00Z' : null,
              ),
            ),
          );
        case 'POST /v1/shops/3/pets/11/passed-away':
          passed = true;
          return FakeResponse(statusCode: 200, data: petDetailJson());
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.markPassedAway);
    expect(find.text(AppStrings.markPassedAwayConfirm), findsOneWidget);
    await tester.tap(_button(AppStrings.markPassedAway));
    await tester.pumpAndSettle();

    expect(setup.calls, contains('POST /v1/shops/3/pets/11/passed-away'));
    expect(find.text(AppStrings.passedAwayBadge), findsOneWidget);
  });

  testWidgets('무지개다리 되돌리기는 확인 없이 바로 보낸다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(passedAwayAt: '2026-09-22T01:00:00Z'),
            ),
          );
        case 'DELETE /v1/shops/3/pets/11/passed-away':
          return FakeResponse(statusCode: 200, data: petDetailJson());
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.unmarkPassedAway);

    expect(setup.calls, contains('DELETE /v1/shops/3/pets/11/passed-away'));
  });

  testWidgets('삭제는 확인을 거쳐 보내고, 끝나면 앞 화면으로 돌아간다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'DELETE /v1/shops/3/pets/11':
          return const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.deletePet);
    await tester.tap(_button(AppStrings.delete));
    await tester.pumpAndSettle();

    expect(
      setup.calls.where((c) => c == 'DELETE /v1/shops/3/pets/11'),
      hasLength(1),
    );
    expect(find.byKey(ScreenKeys.petDetail), findsNothing);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    // 지운 아이의 상세를 다시 부르지 않는다(404 가 잠깐 보이지 않게).
    expect(
      setup.calls.where((c) => c == 'GET /v1/shops/3/pets/11'),
      hasLength(1),
    );
  });

  testWidgets('마지막 반려동물이면(LAST_PET) 문구를 보이고 화면에 남는다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'DELETE /v1/shops/3/pets/11':
          return const FakeResponse(
            statusCode: 409,
            data: {'code': 'LAST_PET', 'message': 'x'},
          );
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.deletePet);
    await tester.tap(_button(AppStrings.delete));
    await tester.pumpAndSettle();

    expect(find.textContaining('고객 삭제'), findsOneWidget);
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('쓰기가 도는 동안 수정·더 보기를 막는다(연타 방지)', (tester) async {
    final gate = Completer<FakeResponse>();
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(passedAwayAt: '2026-09-22T01:00:00Z'),
            ),
          );
        case 'DELETE /v1/shops/3/pets/11/passed-away':
          return gate.future;
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.unmarkPassedAway);
    await tester.tap(find.bySemanticsLabel(AppStrings.more));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.unmarkPassedAway),
      findsNothing,
      reason: '시트가 열리지 않는다',
    );
    expect(
      tester.widget<AppButton>(_button(AppStrings.edit)).onPressed,
      isNull,
    );
    gate.complete(FakeResponse(statusCode: 200, data: petDetailJson()));
    await tester.pumpAndSettle();
    expect(
      tester.widget<AppButton>(_button(AppStrings.edit)).onPressed,
      isNotNull,
    );
  });

  testWidgets('같은 보호자의 다른 아이로 옮기면 화면을 바꿔 끼워, 뒤로 가면 앞 화면이다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(siblings: [siblingJson(petId: 12, name: '두부')]),
          );
        case 'GET /v1/shops/3/pets/12':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(petId: 12, name: '두부', breed: '푸들'),
              siblings: [siblingJson(petId: 11, name: '콩이')],
            ),
          );
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    // 형제 줄은 목록 아래쪽에 있다 — 보일 때까지 내린다.
    await tester.scrollUntilVisible(find.text('두부'), 200);
    await tester.tap(find.text('두부'));
    await tester.pumpAndSettle();
    expect(find.textContaining('푸들'), findsOneWidget);

    await tester.tap(find.byType(AppBackButton));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('조회가 실패하면 뒤로 가기와 다시 시도가 보이고, 다시 시도하면 나온다', (tester) async {
    var calls = 0;
    final setup = CustomerTestSetup((options, body) {
      calls++;
      if (calls == 1) {
        throw DioException.connectionError(
          requestOptions: options,
          reason: '연결 실패',
        );
      }
      return FakeResponse(statusCode: 200, data: petDetailJson());
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    expect(find.byType(AppBackButton), findsOneWidget);
    expect(find.text('콩이'), findsNothing);

    await tester.tap(_button(AppStrings.retry));
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('NOT_A_MEMBER 면 내 정보를 다시 불러온다(C5)', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      return const FakeResponse(
        statusCode: 403,
        data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    expect(setup.gateway.refreshMeCallCount, 1);
  });

  testWidgets('반려동물 상세 골든 — 기본 탭', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final setup = CustomerTestSetup((options, body) {
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(siblings: [siblingJson(petId: 12, name: '두부')]),
      );
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await expectLater(
      find.byKey(ScreenKeys.petDetail),
      matchesGoldenFile('goldens/pet_detail.png'),
    );
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/pet_detail_screen_test.dart`

Expected: 컴파일 오류 — `pet_detail_screen.dart`와 `ScreenKeys.petDetail`이 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/router/app_router.dart` (수정):

```diff
@@ -10,6 +10,7 @@ import '../../features/auth/screens/shop_select_screen.dart';
 import '../../features/auth/screens/splash_screen.dart';
 import '../../features/auth/state/session.dart';
 import '../../features/auth/state/session_controller.dart';
+import '../../features/customer/screens/pet_detail_screen.dart';
 import '../../features/home/screens/home_shell.dart';
 import '../../features/shop/screens/members_screen.dart';
 import '../../features/shop/screens/settings_screen.dart';
@@ -24,6 +25,12 @@ class _SessionRefreshListenable extends ChangeNotifier {
 /// 매장이 선택되어 있어야만 열리는 경로.
 const _shopScopedSettings = {'/settings', '/settings/members', '/settings/shop'};
 
+/// 고객·반려동물 화면도 매장이 선택되어 있어야 열린다(경로에 ID 가 들어간다).
+bool _isShopScoped(String location) =>
+    _shopScopedSettings.contains(location) ||
+    location.startsWith('/customers/') ||
+    location.startsWith('/pets/');
+
 /// 매장이 없어도(0-shop 사용자도) 열려 있어야 하는 계정 관련 경로 — 로그아웃,
 /// 로그인 수단 해제, 탈퇴는 매장 유무와 무관하게 가능해야 한다.
 const _accountExemptRoutes = {'/settings/account', '/settings/account/withdraw'};
@@ -94,6 +101,12 @@ final routerProvider = Provider<GoRouter>((ref) {
         path: '/settings/account/withdraw',
         builder: (context, state) => const WithdrawScreen(),
       ),
+      GoRoute(
+        path: '/pets/:petId',
+        builder: (context, state) => PetDetailScreen(
+          petId: int.parse(state.pathParameters['petId']!),
+        ),
+      ),
     ],
   );
 
@@ -116,7 +129,7 @@ String? _redirectSignedIn({
     return location == '/shops/select' ? null : '/shops/select';
   }
 
-  if (_shopScopedSettings.contains(location) && selectedShopId == null) {
+  if (_isShopScoped(location) && selectedShopId == null) {
     return '/home';
   }
```

`app/lib/core/router/screen_keys.dart` (수정):

```diff
@@ -13,4 +13,5 @@ class ScreenKeys {
   static const settingsShop = Key('screen_settings_shop');
   static const settingsAccount = Key('screen_settings_account');
   static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
+  static const petDetail = Key('screen_pet_detail');
 }
```

`app/lib/features/customer/screens/customer_labels.dart` (새 파일):

```dart
import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';

/// 반려동물 한 줄 요약 — "강아지 · 말티즈 · 여아(중성화) · 5살 · 3.2kg".
String petSummaryLine(Pet pet) {
  final sex = pet.neutered
      ? '${AppStrings.sexLabel(pet.sex)}(${AppStrings.neutered})'
      : AppStrings.sexLabel(pet.sex);
  return [
    AppStrings.speciesLabel(pet.species),
    pet.breed,
    sex,
    pet.ageLabel,
    formatWeight(pet.weightKg),
  ].join(' · ');
}

/// `2021.03.04`. 날짜만 있는 값(생일)은 그대로, 시각이 있는 값은 기기 시각으로 바꿔 찍는다.
String formatDate(DateTime date) {
  final d = date.isUtc ? date.toLocal() : date;
  return '${d.year}.${d.month.toString().padLeft(2, '0')}.${d.day.toString().padLeft(2, '0')}';
}
```

`app/lib/features/customer/screens/pet_detail_screen.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_segment.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_input.dart';
import '../state/customer_providers.dart';
import 'customer_labels.dart';

/// 반려동물 한 마리 화면 — 큰 사진 자리, 이름·요약, 탭 [기본 / 질병 / 보호자],
/// 같은 보호자의 다른 아이, 수정·무지개다리·삭제(설계 8.1).
class PetDetailScreen extends ConsumerStatefulWidget {
  const PetDetailScreen({super.key, required this.petId});

  final int petId;

  @override
  ConsumerState<PetDetailScreen> createState() => _PetDetailScreenState();
}

class _PetDetailScreenState extends ConsumerState<PetDetailScreen> {
  int _tab = 0;
  bool _busy = false;
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  Future<void> _openActions(PetDetail detail) async {
    final action = await AppSheet.show<String>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _SheetAction(
            label: detail.pet.passedAway
                ? AppStrings.unmarkPassedAway
                : AppStrings.markPassedAway,
            onTap: () => Navigator.of(context).pop('passed'),
          ),
          _SheetAction(
            label: AppStrings.deletePet,
            onTap: () => Navigator.of(context).pop('delete'),
          ),
        ],
      ),
    );
    if (action == null || !mounted) return;
    if (action == 'passed') {
      await _togglePassedAway(detail.pet);
    } else {
      await _delete();
    }
  }

  Future<void> _togglePassedAway(Pet pet) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final commands = ref.read(customerCommandsProvider);
    if (pet.passedAway) {
      await _run(() => commands.unmarkPassedAway(shopId, pet.petId));
      return;
    }
    final confirmed = await _confirm(
      AppStrings.markPassedAwayConfirm,
      AppStrings.markPassedAway,
    );
    if (confirmed != true || !mounted) return;
    await _run(() => commands.markPassedAway(shopId, pet.petId));
  }

  Future<void> _delete() async {
    final shopId = _shopId;
    if (shopId == null) return;
    final confirmed = await _confirm(
      AppStrings.deletePetConfirm,
      AppStrings.delete,
    );
    if (confirmed != true || !mounted) return;
    final deleted = await _run(
      () => ref.read(customerCommandsProvider).deletePet(shopId, widget.petId),
    );
    if (deleted && mounted) {
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/home');
      }
    }
  }

  Future<bool?> _confirm(String message, String confirmLabel) {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(message, style: AppTypography.body, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: confirmLabel,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
  }

  /// 쓰기 하나를 돌린다. 도는 동안 다른 쓰기를 막고(연타 방지), 실패하면
  /// 문구를 보인다. 성공하면 true.
  Future<bool> _run(Future<void> Function() action) async {
    if (_busy) return false;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action();
      if (mounted) setState(() => _busy = false);
      return true;
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _errorText = messageFor(e);
        });
      }
      return false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final detail = shopId == null
        ? const AsyncValue<PetDetail>.loading()
        : ref.watch(petDetailProvider((shopId: shopId, petId: widget.petId)));
    final data = detail.value;

    return Scaffold(
      key: ScreenKeys.petDetail,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 머리는 로딩·오류 상태에서도 보인다 — 오류에 갇혀도 뒤로 갈 수 있다.
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.sm,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const Spacer(),
                    if (data != null) ...[
                      AppButton(
                        label: AppStrings.edit,
                        onPressed: _busy
                            ? null
                            : () => context.push('/pets/${widget.petId}/edit'),
                      ),
                      Pressable(
                        semanticLabel: AppStrings.more,
                        onTap: _busy ? null : () => _openActions(data),
                        child: const Icon(Icons.more_horiz),
                      ),
                    ],
                  ],
                ),
              ),
              if (_errorText != null)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                  ),
                  child: Text(_errorText!, style: AppTypography.caption),
                ),
              Expanded(
                child: detail.when(
                  data: (detail) => _DetailBody(
                    detail: detail,
                    tab: _tab,
                    onTab: (i) => setState(() => _tab = i),
                  ),
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(messageFor(error), style: AppTypography.body),
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: AppStrings.retry,
                          onPressed: () => ref.invalidate(
                            petDetailProvider((
                              shopId: shopId!,
                              petId: widget.petId,
                            )),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({
    required this.detail,
    required this.tab,
    required this.onTab,
  });

  final PetDetail detail;
  final int tab;
  final ValueChanged<int> onTab;

  @override
  Widget build(BuildContext context) {
    final pet = detail.pet;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        // 사진은 ④에서 붙인다 — 지금은 회색 자리.
        const Center(child: AppPhotoTile(image: null, size: 160)),
        const SizedBox(height: AppSpacing.lg),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.xs,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(pet.name, style: AppTypography.titleKo),
            if (pet.hasConditions)
              AppChip(label: AppStrings.conditionCount(pet.conditions.length)),
            if (pet.passedAway)
              const AppChip(label: AppStrings.passedAwayBadge),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(petSummaryLine(pet), style: AppTypography.caption),
        const SizedBox(height: AppSpacing.lg),
        AppSegment(
          labels: const [
            AppStrings.petTabBasic,
            AppStrings.petTabConditions,
            AppStrings.petTabOwner,
          ],
          currentIndex: tab,
          onChanged: onTab,
        ),
        const SizedBox(height: AppSpacing.md),
        switch (tab) {
          0 => _BasicTab(pet: pet),
          1 => _ConditionsTab(pet: pet),
          _ => _OwnerTab(customerId: detail.owner.customerId),
        },
        if (detail.siblings.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          _Siblings(siblings: detail.siblings),
        ],
      ],
    );
  }
}

/// 이름표 + 값 한 줄 카드.
class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: SizedBox(
        width: double.infinity,
        child: AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: AppTypography.caption),
              const SizedBox(height: AppSpacing.xs),
              Text(value, style: AppTypography.body),
            ],
          ),
        ),
      ),
    );
  }
}

class _BasicTab extends StatelessWidget {
  const _BasicTab({required this.pet});

  final Pet pet;

  @override
  Widget build(BuildContext context) {
    final birth = pet.birthDate != null
        ? (AppStrings.birthDateLabel, formatDate(pet.birthDate!))
        : pet.birthYear != null
        ? (AppStrings.birthYearLabel, AppStrings.birthYearText(pet.birthYear!))
        : (AppStrings.birthDateLabel, AppStrings.ageUnknown);
    return Column(
      children: [
        _InfoCard(label: birth.$1, value: birth.$2),
        _InfoCard(
          label: AppStrings.weightLabel,
          value: formatWeight(pet.weightKg),
        ),
        _InfoCard(
          label: AppStrings.petMemoLabel,
          value: pet.memo ?? AppStrings.none,
        ),
      ],
    );
  }
}

class _ConditionsTab extends StatelessWidget {
  const _ConditionsTab({required this.pet});

  final Pet pet;

  @override
  Widget build(BuildContext context) {
    if (pet.conditions.isEmpty) {
      return const _InfoCard(
        label: AppStrings.petTabConditions,
        value: AppStrings.noKnownConditionsConfirmed,
      );
    }
    return Column(
      children: [
        for (final c in pet.conditions)
          _InfoCard(label: c.displayLabel, value: c.note ?? AppStrings.none),
      ],
    );
  }
}

/// 보호자 탭. 전체 번호는 고객 상세 조회에서만 받는다(설계 8.2).
class _OwnerTab extends ConsumerWidget {
  const _OwnerTab({required this.customerId});

  final int customerId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider).value;
    final shopId = session is SignedIn ? session.selectedShopId : null;
    if (shopId == null) return const SizedBox.shrink();
    final key = (shopId: shopId, customerId: customerId);
    return ref
        .watch(customerDetailProvider(key))
        .when(
          data: (detail) {
            final c = detail.customer;
            final consent = c.marketingConsent
                ? AppStrings.marketingAgreed
                : AppStrings.marketingDeclined;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _InfoCard(label: AppStrings.ownerNameLabel, value: c.name),
                _InfoCard(
                  label: AppStrings.ownerPhoneLabel,
                  value: formatPhone(c.phone),
                ),
                if (c.phoneAlt != null)
                  _InfoCard(
                    label: AppStrings.ownerPhoneAltLabel,
                    value: formatPhone(c.phoneAlt!),
                  ),
                _InfoCard(
                  label: AppStrings.marketingConsentLabel,
                  value:
                      '$consent · ${formatDate(c.marketingConsentChangedAt)}',
                ),
                _InfoCard(
                  label: AppStrings.customerMemoLabel,
                  value: c.memo ?? AppStrings.none,
                ),
                const SizedBox(height: AppSpacing.sm),
                Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
                  children: [
                    AppButton(
                      label: AppStrings.editOwner,
                      onPressed: () =>
                          context.push('/customers/$customerId/edit'),
                    ),
                    AppButton(
                      label: AppStrings.addPet,
                      onPressed: () =>
                          context.push('/customers/$customerId/pets/new'),
                    ),
                  ],
                ),
              ],
            );
          },
          loading: () => const Padding(
            padding: EdgeInsets.all(AppSpacing.lg),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (error, _) => Column(
            children: [
              Text(messageFor(error), style: AppTypography.body),
              const SizedBox(height: AppSpacing.sm),
              AppButton(
                label: AppStrings.retry,
                onPressed: () => ref.invalidate(customerDetailProvider(key)),
              ),
            ],
          ),
        );
  }
}

class _Siblings extends StatelessWidget {
  const _Siblings({required this.siblings});

  final List<Sibling> siblings;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(AppStrings.siblingsLabel, style: AppTypography.caption),
            for (final s in siblings)
              Pressable(
                semanticLabel: s.name,
                // 형제로 옮길 때는 화면을 바꿔 끼운다 — 뒤로 가면 목록으로 간다.
                onTap: () => context.pushReplacement('/pets/${s.petId}'),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                  child: Row(
                    children: [
                      Text(s.name, style: AppTypography.bodyStrong),
                      if (s.passedAway) ...[
                        const SizedBox(width: AppSpacing.sm),
                        const AppChip(label: AppStrings.passedAwayBadge),
                      ],
                      const Spacer(),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SheetAction extends StatelessWidget {
  const _SheetAction({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        alignment: Alignment.center,
        child: Text(label, style: AppTypography.body),
      ),
    );
  }
}
```

`app/lib/l10n/app_strings.dart` (수정):

```diff
@@ -114,6 +114,40 @@ class AppStrings {
         _ => sex,
       };
 
+  static const edit = '수정';
+  static const delete = '삭제';
+  static const more = '더 보기';
+  static const none = '없음';
+  static const petTabBasic = '기본';
+  static const petTabConditions = '질병';
+  static const petTabOwner = '보호자';
+  static const passedAwayBadge = '무지개다리';
+  static const markPassedAway = '무지개다리 표시';
+  static const unmarkPassedAway = '무지개다리 되돌리기';
+  static const markPassedAwayConfirm = '무지개다리를 건넜다고 표시할까요? 목록에서 숨겨지고 기록은 남습니다.';
+  static const deletePet = '반려동물 삭제';
+  static const deletePetConfirm = '잘못 등록한 반려동물을 삭제할까요? 질병 기록도 함께 지워지고 되돌릴 수 없습니다.';
+  static const birthDateLabel = '생일';
+  static const birthYearLabel = '태어난 해';
+  static const ageUnknown = '모름';
+  static const weightLabel = '몸무게';
+  static const petMemoLabel = '특이사항';
+  static const noKnownConditions = '질병 없음';
+  static const noKnownConditionsConfirmed = '질병 없음 — 확인함';
+  static const siblingsLabel = '같은 보호자의 아이';
+  static const ownerNameLabel = '이름';
+  static const ownerPhoneLabel = '전화번호';
+  static const ownerPhoneAltLabel = '보조 연락처';
+  static const marketingConsentLabel = '마케팅 수신';
+  static const marketingAgreed = '동의';
+  static const marketingDeclined = '거부';
+  static const customerMemoLabel = '메모';
+  static const editOwner = '보호자 수정';
+  static const addPet = '반려동물 추가';
+
+  static String conditionCount(int count) => '질병 $count';
+  static String birthYearText(int year) => '$year년생';
+
   /// 로그인 수단 제공자 코드를 화면에 보여줄 라벨로 바꾼다. 계정 화면과
   /// 재인증 시트(Task 16)가 함께 쓴다.
   static String providerLabel(String provider) => switch (provider) {
```

- [ ] **Step 4: 골든을 만들고 눈으로 확인한다**

Run: `flutter test --update-goldens test/features/customer/screens/pet_detail_screen_test.dart`

만들어지는 파일: `app/test/features/customer/screens/goldens/pet_detail.png`

Read 도구로 이미지를 열어 확인한다: `pet_detail.png`(390×844) — 위에 뒤로 가기·[수정]·⋯, 가운데 회색 사진 자리, '콩이'와 '질병 1' 칩, 요약 줄, 밑줄 탭 [기본 / 질병 / 보호자], 흰 카드 세 장(생일·몸무게·특이사항)과 '같은 보호자의 아이 — 두부 ›' 카드.

- [ ] **Step 5: 통과를 확인한다**

Run: `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/pet_detail_screen_test.dart` → Expected: `+12: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+295: All tests passed!`

- [ ] **Step 6: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `pet_detail_screen.dart`의 `onTap: _busy ? null : () => _openActions(data),`를 `onTap: () => _openActions(data),`로 바꾼다 → `쓰기가 도는 동안 수정·더 보기를 막는다(연타 방지)` 실패
- `app_router.dart`의 `_isShopScoped`에서 `location.startsWith('/pets/')` 조건을 지워도 이 작업의 테스트는 통과한다(매장이 하나면 늘 선택되어 있다) — 판별 대상이 아니다. 기존 `_shopScopedSettings` 규칙을 넓힌 것이다.

- [ ] **Step 7: 커밋한다**

```bash
git add app/lib/core/router/app_router.dart app/lib/core/router/screen_keys.dart app/lib/features/customer/screens/customer_labels.dart app/lib/features/customer/screens/pet_detail_screen.dart app/lib/l10n/app_strings.dart app/test/design/glass_boundary_test.dart app/test/features/customer/screens/goldens/pet_detail.png app/test/features/customer/screens/pet_detail_screen_test.dart
git commit -m "feat(app): 반려동물 상세 — 탭 세 개, 형제 이동, 무지개다리, 삭제

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: 고객 탭 — 가족 카드 목록·격자, 정렬, 검색, 다음 페이지

**Files:**
- Create: `app/lib/features/customer/screens/customer_list_tab.dart`
- Create: `app/lib/features/customer/screens/family_card_view.dart`
- Modify: `app/lib/features/home/screens/home_shell.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/test/core/router/app_router_test.dart`
- Modify: `app/test/design/glass_boundary_test.dart`
- Create: `app/test/features/customer/screens/customer_list_tab_test.dart`
- Modify: `app/test/features/home/screens/home_shell_test.dart`
- Create (골든, 명령으로 만든다): `app/test/features/customer/screens/goldens/customer_list_grid.png`
- Create (골든, 명령으로 만든다): `app/test/features/customer/screens/goldens/customer_list_list.png`

**Interfaces:**
- Consumes: `customerListControllerProvider`·`CustomerListQuery`(Task 4), `customerViewModeProvider`·`SearchDebouncer`(Task 5), `maskedTail`(Task 3), `AppIconToggle`·`AppChoiceChip`(Task 1), 라우트 `/pets/:petId`(Task 6)
- Produces: `CustomerListTab`(홈 셸의 1번 탭 본문), `FamilyCardView({card, mode})`(목록 줄 키 `pet_row_<id>`, 격자 타일 키 `pet_tile_<id>`). 홈 셸은 고객 탭에서 큰 날짜 머리를 그리지 않는다.

**알아 둘 것:**
- 고객 탭은 홈 셸의 큰 날짜 머리 대신 자기 머리("고객" + "N마리" + 보기 전환)를 쓴다(목업 A안 `.superpowers/brainstorm/94815-1790061769/content/customer-list-v2.html`). 그래서 **설정(톱니) 버튼은 캘린더·매출 탭 머리에만 있다.** 기존 `app_router_test`의 "홈 → 설정 → 뒤로" 테스트는 탭 상태를 매출 탭으로 확인하도록 고친다.
- **"무지개다리 포함" 칩을 더한다(설계 8.1 목록 조작에 없음).** 반려동물이 모두 무지개다리인 가족은 기본 목록·검색에서 빠진다 — 칩이 없으면 그 고객을 찾아 삭제(익명화)할 길이 없다. 서버의 `include_passed=true`를 켠다.
- 조건이 바뀌어 새로 불러오는 동안 앞선 결과를 그대로 보인다(`_lastShown`) — 깜빡이지 않는다.
- 끝에서 400px 안으로 내려오면 다음 페이지를 부른다. 다음 페이지가 실패했으면 스크롤로는 다시 부르지 않고 목록 끝의 [다시 시도]로만 — 오류 중에 스크롤마다 요청이 나가지 않게.
- 테스트의 `_settle`: dio 는 요청을 0초 타이머 뒤에 보낸다. 앞선 결과를 보여 주느라 그릴 프레임이 없으면 `pumpAndSettle`만으로는 시계가 가지 않아 요청이 어댑터에 닿지 않는다 — `pump(1ms)` 뒤 `pumpAndSettle`.
- 목록 아래 여백 120 은 떠 있는 탭바와 + 버튼 몫이다.

**막는 위협:** C7(목록은 가린 번호 뒷자리만), C12(검색 — 늦게 온 옛 결과 무시), C5, A6(다음 페이지 오류에서 스크롤 재요청 없음)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/core/router/app_router_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -264,7 +264,8 @@ void main() {
       await tester.pumpAndSettle();
       expect(find.byKey(ScreenKeys.home), findsOneWidget);
 
-      await tester.tap(find.text(AppStrings.tabCustomers));
+      // 고객 탭은 머리에 설정 버튼이 없다(자기 머리를 쓴다) — 매출 탭으로 본다.
+      await tester.tap(find.text(AppStrings.tabSales));
       await tester.pumpAndSettle();
       expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
```

`app/test/design/glass_boundary_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -11,6 +11,8 @@ void main() {
       'lib/features/auth/screens/shop_select_screen.dart',
       'lib/features/account/screens/account_screen.dart',
       'lib/features/customer/screens/pet_detail_screen.dart',
+      'lib/features/customer/screens/customer_list_tab.dart',
+      'lib/features/customer/screens/family_card_view.dart',
     ];
     final violations = [
       for (final path in scrollScreens)
```

`app/test/features/customer/screens/customer_list_tab_test.dart` (새 파일):

```dart
import 'dart:async';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

/// 홈을 띄우고 고객 탭으로 옮긴다.
Future<void> _openTab(WidgetTester tester, CustomerTestSetup setup) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  await tester.tap(find.text(AppStrings.tabCustomers));
  await tester.pumpAndSettle();
}

/// 조건을 바꾼 뒤 새 요청이 어댑터에 닿을 때까지 돌린다. dio 는 요청을
/// 0초 타이머 뒤에 보내므로, 앞선 결과를 그대로 보여 주느라 그릴 프레임이
/// 없으면 `pumpAndSettle`만으로는 시계가 가지 않는다.
Future<void> _settle(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 1));
  await tester.pumpAndSettle();
}

List<Map<String, dynamic>> _listQueries(CustomerTestSetup setup) => [
  for (final r in setup.adapter.requests)
    if (r.path == '/v1/shops/3/customers') r.queryParameters,
];

final _twoFamilies = pageJson(
  items: [
    familyJson(
      customerId: 7,
      pets: [
        petSummaryJson(petId: 11, name: '콩이', hasConditions: true),
        petSummaryJson(petId: 12, name: '두부', breed: '푸들', ageLabel: '3살'),
      ],
    ),
    familyJson(
      customerId: 8,
      name: '박서준',
      phoneMasked: '010-98··-1122',
      pets: [
        petSummaryJson(petId: 13, name: '초코', breed: '비숑', ageLabel: '7살'),
      ],
    ),
  ],
);

void main() {
  testWidgets('가족 카드를 목록으로 보인다 — 보호자와 가린 뒷자리, 아이들, 질병 표시, 반려동물 수', (
    tester,
  ) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);

    await _openTab(tester, setup);

    expect(find.text(AppStrings.petCountText(3)), findsOneWidget);
    expect(find.text('김민지 · ··5678'), findsOneWidget);
    expect(find.text('박서준 · ··1122'), findsOneWidget);
    expect(find.byKey(const Key('pet_row_11')), findsOneWidget);
    expect(find.text('말티즈 · 5살'), findsOneWidget);
    expect(find.text('푸들 · 3살'), findsOneWidget);
    expect(find.text(AppStrings.conditionsBadge), findsOneWidget);
    expect(_listQueries(setup), [
      {'sort': 'recent', 'include_passed': false},
    ]);
  });

  testWidgets('격자로 바꾸면 타일로 보이고 기기에 기억한다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(find.bySemanticsLabel(AppStrings.viewAsGrid));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('pet_tile_11')), findsOneWidget);
    expect(find.byKey(const Key('pet_row_11')), findsNothing);
    expect(await setup.prefs.readCustomerViewMode(), 'grid');
  });

  testWidgets('기억한 보기가 격자면 격자로 시작한다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);
    await setup.prefs.writeCustomerViewMode('grid');

    await _openTab(tester, setup);

    expect(find.byKey(const Key('pet_tile_11')), findsOneWidget);
  });

  testWidgets('정렬과 무지개다리 포함을 바꾸면 그 조건으로 다시 부른다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(find.text(AppStrings.sortName));
    await _settle(tester);
    await tester.tap(find.bySemanticsLabel(AppStrings.includePassed));
    await _settle(tester);

    expect(_listQueries(setup), [
      {'sort': 'recent', 'include_passed': false},
      {'sort': 'name', 'include_passed': false},
      {'sort': 'name', 'include_passed': true},
    ]);
  });

  testWidgets('검색은 0.3초 쉰 뒤 보내고, 새 검색을 보내면 늦게 온 옛 결과는 버린다(C12)', (
    tester,
  ) async {
    final slow = Completer<FakeResponse>();
    final setup = CustomerTestSetup((options, body) {
      switch (options.queryParameters['q']) {
        case null:
          return FakeResponse(statusCode: 200, data: _twoFamilies);
        case '콩':
          return slow.future;
        case '초코':
          return FakeResponse(
            statusCode: 200,
            data: pageJson(
              items: [_twoFamilies['items'][1] as Map<String, dynamic>],
            ),
          );
      }
      fail('예상하지 못한 검색어: ${options.queryParameters['q']}');
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.enterText(find.byType(TextField), '콩');
    await tester.pump(const Duration(milliseconds: 299));
    expect(_listQueries(setup), hasLength(1));
    await tester.pump(const Duration(milliseconds: 1));
    await tester.pump(
      const Duration(milliseconds: 1),
    ); // 검색어가 바뀐 화면이 새 조건으로 부른다.
    expect(_listQueries(setup).last['q'], '콩');

    await tester.enterText(find.byType(TextField), '초코');
    await tester.pump(const Duration(milliseconds: 300));
    await _settle(tester);
    expect(find.text('박서준 · ··1122'), findsOneWidget);

    slow.complete(FakeResponse(statusCode: 200, data: _twoFamilies));
    await _settle(tester);

    expect(find.text('김민지 · ··5678'), findsNothing);
    expect(find.text('박서준 · ··1122'), findsOneWidget);
  });

  testWidgets('검색 결과가 없으면 그렇게 말하고, 목록이 비었으면 등록을 안내한다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) =>
          FakeResponse(statusCode: 200, data: pageJson(items: [])),
    );
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);
    expect(find.text(AppStrings.customersEmpty), findsOneWidget);

    await tester.enterText(find.byType(TextField), '없는이름');
    await tester.pump(const Duration(milliseconds: 300));
    await _settle(tester);

    expect(find.text(AppStrings.customersNoMatch), findsOneWidget);
  });

  testWidgets('아이를 누르면 반려동물 상세로 간다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      if (options.path == '/v1/shops/3/pets/12') {
        return FakeResponse(
          statusCode: 200,
          data: petDetailJson(pet: petJson(petId: 12, name: '두부')),
        );
      }
      return FakeResponse(statusCode: 200, data: _twoFamilies);
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(find.byKey(const Key('pet_row_12')));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('끝까지 내리면 다음 페이지를 붙이고, 실패하면 그 자리에서 다시 시도한다', (tester) async {
    var failNext = true;
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(
          statusCode: 200,
          data: pageJson(
            items: [
              for (var i = 1; i <= 12; i++)
                familyJson(customerId: i, name: '보호자$i'),
            ],
            nextCursor: 'c1',
          ),
        );
      }
      if (failNext) {
        failNext = false;
        return const FakeResponse(
          statusCode: 500,
          data: {'code': 'INTERNAL', 'message': 'x'},
        );
      }
      return FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 99, name: '마지막보호자')]),
      );
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.fling(find.byType(ListView), const Offset(0, -3000), 3000);
    await tester.pumpAndSettle();
    // 실패한 뒤에는 더 내려도 스크롤로 다시 부르지 않는다.
    await tester.fling(find.byType(ListView), const Offset(0, -3000), 3000);
    await tester.pumpAndSettle();
    expect(_listQueries(setup).where((q) => q['cursor'] == 'c1'), hasLength(1));
    final retry = find.byWidgetPredicate(
      (w) => w is AppButton && w.label == AppStrings.retry,
    );
    // 검색창도 Scrollable 이라 목록의 것을 집어 준다.
    final list = find.descendant(
      of: find.byType(ListView),
      matching: find.byType(Scrollable),
    );
    await tester.scrollUntilVisible(retry, 300, scrollable: list);
    await tester.tap(retry);
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('마지막보호자 · ··5678'),
      300,
      scrollable: list,
    );

    expect(find.text('마지막보호자 · ··5678'), findsOneWidget);
    expect(_listQueries(setup).where((q) => q['cursor'] == 'c1'), hasLength(2));
  });

  testWidgets('첫 조회가 실패하면 다시 시도할 수 있다', (tester) async {
    var calls = 0;
    final setup = CustomerTestSetup((options, body) {
      calls++;
      if (calls == 1) {
        return const FakeResponse(
          statusCode: 500,
          data: {'code': 'INTERNAL', 'message': 'x'},
        );
      }
      return FakeResponse(statusCode: 200, data: _twoFamilies);
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.retry,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('김민지 · ··5678'), findsOneWidget);
  });

  for (final grid in [false, true]) {
    testWidgets('고객 탭 골든 — ${grid ? '격자' : '목록'}', (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final setup = CustomerTestSetup(
        (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
      );
      addTearDown(setup.container.dispose);
      if (grid) await setup.prefs.writeCustomerViewMode('grid');

      await _openTab(tester, setup);

      await expectLater(
        find.byKey(ScreenKeys.home),
        matchesGoldenFile(
          'goldens/customer_list_${grid ? 'grid' : 'list'}.png',
        ),
      );
    });
  }
}
```

`app/test/features/home/screens/home_shell_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -4,11 +4,16 @@ import 'package:chagocnote/design/app_theme.dart';
 import 'package:chagocnote/design/bridge/glass_surface.dart';
 import 'package:chagocnote/features/auth/state/session.dart';
 import 'package:chagocnote/features/auth/state/session_controller.dart';
+import 'package:chagocnote/features/customer/screens/customer_list_tab.dart';
+import 'package:chagocnote/design/widgets/app_big_date.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
 
+import '../../../support/customer_fixtures.dart';
+import '../../../support/customer_test_app.dart';
+import '../../../support/fake_http_client_adapter.dart';
 import '../../../support/fake_session_gateway.dart';
 
 Me _meWithHissHaus() => const Me(
@@ -59,7 +64,11 @@ void main() {
   });
 
   testWidgets('탭을 바꾸면 본문이 바뀐다', (tester) async {
-    final container = _containerWith();
+    // 고객 탭은 목록을 부른다 — 가짜 어댑터로 빈 목록을 준다.
+    final setup = CustomerTestSetup(
+      (options, body) => FakeResponse(statusCode: 200, data: pageJson(items: [])),
+    );
+    final container = setup.container;
     addTearDown(container.dispose);
 
     await tester.pumpWidget(_appWith(container));
@@ -72,7 +81,10 @@ void main() {
     await tester.pumpAndSettle();
 
     expect(find.text(AppStrings.calendarEmptyTitle), findsNothing);
-    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
+    expect(find.byType(CustomerListTab), findsOneWidget);
+    expect(find.text(AppStrings.customersEmpty), findsOneWidget);
+    // 고객 탭은 자기 머리를 쓴다 — 큰 날짜 머리는 없다.
+    expect(find.byType(AppBigDate), findsNothing);
 
     await tester.tap(find.text(AppStrings.tabSales));
     await tester.pumpAndSettle();
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/core/router/app_router_test.dart test/design/glass_boundary_test.dart test/features/customer/screens/customer_list_tab_test.dart test/features/home/screens/home_shell_test.dart`

Expected: 컴파일 오류 — `customer_list_tab.dart`가 없다(`home_shell_test.dart`도 import 한다).

- [ ] **Step 3: 구현한다**

`app/lib/features/customer/screens/customer_list_tab.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/app_icon_toggle.dart';
import '../../../design/widgets/app_segment.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../state/customer_list_controller.dart';
import '../state/customer_view_mode.dart';
import '../state/search_debouncer.dart';
import 'family_card_view.dart';

/// 홈의 "고객" 탭 — 제목과 반려동물 수, 보기 전환, 정렬, 무지개다리 포함,
/// 검색창, 가족 카드 목록(아래로 내리면 다음 페이지).
class CustomerListTab extends ConsumerStatefulWidget {
  const CustomerListTab({super.key});

  @override
  ConsumerState<CustomerListTab> createState() => _CustomerListTabState();
}

class _CustomerListTabState extends ConsumerState<CustomerListTab> {
  static const _sorts = ['recent', 'name'];

  final _search = TextEditingController();
  final _scroll = ScrollController();
  late final SearchDebouncer _debouncer = SearchDebouncer(
    onSearch: (q) => setState(() => _q = q),
  );

  String _q = '';
  String _sort = 'recent';
  bool _includePassed = false;

  /// 조건이 바뀌어 새로 불러오는 동안 앞선 결과를 그대로 보인다(깜빡임 방지).
  CustomerListState? _lastShown;

  @override
  void initState() {
    super.initState();
    _search.addListener(() => _debouncer.onChanged(_search.value));
    _scroll.addListener(_maybeLoadMore);
  }

  @override
  void dispose() {
    _debouncer.dispose();
    _search.dispose();
    _scroll.dispose();
    super.dispose();
  }

  CustomerListQuery? get _query {
    final session = ref.read(sessionControllerProvider).value;
    final shopId = session is SignedIn ? session.selectedShopId : null;
    if (shopId == null) return null;
    return (shopId: shopId, q: _q, sort: _sort, includePassed: _includePassed);
  }

  /// 끝에서 400px 안으로 내려오면 다음 페이지를 부른다. 다음 페이지가 한 번
  /// 실패했으면 스크롤로는 다시 부르지 않는다 — 목록 끝의 "다시 시도"로만.
  void _maybeLoadMore() {
    final query = _query;
    if (query == null || !_scroll.hasClients) return;
    if (_scroll.position.extentAfter > 400) return;
    final provider = customerListControllerProvider(query);
    if (ref.read(provider).value?.loadMoreError != null) return;
    ref.read(provider.notifier).loadMore();
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(sessionControllerProvider);
    final query = _query;
    final mode =
        ref.watch(customerViewModeProvider).value ?? CustomerViewMode.list;
    final async = query == null
        ? const AsyncValue<CustomerListState>.loading()
        : ref.watch(customerListControllerProvider(query));
    final shown = async.value ?? (async.isLoading ? _lastShown : null);
    if (async.value != null) _lastShown = async.value;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            0,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text(AppStrings.customersTitle, style: AppTypography.titleKo),
              const SizedBox(width: AppSpacing.sm),
              if (shown != null)
                Text(
                  AppStrings.petCountText(shown.petCount),
                  style: AppTypography.caption,
                ),
              const Spacer(),
              AppIconToggle(
                icons: const [Icons.view_list, Icons.grid_view],
                labels: const [AppStrings.viewAsList, AppStrings.viewAsGrid],
                currentIndex: mode.index,
                onChanged: (i) => ref
                    .read(customerViewModeProvider.notifier)
                    .select(CustomerViewMode.values[i]),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: Row(
            children: [
              AppSegment(
                labels: const [AppStrings.sortRecent, AppStrings.sortName],
                currentIndex: _sorts.indexOf(_sort),
                onChanged: (i) => setState(() => _sort = _sorts[i]),
              ),
              const Spacer(),
              AppChoiceChip(
                label: AppStrings.includePassed,
                selected: _includePassed,
                onTap: () => setState(() => _includePassed = !_includePassed),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.xs,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: TextField(
            controller: _search,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: AppStrings.customerSearchHint,
              hintStyle: AppTypography.body.copyWith(
                color: AppColors.secondary,
              ),
              prefixIcon: const Icon(Icons.search, color: AppColors.secondary),
              filled: true,
              fillColor: AppColors.white,
              isDense: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: const BorderSide(color: AppColors.line),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: const BorderSide(color: AppColors.line),
              ),
            ),
          ),
        ),
        Expanded(
          child: shown != null
              ? _CardList(
                  state: shown,
                  mode: mode,
                  searching: _q.isNotEmpty,
                  scroll: _scroll,
                  onRetryMore: () => ref
                      .read(customerListControllerProvider(query!).notifier)
                      .loadMore(),
                )
              : async.hasError
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(messageFor(async.error!), style: AppTypography.body),
                      const SizedBox(height: AppSpacing.lg),
                      AppButton(
                        label: AppStrings.retry,
                        onPressed: () => ref.invalidate(
                          customerListControllerProvider(query!),
                        ),
                      ),
                    ],
                  ),
                )
              : const Center(child: CircularProgressIndicator()),
        ),
      ],
    );
  }
}

class _CardList extends StatelessWidget {
  const _CardList({
    required this.state,
    required this.mode,
    required this.searching,
    required this.scroll,
    required this.onRetryMore,
  });

  final CustomerListState state;
  final CustomerViewMode mode;
  final bool searching;
  final ScrollController scroll;
  final VoidCallback onRetryMore;

  @override
  Widget build(BuildContext context) {
    if (state.items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                searching
                    ? AppStrings.customersNoMatch
                    : AppStrings.customersEmpty,
                style: AppTypography.body,
              ),
              if (!searching) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  AppStrings.customersEmptyCaption,
                  style: AppTypography.caption,
                ),
              ],
            ],
          ),
        ),
      );
    }
    // 아래 여백은 떠 있는 탭바와 + 버튼 몫이다.
    return ListView.builder(
      controller: scroll,
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
      itemCount: state.items.length + 1,
      itemBuilder: (context, index) {
        if (index == state.items.length) {
          if (state.loadingMore) {
            return const Padding(
              padding: EdgeInsets.all(AppSpacing.lg),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          if (state.loadMoreError != null) {
            return Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                children: [
                  Text(
                    messageFor(state.loadMoreError!),
                    style: AppTypography.caption,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  AppButton(label: AppStrings.retry, onPressed: onRetryMore),
                ],
              ),
            );
          }
          return const SizedBox.shrink();
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: FamilyCardView(card: state.items[index], mode: mode),
        );
      },
    );
  }
}
```

`app/lib/features/customer/screens/family_card_view.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';
import '../state/customer_view_mode.dart';

/// 가족 카드 — 머리에 보호자 이름과 가린 번호 뒷자리, 안에 아이들을
/// 줄(목록) 또는 2열 타일(격자)로 보인다. 아이를 누르면 반려동물 상세로 간다.
class FamilyCardView extends StatelessWidget {
  const FamilyCardView({super.key, required this.card, required this.mode});

  final FamilyCard card;
  final CustomerViewMode mode;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        AppSpacing.sm,
        AppSpacing.md,
        AppSpacing.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${card.name} · ${maskedTail(card.phoneMasked)}',
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.xs),
          if (mode == CustomerViewMode.list)
            for (final pet in card.pets) _PetRow(pet: pet)
          else
            _PetGrid(pets: card.pets),
        ],
      ),
    );
  }
}

void _openPet(BuildContext context, PetSummary pet) =>
    context.push('/pets/${pet.petId}');

class _Badges extends StatelessWidget {
  const _Badges({required this.pet});

  final PetSummary pet;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.xs,
      children: [
        if (pet.hasConditions) const AppChip(label: AppStrings.conditionsBadge),
        if (pet.passedAway) const AppChip(label: AppStrings.passedAwayBadge),
      ],
    );
  }
}

class _PetRow extends StatelessWidget {
  const _PetRow({required this.pet});

  final PetSummary pet;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      key: Key('pet_row_${pet.petId}'),
      semanticLabel: pet.name,
      onTap: () => _openPet(context, pet),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        child: Row(
          children: [
            // 사진은 ④에서 붙인다 — 지금은 회색 자리.
            const AppPhotoTile(image: null, size: 40),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          pet.name,
                          style: AppTypography.bodyStrong,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      _Badges(pet: pet),
                    ],
                  ),
                  Text(
                    '${pet.breed} · ${pet.ageLabel}',
                    style: AppTypography.caption,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PetGrid extends StatelessWidget {
  const _PetGrid({required this.pets});

  final List<PetSummary> pets;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < pets.length; i += 2)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: _PetTile(pet: pets[i])),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: i + 1 < pets.length
                      ? _PetTile(pet: pets[i + 1])
                      : const SizedBox.shrink(),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _PetTile extends StatelessWidget {
  const _PetTile({required this.pet});

  final PetSummary pet;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      key: Key('pet_tile_${pet.petId}'),
      semanticLabel: pet.name,
      onTap: () => _openPet(context, pet),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 사진은 ④에서 붙인다 — 지금은 회색 자리.
          AspectRatio(
            aspectRatio: 1.3,
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.line,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Wrap(
            spacing: AppSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(pet.name, style: AppTypography.bodyStrong),
              _Badges(pet: pet),
            ],
          ),
          Text(
            '${pet.breed} · ${pet.ageLabel}',
            style: AppTypography.caption,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
```

`app/lib/features/home/screens/home_shell.dart` (수정):

```diff
@@ -14,6 +14,7 @@ import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/session.dart';
 import '../../auth/state/session_controller.dart';
+import '../../customer/screens/customer_list_tab.dart';
 import '../state/today_provider.dart';
 
 /// 홈 화면. 헤더(날짜 + 매장 이름 + 설정), 탭별 본문, 하단 유리 탭바로
@@ -26,6 +27,8 @@ class HomeShell extends ConsumerStatefulWidget {
 }
 
 class _HomeShellState extends ConsumerState<HomeShell> {
+  static const _customersTab = 1;
+
   int _tabIndex = 0;
 
   static const _items = [
@@ -80,34 +83,36 @@ class _HomeShellState extends ConsumerState<HomeShell> {
           bottom: false,
           child: Column(
             children: [
-              Padding(
-                padding: const EdgeInsets.fromLTRB(
-                  AppSpacing.lg,
-                  AppSpacing.md,
-                  AppSpacing.sm,
-                  AppSpacing.md,
-                ),
-                child: Row(
-                  crossAxisAlignment: CrossAxisAlignment.start,
-                  children: [
-                    Expanded(
-                      child: Column(
-                        crossAxisAlignment: CrossAxisAlignment.start,
-                        children: [
-                          AppBigDate(date: today),
-                          const SizedBox(height: AppSpacing.sm),
-                          Text(shopName, style: AppTypography.titleKo),
-                        ],
+              // 고객 탭은 자기 머리(제목·반려동물 수·보기 전환)를 쓴다(목업 A안).
+              if (_tabIndex != _customersTab)
+                Padding(
+                  padding: const EdgeInsets.fromLTRB(
+                    AppSpacing.lg,
+                    AppSpacing.md,
+                    AppSpacing.sm,
+                    AppSpacing.md,
+                  ),
+                  child: Row(
+                    crossAxisAlignment: CrossAxisAlignment.start,
+                    children: [
+                      Expanded(
+                        child: Column(
+                          crossAxisAlignment: CrossAxisAlignment.start,
+                          children: [
+                            AppBigDate(date: today),
+                            const SizedBox(height: AppSpacing.sm),
+                            Text(shopName, style: AppTypography.titleKo),
+                          ],
+                        ),
+                      ),
+                      Pressable(
+                        semanticLabel: AppStrings.settingsLabel,
+                        onTap: () => context.push('/settings'),
+                        child: const Icon(Icons.settings_outlined),
                       ),
-                    ),
-                    Pressable(
-                      semanticLabel: AppStrings.settingsLabel,
-                      onTap: () => context.push('/settings'),
-                      child: const Icon(Icons.settings_outlined),
-                    ),
-                  ],
+                    ],
+                  ),
                 ),
-              ),
               Expanded(child: _TabBody(index: _tabIndex)),
             ],
           ),
@@ -124,6 +129,7 @@ class _TabBody extends StatelessWidget {
 
   @override
   Widget build(BuildContext context) {
+    if (index == _HomeShellState._customersTab) return const CustomerListTab();
     return Center(
       child: index == 0
           ? const _EmptyState(
```

`app/lib/l10n/app_strings.dart` (수정):

```diff
@@ -148,6 +148,20 @@ class AppStrings {
   static String conditionCount(int count) => '질병 $count';
   static String birthYearText(int year) => '$year년생';
 
+  static const customersTitle = '고객';
+  static const viewAsList = '목록으로 보기';
+  static const viewAsGrid = '격자로 보기';
+  static const sortRecent = '최근순';
+  static const sortName = '가나다순';
+  static const includePassed = '무지개다리 포함';
+  static const customerSearchHint = '번호 뒷자리, 이름, 반려동물 (초성 가능)';
+  static const customersEmpty = '등록된 고객이 없어요';
+  static const customersEmptyCaption = '+ 버튼으로 첫 고객을 등록해 보세요.';
+  static const customersNoMatch = '찾는 고객이 없어요';
+  static const conditionsBadge = '질병';
+
+  static String petCountText(int count) => '$count마리';
+
   /// 로그인 수단 제공자 코드를 화면에 보여줄 라벨로 바꾼다. 계정 화면과
   /// 재인증 시트(Task 16)가 함께 쓴다.
   static String providerLabel(String provider) => switch (provider) {
```

- [ ] **Step 4: 골든을 만들고 눈으로 확인한다**

Run: `flutter test --update-goldens test/features/customer/screens/customer_list_tab_test.dart`

만들어지는 파일: `app/test/features/customer/screens/goldens/customer_list_grid.png`, `app/test/features/customer/screens/goldens/customer_list_list.png`

Read 도구로 이미지를 열어 확인한다: `customer_list_list.png` — 위에 '고객 3마리'와 오른쪽 아이콘 토글(목록 선택), [최근순 / 가나다순] 밑줄 탭과 '무지개다리 포함' 칩, 흰 검색창, 가족 카드 두 장('김민지 · ··5678' 안에 콩이(질병 칩)·두부 줄, '박서준 · ··1122' 안에 초코), 아래 + 버튼과 글래스 탭바(고객 선택). `customer_list_grid.png` — 같은 머리에 격자 선택, 카드 안에 회색 타일 2열.

- [ ] **Step 5: 통과를 확인한다**

Run: `flutter test test/core/router/app_router_test.dart test/design/glass_boundary_test.dart test/features/customer/screens/customer_list_tab_test.dart test/features/home/screens/home_shell_test.dart` → Expected: `+30: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+306: All tests passed!`

- [ ] **Step 6: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `customer_list_tab.dart`의 `if (ref.read(provider).value?.loadMoreError != null) return;`을 지운다 → `끝까지 내리면 다음 페이지를 붙이고, 실패하면 그 자리에서 다시 시도한다` 실패
- `home_shell.dart`의 `if (_tabIndex != _customersTab)`를 지운다 → `탭을 바꾸면 본문이 바뀐다`(`AppBigDate` 없음) 실패

- [ ] **Step 7: 커밋한다**

```bash
git add app/lib/features/customer/screens/customer_list_tab.dart app/lib/features/customer/screens/family_card_view.dart app/lib/features/home/screens/home_shell.dart app/lib/l10n/app_strings.dart app/test/core/router/app_router_test.dart app/test/design/glass_boundary_test.dart app/test/features/customer/screens/customer_list_tab_test.dart app/test/features/customer/screens/goldens/customer_list_grid.png app/test/features/customer/screens/goldens/customer_list_list.png app/test/features/home/screens/home_shell_test.dart
git commit -m "feat(app): 고객 탭 — 가족 카드 목록·격자, 정렬, 검색, 다음 페이지

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: 반려동물 폼 — 추가와 수정

**Files:**
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/lib/core/router/screen_keys.dart`
- Create: `app/lib/features/customer/screens/pet_form.dart`
- Create: `app/lib/features/customer/screens/pet_form_screen.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/test/design/glass_boundary_test.dart`
- Create: `app/test/features/customer/screens/pet_form_screen_test.dart`

**Interfaces:**
- Consumes: `conditionTypesProvider`·`petDetailProvider`(Task 4), `customerCommandsProvider.addPet/updatePet`(Task 5), `parseBirthDate`·`isValidBirthYear`·`parseWeight`·`weightText`·`formatWeight`·`optionalText`(Task 3), `formatDate`(Task 6), `todayProvider`(`features/home/state/today_provider.dart`), `AppChoiceChip`(Task 1)
- Produces: `PetForm({conditionTypes, today, submitLabel, busy, onSubmit: ValueChanged<PetFields>, initial: Pet?, errorText})`(등록 3단계가 Task 10 에서 다시 쓴다; 생일 칸 키 `birth_date_field`, 태어난 해 칸 키 `birth_year_field`). `PetFormScreen.add(customerId)`·`PetFormScreen.edit(petId)`(`ScreenKeys.petForm`). 라우트 `/pets/:petId/edit`, `/customers/:customerId/pets/new`.

**알아 둘 것:**
- 필수: 이름, 종류, 품종, 성별, 중성화, 나이(생일 / 태어난 해 / 모름 중 하나를 **직접 골라야** 한다), 몸무게, 질병(하나 이상 또는 "질병 없음"). 특이사항만 선택(설계 2절).
- "질병 없음"을 누르면 고른 질병·기타를 모두 비우고, 질병이나 기타를 고르면 "질병 없음"이 풀린다(C8 을 폼에서 막는다).
- 기타는 여러 줄을 더할 수 있고 이름이 있어야 한다. 정해진 질병은 칩 순서대로 보낸다.
- 품종 칸 아래에 종류별 추천 칩(강아지 8, 고양이 6)을 둔다 — 누르면 칸을 채운다(설계 6.1 "앱이 자주 쓰는 품종을 추천").
- 글자 수 한도는 서버 한도를 입력 제한으로 막는다(이름·품종 50, 기타 이름 30, 질병 메모 100, 특이사항 500).
- 추가가 끝나면 새 아이의 상세로 **바꿔 끼운다**(`pushReplacement`), 수정이 끝나면 뒤로(`pop`).
- 화면의 `_busy` 가드는 저장 버튼의 비활성과 겹쳐 테스트로 따로 판별되지 않는다(참조 구현의 변이에서 확인).

**막는 위협:** C8(질병·질병 없음 동시 — 폼이 막고, 서버 거절 문구도 보인다), A3(저장 연타)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/design/glass_boundary_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -13,6 +13,8 @@ void main() {
       'lib/features/customer/screens/pet_detail_screen.dart',
       'lib/features/customer/screens/customer_list_tab.dart',
       'lib/features/customer/screens/family_card_view.dart',
+      'lib/features/customer/screens/pet_form.dart',
+      'lib/features/customer/screens/pet_form_screen.dart',
     ];
     final violations = [
       for (final path in scrollScreens)
```

`app/test/features/customer/screens/pet_form_screen_test.dart` (새 파일):

```dart
import 'dart:async';
import 'dart:convert';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

/// 폼이 길어 한 화면에 다 들어오게 세로로 긴 화면을 쓴다.
void _tallView(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

/// 홈에서 [location]을 쌓아 연다(뒤로 가면 홈).
Future<void> _open(
  WidgetTester tester,
  CustomerTestSetup setup,
  String location,
) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push(location);
  await tester.pumpAndSettle();
}

/// 생일 검증의 "오늘"을 고정한다.
final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 22))];

Finder _field(String label) => find.widgetWithText(TextField, label);

Finder _save() =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == AppStrings.save);

Future<void> _tapChip(WidgetTester tester, String label) async {
  await tester.tap(find.bySemanticsLabel(label));
  await tester.pump();
}

Map<String, dynamic> _sent(CustomerTestSetup setup, String path) =>
    jsonDecode(utf8.decode(setup.adapter.lastBodyByPath[path]!))
        as Map<String, dynamic>;

FakeHandler _routes({FutureOr<FakeResponse> Function()? write}) =>
    (options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pet-condition-types':
          return const FakeResponse(statusCode: 200, data: conditionTypesJson);
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'GET /v1/shops/3/pets/21':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(petId: 21, name: '보리', noKnownConditions: true),
            ),
          );
        case 'PUT /v1/shops/3/pets/11':
        case 'PUT /v1/shops/3/pets/21':
        case 'POST /v1/shops/3/customers/7/pets':
          if (write != null) return write();
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(petId: 21, name: '보리', noKnownConditions: true),
            ),
          );
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    };

void main() {
  testWidgets('수정은 지금 값을 채워 두고, 바꾼 값을 통째로 보낸 뒤 상세로 돌아간다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11');
    await tester.tap(
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.edit,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.petForm), findsOneWidget);
    expect(find.text(AppStrings.editPetTitle), findsOneWidget);
    expect(find.widgetWithText(TextField, '콩이'), findsOneWidget);
    expect(find.widgetWithText(TextField, '2021.03.04'), findsOneWidget);
    expect(find.widgetWithText(TextField, '3.2'), findsOneWidget);
    expect(find.widgetWithText(TextField, '2기'), findsOneWidget);

    await tester.enterText(_field(AppStrings.weightLabel), '3.5');
    await tester.tap(_save());
    await tester.pumpAndSettle();

    expect(_sent(setup, '/v1/shops/3/pets/11'), {
      'name': '콩이',
      'species': 'dog',
      'breed': '말티즈',
      'sex': 'female',
      'neutered': true,
      'birth_date': '2021-03-04',
      'birth_year': null,
      'weight_kg': 3.5,
      'no_known_conditions': false,
      'conditions': [
        {'type_code': 'patella_luxation', 'custom_label': null, 'note': '2기'},
      ],
      'memo': '귀 만지면 싫어함',
    });
    expect(find.byKey(ScreenKeys.petForm), findsNothing);
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('추가는 빈 폼에서 시작하고, 저장하면 새 아이의 상세로 바꿔 간다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/customers/7/pets/new');

    expect(find.text(AppStrings.addPetTitle), findsOneWidget);
    await tester.enterText(_field(AppStrings.petNameLabel), ' 보리 ');
    await _tapChip(tester, AppStrings.speciesCat);
    await _tapChip(tester, '코리안 숏헤어');
    await _tapChip(tester, AppStrings.sexMale);
    await _tapChip(tester, AppStrings.neuteredNo);
    await _tapChip(tester, AppStrings.ageByBirthYear);
    await tester.enterText(find.byKey(const Key('birth_year_field')), '2020');
    await tester.enterText(_field(AppStrings.weightLabel), '4');
    await _tapChip(tester, AppStrings.noKnownConditions);
    await tester.tap(_save());
    await tester.pumpAndSettle();

    expect(_sent(setup, '/v1/shops/3/customers/7/pets'), {
      'name': '보리',
      'species': 'cat',
      'breed': '코리안 숏헤어',
      'sex': 'male',
      'neutered': false,
      'birth_date': null,
      'birth_year': 2020,
      'weight_kg': 4.0,
      'no_known_conditions': true,
      'conditions': <dynamic>[],
      'memo': null,
    });
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    expect(find.text('보리'), findsOneWidget);
    // 추가 화면은 상세로 바꿔 끼웠다 — 뒤로 가면 홈이다.
    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('빈 폼으로 저장하면 요청 없이 필수 항목을 모두 알린다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/customers/7/pets/new');

    await tester.tap(_save());
    await tester.pump();

    for (final message in [
      AppStrings.petNameRequired,
      AppStrings.speciesRequired,
      AppStrings.breedRequired,
      AppStrings.sexRequired,
      AppStrings.neuteredRequired,
      AppStrings.ageRequired,
      AppStrings.weightInvalid,
      AppStrings.healthRequired,
    ]) {
      expect(find.text(message), findsOneWidget, reason: message);
    }
    expect(setup.calls, isNot(contains('POST /v1/shops/3/customers/7/pets')));
  });

  testWidgets('질병 없음과 질병은 함께 설 수 없다 — 하나를 고르면 다른 쪽이 풀린다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await _tapChip(tester, AppStrings.noKnownConditions);
    expect(
      find.widgetWithText(TextField, '2기'),
      findsNothing,
      reason: '고른 질병이 비워진다',
    );

    await _tapChip(tester, '심장 질환');
    await tester.tap(_save());
    await tester.pumpAndSettle();

    final sent = _sent(setup, '/v1/shops/3/pets/11');
    expect(sent['no_known_conditions'], isFalse);
    expect(sent['conditions'], [
      {'type_code': 'heart_disease', 'custom_label': null, 'note': null},
    ]);
  });

  testWidgets('기타는 이름이 있어야 하고, 이름과 메모를 담아 보낸다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/21/edit');

    await _tapChip(tester, '+ ${AppStrings.conditionOther}');
    await tester.tap(_save());
    await tester.pump();
    expect(find.text(AppStrings.otherLabelRequired), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, AppStrings.conditionOtherHint),
      '눈물 자국',
    );
    await tester.enterText(
      find.widgetWithText(TextField, AppStrings.conditionNoteHint),
      '왼쪽',
    );
    await tester.tap(_save());
    await tester.pumpAndSettle();

    final sent = _sent(setup, '/v1/shops/3/pets/21');
    expect(sent['no_known_conditions'], isFalse);
    expect(sent['conditions'], [
      {'type_code': 'other', 'custom_label': '눈물 자국', 'note': '왼쪽'},
    ]);
  });

  testWidgets('생일·태어난 해·몸무게의 형식을 확인한다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await tester.enterText(
      find.byKey(const Key('birth_date_field')),
      '2099.01.01',
    );
    await tester.enterText(_field(AppStrings.weightLabel), '0');
    await tester.tap(_save());
    await tester.pump();
    expect(find.text(AppStrings.birthDateInvalid), findsOneWidget);
    expect(find.text(AppStrings.weightInvalid), findsOneWidget);

    await _tapChip(tester, AppStrings.ageByBirthYear);
    await tester.enterText(find.byKey(const Key('birth_year_field')), '1900');
    await tester.tap(_save());
    await tester.pump();
    expect(find.text(AppStrings.birthYearInvalid), findsOneWidget);
    expect(setup.calls, isNot(contains('PUT /v1/shops/3/pets/11')));
  });

  testWidgets('서버가 거절하면 그 문구를 보이고 폼에 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        write: () => const FakeResponse(
          statusCode: 422,
          data: {'code': 'PET_HEALTH_CONFLICT', 'message': 'x'},
        ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await tester.tap(_save());
    await tester.pumpAndSettle();

    expect(find.text('질병과 "질병 없음"을 함께 고를 수 없습니다.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.petForm), findsOneWidget);
  });

  testWidgets('저장 중에는 버튼을 막아 요청을 한 번만 보낸다', (tester) async {
    _tallView(tester);
    final gate = Completer<FakeResponse>();
    final setup = CustomerTestSetup(
      _routes(write: () => gate.future),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await tester.tap(_save());
    await tester.pump();
    await tester.tap(_save());
    await tester.pump();
    gate.complete(FakeResponse(statusCode: 200, data: petDetailJson()));
    await tester.pumpAndSettle();

    expect(
      setup.calls.where((c) => c == 'PUT /v1/shops/3/pets/11'),
      hasLength(1),
    );
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/pet_form_screen_test.dart`

Expected: 컴파일 오류 — `pet_form_screen.dart`와 `ScreenKeys.petForm`이 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/router/app_router.dart` (수정):

```diff
@@ -11,6 +11,7 @@ import '../../features/auth/screens/splash_screen.dart';
 import '../../features/auth/state/session.dart';
 import '../../features/auth/state/session_controller.dart';
 import '../../features/customer/screens/pet_detail_screen.dart';
+import '../../features/customer/screens/pet_form_screen.dart';
 import '../../features/home/screens/home_shell.dart';
 import '../../features/shop/screens/members_screen.dart';
 import '../../features/shop/screens/settings_screen.dart';
@@ -107,6 +108,18 @@ final routerProvider = Provider<GoRouter>((ref) {
           petId: int.parse(state.pathParameters['petId']!),
         ),
       ),
+      GoRoute(
+        path: '/pets/:petId/edit',
+        builder: (context, state) => PetFormScreen.edit(
+          petId: int.parse(state.pathParameters['petId']!),
+        ),
+      ),
+      GoRoute(
+        path: '/customers/:customerId/pets/new',
+        builder: (context, state) => PetFormScreen.add(
+          customerId: int.parse(state.pathParameters['customerId']!),
+        ),
+      ),
     ],
   );
```

`app/lib/core/router/screen_keys.dart` (수정):

```diff
@@ -13,5 +13,6 @@ class ScreenKeys {
   static const settingsShop = Key('screen_settings_shop');
   static const settingsAccount = Key('screen_settings_account');
   static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
+  static const petForm = Key('screen_pet_form');
   static const petDetail = Key('screen_pet_detail');
 }
```

`app/lib/features/customer/screens/pet_form.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';
import 'customer_labels.dart';

enum _AgeMode { birthDate, birthYear, unknown }

/// 기타 질병 한 줄(이름 + 메모).
class _OtherEntry {
  _OtherEntry({String label = '', String note = ''})
    : label = TextEditingController(text: label),
      note = TextEditingController(text: note);

  final TextEditingController label;
  final TextEditingController note;

  void dispose() {
    label.dispose();
    note.dispose();
  }
}

/// 반려동물 폼 — 등록 3단계, 반려동물 추가, 반려동물 수정이 함께 쓴다(설계 8.1).
///
/// 필수: 이름, 종류, 품종, 성별, 중성화, 나이(생일 / 태어난 해 / 모름),
/// 몸무게, 질병(하나 이상 또는 "질병 없음"). 특이사항만 선택이다. 입력 규칙을
/// 여기서 먼저 확인해 요청 없이 알려 주고, 통과하면 [onSubmit]에 넘긴다.
class PetForm extends StatefulWidget {
  const PetForm({
    super.key,
    required this.conditionTypes,
    required this.today,
    required this.submitLabel,
    required this.busy,
    required this.onSubmit,
    this.initial,
    this.errorText,
  });

  final List<ConditionType> conditionTypes;
  final DateTime today;
  final String submitLabel;
  final bool busy;
  final ValueChanged<PetFields> onSubmit;

  /// 수정할 때의 처음 값.
  final Pet? initial;

  /// 서버가 거절한 문구(부모가 준다).
  final String? errorText;

  @override
  State<PetForm> createState() => _PetFormState();
}

class _PetFormState extends State<PetForm> {
  final _name = TextEditingController();
  final _breed = TextEditingController();
  final _birthDate = TextEditingController();
  final _birthYear = TextEditingController();
  final _weight = TextEditingController();
  final _memo = TextEditingController();

  String? _species;
  String? _sex;
  bool? _neutered;
  _AgeMode? _ageMode;
  bool _noKnownConditions = false;

  /// 고른 정해진 질병(코드 → 메모 입력 칸). 칩 순서를 지키려고 삽입 순서를 쓴다.
  final Map<String, TextEditingController> _conditions = {};
  final List<_OtherEntry> _others = [];

  Map<String, String> _errors = {};

  @override
  void initState() {
    super.initState();
    final pet = widget.initial;
    if (pet == null) return;
    _name.text = pet.name;
    _breed.text = pet.breed;
    _species = pet.species;
    _sex = pet.sex;
    _neutered = pet.neutered;
    if (pet.birthDate != null) {
      _ageMode = _AgeMode.birthDate;
      _birthDate.text = formatDate(pet.birthDate!);
    } else if (pet.birthYear != null) {
      _ageMode = _AgeMode.birthYear;
      _birthYear.text = '${pet.birthYear}';
    } else {
      _ageMode = _AgeMode.unknown;
    }
    _weight.text = weightText(pet.weightKg);
    _memo.text = pet.memo ?? '';
    _noKnownConditions = pet.noKnownConditions;
    for (final c in pet.conditions) {
      if (c.typeCode == ConditionType.otherCode) {
        _others.add(
          _OtherEntry(label: c.customLabel ?? '', note: c.note ?? ''),
        );
      } else {
        _conditions[c.typeCode] = TextEditingController(text: c.note ?? '');
      }
    }
  }

  @override
  void dispose() {
    for (final c in [_name, _breed, _birthDate, _birthYear, _weight, _memo]) {
      c.dispose();
    }
    for (final c in _conditions.values) {
      c.dispose();
    }
    for (final o in _others) {
      o.dispose();
    }
    super.dispose();
  }

  void _toggleCondition(String code) {
    setState(() {
      final removed = _conditions.remove(code);
      if (removed != null) {
        removed.dispose();
      } else {
        _conditions[code] = TextEditingController();
        _noKnownConditions = false;
      }
    });
  }

  void _addOther() {
    setState(() {
      _others.add(_OtherEntry());
      _noKnownConditions = false;
    });
  }

  void _removeOther(_OtherEntry entry) {
    setState(() => _others.remove(entry));
    entry.dispose();
  }

  /// "질병 없음"을 누르면 고른 질병을 모두 비운다(둘은 함께 설 수 없다).
  void _toggleNoKnown() {
    setState(() {
      _noKnownConditions = !_noKnownConditions;
      if (_noKnownConditions) {
        for (final c in _conditions.values) {
          c.dispose();
        }
        _conditions.clear();
        for (final o in _others) {
          o.dispose();
        }
        _others.clear();
      }
    });
  }

  void _submit() {
    final errors = <String, String>{};
    final name = _name.text.trim();
    final breed = _breed.text.trim();
    if (name.isEmpty) errors['name'] = AppStrings.petNameRequired;
    if (_species == null) errors['species'] = AppStrings.speciesRequired;
    if (breed.isEmpty) errors['breed'] = AppStrings.breedRequired;
    if (_sex == null) errors['sex'] = AppStrings.sexRequired;
    if (_neutered == null) errors['neutered'] = AppStrings.neuteredRequired;

    DateTime? birthDate;
    int? birthYear;
    switch (_ageMode) {
      case null:
        errors['age'] = AppStrings.ageRequired;
      case _AgeMode.birthDate:
        birthDate = parseBirthDate(_birthDate.text, widget.today);
        if (birthDate == null) errors['age'] = AppStrings.birthDateInvalid;
      case _AgeMode.birthYear:
        birthYear = int.tryParse(_birthYear.text.trim());
        if (birthYear == null || !isValidBirthYear(birthYear, widget.today)) {
          errors['age'] = AppStrings.birthYearInvalid;
        }
      case _AgeMode.unknown:
        break;
    }

    final weight = parseWeight(_weight.text);
    if (weight == null) errors['weight'] = AppStrings.weightInvalid;

    final conditions = [
      for (final e in _conditions.entries)
        ConditionEntry(typeCode: e.key, note: optionalText(e.value.text)),
      for (final o in _others)
        ConditionEntry(
          typeCode: ConditionType.otherCode,
          customLabel: optionalText(o.label.text),
          note: optionalText(o.note.text),
        ),
    ];
    if (_others.any((o) => optionalText(o.label.text) == null)) {
      errors['conditions'] = AppStrings.otherLabelRequired;
    } else if (conditions.isEmpty && !_noKnownConditions) {
      errors['conditions'] = AppStrings.healthRequired;
    }

    setState(() => _errors = errors);
    if (errors.isNotEmpty) return;

    widget.onSubmit(
      PetFields(
        name: name,
        species: _species!,
        breed: breed,
        sex: _sex!,
        neutered: _neutered!,
        birthDate: birthDate,
        birthYear: birthYear,
        weightKg: weight!,
        noKnownConditions: _noKnownConditions,
        conditions: conditions,
        memo: optionalText(_memo.text),
      ),
    );
  }

  Widget _label(String text) => Padding(
    padding: const EdgeInsets.only(top: AppSpacing.lg, bottom: AppSpacing.xs),
    child: Text(text, style: AppTypography.caption),
  );

  Widget _error(String key) {
    final message = _errors[key];
    if (message == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xs),
      child: Text(message, style: AppTypography.caption),
    );
  }

  Widget _chips(List<Widget> chips) =>
      Wrap(spacing: AppSpacing.sm, runSpacing: AppSpacing.sm, children: chips);

  @override
  Widget build(BuildContext context) {
    final breeds = switch (_species) {
      'dog' => AppStrings.dogBreeds,
      'cat' => AppStrings.catBreeds,
      _ => const <String>[],
    };
    final fixedTypes = widget.conditionTypes
        .where((t) => t.code != ConditionType.otherCode)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _name,
          inputFormatters: [LengthLimitingTextInputFormatter(50)],
          decoration: InputDecoration(
            labelText: AppStrings.petNameLabel,
            errorText: _errors['name'],
          ),
        ),
        _label(AppStrings.speciesLabelText),
        _chips([
          for (final species in ['dog', 'cat'])
            AppChoiceChip(
              label: AppStrings.speciesLabel(species),
              selected: _species == species,
              onTap: () => setState(() => _species = species),
            ),
        ]),
        _error('species'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _breed,
          inputFormatters: [LengthLimitingTextInputFormatter(50)],
          decoration: InputDecoration(
            labelText: AppStrings.breedLabel,
            errorText: _errors['breed'],
          ),
        ),
        if (breeds.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          _chips([
            for (final breed in breeds)
              AppChoiceChip(
                label: breed,
                selected: _breed.text.trim() == breed,
                onTap: () => setState(() => _breed.text = breed),
              ),
          ]),
        ],
        _label(AppStrings.sexLabelText),
        _chips([
          for (final sex in ['female', 'male'])
            AppChoiceChip(
              label: AppStrings.sexLabel(sex),
              selected: _sex == sex,
              onTap: () => setState(() => _sex = sex),
            ),
          AppChoiceChip(
            label: AppStrings.neuteredYes,
            selected: _neutered == true,
            onTap: () => setState(() => _neutered = true),
          ),
          AppChoiceChip(
            label: AppStrings.neuteredNo,
            selected: _neutered == false,
            onTap: () => setState(() => _neutered = false),
          ),
        ]),
        _error('sex'),
        _error('neutered'),
        _label(AppStrings.ageLabel),
        _chips([
          AppChoiceChip(
            label: AppStrings.ageByBirthDate,
            selected: _ageMode == _AgeMode.birthDate,
            onTap: () => setState(() => _ageMode = _AgeMode.birthDate),
          ),
          AppChoiceChip(
            label: AppStrings.ageByBirthYear,
            selected: _ageMode == _AgeMode.birthYear,
            onTap: () => setState(() => _ageMode = _AgeMode.birthYear),
          ),
          AppChoiceChip(
            label: AppStrings.ageUnknown,
            selected: _ageMode == _AgeMode.unknown,
            onTap: () => setState(() => _ageMode = _AgeMode.unknown),
          ),
        ]),
        if (_ageMode == _AgeMode.birthDate)
          TextField(
            key: const Key('birth_date_field'),
            controller: _birthDate,
            keyboardType: TextInputType.datetime,
            inputFormatters: [LengthLimitingTextInputFormatter(10)],
            decoration: const InputDecoration(
              hintText: AppStrings.birthDateHint,
            ),
          ),
        if (_ageMode == _AgeMode.birthYear)
          TextField(
            key: const Key('birth_year_field'),
            controller: _birthYear,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(4),
            ],
            decoration: const InputDecoration(
              hintText: AppStrings.birthYearHint,
            ),
          ),
        _error('age'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _weight,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
            LengthLimitingTextInputFormatter(5),
          ],
          decoration: InputDecoration(
            labelText: AppStrings.weightLabel,
            hintText: AppStrings.weightHint,
            suffixText: AppStrings.weightUnit,
            errorText: _errors['weight'],
          ),
        ),
        _label(AppStrings.conditionsLabel),
        _chips([
          for (final type in fixedTypes)
            AppChoiceChip(
              label: type.label,
              selected: _conditions.containsKey(type.code),
              onTap: () => _toggleCondition(type.code),
            ),
          AppChoiceChip(
            label: '+ ${AppStrings.conditionOther}',
            selected: false,
            onTap: _addOther,
          ),
          AppChoiceChip(
            label: AppStrings.noKnownConditions,
            selected: _noKnownConditions,
            onTap: _toggleNoKnown,
          ),
        ]),
        for (final type in fixedTypes)
          if (_conditions.containsKey(type.code))
            _ConditionNote(title: type.label, note: _conditions[type.code]!),
        for (final other in _others)
          _OtherCondition(entry: other, onRemove: () => _removeOther(other)),
        _error('conditions'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _memo,
          minLines: 2,
          maxLines: 5,
          inputFormatters: [LengthLimitingTextInputFormatter(500)],
          decoration: const InputDecoration(
            labelText: AppStrings.petMemoLabel,
            hintText: AppStrings.petMemoHint,
          ),
        ),
        if (widget.errorText != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(widget.errorText!, style: AppTypography.caption),
        ],
        const SizedBox(height: AppSpacing.xl),
        Center(
          child: AppButton(
            label: widget.submitLabel,
            filled: true,
            busy: widget.busy,
            onPressed: widget.busy ? null : _submit,
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }
}

class _ConditionNote extends StatelessWidget {
  const _ConditionNote({required this.title, required this.note});

  final String title;
  final TextEditingController note;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        child: Row(
          children: [
            SizedBox(
              width: 96,
              child: Text(title, style: AppTypography.bodyStrong),
            ),
            Expanded(
              child: TextField(
                controller: note,
                inputFormatters: [LengthLimitingTextInputFormatter(100)],
                decoration: const InputDecoration(
                  hintText: AppStrings.conditionNoteHint,
                  border: InputBorder.none,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OtherCondition extends StatelessWidget {
  const _OtherCondition({required this.entry, required this.onRemove});

  final _OtherEntry entry;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        child: Row(
          children: [
            SizedBox(
              width: 96,
              child: TextField(
                controller: entry.label,
                inputFormatters: [LengthLimitingTextInputFormatter(30)],
                decoration: const InputDecoration(
                  hintText: AppStrings.conditionOtherHint,
                  border: InputBorder.none,
                ),
              ),
            ),
            Expanded(
              child: TextField(
                controller: entry.note,
                inputFormatters: [LengthLimitingTextInputFormatter(100)],
                decoration: const InputDecoration(
                  hintText: AppStrings.conditionNoteHint,
                  border: InputBorder.none,
                ),
              ),
            ),
            Pressable(
              semanticLabel: AppStrings.removeCondition,
              onTap: onRemove,
              child: const Icon(Icons.close, size: 18),
            ),
          ],
        ),
      ),
    );
  }
}
```

`app/lib/features/customer/screens/pet_form_screen.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../home/state/today_provider.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_providers.dart';
import 'pet_form.dart';

/// 반려동물 추가(기존 보호자에게)와 수정. 폼은 등록 3단계와 같다.
class PetFormScreen extends ConsumerStatefulWidget {
  const PetFormScreen.add({super.key, required int this.customerId})
    : petId = null;

  const PetFormScreen.edit({super.key, required int this.petId})
    : customerId = null;

  final int? customerId;
  final int? petId;

  @override
  ConsumerState<PetFormScreen> createState() => _PetFormScreenState();
}

class _PetFormScreenState extends ConsumerState<PetFormScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  Future<void> _submit(PetFields fields) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    final commands = ref.read(customerCommandsProvider);
    try {
      final petId = widget.petId;
      if (petId != null) {
        await commands.updatePet(shopId, petId, fields);
        if (mounted) context.pop();
      } else {
        final added = await commands.addPet(shopId, widget.customerId!, fields);
        if (mounted) context.pushReplacement('/pets/${added.pet.petId}');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final petId = widget.petId;
    final types = shopId == null
        ? const AsyncValue<List<ConditionType>>.loading()
        : ref.watch(conditionTypesProvider(shopId));
    final pet = petId == null
        ? const AsyncValue<PetDetail?>.data(null)
        : shopId == null
        ? const AsyncValue<PetDetail?>.loading()
        : ref.watch(petDetailProvider((shopId: shopId, petId: petId)));

    Widget body;
    if (types.hasError || pet.hasError) {
      body = Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              messageFor(types.error ?? pet.error!),
              style: AppTypography.body,
            ),
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              label: AppStrings.retry,
              onPressed: () {
                ref.invalidate(conditionTypesProvider(shopId!));
                if (petId != null) {
                  ref.invalidate(
                    petDetailProvider((shopId: shopId, petId: petId)),
                  );
                }
              },
            ),
          ],
        ),
      );
    } else if (!types.hasValue || !pet.hasValue) {
      body = const Center(child: CircularProgressIndicator());
    } else {
      body = SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: PetForm(
          initial: pet.value?.pet,
          conditionTypes: types.value!,
          today: ref.watch(todayProvider),
          submitLabel: AppStrings.save,
          busy: _busy,
          errorText: _errorText,
          onSubmit: _submit,
        ),
      );
    }

    return Scaffold(
      key: ScreenKeys.petForm,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      petId == null
                          ? AppStrings.addPetTitle
                          : AppStrings.editPetTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(child: body),
            ],
          ),
        ),
      ),
    );
  }
}
```

`app/lib/l10n/app_strings.dart` (수정):

```diff
@@ -162,6 +162,43 @@ class AppStrings {
 
   static String petCountText(int count) => '$count마리';
 
+  static const petNameLabel = '이름';
+  static const speciesLabelText = '종류';
+  static const breedLabel = '품종';
+  static const sexLabelText = '성별';
+  static const neuteredYes = '중성화 했어요';
+  static const neuteredNo = '안 했어요';
+  static const ageLabel = '나이';
+  static const ageByBirthDate = '생일';
+  static const ageByBirthYear = '태어난 해';
+  static const birthDateHint = 'YYYY.MM.DD';
+  static const birthYearHint = '예: 2021';
+  static const weightHint = '예: 3.2';
+  static const weightUnit = 'kg';
+  static const conditionsLabel = '질병';
+  static const conditionOther = '기타';
+  static const conditionOtherHint = '질병 이름';
+  static const conditionNoteHint = '메모 (선택)';
+  static const removeCondition = '이 질병 빼기';
+  static const petMemoHint = '특이사항 (선택)';
+  static const petNameRequired = '이름을 입력해 주세요.';
+  static const speciesRequired = '종류를 골라 주세요.';
+  static const breedRequired = '품종을 입력해 주세요.';
+  static const sexRequired = '성별을 골라 주세요.';
+  static const neuteredRequired = '중성화 여부를 골라 주세요.';
+  static const ageRequired = '생일·태어난 해·모름 중 하나를 골라 주세요.';
+  static const birthDateInvalid = '생일을 YYYY.MM.DD 로 입력해 주세요(오늘까지, 40년 전부터).';
+  static const birthYearInvalid = '태어난 해를 확인해 주세요(올해까지, 40년 전부터).';
+  static const weightInvalid = '몸무게를 kg 으로 입력해 주세요(예: 3.2).';
+  static const healthRequired = '질병을 고르거나 "질병 없음"을 눌러 주세요.';
+  static const otherLabelRequired = '기타 질병의 이름을 입력해 주세요.';
+  static const addPetTitle = '반려동물 추가';
+  static const editPetTitle = '반려동물 수정';
+
+  /// 품종 입력 칸 아래에 보이는 추천(누르면 채운다).
+  static const dogBreeds = ['말티즈', '푸들', '포메라니안', '비숑', '시츄', '요크셔테리어', '치와와', '믹스'];
+  static const catBreeds = ['코리안 숏헤어', '러시안 블루', '페르시안', '브리티시 숏헤어', '스코티시 폴드', '믹스'];
+
   /// 로그인 수단 제공자 코드를 화면에 보여줄 라벨로 바꾼다. 계정 화면과
   /// 재인증 시트(Task 16)가 함께 쓴다.
   static String providerLabel(String provider) => switch (provider) {
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/pet_form_screen_test.dart` → Expected: `+9: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+314: All tests passed!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `pet_form.dart`의 `_toggleNoKnown`에서 `if (_noKnownConditions) { … }` 블록을 지운다 → `질병 없음과 질병은 함께 설 수 없다` 실패
- `_submit`의 `if (_others.any((o) => optionalText(o.label.text) == null))` 분기를 지운다 → `기타는 이름이 있어야 하고` 실패

- [ ] **Step 6: 커밋한다**

```bash
git add app/lib/core/router/app_router.dart app/lib/core/router/screen_keys.dart app/lib/features/customer/screens/pet_form.dart app/lib/features/customer/screens/pet_form_screen.dart app/lib/l10n/app_strings.dart app/test/design/glass_boundary_test.dart app/test/features/customer/screens/pet_form_screen_test.dart
git commit -m "feat(app): 반려동물 폼 — 추가와 수정

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: 보호자 수정과 고객 삭제(사장만)

**Files:**
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/lib/core/router/screen_keys.dart`
- Create: `app/lib/features/customer/screens/customer_edit_screen.dart`
- Create: `app/lib/features/customer/screens/customer_form.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/test/design/glass_boundary_test.dart`
- Create: `app/test/features/customer/screens/customer_edit_screen_test.dart`

**Interfaces:**
- Consumes: `customerDetailProvider`(Task 4), `customerCommandsProvider.updateCustomer/deleteCustomer`(Task 5), `phoneDigits`·`isValidPhone`·`formatPhone`·`optionalText`(Task 3), `AppChoiceChip`(Task 1)
- Produces: `CustomerForm({submitLabel, busy, onSubmit: ValueChanged<CustomerFields>, initial: Customer?, fixedPhone: String?, errorText})`(등록 2단계가 `fixedPhone`으로 전화 칸을 숨기고 다시 쓴다). `CustomerEditScreen(customerId)`(`ScreenKeys.customerEdit`), 라우트 `/customers/:customerId/edit`.

**알아 둘 것:**
- 고객 삭제 버튼은 보호자 수정 화면 맨 아래에 **사장에게만** 보인다(설계 8.2 — 보안 경계는 서버 403). 확인 시트를 거쳐 익명화하고 홈(고객 탭)으로 `go`한다 — 이 고객의 화면은 모두 사라졌다.
- 번호는 하이픈을 넣어 보여 주고(`formatPhone`), 숫자만 보낸다. 보조 연락처도 같은 형식을 본다(결정 기록 005).
- 마케팅 수신은 [동의 / 거부] 중 하나를 골라야 한다(기본값 없음).

**막는 위협:** C4(직원에게 삭제 버튼 없음), C3·C2 문구(`CUSTOMER_PHONE_TAKEN`), C6(삭제 뒤 목록을 다시 부른다)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/design/glass_boundary_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -15,6 +15,8 @@ void main() {
       'lib/features/customer/screens/family_card_view.dart',
       'lib/features/customer/screens/pet_form.dart',
       'lib/features/customer/screens/pet_form_screen.dart',
+      'lib/features/customer/screens/customer_form.dart',
+      'lib/features/customer/screens/customer_edit_screen.dart',
     ];
     final violations = [
       for (final path in scrollScreens)
```

`app/test/features/customer/screens/customer_edit_screen_test.dart` (새 파일):

```dart
import 'dart:convert';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

void _tallView(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 1600);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Future<void> _open(WidgetTester tester, CustomerTestSetup setup) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/pets/11');
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/customers/7/edit');
  await tester.pumpAndSettle();
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

FakeHandler _routes({FakeResponse? put, FakeResponse? delete}) =>
    (options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/customers':
          return FakeResponse(statusCode: 200, data: pageJson());
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'GET /v1/shops/3/customers/7':
          return FakeResponse(
            statusCode: 200,
            data: customerDetailJson(
              customer: customerJson(phoneAlt: '0212345678'),
            ),
          );
        case 'PUT /v1/shops/3/customers/7':
          return put ??
              FakeResponse(statusCode: 200, data: customerDetailJson());
        case 'DELETE /v1/shops/3/customers/7':
          return delete ?? const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    };

void main() {
  testWidgets('지금 값을 채워 두고, 번호는 숫자만 보낸 뒤 상세로 돌아간다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes());
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
    expect(find.widgetWithText(TextField, '김민지'), findsOneWidget);
    expect(find.widgetWithText(TextField, '010-1234-5678'), findsOneWidget);
    expect(find.widgetWithText(TextField, '02-1234-5678'), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, '010-1234-5678'),
      '010-9999-8888',
    );
    await tester.tap(find.bySemanticsLabel(AppStrings.marketingDeclined));
    await tester.pump();
    await tester.tap(_button(AppStrings.save));
    await tester.pumpAndSettle();

    expect(
      jsonDecode(
        utf8.decode(setup.adapter.lastBodyByPath['/v1/shops/3/customers/7']!),
      ),
      {
        'name': '김민지',
        'phone': '01099998888',
        'phone_alt': '0212345678',
        'marketing_consent': false,
        'memo': '오후 방문 선호',
      },
    );
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('번호·보조 연락처 형식이 틀리면 요청 없이 알린다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes());
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.enterText(
      find.widgetWithText(TextField, '010-1234-5678'),
      '010-12',
    );
    await tester.enterText(
      find.widgetWithText(TextField, '02-1234-5678'),
      '1234',
    );
    await tester.tap(_button(AppStrings.save));
    await tester.pump();

    expect(find.text(AppStrings.phoneInvalid), findsOneWidget);
    expect(find.text(AppStrings.phoneAltInvalid), findsOneWidget);
    expect(setup.calls, isNot(contains('PUT /v1/shops/3/customers/7')));
  });

  testWidgets('다른 고객의 번호면(CUSTOMER_PHONE_TAKEN) 문구를 보이고 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        put: const FakeResponse(
          statusCode: 409,
          data: {'code': 'CUSTOMER_PHONE_TAKEN', 'message': 'x'},
        ),
      ),
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.save));
    await tester.pumpAndSettle();

    expect(find.text('이미 등록된 전화번호입니다.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
  });

  testWidgets('직원에게는 고객 삭제가 보이지 않는다(C4 — 경계는 서버 403)', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), role: 'staff');
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(_button(AppStrings.deleteCustomer), findsNothing);
  });

  testWidgets('사장은 확인을 거쳐 고객을 삭제하고, 홈의 고객 탭으로 돌아가 목록을 다시 부른다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes());
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.tabCustomers));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).push('/pets/11');
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).push('/customers/7/edit');
    await tester.pumpAndSettle();

    await tester.tap(_button(AppStrings.deleteCustomer));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.deleteCustomerConfirm), findsOneWidget);
    await tester.tap(_button(AppStrings.deleteCustomer).last);
    await tester.pump(const Duration(milliseconds: 1));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.byKey(ScreenKeys.petDetail), findsNothing);
    final afterDelete = setup.calls.sublist(
      setup.calls.indexOf('DELETE /v1/shops/3/customers/7'),
    );
    expect(afterDelete, [
      'DELETE /v1/shops/3/customers/7',
      'GET /v1/shops/3/customers',
    ]);
  });

  testWidgets('서버가 삭제를 거절하면(PERMISSION_DENIED) 문구를 보이고 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        delete: const FakeResponse(
          statusCode: 403,
          data: {'code': 'PERMISSION_DENIED', 'message': 'x'},
        ),
      ),
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.deleteCustomer));
    await tester.pumpAndSettle();
    await tester.tap(_button(AppStrings.deleteCustomer).last);
    await tester.pumpAndSettle();

    expect(find.text('이 작업을 할 권한이 없습니다.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/customer_edit_screen_test.dart`

Expected: 컴파일 오류 — `customer_edit_screen.dart`와 `ScreenKeys.customerEdit`이 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/router/app_router.dart` (수정):

```diff
@@ -12,6 +12,7 @@ import '../../features/auth/state/session.dart';
 import '../../features/auth/state/session_controller.dart';
 import '../../features/customer/screens/pet_detail_screen.dart';
 import '../../features/customer/screens/pet_form_screen.dart';
+import '../../features/customer/screens/customer_edit_screen.dart';
 import '../../features/home/screens/home_shell.dart';
 import '../../features/shop/screens/members_screen.dart';
 import '../../features/shop/screens/settings_screen.dart';
@@ -120,6 +121,12 @@ final routerProvider = Provider<GoRouter>((ref) {
           customerId: int.parse(state.pathParameters['customerId']!),
         ),
       ),
+      GoRoute(
+        path: '/customers/:customerId/edit',
+        builder: (context, state) => CustomerEditScreen(
+          customerId: int.parse(state.pathParameters['customerId']!),
+        ),
+      ),
     ],
   );
```

`app/lib/core/router/screen_keys.dart` (수정):

```diff
@@ -13,6 +13,7 @@ class ScreenKeys {
   static const settingsShop = Key('screen_settings_shop');
   static const settingsAccount = Key('screen_settings_account');
   static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
+  static const customerEdit = Key('screen_customer_edit');
   static const petForm = Key('screen_pet_form');
   static const petDetail = Key('screen_pet_detail');
 }
```

`app/lib/features/customer/screens/customer_edit_screen.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_providers.dart';
import 'customer_form.dart';

/// 보호자 수정. 사장에게만 맨 아래 "고객 삭제"(익명화)가 보인다 — 보안 경계는
/// 서버의 `customer:delete`(403)다.
class CustomerEditScreen extends ConsumerStatefulWidget {
  const CustomerEditScreen({super.key, required this.customerId});

  final int customerId;

  @override
  ConsumerState<CustomerEditScreen> createState() => _CustomerEditScreenState();
}

class _CustomerEditScreenState extends ConsumerState<CustomerEditScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  /// 쓰기 하나를 돌린다(연타 방지, 실패 문구). 성공하면 true.
  Future<bool> _run(Future<void> Function(int shopId) action) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return false;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action(shopId);
      return true;
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _errorText = messageFor(e);
        });
      }
      return false;
    }
  }

  Future<void> _save(CustomerFields fields) async {
    final saved = await _run(
      (shopId) => ref
          .read(customerCommandsProvider)
          .updateCustomer(shopId, widget.customerId, fields),
    );
    if (saved && mounted) context.pop();
  }

  Future<void> _delete() async {
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.deleteCustomerConfirm,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.deleteCustomer,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final deleted = await _run(
      (shopId) => ref
          .read(customerCommandsProvider)
          .deleteCustomer(shopId, widget.customerId),
    );
    // 이 고객의 화면(반려동물 상세 등)은 모두 사라졌다 — 홈(고객 탭)으로 간다.
    if (deleted && mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final session = ref.watch(sessionControllerProvider).value;
    final isOwner =
        session is SignedIn && (session.selectedShop?.isOwner ?? false);
    final key = shopId == null
        ? null
        : (shopId: shopId, customerId: widget.customerId);
    final detail = key == null
        ? const AsyncValue<CustomerDetail>.loading()
        : ref.watch(customerDetailProvider(key));

    return Scaffold(
      key: ScreenKeys.customerEdit,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      AppStrings.editOwnerTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: detail.when(
                  data: (detail) => SingleChildScrollView(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Column(
                      children: [
                        CustomerForm(
                          initial: detail.customer,
                          submitLabel: AppStrings.save,
                          busy: _busy,
                          errorText: _errorText,
                          onSubmit: _save,
                        ),
                        if (isOwner) ...[
                          const SizedBox(height: AppSpacing.xxl),
                          AppButton(
                            label: AppStrings.deleteCustomer,
                            onPressed: _busy ? null : _delete,
                          ),
                        ],
                      ],
                    ),
                  ),
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(messageFor(error), style: AppTypography.body),
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: AppStrings.retry,
                          onPressed: () =>
                              ref.invalidate(customerDetailProvider(key!)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

`app/lib/features/customer/screens/customer_form.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';

/// 보호자 폼 — 등록 2단계와 보호자 수정이 함께 쓴다(설계 8.1).
///
/// 필수: 이름, 전화, 마케팅 수신(동의 / 거부 중 하나). 보조 연락처·메모는
/// 선택이다. 등록 2단계는 1단계에서 확인한 번호를 [fixedPhone]으로 넘겨
/// 전화 칸을 숨긴다. 번호는 숫자만 보낸다.
class CustomerForm extends StatefulWidget {
  const CustomerForm({
    super.key,
    required this.submitLabel,
    required this.busy,
    required this.onSubmit,
    this.initial,
    this.fixedPhone,
    this.errorText,
  });

  final String submitLabel;
  final bool busy;
  final ValueChanged<CustomerFields> onSubmit;
  final Customer? initial;

  /// 숫자만. 있으면 전화 칸을 보이지 않고 이 번호를 쓴다.
  final String? fixedPhone;
  final String? errorText;

  @override
  State<CustomerForm> createState() => _CustomerFormState();
}

class _CustomerFormState extends State<CustomerForm> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _phoneAlt = TextEditingController();
  final _memo = TextEditingController();
  bool? _consent;
  Map<String, String> _errors = {};

  @override
  void initState() {
    super.initState();
    final c = widget.initial;
    if (c == null) return;
    _name.text = c.name;
    _phone.text = formatPhone(c.phone);
    _phoneAlt.text = c.phoneAlt == null ? '' : formatPhone(c.phoneAlt!);
    _memo.text = c.memo ?? '';
    _consent = c.marketingConsent;
  }

  @override
  void dispose() {
    for (final c in [_name, _phone, _phoneAlt, _memo]) {
      c.dispose();
    }
    super.dispose();
  }

  void _submit() {
    final errors = <String, String>{};
    final name = _name.text.trim();
    if (name.isEmpty) errors['name'] = AppStrings.ownerNameRequired;
    final phone = widget.fixedPhone ?? phoneDigits(_phone.text);
    if (!isValidPhone(phone)) errors['phone'] = AppStrings.phoneInvalid;
    final altDigits = phoneDigits(_phoneAlt.text);
    final phoneAlt = altDigits.isEmpty ? null : altDigits;
    if (phoneAlt != null && !isValidPhone(phoneAlt)) {
      errors['phoneAlt'] = AppStrings.phoneAltInvalid;
    }
    if (_consent == null) errors['consent'] = AppStrings.consentRequired;

    setState(() => _errors = errors);
    if (errors.isNotEmpty) return;

    widget.onSubmit(
      CustomerFields(
        name: name,
        phone: phone,
        phoneAlt: phoneAlt,
        marketingConsent: _consent!,
        memo: optionalText(_memo.text),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final phoneFormatters = [
      FilteringTextInputFormatter.allow(RegExp(r'[0-9\- ]')),
      LengthLimitingTextInputFormatter(20),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _name,
          inputFormatters: [LengthLimitingTextInputFormatter(50)],
          decoration: InputDecoration(
            labelText: AppStrings.ownerNameLabel,
            hintText: AppStrings.ownerNameHint,
            errorText: _errors['name'],
          ),
        ),
        if (widget.fixedPhone == null) ...[
          const SizedBox(height: AppSpacing.sm),
          TextField(
            controller: _phone,
            keyboardType: TextInputType.phone,
            inputFormatters: phoneFormatters,
            decoration: InputDecoration(
              labelText: AppStrings.ownerPhoneLabel,
              hintText: AppStrings.phoneHint,
              errorText: _errors['phone'],
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _phoneAlt,
          keyboardType: TextInputType.phone,
          inputFormatters: phoneFormatters,
          decoration: InputDecoration(
            labelText: AppStrings.ownerPhoneAltLabel,
            hintText: AppStrings.phoneAltHint,
            errorText: _errors['phoneAlt'],
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(
            top: AppSpacing.lg,
            bottom: AppSpacing.xs,
          ),
          child: Text(
            AppStrings.marketingConsentLabel,
            style: AppTypography.caption,
          ),
        ),
        Wrap(
          spacing: AppSpacing.sm,
          children: [
            AppChoiceChip(
              label: AppStrings.marketingAgreed,
              selected: _consent == true,
              onTap: () => setState(() => _consent = true),
            ),
            AppChoiceChip(
              label: AppStrings.marketingDeclined,
              selected: _consent == false,
              onTap: () => setState(() => _consent = false),
            ),
          ],
        ),
        if (_errors['consent'] != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Text(_errors['consent']!, style: AppTypography.caption),
          ),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _memo,
          minLines: 2,
          maxLines: 5,
          inputFormatters: [LengthLimitingTextInputFormatter(500)],
          decoration: const InputDecoration(
            labelText: AppStrings.customerMemoLabel,
            hintText: AppStrings.customerMemoHint,
          ),
        ),
        if (widget.errorText != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(widget.errorText!, style: AppTypography.caption),
        ],
        const SizedBox(height: AppSpacing.xl),
        Center(
          child: AppButton(
            label: widget.submitLabel,
            filled: true,
            busy: widget.busy,
            onPressed: widget.busy ? null : _submit,
          ),
        ),
      ],
    );
  }
}
```

`app/lib/l10n/app_strings.dart` (수정):

```diff
@@ -199,6 +199,18 @@ class AppStrings {
   static const dogBreeds = ['말티즈', '푸들', '포메라니안', '비숑', '시츄', '요크셔테리어', '치와와', '믹스'];
   static const catBreeds = ['코리안 숏헤어', '러시안 블루', '페르시안', '브리티시 숏헤어', '스코티시 폴드', '믹스'];
 
+  static const ownerNameHint = '예: 김민지, 콩이 보호자';
+  static const phoneHint = '예: 010-1234-5678';
+  static const phoneAltHint = '보조 연락처 (선택)';
+  static const customerMemoHint = '메모 (선택)';
+  static const ownerNameRequired = '이름을 입력해 주세요.';
+  static const phoneInvalid = '전화번호를 확인해 주세요.';
+  static const phoneAltInvalid = '보조 연락처를 확인해 주세요.';
+  static const consentRequired = '마케팅 수신 동의 여부를 골라 주세요.';
+  static const editOwnerTitle = '보호자 수정';
+  static const deleteCustomer = '고객 삭제';
+  static const deleteCustomerConfirm = '고객을 삭제할까요? 보호자의 이름·전화번호·메모와 반려동물의 이름·질병 기록이 지워지고 되돌릴 수 없습니다.';
+
   /// 로그인 수단 제공자 코드를 화면에 보여줄 라벨로 바꾼다. 계정 화면과
   /// 재인증 시트(Task 16)가 함께 쓴다.
   static String providerLabel(String provider) => switch (provider) {
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/customer_edit_screen_test.dart` → Expected: `+7: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+320: All tests passed!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `customer_edit_screen.dart`의 `if (isOwner) ...[`를 `if (true) ...[`로 바꾼다 → `직원에게는 고객 삭제가 보이지 않는다` 실패

- [ ] **Step 6: 커밋한다**

```bash
git add app/lib/core/router/app_router.dart app/lib/core/router/screen_keys.dart app/lib/features/customer/screens/customer_edit_screen.dart app/lib/features/customer/screens/customer_form.dart app/lib/l10n/app_strings.dart app/test/design/glass_boundary_test.dart app/test/features/customer/screens/customer_edit_screen_test.dart
git commit -m "feat(app): 보호자 수정과 고객 삭제(사장만)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: 고객 등록 3단계와 번호 조회, 고객 탭의 + 버튼

**Files:**
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/lib/core/router/screen_keys.dart`
- Create: `app/lib/features/customer/screens/register_customer_screen.dart`
- Modify: `app/lib/features/home/screens/home_shell.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/test/design/glass_boundary_test.dart`
- Create: `app/test/features/customer/screens/register_customer_screen_test.dart`
- Create (골든, 명령으로 만든다): `app/test/features/customer/screens/goldens/register_pet_step.png`

**Interfaces:**
- Consumes: `CustomerForm`(Task 9), `PetForm`(Task 8), `customerCommandsProvider.lookup/register`(Task 5), `conditionTypesProvider`(Task 4), `phoneDigits`·`isValidPhone`(Task 3), 라우트 `/customers/:customerId/pets/new`(Task 8)
- Produces: `RegisterCustomerScreen`(`ScreenKeys.registerCustomer`), 라우트 `/customers/new`. 홈 셸의 + 버튼은 고객 탭에서 등록을 연다(이름표 "고객 등록").

**알아 둘 것:**
- 번호가 형식에 맞게 완성되는 순간 조회한다(목업 "번호를 치는 순간"). 형식이 안 맞으면 보내지 않는다 — 서버는 형식이 틀린 번호에 404 가 아니라 422 를 준다(결정 기록 005).
- 이미 있는 번호면 "이미 등록된 번호예요 — 김민지 (콩이, 두부)"와 [이 보호자에게 반려동물 추가] — 반려동물 추가 화면으로 바꿔 끼운다. 이때 [다음]은 막힌다.
- 번호 조회는 입력마다 나갈 수 있다 — 순번(`_lookupSeq`)으로 늦게 온 옛 번호의 결과를 버린다.
- 세 단계는 한 화면의 `IndexedStack`에서 오간다 — 앞 단계로 돌아가도 적은 값이 남는다. 머리의 뒤로 가기와 시스템 뒤로 가기(`PopScope`) 모두 앞 단계로 간다.
- 저장이 끝나면 새 아이의 상세로 바꿔 끼운다 — 뒤로 가면 고객 탭이다.
- 테스트의 `_onStage`: `IndexedStack`은 가려진 단계도 트리에 두므로 보이는 단계의 위젯만 `hitTestable()`로 찾는다.

**막는 위협:** C2(그사이 같은 번호가 등록되면 409 문구), A2(늦게 온 옛 번호 조회 결과), A7(완성되지 않은 번호로 조회하지 않는다)

- [ ] **Step 1: 테스트를 쓴다**

`app/test/design/glass_boundary_test.dart` (수정 — `-` 줄을 지우고 `+` 줄을 더한다):

```diff
@@ -17,6 +17,7 @@ void main() {
       'lib/features/customer/screens/pet_form_screen.dart',
       'lib/features/customer/screens/customer_form.dart',
       'lib/features/customer/screens/customer_edit_screen.dart',
+      'lib/features/customer/screens/register_customer_screen.dart',
     ];
     final violations = [
       for (final path in scrollScreens)
```

`app/test/features/customer/screens/register_customer_screen_test.dart` (새 파일):

```dart
import 'dart:async';
import 'dart:convert';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 22))];

void _tallView(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

/// 보이는 단계(IndexedStack 의 앞면)의 위젯만 찾는다.
Finder _onStage(Finder finder) => find
    .descendant(
      of: find.byWidgetPredicate((w) => w is IndexedStack),
      matching: finder,
    )
    .hitTestable();

/// 홈의 고객 탭에서 + 버튼으로 등록을 연다.
Future<void> _openFromFab(WidgetTester tester, CustomerTestSetup setup) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  await tester.tap(find.text(AppStrings.tabCustomers));
  await tester.pumpAndSettle();
  await tester.tap(find.bySemanticsLabel(AppStrings.registerCustomer));
  await tester.pumpAndSettle();
}

/// 조회가 나갈 시간을 준다(dio 는 0초 타이머 뒤에 보낸다).
Future<void> _settle(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 1));
  await tester.pumpAndSettle();
}

Future<void> _tapChip(WidgetTester tester, String label) async {
  await tester.tap(_onStage(find.bySemanticsLabel(label)));
  await tester.pump();
}

FakeHandler _routes({
  FutureOr<FakeResponse> Function(String phone)? lookup,
  FakeResponse? register,
}) => (options, body) {
  switch ('${options.method} ${options.path}') {
    case 'GET /v1/shops/3/customers':
      return FakeResponse(statusCode: 200, data: pageJson(items: []));
    case 'GET /v1/shops/3/customers/lookup':
      final phone = options.queryParameters['phone'] as String;
      if (lookup != null) return lookup(phone);
      return const FakeResponse(
        statusCode: 404,
        data: {'code': 'CUSTOMER_NOT_FOUND', 'message': 'x'},
      );
    case 'GET /v1/shops/3/pet-condition-types':
      return const FakeResponse(statusCode: 200, data: conditionTypesJson);
    case 'POST /v1/shops/3/customers':
      return register ??
          FakeResponse(
            statusCode: 201,
            data: customerDetailJson(pets: [petJson(petId: 31, name: '보리')]),
          );
    case 'GET /v1/shops/3/pets/31':
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(pet: petJson(petId: 31, name: '보리')),
      );
    case 'GET /v1/shops/3/pets/new':
      fail('pets/new 는 없는 경로다');
  }
  fail('예상하지 못한 요청: ${options.method} ${options.path}');
};

Future<void> _fillPet(WidgetTester tester) async {
  await tester.enterText(
    _onStage(find.widgetWithText(TextField, AppStrings.petNameLabel)),
    '보리',
  );
  await _tapChip(tester, AppStrings.speciesDog);
  await _tapChip(tester, '푸들');
  await _tapChip(tester, AppStrings.sexFemale);
  await _tapChip(tester, AppStrings.neuteredYes);
  await _tapChip(tester, AppStrings.ageUnknown);
  await tester.enterText(
    _onStage(find.widgetWithText(TextField, AppStrings.weightLabel)),
    '2.8',
  );
  await _tapChip(tester, '슬개골 탈구');
}

void main() {
  testWidgets('새 번호 — 번호 확인, 보호자, 반려동물을 거쳐 한 번에 등록하고 새 아이의 상세로 간다', (
    tester,
  ) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    expect(find.byKey(ScreenKeys.registerCustomer), findsOneWidget);
    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepPhone, 1)),
      findsOneWidget,
    );
    expect(
      tester.widget<AppButton>(_onStage(_button(AppStrings.next))).onPressed,
      isNull,
    );

    await tester.enterText(_onStage(find.byType(TextField)), '010-1234-5678');
    await _settle(tester);
    expect(setup.adapter.requests.last.queryParameters, {
      'phone': '01012345678',
    });
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepOwner, 2)),
      findsOneWidget,
    );
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepPet, 3)),
      findsOneWidget,
    );
    await _fillPet(tester);
    await tester.tap(_onStage(_button(AppStrings.save)));
    await tester.pumpAndSettle();

    final sent = jsonDecode(
      utf8.decode(setup.adapter.lastBodyByPath['/v1/shops/3/customers']!),
    );
    expect(sent, {
      'customer': {
        'name': '김민지',
        'phone': '01012345678',
        'phone_alt': null,
        'marketing_consent': true,
        'memo': null,
      },
      'pet': {
        'name': '보리',
        'species': 'dog',
        'breed': '푸들',
        'sex': 'female',
        'neutered': true,
        'birth_date': null,
        'birth_year': null,
        'weight_kg': 2.8,
        'no_known_conditions': false,
        'conditions': [
          {'type_code': 'patella_luxation', 'custom_label': null, 'note': null},
        ],
        'memo': null,
      },
    });
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    // 등록 화면은 상세로 바꿔 끼웠다 — 뒤로 가면 홈(고객 탭)이다.
    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('이미 있는 번호 — 알려 주고, 그 보호자에게 반려동물 추가로 건너뛴다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        lookup: (phone) => const FakeResponse(
          statusCode: 200,
          data: {
            'customer_id': 7,
            'name': '김민지',
            'pet_names': ['콩이', '두부'],
          },
        ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);

    expect(
      find.text(AppStrings.lookupFound('김민지', ['콩이', '두부'])),
      findsOneWidget,
    );
    expect(
      tester.widget<AppButton>(_onStage(_button(AppStrings.next))).onPressed,
      isNull,
    );
    await tester.tap(_button(AppStrings.addPetToExisting));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.petForm), findsOneWidget);
    expect(find.text(AppStrings.addPetTitle), findsOneWidget);
  });

  testWidgets('번호가 완성되기 전에는 조회하지 않는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    await tester.enterText(_onStage(find.byType(TextField)), '010-1234');
    await _settle(tester);

    expect(setup.calls, isNot(contains('GET /v1/shops/3/customers/lookup')));
  });

  testWidgets('번호를 바꾸면 늦게 온 옛 번호의 조회 결과를 버린다', (tester) async {
    _tallView(tester);
    final slow = Completer<FakeResponse>();
    final setup = CustomerTestSetup(
      _routes(
        lookup: (phone) => phone == '01011112222'
            ? slow.future
            : const FakeResponse(
                statusCode: 404,
                data: {'code': 'CUSTOMER_NOT_FOUND', 'message': 'x'},
              ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    await tester.enterText(_onStage(find.byType(TextField)), '01011112222');
    // 느린 조회가 도는 동안은 진행 막대가 움직여 settle 하지 않는다 — 한 번만 돌린다.
    await tester.pump(const Duration(milliseconds: 1));
    await tester.enterText(_onStage(find.byType(TextField)), '01033334444');
    await _settle(tester);
    slow.complete(
      const FakeResponse(
        statusCode: 200,
        data: {
          'customer_id': 7,
          'name': '김민지',
          'pet_names': ['콩이'],
        },
      ),
    );
    await _settle(tester);

    expect(find.text(AppStrings.lookupFound('김민지', ['콩이'])), findsNothing);
    expect(
      tester.widget<AppButton>(_onStage(_button(AppStrings.next))).onPressed,
      isNotNull,
    );
  });

  testWidgets('앞 단계로 돌아가도 적은 값이 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);
    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingDeclined);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepOwner, 2)),
      findsOneWidget,
    );
    expect(_onStage(find.widgetWithText(TextField, '김민지')), findsOneWidget);
  });

  testWidgets('그사이 같은 번호가 등록됐으면(CUSTOMER_PHONE_TAKEN) 문구를 보이고 남는다(C2)', (
    tester,
  ) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        register: const FakeResponse(
          statusCode: 409,
          data: {'code': 'CUSTOMER_PHONE_TAKEN', 'message': 'x'},
        ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);
    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await _fillPet(tester);

    await tester.tap(_onStage(_button(AppStrings.save)));
    await tester.pumpAndSettle();

    expect(find.text('이미 등록된 전화번호입니다.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.registerCustomer), findsOneWidget);
  });

  testWidgets('등록 3단계 골든', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).push('/customers/new');
    await tester.pumpAndSettle();
    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.petNameLabel)),
      '보리',
    );
    await _tapChip(tester, AppStrings.speciesDog);
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.registerCustomer),
      matchesGoldenFile('goldens/register_pet_step.png'),
    );
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/`에서): `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/register_customer_screen_test.dart`

Expected: 컴파일 오류 — `register_customer_screen.dart`와 `ScreenKeys.registerCustomer`가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/router/app_router.dart` (수정):

```diff
@@ -13,6 +13,7 @@ import '../../features/auth/state/session_controller.dart';
 import '../../features/customer/screens/pet_detail_screen.dart';
 import '../../features/customer/screens/pet_form_screen.dart';
 import '../../features/customer/screens/customer_edit_screen.dart';
+import '../../features/customer/screens/register_customer_screen.dart';
 import '../../features/home/screens/home_shell.dart';
 import '../../features/shop/screens/members_screen.dart';
 import '../../features/shop/screens/settings_screen.dart';
@@ -127,6 +128,10 @@ final routerProvider = Provider<GoRouter>((ref) {
           customerId: int.parse(state.pathParameters['customerId']!),
         ),
       ),
+      GoRoute(
+        path: '/customers/new',
+        builder: (context, state) => const RegisterCustomerScreen(),
+      ),
     ],
   );
```

`app/lib/core/router/screen_keys.dart` (수정):

```diff
@@ -13,6 +13,7 @@ class ScreenKeys {
   static const settingsShop = Key('screen_settings_shop');
   static const settingsAccount = Key('screen_settings_account');
   static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
+  static const registerCustomer = Key('screen_register_customer');
   static const customerEdit = Key('screen_customer_edit');
   static const petForm = Key('screen_pet_form');
   static const petDetail = Key('screen_pet_detail');
```

`app/lib/features/customer/screens/register_customer_screen.dart` (새 파일):

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../home/state/today_provider.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_input.dart';
import '../state/customer_providers.dart';
import 'customer_form.dart';
import 'pet_form.dart';

/// 새 고객 등록 — 전화번호 → 보호자 → 반려동물 3단계(설계 8.1).
///
/// 1단계에서 번호가 완성되면 바로 조회해, 이미 있는 번호면 알려 주고 그
/// 보호자에게 반려동물 추가로 건너뛰게 한다. 세 단계는 한 화면 안에서 오가며,
/// 앞 단계로 돌아가도 적은 값이 남는다.
class RegisterCustomerScreen extends ConsumerStatefulWidget {
  const RegisterCustomerScreen({super.key});

  @override
  ConsumerState<RegisterCustomerScreen> createState() =>
      _RegisterCustomerScreenState();
}

class _RegisterCustomerScreenState
    extends ConsumerState<RegisterCustomerScreen> {
  final _phone = TextEditingController();

  int _step = 0;

  /// 조회를 마친 번호와 그 결과. 번호가 바뀌면 비운다.
  String? _checkedPhone;
  CustomerLookup? _found;
  bool _checking = false;

  /// 번호 조회는 입력마다 나갈 수 있다 — 늦게 온 옛 번호의 결과를 버리려고 센다.
  int _lookupSeq = 0;

  CustomerFields? _customer;
  bool _busy = false;
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  String get _digits => phoneDigits(_phone.text);

  @override
  void initState() {
    super.initState();
    _phone.addListener(_onPhoneChanged);
  }

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  /// 마지막으로 본 입력(숫자만). 커서만 옮긴 변경은 건너뛴다.
  String _lastDigits = '';

  void _onPhoneChanged() {
    final digits = _digits;
    if (digits == _lastDigits) return;
    _lastDigits = digits;
    setState(() {
      _checkedPhone = null;
      _found = null;
      _errorText = null;
    });
    if (isValidPhone(digits)) _lookup(digits);
  }

  Future<void> _lookup(String digits) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final seq = ++_lookupSeq;
    setState(() => _checking = true);
    try {
      final found = await ref
          .read(customerCommandsProvider)
          .lookup(shopId, digits);
      if (!mounted || seq != _lookupSeq) return;
      setState(() {
        _checking = false;
        _checkedPhone = digits;
        _found = found;
      });
    } catch (e) {
      if (!mounted || seq != _lookupSeq) return;
      setState(() {
        _checking = false;
        _errorText = messageFor(e);
      });
    }
  }

  /// 1단계의 "다음". 조회가 실패했으면 다시 조회하고, 없는 번호일 때만 넘어간다.
  Future<void> _nextFromPhone() async {
    final digits = _digits;
    if (_checkedPhone != digits) {
      setState(() => _errorText = null);
      await _lookup(digits);
      if (!mounted || _checkedPhone != digits) return;
    }
    if (_found == null) setState(() => _step = 1);
  }

  Future<void> _register(PetFields pet) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final detail = await ref
          .read(customerCommandsProvider)
          .register(shopId, customer: _customer!, pet: pet);
      if (mounted) context.pushReplacement('/pets/${detail.pets.first.petId}');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  void _back() {
    if (_step == 0) {
      context.pop();
    } else {
      setState(() {
        _step--;
        _errorText = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = switch (_step) {
      0 => AppStrings.registerStepTitle(AppStrings.registerStepPhone, 1),
      1 => AppStrings.registerStepTitle(AppStrings.registerStepOwner, 2),
      _ => AppStrings.registerStepTitle(AppStrings.registerStepPet, 3),
    };

    return PopScope(
      // 시스템 뒤로 가기도 앞 단계로 돌아간다.
      canPop: _step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: Scaffold(
        key: ScreenKeys.registerCustomer,
        body: AppBackground(
          child: SafeArea(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.lg,
                    AppSpacing.sm,
                    AppSpacing.lg,
                    0,
                  ),
                  child: Row(
                    children: [
                      AppBackButton(onTap: _back),
                      const SizedBox(width: AppSpacing.sm),
                      Text(title, style: AppTypography.titleKo),
                    ],
                  ),
                ),
                Expanded(
                  // 단계를 오가도 폼의 입력이 남도록 세 단계를 모두 쥐고 있는다.
                  child: IndexedStack(
                    index: _step,
                    children: [_phoneStep(), _ownerStep(), _petStep()],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _phoneStep() {
    final found = _found;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _phone,
            autofocus: true,
            keyboardType: TextInputType.phone,
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'[0-9\- ]')),
              LengthLimitingTextInputFormatter(20),
            ],
            decoration: const InputDecoration(
              labelText: AppStrings.ownerPhoneLabel,
              hintText: AppStrings.phoneHint,
            ),
          ),
          if (_checking) ...[
            const SizedBox(height: AppSpacing.md),
            const LinearProgressIndicator(),
          ],
          if (found != null) ...[
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              width: double.infinity,
              child: AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppStrings.lookupFound(found.name, found.petNames),
                      style: AppTypography.body,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    AppButton(
                      label: AppStrings.addPetToExisting,
                      filled: true,
                      onPressed: () => context.pushReplacement(
                        '/customers/${found.customerId}/pets/new',
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (_step == 0 && _errorText != null) ...[
            const SizedBox(height: AppSpacing.md),
            Text(_errorText!, style: AppTypography.caption),
          ],
          const SizedBox(height: AppSpacing.xl),
          Center(
            child: AppButton(
              label: AppStrings.next,
              filled: true,
              busy: _checking,
              onPressed: isValidPhone(_digits) && found == null && !_checking
                  ? _nextFromPhone
                  : null,
            ),
          ),
        ],
      ),
    );
  }

  Widget _ownerStep() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: CustomerForm(
        fixedPhone: _checkedPhone ?? _digits,
        submitLabel: AppStrings.next,
        busy: false,
        onSubmit: (fields) => setState(() {
          _customer = fields;
          _step = 2;
        }),
      ),
    );
  }

  Widget _petStep() {
    final shopId = _shopId;
    if (shopId == null) return const SizedBox.shrink();
    return ref
        .watch(conditionTypesProvider(shopId))
        .when(
          data: (types) => SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: PetForm(
              conditionTypes: types,
              today: ref.watch(todayProvider),
              submitLabel: AppStrings.save,
              busy: _busy,
              errorText: _step == 2 ? _errorText : null,
              onSubmit: _register,
            ),
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(messageFor(error), style: AppTypography.body),
                const SizedBox(height: AppSpacing.lg),
                AppButton(
                  label: AppStrings.retry,
                  onPressed: () =>
                      ref.invalidate(conditionTypesProvider(shopId)),
                ),
              ],
            ),
          ),
        );
  }
}
```

`app/lib/features/home/screens/home_shell.dart` (수정):

```diff
@@ -61,7 +61,12 @@ class _HomeShellState extends ConsumerState<HomeShell> {
     return Scaffold(
       key: ScreenKeys.home,
       extendBody: true,
-      floatingActionButton: AppFab(onPressed: _openComingSoonSheet),
+      floatingActionButton: _tabIndex == _customersTab
+          ? AppFab(
+              semanticLabel: AppStrings.registerCustomer,
+              onPressed: () => context.push('/customers/new'),
+            )
+          : AppFab(onPressed: _openComingSoonSheet),
       bottomNavigationBar: Padding(
         padding: const EdgeInsets.fromLTRB(
           AppSpacing.lg,
```

`app/lib/l10n/app_strings.dart` (수정):

```diff
@@ -211,6 +211,18 @@ class AppStrings {
   static const deleteCustomer = '고객 삭제';
   static const deleteCustomerConfirm = '고객을 삭제할까요? 보호자의 이름·전화번호·메모와 반려동물의 이름·질병 기록이 지워지고 되돌릴 수 없습니다.';
 
+  static const registerCustomer = '고객 등록';
+  static const registerStepPhone = '전화번호';
+  static const registerStepOwner = '보호자';
+  static const registerStepPet = '반려동물';
+  static const next = '다음';
+  static const addPetToExisting = '이 보호자에게 반려동물 추가';
+
+  static String registerStepTitle(String step, int index) => '$step $index / 3';
+  static String lookupFound(String name, List<String> petNames) => petNames.isEmpty
+      ? '이미 등록된 번호예요 — $name'
+      : '이미 등록된 번호예요 — $name (${petNames.join(', ')})';
+
   /// 로그인 수단 제공자 코드를 화면에 보여줄 라벨로 바꾼다. 계정 화면과
   /// 재인증 시트(Task 16)가 함께 쓴다.
   static String providerLabel(String provider) => switch (provider) {
```

- [ ] **Step 4: 골든을 만들고 눈으로 확인한다**

Run: `flutter test --update-goldens test/features/customer/screens/register_customer_screen_test.dart`

만들어지는 파일: `app/test/features/customer/screens/goldens/register_pet_step.png`

Read 도구로 이미지를 열어 확인한다: `register_pet_step.png`(390×844) — 머리 '반려동물 3 / 3', 이름 '보리', 종류 칩(강아지 검정), 품종 칸과 강아지 품종 추천 칩이 **글자 폭만큼씩 여러 줄로**(한 줄에 칩 하나씩 전체 폭이면 Task 1 의 `widthFactor`가 빠진 것이다), 성별·중성화 칩, 나이 칩, 몸무게, 질병 칩(슬개골 탈구·심장 질환·피부병·+ 기타·질병 없음).

- [ ] **Step 5: 통과를 확인한다**

Run: `flutter test test/design/glass_boundary_test.dart test/features/customer/screens/register_customer_screen_test.dart` → Expected: `+8: All tests passed!`

Run: `flutter analyze` → Expected: `No issues found!`

Run: `flutter test` → Expected: `+327: All tests passed!`

- [ ] **Step 6: 판별력을 확인한다(변이)**

아래를 하나씩 바꿔 해당 테스트가 **실패하는지** 보고, `git checkout -- <파일>`로 되돌린다(새 파일이면 에디터로 되돌린다). 실패하지 않으면 보고한다.

- `register_customer_screen.dart`의 조회 성공 갈래 `if (!mounted || seq != _lookupSeq) return;`을 `if (!mounted) return;`으로 바꾼다 → `번호를 바꾸면 늦게 온 옛 번호의 조회 결과를 버린다` 실패

- [ ] **Step 7: 커밋한다**

```bash
git add app/lib/core/router/app_router.dart app/lib/core/router/screen_keys.dart app/lib/features/customer/screens/register_customer_screen.dart app/lib/features/home/screens/home_shell.dart app/lib/l10n/app_strings.dart app/test/design/glass_boundary_test.dart app/test/features/customer/screens/goldens/register_pet_step.png app/test/features/customer/screens/register_customer_screen_test.dart
git commit -m "feat(app): 고객 등록 3단계와 번호 조회, 고객 탭의 + 버튼

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: 시뮬레이터 흐름 확인과 결정 기록 005 의 앱 몫

**Files:**
- Modify: `_docs/decisions/005-customer-pet.md`

**Interfaces:**
- Consumes: Task 1~10 의 앱 전체, `infra/`의 개발 환경(게이트웨이 `http://127.0.0.1:8080`), `app/tool/run_dev.sh`
- Produces: 결정 기록 005 의 "②-2 앱" 절들

**알아 둘 것:**
- 설계 10절의 완료 기준은 **시뮬레이터에서 사용자와 함께** 확인하는 것이다. 이 작업은 서브에이전트가 아니라 컨트롤러(메인 세션)가 사용자와 한다. 사용자가 앱을 조작하고, 컨트롤러는 터미널 쪽(백엔드 기동, 계정·매장 준비, 로그 확인)을 맡는다(결정 기록 004 와 같은 방식).
- 시뮬레이터는 Xcode → Open Developer Tool → Device Hub 에서 연다(Xcode 27 에는 Simulator.app 이 없다).
- 결정 기록 004 에 적힌 대로 시뮬레이터는 맥의 한글 입력기를 넘기지 않는다. **한글 검색(초성·조합)은 시뮬레이터의 iOS 소프트웨어 키보드에 한국어 자판을 더해 확인한다**(설정 → 일반 → 키보드 → 키보드 → 새로운 키보드 추가 → 한국어).
- 흐름 중 결함이 나오면 고치고(테스트를 먼저 더한다) 커밋한 뒤 그 단계부터 다시 확인한다. 고친 것은 결정 기록의 "검토에서 고친 것"에 적는다.

- [ ] **Step 1: 전체 검증**

Run (`app/`에서): `flutter analyze` → `No issues found!`, `flutter test` → `+327: All tests passed!`(Task 11 전에 고친 것이 있으면 그만큼 더해진 수)

Run (저장소 루트에서): `git diff --stat main -- backend infra` → 빈 출력(이 계획은 백엔드를 바꾸지 않는다)

- [ ] **Step 2: 개발 환경을 띄우고 확인한다**

Run (`infra/`에서): `docker compose up -d` 뒤 `docker compose ps` → 여섯 서비스 `running`

Run: `docker compose run --rm backend alembic current` → `0005 (head)`. 아니면 멈추고 보고한다(②-1 Task 16 에서 올렸어야 한다).

Run (`infra/`에서 — 스크립트가 `docker compose`로 운영자를 지정한다): `bash ../backend/scripts/check_customer_flow.sh` → 마지막 줄까지 통과(게이트웨이 경유 API 계약 확인 — 개발 DB 에 확인용 매장·유저와 익명화한 고객이 남는다).

- [ ] **Step 3: 시뮬레이터 흐름 확인(사용자와 함께)**

앱을 띄운다: `app/tool/run_dev.sh`(iPhone 시뮬레이터). 사장 계정(`owner1` 개발용 로그인 — 결정 기록 004 의 흐름에서 만든 매장이 있으면 그대로, 없으면 운영자 지정·매장 개설을 004 와 같은 방식으로 컨트롤러가 준비)과 직원 계정(`staff1`)을 쓴다.

설계 10절 완료 기준을 차례로 확인하고, 단계마다 통과·실패와 본 것을 적는다.

1. 고객 탭 → 비어 있으면 "등록된 고객이 없어요" → + 버튼 → 등록 1단계. 새 번호(`010-…`)를 치면 조회가 나가고 [다음]이 켜진다.
2. 보호자(이름, 수신 [동의]) → 반려동물(이름, 강아지, 품종 추천 칩, 여아, 중성화, 생일 `YYYY.MM.DD`, 몸무게, 슬개골 탈구 + 메모) → 저장 → 새 아이의 상세. 뒤로 → 고객 탭에 가족 카드.
3. 같은 번호로 다시 등록 → "이미 등록된 번호예요 — 이름 (아이)" → [이 보호자에게 반려동물 추가] → 고양이, 태어난 해, 질병 없음 → 저장 → 상세의 "같은 보호자의 아이"에 첫째가 보인다.
4. 고객 탭에서 [☰ / ▦] 전환 → 격자. 앱을 완전히 껐다 켜도 격자로 시작한다. [최근순 / 가나다순] 전환.
5. 검색: 번호 뒷자리 4자리, 두 자리(치는 중), 보호자 이름, 반려동물 초성(`ㅋㅇ` 등 — 한국어 자판으로). **조합 중에는 요청이 나가지 않고, 조합이 끝나고 0.3초 뒤 한 번 나가는지 본다**(컨트롤러가 `infra/`에서 `docker compose logs -f backend`로 요청을 센다 — 쿼리는 `?[가림]`으로 찍힌다). 마지막 글자가 조합 중으로 남아 검색이 나가지 않으면 **멈추고 사용자에게 묻는다**(설계 8.2 를 바꾸는 일이다).
6. 반려동물 상세의 [질병] 탭(항목·메모), [보호자] 탭(전체 번호·보조 연락처·수신 동의·메모) → [수정] → 몸무게를 바꿔 저장 → 상세에 반영.
7. [보호자 수정] → 번호를 바꿔 저장. 다른 고객의 번호로 바꾸면 "이미 등록된 전화번호입니다."
8. ⋯ → [무지개다리 표시] → 확인 → "무지개다리" 칩. 고객 탭의 기본 목록에서 그 아이가 사라지고, [무지개다리 포함]을 켜면 보인다. ⋯ → [무지개다리 되돌리기].
9. ⋯ → [반려동물 삭제] → 둘째를 지운다. 마지막 한 마리를 지우려 하면 "마지막 반려동물은 삭제할 수 없습니다. 고객 삭제를 이용해 주세요."
10. 사장: [보호자 수정] → 맨 아래 [고객 삭제] → 확인 → 고객 탭으로 돌아오고, 그 번호·이름·아이 이름으로 검색해도 나오지 않는다.
11. 직원(`staff1`)으로 로그인 → 같은 매장 → 보호자 수정 화면에 [고객 삭제]가 없다. 직원도 등록·수정·무지개다리·반려동물 삭제는 된다.
12. 화면 모양: 목록·폼·시트가 불투명 흰 카드이고 글자가 또렷하다, 키보드가 올라와도 폼의 입력 칸이 가려지지 않는다, 모든 하위 화면에 뒤로 가기가 있다.

- [ ] **Step 4: 결정 기록 005 에 앱 몫을 더한다**

`_docs/decisions/005-customer-pet.md`의 머리말 "대상 브랜치" 줄을 `feat/customer-2a-backend` (②-1 백엔드), `feat/customer-2b-app` (②-2 앱)으로 고치고, "근거"에 이 계획서(`docs/superpowers/plans/2026-09-22-customer-2b-app.md`)를 더한다. 문서 끝(“남는 것 — 알고 미룬다” 절 뒤)에 아래 절들을 더한다. 대괄호 안은 실행하며 나온 사실로 채운다 — 없으면 그 줄을 뺀다.

```markdown
## 무엇을 만들었나 (②-2)

`app/lib/features/customer/{api,state,screens}`로 홈의 "고객" 탭을 채웠다. 가족 카드 목록(목록·격자, 최근순·가나다순, 무지개다리 포함, 검색 — 한글 조합이 끝난 뒤 0.3초, 다음 페이지), 등록 3단계(번호가 완성되면 조회, 이미 있는 번호면 반려동물 추가로), 반려동물 상세(탭 [기본 / 질병 / 보호자], 형제 이동, 무지개다리, 삭제), 반려동물 추가·수정, 보호자 수정, 고객 삭제(사장만). 라우트 다섯 개(`/customers/new`, `/customers/:id/edit`, `/customers/:id/pets/new`, `/pets/:id`, `/pets/:id/edit`)는 매장이 선택되어 있어야 열린다. 위젯 두 개(`AppChoiceChip`·`AppIconToggle`)를 `design/widgets`에 더했고 `Pressable`에 `selected`를 더했다. 새 의존성은 없다. 테스트 [N]개(기준 240), 골든 6장(선택 칩·아이콘 토글·반려동물 상세·고객 탭 목록·격자·등록 3단계).

## 앱에서 새로 정한 것

[계획서 "이 계획에서 새로 정한 것" 16개를 한 줄씩 옮긴다. 실행 중 바뀐 것이 있으면 바뀐 대로 적는다.]

## 시뮬레이터 흐름 확인 (②-2)

[날짜, 기기(iPhone … 시뮬레이터, iOS …), 계정. Step 3 의 12단계를 번호대로 "통과" 또는 무엇을 보고 무엇을 고쳤는지. 한글 입력기의 조합 구간이 검색 지연과 어떻게 맞물렸는지를 따로 한 문단으로.]

## 검토에서 고친 것 (②-2)

[작업별 검토와 최종 검토, 시뮬레이터 흐름에서 잡아 고친 것을 작업 순서대로.]

## 남는 것 — 알고 미룬다 (②-2)

- 폼 화면(반려동물 추가·수정, 등록)의 `_busy` 가드는 저장 버튼 비활성과 겹쳐 테스트로 따로 판별되지 않는다.
- 설정(톱니) 버튼은 캘린더·매출 탭 머리에만 있다 — 고객 탭은 목업대로 자기 머리를 쓴다.
- 생일은 글자 입력이다(날짜 선택기는 `flutter_localizations`가 들어올 때 다시 본다).
- 오프라인·목록 캐시가 없다(설계 3.2).
- [흐름 확인과 검토에서 미룬 것.]
```

- [ ] **Step 5: 커밋한다**

```bash
git add _docs/decisions/005-customer-pet.md
git commit -m "docs(customer): 결정 기록 005 에 ②-2 앱 몫과 시뮬레이터 흐름 확인을 더한다

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: 브랜치 마무리**

superpowers:finishing-a-development-branch 를 따른다. 머지·푸시는 사용자가 고른다.
