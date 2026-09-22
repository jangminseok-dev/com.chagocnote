// AccountController을 위젯 트리 없이 ProviderContainer로 직접 검증한다.
// SessionGateway는 FakeSessionGateway, HTTP는 FakeHttpClientAdapter를 문
// 실제 AccountApi/AccountController로 확인한다.
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/state/account_controller.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';
import '../../../support/fake_social_sign_in.dart';

Me _me(List<String> identities) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

/// save()가 불릴 때마다 [order]에 'save'를 남기는 토큰 저장소. 실제 값은
/// 내부의 [MemoryTokenStore]에 그대로 위임한다.
class _OrderTrackingTokenStore implements TokenStore {
  _OrderTrackingTokenStore(this.order);

  final List<String> order;
  final _inner = MemoryTokenStore();

  @override
  Future<void> save({required String access, required String refresh}) async {
    order.add('save');
    await _inner.save(access: access, refresh: refresh);
  }

  @override
  Future<String?> readAccess() => _inner.readAccess();

  @override
  Future<String?> readRefresh() => _inner.readRefresh();

  @override
  Future<void> clear() => _inner.clear();
}

/// refreshMe()가 불릴 때마다 [order]에 'reloadMe'를 남기는 세션 게이트웨이.
class _OrderTrackingGateway extends FakeSessionGateway {
  _OrderTrackingGateway(this.order);

  final List<String> order;

  @override
  Future<Me> refreshMe() async {
    order.add('reloadMe');
    return super.refreshMe();
  }
}

({ProviderContainer container, FakeHttpClientAdapter adapter, TokenStore tokenStore})
    _setUp({
  required FakeSessionGateway gateway,
  required FakeHandler handle,
  List<FakeSocialSignIn> signIns = const [],
  TokenStore? tokenStore,
}) {
  final adapter = FakeHttpClientAdapter(handle);
  // 리프레시 요청은 별도의 Dio 인스턴스로 보내야 한다 — 같은 인스턴스를
  // 재사용하면 리프레시 요청 자체가 401을 받았을 때 다시 리프레시를
  // 시도하는 재귀에 빠진다.
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = tokenStore ?? MemoryTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      socialSignInsProvider.overrideWithValue(signIns),
      tokenStoreProvider.overrideWithValue(store),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: store,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter, tokenStore: store);
}

