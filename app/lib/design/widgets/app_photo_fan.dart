import 'dart:math' as math;

import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_shadows.dart';

/// 부채꼴로 겹친 사진(기준 목업의 달력 미리보기) — 최대 네 장을 조금씩 기울여 나란히 세운다.
/// 아래 변은 테두리 없이 카드 바닥에 닿는다.
class AppPhotoFan extends StatelessWidget {
  const AppPhotoFan({super.key, required this.images, this.height = 74});

  final List<ImageProvider> images;
  final double height;

  static const max = 4;

  // 목업 그대로 — 가장자리일수록 더 기울고 조금 내려앉는다.
  static const _tilts = [-5.0, -1.5, 2.0, 6.0];
  static const _drops = [5.0, 1.0, 2.0, 6.0];

  @override
  Widget build(BuildContext context) {
    final shown = images.take(max).toList();
    // 한두 장이면 바깥쪽 기울기 대신 가운데 쪽(1·2번째)을 쓴다.
    final start = shown.length <= 2 ? 1 : 0;
    return SizedBox(
      height: height,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          for (var i = 0; i < shown.length; i++)
            Flexible(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 1.5),
                child: Transform.translate(
                  offset: Offset(0, _drops[start + i]),
                  child: Transform.rotate(
                    angle: _tilts[start + i] * math.pi / 180,
                    child: Container(
                      constraints: BoxConstraints(maxWidth: height),
                      height: height,
                      decoration: BoxDecoration(
                        color: AppColors.line,
                        image: DecorationImage(
                          image: shown[i],
                          fit: BoxFit.cover,
                        ),
                        borderRadius: const BorderRadius.vertical(
                          top: Radius.circular(AppRadius.sm),
                        ),
                        border: const Border(
                          top: BorderSide(color: AppColors.white, width: 1.5),
                          left: BorderSide(color: AppColors.white, width: 1.5),
                          right: BorderSide(color: AppColors.white, width: 1.5),
                        ),
                        boxShadow: AppShadows.soft,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
