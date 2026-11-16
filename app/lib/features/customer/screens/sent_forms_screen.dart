import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/proxy/share_sheet.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/consent_models.dart';
import '../state/consent_commands.dart';
import '../state/consent_providers.dart';

/// 고객 탭의 `보낸 서류 N`(⑪ 설계 3.6) — 살아 있는 링크가 있을 때만 보인다.
/// 읽는 중·읽지 못함·없음이면 줄이 없다(탭의 본문이 아니다).
class SentFormsEntry extends ConsumerWidget {
  const SentFormsEntry({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopId = ref.watch(selectedShopIdProvider);
    if (shopId == null) return const SizedBox.shrink();
    final forms = ref.watch(sentFormsProvider(shopId));
    // 다시 읽기가 실패했을 때도 없다 — value 는 실패해도 이전 값을 들고 있다.
    final count = forms.hasError ? 0 : (forms.value?.length ?? 0);
    if (count == 0) return const SizedBox.shrink();
    final label = AppStrings.sentFormsEntry(count);
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.xs, AppSpacing.lg, 0),
      child: Pressable(
        semanticLabel: label,
        onTap: () => context.push('/forms'),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
          child: ExcludeSemantics(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label, style: AppTypography.body),
                const Icon(Icons.chevron_right, size: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// 보낸 서류 — 살아 있는 링크. 다시 공유하거나 잘못 보낸 링크를 끊는다.
/// **링크 주소에는 토큰이 들어 있다** — 화면에 그리지 않고 공유 시트에만 넘긴다.
class SentFormsScreen extends ConsumerStatefulWidget {
  const SentFormsScreen({super.key});

  @override
  ConsumerState<SentFormsScreen> createState() => _SentFormsScreenState();
}

class _SentFormsScreenState extends ConsumerState<SentFormsScreen> {
  /// 끊는 중인 링크 — 그 줄의 버튼은 눌리지 않는다.
  int? _revoking;

  Future<void> _share(SentForm form, Rect origin) async {
    try {
      await ref.read(shareSheetProvider).shareText(form.url, origin: origin);
    } on Exception {
      if (mounted) AppSnackBar.show(context, AppStrings.consentShareFailed);
    }
  }

  Future<void> _revoke(SentForm form) async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _revoking != null) return;
    final sure = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Text(AppStrings.sentFormRevokeAsk, style: AppTypography.bodyStrong, textAlign: TextAlign.center),
          ),
          AppSheetAction(label: AppStrings.sentFormRevokeConfirm, onTap: () => Navigator.of(context).pop(true)),
          AppSheetAction(label: AppStrings.sentFormKeep, onTap: () => Navigator.of(context).pop(false)),
        ],
      ),
    );
    if (sure != true || !mounted) return;
    setState(() => _revoking = form.formId);
    String? failure;
    try {
      await ref.read(consentCommandsProvider).revoke(shopId, form.formId);
    } catch (e) {
      failure = messageFor(e);
    }
    if (!mounted) return;
    setState(() => _revoking = null);
    if (failure != null) AppSnackBar.show(context, failure);
  }

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider) ?? 0;
    final forms = ref.watch(sentFormsProvider(shopId));
    return Scaffold(
      key: ScreenKeys.sentForms,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.sm),
                child: Row(
                  children: [
                    AppBackButton(),
                    SizedBox(width: AppSpacing.sm),
                    Expanded(child: Text(AppStrings.sentFormsTitle, style: AppTypography.titleKo)),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<List<SentForm>>(
                  value: forms,
                  onRetry: () => ref.invalidate(sentFormsProvider(shopId)),
                  onRefresh: () => ref.refresh(sentFormsProvider(shopId).future),
                  builder: (items) => ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
                    children: [
                      if (items.isEmpty)
                        const Padding(
                          padding: EdgeInsets.only(top: AppSpacing.xxl),
                          child: Center(child: Text(AppStrings.sentFormsEmpty, style: AppTypography.body)),
                        ),
                      for (final form in items)
                        Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                          child: _row(form),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _row(SentForm form) {
    final busy = _revoking == form.formId;
    return AppCard(
      key: ValueKey('sent-form-${form.formId}'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(AppStrings.sentFormKind, style: AppTypography.caption),
          const SizedBox(height: AppSpacing.xs),
          Text([for (final pet in form.pets) pet.name].join(' · '), style: AppTypography.bodyStrong),
          const SizedBox(height: AppSpacing.xs),
          Text(
            AppStrings.sentFormMeta(form.customerName, form.sentOn, form.expiresOn),
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              IntrinsicWidth(
                // 공유 시트는 누른 버튼에 붙는다(아이패드).
                child: Builder(
                  builder: (context) => AppButton(
                    key: ValueKey('sent-form-share-${form.formId}'),
                    label: AppStrings.consentShareAgain,
                    onPressed: busy
                        ? null
                        : () {
                            final box = context.findRenderObject()! as RenderBox;
                            _share(form, box.localToGlobal(Offset.zero) & box.size);
                          },
                  ),
                ),
              ),
              IntrinsicWidth(
                child: AppButton(
                  key: ValueKey('sent-form-revoke-${form.formId}'),
                  label: AppStrings.sentFormRevoke,
                  busy: busy,
                  onPressed: () => _revoke(form),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
