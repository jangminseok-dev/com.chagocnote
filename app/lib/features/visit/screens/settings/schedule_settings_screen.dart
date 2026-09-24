import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/error_messages.dart';
import '../../../../core/router/screen_keys.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens/app_colors.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_back_button.dart';
import '../../../../design/widgets/app_button.dart';
import '../../../../design/widgets/app_card.dart';
import '../../../../design/widgets/app_choice_chip.dart';
import '../../../../design/widgets/app_sheet.dart';
import '../../../../design/widgets/pressable.dart';
import '../../../../l10n/app_strings.dart';
import '../../../auth/state/shop_selection.dart';
import '../../../../core/time/today_provider.dart';
import '../../api/visit_models.dart';
import '../visit_labels.dart';
import '../../state/visit_commands.dart';
import '../../state/visit_form_rules.dart';
import '../../state/visit_providers.dart';
import '../../state/schedule_input.dart';

/// 설정 → 일정(사장만) — 영업시간, 기본 소요, 매주 쉬는 요일, 임시 휴무
/// (설계 9.1). 영업시간·소요·요일은 [저장]으로 한 번에 보내고, 임시 휴무는
/// 줄마다 바로 더하고 지운다.
class ScheduleSettingsScreen extends ConsumerStatefulWidget {
  const ScheduleSettingsScreen({super.key});

  @override
  ConsumerState<ScheduleSettingsScreen> createState() =>
      _ScheduleSettingsScreenState();
}

