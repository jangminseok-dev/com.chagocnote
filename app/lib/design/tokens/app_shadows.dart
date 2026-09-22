import 'package:flutter/widgets.dart';

/// 그림자 프리셋. 무채색 배경에서 색이 아니라 깊이로만 위계를 준다.
abstract final class AppShadows {
  /// 카드·타일처럼 배경에 살짝 얹힌 요소.
  static const soft = [
    BoxShadow(color: Color(0x14000000), blurRadius: 12, offset: Offset(0, 4)),
  ];

  /// 탭바·FAB·시트처럼 떠 있는 컨트롤 레이어.
  static const floating = [
    BoxShadow(color: Color(0x33000000), blurRadius: 20, offset: Offset(0, 8)),
  ];

  /// 사진 타일의 숫자 동그라미처럼 아주 작은 배지에 얹는 그림자.
  static const badge = [
    BoxShadow(color: Color(0x33000000), blurRadius: 3, offset: Offset(0, 1)),
  ];
}
