// 멤버 화면을 실제 라우터로 검증한다. `sessionGatewayProvider`는
// `FakeSessionGateway`로(세션 복원·재조회를 직접 제어하기 위해), 매장 API는
// `apiClientProvider`를 가짜 어댑터로 문 진짜 `ShopApi`로 검증한다 — 두
// 계층이 서로 다른 경로(세션 vs 매장 API)를 타기 때문에 각각 가짜로
// 대체하는 쪽이 더 명확하다.
import 'package:chagocnote/core/proxy/clipboard.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/tokens/app_typography.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_clipboard.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

const _hissHaus = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'owner');
const _hissHausStaff = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'staff');
const _secondShop = ShopMembership(shopId: 4, shopName: '두 번째 매장', role: 'owner');

Me _ownerMe() => const Me(
      id: 99,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_hissHaus],
    );

Me _staffMe() => const Me(
      id: 50,
      displayName: '직원',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_hissHausStaff],
    );

Me _twoShopOwnerMe() => const Me(
      id: 99,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_hissHaus, _secondShop],
    );

const _membersJson = [
  {
    'member_id': 1,
    'user_id': 99,
    'display_name': '민석',
    'profile_image_url': null,
    'role': 'owner',
    'joined_at': '2026-01-01T00:00:00Z',
  },
  {
    'member_id': 21,
    'user_id': 50,
    'display_name': '직원',
    'profile_image_url': null,
    'role': 'staff',
    'joined_at': '2026-02-02T00:00:00Z',
  },
];

// 두 번째 매장(id 4)의 멤버 목록. Hiss Haus 와 겹치지 않는 이름을 써서 화면이
// 매장을 바꾼 뒤에도 옛 매장의 데이터를 들고 있는지 구분한다.
const _membersJson2 = [
  {
    'member_id': 5,
    'user_id': 99,
    'display_name': '민석',
    'profile_image_url': null,
    'role': 'owner',
    'joined_at': '2026-01-01T00:00:00Z',
  },
  {
    'member_id': 30,
    'user_id': 77,
    'display_name': '새직원',
    'profile_image_url': null,
    'role': 'staff',
    'joined_at': '2026-03-03T00:00:00Z',
  },
];

