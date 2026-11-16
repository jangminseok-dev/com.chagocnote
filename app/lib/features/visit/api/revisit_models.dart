/// 다시 올 때가 된 아이(⑬ 설계 3.3)와 매장의 다시 올 때 설정(3.7)의 응답 모델. 안내 글이 로그에 찍히지 않도록
/// `toString` 을 오버라이드하지 않는다.
library;

import '../../../core/time/grooming_cycle.dart';
import '../../../core/time/shop_time.dart';

/// 목록의 묶음 — 지남·곧.
enum RevisitBucket {
  due('due'),
  soon('soon');

  const RevisitBucket(this.code);

  final String code;

  static RevisitBucket parse(String? code) =>
      values.firstWhere((b) => b.code == code, orElse: () => due);
}

/// 한 줄 — 아이 하나. 돈이 없다(직원도 본다).
class RevisitItem {
  const RevisitItem({
    required this.petId,
    required this.petName,
    required this.photoUrl,
    required this.lastVisitDate,
    required this.lastVisitId,
    required this.cycleWeeks,
    required this.cycleSource,
    required this.lastIntervalWeeks,
    required this.dueDate,
    required this.estimated,
    required this.nudgedOn,
    required this.message,
  });

  /// 모양이 깨진 줄은 null — 나머지 줄은 보인다.
  static RevisitItem? tryParse(Object? json) {
    try {
      final j = json! as Map<String, dynamic>;
      final pet = j['pet'] as Map<String, dynamic>;
      return RevisitItem(
        petId: pet['pet_id'] as int,
        petName: pet['name'] as String,
        photoUrl: pet['photo_url'] as String?,
        lastVisitDate: parseDay(j['last_visit_date'] as String),
        lastVisitId: j['last_visit_id'] as int,
        cycleWeeks: j['cycle_weeks'] as int,
        cycleSource: CycleSource.parse(j['cycle_source']),
        lastIntervalWeeks: j['last_interval_weeks'] as int?,
        dueDate: parseDay(j['due_date'] as String),
        estimated: j['estimated'] as bool,
        nudgedOn: j['nudged_on'] == null ? null : parseDay(j['nudged_on'] as String),
        message: j['message'] as String,
      );
    } catch (_) {
      return null;
    }
  }

  final int petId;
  final String petName;

  /// 아이의 프로필 사진 썸네일 서명 URL.
  final String? photoUrl;
  final DateTime lastVisitDate;

  /// 마지막 완료 방문 — [예약]이 이 방문의 다음 예약 초안을 쓴다.
  final int lastVisitId;

  /// 날짜에 쓰는 주(어림이면 매장의 기본 간격).
  final int cycleWeeks;
  final CycleSource cycleSource;
  final int? lastIntervalWeeks;
  final DateTime dueDate;
  final bool estimated;

  /// 안내한 날 — 마지막 완료 방문보다 뒤일 때만 온다.
  final DateTime? nudgedOn;

  /// 서버가 매장의 템플릿으로 만든 안내 글.
  final String message;
}

class RevisitPage {
  const RevisitPage({required this.items, required this.nextCursor});

  factory RevisitPage.fromJson(Map<String, dynamic> json) => RevisitPage(
    items: [
      for (final e in json['items'] as List) ?RevisitItem.tryParse(e),
    ],
    nextCursor: json['next_cursor'] as String?,
  );

  final List<RevisitItem> items;

  /// null 이면 마지막 쪽이다.
  final String? nextCursor;
}

class RevisitCounts {
  const RevisitCounts({required this.soon, required this.due});

  factory RevisitCounts.fromJson(Map<String, dynamic> json) =>
      RevisitCounts(soon: json['soon'] as int, due: json['due'] as int);

  final int soon;
  final int due;

  int get total => soon + due;
}

/// 매장의 다시 올 때 설정 여섯 칸(⑬ 설계 3.7). [revisitMessage] 가 null 이면 처음 글([defaultMessage])이다.
class RevisitSettings {
  const RevisitSettings({
    required this.defaultCycleWeeks,
    required this.revisitSoonDays,
    required this.revisitMessage,
    required this.countUnsentReports,
    required this.cycleSampleVisits,
    required this.cycleMinGapDays,
    required this.defaultMessage,
  });

  factory RevisitSettings.fromJson(Map<String, dynamic> json) => RevisitSettings(
    defaultCycleWeeks: json['default_cycle_weeks'] as int,
    revisitSoonDays: json['revisit_soon_days'] as int,
    revisitMessage: json['revisit_message'] as String?,
    countUnsentReports: json['count_unsent_reports'] as bool,
    cycleSampleVisits: json['cycle_sample_visits'] as int,
    cycleMinGapDays: json['cycle_min_gap_days'] as int,
    defaultMessage:
        (json['defaults'] as Map<String, dynamic>)['revisit_message'] as String,
  );

  final int defaultCycleWeeks;
  final int revisitSoonDays;
  final String? revisitMessage;
  final bool countUnsentReports;
  final int cycleSampleVisits;
  final int cycleMinGapDays;
  final String defaultMessage;

  /// 지금 쓰는 템플릿.
  String get message => revisitMessage ?? defaultMessage;
}
