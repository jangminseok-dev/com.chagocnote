import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/time/grooming_cycle.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/api/customer_models.dart';
import '../../customer/screens/grooming_cycle_row.dart';
import '../../customer/state/customer_providers.dart';
import '../api/visit_models.dart';
import '../state/visit_commands.dart';
import 'settings/revisit_sheets.dart';
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

  /// 완료한 뒤의 시트(설계 10.1 ④, ⑬ 3.4) — [다음 예약 잡기]면 그때의 초안을 담아 닫고(초안을 못 읽었으면
  /// 초안 없이), 닫으면 null. [draft]가 있으면 다음 예약이 언제로, 어떤 간격으로 잡히는지 보이고 그 자리에서
  /// 간격을 바꾼다 — 바꾸면 초안을 다시 읽는다.
  static Future<NextReservationChoice?> nextReservation(
    BuildContext context, {
    required int shopId,
    required int anchorVisitId,
    NextVisitDraft? draft,
  }) => AppSheet.show<NextReservationChoice>(
    context,
    builder: (context) => _NextReservationSheet(
      shopId: shopId,
      anchorVisitId: anchorVisitId,
      initial: draft,
    ),
  );
}

/// 완료 시트에서 [다음 예약 잡기]를 눌렀다 — [draft] 는 그때 보이던 초안(못 읽었으면 null).
class NextReservationChoice {
  const NextReservationChoice(this.draft);

  final NextVisitDraft? draft;
}

class _NextReservationSheet extends ConsumerStatefulWidget {
  const _NextReservationSheet({
    required this.shopId,
    required this.anchorVisitId,
    required this.initial,
  });

  final int shopId;
  final int anchorVisitId;
  final NextVisitDraft? initial;

  @override
  ConsumerState<_NextReservationSheet> createState() => _NextReservationSheetState();
}

class _NextReservationSheetState extends ConsumerState<_NextReservationSheet> {
  late NextVisitDraft? _draft = widget.initial;
  bool _busy = false;

  /// 간격을 바꾼 뒤 초안을 다시 읽는다. 못 읽으면 알리고 보던 줄을 둔다.
  Future<void> _reload() async {
    try {
      final next = await ref
          .read(visitCommandsProvider)
          .nextDraft(widget.shopId, widget.anchorVisitId);
      if (mounted) setState(() => _draft = next);
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    }
  }

  Future<void> _guard(Future<void> Function() action) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// 그 방문 아이의 주기 시트(가족이면 첫 아이 — 아이 ID 순). 저장했으면 초안을 다시 읽는다.
  Future<void> _changePetInterval(int petId) => _guard(() async {
    final PetDetail pet;
    try {
      pet = await ref.read(petDetailProvider((shopId: widget.shopId, petId: petId)).future);
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
      return;
    }
    final revisit = pet.revisit;
    if (revisit == null || !mounted) return;
    final saved = await showGroomingCycleSheet(context, petId: petId, revisit: revisit);
    if (saved) await _reload();
  });

  /// 매장의 기본 간격(사장만) — 어림한 초안의 날짜가 이 값으로 정해진다.
  Future<void> _changeDefaultInterval(int current) => _guard(() async {
    final weeks = await pickDefaultCycleWeeks(context, current);
    if (weeks == null || weeks == current || !mounted) return;
    try {
      await ref
          .read(visitCommandsProvider)
          .updateRevisitSettings(widget.shopId, {'default_cycle_weeks': weeks});
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
      return;
    }
    await _reload();
  });

  @override
  Widget build(BuildContext context) {
    final draft = _draft;
    final isOwner = ref.watch(isOwnerProvider);
    final petIds = [...?draft?.petIds]..sort();
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(AppStrings.completeTitle, style: AppTypography.titleKo),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.actionNextReservation,
          filled: true,
          icon: Icons.arrow_forward,
          onPressed: _busy
              ? null
              : () => Navigator.of(context).pop(NextReservationChoice(draft)),
        ),
        if (draft != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            AppStrings.nextDraftLine(
              draft.cycleWeeks,
              '${dayLabel(draft.startsAt.wall)} ${hhmm(draft.startsAt.wall)}',
              draftSourceLabel(draft.cycleSource),
            ),
            style: AppTypography.bodyStrong,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.xs),
          const Text(
            AppStrings.nextDraftCaption,
            style: AppTypography.caption,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.xs),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: AppSpacing.md,
            children: [
              if (petIds.isNotEmpty)
                _Link(
                  label: AppStrings.changeInterval,
                  onTap: _busy ? null : () => _changePetInterval(petIds.first),
                ),
              if (draft.cycleSource.estimated && isOwner)
                _Link(
                  label: AppStrings.changeDefaultInterval,
                  onTap: _busy ? null : () => _changeDefaultInterval(draft.cycleWeeks),
                ),
            ],
          ),
        ],
        const SizedBox(height: AppSpacing.sm),
        AppButton(
          label: AppStrings.close,
          onPressed: () => Navigator.of(context).pop(),
        ),
      ],
    );
  }
}

