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
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_pick_tile.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/app_switch.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/record_models.dart';
import '../api/report_models.dart';
import '../state/notification_commands.dart';
import '../state/report_commands.dart';
import '../state/report_providers.dart';
import '../state/report_rules.dart';
import '../state/visit_providers.dart';
import 'visit_labels.dart';

/// 보일 것이 없어 보낼 수 없을 때의 안내 — 서버가 같은 이유로 거절할 때(422 `REPORT_EMPTY`)와 같은 문구다.
final _emptyText = messageFor(
  ApiException(statusCode: 422, code: 'REPORT_EMPTY', message: ''),
);

/// 알림장 보내기 전 미리보기(⑤ 설계 3.2·9.1, 목업 ②) — 보호자가 볼 사진·영상과 케어 메모, 함께 보이는
/// 항목, 링크 기간.
///
/// 사진·영상은 누르면 빠지고 다시 누르면 되살아난다. [보내기]는 뺀 것을 저장하고 링크를 만들어 공유
/// 시트에 넘긴 뒤 `true`로 닫힌다. [picking]이면 보낸 뒤의 [보낼 사진 고르기]다 — 버튼이 [저장]이고
/// 공유 시트를 열지 않는다.
class ReportPreviewScreen extends ConsumerStatefulWidget {
  const ReportPreviewScreen({
    super.key,
    required this.visitId,
    this.picking = false,
  });

  final int visitId;
  final bool picking;

  @override
  ConsumerState<ReportPreviewScreen> createState() =>
      _ReportPreviewScreenState();
}

class _ReportPreviewScreenState extends ConsumerState<ReportPreviewScreen> {
  /// 이번에 누른 것(미디어 ID → 뺄지)만 든다. 서버의 뺌 위에 덮어 보이고, 보낼 때도 직전에 다시 읽은
  /// 서버 상태 위에 이것만 덮는다(`ReportCommands.send`) — 미리보기를 다시 읽어도 비우지 않는다.
  final _changes = <int, bool>{};

  /// 공유 시트가 붙을 자리(아이패드의 말풍선)를 버튼에서 잰다.
  final _buttonKey = GlobalKey();

  bool _busy = false;

  /// 이 알림장에 리뷰 남기기 줄을 넣을지(⑫) — 누르지 않았으면 null 이고, 보낼 때 명령이 다시 읽은 링크의
  /// 값(없으면 넣음)으로 채운다.
  bool? _showReview;

  /// 링크를 만든 뒤 알림톡 결과를 기다리는 중 — 단추는 돌지만 뒤로 갈 수 있다.
  bool _awaiting = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  VisitKey get _key => (shopId: _shopId ?? 0, visitId: widget.visitId);

  bool _hidden(ReportMedia media) => _changes[media.mediaId] ?? media.hidden;

  /// 눌러서 뒤집는다. 서버의 값으로 되돌아왔으면 누르지 않은 것으로 친다 — 그 사이 다른 기기가 바꾼 것을
  /// 내 보내기가 덮지 않게.
  void _toggle(ReportMedia media) => setState(() {
    final next = !_hidden(media);
    if (next == media.hidden) {
      _changes.remove(media.mediaId);
    } else {
      _changes[media.mediaId] = next;
    }
  });

  /// [고치기] — 기록 화면에서 돌아오면 미리보기를 다시 읽는다(기록 저장은 미리보기를 무효화하지 않는다).
  Future<void> _editNote() async {
    await context.push('/visits/${widget.visitId}/record');
    if (mounted) ref.invalidate(visitReportProvider(_key));
  }

