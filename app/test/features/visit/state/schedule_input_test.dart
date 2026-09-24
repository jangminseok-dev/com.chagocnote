import 'package:chagocnote/features/visit/state/schedule_input.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final today = DateTime(2026, 9, 23);

  test('여는 시각은 닫는 시각보다 빨라야 한다', () {
    expect(opensBeforeCloses('10:00', '19:00'), isTrue);
    expect(opensBeforeCloses('19:00', '19:00'), isFalse);
    expect(opensBeforeCloses('20:00', '19:00'), isFalse);
  });

  test('분 ↔ HH:MM', () {
    expect(minutesOf('09:30'), 570);
    expect(hhmmOf(570), '09:30');
    expect(hhmmOf(0), '00:00');
  });

  test('임시 휴무 날짜는 점·하이픈·붙여쓰기를 받고, 오늘부터만', () {
    expect(parseClosedDate('2026.10.09', today), DateTime(2026, 10, 9));
    expect(parseClosedDate('2026-10-09', today), DateTime(2026, 10, 9));
    expect(parseClosedDate('20261009', today), DateTime(2026, 10, 9));
    expect(parseClosedDate('2026.09.23', today), DateTime(2026, 9, 23));
    expect(parseClosedDate('2026.09.22', today), isNull);
    expect(parseClosedDate('2026.02.30', today), isNull);
    expect(parseClosedDate('10.09', today), isNull);
  });
}
