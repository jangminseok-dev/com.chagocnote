/// 알림톡(⑥)의 응답 모델. 화면이 쓰는 칸만 읽는다. 전화번호와 `share_text`(알림장 주소가 들 수 있다)가
/// 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
library;

import '../../../core/time/shop_time.dart';

ShopTime? _time(Object? value) =>
    value == null ? null : ShopTime.parse(value as String);

T? _byCode<T extends Enum>(
  List<T> values,
  String Function(T) code,
  Object? raw,
) {
  for (final value in values) {
    if (code(value) == raw) return value;
  }
  return null;
}

/// 메시지 종류 여섯.
enum NotificationKind {
  confirm('confirm'),
  reminder('reminder'),
  report('report'),
  change('change'),
  cancel('cancel'),
  nextVisit('next_visit');

  const NotificationKind(this.wire);

  /// 서버 값(경로에도 쓴다).
  final String wire;

  static NotificationKind? tryParse(Object? raw) =>
      _byCode(values, (k) => k.wire, raw);
}

enum NotificationStatus {
  scheduled('scheduled'),
  sending('sending'),
  accepted('accepted'),
  sent('sent'),
  fallbackSent('fallback_sent'),
  failed('failed'),
  canceled('canceled');

  const NotificationStatus(this.wire);

  final String wire;

  static NotificationStatus? tryParse(Object? raw) =>
      _byCode(values, (s) => s.wire, raw);

  /// 아직 결과가 나지 않았다(예정·보내는 중·접수).
  bool get pending => switch (this) {
    scheduled || sending || accepted => true,
    sent || fallbackSent || failed || canceled => false,
  };
}

enum NotificationErrorKind {
  transient('transient'),
  permanent('permanent');

  const NotificationErrorKind(this.wire);

  final String wire;

  static NotificationErrorKind? tryParse(Object? raw) =>
      _byCode(values, (e) => e.wire, raw);
}

enum ChannelStatus {
  none('none'),
  tokenRequested('token_requested'),
  linked('linked'),
  unlinked('unlinked');

  const ChannelStatus(this.wire);

  final String wire;

  /// 모르는 값은 연동 전으로 본다.
  static ChannelStatus parse(Object? raw) =>
      _byCode(values, (s) => s.wire, raw) ?? ChannelStatus.none;
}

enum TemplateStatus {
  pending('pending'),
  approved('approved'),
  rejected('rejected');

  const TemplateStatus(this.wire);

  final String wire;

  /// 모르는 값은 심사 중으로 본다.
  static TemplateStatus parse(Object? raw) =>
      _byCode(values, (s) => s.wire, raw) ?? TemplateStatus.pending;
}

/// 매장 채널의 연동 상태와 문자 대체.
class NotificationChannel {
  const NotificationChannel({
    required this.status,
    required this.linkedAt,
    required this.senderNumber,
    required this.senderVerified,
    required this.smsFallbackEnabled,
  });

  factory NotificationChannel.fromJson(Map<String, dynamic> json) =>
      NotificationChannel(
        status: ChannelStatus.parse(json['status']),
        linkedAt: _time(json['linked_at']),
        senderNumber: json['sender_number'] as String?,
        senderVerified: json['sender_verified'] as bool? ?? false,
        smsFallbackEnabled: json['sms_fallback_enabled'] as bool? ?? false,
      );

  final ChannelStatus status;
  final ShopTime? linkedAt;

  /// 문자 대체의 발신번호 — 매장 자기 번호라 화면에 보인다.
  final String? senderNumber;
  final bool senderVerified;
  final bool smsFallbackEnabled;
}

/// 종류별 켜짐과 시각·주기(overview 의 `settings` 여덟 칸).
class NotificationSettings {
  const NotificationSettings({
    required this.confirmEnabled,
    required this.reminderEnabled,
    required this.reportEnabled,
    required this.changeEnabled,
    required this.nextVisitEnabled,
    required this.reminderTime,
    required this.nextVisitAfterWeeks,
    required this.nextVisitCooldownDays,
  });

  factory NotificationSettings.fromJson(Map<String, dynamic> json) =>
      NotificationSettings(
        confirmEnabled: json['confirm_enabled'] as bool,
        reminderEnabled: json['reminder_enabled'] as bool,
        reportEnabled: json['report_enabled'] as bool,
        changeEnabled: json['change_enabled'] as bool,
        nextVisitEnabled: json['next_visit_enabled'] as bool,
        reminderTime: json['reminder_time'] as String,
        nextVisitAfterWeeks: json['next_visit_after_weeks'] as int?,
        nextVisitCooldownDays: json['next_visit_cooldown_days'] as int,
      );

