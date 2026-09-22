import 'package:flutter/widgets.dart';

/// 차곡노트 디자인 톤 — 무채색 회백 배경에 검정 한 가지 포인트.
///
/// 색은 사진에서만 온다. 이 팔레트 밖의 색을 새로 들이지 않는다.
abstract final class AppColors {
  /// 배경 그라데이션 시작(위쪽).
  static const backgroundTop = Color(0xFFF5F5F5);

  /// 배경 그라데이션 끝(아래쪽).
  static const backgroundBottom = Color(0xFFECECEC);

  /// 본문 텍스트·아이콘·단일 포인트 색.
  static const ink = Color(0xFF161616);

  /// 보조 텍스트(캡션, 비활성 상태).
  static const secondary = Color(0xFF8D8D8D);

  /// 구분선.
  static const line = Color(0xFFDCDCDC);

  /// 사진 테두리·글래스 채움·FAB 아이콘에만 쓰는 흰색.
  static const white = Color(0xFFFFFFFF);

  /// 배경에 쓰는 세로 방향 그라데이션.
  static const backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [backgroundTop, backgroundBottom],
  );
}
