import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/error_messages.dart';
import '../../../../core/router/screen_keys.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens/app_colors.dart';
import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_back_button.dart';
import '../../../../design/widgets/app_button.dart';
import '../../../../design/widgets/app_card.dart';
import '../../../../design/widgets/app_choice_chip.dart';
import '../../../../design/widgets/app_error_retry.dart';
import '../../../../design/widgets/app_sheet.dart';
import '../../../../design/widgets/pressable.dart';
import '../../../../l10n/app_strings.dart';
import '../../../auth/state/shop_selection.dart';
import '../../api/visit_models.dart';
import '../../state/record_rules.dart';
import '../../state/visit_commands.dart';
import '../../state/visit_form_rules.dart';
import '../../state/visit_providers.dart';

/// 설정 → 메뉴(사장만) — 메뉴표 추가·이름·기본 소요·정가·순서·보관(설계 9.1, ④ 설계 10.1).
/// 정가는 기록 화면이 메뉴 금액을 미리 채우는 값이다.
/// 메뉴는 지우지 않고 보관한다(지난 방문이 가리킨다).
class MenuSettingsScreen extends ConsumerStatefulWidget {
  const MenuSettingsScreen({super.key});

  @override
  ConsumerState<MenuSettingsScreen> createState() => _MenuSettingsScreenState();
}

