import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/async_body.dart';
import '../../../../core/error/error_messages.dart';
import '../../../../core/router/screen_keys.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_back_button.dart';
import '../../../../design/widgets/app_button.dart';
import '../../../../design/widgets/app_card.dart';
import '../../../../design/widgets/app_sheet.dart';
import '../../../../design/widgets/app_sheet_action.dart';
import '../../../../design/widgets/app_switch.dart';
import '../../../../design/widgets/pressable.dart';
import '../../../../l10n/app_strings.dart';
import '../../../auth/state/shop_selection.dart';
import '../../api/notification_models.dart';
import '../../state/notification_commands.dart';
import '../../state/notification_providers.dart';
import '../../state/notification_rules.dart';

final _adminPhone = RegExp(r'^01[0-9]{8,9}$');
final _senderPhone = RegExp(r'^[0-9]{9,11}$');
final _sixDigits = RegExp(r'^[0-9]{6}$');

/// 종류 줄 다섯 — 서버의 칸 이름, 이름, 템플릿 상태를 볼 종류들(변경·취소는 한 스위치가 둘을 켠다).
const _kindRows = [
  (
    'confirm_enabled',
    AppStrings.notificationKindConfirm,
    [NotificationKind.confirm],
  ),
  (
    'reminder_enabled',
    AppStrings.notificationKindReminder,
    [NotificationKind.reminder],
  ),
  (
    'change_enabled',
    AppStrings.notificationKindChangeCancel,
    [NotificationKind.change, NotificationKind.cancel],
  ),
  (
    'report_enabled',
    AppStrings.notificationKindReport,
    [NotificationKind.report],
  ),
  (
    'next_visit_enabled',
    AppStrings.notificationKindNextVisit,
    [NotificationKind.nextVisit],
  ),
];

/// 설정 → 알림톡(⑥ 설계 8.1). 연동 전에는 준비 안내와 채널 연동, 연동 뒤에는 종류별 스위치와 시각·주기,
/// 문자 대체.
///
/// [저장] 버튼이 없다 — 누르면 바로 아홉 칸 전체를 보낸다. 낙관적으로 그리지 않고, 다시 읽은 서버 값으로
/// 그린다. 연동·설정은 사장만 하고(`shop:update`) 직원에게는 읽기 전용이다. 채널 검색 아이디·관리자
/// 번호·카테고리는 서버도 저장하지 않는다 — 인증번호를 받고 연동할 때까지 이 화면이 들고 있다.
class NotificationSettingsScreen extends ConsumerStatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  ConsumerState<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends ConsumerState<NotificationSettingsScreen> {
  final _searchId = TextEditingController();
  final _phone = TextEditingController();
  final _category = TextEditingController();
  final _token = TextEditingController();

  /// 인증번호를 받았다 — 입력 셋을 잠그고 6자리 칸을 연다.
  bool _tokenRequested = false;
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  @override
  void dispose() {
    _searchId.dispose();
    _phone.dispose();
    _category.dispose();
    _token.dispose();
    super.dispose();
  }

