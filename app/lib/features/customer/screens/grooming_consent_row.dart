import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';

/// 기본 탭의 미용 동의서 줄(③-B 설계 3.4) — 받은 날을 보이고, 받았다고 적거나 지운다.
///
/// 종이 동의서를 받았다는 표시일 뿐이다(전자 동의서가 아니다). 받은 날은 오늘로 적는다.
/// 노령·지병 아이의 예약에 "미용 동의서를 받아 주세요"가 뜨는지는 서버가 이 날짜로 정한다 —
/// 지병을 더하면 서버가 이 칸을 비운다. 실패는 스낵바로 알린다.
class GroomingConsentRow extends ConsumerStatefulWidget {
  const GroomingConsentRow({super.key, required this.pet});

  final Pet pet;

  @override
  ConsumerState<GroomingConsentRow> createState() => _GroomingConsentRowState();
}

class _GroomingConsentRowState extends ConsumerState<GroomingConsentRow> {
  bool _busy = false;

  Future<void> _run(Future<void> Function(int shopId) action) async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _busy) return;
    setState(() => _busy = true);
    String? failure;
    try {
      await action(shopId);
    } catch (e) {
      failure = messageFor(e);
    }
    // 적는 도중 화면을 떠났으면 아무것도 띄우지 않는다.
    if (!mounted) return;
    setState(() => _busy = false);
    if (failure != null) AppSnackBar.show(context, failure);
  }

  Future<void> _set() => _run(
    (shopId) => ref
        .read(customerCommandsProvider)
        .setGroomingConsent(shopId, widget.pet.petId),
  );

  Future<void> _openActions() async {
    final again = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppSheetAction(
            label: AppStrings.groomingConsentAgain,
            onTap: () => Navigator.of(context).pop(true),
          ),
          AppSheetAction(
            label: AppStrings.groomingConsentClear,
            onTap: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
    if (again == null || !mounted) return;
    if (again) {
      await _set();
    } else {
      await _run(
        (shopId) => ref
            .read(customerCommandsProvider)
            .clearGroomingConsent(shopId, widget.pet.petId),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final receivedOn = widget.pet.groomingConsentOn;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: SizedBox(
        width: double.infinity,
        child: AppCard(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      AppStrings.groomingConsentLabel,
                      style: AppTypography.caption,
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      receivedOn == null
                          ? AppStrings.groomingConsentNone
                          : AppStrings.groomingConsentOn(receivedOn),
                      style: AppTypography.body,
                    ),
                  ],
                ),
              ),
              if (receivedOn == null)
                AppButton(
                  key: const ValueKey('grooming-consent-set'),
                  label: AppStrings.consentReceived,
                  busy: _busy,
                  onPressed: _set,
                )
              else
                Pressable(
                  semanticLabel: AppStrings.groomingConsentMore,
                  onTap: _busy ? null : _openActions,
                  child: const Icon(Icons.more_horiz),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
