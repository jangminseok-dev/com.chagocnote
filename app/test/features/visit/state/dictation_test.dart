import 'package:chagocnote/core/proxy/speech_recognizer.dart';
import 'package:chagocnote/design/widgets/dictation_text_editing_controller.dart';
import 'package:chagocnote/features/visit/state/dictation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/upload_fakes.dart';

/// 받아쓰기 세션(④-3b 설계 3.2). 시간은 testWidgets 의 가짜 시계로 건너뛴다 —
/// `tester.pump(시간)` 이 무음 타이머를 돌리고, 인식 이벤트(마이크로태스크)를 흘려보낸다.
void main() {
  late FakeSpeechRecognizer recognizer;
  late DictationTextEditingController controller;
  late Dictation dictation;

  /// [text] 에 커서를 [cursor] 자리에 두고 세션을 만든다.
  void setUp(String text, {int? cursor, int maxLength = 1000}) {
    recognizer = FakeSpeechRecognizer();
    controller = DictationTextEditingController(text: text);
    controller.selection = TextSelection.collapsed(
      offset: cursor ?? text.length,
    );
    dictation = Dictation(
      recognizer: recognizer,
      controller: controller,
      maxLength: maxLength,
    );
    addTearDown(() {
      dictation.dispose();
      controller.dispose();
    });
  }

  testWidgets('partial 은 커서 자리의 진행 중 구간을 갈아 끼우고, final 은 굳혀 커서를 뒤로 옮긴다', (
    tester,
  ) async {
    setUp('앞뒤', cursor: 1);
    await dictation.start();
    expect(dictation.listening, isTrue);
    expect(recognizer.starts, ['ko-KR']);

    recognizer.emitPartial('안녕');
    await tester.pump();
    expect(controller.text, '앞안녕뒤');
    expect(controller.pending, const TextRange(start: 1, end: 3));

    recognizer.emitFinal('안녕하세요');
    await tester.pump();
    expect(controller.text, '앞안녕하세요뒤');
    expect(controller.pending, isNull);
    expect(controller.selection, const TextSelection.collapsed(offset: 6));
    expect(dictation.listening, isTrue);
    await dictation.stop();
  });

  testWidgets('두 구절을 이어 받으면 사이에 띄어쓰기를 하나 넣는다', (tester) async {
    setUp('');
    await dictation.start();
    recognizer.emitFinal('안녕');
    await tester.pump();
    recognizer.emitPartial('반가');
    await tester.pump();
    expect(controller.text, '안녕 반가');
    expect(controller.pending, const TextRange(start: 2, end: 5));
    recognizer.emitFinal('반가워');
    await tester.pump();
    expect(controller.text, '안녕 반가워');
    expect(controller.selection, const TextSelection.collapsed(offset: 6));

    // 앞 구절이 줄바꿈으로 끝났으면 띄어쓰기를 넣지 않는다.
    recognizer.emitFinal('끝\n');
    await tester.pump();
    recognizer.emitFinal('다음');
    await tester.pump();
    expect(controller.text, '안녕 반가워 끝\n다음');
    await dictation.stop();
  });

  testWidgets('무음 10초면 끝난다', (tester) async {
    setUp('');
    await dictation.start();
    await tester.pump(const Duration(seconds: 5));
    recognizer.emitPartial('안녕');
    await tester.pump();

    // 마지막 결과(5초) 뒤 9초 — 아직 듣는다.
    await tester.pump(const Duration(seconds: 9));
    expect(dictation.listening, isTrue);
    expect(recognizer.stops, 0);

    await tester.pump(const Duration(seconds: 1));
    expect(dictation.listening, isFalse);
    expect(recognizer.stops, 1);
    expect(controller.text, '안녕');
    expect(controller.pending, isNull);
  });

  testWidgets('네이티브가 먼저 끝내도 10초 안이면 이어 듣고, 넘었으면 끝난다', (tester) async {
    setUp('');
    await dictation.start();
    await tester.pump(const Duration(seconds: 3));
    recognizer.emitEnded();
    await tester.pump();
    expect(recognizer.starts, hasLength(2));
    expect(dictation.listening, isTrue);

    // 11초 — 타이머가 먼저 stop 했으니 뒤늦은 ended 로는 다시 시작하지 않는다.
    await tester.pump(const Duration(seconds: 8));
    recognizer.emitEnded();
    await tester.pump();
    expect(recognizer.starts, hasLength(2));
    expect(recognizer.stops, 1);
    expect(dictation.listening, isFalse);
  });

  testWidgets('손으로 고치면 끝난다', (tester) async {
    setUp('메모');
    await dictation.start();
    recognizer.emitPartial('안녕');
    await tester.pump();

    // 커서만 옮기는 것은 고침이 아니다.
    controller.selection = const TextSelection.collapsed(offset: 0);
    expect(dictation.listening, isTrue);

    controller.text = '메모 안녕!';
    expect(dictation.listening, isFalse);
    expect(recognizer.stops, 1);
    expect(controller.pending, isNull);
  });

  testWidgets('길이 상한을 넘는 결과는 잘라 넣고 끝난다', (tester) async {
    setUp('12345', maxLength: 8);
    await dictation.start();
    recognizer.emitPartial('가나');
    await tester.pump();
    expect(controller.text, '12345가나');
    expect(dictation.listening, isTrue);

    recognizer.emitPartial('가나다라');
    await tester.pump();
    expect(controller.text, '12345가나다');
    expect(controller.pending, isNull);
    expect(dictation.listening, isFalse);
    expect(recognizer.stops, 1);
  });

  testWidgets('cancel 은 회색 글을 굳혀 두고 끝낸다', (tester) async {
    setUp('');
    await dictation.start();
    recognizer.emitPartial('안녕');
    await tester.pump();

    await dictation.cancel();
    expect(controller.text, '안녕');
    expect(controller.pending, isNull);
    expect(dictation.listening, isFalse);
    expect(recognizer.cancels, 1);
    expect(recognizer.stops, 0);
  });

  testWidgets('오류는 lastError 에 남고 세션이 끝난다', (tester) async {
    setUp('');
    var notified = 0;
    dictation.addListener(() => notified++);

    await dictation.start();
    recognizer.emitPartial('안녕');
    await tester.pump();
    recognizer.emitError(SpeechErrorCode.denied);
    recognizer.emitEnded();
    await tester.pump();
    expect(dictation.lastError, SpeechErrorCode.denied);
    expect(dictation.listening, isFalse);
    expect(controller.text, '안녕');
    expect(controller.pending, isNull);
    // 오류 뒤 ended 로 다시 시작하지 않는다.
    expect(recognizer.starts, hasLength(1));
    expect(notified, greaterThanOrEqualTo(2));

    // 다시 시작하면 지난 오류는 지운다. noSpeech 도 세션을 끝낸다.
    await dictation.start();
    expect(dictation.lastError, isNull);
    recognizer.emitError(SpeechErrorCode.noSpeech);
    await tester.pump();
    expect(dictation.lastError, SpeechErrorCode.noSpeech);
    expect(dictation.listening, isFalse);
    expect(controller.text, '안녕');
  });
}
