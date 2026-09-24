import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_big_date.dart';
import '../../../design/widgets/app_fab.dart';
import '../../../design/widgets/app_glass_bar.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/screens/customer_list_tab.dart';
import '../../visit/api/visit_models.dart';
import '../../visit/screens/calendar_tab.dart';
import '../../visit/state/calendar_selection.dart';
import '../../../core/time/today_provider.dart';

/// 홈 탭 하나 — 탭바 항목, 본문, + 버튼(없으면 준비 중 안내), 머리를 스스로 그리는지.
/// 탭을 더하면 [_HomeShellState._tabs]에 한 줄이다 — 탭바·본문·FAB·머리가 따라온다.
class _HomeTab {
  const _HomeTab({
    required this.item,
    required this.body,
    this.fab,
    this.ownsHeader = false,
  });

  final AppGlassBarItem item;
  final Widget body;

  /// + 버튼. null 이면 "준비 중" 안내 시트를 띄운다.
  final _TabFab? fab;

  /// 탭이 자기 머리(달력의 월·화살표, 고객의 제목·보기 전환)를 그리면 셸의 머리를 숨긴다.
  final bool ownsHeader;
}

class _TabFab {
  const _TabFab({required this.semanticLabel, required this.onPressed});

  final String semanticLabel;
  final VoidCallback onPressed;
}

/// 홈 화면. 헤더(날짜 + 매장 이름 + 설정), 탭별 본문, 하단 유리 탭바로
/// 이루어진다.
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  int _tabIndex = 0;

  late final List<_HomeTab> _tabs = [
    _HomeTab(
      item: const AppGlassBarItem(
        icon: Icons.calendar_today,
        label: AppStrings.tabCalendar,
      ),
      body: const CalendarTab(),
      ownsHeader: true,
      fab: _TabFab(
        semanticLabel: AppStrings.addReservation,
        onPressed: _reserve,
      ),
    ),
    _HomeTab(
      item: const AppGlassBarItem(
        icon: Icons.people_outline,
        label: AppStrings.tabCustomers,
      ),
      body: const CustomerListTab(),
      ownsHeader: true,
      fab: _TabFab(
        semanticLabel: AppStrings.registerCustomer,
        onPressed: () => context.push('/customers/new'),
      ),
    ),
    const _HomeTab(
      item: AppGlassBarItem(
        icon: Icons.bar_chart_outlined,
        label: AppStrings.tabSales,
      ),
      body: Center(child: _EmptyState(title: AppStrings.comingSoonEmptyTitle)),
    ),
  ];

  void _openComingSoonSheet() {
    AppSheet.show<void>(
      context,
      builder: (context) => Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.lg),
        child: Text(
          AppStrings.comingSoonSheetText,
          style: AppTypography.body,
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  /// 고른 날로 예약 등록을 연다. 저장하면 저장한 날을 고른다.
  Future<void> _reserve() async {
    final selected = ref.read(selectedDateProvider);
    final saved = await context.push<DateTime>(
      '/visits/new?date=${isoDay(selected)}',
    );
    if (saved != null && mounted) {
      ref.read(selectedDateProvider.notifier).select(saved);
    }
  }

  @override
  Widget build(BuildContext context) {
    final today = ref.watch(todayProvider);
    final shopName = ref.watch(shopNameProvider);
    final tab = _tabs[_tabIndex];
    final fab = tab.fab;

    return Scaffold(
      key: ScreenKeys.home,
      extendBody: true,
      floatingActionButton: fab == null
          ? AppFab(onPressed: _openComingSoonSheet)
          : AppFab(semanticLabel: fab.semanticLabel, onPressed: fab.onPressed),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          0,
          AppSpacing.lg,
          AppSpacing.lg,
        ),
        child: SafeArea(
          top: false,
          child: AppGlassBar(
            items: [for (final t in _tabs) t.item],
            currentIndex: _tabIndex,
            onTap: (index) => setState(() => _tabIndex = index),
          ),
        ),
      ),
      body: AppBackground(
        child: SafeArea(
          bottom: false,
          child: Column(
            children: [
              if (!tab.ownsHeader)
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.lg,
                    AppSpacing.md,
                    AppSpacing.sm,
                    AppSpacing.md,
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            AppBigDate(date: today),
                            const SizedBox(height: AppSpacing.sm),
                            Text(shopName, style: AppTypography.titleKo),
                          ],
                        ),
                      ),
                      Pressable(
                        semanticLabel: AppStrings.settingsLabel,
                        onTap: () => context.push('/settings'),
                        child: const Icon(Icons.settings_outlined),
                      ),
                    ],
                  ),
                ),
              Expanded(child: tab.body),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Text(
        title,
        style: AppTypography.body,
        textAlign: TextAlign.center,
      ),
    );
  }
}
