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

/// 시트에서 고른 상태 전이. [cancelReason]은 취소일 때만, [thenNext]는
/// "완료하고 다음 예약 잡기"일 때 true, [draft]는 그때 미리 받아 둔 초안.
class VisitChoice {
  const VisitChoice(
    this.action, {
    this.cancelReason,
    this.thenNext = false,
    this.draft,
  });

  final String action;
  final String? cancelReason;
  final bool thenNext;
  final NextVisitDraft? draft;
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
  required String action,
  required int anchorVisitId,
}) async {
  switch (action) {
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
      return next == null
          ? null
          : VisitChoice(VisitAction.complete, thenNext: next, draft: draft);
    default:
      return VisitChoice(action);
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
  if (!choice.thenNext) return;
  final draft = choice.draft ?? await commands.nextDraft(shopId, anchorVisitId);
  // 기다리지 않는다 — 예약 화면이 닫힐 때까지 부른 화면이 "보내는 중"에 묶이지 않게.
  if (context.mounted) context.push('/visits/new', extra: draft);
}
