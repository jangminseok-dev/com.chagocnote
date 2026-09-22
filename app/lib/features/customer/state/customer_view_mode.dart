import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';

enum CustomerViewMode { list, grid }

/// 고객 목록의 보기 방식. 기본은 목록이고, 마지막으로 고른 것을 기기에
/// 기억한다(설계 2절).
class CustomerViewModeController extends AsyncNotifier<CustomerViewMode> {
  @override
  Future<CustomerViewMode> build() async {
    final saved = await ref.read(prefsStoreProvider).readCustomerViewMode();
    return saved == CustomerViewMode.grid.name
        ? CustomerViewMode.grid
        : CustomerViewMode.list;
  }

  Future<void> select(CustomerViewMode mode) async {
    state = AsyncData(mode);
    await ref.read(prefsStoreProvider).writeCustomerViewMode(mode.name);
  }
}

final customerViewModeProvider =
    AsyncNotifierProvider<CustomerViewModeController, CustomerViewMode>(
      CustomerViewModeController.new,
    );
