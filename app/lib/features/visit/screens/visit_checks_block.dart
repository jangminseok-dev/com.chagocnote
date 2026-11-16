import 'package:flutter/material.dart';

import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/check_models.dart';
import '../state/check_rules.dart';

/// "확인할 것" 묶음(③-B 설계 3.4) — 예약 등록과 방문 상세가 함께 쓴다.
///
/// 알리기만 하고 막지 않는다. 톤은 잉크색 글자와 가는 선뿐이다(색 딱지·경고 그림 없음).
/// 할 일인 미용 동의 줄에만 버튼이 붙는다(받는 쪽을 준 화면에서, 아이 묶음에) —
/// [동의서 보내기]·[여기서 서명]·[받았어요]. 주지 않은 것은 그리지 않는다.
/// 지병 줄은 메모가 있으면 눌러서 펼친다. [sections]가 비면 아무것도 그리지 않는다.
class VisitChecksBlock extends StatefulWidget {
  const VisitChecksBlock({
    super.key,
    required this.sections,
    this.onConsent,
    this.consentBusy = false,
    this.onSend,
    this.sendBusy = false,
    this.onSignHere,
  });

  final List<CheckSection> sections;
  final void Function(int petId)? onConsent;

  /// 동의를 적는 중 — 버튼에 스피너를 켜고 다시 누르지 못하게 한다.
  final bool consentBusy;

  /// [동의서 보내기](보낸 링크가 살아 있으면 [다시 공유]) — 아이와, 공유 시트를 붙일 버튼의 사각형(⑪).
  final void Function(int petId, Rect origin)? onSend;
  final bool sendBusy;

  /// [여기서 서명] — 매장에서 바로 서명받는다.
  final void Function(int petId)? onSignHere;

  @override
  State<VisitChecksBlock> createState() => _VisitChecksBlockState();
}

class _VisitChecksBlockState extends State<VisitChecksBlock> {
  /// 메모를 펼친 지병 줄(묶음 번호). 묶음마다 지병 줄은 하나뿐이다.
  final _opened = <int>{};

  @override
  Widget build(BuildContext context) {
    final sections = widget.sections;
    if (sections.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: AppColors.line),
          bottom: BorderSide(color: AppColors.line),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(AppStrings.checksTitle, style: AppTypography.caption),
          for (final (index, section) in sections.indexed) ...[
            if (index > 0)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: AppSpacing.xs),
                child: Divider(height: 1, thickness: 1, color: AppColors.line),
              ),
            if (section.title != null)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.xs),
                child: Text(section.title!, style: AppTypography.caption),
              ),
            for (final check in section.checks) _line(index, section, check),
          ],
        ],
      ),
    );
  }

  /// 버튼을 글자 폭만큼만 차지하게 한다 — 줄바꿈 묶음 안에서는 버튼이 줄 전체로 늘어난다.
  static Widget _fit(Widget button) => IntrinsicWidth(child: button);

  Widget _line(int index, CheckSection section, VisitCheck check) {
    final text = Text(checkLine(check), style: AppTypography.body);
    const pad = EdgeInsets.symmetric(vertical: AppSpacing.xs);
    final petId = section.petId;
    final onConsent = widget.onConsent;
    final onSend = widget.onSend;
    final onSignHere = widget.onSignHere;
    if (check.code == CheckCode.consent &&
        petId != null &&
        (onConsent != null || onSend != null || onSignHere != null)) {
      return Padding(
        padding: pad,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            text,
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                if (onSend != null)
                  // 공유 시트는 누른 버튼에 붙는다(아이패드) — 버튼의 사각형을 넘긴다.
                  _fit(Builder(
                    builder: (context) => AppButton(
                      key: ValueKey('consent-send-$petId'),
                      label: consentSent(check)
                          ? AppStrings.consentShareAgain
                          : AppStrings.consentSend,
                      busy: widget.sendBusy,
                      onPressed: () {
                        final box = context.findRenderObject()! as RenderBox;
                        onSend(petId, box.localToGlobal(Offset.zero) & box.size);
                      },
                    ),
                  )),
                if (onSignHere != null)
                  _fit(AppButton(
                    key: ValueKey('consent-sign-$petId'),
                    label: AppStrings.consentSignHere,
                    onPressed: () => onSignHere(petId),
                  )),
                if (onConsent != null)
                  _fit(AppButton(
                    key: ValueKey('consent-received-$petId'),
                    label: AppStrings.consentReceived,
                    busy: widget.consentBusy,
                    onPressed: () => onConsent(petId),
                  )),
              ],
            ),
          ],
        ),
      );
    }
    final notes = [
      for (final c in check.conditions)
        if (c.note != null && c.note!.isNotEmpty) (c.label, c.note!),
    ];
    if (check.code != CheckCode.conditions || notes.isEmpty) {
      return Padding(padding: pad, child: text);
    }
    final opened = _opened.contains(index);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Pressable(
          semanticLabel: checkLine(check),
          onTap: () => setState(
            () => opened ? _opened.remove(index) : _opened.add(index),
          ),
          child: Padding(
            padding: pad,
            child: ExcludeSemantics(
              child: Row(
                children: [
                  Expanded(child: text),
                  Icon(
                    opened ? Icons.expand_less : Icons.expand_more,
                    size: 20,
                  ),
                ],
              ),
            ),
          ),
        ),
        if (opened)
          for (final (label, note) in notes)
            Padding(
              padding: const EdgeInsets.only(
                left: AppSpacing.md,
                bottom: AppSpacing.xs,
              ),
              child: Text(
                AppStrings.checkConditionNote(label, note),
                style: AppTypography.caption,
              ),
            ),
      ],
    );
  }
}
