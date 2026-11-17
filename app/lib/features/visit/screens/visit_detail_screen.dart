import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/proxy/share_sheet.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/today_provider.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_photo_pager.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/state/customer_input.dart';
import '../api/record_models.dart';
import '../api/report_models.dart';
import '../api/visit_marks.dart';
import '../api/visit_models.dart';
import '../state/check_rules.dart';
import '../state/photo_edits.dart';
import '../state/record_rules.dart';
import '../state/report_commands.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'record_photos.dart';
import 'send_bundle_sheet.dart';
import 'visit_actions.dart';
import 'visit_checks_block.dart';
import 'visit_labels.dart';
import 'visit_notifications_block.dart';

/// 방문 하나 — 기울어진 사진 넘기기(누르면 크게 보기)와 그 위 이름 카드(이름·품종·몸무게·상태), 보호자, 사진 줄과 [사진 추가](미용 중·완료),
/// "오늘의 케어"(기록)와 [기록 수정], 날짜·메뉴·메모·지난 방문·노쇼 횟수, 상태에 맞는 버튼
/// (설계 9.1, ④ 설계 10.1 ③). `···`에 수정·되돌리기·바로 완료·다음 예약 잡기·기록 삭제(사장)가 있다.
///
/// 완료한 방문에는 알림장(⑤ 설계 9.1)이 붙는다 — 보내기 전에는 "알림장" 줄과 [알림장 보내기],
/// 보낸 뒤에는 꼬리표 "완료 · 알림장 보냄"·확인 카드·[다시 공유], `···`에 [보낼 사진 고르기]·[링크 끊기].
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
          // 예약 안내와 동의서 링크를 한 번에(⑪-B) — 저장할 때 보내지 않았거나 다시 보낼 때.
          if (status == VisitStatus.reserved)
            AppSheetAction(
              label: AppStrings.actionSendToGuardian,
              onTap: () => Navigator.of(context).pop(_More.sendToGuardian),
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
          // 보낸 알림장 — 뺄 사진을 다시 고르거나 링크를 끊는다(record:write — 직원도 한다).
          if (detail.report.live) ...[
            AppSheetAction(
              label: AppStrings.reportPickMedia,
              onTap: () => Navigator.of(context).pop(_More.pickReportMedia),
            ),
            AppSheetAction(
              label: AppStrings.reportRevoke,
              onTap: () => Navigator.of(context).pop(_More.revokeReport),
            ),
          ],
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
      case _More.sendToGuardian:
        final shopId = ref.read(selectedShopIdProvider);
        if (shopId == null) return;
        await openSendBundle(
          context,
          ref,
          shopId: shopId,
          visitId: detail.visit.visitId,
          tellWhy: true,
        );
      case _More.next:
        await _openNext(detail);
      case _More.completeNow:
        await _act(detail, VisitAction.complete);
      case _More.revert:
        await _act(detail, VisitAction.revert);
      case _More.pickReportMedia:
        context.push('/visits/${detail.visit.visitId}/report?pick=1');
      case _More.revokeReport:
        await _confirmThen(
          question: AppStrings.reportRevokeConfirm,
          label: AppStrings.reportRevoke,
          send: (shopId) => ref
              .read(reportCommandsProvider)
              .revoke(shopId, detail.visit.visitId),
        );
      case _More.deleteRecord:
        await _confirmThen(
          question: AppStrings.deleteRecordConfirm,
          label: AppStrings.deleteRecord,
          send: (shopId) => ref
              .read(visitCommandsProvider)
              .deleteRecord(shopId, detail.visit.visitId),
        );
    }
  }

  /// 되돌릴 수 없는 일(기록 삭제·링크 끊기)은 한 번 묻고 보낸다. 시트를 닫으면 보내지 않는다.
  Future<void> _confirmThen({
    required String question,
    required String label,
    required Future<void> Function(int shopId) send,
  }) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            question,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: label,
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
      await send(shopId);
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  /// [다시 공유] — 서버를 부르지 않는다. 방문 상세가 읽은 주소를 그대로 공유 시트에 넘긴다(보내기
  /// PUT 을 다시 부르면 뺀 표시를 건드린다). 살아 있는 동안은 같은 링크다.
  Future<void> _shareReport(VisitDetail detail, Rect origin) async {
    try {
      await ref
          .read(shareSheetProvider)
          .shareText(detail.report.url!, origin: origin);
    } on Exception {
      if (mounted) AppSnackBar.show(context, AppStrings.reportShareAgainFailed);
    }
  }

  /// 하루 마무리에서 넘긴 알림장을 되돌린다(⑬) — 다시 남은 일로 센다. 실패는 스낵바, 화면은 다시 읽은 값.
  Future<void> _unskipReport(VisitDetail detail) async {
    final shopId = _shopId;
    if (shopId == null || _busy || _asking) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(visitCommandsProvider)
          .unskipReport(shopId, detail.visit.visitId);
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    } finally {
      if (mounted) setState(() => _busy = false);
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
                child: AsyncBody<VisitDetail>(
                  value: detail,
                  onRetry: () => ref.invalidate(visitDetailProvider(key)),
                  onRefresh: () => ref.refresh(visitDetailProvider(key).future),
                  builder: (detail) => _Body(
                    detail: detail,
                    busy: _busy,
                    errorText: _errorText,
                    onAction: (action) => _act(detail, action),
                    onShareReport: (origin) => _shareReport(detail, origin),
                    onUnskipReport: () => _unskipReport(detail),
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
    required this.onShareReport,
    required this.onUnskipReport,
  });

  final VisitDetail detail;
  final bool busy;
  final String? errorText;
  final ValueChanged<VisitAction> onAction;
  final ValueChanged<Rect> onShareReport;
  final VoidCallback onUnskipReport;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final visit = detail.visit;
    final record = detail.record;
    final report = detail.report;
    final media = record?.media ?? const <RecordMedia>[];
    // 기록은 미용 중·완료 방문에만 쓴다(설계 8절). 사진은 시작부터 넣는다 — 미용 중이면 전, 완료면 후.
    final recordable =
        visit.status == VisitStatus.inProgress ||
        visit.status == VisitStatus.completed;
    // 넘기기는 대표 사진부터(후 → 전 → 영상). 상세는 표시용, 영상은 포스터(설계 7.3).
    final gallery = galleryOrder(media);
    final images = ref.watch(mediaImagesProvider);
    final counts = {for (final p in MediaPhase.values) p: 0};
    // 서버의 group 은 이미 자기를 뺀 형제만 준다.
    final others = detail.group;
    final previous = detail.previousVisit;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg),
      children: [
        AppPhotoPager(
          photos: [
            for (final m in gallery)
              AppPagerPhoto(
                image: images.of(m.displayUrl ?? m.thumbUrl),
                label: phaseLabel(m.phase),
                semanticLabel: AppStrings.openPhotoLabel(
                  phaseLabel(m.phase),
                  counts.update(m.phase, (n) => n + 1),
                ),
                video: m.kind == MediaKind.video,
                durationSeconds: m.durationSeconds,
              ),
          ],
          onTap: (i) => context.push(
            '/visits/${visit.visitId}/photos/${gallery[i].mediaId}',
          ),
          overlay: _WhoCard(visit: visit, marks: detail.marks),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: AppSpacing.md),
              Text(
                AppStrings.ownerLine(ownerLabel(visit.customer)),
                style: AppTypography.caption,
              ),
              if (detail.checks.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.md),
                _DetailChecks(detail: detail),
              ],
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
                          attached: media,
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
              // 보낸 알림장의 확인 카드는 정보 카드 맨 위다(목업 ④).
              if (report.live)
                _ReportCard(report: report, today: ref.watch(todayProvider)),
              // 알림톡 내역(⑥-2) — 따로 읽는다. 줄이 없으면(연동 안 된 매장) 아무것도 그리지 않는다.
              VisitNotificationsBlock(
                visitKey: (
                  shopId: ref.watch(selectedShopIdProvider)!,
                  visitId: visit.visitId,
                ),
              ),
              _InfoCard(
                label: AppStrings.visitDateLabel,
                value:
                    '${dayLabel(visit.startsAt.wall)} · ${hhmm(visit.startsAt.wall)} — ${hhmm(visit.endsAt.wall)}',
              ),
              _InfoCard(
                label: AppStrings.menuLabel,
                value: menusLabel(visit.menus),
              ),
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
              // 하루 마무리에서 "보내지 않음"으로 넘긴 방문(⑬) — 여기서 되돌린다.
              if (visit.status == VisitStatus.completed &&
                  !report.live &&
                  detail.reportSkipped)
                _SkippedReportCard(busy: busy, onUnskip: onUnskipReport)
              // 아직 안 보낸 완료 방문 — 기록이 있어야 보낼 수 있다(없으면 서버가 409 로 거절한다).
              else if (visit.status == VisitStatus.completed && !report.live)
                _InfoCard(
                  label: AppStrings.reportLabel,
                  value: record == null
                      ? AppStrings.reportNeedsRecord
                      : AppStrings.reportNotSent,
                ),
              if (others.isNotEmpty) _GroupCard(others: others),
              if (errorText != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.sm),
                  child: Text(errorText!, style: AppTypography.caption),
                ),
              const SizedBox(height: AppSpacing.md),
              _StatusButtons(
                detail: detail,
                busy: busy,
                onAction: onAction,
                onShareReport: onShareReport,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// 이 방문의 "확인할 것"(③-B). 미용 동의 줄의 [받았어요]는 그 아이의 동의를 오늘로 적는다 —
/// 도는 동안 다시 누르지 못하고, 실패하면 스낵바로 알린다. 성공하면 상세를 다시 읽어 줄이 사라진다.
class _DetailChecks extends ConsumerStatefulWidget {
  const _DetailChecks({required this.detail});

  final VisitDetail detail;

  @override
  ConsumerState<_DetailChecks> createState() => _DetailChecksState();
}

class _DetailChecksState extends ConsumerState<_DetailChecks> {
  bool _busy = false;
  bool _sending = false;

  Future<void> _received(int petId) async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _busy) return;
    setState(() => _busy = true);
    String? failure;
    try {
      await ref.read(visitCommandsProvider).consentReceived(shopId, petId);
    } catch (e) {
      failure = messageFor(e);
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (failure != null) AppSnackBar.show(context, failure);
  }

  /// [동의서 보내기]·[다시 공유] — 링크를 만들고(있으면 같은 링크) 공유 시트에 넘긴다(⑪).
  /// 기준일은 이 방문의 날이다 — 그날에 유효한 동의를 받는다. 링크 주소는 어디에도 적지 않는다.
  Future<void> _send(int petId, Rect origin) async {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null || _sending) return;
    setState(() => _sending = true);
    String? failure;
    try {
      final link = await ref
          .read(visitCommandsProvider)
          .consentFormLink(shopId, petId, forDate: widget.detail.visit.startsAt.day);
      try {
        await ref.read(shareSheetProvider).shareText(link.url, origin: origin);
      } on Exception {
        // 링크는 만들어졌다 — 다시 누르면 같은 링크가 공유된다.
        failure = AppStrings.consentShareFailed;
      }
    } on ApiException catch (e) {
      // 손으로 [받았어요]를 적은 아이는 더 받을 것이 없다고 온다 — 무엇을 해야 하는지 말한다.
      failure = e.code == 'CONSENT_UP_TO_DATE' ? AppStrings.consentSendUpToDate : messageFor(e);
    } catch (e) {
      failure = messageFor(e);
    }
    if (!mounted) return;
    setState(() => _sending = false);
    if (failure != null) AppSnackBar.show(context, failure);
  }

  /// [여기서 서명] — 폰을 보호자에게 건네 그 자리에서 받는다. 돌아오면 확인할 것을 다시 읽는다.
  Future<void> _signHere(int petId) async {
    final day = isoDay(widget.detail.visit.startsAt.day);
    await context.push<void>('/consent/sign?pet_ids=$petId&for_date=$day');
    if (mounted) ref.read(visitCommandsProvider).refreshChecks();
  }

  @override
  Widget build(BuildContext context) {
    final detail = widget.detail;
    return VisitChecksBlock(
      sections: detailSections(
        detail.checks,
        petId: detail.visit.pet?.petId,
      ),
      onConsent: _received,
      consentBusy: _busy,
      onSend: _send,
      sendBusy: _sending,
      onSignHere: _signHere,
    );
  }
}

