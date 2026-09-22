// 멤버 화면을 실제 라우터로 검증한다. `sessionGatewayProvider`는
// `FakeSessionGateway`로(세션 복원·재조회를 직접 제어하기 위해), 매장 API는
// `apiClientProvider`를 가짜 어댑터로 문 진짜 `ShopApi`로 검증한다 — 두
// 계층이 서로 다른 경로(세션 vs 매장 API)를 타기 때문에 각각 가짜로
// 대체하는 쪽이 더 명확하다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

const _hissHaus = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'owner');
const _hissHausStaff = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'staff');

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

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
  FakeSessionGateway gateway,
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
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
  return (container: container, adapter: adapter);
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
    final invitePosts = setup.adapter.requests
        .where((r) => r.path == '/v1/shops/3/invites' && r.method == 'POST');
    expect(invitePosts, hasLength(1));
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
