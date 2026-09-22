import 'package:flutter/cupertino.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/services.dart';

import '../tokens/app_springs.dart';

/// 누르면 0.96배로 눌렸다가 스프링으로 되돌아오는 "누를 수 있는" 래퍼.
///
/// - 누르는 순간 가벼운 햅틱을 준다.
/// - `MediaQuery.disableAnimationsOf`가 true(시스템 "동작 줄이기")이면
///   스프링 스케일 대신 옅은 페이드로 대체한다.
/// - `semanticLabel`을 주면 버튼으로 접근성에 노출한다. 의미 노드는 자기
///   크기(최소 44×44)로 따로 잡힌다 — 행 안에 두어도 행 전체로 번지지 않는다.
/// - 시각적 크기가 44×44보다 작아도 탭 영역은 `minSize`(기본 44) 이상을
///   보장한다.
class Pressable extends StatefulWidget {
  const Pressable({
    super.key,
    required this.child,
    this.onTap,
    this.semanticLabel,
    this.minSize = 44,
  });

  final Widget child;
  final VoidCallback? onTap;
  final String? semanticLabel;
  final double minSize;

  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable>
    with SingleTickerProviderStateMixin {
  static const double _pressedScale = 0.96;
  static const double _pressedOpacity = 0.6;

  late final AnimationController _controller = AnimationController(
    vsync: this,
    value: 0, // 0 = 안 눌림, 1 = 완전히 눌림
  );

  // didChangeDependencies에서 미리 읽어 캐시해둔다. onTapCancel은 위젯이
  // 통째로 해제되는 도중(자식 GestureDetector의 dispose 연쇄)에도 불릴 수
  // 있는데, 그 시점엔 이 State의 context가 이미 "inactive"라 MediaQuery를
  // 다시 조회하면 "Looking up a deactivated widget's ancestor" 단언에
  // 걸린다 — mounted 체크만으론 못 막는다(inactive여도 mounted는 true).
  late bool _reduceMotion;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.disableAnimationsOf(context);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _animateTo(double target) {
    if (_reduceMotion) {
      // 동작 줄이기: 스프링 없이 짧은 페이드만.
      _controller.animateTo(target, duration: AppSprings.fadeDuration);
    } else {
      // 누를 때와 뗄 때 서로 다른 스프링을 써서 "눌림"과 "복귀"의 질감을
      // 다르게 준다 — 복귀 쪽이 조금 더 튀는 느낌.
      final spring = target == 1 ? AppSprings.press : AppSprings.settle;
      final simulation = SpringSimulation(spring, _controller.value, target, 0);
      _controller.animateWith(simulation);
    }
  }

  void _onTapDown(TapDownDetails _) {
    HapticFeedback.lightImpact();
    _animateTo(1);
  }

  void _onTapEnd([TapUpDetails? _]) {
    _animateTo(0);
  }

  @override
  Widget build(BuildContext context) {
    // container: true — 자기 의미 노드를 따로 만든다. 없으면 이름표와 버튼
    // 표시가 조상 노드(예: ListView 의 행)에 합쳐져, 스크린리더 포커스와
    // 이름표로 찾은 탭 위치가 행 전체 폭으로 잡힌다.
    return Semantics(
      container: true,
      button: widget.onTap != null,
      label: widget.semanticLabel,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: widget.onTap,
        onTapDown: _onTapDown,
        onTapUp: _onTapEnd,
        onTapCancel: _onTapEnd,
        // Center를 쓰지 않는다 — Row 안에서 flex가 아닌 자식(예: AppSegment의
        // 탭)은 주축으로 무한대(loose, maxWidth: infinity) 제약을 받는데,
        // Center/Align은 factor가 없으면 "가능한 한 크게" 채우려다 그
        // 무한대를 그대로 자기 크기로 쓰려 해서 런타임에 깨진다. 대신
        // ConstrainedBox 하나만 써서 자식이 원래 크기보다 작을 때만
        // 최소 44×44까지 조용히 채워지게 한다.
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minWidth: widget.minSize,
            minHeight: widget.minSize,
          ),
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final t = _controller.value.clamp(0.0, 1.0);
              if (_reduceMotion) {
                return Opacity(
                  opacity: 1 - t * (1 - _pressedOpacity),
                  child: child,
                );
              }
              final scale = 1 - t * (1 - _pressedScale);
              return Transform.scale(scale: scale, child: child);
            },
            child: widget.child,
          ),
        ),
      ),
    );
  }
}
