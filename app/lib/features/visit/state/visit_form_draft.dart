import '../../customer/api/customer_models.dart';
import '../api/visit_models.dart';
import 'visit_form_rules.dart' as rules;

/// 예약 폼이 내보내는 값. [petIds]가 비었으면 보호자만의 방문이다.
class VisitFormValue {
  const VisitFormValue({
    required this.petIds,
    required this.date,
    required this.startsAt,
    required this.durationMinutes,
    required this.menuIds,
    required this.memo,
  });

  final List<int> petIds;
  final DateTime date;

  /// 서버가 준 시각 문자열(매장 시간대). 없으면 아직 시각을 고르지 않았다.
  final String? startsAt;
  final int durationMinutes;
  final List<int> menuIds;
  final String? memo;
}

/// 폼의 처음 값. [prefilled]면 반려동물을 골라도 "지난번처럼"으로 덮어쓰지
/// 않는다(다음 예약 초안·수정).
class VisitFormInitial {
  const VisitFormInitial({
    required this.date,
    this.petIds = const {},
    this.ownerOnly = false,
    this.at,
    this.durationMinutes,
    this.menus = const [],
    this.memo,
    this.prefilled = false,
  });

  final DateTime date;
  final Set<int> petIds;
  final bool ownerOnly;

  /// `HH:MM`.
  final String? at;
  final int? durationMinutes;
  final List<MenuBrief> menus;
  final String? memo;
  final bool prefilled;
}

/// 예약 폼의 상태와 규칙 — 위젯의 `State`가 쥐던 것을 뺀 순수 객체.
///
/// 반려동물 선택, "지난번처럼" 미리 채우기(늦게 온 옛 응답을 버리는 순서 번호), 메뉴 → 소요
/// 산출, 소요 단계 조정이 여기 있다. 위젯은 이 객체를 바꾸고 `setState`만 부른다. 그래서
/// 규칙은 위젯 없이 단위 테스트로 검증한다.
class VisitFormDraft {
  VisitFormDraft(this.initial)
    : petIds = {...initial.petIds},
      ownerOnly = initial.ownerOnly,
      date = initial.date,
      at = initial.at,
      duration = initial.durationMinutes,
      menuIds = [for (final m in initial.menus) m.menuId],
      knownMenus = [...initial.menus];

  final VisitFormInitial initial;

  Set<int> petIds;
  bool ownerOnly;
  DateTime date;

  /// `HH:MM`. null 이면 아직 시각을 고르지 않았다.
  String? at;

  /// null 이면 매장 기본 소요.
  int? duration;
  List<int> menuIds;

  /// 보관돼 메뉴표에 없지만 이 방문에 붙어 있는 메뉴(이름을 보이려고 둔다).
  List<MenuBrief> knownMenus;

  /// 사용자가 메뉴·소요를 직접 손댔는가 — 손댄 뒤에는 미리 채우기가 덮지 않는다.
  bool menusTouched = false;
  bool durationTouched = false;

  /// "지난번과 같게 채웠어요" 안내를 보일지.
  bool prefilledNote = false;

  bool _petsInitialized = false;
  int _defaultsSeq = 0;

  int effectiveDuration(VisitSettings settings) =>
      duration ?? settings.defaultDurationMinutes;

  bool get petsChosen => ownerOnly || petIds.isNotEmpty;

  /// 반려동물이 하나뿐인 보호자면 그 아이를 미리 고른다. 미리 골라진 아이는
  /// 이 보호자의 아이만 남긴다(카톡 초안이 다른 집 아이를 넘길 수 없게).
  /// 처음 한 번만 한다. 미리 고른 아이(있으면)를 돌려준다 — 부르는 쪽이 그 아이로 미리 채운다.
  int? initPets(List<Pet> living) {
    if (_petsInitialized) return null;
    _petsInitialized = true;
    petIds.removeWhere((id) => !living.any((p) => p.petId == id));
    if (petIds.isNotEmpty || ownerOnly || living.length != 1) return null;
    petIds = {living.single.petId};
    return living.single.petId;
  }

  /// 아이를 고르거나 푼다. [single]이면 한 마리만 고른다. 한 마리만 남으면
  /// (처음 골랐든, 하나를 풀어 하나가 남았든) 그 아이 ID 를 돌려준다 — 그 아이로 미리 채운다.
  int? togglePet(int petId, {required bool single}) {
    ownerOnly = false;
    if (single) {
      petIds = {petId};
    } else if (!petIds.remove(petId)) {
      petIds.add(petId);
    }
    return petIds.length == 1 ? petIds.single : null;
  }

  void chooseOwnerOnly() {
    ownerOnly = true;
    petIds = {};
  }

  /// "지난번처럼"을 시작한다. 손댔거나 미리 채워진 폼이면 null(시작하지 않는다).
  /// 돌려준 번호를 [applyPrefill]에 넘긴다 — 늦게 온 옛 응답은 버린다.
  int? beginPrefill() {
    if (initial.prefilled || menusTouched || durationTouched) return null;
    return ++_defaultsSeq;
  }

  /// [seq]가 아직 최신이고 그 사이 손대지 않았으면 채운다. 채웠으면 true.
  bool applyPrefill(int seq, VisitDefaults defaults) {
    if (seq != _defaultsSeq || menusTouched || durationTouched) return false;
    menuIds = [for (final m in defaults.menus) m.menuId];
    knownMenus = [...knownMenus, ...defaults.menus];
    duration = defaults.durationMinutes;
    prefilledNote = defaults.sourceVisitId != null;
    return true;
  }

  void toggleMenu(Menu menu, List<Menu> all, VisitSettings settings) {
    menusTouched = true;
    prefilledNote = false;
    if (!menuIds.remove(menu.menuId)) menuIds.add(menu.menuId);
    if (!durationTouched) duration = _durationOf(all, settings);
  }

  void stepDuration(
    VisitSettings settings, {
    required bool longer,
    bool long = false,
  }) {
    durationTouched = true;
    prefilledNote = false;
    duration = rules.stepDuration(
      effectiveDuration(settings),
      longer: longer,
      long: long,
    );
  }

  /// 메뉴만 있고 소요가 없는 초안(카톡)은 메뉴 기본 소요의 합으로 시작한다.
  void ensureDuration(List<Menu> menus, VisitSettings settings) {
    if (duration == null && menuIds.isNotEmpty && !durationTouched) {
      duration = _durationOf(menus, settings);
    }
  }

  int _durationOf(List<Menu> menus, VisitSettings settings) {
    final byId = {for (final m in menus) m.menuId: m};
    return rules.menuDuration([
      for (final id in menuIds)
        byId[id]?.defaultDurationMinutes ?? settings.defaultDurationMinutes,
    ], settings.defaultDurationMinutes);
  }

  VisitFormValue value(VisitSettings settings, String? startsAt, String memo) {
    final trimmed = memo.trim();
    return VisitFormValue(
      petIds: ownerOnly ? const [] : petIds.toList(),
      date: date,
      startsAt: startsAt,
      durationMinutes: effectiveDuration(settings),
      menuIds: [...menuIds],
      memo: trimmed.isEmpty ? null : trimmed,
    );
  }
}
