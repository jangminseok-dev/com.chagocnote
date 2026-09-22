import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'design/app_theme.dart';
import 'design/bridge/glass_setup.dart';

class App extends ConsumerWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
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
