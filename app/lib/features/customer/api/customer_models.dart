/// 고객·반려동물 API 의 응답·요청 모델.
///
/// `fromJson`은 서버의 스네이크케이스 키를 그대로 읽는다. 전화번호·이름이
/// 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
library;

/// 목록의 반려동물 한 줄.
class PetSummary {
  const PetSummary({
    required this.petId,
    required this.name,
    required this.species,
    required this.breed,
    required this.ageLabel,
    required this.hasConditions,
    required this.passedAway,
    required this.photo,
  });

  factory PetSummary.fromJson(Map<String, dynamic> json) => PetSummary(
    petId: json['pet_id'] as int,
    name: json['name'] as String,
    species: json['species'] as String,
    breed: json['breed'] as String,
    ageLabel: json['age_label'] as String,
    hasConditions: json['has_conditions'] as bool,
    passedAway: json['passed_away'] as bool,
    photo: json['photo'] as String?,
  );

  final int petId;
  final String name;

  /// 'dog' | 'cat'
  final String species;
  final String breed;
  final String ageLabel;
  final bool hasConditions;
  final bool passedAway;

  /// 프로필 사진 — 가장 최근 완료 기록의 대표 사진 썸네일 서명 URL. 없으면 회색 자리.
  final String? photo;
}

/// 목록의 가족 카드 하나(보호자 한 명과 그 아이들). 번호는 가린 값만 있다.
class FamilyCard {
  const FamilyCard({
    required this.customerId,
    required this.name,
    required this.phoneMasked,
    required this.pets,
    this.caution = false,
  });

  factory FamilyCard.fromJson(Map<String, dynamic> json) => FamilyCard(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    phoneMasked: json['phone_masked'] as String,
    pets: (json['pets'] as List)
        .map((e) => PetSummary.fromJson(e as Map<String, dynamic>))
        .toList(),
    caution: json['caution'] as bool? ?? false,
  );

  final int customerId;
  final String name;

  /// `010-12··-5678` 모양.
  final String phoneMasked;
  final List<PetSummary> pets;

  /// 살아 있는 주의 표시가 있다(③-B). 사유는 목록에 오지 않는다.
  final bool caution;
}

/// 주의 고객 표시(③-B) — 이 매장만 본다. [until]까지 보이고 그 뒤에는 서버가 거른다.
/// 사유가 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
class Caution {
  const Caution({required this.reason, required this.until});

  factory Caution.fromJson(Map<String, dynamic> json) => Caution(
    reason: json['reason'] as String,
    until: DateTime.parse(json['until'] as String),
  );

  /// 칸이 없거나 null 이면 null.
  static Caution? maybe(Object? json) =>
      json == null ? null : Caution.fromJson(json as Map<String, dynamic>);

  final String reason;
  final DateTime until;
}

/// 목록 한 페이지.
class CustomerPage {
  const CustomerPage({
    required this.items,
    required this.nextCursor,
    required this.petCount,
  });

  factory CustomerPage.fromJson(Map<String, dynamic> json) => CustomerPage(
    items: (json['items'] as List)
        .map((e) => FamilyCard.fromJson(e as Map<String, dynamic>))
        .toList(),
    nextCursor: json['next_cursor'] as String?,
    petCount: json['pet_count'] as int,
  );

  final List<FamilyCard> items;

  /// 다음 페이지 커서. 해석하지 않고 그대로 돌려보낸다. 없으면 마지막 페이지.
  final String? nextCursor;

  /// 검색·무지개다리 조건에 맞는 반려동물 수("고객 N마리").
  final int petCount;
}

/// 등록 1단계의 번호 조회 결과.
class CustomerLookup {
  const CustomerLookup({
    required this.customerId,
    required this.name,
    required this.petNames,
  });

  factory CustomerLookup.fromJson(Map<String, dynamic> json) => CustomerLookup(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    petNames: (json['pet_names'] as List).cast<String>(),
  );

  final int customerId;
  final String name;

  /// 무지개다리 아이는 들어 있지 않다.
  final List<String> petNames;
}

