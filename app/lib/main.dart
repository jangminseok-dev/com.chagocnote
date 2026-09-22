import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'design/bridge/glass_setup.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeGlass();
  runApp(
    ProviderScope(
      // Riverpod 3의 기본 재시도를 끈다. 세션 복원 실패는 스플래시 화면이
      // "다시 시도" 버튼으로 사용자가 직접 재시도하게 해야지, 프레임워크가
      // 지수 백오프로 조용히 반복 시도하면 안 된다.
      retry: (retryCount, error) => null,
      child: wrapWithGlass(const App()),
    ),
  );
}
