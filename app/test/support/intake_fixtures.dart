// 문진표 테스트가 함께 쓰는 가짜 응답(⑪-C). 이름·번호는 지어낸 것이고 주소는 가짜다.

const fakeIntakeUrl = 'https://web.test/f/FAKE-INTAKE-LINK';

Map<String, dynamic> intakeItemJson({
  int answerId = 51,
  String mode = 'new',
  String? petName = '모카',
  String? guardianName = '박새롬',
  Map<String, dynamic>? matchedCustomer,
  int? petId,
}) => {
  'answer_id': answerId,
  'mode': mode,
  'pet_name': petName,
  'guardian_name': guardianName,
  'submitted_on': '2026-11-16',
  'matched_customer': matchedCustomer,
  'pet_id': petId,
};

Map<String, dynamic> intakeAnswerJson({
  int answerId = 51,
  String mode = 'new',
  String? petName = '모카',
  String? guardianName = '박새롬',
  String? guardianPhone = '010-9999-0000',
  Map<String, dynamic>? matchedCustomer,
  int? petId,
  String? species = 'dog',
  String? breed = '푸들',
  String? sex = 'male',
  bool? neutered = false,
  String? birthDate,
  int? birthYear = 2022,
  bool birthUnknown = false,
  double? weightKg = 4.5,
  bool? noKnownConditions = true,
  List<Map<String, dynamic>> conditions = const [],
  String? dislikes = '드라이기 소리',
  String? style = '곰돌이 컷',
  List<Map<String, dynamic>> extras = const [],
  List<String> missing = const [],
  String memoDraft = '조심할 것: 드라이기 소리\n원하는 스타일: 곰돌이 컷',
  int memoOver = 0,
}) => {
  ...intakeItemJson(
    answerId: answerId, mode: mode, petName: petName, guardianName: guardianName,
    matchedCustomer: matchedCustomer, petId: petId,
  ),
  'guardian_phone': guardianPhone,
  'species': species,
  'breed': breed,
  'sex': sex,
  'neutered': neutered,
  'birth_date': birthDate,
  'birth_year': birthYear,
  'birth_unknown': birthUnknown,
  'weight_kg': weightKg,
  'no_known_conditions': noKnownConditions,
  'conditions': conditions,
  'dislikes': dislikes,
  'style': style,
  'extras': extras,
  'missing': missing,
  'memo_draft': memoDraft,
  'memo_over': memoOver,
};

Map<String, dynamic> intakeQuestionJson(int id, String label, {bool required = false}) => {
  'question_id': id,
  'label': label,
  'required': required,
};
