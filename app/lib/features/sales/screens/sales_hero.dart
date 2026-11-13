import 'package:flutter/material.dart';

import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_big_date.dart';
import '../../../l10n/app_strings.dart';
import '../api/sales_models.dart';
import '../state/sales_rules.dart';

/// 매출 탭의 머리 — 기간의 제목, 큰 숫자, 견준 문장, 목표(설계 ⑧ 3.2 의 2~4).
///
/// 비교는 초록·빨강 화살표가 아니라 문장이다. 숫자 하나가 주인공이다.
class SalesHero extends StatelessWidget {
  const SalesHero({super.key, required this.summary, required this.empty});

  final SalesSummary summary;

  /// 완료한 방문이 없는 기간 — 큰 숫자 대신 안내를 보인다.
  final bool empty;

  @override
  Widget build(BuildContext context) {
    final compare = compareSentence(summary);
    final yearAgo = yearAgoSentence(summary);
    final goal = goalSentence(summary);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _PeriodTitle(title: periodTitle(summary)),
        const SizedBox(height: AppSpacing.sm),
        if (empty) ...[
          const Text(AppStrings.salesEmptyTitle, style: AppTypography.titleKo),
          const SizedBox(height: AppSpacing.xs),
          const Text(AppStrings.salesEmptyText, style: AppTypography.caption),
        ] else ...[
          // 아주 큰 금액은 줄이 넘치지 않게 줄어든다.
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  won(summary.revenue),
                  key: const Key('sales-revenue'),
                  style: AppTypography.bigNumeral.copyWith(
                    fontSize: 56,
                    height: 1,
                    letterSpacing: -2.5,
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.only(left: AppSpacing.xs, bottom: 6),
                  child: Text(AppStrings.salesWonUnit, style: AppTypography.body),
                ),
              ],
            ),
          ),
          if (compare != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(compare, style: AppTypography.body),
          ],
          if (yearAgo != null) ...[
            const SizedBox(height: 2),
            Text(yearAgo, style: AppTypography.caption),
          ],
        ],
        if (goal != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(goal, style: AppTypography.caption),
          const SizedBox(height: AppSpacing.xs),
          _GoalLine(progress: goalProgress(summary)),
        ],
      ],
    );
  }
}

class _PeriodTitle extends StatelessWidget {
  const _PeriodTitle({required this.title});

  final PeriodTitle title;

  @override
  Widget build(BuildContext context) {
    final ko = title.ko;
    if (ko != null) return Text(ko, style: AppTypography.titleKo);
    final en = title.enText ?? AppBigDate.monthName(title.enMonth!);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(en, style: AppTypography.italicLabel.copyWith(fontSize: 24)),
        if (title.small != null)
          Padding(
            padding: const EdgeInsets.only(left: AppSpacing.xs),
            child: Text(title.small!, style: AppTypography.caption),
          ),
      ],
    );
  }
}

/// 목표까지의 진행 — 가는 선 하나.
class _GoalLine extends StatelessWidget {
  const _GoalLine({required this.progress});

  final double progress;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      key: const Key('sales-goal-line'),
      height: 2,
      child: Stack(
        children: [
          const Positioned.fill(child: ColoredBox(color: AppColors.line)),
          FractionallySizedBox(
            widthFactor: progress,
            child: const ColoredBox(color: AppColors.ink, child: SizedBox.expand()),
          ),
        ],
      ),
    );
  }
}
