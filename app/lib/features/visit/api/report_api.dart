import '../../../core/proxy/api_client.dart';
import 'report_models.dart';

/// 미용 알림장 API(⑤ 설계 6.1). 경로는 모두 `/v1/shops/{shopId}` 아래다.
class ReportApi {
  ReportApi(this._client);

  final ApiClient _client;

  /// 미리보기 — 보호자가 볼 내용과 링크 상태. 기록이 없으면 409 `VISIT_NO_RECORD_YET`.
  Future<VisitReportPreview> preview(int shopId, int visitId) async =>
      VisitReportPreview.fromJson(
        await _client.get('/v1/shops/$shopId/visits/$visitId/report')
            as Map<String, dynamic>,
      );

  /// 뺄 것 전부([hiddenMediaIds], 없으면 빈 목록)를 저장하고, 살아 있는 링크가 없으면 만든다.
  /// 같은 본문으로 여러 번 불러도 결과가 같다.
  Future<VisitReportPreview> send(
    int shopId,
    int visitId, {
    required List<int> hiddenMediaIds,
  }) async => VisitReportPreview.fromJson(
    await _client.put(
          '/v1/shops/$shopId/visits/$visitId/report',
          data: {'hidden_media_ids': hiddenMediaIds},
        )
        as Map<String, dynamic>,
  );

  /// 살아 있는 링크를 끊는다. 없으면 404 `REPORT_NOT_FOUND`.
  Future<void> revoke(int shopId, int visitId) async {
    await _client.delete('/v1/shops/$shopId/visits/$visitId/report');
  }

  Future<ReportSettings> settings(int shopId) async => ReportSettings.fromJson(
    await _client.get('/v1/shops/$shopId/report-settings')
        as Map<String, dynamic>,
  );

  /// 전체 교체. 사장만 할 수 있다(`shop:update`).
  Future<ReportSettings> updateSettings(
    int shopId,
    ReportSettings settings,
  ) async => ReportSettings.fromJson(
    await _client.put(
          '/v1/shops/$shopId/report-settings',
          data: settings.toJson(),
        )
        as Map<String, dynamic>,
  );
}
