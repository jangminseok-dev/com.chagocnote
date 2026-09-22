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
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_segment.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_input.dart';
import '../state/customer_providers.dart';
import 'customer_labels.dart';

/// 반려동물 한 마리 화면 — 큰 사진 자리, 이름·요약, 탭 [기본 / 질병 / 보호자],
/// 같은 보호자의 다른 아이, 수정·무지개다리·삭제(설계 8.1).
class PetDetailScreen extends ConsumerStatefulWidget {
  const PetDetailScreen({super.key, required this.petId});

  final int petId;

  @override
  ConsumerState<PetDetailScreen> createState() => _PetDetailScreenState();
}

class _PetDetailScreenState extends ConsumerState<PetDetailScreen> {
  int _tab = 0;
  bool _busy = false;
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  Future<void> _openActions(PetDetail detail) async {
    final action = await AppSheet.show<String>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _SheetAction(
            label: detail.pet.passedAway
                ? AppStrings.unmarkPassedAway
                : AppStrings.markPassedAway,
            onTap: () => Navigator.of(context).pop('passed'),
          ),
          _SheetAction(
            label: AppStrings.deletePet,
            onTap: () => Navigator.of(context).pop('delete'),
          ),
        ],
      ),
    );
    if (action == null || !mounted) return;
    if (action == 'passed') {
      await _togglePassedAway(detail.pet);
    } else {
      await _delete();
    }
  }

  Future<void> _togglePassedAway(Pet pet) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final commands = ref.read(customerCommandsProvider);
    if (pet.passedAway) {
      await _run(() => commands.unmarkPassedAway(shopId, pet.petId));
      return;
    }
    final confirmed = await _confirm(
      AppStrings.markPassedAwayConfirm,
      AppStrings.markPassedAway,
    );
    if (confirmed != true || !mounted) return;
    await _run(() => commands.markPassedAway(shopId, pet.petId));
  }

  Future<void> _delete() async {
    final shopId = _shopId;
    if (shopId == null) return;
    final confirmed = await _confirm(
      AppStrings.deletePetConfirm,
      AppStrings.delete,
    );
    if (confirmed != true || !mounted) return;
    final deleted = await _run(
      () => ref.read(customerCommandsProvider).deletePet(shopId, widget.petId),
    );
    if (deleted && mounted) {
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/home');
      }
    }
  }

  Future<bool?> _confirm(String message, String confirmLabel) {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(message, style: AppTypography.body, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: confirmLabel,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
  }

  /// 쓰기 하나를 돌린다. 도는 동안 다른 쓰기를 막고(연타 방지), 실패하면
  /// 문구를 보인다. 성공하면 true.
  Future<bool> _run(Future<void> Function() action) async {
    if (_busy) return false;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action();
      if (mounted) setState(() => _busy = false);
      return true;
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _errorText = messageFor(e);
        });
      }
      return false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final detail = shopId == null
        ? const AsyncValue<PetDetail>.loading()
        : ref.watch(petDetailProvider((shopId: shopId, petId: widget.petId)));
    final data = detail.value;

    return Scaffold(
      key: ScreenKeys.petDetail,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 머리는 로딩·오류 상태에서도 보인다 — 오류에 갇혀도 뒤로 갈 수 있다.
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.sm,
                  0,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const Spacer(),
                    if (data != null) ...[
                      AppButton(
                        label: AppStrings.edit,
                        onPressed: _busy
                            ? null
                            : () => context.push('/pets/${widget.petId}/edit'),
                      ),
                      Pressable(
                        semanticLabel: AppStrings.more,
                        onTap: _busy ? null : () => _openActions(data),
                        child: const Icon(Icons.more_horiz),
                      ),
                    ],
                  ],
                ),
              ),
              if (_errorText != null)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                  ),
                  child: Text(_errorText!, style: AppTypography.caption),
                ),
              Expanded(
                child: detail.when(
                  data: (detail) => _DetailBody(
                    detail: detail,
                    tab: _tab,
                    onTab: (i) => setState(() => _tab = i),
                  ),
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
                          onPressed: () => ref.invalidate(
                            petDetailProvider((
                              shopId: shopId!,
                              petId: widget.petId,
                            )),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({
    required this.detail,
    required this.tab,
    required this.onTab,
  });

  final PetDetail detail;
  final int tab;
  final ValueChanged<int> onTab;

  @override
  Widget build(BuildContext context) {
    final pet = detail.pet;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        // 사진은 ④에서 붙인다 — 지금은 회색 자리.
        const Center(child: AppPhotoTile(image: null, size: 160)),
        const SizedBox(height: AppSpacing.lg),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.xs,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(pet.name, style: AppTypography.titleKo),
            if (pet.hasConditions)
              AppChip(label: AppStrings.conditionCount(pet.conditions.length)),
            if (pet.passedAway)
              const AppChip(label: AppStrings.passedAwayBadge),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(petSummaryLine(pet), style: AppTypography.caption),
        const SizedBox(height: AppSpacing.lg),
        AppSegment(
          labels: const [
            AppStrings.petTabBasic,
            AppStrings.petTabConditions,
            AppStrings.petTabOwner,
          ],
          currentIndex: tab,
          onChanged: onTab,
        ),
        const SizedBox(height: AppSpacing.md),
        switch (tab) {
          0 => _BasicTab(pet: pet),
          1 => _ConditionsTab(pet: pet),
          _ => _OwnerTab(customerId: detail.owner.customerId),
        },
        if (detail.siblings.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          _Siblings(siblings: detail.siblings),
        ],
      ],
    );
  }
}

