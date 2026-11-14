/// 고객·반려동물 폼의 입력 규칙과 표시 형식. 서버 규칙(결정 기록 005)을
/// 앱에서 먼저 확인해 요청 없이 바로 알려 주려는 것이다 — 최종 판단은 서버다.
library;

/// 휴대전화(010·011·016~019), 서울(02), 지역 번호(031~065 범위의 세 자리),
/// 인터넷 전화(070). 백엔드 `phone_number.py` 의 `_VALID` 와 같다.
final _validPhone = RegExp(
  r'^(01[016789]\d{7,8}|02\d{7,8}|0[3-6][1-5]\d{7,8}|070\d{8})$',
);

/// 숫자만 남긴다(하이픈·공백 제거). 전각 숫자는 버린다 — 서버도 받지 않는다.
String phoneDigits(String raw) => raw.replaceAll(RegExp(r'[^0-9]'), '');

bool isValidPhone(String digits) => _validPhone.hasMatch(digits);

/// 숫자만 저장된 번호를 `010-1234-5678` 모양으로 보인다.
String formatPhone(String digits) {
  if (!isValidPhone(digits)) return digits;
  final area = digits.startsWith('02')
      ? digits.substring(0, 2)
      : digits.substring(0, 3);
  final rest = digits.substring(area.length);
  final middle = rest.substring(0, rest.length - 4);
  final last = rest.substring(rest.length - 4);
  return '$area-$middle-$last';
}

/// 가린 번호(`010-12··-5678`)의 뒷자리를 `··5678` 로 줄인다(가족 카드 머리).
String maskedTail(String phoneMasked) {
  final last = phoneMasked.length >= 4
      ? phoneMasked.substring(phoneMasked.length - 4)
      : phoneMasked;
  return '··$last';
}

/// 몸무게(kg). 0 초과, 999.9 이하, 소수 한 자리까지. 아니면 null.
double? parseWeight(String raw) {
  final text = raw.trim();
  if (!RegExp(r'^\d{1,3}(\.\d)?$').hasMatch(text)) return null;
  final value = double.parse(text);
  return value > 0 ? value : null;
}

/// 몸무게 입력 칸에 넣을 글자 — `3.2`, `4`.
String weightText(double kg) =>
    kg == kg.roundToDouble() ? kg.toStringAsFixed(0) : kg.toStringAsFixed(1);

/// `3.2kg`, `4kg`.
String formatWeight(double kg) => '${weightText(kg)}kg';

/// 서버는 생일·태어난 해를 40년 전까지 받는다. 태어난 해는 올해까지.
bool isValidBirthYear(int year, DateTime today) =>
    year <= today.year && year >= today.year - 40;

/// 생일로 고를 수 있는 가장 이른 날. 서버(`pet_age.check_birth`)처럼 해만 본다 — 40년 전 해의 1월 1일.
DateTime earliestBirthDate(DateTime today) => DateTime(today.year - 40);

/// 앞뒤 공백을 없애고, 비었으면 null.
String? optionalText(String raw) {
  final text = raw.trim();
  return text.isEmpty ? null : text;
}

/// 생일 입력(`2021.03.04`, `2021-03-04`, `20210304`)을 날짜로 바꾼다. 없는 날짜,
/// 오늘보다 늦은 날, 40년 전 해보다 이른 날은 null.
DateTime? parseBirthDate(String raw, DateTime today) {
  final digits = raw.replaceAll(RegExp(r'[.\-/\s]'), '');
  if (!RegExp(r'^\d{8}$').hasMatch(digits)) return null;
  final year = int.parse(digits.substring(0, 4));
  final month = int.parse(digits.substring(4, 6));
  final day = int.parse(digits.substring(6, 8));
  final date = DateTime(year, month, day);
  if (date.year != year || date.month != month || date.day != day) return null;
  final todayDate = DateTime(today.year, today.month, today.day);
  if (date.isAfter(todayDate) || date.isBefore(earliestBirthDate(today))) {
    return null;
  }
  return date;
}

/// 주의 사유를 한 줄로 다듬는다 — 줄바꿈·탭을 빈칸으로, 이어진 빈칸은 하나로, 앞뒤는 뗀다.
/// 빈 글이면 null(저장하지 않는다). 서버는 제어 문자를 422 로 거절한다.
String? cleanCautionReason(String text) {
  final line = text.replaceAll(RegExp(r'\s+'), ' ').trim();
  return line.isEmpty ? null : line;
}
