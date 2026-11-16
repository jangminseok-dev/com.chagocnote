/// 알림장에서 뺄 사진·영상을 정하는 규칙(순수 함수).
///
/// `PUT …/report` 의 `hidden_media_ids` 는 "뺄 것 전부"다. 화면이 처음 읽은 목록을 그대로 보내면
/// 그 사이 다른 기기에서 뺀 사진이 되살아난다 — 그래서 화면은 이번에 누른 것만 들고, 보내기 직전에
/// 다시 읽은 서버의 상태 위에 덮는다.
library;

import '../../../l10n/app_strings.dart';
import '../api/report_models.dart';

/// 서버의 지금 미디어 위에 이번에 누른 것([changes]: 미디어 ID → 뺄지)을 덮어 "뺄 것 전부"를 만든다.
/// 서버에 이제 없는 ID 는 버린다. 누르지 않은 것은 서버의 hidden 을 따른다(새로 붙은 사진은 보인다).
List<int> hiddenIdsOf(List<ReportMedia> media, Map<int, bool> changes) => [
  for (final m in media)
    if (changes[m.mediaId] ?? m.hidden) m.mediaId,
];

/// 보호자에게 보일 것이 하나라도 있는가 — 빼지 않은 미디어가 있거나 케어 메모가 있다
/// (서버의 `REPORT_EMPTY` 와 같은 규칙. 빈칸뿐인 메모는 없는 것이다).
bool hasSomethingToShow(
  List<ReportMedia> media,
  Map<int, bool> changes,
  String? careNote,
) =>
    hiddenIdsOf(media, changes).length < media.length ||
    (careNote != null && careNote.trim().isNotEmpty);

// --- 알림장 끝의 리뷰 남기기 줄(⑫ 설계 3.6) ---
// 서버(`visit/domain/services/report_rules.check_review`)와 같은 규칙이다 — 앱이 먼저 짚어 [저장]이
// 422 로 떨어지지 않게. 글자 수는 서버처럼 보이는 글자(코드 포인트)로 센다.

const reviewUrlMax = 300;
const reviewTextMax = 60;

/// 제어 문자·형식 문자(너비 없는 공백·방향 뒤집기 등)·줄·문단 나눔 — 서버의 유니코드 범주 Cc·Cf·Zl·Zp.
final _hidden = RegExp(r'[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]', unicode: true);
final _space = RegExp(r'\s', unicode: true);

/// 리뷰 주소 칸의 글을 보낼 값으로 — 앞뒤 공백을 걷고(서버도 걷는다), 비면 null(줄을 지운다). 스킴만
/// 소문자로 바꾼다(`HTTPS://` → `https://`, 서버의 `normalized_review_url` 과 같다 — 저장한 값과 견줄 때
/// 어긋나지 않게).
String? cleanReviewUrl(String input) {
  final text = input.trim();
  if (text.isEmpty) return null;
  final cut = text.indexOf('://');
  return cut < 0
      ? text
      : '${text.substring(0, cut).toLowerCase()}${text.substring(cut)}';
}

/// 리뷰 문구 칸의 글을 보낼 값으로 — 앞뒤 공백을 걷고, 비거나 기본 문구([defaultText])와 같으면 null
/// (기본 문구가 나간다 — 기본 문구가 바뀌면 따라간다).
String? cleanReviewText(String input, {required String? defaultText}) {
  final text = input.trim();
  return text.isEmpty || text == defaultText ? null : text;
}

/// 리뷰 주소의 문제. 없으면 null — 빈 칸은 문제가 아니다(지우기).
String? reviewUrlProblem(String input) {
  final url = cleanReviewUrl(input);
  if (url == null) return null;
  if (!url.toLowerCase().startsWith('https://')) {
    return AppStrings.reviewUrlNotHttps;
  }
  if (url.runes.length > reviewUrlMax) return AppStrings.reviewUrlTooLong;
  // 계정 정보(`user@`)는 호스트 앞(첫 `/`·`?`·`#` 전)의 `@` 로 본다 — 서버의 netloc 과 같다.
  final rest = url.substring('https://'.length);
  final end = rest.indexOf(RegExp('[/?#]'));
  final netloc = end < 0 ? rest : rest.substring(0, end);
  if (netloc.contains('@') || _space.hasMatch(url) || _hidden.hasMatch(url)) {
    return AppStrings.reviewUrlInvalid;
  }
  final Uri uri;
  try {
    uri = Uri.parse(url);
  } on FormatException {
    return AppStrings.reviewUrlInvalid; // 짝 없는 대괄호·숫자가 아닌 포트
  }
  if (uri.host.isEmpty || (uri.hasPort && uri.port > 65535)) {
    return AppStrings.reviewUrlInvalid;
  }
  return null;
}

/// 리뷰 문구의 문제. 없으면 null — 빈 칸은 문제가 아니다(기본 문구).
String? reviewTextProblem(String input) {
  final text = input.trim();
  if (text.runes.length > reviewTextMax) return AppStrings.reviewTextTooLong;
  if (_hidden.hasMatch(text)) return AppStrings.reviewTextOneLine;
  final lowered = text.toLowerCase();
  if (lowered.contains('http') || lowered.contains('www.')) {
    return AppStrings.reviewTextNoLink;
  }
  return null;
}
