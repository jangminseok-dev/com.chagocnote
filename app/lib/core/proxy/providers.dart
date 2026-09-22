import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../storage/prefs_store.dart';
import '../storage/token_store.dart';
import 'api_client.dart';

final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromEnvironment());

final tokenStoreProvider = Provider<TokenStore>((ref) => SecureTokenStore());

final prefsStoreProvider = Provider<PrefsStore>((ref) => SecurePrefsStore());

/// `core`가 `features`를 import하지 않고도 "세션이 끝났다"를 알릴 수 있게
/// 하는 신호. `ApiClient`가 리프레시 실패를 감지하면 [fire]를 부르고,
/// `features/auth`의 세션 컨트롤러가 [listener]를 등록해 받는다.
class SessionEndedSignal {
  void Function()? listener;

  void fire() => listener?.call();
}

final sessionEndedSignalProvider = Provider<SessionEndedSignal>(
  (ref) => SessionEndedSignal(),
);

/// `ApiClient`가 원 요청에 쓰는 `Dio`. `flutter test`는 `TestWidgetsFlutterBinding`이
/// 뜬 상태에서 진짜 `HttpClient`가 만드는 요청을 전부 400으로 가로채므로(dart:io
/// 문서 참고), 실제 소켓을 못 쓴다. 그래서 어댑터를 갈아 끼울 자리를 이 프로바이더로
/// 빼 둔다 — production 은 그대로 두고, 테스트만 `overrideWithValue`로 가짜
/// 어댑터를 문 `Dio`를 꽂는다(fix round 1: session_ended_wiring_test 판정 참고).
final dioProvider = Provider<Dio>((ref) {
  final config = ref.watch(appConfigProvider);
  return Dio(BaseOptions(baseUrl: config.apiBaseUrl));
});

/// 리프레시 요청 전용 "민짜" `Dio`. 용도는 [ApiClient]의 문서를 참고.
final refreshDioProvider = Provider<Dio>((ref) {
  final config = ref.watch(appConfigProvider);
  return Dio(BaseOptions(baseUrl: config.apiBaseUrl));
});

final apiClientProvider = Provider<ApiClient>((ref) {
  final tokenStore = ref.watch(tokenStoreProvider);
  final signal = ref.watch(sessionEndedSignalProvider);
  return ApiClient(
    tokenStore: tokenStore,
    dio: ref.watch(dioProvider),
    refreshDio: ref.watch(refreshDioProvider),
    onSessionEnded: signal.fire,
  );
});
