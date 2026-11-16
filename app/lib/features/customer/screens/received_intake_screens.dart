import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/today_provider.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/customer_models.dart';
import '../api/intake_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_input.dart';
import '../state/customer_providers.dart';
import '../state/intake_commands.dart';
import '../state/intake_prefill.dart';
import '../state/intake_providers.dart';
import 'customer_labels.dart';
import 'pet_form.dart';

/// 고객 탭 목록 위의 `받은 문진표 N`. 받은 답이 있을 때만 보인다(읽는 중·읽기 실패·0건이면 줄이 없다).
class ReceivedIntakeEntry extends ConsumerWidget {
  const ReceivedIntakeEntry({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopId = ref.watch(selectedShopIdProvider);
    if (shopId == null) return const SizedBox.shrink();
    final answers = ref.watch(receivedIntakeProvider(shopId));
    // 다시 읽기가 실패했을 때도 없다 — value 는 실패해도 이전 값을 들고 있다.
    final count = answers.hasError ? 0 : (answers.value?.length ?? 0);
    if (count == 0) return const SizedBox.shrink();
    final label = AppStrings.receivedIntakeEntry(count);
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.xs, AppSpacing.lg, 0),
      child: Pressable(
        semanticLabel: label,
        onTap: () => context.push('/intake-answers'),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
          child: ExcludeSemantics(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label, style: AppTypography.bodyStrong),
                const Icon(Icons.chevron_right, size: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Frame extends StatelessWidget {
  const _Frame({required this.screenKey, required this.title, required this.child});

  final Key screenKey;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: screenKey,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.sm),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(child: Text(title, style: AppTypography.titleKo)),
                  ],
                ),
              ),
              Expanded(child: child),
            ],
          ),
        ),
      ),
    );
  }
}

