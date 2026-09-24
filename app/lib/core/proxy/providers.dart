import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../storage/prefs_store.dart';
import '../storage/token_store.dart';
import 'api_client.dart';
import 'upload_client.dart';

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

/// 원 요청과 갱신 요청이 함께 쓰는 타임아웃. 없으면 서버가 응답하지 않을 때
/// 갱신·restore·signOut 이 수 분씩 멈추고, 갱신이 타임아웃된 뒤 사용자가
/// 다시 시도하는 경로(S2)가 실기기에서 성립하지 않는다.
const _connectTimeout = Duration(seconds: 10);
const _transferTimeout = Duration(seconds: 15);

BaseOptions _baseOptions(String baseUrl) => BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: _connectTimeout,
      receiveTimeout: _transferTimeout,
      sendTimeout: _transferTimeout,
    );

/// `ApiClient`가 원 요청에 쓰는 `Dio`. `flutter test`는 `TestWidgetsFlutterBinding`이
/// 뜬 상태에서 진짜 `HttpClient`가 만드는 요청을 전부 400으로 가로채므로(dart:io
/// 문서 참고), 실제 소켓을 못 쓴다. 그래서 어댑터를 갈아 끼울 자리를 이 프로바이더로
/// 빼 둔다 — production 은 그대로 두고, 테스트만 `overrideWithValue`로 가짜
/// 어댑터를 문 `Dio`를 꽂는다(fix round 1: session_ended_wiring_test 판정 참고).
final dioProvider = Provider<Dio>((ref) {
  final config = ref.watch(appConfigProvider);
  return Dio(_baseOptions(config.apiBaseUrl));
});

/// 리프레시 요청 전용 "민짜" `Dio`. 용도는 [ApiClient]의 문서를 참고.
final refreshDioProvider = Provider<Dio>((ref) {
  final config = ref.watch(appConfigProvider);
  return Dio(_baseOptions(config.apiBaseUrl));
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

/// [UploadClient]가 쓰는 민짜 `Dio`. 인터셉터도 인증도 없다. 테스트는 [dioProvider]처럼
/// 가짜 어댑터를 문 `Dio`를 꽂는다.
final uploadDioProvider = Provider<Dio>(
  (ref) => Dio(BaseOptions(connectTimeout: UploadClient.connectTimeout)),
);

final uploadClientProvider = Provider<UploadClient>(
  (ref) => UploadClient(dio: ref.watch(uploadDioProvider)),
);
