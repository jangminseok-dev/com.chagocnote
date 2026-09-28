import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../../../core/proxy/speech_recognizer.dart';
import '../../../design/widgets/dictation_text_editing_controller.dart';

/// 받아쓰기 세션 하나 — 한 메모 칸의 컨트롤러에 인식 결과를 커서 자리에 넣는다(④-3b 설계 3.2).
///
/// - `partial` 은 진행 중 구간(회색)을 갈아 끼우고, `final` 은 굳혀 커서를 그 뒤로 옮긴다. 다음
///   구간은 그 자리에서 열리고, 앞 구절과의 사이에 띄어쓰기를 하나 넣는다(앞 글자가 공백·줄바꿈이면 안
///   넣는다). 세션의 첫 구간은 사용자가 둔 커서 자리에 그대로 붙인다.
/// - 무음 10초는 여기서 잰다. 네이티브가 제 기준으로 먼저 `ended` 를 보내면(안드로이드 몇 초, iOS 약
///   1분) 타이머가 살아 있는 동안은 다시 시작해 이어 듣는다 — 두 플랫폼의 체감을 같게 한다.
/// - 손으로 고치거나 길이 상한에 닿으면 끝낸다. 어느 끝이든 회색 글은 마지막 결과로 굳혀 남긴다.
/// - 끝난 뒤 네이티브가 보내는 `final`·`ended` 는 무시한다(`stop` 이 이미 회색 글을 굳혔다).
/// - 한 번에 한 칸만 듣게 하는 것은 화면 몫이다(다른 세션을 시작하기 전에 앞 것을 [cancel]).
class Dictation extends ChangeNotifier {
  Dictation({
    required this.recognizer,
    required this.controller,
    required this.maxLength,
    this.silence = const Duration(seconds: 10),
  }) {
    _subscription = recognizer.events.listen(_onEvent);
    controller.addListener(_onControllerChanged);
  }

  final SpeechRecognizer recognizer;
  final DictationTextEditingController controller;
  final int maxLength;
  final Duration silence;

  late final StreamSubscription<SpeechEvent> _subscription;
  Timer? _silenceTimer;

  bool _listening = false;
  bool get listening => _listening;

  SpeechErrorCode? _lastError;

  /// 마지막 세션을 끝낸 오류 — 화면이 스낵바를 고른다. 읽어도 비우지 않고, [start] 가 비운다.
  SpeechErrorCode? get lastError => _lastError;

  /// 진행 중 구간의 시작과 지금 길이(앞 띄어쓰기 포함).
  int _start = 0;
  int _length = 0;

  /// 이 세션에서 굳힌 구절이 있다 — 다음 구간 앞에 띄어쓰기를 넣을지 본다.
  bool _afterPhrase = false;

  /// 우리가 컨트롤러를 바꾸는 중 — 이때의 변화는 손으로 고친 것이 아니다.
  bool _applying = false;
  String _lastText = '';

  Future<void> start() async {
    final selection = controller.selection;
    // 칸을 한 번도 누르지 않았으면 커서가 없다 — 끝에 붙인다.
    _start = selection.isValid ? selection.start : controller.text.length;
    _length = 0;
    _afterPhrase = false;
    _lastText = controller.text;
    _lastError = null;
    _listening = true;
    _restartSilence();
    notifyListeners();
    await recognizer.start();
  }

  /// 회색 구간을 마지막 결과로 굳히고 끝낸다.
  Future<void> stop() async {
    if (!_end()) return;
    await recognizer.stop();
  }

  /// 화면을 나가거나 앱이 뒤로 갈 때 — 회색 글은 굳혀 두고(잃지 않는다) 인식은 결과 없이 끝낸다.
  Future<void> cancel() async {
    _end();
    // 끝난 세션이어도 보낸다 — stop 뒤 늦은 final 이 다음 세션에 섞이지 않게, 콜백이 안 와도 오디오 세션이 풀리게.
    await recognizer.cancel();
  }

  @override
  void dispose() {
    _subscription.cancel();
    _silenceTimer?.cancel();
    controller.removeListener(_onControllerChanged);
    super.dispose();
  }

  void _onEvent(SpeechEvent event) {
    if (!_listening) return;
    switch (event) {
      case SpeechPartial(:final text):
        _restartSilence();
        _replace(text);
      case SpeechFinal(:final text):
        _restartSilence();
        _replace(text);
        _commit();
      case SpeechEnded():
        // 네이티브가 먼저 끝냈다. 무음 타이머가 아직 살아 있으니 이어 듣는다(넘었으면 이미 stop 했다).
        _commit();
        unawaited(recognizer.start());
      case SpeechError(:final code):
        _lastError = code;
        _end();
    }
  }

  /// 진행 중 구간을 [text] 로 갈아 끼운다. 상한을 넘으면 상한까지만 넣고 끝낸다.
  void _replace(String text) {
    final before = controller.text.substring(0, _start);
    final after = controller.text.substring(_start + _length);
    final spaced =
        _afterPhrase &&
        text.isNotEmpty &&
        before.isNotEmpty &&
        !before.endsWith(' ') &&
        !before.endsWith('\n');
    var insert = spaced ? ' $text' : text;
    final room = maxLength - before.length - after.length;
    final over = insert.length > room;
    if (over) insert = insert.substring(0, room);
    _length = insert.length;
    _apply(() {
      controller.value = TextEditingValue(
        text: '$before$insert$after',
        selection: TextSelection.collapsed(offset: _start + _length),
      );
      controller.pending = TextRange(start: _start, end: _start + _length);
    });
    if (over) unawaited(stop());
  }

  /// 진행 중 구간을 굳히고 다음 구간을 그 뒤에서 연다.
  void _commit() {
    if (_length > 0) _afterPhrase = true;
    _start += _length;
    _length = 0;
    _apply(() => controller.pending = null);
  }

  void _apply(VoidCallback change) {
    _applying = true;
    change();
    _applying = false;
    _lastText = controller.text;
  }

  /// 세션을 끝낸다. 이미 끝났으면 false.
  bool _end() {
    if (!_listening) return false;
    _commit();
    _silenceTimer?.cancel();
    _listening = false;
    notifyListeners();
    return true;
  }

  void _restartSilence() {
    _silenceTimer?.cancel();
    _silenceTimer = Timer(silence, () => unawaited(stop()));
  }

  void _onControllerChanged() {
    // 커서만 옮긴 것은 고침이 아니다 — 글이 바뀌었을 때만 끝낸다.
    if (_applying || !_listening || controller.text == _lastText) return;
    unawaited(stop());
  }
}
