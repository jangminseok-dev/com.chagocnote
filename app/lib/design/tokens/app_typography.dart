import 'package:flutter/widgets.dart';

import 'app_colors.dart';

/// 텍스트 스타일 프리셋.
///
/// 본문은 Pretendard, 큰 숫자와 영문 타이틀은 Bodoni Moda(고대비 세리프),
/// 한글 타이틀은 MaruBuri를 쓴다.
abstract final class AppTypography {
  static const _pretendard = 'Pretendard';
  static const _bodoniModa = 'BodoniModa';
  static const _maruBuri = 'MaruBuri';

  /// 기본 본문.
  static const body = TextStyle(
    fontFamily: _pretendard,
    fontSize: 14,
    height: 1.4,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );

  /// 강조 본문(버튼 라벨 등).
  static const bodyStrong = TextStyle(
    fontFamily: _pretendard,
    fontSize: 14,
    height: 1.4,
    fontWeight: FontWeight.w600,
    color: AppColors.ink,
  );

  /// 작은 보조 텍스트.
  static const caption = TextStyle(
    fontFamily: _pretendard,
    fontSize: 11,
    height: 1.3,
    fontWeight: FontWeight.w500,
    color: AppColors.secondary,
  );

  /// 한글 타이틀("오늘의 케어" 같은 섹션 제목).
  static const titleKo = TextStyle(
    fontFamily: _maruBuri,
    fontSize: 19,
    height: 1.25,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );

  /// 영문 타이틀("care diary", "Daily record" 같은 브랜드/화면 제목).
  static const titleEn = TextStyle(
    fontFamily: _bodoniModa,
    fontSize: 16,
    height: 1.1,
    fontWeight: FontWeight.w500,
    color: AppColors.ink,
  );

  /// 날짜 숫자처럼 아주 큰 세리프 숫자. 줄 높이를 바짝 붙인다.
  static const bigNumeral = TextStyle(
    fontFamily: _bodoniModa,
    fontSize: 82,
    height: 0.84,
    letterSpacing: -4,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );

  /// 초대 코드(8자리 영숫자). 사람이 보고 옮겨 적으므로 [bigNumeral]과 달리
  /// 자간을 벌려 글자가 겹치지 않게 한다.
  static const inviteCode = TextStyle(
    fontFamily: _bodoniModa,
    fontSize: 36,
    height: 1.1,
    letterSpacing: 2,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );

  /// 영문 월·요일처럼 기울인 세리프 라벨.
  static const italicLabel = TextStyle(
    fontFamily: _bodoniModa,
    fontSize: 30,
    height: 0.95,
    fontStyle: FontStyle.italic,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );
}