  /// 쓰기 하나를 보낸다. 성공했으면 true. 성공하든 실패하든 명령이 한눈에 보기를 다시 읽게 하고, 화면은
  /// 그 값으로 다시 그린다.
  Future<bool> _run(
    Future<void> Function(NotificationCommands commands, int shopId) action,
  ) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return false;
    // 화면의 값이 방금 읽은 것이 아니면(다시 읽는 중, 다시 읽기 실패로 이전 내용) 누르지 않은 것으로
    // 친다 — 낡은 값 위에 아홉 칸을 덮어 보내면 방금 바꾼 칸을 되돌린다.
    final overview = ref.read(notificationOverviewProvider(shopId));
    if (overview.isLoading || overview.hasError) return false;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    String? error;
    try {
      await action(ref.read(notificationCommandsProvider), shopId);
    } catch (e) {
      error = messageFor(e);
    }
    if (!mounted) return false;
    setState(() {
      _busy = false;
      _errorText = error;
    });
    return error == null;
  }

  /// [field] 한 칸만 바꿔 아홉 칸 전체를 보낸다. 본문은 **지금 읽혀 있는 값**으로 만든다 — 화면이 그릴 때
  /// 잡아 둔 값으로 만들면, 고르기 시트가 열려 있던 사이 바뀐 다른 칸을 옛 값으로 되돌린다. `_run`의 문지기를
  /// 지난 뒤라 그 값은 방금 읽은 것이다.
  Future<void> _set(String field, Object? value) => _run(
    (commands, shopId) => commands.updateSettings(
      shopId,
      ref
          .read(notificationOverviewProvider(shopId))
          .requireValue
          .settingsBody(field: field, value: value),
    ),
  );

  bool get _inputsReady =>
      _searchId.text.trim().isNotEmpty &&
      _category.text.trim().isNotEmpty &&
      _adminPhone.hasMatch(_phone.text);

  Future<void> _requestToken() async {
    final ok = await _run(
      (commands, shopId) => commands.requestChannelToken(
        shopId,
        searchId: _searchId.text.trim(),
        adminPhone: _phone.text,
        categoryCode: _category.text.trim(),
      ),
    );
    if (ok && mounted) setState(() => _tokenRequested = true);
  }

  Future<void> _link() async {
    final ok = await _run(
      (commands, shopId) => commands.linkChannel(
        shopId,
        searchId: _searchId.text.trim(),
        adminPhone: _phone.text,
        categoryCode: _category.text.trim(),
        token: _token.text,
      ),
    );
    if (!ok || !mounted) return;
    // 연동됐다 — 입력값을 더 들고 있지 않는다.
    setState(() {
      _tokenRequested = false;
      for (final c in [_searchId, _phone, _category, _token]) {
        c.clear();
      }
    });
  }

  Future<void> _openMore() async {
    final unlink = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppSheetAction(
            label: AppStrings.notificationUnlink,
            onTap: () => Navigator.of(context).pop(true),
          ),
        ],
      ),
    );
    if (unlink != true || !mounted) return;
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            AppStrings.notificationUnlinkConfirm,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.notificationUnlink,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await _run((commands, shopId) => commands.unlinkChannel(shopId));
  }

  /// 고르기 — 목록에서 하나를 누르면 닫히고 그때 한 번 보낸다. 지금 값을 다시 고르면 보내지 않는다.
  Future<void> _pick<T>({
    required String field,
    required List<T> choices,
    required T current,
    required String Function(T) label,
  }) async {
    // 보내는 중에는 열지 않는다 — 닫힐 때 보낼 수 없고, 열 때의 값이 곧 낡는다.
    if (_busy) return;
    final options = withCurrent(choices, current);
    final index = await AppSheet.show<int>(
      context,
      builder: (context) => ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.6,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final (i, option) in options.indexed)
                AppSheetAction(
                  label: label(option),
                  onTap: () => Navigator.of(context).pop(i),
                ),
            ],
          ),
        ),
      ),
    );
    if (index == null || !mounted || options[index] == current) return;
    await _set(field, options[index]);
  }

  /// 문자 대체 — 켜려는데 발신번호 인증이 없으면 인증 시트부터. 인증을 마치면 곧바로 켠다.
  Future<void> _setFallback(NotificationOverview shown, bool on) async {
    if (!on || shown.channel.senderVerified) {
      await _set('sms_fallback_enabled', on);
      return;
    }
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    final verified = await AppSheet.show<bool>(
      context,
      builder: (context) => _SenderSheet(shopId: shopId),
    );
    if (verified != true || !mounted) return;
    // 인증으로 채널이 바뀌어 한눈에 보기를 다시 읽는 중이다 — 다 읽은 값 위에 켠다(읽는 중에는 누름을
    // 받지 않는다). 읽지 못했으면 켜지 않는다 — 화면이 실패를 보이고, 다시 읽은 뒤 스위치를 누르면 된다.
    try {
      await ref.read(notificationOverviewProvider(shopId).future);
    } on Exception {
      return;
    }
    if (!mounted) return;
    await _set('sms_fallback_enabled', true);
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final overview = shopId == null
        ? const AsyncValue<NotificationOverview>.loading()
        : ref.watch(notificationOverviewProvider(shopId));
    final canEdit = ref.watch(isOwnerProvider);
    return Scaffold(
      key: ScreenKeys.notificationSettings,
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
                      AppStrings.notificationSettingsTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<NotificationOverview>(
                  value: overview,
                  onRetry: () =>
                      ref.invalidate(notificationOverviewProvider(shopId!)),
                  builder: (data) => ListView(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.lg,
                      0,
                      AppSpacing.lg,
                      AppSpacing.xxl,
                    ),
                    children: data.channel.status == ChannelStatus.linked
                        ? _linked(data, canEdit: canEdit)
                        : _unlinked(canEdit: canEdit),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _notice(String text) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.md),
    child: Text(text, style: AppTypography.caption),
  );

  // --- 연동 전 ---------------------------------------------------------------------------------------------

  List<Widget> _unlinked({required bool canEdit}) {
    if (!canEdit) return [_notice(AppStrings.notificationOwnerLinks)];
    final locked = _tokenRequested || _busy;
    return [
      if (_errorText case final error?) _notice(error),
      const AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              AppStrings.notificationPrepareTitle,
              style: AppTypography.bodyStrong,
            ),
            SizedBox(height: AppSpacing.sm),
            _Step(1, AppStrings.notificationPrepare1),
            _Step(2, AppStrings.notificationPrepare2),
            _Step(3, AppStrings.notificationPrepare3),
          ],
        ),
      ),
      const SizedBox(height: AppSpacing.lg),
      TextField(
        key: const Key('notification_search_id'),
        controller: _searchId,
        enabled: !locked,
        onChanged: (_) => setState(() {}),
        decoration: const InputDecoration(
          labelText: AppStrings.notificationSearchIdLabel,
          helperText: AppStrings.notificationSearchIdHint,
        ),
      ),
      const SizedBox(height: AppSpacing.md),
      TextField(
        key: const Key('notification_admin_phone'),
        controller: _phone,
        enabled: !locked,
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        onChanged: (_) => setState(() {}),
        decoration: const InputDecoration(
          labelText: AppStrings.notificationAdminPhoneLabel,
          helperText: AppStrings.notificationAdminPhoneHint,
        ),
      ),
      const SizedBox(height: AppSpacing.md),
      TextField(
        key: const Key('notification_category'),
        controller: _category,
        enabled: !locked,
        onChanged: (_) => setState(() {}),
        decoration: const InputDecoration(
          labelText: AppStrings.notificationCategoryLabel,
          helperText: AppStrings.notificationCategoryHint,
        ),
      ),
      const SizedBox(height: AppSpacing.xl),
      if (!_tokenRequested)
        AppButton(
          label: AppStrings.notificationRequestToken,
          filled: true,
          busy: _busy,
          onPressed: _inputsReady && !_busy ? _requestToken : null,
        )
      else ...[
        TextField(
          key: const Key('notification_token'),
          controller: _token,
          enabled: !_busy,
          keyboardType: TextInputType.number,
          maxLength: 6,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          onChanged: (_) => setState(() {}),
          decoration: const InputDecoration(
            labelText: AppStrings.notificationTokenLabel,
            helperText: AppStrings.notificationTokenHint,
            counterText: '',
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(
          label: AppStrings.notificationLink,
          filled: true,
          busy: _busy,
          onPressed: _sixDigits.hasMatch(_token.text) && !_busy ? _link : null,
        ),
        const SizedBox(height: AppSpacing.sm),
        AppButton(
          label: AppStrings.notificationEditInputs,
          onPressed: _busy
              ? null
              : () => setState(() {
                  _tokenRequested = false;
                  _token.clear();
                  _errorText = null;
                }),
        ),
      ],
    ];
  }

  // --- 연동 후 ---------------------------------------------------------------------------------------------

  /// 줄에 보일 템플릿 상태 문구 — 여러 종류면 나쁜 쪽(반려 > 심사 중 > 승인). 등록한 적이 없으면 null.
  String? _templateText(
    NotificationOverview shown,
    List<NotificationKind> kinds,
  ) {
    final statuses = [for (final kind in kinds) ?shown.templateOf(kind)];
    if (statuses.isEmpty) return null;
    if (statuses.contains(TemplateStatus.rejected)) {
      return AppStrings.notificationTemplateRejected;
    }
    if (statuses.contains(TemplateStatus.pending)) {
      return AppStrings.notificationTemplatePending;
    }
    return AppStrings.notificationTemplateApproved;
  }

  List<Widget> _linked(NotificationOverview shown, {required bool canEdit}) {
    final settings = shown.settings!;
    final body = shown.settingsBody();
    final channel = shown.channel;
    final linkedAt = channel.linkedAt?.wall;
    final notice = canEdit ? _errorText : AppStrings.notificationOwnerOnly;
    return [
      if (notice != null) _notice(notice),
      AppCard(
        child: Row(
          children: [
            Expanded(
              child: Text(
                linkedAt == null
                    ? ''
                    : AppStrings.notificationLinkedOn(
                        linkedAt.month,
                        linkedAt.day,
                      ),
                style: AppTypography.bodyStrong,
              ),
            ),
            if (canEdit)
              Pressable(
                semanticLabel: AppStrings.more,
                onTap: _busy ? null : _openMore,
                child: const Icon(Icons.more_horiz),
              ),
          ],
        ),
      ),
      const SizedBox(height: AppSpacing.lg),
      AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.sm,
        ),
        child: Column(
          children: [
            for (final (field, label, kinds) in _kindRows) ...[
              _SwitchRow(
                label: label,
                hint: _templateText(shown, kinds),
                value: body[field] as bool,
                onChanged: canEdit ? (on) => _set(field, on) : null,
              ),
              if (field == 'reminder_enabled' && settings.reminderEnabled)
                _ChoiceRow(
                  label: AppStrings.notificationReminderTimeLabel,
                  value: settings.reminderTime,
                  onTap: canEdit
                      ? () => _pick<String>(
                          field: 'reminder_time',
                          choices: reminderTimeChoices,
                          current: settings.reminderTime,
                          label: (time) => time,
                        )
                      : null,
                ),
              if (field == 'next_visit_enabled' &&
                  settings.nextVisitEnabled) ...[
                _ChoiceRow(
                  label: AppStrings.notificationNextVisitWeeksLabel,
                  value: _weeks(settings.nextVisitAfterWeeks),
                  onTap: canEdit
                      ? () => _pick<int?>(
                          field: 'next_visit_after_weeks',
                          choices: nextVisitWeekChoices,
                          current: settings.nextVisitAfterWeeks,
                          label: _weeks,
                        )
                      : null,
                ),
                _ChoiceRow(
                  label: AppStrings.notificationCooldownLabel,
                  value: AppStrings.notificationDays(
                    settings.nextVisitCooldownDays,
                  ),
                  onTap: canEdit
                      ? () => _pick<int>(
                          field: 'next_visit_cooldown_days',
                          choices: cooldownDayChoices,
                          current: settings.nextVisitCooldownDays,
                          label: AppStrings.notificationDays,
                        )
                      : null,
                ),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Padding(
                    padding: EdgeInsets.only(bottom: AppSpacing.sm),
                    child: Text(
                      AppStrings.notificationNextVisitHint,
                      style: AppTypography.caption,
                    ),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
      const SizedBox(height: AppSpacing.lg),
      AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.sm,
        ),
        child: _SwitchRow(
          label: AppStrings.notificationSmsFallback,
          hint: channel.senderNumber == null
              ? AppStrings.notificationSmsFallbackHint
              : '${AppStrings.notificationSmsFallbackHint}\n${AppStrings.notificationSenderNumber(channel.senderNumber!)}',
          value: channel.smsFallbackEnabled,
          onChanged: canEdit ? (on) => _setFallback(shown, on) : null,
        ),
      ),
    ];
  }

  String _weeks(int? weeks) => weeks == null
      ? AppStrings.notificationWeeksAuto
      : AppStrings.notificationWeeks(weeks);
}

/// 준비 안내의 한 줄.
class _Step extends StatelessWidget {
  const _Step(this.number, this.text);

  final int number;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 20,
            child: Text('$number', style: AppTypography.caption),
          ),
          Expanded(child: Text(text, style: AppTypography.body)),
        ],
      ),
    );
  }
}

