import 'dart:ui';

import 'package:chagocnote/core/proxy/share_sheet.dart';

/// 공유 시트 대역 — 받은 글과 버튼 사각형을 적어 둔다. 테스트가 `shareSheetProvider`를 이걸로 override 한다.
class FakeShareSheet implements ShareSheet {
  final shared = <String>[];
  final origins = <Rect>[];

  /// 있으면 적지 않고 이것을 던진다(채널 오류 흉내).
  Object? error;

  @override
  Future<void> shareText(String text, {required Rect origin}) async {
    if (error case final error?) throw error;
    shared.add(text);
    origins.add(origin);
  }
}
