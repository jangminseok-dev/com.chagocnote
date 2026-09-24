import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/shop_api.dart';
import '../state/shop_settings_controller.dart';

/// 매장 정보 화면. 사장은 이름·전화번호·주소를 고쳐 저장할 수 있고,
/// 직원은 읽기 전용으로 본다.
class ShopSettingsScreen extends ConsumerStatefulWidget {
  const ShopSettingsScreen({super.key});

  @override
  ConsumerState<ShopSettingsScreen> createState() => _ShopSettingsScreenState();
}

class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _addressController = TextEditingController();
  bool _fieldsInitialized = false;
  bool _busy = false;
  String? _nameError;
  String? _errorText;
  String? _successText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  void _initFields(ShopSettings settings) {
    if (_fieldsInitialized) return;
    _fieldsInitialized = true;
    _nameController.text = settings.name;
    _phoneController.text = settings.phone ?? '';
    _addressController.text = settings.address ?? '';
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final shopId = _shopId;
    if (shopId == null) return;

    final name = _nameController.text.trim();
    if (name.isEmpty || name.length > 50) {
      setState(() => _nameError = AppStrings.shopNameRequired);
      return;
    }

    setState(() {
      _nameError = null;
      _errorText = null;
      _successText = null;
      _busy = true;
    });
    try {
      final phone = _phoneController.text.trim();
      final address = _addressController.text.trim();
      await ref
          .read(shopSettingsControllerProvider(shopId).notifier)
          .save(
            name: name,
            phone: phone.isEmpty ? null : phone,
            address: address.isEmpty ? null : address,
          );
      if (!mounted) return;
      setState(() {
        _busy = false;
        _successText = AppStrings.saved;
      });
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
    // 매장이 바뀌면 다시 그려야 하므로 build 안에서는 watch 한다(_shopId
    // getter 는 read 라 액션 메서드 전용).
    final shopId = ref.watch(selectedShopIdProvider);
    final isOwner = ref.watch(isOwnerProvider);
    final settingsAsync = shopId == null
        ? const AsyncValue<ShopSettings>.loading()
        : ref.watch(shopSettingsControllerProvider(shopId));

    return Scaffold(
      key: ScreenKeys.settingsShop,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 머리는 로딩·오류 상태에서도 보인다 — 오류에 갇혀도 뒤로 갈 수
              // 있어야 한다(최종 검토 C).
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.lg,
                  AppSpacing.lg,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      AppStrings.settingsShopInfo,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: settingsAsync.when(
                  data: (settings) {
                    _initFields(settings);
                    return SingleChildScrollView(
                      padding: const EdgeInsets.all(AppSpacing.lg),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: AppSpacing.sm),
                          TextField(
                            controller: _nameController,
                            enabled: isOwner,
                            decoration: InputDecoration(
                              labelText: AppStrings.shopName,
                              errorText: _nameError,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            controller: _phoneController,
                            enabled: isOwner,
                            decoration: const InputDecoration(
                              labelText: AppStrings.shopPhone,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            controller: _addressController,
                            enabled: isOwner,
                            decoration: const InputDecoration(
                              labelText: AppStrings.shopAddress,
                            ),
                          ),
                          if (isOwner) ...[
                            const SizedBox(height: AppSpacing.xl),
                            AppButton(
                              label: AppStrings.save,
                              filled: true,
                              busy: _busy,
                              onPressed: _busy ? null : _save,
                            ),
                          ],
                          if (_errorText != null) ...[
                            const SizedBox(height: AppSpacing.lg),
                            Text(_errorText!, style: AppTypography.caption),
                          ],
                          if (_successText != null) ...[
                            const SizedBox(height: AppSpacing.lg),
                            Text(_successText!, style: AppTypography.caption),
                          ],
                        ],
                      ),
                    );
                  },
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => AppErrorRetry(
                    message: messageFor(error),
                    onRetry: () =>
                        ref.invalidate(shopSettingsControllerProvider(shopId!)),
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
