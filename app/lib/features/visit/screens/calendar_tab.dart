import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_big_date.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_dashed_tile.dart';
import '../../../design/widgets/app_glass_card.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../home/state/today_provider.dart';
import '../api/visit_models.dart';
import '../state/calendar_selection.dart';
import '../state/day_layout.dart';
import '../state/visit_providers.dart';
import 'visit_labels.dart';

/// 홈의 "캘린더" 탭 — 큰 세리프 월·연도와 이동 화살표, 월 달력, 위쪽 "정리 안 된
/// 예약 N건" 줄, 고른 날의 미리보기 글래스 카드(설계 9.1).
///
/// 사진이 생기기 전(④ 전)에는 지난날 칸을 회색 사진 자리 + 마릿수로, 앞날의
/// 예약은 점선 칸 + 예약 수로, 휴무일은 옅은 "휴무"로 보인다.
class CalendarTab extends ConsumerStatefulWidget {
  const CalendarTab({super.key});

  @override
  ConsumerState<CalendarTab> createState() => _CalendarTabState();
}

class _CalendarTabState extends ConsumerState<CalendarTab> {
  /// 보고 있는 달(1일) — 늘 고른 날의 달이다. 다른 화면(예약 저장)이 고른 날을
  /// 다른 달로 옮기면 달력도 따라간다.
  DateTime get _month {
    final selected = ref.watch(selectedDateProvider);
    return DateTime(selected.year, selected.month);
  }

  /// 달을 옮기면 그달에 오늘이 있으면 오늘을, 없으면 1일을 고른다.
  void _moveMonth(int delta) {
    final current = ref.read(selectedDateProvider);
    final month = DateTime(current.year, current.month + delta);
    final today = ref.read(todayProvider);
    ref
        .read(selectedDateProvider.notifier)
        .select(
          today.year == month.year && today.month == month.month
              ? today
              : month,
        );
  }

  void _openDay(DateTime date) => context.push('/visits/day/${isoDay(date)}');

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider);
    final selected = ref.watch(selectedDateProvider);
    if (shopId == null) return const SizedBox.shrink();
    final monthKey = monthKeyOf(shopId, _month);
    final summary = ref.watch(calendarMonthProvider(monthKey));
    final data = summary.value;

    return Stack(
      children: [
        ListView(
          // 아래 여백은 미리보기 카드와 떠 있는 탭바 몫이다.
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            280,
          ),
          children: [
            _MonthHeader(
              month: _month,
              onPrev: () => _moveMonth(-1),
              onNext: () => _moveMonth(1),
            ),
            if (data != null && data.unresolvedTotal > 0)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.md),
                child: Pressable(
                  semanticLabel: AppStrings.unresolvedBanner(
                    data.unresolvedTotal,
                  ),
                  onTap: data.oldestUnresolvedDate == null
                      ? null
                      : () => _openDay(data.oldestUnresolvedDate!),
                  child: AppCard(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.md,
                      vertical: AppSpacing.sm,
                    ),
                    child: Row(
                      children: [
                        Text(
                          AppStrings.unresolvedBanner(data.unresolvedTotal),
                          style: AppTypography.bodyStrong,
                        ),
                        const Spacer(),
                        const Icon(Icons.chevron_right, size: 18),
                      ],
                    ),
                  ),
                ),
              ),
            const SizedBox(height: AppSpacing.md),
            const _WeekHeader(),
            const SizedBox(height: AppSpacing.xs),
            if (summary.hasError && data == null)
              Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  children: [
                    Text(messageFor(summary.error!), style: AppTypography.body),
                    const SizedBox(height: AppSpacing.md),
                    AppButton(
                      label: AppStrings.retry,
                      onPressed: () =>
                          ref.invalidate(calendarMonthProvider(monthKey)),
                    ),
                  ],
                ),
              )
            else
              _MonthGrid(
                month: _month,
                summary: data,
                today: ref.watch(todayProvider),
                selected: selected,
                onSelect: (date) =>
                    ref.read(selectedDateProvider.notifier).select(date),
              ),
          ],
        ),
        // 오른쪽은 떠 있는 + 버튼 자리다.
        Positioned(
          left: AppSpacing.md,
          right: 76,
          bottom: 96,
          child: _DayPreview(
            shopId: shopId,
            date: selected,
            onOpen: () => _openDay(selected),
          ),
        ),
      ],
    );
  }
}

