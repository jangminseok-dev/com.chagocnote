import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/proxy/clipboard.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_search_field.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/api/customer_models.dart';
import '../../customer/state/customer_input.dart';
import '../../customer/state/customer_list_controller.dart';
import '../../customer/state/customer_providers.dart';
import '../../../core/time/search_debouncer.dart';
import '../../../core/time/today_provider.dart';
import '../api/visit_models.dart';
import '../state/check_rules.dart';
import '../state/visit_commands.dart';
import '../state/visit_prefill.dart';
import '../state/visit_providers.dart';
import 'visit_checks_block.dart';
import 'visit_form.dart';
import 'visit_labels.dart';

/// 예약 등록 — ① 고객 찾기(고객 탭의 검색 그대로) → ② 날짜·시간·반려동물·
/// 메뉴(설계 9.1). 달력에서 날짜를 고른 뒤 열면 ②의 날짜가 그 날이다.
/// [draft](완료하고 다음 예약 잡기)로 열면 ①을 건너뛰고 ②를 채워 연다.
///
/// 저장하면 저장한 날짜를 돌려주며 닫는다 — 부른 화면이 그 날로 옮겨 간다.
class RegisterVisitScreen extends ConsumerStatefulWidget {
  const RegisterVisitScreen({super.key, this.date, this.draft, this.prefill});

  final DateTime? date;
  final NextVisitDraft? draft;

  /// 카톡 초안(③-A3). 보호자가 있으면 ①을 건너뛴다.
  final VisitPrefill? prefill;

  @override
  ConsumerState<RegisterVisitScreen> createState() =>
      _RegisterVisitScreenState();
}

