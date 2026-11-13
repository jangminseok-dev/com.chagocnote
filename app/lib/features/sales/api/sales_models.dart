import '../../../core/time/shop_time.dart';

/// 매출을 보는 기간. 서버에는 이름 그대로 보낸다.
enum SalesSpan { day, week, month, year }

List<T> _list<T>(Object? value, T Function(Map<String, dynamic>) parse) => [
  if (value is List)
    for (final item in value)
      if (item is Map<String, dynamic>) parse(item),
];

DateTime? _day(Object? value) => value is String ? parseDay(value) : null;

/// 화면에 보일 아이 — 이름과 프로필 사진. 사진이 없으면 [photoUrl]이 null 이다.
class PetCard {
  const PetCard({required this.petId, required this.name, this.photoUrl});

  final int petId;
  final String name;
  final String? photoUrl;

  factory PetCard.fromJson(Map<String, dynamic> json) => PetCard(
    petId: json['pet_id'] as int,
    name: json['name'] as String,
    photoUrl: json['photo_url'] as String?,
  );
}

/// 견준 창(앞 기간이나 작년)과 그 창의 매출.
class CompareWindow {
  const CompareWindow({required this.start, required this.end, required this.revenue});

  final DateTime start;
  final DateTime end;
  final int revenue;

  factory CompareWindow.fromJson(Map<String, dynamic> json) => CompareWindow(
    start: parseDay(json['start'] as String),
    end: parseDay(json['end'] as String),
    revenue: json['revenue'] as int,
  );
}

/// 막대 한 칸 — 주·월은 하루(`2026-11-14`), 연은 한 달(`2026-11`).
class SalesBucket {
  const SalesBucket({
    required this.key,
    required this.revenue,
    required this.visitCount,
    required this.future,
    required this.pets,
  });

  final String key;
  final int revenue;
  final int visitCount;

  /// 아직 오지 않은 칸.
  final bool future;

  /// 그날의 아이들(다섯까지). 달 칸에는 없다.
  final List<PetCard> pets;

  factory SalesBucket.fromJson(Map<String, dynamic> json) => SalesBucket(
    key: json['key'] as String,
    revenue: json['revenue'] as int,
    visitCount: json['visit_count'] as int,
    future: json['future'] == true,
    pets: _list(json['pets'], PetCard.fromJson),
  );
}

class SalesPayment {
  const SalesPayment({required this.method, required this.amount});

  /// `card`·`cash`·`transfer`·`none`(고르지 않음). 모르는 값도 그대로 든다.
  final String method;
  final int amount;

  factory SalesPayment.fromJson(Map<String, dynamic> json) =>
      SalesPayment(method: json['method'] as String, amount: json['amount'] as int);
}

class SalesMenu {
  const SalesMenu({
    required this.menuId,
    required this.name,
    required this.amount,
    required this.count,
    required this.pet,
  });

  /// 조정 줄(총액과 항목 합의 차이)이면 null 이다. 그 줄의 금액은 음수일 수 있다.
  final int? menuId;
  final String name;
  final int amount;
  final int count;

  /// 그 메뉴를 가장 최근에 한 아이.
  final PetCard? pet;

  factory SalesMenu.fromJson(Map<String, dynamic> json) => SalesMenu(
    menuId: json['menu_id'] as int?,
    name: json['name'] as String,
    amount: json['amount'] as int,
    count: json['count'] as int,
    pet: json['pet'] is Map<String, dynamic>
        ? PetCard.fromJson(json['pet'] as Map<String, dynamic>)
        : null,
  );
}

class SalesRegular {
  const SalesRegular({required this.pet, required this.visitCount});

  final PetCard pet;
  final int visitCount;

  factory SalesRegular.fromJson(Map<String, dynamic> json) => SalesRegular(
    pet: PetCard.fromJson(json['pet'] as Map<String, dynamic>),
    visitCount: json['visit_count'] as int,
  );
}

class SalesReport {
  const SalesReport({required this.completed, required this.sent, required this.opened});

  final int completed;
  final int sent;
  final int opened;

  factory SalesReport.fromJson(Map<String, dynamic> json) => SalesReport(
    completed: json['completed'] as int,
    sent: json['sent'] as int,
    opened: json['opened'] as int,
  );
}

