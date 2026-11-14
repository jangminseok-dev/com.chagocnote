import '../../../core/proxy/api_client.dart';
import 'search_models.dart';

/// 기록 검색 API. 매장 멤버면 부를 수 있다(사장·직원).
class SearchApi {
  SearchApi(this._client);

  final ApiClient _client;

  /// 매장이 적어 둔 글에서 [q]를 찾는다. [petId]를 주면 그 아이의 글과 그 아이 보호자의 메모 안에서만.
  /// [q]는 다듬은 2~100자여야 한다(`cleanSearchText`).
  Future<SearchResult> search(int shopId, String q, {int? petId}) async {
    final data =
        await _client.get(
              '/v1/shops/$shopId/search',
              queryParameters: {'q': q, 'pet_id': ?petId},
            )
            as Map<String, dynamic>;
    return SearchResult.fromJson(data);
  }
}