class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
  late int? _customerId =
      widget.draft?.customerId ?? widget.prefill?.customerId;
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  void _backToSearch() => setState(() {
    _customerId = null;
    _errorText = null;
  });

  Future<void> _save(VisitFormValue value, {bool walkIn = false}) async {
    final shopId = _shopId;
    final customerId = _customerId;
    if (shopId == null || customerId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final saved = await ref
          .read(visitCommandsProvider)
          .register(
            shopId,
            VisitRequest(
              customerId: customerId,
              petIds: value.petIds,
              startsAt: value.startsAt,
              durationMinutes: value.durationMinutes,
              menuIds: value.menuIds,
              memo: value.memo,
              walkIn: walkIn,
            ),
          );
      // 서버가 저장한 날짜를 돌려준다 — [지금 시작]은 보던 날과 다를 수 있다.
      if (mounted) context.pop(saved.visits.first.startsAt.day);
    } on ApiException catch (e) {
      // 저장을 두 번 눌렀거나(이미 저장됐다), 다음 예약의 한 아이가 그 시각에
      // 이미 예약돼 있다(아무것도 저장되지 않았다). 둘 다 그날 목록을 보면
      // 알 수 있으니 알리고 그날로 닫는다(결정 기록 006, ③-A3).
      if (e.code == 'VISIT_DUPLICATE') {
        if (mounted) {
          AppSnackBar.show(context, AppStrings.duplicateVisitNotice);
          final today = ref.read(todayProvider);
          context.pop(
            walkIn ? DateTime(today.year, today.month, today.day) : value.date,
          );
        }
        return;
      }
      _fail(e);
    } catch (e) {
      _fail(e);
    }
  }

  void _fail(Object error) {
    if (!mounted) return;
    setState(() {
      _busy = false;
      _errorText = messageFor(error);
    });
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final customerId = _customerId;
    final onSearch = customerId == null;
    // 초안으로 열었으면 ①이 없다 — 뒤로 가면 닫는다.
    final backToSearch = !onSearch && !_skippedSearch;
    return PopScope(
      canPop: !backToSearch,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _backToSearch();
      },
      child: Scaffold(
        key: ScreenKeys.registerVisit,
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
                      AppBackButton(onTap: backToSearch ? _backToSearch : null),
                      const SizedBox(width: AppSpacing.sm),
                      Text(
                        onSearch
                            ? AppStrings.reserveWhoTitle
                            : AppStrings.reserveWhenTitle,
                        style: AppTypography.titleKo,
                      ),
                      const Spacer(),
                      Text(
                        AppStrings.stepOf(onSearch ? 1 : 2, 2),
                        style: AppTypography.caption,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: shopId == null
                      ? const SizedBox.shrink()
                      : onSearch
                      ? _CustomerSearch(
                          shopId: shopId,
                          onPick: (id) => setState(() => _customerId = id),
                        )
                      : _formFor(shopId, customerId),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// 다음 예약 초안이나 보호자가 있는 카톡 초안으로 열었으면 ①이 없었다.
  bool get _skippedSearch =>
      widget.draft != null || widget.prefill?.customerId != null;

  Widget _formFor(int shopId, int customerId) {
    final draft = widget.draft;
    final prefill = widget.prefill;
    final initial = draft != null
        ? VisitFormInitial(
            date: draft.startsAt.day,
            petIds: {...draft.petIds},
            ownerOnly: draft.petIds.isEmpty,
            at: hhmm(draft.startsAt.wall),
            durationMinutes: draft.durationMinutes,
            menus: draft.menus,
            prefilled: true,
          )
        : prefill != null
        ? VisitFormInitial(
            date: prefill.date ?? ref.read(todayProvider),
            petIds: prefill.petIds,
            at: prefill.at,
            menus: prefill.menus,
            // 메뉴가 글에 있었으면 "지난번처럼"으로 덮어쓰지 않는다.
            prefilled: prefill.menus.isNotEmpty,
          )
        : VisitFormInitial(date: widget.date ?? ref.read(todayProvider));
    return VisitForm(
      // 보호자를 바꾸면 폼을 새로 만든다 — 앞 보호자의 아이 선택이 남지 않게.
      key: ValueKey(customerId),
      shopId: shopId,
      customerId: customerId,
      initial: initial,
      header: _OwnerCard(
        shopId: shopId,
        customerId: customerId,
        onChange: _skippedSearch ? null : _backToSearch,
      ),
      submitLabel: (date, at) =>
          AppStrings.saveReservation('${dayLabel(date)} $at'),
      onSubmit: _save,
      onWalkIn: (value) => _save(value, walkIn: true),
      busy: _busy,
      errorText: _errorText,
      aboveSubmit: (petIds, date) => _PreviewChecks(
        checksKey: (
          shopId: shopId,
          customerId: customerId,
          petIds: petIdsKey(petIds),
          date: date,
        ),
      ),
    );
  }
}

/// ②의 "확인할 것"(③-B) — 고른 보호자·아이·날짜로 서버에 묻는다. 읽는 중이거나 읽지 못하면
/// 아무것도 그리지 않는다 — 예약을 막지 않는다. 동의를 받았다고 적는 것은 방문 상세에서 한다.
class _PreviewChecks extends ConsumerWidget {
  const _PreviewChecks({required this.checksKey});

  final ChecksKey checksKey;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(visitChecksProvider(checksKey));
    // 다시 읽기가 실패하면 앞서 읽은 값이 남아 있다 — 낡은 묶음을 보이지 않는다.
    final preview = async.hasError ? null : async.value;
    if (preview == null || preview.isEmpty) return const SizedBox.shrink();
    final pets = ref
        .watch(
          customerDetailProvider((
            shopId: checksKey.shopId,
            customerId: checksKey.customerId,
          )),
        )
        .value
        ?.pets;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: VisitChecksBlock(
        sections: checkSections(preview, {
          for (final p in pets ?? const <Pet>[]) p.petId: p.name,
        }),
      ),
    );
  }
}

/// ②의 보호자 카드 — 이름·번호 뒷자리와 [바꾸기].
class _OwnerCard extends ConsumerWidget {
  const _OwnerCard({
    required this.shopId,
    required this.customerId,
    required this.onChange,
  });

  final int shopId;
  final int customerId;
  final VoidCallback? onChange;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final customer = ref
        .watch(customerDetailProvider((shopId: shopId, customerId: customerId)))
        .value
        ?.customer;
    return AppCard(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              customer == null
                  ? ''
                  : '${customer.name} · ${maskedTail(customer.phone)}',
              style: AppTypography.bodyStrong,
            ),
          ),
          if (onChange != null)
            AppButton(label: AppStrings.changeCustomer, onPressed: onChange),
        ],
      ),
    );
  }
}

