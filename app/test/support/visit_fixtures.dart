/// 예약·방문 API 응답의 JSON 모양(백엔드 `visit` 스포크의 스키마 그대로).
///
/// 테스트가 필요한 칸만 바꿔 쓴다. 시각은 매장 시간대(`+09:00`)가 붙어 온다.
library;

Map<String, dynamic> menuBriefJson({int menuId = 1, String name = '목욕'}) => {
  'menu_id': menuId,
  'name': name,
};

Map<String, dynamic> visitCustomerJson({
  int customerId = 7,
  String? name = '이수진',
  String? phoneMasked = '010-12··-5678',
}) => {'customer_id': customerId, 'name': name, 'phone_masked': phoneMasked};

Map<String, dynamic> visitPetJson({
  int petId = 11,
  String? name = '두부',
  String species = 'dog',
  String breed = '말티푸',
  num weightKg = 4.2,
}) => {
  'pet_id': petId,
  'name': name,
  'species': species,
  'breed': breed,
  'weight_kg': weightKg,
};

/// 시각은 `HH:MM`만 받아 [date]에 붙인다.
Map<String, dynamic> visitJson({
  int visitId = 101,
  String date = '2026-10-02',
  String start = '14:00',
  int durationMinutes = 90,
  String status = 'reserved',
  Map<String, dynamic>? customer,
  Map<String, dynamic>? pet,
  bool ownerOnly = false,
  List<Map<String, dynamic>>? menus,
  String? memo = '발톱 짧게',
  String? cancelReason,
}) {
  final startParts = start.split(':').map(int.parse).toList();
  final endTotal = startParts[0] * 60 + startParts[1] + durationMinutes;
  String two(int n) => n.toString().padLeft(2, '0');
  final end = '${two(endTotal ~/ 60)}:${two(endTotal % 60)}';
  return {
    'visit_id': visitId,
    'customer': customer ?? visitCustomerJson(),
    'pet': ownerOnly ? null : (pet ?? visitPetJson()),
    'starts_at': '${date}T$start:00+09:00',
    'ends_at': '${date}T$end:00+09:00',
    'duration_minutes': durationMinutes,
    'status': status,
    'started_at': status == 'in_progress' || status == 'completed'
        ? '${date}T$start:00+09:00'
        : null,
    'completed_at': status == 'completed' ? '${date}T$end:00+09:00' : null,
    'canceled_at': status == 'canceled' ? '${date}T09:00:00+09:00' : null,
    'cancel_reason': status == 'canceled'
        ? (cancelReason ?? 'customer_request')
        : null,
    'memo': memo,
    'menus': menus ?? [menuBriefJson()],
    'status_changed_by_member_id': status == 'reserved' ? null : 1,
  };
}

Map<String, dynamic> dayItemJson(
  Map<String, dynamic> visit, {
  String? groupKey,
  bool overlapping = false,
  bool unresolved = false,
  bool hasRecord = false,
  String? cover,
  bool reportSent = false,
}) => {
  'visit': visit,
  'group_key':
      groupKey ??
      '${(visit['customer'] as Map)['customer_id']}@${visit['starts_at']}',
  'overlapping': overlapping,
  'unresolved': unresolved,
  'has_record': hasRecord,
  'cover': cover,
  'report_sent': reportSent,
};

Map<String, dynamic> dayJson({
  String date = '2026-10-02',
  bool closedDay = false,
  List<Map<String, dynamic>> items = const [],
}) {
  int count(String status) =>
      items.where((i) => (i['visit'] as Map)['status'] == status).length;
  return {
    'date': date,
    'closed_day': closedDay,
    'counts': {
      'visit_count':
          count('reserved') + count('in_progress') + count('completed'),
      'reserved': count('reserved'),
      'in_progress': count('in_progress'),
      'completed': count('completed'),
      'canceled': count('canceled'),
      'no_show': count('no_show'),
      'unresolved': items.where((i) => i['unresolved'] == true).length,
    },
    'items': items,
  };
}

