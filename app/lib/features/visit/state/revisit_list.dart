import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/shop_scoped.dart';
import '../api/revisit_models.dart';
import 'visit_providers.dart';

/// 다시 올 때가 된 아이 목록(⑬) — 지금까지 불러온 줄과 다음 쪽 상태(매출 목록·피드와 같은 꼴).
class RevisitListState {
  const RevisitListState({
    required this.items,
    required this.nextCursor,
    this.loadingMore = false,
    this.loadMoreError,
  });

  final List<RevisitItem> items;
  final String? nextCursor;
  final bool loadingMore;

  /// 마지막 다음 쪽 요청의 오류. 이미 보인 줄은 그대로 둔다.
  final Object? loadMoreError;

  bool get hasMore => nextCursor != null;
}

typedef RevisitsKey = ({int shopId, RevisitBucket bucket});

/// 커서로 이어 읽는 목록 — 첫 쪽은 build, 다음 쪽은 [loadMore]. 규칙은 매출의 `SalesPagedController` 와 같다
/// (visit 는 sales 를 import 하지 않는다): 세대 번호로 옛 쪽을 버리고, 다음 쪽이 실패하면 보인 줄은 두고,
/// [reload] 는 불러온 만큼을 처음부터 다시 읽어 갈아 끼운다(예약을 잡고 돌아오면 그 줄이 빠진다).
class RevisitListController extends AsyncNotifier<RevisitListState> {
  RevisitListController(this.key);

  final RevisitsKey key;
  int _generation = 0;

  Future<RevisitPage> _fetch(String? cursor) => runShopScoped(
    ref,
    () => ref.read(visitApiProvider).revisits(key.shopId, key.bucket, cursor: cursor),
  );

  @override
  Future<RevisitListState> build() async {
    _generation++;
    final page = await _fetch(null);
    return RevisitListState(items: page.items, nextCursor: page.nextCursor);
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current == null || !current.hasMore || current.loadingMore) return;
    final generation = _generation;
    bool stale() => !ref.mounted || generation != _generation;
    state = AsyncData(
      RevisitListState(items: current.items, nextCursor: current.nextCursor, loadingMore: true),
    );
    try {
      final page = await _fetch(current.nextCursor);
      if (stale()) return;
      state = AsyncData(
        RevisitListState(items: [...current.items, ...page.items], nextCursor: page.nextCursor),
      );
    } catch (e) {
      if (stale()) return;
      state = AsyncData(
        RevisitListState(items: current.items, nextCursor: current.nextCursor, loadMoreError: e),
      );
    }
  }

  Future<void> reload() async {
    final current = state.value;
    if (state.isLoading || current == null || current.loadingMore) return;
    final generation = _generation;
    try {
      final items = <RevisitItem>[];
      String? cursor;
      do {
        final page = await _fetch(cursor);
        if (!ref.mounted || generation != _generation) return;
        items.addAll(page.items);
        cursor = page.nextCursor;
      } while (cursor != null && items.length < current.items.length);
      if (state.value != current) return;
      state = AsyncData(RevisitListState(items: items, nextCursor: cursor));
    } catch (_) {
      // 보이던 줄을 그대로 둔다(당겨서 새로고침으로 다시 읽을 수 있다).
    }
  }
}

final revisitsProvider = AsyncNotifierProvider.autoDispose
    .family<RevisitListController, RevisitListState, RevisitsKey>(RevisitListController.new);
