import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
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
  ///
  /// [onlyIfLive] — 보낼 사진 고르기: 살아 있는 링크의 뺌만 고친다. 다시 읽은 링크가 닫혀 있으면
  /// PUT(없으면 링크를 만든다)을 보내지 않고 `REPORT_NOT_FOUND` 로 끝낸다.
  Future<VisitReportPreview> send(
    int shopId,
    int visitId, {
    required Map<int, bool> changes,
    bool onlyIfLive = false,
  }) => _linkWrite(() async {
    final now = await _api.preview(shopId, visitId);
    if (onlyIfLive && !now.link.live) {
      throw ApiException(
        statusCode: 404,
        code: 'REPORT_NOT_FOUND',
        message: '',
      );
    }
    return _api.send(
      shopId,
      visitId,
      hiddenMediaIds: hiddenIdsOf(now.media, changes),
    );
  });

  /// 링크 끊기 — '안 보냄'으로 돌아간다.
  Future<void> revoke(int shopId, int visitId) =>
      _linkWrite(() => _api.revoke(shopId, visitId));

  /// 설정 전체 교체. 미리보기의 "함께 보이는 항목"과 기간 안내가 설정을 따른다. **성공하든 실패하든**
  /// 설정을 다시 읽게 한다 — 설정 화면은 낙관적으로 그리지 않고 다시 읽은 값으로 그리며, 거절(403)됐다면
  /// 화면이 든 값이 낡았을 수 있다.
  Future<ReportSettings> updateSettings(
    int shopId,
    ReportSettings settings,
  ) async {
    try {
      return await runShopScoped(
        _ref,
        () => _api.updateSettings(shopId, settings),
      );
    } finally {
      _ref.invalidate(reportSettingsProvider);
      _ref.invalidate(visitReportProvider);
    }
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
