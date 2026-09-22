import 'package:flutter/widgets.dart';

import '../bridge/glass_surface.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';

/// 앱 전역에서 쓰는 반투명 유리 카드.
///
/// 실제 렌더링은 [GlassSurface]에 위임한다 — "투명도 줄이기"가 켜져
/// 있으면 자동으로 불투명 대체 표면을 쓴다.
class AppGlassCard extends StatelessWidget {
  const AppGlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.lg),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      borderRadius: const BorderRadius.all(Radius.circular(AppRadius.lg)),
      padding: padding,
      child: child,
    );
  }
}
