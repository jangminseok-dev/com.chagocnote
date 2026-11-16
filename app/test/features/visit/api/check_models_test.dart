// 확인할 것의 해석 — 모르는 code 와 모양이 깨진 항목은 버리고 나머지는 읽는다(설계 4.3).
import 'package:chagocnote/features/customer/api/consent_models.dart';
import 'package:chagocnote/features/visit/api/check_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

void main() {
  test('여섯 가지 항목을 칸까지 읽는다', () {
    final checks = parseChecks([
      checkJson('caution', detail: {'reason': '노쇼 3번', 'until': '2027-11-14'}),
      checkJson('no_show', detail: {'count': 2}),
      checkJson('first_visit', scope: 'pet'),
      checkJson(
        'consent',
        scope: 'pet',
        detail: {
          'reasons': ['senior', 'conditions'],
          'state': 'expired',
          'received_on': '2025-11-01',
        },
      ),
      checkJson(
        'conditions',
        scope: 'pet',
        detail: {
          'items': [
            {'label': '심장병', 'note': '약 복용'},
            {'label': '슬개골', 'note': null},
          ],
        },
      ),
      checkJson(
        'long_absence',
        scope: 'pet',
        detail: {'days': 200, 'last_visit_on': '2026-04-28'},
      ),
    ]);

    expect(checks.map((c) => c.code), CheckCode.values);
    expect(checks[0].scope, CheckScope.customer);
    expect(checks[0].reason, '노쇼 3번');
    expect(checks[0].until, DateTime(2027, 11, 14));
    expect(checks[1].count, 2);
    expect(checks[2].scope, CheckScope.pet);
    expect(checks[3].consentReasons, [
      ConsentReason.senior,
      ConsentReason.conditions,
    ]);
    expect(checks[3].consentState, ConsentState.expired);
    expect(checks[3].receivedOn, DateTime(2025, 11, 1));
    expect(checks[4].conditions.map((c) => (c.label, c.note)), [
      ('심장병', '약 복용'),
      ('슬개골', null),
    ]);
    expect(checks[5].days, 200);
    expect(checks[5].lastVisitOn, DateTime(2026, 4, 28));
  });

  test('모르는 code 는 버리고 아는 항목은 남긴다', () {
    final checks = parseChecks([
      checkJson('vaccination', scope: 'pet', detail: {'due': '2026-12-01'}),
      checkJson('first_visit', scope: 'pet'),
    ]);

    expect(checks.map((c) => c.code), [CheckCode.firstVisit]);
  });

  test('모양이 깨진 항목은 버린다 — 빠진 칸, 다른 형, 모르는 scope, 맵이 아닌 것', () {
    final checks = parseChecks([
      checkJson('caution', detail: {'until': '2027-11-14'}), // reason 없음
      checkJson('caution', detail: {'reason': 'x', 'until': '내년'}),
      checkJson('no_show', detail: {'count': '둘'}),
      checkJson('first_visit', scope: 'shop'),
      checkJson('consent', scope: 'pet', detail: {'reasons': 'senior'}),
      checkJson('consent', scope: 'pet', detail: {'reasons': [], 'state': '?'}),
      checkJson('conditions', scope: 'pet', detail: {'items': [3]}),
      checkJson('long_absence', scope: 'pet', detail: {'days': 200}),
      {'code': 'first_visit', 'scope': 'pet'}, // detail 없음
      '글자',
      null,
      checkJson('no_show', detail: {'count': 1}),
    ]);

    expect(checks.map((c) => (c.code, c.count)), [(CheckCode.noShow, 1)]);
  });

  test('동의 사유에 모르는 값이 섞이면 아는 것만 남긴다', () {
    final check = VisitCheck.tryParse(
      checkJson(
        'consent',
        scope: 'pet',
        detail: {
          'reasons': ['senior', 'breed'],
          'state': 'missing',
          'received_on': null,
        },
      ),
    )!;

    expect(check.consentReasons, [ConsentReason.senior]);
    expect(check.consentState, ConsentState.missing);
    expect(check.receivedOn, isNull);
  });

  test('목록이 아니거나 없으면 빈 목록이다', () {
    expect(parseChecks(null), isEmpty);
    expect(parseChecks('x'), isEmpty);
    expect(parseChecks({'code': 'first_visit'}), isEmpty);
  });

  test('checks 칸이 없는 옛 방문 상세는 빈 목록으로 읽는다', () {
    final json = visitDetailJson()..remove('checks');

    expect(VisitDetail.fromJson(json).checks, isEmpty);
  });

  test('방문 상세의 checks 를 읽는다', () {
    final detail = VisitDetail.fromJson(
      visitDetailJson(checks: [checkJson('first_visit', scope: 'pet')]),
    );

    expect(detail.checks.single.code, CheckCode.firstVisit);
  });

  test('하루 목록의 수 칸이 없으면 0 이다', () {
    final json = dayItemJson(visitJson())
      ..remove('customer_check_count')
      ..remove('pet_check_count');
    final item = DayVisitItem.fromJson(json);

    expect((item.customerCheckCount, item.petCheckCount), (0, 0));
  });

  test('미리 보기는 보호자 항목과 아이별 항목을 읽고, 깨진 아이 줄은 버린다', () {
    final preview = VisitChecksPreview.fromJson({
      'customer': [
        checkJson('no_show', detail: {'count': 2}),
      ],
      'pets': [
        {
          'pet_id': 11,
          'checks': [checkJson('first_visit', scope: 'pet')],
        },
        {'pet_id': '열둘', 'checks': []},
        {'pet_id': 12, 'checks': []},
      ],
    });

    expect(preview.customer.single.count, 2);
    expect(preview.pets.map((p) => (p.petId, p.checks.length)), [
      (11, 1),
      (12, 0),
    ]);
    expect(preview.isEmpty, isFalse);
    expect(
      VisitChecksPreview.fromJson({'customer': [], 'pets': []}).isEmpty,
      isTrue,
    );
  });

  consentTests();
}

