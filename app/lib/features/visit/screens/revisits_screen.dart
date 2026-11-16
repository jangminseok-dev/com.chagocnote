import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/proxy/media_images.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/today_provider.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_error_retry.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_segment.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/revisit_models.dart';
import '../api/visit_models.dart';
import '../state/revisit_list.dart';
import '../state/revisit_rules.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'revisit_nudge_sheet.dart';
import 'settings/revisit_sheets.dart';
import 'visit_actions.dart';

/// 다시 올 때가 된 아이(⑬ 설계 3.3) — [지남][곧] 두 묶음, 줄마다 [예약]·[안내]. 돈이 없는 목록이라 직원도 본다.
/// 줄의 이름을 누르면 반려동물 상세, 주기 글을 누르면 그 아이의 주기 시트. 다녀오면 다시 읽는다.
class RevisitsScreen extends ConsumerStatefulWidget {
  const RevisitsScreen({super.key, this.initial = RevisitBucket.due});

  final RevisitBucket initial;

  @override
  ConsumerState<RevisitsScreen> createState() => _RevisitsScreenState();
}

class _RevisitsScreenState extends ConsumerState<RevisitsScreen> {
  late RevisitBucket _bucket = widget.initial;
  bool _busy = false;

  RevisitsKey _key(int shopId) => (shopId: shopId, bucket: _bucket);

  /// 목록(불러온 만큼)과 두 묶음의 수를 다시 읽는다 — 예약을 잡았거나 안내했거나 주기를 바꿨을 수 있다.
  Future<void> _refresh(int shopId) async {
    ref.invalidate(revisitCountsProvider(shopId));
    await ref.read(revisitsProvider(_key(shopId)).notifier).reload();
  }

  Future<void> _guard(Future<void> Function() action) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// [예약] — 마지막 완료 방문의 다음 예약 초안을 내일 이후로 옮겨 예약 화면을 채워 연다.
  Future<void> _book(int shopId, RevisitItem item) => _guard(() async {
    final today = ref.read(todayProvider);
    final NextVisitDraft draft;
    try {
      draft = await ref.read(visitCommandsProvider).nextDraft(shopId, item.lastVisitId);
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
      return;
    }
    if (!mounted) return;
    await context.push('/visits/new', extra: draftForBooking(draft, today));
    if (mounted) await _refresh(shopId);
  });

  Future<void> _nudge(int shopId, RevisitItem item) => _guard(() async {
    final nudged = await showRevisitNudgeSheet(context, item);
    if (nudged && mounted) await _refresh(shopId);
  });

  Future<void> _cycle(int shopId, RevisitItem item) => _guard(() async {
    final saved = await openPetCycleSheet(context, ref, shopId: shopId, petId: item.petId);
    if (saved && mounted) await _refresh(shopId);
  });

  Future<void> _openPet(int shopId, RevisitItem item) async {
    await context.push('/pets/${item.petId}');
    if (mounted) await _refresh(shopId);
  }

  /// '곧'으로 치는 날 수(사장만).
  Future<void> _changeSoonDays(int shopId, int current) => _guard(() async {
    final days = await pickSoonDays(context, current);
    if (days == null || days == current || !mounted) return;
    try {
      await ref.read(visitCommandsProvider).updateRevisitSettings(shopId, {'revisit_soon_days': days});
    } catch (e) {
      if (mounted) AppSnackBar.show(context, messageFor(e));
    }
  });

