import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/shop_scoped.dart';
import '../api/report_api.dart';
import '../api/report_models.dart';
import 'feed_controller.dart';
import 'report_providers.dart';
import 'report_rules.dart';
import 'visit_providers.dart';

/// 알림장 쓰기 — 보내기·끊기·설정. 모든 호출은 매장 범위 공통 처리(`NOT_A_MEMBER` → 내 정보
/// 재조회)를 거친다.
class ReportCommands {
  ReportCommands(this._ref);

  final Ref _ref;

  ReportApi get _api => _ref.read(reportApiProvider);

  /// 보내기·다시 저장. 직전에 미리보기를 다시 읽어 [changes](미디어 ID → 뺄지)를 덮은 목록으로
  /// PUT 한다 — 낡은 화면이 그 사이 다른 기기에서 뺀 사진을 되살리지 않게.
  Future<VisitReportPreview> send(
    int shopId,
    int visitId, {
    required Map<int, bool> changes,
  }) => _linkWrite(() async {
    final now = await _api.preview(shopId, visitId);
    return _api.send(
      shopId,
      visitId,
      hiddenMediaIds: hiddenIdsOf(now.media, changes),
    );
  });

  /// 링크 끊기 — '안 보냄'으로 돌아간다.
  Future<void> revoke(int shopId, int visitId) =>
      _linkWrite(() => _api.revoke(shopId, visitId));

  /// 설정 전체 교체. 미리보기의 "함께 보이는 항목"과 기간 안내가 설정을 따른다.
  Future<ReportSettings> updateSettings(
    int shopId,
    ReportSettings settings,
  ) async {
    final result = await runShopScoped(
      _ref,
      () => _api.updateSettings(shopId, settings),
    );
    _ref.invalidate(reportSettingsProvider);
    _ref.invalidate(visitReportProvider);
    return result;
  }

  /// 보내기·끊기는 **성공하든 실패하든** 링크 상태를 보이는 화면을 다시 불러오게 한다 — 방문 상세,
  /// 하루 목록·피드(반려동물 상세의 [기록] 탭 포함)의 보냄 표시, 미리보기. 409·404 가 나면 화면이
  /// 서버와 어긋나 있다는 뜻이다(`VisitCommands` 와 같은 이유). 달력·고객 쪽은 알림장과 무관하다.
  Future<T> _linkWrite<T>(Future<T> Function() action) async {
    try {
      return await runShopScoped(_ref, action);
    } finally {
      _ref.invalidate(visitDetailProvider);
      _ref.invalidate(dayVisitsProvider);
      _ref.invalidate(feedControllerProvider);
      _ref.invalidate(visitReportProvider);
    }
  }
}

final reportCommandsProvider = Provider<ReportCommands>(
  (ref) => ReportCommands(ref),
);
