import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // 키보드가 올라오면 Scaffold 본문이 줄어든다. 스캐폴드 바탕이 투명이면 그
  // 아래(키보드 둥근 모서리 뒤, 시트 막 아래)가 검게 보인다 — 바탕
  // 그라데이션의 아래쪽 색으로 칠해 둔다(사용자 시뮬레이터 발견).
  test('스캐폴드 바탕은 배경 그라데이션의 아래쪽 색(AppColors.backgroundBottom)이다', () {
    expect(appTheme().scaffoldBackgroundColor, AppColors.backgroundBottom);
  });
}
