import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';

/// 사진 위에 얹는 흰 진행 링. [value]가 null 이면 도는 링(준비 중)이다.
class AppProgressRing extends StatelessWidget {
  const AppProgressRing({super.key, required this.value, this.size = 28});

  final double? value;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        value: value,
        strokeWidth: 2.5,
        color: AppColors.white,
        backgroundColor: AppColors.scrim,
      ),
    );
  }
}
