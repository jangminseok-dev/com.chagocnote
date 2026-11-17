import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/today_provider.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/record_models.dart';
import '../api/visit_marks.dart';
import '../api/visit_models.dart';
import '../api/wrap_up_models.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import '../state/wrap_up_controller.dart';
import '../state/wrap_up_rules.dart';
import 'visit_actions.dart';
import 'visit_labels.dart';

/// 하루 마무리(⑬ 설계 3.6) — 그날의 남은 일을 한 장씩 넘기며 끝낸다(방문을 하나씩 찾아 들어가지 않는다).
///
/// 차례는 정리 안 된 예약 → 결제 안 적음 → 알림장 안 보냄(누른 종류부터). 장마다 지금 있는 동작을 부른다 — 상태
/// 바꾸기, 기록 저장(총액·결제 수단만), 알림장 보내기·보내지 않음. 한 장을 끝내면 저절로 다음 장이다. 처리가 실패하면
/// (다른 기기가 먼저 끝냈을 수 있다) 알리고 다시 읽어 다음 장으로 간다. 끝 화면의 수에는 금액이 없다.
class WrapUpScreen extends ConsumerStatefulWidget {
  const WrapUpScreen({super.key, required this.date, this.start});

  final DateTime date;
  final WrapUpKind? start;

  @override
  ConsumerState<WrapUpScreen> createState() => _WrapUpScreenState();
}

class _WrapUpScreenState extends ConsumerState<WrapUpScreen> {
  bool _busy = false;

  WrapUpKey _key(int shopId) => (shopId: shopId, date: widget.date, start: widget.start);

  WrapUpController _controller(int shopId) => ref.read(wrapUpControllerProvider(_key(shopId)).notifier);

