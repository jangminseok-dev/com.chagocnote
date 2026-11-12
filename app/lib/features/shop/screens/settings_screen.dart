import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';

/// 설정 허브. 매장/다른 매장/계정 세 묶음으로 이동한다.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopId = ref.watch(selectedShopIdProvider);
    final shopName = ref.watch(shopNameProvider);
    final isOwner = ref.watch(isOwnerProvider);
    final shopCount = ref.watch(shopCountProvider);

    return Scaffold(
      key: ScreenKeys.settings,
      body: AppBackground(
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            children: [
              // ListView 는 자식을 가로로 늘린다 — 아이콘이 가운데에 그려지지
              // 않게 왼쪽에 붙인다.
              const Align(
                alignment: Alignment.centerLeft,
                child: AppBackButton(),
              ),
              const SizedBox(height: AppSpacing.lg),
              if (shopId != null) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(shopName, style: AppTypography.titleKo),
                    AppChip(
                      label: isOwner
                          ? AppStrings.roleOwner
                          : AppStrings.roleStaff,
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.xl),
              ],
              const _SectionLabel(AppStrings.settingsSectionShop),
              _SettingsRow(
                label: AppStrings.settingsMembers,
                onTap: () => context.push('/settings/members'),
              ),
              _SettingsRow(
                label: AppStrings.settingsShopInfo,
                onTap: () => context.push('/settings/shop'),
              ),
              // 일정·메뉴는 사장만 바꾼다(보안 경계는 서버 403) — 직원에게는 보이지 않는다.
              if (isOwner)
                _SettingsRow(
                  label: AppStrings.settingsSchedule,
                  onTap: () => context.push('/settings/schedule'),
                ),
              if (isOwner)
                _SettingsRow(
                  label: AppStrings.settingsMenus,
                  onTap: () => context.push('/settings/menus'),
                ),
              // 알림장 설정도 사장만 바꾸지만 직원에게도 보인다 — 읽기 전용으로 열린다(⑤ 설계 9.1).
              _SettingsRow(
                label: AppStrings.settingsReport,
                onTap: () => context.push('/settings/report'),
              ),
              // 알림톡도 같다 — 연동·설정은 사장만, 직원에게는 읽기 전용으로 열린다(⑥ 설계 8.1).
              _SettingsRow(
                label: AppStrings.settingsNotification,
                onTap: () => context.push('/settings/notification'),
              ),
              const SizedBox(height: AppSpacing.xl),
              const _SectionLabel(AppStrings.settingsSectionOtherShops),
              if (shopCount >= 2)
                _SettingsRow(
                  label: AppStrings.settingsSwitchShop,
                  onTap: () => context.push('/shops/select'),
                ),
              _SettingsRow(
                label: AppStrings.settingsJoinByInvite,
                onTap: () => context.push('/invite'),
              ),
              const SizedBox(height: AppSpacing.xl),
              const _SectionLabel(AppStrings.settingsSectionAccount),
              _SettingsRow(
                label: AppStrings.settingsAccount,
                onTap: () => context.push('/settings/account'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Text(label, style: AppTypography.caption),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: AppColors.line)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: AppTypography.body),
            const Icon(
              Icons.chevron_right,
              size: 18,
              color: AppColors.secondary,
            ),
          ],
        ),
      ),
    );
  }
}
