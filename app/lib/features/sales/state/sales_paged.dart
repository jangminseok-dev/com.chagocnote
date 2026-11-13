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

  /// 지금까지 불러온 만큼을 처음부터 다시 읽어 갈아 끼운다 — 상세에 다녀온 뒤에 쓴다.
  ///
  /// 무효화(build 를 다시 돌리기)와 달리 [더 보기]로 이어 읽은 줄이 첫 쪽으로 줄지 않고, 읽는 동안에도
  /// 보이던 줄이 그대로 있다. 실패하면 보이던 목록을 둔다(당겨서 새로고침으로 다시 읽을 수 있다).
  Future<void> reload() async {
    final current = state.value;
    if (state.isLoading || current == null || current.loadingMore) return;
    final generation = _generation;
    try {
      final items = <T>[];
      String? cursor;
      do {
        final at = cursor;
        final page = await runShopScoped(ref, () => fetch(at));
        if (!ref.mounted || generation != _generation) return;
        items.addAll(page.items);
        cursor = page.nextCursor;
      } while (cursor != null && items.length < current.items.length);
      // 읽는 사이 [더 보기]가 줄을 붙였으면 그쪽이 더 새롭다 — 덮지 않는다.
      if (state.value != current) return;
      state = AsyncData(SalesPagedState(items: items, nextCursor: cursor));
    } catch (_) {
      // 보이던 목록을 그대로 둔다.
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
