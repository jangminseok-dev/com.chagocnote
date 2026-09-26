# 차곡노트 — 오류 화면 다듬기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 오류를 원인(인터넷 없음·서버·권한·없음·그 밖)별 문구와 행동으로 보이고, 받은 데이터는 두고 위에 얇은 띠, 인터넷이 돌아오면 보이는 화면이 스스로 다시 불러오며, 목록·상세는 당겨서 새로고침, 업로드 대기열은 다시 해도 안 되는 실패에서 멈춰 [다시 시도]·[올리기 취소]를 준다. 앱 문구는 해요체다.

**Architecture:** 열 작업이다. ① 원인 분류 `ErrorKind`와 문구(`messageFor` 누른 일 / `loadMessageFor` 불러오기) ② 화면 문구 해요체 ③ 모양 위젯 `AppErrorBanner`·`AppErrorRetry`의 [돌아가기] ④ Riverpod 을 아는 화면 본문 틀 `AsyncBody`(`core/error/async_body.dart`) ⑤ 목록 화면 ⑥ 상세 화면 ⑦ 폼·설정 화면과 구조 테스트 ⑧ 스플래시 ⑨ 대기열 멈춤 ⑩ 시뮬레이터 흐름과 문서. 서버는 바꾸지 않는다. 모든 코드는 참조 작업 트리(`.superpowers/ref/wt-error-polish`, 브랜치 `ref/error-polish`, 커밋 7dba9ec…dea05c2)에서 먼저 돌렸다 — 커밋마다 `flutter analyze` 0·테스트 초록, 작업마다 변이로 판별력 확인, 시뮬레이터(iOS 27, 실서버)에서 확인 넷 통과.

**Tech Stack:** Flutter 3.44 · Riverpod 3 · go_router · dio · connectivity_plus(이미 있음). **새 의존성 없음.**

**Spec:** `docs/superpowers/specs/2026-09-26-error-polish-design.md` — 2절(원인·문구·[돌아가기]·해요체), 3절(`AsyncBody`·띠·자동 다시 불러오기·당겨서 새로고침·다음 쪽·폼·구조 테스트), 4절(대기열 멈춤), 5절(스플래시), 6절(④-0 에서 모양이 바뀐 세 곳), 7절(검증). 실행자는 `app/CLAUDE.md`, `_docs/harness.md`, `_docs/decisions/007-record-media.md`(④-2a·④-2b 절)를 함께 읽는다.

**계획의 위치:** ④ 설계 14절이 ④-2 뒤로 미룬 작은 계획이다. ④-2b(main ad12d88) → 안드로이드 흐름 도구(8df7552) → **오류 화면 다듬기(이 문서)** → ④-3 영상·음성.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 앱 명령은 `app/`에서, 준비 스크립트는 `infra/`에서 돌린다.
- 작업 브랜치는 `feat/error-polish`다(`main` `8df7552`에서 땄고, 설계 커밋 e3f4be2 와 이 계획서 커밋이 앞에 있다). `main`에서 직접 작업하지 않는다.
- **사용자가 작업 단위 커밋을 허용했다(2026-09-22 이후 계속).** 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.**
- 계획서의 코드 블록은 그대로 옮긴다. 새 파일은 전문이고, 수정 파일은 diff 다. diff 가 적용되지 않으면 멈추고 보고한다 — 손으로 "비슷하게" 고치지 않는다.
- **`dart format`을 돌리지 않는다**(새 파일도). 계획 본문이 이미 참조 트리의 모양이고, 뒤 작업이 앞 작업의 파일을 diff 로 고친다.
- **변이 검사는 편집으로 넣고 편집으로 되돌린다.** `git checkout -- <파일>`로 되돌리지 않는다 — 커밋 전 수정이 함께 날아간다(참조 구현에서 겪었다). 같은 글이 파일에 여러 번 나오면 되돌리기가 엉뚱한 곳을 고친다 — 원문을 통째로 저장해 두었다가 되쓴다. 골든이 실패하면 `test/**/failures/`에 png 가 남는다 — 커밋 전에 지운다.
- 골든은 이 계획이 만드는 하나(`test/design/goldens/app_error_banner.png`)뿐이다. 그 밖의 골든이 실패하면 코드가 계획과 다른 것이니 `--update-goldens`를 돌리지 말고 멈추고 보고한다(참조 구현에서는 해요체로 바뀐 문구가 찍힌 골든이 없었다).
- 비밀값·토큰·고객 개인정보를 로그에 남기지 않는다. 앱 코드에 `print`·`debugPrint`·dio `LogInterceptor`를 쓰지 않는다(흐름 테스트의 `debugPrint`는 기존 흐름과 같다).
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (`app/CLAUDE.md` — 작업 10 이 더하는 규칙 포함)
- 웹뷰 금지. 기능 폴더 안은 `screens/`·`state/`·`api/` 세 층뿐. 기능 폴더 import 는 `auth` 공용·`home` 껍데기·`visit → customer`만(`test/design/feature_imports_test.dart`). customer 는 visit 를 import 하지 않는다 — 반려동물 상세가 [기록] 탭을 다시 읽게 하는 것도 `core/plugs` 자리로 한다(작업 6).
- `design/widgets`는 Riverpod 을 모르는 모양 위젯만 둔다 — `AppErrorBanner`는 여기, Riverpod 을 아는 `AsyncBody`는 `core/error/`.
- 플러그인은 `core/proxy/`의 프로바이더로만 — 인터넷 복귀 신호는 `networkWatcherProvider`. 테스트에는 연결 상태 플러그인이 없다 — 복귀 신호는 오류가 인터넷 없음인 동안만 듣고, 공용 테스트 준비물이 `FakeNetworkWatcher`를 끼운다(작업 4).
- 누른 일(저장·삭제)의 실패는 지금처럼 화면의 문구·스낵바로 보인다 — 쓰던 내용을 지우지 않는다. `AsyncBody`는 불러오기만 다룬다.
- 앱 문구는 해요체다(작업 2 의 구조 테스트). 서버 문구는 바꾸지 않는다.

검증 명령 (`app/`에서)
- 정적 분석: `flutter analyze` → `No issues found!`(info 도 0)
- 테스트: `flutter test --timeout 60s` — 시작 660 → 끝 698. 골든 포함.
- 파일 몇 개만: `flutter test --timeout 60s <경로들>`
- 시뮬레이터 흐름: 작업 10(`_docs/harness.md`의 "앱 흐름 확인" 행)
- 참조 브랜치와 대조(선택, 마지막에): `git diff ref/error-polish -- app _docs` 가 비어 있어야 한다.

## 이 계획에서 새로 정한 것

설계와 다른 것과 새로 정한 것은 결정 기록 007 의 "오류 화면 다듬기에서 정한 것" 절(작업 10)에 적는다. 요약:
- 문구 함수는 인자 하나가 아니라 이름 둘 — `messageFor`(누른 일, 부르는 곳 그대로) / `loadMessageFor`(불러오기). 인터넷 없음 문구만 다르다.
- 복귀 신호는 오류가 인터넷 없음인 동안만 듣는다(`AsyncBody`와 두 목록 컨트롤러). `AsyncBody.inline`의 `placeholder`(달력 빈 칸, 스플래시 앱 이름).
- 여럿을 기다리는 폼은 `AsyncValue<void>` 하나로 묶는다. 기록 화면은 한 번 채운 뒤 다시 읽기가 실패해도 폼을 남긴다.
- 반려동물 상세의 당기기가 [기록] 탭도 다시 읽게 `core/plugs`의 `petRecordsRefreshPlugProvider`(기본은 아무것도 안 함) ← visit 의 `petRecordsRefresher`.
- 대기열의 멈춤 판정 `stopsUpload`: 권한·없음·업무 4xx(401·429 제외), `MEDIA_NOT_FOUND`는 예전처럼 재발급. 멈춘 이유는 `queue.json`의 `stopped_code`.
- 한 줄 자리(휴무일 목록·시간 칸)와 달력 미리보기는 원인 문구만 — 스스로 다시 부르지 않는다.
- 시뮬레이터 흐름은 API `Dio`에 스위치를 끼워 연결 실패·503 을 흉내 낸다(네이티브 `flutter drive`는 흐름 도중 맥과 주고받지 못한다).

## Review Focus

설계가 말하지만 화면만 봐서는 드러나지 않는 입력 다섯. 각 줄의 테스트를 해당 작업에 넣었다.
1. **서버 오류로 실패한 화면에 인터넷 복귀 신호가 오는 경우** — 원인이 인터넷이 아니었으니 스스로 다시 부르면 안 된다(요청 폭주) → 작업 4 `async_body_test.dart::서버 오류로 실패하면 인터넷이 돌아와도 스스로 다시 부르지 않는다`, 작업 5 `feed_controller_test.dart::…서버 오류면 부르지 않는다`.
2. **뒤로 갈 곳이 없는 탭 화면에서 권한·없음 오류** — [돌아가기]가 없어야 한다(누르면 앱이 닫히거나 아무 일도 없다) → 작업 4 `async_body_test.dart::뒤로 갈 곳이 없으면(탭 화면) 없어진 것은 문구만 보인다`.
3. **기록을 쓰던 중 다시 읽기가 실패하는 경우(409 뒤)** — 쓰던 폼이 오류 화면으로 바뀌면 안 된다 → 작업 7 `record_screen_test.dart::어긋나 다시 읽는데 그것마저 실패해도 쓰던 폼은 남고 문구만 보인다`.
4. **세션이 만료된 사이(401)·잦은 시도(429)로 대기열이 실패하는 경우** — 멈추면 사진이 영영 안 올라간다 → 작업 9 `upload_queue_test.dart::다시 해도 안 되는 실패는 권한·없음·업무 4xx 다 — 인터넷·서버·세션 만료·잦은 시도는 다시 해 본다`.
5. **멈춤 칸이 없던 옛 `queue.json`을 새 앱이 읽는 경우(앱 갱신)** — 옛 항목은 멈추지 않은 것으로 이어 올려야 한다 → 작업 9 `upload_queue_test.dart::멈춘 항목은 앱을 다시 켜도 멈춰 있고, 멈춤 칸이 없던 옛 항목은 그대로 올린다`.

---

### Task 1: 오류 원인 분류(`ErrorKind`)와 원인별 문구 — 누른 일용 `messageFor`, 불러오기용 `loadMessageFor`, 오류 문구 해요체

**Files:**
- Create: `app/lib/core/error/error_kind.dart`
- Modify: `app/lib/core/error/error_messages.dart`
- Create: `app/test/core/error/error_kind_test.dart`
- Modify: `app/test/core/error/error_messages_test.dart`
- Modify: `app/integration_test/visit_flow_test.dart`
- Modify: `app/test/features/account/screens/account_screen_test.dart`
- Modify: `app/test/features/account/screens/reauth_sheet_test.dart`
- Modify: `app/test/features/account/screens/withdraw_screen_test.dart`
- Modify: `app/test/features/auth/screens/invite_code_screen_test.dart`
- Modify: `app/test/features/auth/screens/login_screen_test.dart`
- Modify: `app/test/features/auth/screens/splash_screen_test.dart`
- Modify: `app/test/features/customer/screens/customer_edit_screen_test.dart`
- Modify: `app/test/features/customer/screens/pet_form_screen_test.dart`
- Modify: `app/test/features/customer/screens/register_customer_screen_test.dart`
- Modify: `app/test/features/shop/screens/members_screen_test.dart`
- Modify: `app/test/features/visit/screens/photo_viewer_screen_test.dart`
- Modify: `app/test/features/visit/screens/record_screen_test.dart`
- Modify: `app/test/features/visit/screens/register_visit_screen_test.dart`
- Modify: `app/test/features/visit/screens/settings/menu_settings_screen_test.dart`
- Modify: `app/test/features/visit/screens/settings/schedule_settings_screen_test.dart`
- Modify: `app/test/features/visit/screens/visit_detail_screen_test.dart`

**Interfaces:**
- Consumes: `core/error/api_exception.dart`의 `ApiException(statusCode, code, message)`·`isNetwork`.
- Produces: `core/error/error_kind.dart` — `enum ErrorKind { offline, server, denied, gone, other }`와 `bool get retryable`(denied·gone 만 false), `ErrorKind kindOf(Object error)`(NETWORK → offline, 5xx 또는 `HTTP_ERROR` → server, 403 → denied, 404 → gone, 나머지·`ApiException` 아님 → other). `core/error/error_messages.dart` — `String messageFor(Object)`(누른 일), `String loadMessageFor(Object)`(화면 불러오기), 상수 `offlineActionMessage`·`offlineLoadMessage`. 모든 오류 문구는 해요체.

설계 2절. 원인은 서버 코드와 상태 번호만으로 가른다(서버는 바꾸지 않는다). 인터넷 없음과 서버 오류는 원인 문구를, 나머지는 코드별 문구를 쓴다. 설계는 `messageFor(error, forAction: true)` 꼴 인자를 말했지만, 누른 일의 문구를 쓰는 곳이 서른다섯 곳이라 이름을 둘로 나눴다 — `messageFor`는 그대로 누른 일, 새 `loadMessageFor`가 불러오기(결정 기록 007, 작업 10). 문구가 바뀌어 기존 테스트 열아홉 파일의 기대 문구도 함께 바꾼다(503 으로 흉내 낸 곳은 이제 서버 문구다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/core/error/error_kind_test.dart`:

```dart
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_kind.dart';
import 'package:flutter_test/flutter_test.dart';

ApiException _error(String code, int? status) =>
    ApiException(statusCode: status, code: code, message: '서버 문구');

void main() {
  test('인터넷 없음·시간 초과는 offline 이다', () {
    expect(kindOf(ApiException.network('timeout')), ErrorKind.offline);
  });

  test('5xx 와 형식을 모르는 응답은 server 다', () {
    expect(kindOf(_error('INTERNAL', 500)), ErrorKind.server);
    expect(kindOf(_error('HTTP_ERROR', 502)), ErrorKind.server);
    expect(kindOf(_error('HTTP_ERROR', 413)), ErrorKind.server);
  });

  test('403 은 denied, 404 는 gone 이다 — 다시 해도 같다', () {
    expect(kindOf(_error('PERMISSION_DENIED', 403)), ErrorKind.denied);
    expect(kindOf(_error('VISIT_NOT_FOUND', 404)), ErrorKind.gone);
    expect(ErrorKind.denied.retryable, isFalse);
    expect(ErrorKind.gone.retryable, isFalse);
  });

  test('업무 규칙 4xx 와 ApiException 이 아닌 오류는 other 다', () {
    expect(kindOf(_error('VISIT_STATE_CONFLICT', 409)), ErrorKind.other);
    expect(kindOf(_error('VALIDATION_ERROR', 422)), ErrorKind.other);
    expect(kindOf(StateError('x')), ErrorKind.other);
    for (final kind in [ErrorKind.offline, ErrorKind.server, ErrorKind.other]) {
      expect(kind.retryable, isTrue, reason: kind.name);
    }
  });
}
```

`app/test/core/error/error_messages_test.dart`:

```diff
@@ -7,14 +7,14 @@ ApiException _error(String code, {String message = '서버 문구', int? status
 
 void main() {
   test('아는 코드는 서버 문구가 아니라 앱의 문구를 쓴다', () {
-    expect(messageFor(_error('INVITE_EXPIRED')), '만료된 초대 코드입니다. 새 코드를 받아 주세요.');
+    expect(messageFor(_error('INVITE_EXPIRED')), '만료된 초대 코드예요. 새 코드를 받아 주세요.');
     expect(messageFor(_error('REAUTH_REQUIRED', status: 403)), '보안을 위해 다시 로그인해 주세요.');
   });
 
   test('IDENTITY_ALREADY_LINKED 는 그 계정에서 탈퇴한 뒤 다시 연결하라고 안내한다(설계 5.6)', () {
     expect(
       messageFor(_error('IDENTITY_ALREADY_LINKED', status: 409)),
-      '다른 계정에 연결된 로그인 수단입니다. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
+      '다른 계정에 연결된 로그인 수단이에요. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
     );
   });
 
@@ -22,14 +22,27 @@ void main() {
     expect(messageFor(_error('SOMETHING_NEW', message: '새로 생긴 안내')), '새로 생긴 안내');
   });
 
-  test('형식을 모르는 응답과 예외가 아닌 오류는 일반 문구다', () {
-    const fallback = '문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.';
-    expect(messageFor(_error('HTTP_ERROR', message: '상태 코드 500 응답을 처리할 수 없습니다.')), fallback);
+  test('예외가 아닌 오류와 문구가 빈 오류는 일반 문구다', () {
+    const fallback = '문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.';
     expect(messageFor(StateError('x')), fallback);
+    expect(messageFor(_error('SOMETHING_NEW', message: '')), fallback);
   });
 
-  test('네트워크 오류는 다시 시도를 안내한다', () {
-    expect(messageFor(ApiException.network('timeout')), contains('다시 시도'));
+  test('서버 오류(5xx·형식을 모르는 응답)는 서버 문구다', () {
+    const server = '서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.';
+    expect(messageFor(_error('HTTP_ERROR', message: '상태 코드 502 응답을 처리할 수 없습니다.', status: 502)), server);
+    expect(messageFor(_error('INTERNAL', status: 500)), server);
+    expect(loadMessageFor(_error('INTERNAL', status: 500)), server);
+  });
+
+  test('인터넷 없음은 누른 일이면 연결 확인을, 화면을 불러올 때면 스스로 다시 불러온다고 안내한다', () {
+    expect(messageFor(ApiException.network('timeout')), '인터넷에 연결되지 않았어요. 연결을 확인해 주세요.');
+    expect(loadMessageFor(ApiException.network('timeout')), '인터넷에 연결되지 않았어요. 연결되면 다시 불러올게요.');
+  });
+
+  test('권한·없음·업무 오류는 불러올 때도 코드별 문구다', () {
+    expect(loadMessageFor(_error('VISIT_NOT_FOUND', status: 404)), '방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.');
+    expect(loadMessageFor(_error('PERMISSION_DENIED', status: 403)), '이 작업을 할 권한이 없어요.');
   });
 
   test('설계 문서 7절의 코드는 모두 앱의 문구가 있다', () {
```

`app/integration_test/visit_flow_test.dart`:

```diff
@@ -643,8 +643,8 @@ void main() {
       await tap(btn(AppStrings.actionNoShow));
       await waitFor(find.text(AppStrings.noShowConfirm));
       await tap(btn(AppStrings.actionNoShow), last: true);
-      await waitFor(find.textContaining('아직 할 수 없습니다'));
-      note('시각 전 노쇼 문구 = ${find.textContaining('아직 할 수 없습니다').evaluate().map((e) => (e.widget as Text).data).first}');
+      await waitFor(find.textContaining('아직 할 수 없어요'));
+      note('시각 전 노쇼 문구 = ${find.textContaining('아직 할 수 없어요').evaluate().map((e) => (e.widget as Text).data).first}');
       await shot('05c-noshow-not-yet');
       expect(chip(AppStrings.statusReserved), findsWidgets);
     });
```

`app/test/features/account/screens/account_screen_test.dart`:

```diff
@@ -302,7 +302,7 @@ void main() {
     await tester.pumpAndSettle();
 
     expect(
-      find.text('다른 계정에 연결된 로그인 수단입니다. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.'),
+      find.text('다른 계정에 연결된 로그인 수단이에요. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.'),
       findsOneWidget,
     );
   });
@@ -328,7 +328,7 @@ void main() {
     await tester.tap(_confirmUnlinkButton);
     await tester.pumpAndSettle();
 
-    expect(find.text('마지막 로그인 수단은 해제할 수 없습니다.'), findsOneWidget);
+    expect(find.text('마지막 로그인 수단은 해제할 수 없어요.'), findsOneWidget);
     expect(gateway.refreshMeCallCount, 0);
   });
```

`app/test/features/account/screens/reauth_sheet_test.dart`:

```diff
@@ -54,6 +54,6 @@ void main() {
     expect(tester.takeException(), isNull);
     expect(apple.signInCallCount, 1);
     expect(find.text(AppStrings.reauthPromptTitle), findsOneWidget);
-    expect(find.text('문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.'), findsOneWidget);
+    expect(find.text('문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.'), findsOneWidget);
   });
 }
```

`app/test/features/account/screens/withdraw_screen_test.dart`:

```diff
@@ -341,7 +341,7 @@ void main() {
     await tester.tap(_submitButton);
     await tester.pumpAndSettle();
 
-    expect(find.text('혼자 사장인 매장에 다른 멤버가 있습니다. 먼저 다른 사장을 지정해 주세요.'), findsOneWidget);
+    expect(find.text('혼자 사장인 매장에 다른 멤버가 있어요. 먼저 다른 사장을 지정해 주세요.'), findsOneWidget);
     expect(find.text(AppStrings.goToMembers), findsOneWidget);
     expect(setup.adapter.requests, hasLength(1));
   });
```

`app/test/features/auth/screens/invite_code_screen_test.dart`:

```diff
@@ -152,7 +152,7 @@ void main() {
     await tester.pumpAndSettle();
 
     expect(find.byKey(ScreenKeys.invite), findsOneWidget);
-    expect(find.text('만료된 초대 코드입니다. 새 코드를 받아 주세요.'), findsOneWidget);
+    expect(find.text('만료된 초대 코드예요. 새 코드를 받아 주세요.'), findsOneWidget);
   });
 
   testWidgets('빈 코드로 제출하면 요청 없이 검증만 한다', (tester) async {
```

`app/test/features/auth/screens/login_screen_test.dart`:

```diff
@@ -145,7 +145,7 @@ void main() {
     await tester.pump();
     await tester.pump();
 
-    expect(find.text('로그인 정보를 확인하지 못했습니다. 다시 시도해 주세요.'), findsOneWidget);
+    expect(find.text('로그인 정보를 확인하지 못했어요. 다시 시도해 주세요.'), findsOneWidget);
     expect(find.text(AppStrings.continueWithKakao), findsOneWidget);
   });
```

`app/test/features/auth/screens/splash_screen_test.dart`:

```diff
@@ -33,7 +33,7 @@ void main() {
     await tester.pumpWidget(_appWith(container));
     await tester.pumpAndSettle();
 
-    expect(find.text('문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.'), findsOneWidget);
+    expect(find.text('문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.'), findsOneWidget);
     expect(gateway.restoreCallCount, 1);
 
     gateway.restoreError = null;
```

`app/test/features/customer/screens/customer_edit_screen_test.dart`:

```diff
@@ -127,7 +127,7 @@ void main() {
     await tester.tap(_button(AppStrings.save));
     await tester.pumpAndSettle();
 
-    expect(find.text('이미 등록된 전화번호입니다.'), findsOneWidget);
+    expect(find.text('이미 등록된 전화번호예요.'), findsOneWidget);
     expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
   });
 
@@ -189,7 +189,7 @@ void main() {
     await tester.tap(_button(AppStrings.deleteCustomer).last);
     await tester.pumpAndSettle();
 
-    expect(find.text('이 작업을 할 권한이 없습니다.'), findsOneWidget);
+    expect(find.text('이 작업을 할 권한이 없어요.'), findsOneWidget);
     expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
   });
 }
```

`app/test/features/customer/screens/pet_form_screen_test.dart`:

```diff
@@ -279,7 +279,7 @@ void main() {
     await tester.tap(_save());
     await tester.pumpAndSettle();
 
-    expect(find.text('질병과 "질병 없음"을 함께 고를 수 없습니다.'), findsOneWidget);
+    expect(find.text('질병과 "질병 없음"을 함께 고를 수 없어요.'), findsOneWidget);
     expect(find.byKey(ScreenKeys.petForm), findsOneWidget);
   });
```

`app/test/features/customer/screens/register_customer_screen_test.dart`:

```diff
@@ -399,7 +399,7 @@ void main() {
     await tester.tap(_onStage(_button(AppStrings.save)));
     await tester.pumpAndSettle();
 
-    expect(find.text('이미 등록된 전화번호입니다.'), findsOneWidget);
+    expect(find.text('이미 등록된 전화번호예요.'), findsOneWidget);
     expect(find.byKey(ScreenKeys.registerCustomer), findsOneWidget);
   });
