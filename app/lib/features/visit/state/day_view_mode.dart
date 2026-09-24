import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/prefs_store.dart';
import '../../../core/storage/view_mode_controller.dart';

enum DayViewMode { list, timeline }

/// 하루 화면의 보기 방식. 기본은 목록이고, 마지막으로 고른 것을 기기에
/// 기억한다(설계 2절).
final dayViewModeProvider =
    AsyncNotifierProvider<ViewModeController<DayViewMode>, DayViewMode>(
      () => ViewModeController(
        key: PrefsKeys.dayViewMode,
        values: DayViewMode.values,
        fallback: DayViewMode.list,
      ),
    );
