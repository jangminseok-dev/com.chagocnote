# 차곡노트 ④ 미용 기록·피드 뷰 — 계획 ④-0 앱: SOLID 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ①~③ 앱 코드에서 SOLID 감사(설계 4.2절 A1~A13)가 찾은 위반을 **기능 코드 없이** 전부 고친다 — `flutter analyze` 0, 테스트 전부 통과, 골든 변경 없음, 새 의존성 없음.

**Architecture:** 열한 작업이 각각 하나의 위반을 닫는다. ① 세션 파생 프로바이더 다섯(화면은 그것만 `select`로 watch) ② 공유 상태의 자리(오늘 날짜는 `core/time`, `runShopScoped`는 `auth/state`, 메뉴·일정 설정은 `visit/screens/settings/`) ③ 기능 폴더 import 방향과 구조 테스트 ④ `VisitStatus`·`VisitAction` enum 과 sealed `AfterComplete` ⑤ 키 기반 `PrefsStore`와 `ViewModeController<T>` 하나 ⑥ 홈 탭 목록 하나와 라우터 가드 기본값 뒤집기 ⑦ 오류·재시도 21곳·시트 항목·검색창을 `design/widgets`로 ⑧ 폼 규칙을 순수 객체 `VisitFormDraft`로, 시간표 범위를 `day_layout`으로, 고객 상세는 `pets`만 select ⑨ `GlassSurface` 반지름 계약 ⑩ `core/proxy`에 `clipboardProvider`·`UploadClient` ⑪ 문서. 어느 작업도 화면 구성·API 호출·서버 필드를 바꾸지 않는다. 모든 코드는 참조 작업 트리(`.superpowers/ref/wt-record-4-0-app`, 브랜치 `ref/record-4-0-app`, 커밋 93ad185…5f7f4f8)에서 먼저 돌려 검증했고, 변이 22개로 판별력을 확인했다(가드 변이 하나가 통과해 작업 6 의 라우터 가드를 고쳤다 — "이 계획에서 새로 정한 것").

**Tech Stack:** Flutter 3.44 · Riverpod 3 · go_router 18 · dio · flutter_secure_storage · liquid_glass_widgets — **새 의존성 없음(`pubspec.yaml` 불변), 새 화면 없음, 새 API 호출 없음.**

**Spec:** `docs/superpowers/specs/2026-09-24-record-media-design.md` — 이 계획은 4절 "SOLID 점검 결과와 정리(④-0)"의 4.2 앱 표(A1~A13)와 13절 첫 줄(④-0 검증 기준), 14절의 "④-0 SOLID 정리 — 앱"이다. A4 의 사진 선택기·마이크 프로바이더와 A6 이미지 로더는 패키지가 들어오는 ④-2·④-3 으로 미룬다(이 계획의 제약이 "새 의존성 없음"이라서다 — 결정 기록 007). 실행자는 설계 문서와 함께 `app/CLAUDE.md`, `_docs/harness.md`, `_docs/decisions/007-record-media.md`(백엔드 절 — 같은 서브 프로젝트의 결정)를 읽는다.