/// "09 September 2026 ‹ ›" 와 설정 버튼.
class _MonthHeader extends StatelessWidget {
  const _MonthHeader({
    required this.month,
    required this.onPrev,
    required this.onNext,
  });

  final DateTime month;
  final VoidCallback onPrev;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final monthName = AppBigDate.monthName(month.month);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(
          month.month.toString().padLeft(2, '0'),
          style: AppTypography.bigNumeral,
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${month.year}', style: AppTypography.caption),
                Text(
                  monthName,
                  style: AppTypography.italicLabel.copyWith(fontSize: 24),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ),
        Pressable(
          semanticLabel: AppStrings.prevMonth,
          onTap: onPrev,
          child: const Icon(Icons.chevron_left),
        ),
        Pressable(
          semanticLabel: AppStrings.nextMonth,
          onTap: onNext,
          child: const Icon(Icons.chevron_right),
        ),
        Pressable(
          semanticLabel: AppStrings.settingsLabel,
          onTap: () => context.push('/settings'),
          child: const Icon(Icons.settings_outlined),
        ),
      ],
    );
  }
}

class _WeekHeader extends StatelessWidget {
  const _WeekHeader();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (final d in AppStrings.calendarWeekHeader)
          Expanded(
            child: Text(
              d,
              textAlign: TextAlign.center,
              style: AppTypography.caption,
            ),
          ),
      ],
    );
  }
}

/// 일요일부터 시작하는 월 달력(기준 목업).
class _MonthGrid extends StatelessWidget {
  const _MonthGrid({
    required this.month,
    required this.summary,
    required this.today,
    required this.selected,
    required this.onSelect,
  });

  final DateTime month;
  final CalendarMonth? summary;
  final DateTime today;
  final DateTime selected;
  final ValueChanged<DateTime> onSelect;

  @override
  Widget build(BuildContext context) {
    final lead = DateTime(month.year, month.month, 1).weekday % 7;
    final days = DateTime(month.year, month.month + 1, 0).day;
    final cells = lead + days;
    final rows = (cells / 7).ceil();
    final todayDate = DateTime(today.year, today.month, today.day);
    return Column(
      children: [
        for (var r = 0; r < rows; r++)
          Row(
            children: [
              for (var c = 0; c < 7; c++)
                Expanded(
                  child: () {
                    final day = r * 7 + c - lead + 1;
                    if (day < 1 || day > days) {
                      return const SizedBox(height: 56);
                    }
                    final date = DateTime(month.year, month.month, day);
                    return _DayCell(
                      date: date,
                      summary: summary?.dayOf(date),
                      isToday: date == todayDate,
                      isPast: date.isBefore(todayDate),
                      isSelected: date == selected,
                      onTap: () => onSelect(date),
                    );
                  }(),
                ),
            ],
          ),
      ],
    );
  }
}

class _DayCell extends StatelessWidget {
  const _DayCell({
    required this.date,
    required this.summary,
    required this.isToday,
    required this.isPast,
    required this.isSelected,
    required this.onTap,
  });