```

`app/test/features/shop/screens/members_screen_test.dart`:

```diff
@@ -360,7 +360,7 @@ void main() {
     await tester.tap(find.text(AppStrings.promoteToOwner));
     await tester.pumpAndSettle();
 
-    expect(find.text('매장에는 사장이 한 명 이상 있어야 합니다.'), findsOneWidget);
+    expect(find.text('매장에는 사장이 한 명 이상 있어야 해요.'), findsOneWidget);
   });
 
   testWidgets(
```

`app/test/features/visit/screens/photo_viewer_screen_test.dart`:

```diff
@@ -308,7 +308,7 @@ void main() {
     await _tap(tester, find.bySemanticsLabel(AppStrings.toAfter));
 
     expect(server.puts, hasLength(2));
-    expect(find.text('다른 기기에서 기록이 먼저 바뀌었습니다. 화면을 새로 불러왔어요.'), findsOneWidget);
+    expect(find.text('다른 기기에서 기록이 먼저 바뀌었어요. 화면을 새로 불러왔어요.'), findsOneWidget);
   });
 
   testWidgets('예약됨으로 되돌린 방문은 기록을 바꿀 수 없어 원본 저장만 있다', (tester) async {
```

`app/test/features/visit/screens/record_screen_test.dart`:

```diff
@@ -331,7 +331,7 @@ void main() {
     await _tap(tester, _button(AppStrings.save));
 
     expect(server.puts, hasLength(2));
-    expect(find.textContaining('기록이 먼저 바뀌었습니다'), findsOneWidget);
+    expect(find.textContaining('기록이 먼저 바뀌었어요'), findsOneWidget);
     expect(closed.closed, isFalse);
   });
 
@@ -465,7 +465,7 @@ void main() {
 
     await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
 
-    expect(find.text('방문 하나에 사진은 30장까지 붙일 수 있습니다.'), findsOneWidget);
+    expect(find.text('방문 하나에 사진은 30장까지 붙일 수 있어요.'), findsOneWidget);
     expect(_button(AppStrings.takePhoto), findsNothing);
     expect(app.picker.limits, isEmpty);
     expect(app.queue.added, isEmpty);
```

`app/test/features/visit/screens/register_visit_screen_test.dart`:

```diff
@@ -424,7 +424,7 @@ void main() {
     await settle(tester);
 
     expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
-    expect(find.textContaining('자정을 넘습니다'), findsOneWidget);
+    expect(find.textContaining('자정을 넘어요'), findsOneWidget);
   });
 
   testWidgets('저장 중에는 버튼을 막아 요청을 한 번만 보낸다', (tester) async {
```

`app/test/features/visit/screens/settings/menu_settings_screen_test.dart`:

```diff
@@ -206,7 +206,7 @@ void main() {
     expect(server.writes, ['PUT 1 2', 'PUT 2 1']);
     expect(server.menus[0]['sort_order'], 2);
     expect(server.menus[1]['sort_order'], 2);
-    expect(find.textContaining('문제가 생겼습니다'), findsOneWidget);
+    expect(find.textContaining('서버에 잠시 문제가 있어요'), findsOneWidget);
     expect(_names(tester), ['목욕', '위생', '부분 미용', '전체 미용', '스포팅']);
 
     // 같은 ▼를 다시 누르면 순서값이 같아도(v / v+1) 풀린다.
```

`app/test/features/visit/screens/settings/schedule_settings_screen_test.dart`:

```diff
@@ -167,7 +167,7 @@ void main() {
     await _tap(tester, _button(AppStrings.save));
 
     expect(find.byKey(ScreenKeys.settingsSchedule), findsOneWidget);
-    expect(find.textContaining('권한이 없습니다'), findsOneWidget);
+    expect(find.textContaining('권한이 없어요'), findsOneWidget);
   });
 
   testWidgets('설정을 불러오지 못하면 다시 시도한다', (tester) async {
```

`app/test/features/visit/screens/visit_detail_screen_test.dart`:

```diff
@@ -286,7 +286,7 @@ void main() {
     await _tap(tester, _button(AppStrings.actionNextReservation));
 
     expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
-    expect(find.textContaining('문제가 생겼습니다'), findsOneWidget);
+    expect(find.textContaining('서버에 잠시 문제가 있어요'), findsOneWidget);
   });
 
   testWidgets('초안을 못 읽어도 다음 예약 시트는 미리보기 없이 뜬다', (tester) async {
@@ -395,7 +395,7 @@ void main() {
 
     await _tap(tester, _button(AppStrings.actionStart));
 
-    expect(find.textContaining('아직 할 수 없습니다'), findsOneWidget);
+    expect(find.textContaining('아직 할 수 없어요'), findsOneWidget);
     expect(setup.calls, contains('GET /v1/shops/3/visits/101'));
   });
 
@@ -501,7 +501,7 @@ void main() {
     final setup = CustomerTestSetup(server.backend.call, overrides: _today);
     addTearDown(setup.container.dispose);
     await _open(tester, setup);
-    expect(find.textContaining('방문을 찾을 수 없습니다'), findsOneWidget);
+    expect(find.textContaining('방문을 찾을 수 없어요'), findsOneWidget);
     expect(find.bySemanticsLabel(AppStrings.back), findsOneWidget);
 
     fail = false;
@@ -686,7 +686,7 @@ void main() {
 
       await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
 
-      expect(find.text('방문 하나에 사진은 30장까지 붙일 수 있습니다.'), findsOneWidget);
+      expect(find.text('방문 하나에 사진은 30장까지 붙일 수 있어요.'), findsOneWidget);
       expect(_button(AppStrings.takePhoto), findsNothing);
       expect(app.queue.added, isEmpty);
     });
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/core/error`
Expected: 컴파일 실패 — `error_kind.dart`와 `loadMessageFor`가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/error/error_kind.dart`:

```dart
import 'api_exception.dart';

/// 오류의 원인 — 문구와 화면이 보일 행동(다시 시도·돌아가기·스스로 잇기)을 정한다(오류 화면 다듬기 설계 2절).
enum ErrorKind {
  /// 인터넷이 없거나 서버에 닿지 못했다. 인터넷이 돌아오면 스스로 다시 한다.
  offline,

  /// 서버가 5xx 이거나 형식을 모르는 응답을 줬다(게이트웨이 502·503 등).
  server,

  /// 403 — 다시 해도 같다.
  denied,

  /// 404 — 이미 지워졌을 수 있다. 다시 해도 같다.
  gone,

  /// 그 밖(업무 규칙 4xx, `ApiException`이 아닌 오류).
  other;

  /// 다시 해 볼 만한가 — 권한·없음은 다시 해도 같으니 [다시 시도] 대신 [돌아가기]를 준다.
  bool get retryable => this != denied && this != gone;
}

/// [error]의 원인. 기준은 `ApiException`의 코드와 상태 번호뿐이다.
ErrorKind kindOf(Object error) {
  if (error is! ApiException) return ErrorKind.other;
  if (error.isNetwork) return ErrorKind.offline;
  final status = error.statusCode;
  if ((status != null && status >= 500) || error.code == 'HTTP_ERROR') {
    return ErrorKind.server;
  }
  if (status == 403) return ErrorKind.denied;
  if (status == 404) return ErrorKind.gone;
  return ErrorKind.other;
}
```

`app/lib/core/error/error_messages.dart`:

```diff
@@ -1,74 +1,96 @@
 import 'api_exception.dart';
+import 'error_kind.dart';
 
-/// 서버 오류 코드를 사용자에게 보여 줄 한국어 문구로 바꾼다.
+/// 서버 오류 코드를 사용자에게 보여 줄 한국어 문구(해요체)로 바꾼다.
 ///
 /// 문구는 서버의 `message` 가 아니라 `code` 로 고른다. 모르는 코드일 때만 서버 문구를 쓴다.
 const Map<String, String> _messages = {
-  'NETWORK': '네트워크 연결을 확인하고 다시 시도해 주세요.',
   'UNAUTHENTICATED': '보안을 위해 다시 로그인해 주세요.',
   'REAUTH_REQUIRED': '보안을 위해 다시 로그인해 주세요.',
-  'PROVIDER_VERIFICATION_FAILED': '로그인 정보를 확인하지 못했습니다. 다시 시도해 주세요.',
-  'PROVIDER_NOT_SUPPORTED': '지원하지 않는 로그인 방식입니다.',
-  'ACCOUNT_SUSPENDED': '이용이 정지된 계정입니다. 고객센터에 문의해 주세요.',
-  'NOT_A_MEMBER': '이 매장의 멤버가 아니거나 역할이 바뀌었습니다.',
-  'PERMISSION_DENIED': '이 작업을 할 권한이 없습니다.',
-  'SHOP_CLOSED': '닫힌 매장입니다.',
-  'SHOP_SUSPENDED': '이용이 정지된 매장입니다.',
-  'MEMBER_NOT_FOUND': '멤버를 찾을 수 없습니다.',
-  'IDENTITY_NOT_FOUND': '연결되어 있지 않은 로그인 수단입니다.',
+  'PROVIDER_VERIFICATION_FAILED': '로그인 정보를 확인하지 못했어요. 다시 시도해 주세요.',
+  'PROVIDER_NOT_SUPPORTED': '지원하지 않는 로그인 방식이에요.',
+  'ACCOUNT_SUSPENDED': '이용이 정지된 계정이에요. 고객센터에 문의해 주세요.',
+  'NOT_A_MEMBER': '이 매장의 멤버가 아니거나 역할이 바뀌었어요.',
+  'PERMISSION_DENIED': '이 작업을 할 권한이 없어요.',
+  'SHOP_CLOSED': '닫힌 매장이에요.',
+  'SHOP_SUSPENDED': '이용이 정지된 매장이에요.',
+  'MEMBER_NOT_FOUND': '멤버를 찾을 수 없어요.',
+  'IDENTITY_NOT_FOUND': '연결되어 있지 않은 로그인 수단이에요.',
   'INVITE_INVALID': '초대 코드를 확인해 주세요.',
-  'INVITE_EXPIRED': '만료된 초대 코드입니다. 새 코드를 받아 주세요.',
-  'INVITE_EXHAUSTED': '이미 사용된 초대 코드입니다. 새 코드를 받아 주세요.',
-  'LAST_OWNER': '매장에는 사장이 한 명 이상 있어야 합니다.',
-  'ALREADY_A_MEMBER': '이미 이 매장의 멤버입니다.',
-  'IDENTITY_ALREADY_LINKED': '다른 계정에 연결된 로그인 수단입니다. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
-  'PROVIDER_ALREADY_LINKED': '같은 종류의 로그인 수단이 이미 연결되어 있습니다.',
-  'LAST_IDENTITY': '마지막 로그인 수단은 해제할 수 없습니다.',
-  'OWNERSHIP_TRANSFER_REQUIRED': '혼자 사장인 매장에 다른 멤버가 있습니다. 먼저 다른 사장을 지정해 주세요.',
-  'SHOP_CLOSE_CONFIRM_REQUIRED': '탈퇴하면 혼자 운영하는 매장도 함께 닫힙니다.',
+  'INVITE_EXPIRED': '만료된 초대 코드예요. 새 코드를 받아 주세요.',
+  'INVITE_EXHAUSTED': '이미 사용된 초대 코드예요. 새 코드를 받아 주세요.',
+  'LAST_OWNER': '매장에는 사장이 한 명 이상 있어야 해요.',
+  'ALREADY_A_MEMBER': '이미 이 매장의 멤버예요.',
+  'IDENTITY_ALREADY_LINKED': '다른 계정에 연결된 로그인 수단이에요. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
+  'PROVIDER_ALREADY_LINKED': '같은 종류의 로그인 수단이 이미 연결되어 있어요.',
+  'LAST_IDENTITY': '마지막 로그인 수단은 해제할 수 없어요.',
+  'OWNERSHIP_TRANSFER_REQUIRED': '혼자 사장인 매장에 다른 멤버가 있어요. 먼저 다른 사장을 지정해 주세요.',
+  'SHOP_CLOSE_CONFIRM_REQUIRED': '탈퇴하면 혼자 운영하는 매장도 함께 닫혀요.',
   'VALIDATION_ERROR': '입력한 내용을 확인해 주세요.',
-  'TOO_MANY_ATTEMPTS': '시도가 너무 잦습니다. 잠시 뒤에 다시 해 주세요.',
-  'CUSTOMER_NOT_FOUND': '고객을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다.',
-  'PET_NOT_FOUND': '반려동물을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다.',
-  'CUSTOMER_PHONE_TAKEN': '이미 등록된 전화번호입니다.',
-  'LAST_PET': '마지막 반려동물은 삭제할 수 없습니다. 고객 삭제를 이용해 주세요.',
+  'TOO_MANY_ATTEMPTS': '시도가 너무 잦아요. 잠시 뒤에 다시 해 주세요.',
+  'CUSTOMER_NOT_FOUND': '고객을 찾을 수 없어요. 이미 삭제되었을 수 있어요.',
+  'PET_NOT_FOUND': '반려동물을 찾을 수 없어요. 이미 삭제되었을 수 있어요.',
+  'CUSTOMER_PHONE_TAKEN': '이미 등록된 전화번호예요.',
+  'LAST_PET': '마지막 반려동물은 삭제할 수 없어요. 고객 삭제를 이용해 주세요.',
   'PET_HEALTH_REQUIRED': '질병을 고르거나 "질병 없음"을 눌러 주세요.',
-  'PET_HEALTH_CONFLICT': '질병과 "질병 없음"을 함께 고를 수 없습니다.',
-  'PET_HAS_VISITS': '방문 기록이 있는 반려동물은 삭제할 수 없습니다. 무지개다리 표시를 이용해 주세요.',
-  'PET_HAS_UPCOMING_VISITS': '앞으로의 예약이 있습니다. 예약을 먼저 취소해 주세요.',
-  'CUSTOMER_HAS_UPCOMING_VISITS': '앞으로의 예약이 있는 고객은 삭제할 수 없습니다. 예약을 먼저 취소해 주세요.',
-  'PET_PASSED_AWAY': '무지개다리를 건넌 반려동물은 예약할 수 없습니다.',
-  'VISIT_NOT_FOUND': '방문을 찾을 수 없습니다. 이미 지워졌을 수 있습니다.',
-  'VISIT_STATE_CONFLICT': '다른 기기에서 먼저 바뀌었습니다. 화면을 새로 불러왔어요.',
-  'VISIT_NOT_YET': '아직 할 수 없습니다. 예약한 날(노쇼는 예약 시각)이 지나야 합니다.',
-  'VISIT_DUPLICATE': '이미 저장된 예약입니다.',
-  'VISIT_CROSSES_MIDNIGHT': '끝나는 시각이 자정을 넘습니다. 소요를 줄여 주세요.',
-  'VISIT_GROUP_MISMATCH': '같은 보호자의 방문만 함께 바꿀 수 있습니다.',
-  'MENU_NOT_FOUND': '없거나 보관된 메뉴입니다. 메뉴를 다시 골라 주세요.',
-  'MENU_NAME_TAKEN': '같은 이름의 메뉴가 이미 있습니다.',
+  'PET_HEALTH_CONFLICT': '질병과 "질병 없음"을 함께 고를 수 없어요.',
+  'PET_HAS_VISITS': '방문 기록이 있는 반려동물은 삭제할 수 없어요. 무지개다리 표시를 이용해 주세요.',
+  'PET_HAS_UPCOMING_VISITS': '앞으로의 예약이 있어요. 예약을 먼저 취소해 주세요.',
+  'CUSTOMER_HAS_UPCOMING_VISITS': '앞으로의 예약이 있는 고객은 삭제할 수 없어요. 예약을 먼저 취소해 주세요.',
+  'PET_PASSED_AWAY': '무지개다리를 건넌 반려동물은 예약할 수 없어요.',
+  'VISIT_NOT_FOUND': '방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.',
+  'VISIT_STATE_CONFLICT': '다른 기기에서 먼저 바뀌었어요. 화면을 새로 불러왔어요.',
+  'VISIT_NOT_YET': '아직 할 수 없어요. 예약한 날(노쇼는 예약 시각)이 지나야 해요.',
+  'VISIT_DUPLICATE': '이미 저장된 예약이에요.',
+  'VISIT_CROSSES_MIDNIGHT': '끝나는 시각이 자정을 넘어요. 소요를 줄여 주세요.',
+  'VISIT_GROUP_MISMATCH': '같은 보호자의 방문만 함께 바꿀 수 있어요.',
+  'MENU_NOT_FOUND': '없거나 보관된 메뉴예요. 메뉴를 다시 골라 주세요.',
+  'MENU_NAME_TAKEN': '같은 이름의 메뉴가 이미 있어요.',
   // 미용 기록·사진(④ 설계 9절)
-  'VISIT_NO_RECORD_YET': '미용을 시작한 방문에만 기록을 쓸 수 있습니다.',
-  'RECORD_NOT_FOUND': '기록이 없습니다. 이미 지워졌을 수 있습니다.',
-  'RECORD_VERSION_CONFLICT': '다른 기기에서 기록이 먼저 바뀌었습니다. 화면을 새로 불러왔어요.',
-  'RECORD_WEIGHT_WITHOUT_PET': '보호자만의 방문에는 몸무게를 적을 수 없습니다.',
-  'RECORD_ITEM_DUPLICATE': '같은 메뉴를 두 번 적을 수 없습니다.',
-  'MEDIA_NOT_FOUND': '사진을 찾을 수 없습니다. 다시 올려 주세요.',
-  'MEDIA_NOT_UPLOADED': '사진이 아직 다 올라가지 않았습니다.',
-  'MEDIA_NOT_READY': '사진이 아직 다 올라가지 않았습니다.',
-  'MEDIA_ALREADY_ATTACHED': '이미 다른 기록에 붙은 사진입니다.',
-  'MEDIA_TOO_LARGE': '사진은 20MB까지 올릴 수 있습니다.',
-  'MEDIA_TYPE_UNSUPPORTED': '올릴 수 없는 형식의 파일입니다.',
-  'MEDIA_LIMIT_EXCEEDED': '방문 하나에 사진은 30장까지 붙일 수 있습니다.',
+  'VISIT_NO_RECORD_YET': '미용을 시작한 방문에만 기록을 쓸 수 있어요.',
+  'RECORD_NOT_FOUND': '기록이 없어요. 이미 지워졌을 수 있어요.',
+  'RECORD_VERSION_CONFLICT': '다른 기기에서 기록이 먼저 바뀌었어요. 화면을 새로 불러왔어요.',
+  'RECORD_WEIGHT_WITHOUT_PET': '보호자만의 방문에는 몸무게를 적을 수 없어요.',
+  'RECORD_ITEM_DUPLICATE': '같은 메뉴를 두 번 적을 수 없어요.',
+  'MEDIA_NOT_FOUND': '사진을 찾을 수 없어요. 다시 올려 주세요.',
+  'MEDIA_NOT_UPLOADED': '사진이 아직 다 올라가지 않았어요.',
+  'MEDIA_NOT_READY': '사진이 아직 다 올라가지 않았어요.',
+  'MEDIA_ALREADY_ATTACHED': '이미 다른 기록에 붙은 사진이에요.',
+  'MEDIA_TOO_LARGE': '사진은 20MB까지 올릴 수 있어요.',
+  'MEDIA_TYPE_UNSUPPORTED': '올릴 수 없는 형식의 파일이에요.',
+  'MEDIA_LIMIT_EXCEEDED': '방문 하나에 사진은 30장까지 붙일 수 있어요.',
 };
 
-const String _fallback = '문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.';
+/// 인터넷 없음 — 누른 일(저장·삭제 등)이 실패했을 때.
+const String offlineActionMessage = '인터넷에 연결되지 않았어요. 연결을 확인해 주세요.';
 
-/// 어떤 오류든 화면에 보여 줄 문구 한 줄로 바꾼다.
-String messageFor(Object error) {
+/// 인터넷 없음 — 화면을 불러오지 못했을 때. 인터넷이 돌아오면 화면이 스스로 다시 불러온다.
+const String offlineLoadMessage = '인터넷에 연결되지 않았어요. 연결되면 다시 불러올게요.';
+
+const String _server = '서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.';
+
+const String _fallback = '문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.';
+
+/// 누른 일이 실패했을 때 보일 문구 한 줄.
+String messageFor(Object error) => _message(error, offlineActionMessage);
+
+/// 화면을 불러오지 못했을 때 보일 문구 한 줄(`AsyncBody`·스플래시).
+String loadMessageFor(Object error) => _message(error, offlineLoadMessage);
+
+String _message(Object error, String offline) {
+  switch (kindOf(error)) {
+    case ErrorKind.offline:
+      return offline;
+    case ErrorKind.server:
+      return _server;
+    case ErrorKind.denied:
+    case ErrorKind.gone:
+    case ErrorKind.other:
+      break;
+  }
   if (error is! ApiException) return _fallback;
   final known = _messages[error.code];
   if (known != null) return known;
-  // HTTP_ERROR 는 서버가 {code, message} 를 주지 못한 경우라 기술적인 문구다. 보여 주지 않는다.
-  if (error.code == 'HTTP_ERROR' || error.message.isEmpty) return _fallback;
+  if (error.message.isEmpty) return _fallback;
   return error.message;
 }
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/core/error` → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 666 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `error_kind.dart`의 `status >= 500`을 `status > 500`으로 → `error_messages_test.dart::서버 오류(5xx·형식을 모르는 응답)는 서버 문구다` 실패.
- `loadMessageFor`가 `offlineActionMessage`를 넘기게 → `error_messages_test.dart::인터넷 없음은 누른 일이면 연결 확인을, 화면을 불러올 때면 스스로 다시 불러온다고 안내한다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 오류 원인 분류(ErrorKind) — 인터넷 없음·서버·권한·없음·그 밖, 원인별 문구와 불러오기용 문구, 오류 문구 해요체

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 화면 문구 해요체와 구조 테스트, 대기열 [빼기] → [올리기 취소]

**Files:**
- Modify: `app/lib/l10n/app_strings.dart`
- Create: `app/test/design/copy_tone_test.dart`

**Interfaces:**
- Consumes: 작업 1(오류 문구는 이미 해요체).
- Produces: `AppStrings`의 합니다체 문구 열일곱을 해요체로, `AppStrings.removeUpload = '올리기 취소'`. 구조 테스트 `test/design/copy_tone_test.dart`(`app_strings.dart`·`error_messages.dart` 문자열에 `…니다` 없음).

설계 2.1. "~해 주세요"·"~할까요?"는 이미 해요체라 그대로다. `api_exception.dart`·`api_client.dart`·`StateError`의 합니다체는 화면에 닿지 않는다(`messageFor`가 코드로 고르거나 공통 문구) — 그대로 둔다. 사용자가 "빼기가 뭐야?"라고 물었다 — 대기열 타일의 X 는 앨범 사진을 지우지 않고 올리기만 그만둔다는 것이 드러나게 [올리기 취소]다(붙은 사진을 폼에서 빼는 `removePhoto`는 그대로).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/copy_tone_test.dart`:

```dart
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 오류 화면 다듬기 설계 2.1: 앱 문구는 해요체다. 화면에 닿는 문구가 모인 두 파일의 문자열에
/// 합니다체(…니다)가 없어야 한다. 주석은 보지 않는다.
void main() {
  test('화면 문구와 오류 문구는 해요체다(…니다 없음)', () {
    const files = [
      'lib/l10n/app_strings.dart',
      'lib/core/error/error_messages.dart',
    ];
    final literal = RegExp(r"'[^']*니다[^']*'");
    final violations = [
      for (final path in files)
        for (final line in File(path).readAsLinesSync())
          if (!line.trimLeft().startsWith('//') && literal.hasMatch(line))
            '$path: ${line.trim()}',
    ];

    expect(violations, isEmpty, reason: '합니다체 문구: $violations');
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/design/copy_tone_test.dart`
Expected: 실패 — 합니다체 문구 열일곱이 걸린다.

- [ ] **Step 3: 구현한다**

`app/lib/l10n/app_strings.dart`:

```diff
@@ -35,7 +35,7 @@ class AppStrings {
   static const tabCalendar = '캘린더';
   static const tabCustomers = '고객';
   static const tabSales = '매출';
-  static const comingSoonEmptyTitle = '준비 중입니다';
+  static const comingSoonEmptyTitle = '준비 중이에요';
   static const comingSoonSheetText = '매출은 다음 업데이트에서 만나요';
 
   // 설정 허브
@@ -63,7 +63,7 @@ class AppStrings {
   static const shopPhone = '전화번호';
   static const shopAddress = '주소';
   static const save = '저장';
-  static const saved = '저장했습니다';
+  static const saved = '저장했어요';
   static const shopNameRequired = '매장 이름을 입력해 주세요.';
 
   // 계정
@@ -74,22 +74,22 @@ class AppStrings {
   static const accountLinkedMethods = '로그인 수단';
   static const accountAddMethod = '로그인 수단 추가';
   static const unlink = '해제';
-  static const unlinkOnlyOneCaption = '마지막 로그인 수단은 해제할 수 없습니다.';
-  static const unlinkConfirmMessage = '해제하면 다른 모든 기기에서 로그아웃됩니다.';
+  static const unlinkOnlyOneCaption = '마지막 로그인 수단은 해제할 수 없어요.';
+  static const unlinkConfirmMessage = '해제하면 다른 모든 기기에서 로그아웃돼요.';
   static const withdraw = '회원 탈퇴';
 
   // 재인증
   static const reauthPromptTitle = '보안을 위해 다시 로그인해 주세요';
-  static const reauthMismatch = '다른 계정입니다. 이 계정에 연결된 로그인 수단으로 다시 로그인해 주세요.';
+  static const reauthMismatch = '다른 계정이에요. 이 계정에 연결된 로그인 수단으로 다시 로그인해 주세요.';
 
   // 회원 탈퇴
-  static const withdrawNoticeIrreversible = '되돌릴 수 없습니다.';
-  static const withdrawNoticeShopRecordsStay = '매장의 기록은 매장에 남습니다.';
-  static const withdrawNoticeMembershipGone = '소속과 초대 코드는 사라집니다.';
-  static const withdrawNoticeNewAccount = '같은 소셜 계정으로 다시 가입하면 새 계정이 됩니다.';
-  static const withdrawConfirmCheckbox = '안내를 확인했습니다';
+  static const withdrawNoticeIrreversible = '되돌릴 수 없어요.';
+  static const withdrawNoticeShopRecordsStay = '매장의 기록은 매장에 남아요.';
+  static const withdrawNoticeMembershipGone = '소속과 초대 코드는 사라져요.';
+  static const withdrawNoticeNewAccount = '같은 소셜 계정으로 다시 가입하면 새 계정이 돼요.';
+  static const withdrawConfirmCheckbox = '안내를 확인했어요';
   static const withdrawSubmit = '탈퇴하기';
-  static const withdrawShopCloseTitle = '혼자 운영하는 매장도 함께 닫힙니다';
+  static const withdrawShopCloseTitle = '혼자 운영하는 매장도 함께 닫혀요';
   static const withdrawShopCloseConfirm = '매장을 닫고 탈퇴';
   static const goToMembers = '멤버 관리로 이동';
 
@@ -113,9 +113,9 @@ class AppStrings {
   static const passedAwayBadge = '무지개다리';
   static const markPassedAway = '무지개다리 표시';
   static const unmarkPassedAway = '무지개다리 되돌리기';
-  static const markPassedAwayConfirm = '무지개다리를 건넜다고 표시할까요? 목록에서 숨겨지고 기록은 남습니다.';
+  static const markPassedAwayConfirm = '무지개다리를 건넜다고 표시할까요? 목록에서 숨겨지고 기록은 남아요.';
   static const deletePet = '반려동물 삭제';
-  static const deletePetConfirm = '잘못 등록한 반려동물을 삭제할까요? 질병 기록도 함께 지워지고 되돌릴 수 없습니다.';
+  static const deletePetConfirm = '잘못 등록한 반려동물을 삭제할까요? 질병 기록도 함께 지워지고 되돌릴 수 없어요.';
   static const birthDateLabel = '생일';
   static const birthYearLabel = '태어난 해';
   static const ageUnknown = '모름';
@@ -201,7 +201,7 @@ class AppStrings {
   static const consentRequired = '마케팅 수신 동의 여부를 골라 주세요.';
   static const editOwnerTitle = '보호자 수정';
   static const deleteCustomer = '고객 삭제';
-  static const deleteCustomerConfirm = '고객을 삭제할까요? 보호자의 이름·전화번호·메모와 반려동물의 이름·질병 기록이 지워지고 되돌릴 수 없습니다.';
+  static const deleteCustomerConfirm = '고객을 삭제할까요? 보호자의 이름·전화번호·메모와 반려동물의 이름·질병 기록이 지워지고 되돌릴 수 없어요.';
 
   static const registerCustomer = '고객 등록';
   static const registerStepPhone = '전화번호';
@@ -294,7 +294,7 @@ class AppStrings {
   static String completeAndNextCaption(int weeks) =>
       '$weeks주 뒤 같은 요일·시간·메뉴로 채워진 예약 화면이 열려요.';
   static const cancelReasonTitle = '취소 사유를 골라 주세요';
-  static const noShowConfirm = '노쇼로 기록할까요? 보호자의 노쇼 횟수에 더해집니다.';
+  static const noShowConfirm = '노쇼로 기록할까요? 보호자의 노쇼 횟수에 더해져요.';
 
   static String noShowCount(int count) => '노쇼 $count회';
   static const noShowCountLabel = '노쇼 횟수';
@@ -382,7 +382,7 @@ class AppStrings {
   static const addPhotoPhaseLabel = '어느 사진인가요?';
   static const uploading = '올리는 중';
   static const uploadWaiting = '대기 중';
-  static const removeUpload = '빼기';
+  static const removeUpload = '올리기 취소';
   static const removePhoto = '사진 빼기';
   static const recordMenusLabel = '메뉴 · 금액';
   static const totalLabel = '총액';
@@ -402,7 +402,7 @@ class AppStrings {
   static const editRecord = '기록 수정';
   static const writeRecord = '기록 쓰기';
   static const deleteRecord = '기록 삭제';
-  static const deleteRecordConfirm = '이 방문의 미용 기록을 삭제할까요? 사진·메모·금액이 함께 지워지고 되돌릴 수 없습니다.';
+  static const deleteRecordConfirm = '이 방문의 미용 기록을 삭제할까요? 사진·메모·금액이 함께 지워지고 되돌릴 수 없어요.';
 
   /// '전 사진 1' — 사진 줄의 타일(접근성 이름).
   static String photoTileLabel(String phase, int index) => '$phase 사진 $index';
@@ -428,7 +428,7 @@ class AppStrings {
   static const toBefore = '전으로 바꾸기';
   static const makeCover = '대표로';
   static const deletePhoto = '사진 삭제';
-  static const deletePhotoConfirm = '이 사진을 기록에서 지울까요? 되돌릴 수 없습니다.';
+  static const deletePhotoConfirm = '이 사진을 기록에서 지울까요? 되돌릴 수 없어요.';
   static const savedToAlbum = '앨범에 저장했어요.';
   static const albumDenied = '사진 보관함 권한이 없어요. 설정에서 켜 주세요.';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/design/copy_tone_test.dart` → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 667 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `AppStrings.saved`를 `'저장했습니다'`로 → `copy_tone_test.dart` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 화면 문구 해요체 — 합니다체 문구 열일곱을 바꾸고 구조 테스트로 지킨다, 대기열 [빼기]는 [올리기 취소]

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 얇은 오류 띠 `AppErrorBanner`와 `AppErrorRetry`의 [돌아가기]

**Files:**
- Create: `app/lib/design/widgets/app_error_banner.dart`
- Modify: `app/lib/design/widgets/app_error_retry.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Create: `app/test/design/app_error_banner_test.dart`
- Modify: `app/test/design/app_error_retry_test.dart`
- Create: `app/test/design/goldens/app_error_banner.png`

**Interfaces:**
- Consumes: `design/widgets`의 `Pressable`·`AppButton`, 토큰.
- Produces: `design/widgets/app_error_banner.dart` — `AppErrorBanner({required String message, bool offline = false, VoidCallback? onRetry})`(높이 44, 불투명 흰 면, 아래 구분선, offline 이면 `Icons.wifi_off_rounded`). `AppErrorRetry`(가운데·`inline`·`row`)의 `onRetry`가 선택이 되고 `VoidCallback? onBack`이 생긴다 — `onRetry`가 있으면 [다시 시도], 없고 `onBack`이 있으면 [돌아가기], 둘 다 없으면 문구만. `AppStrings.goBack = '돌아가기'`.

설계 3.1·2절. 띠는 스크롤 콘텐츠 위라 글래스가 아니다(`glass_boundary_test`). 띠의 [다시 시도]는 누르는 자리 44 를 지키려고 띠 높이를 44 로 맞췄다 — 버튼이 없어도 높이가 같다. 모양 위젯이라 Riverpod 을 모른다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/app_error_banner_test.dart`:

```dart
import 'package:chagocnote/design/widgets/app_error_banner.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  testWidgets('문구를 보이고, onRetry 가 있으면 [다시 시도]를 누를 수 있다', (tester) async {
    var retried = 0;
    await tester.pumpWidget(
      _wrap(AppErrorBanner(message: '서버에 잠시 문제가 있어요', onRetry: () => retried++)),
    );
    expect(find.text('서버에 잠시 문제가 있어요'), findsOneWidget);
    await tester.tap(find.text(AppStrings.retry));
    expect(retried, 1);
  });

  testWidgets('onRetry 가 없으면 [다시 시도]가 없고, offline 이면 끊김 아이콘이다', (tester) async {
    await tester.pumpWidget(
      _wrap(const AppErrorBanner(message: '인터넷에 연결되지 않았어요', offline: true)),
    );
    expect(find.text(AppStrings.retry), findsNothing);
    expect(find.byIcon(Icons.wifi_off_rounded), findsOneWidget);
  });

  testWidgets('AppErrorBanner 골든 — 인터넷 없음 한 줄, 서버 오류와 [다시 시도] 한 줄', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const AppErrorBanner(
            message: '인터넷에 연결되지 않았어요 · 이전 내용이에요',
            offline: true,
          ),
          const SizedBox(height: 8),
          AppErrorBanner(
            message: '서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.',
            onRetry: () {},
          ),
        ],
      ),
      surfaceSize: const Size(390, 160),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_error_banner.png'));
  });
}
```

`app/test/design/app_error_retry_test.dart`:

```diff
@@ -22,6 +22,21 @@ void main() {
     expect(retried, 1);
   });
 
+  testWidgets('onRetry 없이 onBack 만 주면 [돌아가기]만, 둘 다 없으면 문구만 보인다', (tester) async {
+    var back = 0;
+    await tester.pumpWidget(
+      _wrap(AppErrorRetry(message: '권한이 없어요', onBack: () => back++)),
+    );
+    expect(find.text(AppStrings.retry), findsNothing);
+    await tester.tap(find.text(AppStrings.goBack));
+    expect(back, 1);
+
+    await tester.pumpWidget(_wrap(const AppErrorRetry(message: '권한이 없어요')));
+    expect(find.text('권한이 없어요'), findsOneWidget);
+    expect(find.text(AppStrings.retry), findsNothing);
+    expect(find.text(AppStrings.goBack), findsNothing);
+  });
+
   testWidgets('row 변형은 한 줄에 문구와 버튼을 나란히 놓는다', (tester) async {
     await tester.pumpWidget(
       _wrap(AppErrorRetry.row(message: '못 읽었어요', onRetry: () {})),
```

`app/test/design/goldens/app_error_banner.png`: 골든 이미지 — 이 문서에 넣지 않는다. 이 작업의 골든 테스트를 `--update-goldens`로 돌려 만들고 눈으로 본다(의도한 변경).

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/design/app_error_banner_test.dart test/design/app_error_retry_test.dart`
Expected: 컴파일 실패 — `AppErrorBanner`·`onBack`·`AppStrings.goBack`이 없다.

- [ ] **Step 3: 구현한다**

`app/lib/design/widgets/app_error_banner.dart`:

```dart
import 'package:flutter/material.dart';

import '../../l10n/app_strings.dart';
import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 이미 보이는 내용 위에 까는 얇은 오류 띠 — 새로 불러오다 실패해도 받은 데이터는 그대로 둔다
/// (오류 화면 다듬기 설계 3.1). 스크롤 콘텐츠 위라 글래스가 아니라 불투명 흰 면이다.
///
/// [offline]이면 와이파이 끊김 아이콘, 아니면 느낌표. [onRetry]가 있으면 오른쪽에 [다시 시도].
class AppErrorBanner extends StatelessWidget {
  const AppErrorBanner({
    super.key,
    required this.message,
    this.offline = false,
    this.onRetry,
  });

  final String message;
  final bool offline;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      // 높이는 [다시 시도]의 누르는 자리(44)에 맞춘다 — 버튼이 없어도 띠 높이가 같다.
      constraints: const BoxConstraints(minHeight: 44),
      padding: const EdgeInsets.only(left: AppSpacing.lg),
      decoration: const BoxDecoration(
        color: AppColors.white,
        border: Border(bottom: BorderSide(color: AppColors.line)),
      ),
      child: Row(
        children: [
          Icon(
            offline ? Icons.wifi_off_rounded : Icons.error_outline_rounded,
            size: 16,
            color: AppColors.ink,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: Text(message, style: AppTypography.caption),
            ),
          ),
          // 버튼이 없으면 오른쪽 여백만.
          if (onRetry == null) const SizedBox(width: AppSpacing.lg),
          if (onRetry != null)
            Pressable(
              semanticLabel: AppStrings.retry,
              onTap: onRetry,
              child: SizedBox(
                height: 44,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                  ),
                  child: Center(
                    child: Text(
                      AppStrings.retry,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.ink,
                        fontWeight: FontWeight.w600,
                      ),
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

`app/lib/design/widgets/app_error_retry.dart`:

```diff
@@ -5,34 +5,48 @@ import '../tokens/app_spacing.dart';
 import '../tokens/app_typography.dart';
 import 'app_button.dart';
 
-/// 오류 문구와 [다시 시도] 버튼. 화면마다 복사하던 블록을 하나로.
+/// 오류 문구와 행동 버튼. 화면마다 복사하던 블록을 하나로.
+///
+/// [onRetry]가 있으면 [다시 시도], [onBack]이 있으면 [돌아가기]를 보인다. 다시 해도 같은 오류(권한·없음)는
+/// [onRetry] 없이 [onBack]만 주고, 뒤로 갈 곳도 없으면 문구만 남는다(오류 화면 다듬기 설계 2절).
 ///
 /// 기본은 화면 가운데(목록·상세의 `AsyncValue.when(error: …)` 자리). [AppErrorRetry.inline]은
 /// 흐름 안에 여백을 두고 놓이고(달력 아래, 카드 안), [AppErrorRetry.row]는 한 줄(작은 글씨 +
 /// 버튼)로 좁은 자리에 들어간다(시간 칸, 임시 휴무 목록).
 class AppErrorRetry extends StatelessWidget {
-  const AppErrorRetry({super.key, required this.message, required this.onRetry})
-    : _layout = _Layout.centered;
+  const AppErrorRetry({
+    super.key,
+    required this.message,
+    this.onRetry,
+    this.onBack,
+  }) : _layout = _Layout.centered;
 
   const AppErrorRetry.inline({
     super.key,
     required this.message,
-    required this.onRetry,
+    this.onRetry,
+    this.onBack,
   }) : _layout = _Layout.inline;
 
   const AppErrorRetry.row({
     super.key,
     required this.message,
-    required this.onRetry,
+    this.onRetry,
+    this.onBack,
   }) : _layout = _Layout.row;
 
   final String message;
-  final VoidCallback onRetry;
+  final VoidCallback? onRetry;
+  final VoidCallback? onBack;
   final _Layout _layout;
 
   @override
   Widget build(BuildContext context) {
-    final button = AppButton(label: AppStrings.retry, onPressed: onRetry);
+    final button = onRetry != null
+        ? AppButton(label: AppStrings.retry, onPressed: onRetry)
+        : onBack != null
+        ? AppButton(label: AppStrings.goBack, onPressed: onBack)
+        : null;
     return switch (_layout) {
       _Layout.centered => Center(
         child: Column(
@@ -43,8 +57,10 @@ class AppErrorRetry extends StatelessWidget {
               style: AppTypography.body,
               textAlign: TextAlign.center,
             ),
-            const SizedBox(height: AppSpacing.lg),
-            button,
+            if (button != null) ...[
+              const SizedBox(height: AppSpacing.lg),
+              button,
+            ],
           ],
         ),
       ),
@@ -58,15 +74,17 @@ class AppErrorRetry extends StatelessWidget {
               style: AppTypography.body,
               textAlign: TextAlign.center,
             ),
-            const SizedBox(height: AppSpacing.md),
-            button,
+            if (button != null) ...[
+              const SizedBox(height: AppSpacing.md),
+              button,
+            ],
           ],
         ),
       ),
       _Layout.row => Row(
         children: [
           Expanded(child: Text(message, style: AppTypography.caption)),
-          button,
+          ?button,
         ],
       ),
     };
```

`app/lib/l10n/app_strings.dart`:

```diff
@@ -8,6 +8,7 @@ class AppStrings {
   static const appName = '차곡노트';
   static const retry = '다시 시도';
   static const back = '뒤로';
+  static const goBack = '돌아가기';
 
   // 로그인
   static const continueWithKakao = '카카오로 계속하기';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/design/app_error_banner_test.dart --update-goldens` → 골든 `app_error_banner.png`를 눈으로 본다(끊김 아이콘 한 줄, 느낌표·[다시 시도] 한 줄, 글자와 버튼이 가운데 줄).

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 671 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `AppErrorRetry`에서 `onBack` 갈래의 `AppButton(label: AppStrings.goBack, …)`을 `null`로 → `app_error_retry_test.dart::onRetry 없이 onBack 만 주면 [돌아가기]만, 둘 다 없으면 문구만 보인다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 얇은 오류 띠 AppErrorBanner 와 AppErrorRetry 의 [돌아가기] — 다시 해도 같은 오류는 다시 시도 대신 돌아가기, 둘 다 없으면 문구만

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 화면 본문 틀 `AsyncBody` — 불러오는 중·처음 실패·받은 데이터 위 띠·인터넷 복귀 때 스스로 다시 불러오기·당겨서 새로고침

**Files:**
- Create: `app/lib/core/error/async_body.dart`
- Modify: `app/lib/core/error/error_messages.dart`
- Modify: `app/test/support/customer_test_app.dart`
- Create: `app/test/core/error/async_body_test.dart`
- Modify: `app/test/features/visit/state/upload_queue_test.dart`

**Interfaces:**
- Consumes: 작업 1(`kindOf`·`ErrorKind.retryable`·`loadMessageFor`), 작업 3(`AppErrorBanner`·`AppErrorRetry(onRetry, onBack)`), `core/proxy/network_watcher.dart`의 `networkWatcherProvider`(`Stream<void> restored`), `test/support/upload_fakes.dart`의 `FakeNetworkWatcher`.
- Produces: `core/error/async_body.dart` — `AsyncBody<T>({required AsyncValue<T> value, required VoidCallback onRetry, required Widget Function(T) builder, Future<void> Function()? onRefresh})`(높이를 채움, 띠 + `Expanded`), `AsyncBody<T>.inline({value, onRetry, builder, Widget? placeholder})`(흐름 안, 처음 불러오는 동안 `placeholder`). 상수 `offlineBannerMessage`(`error_messages.dart`). 테스트 준비물 `CustomerTestSetup`이 `networkWatcherProvider`를 `FakeNetworkWatcher`로 늘 바꿔 끼우고 `setup.network`로 내놓는다 — 같은 프로바이더를 두 번 override 하면 Riverpod 이 거절하므로 `upload_queue_test.dart`는 자기 것 대신 `setup.network`를 쓴다.

설계 3절. 네 상태: 값 없이 로딩 → 로딩(또는 `placeholder`), 값 없이 실패 → `AppErrorRetry`(원인 문구, 다시 해 볼 만하면 [다시 시도], 아니면 `Navigator.canPop`일 때 [돌아가기]), 값 있는데 새로 불러오다 실패 → `builder` 그대로 + 위에 `AppErrorBanner`(인터넷 없음은 [다시 시도] 없이 스스로, 권한·없음도 없음), 성공 → 띠 없음. 다시 시도 중(오류를 품은 로딩)은 로딩이다 — 누른 게 먹혔는지 보이게. **복귀 신호는 오류가 인터넷 없음인 동안만 듣는다** — 멀쩡한 화면은 듣지 않고, 테스트에는 연결 상태 플러그인이 없어 늘 들으면 `MissingPluginException`이 난다(참조 구현에서 홈 셸 골든이 이렇게 깨졌다). 당겨서 새로고침의 실패는 `value`의 오류(띠)로 보이므로 `onRefresh`의 예외는 삼킨다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/support/customer_test_app.dart`:

```diff
@@ -1,4 +1,5 @@
 import 'package:chagocnote/core/proxy/api_client.dart';
+import 'package:chagocnote/core/proxy/network_watcher.dart';
 import 'package:chagocnote/core/proxy/providers.dart';
 import 'package:chagocnote/core/router/app_router.dart';
 import 'package:chagocnote/core/storage/prefs_store.dart';
@@ -14,6 +15,7 @@ import 'package:flutter_riverpod/misc.dart' show Override;
 
 import 'fake_http_client_adapter.dart';
 import 'fake_session_gateway.dart';
+import 'upload_fakes.dart';
 
 /// 고객 기능 테스트의 매장(3번, 첫 입점 매장 이름).
 const customerTestShopId = 3;
@@ -52,6 +54,8 @@ class CustomerTestSetup {
       overrides: [
         sessionGatewayProvider.overrideWithValue(gateway),
         prefsStoreProvider.overrideWithValue(prefs),
+        // 테스트에는 연결 상태 플러그인이 없다 — 인터넷 복귀 신호는 [network]로 보낸다.
+        networkWatcherProvider.overrideWithValue(network),
         apiClientProvider.overrideWith(
           (ref) => ApiClient(
             tokenStore: MemoryTokenStore(),
@@ -67,6 +71,7 @@ class CustomerTestSetup {
 
   final FakeHttpClientAdapter adapter;
   final FakeSessionGateway gateway;
+  final network = FakeNetworkWatcher();
   final MemoryPrefsStore prefs;
   late final ProviderContainer container;
```

`app/test/core/error/async_body_test.dart`:

```dart
import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/async_body.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/upload_fakes.dart';

/// 부를 때마다 [next]의 앞에서 하나를 꺼내 돌려주거나(목록) 기다리거나(Completer) 던지는 목록 원본.
class _Source {
  final next = <Object>[];
  var calls = 0;

  Future<List<String>> load() async {
    calls++;
    final item = next.removeAt(0);
    if (item is List<String>) return item;
    if (item is Completer<List<String>>) return item.future;
    throw item;
  }
}

final _sourceProvider = Provider<_Source>((ref) => throw UnimplementedError());

final _listProvider = FutureProvider<List<String>>(
  (ref) => ref.read(_sourceProvider).load(),
);

final _offline = ApiException.network('timeout');
final _server = ApiException(statusCode: 503, code: 'HTTP_ERROR', message: 'x');
final _gone = ApiException(
  statusCode: 404,
  code: 'VISIT_NOT_FOUND',
  message: 'x',
);

class _Body extends ConsumerWidget {
  const _Body({this.refresh = false});

  final bool refresh;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncBody<List<String>>(
      value: ref.watch(_listProvider),
      onRetry: () => ref.invalidate(_listProvider),
      onRefresh: refresh ? () => ref.refresh(_listProvider.future) : null,
      builder: (items) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [for (final i in items) ListTile(title: Text(i))],
      ),
    );
  }
}

Future<(_Source, FakeNetworkWatcher)> _pump(
  WidgetTester tester,
  List<Object> results, {
  bool refresh = false,
  bool pushed = false,
}) async {
  final source = _Source()..next.addAll(results);
  final network = FakeNetworkWatcher();
  Widget body = Scaffold(body: _Body(refresh: refresh));
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        _sourceProvider.overrideWithValue(source),
        networkWatcherProvider.overrideWithValue(network),
      ],
      retry: (_, _) => null,
      child: MaterialApp(
        home: pushed
            ? Builder(
                builder: (context) => Scaffold(
                  body: TextButton(
                    onPressed: () => Navigator.of(
                      context,
                    ).push(MaterialPageRoute<void>(builder: (_) => body)),
                    child: const Text('열기'),
                  ),
                ),
              )
            : body,
      ),
    ),
  );
  if (pushed) {
    await tester.tap(find.text('열기'));
  }
  await tester.pumpAndSettle();
  return (source, network);
}

Future<void> _retry(WidgetTester tester) async {
  await tester.tap(find.text(AppStrings.retry));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('처음 불러오는 중이면 로딩, 받으면 내용을 보인다', (tester) async {
    final source = _Source();
    final gate = Completer<List<String>>();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          _sourceProvider.overrideWithValue(source),
          networkWatcherProvider.overrideWithValue(FakeNetworkWatcher()),
          _listProvider.overrideWith((ref) => gate.future),
        ],
        child: const MaterialApp(home: Scaffold(body: _Body())),
      ),
    );
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    gate.complete(['콩이']);
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('inline 에 placeholder 를 주면 처음 불러오는 동안 로딩 대신 그것을 보인다(달력의 빈 칸)', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          networkWatcherProvider.overrideWithValue(FakeNetworkWatcher()),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: AsyncBody<int>.inline(
              value: const AsyncLoading(),
              onRetry: () {},
              placeholder: const Text('빈 칸'),
              builder: (v) => Text('$v'),
            ),
          ),
        ),
      ),
    );
    expect(find.text('빈 칸'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('값 없이 인터넷 없음이면 불러오기 문구와 [다시 시도], 인터넷이 돌아오면 스스로 다시 불러온다', (
    tester,
  ) async {
    final (source, network) = await _pump(tester, [
      _offline,
      ['콩이'],
    ]);
    expect(find.text(offlineLoadMessage), findsOneWidget);
    expect(find.text(AppStrings.retry), findsOneWidget);

    network.restore();
    await tester.pumpAndSettle();
    expect(source.calls, 2);
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('다시 시도하는 동안은 오류 대신 로딩을 보인다', (tester) async {
    final gate = Completer<List<String>>();
    await _pump(tester, [_server, gate]);

    await tester.tap(find.text(AppStrings.retry));
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);

    gate.complete(['콩이']);
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('서버 오류로 실패하면 인터넷이 돌아와도 스스로 다시 부르지 않는다', (tester) async {
    final (source, network) = await _pump(tester, [_server]);
    expect(
      find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
      findsOneWidget,
    );
    network.restore();
    await tester.pumpAndSettle();
    expect(source.calls, 1);
  });

  testWidgets('없어진 것(404)은 [다시 시도] 대신, 뒤로 갈 수 있으면 [돌아가기]', (tester) async {
    await _pump(tester, [_gone], pushed: true);
    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);

    await tester.tap(find.text(AppStrings.goBack));
    await tester.pumpAndSettle();
    expect(find.text('열기'), findsOneWidget);
  });

  testWidgets('뒤로 갈 곳이 없으면(탭 화면) 없어진 것은 문구만 보인다', (tester) async {
    await _pump(tester, [_gone]);
    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);
    expect(find.text(AppStrings.goBack), findsNothing);
  });

  testWidgets('받은 데이터가 있는데 새로 불러오다 서버 오류면 내용은 그대로, 위에 띠와 [다시 시도]', (
    tester,
  ) async {
    final (source, _) = await _pump(tester, [
      ['콩이'],
    ], refresh: true);
    source.next.addAll([
      _server,
      ['콩이', '보리'],
    ]);

    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
    expect(
      find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
      findsOneWidget,
    );

    await _retry(tester);
    expect(find.text('보리'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);
  });

  testWidgets('받은 데이터 위 인터넷 없음은 [다시 시도] 없는 띠, 인터넷이 돌아오면 스스로 다시 불러와 띠가 사라진다', (
    tester,
  ) async {
    final (source, network) = await _pump(tester, [
      ['콩이'],
    ], refresh: true);
    source.next.addAll([
      _offline,
      ['콩이', '보리'],
    ]);

    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(find.text(offlineBannerMessage), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);

    network.restore();
    await tester.pumpAndSettle();
    expect(find.text('보리'), findsOneWidget);
    expect(find.text(offlineBannerMessage), findsNothing);
  });
}
```

`app/test/features/visit/state/upload_queue_test.dart`:

```diff
@@ -3,7 +3,6 @@ import 'dart:convert';
 import 'dart:io';
 
 import 'package:chagocnote/core/proxy/app_dirs.dart';
-import 'package:chagocnote/core/proxy/network_watcher.dart';
 import 'package:chagocnote/core/proxy/photo_renditions.dart';
 import 'package:chagocnote/core/proxy/providers.dart';
 import 'package:chagocnote/features/auth/api/social_sign_in.dart';
@@ -42,7 +41,6 @@ class _Env {
       overrides: [
         uploadsDirProvider.overrideWith((ref) async => root),
         photoRenditionMakerProvider.overrideWithValue(maker),
-        networkWatcherProvider.overrideWithValue(network),
         uploadRetrySchedulerProvider.overrideWithValue(retries.call),
         uploadDioProvider.overrideWithValue(
           Dio(BaseOptions())..httpClientAdapter = storage,
@@ -54,7 +52,7 @@ class _Env {
   final Directory root;
   late final CustomerTestSetup setup;
   final maker = FakeRenditionMaker();
-  final network = FakeNetworkWatcher();
+  FakeNetworkWatcher get network => setup.network;
   final retries = FakeRetryScheduler();
 
   /// 발급할 때마다 51, 52… 를 준다.
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/core/error/async_body_test.dart`
Expected: 컴파일 실패 — `async_body.dart`가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/error/async_body.dart`:

```dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../design/widgets/app_error_banner.dart';
import '../../design/widgets/app_error_retry.dart';
import '../proxy/network_watcher.dart';
import 'error_kind.dart';
import 'error_messages.dart';

/// 서버에서 읽는 화면 본문의 틀 — 불러오는 중·처음부터 실패·받은 데이터 위 실패·성공을 한 곳에서
/// 그린다(오류 화면 다듬기 설계 3절).
///
/// - 값이 없고 실패면 [AppErrorRetry] — 원인 문구와 원인 행동(다시 시도, 또는 뒤로 갈 수 있으면 돌아가기).
/// - 값이 있는데 새로 불러오다 실패면 [builder]를 그대로 두고 위에 [AppErrorBanner].
/// - 이 틀이 화면에 있는 동안 인터넷이 돌아오면, 오류가 인터넷 없음일 때 [onRetry]를 한 번 부른다.
/// - [onRefresh]가 있으면 당겨서 새로고침. 실패는 [value]의 오류로 보이므로 여기서 삼킨다.
///
/// 저장 실패처럼 누른 일의 오류는 이 틀이 아니라 화면의 문구·스낵바로 보인다(쓰던 내용을 지우지 않는다).
class AsyncBody<T> extends ConsumerStatefulWidget {
  const AsyncBody({
    super.key,
    required this.value,
    required this.onRetry,
    required this.builder,
    this.onRefresh,
  }) : inline = false,
       placeholder = null;

  /// 흐름 안에 놓이는 자리(달력, 탭 안) — 높이를 채우지 않고, 오류는 [AppErrorRetry.inline].
  /// [placeholder]를 주면 처음 불러오는 동안 로딩 대신 그것을 보인다(달력은 빈 칸을 먼저 그린다).
  const AsyncBody.inline({
    super.key,
    required this.value,
    required this.onRetry,
    required this.builder,
    this.placeholder,
  }) : inline = true,
       onRefresh = null;

  final AsyncValue<T> value;
  final VoidCallback onRetry;
  final Widget Function(T data) builder;
  final Future<void> Function()? onRefresh;
  final bool inline;
  final Widget? placeholder;

  @override
  ConsumerState<AsyncBody<T>> createState() => _AsyncBodyState<T>();
}

class _AsyncBodyState<T> extends ConsumerState<AsyncBody<T>> {
  StreamSubscription<void>? _restored;

  @override
  void initState() {
    super.initState();
    _watchNetwork();
  }

  @override
  void didUpdateWidget(AsyncBody<T> oldWidget) {
    super.didUpdateWidget(oldWidget);
    _watchNetwork();
  }

  @override
  void dispose() {
    _restored?.cancel();
    super.dispose();
  }

  /// 오류가 인터넷 없음인 동안만 복귀 신호를 듣는다 — 멀쩡한 화면은 듣지 않는다.
  void _watchNetwork() {
    final value = widget.value;
    final offline =
        value.hasError && kindOf(value.error!) == ErrorKind.offline;
    if (offline && _restored == null) {
      _restored = ref.read(networkWatcherProvider).restored.listen((_) {
        _restored?.cancel();
        _restored = null;
        widget.onRetry();
      });
    } else if (!offline && _restored != null) {
      _restored!.cancel();
      _restored = null;
    }
  }

  Future<void> _refresh() async {
    try {
      await widget.onRefresh!();
    } catch (_) {
      // 실패는 value 의 오류(띠)로 보인다.
    }
  }

  @override
  Widget build(BuildContext context) {
    final value = widget.value;
    if (!value.hasValue) {
      // 다시 시도 중(오류를 품은 로딩)이면 오류 대신 로딩을 보인다.
      if (value.hasError && !value.isLoading) {
        return _failure(context, value.error!);
      }
      if (widget.placeholder case final placeholder?) return placeholder;
      return widget.inline
          ? const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            )
          : const Center(child: CircularProgressIndicator());
    }
    Widget content = widget.builder(value.requireValue);
    if (widget.onRefresh != null) {
      content = RefreshIndicator(onRefresh: _refresh, child: content);
    }
    final banner = AnimatedSize(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
      alignment: Alignment.topCenter,
      child: value.hasError ? _banner(value.error!) : const SizedBox.shrink(),
    );
    return widget.inline
        ? Column(mainAxisSize: MainAxisSize.min, children: [banner, content])
        : Column(children: [banner, Expanded(child: content)]);
  }

  Widget _failure(BuildContext context, Object error) {
    final kind = kindOf(error);
    final navigator = Navigator.of(context);
    final onRetry = kind.retryable ? widget.onRetry : null;
    final onBack = !kind.retryable && navigator.canPop()
        ? () => navigator.maybePop()
        : null;
    final message = loadMessageFor(error);
    return widget.inline
        ? AppErrorRetry.inline(
            message: message,
            onRetry: onRetry,
            onBack: onBack,
          )
        : AppErrorRetry(message: message, onRetry: onRetry, onBack: onBack);
  }

  Widget _banner(Object error) {
    final kind = kindOf(error);
    final offline = kind == ErrorKind.offline;
    return AppErrorBanner(
      message: offline ? offlineBannerMessage : loadMessageFor(error),
      offline: offline,
      // 인터넷 없음은 스스로 잇고, 권한·없음은 다시 해도 같다.
      onRetry: !offline && kind.retryable ? widget.onRetry : null,
    );
  }
}
```

`app/lib/core/error/error_messages.dart`:

```diff
@@ -67,6 +67,9 @@ const String offlineActionMessage = '인터넷에 연결되지 않았어요. 연
 /// 인터넷 없음 — 화면을 불러오지 못했을 때. 인터넷이 돌아오면 화면이 스스로 다시 불러온다.
 const String offlineLoadMessage = '인터넷에 연결되지 않았어요. 연결되면 다시 불러올게요.';
 
+/// 인터넷 없음 — 받은 데이터 위의 띠.
+const String offlineBannerMessage = '인터넷에 연결되지 않았어요 · 이전 내용이에요';
+
 const String _server = '서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.';
 
 const String _fallback = '문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/core/error/async_body_test.dart` → 9 passed

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 680 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 복귀 조건 `value.hasError && kindOf(value.error!) == ErrorKind.offline`을 `value.hasError`로 → `async_body_test.dart::서버 오류로 실패하면 인터넷이 돌아와도 스스로 다시 부르지 않는다` 실패.
- `value.hasError && !value.isLoading`을 `value.hasError`로 → `다시 시도하는 동안은 오류 대신 로딩을 보인다` 실패.
- 띠의 `onRetry: !offline && kind.retryable ? …`에서 `!offline &&`를 빼면 → `받은 데이터 위 인터넷 없음은 [다시 시도] 없는 띠…` 실패.
- `!kind.retryable && navigator.canPop()`에서 `&& navigator.canPop()`을 빼면 → `뒤로 갈 곳이 없으면(탭 화면) 없어진 것은 문구만 보인다` 실패.
- `_refresh`의 `catch`에서 `rethrow` → `받은 데이터가 있는데 새로 불러오다 서버 오류면…` 실패.
- `if (widget.placeholder case final placeholder?) return placeholder;`를 지우면 → `inline 에 placeholder 를 주면…` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 화면 본문 틀 AsyncBody — 불러오는 중·처음 실패·받은 데이터 위 띠·인터넷 복귀 때 스스로 다시 불러오기·당겨서 새로고침

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 목록 화면을 `AsyncBody`로 — 피드·고객 목록·하루 목록 당겨서 새로고침과 띠, 달력은 빈 칸을 먼저, 다음 쪽 인터넷 없음은 복귀 때 다시

**Files:**
- Modify: `app/lib/features/visit/state/feed_controller.dart`
- Modify: `app/lib/features/customer/state/customer_list_controller.dart`
- Modify: `app/lib/features/visit/screens/feed_view.dart`
- Modify: `app/lib/features/customer/screens/customer_list_tab.dart`
- Modify: `app/lib/features/visit/screens/day_screen.dart`
- Modify: `app/lib/features/visit/screens/calendar_tab.dart`
- Modify: `app/test/features/customer/screens/customer_list_tab_test.dart`
- Modify: `app/test/features/customer/state/customer_list_controller_test.dart`
- Modify: `app/test/features/visit/screens/calendar_tab_test.dart`
- Modify: `app/test/features/visit/screens/day_screen_test.dart`
- Modify: `app/test/features/visit/state/feed_controller_test.dart`

**Interfaces:**
- Consumes: 작업 4 `AsyncBody`·`AsyncBody.inline(placeholder:)`·`setup.network`, 작업 1 `loadMessageFor`·`kindOf`.
- Produces: `FeedController`·`CustomerListController`가 다음 쪽이 인터넷 없음으로 실패한 동안만 복귀 신호를 듣고 돌아오면 `loadMore()`를 한 번. 피드(`FeedList`·`PetRecordsView`)·고객 목록 탭·하루 화면·달력(월 격자)이 `AsyncBody`를 쓴다. 빈 목록도 당길 수 있게 `CustomScrollView` + `SliverFillRemaining`, 목록은 `AlwaysScrollableScrollPhysics`.

설계 3절의 목록 넷(피드·고객 목록·하루 목록·[기록] 탭 — [기록] 탭은 반려동물 상세 안이라 당기기는 작업 6). 고객 목록은 조건이 바뀌어 새로 불러오는 동안 앞선 결과를 보이던 `_lastShown`을 `AsyncData(shown)`로 넘겨 그대로 지킨다. 달력은 처음 불러오는 동안 빈 격자를 그리던 대로 `placeholder`로 둔다. 달력 미리보기의 오류는 문구만 `loadMessageFor`로(스스로 다시 부르지 않는다 — 007 남는 것). 이 작업에서 ④-2b 가 미뤘던 피드 당겨서 새로고침·다음 쪽 실패 위젯 테스트를 채운다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/customer/screens/customer_list_tab_test.dart`:

```diff
@@ -1,11 +1,13 @@
 import 'dart:async';
 
+import 'package:chagocnote/core/error/error_messages.dart';
 import 'package:chagocnote/core/proxy/media_images.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/core/storage/prefs_store.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/design/widgets/app_photo_tile.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
+import 'package:dio/dio.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
 
@@ -287,6 +289,36 @@ void main() {
     expect(_listQueries(setup).where((q) => q['cursor'] == 'c1'), hasLength(2));
   });
 
+  testWidgets('당겨서 새로고침이 실패하면 목록은 두고 위에 띠, 인터넷 없음은 [다시 시도] 없이 돌아오면 스스로 다시 읽는다', (
+    tester,
+  ) async {
+    var offline = false;
+    final setup = CustomerTestSetup((options, body) {
+      if (offline) {
+        throw DioException.connectionError(
+          requestOptions: options,
+          reason: 'offline',
+        );
+      }
+      return FakeResponse(statusCode: 200, data: _twoFamilies);
+    });
+    addTearDown(setup.container.dispose);
+    await _openTab(tester, setup);
+
+    offline = true;
+    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
+    await tester.pumpAndSettle();
+    expect(find.text(offlineBannerMessage), findsOneWidget);
+    expect(find.text('콩이'), findsOneWidget);
+    expect(find.text(AppStrings.retry), findsNothing);
+
+    offline = false;
+    setup.network.restore();
+    await tester.pumpAndSettle();
+    expect(find.text(offlineBannerMessage), findsNothing);
+    expect(_listQueries(setup), hasLength(3));
+  });
+
   testWidgets('"최근 방문순"을 누르면 sort=last_visit 으로 다시 부른다', (tester) async {
     final setup = CustomerTestSetup(
       (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
```

`app/test/features/customer/state/customer_list_controller_test.dart`:

```diff
@@ -3,6 +3,7 @@ import 'dart:async';
 import 'package:chagocnote/core/error/api_exception.dart';
 import 'package:chagocnote/features/auth/state/session_controller.dart';
 import 'package:chagocnote/features/customer/state/customer_list_controller.dart';
+import 'package:dio/dio.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
 
@@ -129,6 +130,46 @@ void main() {
     expect(state.loadMoreError, isA<ApiException>());
   });
 
+  test('다음 페이지가 인터넷 없음으로 실패했으면 인터넷이 돌아올 때 한 번 다시 부른다', () async {
+    var online = false;
+    final setup = CustomerTestSetup((options, body) {
+      if (options.queryParameters['cursor'] == null) {
+        return FakeResponse(
+          statusCode: 200,
+          data: pageJson(items: [familyJson(customerId: 1)], nextCursor: 'c1'),
+        );
+      }
+      if (!online) {
+        throw DioException.connectionError(
+          requestOptions: options,
+          reason: 'offline',
+        );
+      }
+      return FakeResponse(
+        statusCode: 200,
+        data: pageJson(items: [familyJson(customerId: 2)]),
+      );
+    });
+    addTearDown(setup.container.dispose);
+    _listen(setup.container, _query);
+    await setup.container.read(customerListControllerProvider(_query).future);
+
+    await setup.container
+        .read(customerListControllerProvider(_query).notifier)
+        .loadMore();
+    expect(
+      setup.container.read(customerListControllerProvider(_query)).value!.loadMoreError,
+      isA<ApiException>().having((e) => e.isNetwork, 'isNetwork', isTrue),
+    );
+
+    online = true;
+    setup.network.restore();
+    await pumpEventQueue();
+    final state = setup.container.read(customerListControllerProvider(_query)).value!;
+    expect(state.items.map((c) => c.customerId), [1, 2]);
+    expect(state.loadMoreError, isNull);
+  });
+
   test('다음 페이지를 기다리는 사이 다시 불러오면 옛 목록에 이어 붙이지 않는다', () async {
     final gate = Completer<FakeResponse>();
     var firstPages = 0;
```

`app/test/features/visit/screens/calendar_tab_test.dart`:

```diff
@@ -426,6 +426,63 @@ void main() {
       );
     });
 
+    testWidgets('다음 쪽이 실패하면 목록 끝에 원인 문구와 [다시 시도], 누르면 이어 붙인다', (tester) async {
+      final backend = feedBackend(first: 6);
+      final ok = backend.routes['GET /v1/shops/3/visits/feed']!;
+      var failNext = true;
+      backend.routes['GET /v1/shops/3/visits/feed'] = (o, b) {
+        if (o.queryParameters['cursor'] != null && failNext) {
+          failNext = false;
+          return const FakeResponse(statusCode: 503, data: 'x');
+        }
+        return ok(o, b);
+      };
+      final app = build(backend);
+      await app.setup.prefs.write(PrefsKeys.calendarViewMode, 'feed');
+      await _pumpHome(tester, app.setup);
+
+      final retry = find.byWidgetPredicate(
+        (w) => w is AppButton && w.label == AppStrings.retry,
+      );
+      await tester.dragUntilVisible(
+        retry,
+        find.byType(ListView),
+        const Offset(0, -300),
+      );
+      await settle(tester);
+      expect(
+        find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
+        findsOneWidget,
+      );
+
+      await tester.tap(retry);
+      await settle(tester);
+      await tester.dragUntilVisible(
+        find.text('보리'),
+        find.byType(ListView),
+        const Offset(0, -300),
+      );
+      expect(find.text('보리'), findsOneWidget);
+    });
+
+    testWidgets('당겨서 새로고침하면 첫 쪽부터 다시 읽는다', (tester) async {
+      final app = build(feedBackend());
+      await app.setup.prefs.write(PrefsKeys.calendarViewMode, 'feed');
+      await _pumpHome(tester, app.setup);
+
+      await tester.fling(find.text('두부'), const Offset(0, 400), 1000);
+      await settle(tester);
+
+      expect(
+        [
+          for (final r in app.setup.adapter.requests)
+            if (r.path == '/v1/shops/3/visits/feed')
+              r.queryParameters['cursor'],
+        ],
+        [null, null],
+      );
+    });
+
     testWidgets('이름·품종이 길면 이름 카드는 사진 안에서 한 줄로 줄인다', (tester) async {
       const name = '초코송이바닐라라떼크림치즈케이크마카롱';
       const breed = '미니어처오스트레일리안셰퍼드골든리트리버래브라도푸들믹스';
```

`app/test/features/visit/screens/day_screen_test.dart`:

```diff
@@ -598,6 +598,36 @@ void main() {
     expect(find.text('두부 · 보리'), findsOneWidget);
   });
 
+  testWidgets('당겨서 새로고침하면 다시 읽고, 실패하면 목록은 두고 위에 띠를 보인다 — 띠의 [다시 시도]로 다시 읽는다', (
+    tester,
+  ) async {
+    var fail = false;
+    var calls = 0;
+    final backend = _backend();
+    final ok = backend.routes['GET /v1/shops/3/visits']!;
+    backend.routes['GET /v1/shops/3/visits'] = (o, b) {
+      calls++;
+      return fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
+    };
+    final setup = CustomerTestSetup(backend.call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _open(tester, setup);
+    expect(calls, 1);
+
+    fail = true;
+    await tester.fling(find.text('두부 · 보리'), const Offset(0, 400), 1000);
+    await settle(tester);
+    expect(calls, 2);
+    expect(find.text('두부 · 보리'), findsOneWidget, reason: '받은 목록은 그대로');
+    expect(find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'), findsOneWidget);
+
+    fail = false;
+    await tester.tap(find.text(AppStrings.retry));
+    await settle(tester);
+    expect(calls, 3);
+    expect(find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'), findsNothing);
+  });
+
   testWidgets('하루 목록 골든', (tester) async {
     final setup = CustomerTestSetup(_backend().call, overrides: _today);
     addTearDown(setup.container.dispose);
```

`app/test/features/visit/state/feed_controller_test.dart`:

```diff
@@ -1,6 +1,7 @@
 import 'dart:async';
 
 import 'package:chagocnote/core/error/api_exception.dart';
+import 'package:dio/dio.dart';
 import 'package:chagocnote/features/visit/state/feed_controller.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
@@ -95,6 +96,54 @@ void main() {
     expect(state.loadMoreError, isA<ApiException>());
   });
 
+  test('다음 쪽이 인터넷 없음으로 실패했으면 인터넷이 돌아올 때 한 번 다시 부른다 — 서버 오류면 부르지 않는다', () async {
+    var failure = 'offline';
+    final setup = CustomerTestSetup((options, body) {
+      if (options.queryParameters['cursor'] == null) {
+        return FakeResponse(
+          statusCode: 200,
+          data: feedJson(items: [feedItemJson(visitId: 1)], nextCursor: 'c1'),
+        );
+      }
+      switch (failure) {
+        case 'offline':
+          throw DioException.connectionError(
+            requestOptions: options,
+            reason: 'offline',
+          );
+        case 'server':
+          return const FakeResponse(statusCode: 503, data: 'x');
+      }
+      return FakeResponse(
+        statusCode: 200,
+        data: feedJson(items: [feedItemJson(visitId: 2)]),
+      );
+    });
+    addTearDown(setup.container.dispose);
+    _listen(setup.container, _all);
+    await setup.container.read(feedControllerProvider(_all).future);
+    final notifier = setup.container.read(feedControllerProvider(_all).notifier);
+
+    await notifier.loadMore();
+    failure = 'server';
+    setup.network.restore();
+    await pumpEventQueue();
+    expect(
+      setup.container.read(feedControllerProvider(_all)).value!.loadMoreError,
+      isA<ApiException>().having((e) => e.code, 'code', 'HTTP_ERROR'),
+      reason: '인터넷 없음이었으니 돌아오자 한 번 다시 불렀다(이번엔 서버 오류)',
+    );
+
+    failure = 'none';
+    setup.network.restore();
+    await pumpEventQueue();
+    expect(
+      setup.adapter.requests.where((r) => r.queryParameters['cursor'] != null),
+      hasLength(2),
+      reason: '서버 오류는 인터넷이 돌아와도 스스로 다시 부르지 않는다',
+    );
+  });
+
   test('다음 쪽을 기다리는 사이 다시 불러오면(기록 저장 뒤) 옛 목록에 이어 붙이지 않는다', () async {
     final gate = Completer<FakeResponse>();
     var firstPages = 0;
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/features/visit/state/feed_controller_test.dart test/features/customer/state/customer_list_controller_test.dart test/features/visit/screens/day_screen_test.dart test/features/visit/screens/calendar_tab_test.dart test/features/customer/screens/customer_list_tab_test.dart`
Expected: 새 테스트 다섯 실패 — 복귀 때 다음 쪽을 다시 부르지 않고, 당겨도 다시 읽지 않고(새로고침이 없다), 띠가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/state/feed_controller.dart`:

```diff
@@ -1,5 +1,9 @@
+import 'dart:async';
+
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../core/error/error_kind.dart';
+import '../../../core/proxy/network_watcher.dart';
 import '../../auth/state/shop_scoped.dart';
 import '../api/feed_models.dart';
 import 'visit_providers.dart';
@@ -38,6 +42,15 @@ class FeedController extends AsyncNotifier<FeedState> {
   /// 붙이지 않게 비교한다(고객 목록과 같은 이유).
   int _generation = 0;
 
+  /// 다음 쪽이 인터넷 없음으로 실패한 동안만 복귀 신호를 듣는다 — 돌아오면 한 번 다시 부른다
+  /// (오류 화면 다듬기 설계 3절).
+  StreamSubscription<void>? _restored;
+
+  void _stopWatchingNetwork() {
+    _restored?.cancel();
+    _restored = null;
+  }
+
   Future<VisitFeed> _fetch(String? cursor) => runShopScoped(
     ref,
     () => ref
@@ -48,6 +61,7 @@ class FeedController extends AsyncNotifier<FeedState> {
   @override
   Future<FeedState> build() async {
     _generation++;
+    ref.onDispose(_stopWatchingNetwork);
     final page = await _fetch(null);
     return FeedState(items: page.items, nextCursor: page.nextCursor);
   }
@@ -82,6 +96,12 @@ class FeedController extends AsyncNotifier<FeedState> {
       );
     } catch (e) {
       if (stale()) return;
+      if (kindOf(e) == ErrorKind.offline) {
+        _restored ??= ref.read(networkWatcherProvider).restored.listen((_) {
+          _stopWatchingNetwork();
+          loadMore();
+        });
+      }
       state = AsyncData(
         FeedState(
           items: current.items,
```

`app/lib/features/customer/state/customer_list_controller.dart`:

```diff
@@ -1,5 +1,9 @@
+import 'dart:async';
+
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../core/error/error_kind.dart';
+import '../../../core/proxy/network_watcher.dart';
 import '../../auth/state/shop_scoped.dart';
 import '../api/customer_api.dart';
 import '../api/customer_models.dart';
@@ -50,6 +54,15 @@ class CustomerListController extends AsyncNotifier<CustomerListState> {
   /// 다시 불러와도 컨트롤러 인스턴스는 그대로라 `ref.mounted`만으로는 모른다.
   int _generation = 0;
 
+  /// 다음 페이지가 인터넷 없음으로 실패한 동안만 복귀 신호를 듣는다 — 돌아오면 한 번 다시 부른다
+  /// (오류 화면 다듬기 설계 3절).
+  StreamSubscription<void>? _restored;
+
+  void _stopWatchingNetwork() {
+    _restored?.cancel();
+    _restored = null;
+  }
+
   Future<CustomerPage> _fetch(String? cursor) => _api.list(
     query.shopId,
     q: query.q,
@@ -61,6 +74,7 @@ class CustomerListController extends AsyncNotifier<CustomerListState> {
   @override
   Future<CustomerListState> build() async {
     _generation++;
+    ref.onDispose(_stopWatchingNetwork);
     final page = await runShopScoped(ref, () => _fetch(null));
     return CustomerListState(
       items: page.items,
@@ -102,6 +116,12 @@ class CustomerListController extends AsyncNotifier<CustomerListState> {
       );
     } catch (e) {
       if (stale()) return;
+      if (kindOf(e) == ErrorKind.offline) {
+        _restored ??= ref.read(networkWatcherProvider).restored.listen((_) {
+          _stopWatchingNetwork();
+          loadMore();
+        });
+      }
       state = AsyncData(
         CustomerListState(
           items: current.items,
```

`app/lib/features/visit/screens/feed_view.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/proxy/media_images.dart';
 import '../../../design/tokens/app_colors.dart';
@@ -57,46 +58,48 @@ class _FeedListState extends ConsumerState<FeedList> {
   @override
   Widget build(BuildContext context) {
     final provider = feedControllerProvider(widget.query);
-    final async = ref.watch(provider);
-    final state = async.value;
-    if (state == null) {
-      return async.hasError
-          ? AppErrorRetry(
-              message: messageFor(async.error!),
-              onRetry: () => ref.invalidate(provider),
-            )
-          : const Center(child: CircularProgressIndicator());
-    }
-    if (state.items.isEmpty) return const _Empty();
-    // 아래 여백은 떠 있는 탭바와 + 버튼 몫이다.
-    return ListView.builder(
-      controller: _scroll,
-      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
-      itemCount: state.items.length + 1,
-      itemBuilder: (context, index) {
-        if (index < state.items.length) {
-          return Padding(
-            padding: const EdgeInsets.only(bottom: AppSpacing.lg),
-            child: FeedCard(item: state.items[index]),
-          );
-        }
-        if (state.loadingMore) {
-          return const Padding(
-            padding: EdgeInsets.all(AppSpacing.lg),
-            child: Center(child: CircularProgressIndicator()),
-          );
-        }
-        if (state.loadMoreError != null) {
-          return Padding(
-            padding: const EdgeInsets.all(AppSpacing.lg),
-            child: AppErrorRetry.row(
-              message: messageFor(state.loadMoreError!),
-              onRetry: () => ref.read(provider.notifier).loadMore(),
+    return AsyncBody<FeedState>(
+      value: ref.watch(provider),
+      onRetry: () => ref.invalidate(provider),
+      onRefresh: () => ref.refresh(provider.future),
+      builder: (state) => state.items.isEmpty
+          ? const _Empty()
+          // 아래 여백은 떠 있는 탭바와 + 버튼 몫이다.
+          : ListView.builder(
+              controller: _scroll,
+              physics: const AlwaysScrollableScrollPhysics(),
+              padding: const EdgeInsets.fromLTRB(
+                AppSpacing.lg,
+                0,
+                AppSpacing.lg,
+                120,
+              ),
+              itemCount: state.items.length + 1,
+              itemBuilder: (context, index) {
+                if (index < state.items.length) {
+                  return Padding(
+                    padding: const EdgeInsets.only(bottom: AppSpacing.lg),
+                    child: FeedCard(item: state.items[index]),
+                  );
+                }
+                if (state.loadingMore) {
+                  return const Padding(
+                    padding: EdgeInsets.all(AppSpacing.lg),
+                    child: Center(child: CircularProgressIndicator()),
+                  );
+                }
+                if (state.loadMoreError != null) {
+                  return Padding(
+                    padding: const EdgeInsets.all(AppSpacing.lg),
+                    child: AppErrorRetry.row(
+                      message: loadMessageFor(state.loadMoreError!),
+                      onRetry: () => ref.read(provider.notifier).loadMore(),
+                    ),
+                  );
+                }
+                return const SizedBox.shrink();
+              },
             ),
-          );
-        }
-        return const SizedBox.shrink();
-      },
     );
   }
 }
@@ -113,48 +116,41 @@ class PetRecordsView extends ConsumerWidget {
     final shopId = ref.watch(selectedShopIdProvider);
     if (shopId == null) return const SizedBox.shrink();
     final provider = feedControllerProvider((shopId: shopId, petId: petId));
-    final async = ref.watch(provider);
-    final state = async.value;
-    if (state == null) {
-      return async.hasError
-          ? AppErrorRetry.inline(
-              message: messageFor(async.error!),
-              onRetry: () => ref.invalidate(provider),
-            )
-          : const Padding(
+    return AsyncBody<FeedState>.inline(
+      value: ref.watch(provider),
+      onRetry: () => ref.invalidate(provider),
+      builder: (state) => state.items.isEmpty
+          ? const Padding(
               padding: EdgeInsets.all(AppSpacing.lg),
-              child: Center(child: CircularProgressIndicator()),
-            );
-    }
-    if (state.items.isEmpty) {
-      return const Padding(
-        padding: EdgeInsets.all(AppSpacing.lg),
-        child: Center(
-          child: Text(AppStrings.petRecordsEmpty, style: AppTypography.body),
-        ),
-      );
-    }
-    return Column(
-      crossAxisAlignment: CrossAxisAlignment.stretch,
-      children: [
-        for (final item in state.items)
-          Padding(
-            padding: const EdgeInsets.only(bottom: AppSpacing.lg),
-            child: FeedCard(item: item),
-          ),
-        if (state.loadingMore)
-          const Center(child: CircularProgressIndicator())
-        else if (state.loadMoreError != null)
-          AppErrorRetry.row(
-            message: messageFor(state.loadMoreError!),
-            onRetry: () => ref.read(provider.notifier).loadMore(),
-          )
-        else if (state.hasMore)
-          AppButton(
-            label: AppStrings.loadMore,
-            onPressed: () => ref.read(provider.notifier).loadMore(),
-          ),
-      ],
+              child: Center(
+                child: Text(
+                  AppStrings.petRecordsEmpty,
+                  style: AppTypography.body,
+                ),
+              ),
+            )
+          : Column(
+              crossAxisAlignment: CrossAxisAlignment.stretch,
+              children: [
+                for (final item in state.items)
+                  Padding(
+                    padding: const EdgeInsets.only(bottom: AppSpacing.lg),
+                    child: FeedCard(item: item),
+                  ),
+                if (state.loadingMore)
+                  const Center(child: CircularProgressIndicator())
+                else if (state.loadMoreError != null)
+                  AppErrorRetry.row(
+                    message: loadMessageFor(state.loadMoreError!),
+                    onRetry: () => ref.read(provider.notifier).loadMore(),
+                  )
+                else if (state.hasMore)
+                  AppButton(
+                    label: AppStrings.loadMore,
+                    onPressed: () => ref.read(provider.notifier).loadMore(),
+                  ),
+              ],
+            ),
     );
   }
 }
@@ -162,19 +158,31 @@ class PetRecordsView extends ConsumerWidget {
 class _Empty extends StatelessWidget {
   const _Empty();
 
+  // 비어 있어도 당겨서 새로고침이 되게 스크롤 면에 둔다.
   @override
-  Widget build(BuildContext context) => const Center(
-    child: Padding(
-      padding: EdgeInsets.all(AppSpacing.xl),
-      child: Column(
-        mainAxisSize: MainAxisSize.min,
-        children: [
-          Text(AppStrings.feedEmpty, style: AppTypography.body),
-          SizedBox(height: AppSpacing.xs),
-          Text(AppStrings.feedEmptyCaption, style: AppTypography.caption),
-        ],
+  Widget build(BuildContext context) => const CustomScrollView(
+    physics: AlwaysScrollableScrollPhysics(),
+    slivers: [
+      SliverFillRemaining(
+        hasScrollBody: false,
+        child: Center(
+          child: Padding(
+            padding: EdgeInsets.all(AppSpacing.xl),
+            child: Column(
+              mainAxisSize: MainAxisSize.min,
+              children: [
+                Text(AppStrings.feedEmpty, style: AppTypography.body),
+                SizedBox(height: AppSpacing.xs),
+                Text(
+                  AppStrings.feedEmptyCaption,
+                  style: AppTypography.caption,
+                ),
+              ],
+            ),
+          ),
+        ),
       ),
-    ),
+    ],
   );
 }
```

`app/lib/features/customer/screens/customer_list_tab.dart`:

```diff
@@ -1,6 +1,7 @@
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
@@ -166,23 +167,25 @@ class _CustomerListTabState extends ConsumerState<CustomerListTab> {
           ),
         ),
         Expanded(
-          child: shown != null
-              ? _CardList(
-                  state: shown,
-                  mode: mode,
-                  searching: _q.isNotEmpty,
-                  scroll: _scroll,
-                  onRetryMore: () => ref
-                      .read(customerListControllerProvider(query!).notifier)
-                      .loadMore(),
-                )
-              : async.hasError
-              ? AppErrorRetry(
-                  message: messageFor(async.error!),
-                  onRetry: () =>
-                      ref.invalidate(customerListControllerProvider(query!)),
-                )
-              : const Center(child: CircularProgressIndicator()),
+          child: AsyncBody<CustomerListState>(
+            // 조건이 바뀌어 새로 불러오는 동안은 앞선 결과를 그대로 보인다.
+            value: shown != null && !async.hasValue
+                ? AsyncData(shown)
+                : async,
+            onRetry: () =>
+                ref.invalidate(customerListControllerProvider(query!)),
+            onRefresh: () =>
+                ref.refresh(customerListControllerProvider(query!).future),
+            builder: (state) => _CardList(
+              state: state,
+              mode: mode,
+              searching: _q.isNotEmpty,
+              scroll: _scroll,
+              onRetryMore: () => ref
+                  .read(customerListControllerProvider(query!).notifier)
+                  .loadMore(),
+            ),
+          ),
         ),
       ],
     );
@@ -207,33 +210,43 @@ class _CardList extends StatelessWidget {
   @override
   Widget build(BuildContext context) {
     if (state.items.isEmpty) {
-      return Center(
-        child: Padding(
-          padding: const EdgeInsets.all(AppSpacing.xl),
-          child: Column(
-            mainAxisSize: MainAxisSize.min,
-            children: [
-              Text(
-                searching
-                    ? AppStrings.customersNoMatch
-                    : AppStrings.customersEmpty,
-                style: AppTypography.body,
-              ),
-              if (!searching) ...[
-                const SizedBox(height: AppSpacing.xs),
-                Text(
-                  AppStrings.customersEmptyCaption,
-                  style: AppTypography.caption,
+      // 비어 있어도 당겨서 새로고침이 되게 스크롤 면에 둔다.
+      return CustomScrollView(
+        physics: const AlwaysScrollableScrollPhysics(),
+        slivers: [
+          SliverFillRemaining(
+            hasScrollBody: false,
+            child: Center(
+              child: Padding(
+                padding: const EdgeInsets.all(AppSpacing.xl),
+                child: Column(
+                  mainAxisSize: MainAxisSize.min,
+                  children: [
+                    Text(
+                      searching
+                          ? AppStrings.customersNoMatch
+                          : AppStrings.customersEmpty,
+                      style: AppTypography.body,
+                    ),
+                    if (!searching) ...[
+                      const SizedBox(height: AppSpacing.xs),
+                      Text(
+                        AppStrings.customersEmptyCaption,
+                        style: AppTypography.caption,
+                      ),
+                    ],
+                  ],
                 ),
-              ],
-            ],
+              ),
+            ),
           ),
-        ),
+        ],
       );
     }
     // 아래 여백은 떠 있는 탭바와 + 버튼 몫이다.
     return ListView.builder(
       controller: scroll,
+      physics: const AlwaysScrollableScrollPhysics(),
       padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
       itemCount: state.items.length + 1,
       itemBuilder: (context, index) {
@@ -248,7 +261,7 @@ class _CardList extends StatelessWidget {
             return Padding(
               padding: const EdgeInsets.all(AppSpacing.lg),
               child: AppErrorRetry.row(
-                message: messageFor(state.loadMoreError!),
+                message: loadMessageFor(state.loadMoreError!),
                 onRetry: onRetryMore,
               ),
             );
```

`app/lib/features/visit/screens/day_screen.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/proxy/media_images.dart';
 import '../../../core/router/screen_keys.dart';
@@ -16,7 +17,6 @@ import '../../../design/widgets/app_big_date.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_fab.dart';
 import '../../../design/widgets/app_icon_toggle.dart';
 import '../../../design/widgets/app_photo_tile.dart';
@@ -255,14 +255,11 @@ class _DayScreenState extends ConsumerState<DayScreen> {
                 ),
               ),
               Expanded(
-                child: day.when(
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () => ref.invalidate(dayVisitsProvider(key)),
-                  ),
-                  data: (data) {
+                child: AsyncBody<DayVisits>(
+                  value: day,
+                  onRetry: () => ref.invalidate(dayVisitsProvider(key)),
+                  onRefresh: () => ref.refresh(dayVisitsProvider(key).future),
+                  builder: (data) {
                     final groups = groupDay(data.items);
                     if (groups.isEmpty) return const _Empty();
                     return mode == DayViewMode.list
@@ -292,15 +289,24 @@ class _Empty extends StatelessWidget {
 
   @override
   Widget build(BuildContext context) {
-    return const Center(
-      child: Column(
-        mainAxisSize: MainAxisSize.min,
-        children: [
-          Text(AppStrings.dayEmpty, style: AppTypography.body),
-          SizedBox(height: AppSpacing.xs),
-          Text(AppStrings.dayEmptyCaption, style: AppTypography.caption),
-        ],
-      ),
+    // 비어 있어도 당겨서 새로고침이 되게 스크롤 면에 둔다.
+    return const CustomScrollView(
+      physics: AlwaysScrollableScrollPhysics(),
+      slivers: [
+        SliverFillRemaining(
+          hasScrollBody: false,
+          child: Center(
+            child: Column(
+              mainAxisSize: MainAxisSize.min,
+              children: [
+                Text(AppStrings.dayEmpty, style: AppTypography.body),
+                SizedBox(height: AppSpacing.xs),
+                Text(AppStrings.dayEmptyCaption, style: AppTypography.caption),
+              ],
+            ),
+          ),
+        ),
+      ],
     );
   }
 }
@@ -326,6 +332,7 @@ class _DayList extends StatelessWidget {
     final gaps = gapsBefore(groups);
     // 아래 여백은 떠 있는 + 버튼 몫이다.
     return ListView(
+      physics: const AlwaysScrollableScrollPhysics(),
       padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
       children: [
         for (var i = 0; i < groups.length; i++) ...[
@@ -518,6 +525,7 @@ class _Timeline extends ConsumerWidget {
         ((t.hour - firstHour) * 60 + t.minute) / 60 * _hourHeight;
 
     return ListView(
+      physics: const AlwaysScrollableScrollPhysics(),
       padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
       children: [
         LayoutBuilder(
```

`app/lib/features/visit/screens/calendar_tab.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/proxy/media_images.dart';
 import '../../../design/tokens/app_colors.dart';
@@ -11,7 +12,6 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_big_date.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_dashed_tile.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_glass_card.dart';
 import '../../../design/widgets/app_icon_toggle.dart';
 import '../../../design/widgets/app_photo_fan.dart';
@@ -94,6 +94,14 @@ class _CalendarTabState extends ConsumerState<CalendarTab> {
     final monthKey = monthKeyOf(shopId, _month);
     final summary = ref.watch(calendarMonthProvider(monthKey));
     final data = summary.value;
+    Widget grid(CalendarMonth? month) => _MonthGrid(
+      month: _month,
+      summary: month,
+      images: ref.watch(mediaImagesProvider),
+      today: ref.watch(todayProvider),
+      selected: selected,
+      onSelect: (date) => ref.read(selectedDateProvider.notifier).select(date),
+    );
 
     return Stack(
       children: [
@@ -142,21 +150,12 @@ class _CalendarTabState extends ConsumerState<CalendarTab> {
             const SizedBox(height: AppSpacing.md),
             const _WeekHeader(),
             const SizedBox(height: AppSpacing.xs),
-            if (summary.hasError && data == null)
-              AppErrorRetry.inline(
-                message: messageFor(summary.error!),
-                onRetry: () => ref.invalidate(calendarMonthProvider(monthKey)),
-              )
-            else
-              _MonthGrid(
-                month: _month,
-                summary: data,
-                images: ref.watch(mediaImagesProvider),
-                today: ref.watch(todayProvider),
-                selected: selected,
-                onSelect: (date) =>
-                    ref.read(selectedDateProvider.notifier).select(date),
-              ),
+            AsyncBody<CalendarMonth>.inline(
+              value: summary,
+              onRetry: () => ref.invalidate(calendarMonthProvider(monthKey)),
+              placeholder: grid(null),
+              builder: grid,
+            ),
           ],
         ),
         // 오른쪽은 떠 있는 + 버튼 자리다.
@@ -536,7 +535,7 @@ class _DayPreview extends ConsumerWidget {
                   ),
                 ),
               if (day.hasError)
-                Text(messageFor(day.error!), style: AppTypography.caption)
+                Text(loadMessageFor(day.error!), style: AppTypography.caption)
               else if (data != null && groups.isEmpty)
                 Text(
                   data.closedDay
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

같은 명령 → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 686 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `FeedController`의 `if (kindOf(e) == ErrorKind.offline) {`를 `if (true) {`로 → `feed_controller_test.dart::다음 쪽이 인터넷 없음으로 실패했으면 인터넷이 돌아올 때 한 번 다시 부른다 — 서버 오류면 부르지 않는다` 실패.
- `CustomerListController`의 복귀 콜백에서 `loadMore();`를 지우면 → `customer_list_controller_test.dart::다음 페이지가 인터넷 없음으로 실패했으면…` 실패.
- 하루 화면의 `onRefresh:` 줄을 지우면 → `day_screen_test.dart::당겨서 새로고침하면 다시 읽고…` 실패.
- 피드의 `onRefresh:` 줄을 지우면 → `calendar_tab_test.dart::피드 당겨서 새로고침하면 첫 쪽부터 다시 읽는다` 실패.
- 고객 목록의 `value: shown != null && !async.hasValue ? AsyncData(shown) : async`를 `shown != null ? AsyncData(shown) : async`로 → `customer_list_tab_test.dart::당겨서 새로고침이 실패하면 목록은 두고 위에 띠…` 실패.
- 피드 다음 쪽 줄의 `message: loadMessageFor(…)`를 `''`로 → `calendar_tab_test.dart::피드 다음 쪽이 실패하면 목록 끝에 원인 문구와 [다시 시도]…` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 목록 화면을 AsyncBody 로 — 피드·고객 목록·하루 목록 당겨서 새로고침과 띠, 달력은 빈 칸을 먼저, 다음 쪽 인터넷 없음은 복귀 때 다시

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: 상세 화면을 `AsyncBody`로 — 방문·반려동물 상세 당겨서 새로고침(보호자·[기록] 탭도 함께), 지워진 방문은 [돌아가기], 보호자 탭 오류는 탭 안에서

**Files:**
- Modify: `app/lib/core/plugs/pet_records_plug.dart`
- Modify: `app/lib/features/visit/state/feed_controller.dart`
- Modify: `app/lib/app.dart`
- Modify: `app/lib/features/visit/screens/visit_detail_screen.dart`
- Modify: `app/lib/features/customer/screens/pet_detail_screen.dart`
- Modify: `app/test/features/customer/screens/pet_detail_screen_test.dart`
- Modify: `app/test/features/visit/screens/pet_records_view_test.dart`
- Modify: `app/test/features/visit/screens/visit_detail_screen_test.dart`

**Interfaces:**
- Consumes: 작업 4·5. `core/plugs/pet_records_plug.dart`의 `petRecordsPlugProvider`, `app.dart`의 `buildRoot`.
- Produces: `core/plugs/pet_records_plug.dart` — `typedef PetRecordsRefresher = void Function(int petId)`, `petRecordsRefreshPlugProvider`(기본은 아무것도 안 함). `features/visit/state/feed_controller.dart` — `PetRecordsRefresher petRecordsRefresher(Ref ref)`(피드를 무효화), `buildRoot`가 `petRecordsRefreshPlugProvider.overrideWith(petRecordsRefresher)`로 꽂는다.

설계 3절의 상세 둘(고객 상세는 따로 된 화면이 없고 가족 카드다). 반려동물 상세를 당기면 상세·보호자(`customerDetailProvider`)·[기록] 탭을 함께 다시 읽는다 — [기록] 탭은 visit 것이고 customer 는 visit 를 import 하지 않으므로 `core/plugs`에 자리를 하나 더 둔다(④-2b 의 [기록] 탭과 같은 방식). 404 방문은 이제 [다시 시도] 대신 [돌아가기]라 옛 테스트 `불러오지 못하면 다시 시도할 수 있고 뒤로 갈 수 있다`를 503·404 둘로 나눈다. `pet_records_view_test.dart`는 `useTallView(2400)`이라 `RefreshIndicator`가 걸리려면 화면 높이 4분의 1 넘게(800) 당긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/customer/screens/pet_detail_screen_test.dart`:

```diff
@@ -493,4 +493,64 @@ void main() {
     await tester.pumpAndSettle();
     expect(find.text('기록 자리 11'), findsOneWidget);
   });
+
+  testWidgets('당겨서 새로고침하면 상세와 보호자를 다시 읽고 [기록] 탭도 다시 읽게 한다', (tester) async {
+    final refreshed = <int>[];
+    final setup = CustomerTestSetup((options, body) {
+      switch ('${options.method} ${options.path}') {
+        case 'GET /v1/shops/3/pets/11':
+          return FakeResponse(statusCode: 200, data: petDetailJson());
+        case 'GET /v1/shops/3/customers/7':
+          return FakeResponse(statusCode: 200, data: customerDetailJson());
+      }
+      fail('예상하지 못한 요청: ${options.method} ${options.path}');
+    }, overrides: [
+      petRecordsRefreshPlugProvider.overrideWithValue(refreshed.add),
+    ]);
+    addTearDown(setup.container.dispose);
+    await _openPet(tester, setup, 11);
+    await tester.tap(find.text(AppStrings.petTabOwner));
+    await tester.pumpAndSettle();
+
+    await tester.fling(find.text('콩이'), const Offset(0, 400), 1000);
+    await tester.pumpAndSettle();
+
+    expect(
+      setup.calls.where((c) => c == 'GET /v1/shops/3/pets/11'),
+      hasLength(2),
+    );
+    expect(
+      setup.calls.where((c) => c == 'GET /v1/shops/3/customers/7'),
+      hasLength(2),
+    );
+    expect(refreshed, [11]);
+  });
+
+  testWidgets('보호자 탭을 불러오지 못하면 탭 안에서 원인 문구와 [다시 시도]', (tester) async {
+    var failOwner = true;
+    final setup = CustomerTestSetup((options, body) {
+      switch ('${options.method} ${options.path}') {
+        case 'GET /v1/shops/3/pets/11':
+          return FakeResponse(statusCode: 200, data: petDetailJson());
+        case 'GET /v1/shops/3/customers/7':
+          return failOwner
+              ? const FakeResponse(statusCode: 503, data: 'x')
+              : FakeResponse(statusCode: 200, data: customerDetailJson());
+      }
+      fail('예상하지 못한 요청: ${options.method} ${options.path}');
+    });
+    addTearDown(setup.container.dispose);
+    await _openPet(tester, setup, 11);
+    await tester.tap(find.text(AppStrings.petTabOwner));
+    await tester.pumpAndSettle();
+    expect(
+      find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
+      findsOneWidget,
+    );
+
+    failOwner = false;
+    await tester.tap(_button(AppStrings.retry));
+    await tester.pumpAndSettle();
+    expect(find.text('010-1234-5678'), findsOneWidget);
+  });
 }
```

`app/test/features/visit/screens/pet_records_view_test.dart`:

```diff
@@ -3,6 +3,7 @@ import 'package:chagocnote/core/proxy/media_images.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/features/visit/screens/feed_view.dart';
+import 'package:chagocnote/features/visit/state/feed_controller.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter_test/flutter_test.dart';
 
@@ -58,6 +59,7 @@ Future<CustomerTestSetup> _open(
       petRecordsPlugProvider.overrideWithValue(
         (petId) => PetRecordsView(petId: petId),
       ),
+      petRecordsRefreshPlugProvider.overrideWith(petRecordsRefresher),
     ],
   );
   addTearDown(setup.container.dispose);
@@ -104,4 +106,24 @@ void main() {
 
     expect(find.text(AppStrings.petRecordsEmpty), findsOneWidget);
   });
+
+  testWidgets('반려동물 상세를 당겨서 새로고침하면 [기록] 탭도 첫 쪽부터 다시 읽는다', (tester) async {
+    final setup = await _open(tester, _backend());
+
+    // 화면이 길어(2400) 새로고침이 걸리려면 화면 높이의 4분의 1보다 더 당겨야 한다.
+    await tester.fling(
+      find.text('10월 2일 금 · 전체 미용'),
+      const Offset(0, 800),
+      1000,
+    );
+    await settle(tester);
+
+    expect(
+      [
+        for (final r in setup.adapter.requests)
+          if (r.path == '/v1/shops/3/visits/feed') r.queryParameters['cursor'],
+      ],
+      [null, null],
+    );
+  });
 }
```

`app/test/features/visit/screens/visit_detail_screen_test.dart`:

```diff
@@ -488,20 +488,16 @@ void main() {
     );
   });
 
-  testWidgets('불러오지 못하면 다시 시도할 수 있고 뒤로 갈 수 있다', (tester) async {
+  testWidgets('서버 오류로 불러오지 못하면 다시 시도할 수 있고 뒤로 갈 수 있다', (tester) async {
     var fail = true;
     final server = _Server();
     final ok = server.backend.routes['GET /v1/shops/3/visits/101']!;
-    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) => fail
-        ? const FakeResponse(
-            statusCode: 404,
-            data: {'code': 'VISIT_NOT_FOUND', 'message': 'x'},
-          )
-        : ok(o, b);
+    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) =>
+        fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
     final setup = CustomerTestSetup(server.backend.call, overrides: _today);
     addTearDown(setup.container.dispose);
     await _open(tester, setup);
-    expect(find.textContaining('방문을 찾을 수 없어요'), findsOneWidget);
+    expect(find.textContaining('서버에 잠시 문제가 있어요'), findsOneWidget);
     expect(find.bySemanticsLabel(AppStrings.back), findsOneWidget);
 
     fail = false;
@@ -510,6 +506,49 @@ void main() {
     expect(find.text('두부'), findsOneWidget);
   });
 
+  testWidgets('지워진 방문(404)이면 [다시 시도] 대신 [돌아가기]로 앞 화면에 돌아간다', (tester) async {
+    final server = _Server();
+    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) =>
+        const FakeResponse(
+          statusCode: 404,
+          data: {'code': 'VISIT_NOT_FOUND', 'message': 'x'},
+        );
+    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _open(tester, setup);
+    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
+    expect(_button(AppStrings.retry), findsNothing);
+
+    await _tap(tester, _button(AppStrings.goBack));
+
+    expect(find.byKey(ScreenKeys.visitDetail), findsNothing);
+  });
+
+  testWidgets('당겨서 새로고침하면 다시 읽고, 실패하면 내용은 두고 위에 띠를 보인다', (tester) async {
+    var fail = false;
+    var reads = 0;
+    final server = _Server();
+    final ok = server.backend.routes['GET /v1/shops/3/visits/101']!;
+    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) {
+      reads++;
+      return fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
+    };
+    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _open(tester, setup);
+
+    fail = true;
+    await tester.fling(find.text('두부'), const Offset(0, 400), 1000);
+    await tester.pumpAndSettle();
+
+    expect(reads, 2);
+    expect(find.text('두부'), findsOneWidget);
+    expect(
+      find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
+      findsOneWidget,
+    );
+  });
+
   testWidgets('방문 상세 골든', (tester) async {
     final server = _Server(withBori: true);
     final setup = CustomerTestSetup(server.backend.call, overrides: _today);
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/features/visit/screens/visit_detail_screen_test.dart test/features/customer/screens/pet_detail_screen_test.dart test/features/visit/screens/pet_records_view_test.dart`
Expected: 실패 — `petRecordsRefreshPlugProvider`·`petRecordsRefresher`가 없어 컴파일 실패.

- [ ] **Step 3: 구현한다**

`app/lib/core/plugs/pet_records_plug.dart`:

```diff
@@ -8,3 +8,11 @@ typedef PetRecordsBuilder = Widget Function(int petId);
 final petRecordsPlugProvider = Provider<PetRecordsBuilder>(
   (ref) => throw UnimplementedError('app.dart 의 buildRoot 가 채운다'),
 );
+
+/// [기록] 탭을 다시 읽게 하는 자리 — 반려동물 상세를 당겨서 새로고침할 때 부른다(오류 화면 다듬기 설계
+/// 3절). `buildRoot`가 visit 의 피드를 무효화하도록 채운다. 채우지 않으면(테스트) 아무것도 하지 않는다.
+typedef PetRecordsRefresher = void Function(int petId);
+
+final petRecordsRefreshPlugProvider = Provider<PetRecordsRefresher>(
+  (ref) => (_) {},
+);
```

`app/lib/features/visit/state/feed_controller.dart`:

```diff
@@ -3,6 +3,7 @@ import 'dart:async';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../../core/error/error_kind.dart';
+import '../../../core/plugs/pet_records_plug.dart';
 import '../../../core/proxy/network_watcher.dart';
 import '../../auth/state/shop_scoped.dart';
 import '../api/feed_models.dart';
@@ -115,3 +116,8 @@ class FeedController extends AsyncNotifier<FeedState> {
 
 final feedControllerProvider = AsyncNotifierProvider.autoDispose
     .family<FeedController, FeedState, FeedQuery>(FeedController.new);
+
+/// 반려동물 상세를 당겨서 새로고침하면 [기록] 탭(그 아이의 피드)도 다시 읽는다 — `app.dart`가
+/// `petRecordsRefreshPlugProvider`에 꽂는다.
+PetRecordsRefresher petRecordsRefresher(Ref ref) =>
+    (_) => ref.invalidate(feedControllerProvider);
```

`app/lib/app.dart`:

```diff
@@ -11,6 +11,7 @@ import 'design/bridge/glass_setup.dart';
 import 'features/auth/state/session.dart';
 import 'features/auth/state/session_controller.dart';
 import 'features/visit/screens/feed_view.dart';
+import 'features/visit/state/feed_controller.dart';
 
 /// 공유로 받은 글 가운데 지금 열 수 있는 것 — 로그인했고 매장을 골랐을 때만.
 /// 콜드 스타트에서 로그인 뒤에, 또는 앱이 떠 있을 때 바로 열린다(③-A3).
@@ -99,6 +100,7 @@ Widget buildRoot({List<Override> overrides = const []}) {
       petRecordsPlugProvider.overrideWithValue(
         (petId) => PetRecordsView(petId: petId),
       ),
+      petRecordsRefreshPlugProvider.overrideWith(petRecordsRefresher),
       ...overrides,
     ],
     child: wrapWithGlass(const App()),
```

`app/lib/features/visit/screens/visit_detail_screen.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/proxy/media_images.dart';
 import '../../../core/router/screen_keys.dart';
@@ -12,7 +13,6 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_photo_pager.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/app_sheet_action.dart';
@@ -258,14 +258,11 @@ class _VisitDetailScreenState extends ConsumerState<VisitDetailScreen> {
                 ),
               ),
               Expanded(
-                child: detail.when(
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () => ref.invalidate(visitDetailProvider(key)),
-                  ),
-                  data: (detail) => _Body(
+                child: AsyncBody<VisitDetail>(
+                  value: detail,
+                  onRetry: () => ref.invalidate(visitDetailProvider(key)),
+                  onRefresh: () => ref.refresh(visitDetailProvider(key).future),
+                  builder: (detail) => _Body(
                     detail: detail,
                     busy: _busy,
                     errorText: _errorText,
@@ -311,6 +308,7 @@ class _Body extends ConsumerWidget {
     final others = detail.group;
     final previous = detail.previousVisit;
     return ListView(
+      physics: const AlwaysScrollableScrollPhysics(),
       padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg),
       children: [
         AppPhotoPager(
```

`app/lib/features/customer/screens/pet_detail_screen.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/plugs/pet_records_plug.dart';
 import '../../../core/proxy/media_images.dart';
@@ -15,7 +16,6 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_segment.dart';
 import '../../../design/widgets/app_sheet.dart';
@@ -214,20 +214,27 @@ class _PetDetailScreenState extends ConsumerState<PetDetailScreen> {
                   child: Text(_errorText!, style: AppTypography.caption),
                 ),
               Expanded(
-                child: detail.when(
-                  data: (detail) => _DetailBody(
+                child: AsyncBody<PetDetail>(
+                  value: detail,
+                  onRetry: () => ref.invalidate(
+                    petDetailProvider((shopId: shopId!, petId: widget.petId)),
+                  ),
+                  // 탭 안의 보호자·기록도 함께 다시 읽는다.
+                  onRefresh: () {
+                    ref.invalidate(customerDetailProvider);
+                    ref.read(petRecordsRefreshPlugProvider)(widget.petId);
+                    return ref.refresh(
+                      petDetailProvider((
+                        shopId: shopId!,
+                        petId: widget.petId,
+                      )).future,
+                    );
+                  },
+                  builder: (detail) => _DetailBody(
                     detail: detail,
                     tab: _tab,
                     onTab: (i) => setState(() => _tab = i),
                   ),
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () => ref.invalidate(
-                      petDetailProvider((shopId: shopId!, petId: widget.petId)),
-                    ),
-                  ),
                 ),
               ),
             ],
@@ -254,6 +261,7 @@ class _DetailBody extends ConsumerWidget {
     final pet = detail.pet;
     final photo = pet.photo;
     return ListView(
+      physics: const AlwaysScrollableScrollPhysics(),
       padding: const EdgeInsets.all(AppSpacing.lg),
       children: [
         Center(
@@ -395,10 +403,10 @@ class _OwnerTab extends ConsumerWidget {
     final shopId = ref.watch(selectedShopIdProvider);
     if (shopId == null) return const SizedBox.shrink();
     final key = (shopId: shopId, customerId: customerId);
-    return ref
-        .watch(customerDetailProvider(key))
-        .when(
-          data: (detail) {
+    return AsyncBody<CustomerDetail>.inline(
+      value: ref.watch(customerDetailProvider(key)),
+      onRetry: () => ref.invalidate(customerDetailProvider(key)),
+      builder: (detail) {
             final c = detail.customer;
             final consent = c.marketingConsent
                 ? AppStrings.marketingAgreed
@@ -449,16 +457,8 @@ class _OwnerTab extends ConsumerWidget {
                 ),
               ],
             );
-          },
-          loading: () => const Padding(
-            padding: EdgeInsets.all(AppSpacing.lg),
-            child: Center(child: CircularProgressIndicator()),
-          ),
-          error: (error, _) => AppErrorRetry.inline(
-            message: messageFor(error),
-            onRetry: () => ref.invalidate(customerDetailProvider(key)),
-          ),
-        );
+      },
+    );
   }
 }
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

같은 명령 → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 691 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 반려동물 상세 `onRefresh`의 `ref.read(petRecordsRefreshPlugProvider)(widget.petId);`를 지우면 → `pet_detail_screen_test.dart::당겨서 새로고침하면 상세와 보호자를 다시 읽고 [기록] 탭도 다시 읽게 한다` 실패.
- 같은 곳의 `ref.invalidate(customerDetailProvider);`를 지우면 → 같은 테스트 실패.
- 방문 상세의 `onRefresh:` 줄을 지우면 → `visit_detail_screen_test.dart::당겨서 새로고침하면 다시 읽고, 실패하면 내용은 두고 위에 띠를 보인다` 실패.
- `petRecordsRefresher`를 `(_) {}`로 → `pet_records_view_test.dart::반려동물 상세를 당겨서 새로고침하면 [기록] 탭도 첫 쪽부터 다시 읽는다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 상세 화면을 AsyncBody 로 — 방문·반려동물 상세 당겨서 새로고침(보호자·[기록] 탭도 함께), 지워진 방문은 [돌아가기], 보호자 탭 오류는 탭 안에서

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: 폼·설정 화면을 `AsyncBody`로 — 여럿을 기다리는 폼은 하나로 묶어 넘기고, 기록 화면은 채운 뒤 다시 읽기가 실패해도 폼을 남긴다, 구조 테스트

**Files:**
- Modify: `app/lib/features/customer/screens/customer_edit_screen.dart`
- Modify: `app/lib/features/customer/screens/pet_form_screen.dart`
- Modify: `app/lib/features/customer/screens/register_customer_screen.dart`
- Modify: `app/lib/features/shop/screens/members_screen.dart`
- Modify: `app/lib/features/shop/screens/shop_settings_screen.dart`
- Modify: `app/lib/features/visit/screens/draft_screen.dart`
- Modify: `app/lib/features/visit/screens/photo_viewer_screen.dart`
- Modify: `app/lib/features/visit/screens/record_screen.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Modify: `app/lib/features/visit/screens/settings/menu_settings_screen.dart`
- Modify: `app/lib/features/visit/screens/settings/schedule_settings_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_edit_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_form.dart`
- Create: `app/test/design/async_body_usage_test.dart`
- Modify: `app/test/features/visit/screens/record_screen_test.dart`

**Interfaces:**
- Consumes: 작업 4 `AsyncBody`, 작업 1 `loadMessageFor`.
- Produces: 구조 테스트 `test/design/async_body_usage_test.dart`(기능 화면이 `AppErrorRetry(`·`AppErrorRetry.inline(`을 직접 만들지 않는다 — `row`는 허용). 이 작업 뒤 예외는 스플래시 하나(작업 8 이 지운다).

한 값을 기다리는 화면 열(멤버·매장 정보·카톡 초안·예약 수정·일정 설정·메뉴 설정·보호자 수정·고객 등록 2단계·예약 ① 고객 고르기·사진 크게 보기)은 `.when`을 `AsyncBody`로 바꾼다(당기기 없음 — 폼이다). 여럿을 기다리는 폼 셋(예약 폼·반려동물 폼·기록 화면)은 값들을 `AsyncValue<void>` 하나(`AsyncError` / `AsyncLoading` / `AsyncData(null)`)로 묶어 넘기고 `builder`는 모아 둔 값을 쓴다. **기록 화면은 한 번 채운 뒤(`_started`)에는 다시 읽기가 실패해도 폼을 남긴다** — 예전에는 409 뒤 다시 읽기가 실패하면 쓰던 폼이 오류 화면으로 바뀌었다(쓰던 내용을 지우지 않는다, 설계 3절). 한 줄 자리(휴무일 목록·시간 칸)는 `AppErrorRetry.row`에 `loadMessageFor`만 — 스스로 다시 부르지 않는다(007 남는 것).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/async_body_usage_test.dart`:

```dart
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 오류 화면 다듬기 설계 3.2: 화면을 불러오지 못했을 때의 오류는 `AsyncBody`가 그린다(원인 문구·
/// 다시 시도/돌아가기·받은 데이터 위 띠·인터넷 복귀 때 다시). 기능 화면이 `AppErrorRetry`의 가운데·
/// inline 모양을 직접 만들면 이 규칙을 빠뜨린다. 한 줄 모양(`AppErrorRetry.row` — 다음 쪽 실패, 시간 칸,
/// 휴무일 목록)은 좁은 자리라 화면이 직접 쓴다.
void main() {
  test('기능 화면은 AppErrorRetry 의 가운데·inline 모양을 직접 만들지 않는다', () {
    const allowed = <String>{
      // 세션 복원은 AsyncBody 가 아니라 스플래시가 다룬다(작업 8 에서 옮긴다).
      'lib/features/auth/screens/splash_screen.dart',
    };
    final direct = RegExp(r'AppErrorRetry(\.inline)?\(');
    final violations = [
      for (final entity in Directory('lib/features').listSync(recursive: true))
        if (entity is File &&
            entity.path.endsWith('.dart') &&
            !allowed.contains(entity.path.replaceAll(r'\', '/')) &&
            direct.hasMatch(entity.readAsStringSync()))
          entity.path,
    ];

    expect(violations, isEmpty, reason: 'AsyncBody 를 쓰지 않음: $violations');
  });
}
```

`app/test/features/visit/screens/record_screen_test.dart`:

```diff
@@ -335,6 +335,29 @@ void main() {
     expect(closed.closed, isFalse);
   });
 
+  testWidgets('어긋나 다시 읽는데 그것마저 실패해도 쓰던 폼은 남고 문구만 보인다', (tester) async {
+    final server = _Server(record: recordJson(careNote: '메모', version: 3));
+    server.putResponses.add(
+      const FakeResponse(
+        statusCode: 409,
+        data: {'code': 'RECORD_VERSION_CONFLICT', 'message': 'x'},
+      ),
+    );
+    final ok = server.backend.routes['GET /v1/shops/3/visits/101']!;
+    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) =>
+        server.detailReads > 0
+        ? const FakeResponse(statusCode: 503, data: 'x')
+        : ok(o, b);
+    final (_, closed) = await _open(tester, server);
+    await tester.enterText(find.widgetWithText(TextField, '메모'), '고쳐 쓴 메모');
+
+    await _tap(tester, _button(AppStrings.save));
+
+    expect(find.text('고쳐 쓴 메모'), findsOneWidget, reason: '쓰던 폼이 오류 화면으로 바뀌지 않는다');
+    expect(find.textContaining('서버에 잠시 문제가 있어요'), findsOneWidget);
+    expect(closed.closed, isFalse);
+  });
+
   testWidgets('나중에 적고 완료는 기록을 보내지 않고 완료만 한다', (tester) async {
     final server = _Server();
     final (_, closed) = await _open(tester, server, completing: true);
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/design/async_body_usage_test.dart test/features/visit/screens/record_screen_test.dart`
Expected: 실패 — 구조 테스트가 화면 열셋을 잡고, `어긋나 다시 읽는데 그것마저 실패해도 쓰던 폼은 남고 문구만 보인다`가 오류 화면으로 바뀐 폼을 잡는다.

- [ ] **Step 3: 구현한다**

`app/lib/features/customer/screens/customer_edit_screen.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
@@ -9,7 +10,6 @@ import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -140,8 +140,10 @@ class _CustomerEditScreenState extends ConsumerState<CustomerEditScreen> {
                 ),
               ),
               Expanded(
-                child: detail.when(
-                  data: (detail) => SingleChildScrollView(
+                child: AsyncBody<CustomerDetail>(
+                  value: detail,
+                  onRetry: () => ref.invalidate(customerDetailProvider(key!)),
+                  builder: (detail) => SingleChildScrollView(
                     padding: const EdgeInsets.all(AppSpacing.lg),
                     child: Column(
                       children: [
@@ -162,12 +164,6 @@ class _CustomerEditScreenState extends ConsumerState<CustomerEditScreen> {
                       ],
                     ),
                   ),
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () => ref.invalidate(customerDetailProvider(key!)),
-                  ),
                 ),
               ),
             ],
```

`app/lib/features/customer/screens/pet_form_screen.dart`:

```diff
@@ -2,13 +2,13 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../../../core/time/today_provider.dart';
@@ -77,21 +77,21 @@ class _PetFormScreenState extends ConsumerState<PetFormScreen> {
         ? const AsyncValue<PetDetail?>.loading()
         : ref.watch(petDetailProvider((shopId: shopId, petId: petId)));
 
-    Widget body;
-    if (types.hasError || pet.hasError) {
-      body = AppErrorRetry(
-        message: messageFor(types.error ?? pet.error!),
-        onRetry: () {
-          ref.invalidate(conditionTypesProvider(shopId!));
-          if (petId != null) {
-            ref.invalidate(petDetailProvider((shopId: shopId, petId: petId)));
-          }
-        },
-      );
-    } else if (!types.hasValue || !pet.hasValue) {
-      body = const Center(child: CircularProgressIndicator());
-    } else {
-      body = SingleChildScrollView(
+    // 질병 종류와(수정이면) 반려동물 상세를 하나로 묶어 불러오기 틀에 넘긴다.
+    final error = types.error ?? pet.error;
+    final body = AsyncBody<void>(
+      value: error != null
+          ? AsyncError(error, StackTrace.empty)
+          : !types.hasValue || !pet.hasValue
+          ? const AsyncLoading()
+          : const AsyncData(null),
+      onRetry: () {
+        ref.invalidate(conditionTypesProvider(shopId!));
+        if (petId != null) {
+          ref.invalidate(petDetailProvider((shopId: shopId, petId: petId)));
+        }
+      },
+      builder: (_) => SingleChildScrollView(
         padding: const EdgeInsets.all(AppSpacing.lg),
         child: PetForm(
           initial: pet.value?.pet,
@@ -102,8 +102,8 @@ class _PetFormScreenState extends ConsumerState<PetFormScreen> {
           errorText: _errorText,
           onSubmit: _submit,
         ),
-      );
-    }
+      ),
+    );
 
     return Scaffold(
       key: ScreenKeys.petForm,
```

`app/lib/features/customer/screens/register_customer_screen.dart`:

```diff
@@ -4,6 +4,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
 import '../../../core/error/api_exception.dart';
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
@@ -12,7 +13,6 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../../../core/time/today_provider.dart';
@@ -306,10 +306,10 @@ class _RegisterCustomerScreenState
   Widget _petStep() {
     final shopId = _shopId;
     if (shopId == null) return const SizedBox.shrink();
-    return ref
-        .watch(conditionTypesProvider(shopId))
-        .when(
-          data: (types) => SingleChildScrollView(
+    return AsyncBody<List<ConditionType>>(
+      value: ref.watch(conditionTypesProvider(shopId)),
+      onRetry: () => ref.invalidate(conditionTypesProvider(shopId)),
+      builder: (types) => SingleChildScrollView(
             padding: const EdgeInsets.all(AppSpacing.lg),
             child: PetForm(
               conditionTypes: types,
@@ -319,12 +319,7 @@ class _RegisterCustomerScreenState
               errorText: _step == 2 ? _errorText : null,
               onSubmit: _register,
             ),
-          ),
-          loading: () => const Center(child: CircularProgressIndicator()),
-          error: (error, _) => AppErrorRetry(
-            message: messageFor(error),
-            onRetry: () => ref.invalidate(conditionTypesProvider(shopId)),
-          ),
-        );
+      ),
+    );
   }
 }
```

`app/lib/features/shop/screens/members_screen.dart`:

```diff
@@ -1,6 +1,7 @@
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/proxy/clipboard.dart';
 import '../../../core/router/screen_keys.dart';
@@ -11,7 +12,6 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
@@ -212,8 +212,11 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
                   child: Text(_errorText!, style: AppTypography.caption),
                 ),
               Expanded(
-                child: members.when(
-                  data: (list) => ListView.builder(
+                child: AsyncBody<List<ShopMember>>(
+                  value: members,
+                  onRetry: () =>
+                      ref.invalidate(membersControllerProvider(shopId!)),
+                  builder: (list) => ListView.builder(
                     padding: const EdgeInsets.all(AppSpacing.lg),
                     itemCount: list.length,
                     itemBuilder: (context, index) {
@@ -265,13 +268,6 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
                       );
                     },
                   ),
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () =>
-                        ref.invalidate(membersControllerProvider(shopId!)),
-                  ),
                 ),
               ),
             ],
```

`app/lib/features/shop/screens/shop_settings_screen.dart`:

```diff
@@ -1,6 +1,7 @@
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
@@ -8,7 +9,6 @@ import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../api/shop_api.dart';
@@ -129,8 +129,11 @@ class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
                 ),
               ),
               Expanded(
-                child: settingsAsync.when(
-                  data: (settings) {
+                child: AsyncBody<ShopSettings>(
+                  value: settingsAsync,
+                  onRetry: () =>
+                      ref.invalidate(shopSettingsControllerProvider(shopId!)),
+                  builder: (settings) {
                     _initFields(settings);
                     return SingleChildScrollView(
                       padding: const EdgeInsets.all(AppSpacing.lg),
@@ -183,13 +186,6 @@ class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
                       ),
                     );
                   },
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () =>
-                        ref.invalidate(shopSettingsControllerProvider(shopId!)),
-                  ),
                 ),
               ),
             ],
```

`app/lib/features/visit/screens/draft_screen.dart`:

```diff
@@ -2,7 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
-import '../../../core/error/error_messages.dart';
+import '../../../core/error/async_body.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
@@ -11,7 +11,6 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -109,14 +108,10 @@ class _DraftScreenState extends ConsumerState<DraftScreen> {
                 ),
               ),
               Expanded(
-                child: draft.when(
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () => ref.invalidate(visitDraftProvider(key)),
-                  ),
-                  data: (draft) => _body(shopId!, draft),
+                child: AsyncBody<VisitDraft>(
+                  value: draft,
+                  onRetry: () => ref.invalidate(visitDraftProvider(key)),
+                  builder: (draft) => _body(shopId!, draft),
                 ),
               ),
             ],
```

`app/lib/features/visit/screens/photo_viewer_screen.dart`:

```diff
@@ -3,6 +3,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
 import '../../../core/error/api_exception.dart';
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/proxy/media_images.dart';
 import '../../../core/proxy/photo_album.dart';
@@ -13,7 +14,6 @@ import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/app_snack_bar.dart';
 import '../../../design/widgets/pressable.dart';
@@ -211,21 +211,19 @@ class _PhotoViewerScreenState extends ConsumerState<PhotoViewerScreen> {
                 ),
               ),
               Expanded(
-                child: detail.hasError && data == null
-                    ? AppErrorRetry(
-                        message: messageFor(detail.error!),
-                        onRetry: () =>
-                            ref.invalidate(visitDetailProvider(_key)),
-                      )
-                    : pages == null
-                    ? const Center(child: CircularProgressIndicator())
-                    : PageView.builder(
-                        controller: pages,
-                        itemCount: gallery.length,
-                        onPageChanged: (i) =>
-                            setState(() => _mediaId = gallery[i].mediaId),
-                        itemBuilder: (context, i) => _Page(media: gallery[i]),
-                      ),
+                child: AsyncBody<VisitDetail>(
+                  value: detail,
+                  onRetry: () => ref.invalidate(visitDetailProvider(_key)),
+                  builder: (_) => pages == null
+                      ? const Center(child: CircularProgressIndicator())
+                      : PageView.builder(
+                          controller: pages,
+                          itemCount: gallery.length,
+                          onPageChanged: (i) =>
+                              setState(() => _mediaId = gallery[i].mediaId),
+                          itemBuilder: (context, i) => _Page(media: gallery[i]),
+                        ),
+                ),
               ),
               if (current != null)
                 _Actions(
```

`app/lib/features/visit/screens/record_screen.dart`:

```diff
@@ -4,6 +4,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
 import '../../../core/error/api_exception.dart';
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
@@ -13,7 +14,6 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_choice_chip.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../../customer/state/customer_input.dart';
@@ -311,20 +311,24 @@ class _RecordScreenState extends ConsumerState<RecordScreen> {
                 ),
               ),
               Expanded(
-                child: switch ((detail, menus)) {
-                  (AsyncError(:final error), _) ||
-                  (_, AsyncError(:final error)) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () {
-                      ref.invalidate(visitDetailProvider(key));
-                      ref.invalidate(menusProvider);
-                    },
-                  ),
-                  _ when !_started => const Center(
-                    child: CircularProgressIndicator(),
-                  ),
-                  _ => _form(d!, m!),
-                },
+                // 방문 상세와 메뉴를 하나로 묶어 불러오기 틀에 넘긴다. 폼은 한 번 채운 뒤(_started)
+                // 다시 읽기에 흔들리지 않는다.
+                child: AsyncBody<void>(
+                  value: switch ((detail, menus)) {
+                    (AsyncError(:final error), _) ||
+                    (_, AsyncError(:final error)) when !_started => AsyncError(
+                      error,
+                      StackTrace.empty,
+                    ),
+                    _ when !_started => const AsyncLoading(),
+                    _ => const AsyncData(null),
+                  },
+                  onRetry: () {
+                    ref.invalidate(visitDetailProvider(key));
+                    ref.invalidate(menusProvider);
+                  },
+                  builder: (_) => _form(d!, m!),
+                ),
               ),
             ],
           ),
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -3,6 +3,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
 import '../../../core/error/api_exception.dart';
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/proxy/clipboard.dart';
 import '../../../core/router/screen_keys.dart';
@@ -12,7 +13,6 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_search_field.dart';
 import '../../../design/widgets/app_snack_bar.dart';
 import '../../../design/widgets/pressable.dart';
@@ -364,14 +364,11 @@ class _CustomerSearchState extends ConsumerState<_CustomerSearch> {
         ),
         const SizedBox(height: AppSpacing.sm),
         Expanded(
-          child: list.when(
-            loading: () => const Center(child: CircularProgressIndicator()),
-            error: (error, _) => AppErrorRetry(
-              message: messageFor(error),
-              onRetry: () =>
-                  ref.invalidate(customerListControllerProvider(query)),
-            ),
-            data: (state) => ListView(
+          child: AsyncBody<CustomerListState>(
+            value: list,
+            onRetry: () =>
+                ref.invalidate(customerListControllerProvider(query)),
+            builder: (state) => ListView(
               padding: const EdgeInsets.fromLTRB(
                 AppSpacing.lg,
                 0,
```

`app/lib/features/visit/screens/settings/menu_settings_screen.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../../core/error/async_body.dart';
 import '../../../../core/error/error_messages.dart';
 import '../../../../core/router/screen_keys.dart';
 import '../../../../design/app_theme.dart';
@@ -12,7 +13,6 @@ import '../../../../design/widgets/app_back_button.dart';
 import '../../../../design/widgets/app_button.dart';
 import '../../../../design/widgets/app_card.dart';
 import '../../../../design/widgets/app_choice_chip.dart';
-import '../../../../design/widgets/app_error_retry.dart';
 import '../../../../design/widgets/app_sheet.dart';
 import '../../../../design/widgets/pressable.dart';
 import '../../../../l10n/app_strings.dart';
@@ -217,14 +217,10 @@ class _MenuSettingsScreenState extends ConsumerState<MenuSettingsScreen> {
                   child: Text(_errorText!, style: AppTypography.caption),
                 ),
               Expanded(
-                child: menus.when(
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () => ref.invalidate(menusProvider(key)),
-                  ),
-                  data: (items) {
+                child: AsyncBody<List<Menu>>(
+                  value: menus,
+                  onRetry: () => ref.invalidate(menusProvider(key)),
+                  builder: (items) {
                     final sorted = [...items]
                       ..sort((a, b) => a.sortOrder.compareTo(b.sortOrder));
                     if (sorted.isEmpty) {
```

`app/lib/features/visit/screens/settings/schedule_settings_screen.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../../core/error/async_body.dart';
 import '../../../../core/error/error_messages.dart';
 import '../../../../core/router/screen_keys.dart';
 import '../../../../design/app_theme.dart';
@@ -212,15 +213,11 @@ class _ScheduleSettingsScreenState
                 ),
               ),
               Expanded(
-                child: settings.when(
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () =>
-                        ref.invalidate(visitSettingsProvider(shopId!)),
-                  ),
-                  data: (data) {
+                child: AsyncBody<VisitSettings>(
+                  value: settings,
+                  onRetry: () =>
+                      ref.invalidate(visitSettingsProvider(shopId!)),
+                  builder: (data) {
                     _init(data);
                     return _body(shopId!);
                   },
@@ -343,7 +340,7 @@ class _ScheduleSettingsScreenState
               closedDates.when(
                 loading: () => const Center(child: CircularProgressIndicator()),
                 error: (error, _) => AppErrorRetry.row(
-                  message: messageFor(error),
+                  message: loadMessageFor(error),
                   onRetry: () => ref.invalidate(closedDatesProvider),
                 ),
                 data: (items) => items.isEmpty
```

`app/lib/features/visit/screens/visit_edit_screen.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
@@ -10,7 +11,6 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -154,14 +154,10 @@ class _VisitEditScreenState extends ConsumerState<VisitEditScreen> {
                 ),
               ),
               Expanded(
-                child: detail.when(
-                  loading: () =>
-                      const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => AppErrorRetry(
-                    message: messageFor(error),
-                    onRetry: () => ref.invalidate(visitDetailProvider(key)),
-                  ),
-                  data: (detail) => _form(shopId!, detail),
+                child: AsyncBody<VisitDetail>(
+                  value: detail,
+                  onRetry: () => ref.invalidate(visitDetailProvider(key)),
+                  builder: (detail) => _form(shopId!, detail),
                 ),
               ),
             ],
```

`app/lib/features/visit/screens/visit_form.dart`:

```diff
@@ -2,6 +2,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../design/tokens/app_colors.dart';
 import '../../../design/tokens/app_radius.dart';
@@ -182,28 +183,30 @@ class _VisitFormState extends ConsumerState<VisitForm> {
       menusProvider((shopId: widget.shopId, includeArchived: false)),
     );
     final error = settings.error ?? customer.error ?? menus.error;
-    if (error != null) {
-      return AppErrorRetry(
-        message: messageFor(error),
-        onRetry: () {
-          ref.invalidate(visitSettingsProvider(widget.shopId));
-          ref.invalidate(customerDetailProvider);
-          ref.invalidate(menusProvider);
-        },
-      );
-    }
     final s = settings.value;
     final pets = customer.pets;
     final m = menus.value;
-    if (s == null || pets == null || m == null) {
-      return const Center(child: CircularProgressIndicator());
-    }
-    final living = [
-      for (final p in pets)
-        if (!p.passedAway || widget.initial.petIds.contains(p.petId)) p,
-    ];
-    _initPets(living);
-    return _buildForm(s, living, m);
+    // 셋을 하나로 묶어 불러오기 틀에 넘긴다 — 하나라도 실패면 오류, 셋 다 오면 폼.
+    return AsyncBody<void>(
+      value: error != null
+          ? AsyncError(error, StackTrace.empty)
+          : s == null || pets == null || m == null
+          ? const AsyncLoading()
+          : const AsyncData(null),
+      onRetry: () {
+        ref.invalidate(visitSettingsProvider(widget.shopId));
+        ref.invalidate(customerDetailProvider);
+        ref.invalidate(menusProvider);
+      },
+      builder: (_) {
+        final living = [
+          for (final p in pets!)
+            if (!p.passedAway || widget.initial.petIds.contains(p.petId)) p,
+        ];
+        _initPets(living);
+        return _buildForm(s!, living, m!);
+      },
+    );
   }
 
   Widget _buildForm(VisitSettings settings, List<Pet> pets, List<Menu> menus) {
@@ -563,7 +566,7 @@ class _SlotGrid extends ConsumerWidget {
         child: Center(child: CircularProgressIndicator()),
       ),
       error: (error, _) => AppErrorRetry.row(
-        message: messageFor(error),
+        message: loadMessageFor(error),
         onRetry: () => ref.invalidate(visitSlotsProvider(slotsKey)),
       ),
       data: (data) => Wrap(
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

같은 명령 → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 693 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `draft_screen.dart`에서 `child: AsyncBody<VisitDraft>(`를 `child: AppErrorRetry(message: '', onRetry: () {}), foo: AsyncBody<VisitDraft>(`로(구조 테스트만 볼 것) → `async_body_usage_test.dart` 실패.
- `record_screen.dart`의 `(_, AsyncError(:final error)) when !_started => AsyncError(`에서 `when !_started`를 빼면 → `record_screen_test.dart::어긋나 다시 읽는데 그것마저 실패해도 쓰던 폼은 남고 문구만 보인다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 폼·설정 화면을 AsyncBody 로 — 여럿을 기다리는 폼은 하나로 묶어 넘기고, 기록 화면은 채운 뒤 다시 읽기가 실패해도 폼을 남긴다, 구조 테스트

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: 스플래시 오류를 `AsyncBody`로 — 원인 문구, 인터넷 없이 켜면 돌아올 때 스스로 다시 복원

**Files:**
- Modify: `app/lib/features/auth/screens/splash_screen.dart`
- Modify: `app/test/design/async_body_usage_test.dart`
- Modify: `app/test/features/auth/screens/splash_screen_test.dart`

**Interfaces:**
- Consumes: 작업 4 `AsyncBody.inline(placeholder:)`, `sessionControllerProvider`.
- Produces: 스플래시가 `AsyncBody.inline`을 쓴다(로딩은 앱 이름 + 로딩, 값이면 로딩 — 라우터가 곧 옮긴다). 구조 테스트의 예외 목록이 없어진다.

설계 5절. 오프라인으로 앱에 들어가지 않는다(서버 데이터를 기기에 두지 않는다). 인터넷 없음 문구는 화면 불러오기와 같은 "연결되면 다시 불러올게요"다 — 설계의 "다시 시도할게요"와 한 단어 다르지만 문구를 하나로 둔다(007).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/async_body_usage_test.dart`:

```diff
@@ -8,16 +8,11 @@ import 'package:flutter_test/flutter_test.dart';
 /// 휴무일 목록)은 좁은 자리라 화면이 직접 쓴다.
 void main() {
   test('기능 화면은 AppErrorRetry 의 가운데·inline 모양을 직접 만들지 않는다', () {
-    const allowed = <String>{
-      // 세션 복원은 AsyncBody 가 아니라 스플래시가 다룬다(작업 8 에서 옮긴다).
-      'lib/features/auth/screens/splash_screen.dart',
-    };
     final direct = RegExp(r'AppErrorRetry(\.inline)?\(');
     final violations = [
       for (final entity in Directory('lib/features').listSync(recursive: true))
         if (entity is File &&
             entity.path.endsWith('.dart') &&
-            !allowed.contains(entity.path.replaceAll(r'\', '/')) &&
             direct.hasMatch(entity.readAsStringSync()))
           entity.path,
     ];
```

`app/test/features/auth/screens/splash_screen_test.dart`:

```diff
@@ -1,3 +1,6 @@
+import 'package:chagocnote/core/error/api_exception.dart';
+import 'package:chagocnote/core/error/error_messages.dart';
+import 'package:chagocnote/core/proxy/network_watcher.dart';
 import 'package:chagocnote/design/app_theme.dart';
 import 'package:chagocnote/design/bridge/glass_surface.dart';
 import 'package:chagocnote/features/auth/screens/splash_screen.dart';
@@ -7,6 +10,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
 
 import '../../../support/fake_session_gateway.dart';
+import '../../../support/upload_fakes.dart';
 
 Widget _appWith(ProviderContainer container) {
   return UncontrolledProviderScope(
@@ -45,4 +49,30 @@ void main() {
 
     expect(gateway.restoreCallCount, 2);
   });
+
+  testWidgets('인터넷 없이 켜면 인터넷 문구를 보이고, 인터넷이 돌아오면 스스로 다시 복원한다', (tester) async {
+    final gateway = FakeSessionGateway()
+      ..restoreError = ApiException.network('연결 실패');
+    final network = FakeNetworkWatcher();
+    final container = ProviderContainer.test(
+      retry: (retryCount, error) => null,
+      overrides: [
+        sessionGatewayProvider.overrideWithValue(gateway),
+        networkWatcherProvider.overrideWithValue(network),
+      ],
+    );
+    addTearDown(container.dispose);
+
+    await tester.pumpWidget(_appWith(container));
+    await tester.pumpAndSettle();
+    expect(find.text(offlineLoadMessage), findsOneWidget);
+    expect(find.text('다시 시도'), findsOneWidget);
+
+    gateway.restoreError = null;
+    network.restore();
+    await tester.pump();
+    await tester.pump(const Duration(milliseconds: 100));
+
+    expect(gateway.restoreCallCount, 2);
+  });
 }
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/features/auth/screens/splash_screen_test.dart`
Expected: 새 테스트 실패 — 인터넷 없음 문구가 누른 일 문구이고, 복귀 신호에 다시 복원하지 않는다.

- [ ] **Step 3: 구현한다**

`app/lib/features/auth/screens/splash_screen.dart`:

```diff
@@ -1,17 +1,16 @@
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../../core/error/error_messages.dart';
+import '../../../core/error/async_body.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
-import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../state/session_controller.dart';
 
-/// 세션 복원 동안 보여주는 스플래시. 복원이 실패하면 오류 문구와 재시도
-/// 버튼을 보여준다.
+/// 세션 복원 동안 보여주는 스플래시. 복원이 실패하면 원인 문구와 재시도 버튼을 보여주고,
+/// 인터넷 없음이면 인터넷이 돌아올 때 스스로 다시 복원한다(오류 화면 다듬기 설계 5절).
 class SplashScreen extends ConsumerWidget {
   const SplashScreen({super.key});
 
@@ -23,9 +22,10 @@ class SplashScreen extends ConsumerWidget {
       key: ScreenKeys.splash,
       body: AppBackground(
         child: Center(
-          child: session.when(
-            data: (_) => const CircularProgressIndicator(),
-            loading: () => Column(
+          child: AsyncBody.inline(
+            value: session,
+            onRetry: () => ref.invalidate(sessionControllerProvider),
+            placeholder: Column(
               mainAxisSize: MainAxisSize.min,
               children: [
                 Text(AppStrings.appName, style: AppTypography.titleKo),
@@ -33,10 +33,7 @@ class SplashScreen extends ConsumerWidget {
                 const CircularProgressIndicator(),
               ],
             ),
-            error: (error, _) => AppErrorRetry.inline(
-              message: messageFor(error),
-              onRetry: () => ref.invalidate(sessionControllerProvider),
-            ),
+            builder: (_) => const CircularProgressIndicator(),
           ),
         ),
       ),
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/features/auth/screens/splash_screen_test.dart test/design/async_body_usage_test.dart` → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 694 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `async_body.dart`의 복귀 콜백에서 `widget.onRetry();`를 지우면 → `splash_screen_test.dart::인터넷 없이 켜면 인터넷 문구를 보이고, 인터넷이 돌아오면 스스로 다시 복원한다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 스플래시 오류를 AsyncBody 로 — 원인 문구, 인터넷 없이 켜면 돌아올 때 스스로 다시 복원

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: 대기열 멈춤 — 다시 해도 안 되는 실패는 스스로 다시 하지 않고 이유를 기기에 남긴다, 느낌표 타일과 [다시 시도]·[올리기 취소] 시트

**Files:**
- Modify: `app/lib/features/visit/state/upload_job.dart`
- Modify: `app/lib/features/visit/state/upload_queue.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/lib/features/visit/screens/record_photos.dart`
- Modify: `app/test/support/upload_fakes.dart`
- Modify: `app/test/features/visit/screens/record_screen_test.dart`
- Modify: `app/test/features/visit/state/upload_queue_test.dart`

**Interfaces:**
- Consumes: 작업 1 `kindOf`·`messageFor`, 작업 2 `AppStrings.removeUpload`, ④-2a 의 `UploadQueue`·`UploadJob`·`visitUploadsProvider`·`RecordPhotoStrip`.
- Produces: `UploadJob.stoppedCode: String?`(JSON `stopped_code`, 옛 항목엔 없어 null)·`bool get stopped`, `waiting`은 멈춘 항목이 아니다. `upload_queue.dart` — `bool stopsUpload(Object error)`(denied·gone·그 밖 4xx 는 true, 401·429·인터넷·서버는 false), `UploadQueue.retry(String id)`. `AppStrings.uploadStopped = '올리지 못한 사진'`. `FakeUploadQueue.retried`(테스트 대역).

설계 4절(A′ — 사용자가 고름). `MEDIA_NOT_FOUND`는 먼저 걸러 예전처럼 재발급 쪽이다. 멈춘 항목은 `_pump`가 건너뛰고 앱을 다시 켜도·인터넷이 돌아와도 스스로 시작하지 않는다. 파일은 [올리기 취소]까지 남는다. 멈춘 항목도 30장 한도에 센다(`visitUploadsProvider`에 그대로 든다). 멈춘 타일은 진행 링 대신 느낌표, 누르면 시트(이유 = `messageFor(ApiException(code: stoppedCode))`, [다시 시도]·[올리기 취소]). X 는 그대로다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/support/upload_fakes.dart`:

```diff
@@ -121,10 +121,14 @@ class FakeUploadQueue extends UploadQueue {
   final List<UploadJob> initial;
   final added = <({int visitId, MediaPhase phase, List<String> sources})>[];
   final removed = <String>[];
+  final retried = <String>[];
 
   @override
   Future<List<UploadJob>> build() async => initial;
 
+  @override
+  Future<void> retry(String id) async => retried.add(id);
+
   @override
   Future<void> addPhotos({
     required int shopId,
```

`app/test/features/visit/screens/record_screen_test.dart`:

```diff
@@ -152,8 +152,12 @@ Map<String, dynamic> _savedRecord() => recordJson(
   version: 3,
 );
 
-UploadJob _job(String id, {bool running = false, int failures = 0}) =>
-    UploadJob(
+UploadJob _job(
+  String id, {
+  bool running = false,
+  int failures = 0,
+  String? stoppedCode,
+}) => UploadJob(
       id: id,
       userId: 1,
       shopId: 3,
@@ -163,6 +167,7 @@ UploadJob _job(String id, {bool running = false, int failures = 0}) =>
       progress: 0.5,
       running: running,
       failures: failures,
+      stoppedCode: stoppedCode,
     );
 
 void main() {
@@ -444,6 +449,31 @@ void main() {
     expect(app.queue.removed, ['j2']);
   });
 
+  testWidgets('멈춘 사진은 느낌표이고, 누르면 이유와 [다시 시도]·[올리기 취소]를 보인다', (tester) async {
+    final server = _Server();
+    final (app, _) = await _open(
+      tester,
+      server,
+      uploads: [
+        _job('j1', stoppedCode: 'MEDIA_LIMIT_EXCEEDED'),
+        _job('j2', stoppedCode: 'VISIT_NOT_FOUND'),
+      ],
+    );
+    expect(find.byIcon(Icons.priority_high), findsNWidgets(2));
+    expect(find.text(AppStrings.uploadWaiting), findsNothing);
+
+    await _tap(tester, find.bySemanticsLabel(AppStrings.uploadStopped).first);
+    expect(find.text('방문 하나에 사진은 30장까지 붙일 수 있어요.'), findsOneWidget);
+    await _tap(tester, find.text(AppStrings.retry));
+    expect(app.queue.retried, ['j1']);
+
+    await _tap(tester, find.bySemanticsLabel(AppStrings.uploadStopped).last);
+    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
+    await _tap(tester, find.text(AppStrings.removeUpload).last);
+    expect(app.queue.removed, ['j2']);
+    expect(app.queue.retried, ['j1']);
+  });
+
   testWidgets(
     '사진 추가는 전/후를 고르고 앨범에서 고른 사진을 대기열에 넣는다 — 한도는 30장에서 서버에 붙은 사진(폼에서 뺀 것 포함)과 대기열을 뺀 것',
     (tester) async {
```

`app/test/features/visit/state/upload_queue_test.dart`:

```diff
@@ -2,6 +2,7 @@ import 'dart:async';
 import 'dart:convert';
 import 'dart:io';
 
+import 'package:chagocnote/core/error/api_exception.dart';
 import 'package:chagocnote/core/proxy/app_dirs.dart';
 import 'package:chagocnote/core/proxy/photo_renditions.dart';
 import 'package:chagocnote/core/proxy/providers.dart';
@@ -161,6 +162,7 @@ UploadJob _saved(
   UploadStage stage = UploadStage.prepared,
   int? mediaId,
   int userId = 1,
+  String? stoppedCode,
 }) => UploadJob(
   id: id,
   userId: userId,
@@ -171,6 +173,7 @@ UploadJob _saved(
   width: 3000,
   height: 2000,
   mediaId: mediaId,
+  stoppedCode: stoppedCode,
 );
 
 void main() {
@@ -380,6 +383,84 @@ void main() {
     );
   });
 
+  test('다시 해도 안 되는 실패는 권한·없음·업무 4xx 다 — 인터넷·서버·세션 만료·잦은 시도는 다시 해 본다', () {
+    ApiException error(int status, String code) =>
+        ApiException(statusCode: status, code: code, message: 'x');
+    expect(stopsUpload(error(422, 'MEDIA_LIMIT_EXCEEDED')), isTrue);
+    expect(stopsUpload(error(409, 'MEDIA_ALREADY_ATTACHED')), isTrue);
+    expect(stopsUpload(error(403, 'PERMISSION_DENIED')), isTrue);
+    expect(stopsUpload(error(404, 'VISIT_NOT_FOUND')), isTrue);
+    expect(stopsUpload(ApiException.network('끊김')), isFalse);
+    expect(stopsUpload(error(503, 'HTTP_ERROR')), isFalse);
+    expect(stopsUpload(error(401, 'UNAUTHENTICATED')), isFalse);
+    expect(stopsUpload(error(429, 'TOO_MANY_ATTEMPTS')), isFalse);
+    expect(stopsUpload(StateError('x')), isFalse);
+  });
+
+  test('다시 해도 안 되는 실패면 멈추고 이유를 기기에 남긴다 — 스스로도, 인터넷이 돌아와도 다시 하지 않고 파일은 남는다', () async {
+    final env = env0();
+    var full = true;
+    env.apiFailure = (call) => full && call == 'POST /v1/shops/3/media/uploads'
+        ? const FakeResponse(
+            statusCode: 422,
+            data: {'code': 'MEDIA_LIMIT_EXCEEDED', 'message': 'x'},
+          )
+        : null;
+    await env.open();
+
+    await env.queue.addPhotos(
+      shopId: 3,
+      visitId: 101,
+      phase: MediaPhase.before,
+      sources: ['/picked/a.jpg'],
+    );
+    await _until(() => env.jobs.single.stopped);
+
+    final job = env.jobs.single;
+    expect(job.stoppedCode, 'MEDIA_LIMIT_EXCEEDED');
+    expect(job.waiting, isFalse);
+    expect(env.retries.delays, isEmpty, reason: '간격 재시도를 잡지 않는다');
+    expect(env.savedJson.single['stopped_code'], 'MEDIA_LIMIT_EXCEEDED');
+    expect(env.folders, [job.id]);
+
+    env.network.restore();
+    await Future<void>.delayed(const Duration(milliseconds: 50));
+    expect(
+      env.calls.where((c) => c == 'POST /v1/shops/3/media/uploads'),
+      hasLength(1),
+    );
+
+    // 사용자가 다른 사진을 지워 자리를 낸 뒤 [다시 시도].
+    full = false;
+    await env.queue.retry(job.id);
+    await _until(() => env.drained);
+  });
+
+  test('멈춘 항목은 앱을 다시 켜도 멈춰 있고, 멈춤 칸이 없던 옛 항목은 그대로 올린다', () async {
+    final env = env0(
+      saved: [
+        _saved('j1', stoppedCode: 'VISIT_NOT_FOUND'),
+        _saved('j2'),
+      ],
+    );
+    env.apiFailure = (call) => call == 'POST /v1/shops/3/visits/101/record/media'
+        ? FakeResponse(statusCode: 200, data: recordJson())
+        : null;
+    // 옛 항목 j2 는 stopped_code 없이 저장돼 있었다.
+    final saved = env.savedJson;
+    expect(saved.last.containsKey('stopped_code'), isTrue);
+    File('${root.path}/queue.json').writeAsStringSync(
+      jsonEncode([saved.first, {...saved.last}..remove('stopped_code')]),
+    );
+
+    await env.open();
+    await _until(() => env.jobs.length == 1);
+
+    expect(env.jobs.single.id, 'j1');
+    expect(env.jobs.single.stoppedCode, 'VISIT_NOT_FOUND');
+    expect(env.folders, ['j1']);
+  });
+
   test('서명 URL 이 만료돼 저장소가 거절하면 다음 시도는 발급부터 다시 한다', () async {
     final env = env0();
     var expired = true;
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/features/visit/state/upload_queue_test.dart test/features/visit/screens/record_screen_test.dart`
Expected: 컴파일 실패 — `stoppedCode`·`stopsUpload`·`retry`·`uploadStopped`가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/state/upload_job.dart`:

```diff
@@ -28,6 +28,7 @@ class UploadJob {
     this.progress = 0,
     this.failures = 0,
     this.running = false,
+    this.stoppedCode,
   });
 
   /// 폴더는 업로드 폴더 [root] 아래 항목 ID 다 — iOS 는 앱 폴더의 절대 경로가 실행마다 바뀔 수 있어
@@ -44,6 +45,8 @@ class UploadJob {
         width: json['width'] as int,
         height: json['height'] as int,
         mediaId: json['media_id'] as int?,
+        // 이 칸이 생기기 전에 저장된 항목에는 없다 — 멈추지 않은 것으로 읽는다.
+        stoppedCode: json['stopped_code'] as String?,
       );
 
   final String id;
@@ -61,6 +64,13 @@ class UploadJob {
   final int height;
   final int? mediaId;
 
+  /// 다시 해도 안 되는 실패로 멈췄으면 그 오류 코드(예: `MEDIA_LIMIT_EXCEEDED`). 멈춘 항목은 스스로 다시
+  /// 하지 않고, 사용자가 [다시 시도]하거나 [올리기 취소]할 때까지 파일과 함께 남는다(오류 화면 다듬기
+  /// 설계 4절). 기기에 남긴다.
+  final String? stoppedCode;
+
+  bool get stopped => stoppedCode != null;
+
   // 아래 셋은 기기에 남기지 않는다(다시 켜면 처음부터 센다).
 
   /// 올리기 진행률 0~1.
@@ -72,8 +82,8 @@ class UploadJob {
   /// 지금 올리는 중.
   final bool running;
 
-  /// 실패한 뒤 다시 시도를 기다리는 중 — 타일은 "대기 중"과 [빼기]만 보인다.
-  bool get waiting => failures > 0 && !running;
+  /// 실패한 뒤 다시 시도를 기다리는 중 — 타일은 "대기 중"과 [올리기 취소]만 보인다.
+  bool get waiting => failures > 0 && !running && !stopped;
 
   String? get originalPath => dir == null ? null : '$dir/original.jpg';
   String? get displayPath => dir == null ? null : '$dir/display.jpg';
@@ -88,6 +98,7 @@ class UploadJob {
     double? progress,
     int? failures,
     bool? running,
+    String? Function()? stoppedCode,
   }) => UploadJob(
     id: id,
     userId: userId,
@@ -102,6 +113,7 @@ class UploadJob {
     progress: progress ?? this.progress,
     failures: failures ?? this.failures,
     running: running ?? this.running,
+    stoppedCode: stoppedCode == null ? this.stoppedCode : stoppedCode(),
   );
 
   Map<String, dynamic> toJson() => {
@@ -114,5 +126,6 @@ class UploadJob {
     'width': width,
     'height': height,
     'media_id': mediaId,
+    'stopped_code': stoppedCode,
   };
 }
```

`app/lib/features/visit/state/upload_queue.dart`:

```diff
@@ -6,6 +6,7 @@ import 'package:dio/dio.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../../core/error/api_exception.dart';
+import '../../../core/error/error_kind.dart';
 import '../../../core/proxy/app_dirs.dart';
 import '../../../core/proxy/network_watcher.dart';
 import '../../../core/proxy/photo_renditions.dart';
@@ -29,6 +30,19 @@ final uploadRetrySchedulerProvider = Provider<RetryScheduler>(
   (ref) => Timer.new,
 );
 
+/// 다시 해도 안 되는 실패인가 — 권한·없음·업무 규칙 4xx(한도 초과·형식·크기·방문 삭제 등). 인터넷·서버
+/// 오류와 세션 만료(401)·잦은 시도(429)는 다시 해 볼 만하다(오류 화면 다듬기 설계 4절).
+bool stopsUpload(Object error) {
+  if (error is! ApiException) return false;
+  final status = error.statusCode;
+  return switch (kindOf(error)) {
+    ErrorKind.denied || ErrorKind.gone => true,
+    ErrorKind.other =>
+      status != null && status >= 400 && status < 500 && status != 401 && status != 429,
+    ErrorKind.offline || ErrorKind.server => false,
+  };
+}
+
 /// [failures]번 연달아 실패한 뒤 다시 시도까지 — 1·2·4… 초, 최대 5분(설계 10.2).
 Duration retryDelay(int failures) =>
     Duration(seconds: min(300, 1 << min(failures - 1, 9)));
@@ -140,7 +154,7 @@ class UploadQueue extends AsyncNotifier<List<UploadJob>> {
     }
   }
 
-  /// [빼기] — 올리는 중이면 취소한다. 취소는 오류가 아니라 아무 문구도 없다.
+  /// [올리기 취소] — 올리는 중이면 취소한다. 취소는 오류가 아니라 아무 문구도 없다.
   Future<void> remove(String id) async {
     final job = _find(id);
     if (job == null) return;
@@ -154,7 +168,15 @@ class UploadQueue extends AsyncNotifier<List<UploadJob>> {
     await _store.deleteDir(_dirOf(id));
   }
 
-  /// 기다리는 항목을 지금 다시 해 본다(인터넷이 돌아왔을 때).
+  /// 멈춘 항목을 [다시 시도] — 멈춘 이유와 실패 횟수를 지우고 처음처럼 다시 태운다.
+  Future<void> retry(String id) async {
+    if (_find(id)?.stopped != true) return;
+    _update(id, (j) => j.copyWith(failures: 0, stoppedCode: () => null));
+    await _persist();
+    unawaited(_pump());
+  }
+
+  /// 기다리는 항목을 지금 다시 해 본다(인터넷이 돌아왔을 때). 멈춘 항목은 건드리지 않는다.
   void retryNow() {
     for (final t in _timers.values) {
       t.cancel();
@@ -174,6 +196,7 @@ class UploadQueue extends AsyncNotifier<List<UploadJob>> {
               (j) =>
                   j.stage != UploadStage.preparing &&
                   !j.running &&
+                  !j.stopped &&
                   !_timers.containsKey(j.id),
             )
             .firstOrNull;
@@ -219,15 +242,18 @@ class UploadQueue extends AsyncNotifier<List<UploadJob>> {
         await remove(job.id);
         return;
       }
-      if (e is ApiException &&
-          e.code == 'MEDIA_NOT_FOUND' &&
-          _find(job.id)?.mediaId != null) {
+      if (e is ApiException && e.code == 'MEDIA_NOT_FOUND') {
         // 서버가 붙지 않은 사진을 정리했다 — 간격을 두고 로컬 파일로 발급부터 다시 한다.
-        _update(
-          job.id,
-          (j) => j.copyWith(stage: UploadStage.prepared, mediaId: () => null),
-        );
-        await _persist();
+        if (_find(job.id)?.mediaId != null) {
+          _update(
+            job.id,
+            (j) => j.copyWith(stage: UploadStage.prepared, mediaId: () => null),
+          );
+          await _persist();
+        }
+      } else if (stopsUpload(e)) {
+        await _stop(job.id, (e as ApiException).code);
+        return;
       }
       _fail(job.id);
     }
@@ -300,6 +326,15 @@ class UploadQueue extends AsyncNotifier<List<UploadJob>> {
     ref.invalidate(petDetailProvider);
   }
 
+  /// 다시 해도 안 되는 실패 — 스스로 다시 하지 않고 이유를 남긴다. 파일은 그대로 둔다.
+  Future<void> _stop(String id, String code) async {
+    _update(
+      id,
+      (j) => j.copyWith(running: false, progress: 0, stoppedCode: () => code),
+    );
+    await _persist();
+  }
+
   void _fail(String id) {
     final failures = (_find(id)?.failures ?? 0) + 1;
     _update(
```

`app/lib/l10n/app_strings.dart`:

```diff
@@ -383,6 +383,7 @@ class AppStrings {
   static const addPhotoPhaseLabel = '어느 사진인가요?';
   static const uploading = '올리는 중';
   static const uploadWaiting = '대기 중';
+  static const uploadStopped = '올리지 못한 사진';
   static const removeUpload = '올리기 취소';
   static const removePhoto = '사진 빼기';
   static const recordMenusLabel = '메뉴 · 금액';
```

`app/lib/features/visit/screens/record_photos.dart`:

```diff
@@ -16,6 +16,7 @@ import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_progress_ring.dart';
 import '../../../design/widgets/app_segment.dart';
 import '../../../design/widgets/app_sheet.dart';
+import '../../../design/widgets/app_sheet_action.dart';
 import '../../../design/widgets/app_snack_bar.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
@@ -98,6 +99,7 @@ class RecordPhotoStrip extends ConsumerWidget {
                 job: job,
                 onRemove: () =>
                     ref.read(uploadQueueProvider.notifier).remove(job.id),
+                onStopped: () => _openStopped(context, ref, job),
               ),
             ),
         ],
@@ -206,40 +208,107 @@ class _MediaTile extends StatelessWidget {
   }
 }
 
-/// 대기열의 사진 — 기기에 있는 썸네일 위에 진행 링. 실패해 기다리는 중이면 "대기 중"과 [빼기]만.
+/// 대기열의 사진 — 기기에 있는 썸네일 위에 진행 링. 실패해 기다리는 중이면 "대기 중"과 [올리기 취소]만.
+/// 다시 해도 안 되는 실패로 멈췄으면 느낌표 — 누르면 이유와 [다시 시도]·[올리기 취소](오류 화면 다듬기
+/// 설계 4절).
 class _UploadTile extends StatelessWidget {
-  const _UploadTile({required this.job, required this.onRemove});
+  const _UploadTile({
+    required this.job,
+    required this.onRemove,
+    required this.onStopped,
+  });
 
   final UploadJob job;
   final VoidCallback onRemove;
+  final VoidCallback onStopped;
 
   @override
   Widget build(BuildContext context) {
     final thumb = job.thumbPath;
+    final tile = Stack(
+      alignment: Alignment.center,
+      children: [
+        AppPhotoTile(
+          image: thumb == null ? null : FileImage(File(thumb)),
+          size: _tileSize,
+        ),
+        if (job.stopped)
+          const _StoppedBadge()
+        else if (job.waiting)
+          const _Pill(AppStrings.uploadWaiting)
+        else
+          AppProgressRing(
+            value: job.stage == UploadStage.preparing || !job.running
+                ? null
+                : job.progress,
+          ),
+        _RemoveButton(label: AppStrings.removeUpload, onTap: onRemove),
+      ],
+    );
+    if (job.stopped) {
+      return Pressable(
+        semanticLabel: AppStrings.uploadStopped,
+        onTap: onStopped,
+        child: tile,
+      );
+    }
     return Semantics(
       label: job.waiting ? AppStrings.uploadWaiting : AppStrings.uploading,
-      child: Stack(
-        alignment: Alignment.center,
-        children: [
-          AppPhotoTile(
-            image: thumb == null ? null : FileImage(File(thumb)),
-            size: _tileSize,
-          ),
-          if (job.waiting)
-            const _Pill(AppStrings.uploadWaiting)
-          else
-            AppProgressRing(
-              value: job.stage == UploadStage.preparing || !job.running
-                  ? null
-                  : job.progress,
-            ),
-          _RemoveButton(label: AppStrings.removeUpload, onTap: onRemove),
-        ],
-      ),
+      child: tile,
     );
   }
 }
 
+class _StoppedBadge extends StatelessWidget {
+  const _StoppedBadge();
+
+  @override
+  Widget build(BuildContext context) => Container(
+    width: 28,
+    height: 28,
+    decoration: const BoxDecoration(
+      color: AppColors.white,
+      shape: BoxShape.circle,
+    ),
+    child: const Icon(Icons.priority_high, size: 18, color: AppColors.ink),
+  );
+}
+
+/// 멈춘 사진의 시트 — 이유 한 줄과 [다시 시도]·[올리기 취소].
+Future<void> _openStopped(
+  BuildContext context,
+  WidgetRef ref,
+  UploadJob job,
+) async {
+  final retry = await AppSheet.show<bool>(
+    context,
+    builder: (context) => Column(
+      mainAxisSize: MainAxisSize.min,
+      children: [
+        Text(
+          messageFor(
+            ApiException(statusCode: null, code: job.stoppedCode!, message: ''),
+          ),
+          style: AppTypography.body,
+          textAlign: TextAlign.center,
+        ),
+        const SizedBox(height: AppSpacing.lg),
+        AppSheetAction(
+          label: AppStrings.retry,
+          onTap: () => Navigator.of(context).pop(true),
+        ),
+        AppSheetAction(
+          label: AppStrings.removeUpload,
+          onTap: () => Navigator.of(context).pop(false),
+        ),
+      ],
+    ),
+  );
+  if (retry == null) return;
+  final queue = ref.read(uploadQueueProvider.notifier);
+  await (retry ? queue.retry(job.id) : queue.remove(job.id));
+}
+
 enum _Source { camera, album }
 
 /// [사진 추가] — 전/후를 고르고 카메라·앨범에서 가져와 대기열에 넣는다. [attached]는 서버 기록에 붙은
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

같은 명령 → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 698 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_pump`의 `!j.stopped &&`를 지우면 → `upload_queue_test.dart::멈춘 항목은 앱을 다시 켜도 멈춰 있고…` 실패.
- `} else if (stopsUpload(e)) {`를 `} else if (false) {`로 → `다시 해도 안 되는 실패면 멈추고 이유를 기기에 남긴다…` 실패.
- `UploadJob.fromJson`의 `stoppedCode:` 줄을 지우면 → `멈춘 항목은 앱을 다시 켜도 멈춰 있고…` 실패.
- `retry`의 `_update(… stoppedCode: () => null)` 줄을 지우면 → `다시 해도 안 되는 실패면 멈추고…`가 기다리다 실패.
- `stopsUpload`에서 `&& status != 401 && status != 429`를 빼면 → `다시 해도 안 되는 실패는 권한·없음·업무 4xx 다…` 실패.
- 시트의 `retry ? queue.retry(job.id) : queue.remove(job.id)`를 바꿔 끼우면 → `record_screen_test.dart::멈춘 사진은 느낌표이고, 누르면 이유와 [다시 시도]·[올리기 취소]를 보인다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 대기열 멈춤 — 다시 해도 안 되는 실패(권한·없음·업무 4xx)는 스스로 다시 하지 않고 이유를 기기에 남긴다, 느낌표 타일과 [다시 시도]·[올리기 취소] 시트

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: 시뮬레이터 흐름(띠·처음 실패·인터넷 복귀·대기열 멈춤)과 문서 — 앱 규칙·하네스·결정 기록 007

**Files:**
- Create: `app/integration_test/error_flow_test.dart`
- Modify: `app/CLAUDE.md`
- Modify: `_docs/harness.md`
- Modify: `_docs/decisions/007-record-media.md`

**Interfaces:**
- Consumes: 작업 1~9 전부, `integration_test/flow_kit.dart`, `app/tool/prepare_record_flow.sh`(그대로), `buildRoot(overrides:)`.
- Produces: `integration_test/error_flow_test.dart`(확인 넷), 문서 셋.

기기 연결은 흐름이 끊을 수 없고, 네이티브 `flutter drive`는 스크린샷을 테스트가 끝난 뒤 한꺼번에 맥으로 넘겨 흐름 도중 맥에서 게이트웨이를 끌 수도 없다(참조 구현에서 확인). 그래서 앱의 API `Dio`(`dioProvider`)에 스위치(`Outage` — 연결 실패 / 503)를 끼우고, 인터넷 복귀 신호는 흐름이 보내며(`FlowNetwork`), 대기열의 간격 재시도는 멈춰 둔다(복귀 신호가 곧 다시 시도). 서버·렌디션·업로드는 실제로 한다. 대기열 멈춤은 사진을 넣은 뒤 API 로 방문을 미용 전으로 되돌려 덧붙이기가 `VISIT_NO_RECORD_YET`(422)로 거절되게 하고, 다시 시작한 뒤 [다시 시도]로 붙인다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/integration_test/error_flow_test.dart`:

```dart
// 오류 화면 다듬기 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 받은 데이터 위 띠(인터넷 없음·
// 서버 오류), 처음 실패의 원인 문구, 인터넷 복귀 때 스스로 다시 불러오기, 대기열 멈춤과 [다시 시도]를 확인한다.
// 도구는 `flow_kit.dart`.
//
// 기기의 연결은 흐름이 끊을 수 없다. 그래서 앱의 API `Dio`에 스위치([Outage])를 끼워 요청을 연결 실패나 503 으로
// 돌려보내고, 인터넷 복귀 신호는 [FlowNetwork]로 보낸다. 대기열의 간격 재시도는 흐름이 기다리지 않게 멈춰
// 둔다 — 복귀 신호가 곧 다시 시도다. 그 밖은 실제로 한다(서버·렌디션·업로드).
//
// 준비(infra/ 에서): bash ../app/tool/prepare_record_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/error_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'dart:async';

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_error_banner.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const visitA = int.fromEnvironment('VISIT_A');
const visitB = int.fromEnvironment('VISIT_B');
const ownerName = String.fromEnvironment('OWNER');

enum OutageMode { offline, server }

/// 요청을 서버에 닿기 전에 돌려보내는 스위치. [mode]가 null 이면 그대로 보낸다.
class Outage extends Interceptor {
  OutageMode? mode;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    switch (mode) {
      case null:
        handler.next(options);
      case OutageMode.offline:
        handler.reject(
          DioException.connectionError(requestOptions: options, reason: '흐름: 끊김'),
        );
      case OutageMode.server:
        handler.reject(
          DioException.badResponse(
            statusCode: 503,
            requestOptions: options,
            response: Response(
              requestOptions: options,
              statusCode: 503,
              data: 'Service Unavailable',
            ),
          ),
        );
    }
  }
}

/// 인터넷 복귀 신호 — 흐름이 [restore]로 보낸다.
class FlowNetwork implements NetworkWatcher {
  final _controller = StreamController<void>.broadcast();

  @override
  Stream<void> get restored => _controller.stream;

  void restore() => _controller.add(null);
}

/// 대기열의 간격 재시도를 멈춰 둔다(돌지 않는 타이머).
Timer _never(Duration delay, void Function() run) => Timer(
  const Duration(days: 1),
  () {},
);

/// 카메라 대신 — 한 장.
class OnePhoto implements MediaPicker {
  var made = 0;

  @override
  Future<List<String>> pickPhotos({required int limit}) async => [
    await makePhoto('eflow-${made++}', made),
  ];

  @override
  Future<String?> takePhoto() => makePhoto('eflow-${made++}', made);
}

final outage = Outage();
final network = FlowNetwork();

String get today {
  final now = DateTime.now();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${now.year}-${two(now.month)}-${two(now.day)}';
}

Finder bannerWith(String text) => find.descendant(
  of: find.byType(AppErrorBanner),
  matching: find.text(text),
);

Future<void> pull() async {
  final list = find.byWidgetPredicate(
    (w) => w is ListView && w.scrollDirection == Axis.vertical,
  );
  await t.fling(list.first, const Offset(0, 500), 1200);
  await pumpFor(const Duration(seconds: 2));
}

Future<int> photosOf(int visitId) async {
  final detail = await container.read(visitApiProvider).detail(shopId, visitId);
  return detail.record?.media.length ?? 0;
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('오류 화면 다듬기 완료 기준', timeout: const Timeout(Duration(minutes: 15)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    await t.pumpWidget(
      buildRoot(
        overrides: [
          dioProvider.overrideWith(
            (ref) => Dio(
              BaseOptions(
                baseUrl: ref.watch(appConfigProvider).apiBaseUrl,
                connectTimeout: const Duration(seconds: 10),
                receiveTimeout: const Duration(seconds: 15),
                sendTimeout: const Duration(seconds: 15),
              ),
            )..interceptors.add(outage),
          ),
          networkWatcherProvider.overrideWithValue(network),
          uploadRetrySchedulerProvider.overrideWithValue(_never),
          mediaPickerProvider.overrideWithValue(OnePhoto()),
        ],
      ),
    );
    final end = DateTime.now().add(const Duration(seconds: 40));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 100));
      drain();
      if (find.byKey(ScreenKeys.login).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.home).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.shopSelect).evaluate().isNotEmpty) {
        break;
      }
    }
    if (find.byKey(ScreenKeys.login).evaluate().isEmpty) await logout();
    await login(ownerName);

    await step('1', '하루 목록 — 당겼는데 인터넷 없음이면 목록은 두고 띠, 돌아오면 스스로 다시 불러와 띠가 사라진다', () async {
      router.push('/visits/day/$today');
      await waitFor(find.byKey(ScreenKeys.day));
      await waitFor(find.text('콩이').first);
      outage.mode = OutageMode.offline;
      await pull();
      await shot('01a-offline-banner');
      soft(bannerWith(offlineBannerMessage).evaluate().isNotEmpty, '인터넷 없음 띠가 없다');
      soft(find.text('콩이').evaluate().isNotEmpty, '받은 목록이 사라졌다');
      soft(find.text(AppStrings.retry).evaluate().isEmpty, '인터넷 없음 띠에 [다시 시도]가 있다');

      outage.mode = null;
      network.restore();
      await pumpFor(const Duration(seconds: 2));
      await shot('01b-restored');
      soft(find.byType(AppErrorBanner).evaluate().isEmpty, '돌아왔는데 띠가 남았다');
    });

    await step('2', '하루 목록 — 서버 오류면 띠에 [다시 시도], 누르면 다시 불러와 띠가 사라진다', () async {
      outage.mode = OutageMode.server;
      await pull();
      await shot('02a-server-banner');
      soft(
        bannerWith('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.').evaluate().isNotEmpty,
        '서버 오류 띠가 없다',
      );
      outage.mode = null;
      await tap(find.descendant(of: find.byType(AppErrorBanner), matching: find.text(AppStrings.retry)));
      await pumpFor(const Duration(seconds: 2));
      await shot('02b-retried');
      soft(find.byType(AppErrorBanner).evaluate().isEmpty, '다시 불러왔는데 띠가 남았다');
    });

    await step('3', '방문 상세 — 처음부터 인터넷 없음이면 원인 문구와 [다시 시도], 돌아오면 스스로 연다', () async {
      outage.mode = OutageMode.offline;
      router.push('/visits/$visitA');
      await waitFor(find.text(offlineLoadMessage));
      await shot('03a-offline-first');
      soft(find.text(AppStrings.retry).evaluate().isNotEmpty, '[다시 시도]가 없다');
      outage.mode = null;
      network.restore();
      await waitFor(p(AppStrings.addPhoto));
      await shot('03b-opened');
    });

    await step('4', '대기열 — 다시 해도 안 되는 실패(미용 전으로 되돌린 방문)면 멈춰 느낌표, 시작한 뒤 [다시 시도]로 붙는다', () async {
      await openVisit(visitB);
      outage.mode = OutageMode.offline;
      await tap(p(AppStrings.addPhoto));
      await tap(btn(AppStrings.takePhoto));
      await waitFor(find.text(AppStrings.uploadWaiting));
      await shot('04a-waiting');

      // 서버에서 방문을 미용 전으로 되돌린다 — 덧붙이기가 VISIT_NO_RECORD_YET(422)로 거절된다.
      outage.mode = null;
      final api = container.read(visitApiProvider);
      await api.transition(shopId, visitIds: [visitB], action: VisitAction.revert);
      network.restore();
      await waitFor(find.byIcon(Icons.priority_high), timeout: const Duration(seconds: 60));
      await shot('04b-stopped');
      final job = container.read(uploadQueueProvider).value!.single;
      note('멈춘 이유 ${job.stoppedCode}');
      soft(job.stoppedCode == 'VISIT_NO_RECORD_YET', '멈춘 이유가 다르다');

      await api.transition(shopId, visitIds: [visitB], action: VisitAction.start);
      await tap(p(AppStrings.uploadStopped));
      await waitFor(find.text('미용을 시작한 방문에만 기록을 쓸 수 있어요.'));
      await shot('04c-sheet');
      await tap(find.text(AppStrings.retry));
      final end = DateTime.now().add(const Duration(seconds: 60));
      while (await photosOf(visitB) < 1) {
        if (DateTime.now().isAfter(end)) throw TestFailure('사진이 붙지 않았다');
        await pumpFor(const Duration(seconds: 1));
      }
      await pumpFor(const Duration(seconds: 2));
      await shot('04d-attached');
      soft(container.read(uploadQueueProvider).value!.isEmpty, '대기열이 비지 않았다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

흐름·문서 작업이라 먼저 실패하는 단위 테스트는 없다. Run (`app/`): `flutter analyze` → `No issues found!`(흐름 파일 포함).

- [ ] **Step 3: 구현한다**

`app/CLAUDE.md`:

```diff
@@ -6,10 +6,11 @@
 
 - **웹뷰 방식 금지.** 웹뷰 패키지를 넣지 않고, 어떤 화면도 인앱 웹뷰로 만들지 않는다. 소셜 로그인도 네이티브 경로다(Apple 버튼은 iOS 만).
 - 폴더는 `lib/core/{config,proxy,storage,router,error,time,plugs}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
-- **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`의 `buildRoot`가 채운다(지금은 반려동물 상세의 [기록] 탭 `petRecordsPlugProvider` ← visit 의 `PetRecordsView`). 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
+- **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`의 `buildRoot`가 채운다(지금은 반려동물 상세의 [기록] 탭 `petRecordsPlugProvider` ← visit 의 `PetRecordsView`, 그 탭을 다시 읽는 `petRecordsRefreshPlugProvider` ← `petRecordsRefresher`). 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
 - **매장 범위 화면**은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다. `auth/state/shop_selection.dart`의 파생 프로바이더(`selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider`·`shopCountProvider`·`currentUserIdProvider`)만 watch 한다. 매장 선택 전(account·auth 화면: 로그인·스플래시·초대·매장 선택·계정)은 세션 전체를 봐야 하므로 이 규칙 밖이다.
 - 플러그인은 `lib/core/proxy/`의 프로바이더로만 부른다 — 클립보드 `clipboardProvider`, 사진 고르기·찍기 `mediaPickerProvider`, 렌디션(리사이즈·EXIF 제거) `photoRenditionMakerProvider`, 인터넷 복귀 신호 `networkWatcherProvider`, 업로드 폴더 `uploadsDirProvider`, 서명 URL 사진 보이기와 원본 받기 `mediaImagesProvider`, 앨범에 저장 `photoAlbumProvider`(마이크·음성은 ④-3). 화면은 `Clipboard`·`ImagePicker`·`Image.network`를 직접 부르지 않는다. 테스트는 프로바이더를 override 한다(`test/support/upload_fakes.dart`). 서명 URL 업로드는 `core/proxy/upload_client.dart`(인증 헤더 없음·진행률·재시도 없음)로 하고, 사용자가 취소한 업로드는 `ApiException`의 `CANCELLED`라 문구를 띄우지 않는다.
-- **사진 올리기는 업로드 대기열(`features/visit/state/upload_queue.dart`)로만 한다.** 화면은 `uploadQueueProvider.notifier`의 `addPhotos`·`remove`만 부르고, 대기 중인 사진은 `visitUploadsProvider(visitId)`로 본다. 대기열이 발급 → 올리기 셋 → 확인 → 덧붙이기를 하고 기기에 남긴다(설계 10.2). 기록 전체 교체(`saveRecord`)는 이미 붙은 사진만 보낸다 — 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 새 사진을 더해 한 번 더 보낸다(`record_screen.dart`).
+- **서버에서 읽는 화면 본문은 `core/error/async_body.dart`의 `AsyncBody`로 그린다**(`test/design/async_body_usage_test.dart`). 불러오는 중·처음 실패(원인 문구와 [다시 시도], 권한·없음은 뒤로 갈 수 있으면 [돌아가기])·받은 데이터 위 띠·인터넷 복귀 때 스스로 다시 불러오기·`onRefresh`의 당겨서 새로고침을 한 곳에서 한다. 화면은 `AppErrorRetry`의 가운데·inline 모양을 직접 만들지 않는다(한 줄 `AppErrorRetry.row`는 다음 쪽 실패 같은 좁은 자리에만). 오류 문구는 누른 일이면 `messageFor`, 화면을 불러오지 못했으면 `loadMessageFor`(원인은 `core/error/error_kind.dart`의 `kindOf`). 앱 문구는 해요체다(`test/design/copy_tone_test.dart`).
+- **사진 올리기는 업로드 대기열(`features/visit/state/upload_queue.dart`)로만 한다.** 화면은 `uploadQueueProvider.notifier`의 `addPhotos`·`remove`·`retry`만 부르고, 다시 해도 안 되는 실패(`stopsUpload`)로 멈춘 항목은 스스로 다시 하지 않는다 — 사용자가 [다시 시도]하거나 [올리기 취소]한다. 대기 중인 사진은 `visitUploadsProvider(visitId)`로 본다. 대기열이 발급 → 올리기 셋 → 확인 → 덧붙이기를 하고 기기에 남긴다(설계 10.2). 기록 전체 교체(`saveRecord`)는 이미 붙은 사진만 보낸다 — 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 새 사진을 더해 한 번 더 보낸다(`record_screen.dart`).
 - **사진을 보이는 순서는 대표 규칙이다**(`features/visit/state/photo_edits.dart`의 `galleryOrder` — 후 → 전 → 영상, 첫 장이 대표). 크게 보기의 전/후 바꾸기·대표로·삭제는 `applyPhotoEdit` + `recordInputOf`로 기록 전체 교체 한 번이고, 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 같은 바꾸기를 한 번 더 보낸다.
 - 글래스는 떠 있는 조작 계층에만 쓴다(`test/design/glass_boundary_test.dart`). 예외는 피드 카드의 이름 카드 하나(④ 설계 10.1 ②) — 실제 글래스는 비쳐 보이므로 그 위 글자는 잉크색으로 쓴다.
 - 서버의 상태 문자열은 `fromJson`에서 enum(`VisitStatus`·`VisitAction`)으로 한 번만 바꾼다. 화면의 `switch`는 `_ =>` 폴백 없이 완전 열거한다 — 상태·행동을 더하면 컴파일러가 빠진 곳을 찾는다.
```

`_docs/harness.md`:

```diff
@@ -25,7 +25,7 @@
 | 앱 구조 테스트 (기능 폴더 import 방향·라우터 가드 전수) | `flutter test test/design/feature_imports_test.dart test/core/router/app_router_test.dart` (`app/`에서. 전체 테스트에 포함되지만 구조를 건드린 변경은 이 둘을 먼저 돌린다) |
 | 앱 골든 갱신 | `flutter test --update-goldens` (`app/`에서, 의도해서 바꿀 때만) |
 | 앱 개발용 실행 | `app/tool/run_dev.sh` (백엔드를 `infra/`에서 먼저 띄운 뒤) |
-| 앱 흐름 확인 (시뮬레이터 + 실서버) | `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/<파일> -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 …` (`app/`에서. 파일 머리 주석에 준비와 추가 `--dart-define`이 있다 — `visit_flow_test.dart`(③-A2), `draft_flow_test.dart`(③-A3 카톡 초안), `record_flow_test.dart`(④-2a 사진·기록·완료 — 준비는 `infra/`에서 `bash ../app/tool/prepare_record_flow.sh`, 실행마다 새로), `photo_flow_test.dart`(④-2b 넘기기·크게 보기·원본 저장·피드·달력·고객 탭 사진 — 준비는 같은 스크립트, 그리고 실행마다 바로 앞에 `xcrun simctl privacy <기기> grant photos-add com.chagocnote.app`: `flutter drive`가 끝날 때 앱을 지워 권한도 사라진다)). 공용 도구는 `integration_test/flow_kit.dart`. 안드로이드 에뮬레이터는 `-d emulator-5554`로 같은 명령을 쓰되, 먼저 `adb reverse tcp:8080 tcp:8080`과 `adb reverse tcp:9010 tcp:9010`(에뮬레이터 안의 127.0.0.1 을 맥의 게이트웨이·MinIO 로)을 한다 — 앨범 권한은 API 29 넘으면 필요 없다. zsh 에서 준비 결과를 변수로 받으면 `${=D}`로 펼친다 — 그냥 `$D`는 한 인자로 넘어가 `--dart-define`이 비는다 |
+| 앱 흐름 확인 (시뮬레이터 + 실서버) | `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/<파일> -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 …` (`app/`에서. 파일 머리 주석에 준비와 추가 `--dart-define`이 있다 — `visit_flow_test.dart`(③-A2), `draft_flow_test.dart`(③-A3 카톡 초안), `record_flow_test.dart`(④-2a 사진·기록·완료 — 준비는 `infra/`에서 `bash ../app/tool/prepare_record_flow.sh`, 실행마다 새로), `photo_flow_test.dart`(④-2b 넘기기·크게 보기·원본 저장·피드·달력·고객 탭 사진 — 준비는 같은 스크립트, 그리고 실행마다 바로 앞에 `xcrun simctl privacy <기기> grant photos-add com.chagocnote.app`: `flutter drive`가 끝날 때 앱을 지워 권한도 사라진다), `error_flow_test.dart`(오류 화면 다듬기 — 띠·처음 실패 문구·인터넷 복귀·대기열 멈춤, 준비는 같은 스크립트)). 공용 도구는 `integration_test/flow_kit.dart`. 안드로이드 에뮬레이터는 `-d emulator-5554`로 같은 명령을 쓰되, 먼저 `adb reverse tcp:8080 tcp:8080`과 `adb reverse tcp:9010 tcp:9010`(에뮬레이터 안의 127.0.0.1 을 맥의 게이트웨이·MinIO 로)을 한다 — 앨범 권한은 API 29 넘으면 필요 없다. zsh 에서 준비 결과를 변수로 받으면 `${=D}`로 펼친다 — 그냥 `$D`는 한 인자로 넘어가 `--dart-define`이 비는다 |
 | 공유 받기 확인 | 실기기에서 카톡 [공유] → 차곡노트 (시뮬레이터엔 카톡이 없고 App Group 은 서명이 있어야 붙는다) |
 
 - 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 쓴다. 개발 데이터를 건드리지 않는다. pytest가 세션마다 한 번 `scripts/prepare_test_db.py`를 돌려 스키마를 비우고 `alembic upgrade head`로 다시 만든다. 테스트 사이에는 시드 표(`roles`, `permissions`, `role_permissions`, `pet_condition_types`)와 마이그레이션 버전 표(`alembic_version`)를 뺀 모든 표를 비운다.
```

`_docs/decisions/007-record-media.md`:

```diff
@@ -162,3 +162,29 @@
 - 크게 보기의 알림 띠가 아래 버튼 줄을 3초 가린다.
 - 앨범 저장은 시뮬레이터에서만 확인했다(실기기는 ④-3 과 함께).
 
+
+## 오류 화면 다듬기에서 정한 것
+
+설계는 `docs/superpowers/specs/2026-09-26-error-polish-design.md`(④ 설계 14절의 작은 계획)다. 앱만 바꿨다.
+
+### 설계와 다르게 간 것
+
+- **문구 함수가 인자 하나 대신 이름 둘이다.** `messageFor`는 누른 일(저장·삭제)의 문구로 그대로 두고(부르는 곳 서른다섯 곳을 바꾸지 않는다), 화면을 불러오지 못했을 때는 `loadMessageFor`를 쓴다. 둘은 인터넷 없음 문구만 다르다("연결을 확인해 주세요" / "연결되면 다시 불러올게요").
+- **스플래시의 인터넷 없음 문구는 화면 불러오기 문구와 같다**("연결되면 다시 불러올게요"). 설계 5절의 "다시 시도할게요"와 한 단어 다르지만 문구를 하나로 둔다.
+- **한 줄 오류(휴무일 목록·시간 칸)는 `AsyncBody`로 옮기지 않았다.** 좁은 자리라 `AppErrorRetry.row`에 원인 문구만 쓰고, 인터넷이 돌아와도 스스로 다시 부르지 않는다(누르면 다시). 다음 쪽 실패(피드·고객 목록)는 컨트롤러가 복귀 때 다시 부른다.
+
+### 이 계획에서 새로 정한 것
+
+- `AsyncBody`와 두 목록 컨트롤러는 **오류가 인터넷 없음인 동안만** 복귀 신호를 듣는다 — 멀쩡한 화면은 듣지 않는다. 테스트에는 연결 상태 플러그인이 없어 늘 들으면 예외가 난다. 공용 테스트 준비물(`CustomerTestSetup`)은 `FakeNetworkWatcher`를 기본으로 끼운다(`setup.network`).
+- `AsyncBody.inline`의 `placeholder` — 달력은 처음 불러오는 동안 로딩 대신 빈 칸을, 스플래시는 앱 이름과 로딩을 보인다.
+- 여럿을 기다리는 폼(예약 폼·반려동물 폼·기록 화면)은 값들을 `AsyncValue<void>` 하나로 묶어 `AsyncBody`에 넘긴다. **기록 화면은 한 번 채운 뒤에는 다시 읽기가 실패해도 폼을 남긴다** — 예전에는 409 뒤 다시 읽기가 실패하면 쓰던 폼이 오류 화면으로 바뀌었다.
+- 비어 있는 목록도 당겨서 새로고침이 되게 스크롤 면(`SliverFillRemaining`)에 둔다. 목록은 `AlwaysScrollableScrollPhysics`.
+- 반려동물 상세를 당기면 보호자 탭과 [기록] 탭도 다시 읽는다 — [기록] 탭은 visit 것이라 `core/plugs`의 `petRecordsRefreshPlugProvider` 자리에 `buildRoot`가 `petRecordsRefresher`를 꽂는다(채우지 않으면 아무것도 하지 않는다).
+- 대기열이 멈추는 실패는 `stopsUpload`: 권한·없음·업무 4xx. 세션 만료(401)·잦은 시도(429)·인터넷·서버는 다시 해 본다. `MEDIA_NOT_FOUND`는 예전처럼 재발급 쪽이다. 멈춘 이유는 `queue.json`의 `stopped_code`에 남는다(옛 항목엔 없어 null).
+- 시뮬레이터 흐름 `error_flow_test.dart`는 기기 연결을 끊을 수 없어 앱의 API `Dio`에 스위치를 끼워 연결 실패·503 을 흉내 내고, 복귀 신호를 흐름이 보낸다(네이티브 `flutter drive`는 스크린샷을 끝에 한꺼번에 넘겨 흐름 도중 맥에서 게이트웨이를 끌 수 없다).
+
+### 남는 것 — 알고 미룬다
+
+- 달력 미리보기의 오류는 원인 문구만 보이고 스스로 다시 부르지 않는다.
+- 게이트웨이가 꺼져 연결이 거절돼도 "인터넷에 연결되지 않았어요"로 보인다(기기는 원인을 가릴 수 없다). 운영에서는 게이트웨이 뒤가 죽으면 502 라 서버 문구다.
+- 서버 문구는 합니다체 그대로다(앱이 모르는 코드일 때만 보인다).
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 698 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

Run (`infra/`): `D=$(bash ../app/tool/prepare_record_flow.sh | tail -1)`

Run (`app/`): `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/error_flow_test.dart -d <시뮬레이터> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 ${=D}` → `PASS 1`~`PASS 4`, `All tests passed.` 스크린샷을 눈으로 본다(`01a-offline-banner` 목록 위 끊김 띠, `02a-server-banner` [다시 시도] 띠, `03a-offline-first` 원인 문구, `04b-stopped` 느낌표 타일, `04c-sheet` 이유와 두 버튼, `04d-attached`).

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 흐름·문서 작업이라 변이는 없다. 참조 구현의 첫 실행에서 흐름이 [사진 추가]를 글자로 찾아 `3`이 실패했다 — 아이콘 타일이라 `p(AppStrings.addPhoto)`로 찾는다.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "docs(app): 오류 화면 다듬기 — 시뮬레이터 흐름(띠·처음 실패·인터넷 복귀·대기열 멈춤), 앱 규칙·하네스·결정 기록 007

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---