/// 받은 문진표의 목록(⑪ 설계 3.6 의 4) — 아직 등록하지 않은 답. 줄을 누르면 한 장이다.
class ReceivedIntakeScreen extends ConsumerWidget {
  const ReceivedIntakeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopId = ref.watch(selectedShopIdProvider);
    final answers = shopId == null
        ? const AsyncValue<List<IntakeAnswerItem>>.loading()
        : ref.watch(receivedIntakeProvider(shopId));
    return _Frame(
      screenKey: ScreenKeys.receivedIntake,
      title: AppStrings.receivedIntakeTitle,
      child: AsyncBody<List<IntakeAnswerItem>>(
        value: answers,
        onRetry: () => ref.invalidate(receivedIntakeProvider(shopId!)),
        onRefresh: () => ref.refresh(receivedIntakeProvider(shopId!).future),
        builder: (items) => items.isEmpty
            ? const Center(child: Text(AppStrings.receivedIntakeEmpty, style: AppTypography.caption))
            : ListView(
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
                children: [
                  for (final item in items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                      child: _row(context, item),
                    ),
                ],
              ),
      ),
    );
  }

  Widget _row(BuildContext context, IntakeAnswerItem item) {
    final name = item.petName ?? AppStrings.intakeNoName;
    final tag = switch (item.mode) {
      IntakeMode.update => AppStrings.intakeModeUpdate,
      IntakeMode.addPet => AppStrings.intakeModeAddPet,
      IntakeMode.newGuest => item.matchedCustomer == null ? null : AppStrings.intakeMatched,
    };
    final meta = AppStrings.receivedIntakeMeta(item.guardianName ?? item.matchedCustomer?.name, item.submittedOn);
    return Pressable(
      key: ValueKey('intake-answer-${item.answerId}'),
      semanticLabel: [name, meta, ?tag].join(', '),
      onTap: () => context.push('/intake-answers/${item.answerId}'),
      child: AppCard(
        child: ExcludeSemantics(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: AppTypography.bodyStrong),
                    const SizedBox(height: AppSpacing.xs),
                    Text(meta, style: AppTypography.caption),
                  ],
                ),
              ),
              if (tag != null) Text(tag, style: AppTypography.caption),
              const SizedBox(width: AppSpacing.xs),
              const Icon(Icons.chevron_right, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

/// 답으로 등록·반영한다 — 한 장의 [이대로 등록]과 폼의 [저장]이 함께 쓴다.
///
/// 새 손님의 답이고 이어 둔 고객이 없으면 새 고객으로, 이어 둔 고객이 있거나 그 고객의 새 아이용이면 아이를 더하고,
/// 다시 받은 답이면 그 아이를 고친다. 서버가 같은 처리 안에서 답을 지운다 — 같은 답으로 두 번 등록되지 않는다.
Future<int> saveFromAnswer(WidgetRef ref, int shopId, IntakeAnswer answer, PetFields pet, {int? intoCustomerId}) async {
  final commands = ref.read(customerCommandsProvider);
  final customerId = intoCustomerId ?? answer.matchedCustomer?.customerId;
  if (answer.mode == IntakeMode.update) {
    final saved = await commands.updatePet(shopId, answer.petId!, pet, intakeAnswerId: answer.answerId);
    return saved.pet.petId;
  }
  if (customerId != null) {
    final saved = await commands.addPet(shopId, customerId, pet, intakeAnswerId: answer.answerId);
    return saved.pet.petId;
  }
  final customer = readyCustomerFields(answer);
  if (customer == null) {
    throw ApiException(statusCode: 422, code: 'VALIDATION_ERROR', message: '');
  }
  final saved = await commands.register(shopId, customer: customer, pet: pet, intakeAnswerId: answer.answerId);
  return saved.pets.first.petId;
}

/// 저장이 실패했을 때의 처리. 답이 이미 없으면(다른 기기가 먼저 썼다) 알리고 목록으로 돌아간다.
/// 새 고객으로 등록하려는데 그 번호의 고객이 이미 있으면, 그 고객의 새 아이로 더할지 묻는다 — 조용히 덮어쓰지 않는다.
/// 돌려주는 값: 다시 저장할 고객 ID(새 아이로 더하기를 골랐을 때), 아니면 `null`.
Future<int?> handleSaveFailure(
  BuildContext context,
  WidgetRef ref,
  int shopId,
  IntakeAnswer answer,
  Object error, {
  required void Function(String message) onMessage,
}) async {
  if (error is ApiException && error.code == 'INTAKE_ANSWER_NOT_FOUND') {
    AppSnackBar.show(context, AppStrings.intakeGone);
    context.go('/home');
    return null;
  }
  if (error is ApiException && error.code == 'CUSTOMER_PHONE_TAKEN') {
    CustomerLookup? found;
    try {
      found = await ref.read(customerCommandsProvider).lookup(shopId, phoneDigits(answer.guardianPhone ?? ''));
    } catch (_) {
      found = null;
    }
    if (found != null && context.mounted) {
      final existing = found;
      final add = await AppSheet.show<bool>(
        context,
        builder: (context) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: Text(AppStrings.intakePhoneTaken(existing.name), style: AppTypography.bodyStrong),
            ),
            AppSheetAction(label: AppStrings.intakeAddToExisting, onTap: () => Navigator.of(context).pop(true)),
            AppSheetAction(label: AppStrings.cancel, onTap: () => Navigator.of(context).pop(false)),
          ],
        ),
      );
      if (add == true) return existing.customerId;
      return null;
    }
  }
  onMessage(messageFor(error));
  return null;
}

/// 받은 문진표 한 장(⑪ 설계 3.4) — 보호자가 적은 답 전부와 [이대로 등록]·[지우기].
///
/// 답이 다 찼으면 [이대로 등록] 한 번으로 끝난다(다시 치는 칸이 없다). 빈 필수 칸이 있거나 메모가 넘치면 그 칸만
/// 채우는 폼으로 간다 — 지어내지 않는다. 다시 받은 답은 늘 폼에서 지금 값과 견줘 보고 반영한다.
class IntakeAnswerScreen extends ConsumerStatefulWidget {
  const IntakeAnswerScreen({super.key, required this.answerId});

