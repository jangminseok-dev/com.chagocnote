import 'package:chagocnote/core/time/grooming_cycle.dart';
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';

void main() {
  test('반려동물 상세의 주기를 읽고, 없거나 깨졌으면 null 이다', () {
    final r = PetDetail.fromJson(
      petDetailJson(revisit: petRevisitJson(cycleSource: 'manual', nudgedOn: '2026-11-10')),
    ).revisit!;
    expect((r.cycleWeeks, r.cycleSource, r.estimated), (6, CycleSource.manual, false));
    expect(r.nudgedOn, DateTime(2026, 11, 10));
    expect(r.lastVisitDate, DateTime(2026, 10, 1));
    expect(PetDetail.fromJson(petDetailJson()).revisit, isNull);
    expect(PetDetail.fromJson(petDetailJson(revisit: {'cycle_weeks': 'x'})).revisit, isNull);
  });
}
