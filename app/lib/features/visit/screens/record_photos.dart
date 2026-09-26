import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/proxy/media_picker.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_progress_ring.dart';
import '../../../design/widgets/app_segment.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/app_video_badge.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/record_models.dart';
import '../state/record_rules.dart';
import '../state/upload_job.dart';
import '../state/upload_queue.dart';
import 'visit_labels.dart';

/// 방문 하나에 붙일 수 있는 사진 수(설계 9절).
const maxPhotosPerVisit = 30;

/// 방문 하나에 붙일 수 있는 영상 수(④-3a 설계 4.5). 사진과 따로 센다.
const maxVideosPerVisit = 3;

const _tileSize = 96.0;

/// 기록의 사진 줄 — [사진 추가](맨 앞이라 사진이 많아도 보인다), 붙은 사진(썸네일), 대기열의 사진(진행 링 ·
/// "대기 중" · [빼기]).
///
/// 붙은 사진을 누르면 [onTapMedia](기록 화면은 전/후 바꾸기), [onRemoveMedia]가 있으면 빼기 단추를
/// 얹는다. [onAdd]가 null 이면 추가 타일이 없다.
class RecordPhotoStrip extends ConsumerWidget {
  const RecordPhotoStrip({
    super.key,
    required this.visitId,
    required this.media,
    this.onTapMedia,
    this.onRemoveMedia,
    this.onAdd,
  });

  final int visitId;
  final List<FormMedia> media;
  final ValueChanged<FormMedia>? onTapMedia;
  final ValueChanged<FormMedia>? onRemoveMedia;
  final VoidCallback? onAdd;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final images = ref.watch(mediaImagesProvider);
    final uploads = ref.watch(visitUploadsProvider(visitId));
    final counts = {for (final p in MediaPhase.values) p: 0};
    return SizedBox(
      height: _tileSize,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          if (onAdd != null)
            _Gap(
              child: Pressable(
                semanticLabel: AppStrings.addPhoto,
                onTap: onAdd,
                child: Container(
                  width: _tileSize,
                  height: _tileSize,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppColors.line, width: 1.5),
                  ),
                  child: const Icon(Icons.add_a_photo_outlined),
                ),
              ),
            ),
          for (final m in media)
            _Gap(
              child: _MediaTile(
                label: AppStrings.photoTileLabel(
                  phaseLabel(m.phase),
                  counts.update(m.phase, (n) => n + 1),
                ),
                phase: m.phase,
                kind: m.media.kind,
                durationSeconds: m.media.durationSeconds,
                image: images.of(m.media.thumbUrl),
                onTap: onTapMedia == null ? null : () => onTapMedia!(m),
                onRemove: onRemoveMedia == null
                    ? null
                    : () => onRemoveMedia!(m),
              ),
            ),
          for (final job in uploads)
            _Gap(
              child: _UploadTile(
                job: job,
                onRemove: () =>
                    ref.read(uploadQueueProvider.notifier).remove(job.id),
                onStopped: () => _openStopped(context, ref, job),
              ),
            ),
        ],
      ),
    );
  }
}

class _Gap extends StatelessWidget {
  const _Gap({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(right: AppSpacing.sm),
    child: child,
  );
}

/// 흰 알약 글자 — 사진 위 왼쪽 위의 전/후, 가운데의 "대기 중".
class _Pill extends StatelessWidget {
  const _Pill(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
    decoration: BoxDecoration(
      color: AppColors.white,
      borderRadius: BorderRadius.circular(AppRadius.pill),
    ),
    child: Text(text, style: AppTypography.caption.copyWith(fontSize: 10)),
  );
}

/// 사진 오른쪽 위의 작은 빼기 단추. 누름 영역은 44×44(모서리), 보이는 원은 20이다 —
/// 타일(96)의 가운데는 덮지 않는다.
class _RemoveButton extends StatelessWidget {
  const _RemoveButton({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Positioned(
    right: 0,
    top: 0,
    child: Pressable(
      semanticLabel: label,
      onTap: onTap,
      child: SizedBox(
        width: 44,
        height: 44,
        child: Align(
          alignment: Alignment.topRight,
          child: Container(
            margin: const EdgeInsets.all(4),
            width: 20,
            height: 20,
            decoration: const BoxDecoration(
              color: AppColors.white,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.close, size: 14, color: AppColors.ink),
          ),
        ),
      ),
    ),
  );
}

class _MediaTile extends StatelessWidget {
  const _MediaTile({
    required this.label,
    required this.phase,
    required this.kind,
    required this.durationSeconds,
    required this.image,
    required this.onTap,
    required this.onRemove,
  });

  final String label;
  final MediaPhase phase;
  final MediaKind kind;
  final int? durationSeconds;
  final ImageProvider image;
  final VoidCallback? onTap;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Pressable(
          semanticLabel: label,
          onTap: onTap,
          child: AppPhotoTile(image: image, size: _tileSize),
        ),
        Positioned(left: 4, top: 4, child: _Pill(phaseLabel(phase))),
        if (kind == MediaKind.video)
          Positioned(
            left: 4,
            bottom: 4,
            child: AppVideoBadge(durationSeconds: durationSeconds),
          ),
        if (onRemove != null)
          _RemoveButton(
            label: '${AppStrings.removePhoto} $label',
            onTap: onRemove!,
          ),
      ],
    );
  }
}

