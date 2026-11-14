import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/search_api.dart';
import '../api/search_models.dart';
import 'search_rules.dart';

final searchApiProvider = Provider<SearchApi>((ref) => SearchApi(ref.watch(apiClientProvider)));

/// 어디에서 찾는가 — 매장 전체([petId] 없음)이거나 한 아이 안.
typedef SearchScope = ({int shopId, int? petId});

/// 검색 화면의 상태. [result]가 null 이면 아직 묻지 않았다(처음 화면).
class SearchState {
  const SearchState({this.query = '', this.result, this.shown});

  /// 마지막으로 물은(묻고 있는) 다듬은 검색어. 묻지 않았으면 빈 글자.
  final String query;
  final AsyncValue<SearchResult>? result;

  /// 다시 묻는 동안 그대로 보일 앞 결과. 없으면 null.
  final SearchResult? shown;

  /// 화면이 그릴 값 — 다시 묻는 동안에는 앞 결과를 그대로 보인다.
  AsyncValue<SearchResult>? get display =>
      result != null && result!.isLoading && shown != null ? AsyncData(shown!) : result;
}

/// 검색어를 받아 서버에 묻는다. 검색어는 기기에 남기지 않는다 — 화면을 떠나면 버린다(autoDispose).
class SearchController extends Notifier<SearchState> {
  SearchController(this.scope);

  final SearchScope scope;

  /// 물을 때마다, 그리고 처음 화면으로 돌아갈 때마다 하나씩 는다 — 늦게 온 옛 결과를 버리는 데 쓴다.
  int _generation = 0;

  @override
  SearchState build() => const SearchState();

  /// 입력 칸의 글로 찾는다. 다듬어 두 자 미만이면 처음 화면으로 돌아가고(진행 중이던 요청의 결과는 버린다),
  /// 마지막 검색어와 같으면 아무것도 하지 않는다.
  void search(String text) {
    final query = cleanSearchText(text);
    if (query == null) {
      _generation++;
      state = const SearchState();
      return;
    }
    if (query == state.query) return;
    _ask(query);
  }

  /// 실패한 검색을 같은 검색어로 다시 묻는다.
  void retry() {
    if (state.query.isEmpty) return;
    _ask(state.query);
  }

  Future<void> _ask(String query) async {
    final generation = ++_generation;
    bool stale() => !ref.mounted || generation != _generation;
    // 다시 묻는 동안 앞 결과를 그대로 보인다.
    final shown = state.result?.value ?? state.shown;
    state = SearchState(query: query, result: const AsyncLoading(), shown: shown);
    try {
      final result = await runShopScoped(
        ref,
        () => ref.read(searchApiProvider).search(scope.shopId, query, petId: scope.petId),
      );
      if (stale()) return;
      state = SearchState(query: query, result: AsyncData(result));
    } catch (e, stack) {
      if (stale()) return;
      state = SearchState(query: query, result: AsyncError(e, stack));
    }
  }
}

final searchControllerProvider = NotifierProvider.autoDispose
    .family<SearchController, SearchState, SearchScope>(SearchController.new);
