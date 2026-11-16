import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/app_switch.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/intake_models.dart';
import '../state/intake_commands.dart';
import '../state/intake_providers.dart';

/// 고치는 중인 질문 한 줄.
class _Row {
  _Row({this.questionId, String label = '', this.required = false}) : label = TextEditingController(text: label);

  final int? questionId;
  final TextEditingController label;
  bool required;
}

/// 설정 → 서류 → 매장이 더한 질문(⑪ 설계 3.4) — 문진표에 우리 매장만 묻고 싶은 것을 다섯 개까지 더한다.
///
/// [저장]이 목록 전체를 보낸다 — 빠진 질문은 지운 것이다(이미 받은 답은 그 질문과 함께 남는다).
/// 빈 질문은 저장되지 않는다. 바꾸는 것은 사장만이고 직원에게는 읽기 전용이다.
class IntakeQuestionsScreen extends ConsumerStatefulWidget {
  const IntakeQuestionsScreen({super.key});

  static const saveKey = Key('intake-questions-save');
  static const addKey = Key('intake-questions-add');

  @override
  ConsumerState<IntakeQuestionsScreen> createState() => _IntakeQuestionsScreenState();
}

class _IntakeQuestionsScreenState extends ConsumerState<IntakeQuestionsScreen> {
  List<_Row>? _rows; // 읽은 뒤 한 번 채운다
  bool _dirty = false;
  bool _busy = false;
  String? _notice;

  @override
  void dispose() {
    for (final row in _rows ?? const <_Row>[]) {
      row.label.dispose();
    }
    super.dispose();
  }

  void _change(VoidCallback change) => setState(() {
    change();
    _dirty = true;
    _notice = null;
  });

  Future<void> _save() async {
    final shopId = ref.read(selectedShopIdProvider);
    final rows = _rows;
    if (shopId == null || rows == null || _busy) return;
    if (rows.any((row) => row.label.text.trim().isEmpty)) {
      setState(() => _notice = AppStrings.intakeQuestionEmpty);
      return;
    }
    setState(() {
      _busy = true;
      _notice = null;
    });
    try {
      await ref.read(intakeCommandsProvider).updateQuestions(shopId, [
        for (final row in rows)
          IntakeQuestion(questionId: row.questionId, label: row.label.text.trim(), required: row.required),
      ]);
      if (!mounted) return;
      AppSnackBar.show(context, AppStrings.intakeQuestionsSaved);
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _notice = messageFor(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider);
    final questions = shopId == null
        ? const AsyncValue<List<IntakeQuestion>>.loading()
        : ref.watch(intakeQuestionsProvider(shopId));
    final canEdit = ref.watch(isOwnerProvider);
    return Scaffold(
      key: ScreenKeys.intakeQuestions,
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
                    Text(AppStrings.intakeQuestionsTitle, style: AppTypography.titleKo),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<List<IntakeQuestion>>(
                  value: questions,
                  onRetry: () => ref.invalidate(intakeQuestionsProvider(shopId!)),
                  builder: (loaded) {
                    // 처음 읽은 것으로 한 번만 채운다 — 저장이 다시 읽게 해도 고치던 줄이 날아가지 않는다.
                    final rows = _rows ??= [
                      for (final q in loaded) _Row(questionId: q.questionId, label: q.label, required: q.required),
                    ];
                    return _body(rows, canEdit: canEdit);
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(List<_Row> rows, {required bool canEdit}) {
    final full = rows.length >= intakeQuestionMax;
    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
      children: [
        Text(
          canEdit ? AppStrings.formIntakeQuestionsHint : AppStrings.reportSettingsOwnerOnly,
          style: AppTypography.caption,
        ),
        const SizedBox(height: AppSpacing.md),
        if (rows.isEmpty) const Text(AppStrings.intakeQuestionsNone, style: AppTypography.body),
        for (final (index, row) in rows.indexed)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    key: ValueKey('intake-question-$index'),
                    controller: row.label,
                    readOnly: !canEdit,
                    maxLength: intakeQuestionLabelMax,
                    decoration: const InputDecoration(hintText: AppStrings.intakeQuestionHint, counterText: ''),
                    onChanged: (_) => _change(() {}),
                  ),
                  Row(
                    children: [
                      const ExcludeSemantics(
                        child: Text(AppStrings.intakeQuestionRequired, style: AppTypography.caption),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      AppSwitch(
                        key: ValueKey('intake-question-required-$index'),
                        value: row.required,
                        semanticLabel: AppStrings.intakeQuestionRequired,
                        onChanged: canEdit ? (on) => _change(() => row.required = on) : null,
                      ),
                      const Spacer(),
                      if (canEdit)
                        Pressable(
                          key: ValueKey('intake-question-remove-$index'),
                          semanticLabel: AppStrings.intakeQuestionRemove,
                          onTap: () => _change(() => rows.removeAt(index).label.dispose()),
                          child: const Padding(
                            padding: EdgeInsets.all(AppSpacing.sm),
                            child: Icon(Icons.close, size: 20),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        if (canEdit) ...[
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            key: IntakeQuestionsScreen.addKey,
            label: AppStrings.intakeQuestionAdd,
            onPressed: full ? null : () => _change(() => rows.add(_Row())),
          ),
          if (full)
            const Padding(
              padding: EdgeInsets.only(top: AppSpacing.sm),
              child: Text(AppStrings.intakeQuestionFull, style: AppTypography.caption),
            ),
          if (_notice != null)
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.md),
              child: Semantics(liveRegion: true, child: Text(_notice!, style: AppTypography.bodyStrong)),
            ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            key: IntakeQuestionsScreen.saveKey,
            label: AppStrings.save,
            filled: true,
            busy: _busy,
            onPressed: _dirty ? _save : null,
          ),
        ],
      ],
    );
  }
}
