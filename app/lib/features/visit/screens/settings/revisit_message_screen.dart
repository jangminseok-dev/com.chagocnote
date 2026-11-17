import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/async_body.dart';
import '../../../../core/router/screen_keys.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_back_button.dart';
import '../../../../l10n/app_strings.dart';
import '../../../auth/state/shop_selection.dart';
import '../../../customer/screens/form_text_edit_screens.dart';
import '../../api/revisit_models.dart';
import '../../state/revisit_rules.dart';
import '../../state/visit_commands.dart';
import '../../state/visit_providers.dart';

/// 다시 올 때가 된 아이에게 보낼 글의 템플릿(⑬ 설계 3.7) — 글 칸, 넣을 수 있는 자리(아이 이름·지난 주 수·매장 이름),
/// 보호자가 받는 모습, [저장], [처음 글로 돌아가기]. 몸통은 서류 설정의 `FormTextEdit` 그대로다.
/// 빈 글은 저장하지 않는다(서버도 거절한다). 바꾸는 것은 사장만이다. 템플릿을 로그에 남기지 않는다.
class RevisitMessageScreen extends ConsumerWidget {
  const RevisitMessageScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopId = ref.watch(selectedShopIdProvider);
    final settings = shopId == null
        ? const AsyncValue<RevisitSettings>.loading()
        : ref.watch(revisitSettingsProvider(shopId));
    return Scaffold(
      key: ScreenKeys.revisitMessage,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.sm),
                child: Row(
                  children: [
                    // 뒤로 가기는 몸통의 PopScope 를 거친다 — 고친 글이 있으면 묻는다.
                    AppBackButton(onTap: () => Navigator.of(context).maybePop()),
                    const SizedBox(width: AppSpacing.sm),
                    const Expanded(
                      child: Text(AppStrings.revisitMessageTitle, style: AppTypography.titleKo),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<RevisitSettings>(
                  value: settings,
                  onRetry: () => ref.invalidate(revisitSettingsProvider(shopId!)),
                  builder: (s) {
                    final commands = ref.read(visitCommandsProvider);
                    final shop = ref.watch(shopNameProvider);
                    return FormTextEdit(
                      initial: s.message,
                      maxLength: revisitMessageMax,
                      canEdit: ref.watch(isOwnerProvider),
                      slots: revisitSlots,
                      slotLabel: revisitSlotLabel,
                      notice: revisitMessageProblem,
                      preview: (text) => Text(
                        fillRevisitMessage(
                          text,
                          shop: shop,
                          pet: AppStrings.revisitSamplePet,
                          weeks: s.defaultCycleWeeks,
                        ),
                        style: AppTypography.body,
                      ),
                      savedMessage: AppStrings.revisitMessageSaved,
                      onSave: (text) =>
                          commands.updateRevisitSettings(shopId!, {'revisit_message': text}),
                      onReset: s.revisitMessage == null
                          ? null
                          : () => commands.updateRevisitSettings(shopId!, {'revisit_message': null}),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
