import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/shop_api.dart';
import 'shop_errors.dart';
import 'shop_providers.dart';

/// 매장 하나의 멤버 목록과 그 관리 동작. 매장 id로 만든
/// [membersControllerProvider] family가 매장마다 별도 인스턴스를 준다.
class MembersController extends AsyncNotifier<List<ShopMember>> {
  MembersController(this.shopId);

  final int shopId;

  ShopApi get _api => ref.read(shopApiProvider);

  @override
  Future<List<ShopMember>> build() => _api.members(shopId);

  Future<void> _reload() async {
    state = AsyncData(await _api.members(shopId));
  }

  int? _userIdFor(int memberId) {
    for (final member in state.value ?? const <ShopMember>[]) {
      if (member.memberId == memberId) return member.userId;
    }
    return null;
  }

  bool _isCurrentUser(int userId) {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn && session.me.id == userId;
  }

  Future<CreatedInvite> createInvite() {
    return runShopScoped(ref, () async {
      final result = await _api.createInvite(shopId);
      await _reload();
      return result;
    });
  }

  Future<void> changeRole(int memberId, String role) {
    return runShopScoped(ref, () async {
      final userId = _userIdFor(memberId);
      await _api.changeRole(shopId, memberId, role);
      await _reload();
      if (userId != null && _isCurrentUser(userId)) {
        await ref.read(sessionControllerProvider.notifier).reloadMe();
      }
    });
  }

  Future<void> remove(int memberId) {
    return runShopScoped(ref, () async {
      final userId = _userIdFor(memberId);
      await _api.removeMember(shopId, memberId);
      await _reload();
      if (userId != null && _isCurrentUser(userId)) {
        await ref.read(sessionControllerProvider.notifier).reloadMe();
      }
    });
  }
}

final membersControllerProvider =
    AsyncNotifierProvider.family<MembersController, List<ShopMember>, int>(
  MembersController.new,
);
