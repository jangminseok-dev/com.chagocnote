/// 기록 피드(설계 9절 `GET /visits/feed`)의 응답 모델. 메모가 로그에 찍히지 않도록 `toString`을
/// 오버라이드하지 않는다.
library;

import 'visit_marks.dart';
import 'visit_models.dart';

/// 피드 한 장 — 완료 방문 하나.
class FeedItem {
  const FeedItem({
    required this.visitId,
    required this.customer,
    required this.pet,
    required this.completedAt,
    required this.cover,
    required this.menus,
    required this.careNote,
    required this.mediaCount,
    required this.reportSent,
    this.marks = const [],
  });

  factory FeedItem.fromJson(Map<String, dynamic> json) => FeedItem(
    visitId: json['visit_id'] as int,
    customer: CustomerBrief.fromJson(json['customer'] as Map<String, dynamic>),
    pet: json['pet'] == null
        ? null
        : PetBrief.fromJson(json['pet'] as Map<String, dynamic>),
    completedAt: ShopTime.parse(json['completed_at'] as String),
    cover: json['cover'] as String?,
    menus: [for (final m in json['menus'] as List) m as String],
    careNote: json['care_note'] as String?,
    mediaCount: json['media_count'] as int,
    reportSent: json['report_sent'] as bool,
    marks: parseMarks(json['marks']),
  );

  final int visitId;
  final CustomerBrief customer;

  /// null 이면 보호자만의 방문.
  final PetBrief? pet;
  final ShopTime completedAt;

  /// 대표 사진 썸네일 서명 URL. 없으면 회색 자리.
  final String? cover;

  /// 기록의 실제 메뉴 이름, 없으면 예약 메뉴.
  final List<String> menus;

  /// 케어 메모 앞 80자.
  final String? careNote;
  final int mediaCount;

  /// 살아 있는 알림장 링크가 있다.
  final bool reportSent;

  /// 끝낸 일의 낱말(⑬).
  final List<VisitMark> marks;
}

/// 피드 한 쪽. [nextCursor]가 null 이면 마지막 쪽이다.
class VisitFeed {
  const VisitFeed({required this.items, required this.nextCursor});

  factory VisitFeed.fromJson(Map<String, dynamic> json) => VisitFeed(
    items: [
      for (final e in json['items'] as List)
        FeedItem.fromJson(e as Map<String, dynamic>),
    ],
    nextCursor: json['next_cursor'] as String?,
  );

  final List<FeedItem> items;
  final String? nextCursor;
}