/// 대기열의 사진 — 기기에 있는 썸네일 위에 진행 링. 영상은 포스터 위에 재생 표시와 길이(압축 중엔 포스터도
/// 길이도 없어 회색 바탕에 재생 표시만). 실패해 기다리는 중이면 "대기 중"과 [올리기 취소]만.
/// 다시 해도 안 되는 실패로 멈췄으면 느낌표 — 누르면 이유와 [다시 시도]·[올리기 취소](오류 화면 다듬기
/// 설계 4절).
class _UploadTile extends StatelessWidget {
  const _UploadTile({
    required this.job,
    required this.onRemove,
    required this.onStopped,
  });

  final UploadJob job;
  final VoidCallback onRemove;
  final VoidCallback onStopped;

  @override
  Widget build(BuildContext context) {
    final thumb = job.thumbPath;
    // 영상의 준비(압축)는 진행률을 안다 — 링에 그대로 흘린다(④-3a 설계 4.2).
    final compressing =
        job.kind == MediaKind.video && job.stage == UploadStage.preparing;
    final tile = Stack(
      alignment: Alignment.center,
      children: [
        AppPhotoTile(
          image: thumb == null ? null : FileImage(File(thumb)),
          size: _tileSize,
        ),
        if (job.kind == MediaKind.video)
          Positioned(
            left: 4,
            bottom: 4,
            child: AppVideoBadge(durationSeconds: job.durationSeconds),
          ),
        if (job.stopped)
          const _StoppedBadge()
        else if (job.waiting)
          const _Pill(AppStrings.uploadWaiting)
        else
          AppProgressRing(
            value: compressing
                ? job.progress
                : job.stage == UploadStage.preparing || !job.running
                ? null
                : job.progress,
          ),
        _RemoveButton(label: AppStrings.removeUpload, onTap: onRemove),
      ],
    );
    if (job.stopped) {
      return Pressable(
        semanticLabel: AppStrings.uploadStopped,
        onTap: onStopped,
        child: tile,
      );
    }
    return Semantics(
      label: job.waiting ? AppStrings.uploadWaiting : AppStrings.uploading,
      child: tile,
    );
  }
}

class _StoppedBadge extends StatelessWidget {
  const _StoppedBadge();

  @override
  Widget build(BuildContext context) => Container(
    width: 28,
    height: 28,
    decoration: const BoxDecoration(
      color: AppColors.white,
      shape: BoxShape.circle,
    ),
    child: const Icon(Icons.priority_high, size: 18, color: AppColors.ink),
  );
}

/// 멈춘 사진의 시트 — 이유 한 줄과 [다시 시도]·[올리기 취소]. 너무 커서 멈췄으면(`MEDIA_TOO_LARGE`) 다시 해도
/// 같으니 [올리기 취소]만.
Future<void> _openStopped(
  BuildContext context,
  WidgetRef ref,
  UploadJob job,
) async {
  final tooLarge = job.stoppedCode == 'MEDIA_TOO_LARGE';
  final retry = await AppSheet.show<bool>(
    context,
    builder: (context) => Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          messageFor(
            ApiException(statusCode: null, code: job.stoppedCode!, message: ''),
          ),
          style: AppTypography.body,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.lg),
        if (!tooLarge)
          AppSheetAction(
            label: AppStrings.retry,
            onTap: () => Navigator.of(context).pop(true),
          ),
        AppSheetAction(
          label: AppStrings.removeUpload,
          onTap: () => Navigator.of(context).pop(false),
        ),
      ],
    ),
  );
  if (retry == null) return;
  if (!context.mounted) return;
  final queue = ref.read(uploadQueueProvider.notifier);
  await (retry ? queue.retry(job.id) : queue.remove(job.id));
}

enum _Source { camera, album, videoAlbum, videoCamera }

void _showLimit(BuildContext context) => AppSnackBar.show(
  context,
  messageFor(
    ApiException(statusCode: 422, code: 'MEDIA_LIMIT_EXCEEDED', message: ''),
  ),
);

