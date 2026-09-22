// WithdrawController를 위젯 트리 없이 ProviderContainer로 직접 검증한다.
// 구글 연결 해제(베스트 에포트)처럼 화면 없이도 확인할 수 있는 동작에
// 집중한다 — 화면 흐름(시트, 오류 문구)은 withdraw_screen_test.dart에서 본다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/state/withdraw_controller.dart';
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

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp({
  required FakeSessionGateway gateway,
  required FakeHandler handle,
  List<FakeSocialSignIn> signIns = const [],
}) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final tokenStore = MemoryTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      socialSignInsProvider.overrideWithValue(signIns),
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
  return (container: container, adapter: adapter);
}

void main() {
  test('구글이 연결되어 있었으면 탈퇴 후 disconnect() 를 한 번 부른다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'google']);
    final google = FakeSocialSignIn('google');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(statusCode: 204),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(withdrawControllerProvider.notifier).withdraw();

    expect(google.disconnectCallCount, 1);
    expect(gateway.clearLocalCalled, isTrue);
  });

  test('구글이 없었으면 disconnect() 를 부르지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final google = FakeSocialSignIn('google');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(statusCode: 204),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(withdrawControllerProvider.notifier).withdraw();

    expect(google.disconnectCallCount, 0);
  });

  test('disconnect() 가 던져도 탈퇴 자체는 실패하지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'google']);
    final google = FakeSocialSignIn('google')..disconnectError = Exception('실패');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(statusCode: 204),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(withdrawControllerProvider.notifier).withdraw();

    expect(google.disconnectCallCount, 1);
    expect(gateway.clearLocalCalled, isTrue);
  });
}
