import 'dart:async';

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
/// [timeout] 안에 글이 오지 않으면 읽지 못한 것으로 친다 — 저장 화면이 오래 붙들리지 않는다.
/// [onReady] 는 시트를 띄우기 직전(또는 띄우지 않기로 한 때)에 한 번 불린다 — 부른 화면이 진행 표시를 끈다.
///
/// **보내지 않고 닫으면 이 조립이 새로 만든 동의서 링크를 끊는다** — 보내지 않았는데 "보냈어요"가 뜨지 않는다.
Future<bool> openSendBundle(
  BuildContext context,
  WidgetRef ref, {
  required int shopId,
  required int visitId,
  bool tellWhy = false,
  Duration? timeout,
  VoidCallback? onReady,
}) async {
  final commands = ref.read(visitCommandsProvider);
  SendBundle bundle;
  final reading = commands.sendBundle(shopId, visitId);
  try {
    bundle = await (timeout == null ? reading : reading.timeout(timeout));
  } on TimeoutException {
    // 기다리지 않기로 했다 — 뒤늦게 온 응답이 링크를 만들었으면 그것도 끊는다(보내지 않았다).
    unawaited(
      reading.then<void>((late) async {
        if (late.createdFormId case final formId?) await commands.dropUnsentLink(shopId, formId);
      }, onError: (_) {}),
    );
    onReady?.call();
    return false;
  } catch (_) {
    onReady?.call();
    if (tellWhy && context.mounted) AppSnackBar.show(context, AppStrings.bundleLoadFailed);
    return false;
  }
  onReady?.call();
  final created = bundle.createdFormId;
  if (!context.mounted || bundle.parts.isEmpty) {
    if (created != null) await commands.dropUnsentLink(shopId, created);
    if (tellWhy && context.mounted) AppSnackBar.show(context, AppStrings.bundleNothing);
    return false;
  }
  final sent = await AppSheet.show<bool>(context, builder: (_) => SendBundleSheet(parts: bundle.parts)) == true;
  if (!sent && created != null) await commands.dropUnsentLink(shopId, created);
  return sent;
}

/// 보낼 것 시트 — 토막마다 글을 고치거나 뺄 수 있고, [보내기]는 공유 시트 한 번이다.
///
/// 보내지 않고 닫아도 된다(`false`). **[보내기] 뒤에도 시트는 남는다** — 공유 창에서 취소했는지를 앱이 알 수
/// 없어서다(고친 글을 잃지 않고 다시 보낼 수 있다). 한 번이라도 공유 창을 열었으면 [닫기]가 `true` 를 돌려준다.
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
  bool _shared = false; // 공유 창을 한 번이라도 열었다

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
    if (mounted) {
      setState(() {
        _busy = false;
        _shared = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final empty = _message.isEmpty;
    final media = MediaQuery.of(context);
    // 글이 길어도, 키보드가 올라와도 시트가 보이는 자리를 넘지 않는다 — 안에서 구르고 [보내기]는 늘 보인다.
    // 96 은 시트의 바깥 여백·안쪽 여백·잡이의 높이다.
    final room = media.size.height - media.viewInsets.bottom - media.padding.top - media.padding.bottom - 96;
    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: room.clamp(160.0, media.size.height * 0.7)),
      child: GestureDetector(
        // 글 밖을 누르면 키보드가 내려간다(여러 줄 입력에는 내리는 키가 없다).
        behavior: HitTestBehavior.translucent,
        onTap: () => FocusManager.instance.primaryFocus?.unfocus(),
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
              label: _shared ? AppStrings.bundleSendAgain : AppStrings.bundleSend,
              filled: !_shared,
              busy: _busy,
              onPressed: empty ? null : () => _send(buttonContext),
            ),
          ),
          if (_shared)
            const Padding(
              padding: EdgeInsets.only(top: AppSpacing.sm),
              child: Text(AppStrings.bundleSentHint, style: AppTypography.caption, textAlign: TextAlign.center),
            ),
          AppSheetAction(
            label: _shared ? AppStrings.close : AppStrings.bundleLater,
            onTap: () => Navigator.of(context).pop(_shared),
          ),
        ],
        ),
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
