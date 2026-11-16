import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/error_messages.dart';
import '../../../../design/tokens/app_colors.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_card.dart';
import '../../../../design/widgets/app_error_retry.dart';
import '../../../../design/widgets/pressable.dart';
import '../../../../l10n/app_strings.dart';
import '../../api/report_models.dart';
import '../../state/report_commands.dart';
import '../../state/report_providers.dart';

/// 알림장 설정의 `가족과 함께 보기 — 고객 한 명당 N명까지`(⑫ 설계 8절 — 매장이 정한다, 0~10, 기본 3).
///
/// 알림장 설정과 따로 읽고 따로 쓴다(값은 서버의 보호자 쪽에 있다). 읽지 못하면 이 구역만 한 줄 다시 시도다.
/// [−]·[+]는 누르면 바로 한 칸씩 보내고 다시 읽은 값으로 그린다 — 보내는 중·다시 읽는 중에는 누름을 받지
/// 않는다(빠르게 두 번 눌러 두 번 보내지 않게). 사장만 바꾼다.
class ReportFamilySection extends ConsumerStatefulWidget {
  const ReportFamilySection({
    super.key,
    required this.shopId,
    required this.canEdit,
  });

  final int shopId;
  final bool canEdit;

  @override
  ConsumerState<ReportFamilySection> createState() =>
      _ReportFamilySectionState();
}

class _ReportFamilySectionState extends ConsumerState<ReportFamilySection> {
  bool _busy = false;
  String? _error;

  Future<void> _set(int familyMax) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    String? error;
    try {
      await ref
          .read(reportCommandsProvider)
          .updateGuardianSettings(widget.shopId, familyMax: familyMax);
    } catch (e) {
      error = messageFor(e);
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _error = error;
    });
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(guardianSettingsProvider(widget.shopId));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(AppStrings.familyLabel, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.sm),
        // 다시 읽기가 실패하면 앞서 읽은 값이 남아 있다 — 낡은 값을 보이지 않게 실패를 먼저 본다.
        if (settings.hasError && !settings.isLoading)
          AppErrorRetry.row(
            message: loadMessageFor(settings.error!),
            onRetry: () =>
                ref.invalidate(guardianSettingsProvider(widget.shopId)),
          )
        else if (settings.value case final value?)
          _body(value, locked: _busy || settings.isLoading || !widget.canEdit)
        else
          const SizedBox(height: 44),
      ],
    );
  }

  Widget _body(GuardianSettings value, {required bool locked}) {
    final count = value.familyMax;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  AppStrings.familyMaxLine(count),
                  style: AppTypography.body,
                ),
              ),
              Pressable(
                semanticLabel: AppStrings.familyLess,
                onTap: !locked && count > GuardianSettings.min
                    ? () => _set(count - 1)
                    : null,
                child: Icon(
                  Icons.remove,
                  color: !locked && count > GuardianSettings.min
                      ? AppColors.ink
                      : AppColors.line,
                ),
              ),
              Pressable(
                semanticLabel: AppStrings.familyMore,
                onTap: !locked && count < GuardianSettings.max
                    ? () => _set(count + 1)
                    : null,
                child: Icon(
                  Icons.add,
                  color: !locked && count < GuardianSettings.max
                      ? AppColors.ink
                      : AppColors.line,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          const Text(AppStrings.familyHint, style: AppTypography.caption),
          const SizedBox(height: AppSpacing.xs),
          Text(
            count == 0 ? AppStrings.familyNone : AppStrings.familyKeep,
            style: AppTypography.caption,
          ),
          if (_error != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(_error!, style: AppTypography.caption),
          ],
        ],
      ),
    );
  }
}
