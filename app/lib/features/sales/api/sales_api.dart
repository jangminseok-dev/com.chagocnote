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

  /// 매출 탭의 숫자에서 이어지는 방문들 — 그 기간의 것만, 최신순 20개씩.
  /// [filter]가 메뉴면 [menuId]가 있어야 한다.
  Future<SalesPage<SalesVisitItem>> visits(
    int shopId,
    SalesSpan span,
    DateTime anchor,
    SalesVisitFilter filter, {
    int? menuId,
    String? cursor,
  }) async {
    final data =
        await _client.get(
              '/v1/shops/$shopId/sales/visits',
              queryParameters: {
                'span': span.name,
                'anchor': isoDay(anchor),
                'filter': filter.wire,
                'menu_id': ?menuId,
                'cursor': ?cursor,
              },
            )
            as Map<String, dynamic>;
    return SalesPage.fromJson(data, SalesVisitItem.fromJson);
  }

  /// 월 목표를 정한다. null 이면 지운다. 저장된 값을 돌려준다.
  Future<int?> setGoal(int shopId, int? monthlyAmount) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/sales/goal',
              data: {'monthly_amount': monthlyAmount},
            )
            as Map<String, dynamic>;
    return data['monthly_amount'] as int?;
  }
}