/// 반려동물의 질병 한 항목.
class PetCondition {
  const PetCondition({
    required this.typeCode,
    required this.label,
    required this.customLabel,
    required this.note,
  });

  factory PetCondition.fromJson(Map<String, dynamic> json) => PetCondition(
    typeCode: json['type_code'] as String,
    label: json['label'] as String,
    customLabel: json['custom_label'] as String?,
    note: json['note'] as String?,
  );

  final String typeCode;

  /// 정해진 질병의 이름(기타면 "기타").
  final String label;

  /// 기타일 때만 있는 직접 입력 이름.
  final String? customLabel;
  final String? note;

  /// 화면에 보일 이름 — 기타면 직접 입력한 이름.
  String get displayLabel => customLabel ?? label;
}

/// 반려동물 전체.
/// 미용 동의를 받은 길(⑪) — 전자 서명, 또는 손으로 [받았어요].
enum ConsentVia { signature, manual }

class Pet {
  const Pet({
    required this.petId,
    required this.customerId,
    required this.name,
    required this.species,
    required this.breed,
    required this.sex,
    required this.neutered,
    required this.birthDate,
    required this.birthYear,
    required this.ageLabel,
    required this.weightKg,
    required this.noKnownConditions,
    required this.hasConditions,
    required this.conditions,
    required this.memo,
    required this.passedAwayAt,
    required this.photo,
    this.groomingConsentOn,
    this.groomingConsentVia,
  });

  factory Pet.fromJson(Map<String, dynamic> json) => Pet(
    petId: json['pet_id'] as int,
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    species: json['species'] as String,
    breed: json['breed'] as String,
    sex: json['sex'] as String,
    neutered: json['neutered'] as bool,
    birthDate: json['birth_date'] == null
        ? null
        : DateTime.parse(json['birth_date'] as String),
    birthYear: json['birth_year'] as int?,
    ageLabel: json['age_label'] as String,
    weightKg: (json['weight_kg'] as num).toDouble(),
    noKnownConditions: json['no_known_conditions'] as bool,
    hasConditions: json['has_conditions'] as bool,
    conditions: (json['conditions'] as List)
        .map((e) => PetCondition.fromJson(e as Map<String, dynamic>))
        .toList(),
    memo: json['memo'] as String?,
    passedAwayAt: json['passed_away_at'] == null
        ? null
        : DateTime.parse(json['passed_away_at'] as String),
    photo: json['photo'] as String?,
    groomingConsentOn: json['grooming_consent_on'] == null
        ? null
        : DateTime.parse(json['grooming_consent_on'] as String),
    // 모르는 값이면 손으로 적은 것으로 본다 — [서명 보기]를 잘못 보이지 않는다.
    groomingConsentVia: switch (json['grooming_consent_via']) {
      'signature' => ConsentVia.signature,
      null => null,
      _ => ConsentVia.manual,
    },
  );

  final int petId;
  final int customerId;
  final String name;

  /// 'dog' | 'cat'
  final String species;
  final String breed;

  /// 'female' | 'male'
  final String sex;
  final bool neutered;

  /// 날짜만 쓴다(시각은 자정).
  final DateTime? birthDate;
  final int? birthYear;
  final String ageLabel;
  final double weightKg;
  final bool noKnownConditions;
  final bool hasConditions;
  final List<PetCondition> conditions;
  final String? memo;
  final DateTime? passedAwayAt;

  /// 프로필 사진 썸네일 서명 URL — 상세 조회에만 온다(등록·수정 응답에는 없어 null).
  final String? photo;

  /// 미용 동의서를 받은 날(③-B). 받은 적이 없거나 지병을 더해 비워졌으면 null.
  final DateTime? groomingConsentOn;

  /// 그 동의를 어떻게 받았나(⑪) — 서명으로, 또는 손으로 적어서. 받은 것이 없으면 null.
  final ConsentVia? groomingConsentVia;

  bool get passedAway => passedAwayAt != null;
}

/// 보호자 전체. 전체 번호가 들어 있는 유일한 모델이다.
class Customer {
  const Customer({
    required this.customerId,
    required this.name,
    required this.phone,
    required this.phoneAlt,
    required this.marketingConsent,
    required this.marketingConsentChangedAt,
    required this.memo,
    this.caution,
  });

