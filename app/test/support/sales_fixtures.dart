// 매출 요약 응답(JSON). 기본값은 목업의 11월 — 14일(토)까지 3,250,000원, 방문 48건, 아이 41마리.

Map<String, dynamic> petCardJson(int id, String name, {String? photo}) => {
  'pet_id': id,
  'name': name,
  'photo_url': photo,
};

/// 11월 1~14일의 하루 매출(만 원) — 합이 325 다. 15일부터는 아직 오지 않은 날이다.
const salesNovemberDays = [0, 18, 22, 15, 24, 31, 38, 0, 16, 20, 19, 27, 44, 51];

List<Map<String, dynamic>> salesNovemberBuckets() => [
  for (var d = 1; d <= 30; d++)
    {
      'key': '2026-11-${d.toString().padLeft(2, '0')}',
      'revenue': d <= 14 ? salesNovemberDays[d - 1] * 10000 : 0,
      'visit_count': d <= 14 ? (salesNovemberDays[d - 1] == 0 ? 0 : 3 + d % 3) : 0,
      'future': d > 14,
      'pets': d == 14
          ? [
              petCardJson(101, '보리', photo: 'https://media.test/101.jpg'),
              petCardJson(102, '코코'),
              petCardJson(103, '두부', photo: 'https://media.test/103.jpg'),
            ]
          : <Map<String, dynamic>>[],
    },
];

Map<String, dynamic> salesSummaryJson({
  String span = 'month',
  String start = '2026-11-01',
  String end = '2026-11-30',
  String? elapsedEnd = '2026-11-14',
  int revenue = 3250000,
  int visitCount = 48,
  int pricedCount = 48,
  int? average = 67708,
  Map<String, dynamic>? previous = const {
    'start': '2026-10-01',
    'end': '2026-10-14',
    'revenue': 2830000,
  },
  Map<String, dynamic>? yearAgo,
  int? goal,
  Map<String, dynamic>? pets,
  List<Map<String, dynamic>>? buckets,
  List<Map<String, dynamic>>? payments,
  List<Map<String, dynamic>>? menus,
  List<Map<String, dynamic>>? regulars,
  Map<String, dynamic>? bookings,
  Object? weekdays = const [100000, 180000, 380000, 420000, 550000, 890000, 730000],
  Object? report = const {'completed': 48, 'sent': 40, 'opened': 31},
  int unrecordedCount = 3,
  int duePetCount = 7,
}) => {
  'span': span,
  'period': {'start': start, 'end': end, 'elapsed_end': elapsedEnd},
  'revenue': revenue,
  'visit_count': visitCount,
  'priced_count': pricedCount,
  'average': average,
  'compare': {'previous': previous, 'year_ago': yearAgo},
  'goal': goal == null ? null : {'monthly_amount': goal},
  'pets':
      pets ??
      {
        'count': 41,
        'new_count': 6,
        'returning_count': 35,
        'faces': [
          petCardJson(101, '보리', photo: 'https://media.test/101.jpg'),
          petCardJson(102, '코코'),
          petCardJson(103, '두부', photo: 'https://media.test/103.jpg'),
        ],
        'new': [petCardJson(104, '몽이')],
        'returning': [petCardJson(101, '보리', photo: 'https://media.test/101.jpg')],
      },
  'buckets': buckets ?? salesNovemberBuckets(),
  'payments':
      payments ??
      [
        {'method': 'card', 'amount': 2400000},
        {'method': 'cash', 'amount': 550000},
        {'method': 'transfer', 'amount': 300000},
      ],
  'menus':
      menus ??
      [
        {
          'menu_id': 1,
          'name': '전체 미용',
          'amount': 2100000,
          'count': 30,
          'pet': petCardJson(103, '두부', photo: 'https://media.test/103.jpg'),
        },
        {'menu_id': 2, 'name': '목욕', 'amount': 750000, 'count': 15, 'pet': null},
        {'menu_id': 3, 'name': '스파', 'amount': 400000, 'count': 8, 'pet': null},
      ],
  'regulars':
      regulars ??
      [
        {'pet': petCardJson(101, '보리', photo: 'https://media.test/101.jpg'), 'visit_count': 9},
        {'pet': petCardJson(102, '코코'), 'visit_count': 7},
      ],
  'bookings':
      bookings ??
      {'remaining': 12, 'expected_amount': 840000, 'no_show': 2, 'canceled': 3},
  'weekdays': weekdays,
  'report': report,
  'unrecorded_count': unrecordedCount,
  'due_pet_count': duePetCount,
};

Map<String, dynamic> salesVisitJson(
  int visitId, {
  String date = '2026-11-14',
  Map<String, dynamic>? pet,
  int? amount,
}) => {'visit_id': visitId, 'date': date, 'pet': pet, 'amount': amount};

Map<String, dynamic> duePetJson(int petId, String name, String lastVisit, {String? photo}) => {
  'pet': petCardJson(petId, name, photo: photo),
  'last_visit_date': lastVisit,
};

Map<String, dynamic> salesPageJson(List<Map<String, dynamic>> items, {String? nextCursor}) => {
  'items': items,
  'next_cursor': nextCursor,
};
