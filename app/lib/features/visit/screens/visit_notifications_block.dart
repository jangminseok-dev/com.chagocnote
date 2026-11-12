import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/share_sheet.dart';
import '../../../core/time/time_labels.dart';
import '../../../core/time/today_provider.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../l10n/app_strings.dart';
import '../api/notification_models.dart';
import '../state/notification_commands.dart';
import '../state/notification_providers.dart';
import '../state/notification_rules.dart';
import '../state/visit_providers.dart';

/// 방문 상세의 "알림톡" 블록(⑥ 설계 8.2) — 이 방문의 알림 줄을 최신순으로 보인다. 취소된 줄은 그리지
/// 않고, 줄이 없으면(연동 안 된 매장 포함) 블록도 없다.
///
/// 내역은 방문 상세와 따로 읽는다. 읽는 중이거나 읽지 못했으면 블록만 없다 — 상세 본문을 막지 않는다.
/// 실패한 줄 가운데 그 종류의 가장 최근 줄에만 단추가 있다: 일시 실패는 [다시 보내기](직원도 한다),
/// 영구 실패는 [다른 방법으로 보내기](문자용 문안을 공유 시트에).
class VisitNotificationsBlock extends ConsumerStatefulWidget {
  const VisitNotificationsBlock({super.key, required this.visitKey});

  final VisitKey visitKey;

  @override
  ConsumerState<VisitNotificationsBlock> createState() =>
      _VisitNotificationsBlockState();
}

class _VisitNotificationsBlockState
    extends ConsumerState<VisitNotificationsBlock> {
  bool _busy = false;

  Future<void> _resend(NotificationKind kind) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(notificationCommandsProvider)
          .resend(widget.visitKey.shopId, widget.visitKey.visitId, kind);
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  /// 문안에는 알림장 주소(토큰)가 들 수 있다 — 공유 시트에만 넘기고 어디에도 남기지 않는다.
  Future<void> _shareInstead(String text, Rect origin) async {
    try {
      await ref.read(shareSheetProvider).shareText(text, origin: origin);
    } on Exception {
      if (mounted) AppSnackBar.show(context, AppStrings.reportShareAgainFailed);
    }
  }

  @override
  Widget build(BuildContext context) {
    final all = ref.watch(visitNotificationsProvider(widget.visitKey)).value;
    if (all == null) return const SizedBox.shrink();
    final rows = visibleRows(all);
    if (rows.isEmpty) return const SizedBox.shrink();
    final today = ref.watch(todayProvider);
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: SizedBox(
        width: double.infinity,
        child: AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                AppStrings.notificationBlockTitle,
                style: AppTypography.caption,
              ),
              for (final row in rows) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(_line(row, today), style: AppTypography.body),
                if (row.status == NotificationStatus.failed &&
                    isLatestOfKind(all, row))
                  ..._actions(row),
              ],
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _actions(NotificationMessage row) => switch (row.errorKind) {
    NotificationErrorKind.transient => [
      const SizedBox(height: AppSpacing.xs),
      AppButton(
        label: AppStrings.notificationResend,
        busy: _busy,
        onPressed: _busy ? null : () => _resend(row.kind),
      ),
    ],
    NotificationErrorKind.permanent => [
      if (row.shareText case final text?) ...[
        const SizedBox(height: AppSpacing.xs),
        Builder(
          builder: (context) => AppButton(
            label: AppStrings.notificationShareInstead,
            onPressed: () {
              final box = context.findRenderObject()! as RenderBox;
              _shareInstead(text, box.localToGlobal(Offset.zero) & box.size);
            },
          ),
        ),
      ],
    ],
    null => const [],
  };

  /// 시각 — 오늘이면 시:분만, 아니면 날짜도 붙인다.
  String _at(DateTime at, DateTime today) =>
      sameDay(at, today) ? hhmm(at) : '${dayLabel(at)} ${hhmm(at)}';

  String _line(NotificationMessage row, DateTime today) {
    final kind = switch (row.kind) {
      NotificationKind.confirm => AppStrings.notificationRowConfirm,
      NotificationKind.reminder => AppStrings.notificationRowReminder,
      NotificationKind.report => AppStrings.notificationRowReport,
      NotificationKind.change => AppStrings.notificationRowChange,
      NotificationKind.cancel => AppStrings.notificationRowCancel,
      NotificationKind.nextVisit => AppStrings.notificationRowNextVisit,
    };
    // 보낸 시각이 없으면(서버가 비워 준 경우) 보낼 시각으로 대신한다.
    final sentAt = _at((row.sentAt ?? row.scheduledAt).wall, today);
    final state = switch (row.status) {
      NotificationStatus.scheduled => AppStrings.notificationScheduled(
        _at(row.scheduledAt.wall, today),
      ),
      NotificationStatus.sending ||
      NotificationStatus.accepted => AppStrings.notificationSending,
      NotificationStatus.sent => AppStrings.notificationSent(sentAt),
      NotificationStatus.fallbackSent => AppStrings.notificationSentBySms(
        sentAt,
      ),
      NotificationStatus.failed =>
        '${AppStrings.notificationFailed} · ${switch (row.errorKind) {
          NotificationErrorKind.permanent => AppStrings.notificationFailedPermanent,
          NotificationErrorKind.transient || null => AppStrings.notificationFailedTransient,
        }}',
      // 취소된 줄은 그리지 않는다(visibleRows 가 뺀다).
      NotificationStatus.canceled => '',
    };
    return '$kind · $state';
  }
}
