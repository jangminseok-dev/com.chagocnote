import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/session_controller.dart';
import '../api/shop_api.dart';
import 'shop_errors.dart';
import 'shop_providers.dart';

/// 매장 하나의 정보. 매장 id로 만든 [shopSettingsControllerProvider]
/// family가 매장마다 별도 인스턴스를 준다.
class ShopSettingsController extends AsyncNotifier<ShopSettings> {
  ShopSettingsController(this.shopId);

  final int shopId;

  ShopApi get _api => ref.read(shopApiProvider);

  @override
  Future<ShopSettings> build() =>
      runShopScoped(ref, () => _api.settings(shopId));

  Future<void> save({
    required String name,
    String? phone,
    String? address,
  }) {
    return runShopScoped(ref, () async {
      final updated = await _api.updateSettings(
        shopId,
        name: name,
        phone: phone,
        address: address,
      );
      state = AsyncData(updated);
      // 이름이 바뀌었을 수 있으니 본인 정보를 다시 불러와 홈의 매장 이름도
      // 갱신한다.
      await ref.read(sessionControllerProvider.notifier).reloadMe();
    });
  }
}

final shopSettingsControllerProvider = AsyncNotifierProvider.family<
    ShopSettingsController, ShopSettings, int>(
  ShopSettingsController.new,
);
