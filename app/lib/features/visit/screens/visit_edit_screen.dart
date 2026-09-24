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
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/visit_models.dart';
import '../state/visit_commands.dart';
import '../state/visit_providers.dart';
import 'visit_form.dart';
import 'visit_labels.dart';

/// 방문 수정 — 예약 ②와 같은 폼(설계 9.1). 날짜·시간·반려동물은 예약됨일
/// 때만 바꾸고, 메뉴·소요·메모는 미용 중·완료일 때도 바꾼다(설계 6.2).
/// 묶음 방문의 시간을 바꾸면 같은 묶음의 예약도 같이 옮길지 묻는다.
class VisitEditScreen extends ConsumerStatefulWidget {
  const VisitEditScreen({super.key, required this.visitId});

  final int visitId;

  @override
  ConsumerState<VisitEditScreen> createState() => _VisitEditScreenState();
}

class _VisitEditScreenState extends ConsumerState<VisitEditScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  /// 같이 옮길 수 있는 묶음의 다른 예약(예약됨만 옮길 수 있다). 서버의
  /// group 은 이미 자기를 뺀 형제만 준다.
  List<Visit> _movableSiblings(VisitDetail detail) => [
    for (final v in detail.group)
      if (v.status == VisitStatus.reserved) v,
  ];

  Future<bool?> _askMoveTogether(List<Visit> siblings) {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.moveTogetherQuestion(visitsTitle(siblings)),
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.moveTogether,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.moveOnlyThis,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
  }

  Future<void> _save(VisitDetail detail, VisitFormValue value) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    final visit = detail.visit;
    final startsAt = value.startsAt!;
    final siblings = _movableSiblings(detail);
    var together = false;
    // 문자열이 아니라 벽시계로 견준다 — 서버 직렬화 서식이 달라져도 "안 바뀜"을 안다.
    final timeChanged = ShopTime.parse(startsAt).wall != visit.startsAt.wall;
    if (timeChanged && siblings.isNotEmpty) {
      final answer = await _askMoveTogether(siblings);
      if (answer == null || !mounted) return;
      together = answer;
    }
    setState(() {
      _busy = true;
      _errorText = null;
    });
    final commands = ref.read(visitCommandsProvider);
    try {
      // 묶음을 먼저 한 번에 옮기고(전부 아니면 전무), 이 방문의 나머지 칸을 고친다.
      if (together) {
        await commands.reschedule(
          shopId,
          visitIds: [visit.visitId, for (final v in siblings) v.visitId],
          startsAt: startsAt,
        );
      }
      await commands.update(
        shopId,
        visit.visitId,
        VisitUpdate(
          startsAt: startsAt,
          petId: value.petIds.firstOrNull,
          durationMinutes: value.durationMinutes,
          menuIds: value.menuIds,
          memo: value.memo,
        ),
      );
      if (mounted) context.pop();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final key = (shopId: shopId ?? 0, visitId: widget.visitId);
    final detail = shopId == null
        ? const AsyncValue<VisitDetail>.loading()
        : ref.watch(visitDetailProvider(key));
    return Scaffold(
      key: ScreenKeys.visitEdit,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  AppSpacing.sm,
                ),
                child: Row(
                  children: [
                    AppBackButton(),
                    SizedBox(width: AppSpacing.sm),
                    Text(
                      AppStrings.editVisitTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: detail.when(
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
                              ref.invalidate(visitDetailProvider(key)),
                        ),
                      ],
                    ),
                  ),
                  data: (detail) => _form(shopId!, detail),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _form(int shopId, VisitDetail detail) {
    final visit = detail.visit;
    return VisitForm(
      shopId: shopId,
      customerId: visit.customer.customerId,
      initial: VisitFormInitial(
        date: visit.startsAt.day,
        petIds: {if (visit.pet != null) visit.pet!.petId},
        ownerOnly: visit.pet == null,
        at: hhmm(visit.startsAt.wall),
        durationMinutes: visit.durationMinutes,
        menus: visit.menus,
        memo: visit.memo,
        prefilled: true,
      ),
      header: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.md,
        ),
        child: SizedBox(
          width: double.infinity,
          child: Text(
            '${ownerLabel(visit.customer)} · ${statusLabel(visit.status)}',
            style: AppTypography.bodyStrong,
          ),
        ),
      ),
      submitLabel: (date, at) => AppStrings.save,
      onSubmit: (value) => _save(detail, value),
      busy: _busy,
      errorText: _errorText,
      singlePet: true,
      scheduleLocked: visit.status != VisitStatus.reserved,
      // 옮기는 동안 자기 자신·같은 묶음과 겹친다고 하지 않게 뺀다. 서버의
      // group 은 자기를 빼므로 자기 ID 를 따로 넣는다.
      excludeVisitIds: [visit.visitId, for (final v in detail.group) v.visitId],
    );
  }
}
