import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/proxy/media_files.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/proxy/photo_album.dart';
import '../../../core/proxy/video_playback.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/app_video_player.dart';
import '../../../design/widgets/video_playback.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/record_models.dart';
import '../api/visit_models.dart';
import '../state/photo_edits.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'visit_labels.dart';

/// 크게 보기(설계 10.1 ⑤) — 사진을 화면 가득 좌우로 넘기고, 원본 저장·전/후 바꾸기·대표로·삭제.
/// 바꾸기·삭제는 기록 전체 교체 한 번이다. 버전이 어긋나면(대기열이 그사이 사진을 붙임) 다시 읽어
/// 같은 바꾸기를 한 번 더 보낸다.
class PhotoViewerScreen extends ConsumerStatefulWidget {
  const PhotoViewerScreen({
    super.key,
    required this.visitId,
    required this.mediaId,
  });

  final int visitId;

  /// 처음 보일 사진.
  final int mediaId;

  @override
  ConsumerState<PhotoViewerScreen> createState() => _PhotoViewerScreenState();
}

class _PhotoViewerScreenState extends ConsumerState<PhotoViewerScreen> {
  PageController? _pages;

  /// 보고 있는 사진 — 자리(인덱스)가 아니라 ID 로 따라간다. 대표로·전/후 바꾸기는 순서를 바꾼다.
  late int _mediaId = widget.mediaId;
  bool _busy = false;

  /// 닫기를 예약했다 — 다시 그려져도 두 번 닫지 않는다.
  bool _closing = false;

  int? get _shopId => ref.read(selectedShopIdProvider);

  VisitKey get _key => (shopId: _shopId ?? 0, visitId: widget.visitId);

  @override
  void dispose() {
    _pages?.dispose();
    super.dispose();
  }

