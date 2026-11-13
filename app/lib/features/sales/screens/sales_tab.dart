import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/async_body.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/time/shop_time.dart';
import '../../../core/time/today_provider.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_photo_fan.dart';
import '../../../design/widgets/app_segment.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/sales_models.dart';
import '../state/sales_providers.dart';
import '../state/sales_rules.dart';
import 'sales_chart.dart';
import 'sales_hero.dart';
import 'sales_sections.dart';

/// 홈의 [매출] 탭(설계 ⑧ 3.2) — 기간의 매출을 큰 숫자와 그 매출을 만든 아이들의 사진으로 보인다.
///
/// 사장만 본다. 직원에게는 안내만 보이고 서버를 부르지 않는다(가리는 것은 서버다).
/// 색은 사진에서만 온다 — 색 카드·도넛·초록빨강 표시를 쓰지 않는다.
class SalesTab extends ConsumerStatefulWidget {
  const SalesTab({super.key});

  @override
  ConsumerState<SalesTab> createState() => _SalesTabState();
}

class _SalesTabState extends ConsumerState<SalesTab> {
  SalesSpan _span = SalesSpan.month;

  /// 보는 기간 안의 아무 날. null 이면 오늘이다.
  DateTime? _anchor;

  /// 손으로 고른 칸. 기간을 바꾸면 비운다.
  String? _picked;

  void _show(SalesSpan span, DateTime? anchor) => setState(() {
    _span = span;
    _anchor = anchor;
    _picked = null;
  });

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider);
    final today = ref.watch(todayProvider);
    final anchor = _anchor ?? today;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Head(),
        if (!ref.watch(isOwnerProvider) || shopId == null)
          const Expanded(
            child: Center(
              child: Padding(
                padding: EdgeInsets.all(AppSpacing.xl),
                child: Text(
                  AppStrings.salesOwnerOnly,
                  style: AppTypography.body,
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          )
        else ...[
          _PeriodBar(
            span: _span,
            canGoNext: canGoNext(_span, anchor, today),
            onSpan: (span) => _show(span, null),
            onShift: (step) => _show(_span, shiftAnchor(_span, anchor, step)),
          ),
          Expanded(child: _body(shopId, anchor, today)),
        ],
      ],
    );
  }

  Widget _body(int shopId, DateTime anchor, DateTime today) {
    final key = (shopId: shopId, span: _span, anchor: isoDay(anchor));
    return AsyncBody<SalesSummary>(
      value: ref.watch(salesSummaryProvider(key)),
      onRetry: () => ref.invalidate(salesSummaryProvider(key)),
      onRefresh: () => ref.refresh(salesSummaryProvider(key).future),
      builder: (summary) => _SalesBody(
        summary: summary,
        picked: _picked ?? selectedBucketKey(summary, today),
        onPick: (bucketKey) {
          if (summary.span == SalesSpan.year) {
            // 연 보기의 막대는 그 달의 월 보기로 간다.
            final parts = bucketKey.split('-');
            _show(SalesSpan.month, DateTime(int.parse(parts[0]), int.parse(parts[1])));
          } else {
            setState(() => _picked = bucketKey);
          }
        },
      ),
    );
  }
}

/// 매장 이름과 설정.
class _Head extends ConsumerWidget {
  const _Head();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.sm, 0),
      child: Row(
        children: [
          Expanded(
            child: Text(
              ref.watch(shopNameProvider),
              style: AppTypography.titleEn,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          Pressable(
            semanticLabel: AppStrings.settingsLabel,
            onTap: () => context.push('/settings'),
            child: const Icon(Icons.settings_outlined),
          ),
        ],
      ),
    );
  }
}

/// 기간 고르기 — [일][주][월][연] 과 앞뒤 이동. 이번 기간에서는 다음으로 가지 못한다.
class _PeriodBar extends StatelessWidget {
  const _PeriodBar({
    required this.span,
    required this.canGoNext,
    required this.onSpan,
    required this.onShift,
  });

  final SalesSpan span;
  final bool canGoNext;
  final ValueChanged<SalesSpan> onSpan;
  final ValueChanged<int> onShift;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.sm, 0),
      child: Row(
        children: [
          // 좁은 화면(폭 320)에서는 네 칸과 화살표 둘이 한 줄에 다 들어가지 않는다 — 세그먼트가 조금 줄어든다.
          Expanded(
            child: Align(
              alignment: Alignment.centerLeft,
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: AppSegment(
                  labels: const [
                    AppStrings.salesSpanDay,
                    AppStrings.salesSpanWeek,
                    AppStrings.salesSpanMonth,
                    AppStrings.salesSpanYear,
                  ],
                  currentIndex: span.index,
                  onChanged: (i) => onSpan(SalesSpan.values[i]),
                ),
              ),
            ),
          ),
          Pressable(
            semanticLabel: AppStrings.salesPrev,
            onTap: () => onShift(-1),
            child: const Icon(Icons.chevron_left),
          ),
          Pressable(
            semanticLabel: AppStrings.salesNext,
            onTap: canGoNext ? () => onShift(1) : null,
            child: Opacity(
              opacity: canGoNext ? 1 : 0.3,
              child: const Icon(Icons.chevron_right),
            ),
          ),
        ],
      ),
    );
  }
}