/// 이름 + 한 줄 설명 + 스위치.
class _SwitchRow extends StatelessWidget {
  const _SwitchRow({
    required this.label,
    required this.hint,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final String? hint;
  final bool value;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 이름은 스위치가 읽는다 — 글자를 한 번 더 읽지 않게 뺀다.
                ExcludeSemantics(child: Text(label, style: AppTypography.body)),
                if (hint case final hint?)
                  Text(hint, style: AppTypography.caption),
              ],
            ),
          ),
          AppSwitch(value: value, semanticLabel: label, onChanged: onChanged),
        ],
      ),
    );
  }
}

/// 스위치에 딸린 고르기 한 줄 — 누르면 목록이 뜬다.
class _ChoiceRow extends StatelessWidget {
  const _ChoiceRow({
    required this.label,
    required this.value,
    required this.onTap,
  });

  final String label;
  final String value;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: '$label $value',
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.only(
          left: AppSpacing.md,
          top: AppSpacing.xs,
          bottom: AppSpacing.sm,
        ),
        child: Row(
          children: [
            Expanded(child: Text(label, style: AppTypography.caption)),
            Text(value, style: AppTypography.body),
            const SizedBox(width: AppSpacing.xs),
            const Icon(Icons.chevron_right, size: 18),
          ],
        ),
      ),
    );
  }
}

