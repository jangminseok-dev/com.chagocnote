import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../home/state/today_provider.dart';
import '../api/customer_models.dart';
import '../state/customer_commands.dart';
import '../state/customer_providers.dart';
import 'pet_form.dart';

/// 반려동물 추가(기존 보호자에게)와 수정. 폼은 등록 3단계와 같다.
class PetFormScreen extends ConsumerStatefulWidget {
  const PetFormScreen.add({super.key, required int this.customerId})
    : petId = null;

  const PetFormScreen.edit({super.key, required int this.petId})
    : customerId = null;

  final int? customerId;
  final int? petId;

  @override
  ConsumerState<PetFormScreen> createState() => _PetFormScreenState();
}

class _PetFormScreenState extends ConsumerState<PetFormScreen> {
  bool _busy = false;
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  Future<void> _submit(PetFields fields) async {
    final shopId = _shopId;
    if (shopId == null || _busy) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    final commands = ref.read(customerCommandsProvider);
    try {
      final petId = widget.petId;
      if (petId != null) {
        await commands.updatePet(shopId, petId, fields);
        if (mounted) context.pop();
      } else {
        final added = await commands.addPet(shopId, widget.customerId!, fields);
        if (mounted) context.pushReplacement('/pets/${added.pet.petId}');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final petId = widget.petId;
    final types = shopId == null
        ? const AsyncValue<List<ConditionType>>.loading()
        : ref.watch(conditionTypesProvider(shopId));
    final pet = petId == null
        ? const AsyncValue<PetDetail?>.data(null)
        : shopId == null
        ? const AsyncValue<PetDetail?>.loading()
        : ref.watch(petDetailProvider((shopId: shopId, petId: petId)));

    Widget body;
    if (types.hasError || pet.hasError) {
      body = Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              messageFor(types.error ?? pet.error!),
              style: AppTypography.body,
            ),
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              label: AppStrings.retry,
              onPressed: () {
                ref.invalidate(conditionTypesProvider(shopId!));
                if (petId != null) {
                  ref.invalidate(
                    petDetailProvider((shopId: shopId, petId: petId)),
                  );
                }
              },
            ),
          ],
        ),
      );
    } else if (!types.hasValue || !pet.hasValue) {
      body = const Center(child: CircularProgressIndicator());
    } else {
      body = SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: PetForm(
          initial: pet.value?.pet,
          conditionTypes: types.value!,
          today: ref.watch(todayProvider),
          submitLabel: AppStrings.save,
          busy: _busy,
          errorText: _errorText,
          onSubmit: _submit,
        ),
      );
    }

    return Scaffold(
      key: ScreenKeys.petForm,
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
                    const AppBackButton(),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      petId == null
                          ? AppStrings.addPetTitle
                          : AppStrings.editPetTitle,
                      style: AppTypography.titleKo,
                    ),
                  ],
                ),
              ),
              Expanded(child: body),
            ],
          ),
        ),
      ),
    );
  }
}
