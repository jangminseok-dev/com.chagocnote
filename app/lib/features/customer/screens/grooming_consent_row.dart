import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/share_sheet.dart';
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
import '../state/consent_commands.dart';
import '../state/customer_commands.dart';

/// 기본 탭의 미용 동의서 줄(③-B 설계 3.4) — 받은 날을 보이고, 받았다고 적거나 지운다.
///
/// 손으로 적는 [받았어요]는 종이·말로 받았다는 표시다. 전자 서명(⑪)으로 받았으면 `서명 받음`과 [서명 보기]가
/// 보이고, `···`에서 동의서를 보내거나 그 자리에서 서명받을 수 있다. 받은 날은 오늘로 적는다.
/// 노령·지병 아이의 예약에 "미용 동의서를 받아 주세요"가 뜨는지는 서버가 이 날짜로 정한다 —
/// 지병을 더하면 서버가 이 칸을 비운다. 실패는 스낵바로 알린다.
class GroomingConsentRow extends ConsumerStatefulWidget {
  const GroomingConsentRow({super.key, required this.pet});

  final Pet pet;

  @override
  ConsumerState<GroomingConsentRow> createState() => _GroomingConsentRowState();
}

enum _ConsentAction { send, signHere, again, clear }

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

  /// 동의서 링크를 만들어(있으면 같은 링크) 공유 시트에 넘긴다. 예약 없이 보내는 것이라 기준일은 오늘이다.
  /// 링크 주소는 어디에도 적지 않는다.
  Future<void> _send(Rect origin) async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _busy) return;
    setState(() => _busy = true);
    String? failure;
    try {
      final link = await ref.read(consentCommandsProvider).send(shopId, [widget.pet.petId]);
      try {
        await ref.read(shareSheetProvider).shareText(link.url, origin: origin);
      } on Exception {
        failure = AppStrings.consentShareFailed;
      }
    } on ApiException catch (e) {
      failure = e.code == 'CONSENT_UP_TO_DATE' ? AppStrings.consentSendUpToDateHere : messageFor(e);
    } catch (e) {
      failure = messageFor(e);
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (failure != null) AppSnackBar.show(context, failure);
  }

  Future<void> _openActions() async {
    // 공유 시트를 붙일 자리 — 시트를 띄우기 전에 이 줄의 사각형을 잡아 둔다.
    final box = context.findRenderObject()! as RenderBox;
    final origin = box.localToGlobal(Offset.zero) & box.size;
    final received = widget.pet.groomingConsentOn != null;
    final picked = await AppSheet.show<_ConsentAction>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppSheetAction(
            label: AppStrings.consentSend,
            onTap: () => Navigator.of(context).pop(_ConsentAction.send),
          ),
          AppSheetAction(
            label: AppStrings.consentSignHere,
            onTap: () => Navigator.of(context).pop(_ConsentAction.signHere),
          ),
          if (received) ...[
            AppSheetAction(
              label: AppStrings.groomingConsentAgain,
              onTap: () => Navigator.of(context).pop(_ConsentAction.again),
            ),
            AppSheetAction(
              label: AppStrings.groomingConsentClear,
              onTap: () => Navigator.of(context).pop(_ConsentAction.clear),
            ),
          ],
        ],
      ),
    );
    if (picked == null || !mounted) return;
    switch (picked) {
      case _ConsentAction.send:
        await _send(origin);
      case _ConsentAction.signHere:
        await context.push<void>('/consent/sign?pet_ids=${widget.pet.petId}');
      case _ConsentAction.again:
        await _set();
      case _ConsentAction.clear:
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
    final signed = widget.pet.groomingConsentVia == ConsentVia.signature;
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
                          : signed
                          ? AppStrings.groomingConsentSignedOn(receivedOn)
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
              else if (signed)
                AppButton(
                  key: const ValueKey('grooming-consent-signatures'),
                  label: AppStrings.consentViewSignatures,
                  onPressed: () => context.push('/pets/${widget.pet.petId}/signatures'),
                ),
              const SizedBox(width: AppSpacing.xs),
              Pressable(
                key: const ValueKey('grooming-consent-more'),
                semanticLabel: AppStrings.groomingConsentMore,
                onTap: _busy ? null : _openActions,
                child: const Padding(
                  padding: EdgeInsets.all(AppSpacing.sm),
                  child: Icon(Icons.more_horiz),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
