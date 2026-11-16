import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_switch.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/consent_models.dart';
import '../api/form_settings_models.dart';
import '../api/intake_models.dart';
import '../state/form_settings_commands.dart';
import '../state/form_settings_providers.dart';
import '../state/intake_providers.dart';
import 'consent_sign_screen.dart';

/// 설정 → 서류(⑪ 설계 3.6 의 6) — 동의서에 적힌 글, 보호자에게 보내는 글, 링크 기간·노령 나이·동의 기한.
///
/// 아무것도 건드리지 않아도 기본값으로 돈다. 줄의 이름은 일어나는 일이고 줄 아래에 무슨 일이 생기는지 적는다.
/// 기준값은 [저장] 없이 누르면 바로 다섯 칸 전체를 보낸다 — 낙관적으로 그리지 않고 다시 읽은 값으로 그린다.
/// 바꾸는 것은 사장만이고 직원에게는 읽기 전용이다.
class FormSettingsScreen extends ConsumerStatefulWidget {
  const FormSettingsScreen({super.key});

  @override
  ConsumerState<FormSettingsScreen> createState() => _FormSettingsScreenState();
}

class _FormSettingsScreenState extends ConsumerState<FormSettingsScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  Future<void> _set(FormSettings changed) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    // 화면의 값이 방금 읽은 것이 아니면 누르지 않은 것으로 친다 — 낡은 값 위에 덮어 보내지 않는다.
    final now = ref.read(formSettingsProvider(shopId));
    if (now.isLoading || now.hasError) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    String? error;
    try {
      await ref.read(formSettingsCommandsProvider).update(shopId, changed);
    } catch (e) {
      error = messageFor(e);
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _errorText = error;
    });
  }

  /// 칩에 없는 값을 직접 정한다. 범위 밖이면 보내지 않고 그 자리에서 말한다.
  Future<void> _custom(String field, String label, int now, (int, int) range, FormSettings Function(int) apply) async {
    final value = await AppSheet.show<int>(
      context,
      builder: (_) => _NumberSheet(label: label, initial: now, range: range),
    );
    if (value != null && value != now) await _set(apply(value));
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final settings = shopId == null
        ? const AsyncValue<FormSettings>.loading()
        : ref.watch(formSettingsProvider(shopId));
    final texts = shopId == null
        ? const AsyncValue<List<ConsentTextPart>>.loading()
        : ref.watch(consentTextsProvider(shopId));
    final questions = shopId == null
        ? const AsyncValue<List<IntakeQuestion>>.loading()
        : ref.watch(intakeQuestionsProvider(shopId));
    final canEdit = ref.watch(isOwnerProvider);
    return Scaffold(
      key: ScreenKeys.formSettings,
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
                    Text(AppStrings.formSettingsTitle, style: AppTypography.titleKo),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<FormSettings>(
                  value: settings,
                  onRetry: () => ref.invalidate(formSettingsProvider(shopId!)),
                  builder: (data) => _body(data, texts.value ?? const [], questions.value?.length ?? 0, canEdit: canEdit),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(FormSettings shown, List<ConsentTextPart> texts, int questions, {required bool canEdit}) {
    final notice = canEdit ? _errorText : AppStrings.reportSettingsOwnerOnly;
    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
      children: [
        if (notice != null)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: Text(notice, key: const ValueKey('form-settings-notice'), style: AppTypography.caption),
          ),
        const _Label(AppStrings.formSectionTexts),
        AppCard(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.xs),
          child: Column(
            children: [
              for (final part in ConsentPart.values)
                _LinkRow(
                  title: consentPartTitle(part),
                  hint: switch (part) {
                    ConsentPart.basic => AppStrings.formPartWhenBasic,
                    ConsentPart.senior => AppStrings.formPartWhenSenior(shown.seniorAge),
                    ConsentPart.condition => AppStrings.formPartWhenCondition,
                  },
                  edited: texts.any((t) => t.part == part && t.edited),
                  onTap: () => context.push('/settings/forms/text/${part.name}'),
                ),
            ],
          ),
        ),
        const _Hint(AppStrings.formSectionTextsHint),
        const _Label(AppStrings.formSectionMessages),
        AppCard(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.xs),
          child: Column(
            children: [
              _LinkRow(
                title: AppStrings.bundlePartReservation,
                edited: shown.reservationText != shown.defaults.reservationText,
                onTap: () => context.push('/settings/forms/message/reservation'),
              ),
              _LinkRow(
                title: AppStrings.bundlePartConsent,
                edited: shown.consentText != shown.defaults.consentText,
                onTap: () => context.push('/settings/forms/message/consent'),
              ),
            ],
          ),
        ),
        const _Hint(AppStrings.formSectionMessagesHint),
        const _Label(AppStrings.formSectionIntake),
        AppCard(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final code in intakeHideable)
                Row(
                  children: [
                    // 이름은 스위치가 읽는다 — 글자를 한 번 더 읽지 않게 뺀다.
                    Expanded(
                      child: ExcludeSemantics(
                        child: Text(AppStrings.intakeFieldNames[code] ?? code, style: AppTypography.body),
                      ),
                    ),
                    AppSwitch(
                      key: ValueKey('intake-field-$code'),
                      value: !shown.intakeHidden.contains(code),
                      semanticLabel: AppStrings.intakeFieldNames[code] ?? code,
                      onChanged: canEdit
                          ? (on) => _set(shown.copyWith(intakeHidden: [
                              for (final other in intakeHideable)
                                if (other == code ? !on : shown.intakeHidden.contains(other)) other,
                            ]))
                          : null,
                    ),
                  ],
                ),
              const SizedBox(height: AppSpacing.xs),
              // 끌 수 없는 칸과 그 까닭 — 누구의 답인지, 어떤 동의가 필요한지가 여기서 정해진다.
              const Text(AppStrings.formIntakeAlways, style: AppTypography.caption),
              _LinkRow(
                title: AppStrings.formIntakeQuestions(questions),
                hint: AppStrings.formIntakeQuestionsHint,
                edited: false,
                onTap: () => context.push('/settings/forms/questions'),
              ),
            ],
          ),
        ),
        const _Hint(AppStrings.formIntakeHiddenHint),
        _Choice(
          field: 'link_days',
          label: AppStrings.formLinkDaysLabel,
          hint: AppStrings.formLinkDaysHint(shown.linkDays),
          value: shown.linkDays,
          choices: const [7, 14, 30],
          text: AppStrings.formDays,
          onPick: canEdit ? (v) => _set(shown.copyWith(linkDays: v)) : null,
          onCustom: canEdit
              ? () => _custom(
                  'link_days',
                  AppStrings.formLinkDaysLabel,
                  shown.linkDays,
                  linkDaysRange,
                  (v) => shown.copyWith(linkDays: v),
                )
              : null,
        ),
        _Choice(
          field: 'senior_age',
          label: AppStrings.formSeniorAgeLabel,
          hint: AppStrings.formSeniorAgeHint(shown.seniorAge),
          value: shown.seniorAge,
          choices: const [8, 10, 12],
          text: AppStrings.formAge,
          onPick: canEdit ? (v) => _set(shown.copyWith(seniorAge: v)) : null,
          onCustom: canEdit
              ? () => _custom(
                  'senior_age',
                  AppStrings.formSeniorAgeLabel,
                  shown.seniorAge,
                  seniorAgeRange,
                  (v) => shown.copyWith(seniorAge: v),
                )
              : null,
        ),
        _Choice(
          field: 'consent_days',
          label: AppStrings.formConsentDaysLabel,
          hint: AppStrings.formConsentDaysHint(shown.consentDays),
          value: shown.consentDays,
          choices: const [180, 365, 730],
          text: AppStrings.formPeriod,
          onPick: canEdit ? (v) => _set(shown.copyWith(consentDays: v)) : null,
          onCustom: canEdit
              ? () => _custom(
                  'consent_days',
                  AppStrings.formConsentDaysLabel,
                  shown.consentDays,
                  consentDaysRange,
                  (v) => shown.copyWith(consentDays: v),
                )
              : null,
        ),
        _Choice(
          field: 'intake_keep_days',
          label: AppStrings.formIntakeKeepLabel,
          hint: AppStrings.formIntakeKeepHint(shown.intakeKeepDays),
          value: shown.intakeKeepDays,
          choices: const [7, 30, 90],
          text: AppStrings.formDays,
          onPick: canEdit ? (v) => _set(shown.copyWith(intakeKeepDays: v)) : null,
          onCustom: canEdit
              ? () => _custom(
                  'intake_keep_days',
                  AppStrings.formIntakeKeepLabel,
                  shown.intakeKeepDays,
                  intakeKeepDaysRange,
                  (v) => shown.copyWith(intakeKeepDays: v),
                )
              : null,
        ),
      ],
    );
  }
}

