import 'package:flutter/cupertino.dart';
import 'package:liquid_glass_widgets/liquid_glass_widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_shadows.dart';

/// 유리(glass) 표면을 실제로 그리는 방법을 감춘 추상 팩토리.
///
/// 구현체를 바꿔치기하면 실제 리퀴드 글래스 렌더러(`GlassContainer`)와
/// 완전 불투명 대체 표면(`OpaqueSurfaceFactory`)을 동일한 인터페이스로
/// 다룰 수 있다.
///
/// 모서리는 네 곳이 같은 반지름 [radius] 하나다. 리퀴드 글래스 모양이 대칭
/// 반지름만 받으므로 계약도 그만큼만 약속한다 — 비대칭 반지름을 받아 놓고
/// 구현마다 다르게 그리던 것을 없앤다.
abstract class GlassSurfaceFactory {
  Widget build({
    required Widget child,
    required double radius,
    EdgeInsetsGeometry? padding,
  });
}

/// `liquid_glass_widgets`의 [GlassContainer]로 실제 유리 효과를 그린다.
///
/// `useOwnLayer: true`를 써서 주변에 [LiquidGlassLayer] 조상이 없어도
/// 어디서든 단독으로 쓸 수 있게 한다 (README의 "Standalone Mode").
class LiquidGlassSurfaceFactory implements GlassSurfaceFactory {
  const LiquidGlassSurfaceFactory();

  @override
  Widget build({
    required Widget child,
    required double radius,
    EdgeInsetsGeometry? padding,
  }) {
    return GlassContainer(
      useOwnLayer: true,
      shape: LiquidRoundedRectangle(borderRadius: radius),
      padding: padding,
      child: child,
    );
  }
}

/// 그림자 없는 완전 불투명 대체 표면.
///
/// 흰색 92% 불투명 채움 + 1px 구분선 테두리(`AppColors.line`) + 은은한
/// 그림자(`AppShadows.soft`)로, 셰이더도 `BackdropFilter`도 전혀 쓰지
/// 않는다. 테스트 환경, 저사양 기기, "투명도 줄이기"가 켜진 경우의 대체
/// 표면으로 쓴다.
class OpaqueSurfaceFactory implements GlassSurfaceFactory {
  const OpaqueSurfaceFactory();

  static const _fill = Color.fromRGBO(255, 255, 255, 0.92);

  @override
  Widget build({
    required Widget child,
    required double radius,
    EdgeInsetsGeometry? padding,
  }) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: _fill,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: AppColors.line, width: 1),
        boxShadow: AppShadows.soft,
      ),
      child: child,
    );
  }
}

/// 상위 트리에 유리 표면 팩토리를 제공하는 [InheritedWidget].
///
/// 화면/기능 단위에서 실제 렌더러를 바꿔 끼우고 싶을 때(예: 데모 화면에서
/// 강제로 불투명 표면만 보여주기) 이 위젯으로 감싸면 된다. 감싸지 않으면
/// [GlassSurface]가 기본값으로 [LiquidGlassSurfaceFactory]를 쓴다.
class GlassBridge extends InheritedWidget {
  const GlassBridge({
    super.key,
    required this.factory,
    required super.child,
  });

  final GlassSurfaceFactory factory;

  static GlassSurfaceFactory of(BuildContext context) {
    final bridge = context.dependOnInheritedWidgetOfExactType<GlassBridge>();
    return bridge?.factory ?? const LiquidGlassSurfaceFactory();
  }

  @override
  bool updateShouldNotify(GlassBridge oldWidget) =>
      factory != oldWidget.factory;
}

/// 유리 표면 하나를 그리는 위젯.
///
/// "투명도 줄이기"를 존중해야 하는 상황이면(시스템 설정, 명시적
/// [GlassAccessibilityScope] 오버라이드, 혹은 테스트에서 강제로 켠 경우)
/// [OpaqueSurfaceFactory]로 대체하고, 그렇지 않으면 [GlassBridge]가
/// 제공한 팩토리(기본은 실제 리퀴드 글래스)를 그대로 쓴다.
///
/// 판정 기준은 `liquid_glass_widgets`가 이미 갖고 있는
/// [GlassAccessibilityData.of]를 그대로 재사용한다 — 우선순위는
/// (1) 트리 안의 명시적 [GlassAccessibilityScope],
/// (2) 시스템 `MediaQuery.highContrastOf` (iOS "투명도 줄이기"에 대한
/// Flutter의 근사치 — 정확히 일치하는 신호는 없다),
/// (3) `LiquidGlassWidgets.wrap(respectSystemAccessibility: false)`로
/// 전역 비활성화한 경우의 기본값(false) 순이다.
class GlassSurface extends StatelessWidget {
  const GlassSurface({
    super.key,
    required this.child,
    this.radius = 16,
    this.padding,
  });

  final Widget child;

  /// 네 모서리 공통 반지름.
  final double radius;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final reduceTransparency =
        GlassAccessibilityData.of(context).reduceTransparency;
    final factory = reduceTransparency
        ? const OpaqueSurfaceFactory()
        : GlassBridge.of(context);
    return factory.build(
      child: child,
      radius: radius,
      padding: padding,
    );
  }
}
