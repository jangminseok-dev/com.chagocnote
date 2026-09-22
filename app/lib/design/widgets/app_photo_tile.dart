import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_shadows.dart';
import '../tokens/app_typography.dart';

/// 흰 테두리의 둥근 사각형 사진 타일.
///
/// `count`를 주면 안쪽 우측 하단에 흰 동그라미 숫자를 얹는다. `image`가
/// null이면 선(line) 색 플레이스홀더를 보여준다.
class AppPhotoTile extends StatelessWidget {
  const AppPhotoTile({
    super.key,
    required this.image,
    this.count,
    this.size = 72,
  });

  final ImageProvider? image;
  final int? count;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                color: image == null ? AppColors.line : null,
                image: image != null
                    ? DecorationImage(image: image!, fit: BoxFit.cover)
                    : null,
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(color: AppColors.white, width: 1.5),
                boxShadow: AppShadows.soft,
              ),
            ),
          ),
          if (count != null)
            Positioned(
              right: 4,
              bottom: 4,
              child: Container(
                width: 16,
                height: 16,
                decoration: const BoxDecoration(
                  color: AppColors.white,
                  shape: BoxShape.circle,
                  boxShadow: AppShadows.badge,
                ),
                alignment: Alignment.center,
                child: Text(
                  '$count',
                  style: AppTypography.caption.copyWith(
                    fontSize: 9,
                    height: 1,
                    fontWeight: FontWeight.w700,
                    color: AppColors.ink,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