class _Label extends StatelessWidget {
  const _Label(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: AppSpacing.lg, bottom: AppSpacing.sm),
    child: Text(text, style: AppTypography.caption),
  );
}

class _Hint extends StatelessWidget {
  const _Hint(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: AppSpacing.sm),
    child: Text(text, style: AppTypography.caption),
  );
}

/// 누르면 고치는 화면으로 가는 줄 — 이름, 언제 쓰이는지 한 줄, 고쳤으면 `고침`.
class _LinkRow extends StatelessWidget {
  const _LinkRow({required this.title, required this.edited, required this.onTap, this.hint});

  final String title;
  final String? hint;
  final bool edited;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: [title, ?hint, if (edited) AppStrings.formEdited].join(', '),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        child: ExcludeSemantics(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppTypography.body),
                    if (hint != null) Text(hint!, style: AppTypography.caption),
                  ],
                ),
              ),
              if (edited) const Text(AppStrings.formEdited, style: AppTypography.caption),
              const SizedBox(width: AppSpacing.sm),
              const Icon(Icons.chevron_right, color: AppColors.secondary),
            ],
          ),
        ),
      ),
    );
  }
}

/// 기준값 한 줄 — 흔한 값의 칩과 [직접]. 지금 값이 칩에 없으면 그 값의 칩이 하나 더 보인다.
class _Choice extends StatelessWidget {
  const _Choice({
    required this.field,
    required this.label,
    required this.hint,
    required this.value,
    required this.choices,
    required this.text,
    required this.onPick,
    required this.onCustom,
  });