  final bool confirmEnabled;
  final bool reminderEnabled;
  final bool reportEnabled;

  /// 변경과 취소 안내를 함께 켠다.
  final bool changeEnabled;
  final bool nextVisitEnabled;

  /// "HH:MM"(매장 시간대).
  final String reminderTime;

  /// null 이면 지난 방문 간격대로.
  final int? nextVisitAfterWeeks;
  final int nextVisitCooldownDays;

  Map<String, dynamic> toJson() => {
    'confirm_enabled': confirmEnabled,
    'reminder_enabled': reminderEnabled,
    'report_enabled': reportEnabled,
    'change_enabled': changeEnabled,
    'next_visit_enabled': nextVisitEnabled,
    'reminder_time': reminderTime,
    'next_visit_after_weeks': nextVisitAfterWeeks,
    'next_visit_cooldown_days': nextVisitCooldownDays,
  };
}

/// 종류별 템플릿의 심사 상태. 반려 사유는 읽지 않는다 — 문구는 [status]로만 고른다(승인된 종류의 새 판이
/// 반려되면 `approved` 인데도 사유가 차 있을 수 있다).
class NotificationTemplate {
  const NotificationTemplate({required this.kind, required this.status});

  final NotificationKind kind;
  final TemplateStatus status;
}

/// 알림톡 한눈에 보기(GET·설정 PUT·연동·발신번호 인증의 응답).
class NotificationOverview {
  const NotificationOverview({
    required this.channel,
    required this.settings,
    required this.templates,
  });

  factory NotificationOverview.fromJson(Map<String, dynamic> json) {
    final settings = json['settings'] as Map<String, dynamic>?;
    return NotificationOverview(
      channel: NotificationChannel.fromJson(
        json['channel'] as Map<String, dynamic>,
      ),
      settings: settings == null
          ? null
          : NotificationSettings.fromJson(settings),
      templates: [
        for (final e in json['templates'] as List)
          if (NotificationKind.tryParse((e as Map<String, dynamic>)['kind'])
              case final kind?)
            NotificationTemplate(
              kind: kind,
              status: TemplateStatus.parse(e['status']),
            ),
      ],
    );
  }

  final NotificationChannel channel;

  /// 연동 전·해제 뒤에는 null.
  final NotificationSettings? settings;
  final List<NotificationTemplate> templates;

  /// 그 종류의 템플릿 상태. 등록한 적이 없으면 null.
  TemplateStatus? templateOf(NotificationKind kind) {
    for (final template in templates) {
      if (template.kind == kind) return template.status;
    }
    return null;
  }

  /// 설정 PUT 의 본문 아홉 칸 — 설정 여덟에 채널의 문자 대체를 더한다. [field] 한 칸만 [value]로 바꾼다.
  Map<String, dynamic> settingsBody({String? field, Object? value}) {
    final current = settings;
    if (current == null) throw StateError('연동 전에는 설정이 없다');
    return {
      ...current.toJson(),
      'sms_fallback_enabled': channel.smsFallbackEnabled,
      ?field: value,
    };
  }
}

/// 방문의 알림 줄 하나.
class NotificationMessage {
  const NotificationMessage({
    required this.messageId,
    required this.kind,
    required this.status,
    required this.scheduledAt,
    required this.sentAt,
    required this.errorKind,
    required this.shareText,
  });

  /// 모르는 종류·상태면 null — 서버가 값을 더해도 화면이 죽지 않게 그 줄만 뺀다.
  static NotificationMessage? tryFromJson(Map<String, dynamic> json) {
    final kind = NotificationKind.tryParse(json['kind']);
    final status = NotificationStatus.tryParse(json['status']);
    if (kind == null || status == null) return null;
    return NotificationMessage(
      messageId: json['message_id'] as int,
      kind: kind,
      status: status,
      scheduledAt: ShopTime.parse(json['scheduled_at'] as String),
      sentAt: _time(json['sent_at']),
      errorKind: NotificationErrorKind.tryParse(json['error_kind']),
      shareText: json['share_text'] as String?,
    );
  }

  static List<NotificationMessage> listFromJson(Map<String, dynamic> json) => [
    for (final e in json['items'] as List)
      ?tryFromJson(e as Map<String, dynamic>),
  ];

  final int messageId;
  final NotificationKind kind;
  final NotificationStatus status;

  /// 보낼 시각(즉시 줄은 만든 시각).
  final ShopTime scheduledAt;
  final ShopTime? sentAt;

  /// 실패한 줄에만.
  final NotificationErrorKind? errorKind;

  /// 실패한 줄에만 — 다른 방법으로 보낼 문자용 문안. 알림장이면 주소(토큰)가 들어 있다.
  final String? shareText;
}
