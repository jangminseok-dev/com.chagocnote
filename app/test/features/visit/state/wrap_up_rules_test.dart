import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/api/wrap_up_models.dart';
import 'package:chagocnote/features/visit/state/wrap_up_rules.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

WrapUpCard _card(String kind, int id) =>
    WrapUpCard.tryParse(wrapUpCardJson(kind: kind, visit: visitJson(visitId: id, status: 'completed')))!;

void main() {
  test('고른 종류부터, 그다음은 서버의 차례(정리 → 결제 → 알림장)', () {
    final cards = [_card('unresolved', 1), _card('unpaid', 2), _card('unpaid', 3), _card('report_unsent', 4)];
    List<String> keys(List<WrapUpCard> c) => [for (final x in c) cardKey(x)];

    expect(keys(orderCards(cards, null)), ['unresolved:1', 'unpaid:2', 'unpaid:3', 'report_unsent:4']);
    expect(keys(orderCards(cards, WrapUpKind.unpaid)), ['unpaid:2', 'unpaid:3', 'unresolved:1', 'report_unsent:4']);
    expect(keys(orderCards(cards, WrapUpKind.reportUnsent)), ['report_unsent:4', 'unresolved:1', 'unpaid:2', 'unpaid:3']);
  });

  test('하루 머리의 남은 일 — 0 인 것은 빼고 차례대로', () {
    DayCounts counts({int unresolved = 0, int unpaid = 0, int report = 0}) => DayCounts(
      visitCount: 0, reserved: 0, inProgress: 0, completed: 0, canceled: 0, noShow: 0,
      unresolved: unresolved, unpaid: unpaid, reportUnsent: report,
    );
    expect(remainingWords(counts(unresolved: 1, unpaid: 2, report: 1)), [
      (WrapUpKind.unresolved, AppStrings.remainingUnresolved(1)),
      (WrapUpKind.unpaid, AppStrings.remainingUnpaid(2)),
      (WrapUpKind.reportUnsent, AppStrings.remainingReportUnsent(1)),
    ]);
    expect(remainingWords(counts(report: 3)), [(WrapUpKind.reportUnsent, AppStrings.remainingReportUnsent(3))]);
    expect(remainingWords(counts()), isEmpty);
    expect(remainingLine(counts(unpaid: 2, report: 1)), '결제 안 적음 2 · 알림장 안 보냄 1');
  });

  test('결제 장의 저장 — 기록이 없으면 총액·수단만, 있으면 다른 칸·사진 자리·버전 그대로', () {
    final blank = paymentInputOf(null, total: 30000, method: PaymentMethod.card).toJson();
    expect(blank['total_amount'], 30000);
    expect(blank['payment_method'], 'card');
    expect(blank.containsKey('version'), isFalse);
    expect(blank['items'], isEmpty);
    expect(blank['media'], isEmpty);

    final record = VisitRecord.fromJson(
      recordJson(
        careNote: '잘 참았어요',
        weightKg: 3.4,
        items: [
          {'menu_id': 4, 'name': '목욕', 'amount': 28000},
        ],
        media: [recordMediaJson(mediaId: 52, phase: 'after'), recordMediaJson(mediaId: 51)],
        version: 3,
      ),
    );
    final kept = paymentInputOf(record, total: 28000, method: PaymentMethod.cash).toJson();
    expect(kept['version'], 3);
    expect(kept['care_note'], '잘 참았어요');
    expect(kept['weight_kg'], 3.4);
    expect(kept['total_amount'], 28000);
    expect(kept['payment_method'], 'cash');
    expect(kept['items'], [
      {'menu_id': 4, 'amount': 28000},
    ]);
    expect(kept['media'], [
      {'media_id': 51, 'phase': 'before', 'sort_order': 0},
      {'media_id': 52, 'phase': 'after', 'sort_order': 0},
    ]);
  });
}
