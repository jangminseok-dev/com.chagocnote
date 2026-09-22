import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';

/// 보호자 폼 — 등록 2단계와 보호자 수정이 함께 쓴다(설계 8.1).
///
/// 필수: 이름, 전화, 마케팅 수신(동의 / 거부 중 하나). 보조 연락처·메모는
/// 선택이다. 등록 2단계는 1단계에서 확인한 번호를 [fixedPhone]으로 넘겨
/// 전화 칸을 숨긴다. 번호는 숫자만 보낸다.
class CustomerForm extends StatefulWidget {
  const CustomerForm({
    super.key,
    required this.submitLabel,
    required this.busy,
    required this.onSubmit,
    this.initial,
    this.fixedPhone,
    this.errorText,
  });

  final String submitLabel;
  final bool busy;
  final ValueChanged<CustomerFields> onSubmit;
  final Customer? initial;

  /// 숫자만. 있으면 전화 칸을 보이지 않고 이 번호를 쓴다.
  final String? fixedPhone;
  final String? errorText;

  @override
  State<CustomerForm> createState() => _CustomerFormState();
}

class _CustomerFormState extends State<CustomerForm> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _phoneAlt = TextEditingController();
  final _memo = TextEditingController();
  bool? _consent;
  Map<String, String> _errors = {};

  @override
  void initState() {
    super.initState();
    final c = widget.initial;
    if (c == null) return;
    _name.text = c.name;
    _phone.text = formatPhone(c.phone);
    _phoneAlt.text = c.phoneAlt == null ? '' : formatPhone(c.phoneAlt!);
    _memo.text = c.memo ?? '';
    _consent = c.marketingConsent;
  }

  @override
  void dispose() {
    for (final c in [_name, _phone, _phoneAlt, _memo]) {
      c.dispose();
    }
    super.dispose();
  }

  void _submit() {
    final errors = <String, String>{};
    final name = _name.text.trim();
    if (name.isEmpty) errors['name'] = AppStrings.ownerNameRequired;
    final phone = widget.fixedPhone ?? phoneDigits(_phone.text);
    if (!isValidPhone(phone)) errors['phone'] = AppStrings.phoneInvalid;
    final altDigits = phoneDigits(_phoneAlt.text);
    final phoneAlt = altDigits.isEmpty ? null : altDigits;
    if (phoneAlt != null && !isValidPhone(phoneAlt)) {
      errors['phoneAlt'] = AppStrings.phoneAltInvalid;
    }
    if (_consent == null) errors['consent'] = AppStrings.consentRequired;

    setState(() => _errors = errors);
    if (errors.isNotEmpty) return;

    widget.onSubmit(
      CustomerFields(
        name: name,
        phone: phone,
        phoneAlt: phoneAlt,
        marketingConsent: _consent!,
        memo: optionalText(_memo.text),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final phoneFormatters = [
      FilteringTextInputFormatter.allow(RegExp(r'[0-9\- ]')),
      LengthLimitingTextInputFormatter(20),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _name,
          inputFormatters: [LengthLimitingTextInputFormatter(50)],
          decoration: InputDecoration(
            labelText: AppStrings.ownerNameLabel,
            hintText: AppStrings.ownerNameHint,
            errorText: _errors['name'],
          ),
        ),
        if (widget.fixedPhone == null) ...[
          const SizedBox(height: AppSpacing.sm),
          TextField(
            controller: _phone,
            keyboardType: TextInputType.phone,
            inputFormatters: phoneFormatters,
            decoration: InputDecoration(
              labelText: AppStrings.ownerPhoneLabel,
              hintText: AppStrings.phoneHint,
              errorText: _errors['phone'],
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _phoneAlt,
          keyboardType: TextInputType.phone,
          inputFormatters: phoneFormatters,
          decoration: InputDecoration(
            labelText: AppStrings.ownerPhoneAltLabel,
            hintText: AppStrings.phoneAltHint,
            errorText: _errors['phoneAlt'],
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(
            top: AppSpacing.lg,
            bottom: AppSpacing.xs,
          ),
          child: Text(
            AppStrings.marketingConsentLabel,
            style: AppTypography.caption,
          ),
        ),
        Wrap(
          spacing: AppSpacing.sm,
          children: [
            AppChoiceChip(
              label: AppStrings.marketingAgreed,
              selected: _consent == true,
              onTap: () => setState(() => _consent = true),
            ),
            AppChoiceChip(
              label: AppStrings.marketingDeclined,
              selected: _consent == false,
              onTap: () => setState(() => _consent = false),
            ),
          ],
        ),
        if (_errors['consent'] != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Text(_errors['consent']!, style: AppTypography.caption),
          ),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _memo,
          minLines: 2,
          maxLines: 5,
          inputFormatters: [LengthLimitingTextInputFormatter(500)],
          decoration: const InputDecoration(
            labelText: AppStrings.customerMemoLabel,
            hintText: AppStrings.customerMemoHint,
          ),
        ),
        if (widget.errorText != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(widget.errorText!, style: AppTypography.caption),
        ],
        const SizedBox(height: AppSpacing.xl),
        Center(
          child: AppButton(
            label: widget.submitLabel,
            filled: true,
            busy: widget.busy,
            onPressed: widget.busy ? null : _submit,
          ),
        ),
      ],
    );
  }
}
