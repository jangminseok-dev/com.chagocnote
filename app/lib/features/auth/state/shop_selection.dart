import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'session.dart';
import 'session_controller.dart';

/// 세션에서 파생한 매장 선택 값들.
///
/// 화면은 세션 전체(`sessionControllerProvider`)가 아니라 여기 있는 값만 watch 한다.
/// `select`로 좁혀 두었으므로 `reloadMe`로 `Me` 객체가 통째로 바뀌어도 값이 같으면
/// 화면을 다시 그리지 않는다(인터페이스 분리 — 화면은 필요한 것만 안다).
///
/// 로그아웃·미선택이면 `selectedShopIdProvider`가 null 이고 나머지는 빈값이다.

/// 지금 고른 매장 ID. 매장 범위 화면은 이것으로 프로바이더 키를 만든다.
final selectedShopIdProvider = Provider<int?>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.selectedShopId : null;
    }),
  ),
);

/// 고른 매장에서 사장인가. 직원에게 숨기는 화면·버튼이 본다(보안 경계는 서버 403).
final isOwnerProvider = Provider<bool>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn && (value.selectedShop?.isOwner ?? false);
    }),
  ),
);

/// 고른 매장의 이름. 없으면 빈 문자열.
final shopNameProvider = Provider<String>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.selectedShop?.shopName ?? '' : '';
    }),
  ),
);

/// 소속 매장 수. 설정 화면이 "매장 바꾸기" 줄을 보일지 정한다.
final shopCountProvider = Provider<int>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.me.shops.length : 0;
    }),
  ),
);

/// 로그인한 유저의 ID. 멤버 목록에서 "나"를 표시할 때 쓴다.
final currentUserIdProvider = Provider<int?>(
  (ref) => ref.watch(
    sessionControllerProvider.select((session) {
      final value = session.value;
      return value is SignedIn ? value.me.id : null;
    }),
  ),
);
