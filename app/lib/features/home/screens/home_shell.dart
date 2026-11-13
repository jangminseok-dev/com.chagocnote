import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/widgets/app_fab.dart';
import '../../../design/widgets/app_glass_bar.dart';
import '../../../l10n/app_strings.dart';
import '../../customer/screens/customer_list_tab.dart';
import '../../sales/screens/sales_tab.dart';
import '../../visit/api/visit_models.dart';
import '../../visit/screens/calendar_tab.dart';
import '../../visit/state/calendar_selection.dart';
import '../../visit/state/upload_queue.dart';

/// 홈 탭 하나 — 탭바 항목, 본문, + 버튼. 머리는 탭이 스스로 그린다(달력의 월·화살표, 고객의 제목, 매출의 매장 이름).
/// 탭을 더하면 [_HomeShellState._tabs]에 한 줄이다 — 탭바·본문·FAB 가 따라온다.
class _HomeTab {
  const _HomeTab({
    required this.item,
    required this.body,
    required this.fab,
  });

  final AppGlassBarItem item;
  final Widget body;

  /// + 버튼.
  final _TabFab fab;
}

class _TabFab {
  const _TabFab({required this.semanticLabel, required this.onPressed});

  final String semanticLabel;
  final VoidCallback onPressed;
}

/// 홈 화면. 탭별 본문과 하단 유리 탭바로 이루어진다.
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
      fab: _TabFab(
        semanticLabel: AppStrings.registerCustomer,
        onPressed: () => context.push('/customers/new'),
      ),
    ),
    _HomeTab(
      item: const AppGlassBarItem(
        icon: Icons.bar_chart_outlined,
        label: AppStrings.tabSales,
      ),
      body: const SalesTab(),
      // 매출을 보다가도 + 는 예약 등록이다(캘린더와 같다).
      fab: _TabFab(
        semanticLabel: AppStrings.addReservation,
        onPressed: _reserve,
      ),
    ),
  ];

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
    // 업로드 대기열을 깨운다 — 앱이 꺼졌다 켜져도 남은 사진을 바로 이어 올린다(설계 10.2).
    ref.listen(uploadQueueProvider, (_, _) {});
    final tab = _tabs[_tabIndex];
    final fab = tab.fab;

    return Scaffold(
      key: ScreenKeys.home,
      extendBody: true,
      floatingActionButton: AppFab(
        semanticLabel: fab.semanticLabel,
        onPressed: fab.onPressed,
      ),
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
              Expanded(child: tab.body),
            ],
          ),
        ),
      ),
    );
  }
}
