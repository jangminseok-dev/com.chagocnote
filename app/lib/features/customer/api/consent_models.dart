/// 전자 동의서(⑪-A)의 모델. 서버 응답의 필드명을 그대로 읽는다.
///
/// **링크 주소에는 토큰이 들어 있고, 서명에는 적은 이름이 들어 있다** — 로그에 찍히지 않도록
/// `toString`을 오버라이드하지 않는다. 모르는 토막·길(channel)은 그 항목을 버린다 — 서버가 더해도 옛 앱이 죽지 않게.
library;

import '../../../core/time/shop_time.dart';
import 'intake_models.dart';

/// 동의서의 토막. 문서의 순서 그대로다.
enum ConsentPart { basic, senior, condition }

/// 서명을 받은 길.
enum SignatureChannel {
  link('link'),
  inShop('in_shop');

  const SignatureChannel(this.wire);

  final String wire;
}

T? _byName<T>(List<T> values, String Function(T) name, Object? wire) {
  for (final v in values) {
    if (name(v) == wire) return v;
  }
  return null;
}

ConsentPart? _part(Object? wire) => _byName(ConsentPart.values, (p) => p.name, wire);

List<ConsentPart> _parts(Object? list) => list is! List
    ? const []
    : [
        // 문서의 순서로 맞춘다 — 서버가 다른 순서로 줘도 화면의 순서는 같다.
        for (final part in ConsentPart.values)
          if (list.contains(part.name)) part,
      ];

List<String> _strings(Object? list) => list is! List ? const [] : [for (final v in list) if (v is String) v];

/// 보호자에게 보낼 동의서 링크.
class FormLink {
  const FormLink({required this.formId, required this.url, required this.expiresOn, required this.sentOn});

  factory FormLink.fromJson(Map<String, dynamic> json) => FormLink(
    formId: json['form_id'] as int,
    url: json['url'] as String,
    expiresOn: parseDay(json['expires_on'] as String),
    sentOn: parseDay(json['sent_on'] as String),
  );

  final int formId;
  final String url;
  final DateTime expiresOn;
  final DateTime sentOn;
}

/// 서류의 종류.
enum FormKind { consent, intake }

/// 보낸 서류 한 줄 — 살아 있는 요청(동의서·문진표). **[url] 에는 토큰이 들어 있다 — 로그에 남기지 않는다.**
class SentForm {
  const SentForm({
    required this.formId,
    required this.kind,
    required this.mode,
    required this.customerId,
    required this.customerName,
    required this.pets,
    required this.sentOn,
    required this.expiresOn,
    required this.url,
  });

  /// 모르는 종류이거나 모양이 깨진 줄이면 `null` — 목록에서 뺀다(나머지는 보인다).
  static SentForm? tryParse(Object? raw) {
    if (raw is! Map<String, dynamic>) return null;
    final kind = FormKind.values.where((k) => k.name == raw['kind']).firstOrNull;
    final formId = raw['form_id'];
    final sentOn = raw['sent_on'];
    final expiresOn = raw['expires_on'];
    final url = raw['url'];
    if (kind == null || formId is! int || sentOn is! String || expiresOn is! String || url is! String) return null;
    final mode = IntakeMode.parse(raw['mode']);
    if (kind == FormKind.intake && mode == null) return null;
    // 새 손님용 문진표에는 고객이 없다.
    final customer = raw['customer'];
    return SentForm(
      formId: formId,
      kind: kind,
      mode: kind == FormKind.intake ? mode : null,
      customerId: customer is Map<String, dynamic> ? customer['customer_id'] as int? : null,
      customerName: customer is Map<String, dynamic> ? customer['name'] as String? : null,
      pets: [
        for (final pet in raw['pets'] as List? ?? const [])
          if (pet is Map<String, dynamic> && pet['pet_id'] is int)
            (petId: pet['pet_id'] as int, name: pet['name'] as String? ?? ''),
      ],
      sentOn: parseDay(sentOn),
      expiresOn: parseDay(expiresOn),
      url: url,
    );
  }

  static List<SentForm> listFrom(List<dynamic> items) => [for (final raw in items) ?tryParse(raw)];

  final int formId;
  final FormKind kind;
  final IntakeMode? mode; // 문진표를 보낸 곳. 동의서는 null
  final int? customerId; // 새 손님용 문진표는 null
  final String? customerName;
  final List<({int petId, String name})> pets;
  final DateTime sentOn;
  final DateTime expiresOn;
  final String url;
}