void main() {
  test('취소된 소셜 로그인은 요청을 보내지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final kakao = FakeSocialSignIn('kakao')..credentialToReturn = null;
    final setup = _setUp(
      gateway: gateway,
      signIns: [kakao],
      handle: (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).link(kakao);

    expect(kakao.signInCallCount, 1);
    expect(setup.adapter.requests, isEmpty);
    expect(gateway.refreshMeCallCount, 0);
  });

  test('로그인 성공하면 연결 요청 후 reloadMe 를 부른다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple'])
      ..meOnRefresh = _me(['apple', 'kakao']);
    final kakao = FakeSocialSignIn('kakao')
      ..credentialToReturn = const SocialCredential(provider: 'kakao', token: 'tok');
    final setup = _setUp(
      gateway: gateway,
      signIns: [kakao],
      handle: (options, body) {
        expect(options.method, 'POST');
        expect(options.path, '/v1/auth/identities');
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple', 'kakao'],
          },
        );
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).link(kakao);

    expect(setup.adapter.requests, hasLength(1));
    expect(gateway.refreshMeCallCount, 1);
  });

  test('개발용 연결은 이름을 dev 자격 증명으로 보낸다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple'])
      ..meOnRefresh = _me(['apple', 'dev']);
    Map<String, dynamic>? sentBody;
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        sentBody = jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple', 'dev'],
          },
        );
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).linkDev('민석');

    expect(sentBody, {'provider': 'dev', 'token': '민석'});
    expect(gateway.refreshMeCallCount, 1);
  });

  test('해제하면 토큰을 먼저 저장한 뒤에 reloadMe 를 부른다(S5 순서 고정)', () async {
    final order = <String>[];
    final gateway = _OrderTrackingGateway(order)
      ..meOnRestore = _me(['apple', 'kakao'])
      ..meOnRefresh = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      tokenStore: _OrderTrackingTokenStore(order),
      handle: (options, body) {
        expect(options.method, 'DELETE');
        expect(options.path, '/v1/auth/identities/kakao');
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple'],
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
            'token_type': 'Bearer',
            'expires_in': 3600,
          },
        );
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('kakao');

    expect(order, ['save', 'reloadMe']);
    expect(await setup.tokenStore.readAccess(), 'new-access');
  });

  test('구글 해제 후 disconnect() 를 한 번 부른다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'google'])
      ..meOnRefresh = _me(['apple']);
    final google = FakeSocialSignIn('google');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(
        statusCode: 200,
        data: {
          'identities': ['apple'],
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'token_type': 'Bearer',
          'expires_in': 3600,
        },
      ),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('google');

    expect(google.disconnectCallCount, 1);
  });

  test('disconnect() 가 던져도 해제 자체는 실패하지 않는다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'google'])
      ..meOnRefresh = _me(['apple']);
    final google = FakeSocialSignIn('google')
      ..disconnectError = Exception('연결 끊기 실패');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(
        statusCode: 200,
        data: {
          'identities': ['apple'],
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'token_type': 'Bearer',
          'expires_in': 3600,
        },
      ),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('google');

    expect(google.disconnectCallCount, 1);
  });

  group('fix round 1 — disconnect 위치', () {
    test('reloadMe 가 던져도 disconnect 는 한 번 불리고 unlink 는 성공으로 끝난다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(['apple', 'google'])
        ..refreshMeError = Exception('네트워크 오류');
      final google = FakeSocialSignIn('google');
      final setup = _setUp(
        gateway: gateway,
        signIns: [google],
        handle: (options, body) => const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple'],
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
            'token_type': 'Bearer',
            'expires_in': 3600,
          },
        ),
      );
      addTearDown(setup.container.dispose);
      await setup.container.read(sessionControllerProvider.future);

      await expectLater(
        setup.container.read(accountControllerProvider.notifier).unlink('google'),
        completes,
      );

      expect(google.disconnectCallCount, 1);
    });

    test('해제가 실패하면 disconnect 가 불리지 않는다', () async {
      final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'google']);
      final google = FakeSocialSignIn('google');
      final setup = _setUp(
        gateway: gateway,
        signIns: [google],
        handle: (options, body) => const FakeResponse(
          statusCode: 409,
          data: {'code': 'LAST_IDENTITY', 'message': '마지막 수단'},
        ),
      );
      addTearDown(setup.container.dispose);
      await setup.container.read(sessionControllerProvider.future);

      await expectLater(
        setup.container.read(accountControllerProvider.notifier).unlink('google'),
        throwsA(isA<ApiException>()),
      );

      expect(google.disconnectCallCount, 0);
      expect(gateway.refreshMeCallCount, 0);
    });

    test('구글이 아닌 수단 해제는 disconnect 를 부르지 않는다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(['apple', 'google', 'kakao'])
        ..meOnRefresh = _me(['apple', 'google']);
      final google = FakeSocialSignIn('google');
      final setup = _setUp(
        gateway: gateway,
        signIns: [google],
        handle: (options, body) {
          expect(options.path, '/v1/auth/identities/kakao');
          return const FakeResponse(
            statusCode: 200,
            data: {
              'identities': ['apple', 'google'],
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'token_type': 'Bearer',
              'expires_in': 3600,
            },
          );
        },
      );
      addTearDown(setup.container.dispose);
      await setup.container.read(sessionControllerProvider.future);

      await setup.container.read(accountControllerProvider.notifier).unlink('kakao');

      expect(google.disconnectCallCount, 0);
    });
  });

  test('로그아웃하면 세션 게이트웨이의 signOut 을 부른다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).logout();

    expect(gateway.signOutCalled, isTrue);
  });
}
