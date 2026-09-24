/// 시각·날짜를 화면 글자로. 기능 폴더 여럿이 함께 쓴다(방문·고객·설정).
library;

import '../../l10n/app_strings.dart';

/// `14:00`.
String hhmm(DateTime t) =>
    '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

/// `10월 2일 금`.
String dayLabel(DateTime d) =>
    '${d.month}월 ${d.day}일 ${AppStrings.weekdaysShort[d.weekday - 1]}';

bool sameDay(DateTime a, DateTime b) =>
    a.year == b.year && a.month == b.month && a.day == b.day;
