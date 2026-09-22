import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/state/session.dart';
import '../../features/auth/state/session_controller.dart';
import 'placeholder_screens.dart';

/// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
/// 바뀔 때마다 이걸로 "redirect를 다시 평가해라"라고 알린다.
class _SessionRefreshListenable extends ChangeNotifier {
  void ping() => notifyListeners();
}

/// 매장이 선택되어 있어야만 열리는 경로.
const _shopScopedSettings = {'/settings', '/settings/members', '/settings/shop'};

/// 매장이 없어도(0-shop 사용자도) 열려 있어야 하는 계정 관련 경로 — 로그아웃,
/// 로그인 수단 해제, 탈퇴는 매장 유무와 무관하게 가능해야 한다.
const _accountExemptRoutes = {'/settings/account', '/settings/account/withdraw'};

/// 로그인/스플래시처럼 "머물 이유가 없는" 진입 화면. 로그인된 사용자가
/// 여기 있으면 홈으로 밀어낸다. `/invite`, `/shops/select`는 매장을 이미 가진
/// 사용자도 다시 열 수 있어야 하므로(다른 매장 합류, 매장 전환) 여기 넣지
/// 않는다.
const _entryOnlyRoutes = {'/login', '/splash'};

/// 라우터는 앱 생애주기 동안 단 한 번만 만들어져야 한다(그렇지 않으면
/// 내비게이션 스택이 매번 리셋된다). 그래서 `Provider`(autoDispose 아님)로
/// 제공하고, 세션이 바뀔 때는 redirect만 재평가되도록 `ref.listen` +
/// `refreshListenable` 조합을 쓴다. `redirect` 콜백 안에서 세션을 `ref.watch`
/// 하면 이 프로바이더 자체가 재실행되어 `GoRouter` 인스턴스가 새로 만들어지므로
/// 절대 하지 않는다.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _SessionRefreshListenable();
  ref.listen(sessionControllerProvider, (previous, next) => refresh.ping());
  ref.onDispose(refresh.dispose);

  final router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final location = state.matchedLocation;
      final session = ref.read(sessionControllerProvider);

      if (session.isLoading || session.hasError) {
        return location == '/splash' ? null : '/splash';
      }

      return switch (session.value) {
        null || SignedOut() => location == '/login' ? null : '/login',
        SignedIn(:final me, :final selectedShopId) => _redirectSignedIn(
            location: location,
            shopCount: me.shops.length,
            selectedShopId: selectedShopId,
          ),
      };
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/invite', builder: (context, state) => const InviteScreen()),
      GoRoute(
        path: '/shops/select',
        builder: (context, state) => const ShopSelectScreen(),
      ),
      GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/settings/members',
        builder: (context, state) => const SettingsMembersScreen(),
      ),
      GoRoute(
        path: '/settings/shop',
        builder: (context, state) => const SettingsShopScreen(),
      ),
      GoRoute(
        path: '/settings/account',
        builder: (context, state) => const SettingsAccountScreen(),
      ),
      GoRoute(
        path: '/settings/account/withdraw',
        builder: (context, state) => const SettingsAccountWithdrawScreen(),
      ),
    ],
  );

  ref.onDispose(router.dispose);
  return router;
});

String? _redirectSignedIn({
  required String location,
  required int shopCount,
  required int? selectedShopId,
}) {
  if (shopCount == 0) {
    if (_accountExemptRoutes.contains(location)) return null;
    return location == '/invite' ? null : '/invite';
  }

  if (shopCount >= 2 && selectedShopId == null) {
    if (_accountExemptRoutes.contains(location)) return null;
    return location == '/shops/select' ? null : '/shops/select';
  }

  if (_shopScopedSettings.contains(location) && selectedShopId == null) {
    return '/home';
  }

  if (_entryOnlyRoutes.contains(location)) {
    return '/home';
  }

  return null;
}
