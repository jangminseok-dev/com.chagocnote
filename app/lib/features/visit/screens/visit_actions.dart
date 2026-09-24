import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../api/visit_models.dart';
import '../state/visit_commands.dart';
import 'visit_labels.dart';

/// 상태를 바꾸기 전에 묻는 시트들 — 방문 상세와 하루 목록 카드가 함께 쓴다.
abstract final class VisitSheets {
  /// 취소 사유(필수). 닫으면 null.
  static Future<String?> cancelReason(BuildContext context) =>
      AppSheet.show<String>(
        context,
        builder: (context) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(AppStrings.cancelReasonTitle, style: AppTypography.body),
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              label: AppStrings.reasonCustomerRequest,
              onPressed: () => Navigator.of(context).pop('customer_request'),
            ),
            const SizedBox(height: AppSpacing.sm),
            AppButton(
              label: AppStrings.reasonShopReason,
              onPressed: () => Navigator.of(context).pop('shop_reason'),
            ),
          ],
        ),
      );

  /// 노쇼는 보호자 기록에 남으므로 한 번 묻는다.
  static Future<bool?> confirmNoShow(BuildContext context) =>
      AppSheet.show<bool>(
        context,
        builder: (context) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              AppStrings.noShowConfirm,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              label: AppStrings.actionNoShow,
              filled: true,
              onPressed: () => Navigator.of(context).pop(true),
            ),
            const SizedBox(height: AppSpacing.sm),
            AppButton(
              label: AppStrings.cancel,
              onPressed: () => Navigator.of(context).pop(false),
            ),
          ],
        ),
      );

  /// 완료 시트. true 면 "완료하고 다음 예약 잡기", false 면 완료만, 닫으면 null.
  /// [draft]가 있으면 다음 예약이 언제로 잡히는지 미리 보인다(목업 ④).
  static Future<bool?> complete(
    BuildContext context, {
    NextVisitDraft? draft,
  }) => AppSheet.show<bool>(
    context,
    builder: (context) => Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(AppStrings.completeTitle, style: AppTypography.titleKo),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.actionComplete,
          filled: true,
          icon: Icons.check,
          onPressed: () => Navigator.of(context).pop(false),
        ),
        const SizedBox(height: AppSpacing.sm),
        AppButton(
          label: AppStrings.completeAndNext,
          icon: Icons.arrow_forward,
          onPressed: () => Navigator.of(context).pop(true),
        ),
        if (draft != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            AppStrings.nextPreview(
              '${dayLabel(draft.startsAt.wall)} ${hhmm(draft.startsAt.wall)}',
            ),
            style: AppTypography.bodyStrong,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            AppStrings.completeAndNextCaption(draft.intervalWeeks),
            style: AppTypography.caption,
            textAlign: TextAlign.center,
          ),
        ],
      ],
    ),
  );
}

/// 완료 뒤에 이어서 할 일. 완료 시트의 선택이다 — bool 둘 대신 닫힌 타입으로 두어
/// 종류가 늘 때(④-2 "기록으로") `switch` 한 곳에 분기가 붙는다.
sealed class AfterComplete {
  const AfterComplete();
}

/// 완료만 한다.
class AfterNothing extends AfterComplete {
  const AfterNothing();
}

/// 완료하고 다음 예약 잡기. [draft]는 시트를 띄우기 전에 미리 받아 둔 초안(없을 수 있다).
class AfterNextReservation extends AfterComplete {
  const AfterNextReservation({this.draft});

  final NextVisitDraft? draft;
}

/// 시트에서 고른 상태 전이. [cancelReason]은 취소일 때만, [after]는 완료일 때
/// 이어서 할 일.
class VisitChoice {
  const VisitChoice(
    this.action, {
    this.cancelReason,
    this.after = const AfterNothing(),
  });

  final VisitAction action;
  final String? cancelReason;
  final AfterComplete after;
}

/// 전이에 필요한 것을 시트로 묻는다(취소 사유, 노쇼 확인, 완료 / 완료하고
/// 다음 예약). 묻지 않는 전이(시작·되돌리기)는 그대로 돌려준다. 시트를 닫으면
/// null — 아무것도 보내지 않는다.
///
/// 완료 시트는 먼저 [anchorVisitId]의 다음 예약 초안을 읽어 날짜를 미리 보인다
/// (백엔드가 완료 전 방문의 초안도 준다). 초안을 못 읽어도 시트는 뜬다 —
/// 미리보기는 돕는 것이다.
///
/// 묻는 것과 보내는 것을 나눈다 — 시트가 떠 있는 동안 화면이 "보내는 중"이
/// 되지 않게.
Future<VisitChoice?> askVisitAction(
  BuildContext context,
  WidgetRef ref, {
  required int shopId,
  required VisitAction action,
  required int anchorVisitId,
}) async {
  switch (action) {
    case VisitAction.start:
    case VisitAction.revert:
      return VisitChoice(action);
    case VisitAction.cancel:
      final reason = await VisitSheets.cancelReason(context);
      return reason == null ? null : VisitChoice(action, cancelReason: reason);
    case VisitAction.noShow:
      final ok = await VisitSheets.confirmNoShow(context);
      return ok == true ? const VisitChoice(VisitAction.noShow) : null;
    case VisitAction.complete:
      NextVisitDraft? draft;
      try {
        draft = await ref
            .read(visitCommandsProvider)
            .nextDraft(shopId, anchorVisitId);
      } catch (_) {
        // 미리보기를 못 받아도 완료는 할 수 있어야 한다.
      }
      if (!context.mounted) return null;
      final next = await VisitSheets.complete(context, draft: draft);
      if (next == null) return null;
      return VisitChoice(
        VisitAction.complete,
        after: next ? AfterNextReservation(draft: draft) : const AfterNothing(),
      );
  }
}

/// 고른 전이를 묶음 한 번에 보낸다. [ids]는 같은 보호자·같은 상태의 방문들이다
/// (설계 6.2 — 가족 한 번에). "완료하고 다음 예약 잡기"면 완료한 뒤 미리 받아
/// 둔 초안(없으면 [anchorVisitId]로 다시 읽는다)으로 예약 ② 화면을 채워 연다.
Future<void> sendVisitAction(
  BuildContext context,
  WidgetRef ref, {
  required int shopId,
  required VisitChoice choice,
  required List<int> ids,
  required int anchorVisitId,
}) async {
  final commands = ref.read(visitCommandsProvider);
  await commands.transition(
    shopId,
    visitIds: ids,
    action: choice.action,
    cancelReason: choice.cancelReason,
  );
  switch (choice.after) {
    case AfterNothing():
      return;
    case AfterNextReservation(:final draft):
      final next = draft ?? await commands.nextDraft(shopId, anchorVisitId);
      // 기다리지 않는다 — 예약 화면이 닫힐 때까지 부른 화면이 "보내는 중"에 묶이지 않게.
      if (context.mounted) context.push('/visits/new', extra: next);
  }
}
