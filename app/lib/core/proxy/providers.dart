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

final apiClientProvider = Provider<ApiClient>((ref) {
  final config = ref.watch(appConfigProvider);
  final tokenStore = ref.watch(tokenStoreProvider);
  final signal = ref.watch(sessionEndedSignalProvider);
  return ApiClient(
    tokenStore: tokenStore,
    baseUrl: config.apiBaseUrl,
    onSessionEnded: signal.fire,
  );
});
