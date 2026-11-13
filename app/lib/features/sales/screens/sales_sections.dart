import 'package:flutter/material.dart';

import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../l10n/app_strings.dart';
import '../api/sales_models.dart';
import '../state/sales_rules.dart';

typedef PhotoOf = ImageProvider Function(String url);

/// 구역 하나 — 가는 선, 한글 이름과 기울인 영문 장식, 본문. 카드에 담지 않는다(선과 여백으로 나눈다).
class SalesSection extends StatelessWidget {
  const SalesSection({super.key, required this.title, required this.en, required this.child});

  final String title;
  final String en;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(height: 1, thickness: 1, color: AppColors.line),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            Text(title, style: AppTypography.caption),
            const Spacer(),
            ExcludeSemantics(
              child: Text(
                en,
                style: AppTypography.italicLabel.copyWith(fontSize: 14, color: AppColors.secondary),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        child,
        const SizedBox(height: AppSpacing.lg),
      ],
    );
  }
}

Widget _photo(PetCard? pet, PhotoOf photoOf, double size) => AppPhotoTile(
  image: pet?.photoUrl == null ? null : photoOf(pet!.photoUrl!),
  size: size,
);

/// 겹쳐 놓은 사진들.
class PetStack extends StatelessWidget {
  const PetStack({super.key, required this.pets, required this.photoOf, this.size = 26});

  final List<PetCard> pets;
  final PhotoOf photoOf;
  final double size;

  @override
  Widget build(BuildContext context) {
    final step = size * 0.74;
    return SizedBox(
      width: pets.isEmpty ? 0 : size + step * (pets.length - 1),
      height: size,
      child: Stack(
        children: [
          for (var i = 0; i < pets.length; i++)
            Positioned(left: step * i, child: _photo(pets[i], photoOf, size)),
        ],
      ),
    );
  }
}

/// 결제 수단 — 이름, 가는 막대, 금액, 비율.
class SalesPayments extends StatelessWidget {
  const SalesPayments({super.key, required this.summary});

  final SalesSummary summary;

  @override
  Widget build(BuildContext context) {
    final total = summary.revenue;
    return Column(
      children: [
        for (final payment in summary.payments)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Row(
              children: [
                SizedBox(width: 54, child: Text(paymentLabel(payment.method), style: AppTypography.body)),
                Expanded(
                  child: _Track(ratio: total > 0 ? payment.amount / total : 0),
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(won(payment.amount), style: AppTypography.body),
                SizedBox(
                  width: 38,
                  child: Text(
                    total > 0 ? '${payment.amount * 100 ~/ total}%' : '',
                    style: AppTypography.caption,
                    textAlign: TextAlign.right,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Track extends StatelessWidget {
  const _Track({required this.ratio});

  final double ratio;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 2,
      child: Stack(
        children: [
          const Positioned.fill(child: ColoredBox(color: AppColors.line)),
          FractionallySizedBox(
            // 읽는 도중 합이 어긋나도 폭이 0~1 을 벗어나지 않게 자른다.
            widthFactor: ratio.clamp(0, 1).toDouble(),
            child: const ColoredBox(color: AppColors.ink, child: SizedBox.expand()),
          ),
        ],
      ),
    );
  }
}

/// 메뉴 — 그 메뉴를 가장 최근에 한 아이의 사진, 이름과 건수, 금액. 다섯 줄까지.
class SalesMenus extends StatelessWidget {
  const SalesMenus({super.key, required this.menus, required this.photoOf});

  final List<SalesMenu> menus;
  final PhotoOf photoOf;

  static const _limit = 5;

  @override
  Widget build(BuildContext context) {
    // 다섯으로 자르는 것은 메뉴뿐이다. 조정 줄(서버가 맨 끝에 붙인다)은 늘 보인다 — 합이 맞아야 한다.
    final shown = [
      ...menus.where((m) => m.menuId != null).take(_limit),
      ...menus.where((m) => m.menuId == null),
    ];
    return Column(
      children: [
        for (final menu in shown)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Row(
              children: [
                // 조정 줄(총액과 항목 합의 차이)은 메뉴가 아니다 — 사진 칸 없이 자리만 맞춘다.
                if (menu.menuId == null) const SizedBox(width: 26) else _photo(menu.pet, photoOf, 26),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    menu.name,
                    style: AppTypography.body,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (menu.menuId != null) ...[
                  Text(AppStrings.salesCount(menu.count), style: AppTypography.caption),
                  const SizedBox(width: AppSpacing.md),
                ],
                Text(won(menu.amount), style: AppTypography.body),
              ],
            ),
          ),
      ],
    );
  }
}

/// 손님 — 처음 온 아이와 다시 온 아이, 그리고 단골.
class SalesGuests extends StatelessWidget {
  const SalesGuests({super.key, required this.summary, required this.photoOf});

  final SalesSummary summary;
  final PhotoOf photoOf;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        IntrinsicHeight(
          child: Row(
            children: [
              Expanded(
                child: _Half(
                  count: summary.newPetCount,
                  label: AppStrings.salesNewPets,
                  pets: summary.newPets,
                  photoOf: photoOf,
                ),
              ),
              const VerticalDivider(width: AppSpacing.xl, thickness: 1, color: AppColors.line),
              Expanded(
                child: _Half(
                  count: summary.returningPetCount,
                  label: AppStrings.salesReturningPets,
                  pets: summary.returningPets,
                  photoOf: photoOf,
                ),
              ),
            ],
          ),
        ),
        if (summary.regulars.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.lg),
          const Text(AppStrings.salesRegulars, style: AppTypography.caption),
          for (final regular in summary.regulars)
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.sm),
              child: Row(
                children: [
                  _photo(regular.pet, photoOf, 26),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      regular.pet.name,
                      style: AppTypography.body,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(AppStrings.salesTimes(regular.visitCount), style: AppTypography.caption),
                ],
              ),
            ),
        ],
      ],
    );
  }
}

