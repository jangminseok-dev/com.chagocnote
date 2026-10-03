import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/account/screens/account_screen.dart';
import '../../features/account/screens/withdraw_screen.dart';
import '../../features/auth/screens/invite_code_screen.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/shop_select_screen.dart';
import '../../features/auth/screens/splash_screen.dart';
import '../../features/auth/state/session.dart';
import '../../features/auth/state/session_controller.dart';
import '../../features/customer/screens/pet_detail_screen.dart';
import '../../features/customer/screens/pet_form_screen.dart';
import '../../features/customer/screens/customer_edit_screen.dart';
import '../../features/customer/screens/register_customer_screen.dart';
import '../../features/home/screens/home_shell.dart';
import '../../features/shop/screens/members_screen.dart';
import '../../features/shop/screens/settings_screen.dart';
import '../../features/shop/screens/shop_settings_screen.dart';
import '../../features/visit/api/visit_models.dart';
import '../../features/visit/screens/day_screen.dart';
import '../../features/visit/screens/draft_screen.dart';
import '../../features/visit/screens/photo_viewer_screen.dart';
import '../../features/visit/screens/record_screen.dart';
import '../../features/visit/screens/register_visit_screen.dart';
import '../../features/visit/screens/report_preview_screen.dart';
import '../../features/visit/screens/settings/menu_settings_screen.dart';
import '../../features/visit/screens/settings/schedule_settings_screen.dart';
import '../../features/visit/screens/visit_detail_screen.dart';
import '../../features/visit/screens/visit_edit_screen.dart';
import '../../features/visit/state/visit_prefill.dart';

/// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
/// 바뀔 때마다 이걸로 "redirect를 다시 평가해라"라고 알린다.
class _SessionRefreshListenable extends ChangeNotifier {
  void ping() => notifyListeners();
}

