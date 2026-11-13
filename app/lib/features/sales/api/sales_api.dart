import '../../../core/proxy/api_client.dart';
import '../../../core/time/shop_time.dart';
import 'sales_models.dart';

/// 매출 통계 API. 경로는 모두 `/v1/shops/{shopId}/sales` 아래이고 사장만 부른다(`sales:read`).
class SalesApi {
  SalesApi(this._client);

  final ApiClient _client;

  /// 기간의 요약. [anchor]는 그 기간 안의 아무 날이다.
  Future<SalesSummary> summary(int shopId, SalesSpan span, DateTime anchor) async {
    final data =
        await _client.get(
              '/v1/shops/$shopId/sales/summary',
              queryParameters: {'span': span.name, 'anchor': isoDay(anchor)},
            )
            as Map<String, dynamic>;
    return SalesSummary.fromJson(data, span);
  }
}
