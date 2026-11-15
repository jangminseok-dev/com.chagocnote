// 기록 검색 응답(JSON). 기본값은 콩이(101)의 11월 3일 방문(7)의 케어 노트 한 줄이다.

Map<String, dynamic> searchItemJson({
  String kind = 'care_note',
  int customerId = 1,
  String owner = '김민지',
  int? petId = 101,
  String? pet = '콩이',
  String? photo,
  int? visitId = 7,
  int? openPetId,
  String? date = '2026-11-03',
  String snippet = '귀 청소할 때 예민하게 반응했어요',
}) => {
  'kind': kind,
  'owner': {'customer_id': customerId, 'name': owner},
  'pet': petId == null ? null : {'pet_id': petId, 'name': pet, 'photo': photo},
  'visit_id': visitId,
  'open_pet_id': openPetId,
  'date': date,
  'snippet': snippet,
};

/// 방문이 없는 줄(특이사항·지병) — 그 아이를 연다.
Map<String, dynamic> searchPetItemJson({
  String kind = 'pet_memo',
  int petId = 101,
  String pet = '콩이',
  String snippet = '드라이기 소리를 무서워해요',
}) => searchItemJson(
  kind: kind, petId: petId, pet: pet, visitId: null, openPetId: petId, date: null, snippet: snippet,
);

/// 보호자 메모 — 아이 없이 보호자 이름으로. [openPetId]가 null 이면 갈 곳이 없다.
Map<String, dynamic> searchOwnerItemJson({
  int customerId = 1,
  String owner = '김민지',
  int? openPetId = 101,
  String snippet = '미용이 끝나면 전화를 달라고 하심',
}) => searchItemJson(
  kind: 'customer_memo', customerId: customerId, owner: owner, petId: null, pet: null, visitId: null,
  openPetId: openPetId, date: null, snippet: snippet,
);

Map<String, dynamic> searchResultJson(List<Map<String, dynamic>> items, {bool semantic = true}) => {
  'items': items,
  'semantic': semantic,
};
