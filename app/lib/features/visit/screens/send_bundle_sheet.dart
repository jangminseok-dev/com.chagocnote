import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/share_sheet.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/app_sheet_action.dart';
import '../../../design/widgets/app_snack_bar.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/visit_models.dart';
import '../state/visit_commands.dart';

/// 토막의 이름표. 모르는 종류면 이름표가 없다 — 글은 그대로 싣는다.
String? bundlePartLabel(String kind) => switch (kind) {
  'reservation' => AppStrings.bundlePartReservation,
  'consent' => AppStrings.bundlePartConsent,
  _ => null,
};

/// 그 예약의 보낼 글을 읽어 시트를 띄운다(⑪ 설계 3.5). 보냈으면 `true`.
///
/// 토막이 없거나 읽기에 실패하면 시트를 띄우지 않는다 — 예약은 이미 저장돼 있다. [tellWhy] 면 그 까닭을
/// 스낵바로 알린다(방문 상세의 [보호자에게 보내기] — 사장이 눌렀으니 답이 있어야 한다).
Future<bool> openSendBundle(
  BuildContext context,
  WidgetRef ref, {
  required int shopId,
  required int visitId,
  bool tellWhy = false,
}) async {
  List<BundlePart> parts;
  try {
    parts = await ref.read(visitCommandsProvider).sendBundle(shopId, visitId);
  } catch (_) {
    if (tellWhy && context.mounted) AppSnackBar.show(context, AppStrings.bundleLoadFailed);
    return false;
  }
  if (!context.mounted) return false;
  if (parts.isEmpty) {
    if (tellWhy) AppSnackBar.show(context, AppStrings.bundleNothing);
    return false;
  }
  final sent = await AppSheet.show<bool>(context, builder: (_) => SendBundleSheet(parts: parts));
  return sent == true;
}

/// 보낼 것 시트 — 토막마다 글을 고치거나 뺄 수 있고, [보내기]는 공유 시트 한 번이다.
///
/// 보내지 않고 닫아도 된다(`false`). 공유가 실패하면 시트가 남는다 — 고친 글을 잃지 않는다.
/// **글에는 서류 주소가 들 수 있다 — 로그·오류 문구에 남기지 않는다.**
class SendBundleSheet extends ConsumerStatefulWidget {
  const SendBundleSheet({super.key, required this.parts});

  static const sendKey = Key('bundle-send');

  final List<BundlePart> parts;

  @override
  ConsumerState<SendBundleSheet> createState() => _SendBundleSheetState();
}

class _SendBundleSheetState extends ConsumerState<SendBundleSheet> {
  late final _texts = [for (final part in widget.parts) TextEditingController(text: part.text)];
  late final _included = [for (final _ in widget.parts) true];
  bool _busy = false;
  bool _failed = false;

  @override
  void dispose() {
    for (final text in _texts) {
      text.dispose();
    }
    super.dispose();
  }

  /// 나갈 글 — 넣어 둔 토막 가운데 글자가 있는 것을 빈 줄을 사이에 두고 잇는다.
  String get _message => [
    for (var i = 0; i < _texts.length; i++)
      if (_included[i] && _texts[i].text.trim().isNotEmpty) _texts[i].text.trim(),
  ].join('\n\n');

  Future<void> _send(BuildContext buttonContext) async {
    final message = _message;
    if (message.isEmpty || _busy) return;
    final box = buttonContext.findRenderObject() as RenderBox;
    final origin = box.localToGlobal(Offset.zero) & box.size;
    setState(() {
      _busy = true;
      _failed = false;
    });
    try {
      await ref.read(shareSheetProvider).shareText(message, origin: origin);
    } on Exception {
      if (mounted) {
        setState(() {
          _busy = false;
          _failed = true;
        });
      }
      return;
    }
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final empty = _message.isEmpty;
    return ConstrainedBox(
      // 글이 길어도 시트가 화면을 넘지 않는다 — 안에서 구른다.
      constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.7),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(AppStrings.bundleSheetTitle, style: AppTypography.bodyStrong),
          const SizedBox(height: AppSpacing.xs),
          const Text(AppStrings.bundleSheetHint, style: AppTypography.caption),
          const SizedBox(height: AppSpacing.sm),
          Flexible(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [for (var i = 0; i < widget.parts.length; i++) _part(i)],
              ),
            ),
          ),
          if (empty || _failed)
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.sm),
              child: Semantics(
                liveRegion: true,
                child: Text(
                  empty ? AppStrings.bundleEmpty : AppStrings.bundleShareFailed,
                  style: AppTypography.caption,
                ),
              ),
            ),
          const SizedBox(height: AppSpacing.md),
          Builder(
            builder: (buttonContext) => AppButton(
              key: SendBundleSheet.sendKey,
              label: AppStrings.bundleSend,
              filled: true,
              busy: _busy,
              onPressed: empty ? null : () => _send(buttonContext),
            ),
          ),
          AppSheetAction(label: AppStrings.bundleLater, onTap: () => Navigator.of(context).pop(false)),
        ],
      ),
    );
  }

  Widget _part(int i) {
    final part = widget.parts[i];
    final label = bundlePartLabel(part.kind);
    final included = _included[i];
    final changed = _texts[i].text != part.text;
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text(label ?? '', style: AppTypography.caption)),
              if (included && changed)
                _TextAction(
                  key: ValueKey('bundle-reset-${part.kind}'),
                  label: AppStrings.bundleReset,
                  onTap: () => setState(() => _texts[i].text = part.text),
                ),
              _TextAction(
                key: ValueKey('bundle-toggle-${part.kind}'),
                label: included ? AppStrings.bundleRemove : AppStrings.bundleRestore,
                onTap: () => setState(() => _included[i] = !included),
              ),
            ],
          ),
          TextField(
            key: ValueKey('bundle-part-${part.kind}'),
            controller: _texts[i],
            enabled: included,
            minLines: 1,
            maxLines: null,
            maxLength: 1000,
            keyboardType: TextInputType.multiline,
            style: included ? AppTypography.body : AppTypography.body.copyWith(color: AppColors.secondary),
            decoration: const InputDecoration(counterText: ''),
            onChanged: (_) => setState(() => _failed = false),
          ),
        ],
      ),
    );
  }
}

/// 밑줄 글자 버튼 — 누르는 자리는 44 이상이다.
class _TextAction extends StatelessWidget {
  const _TextAction({super.key, required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: label,
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, 0, AppSpacing.sm),
        child: ExcludeSemantics(
          child: Text(
            label,
            style: const TextStyle(
              inherit: true,
              decoration: TextDecoration.underline,
              color: AppColors.secondary,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}