  Future<void> _send() async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    final notifications = ref.read(notificationCommandsProvider);
    // 알림톡으로 나가는지 보려면 보내기 전에 있던 알림장 알림톡 줄을 알아야 한다 — 이번 보내기가 만든
    // 줄만 결과로 친다(끊고 다시 보낼 때 옛 '보냄' 줄을 새 발송으로 알리지 않게). 고르기는 보지 않는다.
    final before = widget.picking
        ? null
        : await notifications.reportRowIds(shopId, widget.visitId);
    final VisitReportPreview sent;
    try {
      sent = await ref
          .read(reportCommandsProvider)
          .send(
            shopId,
            widget.visitId,
            changes: _changes,
            onlyIfLive: widget.picking,
            showReview: _showReview,
          );
    } catch (e) {
      // 실패해도 `send`가 미리보기를 다시 읽게 한다 — 누른 것은 그대로 두고 문구만 보인다.
      if (!mounted) return;
      // 고르는 사이 링크가 닫혔다 — 남아 있으면 [저장]이 계속 실패하니 알리고 닫는다.
      if (widget.picking && e is ApiException && e.code == 'REPORT_NOT_FOUND') {
        setState(() => _busy = false);
        AppSnackBar.show(context, messageFor(e));
        context.pop();
        return;
      }
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
      return;
    }
    if (!mounted) return;
    if (!widget.picking) {
      // 링크는 만들어졌다('보냄'). 알림톡이 나가는지 최대 10초 본다 — 그동안 단추는 돌지만 뒤로 가기는
      // 막지 않는다. 닫고 나갔으면 아무것도 띄우지 않는다(방문 상세의 알림톡 블록이 결과를 보인다).
      setState(() => _awaiting = true);
      final delivery = await notifications.awaitReport(
        shopId,
        widget.visitId,
        before: before,
      );
      if (!mounted) return;
      switch (delivery) {
        case ReportDelivered():
          AppSnackBar.show(context, AppStrings.reportSentByAlimtalk);
        case ReportPending():
          AppSnackBar.show(context, AppStrings.reportAlimtalkPending);
        case ReportFailed(:final shareText):
          AppSnackBar.show(context, AppStrings.reportAlimtalkFailed);
          await _share(shareText ?? sent.link.url!);
        case ReportNotSent():
          await _share(sent.link.url!);
      }
    }
    if (mounted) context.pop(true);
  }

  /// 공유 시트에 [text](링크 주소 또는 문자용 문안 — 둘 다 토큰이 들 수 있다)를 넘긴다.
  Future<void> _share(String text) async {
    final box = _buttonKey.currentContext!.findRenderObject()! as RenderBox;
    try {
      await ref
          .read(shareSheetProvider)
          .shareText(text, origin: box.localToGlobal(Offset.zero) & box.size);
    } on Exception {
      // 링크는 이미 만들어졌다('보냄') — 닫고, 방문 상세의 [다시 공유]로 다시 낼 수 있다고 알린다.
      if (mounted) AppSnackBar.show(context, AppStrings.reportShareFailed);
    }
  }

  /// 기간 안내 — 이미 보낸 링크는 그 링크의 기한, 새로 보내면 오늘에서 설정의 일수 뒤.
  String _period(VisitReportPreview preview, DateTime today) {
    final DateTime? until;
    if (preview.link.live) {
      until = preview.link.expiresAt?.wall;
    } else {
      final days = preview.settings.linkDays;
      until = days == null
          ? null
          : DateTime(today.year, today.month, today.day + days);
    }
    return until == null
        ? AppStrings.reportOpenForever
        : AppStrings.reportOpenUntil(until.month, until.day);
  }

  @override
  Widget build(BuildContext context) {
    final preview = _shopId == null
        ? const AsyncValue<VisitReportPreview>.loading()
        : ref.watch(visitReportProvider(_key));
    final media = preview.value?.media ?? const <ReportMedia>[];
    final images = ref.watch(mediaImagesProvider);
    final today = ref.watch(todayProvider);
    return Scaffold(
      key: ScreenKeys.reportPreview,
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
                    // 보내는 중에는 닫기도 시스템 뒤로 가기도 닫지 않는다 — 닫히면 만든 링크를 공유 시트에
                    // 넘기지 못한다. PopScope 는 경로 안 어디에 있어도 경로 전체에 걸린다. 링크를 만든 뒤
                    // 알림톡 결과를 기다리는 동안은 닫을 수 있다(⑥ 설계 8.3).
                    PopScope(
                      canPop: !_busy || _awaiting,
                      child: Pressable(
                        semanticLabel: AppStrings.close,
                        onTap: () => Navigator.of(context).maybePop(),
                        child: const Icon(Icons.close, color: AppColors.ink),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    const Text(
                      AppStrings.reportPreviewTitle,
                      style: AppTypography.titleKo,
                    ),
                    const Spacer(),
                    if (media.isNotEmpty)
                      Text(
                        AppStrings.reportShownCount(
                          media.length,
                          media.length - hiddenIdsOf(media, _changes).length,
                        ),
                        style: AppTypography.caption,
                      ),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<VisitReportPreview>(
                  value: preview,
                  onRetry: () => ref.invalidate(visitReportProvider(_key)),
                  builder: (preview) => _body(preview, images, today),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(VisitReportPreview preview, MediaImages images, DateTime today) {
    final media = preview.media;
    final note = preview.careNote;
    final settings = preview.settings;
    // 살아 있는 링크의 사진 고르기는 전부 빼도 저장할 수 있다 — 서버는 링크를 새로 만들 때만 막는다(설계 7.4).
    final empty = !widget.picking && !hasSomethingToShow(media, _changes, note);
    final message = empty ? _emptyText : _errorText;
    // 내용만 스크롤되고, 이유·실패 문구와 버튼은 아래에 고정이다.
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            children: [
              const _Label(AppStrings.reportMediaLabel),
              if (media.isEmpty)
                const Text(AppStrings.reportNoMedia, style: AppTypography.body)
              else
                _grid(media, images),
              const SizedBox(height: AppSpacing.lg),
              _Label(
                AppStrings.careNoteLabel,
                trailing: Pressable(
                  onTap: _busy ? null : _editNote,
                  // 누름 영역(44×44)의 오른쪽 가운데에 글자를 둔다 — 제목과 같은 줄에 놓인다.
                  child: Align(
                    alignment: Alignment.centerRight,
                    widthFactor: 1,
                    heightFactor: 1,
                    child: Text(
                      AppStrings.reportEditNote,
                      style: AppTypography.caption.copyWith(
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ),
                ),
              ),
              SizedBox(
                width: double.infinity,
                child: AppCard(
                  child: note == null
                      ? const Text(
                          AppStrings.reportNoCareNote,
                          style: AppTypography.caption,
                        )
                      : Text(note, style: AppTypography.body),
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              const _Label(
                AppStrings.reportItemsLabel,
                trailing: Text(
                  AppStrings.reportItemsHint,
                  style: AppTypography.caption,
                ),
              ),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  _ItemChip(AppStrings.reportItemMenus, on: settings.showMenus),
                  _ItemChip(
                    AppStrings.reportItemShopInfo,
                    on: settings.showShopInfo,
                  ),
                  _ItemChip(
                    AppStrings.reportItemAmount,
                    on: settings.showAmount,
                  ),
                  _ItemChip(
                    AppStrings.reportItemWeight,
                    on: settings.showWeight,
                  ),
                ],
              ),
              // 리뷰 남기기 줄(⑫) — 매장이 주소를 넣었을 때만. 주소가 없으면 아무것도 더하지 않는다(권하는 줄을
              // 미리보기에 끼워 넣지 않는다 — 설정에서 한다).
              if (preview.reviewUrl != null) ..._review(preview),
              const SizedBox(height: AppSpacing.md),
              Text(
                '${_period(preview, today)} ${AppStrings.reportReflectsEdits}',
                style: AppTypography.caption,
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.sm,
            AppSpacing.lg,
            AppSpacing.lg,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (message != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Text(message, style: AppTypography.caption),
                ),
              AppButton(
                key: _buttonKey,
                label: widget.picking ? AppStrings.save : AppStrings.reportSend,
                filled: true,
                busy: _busy,
                onPressed: empty ? null : _send,
              ),
            ],
          ),
        ),
      ],
    );
  }

  /// 리뷰 남기기 줄의 스위치와, 켰을 때 줄의 본(누르지 않는다). 처음 값은 그 링크의 값(없으면 넣음)이다.
  List<Widget> _review(VisitReportPreview preview) {
    final on = _showReview ?? preview.link.showReview ?? true;
    return [
      const SizedBox(height: AppSpacing.lg),
      Row(
        children: [
          const Expanded(
            child: ExcludeSemantics(
              child: Text(
                AppStrings.reportReviewSwitch,
                style: AppTypography.body,
              ),
            ),
          ),
          AppSwitch(
            key: const ValueKey('report-preview-review'),
            value: on,
            semanticLabel: AppStrings.reportReviewSwitch,
            onChanged: _busy ? null : (v) => setState(() => _showReview = v),
          ),
        ],
      ),
      const Text(
        AppStrings.reportReviewSwitchHint,
        style: AppTypography.caption,
      ),
      if (on && preview.reviewText != null) ...[
        const SizedBox(height: AppSpacing.sm),
        Center(
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.sm,
            ),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppRadius.pill),
              border: Border.all(color: AppColors.ink),
            ),
            child: Text(
              preview.reviewText!,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ],
    ];
  }

  /// 3열 정사각 격자 — 서버가 준 순서 그대로(후 → 전). 순번은 전·후를 따로 센다.
  Widget _grid(List<ReportMedia> media, MediaImages images) {
    return LayoutBuilder(
      builder: (context, box) {
        final size = ((box.maxWidth - AppSpacing.sm * 2) / 3).floorToDouble();
        final counts = {for (final p in MediaPhase.values) p: 0};
        return Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: [
            for (final m in media)
              AppPickTile(
                image: images.of(m.thumbUrl),
                size: size,
                picked: !_hidden(m),
                offLabel: AppStrings.reportHiddenMark,
                semanticLabel: AppStrings.reportTileLabel(
                  phaseLabel(m.phase),
                  counts.update(m.phase, (n) => n + 1),
                  hidden: _hidden(m),
                ),
                video: m.kind == MediaKind.video,
                durationSeconds: m.durationSeconds,
                onTap: _busy ? null : () => _toggle(m),
              ),
          ],
        );
      },
    );
  }
}

/// 구역 제목 줄 — 왼쪽에 제목, 오른쪽에 [trailing].
class _Label extends StatelessWidget {
  const _Label(this.text, {this.trailing});

  final String text;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: Row(
      children: [
        Expanded(child: Text(text, style: AppTypography.caption)),
        ?trailing,
      ],
    ),
  );
}

/// 함께 보이는 항목 하나 — 켠 것은 채운 칩, 끈 것은 옅게 줄을 그은 칩. 누르는 동작은 없다(설정에서 바꾼다).
class _ItemChip extends StatelessWidget {
  const _ItemChip(this.label, {required this.on});

  final String label;
  final bool on;

  @override
  Widget build(BuildContext context) => Semantics(
    // 칩마다 의미 노드를 따로 둔다 — 없으면 네 이름이 한 줄로 합쳐져 읽힌다.
    container: true,
    label: on ? label : AppStrings.reportItemOff(label),
    child: ExcludeSemantics(
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: on ? AppColors.ink : null,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(color: on ? AppColors.ink : AppColors.line),
        ),
        child: Text(
          label,
          style: AppTypography.caption.copyWith(
            color: on ? AppColors.white : AppColors.secondary,
            decoration: on ? null : TextDecoration.lineThrough,
          ),
        ),
      ),
    ),
  );
}