/// 넘기기 위의 이름 카드(기준 목업) — 이름, 품종·몸무게, 상태. 목업은 글래스지만 스크롤 화면이라 불투명
/// 카드다(기반 설계 6.2, `glass_boundary_test`). 알림장을 보냈으면 상태 뒤에 "알림장 보냄"이 붙는다.
class _WhoCard extends StatelessWidget {
  const _WhoCard({required this.visit, required this.marks});

  final Visit visit;

  /// 끝낸 일의 낱말(⑬ — 결제 완료·알림장 보냄 …).
  final List<VisitMark> marks;

  @override
  Widget build(BuildContext context) {
    final pet = visit.pet;
    return SizedBox(
      width: 220,
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    visitsTitle([visit]),
                    style: AppTypography.titleKo.copyWith(fontSize: 17),
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (pet != null)
                    Text(
                      '${pet.breed} · ${formatWeight(pet.weightKg)}',
                      style: AppTypography.caption,
                    ),
                ],
              ),
            ),
            AppChip(
              label: [
                statusLabel(visit.status),
                for (final m in marks) markLabel(m),
              ].join(' · '),
            ),
          ],
        ),
      ),
    );
  }
}

/// 상태에 맞는 버튼만 — 예약됨이면 [노쇼 · 취소 · 시작], 미용 중이면 [완료], 완료면 알림장
/// (보냈으면 [다시 공유], 안 보냈고 기록이 있으면 [알림장 보내기]).
class _StatusButtons extends StatelessWidget {
  const _StatusButtons({
    required this.detail,
    required this.busy,
    required this.onAction,
    required this.onShareReport,
  });