  factory Customer.fromJson(Map<String, dynamic> json) => Customer(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    phone: json['phone'] as String,
    phoneAlt: json['phone_alt'] as String?,
    marketingConsent: json['marketing_consent'] as bool,
    marketingConsentChangedAt: DateTime.parse(
      json['marketing_consent_changed_at'] as String,
    ),
    memo: json['memo'] as String?,
    caution: Caution.maybe(json['caution']),
  );

  final int customerId;
  final String name;

  /// 숫자만(`01012345678`).
  final String phone;
  final String? phoneAlt;
  final bool marketingConsent;
  final DateTime marketingConsentChangedAt;
  final String? memo;

  /// 살아 있는 주의 표시. 없거나 기한이 지났으면 null.
  final Caution? caution;
}

/// 고객 상세의 다가오는 예약 한 줄(오늘 이후 시작, 최대 3건).
class UpcomingVisit {
  const UpcomingVisit({
    required this.visitId,
    required this.petId,
    required this.petName,
    required this.startsAt,
  });

  factory UpcomingVisit.fromJson(Map<String, dynamic> json) => UpcomingVisit(
    visitId: json['visit_id'] as int,
    petId: json['pet_id'] as int?,
    petName: json['pet_name'] as String?,
    startsAt: json['starts_at'] as String,
  );

  final int visitId;

  /// null 이면 보호자만의 예약.
  final int? petId;
  final String? petName;

  /// 매장 시간대가 붙은 시각 문자열. 화면은 `core/time`의 `ShopTime`으로 읽는다.
  final String startsAt;
}

/// 고객 상세 — 보호자 전체와 반려동물 전체. 조회(GET) 응답에만 방문 요약
/// (노쇼 횟수·다가오는 예약)이 실린다 — 등록·수정 응답에는 없어 0·빈 목록이다.
class CustomerDetail {
  const CustomerDetail({
    required this.customer,
    required this.pets,
    this.noShowCount = 0,
    this.upcomingVisits = const [],
  });

