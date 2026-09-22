import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../api/invite_api.dart';
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
      // 수락이 ALREADY_A_MEMBER 면 앞선 수락이 서버에서 이미 끝났는데 뒤이은
      // 재조회만 실패했던 경우다 — 오류로 끝내지 않고 재조회부터 다시 한다
      // (최종 재검토 F6).
      InviteAccepted? result;
      ApiException? alreadyMember;
      try {
        result = await ref.read(inviteApiProvider).accept(code);
      } on ApiException catch (e) {
        if (e.code != 'ALREADY_A_MEMBER') rethrow;
        alreadyMember = e;
      }
      final controller = ref.read(sessionControllerProvider.notifier);
      Object? reloadError;
      try {
        await controller.reloadMe();
      } catch (e) {
        // 소속이 이미 있으면 홈으로 가도 된다(다음 재조회로 맞춰진다). 소속이
        // 비어 있으면 아래에서 문구로 보여준다.
        reloadError = e;
      }
      if (result != null) await controller.selectShop(result.shopId);
      if (!mounted) return;
      final session = ref.read(sessionControllerProvider).value;
      final hasShops = session is SignedIn && session.me.shops.isNotEmpty;
      if (!hasShops) {
        // 라우터가 /home 을 /invite 로 되돌려 이 화면(State)이 그대로 남는다
        // — 스피너를 풀고 다시 누를 수 있게 한다.
        setState(() {
          _busy = false;
          _errorText = messageFor(
            reloadError ?? alreadyMember ?? StateError('소속 없음'),
          );
        });
        return;
      }
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
      body: AppBackground(
        child: SafeArea(
          child: Stack(
            children: [
              _buildForm(hasShops),
              // 소속이 있는 유저(설정에서 들어옴)만 뒤로 갈 수 있다. AppBar 를
              // 쓰면 테마 색 띠가 깔려 검은 아이콘이 묻힌다 — 다른 설정 화면처럼
              // 본문 머리 왼쪽에 둔다.
              if (hasShops)
                Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: AppBackButton(
                    onTap: () {
                      if (context.canPop()) {
                        context.pop();
                      } else {
                        context.go('/settings');
                      }
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildForm(bool hasShops) {
    return Center(
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
    );
  }
}
