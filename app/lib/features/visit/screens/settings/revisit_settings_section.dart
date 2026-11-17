import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/error/error_messages.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_card.dart';
import '../../../../design/widgets/app_error_retry.dart';
import '../../../../design/widgets/app_snack_bar.dart';
import '../../../../design/widgets/app_switch.dart';
import '../../../../design/widgets/pressable.dart';
import '../../../../l10n/app_strings.dart';
import '../../../auth/state/shop_selection.dart';
import '../../api/revisit_models.dart';
import '../../state/revisit_rules.dart';
import '../../state/visit_commands.dart';
import '../../state/visit_providers.dart';
import 'revisit_sheets.dart';

/// 예약 설정의 다시 올 때(⑬ 설계 3.7) — 줄 여섯. 줄 이름만 읽고 무슨 일이 생기는지 알게, 아래에 지금 값으로 생기는 일.
///
/// 값은 `revisit-settings`(따로 읽고 따로 쓴다). 숫자는 시트에서 고른 값을, 스위치는 누르면 바로 그 칸 하나만 보낸다.
/// 낙관적으로 그리지 않고 다시 읽은 서버 값으로 그린다. 보내는 중에는 누름을 받지 않는다. 예약 설정 화면이 사장만이라
/// 이 구역도 사장만 본다.
class RevisitSettingsSection extends ConsumerStatefulWidget {
  const RevisitSettingsSection({super.key, required this.shopId});

  final int shopId;

  @override
  ConsumerState<RevisitSettingsSection> createState() => _RevisitSettingsSectionState();
}

class _RevisitSettingsSectionState extends ConsumerState<RevisitSettingsSection> {
  bool _busy = false;

  Future<void> _send(Map<String, Object?> changes) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await ref.read(visitCommandsProvider).updateRevisitSettings(widget.shopId, changes);
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pick(
    String field,
    Future<int?> Function() pick,
    int current,
  ) async {
    if (_busy) return;
    final value = await pick();
    if (value == null || value == current || !mounted) return;
    await _send({field: value});
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(revisitSettingsProvider(widget.shopId));
    final counts = ref.watch(revisitCountsProvider(widget.shopId)).value;
    final s = settings.value;
    if (s == null) {
      return settings.hasError
          ? AppErrorRetry.row(
              message: loadMessageFor(settings.error!),
              onRetry: () => ref.invalidate(revisitSettingsProvider(widget.shopId)),
            )
          : const SizedBox.shrink();
    }
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(AppStrings.revisitSectionTitle, style: AppTypography.caption),
          const SizedBox(height: AppSpacing.sm),
          _Row(
            label: AppStrings.revisitDefaultWeeksLabel,
            value: AppStrings.weeksUnit(s.defaultCycleWeeks),
            note: AppStrings.revisitDefaultWeeksNote(s.defaultCycleWeeks),
            onTap: () => _pick(
              'default_cycle_weeks',
              () => pickDefaultCycleWeeks(context, s.defaultCycleWeeks),
              s.defaultCycleWeeks,
            ),
          ),
          _Row(
            label: AppStrings.revisitSoonDaysLabel,
            value: AppStrings.daysUnit(s.revisitSoonDays),
            note: counts == null ? null : AppStrings.revisitSoonCountNote(counts.soon),
            onTap: () => _pick(
              'revisit_soon_days',
              () => pickSoonDays(context, s.revisitSoonDays),
              s.revisitSoonDays,
            ),
          ),
          _Row(
            label: AppStrings.revisitMessageLabel,
            note: _preview(s),
            onTap: () => context.push('/settings/revisit-message'),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Row(
              children: [
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(AppStrings.revisitCountUnsentLabel, style: AppTypography.body),
                      SizedBox(height: AppSpacing.xs),
                      Text(AppStrings.revisitCountUnsentNote, style: AppTypography.caption),
                    ],
                  ),
                ),
                AppSwitch(
                  value: s.countUnsentReports,
                  semanticLabel: AppStrings.revisitCountUnsentLabel,
                  onChanged: _busy ? null : (on) => _send({'count_unsent_reports': on}),
                ),
              ],
            ),
          ),
          _Row(
            label: AppStrings.revisitSampleVisitsLabel,
            value: AppStrings.visitsUnit(s.cycleSampleVisits),
            note: AppStrings.revisitSampleVisitsNote(s.cycleSampleVisits),
            onTap: () => _pick(
              'cycle_sample_visits',
              () => pickRevisitNumber(
                context,
                title: AppStrings.revisitSampleVisitsLabel,
                initial: s.cycleSampleVisits,
                min: 3,
                max: 12,
                unit: AppStrings.visitsUnit,
                note: AppStrings.revisitSampleVisitsNote,
              ),
              s.cycleSampleVisits,
            ),
          ),
          _Row(
            label: AppStrings.revisitMinGapLabel,
            value: AppStrings.daysUnit(s.cycleMinGapDays),
            note: AppStrings.revisitMinGapNote(s.cycleMinGapDays),
            onTap: () => _pick(
              'cycle_min_gap_days',
              () => pickRevisitNumber(
                context,
                title: AppStrings.revisitMinGapLabel,
                initial: s.cycleMinGapDays,
                min: 0,
                max: 28,
                unit: AppStrings.daysUnit,
                note: AppStrings.revisitMinGapNote,
              ),
              s.cycleMinGapDays,
            ),
          ),
        ],
      ),
    );
  }

  /// 보호자가 받는 모습의 첫 줄 — 예시 아이 이름과 매장의 기본 간격으로 채운다.
  String _preview(RevisitSettings s) => fillRevisitMessage(
    s.message,
    shop: ref.watch(shopNameProvider),
    pet: AppStrings.revisitSamplePet,
    weeks: s.defaultCycleWeeks,
  ).split('\n').first;
}

class _Row extends StatelessWidget {
  const _Row({required this.label, this.value, this.note, required this.onTap});

  final String label;
  final String? value;
  final String? note;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: label,
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: AppTypography.body),
                  if (note != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(note!, style: AppTypography.caption, maxLines: 2, overflow: TextOverflow.ellipsis),
                  ],
                ],
              ),
            ),
            if (value != null) ...[
              const SizedBox(width: AppSpacing.sm),
              Text(value!, style: AppTypography.bodyStrong),
            ],
            const Icon(Icons.chevron_right, size: 18),
          ],
        ),
      ),
    );
  }
}
