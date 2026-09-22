import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/providers.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_glass_card.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/api/social_sign_in.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../auth/state/social_sign_ins.dart';
import '../state/account_controller.dart';

/// 계정 화면 — 로그인 수단 연결/해제, 로그아웃, 회원 탈퇴로 가는 입구.
class AccountScreen extends ConsumerStatefulWidget {
  const AccountScreen({super.key});

  @override
  ConsumerState<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends ConsumerState<AccountScreen> {
  final _devNameController = TextEditingController();
  bool _busy = false;
  String? _errorText;
  String? _devNameError;

  @override
  void dispose() {
    _devNameController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action();
      if (!mounted) return;
      setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _link(SocialSignIn signIn) =>
      _run(() => ref.read(accountControllerProvider.notifier).link(signIn));

  Future<void> _linkDev() {
    final name = _devNameController.text.trim();
    if (name.isEmpty) {
      setState(() => _devNameError = AppStrings.devNameRequired);
      return Future.value();
    }
    setState(() => _devNameError = null);
    return _run(
      () => ref.read(accountControllerProvider.notifier).linkDev(name),
    );
  }

  Future<void> _confirmUnlink(String provider) async {
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.unlinkConfirmMessage,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.unlink,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await _run(
      () => ref.read(accountControllerProvider.notifier).unlink(provider),
    );
  }

  Future<void> _logout() =>
      _run(() => ref.read(accountControllerProvider.notifier).logout());

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider).value;
    final displayName = session is SignedIn ? session.me.displayName : '';
    final identities = ref.watch(accountIdentitiesProvider);
    final signIns = ref.watch(socialSignInsProvider);
    final config = ref.watch(appConfigProvider);
    final linkable =
        signIns.where((s) => !identities.contains(s.provider)).toList();
    final showDevLink = config.isDev && !identities.contains('dev');

    return Scaffold(
      key: ScreenKeys.settingsAccount,
      body: AppBackground(
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Text(displayName, style: AppTypography.titleKo),
                  ],
                ),
                const SizedBox(height: AppSpacing.xl),
                Text(
                  AppStrings.accountLinkedMethods,
                  style: AppTypography.caption,
                ),
                const SizedBox(height: AppSpacing.sm),
                for (final provider in identities)
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                    child: AppGlassCard(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            AppStrings.providerLabel(provider),
                            style: AppTypography.body,
                          ),
                          if (identities.length <= 1)
                            Text(
                              AppStrings.unlinkOnlyOneCaption,
                              style: AppTypography.caption,
                            )
                          else
                            AppButton(
                              label: AppStrings.unlink,
                              busy: _busy,
                              onPressed:
                                  _busy ? null : () => _confirmUnlink(provider),
                            ),
                        ],
                      ),
                    ),
                  ),
                if (linkable.isNotEmpty || showDevLink) ...[
                  const SizedBox(height: AppSpacing.xl),
                  Text(
                    AppStrings.accountAddMethod,
                    style: AppTypography.caption,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  for (final signIn in linkable) ...[
                    SizedBox(
                      width: double.infinity,
                      child: AppButton(
                        label: AppStrings.providerLabel(signIn.provider),
                        busy: _busy,
                        onPressed: _busy ? null : () => _link(signIn),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  if (showDevLink) ...[
                    TextField(
                      controller: _devNameController,
                      decoration: InputDecoration(
                        labelText: AppStrings.devNameLabel,
                        errorText: _devNameError,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    SizedBox(
                      width: double.infinity,
                      child: AppButton(
                        label: AppStrings.devSignIn,
                        busy: _busy,
                        onPressed: _busy ? null : _linkDev,
                      ),
                    ),
                  ],
                ],
                const SizedBox(height: AppSpacing.xl),
                AppButton(
                  label: AppStrings.logout,
                  onPressed: _busy ? null : _logout,
                ),
                const SizedBox(height: AppSpacing.sm),
                AppButton(
                  label: AppStrings.withdraw,
                  onPressed: () => context.push('/settings/account/withdraw'),
                ),
                if (_errorText != null) ...[
                  const SizedBox(height: AppSpacing.lg),
                  Text(_errorText!, style: AppTypography.caption),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