/// 그달의 모든 날. [days]에 준 날만 수·사진을 채운다(`{day: {...}}` — `cover`·`covers`도 여기서 준다).
Map<String, dynamic> calendarJson({
  int year = 2026,
  int month = 9,
  Map<int, Map<String, Object>> days = const {},
  Set<int> closedDays = const {},
  int unresolvedTotal = 0,
  String? oldestUnresolvedDate,
}) {
  final last = DateTime(year, month + 1, 0).day;
  String two(int n) => n.toString().padLeft(2, '0');
  return {
    'month': '$year-${two(month)}',
    'days': [
      for (var d = 1; d <= last; d++)
        {
          'date': '$year-${two(month)}-${two(d)}',
          'visit_count': days[d]?['visit_count'] ?? 0,
          'completed_count': days[d]?['completed_count'] ?? 0,
          'open_count': days[d]?['open_count'] ?? 0,
          'unresolved_count': days[d]?['unresolved_count'] ?? 0,
          'closed_day': closedDays.contains(d),
          'cover': days[d]?['cover'],
          'covers': days[d]?['covers'] ?? const <String>[],
        },
    ],
    'unresolved_total': unresolvedTotal,
    'oldest_unresolved_date': oldestUnresolvedDate,
  };
}

/// 정시 칸. [warnings]에 준 시(時)만 경고를 단다(`{14: ['overlap']}`).
Map<String, dynamic> slotsJson({
  String date = '2026-10-02',
  int durationMinutes = 90,
  bool closedDay = false,
  int fromHour = 10,
  int toHour = 19,
  Map<int, List<String>> warnings = const {},
}) {
  String two(int n) => n.toString().padLeft(2, '0');
  return {
    'date': date,
    'duration_minutes': durationMinutes,
    'closed_day': closedDay,
    'slots': [
      for (var h = fromHour; h < toHour; h++)
        {
          'starts_at': '${date}T${two(h)}:00:00+09:00',
          'warnings': warnings[h] ?? const <String>[],
        },
    ],
  };
}

/// `at` 하나를 물었을 때의 응답.
Map<String, dynamic> slotAtJson({
  String date = '2026-10-02',
  String at = '14:00',
  int durationMinutes = 90,
  List<String> warnings = const [],
}) => {
  'date': date,
  'duration_minutes': durationMinutes,
  'closed_day': warnings.contains('closed_day'),
  'slots': [
    {'starts_at': '${date}T$at:00+09:00', 'warnings': warnings},
  ],
};

Map<String, dynamic> defaultsJson({
  int? sourceVisitId = 90,
  int durationMinutes = 90,
  List<Map<String, dynamic>>? menus,
}) => {
  'source_visit_id': sourceVisitId,
  'duration_minutes': durationMinutes,
  'menus': menus ?? [menuBriefJson()],
};

Map<String, dynamic> visitDetailJson({
  Map<String, dynamic>? visit,
  List<Map<String, dynamic>>? group,
  Map<String, dynamic>? previousVisit = const {
    'visit_id': 90,
    'starts_at': '2026-09-02T14:00:00+09:00',
  },
  int noShowCount = 0,
  Map<String, dynamic>? record,
  Map<String, dynamic>? report,
}) {
  final v = visit ?? visitJson();
  return {
    'visit': v,
    // 서버 계약 — group 은 같은 묶음의 다른 방문(자기 제외)이다.
    'group': group ?? [],
    'previous_visit': previousVisit,
    'no_show_count': noShowCount,
    'record': record,
    'cover': null,
    'report': report ?? reportLinkJson(),
  };
}

/// 기록에 붙은 사진 하나. URL 은 서명 URL 모양이다.
Map<String, dynamic> recordMediaJson({
  int mediaId = 51,
  String phase = 'before',
  int sortOrder = 0,
  String kind = 'photo',
  int? durationSeconds,
}) => {
  'media_id': mediaId,
  'kind': kind,
  'phase': phase,
  'sort_order': sortOrder,
  'original_url': 'http://media.test/b/original/shops/3/$mediaId.jpg?sig=a',
  'display_url': 'http://media.test/b/display/shops/3/$mediaId.jpg?sig=a',
  'thumb_url': 'http://media.test/b/thumb/shops/3/$mediaId.jpg?sig=a',
  'width': 3000,
  'height': 2000,
  'duration_seconds': durationSeconds,
};

