import 'package:flutter/material.dart';

/// 테스트/개발 중 화면을 식별하기 위한 키. 실제 화면이 생기면 이 파일 전체를
/// 걷어낸다.
class ScreenKeys {
  static const splash = Key('screen_splash');
  static const login = Key('screen_login');
  static const invite = Key('screen_invite');
  static const shopSelect = Key('screen_shop_select');
  static const home = Key('screen_home');
  static const settings = Key('screen_settings');
  static const settingsMembers = Key('screen_settings_members');
  static const settingsShop = Key('screen_settings_shop');
  static const settingsAccount = Key('screen_settings_account');
  static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
}

class _PlaceholderScreen extends StatelessWidget {
  const _PlaceholderScreen({required this.label, required this.screenKey});

  final String label;
  final Key screenKey;

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: Center(child: Text(label, key: screenKey)));
  }
}

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'splash', screenKey: ScreenKeys.splash);
}

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'login', screenKey: ScreenKeys.login);
}

class InviteScreen extends StatelessWidget {
  const InviteScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'invite', screenKey: ScreenKeys.invite);
}

class ShopSelectScreen extends StatelessWidget {
  const ShopSelectScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'shop_select',
        screenKey: ScreenKeys.shopSelect,
      );
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'home', screenKey: ScreenKeys.home);
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings',
        screenKey: ScreenKeys.settings,
      );
}

class SettingsMembersScreen extends StatelessWidget {
  const SettingsMembersScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_members',
        screenKey: ScreenKeys.settingsMembers,
      );
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
