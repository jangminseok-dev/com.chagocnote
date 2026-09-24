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

/// 홈 화면. 헤더(날짜 + 매장 이름 + 설정), 탭별 본문, 하단 유리 탭바로
/// 이루어진다.
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  static const _calendarTab = 0;
  static const _customersTab = 1;

  int _tabIndex = 0;

  static const _items = [
    AppGlassBarItem(icon: Icons.calendar_today, label: AppStrings.tabCalendar),
    AppGlassBarItem(icon: Icons.people_outline, label: AppStrings.tabCustomers),
    AppGlassBarItem(icon: Icons.bar_chart_outlined, label: AppStrings.tabSales),
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

    return Scaffold(
      key: ScreenKeys.home,
      extendBody: true,
      floatingActionButton: switch (_tabIndex) {
        _calendarTab => AppFab(
          semanticLabel: AppStrings.addReservation,
          onPressed: _reserve,
        ),
        _customersTab => AppFab(
          semanticLabel: AppStrings.registerCustomer,
          onPressed: () => context.push('/customers/new'),
        ),
        _ => AppFab(onPressed: _openComingSoonSheet),
      },
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
            items: _items,
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
              // 캘린더·고객 탭은 자기 머리를 쓴다(달력의 월·화살표, 고객의
              // 제목·반려동물 수·보기 전환).
              if (_tabIndex != _calendarTab && _tabIndex != _customersTab)
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
              Expanded(child: _TabBody(index: _tabIndex)),
            ],
          ),
        ),
      ),
    );
  }
}

class _TabBody extends StatelessWidget {
  const _TabBody({required this.index});

  final int index;

  @override
  Widget build(BuildContext context) {
    return switch (index) {
      _HomeShellState._calendarTab => const CalendarTab(),
      _HomeShellState._customersTab => const CustomerListTab(),
      _ => const Center(
        child: _EmptyState(title: AppStrings.comingSoonEmptyTitle),
      ),
    };
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
