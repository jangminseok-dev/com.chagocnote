import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_shadows.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_big_date.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../design/widgets/app_fab.dart';
import '../../../design/widgets/app_icon_toggle.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/visit_models.dart';
import '../state/day_layout.dart';
import '../state/day_view_mode.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'visit_actions.dart';
import 'visit_labels.dart';

/// 하루 화면 — 큰 날짜, 상태별 수, [목록 / 시간표] 전환(마지막 선택을 기기에
/// 기억), 가족 묶음 카드(설계 9.1). 목록 카드의 버튼은 묶음 전체를 한 번에
/// 바꾼다 — 예약됨이면 [시작], 미용 중이면 [완료하기].
class DayScreen extends ConsumerStatefulWidget {
  const DayScreen({super.key, required this.date});

  final DateTime date;

  @override
  ConsumerState<DayScreen> createState() => _DayScreenState();
}

class _DayScreenState extends ConsumerState<DayScreen> {
  /// 보내는 중인 묶음의 첫 방문 ID(휴무 표시 중이면 -1). 그동안 다른 버튼을 막는다.
  int? _busyVisitId;
  // 완료 흐름(기록 화면 → 다음 예약 시트)이나 다른 시트가 떠 있는 동안의
  // 재진입을 막는다. "보내는 중"이 아니므로 버튼에 스피너를 켜지 않는다 —
  // `_busyVisitId`와는 다른 신호다.
  bool _asking = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  Future<void> _act(DayGroup group, VisitAction action) async {
    final shopId = _shopId;
    if (shopId == null || _busyVisitId != null || _asking) return;
    // 상태가 섞인 묶음이면 아직 진행 가능한 아이들만(완료 흐름의 기록 화면도 그 아이 기준).
    final ids = group.actionableIds;
    final anchorVisitId = ids.isEmpty ? group.first.visitId : ids.first;
    setState(() => _asking = true);
    VisitChoice? choice;
    try {
      choice = await askVisitAction(
        context,
        ref,
        shopId: shopId,
        action: action,
        anchorVisitId: anchorVisitId,
      );
    } finally {
      if (mounted) setState(() => _asking = false);
    }
    if (choice == null || !mounted) return;
    setState(() {
      _busyVisitId = group.first.visitId;
      _errorText = null;
    });
    try {
      await sendVisitAction(ref, shopId: shopId, choice: choice, ids: ids);
    } catch (e) {
      if (mounted) setState(() => _errorText = messageFor(e));
    }
    if (mounted) setState(() => _busyVisitId = null);
  }

