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
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../state/today_provider.dart';

/// 홈 화면. 헤더(날짜 + 매장 이름 + 설정), 탭별 본문, 하단 유리 탭바로
/// 이루어진다.
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
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

  @override
  Widget build(BuildContext context) {
    final today = ref.watch(todayProvider);
    final session = ref.watch(sessionControllerProvider).value;
    final shopName =
        session is SignedIn ? session.selectedShop?.shopName ?? '' : '';

    return Scaffold(
      key: ScreenKeys.home,
      extendBody: true,
      floatingActionButton: AppFab(onPressed: _openComingSoonSheet),
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
                      onTap: () => context.go('/settings'),
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
    return Center(
      child: index == 0
          ? const _EmptyState(
              title: AppStrings.calendarEmptyTitle,
              caption: AppStrings.calendarEmptyCaption,
            )
          : const _EmptyState(title: AppStrings.comingSoonEmptyTitle),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.title, this.caption});

  final String title;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(title, style: AppTypography.body, textAlign: TextAlign.center),
          if (caption != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              caption!,
              style: AppTypography.caption,
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }
}