  static const registerKey = Key('intake-register');
  static const editKey = Key('intake-register-edit');
  static const deleteKey = Key('intake-delete');

  final int answerId;

  @override
  ConsumerState<IntakeAnswerScreen> createState() => _IntakeAnswerScreenState();
}

class _IntakeAnswerScreenState extends ConsumerState<IntakeAnswerScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  Future<void> _register(IntakeAnswer answer, PetFields pet, {int? intoCustomerId}) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final petId = await saveFromAnswer(ref, shopId, answer, pet, intoCustomerId: intoCustomerId);
      if (!mounted) return;
      AppSnackBar.show(context, AppStrings.intakeRegistered);
      context.pushReplacement('/pets/$petId');
    } catch (e) {
      if (!mounted) return;
      // 묻는 시트를 띄우기 전에 진행 표시를 끈다 — 시트 뒤에서 돌지 않게.
      setState(() => _busy = false);
      final into = await handleSaveFailure(
        context, ref, shopId, answer, e,
        onMessage: (message) => _errorText = message,
      );
      if (!mounted) return;
      setState(() {});
      if (into != null) await _register(answer, pet, intoCustomerId: into);
    }
  }

  Future<void> _delete() async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    final sure = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Text(AppStrings.intakeDeleteAsk, style: AppTypography.bodyStrong),
          ),
          AppSheetAction(label: AppStrings.intakeDeleteConfirm, onTap: () => Navigator.of(context).pop(true)),
          AppSheetAction(label: AppStrings.intakeKeep, onTap: () => Navigator.of(context).pop(false)),
        ],
      ),
    );
    if (sure != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await ref.read(intakeCommandsProvider).deleteAnswer(shopId, widget.answerId);
      if (mounted) context.pop();
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
    final shopId = ref.watch(selectedShopIdProvider);
    final key = (shopId: shopId ?? 0, answerId: widget.answerId);
    final answer = shopId == null ? const AsyncValue<IntakeAnswer>.loading() : ref.watch(intakeAnswerProvider(key));
    return _Frame(
      screenKey: ScreenKeys.intakeAnswer,
      title: AppStrings.intakeAnswerTitle,
      child: AsyncBody<IntakeAnswer>(
        value: answer,
        onRetry: () => ref.invalidate(intakeAnswerProvider(key)),
        builder: _body,
      ),
    );
  }

  Widget _body(IntakeAnswer a) {
    final update = a.mode == IntakeMode.update;
    final ready = update ? null : readyPetFields(a);
    // 새 고객으로 곧바로 등록하려면 보호자 이름·번호도 있어야 한다.
    final direct = ready != null && (a.matchedCustomer != null || readyCustomerFields(a) != null);
    final formPath = '/intake-answers/${a.answerId}/register';
    final target = update
        ? AppStrings.intakeTargetUpdate(a.petName ?? AppStrings.intakeNoName)
        : a.matchedCustomer != null
        ? AppStrings.intakeTargetMatched(a.matchedCustomer!.name)
        : AppStrings.intakeTargetNew(a.guardianName ?? '');
    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
      children: [
        Text(target, style: AppTypography.body),
        if (a.missing.isNotEmpty)
          _Note(AppStrings.intakeMissing([for (final code in a.missing) AppStrings.intakeFieldLabels[code] ?? code].join(' · '))),
        if (a.memoOver > 0) _Note(AppStrings.intakeMemoOver(a.memoOver)),
        if (a.guardianName != null || a.guardianPhone != null)
          _Section(AppStrings.intakeSectionGuardian, [
            (AppStrings.ownerNameLabel, a.guardianName),
            (AppStrings.ownerPhoneLabel, a.guardianPhone),
          ], skipEmpty: false),
        _Section(AppStrings.intakeSectionPet, [
          (AppStrings.intakeFieldLabels['name']!, a.petName),
          (AppStrings.intakeFieldLabels['species']!, a.species == null ? null : AppStrings.speciesLabel(a.species!)),
          (AppStrings.intakeFieldLabels['breed']!, a.breed),
          (AppStrings.intakeFieldLabels['sex']!, a.sex == null ? null : AppStrings.sexLabel(a.sex!)),
          (
            AppStrings.intakeFieldLabels['neutered']!,
            a.neutered == null ? null : (a.neutered! ? AppStrings.neuteredYes : AppStrings.neuteredNo),
          ),
          (
            AppStrings.intakeFieldLabels['birth']!,
            a.birthDate != null
                ? formatDate(a.birthDate!)
                : a.birthYear != null
                ? AppStrings.intakeBirthYear(a.birthYear!)
                : a.birthUnknown
                ? AppStrings.intakeBirthUnknown
                : null,
          ),
          (AppStrings.intakeFieldLabels['weight']!, a.weightKg == null ? null : formatWeight(a.weightKg!)),
        ], skipEmpty: update),
        _Section(AppStrings.intakeSectionHealth, [
          if (a.noKnownConditions == true) (AppStrings.intakeFieldLabels['conditions']!, AppStrings.intakeNoConditions),
          for (final c in a.conditions) (c.customLabel ?? c.label, c.note ?? ''),
          if (a.noKnownConditions == null) (AppStrings.intakeFieldLabels['conditions']!, null),
        ], skipEmpty: update),
        _Section(AppStrings.intakeSectionMore, [
          (AppStrings.intakeDislikes, a.dislikes),
          (AppStrings.intakeStyle, a.style),
          for (final extra in a.extras) (extra.label, extra.body),
        ], skipEmpty: true),
        if (_errorText != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.md),
            child: Semantics(liveRegion: true, child: Text(_errorText!, style: AppTypography.bodyStrong)),
          ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          key: IntakeAnswerScreen.registerKey,
          label: update
              ? AppStrings.intakeApply
              : direct
              ? AppStrings.intakeRegisterNow
              : AppStrings.intakeFillAndRegister,
          filled: true,
          busy: _busy,
          // 다 찼으면 곧바로 등록하고, 아니면 미리 채운 폼으로 간다(빈 칸만 채운다).
          onPressed: direct ? () => _register(a, ready) : () => context.push(formPath),
        ),
        if (direct) ...[
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            key: IntakeAnswerScreen.editKey,
            label: AppStrings.intakeRegisterEdit,
            onPressed: _busy ? null : () => context.push(formPath),
          ),
        ],
        const SizedBox(height: AppSpacing.sm),
        AppButton(key: IntakeAnswerScreen.deleteKey, label: AppStrings.intakeDelete, onPressed: _busy ? null : _delete),
      ],
    );
  }
}