({
  ProviderContainer container,
  FakeHttpClientAdapter adapter,
  FakeClipboard clipboard,
})
_setUp(
  FakeSessionGateway gateway,
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final clipboard = FakeClipboard();
  // dio(원 요청)와 refreshDio(리프레시 전용)는 같은 인스턴스를 쓰지 않는다 —
  // 같은 인터셉터를 타는 하나의 Dio를 둘 다에 쓰면 리프레시 요청 자체가
  // 401을 받았을 때 다시 리프레시를 시도하는 재귀에 빠질 위험이 있다
  // (ApiClient 문서 참고). 같은 가짜 어댑터를 문 별도 Dio 두 개로 나눈다.
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      clipboardProvider.overrideWithValue(clipboard),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: _NoopTokenStore(),
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter, clipboard: clipboard);
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('직원은 관리 UI가 안 보인다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _staffMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
    expect(find.text(AppStrings.createInvite), findsNothing);

    // 헤더 버튼뿐 아니라 행 자체도 관리 동작을 열지 않는다 — `canManage`가
    // `!isSelf`만으로 느슨해져도 이 단언이 잡아내도록, 자기 자신이 아닌
    // 다른 멤버('민석')의 행을 누른다.
    await tester.tap(find.text('민석'));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.promoteToOwner), findsNothing);
    expect(find.text(AppStrings.demoteToStaff), findsNothing);
    expect(find.text(AppStrings.removeMember), findsNothing);
  });

  testWidgets('사장은 초대 코드 만들기 버튼을 본다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.createInvite), findsOneWidget);
  });

  testWidgets('초대 코드를 만들면 코드를 보여주고 POST 요청을 보낸다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      if (options.path == '/v1/shops/3/invites') {
        return const FakeResponse(
          statusCode: 201,
          data: {
            'code': 'ABC123',
            'role': 'staff',
            'expires_at': '2026-09-23T00:00:00Z',
          },
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.createInvite));
    await tester.pumpAndSettle();

    expect(find.text('ABC123'), findsOneWidget);
    // 사람이 옮겨 적는 코드라 글자가 겹치면 안 된다 — 날짜용 bigNumeral(음수
    // 자간)이 아니라 초대 코드용 스타일을 쓴다(F4).
    final codeStyle = tester.widget<Text>(find.text('ABC123')).style!;
    expect(codeStyle, AppTypography.inviteCode);
    expect(codeStyle.letterSpacing, greaterThanOrEqualTo(0));
    final invitePosts = setup.adapter.requests
        .where((r) => r.path == '/v1/shops/3/invites' && r.method == 'POST');
    expect(invitePosts, hasLength(1));

    // [복사]는 화면이 플러그인을 직접 부르지 않고 클립보드 프로바이더에 쓴다(A4).
    await tester.tap(find.text(AppStrings.copy));
    await tester.pump();
    expect(setup.clipboard.text, 'ABC123');
  });

  testWidgets('역할 변경은 PATCH 를 보내고 목록을 새로고침한다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    var patched = false;
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return FakeResponse(
          statusCode: 200,
          data: patched
              ? [
                  _membersJson[0],
                  {..._membersJson[1], 'role': 'owner'},
                ]
              : _membersJson,
        );
      }
      if (options.path == '/v1/shops/3/members/21' && options.method == 'PATCH') {
        patched = true;
        return const FakeResponse(
          statusCode: 200,
          data: {'member_id': 21, 'user_id': 50, 'role': 'owner'},
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text('직원').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.promoteToOwner));
    await tester.pumpAndSettle();

    final patchRequest = setup.adapter.requests.firstWhere(
      (r) => r.path == '/v1/shops/3/members/21' && r.method == 'PATCH',
    );
    final sentBody =
        setup.adapter.lastBodyByPath['/v1/shops/3/members/21'];
    expect(patchRequest.method, 'PATCH');
    expect(String.fromCharCodes(sentBody!), '{"role":"owner"}');

    // 새로고침을 단언한다: 목록 GET 이 (최초 진입 + 역할 변경 뒤) 두 번
    // 나갔고, 화면에도 새로고침된 데이터(사장 칩 둘)가 반영됐다.
    final memberListGets = setup.adapter.requests.where(
      (r) => r.path == '/v1/shops/3/members' && r.method == 'GET',
    );
    expect(memberListGets, hasLength(2));
    expect(find.text(AppStrings.roleOwner), findsNWidgets(2));
  });

  testWidgets('내보내기는 확인 후 DELETE 를 보내고 목록을 새로고침한다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    var removed = false;
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return FakeResponse(
          statusCode: 200,
          data: removed ? [_membersJson[0]] : _membersJson,
        );
      }
      if (options.path == '/v1/shops/3/members/21' &&
          options.method == 'DELETE') {
        removed = true;
        return const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text('직원').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.removeMember));
    await tester.pumpAndSettle();
    // 확인 시트에도 같은 라벨의 버튼이 있다 — 마지막(확인 시트)을 누른다.
    await tester.tap(find.text(AppStrings.removeMember).last);
    await tester.pumpAndSettle();

    expect(
      setup.adapter.requests.where(
        (r) => r.path == '/v1/shops/3/members/21' && r.method == 'DELETE',
      ),
      hasLength(1),
    );
    expect(find.text('직원'), findsNothing);
  });

  testWidgets('LAST_OWNER 면 문구를 보여준다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      if (options.path == '/v1/shops/3/members/21' && options.method == 'PATCH') {
        return const FakeResponse(
          statusCode: 409,
          data: {'code': 'LAST_OWNER', 'message': '마지막 사장'},
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text('직원').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.promoteToOwner));
    await tester.pumpAndSettle();

    expect(find.text('매장에는 사장이 한 명 이상 있어야 합니다.'), findsOneWidget);
  });

  testWidgets(
    'NOT_A_MEMBER 면 reloadMe 를 부른다 — 매장이 남아있으면 그대로 머무른다',
    (tester) async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _ownerMe()
        ..meOnRefresh = _ownerMe(); // 강등됐지만 여전히 멤버
      final setup = _setUp(gateway, (options, body) {
        if (options.path == '/v1/shops/3/members') {
          return const FakeResponse(statusCode: 200, data: _membersJson);
        }
        if (options.path == '/v1/shops/3/members/21' &&
            options.method == 'PATCH') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'NOT_A_MEMBER', 'message': '멤버 아님'},
          );
        }
        fail('예상하지 못한 경로: ${options.method} ${options.path}');
      });
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();

      await tester.tap(find.text('직원').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.promoteToOwner));
      await tester.pumpAndSettle();

      expect(gateway.refreshMeCallCount, 1);
      expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
    },
  );

  testWidgets(
    'NOT_A_MEMBER 면 reloadMe 를 부른다 — 매장이 사라졌으면 라우터가 내보낸다',
    (tester) async {
      final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
      final setup = _setUp(gateway, (options, body) {
        if (options.path == '/v1/shops/3/members') {
          return const FakeResponse(statusCode: 200, data: _membersJson);
        }
        if (options.path == '/v1/shops/3/members/21' &&
            options.method == 'PATCH') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'NOT_A_MEMBER', 'message': '멤버 아님'},
          );
        }
        fail('예상하지 못한 경로: ${options.method} ${options.path}');
      });
      // 제거됨 — 더는 이 매장의 멤버가 아니다.
      gateway.meOnRefresh = const Me(
        id: 99,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [],
      );
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();

      await tester.tap(find.text('직원').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.promoteToOwner));
      await tester.pumpAndSettle();

      expect(gateway.refreshMeCallCount, 1);
      expect(find.byKey(ScreenKeys.invite), findsOneWidget);
    },
  );

  testWidgets(
    '목록 조회 자체가 NOT_A_MEMBER 를 받아도 reloadMe 를 부른다 — 매장이 사라졌으면 라우터가 내보낸다',
    (tester) async {
      // S8: build()도 runShopScoped를 거쳐야 한다. 내보내진 직원이 멤버
      // 화면에 들어오면 첫 목록 GET부터 403 NOT_A_MEMBER를 받을 수 있다.
      final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
      final setup = _setUp(gateway, (options, body) {
        if (options.path == '/v1/shops/3/members') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'NOT_A_MEMBER', 'message': '멤버 아님'},
          );
        }
        fail('예상하지 못한 경로: ${options.method} ${options.path}');
      });
      // 제거됨 — 더는 이 매장의 멤버가 아니다.
      gateway.meOnRefresh = const Me(
        id: 99,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [],
      );
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();

      expect(gateway.refreshMeCallCount, 1);
      expect(find.byKey(ScreenKeys.invite), findsOneWidget);
    },
  );

  testWidgets('초대 만료 시각은 기기 로컬 시간으로 보여준다', (tester) async {
    // 서버는 UTC로 만료 시각을 준다. 테스트 환경의 시간대에 의존하지
    // 않도록, 기대 문자열도 같은 `toLocal()`로 계산한다.
    const expiresAtIso = '2026-09-28T20:00:00Z';
    final expiresAt = DateTime.parse(expiresAtIso);
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      if (options.path == '/v1/shops/3/invites') {
        return const FakeResponse(
          statusCode: 201,
          data: {
            'code': 'XYZ789',
            'role': 'staff',
            'expires_at': expiresAtIso,
          },
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.createInvite));
    await tester.pumpAndSettle();

    final local = expiresAt.toLocal();
    final expectedDate = '${local.year}.'
        '${local.month.toString().padLeft(2, '0')}.'
        '${local.day.toString().padLeft(2, '0')}';
    final expectedTime = '${local.hour.toString().padLeft(2, '0')}:'
        '${local.minute.toString().padLeft(2, '0')}';

    expect(
      find.text(
        '${AppStrings.inviteExpiresAtLabel} $expectedDate $expectedTime',
      ),
      findsOneWidget,
    );
  });

  testWidgets('매장을 바꾸면 새 매장의 멤버 목록을 다시 불러온다(최종 검토 Minor 1)', (tester) async {
    // 역할(owner)은 두 매장에서 같게 둬서, isOwnerProvider·currentUserIdProvider
    // 만으로는 다시 그려지지 않는다 — build 가 selectedShopIdProvider 를
    // watch 해야만 매장이 바뀐 걸 알아챈다.
    final gateway = FakeSessionGateway()
      ..meOnRestore = _twoShopOwnerMe()
      ..lastShopId = 3;
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      if (options.path == '/v1/shops/4/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson2);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    // '직원'은 role 칩 문구('직원'=staff)와 겹쳐서 찾을 수 있으니, 매장4에만
    // 있는 표시 이름('새직원')으로 구분한다.
    expect(find.text('새직원'), findsNothing);

    await setup.container.read(sessionControllerProvider.notifier).selectShop(4);
    await tester.pumpAndSettle();

    final shop4Gets = setup.adapter.requests.where(
      (r) => r.path == '/v1/shops/4/members' && r.method == 'GET',
    );
    expect(shop4Gets, hasLength(1));
    expect(find.text('새직원'), findsOneWidget);
  });

  group('오류 고착(최종 검토 C)', () {
    testWidgets('첫 조회가 NETWORK 오류면 뒤로 가기와 다시 시도가 보이고, 다시 시도하면 목록이 나온다', (
      tester,
    ) async {
      final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
      var calls = 0;
      final setup = _setUp(gateway, (options, body) {
        if (options.path == '/v1/shops/3/members') {
          calls++;
          if (calls == 1) {
            throw DioException.connectionError(
              requestOptions: options,
              reason: '연결 실패',
            );
          }
          return const FakeResponse(statusCode: 200, data: _membersJson);
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();

      expect(find.byType(AppBackButton), findsOneWidget);
      final retry = find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.retry,
      );
      expect(retry, findsOneWidget);
      expect(find.text('직원'), findsNothing);

      await tester.tap(retry);
      await tester.pumpAndSettle();

      expect(calls, 2);
      expect(find.text('직원'), findsWidgets);
      expect(retry, findsNothing);
    });

    testWidgets('오류가 난 뒤 화면을 떠났다가 다시 들어오면 새로 조회한다(autoDispose)', (tester) async {
      final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
      var calls = 0;
      final setup = _setUp(gateway, (options, body) {
        if (options.path == '/v1/shops/3/members') {
          calls++;
          if (calls == 1) {
            throw DioException.connectionError(
              requestOptions: options,
              reason: '연결 실패',
            );
          }
          return const FakeResponse(statusCode: 200, data: _membersJson);
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();
      expect(find.text('직원'), findsNothing);

      await tester.tap(find.byType(AppBackButton));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.settingsMembers), findsNothing);

      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();

      expect(calls, 2);
      expect(find.text('직원'), findsWidgets);
    });
  });
}

class _NoopTokenStore implements TokenStore {
  @override
  Future<void> clear() async {}

  @override
  Future<String?> readAccess() async => null;

  @override
  Future<String?> readRefresh() async => null;

  @override
  Future<void> save({required String access, required String refresh}) async {}
}
