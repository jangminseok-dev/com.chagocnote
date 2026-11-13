import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../state/sales_commands.dart';
import '../state/sales_rules.dart';

/// 이번 달 목표를 정하는 시트(설계 ⑧ 3.5). 저장하면 닫히고 요약이 다시 읽힌다. 실패하면 남아서 원인을 보인다.
abstract final class SalesGoalSheet {
  static Future<void> show(BuildContext context, {required int shopId, required int? current}) =>
      AppSheet.show<void>(
        context,
        builder: (context) => _GoalForm(shopId: shopId, current: current),
      );
}

class _GoalForm extends ConsumerStatefulWidget {
  const _GoalForm({required this.shopId, required this.current});

  final int shopId;
  final int? current;

  @override
  ConsumerState<_GoalForm> createState() => _GoalFormState();
}

class _GoalFormState extends ConsumerState<_GoalForm> {
  late final _amount = TextEditingController(text: widget.current == null ? '' : '${widget.current}');
  bool _busy = false;
  String? _errorText;

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  void _save() {
    final int? amount;
    try {
      amount = parseGoal(_amount.text);
    } on FormatException {
      setState(() => _errorText = AppStrings.salesGoalTooBig);
      return;
    }
    _send(amount);
  }

  /// 쓰기 하나. 도는 동안 다시 누른 것은 받지 않는다.
  Future<void> _send(int? amount) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref.read(salesCommandsProvider).setGoal(widget.shopId, amount);
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
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(AppStrings.salesGoalTitle, style: AppTypography.titleKo),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: _amount,
          autofocus: true,
          enabled: !_busy,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(9),
          ],
          decoration: InputDecoration(
            labelText: AppStrings.salesGoalLabel,
            hintText: AppStrings.salesGoalHint,
            suffixText: AppStrings.wonUnit,
            errorText: _errorText,
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(label: AppStrings.save, filled: true, busy: _busy, onPressed: _save),
        if (widget.current != null) ...[
          const SizedBox(height: AppSpacing.sm),
          AppButton(label: AppStrings.salesGoalClear, onPressed: _busy ? null : () => _send(null)),
        ],
      ],
    );
  }
}