/// 미용 기록(설계 9절 응답).
Map<String, dynamic> recordJson({
  int visitId = 101,
  double? weightKg,
  String? careNote,
  String? internalNote,
  String? paymentMethod,
  int? totalAmount,
  List<Map<String, dynamic>> items = const [],
  List<Map<String, dynamic>> media = const [],
  int version = 1,
}) => {
  'visit_id': visitId,
  'weight_kg': weightKg,
  'care_note': careNote,
  'internal_note': internalNote,
  'payment_method': paymentMethod,
  'total_amount': totalAmount,
  'items': items,
  'media': media,
  'version': version,
};

/// 썸네일 서명 URL 모양 — 사진 로더는 서명을 뺀 주소로 캐시한다.
String thumbUrl(int mediaId) =>
    'http://media.test/b/thumb/shops/3/$mediaId.jpg?sig=a';

/// 피드 한 장(설계 9절). 시각은 `HH:MM`만 받아 [date]에 붙인다.
Map<String, dynamic> feedItemJson({
  int visitId = 101,
  String date = '2026-10-02',
  String completedAt = '15:30',
  Map<String, dynamic>? customer,
  Map<String, dynamic>? pet,
  bool ownerOnly = false,
  String? cover,
  List<String> menus = const ['목욕'],
  String? careNote = '귀 청소했어요',
  int mediaCount = 0,
  bool reportSent = false,
}) => {
  'visit_id': visitId,
  'customer': customer ?? visitCustomerJson(),
  'pet': ownerOnly ? null : (pet ?? visitPetJson()),
  'completed_at': '${date}T$completedAt:00+09:00',
  'cover': cover,
  'menus': menus,
  'care_note': careNote,
  'media_count': mediaCount,
  'report_sent': reportSent,
};

Map<String, dynamic> feedJson({
  List<Map<String, dynamic>> items = const [],
  String? nextCursor,
}) => {'items': items, 'next_cursor': nextCursor};

/// 알림장 링크의 상태(방문 상세의 `report`, 미리보기의 `link`). 안 보냈으면 나머지 칸은 null 이다.
/// 주소는 가짜다 — 진짜 링크에는 토큰이 들어 있어 테스트에 옮겨 적지 않는다.
Map<String, dynamic> reportLinkJson({
  bool live = false,
  String? firstViewedAt,
  String? expiresAt = '2026-11-01T15:30:00+09:00',
}) => {
  'status': live ? 'live' : 'none',
  'url': live ? 'http://127.0.0.1:3010/r/TEST-TOKEN' : null,
  'expires_at': live ? expiresAt : null,
  'first_viewed_at': live ? firstViewedAt : null,
  'created_at': live ? '2026-10-02T15:30:00+09:00' : null,
};

/// 알림장 미리보기의 사진·영상 하나. 뺀 것도 `hidden: true`로 함께 온다.
Map<String, dynamic> reportMediaJson({
  int mediaId = 51,
  String kind = 'photo',
  String phase = 'after',
  bool hidden = false,
  int? durationSeconds,
}) => {
  'media_id': mediaId,
  'kind': kind,
  'phase': phase,
  'hidden': hidden,
  'width': 3000,
  'height': 2000,
  'duration_seconds': durationSeconds,
  'display_url': 'http://media.test/b/display/shops/3/$mediaId.jpg?sig=a',
  'thumb_url': thumbUrl(mediaId),
  'download_url': 'http://media.test/b/original/shops/3/$mediaId.jpg?sig=a',
};

/// 알림장 설정(요청·응답이 같은 모양). 기본값은 서버의 기본값이다.
Map<String, dynamic> reportSettingsJson({
  int? linkDays = 30,
  bool showMenus = true,
  bool showShopInfo = true,
  bool showWeight = false,
  bool showAmount = false,
}) => {
  'link_days': linkDays,
  'show_menus': showMenus,
  'show_shop_info': showShopInfo,
  'show_weight': showWeight,
  'show_amount': showAmount,
};

