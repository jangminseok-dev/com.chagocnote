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
import '../../../design/widgets/app_error_retry.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_providers.dart';
import 'customer_form.dart';

/// 보호자 수정. 사장에게만 맨 아래 "고객 삭제"(익명화)가 보인다 — 보안 경계는
/// 서버의 `customer:delete`(403)다.
class CustomerEditScreen extends ConsumerStatefulWidget {
  const CustomerEditScreen({super.key, required this.customerId});

  final int customerId;

  @override
  ConsumerState<CustomerEditScreen> createState() => _CustomerEditScreenState();
}

class _CustomerEditScreenState extends ConsumerState<CustomerEditScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  /// 쓰기 하나를 돌린다(연타 방지, 실패 문구). 성공하면 true.
  Future<bool> _run(Future<void> Function(int shopId) action) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return false;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action(shopId);
      return true;
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _errorText = messageFor(e);
        });
      }
      return false;
    }
  }

  Future<void> _save(CustomerFields fields) async {
    final saved = await _run(
      (shopId) => ref
          .read(customerCommandsProvider)
          .updateCustomer(shopId, widget.customerId, fields),
    );
    if (saved && mounted) context.pop();
  }

  Future<void> _delete() async {
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.deleteCustomerConfirm,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.deleteCustomer,
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
    final deleted = await _run(
      (shopId) => ref
          .read(customerCommandsProvider)
          .deleteCustomer(shopId, widget.customerId),
    );
    // 이 고객의 화면(반려동물 상세 등)은 모두 사라졌다 — 홈(고객 탭)으로 간다.
    if (deleted && mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    // 매장이 바뀌면 다시 그려야 하므로 build 안에서는 watch 한다(_shopId
    // getter 는 read 라 액션 메서드 전용).
    final shopId = ref.watch(selectedShopIdProvider);
    final isOwner = ref.watch(isOwnerProvider);
    final key = shopId == null
        ? null
        : (shopId: shopId, customerId: widget.customerId);
    final detail = key == null
        ? const AsyncValue<CustomerDetail>.loading()
        : ref.watch(customerDetailProvider(key));

    return Scaffold(
      key: ScreenKeys.customerEdit,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      AppStrings.editOwnerTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: detail.when(
                  data: (detail) => SingleChildScrollView(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Column(
                      children: [
                        CustomerForm(
                          initial: detail.customer,
                          submitLabel: AppStrings.save,
                          busy: _busy,
                          errorText: _errorText,
                          onSubmit: _save,
                        ),
                        if (isOwner) ...[
                          const SizedBox(height: AppSpacing.xxl),
                          AppButton(
                            label: AppStrings.deleteCustomer,
                            onPressed: _busy ? null : _delete,
                          ),
                        ],
                      ],
                    ),
                  ),
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => AppErrorRetry(
                    message: messageFor(error),
                    onRetry: () => ref.invalidate(customerDetailProvider(key!)),
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
