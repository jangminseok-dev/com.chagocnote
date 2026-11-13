import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/time/shop_time.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/sales_models.dart';
import 'sales_providers.dart';

/// 지금까지 불러온 목록과 다음 쪽 상태(피드와 같은 꼴).
class SalesPagedState<T> {
  const SalesPagedState({
    required this.items,
    required this.nextCursor,
    this.loadingMore = false,
    this.loadMoreError,
  });

  final List<T> items;
  final String? nextCursor;

  /// 다음 쪽을 불러오는 중.
  final bool loadingMore;

  /// 마지막 다음 쪽 요청의 오류. 이미 보인 목록은 그대로 둔다.
  final Object? loadMoreError;

  bool get hasMore => nextCursor != null;
}

/// 커서로 이어 읽는 목록. 첫 쪽은 build 가, 다음 쪽은 [loadMore]가 읽는다.
abstract class SalesPagedController<T> extends AsyncNotifier<SalesPagedState<T>> {
  /// build() 가 돌 때마다 하나씩 는다 — 다시 불러오는 사이 끝난 다음 쪽 요청이 새 목록에 옛 쪽을 붙이지 않게.
  int _generation = 0;

  Future<SalesPage<T>> fetch(String? cursor);

  @override
  Future<SalesPagedState<T>> build() async {
    _generation++;
    final page = await runShopScoped(ref, () => fetch(null));
    return SalesPagedState(items: page.items, nextCursor: page.nextCursor);
  }

  /// 다음 쪽을 붙인다. 첫 쪽을 불러오는 중이거나, 이미 다음 쪽을 불러오는 중이거나, 마지막 쪽이면 아무것도 하지 않는다.
  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current == null || !current.hasMore || current.loadingMore) return;
    final generation = _generation;
    bool stale() => !ref.mounted || generation != _generation;
    state = AsyncData(
      SalesPagedState(items: current.items, nextCursor: current.nextCursor, loadingMore: true),
    );
    try {
      final page = await runShopScoped(ref, () => fetch(current.nextCursor));
      if (stale()) return;
      state = AsyncData(
        SalesPagedState(items: [...current.items, ...page.items], nextCursor: page.nextCursor),
      );
    } catch (e) {
      if (stale()) return;
      state = AsyncData(
        SalesPagedState(items: current.items, nextCursor: current.nextCursor, loadMoreError: e),
      );
    }
  }
}

/// 방문 목록의 조건. [anchor]는 `2026-11-14` 꼴의 글자다.
typedef SalesVisitsKey = ({
  int shopId,
  SalesSpan span,
  String anchor,
  SalesVisitFilter filter,
  int? menuId,
});

class SalesVisitsController extends SalesPagedController<SalesVisitItem> {
  SalesVisitsController(this.query);

  final SalesVisitsKey query;

  @override
  Future<SalesPage<SalesVisitItem>> fetch(String? cursor) => ref
      .read(salesApiProvider)
      .visits(
        query.shopId,
        query.span,
        parseDay(query.anchor),
        query.filter,
        menuId: query.menuId,
        cursor: cursor,
      );
}

final salesVisitsProvider = AsyncNotifierProvider.autoDispose
    .family<SalesVisitsController, SalesPagedState<SalesVisitItem>, SalesVisitsKey>(
      SalesVisitsController.new,
    );

class DuePetsController extends SalesPagedController<DuePetItem> {
  DuePetsController(this.shopId);

  final int shopId;

  @override
  Future<SalesPage<DuePetItem>> fetch(String? cursor) =>
      ref.read(salesApiProvider).duePets(shopId, cursor: cursor);
}

final duePetsProvider = AsyncNotifierProvider.autoDispose
    .family<DuePetsController, SalesPagedState<DuePetItem>, int>(DuePetsController.new);
