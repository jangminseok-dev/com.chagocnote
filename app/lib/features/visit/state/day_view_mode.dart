import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';

enum DayViewMode { list, timeline }

/// 하루 화면의 보기 방식. 기본은 목록이고, 마지막으로 고른 것을 기기에
/// 기억한다(설계 2절).
class DayViewModeController extends AsyncNotifier<DayViewMode> {
  @override
  Future<DayViewMode> build() async {
    final saved = await ref.read(prefsStoreProvider).readDayViewMode();
    return saved == DayViewMode.timeline.name
        ? DayViewMode.timeline
        : DayViewMode.list;
  }

  Future<void> select(DayViewMode mode) async {
    state = AsyncData(mode);
    await ref.read(prefsStoreProvider).writeDayViewMode(mode.name);
  }
}

final dayViewModeProvider =
    AsyncNotifierProvider<DayViewModeController, DayViewMode>(
      DayViewModeController.new,
    );
