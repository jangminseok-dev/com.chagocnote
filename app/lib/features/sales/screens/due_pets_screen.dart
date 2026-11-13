import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/proxy/media_images.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/today_provider.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/sales_models.dart';
import '../state/sales_paged.dart';
import '../state/sales_rules.dart';
import 'sales_paged_list.dart';

/// 다시 올 때가 지난 아이(설계 ⑧ 3.3) — 사진·이름·"9주 전", 오래된 순. 기간과 상관없다.
///
/// 줄을 누르면 반려동물 상세로 간다(거기서 보호자 번호·예약으로 이어진다). 연락·알림 버튼은 없다.
class DuePetsScreen extends ConsumerWidget {
  const DuePetsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final provider = duePetsProvider(ref.watch(selectedShopIdProvider) ?? 0);
    final images = ref.watch(mediaImagesProvider);
    final today = ref.watch(todayProvider);
    return SalesPagedScaffold<DuePetItem>(
      screenKey: ScreenKeys.duePets,
      title: AppStrings.salesDuePetsTitle,
      value: ref.watch(provider),
      emptyText: AppStrings.salesDuePetsEmpty,
      onRetry: () => ref.invalidate(provider),
      onRefresh: () => ref.refresh(provider.future),
      onLoadMore: () => ref.read(provider.notifier).loadMore(),
      row: (item) {
        final since = sinceLabel(item.lastVisitDate, today);
        return SalesListRow(
          semanticLabel: AppStrings.salesDuePetRowLabel(item.pet.name, since),
          // 상세에서 예약을 잡으면 이 목록에서 빠진다 — 돌아오면 다시 읽는다.
          onTap: () async {
            await context.push('/pets/${item.pet.petId}');
            ref.invalidate(provider);
          },
          showPhoto: true,
          photo: item.pet.photoUrl == null ? null : images.of(item.pet.photoUrl!),
          title: item.pet.name,
          trailing: since,
        );
      },
    );
  }
}
