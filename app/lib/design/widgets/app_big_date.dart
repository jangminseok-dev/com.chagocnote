import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// 큰 세리프 날짜 숫자 + 기울인 영문 월·요일.
///
/// `intl` 없이 영문 월/요일 이름 표를 직접 들고 있는다(요구사항 — 이 두
/// 표 말고는 지역화하지 않는다).
class AppBigDate extends StatelessWidget {
  const AppBigDate({super.key, required this.date});

  final DateTime date;

  static const _months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  static const _weekdays = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];

  /// 일(day) 숫자만 뽑아낸 문자열("22").
  String get dayText => date.day.toString();

  /// 영문 월 이름("September").
  String get monthText => _months[date.month - 1];

  /// 영문 요일 이름("Tuesday").
  String get weekdayText => weekdayName(date.weekday);

  /// [weekday](월=1 … 일=7)의 영문 이름. 하루 화면의 머리도 쓴다.
  static String weekdayName(int weekday) => _weekdays[weekday - 1];

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(dayText, style: AppTypography.bigNumeral),
        const SizedBox(width: AppSpacing.sm),
        Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.xs),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(monthText, style: AppTypography.italicLabel),
              Text(
                weekdayText,
                style: AppTypography.italicLabel.copyWith(
                  fontSize: 14,
                  height: 1.2,
                  color: AppColors.secondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
