import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../customer/state/customer_input.dart';
import '../api/visit_models.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'visit_actions.dart';
import 'visit_labels.dart';

/// 방문 하나 — 사진 자리와 상태, 이름·품종·몸무게·보호자, 날짜·메뉴·메모·
/// 지난 방문·노쇼 횟수, 상태에 맞는 버튼(설계 9.1). `···`에 수정·되돌리기·
/// 바로 완료·다음 예약 잡기가 있다.
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
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  /// 같은 묶음에서 이 방문과 상태가 같은 방문(자기 포함).
  List<int> _sameStatusIds(VisitDetail detail) => [
    for (final v in detail.group)
      if (v.status == detail.visit.status) v.visitId,
  ];

  Future<void> _act(VisitDetail detail, String action) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    final choice = await askVisitAction(
      context,
      ref,
      shopId: shopId,
      action: action,
      anchorVisitId: detail.visit.visitId,
    );
    if (choice == null || !mounted) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await sendVisitAction(
        context,
        ref,
        shopId: shopId,
        choice: choice,
        ids: _sameStatusIds(detail),
        anchorVisitId: detail.visit.visitId,
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
    final choice = await AppSheet.show<String>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status != VisitStatus.canceled && status != VisitStatus.noShow)
            const _SheetAction(label: AppStrings.edit, value: 'edit'),
          if (status == VisitStatus.reserved)
            const _SheetAction(
              label: AppStrings.actionCompleteNow,
              value: VisitAction.complete,
            ),
          if (status != VisitStatus.reserved)
            const _SheetAction(
              label: AppStrings.actionRevert,
              value: VisitAction.revert,
            ),
          if (status == VisitStatus.completed)
            const _SheetAction(
              label: AppStrings.actionNextReservation,
              value: 'next',
            ),
        ],
      ),
    );
    if (choice == null || !mounted) return;
    switch (choice) {
      case 'edit':
        context.push('/visits/${detail.visit.visitId}/edit');
      case 'next':
        await _openNext(detail);
      default:
        await _act(detail, choice);
    }
  }

  Future<void> _openNext(VisitDetail detail) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    try {
      final draft = await ref
          .read(visitCommandsProvider)
          .nextDraft(shopId, detail.visit.visitId);
      if (mounted) context.push('/visits/new', extra: draft);
    } catch (e) {
      if (mounted) setState(() => _errorText = messageFor(e));
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
                        onTap: _busy ? null : () => _openMore(data),
                        child: const Icon(Icons.more_horiz),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: detail.when(
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
                              ref.invalidate(visitDetailProvider(key)),
                        ),
                      ],
                    ),
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

class _Body extends StatelessWidget {
  const _Body({
    required this.detail,
    required this.busy,
    required this.errorText,
    required this.onAction,
  });

  final VisitDetail detail;
  final bool busy;
  final String? errorText;
  final ValueChanged<String> onAction;

  @override
  Widget build(BuildContext context) {
    final visit = detail.visit;
    final pet = visit.pet;
    final others = [
      for (final v in detail.group)
        if (v.visitId != visit.visitId) v,
    ];
    final previous = detail.previousVisit;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        // 사진은 ④에서 붙인다 — 지금은 회색 자리.
        const Center(child: AppPhotoTile(image: null, size: 160)),
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
        const SizedBox(height: AppSpacing.lg),
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

  final String status;
  final bool busy;
  final ValueChanged<String> onAction;

  @override
  Widget build(BuildContext context) {
    VoidCallback? on(String action) => busy ? null : () => onAction(action);
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
      _ => const SizedBox.shrink(),
    };
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

class _SheetAction extends StatelessWidget {
  const _SheetAction({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: () => Navigator.of(context).pop(value),
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        alignment: Alignment.center,
        child: Text(label, style: AppTypography.body),
      ),
    );
  }
}