  /// 원본을 받아 앨범에 넣는다. 사진은 원본 캐시(`fileOf`)에서, 영상은 mp4 를 임시 파일로 받아 넣고 지운다
  /// (④-3a 설계 5.4). 받는 중에 화면을 나가도 저장·삭제는 끝까지 하고, 문구만 띄우지 않는다.
  Future<void> _save(RecordMedia media) async {
    final images = ref.read(mediaImagesProvider);
    final files = ref.read(mediaFilesProvider);
    final album = ref.read(photoAlbumProvider);
    setState(() => _busy = true);
    String? temp;
    try {
      final String path;
      if (media.kind == MediaKind.video) {
        path = temp = await files.download(media.originalUrl, suffix: '.mp4');
      } else {
        path = await images.fileOf(media.originalUrl);
      }
      await album.save(path);
      if (mounted) AppSnackBar.show(context, AppStrings.savedToAlbum);
    } on PhotoAlbumDenied {
      if (mounted) AppSnackBar.show(context, AppStrings.albumDenied);
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    } finally {
      if (temp != null) await File(temp).delete();
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _edit(List<RecordMedia> gallery, PhotoEdit edit) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final target = _mediaId;
    int? next;
    if (edit == PhotoEdit.remove) {
      final confirmed = await _confirmDelete();
      if (confirmed != true || !mounted) return;
      // 지운 뒤에는 옆 사진을 본다(마지막이면 앞 사진). 저장이 실패하면 보던 사진에 남는다.
      final at = gallery.indexWhere((m) => m.mediaId == target);
      final i = at + 1 < gallery.length ? at + 1 : at - 1;
      if (i >= 0) next = gallery[i].mediaId;
    }
    setState(() => _busy = true);
    final commands = ref.read(visitCommandsProvider);
    try {
      var detail = await ref.read(visitDetailProvider(_key).future);
      for (var attempt = 0; ; attempt++) {
        final record = detail.record;
        final placements = record == null
            ? null
            : applyPhotoEdit(record.media, target, edit);
        if (placements == null) break; // 그사이 빠졌다 — 보낼 것이 없다.
        try {
          await commands.saveRecord(
            shopId,
            widget.visitId,
            recordInputOf(record!, placements),
          );
          break;
        } on ApiException catch (e) {
          if (e.code != 'RECORD_VERSION_CONFLICT' || attempt > 0) rethrow;
          // 저장이 상세를 무효화했다 — 다시 읽어 같은 바꾸기를 새 기록에 한 번 더.
          detail = await ref.read(visitDetailProvider(_key).future);
        }
      }
      if (next != null) _mediaId = next;
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// 영상 [다시 시도] — 상세를 다시 읽어 새 서명 URL 을 받는다(만료 403, 설계 5.4). 다시 읽기가 실패하면
  /// 화면의 `AsyncBody` 가 알리고, 영상은 그대로 둔다(null).
  Future<String?> _freshOriginalUrl(int mediaId) async {
    ref.invalidate(visitDetailProvider(_key));
    try {
      final detail = await ref.read(visitDetailProvider(_key).future);
      for (final m in detail.record?.media ?? const <RecordMedia>[]) {
        if (m.mediaId == mediaId) return m.originalUrl;
      }
    } catch (_) {}
    return null;
  }

  Future<bool?> _confirmDelete() => AppSheet.show<bool>(
    context,
    builder: (context) => Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          AppStrings.deletePhotoConfirm,
          style: AppTypography.body,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.delete,
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

  @override
  Widget build(BuildContext context) {
    final detail = _shopId == null
        ? const AsyncValue<VisitDetail>.loading()
        : ref.watch(visitDetailProvider(_key));
    final data = detail.value;
    final gallery = galleryOrder(data?.record?.media ?? const []);
    final found = gallery.indexWhere((m) => m.mediaId == _mediaId);
    // 찾는 사진이 그사이 빠졌으면 첫 장부터.
    final index = found < 0 && gallery.isNotEmpty ? 0 : found;
    if (found < 0 && gallery.isNotEmpty) _mediaId = gallery.first.mediaId;
    // 사진이 모두 빠졌으면(마지막 사진을 지움) 한 번만 닫는다.
    if (data != null && gallery.isEmpty && !_closing) {
      _closing = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && context.canPop()) context.pop();
      });
    }
    final current = index < 0 ? null : gallery[index];
    final pages = _pages ??= index < 0
        ? null
        : PageController(initialPage: index);
    // 순서가 바뀌면(대표로·전/후) 보던 사진의 새 자리로 옮긴다.
    if (pages != null &&
        pages.hasClients &&
        index >= 0 &&
        pages.page?.round() != index) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && pages.hasClients) pages.jumpToPage(index);
      });
    }
    final status = data?.visit.status;
    final editable =
        status == VisitStatus.inProgress || status == VisitStatus.completed;
    return Scaffold(
      key: ScreenKeys.photoViewer,
      body: AppBackground(
        child: SafeArea(
          child: Column(
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
                    const Spacer(),
                    if (current != null)
                      Text(
                        '${phaseLabel(current.phase)} · ${index + 1} / ${gallery.length}',
                        style: AppTypography.caption,
                      ),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<VisitDetail>(
                  value: detail,
                  onRetry: () => ref.invalidate(visitDetailProvider(_key)),
                  builder: (_) => pages == null
                      ? const Center(child: CircularProgressIndicator())
                      : PageView.builder(
                          controller: pages,
                          itemCount: gallery.length,
                          onPageChanged: (i) =>
                              setState(() => _mediaId = gallery[i].mediaId),
                          itemBuilder: (context, i) => _Page(
                            key: ValueKey(gallery[i].mediaId),
                            media: gallery[i],
                            active: gallery[i].mediaId == _mediaId,
                            onRetry: () => _freshOriginalUrl(gallery[i].mediaId),
                          ),
                        ),
                ),
              ),
              if (current != null)
                _Actions(
                  media: current,
                  gallery: gallery,
                  editable: editable,
                  busy: _busy,
                  onSave: () => _save(current),
                  onEdit: (edit) => _edit(gallery, edit),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 한 장 — 원본을 화면에 맞춰 보이고 두 손가락으로 키운다. 영상은 포스터 위 재생 버튼을 누르면 그 자리에서
/// 재생한다(④-3a 설계 5.4). 재생은 페이지마다 하나 — 넘기면([active]가 꺼지면) 멈추고, 페이지가 사라지면 해제한다.
class _Page extends ConsumerStatefulWidget {
  const _Page({
    super.key,
    required this.media,
    required this.active,
    required this.onRetry,
  });

  final RecordMedia media;

  /// 지금 보고 있는 페이지인가.
  final bool active;

  /// 영상 [다시 시도] — 새 원본 URL.
  final Future<String?> Function() onRetry;

  @override
  ConsumerState<_Page> createState() => _PageState();
}

class _PageState extends ConsumerState<_Page> {
  /// 영상 페이지만 만든다.
  late final VideoPlayback? _playback = widget.media.kind == MediaKind.video
      ? ref.read(videoPlaybackFactoryProvider).create()
      : null;

  @override
  void didUpdateWidget(_Page old) {
    super.didUpdateWidget(old);
    if (old.active && !widget.active) _playback?.pause();
  }

  @override
  void dispose() {
    _playback?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final images = ref.watch(mediaImagesProvider);
    final media = widget.media;
    final playback = _playback;
    if (playback != null) {
      return AppVideoPlayer(
        playback: playback,
        url: media.originalUrl,
        poster: images.of(media.thumbUrl),
        errorMessage: loadMessageFor,
        onRetry: widget.onRetry,
      );
    }
    return InteractiveViewer(
      maxScale: 4,
      child: Center(
        child: Image(
          image: images.original(media.originalUrl),
          fit: BoxFit.contain,
          semanticLabel: phaseLabel(media.phase),
        ),
      ),
    );
  }
}

class _Actions extends StatelessWidget {
  const _Actions({
    required this.media,
    required this.gallery,
    required this.editable,
    required this.busy,
    required this.onSave,
    required this.onEdit,
  });

  final RecordMedia media;
  final List<RecordMedia> gallery;

  /// 미용 중·완료 방문만 기록을 바꿀 수 있다(설계 8절). 되돌려진 방문은 저장만.
  final bool editable;
  final bool busy;
  final VoidCallback onSave;
  final ValueChanged<PhotoEdit> onEdit;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // 영상도 원본(mp4)을 저장한다(④-3a 설계 5.4).
          _Action(
            icon: Icons.download_outlined,
            label: AppStrings.saveOriginal,
            onTap: busy ? null : onSave,
          ),
          if (editable) ...[
            _Action(
              icon: Icons.swap_horiz,
              label: media.phase == MediaPhase.before
                  ? AppStrings.toAfter
                  : AppStrings.toBefore,
              onTap: busy ? null : () => onEdit(PhotoEdit.togglePhase),
            ),
            if (canMakeCover(gallery, media.mediaId))
              _Action(
                icon: Icons.star_outline,
                label: AppStrings.makeCover,
                onTap: busy ? null : () => onEdit(PhotoEdit.makeCover),
              ),
            _Action(
              icon: Icons.delete_outline,
              label: AppStrings.deletePhoto,
              onTap: busy ? null : () => onEdit(PhotoEdit.remove),
            ),
          ],
        ],
      ),
    );
  }
}

class _Action extends StatelessWidget {
  const _Action({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Pressable(
    semanticLabel: label,
    onTap: onTap,
    child: ExcludeSemantics(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xs),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: onTap == null ? AppColors.line : AppColors.ink),
            const SizedBox(height: 2),
            Text(label, style: AppTypography.caption),
          ],
        ),
      ),
    ),
  );
}
