import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/state/customer_input.dart';
import '../api/record_models.dart';
import '../api/visit_models.dart';
import '../state/record_rules.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'record_photos.dart';
import 'visit_actions.dart';
import 'visit_labels.dart';

/// 방문 하나 — 대표 사진과 상태, 이름·품종·몸무게·보호자, 사진 줄과 [사진 추가](미용 중·완료),
/// "오늘의 케어"(기록)와 [기록 수정], 날짜·메뉴·메모·지난 방문·노쇼 횟수, 상태에 맞는 버튼
/// (설계 9.1, ④ 설계 10.1 ③). `···`에 수정·되돌리기·바로 완료·다음 예약 잡기·기록 삭제(사장)가 있다.
///
/// 버튼은 같은 묶음에서 이 방문과 상태가 같은 방문들을 한 번에 바꾼다 —
/// 두 마리가 함께 왔으면 함께 시작하고 함께 끝낸다.
class VisitDetailScreen extends ConsumerStatefulWidget {
  const VisitDetailScreen({super.key, required this.visitId});

  final int visitId;

  @override
  ConsumerState<VisitDetailScreen> createState() => _VisitDetailScreenState();
}

class _VisitDetailScreenState extends ConsumerState<VisitDetailScreen> {
  bool _busy = false;
  // 완료 흐름(기록 화면 → 다음 예약 시트)이나 다른 시트가 떠 있는 동안의
  // 재진입을 막는다. "보내는 중"이 아니므로 버튼에 스피너를 켜지 않는다 —
  // `_busy`와는 다른 신호다.
  bool _asking = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  /// 앵커(이 방문) + 같은 묶음에서 상태가 같은 형제. 서버의 `group`은 자기를
  /// 뺀 형제만 주므로 앵커를 먼저 넣는다.
  List<int> _sameStatusIds(VisitDetail detail) => [
    detail.visit.visitId,
    for (final v in detail.group)
      if (v.status == detail.visit.status) v.visitId,
  ];

