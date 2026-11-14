// 확인할 것의 문구와 묶기(설계 4.3) — 화면 없이 검증한다.
import 'package:chagocnote/features/visit/api/check_models.dart';
import 'package:chagocnote/features/visit/state/check_rules.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

VisitCheck _c(String code, {String scope = 'customer', Map<String, dynamic>? d}) =>
    VisitCheck.tryParse(checkJson(code, scope: scope, detail: d ?? {}))!;

void main() {
  group('checkLine', () {
    test('주의 고객', () {
      expect(
        checkLine(_c('caution', d: {'reason': '노쇼 3번', 'until': '2027-11-14'})),
        '주의 고객이에요 · 노쇼 3번',
      );
    });

    test('노쇼', () {
      expect(checkLine(_c('no_show', d: {'count': 2})), '지난 1년 동안 노쇼 2번');
    });

    test('첫 방문', () {
      expect(checkLine(_c('first_visit', scope: 'pet')), '처음 오는 아이예요');
    });

    test('동의서 — 받은 적 없음은 사유를 붙인다', () {
      expect(
        checkLine(
          _c(
            'consent',
            scope: 'pet',
            d: {
              'reasons': ['senior', 'conditions'],
              'state': 'missing',
              'received_on': null,
            },
          ),
        ),
        '미용 동의서를 받아 주세요 (노령 · 지병)',
      );
      expect(
        checkLine(
          _c(
            'consent',
            scope: 'pet',
            d: {
              'reasons': ['conditions'],
              'state': 'missing',
              'received_on': null,
            },
          ),
        ),
        '미용 동의서를 받아 주세요 (지병)',
      );
    });

    test('동의서 — 사유를 하나도 모르면 괄호가 없다', () {
      expect(
        checkLine(
          _c(
            'consent',
            scope: 'pet',
            d: {
              'reasons': ['breed'],
              'state': 'missing',
              'received_on': null,
            },
          ),
        ),
        '미용 동의서를 받아 주세요',
      );
    });

    test('동의서 — 기한이 지났으면 지난번 날짜를 붙인다', () {
      expect(
        checkLine(
          _c(
            'consent',
            scope: 'pet',
            d: {
              'reasons': ['senior'],
              'state': 'expired',
              'received_on': '2025-11-01',
            },
          ),
        ),
        '미용 동의서를 다시 받아 주세요 · 지난번 2025년 11월 1일',
      );
    });

    test('지병은 이름을 쉼표로 잇는다', () {
      expect(
        checkLine(
          _c(
            'conditions',
            scope: 'pet',
            d: {
              'items': [
                {'label': '심장병', 'note': '약'},
                {'label': '슬개골', 'note': null},
              ],
            },
          ),
        ),
        '지병 · 심장병, 슬개골',
      );
    });

    test('오랜만', () {
      expect(
        checkLine(
          _c(
            'long_absence',
            scope: 'pet',
            d: {'days': 200, 'last_visit_on': '2026-04-28'},
          ),
        ),
        '200일 만에 와요 · 지난 방문 4월 28일',
      );
    });
  });

  group('checkSections', () {
    VisitChecksPreview preview({
      List<Map<String, dynamic>> customer = const [],
      Map<int, List<Map<String, dynamic>>> pets = const {},
    }) => VisitChecksPreview.fromJson({
      'customer': customer,
      'pets': [
        for (final e in pets.entries) {'pet_id': e.key, 'checks': e.value},
      ],
    });

    test('아무것도 없으면 묶음이 없다', () {
      expect(checkSections(preview(pets: {11: []}), {11: '두부'}), isEmpty);
    });

    test('보호자 묶음이 먼저, 아이가 하나면 아이 이름을 붙이지 않는다', () {
      final sections = checkSections(
        preview(
          customer: [
            checkJson('no_show', detail: {'count': 2}),
          ],
          pets: {
            11: [checkJson('first_visit', scope: 'pet')],
          },
        ),
        {11: '두부'},
      );

      expect(sections.map((s) => (s.title, s.petId, s.checks.length)), [
        (null, null, 1),
        (null, 11, 1),
      ]);
    });

    test('아이가 둘이면 이름으로 나누고 빈 아이는 뺀다', () {
      final sections = checkSections(
        preview(
          pets: {
            11: [checkJson('first_visit', scope: 'pet')],
            12: [],
            13: [checkJson('first_visit', scope: 'pet')],
          },
        ),
        {11: '두부', 12: '콩이'},
      );

      // 이름을 모르는 아이(13)도 항목은 보인다 — 제목만 없다.
      expect(sections.map((s) => (s.title, s.petId)), [('두부', 11), (null, 13)]);
    });
  });

  test('detailSections 는 묶음 하나, 비면 없다', () {
    expect(detailSections(const [], petId: 11), isEmpty);
    final sections = detailSections([
      _c('no_show', d: {'count': 1}),
      _c('first_visit', scope: 'pet'),
    ], petId: 11);

    expect(sections.single.petId, 11);
    expect(sections.single.title, isNull);
    expect(sections.single.checks.length, 2);
  });

  test('petIdsKey 는 오름차순으로 잇는다', () {
    expect(petIdsKey({12, 3, 7}), '3,7,12');
    expect(petIdsKey(const <int>[]), '');
  });
}
