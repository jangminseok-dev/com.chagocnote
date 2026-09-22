// 매장 정보 화면을 실제 라우터 + 가짜 HTTP 어댑터로 검증한다.
// 멤버 화면 테스트와 같은 이유로 `sessionGatewayProvider`는
// `FakeSessionGateway`, 매장 API는 `apiClientProvider`를 가짜 어댑터로
// 문 진짜 `ShopApi`로 검증한다.
import 'dart:convert';

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

const _hissHausOwner = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'owner');
const _hissHausStaff = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'staff');

const _settingsJson = {
  'shop_id': 3,
  'name': 'Hiss Haus',
  'business_type': 'grooming',
  'phone': '02-1234-5678',
  'address': '서울시 강남구',
  'timezone': 'Asia/Seoul',
};

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
  testWidgets('직원은 읽기 전용으로 보고 저장 버튼이 없다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '직원',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausStaff],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsShop), findsOneWidget);
    expect(find.text(AppStrings.save), findsNothing);
    final nameField = tester.widget<TextField>(find.byType(TextField).first);
    expect(nameField.enabled, isFalse);
  });

  testWidgets('사장이 저장하면 정확한 JSON 본문으로 PUT 을 보낸다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      )
      ..meOnRefresh = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      if (options.path == '/v1/shops/3/settings' && options.method == 'PUT') {
        return const FakeResponse(
          statusCode: 200,
          data: {
            'shop_id': 3,
            'name': '새 이름',
            'business_type': 'grooming',
            'phone': null,
            'address': null,
            'timezone': 'Asia/Seoul',
          },
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(0), '새 이름');
    await tester.enterText(find.byType(TextField).at(1), '');
    await tester.enterText(find.byType(TextField).at(2), '');
    await tester.tap(find.text(AppStrings.save));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.saved), findsOneWidget);
    final sentBody = setup.adapter.lastBodyByPath['/v1/shops/3/settings'];
    expect(
      utf8.decode(sentBody!),
      '{"name":"새 이름","phone":null,"address":null}',
    );
    // 저장에 성공하면 이름이 바뀌었을 수 있으니 본인 정보를 다시 불러온다
    // (shop_settings_controller.dart save() 의 reloadMe 호출).
    expect(gateway.refreshMeCallCount, 1);
  });

  testWidgets('이름이 비어 있으면 요청 없이 검증만 한다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(0), '   ');
    await tester.tap(find.text(AppStrings.save));
    await tester.pump();

    expect(find.text(AppStrings.shopNameRequired), findsOneWidget);
    expect(
      setup.adapter.requests.where((r) => r.method == 'PUT'),
      isEmpty,
    );
  });

  testWidgets('VALIDATION_ERROR 면 문구를 보여준다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      if (options.path == '/v1/shops/3/settings' && options.method == 'PUT') {
        return const FakeResponse(
          statusCode: 422,
          data: {'code': 'VALIDATION_ERROR', 'message': '잘못됨'},
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.save));
    await tester.pumpAndSettle();

    expect(find.text('입력한 내용을 확인해 주세요.'), findsOneWidget);
  });

  testWidgets('NOT_A_MEMBER 면 reloadMe 를 부른다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      )
      ..meOnRefresh = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausStaff],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      if (options.path == '/v1/shops/3/settings' && options.method == 'PUT') {
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
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.save));
    await tester.pumpAndSettle();

    expect(gateway.refreshMeCallCount, 1);
    expect(find.byKey(ScreenKeys.settingsShop), findsOneWidget);
  });

  testWidgets('설정 조회(GET)가 NOT_A_MEMBER 면 build() 안에서도 reloadMe 를 부른다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      )
      ..meOnRefresh = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausStaff],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
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
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    expect(gateway.refreshMeCallCount, 1);
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