/// 매장을 고르지 않아도 열리는 계정 경로 — 로그아웃, 로그인 수단 해제, 탈퇴는 매장 유무와 무관하게
/// 가능해야 한다. **이 밖의 모든 경로는 매장 범위다**(기본이 매장 범위라 새 경로를 더하며 가드를 잊을 수
/// 없다). `test/core/router/app_router_test.dart`가 라우터의 경로를 전부 돌며 이 목록 밖은 매장 선택으로
/// 밀리는지 확인한다.
const accountRoutes = {'/settings/account', '/settings/account/withdraw'};

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
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/invite',
        builder: (context, state) => const InviteCodeScreen(),
      ),
      GoRoute(
        path: '/shops/select',
        builder: (context, state) => const ShopSelectScreen(),
      ),
      GoRoute(path: '/home', builder: (context, state) => const HomeShell()),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/settings/members',
        builder: (context, state) => const MembersScreen(),
      ),
      GoRoute(
        path: '/settings/shop',
        builder: (context, state) => const ShopSettingsScreen(),
      ),
      GoRoute(
        path: '/settings/schedule',
        builder: (context, state) => const ScheduleSettingsScreen(),
      ),
      GoRoute(
        path: '/settings/menus',
        builder: (context, state) => const MenuSettingsScreen(),
      ),
      GoRoute(
        path: '/settings/account',
        builder: (context, state) => const AccountScreen(),
      ),
      GoRoute(
        path: '/settings/account/withdraw',
        builder: (context, state) => const WithdrawScreen(),
      ),
      GoRoute(
        path: '/pets/:petId',
        builder: (context, state) =>
            PetDetailScreen(petId: int.parse(state.pathParameters['petId']!)),
      ),
      GoRoute(
        path: '/pets/:petId/edit',
        builder: (context, state) => PetFormScreen.edit(
          petId: int.parse(state.pathParameters['petId']!),
        ),
      ),
      GoRoute(
        path: '/customers/:customerId/pets/new',
        builder: (context, state) => PetFormScreen.add(
          customerId: int.parse(state.pathParameters['customerId']!),
        ),
      ),
      GoRoute(
        path: '/customers/:customerId/edit',
        builder: (context, state) => CustomerEditScreen(
          customerId: int.parse(state.pathParameters['customerId']!),
        ),
      ),
      // `?pick=1`이면 예약 ①에서 연 것 — 등록한 고객 ID 를 돌려주며 닫는다.
      GoRoute(
        path: '/customers/new',
        builder: (context, state) => RegisterCustomerScreen(
          pickForReservation: state.uri.queryParameters['pick'] == '1',
        ),
      ),
      // `?date=2026-10-02`면 그 날로 연다. `extra`가 다음 예약 초안이면 ②를 채워 연다.
      GoRoute(
        path: '/visits/new',
        builder: (context, state) {
          final date = state.uri.queryParameters['date'];
          final extra = state.extra;
          return RegisterVisitScreen(
            date: date == null ? null : parseDay(date),
            draft: extra is NextVisitDraft ? extra : null,
            prefill: extra is VisitPrefill ? extra : null,
          );
        },
      ),
      GoRoute(
        path: '/visits/draft',
        builder: (context, state) => DraftScreen(text: state.extra as String),
      ),
      GoRoute(
        path: '/visits/day/:date',
        builder: (context, state) =>
            DayScreen(date: parseDay(state.pathParameters['date']!)),
      ),
      // '/visits/new' 뒤에 둔다 — 먼저 두면 'new'를 방문 ID 로 읽는다.
      GoRoute(
        path: '/visits/:visitId',
        builder: (context, state) => VisitDetailScreen(
          visitId: int.parse(state.pathParameters['visitId']!),
        ),
      ),
      GoRoute(
        path: '/visits/:visitId/edit',
        builder: (context, state) => VisitEditScreen(
          visitId: int.parse(state.pathParameters['visitId']!),
        ),
      ),
      // `?complete=1`이면 완료 흐름 — 저장 버튼이 "완료하기"이고 완료하면 true 로 닫힌다.
      GoRoute(
        path: '/visits/:visitId/record',
        builder: (context, state) => RecordScreen(
          visitId: int.parse(state.pathParameters['visitId']!),
          completing: state.uri.queryParameters['complete'] == '1',
        ),
      ),
      // 알림장 보내기 전 미리보기. `?pick=1`이면 보낸 뒤의 [보낼 사진 고르기] — 버튼이 [저장]이고
      // 공유 시트를 열지 않는다. 보냈거나 저장했으면 true 로 닫힌다.
      GoRoute(
        path: '/visits/:visitId/report',
        builder: (context, state) => ReportPreviewScreen(
          visitId: int.parse(state.pathParameters['visitId']!),
          picking: state.uri.queryParameters['pick'] == '1',
        ),
      ),
      // 크게 보기 — [mediaId]의 사진부터 연다.
      GoRoute(
        path: '/visits/:visitId/photos/:mediaId',
        builder: (context, state) => PhotoViewerScreen(
          visitId: int.parse(state.pathParameters['visitId']!),
          mediaId: int.parse(state.pathParameters['mediaId']!),
        ),
      ),
    ],
  );

  ref.onDispose(router.dispose);
  return router;
});

// 불변식: 매장이 하나면 세션(`SessionController._resolveWith`)이 자동으로
// 선택한다 — 그래서 `selectedShopId == null`은 매장이 둘 이상일 때만 있을 수
// 있다. 이 함수의 매장 ≥2 분기는 그 불변식에 기대고 있으므로, `_resolveWith`의
// 자동 선택 규칙을 바꾸면 여기 가드에도 구멍이 생길 수 있다.
String? _redirectSignedIn({
  required String location,
  required int shopCount,
  required int? selectedShopId,
}) {
  if (shopCount == 0) {
    if (accountRoutes.contains(location)) return null;
    return location == '/invite' ? null : '/invite';
  }

  if (shopCount >= 2 && selectedShopId == null) {
    if (accountRoutes.contains(location)) return null;
    return location == '/shops/select' ? null : '/shops/select';
  }

  if (_entryOnlyRoutes.contains(location)) {
    return '/home';
  }

  return null;
}
