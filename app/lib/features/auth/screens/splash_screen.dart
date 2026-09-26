import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/async_body.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../l10n/app_strings.dart';
import '../state/session_controller.dart';

/// 세션 복원 동안 보여주는 스플래시. 복원이 실패하면 원인 문구와 재시도 버튼을 보여주고,
/// 인터넷 없음이면 인터넷이 돌아올 때 스스로 다시 복원한다(오류 화면 다듬기 설계 5절).
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);

    return Scaffold(
      key: ScreenKeys.splash,
      body: AppBackground(
        child: Center(
          child: AsyncBody.inline(
            value: session,
            onRetry: () => ref.invalidate(sessionControllerProvider),
            placeholder: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(AppStrings.appName, style: AppTypography.titleKo),
                const SizedBox(height: AppSpacing.lg),
                const CircularProgressIndicator(),
              ],
            ),
            builder: (_) => const CircularProgressIndicator(),
          ),
        ),
      ),
    );
  }
}