  Future<void> _act(VisitDetail detail, VisitAction action) async {
    final shopId = _shopId;
    if (shopId == null || _busy || _asking) return;
    setState(() => _asking = true);
    VisitChoice? choice;
    try {
      choice = await askVisitAction(
        context,
        ref,
        shopId: shopId,
        action: action,
        anchorVisitId: detail.visit.visitId,
      );
    } finally {
      if (mounted) setState(() => _asking = false);
    }
    if (choice == null || !mounted) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await sendVisitAction(
        ref,
        shopId: shopId,
        choice: choice,
        ids: _sameStatusIds(detail),
      );
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _openMore(VisitDetail detail) async {
    final status = detail.visit.status;
    final choice = await AppSheet.show<_More>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status != VisitStatus.canceled && status != VisitStatus.noShow)
            AppSheetAction(
              label: AppStrings.edit,
              onTap: () => Navigator.of(context).pop(_More.edit),
            ),
          if (status == VisitStatus.reserved)
            AppSheetAction(
              label: AppStrings.actionCompleteNow,
              onTap: () => Navigator.of(context).pop(_More.completeNow),
            ),
          if (status != VisitStatus.reserved)
            AppSheetAction(
              label: AppStrings.actionRevert,
              onTap: () => Navigator.of(context).pop(_More.revert),
            ),
          if (status == VisitStatus.completed)
            AppSheetAction(
              label: AppStrings.actionNextReservation,
              onTap: () => Navigator.of(context).pop(_More.next),
            ),
          // 기록 삭제는 record:delete — 사장만(설계 9절).
          if (detail.record != null && ref.read(isOwnerProvider))
            AppSheetAction(
              label: AppStrings.deleteRecord,
              onTap: () => Navigator.of(context).pop(_More.deleteRecord),
            ),
        ],
      ),
    );
    if (choice == null || !mounted) return;
    switch (choice) {
      case _More.edit:
        context.push('/visits/${detail.visit.visitId}/edit');
      case _More.next:
        await _openNext(detail);
      case _More.completeNow:
        await _act(detail, VisitAction.complete);
      case _More.revert:
        await _act(detail, VisitAction.revert);
      case _More.deleteRecord:
        await _deleteRecord(detail);
    }
  }

  Future<void> _deleteRecord(VisitDetail detail) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            AppStrings.deleteRecordConfirm,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.deleteRecord,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref
          .read(visitCommandsProvider)
          .deleteRecord(shopId, detail.visit.visitId);
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _openNext(VisitDetail detail) async {
    final shopId = _shopId;
    if (shopId == null || _busy || _asking) return;
    setState(() => _asking = true);
    try {
      final draft = await ref
          .read(visitCommandsProvider)
          .nextDraft(shopId, detail.visit.visitId);
      if (mounted) context.push('/visits/new', extra: draft);
    } catch (e) {
      if (mounted) setState(() => _errorText = messageFor(e));
    } finally {
      if (mounted) setState(() => _asking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final key = (shopId: shopId ?? 0, visitId: widget.visitId);
    final detail = shopId == null
        ? const AsyncValue<VisitDetail>.loading()
        : ref.watch(visitDetailProvider(key));
    final data = detail.value;
    return Scaffold(
      key: ScreenKeys.visitDetail,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 머리는 로딩·오류 상태에서도 보인다 — 오류에 갇혀도 뒤로 갈 수 있다.
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.sm,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    const Text(
                      AppStrings.visitTitleEn,
                      style: AppTypography.titleEn,
                    ),
                    const Spacer(),
                    if (data != null)
                      Pressable(
                        semanticLabel: AppStrings.more,
                        onTap: (_busy || _asking)
                            ? null
                            : () => _openMore(data),
                        child: const Icon(Icons.more_horiz),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: detail.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => AppErrorRetry(
                    message: messageFor(error),
                    onRetry: () => ref.invalidate(visitDetailProvider(key)),
                  ),
                  data: (detail) => _Body(
                    detail: detail,
                    busy: _busy,
                    errorText: _errorText,
                    onAction: (action) => _act(detail, action),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({
    required this.detail,
    required this.busy,
    required this.errorText,
    required this.onAction,
  });

  final VisitDetail detail;
  final bool busy;
  final String? errorText;
  final ValueChanged<VisitAction> onAction;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final visit = detail.visit;
    final pet = visit.pet;
    final record = detail.record;
    final media = record?.media ?? const <RecordMedia>[];
    // 기록은 미용 중·완료 방문에만 쓴다(설계 8절). 사진은 시작부터 넣는다 — 미용 중이면 전, 완료면 후.
    final recordable =
        visit.status == VisitStatus.inProgress ||
        visit.status == VisitStatus.completed;
    final cover = coverOf(media);
    // 서버의 group 은 이미 자기를 뺀 형제만 준다.
    final others = detail.group;
    final previous = detail.previousVisit;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        // 대표 사진(후 → 전). 기울어진 넘기기·크게 보기는 ④-2b.
        Center(
          child: AppPhotoTile(
            image: cover == null
                ? null
                : ref
                      .watch(mediaImagesProvider)
                      .of(cover.displayUrl ?? cover.thumbUrl),
            size: 160,
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Wrap(
          spacing: AppSpacing.sm,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(visitsTitle([visit]), style: AppTypography.titleKo),
            AppChip(label: statusLabel(visit.status)),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          [
            if (pet != null) ...[pet.breed, formatWeight(pet.weightKg)],
            ownerLabel(visit.customer),
          ].join(' · '),
          style: AppTypography.caption,
        ),
        if (recordable || media.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          RecordPhotoStrip(
            visitId: visit.visitId,
            media: [for (final m in media) FormMedia(m, m.phase)],
            onAdd: !recordable || busy
                ? null
                : () => addPhotos(
                    context,
                    ref,
                    shopId: ref.read(selectedShopIdProvider)!,
                    visitId: visit.visitId,
                    phase: visit.status == VisitStatus.inProgress
                        ? MediaPhase.before
                        : MediaPhase.after,
                    attached: media.length,
                  ),
          ),
        ],
        const SizedBox(height: AppSpacing.lg),
        // 사진만 붙은 기록(대기열이 만든 것)은 적은 것이 없어 케어 카드를 숨기고 [기록 쓰기]로 보인다.
        if (!isBlankRecord(record))
          _CareCard(record: record!, startsAt: visit.startsAt),
        if (recordable)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: AppButton(
              label: isBlankRecord(record)
                  ? AppStrings.writeRecord
                  : AppStrings.editRecord,
              onPressed: busy
                  ? null
                  : () => context.push('/visits/${visit.visitId}/record'),
            ),
          ),
        _InfoCard(
          label: AppStrings.visitDateLabel,
          value:
              '${dayLabel(visit.startsAt.wall)} · ${hhmm(visit.startsAt.wall)} — ${hhmm(visit.endsAt.wall)}',
        ),
        _InfoCard(label: AppStrings.menuLabel, value: menusLabel(visit.menus)),
        if (visit.memo != null)
          _InfoCard(label: AppStrings.visitMemoLabel, value: visit.memo!),
        if (visit.cancelReason != null)
          _InfoCard(
            label: AppStrings.cancelReasonLabel,
            value: visit.cancelReason == 'shop_reason'
                ? AppStrings.reasonShopReason
                : AppStrings.reasonCustomerRequest,
          ),
        _InfoCard(
          label: AppStrings.previousVisitLabel,
          value:
              '${previous == null ? AppStrings.none : dayLabel(previous.startsAt.wall)} · ${AppStrings.noShowCount(detail.noShowCount)}',
        ),
        if (others.isNotEmpty) _GroupCard(others: others),
        if (errorText != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(errorText!, style: AppTypography.caption),
          ),
        const SizedBox(height: AppSpacing.md),
        _StatusButtons(status: visit.status, busy: busy, onAction: onAction),
      ],
    );
  }
}

/// 상태에 맞는 버튼만 — 예약됨이면 [노쇼 · 취소 · 시작], 미용 중이면 [완료].
class _StatusButtons extends StatelessWidget {
  const _StatusButtons({
    required this.status,
    required this.busy,
    required this.onAction,
  });

  final VisitStatus status;
  final bool busy;
  final ValueChanged<VisitAction> onAction;

  @override
  Widget build(BuildContext context) {
    VoidCallback? on(VisitAction action) =>
        busy ? null : () => onAction(action);
    return switch (status) {
      VisitStatus.reserved => Row(
        children: [
          AppButton(
            label: AppStrings.actionNoShow,
            onPressed: on(VisitAction.noShow),
          ),
          const SizedBox(width: AppSpacing.sm),
          AppButton(
            label: AppStrings.actionCancelVisit,
            onPressed: on(VisitAction.cancel),
          ),
          const Spacer(),
          AppButton(
            label: AppStrings.actionStart,
            filled: true,
            busy: busy,
            onPressed: on(VisitAction.start),
          ),
        ],
      ),
      VisitStatus.inProgress => AppButton(
        label: AppStrings.actionComplete,
        filled: true,
        busy: busy,
        onPressed: on(VisitAction.complete),
      ),
      VisitStatus.completed ||
      VisitStatus.canceled ||
      VisitStatus.noShow ||
      VisitStatus.unknown => const SizedBox.shrink(),
    };
  }
}

/// "오늘의 케어" — 실제 메뉴와 금액, 몸무게, 케어 메모, 총액·결제 수단, 내부 메모(설계 10.1 ③).
/// 적은 칸만 보인다.
class _CareCard extends StatelessWidget {
  const _CareCard({required this.record, required this.startsAt});

  final VisitRecord record;
  final ShopTime startsAt;

  @override
  Widget build(BuildContext context) {
    final weight = record.weightKg;
    final total = record.totalAmount;
    final payment = record.paymentMethod;
    final lines = [
      for (final i in record.items)
        '${i.name} · ${AppStrings.wonText(i.amount)}',
      if (weight != null) '${AppStrings.weightLabel} ${formatWeight(weight)}',
      if (total != null || payment != null)
        [
          if (total != null)
            '${AppStrings.totalLabel} ${AppStrings.wonText(total)}',
          if (payment != null) paymentLabel(payment),
        ].join(' · '),
    ];
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: SizedBox(
        width: double.infinity,
        child: AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${AppStrings.todayCareLabel} · ${dayLabel(startsAt.wall)}',
                style: AppTypography.caption,
              ),
              const SizedBox(height: AppSpacing.xs),
              for (final line in lines) Text(line, style: AppTypography.body),
              if (record.careNote != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(record.careNote!, style: AppTypography.body),
              ],
              if (record.internalNote != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '${AppStrings.internalNoteLabel} · ${record.internalNote}',
                  style: AppTypography.caption,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: SizedBox(
        width: double.infinity,
        child: AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: AppTypography.caption),
              const SizedBox(height: AppSpacing.xs),
              Text(value, style: AppTypography.body),
            ],
          ),
        ),
      ),
    );
  }
}

/// 같은 묶음의 다른 방문. 누르면 그 방문으로 화면을 바꿔 끼운다.
class _GroupCard extends StatelessWidget {
  const _GroupCard({required this.others});

  final List<Visit> others;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(AppStrings.groupLabel, style: AppTypography.caption),
            for (final v in others)
              Pressable(
                semanticLabel: visitsTitle([v]),
                onTap: () => context.pushReplacement('/visits/${v.visitId}'),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                  child: Row(
                    children: [
                      Text(visitsTitle([v]), style: AppTypography.bodyStrong),
                      const SizedBox(width: AppSpacing.sm),
                      AppChip(label: statusLabel(v.status)),
                      const Spacer(),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// `···` 시트의 항목. 문자열 대신 닫힌 enum 이라 처리 `switch`가 완전 열거된다.
enum _More { edit, completeNow, revert, next, deleteRecord }
