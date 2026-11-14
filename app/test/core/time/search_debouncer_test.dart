import 'package:chagocnote/core/time/search_debouncer.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

TextEditingValue _typed(String text) => TextEditingValue(
  text: text,
  selection: TextSelection.collapsed(offset: text.length),
);

/// 마지막 글자가 아직 조합 중인 입력(한글 입력기가 주는 모양).
TextEditingValue _composing(String text) => TextEditingValue(
  text: text,
  selection: TextSelection.collapsed(offset: text.length),
  composing: TextRange(start: text.length - 1, end: text.length),
);

void main() {
  // testWidgets 는 가짜 시계로 돈다 — pump(시간)으로 타이머를 앞당긴다.
  testWidgets('조합이 끝난 뒤 0.3초 쉬면 한 번 보낸다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_composing('ㅋ'));
    debouncer.onChanged(_composing('코'));
    debouncer.onChanged(_composing('콩'));
    await tester.pump(const Duration(seconds: 1));
    expect(sent, isEmpty, reason: '조합 중에는 보내지 않는다');

    debouncer.onChanged(_typed('콩'));
    await tester.pump(const Duration(milliseconds: 299));
    expect(sent, isEmpty);
    await tester.pump(const Duration(milliseconds: 1));
    expect(sent, ['콩']);
  });

  testWidgets('0.3초 안에 이어 치면 마지막 것 하나만 보낸다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_typed('5'));
    await tester.pump(const Duration(milliseconds: 200));
    debouncer.onChanged(_typed('56'));
    await tester.pump(const Duration(milliseconds: 200));
    debouncer.onChanged(_typed('567'));
    await tester.pump(const Duration(milliseconds: 300));

    expect(sent, ['567']);
  });

  testWidgets('다시 조합을 시작하면 기다리던 요청을 취소한다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_typed('콩'));
    await tester.pump(const Duration(milliseconds: 200));
    debouncer.onChanged(_composing('콩ㅇ'));
    await tester.pump(const Duration(seconds: 1));

    expect(sent, isEmpty);
  });

  testWidgets('앞뒤 공백을 없앤 검색어가 마지막으로 보낸 것과 같으면 보내지 않는다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);
    addTearDown(debouncer.dispose);

    debouncer.onChanged(_typed('콩'));
    await tester.pump(const Duration(milliseconds: 300));
    debouncer.onChanged(_typed('콩 '));
    await tester.pump(const Duration(milliseconds: 300));
    debouncer.onChanged(_typed(''));
    await tester.pump(const Duration(milliseconds: 300));

    expect(sent, ['콩', '']);
  });

  testWidgets('dispose 하면 기다리던 요청을 보내지 않는다', (tester) async {
    final sent = <String>[];
    final debouncer = SearchDebouncer(onSearch: sent.add);

    debouncer.onChanged(_typed('콩'));
    debouncer.dispose();
    await tester.pump(const Duration(seconds: 1));

    expect(sent, isEmpty);
  });
}