  factory CustomerDetail.fromJson(Map<String, dynamic> json) => CustomerDetail(
    customer: Customer.fromJson(json['customer'] as Map<String, dynamic>),
    pets: (json['pets'] as List)
        .map((e) => Pet.fromJson(e as Map<String, dynamic>))
        .toList(),
    noShowCount: json['no_show_count'] as int? ?? 0,
    upcomingVisits: (json['upcoming_visits'] as List? ?? const [])
        .map((e) => UpcomingVisit.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final Customer customer;
  final List<Pet> pets;
  final int noShowCount;
  final List<UpcomingVisit> upcomingVisits;
}

/// 반려동물 상세의 보호자 요약. 번호는 가린 값이다.
class OwnerSummary {
  const OwnerSummary({
    required this.customerId,
    required this.name,
    required this.phoneMasked,
  });

  factory OwnerSummary.fromJson(Map<String, dynamic> json) => OwnerSummary(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    phoneMasked: json['phone_masked'] as String,
  );

  final int customerId;
  final String name;
  final String phoneMasked;
}

/// 같은 보호자의 다른 아이.
class Sibling {
  const Sibling({
    required this.petId,
    required this.name,
    required this.species,
    required this.passedAway,
  });

  factory Sibling.fromJson(Map<String, dynamic> json) => Sibling(
    petId: json['pet_id'] as int,
    name: json['name'] as String,
    species: json['species'] as String,
    passedAway: json['passed_away'] as bool,
  );

  final int petId;
  final String name;
  final String species;
  final bool passedAway;
}

/// 반려동물 상세 — 반려동물 전체, 보호자 요약, 같은 보호자의 다른 아이.
class PetDetail {
  const PetDetail({
    required this.pet,
    required this.owner,
    required this.siblings,
    this.caution,
  });

  factory PetDetail.fromJson(Map<String, dynamic> json) => PetDetail(
    pet: Pet.fromJson(json['pet'] as Map<String, dynamic>),
    owner: OwnerSummary.fromJson(json['owner'] as Map<String, dynamic>),
    siblings: (json['siblings'] as List)
        .map((e) => Sibling.fromJson(e as Map<String, dynamic>))
        .toList(),
    caution: Caution.maybe(json['caution']),
  );

  final Pet pet;
  final OwnerSummary owner;
  final List<Sibling> siblings;

  /// 보호자의 주의 표시.
  final Caution? caution;
}

/// 정해진 질병 종류 하나.
class ConditionType {
  const ConditionType({
    required this.code,
    required this.label,
    required this.sortOrder,
  });

  factory ConditionType.fromJson(Map<String, dynamic> json) => ConditionType(
    code: json['code'] as String,
    label: json['label'] as String,
    sortOrder: json['sort_order'] as int,
  );

  static const otherCode = 'other';

  final String code;
  final String label;
  final int sortOrder;
}

/// 보호자 폼(등록 2단계·보호자 수정). 전화번호는 숫자만 보낸다.
class CustomerFields {
  const CustomerFields({
    required this.name,
    required this.phone,
    required this.phoneAlt,
    required this.marketingConsent,
    required this.memo,
  });

  final String name;
  final String phone;
  final String? phoneAlt;
  final bool marketingConsent;
  final String? memo;

  Map<String, dynamic> toJson() => {
    'name': name,
    'phone': phone,
    'phone_alt': phoneAlt,
    'marketing_consent': marketingConsent,
    'memo': memo,
  };
}

/// 반려동물 폼에 넣는 질병 한 항목.
class ConditionEntry {
  const ConditionEntry({required this.typeCode, this.customLabel, this.note});

  final String typeCode;
  final String? customLabel;
  final String? note;

  Map<String, dynamic> toJson() => {
    'type_code': typeCode,
    'custom_label': customLabel,
    'note': note,
  };
}

/// 반려동물 폼(등록 3단계·반려동물 추가·수정). 생일과 태어난 해는 하나만,
/// 둘 다 없으면 "나이 모름"이다. 질병은 목록 전체를 보낸다.
class PetFields {
  const PetFields({
    required this.name,
    required this.species,
    required this.breed,
    required this.sex,
    required this.neutered,
    required this.birthDate,
    required this.birthYear,
    required this.weightKg,
    required this.noKnownConditions,
    required this.conditions,
    required this.memo,
  });

  final String name;
  final String species;
  final String breed;
  final String sex;
  final bool neutered;
  final DateTime? birthDate;
  final int? birthYear;
  final double weightKg;
  final bool noKnownConditions;
  final List<ConditionEntry> conditions;
  final String? memo;

  Map<String, dynamic> toJson() => {
    'name': name,
    'species': species,
    'breed': breed,
    'sex': sex,
    'neutered': neutered,
    'birth_date': birthDate == null ? null : _isoDate(birthDate!),
    'birth_year': birthYear,
    'weight_kg': weightKg,
    'no_known_conditions': noKnownConditions,
    'conditions': [for (final c in conditions) c.toJson()],
    'memo': memo,
  };

  static String _isoDate(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

/// 고객 카드와 보호자 계정의 연결. 매장에는 여부와 이은 날만 온다 — 보호자가
/// 누구인지는 없다(매장은 고객이 다른 매장의 사장인지 알 수 없다).
class GuardianLink {
  const GuardianLink({
    required this.linked,
    required this.linkedAt,
    this.familyCount = 0,
  });

  final bool linked;

  /// 이은 시각(매장 시간대 ISO). 연결이 없으면 null.
  final String? linkedAt;

  /// 보호자와 함께 보는 가족의 수(⑫) — 수만 온다(누구인지는 없다). 없거나 깨졌으면 0.
  final int familyCount;

  factory GuardianLink.fromJson(Map<String, dynamic> json) {
    final linkedAt = json['linked_at'];
    final familyCount = json['family_count'];
    return GuardianLink(
      linked: json['linked'] == true,
      linkedAt: linkedAt is String ? linkedAt : null,
      familyCount: familyCount is int && familyCount > 0 ? familyCount : 0,
    );
  }
}
