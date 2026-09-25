import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/record_rules.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

VisitDetail _detail({Map<String, dynamic>? record, bool ownerOnly = false}) =>
    VisitDetail.fromJson(
      visitDetailJson(
        visit: visitJson(
          status: 'in_progress',
          ownerOnly: ownerOnly,
          menus: [
            menuBriefJson(menuId: 1, name: '목욕'),
            menuBriefJson(menuId: 2, name: '위생'),
          ],
        ),
        record: record,
      ),
    );

final _menus = [
  Menu.fromJson(menuJson(menuId: 1, name: '목욕', price: 30000)),
  Menu.fromJson(menuJson(menuId: 2, name: '위생')),
];

FormMedia _m(int id, MediaPhase phase) => FormMedia(
  RecordMedia.fromJson(recordMediaJson(mediaId: id, phase: phase.code)),
  phase,
);

void main() {
  group('처음 값', () {
    test('기록이 없으면 현재 몸무게와 예약 메뉴·정가로 채운다(정가 없으면 비움)', () {
      final start = recordFormStart(_detail(), _menus);

      expect(start.weightKg, 4.2);
      expect(start.lines.map((l) => (l.menuId, l.amount)), [
        (1, 30000),
        (2, null),
      ]);
      expect(start.totalAmount, isNull);
      expect(start.version, isNull);
    });

    test('사진만 있는 기록(대기열이 만든 것)도 비었다고 보고 채우되, 사진과 버전은 가져온다', () {
      final start = recordFormStart(
        _detail(record: recordJson(media: [recordMediaJson()], version: 2)),
        _menus,
      );

      expect(start.weightKg, 4.2);
      expect(start.lines, hasLength(2));
      expect(start.media.single.mediaId, 51);
      expect(start.version, 2);
    });

    test('조금이라도 적은 기록은 적은 그대로 — 몸무게가 비었어도 채우지 않는다', () {
      final start = recordFormStart(
        _detail(record: recordJson(careNote: '메모만', version: 5)),
        _menus,
      );

      expect(start.weightKg, isNull);
      expect(start.lines, isEmpty);
      expect(start.careNote, '메모만');
      expect(start.version, 5);
    });

    test('보호자만의 방문은 몸무게가 없다', () {
      expect(recordFormStart(_detail(ownerOnly: true), _menus).weightKg, isNull);
    });
  });

  test('항목 합은 비운 금액을 0원으로 세고, 금액을 하나도 적지 않았으면 총액 칸을 비운다', () {
    const lines = [
      FormLine(menuId: 1, name: '목욕', amount: 30000),
      FormLine(menuId: 2, name: '위생'),
    ];
    expect(sumOfLines(lines), 30000);
    expect(sumText(lines), '30000');
    expect(sumText(const [FormLine(menuId: 2, name: '위생')]), '');
    expect(sumText(const []), '');
  });

  test('사진 자리는 놓인 순서대로 전·후 칸마다 0부터 센다', () {
    final placements = placementsOf([
      _m(51, MediaPhase.before),
      _m(52, MediaPhase.after),
      _m(53, MediaPhase.before),
    ]);

    expect(placements.map((p) => (p.mediaId, p.phase, p.sortOrder)), [
      (51, MediaPhase.before, 0),
      (52, MediaPhase.after, 0),
      (53, MediaPhase.before, 1),
    ]);
  });

  test('새 사진만 뒤에 더한다 — 폼에 있거나 사용자가 뺀 사진은 두고, 폼의 전/후는 그대로', () {
    final fresh = VisitRecord.fromJson(
      recordJson(
        media: [
          recordMediaJson(mediaId: 51, phase: 'before'),
          recordMediaJson(mediaId: 52),
          recordMediaJson(mediaId: 60, phase: 'after'),
        ],
      ),
    );

    final merged = withNewMedia([_m(51, MediaPhase.after)], {52}, fresh);

    expect(merged.map((m) => (m.mediaId, m.phase)), [
      (51, MediaPhase.after),
      (60, MediaPhase.after),
    ]);
    expect(withNewMedia([_m(51, MediaPhase.before)], {}, null), hasLength(1));
  });

  test('메모는 앞뒤 공백을 떼고, 비면 null(지운다)', () {
    expect(noteOrNull('  각질  '), '각질');
    expect(noteOrNull('   '), isNull);
  });
}