  @override
  Widget build(BuildContext context) {
    final shopId = ref.watch(selectedShopIdProvider);
    if (shopId == null) return const Scaffold(key: ScreenKeys.revisits);
    final counts = ref.watch(revisitCountsProvider(shopId)).value;
    final provider = revisitsProvider(_key(shopId));
    return Scaffold(
      key: ScreenKeys.revisits,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.sm),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    const Expanded(child: Text(AppStrings.revisitsTitle, style: AppTypography.titleKo)),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                child: AppSegment(
                  labels: [AppStrings.revisitsDueTab(counts?.due), AppStrings.revisitsSoonTab(counts?.soon)],
                  currentIndex: _bucket == RevisitBucket.due ? 0 : 1,
                  onChanged: (i) => setState(() => _bucket = i == 0 ? RevisitBucket.due : RevisitBucket.soon),
                ),
              ),
              if (_bucket == RevisitBucket.soon) _SoonHeader(shopId: shopId, onChange: _changeSoonDays),
              Expanded(
                child: AsyncBody<RevisitListState>(
                  value: ref.watch(provider),
                  onRetry: () => ref.invalidate(provider),
                  onRefresh: () async {
                    ref.invalidate(revisitCountsProvider(shopId));
                    final _ = await ref.refresh(provider.future);
                  },
                  builder: (state) => _list(shopId, state),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _list(int shopId, RevisitListState state) {
    final images = ref.watch(mediaImagesProvider);
    final today = ref.watch(todayProvider);
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.xl),
      children: [
        if (state.items.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xl),
            child: Text(
              _bucket == RevisitBucket.due ? AppStrings.revisitsDueEmpty : AppStrings.revisitsSoonEmpty,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
          ),
        for (final item in state.items) ...[
          _Row(
            item: item,
            line: revisitRowLine(item, today),
            nudged: item.nudgedOn == null ? null : AppStrings.revisitNudgedOn(item.nudgedOn!, today),
            photo: item.photoUrl == null ? null : images.of(item.photoUrl!),
            busy: _busy,
            onOpen: () => _openPet(shopId, item),
            onCycle: () => _cycle(shopId, item),
            onBook: () => _book(shopId, item),
            onNudge: () => _nudge(shopId, item),
          ),
          const Divider(height: 1, thickness: 1, color: AppColors.line),
        ],
        const SizedBox(height: AppSpacing.md),
        if (state.loadingMore)
          const Center(child: CircularProgressIndicator())
        else if (state.loadMoreError != null)
          AppErrorRetry.row(
            message: loadMessageFor(state.loadMoreError!),
            onRetry: () => ref.read(revisitsProvider(_key(shopId)).notifier).loadMore(),
          )
        else if (state.hasMore)
          AppButton(
            label: AppStrings.loadMore,
            onPressed: () => ref.read(revisitsProvider(_key(shopId)).notifier).loadMore(),
          ),
      ],
    );
  }
}

/// '곧' 묶음 머리 — `7일 안`(사장이면 ` · 바꾸기`).
class _SoonHeader extends ConsumerWidget {
  const _SoonHeader({required this.shopId, required this.onChange});

  final int shopId;
  final Future<void> Function(int shopId, int current) onChange;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOwner = ref.watch(isOwnerProvider);
    // 직원은 매장의 값을 읽지 못할 수도 있다(읽기는 멤버지만) — 못 읽으면 머리가 없다.
    final settings = ref.watch(revisitSettingsProvider(shopId)).value;
    if (settings == null) return const SizedBox(height: AppSpacing.sm);
    final days = settings.revisitSoonDays;
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, 0),
      child: Row(
        children: [
          Text(AppStrings.revisitSoonHeader(days), style: AppTypography.caption),
          if (isOwner) ...[
            const Text(' · ', style: AppTypography.caption),
            Pressable(
              semanticLabel: AppStrings.revisitChange,
              onTap: () => onChange(shopId, days),
              child: Text(
                AppStrings.revisitChange,
                style: AppTypography.caption.copyWith(decoration: TextDecoration.underline),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// 한 줄 — 사진·이름(누르면 반려동물 상세), 주기 글(누르면 주기 시트), 안내한 날, [예약]·[안내].
class _Row extends StatelessWidget {
  const _Row({
    required this.item,
    required this.line,
    required this.nudged,
    required this.photo,
    required this.busy,
    required this.onOpen,
    required this.onCycle,
    required this.onBook,
    required this.onNudge,
  });

  final RevisitItem item;
  final String line;
  final String? nudged;
  final ImageProvider? photo;
  final bool busy;
  final VoidCallback onOpen;
  final VoidCallback onCycle;
  final VoidCallback onBook;
  final VoidCallback onNudge;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Row(
        children: [
          Pressable(
            semanticLabel: item.petName,
            onTap: onOpen,
            child: AppPhotoTile(image: photo, size: 40),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Pressable(
                  semanticLabel: item.petName,
                  onTap: onOpen,
                  child: Text(item.petName, style: AppTypography.bodyStrong, maxLines: 1, overflow: TextOverflow.ellipsis),
                ),
                Pressable(
                  semanticLabel: '${AppStrings.cycleLabel} $line',
                  onTap: busy ? null : onCycle,
                  child: Text(line, style: AppTypography.caption),
                ),
                if (nudged != null) Text(nudged!, style: AppTypography.caption),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          AppButton(label: AppStrings.revisitBook, onPressed: busy ? null : onBook),
          const SizedBox(width: AppSpacing.xs),
          AppButton(label: AppStrings.revisitNudge, onPressed: busy ? null : onNudge),
        ],
      ),
    );
  }
}
