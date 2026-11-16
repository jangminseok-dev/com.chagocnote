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
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/consent_models.dart';
import '../api/form_settings_models.dart';
import '../state/form_settings_commands.dart';
import '../state/form_settings_providers.dart';
import 'consent_sign_screen.dart';

final _slot = RegExp(r'\{[^{}\s]*\}');

/// 보내는 글을 예시 값으로 채운 모습 — 서버의 조립과 같은 자리 이름을 쓴다(실제 값은 예약마다 다르다).
String sampleMessage(String template) => template
    .replaceAll('{매장}', AppStrings.formSampleShop)
    .replaceAll('{아이}', AppStrings.formSamplePet)
    .replaceAll('{날짜}', AppStrings.formSampleDay)
    .replaceAll('{시간}', AppStrings.formSampleTime)
    .replaceAll('{메뉴}', AppStrings.formSampleMenu)
    .replaceAll(linkSlot, AppStrings.formSampleLink);

/// 보내는 글의 규칙 — 서버와 같다(어긋나면 422). 막는 까닭을 돌려주고, 괜찮으면 `null`.
String? messageNotice(String text, List<String> slots) {
  if (text.trim().isEmpty) return AppStrings.formTextEmpty;
  if (_slot.allMatches(text).any((m) => !slots.contains(m.group(0)))) return AppStrings.formUnknownSlot;
  if (slots.contains(linkSlot) && !text.contains(linkSlot)) return AppStrings.formLinkSlotMissing;
  return null;
}

/// 설정 → 서류 → 동의서의 토막 하나(⑪ 설계 3.2). 고치면 새 판이 쌓이고 다음 서명부터 이 글이다 —
/// 이미 받은 동의는 그대로다. 비워 저장할 수 없고 기본 글로 되돌릴 수 있다.
class ConsentTextEditScreen extends ConsumerWidget {
  const ConsentTextEditScreen({super.key, required this.partName});

  final String partName;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopId = ref.watch(selectedShopIdProvider);
    final part = ConsentPart.values.where((p) => p.name == partName).firstOrNull;
    final texts = shopId == null || part == null
        ? const AsyncValue<List<ConsentTextPart>>.loading()
        : ref.watch(consentTextsProvider(shopId));
    return _Frame<List<ConsentTextPart>>(
      title: part == null ? AppStrings.formSectionTexts : consentPartTitle(part),
      value: texts,
      onRetry: () => ref.invalidate(consentTextsProvider(shopId!)),
      builder: (parts) {
        final now = parts.where((p) => p.part == part).firstOrNull;
        if (now == null) return const SizedBox.shrink();
        final commands = ref.read(formSettingsCommandsProvider);
        return FormTextEdit(
          initial: now.body,
          maxLength: consentBodyMax,
          canEdit: ref.watch(isOwnerProvider),
          notice: (text) => text.trim().isEmpty ? AppStrings.formTextEmpty : null,
          preview: (text) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(consentPartTitle(now.part), style: AppTypography.bodyStrong),
              for (final line in text.split('\n'))
                if (line.trim().isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.sm),
                    child: Text(line.trim(), style: AppTypography.body),
                  ),
            ],
          ),
          savedMessage: AppStrings.formTextSaved,
          onSave: (text) => commands.updateText(shopId!, now.part, text),
          onReset: now.edited ? () => commands.updateText(shopId!, now.part, null) : null,
        );
      },
    );
  }
}

/// 설정 → 서류 → 보호자에게 보내는 글(⑪ 설계 3.5) — 예약 안내(`reservation`)·동의서(`consent`)의 템플릿.
/// 자리(`{날짜}` 등)는 칩을 눌러 넣는다. 동의서 글에는 `{링크}` 가 꼭 있어야 한다.
class BundleTextEditScreen extends ConsumerWidget {
  const BundleTextEditScreen({super.key, required this.kind});

  final String kind;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopId = ref.watch(selectedShopIdProvider);
    final consent = kind == 'consent';
    final settings = shopId == null
        ? const AsyncValue<FormSettings>.loading()
        : ref.watch(formSettingsProvider(shopId));
    final slots = consent ? consentSlots : reservationSlots;
    return _Frame<FormSettings>(
      title: consent ? AppStrings.bundlePartConsent : AppStrings.bundlePartReservation,
      value: settings,
      onRetry: () => ref.invalidate(formSettingsProvider(shopId!)),
      builder: (now) {
        final commands = ref.read(formSettingsCommandsProvider);
        final text = consent ? now.consentText : now.reservationText;
        final fallback = consent ? now.defaults.consentText : now.defaults.reservationText;
        Future<void> save(String value) => commands.update(
          shopId!,
          consent ? now.copyWith(consentText: value) : now.copyWith(reservationText: value),
        );
        return FormTextEdit(
          initial: text,
          maxLength: bundleTextMax,
          canEdit: ref.watch(isOwnerProvider),
          slots: slots,
          notice: (value) => messageNotice(value, slots),
          preview: (value) => Text(sampleMessage(value), style: AppTypography.body),
          savedMessage: AppStrings.formMessageSaved,
          onSave: save,
          onReset: text == fallback ? null : () => save(fallback),
        );
      },
    );
  }
}

class _Frame<T> extends StatelessWidget {
  const _Frame({required this.title, required this.value, required this.onRetry, required this.builder});

