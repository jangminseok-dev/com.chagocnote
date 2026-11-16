/// 예약·방문 API 의 응답·요청 모델.
///
/// `fromJson`은 서버의 스네이크케이스 키를 그대로 읽는다. 이름·번호·메모가
/// 로그에 찍히지 않도록 `toString`을 오버라이드하지 않는다.
library;

// 매장 시각·날짜 문자열 도우미는 core/time 에 있다. 이 모듈을 import 하던 곳이 그대로 쓰게 다시 내보낸다.
import '../../../core/time/grooming_cycle.dart';
import '../../../core/time/shop_time.dart';
import 'check_models.dart';
import 'record_models.dart';
import 'report_models.dart';
import 'visit_marks.dart';

export '../../../core/time/shop_time.dart';

/// 방문 상태. 서버 문자열은 `fromJson`에서 한 번만 enum 으로 바꾼다.
///
/// 모르는 값은 [unknown] — 서버가 앱보다 먼저 새 상태를 알게 됐을 때 화면은 상태
/// 이름을 "알 수 없음"으로 보이고 버튼을 내지 않는다. `switch`는 폴백 없이 완전
/// 열거한다 — 상태를 더하면 컴파일러가 빠진 곳을 알려 준다.
enum VisitStatus {
  reserved('reserved'),
  inProgress('in_progress'),
  completed('completed'),
  canceled('canceled'),
  noShow('no_show'),
  unknown('');

  const VisitStatus(this.code);

  /// 서버 값.
  final String code;

  static VisitStatus fromCode(String code) => values.firstWhere(
    (status) => status.code == code,
    orElse: () => VisitStatus.unknown,
  );

  /// 시간을 차지하는 상태(예약됨·미용 중·완료). 취소·노쇼는 빈 시간이다.
  bool get occupiesTime => switch (this) {
    reserved || inProgress || completed || unknown => true,
    canceled || noShow => false,
  };
}

/// 상태 전이 행동. 서버에는 [code]를 보낸다.
enum VisitAction {
  start('start'),
  complete('complete'),
  cancel('cancel'),
  noShow('no_show'),
  revert('revert');

  const VisitAction(this.code);

  final String code;
}

/// 막지 않는 경고. 서버 값 그대로다.
abstract final class VisitWarning {
  static const overlap = 'overlap';
  static const closedDay = 'closed_day';
  static const outsideHours = 'outside_hours';
}

class MenuBrief {
  const MenuBrief({required this.menuId, required this.name});

  factory MenuBrief.fromJson(Map<String, dynamic> json) =>
      MenuBrief(menuId: json['menu_id'] as int, name: json['name'] as String);

  final int menuId;
  final String name;
}

List<MenuBrief> _menus(Object? value) => (value as List)
    .map((e) => MenuBrief.fromJson(e as Map<String, dynamic>))
    .toList();

/// 방문의 보호자 요약. 익명화한 고객이면 이름·번호가 null 이다.
class CustomerBrief {
  const CustomerBrief({
    required this.customerId,
    required this.name,
    required this.phoneMasked,
  });

  factory CustomerBrief.fromJson(Map<String, dynamic> json) => CustomerBrief(
    customerId: json['customer_id'] as int,
    name: json['name'] as String?,
    phoneMasked: json['phone_masked'] as String?,
  );

  final int customerId;
  final String? name;
  final String? phoneMasked;
}

/// 방문의 반려동물 요약. 익명화한 고객의 아이면 이름이 null 이다.
class PetBrief {
  const PetBrief({
    required this.petId,
    required this.name,
    required this.species,
    required this.breed,
    required this.weightKg,
  });

  factory PetBrief.fromJson(Map<String, dynamic> json) => PetBrief(
    petId: json['pet_id'] as int,
    name: json['name'] as String?,
    species: json['species'] as String,
    breed: json['breed'] as String,
    weightKg: (json['weight_kg'] as num).toDouble(),
  );

  final int petId;
  final String? name;
  final String species;
  final String breed;
  final double weightKg;
}

