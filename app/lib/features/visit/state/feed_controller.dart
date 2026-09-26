import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_kind.dart';
import '../../../core/plugs/pet_records_plug.dart';
import '../../../core/proxy/network_watcher.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/feed_models.dart';
import 'visit_providers.dart';

/// 피드 조회 조건. [petId]가 있으면 그 아이의 기록만(반려동물 상세의 [기록] 탭).
typedef FeedQuery = ({int shopId, int? petId});

/// 지금까지 불러온 피드와 다음 쪽 상태.
class FeedState {
  const FeedState({
    required this.items,
    required this.nextCursor,
    this.loadingMore = false,
    this.loadMoreError,
  });

  final List<FeedItem> items;
  final String? nextCursor;

  /// 다음 쪽을 불러오는 중.
  final bool loadingMore;

  /// 마지막 다음 쪽 요청의 오류. 이미 보인 목록은 그대로 둔다.
  final Object? loadMoreError;

  bool get hasMore => nextCursor != null;
}

/// 완료 방문 피드 — 커서로 이어 읽는다(설계 9절). 기록·전이를 쓰면 `VisitCommands`가 무효화한다.
class FeedController extends AsyncNotifier<FeedState> {
  FeedController(this.query);

  final FeedQuery query;

  /// build() 가 돌 때마다 하나씩 는다 — 다시 불러오는 사이 끝난 다음 쪽 요청이 새 목록에 옛 쪽을
  /// 붙이지 않게 비교한다(고객 목록과 같은 이유).
  int _generation = 0;

  /// 다음 쪽이 인터넷 없음으로 실패한 동안만 복귀 신호를 듣는다 — 돌아오면 한 번 다시 부른다
  /// (오류 화면 다듬기 설계 3절).
  StreamSubscription<void>? _restored;

  void _stopWatchingNetwork() {
    _restored?.cancel();
    _restored = null;
  }

  Future<VisitFeed> _fetch(String? cursor) => runShopScoped(
    ref,
    () => ref
        .read(visitApiProvider)
        .feed(query.shopId, cursor: cursor, petId: query.petId),
  );

  @override
  Future<FeedState> build() async {
    _generation++;
    ref.onDispose(_stopWatchingNetwork);
    final page = await _fetch(null);
    return FeedState(items: page.items, nextCursor: page.nextCursor);
  }

  /// 다음 쪽을 붙인다. 첫 쪽을 불러오는 중이거나, 이미 다음 쪽을 불러오는 중이거나, 마지막 쪽이면
  /// 아무것도 하지 않는다.
  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading ||
        current == null ||
        !current.hasMore ||
        current.loadingMore) {
      return;
    }
    final generation = _generation;
    bool stale() => !ref.mounted || generation != _generation;
    state = AsyncData(
      FeedState(
        items: current.items,
        nextCursor: current.nextCursor,
        loadingMore: true,
      ),
    );
    try {
      final page = await _fetch(current.nextCursor);
      if (stale()) return;
      state = AsyncData(
        FeedState(
          items: [...current.items, ...page.items],
          nextCursor: page.nextCursor,
        ),
      );
    } catch (e) {
      if (stale()) return;
      if (kindOf(e) == ErrorKind.offline) {
        _restored ??= ref.read(networkWatcherProvider).restored.listen((_) {
          _stopWatchingNetwork();
          loadMore();
        });
      }
      state = AsyncData(
        FeedState(
          items: current.items,
          nextCursor: current.nextCursor,
          loadMoreError: e,
        ),
      );
    }
  }
}

final feedControllerProvider = AsyncNotifierProvider.autoDispose
    .family<FeedController, FeedState, FeedQuery>(FeedController.new);

/// 반려동물 상세를 당겨서 새로고침하면 [기록] 탭(그 아이의 피드)도 다시 읽는다 — `app.dart`가
/// `petRecordsRefreshPlugProvider`에 꽂는다.
PetRecordsRefresher petRecordsRefresher(Ref ref) =>
    (_) => ref.invalidate(feedControllerProvider);
