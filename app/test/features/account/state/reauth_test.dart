// ReauthCoordinator를 위젯 트리 없이 ProviderContainer로 직접 검증한다.
// 프롬프트는 함수(콜백)로 갈아 끼워서, 시트 UI 없이도 "재인증 성공/취소/
// 다른 계정" 분기를 확인한다. 화면(시트 UI) 쪽은 withdraw_screen_test.dart의
// 위젯 테스트에서 본다.
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/state/account_controller.dart';
import 'package:chagocnote/features/account/state/reauth.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

Me _me(List<String> identities, {int id = 1}) => Me(
      id: id,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

const _socialLoginOk = {
  'token_type': 'Bearer',
  'expires_in': 3600,
  'is_new_user': false,
};

({ProviderContainer container, FakeHttpClientAdapter adapter, TokenStore tokenStore})
    _setUp({
  required FakeSessionGateway gateway,
  required FakeHandler handle,
  ReauthPrompt? prompt,
}) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final tokenStore = MemoryTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      tokenStoreProvider.overrideWithValue(tokenStore),
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
  if (prompt != null) container.read(reauthPromptProvider).prompt = prompt;
  return (container: container, adapter: adapter, tokenStore: tokenStore);
}

void main() {
  test('REAUTH_REQUIRED → 프롬프트 → 재로그인 → 재시도가 새 토큰으로 성공한다', () async {
    var probeCallCount = 0;
    String? authHeaderOnRetry;
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'user_id': 1,
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/probe') {
          probeCallCount++;
          if (probeCallCount == 1) {
            return const FakeResponse(
              statusCode: 403,
              data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
            );
          }
          authHeaderOnRetry = options.headers['Authorization'] as String?;
          return const FakeResponse(statusCode: 200, data: {'ok': true});
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async =>
          const SocialCredential(provider: 'apple', token: 'tok'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    final result = await setup.container.read(reauthCoordinatorProvider).run(
          () => setup.container.read(apiClientProvider).get('/probe'),
        );

    expect(result, {'ok': true});
    expect(probeCallCount, 2);
    expect(authHeaderOnRetry, 'Bearer new-access');
  });

  test('S6 — 다른 계정으로 재로그인하면 저장된 토큰은 그대로고 그 세션은 로그아웃된다', () async {
    String? loggedOutRefreshToken;
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple'], id: 1);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'other-access',
              'refresh_token': 'other-refresh',
              'user_id': 999, // 다른 계정
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/v1/auth/logout') {
          final payload = jsonDecode(utf8.decode(body!)) as Map;
          loggedOutRefreshToken = payload['refresh_token'] as String;
          return const FakeResponse(statusCode: 204);
        }
        if (options.path == '/probe') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
          );
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async =>
          const SocialCredential(provider: 'apple', token: 'tok'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);
    await setup.tokenStore.save(access: 'own-access', refresh: 'own-refresh');
    final accessBefore = await setup.tokenStore.readAccess();
    final refreshBefore = await setup.tokenStore.readRefresh();

    await expectLater(
      setup.container.read(reauthCoordinatorProvider).run(
            () => setup.container.read(apiClientProvider).get('/probe'),
          ),
      throwsA(isA<ReauthMismatchException>()),
    );

    // 토큰 값 자체는 절대 출력하지 않는다 — 불리언 비교로만 "안 바뀜"을 본다.
    expect(await setup.tokenStore.readAccess() == accessBefore, isTrue);
    expect(await setup.tokenStore.readRefresh() == refreshBefore, isTrue);
    expect(loggedOutRefreshToken, 'other-refresh');
  });

  test('프롬프트를 닫으면(취소) 재로그인 요청 없이 원래 REAUTH_REQUIRED 문구가 그대로 올라온다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/probe') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인해 주세요'},
          );
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async => null, // 사용자가 시트를 닫음
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await expectLater(
      setup.container.read(reauthCoordinatorProvider).run(
            () => setup.container.read(apiClientProvider).get('/probe'),
          ),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', 'REAUTH_REQUIRED')
            .having((e) => e.message, 'message', '다시 로그인해 주세요'),
      ),
    );
    expect(
      setup.adapter.requests.where((r) => r.path == '/v1/auth/social'),
      isEmpty,
    );
  });

  test('재시도에서도 REAUTH_REQUIRED 면 다시 프롬프트하지 않고 그대로 던진다(루프 없음)', () async {
    var promptCallCount = 0;
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'user_id': 1,
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/probe') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
          );
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async {
        promptCallCount++;
        return const SocialCredential(provider: 'apple', token: 'tok');
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await expectLater(
      setup.container.read(reauthCoordinatorProvider).run(
            () => setup.container.read(apiClientProvider).get('/probe'),
          ),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'REAUTH_REQUIRED')),
    );
    expect(promptCallCount, 1);
  });

  test('unlink 이 재인증을 거쳐도 해제 응답의 토큰이 마지막에 저장된다(이긴다)', () async {
    var unlinkCallCount = 0;
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'kakao'])
      ..meOnRefresh = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'reauth-access',
              'refresh_token': 'reauth-refresh',
              'user_id': 1,
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/v1/auth/identities/kakao' &&
            options.method == 'DELETE') {
          unlinkCallCount++;
          if (unlinkCallCount == 1) {
            return const FakeResponse(
              statusCode: 403,
              data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
            );
          }
          return const FakeResponse(
            statusCode: 200,
            data: {
              'identities': ['apple'],
              'access_token': 'unlink-access',
              'refresh_token': 'unlink-refresh',
              'token_type': 'Bearer',
              'expires_in': 3600,
            },
          );
        }
        fail('예상하지 못한 요청: ${options.method} ${options.path}');
      },
      prompt: (linked) async =>
          const SocialCredential(provider: 'apple', token: 'tok'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('kakao');

    expect(unlinkCallCount, 2);
    expect(await setup.tokenStore.readAccess(), 'unlink-access');
    expect(await setup.tokenStore.readRefresh(), 'unlink-refresh');
  });
}