**계획의 위치:** ④의 구현 계획 다섯 가운데 둘째다. ④-0 백엔드(완료, main 189c9bd) · **④-0 앱(이 문서)** → ④-1 백엔드(media 스포크·기록) → ④-2 앱 → ④-3 영상·음성. ④-2 는 이 계획이 만든 이름(`VisitStatus`·`AfterComplete`·`ViewModeController`·`_HomeTab` 목록·`AppErrorRetry`·`clipboardProvider`·`UploadClient`·`feature_imports_test`)에 기댄다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 앱 명령은 `app/`에서 돌린다.
- 작업 브랜치는 `feat/record-4-0-app-solid`다(`main` `189c9bd`에서 딴다. 이 계획서 커밋이 첫 커밋이다). `main`에서 직접 작업하지 않는다.
- **사용자가 작업 단위 커밋을 허용했다(2026-09-22 이후 계속).** 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.**
- **이 계획은 새 의존성·새 화면·새 API 호출·서버 필드 변경을 하지 않는다.** `pubspec.yaml`·`pubspec.lock`은 건드리지 않는다. 골든 이미지(`*.png`)는 하나도 바뀌지 않는다 — 골든이 실패하면 코드가 계획과 다른 것이니 `--update-goldens`를 돌리지 말고 멈추고 보고한다.
- 계획서의 코드 블록은 그대로 옮긴다. 새 파일은 전문이고, 수정 파일은 diff 다. 이름 바꾼 파일은 `git mv` 뒤 diff 다. diff 가 적용되지 않으면 멈추고 보고한다 — 손으로 "비슷하게" 고치지 않는다.
- **`dart format`은 새로 만든 파일에만 돌린다.** 기존 파일은 diff 그대로 두고 재포맷하지 않는다(`dart format lib/`처럼 폴더째 돌리면 무관한 파일 수십 개가 바뀐다 — 참조 구현에서 실제로 일어났다).
- **변이 검사는 편집으로 넣고 편집으로 되돌린다.** `git checkout -- <파일>`로 되돌리지 않는다(아직 커밋하지 않은 구현이 함께 사라진다 — ④-0 백엔드에서 실제로 일어났다).
- 비밀값·토큰·고객 개인정보를 로그에 남기지 않는다. `print`·`debugPrint`·dio `LogInterceptor`를 쓰지 않는다.
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (`app/CLAUDE.md` 그대로 — 이 계획이 문서에 더하는 규칙 포함)
- 웹뷰 금지. `lib/features`에서 dio·secure storage·`MethodChannel`·`Clipboard`를 직접 import 하지 않는다. `liquid_glass_widgets`는 `lib/design/bridge/` 안에서만.
- 기능 폴더 안은 `screens/`·`state/`·`api/` 세 층뿐이다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
- **기능 폴더 사이의 import 는 방향이 하나다**(작업 3 이 세우는 규칙, `test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용, `home`은 조립 껍데기(아무도 import 하지 않는다), `visit → customer`만 허용. 여러 기능이 함께 쓰는 것은 `lib/core/`에 둔다.
- **화면은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다**(작업 1). `auth/state/shop_selection.dart`의 파생 프로바이더 다섯만 watch 한다.
- **서버의 상태 문자열은 `fromJson`에서 enum 으로 한 번만 바꾼다**(작업 4). 화면의 `switch`는 `_ =>` 폴백 없이 완전 열거한다.
- **플러그인은 `lib/core/proxy/`의 프로바이더로만 부른다**(작업 10). 테스트는 프로바이더를 override 한다.

검증 명령 (`app/`에서)
- 정적 분석: `flutter analyze` → `No issues found!`(info 도 0)
- 테스트: `flutter test --timeout 30s` — 시작 502 → 끝 542. 골든 포함. 실패한 골든은 `test/**/failures/`에 png 를 남기니 커밋 전에 `git status`로 그 폴더가 없는지 본다.
- 구조 테스트만: `flutter test test/design/feature_imports_test.dart test/core/router/app_router_test.dart`
- 파일 몇 개만: `flutter test --timeout 30s <경로들>`
- 참조 브랜치와 대조(선택, 마지막에): `git diff ref/record-4-0-app -- app _docs` 가 비어 있어야 한다. 비어 있지 않으면 어느 diff 를 잘못 적용했는지 찾는다.

## 이 계획에서 새로 정한 것

설계 4.2 절과 다른 것은 결정 기록 007(작업 11)에 적는다. 요약:
- 완료 후속 행동은 `AfterNothing`·`AfterNextReservation` 둘(`record`는 기록 화면이 생기는 ④-2 에서 셋째로). 모르는 상태는 `VisitStatus.unknown`이고 시간표 자리는 차지한다.
- `PrefsStore`에 `remove(key)`는 없다(쓰는 곳이 없다). `clear()`는 마지막 매장만 지운다.
- 플러그인 프로바이더는 클립보드만. 사진 선택기·마이크(A4)와 이미지 로더(A6)는 ④-2·④-3.
- `UploadClient`는 송신 타임아웃을 두지 않는다(바이트 전체에 걸려 큰 영상이 끊긴다). 오류는 `ApiException`.
- 홈 탭 목록은 비공개 `_HomeTab`. 라우터 가드는 목록이 아니라 규칙 하나 — 옛 `_isShopScoped` 분기는 매장이 하나면 세션이 자동으로 고르므로 닿을 수 없는 코드였고(변이 검사에서 드러났다) 지웠다. 예외는 `accountRoutes` 둘.
- A9 의 ③(`core/plugs/` 자리)·④(`ShopDataChanged` 신호)는 지금 필요 없다 — `customer → visit` import 는 시각 도우미뿐이라 `core/time`으로 옮기니 사라졌고, `visit → customer` 무효화는 허용 방향이다. 구조 테스트는 `test/design/`에 둔다.
- 폼 규칙은 Notifier 가 아니라 순수 객체 `VisitFormDraft`(폼은 화면 인스턴스마다 하나라 프로바이더로 공유할 이유가 없다).
- 세션 파생 프로바이더는 셋이 아니라 다섯(`shopCountProvider`·`currentUserIdProvider` 추가).

## Review Focus

설계가 말하지만 어느 작업의 테스트도 직접 겨누지 않던 입력 다섯. 각 줄의 테스트를 해당 작업에 넣었다.
1. **서버가 앱이 모르는 상태 문자열을 보낼 때** — 화면이 방문을 숨기거나 죽지 않고 "알 수 없음"으로 보이며 시간표 자리는 차지해야 한다 → 작업 4 `test/features/visit/api/visit_status_test.dart::모르는 상태는 unknown 이고 화면은 "알 수 없음"으로 보인다`·`취소·노쇼만 빈 시간이다`.
2. **기기에 남은 보기 방식 이름이 옛 버전 값일 때** — 기본값으로 시작해야 한다(죽지 않는다) → 작업 5 `test/core/storage/view_mode_controller_test.dart::저장된 이름으로 시작하고, 모르는 이름이면 기본값이다`.
3. **"지난번처럼" 응답이 늦게 도착해 사용자가 이미 손댄 폼을 덮는 경우** — 옛 응답과 손댄 뒤의 응답은 버려야 한다 → 작업 8 `test/features/visit/state/visit_form_draft_test.dart::늦게 온 옛 응답은 버린다 — 순서 번호가 최신일 때만 채운다`·`응답을 기다리는 사이 손댔으면 채우지 않는다`.
4. **라우터에 새 경로를 더하고 매장 가드를 잊은 경우** — 매장 선택 없이 열리면 안 된다 → 작업 6 `test/core/router/app_router_test.dart::계정 경로 밖의 모든 경로는 매장 선택이 없으면 매장 선택으로 밀려난다`(라우터의 `GoRoute` 전수).
5. **서명 URL 업로드에 액세스 토큰이 붙거나 저장소가 거절하는 경우** — 인증 헤더 없이 보내고, 거절은 `ApiException`으로 한 번만 → 작업 10 `test/core/proxy/upload_client_test.dart::PUT 은 인증 헤더 없이 바디·content-type·길이를 보내고 진행률을 알린다`·`저장소가 거절하면 ApiException 으로 던지고 다시 보내지 않는다`.

---
### Task 1: 세션 파생 프로바이더 — 화면은 `selectedShopId`·`isOwner`·`shopName`·`shopCount`·`currentUserId`만 `select`로 watch 한다 (A2)

**Files:**
- Create: `app/lib/features/auth/state/shop_selection.dart`
- Modify: `app/lib/features/customer/screens/customer_edit_screen.dart`
- Modify: `app/lib/features/customer/screens/customer_list_tab.dart`
- Modify: `app/lib/features/customer/screens/pet_detail_screen.dart`
- Modify: `app/lib/features/customer/screens/pet_form_screen.dart`
- Modify: `app/lib/features/customer/screens/register_customer_screen.dart`
- Modify: `app/lib/features/home/screens/home_shell.dart`
- Modify: `app/lib/features/shop/screens/members_screen.dart`
- Modify: `app/lib/features/shop/screens/menu_settings_screen.dart`
- Modify: `app/lib/features/shop/screens/schedule_settings_screen.dart`
- Modify: `app/lib/features/shop/screens/settings_screen.dart`
- Modify: `app/lib/features/shop/screens/shop_settings_screen.dart`
- Modify: `app/lib/features/visit/screens/calendar_tab.dart`
- Modify: `app/lib/features/visit/screens/day_screen.dart`
- Modify: `app/lib/features/visit/screens/draft_screen.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_detail_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_edit_screen.dart`
- Create: `app/test/features/auth/state/shop_selection_test.dart`

**Interfaces:**
- Consumes: `features/auth/state/session_controller.dart`의 `sessionControllerProvider`(`AsyncValue<SessionState>`; `SignedIn(me, selectedShopId, selectedShop)`), `Me.shops: List<ShopMembership>`(`shopId`·`shopName`·`isOwner`), `Me.id`.
- Produces: `features/auth/state/shop_selection.dart` — `selectedShopIdProvider: Provider<int?>`, `isOwnerProvider: Provider<bool>`, `shopNameProvider: Provider<String>`(없으면 `''`), `shopCountProvider: Provider<int>`, `currentUserIdProvider: Provider<int?>`. 각각 `ref.watch(sessionControllerProvider.select(...))`로 값만 뽑는다 — 값이 같으면 다시 알리지 않는다. 화면 17곳의 `ref.watch(sessionControllerProvider)`와 복붙된 `_shopId` getter 가 이 프로바이더로 바뀐다(`_shopId` getter 는 `ref.read(selectedShopIdProvider)`).

감사 결과(설계 4.2 A2): 화면 14곳이 세션 컨트롤러 전체를 watch 해(`.select` 0건) `reloadMe`마다 화면 전체가 재빌드되고, `_shopId` getter 가 15개 화면에 복붙돼 있었다. 이 작업은 파생 프로바이더 다섯을 두고 화면이 그것만 watch 하게 한다. **설계와 다른 점**(결정 기록 007): 셋이 아니라 다섯 — `shopCountProvider`(설정 화면의 "매장 바꾸기" 줄)와 `currentUserIdProvider`(멤버 화면의 "나")가 더 필요했다. 화면 구성·문구·API 호출은 바뀌지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/auth/state/shop_selection_test.dart`:

```dart
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/shop_selection.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me({List<ShopMembership> shops = const [], String displayName = '민석'}) =>
    Me(
      id: 7,
      displayName: displayName,
      profileImageUrl: null,
      identities: const ['apple'],
      shops: shops,
    );

Future<ProviderContainer> _signedIn(FakeSessionGateway gateway) async {
  final container = ProviderContainer(
    overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
  );
  addTearDown(container.dispose);
  await container.read(sessionControllerProvider.future);
  return container;
}

void main() {
  test('매장이 하나면 그 매장의 ID·이름·역할·수를 준다', () async {
    final container = await _signedIn(
      FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]),
    );
    expect(container.read(selectedShopIdProvider), 1);
    expect(container.read(shopNameProvider), 'A매장');
    expect(container.read(isOwnerProvider), isTrue);
    expect(container.read(shopCountProvider), 1);
    expect(container.read(currentUserIdProvider), 7);
  });

  test('로그아웃이면 매장 값이 비어 있다', () async {
    final container = await _signedIn(FakeSessionGateway()..meOnRestore = null);
    expect(container.read(selectedShopIdProvider), isNull);
    expect(container.read(shopNameProvider), '');
    expect(container.read(isOwnerProvider), isFalse);
    expect(container.read(shopCountProvider), 0);
    expect(container.read(currentUserIdProvider), isNull);
  });

  test('직원 매장을 고르면 사장이 아니다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(shops: [_ownerA, _staffB])
      ..lastShopId = 2;
    final container = await _signedIn(gateway);
    expect(container.read(selectedShopIdProvider), 2);
    expect(container.read(isOwnerProvider), isFalse);
    expect(container.read(shopNameProvider), 'B매장');
  });

  test('Me 가 갱신돼도 값이 같으면 파생 프로바이더는 다시 알리지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = await _signedIn(gateway);
    var shopIdNotified = 0;
    var nameNotified = 0;
    container.listen(selectedShopIdProvider, (_, _) => shopIdNotified++);
    container.listen(shopNameProvider, (_, _) => nameNotified++);

    // 표시 이름만 바뀐 새 Me — 매장 값은 그대로다.
    gateway.meOnRefresh = _me(shops: [_ownerA], displayName: '민석2');
    await container.read(sessionControllerProvider.notifier).reloadMe();
    // 파생 프로바이더의 알림은 다음 이벤트 루프에서 전달된다.
    await container.pump();

    expect(shopIdNotified, 0);
    expect(nameNotified, 0);
  });

  test('매장 이름이 바뀌면 이름 프로바이더만 알린다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = await _signedIn(gateway);
    var shopIdNotified = 0;
    var nameNotified = 0;
    container.listen(selectedShopIdProvider, (_, _) => shopIdNotified++);
    container.listen(shopNameProvider, (_, _) => nameNotified++);

    gateway.meOnRefresh = _me(
      shops: const [
        ShopMembership(shopId: 1, shopName: 'A매장(이전)', role: 'owner'),
      ],
    );
    await container.read(sessionControllerProvider.notifier).reloadMe();
    // 파생 프로바이더의 알림은 다음 이벤트 루프에서 전달된다.
    await container.pump();

    expect(shopIdNotified, 0);
    expect(nameNotified, 1);
    expect(container.read(shopNameProvider), 'A매장(이전)');
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/features/auth/state/shop_selection_test.dart`
Expected: 컴파일 실패 — `Error: Error when reading 'lib/features/auth/state/shop_selection.dart'`.

- [ ] **Step 3: 구현한다**

`app/lib/features/auth/state/shop_selection.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'session.dart';
import 'session_controller.dart';

/// 세션에서 파생한 매장 선택 값들.
///
/// 화면은 세션 전체(`sessionControllerProvider`)가 아니라 여기 있는 값만 watch 한다.
/// `select`로 좁혀 두었으므로 `reloadMe`로 `Me` 객체가 통째로 바뀌어도 값이 같으면
/// 화면을 다시 그리지 않는다(인터페이스 분리 — 화면은 필요한 것만 안다).
///
/// 로그아웃·미선택이면 `selectedShopIdProvider`가 null 이고 나머지는 빈값이다.

/// 지금 고른 매장 ID. 매장 범위 화면은 이것으로 프로바이더 키를 만든다.
final selectedShopIdProvider = Provider<int?>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.selectedShopId : null;
    }),
  ),
);

/// 고른 매장에서 사장인가. 직원에게 숨기는 화면·버튼이 본다(보안 경계는 서버 403).
final isOwnerProvider = Provider<bool>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn && (value.selectedShop?.isOwner ?? false);
    }),
  ),
);

/// 고른 매장의 이름. 없으면 빈 문자열.
final shopNameProvider = Provider<String>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.selectedShop?.shopName ?? '' : '';
    }),
  ),
);

/// 소속 매장 수. 설정 화면이 "매장 바꾸기" 줄을 보일지 정한다.
final shopCountProvider = Provider<int>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.me.shops.length : 0;
    }),
  ),
);

/// 로그인한 유저의 ID. 멤버 목록에서 "나"를 표시할 때 쓴다.
final currentUserIdProvider = Provider<int?>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.me.id : null;
    }),
  ),
);
```

`app/lib/features/customer/screens/customer_edit_screen.dart`:

```diff
@@ -11,8 +11,7 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../api/customer_models.dart';
 import '../state/customer_commands.dart';
 import '../state/customer_providers.dart';
@@ -33,10 +32,7 @@ class _CustomerEditScreenState extends ConsumerState<CustomerEditScreen> {
   bool _busy = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   /// 쓰기 하나를 돌린다(연타 방지, 실패 문구). 성공하면 true.
   Future<bool> _run(Future<void> Function(int shopId) action) async {
@@ -107,9 +103,7 @@ class _CustomerEditScreenState extends ConsumerState<CustomerEditScreen> {
   @override
   Widget build(BuildContext context) {
     final shopId = _shopId;
-    final session = ref.watch(sessionControllerProvider).value;
-    final isOwner =
-        session is SignedIn && (session.selectedShop?.isOwner ?? false);
+    final isOwner = ref.watch(isOwnerProvider);
     final key = shopId == null
         ? null
         : (shopId: shopId, customerId: widget.customerId);
```

`app/lib/features/customer/screens/customer_list_tab.dart`:

```diff
@@ -11,8 +11,7 @@ import '../../../design/widgets/app_choice_chip.dart';
 import '../../../design/widgets/app_icon_toggle.dart';
 import '../../../design/widgets/app_segment.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../state/customer_list_controller.dart';
 import '../state/customer_view_mode.dart';
 import '../state/search_debouncer.dart';
@@ -67,8 +66,7 @@ class _CustomerListTabState extends ConsumerState<CustomerListTab> {
   }
 
   CustomerListQuery? get _query {
-    final session = ref.read(sessionControllerProvider).value;
-    final shopId = session is SignedIn ? session.selectedShopId : null;
+    final shopId = ref.read(selectedShopIdProvider);
     if (shopId == null) return null;
     return (shopId: shopId, q: _q, sort: _sort, includePassed: _includePassed);
   }
@@ -86,7 +84,7 @@ class _CustomerListTabState extends ConsumerState<CustomerListTab> {
 
   @override
   Widget build(BuildContext context) {
-    ref.watch(sessionControllerProvider);
+    ref.watch(selectedShopIdProvider);   // 매장이 바뀌면 다시 그린다
     final query = _query;
     final mode =
         ref.watch(customerViewModeProvider).value ?? CustomerViewMode.list;
```

`app/lib/features/customer/screens/pet_detail_screen.dart`:

```diff
@@ -16,8 +16,7 @@ import '../../../design/widgets/app_segment.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../visit/api/visit_models.dart';
 import '../../visit/screens/visit_labels.dart';
 import '../api/customer_models.dart';
@@ -42,10 +41,7 @@ class _PetDetailScreenState extends ConsumerState<PetDetailScreen> {
   bool _busy = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   Future<void> _openActions(PetDetail detail) async {
     final action = await AppSheet.show<String>(
@@ -394,8 +390,7 @@ class _OwnerTab extends ConsumerWidget {
 
   @override
   Widget build(BuildContext context, WidgetRef ref) {
-    final session = ref.watch(sessionControllerProvider).value;
-    final shopId = session is SignedIn ? session.selectedShopId : null;
+    final shopId = ref.watch(selectedShopIdProvider);
     if (shopId == null) return const SizedBox.shrink();
     final key = (shopId: shopId, customerId: customerId);
     return ref
```

`app/lib/features/customer/screens/pet_form_screen.dart`:

```diff
@@ -10,8 +10,7 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../home/state/today_provider.dart';
 import '../api/customer_models.dart';
 import '../state/customer_commands.dart';
@@ -37,10 +36,7 @@ class _PetFormScreenState extends ConsumerState<PetFormScreen> {
   bool _busy = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   Future<void> _submit(PetFields fields) async {
     final shopId = _shopId;
```

`app/lib/features/customer/screens/register_customer_screen.dart`:

```diff
@@ -13,8 +13,7 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../home/state/today_provider.dart';
 import '../api/customer_models.dart';
 import '../state/customer_commands.dart';
@@ -61,10 +60,7 @@ class _RegisterCustomerScreenState
   bool _busy = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   String get _digits => phoneDigits(_phone.text);
```

`app/lib/features/home/screens/home_shell.dart`:

```diff
@@ -12,8 +12,7 @@ import '../../../design/widgets/app_glass_bar.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../customer/screens/customer_list_tab.dart';
 import '../../visit/api/visit_models.dart';
 import '../../visit/screens/calendar_tab.dart';
@@ -69,9 +68,7 @@ class _HomeShellState extends ConsumerState<HomeShell> {
   @override
   Widget build(BuildContext context) {
     final today = ref.watch(todayProvider);
-    final session = ref.watch(sessionControllerProvider).value;
-    final shopName =
-        session is SignedIn ? session.selectedShop?.shopName ?? '' : '';
+    final shopName = ref.watch(shopNameProvider);
 
     return Scaffold(
       key: ScreenKeys.home,
```

`app/lib/features/shop/screens/members_screen.dart`:

```diff
@@ -15,8 +15,7 @@ import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../api/shop_api.dart';
 import '../state/members_controller.dart';
 
@@ -32,10 +31,7 @@ class MembersScreen extends ConsumerStatefulWidget {
 class _MembersScreenState extends ConsumerState<MembersScreen> {
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   Future<void> _createInvite() async {
     final shopId = _shopId;
@@ -172,10 +168,8 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
   @override
   Widget build(BuildContext context) {
     final shopId = _shopId;
-    final session = ref.watch(sessionControllerProvider).value;
-    final isOwner =
-        session is SignedIn && (session.selectedShop?.isOwner ?? false);
-    final myUserId = session is SignedIn ? session.me.id : null;
+    final isOwner = ref.watch(isOwnerProvider);
+    final myUserId = ref.watch(currentUserIdProvider);
     final members = shopId == null
         ? const AsyncValue<List<ShopMember>>.data(<ShopMember>[])
         : ref.watch(membersControllerProvider(shopId));
```

`app/lib/features/shop/screens/menu_settings_screen.dart`:

```diff
@@ -15,8 +15,7 @@ import '../../../design/widgets/app_choice_chip.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../visit/api/visit_models.dart';
 import '../../visit/state/visit_commands.dart';
 import '../../visit/state/visit_form_rules.dart';
@@ -35,10 +34,7 @@ class _MenuSettingsScreenState extends ConsumerState<MenuSettingsScreen> {
   bool _busy = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   /// 쓰기 하나를 돌린다. 도는 동안 다른 쓰기를 막고, 실패하면 문구를 보인다.
   Future<void> _run(Future<void> Function() action) async {
```

`app/lib/features/shop/screens/schedule_settings_screen.dart`:

```diff
@@ -15,8 +15,7 @@ import '../../../design/widgets/app_choice_chip.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../home/state/today_provider.dart';
 import '../../visit/api/visit_models.dart';
 import '../../visit/screens/visit_labels.dart';
@@ -52,10 +51,7 @@ class _ScheduleSettingsScreenState
   String? _successText;
   String? _dateError;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   @override
   void dispose() {
```

`app/lib/features/shop/screens/settings_screen.dart`:

```diff
@@ -11,8 +11,7 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_chip.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 
 /// 설정 허브. 매장/다른 매장/계정 세 묶음으로 이동한다.
 class SettingsScreen extends ConsumerWidget {
@@ -20,9 +19,10 @@ class SettingsScreen extends ConsumerWidget {
 
   @override
   Widget build(BuildContext context, WidgetRef ref) {
-    final session = ref.watch(sessionControllerProvider).value;
-    final shop = session is SignedIn ? session.selectedShop : null;
-    final shopCount = session is SignedIn ? session.me.shops.length : 0;
+    final shopId = ref.watch(selectedShopIdProvider);
+    final shopName = ref.watch(shopNameProvider);
+    final isOwner = ref.watch(isOwnerProvider);
+    final shopCount = ref.watch(shopCountProvider);
 
     return Scaffold(
       key: ScreenKeys.settings,
@@ -38,13 +38,13 @@ class SettingsScreen extends ConsumerWidget {
                 child: AppBackButton(),
               ),
               const SizedBox(height: AppSpacing.lg),
-              if (shop != null) ...[
+              if (shopId != null) ...[
                 Row(
                   mainAxisAlignment: MainAxisAlignment.spaceBetween,
                   children: [
-                    Text(shop.shopName, style: AppTypography.titleKo),
+                    Text(shopName, style: AppTypography.titleKo),
                     AppChip(
-                      label: shop.isOwner
+                      label: isOwner
                           ? AppStrings.roleOwner
                           : AppStrings.roleStaff,
                     ),
@@ -62,12 +62,12 @@ class SettingsScreen extends ConsumerWidget {
                 onTap: () => context.push('/settings/shop'),
               ),
               // 일정·메뉴는 사장만 바꾼다(보안 경계는 서버 403) — 직원에게는 보이지 않는다.
-              if (shop?.isOwner ?? false)
+              if (isOwner)
                 _SettingsRow(
                   label: AppStrings.settingsSchedule,
                   onTap: () => context.push('/settings/schedule'),
                 ),
-              if (shop?.isOwner ?? false)
+              if (isOwner)
                 _SettingsRow(
                   label: AppStrings.settingsMenus,
                   onTap: () => context.push('/settings/menus'),
```

`app/lib/features/shop/screens/shop_settings_screen.dart`:

```diff
@@ -9,8 +9,7 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../api/shop_api.dart';
 import '../state/shop_settings_controller.dart';
 
@@ -34,10 +33,7 @@ class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
   String? _errorText;
   String? _successText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   void _initFields(ShopSettings settings) {
     if (_fieldsInitialized) return;
@@ -96,9 +92,7 @@ class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
   @override
   Widget build(BuildContext context) {
     final shopId = _shopId;
-    final session = ref.watch(sessionControllerProvider).value;
-    final isOwner =
-        session is SignedIn && (session.selectedShop?.isOwner ?? false);
+    final isOwner = ref.watch(isOwnerProvider);
     final settingsAsync = shopId == null
         ? const AsyncValue<ShopSettings>.loading()
         : ref.watch(shopSettingsControllerProvider(shopId));
```

`app/lib/features/visit/screens/calendar_tab.dart`:

```diff
@@ -15,8 +15,7 @@ import '../../../design/widgets/app_glass_card.dart';
 import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../home/state/today_provider.dart';
 import '../api/visit_models.dart';
 import '../state/calendar_selection.dart';
@@ -44,11 +43,6 @@ class _CalendarTabState extends ConsumerState<CalendarTab> {
     return DateTime(selected.year, selected.month);
   }
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
-
   /// 달을 옮기면 그달에 오늘이 있으면 오늘을, 없으면 1일을 고른다.
   void _moveMonth(int delta) {
     final current = ref.read(selectedDateProvider);
@@ -67,8 +61,7 @@ class _CalendarTabState extends ConsumerState<CalendarTab> {
 
   @override
   Widget build(BuildContext context) {
-    ref.watch(sessionControllerProvider);
-    final shopId = _shopId;
+    final shopId = ref.watch(selectedShopIdProvider);
     final selected = ref.watch(selectedDateProvider);
     if (shopId == null) return const SizedBox.shrink();
     final monthKey = monthKeyOf(shopId, _month);
```

`app/lib/features/visit/screens/day_screen.dart`:

```diff
@@ -21,8 +21,7 @@ import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../api/visit_models.dart';
 import '../state/day_layout.dart';
 import '../state/day_view_mode.dart';
@@ -52,10 +51,7 @@ class _DayScreenState extends ConsumerState<DayScreen> {
   bool _asking = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   Future<void> _act(DayGroup group, String action) async {
     final shopId = _shopId;
@@ -155,9 +151,7 @@ class _DayScreenState extends ConsumerState<DayScreen> {
         : ref.watch(dayVisitsProvider(key));
     final mode = ref.watch(dayViewModeProvider).value ?? DayViewMode.list;
     final data = day.value;
-    final session = ref.watch(sessionControllerProvider).value;
-    final isOwner =
-        session is SignedIn && (session.selectedShop?.isOwner ?? false);
+    final isOwner = ref.watch(isOwnerProvider);
     return Scaffold(
       key: ScreenKeys.day,
       floatingActionButton: AppFab(
```

`app/lib/features/visit/screens/draft_screen.dart`:

```diff
@@ -13,8 +13,7 @@ import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../customer/state/customer_input.dart';
 import '../api/visit_models.dart';
 import '../state/visit_prefill.dart';
@@ -42,10 +41,7 @@ class _DraftScreenState extends ConsumerState<DraftScreen> {
   bool _expanded = false;
   bool _continuing = false;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   /// 예약 ②(보호자가 있으면 바로, 없으면 ① 뒤)를 초안으로 채워 연다. 저장한
   /// 날짜가 돌아오면 이 화면도 그 날짜로 닫힌다.
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -17,8 +17,7 @@ import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_snack_bar.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../customer/api/customer_models.dart';
 import '../../customer/state/customer_input.dart';
 import '../../customer/state/customer_list_controller.dart';
@@ -61,10 +60,7 @@ class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
   bool _busy = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   void _backToSearch() => setState(() {
     _customerId = null;
```

`app/lib/features/visit/screens/visit_detail_screen.dart`:

```diff
@@ -15,8 +15,7 @@ import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../../customer/state/customer_input.dart';
 import '../api/visit_models.dart';
 import '../state/visit_commands.dart';
@@ -47,10 +46,7 @@ class _VisitDetailScreenState extends ConsumerState<VisitDetailScreen> {
   bool _asking = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   /// 앵커(이 방문) + 같은 묶음에서 상태가 같은 형제. 서버의 `group`은 자기를
   /// 뺀 형제만 주므로 앵커를 먼저 넣는다.
```

`app/lib/features/visit/screens/visit_edit_screen.dart`:

```diff
@@ -12,8 +12,7 @@ import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../l10n/app_strings.dart';
-import '../../auth/state/session.dart';
-import '../../auth/state/session_controller.dart';
+import '../../auth/state/shop_selection.dart';
 import '../api/visit_models.dart';
 import '../state/visit_commands.dart';
 import '../state/visit_providers.dart';
@@ -36,10 +35,7 @@ class _VisitEditScreenState extends ConsumerState<VisitEditScreen> {
   bool _busy = false;
   String? _errorText;
 
-  int? get _shopId {
-    final session = ref.read(sessionControllerProvider).value;
-    return session is SignedIn ? session.selectedShopId : null;
-  }
+  int? get _shopId => ref.read(selectedShopIdProvider);
 
   /// 같이 옮길 수 있는 묶음의 다른 예약(예약됨만 옮길 수 있다). 서버의
   /// group 은 이미 자기를 뺀 형제만 준다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/features/auth/state/shop_selection_test.dart` → 5 passed

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 507 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `shop_selection.dart`의 `isOwnerProvider`가 `return value is SignedIn && (value.selectedShop?.isOwner ?? false);` 대신 `return false;` → `매장이 하나면 그 매장의 ID·이름·역할·수를 준다` 실패.
- `shopNameProvider`의 `.select` 안에서 `value.selectedShop?.shopName ?? ''`를 `value.me.shops.first.shopName`으로 → `직원 매장을 고르면 사장이 아니다`(이름이 A 매장으로 나온다) 또는 `매장 이름이 바뀌면 이름 프로바이더만 알린다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 세션 파생 프로바이더 — 화면은 selectedShopId·isOwner·shopName·shopCount·currentUserId 만 select 로 watch 한다(A2)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 공유 상태의 자리를 바로잡는다 — `today_provider`는 `core/time`, `runShopScoped`는 `auth/state`, 메뉴·일정 설정 화면과 `schedule_input`은 소유자인 `visit`로 (A9 ①·②)

**Files:**
- Rename: `app/lib/features/home/state/today_provider.dart` → `app/lib/core/time/today_provider.dart`
- Rename: `app/lib/features/shop/state/shop_errors.dart` → `app/lib/features/auth/state/shop_scoped.dart`
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/lib/features/customer/screens/pet_form_screen.dart`
- Modify: `app/lib/features/customer/screens/register_customer_screen.dart`
- Modify: `app/lib/features/customer/state/customer_commands.dart`
- Modify: `app/lib/features/customer/state/customer_list_controller.dart`
- Modify: `app/lib/features/customer/state/customer_providers.dart`
- Modify: `app/lib/features/home/screens/home_shell.dart`
- Modify: `app/lib/features/shop/state/members_controller.dart`
- Modify: `app/lib/features/shop/state/shop_settings_controller.dart`
- Modify: `app/lib/features/visit/screens/calendar_tab.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Rename: `app/lib/features/shop/screens/menu_settings_screen.dart` → `app/lib/features/visit/screens/settings/menu_settings_screen.dart`
- Rename: `app/lib/features/shop/screens/schedule_settings_screen.dart` → `app/lib/features/visit/screens/settings/schedule_settings_screen.dart`
- Modify: `app/lib/features/visit/state/calendar_selection.dart`
- Rename: `app/lib/features/shop/state/schedule_input.dart` → `app/lib/features/visit/state/schedule_input.dart`
- Modify: `app/lib/features/visit/state/visit_commands.dart`
- Modify: `app/lib/features/visit/state/visit_providers.dart`
- Modify: `app/test/design/glass_boundary_test.dart`
- Modify: `app/test/features/customer/screens/pet_form_screen_test.dart`
- Modify: `app/test/features/customer/screens/register_customer_screen_test.dart`
- Modify: `app/test/features/home/screens/home_shell_golden_test.dart`
- Modify: `app/test/features/home/screens/home_shell_test.dart`
- Modify: `app/test/features/visit/screens/calendar_tab_test.dart`
- Modify: `app/test/features/visit/screens/day_screen_test.dart`
- Modify: `app/test/features/visit/screens/draft_screen_test.dart`
- Modify: `app/test/features/visit/screens/register_visit_screen_test.dart`
- Rename: `app/test/features/shop/screens/menu_settings_screen_test.dart` → `app/test/features/visit/screens/settings/menu_settings_screen_test.dart`
- Rename: `app/test/features/shop/screens/schedule_settings_screen_test.dart` → `app/test/features/visit/screens/settings/schedule_settings_screen_test.dart`
- Modify: `app/test/features/visit/screens/shared_text_gate_test.dart`
- Modify: `app/test/features/visit/screens/visit_detail_screen_test.dart`
- Modify: `app/test/features/visit/screens/visit_edit_screen_test.dart`
- Rename: `app/test/features/shop/state/schedule_input_test.dart` → `app/test/features/visit/state/schedule_input_test.dart`

**Interfaces:**
- Consumes: `features/home/state/today_provider.dart`(`todayProvider`), `features/shop/state/shop_errors.dart`(`runShopScoped`), `features/shop/screens/{menu,schedule}_settings_screen.dart`, `features/shop/state/schedule_input.dart`와 그 테스트 셋.
- Produces: `lib/core/time/today_provider.dart`(`todayProvider: Provider<DateTime>` — 내용 그대로), `lib/features/auth/state/shop_scoped.dart`(`Future<T> runShopScoped<T>(Ref ref, Future<T> Function() action)` — 내용 그대로), `lib/features/visit/screens/settings/menu_settings_screen.dart`·`schedule_settings_screen.dart`, `lib/features/visit/state/schedule_input.dart`. 옮긴 파일의 import 경로만 바뀐다. 라우터의 두 설정 경로(`/settings/menus`·`/settings/schedule`)는 그대로다.

감사 결과(설계 4.2 A9 ①·②): 기능 폴더끼리 서로 import 했다 — `shop → visit`(메뉴·일정 설정 화면이 visit 의 API·상태를 쓴다), 여러 기능 → `home`(오늘 날짜), 여러 기능 → `shop`(`runShopScoped`). 이 작업은 파일을 소유자에게 옮긴다. 옮기기만 하고 내용은 바꾸지 않는다(이름 바꾼 파일의 diff 는 import 경로뿐이다). 작업 3 의 구조 테스트가 이 자리를 고정한다. 이 작업의 판별은 컴파일이다 — 옛 경로를 import 하는 곳이 남으면 `flutter analyze`가 잡는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/glass_boundary_test.dart`:

```diff
@@ -25,8 +25,8 @@ void main() {
       'lib/features/visit/screens/visit_actions.dart',
       'lib/features/visit/screens/day_screen.dart',
       'lib/features/visit/screens/draft_screen.dart',
-      'lib/features/shop/screens/schedule_settings_screen.dart',
-      'lib/features/shop/screens/menu_settings_screen.dart',
+      'lib/features/visit/screens/settings/schedule_settings_screen.dart',
+      'lib/features/visit/screens/settings/menu_settings_screen.dart',
     ];
     final violations = [
       for (final path in scrollScreens)
```

`app/test/features/customer/screens/pet_form_screen_test.dart`:

```diff
@@ -4,7 +4,7 @@ import 'dart:convert';
 import 'package:chagocnote/core/router/app_router.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/customer/screens/register_customer_screen_test.dart`:

```diff
@@ -4,7 +4,7 @@ import 'dart:convert';
 import 'package:chagocnote/core/router/app_router.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/home/screens/home_shell_golden_test.dart`:

```diff
@@ -1,5 +1,5 @@
 import 'package:chagocnote/core/router/screen_keys.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/home/screens/home_shell_test.dart`:

```diff
@@ -1,7 +1,7 @@
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_big_date.dart';
 import 'package:chagocnote/features/customer/screens/customer_list_tab.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/features/visit/screens/calendar_tab.dart';
 import 'package:chagocnote/features/visit/state/calendar_selection.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
```

`app/test/features/visit/screens/calendar_tab_test.dart`:

```diff
@@ -2,7 +2,7 @@ import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/design/widgets/app_dashed_tile.dart';
 import 'package:chagocnote/design/widgets/app_photo_tile.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/features/visit/state/calendar_selection.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
```

`app/test/features/visit/screens/day_screen_test.dart`:

```diff
@@ -2,7 +2,7 @@ import 'dart:async';
 
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/visit/screens/draft_screen_test.dart`:

```diff
@@ -3,7 +3,7 @@ import 'dart:async';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/design/widgets/app_chip.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/visit/screens/register_visit_screen_test.dart`:

```diff
@@ -4,7 +4,7 @@ import 'package:chagocnote/core/router/app_router.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/tokens/app_colors.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/features/visit/api/visit_models.dart';
 import 'package:chagocnote/features/visit/state/visit_prefill.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
```

`app/test/features/shop/screens/menu_settings_screen_test.dart` → `app/test/features/visit/screens/settings/menu_settings_screen_test.dart` 로 옮긴다(`git mv`). 옮긴 뒤 diff:

```diff
@@ -1,14 +1,14 @@
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
 
-import '../../../support/customer_test_app.dart';
-import '../../../support/fake_http_client_adapter.dart';
-import '../../../support/visit_fixtures.dart';
-import '../../../support/visit_test_backend.dart';
+import '../../../../support/customer_test_app.dart';
+import '../../../../support/fake_http_client_adapter.dart';
+import '../../../../support/visit_fixtures.dart';
+import '../../../../support/visit_test_backend.dart';
 
 final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];
```

`app/test/features/shop/screens/schedule_settings_screen_test.dart` → `app/test/features/visit/screens/settings/schedule_settings_screen_test.dart` 로 옮긴다(`git mv`). 옮긴 뒤 diff:

```diff
@@ -1,15 +1,15 @@
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/design/widgets/app_choice_chip.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
 
-import '../../../support/customer_test_app.dart';
-import '../../../support/fake_http_client_adapter.dart';
-import '../../../support/visit_fixtures.dart';
-import '../../../support/visit_test_backend.dart';
+import '../../../../support/customer_test_app.dart';
+import '../../../../support/fake_http_client_adapter.dart';
+import '../../../../support/visit_fixtures.dart';
+import '../../../../support/visit_test_backend.dart';
 
 final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];
```

`app/test/features/visit/screens/shared_text_gate_test.dart`:

```diff
@@ -8,7 +8,7 @@ import 'package:chagocnote/design/bridge/glass_surface.dart';
 import 'package:chagocnote/features/auth/api/social_sign_in.dart';
 import 'package:chagocnote/features/auth/state/session.dart';
 import 'package:chagocnote/features/auth/state/session_controller.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/visit/screens/visit_detail_screen_test.dart`:

```diff
@@ -3,7 +3,7 @@ import 'dart:async';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/design/widgets/app_card.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/visit/screens/visit_edit_screen_test.dart`:

```diff
@@ -1,7 +1,7 @@
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/design/widgets/app_choice_chip.dart';
-import 'package:chagocnote/features/home/state/today_provider.dart';
+import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
```

`app/test/features/shop/state/schedule_input_test.dart` → `app/test/features/visit/state/schedule_input_test.dart` 로 옮긴다(`git mv`). 옮긴 뒤 diff:

```diff
@@ -1,4 +1,4 @@
-import 'package:chagocnote/features/shop/state/schedule_input.dart';
+import 'package:chagocnote/features/visit/state/schedule_input.dart';
 import 'package:flutter_test/flutter_test.dart';
 
 void main() {
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

이 작업은 새 테스트가 없다(테스트 파일은 옮기기만 한다). 옮기기 전 `flutter analyze` → `No issues found!`를 확인해 둔다.

- [ ] **Step 3: 구현한다**

`app/lib/features/home/state/today_provider.dart` → `app/lib/core/time/today_provider.dart` 로 옮긴다(`git mv`). 내용은 그대로다.

`app/lib/features/shop/state/shop_errors.dart` → `app/lib/features/auth/state/shop_scoped.dart` 로 옮긴다(`git mv`). 옮긴 뒤 diff:

```diff
@@ -1,7 +1,7 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../../core/error/api_exception.dart';
-import '../../auth/state/session_controller.dart';
+import 'session_controller.dart';
 
 /// 매장 범위 호출 공통 오류 처리.
 ///
```

`app/lib/core/router/app_router.dart`:

```diff
@@ -16,14 +16,14 @@ import '../../features/customer/screens/customer_edit_screen.dart';
 import '../../features/customer/screens/register_customer_screen.dart';
 import '../../features/home/screens/home_shell.dart';
 import '../../features/shop/screens/members_screen.dart';
-import '../../features/shop/screens/menu_settings_screen.dart';
-import '../../features/shop/screens/schedule_settings_screen.dart';
 import '../../features/shop/screens/settings_screen.dart';
 import '../../features/shop/screens/shop_settings_screen.dart';
 import '../../features/visit/api/visit_models.dart';
 import '../../features/visit/screens/day_screen.dart';
 import '../../features/visit/screens/draft_screen.dart';
 import '../../features/visit/screens/register_visit_screen.dart';
+import '../../features/visit/screens/settings/menu_settings_screen.dart';
+import '../../features/visit/screens/settings/schedule_settings_screen.dart';
 import '../../features/visit/screens/visit_detail_screen.dart';
 import '../../features/visit/screens/visit_edit_screen.dart';
 import '../../features/visit/state/visit_prefill.dart';
```

`app/lib/features/customer/screens/pet_form_screen.dart`:

```diff
@@ -11,7 +11,7 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
-import '../../home/state/today_provider.dart';
+import '../../../core/time/today_provider.dart';
 import '../api/customer_models.dart';
 import '../state/customer_commands.dart';
 import '../state/customer_providers.dart';
```

`app/lib/features/customer/screens/register_customer_screen.dart`:

```diff
@@ -14,7 +14,7 @@ import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
-import '../../home/state/today_provider.dart';
+import '../../../core/time/today_provider.dart';
 import '../api/customer_models.dart';
 import '../state/customer_commands.dart';
 import '../state/customer_input.dart';
```

`app/lib/features/customer/state/customer_commands.dart`:

```diff
@@ -1,6 +1,6 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../shop/state/shop_errors.dart';
+import '../../auth/state/shop_scoped.dart';
 import '../api/customer_api.dart';
 import '../api/customer_models.dart';
 import 'customer_list_controller.dart';
```

`app/lib/features/customer/state/customer_list_controller.dart`:

```diff
@@ -1,6 +1,6 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../shop/state/shop_errors.dart';
+import '../../auth/state/shop_scoped.dart';
 import '../api/customer_api.dart';
 import '../api/customer_models.dart';
 import 'customer_providers.dart';
```

`app/lib/features/customer/state/customer_providers.dart`:

```diff
@@ -1,7 +1,7 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../../core/proxy/providers.dart';
-import '../../shop/state/shop_errors.dart';
+import '../../auth/state/shop_scoped.dart';
 import '../api/customer_api.dart';
 import '../api/customer_models.dart';
```

`app/lib/features/home/screens/home_shell.dart`:

```diff
@@ -17,7 +17,7 @@ import '../../customer/screens/customer_list_tab.dart';
 import '../../visit/api/visit_models.dart';
 import '../../visit/screens/calendar_tab.dart';
 import '../../visit/state/calendar_selection.dart';
-import '../state/today_provider.dart';
+import '../../../core/time/today_provider.dart';
 
 /// 홈 화면. 헤더(날짜 + 매장 이름 + 설정), 탭별 본문, 하단 유리 탭바로
 /// 이루어진다.
```

`app/lib/features/shop/state/members_controller.dart`:

```diff
@@ -3,7 +3,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import '../../auth/state/session.dart';
 import '../../auth/state/session_controller.dart';
 import '../api/shop_api.dart';
-import 'shop_errors.dart';
+import '../../auth/state/shop_scoped.dart';
 import 'shop_providers.dart';
 
 /// 매장 하나의 멤버 목록과 그 관리 동작. 매장 id로 만든
```

`app/lib/features/shop/state/shop_settings_controller.dart`:

```diff
@@ -2,7 +2,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../auth/state/session_controller.dart';
 import '../api/shop_api.dart';
-import 'shop_errors.dart';
+import '../../auth/state/shop_scoped.dart';
 import 'shop_providers.dart';
 
 /// 매장 하나의 정보. 매장 id로 만든 [shopSettingsControllerProvider]
```

`app/lib/features/visit/screens/calendar_tab.dart`:

```diff
@@ -16,7 +16,7 @@ import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
-import '../../home/state/today_provider.dart';
+import '../../../core/time/today_provider.dart';
 import '../api/visit_models.dart';
 import '../state/calendar_selection.dart';
 import '../state/day_layout.dart';
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -23,7 +23,7 @@ import '../../customer/state/customer_input.dart';
 import '../../customer/state/customer_list_controller.dart';
 import '../../customer/state/customer_providers.dart';
 import '../../customer/state/search_debouncer.dart';
-import '../../home/state/today_provider.dart';
+import '../../../core/time/today_provider.dart';
 import '../api/visit_models.dart';
 import '../state/visit_commands.dart';
 import '../state/visit_prefill.dart';
```

`app/lib/features/shop/screens/menu_settings_screen.dart` → `app/lib/features/visit/screens/settings/menu_settings_screen.dart` 로 옮긴다(`git mv`). 옮긴 뒤 diff:

```diff
@@ -2,24 +2,24 @@ import 'package:flutter/material.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../../core/error/error_messages.dart';
-import '../../../core/router/screen_keys.dart';
-import '../../../design/app_theme.dart';
-import '../../../design/tokens/app_colors.dart';
-import '../../../design/tokens/app_spacing.dart';
-import '../../../design/tokens/app_typography.dart';
-import '../../../design/widgets/app_back_button.dart';
-import '../../../design/widgets/app_button.dart';
-import '../../../design/widgets/app_card.dart';
-import '../../../design/widgets/app_choice_chip.dart';
-import '../../../design/widgets/app_sheet.dart';
-import '../../../design/widgets/pressable.dart';
-import '../../../l10n/app_strings.dart';
-import '../../auth/state/shop_selection.dart';
-import '../../visit/api/visit_models.dart';
-import '../../visit/state/visit_commands.dart';
-import '../../visit/state/visit_form_rules.dart';
-import '../../visit/state/visit_providers.dart';
+import '../../../../core/error/error_messages.dart';
+import '../../../../core/router/screen_keys.dart';
+import '../../../../design/app_theme.dart';
+import '../../../../design/tokens/app_colors.dart';
+import '../../../../design/tokens/app_spacing.dart';
+import '../../../../design/tokens/app_typography.dart';
+import '../../../../design/widgets/app_back_button.dart';
+import '../../../../design/widgets/app_button.dart';
+import '../../../../design/widgets/app_card.dart';
+import '../../../../design/widgets/app_choice_chip.dart';
+import '../../../../design/widgets/app_sheet.dart';
+import '../../../../design/widgets/pressable.dart';
+import '../../../../l10n/app_strings.dart';
+import '../../../auth/state/shop_selection.dart';
+import '../../api/visit_models.dart';
+import '../../state/visit_commands.dart';
+import '../../state/visit_form_rules.dart';
+import '../../state/visit_providers.dart';
 
 /// 설정 → 메뉴(사장만) — 메뉴표 추가·이름·기본 소요·순서·보관(설계 9.1).
 /// 메뉴는 지우지 않고 보관한다(지난 방문이 가리킨다).
```

`app/lib/features/shop/screens/schedule_settings_screen.dart` → `app/lib/features/visit/screens/settings/schedule_settings_screen.dart` 로 옮긴다(`git mv`). 옮긴 뒤 diff:

```diff
@@ -2,27 +2,27 @@ import 'package:flutter/material.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../../core/error/error_messages.dart';
-import '../../../core/router/screen_keys.dart';
-import '../../../design/app_theme.dart';
-import '../../../design/tokens/app_colors.dart';
-import '../../../design/tokens/app_spacing.dart';
-import '../../../design/tokens/app_typography.dart';
-import '../../../design/widgets/app_back_button.dart';
-import '../../../design/widgets/app_button.dart';
-import '../../../design/widgets/app_card.dart';
-import '../../../design/widgets/app_choice_chip.dart';
-import '../../../design/widgets/app_sheet.dart';
-import '../../../design/widgets/pressable.dart';
-import '../../../l10n/app_strings.dart';
-import '../../auth/state/shop_selection.dart';
-import '../../home/state/today_provider.dart';
-import '../../visit/api/visit_models.dart';
-import '../../visit/screens/visit_labels.dart';
-import '../../visit/state/visit_commands.dart';
-import '../../visit/state/visit_form_rules.dart';
-import '../../visit/state/visit_providers.dart';
-import '../state/schedule_input.dart';
+import '../../../../core/error/error_messages.dart';
+import '../../../../core/router/screen_keys.dart';
+import '../../../../design/app_theme.dart';
+import '../../../../design/tokens/app_colors.dart';
+import '../../../../design/tokens/app_spacing.dart';
+import '../../../../design/tokens/app_typography.dart';
+import '../../../../design/widgets/app_back_button.dart';
+import '../../../../design/widgets/app_button.dart';
+import '../../../../design/widgets/app_card.dart';
+import '../../../../design/widgets/app_choice_chip.dart';
+import '../../../../design/widgets/app_sheet.dart';
+import '../../../../design/widgets/pressable.dart';
+import '../../../../l10n/app_strings.dart';
+import '../../../auth/state/shop_selection.dart';
+import '../../../../core/time/today_provider.dart';
+import '../../api/visit_models.dart';
+import '../visit_labels.dart';
+import '../../state/visit_commands.dart';
+import '../../state/visit_form_rules.dart';
+import '../../state/visit_providers.dart';
+import '../../state/schedule_input.dart';
 
 /// 설정 → 일정(사장만) — 영업시간, 기본 소요, 매주 쉬는 요일, 임시 휴무
 /// (설계 9.1). 영업시간·소요·요일은 [저장]으로 한 번에 보내고, 임시 휴무는
```

`app/lib/features/visit/state/calendar_selection.dart`:

```diff
@@ -1,6 +1,6 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../home/state/today_provider.dart';
+import '../../../core/time/today_provider.dart';
 
 /// 캘린더 탭에서 고른 날. 처음에는 오늘이다. 홈의 + 버튼이 이 날로 예약
 /// 등록을 연다(달력에서 날짜를 고른 뒤 +, 설계 9.1).
```

`app/lib/features/shop/state/schedule_input.dart` → `app/lib/features/visit/state/schedule_input.dart` 로 옮긴다(`git mv`). 내용은 그대로다.

`app/lib/features/visit/state/visit_commands.dart`:

```diff
@@ -2,7 +2,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../customer/state/customer_list_controller.dart';
 import '../../customer/state/customer_providers.dart';
-import '../../shop/state/shop_errors.dart';
+import '../../auth/state/shop_scoped.dart';
 import '../api/visit_api.dart';
 import '../api/visit_models.dart';
 import 'visit_providers.dart';
```

`app/lib/features/visit/state/visit_providers.dart`:

```diff
@@ -1,7 +1,7 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../../core/proxy/providers.dart';
-import '../../shop/state/shop_errors.dart';
+import '../../auth/state/shop_scoped.dart';
 import '../api/visit_api.dart';
 import '../api/visit_models.dart';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 507 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 이 작업은 옮기기라 변이 대신 컴파일로 판별한다: 옮긴 뒤 `lib/features/home/state/today_provider.dart`를 옛 자리에 다시 만들면(같은 내용) `flutter analyze`는 통과하지만 작업 3 의 `feature_imports_test`(아무도 home 을 import 하지 않는다)가 그 파일을 import 하는 곳이 있을 때 잡는다.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 공유 상태의 자리를 바로잡는다 — today_provider 는 core/time, runShopScoped 는 auth/state, 메뉴·일정 설정 화면과 schedule_input 은 소유자인 visit 로(A9 ①·②)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 기능 폴더 간 import 규칙 — 시각·날짜 도우미를 `core/time`으로 옮겨 `customer`가 `visit`를 모르게 하고, 구조 테스트가 방향을 고정한다 (A9 ③·⑤)

**Files:**
- Create: `app/lib/core/time/shop_time.dart`
- Create: `app/lib/core/time/time_labels.dart`
- Modify: `app/CLAUDE.md`
- Modify: `app/lib/features/customer/api/customer_models.dart`
- Modify: `app/lib/features/customer/screens/pet_detail_screen.dart`
- Modify: `app/lib/features/visit/api/visit_models.dart`
- Modify: `app/lib/features/visit/screens/visit_labels.dart`
- Create: `app/test/design/feature_imports_test.dart`

**Interfaces:**
- Consumes: `features/visit/api/visit_models.dart`의 `ShopTime`·`parseDay`·`isoDay`·`isoMonth`, `features/visit/screens/visit_labels.dart`의 `hhmm`·`dayLabel`·`sameDay`(customer 의 반려동물 상세가 이것 때문에 visit 를 import 했다).
- Produces: `lib/core/time/shop_time.dart`(`class ShopTime`, `DateTime parseDay(String)`, `String isoDay(DateTime)`, `String isoMonth(DateTime)`), `lib/core/time/time_labels.dart`(`String hhmm(DateTime)`, `String dayLabel(DateTime)`, `bool sameDay(DateTime, DateTime)`). `visit_models.dart`는 `import` + `export '../../../core/time/shop_time.dart';`, `visit_labels.dart`는 `export '../../../core/time/time_labels.dart';`로 옛 이름을 그대로 내보낸다(visit 쪽 호출은 바뀌지 않는다). `test/design/feature_imports_test.dart` — 규칙 표 `allowed = {'visit': {'customer'}}`, `shared = {'auth'}`, `shell = {'home'}`; 상대 import 를 `Uri.file(...).resolve`로 풀어 `lib/features/<to>/`를 판정한다. `app/CLAUDE.md`에 규칙 두 줄(기능 폴더 import 방향, 세션 파생 프로바이더만 watch).

감사 결과(설계 4.2 A9 ③·⑤): `customer → visit` import 가 있었고(반려동물 상세의 시각 도우미), 백엔드의 허브-스포크 같은 규칙이 앱에는 없었다. **설계와 다른 점**(결정 기록 007): 설계 ③의 `core/plugs/` 자리는 만들지 않는다 — `customer → visit` 의존은 시각 도우미뿐이라 `core/time`으로 옮기니 사라졌다. [기록] 탭이 생기는 ④-2 에서 그때 만든다. ④(`ShopDataChanged` 신호)도 만들지 않는다 — `visit_commands`가 customer 프로바이더를 무효화하는 것은 허용 방향이다. 구조 테스트는 `test/structure/`가 아니라 기존 `test/design/`(구조 테스트 `glass_boundary_test.dart`의 선례)에 둔다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/feature_imports_test.dart`:

```dart
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 기능 폴더(`lib/features/<기능>/`) 사이의 import 규칙 — 백엔드의 허브-스포크처럼 방향을 하나로 둔다.
///
/// - `auth`는 공용이다(세션·매장 선택·`runShopScoped`). 누구나 import 할 수 있다.
/// - `home`은 조립 껍데기다. 다른 기능을 import 할 수 있고, 아무도 `home`을 import 하지 않는다.
/// - `visit → customer`는 허용한다(예약 ①이 고객 검색을 재사용한다).
/// - 그 밖의 기능 간 import 는 금지다. 반대 방향이 필요하면 `lib/core/plugs/`의 자리를 `app.dart`가 채운다
///   (백엔드의 `dependencies/hub_ports.py`와 같은 꼴).
/// - 여러 기능이 함께 쓰는 것(시각·날짜 도우미, 오늘 날짜)은 `lib/core/`에 둔다.
void main() {
  const allowed = <String, Set<String>>{
    'visit': {'customer'},
  };
  const shared = {'auth'};
  const shell = {'home'};

  test('기능 폴더끼리는 정해진 방향으로만 import 한다', () {
    final root = Directory('lib/features');
    final violations = <String>[];
    final relative = RegExp(r"^import '(\.\.?/[^']+)';", multiLine: true);

    for (final entity in root.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      final normalized = entity.path.replaceAll(r'\', '/');
      final from = normalized.split('lib/features/')[1].split('/')[0];
      if (shell.contains(from)) continue;

      for (final match in relative.allMatches(entity.readAsStringSync())) {
        // 상대 경로를 파일 위치 기준으로 풀어 어느 기능 폴더로 가는지 본다.
        final target = Uri.file(normalized).resolve(match.group(1)!).path;
        final marker = target.indexOf('lib/features/');
        if (marker < 0) continue; // core·design·l10n 은 기능이 아니다
        final to = target
            .substring(marker + 'lib/features/'.length)
            .split('/')[0];
        if (to == from) continue;
        if (shared.contains(to)) continue;
        if (allowed[from]?.contains(to) ?? false) continue;
        violations.add('$normalized → $to');
      }
    }

    expect(violations, isEmpty, reason: '허용되지 않은 기능 간 import: $violations');
  });

  test('아무도 home 을 import 하지 않는다', () {
    final violations = <String>[];
    for (final entity in Directory('lib').listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      final normalized = entity.path.replaceAll(r'\', '/');
      if (normalized.contains('lib/features/home/')) continue;
      if (normalized == 'lib/core/router/app_router.dart') {
        continue; // 라우터는 조립 지점이다
      }
      if (entity.readAsStringSync().contains('features/home/')) {
        violations.add(normalized);
      }
    }
    expect(violations, isEmpty, reason: 'home 을 import 함: $violations');
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/design/feature_imports_test.dart`
Expected: `기능 폴더끼리는 정해진 방향으로만 import 한다` 실패 — 이유에 `customer/screens/pet_detail_screen.dart → visit` 가 보인다.

- [ ] **Step 3: 구현한다**

`app/lib/core/time/shop_time.dart`:

```dart
/// 서버가 주는 매장 시각·날짜 문자열과 화면의 `DateTime` 사이의 변환. 기능 폴더 여럿이 함께 쓴다.
///
/// 시간대 계산은 하지 않는다 — 응답 시각은 매장 시간대이고 앱은 벽시계 값만 보인다(결정 기록 006).
library;

/// 매장 시간대가 붙은 시각(`2026-10-02T14:00:00+09:00`).
///
/// 화면에는 [wall](매장의 벽시계 — 시간대 없이 만든 `DateTime`)을 보이고,
/// 서버에는 받은 문자열 [iso]를 그대로 돌려보낸다. 기기 시간대로 바꾸지 않는다
/// (결정 기록 006 — 응답 시각은 매장 시간대다).
class ShopTime {
  const ShopTime._(this.wall, this.iso);

  factory ShopTime.parse(String iso) {
    final m = _pattern.firstMatch(iso);
    if (m == null) throw FormatException('시각 형식이 아닙니다', iso);
    int part(int i) => int.parse(m.group(i) ?? '0');
    return ShopTime._(
      DateTime(part(1), part(2), part(3), part(4), part(5), part(6)),
      iso,
    );
  }

  static final _pattern = RegExp(
    r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?',
  );

  final DateTime wall;
  final String iso;

  /// 그날(매장 시간대)의 날짜만.
  DateTime get day => DateTime(wall.year, wall.month, wall.day);
}

/// `2026-10-02` → 그날 자정(시간대 없음).
DateTime parseDay(String value) {
  final parts = value.split('-').map(int.parse).toList();
  return DateTime(parts[0], parts[1], parts[2]);
}

/// 날짜를 `2026-10-02`로.
String isoDay(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// 달을 `2026-10`으로.
String isoMonth(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}';
```

`app/lib/core/time/time_labels.dart`:

```dart
/// 시각·날짜를 화면 글자로. 기능 폴더 여럿이 함께 쓴다(방문·고객·설정).
library;

import '../../l10n/app_strings.dart';

/// `14:00`.
String hhmm(DateTime t) =>
    '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

/// `10월 2일 금`.
String dayLabel(DateTime d) =>
    '${d.month}월 ${d.day}일 ${AppStrings.weekdaysShort[d.weekday - 1]}';

bool sameDay(DateTime a, DateTime b) =>
    a.year == b.year && a.month == b.month && a.day == b.day;
```

`app/CLAUDE.md`:

```diff
@@ -6,6 +6,8 @@
 
 - **웹뷰 방식 금지.** 웹뷰 패키지를 넣지 않고, 어떤 화면도 인앱 웹뷰로 만들지 않는다. 소셜 로그인도 네이티브 경로다(Apple 버튼은 iOS 만).
 - 폴더는 `lib/core/{config,proxy,storage,router,error}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
+- **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`가 채운다. 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
+- 화면은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다. `auth/state/shop_selection.dart`의 파생 프로바이더(`selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider`·`shopCountProvider`·`currentUserIdProvider`)만 watch 한다.
 - 서버 응답의 필드명은 변환하지 않는다. 모델은 평범한 클래스에 `fromJson` 을 직접 쓴다. 코드 생성기를 도입하지 않는다.
 - `liquid_glass_widgets` 는 `lib/design/bridge/` 안에서만 import 한다. 화면은 `lib/design/widgets` 만 쓴다.
 - 토큰을 로그에 남기지 않는다. `print`·`debugPrint`·dio `LogInterceptor` 를 쓰지 않는다(`avoid_print` 는 오류다).
```

`app/lib/features/customer/api/customer_models.dart`:

```diff
@@ -267,7 +267,7 @@ class UpcomingVisit {
   final int? petId;
   final String? petName;
 
-  /// 매장 시간대가 붙은 시각 문자열. 화면은 `visit` 기능의 `ShopTime`으로 읽는다.
+  /// 매장 시간대가 붙은 시각 문자열. 화면은 `core/time`의 `ShopTime`으로 읽는다.
   final String startsAt;
 }
```

`app/lib/features/customer/screens/pet_detail_screen.dart`:

```diff
@@ -4,6 +4,8 @@ import 'package:go_router/go_router.dart';
 
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
+import '../../../core/time/shop_time.dart';
+import '../../../core/time/time_labels.dart';
 import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
@@ -17,8 +19,6 @@ import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
-import '../../visit/api/visit_models.dart';
-import '../../visit/screens/visit_labels.dart';
 import '../api/customer_models.dart';
 import '../state/customer_commands.dart';
 import '../state/customer_input.dart';
```

`app/lib/features/visit/api/visit_models.dart`:

```diff
@@ -4,48 +4,10 @@
 /// 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
 library;
 
-/// 매장 시간대가 붙은 시각(`2026-10-02T14:00:00+09:00`).
-///
-/// 화면에는 [wall](매장의 벽시계 — 시간대 없이 만든 `DateTime`)을 보이고,
-/// 서버에는 받은 문자열 [iso]를 그대로 돌려보낸다. 기기 시간대로 바꾸지 않는다
-/// (결정 기록 006 — 응답 시각은 매장 시간대다).
-class ShopTime {
-  const ShopTime._(this.wall, this.iso);
-
-  factory ShopTime.parse(String iso) {
-    final m = _pattern.firstMatch(iso);
-    if (m == null) throw FormatException('시각 형식이 아닙니다', iso);
-    int part(int i) => int.parse(m.group(i) ?? '0');
-    return ShopTime._(
-      DateTime(part(1), part(2), part(3), part(4), part(5), part(6)),
-      iso,
-    );
-  }
-
-  static final _pattern = RegExp(
-    r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?',
-  );
-
-  final DateTime wall;
-  final String iso;
-
-  /// 그날(매장 시간대)의 날짜만.
-  DateTime get day => DateTime(wall.year, wall.month, wall.day);
-}
-
-/// `2026-10-02` → 그날 자정(시간대 없음).
-DateTime parseDay(String value) {
-  final parts = value.split('-').map(int.parse).toList();
-  return DateTime(parts[0], parts[1], parts[2]);
-}
-
-/// 날짜를 `2026-10-02`로.
-String isoDay(DateTime d) =>
-    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
+// 매장 시각·날짜 문자열 도우미는 core/time 에 있다. 이 모듈을 import 하던 곳이 그대로 쓰게 다시 내보낸다.
+import '../../../core/time/shop_time.dart';
 
-/// 달을 `2026-10`으로.
-String isoMonth(DateTime d) =>
-    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}';
+export '../../../core/time/shop_time.dart';
 
 /// 방문 상태. 서버 값 그대로다.
 abstract final class VisitStatus {
```

`app/lib/features/visit/screens/visit_labels.dart`:

```diff
@@ -1,16 +1,8 @@
 import '../../../l10n/app_strings.dart';
 import '../api/visit_models.dart';
 
-/// `14:00`.
-String hhmm(DateTime t) =>
-    '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
-
-/// `10월 2일 금`.
-String dayLabel(DateTime d) =>
-    '${d.month}월 ${d.day}일 ${AppStrings.weekdaysShort[d.weekday - 1]}';
-
-bool sameDay(DateTime a, DateTime b) =>
-    a.year == b.year && a.month == b.month && a.day == b.day;
+// 시각·날짜 표기(hhmm·dayLabel·sameDay)는 core/time 에 있다. 이 모듈을 import 하던 곳이 그대로 쓰게 다시 내보낸다.
+export '../../../core/time/time_labels.dart';
 
 String statusLabel(String status) => switch (status) {
   VisitStatus.reserved => AppStrings.statusReserved,
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/design/feature_imports_test.dart` → 2 passed

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 509 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `lib/features/customer/screens/pet_detail_screen.dart`에 `import '../../visit/api/visit_models.dart';`를 더한다 → `기능 폴더끼리는 정해진 방향으로만 import 한다` 실패.
- `lib/features/visit/screens/day_screen.dart`에 `import '../../home/screens/home_shell.dart';`를 더한다 → 같은 테스트와 `아무도 home 을 import 하지 않는다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 기능 폴더 간 import 규칙 — 시각·날짜 도우미를 core/time 으로 옮겨 customer 가 visit 를 모르게 하고, 구조 테스트가 방향을 고정한다(A9 ③·⑤)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 방문 상태·행동을 enum 으로, 완료 후속 행동을 sealed 타입으로 — 문자열 `switch`의 폴백을 없앤다 (A1)

**Files:**
- Modify: `app/lib/features/visit/api/visit_models.dart`
- Modify: `app/lib/features/visit/api/visit_api.dart`
- Modify: `app/lib/features/visit/screens/visit_actions.dart`
- Modify: `app/integration_test/draft_flow_test.dart`
- Modify: `app/lib/features/visit/screens/day_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_detail_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_labels.dart`
- Modify: `app/lib/features/visit/state/day_layout.dart`
- Modify: `app/lib/features/visit/state/visit_commands.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Create: `app/test/features/visit/api/visit_status_test.dart`

**Interfaces:**
- Consumes: `features/visit/api/visit_models.dart`의 문자열 상수 `VisitStatus`와 `Visit.status: String`, `VisitApi.transition(action: String)`, `features/visit/screens/visit_actions.dart`의 `VisitChoice(action, cancelReason, thenNext, draft)`, 화면 다섯의 문자열 `switch`.
- Produces: `enum VisitStatus { reserved('reserved'), inProgress('in_progress'), completed('completed'), canceled('canceled'), noShow('no_show'), unknown('') }` — `code`, `static VisitStatus fromCode(String)`(모르면 `unknown`), `bool get occupiesTime`(취소·노쇼만 false); `Visit.status: VisitStatus`(`fromJson`이 `fromCode`); `enum VisitAction { start, complete, cancel, noShow, revert }`(`code`); `VisitApi.transition(..., required VisitAction action)`은 `action.code`를 보낸다; `sealed class AfterComplete` — `AfterNothing()`, `AfterNextReservation({NextVisitDraft? draft})`; `VisitChoice(VisitAction action, {String? cancelReason, AfterComplete after = const AfterNothing()})`; `askVisitAction(..., required VisitAction action, ...)`·`sendVisitAction`은 `switch`로 완전 열거; `AppStrings.statusUnknown = '알 수 없음'`. 모든 `switch`에서 `_ =>` 폴백이 사라진다. 서버에 보내는 문자열과 받는 JSON 은 그대로다.

감사 결과(설계 4.2 A1): 방문 상태 문자열 `switch`가 다섯 파일에 흩어져 있고 `_ =>` 폴백 때문에 새 상태·행동이 UI 에서 조용히 빠졌다. 완료 후속 행동이 bool 둘이었다. **설계와 다른 점**(결정 기록 007): `AfterComplete`는 `none`·`nextReservation` 둘뿐이다 — `record`는 기록 화면이 생기는 ④-2 에서 셋째로 더하고, 그때 `sendVisitAction`의 `switch`가 빠진 분기를 컴파일 오류로 알린다. 모르는 상태는 `unknown`으로 받아 화면은 "알 수 없음"으로 보이고 버튼을 내지 않으며 시간표 자리는 차지한다(서버가 앱보다 먼저 새 상태를 알게 됐을 때 방문을 숨기지 않는다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/integration_test/draft_flow_test.dart`:

```diff
@@ -907,7 +907,7 @@ void main() {
       await shot('08c-mixed-completed');
       soft(
         after.length == 2 &&
-            after.every((s) => s.endsWith(VisitStatus.completed)),
+            after.every((s) => s.endsWith(VisitStatus.completed.code)),
         '$mixedAt 두 마리가 모두 완료가 아니다',
       );
```

`app/test/features/visit/api/visit_status_test.dart`:

```dart
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/screens/visit_labels.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

void main() {
  test('서버 상태 문자열은 enum 으로 한 번만 바뀐다', () {
    expect(VisitStatus.fromCode('reserved'), VisitStatus.reserved);
    expect(VisitStatus.fromCode('in_progress'), VisitStatus.inProgress);
    expect(VisitStatus.fromCode('completed'), VisitStatus.completed);
    expect(VisitStatus.fromCode('canceled'), VisitStatus.canceled);
    expect(VisitStatus.fromCode('no_show'), VisitStatus.noShow);
    expect(
      Visit.fromJson(visitJson(status: 'no_show')).status,
      VisitStatus.noShow,
    );
  });

  test('모르는 상태는 unknown 이고 화면은 "알 수 없음"으로 보인다', () {
    expect(VisitStatus.fromCode('paused'), VisitStatus.unknown);
    expect(statusLabel(VisitStatus.unknown), AppStrings.statusUnknown);
  });

  test('취소·노쇼만 빈 시간이다', () {
    expect(VisitStatus.values.where((s) => !s.occupiesTime).toList(), [
      VisitStatus.canceled,
      VisitStatus.noShow,
    ]);
  });

  test('행동의 서버 값은 그대로다', () {
    expect(
      [for (final a in VisitAction.values) a.code],
      ['start', 'complete', 'cancel', 'no_show', 'revert'],
    );
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/features/visit/api/visit_status_test.dart`
Expected: 컴파일 실패 — `VisitStatus.fromCode` 가 없다(`Member not found: 'fromCode'`).

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/api/visit_models.dart`:

```diff
@@ -9,22 +9,47 @@ import '../../../core/time/shop_time.dart';
 
 export '../../../core/time/shop_time.dart';
 
-/// 방문 상태. 서버 값 그대로다.
-abstract final class VisitStatus {
-  static const reserved = 'reserved';
-  static const inProgress = 'in_progress';
-  static const completed = 'completed';
-  static const canceled = 'canceled';
-  static const noShow = 'no_show';
+/// 방문 상태. 서버 문자열은 `fromJson`에서 한 번만 enum 으로 바꾼다.
+///
+/// 모르는 값은 [unknown] — 서버가 앱보다 먼저 새 상태를 알게 됐을 때 화면은 상태
+/// 이름을 "알 수 없음"으로 보이고 버튼을 내지 않는다. `switch`는 폴백 없이 완전
+/// 열거한다 — 상태를 더하면 컴파일러가 빠진 곳을 알려 준다.
+enum VisitStatus {
+  reserved('reserved'),
+  inProgress('in_progress'),
+  completed('completed'),
+  canceled('canceled'),
+  noShow('no_show'),
+  unknown('');
+
+  const VisitStatus(this.code);
+
+  /// 서버 값.
+  final String code;
+
+  static VisitStatus fromCode(String code) => values.firstWhere(
+    (status) => status.code == code,
+    orElse: () => VisitStatus.unknown,
+  );
+
+  /// 시간을 차지하는 상태(예약됨·미용 중·완료). 취소·노쇼는 빈 시간이다.
+  bool get occupiesTime => switch (this) {
+    reserved || inProgress || completed || unknown => true,
+    canceled || noShow => false,
+  };
 }
 
-/// 상태 전이 행동. 서버 값 그대로다.
-abstract final class VisitAction {
-  static const start = 'start';
-  static const complete = 'complete';
-  static const cancel = 'cancel';
-  static const noShow = 'no_show';
-  static const revert = 'revert';
+/// 상태 전이 행동. 서버에는 [code]를 보낸다.
+enum VisitAction {
+  start('start'),
+  complete('complete'),
+  cancel('cancel'),
+  noShow('no_show'),
+  revert('revert');
+
+  const VisitAction(this.code);
+
+  final String code;
 }
 
 /// 막지 않는 경고. 서버 값 그대로다.
@@ -116,7 +141,7 @@ class Visit {
     startsAt: ShopTime.parse(json['starts_at'] as String),
     endsAt: ShopTime.parse(json['ends_at'] as String),
     durationMinutes: json['duration_minutes'] as int,
-    status: json['status'] as String,
+    status: VisitStatus.fromCode(json['status'] as String),
     cancelReason: json['cancel_reason'] as String?,
     memo: json['memo'] as String?,
     menus: _menus(json['menus']),
@@ -130,7 +155,7 @@ class Visit {
   final ShopTime startsAt;
   final ShopTime endsAt;
   final int durationMinutes;
-  final String status;
+  final VisitStatus status;
 
   /// 'customer_request' | 'shop_reason' — 취소일 때만.
   final String? cancelReason;
@@ -138,8 +163,7 @@ class Visit {
   final List<MenuBrief> menus;
 
   /// 시간을 차지하는 방문(예약됨·미용 중·완료). 취소·노쇼는 빈 시간이다.
-  bool get occupiesTime =>
-      status != VisitStatus.canceled && status != VisitStatus.noShow;
+  bool get occupiesTime => status.occupiesTime;
 }
 
 class DayCounts {
```

`app/lib/features/visit/api/visit_api.dart`:

```diff
@@ -79,7 +79,7 @@ class VisitApi {
   Future<List<Visit>> transition(
     int shopId, {
     required List<int> visitIds,
-    required String action,
+    required VisitAction action,
     String? cancelReason,
   }) async {
     final data =
@@ -87,7 +87,7 @@ class VisitApi {
               '/v1/shops/$shopId/visits/transitions',
               data: {
                 'visit_ids': visitIds,
-                'action': action,
+                'action': action.code,
                 'cancel_reason': ?cancelReason,
               },
             )
```

`app/lib/features/visit/screens/visit_actions.dart`:

```diff
@@ -106,20 +106,36 @@ abstract final class VisitSheets {
   );
 }
 
-/// 시트에서 고른 상태 전이. [cancelReason]은 취소일 때만, [thenNext]는
-/// "완료하고 다음 예약 잡기"일 때 true, [draft]는 그때 미리 받아 둔 초안.
+/// 완료 뒤에 이어서 할 일. 완료 시트의 선택이다 — bool 둘 대신 닫힌 타입으로 두어
+/// 종류가 늘 때(④-2 "기록으로") `switch` 한 곳에 분기가 붙는다.
+sealed class AfterComplete {
+  const AfterComplete();
+}
+
+/// 완료만 한다.
+class AfterNothing extends AfterComplete {
+  const AfterNothing();
+}
+
+/// 완료하고 다음 예약 잡기. [draft]는 시트를 띄우기 전에 미리 받아 둔 초안(없을 수 있다).
+class AfterNextReservation extends AfterComplete {
+  const AfterNextReservation({this.draft});
+
+  final NextVisitDraft? draft;
+}
+
+/// 시트에서 고른 상태 전이. [cancelReason]은 취소일 때만, [after]는 완료일 때
+/// 이어서 할 일.
 class VisitChoice {
   const VisitChoice(
     this.action, {
     this.cancelReason,
-    this.thenNext = false,
-    this.draft,
+    this.after = const AfterNothing(),
   });
 
-  final String action;
+  final VisitAction action;
   final String? cancelReason;
-  final bool thenNext;
-  final NextVisitDraft? draft;
+  final AfterComplete after;
 }
 
 /// 전이에 필요한 것을 시트로 묻는다(취소 사유, 노쇼 확인, 완료 / 완료하고
@@ -136,10 +152,13 @@ Future<VisitChoice?> askVisitAction(
   BuildContext context,
   WidgetRef ref, {
   required int shopId,
-  required String action,
+  required VisitAction action,
   required int anchorVisitId,
 }) async {
   switch (action) {
+    case VisitAction.start:
+    case VisitAction.revert:
+      return VisitChoice(action);
     case VisitAction.cancel:
       final reason = await VisitSheets.cancelReason(context);
       return reason == null ? null : VisitChoice(action, cancelReason: reason);
@@ -157,11 +176,11 @@ Future<VisitChoice?> askVisitAction(
       }
       if (!context.mounted) return null;
       final next = await VisitSheets.complete(context, draft: draft);
-      return next == null
-          ? null
-          : VisitChoice(VisitAction.complete, thenNext: next, draft: draft);
-    default:
-      return VisitChoice(action);
+      if (next == null) return null;
+      return VisitChoice(
+        VisitAction.complete,
+        after: next ? AfterNextReservation(draft: draft) : const AfterNothing(),
+      );
   }
 }
 
@@ -183,8 +202,12 @@ Future<void> sendVisitAction(
     action: choice.action,
     cancelReason: choice.cancelReason,
   );
-  if (!choice.thenNext) return;
-  final draft = choice.draft ?? await commands.nextDraft(shopId, anchorVisitId);
-  // 기다리지 않는다 — 예약 화면이 닫힐 때까지 부른 화면이 "보내는 중"에 묶이지 않게.
-  if (context.mounted) context.push('/visits/new', extra: draft);
+  switch (choice.after) {
+    case AfterNothing():
+      return;
+    case AfterNextReservation(:final draft):
+      final next = draft ?? await commands.nextDraft(shopId, anchorVisitId);
+      // 기다리지 않는다 — 예약 화면이 닫힐 때까지 부른 화면이 "보내는 중"에 묶이지 않게.
+      if (context.mounted) context.push('/visits/new', extra: next);
+  }
 }
```

`app/lib/features/visit/screens/day_screen.dart`:

```diff
@@ -53,7 +53,7 @@ class _DayScreenState extends ConsumerState<DayScreen> {
 
   int? get _shopId => ref.read(selectedShopIdProvider);
 
-  Future<void> _act(DayGroup group, String action) async {
+  Future<void> _act(DayGroup group, VisitAction action) async {
     final shopId = _shopId;
     if (shopId == null || _busyVisitId != null || _asking) return;
     // 상태가 섞인 묶음이면 아직 진행 가능한 아이들만(다음 예약 초안도 그 아이 기준).
@@ -332,7 +332,7 @@ class _DayList extends StatelessWidget {
   /// 완료 시트를 띄우기 전 초안을 읽는 동안(설계 6.2) — 이때는 카드 버튼을
   /// 전부 막지만 스피너는 켜지 않는다.
   final bool asking;
-  final void Function(DayGroup group, String action) onAction;
+  final void Function(DayGroup group, VisitAction action) onAction;
 
   @override
   Widget build(BuildContext context) {
@@ -382,7 +382,7 @@ class _GroupCard extends StatelessWidget {
   final DayGroup group;
   final bool busy;
   final bool otherBusy;
-  final ValueChanged<String> onAction;
+  final ValueChanged<VisitAction> onAction;
 
   @override
   Widget build(BuildContext context) {
@@ -395,7 +395,7 @@ class _GroupCard extends StatelessWidget {
     // 상태가 섞였으면 아직 진행 가능한 아이들의 상태로 버튼을 정한다(A2 잔여).
     final mixed = status == null;
     final buttonStatus = mixed ? group.actionableStatus : status;
-    VoidCallback? on(String action) =>
+    VoidCallback? on(VisitAction action) =>
         busy || otherBusy ? null : () => onAction(action);
     final Widget trailing = switch (buttonStatus) {
       VisitStatus.reserved => AppButton(
```

`app/lib/features/visit/screens/visit_detail_screen.dart`:

```diff
@@ -56,7 +56,7 @@ class _VisitDetailScreenState extends ConsumerState<VisitDetailScreen> {
       if (v.status == detail.visit.status) v.visitId,
   ];
 
-  Future<void> _act(VisitDetail detail, String action) async {
+  Future<void> _act(VisitDetail detail, VisitAction action) async {
     final shopId = _shopId;
     if (shopId == null || _busy || _asking) return;
     setState(() => _asking = true);
@@ -98,39 +98,41 @@ class _VisitDetailScreenState extends ConsumerState<VisitDetailScreen> {
 
   Future<void> _openMore(VisitDetail detail) async {
     final status = detail.visit.status;
-    final choice = await AppSheet.show<String>(
+    final choice = await AppSheet.show<_More>(
       context,
       builder: (context) => Column(
         mainAxisSize: MainAxisSize.min,
         children: [
           if (status != VisitStatus.canceled && status != VisitStatus.noShow)
-            const _SheetAction(label: AppStrings.edit, value: 'edit'),
+            const _SheetAction(label: AppStrings.edit, value: _More.edit),
           if (status == VisitStatus.reserved)
             const _SheetAction(
               label: AppStrings.actionCompleteNow,
-              value: VisitAction.complete,
+              value: _More.completeNow,
             ),
           if (status != VisitStatus.reserved)
             const _SheetAction(
               label: AppStrings.actionRevert,
-              value: VisitAction.revert,
+              value: _More.revert,
             ),
           if (status == VisitStatus.completed)
             const _SheetAction(
               label: AppStrings.actionNextReservation,
-              value: 'next',
+              value: _More.next,
             ),
         ],
       ),
     );
     if (choice == null || !mounted) return;
     switch (choice) {
-      case 'edit':
+      case _More.edit:
         context.push('/visits/${detail.visit.visitId}/edit');
-      case 'next':
+      case _More.next:
         await _openNext(detail);
-      default:
-        await _act(detail, choice);
+      case _More.completeNow:
+        await _act(detail, VisitAction.complete);
+      case _More.revert:
+        await _act(detail, VisitAction.revert);
     }
   }
 
@@ -238,7 +240,7 @@ class _Body extends StatelessWidget {
   final VisitDetail detail;
   final bool busy;
   final String? errorText;
-  final ValueChanged<String> onAction;
+  final ValueChanged<VisitAction> onAction;
 
   @override
   Widget build(BuildContext context) {
@@ -311,13 +313,14 @@ class _StatusButtons extends StatelessWidget {
     required this.onAction,
   });
 
-  final String status;
+  final VisitStatus status;
   final bool busy;
-  final ValueChanged<String> onAction;
+  final ValueChanged<VisitAction> onAction;
 
   @override
   Widget build(BuildContext context) {
-    VoidCallback? on(String action) => busy ? null : () => onAction(action);
+    VoidCallback? on(VisitAction action) =>
+        busy ? null : () => onAction(action);
     return switch (status) {
       VisitStatus.reserved => Row(
         children: [
@@ -416,11 +419,14 @@ class _GroupCard extends StatelessWidget {
   }
 }
 
+/// `···` 시트의 항목. 문자열 대신 닫힌 enum 이라 처리 `switch`가 완전 열거된다.
+enum _More { edit, completeNow, revert, next }
+
 class _SheetAction extends StatelessWidget {
   const _SheetAction({required this.label, required this.value});
 
   final String label;
-  final String value;
+  final _More value;
 
   @override
   Widget build(BuildContext context) {
```

`app/lib/features/visit/screens/visit_labels.dart`:

```diff
@@ -4,13 +4,13 @@ import '../api/visit_models.dart';
 // 시각·날짜 표기(hhmm·dayLabel·sameDay)는 core/time 에 있다. 이 모듈을 import 하던 곳이 그대로 쓰게 다시 내보낸다.
 export '../../../core/time/time_labels.dart';
 
-String statusLabel(String status) => switch (status) {
+String statusLabel(VisitStatus status) => switch (status) {
   VisitStatus.reserved => AppStrings.statusReserved,
   VisitStatus.inProgress => AppStrings.statusInProgress,
   VisitStatus.completed => AppStrings.statusCompleted,
   VisitStatus.canceled => AppStrings.statusCanceled,
   VisitStatus.noShow => AppStrings.statusNoShow,
-  _ => status,
+  VisitStatus.unknown => AppStrings.statusUnknown,
 };
 
 String warningLabel(String warning) => switch (warning) {
```

`app/lib/features/visit/state/day_layout.dart`:

```diff
@@ -29,7 +29,7 @@ class DayGroup {
   bool get occupiesTime => items.any((i) => i.visit.occupiesTime);
 
   /// 묶음의 상태가 모두 같으면 그 상태, 섞였으면 null.
-  String? get uniformStatus {
+  VisitStatus? get uniformStatus {
     final statuses = {for (final i in items) i.visit.status};
     return statuses.length == 1 ? statuses.single : null;
   }
@@ -44,7 +44,7 @@ class DayGroup {
   ];
 
   /// 진행 가능한 구성원의 상태가 하나면 그 상태(버튼을 낼 수 있다), 아니면 null.
-  String? get actionableStatus {
+  VisitStatus? get actionableStatus {
     final statuses = {for (final v in actionable) v.status};
     return statuses.length == 1 ? statuses.single : null;
   }
```

`app/lib/features/visit/state/visit_commands.dart`:

```diff
@@ -38,7 +38,7 @@ class VisitCommands {
   Future<List<Visit>> transition(
     int shopId, {
     required List<int> visitIds,
-    required String action,
+    required VisitAction action,
     String? cancelReason,
   }) => _visitWrite(
     () => _api.transition(
```

`app/lib/l10n/app_strings.dart`:

```diff
@@ -215,6 +215,7 @@ class AppStrings {
   // 예약·방문
   static const weekdaysShort = ['월', '화', '수', '목', '금', '토', '일'];
   static const statusReserved = '예약됨';
+  static const statusUnknown = '알 수 없음';
   static const statusInProgress = '미용 중';
   static const statusCompleted = '완료';
   static const statusCanceled = '취소';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/features/visit/api/visit_status_test.dart test/features/visit/screens/visit_detail_screen_test.dart test/features/visit/screens/day_screen_test.dart` → 전부 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 513 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `VisitStatus.fromCode`의 `orElse: () => VisitStatus.unknown`을 `VisitStatus.reserved`로 → `모르는 상태는 unknown 이고 화면은 "알 수 없음"으로 보인다` 실패.
- `occupiesTime`에서 `canceled`를 true 쪽으로 옮긴다 → `취소·노쇼만 빈 시간이다` 실패.
- `VisitAction.noShow`의 code 를 `'noshow'`로 → `행동의 서버 값은 그대로다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 방문 상태·행동을 enum 으로, 완료 후속 행동을 sealed 타입으로 — 문자열 switch 의 폴백을 없앤다(A1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 기기 설정 저장소를 키 기반 read/write 로, 보기 방식 컨트롤러를 하나로 — 설정이 늘어도 인터페이스·구현·컨트롤러를 복사하지 않는다 (A3)

**Files:**
- Modify: `app/lib/core/storage/prefs_store.dart`
- Create: `app/lib/core/storage/view_mode_controller.dart`
- Modify: `app/integration_test/visit_flow_test.dart`
- Modify: `app/lib/core/storage/token_store.dart`
- Modify: `app/lib/features/customer/state/customer_view_mode.dart`
- Modify: `app/lib/features/visit/state/day_view_mode.dart`
- Modify: `app/test/core/storage/stores_test.dart`
- Create: `app/test/core/storage/view_mode_controller_test.dart`
- Modify: `app/test/features/customer/screens/customer_list_tab_test.dart`
- Modify: `app/test/features/customer/state/customer_view_mode_test.dart`
- Modify: `app/test/features/visit/screens/day_screen_test.dart`
- Modify: `app/test/features/visit/state/day_view_mode_test.dart`

**Interfaces:**
- Consumes: `core/storage/prefs_store.dart`의 `PrefsStore`(항목마다 read/write 쌍 여섯), `features/customer/state/customer_view_mode.dart`·`features/visit/state/day_view_mode.dart`(복사본 컨트롤러 둘).
- Produces: `abstract class PrefsStore { Future<String?> read(String key); Future<void> write(String key, String value); Future<void> clear(); }` — `clear()`는 마지막 매장만 지운다(전과 같다); `abstract final class PrefsKeys { lastShopId = 'last_shop_id'; customerViewMode = 'customer_view_mode'; dayViewMode = 'day_view_mode'; }`(저장 키 문자열은 전과 같다 — 기기에 남은 값이 그대로 읽힌다); `extension LastShopPrefs on PrefsStore { Future<int?> readLastShopId(); Future<void> writeLastShopId(int) }`; `SecurePrefsStore`·`MemoryPrefsStore`. `lib/core/storage/view_mode_controller.dart` — `class ViewModeController<T extends Enum> extends AsyncNotifier<T> { ViewModeController({required String key, required List<T> values, required T fallback}); Future<T> build(); Future<void> select(T mode); }` — 저장된 이름이 값 목록에 없으면 `fallback`. `dayViewModeProvider`·`customerViewModeProvider`는 `AsyncNotifierProvider<ViewModeController<X>, X>(() => ViewModeController(key: PrefsKeys.…, values: X.values, fallback: X.list))` 한 줄이다.

감사 결과(설계 4.2 A3): 기기 설정 저장소가 항목마다 read/write 쌍을 인터페이스와 두 구현에 요구하고, 보기 방식 컨트롤러 둘이 복사본이라 [달력/피드] 토글(④-2)이 셋째 복사본이 될 참이었다. **설계와 다른 점**(결정 기록 007): `remove(key)`는 쓰는 곳이 없어 넣지 않았다. 저장 키 문자열은 전과 같아 이미 기기에 남은 값이 그대로 읽힌다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/integration_test/visit_flow_test.dart`:

```diff
@@ -1,3 +1,4 @@
+import 'package:chagocnote/core/storage/prefs_store.dart';
 // ③-A2 Task 12 Step 3 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 완료 기준
 // 12개를 확인한다. 확인마다 스크린샷을 찍고, 단언이 실패해도 다음 확인으로
 // 넘어가며, 마지막에 결과를 모아 찍는다.
@@ -485,8 +486,8 @@ void main() {
       await shot('02a-day-list');
       await tap(p(AppStrings.viewAsTimeline), after: const Duration(seconds: 1));
       await shot('02b-day-timeline');
-      final saved = await container.read(prefsStoreProvider).readDayViewMode();
-      note('시간표로 바꾼 뒤 PrefsStore.readDayViewMode() = $saved');
+      final saved = await container.read(prefsStoreProvider).read(PrefsKeys.dayViewMode);
+      note('시간표로 바꾼 뒤 PrefsStore.read(PrefsKeys.dayViewMode) = $saved');
       expect(saved, 'timeline');
       await tap(p(AppStrings.back));
       await waitFor(find.byKey(ScreenKeys.home));
@@ -499,7 +500,7 @@ void main() {
       await shot('02c-day-reopened-timeline');
       expect(idx, 1);
       await tap(p(AppStrings.viewAsList), after: const Duration(seconds: 1));
-      final back = await container.read(prefsStoreProvider).readDayViewMode();
+      final back = await container.read(prefsStoreProvider).read(PrefsKeys.dayViewMode);
       note('목록으로 되돌린 뒤 저장값 = $back');
       await shot('02d-day-list-again');
       expect(back, 'list');
```

`app/test/core/storage/stores_test.dart`:

```diff
@@ -21,19 +21,21 @@ void main() {
     expect(await prefs.readLastShopId(), isNull);
   });
 
-  test('고객 목록 보기 방식은 기억하고, 로그아웃 정리(clear)로 지워지지 않는다', () async {
+  test('키로 읽고 쓴다 — 설정이 늘어도 저장소 인터페이스는 그대로다', () async {
     final prefs = MemoryPrefsStore();
-    expect(await prefs.readCustomerViewMode(), isNull);
-    await prefs.writeCustomerViewMode('grid');
-    await prefs.clear();
-    expect(await prefs.readCustomerViewMode(), 'grid');
+    expect(await prefs.read('anything'), isNull);
+    await prefs.write('anything', 'value');
+    expect(await prefs.read('anything'), 'value');
   });
 
-  test('하루 화면 보기 방식은 기억하고, 로그아웃 정리(clear)로 지워지지 않는다', () async {
+  test('보기 방식 같은 기기 설정은 clear 가 지우지 않는다', () async {
     final prefs = MemoryPrefsStore();
-    expect(await prefs.readDayViewMode(), isNull);
-    await prefs.writeDayViewMode('timeline');
+    await prefs.write(PrefsKeys.customerViewMode, 'grid');
+    await prefs.write(PrefsKeys.dayViewMode, 'timeline');
+    await prefs.writeLastShopId(3);
     await prefs.clear();
-    expect(await prefs.readDayViewMode(), 'timeline');
+    expect(await prefs.read(PrefsKeys.customerViewMode), 'grid');
+    expect(await prefs.read(PrefsKeys.dayViewMode), 'timeline');
+    expect(await prefs.readLastShopId(), isNull);
   });
 }
```

`app/test/core/storage/view_mode_controller_test.dart`:

```dart
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/view_mode_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

enum _Mode { one, two }

final _provider = AsyncNotifierProvider<ViewModeController<_Mode>, _Mode>(
  () => ViewModeController(
    key: 'mode',
    values: _Mode.values,
    fallback: _Mode.one,
  ),
);

ProviderContainer _container(MemoryPrefsStore prefs) {
  final container = ProviderContainer(
    overrides: [prefsStoreProvider.overrideWithValue(prefs)],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('저장된 것이 없으면 기본값이다', () async {
    final container = _container(MemoryPrefsStore());
    expect(await container.read(_provider.future), _Mode.one);
  });

  test('고르면 바로 바뀌고 기기에 이름으로 남는다', () async {
    final prefs = MemoryPrefsStore();
    final container = _container(prefs);
    await container.read(_provider.future);
    await container.read(_provider.notifier).select(_Mode.two);
    expect(container.read(_provider).value, _Mode.two);
    expect(await prefs.read('mode'), 'two');
  });

  test('저장된 이름으로 시작하고, 모르는 이름이면 기본값이다', () async {
    final prefs = MemoryPrefsStore();
    await prefs.write('mode', 'two');
    expect(await _container(prefs).read(_provider.future), _Mode.two);

    final stale = MemoryPrefsStore();
    await stale.write('mode', 'three');
    expect(await _container(stale).read(_provider.future), _Mode.one);
  });
}
```

`app/test/features/customer/screens/customer_list_tab_test.dart`:

```diff
@@ -1,3 +1,4 @@
+import 'package:chagocnote/core/storage/prefs_store.dart';
 import 'dart:async';
 
 import 'package:chagocnote/core/router/screen_keys.dart';
@@ -86,7 +87,7 @@ void main() {
 
     expect(find.byKey(const Key('pet_tile_11')), findsOneWidget);
     expect(find.byKey(const Key('pet_row_11')), findsNothing);
-    expect(await setup.prefs.readCustomerViewMode(), 'grid');
+    expect(await setup.prefs.read(PrefsKeys.customerViewMode), 'grid');
   });
 
   testWidgets('기억한 보기가 격자면 격자로 시작한다', (tester) async {
@@ -94,7 +95,7 @@ void main() {
       (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
     );
     addTearDown(setup.container.dispose);
-    await setup.prefs.writeCustomerViewMode('grid');
+    await setup.prefs.write(PrefsKeys.customerViewMode, 'grid');
 
     await _openTab(tester, setup);
 
@@ -339,7 +340,7 @@ void main() {
         (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
       );
       addTearDown(setup.container.dispose);
-      if (grid) await setup.prefs.writeCustomerViewMode('grid');
+      if (grid) await setup.prefs.write(PrefsKeys.customerViewMode, 'grid');
 
       await _openTab(tester, setup);
```

`app/test/features/customer/state/customer_view_mode_test.dart`:

```diff
@@ -1,3 +1,4 @@
+import 'package:chagocnote/core/storage/prefs_store.dart';
 import 'package:chagocnote/features/customer/state/customer_view_mode.dart';
 import 'package:flutter_test/flutter_test.dart';
 
@@ -23,7 +24,7 @@ void main() {
       setup.container.read(customerViewModeProvider).value,
       CustomerViewMode.grid,
     );
-    expect(await setup.prefs.readCustomerViewMode(), 'grid');
+    expect(await setup.prefs.read(PrefsKeys.customerViewMode), 'grid');
   });
 
   test('기억한 것이 격자면 격자로 시작한다', () async {
@@ -31,7 +32,7 @@ void main() {
       (options, body) => const FakeResponse(statusCode: 500),
     );
     addTearDown(setup.container.dispose);
-    await setup.prefs.writeCustomerViewMode('grid');
+    await setup.prefs.write(PrefsKeys.customerViewMode, 'grid');
 
     expect(
       await setup.container.read(customerViewModeProvider.future),
```

`app/test/features/visit/screens/day_screen_test.dart`:

```diff
@@ -1,3 +1,4 @@
+import 'package:chagocnote/core/storage/prefs_store.dart';
 import 'dart:async';
 
 import 'package:chagocnote/core/router/screen_keys.dart';
@@ -434,7 +435,7 @@ void main() {
     await tester.tap(find.bySemanticsLabel(AppStrings.viewAsTimeline));
     await settle(tester);
 
-    expect(await setup.prefs.readDayViewMode(), 'timeline');
+    expect(await setup.prefs.read(PrefsKeys.dayViewMode), 'timeline');
     expect(find.text('10:00'), findsOneWidget);
     expect(find.text('19:00'), findsOneWidget);
     expect(find.text('Wednesday'), findsOneWidget);
@@ -450,7 +451,7 @@ void main() {
   testWidgets('기억한 것이 시간표면 시간표로 연다', (tester) async {
     final setup = CustomerTestSetup(_backend().call, overrides: _today);
     addTearDown(setup.container.dispose);
-    await setup.prefs.writeDayViewMode('timeline');
+    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
     await _open(tester, setup);
 
     expect(find.text('10:00'), findsOneWidget);
@@ -463,7 +464,7 @@ void main() {
       overrides: _today,
     );
     addTearDown(setup.container.dispose);
-    await setup.prefs.writeDayViewMode('timeline');
+    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
     await _open(tester, setup);
 
     expect(tester.takeException(), isNull);
@@ -481,7 +482,7 @@ void main() {
         );
     final setup = CustomerTestSetup(backend.call, overrides: _today);
     addTearDown(setup.container.dispose);
-    await setup.prefs.writeDayViewMode('timeline');
+    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
     await _open(tester, setup);
 
     expect(find.text('19:00'), findsOneWidget);
@@ -600,7 +601,7 @@ void main() {
   testWidgets('하루 시간표 골든', (tester) async {
     final setup = CustomerTestSetup(_backend().call, overrides: _today);
     addTearDown(setup.container.dispose);
-    await setup.prefs.writeDayViewMode('timeline');
+    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
     await _open(tester, setup);
     tester.view.physicalSize = const Size(390, 844);
     await tester.pumpAndSettle();
```

`app/test/features/visit/state/day_view_mode_test.dart`:

```diff
@@ -1,3 +1,4 @@
+import 'package:chagocnote/core/storage/prefs_store.dart';
 import 'package:chagocnote/features/visit/state/day_view_mode.dart';
 import 'package:flutter_test/flutter_test.dart';
 
@@ -23,7 +24,7 @@ void main() {
       setup.container.read(dayViewModeProvider).value,
       DayViewMode.timeline,
     );
-    expect(await setup.prefs.readDayViewMode(), 'timeline');
+    expect(await setup.prefs.read(PrefsKeys.dayViewMode), 'timeline');
   });
 
   test('기억한 것이 시간표면 시간표로 시작한다', () async {
@@ -31,7 +32,7 @@ void main() {
       (options, body) => const FakeResponse(statusCode: 500),
     );
     addTearDown(setup.container.dispose);
-    await setup.prefs.writeDayViewMode('timeline');
+    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
 
     expect(
       await setup.container.read(dayViewModeProvider.future),
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/core/storage/view_mode_controller_test.dart`
Expected: 컴파일 실패 — `lib/core/storage/view_mode_controller.dart` 없음.

- [ ] **Step 3: 구현한다**

`app/lib/core/storage/prefs_store.dart`:

```diff
@@ -1,80 +1,63 @@
 import 'package:flutter_secure_storage/flutter_secure_storage.dart';
 
-/// 기기에 남기는 작은 설정. "마지막으로 고른 매장"과 "고객 목록·하루 화면 보기 방식"이다.
+/// 기기에 남기는 작은 설정. 키로 읽고 쓴다 — 항목이 늘어도 인터페이스와 구현 둘을
+/// 고치지 않는다(설정마다 read/write 쌍을 늘리던 것을 대신한다).
 ///
 /// 저장소 패키지를 늘리지 않으려고 보안 저장소를 같이 쓴다.
 abstract class PrefsStore {
-  Future<int?> readLastShopId();
-  Future<void> writeLastShopId(int shopId);
+  Future<String?> read(String key);
+  Future<void> write(String key, String value);
 
-  /// 고객 목록 보기 방식('list' | 'grid'). 기기 설정이라 [clear]가 지우지 않는다.
-  Future<String?> readCustomerViewMode();
-  Future<void> writeCustomerViewMode(String mode);
-
-  /// 하루 화면 보기 방식('list' | 'timeline'). 기기 설정이라 [clear]가 지우지 않는다.
-  Future<String?> readDayViewMode();
-  Future<void> writeDayViewMode(String mode);
-
-  /// 마지막으로 고른 매장을 지운다(로그아웃·탈퇴).
+  /// 마지막으로 고른 매장을 지운다(로그아웃·탈퇴). 보기 방식 같은 기기 설정은 남긴다.
   Future<void> clear();
 }
 
-class SecurePrefsStore implements PrefsStore {
-  SecurePrefsStore([FlutterSecureStorage? storage])
-      : _storage = storage ?? const FlutterSecureStorage();
+/// 잘 알려진 키. 새 설정은 여기에 키만 더한다.
+abstract final class PrefsKeys {
+  static const lastShopId = 'last_shop_id';
 
-  static const _lastShopKey = 'last_shop_id';
-  static const _customerViewModeKey = 'customer_view_mode';
-  static const _dayViewModeKey = 'day_view_mode';
-  final FlutterSecureStorage _storage;
+  /// 고객 목록 보기 방식('list' | 'grid').
+  static const customerViewMode = 'customer_view_mode';
 
-  @override
-  Future<int?> readLastShopId() async => int.tryParse(await _storage.read(key: _lastShopKey) ?? '');
+  /// 하루 화면 보기 방식('list' | 'timeline').
+  static const dayViewMode = 'day_view_mode';
+}
 
-  @override
-  Future<void> writeLastShopId(int shopId) => _storage.write(key: _lastShopKey, value: '$shopId');
+/// 마지막으로 고른 매장 — 정수로 읽고 쓴다.
+extension LastShopPrefs on PrefsStore {
+  Future<int?> readLastShopId() async =>
+      int.tryParse(await read(PrefsKeys.lastShopId) ?? '');
 
-  @override
-  Future<String?> readCustomerViewMode() => _storage.read(key: _customerViewModeKey);
+  Future<void> writeLastShopId(int shopId) =>
+      write(PrefsKeys.lastShopId, '$shopId');
+}
 
-  @override
-  Future<void> writeCustomerViewMode(String mode) =>
-      _storage.write(key: _customerViewModeKey, value: mode);
+class SecurePrefsStore implements PrefsStore {
+  SecurePrefsStore([FlutterSecureStorage? storage])
+    : _storage = storage ?? const FlutterSecureStorage();
+
+  final FlutterSecureStorage _storage;
 
   @override
-  Future<String?> readDayViewMode() => _storage.read(key: _dayViewModeKey);
+  Future<String?> read(String key) => _storage.read(key: key);
 
   @override
-  Future<void> writeDayViewMode(String mode) =>
-      _storage.write(key: _dayViewModeKey, value: mode);
+  Future<void> write(String key, String value) =>
+      _storage.write(key: key, value: value);
 
   @override
-  Future<void> clear() => _storage.delete(key: _lastShopKey);
+  Future<void> clear() => _storage.delete(key: PrefsKeys.lastShopId);
 }
 
 class MemoryPrefsStore implements PrefsStore {
-  int? _lastShopId;
-  String? _customerViewMode;
-  String? _dayViewMode;
-
-  @override
-  Future<int?> readLastShopId() async => _lastShopId;
-
-  @override
-  Future<void> writeLastShopId(int shopId) async => _lastShopId = shopId;
-
-  @override
-  Future<String?> readCustomerViewMode() async => _customerViewMode;
-
-  @override
-  Future<void> writeCustomerViewMode(String mode) async => _customerViewMode = mode;
+  final _values = <String, String>{};
 
   @override
-  Future<String?> readDayViewMode() async => _dayViewMode;
+  Future<String?> read(String key) async => _values[key];
 
   @override
-  Future<void> writeDayViewMode(String mode) async => _dayViewMode = mode;
+  Future<void> write(String key, String value) async => _values[key] = value;
 
   @override
-  Future<void> clear() async => _lastShopId = null;
+  Future<void> clear() async => _values.remove(PrefsKeys.lastShopId);
 }
```

`app/lib/core/storage/view_mode_controller.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../proxy/providers.dart';

/// "보기 방식"처럼 enum 하나를 기기에 기억하는 컨트롤러. 기능마다 복사하던 것을
/// 하나로 — 새 토글은 키·값 목록·기본값만 주면 된다.
///
/// 기본값은 [fallback]이고, 저장된 이름이 값 목록에 없으면(옛 버전·오타) 기본값이다.
class ViewModeController<T extends Enum> extends AsyncNotifier<T> {
  ViewModeController({
    required this.key,
    required this.values,
    required this.fallback,
  });

  final String key;
  final List<T> values;
  final T fallback;

  @override
  Future<T> build() async {
    final saved = await ref.read(prefsStoreProvider).read(key);
    return values.firstWhere((v) => v.name == saved, orElse: () => fallback);
  }

  Future<void> select(T mode) async {
    state = AsyncData(mode);
    await ref.read(prefsStoreProvider).write(key, mode.name);
  }
}
```

`app/lib/core/storage/token_store.dart`:

```diff
@@ -11,7 +11,7 @@ abstract class TokenStore {
 /// flutter_secure_storage 로 토큰을 보관하는 구현체.
 class SecureTokenStore implements TokenStore {
   SecureTokenStore({FlutterSecureStorage? storage})
-      : _storage = storage ?? const FlutterSecureStorage();
+    : _storage = storage ?? const FlutterSecureStorage();
 
   static const _accessKey = 'access_token';
   static const _refreshKey = 'refresh_token';
```

`app/lib/features/customer/state/customer_view_mode.dart`:

```diff
@@ -1,27 +1,20 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../../core/proxy/providers.dart';
+import '../../../core/storage/prefs_store.dart';
+import '../../../core/storage/view_mode_controller.dart';
 
 enum CustomerViewMode { list, grid }
 
 /// 고객 목록의 보기 방식. 기본은 목록이고, 마지막으로 고른 것을 기기에
 /// 기억한다(설계 2절).
-class CustomerViewModeController extends AsyncNotifier<CustomerViewMode> {
-  @override
-  Future<CustomerViewMode> build() async {
-    final saved = await ref.read(prefsStoreProvider).readCustomerViewMode();
-    return saved == CustomerViewMode.grid.name
-        ? CustomerViewMode.grid
-        : CustomerViewMode.list;
-  }
-
-  Future<void> select(CustomerViewMode mode) async {
-    state = AsyncData(mode);
-    await ref.read(prefsStoreProvider).writeCustomerViewMode(mode.name);
-  }
-}
-
 final customerViewModeProvider =
-    AsyncNotifierProvider<CustomerViewModeController, CustomerViewMode>(
-      CustomerViewModeController.new,
+    AsyncNotifierProvider<
+      ViewModeController<CustomerViewMode>,
+      CustomerViewMode
+    >(
+      () => ViewModeController(
+        key: PrefsKeys.customerViewMode,
+        values: CustomerViewMode.values,
+        fallback: CustomerViewMode.list,
+      ),
     );
```

`app/lib/features/visit/state/day_view_mode.dart`:

```diff
@@ -1,27 +1,17 @@
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
-import '../../../core/proxy/providers.dart';
+import '../../../core/storage/prefs_store.dart';
+import '../../../core/storage/view_mode_controller.dart';
 
 enum DayViewMode { list, timeline }
 
 /// 하루 화면의 보기 방식. 기본은 목록이고, 마지막으로 고른 것을 기기에
 /// 기억한다(설계 2절).
-class DayViewModeController extends AsyncNotifier<DayViewMode> {
-  @override
-  Future<DayViewMode> build() async {
-    final saved = await ref.read(prefsStoreProvider).readDayViewMode();
-    return saved == DayViewMode.timeline.name
-        ? DayViewMode.timeline
-        : DayViewMode.list;
-  }
-
-  Future<void> select(DayViewMode mode) async {
-    state = AsyncData(mode);
-    await ref.read(prefsStoreProvider).writeDayViewMode(mode.name);
-  }
-}
-
 final dayViewModeProvider =
-    AsyncNotifierProvider<DayViewModeController, DayViewMode>(
-      DayViewModeController.new,
+    AsyncNotifierProvider<ViewModeController<DayViewMode>, DayViewMode>(
+      () => ViewModeController(
+        key: PrefsKeys.dayViewMode,
+        values: DayViewMode.values,
+        fallback: DayViewMode.list,
+      ),
     );
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/core/storage/view_mode_controller_test.dart test/core/storage/stores_test.dart test/features/customer/state/customer_view_mode_test.dart test/features/visit/state/day_view_mode_test.dart` → 전부 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 516 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `ViewModeController.build`가 `return fallback;`만 한다 → `저장된 이름으로 시작하고, 모르는 이름이면 기본값이다` 실패.
- `ViewModeController.select`에서 `prefs.write(...)` 줄을 뺀다 → `고르면 바로 바뀌고 기기에 이름으로 남는다` 실패.
- `MemoryPrefsStore.clear()`가 `_values.clear()`로 전부 지운다 → `stores_test.dart::보기 방식 같은 기기 설정은 clear 가 지우지 않는다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 기기 설정 저장소를 키 기반 read/write 로, 보기 방식 컨트롤러를 하나로 — 설정이 늘어도 인터페이스·구현·컨트롤러를 복사하지 않는다(A3)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 홈 탭을 목록 하나로 정의하고, 라우터의 매장 범위 가드를 기본값으로 뒤집는다 — 계정 경로만 예외로 열거하고 나머지는 전부 매장 범위다 (A7·A8)

**Files:**
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/lib/features/home/screens/home_shell.dart`
- Modify: `app/test/core/router/app_router_test.dart`

**Interfaces:**
- Consumes: `features/home/screens/home_shell.dart`(`_items`·FAB `switch`·머리 조건·`_TabBody` 네 곳), `core/router/app_router.dart`의 `_shopScopedSettings`·접두사 목록 `_isShopScoped`·`_accountExemptRoutes`.
- Produces: `home_shell.dart` 안 비공개 `class _HomeTab { AppGlassBarItem item; Widget body; _TabFab? fab; bool ownsHeader; }`와 `late final List<_HomeTab> _tabs`(캘린더·고객·매출 순, 매출은 FAB 없음 → 준비 중 시트). 탭 추가는 목록에 한 줄. `app_router.dart` — `const accountRoutes = {'/settings/account', '/settings/account/withdraw'};`(공개 — 테스트가 라우터 경로와 대조한다), `_isShopScoped`와 그 분기 삭제. `_redirectSignedIn`: 매장 0 → `/invite`(계정 경로 제외), 매장 ≥2 이고 선택 없음 → `/shops/select`(계정 경로 제외), 진입 화면은 `/home`. `app_router_test.dart`의 새 테스트는 `router.configuration.routes.whereType<GoRoute>()`를 전부 돌며(`:param` → `1`) 계정 경로와 `/shops/select` 밖은 `/shops/select`로 밀리는지 본다.

감사 결과(설계 4.2 A7·A8): 홈 셸은 탭 하나 더하면 네 곳을 고쳐야 했고, 라우터의 매장 범위 가드는 접두사 목록이라 새 경로를 잊으면 가드가 빠졌다. **설계와 다른 점**(결정 기록 007): 가드는 "열린 경로 목록"조차 두지 않는다 — 옛 `_isShopScoped` 분기는 매장이 하나면 세션이 자동으로 고르므로(`SessionController._resolveWith`) 닿을 수 없는 코드였다. 참조 구현의 변이 검사에서 가드를 꺼도 테스트가 통과해 드러났고, 지웠다. "선택 없음"은 매장이 둘 이상일 때뿐이고 그때는 계정 경로 밖 전부가 매장 선택으로 밀린다. `_HomeTab`은 밖에서 쓸 일이 없어 비공개다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/core/router/app_router_test.dart`:

```diff
@@ -11,6 +11,7 @@ import 'package:dio/dio.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
+import 'package:go_router/go_router.dart';
 
 import '../../support/fake_http_client_adapter.dart';
 import '../../support/fake_session_gateway.dart';
@@ -19,12 +20,12 @@ const _ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
 const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');
 
 Me _me({List<ShopMembership> shops = const []}) => Me(
-      id: 1,
-      displayName: '민석',
-      profileImageUrl: null,
-      identities: const ['apple'],
-      shops: shops,
-    );
+  id: 1,
+  displayName: '민석',
+  profileImageUrl: null,
+  identities: const ['apple'],
+  shops: shops,
+);
 
 /// `MaterialApp.router`로 실제 앱과 같은 방식으로 라우터를 꽂는다.
 /// [container]를 직접 받아서, 위젯 트리 바깥에서도 컨트롤러/라우터를
@@ -44,15 +45,14 @@ Widget _appWith(ProviderContainer container) {
 ProviderContainer _containerWith(
   SessionGateway gateway, {
   ApiClient Function(Ref ref)? apiClientBuilder,
-}) =>
-    ProviderContainer.test(
-      retry: (retryCount, error) => null,
-      overrides: [
-        sessionGatewayProvider.overrideWithValue(gateway),
-        if (apiClientBuilder != null)
-          apiClientProvider.overrideWith(apiClientBuilder),
-      ],
-    );
+}) => ProviderContainer.test(
+  retry: (retryCount, error) => null,
+  overrides: [
+    sessionGatewayProvider.overrideWithValue(gateway),
+    if (apiClientBuilder != null)
+      apiClientProvider.overrideWith(apiClientBuilder),
+  ],
+);
 
 void main() {
   testWidgets('로그아웃 상태면 로그인 화면으로 간다', (tester) async {
@@ -85,31 +85,30 @@ void main() {
     expect(find.byKey(ScreenKeys.home), findsOneWidget);
   });
 
-  testWidgets(
-    '매장이 둘이고 선택된 게 없으면 매장 선택 화면으로 가고, 고른 뒤 홈으로 이동하면 그대로 머무른다',
-    (tester) async {
-      // `/shops/select`는 매장을 이미 가진 사용자도 다시 열 수 있어야 하므로
-      // (설정에서 매장 전환) 선택만으로 라우터가 자동으로 홈으로 밀어내지
-      // 않는다 — 실제 화면이라면 선택 버튼의 onPressed가 `/home`으로 이동
-      // 시킬 것이다. 지금은 자리 표시 화면이라 그 이동을 직접 흉내낸다.
-      final gateway = FakeSessionGateway()
-        ..meOnRestore = _me(shops: [_ownerA, _staffB]);
-      final container = _containerWith(gateway);
-
-      await tester.pumpWidget(_appWith(container));
-      await tester.pumpAndSettle();
-      expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
+  testWidgets('매장이 둘이고 선택된 게 없으면 매장 선택 화면으로 가고, 고른 뒤 홈으로 이동하면 그대로 머무른다', (
+    tester,
+  ) async {
+    // `/shops/select`는 매장을 이미 가진 사용자도 다시 열 수 있어야 하므로
+    // (설정에서 매장 전환) 선택만으로 라우터가 자동으로 홈으로 밀어내지
+    // 않는다 — 실제 화면이라면 선택 버튼의 onPressed가 `/home`으로 이동
+    // 시킬 것이다. 지금은 자리 표시 화면이라 그 이동을 직접 흉내낸다.
+    final gateway = FakeSessionGateway()
+      ..meOnRestore = _me(shops: [_ownerA, _staffB]);
+    final container = _containerWith(gateway);
 
-      await container
-          .read(sessionControllerProvider.notifier)
-          .selectShop(_staffB.shopId);
-      container.read(routerProvider).go('/home');
-      await tester.pumpAndSettle();
+    await tester.pumpWidget(_appWith(container));
+    await tester.pumpAndSettle();
+    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
 
-      expect(find.byKey(ScreenKeys.home), findsOneWidget);
-      expect(gateway.writtenShopId, _staffB.shopId);
-    },
-  );
+    await container
+        .read(sessionControllerProvider.notifier)
+        .selectShop(_staffB.shopId);
+    container.read(routerProvider).go('/home');
+    await tester.pumpAndSettle();
+
+    expect(find.byKey(ScreenKeys.home), findsOneWidget);
+    expect(gateway.writtenShopId, _staffB.shopId);
+  });
 
   testWidgets('기억해둔 매장 id 가 있으면 매장 선택 화면을 건너뛰고 홈으로 간다', (tester) async {
     final gateway = FakeSessionGateway()
@@ -124,26 +123,22 @@ void main() {
     expect(find.byKey(ScreenKeys.shopSelect), findsNothing);
   });
 
-  testWidgets(
-    '복원이 네트워크 오류로 실패하면 스플래시에 머무르고, '
-    '다시 시도해서 성공하면 홈으로 간다',
-    (tester) async {
-      final gateway = FakeSessionGateway()
-        ..restoreError = Exception('네트워크 오류');
-      final container = _containerWith(gateway);
+  testWidgets('복원이 네트워크 오류로 실패하면 스플래시에 머무르고, '
+      '다시 시도해서 성공하면 홈으로 간다', (tester) async {
+    final gateway = FakeSessionGateway()..restoreError = Exception('네트워크 오류');
+    final container = _containerWith(gateway);
 
-      await tester.pumpWidget(_appWith(container));
-      await tester.pumpAndSettle();
-      expect(find.byKey(ScreenKeys.splash), findsOneWidget);
+    await tester.pumpWidget(_appWith(container));
+    await tester.pumpAndSettle();
+    expect(find.byKey(ScreenKeys.splash), findsOneWidget);
 
-      gateway.restoreError = null;
-      gateway.meOnRestore = _me(shops: [_ownerA]);
-      container.invalidate(sessionControllerProvider);
-      await tester.pumpAndSettle();
+    gateway.restoreError = null;
+    gateway.meOnRestore = _me(shops: [_ownerA]);
+    container.invalidate(sessionControllerProvider);
+    await tester.pumpAndSettle();
 
-      expect(find.byKey(ScreenKeys.home), findsOneWidget);
-    },
-  );
+    expect(find.byKey(ScreenKeys.home), findsOneWidget);
+  });
 
   testWidgets('홈에 있는 중 endSession 이 호출되면 로그인 화면으로 밀려난다', (tester) async {
     final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
@@ -203,89 +198,83 @@ void main() {
     expect(find.byKey(ScreenKeys.invite), findsOneWidget);
   });
 
-  testWidgets(
-    '매장 전환 뒤에도 라우터는 다시 만들어지지 않고 현재 화면에 그대로 머무른다',
-    (tester) async {
-      // 이 테스트는 "redirect 안에서는 ref.read만 쓴다" 규칙을 지킨다.
-      // routerProvider 본문에서 세션을 ref.watch 하면 세션이 바뀔 때마다
-      // GoRouter가 새로 만들어지므로(=내비게이션 스택이 리셋되므로) 이
-      // identical 비교가 실패한다.
-      final gateway = FakeSessionGateway()
-        ..meOnRestore = _me(shops: [_ownerA, _staffB])
-        ..lastShopId = _ownerA.shopId;
-      // `/settings/members`는 이제 실제 화면이라 매장 API를 부른다. 실제
-      // 네트워크로 나가 pumpAndSettle이 멎지 않도록 가짜 어댑터를 문
-      // apiClientProvider로 덮어쓴다.
-      final adapter = FakeHttpClientAdapter(
-        (options, body) =>
-            const FakeResponse(statusCode: 200, data: <dynamic>[]),
-      );
-      final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
-      final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
-      final container = _containerWith(
-        gateway,
-        apiClientBuilder: (ref) => ApiClient(
-          tokenStore: MemoryTokenStore(),
-          dio: dio,
-          refreshDio: refreshDio,
-          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
-        ),
-      );
+  testWidgets('매장 전환 뒤에도 라우터는 다시 만들어지지 않고 현재 화면에 그대로 머무른다', (tester) async {
+    // 이 테스트는 "redirect 안에서는 ref.read만 쓴다" 규칙을 지킨다.
+    // routerProvider 본문에서 세션을 ref.watch 하면 세션이 바뀔 때마다
+    // GoRouter가 새로 만들어지므로(=내비게이션 스택이 리셋되므로) 이
+    // identical 비교가 실패한다.
+    final gateway = FakeSessionGateway()
+      ..meOnRestore = _me(shops: [_ownerA, _staffB])
+      ..lastShopId = _ownerA.shopId;
+    // `/settings/members`는 이제 실제 화면이라 매장 API를 부른다. 실제
+    // 네트워크로 나가 pumpAndSettle이 멎지 않도록 가짜 어댑터를 문
+    // apiClientProvider로 덮어쓴다.
+    final adapter = FakeHttpClientAdapter(
+      (options, body) => const FakeResponse(statusCode: 200, data: <dynamic>[]),
+    );
+    final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
+    final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
+    final container = _containerWith(
+      gateway,
+      apiClientBuilder: (ref) => ApiClient(
+        tokenStore: MemoryTokenStore(),
+        dio: dio,
+        refreshDio: refreshDio,
+        onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
+      ),
+    );
 
-      await tester.pumpWidget(_appWith(container));
-      await tester.pumpAndSettle();
+    await tester.pumpWidget(_appWith(container));
+    await tester.pumpAndSettle();
 
-      final router = container.read(routerProvider);
-      router.go('/settings/members');
-      await tester.pumpAndSettle();
-      expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
+    final router = container.read(routerProvider);
+    router.go('/settings/members');
+    await tester.pumpAndSettle();
+    expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
 
-      await container
-          .read(sessionControllerProvider.notifier)
-          .selectShop(_staffB.shopId);
-      await tester.pumpAndSettle();
+    await container
+        .read(sessionControllerProvider.notifier)
+        .selectShop(_staffB.shopId);
+    await tester.pumpAndSettle();
 
-      expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
-      expect(identical(container.read(routerProvider), router), isTrue);
-    },
-  );
+    expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
+    expect(identical(container.read(routerProvider), router), isTrue);
+  });
 
-  testWidgets(
-    '홈 → 설정 버튼 → 설정 화면 → 뒤로 → 홈 (홈은 쌓인 채라 탭 상태를 유지한다)',
-    (tester) async {
-      // 설정으로 갈 때 push(쌓기)를 쓰는지 확인하려고, 홈에서 탭을 바꿔 둔
-      // 뒤 설정에 들어갔다 돌아왔을 때도 그 탭이 그대로인지를 본다. go로
-      // 이동했다면 홈이 통째로 다시 만들어져 탭이 첫 화면으로 리셋된다.
-      final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
-      final container = _containerWith(gateway);
-      addTearDown(container.dispose);
-
-      await tester.pumpWidget(_appWith(container));
-      await tester.pumpAndSettle();
-      expect(find.byKey(ScreenKeys.home), findsOneWidget);
+  testWidgets('홈 → 설정 버튼 → 설정 화면 → 뒤로 → 홈 (홈은 쌓인 채라 탭 상태를 유지한다)', (
+    tester,
+  ) async {
+    // 설정으로 갈 때 push(쌓기)를 쓰는지 확인하려고, 홈에서 탭을 바꿔 둔
+    // 뒤 설정에 들어갔다 돌아왔을 때도 그 탭이 그대로인지를 본다. go로
+    // 이동했다면 홈이 통째로 다시 만들어져 탭이 첫 화면으로 리셋된다.
+    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
+    final container = _containerWith(gateway);
+    addTearDown(container.dispose);
 
-      // 고객 탭은 머리에 설정 버튼이 없다(자기 머리를 쓴다) — 매출 탭으로 본다.
-      await tester.tap(find.text(AppStrings.tabSales));
-      await tester.pumpAndSettle();
-      expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
+    await tester.pumpWidget(_appWith(container));
+    await tester.pumpAndSettle();
+    expect(find.byKey(ScreenKeys.home), findsOneWidget);
 
-      await tester.tap(find.bySemanticsLabel(AppStrings.settingsLabel));
-      await tester.pumpAndSettle();
-      expect(find.byKey(ScreenKeys.settings), findsOneWidget);
+    // 고객 탭은 머리에 설정 버튼이 없다(자기 머리를 쓴다) — 매출 탭으로 본다.
+    await tester.tap(find.text(AppStrings.tabSales));
+    await tester.pumpAndSettle();
+    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
 
-      await tester.tap(find.bySemanticsLabel(AppStrings.back));
-      await tester.pumpAndSettle();
+    await tester.tap(find.bySemanticsLabel(AppStrings.settingsLabel));
+    await tester.pumpAndSettle();
+    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
 
-      expect(find.byKey(ScreenKeys.home), findsOneWidget);
-      expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
-    },
-  );
+    await tester.tap(find.bySemanticsLabel(AppStrings.back));
+    await tester.pumpAndSettle();
+
+    expect(find.byKey(ScreenKeys.home), findsOneWidget);
+    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
+  });
 
   testWidgets('설정 → 멤버 → 뒤로 → 설정', (tester) async {
     final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
     final adapter = FakeHttpClientAdapter(
-      (options, body) =>
-          const FakeResponse(statusCode: 200, data: <dynamic>[]),
+      (options, body) => const FakeResponse(statusCode: 200, data: <dynamic>[]),
     );
     final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
     final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
@@ -315,6 +304,41 @@ void main() {
     expect(find.byKey(ScreenKeys.settings), findsOneWidget);
   });
 
+  testWidgets('계정 경로 밖의 모든 경로는 매장 선택이 없으면 매장 선택으로 밀려난다', (tester) async {
+    // 매장 범위가 기본값이다 — 새 경로를 더하고 가드를 잊는 실수가 없게, 라우터의 경로를 전부 돈다.
+    // 매장 선택 화면 자신만 제자리다.
+    final gateway = FakeSessionGateway()
+      ..meOnRestore = _me(shops: [_ownerA, _staffB]);
+    final container = _containerWith(gateway);
+    addTearDown(container.dispose);
+
+    await tester.pumpWidget(_appWith(container));
+    await tester.pumpAndSettle();
+    final router = container.read(routerProvider);
+    final paths = [
+      for (final route in router.configuration.routes.whereType<GoRoute>())
+        route.path,
+    ];
+    expect(
+      paths.toSet().containsAll(accountRoutes),
+      isTrue,
+      reason: '계정 경로 목록에 라우터에 없는 경로가 있다: $accountRoutes',
+    );
+
+    final scoped = paths.where(
+      (p) => !accountRoutes.contains(p) && p != '/shops/select',
+    );
+    for (final path in scoped) {
+      router.go(path.replaceAll(RegExp(r':[a-zA-Z]+'), '1'));
+      await tester.pumpAndSettle();
+      expect(
+        router.state.uri.path,
+        '/shops/select',
+        reason: '$path 가 매장 범위로 막히지 않았다',
+      );
+    }
+  });
+
   testWidgets('매장이 둘이고 선택이 없을 때 /pets/1·/customers/new 로 가면 매장 선택으로 밀려난다', (
     tester,
   ) async {
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/core/router/app_router_test.dart`
Expected: 컴파일 실패 — `accountRoutes` 가 없다(`Undefined name 'accountRoutes'`).

- [ ] **Step 3: 구현한다**

`app/lib/core/router/app_router.dart`:

```diff
@@ -34,25 +34,11 @@ class _SessionRefreshListenable extends ChangeNotifier {
   void ping() => notifyListeners();
 }
 
-/// 매장이 선택되어 있어야만 열리는 경로.
-const _shopScopedSettings = {
-  '/settings',
-  '/settings/members',
-  '/settings/shop',
-  '/settings/schedule',
-  '/settings/menus',
-};
-
-/// 고객·반려동물·방문 화면도 매장이 선택되어 있어야 열린다(경로에 ID 가 들어간다).
-bool _isShopScoped(String location) =>
-    _shopScopedSettings.contains(location) ||
-    location.startsWith('/customers/') ||
-    location.startsWith('/pets/') ||
-    location.startsWith('/visits/');
-
-/// 매장이 없어도(0-shop 사용자도) 열려 있어야 하는 계정 관련 경로 — 로그아웃,
-/// 로그인 수단 해제, 탈퇴는 매장 유무와 무관하게 가능해야 한다.
-const _accountExemptRoutes = {'/settings/account', '/settings/account/withdraw'};
+/// 매장을 고르지 않아도 열리는 계정 경로 — 로그아웃, 로그인 수단 해제, 탈퇴는 매장 유무와 무관하게
+/// 가능해야 한다. **이 밖의 모든 경로는 매장 범위다**(기본이 매장 범위라 새 경로를 더하며 가드를 잊을 수
+/// 없다). `test/core/router/app_router_test.dart`가 라우터의 경로를 전부 돌며 이 목록 밖은 매장 선택으로
+/// 밀리는지 확인한다.
+const accountRoutes = {'/settings/account', '/settings/account/withdraw'};
 
 /// 로그인/스플래시처럼 "머물 이유가 없는" 진입 화면. 로그인된 사용자가
 /// 여기 있으면 홈으로 밀어낸다. `/invite`, `/shops/select`는 매장을 이미 가진
@@ -85,16 +71,22 @@ final routerProvider = Provider<GoRouter>((ref) {
       return switch (session.value) {
         null || SignedOut() => location == '/login' ? null : '/login',
         SignedIn(:final me, :final selectedShopId) => _redirectSignedIn(
-            location: location,
-            shopCount: me.shops.length,
-            selectedShopId: selectedShopId,
-          ),
+          location: location,
+          shopCount: me.shops.length,
+          selectedShopId: selectedShopId,
+        ),
       };
     },
     routes: [
-      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
+      GoRoute(
+        path: '/splash',
+        builder: (context, state) => const SplashScreen(),
+      ),
       GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
-      GoRoute(path: '/invite', builder: (context, state) => const InviteCodeScreen()),
+      GoRoute(
+        path: '/invite',
+        builder: (context, state) => const InviteCodeScreen(),
+      ),
       GoRoute(
         path: '/shops/select',
         builder: (context, state) => const ShopSelectScreen(),
@@ -130,9 +122,8 @@ final routerProvider = Provider<GoRouter>((ref) {
       ),
       GoRoute(
         path: '/pets/:petId',
-        builder: (context, state) => PetDetailScreen(
-          petId: int.parse(state.pathParameters['petId']!),
-        ),
+        builder: (context, state) =>
+            PetDetailScreen(petId: int.parse(state.pathParameters['petId']!)),
       ),
       GoRoute(
         path: '/pets/:petId/edit',
@@ -174,8 +165,7 @@ final routerProvider = Provider<GoRouter>((ref) {
       ),
       GoRoute(
         path: '/visits/draft',
-        builder: (context, state) =>
-            DraftScreen(text: state.extra as String),
+        builder: (context, state) => DraftScreen(text: state.extra as String),
       ),
       GoRoute(
         path: '/visits/day/:date',
@@ -208,19 +198,15 @@ String? _redirectSignedIn({
   required int? selectedShopId,
 }) {
   if (shopCount == 0) {
-    if (_accountExemptRoutes.contains(location)) return null;
+    if (accountRoutes.contains(location)) return null;
     return location == '/invite' ? null : '/invite';
   }
 
   if (shopCount >= 2 && selectedShopId == null) {
-    if (_accountExemptRoutes.contains(location)) return null;
+    if (accountRoutes.contains(location)) return null;
     return location == '/shops/select' ? null : '/shops/select';
   }
 
-  if (_isShopScoped(location) && selectedShopId == null) {
-    return '/home';
-  }
-
   if (_entryOnlyRoutes.contains(location)) {
     return '/home';
   }
```

`app/lib/features/home/screens/home_shell.dart`:

```diff
@@ -19,6 +19,33 @@ import '../../visit/screens/calendar_tab.dart';
 import '../../visit/state/calendar_selection.dart';
 import '../../../core/time/today_provider.dart';
 
+/// 홈 탭 하나 — 탭바 항목, 본문, + 버튼(없으면 준비 중 안내), 머리를 스스로 그리는지.
+/// 탭을 더하면 [_HomeShellState._tabs]에 한 줄이다 — 탭바·본문·FAB·머리가 따라온다.
+class _HomeTab {
+  const _HomeTab({
+    required this.item,
+    required this.body,
+    this.fab,
+    this.ownsHeader = false,
+  });
+
+  final AppGlassBarItem item;
+  final Widget body;
+
+  /// + 버튼. null 이면 "준비 중" 안내 시트를 띄운다.
+  final _TabFab? fab;
+
+  /// 탭이 자기 머리(달력의 월·화살표, 고객의 제목·보기 전환)를 그리면 셸의 머리를 숨긴다.
+  final bool ownsHeader;
+}
+
+class _TabFab {
+  const _TabFab({required this.semanticLabel, required this.onPressed});
+
+  final String semanticLabel;
+  final VoidCallback onPressed;
+}
+
 /// 홈 화면. 헤더(날짜 + 매장 이름 + 설정), 탭별 본문, 하단 유리 탭바로
 /// 이루어진다.
 class HomeShell extends ConsumerStatefulWidget {
@@ -29,15 +56,40 @@ class HomeShell extends ConsumerStatefulWidget {
 }
 
 class _HomeShellState extends ConsumerState<HomeShell> {
-  static const _calendarTab = 0;
-  static const _customersTab = 1;
-
   int _tabIndex = 0;
 
-  static const _items = [
-    AppGlassBarItem(icon: Icons.calendar_today, label: AppStrings.tabCalendar),
-    AppGlassBarItem(icon: Icons.people_outline, label: AppStrings.tabCustomers),
-    AppGlassBarItem(icon: Icons.bar_chart_outlined, label: AppStrings.tabSales),
+  late final List<_HomeTab> _tabs = [
+    _HomeTab(
+      item: const AppGlassBarItem(
+        icon: Icons.calendar_today,
+        label: AppStrings.tabCalendar,
+      ),
+      body: const CalendarTab(),
+      ownsHeader: true,
+      fab: _TabFab(
+        semanticLabel: AppStrings.addReservation,
+        onPressed: _reserve,
+      ),
+    ),
+    _HomeTab(
+      item: const AppGlassBarItem(
+        icon: Icons.people_outline,
+        label: AppStrings.tabCustomers,
+      ),
+      body: const CustomerListTab(),
+      ownsHeader: true,
+      fab: _TabFab(
+        semanticLabel: AppStrings.registerCustomer,
+        onPressed: () => context.push('/customers/new'),
+      ),
+    ),
+    const _HomeTab(
+      item: AppGlassBarItem(
+        icon: Icons.bar_chart_outlined,
+        label: AppStrings.tabSales,
+      ),
+      body: Center(child: _EmptyState(title: AppStrings.comingSoonEmptyTitle)),
+    ),
   ];
 
   void _openComingSoonSheet() {
@@ -69,21 +121,15 @@ class _HomeShellState extends ConsumerState<HomeShell> {
   Widget build(BuildContext context) {
     final today = ref.watch(todayProvider);
     final shopName = ref.watch(shopNameProvider);
+    final tab = _tabs[_tabIndex];
+    final fab = tab.fab;
 
     return Scaffold(
       key: ScreenKeys.home,
       extendBody: true,
-      floatingActionButton: switch (_tabIndex) {
-        _calendarTab => AppFab(
-          semanticLabel: AppStrings.addReservation,
-          onPressed: _reserve,
-        ),
-        _customersTab => AppFab(
-          semanticLabel: AppStrings.registerCustomer,
-          onPressed: () => context.push('/customers/new'),
-        ),
-        _ => AppFab(onPressed: _openComingSoonSheet),
-      },
+      floatingActionButton: fab == null
+          ? AppFab(onPressed: _openComingSoonSheet)
+          : AppFab(semanticLabel: fab.semanticLabel, onPressed: fab.onPressed),
       bottomNavigationBar: Padding(
         padding: const EdgeInsets.fromLTRB(
           AppSpacing.lg,
@@ -94,7 +140,7 @@ class _HomeShellState extends ConsumerState<HomeShell> {
         child: SafeArea(
           top: false,
           child: AppGlassBar(
-            items: _items,
+            items: [for (final t in _tabs) t.item],
             currentIndex: _tabIndex,
             onTap: (index) => setState(() => _tabIndex = index),
           ),
@@ -105,9 +151,7 @@ class _HomeShellState extends ConsumerState<HomeShell> {
           bottom: false,
           child: Column(
             children: [
-              // 캘린더·고객 탭은 자기 머리를 쓴다(달력의 월·화살표, 고객의
-              // 제목·반려동물 수·보기 전환).
-              if (_tabIndex != _calendarTab && _tabIndex != _customersTab)
+              if (!tab.ownsHeader)
                 Padding(
                   padding: const EdgeInsets.fromLTRB(
                     AppSpacing.lg,
@@ -136,7 +180,7 @@ class _HomeShellState extends ConsumerState<HomeShell> {
                     ],
                   ),
                 ),
-              Expanded(child: _TabBody(index: _tabIndex)),
+              Expanded(child: tab.body),
             ],
           ),
         ),
@@ -145,23 +189,6 @@ class _HomeShellState extends ConsumerState<HomeShell> {
   }
 }
 
-class _TabBody extends StatelessWidget {
-  const _TabBody({required this.index});
-
-  final int index;
-
-  @override
-  Widget build(BuildContext context) {
-    return switch (index) {
-      _HomeShellState._calendarTab => const CalendarTab(),
-      _HomeShellState._customersTab => const CustomerListTab(),
-      _ => const Center(
-        child: _EmptyState(title: AppStrings.comingSoonEmptyTitle),
-      ),
-    };
-  }
-}
-
 class _EmptyState extends StatelessWidget {
   const _EmptyState({required this.title});
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/core/router/app_router_test.dart test/features/home` → 전부 통과(라우터 16, 홈 셸·골든)

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 517 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `accountRoutes`에 `'/customers/new'`를 더한다 → `계정 경로 밖의 모든 경로는 매장 선택이 없으면 매장 선택으로 밀려난다` 실패.
- `_redirectSignedIn`의 `if (shopCount >= 2 && selectedShopId == null) {...}` 블록을 지운다 → 같은 테스트와 `매장이 둘이고 선택된 게 없으면 매장 선택 화면으로 가고…` 실패.
- `_tabs`의 고객 탭에서 `ownsHeader: true`를 뺀다 → `test/features/customer/screens/customer_list_tab_test.dart`의 고객 탭 골든 실패(머리가 두 번 그려진다).
- `_tabs`에서 매출 탭을 뺀다 → `home_shell_test.dart::홈은 캘린더 탭으로 열리고, 매장 이름은 매출 탭 머리에 보인다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 홈 탭을 목록 하나로 정의하고, 라우터의 매장 범위 가드를 기본값으로 뒤집는다 — 계정 경로만 예외로 열거하고 나머지는 전부 매장 범위다(A7·A8)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 오류·재시도 블록 21곳, 시트 항목, 검색창을 `design/widgets`의 `AppErrorRetry`·`AppSheetAction`·`AppSearchField`로 걷어낸다 (A10)

**Files:**
- Create: `app/lib/design/widgets/app_error_retry.dart`
- Create: `app/lib/design/widgets/app_sheet_action.dart`
- Create: `app/lib/design/widgets/app_search_field.dart`
- Modify: `app/lib/features/auth/screens/splash_screen.dart`
- Modify: `app/lib/features/customer/screens/customer_edit_screen.dart`
- Modify: `app/lib/features/customer/screens/customer_list_tab.dart`
- Modify: `app/lib/features/customer/screens/pet_detail_screen.dart`
- Modify: `app/lib/features/customer/screens/pet_form_screen.dart`
- Modify: `app/lib/features/customer/screens/register_customer_screen.dart`
- Modify: `app/lib/features/shop/screens/members_screen.dart`
- Modify: `app/lib/features/shop/screens/shop_settings_screen.dart`
- Modify: `app/lib/features/visit/screens/calendar_tab.dart`
- Modify: `app/lib/features/visit/screens/day_screen.dart`
- Modify: `app/lib/features/visit/screens/draft_screen.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Modify: `app/lib/features/visit/screens/settings/menu_settings_screen.dart`
- Modify: `app/lib/features/visit/screens/settings/schedule_settings_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_detail_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_edit_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_form.dart`
- Create: `app/test/design/app_error_retry_test.dart`

**Interfaces:**
- Consumes: 화면 17곳의 "오류 문구 + `AppButton(label: AppStrings.retry)`" 블록, `visit_detail_screen.dart`·`day_screen.dart`의 `_SheetAction`, `customer_list_tab.dart`·`register_visit_screen.dart`의 검색창 데코.
- Produces: `lib/design/widgets/app_error_retry.dart` — `AppErrorRetry({required String message, required VoidCallback onRetry})`(가운데), `AppErrorRetry.inline(...)`(흐름 안, 여백 lg·간격 md), `AppErrorRetry.row(...)`(한 줄: `Expanded` caption + 버튼); `app_sheet_action.dart` — `AppSheetAction({required String label, required VoidCallback onTap})`; `app_search_field.dart` — `AppSearchField({required TextEditingController controller, required String hintText, bool autofocus = false})`. 문구는 화면마다 전과 같다(문구 통일은 하지 않는다). 골든은 바뀌지 않는다.

감사 결과(설계 4.2 A10): "오류 문구 + 다시 시도" 블록 21곳, `_SheetAction` 위젯이 두 파일에 중복, 검색창 데코가 두 곳에 복제. 이 작업은 셋을 `design/widgets`로 걷어낸다. 픽셀이 같도록 여백·글꼴을 원래 블록과 맞췄으므로 골든은 바뀌지 않는다(바뀌면 diff 를 잘못 적용한 것이다 — `--update-goldens`를 돌리지 말고 보고한다). 이 작업의 diff 는 21개 파일에 걸치지만 하나하나는 블록 치환이다 — 순서대로 적용하고 파일마다 `flutter analyze`로 확인한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/app_error_retry_test.dart`:

```dart
import 'package:chagocnote/design/widgets/app_error_retry.dart';
import 'package:chagocnote/design/widgets/app_search_field.dart';
import 'package:chagocnote/design/widgets/app_sheet_action.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _wrap(Widget child) => MaterialApp(
  home: Scaffold(body: Center(child: child)),
);

void main() {
  testWidgets('AppErrorRetry 는 문구와 [다시 시도]를 보이고, 누르면 onRetry 를 부른다', (
    tester,
  ) async {
    var retried = 0;
    await tester.pumpWidget(
      _wrap(AppErrorRetry(message: '문제가 생겼어요', onRetry: () => retried++)),
    );
    expect(find.text('문제가 생겼어요'), findsOneWidget);
    await tester.tap(find.text(AppStrings.retry));
    expect(retried, 1);
  });

  testWidgets('row 변형은 한 줄에 문구와 버튼을 나란히 놓는다', (tester) async {
    await tester.pumpWidget(
      _wrap(AppErrorRetry.row(message: '못 읽었어요', onRetry: () {})),
    );
    final text = tester.getTopLeft(find.text('못 읽었어요'));
    final button = tester.getTopLeft(find.text(AppStrings.retry));
    expect(button.dx, greaterThan(text.dx));
    expect((button.dy - text.dy).abs(), lessThan(24));
  });

  testWidgets('AppSheetAction 은 누르면 onTap 을 부른다', (tester) async {
    var tapped = 0;
    await tester.pumpWidget(
      _wrap(AppSheetAction(label: '수정', onTap: () => tapped++)),
    );
    await tester.tap(find.text('수정'));
    expect(tapped, 1);
  });

  testWidgets('AppSearchField 는 힌트를 보이고 컨트롤러에 글을 넣는다', (tester) async {
    final controller = TextEditingController();
    addTearDown(controller.dispose);
    await tester.pumpWidget(
      _wrap(AppSearchField(controller: controller, hintText: '이름·번호')),
    );
    expect(find.text('이름·번호'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '콩이');
    expect(controller.text, '콩이');
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/design/app_error_retry_test.dart`
Expected: 컴파일 실패 — `lib/design/widgets/app_error_retry.dart` 없음.

- [ ] **Step 3: 구현한다**

`app/lib/design/widgets/app_error_retry.dart`:

```dart
import 'package:flutter/material.dart';

import '../../l10n/app_strings.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'app_button.dart';

/// 오류 문구와 [다시 시도] 버튼. 화면마다 복사하던 블록을 하나로.
///
/// 기본은 화면 가운데(목록·상세의 `AsyncValue.when(error: …)` 자리). [AppErrorRetry.inline]은
/// 흐름 안에 여백을 두고 놓이고(달력 아래, 카드 안), [AppErrorRetry.row]는 한 줄(작은 글씨 +
/// 버튼)로 좁은 자리에 들어간다(시간 칸, 임시 휴무 목록).
class AppErrorRetry extends StatelessWidget {
  const AppErrorRetry({super.key, required this.message, required this.onRetry})
    : _layout = _Layout.centered;

  const AppErrorRetry.inline({
    super.key,
    required this.message,
    required this.onRetry,
  }) : _layout = _Layout.inline;

  const AppErrorRetry.row({
    super.key,
    required this.message,
    required this.onRetry,
  }) : _layout = _Layout.row;

  final String message;
  final VoidCallback onRetry;
  final _Layout _layout;

  @override
  Widget build(BuildContext context) {
    final button = AppButton(label: AppStrings.retry, onPressed: onRetry);
    return switch (_layout) {
      _Layout.centered => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            button,
          ],
        ),
      ),
      _Layout.inline => Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            button,
          ],
        ),
      ),
      _Layout.row => Row(
        children: [
          Expanded(child: Text(message, style: AppTypography.caption)),
          button,
        ],
      ),
    };
  }
}

enum _Layout { centered, inline, row }
```

`app/lib/design/widgets/app_sheet_action.dart`:

```dart
import 'package:flutter/material.dart';

import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 시트(`AppSheet`) 안의 한 줄 항목 — 누르면 [onTap]. 보통 `Navigator.pop(값)`을 넘긴다.
class AppSheetAction extends StatelessWidget {
  const AppSheetAction({super.key, required this.label, required this.onTap});

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

`app/lib/design/widgets/app_search_field.dart`:

```dart
import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_typography.dart';

/// 검색창 — 돋보기, 흰 채움, 구분선 테두리. 고객 목록과 예약 ①이 같은 모양을 쓴다.
class AppSearchField extends StatelessWidget {
  const AppSearchField({
    super.key,
    required this.controller,
    required this.hintText,
    this.autofocus = false,
  });

  final TextEditingController controller;
  final String hintText;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    final border = OutlineInputBorder(
      borderRadius: BorderRadius.circular(AppRadius.md),
      borderSide: const BorderSide(color: AppColors.line),
    );
    return TextField(
      controller: controller,
      autofocus: autofocus,
      textInputAction: TextInputAction.search,
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: AppTypography.body.copyWith(color: AppColors.secondary),
        prefixIcon: const Icon(Icons.search, color: AppColors.secondary),
        filled: true,
        fillColor: AppColors.white,
        isDense: true,
        border: border,
        enabledBorder: border,
      ),
    );
  }
}
```

`app/lib/features/auth/screens/splash_screen.dart`:

```diff
@@ -6,7 +6,7 @@ import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
-import '../../../design/widgets/app_button.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../state/session_controller.dart';
 
@@ -33,23 +33,9 @@ class SplashScreen extends ConsumerWidget {
                 const CircularProgressIndicator(),
               ],
             ),
-            error: (error, _) => Padding(
-              padding: const EdgeInsets.all(AppSpacing.xl),
-              child: Column(
-                mainAxisSize: MainAxisSize.min,
-                children: [
-                  Text(
-                    messageFor(error),
-                    style: AppTypography.body,
-                    textAlign: TextAlign.center,
-                  ),
-                  const SizedBox(height: AppSpacing.lg),
-                  AppButton(
-                    label: AppStrings.retry,
-                    onPressed: () => ref.invalidate(sessionControllerProvider),
-                  ),
-                ],
-              ),
+            error: (error, _) => AppErrorRetry.inline(
+              message: messageFor(error),
+              onRetry: () => ref.invalidate(sessionControllerProvider),
             ),
           ),
         ),
```

`app/lib/features/customer/screens/customer_edit_screen.dart`:

```diff
@@ -9,6 +9,7 @@ import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -161,19 +162,9 @@ class _CustomerEditScreenState extends ConsumerState<CustomerEditScreen> {
                   ),
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () =>
-                              ref.invalidate(customerDetailProvider(key!)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () => ref.invalidate(customerDetailProvider(key!)),
                   ),
                 ),
               ),
```

`app/lib/features/customer/screens/customer_list_tab.dart`:

```diff
@@ -2,13 +2,12 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../../core/error/error_messages.dart';
-import '../../../design/tokens/app_colors.dart';
-import '../../../design/tokens/app_radius.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
-import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_choice_chip.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_icon_toggle.dart';
+import '../../../design/widgets/app_search_field.dart';
 import '../../../design/widgets/app_segment.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -84,7 +83,7 @@ class _CustomerListTabState extends ConsumerState<CustomerListTab> {
 
   @override
   Widget build(BuildContext context) {
-    ref.watch(selectedShopIdProvider);   // 매장이 바뀌면 다시 그린다
+    ref.watch(selectedShopIdProvider); // 매장이 바뀌면 다시 그린다
     final query = _query;
     final mode =
         ref.watch(customerViewModeProvider).value ?? CustomerViewMode.list;
@@ -161,27 +160,9 @@ class _CustomerListTabState extends ConsumerState<CustomerListTab> {
             AppSpacing.lg,
             AppSpacing.sm,
           ),
-          child: TextField(
+          child: AppSearchField(
             controller: _search,
-            textInputAction: TextInputAction.search,
-            decoration: InputDecoration(
-              hintText: AppStrings.customerSearchHint,
-              hintStyle: AppTypography.body.copyWith(
-                color: AppColors.secondary,
-              ),
-              prefixIcon: const Icon(Icons.search, color: AppColors.secondary),
-              filled: true,
-              fillColor: AppColors.white,
-              isDense: true,
-              border: OutlineInputBorder(
-                borderRadius: BorderRadius.circular(AppRadius.md),
-                borderSide: const BorderSide(color: AppColors.line),
-              ),
-              enabledBorder: OutlineInputBorder(
-                borderRadius: BorderRadius.circular(AppRadius.md),
-                borderSide: const BorderSide(color: AppColors.line),
-              ),
-            ),
+            hintText: AppStrings.customerSearchHint,
           ),
         ),
         Expanded(
@@ -196,20 +177,10 @@ class _CustomerListTabState extends ConsumerState<CustomerListTab> {
                       .loadMore(),
                 )
               : async.hasError
-              ? Center(
-                  child: Column(
-                    mainAxisSize: MainAxisSize.min,
-                    children: [
-                      Text(messageFor(async.error!), style: AppTypography.body),
-                      const SizedBox(height: AppSpacing.lg),
-                      AppButton(
-                        label: AppStrings.retry,
-                        onPressed: () => ref.invalidate(
-                          customerListControllerProvider(query!),
-                        ),
-                      ),
-                    ],
-                  ),
+              ? AppErrorRetry(
+                  message: messageFor(async.error!),
+                  onRetry: () =>
+                      ref.invalidate(customerListControllerProvider(query!)),
                 )
               : const Center(child: CircularProgressIndicator()),
         ),
@@ -276,15 +247,9 @@ class _CardList extends StatelessWidget {
           if (state.loadMoreError != null) {
             return Padding(
               padding: const EdgeInsets.all(AppSpacing.lg),
-              child: Column(
-                children: [
-                  Text(
-                    messageFor(state.loadMoreError!),
-                    style: AppTypography.caption,
-                  ),
-                  const SizedBox(height: AppSpacing.sm),
-                  AppButton(label: AppStrings.retry, onPressed: onRetryMore),
-                ],
+              child: AppErrorRetry.row(
+                message: messageFor(state.loadMoreError!),
+                onRetry: onRetryMore,
               ),
             );
           }
```

`app/lib/features/customer/screens/pet_detail_screen.dart`:

```diff
@@ -13,9 +13,11 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_segment.dart';
 import '../../../design/widgets/app_sheet.dart';
+import '../../../design/widgets/app_sheet_action.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -49,13 +51,13 @@ class _PetDetailScreenState extends ConsumerState<PetDetailScreen> {
       builder: (context) => Column(
         mainAxisSize: MainAxisSize.min,
         children: [
-          _SheetAction(
+          AppSheetAction(
             label: detail.pet.passedAway
                 ? AppStrings.unmarkPassedAway
                 : AppStrings.markPassedAway,
             onTap: () => Navigator.of(context).pop('passed'),
           ),
-          _SheetAction(
+          AppSheetAction(
             label: AppStrings.deletePet,
             onTap: () => Navigator.of(context).pop('delete'),
           ),
@@ -217,22 +219,10 @@ class _PetDetailScreenState extends ConsumerState<PetDetailScreen> {
                   ),
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () => ref.invalidate(
-                            petDetailProvider((
-                              shopId: shopId!,
-                              petId: widget.petId,
-                            )),
-                          ),
-                        ),
-                      ],
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () => ref.invalidate(
+                      petDetailProvider((shopId: shopId!, petId: widget.petId)),
                     ),
                   ),
                 ),
@@ -452,15 +442,9 @@ class _OwnerTab extends ConsumerWidget {
             padding: EdgeInsets.all(AppSpacing.lg),
             child: Center(child: CircularProgressIndicator()),
           ),
-          error: (error, _) => Column(
-            children: [
-              Text(messageFor(error), style: AppTypography.body),
-              const SizedBox(height: AppSpacing.sm),
-              AppButton(
-                label: AppStrings.retry,
-                onPressed: () => ref.invalidate(customerDetailProvider(key)),
-              ),
-            ],
+          error: (error, _) => AppErrorRetry.inline(
+            message: messageFor(error),
+            onRetry: () => ref.invalidate(customerDetailProvider(key)),
           ),
         );
   }
@@ -568,24 +552,3 @@ class _Siblings extends StatelessWidget {
     );
   }
 }
-
-class _SheetAction extends StatelessWidget {
-  const _SheetAction({required this.label, required this.onTap});
-
-  final String label;
-  final VoidCallback onTap;
-
-  @override
-  Widget build(BuildContext context) {
-    return Pressable(
-      onTap: onTap,
-      semanticLabel: label,
-      child: Container(
-        width: double.infinity,
-        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
-        alignment: Alignment.center,
-        child: Text(label, style: AppTypography.body),
-      ),
-    );
-  }
-}
```

`app/lib/features/customer/screens/pet_form_screen.dart`:

```diff
@@ -8,7 +8,7 @@ import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
-import '../../../design/widgets/app_button.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../../../core/time/today_provider.dart';
@@ -79,28 +79,14 @@ class _PetFormScreenState extends ConsumerState<PetFormScreen> {
 
     Widget body;
     if (types.hasError || pet.hasError) {
-      body = Center(
-        child: Column(
-          mainAxisSize: MainAxisSize.min,
-          children: [
-            Text(
-              messageFor(types.error ?? pet.error!),
-              style: AppTypography.body,
-            ),
-            const SizedBox(height: AppSpacing.lg),
-            AppButton(
-              label: AppStrings.retry,
-              onPressed: () {
-                ref.invalidate(conditionTypesProvider(shopId!));
-                if (petId != null) {
-                  ref.invalidate(
-                    petDetailProvider((shopId: shopId, petId: petId)),
-                  );
-                }
-              },
-            ),
-          ],
-        ),
+      body = AppErrorRetry(
+        message: messageFor(types.error ?? pet.error!),
+        onRetry: () {
+          ref.invalidate(conditionTypesProvider(shopId!));
+          if (petId != null) {
+            ref.invalidate(petDetailProvider((shopId: shopId, petId: petId)));
+          }
+        },
       );
     } else if (!types.hasValue || !pet.hasValue) {
       body = const Center(child: CircularProgressIndicator());
```

`app/lib/features/customer/screens/register_customer_screen.dart`:

```diff
@@ -12,6 +12,7 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../../../core/time/today_provider.dart';
@@ -320,19 +321,9 @@ class _RegisterCustomerScreenState
             ),
           ),
           loading: () => const Center(child: CircularProgressIndicator()),
-          error: (error, _) => Center(
-            child: Column(
-              mainAxisSize: MainAxisSize.min,
-              children: [
-                Text(messageFor(error), style: AppTypography.body),
-                const SizedBox(height: AppSpacing.lg),
-                AppButton(
-                  label: AppStrings.retry,
-                  onPressed: () =>
-                      ref.invalidate(conditionTypesProvider(shopId)),
-                ),
-              ],
-            ),
+          error: (error, _) => AppErrorRetry(
+            message: messageFor(error),
+            onRetry: () => ref.invalidate(conditionTypesProvider(shopId)),
           ),
         );
   }
```

`app/lib/features/shop/screens/members_screen.dart`:

```diff
@@ -11,6 +11,7 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
@@ -38,8 +39,9 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
     if (shopId == null) return;
     setState(() => _errorText = null);
     try {
-      final invite =
-          await ref.read(membersControllerProvider(shopId).notifier).createInvite();
+      final invite = await ref
+          .read(membersControllerProvider(shopId).notifier)
+          .createInvite();
       if (!mounted) return;
       _showInviteSheet(invite);
     } catch (e) {
@@ -54,10 +56,7 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
       builder: (context) => Column(
         mainAxisSize: MainAxisSize.min,
         children: [
-          Text(
-            invite.code,
-            style: AppTypography.inviteCode,
-          ),
+          Text(invite.code, style: AppTypography.inviteCode),
           const SizedBox(height: AppSpacing.sm),
           Text(
             '${AppStrings.inviteExpiresAtLabel} ${_formatDateTime(invite.expiresAt)}',
@@ -66,7 +65,8 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
           const SizedBox(height: AppSpacing.lg),
           AppButton(
             label: AppStrings.copy,
-            onPressed: () => Clipboard.setData(ClipboardData(text: invite.code)),
+            onPressed: () =>
+                Clipboard.setData(ClipboardData(text: invite.code)),
           ),
         ],
       ),
@@ -83,8 +83,8 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
             label: member.isOwner
                 ? AppStrings.demoteToStaff
                 : AppStrings.promoteToOwner,
-            onTap: () => Navigator.of(context)
-                .pop(member.isOwner ? 'staff' : 'owner'),
+            onTap: () =>
+                Navigator.of(context).pop(member.isOwner ? 'staff' : 'owner'),
           ),
           _ActionRow(
             label: AppStrings.removeMember,
@@ -208,10 +208,7 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
                   padding: const EdgeInsets.symmetric(
                     horizontal: AppSpacing.lg,
                   ),
-                  child: Text(
-                    _errorText!,
-                    style: AppTypography.caption,
-                  ),
+                  child: Text(_errorText!, style: AppTypography.caption),
                 ),
               Expanded(
                 child: members.when(
@@ -269,19 +266,10 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
                   ),
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () => ref
-                              .invalidate(membersControllerProvider(shopId!)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () =>
+                        ref.invalidate(membersControllerProvider(shopId!)),
                   ),
                 ),
               ),
```

`app/lib/features/shop/screens/shop_settings_screen.dart`:

```diff
@@ -8,6 +8,7 @@ import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../api/shop_api.dart';
@@ -19,8 +20,7 @@ class ShopSettingsScreen extends ConsumerStatefulWidget {
   const ShopSettingsScreen({super.key});
 
   @override
-  ConsumerState<ShopSettingsScreen> createState() =>
-      _ShopSettingsScreenState();
+  ConsumerState<ShopSettingsScreen> createState() => _ShopSettingsScreenState();
 }
 
 class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
@@ -70,7 +70,9 @@ class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
     try {
       final phone = _phoneController.text.trim();
       final address = _addressController.text.trim();
-      await ref.read(shopSettingsControllerProvider(shopId).notifier).save(
+      await ref
+          .read(shopSettingsControllerProvider(shopId).notifier)
+          .save(
             name: name,
             phone: phone.isEmpty ? null : phone,
             address: address.isEmpty ? null : address,
@@ -181,20 +183,10 @@ class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
                   },
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () => ref.invalidate(
-                            shopSettingsControllerProvider(shopId!),
-                          ),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () =>
+                        ref.invalidate(shopSettingsControllerProvider(shopId!)),
                   ),
                 ),
               ),
```

`app/lib/features/visit/screens/calendar_tab.dart`:

```diff
@@ -8,9 +8,9 @@ import '../../../design/tokens/app_radius.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_big_date.dart';
-import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_dashed_tile.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_glass_card.dart';
 import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/pressable.dart';
@@ -116,19 +116,9 @@ class _CalendarTabState extends ConsumerState<CalendarTab> {
             const _WeekHeader(),
             const SizedBox(height: AppSpacing.xs),
             if (summary.hasError && data == null)
-              Padding(
-                padding: const EdgeInsets.all(AppSpacing.lg),
-                child: Column(
-                  children: [
-                    Text(messageFor(summary.error!), style: AppTypography.body),
-                    const SizedBox(height: AppSpacing.md),
-                    AppButton(
-                      label: AppStrings.retry,
-                      onPressed: () =>
-                          ref.invalidate(calendarMonthProvider(monthKey)),
-                    ),
-                  ],
-                ),
+              AppErrorRetry.inline(
+                message: messageFor(summary.error!),
+                onRetry: () => ref.invalidate(calendarMonthProvider(monthKey)),
               )
             else
               _MonthGrid(
```

`app/lib/features/visit/screens/day_screen.dart`:

```diff
@@ -15,6 +15,7 @@ import '../../../design/widgets/app_big_date.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_fab.dart';
 import '../../../design/widgets/app_icon_toggle.dart';
 import '../../../design/widgets/app_photo_tile.dart';
@@ -261,19 +262,9 @@ class _DayScreenState extends ConsumerState<DayScreen> {
                 child: day.when(
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () =>
-                              ref.invalidate(dayVisitsProvider(key)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () => ref.invalidate(dayVisitsProvider(key)),
                   ),
                   data: (data) {
                     final groups = groupDay(data.items);
```

`app/lib/features/visit/screens/draft_screen.dart`:

```diff
@@ -11,6 +11,7 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -111,19 +112,9 @@ class _DraftScreenState extends ConsumerState<DraftScreen> {
                 child: draft.when(
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () =>
-                              ref.invalidate(visitDraftProvider(key)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () => ref.invalidate(visitDraftProvider(key)),
                   ),
                   data: (draft) => _body(shopId!, draft),
                 ),
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -7,13 +7,13 @@ import '../../../core/error/api_exception.dart';
 import '../../../core/error/error_messages.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
-import '../../../design/tokens/app_colors.dart';
-import '../../../design/tokens/app_radius.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
+import '../../../design/widgets/app_error_retry.dart';
+import '../../../design/widgets/app_search_field.dart';
 import '../../../design/widgets/app_snack_bar.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
@@ -36,12 +36,7 @@ import 'visit_labels.dart';
 ///
 /// 저장하면 저장한 날짜를 돌려주며 닫는다 — 부른 화면이 그 날로 옮겨 간다.
 class RegisterVisitScreen extends ConsumerStatefulWidget {
-  const RegisterVisitScreen({
-    super.key,
-    this.date,
-    this.draft,
-    this.prefill,
-  });
+  const RegisterVisitScreen({super.key, this.date, this.draft, this.prefill});
 
   final DateTime? date;
   final NextVisitDraft? draft;
@@ -361,47 +356,20 @@ class _CustomerSearchState extends ConsumerState<_CustomerSearch> {
         ),
         Padding(
           padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
-          child: TextField(
+          child: AppSearchField(
             controller: _search,
+            hintText: AppStrings.customerSearchHint,
             autofocus: true,
-            textInputAction: TextInputAction.search,
-            decoration: InputDecoration(
-              hintText: AppStrings.customerSearchHint,
-              hintStyle: AppTypography.body.copyWith(
-                color: AppColors.secondary,
-              ),
-              prefixIcon: const Icon(Icons.search, color: AppColors.secondary),
-              filled: true,
-              fillColor: AppColors.white,
-              isDense: true,
-              border: OutlineInputBorder(
-                borderRadius: BorderRadius.circular(AppRadius.md),
-                borderSide: const BorderSide(color: AppColors.line),
-              ),
-              enabledBorder: OutlineInputBorder(
-                borderRadius: BorderRadius.circular(AppRadius.md),
-                borderSide: const BorderSide(color: AppColors.line),
-              ),
-            ),
           ),
         ),
         const SizedBox(height: AppSpacing.sm),
         Expanded(
           child: list.when(
             loading: () => const Center(child: CircularProgressIndicator()),
-            error: (error, _) => Center(
-              child: Column(
-                mainAxisSize: MainAxisSize.min,
-                children: [
-                  Text(messageFor(error), style: AppTypography.body),
-                  const SizedBox(height: AppSpacing.lg),
-                  AppButton(
-                    label: AppStrings.retry,
-                    onPressed: () =>
-                        ref.invalidate(customerListControllerProvider(query)),
-                  ),
-                ],
-              ),
+            error: (error, _) => AppErrorRetry(
+              message: messageFor(error),
+              onRetry: () =>
+                  ref.invalidate(customerListControllerProvider(query)),
             ),
             data: (state) => ListView(
               padding: const EdgeInsets.fromLTRB(
```

`app/lib/features/visit/screens/settings/menu_settings_screen.dart`:

```diff
@@ -12,6 +12,7 @@ import '../../../../design/widgets/app_back_button.dart';
 import '../../../../design/widgets/app_button.dart';
 import '../../../../design/widgets/app_card.dart';
 import '../../../../design/widgets/app_choice_chip.dart';
+import '../../../../design/widgets/app_error_retry.dart';
 import '../../../../design/widgets/app_sheet.dart';
 import '../../../../design/widgets/pressable.dart';
 import '../../../../l10n/app_strings.dart';
@@ -213,18 +214,9 @@ class _MenuSettingsScreenState extends ConsumerState<MenuSettingsScreen> {
                 child: menus.when(
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () => ref.invalidate(menusProvider(key)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () => ref.invalidate(menusProvider(key)),
                   ),
                   data: (items) {
                     final sorted = [...items]
```

`app/lib/features/visit/screens/settings/schedule_settings_screen.dart`:

```diff
@@ -12,6 +12,7 @@ import '../../../../design/widgets/app_back_button.dart';
 import '../../../../design/widgets/app_button.dart';
 import '../../../../design/widgets/app_card.dart';
 import '../../../../design/widgets/app_choice_chip.dart';
+import '../../../../design/widgets/app_error_retry.dart';
 import '../../../../design/widgets/app_sheet.dart';
 import '../../../../design/widgets/pressable.dart';
 import '../../../../l10n/app_strings.dart';
@@ -214,19 +215,10 @@ class _ScheduleSettingsScreenState
                 child: settings.when(
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () =>
-                              ref.invalidate(visitSettingsProvider(shopId!)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () =>
+                        ref.invalidate(visitSettingsProvider(shopId!)),
                   ),
                   data: (data) {
                     _init(data);
@@ -350,19 +342,9 @@ class _ScheduleSettingsScreenState
               const SizedBox(height: AppSpacing.sm),
               closedDates.when(
                 loading: () => const Center(child: CircularProgressIndicator()),
-                error: (error, _) => Row(
-                  children: [
-                    Expanded(
-                      child: Text(
-                        messageFor(error),
-                        style: AppTypography.caption,
-                      ),
-                    ),
-                    AppButton(
-                      label: AppStrings.retry,
-                      onPressed: () => ref.invalidate(closedDatesProvider),
-                    ),
-                  ],
+                error: (error, _) => AppErrorRetry.row(
+                  message: messageFor(error),
+                  onRetry: () => ref.invalidate(closedDatesProvider),
                 ),
                 data: (items) => items.isEmpty
                     ? const Text(
```

`app/lib/features/visit/screens/visit_detail_screen.dart`:

```diff
@@ -11,8 +11,10 @@ import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_chip.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_photo_tile.dart';
 import '../../../design/widgets/app_sheet.dart';
+import '../../../design/widgets/app_sheet_action.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -104,21 +106,24 @@ class _VisitDetailScreenState extends ConsumerState<VisitDetailScreen> {
         mainAxisSize: MainAxisSize.min,
         children: [
           if (status != VisitStatus.canceled && status != VisitStatus.noShow)
-            const _SheetAction(label: AppStrings.edit, value: _More.edit),
+            AppSheetAction(
+              label: AppStrings.edit,
+              onTap: () => Navigator.of(context).pop(_More.edit),
+            ),
           if (status == VisitStatus.reserved)
-            const _SheetAction(
+            AppSheetAction(
               label: AppStrings.actionCompleteNow,
-              value: _More.completeNow,
+              onTap: () => Navigator.of(context).pop(_More.completeNow),
             ),
           if (status != VisitStatus.reserved)
-            const _SheetAction(
+            AppSheetAction(
               label: AppStrings.actionRevert,
-              value: _More.revert,
+              onTap: () => Navigator.of(context).pop(_More.revert),
             ),
           if (status == VisitStatus.completed)
-            const _SheetAction(
+            AppSheetAction(
               label: AppStrings.actionNextReservation,
-              value: _More.next,
+              onTap: () => Navigator.of(context).pop(_More.next),
             ),
         ],
       ),
@@ -199,19 +204,9 @@ class _VisitDetailScreenState extends ConsumerState<VisitDetailScreen> {
                 child: detail.when(
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () =>
-                              ref.invalidate(visitDetailProvider(key)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () => ref.invalidate(visitDetailProvider(key)),
                   ),
                   data: (detail) => _Body(
                     detail: detail,
@@ -421,24 +416,3 @@ class _GroupCard extends StatelessWidget {
 
 /// `···` 시트의 항목. 문자열 대신 닫힌 enum 이라 처리 `switch`가 완전 열거된다.
 enum _More { edit, completeNow, revert, next }
-
-class _SheetAction extends StatelessWidget {
-  const _SheetAction({required this.label, required this.value});
-
-  final String label;
-  final _More value;
-
-  @override
-  Widget build(BuildContext context) {
-    return Pressable(
-      onTap: () => Navigator.of(context).pop(value),
-      semanticLabel: label,
-      child: Container(
-        width: double.infinity,
-        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
-        alignment: Alignment.center,
-        child: Text(label, style: AppTypography.body),
-      ),
-    );
-  }
-}
```

`app/lib/features/visit/screens/visit_edit_screen.dart`:

```diff
@@ -10,6 +10,7 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
@@ -156,19 +157,9 @@ class _VisitEditScreenState extends ConsumerState<VisitEditScreen> {
                 child: detail.when(
                   loading: () =>
                       const Center(child: CircularProgressIndicator()),
-                  error: (error, _) => Center(
-                    child: Column(
-                      mainAxisSize: MainAxisSize.min,
-                      children: [
-                        Text(messageFor(error), style: AppTypography.body),
-                        const SizedBox(height: AppSpacing.lg),
-                        AppButton(
-                          label: AppStrings.retry,
-                          onPressed: () =>
-                              ref.invalidate(visitDetailProvider(key)),
-                        ),
-                      ],
-                    ),
+                  error: (error, _) => AppErrorRetry(
+                    message: messageFor(error),
+                    onRetry: () => ref.invalidate(visitDetailProvider(key)),
                   ),
                   data: (detail) => _form(shopId!, detail),
                 ),
```

`app/lib/features/visit/screens/visit_form.dart`:

```diff
@@ -10,6 +10,7 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_choice_chip.dart';
+import '../../../design/widgets/app_error_retry.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
@@ -296,22 +297,13 @@ class _VisitFormState extends ConsumerState<VisitForm> {
     );
     final error = settings.error ?? customer.error ?? menus.error;
     if (error != null) {
-      return Center(
-        child: Column(
-          mainAxisSize: MainAxisSize.min,
-          children: [
-            Text(messageFor(error), style: AppTypography.body),
-            const SizedBox(height: AppSpacing.lg),
-            AppButton(
-              label: AppStrings.retry,
-              onPressed: () {
-                ref.invalidate(visitSettingsProvider(widget.shopId));
-                ref.invalidate(customerDetailProvider);
-                ref.invalidate(menusProvider);
-              },
-            ),
-          ],
-        ),
+      return AppErrorRetry(
+        message: messageFor(error),
+        onRetry: () {
+          ref.invalidate(visitSettingsProvider(widget.shopId));
+          ref.invalidate(customerDetailProvider);
+          ref.invalidate(menusProvider);
+        },
       );
     }
     final s = settings.value;
@@ -691,16 +683,9 @@ class _SlotGrid extends ConsumerWidget {
         padding: EdgeInsets.all(AppSpacing.md),
         child: Center(child: CircularProgressIndicator()),
       ),
-      error: (error, _) => Row(
-        children: [
-          Expanded(
-            child: Text(messageFor(error), style: AppTypography.caption),
-          ),
-          AppButton(
-            label: AppStrings.retry,
-            onPressed: () => ref.invalidate(visitSlotsProvider(slotsKey)),
-          ),
-        ],
+      error: (error, _) => AppErrorRetry.row(
+        message: messageFor(error),
+        onRetry: () => ref.invalidate(visitSlotsProvider(slotsKey)),
       ),
       data: (data) => Wrap(
         spacing: AppSpacing.sm,
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/design/app_error_retry_test.dart` → 4 passed

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 521 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `AppErrorRetry`의 `_Layout.row` 분기를 `Column`으로 → `row 변형은 한 줄에 문구와 버튼을 나란히 놓는다` 실패.
- `AppSheetAction`의 `onTap`을 부르지 않는다 → `AppSheetAction 은 누르면 onTap 을 부른다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 오류·재시도 블록 21곳, 시트 항목, 검색창을 design/widgets 의 AppErrorRetry·AppSheetAction·AppSearchField 로 걷어낸다(A10)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: 예약 폼 규칙을 `VisitFormDraft`로 빼고 시간표 범위를 `timelineHours`로, 고객 상세는 `pets`만 select 한다 (A11·A12)

**Files:**
- Create: `app/lib/features/visit/state/visit_form_draft.dart`
- Modify: `app/lib/features/visit/state/day_layout.dart`
- Modify: `app/lib/features/visit/screens/day_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_form.dart`
- Modify: `app/test/features/visit/state/day_layout_test.dart`
- Create: `app/test/features/visit/state/visit_form_draft_test.dart`

**Interfaces:**
- Consumes: `features/visit/screens/visit_form.dart`의 `State`가 쥐던 필드·규칙(`_petIds`·`_ownerOnly`·`_duration`·`_menuIds`·`_knownMenus`·`_menusTouched`·`_durationTouched`·`_prefilledNote`·`_defaultsSeq`·`_initPets`·`_togglePet`·`_prefill`·`_toggleMenu`·`_stepDuration`·`_value`), `VisitFormInitial`·`VisitFormValue`(같은 파일에 있던 값 클래스), `features/visit/state/visit_form_rules.dart`의 `stepDuration`·`menuDuration`, `day_screen.dart`의 시간표 범위 계산.
- Produces: `lib/features/visit/state/visit_form_draft.dart` — `VisitFormValue`·`VisitFormInitial`(옮김, 내용 그대로), `class VisitFormDraft { VisitFormDraft(VisitFormInitial initial); Set<int> petIds; bool ownerOnly; DateTime date; String? at; int? duration; List<int> menuIds; List<MenuBrief> knownMenus; bool menusTouched, durationTouched, prefilledNote; int effectiveDuration(VisitSettings); bool get petsChosen; int? initPets(List<Pet> living); int? togglePet(int petId, {required bool single}); void chooseOwnerOnly(); int? beginPrefill(); bool applyPrefill(int seq, VisitDefaults); void toggleMenu(Menu, List<Menu> all, VisitSettings); void stepDuration(VisitSettings, {required bool longer, bool long = false}); void ensureDuration(List<Menu>, VisitSettings); VisitFormValue value(VisitSettings, String? startsAt, String memo); }`. `visit_form.dart`는 `export '../state/visit_form_draft.dart' show VisitFormInitial, VisitFormValue;`로 옛 이름을 내보내고 `late final _draft = VisitFormDraft(widget.initial)`에 위임한다(`State`에는 `_memo`·`_stripStart`만 남는다); 고객 상세는 `customerDetailProvider(...).select((async) => (error: async.error, pets: async.value?.pets))`로 본다. `lib/features/visit/state/day_layout.dart` — `({int first, int last}) timelineHours(VisitSettings? settings, List<DayGroup> active)`(설정 없으면 10~19, 영업시간이 기본, 닫는 시각에 분이 있으면 +1, 걸친 묶음만큼 넓힌다).

감사 결과(설계 4.2 A11·A12): `visit_form.dart`(879줄)의 `State`가 프리필 경쟁·메뉴→소요 산출·프로바이더 합성·시간 칸 재조회를 다 쥐어 단위 테스트가 없었고, `day_screen`의 시간표 범위 계산이 위젯 안에 있었으며, 폼이 `customerDetailProvider` 전체를 watch 했다. **설계와 다른 점**(결정 기록 007): 규칙은 Notifier(`visit_form_controller.dart`)가 아니라 순수 객체 `VisitFormDraft`다 — 폼은 화면 인스턴스마다 하나이고 프로바이더로 공유할 이유가 없다. 위젯은 이 객체를 바꾸고 `setState`만 부른다. 화면의 동작(반려동물 선택, 지난번처럼, 메뉴·소요, 저장)은 전과 같다 — 기존 폼 위젯 테스트가 그대로 통과한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/visit/state/day_layout_test.dart`:

```diff
@@ -49,13 +49,7 @@ void main() {
   test('취소된 형제의 긴 소요는 묶음 끝에 들지 않는다', () {
     final group = groupDay([
       _item(1, '13:00', duration: 60, group: 'a'),
-      _item(
-        2,
-        '13:00',
-        duration: 150,
-        group: 'a',
-        status: 'canceled',
-      ),
+      _item(2, '13:00', duration: 150, group: 'a', status: 'canceled'),
     ]).single;
 
     expect(group.endsAt, DateTime(2026, 10, 2, 14));
@@ -109,4 +103,26 @@ void main() {
 
     expect(timelineColumns(groups), [0, 1, 0, 1]);
   });
+
+  group('시간표 범위', () {
+    test('설정이 없으면 10~19시, 영업시간이 있으면 그 시간이 기본이다', () {
+      expect(timelineHours(null, []), (first: 10, last: 19));
+      final settings = VisitSettings.fromJson(
+        settingsJson(opensAt: '09:00:00', closesAt: '18:30:00'),
+      );
+      expect(timelineHours(settings, []), (
+        first: 9,
+        last: 19,
+      )); // 18:30 은 19시 칸까지
+    });
+
+    test('영업시간 밖에 걸친 묶음이 있으면 그만큼 넓힌다', () {
+      final settings = VisitSettings.fromJson(settingsJson());
+      final groups = groupDay([
+        _item(1, '08:30', duration: 60),
+        _item(2, '18:00', duration: 90),
+      ]);
+      expect(timelineHours(settings, groups), (first: 8, last: 20));
+    });
+  });
 }
```

`app/test/features/visit/state/visit_form_draft_test.dart`:

```dart
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/visit_form_draft.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/visit_fixtures.dart';

final _date = DateTime(2026, 10, 2);
final _settings = VisitSettings.fromJson(
  settingsJson(defaultDurationMinutes: 120),
);
final _menus = [for (final j in defaultMenusJson()) Menu.fromJson(j)];
Menu _menu(int id) => _menus.firstWhere((m) => m.menuId == id);
Pet _pet(int id) => Pet.fromJson(petJson(petId: id));

VisitFormDraft _draft({Set<int> petIds = const {}, bool prefilled = false}) =>
    VisitFormDraft(
      VisitFormInitial(date: _date, petIds: petIds, prefilled: prefilled),
    );

void main() {
  group('반려동물', () {
    test('보호자의 아이가 하나뿐이면 처음에 그 아이를 고르고 미리 채울 아이로 준다', () {
      final draft = _draft();
      expect(draft.initPets([_pet(11)]), 11);
      expect(draft.petIds, {11});
      expect(draft.initPets([_pet(11)]), isNull); // 처음 한 번만
    });

    test('미리 골라진 아이 가운데 이 보호자의 아이만 남긴다', () {
      final draft = _draft(petIds: {11, 99});
      expect(draft.initPets([_pet(11), _pet(12)]), isNull);
      expect(draft.petIds, {11});
    });

    test('여러 마리 폼에서는 고르고 풀 수 있고, 한 마리만 남을 때 그 아이를 돌려준다', () {
      final draft = _draft();
      expect(draft.togglePet(11, single: false), 11);
      expect(draft.togglePet(12, single: false), isNull);
      expect(draft.petIds, {11, 12});
      expect(draft.togglePet(11, single: false), 12);
    });

    test('한 마리 폼에서는 고른 아이로 바뀐다', () {
      final draft = _draft(petIds: {11});
      expect(draft.togglePet(12, single: true), 12);
      expect(draft.petIds, {12});
    });

    test('보호자만 고르면 아이가 비고, 아이를 고르면 보호자만이 풀린다', () {
      final draft = _draft(petIds: {11});
      draft.chooseOwnerOnly();
      expect(draft.ownerOnly, isTrue);
      expect(draft.petIds, isEmpty);
      expect(draft.petsChosen, isTrue);
      draft.togglePet(11, single: false);
      expect(draft.ownerOnly, isFalse);
    });
  });

  group('지난번처럼', () {
    test('늦게 온 옛 응답은 버린다 — 순서 번호가 최신일 때만 채운다', () {
      final draft = _draft();
      final first = draft.beginPrefill()!;
      final second = draft.beginPrefill()!;
      final defaults = VisitDefaults.fromJson(
        defaultsJson(durationMinutes: 90),
      );
      expect(draft.applyPrefill(first, defaults), isFalse);
      expect(draft.duration, isNull);
      expect(draft.applyPrefill(second, defaults), isTrue);
      expect(draft.duration, 90);
      expect(draft.menuIds, [1]);
      expect(draft.prefilledNote, isTrue);
    });

    test('메뉴나 소요를 손댔거나 미리 채워진 폼이면 시작하지 않는다', () {
      final touched = _draft()..toggleMenu(_menu(1), _menus, _settings);
      expect(touched.beginPrefill(), isNull);
      expect(_draft(prefilled: true).beginPrefill(), isNull);
    });

    test('응답을 기다리는 사이 손댔으면 채우지 않는다', () {
      final draft = _draft();
      final seq = draft.beginPrefill()!;
      draft.stepDuration(_settings, longer: true);
      expect(
        draft.applyPrefill(seq, VisitDefaults.fromJson(defaultsJson())),
        isFalse,
      );
      expect(draft.duration, 130);
    });
  });

  group('메뉴와 소요', () {
    test('메뉴를 고르면 소요는 메뉴 기본 소요의 합이 되고 안내는 사라진다', () {
      final draft = _draft()..prefilledNote = true;
      draft.toggleMenu(_menu(1), _menus, _settings); // 60
      draft.toggleMenu(_menu(3), _menus, _settings); // +90
      expect(draft.menuIds, [1, 3]);
      expect(draft.duration, 150);
      expect(draft.prefilledNote, isFalse);
      draft.toggleMenu(_menu(1), _menus, _settings);
      expect(draft.menuIds, [3]);
      expect(draft.duration, 90);
    });

    test('소요를 직접 바꾼 뒤에는 메뉴를 골라도 소요가 따라오지 않는다', () {
      final draft = _draft();
      draft.stepDuration(_settings, longer: false, long: true); // 120 - 30
      expect(draft.duration, 90);
      draft.toggleMenu(_menu(4), _menus, _settings);
      expect(draft.duration, 90);
    });

    test('메뉴만 있고 소요가 없는 초안은 메뉴 기본 소요의 합으로 시작한다', () {
      final draft = VisitFormDraft(
        VisitFormInitial(
          date: _date,
          menus: [MenuBrief.fromJson(menuBriefJson(menuId: 4, name: '전체 미용'))],
        ),
      );
      draft.ensureDuration(_menus, _settings);
      expect(draft.duration, 150);
      expect(draft.effectiveDuration(_settings), 150);
      expect(_draft().effectiveDuration(_settings), 120);
    });
  });

  test('값을 만들 때 보호자만이면 아이가 비고, 빈 메모는 null 이다', () {
    final draft = _draft(petIds: {11})..chooseOwnerOnly();
    final value = draft.value(_settings, '2026-10-02T14:00:00+09:00', '  ');
    expect(value.petIds, isEmpty);
    expect(value.memo, isNull);
    expect(value.durationMinutes, 120);
    expect(value.startsAt, '2026-10-02T14:00:00+09:00');
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/features/visit/state/visit_form_draft_test.dart`
Expected: 컴파일 실패 — `lib/features/visit/state/visit_form_draft.dart` 없음.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/state/visit_form_draft.dart`:

```dart
import '../../customer/api/customer_models.dart';
import '../api/visit_models.dart';
import 'visit_form_rules.dart' as rules;

/// 예약 폼이 내보내는 값. [petIds]가 비었으면 보호자만의 방문이다.
class VisitFormValue {
  const VisitFormValue({
    required this.petIds,
    required this.date,
    required this.startsAt,
    required this.durationMinutes,
    required this.menuIds,
    required this.memo,
  });

  final List<int> petIds;
  final DateTime date;

  /// 서버가 준 시각 문자열(매장 시간대). 없으면 아직 시각을 고르지 않았다.
  final String? startsAt;
  final int durationMinutes;
  final List<int> menuIds;
  final String? memo;
}

/// 폼의 처음 값. [prefilled]면 반려동물을 골라도 "지난번처럼"으로 덮어쓰지
/// 않는다(다음 예약 초안·수정).
class VisitFormInitial {
  const VisitFormInitial({
    required this.date,
    this.petIds = const {},
    this.ownerOnly = false,
    this.at,
    this.durationMinutes,
    this.menus = const [],
    this.memo,
    this.prefilled = false,
  });

  final DateTime date;
  final Set<int> petIds;
  final bool ownerOnly;

  /// `HH:MM`.
  final String? at;
  final int? durationMinutes;
  final List<MenuBrief> menus;
  final String? memo;
  final bool prefilled;
}

/// 예약 폼의 상태와 규칙 — 위젯의 `State`가 쥐던 것을 뺀 순수 객체.
///
/// 반려동물 선택, "지난번처럼" 미리 채우기(늦게 온 옛 응답을 버리는 순서 번호), 메뉴 → 소요
/// 산출, 소요 단계 조정이 여기 있다. 위젯은 이 객체를 바꾸고 `setState`만 부른다. 그래서
/// 규칙은 위젯 없이 단위 테스트로 검증한다.
class VisitFormDraft {
  VisitFormDraft(this.initial)
    : petIds = {...initial.petIds},
      ownerOnly = initial.ownerOnly,
      date = initial.date,
      at = initial.at,
      duration = initial.durationMinutes,
      menuIds = [for (final m in initial.menus) m.menuId],
      knownMenus = [...initial.menus];

  final VisitFormInitial initial;

  Set<int> petIds;
  bool ownerOnly;
  DateTime date;

  /// `HH:MM`. null 이면 아직 시각을 고르지 않았다.
  String? at;

  /// null 이면 매장 기본 소요.
  int? duration;
  List<int> menuIds;

  /// 보관돼 메뉴표에 없지만 이 방문에 붙어 있는 메뉴(이름을 보이려고 둔다).
  List<MenuBrief> knownMenus;

  /// 사용자가 메뉴·소요를 직접 손댔는가 — 손댄 뒤에는 미리 채우기가 덮지 않는다.
  bool menusTouched = false;
  bool durationTouched = false;

  /// "지난번과 같게 채웠어요" 안내를 보일지.
  bool prefilledNote = false;

  bool _petsInitialized = false;
  int _defaultsSeq = 0;

  int effectiveDuration(VisitSettings settings) =>
      duration ?? settings.defaultDurationMinutes;

  bool get petsChosen => ownerOnly || petIds.isNotEmpty;

  /// 반려동물이 하나뿐인 보호자면 그 아이를 미리 고른다. 미리 골라진 아이는
  /// 이 보호자의 아이만 남긴다(카톡 초안이 다른 집 아이를 넘길 수 없게).
  /// 처음 한 번만 한다. 미리 고른 아이(있으면)를 돌려준다 — 부르는 쪽이 그 아이로 미리 채운다.
  int? initPets(List<Pet> living) {
    if (_petsInitialized) return null;
    _petsInitialized = true;
    petIds.removeWhere((id) => !living.any((p) => p.petId == id));
    if (petIds.isNotEmpty || ownerOnly || living.length != 1) return null;
    petIds = {living.single.petId};
    return living.single.petId;
  }

  /// 아이를 고르거나 푼다. [single]이면 한 마리만 고른다. 한 마리만 남으면
  /// (처음 골랐든, 하나를 풀어 하나가 남았든) 그 아이 ID 를 돌려준다 — 그 아이로 미리 채운다.
  int? togglePet(int petId, {required bool single}) {
    ownerOnly = false;
    if (single) {
      petIds = {petId};
    } else if (!petIds.remove(petId)) {
      petIds.add(petId);
    }
    return petIds.length == 1 ? petIds.single : null;
  }

  void chooseOwnerOnly() {
    ownerOnly = true;
    petIds = {};
  }

  /// "지난번처럼"을 시작한다. 손댔거나 미리 채워진 폼이면 null(시작하지 않는다).
  /// 돌려준 번호를 [applyPrefill]에 넘긴다 — 늦게 온 옛 응답은 버린다.
  int? beginPrefill() {
    if (initial.prefilled || menusTouched || durationTouched) return null;
    return ++_defaultsSeq;
  }

  /// [seq]가 아직 최신이고 그 사이 손대지 않았으면 채운다. 채웠으면 true.
  bool applyPrefill(int seq, VisitDefaults defaults) {
    if (seq != _defaultsSeq || menusTouched || durationTouched) return false;
    menuIds = [for (final m in defaults.menus) m.menuId];
    knownMenus = [...knownMenus, ...defaults.menus];
    duration = defaults.durationMinutes;
    prefilledNote = defaults.sourceVisitId != null;
    return true;
  }

  void toggleMenu(Menu menu, List<Menu> all, VisitSettings settings) {
    menusTouched = true;
    prefilledNote = false;
    if (!menuIds.remove(menu.menuId)) menuIds.add(menu.menuId);
    if (!durationTouched) duration = _durationOf(all, settings);
  }

  void stepDuration(
    VisitSettings settings, {
    required bool longer,
    bool long = false,
  }) {
    durationTouched = true;
    prefilledNote = false;
    duration = rules.stepDuration(
      effectiveDuration(settings),
      longer: longer,
      long: long,
    );
  }

  /// 메뉴만 있고 소요가 없는 초안(카톡)은 메뉴 기본 소요의 합으로 시작한다.
  void ensureDuration(List<Menu> menus, VisitSettings settings) {
    if (duration == null && menuIds.isNotEmpty && !durationTouched) {
      duration = _durationOf(menus, settings);
    }
  }

  int _durationOf(List<Menu> menus, VisitSettings settings) {
    final byId = {for (final m in menus) m.menuId: m};
    return rules.menuDuration([
      for (final id in menuIds)
        byId[id]?.defaultDurationMinutes ?? settings.defaultDurationMinutes,
    ], settings.defaultDurationMinutes);
  }

  VisitFormValue value(VisitSettings settings, String? startsAt, String memo) {
    final trimmed = memo.trim();
    return VisitFormValue(
      petIds: ownerOnly ? const [] : petIds.toList(),
      date: date,
      startsAt: startsAt,
      durationMinutes: effectiveDuration(settings),
      menuIds: [...menuIds],
      memo: trimmed.isEmpty ? null : trimmed,
    );
  }
}
```

`app/lib/features/visit/state/day_layout.dart`:

```diff
@@ -100,3 +100,25 @@ List<int> timelineColumns(List<DayGroup> groups) {
   }
   return result;
 }
+
+/// 시간표가 그릴 첫 시와 마지막 시(끝 포함). 영업시간을 기본으로, 그 밖에 걸친 묶음이
+/// 있으면 넓힌다. [settings]가 아직 없으면 10~19시.
+({int first, int last}) timelineHours(
+  VisitSettings? settings,
+  List<DayGroup> active,
+) {
+  var first = settings == null
+      ? 10
+      : int.parse(settings.opensAt.substring(0, 2));
+  var last = settings == null
+      ? 19
+      : int.parse(settings.closesAt.substring(0, 2)) +
+            (int.parse(settings.closesAt.substring(3, 5)) > 0 ? 1 : 0);
+  for (final g in active) {
+    if (g.startsAt.wall.hour < first) first = g.startsAt.wall.hour;
+    final end = g.endsAt;
+    final endHour = end.minute == 0 ? end.hour : end.hour + 1;
+    if (endHour > last) last = endHour;
+  }
+  return (first: first, last: last);
+}
```

`app/lib/features/visit/screens/day_screen.dart`:

```diff
@@ -504,20 +504,7 @@ class _Timeline extends ConsumerWidget {
       for (final g in groups)
         if (g.occupiesTime) g,
     ];
-    // 영업시간을 기본으로, 그 밖의 방문이 있으면 넓힌다.
-    var firstHour = settings == null
-        ? 10
-        : int.parse(settings.opensAt.substring(0, 2));
-    var lastHour = settings == null
-        ? 19
-        : int.parse(settings.closesAt.substring(0, 2)) +
-              (int.parse(settings.closesAt.substring(3, 5)) > 0 ? 1 : 0);
-    for (final g in active) {
-      if (g.startsAt.wall.hour < firstHour) firstHour = g.startsAt.wall.hour;
-      final end = g.endsAt;
-      final endHour = end.minute == 0 ? end.hour : end.hour + 1;
-      if (endHour > lastHour) lastHour = endHour;
-    }
+    final (first: firstHour, last: lastHour) = timelineHours(settings, active);
     final columns = timelineColumns(active);
     final columnCount = columns.isEmpty
         ? 1
```

`app/lib/features/visit/screens/visit_form.dart`:

```diff
@@ -18,56 +18,12 @@ import '../../customer/api/customer_models.dart';
 import '../../customer/state/customer_providers.dart';
 import '../api/visit_models.dart';
 import '../state/visit_commands.dart';
-import '../state/visit_form_rules.dart';
+import '../state/visit_form_draft.dart';
 import '../state/visit_providers.dart';
 import 'visit_labels.dart';
 
-/// 예약 폼이 내보내는 값. [petIds]가 비었으면 보호자만의 방문이다.
-class VisitFormValue {
-  const VisitFormValue({
-    required this.petIds,
-    required this.date,
-    required this.startsAt,
-    required this.durationMinutes,
-    required this.menuIds,
-    required this.memo,
-  });
-
-  final List<int> petIds;
-  final DateTime date;
-
-  /// 서버가 시간 칸으로 준 시각 문자열. 지금 시작이면 null.
-  final String? startsAt;
-  final int durationMinutes;
-  final List<int> menuIds;
-  final String? memo;
-}
-
-/// 폼의 처음 값. [prefilled]면 반려동물을 골라도 "지난번처럼"으로 덮어쓰지
-/// 않는다(다음 예약 초안·수정).
-class VisitFormInitial {
-  const VisitFormInitial({
-    required this.date,
-    this.petIds = const {},
-    this.ownerOnly = false,
-    this.at,
-    this.durationMinutes,
-    this.menus = const [],
-    this.memo,
-    this.prefilled = false,
-  });
-
-  final DateTime date;
-  final Set<int> petIds;
-  final bool ownerOnly;
-
-  /// `HH:MM`.
-  final String? at;
-  final int? durationMinutes;
-  final List<MenuBrief> menus;
-  final String? memo;
-  final bool prefilled;
-}
+// 폼의 값·처음 값은 state/visit_form_draft 에 있다. 이 화면을 import 하던 곳이 그대로 쓰게 다시 내보낸다.
+export '../state/visit_form_draft.dart' show VisitFormInitial, VisitFormValue;
 
 /// 예약 ②(등록)와 수정이 함께 쓰는 폼 — 반려동물 칩, 날짜 줄, 시간 칸,
 /// 메뉴·소요, 메모, 저장 버튼(설계 9.1).
@@ -121,25 +77,10 @@ class VisitForm extends ConsumerStatefulWidget {
 
 class _VisitFormState extends ConsumerState<VisitForm> {
   late final _memo = TextEditingController(text: widget.initial.memo);
-
-  late Set<int> _petIds = {...widget.initial.petIds};
-  late bool _ownerOnly = widget.initial.ownerOnly;
-  late DateTime _date = widget.initial.date;
   late DateTime _stripStart = _weekStart(widget.initial.date);
-  late String? _at = widget.initial.at;
-  late int? _duration = widget.initial.durationMinutes;
-  late List<int> _menuIds = [for (final m in widget.initial.menus) m.menuId];
 
-  /// 보관돼 메뉴표에 없지만 이 방문에 붙어 있는 메뉴(이름을 보이려고 둔다).
-  late List<MenuBrief> _knownMenus = [...widget.initial.menus];
-
-  bool _menusTouched = false;
-  bool _durationTouched = false;
-  bool _prefilledNote = false;
-  bool _petsInitialized = false;
-
-  /// "지난번처럼"은 반려동물을 고를 때마다 나갈 수 있다 — 늦게 온 옛 결과를 버린다.
-  int _defaultsSeq = 0;
+  /// 폼의 상태와 규칙. 위젯은 이것을 바꾸고 `setState`만 부른다.
+  late final _draft = VisitFormDraft(widget.initial);
 
   @override
   void dispose() {
@@ -152,96 +93,49 @@ class _VisitFormState extends ConsumerState<VisitForm> {
 
   String get _exclude => widget.excludeVisitIds.join(',');
 
-  int _effectiveDuration(VisitSettings settings) =>
-      _duration ?? settings.defaultDurationMinutes;
-
-  /// 반려동물이 하나뿐인 보호자면 그 아이를 미리 고른다. 미리 골라진 아이는
-  /// 이 보호자의 아이만 남긴다(카톡 초안이 다른 집 아이를 넘길 수 없게).
+  /// 반려동물이 하나뿐인 보호자면 그 아이를 미리 고르고 "지난번처럼"을 채운다(처음 한 번).
   void _initPets(List<Pet> living) {
-    if (_petsInitialized) return;
-    _petsInitialized = true;
-    _petIds.removeWhere((id) => !living.any((p) => p.petId == id));
-    if (_petIds.isNotEmpty || _ownerOnly || living.length != 1) return;
-    _petIds = {living.single.petId};
-    WidgetsBinding.instance.addPostFrameCallback(
-      (_) => _prefill(living.single.petId),
-    );
+    final only = _draft.initPets(living);
+    if (only != null) {
+      WidgetsBinding.instance.addPostFrameCallback((_) => _prefill(only));
+    }
   }
 
   void _togglePet(int petId) {
-    setState(() {
-      _ownerOnly = false;
-      if (widget.singlePet) {
-        _petIds = {petId};
-      } else if (!_petIds.remove(petId)) {
-        _petIds.add(petId);
-      }
-    });
-    // 한 마리만 남으면(처음 골랐든, 하나를 풀어 하나가 남았든) 그 아이로 채운다.
-    if (_petIds.length == 1) _prefill(_petIds.single);
+    int? only;
+    setState(() => only = _draft.togglePet(petId, single: widget.singlePet));
+    if (only != null) _prefill(only!);
   }
 
-  void _chooseOwnerOnly() {
-    setState(() {
-      _ownerOnly = true;
-      _petIds = {};
-    });
-  }
+  void _chooseOwnerOnly() => setState(_draft.chooseOwnerOnly);
 
   /// 처음 고른 아이의 지난 완료 방문 메뉴·소요로 채운다. 이미 손댔거나
   /// 초안·수정으로 채워진 폼이면 두고, 실패해도 그대로 둔다(돕는 기능이다).
   Future<void> _prefill(int petId) async {
-    if (widget.initial.prefilled || _menusTouched || _durationTouched) return;
-    final seq = ++_defaultsSeq;
+    final seq = _draft.beginPrefill();
+    if (seq == null) return;
     try {
       final defaults = await ref
           .read(visitCommandsProvider)
           .defaults(widget.shopId, petId);
-      if (!mounted || seq != _defaultsSeq) return;
-      if (_menusTouched || _durationTouched) return;
-      setState(() {
-        _menuIds = [for (final m in defaults.menus) m.menuId];
-        _knownMenus = [..._knownMenus, ...defaults.menus];
-        _duration = defaults.durationMinutes;
-        _prefilledNote = defaults.sourceVisitId != null;
-      });
+      if (!mounted) return;
+      setState(() => _draft.applyPrefill(seq, defaults));
     } catch (_) {
       // 미리 채우기는 돕는 것뿐이다 — 실패하면 빈 채로 둔다.
     }
   }
 
-  void _toggleMenu(Menu menu, List<Menu> all, VisitSettings settings) {
-    setState(() {
-      _menusTouched = true;
-      _prefilledNote = false;
-      if (!_menuIds.remove(menu.menuId)) _menuIds.add(menu.menuId);
-      if (!_durationTouched) {
-        final byId = {for (final m in all) m.menuId: m};
-        _duration = menuDuration([
-          for (final id in _menuIds)
-            byId[id]?.defaultDurationMinutes ?? settings.defaultDurationMinutes,
-        ], settings.defaultDurationMinutes);
-      }
-    });
-  }
+  void _toggleMenu(Menu menu, List<Menu> all, VisitSettings settings) =>
+      setState(() => _draft.toggleMenu(menu, all, settings));
 
   void _stepDuration(
     VisitSettings settings, {
     required bool longer,
     bool long = false,
-  }) {
-    setState(() {
-      _durationTouched = true;
-      _prefilledNote = false;
-      _duration = stepDuration(
-        _effectiveDuration(settings),
-        longer: longer,
-        long: long,
-      );
-    });
-  }
+  }) =>
+      setState(() => _draft.stepDuration(settings, longer: longer, long: long));
 
-  void _pickDate(DateTime date) => setState(() => _date = date);
+  void _pickDate(DateTime date) => setState(() => _draft.date = date);
 
   Future<void> _pickMinute(DateTime hour) async {
     final picked = await AppSheet.show<String>(
@@ -268,29 +162,21 @@ class _VisitFormState extends ConsumerState<VisitForm> {
         ],
       ),
     );
-    if (picked != null && mounted) setState(() => _at = picked);
+    if (picked != null && mounted) setState(() => _draft.at = picked);
   }
 
-  VisitFormValue _value(VisitSettings settings, String? startsAt) {
-    final memo = _memo.text.trim();
-    return VisitFormValue(
-      petIds: _ownerOnly ? const [] : _petIds.toList(),
-      date: _date,
-      startsAt: startsAt,
-      durationMinutes: _effectiveDuration(settings),
-      menuIds: [..._menuIds],
-      memo: memo.isEmpty ? null : memo,
-    );
-  }
+  VisitFormValue _value(VisitSettings settings, String? startsAt) =>
+      _draft.value(settings, startsAt, _memo.text);
 
   @override
   Widget build(BuildContext context) {
     final settings = ref.watch(visitSettingsProvider(widget.shopId));
+    // 고객 상세에서 반려동물만 본다 — 전화번호·다가오는 예약이 바뀌어도 폼은 다시 그리지 않는다.
     final customer = ref.watch(
       customerDetailProvider((
         shopId: widget.shopId,
         customerId: widget.customerId,
-      )),
+      )).select((async) => (error: async.error, pets: async.value?.pets)),
     );
     final menus = ref.watch(
       menusProvider((shopId: widget.shopId, includeArchived: false)),
@@ -307,13 +193,13 @@ class _VisitFormState extends ConsumerState<VisitForm> {
       );
     }
     final s = settings.value;
-    final c = customer.value;
+    final pets = customer.pets;
     final m = menus.value;
-    if (s == null || c == null || m == null) {
+    if (s == null || pets == null || m == null) {
       return const Center(child: CircularProgressIndicator());
     }
     final living = [
-      for (final p in c.pets)
+      for (final p in pets)
         if (!p.passedAway || widget.initial.petIds.contains(p.petId)) p,
     ];
     _initPets(living);
@@ -321,30 +207,23 @@ class _VisitFormState extends ConsumerState<VisitForm> {
   }
 
   Widget _buildForm(VisitSettings settings, List<Pet> pets, List<Menu> menus) {
-    // 메뉴만 있고 소요가 없는 초안(카톡)은 메뉴 기본 소요의 합으로 시작한다.
-    if (_duration == null && _menuIds.isNotEmpty && !_durationTouched) {
-      final byId = {for (final m in menus) m.menuId: m};
-      _duration = menuDuration([
-        for (final id in _menuIds)
-          byId[id]?.defaultDurationMinutes ?? settings.defaultDurationMinutes,
-      ], settings.defaultDurationMinutes);
-    }
-    final duration = _effectiveDuration(settings);
-    final selection = _at == null
+    _draft.ensureDuration(menus, settings);
+    final duration = _draft.effectiveDuration(settings);
+    final selection = _draft.at == null
         ? null
         : ref.watch(
             visitSlotsProvider((
               shopId: widget.shopId,
-              date: _date,
+              date: _draft.date,
               duration: duration,
-              at: _at,
+              at: _draft.at,
               exclude: _exclude,
             )),
           );
     final chosen = selection?.value?.slots.firstOrNull;
-    final petsChosen = _ownerOnly || _petIds.isNotEmpty;
+    final petsChosen = _draft.petsChosen;
     final canSubmit =
-        petsChosen && chosen != null && !widget.busy && _at != null;
+        petsChosen && chosen != null && !widget.busy && _draft.at != null;
 
     return ListView(
       padding: const EdgeInsets.fromLTRB(
@@ -358,8 +237,8 @@ class _VisitFormState extends ConsumerState<VisitForm> {
         const SizedBox(height: AppSpacing.md),
         _PetChips(
           pets: pets,
-          selected: _petIds,
-          ownerOnly: _ownerOnly,
+          selected: _draft.petIds,
+          ownerOnly: _draft.ownerOnly,
           locked: widget.scheduleLocked,
           onPet: _togglePet,
           onOwnerOnly: _chooseOwnerOnly,
@@ -368,7 +247,7 @@ class _VisitFormState extends ConsumerState<VisitForm> {
         _DateStrip(
           shopId: widget.shopId,
           start: _stripStart,
-          selected: _date,
+          selected: _draft.date,
           locked: widget.scheduleLocked,
           onMove: (days) => setState(
             () => _stripStart = DateTime(
@@ -394,14 +273,14 @@ class _VisitFormState extends ConsumerState<VisitForm> {
         _SlotGrid(
           slotsKey: (
             shopId: widget.shopId,
-            date: _date,
+            date: _draft.date,
             duration: duration,
             at: null,
             exclude: _exclude,
           ),
-          selectedAt: _at,
+          selectedAt: _draft.at,
           locked: widget.scheduleLocked,
-          onPick: (at) => setState(() => _at = at),
+          onPick: (at) => setState(() => _draft.at = at),
           onLongPress: _pickMinute,
         ),
         if (!widget.scheduleLocked)
@@ -432,10 +311,10 @@ class _VisitFormState extends ConsumerState<VisitForm> {
         const SizedBox(height: AppSpacing.lg),
         _MenuSection(
           menus: menus,
-          knownMenus: _knownMenus,
-          selectedIds: _menuIds,
+          knownMenus: _draft.knownMenus,
+          selectedIds: _draft.menuIds,
           duration: duration,
-          prefilledNote: _prefilledNote,
+          prefilledNote: _draft.prefilledNote,
           onToggle: (menu) => _toggleMenu(menu, menus, settings),
           onShorter: ({bool long = false}) =>
               _stepDuration(settings, longer: false, long: long),
@@ -465,9 +344,9 @@ class _VisitFormState extends ConsumerState<VisitForm> {
         AppButton(
           label: !petsChosen
               ? AppStrings.pickPetFirst
-              : _at == null
+              : _draft.at == null
               ? AppStrings.pickTimeFirst
-              : widget.submitLabel(_date, _at!),
+              : widget.submitLabel(_draft.date, _draft.at!),
           filled: true,
           busy: widget.busy,
           onPressed: canSubmit
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/features/visit/state/visit_form_draft_test.dart test/features/visit/state/day_layout_test.dart test/features/visit/screens/register_visit_screen_test.dart test/features/visit/screens/visit_edit_screen_test.dart test/features/visit/screens/draft_screen_test.dart` → 전부 통과(초안 12, 하루 배치 9 포함)

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 535 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `VisitFormDraft.applyPrefill`의 조건에서 `seq != _defaultsSeq ||`를 뺀다 → `늦게 온 옛 응답은 버린다 — 순서 번호가 최신일 때만 채운다` 실패.
- `VisitFormDraft.toggleMenu`에서 `if (!durationTouched)`를 뺀다(항상 소요를 다시 계산) → `소요를 직접 바꾼 뒤에는 메뉴를 골라도 소요가 따라오지 않는다` 실패.
- `timelineHours`의 `for (final g in active)` 안에서 `first`를 갱신하지 않는다 → `영업시간 밖에 걸친 묶음이 있으면 그만큼 넓힌다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): 예약 폼 규칙을 VisitFormDraft 로 빼고 시간표 범위를 timelineHours 로, 고객 상세는 pets 만 select 한다(A11·A12)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: `GlassSurface` 계약을 `double radius`로 좁힌다 (A13)

**Files:**
- Modify: `app/lib/design/bridge/glass_surface.dart`
- Modify: `app/lib/design/widgets/app_glass_bar.dart`
- Modify: `app/lib/design/widgets/app_glass_card.dart`
- Modify: `app/test/design/glass_surface_test.dart`

**Interfaces:**
- Consumes: `design/bridge/glass_surface.dart`의 `GlassSurfaceFactory.build({child, BorderRadius borderRadius, padding})`, `GlassSurface(borderRadius: BorderRadius)`, 사용처 `AppGlassCard`·`AppGlassBar`.
- Produces: `GlassSurfaceFactory.build({required Widget child, required double radius, EdgeInsetsGeometry? padding})`, `GlassSurface({required Widget child, double radius = 16, EdgeInsetsGeometry? padding})`. 리퀴드 글래스는 `LiquidRoundedRectangle(borderRadius: radius)`, 불투명 표면은 `BorderRadius.circular(radius)`. `AppGlassCard`는 `radius: AppRadius.lg`, `AppGlassBar`는 `radius: AppRadius.pill`.

감사 결과(설계 4.2 A13): 글래스 표면 두 구현이 `BorderRadius`를 다르게 읽었다(리퀴드 글래스는 `topLeft.x`만, 불투명 표면은 네 모서리). 리퀴드 글래스 모양이 대칭 반지름만 받으므로 계약도 그만큼만 약속한다. 두 사용처 모두 대칭 반지름이라 픽셀은 같다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/glass_surface_test.dart`:

```diff
@@ -23,7 +23,9 @@ void main() {
     tester,
   ) async {
     await tester.pumpWidget(
-      const CupertinoApp(home: Center(child: GlassSurface(child: Text('안녕')))),
+      const CupertinoApp(
+        home: Center(child: GlassSurface(child: Text('안녕'))),
+      ),
     );
     await tester.pump();
 
@@ -43,4 +45,32 @@ void main() {
 
     expect(find.byType(GlassContainer), findsNothing);
   });
+
+  testWidgets('반지름 하나가 두 구현에 같은 값으로 닿는다 — 불투명 표면은 네 모서리, 유리는 모양', (
+    tester,
+  ) async {
+    await tester.pumpWidget(
+      const CupertinoApp(
+        home: GlassBridge(
+          factory: OpaqueSurfaceFactory(),
+          child: Center(child: GlassSurface(radius: 24, child: Text('안녕'))),
+        ),
+      ),
+    );
+    final decoration =
+        tester.widget<Container>(find.byType(Container)).decoration
+            as BoxDecoration;
+    expect(decoration.borderRadius, BorderRadius.circular(24));
+
+    await tester.pumpWidget(
+      const CupertinoApp(
+        home: Center(child: GlassSurface(radius: 24, child: Text('안녕'))),
+      ),
+    );
+    await tester.pump();
+    final shape =
+        tester.widget<GlassContainer>(find.byType(GlassContainer)).shape
+            as LiquidRoundedRectangle;
+    expect(shape.borderRadius, 24);
+  });
 }
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/design/glass_surface_test.dart`
Expected: 컴파일 실패 — `GlassSurface`에 `radius` 인자가 없다(`No named parameter with the name 'radius'`).

- [ ] **Step 3: 구현한다**

`app/lib/design/bridge/glass_surface.dart`:

```diff
@@ -9,10 +9,14 @@ import '../tokens/app_shadows.dart';
 /// 구현체를 바꿔치기하면 실제 리퀴드 글래스 렌더러(`GlassContainer`)와
 /// 완전 불투명 대체 표면(`OpaqueSurfaceFactory`)을 동일한 인터페이스로
 /// 다룰 수 있다.
+///
+/// 모서리는 네 곳이 같은 반지름 [radius] 하나다. 리퀴드 글래스 모양이 대칭
+/// 반지름만 받으므로 계약도 그만큼만 약속한다 — 비대칭 반지름을 받아 놓고
+/// 구현마다 다르게 그리던 것을 없앤다.
 abstract class GlassSurfaceFactory {
   Widget build({
     required Widget child,
-    required BorderRadius borderRadius,
+    required double radius,
     EdgeInsetsGeometry? padding,
   });
 }
@@ -27,14 +31,12 @@ class LiquidGlassSurfaceFactory implements GlassSurfaceFactory {
   @override
   Widget build({
     required Widget child,
-    required BorderRadius borderRadius,
+    required double radius,
     EdgeInsetsGeometry? padding,
   }) {
-    // LiquidRoundedRectangle은 모서리 반지름을 double 하나로 받는다(대칭 모양
-    // 전용). 카드류는 보통 네 모서리가 같으므로 topLeft 값을 대표로 쓴다.
     return GlassContainer(
       useOwnLayer: true,
-      shape: LiquidRoundedRectangle(borderRadius: borderRadius.topLeft.x),
+      shape: LiquidRoundedRectangle(borderRadius: radius),
       padding: padding,
       child: child,
     );
@@ -55,14 +57,14 @@ class OpaqueSurfaceFactory implements GlassSurfaceFactory {
   @override
   Widget build({
     required Widget child,
-    required BorderRadius borderRadius,
+    required double radius,
     EdgeInsetsGeometry? padding,
   }) {
     return Container(
       padding: padding,
       decoration: BoxDecoration(
         color: _fill,
-        borderRadius: borderRadius,
+        borderRadius: BorderRadius.circular(radius),
         border: Border.all(color: AppColors.line, width: 1),
         boxShadow: AppShadows.soft,
       ),
@@ -113,12 +115,14 @@ class GlassSurface extends StatelessWidget {
   const GlassSurface({
     super.key,
     required this.child,
-    this.borderRadius = const BorderRadius.all(Radius.circular(16)),
+    this.radius = 16,
     this.padding,
   });
 
   final Widget child;
-  final BorderRadius borderRadius;
+
+  /// 네 모서리 공통 반지름.
+  final double radius;
   final EdgeInsetsGeometry? padding;
 
   @override
@@ -130,7 +134,7 @@ class GlassSurface extends StatelessWidget {
         : GlassBridge.of(context);
     return factory.build(
       child: child,
-      borderRadius: borderRadius,
+      radius: radius,
       padding: padding,
     );
   }
```

`app/lib/design/widgets/app_glass_bar.dart`:

```diff
@@ -33,7 +33,7 @@ class AppGlassBar extends StatelessWidget {
   @override
   Widget build(BuildContext context) {
     return GlassSurface(
-      borderRadius: const BorderRadius.all(Radius.circular(AppRadius.pill)),
+      radius: AppRadius.pill,
       padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
       child: SizedBox(
         height: 56,
```

`app/lib/design/widgets/app_glass_card.dart`:

```diff
@@ -21,7 +21,7 @@ class AppGlassCard extends StatelessWidget {
   @override
   Widget build(BuildContext context) {
     return GlassSurface(
-      borderRadius: const BorderRadius.all(Radius.circular(AppRadius.lg)),
+      radius: AppRadius.lg,
       padding: padding,
       child: child,
     );
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/design` → 전부 통과(글래스 4 포함)

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 536 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `OpaqueSurfaceFactory.build`의 `BorderRadius.circular(radius)`를 `BorderRadius.circular(16)`으로 → `반지름 하나가 두 구현에 같은 값으로 닿는다 — 불투명 표면은 네 모서리, 유리는 모양` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(app): GlassSurface 계약을 double radius 로 좁힌다(A13)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: `core/proxy`에 `clipboardProvider`와 `UploadClient`를 둔다 (A4·A5)

**Files:**
- Create: `app/lib/core/proxy/clipboard.dart`
- Create: `app/lib/core/proxy/upload_client.dart`
- Modify: `app/lib/core/proxy/providers.dart`
- Modify: `app/lib/features/shop/screens/members_screen.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Create: `app/test/core/proxy/clipboard_test.dart`
- Modify: `app/test/core/proxy/providers_test.dart`
- Create: `app/test/core/proxy/upload_client_test.dart`
- Modify: `app/test/features/shop/screens/members_screen_test.dart`
- Modify: `app/test/features/visit/screens/draft_screen_test.dart`
- Create: `app/test/support/fake_clipboard.dart`

**Interfaces:**
- Consumes: `register_visit_screen.dart`의 `Clipboard.getData`, `members_screen.dart`의 `Clipboard.setData`, `core/proxy/providers.dart`의 `dioProvider` 선례, `core/error/api_exception.dart`의 `ApiException.fromDioException`, 테스트 지원 `test/support/fake_http_client_adapter.dart`(`FakeHttpClientAdapter`·`FakeResponse`).
- Produces: `lib/core/proxy/clipboard.dart` — `abstract class AppClipboard { Future<String?> readText(); Future<void> writeText(String text); }`, `SystemClipboard`, `clipboardProvider: Provider<AppClipboard>`; `lib/core/proxy/upload_client.dart` — `class UploadClient { UploadClient({Dio? dio}); static const connectTimeout = Duration(seconds: 10); static const receiveTimeout = Duration(seconds: 30); Future<void> put(Uri url, {required Stream<List<int>> body, required int length, required String contentType, ProgressCallback? onSendProgress, CancelToken? cancelToken}); }` — 인증 헤더 없음, 송신 타임아웃 없음, 재시도 없음, 오류는 `ApiException`; `providers.dart`의 `uploadDioProvider: Provider<Dio>`(민짜)·`uploadClientProvider: Provider<UploadClient>`; `test/support/fake_clipboard.dart`의 `FakeClipboard([String? text])`(`text` 필드). 화면 둘은 `ref.read(clipboardProvider).readText()/writeText(...)`를 부르고 `flutter/services` import 가 사라진다. 기존 초안·멤버 화면 테스트는 플랫폼 채널 mock 대신 `clipboardProvider.overrideWithValue(FakeClipboard(...))`를 쓴다.

감사 결과(설계 4.2 A4·A5): 화면이 `Clipboard`를 직접 불렀고, presigned PUT 에 필요한 "인증 헤더 없음 + 진행률"이 `ApiClient`에 없었다. **설계와 다른 점**(결정 기록 007): 플러그인 프로바이더는 클립보드만 — 사진 선택기·마이크는 그 패키지가 들어오는 ④-2·④-3 에서 같은 모양으로 더한다(지금 넣으면 아무도 부르지 않는 코드다). `UploadClient`는 송신 타임아웃을 두지 않는다(dio 의 `sendTimeout`은 바이트 전체에 걸려 큰 영상이 느린 망에서 끊긴다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/core/proxy/clipboard_test.dart`:

```dart
import 'package:chagocnote/core/proxy/clipboard.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('SystemClipboard 는 플랫폼 클립보드를 읽고 쓴다', () async {
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
          calls.add(call);
          if (call.method == 'Clipboard.getData') return {'text': '콩이'};
          return null;
        });
    addTearDown(
      () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(SystemChannels.platform, null),
    );

    const clipboard = SystemClipboard();
    expect(await clipboard.readText(), '콩이');
    await clipboard.writeText('ABC123');
    expect(calls.map((c) => c.method), [
      'Clipboard.getData',
      'Clipboard.setData',
    ]);
    expect(calls.last.arguments, {'text': 'ABC123'});
  });
}
```

`app/test/core/proxy/providers_test.dart`:

```diff
@@ -1,4 +1,5 @@
 import 'package:chagocnote/core/proxy/providers.dart';
+import 'package:chagocnote/core/proxy/upload_client.dart';
 import 'package:dio/dio.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
@@ -19,4 +20,22 @@ void main() {
       expect(options.sendTimeout, const Duration(seconds: 15));
     });
   }
+
+  test('uploadDioProvider 는 인터셉터가 없고 연결 타임아웃만 건다 — 송신 타임아웃은 큰 영상을 끊는다', () {
+    final container = ProviderContainer.test();
+    final dio = container.read(uploadDioProvider);
+
+    expect(
+      dio.interceptors.whereType<InterceptorsWrapper>(),
+      isEmpty,
+      reason: 'ApiClient 의 토큰 인터셉터(InterceptorsWrapper)가 붙으면 안 된다',
+    );
+    expect(dio.options.connectTimeout, const Duration(seconds: 10));
+    expect(dio.options.sendTimeout, isNull);
+  });
+
+  test('uploadClientProvider 는 uploadDioProvider 의 Dio 를 쓴다', () {
+    final container = ProviderContainer.test();
+    expect(container.read(uploadClientProvider), isA<UploadClient>());
+  });
 }
```

`app/test/core/proxy/upload_client_test.dart`:

```dart
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/upload_client.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

final _url = Uri.parse('https://media.example/bucket/key?X-Amz-Signature=abc');
final _bytes = Uint8List.fromList(List<int>.generate(2048, (i) => i % 251));

({UploadClient client, FakeHttpClientAdapter adapter}) _setUp(
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return (client: UploadClient(dio: dio), adapter: adapter);
}

void main() {
  test('PUT 은 인증 헤더 없이 바디·content-type·길이를 보내고 진행률을 알린다', () async {
    final setup = _setUp(
      (options, body) => const FakeResponse(statusCode: 200),
    );
    final progress = <(int, int)>[];

    await setup.client.put(
      _url,
      body: Stream.value(_bytes),
      length: _bytes.length,
      contentType: 'image/jpeg',
      onSendProgress: (sent, total) => progress.add((sent, total)),
    );

    final request = setup.adapter.requests.single;
    expect(request.method, 'PUT');
    expect(request.uri, _url);
    expect(
      request.headers.keys.map((k) => k.toLowerCase()),
      isNot(contains('authorization')),
    );
    expect(request.headers[Headers.contentTypeHeader], 'image/jpeg');
    expect(request.headers[Headers.contentLengthHeader], _bytes.length);
    expect(setup.adapter.lastBodyByPath[request.path], _bytes);
    expect(progress, isNotEmpty);
    expect(progress.last, (_bytes.length, _bytes.length));
  });

  test('저장소가 거절하면 ApiException 으로 던지고 다시 보내지 않는다', () async {
    final setup = _setUp(
      (options, body) => const FakeResponse(
        statusCode: 403,
        data: '<Error><Code>AccessDenied</Code></Error>',
      ),
    );

    await expectLater(
      setup.client.put(
        _url,
        body: Stream.value(_bytes),
        length: _bytes.length,
        contentType: 'image/jpeg',
      ),
      throwsA(
        isA<ApiException>().having((e) => e.statusCode, 'statusCode', 403),
      ),
    );
    expect(setup.adapter.requests, hasLength(1));
  });

  test('연결 오류는 NETWORK 로 던진다', () async {
    final setup = _setUp(
      (options, body) => throw DioException.connectionError(
        requestOptions: options,
        reason: '끊김',
      ),
    );

    await expectLater(
      setup.client.put(
        _url,
        body: Stream.value(_bytes),
        length: _bytes.length,
        contentType: 'video/mp4',
      ),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'NETWORK')),
    );
  });
}
```

`app/test/features/shop/screens/members_screen_test.dart`:

```diff
@@ -3,6 +3,7 @@
 // `apiClientProvider`를 가짜 어댑터로 문 진짜 `ShopApi`로 검증한다 — 두
 // 계층이 서로 다른 경로(세션 vs 매장 API)를 타기 때문에 각각 가짜로
 // 대체하는 쪽이 더 명확하다.
+import 'package:chagocnote/core/proxy/clipboard.dart';
 import 'package:chagocnote/core/proxy/api_client.dart';
 import 'package:chagocnote/core/proxy/providers.dart';
 import 'package:chagocnote/core/router/app_router.dart';
@@ -21,6 +22,7 @@ import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:flutter_test/flutter_test.dart';
 
+import '../../../support/fake_clipboard.dart';
 import '../../../support/fake_http_client_adapter.dart';
 import '../../../support/fake_session_gateway.dart';
 
@@ -62,11 +64,17 @@ const _membersJson = [
   },
 ];
 
-({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
+({
+  ProviderContainer container,
+  FakeHttpClientAdapter adapter,
+  FakeClipboard clipboard,
+})
+_setUp(
   FakeSessionGateway gateway,
   FakeHandler handle,
 ) {
   final adapter = FakeHttpClientAdapter(handle);
+  final clipboard = FakeClipboard();
   // dio(원 요청)와 refreshDio(리프레시 전용)는 같은 인스턴스를 쓰지 않는다 —
   // 같은 인터셉터를 타는 하나의 Dio를 둘 다에 쓰면 리프레시 요청 자체가
   // 401을 받았을 때 다시 리프레시를 시도하는 재귀에 빠질 위험이 있다
@@ -77,6 +85,7 @@ const _membersJson = [
     retry: (retryCount, error) => null,
     overrides: [
       sessionGatewayProvider.overrideWithValue(gateway),
+      clipboardProvider.overrideWithValue(clipboard),
       apiClientProvider.overrideWith(
         (ref) => ApiClient(
           tokenStore: _NoopTokenStore(),
@@ -87,7 +96,7 @@ const _membersJson = [
       ),
     ],
   );
-  return (container: container, adapter: adapter);
+  return (container: container, adapter: adapter, clipboard: clipboard);
 }
 
 Widget _appWith(ProviderContainer container) {
@@ -194,6 +203,11 @@ void main() {
     final invitePosts = setup.adapter.requests
         .where((r) => r.path == '/v1/shops/3/invites' && r.method == 'POST');
     expect(invitePosts, hasLength(1));
+
+    // [복사]는 화면이 플러그인을 직접 부르지 않고 클립보드 프로바이더에 쓴다(A4).
+    await tester.tap(find.text(AppStrings.copy));
+    await tester.pump();
+    expect(setup.clipboard.text, 'ABC123');
   });
 
   testWidgets('역할 변경은 PATCH 를 보내고 목록을 새로고침한다', (tester) async {
```

`app/test/features/visit/screens/draft_screen_test.dart`:

```diff
@@ -3,13 +3,14 @@ import 'dart:async';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/design/widgets/app_chip.dart';
+import 'package:chagocnote/core/proxy/clipboard.dart';
 import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
-import 'package:flutter/services.dart';
 import 'package:flutter_test/flutter_test.dart';
 
 import '../../../support/customer_fixtures.dart';
 import '../../../support/customer_test_app.dart';
+import '../../../support/fake_clipboard.dart';
 import '../../../support/fake_http_client_adapter.dart';
 import '../../../support/visit_fixtures.dart';
 import '../../../support/visit_test_backend.dart';
@@ -34,21 +35,6 @@ Finder _guessChips() => find.byWidgetPredicate(
   (w) => w is AppChip && w.label == AppStrings.draftGuessed,
 );
 
-/// `Clipboard.getData`가 [text]를 돌려주게 한다(null 이면 빈 클립보드).
-void _mockClipboard(WidgetTester tester, String? text) {
-  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
-      .setMockMethodCallHandler(SystemChannels.platform, (call) async {
-        if (call.method == 'Clipboard.getData') {
-          return text == null ? null : {'text': text};
-        }
-        return null;
-      });
-  addTearDown(
-    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
-        .setMockMethodCallHandler(SystemChannels.platform, null),
-  );
-}
-
 void main() {
   testWidgets(
     '후보가 하나면 고른 상태로 보이고 짐작한 칸에 표시가 붙으며, [예약 이어서]가 ②를 채워 열고 저장한 날짜를 돌려준다',
@@ -261,7 +247,11 @@ void main() {
       draftBody = bodyOf(body);
       return FakeResponse(statusCode: 200, data: visitDraftJson());
     };
-    final setup = CustomerTestSetup(backend.call, overrides: _today);
+    final clipboard = FakeClipboard('가' * 1200);
+    final setup = CustomerTestSetup(
+      backend.call,
+      overrides: [..._today, clipboardProvider.overrideWithValue(clipboard)],
+    );
     addTearDown(setup.container.dispose);
     await _open(
       tester,
@@ -270,7 +260,6 @@ void main() {
       extra: null,
     );
 
-    _mockClipboard(tester, '가' * 1200);
     await tester.tap(_button(AppStrings.pasteFromKakao));
     await settle(tester);
     expect((draftBody?['text'] as String).length, 1000);
@@ -285,7 +274,11 @@ void main() {
       draftBody = bodyOf(body);
       return FakeResponse(statusCode: 200, data: visitDraftJson());
     };
-    final setup = CustomerTestSetup(backend.call, overrides: _today);
+    final clipboard = FakeClipboard();
+    final setup = CustomerTestSetup(
+      backend.call,
+      overrides: [..._today, clipboardProvider.overrideWithValue(clipboard)],
+    );
     addTearDown(setup.container.dispose);
     final result = await _open(
       tester,
@@ -294,13 +287,12 @@ void main() {
       extra: null,
     );
 
-    _mockClipboard(tester, null);
     await tester.tap(_button(AppStrings.pasteFromKakao));
     await settle(tester);
     expect(find.text(AppStrings.clipboardEmpty), findsOneWidget);
     expect(find.byKey(ScreenKeys.visitDraft), findsNothing);
 
-    _mockClipboard(tester, '  $_text  ');
+    clipboard.text = '  $_text  ';
     await tester.tap(_button(AppStrings.pasteFromKakao));
     await settle(tester);
     expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
```

`app/test/support/fake_clipboard.dart`:

```dart
import 'package:chagocnote/core/proxy/clipboard.dart';

/// 메모리 클립보드. 테스트가 `clipboardProvider`를 이걸로 override 한다.
class FakeClipboard implements AppClipboard {
  FakeClipboard([this.text]);

  String? text;

  @override
  Future<String?> readText() async => text;

  @override
  Future<void> writeText(String value) async => text = value;
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/core/proxy/upload_client_test.dart test/core/proxy/clipboard_test.dart`
Expected: 컴파일 실패 — `lib/core/proxy/upload_client.dart`·`clipboard.dart` 없음.

- [ ] **Step 3: 구현한다**

`app/lib/core/proxy/clipboard.dart`:

```dart
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 클립보드 — 화면이 [Clipboard] 플러그인을 직접 부르지 않게 감싼 자리.
///
/// 사진 선택기·카메라·마이크(④-2·④-3)도 같은 모양으로 `core/proxy/`에 둔다.
/// 화면은 프로바이더만 읽고, 테스트는 프로바이더를 override 한다.
abstract class AppClipboard {
  /// 클립보드의 글. 비었거나 글이 아니면 null.
  Future<String?> readText();

  Future<void> writeText(String text);
}

/// 실제 기기의 클립보드.
class SystemClipboard implements AppClipboard {
  const SystemClipboard();

  @override
  Future<String?> readText() async =>
      (await Clipboard.getData(Clipboard.kTextPlain))?.text;

  @override
  Future<void> writeText(String text) =>
      Clipboard.setData(ClipboardData(text: text));
}

final clipboardProvider = Provider<AppClipboard>(
  (ref) => const SystemClipboard(),
);
```

`app/lib/core/proxy/upload_client.dart`:

```dart
import 'package:dio/dio.dart';

import '../error/api_exception.dart';

/// 서명(presigned) URL 로 파일을 올리는 전용 클라이언트.
///
/// [ApiClient]와 다른 점 세 가지가 이 클래스가 따로 있는 이유다.
/// - 인증 헤더가 없다. 서명 URL 이 곧 권한이라 액세스 토큰이 붙으면 저장소가 거절한다.
/// - 진행률([onSendProgress])을 준다. 사진·영상은 몇 초씩 걸린다.
/// - 재시도가 없다. 서명 URL 은 수명이 있어 다시 올릴지는 호출자가 정한다.
///
/// 오류는 [ApiException]으로 던진다(연결·타임아웃은 `NETWORK`, 저장소 거절은 상태 코드).
class UploadClient {
  UploadClient({Dio? dio})
    : _dio = dio ?? Dio(BaseOptions(connectTimeout: connectTimeout));

  /// 송신 타임아웃은 두지 않는다 — dio 의 송신 타임아웃은 바이트 전체에 걸려 큰 영상이
  /// 느린 망에서 끊긴다. 연결과 응답 대기만 제한한다.
  static const connectTimeout = Duration(seconds: 10);
  static const receiveTimeout = Duration(seconds: 30);

  final Dio _dio;

  /// [url]에 [body]를 PUT 한다. [length]는 바이트 수(서명에 들어가므로 정확해야 한다).
  Future<void> put(
    Uri url, {
    required Stream<List<int>> body,
    required int length,
    required String contentType,
    ProgressCallback? onSendProgress,
    CancelToken? cancelToken,
  }) async {
    try {
      await _dio.putUri<void>(
        url,
        data: body,
        options: Options(
          headers: {
            Headers.contentTypeHeader: contentType,
            Headers.contentLengthHeader: length,
          },
          receiveTimeout: receiveTimeout,
        ),
        onSendProgress: onSendProgress,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    }
  }
}
```

`app/lib/core/proxy/providers.dart`:

```diff
@@ -5,6 +5,7 @@ import '../config/app_config.dart';
 import '../storage/prefs_store.dart';
 import '../storage/token_store.dart';
 import 'api_client.dart';
+import 'upload_client.dart';
 
 final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromEnvironment());
 
@@ -64,3 +65,13 @@ final apiClientProvider = Provider<ApiClient>((ref) {
     onSessionEnded: signal.fire,
   );
 });
+
+/// [UploadClient]가 쓰는 민짜 `Dio`. 인터셉터도 인증도 없다. 테스트는 [dioProvider]처럼
+/// 가짜 어댑터를 문 `Dio`를 꽂는다.
+final uploadDioProvider = Provider<Dio>(
+  (ref) => Dio(BaseOptions(connectTimeout: UploadClient.connectTimeout)),
+);
+
+final uploadClientProvider = Provider<UploadClient>(
+  (ref) => UploadClient(dio: ref.watch(uploadDioProvider)),
+);
```

`app/lib/features/shop/screens/members_screen.dart`:

```diff
@@ -1,8 +1,8 @@
 import 'package:flutter/material.dart';
-import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
 import '../../../core/error/error_messages.dart';
+import '../../../core/proxy/clipboard.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
@@ -65,8 +65,7 @@ class _MembersScreenState extends ConsumerState<MembersScreen> {
           const SizedBox(height: AppSpacing.lg),
           AppButton(
             label: AppStrings.copy,
-            onPressed: () =>
-                Clipboard.setData(ClipboardData(text: invite.code)),
+            onPressed: () => ref.read(clipboardProvider).writeText(invite.code),
           ),
         ],
       ),
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -1,10 +1,10 @@
 import 'package:flutter/material.dart';
-import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
 import '../../../core/error/api_exception.dart';
 import '../../../core/error/error_messages.dart';
+import '../../../core/proxy/clipboard.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
 import '../../../design/tokens/app_spacing.dart';
@@ -301,8 +301,8 @@ class _CustomerSearchState extends ConsumerState<_CustomerSearch> {
   /// 클립보드의 카톡 글로 초안 화면을 연다(③-A3). 초안에서 예약을 저장하고
   /// 돌아오면 ①도 그 날짜로 닫힌다 — 홈이 그날을 고른다.
   Future<void> _pasteFromKakao(BuildContext context) async {
-    final data = await Clipboard.getData(Clipboard.kTextPlain);
-    var text = data?.text?.trim() ?? '';
+    final data = await ref.read(clipboardProvider).readText();
+    var text = data?.trim() ?? '';
     if (!context.mounted) return;
     if (text.isEmpty) {
       setState(() => _pasteNote = AppStrings.clipboardEmpty);
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s test/core/proxy test/features/shop/screens/members_screen_test.dart test/features/visit/screens/draft_screen_test.dart` → 전부 통과(proxy 35)

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 30s` → 542 passed(골든 포함, `test/**/failures/` 없음)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `UploadClient.put`의 헤더에 `'authorization': 'Bearer x'`를 더한다 → `PUT 은 인증 헤더 없이 바디·content-type·길이를 보내고 진행률을 알린다` 실패.
- `UploadClient.put`의 `throw ApiException.fromDioException(e)`를 `rethrow`로 → `저장소가 거절하면 ApiException 으로 던지고 다시 보내지 않는다` 실패.
- `members_screen.dart`의 [복사] `onPressed`를 `() {}`로 → `members_screen_test.dart::초대 코드를 만들면 코드를 보여주고 POST 요청을 보낸다` 실패(클립보드가 비어 있다).
- `register_visit_screen.dart`의 `_pasteFromKakao`가 프로바이더 대신 `null`을 읽는다 → `draft_screen_test.dart::붙여넣은 글이 1000자를 넘으면 앞 1000자만 보낸다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): core/proxy 에 clipboardProvider 와 UploadClient 를 둔다(A4·A5)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: 문서 — 앱 CLAUDE(플러그인 프로바이더·상태 enum), 하네스(앱 구조 테스트), 결정 기록 007(④-0 앱 절)

**Files:**
- Modify: `app/CLAUDE.md`
- Modify: `_docs/harness.md`
- Modify: `_docs/decisions/007-record-media.md`

**Interfaces:**
- Consumes: 작업 1~10 이 세운 규칙과 이름.
- Produces: `app/CLAUDE.md`에 규칙 두 줄(플러그인은 `core/proxy` 프로바이더로만, 상태 문자열은 `fromJson`에서 enum 으로 한 번만), `_docs/harness.md`에 앱 구조 테스트 행과 설명 줄, `_docs/decisions/007-record-media.md`에 "④-0 SOLID 정리(앱)에서 정한 것" 절(설계와 다르게 간 것 열 가지, 남는 것 셋).

이 작업은 코드가 없다. 문서 셋의 diff 를 그대로 적용한다. 결정 기록의 내용은 작업 1~10 의 머리말과 같다 — 실행 중 판정이 달라진 것이 있으면(검토가 더한 테스트 등) 그 사실을 이 절 끝에 한 줄 더한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

이 작업은 테스트가 없다(문서). 적용 전 `git status`가 깨끗한지 본다.

- [ ] **Step 3: 구현한다**

`app/CLAUDE.md`:

```diff
@@ -8,6 +8,8 @@
 - 폴더는 `lib/core/{config,proxy,storage,router,error}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
 - **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`가 채운다. 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
 - 화면은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다. `auth/state/shop_selection.dart`의 파생 프로바이더(`selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider`·`shopCountProvider`·`currentUserIdProvider`)만 watch 한다.
+- 플러그인(클립보드, 앞으로의 사진 선택기·카메라·마이크)은 `lib/core/proxy/`의 프로바이더(`clipboardProvider` 등)로만 부른다. 화면은 `flutter/services`의 `Clipboard`를 직접 부르지 않는다. 테스트는 프로바이더를 override 한다. 서명 URL 업로드는 `core/proxy/upload_client.dart`(인증 헤더 없음·진행률·재시도 없음)로 한다.
+- 서버의 상태 문자열은 `fromJson`에서 enum(`VisitStatus`·`VisitAction`)으로 한 번만 바꾼다. 화면의 `switch`는 `_ =>` 폴백 없이 완전 열거한다 — 상태·행동을 더하면 컴파일러가 빠진 곳을 찾는다.
 - 서버 응답의 필드명은 변환하지 않는다. 모델은 평범한 클래스에 `fromJson` 을 직접 쓴다. 코드 생성기를 도입하지 않는다.
 - `liquid_glass_widgets` 는 `lib/design/bridge/` 안에서만 import 한다. 화면은 `lib/design/widgets` 만 쓴다.
 - 토큰을 로그에 남기지 않는다. `print`·`debugPrint`·dio `LogInterceptor` 를 쓰지 않는다(`avoid_print` 는 오류다).
```

`_docs/harness.md`:

```diff
@@ -19,6 +19,7 @@
 | 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
 | 앱 정적 분석 | `flutter analyze` (`app/`에서, 경고 0) |
 | 앱 테스트 (위젯·골든·`ApiClient` 포함) | `flutter test --timeout 30s` (`app/`에서. 화면이 닫히기를 잘못 기다리는 테스트가 기본 10분을 멈추지 않게) |
+| 앱 구조 테스트 (기능 폴더 import 방향·라우터 가드 전수) | `flutter test test/design/feature_imports_test.dart test/core/router/app_router_test.dart` (`app/`에서. 전체 테스트에 포함되지만 구조를 건드린 변경은 이 둘을 먼저 돌린다) |
 | 앱 골든 갱신 | `flutter test --update-goldens` (`app/`에서, 의도해서 바꿀 때만) |
 | 앱 개발용 실행 | `app/tool/run_dev.sh` (백엔드를 `infra/`에서 먼저 띄운 뒤) |
 | 앱 흐름 확인 (시뮬레이터 + 실서버) | `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/<파일> -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 …` (`app/`에서. 파일 머리 주석에 준비와 추가 `--dart-define`이 있다 — `visit_flow_test.dart`(③-A2), `draft_flow_test.dart`(③-A3 카톡 초안)) |
@@ -28,6 +29,7 @@
 - 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 마이그레이션 결과와 ORM이 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에 등록한다.
 - 구조 위반은 테스트가 아니라 import-linter가 잡는다. 구조를 건드린 변경은 테스트와 구조 계약을 둘 다 돌린다. 계약은 6종이다 — 설계 문서가 말하는 5종에 "core는 스포크를 import하지 않는다"를 하네스에서 더했다.
 - 라우터를 추가하거나 옮긴 변경은 라우트 표를 변경 전후로 비교한다.
+- 앱의 구조 위반은 `test/design/feature_imports_test.dart`(기능 폴더 사이 import 는 `auth` 공용·`home` 껍데기·`visit → customer`만)와 `test/core/router/app_router_test.dart`(열린 경로 목록 밖의 모든 경로는 매장 선택이 없으면 막힌다)가 잡는다. 기능 폴더나 경로를 더한 변경은 이 둘을 돌린다.
 - 유스케이스는 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다. 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간 잡힌다(`apps/*/tests/test_fakes_are_ports.py`). 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 상속하지 않는다.
 - `tests/integration/`은 두 프로세스의 실제 앱 객체에 붙어 프로바이더·DB 커밋·Redis까지 통과한다. 인증 프로세스의 개인키는 테스트마다 새로 만든 키로 바꿔 넣는다.
 - 스포크를 새로 만들면 첫 통합 테스트로 "A매장 멤버가 B매장의 경로를 부르면 403"(테넌트 격리)을 둔다.
```

`_docs/decisions/007-record-media.md`:

```diff
@@ -30,3 +30,26 @@
 - `completion_changed`를 `touches_completion`으로 바꿨다. 판정은 "전후 어느 쪽에든 완료 방문이 있는가"이고 둘 다 완료여도 참이다(후속 처리는 멱등). ④-1 의 기록 유스케이스가 이 함수를 부를 때 "최근 방문일 때만 몸무게 동기화" 같은 조건은 `apply_completion_effects` 안에서 따로 판정한다. 계획서(작업 4)의 코드 블록은 옛 이름 그대로다 — 계획서는 실행 기록이라 고치지 않았다.
 - 탈퇴 인터랙터 테스트의 스텁이 자체 예외 대신 허브 오류 `WithdrawalOwnershipTransferRequiredError`를 던진다(설계 B2 "스텁도 같은 예외"). 오류 배선 통합 테스트의 docstring 이 "리포지토리 오류가 샐 수도 있다"고 하던 것을 사실("포트 구현은 도메인 오류를 내보내지 않는다; tenancy 맵 등록은 방어용")로 고쳤다.
 - 미룬 것(최종 검토 판정): import 정렬 세 테스트 파일, `membership_lifecycle_port.py` 긴 docstring 줄, `test_포트끼리_메서드가_겹치지_않는다` docstring, `visit_orm.py`의 상태별 칸 CHECK 에 남은 `'canceled'`·`'completed'` 리터럴, `test_visit_status.py`의 비공개 `_STATES` import, `visit_board.COUNTED` 별칭, `RecentLogin(auth_time=…)`의 정적 타입 `int | None`. 기각한 것: 분리 구조 테스트의 사용 차원 검사(타입 힌트가 계약), 서비스 함수 둘의 포트 검사, `X | None` 힌트, `phone_digits` 재계산, 가드 테스트의 키 쌍 직접 생성(`now` 고정에 필요).
+
+## ④-0 SOLID 정리(앱)에서 정한 것
+
+2026-09-24 감사(설계 4.2절 A1~A13)를 기능 코드 없이 적용했다. 검증 기준은 "`flutter analyze` 0, 테스트 전부 통과, 골든은 의도한 것만 갱신"이었고 그대로 지켰다(테스트 502 → 542, 골든 변경 없음, 새 의존성 없음).
+
+### 설계와 다르게 간 것
+
+- **완료 후속 행동은 둘.** 설계 A1 은 `AfterComplete { none, nextReservation, record }`를 말했다. `record`(기록 화면으로)는 기록 화면이 생기는 ④-2 의 것이라 지금은 `AfterNothing`·`AfterNextReservation(draft)` 둘만 두고 sealed 로 닫았다. ④-2 가 셋째를 더하면 `sendVisitAction`의 `switch`가 빠진 분기를 컴파일 오류로 알린다. 모르는 상태 문자열은 `VisitStatus.unknown`으로 받고 시간표에서는 자리를 차지한다(`occupiesTime`) — 새 상태가 서버에 먼저 들어와도 화면이 방문을 숨기지 않게.
+- **`PrefsStore`에 `remove(key)`는 없다.** 설계 A3 이 말한 `remove`를 쓰는 곳이 없어 넣지 않았다. 대신 `clear()`는 "로그아웃 때 지우는 것"(마지막 매장)만 지우고 보기 방식은 남긴다 — 전에도 그랬다. 키는 `PrefsKeys`에 모아 두고, 컨트롤러는 `ViewModeController<T extends Enum>(key, values, fallback)` 하나다. [달력/피드] 토글(④-2)은 키 하나와 프로바이더 한 줄이다.
+- **플러그인 프로바이더는 클립보드만.** 설계 A4 의 `mediaPickerProvider`·`speechRecognizerProvider`는 그 패키지가 들어오는 ④-2·④-3 에서 같은 모양(`core/proxy/<이름>.dart` 의 추상 + 실제 구현 + 프로바이더, 테스트는 `FakeX`로 override)으로 더한다. 지금 넣으면 아무도 부르지 않는 코드가 된다.
+- **이미지 로더(A6)는 ④-2 로.** `media_id`를 캐시 키로 쓰는 로더는 이미지 캐시 패키지가 필요하고 부르는 화면도 ④-2 에 있다. 새 의존성 없음이 ④-0 의 제약이라 미뤘다.
+- **`UploadClient`는 송신 타임아웃을 두지 않는다.** dio 의 `sendTimeout`은 바이트 전체에 걸려 큰 영상이 느린 망에서 끊긴다. 연결 10초·응답 30초만 제한한다. 오류는 `ApiException`으로 바꿔 던진다(저장소의 XML 오류 바디는 `HTTP_ERROR` + 상태 코드가 된다).
+- **홈 탭 목록은 비공개 `_HomeTab`.** 설계 A7 의 `HomeTab`을 밖으로 내보낼 이유가 없어 `home_shell.dart` 안에 뒀다. 탭 추가는 목록에 한 줄이다.
+- **라우터 가드는 목록이 아니라 규칙 하나다.** 설계 A8 은 "기본을 매장 범위로 뒤집고 예외만 열거"였다. 옛 `_isShopScoped`(접두사 목록) 분기는 매장이 하나면 세션이 자동으로 고르므로 닿을 수 없는 코드였다(변이 검사에서 가드를 꺼도 테스트가 통과해 드러났다). 지웠다. "선택 없음"은 매장이 둘 이상일 때뿐이고 그때는 계정 경로(`accountRoutes` 둘) 밖 전부가 매장 선택으로 밀린다. 테스트는 라우터의 모든 `GoRoute`를 돌며 이를 확인한다 — 경로를 더하면 자동으로 검사되고, 계정 경로에 매장 범위 경로를 넣거나 규칙을 지우면 실패한다.
+- **기능 폴더 규칙(A9)에서 ③·④는 지금 필요 없다.** `customer → visit` import 는 시각 도우미뿐이라 `core/time`으로 옮기니 사라졌다 — `core/plugs/` 자리는 반려동물 상세의 [기록] 탭이 생기는 ④-2 에서 만든다. `visit_commands`가 customer 프로바이더를 무효화하는 것은 허용 방향(`visit → customer`)이라 `ShopDataChanged` 신호로 바꾸지 않았다. 구조 테스트는 `test/structure/`가 아니라 기존 폴더 `test/design/feature_imports_test.dart`에 뒀다(구조 테스트는 그 폴더의 `glass_boundary_test.dart`가 선례). 메뉴·일정 설정 화면은 `visit/screens/settings/`로 옮겼고, 오늘 날짜는 `core/time/today_provider.dart`, `runShopScoped`는 `auth/state/shop_scoped.dart`다.
+- **폼 규칙은 Notifier 가 아니라 순수 객체 `VisitFormDraft`.** 설계 A11 은 `visit_form_controller.dart`(Notifier)를 말했다. 폼은 화면 인스턴스마다 하나이고 프로바이더로 공유할 이유가 없어, 위젯의 `State`가 쥐고 `setState`만 부르는 순수 객체로 뺐다. 반려동물 선택·"지난번처럼" 순서 번호·메뉴 → 소요·소요 단계·값 생성이 위젯 없이 단위 테스트된다. 시간표 범위는 `day_layout.timelineHours`.
+- **세션 파생 프로바이더는 다섯.** 설계 A2 의 셋에 `shopCountProvider`(매장 선택 화면·설정)와 `currentUserIdProvider`(멤버 화면의 "나")를 더했다. 화면은 이 다섯만 `select`로 watch 한다(`app/CLAUDE.md`).
+
+### 남는 것 — 알고 미룬다
+
+- `AppErrorRetry`가 걷어낸 21곳 가운데 문구가 화면마다 조금씩 다른 것은 그대로 두었다(문구 통일은 디자인 판단).
+- `visit_form.dart`는 여전히 500줄이 넘는다. 규칙은 빠졌지만 프로바이더 합성과 시간 칸 재조회는 위젯에 남아 있다. ④-2 가 기록 입력을 붙일 때 다시 본다.
+- `GlassSurface`의 기본 반지름 16 은 `AppRadius` 토큰이 아니라 리터럴이다. 두 사용처(`AppGlassCard`·`AppGlassBar`)가 모두 토큰을 넘기므로 기본값을 쓰는 곳이 없다 — 그대로 두었다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 30s` → 542 passed(코드가 바뀌지 않았으니 작업 10 과 같다)

확인: `_docs/decisions/007-record-media.md`의 새 절 제목이 `## ④-0 SOLID 정리(앱)에서 정한 것`이고, `app/CLAUDE.md`의 규칙이 작업 3 이 더한 두 줄 아래에 두 줄 더 있다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 문서 작업이라 변이가 없다.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "docs: ④-0 앱 SOLID 정리의 규칙과 결정을 적는다 — 앱 CLAUDE(플러그인 프로바이더·상태 enum), 하네스(앱 구조 테스트), 결정 기록 007(앱 절)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---
