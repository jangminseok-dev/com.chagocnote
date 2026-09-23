import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/proxy/shared_text_channel.dart';
import 'core/router/app_router.dart';
import 'design/app_theme.dart';
import 'design/bridge/glass_setup.dart';
import 'features/auth/state/session.dart';
import 'features/auth/state/session_controller.dart';

/// 공유로 받은 글 가운데 지금 열 수 있는 것 — 로그인했고 매장을 골랐을 때만.
/// 콜드 스타트에서 로그인 뒤에, 또는 앱이 떠 있을 때 바로 열린다(③-A3).
final sharedTextToOpenProvider = Provider<String?>((ref) {
  final session = ref.watch(sessionControllerProvider).value;
  final text = ref.watch(pendingSharedTextProvider);
  return session is SignedIn && session.selectedShopId != null ? text : null;
});

class App extends ConsumerWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    ref.listen<String?>(sharedTextToOpenProvider, (_, text) {
      if (text == null) return;
      // 한 번 열면 비운다 — 세션이 바뀌어도 다시 열리지 않게.
      ref.read(pendingSharedTextProvider.notifier).clear();
      router.push('/visits/draft', extra: text);
    });
    return MaterialApp.router(
      routerConfig: router,
      title: '차곡노트',
      theme: appTheme(),
    );
  }
}

/// `main()`이 `runApp`에 그대로 넘길 루트 위젯을 만든다. 별도 함수로 뽑아
/// 두면 `WidgetsFlutterBinding.ensureInitialized()`나 셰이더 로딩 없이도,
/// 이 함수가 돌려준 `ProviderScope`의 `retry`가 실제로 재시도를 끄는지
/// 테스트로 확인할 수 있다(S2) — `main()` 안에 직접 적어 두면 그 줄을
/// 지워도 어떤 테스트도 실패하지 않는다.
Widget buildRoot() {
  return ProviderScope(
    // Riverpod 3의 기본 재시도를 끈다. 세션 복원 실패는 스플래시 화면이
    // "다시 시도" 버튼으로 사용자가 직접 재시도하게 해야지, 프레임워크가
    // 지수 백오프로 조용히 반복 시도하면 안 된다.
    retry: (retryCount, error) => null,
    child: wrapWithGlass(const App()),
  );
}
