import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/providers.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../api/social_sign_in.dart';
import '../state/session.dart';
import '../state/session_controller.dart';
import '../state/social_sign_ins.dart';

/// 로그인 화면. 소셜 로그인 공급자마다 버튼 하나, 개발 환경에서는 이름만
/// 넣는 개발용 로그인도 함께 보여준다.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _devNameController = TextEditingController();
  bool _busy = false;
  String? _errorText;
  String? _devNameError;

  @override
  void dispose() {
    _devNameController.dispose();
    super.dispose();
  }

  Future<void> _signInWith(SocialSignIn signIn) async {
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final credential = await signIn.signIn();
      if (credential == null) {
        // 사용자가 취소했다 — 요청 없이 그대로 로그인 화면에 머무른다.
        if (mounted) setState(() => _busy = false);
        return;
      }
      await ref.read(sessionControllerProvider.notifier).signIn(credential);
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _signInDev() async {
    final name = _devNameController.text.trim();
    if (name.isEmpty) {
      setState(() => _devNameError = AppStrings.devNameRequired);
      return;
    }
    setState(() {
      _devNameError = null;
      _busy = true;
      _errorText = null;
    });
    try {
      await ref.read(sessionControllerProvider.notifier).signIn(
            SocialCredential(provider: 'dev', token: name),
          );
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  String _labelFor(String provider) => switch (provider) {
        'kakao' => AppStrings.continueWithKakao,
        'google' => AppStrings.continueWithGoogle,
        'apple' => AppStrings.continueWithApple,
        _ => provider,
      };

  @override
  Widget build(BuildContext context) {
    final signIns = ref.watch(socialSignInsProvider);
    final config = ref.watch(appConfigProvider);
    final session = ref.watch(sessionControllerProvider).value;
    final expired = session is SignedOut && session.sessionExpired;

    return Scaffold(
      key: ScreenKeys.login,
      body: AppBackground(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(AppStrings.appName, style: AppTypography.titleKo),
                  const SizedBox(height: AppSpacing.xxl),
                  if (expired) ...[
                    Text(
                      AppStrings.sessionExpiredBanner,
                      style: AppTypography.caption,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                  ],
                  for (final signIn in signIns) ...[
                    SizedBox(
                      width: double.infinity,
                      child: AppButton(
                        label: _labelFor(signIn.provider),
                        filled: true,
                        busy: _busy,
                        onPressed: _busy ? null : () => _signInWith(signIn),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  if (config.isDev) ...[
                    const SizedBox(height: AppSpacing.lg),
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
                        onPressed: _busy ? null : _signInDev,
                      ),
                    ),
                  ],
                  if (_errorText != null) ...[
                    const SizedBox(height: AppSpacing.lg),
                    Text(
                      _errorText!,
                      style: AppTypography.caption,
                      textAlign: TextAlign.center,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
