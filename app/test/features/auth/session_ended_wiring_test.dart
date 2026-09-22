// `core/proxy`(ApiClient)가 `features/auth`를 몰라도 리프레시 실패를 세션
// 컨트롤러에 전달할 수 있는지를, 실제 프로바이더 그래프로 확인한다.
//
// `apiClientProvider`는 production 코드에서 `Dio`/`FakeHttpClientAdapter`를
// 주입할 자리가 없다(baseUrl만 받는다). 이 테스트만을 위해 새 프로바이더를
// 추가하기보다, 테스트에서 `apiClientProvider` 자체를 가짜 어댑터를 문
// `ApiClient`로 오버라이드하는 쪽이 더 단순하다 — production 코드는 그대로
// 두고, `onSessionEnded`는 실제 코드와 똑같이
// `ref.read(sessionEndedSignalProvider).fire`를 그대로 쓴다.
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
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
      final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
      final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;

      final container = ProviderContainer.test(
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
}
