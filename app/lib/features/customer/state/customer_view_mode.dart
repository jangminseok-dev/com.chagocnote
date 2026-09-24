import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/prefs_store.dart';
import '../../../core/storage/view_mode_controller.dart';

enum CustomerViewMode { list, grid }

/// 고객 목록의 보기 방식. 기본은 목록이고, 마지막으로 고른 것을 기기에
/// 기억한다(설계 2절).
final customerViewModeProvider =
    AsyncNotifierProvider<
      ViewModeController<CustomerViewMode>,
      CustomerViewMode
    >(
      () => ViewModeController(
        key: PrefsKeys.customerViewMode,
        values: CustomerViewMode.values,
        fallback: CustomerViewMode.list,
      ),
    );
