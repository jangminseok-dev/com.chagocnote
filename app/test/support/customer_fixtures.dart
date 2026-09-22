/// 고객·반려동물 API 응답의 JSON 모양(백엔드 `customer` 스포크의 스키마 그대로).
///
/// 테스트가 필요한 칸만 바꿔 쓴다. 번호·이름은 가짜 값이다.
library;

Map<String, dynamic> petSummaryJson({
  int petId = 11,
  String name = '콩이',
  String species = 'dog',
  String breed = '말티즈',
  String ageLabel = '5살',
  bool hasConditions = false,
  bool passedAway = false,
}) => {
  'pet_id': petId,
  'name': name,
  'species': species,
  'breed': breed,
  'age_label': ageLabel,
  'has_conditions': hasConditions,
  'passed_away': passedAway,
};

Map<String, dynamic> familyJson({
  int customerId = 7,
  String name = '김민지',
  String phoneMasked = '010-12··-5678',
  List<Map<String, dynamic>>? pets,
}) => {
  'customer_id': customerId,
  'name': name,
  'phone_masked': phoneMasked,
  'pets': pets ?? [petSummaryJson()],
};

Map<String, dynamic> pageJson({
  List<Map<String, dynamic>>? items,
  String? nextCursor,
  int? petCount,
}) {
  final list = items ?? [familyJson()];
  return {
    'items': list,
    'next_cursor': nextCursor,
    'pet_count':
        petCount ??
        list.fold<int>(0, (sum, f) => sum + (f['pets'] as List).length),
  };
}

Map<String, dynamic> conditionJson({
  String typeCode = 'patella_luxation',
  String label = '슬개골 탈구',
  String? customLabel,
  String? note = '2기',
}) => {
  'type_code': typeCode,
  'label': label,
  'custom_label': customLabel,
  'note': note,
};

Map<String, dynamic> petJson({
  int petId = 11,
  int customerId = 7,
  String name = '콩이',
  String species = 'dog',
  String breed = '말티즈',
  String sex = 'female',
  bool neutered = true,
  String? birthDate = '2021-03-04',
  int? birthYear,
  String ageLabel = '5살',
  num weightKg = 3.2,
  bool noKnownConditions = false,
  List<Map<String, dynamic>>? conditions,
  String? memo = '귀 만지면 싫어함',
  String? passedAwayAt,
}) {
  final list = conditions ?? (noKnownConditions ? const [] : [conditionJson()]);
  return {
    'pet_id': petId,
    'customer_id': customerId,
    'name': name,
    'species': species,
    'breed': breed,
    'sex': sex,
    'neutered': neutered,
    'birth_date': birthDate,
    'birth_year': birthYear,
    'age_label': ageLabel,
    'weight_kg': weightKg,
    'no_known_conditions': noKnownConditions,
    'has_conditions': list.isNotEmpty,
    'conditions': list,
    'memo': memo,
    'passed_away_at': passedAwayAt,
  };
}

Map<String, dynamic> customerJson({
  int customerId = 7,
  String name = '김민지',
  String phone = '01012345678',
  String? phoneAlt,
  bool marketingConsent = true,
  String marketingConsentChangedAt = '2026-09-20T12:00:00Z',
  String? memo = '오후 방문 선호',
}) => {
  'customer_id': customerId,
  'name': name,
  'phone': phone,
  'phone_alt': phoneAlt,
  'marketing_consent': marketingConsent,
  'marketing_consent_changed_at': marketingConsentChangedAt,
  'memo': memo,
};

Map<String, dynamic> customerDetailJson({
  Map<String, dynamic>? customer,
  List<Map<String, dynamic>>? pets,
}) => {
  'customer': customer ?? customerJson(),
  'pets': pets ?? [petJson()],
};

Map<String, dynamic> petDetailJson({
  Map<String, dynamic>? pet,
  int customerId = 7,
  String ownerName = '김민지',
  String phoneMasked = '010-12··-5678',
  List<Map<String, dynamic>> siblings = const [],
}) => {
  'pet': pet ?? petJson(customerId: customerId),
  'owner': {
    'customer_id': customerId,
    'name': ownerName,
    'phone_masked': phoneMasked,
  },
  'siblings': siblings,
};

Map<String, dynamic> siblingJson({
  int petId = 12,
  String name = '두부',
  String species = 'dog',
  bool passedAway = false,
}) => {
  'pet_id': petId,
  'name': name,
  'species': species,
  'passed_away': passedAway,
};

const conditionTypesJson = [
  {'code': 'patella_luxation', 'label': '슬개골 탈구', 'sort_order': 1},
  {'code': 'heart_disease', 'label': '심장 질환', 'sort_order': 2},
  {'code': 'skin_disease', 'label': '피부병', 'sort_order': 3},
  {'code': 'other', 'label': '기타', 'sort_order': 10},
];
