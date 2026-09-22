import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/api/social_sign_in.dart';
import '../../auth/state/social_sign_ins.dart';

/// `reauthPromptProvider`(state/reauth.dart)에 연결하는 표준 시트 구현.
/// `AppSheet`로 "보안을 위해 다시 로그인해 주세요"를 보여주고, 이 기기에서
/// 쓸 수 있는(`socialSignInsProvider`) 로그인 수단 중 이미 연결된 것만
/// 버튼으로 늘어놓는다(개발 환경의 dev는 이름 입력 필드로).
Future<SocialCredential?> showReauthPrompt(
  BuildContext context,
  WidgetRef ref,
  List<String> linkedProviders,
) {
  final availableSignIns = ref
      .read(socialSignInsProvider)
      .where((signIn) => linkedProviders.contains(signIn.provider))
      .toList();
  final showDev =
      ref.read(appConfigProvider).isDev && linkedProviders.contains('dev');

  return AppSheet.show<SocialCredential?>(
    context,
    builder: (context) => _ReauthSheetContent(
      signIns: availableSignIns,
      showDev: showDev,
    ),
  );
}

class _ReauthSheetContent extends StatefulWidget {
  const _ReauthSheetContent({required this.signIns, required this.showDev});

  final List<SocialSignIn> signIns;
  final bool showDev;

  @override
  State<_ReauthSheetContent> createState() => _ReauthSheetContentState();
}

class _ReauthSheetContentState extends State<_ReauthSheetContent> {
  final _devNameController = TextEditingController();

  @override
  void dispose() {
    _devNameController.dispose();
    super.dispose();
  }

  Future<void> _signInWith(SocialSignIn signIn) async {
    final credential = await signIn.signIn();
    if (mounted) Navigator.of(context).pop(credential);
  }

  void _signInDev() {
    final name = _devNameController.text.trim();
    if (name.isEmpty) return;
    Navigator.of(context).pop(SocialCredential(provider: 'dev', token: name));
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.reauthPromptTitle,
          style: AppTypography.body,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.lg),
        for (final signIn in widget.signIns) ...[
          SizedBox(
            width: double.infinity,
            child: AppButton(
              label: AppStrings.providerLabel(signIn.provider),
              filled: true,
              onPressed: () => _signInWith(signIn),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
        if (widget.showDev) ...[
          TextField(
            controller: _devNameController,
            decoration: const InputDecoration(labelText: AppStrings.devNameLabel),
          ),
          const SizedBox(height: AppSpacing.sm),
          SizedBox(
            width: double.infinity,
            child: AppButton(label: AppStrings.devSignIn, onPressed: _signInDev),
          ),
        ],
      ],
    );
  }
}
