import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/proxy/speech_recognizer.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;

import 'fake_http_client_adapter.dart';
import 'fake_session_gateway.dart';
import 'fake_share_sheet.dart';
import 'upload_fakes.dart';

/// 고객 기능 테스트의 매장(3번, 첫 입점 매장 이름).
const customerTestShopId = 3;

Me customerTestMe({String role = 'owner'}) => Me(
  id: 1,
  displayName: '민석',
  profileImageUrl: null,
  identities: const ['apple'],
  shops: [
    ShopMembership(
      shopId: customerTestShopId,
      shopName: 'Hiss Haus',
      role: role,
    ),
  ],
);

/// 고객 기능 테스트의 준비물 — 가짜 세션(3번 매장의 [role]), 가짜 HTTP 어댑터를
/// 문 진짜 `ApiClient`, 메모리 설정 저장소.
class CustomerTestSetup {
  CustomerTestSetup(
    FakeHandler handle, {
    String role = 'owner',
    List<Override> overrides = const [],
  }) : adapter = FakeHttpClientAdapter(handle),
       gateway = FakeSessionGateway()
         ..meOnRestore = customerTestMe(role: role)
         ..meOnRefresh = customerTestMe(role: role),
       prefs = MemoryPrefsStore() {
    // 원 요청과 갱신은 같은 가짜 어댑터를 문 별도 Dio 두 개로 나눈다(ApiClient 문서).
    final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
    final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
    container = ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [
        sessionGatewayProvider.overrideWithValue(gateway),
        prefsStoreProvider.overrideWithValue(prefs),
        // 테스트에는 연결 상태 플러그인이 없다 — 인터넷 복귀 신호는 [network]로 보낸다.
        networkWatcherProvider.overrideWithValue(network),
        // 테스트에는 음성 인식 채널이 없다 — 기록 화면의 받아쓰기는 [speech]로 흘린다.
        speechRecognizerProvider.overrideWithValue(speech),
        // 테스트에는 공유 시트 채널이 없다 — 넘긴 글과 버튼 사각형은 [shareSheet]에 적힌다.
        shareSheetProvider.overrideWithValue(shareSheet),
        apiClientProvider.overrideWith(
          (ref) => ApiClient(
            tokenStore: MemoryTokenStore(),
            dio: dio,
            refreshDio: refreshDio,
            onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
          ),
        ),
        ...overrides,
      ],
    );
  }

  final FakeHttpClientAdapter adapter;
  final FakeSessionGateway gateway;
  final network = FakeNetworkWatcher();
  final speech = FakeSpeechRecognizer();
  final shareSheet = FakeShareSheet();
  final MemoryPrefsStore prefs;
  late final ProviderContainer container;

  /// 어댑터를 거쳐 간 요청을 `METHOD path` 로 줄인 것.
  List<String> get calls => [
    for (final r in adapter.requests) '${r.method} ${r.path}',
  ];
}

/// 실제 라우터로 앱을 띄운다. 글래스는 불투명 대체 면으로 그린다.
Widget customerRouterApp(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) =>
              GlassBridge(factory: const OpaqueSurfaceFactory(), child: child!),
        );
      },
    ),
  );
}
