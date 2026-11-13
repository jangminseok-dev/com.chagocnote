import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/time/shop_time.dart';
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
import '../state/customer_commands.dart';
import '../state/customer_providers.dart';

/// 보호자 탭의 한 줄 — 이 고객 카드가 보호자 계정에 이어져 있으면 "보호자 계정
/// 연결됨 · 11월 13일"과 `···`의 [연결 끊기](설계 ⑦ 4.5).
///
/// 고객 상세와 따로 읽는다. 읽는 중·읽지 못함·이어지지 않음이면 줄이 없다 —
/// 탭의 본문이 아니라 덧붙는 표시라 실패를 알리지 않는다. 매장에는 여부와
/// 이은 날만 온다(보호자가 누구인지는 받지도 그리지도 않는다). 끊기는 직원도 한다.
class GuardianLinkRow extends ConsumerStatefulWidget {
  const GuardianLinkRow({super.key, required this.customerId});

  final int customerId;

  @override
  ConsumerState<GuardianLinkRow> createState() => _GuardianLinkRowState();
}

class _GuardianLinkRowState extends ConsumerState<GuardianLinkRow> {
  bool _busy = false;

  Future<void> _openActions(int shopId) async {
    final end = await AppSheet.show<bool>(
      context,
      builder: (context) => AppSheetAction(
        label: AppStrings.endGuardianLink,
        onTap: () => Navigator.of(context).pop(true),
      ),
    );
    if (end != true || !mounted) return;
    final confirmed = await _confirm();
    if (confirmed != true || !mounted) return;
    await _end(shopId);
  }

  Future<bool?> _confirm() {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            AppStrings.endGuardianLinkConfirm,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.endGuardianLink,
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

  /// 연결을 끊는다. 도는 동안 `···`를 막는다. 줄은 명령이 연결을 다시 읽게 해
  /// 스스로 사라진다(실패면 남는다).
  Future<void> _end(int shopId) async {
    if (_busy) return;
    setState(() => _busy = true);
    String message;
    try {
      await ref
          .read(customerCommandsProvider)
          .endGuardianLink(shopId, widget.customerId);
      message = AppStrings.guardianLinkEnded;
    } catch (e) {
      message = messageFor(e);
    }
    // 끊는 도중 화면을 떠났으면 아무것도 띄우지 않는다.
    if (!mounted) return;
    setState(() => _busy = false);
    AppSnackBar.show(context, message);
  }

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider);
    if (shopId == null) return const SizedBox.shrink();
    final link = ref
        .watch(
          guardianLinkProvider((shopId: shopId, customerId: widget.customerId)),
        )
        .value;
    if (link == null || !link.linked) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: SizedBox(
        width: double.infinity,
        child: AppCard(
          child: Row(
            children: [
              Expanded(
                child: Text(_label(link.linkedAt), style: AppTypography.body),
              ),
              Pressable(
                semanticLabel: AppStrings.guardianLinkMore,
                onTap: _busy ? null : () => _openActions(shopId),
                child: const Icon(Icons.more_horiz),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 이은 날을 붙인 글자. 날짜가 없거나 읽지 못하면 날짜 없이 보인다.
String _label(String? linkedAt) {
  if (linkedAt == null) return AppStrings.guardianLinked;
  try {
    final wall = ShopTime.parse(linkedAt).wall;
    return AppStrings.guardianLinkedOn(wall.month, wall.day);
  } on FormatException {
    return AppStrings.guardianLinked;
  }
}
