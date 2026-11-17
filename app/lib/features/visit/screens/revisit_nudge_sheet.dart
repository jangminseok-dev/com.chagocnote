import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/share_sheet.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/state/customer_commands.dart';
import '../api/revisit_models.dart';
import '../state/revisit_rules.dart';

/// [안내]의 미리 보기 시트(⑬ 설계 3.3) — 서버가 매장의 템플릿으로 **이미 써 둔** 글. 이번만 고쳐 보낼 수 있고,
/// [보내기] 한 번으로 공유 시트에 넘긴다. 공유 시트를 열었으면 그 아이에 안내한 날(오늘)을 적고 true.
/// 공유 시트를 열지 못하면 알리고 안내한 날을 적지 않는다. 사장이면 아래에 `안내 글 템플릿 바꾸기`.
/// 글(아이 이름이 들었다)을 로그·오류 문구에 남기지 않는다.
Future<bool> showRevisitNudgeSheet(BuildContext context, RevisitItem item) async =>
    await AppSheet.show<bool>(
      context,
      builder: (context) => _NudgeSheet(item: item),
    ) ==
    true;

class _NudgeSheet extends ConsumerStatefulWidget {
  const _NudgeSheet({required this.item});

  final RevisitItem item;

  @override
  ConsumerState<_NudgeSheet> createState() => _NudgeSheetState();
}

class _NudgeSheetState extends ConsumerState<_NudgeSheet> {
  late final _text = TextEditingController(text: widget.item.message);
  final _sendKey = GlobalKey();
  bool _busy = false;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _busy) return;
    final box = _sendKey.currentContext!.findRenderObject()! as RenderBox;
    final origin = box.localToGlobal(Offset.zero) & box.size;
    setState(() => _busy = true);
    try {
      await ref.read(shareSheetProvider).shareText(_text.text, origin: origin);
    } on Exception {
      if (mounted) {
        setState(() => _busy = false);
        AppSnackBar.show(context, AppStrings.revisitNudgeShareFailed);
      }
      return;
    }
    try {
      await ref.read(customerCommandsProvider).markRevisitNudged(shopId, widget.item.petId);
    } catch (e) {
      // 글은 이미 넘어갔다 — 안내한 날만 못 적었다. 알리고 닫는다.
      if (mounted) AppSnackBar.show(context, messageFor(e));
    }
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final canSend = _text.text.trim().isNotEmpty && !_busy;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '${AppStrings.revisitNudgeTitle} · ${widget.item.petName}',
          style: AppTypography.bodyStrong,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          key: const ValueKey('revisit-nudge-text'),
          controller: _text,
          minLines: 3,
          maxLines: 8,
          maxLength: revisitMessageMax * 2,
          keyboardType: TextInputType.multiline,
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.sm),
        AppButton(
          key: _sendKey,
          label: AppStrings.revisitNudgeSend,
          filled: true,
          busy: _busy,
          onPressed: canSend ? _send : null,
        ),
        if (ref.watch(isOwnerProvider))
          Center(
            child: Pressable(
              semanticLabel: AppStrings.revisitTemplateLink,
              onTap: () {
                Navigator.of(context).pop(false);
                context.push('/settings/revisit-message');
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                child: Text(
                  AppStrings.revisitTemplateLink,
                  style: AppTypography.caption.copyWith(decoration: TextDecoration.underline),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
