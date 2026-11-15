import '../../../core/time/shop_time.dart';

/// 찾아지는 글의 종류. 서버의 글자를 여기서 한 번만 바꾼다.
enum SearchKind {
  careNote('care_note'),
  internalNote('internal_note'),
  visitMemo('visit_memo'),
  petMemo('pet_memo'),
  conditionNote('condition_note'),
  customerMemo('customer_memo');

  const SearchKind(this.wire);

  /// 서버가 쓰는 이름.
  final String wire;
}

/// 검색 결과의 한 줄 — 누구의 어떤 글인지와 걸린 토막.
class SearchItem {
  const SearchItem({
    required this.kind,
    required this.ownerId,
    required this.ownerName,
    required this.snippet,
    this.petId,
    this.petName,
    this.photoUrl,
    this.visitId,
    this.openPetId,
    this.date,
  });

  final SearchKind kind;
  final int ownerId;
  final String ownerName;

  /// 아이. 보호자 메모와 보호자만의 방문에는 없다.
  final int? petId;
  final String? petName;

  /// 아이의 프로필 사진(썸네일) 주소.
  final String? photoUrl;

  /// 있으면 방문 상세로 간다.
  final int? visitId;

  /// 방문이 없는 줄을 눌렀을 때 열 반려동물. 보호자에게 아이가 없으면 이것도 없다.
  final int? openPetId;

  /// 방문 날. 방문에 딸린 글에만 있다.
  final DateTime? date;

  /// 걸린 자리의 글 한 토막.
  final String snippet;

  /// 모르는 종류이거나 모양이 깨진 줄은 null 이다 — 그 줄만 버리고 나머지는 보인다.
  /// 날짜만 깨졌으면 날짜 없이 살린다.
  static SearchItem? tryParse(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final kind = SearchKind.values.where((k) => k.wire == json['kind']).firstOrNull;
    final owner = json['owner'];
    final snippet = json['snippet'];
    if (kind == null || owner is! Map<String, dynamic> || snippet is! String) return null;
    final ownerId = owner['customer_id'];
    final ownerName = owner['name'];
    if (ownerId is! int || ownerName is! String) return null;

    final pet = json['pet'];
    int? petId;
    String? petName;
    String? photoUrl;
    if (pet != null) {
      if (pet is! Map<String, dynamic>) return null;
      final id = pet['pet_id'];
      final name = pet['name'];
      final photo = pet['photo'];
      if (id is! int || name is! String) return null;
      petId = id;
      petName = name;
      photoUrl = photo is String ? photo : null;
    }
    final visitId = json['visit_id'];
    final openPetId = json['open_pet_id'];
    return SearchItem(
      kind: kind,
      ownerId: ownerId,
      ownerName: ownerName,
      snippet: snippet,
      petId: petId,
      petName: petName,
      photoUrl: photoUrl,
      visitId: visitId is int ? visitId : null,
      openPetId: openPetId is int ? openPetId : null,
      date: _day(json['date']),
    );
  }
}

DateTime? _day(Object? value) {
  if (value is! String) return null;
  try {
    return parseDay(value);
  } on Object {
    return null;
  }
}

/// 검색 결과 — 가까운 순의 줄들.
///
/// 서버는 뜻 검색이 함께 됐는지(`semantic`)도 주지만 화면은 그것으로 아무것도 그리지 않으므로 읽지 않는다.
class SearchResult {
  const SearchResult({required this.items});

  final List<SearchItem> items;

  factory SearchResult.fromJson(Map<String, dynamic> json) {
    final items = json['items'];
    return SearchResult(
      items: [
        if (items is List)
          for (final item in items) ?SearchItem.tryParse(item),
      ],
    );
  }
}