  /// `···` — 이 날을 임시 휴무로 표시하거나 해제한다(사장만, 같은 API 를 쓰는
  /// 설정 화면보다 달력에서 바로 하는 편이 쉽다). 매주 쉬는 요일은 설정에서 푼다.
  Future<void> _openMore(DayVisits data) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final choice = await AppSheet.show<String>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Pressable(
            semanticLabel: data.closedDay
                ? AppStrings.unmarkClosedDate
                : AppStrings.markClosedDate,
            onTap: () => Navigator.of(context).pop('toggle'),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
              alignment: Alignment.center,
              child: ExcludeSemantics(
                child: Text(
                  data.closedDay
                      ? AppStrings.unmarkClosedDate
                      : AppStrings.markClosedDate,
                  style: AppTypography.body,
                ),
              ),
            ),
          ),
        ],
      ),
    );
    if (choice == null || !mounted) return;
    setState(() {
      _busyVisitId = -1;
      _errorText = null;
    });
    try {
      final commands = ref.read(visitCommandsProvider);
      if (data.closedDay) {
        await commands.deleteClosedDate(shopId, widget.date);
      } else {
        await commands.addClosedDate(shopId, widget.date);
      }
    } catch (e) {
      if (mounted) setState(() => _errorText = messageFor(e));
    }
    if (mounted) setState(() => _busyVisitId = null);
  }

  @override
  Widget build(BuildContext context) {
    // 매장이 바뀌면 다시 그려야 하므로 build 안에서는 watch 한다(_shopId
    // getter 는 read 라 액션 메서드 전용).
    final shopId = ref.watch(selectedShopIdProvider);
    final key = (shopId: shopId ?? 0, date: widget.date);
    final day = shopId == null
        ? const AsyncValue<DayVisits>.loading()
        : ref.watch(dayVisitsProvider(key));
    final mode = ref.watch(dayViewModeProvider).value ?? DayViewMode.list;
    final data = day.value;
    final isOwner = ref.watch(isOwnerProvider);
    return Scaffold(
      key: ScreenKeys.day,
      floatingActionButton: AppFab(
        semanticLabel: AppStrings.addReservation,
        onPressed: () =>
            context.push('/visits/new?date=${isoDay(widget.date)}'),
      ),
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    const Text(
                      AppStrings.dayTitleEn,
                      style: AppTypography.titleEn,
                    ),
                    const Spacer(),
                    if (isOwner)
                      Pressable(
                        semanticLabel: AppStrings.more,
                        onTap: data == null || _busyVisitId != null || _asking
                            ? null
                            : () => _openMore(data),
                        child: const Icon(Icons.more_horiz),
                      ),
                    AppIconToggle(
                      icons: const [Icons.view_list, Icons.view_timeline],
                      labels: const [
                        AppStrings.viewAsList,
                        AppStrings.viewAsTimeline,
                      ],
                      currentIndex: mode.index,
                      onChanged: (i) => ref
                          .read(dayViewModeProvider.notifier)
                          .select(DayViewMode.values[i]),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.md,
                  AppSpacing.lg,
                  AppSpacing.sm,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 목업: 큰 날짜 + 기울인 영문 요일, 그 아래 "2026년 9월".
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '${widget.date.day}',
                          style: AppTypography.bigNumeral,
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                          child: Text(
                            AppBigDate.weekdayName(widget.date.weekday),
                            style: AppTypography.italicLabel,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      AppStrings.yearMonth(widget.date.year, widget.date.month),
                      style: AppTypography.caption,
                    ),
                    if (data != null) ...[
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        [
                          if (data.closedDay) AppStrings.closedDayNote,
                          AppStrings.dayCountsText(
                            visits: data.counts.visitCount,
                            completed: data.counts.completed,
                            inProgress: data.counts.inProgress,
                            reserved: data.counts.reserved,
                            canceled: data.counts.canceled,
                            noShow: data.counts.noShow,
                          ),
                        ].join(' · '),
                        style: AppTypography.bodyStrong,
                      ),
                    ],
                    if (_errorText != null)
                      Text(_errorText!, style: AppTypography.caption),
                  ],
                ),
              ),
              Expanded(
                child: day.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => AppErrorRetry(
                    message: messageFor(error),
                    onRetry: () => ref.invalidate(dayVisitsProvider(key)),
                  ),
                  data: (data) {
                    final groups = groupDay(data.items);
                    if (groups.isEmpty) return const _Empty();
                    return mode == DayViewMode.list
                        ? _DayList(
                            groups: groups,
                            busyVisitId: _busyVisitId,
                            asking: _asking,
                            onAction: _act,
                          )
                        : _Timeline(shopId: shopId!, groups: groups);
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

void _openGroup(BuildContext context, DayGroup group) =>
    context.push('/visits/${group.first.visitId}');

class _Empty extends StatelessWidget {
  const _Empty();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(AppStrings.dayEmpty, style: AppTypography.body),
          SizedBox(height: AppSpacing.xs),
          Text(AppStrings.dayEmptyCaption, style: AppTypography.caption),
        ],
      ),
    );
  }
}

class _DayList extends StatelessWidget {
  const _DayList({
    required this.groups,
    required this.busyVisitId,
    required this.asking,
    required this.onAction,
  });

  final List<DayGroup> groups;
  final int? busyVisitId;

  /// 완료 시트를 띄우기 전 초안을 읽는 동안(설계 6.2) — 이때는 카드 버튼을
  /// 전부 막지만 스피너는 켜지 않는다.
  final bool asking;
  final void Function(DayGroup group, VisitAction action) onAction;

