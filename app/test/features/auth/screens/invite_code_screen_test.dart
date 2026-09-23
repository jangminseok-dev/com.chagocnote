// 초대 코드 화면을 실제 라우터 + 가짜 HTTP 어댑터로 끝까지 검증한다.
// `sessionGatewayProvider`는 오버라이드하지 않는다 — 진짜 `HttpSessionGateway`가
// (가짜 어댑터를 문) `apiClientProvider` 위에서 그대로 동작하게 해서,
// 세션 복원·재시도·초대 수락이 전부 같은 HTTP 계층을 타는 실제 통합
// 경로를 검증한다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';

const _meNoShops = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': <Map<String, dynamic>>[],
};

const _meWithShop = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': [
    {'shop_id': 3, 'shop_name': 'Hiss Haus', 'role': 'staff'},
  ],
};

ProviderContainer _containerWith(FakeHttpClientAdapter adapter) {
  final tokenStore = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      tokenStoreProvider.overrideWithValue(tokenStore),
      prefsStoreProvider.overrideWithValue(MemoryPrefsStore()),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: tokenStore,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
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
  testWidgets(
    '성공하면 수락 → 본인 정보 재조회 → 매장 선택 순으로 부르고 홈으로 이동한다',
    (tester) async {
      var meCallCount = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
          meCallCount++;
          return FakeResponse(
            statusCode: 200,
            data: meCallCount == 1 ? _meNoShops : _meWithShop,
          );
        }
        if (options.path == '/v1/invites/accept') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'shop_id': 3,
              'shop_name': 'Hiss Haus',
              'role': 'staff',
              'member_id': 21,
            },
          );
        }
        // 홈(캘린더 탭)이 부르는 월 요약·하루 목록은 이 테스트의 관심이 아니다.
        if (options.path.startsWith('/v1/shops/')) {
          return const FakeResponse(statusCode: 500, data: 'x');
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      final container = _containerWith(adapter);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.invite), findsOneWidget);

      await tester.enterText(find.byType(TextField), 'ABC123');
      await tester.tap(find.text(AppStrings.inviteSubmit));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.home), findsOneWidget);
      final paths = adapter.requests
          .map((r) => r.path)
          .where((p) => !p.startsWith('/v1/shops/'))
          .toList();
      expect(paths, ['/v1/me', '/v1/invites/accept', '/v1/me']);
    },
  );

  testWidgets('INVITE_EXPIRED 면 문구를 보여주고 초대 화면에 머무른다', (tester) async {
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        return const FakeResponse(statusCode: 200, data: _meNoShops);
      }
      if (options.path == '/v1/invites/accept') {
        return const FakeResponse(
          statusCode: 400,
          data: {'code': 'INVITE_EXPIRED', 'message': '만료된 코드'},
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'EXPIRED1');
    await tester.tap(find.text(AppStrings.inviteSubmit));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
    expect(find.text('만료된 초대 코드입니다. 새 코드를 받아 주세요.'), findsOneWidget);
  });

  testWidgets('빈 코드로 제출하면 요청 없이 검증만 한다', (tester) async {
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        return const FakeResponse(statusCode: 200, data: _meNoShops);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.inviteSubmit));
    await tester.pump();

    expect(find.text(AppStrings.inviteCodeRequired), findsOneWidget);
    expect(
      adapter.requests.where((r) => r.path == '/v1/invites/accept'),
      isEmpty,
    );
  });

  testWidgets('수락이 401 이고 리프레시도 401 이면 로그인 화면으로 밀려난다', (tester) async {
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        return const FakeResponse(statusCode: 200, data: _meNoShops);
      }
      if (options.path == '/v1/invites/accept') {
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '액세스 토큰 만료'},
        );
      }
      if (options.path == '/v1/auth/refresh') {
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 만료'},
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'ABC123');
    await tester.tap(find.text(AppStrings.inviteSubmit));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets(
    '소속이 없는 유저는 계정 설정·로그아웃 버튼이 있고, 로그아웃하면 로그인 화면으로 간다',
    (tester) async {
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
          return const FakeResponse(statusCode: 200, data: _meNoShops);
        }
        if (options.path == '/v1/auth/logout') {
          return const FakeResponse(statusCode: 200);
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      final container = _containerWith(adapter);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.invite), findsOneWidget);

      expect(find.text(AppStrings.accountSettings), findsOneWidget);
      expect(find.text(AppStrings.logout), findsOneWidget);

      await tester.tap(find.text(AppStrings.logout));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.login), findsOneWidget);
    },
  );

  testWidgets('소속이 있는 유저는 계정 설정·로그아웃 버튼이 없다', (tester) async {
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        return const FakeResponse(statusCode: 200, data: _meWithShop);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);

    container.read(routerProvider).go('/invite');
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.invite), findsOneWidget);

    expect(find.text(AppStrings.accountSettings), findsNothing);
    expect(find.text(AppStrings.logout), findsNothing);
  });

  testWidgets('수락은 성공했는데 뒤이은 본인 정보 재조회가 실패해도 오류를 띄우지 않고 홈으로 간다(F6)', (
    tester,
  ) async {
    var meCallCount = 0;
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        meCallCount++;
        if (meCallCount == 1) {
          return const FakeResponse(statusCode: 200, data: _meWithShop);
        }
        throw DioException.connectionError(
          requestOptions: options,
          reason: '연결 실패',
        );
      }
      if (options.path == '/v1/invites/accept') {
        return const FakeResponse(
          statusCode: 200,
          data: {
            'shop_id': 5,
            'shop_name': '두 번째 매장',
            'role': 'staff',
            'member_id': 30,
          },
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/invite');
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'ABC123');
    await tester.tap(find.text(AppStrings.inviteSubmit));
    await tester.pumpAndSettle();

    // 수락은 서버에서 이미 끝났다 — 다시 누르게 두면 ALREADY_A_MEMBER 에 갇힌다.
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(
      adapter.requests.where((r) => r.path == '/v1/invites/accept'),
      hasLength(1),
    );
  });

  testWidgets(
    '소속 0개 유저: 수락 성공 뒤 재조회가 실패하면 스피너 없이 다시 누를 수 있고, 다시 누르면 '
    'ALREADY_A_MEMBER → 재조회 성공 → 홈(최종 재검토 F6)',
    (tester) async {
      var meCallCount = 0;
      var acceptCallCount = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
          meCallCount++;
          if (meCallCount == 1) {
            return const FakeResponse(statusCode: 200, data: _meNoShops);
          }
          if (meCallCount == 2) {
            throw DioException.connectionError(
              requestOptions: options,
              reason: '연결 실패',
            );
          }
          return const FakeResponse(statusCode: 200, data: _meWithShop);
        }
        if (options.path == '/v1/invites/accept') {
          acceptCallCount++;
          if (acceptCallCount == 1) {
            return const FakeResponse(
              statusCode: 200,
              data: {
                'shop_id': 3,
                'shop_name': 'Hiss Haus',
                'role': 'staff',
                'member_id': 21,
              },
            );
          }
          return const FakeResponse(
            statusCode: 409,
            data: {'code': 'ALREADY_A_MEMBER', 'message': '이미 멤버'},
          );
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      final container = _containerWith(adapter);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.invite), findsOneWidget);

      await tester.enterText(find.byType(TextField), 'ABC123');
      await tester.tap(find.text(AppStrings.inviteSubmit));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.invite), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsNothing);
      final submit = tester.widget<AppButton>(
        find.byWidgetPredicate(
          (w) => w is AppButton && w.label == AppStrings.inviteSubmit,
        ),
      );
      expect(submit.onPressed, isNotNull);
      expect(
        tester.widget<TextField>(find.byType(TextField)).decoration!.errorText,
        isNotNull,
      );

      await tester.tap(find.text(AppStrings.inviteSubmit));
      await tester.pumpAndSettle();

      expect(acceptCallCount, 2);
      expect(meCallCount, 3);
      expect(find.byKey(ScreenKeys.home), findsOneWidget);
    },
  );
}
