import '../../../core/time/shop_time.dart';

/// 문진표를 보낸 곳(⑪-C). 새 손님 · 등록된 고객의 새 아이 · 이미 있는 아이의 정보를 다시 받기.
enum IntakeMode {
  newGuest('new'),
  addPet('add_pet'),
  update('update');

  const IntakeMode(this.wire);

  final String wire;

  static IntakeMode? parse(Object? wire) {
    for (final mode in values) {
      if (mode.wire == wire) return mode;
    }
    return null;
  }
}

typedef MatchedCustomer = ({int customerId, String name});

/// 받은 문진표 한 줄. **이름이 들어 있다 — 로그·오류 문구에 남기지 않는다.**
class IntakeAnswerItem {
  const IntakeAnswerItem({
    required this.answerId,
    required this.mode,
    required this.petName,
    required this.guardianName,
    required this.submittedOn,
    required this.matchedCustomer,
    required this.petId,
  });

  /// 모르는 보내는 곳이거나 모양이 깨진 줄이면 `null` — 목록에서 뺀다(나머지는 보인다).
  static IntakeAnswerItem? tryParse(Object? raw) {
    if (raw is! Map<String, dynamic>) return null;
    final answerId = raw['answer_id'];
    final mode = IntakeMode.parse(raw['mode']);
    final submittedOn = raw['submitted_on'];
    if (answerId is! int || mode == null || submittedOn is! String) return null;
    final matched = raw['matched_customer'];
    return IntakeAnswerItem(
      answerId: answerId,
      mode: mode,
      petName: raw['pet_name'] as String?,
      guardianName: raw['guardian_name'] as String?,
      submittedOn: parseDay(submittedOn),
      matchedCustomer: matched is Map<String, dynamic> && matched['customer_id'] is int
          ? (customerId: matched['customer_id'] as int, name: matched['name'] as String? ?? '')
          : null,
      petId: raw['pet_id'] as int?,
    );
  }

  final int answerId;
  final IntakeMode mode;
  final String? petName; // 답에 적은 이름. 다시 받기면 그 아이의 지금 이름
  final String? guardianName;
  final DateTime submittedOn;
  final MatchedCustomer? matchedCustomer; // 미리 이어 둔 등록된 고객
  final int? petId; // 다시 받기일 때 — 그 아이
}

class IntakeCondition {
  const IntakeCondition({required this.typeCode, required this.label, this.customLabel, this.note});

  final String typeCode;
  final String label;
  final String? customLabel;
  final String? note;
}

/// 받은 문진표 한 장 — 답 전부. 끈 칸·모르겠어요·적지 않은 칸은 `null` 이다(지어내지 않는다).
class IntakeAnswer extends IntakeAnswerItem {
  const IntakeAnswer({
    required super.answerId,
    required super.mode,
    required super.petName,
    required super.guardianName,
    required super.submittedOn,
    required super.matchedCustomer,
    required super.petId,
    required this.guardianPhone,
    required this.species,
    required this.breed,
    required this.sex,
    required this.neutered,
    required this.birthDate,
    required this.birthYear,
    required this.birthUnknown,
    required this.weightKg,
    required this.noKnownConditions,
    required this.conditions,
    required this.dislikes,
    required this.style,
    required this.extras,
    required this.missing,
    required this.memoDraft,
    required this.memoOver,
  });

  factory IntakeAnswer.fromJson(Map<String, dynamic> json) {
    final item = IntakeAnswerItem.tryParse(json);
    if (item == null) throw const FormatException('받은 문진표의 모양이 다르다');
    return IntakeAnswer(
      answerId: item.answerId,
      mode: item.mode,
      petName: item.petName,
      guardianName: item.guardianName,
      submittedOn: item.submittedOn,
      matchedCustomer: item.matchedCustomer,
      petId: item.petId,
      guardianPhone: json['guardian_phone'] as String?,
      species: json['species'] as String?,
      breed: json['breed'] as String?,
      sex: json['sex'] as String?,
      neutered: json['neutered'] as bool?,
      birthDate: json['birth_date'] is String ? parseDay(json['birth_date'] as String) : null,
      birthYear: json['birth_year'] as int?,
      birthUnknown: json['birth_unknown'] == true,
      weightKg: (json['weight_kg'] as num?)?.toDouble(),
      noKnownConditions: json['no_known_conditions'] as bool?,
      conditions: [
        for (final raw in json['conditions'] as List? ?? const [])
          if (raw is Map<String, dynamic> && raw['type_code'] is String)
            IntakeCondition(
              typeCode: raw['type_code'] as String,
              label: raw['label'] as String? ?? '',
              customLabel: raw['custom_label'] as String?,
              note: raw['note'] as String?,
            ),
      ],
      dislikes: json['dislikes'] as String?,
      style: json['style'] as String?,
      extras: [
        for (final raw in json['extras'] as List? ?? const [])
          if (raw is Map<String, dynamic>) (label: raw['label'] as String? ?? '', body: raw['body'] as String? ?? ''),
      ],
      missing: [
        for (final code in json['missing'] as List? ?? const [])
          if (code is String) code,
      ],
      memoDraft: json['memo_draft'] as String? ?? '',
      memoOver: json['memo_over'] as int? ?? 0,
    );
  }

  final String? guardianPhone;
  final String? species;
  final String? breed;
  final String? sex;
  final bool? neutered;
  final DateTime? birthDate;
  final int? birthYear;
  final bool birthUnknown; // 몰라요를 골랐다
  final double? weightKg;
  final bool? noKnownConditions; // null 이면 답하지 않았다(다시 받기)
  final List<IntakeCondition> conditions;
  final String? dislikes;
  final String? style;
  final List<({String label, String body})> extras; // 매장이 더한 질문과 답
  final List<String> missing; // 등록에 꼭 있어야 하는데 빈 칸의 코드(species·breed·sex·neutered·weight)
  final String memoDraft; // 반려동물 메모의 초안
  final int memoOver; // 메모 칸(500자)을 넘친 글자 수
}

/// 매장이 문진표에 더한 질문. [questionId] 가 `null` 이면 아직 저장하지 않은 새 질문이다.
class IntakeQuestion {
  const IntakeQuestion({required this.questionId, required this.label, required this.required});

  static IntakeQuestion? tryParse(Object? raw) {
    if (raw is! Map<String, dynamic> || raw['question_id'] is! int || raw['label'] is! String) return null;
    return IntakeQuestion(
      questionId: raw['question_id'] as int,
      label: raw['label'] as String,
      required: raw['required'] == true,
    );
  }

  final int? questionId;
  final String label;
  final bool required;

  Map<String, dynamic> toJson() => {'question_id': questionId, 'label': label, 'required': required};
}

/// 질문의 한도 — 서버의 규칙과 같다.
const intakeQuestionMax = 5;
const intakeQuestionLabelMax = 100;

/// 문진표에서 매장이 끌 수 있는 칸(서버의 순서). 보호자·아이 이름·지병·개인정보 안내는 끌 수 없다.
const intakeHideable = ['species', 'breed', 'sex', 'neutered', 'birth', 'weight', 'dislikes', 'style'];
