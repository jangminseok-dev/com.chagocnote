import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/state/customer_input.dart';
import '../api/record_models.dart';
import '../api/visit_models.dart';
import '../state/record_rules.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'record_photos.dart';
import 'visit_labels.dart';

/// 미용 기록 — 완료 흐름과 [기록 수정]이 같은 폼이다(설계 10.1 ④).
///
/// 사진 줄(붙은 사진 · 올리는 중 · 추가), 몸무게, 실제 메뉴와 금액, 총액, 결제 수단, 케어 메모, 내부 메모.
/// [completing]이면 저장 버튼이 "완료하기"(기록 저장 → 같은 묶음 완료)이고 맨 아래 "나중에 적고 완료"가
/// 있다. 완료했으면 `true`로 닫힌다 — 부른 화면이 다음 예약 시트를 띄운다.
///
/// 올리는 중이어도 저장을 막지 않는다. 저장은 이미 붙은 사진만 보내고 남은 사진은 대기열이 덧붙인다.
/// 그 사이 붙은 사진 때문에 버전이 어긋나면(409) 다시 읽어 새 사진만 더하고 한 번 더 보낸다(설계 8절).
class RecordScreen extends ConsumerStatefulWidget {
  const RecordScreen({
    super.key,
    required this.visitId,
    this.completing = false,
  });

  final int visitId;
  final bool completing;

  @override
  ConsumerState<RecordScreen> createState() => _RecordScreenState();
}

class _RecordScreenState extends ConsumerState<RecordScreen> {
  bool _started = false;
  final _weight = TextEditingController();
  final _total = TextEditingController();
  final _careNote = TextEditingController();
  final _internalNote = TextEditingController();

  /// 고른 메뉴(고른 순서)와 메뉴마다의 금액 칸.
  final _lines = <({int menuId, String name})>[];
  final _amounts = <int, TextEditingController>{};

  /// 총액을 직접 고쳤는지. 고치기 전에는 항목 합을 따라간다.
  bool _totalTouched = false;
  PaymentMethod? _payment;
  List<FormMedia> _media = const [];
  final _removed = <int>{};
  int? _version;

  bool _busy = false;
  String? _errorText;

  /// 완료 전이를 이미 보냈다 — 기록 저장이 뒤에 실패해 다시 누르면 저장만 한다.
  bool _completed = false;
  Map<String, String> _fieldErrors = const {};

  int? get _shopId => ref.read(selectedShopIdProvider);

