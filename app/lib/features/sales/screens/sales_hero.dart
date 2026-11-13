import 'package:flutter/material.dart';

import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_big_date.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/sales_models.dart';
import '../state/sales_rules.dart';
import 'sales_sections.dart';

/// 매출 탭의 머리 — 기간의 제목, 큰 숫자, 견준 문장, 목표(설계 ⑧ 3.2 의 2~4).
///
/// 비교는 초록·빨강 화살표가 아니라 문장이다. 숫자 하나가 주인공이다.
class SalesHero extends StatelessWidget {
  const SalesHero({
    super.key,
    required this.summary,
    required this.empty,
    required this.today,
    this.onGoal,
  });

  final SalesSummary summary;

  /// 기기의 오늘 — 오늘의 일 보기는 "어제보다"로 말한다.
  final DateTime today;

  /// 목표 줄(없으면 [이번 달 목표 정하기])을 눌렀을 때. 이번 달의 월 보기에서만 준다 — null 이면 줄이 눌리지 않고
  /// 정하기도 없다.
  final VoidCallback? onGoal;

  /// 완료한 방문이 없는 기간 — 큰 숫자 대신 안내를 보인다.
  final bool empty;

  @override
  Widget build(BuildContext context) {
    final compare = compareSentence(summary, today: today);
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
                  child: Text(
                    AppStrings.salesWonUnit,
                    style: AppTypography.body,
                  ),
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
          Pressable(
            key: const Key('sales-goal'),
            minSize: 0,
            semanticLabel: goal,
            onTap: onGoal,
            child: ExcludeSemantics(
              // 줄은 가늘어도 누름 영역의 높이는 44 다.
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 44),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(goal, style: AppTypography.caption),
                        ),
                        if (onGoal != null)
                          const Icon(
                            Icons.chevron_right,
                            size: 14,
                            color: AppColors.secondary,
                          ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    _GoalLine(progress: goalProgress(summary)),
                  ],
                ),
              ),
            ),
          ),
        ] else if (onGoal != null) ...[
          Pressable(
            key: const Key('sales-goal'),
            minSize: 0,
            onTap: onGoal,
            child: SalesTapArea(
              child: Text(AppStrings.salesSetGoal, style: salesLinkStyle),
            ),
          ),
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
    // 폭을 채워야 회색 바탕선이 끝까지 간다 — 채우지 않으면 진행한 만큼만 있는 밑줄로 보인다.
    return SizedBox(
      key: const Key('sales-goal-line'),
      width: double.infinity,
      height: 2,
      child: Stack(
        children: [
          const Positioned.fill(child: ColoredBox(color: AppColors.line)),
          FractionallySizedBox(
            widthFactor: progress,
            child: const ColoredBox(
              color: AppColors.ink,
              child: SizedBox.expand(),
            ),
          ),
        ],
      ),
    );
  }
}
