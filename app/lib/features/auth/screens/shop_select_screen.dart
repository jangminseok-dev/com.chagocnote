import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_glass_card.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../state/session.dart';
import '../state/session_controller.dart';

/// 소속 매장 목록에서 하나를 골라 홈으로 들어가는 화면.
class ShopSelectScreen extends ConsumerWidget {
  const ShopSelectScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider).value;
    final shops = session is SignedIn ? session.me.shops : const <ShopMembership>[];

    return Scaffold(
      key: ScreenKeys.shopSelect,
      body: AppBackground(
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            children: [
              Text(AppStrings.selectShopTitle, style: AppTypography.titleKo),
              const SizedBox(height: AppSpacing.lg),
              for (final shop in shops)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Pressable(
                    semanticLabel: shop.shopName,
                    onTap: () async {
                      await ref
                          .read(sessionControllerProvider.notifier)
                          .selectShop(shop.shopId);
                      if (context.mounted) context.go('/home');
                    },
                    child: AppGlassCard(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(shop.shopName, style: AppTypography.body),
                          AppChip(
                            label: shop.isOwner
                                ? AppStrings.roleOwner
                                : AppStrings.roleStaff,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
