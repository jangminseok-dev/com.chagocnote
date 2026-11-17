import 'package:flutter/material.dart';

import '../../../../design/tokens/app_spacing.dart';
import '../../../../design/tokens/app_typography.dart';
import '../../../../design/widgets/app_button.dart';
import '../../../../design/widgets/app_sheet.dart';
import '../../../../design/widgets/app_stepper.dart';
import '../../../../l10n/app_strings.dart';

/// 매장의 다시 올 때 값(⑬) 하나를 고르는 시트 — `[−] 값 [+]`, 고르는 대로 바뀌는 아래 글, [저장].
/// [저장]이면 고른 값, 닫으면 null(아무것도 보내지 않는다). 예약 설정·완료 시트·다시 올 때 목록이 함께 쓴다.
Future<int?> pickRevisitNumber(
  BuildContext context, {
  required String title,
  required int initial,
  required int min,
  required int max,
  required String Function(int value) unit,
  required String Function(int value) note,
}) => AppSheet.show<int>(
  context,
  builder: (context) {
    var value = initial;
    return StatefulBuilder(
      builder: (context, setState) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(title, style: AppTypography.bodyStrong, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.lg),
          AppStepper(
            value: value,
            min: min,
            max: max,
            label: unit,
            decreaseLabel: AppStrings.stepDown,
            increaseLabel: AppStrings.stepUp,
            onChanged: (v) => setState(() => value = v),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(note(value), style: AppTypography.caption, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.save,
            filled: true,
            onPressed: () => Navigator.of(context).pop(value),
          ),
        ],
      ),
    );
  },
);

/// 매장의 기본 간격(1~52주) — 예약 설정과 완료 시트의 `기본 간격 바꾸기` 가 함께 쓴다.
Future<int?> pickDefaultCycleWeeks(BuildContext context, int initial) => pickRevisitNumber(
  context,
  title: AppStrings.revisitDefaultWeeksLabel,
  initial: initial,
  min: 1,
  max: 52,
  unit: AppStrings.weeksUnit,
  note: AppStrings.revisitDefaultWeeksNote,
);

/// '곧'으로 치는 날 수(1~30일) — 예약 설정과 다시 올 때 목록의 `바꾸기` 가 함께 쓴다.
Future<int?> pickSoonDays(BuildContext context, int initial) => pickRevisitNumber(
  context,
  title: AppStrings.revisitSoonDaysLabel,
  initial: initial,
  min: 1,
  max: 30,
  unit: AppStrings.daysUnit,
  note: AppStrings.revisitSoonDaysNote,
);
