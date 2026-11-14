import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/async_body.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/search_debouncer.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_search_field.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/search_models.dart';
import '../state/search_controller.dart';
import '../state/search_rules.dart';

/// 기록 찾기(⑨-1b) — 매장이 적어 둔 글을 적어 둔 말로 찾는다. [petId]를 주면 그 아이 안에서만 찾는다.
///
/// 입력을 0.5초 쉬면 묻는다. 줄을 누르면 방문 상세나 반려동물 상세로 가고, 돌아오면 검색어와 결과가 그대로다.
/// 서버는 맞는 글이 없어도 가까운 글을 몇 줄 준다 — 그래서 결과 위에 "가까운 기록부터"라고 한 줄 알린다.
/// 뜻으로 찾았는지 글자로 찾았는지는 가르지 않는다. 검색어는 기기에 남기지 않는다.
class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key, this.petId, this.petName});

  final int? petId;

  /// 좁힌 아이의 이름 — 화면 위의 한 줄에만 쓴다. 없으면 이름 없이 알린다.
  final String? petName;

  static const fieldKey = Key('search-field');

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _text = TextEditingController();
  late final SearchDebouncer _debouncer;

  SearchScope get _scope =>
      (shopId: ref.read(selectedShopIdProvider) ?? 0, petId: widget.petId);

  @override
  void initState() {
    super.initState();
    _debouncer = SearchDebouncer(
      delay: const Duration(milliseconds: 500),
      onSearch: (query) {
        if (!mounted) return;
        ref.read(searchControllerProvider(_scope).notifier).search(query);
      },
    );
    _text.addListener(_onTextChanged);
  }

  /// 묻는 것은 0.5초를 쉰 뒤지만, 칸을 비우면(두 자 미만) 곧바로 처음 화면으로 돌아간다 — 빈 칸 아래에 옛 결과가
  /// 남거나 진행 중이던 결과가 뒤늦게 나타나지 않게.
  void _onTextChanged() {
    if (cleanSearchText(_text.text) == null) {
      _debouncer.reset();
      ref.read(searchControllerProvider(_scope).notifier).search('');
      return;
    }
    _debouncer.onChanged(_text.value);
  }

  @override
  void dispose() {
    _debouncer.dispose();
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scope = (
      shopId: ref.watch(selectedShopIdProvider) ?? 0,
      petId: widget.petId,
    );
    final state = ref.watch(searchControllerProvider(scope));
    final display = state.display;
    return Scaffold(
      key: ScreenKeys.search,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  AppSpacing.sm,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    const Expanded(
                      child: Text(
                        AppStrings.searchTitle,
                        style: AppTypography.titleKo,
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                child: AppSearchField(
                  key: SearchScreen.fieldKey,
                  controller: _text,
                  hintText: AppStrings.searchHint,
                  autofocus: true,
                ),
              ),
              if (widget.petId != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.lg,
                    AppSpacing.sm,
                    AppSpacing.lg,
                    0,
                  ),
                  child: Text(
                    widget.petName == null || widget.petName!.isEmpty
                        ? AppStrings.searchInThisPet
                        : AppStrings.searchInPet(widget.petName!),
                    style: AppTypography.caption,
                  ),
                ),
              Expanded(
                child: display == null
                    ? const _Intro()
                    : AsyncBody<SearchResult>(
                        value: display,
                        onRetry: () => ref
                            .read(searchControllerProvider(scope).notifier)
                            .retry(),
                        builder: (result) => _Results(result: result),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 처음 화면 — 무엇으로 찾을 수 있는지와 예시 둘.
class _Intro extends StatelessWidget {
  const _Intro();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.xl,
        AppSpacing.lg,
        AppSpacing.xl,
      ),
      children: [
        const Text(AppStrings.searchIntro, style: AppTypography.body),
        const SizedBox(height: AppSpacing.sm),
        Text(AppStrings.searchExampleA, style: AppTypography.caption),
        Text(AppStrings.searchExampleB, style: AppTypography.caption),
      ],
    );
  }
}

class _Results extends ConsumerWidget {
  const _Results({required this.result});

  final SearchResult result;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final images = ref.watch(mediaImagesProvider);
    final items = result.items;
    return ListView(
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.md,
        AppSpacing.lg,
        AppSpacing.xl,
      ),
      children: [
        if (items.isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: AppSpacing.xl),
            child: Text(
              AppStrings.searchEmpty,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
          )
        else
          Text(AppStrings.searchNearest, style: AppTypography.caption),
        for (final (index, item) in items.indexed) ...[
          _SearchRow(
            key: ValueKey('search-item-$index'),
            item: item,
            photo: item.photoUrl == null ? null : images.of(item.photoUrl!),
          ),
          const Divider(height: 1, thickness: 1, color: AppColors.line),
        ],
      ],
    );
  }
}

/// 결과 한 줄 — 사진, 이름, 종류와 날짜, 걸린 문장 두 줄. 갈 곳이 없는 줄은 눌리지 않고 화살표가 없다.
class _SearchRow extends StatelessWidget {
  const _SearchRow({super.key, required this.item, required this.photo});

  final SearchItem item;
  final ImageProvider? photo;

  static const _photoSize = 40.0;

  @override
  Widget build(BuildContext context) {
    final destination = destinationOf(item);
    final title = titleOf(item);
    final meta = metaLine(item);
    return Pressable(
      semanticLabel: AppStrings.searchRowLabel(title, meta, item.snippet),
      // 돌아와도 다시 묻지 않는다 — 검색어와 결과를 그대로 둔다.
      onTap: destination == null ? null : () => context.push(destination),
      // 이름표가 줄의 글을 다 읽는다 — 안의 글자가 한 번 더 읽히지 않게 뺀다.
      child: ExcludeSemantics(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 아이가 없는 줄(보호자 메모·보호자만의 방문)은 사진 칸 없이 자리만 맞춘다.
              if (item.petId != null)
                AppPhotoTile(image: photo, size: _photoSize)
              else
                const SizedBox(width: _photoSize, height: _photoSize),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: AppTypography.body,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(meta, style: AppTypography.caption),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      item.snippet,
                      style: AppTypography.body.copyWith(
                        color: AppColors.secondary,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              if (destination != null)
                const Padding(
                  padding: EdgeInsets.only(top: AppSpacing.xs),
                  child: Icon(
                    Icons.chevron_right,
                    size: 18,
                    color: AppColors.secondary,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
