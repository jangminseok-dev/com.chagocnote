import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_typography.dart';
import 'app_photo_tile.dart';
import 'app_video_badge.dart';
import 'pressable.dart';

/// 실을지 말지 누르는 사진 타일(알림장 미리보기의 격자).
///
/// 고른 것은 오른쪽 위에 체크, 뺀 것은 흐리게 하고 가운데에 [offLabel]("뺌")을 얹는다. 영상이면
/// 왼쪽 아래에 재생 표시와 길이. 스크린리더는 [semanticLabel]만 읽는다 — 얹은 글자는 따로 읽지 않는다.
class AppPickTile extends StatelessWidget {
  const AppPickTile({
    super.key,
    required this.image,
    required this.size,
    required this.picked,
    required this.offLabel,
    required this.semanticLabel,
    required this.onTap,
    this.video = false,
    this.durationSeconds,
  });

  final ImageProvider image;
  final double size;
  final bool picked;
  final String offLabel;
  final String semanticLabel;
  final VoidCallback? onTap;
  final bool video;

  /// 영상 길이(초). 모르면 재생 표시만.
  final int? durationSeconds;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: semanticLabel,
      selected: picked,
      onTap: onTap,
      child: ExcludeSemantics(
        child: Stack(
          alignment: Alignment.center,
          children: [
            Opacity(
              opacity: picked ? 1 : 0.35,
              child: AppPhotoTile(image: image, size: size),
            ),
            if (video)
              Positioned(
                left: 6,
                bottom: 6,
                child: AppVideoBadge(durationSeconds: durationSeconds),
              ),
            if (picked)
              Positioned(
                right: 6,
                top: 6,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    color: AppColors.ink,
                    shape: BoxShape.circle,
                    border: Border.all(color: AppColors.white, width: 1.5),
                  ),
                  child: const Icon(
                    Icons.check,
                    size: 12,
                    color: AppColors.white,
                  ),
                ),
              )
            else
              Text(offLabel, style: AppTypography.bodyStrong),
          ],
        ),
      ),
    );
  }
}
