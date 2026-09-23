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
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';

/// 설정 허브. 매장/다른 매장/계정 세 묶음으로 이동한다.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider).value;
    final shop = session is SignedIn ? session.selectedShop : null;
    final shopCount = session is SignedIn ? session.me.shops.length : 0;

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
              if (shop != null) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(shop.shopName, style: AppTypography.titleKo),
                    AppChip(
                      label: shop.isOwner
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
              if (shop?.isOwner ?? false)
                _SettingsRow(
                  label: AppStrings.settingsSchedule,
                  onTap: () => context.push('/settings/schedule'),
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
