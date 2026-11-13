import 'package:flutter/material.dart';

import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/sales_models.dart';
import '../state/sales_rules.dart';

/// 칸별 매출 막대(설계 ⑧ 3.2 의 6). 고른 칸만 검정이고 나머지는 옅은 회색, 아직 오지 않은 칸은 바닥선뿐이다.
/// 고른 칸 위에는 그날의 대표 사진이 뜬다. 차트 패키지를 쓰지 않고 직접 그린다.
class SalesChart extends StatelessWidget {
  const SalesChart({
    super.key,
    required this.span,
    required this.buckets,
    required this.picked,
    required this.onPick,
    required this.photoOf,
  });

  final SalesSpan span;
  final List<SalesBucket> buckets;

  /// 고른 칸의 key. 연 보기에서는 쓰지 않는다.
  final String? picked;
  final ValueChanged<String> onPick;

  /// 사진 주소 → 그림. 화면이 `mediaImagesProvider` 를 넘긴다.
  final ImageProvider Function(String url) photoOf;

  static const _barHeight = 66.0;
  static const _pinSize = 22.0;

  @override
  Widget build(BuildContext context) {
    final ratios = barRatios([for (final b in buckets) b.revenue]);
    return Column(
      key: const Key('sales-chart'),
      children: [
        SizedBox(
          height: _barHeight + _pinSize + 6,
          child: DecoratedBox(
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppColors.ink)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (var i = 0; i < buckets.length; i++)
                  Expanded(child: _bar(buckets[i], ratios[i])),
              ],
            ),
          ),
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            for (final label in _axis())
              Text(label, style: AppTypography.caption.copyWith(fontSize: 9)),
          ],
        ),
      ],
    );
  }

  Widget _bar(SalesBucket bucket, double ratio) {
    final on = bucket.key == picked;
    final photo = on && bucket.pets.isNotEmpty ? bucket.pets.first.photoUrl : null;
    return Pressable(
      minSize: 0,
      semanticLabel: AppStrings.salesBarLabel(_spoken(bucket.key), won(bucket.revenue)),
      selected: on,
      onTap: bucket.future ? null : () => onPick(bucket.key),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 1.5),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            if (on)
              // 막대보다 넓은 사진 — 옆 칸 위로 넘쳐도 된다.
              SizedBox(
                height: _pinSize + 4,
                child: OverflowBox(
                  minWidth: _pinSize,
                  maxWidth: _pinSize,
                  alignment: Alignment.topCenter,
                  child: AppPhotoTile(
                    image: photo == null ? null : photoOf(photo),
                    size: _pinSize,
                  ),
                ),
              ),
            Container(
              // 방문이 있는 날은 0원이어도 1 은 보이게, 아직 오지 않은 날은 바닥선만.
              height: bucket.future ? 0 : (ratio * _barHeight).clamp(1, _barHeight),
              decoration: BoxDecoration(
                color: on ? AppColors.ink : AppColors.line,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(2)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 화면 읽기용 — `14일`, `11월`.
  String _spoken(String key) {
    final parts = key.split('-');
    return parts.length == 3 ? '${int.parse(parts[2])}일' : '${int.parse(parts[1])}월';
  }

  List<String> _axis() {
    if (buckets.isEmpty) return const [];
    if (span == SalesSpan.week) return AppStrings.weekdaysShort;
    if (span == SalesSpan.year) return [for (var m = 1; m <= buckets.length; m++) '$m'];
    return ['1', '10', '20', '${buckets.length}'];
  }
}
