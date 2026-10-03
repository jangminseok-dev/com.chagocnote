/// 미용 알림장(⑤)의 응답·요청 모델. 화면이 쓰는 칸만 읽는다. 메모와 링크 주소(토큰이 들어 있다)가
/// 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
library;

import '../../../core/time/shop_time.dart';
import 'record_models.dart';

ShopTime? _time(Object? value) =>
    value == null ? null : ShopTime.parse(value as String);

/// 알림장 링크의 상태(방문 상세의 `report`, 미리보기의 `link`). 살아 있지 않으면 나머지는 null.
class ReportLink {
  const ReportLink({
    required this.live,
    required this.url,
    required this.expiresAt,
    required this.firstViewedAt,
    required this.createdAt,
  });

  factory ReportLink.fromJson(Map<String, dynamic> json) => ReportLink(
    live: json['status'] == 'live',
    url: json['url'] as String?,
    expiresAt: _time(json['expires_at']),
    firstViewedAt: _time(json['first_viewed_at']),
    createdAt: _time(json['created_at']),
  );

  /// 보호자가 열 수 있는 링크가 있다('보냄').
  final bool live;

  /// 공유 시트에 넘길 주소. 토큰이 들어 있다 — 로그·오류 문구에 싣지 않는다.
  final String? url;

  /// null 이면 기간이 없다(계속).
  final ShopTime? expiresAt;

  /// 보호자가 처음 연 시각. 아직 안 열었으면 null.
  final ShopTime? firstViewedAt;

  /// 링크를 만든 시각 — '보냄'의 시점이다.
  final ShopTime? createdAt;
}

/// 미리보기 격자의 사진·영상 하나.
class ReportMedia {
  const ReportMedia({
    required this.mediaId,
    required this.kind,
    required this.phase,
    required this.hidden,
    required this.durationSeconds,
    required this.thumbUrl,
  });

  factory ReportMedia.fromJson(Map<String, dynamic> json) => ReportMedia(
    mediaId: json['media_id'] as int,
    kind: MediaKind.fromCode(json['kind'] as String),
    phase: MediaPhase.fromCode(json['phase'] as String),
    hidden: json['hidden'] as bool,
    durationSeconds: json['duration_seconds'] as int?,
    thumbUrl: json['thumb_url'] as String,
  );

  final int mediaId;
  final MediaKind kind;
  final MediaPhase phase;

  /// 알림장에서 뺀 것.
  final bool hidden;
  final int? durationSeconds;

  /// 영상이면 포스터.
  final String thumbUrl;
}

/// 알림장 설정(요청·응답이 같은 모양). 다섯 칸 전체 교체.
class ReportSettings {
  const ReportSettings({
    required this.linkDays,
    required this.showMenus,
    required this.showShopInfo,
    required this.showWeight,
    required this.showAmount,
  });

  factory ReportSettings.fromJson(Map<String, dynamic> json) => ReportSettings(
    linkDays: json['link_days'] as int?,
    showMenus: json['show_menus'] as bool,
    showShopInfo: json['show_shop_info'] as bool,
    showWeight: json['show_weight'] as bool,
    showAmount: json['show_amount'] as bool,
  );

  /// 링크 기간(일) — 7·30, null 이면 무기한.
  final int? linkDays;
  final bool showMenus;
  final bool showShopInfo;
  final bool showWeight;
  final bool showAmount;

  /// 무기한(null)도 칸을 그대로 보낸다 — 서버는 다섯 칸 모두를 요구한다.
  Map<String, dynamic> toJson() => {
    'link_days': linkDays,
    'show_menus': showMenus,
    'show_shop_info': showShopInfo,
    'show_weight': showWeight,
    'show_amount': showAmount,
  };
}

/// 미리보기(GET·PUT 응답 `{report, link, settings}`).
class VisitReportPreview {
  const VisitReportPreview({
    required this.media,
    required this.careNote,
    required this.link,
    required this.settings,
  });

  factory VisitReportPreview.fromJson(Map<String, dynamic> json) {
    final report = json['report'] as Map<String, dynamic>;
    return VisitReportPreview(
      media: [
        for (final e in report['media'] as List)
          ReportMedia.fromJson(e as Map<String, dynamic>),
      ],
      careNote: report['care_note'] as String?,
      link: ReportLink.fromJson(json['link'] as Map<String, dynamic>),
      settings: ReportSettings.fromJson(
        json['settings'] as Map<String, dynamic>,
      ),
    );
  }

  /// 후 → 전, 그 안에서 순서대로. 뺀 것도 `hidden: true`로 함께 온다.
  final List<ReportMedia> media;
  final String? careNote;
  final ReportLink link;

  /// 지금 매장 설정 — "함께 보이는 항목"과 기간 안내를 이것으로 그린다.
  final ReportSettings settings;
}
