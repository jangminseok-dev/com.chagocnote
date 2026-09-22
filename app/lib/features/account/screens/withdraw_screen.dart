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
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../state/withdraw_controller.dart';

/// 회원 탈퇴 화면. 안내를 확인해야 탈퇴 버튼이 활성화되고, 서버가 추가
/// 확인을 요구하면(매장 함께 닫기) 시트로 물어본 뒤 다시 요청한다.
class WithdrawScreen extends ConsumerStatefulWidget {
  const WithdrawScreen({super.key});

  @override
  ConsumerState<WithdrawScreen> createState() => _WithdrawScreenState();
}

class _WithdrawScreenState extends ConsumerState<WithdrawScreen> {
  bool _agreed = false;
  bool _busy = false;
  String? _errorText;
  bool _ownershipTransferRequired = false;

  Future<void> _withdraw({bool confirmCloseShops = false}) async {
    setState(() {
      _busy = true;
      _errorText = null;
      _ownershipTransferRequired = false;
    });
    try {
      await ref
          .read(withdrawControllerProvider.notifier)
          .withdraw(confirmCloseShops: confirmCloseShops);
      // 성공하면 세션이 로그아웃 상태가 되고 라우터가 로그인 화면으로
      // 보낸다. 화면이 아직 남아 있다면(드문 경우) busy만 풀어 둔다.
      if (mounted) setState(() => _busy = false);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.code == 'SHOP_CLOSE_CONFIRM_REQUIRED') {
        setState(() => _busy = false);
        final confirmed = await _confirmShopClose();
        if (confirmed == true && mounted) {
          await _withdraw(confirmCloseShops: true);
        }
        return;
      }
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
        _ownershipTransferRequired = e.code == 'OWNERSHIP_TRANSFER_REQUIRED';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<bool?> _confirmShopClose() {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.withdrawShopCloseTitle,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.withdrawShopCloseConfirm,
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
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: ScreenKeys.settingsAccountWithdraw,
      body: AppBackground(
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const AppBackButton(),
                const SizedBox(height: AppSpacing.lg),
                Text(AppStrings.withdraw, style: AppTypography.titleKo),
                const SizedBox(height: AppSpacing.xl),
                _NoticeLine(AppStrings.withdrawNoticeIrreversible),
                _NoticeLine(AppStrings.withdrawNoticeShopRecordsStay),
                _NoticeLine(AppStrings.withdrawNoticeMembershipGone),
                _NoticeLine(AppStrings.withdrawNoticeNewAccount),
                const SizedBox(height: AppSpacing.xl),
                CheckboxListTile(
                  value: _agreed,
                  onChanged: _busy
                      ? null
                      : (checked) => setState(() => _agreed = checked ?? false),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    AppStrings.withdrawConfirmCheckbox,
                    style: AppTypography.body,
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),
                AppButton(
                  label: AppStrings.withdrawSubmit,
                  filled: true,
                  busy: _busy,
                  onPressed: (_agreed && !_busy) ? () => _withdraw() : null,
                ),
                if (_errorText != null) ...[
                  const SizedBox(height: AppSpacing.lg),
                  Text(_errorText!, style: AppTypography.caption),
                ],
                if (_ownershipTransferRequired) ...[
                  const SizedBox(height: AppSpacing.sm),
                  AppButton(
                    label: AppStrings.goToMembers,
                    onPressed: () => context.push('/settings/members'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NoticeLine extends StatelessWidget {
  const _NoticeLine(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
        child: Text('· $text', style: AppTypography.body),
      );
}
