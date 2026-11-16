import 'consent_models.dart';

/// 서류 설정의 다섯 값(⑪-B) — 링크 기간·노령 나이·동의 기한과 보호자에게 보내는 글의 템플릿 둘.
class FormSettingsValues {
  const FormSettingsValues({
    required this.linkDays,
    required this.seniorAge,
    required this.consentDays,
    required this.reservationText,
    required this.consentText,
  });

  factory FormSettingsValues.fromJson(Map<String, dynamic> json) => FormSettingsValues(
    linkDays: json['link_days'] as int,
    seniorAge: json['senior_age'] as int,
    consentDays: json['consent_days'] as int,
    reservationText: json['reservation_text'] as String,
    consentText: json['consent_text'] as String,
  );

  final int linkDays; // 링크를 열 수 있는 날 수(1~30)
  final int seniorAge; // 노령으로 보는 나이(5~20)
  final int consentDays; // 동의를 다시 받는 날 수(30~1095)
  final String reservationText; // 예약 안내의 템플릿 — 지금 쓰는 글(고치지 않았으면 기본 글)
  final String consentText; // 동의서 링크를 보내는 글의 템플릿
}

/// 매장의 서류 설정 — 지금 값과 기본값([defaults]). 화면에 빈칸이 없다.
class FormSettings extends FormSettingsValues {
  const FormSettings({
    required super.linkDays,
    required super.seniorAge,
    required super.consentDays,
    required super.reservationText,
    required super.consentText,
    required this.defaults,
  });

  factory FormSettings.fromJson(Map<String, dynamic> json) {
    final now = FormSettingsValues.fromJson(json);
    return FormSettings(
      linkDays: now.linkDays,
      seniorAge: now.seniorAge,
      consentDays: now.consentDays,
      reservationText: now.reservationText,
      consentText: now.consentText,
      defaults: FormSettingsValues.fromJson(json['defaults'] as Map<String, dynamic>),
    );
  }

  final FormSettingsValues defaults;

  FormSettings copyWith({
    int? linkDays,
    int? seniorAge,
    int? consentDays,
    String? reservationText,
    String? consentText,
  }) => FormSettings(
    linkDays: linkDays ?? this.linkDays,
    seniorAge: seniorAge ?? this.seniorAge,
    consentDays: consentDays ?? this.consentDays,
    reservationText: reservationText ?? this.reservationText,
    consentText: consentText ?? this.consentText,
    defaults: defaults,
  );

  /// 전체 교체의 본문. 기본 글 그대로인 글은 `null` 로 보낸다 — 고치지 않은 것으로 남는다.
  Map<String, dynamic> toJson() => {
    'link_days': linkDays,
    'senior_age': seniorAge,
    'consent_days': consentDays,
    'reservation_text': reservationText == defaults.reservationText ? null : reservationText,
    'consent_text': consentText == defaults.consentText ? null : consentText,
  };
}

/// 서류 설정의 범위 — 서버의 규칙과 같다(벗어나면 422).
const linkDaysRange = (1, 30);
const seniorAgeRange = (5, 20);
const consentDaysRange = (30, 1095);
const consentBodyMax = 2000;
const bundleTextMax = 500;

/// 보내는 글에 넣을 수 있는 자리.
const reservationSlots = ['{매장}', '{아이}', '{날짜}', '{시간}', '{메뉴}'];
const consentSlots = ['{매장}', '{아이}', '{링크}'];
const linkSlot = '{링크}';

/// 동의서 토막 하나의 글 — 지금 글과 기본 글.
class ConsentTextPart {
  const ConsentTextPart({required this.part, required this.body, required this.edited, required this.defaultBody});

  /// 모르는 토막이면 `null` — 목록에서 뺀다.
  static ConsentTextPart? tryParse(Object? raw) {
    if (raw is! Map<String, dynamic>) return null;
    final part = ConsentPart.values.where((p) => p.name == raw['part']).firstOrNull;
    final body = raw['body'];
    final defaultBody = raw['default_body'];
    if (part == null || body is! String || defaultBody is! String) return null;
    return ConsentTextPart(part: part, body: body, edited: raw['edited'] == true, defaultBody: defaultBody);
  }

  final ConsentPart part;
  final String body;
  final bool edited; // 매장이 고친 글인가
  final String defaultBody;
}
