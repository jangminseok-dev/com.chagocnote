import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../customer/api/customer_models.dart';
import '../../customer/state/customer_providers.dart';
import '../api/visit_models.dart';
import '../state/visit_commands.dart';
import '../state/visit_form_draft.dart';
import '../state/visit_providers.dart';
import 'visit_labels.dart';

// 폼의 값·처음 값은 state/visit_form_draft 에 있다. 이 화면을 import 하던 곳이 그대로 쓰게 다시 내보낸다.
export '../state/visit_form_draft.dart' show VisitFormInitial, VisitFormValue;

/// 예약 ②(등록)와 수정이 함께 쓰는 폼 — 반려동물 칩, 날짜 줄, 시간 칸,
/// 메뉴·소요, 메모, 저장 버튼(설계 9.1).
///
/// 시간 칸의 줄긋기와 경고 문구는 서버의 시간 칸 응답만 쓴다(설계 6.3).
/// 고른 시각도 서버에 한 번 더 물어 그 응답의 시각 문자열을 저장에 쓴다 —
/// 매장 시간대를 앱이 계산하지 않는다.
class VisitForm extends ConsumerStatefulWidget {
  const VisitForm({
    super.key,
    required this.shopId,
    required this.customerId,
    required this.initial,
    required this.header,
    required this.submitLabel,
    required this.onSubmit,
    required this.busy,
    required this.errorText,
    this.onWalkIn,
    this.singlePet = false,
    this.scheduleLocked = false,
    this.excludeVisitIds = const [],
    this.aboveSubmit,
  });

  final int shopId;
  final int customerId;
  final VisitFormInitial initial;

  /// 폼 맨 위(보호자 카드).
  final Widget header;
  final String Function(DateTime date, String at) submitLabel;
  final Future<void> Function(VisitFormValue value) onSubmit;

  /// 있으면 [지금 시작]을 보인다(예약 없이 온 손님).
  final Future<void> Function(VisitFormValue value)? onWalkIn;
  final bool busy;
  final String? errorText;

  /// 수정 — 방문 하나는 반려동물 하나(또는 보호자만)다.
  final bool singlePet;

  /// 수정 — 예약됨이 아니면 날짜·시간·반려동물을 바꾸지 않는다(설계 6.2).
  final bool scheduleLocked;

  /// 옮길 방문. 시간 칸이 자기 자신과 겹치지 않게 뺀다.
  final List<int> excludeVisitIds;

  /// 저장 버튼 위에 둘 것(예약 등록의 "확인할 것"). 아이나 '보호자만'을 고른 뒤에만 부른다.
  final Widget Function(Set<int> petIds, DateTime date)? aboveSubmit;

  @override
  ConsumerState<VisitForm> createState() => _VisitFormState();
}

class _VisitFormState extends ConsumerState<VisitForm> {
  late final _memo = TextEditingController(text: widget.initial.memo);
  late DateTime _stripStart = _weekStart(widget.initial.date);

  /// 폼의 상태와 규칙. 위젯은 이것을 바꾸고 `setState`만 부른다.
  late final _draft = VisitFormDraft(widget.initial);

  @override
  void dispose() {
    _memo.dispose();
    super.dispose();
  }

  static DateTime _weekStart(DateTime d) =>
      DateTime(d.year, d.month, d.day - (d.weekday - 1));

  String get _exclude => widget.excludeVisitIds.join(',');

