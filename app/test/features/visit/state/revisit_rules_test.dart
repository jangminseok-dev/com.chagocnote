import 'package:chagocnote/features/visit/state/revisit_rules.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('안내 글은 서버와 같은 셋 — 매장·아이·주를 채우고 모르는 자리는 그대로 둔다', () {
    expect(
      fillRevisitMessage('{아이} {아이} {주}주 · {매장} · {모르는칸}', shop: '히스', pet: '콩이', weeks: 6),
      '콩이 콩이 6주 · 히스 · {모르는칸}',
    );
  });

  test('빈 글·공백뿐·300자 넘는 글은 저장하지 않는다', () {
    expect(revisitMessageProblem(''), AppStrings.revisitMessageEmpty);
    expect(revisitMessageProblem('  \n '), AppStrings.revisitMessageEmpty);
    expect(revisitMessageProblem('가' * 301), AppStrings.revisitMessageTooLong);
    expect(revisitMessageProblem('가' * 300), isNull);
    expect(revisitMessageProblem('칩이 없는 글'), isNull);
  });

  test('줄 아래의 말 — 지금 값으로 무슨 일이 생기는지', () {
    expect(AppStrings.revisitDefaultWeeksNote(4), "한 번 온 아이: 4주 뒤로 잡고, 4주가 지나면 '지남'에 올라요");
    expect(AppStrings.revisitSoonCountNote(3), "지금 3마리가 '곧'에 있어요");
    expect(AppStrings.revisitSampleVisitsNote(6), '최근 6번의 방문 사이 간격의 가운데 값을 써요');
    expect(AppStrings.revisitMinGapNote(7), '7일 안에 다시 온 방문은 주기 계산에서 빼요');
    expect(AppStrings.revisitMinGapNote(0), '모든 방문을 셈에 넣어요');
  });
}
