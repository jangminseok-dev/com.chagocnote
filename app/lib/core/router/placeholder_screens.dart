import 'package:flutter/material.dart';

import 'screen_keys.dart';

/// 테스트/개발 중 화면을 식별하기 위한 자리 표시 화면. 실제 화면이 생기면
/// 이 파일에서 하나씩 걷어낸다.
class _PlaceholderScreen extends StatelessWidget {
  const _PlaceholderScreen({required this.label, required this.screenKey});

  final String label;
  final Key screenKey;

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: Center(child: Text(label, key: screenKey)));
  }
}

class SettingsShopScreen extends StatelessWidget {
  const SettingsShopScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_shop',
        screenKey: ScreenKeys.settingsShop,
      );
}

class SettingsAccountScreen extends StatelessWidget {
  const SettingsAccountScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_account',
        screenKey: ScreenKeys.settingsAccount,
      );
}

class SettingsAccountWithdrawScreen extends StatelessWidget {
  const SettingsAccountWithdrawScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_account_withdraw',
        screenKey: ScreenKeys.settingsAccountWithdraw,
      );
}