  /// 한 장의 일을 하고 다음 장으로 — 실패하면 알리고(다른 기기가 먼저 끝냈을 수 있다) 다시 읽는다.
  /// [advance] 가 false 를 돌려주면(사용자가 닫았다) 그대로 둔다.
  Future<void> _run(int shopId, Future<bool> Function() action) async {
    if (_busy) return;
    setState(() => _busy = true);
    var advance = true;
    try {
      advance = await action();
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    }
    if (advance && mounted) await _controller(shopId).done();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _act(int shopId, Visit visit, VisitAction action) => _run(shopId, () async {
    final choice = await askVisitAction(
      context,
      ref,
      shopId: shopId,
      action: action,
      anchorVisitId: visit.visitId,
    );
    // 완료는 완료 흐름(기록 화면 → 다음 예약 시트)이 끝까지 돌았다 — 다시 읽어 본다.
    if (action == VisitAction.complete) return true;
    if (choice == null) return false;
    await sendVisitAction(ref, shopId: shopId, choice: choice, ids: [visit.visitId]);
    return true;
  });

  Future<void> _savePayment(int shopId, int visitId, int total, PaymentMethod method) => _run(shopId, () async {
    final key = (shopId: shopId, visitId: visitId);
    final commands = ref.read(visitCommandsProvider);
    var detail = await ref.read(visitDetailProvider(key).future);
    for (var attempt = 0; ; attempt++) {
      try {
        await commands.saveRecord(shopId, visitId, paymentInputOf(detail.record, total: total, method: method));
        return true;
      } on ApiException catch (e) {
        if (e.code != 'RECORD_VERSION_CONFLICT' || attempt > 0) rethrow;
        // 저장이 상세를 무효화했다 — 새 기록 위에 같은 총액·수단을 한 번 더.
        detail = await ref.read(visitDetailProvider(key).future);
      }
    }
  });

  Future<void> _previewReport(int shopId, int visitId) => _run(shopId, () async {
    final sent = await context.push<bool>('/visits/$visitId/report');
    return sent == true;
  });

  Future<void> _skipReport(int shopId, int visitId) => _run(shopId, () async {
    await ref.read(visitCommandsProvider).skipReport(shopId, visitId);
    return true;
  });

  Future<void> _stopCounting(int shopId) => _run(shopId, () async {
    await ref.read(visitCommandsProvider).updateRevisitSettings(shopId, {'count_unsent_reports': false});
    return true;
  });

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider);
    final value = shopId == null
        ? const AsyncValue<WrapUpState>.loading()
        : ref.watch(wrapUpControllerProvider(_key(shopId)));
    final state = value.value;
    final current = state?.current;
    return Scaffold(
      key: ScreenKeys.wrapUp,
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
                    const Expanded(child: Text(AppStrings.wrapUpTitle, style: AppTypography.titleKo)),
                    if (state != null && current != null)
                      Text(AppStrings.wrapUpProgress(state.position, state.total), style: AppTypography.caption),
                  ],
                ),
              ),
              if (state != null && current != null) _Dots(passed: state.passed, total: state.total),
              Expanded(
                child: AsyncBody<WrapUpState>(
                  value: value,
                  onRetry: () => ref.invalidate(wrapUpControllerProvider(_key(shopId!))),
                  builder: (s) {
                    final card = s.current;
                    if (card == null) {
                      return _Done(
                        shopId: shopId!,
                        date: widget.date,
                        skipped: s.skippedCount,
                        onReview: () => _controller(shopId).reviewSkipped(),
                      );
                    }
                    return ListView(
                      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.xxl),
                      children: [
                        _Who(card: card),
                        const SizedBox(height: AppSpacing.lg),
                        switch (card.kind) {
                          WrapUpKind.unresolved => _UnresolvedActions(
                            busy: _busy,
                            onAction: (a) => _act(shopId!, card.visit, a),
                          ),
                          WrapUpKind.unpaid => _PaymentForm(
                            key: ValueKey(cardKey(card)),
                            prefill: card.prefill,
                            busy: _busy,
                            onSave: (total, method) => _savePayment(shopId!, card.visit.visitId, total, method),
                          ),
                          WrapUpKind.reportUnsent => _ReportActions(
                            busy: _busy,
                            canStopCounting: ref.watch(isOwnerProvider),
                            onPreview: () => _previewReport(shopId!, card.visit.visitId),
                            onSkip: () => _skipReport(shopId!, card.visit.visitId),
                            onStopCounting: () => _stopCounting(shopId!),
                          ),
                        },
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: AppStrings.wrapUpSkip,
                          onPressed: _busy ? null : () => _controller(shopId!).skip(),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 넘김 점 — 지나온 장은 채운다. 장이 많으면(열둘 넘게) 위의 글로 충분하다.
class _Dots extends StatelessWidget {
  const _Dots({required this.passed, required this.total});

  final int passed;
  final int total;

  @override
  Widget build(BuildContext context) {
    if (total > 12 || total < 2) return const SizedBox.shrink();
    return ExcludeSemantics(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
        child: Row(
          children: [
            for (var i = 0; i < total; i++)
              Container(
                width: 6,
                height: 6,
                margin: const EdgeInsets.only(right: 4),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: i <= passed ? AppColors.ink : AppColors.line,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// 장 위 — 종류, 사진·이름·시각·메뉴(어떤 아이인지 안다).
class _Who extends ConsumerWidget {
  const _Who({required this.card});

  final WrapUpCard card;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final visit = card.visit;
    final images = ref.watch(mediaImagesProvider);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            switch (card.kind) {
              WrapUpKind.unresolved => AppStrings.wrapUpKindUnresolved,
              WrapUpKind.unpaid => AppStrings.wrapUpKindUnpaid,
              WrapUpKind.reportUnsent => AppStrings.wrapUpKindReport,
            },
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              AppPhotoTile(image: card.photoUrl == null ? null : images.of(card.photoUrl!), size: 56),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(visitsTitle([visit]), style: AppTypography.titleKo, overflow: TextOverflow.ellipsis),
                    Text(
                      '${hhmm(visit.startsAt.wall)} · ${menusLabel(visit.menus)}',
                      style: AppTypography.caption,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _UnresolvedActions extends StatelessWidget {
  const _UnresolvedActions({required this.busy, required this.onAction});

  final bool busy;
  final ValueChanged<VisitAction> onAction;

  @override
  Widget build(BuildContext context) {
    VoidCallback? on(VisitAction a) => busy ? null : () => onAction(a);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppButton(label: AppStrings.actionComplete, filled: true, onPressed: on(VisitAction.complete)),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(child: AppButton(label: AppStrings.actionNoShow, onPressed: on(VisitAction.noShow))),
            const SizedBox(width: AppSpacing.sm),
            Expanded(child: AppButton(label: AppStrings.actionCancelVisit, onPressed: on(VisitAction.cancel))),
          ],
        ),
      ],
    );
  }
}

/// 결제 장 — 총액(채워 둔 값, 숫자만)과 결제 수단(지난번 수단)을 고쳐 [저장]. 둘 다 있어야 눌린다.
class _PaymentForm extends StatefulWidget {
  const _PaymentForm({super.key, required this.prefill, required this.busy, required this.onSave});

  final WrapUpPrefill? prefill;
  final bool busy;
  final void Function(int total, PaymentMethod method) onSave;

  @override
  State<_PaymentForm> createState() => _PaymentFormState();
}

class _PaymentFormState extends State<_PaymentForm> {
  late final _total = TextEditingController(text: widget.prefill?.totalAmount?.toString() ?? '');
  late PaymentMethod? _method = widget.prefill?.paymentMethod;

  @override
  void dispose() {
    _total.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final total = int.tryParse(_total.text);
    final method = _method;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          key: const ValueKey('wrap-up-total'),
          controller: _total,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(9)],
          decoration: const InputDecoration(labelText: AppStrings.totalLabel, suffixText: AppStrings.wonUnit),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.md),
        const Text(AppStrings.paymentLabel, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          children: [
            for (final m in PaymentMethod.values)
              AppChoiceChip(
                label: paymentLabel(m),
                selected: m == method,
                onTap: () => setState(() => _method = m),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.save,
          filled: true,
          busy: widget.busy,
          onPressed: widget.busy || total == null || method == null ? null : () => widget.onSave(total, method),
        ),
      ],
    );
  }
}

class _ReportActions extends StatelessWidget {
  const _ReportActions({
    required this.busy,
    required this.canStopCounting,
    required this.onPreview,
    required this.onSkip,
    required this.onStopCounting,
  });

  final bool busy;
  final bool canStopCounting;
  final VoidCallback onPreview;
  final VoidCallback onSkip;
  final VoidCallback onStopCounting;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppButton(label: AppStrings.wrapUpReportPreview, filled: true, onPressed: busy ? null : onPreview),
        const SizedBox(height: AppSpacing.sm),
        AppButton(label: AppStrings.wrapUpReportSkip, onPressed: busy ? null : onSkip),
        if (canStopCounting)
          Center(
            child: Pressable(
              semanticLabel: AppStrings.wrapUpStopCounting,
              onTap: busy ? null : onStopCounting,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                child: Text(
                  AppStrings.wrapUpStopCounting,
                  style: AppTypography.caption.copyWith(decoration: TextDecoration.underline),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// 끝 화면 — 그날의 수(금액 없음), 남겨 둔 것과 [다시 보기], [닫기].
class _Done extends ConsumerWidget {
  const _Done({required this.shopId, required this.date, required this.skipped, required this.onReview});

  final int shopId;
  final DateTime date;
  final int skipped;
  final VoidCallback onReview;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final today = ref.watch(todayProvider);
    final day = ref.watch(dayVisitsProvider((shopId: shopId, date: date))).value;
    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.xl, AppSpacing.lg, AppSpacing.xxl),
      children: [
        Text(
          sameDay(date, today) ? AppStrings.wrapUpDoneToday : AppStrings.wrapUpDonePast,
          style: AppTypography.titleKo,
          textAlign: TextAlign.center,
        ),
        if (day != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            AppStrings.wrapUpDoneCounts(
              day.counts.completed,
              day.items.where((i) => i.marks.contains(VisitMark.reportSent)).length,
            ),
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
        ],
        if (skipped > 0) ...[
          const SizedBox(height: AppSpacing.lg),
          Text(AppStrings.wrapUpSkipped(skipped), style: AppTypography.caption, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.sm),
          AppButton(label: AppStrings.wrapUpReview, onPressed: onReview),
        ],
        const SizedBox(height: AppSpacing.sm),
        AppButton(label: AppStrings.close, filled: true, onPressed: () => context.pop()),
      ],
    );
  }
}