  @override
  Widget build(BuildContext context) {
    final gaps = gapsBefore(groups);
    // 아래 여백은 떠 있는 + 버튼 몫이다.
    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
      children: [
        for (var i = 0; i < groups.length; i++) ...[
          if (gaps[i] != null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Center(
                child: Text(
                  AppStrings.gapText(gaps[i]!),
                  style: AppTypography.caption,
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: _GroupCard(
              group: groups[i],
              busy: busyVisitId == groups[i].first.visitId,
              otherBusy:
                  (busyVisitId != null || asking) &&
                  busyVisitId != groups[i].first.visitId,
              onAction: (action) => onAction(groups[i], action),
            ),
          ),
        ],
      ],
    );
  }
}

/// 목록 카드 — 시간·끝 시각, 사진 자리(가족은 겹친 자리), 이름, 메뉴·보호자,
/// 겹침·정리 안 됨 표시, 상태 버튼.
class _GroupCard extends StatelessWidget {
  const _GroupCard({
    required this.group,
    required this.busy,
    required this.otherBusy,
    required this.onAction,
  });

  final DayGroup group;
  final bool busy;
  final bool otherBusy;
  final ValueChanged<VisitAction> onAction;

  @override
  Widget build(BuildContext context) {
    final first = group.first;
    final marks = [
      if (group.overlapping) AppStrings.markOverlap,
      if (group.unresolved) AppStrings.markUnresolved,
    ];
    final status = group.uniformStatus;
    // 상태가 섞였으면 아직 진행 가능한 아이들의 상태로 버튼을 정한다(A2 잔여).
    final mixed = status == null;
    final buttonStatus = mixed ? group.actionableStatus : status;
    VoidCallback? on(VisitAction action) =>
        busy || otherBusy ? null : () => onAction(action);
    final Widget trailing = switch (buttonStatus) {
      VisitStatus.reserved => AppButton(
        label: AppStrings.actionStart,
        filled: true,
        busy: busy,
        onPressed: on(VisitAction.start),
      ),
      VisitStatus.inProgress => AppButton(
        label: AppStrings.actionCompleteShort,
        filled: true,
        busy: busy,
        onPressed: on(VisitAction.complete),
      ),
      null ||
      VisitStatus.completed ||
      VisitStatus.canceled ||
      VisitStatus.noShow ||
      VisitStatus.unknown => AppChip(label: statusLabel(status ?? first.status)),
    };
    final caption = [
      menusLabel(first.menus),
      ownerLabel(first.customer),
      ...marks,
    ].join(' · ');
    return Opacity(
      opacity: group.occupiesTime ? 1 : 0.5,
      child: Pressable(
        semanticLabel: visitsTitle(group.visits),
        onTap: () => _openGroup(context, group),
        child: AppCard(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              SizedBox(
                width: 48,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(hhmm(first.startsAt.wall), style: AppTypography.body),
                    Text(
                      '~${hhmm(group.endsAt)}',
                      style: AppTypography.caption,
                    ),
                  ],
                ),
              ),
              _PhotoStack(count: group.items.length),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      visitsTitle(group.visits),
                      style: AppTypography.bodyStrong,
                    ),
                    Text(caption, style: AppTypography.caption),
                    if (mixed)
                      Text(
                        statusSummary(group.visits),
                        style: AppTypography.caption,
                      ),
                  ],
                ),
              ),
              trailing,
            ],
          ),
        ),
      ),
    );
  }
}

/// 사진 자리. 가족이면 두 장을 겹쳐 보인다(사진은 ④에서).
class _PhotoStack extends StatelessWidget {
  const _PhotoStack({required this.count});

  static const size = 38.0;

  final int count;

  @override
  Widget build(BuildContext context) {
    final shown = count > 1 ? 2 : 1;
    final offset = size * 0.3;
    return SizedBox(
      width: size + offset * (shown - 1),
      height: size,
      child: Stack(
        children: [
          for (var i = 0; i < shown; i++)
            Positioned(
              left: offset * i,
              child: AppPhotoTile(image: null, size: size),
            ),
        ],
      ),
    );
  }
}

/// 시간표 — 시간 줄 위에 묶음 블록. 겹치면 옆 칸으로 나눠 그린다. 취소·노쇼는
/// 빈 시간이라 그리지 않는다.
class _Timeline extends ConsumerWidget {
  const _Timeline({required this.shopId, required this.groups});

