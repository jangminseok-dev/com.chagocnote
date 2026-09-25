import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/media_images.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_shadows.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../design/widgets/app_glass_card.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../customer/state/customer_input.dart';
import '../api/feed_models.dart';
import '../state/feed_controller.dart';
import 'visit_labels.dart';

/// 기록 피드(④ 설계 10.1 ②) — 완료 방문을 최신순으로. 끝에서 400px 안으로 내려오면 다음 쪽을 부른다.
/// 다음 쪽이 한 번 실패했으면 스크롤로는 다시 부르지 않는다 — 목록 끝의 "다시 시도"로만.
class FeedList extends ConsumerStatefulWidget {
  const FeedList({super.key, required this.query});

  final FeedQuery query;

  @override
  ConsumerState<FeedList> createState() => _FeedListState();
}

class _FeedListState extends ConsumerState<FeedList> {
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_maybeLoadMore);
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _maybeLoadMore() {
    if (!_scroll.hasClients || _scroll.position.extentAfter > 400) return;
    final provider = feedControllerProvider(widget.query);
    if (ref.read(provider).value?.loadMoreError != null) return;
    ref.read(provider.notifier).loadMore();
  }

  @override
  Widget build(BuildContext context) {
    final provider = feedControllerProvider(widget.query);
    final async = ref.watch(provider);
    final state = async.value;
    if (state == null) {
      return async.hasError
          ? AppErrorRetry(
              message: messageFor(async.error!),
              onRetry: () => ref.invalidate(provider),
            )
          : const Center(child: CircularProgressIndicator());
    }
    if (state.items.isEmpty) return const _Empty();
    // 아래 여백은 떠 있는 탭바와 + 버튼 몫이다.
    return ListView.builder(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
      itemCount: state.items.length + 1,
      itemBuilder: (context, index) {
        if (index < state.items.length) {
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.lg),
            child: FeedCard(item: state.items[index]),
          );
        }
        if (state.loadingMore) {
          return const Padding(
            padding: EdgeInsets.all(AppSpacing.lg),
            child: Center(child: CircularProgressIndicator()),
          );
        }
        if (state.loadMoreError != null) {
          return Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: AppErrorRetry.row(
              message: messageFor(state.loadMoreError!),
              onRetry: () => ref.read(provider.notifier).loadMore(),
            ),
          );
        }
        return const SizedBox.shrink();
      },
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty();

  @override
  Widget build(BuildContext context) => const Center(
    child: Padding(
      padding: EdgeInsets.all(AppSpacing.xl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(AppStrings.feedEmpty, style: AppTypography.body),
          SizedBox(height: AppSpacing.xs),
          Text(AppStrings.feedEmptyCaption, style: AppTypography.caption),
        ],
      ),
    ),
  );
}

/// 피드 한 장 — 대표 사진 크게(둥근 사각형·흰 테두리), 그 위 글래스 이름 카드, 아래에 날짜·메뉴·
/// 케어 메모 앞부분·사진 수. 사진이 없으면 회색 자리. 누르면 방문 상세.
class FeedCard extends ConsumerWidget {
  const FeedCard({super.key, required this.item});

  final FeedItem item;

  static const _photoHeight = 240.0;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cover = item.cover;
    final pet = item.pet;
    final name = pet?.name ?? ownerLabel(item.customer);
    return Pressable(
      semanticLabel: '$name ${dayLabel(item.completedAt.wall)}',
      onTap: () => context.push('/visits/${item.visitId}'),
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Stack(
              children: [
                Container(
                  height: _photoHeight,
                  decoration: BoxDecoration(
                    color: AppColors.line,
                    image: cover == null
                        ? null
                        : DecorationImage(
                            image: ref.watch(mediaImagesProvider).of(cover),
                            fit: BoxFit.cover,
                          ),
                    borderRadius: BorderRadius.circular(AppRadius.lg),
                    border: Border.all(color: AppColors.white, width: 2),
                    boxShadow: AppShadows.floating,
                  ),
                ),
                // 글래스는 이 이름 카드에만(설계 10.1 ②).
                Positioned(
                  left: AppSpacing.md,
                  bottom: AppSpacing.md,
                  child: AppGlassCard(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.md,
                      vertical: AppSpacing.sm,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          name,
                          style: AppTypography.titleKo.copyWith(fontSize: 17),
                        ),
                        if (pet != null)
                          Text(
                            '${pet.breed} · ${formatWeight(pet.weightKg)}',
                            style: AppTypography.caption,
                          ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            AppCard(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    [
                      dayLabel(item.completedAt.wall),
                      if (item.menus.isNotEmpty) item.menus.join(' · '),
                    ].join(' · '),
                    style: AppTypography.bodyStrong,
                  ),
                  if (item.careNote != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      item.careNote!,
                      style: AppTypography.body,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                  if (item.mediaCount > 0) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      AppStrings.mediaCount(item.mediaCount),
                      style: AppTypography.caption,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
