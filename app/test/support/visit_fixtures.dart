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
}) => {
  'visit': visit,
  'group_key':
      groupKey ??
      '${(visit['customer'] as Map)['customer_id']}@${visit['starts_at']}',
  'overlapping': overlapping,
  'unresolved': unresolved,
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

/// 그달의 모든 날. [days]에 준 날만 수를 채운다(`{day: {...}}`).
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
}) {
  final v = visit ?? visitJson();
  return {
    'visit': v,
    // 서버 계약 — group 은 같은 묶음의 다른 방문(자기 제외)이다.
    'group': group ?? [],
    'previous_visit': previousVisit,
    'no_show_count': noShowCount,
  };
}

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
}) => {
  'menu_id': menuId,
  'name': name,
  'default_duration_minutes': defaultDurationMinutes,
  'sort_order': sortOrder,
  'archived': archived,
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
