import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../state/session_controller.dart';

/// 세션 복원 동안 보여주는 스플래시. 복원이 실패하면 오류 문구와 재시도
/// 버튼을 보여준다.
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);

    return Scaffold(
      key: ScreenKeys.splash,
      body: AppBackground(
        child: Center(
          child: session.when(
            data: (_) => const CircularProgressIndicator(),
            loading: () => Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(AppStrings.appName, style: AppTypography.titleKo),
                const SizedBox(height: AppSpacing.lg),
                const CircularProgressIndicator(),
              ],
            ),
            error: (error, _) => Padding(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    messageFor(error),
                    style: AppTypography.body,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  AppButton(
                    label: AppStrings.retry,
                    onPressed: () => ref.invalidate(sessionControllerProvider),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
