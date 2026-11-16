import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/async_body.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../core/time/shop_time.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../api/consent_models.dart';
import '../state/consent_commands.dart';
import '../state/consent_providers.dart';
import '../state/signature_png.dart';
import 'signature_pad.dart';

/// 서명의 선들을 PNG 로 만드는 일. 테스트는 이것을 갈아 끼운다(그림 만들기는 가짜 시계에서 끝나지 않는다).
final signaturePngMakerProvider = Provider<Future<Uint8List> Function(List<List<Offset>>)>((ref) => signaturePng);

String consentPartTitle(ConsentPart part) => switch (part) {
  ConsentPart.basic => AppStrings.consentPartTitleBasic,
  ConsentPart.senior => AppStrings.consentPartTitleSenior,
  ConsentPart.condition => AppStrings.consentPartTitleCondition,
};

/// 매장에서 바로 받는 서명(⑪ 설계 3.3). 사장이 폰을 보호자에게 건넨다 — 네이티브 화면이다.
///
/// 문서는 서버가 아이의 지금 사실로 조립한다. 읽은 문서의 지문을 그대로 돌려보내, 읽는 사이 내용이 바뀌었으면
/// 받지 않고 다시 읽는다. [forDate] 는 예약 날이다 — 그날에 유효한 동의를 지금 받는다.
///
/// 보호자가 뒤로 가도 매장의 다른 화면이 보이지 않게 뒤로 가기는 한 번 묻고, 낸 뒤의 [닫기]는 사장이 누른다.
class ConsentSignScreen extends ConsumerStatefulWidget {
  const ConsentSignScreen({super.key, required this.petIds, this.forDate});

  static const nameKey = Key('consent-name');
  static const agreeKey = Key('consent-agree');
  static const submitKey = Key('consent-submit');
  static const closeKey = Key('consent-close');

  final List<int> petIds;
  final DateTime? forDate;

  @override
  ConsumerState<ConsentSignScreen> createState() => _ConsentSignScreenState();
}

enum _Stage { signing, done, upToDate }

class _ConsentSignScreenState extends ConsumerState<ConsentSignScreen> {
  final _name = TextEditingController();
  final _signature = SignatureController();
  bool _agreed = false;
  bool _sending = false;
  String? _notice;
  _Stage _stage = _Stage.signing;

  @override
  void initState() {
    super.initState();
    // 서명하면 빠진 것의 안내를 지운다. 비울 때는 지우지 않는다 — "내용이 바뀌었어요"가 서명을 비우면서 사라지면 안 된다.
    _signature.addListener(() {
      if (!_signature.isEmpty) _clearNotice();
    });
  }

  @override
  void dispose() {
    _name.dispose();
    _signature.dispose();
    super.dispose();
  }

  void _clearNotice() {
    if (_notice != null && mounted) setState(() => _notice = null);
  }

  ConsentDocumentKey get _key => (
    shopId: ref.read(selectedShopIdProvider) ?? 0,
    petIds: ([...widget.petIds]..sort()).join(','),
    forDate: widget.forDate == null ? null : isoDay(widget.forDate!),
  );

  /// 빠진 것. 없으면 null — 있으면 서버를 부르지 않는다.
  String? _missing() {
    if (_name.text.trim().isEmpty) return AppStrings.consentNameMissing;
    if (_signature.isEmpty) return AppStrings.consentSignatureMissing;
    if (!_agreed) return AppStrings.consentAgreeMissing;
    return null;
  }

  Future<void> _send(ConsentDocument doc) async {
    if (_sending) return;
    final lacking = _missing();
    if (lacking != null) {
      setState(() => _notice = lacking);
      return;
    }
    final shopId = ref.read(selectedShopIdProvider);
    if (shopId == null) return;
    setState(() {
      _sending = true;
      _notice = null;
    });
    String? notice;
    String? failure;
    var stage = _Stage.signing;
    try {
      final png = await ref.read(signaturePngMakerProvider)(_signature.strokes);
      await ref.read(consentCommandsProvider).signInShop(
        shopId,
        petIds: [for (final pet in doc.pets) pet.petId],
        digest: doc.digest,
        signerName: _name.text.trim(),
        png: png,
        forDate: widget.forDate,
      );
      stage = _Stage.done;
    } on ApiException catch (e) {
      switch (e.code) {
        case 'CONSENT_DOCUMENT_CHANGED':
          // 읽는 사이 내용이 바뀌었다 — 다시 읽고 다시 서명한다. 적은 이름은 남긴다.
          notice = AppStrings.consentChanged;
        case 'CONSENT_UP_TO_DATE':
          stage = _Stage.upToDate;
        case 'VALIDATION_ERROR':
          notice = AppStrings.consentSignatureTooBig;
        default:
          failure = messageFor(e);
      }
    } catch (e) {
      failure = messageFor(e);
    }
    if (!mounted) return;
    setState(() {
      _sending = false;
      _stage = stage;
      _notice = notice;
      if (notice == AppStrings.consentChanged) {
        _agreed = false;
        _signature.clear();
      }
    });
    if (notice == AppStrings.consentChanged) ref.invalidate(consentDocumentProvider(_key));
    if (failure != null) AppSnackBar.show(context, failure);
  }

