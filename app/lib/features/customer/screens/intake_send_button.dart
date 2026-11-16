import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/share_sheet.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../state/intake_commands.dart';

/// 문진표 링크를 보내는 버튼(⑪-C) — 누르기 한 번으로 링크를 만들고 공유 시트를 띄운다.
///
/// 둘 다 없으면 새 손님용, [customerId] 면 그 고객의 새 아이, [petId] 면 그 아이의 정보를 다시 받는다.
/// 공유 시트에는 주소만 넘긴다. 링크는 서버에 만들어져 있다 — 공유가 실패해도 보낸 서류에서 다시 공유한다.
/// **주소에는 토큰이 들어 있다 — 로그·오류 문구에 남기지 않는다.**
class IntakeSendButton extends ConsumerStatefulWidget {
  const IntakeSendButton({super.key, required this.label, this.customerId, this.petId});

  final String label;
  final int? customerId;
  final int? petId;

  @override
  ConsumerState<IntakeSendButton> createState() => _IntakeSendButtonState();
}

class _IntakeSendButtonState extends ConsumerState<IntakeSendButton> {
  bool _busy = false;

  Future<void> _send() async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _busy) return;
    // 공유 시트는 누른 버튼에 붙는다(아이패드) — 기다리기 전에 자리를 재 둔다.
    final box = context.findRenderObject()! as RenderBox;
    final origin = box.localToGlobal(Offset.zero) & box.size;
    setState(() => _busy = true);
    String? failure;
    try {
      final link = await ref
          .read(intakeCommandsProvider)
          .send(shopId, customerId: widget.customerId, petId: widget.petId);
      try {
        await ref.read(shareSheetProvider).shareText(link.url, origin: origin);
      } on Exception {
        failure = AppStrings.intakeShareFailed;
      }
    } catch (_) {
      failure = AppStrings.intakeSendFailed;
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (failure != null) AppSnackBar.show(context, failure);
  }

  @override
  Widget build(BuildContext context) {
    return AppButton(label: widget.label, busy: _busy, onPressed: _send);
  }
}