/// ① 고객 찾기 — 고객 탭과 같은 검색(뒷자리·이름·반려동물, 초성)과 목록.
class _CustomerSearch extends ConsumerStatefulWidget {
  const _CustomerSearch({required this.shopId, required this.onPick});

  final int shopId;
  final ValueChanged<int> onPick;

  @override
  ConsumerState<_CustomerSearch> createState() => _CustomerSearchState();
}

class _CustomerSearchState extends ConsumerState<_CustomerSearch> {
  final _search = TextEditingController();
  late final _debouncer = SearchDebouncer(
    onSearch: (q) => setState(() => _q = q),
  );
  String _q = '';
  String? _pasteNote;

  @override
  void initState() {
    super.initState();
    _search.addListener(() => _debouncer.onChanged(_search.value));
  }

  @override
  void dispose() {
    _debouncer.dispose();
    _search.dispose();
    super.dispose();
  }

  /// 클립보드의 카톡 글로 초안 화면을 연다(③-A3). 초안에서 예약을 저장하고
  /// 돌아오면 ①도 그 날짜로 닫힌다 — 홈이 그날을 고른다.
  Future<void> _pasteFromKakao(BuildContext context) async {
    final data = await ref.read(clipboardProvider).readText();
    var text = data?.trim() ?? '';
    if (!context.mounted) return;
    if (text.isEmpty) {
      setState(() => _pasteNote = AppStrings.clipboardEmpty);
      return;
    }
    if (text.length > 1000) text = text.substring(0, 1000);
    setState(() => _pasteNote = null);
    final saved = await context.push<DateTime>('/visits/draft', extra: text);
    if (saved != null && context.mounted) context.pop(saved);
  }

  /// 새 고객을 등록하고 돌아오면 그 고객으로 ②에 바로 간다.
  Future<void> _registerNew(BuildContext context) async {
    final customerId = await context.push<int>('/customers/new?pick=1');
    if (customerId != null && mounted) widget.onPick(customerId);
  }

  @override
  Widget build(BuildContext context) {
    final query = (
      shopId: widget.shopId,
      q: _q,
      sort: 'recent',
      includePassed: false,
    );
    final list = ref.watch(customerListControllerProvider(query));
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            0,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Row(
            children: [
              AppButton(
                label: AppStrings.pasteFromKakao,
                icon: Icons.content_paste,
                onPressed: () => _pasteFromKakao(context),
              ),
              if (_pasteNote != null) ...[
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(_pasteNote!, style: AppTypography.caption),
                ),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: AppSearchField(
            controller: _search,
            hintText: AppStrings.customerSearchHint,
            autofocus: true,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Expanded(
          child: AsyncBody<CustomerListState>(
            value: list,
            onRetry: () =>
                ref.invalidate(customerListControllerProvider(query)),
            builder: (state) => ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.lg,
                0,
                AppSpacing.lg,
                AppSpacing.xxl,
              ),
              children: [
                for (final card in state.items)
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                    child: _FamilyRow(
                      card: card,
                      onTap: () => widget.onPick(card.customerId),
                    ),
                  ),
                const SizedBox(height: AppSpacing.md),
                Center(
                  child: Text(
                    AppStrings.reserveNoCustomer,
                    style: AppTypography.caption,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Center(
                  child: AppButton(
                    label: AppStrings.registerNewCustomer,
                    onPressed: () => _registerNew(context),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _FamilyRow extends StatelessWidget {
  const _FamilyRow({required this.card, required this.onTap});

  final FamilyCard card;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final names = card.pets.map((p) => p.name).join(' · ');
    return Pressable(
      semanticLabel: '${card.name} $names',
      onTap: onTap,
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        child: SizedBox(
          width: double.infinity,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(names, style: AppTypography.bodyStrong),
              Text(
                '${card.name} · ${card.phoneMasked}',
                style: AppTypography.caption,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
