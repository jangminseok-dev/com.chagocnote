/// 알림장에서 뺄 사진·영상을 정하는 규칙(순수 함수).
///
/// `PUT …/report` 의 `hidden_media_ids` 는 "뺄 것 전부"다. 화면이 처음 읽은 목록을 그대로 보내면
/// 그 사이 다른 기기에서 뺀 사진이 되살아난다 — 그래서 화면은 이번에 누른 것만 들고, 보내기 직전에
/// 다시 읽은 서버의 상태 위에 덮는다.
library;

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