/// 알림장 미리보기(GET·PUT 응답). 앱은 `report` 에서 미디어와 케어 메모만 읽는다 — 나머지 칸은
/// 서버가 주는 모양대로 채워 둔다(끈 항목은 null).
Map<String, dynamic> visitReportJson({
  List<Map<String, dynamic>> media = const [],
  String? careNote,
  Map<String, dynamic>? link,
  Map<String, dynamic>? settings,
}) => {
  'report': {
    'pet_name': '두부',
    'visit_date': '2026-10-02',
    'care_note': careNote,
    'media': media,
    'cover': null,
    'menus': [
      {'name': '목욕', 'amount': null},
    ],
    'total_amount': null,
    'weight_kg': null,
    'shop': {'name': 'Hiss Haus', 'phone': null, 'address': null},
  },
  'link': link ?? reportLinkJson(),
  'settings': settings ?? reportSettingsJson(),
};

/// 알림톡 설정 여덟 칸(overview 의 `settings`). 기본값은 서버가 연동할 때 만드는 값이다.
Map<String, dynamic> notificationSettingsJson({
  bool confirmEnabled = true,
  bool reminderEnabled = true,
  bool reportEnabled = true,
  bool changeEnabled = true,
  bool nextVisitEnabled = false,
  String reminderTime = '18:00',
  int? nextVisitAfterWeeks,
  int nextVisitCooldownDays = 30,
}) => {
  'confirm_enabled': confirmEnabled,
  'reminder_enabled': reminderEnabled,
  'report_enabled': reportEnabled,
  'change_enabled': changeEnabled,
  'next_visit_enabled': nextVisitEnabled,
  'reminder_time': reminderTime,
  'next_visit_after_weeks': nextVisitAfterWeeks,
  'next_visit_cooldown_days': nextVisitCooldownDays,
};

Map<String, dynamic> notificationTemplateJson({
  String kind = 'confirm',
  String status = 'approved',
  String? rejectedReason,
}) => {
  'kind': kind,
  'status': status,
  'rejected_reason': rejectedReason,
  'requested_at': '2026-10-14T10:00:00+09:00',
  'decided_at': status == 'pending' ? null : '2026-10-15T10:00:00+09:00',
};

/// 알림톡 한눈에 보기. 기본은 연동된 매장(설정 기본값, 기본 다섯 종류 승인). 연동되지 않은
/// [channel](none·token_requested·unlinked)이면 설정은 null, 템플릿은 빈 목록이다.
Map<String, dynamic> notificationOverviewJson({
  String channel = 'linked',
  bool senderVerified = false,
  bool smsFallback = false,
  String? senderNumber,
  Map<String, dynamic>? settings,
  List<Map<String, dynamic>>? templates,
}) {
  final linked = channel == 'linked';
  return {
    'channel': {
      'status': channel,
      'linked_at': linked ? '2026-10-14T10:00:00+09:00' : null,
      'sender_number': senderVerified ? (senderNumber ?? '0212345678') : null,
      'sender_verified': senderVerified,
      'sms_fallback_enabled': smsFallback,
    },
    'settings': linked ? (settings ?? notificationSettingsJson()) : null,
    'templates': linked
        ? (templates ??
              [
                for (final kind in const [
                  'confirm',
                  'reminder',
                  'report',
                  'change',
                  'cancel',
                ])
                  notificationTemplateJson(kind: kind),
              ])
        : <Map<String, dynamic>>[],
  };
}

/// 방문의 알림 줄 하나(칸 열 개). `share_text` 는 실패한 줄에만 온다 — 테스트의 글은 가짜다.
Map<String, dynamic> notificationMessageJson({
  int messageId = 1,
  String kind = 'confirm',
  String status = 'sent',
  String? errorKind,
  String? shareText,
  String scheduledAt = '2026-10-02T14:02:00+09:00',
  String? sentAt,
  String? channelUsed,
}) => {
  'message_id': messageId,
  'kind': kind,
  'status': status,
  'channel_used': channelUsed,
  'scheduled_at': scheduledAt,
  'sent_at': sentAt,
  'error_kind': errorKind,
  'canceled_reason': status == 'canceled' ? 'visit_canceled' : null,
  'requested_by_member_id': null,
  'share_text': shareText,
};

