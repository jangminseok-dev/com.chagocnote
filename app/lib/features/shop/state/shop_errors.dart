import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../auth/state/session_controller.dart';

/// 매장 범위 호출 공통 오류 처리.
///
/// 어떤 매장 범위 호출이든 `NOT_A_MEMBER`(제거되었거나 역할이 바뀐 경우)를
/// 받을 수 있다. 이때 매장을 로컬에서 지우지 않고 본인 정보만 다시
/// 불러와 라우터가 다시 평가하게 한다 — 강등된 멤버는 여전히 멤버라 그대로
/// 머무르고, 제거된 멤버는 라우터가 알아서 내보낸다. 그 외 오류는 그대로
/// 다시 던져서 화면이 문구로 보여주게 한다.
Future<T> runShopScoped<T>(Ref ref, Future<T> Function() action) async {
  try {
    return await action();
  } on ApiException catch (e) {
    if (e.code == 'NOT_A_MEMBER') {
      await ref.read(sessionControllerProvider.notifier).reloadMe();
    }
    rethrow;
  }
}