/// 이름표 + 값 한 줄 카드.
class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: SizedBox(
        width: double.infinity,
        child: AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: AppTypography.caption),
              const SizedBox(height: AppSpacing.xs),
              Text(value, style: AppTypography.body),
            ],
          ),
        ),
      ),
    );
  }
}

class _BasicTab extends StatelessWidget {
  const _BasicTab({required this.pet});

  final Pet pet;

  @override
  Widget build(BuildContext context) {
    final birth = pet.birthDate != null
        ? (AppStrings.birthDateLabel, formatDate(pet.birthDate!))
        : pet.birthYear != null
        ? (AppStrings.birthYearLabel, AppStrings.birthYearText(pet.birthYear!))
        : (AppStrings.birthDateLabel, AppStrings.ageUnknown);
    return Column(
      children: [
        _InfoCard(label: birth.$1, value: birth.$2),
        _InfoCard(
          label: AppStrings.weightLabel,
          value: formatWeight(pet.weightKg),
        ),
        _InfoCard(
          label: AppStrings.petMemoLabel,
          value: pet.memo ?? AppStrings.none,
        ),
      ],
    );
  }
}

class _ConditionsTab extends StatelessWidget {
  const _ConditionsTab({required this.pet});

  final Pet pet;

  @override
  Widget build(BuildContext context) {
    if (pet.conditions.isEmpty) {
      return const _InfoCard(
        label: AppStrings.petTabConditions,
        value: AppStrings.noKnownConditionsConfirmed,
      );
    }
    return Column(
      children: [
        for (final c in pet.conditions)
          _InfoCard(label: c.displayLabel, value: c.note ?? AppStrings.none),
      ],
    );
  }
}

/// 보호자 탭. 전체 번호는 고객 상세 조회에서만 받는다(설계 8.2).
class _OwnerTab extends ConsumerWidget {
  const _OwnerTab({required this.customerId});

  final int customerId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider).value;
    final shopId = session is SignedIn ? session.selectedShopId : null;
    if (shopId == null) return const SizedBox.shrink();
    final key = (shopId: shopId, customerId: customerId);
    return ref
        .watch(customerDetailProvider(key))
        .when(
          data: (detail) {
            final c = detail.customer;
            final consent = c.marketingConsent
                ? AppStrings.marketingAgreed
                : AppStrings.marketingDeclined;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _InfoCard(label: AppStrings.ownerNameLabel, value: c.name),
                _InfoCard(
                  label: AppStrings.ownerPhoneLabel,
                  value: formatPhone(c.phone),
                ),
                if (c.phoneAlt != null)
                  _InfoCard(
                    label: AppStrings.ownerPhoneAltLabel,
                    value: formatPhone(c.phoneAlt!),
                  ),
                _InfoCard(
                  label: AppStrings.marketingConsentLabel,
                  value:
                      '$consent · ${formatDate(c.marketingConsentChangedAt)}',
                ),
                _InfoCard(
                  label: AppStrings.customerMemoLabel,
                  value: c.memo ?? AppStrings.none,
                ),
                const SizedBox(height: AppSpacing.sm),
                Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
                  children: [
                    AppButton(
                      label: AppStrings.editOwner,
                      onPressed: () =>
                          context.push('/customers/$customerId/edit'),
                    ),
                    AppButton(
                      label: AppStrings.addPet,
                      onPressed: () =>
                          context.push('/customers/$customerId/pets/new'),
                    ),
                  ],
                ),
              ],
            );
          },
          loading: () => const Padding(
            padding: EdgeInsets.all(AppSpacing.lg),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (error, _) => Column(
            children: [
              Text(messageFor(error), style: AppTypography.body),
              const SizedBox(height: AppSpacing.sm),
              AppButton(
                label: AppStrings.retry,
                onPressed: () => ref.invalidate(customerDetailProvider(key)),
              ),
            ],
          ),
        );
  }
}

class _Siblings extends StatelessWidget {
  const _Siblings({required this.siblings});

  final List<Sibling> siblings;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(AppStrings.siblingsLabel, style: AppTypography.caption),
            for (final s in siblings)
              Pressable(
                semanticLabel: s.name,
                // 형제로 옮길 때는 화면을 바꿔 끼운다 — 뒤로 가면 목록으로 간다.
                onTap: () => context.pushReplacement('/pets/${s.petId}'),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                  child: Row(
                    children: [
                      Text(s.name, style: AppTypography.bodyStrong),
                      if (s.passedAway) ...[
                        const SizedBox(width: AppSpacing.sm),
                        const AppChip(label: AppStrings.passedAwayBadge),
                      ],
                      const Spacer(),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SheetAction extends StatelessWidget {
  const _SheetAction({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        alignment: Alignment.center,
        child: Text(label, style: AppTypography.body),
      ),
    );
  }
}