/// 사진 발급 응답(설계 7.1).
Map<String, dynamic> issuedUploadJson({int mediaId = 51}) => {
  'media_id': mediaId,
  'puts': {
    'original': 'http://media.test/b/original/shops/3/$mediaId.jpg?put=1',
    'display': 'http://media.test/b/display/shops/3/$mediaId.jpg?put=1',
    'thumb': 'http://media.test/b/thumb/shops/3/$mediaId.jpg?put=1',
  },
  'expires_at': '2026-09-25T10:15:00+09:00',
};

Map<String, dynamic> savedJson(
  List<Map<String, dynamic>> visits, {
  List<String> warnings = const [],
}) => {'visits': visits, 'warnings': warnings};

Map<String, dynamic> nextDraftJson({
  int customerId = 7,
  List<int> petIds = const [11],
  String startsAt = '2026-10-30T14:00:00+09:00',
  int durationMinutes = 90,
  List<Map<String, dynamic>>? menus,
  int intervalWeeks = 4,
}) => {
  'customer_id': customerId,
  'pet_ids': petIds,
  'starts_at': startsAt,
  'duration_minutes': durationMinutes,
  'menus': menus ?? [menuBriefJson()],
  'interval_weeks': intervalWeeks,
};

Map<String, dynamic> settingsJson({
  String opensAt = '10:00:00',
  String closesAt = '19:00:00',
  int defaultDurationMinutes = 120,
  List<int> closedWeekdays = const [0],
}) => {
  'opens_at': opensAt,
  'closes_at': closesAt,
  'default_duration_minutes': defaultDurationMinutes,
  'closed_weekdays': closedWeekdays,
};

Map<String, dynamic> menuJson({
  int menuId = 1,
  String name = '목욕',
  int? defaultDurationMinutes = 60,
  int sortOrder = 1,
  bool archived = false,
  int? price,
}) => {
  'menu_id': menuId,
  'name': name,
  'default_duration_minutes': defaultDurationMinutes,
  'sort_order': sortOrder,
  'archived': archived,
  'price': price,
};

/// 기본 메뉴 다섯(서버가 매장을 처음 쓸 때 넣는 것).
List<Map<String, dynamic>> defaultMenusJson() => [
  menuJson(menuId: 1, name: '목욕', defaultDurationMinutes: 60, sortOrder: 1),
  menuJson(menuId: 2, name: '위생', defaultDurationMinutes: 60, sortOrder: 2),
  menuJson(menuId: 3, name: '부분 미용', defaultDurationMinutes: 90, sortOrder: 3),
  menuJson(menuId: 4, name: '전체 미용', defaultDurationMinutes: 150, sortOrder: 4),
  menuJson(menuId: 5, name: '스포팅', defaultDurationMinutes: 120, sortOrder: 5),
];

/// 카톡 예약 초안 응답(③-A3). 후보가 없으면 `candidates: []`.
Map<String, dynamic> visitDraftJson({
  String? date = '2026-10-02',
  String? time = '14:00',
  List<Map<String, dynamic>>? candidates,
  List<int> petIds = const [11],
  List<int> menuIds = const [1],
  bool guessedDate = false,
  bool guessedTime = false,
  bool guessedWho = false,
  bool guessedMenu = false,
}) => {
  'date': date,
  'time': time,
  'customer_candidates': candidates ?? [draftCandidateJson()],
  'pet_ids': petIds,
  'menu_ids': menuIds,
  'guessed': {
    'date': guessedDate,
    'time': guessedTime,
    'who': guessedWho,
    'menu': guessedMenu,
  },
};

Map<String, dynamic> draftCandidateJson({
  int customerId = 7,
  String name = '이수진',
  String phoneMasked = '010-12··-5678',
  List<Map<String, dynamic>>? pets,
  List<int> matchedPetIds = const [11],
}) => {
  'customer_id': customerId,
  'name': name,
  'phone_masked': phoneMasked,
  'pets': pets ?? [draftPetJson()],
  'matched_pet_ids': matchedPetIds,
};

Map<String, dynamic> draftPetJson({int petId = 11, String name = '두부'}) => {
  'pet_id': petId,
  'name': name,
};