  final String title;
  final AsyncValue<T> value;
  final VoidCallback onRetry;
  final Widget Function(T) builder;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: ScreenKeys.formTextEdit,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.sm),
                child: Row(
                  children: [
                    // 뒤로 가기는 화면의 PopScope 를 거친다 — 고친 글이 있으면 묻는다.
                    AppBackButton(onTap: () => Navigator.of(context).maybePop()),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(child: Text(title, style: AppTypography.titleKo)),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<T>(value: value, onRetry: onRetry, builder: builder),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 글 하나를 고치는 몸통 — 글 칸, 넣을 수 있는 자리, **보호자가 받는 모습**, [저장], [기본 글로 되돌리기].
///
/// 저장에 성공하면 화면을 닫는다. 실패하면 적은 글이 남고 그 자리에서 말한다. 고친 글이 있으면 뒤로 가기 전에 묻는다.
/// [canEdit] 이 아니면(직원) 읽기 전용이다.
class FormTextEdit extends StatefulWidget {
  const FormTextEdit({
    super.key,
    required this.initial,
    required this.maxLength,
    required this.canEdit,
    required this.notice,
    required this.preview,
    required this.savedMessage,
    required this.onSave,
    required this.onReset,
    this.slots = const [],
    this.slotLabel,
  });

  static const inputKey = Key('form-text-input');
  static const previewKey = Key('form-text-preview');
  static const saveKey = Key('form-text-save');
  static const resetKey = Key('form-text-reset');
  static const noticeKey = Key('form-text-notice');

  final String initial;
  final int maxLength;
  final bool canEdit;
  final List<String> slots;

  /// 칩의 이름표(⑬ — `{아이}` 를 `아이 이름` 으로). 없으면 자리 글 그대로다.
  final String Function(String slot)? slotLabel;

  /// 저장을 막는 까닭. 괜찮으면 `null`.
  final String? Function(String text) notice;
  final Widget Function(String text) preview;
  final String savedMessage;
  final Future<void> Function(String text) onSave;

  /// 기본 글로 되돌린다. 이미 기본 글이면 `null` — 버튼이 없다.
  final Future<void> Function()? onReset;

  @override
  State<FormTextEdit> createState() => _FormTextEditState();
}

class _FormTextEditState extends State<FormTextEdit> {
  late final _input = TextEditingController(text: widget.initial);
  bool _busy = false;
  String? _errorText;

  bool get _dirty => _input.text != widget.initial;

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _errorText = messageFor(e);
        });
      }
      return;
    }
    if (!mounted) return;
    AppSnackBar.show(context, widget.savedMessage);
    // 저장이 끝났다 — 물어보지 않고 닫는다.
    setState(() => _left = true);
    Navigator.of(context).pop();
  }

  bool _left = false;

  void _insert(String slot) {
    final selection = _input.selection;
    final text = _input.text;
    final at = selection.isValid ? selection.start : text.length;
    final end = selection.isValid ? selection.end : text.length;
    _input.value = TextEditingValue(
      text: text.replaceRange(at, end, slot),
      selection: TextSelection.collapsed(offset: at + slot.length),
    );
    setState(() => _errorText = null);
  }

  Future<void> _askLeave() async {
    final leave = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Text(AppStrings.formLeaveAsk, style: AppTypography.bodyStrong),
          ),
          AppSheetAction(label: AppStrings.formLeave, onTap: () => Navigator.of(context).pop(true)),
          AppSheetAction(label: AppStrings.formLeaveStay, onTap: () => Navigator.of(context).pop(false)),
        ],
      ),
    );
    if (leave == true && mounted) {
      setState(() => _left = true);
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = _input.text;
    final blocked = widget.notice(text);
    final notice = _errorText ?? (_dirty ? blocked : null);
    return PopScope(
      canPop: _left || !_dirty,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _askLeave();
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
        children: [
          if (!widget.canEdit)
            const Padding(
              padding: EdgeInsets.only(bottom: AppSpacing.md),
              child: Text(AppStrings.reportSettingsOwnerOnly, style: AppTypography.caption),
            ),
          TextField(
            key: FormTextEdit.inputKey,
            controller: _input,
            readOnly: !widget.canEdit,
            minLines: 4,
            maxLines: null,
            maxLength: widget.maxLength,
            keyboardType: TextInputType.multiline,
            onChanged: (_) => setState(() => _errorText = null),
          ),
          if (widget.canEdit && widget.slots.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.sm),
            const Text(AppStrings.formSlotsLabel, style: AppTypography.caption),
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                for (final slot in widget.slots)
                  AppChoiceChip(
                    key: ValueKey('form-slot-$slot'),
                    label: widget.slotLabel?.call(slot) ?? slot,
                    selected: false,
                    onTap: () => _insert(slot),
                  ),
              ],
            ),
          ],
          const SizedBox(height: AppSpacing.lg),
          const Text(AppStrings.formPreviewLabel, style: AppTypography.caption),
          const SizedBox(height: AppSpacing.sm),
          AppCard(
            key: FormTextEdit.previewKey,
            child: SizedBox(width: double.infinity, child: widget.preview(text)),
          ),
          if (notice != null)
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.md),
              child: Semantics(
                liveRegion: true,
                child: Text(notice, key: FormTextEdit.noticeKey, style: AppTypography.bodyStrong),
              ),
            ),
          if (widget.canEdit) ...[
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              key: FormTextEdit.saveKey,
              label: AppStrings.save,
              filled: true,
              busy: _busy,
              onPressed: _dirty && blocked == null ? () => _run(() => widget.onSave(text)) : null,
            ),
            if (widget.onReset != null) ...[
              const SizedBox(height: AppSpacing.sm),
              AppButton(
                key: FormTextEdit.resetKey,
                label: AppStrings.formTextReset,
                onPressed: _busy ? null : () => _run(widget.onReset!),
              ),
            ],
          ],
        ],
      ),
    );
  }
}