  final int shopId;
  final List<DayGroup> groups;

  static const _hourHeight = 64.0;
  static const _labelWidth = 44.0;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(visitSettingsProvider(shopId)).value;
    final active = [
      for (final g in groups)
        if (g.occupiesTime) g,
    ];
    final (first: firstHour, last: lastHour) = timelineHours(settings, active);
    final columns = timelineColumns(active);
    final columnCount = columns.isEmpty
        ? 1
        : columns.reduce((a, b) => a > b ? a : b) + 1;
    double top(DateTime t) =>
        ((t.hour - firstHour) * 60 + t.minute) / 60 * _hourHeight;

    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final width = (constraints.maxWidth - _labelWidth) / columnCount;
            return SizedBox(
              height: (lastHour - firstHour) * _hourHeight + AppSpacing.md,
              child: Stack(
                children: [
                  for (var h = firstHour; h <= lastHour; h++)
                    Positioned(
                      top: (h - firstHour) * _hourHeight,
                      left: 0,
                      right: 0,
                      child: Row(
                        children: [
                          SizedBox(
                            width: _labelWidth,
                            child: Text(
                              '${h.toString().padLeft(2, '0')}:00',
                              style: AppTypography.caption,
                            ),
                          ),
                          Expanded(
                            child: Container(height: 1, color: AppColors.line),
                          ),
                        ],
                      ),
                    ),
                  for (var i = 0; i < active.length; i++)
                    Positioned(
                      top: top(active[i].startsAt.wall),
                      height:
                          top(active[i].endsAt) - top(active[i].startsAt.wall),
                      left: _labelWidth + width * columns[i],
                      width: width,
                      child: _Block(group: active[i]),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _Block extends StatelessWidget {
  const _Block({required this.group});

  final DayGroup group;

  /// 이름 + 메뉴·보호자·상태 두 줄을 담는 데 필요한 최소 블록 높이.
  static const _twoLineMinHeight = 44.0;

  @override
  Widget build(BuildContext context) {
    final inProgress = group.uniformStatus == VisitStatus.inProgress;
    final completed = group.uniformStatus == VisitStatus.completed;
    return LayoutBuilder(
      builder: (context, constraints) {
        // 30분처럼 짧은 블록은 둘째 줄(메뉴·보호자·상태)을 담을 높이가 없다
        // — 그럴 때는 이름 한 줄만 그린다(넘침 방지).
        final showCaption = constraints.maxHeight >= _twoLineMinHeight;
        return Pressable(
          semanticLabel: visitsTitle(group.visits),
          onTap: () => _openGroup(context, group),
          child: Container(
            margin: const EdgeInsets.only(left: 2, bottom: 2),
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: AppSpacing.xs,
            ),
            clipBehavior: Clip.hardEdge,
            decoration: BoxDecoration(
              color: completed ? AppColors.backgroundTop : AppColors.white,
              borderRadius: BorderRadius.circular(AppRadius.sm),
              border: Border.all(
                color: inProgress ? AppColors.ink : AppColors.line,
                width: inProgress ? 1.5 : 1,
              ),
              boxShadow: completed ? null : AppShadows.soft,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // 둘째 줄이 없으면 메뉴를 이름 뒤에 같은 줄로 잇는다(A2 잔여).
                if (showCaption)
                  Text(
                    visitsTitle(group.visits),
                    style: AppTypography.bodyStrong,
                    overflow: TextOverflow.ellipsis,
                  )
                else
                  Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: visitsTitle(group.visits),
                          style: AppTypography.bodyStrong,
                        ),
                        TextSpan(
                          text: ' · ${menusLabel(group.first.menus)}',
                          style: AppTypography.caption,
                        ),
                      ],
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                if (showCaption)
                  Text(
                    [
                      menusLabel(group.first.menus),
                      ownerLabel(group.first.customer),
                      statusLabel(group.uniformStatus ?? group.first.status),
                      if (group.overlapping) AppStrings.markOverlap,
                    ].join(' · '),
                    style: AppTypography.caption,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}