/// 글자뿐인 누를 것 — 누름 영역은 44 다(Pressable).
class _Link extends StatelessWidget {
  const _Link({required this.label, required this.onTap});

  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Pressable(
    semanticLabel: label,
    onTap: onTap,
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Text(
        label,
        style: AppTypography.caption.copyWith(decoration: TextDecoration.underline),
      ),
    ),
  );
}

/// 시트에서 고른 상태 전이. [cancelReason]은 취소일 때만.
class VisitChoice {
  const VisitChoice(this.action, {this.cancelReason});

  final VisitAction action;
  final String? cancelReason;
}

/// 전이에 필요한 것을 시트로 묻는다(취소 사유, 노쇼 확인). 묻지 않는 전이(시작·되돌리기)는 그대로
/// 돌려준다. 시트를 닫으면 null — 아무것도 보내지 않는다.
///
/// 완료는 묻는 대신 완료 흐름을 끝까지 돌리고 null 을 돌려준다(보낼 것이 남지 않는다) —
/// [completeVisit]. 묶음은 [anchorVisitId]의 기록 화면이 함께 완료한다.
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
      await completeVisit(
        context,
        ref,
        shopId: shopId,
        anchorVisitId: anchorVisitId,
      );
      return null;
  }
}

/// 완료 흐름(설계 10.1 ④) — 기록 화면을 완료 모드로 열고, 완료했으면 다음 예약 시트를 띄운다.
/// [다음 예약 잡기]면 초안으로 예약 ② 화면을 채워 연다. 초안을 못 읽어도 시트는 뜬다 —
/// 미리보기는 돕는 것이고, 누르면 다시 읽는다.
Future<void> completeVisit(
  BuildContext context,
  WidgetRef ref, {
  required int shopId,
  required int anchorVisitId,
}) async {
  final completed = await context.push<bool>(
    '/visits/$anchorVisitId/record?complete=1',
  );
  if (completed != true || !context.mounted) return;
  final commands = ref.read(visitCommandsProvider);
  NextVisitDraft? draft;
  try {
    draft = await commands.nextDraft(shopId, anchorVisitId);
  } catch (_) {
    // 미리보기를 못 받아도 시트는 뜬다.
  }
  if (!context.mounted) return;
  final next = await VisitSheets.nextReservation(
    context,
    shopId: shopId,
    anchorVisitId: anchorVisitId,
    draft: draft,
  );
  if (next == null || !context.mounted) return;
  NextVisitDraft chosen;
  try {
    // 시트에서 간격을 바꿨으면 그 초안이다 — 다시 읽지 않는다.
    chosen = next.draft ?? await commands.nextDraft(shopId, anchorVisitId);
  } catch (e) {
    // 미리보기도 실패했던 초안을 다시 읽다 또 실패하면 문구로 알린다 — 예약 화면은 열지 않는다.
    if (context.mounted) AppSnackBar.show(context, messageFor(e));
    return;
  }
  // 기다리지 않는다 — 예약 화면이 닫힐 때까지 부른 화면이 묶이지 않게.
  if (context.mounted) context.push('/visits/new', extra: chosen);
}

/// 고른 전이를 묶음 한 번에 보낸다. [ids]는 같은 보호자·같은 상태의 방문들이다
/// (설계 6.2 — 가족 한 번에).
Future<void> sendVisitAction(
  WidgetRef ref, {
  required int shopId,
  required VisitChoice choice,
  required List<int> ids,
}) => ref
    .read(visitCommandsProvider)
    .transition(
      shopId,
      visitIds: ids,
      action: choice.action,
      cancelReason: choice.cancelReason,
    );