class _Half extends StatelessWidget {
  const _Half({required this.count, required this.label, required this.pets, required this.photoOf});

  final int count;
  final String label;
  final List<PetCard> pets;
  final PhotoOf photoOf;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _BigCount(value: count, unit: AppStrings.salesHeads(count).replaceFirst('$count', '')),
        Text(label, style: AppTypography.caption),
        if (pets.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          PetStack(pets: pets, photoOf: photoOf, size: 24),
        ],
      ],
    );
  }
}

/// 세리프 숫자와 작은 단위.
class _BigCount extends StatelessWidget {
  const _BigCount({required this.value, this.unit});

  final int value;
  final String? unit;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$value',
          style: AppTypography.bigNumeral.copyWith(fontSize: 30, height: 1, letterSpacing: -1),
        ),
        if (unit != null)
          Padding(
            padding: const EdgeInsets.only(left: 3, bottom: 3),
            child: Text(unit!, style: AppTypography.caption),
          ),
      ],
    );
  }
}

/// 예약 — 남은 예약(과 정가로 본 예상 금액), 노쇼, 취소.
class SalesBookings extends StatelessWidget {
  const SalesBookings({super.key, required this.summary});

  final SalesSummary summary;

  @override
  Widget build(BuildContext context) {
    final remaining = summary.remaining;
    final expected = summary.expectedAmount;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (remaining != null)
              Expanded(child: _Fact(value: remaining, label: AppStrings.salesRemaining)),
            Expanded(child: _Fact(value: summary.noShow, label: AppStrings.salesNoShow)),
            Expanded(child: _Fact(value: summary.canceled, label: AppStrings.salesCanceled)),
          ],
        ),
        if (remaining != null && remaining > 0 && expected != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(
              AppStrings.salesExpected(amountPhrase(expected)),
              style: AppTypography.caption,
            ),
          ),
      ],
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact({required this.value, required this.label});

  final int value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _BigCount(value: value),
        Text(label, style: AppTypography.caption),
      ],
    );
  }
}

/// 요일별 매출 — 가장 높은 요일만 검정.
class SalesWeekdays extends StatelessWidget {
  const SalesWeekdays({super.key, required this.weekdays});

  final List<int> weekdays;

  @override
  Widget build(BuildContext context) {
    final ratios = barRatios(weekdays);
    var top = -1;
    for (var i = 0; i < weekdays.length; i++) {
      if (weekdays[i] > 0 && (top < 0 || weekdays[i] > weekdays[top])) top = i;
    }
    return SizedBox(
      height: 56,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (var i = 0; i < weekdays.length && i < 7; i++)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Container(
                      height: (ratios[i] * 36).clamp(1, 36),
                      color: i == top ? AppColors.ink : AppColors.line,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      AppStrings.weekdaysShort[i],
                      style: i == top ? AppTypography.bodyStrong.copyWith(fontSize: 11) : AppTypography.caption,
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
