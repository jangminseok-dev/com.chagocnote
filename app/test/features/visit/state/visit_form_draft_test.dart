import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/visit_form_draft.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/visit_fixtures.dart';

final _date = DateTime(2026, 10, 2);
final _settings = VisitSettings.fromJson(
  settingsJson(defaultDurationMinutes: 120),
);
final _menus = [for (final j in defaultMenusJson()) Menu.fromJson(j)];
Menu _menu(int id) => _menus.firstWhere((m) => m.menuId == id);
Pet _pet(int id) => Pet.fromJson(petJson(petId: id));

VisitFormDraft _draft({Set<int> petIds = const {}, bool prefilled = false}) =>
    VisitFormDraft(
      VisitFormInitial(date: _date, petIds: petIds, prefilled: prefilled),
    );

void main() {
  group('반려동물', () {
    test('보호자의 아이가 하나뿐이면 처음에 그 아이를 고르고 미리 채울 아이로 준다', () {
      final draft = _draft();
      expect(draft.initPets([_pet(11)]), 11);
      expect(draft.petIds, {11});
      expect(draft.initPets([_pet(11)]), isNull); // 처음 한 번만
    });

    test('미리 골라진 아이 가운데 이 보호자의 아이만 남긴다', () {
      final draft = _draft(petIds: {11, 99});
      expect(draft.initPets([_pet(11), _pet(12)]), isNull);
      expect(draft.petIds, {11});
    });

    test('여러 마리 폼에서는 고르고 풀 수 있고, 한 마리만 남을 때 그 아이를 돌려준다', () {
      final draft = _draft();
      expect(draft.togglePet(11, single: false), 11);
      expect(draft.togglePet(12, single: false), isNull);
      expect(draft.petIds, {11, 12});
      expect(draft.togglePet(11, single: false), 12);
    });

    test('한 마리 폼에서는 고른 아이로 바뀐다', () {
      final draft = _draft(petIds: {11});
      expect(draft.togglePet(12, single: true), 12);
      expect(draft.petIds, {12});
    });

    test('보호자만 고르면 아이가 비고, 아이를 고르면 보호자만이 풀린다', () {
      final draft = _draft(petIds: {11});
      draft.chooseOwnerOnly();
      expect(draft.ownerOnly, isTrue);
      expect(draft.petIds, isEmpty);
      expect(draft.petsChosen, isTrue);
      draft.togglePet(11, single: false);
      expect(draft.ownerOnly, isFalse);
    });
  });

  group('지난번처럼', () {
    test('늦게 온 옛 응답은 버린다 — 순서 번호가 최신일 때만 채운다', () {
      final draft = _draft();
      final first = draft.beginPrefill()!;
      final second = draft.beginPrefill()!;
      final defaults = VisitDefaults.fromJson(
        defaultsJson(durationMinutes: 90),
      );
      expect(draft.applyPrefill(first, defaults), isFalse);
      expect(draft.duration, isNull);
      expect(draft.applyPrefill(second, defaults), isTrue);
      expect(draft.duration, 90);
      expect(draft.menuIds, [1]);
      expect(draft.prefilledNote, isTrue);
    });

    test('메뉴나 소요를 손댔거나 미리 채워진 폼이면 시작하지 않는다', () {
      final touched = _draft()..toggleMenu(_menu(1), _menus, _settings);
      expect(touched.beginPrefill(), isNull);
      expect(_draft(prefilled: true).beginPrefill(), isNull);
    });

    test('응답을 기다리는 사이 손댔으면 채우지 않는다', () {
      final draft = _draft();
      final seq = draft.beginPrefill()!;
      draft.stepDuration(_settings, longer: true);
      expect(
        draft.applyPrefill(seq, VisitDefaults.fromJson(defaultsJson())),
        isFalse,
      );
      expect(draft.duration, 130);
    });
  });

  group('메뉴와 소요', () {
    test('메뉴를 고르면 소요는 메뉴 기본 소요의 합이 되고 안내는 사라진다', () {
      final draft = _draft()..prefilledNote = true;
      draft.toggleMenu(_menu(1), _menus, _settings); // 60
      draft.toggleMenu(_menu(3), _menus, _settings); // +90
      expect(draft.menuIds, [1, 3]);
      expect(draft.duration, 150);
      expect(draft.prefilledNote, isFalse);
      draft.toggleMenu(_menu(1), _menus, _settings);
      expect(draft.menuIds, [3]);
      expect(draft.duration, 90);
    });

    test('소요를 직접 바꾼 뒤에는 메뉴를 골라도 소요가 따라오지 않는다', () {
      final draft = _draft();
      draft.stepDuration(_settings, longer: false, long: true); // 120 - 30
      expect(draft.duration, 90);
      draft.toggleMenu(_menu(4), _menus, _settings);
      expect(draft.duration, 90);
    });

    test('메뉴만 있고 소요가 없는 초안은 메뉴 기본 소요의 합으로 시작한다', () {
      final draft = VisitFormDraft(
        VisitFormInitial(
          date: _date,
          menus: [MenuBrief.fromJson(menuBriefJson(menuId: 4, name: '전체 미용'))],
        ),
      );
      draft.ensureDuration(_menus, _settings);
      expect(draft.duration, 150);
      expect(draft.effectiveDuration(_settings), 150);
      expect(_draft().effectiveDuration(_settings), 120);
    });
  });

  test('값을 만들 때 보호자만이면 아이가 비고, 빈 메모는 null 이다', () {
    final draft = _draft(petIds: {11})..chooseOwnerOnly();
    final value = draft.value(_settings, '2026-10-02T14:00:00+09:00', '  ');
    expect(value.petIds, isEmpty);
    expect(value.memo, isNull);
    expect(value.durationMinutes, 120);
    expect(value.startsAt, '2026-10-02T14:00:00+09:00');
  });
}