  @override
  void dispose() {
    for (final c in [
      _weight,
      _total,
      _careNote,
      _internalNote,
      ..._amounts.values,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  /// 처음 한 번 폼을 채운다(설계 10.1 ④의 미리 채움 — `recordFormStart`).
  void _start(VisitDetail detail, List<Menu> menus) {
    final start = recordFormStart(detail, menus);
    final weight = start.weightKg;
    _weight.text = weight == null ? '' : weightText(weight);
    for (final line in start.lines) {
      _lines.add((menuId: line.menuId, name: line.name));
      _amounts[line.menuId] = TextEditingController(
        text: line.amount?.toString() ?? '',
      );
    }
    final total = start.totalAmount;
    _totalTouched = total != null && '$total' != sumText(start.lines);
    _total.text = total == null ? sumText(start.lines) : '$total';
    _payment = start.payment;
    _careNote.text = start.careNote;
    _internalNote.text = start.internalNote;
    _media = start.media;
    _version = start.version;
    _started = true;
  }

  int? _amountOf(int menuId) => int.tryParse(_amounts[menuId]?.text ?? '');

  List<FormLine> get _formLines => [
    for (final l in _lines)
      FormLine(menuId: l.menuId, name: l.name, amount: _amountOf(l.menuId)),
  ];

  void _followSum() {
    if (_totalTouched) return;
    _total.text = sumText(_formLines);
  }

  void _toggleMenu(Menu menu) {
    setState(() {
      final i = _lines.indexWhere((l) => l.menuId == menu.menuId);
      if (i >= 0) {
        _lines.removeAt(i);
        _amounts.remove(menu.menuId)?.dispose();
      } else {
        _lines.add((menuId: menu.menuId, name: menu.name));
        _amounts[menu.menuId] = TextEditingController(
          text: menu.price?.toString() ?? '',
        );
      }
      _followSum();
    });
  }

  void _togglePhase(FormMedia media) => setState(() {
    _media = [
      for (final m in _media)
        if (m.mediaId == media.mediaId)
          FormMedia(
            m.media,
            m.phase == MediaPhase.before ? MediaPhase.after : MediaPhase.before,
          )
        else
          m,
    ];
  });

  void _removeMedia(FormMedia media) => setState(() {
    _removed.add(media.mediaId);
    _media = [
      for (final m in _media)
        if (m.mediaId != media.mediaId) m,
    ];
  });

  /// 보낼 값. 칸이 틀렸으면 문구를 달고 null.
  RecordInput? _input(VisitDetail detail) {
    final errors = <String, String>{};
    double? weight;
    if (detail.visit.pet != null && _weight.text.trim().isNotEmpty) {
      weight = parseWeight(_weight.text);
      if (weight == null) errors['weight'] = AppStrings.weightInvalid;
    }
    final total = int.tryParse(_total.text);
    final amounts = [for (final l in _lines) _amountOf(l.menuId) ?? 0];
    if ((total ?? 0) > maxAmount || amounts.any((a) => a > maxAmount)) {
      errors['amount'] = AppStrings.amountTooLarge;
    }
    setState(() => _fieldErrors = errors);
    if (errors.isNotEmpty) return null;
    return RecordInput(
      version: _version,
      weightKg: weight,
      careNote: noteOrNull(_careNote.text),
      internalNote: noteOrNull(_internalNote.text),
      paymentMethod: _payment,
      totalAmount: total,
      items: [
        for (var i = 0; i < _lines.length; i++)
          (menuId: _lines[i].menuId, amount: amounts[i]),
      ],
      media: placementsOf(_media),
    );
  }

  /// 저장. 버전이 어긋나면 다시 읽어 새 사진만 더하고 한 번 더 보낸다.
  Future<void> _put(int shopId, VisitDetail detail) async {
    final commands = ref.read(visitCommandsProvider);
    final input = _input(detail);
    if (input == null) throw const _Invalid();
    VisitRecord saved;
    try {
      saved = await commands.saveRecord(shopId, widget.visitId, input);
    } on ApiException catch (e) {
      if (e.code != 'RECORD_VERSION_CONFLICT') rethrow;
      // 저장이 상세를 무효화했다 — 다시 읽으면 `build`의 `ref.listen`이 새 사진을 폼에 더한다.
      final fresh = await ref.read(
        visitDetailProvider((shopId: shopId, visitId: widget.visitId)).future,
      );
      _version = fresh.record?.version;
      final again = _input(detail);
      if (again == null) throw const _Invalid();
      saved = await commands.saveRecord(shopId, widget.visitId, again);
    }
    _version = saved.version;
  }

  /// 같은 묶음에서 이 방문과 상태가 같은 방문들 — 가족은 함께 끝낸다. 기록은 이 방문에만 쓴다.
  List<int> _sameStatusIds(VisitDetail detail) => [
    detail.visit.visitId,
    for (final v in detail.group)
      if (v.status == detail.visit.status) v.visitId,
  ];

  Future<void> _submit(VisitDetail detail, {required bool withRecord}) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    Future<void> complete() async {
      if (!widget.completing || _completed) return;
      await ref
          .read(visitCommandsProvider)
          .transition(
            shopId,
            visitIds: _sameStatusIds(detail),
            action: VisitAction.complete,
          );
      _completed = true;
    }

    try {
      // 예약됨에서 바로 완료하면 먼저 완료한다 — 기록은 미용 중·완료 방문에만 쓴다(설계 8절).
      if (detail.visit.status == VisitStatus.reserved) await complete();
      if (withRecord) await _put(shopId, detail);
      await complete();
      if (mounted) context.pop(widget.completing);
    } on _Invalid {
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
    final key = (shopId: shopId ?? 0, visitId: widget.visitId);
    final detail = shopId == null
        ? const AsyncValue<VisitDetail>.loading()
        : ref.watch(visitDetailProvider(key));
    final menus = shopId == null
        ? const AsyncValue<List<Menu>>.loading()
        : ref.watch(menusProvider((shopId: shopId, includeArchived: false)));
    // 대기열이 사진을 붙이면 상세를 다시 읽는다 — 새 사진을 폼에 더한다(고친 칸은 그대로).
    ref.listen(visitDetailProvider(key), (_, next) {
      final fresh = next.value;
      if (!_started || fresh == null) return;
      setState(() => _media = withNewMedia(_media, _removed, fresh.record));
    });
    final d = detail.value;
    final m = menus.value;
    if (!_started && d != null && m != null) _start(d, m);
    return Scaffold(
      key: ScreenKeys.visitRecord,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      widget.completing
                          ? AppStrings.completeRecordTitle
                          : AppStrings.recordTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: switch ((detail, menus)) {
                  (AsyncError(:final error), _) ||
                  (_, AsyncError(:final error)) => AppErrorRetry(
                    message: messageFor(error),
                    onRetry: () {
                      ref.invalidate(visitDetailProvider(key));
                      ref.invalidate(menusProvider);
                    },
                  ),
                  _ when !_started => const Center(
                    child: CircularProgressIndicator(),
                  ),
                  _ => _form(d!, m!),
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _form(VisitDetail detail, List<Menu> menus) {
    final visit = detail.visit;
    final selected = {for (final l in _lines) l.menuId};
    final active = {for (final menu in menus) menu.menuId};
    // 보관된 메뉴가 기록에 있으면 이름만 보이고 뺄 수 있게 한다.
    final chips = [
      for (final menu in menus) menu,
      for (final l in _lines)
        if (!active.contains(l.menuId))
          Menu(
            menuId: l.menuId,
            name: l.name,
            defaultDurationMinutes: null,
            sortOrder: 0,
            archived: true,
            price: null,
          ),
    ];
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        Text(visitsTitle([visit]), style: AppTypography.caption),
        const SizedBox(height: AppSpacing.md),
        RecordPhotoStrip(
          visitId: widget.visitId,
          media: _media,
          onTapMedia: _busy ? null : _togglePhase,
          onRemoveMedia: _busy ? null : _removeMedia,
          onAdd: _busy
              ? null
              : () => addPhotos(
                  context,
                  ref,
                  shopId: _shopId!,
                  visitId: widget.visitId,
                  phase: MediaPhase.after,
                  // 폼에서 뺀 사진도 저장 전까지는 서버 자리를 차지한다.
                  attached: detail.record?.media.length ?? 0,
                ),
        ),
        const SizedBox(height: AppSpacing.lg),
        if (visit.pet != null)
          _Section(
            label: AppStrings.weightLabel,
            child: TextField(
              controller: _weight,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
                LengthLimitingTextInputFormatter(5),
              ],
              decoration: InputDecoration(
                hintText: AppStrings.weightHint,
                suffixText: AppStrings.weightUnit,
                errorText: _fieldErrors['weight'],
              ),
            ),
          ),
        _Section(
          label: AppStrings.recordMenusLabel,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  for (final menu in chips)
                    AppChoiceChip(
                      label: menu.name,
                      selected: selected.contains(menu.menuId),
                      onTap: _busy ? null : () => _toggleMenu(menu),
                    ),
                ],
              ),
              for (final l in _lines)
                Row(
                  children: [
                    Expanded(child: Text(l.name, style: AppTypography.body)),
                    SizedBox(
                      width: 140,
                      child: TextField(
                        key: ValueKey('amount-${l.menuId}'),
                        controller: _amounts[l.menuId],
                        keyboardType: TextInputType.number,
                        textAlign: TextAlign.end,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(9),
                        ],
                        decoration: const InputDecoration(
                          hintText: AppStrings.amountHint,
                          suffixText: AppStrings.wonUnit,
                        ),
                        onChanged: (_) => setState(_followSum),
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
        _Section(
          label: AppStrings.totalLabel,
          child: TextField(
            key: const ValueKey('total'),
            controller: _total,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(9),
            ],
            decoration: InputDecoration(
              suffixText: AppStrings.wonUnit,
              errorText: _fieldErrors['amount'],
            ),
            onChanged: (_) => _totalTouched = true,
          ),
        ),
        _Section(
          label: AppStrings.paymentLabel,
          child: Wrap(
            spacing: AppSpacing.sm,
            children: [
              for (final method in PaymentMethod.values)
                AppChoiceChip(
                  label: paymentLabel(method),
                  selected: _payment == method,
                  onTap: _busy
                      ? null
                      : () => setState(
                          () => _payment = _payment == method ? null : method,
                        ),
                ),
            ],
          ),
        ),
        _Section(
          label: AppStrings.careNoteLabel,
          child: TextField(
            key: const ValueKey('careNote'),
            controller: _careNote,
            maxLines: null,
            inputFormatters: [LengthLimitingTextInputFormatter(maxNoteLength)],
            decoration: const InputDecoration(
              hintText: AppStrings.careNoteHint,
            ),
          ),
        ),
        _Section(
          label: AppStrings.internalNoteLabel,
          child: TextField(
            key: const ValueKey('internalNote'),
            controller: _internalNote,
            maxLines: null,
            inputFormatters: [LengthLimitingTextInputFormatter(maxNoteLength)],
            decoration: const InputDecoration(
              hintText: AppStrings.internalNoteHint,
            ),
          ),
        ),
        if (_errorText != null)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(_errorText!, style: AppTypography.caption),
          ),
        AppButton(
          label: widget.completing
              ? AppStrings.completeWithRecord
              : AppStrings.save,
          filled: true,
          busy: _busy,
          onPressed: _busy ? null : () => _submit(detail, withRecord: true),
        ),
        if (widget.completing) ...[
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.completeWithoutRecord,
            onPressed: _busy ? null : () => _submit(detail, withRecord: false),
          ),
        ],
      ],
    );
  }
}

/// 칸이 틀려 보내지 않았다 — 문구는 칸 아래에 이미 달았다.
class _Invalid implements Exception {
  const _Invalid();
}

class _Section extends StatelessWidget {
  const _Section({required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: SizedBox(
      width: double.infinity,
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: AppTypography.caption),
            const SizedBox(height: AppSpacing.xs),
            child,
          ],
        ),
      ),
    ),
  );
}
