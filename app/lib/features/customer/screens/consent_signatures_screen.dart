import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/async_body.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/consent_models.dart';
import '../state/consent_providers.dart';
import 'consent_sign_screen.dart' show consentPartTitle;

String _via(SignatureChannel channel) => switch (channel) {
  SignatureChannel.link => AppStrings.signatureViaLink,
  SignatureChannel.inShop => AppStrings.signatureViaShop,
  SignatureChannel.intake => AppStrings.signatureViaIntake,
};

class _Head extends StatelessWidget {
  const _Head(this.title);

  final String title;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.sm),
    child: Row(
      children: [
        const AppBackButton(),
        const SizedBox(width: AppSpacing.sm),
        Expanded(child: Text(title, style: AppTypography.titleKo)),
      ],
    ),
  );
}

/// 그 아이가 받은 서명들(⑪ 설계 3.6), 새것부터. 누르면 한 장을 본다.
class ConsentSignaturesScreen extends ConsumerWidget {
  const ConsentSignaturesScreen({super.key, required this.petId});

  final int petId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final key = (shopId: ref.watch(selectedShopIdProvider) ?? 0, petId: petId);
    return Scaffold(
      key: ScreenKeys.consentSignatures,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _Head(AppStrings.signaturesTitle),
              Expanded(
                child: AsyncBody<List<SignatureBrief>>(
                  value: ref.watch(petSignaturesProvider(key)),
                  onRetry: () => ref.invalidate(petSignaturesProvider(key)),
                  builder: (items) => ListView(
                    padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
                    children: [
                      if (items.isEmpty)
                        const Padding(
                          padding: EdgeInsets.only(top: AppSpacing.xxl),
                          child: Center(child: Text(AppStrings.signaturesEmpty, style: AppTypography.body)),
                        ),
                      for (final item in items) _row(context, item),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _row(BuildContext context, SignatureBrief item) {
    final line = AppStrings.signatureRow(item.signedAt.toLocal(), _via(item.channel), item.signerName);
    final parts = [for (final part in item.parts) consentPartTitle(part)].join(' · ');
    return Pressable(
      key: ValueKey('signature-${item.signatureId}'),
      semanticLabel: '$line, $parts',
      onTap: () => context.push('/consent-signatures/${item.signatureId}'),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.line))),
        child: ExcludeSemantics(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(line, style: AppTypography.body),
                    const SizedBox(height: AppSpacing.xs),
                    Text(parts, style: AppTypography.caption),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

/// 서명 한 장 — 그때 읽은 글과 보인 사실, 적은 이름, 서명 그림.
/// 그림은 기기에 저장하지 않고 받은 바이트를 그대로 그린다(흰 바탕 위에).
class ConsentSignatureScreen extends ConsumerWidget {
  const ConsentSignatureScreen({super.key, required this.signatureId});

  static const imageKey = Key('signature-image');

  final int signatureId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final key = (shopId: ref.watch(selectedShopIdProvider) ?? 0, signatureId: signatureId);
    return Scaffold(
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _Head(AppStrings.signatureDetailTitle),
              Expanded(
                child: AsyncBody<SignatureDetail>(
                  value: ref.watch(signatureDetailProvider(key)),
                  onRetry: () => ref.invalidate(signatureDetailProvider(key)),
                  builder: (detail) => _body(ref, key, detail),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(WidgetRef ref, SignatureKey key, SignatureDetail detail) {
    final image = ref.watch(signatureImageProvider(key));
    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
      children: [
        Text(AppStrings.fullDate(detail.signedAt.toLocal()), style: AppTypography.bodyStrong),
        const SizedBox(height: AppSpacing.xs),
        // 본인 인증이 없다 — 누가 어떻게 적은 서명인지를 그대로 말한다.
        Text(
          switch (detail.channel) {
            SignatureChannel.link => AppStrings.signatureNoteLink,
            SignatureChannel.inShop => AppStrings.signatureNoteShop,
            SignatureChannel.intake => AppStrings.signatureNoteIntake,
          },
          style: AppTypography.caption,
        ),
        for (final pet in detail.pets) ...[
          const SizedBox(height: AppSpacing.lg),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(pet.shownName, style: AppTypography.bodyStrong),
                if (pet.conditions.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.xs),
                    child: Text(AppStrings.consentConditions(pet.conditions), style: AppTypography.caption),
                  ),
              ],
            ),
          ),
          for (final item in pet.parts) ...[
            const SizedBox(height: AppSpacing.lg),
            Text(consentPartTitle(item.part), style: AppTypography.bodyStrong),
            for (final line in item.body.split('\n'))
              if (line.trim().isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.sm),
                  child: Text(line, style: AppTypography.body),
                ),
          ],
        ],
        const Padding(
          padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
          child: Divider(height: 1, thickness: 1, color: AppColors.ink),
        ),
        Text(AppStrings.signatureSigner(detail.signerName), style: AppTypography.body),
        const SizedBox(height: AppSpacing.sm),
        AspectRatio(
          aspectRatio: 5 / 2,
          child: DecoratedBox(
            decoration: BoxDecoration(color: AppColors.white, border: Border.all(color: AppColors.line)),
            // 그림을 읽지 못해도 글은 보인다 — 그 자리만 비운다.
            child: switch (image) {
              AsyncData(:final value) => Image.memory(
                value,
                key: imageKey,
                fit: BoxFit.contain,
                semanticLabel: AppStrings.signatureImageLabel,
                gaplessPlayback: true,
                errorBuilder: (context, _, _) => const SizedBox.shrink(),
              ),
              _ => const SizedBox.shrink(),
            },
          ),
        ),
      ],
    );
  }
}
