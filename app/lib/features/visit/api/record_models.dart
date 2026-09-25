/// 미용 기록(④)의 응답·요청 모델. 메모·금액이 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
library;

/// 결제 수단. 서버에는 [code]를 보낸다.
enum PaymentMethod {
  card('card'),
  cash('cash'),
  transfer('transfer');

  const PaymentMethod(this.code);

  final String code;

  static PaymentMethod? fromCode(String? code) =>
      code == null ? null : values.firstWhere((m) => m.code == code);
}

/// 사진이 미용 전인지 후인지.
enum MediaPhase {
  before('before'),
  after('after');

  const MediaPhase(this.code);

  final String code;

  static MediaPhase fromCode(String code) =>
      values.firstWhere((p) => p.code == code);
}

/// 사진·영상. 영상은 ④-3 에서 올리고, 지금은 받아서 보여 주기만 한다.
enum MediaKind {
  photo('photo'),
  video('video');

  const MediaKind(this.code);

  final String code;

  static MediaKind fromCode(String code) =>
      values.firstWhere((k) => k.code == code);
}

/// 기록의 실제 메뉴와 받은 금액.
class RecordItem {
  const RecordItem({
    required this.menuId,
    required this.name,
    required this.amount,
  });

  factory RecordItem.fromJson(Map<String, dynamic> json) => RecordItem(
    menuId: json['menu_id'] as int,
    name: json['name'] as String,
    amount: json['amount'] as int,
  );

  final int menuId;
  final String name;
  final int amount;
}

/// 기록에 붙은 사진·영상 하나. URL 은 서명 URL 이라 하루 뒤 바뀐다(캐시 키는 사진 로더가 정한다).
class RecordMedia {
  const RecordMedia({
    required this.mediaId,
    required this.kind,
    required this.phase,
    required this.sortOrder,
    required this.originalUrl,
    required this.displayUrl,
    required this.thumbUrl,
    required this.width,
    required this.height,
    required this.durationSeconds,
  });

  factory RecordMedia.fromJson(Map<String, dynamic> json) => RecordMedia(
    mediaId: json['media_id'] as int,
    kind: MediaKind.fromCode(json['kind'] as String),
    phase: MediaPhase.fromCode(json['phase'] as String),
    sortOrder: json['sort_order'] as int,
    originalUrl: json['original_url'] as String,
    displayUrl: json['display_url'] as String?,
    thumbUrl: json['thumb_url'] as String,
    width: json['width'] as int,
    height: json['height'] as int,
    durationSeconds: json['duration_seconds'] as int?,
  );

  final int mediaId;
  final MediaKind kind;
  final MediaPhase phase;
  final int sortOrder;
  final String originalUrl;

  /// 영상이면 null.
  final String? displayUrl;

  /// 영상이면 포스터.
  final String thumbUrl;
  final int width;
  final int height;
  final int? durationSeconds;
}

/// 방문 하나의 미용 기록. [version]은 다음 전체 교체에 그대로 보낸다(설계 8절).
class VisitRecord {
  const VisitRecord({
    required this.visitId,
    required this.weightKg,
    required this.careNote,
    required this.internalNote,
    required this.paymentMethod,
    required this.totalAmount,
    required this.items,
    required this.media,
    required this.version,
  });

  factory VisitRecord.fromJson(Map<String, dynamic> json) => VisitRecord(
    visitId: json['visit_id'] as int,
    weightKg: (json['weight_kg'] as num?)?.toDouble(),
    careNote: json['care_note'] as String?,
    internalNote: json['internal_note'] as String?,
    paymentMethod: PaymentMethod.fromCode(json['payment_method'] as String?),
    totalAmount: json['total_amount'] as int?,
    items: [
      for (final e in json['items'] as List)
        RecordItem.fromJson(e as Map<String, dynamic>),
    ],
    media: [
      for (final e in json['media'] as List)
        RecordMedia.fromJson(e as Map<String, dynamic>),
    ],
    version: json['version'] as int,
  );

  final int visitId;
  final double? weightKg;

  /// 알림장(⑤)에 그대로 실리는 공개 메모.
  final String? careNote;

  /// 매장만 보는 메모.
  final String? internalNote;
  final PaymentMethod? paymentMethod;

  /// 받은 돈 — 항목 합과 따로 저장한다(할인은 이 값을 고쳐 표현한다).
  final int? totalAmount;
  final List<RecordItem> items;

  /// 전 → 후, 칸마다 순서대로.
  final List<RecordMedia> media;
  final int version;
}

/// 기록 안에서 사진 하나의 자리.
class MediaPlacement {
  const MediaPlacement({
    required this.mediaId,
    required this.phase,
    required this.sortOrder,
  });

  final int mediaId;
  final MediaPhase phase;
  final int sortOrder;

  Map<String, dynamic> toJson() => {
    'media_id': mediaId,
    'phase': phase.code,
    'sort_order': sortOrder,
  };
}

/// 기록 전체 교체 요청. 비운 칸은 지운다. [version]은 읽은 기록의 버전(기록이 없었으면 null).
class RecordInput {
  const RecordInput({
    required this.version,
    required this.weightKg,
    required this.careNote,
    required this.internalNote,
    required this.paymentMethod,
    required this.totalAmount,
    required this.items,
    required this.media,
  });

  final int? version;
  final double? weightKg;
  final String? careNote;
  final String? internalNote;
  final PaymentMethod? paymentMethod;
  final int? totalAmount;

  /// (메뉴 ID, 금액).
  final List<({int menuId, int amount})> items;
  final List<MediaPlacement> media;

  Map<String, dynamic> toJson() => {
    'version': ?version,
    'weight_kg': weightKg,
    'care_note': careNote,
    'internal_note': internalNote,
    'payment_method': paymentMethod?.code,
    'total_amount': totalAmount,
    'items': [
      for (final i in items) {'menu_id': i.menuId, 'amount': i.amount},
    ],
    'media': [for (final m in media) m.toJson()],
  };
}
