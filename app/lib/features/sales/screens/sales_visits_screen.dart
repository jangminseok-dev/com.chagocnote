import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/proxy/media_images.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/shop_time.dart';
import '../../../core/time/today_provider.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/sales_models.dart';
import '../state/sales_paged.dart';
import '../state/sales_rules.dart';
import 'sales_paged_list.dart';

/// 매출 탭의 숫자에서 이어지는 방문들(설계 ⑧ 3.2 의 9·12·15) — 금액을 적지 않은 방문, 노쇼, 취소, 한 메뉴의 방문.
///
/// 그 기간의 것만 보인다. 줄을 누르면 방문 상세로 간다. 아이를 보일 수 없는 방문(보호자만의 방문,
/// 익명화한 고객)도 줄은 있다 — 날짜만 보인다.
class SalesVisitsScreen extends ConsumerWidget {
  const SalesVisitsScreen({super.key, required this.query});

  /// 주소의 질의(`span`·`anchor`·`filter`·`menu_id`·`menu`). 깨진 값은 기본값으로 읽는다.
  final Map<String, String> query;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asked = visitsQueryOf(query, ref.watch(todayProvider));
    final SalesVisitsKey key = (
      shopId: ref.watch(selectedShopIdProvider) ?? 0,
      span: asked.span,
      anchor: isoDay(asked.anchor),
      filter: asked.filter,
      menuId: asked.menuId,
    );
    final provider = salesVisitsProvider(key);
    final images = ref.watch(mediaImagesProvider);
    return SalesPagedScaffold<SalesVisitItem>(
      screenKey: ScreenKeys.salesVisits,
      title: visitsTitle(asked.filter, menuName: query['menu']),
      value: ref.watch(provider),
      emptyText: AppStrings.salesVisitsEmpty,
      onRetry: () => ref.invalidate(provider),
      onRefresh: () => ref.refresh(provider.future),
      onLoadMore: () => ref.read(provider.notifier).loadMore(),
      row: (item) {
        final pet = item.pet;
        final date = visitDateLabel(item.date);
        final amount = item.amount;
        return SalesListRow(
          semanticLabel: AppStrings.salesVisitRowLabel(pet?.name ?? '', date).trim(),
          // 상세에서 금액을 적거나 상태를 되돌렸을 수 있다 — 돌아오면 다시 읽는다.
          onTap: () async {
            await context.push('/visits/${item.visitId}');
            ref.invalidate(provider);
          },
          showPhoto: pet != null,
          photo: pet?.photoUrl == null ? null : images.of(pet!.photoUrl!),
          title: pet?.name ?? date,
          subtitle: pet == null ? null : date,
          trailing: amount == null ? null : '${won(amount)}${AppStrings.wonUnit}',
        );
      },
    );
  }
}
