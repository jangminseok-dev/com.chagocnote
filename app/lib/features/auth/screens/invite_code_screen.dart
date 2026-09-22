import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../state/auth_providers.dart';
import '../state/session.dart';
import '../state/session_controller.dart';

/// 초대 코드 입력 화면. 성공하면 본인 정보를 다시 불러와 해당 매장을 선택한
/// 뒤 홈으로 이동한다.
class InviteCodeScreen extends ConsumerStatefulWidget {
  const InviteCodeScreen({super.key});

  @override
  ConsumerState<InviteCodeScreen> createState() => _InviteCodeScreenState();
}

class _InviteCodeScreenState extends ConsumerState<InviteCodeScreen> {
  final _codeController = TextEditingController();
  bool _busy = false;
  String? _errorText;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      setState(() => _errorText = AppStrings.inviteCodeRequired);
      return;
    }

    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final result = await ref.read(inviteApiProvider).accept(code);
      final controller = ref.read(sessionControllerProvider.notifier);
      try {
        await controller.reloadMe();
      } catch (_) {
        // 수락은 서버에서 이미 끝났다 — 재조회 실패를 수락 실패로 보이면
        // 사용자가 다시 눌러 ALREADY_A_MEMBER 에 갇힌다. 해제 때처럼 삼키고,
        // 다음 재조회·라우터 평가로 맞춰지게 둔다(최종 검토 F6).
      }
      await controller.selectShop(result.shopId);
      if (!mounted) return;
      context.go('/home');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider).value;
    final hasShops = session is SignedIn && session.me.shops.isNotEmpty;

    return Scaffold(
      key: ScreenKeys.invite,
      appBar: hasShops
          ? AppBar(
              backgroundColor: Colors.transparent,
              elevation: 0,
              leading: AppBackButton(
                onTap: () {
                  if (context.canPop()) {
                    context.pop();
                  } else {
                    context.go('/settings');
                  }
                },
              ),
            )
          : null,
      body: AppBackground(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(AppStrings.inviteCodeLabel, style: AppTypography.titleKo),
                  const SizedBox(height: AppSpacing.lg),
                  TextField(
                    controller: _codeController,
                    decoration: InputDecoration(
                      labelText: AppStrings.inviteCodeLabel,
                      errorText: _errorText,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  SizedBox(
                    width: double.infinity,
                    child: AppButton(
                      label: AppStrings.inviteSubmit,
                      filled: true,
                      busy: _busy,
                      onPressed: _busy ? null : _submit,
                    ),
                  ),
                  if (!hasShops) ...[
                    const SizedBox(height: AppSpacing.xxl),
                    AppButton(
                      label: AppStrings.accountSettings,
                      onPressed: () => context.go('/settings/account'),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    AppButton(
                      label: AppStrings.logout,
                      onPressed: () =>
                          ref.read(sessionControllerProvider.notifier).signOut(),
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