/// 방문 하나(반려동물 한 마리, 또는 보호자만).
class Visit {
  const Visit({
    required this.visitId,
    required this.customer,
    required this.pet,
    required this.startsAt,
    required this.endsAt,
    required this.durationMinutes,
    required this.status,
    required this.cancelReason,
    required this.memo,
    required this.menus,
  });

  factory Visit.fromJson(Map<String, dynamic> json) => Visit(
    visitId: json['visit_id'] as int,
    customer: CustomerBrief.fromJson(json['customer'] as Map<String, dynamic>),
    pet: json['pet'] == null
        ? null
        : PetBrief.fromJson(json['pet'] as Map<String, dynamic>),
    startsAt: ShopTime.parse(json['starts_at'] as String),
    endsAt: ShopTime.parse(json['ends_at'] as String),
    durationMinutes: json['duration_minutes'] as int,
    status: VisitStatus.fromCode(json['status'] as String),
    cancelReason: json['cancel_reason'] as String?,
    memo: json['memo'] as String?,
    menus: _menus(json['menus']),
  );

  final int visitId;
  final CustomerBrief customer;

  /// null 이면 보호자만의 방문.
  final PetBrief? pet;
  final ShopTime startsAt;
  final ShopTime endsAt;
  final int durationMinutes;
  final VisitStatus status;

  /// 'customer_request' | 'shop_reason' — 취소일 때만.
  final String? cancelReason;
  final String? memo;
  final List<MenuBrief> menus;

  /// 시간을 차지하는 방문(예약됨·미용 중·완료). 취소·노쇼는 빈 시간이다.
  bool get occupiesTime => status.occupiesTime;
}

class DayCounts {
  const DayCounts({
    required this.visitCount,
    required this.reserved,
    required this.inProgress,
    required this.completed,
    required this.canceled,
    required this.noShow,
    required this.unresolved,
    this.unpaid = 0,
    this.reportUnsent = 0,
    this.checks = 0,
  });

  factory DayCounts.fromJson(Map<String, dynamic> json) => DayCounts(
    visitCount: json['visit_count'] as int,
    reserved: json['reserved'] as int,
    inProgress: json['in_progress'] as int,
    completed: json['completed'] as int,
    canceled: json['canceled'] as int,
    noShow: json['no_show'] as int,
    unresolved: json['unresolved'] as int,
    unpaid: json['unpaid'] as int? ?? 0,
    reportUnsent: json['report_unsent'] as int? ?? 0,
    checks: json['checks'] as int? ?? 0,
  );

  /// 마릿수 — 예약됨·미용 중·완료.
  final int visitCount;
  final int reserved;
  final int inProgress;
  final int completed;
  final int canceled;
  final int noShow;
  final int unresolved;

  /// 남은 일(⑬) — 결제 안 적음·알림장 안 보냄. 지난 날·오늘만 0 이 아니다(서버가 센다).
  final int unpaid;
  final int reportUnsent;

  /// 확인할 것이 있는 살아 있는 방문의 수 — 앞날을 고른 달력 카드의 `확인 N`.
  final int checks;
}

class DayVisitItem {
  const DayVisitItem({
    required this.visit,
    required this.groupKey,
    required this.overlapping,
    required this.unresolved,
    required this.hasRecord,
    required this.cover,
    required this.reportSent,
    this.customerCheckCount = 0,
    this.petCheckCount = 0,
    this.marks = const [],
  });

  factory DayVisitItem.fromJson(Map<String, dynamic> json) => DayVisitItem(
    visit: Visit.fromJson(json['visit'] as Map<String, dynamic>),
    groupKey: json['group_key'] as String,
    overlapping: json['overlapping'] as bool,
    unresolved: json['unresolved'] as bool,
    hasRecord: json['has_record'] as bool,
    cover: json['cover'] as String?,
    reportSent: json['report_sent'] as bool,
    customerCheckCount: json['customer_check_count'] as int? ?? 0,
    petCheckCount: json['pet_check_count'] as int? ?? 0,
    marks: parseMarks(json['marks']),
  );

