import 'package:chagocnote/features/visit/state/visit_form_rules.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('메뉴가 없으면 매장 기본 소요다', () {
    expect(menuDuration(const [], 120), 120);
  });

  test('메뉴 기본 소요를 더하고, 기본 소요가 없는 메뉴는 매장 기본 소요로 센다', () {
    expect(menuDuration(const [60, 90], 120), 150);
    expect(menuDuration(const [60, null], 120), 180);
  });

  test('합이 600분을 넘으면 600분이다(넘기면 서버가 422)', () {
    expect(menuDuration(const [300, 300, 60], 120), 600);
  });

  test('한 칸에 10분씩(길게 누르면 30분) 늘리고 줄이되 10~600분을 벗어나지 않는다', () {
    expect(stepDuration(90, longer: true), 100);
    expect(stepDuration(90, longer: false), 80);
    expect(stepDuration(90, longer: true, long: true), 120);
    expect(stepDuration(90, longer: false, long: true), 60);
    expect(stepDuration(10, longer: false), 10);
    expect(stepDuration(590, longer: true, long: true), 600);
  });
}