class _MenuSettingsScreenState extends ConsumerState<MenuSettingsScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  /// 쓰기 하나를 돌린다. 도는 동안 다른 쓰기를 막고, 실패하면 문구를 보인다.
  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action();
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _add() async {
    final shopId = _shopId;
    if (shopId == null) return;
    final value = await AppSheet.show<_MenuValue>(
      context,
      builder: (context) => const _MenuSheet(initial: null),
    );
    if (value == null || !mounted) return;
    await _run(
      () => ref
          .read(visitCommandsProvider)
          .createMenu(
            shopId,
            name: value.name,
            defaultDurationMinutes: value.durationMinutes,
            price: value.price,
          ),
    );
  }

  Future<void> _edit(Menu menu) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final value = await AppSheet.show<_MenuValue>(
      context,
      builder: (context) => _MenuSheet(initial: menu),
    );
    if (value == null || !mounted) return;
    await _run(
      () => ref
          .read(visitCommandsProvider)
          .updateMenu(
            shopId,
            menu.menuId,
            name: value.name,
            defaultDurationMinutes: value.durationMinutes,
            sortOrder: menu.sortOrder,
            price: value.price,
          ),
    );
  }

  /// 이웃과 순서값을 맞바꾼다(두 번 고친다). [aMovesUp]은 [a]가 위로 가는
  /// 눌림(▲)인지 아래로 가는 눌림(▼)인지다 — 둘째 PUT이 실패해 두 메뉴의
  /// 순서값이 같아진 뒤에는 단순히 맞바꿔서는(값이 같아 그대로) 풀리지
  /// 않으므로, 그 경우 위로 갈 메뉴에 그 값을, 아래로 갈 메뉴에 그 값+1을
  /// 보낸다.
  Future<void> _swap(Menu a, Menu b, {required bool aMovesUp}) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final commands = ref.read(visitCommandsProvider);
    final int aOrder;
    final int bOrder;
    if (a.sortOrder == b.sortOrder) {
      final v = a.sortOrder;
      aOrder = aMovesUp ? v : v + 1;
      bOrder = aMovesUp ? v + 1 : v;
    } else {
      aOrder = b.sortOrder;
      bOrder = a.sortOrder;
    }
    await _run(() async {
      await commands.updateMenu(
        shopId,
        a.menuId,
        name: a.name,
        defaultDurationMinutes: a.defaultDurationMinutes,
        sortOrder: aOrder,
        price: a.price,
      );
      await commands.updateMenu(
        shopId,
        b.menuId,
        name: b.name,
        defaultDurationMinutes: b.defaultDurationMinutes,
        sortOrder: bOrder,
        price: b.price,
      );
    });
  }

  Future<void> _archive(Menu menu) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            AppStrings.archiveMenuConfirm,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.archiveMenu,
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
    await _run(
      () => ref.read(visitCommandsProvider).archiveMenu(shopId, menu.menuId),
    );
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final key = (shopId: shopId ?? 0, includeArchived: false);
    final menus = shopId == null
        ? const AsyncValue<List<Menu>>.loading()
        : ref.watch(menusProvider(key));
    return Scaffold(
      key: ScreenKeys.settingsMenus,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  AppSpacing.sm,
                ),
                child: Row(
                  children: [
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    const Text(
                      AppStrings.settingsMenus,
                      style: AppTypography.titleKo,
                    ),
                    const Spacer(),
                    AppButton(
                      label: AppStrings.addMenu,
                      onPressed: _busy ? null : _add,
                    ),
                  ],
                ),
              ),
              if (_errorText != null)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                  ),
                  child: Text(_errorText!, style: AppTypography.caption),
                ),
              Expanded(
                child: menus.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => AppErrorRetry(
                    message: messageFor(error),
                    onRetry: () => ref.invalidate(menusProvider(key)),
                  ),
                  data: (items) {
                    final sorted = [...items]
                      ..sort((a, b) => a.sortOrder.compareTo(b.sortOrder));
                    if (sorted.isEmpty) {
                      return const Center(
                        child: Padding(
                          padding: EdgeInsets.all(AppSpacing.xl),
                          child: Text(
                            AppStrings.menusEmpty,
                            style: AppTypography.body,
                            textAlign: TextAlign.center,
                          ),
                        ),
                      );
                    }
                    return ListView(
                      padding: const EdgeInsets.fromLTRB(
                        AppSpacing.lg,
                        0,
                        AppSpacing.lg,
                        AppSpacing.xxl,
                      ),
                      children: [
                        for (var i = 0; i < sorted.length; i++)
                          Padding(
                            padding: const EdgeInsets.only(
                              bottom: AppSpacing.sm,
                            ),
                            child: _MenuRow(
                              menu: sorted[i],
                              busy: _busy,
                              onUp: i == 0
                                  ? null
                                  : () => _swap(
                                      sorted[i],
                                      sorted[i - 1],
                                      aMovesUp: true,
                                    ),
                              onDown: i == sorted.length - 1
                                  ? null
                                  : () => _swap(
                                      sorted[i],
                                      sorted[i + 1],
                                      aMovesUp: false,
                                    ),
                              onEdit: () => _edit(sorted[i]),
                              onArchive: () => _archive(sorted[i]),
                            ),
                          ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MenuRow extends StatelessWidget {
  const _MenuRow({
    required this.menu,
    required this.busy,
    required this.onUp,
    required this.onDown,
    required this.onEdit,
    required this.onArchive,
  });

  final Menu menu;
  final bool busy;
  final VoidCallback? onUp;
  final VoidCallback? onDown;
  final VoidCallback onEdit;
  final VoidCallback onArchive;

  @override
  Widget build(BuildContext context) {
    final duration = menu.defaultDurationMinutes;
    final price = menu.price;
    return AppCard(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.xs,
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(menu.name, style: AppTypography.bodyStrong),
                Text(
                  '${duration == null ? AppStrings.useShopDefault : AppStrings.durationText(duration)}'
                  ' · ${price == null ? AppStrings.priceUnset : AppStrings.wonText(price)}',
                  style: AppTypography.caption,
                ),
              ],
            ),
          ),
          Pressable(
            semanticLabel: '${AppStrings.moveUp} ${menu.name}',
            onTap: busy ? null : onUp,
            child: Icon(
              Icons.keyboard_arrow_up,
              size: 20,
              color: onUp == null ? AppColors.line : AppColors.ink,
            ),
          ),
          Pressable(
            semanticLabel: '${AppStrings.moveDown} ${menu.name}',
            onTap: busy ? null : onDown,
            child: Icon(
              Icons.keyboard_arrow_down,
              size: 20,
              color: onDown == null ? AppColors.line : AppColors.ink,
            ),
          ),
          Pressable(
            semanticLabel: '${AppStrings.edit} ${menu.name}',
            onTap: busy ? null : onEdit,
            child: const Icon(Icons.edit_outlined, size: 18),
          ),
          Pressable(
            semanticLabel: '${AppStrings.archiveMenu} ${menu.name}',
            onTap: busy ? null : onArchive,
            child: const Icon(Icons.archive_outlined, size: 18),
          ),
        ],
      ),
    );
  }
}

