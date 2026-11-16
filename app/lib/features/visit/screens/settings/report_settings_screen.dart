import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/async_body.dart';
import '../../../../core/error/error_messages.dart';
import '../../../../core/router/screen_keys.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_back_button.dart';
import '../../../../design/widgets/app_card.dart';
import '../../../../design/widgets/app_choice_chip.dart';
import '../../../../design/widgets/app_switch.dart';
import '../../../../l10n/app_strings.dart';
import '../../../auth/state/shop_selection.dart';
import '../../api/report_models.dart';
import '../../state/report_commands.dart';
import '../../state/report_providers.dart';
import 'report_family_section.dart';
import 'report_guardian_previews.dart';
import 'report_review_section.dart';

/// 켜고 끄는 항목 넷(목업 ⑤의 순서) — 서버의 칸 이름, 이름, 설명.
const _items = [
  ('show_menus', AppStrings.reportItemMenus, AppStrings.reportItemMenusHint),
  ('show_amount', AppStrings.reportItemAmount, AppStrings.reportItemAmountHint),
  ('show_weight', AppStrings.reportItemWeight, AppStrings.reportItemWeightHint),
  (
    'show_shop_info',
    AppStrings.reportItemShopInfo,
    AppStrings.reportItemShopInfoHint,
  ),
];

/// 설정 → 알림장(⑤ 설계 2절·9.1, 목업 ⑤) — 링크가 열려 있는 기간(7일·30일·계속)과 알림장에 보여 줄
/// 항목 넷.
///
/// [저장] 버튼이 없다 — 누르면 바로 다섯 칸 전체를 보낸다. 낙관적으로 그리지 않고, 다시 읽은 서버 값으로
/// 그린다. 바꾸는 것은 사장만이고(`shop:update`) 직원에게는 읽기 전용이다.
class ReportSettingsScreen extends ConsumerStatefulWidget {
  const ReportSettingsScreen({super.key});

  @override
  ConsumerState<ReportSettingsScreen> createState() =>
      _ReportSettingsScreenState();
}

class _ReportSettingsScreenState extends ConsumerState<ReportSettingsScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  /// 화면이 보이는 서버 값 [shown]에서 [field] 한 칸만 바꿔 전체를 보낸다.
  Future<void> _set(ReportSettings shown, String field, Object? value) =>
      _save(ReportSettings.fromJson({...shown.toJson(), field: value}));

  /// [next] 로 전체(일곱 칸)를 보낸다. 성공하든 실패하든 `updateSettings`가 설정을 다시 읽게 하고, 화면은
  /// 그 값으로 다시 그린다.
  Future<void> _save(ReportSettings next) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    // 화면의 값이 방금 읽은 것이 아니면(다시 읽는 중, 다시 읽기 실패로 이전 내용) 누르지 않은 것으로
    // 친다 — 낡은 값 위에 덮어 보내면 방금 바꾼 칸을 되돌린다.
    final settings = ref.read(reportSettingsProvider(shopId));
    if (settings.isLoading || settings.hasError) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    String? error;
    try {
      await ref.read(reportCommandsProvider).updateSettings(shopId, next);
    } catch (e) {
      error = messageFor(e);
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _errorText = error;
    });
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final settings = shopId == null
        ? const AsyncValue<ReportSettings>.loading()
        : ref.watch(reportSettingsProvider(shopId));
    final canEdit = ref.watch(isOwnerProvider);
    return Scaffold(
      key: ScreenKeys.reportSettings,
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
                      AppStrings.reportSettingsTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: AsyncBody<ReportSettings>(
                  value: settings,
                  onRetry: () =>
                      ref.invalidate(reportSettingsProvider(shopId!)),
                  builder: (data) => _body(
                    data,
                    canEdit: canEdit,
                    locked: _busy || settings.isLoading || settings.hasError,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(
    ReportSettings shown, {
    required bool canEdit,
    required bool locked,
  }) {
    final json = shown.toJson();
    // 맨 위 한 줄 — 직원에게는 읽기 전용 안내, 사장에게는 마지막 실패 문구.
    final notice = canEdit ? _errorText : AppStrings.reportSettingsOwnerOnly;
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        0,
        AppSpacing.lg,
        AppSpacing.xxl,
      ),
      children: [
        if (notice != null)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: Text(notice, style: AppTypography.caption),
          ),
        const Text(
          AppStrings.reportLinkDaysLabel,
          style: AppTypography.caption,
        ),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          children: [
            for (final days in const [7, 30, null])
              AppChoiceChip(
                label: AppStrings.reportLinkDays(days),
                selected: days == shown.linkDays,
                // 이미 고른 기간은 눌리지 않는다(다시 보내지 않는다).
                onTap: canEdit && days != shown.linkDays
                    ? () => _set(shown, 'link_days', days)
                    : null,
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        const Text(AppStrings.reportLinkDaysHint, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xl),
        const Text(
          AppStrings.reportShowItemsLabel,
          style: AppTypography.caption,
        ),
        const SizedBox(height: AppSpacing.sm),
        AppCard(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.sm,
          ),
          child: Column(
            children: [
              for (final (field, label, hint) in _items) ...[
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // 이름은 스위치가 읽는다 — 글자를 한 번 더 읽지 않게 뺀다.
                          ExcludeSemantics(
                            child: Text(label, style: AppTypography.body),
                          ),
                          Text(hint, style: AppTypography.caption),
                        ],
                      ),
                    ),
                    AppSwitch(
                      value: json[field] as bool,
                      semanticLabel: label,
                      onChanged: canEdit
                          ? (on) => _set(shown, field, on)
                          : null,
                    ),
                  ],
                ),
                // 몸무게는 기본이 꺼짐이라 대부분의 매장에서 보호자에게 안 보인다 — 왜 안 보이는지와 켜면 무엇이
                // 보이는지를 스위치 바로 아래에서 보인다(⑫ 설계 3.3).
                if (field == 'show_weight') WeightPreview(on: shown.showWeight),
              ],
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        const Text(
          AppStrings.reportShowItemsHint,
          style: AppTypography.caption,
        ),
        const SizedBox(height: AppSpacing.xl),
        ReportReviewSection(
          shown: shown,
          shopName: ref.watch(shopNameProvider),
          canEdit: canEdit,
          locked: locked,
          onSave: _save,
        ),
        if (_shopId case final shopId?) ...[
          const SizedBox(height: AppSpacing.xl),
          ReportFamilySection(shopId: shopId, canEdit: canEdit),
        ],
      ],
    );
  }
}
