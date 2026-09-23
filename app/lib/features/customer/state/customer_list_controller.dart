import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shop/state/shop_errors.dart';
import '../api/customer_api.dart';
import '../api/customer_models.dart';
import 'customer_providers.dart';

/// 목록 조회 조건. 조건마다 컨트롤러가 따로 생긴다 — 검색어가 바뀌면 화면은
/// 새 조건의 컨트롤러를 보고, 앞선 조건의 컨트롤러는 버려진다(autoDispose).
/// 그래서 늦게 도착한 옛 검색 결과가 새 결과를 덮지 않는다(C12).
typedef CustomerListQuery = ({
  int shopId,
  String q,
  String sort,
  bool includePassed,
});

/// 지금까지 불러온 가족 카드와 다음 페이지 상태.
class CustomerListState {
  const CustomerListState({
    required this.items,
    required this.nextCursor,
    required this.petCount,
    this.loadingMore = false,
    this.loadMoreError,
  });

  final List<FamilyCard> items;
  final String? nextCursor;
  final int petCount;

  /// 다음 페이지를 불러오는 중.
  final bool loadingMore;

  /// 마지막 다음 페이지 요청의 오류. 이미 보인 목록은 그대로 둔다.
  final Object? loadMoreError;

  bool get hasMore => nextCursor != null;
}

class CustomerListController extends AsyncNotifier<CustomerListState> {
  CustomerListController(this.query);

  final CustomerListQuery query;

  CustomerApi get _api => ref.read(customerApiProvider);

  /// build() 가 돌 때마다 하나씩 는다. 다시 불러오는 사이(쓰기 뒤 invalidate)
  /// 끝난 다음 페이지 요청이 새 목록에 옛 페이지를 붙이지 않게 비교한다 —
  /// 다시 불러와도 컨트롤러 인스턴스는 그대로라 `ref.mounted`만으로는 모른다.
  int _generation = 0;

  Future<CustomerPage> _fetch(String? cursor) => _api.list(
    query.shopId,
    q: query.q,
    sort: query.sort,
    includePassed: query.includePassed,
    cursor: cursor,
  );

  @override
  Future<CustomerListState> build() async {
    _generation++;
    final page = await runShopScoped(ref, () => _fetch(null));
    return CustomerListState(
      items: page.items,
      nextCursor: page.nextCursor,
      petCount: page.petCount,
    );
  }

  /// 다음 페이지를 붙인다. 첫 페이지를 불러오는 중이거나, 이미 다음 페이지를
  /// 불러오는 중이거나, 마지막 페이지면 아무것도 하지 않는다.
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
      CustomerListState(
        items: current.items,
        nextCursor: current.nextCursor,
        petCount: current.petCount,
        loadingMore: true,
      ),
    );
    try {
      final page = await runShopScoped(ref, () => _fetch(current.nextCursor));
      // 그사이 다시 불러왔으면(쓰기 뒤 invalidate) 옛 목록에 이어 붙이지 않는다.
      if (stale()) return;
      state = AsyncData(
        CustomerListState(
          items: [...current.items, ...page.items],
          nextCursor: page.nextCursor,
          petCount: page.petCount,
        ),
      );
    } catch (e) {
      if (stale()) return;
      state = AsyncData(
        CustomerListState(
          items: current.items,
          nextCursor: current.nextCursor,
          petCount: current.petCount,
          loadMoreError: e,
        ),
      );
    }
  }
}

final customerListControllerProvider = AsyncNotifierProvider.autoDispose
    .family<CustomerListController, CustomerListState, CustomerListQuery>(
      CustomerListController.new,
    );