/// 문자 대체의 발신번호 인증 — 번호로 인증번호를 받고 6자리를 확인한다. 끝나면 true 로 닫힌다.
class _SenderSheet extends ConsumerStatefulWidget {
  const _SenderSheet({required this.shopId});

  final int shopId;

  @override
  ConsumerState<_SenderSheet> createState() => _SenderSheetState();
}

class _SenderSheetState extends ConsumerState<_SenderSheet> {
  final _phone = TextEditingController();
  final _code = TextEditingController();
  bool _requested = false;
  bool _busy = false;
  String? _errorText;

  @override
  void dispose() {
    _phone.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<bool> _run(
    Future<void> Function(NotificationCommands commands) action,
  ) async {
    if (_busy) return false;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    String? error;
    try {
      await action(ref.read(notificationCommandsProvider));
    } catch (e) {
      error = messageFor(e);
    }
    if (!mounted) return false;
    setState(() {
      _busy = false;
      _errorText = error;
    });
    return error == null;
  }

  Future<void> _request() async {
    final ok = await _run(
      (commands) =>
          commands.requestSenderVerification(widget.shopId, _phone.text),
    );
    if (ok && mounted) setState(() => _requested = true);
  }

  Future<void> _confirm() async {
    final ok = await _run(
      (commands) => commands.confirmSender(
        widget.shopId,
        phone: _phone.text,
        code: _code.text,
      ),
    );
    if (ok && mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      // 자판이 올라와도 칸이 가려지지 않게.
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            AppStrings.notificationSenderTitle,
            style: AppTypography.bodyStrong,
          ),
          if (_errorText case final error?) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(error, style: AppTypography.caption),
          ],
          const SizedBox(height: AppSpacing.md),
          TextField(
            key: const Key('notification_sender_phone'),
            controller: _phone,
            enabled: !_requested && !_busy,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              labelText: AppStrings.notificationSenderPhoneLabel,
              helperText: AppStrings.notificationSenderPhoneHint,
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          if (!_requested)
            AppButton(
              label: AppStrings.notificationRequestToken,
              filled: true,
              busy: _busy,
              onPressed: _senderPhone.hasMatch(_phone.text) && !_busy
                  ? _request
                  : null,
            )
          else ...[
            TextField(
              key: const Key('notification_sender_code'),
              controller: _code,
              enabled: !_busy,
              keyboardType: TextInputType.number,
              maxLength: 6,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                labelText: AppStrings.notificationSenderCodeLabel,
                counterText: '',
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              label: AppStrings.notificationSenderConfirm,
              filled: true,
              busy: _busy,
              onPressed: _sixDigits.hasMatch(_code.text) && !_busy
                  ? _confirm
                  : null,
            ),
          ],
        ],
      ),
    );
  }
}