/// [사진 추가] — 전/후를 고르고 카메라·앨범에서 사진이나 영상을 가져와 대기열에 넣는다. [attached]는 서버
/// 기록에 붙은 사진·영상이다. 한도(사진 30장·영상 3편, 따로 센다)는 여기에 대기열의 것을 더해 센다 — 한쪽만
/// 찼으면 시트의 그쪽 항목이 회색이고, 둘 다 찼으면 시트 없이 한도 문구만 보인다.
Future<void> addPhotos(
  BuildContext context,
  WidgetRef ref, {
  required int shopId,
  required int visitId,
  required MediaPhase phase,
  required List<RecordMedia> attached,
}) async {
  final uploads = ref.read(visitUploadsProvider(visitId));
  int count(MediaKind kind) =>
      attached.where((m) => m.kind == kind).length +
      uploads.where((j) => j.kind == kind).length;
  final remaining = maxPhotosPerVisit - count(MediaKind.photo);
  final videosLeft = maxVideosPerVisit - count(MediaKind.video);
  if (remaining <= 0 && videosLeft <= 0) {
    _showLimit(context);
    return;
  }
  final choice = await AppSheet.show<(_Source, MediaPhase)>(
    context,
    builder: (context) => _AddPhotoSheet(
      initialPhase: phase,
      photosFull: remaining <= 0,
      videosFull: videosLeft <= 0,
    ),
  );
  if (choice == null) return;
  final (source, chosen) = choice;
  final picker = ref.read(mediaPickerProvider);
  final queue = ref.read(uploadQueueProvider.notifier);
  if (source case _Source.videoAlbum || _Source.videoCamera) {
    final path = source == _Source.videoAlbum
        ? await picker.pickVideo()
        : await picker.takeVideo(maxSeconds: 60);
    if (path == null) return;
    final outcome = await queue.addVideo(
      shopId: shopId,
      visitId: visitId,
      phase: chosen,
      source: path,
    );
    if (!context.mounted) return;
    final text = switch (outcome) {
      VideoAddOutcome.trimmed => AppStrings.videoTrimmed,
      VideoAddOutcome.unsupported => AppStrings.videoUnsupported,
      VideoAddOutcome.tooShort => AppStrings.videoTooShort,
      VideoAddOutcome.added || VideoAddOutcome.cancelled => null,
    };
    if (text != null) AppSnackBar.show(context, text);
    return;
  }
  final paths = switch (source) {
    _Source.camera => [?await picker.takePhoto()],
    _ => await picker.pickPhotos(limit: remaining),
  };
  if (paths.isEmpty) return;
  await queue.addPhotos(
    shopId: shopId,
    visitId: visitId,
    phase: chosen,
    sources: paths.take(remaining).toList(),
  );
}

class _AddPhotoSheet extends StatefulWidget {
  const _AddPhotoSheet({
    required this.initialPhase,
    required this.photosFull,
    required this.videosFull,
  });

  final MediaPhase initialPhase;

  /// 찼으면 그 항목들을 회색으로 두고, 누르면 시트를 닫고 한도 문구를 보인다.
  final bool photosFull;
  final bool videosFull;

  @override
  State<_AddPhotoSheet> createState() => _AddPhotoSheetState();
}

class _AddPhotoSheetState extends State<_AddPhotoSheet> {
  late MediaPhase _phase = widget.initialPhase;

  Widget _item(String label, IconData icon, _Source source, bool full) {
    if (!full) {
      return AppButton(
        label: label,
        icon: icon,
        onPressed: () => Navigator.of(context).pop((source, _phase)),
      );
    }
    // 회색 단추는 스스로 눌리지 않는다 — 누름은 겉의 Pressable 이 받는다.
    return Pressable(
      semanticLabel: label,
      onTap: () {
        Navigator.of(context).pop();
        _showLimit(context);
      },
      child: IgnorePointer(
        child: AppButton(label: label, icon: icon, onPressed: null),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(AppStrings.addPhotoPhaseLabel, style: AppTypography.body),
        const SizedBox(height: AppSpacing.sm),
        AppSegment(
          labels: [for (final p in MediaPhase.values) phaseLabel(p)],
          currentIndex: _phase.index,
          onChanged: (i) => setState(() => _phase = MediaPhase.values[i]),
        ),
        const SizedBox(height: AppSpacing.lg),
        _item(
          AppStrings.takePhoto,
          Icons.photo_camera_outlined,
          _Source.camera,
          widget.photosFull,
        ),
        const SizedBox(height: AppSpacing.sm),
        _item(
          AppStrings.pickFromAlbum,
          Icons.photo_library_outlined,
          _Source.album,
          widget.photosFull,
        ),
        const SizedBox(height: AppSpacing.sm),
        _item(
          AppStrings.takeVideo,
          Icons.videocam_outlined,
          _Source.videoCamera,
          widget.videosFull,
        ),
        const SizedBox(height: AppSpacing.sm),
        _item(
          AppStrings.pickVideo,
          Icons.video_library_outlined,
          _Source.videoAlbum,
          widget.videosFull,
        ),
      ],
    );
  }
}
