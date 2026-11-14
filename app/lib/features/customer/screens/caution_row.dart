import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
import '../state/customer_input.dart';

/// 보호자 탭의 주의 고객 줄(③-B 설계 3.4) — 표시가 있으면 사유와 기한, `···`에 [사유 고치기]·
/// [주의 표시 지우기]. 없으면 [표시하기]; 노쇼가 2번 이상이면 그 사실을 알리고 시트의 사유를
/// `노쇼 N번`으로 채워 연다(제안일 뿐 저절로 표시하지 않는다).
///
/// 이 표시는 이 매장만 본다 — 다른 매장과 공유하지 않는다. 사유는 로그·오류 문구에 싣지 않는다.
class CautionRow extends ConsumerStatefulWidget {
  const CautionRow({
    super.key,
    required this.customerId,
    required this.caution,
    required this.noShowCount,
  });

  final int customerId;
  final Caution? caution;
  final int noShowCount;

  /// 이 횟수부터 주의 표시를 제안한다.
  static const suggestFrom = 2;

  @override
  ConsumerState<CautionRow> createState() => _CautionRowState();
}

class _CautionRowState extends ConsumerState<CautionRow> {
  bool _busy = false;

  bool get _suggest =>
      widget.caution == null && widget.noShowCount >= CautionRow.suggestFrom;

  Future<void> _openSheet() => AppSheet.show<void>(
    context,
    builder: (context) => CautionSheet(
      customerId: widget.customerId,
      initial:
          widget.caution?.reason ??
          (_suggest ? AppStrings.cautionNoShowReason(widget.noShowCount) : ''),
    ),
  );

  Future<void> _openActions() async {
    final edit = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppSheetAction(
            label: AppStrings.cautionEdit,
            onTap: () => Navigator.of(context).pop(true),
          ),
          AppSheetAction(
            label: AppStrings.cautionClear,
            onTap: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
    if (edit == null || !mounted) return;
    if (edit) {
      await _openSheet();
    } else {
      await _clear();
    }
  }

  Future<void> _clear() async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _busy) return;
    setState(() => _busy = true);
    String? failure;
    try {
      await ref
          .read(customerCommandsProvider)
          .clearCaution(shopId, widget.customerId);
    } catch (e) {
      failure = messageFor(e);
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (failure != null) AppSnackBar.show(context, failure);
  }

  @override
  Widget build(BuildContext context) {
    final caution = widget.caution;
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
                      AppStrings.cautionLabel,
                      style: AppTypography.caption,
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    if (caution != null) ...[
                      Text(caution.reason, style: AppTypography.bodyStrong),
                      Text(
                        AppStrings.cautionUntil(caution.until),
                        style: AppTypography.caption,
                      ),
                    ] else
                      Text(
                        _suggest
                            ? AppStrings.cautionSuggest(widget.noShowCount)
                            : AppStrings.cautionNone,
                        style: AppTypography.body,
                      ),
                  ],
                ),
              ),
              if (caution == null)
                AppButton(
                  key: const ValueKey('caution-set'),
                  label: AppStrings.cautionSet,
                  onPressed: _openSheet,
                )
              else
                Pressable(
                  semanticLabel: AppStrings.cautionMore,
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

/// 주의 사유를 적는 시트 — 한 줄, 100자. 빈 글이면 [저장]이 눌리지 않는다. 저장하는 동안
/// 다시 누르지 못하고, 실패하면 시트가 남고 원인 문구가 보인다(사유는 문구에 싣지 않는다).
class CautionSheet extends ConsumerStatefulWidget {
  const CautionSheet({
    super.key,
    required this.customerId,
    required this.initial,
  });

  final int customerId;
  final String initial;

  static const maxLength = 100;

  @override
  ConsumerState<CautionSheet> createState() => _CautionSheetState();
}

class _CautionSheetState extends ConsumerState<CautionSheet> {
  late final _reason = TextEditingController(text: widget.initial);
  bool _busy = false;
  String? _errorText;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final shopId = ref.read(selectedShopIdProvider);
    final reason = cleanCautionReason(_reason.text);
    if (shopId == null || reason == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref
          .read(customerCommandsProvider)
          .setCaution(shopId, widget.customerId, reason);
      if (mounted) Navigator.of(context).pop();
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
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(AppStrings.cautionSheetTitle, style: AppTypography.body),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          key: const ValueKey('caution-reason'),
          controller: _reason,
          autofocus: true,
          maxLines: 1,
          enabled: !_busy,
          textInputAction: TextInputAction.done,
          inputFormatters: [
            LengthLimitingTextInputFormatter(CautionSheet.maxLength),
          ],
          decoration: const InputDecoration(
            hintText: AppStrings.cautionReasonHint,
          ),
          onChanged: (_) => setState(() {}),
          onSubmitted: (_) => _save(),
        ),
        const SizedBox(height: AppSpacing.sm),
        const Text(AppStrings.cautionSheetNote, style: AppTypography.caption),
        if (_errorText != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(_errorText!, style: AppTypography.caption),
          ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.save,
          filled: true,
          busy: _busy,
          onPressed: cleanCautionReason(_reason.text) == null ? null : _save,
        ),
      ],
    );
  }
}