  /// 반려동물이 하나뿐인 보호자면 그 아이를 미리 고르고 "지난번처럼"을 채운다(처음 한 번).
  void _initPets(List<Pet> living) {
    final only = _draft.initPets(living);
    if (only != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _prefill(only));
    }
  }

  void _togglePet(int petId) {
    int? only;
    setState(() => only = _draft.togglePet(petId, single: widget.singlePet));
    if (only != null) _prefill(only!);
  }

  void _chooseOwnerOnly() => setState(_draft.chooseOwnerOnly);

  /// 처음 고른 아이의 지난 완료 방문 메뉴·소요로 채운다. 이미 손댔거나
  /// 초안·수정으로 채워진 폼이면 두고, 실패해도 그대로 둔다(돕는 기능이다).
  Future<void> _prefill(int petId) async {
    final seq = _draft.beginPrefill();
    if (seq == null) return;
    try {
      final defaults = await ref
          .read(visitCommandsProvider)
          .defaults(widget.shopId, petId);
      if (!mounted) return;
      if (_draft.applyPrefill(seq, defaults)) setState(() {});
    } catch (_) {
      // 미리 채우기는 돕는 것뿐이다 — 실패하면 빈 채로 둔다.
    }
  }

  void _toggleMenu(Menu menu, List<Menu> all, VisitSettings settings) =>
      setState(() => _draft.toggleMenu(menu, all, settings));

  void _stepDuration(
    VisitSettings settings, {
    required bool longer,
    bool long = false,
  }) =>
      setState(() => _draft.stepDuration(settings, longer: longer, long: long));

  void _pickDate(DateTime date) => setState(() => _draft.date = date);

  Future<void> _pickMinute(DateTime hour) async {
    final picked = await AppSheet.show<String>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(AppStrings.pickMinuteTitle, style: AppTypography.body),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              for (var m = 0; m < 60; m += 10)
                AppChoiceChip(
                  label: hhmm(DateTime(2000, 1, 1, hour.hour, m)),
                  selected: false,
                  onTap: () => Navigator.of(
                    context,
                  ).pop(hhmm(DateTime(2000, 1, 1, hour.hour, m))),
                ),
            ],
          ),
        ],
      ),
    );
    if (picked != null && mounted) setState(() => _draft.at = picked);
  }

  VisitFormValue _value(VisitSettings settings, String? startsAt) =>
      _draft.value(settings, startsAt, _memo.text);

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(visitSettingsProvider(widget.shopId));
    // 고객 상세 가운데 pets 만 본다 — 같은 값을 유지한 채 로딩 상태만 바뀔 때는 다시 그리지 않는다.
    final customer = ref.watch(
      customerDetailProvider((
        shopId: widget.shopId,
        customerId: widget.customerId,
      )).select((async) => (error: async.error, pets: async.value?.pets)),
    );
    final menus = ref.watch(
      menusProvider((shopId: widget.shopId, includeArchived: false)),
    );
    final error = settings.error ?? customer.error ?? menus.error;
    final s = settings.value;
    final pets = customer.pets;
    final m = menus.value;
    // 셋을 하나로 묶어 불러오기 틀에 넘긴다 — 하나라도 실패면 오류, 셋 다 오면 폼.
    return AsyncBody<void>(
      value: error != null
          ? AsyncError(error, StackTrace.empty)
          : s == null || pets == null || m == null
          ? const AsyncLoading()
          : const AsyncData(null),
      onRetry: () {
        ref.invalidate(visitSettingsProvider(widget.shopId));
        ref.invalidate(customerDetailProvider);
        ref.invalidate(menusProvider);
      },
      builder: (_) {
        final living = [
          for (final p in pets!)
            if (!p.passedAway || widget.initial.petIds.contains(p.petId)) p,
        ];
        _initPets(living);
        return _buildForm(s!, living, m!);
      },
    );
  }

  Widget _buildForm(VisitSettings settings, List<Pet> pets, List<Menu> menus) {
    _draft.ensureDuration(menus, settings);
    final duration = _draft.effectiveDuration(settings);
    final selection = _draft.at == null
        ? null
        : ref.watch(
            visitSlotsProvider((
              shopId: widget.shopId,
              date: _draft.date,
              duration: duration,
              at: _draft.at,
              exclude: _exclude,
            )),
          );
    final chosen = selection?.value?.slots.firstOrNull;
    final petsChosen = _draft.petsChosen;
    final canSubmit =
        petsChosen && chosen != null && !widget.busy && _draft.at != null;

    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.sm,
        AppSpacing.lg,
        AppSpacing.xxl,
      ),
      children: [
        widget.header,
        const SizedBox(height: AppSpacing.md),
        _PetChips(
          pets: pets,
          selected: _draft.petIds,
          ownerOnly: _draft.ownerOnly,
          locked: widget.scheduleLocked,
          onPet: _togglePet,
          onOwnerOnly: _chooseOwnerOnly,
        ),
        const SizedBox(height: AppSpacing.lg),
        _DateStrip(
          shopId: widget.shopId,
          start: _stripStart,
          selected: _draft.date,
          locked: widget.scheduleLocked,
          onMove: (days) => setState(
            () => _stripStart = DateTime(
              _stripStart.year,
              _stripStart.month,
              _stripStart.day + days,
            ),
          ),
          onPick: _pickDate,
        ),
        const SizedBox(height: AppSpacing.lg),
        Row(
          children: [
            const Text(AppStrings.visitTimeLabel, style: AppTypography.caption),
            const Spacer(),
            Text(
              AppStrings.businessHours(settings.opensAt, settings.closesAt),
              style: AppTypography.caption,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        _SlotGrid(
          slotsKey: (
            shopId: widget.shopId,
            date: _draft.date,
            duration: duration,
            at: null,
            exclude: _exclude,
          ),
          selectedAt: _draft.at,
          locked: widget.scheduleLocked,
          onPick: (at) => setState(() => _draft.at = at),
          onLongPress: _pickMinute,
        ),
        if (!widget.scheduleLocked)
          const Padding(
            padding: EdgeInsets.only(top: AppSpacing.xs),
            child: Text(
              AppStrings.pickMinuteHint,
              style: AppTypography.caption,
            ),
          ),
        if (chosen != null)
          for (final w in chosen.warnings)
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.xs),
              child: Text(
                '· ${warningLabel(w)}',
                style: AppTypography.bodyStrong,
              ),
            ),
        if (selection?.error != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Text(
              messageFor(selection!.error!),
              style: AppTypography.caption,
            ),
          ),
        const SizedBox(height: AppSpacing.lg),
        _MenuSection(
          menus: menus,
          knownMenus: _draft.knownMenus,
          selectedIds: _draft.menuIds,
          duration: duration,
          prefilledNote: _draft.prefilledNote,
          onToggle: (menu) => _toggleMenu(menu, menus, settings),
          onShorter: ({bool long = false}) =>
              _stepDuration(settings, longer: false, long: long),
          onLonger: ({bool long = false}) =>
              _stepDuration(settings, longer: true, long: long),
        ),
        const SizedBox(height: AppSpacing.lg),
        AppCard(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: TextField(
            controller: _memo,
            maxLines: 3,
            minLines: 1,
            inputFormatters: [LengthLimitingTextInputFormatter(500)],
            decoration: const InputDecoration(
              hintText: AppStrings.visitMemoHint,
              border: InputBorder.none,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        if (widget.aboveSubmit != null && petsChosen)
          widget.aboveSubmit!({..._draft.petIds}, _draft.date),
        if (widget.errorText != null)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(widget.errorText!, style: AppTypography.caption),
          ),
        AppButton(
          label: !petsChosen
              ? AppStrings.pickPetFirst
              : _draft.at == null
              ? AppStrings.pickTimeFirst
              : widget.submitLabel(_draft.date, _draft.at!),
          filled: true,
          busy: widget.busy,
          onPressed: canSubmit
              ? () => widget.onSubmit(_value(settings, chosen.startsAt.iso))
              : null,
        ),
        // 예약 없이 온 손님은 어느 날을 보고 있든 지금 시작한다 — 시각은 서버가 지금으로 놓는다.
        if (widget.onWalkIn != null) ...[
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.startNow,
            onPressed: petsChosen && !widget.busy
                ? () => widget.onWalkIn!(_value(settings, null))
                : null,
          ),
        ],
      ],
    );
  }
}

