import 'package:flutter/material.dart';

import 'tokens/app_colors.dart';

/// Material 3 기반 앱 테마. 무채색 톤이라 시드에서 나온 색조가 새 색을
/// 들이지 않도록 주요 역할(primary/secondary/surface/error)을 직접
/// ink/white/backgroundTop으로 덮어쓴다. `outline`·`onSurfaceVariant`도
/// 시드가 만든 팔레트 밖 회색 대신 `AppColors.line`·`AppColors.secondary`로
/// 덮어써서, 구분선·보조 텍스트가 항상 디자인 토큰과 같은 색을 쓰게 한다.
ThemeData appTheme() {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.ink,
  ).copyWith(
    primary: AppColors.ink,
    onPrimary: AppColors.white,
    secondary: AppColors.ink,
    onSecondary: AppColors.white,
    surface: AppColors.backgroundTop,
    onSurface: AppColors.ink,
    onSurfaceVariant: AppColors.secondary,
    outline: AppColors.line,
    error: AppColors.ink,
    onError: AppColors.white,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    fontFamily: 'Pretendard',
    // 배경 그라데이션은 AppBackground가 그리므로 스캐폴드 자체는 투명하게
    // 비워둔다.
    scaffoldBackgroundColor: Colors.transparent,
    // Pressable이 스케일+햅틱으로 자체 눌림 피드백을 주므로, Material
    // 기본 잉크 리플/하이라이트는 새 색조를 들이지 않게 꺼둔다.
    splashFactory: NoSplash.splashFactory,
    splashColor: Colors.transparent,
    highlightColor: Colors.transparent,
    hoverColor: Colors.transparent,
    focusColor: Colors.transparent,
    textTheme: Typography.blackMountainView.apply(
      fontFamily: 'Pretendard',
      bodyColor: AppColors.ink,
      displayColor: AppColors.ink,
    ),
  );
}

/// 화면 배경에 세로 그라데이션(`#f5f5f5` → `#ececec`)을 깔아주는 위젯.
///
/// `Scaffold`는 투명 배경으로 두고, 이 위젯으로 감싸서 그 뒤에 그라데이션이
/// 보이게 한다.
class AppBackground extends StatelessWidget {
  const AppBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
      child: child,
    );
  }
}