  final String field;
  final String label;
  final String hint;
  final int value;
  final List<int> choices;
  final String Function(int) text;
  final void Function(int)? onPick;
  final VoidCallback? onCustom;

  @override
  Widget build(BuildContext context) {
    final shown = [...choices, if (!choices.contains(value)) value]..sort();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _Label(label),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: [
            for (final choice in shown)
              AppChoiceChip(
                label: text(choice),
                selected: choice == value,
                // 이미 고른 값은 눌리지 않는다(다시 보내지 않는다).
                onTap: onPick == null || choice == value ? null : () => onPick!(choice),
              ),
            AppChoiceChip(
              key: ValueKey('form-custom-$field'),
              label: AppStrings.formCustom,
              selected: false,
              onTap: onCustom,
            ),
          ],
        ),
        _Hint(hint),
      ],
    );
  }
}

/// 숫자 하나를 직접 정하는 시트. 범위 밖이면 닫지 않고 그 자리에서 말한다.
class _NumberSheet extends StatefulWidget {
  const _NumberSheet({required this.label, required this.initial, required this.range});

  final String label;
  final int initial;
  final (int, int) range;

  @override
  State<_NumberSheet> createState() => _NumberSheetState();
}

class _NumberSheetState extends State<_NumberSheet> {
  late final _input = TextEditingController(text: '${widget.initial}');
  bool _outOfRange = false;

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  void _save() {
    final value = int.tryParse(_input.text.trim());
    final (low, high) = widget.range;
    if (value == null || value < low || value > high) {
      setState(() => _outOfRange = true);
      return;
    }
    Navigator.of(context).pop(value);
  }

  @override
  Widget build(BuildContext context) {
    final (low, high) = widget.range;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(widget.label, style: AppTypography.bodyStrong),
        TextField(
          key: const ValueKey('form-custom-input'),
          controller: _input,
          autofocus: true,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(4)],
          onChanged: (_) => setState(() => _outOfRange = false),
          onSubmitted: (_) => _save(),
        ),
        const SizedBox(height: AppSpacing.xs),
        Semantics(
          liveRegion: _outOfRange,
          child: Text(
            AppStrings.formRangeNotice(low, high),
            style: _outOfRange ? AppTypography.bodyStrong : AppTypography.caption,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AppButton(key: const ValueKey('form-custom-save'), label: AppStrings.save, filled: true, onPressed: _save),
      ],
    );
  }
}
