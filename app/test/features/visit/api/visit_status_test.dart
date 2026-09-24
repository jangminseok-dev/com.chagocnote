import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/screens/visit_labels.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

void main() {
  test('서버 상태 문자열은 enum 으로 한 번만 바뀐다', () {
    expect(VisitStatus.fromCode('reserved'), VisitStatus.reserved);
    expect(VisitStatus.fromCode('in_progress'), VisitStatus.inProgress);
    expect(VisitStatus.fromCode('completed'), VisitStatus.completed);
    expect(VisitStatus.fromCode('canceled'), VisitStatus.canceled);
    expect(VisitStatus.fromCode('no_show'), VisitStatus.noShow);
    expect(
      Visit.fromJson(visitJson(status: 'no_show')).status,
      VisitStatus.noShow,
    );
  });

  test('모르는 상태는 unknown 이고 화면은 "알 수 없음"으로 보인다', () {
    expect(VisitStatus.fromCode('paused'), VisitStatus.unknown);
    expect(statusLabel(VisitStatus.unknown), AppStrings.statusUnknown);
  });

  test('취소·노쇼만 빈 시간이다', () {
    expect(VisitStatus.values.where((s) => !s.occupiesTime).toList(), [
      VisitStatus.canceled,
      VisitStatus.noShow,
    ]);
  });

  test('행동의 서버 값은 그대로다', () {
    expect(
      [for (final a in VisitAction.values) a.code],
      ['start', 'complete', 'cancel', 'no_show', 'revert'],
    );
  });
}
