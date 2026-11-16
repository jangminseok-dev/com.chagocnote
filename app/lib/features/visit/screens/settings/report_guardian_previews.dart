import 'package:flutter/material.dart';

import '../../../../design/tokens/app_colors.dart';
import '../../../../design/tokens/app_radius.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../l10n/app_strings.dart';

/// 알림장 설정의 **보호자가 받는 모습**(⑫ 설계 3.3·3.6) — 바꾸면 보호자에게 무엇이 달라지는지를 설정하는
/// 자리에서 보인다. 본뜬 그림이라 누르는 동작은 없다.

/// 몸무게 보이기 스위치 바로 아래. 켜져 있으면 알림장의 몸무게 한 줄과 작은 변화 그림의 본, 꺼져 있으면
/// 보호자에게 보이지 않는다는 글.
class WeightPreview extends StatelessWidget {
  const WeightPreview({super.key, required this.on});

  final bool on;

  @override
  Widget build(BuildContext context) {
    if (!on) {
      return const Padding(
        padding: EdgeInsets.only(bottom: AppSpacing.sm),
        child: SizedBox(
          width: double.infinity,
          child: Text(AppStrings.reportWeightOff, style: AppTypography.caption),
        ),
      );
    }
    return Padding(
      key: const ValueKey('report-weight-preview'),
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            AppStrings.reportGuardianSees,
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.xs),
          Row(
            children: [
              const Text(
                AppStrings.reportWeightSample,
                style: AppTypography.body,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: SizedBox(
                  height: 28,
                  child: ExcludeSemantics(
                    child: CustomPaint(painter: _SampleLinePainter()),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// 몸무게 변화의 본 — 점 넷을 잇는 가는 선. 숫자·풀이 없이 모양만(웹의 몸무게 그림과 같은 결).
class _SampleLinePainter extends CustomPainter {
  static const _points = [0.55, 0.35, 0.5, 0.2];

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.ink
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
    final dot = Paint()..color = AppColors.ink;
    final step = size.width / (_points.length - 1);
    final path = Path();
    for (final (i, y) in _points.indexed) {
      final point = Offset(i * step, y * size.height + 4);
      i == 0
          ? path.moveTo(point.dx, point.dy)
          : path.lineTo(point.dx, point.dy);
      canvas.drawCircle(point, 2.5, dot);
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// 알림장 끝부분의 본 — 매장 카드(매장 정보를 켰을 때) → 리뷰 줄 → 꼬리. [faded] 면 흐리게(주소가 아직
/// 없을 때 "이렇게 나와요").
class ReviewPreview extends StatelessWidget {
  const ReviewPreview({
    super.key,
    required this.shopName,
    required this.showShopInfo,
    required this.text,
    this.faded = false,
  });

  final String shopName;
  final bool showShopInfo;
  final String text;
  final bool faded;

  @override
  Widget build(BuildContext context) {
    final preview = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (showShopInfo)
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppColors.line),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(shopName, style: AppTypography.bodyStrong),
                const SizedBox(height: AppSpacing.xs),
                const _Bar(width: 140),
                const SizedBox(height: AppSpacing.xs),
                const _Bar(width: 100),
              ],
            ),
          ),
        const SizedBox(height: AppSpacing.md),
        Center(
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.sm,
            ),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppRadius.pill),
              border: Border.all(color: AppColors.ink),
            ),
            child: Text(
              text,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Center(
          child: Text(
            AppStrings.reportTail,
            style: AppTypography.caption.copyWith(fontStyle: FontStyle.italic),
          ),
        ),
      ],
    );
    return faded ? Opacity(opacity: 0.4, child: preview) : preview;
  }
}

/// 매장 카드 안의 글 자리(전화·주소) — 글 대신 옅은 막대.
class _Bar extends StatelessWidget {
  const _Bar({required this.width});

  final double width;

  @override
  Widget build(BuildContext context) => Container(
    width: width,
    height: 8,
    decoration: BoxDecoration(
      color: AppColors.line,
      borderRadius: BorderRadius.circular(AppRadius.pill),
    ),
  );
}
