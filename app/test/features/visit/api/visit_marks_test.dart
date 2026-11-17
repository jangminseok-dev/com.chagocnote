import 'package:chagocnote/features/visit/api/visit_marks.dart';
import 'package:chagocnote/features/visit/screens/visit_labels.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('아는 코드만 정해 둔 차례로 읽고 모르는 코드는 버린다', () {
    expect(parseMarks(['report_sent', 'paid', 'consent_sent']), [
      VisitMark.paid,
      VisitMark.reportSent,
    ]);
    expect(parseMarks(null), isEmpty);
    expect(parseMarks('paid'), isEmpty);
    expect(parseMarks(['deposit_received', 'pass_used', 'paid', 'paid']), [
      VisitMark.paid,
      VisitMark.passUsed,
      VisitMark.depositReceived,
    ]);
  });

  test('낱말과 차례는 설계 4.4 의 표 그대로다', () {
    expect([for (final m in VisitMark.values) markLabel(m)], [
      '결제 완료',
      '알림장 보냄',
      '정기권',
      '예약금 받음',
    ]);
  });

  test('한 줄의 낱말이 넷을 넘으면 뒤를 +N 으로 접는다', () {
    expect(foldWords(['a', 'b', 'c', 'd']), ['a', 'b', 'c', 'd']);
    expect(foldWords(['a', 'b', 'c', 'd', 'e', 'f']), ['a', 'b', 'c', 'd', '+2']);
    expect(foldWords(const []), isEmpty);
  });
}