/// 동의서 한 장에서 아이 하나의 구역.
class DocumentPet {
  const DocumentPet({required this.petId, required this.name, required this.conditions, required this.parts});

  final int petId;
  final String name;

  /// 알려 준 지병의 이름(메모는 오지 않는다).
  final List<String> conditions;

  /// 이번에 읽고 서명할 토막.
  final List<ConsentPart> parts;
}

/// 매장에서 바로 서명받을 동의서 — 서버가 아이의 지금 사실로 조립한 것이다.
class ConsentDocument {
  const ConsentDocument({required this.pets, required this.texts, required this.previousConsentOn, required this.digest});

  factory ConsentDocument.fromJson(Map<String, dynamic> json) {
    final texts = <ConsentPart, String>{};
    final rawTexts = json['texts'];
    if (rawTexts is Map) {
      for (final part in ConsentPart.values) {
        final text = rawTexts[part.name];
        if (text is Map && text['body'] is String) texts[part] = text['body'] as String;
      }
    }
    final previous = json['previous_consent_on'];
    return ConsentDocument(
      pets: [
        for (final pet in json['pets'] as List)
          DocumentPet(
            petId: (pet as Map)['pet_id'] as int,
            name: pet['name'] as String? ?? '',
            conditions: _strings(pet['conditions']),
            parts: [for (final part in _parts(pet['parts'])) if (texts.containsKey(part)) part],
          ),
      ],
      texts: texts,
      previousConsentOn: previous is String ? parseDay(previous) : null,
      digest: json['doc_digest'] as String,
    );
  }

  final List<DocumentPet> pets;
  final Map<ConsentPart, String> texts;

  /// 바뀐 부분만 받을 때의 지난 동의 날.
  final DateTime? previousConsentOn;

  /// 읽은 문서의 지문 — 낼 때 그대로 돌려보낸다.
  final String digest;

  /// 이 문서가 쓰는 토막, 문서의 순서로.
  List<ConsentPart> get parts => [
    for (final part in ConsentPart.values)
      if (texts.containsKey(part)) part,
  ];
}

/// 서명 목록의 한 줄.
class SignatureBrief {
  const SignatureBrief({
    required this.signatureId,
    required this.signedAt,
    required this.channel,
    required this.signerName,
    required this.parts,
  });

  /// 모르는 길이거나 모양이 깨졌으면 null.
  static SignatureBrief? tryParse(Object? json) {
    if (json is! Map) return null;
    final channel = _byName(SignatureChannel.values, (c) => c.wire, json['channel']);
    final id = json['signature_id'];
    final at = json['signed_at'];
    final signedAt = at is String ? DateTime.tryParse(at) : null;
    if (channel == null || id is! int || signedAt == null) return null;
    return SignatureBrief(
      signatureId: id,
      signedAt: signedAt,
      channel: channel,
      signerName: json['signer_name'] as String? ?? '',
      parts: _parts(json['parts']),
    );
  }

  final int signatureId;
  final DateTime signedAt;
  final SignatureChannel channel;
  final String signerName;
  final List<ConsentPart> parts;
}

/// 서명 한 장에서 아이 하나 — 그때 보인 이름·지병과 읽은 글.
class SignaturePet {
  const SignaturePet({required this.petId, required this.shownName, required this.conditions, required this.parts});

  final int? petId;
  final String shownName;
  final List<String> conditions;
  final List<({ConsentPart part, String body})> parts;
}

class SignatureDetail {
  const SignatureDetail({
    required this.signatureId,
    required this.signedAt,
    required this.channel,
    required this.signerName,
    required this.pets,
  });

  factory SignatureDetail.fromJson(Map<String, dynamic> json) => SignatureDetail(
    signatureId: json['signature_id'] as int,
    signedAt: DateTime.parse(json['signed_at'] as String),
    channel: _byName(SignatureChannel.values, (c) => c.wire, json['channel']) ?? SignatureChannel.link,
    signerName: json['signer_name'] as String? ?? '',
    pets: [
      for (final pet in json['pets'] as List)
        SignaturePet(
          petId: (pet as Map)['pet_id'] as int?,
          shownName: pet['shown_name'] as String? ?? '',
          conditions: _strings(pet['conditions']),
          parts: [
            for (final item in pet['parts'] as List)
              if (_part((item as Map)['part']) case final part?) (part: part, body: item['body'] as String? ?? ''),
          ],
        ),
    ],
  );

  final int signatureId;
  final DateTime signedAt;
  final SignatureChannel channel;
  final String signerName;
  final List<SignaturePet> pets;
}
