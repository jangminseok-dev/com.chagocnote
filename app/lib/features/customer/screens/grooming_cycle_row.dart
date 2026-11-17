import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/time/grooming_cycle.dart';
import '../../../core/time/today_provider.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_stepper.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';

/// 반려동물 상세 정보 탭의 미용 주기 줄(⑬ 설계 3.1·3.2) — 주기와 그 출처, 다음 올 때(늘 "쯤"), 어림이면 무엇으로
/// 어림했는지, 안내한 날. 완료 방문이 없으면 `미용 주기 정하기` 한 줄. 누르면 시트에서 직접 정한다.
/// 계산은 서버(visit)가 한다 — 여기는 받은 값을 글로만 바꾼다.
class GroomingCycleRow extends ConsumerWidget {
  const GroomingCycleRow({super.key, required this.petId, required this.revisit});

  final int petId;
  final PetRevisit revisit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final r = revisit;
    final visited = r.lastVisitDate != null;
    final first = cycleSourceLine(
      source: r.cycleSource,
      weeks: r.cycleWeeks,
      lastIntervalWeeks: r.lastIntervalWeeks,
      visited: visited,
    );
    final today = ref.watch(todayProvider);
    final lines = [
      if (visited && r.estimated) estimateNote(r.cycleWeeks),
      if (visited)
        r.hasUpcoming
            ? AppStrings.cycleHasUpcoming
            : r.dueDate == null
            ? null
            : dueLine(r.dueDate!, estimated: r.estimated),
      if (r.nudgedOn != null) AppStrings.revisitNudgedOn(r.nudgedOn!, today),
    ].whereType<String>();
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Pressable(
        semanticLabel: '${AppStrings.cycleLabel} $first',
        onTap: () => showGroomingCycleSheet(context, petId: petId, revisit: r),
        child: SizedBox(
          width: double.infinity,
          child: AppCard(
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(AppStrings.cycleLabel, style: AppTypography.caption),
                      const SizedBox(height: AppSpacing.xs),
                      Text(first, style: AppTypography.body),
                      for (final line in lines)
                        Text(line, style: AppTypography.caption),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, size: 18),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// 아이의 미용 주기를 직접 정하는 시트(⑬ 설계 3.2) — 지금 값과 출처, `[−] N주 [+]`(1~52), 고르는 대로 바뀌는
/// `이렇게 정하면 다음은 …쯤이에요`, [저장], 직접 정한 값이면 [계산한 값으로 돌아가기]. 저장·되돌리기를 했으면 true.
/// 실패하면 시트 안에서 말하고 시트는 남는다. 반려동물 상세·완료 시트·다시 올 때 목록이 함께 연다.
Future<bool> showGroomingCycleSheet(
  BuildContext context, {
  required int petId,
  required PetRevisit revisit,
}) async =>
    await AppSheet.show<bool>(
      context,
      builder: (context) => _CycleSheet(petId: petId, revisit: revisit),
    ) ==
    true;

class _CycleSheet extends ConsumerStatefulWidget {
  const _CycleSheet({required this.petId, required this.revisit});

  final int petId;
  final PetRevisit revisit;

  @override
  ConsumerState<_CycleSheet> createState() => _CycleSheetState();
}

class _CycleSheetState extends ConsumerState<_CycleSheet> {
  late int _weeks = widget.revisit.cycleWeeks.clamp(1, 52);
  bool _busy = false;
  String? _errorText;

  Future<void> _run(Future<void> Function(int shopId) action) async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action(shopId);
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _errorText = messageFor(e);
        });
      }
      return;
    }
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.revisit;
    final commands = ref.read(customerCommandsProvider);
    final last = r.lastVisitDate;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(AppStrings.cycleLabel, style: AppTypography.bodyStrong),
        const SizedBox(height: AppSpacing.xs),
        Text(
          cycleSourceLine(
            source: r.cycleSource,
            weeks: r.cycleWeeks,
            lastIntervalWeeks: r.lastIntervalWeeks,
            visited: last != null,
          ),
          style: AppTypography.caption,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.lg),
        AppStepper(
          value: _weeks,
          min: 1,
          max: 52,
          label: AppStrings.weeksUnit,
          decreaseLabel: AppStrings.stepDown,
          increaseLabel: AppStrings.stepUp,
          onChanged: (v) => setState(() => _weeks = v),
        ),
        if (last != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(
            AppStrings.cycleSheetPreview(nextDueOf(last, _weeks)),
            style: AppTypography.caption,
            textAlign: TextAlign.center,
          ),
        ],
        if (_errorText != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.md),
            child: Text(
              _errorText!,
              key: const ValueKey('grooming-cycle-error'),
              style: AppTypography.caption,
              textAlign: TextAlign.center,
            ),
          ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.save,
          filled: true,
          busy: _busy,
          onPressed: _busy
              ? null
              : () => _run((shopId) => commands.setGroomingCycle(shopId, widget.petId, _weeks)),
        ),
        if (r.cycleSource == CycleSource.manual) ...[
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cycleReset,
            onPressed: _busy
                ? null
                : () => _run((shopId) => commands.clearGroomingCycle(shopId, widget.petId)),
          ),
        ],
      ],
    );
  }
}
