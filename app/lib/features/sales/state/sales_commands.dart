import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/shop_scoped.dart';
import 'sales_providers.dart';

/// 매출의 쓰기 — 월 목표 하나. 성공하든 실패하든 요약을 다시 읽게 한다(다른 기기에서 바꿨을 수 있다).
class SalesCommands {
  SalesCommands(this._ref);

  final Ref _ref;

  /// 월 목표를 정한다. null 이면 지운다. 저장된 값을 돌려준다.
  Future<int?> setGoal(int shopId, int? monthlyAmount) async {
    try {
      return await runShopScoped(
        _ref,
        () => _ref.read(salesApiProvider).setGoal(shopId, monthlyAmount),
      );
    } finally {
      _ref.invalidate(salesSummaryProvider);
    }
  }
}

final salesCommandsProvider = Provider<SalesCommands>((ref) => SalesCommands(ref));
