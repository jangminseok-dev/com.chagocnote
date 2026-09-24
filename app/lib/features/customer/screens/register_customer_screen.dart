import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/shop_selection.dart';
import '../../../core/time/today_provider.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_input.dart';
import '../state/customer_providers.dart';
import 'customer_form.dart';
import 'pet_form.dart';

/// 새 고객 등록 — 전화번호 → 보호자 → 반려동물 3단계(설계 8.1).
///
/// 1단계에서 번호가 완성되면 바로 조회해, 이미 있는 번호면 알려 주고 그
/// 보호자에게 반려동물 추가로 건너뛰게 한다. 세 단계는 한 화면 안에서 오가며,
/// 앞 단계로 돌아가도 적은 값이 남는다.
class RegisterCustomerScreen extends ConsumerStatefulWidget {
  const RegisterCustomerScreen({super.key, this.pickForReservation = false});

  /// 예약 ①(고객 찾기)에서 열었으면 등록한 고객 ID 를 돌려주며 닫는다 —
  /// 예약 ②로 바로 넘어간다. 아니면 새 아이의 상세로 간다.
  final bool pickForReservation;

  @override
  ConsumerState<RegisterCustomerScreen> createState() =>
      _RegisterCustomerScreenState();
}

class _RegisterCustomerScreenState
    extends ConsumerState<RegisterCustomerScreen> {
  final _phone = TextEditingController();

  int _step = 0;

  /// 조회를 마친 번호와 그 결과. 번호가 바뀌면 비운다.
  String? _checkedPhone;
  CustomerLookup? _found;
  bool _checking = false;

  /// 번호 조회는 입력마다 나갈 수 있다 — 늦게 온 옛 번호의 결과를 버리려고 센다.
  int _lookupSeq = 0;

  /// 마지막으로 본 입력(숫자만). 커서만 옮긴 변경은 건너뛴다.
  String _lastDigits = '';

  CustomerFields? _customer;
  bool _busy = false;
  String? _errorText;

  int? get _shopId => ref.read(selectedShopIdProvider);

  String get _digits => phoneDigits(_phone.text);

  @override
  void initState() {
    super.initState();
    _phone.addListener(_onPhoneChanged);
  }

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  void _onPhoneChanged() {
    final digits = _digits;
    if (digits == _lastDigits) return;
    _lastDigits = digits;
    // 번호가 바뀔 때마다 순번을 올려, 도는 중인 옛 조회의 결과를 버린다(A2).
    _lookupSeq++;
    setState(() {
      _checking = false;
      _checkedPhone = null;
      _found = null;
      _errorText = null;
    });
    if (isValidPhone(digits)) _lookup(digits);
  }

  Future<void> _lookup(String digits) async {
    final shopId = _shopId;
    if (shopId == null) return;
    final seq = _lookupSeq;
    setState(() => _checking = true);
    try {
      final found = await ref
          .read(customerCommandsProvider)
          .lookup(shopId, digits);
      if (!mounted || seq != _lookupSeq) return;
      setState(() {
        _checking = false;
        _checkedPhone = digits;
        _found = found;
      });
    } catch (e) {
      if (!mounted || seq != _lookupSeq) return;
      setState(() {
        _checking = false;
        _errorText = messageFor(e);
      });
    }
  }

  /// 1단계의 "다음". 조회가 실패했으면 다시 조회하고, 없는 번호일 때만 넘어간다.
  Future<void> _nextFromPhone() async {
    final digits = _digits;
    if (_checkedPhone != digits) {
      setState(() => _errorText = null);
      await _lookup(digits);
      if (!mounted || _checkedPhone != digits) return;
    }
    if (_found == null) setState(() => _step = 1);
  }

  Future<void> _register(PetFields pet) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final detail = await ref
          .read(customerCommandsProvider)
          .register(shopId, customer: _customer!, pet: pet);
      if (!mounted) return;
      if (widget.pickForReservation) {
        context.pop(detail.customer.customerId);
      } else {
        context.pushReplacement('/pets/${detail.pets.first.petId}');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
        // 그사이 같은 번호가 등록됐으면(C2) 1단계로 돌아가 다시 조회되게 한다.
        if (e is ApiException && e.code == 'CUSTOMER_PHONE_TAKEN') {
          _checkedPhone = null;
        }
      });
    }
  }

  void _back() {
    if (_step == 0) {
      context.pop();
    } else {
      setState(() {
        _step--;
        _errorText = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = switch (_step) {
      0 => AppStrings.registerStepTitle(AppStrings.registerStepPhone, 1),
      1 => AppStrings.registerStepTitle(AppStrings.registerStepOwner, 2),
      _ => AppStrings.registerStepTitle(AppStrings.registerStepPet, 3),
    };

    return PopScope(
      // 시스템 뒤로 가기도 앞 단계로 돌아간다.
      canPop: _step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: Scaffold(
        key: ScreenKeys.registerCustomer,
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
                    0,
                  ),
                  child: Row(
                    children: [
                      AppBackButton(onTap: _back),
                      const SizedBox(width: AppSpacing.sm),
                      Text(title, style: AppTypography.titleKo),
                    ],
                  ),
                ),
                Expanded(
                  // 단계를 오가도 폼의 입력이 남도록 세 단계를 모두 쥐고 있는다.
                  child: IndexedStack(
                    index: _step,
                    children: [_phoneStep(), _ownerStep(), _petStep()],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _phoneStep() {
    final found = _found;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _phone,
            autofocus: true,
            keyboardType: TextInputType.phone,
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'[0-9\- ]')),
              LengthLimitingTextInputFormatter(20),
            ],
            decoration: const InputDecoration(
              labelText: AppStrings.ownerPhoneLabel,
              hintText: AppStrings.phoneHint,
            ),
          ),
          if (_checking) ...[
            const SizedBox(height: AppSpacing.md),
            const LinearProgressIndicator(),
          ],
          if (found != null) ...[
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              width: double.infinity,
              child: AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppStrings.lookupFound(found.name, found.petNames),
                      style: AppTypography.body,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    AppButton(
                      label: AppStrings.addPetToExisting,
                      filled: true,
                      onPressed: () => context.pushReplacement(
                        '/customers/${found.customerId}/pets/new',
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (_step == 0 && _errorText != null) ...[
            const SizedBox(height: AppSpacing.md),
            Text(_errorText!, style: AppTypography.caption),
          ],
          const SizedBox(height: AppSpacing.xl),
          Center(
            child: AppButton(
              label: AppStrings.next,
              filled: true,
              busy: _checking,
              onPressed: isValidPhone(_digits) && found == null && !_checking
                  ? _nextFromPhone
                  : null,
            ),
          ),
        ],
      ),
    );
  }

  Widget _ownerStep() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: CustomerForm(
        fixedPhone: _checkedPhone ?? _digits,
        submitLabel: AppStrings.next,
        busy: false,
        onSubmit: (fields) => setState(() {
          _customer = fields;
          _step = 2;
        }),
      ),
    );
  }

  Widget _petStep() {
    final shopId = _shopId;
    if (shopId == null) return const SizedBox.shrink();
    return ref
        .watch(conditionTypesProvider(shopId))
        .when(
          data: (types) => SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: PetForm(
              conditionTypes: types,
              today: ref.watch(todayProvider),
              submitLabel: AppStrings.save,
              busy: _busy,
              errorText: _step == 2 ? _errorText : null,
              onSubmit: _register,
            ),
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(messageFor(error), style: AppTypography.body),
                const SizedBox(height: AppSpacing.lg),
                AppButton(
                  label: AppStrings.retry,
                  onPressed: () =>
                      ref.invalidate(conditionTypesProvider(shopId)),
                ),
              ],
            ),
          ),
        );
  }
}
