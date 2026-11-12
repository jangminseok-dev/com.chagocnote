import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../auth/state/shop_scoped.dart';
import '../api/notification_api.dart';
import '../api/notification_models.dart';
import 'notification_providers.dart';

/// 알림장을 보낸 뒤 알림톡이 어떻게 됐는지.
sealed class ReportDelivery {
  const ReportDelivery();
}

/// 이번 보내기가 만든 알림톡 줄이 없다(미연동·꺼짐·미승인, 또는 곧바로 취소됨) — 공유 시트로 보낸다.
class ReportNotSent extends ReportDelivery {
  const ReportNotSent();
}

/// 알림톡(또는 문자 대체)으로 나갔다.
class ReportDelivered extends ReportDelivery {
  const ReportDelivered();
}

/// 못 보냈다. [shareText]는 다른 방법으로 보낼 문안(주소가 들어 있다 — 남기지 않는다).
class ReportFailed extends ReportDelivery {
  const ReportFailed(this.shareText);

  final String? shareText;
}

/// 기다려도 아직 보내는 중이다 — 방문 상세의 블록이 나중에 보인다.
class ReportPending extends ReportDelivery {
  const ReportPending();
}

/// 알림톡 쓰기 — 연동·설정·발신번호, 알림장 발송 결과 기다리기, 다시 보내기. 모든 호출은 매장 범위 공통
/// 처리(`NOT_A_MEMBER` → 내 정보 재조회)를 거친다.
class NotificationCommands {
  NotificationCommands(this._ref);

  /// 알림장 발송 결과를 보는 횟수(1초 간격 — 최대 10초).
  static const _reportPolls = 10;

  /// 재발송 뒤 그 줄을 보는 횟수.
  static const _resendPolls = 5;

  final Ref _ref;

  NotificationApi get _api => _ref.read(notificationApiProvider);

  Future<void> _wait() => _ref.read(notificationPollWaitProvider)();

  Future<void> requestChannelToken(
    int shopId, {
    required String searchId,
    required String adminPhone,
    required String categoryCode,
  }) => _overviewWrite(
    () => _api.requestChannelToken(
      shopId,
      searchId: searchId,
      adminPhone: adminPhone,
      categoryCode: categoryCode,
    ),
  );

  Future<void> linkChannel(
    int shopId, {
    required String searchId,
    required String adminPhone,
    required String categoryCode,
    required String token,
  }) => _overviewWrite(
    () => _api.linkChannel(
      shopId,
      searchId: searchId,
      adminPhone: adminPhone,
      categoryCode: categoryCode,
      token: token,
    ),
  );

  Future<void> unlinkChannel(int shopId) =>
      _overviewWrite(() => _api.unlinkChannel(shopId));

  /// 설정 전체 교체(아홉 칸).
  Future<void> updateSettings(int shopId, Map<String, dynamic> body) =>
      _overviewWrite(() => _api.updateSettings(shopId, body));

  Future<void> requestSenderVerification(int shopId, String phone) =>
      _overviewWrite(() => _api.requestSenderVerification(shopId, phone));

  Future<void> confirmSender(
    int shopId, {
    required String phone,
    required String code,
  }) => _overviewWrite(
    () => _api.confirmSender(shopId, phone: phone, code: code),
  );

  /// 알림장을 보내기 **전에** 부른다 — 그 방문에 이미 있는 알림장 알림톡 줄의 ID. 보낸 뒤 이 밖의 줄만
  /// 이번 보내기의 결과로 친다(끊고 다시 보낼 때 옛 '보냄' 줄을 새 발송으로 알리지 않게). 읽지 못하면 null.
  Future<Set<int>?> reportRowIds(int shopId, int visitId) async {
    try {
      final rows = await runShopScoped(
        _ref,
        () => _api.forVisit(shopId, visitId),
      );
      return {
        for (final row in rows)
          if (row.kind == NotificationKind.report) row.messageId,
      };
    } on ApiException {
      return null;
    }
  }

  /// 알림장을 보낸 뒤 [before] 밖의 가장 최근 알림장 줄을 1초 간격으로 최대 열 번 본다. [before]가
  /// null(보내기 전 내역을 읽지 못함)이면 보지 않는다. 끝나면 방문의 내역을 다시 읽게 한다.
  Future<ReportDelivery> awaitReport(
    int shopId,
    int visitId, {
    required Set<int>? before,
  }) async {
    if (before == null) return const ReportNotSent();
    try {
      for (var poll = 0; poll < _reportPolls; poll++) {
        if (poll > 0) await _wait();
        final List<NotificationMessage> rows;
        try {
          rows = await runShopScoped(
            _ref,
            () => _api.forVisit(shopId, visitId),
          );
        } on ApiException {
          continue; // 이번 한 번은 건너뛴다 — 다음에 다시 본다.
        }
        final row = rows
            .where(
              (m) =>
                  m.kind == NotificationKind.report &&
                  !before.contains(m.messageId),
            )
            .firstOrNull;
        if (row == null) return const ReportNotSent();
        switch (row.status) {
          case NotificationStatus.sent || NotificationStatus.fallbackSent:
            return const ReportDelivered();
          case NotificationStatus.failed:
            return ReportFailed(row.shareText);
          case NotificationStatus.canceled:
            return const ReportNotSent();
          case NotificationStatus.scheduled ||
              NotificationStatus.sending ||
              NotificationStatus.accepted:
            break;
        }
      }
      return const ReportPending();
    } finally {
      _ref.invalidate(visitNotificationsProvider);
    }
  }

  /// 그 종류의 가장 최근 줄을 다시 보내고, 1초 간격으로 최대 다섯 번 그 줄이 끝났는지 본다. 재발송
  /// 직후와 끝난 뒤(실패해도) 방문의 내역을 다시 읽게 한다 — 404·409 는 화면이 서버와 어긋나 있다는 뜻이다.
  Future<void> resend(int shopId, int visitId, NotificationKind kind) async {
    final int messageId;
    try {
      messageId = await runShopScoped(
        _ref,
        () => _api.resend(shopId, visitId, kind),
      );
    } finally {
      _ref.invalidate(visitNotificationsProvider);
    }
    try {
      for (var poll = 0; poll < _resendPolls; poll++) {
        await _wait();
        try {
          final row = await runShopScoped(
            _ref,
            () => _api.message(shopId, messageId),
          );
          if (row == null || !row.status.pending) return;
        } on ApiException {
          // 상태를 못 읽어도 재발송은 됐다 — 다음에 다시 본다.
        }
      }
    } finally {
      _ref.invalidate(visitNotificationsProvider);
    }
  }

  /// 연동·설정·발신번호 쓰기는 **성공하든 실패하든** 한눈에 보기를 다시 읽게 한다 — 설정 화면은
  /// 낙관적으로 그리지 않고 다시 읽은 값으로 그린다.
  Future<void> _overviewWrite(Future<Object?> Function() action) async {
    try {
      await runShopScoped(_ref, action);
    } finally {
      _ref.invalidate(notificationOverviewProvider);
    }
  }
}

final notificationCommandsProvider = Provider<NotificationCommands>(
  (ref) => NotificationCommands(ref),
);
