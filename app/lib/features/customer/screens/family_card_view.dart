import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/proxy/media_images.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_radius.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';
import '../state/customer_view_mode.dart';

/// 가족 카드 — 머리에 보호자 이름과 가린 번호 뒷자리, 안에 아이들을
/// 줄(목록) 또는 2열 타일(격자)로 보인다. 아이를 누르면 반려동물 상세로 간다.
class FamilyCardView extends StatelessWidget {
  const FamilyCardView({super.key, required this.card, required this.mode});

  final FamilyCard card;
  final CustomerViewMode mode;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        AppSpacing.sm,
        AppSpacing.md,
        AppSpacing.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text.rich(
            TextSpan(
              text: '${card.name} · ${maskedTail(card.phoneMasked)}',
              children: [
                // 주의 표시가 살아 있는 가족(③-B) — 색 딱지 없이 잉크색 두 글자. 사유는 상세에서 본다.
                if (card.caution) ...[
                  const TextSpan(text: ' · '),
                  TextSpan(
                    text: AppStrings.cautionMark,
                    style: AppTypography.caption.copyWith(
                      color: AppColors.ink,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ],
            ),
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.xs),
          if (mode == CustomerViewMode.list)
            for (final pet in card.pets) _PetRow(pet: pet)
          else
            _PetGrid(pets: card.pets),
        ],
      ),
    );
  }
}

void _openPet(BuildContext context, PetSummary pet) =>
    context.push('/pets/${pet.petId}');

class _Badges extends StatelessWidget {
  const _Badges({required this.pet});

  final PetSummary pet;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.xs,
      children: [
        if (pet.hasConditions) const AppChip(label: AppStrings.conditionsBadge),
        if (pet.passedAway) const AppChip(label: AppStrings.passedAwayBadge),
      ],
    );
  }
}

/// 프로필 사진(가장 최근 완료 기록의 대표 사진). 없으면 null — 회색 자리.
ImageProvider? _photoOf(WidgetRef ref, PetSummary pet) {
  final photo = pet.photo;
  return photo == null ? null : ref.watch(mediaImagesProvider).of(photo);
}

class _PetRow extends ConsumerWidget {
  const _PetRow({required this.pet});

  final PetSummary pet;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Pressable(
      key: Key('pet_row_${pet.petId}'),
      semanticLabel: pet.name,
      onTap: () => _openPet(context, pet),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        child: Row(
          children: [
            AppPhotoTile(image: _photoOf(ref, pet), size: 40),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          pet.name,
                          style: AppTypography.bodyStrong,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      _Badges(pet: pet),
                    ],
                  ),
                  Text(
                    '${pet.breed} · ${pet.ageLabel}',
                    style: AppTypography.caption,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PetGrid extends StatelessWidget {
  const _PetGrid({required this.pets});

  final List<PetSummary> pets;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < pets.length; i += 2)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: _PetTile(pet: pets[i])),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: i + 1 < pets.length
                      ? _PetTile(pet: pets[i + 1])
                      : const SizedBox.shrink(),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _PetTile extends ConsumerWidget {
  const _PetTile({required this.pet});

  final PetSummary pet;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final photo = _photoOf(ref, pet);
    return Pressable(
      key: Key('pet_tile_${pet.petId}'),
      semanticLabel: pet.name,
      onTap: () => _openPet(context, pet),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AspectRatio(
            aspectRatio: 1.3,
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.line,
                image: photo == null
                    ? null
                    : DecorationImage(image: photo, fit: BoxFit.cover),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Wrap(
            spacing: AppSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(pet.name, style: AppTypography.bodyStrong),
              _Badges(pet: pet),
            ],
          ),
          Text(
            '${pet.breed} · ${pet.ageLabel}',
            style: AppTypography.caption,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
