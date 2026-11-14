/// 확인할 것(③-B) — 서버가 판정해 준 `{code, scope, detail}`.
///
/// 앱은 판정하지 않고 그리기만 한다. **모르는 code 와 모양이 깨진 항목은 버린다** — 서버가
/// 항목을 더해도 옛 앱이 죽지 않게(설계 4.3). 사유·메모가 로그에 찍히지 않도록 `toString`을
/// 오버라이드하지 않는다.
library;

/// 서버가 주는 순서 그대로다(주의 → 노쇼 → 첫 방문 → 동의 → 지병 → 오랜만).
enum CheckCode {
  caution('caution'),
  noShow('no_show'),
  firstVisit('first_visit'),
  consent('consent'),
  conditions('conditions'),
  longAbsence('long_absence');

  const CheckCode(this.wire);

  final String wire;
}

enum CheckScope { customer, pet }

enum ConsentReason { senior, conditions }

enum ConsentState { missing, expired }

class CheckCondition {
  const CheckCondition({required this.label, required this.note});

  final String label;
  final String? note;
}

class VisitCheck {
  const VisitCheck._({
    required this.code,
    required this.scope,
    this.reason,
    this.until,
    this.count,
    this.consentReasons = const [],
    this.consentState,
    this.receivedOn,
    this.conditions = const [],
    this.days,
    this.lastVisitOn,
  });

  final CheckCode code;
  final CheckScope scope;

  /// 주의 고객 — 사유와 기한(그날까지 보인다).
  final String? reason;
  final DateTime? until;

  /// 노쇼 — 방문 날 앞 1년의 횟수.
  final int? count;

  /// 미용 동의 — 왜 필요한지, 받은 적이 없는지 기한이 지났는지, 지난번 받은 날.
  final List<ConsentReason> consentReasons;
  final ConsentState? consentState;
  final DateTime? receivedOn;

  /// 지병 — 이름과 메모.
  final List<CheckCondition> conditions;

  /// 오랜만 — 지난 방문에서 며칠, 그날.
  final int? days;
  final DateTime? lastVisitOn;

  /// 한 항목을 읽는다. 모르는 code·scope, 빠진 칸, 다른 형이면 null.
  static VisitCheck? tryParse(Object? json) {
    if (json is! Map) return null;
    final code = _byName(CheckCode.values, (c) => c.wire, json['code']);
    final scope = _byName(CheckScope.values, (s) => s.name, json['scope']);
    final detail = json['detail'];
    if (code == null || scope == null || detail is! Map) return null;
    switch (code) {
      case CheckCode.caution:
        final reason = detail['reason'];
        final until = _day(detail['until']);
        if (reason is! String || until == null) return null;
        return VisitCheck._(
          code: code,
          scope: scope,
          reason: reason,
          until: until,
        );
      case CheckCode.noShow:
        final count = detail['count'];
        if (count is! int) return null;
        return VisitCheck._(code: code, scope: scope, count: count);
      case CheckCode.firstVisit:
        return VisitCheck._(code: code, scope: scope);
      case CheckCode.consent:
        final reasons = detail['reasons'];
        final state = _byName(
          ConsentState.values,
          (s) => s.name,
          detail['state'],
        );
        final received = detail['received_on'];
        final receivedOn = _day(received);
        if (reasons is! List || state == null) return null;
        if (received != null && receivedOn == null) return null;
        return VisitCheck._(
          code: code,
          scope: scope,
          consentReasons: [
            for (final r in reasons)
              ?_byName(ConsentReason.values, (v) => v.name, r),
          ],
          consentState: state,
          receivedOn: receivedOn,
        );
      case CheckCode.conditions:
        final items = detail['items'];
        if (items is! List) return null;
        final conditions = <CheckCondition>[];
        for (final item in items) {
          if (item is! Map) return null;
          final label = item['label'];
          final note = item['note'];
          if (label is! String || (note != null && note is! String)) {
            return null;
          }
          conditions.add(CheckCondition(label: label, note: note as String?));
        }
        return VisitCheck._(code: code, scope: scope, conditions: conditions);
      case CheckCode.longAbsence:
        final days = detail['days'];
        final last = _day(detail['last_visit_on']);
        if (days is! int || last == null) return null;
        return VisitCheck._(
          code: code,
          scope: scope,
          days: days,
          lastVisitOn: last,
        );
    }
  }
}

T? _byName<T>(List<T> values, String Function(T) name, Object? wire) {
  for (final v in values) {
    if (name(v) == wire) return v;
  }
  return null;
}

/// `2026-11-14` → 날짜(시각은 자정). 글자가 아니거나 날짜가 아니면 null.
DateTime? _day(Object? value) {
  if (value is! String) return null;
  final parsed = DateTime.tryParse(value);
  return parsed == null
      ? null
      : DateTime(parsed.year, parsed.month, parsed.day);
}

/// 항목 목록을 읽는다. 목록이 아니거나 없으면 빈 목록, 읽지 못한 항목은 뺀다.
List<VisitCheck> parseChecks(Object? list) => list is! List
    ? const []
    : [for (final item in list) ?VisitCheck.tryParse(item)];

class PetChecks {
  const PetChecks({required this.petId, required this.checks});

  final int petId;
  final List<VisitCheck> checks;
}

/// 예약 등록의 미리 보기 — 보호자 항목은 한 번, 아이 항목은 아이별로.
class VisitChecksPreview {
  const VisitChecksPreview({required this.customer, required this.pets});

  factory VisitChecksPreview.fromJson(Map<String, dynamic> json) {
    final pets = json['pets'];
    return VisitChecksPreview(
      customer: parseChecks(json['customer']),
      pets: [
        if (pets is List)
          for (final p in pets)
            if (p is Map && p['pet_id'] is int)
              PetChecks(
                petId: p['pet_id'] as int,
                checks: parseChecks(p['checks']),
              ),
      ],
    );
  }

  final List<VisitCheck> customer;
  final List<PetChecks> pets;

  bool get isEmpty => customer.isEmpty && pets.every((p) => p.checks.isEmpty);
}
