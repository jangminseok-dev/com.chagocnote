import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/app_icon_toggle.dart';
import '../../../design/widgets/app_segment.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../state/customer_list_controller.dart';
import '../state/customer_view_mode.dart';
import '../state/search_debouncer.dart';
import 'family_card_view.dart';

/// 홈의 "고객" 탭 — 제목과 반려동물 수, 보기 전환, 정렬, 무지개다리 포함,
/// 검색창, 가족 카드 목록(아래로 내리면 다음 페이지).
class CustomerListTab extends ConsumerStatefulWidget {
  const CustomerListTab({super.key});

  @override
  ConsumerState<CustomerListTab> createState() => _CustomerListTabState();
}

class _CustomerListTabState extends ConsumerState<CustomerListTab> {
  static const _sorts = ['recent', 'name', 'last_visit'];

  final _search = TextEditingController();
  final _scroll = ScrollController();
  late final SearchDebouncer _debouncer = SearchDebouncer(
    onSearch: (q) => setState(() {
      _q = q;
      _scrollToTop();
    }),
  );

  String _q = '';
  String _sort = 'recent';
  bool _includePassed = false;

  /// 조건이 바뀌어 새로 불러오는 동안 앞선 결과를 그대로 보인다(깜빡임 방지).
  CustomerListState? _lastShown;

  /// 검색어·정렬·무지개다리 포함이 바뀌면 목록 스크롤을 맨 위로 되돌린다.
  void _scrollToTop() {
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  @override
  void initState() {
    super.initState();
    _search.addListener(() => _debouncer.onChanged(_search.value));
    _scroll.addListener(_maybeLoadMore);
  }

  @override
  void dispose() {
    _debouncer.dispose();
    _search.dispose();
    _scroll.dispose();
    super.dispose();
  }

  CustomerListQuery? get _query {
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null) return null;
    return (shopId: shopId, q: _q, sort: _sort, includePassed: _includePassed);
  }

  /// 끝에서 400px 안으로 내려오면 다음 페이지를 부른다. 다음 페이지가 한 번
  /// 실패했으면 스크롤로는 다시 부르지 않는다 — 목록 끝의 "다시 시도"로만.
  void _maybeLoadMore() {
    final query = _query;
    if (query == null || !_scroll.hasClients) return;
    if (_scroll.position.extentAfter > 400) return;
    final provider = customerListControllerProvider(query);
    if (ref.read(provider).value?.loadMoreError != null) return;
    ref.read(provider.notifier).loadMore();
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(selectedShopIdProvider);   // 매장이 바뀌면 다시 그린다
    final query = _query;
    final mode =
        ref.watch(customerViewModeProvider).value ?? CustomerViewMode.list;
    final async = query == null
        ? const AsyncValue<CustomerListState>.loading()
        : ref.watch(customerListControllerProvider(query));
    final shown = async.value ?? (async.isLoading ? _lastShown : null);
    if (async.value != null) _lastShown = async.value;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            0,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text(AppStrings.customersTitle, style: AppTypography.titleKo),
              const SizedBox(width: AppSpacing.sm),
              if (shown != null)
                Text(
                  AppStrings.petCountText(shown.petCount),
                  style: AppTypography.caption,
                ),
              const Spacer(),
              AppIconToggle(
                icons: const [Icons.view_list, Icons.grid_view],
                labels: const [AppStrings.viewAsList, AppStrings.viewAsGrid],
                currentIndex: mode.index,
                onChanged: (i) => ref
                    .read(customerViewModeProvider.notifier)
                    .select(CustomerViewMode.values[i]),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: Row(
            children: [
              AppSegment(
                labels: const [
                  AppStrings.sortRecent,
                  AppStrings.sortName,
                  AppStrings.sortLastVisit,
                ],
                currentIndex: _sorts.indexOf(_sort),
                onChanged: (i) => setState(() {
                  _sort = _sorts[i];
                  _scrollToTop();
                }),
              ),
              const Spacer(),
              AppChoiceChip(
                label: AppStrings.includePassed,
                selected: _includePassed,
                onTap: () => setState(() {
                  _includePassed = !_includePassed;
                  _scrollToTop();
                }),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.xs,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: TextField(
            controller: _search,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: AppStrings.customerSearchHint,
              hintStyle: AppTypography.body.copyWith(
                color: AppColors.secondary,
              ),
              prefixIcon: const Icon(Icons.search, color: AppColors.secondary),
              filled: true,
              fillColor: AppColors.white,
              isDense: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: const BorderSide(color: AppColors.line),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: const BorderSide(color: AppColors.line),
              ),
            ),
          ),
        ),
        Expanded(
          child: shown != null
              ? _CardList(
                  state: shown,
                  mode: mode,
                  searching: _q.isNotEmpty,
                  scroll: _scroll,
                  onRetryMore: () => ref
                      .read(customerListControllerProvider(query!).notifier)
                      .loadMore(),
                )
              : async.hasError
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(messageFor(async.error!), style: AppTypography.body),
                      const SizedBox(height: AppSpacing.lg),
                      AppButton(
                        label: AppStrings.retry,
                        onPressed: () => ref.invalidate(
                          customerListControllerProvider(query!),
                        ),
                      ),
                    ],
                  ),
                )
              : const Center(child: CircularProgressIndicator()),
        ),
      ],
    );
  }
}

class _CardList extends StatelessWidget {
  const _CardList({
    required this.state,
    required this.mode,
    required this.searching,
    required this.scroll,
    required this.onRetryMore,
  });

  final CustomerListState state;
  final CustomerViewMode mode;
  final bool searching;
  final ScrollController scroll;
  final VoidCallback onRetryMore;

  @override
  Widget build(BuildContext context) {
    if (state.items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                searching
                    ? AppStrings.customersNoMatch
                    : AppStrings.customersEmpty,
                style: AppTypography.body,
              ),
              if (!searching) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  AppStrings.customersEmptyCaption,
                  style: AppTypography.caption,
                ),
              ],
            ],
          ),
        ),
      );
    }
    // 아래 여백은 떠 있는 탭바와 + 버튼 몫이다.
    return ListView.builder(
      controller: scroll,
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, 120),
      itemCount: state.items.length + 1,
      itemBuilder: (context, index) {
        if (index == state.items.length) {
          if (state.loadingMore) {
            return const Padding(
              padding: EdgeInsets.all(AppSpacing.lg),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          if (state.loadMoreError != null) {
            return Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                children: [
                  Text(
                    messageFor(state.loadMoreError!),
                    style: AppTypography.caption,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  AppButton(label: AppStrings.retry, onPressed: onRetryMore),
                ],
              ),
            );
          }
          return const SizedBox.shrink();
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: FamilyCardView(card: state.items[index], mode: mode),
        );
      },
    );
  }
}
