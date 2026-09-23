import 'package:chagocnote/features/customer/state/customer_input.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('전화번호', () {
    test('숫자만 남긴다 — 하이픈·공백·전각 숫자는 버린다', () {
      expect(phoneDigits('010-1234 5678'), '01012345678');
      expect(phoneDigits('０１０'), '');
    });

    test('서버와 같은 형식만 받는다', () {
      for (final ok in [
        '01012345678',
        '0111234567',
        '0212345678',
        '021234567',
        '0311234567',
        '07012345678',
      ]) {
        expect(isValidPhone(ok), isTrue, reason: ok);
      }
      for (final bad in [
        '',
        '0101234',
        '01212345678',
        '0701234567',
        '0661234567',
        '821012345678',
      ]) {
        expect(isValidPhone(bad), isFalse, reason: bad);
      }
    });

    test('하이픈을 넣어 보인다 — 서울은 두 자리 국번', () {
      expect(formatPhone('01012345678'), '010-1234-5678');
      expect(formatPhone('0212345678'), '02-1234-5678');
      expect(formatPhone('021234567'), '02-123-4567');
      expect(formatPhone('0311234567'), '031-123-4567');
      expect(formatPhone('123'), '123');
    });

    test('가린 번호의 뒷자리를 줄여 보인다', () {
      expect(maskedTail('010-12··-5678'), '··5678');
    });
  });

  group('몸무게', () {
    test('0 초과, 세 자리 정수와 소수 한 자리까지', () {
      expect(parseWeight('3.2'), 3.2);
      expect(parseWeight(' 12 '), 12);
      expect(parseWeight('999.9'), 999.9);
      for (final bad in ['', '0', '0.0', '-1', '3.25', '1000', 'abc', '3.']) {
        expect(parseWeight(bad), isNull, reason: bad);
      }
    });

    test('정수면 소수점을 빼고 보인다', () {
      expect(formatWeight(3.2), '3.2kg');
      expect(formatWeight(4), '4kg');
      expect(weightText(3.2), '3.2');
    });
  });

  test('태어난 해는 올해부터 40년 전까지', () {
    final today = DateTime(2026, 9, 22);
    expect(isValidBirthYear(2026, today), isTrue);
    expect(isValidBirthYear(1986, today), isTrue);
    expect(isValidBirthYear(1985, today), isFalse);
    expect(isValidBirthYear(2027, today), isFalse);
    expect(earliestBirthDate(today), DateTime(1986, 1, 1));
  });

  test('빈 선택 입력은 null', () {
    expect(optionalText('  '), isNull);
    expect(optionalText(' 메모 '), '메모');
  });

  test('생일은 여러 모양으로 받고, 없는 날·미래·40년 전 해보다 이른 날은 거절한다', () {
    final today = DateTime(2026, 9, 22);
    expect(parseBirthDate('2021.03.04', today), DateTime(2021, 3, 4));
    expect(parseBirthDate('2021-03-04', today), DateTime(2021, 3, 4));
    expect(parseBirthDate('20210304', today), DateTime(2021, 3, 4));
    expect(parseBirthDate('2026.09.22', today), DateTime(2026, 9, 22));
    expect(parseBirthDate('1986.09.22', today), DateTime(1986, 9, 22));
    expect(parseBirthDate('1986.01.01', today), DateTime(1986, 1, 1));
    for (final bad in [
      '',
      '2021.02.30',
      '2026.09.23',
      '1985.12.31',
      '21.03.04',
      'abcd',
    ]) {
      expect(parseBirthDate(bad, today), isNull, reason: bad);
    }
  });
}
