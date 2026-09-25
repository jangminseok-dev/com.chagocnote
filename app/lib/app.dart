import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:go_router/go_router.dart';

import 'core/plugs/pet_records_plug.dart';
import 'core/proxy/shared_text_channel.dart';
import 'core/router/app_router.dart';
import 'design/app_theme.dart';
import 'design/bridge/glass_setup.dart';
import 'features/auth/state/session.dart';
import 'features/auth/state/session_controller.dart';
import 'features/visit/screens/feed_view.dart';

/// 공유로 받은 글 가운데 지금 열 수 있는 것 — 로그인했고 매장을 골랐을 때만.
/// 콜드 스타트에서 로그인 뒤에, 또는 앱이 떠 있을 때 바로 열린다(③-A3).
final sharedTextToOpenProvider = Provider<String?>((ref) {
  final session = ref.watch(sessionControllerProvider).value;
  final text = ref.watch(pendingSharedTextProvider);
  return session is SignedIn && session.selectedShopId != null ? text : null;
});

class App extends ConsumerStatefulWidget {
  const App({super.key});

  @override
  ConsumerState<App> createState() => _AppState();
}

/// 공유로 받은 글을 열지 말지 정하는 관문이 있는 자리. 라우터가 정착한 뒤에만 연다 —
/// 로그인·매장 선택 직후에는 redirect 나 `go('/home')`이 스택을 갈아 먼저 연 화면이 사라진다.
class _AppState extends ConsumerState<App> {
  late final GoRouter _router = ref.read(routerProvider);

  @override
  void initState() {
    super.initState();
    _router.routerDelegate.addListener(_tryOpen);
  }

  @override
  void dispose() {
    _router.routerDelegate.removeListener(_tryOpen);
    super.dispose();
  }

  /// 같은 프레임의 이동(`go('/home')`·redirect)이 끝난 뒤 위치를 보고 연다.
  /// 진입 화면에 있거나 이미 초안 화면이면 글을 그대로 들고 기다린다.
  void _tryOpen() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final text = ref.read(sharedTextToOpenProvider);
      if (text == null) return;
      // 맨 위 화면의 위치 — `currentConfiguration.uri`는 push 로 쌓은 화면을 빼고 본다.
      final path = _router.state.uri.path;
      if (_waitRoutes.contains(path)) return;
      // 한 번 열면 비운다 — 세션이 바뀌어도 다시 열리지 않게.
      ref.read(pendingSharedTextProvider.notifier).clear();
      _router.push('/visits/draft', extra: text);
    });
    // 앱이 쉬고 있을 때 온 공유도 다음 프레임을 기다리지 않게 프레임을 청한다.
    WidgetsBinding.instance.ensureVisualUpdate();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<String?>(sharedTextToOpenProvider, (_, _) => _tryOpen());
    return MaterialApp.router(
      routerConfig: _router,
      title: '차곡노트',
      theme: appTheme(),
    );
  }
}

/// 관문이 글을 열지 않고 기다리는 위치 — 진입 화면들과 이미 열린 초안 화면.
const _waitRoutes = {
  '/splash',
  '/login',
  '/invite',
  '/shops/select',
  '/visits/draft',
};

/// `main()`이 `runApp`에 그대로 넘길 루트 위젯을 만든다. 별도 함수로 뽑아
/// 두면 `WidgetsFlutterBinding.ensureInitialized()`나 셰이더 로딩 없이도,
/// 이 함수가 돌려준 `ProviderScope`의 `retry`가 실제로 재시도를 끄는지
/// 테스트로 확인할 수 있다(S2) — `main()` 안에 직접 적어 두면 그 줄을
/// 지워도 어떤 테스트도 실패하지 않는다.
/// [overrides]는 시뮬레이터 흐름이 사진 선택기 같은 플러그인을 바꿔 끼울 때만 준다.
Widget buildRoot({List<Override> overrides = const []}) {
  return ProviderScope(
    // Riverpod 3의 기본 재시도를 끈다. 세션 복원 실패는 스플래시 화면이
    // "다시 시도" 버튼으로 사용자가 직접 재시도하게 해야지, 프레임워크가
    // 지수 백오프로 조용히 반복 시도하면 안 된다.
    retry: (retryCount, error) => null,
    // 기능 폴더 사이의 반대 방향 자리를 여기서 채운다(customer 의 [기록] 탭 ← visit 의 피드).
    overrides: [
      petRecordsPlugProvider.overrideWithValue(
        (petId) => PetRecordsView(petId: petId),
      ),
      ...overrides,
    ],
    child: wrapWithGlass(const App()),
  );
}
