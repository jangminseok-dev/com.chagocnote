import 'package:flutter/physics.dart';

/// 스프링 물리 프리셋. 고정 커브 대신 스프링으로 눌림/복귀를 표현한다.
abstract final class AppSprings {
  /// 누르는 순간(스케일이 줄어드는 쪽) — 빠르고 절제된 반응.
  static final press = SpringDescription.withDampingRatio(
    mass: 1,
    stiffness: 500,
    ratio: 0.6,
  );

  /// 손을 뗐을 때 원래 크기로 되돌아오는 쪽 — 살짝 더 튀는 느낌을 준다.
  static final settle = SpringDescription.withDampingRatio(
    mass: 1,
    stiffness: 300,
    ratio: 0.5,
  );

  /// "동작 줄이기"가 켜졌을 때 스프링 대신 쓰는 페이드 지속 시간.
  static const fadeDuration = Duration(milliseconds: 80);
}