// --- 전자 동의서(⑪) — 바뀐 부분만, 보낸 날 ---------------------------------------------------------------------

void consentTests() {
  test('바뀐 부분만 남은 동의를 읽는다 — 토막과 지난번 받은 날', () {
    final check = VisitCheck.tryParse(checkJson('consent', scope: 'pet', detail: {
      'reasons': ['senior', 'conditions'],
      'state': 'partial',
      'received_on': '2026-03-02',
      'parts': ['condition', 'senior', 'vaccine'],
    }))!;

    expect(check.consentState, ConsentState.partial);
    expect(check.consentParts, [ConsentPart.senior, ConsentPart.condition]);   // 문서의 순서, 모르는 토막은 버린다
    expect(check.receivedOn, DateTime(2026, 3, 2));
    expect(check.formSentOn, isNull);
  });

  test('동의서를 보낸 날이 있으면 읽고, 없거나 깨졌으면 없는 것으로 본다', () {
    Map<String, dynamic> detail(Object? sent) => {
      'reasons': ['senior'],
      'state': 'missing',
      'received_on': null,
      'form_sent_on': ?sent,
    };

    expect(VisitCheck.tryParse(checkJson('consent', scope: 'pet', detail: detail('2026-11-16')))!.formSentOn, DateTime(2026, 11, 16));
    expect(VisitCheck.tryParse(checkJson('consent', scope: 'pet', detail: detail(null)))!.formSentOn, isNull);
    expect(VisitCheck.tryParse(checkJson('consent', scope: 'pet', detail: detail(7)))!.formSentOn, isNull);
  });

  test('옛 서버의 응답(칸이 없다)도 그대로 읽는다', () {
    final check = VisitCheck.tryParse(checkJson('consent', scope: 'pet', detail: {
      'reasons': ['senior'], 'state': 'missing', 'received_on': null,
    }))!;

    expect(check.consentParts, isEmpty);
    expect(check.formSentOn, isNull);
  });
}