  /// 뒤로 가기 — 서명하는 중이면 한 번 묻는다(보호자가 폰을 쥐고 있다).
  Future<void> _leave() async {
    final leave = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Text(AppStrings.consentLeaveAsk, style: AppTypography.bodyStrong),
          ),
          AppSheetAction(label: AppStrings.consentLeave, onTap: () => Navigator.of(context).pop(true)),
          AppSheetAction(label: AppStrings.consentStay, onTap: () => Navigator.of(context).pop(false)),
        ],
      ),
    );
    if (leave == true && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final value = ref.watch(consentDocumentProvider(_key));
    // 더 받을 것이 없다고 하면 오류 화면이 아니라 그렇게 말한다.
    final error = value.hasError ? value.error : null;
    final upToDate = _stage == _Stage.upToDate || (error is ApiException && error.code == 'CONSENT_UP_TO_DATE');
    final signing = _stage == _Stage.signing && !upToDate;
    return PopScope(
      canPop: !signing,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _leave();
      },
      child: Scaffold(
        key: ScreenKeys.consentSign,
        body: AppBackground(
          child: SafeArea(
            child: switch ((_stage, upToDate)) {
              (_Stage.done, _) => const _Finished(title: AppStrings.consentDoneTitle, text: AppStrings.consentDoneText),
              // 열자마자면 사장이 방금 누른 것이다 — 손 표시를 서명으로 바꾸는 길을 말한다.
              // 보내는 사이에 그렇게 됐으면(보호자가 들고 있다) 받았다고만 말한다.
              (_, true) => _Finished(
                title: AppStrings.consentUpToDateTitle,
                text: _stage == _Stage.upToDate ? AppStrings.consentUpToDateText : AppStrings.consentUpToDateHint,
              ),
              _ => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.sm),
                    child: Row(
                      children: [
                        AppBackButton(onTap: _leave),
                        const SizedBox(width: AppSpacing.sm),
                        const Expanded(child: Text(AppStrings.consentSignTitle, style: AppTypography.titleKo)),
                      ],
                    ),
                  ),
                  Expanded(
                    child: AsyncBody<ConsentDocument>(
                      value: value,
                      onRetry: () => ref.invalidate(consentDocumentProvider(_key)),
                      builder: _form,
                    ),
                  ),
                ],
              ),
            },
          ),
        ),
      ),
    );
  }

  Widget _form(ConsentDocument doc) {
    final family = doc.pets.length > 1;
    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.xxl),
      children: [
        Text(ref.watch(shopNameProvider), style: AppTypography.caption),
        if (doc.previousConsentOn != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(AppStrings.consentPartialNotice(doc.previousConsentOn!), style: AppTypography.body),
          ),
        const SizedBox(height: AppSpacing.md),
        // 아이의 이름과 지병의 이름은 문안 밖에서 늘 따로 그린다 — 무엇에 동의하는지가 빠지지 않는다.
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final (index, pet) in doc.pets.indexed) ...[
                if (index > 0) const Divider(height: AppSpacing.xl, thickness: 1, color: AppColors.line),
                Text(pet.name, style: AppTypography.bodyStrong),
                if (pet.conditions.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.xs),
                    child: Text(AppStrings.consentConditions(pet.conditions), style: AppTypography.caption),
                  ),
              ],
            ],
          ),
        ),
        for (final part in doc.parts) ...[
          const SizedBox(height: AppSpacing.xl),
          Text(consentPartTitle(part), style: AppTypography.bodyStrong),
          if (family)
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.xs),
              child: Text(
                AppStrings.consentAppliesTo([
                  for (final pet in doc.pets)
                    if (pet.parts.contains(part)) pet.name,
                ]),
                style: AppTypography.caption,
              ),
            ),
          for (final line in doc.texts[part]!.split('\n'))
            if (line.trim().isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.sm),
                child: Text(line, style: AppTypography.body),
              ),
        ],
        const Padding(
          padding: EdgeInsets.only(top: AppSpacing.xl),
          child: Divider(height: 1, thickness: 1, color: AppColors.ink),
        ),
        const SizedBox(height: AppSpacing.lg),
        const Text(AppStrings.consentNameLabel, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xs),
        TextField(
          key: ConsentSignScreen.nameKey,
          controller: _name,
          maxLength: 50,
          textInputAction: TextInputAction.done,
          autofillHints: const [AutofillHints.name],
          onChanged: (_) => _clearNotice(),
          decoration: const InputDecoration(counterText: ''),
        ),
        const SizedBox(height: AppSpacing.lg),
        const Text(AppStrings.consentSignatureLabel, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xs),
        SignaturePad(controller: _signature),
        Pressable(
          key: ConsentSignScreen.agreeKey,
          semanticLabel: AppStrings.consentAgree,
          onTap: () => setState(() {
            _agreed = !_agreed;
            if (_agreed) _notice = null;
          }),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
            child: ExcludeSemantics(
              child: Row(
                children: [
                  Icon(_agreed ? Icons.check_box : Icons.check_box_outline_blank, color: AppColors.ink),
                  const SizedBox(width: AppSpacing.sm),
                  const Expanded(child: Text(AppStrings.consentAgree, style: AppTypography.body)),
                ],
              ),
            ),
          ),
        ),
        if (_notice != null)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Semantics(
              liveRegion: true,
              child: Text(_notice!, style: AppTypography.bodyStrong),
            ),
          ),
        AppButton(
          key: ConsentSignScreen.submitKey,
          label: AppStrings.consentSubmit,
          filled: true,
          busy: _sending,
          onPressed: () => _send(doc),
        ),
      ],
    );
  }
}

/// 낸 뒤(또는 더 받을 것이 없을 때)의 한 장. [닫기]는 사장이 누른다.
class _Finished extends StatelessWidget {
  const _Finished({required this.title, required this.text});

  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            liveRegion: true,
            child: Text(title, style: AppTypography.titleKo, textAlign: TextAlign.center),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(text, style: AppTypography.body, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.xxl),
          Center(
            child: AppButton(
              key: ConsentSignScreen.closeKey,
              label: AppStrings.consentClose,
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),
        ],
      ),
    );
  }
}
