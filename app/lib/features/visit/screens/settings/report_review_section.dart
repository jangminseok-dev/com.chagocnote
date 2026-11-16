import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/proxy/external_link.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_button.dart';
import '../../../../design/widgets/app_card.dart';
import '../../../../design/widgets/app_snack_bar.dart';
import '../../../../l10n/app_strings.dart';
import '../../api/report_models.dart';
import '../../state/report_rules.dart';
import 'report_guardian_previews.dart';

/// 알림장 설정의 `알림장 끝에 리뷰 남기기 줄 넣기`(⑫ 설계 3.6) — 주소 칸 · [열어 보기] · 문구 칸 · [저장]과
/// 그 아래 보호자가 받는 모습.
///
/// 글을 치는 칸이라 이 구역만 [저장]이 있다. 저장은 화면이 보이는 서버 값의 나머지 칸에 적은 두 칸을 얹어
/// 전체를 보낸다([onSave]). 다른 스위치·칩은 서버의 리뷰 값을 실어 보내므로, 적던 글은 칸에 남고 함께
/// 나가지 않는다. 서버 값이 바뀌면(저장·다시 읽기) 고치지 않은 칸만 따라간다.
class ReportReviewSection extends ConsumerStatefulWidget {
  const ReportReviewSection({
    super.key,
    required this.shown,
    required this.shopName,
    required this.canEdit,
    required this.locked,
    required this.onSave,
  });

  /// 화면이 보이는 서버 값.
  final ReportSettings shown;
  final String shopName;

  /// 사장만 바꾼다. 직원도 [열어 보기]는 된다.
  final bool canEdit;

  /// 보내는 중·다시 읽는 중 — [저장]을 받지 않는다.
  final bool locked;
  final Future<void> Function(ReportSettings next) onSave;

  @override
  ConsumerState<ReportReviewSection> createState() =>
      _ReportReviewSectionState();
}

class _ReportReviewSectionState extends ConsumerState<ReportReviewSection> {
  late final _url = TextEditingController(text: widget.shown.reviewUrl ?? '');
  late final _text = TextEditingController(text: _textOf(widget.shown));
  String? _urlError;
  String? _textError;
  bool _saving = false;

  /// 문구 칸에 보일 글 — 매장이 고친 문구, 없으면 기본 문구.
  static String _textOf(ReportSettings s) =>
      s.reviewText ?? s.reviewTextDefault ?? '';

  @override
  void initState() {
    super.initState();
    // 고치면 그 칸의 까닭을 지우고 보호자가 받는 모습을 다시 그린다.
    _url.addListener(() => setState(() => _urlError = null));
    _text.addListener(() => setState(() => _textError = null));
  }

  @override
  void didUpdateWidget(ReportReviewSection old) {
    super.didUpdateWidget(old);
    final now = widget.shown;
    // 서버 값이 바뀌면, 고치지 않은 칸(보낼 값이 앞 서버 값과 같다)과 방금 저장한 칸(보낼 값이 새 서버 값과
    // 같다)만 새 서버 값으로 그린다 — 저장한 뒤 칸이 서버가 둔 모양(소문자 스킴·기본 문구)을 따라간다.
    // 고치던 칸은 그대로 둔다.
    if (now.reviewUrl != old.shown.reviewUrl) {
      final typed = cleanReviewUrl(_url.text);
      if (typed == old.shown.reviewUrl || typed == now.reviewUrl) {
        _url.text = now.reviewUrl ?? '';
      }
    }
    if (now.reviewText != old.shown.reviewText ||
        now.reviewTextDefault != old.shown.reviewTextDefault) {
      if (_cleanText(old.shown) == old.shown.reviewText ||
          _cleanText(now) == now.reviewText) {
        _text.text = _textOf(now);
      }
    }
  }

  @override
  void dispose() {
    _url.dispose();
    _text.dispose();
    super.dispose();
  }

  String? _cleanText(ReportSettings against) =>
      cleanReviewText(_text.text, defaultText: against.reviewTextDefault);

  bool get _dirty =>
      cleanReviewUrl(_url.text) != widget.shown.reviewUrl ||
      _cleanText(widget.shown) != widget.shown.reviewText;

  Future<void> _save() async {
    final urlProblem = reviewUrlProblem(_url.text);
    final textProblem = reviewTextProblem(_text.text);
    if (urlProblem != null || textProblem != null) {
      setState(() {
        _urlError = urlProblem;
        _textError = textProblem;
      });
      return;
    }
    setState(() => _saving = true);
    await widget.onSave(
      ReportSettings.fromJson({
        ...widget.shown.toJson(),
        'review_url': cleanReviewUrl(_url.text),
        'review_text': _cleanText(widget.shown),
      }),
    );
    if (mounted) setState(() => _saving = false);
  }

  /// 기기의 브라우저로 칸의 주소를 연다 — 맞는 곳인지 매장이 본다. 틀린 주소는 열지 않고 까닭을 말한다.
  Future<void> _open() async {
    final url = cleanReviewUrl(_url.text);
    final problem = reviewUrlProblem(_url.text);
    if (url == null || problem != null) {
      setState(() => _urlError = problem ?? AppStrings.reviewUrlNotHttps);
      return;
    }
    try {
      await ref.read(externalLinkProvider).open(Uri.parse(url));
    } on Exception {
      if (mounted) AppSnackBar.show(context, AppStrings.reviewOpenFailed);
    } on ArgumentError {
      if (mounted) AppSnackBar.show(context, AppStrings.reviewOpenFailed);
    }
  }

  @override
  Widget build(BuildContext context) {
    final url = cleanReviewUrl(_url.text);
    final text = _text.text.trim().isEmpty
        ? (widget.shown.reviewTextDefault ?? '')
        : _text.text.trim();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(AppStrings.reviewSectionLabel, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.sm),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: TextField(
                      key: const ValueKey('report-review-url'),
                      controller: _url,
                      readOnly: !widget.canEdit,
                      keyboardType: TextInputType.url,
                      autocorrect: false,
                      enableSuggestions: false,
                      decoration: InputDecoration(
                        hintText: AppStrings.reviewUrlHint,
                        errorText: _urlError,
                        errorMaxLines: 2,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  AppButton(
                    label: AppStrings.reviewOpen,
                    onPressed: _url.text.trim().isEmpty ? null : _open,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              TextField(
                key: const ValueKey('report-review-text'),
                controller: _text,
                readOnly: !widget.canEdit,
                maxLines: 1,
                decoration: InputDecoration(
                  hintText: AppStrings.reviewTextHint,
                  errorText: _textError,
                  errorMaxLines: 2,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              const Text(
                AppStrings.reviewSectionHint,
                style: AppTypography.caption,
              ),
              if (widget.canEdit) ...[
                const SizedBox(height: AppSpacing.md),
                AppButton(
                  label: AppStrings.save,
                  filled: true,
                  busy: _saving,
                  onPressed: !widget.locked && !_saving && _dirty
                      ? _save
                      : null,
                ),
              ],
              const SizedBox(height: AppSpacing.lg),
              const Text(
                AppStrings.reportGuardianSees,
                style: AppTypography.caption,
              ),
              const SizedBox(height: AppSpacing.sm),
              if (url == null)
                const Padding(
                  padding: EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Text(
                    AppStrings.reviewEmptyPreview,
                    style: AppTypography.caption,
                  ),
                ),
              ReviewPreview(
                shopName: widget.shopName,
                showShopInfo: widget.shown.showShopInfo,
                text: text,
                faded: url == null,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
