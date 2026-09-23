import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_typography.dart';

/// 점선 테두리의 둥근 사각형 자리 — 아직 오지 않은 날의 예약처럼 "비어 있지만
/// 잡혀 있는" 것을 보인다. [count]를 가운데에 옅게 적는다.
class AppDashedTile extends StatelessWidget {
  const AppDashedTile({super.key, required this.count, this.size = 38});

  final int count;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: const _DashedBorderPainter(),
        child: Center(
          child: Text(
            '$count',
            style: AppTypography.caption.copyWith(fontWeight: FontWeight.w700),
          ),
        ),
      ),
    );
  }
}

class _DashedBorderPainter extends CustomPainter {
  const _DashedBorderPainter();

  static const _dash = 3.0;
  static const _gap = 2.5;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(AppRadius.sm),
    ).deflate(0.5);
    canvas.drawRRect(rect, Paint()..color = AppColors.backgroundBottom);
    final border = Paint()
      ..color = AppColors.secondary
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final path = Path()..addRRect(rect);
    for (final metric in path.computeMetrics()) {
      for (var d = 0.0; d < metric.length; d += _dash + _gap) {
        canvas.drawPath(metric.extractPath(d, d + _dash), border);
      }
    }
  }

  @override
  bool shouldRepaint(_DashedBorderPainter oldDelegate) => false;
}
