import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/state/customer_input.dart';
import '../api/visit_models.dart';
import '../state/visit_prefill.dart';
import '../state/visit_providers.dart';
import 'visit_labels.dart';

/// 카톡 글을 해석한 예약 초안을 확인하는 화면(설계 7절, ③-A3 A안). 붙여넣기와
/// 공유 받기가 같은 화면으로 온다.
///
/// 받은 글, 보호자 후보(하나면 고른 상태, 여럿이면 골라야 한다), 날짜·시작·
/// 메뉴 줄(짐작한 칸에 "짐작" 표시)을 보이고, [예약 이어서]가 기존 예약 ②를
/// 미리 채워 연다. 후보가 없으면 [고객 찾기]로 ①에 간 뒤 ②가 채워진다.
/// 서버도 이 화면도 글을 저장하지 않는다 — 저장은 사람이 확인한 뒤 ②에서.
class DraftScreen extends ConsumerStatefulWidget {
  const DraftScreen({super.key, required this.text});

  final String text;

  @override
  ConsumerState<DraftScreen> createState() => _DraftScreenState();
}

class _DraftScreenState extends ConsumerState<DraftScreen> {
  int? _pickedCustomerId;
  bool _expanded = false;
  bool _continuing = false;

  int? get _shopId => ref.read(selectedShopIdProvider);