class _Note extends StatelessWidget {
  const _Note(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: AppSpacing.sm),
    child: Text(text, style: AppTypography.bodyStrong),
  );
}

/// 답의 한 묶음. 값이 없는 줄은 `적지 않았어요` 로 보인다 — [skipEmpty] 면 그 줄을 뺀다(다시 받기·선택 칸).
class _Section extends StatelessWidget {
  const _Section(this.title, this.rows, {required this.skipEmpty});

  final String title;
  final List<(String, String?)> rows;
  final bool skipEmpty;

  @override
  Widget build(BuildContext context) {
    final shown = [
      for (final (label, value) in rows)
        if (!skipEmpty || (value != null && value.isNotEmpty)) (label, value),
    ];
    if (shown.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTypography.caption),
          const SizedBox(height: AppSpacing.sm),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final (index, (label, value)) in shown.indexed) ...[
                  if (index > 0) const SizedBox(height: AppSpacing.md),
                  Text(label, style: AppTypography.caption),
                  Text(
                    value == null || value.isEmpty ? AppStrings.intakeNotAnswered : value,
                    style: AppTypography.body,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 답으로 미리 채운 반려동물 폼 — 빈 칸만 채우거나 고쳐서 등록한다. 다시 받은 답은 지금 값 위에 적어 낸 칸만 덮여 있다.
class IntakeRegisterScreen extends ConsumerStatefulWidget {
  const IntakeRegisterScreen({super.key, required this.answerId});

  final int answerId;

  @override
  ConsumerState<IntakeRegisterScreen> createState() => _IntakeRegisterScreenState();
}

class _IntakeRegisterScreenState extends ConsumerState<IntakeRegisterScreen> {
  bool _busy = false;
  String? _errorText;

  /// 저장에 쓰는 답 — 화면이 처음 읽은 것을 쥐고 있는다(저장이 답을 지우면 다시 읽기가 404 다).
  IntakeAnswer? _answer;
  Pet? _current;
  bool _loaded = false;
  Object? _loadError;

  int? get _shopId => ref.read(selectedShopIdProvider);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final shopId = _shopId;
    if (shopId == null) return;
    setState(() {
      _loadError = null;
      _loaded = false;
    });
    try {
      final answer = await ref.read(intakeAnswerProvider((shopId: shopId, answerId: widget.answerId)).future);
      final current = answer.mode == IntakeMode.update
          ? (await ref.read(petDetailProvider((shopId: shopId, petId: answer.petId!)).future)).pet
          : null;
      await ref.read(conditionTypesProvider(shopId).future);
      if (!mounted) return;
      setState(() {
        _answer = answer;
        _current = current;
        _loaded = true;
      });
    } catch (e) {
      if (mounted) setState(() => _loadError = e);
    }
  }

  Future<void> _submit(PetFields fields, {int? intoCustomerId}) async {
    final shopId = _shopId;
    final answer = _answer;
    if (shopId == null || answer == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final petId = await saveFromAnswer(ref, shopId, answer, fields, intoCustomerId: intoCustomerId);
      if (!mounted) return;
      AppSnackBar.show(context, answer.mode == IntakeMode.update ? AppStrings.intakeApplied : AppStrings.intakeRegistered);
      context.go('/home');
      context.push('/pets/$petId');
    } catch (e) {
      if (!mounted) return;
      // 묻는 시트를 띄우기 전에 진행 표시를 끈다 — 시트 뒤에서 돌지 않게.
      setState(() => _busy = false);
      final into = await handleSaveFailure(
        context, ref, shopId, answer, e,
        onMessage: (message) => _errorText = message,
      );
      if (!mounted) return;
      setState(() {});
      if (into != null) await _submit(fields, intoCustomerId: into);
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider);
    final answer = _answer;
    final types = shopId == null ? null : ref.watch(conditionTypesProvider(shopId)).value;
    final state = _loadError != null
        ? AsyncError<void>(_loadError!, StackTrace.empty)
        : !_loaded || answer == null || types == null
        ? const AsyncLoading<void>()
        : const AsyncData<void>(null);
    return _Frame(
      screenKey: ScreenKeys.intakeRegister,
      title: answer?.mode == IntakeMode.update ? AppStrings.intakeApplyTitle : AppStrings.intakeRegisterTitle,
      child: AsyncBody<void>(
        value: state,
        onRetry: _load,
        builder: (_) {
          final prefill = prefillOf(answer!, current: _current);
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 무엇이 문진표에서 왔는지 알린다 — 지금 값과 다르게 채운 칸.
                if (prefill.changed.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.md),
                    child: Text(
                      AppStrings.intakeChangedFields([
                        for (final code in AppStrings.intakeFieldLabels.keys)
                          if (prefill.changed.contains(code)) AppStrings.intakeFieldLabels[code]!,
                      ].join(' · ')),
                      style: AppTypography.bodyStrong,
                    ),
                  ),
                PetForm(
                  prefill: prefill,
                  conditionTypes: types!,
                  today: ref.watch(todayProvider),
                  submitLabel: AppStrings.save,
                  busy: _busy,
                  errorText: _errorText,
                  onSubmit: _submit,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