class _PetChips extends StatelessWidget {
  const _PetChips({
    required this.pets,
    required this.selected,
    required this.ownerOnly,
    required this.locked,
    required this.onPet,
    required this.onOwnerOnly,
  });

  final List<Pet> pets;
  final Set<int> selected;
  final bool ownerOnly;
  final bool locked;
  final ValueChanged<int> onPet;
  final VoidCallback onOwnerOnly;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: [
        for (final p in pets)
          AppChoiceChip(
            label: p.name,
            selected: selected.contains(p.petId),
            onTap: locked ? null : () => onPet(p.petId),
          ),
        AppChoiceChip(
          label: AppStrings.ownerOnly,
          selected: ownerOnly,
          onTap: locked ? null : onOwnerOnly,
        ),
      ],
    );
  }
}

/// 날짜 줄 — 한 주(월~일)를 보이고 ‹ › 로 한 주씩 옮긴다. 휴무일은 옅게
/// 보이지만 고를 수 있다(경고만, 설계 2절).
class _DateStrip extends ConsumerWidget {
  const _DateStrip({
    required this.shopId,
    required this.start,
    required this.selected,
    required this.locked,
    required this.onMove,
    required this.onPick,
  });

  final int shopId;
  final DateTime start;
  final DateTime selected;
  final bool locked;
  final ValueChanged<int> onMove;
  final ValueChanged<DateTime> onPick;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final days = [
      for (var i = 0; i < 7; i++)
        DateTime(start.year, start.month, start.day + i),
    ];
    // 한 주가 두 달에 걸치면 두 달을 다 읽는다.
    final months = {for (final d in days) DateTime(d.year, d.month)};
    final closed = <DateTime>{};
    for (final month in months) {
      final summary = ref
          .watch(calendarMonthProvider((shopId: shopId, month: month)))
          .value;
      for (final d in summary?.days ?? const <CalendarDay>[]) {
        if (d.closedDay) closed.add(d.date);
      }
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(AppStrings.visitDateLabel, style: AppTypography.caption),
            const Spacer(),
            Text(
              AppStrings.monthLabel(selected.month),
              style: AppTypography.bodyStrong,
            ),
            Pressable(
              semanticLabel: AppStrings.prevWeek,
              onTap: locked ? null : () => onMove(-7),
              child: const Icon(Icons.chevron_left, size: 20),
            ),
            Pressable(
              semanticLabel: AppStrings.nextWeek,
              onTap: locked ? null : () => onMove(7),
              child: const Icon(Icons.chevron_right, size: 20),
            ),
          ],
        ),
        Row(
          children: [
            for (final d in days)
              Expanded(
                child: _DayCell(
                  date: d,
                  selected: sameDay(d, selected),
                  closed: closed.contains(d),
                  onTap: locked ? null : () => onPick(d),
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class _DayCell extends StatelessWidget {
  const _DayCell({
    required this.date,
    required this.selected,
    required this.closed,
    required this.onTap,
  });

  final DateTime date;
  final bool selected;
  final bool closed;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected
        ? AppColors.white
        : closed
        ? AppColors.line
        : AppColors.ink;
    return Pressable(
      semanticLabel: dayLabel(date),
      selected: selected,
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 2),
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        decoration: BoxDecoration(
          color: selected ? AppColors.ink : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: selected ? AppColors.ink : AppColors.line),
        ),
        child: ExcludeSemantics(
          child: Column(
            children: [
              Text(
                AppStrings.weekdaysShort[date.weekday - 1],
                style: AppTypography.caption.copyWith(
                  color: selected ? AppColors.white : AppColors.secondary,
                ),
              ),
              Text(
                '${date.day}',
                style: AppTypography.bodyStrong.copyWith(color: color),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 정시 칸. 겹치는 칸은 줄을 긋고, 휴무·영업시간 밖은 옅게 그린다 — 그래도
/// 누를 수 있다(경고만). 길게 누르면 그 시간의 10분 단위를 고른다.
class _SlotGrid extends ConsumerWidget {
  const _SlotGrid({
    required this.slotsKey,
    required this.selectedAt,
    required this.locked,
    required this.onPick,
    required this.onLongPress,
  });

  final SlotsKey slotsKey;
  final String? selectedAt;
  final bool locked;
  final ValueChanged<String> onPick;
  final ValueChanged<DateTime> onLongPress;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final slots = ref.watch(visitSlotsProvider(slotsKey));
    return slots.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(AppSpacing.md),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, _) => AppErrorRetry.row(
        message: loadMessageFor(error),
        onRetry: () => ref.invalidate(visitSlotsProvider(slotsKey)),
      ),
      data: (data) => Wrap(
        spacing: AppSpacing.sm,
        runSpacing: AppSpacing.sm,
        children: [
          for (final slot in data.slots)
            _SlotChip(
              slot: slot,
              selectedAt: selectedAt,
              onTap: locked ? null : () => onPick(hhmm(slot.startsAt.wall)),
              onLongPress: locked
                  ? null
                  : () => onLongPress(slot.startsAt.wall),
            ),
        ],
      ),
    );
  }
}

class _SlotChip extends StatelessWidget {
  const _SlotChip({
    required this.slot,
    required this.selectedAt,
    required this.onTap,
    required this.onLongPress,
  });

  final Slot slot;
  final String? selectedAt;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    final hour = slot.startsAt.wall.hour;
    // 10분 단위로 고른 시각은 그 시(時)의 칸에 보인다.
    final selectedHere =
        selectedAt != null && int.parse(selectedAt!.substring(0, 2)) == hour;
    final label = selectedHere ? selectedAt! : hhmm(slot.startsAt.wall);
    final overlap = slot.warnings.contains(VisitWarning.overlap);
    final faint =
        slot.warnings.contains(VisitWarning.closedDay) ||
        slot.warnings.contains(VisitWarning.outsideHours);
    return Pressable(
      semanticLabel: label,
      selected: selectedHere,
      onTap: onTap,
      onLongPress: onLongPress,
      child: Container(
        width: 64,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
        // 휴무·영업 밖은 옅은 바탕에 옅은 글자, 겹침은 흰 바탕에 줄긋기 —
        // 둘이 한눈에 구분된다(A2 잔여).
        decoration: BoxDecoration(
          color: selectedHere
              ? AppColors.ink
              : faint
              ? AppColors.backgroundTop
              : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(
            color: selectedHere ? AppColors.ink : AppColors.line,
          ),
        ),
        alignment: Alignment.center,
        child: ExcludeSemantics(
          child: Text(
            label,
            style: AppTypography.body.copyWith(
              color: selectedHere
                  ? AppColors.white
                  : faint
                  ? AppColors.secondary
                  : AppColors.ink,
              decoration: overlap ? TextDecoration.lineThrough : null,
            ),
          ),
        ),
      ),
    );
  }
}

class _MenuSection extends StatelessWidget {
  const _MenuSection({
    required this.menus,
    required this.knownMenus,
    required this.selectedIds,
    required this.duration,
    required this.prefilledNote,
    required this.onToggle,
    required this.onShorter,
    required this.onLonger,
  });

  final List<Menu> menus;
  final List<MenuBrief> knownMenus;
  final List<int> selectedIds;
  final int duration;
  final bool prefilledNote;
  final ValueChanged<Menu> onToggle;
  final void Function({bool long}) onShorter;
  final void Function({bool long}) onLonger;

  @override
  Widget build(BuildContext context) {
    final activeIds = {for (final m in menus) m.menuId};
    // 보관된 메뉴가 이 방문에 붙어 있으면 이름만 보이고 뺄 수 있게 한다.
    final archived = [
      for (final m in knownMenus)
        if (!activeIds.contains(m.menuId) && selectedIds.contains(m.menuId))
          Menu(
            menuId: m.menuId,
            name: m.name,
            defaultDurationMinutes: null,
            sortOrder: 0,
            archived: true,
            price: null,
          ),
    ];
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            AppStrings.menuDurationLabel,
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              for (final m in [...menus, ...archived])
                AppChoiceChip(
                  label: m.name,
                  selected: selectedIds.contains(m.menuId),
                  onTap: () => onToggle(m),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              const Text(AppStrings.durationLabel, style: AppTypography.body),
              const Spacer(),
              Pressable(
                semanticLabel: AppStrings.shorter,
                onTap: () => onShorter(),
                onLongPress: () => onShorter(long: true),
                child: const Icon(Icons.remove, size: 18),
              ),
              Text(
                AppStrings.durationText(duration),
                style: AppTypography.bodyStrong,
              ),
              Pressable(
                semanticLabel: AppStrings.longer,
                onTap: () => onLonger(),
                onLongPress: () => onLonger(long: true),
                child: const Icon(Icons.add, size: 18),
              ),
            ],
          ),
          if (prefilledNote) ...[
            const SizedBox(height: AppSpacing.xs),
            const Text(
              AppStrings.prefilledFromLast,
              style: AppTypography.caption,
            ),
          ],
        ],
      ),
    );
  }
}