/// 매출 탭 한 화면. 금액은 원, 날짜는 매장 시간대의 날짜다(결정 기록 011).
class SalesSummary {
  const SalesSummary({
    required this.span,
    required this.start,
    required this.end,
    required this.elapsedEnd,
    required this.revenue,
    required this.visitCount,
    required this.pricedCount,
    required this.average,
    required this.previous,
    required this.yearAgo,
    required this.goalAmount,
    required this.petCount,
    required this.newPetCount,
    required this.returningPetCount,
    required this.faces,
    required this.newPets,
    required this.returningPets,
    required this.buckets,
    required this.payments,
    required this.menus,
    required this.regulars,
    required this.remaining,
    required this.expectedAmount,
    required this.noShow,
    required this.canceled,
    required this.weekdays,
    required this.report,
    required this.unrecordedCount,
    required this.duePetCount,
  });

  final SalesSpan span;
  final DateTime start;

  /// 끝날(포함).
  final DateTime end;

  /// 지나간 마지막 날. 아직 오지 않은 기간이면 null.
  final DateTime? elapsedEnd;
  final int revenue;
  final int visitCount;
  final int pricedCount;
  final int? average;

  /// 바로 앞 기간(진행 중이면 같은 길이만큼).
  final CompareWindow? previous;

  /// 작년 같은 때 — 매출이 있었을 때만.
  final CompareWindow? yearAgo;

  /// 월 목표. 이번 달의 월 보기에서 목표가 있을 때만.
  final int? goalAmount;
  final int petCount;
  final int newPetCount;
  final int returningPetCount;
  final List<PetCard> faces;
  final List<PetCard> newPets;
  final List<PetCard> returningPets;
  final List<SalesBucket> buckets;
  final List<SalesPayment> payments;
  final List<SalesMenu> menus;
  final List<SalesRegular> regulars;

  /// 남은 예약. 진행 중인 기간에만 있다.
  final int? remaining;

  /// 남은 예약의 정가 합. 정가가 없으면 null.
  final int? expectedAmount;
  final int noShow;
  final int canceled;

  /// 요일별 매출(월~일). 월·연 보기에만.
  final List<int>? weekdays;
  final SalesReport? report;
  final int unrecordedCount;
  final int duePetCount;

  /// [asked]는 요청한 기간이다 — 서버가 모르는 기간을 돌려주면 이것을 쓴다.
  factory SalesSummary.fromJson(Map<String, dynamic> json, SalesSpan asked) {
    final period = json['period'] as Map<String, dynamic>;
    final compare = json['compare'] as Map<String, dynamic>? ?? const {};
    final pets = json['pets'] as Map<String, dynamic>? ?? const {};
    final bookings = json['bookings'] as Map<String, dynamic>? ?? const {};
    final goal = json['goal'];
    final weekdays = json['weekdays'];
    CompareWindow? window(Object? value) =>
        value is Map<String, dynamic> ? CompareWindow.fromJson(value) : null;
    return SalesSummary(
      span: SalesSpan.values.asNameMap()[json['span']] ?? asked,
      start: parseDay(period['start'] as String),
      end: parseDay(period['end'] as String),
      elapsedEnd: _day(period['elapsed_end']),
      revenue: json['revenue'] as int,
      visitCount: json['visit_count'] as int,
      pricedCount: json['priced_count'] as int,
      average: json['average'] as int?,
      previous: window(compare['previous']),
      yearAgo: window(compare['year_ago']),
      goalAmount: goal is Map<String, dynamic> ? goal['monthly_amount'] as int? : null,
      petCount: pets['count'] as int? ?? 0,
      newPetCount: pets['new_count'] as int? ?? 0,
      returningPetCount: pets['returning_count'] as int? ?? 0,
      faces: _list(pets['faces'], PetCard.fromJson),
      newPets: _list(pets['new'], PetCard.fromJson),
      returningPets: _list(pets['returning'], PetCard.fromJson),
      buckets: _list(json['buckets'], SalesBucket.fromJson),
      payments: _list(json['payments'], SalesPayment.fromJson),
      menus: _list(json['menus'], SalesMenu.fromJson),
      regulars: _list(json['regulars'], SalesRegular.fromJson),
      remaining: bookings['remaining'] as int?,
      expectedAmount: bookings['expected_amount'] as int?,
      noShow: bookings['no_show'] as int? ?? 0,
      canceled: bookings['canceled'] as int? ?? 0,
      weekdays: weekdays is List ? [for (final v in weekdays) v as int] : null,
      report: json['report'] is Map<String, dynamic>
          ? SalesReport.fromJson(json['report'] as Map<String, dynamic>)
          : null,
      unrecordedCount: json['unrecorded_count'] as int? ?? 0,
      duePetCount: json['due_pet_count'] as int? ?? 0,
    );
  }
}