  final VisitDetail detail;
  final bool busy;
  final ValueChanged<VisitAction> onAction;

  /// [다시 공유] — 공유 시트가 붙을 자리(버튼의 화면 사각형, 아이패드의 말풍선)를 넘긴다.
  final ValueChanged<Rect> onShareReport;

  @override
  Widget build(BuildContext context) {
    VoidCallback? on(VisitAction action) =>
        busy ? null : () => onAction(action);
    return switch (detail.visit.status) {
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
      VisitStatus.completed when detail.report.live => Builder(
        builder: (context) => AppButton(
          label: AppStrings.reportShareAgain,
          filled: true,
          onPressed: busy
              ? null
              : () {
                  final box = context.findRenderObject()! as RenderBox;
                  onShareReport(box.localToGlobal(Offset.zero) & box.size);
                },
        ),
      ),
      VisitStatus.completed when detail.record != null => AppButton(
        label: AppStrings.reportStart,
        filled: true,
        onPressed: busy
            ? null
            : () => context.push('/visits/${detail.visit.visitId}/report'),
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

/// 보낸 알림장의 확인 카드(목업 ④) — 보호자가 열었는지와 처음 연 시각, 링크 기간. 열람은 처음 연
/// 시각만 보인다(설계 2절).
class _ReportCard extends StatelessWidget {
  const _ReportCard({required this.report, required this.today});

  final ReportLink report;
  final DateTime today;

  /// 처음 연 시각 — 오늘이 아니면 날짜도 붙인다.
  String _at(DateTime viewed) => sameDay(viewed, today)
      ? hhmm(viewed)
      : '${dayLabel(viewed)} ${hhmm(viewed)}';

  @override
  Widget build(BuildContext context) {
    final viewed = report.firstViewedAt?.wall;
    final until = report.expiresAt?.wall;
    final period = until == null
        ? AppStrings.reportOpenForever
        : AppStrings.reportOpenUntil(until.month, until.day);
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: AppCard(
        child: Row(
          children: [
            if (viewed != null) ...[
              Container(
                width: 28,
                height: 28,
                decoration: const BoxDecoration(
                  color: AppColors.ink,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.check,
                  size: 16,
                  color: AppColors.white,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
            ],
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    viewed == null
                        ? AppStrings.reportNotViewed
                        : AppStrings.reportViewed,
                    style: AppTypography.bodyStrong,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    viewed == null ? period : '${_at(viewed)} · $period',
                    style: AppTypography.caption,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 알림장을 보내지 않기로 한 방문(⑬) — 줄과 [되돌리기].
class _SkippedReportCard extends StatelessWidget {
  const _SkippedReportCard({required this.busy, required this.onUnskip});

  final bool busy;
  final VoidCallback onUnskip;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: AppCard(
        child: Row(
          children: [
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(AppStrings.reportLabel, style: AppTypography.caption),
                  SizedBox(height: AppSpacing.xs),
                  Text(AppStrings.reportSkipped, style: AppTypography.body),
                ],
              ),
            ),
            AppButton(
              label: AppStrings.reportUnskip,
              onPressed: busy ? null : onUnskip,
            ),
          ],
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
enum _More {
  edit,
  sendToGuardian,
  completeNow,
  revert,
  next,
  pickReportMedia,
  revokeReport,
  deleteRecord,
}