  /// 예약 ②(보호자가 있으면 바로, 없으면 ① 뒤)를 초안으로 채워 연다. 저장한
  /// 날짜가 돌아오면 이 화면도 그 날짜로 닫힌다.
  Future<void> _continue(
    int shopId,
    VisitDraft draft,
    DraftCandidate? picked,
  ) async {
    if (_continuing) return;
    setState(() => _continuing = true);
    // 메뉴표를 아직 못 읽었으면 기다린다 — 안 그러면 글에 있던 메뉴가 빠진 채 ②가 열린다.
    List<Menu> menus;
    try {
      menus = await ref.read(
        menusProvider((shopId: shopId, includeArchived: false)).future,
      );
    } catch (_) {
      menus = const []; // 메뉴표를 못 읽으면 메뉴 없이 넘긴다 — ②에서 고른다.
    }
    if (!mounted) return;
    setState(() => _continuing = false);
    final byId = {for (final m in menus) m.menuId: m};
    final prefill = VisitPrefill(
      customerId: picked?.customerId,
      date: draft.date,
      at: draft.time,
      petIds: {...?picked?.matchedPetIds},
      menus: [
        for (final id in draft.menuIds)
          if (byId[id] case final m?) MenuBrief(menuId: id, name: m.name),
      ],
    );
    final saved = await context.push<DateTime>('/visits/new', extra: prefill);
    if (saved != null && mounted) context.pop(saved);
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final key = (shopId: shopId ?? 0, text: widget.text);
    final draft = shopId == null
        ? const AsyncValue<VisitDraft>.loading()
        : ref.watch(visitDraftProvider(key));
    return Scaffold(
      key: ScreenKeys.visitDraft,
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
                child: const Row(
                  children: [
                    AppBackButton(),
                    SizedBox(width: AppSpacing.sm),
                    Text(AppStrings.draftTitle, style: AppTypography.titleKo),
                  ],
                ),
              ),
              Expanded(
                child: draft.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(messageFor(error), style: AppTypography.body),
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: AppStrings.retry,
                          onPressed: () =>
                              ref.invalidate(visitDraftProvider(key)),
                        ),
                      ],
                    ),
                  ),
                  data: (draft) => _body(shopId!, draft),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(int shopId, VisitDraft draft) {
    final candidates = draft.candidates;
    // 후보가 하나면 고른 상태로 시작한다. 여럿이면 골라야 한다.
    final pickedId =
        _pickedCustomerId ??
        (candidates.length == 1 ? candidates.single.customerId : null);
    final picked = candidates
        .where((c) => c.customerId == pickedId)
        .firstOrNull;
    final menus = ref
        .watch(menusProvider((shopId: shopId, includeArchived: false)))
        .value;
    final menuNames = menus == null
        ? null
        : [
            for (final id in draft.menuIds)
              for (final m in menus)
                if (m.menuId == id) m.name,
          ];
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        0,
        AppSpacing.lg,
        AppSpacing.xxl,
      ),
      children: [
        const Text(AppStrings.draftReceivedText, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xs),
        Pressable(
          semanticLabel: AppStrings.draftReceivedText,
          onTap: () => setState(() => _expanded = !_expanded),
          child: AppCard(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: SizedBox(
              width: double.infinity,
              child: ExcludeSemantics(
                child: Text(
                  widget.text,
                  style: AppTypography.body,
                  maxLines: _expanded ? null : 3,
                  overflow: _expanded ? null : TextOverflow.ellipsis,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Row(
          children: [
            const Text(
              AppStrings.draftOwnerSection,
              style: AppTypography.caption,
            ),
            if (draft.guessed.who && candidates.isNotEmpty) ...[
              const SizedBox(width: AppSpacing.sm),
              const AppChip(label: AppStrings.draftGuessed),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        if (candidates.isEmpty)
          const Text(AppStrings.draftNoCandidates, style: AppTypography.body)
        else
          for (final c in candidates)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: _CandidateRow(
                candidate: c,
                selected: c.customerId == pickedId,
                onTap: () => setState(() => _pickedCustomerId = c.customerId),
              ),
            ),
        const SizedBox(height: AppSpacing.md),
        _Line(
          label: AppStrings.visitDateLabel,
          value: draft.date == null ? null : dayLabel(draft.date!),
          guessed: draft.guessed.date,
        ),
        _Line(
          label: AppStrings.visitTimeLabel,
          value: draft.time,
          guessed: draft.guessed.time,
        ),
        _Line(
          label: AppStrings.menuLabel,
          value: menuNames == null || menuNames.isEmpty
              ? null
              : menuNames.join(' · '),
          guessed: draft.guessed.menu,
        ),
        const SizedBox(height: AppSpacing.lg),
        const Text(AppStrings.draftHint, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.sm),
        if (candidates.isEmpty)
          AppButton(
            label: AppStrings.draftFindCustomer,
            filled: true,
            busy: _continuing,
            onPressed: () => _continue(shopId, draft, null),
          )
        else
          AppButton(
            label: AppStrings.draftContinue,
            filled: true,
            busy: _continuing,
            onPressed: picked == null
                ? null
                : () => _continue(shopId, draft, picked),
          ),
      ],
    );
  }
}

/// 보호자 후보 한 줄 — 이름 · 번호 뒷자리, 아이 이름들. 고르면 체크.
class _CandidateRow extends StatelessWidget {
  const _CandidateRow({
    required this.candidate,
    required this.selected,
    required this.onTap,
  });

  final DraftCandidate candidate;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = candidate;
    final pets = c.pets.map((p) => p.name).join(' · ');
    return Pressable(
      semanticLabel: '${c.name} $pets',
      selected: selected,
      onTap: onTap,
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        child: ExcludeSemantics(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${c.name} · ${maskedTail(c.phoneMasked)}',
                      style: AppTypography.bodyStrong,
                    ),
                    if (pets.isNotEmpty)
                      Text(pets, style: AppTypography.caption),
                  ],
                ),
              ),
              if (selected) const Icon(Icons.check, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

/// 날짜·시작·메뉴 한 줄. 값이 없으면 "—", 짐작이면 칩.
class _Line extends StatelessWidget {
  const _Line({
    required this.label,
    required this.value,
    required this.guessed,
  });

  final String label;
  final String? value;
  final bool guessed;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        children: [
          SizedBox(width: 48, child: Text(label, style: AppTypography.caption)),
          Expanded(
            child: Text(
              value ?? AppStrings.draftEmptyValue,
              style: AppTypography.body,
            ),
          ),
          if (value != null && guessed)
            const AppChip(label: AppStrings.draftGuessed),
        ],
      ),
    );
  }
}