class _ScheduleSettingsScreenState
    extends ConsumerState<ScheduleSettingsScreen> {
  final _date = TextEditingController();
  final _note = TextEditingController();

  bool _initialized = false;
  late String _opensAt;
  late String _closesAt;
  late int _duration;
  late Set<int> _closedWeekdays;

  bool _busy = false;
  String? _errorText;
  String? _successText;
  String? _dateError;

  int? get _shopId => ref.read(selectedShopIdProvider);

  @override
  void dispose() {
    _date.dispose();
    _note.dispose();
    super.dispose();
  }

  void _init(VisitSettings settings) {
    if (_initialized) return;
    _initialized = true;
    _opensAt = settings.opensAt;
    _closesAt = settings.closesAt;
    _duration = settings.defaultDurationMinutes;
    _closedWeekdays = {...settings.closedWeekdays};
  }

  /// 10분씩, 길게 누르면 30분씩.
  void _stepDuration({required bool longer, bool long = false}) => setState(() {
    _duration = stepDuration(_duration, longer: longer, long: long);
    _successText = null;
  });

  Future<void> _pickTime({required bool opens}) async {
    final picked = await AppSheet.show<String>(
      context,
      builder: (context) => _TimeSheet(initial: opens ? _opensAt : _closesAt),
    );
    if (picked == null || !mounted) return;
    setState(() {
      if (opens) {
        _opensAt = picked;
      } else {
        _closesAt = picked;
      }
      _successText = null;
    });
  }

  Future<void> _save() async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    if (!opensBeforeCloses(_opensAt, _closesAt)) {
      setState(() => _errorText = AppStrings.closesBeforeOpens);
      return;
    }
    setState(() {
      _busy = true;
      _errorText = null;
      _successText = null;
    });
    try {
      await ref
          .read(visitCommandsProvider)
          .updateSettings(
            shopId,
            VisitSettings(
              opensAt: _opensAt,
              closesAt: _closesAt,
              defaultDurationMinutes: _duration,
              closedWeekdays: _closedWeekdays.toList()..sort(),
            ),
          );
      if (!mounted) return;
      setState(() {
        _busy = false;
        _successText = AppStrings.saved;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _addClosedDate() async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    final date = parseClosedDate(_date.text, ref.read(todayProvider));
    if (date == null) {
      setState(() => _dateError = AppStrings.closedDateInvalid);
      return;
    }
    setState(() {
      _busy = true;
      _dateError = null;
      _errorText = null;
    });
    try {
      final note = _note.text.trim();
      await ref
          .read(visitCommandsProvider)
          .addClosedDate(shopId, date, note: note.isEmpty ? null : note);
      if (!mounted) return;
      _date.clear();
      _note.clear();
      setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _deleteClosedDate(DateTime date) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref.read(visitCommandsProvider).deleteClosedDate(shopId, date);
      if (mounted) setState(() => _busy = false);
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
    final shopId = _shopId;
    final settings = shopId == null
        ? const AsyncValue<VisitSettings>.loading()
        : ref.watch(visitSettingsProvider(shopId));
    return Scaffold(
      key: ScreenKeys.settingsSchedule,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  AppSpacing.sm,
                ),
                child: Row(
                  children: [
                    AppBackButton(),
                    SizedBox(width: AppSpacing.sm),
                    Text(
                      AppStrings.settingsSchedule,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: settings.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(messageFor(error), style: AppTypography.body),
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: AppStrings.retry,
                          onPressed: () =>
                              ref.invalidate(visitSettingsProvider(shopId!)),
                        ),
                      ],
                    ),
                  ),
                  data: (data) {
                    _init(data);
                    return _body(shopId!);
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(int shopId) {
    final today = ref.watch(todayProvider);
    final closedDates = ref.watch(
      closedDatesProvider((
        shopId: shopId,
        from: DateTime(today.year, today.month, today.day),
      )),
    );
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        0,
        AppSpacing.lg,
        AppSpacing.xxl,
      ),
      children: [
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _TimeRow(
                label: AppStrings.opensAtLabel,
                value: _opensAt,
                onTap: () => _pickTime(opens: true),
              ),
              _TimeRow(
                label: AppStrings.closesAtLabel,
                value: _closesAt,
                onTap: () => _pickTime(opens: false),
              ),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  const Text(
                    AppStrings.defaultDurationLabel,
                    style: AppTypography.body,
                  ),
                  const Spacer(),
                  Pressable(
                    semanticLabel: AppStrings.shorter,
                    onTap: () => _stepDuration(longer: false),
                    onLongPress: () => _stepDuration(longer: false, long: true),
                    child: const Icon(Icons.remove, size: 18),
                  ),
                  Text(
                    AppStrings.durationText(_duration),
                    style: AppTypography.bodyStrong,
                  ),
                  Pressable(
                    semanticLabel: AppStrings.longer,
                    onTap: () => _stepDuration(longer: true),
                    onLongPress: () => _stepDuration(longer: true, long: true),
                    child: const Icon(Icons.add, size: 18),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              const Text(
                AppStrings.closedWeekdaysLabel,
                style: AppTypography.caption,
              ),
              const SizedBox(height: AppSpacing.sm),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  for (var d = 0; d < 7; d++)
                    AppChoiceChip(
                      label: AppStrings.weekdaysShort[d],
                      selected: _closedWeekdays.contains(d),
                      onTap: () => setState(() {
                        if (!_closedWeekdays.remove(d)) _closedWeekdays.add(d);
                        _successText = null;
                      }),
                    ),
                ],
              ),
              const SizedBox(height: AppSpacing.lg),
              if (_errorText != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Text(_errorText!, style: AppTypography.caption),
                ),
              if (_successText != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Text(_successText!, style: AppTypography.caption),
                ),
              AppButton(
                label: AppStrings.save,
                filled: true,
                busy: _busy,
                onPressed: _busy ? null : _save,
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                AppStrings.closedDatesLabel,
                style: AppTypography.caption,
              ),
              const SizedBox(height: AppSpacing.sm),
              closedDates.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, _) => Row(
                  children: [
                    Expanded(
                      child: Text(
                        messageFor(error),
                        style: AppTypography.caption,
                      ),
                    ),
                    AppButton(
                      label: AppStrings.retry,
                      onPressed: () => ref.invalidate(closedDatesProvider),
                    ),
                  ],
                ),
                data: (items) => items.isEmpty
                    ? const Text(
                        AppStrings.closedDatesEmpty,
                        style: AppTypography.body,
                      )
                    : Column(
                        children: [
                          for (final c in items)
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    [
                                      dayLabel(c.date),
                                      if (c.note != null) c.note!,
                                    ].join(' · '),
                                    style: AppTypography.body,
                                  ),
                                ),
                                Pressable(
                                  semanticLabel:
                                      '${AppStrings.delete} ${dayLabel(c.date)}',
                                  onTap: _busy
                                      ? null
                                      : () => _deleteClosedDate(c.date),
                                  child: const Icon(
                                    Icons.close,
                                    size: 18,
                                    color: AppColors.secondary,
                                  ),
                                ),
                              ],
                            ),
                        ],
                      ),
              ),
              const SizedBox(height: AppSpacing.md),
              TextField(
                controller: _date,
                keyboardType: TextInputType.datetime,
                inputFormatters: [LengthLimitingTextInputFormatter(10)],
                decoration: InputDecoration(
                  hintText: AppStrings.closedDateHint,
                  errorText: _dateError,
                ),
              ),
              TextField(
                controller: _note,
                inputFormatters: [LengthLimitingTextInputFormatter(30)],
                decoration: const InputDecoration(
                  hintText: AppStrings.closedDateNoteHint,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              AppButton(
                label: AppStrings.addClosedDate,
                onPressed: _busy ? null : _addClosedDate,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TimeRow extends StatelessWidget {
  const _TimeRow({
    required this.label,
    required this.value,
    required this.onTap,
  });

  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: label,
      onTap: onTap,
      // 이름표는 Pressable 이 읽는다 — 글자를 한 번 더 읽지 않게 뺀다.
      child: ExcludeSemantics(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
          child: Row(
            children: [
              Text(label, style: AppTypography.body),
              const Spacer(),
              Text(value, style: AppTypography.bodyStrong),
              const Icon(
                Icons.chevron_right,
                size: 18,
                color: AppColors.secondary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 시(0~23)와 분(10분 단위)을 칩으로 고르는 시트.
class _TimeSheet extends StatefulWidget {
  const _TimeSheet({required this.initial});

  final String initial;

  @override
  State<_TimeSheet> createState() => _TimeSheetState();
}

class _TimeSheetState extends State<_TimeSheet> {
  late int _hour = int.parse(widget.initial.substring(0, 2));
  late int _minute = int.parse(widget.initial.substring(3, 5));

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(AppStrings.pickTimeTitle, style: AppTypography.body),
        const SizedBox(height: AppSpacing.md),
        const Text(AppStrings.hourLabel, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xs),
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: [
            for (var h = 0; h < 24; h++)
              AppChoiceChip(
                label: h.toString().padLeft(2, '0'),
                selected: h == _hour,
                onTap: () => setState(() => _hour = h),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        const Text(AppStrings.minuteLabel, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xs),
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: [
            for (var m = 0; m < 60; m += 10)
              AppChoiceChip(
                label: m.toString().padLeft(2, '0'),
                selected: m == _minute,
                onTap: () => setState(() => _minute = m),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.confirm,
          filled: true,
          onPressed: () =>
              Navigator.of(context).pop(hhmmOf(_hour * 60 + _minute)),
        ),
      ],
    );
  }
}