  final Visit visit;

  /// 가족 묶음 키. 해석하지 않고 같은지만 본다(결정 기록 006).
  final String groupKey;
  final bool overlapping;
  final bool unresolved;
  final bool hasRecord;

  /// 대표 사진 썸네일 서명 URL. 없으면 회색 자리.
  final String? cover;

  /// 살아 있는 알림장 링크가 있다.
  final bool reportSent;

  /// 확인할 것의 수(③-B) — 보호자 항목과 아이 항목을 따로 준다. 가족 묶음에서 보호자 수는
  /// 구성원마다 같은 값이 오므로 한 번만 센다(`DayGroup.checkCount`). 지병은 세지 않는다.
  final int customerCheckCount;
  final int petCheckCount;

  /// 끝낸 일의 낱말(⑬) — 아는 코드만, 정해 둔 차례로.
  final List<VisitMark> marks;
}

/// 하루 목록 — 취소·노쇼까지 모두, 시작 순.
class DayVisits {
  const DayVisits({
    required this.date,
    required this.closedDay,
    required this.counts,
    required this.items,
  });

  factory DayVisits.fromJson(Map<String, dynamic> json) => DayVisits(
    date: parseDay(json['date'] as String),
    closedDay: json['closed_day'] as bool,
    counts: DayCounts.fromJson(json['counts'] as Map<String, dynamic>),
    items: (json['items'] as List)
        .map((e) => DayVisitItem.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final DateTime date;
  final bool closedDay;
  final DayCounts counts;
  final List<DayVisitItem> items;
}

class CalendarDay {
  const CalendarDay({
    required this.date,
    required this.visitCount,
    required this.completedCount,
    required this.openCount,
    required this.unresolvedCount,
    required this.closedDay,
    required this.cover,
    required this.covers,
    this.unpaidCount = 0,
    this.reportUnsentCount = 0,
  });

  factory CalendarDay.fromJson(Map<String, dynamic> json) => CalendarDay(
    date: parseDay(json['date'] as String),
    visitCount: json['visit_count'] as int,
    completedCount: json['completed_count'] as int,
    openCount: json['open_count'] as int,
    unresolvedCount: json['unresolved_count'] as int,
    closedDay: json['closed_day'] as bool,
    cover: json['cover'] as String?,
    covers: [for (final c in json['covers'] as List) c as String],
    unpaidCount: json['unpaid_count'] as int? ?? 0,
    reportUnsentCount: json['report_unsent_count'] as int? ?? 0,
  );

  final DateTime date;
  final int visitCount;
  final int completedCount;

  /// 예약됨·미용 중.
  final int openCount;
  final int unresolvedCount;
  final bool closedDay;

  /// 그날 완료 방문 가운데 시작 순 첫 대표 사진(썸네일 URL). 없으면 회색 자리.
  final String? cover;

  /// 미리보기 카드에 겹쳐 보일 사진 — 최대 4장.
  final List<String> covers;

  /// 남은 일(⑬) — 결제 안 적음·알림장 안 보냄. 지난 날·오늘만 0 이 아니다.
  final int unpaidCount;
  final int reportUnsentCount;

  /// 칸 오른쪽 위의 숫자 — 그날의 남은 일(정리 안 된 예약 + 결제 안 적음 + 알림장 안 보냄, 설계 3.8).
  int get remainingCount => unresolvedCount + unpaidCount + reportUnsentCount;
}

/// 월 요약. [days]는 그달의 모든 날이다.
class CalendarMonth {
  const CalendarMonth({
    required this.days,
    required this.unresolvedTotal,
    required this.oldestUnresolvedDate,
  });

  factory CalendarMonth.fromJson(Map<String, dynamic> json) => CalendarMonth(
    days: (json['days'] as List)
        .map((e) => CalendarDay.fromJson(e as Map<String, dynamic>))
        .toList(),
    unresolvedTotal: json['unresolved_total'] as int,
    oldestUnresolvedDate: json['oldest_unresolved_date'] == null
        ? null
        : parseDay(json['oldest_unresolved_date'] as String),
  );

  final List<CalendarDay> days;

  /// 매장 전체의 정리 안 된 예약 수(달과 상관없다).
  final int unresolvedTotal;
  final DateTime? oldestUnresolvedDate;

  CalendarDay? dayOf(DateTime date) {
    for (final d in days) {
      if (d.date.year == date.year &&
          d.date.month == date.month &&
          d.date.day == date.day) {
        return d;
      }
    }
    return null;
  }
}

class Slot {
  const Slot({required this.startsAt, required this.warnings});

  factory Slot.fromJson(Map<String, dynamic> json) => Slot(
    startsAt: ShopTime.parse(json['starts_at'] as String),
    warnings: (json['warnings'] as List).cast<String>(),
  );

  final ShopTime startsAt;
  final List<String> warnings;
}

/// 시간 칸과 그 경고. 경고 판단은 서버에만 있다(설계 6.3).
class VisitSlots {
  const VisitSlots({
    required this.durationMinutes,
    required this.closedDay,
    required this.slots,
  });

  factory VisitSlots.fromJson(Map<String, dynamic> json) => VisitSlots(
    durationMinutes: json['duration_minutes'] as int,
    closedDay: json['closed_day'] as bool,
    slots: (json['slots'] as List)
        .map((e) => Slot.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final int durationMinutes;
  final bool closedDay;
  final List<Slot> slots;
}

/// "지난번처럼" — 그 아이의 마지막 완료 방문의 메뉴와 소요.
class VisitDefaults {
  const VisitDefaults({
    required this.sourceVisitId,
    required this.durationMinutes,
    required this.menus,
  });

  factory VisitDefaults.fromJson(Map<String, dynamic> json) => VisitDefaults(
    sourceVisitId: json['source_visit_id'] as int?,
    durationMinutes: json['duration_minutes'] as int,
    menus: _menus(json['menus']),
  );

  /// null 이면 지난 방문이 없어 매장 기본값이다.
  final int? sourceVisitId;
  final int durationMinutes;
  final List<MenuBrief> menus;
}

class PreviousVisit {
  const PreviousVisit({required this.visitId, required this.startsAt});

  factory PreviousVisit.fromJson(Map<String, dynamic> json) => PreviousVisit(
    visitId: json['visit_id'] as int,
    startsAt: ShopTime.parse(json['starts_at'] as String),
  );

  final int visitId;
  final ShopTime startsAt;
}

/// 방문 상세 — 방문, 같은 묶음의 다른 방문(자기 제외), 지난 방문, 노쇼 횟수, 미용 기록, 알림장 링크.
class VisitDetail {
  const VisitDetail({
    required this.visit,
    required this.group,
    required this.previousVisit,
    required this.noShowCount,
    required this.record,
    required this.report,
    this.checks = const [],
    this.marks = const [],
    this.reportSkipped = false,
  });

  factory VisitDetail.fromJson(Map<String, dynamic> json) => VisitDetail(
    visit: Visit.fromJson(json['visit'] as Map<String, dynamic>),
    group: (json['group'] as List)
        .map((e) => Visit.fromJson(e as Map<String, dynamic>))
        .toList(),
    previousVisit: json['previous_visit'] == null
        ? null
        : PreviousVisit.fromJson(
            json['previous_visit'] as Map<String, dynamic>,
          ),
    noShowCount: json['no_show_count'] as int,
    record: json['record'] == null
        ? null
        : VisitRecord.fromJson(json['record'] as Map<String, dynamic>),
    report: ReportLink.fromJson(json['report'] as Map<String, dynamic>),
    checks: parseChecks(json['checks']),
    marks: parseMarks(json['marks']),
    reportSkipped: json['report_skipped'] as bool? ?? false,
  );

  final Visit visit;
  final List<Visit> group;
  final PreviousVisit? previousVisit;
  final int noShowCount;

  /// 없으면 null(아직 사진도 메모도 없다).
  final VisitRecord? record;

  /// 알림장 링크의 상태. 서버가 늘 준다 — 안 보냈으면 `live` 가 false 다.
  final ReportLink report;

  /// 확인할 것(③-B). 예약됨·미용 중에만 온다. 모르는 항목은 이미 버렸다.
  final List<VisitCheck> checks;

  /// 끝낸 일의 낱말(⑬).
  final List<VisitMark> marks;

  /// 하루 마무리에서 "알림장을 보내지 않음"으로 넘겼다 — 방문 상세에서 되돌린다.
  final bool reportSkipped;
}

/// 다음 예약 초안. 저장하지 않은 값이다.
class NextVisitDraft {
  const NextVisitDraft({
    required this.customerId,
    required this.petIds,
    required this.startsAt,
    required this.durationMinutes,
    required this.menus,
    required this.intervalWeeks,
    int? cycleWeeks,
    this.cycleSource = CycleSource.none,
  }) : cycleWeeks = cycleWeeks ?? intervalWeeks;

  factory NextVisitDraft.fromJson(Map<String, dynamic> json) => NextVisitDraft(
    customerId: json['customer_id'] as int,
    petIds: (json['pet_ids'] as List).cast<int>(),
    startsAt: ShopTime.parse(json['starts_at'] as String),
    durationMinutes: json['duration_minutes'] as int,
    menus: _menus(json['menus']),
    intervalWeeks: json['interval_weeks'] as int,
    cycleWeeks: json['cycle_weeks'] as int?,
    cycleSource: CycleSource.parse(json['cycle_source']),
  );

  final int customerId;
  final List<int> petIds;
  final ShopTime startsAt;
  final int durationMinutes;
  final List<MenuBrief> menus;
  final int intervalWeeks;

  /// 날짜에 쓴 주(⑬) — 직접·계산이면 그 값, 어림이면 매장의 기본 간격. 옛 응답이면 [intervalWeeks].
  final int cycleWeeks;
  final CycleSource cycleSource;

  /// 같은 벽시계 시각의 [day] 로 옮긴 초안(다시 올 때 목록의 [예약] — 지난 날을 옮긴다).
  NextVisitDraft movedTo(DateTime day) {
    String two(int n) => n.toString().padLeft(2, '0');
    final w = startsAt.wall;
    return NextVisitDraft(
      customerId: customerId,
      petIds: petIds,
      startsAt: ShopTime.parse(
        '${isoDay(day)}T${two(w.hour)}:${two(w.minute)}:${two(w.second)}',
      ),
      durationMinutes: durationMinutes,
      menus: menus,
      intervalWeeks: intervalWeeks,
      cycleWeeks: cycleWeeks,
      cycleSource: cycleSource,
    );
  }
}

/// 등록·수정·옮기기의 결과 — 방문들과 막지 않는 경고.
class SavedVisits {
  const SavedVisits({required this.visits, required this.warnings});

  factory SavedVisits.fromJson(Map<String, dynamic> json) => SavedVisits(
    visits: (json['visits'] as List)
        .map((e) => Visit.fromJson(e as Map<String, dynamic>))
        .toList(),
    warnings: (json['warnings'] as List).cast<String>(),
  );

  final List<Visit> visits;
  final List<String> warnings;
}

/// 매장 일정. 영업시간은 `HH:MM`(10분 단위), 쉬는 요일은 월=0 … 일=6.
class VisitSettings {
  const VisitSettings({
    required this.opensAt,
    required this.closesAt,
    required this.defaultDurationMinutes,
    required this.closedWeekdays,
  });

  factory VisitSettings.fromJson(Map<String, dynamic> json) => VisitSettings(
    opensAt: _hhmm(json['opens_at'] as String),
    closesAt: _hhmm(json['closes_at'] as String),
    defaultDurationMinutes: json['default_duration_minutes'] as int,
    closedWeekdays: (json['closed_weekdays'] as List).cast<int>(),
  );

  /// 서버는 `10:00:00`으로 준다 — 앞 다섯 글자만 쓴다.
  static String _hhmm(String value) => value.substring(0, 5);

  final String opensAt;
  final String closesAt;
  final int defaultDurationMinutes;
  final List<int> closedWeekdays;

  Map<String, dynamic> toJson() => {
    'opens_at': opensAt,
    'closes_at': closesAt,
    'default_duration_minutes': defaultDurationMinutes,
    'closed_weekdays': closedWeekdays,
  };
}

class ClosedDate {
  const ClosedDate({required this.date, required this.note});

  factory ClosedDate.fromJson(Map<String, dynamic> json) => ClosedDate(
    date: parseDay(json['date'] as String),
    note: json['note'] as String?,
  );

  final DateTime date;
  final String? note;
}

class Menu {
  const Menu({
    required this.menuId,
    required this.name,
    required this.defaultDurationMinutes,
    required this.sortOrder,
    required this.archived,
    required this.price,
  });

  factory Menu.fromJson(Map<String, dynamic> json) => Menu(
    menuId: json['menu_id'] as int,
    name: json['name'] as String,
    defaultDurationMinutes: json['default_duration_minutes'] as int?,
    sortOrder: json['sort_order'] as int,
    archived: json['archived'] as bool,
    price: json['price'] as int?,
  );

  final int menuId;
  final String name;

  /// null 이면 매장 기본 소요.
  final int? defaultDurationMinutes;
  final int sortOrder;
  final bool archived;

  /// 정가(원). null 이면 가격 미정 — 기록 화면이 금액을 미리 채우지 않는다.
  final int? price;
}

/// 예약 등록 요청. [startsAt]은 서버가 준 시각 문자열을 그대로 쓴다.
/// [walkIn]이면 [startsAt]을 보내지 않는다 — 지금 시작한 손님이다.
class VisitRequest {
  const VisitRequest({
    required this.customerId,
    required this.petIds,
    required this.startsAt,
    required this.durationMinutes,
    required this.menuIds,
    required this.memo,
    this.walkIn = false,
  });

  final int customerId;
  final List<int> petIds;
  final String? startsAt;
  final int durationMinutes;
  final List<int> menuIds;
  final String? memo;
  final bool walkIn;

  Map<String, dynamic> toJson() => {
    'customer_id': customerId,
    'pet_ids': petIds,
    if (!walkIn) 'starts_at': startsAt,
    'duration_minutes': durationMinutes,
    'menu_ids': menuIds,
    'memo': memo,
    'walk_in': walkIn,
  };
}

/// 방문 수정 요청(PUT — 모든 칸). [petId]가 null 이면 보호자만의 방문이다.
class VisitUpdate {
  const VisitUpdate({
    required this.startsAt,
    required this.petId,
    required this.durationMinutes,
    required this.menuIds,
    required this.memo,
  });

  final String startsAt;
  final int? petId;
  final int durationMinutes;
  final List<int> menuIds;
  final String? memo;

  Map<String, dynamic> toJson() => {
    'starts_at': startsAt,
    'pet_id': petId,
    'duration_minutes': durationMinutes,
    'menu_ids': menuIds,
    'memo': memo,
  };
}

/// 카톡 글을 해석한 예약 초안(설계 7절). 서버는 저장하지 않는다 — 사람이
/// 확인한 뒤 등록 API 로 저장한다. 못 찾은 칸은 null·빈 목록이다.
class VisitDraft {
  const VisitDraft({
    required this.date,
    required this.time,
    required this.candidates,
    required this.petIds,
    required this.menuIds,
    required this.guessed,
  });

  factory VisitDraft.fromJson(Map<String, dynamic> json) => VisitDraft(
    date: json['date'] == null ? null : parseDay(json['date'] as String),
    time: json['time'] as String?,
    candidates: (json['customer_candidates'] as List)
        .map((e) => DraftCandidate.fromJson(e as Map<String, dynamic>))
        .toList(),
    petIds: (json['pet_ids'] as List).cast<int>(),
    menuIds: (json['menu_ids'] as List).cast<int>(),
    guessed: DraftGuess.fromJson(json['guessed'] as Map<String, dynamic>),
  );

  final DateTime? date;

  /// `HH:MM`.
  final String? time;

  /// 글의 낱말로 찾은 보호자 후보(최대 5). 하나면 그 보호자로 짐작한 것이다.
  final List<DraftCandidate> candidates;

  /// 후보가 하나일 때 글에 이름이 나온 그 집 아이들.
  final List<int> petIds;
  final List<int> menuIds;
  final DraftGuess guessed;
}

class DraftCandidate {
  const DraftCandidate({
    required this.customerId,
    required this.name,
    required this.phoneMasked,
    required this.pets,
    required this.matchedPetIds,
  });

  factory DraftCandidate.fromJson(Map<String, dynamic> json) => DraftCandidate(
    customerId: json['customer_id'] as int,
    name: json['name'] as String,
    phoneMasked: json['phone_masked'] as String,
    pets: (json['pets'] as List)
        .map((e) => DraftPet.fromJson(e as Map<String, dynamic>))
        .toList(),
    matchedPetIds: (json['matched_pet_ids'] as List).cast<int>(),
  );

  final int customerId;
  final String name;
  final String phoneMasked;
  final List<DraftPet> pets;

  /// 글의 낱말과 이름이 맞은 아이.
  final List<int> matchedPetIds;
}

class DraftPet {
  const DraftPet({required this.petId, required this.name});

  factory DraftPet.fromJson(Map<String, dynamic> json) =>
      DraftPet(petId: json['pet_id'] as int, name: json['name'] as String);

  final int petId;
  final String name;
}

/// 해석기가 확신하지 못한 칸 — 화면에 "짐작" 표시를 단다.
class DraftGuess {
  const DraftGuess({
    required this.date,
    required this.time,
    required this.who,
    required this.menu,
  });

  factory DraftGuess.fromJson(Map<String, dynamic> json) => DraftGuess(
    date: json['date'] as bool,
    time: json['time'] as bool,
    who: json['who'] as bool,
    menu: json['menu'] as bool,
  );

  final bool date;
  final bool time;
  final bool who;
  final bool menu;
}


/// 한 예약에 보호자에게 보낼 글(⑪-B) — 토막들과, 이 조립이 새로 만든 동의서 링크.
class SendBundle {
  const SendBundle({required this.parts, this.createdFormId});

  factory SendBundle.fromJson(Map<String, dynamic> json) => SendBundle(
    parts: [
      if (json['parts'] case final List list)
        for (final raw in list) ?BundlePart.tryParse(raw),
    ],
    createdFormId: json['created_form_id'] is int ? json['created_form_id'] as int : null,
  );

  final List<BundlePart> parts;

  /// 묶음을 읽으면서 새로 만들어진 동의서 링크. 보내지 않고 닫으면 이것을 끊는다 — 보내지 않은 링크로
  /// "보냈어요"가 뜨지 않게. 살아 있던 링크를 썼거나 링크가 없으면 `null`.
  final int? createdFormId;
}

/// 보호자에게 보낼 글의 토막 하나(⑪-B). [kind] 는 `reservation`·`consent` — 서버가 종류를 더해도
/// 글은 그대로 싣는다. **[text] 에는 서류 주소(토큰)가 들 수 있다 — 로그·오류 문구에 남기지 않는다.**
class BundlePart {
  const BundlePart({required this.kind, required this.text});

  /// 글이 비었거나 모양이 깨진 토막은 `null` — 빈 글은 내보내지 않는다.
  static BundlePart? tryParse(Object? raw) {
    if (raw is! Map<String, dynamic>) return null;
    final kind = raw['kind'];
    final text = raw['text'];
    if (kind is! String || text is! String || text.trim().isEmpty) return null;
    return BundlePart(kind: kind, text: text);
  }

  final String kind;
  final String text;
}
