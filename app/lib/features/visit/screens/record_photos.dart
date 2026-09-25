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
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/record_models.dart';
import '../state/record_rules.dart';
import '../state/upload_job.dart';
import '../state/upload_queue.dart';
import 'visit_labels.dart';

/// 방문 하나에 붙일 수 있는 사진 수(설계 9절).
const maxPhotosPerVisit = 30;

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
    required this.image,
    required this.onTap,
    required this.onRemove,
  });

  final String label;
  final MediaPhase phase;
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
        if (onRemove != null)
          _RemoveButton(
            label: '${AppStrings.removePhoto} $label',
            onTap: onRemove!,
          ),
      ],
    );
  }
}

/// 대기열의 사진 — 기기에 있는 썸네일 위에 진행 링. 실패해 기다리는 중이면 "대기 중"과 [빼기]만.
class _UploadTile extends StatelessWidget {
  const _UploadTile({required this.job, required this.onRemove});

  final UploadJob job;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final thumb = job.thumbPath;
    return Semantics(
      label: job.waiting ? AppStrings.uploadWaiting : AppStrings.uploading,
      child: Stack(
        alignment: Alignment.center,
        children: [
          AppPhotoTile(
            image: thumb == null ? null : FileImage(File(thumb)),
            size: _tileSize,
          ),
          if (job.waiting)
            const _Pill(AppStrings.uploadWaiting)
          else
            AppProgressRing(
              value: job.stage == UploadStage.preparing || !job.running
                  ? null
                  : job.progress,
            ),
          _RemoveButton(label: AppStrings.removeUpload, onTap: onRemove),
        ],
      ),
    );
  }
}

enum _Source { camera, album }

/// [사진 추가] — 전/후를 고르고 카메라·앨범에서 가져와 대기열에 넣는다. [attached]는 서버 기록에 붙은
/// 사진 수다. 한도 30장은 여기에 대기열의 사진을 더해 센다 — 차면 시트 없이 한도 문구만 보인다.
Future<void> addPhotos(
  BuildContext context,
  WidgetRef ref, {
  required int shopId,
  required int visitId,
  required MediaPhase phase,
  required int attached,
}) async {
  final remaining =
      maxPhotosPerVisit -
      attached -
      ref.read(visitUploadsProvider(visitId)).length;
  if (remaining <= 0) {
    AppSnackBar.show(
      context,
      messageFor(
        ApiException(
          statusCode: 422,
          code: 'MEDIA_LIMIT_EXCEEDED',
          message: '',
        ),
      ),
    );
    return;
  }
  final choice = await AppSheet.show<(_Source, MediaPhase)>(
    context,
    builder: (context) => _AddPhotoSheet(initialPhase: phase),
  );
  if (choice == null) return;
  final (source, chosen) = choice;
  final picker = ref.read(mediaPickerProvider);
  final paths = switch (source) {
    _Source.camera => [?await picker.takePhoto()],
    _Source.album => await picker.pickPhotos(limit: remaining),
  };
  if (paths.isEmpty) return;
  await ref
      .read(uploadQueueProvider.notifier)
      .addPhotos(
        shopId: shopId,
        visitId: visitId,
        phase: chosen,
        sources: paths.take(remaining).toList(),
      );
}

class _AddPhotoSheet extends StatefulWidget {
  const _AddPhotoSheet({required this.initialPhase});

  final MediaPhase initialPhase;

  @override
  State<_AddPhotoSheet> createState() => _AddPhotoSheetState();
}

class _AddPhotoSheetState extends State<_AddPhotoSheet> {
  late MediaPhase _phase = widget.initialPhase;

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
        AppButton(
          label: AppStrings.takePhoto,
          icon: Icons.photo_camera_outlined,
          onPressed: () => Navigator.of(context).pop((_Source.camera, _phase)),
        ),
        const SizedBox(height: AppSpacing.sm),
        AppButton(
          label: AppStrings.pickFromAlbum,
          icon: Icons.photo_library_outlined,
          onPressed: () => Navigator.of(context).pop((_Source.album, _phase)),
        ),
      ],
    );
  }
}
