import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../state/sales_paged.dart';

/// 매출 탭에서 이어지는 목록 화면의 뼈대 — 머리(뒤로 + 제목)와 쪽으로 이어 읽는 줄들.
///
/// 빈 목록은 안내 한 줄, 다음 쪽이 실패하면 보인 줄은 그대로 두고 [다시 시도]를 보인다.
class SalesPagedScaffold<T> extends StatelessWidget {
  const SalesPagedScaffold({
    super.key,
    required this.screenKey,
    required this.title,
    required this.value,
    required this.emptyText,
    required this.onRetry,
    required this.onRefresh,
    required this.onLoadMore,
    required this.row,
  });

  final Key screenKey;
  final String title;
  final AsyncValue<SalesPagedState<T>> value;
  final String emptyText;
  final VoidCallback onRetry;
  final Future<void> Function() onRefresh;
  final VoidCallback onLoadMore;
  final Widget Function(T item) row;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: screenKey,
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
                    Expanded(
                      child: Text(
                        title,
                        style: AppTypography.titleKo,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<SalesPagedState<T>>(
                  value: value,
                  onRetry: onRetry,
                  onRefresh: onRefresh,
                  builder: _list,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _list(SalesPagedState<T> state) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.xl),
      children: [
        if (state.items.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xl),
            child: Text(emptyText, style: AppTypography.body, textAlign: TextAlign.center),
          ),
        for (final item in state.items) ...[
          row(item),
          const Divider(height: 1, thickness: 1, color: AppColors.line),
        ],
        const SizedBox(height: AppSpacing.md),
        if (state.loadingMore)
          const Center(child: CircularProgressIndicator())
        else if (state.loadMoreError != null)
          AppErrorRetry.row(message: loadMessageFor(state.loadMoreError!), onRetry: onLoadMore)
        else if (state.hasMore)
          AppButton(label: AppStrings.loadMore, onPressed: onLoadMore),
      ],
    );
  }
}

/// 목록의 한 줄 — 사진, 큰 글자와 작은 글자, 오른쪽 글자, 화살표.
class SalesListRow extends StatelessWidget {
  const SalesListRow({
    super.key,
    required this.semanticLabel,
    required this.onTap,
    required this.photo,
    required this.showPhoto,
    required this.title,
    this.subtitle,
    this.trailing,
  });

  final String semanticLabel;
  final VoidCallback onTap;

  /// 사진. 없으면 빈 사진 칸이다.
  final ImageProvider? photo;

  /// 아이를 보일 수 없는 줄은 사진 칸 없이 자리만 맞춘다.
  final bool showPhoto;
  final String title;
  final String? subtitle;
  final String? trailing;

  static const _photoSize = 34.0;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: semanticLabel,
      onTap: onTap,
      child: ExcludeSemantics(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
          child: Row(
            children: [
              if (showPhoto)
                AppPhotoTile(image: photo, size: _photoSize)
              else
                const SizedBox(width: _photoSize, height: _photoSize),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppTypography.body, maxLines: 1, overflow: TextOverflow.ellipsis),
                    if (subtitle != null) Text(subtitle!, style: AppTypography.caption),
                  ],
                ),
              ),
              if (trailing != null) ...[
                const SizedBox(width: AppSpacing.sm),
                Text(trailing!, style: AppTypography.body),
              ],
              const Icon(Icons.chevron_right, size: 18, color: AppColors.secondary),
            ],
          ),
        ),
      ),
    );
  }
}