class _MenuValue {
  const _MenuValue(this.name, this.durationMinutes, this.price);

  final String name;

  /// null 이면 매장 기본 소요.
  final int? durationMinutes;

  /// null 이면 가격 미정.
  final int? price;
}

/// 이름·기본 소요·정가를 적는 시트(추가·수정).
class _MenuSheet extends StatefulWidget {
  const _MenuSheet({required this.initial});

  final Menu? initial;

  @override
  State<_MenuSheet> createState() => _MenuSheetState();
}

class _MenuSheetState extends State<_MenuSheet> {
  late final _name = TextEditingController(text: widget.initial?.name ?? '');
  late final _price = TextEditingController(
    text: widget.initial?.price?.toString() ?? '',
  );
  late int? _duration = widget.initial?.defaultDurationMinutes;
  String? _nameError;
  String? _priceError;

  @override
  void dispose() {
    _name.dispose();
    _price.dispose();
    super.dispose();
  }

  void _submit() {
    final name = _name.text.trim();
    // 숫자만 받으니 비었거나 숫자다. 비우면 가격 미정.
    final price = int.tryParse(_price.text);
    setState(() {
      _nameError = name.isEmpty ? AppStrings.menuNameRequired : null;
      _priceError = price != null && price > maxAmount
          ? AppStrings.amountTooLarge
          : null;
    });
    if (_nameError != null || _priceError != null) return;
    Navigator.of(context).pop(_MenuValue(name, _duration, price));
  }

  @override
  Widget build(BuildContext context) {
    final duration = _duration;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          widget.initial == null ? AppStrings.addMenu : AppStrings.editMenu,
          style: AppTypography.titleKo,
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: _name,
          autofocus: true,
          inputFormatters: [LengthLimitingTextInputFormatter(30)],
          decoration: InputDecoration(
            hintText: AppStrings.menuNameHint,
            errorText: _nameError,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            const Text(
              AppStrings.menuDefaultDurationLabel,
              style: AppTypography.body,
            ),
            const SizedBox(width: AppSpacing.sm),
            AppChoiceChip(
              label: AppStrings.useShopDefault,
              selected: duration == null,
              onTap: () =>
                  setState(() => _duration = duration == null ? 60 : null),
            ),
            const Spacer(),
            if (duration != null) ...[
              Pressable(
                semanticLabel: AppStrings.shorter,
                onTap: () => setState(
                  () => _duration = stepDuration(duration, longer: false),
                ),
                onLongPress: () => setState(
                  () => _duration = stepDuration(
                    duration,
                    longer: false,
                    long: true,
                  ),
                ),
                child: const Icon(Icons.remove, size: 18),
              ),
              Text(
                AppStrings.durationText(duration),
                style: AppTypography.bodyStrong,
              ),
              Pressable(
                semanticLabel: AppStrings.longer,
                onTap: () => setState(
                  () => _duration = stepDuration(duration, longer: true),
                ),
                onLongPress: () => setState(
                  () => _duration = stepDuration(
                    duration,
                    longer: true,
                    long: true,
                  ),
                ),
                child: const Icon(Icons.add, size: 18),
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: _price,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(9),
          ],
          decoration: InputDecoration(
            labelText: AppStrings.menuPriceLabel,
            hintText: AppStrings.priceUnset,
            suffixText: AppStrings.wonUnit,
            errorText: _priceError,
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        AppButton(label: AppStrings.save, filled: true, onPressed: _submit),
      ],
    );
  }
}
