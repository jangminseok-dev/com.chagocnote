import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/prefs_store.dart';
import '../../../core/storage/view_mode_controller.dart';

enum CalendarViewMode { calendar, feed }

/// 캘린더 탭의 [달력 / 피드](④ 설계 10.1 ①). 기본은 달력이고, 마지막으로 고른 것을 기기에 기억한다.
final calendarViewModeProvider =
    AsyncNotifierProvider<
      ViewModeController<CalendarViewMode>,
      CalendarViewMode
    >(
      () => ViewModeController(
        key: PrefsKeys.calendarViewMode,
        values: CalendarViewMode.values,
        fallback: CalendarViewMode.calendar,
      ),
    );
