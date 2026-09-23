import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../home/state/today_provider.dart';

/// 캘린더 탭에서 고른 날. 처음에는 오늘이다. 홈의 + 버튼이 이 날로 예약
/// 등록을 연다(달력에서 날짜를 고른 뒤 +, 설계 9.1).
class SelectedDate extends Notifier<DateTime> {
  @override
  DateTime build() {
    final today = ref.watch(todayProvider);
    return DateTime(today.year, today.month, today.day);
  }

  void select(DateTime date) =>
      state = DateTime(date.year, date.month, date.day);
}

final selectedDateProvider = NotifierProvider<SelectedDate, DateTime>(
  SelectedDate.new,
);