  final DateTime date;
  final CalendarDay? summary;
  final bool isToday;
  final bool isPast;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final s = summary;
    final count = s?.visitCount ?? 0;
    final Widget body;
    if (count > 0 && (isPast || isToday)) {
      body = AppPhotoTile(image: null, count: count, size: 34);
    } else if (count > 0) {
      body = AppDashedTile(count: count, size: 34);
    } else if (s?.closedDay ?? false) {
      body = Text(
        AppStrings.closedShort,
        style: AppTypography.caption.copyWith(
          color: AppColors.line,
          fontSize: 9,
        ),
      );
    } else {
      body = const SizedBox.shrink();
    }
    return Pressable(
      semanticLabel: dayLabel(date),
      selected: isSelected,
      onTap: onTap,
      child: Container(
        height: 56,
        margin: const EdgeInsets.all(1),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: Border.all(
            color: isSelected ? AppColors.ink : const Color(0x00000000),
          ),
        ),
        child: ExcludeSemantics(
          child: Stack(
            children: [
              Positioned(left: 4, top: 2, child: _DayNumber(date, isToday)),
              // 정리 안 된 예약 수(설계 6.4 "날마다 수를").
              if ((s?.unresolvedCount ?? 0) > 0)
                Positioned(
                  right: 3,
                  top: 1,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      color: AppColors.ink,
                      borderRadius: BorderRadius.circular(AppRadius.pill),
                    ),
                    child: Text(
                      '${s!.unresolvedCount}',
                      style: AppTypography.caption.copyWith(
                        fontSize: 8,
                        height: 1.4,
                        color: AppColors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              Positioned(
                left: 0,
                right: 0,
                top: 17,
                bottom: 2,
                child: Center(child: body),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DayNumber extends StatelessWidget {
  const _DayNumber(this.date, this.isToday);

  final DateTime date;
  final bool isToday;

  @override
  Widget build(BuildContext context) {
    final text = Text(
      '${date.day}',
      style: AppTypography.caption.copyWith(
        fontSize: 10,
        color: isToday ? AppColors.white : AppColors.ink,
        fontWeight: isToday ? FontWeight.w700 : FontWeight.w500,
      ),
    );
    if (!isToday) return text;
    return Container(
      width: 16,
      height: 16,
      alignment: Alignment.center,
      decoration: const BoxDecoration(
        color: AppColors.ink,
        shape: BoxShape.circle,
      ),
      child: text,
    );
  }
}

/// 고른 날의 미리보기 — 떠 있는 글래스 카드. 누르면 하루 화면.
class _DayPreview extends ConsumerWidget {
  const _DayPreview({
    required this.shopId,
    required this.date,
    required this.onOpen,
  });

  final int shopId;
  final DateTime date;
  final VoidCallback onOpen;

  static const _maxRows = 4;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final day = ref.watch(dayVisitsProvider((shopId: shopId, date: date)));
    final data = day.value;
    final groups = data == null ? const <DayGroup>[] : groupDay(data.items);
    return Pressable(
      semanticLabel: AppStrings.dayHeading(date.day, date.weekday),
      onTap: onOpen,
      child: AppGlassCard(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.md,
          AppSpacing.lg,
          AppSpacing.md,
        ),
        child: ExcludeSemantics(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Text(
                    AppStrings.dayHeading(date.day, date.weekday),
                    style: AppTypography.bodyStrong,
                  ),
                  const Spacer(),
                  if (data != null)
                    Text(
                      AppStrings.previewCounts(
                        data.counts.visitCount,
                        data.counts.completed,
                      ),
                      style: AppTypography.caption,
                    ),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              if (day.hasError)
                Text(messageFor(day.error!), style: AppTypography.caption)
              else if (data != null && groups.isEmpty)
                Text(
                  data.closedDay
                      ? AppStrings.closedDayNote
                      : AppStrings.dayEmpty,
                  style: AppTypography.caption,
                )
              else
                for (final g in groups.take(_maxRows))
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 44,
                          child: Text(
                            hhmm(g.startsAt.wall),
                            style: AppTypography.caption,
                          ),
                        ),
                        Expanded(
                          child: Text(
                            visitsTitle(g.visits),
                            style: AppTypography.body,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Text(
                          [
                            statusLabel(g.uniformStatus ?? g.first.status),
                            if (g.overlapping) AppStrings.markOverlap,
                          ].join(' · '),
                          style: AppTypography.caption,
                        ),
                      ],
                    ),
                  ),
              if (groups.length > _maxRows)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(
                    AppStrings.moreGroups(groups.length - _maxRows),
                    style: AppTypography.caption,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