class _SalesBody extends ConsumerWidget {
  const _SalesBody({required this.summary, required this.picked, required this.onPick});

  final SalesSummary summary;
  final String? picked;
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = summary;
    final images = ref.watch(mediaImagesProvider);
    // 완료한 방문이 하나도 없는 기간 — 0 을 크게 두지 않고 안내를 보인다.
    final empty = s.revenue == 0 && s.visitCount == 0;
    SalesBucket? chosen;
    for (final bucket in s.buckets) {
      if (bucket.key == picked) chosen = bucket;
    }
    final weekdays = s.weekdays;
    final report = s.report;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      // 아래 여백은 떠 있는 탭바와 + 버튼의 자리다.
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, 132),
      children: [
        SalesHero(summary: s, empty: empty),
        if (!empty) ...[
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              PetStack(pets: s.faces, photoOf: images.of, size: 34),
              if (s.faces.isNotEmpty) const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(facesLine(s), style: AppTypography.body),
                    if (s.average != null)
                      Text(AppStrings.salesAverage(won(s.average!)), style: AppTypography.caption),
                  ],
                ),
              ),
            ],
          ),
          if (s.buckets.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.lg),
            SalesChart(
              span: s.span,
              buckets: s.buckets,
              picked: picked,
              onPick: onPick,
              photoOf: images.of,
            ),
          ],
          if (chosen != null && s.span != SalesSpan.year) ...[
            const SizedBox(height: AppSpacing.md),
            _DayCard(bucket: chosen, photoOf: images.of),
          ],
        ],
        const SizedBox(height: AppSpacing.xl),
        if (!empty && s.payments.isNotEmpty)
          SalesSection(
            title: AppStrings.salesPayment,
            en: AppStrings.salesPaymentEn,
            child: SalesPayments(summary: s),
          ),
        if (!empty && s.menus.isNotEmpty)
          SalesSection(
            title: AppStrings.salesMenu,
            en: AppStrings.salesMenuEn,
            child: SalesMenus(menus: s.menus, photoOf: images.of),
          ),
        if (!empty)
          SalesSection(
            title: AppStrings.salesGuests,
            en: AppStrings.salesGuestsEn,
            child: SalesGuests(summary: s, photoOf: images.of),
          ),
        SalesSection(
          title: AppStrings.salesBookings,
          en: AppStrings.salesBookingsEn,
          child: SalesBookings(summary: s),
        ),
        if (!empty && weekdays != null)
          SalesSection(
            title: AppStrings.salesWeekday,
            en: AppStrings.salesWeekdayEn,
            child: SalesWeekdays(weekdays: weekdays),
          ),
        if (!empty && report != null)
          SalesSection(
            title: AppStrings.salesReport,
            en: AppStrings.salesReportEn,
            child: Text(
              AppStrings.salesReportLine(report.completed, report.sent, report.opened),
              style: AppTypography.body,
            ),
          ),
        // 아래 두 줄은 ⑧-3 에서 목록으로 이어진다. 지금은 사실만 보인다.
        if (s.duePetCount > 0)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(AppStrings.salesDuePets(s.duePetCount), style: AppTypography.body),
          ),
        if (s.unrecordedCount > 0)
          Text(AppStrings.salesUnrecorded(s.unrecordedCount), style: AppTypography.caption),
      ],
    );
  }
}

/// 고른 날 — 날짜와 금액, 그날 아이들의 겹친 사진과 이름. 누르면 그날의 하루 화면으로 간다.
///
/// 스크롤되는 본문 안이라 글래스가 아니라 흰 카드다(글래스는 떠 있는 조작 계층에만 쓴다).
class _DayCard extends StatelessWidget {
  const _DayCard({required this.bucket, required this.photoOf});

  final SalesBucket bucket;
  final ImageProvider Function(String url) photoOf;

  @override
  Widget build(BuildContext context) {
    final date = parseDay(bucket.key);
    final heading = AppStrings.dayHeading(date.day, date.weekday);
    final photos = [
      for (final pet in bucket.pets)
        if (pet.photoUrl != null) photoOf(pet.photoUrl!),
    ];
    return Pressable(
      key: const Key('sales-day-card'),
      semanticLabel: heading,
      onTap: () => context.push('/visits/day/${bucket.key}'),
      child: AppCard(
        padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.md),
        child: ExcludeSemantics(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Text(heading, style: AppTypography.bodyStrong),
                  const Spacer(),
                  Text('${won(bucket.revenue)}원', style: AppTypography.bodyStrong),
                ],
              ),
              if (photos.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.sm),
                  child: AppPhotoFan(images: photos, height: 62),
                ),
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      bucket.pets.isEmpty
                          ? AppStrings.salesCount(bucket.visitCount)
                          : bucket.pets.map((p) => p.name).join(' · '),
                      style: AppTypography.caption,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const Icon(Icons.chevron_right, size: 18),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
