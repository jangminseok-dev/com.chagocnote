// `core/proxy`(ApiClient)가 `features/auth`를 몰라도 리프레시 실패를 세션
// 컨트롤러에 전달할 수 있는지를, 실제 프로바이더 그래프로 확인한다.
//
// (fix round 1) 처음 버전은 `apiClientProvider` 자체를 오버라이드해 그 안에서
// `onSessionEnded: ref.read(sessionEndedSignalProvider).fire`를 테스트가 직접
// 다시 심었다 — 그래서 `providers.dart`의 실제 배선(`onSessionEnded:
// signal.fire`)을 지워도 이 테스트는 통과했다(판별력이 없었다). 실제
// 루프백 소켓으로 바꿔 보았지만, `flutter test`는 `TestWidgetsFlutterBinding`이
// 뜬 상태에서 진짜 `HttpClient`의 모든 요청을 400으로 가로챈다(dart:io의
// 알려진 제약 — 실행 시 "creates an HttpClient … all HTTP requests will
// return status code 400" 경고로 확인했다). 그래서 `apiClientProvider`는
// 그대로 두고, `ApiClient`가 쓰는 `Dio`를 만드는 자리(`dioProvider`/
// `refreshDioProvider`)만 오버라이드해 가짜 어댑터를 문다. `apiClientProvider`
// 자체(그 안의 `onSessionEnded: signal.fire` 포함)는 production 코드
// 그대로 실행된다.
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

const _meJson = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': <Map<String, dynamic>>[],
};

void main() {
  test(
    '보호된 호출이 401 을 받고 리프레시도 401 이면 '
    '세션 컨트롤러가 SignedOut(sessionExpired: true) 로 끝난다',
    () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
          return const FakeResponse(statusCode: 200, data: _meJson);
        }
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 만료'},
          );
        }
        if (options.path == '/protected-probe') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '액세스 토큰 만료'},
          );
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      final container = _containerWith(tokenStore, adapter);
      addTearDown(container.dispose);

      final initial = await container.read(sessionControllerProvider.future);
      expect(initial, isA<SignedIn>());

      final client = container.read(apiClientProvider);
      await expectLater(
        client.get('/protected-probe'),
        throwsA(isA<ApiException>()),
      );

      final state = container.read(sessionControllerProvider).value as SignedOut;
      expect(state.sessionExpired, isTrue);
    },
  );

  test(
    '앱 시작 때 /v1/me 가 401, 리프레시도 401 이면 '
    'SignedOut(sessionExpired: true) 로 끝난다(AsyncError 가 아니다) — fix round 1',
    () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
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
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      final container = _containerWith(tokenStore, adapter);
      addTearDown(container.dispose);

      final state = await container.read(sessionControllerProvider.future);

      expect(state, isA<SignedOut>());
      expect((state as SignedOut).sessionExpired, isTrue);
      expect(await tokenStore.readRefresh(), isNull);
    },
  );

  test(
    '앱 시작 때 리프레시가 403 ACCOUNT_SUSPENDED 로 끝나도 같은 결과다'
    '(AsyncError 가 아니다) — fix round 1',
    () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '액세스 토큰 만료'},
          );
        }
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'ACCOUNT_SUSPENDED', 'message': '정지된 계정'},
          );
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      final container = _containerWith(tokenStore, adapter);
      addTearDown(container.dispose);

      final state = await container.read(sessionControllerProvider.future);

      expect(state, isA<SignedOut>());
      expect((state as SignedOut).sessionExpired, isTrue);
    },
  );

  test(
    '앱 시작 때 연결 오류가 나면 토큰은 그대로 남고 예외가 올라온다 — fix round 1',
    () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        throw DioException.connectionTimeout(
          timeout: const Duration(seconds: 5),
          requestOptions: options,
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final container = _containerWith(tokenStore, adapter);
      addTearDown(container.dispose);

      await expectLater(
        container.read(sessionControllerProvider.future),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', 'NETWORK')),
      );
      expect(await tokenStore.readAccess(), 'access-1');
      expect(await tokenStore.readRefresh(), 'refresh-1');
    },
  );
}

ProviderContainer _containerWith(
  TokenStore tokenStore,
  FakeHttpClientAdapter adapter,
) {
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      tokenStoreProvider.overrideWithValue(tokenStore),
      prefsStoreProvider.overrideWithValue(MemoryPrefsStore()),
      dioProvider.overrideWithValue(dio),
      refreshDioProvider.overrideWithValue(refreshDio),
    ],
  );
}
