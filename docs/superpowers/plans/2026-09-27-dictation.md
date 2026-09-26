# 차곡노트 — ④-3b 말로 기록하기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기록 화면의 케어 메모·내부 메모에 마이크 버튼을 두고, 기기 안(온디바이스) 음성 인식으로 커서 자리에 실시간 받아쓴다. 토글 조작, 무음 10초면 끝, 지원하지 않는 기기·권한 거부·인식 실패는 문구로 안내하고 손 입력으로 잇는다. 서버는 바꾸지 않는다.

**Architecture:** 다섯 작업이다. ① 플러그 자리(`SpeechRecognizer` 채널·대역, 권한 문구) ② iOS 네이티브(`SFSpeechRecognizer` 온디바이스 강제) ③ Android 네이티브(`createOnDeviceSpeechRecognizer`) ④ 받아쓰기 세션 `Dictation`·회색 구간 컨트롤러·마이크 버튼 ⑤ 기록 화면·안내·시뮬레이터 흐름·문서. 모든 코드는 참조 작업 트리(`.superpowers/ref/wt-dictation`, 브랜치 `ref/dictation`, 커밋 f4e04e8 cf463f0 335a99f 2e92861 1148067)에서 먼저 돌렸다 — 커밋마다 `flutter analyze` 0·테스트 초록, 작업마다 변이로 판별력 확인, 네이티브 둘은 시뮬레이터·에뮬레이터에서 가용성 경로 확인(iOS 시뮬레이터는 ko-KR 온디바이스 가용성 true 이나 시작하면 미지원으로 끝남, 안드로이드 에뮬레이터는 한국어 모델이 없어 언어 미지원), 흐름 `dictation_flow_test.dart` 2/2(실제 채널 미지원 경로 + 대역 받아쓰기·저장).

**Tech Stack:** Flutter 3.44 · Riverpod 3 · 자체 네이티브 Swift(`Speech`·`AVFoundation`)·Kotlin(`android.speech`). **새 의존성 없음.**

**Spec:** `docs/superpowers/specs/2026-09-26-dictation-design.md` — 2절(흐름), 3절(플러그 자리·세션·버튼·네이티브), 4절(오류·경계), 5절(검증), 6절(문서). 실행자는 `app/CLAUDE.md`, `_docs/harness.md`, `_docs/decisions/007-record-media.md`(④-3a 절)를 함께 읽는다.

**계획의 위치:** ④ 설계 14절의 마지막 조각. ④-3a 영상(main 4d19b53) → **④-3b 말로 기록하기(이 문서)** → ④ 끝.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 앱 명령은 `app/`에서, 준비 스크립트는 `infra/`에서 돌린다.
- 작업 브랜치는 `feat/dictation`이다(`main` `4d19b53`에서 땄고, 설계 커밋 93655a2 와 이 계획서 커밋이 앞에 있다). `main`에서 직접 작업하지 않는다.
- **사용자가 작업 단위 커밋을 허용했다(2026-09-22 이후 계속).** 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.**
- 계획서의 코드 블록은 그대로 옮긴다. 새 파일은 전문이고, 수정 파일은 diff 다(hunk 헤더 줄 수가 안 맞으면 파일별 `git apply --recount`). diff 가 적용되지 않으면 멈추고 보고한다 — 손으로 "비슷하게" 고치지 않는다.
- **`dart format`을 돌리지 않는다**(새 파일도).
- **변이 검사는 편집으로 넣고 편집으로 되돌린다.** `git checkout -- <파일>`로 되돌리지 않는다. 골든이 실패하면 `test/**/failures/`에 png 가 남는다 — 커밋 전에 지운다.
- 골든은 이 계획이 만드는 것(`test/design/goldens/app_mic_button.png` 새로 하나, `test/features/visit/screens/goldens/record_screen.png` 갱신 하나)뿐이다. 그 밖의 골든이 실패하면 `--update-goldens`를 돌리지 말고 멈추고 보고한다.
- 비밀값·토큰·고객 개인정보를 로그에 남기지 않는다. 앱 코드에 `print`·`debugPrint`·dio `LogInterceptor`를 쓰지 않는다. 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.
- 네이티브 코드(Swift·Kotlin)는 단위 테스트가 없다. 작업 2·3 의 "실기 확인"(임시 진입점 `.superpowers/ref/dictation-plan-gen/probe_speech.dart` 복사)과 작업 5 의 흐름이 확인한다. 임시 진입점은 커밋하지 않는다.

구조 (`app/CLAUDE.md` — 작업 5 가 더하는 규칙 포함)
- 웹뷰 금지. 앱은 전부 네이티브다. 기능 폴더 import 는 `auth` 공용·`home` 껍데기·`visit → customer`만(`test/design/feature_imports_test.dart`).
- 플러그인은 `core/proxy/`의 프로바이더로만 — `speechRecognizerProvider`. **화면·모양 위젯은 플러그인·채널을 직접 import 하지 않고, `design/widgets` 는 `core` 를 import 하지 않는다**(`test/design/plugin_imports_test.dart`).
- 받아쓰기 규칙: 온디바이스 인식만(iOS `requiresOnDeviceRecognition`, Android `createOnDeviceSpeechRecognizer` API 31+), 한국어 `ko-KR` 고정, 토글, 무음 10초는 Dart 가 잰다(네이티브가 먼저 끝내면 10초 안이면 이어 듣는다), 한 번에 한 칸, 진행 중 구간은 회색, 손 입력·다른 칸·상한이면 끝, 화면을 나가면 `cancel`(회색 글은 굳혀 둔다).
- 앱 문구는 해요체(`test/design/copy_tone_test.dart`). 서버 문구는 바꾸지 않는다.

검증 명령 (`app/`에서)
- 정적 분석: `flutter analyze` → `No issues found!`(info 도 0)
- 테스트: `flutter test --timeout 60s` — 시작 748 → 끝 773. 골든 포함. `test/design/app_photo_pager_test.dart` 의 tap/drag 경고 2건은 main 부터 있던 잡음이다.
- iOS 빌드: `flutter build ios --simulator --debug`(작업 2). Android 빌드: `flutter build apk --debug`(작업 3).
- 시뮬레이터 흐름: 작업 5(`_docs/harness.md`의 "앱 흐름 확인" 행)
- 참조 브랜치와 대조(선택, 마지막에): `git diff ref/dictation -- app _docs` 가 비어 있어야 한다.

## 이 계획에서 새로 정한 것

설계와 다른 것과 새로 정한 것은 결정 기록 007 의 "④-3b 말로 기록하기에서 정한 것" 절(작업 5)에 적는다. 요약:
- 키보드 받아쓰기로만 두지 않고 앱 안 마이크 + 온디바이스 강제(키보드 🎤 는 서버 인식일 수 있다). 대가: iOS 온디바이스 한국어 모델 기기·안드로이드 API 31+ 와 한국어 모델 기기만(33+ 는 미리, 31~32 는 누른 뒤 앎).
- 토글·무음 10초·Dart 가 재는 무음(네이티브가 먼저 끝내면 10초 안이면 이어 듣는다). 자체 네이티브 채널 `chagocnote/speech`(`speech_to_text` 는 안드로이드 온디바이스 보장 불가).
- 듣는 중 표시는 붉은 점 대신 잉크색 점(팔레트 밖 색 금지). 띄어쓰기는 한 세션 안 구절 사이에만. 진행 중 구간 회색(`AppColors.secondary`).
- 시작 전 실패도 `error`+`ended` 이벤트(두 플랫폼). `denied` 는 오류 코드가 아니라 현재 권한 상태로. `stop` 뒤엔 `ended` 만. 끝난 세션의 `final`·`ended` 는 버린다.
- 칸을 바꿀 때·포커스가 떠날 때·화면이 사라질 때·앱이 뒤로 갈 때는 `cancel`(회색 글은 굳혀 둠, 늦은 이벤트가 다음 칸에 섞이지 않게).
- 시뮬레이터 흐름의 범위: Xcode 27 시뮬레이터는 가용성 true 이지만 시작하면 미지원으로 끝난다 — 실제 채널로는 권한·시작·미지원 안내까지, 받아쓰기는 대역으로. 권한은 simctl + TCC 데이터베이스로 미리 준다.
- OS 권한 창의 고정 문구("음성 데이터가 Apple 에 전송됩니다")는 온디바이스 강제여도 그대로다. 마이크 권한 문구는 영상·받아쓰기 둘 다 덮게 고쳤다. `AppSnackBar.show(action:)` 추가.
- 남는 것: 실기기 인식률(시뮬레이터·에뮬레이터 모두 실제 partial·final 을 받지 못함), iOS 1분 세션 이어 듣기, 인터럽션, 권한 창 순서, 안드로이드 모델 내려받기 안내, iOS 오디오 세션 메인 스레드 "Hang Risk" 경고.

## Review Focus

설계가 말하지만 화면만 봐서는 드러나지 않는 입력 다섯. 각 줄의 확인을 해당 작업에 넣었다.
1. **커서가 글 중간에 있을 때 받아쓰기** — 뒤 글을 덮어쓰거나 밀어내면 안 되고 구간 갈아 끼우기가 정확해야 한다 → 작업 4 `dictation_test.dart::partial 은 커서 자리의 진행 중 구간을 갈아 끼우고, final 은 굳혀 커서를 뒤로 옮긴다`(커서 중간).
2. **네이티브가 제 기준으로 먼저 끝냈을 때(안드로이드 몇 초·iOS 1분)** — 10초 규칙 안이면 사용자가 모르게 이어 들어야 한다 → 작업 4 `::네이티브가 먼저 끝내도 10초 안이면 이어 듣고, 넘었으면 끝난다`.
3. **듣는 중에 사용자가 손으로 타이핑** — 우리가 넣은 변경과 구분해 세션을 끝내야 하고, 회색 구간이 남으면 안 된다 → 작업 4 `::손으로 고치면 끝난다`.
4. **두 칸의 마이크를 번갈아 누름** — 한 번에 하나만 듣고 네이티브도 중복 세션을 견뎌야 한다 → 작업 5 `record_screen_test.dart::듣는 중에 내부 메모의 마이크를 누르면 앞 것이 끝나고 뒤 것이 시작한다`, 작업 2·3 의 "진행 중 또 start 가 오면 앞 것을 cancel".
5. **듣는 중에 화면을 나가거나 앱이 뒤로 감** — 마이크가 켜진 채 남거나 회색 글을 잃으면 안 된다 → 작업 5 `::화면을 나가면 cancel 한다`, 작업 4 `::cancel 은 회색 글을 굳혀 두고 끝낸다`.

---

### Task 1: 음성 인식 플러그 자리 — `SpeechRecognizer` 채널·대역, 음성 인식 권한 문구

**Files:**
- Create: `app/lib/core/proxy/speech_recognizer.dart`
- Modify: `app/ios/Runner/Info.plist`
- Create: `app/test/core/proxy/speech_recognizer_test.dart`
- Modify: `app/test/support/upload_fakes.dart`

**Interfaces:**
- Consumes: `core/proxy/video_transcoder.dart`·`test/core/proxy/video_transcoder_test.dart`(채널·테스트의 모양), `test/support/upload_fakes.dart`.
- Produces: `core/proxy/speech_recognizer.dart` — `SpeechAvailability{supported, reason: SpeechUnsupported?{device, locale}}`, `SpeechPermission{granted, denied}`, `sealed SpeechEvent`(`SpeechPartial(text)`·`SpeechFinal(text)`·`SpeechEnded`·`SpeechError(code)`), `SpeechErrorCode{denied, unsupported, noSpeech, failed}`, `abstract class SpeechRecognizer { availability(); requestPermission(); Stream<SpeechEvent> get events; start({locale = 'ko-KR'}); stop(); cancel(); openSettings(); }`, `ChannelSpeechRecognizer`(메서드 채널 `chagocnote/speech`: `availability` → `{supported, reason: 'device'|'locale'|null}`, `requestPermission` → `'granted'|'denied'`, `start{locale}`, `stop`, `cancel`, `openSettings`; 이벤트 채널 `chagocnote/speech/events`: `{type: partial|final|ended|error, text?, code?}`), `speechRecognizerProvider`. `test/support/upload_fakes.dart` 의 `FakeSpeechRecognizer`(`availabilityResult`·`permissionResult`·`starts`·`stops`·`cancels`·`settingsOpened`·`permissionRequests`, `emitPartial/emitFinal/emitEnded/emitError`). `ios/Runner/Info.plist` 에 `NSSpeechRecognitionUsageDescription`.

설계 3.1·3.6 절. 영상의 `ChannelVideoTranscoder` 와 같은 모양이다. `events` 는 네이티브 이벤트 채널을 **한 번만** 구독해 나눠 주고(늦게 구독한 쪽도 받는다 — 영상의 복귀 스트림 공유와 같은 이유), `package:async` 가 없어 `Stream.multi` 로 네이티브 스트림과 Dart 쪽 오류(`start` 의 `MissingPluginException` → `unsupported`)를 합친다. `PlatformException` 코드 매핑은 `start` 에만 있다(`availability` 는 미지원을 값으로 돌려주고, `requestPermission` 은 작업 5 의 화면이 `availability` 뒤에만 부른다). 모르는 코드는 `failed`. 테스트 4 는 이벤트 채널에 조용한 mock 을 걸어 둔다(이벤트 채널까지 없으면 listen 실패가 `reportError` 로 올라온다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/core/proxy/speech_recognizer_test.dart`:

```dart
// 음성 인식 채널(④-3b 설계 3.1)의 Dart 쪽 — 네이티브 채널을 흉내 내 가용성·권한·시작 인자·
// 이벤트·오류 코드가 규약대로 오가는지 보고, 테스트 대역 FakeSpeechRecognizer 자체도 확인한다.
import 'package:chagocnote/core/proxy/speech_recognizer.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/upload_fakes.dart';

const _method = MethodChannel(ChannelSpeechRecognizer.channelName);
const _events = EventChannel(ChannelSpeechRecognizer.eventsChannelName);

final _messenger =
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

void _mockMethods(Future<Object?> Function(MethodCall call) handler) {
  _messenger.setMockMethodCallHandler(_method, handler);
  addTearDown(() => _messenger.setMockMethodCallHandler(_method, null));
}

/// 네이티브 이벤트 쪽 흉내 — 받은 싱크를 쥐고 있다가 [send]로 흘린다.
class _Events extends MockStreamHandler {
  MockStreamHandlerEventSink? sink;
  var listened = 0;
  var cancelled = 0;

  void send(Map<String, Object?> event) => sink!.success(event);

  @override
  void onListen(Object? arguments, MockStreamHandlerEventSink events) {
    listened++;
    sink = events;
  }

  @override
  void onCancel(Object? arguments) => cancelled++;
}

_Events _mockEvents() {
  final handler = _Events();
  _messenger.setMockStreamHandler(_events, handler);
  addTearDown(() => _messenger.setMockStreamHandler(_events, null));
  return handler;
}

/// 이벤트 채널 메시지가 Dart 쪽 스트림까지 닿도록 한 박자 쉰다.
Future<void> _settle() => Future<void>.delayed(Duration.zero);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('availability 와 requestPermission 이 채널 결과를 그대로 돌려준다', () async {
    Object? availability = {'supported': false, 'reason': 'locale'};
    Object? permission = 'denied';
    final calls = <String>[];
    _mockMethods((call) async {
      calls.add(call.method);
      return switch (call.method) {
        'availability' => availability,
        'requestPermission' => permission,
        _ => null,
      };
    });
    final recognizer = ChannelSpeechRecognizer();

    final locale = await recognizer.availability();
    expect((locale.supported, locale.reason), (false, SpeechUnsupported.locale));
    expect(await recognizer.requestPermission(), SpeechPermission.denied);

    availability = {'supported': false, 'reason': 'device'};
    permission = 'granted';
    final device = await recognizer.availability();
    expect((device.supported, device.reason), (false, SpeechUnsupported.device));
    expect(await recognizer.requestPermission(), SpeechPermission.granted);

    availability = {'supported': true, 'reason': null};
    final ok = await recognizer.availability();
    expect((ok.supported, ok.reason), (true, null));

    expect(calls, [
      'availability',
      'requestPermission',
      'availability',
      'requestPermission',
      'availability',
    ]);
  });

  test('start 는 locale 을 보내고, 이벤트 채널의 partial·final·ended·error 가 SpeechEvent 로 온다', () async {
    final native = _mockEvents();
    final calls = <MethodCall>[];
    _mockMethods((call) async {
      calls.add(call);
      return null;
    });
    final recognizer = ChannelSpeechRecognizer();
    final seen = <SpeechEvent>[];
    final subscription = recognizer.events.listen(seen.add);
    addTearDown(subscription.cancel);

    await recognizer.start();
    await recognizer.start(locale: 'en-US');
    await _settle();
    native
      ..send({'type': 'partial', 'text': '발톱'})
      ..send({'type': 'final', 'text': '발톱 정리'})
      ..send({'type': 'error', 'code': 'noSpeech'})
      ..send({'type': 'ended'});
    await _settle();

    expect(calls.map((c) => c.method), ['start', 'start']);
    expect(calls.map((c) => c.arguments), [
      {'locale': 'ko-KR'},
      {'locale': 'en-US'},
    ]);
    expect(seen, hasLength(4));
    expect(seen[0], isA<SpeechPartial>().having((e) => e.text, 'text', '발톱'));
    expect(seen[1], isA<SpeechFinal>().having((e) => e.text, 'text', '발톱 정리'));
    expect(
      seen[2],
      isA<SpeechError>().having((e) => e.code, 'code', SpeechErrorCode.noSpeech),
    );
    expect(seen[3], isA<SpeechEnded>());
  });

  test('events 는 늦게 구독한 쪽도 받는다', () async {
    final native = _mockEvents();
    final recognizer = ChannelSpeechRecognizer();

    final first = <SpeechEvent>[];
    final a = recognizer.events.listen(first.add);
    await _settle();
    native.send({'type': 'partial', 'text': '목욕'});
    await _settle();
    await a.cancel();

    // 앞 구독이 끝난 뒤에 구독해도 네이티브를 다시 듣지 않고 같은 흐름을 받는다.
    final second = <SpeechEvent>[];
    final b = recognizer.events.listen(second.add);
    addTearDown(b.cancel);
    final third = <SpeechEvent>[];
    final c = recognizer.events.listen(third.add);
    addTearDown(c.cancel);
    await _settle();
    native.send({'type': 'final', 'text': '목욕 끝'});
    await _settle();

    expect(first.single, isA<SpeechPartial>());
    expect(second.single, isA<SpeechFinal>().having((e) => e.text, 'text', '목욕 끝'));
    expect(third.single, isA<SpeechFinal>());
    expect((native.listened, native.cancelled), (1, 0));
  });

  test('네이티브가 없으면 availability 는 device 미지원, start 는 unsupported 오류 이벤트, 나머지는 조용하다', () async {
    // 메서드 채널에 처리기가 없다 — MissingPluginException.
    _mockEvents();
    final recognizer = ChannelSpeechRecognizer();
    final seen = <SpeechEvent>[];
    final subscription = recognizer.events.listen(seen.add);
    addTearDown(subscription.cancel);

    final availability = await recognizer.availability();
    expect(
      (availability.supported, availability.reason),
      (false, SpeechUnsupported.device),
    );
    await recognizer.start();
    await recognizer.stop();
    await recognizer.cancel();
    await recognizer.openSettings();
    await _settle();

    expect(
      seen.single,
      isA<SpeechError>().having((e) => e.code, 'code', SpeechErrorCode.unsupported),
    );
  });

  test('모르는 오류 코드는 failed 다', () async {
    final native = _mockEvents();
    var startCode = 'denied';
    _mockMethods((call) async => throw PlatformException(code: startCode));
    final recognizer = ChannelSpeechRecognizer();
    final seen = <SpeechEvent>[];
    final subscription = recognizer.events.listen(seen.add);
    addTearDown(subscription.cancel);
    await _settle();

    await recognizer.start();
    startCode = 'kAFAssistantErrorDomain';
    await recognizer.start();
    native
      ..send({'type': 'error', 'code': 'unsupported'})
      ..send({'type': 'error', 'code': 'ERROR_SERVER'});
    await _settle();

    expect(seen.map((e) => (e as SpeechError).code), [
      SpeechErrorCode.denied,
      SpeechErrorCode.failed,
      SpeechErrorCode.unsupported,
      SpeechErrorCode.failed,
    ]);
  });

  test('FakeSpeechRecognizer 가 호출을 세고 이벤트를 흘린다', () async {
    final fake = FakeSpeechRecognizer()
      ..availabilityResult = const SpeechAvailability(
        supported: false,
        reason: SpeechUnsupported.locale,
      )
      ..permissionResult = SpeechPermission.denied;
    final seen = <SpeechEvent>[];
    final subscription = fake.events.listen(seen.add);
    addTearDown(subscription.cancel);

    expect((await fake.availability()).reason, SpeechUnsupported.locale);
    expect(await fake.requestPermission(), SpeechPermission.denied);
    await fake.start();
    await fake.start(locale: 'en-US');
    await fake.stop();
    await fake.cancel();
    await fake.openSettings();
    fake
      ..emitPartial('귀')
      ..emitFinal('귀 청소')
      ..emitError(SpeechErrorCode.noSpeech)
      ..emitEnded();
    await _settle();

    expect(fake.starts, ['ko-KR', 'en-US']);
    expect(
      (fake.permissionRequests, fake.stops, fake.cancels, fake.settingsOpened),
      (1, 1, 1, 1),
    );
    expect(seen, hasLength(4));
    expect(seen[0], isA<SpeechPartial>().having((e) => e.text, 'text', '귀'));
    expect(seen[1], isA<SpeechFinal>().having((e) => e.text, 'text', '귀 청소'));
    expect(
      seen[2],
      isA<SpeechError>().having((e) => e.code, 'code', SpeechErrorCode.noSpeech),
    );
    expect(seen[3], isA<SpeechEnded>());
  });
}
```

`app/test/support/upload_fakes.dart`:

```diff
@@ -8,6 +8,7 @@ import 'package:chagocnote/core/proxy/media_picker.dart';
 import 'package:chagocnote/core/proxy/network_watcher.dart';
 import 'package:chagocnote/core/proxy/photo_album.dart';
 import 'package:chagocnote/core/proxy/photo_renditions.dart';
+import 'package:chagocnote/core/proxy/speech_recognizer.dart';
 import 'package:chagocnote/core/proxy/video_transcoder.dart';
 import 'package:chagocnote/features/visit/api/record_models.dart';
 import 'package:chagocnote/features/visit/state/upload_job.dart';
@@ -305,3 +306,52 @@ class FakeMediaFiles implements MediaFiles {
     return file.path;
   }
 }
+
+/// 음성 인식 대역 — 가용성·권한을 정해 두고, 호출을 세며, emit* 로 이벤트를 흘린다.
+class FakeSpeechRecognizer implements SpeechRecognizer {
+  SpeechAvailability availabilityResult = const SpeechAvailability(
+    supported: true,
+  );
+  SpeechPermission permissionResult = SpeechPermission.granted;
+
+  final _events = StreamController<SpeechEvent>.broadcast();
+
+  /// start 에 넘긴 locale 들.
+  final starts = <String>[];
+  var stops = 0;
+  var cancels = 0;
+  var settingsOpened = 0;
+  var permissionRequests = 0;
+
+  @override
+  Future<SpeechAvailability> availability() async => availabilityResult;
+
+  @override
+  Future<SpeechPermission> requestPermission() async {
+    permissionRequests++;
+    return permissionResult;
+  }
+
+  @override
+  Stream<SpeechEvent> get events => _events.stream;
+
+  @override
+  Future<void> start({String locale = 'ko-KR'}) async => starts.add(locale);
+
+  @override
+  Future<void> stop() async => stops++;
+
+  @override
+  Future<void> cancel() async => cancels++;
+
+  @override
+  Future<void> openSettings() async => settingsOpened++;
+
+  void emitPartial(String text) => _events.add(SpeechPartial(text));
+
+  void emitFinal(String text) => _events.add(SpeechFinal(text));
+
+  void emitEnded() => _events.add(const SpeechEnded());
+
+  void emitError(SpeechErrorCode code) => _events.add(SpeechError(code));
+}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/core/proxy/speech_recognizer_test.dart`
Expected: 컴파일 실패 — `speech_recognizer.dart`·`FakeSpeechRecognizer` 가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/core/proxy/speech_recognizer.dart`:

```dart
import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 음성 인식(④-3b 설계 3.1) — 받아쓰기 세션·화면이 네이티브 채널을 직접 부르지 않게 감싼 자리.
///
/// 인식은 외부 패키지 없이 네이티브가 기기 안에서만 한다(서버 인식 없음).
/// - iOS `ios/Runner/SpeechRecognizer.swift`: `SFSpeechRecognizer`(ko-KR,
///   `requiresOnDeviceRecognition`)와 `AVAudioEngine` 입력 탭. `AppDelegate` 가 채널을 등록한다.
/// - 안드로이드 `android/app/src/main/kotlin/com/chagocnote/chagocnote/SpeechRecognizer.kt`:
///   API 31+ `createOnDeviceSpeechRecognizer` 와 `RecognitionListener`. 30 이하는 기기 미지원.
///
/// 채널 규약:
/// - 메서드 채널 [ChannelSpeechRecognizer.channelName]
///   - `availability()` → `{supported: bool, reason: 'device'|'locale'|null}`.
///   - `requestPermission()` → `'granted'|'denied'` — 마이크와 음성 인식이 둘 다 허용일 때만 granted.
///   - `start({locale})` — 듣기 시작. 결과는 이벤트 채널로 온다.
///   - `stop()` — 마지막 결과를 `final` 로 확정하고 `ended`. `cancel()` — 결과 없이 끝.
///   - `openSettings()` — 이 앱의 설정 화면을 연다.
///   - 실패는 `PlatformException` 코드 `denied`·`unsupported`·`noSpeech`·`failed`.
/// - 이벤트 채널 [ChannelSpeechRecognizer.eventsChannelName] — `{type: 'partial'|'final'|'ended'|
///   'error', text?, code?}`. `code` 는 위 넷 중 하나이고, 모르는 코드는 `failed` 로 읽는다.
enum SpeechUnsupported { device, locale }

class SpeechAvailability {
  const SpeechAvailability({required this.supported, this.reason});

  final bool supported;

  /// [supported]가 거짓일 때 까닭 — 기기(온디바이스 인식 없음)인지 언어(ko-KR 없음)인지.
  final SpeechUnsupported? reason;
}

enum SpeechPermission { granted, denied }

sealed class SpeechEvent {
  const SpeechEvent();
}

/// 아직 굳지 않은 중간 결과 — 이번 구간 전체 글이다.
class SpeechPartial extends SpeechEvent {
  const SpeechPartial(this.text);

  final String text;
}

/// 굳은 결과 — 이번 구간의 마지막 글이다.
class SpeechFinal extends SpeechEvent {
  const SpeechFinal(this.text);

  final String text;
}

/// 네이티브가 듣기를 끝냈다(요청했든 제 기준이든).
class SpeechEnded extends SpeechEvent {
  const SpeechEnded();
}

class SpeechError extends SpeechEvent {
  const SpeechError(this.code);

  final SpeechErrorCode code;
}

enum SpeechErrorCode { denied, unsupported, noSpeech, failed }

abstract class SpeechRecognizer {
  Future<SpeechAvailability> availability();

  /// 마이크와 음성 인식 둘 다 허용이어야 [SpeechPermission.granted].
  Future<SpeechPermission> requestPermission();

  /// 인식 결과·끝·오류. 브로드캐스트라 여럿이 들어도 된다.
  Stream<SpeechEvent> get events;

  Future<void> start({String locale = 'ko-KR'});

  /// 마지막 결과를 확정하고 끝낸다.
  Future<void> stop();

  /// 결과 없이 끝낸다.
  Future<void> cancel();

  Future<void> openSettings();
}

class ChannelSpeechRecognizer implements SpeechRecognizer {
  ChannelSpeechRecognizer({MethodChannel? channel, EventChannel? events})
    : _channel = channel ?? const MethodChannel(channelName),
      _eventChannel = events ?? const EventChannel(eventsChannelName);

  static const channelName = 'chagocnote/speech';
  static const eventsChannelName = 'chagocnote/speech/events';

  final MethodChannel _channel;
  final EventChannel _eventChannel;

  /// 네이티브가 없을 때처럼 Dart 쪽에서 내는 이벤트.
  final _local = StreamController<SpeechEvent>.broadcast();

  // 이벤트 채널은 한 번만 구독하고 나눠 준다. 받아쓰기 세션마다 구독을 풀고 다시 걸면
  // 네이티브가 listen·cancel 을 거듭 받아 그 사이 이벤트를 놓치므로, 늦게 구독한 쪽도
  // 같은 흐름을 받게 한다(인터넷 복귀 신호의 공유와 같은 까닭).
  late final Stream<SpeechEvent> _native = _eventChannel
      .receiveBroadcastStream()
      .map(_toEvent)
      .asBroadcastStream();

  @override
  late final Stream<SpeechEvent> events = Stream<SpeechEvent>.multi((out) {
    final native = _native.listen(out.addSync, onError: out.addErrorSync);
    final local = _local.stream.listen(out.addSync);
    out.onCancel = () async {
      await native.cancel();
      await local.cancel();
    };
  }, isBroadcast: true);

  @override
  Future<SpeechAvailability> availability() async {
    try {
      final result = await _channel.invokeMapMethod<String, Object?>(
        'availability',
      );
      return SpeechAvailability(
        supported: result!['supported']! as bool,
        reason: switch (result['reason']) {
          'device' => SpeechUnsupported.device,
          'locale' => SpeechUnsupported.locale,
          _ => null,
        },
      );
    } on MissingPluginException {
      // 이 플랫폼에는 인식이 없다(테스트·웹).
      return const SpeechAvailability(
        supported: false,
        reason: SpeechUnsupported.device,
      );
    }
  }

  @override
  Future<SpeechPermission> requestPermission() async {
    final result = await _channel.invokeMethod<String>('requestPermission');
    return result == 'granted'
        ? SpeechPermission.granted
        : SpeechPermission.denied;
  }

  @override
  Future<void> start({String locale = 'ko-KR'}) async {
    try {
      await _channel.invokeMethod<void>('start', {'locale': locale});
    } on PlatformException catch (e) {
      _local.add(SpeechError(_code(e.code)));
    } on MissingPluginException {
      _local.add(const SpeechError(SpeechErrorCode.unsupported));
    }
  }

  @override
  Future<void> stop() => _quietly('stop');

  @override
  Future<void> cancel() => _quietly('cancel');

  @override
  Future<void> openSettings() => _quietly('openSettings');

  Future<void> _quietly(String method) async {
    try {
      await _channel.invokeMethod<void>(method);
    } on MissingPluginException {
      // 이 플랫폼에는 인식이 없다 — 멈출 것도, 열 설정도 없다.
    }
  }

  static SpeechEvent _toEvent(Object? raw) {
    final event = raw! as Map<Object?, Object?>;
    return switch (event['type']) {
      'partial' => SpeechPartial(event['text']! as String),
      'final' => SpeechFinal(event['text']! as String),
      'error' => SpeechError(_code(event['code'] as String?)),
      _ => const SpeechEnded(),
    };
  }

  static SpeechErrorCode _code(String? code) => switch (code) {
    'denied' => SpeechErrorCode.denied,
    'unsupported' => SpeechErrorCode.unsupported,
    'noSpeech' => SpeechErrorCode.noSpeech,
    _ => SpeechErrorCode.failed,
  };
}

final speechRecognizerProvider = Provider<SpeechRecognizer>(
  (ref) => ChannelSpeechRecognizer(),
);
```

`app/ios/Runner/Info.plist`:

```diff
@@ -52,6 +52,8 @@
 	<string>미용 기록의 원본 사진을 앨범에 저장해요.</string>
 	<key>NSPhotoLibraryUsageDescription</key>
 	<string>앨범의 사진을 골라 미용 기록에 붙여요.</string>
+	<key>NSSpeechRecognitionUsageDescription</key>
+	<string>말한 것을 기기 안에서 글로 바꿔 메모에 넣어요.</string>
 	<key>UIApplicationSceneManifest</key>
 	<dict>
 		<key>UIApplicationSupportsMultipleScenes</key>
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/core/proxy/speech_recognizer_test.dart` → 6 passed

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 754 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `availability` 의 `reason` 매핑을 늘 null 로 → `speech_recognizer_test.dart::availability 와 requestPermission 이 채널 결과를 그대로 돌려준다` 실패.
- 이벤트 `type: 'final'` 을 `SpeechPartial` 로 → `::start 는 locale 을 보내고, 이벤트 채널의 partial·final·ended·error 가 SpeechEvent 로 온다`·`::events 는 늦게 구독한 쪽도 받는다` 실패.
- 네이티브 스트림 공유(한 번 구독)를 없애 구독마다 새로 받게 → `::events 는 늦게 구독한 쪽도 받는다` 실패.
- 모르는 오류 코드를 `unsupported` 로 → `::모르는 오류 코드는 failed 다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 음성 인식 플러그 자리 — SpeechRecognizer 채널·대역, 음성 인식 권한 문구

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: iOS 음성 인식 — `SFSpeechRecognizer` 온디바이스 강제, 부분·확정 결과 이벤트, 권한 둘, 인터럽션은 세션 종료

**Files:**
- Create: `app/ios/Runner/SpeechRecognizer.swift`
- Modify: `app/ios/Runner/AppDelegate.swift`
- Modify: `app/ios/Runner.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: 작업 1 의 채널 규약(`chagocnote/speech`·`chagocnote/speech/events`, 오류 코드 `denied|unsupported|noSpeech|failed`, 가용성 `device|locale`), `ios/Runner/VideoTranscoder.swift`·`AppDelegate.swift`(등록 방식), `tool/add_ios_file.rb`.
- Produces: `ios/Runner/SpeechRecognizer.swift` 의 `SpeechRecognizerPlugin`(`AppDelegate` 가 등록). 시작 전 실패(권한·미지원)도 `FlutterError` 가 아니라 `error`+`ended` 이벤트로 알린다. `denied` 는 오류 코드가 아니라 현재 권한 상태로 판정한다(`kAFAssistantErrorDomain` 1101 은 `failed`).

설계 3.4 절. 단위 테스트가 없다 — 빌드와 시뮬레이터 실기 확인이 검증이다. `pbxproj` 는 `ruby tool/add_ios_file.rb ios/Runner/SpeechRecognizer.swift` 를 돌린 뒤 젬이 건드린 무관한 줄을 되돌려 아래 넉 줄 diff 와 같게 한다(UUID 가 아래와 같아야 `git diff ref/dictation` 이 빈다 — 다르면 손으로 아래 넉 줄을 그대로 쓴다). 참조 구현에서 확인한 것: **Xcode 27 시뮬레이터는 `ko-KR` 온디바이스 인식을 지원한다**(`availability supported=true`). 마이크 권한은 `xcrun simctl privacy … grant microphone` 으로 주지만 음성 인식 권한은 simctl 이 지원하지 않아 시스템 창이 뜬다(헤드리스에서 못 누른다). OS 권한 창의 고정 문구("음성 데이터가 Apple 에 전송됩니다")는 온디바이스 강제여도 그대로 보인다 — 결정 기록 007 "남는 것".

- [ ] **Step 1: 구현한다**

`app/ios/Runner/SpeechRecognizer.swift`:

```swift
import AVFoundation
import Flutter
import Speech
import UIKit

/// 음성 인식(④-3b 설계 3.4절) — Dart `core/proxy/speech_recognizer.dart` 의 채널 규약을 따른다.
///
/// 인식은 `SFSpeechRecognizer` 에 `requiresOnDeviceRecognition` 을 걸어 기기 안에서만 한다(서버로 소리를
/// 보내지 않는다). 소리는 `AVAudioEngine` 입력 노드 탭으로 받아 요청에 붙인다. 결과는 이벤트 채널로
/// `{type: partial|final|ended|error, text?, code?}` 를 보낸다. 외부 패키지 없이 Speech·AVFoundation 만 쓴다.
///
/// 한 번에 한 세션만 듣는다. 듣는 중에 또 `start` 가 오면 앞 것을 조용히 취소하고 새로 시작한다
/// (다른 칸의 마이크를 누른 경우 — Dart 가 앞 것을 끝내지만 순서가 엇갈려도 견딘다).
final class SpeechRecognizerPlugin: NSObject, FlutterPlugin, FlutterStreamHandler {
  static let channelName = "chagocnote/speech"
  static let eventsChannelName = "chagocnote/speech/events"

  /// 입력 탭 버퍼 크기(프레임).
  private static let bufferSize: AVAudioFrameCount = 1024

  private var eventSink: FlutterEventSink?

  /// 진행 중인 세션 — 없으면 셋 다 nil.
  private var engine: AVAudioEngine?
  private var request: SFSpeechAudioBufferRecognitionRequest?
  private var task: SFSpeechRecognitionTask?
  /// 인식기는 세션 동안 붙잡아 둔다 — 놓으면 작업이 함께 사라진다.
  private var recognizer: SFSpeechRecognizer?

  /// 세션 번호 — 끝나거나 취소된 세션의 늦은 콜백을 버리려고 세션마다 올린다.
  private var generation = 0
  /// `stop` 을 받았다 — 이제 오는 오류는 알리지 않고 `ended` 만 보낸다.
  private var stopping = false

  static func register(with registrar: FlutterPluginRegistrar) {
    let plugin = SpeechRecognizerPlugin()
    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: registrar.messenger())
    registrar.addMethodCallDelegate(plugin, channel: channel)
    let events = FlutterEventChannel(name: eventsChannelName, binaryMessenger: registrar.messenger())
    events.setStreamHandler(plugin)

    let center = NotificationCenter.default
    center.addObserver(plugin, selector: #selector(onInterruption(_:)),
                       name: AVAudioSession.interruptionNotification, object: nil)
    center.addObserver(plugin, selector: #selector(onRouteChange(_:)),
                       name: AVAudioSession.routeChangeNotification, object: nil)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "availability":
      let locale = (call.arguments as? [String: Any])?["locale"] as? String ?? "ko-KR"
      result(availability(locale: locale))
    case "requestPermission":
      requestPermission(result: result)
    case "start":
      let locale = (call.arguments as? [String: Any])?["locale"] as? String ?? "ko-KR"
      start(locale: locale)
      result(nil)
    case "stop":
      stop()
      result(nil)
    case "cancel":
      // Dart 가 취소를 알고 있다 — 이벤트 없이 조용히.
      teardown(cancelTask: true)
      result(nil)
    case "openSettings":
      UIApplication.shared.open(URL(string: UIApplication.openSettingsURLString)!)
      result(nil)
    default:
      result(FlutterMethodNotImplemented)
    }
  }

  // MARK: - FlutterStreamHandler

  func onListen(withArguments arguments: Any?, eventSink events: @escaping FlutterEventSink) -> FlutterError? {
    eventSink = events
    return nil
  }

  func onCancel(withArguments arguments: Any?) -> FlutterError? {
    eventSink = nil
    return nil
  }

  // MARK: - 가용성·권한

  private func availability(locale: String) -> [String: Any] {
    // 이 언어의 인식기가 아예 없다.
    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale)) else {
      return ["supported": false, "reason": "locale"]
    }
    // 온디바이스 인식이 없는 기기(시뮬레이터 포함)거나 지금 인식기를 쓸 수 없다.
    guard recognizer.supportsOnDeviceRecognition, recognizer.isAvailable else {
      return ["supported": false, "reason": "device"]
    }
    return ["supported": true]
  }

  /// 음성 인식 권한을 먼저, 허용이면 마이크 권한을 묻는다. 둘 다 허용이어야 granted.
  private func requestPermission(result: @escaping FlutterResult) {
    SFSpeechRecognizer.requestAuthorization { status in
      DispatchQueue.main.async {
        guard status == .authorized else {
          result("denied")
          return
        }
        Self.requestRecordPermission { granted in
          DispatchQueue.main.async { result(granted ? "granted" : "denied") }
        }
      }
    }
  }

  private static func requestRecordPermission(_ done: @escaping (Bool) -> Void) {
    if #available(iOS 17.0, *) {
      AVAudioApplication.requestRecordPermission(completionHandler: done)
    } else {
      AVAudioSession.sharedInstance().requestRecordPermission(done)
    }
  }

  /// 지금 두 권한이 모두 허용인가 — 시작 전과 오류를 읽을 때 쓴다.
  private static var permitted: Bool {
    let record: Bool
    if #available(iOS 17.0, *) {
      record = AVAudioApplication.shared.recordPermission == .granted
    } else {
      record = AVAudioSession.sharedInstance().recordPermission == .granted
    }
    return record && SFSpeechRecognizer.authorizationStatus() == .authorized
  }

  // MARK: - 듣기

  private func start(locale: String) {
    // 앞 세션이 남아 있으면 조용히 치운다.
    teardown(cancelTask: true)

    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale)),
          recognizer.supportsOnDeviceRecognition, recognizer.isAvailable else {
      fail("unsupported")
      return
    }
    guard Self.permitted else {
      fail("denied")
      return
    }

    let audio = AVAudioSession.sharedInstance()
    do {
      try audio.setCategory(.record, mode: .measurement, options: .duckOthers)
      try audio.setActive(true, options: .notifyOthersOnDeactivation)
    } catch {
      fail("failed")
      return
    }

    let request = SFSpeechAudioBufferRecognitionRequest()
    // 서버 인식으로 넘어가지 않게 — 기기 안에서만.
    request.requiresOnDeviceRecognition = true
    request.shouldReportPartialResults = true

    let engine = AVAudioEngine()
    let input = engine.inputNode
    let format = input.outputFormat(forBus: 0)
    // 입력 장치가 없으면 형식이 비어 있고, 탭을 걸면 예외로 앱이 죽는다.
    guard format.sampleRate > 0, format.channelCount > 0 else {
      try? audio.setActive(false, options: .notifyOthersOnDeactivation)
      fail("failed")
      return
    }
    input.installTap(onBus: 0, bufferSize: Self.bufferSize, format: format) { buffer, _ in
      request.append(buffer)
    }
    engine.prepare()
    do {
      try engine.start()
    } catch {
      input.removeTap(onBus: 0)
      try? audio.setActive(false, options: .notifyOthersOnDeactivation)
      fail("failed")
      return
    }

    generation += 1
    let current = generation
    stopping = false
    self.recognizer = recognizer
    self.engine = engine
    self.request = request
    self.task = recognizer.recognitionTask(with: request) { [weak self] result, error in
      DispatchQueue.main.async {
        self?.onRecognition(generation: current, result: result, error: error)
      }
    }
  }

  /// 소리를 그만 받고 인식기에 끝을 알린다 — 마지막 결과는 인식 콜백이 `final` 로 보낸다.
  private func stop() {
    guard task != nil, !stopping else { return }
    stopping = true
    stopAudio()
    request?.endAudio()
  }

  private func onRecognition(generation: Int, result: SFSpeechRecognitionResult?, error: Error?) {
    // 이미 끝났거나 취소된 세션의 늦은 콜백.
    guard generation == self.generation, task != nil else { return }

    if let result {
      let text = result.bestTranscription.formattedString
      guard result.isFinal else {
        send(["type": "partial", "text": text])
        return
      }
      if text.isEmpty {
        finish(error: stopping ? nil : "noSpeech")
      } else {
        send(["type": "final", "text": text])
        finish(error: nil)
      }
      return
    }
    if let error {
      // 멈추라고 한 뒤의 오류(말이 없었음 등)는 알리지 않는다 — 끝났다는 것만.
      finish(error: stopping ? nil : Self.code(for: error))
    }
  }

  /// 인식 오류를 채널 오류 코드로.
  private static func code(for error: Error) -> String {
    // 듣는 도중 설정에서 권한을 거둔 경우 — 코드보다 현재 상태가 정확하다.
    guard permitted else { return "denied" }
    let error = error as NSError
    switch (error.domain, error.code) {
    case ("kAFAssistantErrorDomain", 1110):
      // "No speech detected".
      return "noSpeech"
    case ("kLSRErrorDomain", 201), ("kLSRErrorDomain", 300):
      // 받아쓰기가 꺼져 있음 · 온디바이스 인식기를 띄우지 못함(언어 모델 없음).
      return "unsupported"
    default:
      return "failed"
    }
  }

  // MARK: - 끝내기

  /// 세션을 정리하고 (오류가 있으면 먼저) `ended` 를 보낸다.
  private func finish(error: String?) {
    teardown(cancelTask: false)
    if let error { send(["type": "error", "code": error]) }
    send(["type": "ended"])
  }

  /// 시작 전에 실패했다 — 세션이 없으니 정리할 것 없이 알리기만.
  private func fail(_ code: String) {
    send(["type": "error", "code": code])
    send(["type": "ended"])
  }

  private func stopAudio() {
    guard let engine else { return }
    engine.inputNode.removeTap(onBus: 0)
    engine.stop()
    self.engine = nil
  }

  /// 세션을 치운다. 이벤트는 보내지 않는다. 번호를 올려 늦은 콜백을 버린다.
  private func teardown(cancelTask: Bool) {
    guard task != nil else { return }
    generation += 1
    stopAudio()
    request?.endAudio()
    if cancelTask { task?.cancel() }
    task = nil
    request = nil
    recognizer = nil
    stopping = false
    // 줄였던 다른 앱 소리를 되돌린다.
    try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
  }

  private func send(_ event: [String: Any]) {
    // 듣는 쪽이 없으면 조용히 버린다.
    eventSink?(event)
  }

  // MARK: - 인터럽션·라우트

  /// 전화·알람 등이 오디오를 가져갔다 — 세션을 끝낸다(이어 듣기는 Dart 가 정한다).
  @objc private func onInterruption(_ note: Notification) {
    guard let raw = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
          AVAudioSession.InterruptionType(rawValue: raw) == .began else { return }
    DispatchQueue.main.async { [weak self] in
      guard let self, self.task != nil else { return }
      self.finish(error: nil)
    }
  }

  /// 입력 장치가 빠지거나 새로 붙었다 — 엔진의 입력 형식이 바뀌어 탭이 더는 맞지 않으니 끝낸다.
  @objc private func onRouteChange(_ note: Notification) {
    guard let raw = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
          let reason = AVAudioSession.RouteChangeReason(rawValue: raw),
          reason == .oldDeviceUnavailable || reason == .newDeviceAvailable else { return }
    DispatchQueue.main.async { [weak self] in
      guard let self, self.task != nil else { return }
      self.finish(error: nil)
    }
  }
}
```

`app/ios/Runner/AppDelegate.swift`:

```diff
@@ -14,6 +14,7 @@ import UIKit
     GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
     SharedTextPlugin.register(with: engineBridge.pluginRegistry.registrar(forPlugin: "SharedTextPlugin")!)
     VideoTranscoderPlugin.register(with: engineBridge.pluginRegistry.registrar(forPlugin: "VideoTranscoderPlugin")!)
+    SpeechRecognizerPlugin.register(with: engineBridge.pluginRegistry.registrar(forPlugin: "SpeechRecognizerPlugin")!)
   }
 }
```

`app/ios/Runner.xcodeproj/project.pbxproj`:

```diff
@@ -8,6 +8,7 @@
 
 /* Begin PBXBuildFile section */
 		1498D2341E8E89220040F4C2 /* GeneratedPluginRegistrant.m in Sources */ = {isa = PBXBuildFile; fileRef = 1498D2331E8E89220040F4C2 /* GeneratedPluginRegistrant.m */; };
+		2ACC8D98072A49CEB70D40D3 /* SpeechRecognizer.swift in Sources */ = {isa = PBXBuildFile; fileRef = 12B237730DF506B3FDA88997 /* SpeechRecognizer.swift */; };
 		331C808B294A63AB00263BE5 /* RunnerTests.swift in Sources */ = {isa = PBXBuildFile; fileRef = 331C807B294A618700263BE5 /* RunnerTests.swift */; };
 		3B3967161E833CAA004F5970 /* AppFrameworkInfo.plist in Resources */ = {isa = PBXBuildFile; fileRef = 3B3967151E833CAA004F5970 /* AppFrameworkInfo.plist */; };
 		74858FAF1ED2DC5600515810 /* AppDelegate.swift in Sources */ = {isa = PBXBuildFile; fileRef = 74858FAE1ED2DC5600515810 /* AppDelegate.swift */; };
@@ -63,6 +64,7 @@
 /* End PBXCopyFilesBuildPhase section */
 
 /* Begin PBXFileReference section */
+		12B237730DF506B3FDA88997 /* SpeechRecognizer.swift */ = {isa = PBXFileReference; includeInIndex = 1; lastKnownFileType = sourcecode.swift; path = SpeechRecognizer.swift; sourceTree = "<group>"; };
 		1498D2321E8E86230040F4C2 /* GeneratedPluginRegistrant.h */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = GeneratedPluginRegistrant.h; sourceTree = "<group>"; };
 		1498D2331E8E89220040F4C2 /* GeneratedPluginRegistrant.m */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.c.objc; path = GeneratedPluginRegistrant.m; sourceTree = "<group>"; };
 		331C807B294A618700263BE5 /* RunnerTests.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = RunnerTests.swift; sourceTree = "<group>"; };
@@ -162,6 +164,7 @@
 				74858FAD1ED2DC5600515810 /* Runner-Bridging-Header.h */,
 				A3A3000000000000000000B5 /* Runner.entitlements */,
 				D1914BAA92A23587B65950C1 /* VideoTranscoder.swift */,
+				12B237730DF506B3FDA88997 /* SpeechRecognizer.swift */,
 			);
 			path = Runner;
 			sourceTree = "<group>";
@@ -363,6 +366,7 @@
 				1498D2341E8E89220040F4C2 /* GeneratedPluginRegistrant.m in Sources */,
 				7884E8682EC3CC0700C636F2 /* SceneDelegate.swift in Sources */,
 				80A02225F93E277FB1CA3230 /* VideoTranscoder.swift in Sources */,
+				2ACC8D98072A49CEB70D40D3 /* SpeechRecognizer.swift in Sources */,
 			);
 			runOnlyForDeploymentPostprocessing = 0;
 		};
```

- [ ] **Step 2: 빌드와 정적 분석을 확인한다**

Run (`app/`): `ruby tool/add_ios_file.rb ios/Runner/SpeechRecognizer.swift` → `git diff ios/Runner.xcodeproj` 가 아래 diff 와 같은지 본다

Run (`app/`): `flutter build ios --simulator --debug` → 성공, Runner 의 Swift 경고 0(AppIntents 메타데이터 경고 1건은 기존)

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 754 passed(작업 1 과 같다)

- [ ] **Step 3: 시뮬레이터에서 채널을 확인한다**

임시 진입점 `app/tool/probe_speech.dart`(커밋하지 않는다 — 끝나면 지운다)를 `.superpowers/ref/dictation-plan-gen/probe_speech.dart` 에서 복사한다. `availability()` 결과(`supported`·`reason`)를 화면과 로그(`PROBE …`)에 찍고, `--dart-define=TRY_START=true` 면 `requestPermission()` → `start()` → 12초 동안 이벤트 → `stop()` 까지 찍는다.

Run: `xcrun simctl privacy <UDID> grant microphone com.chagocnote.app`(음성 인식은 못 준다)

Run (`app/`): `flutter run -d <시뮬레이터 UDID> -t tool/probe_speech.dart` → `availability supported=true reason=null`(Xcode 27 시뮬레이터 기준; 다르면 값을 적는다)

Run (`app/`): `flutter run -d <UDID> -t tool/probe_speech.dart --dart-define=TRY_START=true` → 권한 창이 뜬다(헤드리스면 못 누른다). 참조 구현은 권한 요청을 건너뛴 채 `start` 를 불러 `error denied` → `ended` 가 오는 것까지 봤다. partial·final 은 사람이 권한 창을 한 번 누르면 시뮬레이터에서도 볼 수 있다(작업 5 의 흐름이 TCC 데이터베이스로 권한을 넣어 다시 시도한다).

끝나면 `tool/probe_speech.dart` 를 지운다.

- [ ] **Step 4: 커밋한다**

```bash
git add -A
git commit -m "feat(app): iOS 음성 인식 — SFSpeechRecognizer 온디바이스 강제, 부분·확정 결과 이벤트, 권한 둘, 인터럽션은 세션 종료

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Android 음성 인식 — `createOnDeviceSpeechRecognizer` 온디바이스 전용(API 31+), 한국어 지원 확인, 부분·확정 결과 이벤트, 권한 요청 전달

**Files:**
- Create: `app/android/app/src/main/kotlin/com/chagocnote/chagocnote/SpeechRecognizer.kt`
- Modify: `app/android/app/src/main/kotlin/com/chagocnote/chagocnote/MainActivity.kt`

**Interfaces:**
- Consumes: 작업 1 의 채널 규약, 작업 2 의 iOS 구현(오류 순서·의미를 같게: 시작 전 실패도 `error`+`ended`, `denied` 는 현재 권한 상태, `stop` 뒤엔 `ended` 만), `android/.../VideoTranscoder.kt`·`MainActivity.kt`(등록 방식).
- Produces: `android/app/src/main/kotlin/com/chagocnote/chagocnote/SpeechRecognizer.kt` 의 `SpeechRecognizerChannel(activity, messenger)`(`MainActivity.configureFlutterEngine` 이 등록하고 `onRequestPermissionsResult` 를 전달). 새 Gradle 의존성 없음.

설계 3.5 절. 단위 테스트가 없다 — `flutter build apk --debug` 와 에뮬레이터 실기 확인이 검증이다. API 31+ 만 지원(`isOnDeviceRecognitionAvailable` 거짓이면 `device`), 33+ 는 `checkRecognitionSupport` 로 `ko-KR` 이 설치된 온디바이스 언어에 있는지 본다(내려받기 가능이어도 `locale` — 유도하지 않는다; `onError` 로 답하면 `device`). 권한은 Activity 기본 `checkSelfPermission`·`requestPermissions`(minSdk 24). 늦은 콜백은 인식기 객체 동일성으로 버린다. 참조 구현에서 확인한 것: 에뮬레이터(API 37)는 온디바이스 서비스는 있으나 한국어 모델이 없어 `supported=false reason=locale` 이고, 권한을 준 뒤 `start` 하면 SODA `ERROR_LANGUAGE_UNAVAILABLE`(13) → `error unsupported` + `ended` 다. partial·final·stop 은 한국어 모델이 있는 실기기 몫(결정 기록 007 "남는 것"). API 31~32 기기는 `availability` 가 true 라 마이크를 누른 뒤에야 `unsupported` 가 온다.

- [ ] **Step 1: 구현한다**

`app/android/app/src/main/kotlin/com/chagocnote/chagocnote/SpeechRecognizer.kt`:

```kotlin
package com.chagocnote.chagocnote

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognitionSupport
import android.speech.RecognitionSupportCallback
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.annotation.RequiresApi
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * 음성 인식(④-3b 설계 3.5절) — Dart `core/proxy/speech_recognizer.dart` 의 채널 규약을 따른다.
 *
 * API 31+ 의 `createOnDeviceSpeechRecognizer` 로만 인식한다(기기 안에서만 — 서버로 소리를 보내지
 * 않는다). 30 이하는 기기 미지원이다. 결과는 이벤트 채널로 `{type: partial|final|ended|error,
 * text?, code?}` 를 보낸다. 오류 순서·의미는 iOS `SpeechRecognizer.swift` 와 같다 — 시작 전 실패도
 * `error` 뒤 `ended` 이벤트로 알리고, 권한 오류는 현재 권한 상태로 가른다, `stop` 뒤 오류는 `ended` 만.
 *
 * 인식기는 세션마다 만들고 끝나면 `destroy()` 한다. 채널 핸들러·리스너 모두 메인 스레드에서 돈다.
 * 권한 결과는 `MainActivity.onRequestPermissionsResult` 가 [onRequestPermissionsResult] 로 넘겨 준다.
 */
class SpeechRecognizerChannel(
    private val activity: Activity,
    messenger: BinaryMessenger,
) : MethodChannel.MethodCallHandler, EventChannel.StreamHandler {

    private var eventSink: EventChannel.EventSink? = null

    /** 진행 중인 세션의 인식기 — 없으면 null. 리스너가 자기 인식기인지 견줘 늦은 콜백을 버린다. */
    private var recognizer: SpeechRecognizer? = null

    /** `stop` 을 받았다 — 이제 오는 오류는 알리지 않고 `ended` 만 보낸다. */
    private var stopping = false

    /** 권한 창의 답을 기다리는 호출. */
    private var permissionResult: MethodChannel.Result? = null

    init {
        MethodChannel(messenger, CHANNEL).setMethodCallHandler(this)
        EventChannel(messenger, EVENTS_CHANNEL).setStreamHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "availability" -> availability(call.argument<String>("locale") ?: DEFAULT_LOCALE, result)
            "requestPermission" -> requestPermission(result)
            "start" -> {
                start(call.argument<String>("locale") ?: DEFAULT_LOCALE)
                result.success(null)
            }
            "stop" -> {
                stop()
                result.success(null)
            }
            "cancel" -> {
                // Dart 가 취소를 알고 있다 — 이벤트 없이 조용히.
                teardown()
                result.success(null)
            }
            "openSettings" -> {
                activity.startActivity(
                    Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                        .setData(Uri.fromParts("package", activity.packageName, null)),
                )
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
        eventSink = events
    }

    override fun onCancel(arguments: Any?) {
        eventSink = null
    }

    // 가용성·권한

    private fun availability(locale: String, result: MethodChannel.Result) {
        // 온디바이스 인식은 31 부터 — 그 아래이거나 이 기기에 온디바이스 인식 서비스가 없다.
        if (!onDeviceAvailable()) {
            result.success(mapOf("supported" to false, "reason" to "device"))
            return
        }
        // 31~32 는 언어를 미리 물을 수 없다 — `start` 의 언어 오류(unsupported)로 가른다.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            result.success(mapOf("supported" to true))
            return
        }
        checkLocale(locale, result)
    }

    /** 이 언어 모델이 기기에 깔려 있는가. 내려받을 수 있기만 해도 `locale` — 내려받기를 유도하지 않는다. */
    @RequiresApi(Build.VERSION_CODES.TIRAMISU)
    private fun checkLocale(locale: String, result: MethodChannel.Result) {
        val checker = SpeechRecognizer.createOnDeviceSpeechRecognizer(activity)
        checker.checkRecognitionSupport(
            recognizeIntent(locale),
            activity.mainExecutor,
            object : RecognitionSupportCallback {
                override fun onSupportResult(support: RecognitionSupport) {
                    checker.destroy()
                    val language = locale.substringBefore('-')
                    val installed = support.installedOnDeviceLanguages.any {
                        it.equals(locale, ignoreCase = true) || it.equals(language, ignoreCase = true)
                    }
                    result.success(
                        if (installed) mapOf("supported" to true)
                        else mapOf("supported" to false, "reason" to "locale"),
                    )
                }

                override fun onError(error: Int) {
                    // 인식 서비스가 지원 여부조차 답하지 못한다 — 기기 쪽 문제로 본다.
                    checker.destroy()
                    result.success(mapOf("supported" to false, "reason" to "device"))
                }
            },
        )
    }

    private fun requestPermission(result: MethodChannel.Result) {
        if (permitted()) {
            result.success("granted")
            return
        }
        permissionResult = result
        activity.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), PERMISSION_REQUEST_CODE)
    }

    /** `MainActivity` 가 넘겨 주는 권한 창의 답. 우리 요청 코드가 아니면 무시한다. */
    fun onRequestPermissionsResult(requestCode: Int, grantResults: IntArray) {
        if (requestCode != PERMISSION_REQUEST_CODE) return
        val result = permissionResult ?: return
        permissionResult = null
        val granted = grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
        result.success(if (granted) "granted" else "denied")
    }

    /** 지금 마이크 권한이 허용인가 — 시작 전과 오류를 읽을 때 쓴다. */
    private fun permitted(): Boolean =
        activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private fun onDeviceAvailable(): Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            SpeechRecognizer.isOnDeviceRecognitionAvailable(activity)

    // 듣기

    private fun start(locale: String) {
        // 앞 세션이 남아 있으면 조용히 치운다.
        teardown()

        if (!onDeviceAvailable()) {
            fail("unsupported")
            return
        }
        if (!permitted()) {
            fail("denied")
            return
        }

        val recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(activity)
        this.recognizer = recognizer
        stopping = false
        recognizer.setRecognitionListener(Listener(recognizer))
        recognizer.startListening(recognizeIntent(locale))
    }

    /** 소리를 그만 받는다 — 뒤이어 `onResults` 또는 `onError` 가 온다. */
    private fun stop() {
        val recognizer = recognizer ?: return
        if (stopping) return
        stopping = true
        recognizer.stopListening()
    }

    private fun recognizeIntent(locale: String): Intent =
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, locale)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)

    private inner class Listener(private val owner: SpeechRecognizer) : RecognitionListener {
        /** 끝났거나 취소된 세션의 늦은 콜백이 아닌가. */
        private val current get() = recognizer === owner

        override fun onPartialResults(partialResults: Bundle?) {
            if (!current) return
            send(mapOf("type" to "partial", "text" to firstText(partialResults)))
        }

        override fun onResults(results: Bundle?) {
            if (!current) return
            val text = firstText(results)
            if (text.isEmpty()) {
                finish(if (stopping) null else "noSpeech")
            } else {
                send(mapOf("type" to "final", "text" to text))
                finish(null)
            }
        }

        override fun onError(error: Int) {
            if (!current) return
            // 멈추라고 한 뒤의 오류(말이 없었음 등)는 알리지 않는다 — 끝났다는 것만.
            finish(if (stopping) null else code(error))
        }

        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}
        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    private fun firstText(bundle: Bundle?): String =
        bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()

    /** 인식 오류를 채널 오류 코드로. */
    private fun code(error: Int): String {
        // 듣는 도중 설정에서 권한을 거둔 경우 — 코드보다 현재 상태가 정확하다(iOS 와 같은 규칙).
        if (!permitted()) return "denied"
        return when (error) {
            SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "noSpeech"
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "denied"
            SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED, SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE -> "unsupported"
            else -> "failed"
        }
    }

    // 끝내기

    /** 세션을 정리하고 (오류가 있으면 먼저) `ended` 를 보낸다. */
    private fun finish(error: String?) {
        teardown()
        fail(error)
    }

    /** 오류가 있으면 알리고 `ended` 를 보낸다 — 시작 전 실패는 세션이 없으니 이것만. */
    private fun fail(error: String?) {
        if (error != null) send(mapOf("type" to "error", "code" to error))
        send(mapOf("type" to "ended"))
    }

    /** 세션을 치운다. 이벤트는 보내지 않는다. `recognizer` 를 비워 늦은 콜백을 버린다. */
    private fun teardown() {
        val recognizer = recognizer ?: return
        this.recognizer = null
        stopping = false
        recognizer.cancel()
        recognizer.destroy()
    }

    private fun send(event: Map<String, Any>) {
        // 듣는 쪽이 없으면 조용히 버린다.
        eventSink?.success(event)
    }

    private companion object {
        const val CHANNEL = "chagocnote/speech"
        const val EVENTS_CHANNEL = "chagocnote/speech/events"
        const val DEFAULT_LOCALE = "ko-KR"
        const val PERMISSION_REQUEST_CODE = 4301
    }
}
```

`app/android/app/src/main/kotlin/com/chagocnote/chagocnote/MainActivity.kt`:

```diff
@@ -16,6 +16,7 @@ import io.flutter.plugin.common.MethodChannel
 class MainActivity : FlutterActivity() {
     private var channel: MethodChannel? = null
     private var pending: String? = null
+    private var speech: SpeechRecognizerChannel? = null
 
     override fun onCreate(savedInstanceState: Bundle?) {
         super.onCreate(savedInstanceState)
@@ -32,6 +33,8 @@ class MainActivity : FlutterActivity() {
         super.configureFlutterEngine(flutterEngine)
         // 영상 압축·포스터(④-3a).
         VideoTranscoderChannel(applicationContext, flutterEngine.dartExecutor.binaryMessenger)
+        // 음성 인식(④-3b) — 권한 창을 띄우고 설정을 열어야 해서 액티비티를 준다.
+        speech = SpeechRecognizerChannel(this, flutterEngine.dartExecutor.binaryMessenger)
         channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).also { ch ->
             ch.setMethodCallHandler { call, result ->
                 if (call.method == "getPending") {
@@ -44,6 +47,12 @@ class MainActivity : FlutterActivity() {
         }
     }
 
+    /** 마이크 권한 창의 답을 음성 인식 채널에 넘긴다. */
+    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
+        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
+        speech?.onRequestPermissionsResult(requestCode, grantResults)
+    }
+
     /**
      * [coldStart]면(onCreate) Dart 엔진이 아직 `onStart` 전이라 이 시점에 invoke 해도
      * 메시지가 버려진다("Dropping platform message on channel") — 그래서 콜드
```

- [ ] **Step 2: 빌드와 정적 분석을 확인한다**

Run (`app/`): `flutter build apk --debug` → 성공, 우리 파일의 Kotlin 경고 0

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 754 passed(작업 2 와 같다)

- [ ] **Step 3: 에뮬레이터에서 채널을 확인한다**

안드로이드 에뮬레이터를 켠다(`flutter emulators --launch <id>`, `adb` 는 `~/Library/Android/sdk/platform-tools/adb`). 임시 진입점 `app/tool/probe_speech.dart`(커밋하지 않는다 — 끝나면 지운다)를 `.superpowers/ref/dictation-plan-gen/probe_speech.dart` 에서 복사한다. `availability()` 결과(`supported`·`reason`)를 화면과 로그(`PROBE …`)에 찍고, `--dart-define=TRY_START=true` 면 `requestPermission()` → `start()` → 12초 동안 이벤트 → `stop()` 까지 찍는다.

Run (`app/`): `flutter run -d <에뮬레이터> -t tool/probe_speech.dart` → 참조 구현(API 37, 한국어 모델 없음)은 `availability supported=false reason=locale`. 모델이 있는 이미지면 `supported=true`.

Run: `adb shell pm grant com.chagocnote.app android.permission.RECORD_AUDIO` 뒤 `flutter run … --dart-define=TRY_START=true` → 모델이 없으면 `permission granted` → `error unsupported` → `ended`; 모델이 있으면 맥 마이크로 한 문장을 말해 `partial`·`final`·`ended` 를 본다(가능하면).

끝나면 `tool/probe_speech.dart` 를 지운다.

- [ ] **Step 4: 커밋한다**

```bash
git add -A
git commit -m "feat(app): Android 음성 인식 — createOnDeviceSpeechRecognizer 온디바이스 전용(API 31+), 한국어 지원 확인, 부분·확정 결과 이벤트, 권한 요청 전달

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 받아쓰기 세션 — 커서 자리 부분·확정 삽입, 무음 10초, 네이티브 종료 뒤 이어 듣기, 손 입력·상한이면 끝, 회색 구간 컨트롤러, 마이크 버튼

**Files:**
- Create: `app/lib/features/visit/state/dictation.dart`
- Create: `app/lib/design/widgets/dictation_text_editing_controller.dart`
- Create: `app/lib/design/widgets/app_mic_button.dart`
- Create: `app/test/features/visit/state/dictation_test.dart`
- Create: `app/test/design/dictation_text_editing_controller_test.dart`
- Create: `app/test/design/app_mic_button_test.dart`
- Create: `app/test/design/goldens/app_mic_button.png`

**Interfaces:**
- Consumes: 작업 1 의 `SpeechRecognizer`·`SpeechEvent`·`SpeechErrorCode`·`FakeSpeechRecognizer`. 네이티브(작업 2·3)는 시작 전 실패도 `error`+`ended` 로, `stop` 뒤엔 `final`(있으면)+`ended` 또는 `ended` 만 보낸다.
- Produces: `design/widgets/dictation_text_editing_controller.dart` — `DictationTextEditingController extends TextEditingController { TextRange? pending; }`(진행 중 구간만 연한 잉크색으로 `buildTextSpan`; Flutter 만 import). `design/widgets/app_mic_button.dart` — `AppMicButton({required bool listening, required VoidCallback onTap, String? semanticLabel})`(44×44, 듣는 중이면 잉크색 점이 깜빡임). `features/visit/state/dictation.dart` — `Dictation extends ChangeNotifier { Dictation({recognizer, controller, maxLength, silence = 10s}); bool get listening; SpeechErrorCode? get lastError; start(); stop(); cancel(); dispose(); }`.

설계 3.2·3.3·4절. `Dictation` 은 시작할 때 커서 자리를 진행 중 구간으로 잡고, `partial` 은 그 구간을 갈아 끼우고 `final` 은 굳혀 커서를 뒤로 옮긴다. 한 세션 안 구절 사이에만 띄어쓰기 하나(첫 구간엔 넣지 않는다 — 커서 앞 글에 붙인다). 무음 10초는 Dart 가 잰다(`start` 와 매 `partial`/`final` 에서 다시). 네이티브가 먼저 `ended` 를 보내면 10초 안이면 `start()` 를 다시 불러 이어 듣고(`final` 없는 `ended` 는 회색 글을 굳힌 뒤), 넘었으면 끝. 끝난 뒤 오는 `final`·`ended` 는 무시한다. 손으로 고치면(우리가 넣은 변경이 아닌 텍스트 변화) 끝, 길이 상한을 넘으면 잘라 넣고 끝, `cancel` 은 회색 글을 굳혀 두고 끝. 점은 설계의 붉은색 대신 **잉크색** — `AppColors` 에 붉은 토큰이 없고 팔레트 밖 색은 금지이며 테마의 error 도 ink 다(결정 기록 007). 시간 테스트는 `fake_async` 가 dev 의존에 없어 `testWidgets` 의 가짜 시계로 한다. **화면 작업 주의(작업 5)**: 칸 A 를 `stop()` 하고 곧바로 칸 B 를 `start()` 하면 A 의 늦은 `final`·`ended` 가 B 에 섞일 수 있다 — 칸을 바꿀 때는 `cancel()` 을 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/visit/state/dictation_test.dart`:

```dart
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
```

`app/test/design/dictation_text_editing_controller_test.dart`:

```dart
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/dictation_text_editing_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('진행 중 구간만 회색으로 나뉘어 그려지고, 구간이 없으면 한 덩이다', (tester) async {
    final controller = DictationTextEditingController(text: '앞안녕뒤');
    addTearDown(controller.dispose);
    late BuildContext context;
    await tester.pumpWidget(
      Builder(
        builder: (c) {
          context = c;
          return const SizedBox();
        },
      ),
    );
    const style = TextStyle(color: AppColors.ink);

    var notified = 0;
    controller.addListener(() => notified++);
    controller.pending = const TextRange(start: 1, end: 3);
    expect(notified, 1);

    final span = controller.buildTextSpan(
      context: context,
      style: style,
      withComposing: false,
    );
    final children = span.children!.cast<TextSpan>();
    expect(children.map((s) => s.text), ['앞', '안녕', '뒤']);
    expect(children[0].style?.color, isNot(AppColors.secondary));
    expect(children[1].style?.color, AppColors.secondary);
    expect(children[2].style?.color, isNot(AppColors.secondary));

    controller.pending = null;
    final plain = controller.buildTextSpan(
      context: context,
      style: style,
      withComposing: false,
    );
    expect(plain.toPlainText(), '앞안녕뒤');
    expect(plain.children, isNull);
  });
}
```

`app/test/design/app_mic_button_test.dart`:

```dart
import 'package:chagocnote/design/widgets/app_mic_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('누르면 onTap 이 불리고, 탭 영역은 44×44 다', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: AppMicButton(
              listening: false,
              onTap: () => taps++,
              semanticLabel: '말로 기록하기',
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.bySemanticsLabel('말로 기록하기'));
    await tester.pump(const Duration(milliseconds: 500));

    expect(taps, 1);
    expect(tester.getSize(find.bySemanticsLabel('말로 기록하기')), const Size(44, 44));
  });

  testWidgets('AppMicButton 골든 — 쉬는 것과 듣는 것', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppMicButton(listening: false, onTap: () {}),
          const SizedBox(width: 12),
          AppMicButton(listening: true, onTap: () {}),
        ],
      ),
      surfaceSize: const Size(160, 80),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_mic_button.png'));
  });
}
```

`app/test/design/goldens/app_mic_button.png`: 골든 이미지 — 이 문서에 넣지 않는다. 이 작업의 골든 테스트를 `--update-goldens`로 돌려 만들고 눈으로 본다(의도한 변경).

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/features/visit/state/dictation_test.dart test/design/dictation_text_editing_controller_test.dart test/design/app_mic_button_test.dart`
Expected: 컴파일 실패 — 세 파일이 없다.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/state/dictation.dart`:

```dart
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
/// - 한 번에 한 칸만 듣게 하는 것은 화면 몫이다(다른 세션을 시작하기 전에 앞 것을 [stop]).
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
    if (!_end()) return;
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
```

`app/lib/design/widgets/dictation_text_editing_controller.dart`:

```dart
import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';

/// 받아쓰기 중인 메모 칸의 컨트롤러 — 아직 굳지 않은 인식 결과([pending])만 회색으로 그린다.
///
/// 그리기만 한다. 구간을 정하고 글을 넣는 것은 받아쓰기 세션(`features/visit/state/dictation.dart`)이다.
class DictationTextEditingController extends TextEditingController {
  DictationTextEditingController({super.text});

  TextRange? _pending;

  /// 진행 중 구간. null 이면 회색 글이 없다.
  TextRange? get pending => _pending;

  set pending(TextRange? range) {
    if (range == _pending) return;
    _pending = range;
    notifyListeners();
  }

  @override
  TextSpan buildTextSpan({
    required BuildContext context,
    TextStyle? style,
    required bool withComposing,
  }) {
    final range = _pending;
    if (range == null) {
      return super.buildTextSpan(
        context: context,
        style: style,
        withComposing: withComposing,
      );
    }
    return TextSpan(
      style: style,
      children: [
        TextSpan(text: range.textBefore(text)),
        TextSpan(
          text: range.textInside(text),
          style: const TextStyle(color: AppColors.secondary),
        ),
        TextSpan(text: range.textAfter(text)),
      ],
    );
  }
}
```

`app/lib/design/widgets/app_mic_button.dart`:

```dart
import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import 'pressable.dart';

/// 메모 칸 제목 줄의 받아쓰기 토글(④-3b 설계 3.3).
///
/// 쉬는 동안은 마이크 아이콘만, 듣는 동안은 아이콘 오른쪽 위에 점이 0.8초 주기로 깜빡인다.
/// 점은 팔레트의 포인트 색(잉크)이다 — 이 앱은 팔레트 밖의 색(붉은색)을 들이지 않는다.
/// 탭 영역은 44×44.
class AppMicButton extends StatefulWidget {
  const AppMicButton({
    super.key,
    required this.listening,
    required this.onTap,
    this.semanticLabel,
  });

  final bool listening;
  final VoidCallback onTap;
  final String? semanticLabel;

  @override
  State<AppMicButton> createState() => _AppMicButtonState();
}

class _AppMicButtonState extends State<AppMicButton>
    with SingleTickerProviderStateMixin {
  // 0.4초에 한 번 꺼지고 0.4초에 켜진다 — 한 주기 0.8초. 첫 프레임(0)은 켜진 점이다.
  late final AnimationController _blink;

  @override
  void initState() {
    super.initState();
    _blink = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    if (widget.listening) _blink.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(AppMicButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.listening == oldWidget.listening) return;
    if (widget.listening) {
      _blink.repeat(reverse: true);
    } else {
      _blink.reset();
    }
  }

  @override
  void dispose() {
    _blink.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: widget.onTap,
      semanticLabel: widget.semanticLabel,
      child: SizedBox(
        width: 44,
        height: 44,
        child: Stack(
          alignment: Alignment.center,
          children: [
            const Icon(Icons.mic_rounded, size: 22, color: AppColors.ink),
            if (widget.listening)
              Positioned(
                top: 9,
                right: 9,
                child: FadeTransition(
                  opacity: ReverseAnimation(_blink),
                  child: Container(
                    width: 7,
                    height: 7,
                    decoration: const BoxDecoration(
                      color: AppColors.ink,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s --update-goldens test/design/app_mic_button_test.dart` → 골든 `test/design/goldens/app_mic_button.png` 생성. 눈으로 본다(쉬는 쪽은 잉크색 마이크만, 듣는 쪽은 마이크 오른쪽 위에 잉크색 점).

Run (`app/`): `flutter test --timeout 60s test/features/visit/state/dictation_test.dart test/design/dictation_text_editing_controller_test.dart test/design/app_mic_button_test.dart` → 11 passed

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 765 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 구절 사이 띄어쓰기 삽입 제거 → `dictation_test.dart::두 구절을 이어 받으면 사이에 띄어쓰기를 하나 넣는다` 실패.
- 무음 타이머를 `partial` 에서 다시 재지 않게 → `::무음 10초면 끝난다` 실패.
- `ended` 뒤 재시작 제거 → `::네이티브가 먼저 끝내도 10초 안이면 이어 듣고, 넘었으면 끝난다` 실패.
- 길이 상한 자르기 제거 → `::길이 상한을 넘는 결과는 잘라 넣고 끝난다` 실패.
- `buildTextSpan` 의 pending 스타일 제거 → `dictation_text_editing_controller_test.dart::진행 중 구간만 회색으로 나뉘어 그려지고, 구간이 없으면 한 덩이다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 받아쓰기 세션 — 커서 자리 부분·확정 삽입, 무음 10초, 네이티브 종료 뒤 이어 듣기, 손 입력·상한이면 끝, 회색 구간 컨트롤러, 마이크 버튼

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 기록 화면 말로 기록하기 — 메모 칸의 마이크, 미지원·권한·인식 실패 안내, 시뮬레이터 흐름, 앱 규칙·하네스·결정 기록 007

**Files:**
- Modify: `app/lib/features/visit/screens/record_screen.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/lib/design/widgets/app_snack_bar.dart`
- Modify: `app/ios/Runner/Info.plist`
- Modify: `app/test/features/visit/screens/record_screen_test.dart`
- Modify: `app/test/support/customer_test_app.dart`
- Modify: `app/test/support/upload_fakes.dart`
- Create: `app/integration_test/dictation_flow_test.dart`
- Modify: `app/CLAUDE.md`
- Modify: `_docs/harness.md`
- Modify: `_docs/decisions/007-record-media.md`
- Modify: `app/test/features/visit/screens/goldens/record_screen.png`

**Interfaces:**
- Consumes: 작업 1 의 `speechRecognizerProvider`·`FakeSpeechRecognizer`, 작업 4 의 `Dictation`·`DictationTextEditingController`·`AppMicButton`, `record_screen.dart` 의 `_Section`·메모 컨트롤러, `AppSnackBar`, `integration_test/record_flow_test.dart`·`flow_kit.dart`.
- Produces: `record_screen.dart` 의 마이크 둘과 `_toggleDictation`, `AppStrings.dictationUnsupported·dictationDenied·dictationNoSpeech·dictationFailed·openSettings·micLabel`, `AppSnackBar.show(action:)`, `test/support/customer_test_app.dart` 의 `FakeSpeechRecognizer` 기본 주입(`setup.speech`), `FakeSpeechRecognizer.calls`(호출 차례), `integration_test/dictation_flow_test.dart`, 문서 셋.

설계 2·4·5·6절. 마이크를 누르면 ① 다른 칸이 듣는 중이면 **`cancel()`**(`stop` 뒤 곧바로 `start` 하면 앞 칸의 늦은 `final`·`ended` 가 뒤 칸에 섞인다 — 결정 기록 007) ② `availability()` 미지원이면 안내 ③ `requestPermission()` 거부면 안내 + [설정 열기] ④ 포커스 주고 `start()`. 포커스가 떠나면·화면이 사라지면(`dispose`)·앱이 뒤로 가면(`AppLifecycleListener.onHide`) `cancel`. 오류 스낵바는 칸마다 마지막으로 띄운 오류를 기억해 한 번만. `AppSnackBar.show` 에 `action` 인자를 더한다(액션이 있는 스낵바는 닫을 때까지 남는다). `NSMicrophoneUsageDescription` 은 영상·받아쓰기 둘 다 덮는 문구로. 골든 `record_screen.png` 는 마이크 버튼 둘이 더해져 **의도한 갱신**이다. 흐름 `dictation_flow_test.dart`: PASS 1 은 실제 채널 — 권한을 미리 주고(`xcrun simctl privacy … grant microphone` + 시뮬레이터 TCC 데이터베이스에 음성 인식 행 삽입 + `tccd` 재시작) 마이크를 누르면 시작까지 가고, Xcode 27 시뮬레이터는 `availability` 가 true 라 답하지만 `start` 하면 곧바로 `error unsupported`·`ended` 라 미지원 안내 스낵바로 끝나는 것을 확인한다(실제 partial·final 은 실기기 몫). PASS 2 는 인식기만 `FakeSpeechRecognizer` 로 바꿔 partial→final 이 커서 자리에 들어가 저장되고 상세에 보이는 것. 흐름 실행 전 시뮬레이터에 예전 권한 창이 남아 있으면 스크린샷이 하얗게 찍힌다 — 시뮬레이터를 껐다 켠다(하네스에 적혀 있다). 첫 실행에서 CoreAudio 교착으로 앱이 한 번 죽은 적이 있다(재현 안 됨).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/visit/screens/record_screen_test.dart`:

```diff
@@ -2,10 +2,13 @@ import 'dart:async';
 
 import 'package:chagocnote/core/proxy/media_images.dart';
 import 'package:chagocnote/core/proxy/media_picker.dart';
+import 'package:chagocnote/core/proxy/speech_recognizer.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/core/time/today_provider.dart';
 import 'package:chagocnote/design/widgets/app_back_button.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
+import 'package:chagocnote/design/widgets/app_mic_button.dart';
+import 'package:chagocnote/design/widgets/dictation_text_editing_controller.dart';
 import 'package:chagocnote/design/widgets/pressable.dart';
 import 'package:chagocnote/features/visit/api/record_models.dart';
 import 'package:chagocnote/features/visit/state/upload_job.dart';
@@ -136,6 +139,25 @@ Future<void> _tap(WidgetTester tester, Finder finder) async {
   await settle(tester);
 }
 
+Finder _mic(String label) => find.byWidgetPredicate(
+  (w) => w is AppMicButton && w.semanticLabel == '$label ${AppStrings.micLabel}',
+);
+
+bool _listening(WidgetTester tester, String label) =>
+    tester.widget<AppMicButton>(_mic(label)).listening;
+
+DictationTextEditingController _controller(WidgetTester tester, String key) =>
+    tester.widget<TextField>(_field(key)).controller!
+        as DictationTextEditingController;
+
+/// 마이크를 누른다. 듣는 동안은 점이 깜빡여 settle 할 수 없다 — 몇 번만 그린다.
+Future<void> _tapMic(WidgetTester tester, String label) async {
+  await tester.ensureVisible(_mic(label));
+  await tester.tap(_mic(label));
+  await tester.pump();
+  await tester.pump();
+}
+
 Map<String, dynamic> _savedRecord() => recordJson(
   weightKg: 4.0,
   careNote: '발바닥 각질',
@@ -706,6 +728,132 @@ void main() {
     );
   });
 
+  group('말로 기록하기', () {
+    testWidgets('케어 메모의 마이크를 누르면 듣기 시작하고, partial 이 커서 자리에 회색으로, final 이 굳어 들어간다', (
+      tester,
+    ) async {
+      final server = _Server(record: recordJson(careNote: '앞뒤', version: 3));
+      final (app, _) = await _open(tester, server);
+      final speech = app.setup.speech;
+      final care = _controller(tester, 'careNote');
+      care.selection = const TextSelection.collapsed(offset: 1);
+
+      await _tapMic(tester, AppStrings.careNoteLabel);
+      expect(_listening(tester, AppStrings.careNoteLabel), isTrue);
+      expect(_listening(tester, AppStrings.internalNoteLabel), isFalse);
+      expect(speech.starts, ['ko-KR']);
+
+      speech.emitPartial('안녕');
+      await tester.pump();
+      expect(care.text, '앞안녕뒤');
+      expect(care.pending, const TextRange(start: 1, end: 3));
+
+      speech.emitFinal('안녕하세요');
+      await tester.pump();
+      expect(care.text, '앞안녕하세요뒤');
+      expect(care.pending, isNull);
+
+      await _tapMic(tester, AppStrings.careNoteLabel);
+      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
+      expect(speech.stops, 1);
+      await _tap(tester, _button(AppStrings.save));
+      expect(server.puts.single['care_note'], '앞안녕하세요뒤');
+    });
+
+    testWidgets('듣는 중에 내부 메모의 마이크를 누르면 앞 것이 끝나고 뒤 것이 시작한다', (tester) async {
+      final (app, _) = await _open(tester, _Server());
+      final speech = app.setup.speech;
+
+      await _tapMic(tester, AppStrings.careNoteLabel);
+      speech.emitPartial('발바닥');
+      await tester.pump();
+      await _tapMic(tester, AppStrings.internalNoteLabel);
+
+      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
+      expect(_listening(tester, AppStrings.internalNoteLabel), isTrue);
+      // 앞 칸의 cancel 이 뒤 칸의 start 보다 먼저다 — 늦으면 뒤 칸의 네이티브 세션을 끊는다.
+      expect(speech.calls, ['start', 'cancel', 'start']);
+      expect(_text(tester, 'careNote'), '발바닥');
+      expect(_controller(tester, 'careNote').pending, isNull);
+
+      speech.emitFinal('예민함');
+      await tester.pump();
+      expect(_text(tester, 'careNote'), '발바닥');
+      expect(_text(tester, 'internalNote'), '예민함');
+      await _tapMic(tester, AppStrings.internalNoteLabel);
+    });
+
+    testWidgets('지원하지 않는 기기면 안내 스낵바가 뜨고 시작하지 않는다', (tester) async {
+      final (app, _) = await _open(tester, _Server());
+      app.setup.speech.availabilityResult = const SpeechAvailability(
+        supported: false,
+        reason: SpeechUnsupported.device,
+      );
+
+      await _tap(tester, _mic(AppStrings.careNoteLabel));
+
+      expect(find.text(AppStrings.dictationUnsupported), findsOneWidget);
+      expect(app.setup.speech.starts, isEmpty);
+      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
+    });
+
+    testWidgets('권한을 거부하면 안내와 [설정 열기]가 뜨고 누르면 설정을 연다', (tester) async {
+      final (app, _) = await _open(tester, _Server());
+      app.setup.speech.permissionResult = SpeechPermission.denied;
+
+      await _tap(tester, _mic(AppStrings.careNoteLabel));
+
+      expect(find.text(AppStrings.dictationDenied), findsOneWidget);
+      expect(app.setup.speech.starts, isEmpty);
+      await _tap(tester, find.text(AppStrings.openSettings));
+      expect(app.setup.speech.settingsOpened, 1);
+    });
+
+    testWidgets('아무 말도 못 알아들으면 문구가 뜬다', (tester) async {
+      final (app, _) = await _open(tester, _Server());
+
+      await _tapMic(tester, AppStrings.careNoteLabel);
+      app.setup.speech.emitError(SpeechErrorCode.noSpeech);
+      await settle(tester);
+
+      expect(find.text(AppStrings.dictationNoSpeech), findsOneWidget);
+      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
+      expect(_text(tester, 'careNote'), '');
+    });
+
+    testWidgets('다른 칸을 누르면 듣기가 끝난다', (tester) async {
+      final (app, _) = await _open(tester, _Server());
+
+      await _tapMic(tester, AppStrings.careNoteLabel);
+      await tester.tap(_field('internalNote'));
+      await settle(tester);
+
+      expect(app.setup.speech.cancels, 1);
+      expect(_listening(tester, AppStrings.careNoteLabel), isFalse);
+    });
+
+    testWidgets('화면을 나가면 cancel 한다', (tester) async {
+      final (app, closed) = await _open(tester, _Server());
+
+      await _tapMic(tester, AppStrings.careNoteLabel);
+      await tester.binding.handlePopRoute();
+      await settle(tester);
+
+      expect(closed.closed, isTrue);
+      expect(app.setup.speech.cancels, 1);
+    });
+
+    testWidgets('포커스를 잃었다는 알림 없이 화면이 사라져도 cancel 한다', (tester) async {
+      final (app, _) = await _open(tester, _Server());
+
+      await _tapMic(tester, AppStrings.careNoteLabel);
+      // 뒤로 가기는 포커스가 먼저 떠나 칸의 리스너가 끝낸다 — 앱째 내려 dispose 만 남긴다.
+      await tester.pumpWidget(const SizedBox());
+
+      expect(app.setup.speech.cancels, 1);
+    });
+  });
+
   testWidgets('기록 화면 골든', (tester) async {
     final server = _Server(record: _savedRecord());
     final (app, _) = await _open(
```

`app/test/support/customer_test_app.dart`:

```diff
@@ -1,6 +1,7 @@
 import 'package:chagocnote/core/proxy/api_client.dart';
 import 'package:chagocnote/core/proxy/network_watcher.dart';
 import 'package:chagocnote/core/proxy/providers.dart';
+import 'package:chagocnote/core/proxy/speech_recognizer.dart';
 import 'package:chagocnote/core/router/app_router.dart';
 import 'package:chagocnote/core/storage/prefs_store.dart';
 import 'package:chagocnote/core/storage/token_store.dart';
@@ -56,6 +57,8 @@ class CustomerTestSetup {
         prefsStoreProvider.overrideWithValue(prefs),
         // 테스트에는 연결 상태 플러그인이 없다 — 인터넷 복귀 신호는 [network]로 보낸다.
         networkWatcherProvider.overrideWithValue(network),
+        // 테스트에는 음성 인식 채널이 없다 — 기록 화면의 받아쓰기는 [speech]로 흘린다.
+        speechRecognizerProvider.overrideWithValue(speech),
         apiClientProvider.overrideWith(
           (ref) => ApiClient(
             tokenStore: MemoryTokenStore(),
@@ -72,6 +75,7 @@ class CustomerTestSetup {
   final FakeHttpClientAdapter adapter;
   final FakeSessionGateway gateway;
   final network = FakeNetworkWatcher();
+  final speech = FakeSpeechRecognizer();
   final MemoryPrefsStore prefs;
   late final ProviderContainer container;
```

`app/test/support/upload_fakes.dart`:

```diff
@@ -323,6 +323,9 @@ class FakeSpeechRecognizer implements SpeechRecognizer {
   var settingsOpened = 0;
   var permissionRequests = 0;
 
+  /// start·stop·cancel 을 부른 차례.
+  final calls = <String>[];
+
   @override
   Future<SpeechAvailability> availability() async => availabilityResult;
 
@@ -336,13 +339,22 @@ class FakeSpeechRecognizer implements SpeechRecognizer {
   Stream<SpeechEvent> get events => _events.stream;
 
   @override
-  Future<void> start({String locale = 'ko-KR'}) async => starts.add(locale);
+  Future<void> start({String locale = 'ko-KR'}) async {
+    starts.add(locale);
+    calls.add('start');
+  }
 
   @override
-  Future<void> stop() async => stops++;
+  Future<void> stop() async {
+    stops++;
+    calls.add('stop');
+  }
 
   @override
-  Future<void> cancel() async => cancels++;
+  Future<void> cancel() async {
+    cancels++;
+    calls.add('cancel');
+  }
 
   @override
   Future<void> openSettings() async => settingsOpened++;
```

`app/integration_test/dictation_flow_test.dart`:

```dart
// ④-3b 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 기록 화면의 말로 기록하기를 확인한다.
// 도구는 `flow_kit.dart`.
//
// PASS 1 은 실제 음성 인식 채널이다. Xcode 27 시뮬레이터는 availability 에 ko-KR 온디바이스 지원(true)이라
// 답하지만, 권한을 넘어 start 하면 인식기가 곧바로 `error unsupported` + `ended` 로 끝난다(2026-09-27 확인 —
// 오디오 엔진은 켜졌다 0.1초 만에 멈춘다). 그래서 흐름은 "실제 채널로 권한·시작까지 가고, 시작이 미지원으로
// 끝나면 미지원 안내가 뜨고 듣는 중이 아니다"를 본다. 무음 10초로 끝나는 경로는 실기기 몫이다. 만약 인식이
// 실제로 시작되면(듣는 중이 유지되면) 무음 10초 뒤 스스로 끝나는지를 대신 본다.
// PASS 2 는 인식기만 대역(`test/support/upload_fakes.dart` 의 `FakeSpeechRecognizer`)으로 바꿔 부분·확정
// 결과를 흘린다 — 커서 자리 삽입·저장·상세 표시는 실제로 한다. 앱은 한 번만 띄우고 인식기 자리를
// [SwitchRecognizer] 로 바꿔 낀다(받아쓰기 세션은 기록 화면을 열 때 인식기를 잡는다).
//
// 준비(infra/ 에서): bash ../app/tool/prepare_record_flow.sh → 마지막 줄의 --dart-define 들(VISIT_A 만 쓴다)
// 권한(실행마다 바로 앞에 — `flutter drive` 가 끝날 때 앱을 지워 권한도 사라진다). 시스템 권한 창은 흐름이
// 누를 수 없다. 음성 인식은 simctl privacy 가 지원하지 않는 서비스라 TCC 데이터베이스에 직접 넣는다:
//   xcrun simctl privacy <기기> grant microphone com.chagocnote.app
//   sqlite3 ~/Library/Developer/CoreSimulator/Devices/<기기>/data/Library/TCC/TCC.db \
//     "INSERT OR REPLACE INTO access (service, client, client_type, auth_value, auth_reason, auth_version, flags) \
//      VALUES ('kTCCServiceSpeechRecognition','com.chagocnote.app',0,2,4,1,0)"
//   xcrun simctl spawn <기기> launchctl kickstart -k system/com.apple.tccd
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/dictation_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/speech_recognizer.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_mic_button.dart';
import 'package:chagocnote/design/widgets/dictation_text_editing_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import '../test/support/upload_fakes.dart';
import 'flow_kit.dart';

const visitA = int.fromEnvironment('VISIT_A');
const ownerName = String.fromEnvironment('OWNER');

/// 인식기 자리 — [target] 으로 넘긴다. 기록 화면을 열기 전에 바꾸면 그 화면은 새 인식기를 쓴다.
class SwitchRecognizer implements SpeechRecognizer {
  SpeechRecognizer target = ChannelSpeechRecognizer();

  @override
  Future<SpeechAvailability> availability() => target.availability();

  @override
  Future<SpeechPermission> requestPermission() => target.requestPermission();

  @override
  Stream<SpeechEvent> get events => target.events;

  @override
  Future<void> start({String locale = 'ko-KR'}) => target.start(locale: locale);

  @override
  Future<void> stop() => target.stop();

  @override
  Future<void> cancel() => target.cancel();

  @override
  Future<void> openSettings() => target.openSettings();
}

final careMic = find.byWidgetPredicate(
  (w) =>
      w is AppMicButton &&
      w.semanticLabel == '${AppStrings.careNoteLabel} ${AppStrings.micLabel}',
);

bool get careListening => t.widget<AppMicButton>(careMic).listening;

Future<void> waitListening(bool listening) async {
  final end = DateTime.now().add(const Duration(seconds: 20));
  while (careListening != listening) {
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('케어 메모 마이크가 listening=$listening 이 되지 않았다');
    }
    await pumpFor(const Duration(milliseconds: 100));
  }
}

String describe(SpeechEvent e) => switch (e) {
  SpeechPartial(:final text) => 'partial "$text"',
  SpeechFinal(:final text) => 'final "$text"',
  SpeechEnded() => 'ended',
  SpeechError(:final code) => 'error ${code.name}',
};

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('④-3b 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    final recognizer = SwitchRecognizer();
    await t.pumpWidget(
      buildRoot(
        overrides: [speechRecognizerProvider.overrideWithValue(recognizer)],
      ),
    );
    final end = DateTime.now().add(const Duration(seconds: 40));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 100));
      drain();
      if (find.byKey(ScreenKeys.login).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.home).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.shopSelect).evaluate().isNotEmpty) {
        break;
      }
    }
    if (find.byKey(ScreenKeys.login).evaluate().isEmpty) await logout();
    await login(ownerName);

    await step('1', '실제 채널 — 권한을 넘어 시작까지 가고, 시뮬레이터 인식기가 미지원으로 끝나면 안내가 뜬다', () async {
      final availability = await recognizer.availability();
      note(
        'availability supported=${availability.supported} reason=${availability.reason?.name}',
      );
      router.push('/visits/$visitA/record');
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await pumpFor(const Duration(seconds: 1));
      await shot('01a-record');
      final events = <String>[];
      final sub = recognizer.events.listen((e) => events.add(describe(e)));
      await tap(careMic);
      // 시작이 곧바로 실패하면 듣는 중 상태가 한 프레임도 안 남을 수 있다 — 이벤트가 오기를 기다린다.
      final deadline = DateTime.now().add(const Duration(seconds: 20));
      while (events.isEmpty && DateTime.now().isBefore(deadline)) {
        await pumpFor(const Duration(milliseconds: 100));
      }
      await pumpFor(const Duration(milliseconds: 500));
      note('탭 뒤 네이티브 이벤트 $events');
      soft(events.isNotEmpty, '20초 안에 네이티브 이벤트가 없다(권한 창에서 멈췄을 수 있다)');
      if (events.contains('error unsupported')) {
        await shot('01b-unsupported');
        soft(
          find.text(AppStrings.dictationUnsupported).evaluate().isNotEmpty,
          '미지원 안내 스낵바가 없다',
        );
        soft(!careListening, '미지원으로 끝났는데 듣는 중이다');
      } else {
        // 인식이 실제로 시작된 기기 — 무음 10초 뒤 스스로 끝나는지 본다.
        await shot('01b-listening');
        final started = DateTime.now();
        while (careListening &&
            DateTime.now().difference(started) < const Duration(seconds: 16)) {
          await pumpFor(const Duration(milliseconds: 200));
        }
        note('듣기 끝까지 ${DateTime.now().difference(started).inMilliseconds}ms, 이벤트 $events');
        await shot('01c-ended');
        soft(!careListening, '16초가 지나도 듣고 있다');
      }
      soft(fieldText('careNote').isEmpty, '메모가 비어 있지 않다: "${fieldText('careNote')}"');
      soft(
        find.text(AppStrings.dictationDenied).evaluate().isEmpty,
        '권한 안내가 떴다 — 권한을 미리 주지 못했다',
      );
      await sub.cancel();
      router.go('/home');
      await pumpFor(const Duration(seconds: 1));
    });

    await step('2', '받아쓴 글이 커서 자리에 들어가고 저장된다(인식기 대역)', () async {
      final speech = FakeSpeechRecognizer();
      recognizer.target = speech;
      await openVisit(visitA);
      await tap(btn(AppStrings.actionComplete));
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await pumpFor(const Duration(seconds: 1));
      await tap(careMic);
      await waitListening(true);
      soft(speech.starts.length == 1, 'start 가 한 번이 아니다(${speech.starts})');
      speech.emitPartial('안녕');
      await pumpFor(const Duration(milliseconds: 300));
      final care =
          t.widget<TextField>(find.byKey(const ValueKey('careNote'))).controller!
              as DictationTextEditingController;
      soft(fieldText('careNote') == '안녕', 'partial 이 들어가지 않았다');
      soft(care.pending != null, 'partial 이 회색 구간이 아니다');
      await shot('02a-partial-gray');
      speech.emitFinal('안녕하세요');
      await pumpFor(const Duration(milliseconds: 300));
      soft(fieldText('careNote') == '안녕하세요', 'final 이 굳지 않았다');
      soft(care.pending == null, 'final 뒤에도 회색 구간이 남았다');
      await tap(careMic);
      await waitListening(false);
      soft(speech.stops == 1, 'stop 이 한 번이 아니다(${speech.stops})');
      await shot('02b-final');
      FocusManager.instance.primaryFocus?.unfocus();
      await pumpFor(const Duration(milliseconds: 600));
      await tap(btn(AppStrings.completeWithRecord));
      await waitFor(find.text(AppStrings.completeTitle));
      await tap(btn(AppStrings.close));
      await waitFor(find.text('안녕하세요'));
      await shot('02c-detail-care');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
```

`app/test/features/visit/screens/goldens/record_screen.png`: 골든 이미지 — 이 문서에 넣지 않는다. 이 작업의 골든 테스트를 `--update-goldens`로 돌려 만들고 눈으로 본다(의도한 변경).

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s test/features/visit/screens/record_screen_test.dart`
Expected: 컴파일 실패 — `AppStrings.dictation*`·`setup.speech` 가 없다.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/screens/record_screen.dart`:

```diff
@@ -1,3 +1,5 @@
+import 'dart:async';
+
 import 'package:flutter/material.dart';
 import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
@@ -6,19 +8,25 @@ import 'package:go_router/go_router.dart';
 import '../../../core/error/api_exception.dart';
 import '../../../core/error/async_body.dart';
 import '../../../core/error/error_messages.dart';
+import '../../../core/proxy/speech_recognizer.dart';
 import '../../../core/router/screen_keys.dart';
 import '../../../design/app_theme.dart';
+import '../../../design/tokens/app_colors.dart';
 import '../../../design/tokens/app_spacing.dart';
 import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
 import '../../../design/widgets/app_choice_chip.dart';
+import '../../../design/widgets/app_mic_button.dart';
+import '../../../design/widgets/app_snack_bar.dart';
+import '../../../design/widgets/dictation_text_editing_controller.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/shop_selection.dart';
 import '../../customer/state/customer_input.dart';
 import '../api/record_models.dart';
 import '../api/visit_models.dart';
+import '../state/dictation.dart';
 import '../state/record_rules.dart';
 import '../state/visit_commands.dart';
 import '../state/visit_providers.dart';
@@ -31,6 +39,9 @@ import 'visit_labels.dart';
 /// [completing]이면 저장 버튼이 "완료하기"(기록 저장 → 같은 묶음 완료)이고 맨 아래 "나중에 적고 완료"가
 /// 있다. 완료했으면 `true`로 닫힌다 — 부른 화면이 다음 예약 시트를 띄운다.
 ///
+/// 케어 메모·내부 메모는 제목 줄의 마이크로 받아쓴다(④-3b). 한 번에 한 칸만 듣고, 다른 칸으로 옮기거나
+/// 화면을 나가거나 앱이 뒤로 가면 듣던 것을 `cancel` 한다(회색 글은 굳혀 둔다).
+///
 /// 올리는 중이어도 저장을 막지 않는다. 저장은 이미 붙은 사진만 보내고 남은 사진은 대기열이 덧붙인다.
 /// 그 사이 붙은 사진 때문에 버전이 어긋나면(409) 다시 읽어 새 사진만 더하고 한 번 더 보낸다(설계 8절).
 class RecordScreen extends ConsumerStatefulWidget {
@@ -51,8 +62,16 @@ class _RecordScreenState extends ConsumerState<RecordScreen> {
   bool _started = false;
   final _weight = TextEditingController();
   final _total = TextEditingController();
-  final _careNote = TextEditingController();
-  final _internalNote = TextEditingController();
+  final _careNote = DictationTextEditingController();
+  final _internalNote = DictationTextEditingController();
+  final _careFocus = FocusNode();
+  final _internalFocus = FocusNode();
+  late final Dictation _careDictation;
+  late final Dictation _internalDictation;
+  late final AppLifecycleListener _lifecycle;
+
+  /// 칸마다 마지막으로 스낵바에 띄운 오류 — 알림이 거듭 와도 한 번만 띄운다.
+  final _shownErrors = <Dictation, SpeechErrorCode>{};
 
   /// 고른 메뉴(고른 순서)와 메뉴마다의 금액 칸.
   final _lines = <({int menuId, String name})>[];
@@ -74,8 +93,49 @@ class _RecordScreenState extends ConsumerState<RecordScreen> {
 
   int? get _shopId => ref.read(selectedShopIdProvider);
 
+  List<Dictation> get _dictations => [_careDictation, _internalDictation];
+
+  @override
+  void initState() {
+    super.initState();
+    final recognizer = ref.read(speechRecognizerProvider);
+    Dictation dictation(DictationTextEditingController controller) =>
+        Dictation(
+          recognizer: recognizer,
+          controller: controller,
+          maxLength: maxNoteLength,
+        );
+    _careDictation = dictation(_careNote);
+    _internalDictation = dictation(_internalNote);
+    for (final (d, focus) in [
+      (_careDictation, _careFocus),
+      (_internalDictation, _internalFocus),
+    ]) {
+      d.addListener(() => _showError(d));
+      // 다른 칸을 눌러 포커스가 옮겨 가면 끝낸다. stop 이 아니라 cancel 인 까닭: stop 뒤 네이티브의 늦은
+      // 결과가 곧 시작할 다른 칸에 섞일 수 있다.
+      focus.addListener(() {
+        if (!focus.hasFocus) unawaited(d.cancel());
+      });
+    }
+    _lifecycle = AppLifecycleListener(onHide: _cancelDictations);
+  }
+
+  void _cancelDictations() {
+    for (final d in _dictations) {
+      unawaited(d.cancel());
+    }
+  }
+
   @override
   void dispose() {
+    _lifecycle.dispose();
+    _cancelDictations();
+    for (final d in _dictations) {
+      d.dispose();
+    }
+    _careFocus.dispose();
+    _internalFocus.dispose();
     for (final c in [
       _weight,
       _total,
@@ -88,6 +148,57 @@ class _RecordScreenState extends ConsumerState<RecordScreen> {
     super.dispose();
   }
 
+  /// 마이크 — 듣는 중이면 끝내고, 아니면 다른 칸을 끝낸 뒤 지원·권한을 확인하고 이 칸에서 듣는다.
+  Future<void> _toggleDictation(Dictation dictation, FocusNode focus) async {
+    if (dictation.listening) return dictation.stop();
+    for (final other in _dictations) {
+      if (other != dictation) await other.cancel();
+    }
+    final recognizer = ref.read(speechRecognizerProvider);
+    final availability = await recognizer.availability();
+    if (!mounted) return;
+    if (!availability.supported) {
+      return AppSnackBar.show(context, AppStrings.dictationUnsupported);
+    }
+    final permission = await recognizer.requestPermission();
+    if (!mounted) return;
+    if (permission == SpeechPermission.denied) return _showDenied();
+    focus.requestFocus();
+    await dictation.start();
+  }
+
+  void _showDenied() => AppSnackBar.show(
+    context,
+    AppStrings.dictationDenied,
+    action: SnackBarAction(
+      label: AppStrings.openSettings,
+      textColor: AppColors.white,
+      onPressed: () =>
+          unawaited(ref.read(speechRecognizerProvider).openSettings()),
+    ),
+  );
+
+  /// 세션을 끝낸 오류를 알린다. 새로 시작하면 오류가 비워져 다음 오류는 다시 띄운다.
+  void _showError(Dictation dictation) {
+    final error = dictation.lastError;
+    if (error == null) {
+      _shownErrors.remove(dictation);
+      return;
+    }
+    if (!mounted || _shownErrors[dictation] == error) return;
+    _shownErrors[dictation] = error;
+    switch (error) {
+      case SpeechErrorCode.denied:
+        _showDenied();
+      case SpeechErrorCode.unsupported:
+        AppSnackBar.show(context, AppStrings.dictationUnsupported);
+      case SpeechErrorCode.noSpeech:
+        AppSnackBar.show(context, AppStrings.dictationNoSpeech);
+      case SpeechErrorCode.failed:
+        AppSnackBar.show(context, AppStrings.dictationFailed);
+    }
+  }
+
   /// 처음 한 번 폼을 채운다(설계 10.1 ④의 미리 채움 — `recordFormStart`).
   void _start(VisitDetail detail, List<Menu> menus) {
     final start = recordFormStart(detail, menus);
@@ -337,6 +448,16 @@ class _RecordScreenState extends ConsumerState<RecordScreen> {
     );
   }
 
+  Widget _mic(String label, Dictation dictation, FocusNode focus) =>
+      ListenableBuilder(
+        listenable: dictation,
+        builder: (_, _) => AppMicButton(
+          listening: dictation.listening,
+          semanticLabel: '$label ${AppStrings.micLabel}',
+          onTap: () => unawaited(_toggleDictation(dictation, focus)),
+        ),
+      );
+
   Widget _form(VisitDetail detail, List<Menu> menus) {
     final visit = detail.visit;
     final selected = {for (final l in _lines) l.menuId};
@@ -478,9 +599,15 @@ class _RecordScreenState extends ConsumerState<RecordScreen> {
         ),
         _Section(
           label: AppStrings.careNoteLabel,
+          trailing: _mic(
+            AppStrings.careNoteLabel,
+            _careDictation,
+            _careFocus,
+          ),
           child: TextField(
             key: const ValueKey('careNote'),
             controller: _careNote,
+            focusNode: _careFocus,
             maxLines: null,
             inputFormatters: [LengthLimitingTextInputFormatter(maxNoteLength)],
             decoration: const InputDecoration(
@@ -490,9 +617,15 @@ class _RecordScreenState extends ConsumerState<RecordScreen> {
         ),
         _Section(
           label: AppStrings.internalNoteLabel,
+          trailing: _mic(
+            AppStrings.internalNoteLabel,
+            _internalDictation,
+            _internalFocus,
+          ),
           child: TextField(
             key: const ValueKey('internalNote'),
             controller: _internalNote,
+            focusNode: _internalFocus,
             maxLines: null,
             inputFormatters: [LengthLimitingTextInputFormatter(maxNoteLength)],
             decoration: const InputDecoration(
@@ -531,11 +664,14 @@ class _Invalid implements Exception {
 }
 
 class _Section extends StatelessWidget {
-  const _Section({required this.label, required this.child});
+  const _Section({required this.label, required this.child, this.trailing});
 
   final String label;
   final Widget child;
 
+  /// 제목 줄 오른쪽(마이크).
+  final Widget? trailing;
+
   @override
   Widget build(BuildContext context) => Padding(
     padding: const EdgeInsets.only(bottom: AppSpacing.sm),
@@ -545,7 +681,15 @@ class _Section extends StatelessWidget {
         child: Column(
           crossAxisAlignment: CrossAxisAlignment.start,
           children: [
-            Text(label, style: AppTypography.caption),
+            if (trailing == null)
+              Text(label, style: AppTypography.caption)
+            else
+              Row(
+                children: [
+                  Expanded(child: Text(label, style: AppTypography.caption)),
+                  trailing!,
+                ],
+              ),
             const SizedBox(height: AppSpacing.xs),
             child,
           ],
```

`app/lib/l10n/app_strings.dart`:

```diff
@@ -405,6 +405,14 @@ class AppStrings {
   static const completeWithoutRecord = '나중에 적고 완료';
   static const amountHint = '금액';
 
+  // 말로 기록하기(④-3b).
+  static const micLabel = '말해서 적기';
+  static const dictationUnsupported = '이 기기는 한국어 받아쓰기를 지원하지 않아요. 키보드의 🎤 를 써 보세요.';
+  static const dictationDenied = '마이크와 음성 인식 권한이 필요해요.';
+  static const dictationNoSpeech = '못 알아들었어요. 다시 말해 주세요.';
+  static const dictationFailed = '받아쓰기를 이어가지 못했어요.';
+  static const openSettings = '설정 열기';
+
   static const todayCareLabel = '오늘의 케어';
   static const editRecord = '기록 수정';
   static const writeRecord = '기록 쓰기';
```

`app/lib/design/widgets/app_snack_bar.dart`:

```diff
@@ -11,7 +11,8 @@ import '../tokens/app_typography.dart';
 /// 그 아래 화면 위에 남는다. 확인이 필요한 일에는 시트를 쓴다 — 이것은
 /// 답을 받지 않는 알림이다.
 abstract final class AppSnackBar {
-  static void show(BuildContext context, String text) {
+  /// [action]은 알림에서 바로 할 일 하나("설정 열기").
+  static void show(BuildContext context, String text, {SnackBarAction? action}) {
     ScaffoldMessenger.of(context)
       ..hideCurrentSnackBar()
       ..showSnackBar(
@@ -32,6 +33,7 @@ abstract final class AppSnackBar {
             borderRadius: BorderRadius.circular(AppRadius.md),
           ),
           duration: const Duration(seconds: 3),
+          action: action,
         ),
       );
   }
```

`app/ios/Runner/Info.plist`:

```diff
@@ -47,7 +47,7 @@
 	<key>NSCameraUsageDescription</key>
 	<string>미용 전후 사진을 찍어 기록에 붙여요.</string>
 	<key>NSMicrophoneUsageDescription</key>
-	<string>영상을 찍을 때 소리를 함께 담아요.</string>
+	<string>영상을 찍을 때 소리를 담고, 말해서 메모를 적을 때 목소리를 들어요.</string>
 	<key>NSPhotoLibraryAddUsageDescription</key>
 	<string>미용 기록의 원본 사진을 앨범에 저장해요.</string>
 	<key>NSPhotoLibraryUsageDescription</key>
```

`app/CLAUDE.md`:

```diff
@@ -8,10 +8,11 @@
 - 폴더는 `lib/core/{config,proxy,storage,router,error,time,plugs}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
 - **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`의 `buildRoot`가 채운다(지금은 반려동물 상세의 [기록] 탭 `petRecordsPlugProvider` ← visit 의 `PetRecordsView`, 그 탭을 다시 읽는 `petRecordsRefreshPlugProvider` ← `petRecordsRefresher`). 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
 - **매장 범위 화면**은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다. `auth/state/shop_selection.dart`의 파생 프로바이더(`selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider`·`shopCountProvider`·`currentUserIdProvider`)만 watch 한다. 매장 선택 전(account·auth 화면: 로그인·스플래시·초대·매장 선택·계정)은 세션 전체를 봐야 하므로 이 규칙 밖이다.
-- 플러그인은 `lib/core/proxy/`의 프로바이더로만 부른다 — 클립보드 `clipboardProvider`, 사진 고르기·찍기 `mediaPickerProvider`, 렌디션(리사이즈·EXIF 제거) `photoRenditionMakerProvider`, 인터넷 복귀 신호 `networkWatcherProvider`, 업로드 폴더 `uploadsDirProvider`, 서명 URL 사진 보이기와 원본 받기 `mediaImagesProvider`, 앨범에 저장 `photoAlbumProvider`(확장자 `.mp4`면 영상으로), 영상 고르기·찍기 `MediaPicker.pickVideo`·`takeVideo(maxSeconds:)`, 영상 압축·포스터 `videoTranscoderProvider`(네이티브 `ios/Runner/VideoTranscoder.swift`·`android/app/src/main/kotlin/com/chagocnote/chagocnote/VideoTranscoder.kt` — 채널 `chagocnote/video_transcoder`의 `transcode({source, outDir, maxSeconds})` → `{video, thumb, width, height, durationSeconds, trimmed}`, `cancel()`, 실패 코드 `UNSUPPORTED`·`TOO_SHORT`·`CANCELLED`, 진행률은 이벤트 채널로 0…1), 영상 재생 `videoPlaybackFactoryProvider`(재생 추상 `VideoPlayback`은 `design/widgets/video_playback.dart`, 구현은 `core/proxy/video_playback.dart`), 큰 파일(영상 원본) 임시 받기 `mediaFilesProvider`(마이크·음성은 ④-3). 화면은 `Clipboard`·`ImagePicker`·`Image.network`를 직접 부르지 않는다. **화면(`lib/features`)과 모양 위젯(`lib/design`)은 플러그인 패키지를 직접 import 하지 않고, 모양 위젯은 `core`를 import 하지 않는다**(`test/design/plugin_imports_test.dart` — 방향은 core → design 하나). 테스트는 프로바이더를 override 한다(`test/support/upload_fakes.dart`). 서명 URL 업로드는 `core/proxy/upload_client.dart`(인증 헤더 없음·진행률·재시도 없음)로 하고, 사용자가 취소한 업로드는 `ApiException`의 `CANCELLED`라 문구를 띄우지 않는다.
+- 플러그인은 `lib/core/proxy/`의 프로바이더로만 부른다 — 클립보드 `clipboardProvider`, 사진 고르기·찍기 `mediaPickerProvider`, 렌디션(리사이즈·EXIF 제거) `photoRenditionMakerProvider`, 인터넷 복귀 신호 `networkWatcherProvider`, 업로드 폴더 `uploadsDirProvider`, 서명 URL 사진 보이기와 원본 받기 `mediaImagesProvider`, 앨범에 저장 `photoAlbumProvider`(확장자 `.mp4`면 영상으로), 영상 고르기·찍기 `MediaPicker.pickVideo`·`takeVideo(maxSeconds:)`, 영상 압축·포스터 `videoTranscoderProvider`(네이티브 `ios/Runner/VideoTranscoder.swift`·`android/app/src/main/kotlin/com/chagocnote/chagocnote/VideoTranscoder.kt` — 채널 `chagocnote/video_transcoder`의 `transcode({source, outDir, maxSeconds})` → `{video, thumb, width, height, durationSeconds, trimmed}`, `cancel()`, 실패 코드 `UNSUPPORTED`·`TOO_SHORT`·`CANCELLED`, 진행률은 이벤트 채널로 0…1), 영상 재생 `videoPlaybackFactoryProvider`(재생 추상 `VideoPlayback`은 `design/widgets/video_playback.dart`, 구현은 `core/proxy/video_playback.dart`), 큰 파일(영상 원본) 임시 받기 `mediaFilesProvider`, 음성 인식 `speechRecognizerProvider`(네이티브 `ios/Runner/SpeechRecognizer.swift`·`android/app/src/main/kotlin/com/chagocnote/chagocnote/SpeechRecognizer.kt` — 채널 `chagocnote/speech`의 `availability()` → `{supported, reason: device|locale}`, `requestPermission()` → `granted|denied`(마이크·음성 인식 둘 다), `start({locale})`·`stop()`·`cancel()`·`openSettings()`, 이벤트 채널 `chagocnote/speech/events`로 `{type: partial|final|ended|error, text?, code?}` — 오류 코드 `denied`·`unsupported`·`noSpeech`·`failed`, 시작 전 실패도 `error`+`ended` 이벤트로 온다). 화면은 `Clipboard`·`ImagePicker`·`Image.network`를 직접 부르지 않는다. **화면(`lib/features`)과 모양 위젯(`lib/design`)은 플러그인 패키지를 직접 import 하지 않고, 모양 위젯은 `core`를 import 하지 않는다**(`test/design/plugin_imports_test.dart` — 방향은 core → design 하나). 테스트는 프로바이더를 override 한다(`test/support/upload_fakes.dart`). 서명 URL 업로드는 `core/proxy/upload_client.dart`(인증 헤더 없음·진행률·재시도 없음)로 하고, 사용자가 취소한 업로드는 `ApiException`의 `CANCELLED`라 문구를 띄우지 않는다.
 - **서버에서 읽는 화면 본문은 `core/error/async_body.dart`의 `AsyncBody`로 그린다**(`test/design/async_body_usage_test.dart`). 불러오는 중·처음 실패(원인 문구와 [다시 시도], 권한·없음은 뒤로 갈 수 있으면 [돌아가기])·받은 데이터 위 띠·인터넷 복귀 때 스스로 다시 불러오기·`onRefresh`의 당겨서 새로고침을 한 곳에서 한다. 화면은 `AppErrorRetry`의 가운데·inline 모양을 직접 만들지 않는다(한 줄 `AppErrorRetry.row`는 다음 쪽 실패 같은 좁은 자리에만). 오류 문구는 누른 일이면 `messageFor`, 화면을 불러오지 못했으면 `loadMessageFor`(원인은 `core/error/error_kind.dart`의 `kindOf`). 앱 문구는 해요체다(`test/design/copy_tone_test.dart`).
 - **사진 올리기는 업로드 대기열(`features/visit/state/upload_queue.dart`)로만 한다.** 화면은 `uploadQueueProvider.notifier`의 `addPhotos`·`remove`·`retry`만 부르고, 다시 해도 안 되는 실패(`stopsUpload`)로 멈춘 항목은 스스로 다시 하지 않는다 — 사용자가 [다시 시도]하거나 [올리기 취소]한다. 대기 중인 사진은 `visitUploadsProvider(visitId)`로 본다. 대기열이 발급 → 올리기 셋 → 확인 → 덧붙이기를 하고 기기에 남긴다(설계 10.2). 기록 전체 교체(`saveRecord`)는 이미 붙은 사진만 보낸다 — 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 새 사진을 더해 한 번 더 보낸다(`record_screen.dart`).
 - **영상은 대기열의 `addVideo`로 넣는다**(④-3a). 네이티브가 1080p(짧은 변 1080·긴 변 1920 안, 키우지 않음) H.264·AAC mp4 와 1초 지점 포스터(긴 변 300)를 만들고, 60초가 넘으면 **앞 60초만** 올린다 — `addVideo`의 반환값 `VideoAddOutcome.trimmed`로 화면이 한 번 안내한다(대기열 항목에 `trimmed` 칸은 없다). 압축은 **한 번에 하나**(뒤 것은 차례를 기다린다), 한도는 사진 30장·영상 3편을 따로 센다. 크게 보기의 재생은 서명 URL 을 그대로 스트리밍하고 **기기에 캐시하지 않는다**. 원본 저장은 mp4 를 임시 파일로 받아 앨범에 넣고 지운다.
+- **말로 기록하기는 기록 화면의 케어 메모·내부 메모에만 있다**(④-3b). 칸 제목 줄의 마이크(`AppMicButton`)가 토글이고, 인식은 **기기 안에서만**(iOS `requiresOnDeviceRecognition`, 안드로이드 API 31+ `createOnDeviceSpeechRecognizer`) **한국어(`ko-KR`)**로 한다 — 온디바이스가 안 되는 기기는 미지원 안내만 하고 서버 인식으로 넘어가지 않는다. 받아쓰기 세션(`features/visit/state/dictation.dart`의 `Dictation`)이 커서 자리에 넣는다: 진행 중 구간은 회색(`DictationTextEditingController`), 확정되면 검게 굳고 구절 사이에 띄어쓰기 하나. **무음 10초는 Dart 가 잰다**(네이티브가 먼저 끝내면 10초 안에서는 다시 시작해 이어 듣는다). 손으로 고치거나 길이 상한에 닿으면 끝낸다. **한 번에 한 칸만 듣는다** — 다른 칸의 마이크·다른 칸 포커스·화면 나감·앱이 뒤로 감은 듣던 세션을 `stop`이 아니라 `cancel`한다(stop 뒤 네이티브의 늦은 결과가 다음 칸에 섞이지 않게, 회색 글은 굳혀 둔다). 미지원·권한 거부([설정 열기])·못 알아들음·실패는 스낵바로 알린다.
 - **사진을 보이는 순서는 대표 규칙이다**(`features/visit/state/photo_edits.dart`의 `galleryOrder` — 후 → 전 → 영상, 첫 장이 대표). 크게 보기의 전/후 바꾸기·대표로·삭제는 `applyPhotoEdit` + `recordInputOf`로 기록 전체 교체 한 번이고, 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 같은 바꾸기를 한 번 더 보낸다.
 - 글래스는 떠 있는 조작 계층에만 쓴다(`test/design/glass_boundary_test.dart`). 예외는 피드 카드의 이름 카드 하나(④ 설계 10.1 ②) — 실제 글래스는 비쳐 보이므로 그 위 글자는 잉크색으로 쓴다.
 - 서버의 상태 문자열은 `fromJson`에서 enum(`VisitStatus`·`VisitAction`)으로 한 번만 바꾼다. 화면의 `switch`는 `_ =>` 폴백 없이 완전 열거한다 — 상태·행동을 더하면 컴파일러가 빠진 곳을 찾는다.
```

`_docs/harness.md`:

```diff
@@ -25,7 +25,7 @@
 | 앱 구조 테스트 (기능 폴더 import 방향·라우터 가드 전수) | `flutter test test/design/feature_imports_test.dart test/core/router/app_router_test.dart` (`app/`에서. 전체 테스트에 포함되지만 구조를 건드린 변경은 이 둘을 먼저 돌린다) |
 | 앱 골든 갱신 | `flutter test --update-goldens` (`app/`에서, 의도해서 바꿀 때만) |
 | 앱 개발용 실행 | `app/tool/run_dev.sh` (백엔드를 `infra/`에서 먼저 띄운 뒤) |
-| 앱 흐름 확인 (시뮬레이터 + 실서버) | `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/<파일> -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 …` (`app/`에서. 파일 머리 주석에 준비와 추가 `--dart-define`이 있다 — `visit_flow_test.dart`(③-A2), `draft_flow_test.dart`(③-A3 카톡 초안), `record_flow_test.dart`(④-2a 사진·기록·완료 — 준비는 `infra/`에서 `bash ../app/tool/prepare_record_flow.sh`, 실행마다 새로), `photo_flow_test.dart`(④-2b 넘기기·크게 보기·원본 저장·피드·달력·고객 탭 사진 — 준비는 같은 스크립트, 그리고 실행마다 바로 앞에 `xcrun simctl privacy <기기> grant photos-add com.chagocnote.app`: `flutter drive`가 끝날 때 앱을 지워 권한도 사라진다), `error_flow_test.dart`(오류 화면 다듬기 — 띠·처음 실패 문구·인터넷 복귀·대기열 멈춤, 준비는 같은 스크립트), `video_flow_test.dart`(④-3a 영상 — 5초 압축·올리기, 65초 앞 60초 자르기, 크게 보기 재생·원본 저장, 방문당 3편 한도, 회전 메타 세로, 준비는 같은 스크립트, 그리고 표본 폴더 `--dart-define=VIDEO_ASSETS=<절대 경로>/app/integration_test/assets` — 시뮬레이터는 맥 파일을 그대로 읽는다. 에뮬레이터는 맥 파일을 못 읽으니 먼저 `adb push integration_test/assets/. /data/local/tmp/vflow/` 하고 `VIDEO_ASSETS=/data/local/tmp/vflow`를 준다. 앨범 저장은 흐름이 대역으로 바꿔 권한이 필요 없다)). 공용 도구는 `integration_test/flow_kit.dart`. 안드로이드 에뮬레이터는 `-d emulator-5554`로 같은 명령을 쓰되, 먼저 `adb reverse tcp:8080 tcp:8080`과 `adb reverse tcp:9010 tcp:9010`(에뮬레이터 안의 127.0.0.1 을 맥의 게이트웨이·MinIO 로)을 한다 — 앨범 권한은 API 29 넘으면 필요 없다. zsh 에서 준비 결과를 변수로 받으면 `${=D}`로 펼친다 — 그냥 `$D`는 한 인자로 넘어가 `--dart-define`이 비는다 |
+| 앱 흐름 확인 (시뮬레이터 + 실서버) | `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/<파일> -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 …` (`app/`에서. 파일 머리 주석에 준비와 추가 `--dart-define`이 있다 — `visit_flow_test.dart`(③-A2), `draft_flow_test.dart`(③-A3 카톡 초안), `record_flow_test.dart`(④-2a 사진·기록·완료 — 준비는 `infra/`에서 `bash ../app/tool/prepare_record_flow.sh`, 실행마다 새로), `photo_flow_test.dart`(④-2b 넘기기·크게 보기·원본 저장·피드·달력·고객 탭 사진 — 준비는 같은 스크립트, 그리고 실행마다 바로 앞에 `xcrun simctl privacy <기기> grant photos-add com.chagocnote.app`: `flutter drive`가 끝날 때 앱을 지워 권한도 사라진다), `error_flow_test.dart`(오류 화면 다듬기 — 띠·처음 실패 문구·인터넷 복귀·대기열 멈춤, 준비는 같은 스크립트), `video_flow_test.dart`(④-3a 영상 — 5초 압축·올리기, 65초 앞 60초 자르기, 크게 보기 재생·원본 저장, 방문당 3편 한도, 회전 메타 세로, 준비는 같은 스크립트, 그리고 표본 폴더 `--dart-define=VIDEO_ASSETS=<절대 경로>/app/integration_test/assets` — 시뮬레이터는 맥 파일을 그대로 읽는다. 에뮬레이터는 맥 파일을 못 읽으니 먼저 `adb push integration_test/assets/. /data/local/tmp/vflow/` 하고 `VIDEO_ASSETS=/data/local/tmp/vflow`를 준다. 앨범 저장은 흐름이 대역으로 바꿔 권한이 필요 없다), `dictation_flow_test.dart`(④-3b 말로 기록하기 — iOS 시뮬레이터. 확인 1은 실제 음성 인식 채널: 시뮬레이터는 availability 는 지원이라 답하지만 시작하면 곧바로 `unsupported`로 끝나 미지원 안내가 뜨는 경로, 확인 2는 인식기 대역으로 커서 자리 받아쓰기·저장·상세. 준비는 같은 스크립트, 그리고 실행마다 바로 앞에 `xcrun simctl privacy <기기> grant microphone com.chagocnote.app` + 음성 인식은 simctl 이 지원하지 않아 시뮬레이터 `data/Library/TCC/TCC.db`의 `access`에 `kTCCServiceSpeechRecognition` 행을 넣고 `launchctl kickstart -k system/com.apple.tccd` — 명령은 파일 머리 주석. 시스템 권한 창이 남아 있으면 스크린샷이 하얗게 찍히니 시뮬레이터를 다시 켠다)). 공용 도구는 `integration_test/flow_kit.dart`. 안드로이드 에뮬레이터는 `-d emulator-5554`로 같은 명령을 쓰되, 먼저 `adb reverse tcp:8080 tcp:8080`과 `adb reverse tcp:9010 tcp:9010`(에뮬레이터 안의 127.0.0.1 을 맥의 게이트웨이·MinIO 로)을 한다 — 앨범 권한은 API 29 넘으면 필요 없다. zsh 에서 준비 결과를 변수로 받으면 `${=D}`로 펼친다 — 그냥 `$D`는 한 인자로 넘어가 `--dart-define`이 비는다 |
 | 공유 받기 확인 | 실기기에서 카톡 [공유] → 차곡노트 (시뮬레이터엔 카톡이 없고 App Group 은 서명이 있어야 붙는다) |
 
 - 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 쓴다. 개발 데이터를 건드리지 않는다. pytest가 세션마다 한 번 `scripts/prepare_test_db.py`를 돌려 스키마를 비우고 `alembic upgrade head`로 다시 만든다. 테스트 사이에는 시드 표(`roles`, `permissions`, `role_permissions`, `pet_condition_types`)와 마이그레이션 버전 표(`alembic_version`)를 뺀 모든 표를 비운다.
```

`_docs/decisions/007-record-media.md`:

```diff
@@ -232,3 +232,38 @@
 - 포스터 크기가 플랫폼마다 1px 다르다(iOS 168×300, 안드로이드 169×300 — 반올림).
 - 크게 보기의 삭제 단추는 영상에서도 "사진 삭제"다.
 - **참조 트리와 다르게 간 것(최종 검토에서 고침).** ① 안드로이드 `VideoTranscoder.kt` — 포스터를 만드는 사이 취소되고 다음 압축이 시작되면 앞 작업의 늦은 완료가 새 요청의 결과로 답하던 경쟁을 압축마다 올리는 세대 정수로 막았다. 같은 파일에서 `DefaultEncoderFactory` 에 비트레이트(`가로×세로×30×0.12`, 1~8Mbps)를 요청해 크기가 안 바뀌는 H.264 원본이 재인코딩 없이 원본 비트레이트 그대로 복사(트랜스먹싱, 촬영본 15~20Mbps → 60초 100MB+)되던 것을 막았다. 안드로이드는 목표 비트레이트 VBR 이고 iOS 프리셋은 품질 VBR 이라 정지 화면 같은 단순 영상에서는 크기가 열 배까지 벌어진다(Media3 1.11 은 CQ 모드가 없다) — 실제 촬영본에서는 둘 다 7~10Mbps 급이다. 출력은 픽셀로 세로가 아니라 1920×1080 + 회전 메타다(Media3 기본, iOS 도 같은 모양) — 재생기·서버·포스터 모두 회전을 반영하며, 회전 메타를 무시하는 도구에서만 눕는다. ② `core/proxy/video_playback.dart` — 초기화가 끝난 뒤 스트리밍 중 오류(연결 끊김·URL 만료)는 `video_player` 가 던지지 않고 `VideoPlayerValue.errorDescription` 에 두므로 `state` 가 `hasError` 를 먼저 봐서 문구와 [다시 시도]가 나오게 했고, 다시 여는 도중(옛 컨트롤러 dispose 사이) 페이지가 사라지면 새 컨트롤러를 만들지 않는다. 만료 문구는 "다시 시도해 주세요" 다 — 자동으로 다시 읽지 않는다. ③ `record_screen_test.dart` — 회색 항목은 `IgnorePointer` 안 단추가 아니라 겉의 `Pressable` 을 눌러 hit test 경고를 없앴다. 압축 중 기록 화면을 나가면 자르기·실패 안내는 뜨지 않는다(`addVideo` 결과를 화면이 받아 띄우므로). 대기열은 압축 성공을 저장한 뒤에도 항목이 그새 빠졌으면 취소로 본다.
+
+## ④-3b 말로 기록하기에서 정한 것
+
+설계는 `docs/superpowers/specs/2026-09-26-dictation-design.md`다. 서버는 바꾸지 않았고, 앱만 바꿨다.
+
+### 설계와 다르게 간 것
+
+- **듣는 중 표시는 붉은 점이 아니라 잉크색 점이다**(설계 2·3.3). `AppColors`에 붉은·오류 토큰이 없고 팔레트 밖 색을 들이지 않는다(테마의 `error`도 잉크). 붉은색이 필요하면 토큰부터 정한다.
+- **띄어쓰기는 한 세션 안 구절 사이에만 넣는다.** 세션의 첫 구간은 사용자가 둔 커서 자리에 그대로 붙인다("앞|뒤" → "앞안녕뒤"). 설계 문구 "구절 사이"를 따랐다.
+- **시작 전 실패(미지원·권한·오디오 세션·입력 장치)도 오류 이벤트다.** 네이티브는 `start`에서 `FlutterError`를 던지지 않고 `error{code}` + `ended`를 보낸다(두 플랫폼). Dart 의 `PlatformException` 매핑은 쓰이지 않는 방어가 됐다.
+- **`denied`는 오류 코드가 아니라 지금 권한 상태로 판정한다.** 오류가 오면 마이크·음성 인식 중 하나라도 허용이 아니면 `denied`. iOS `kAFAssistantErrorDomain` 1101 은 온디바이스 쪽 취소·내부 오류에도 찍혀 `failed`로 둔다. 1110 → `noSpeech`, `kLSRErrorDomain` 201·300 → `unsupported`(실기기에서 코드 값을 확인하지 못했다).
+- **`stop` 뒤 오는 오류·빈 결과는 `ended`만 보낸다.** Dart 는 끝난 세션의 `final`·`ended`를 버린다(`stop`이 이미 회색 글을 굳혔다). `final` 없이 `ended`가 오면 회색을 굳히고 이어 듣는다.
+- **한 칸을 끝내고 다른 칸을 시작할 때는 `stop`이 아니라 `cancel`이다**(설계 3.2 는 "첫째를 stop"). 모든 세션이 같은 이벤트 흐름을 들으므로 앞 칸의 늦은 `final`·`ended`가 뒤 칸에 섞일 수 있다. `cancel`은 회색 글을 굳혀 두고 네이티브는 이벤트 없이 끝난다. 앞 칸의 `cancel`은 뒤 칸의 `start`보다 먼저 부른다(늦으면 뒤 칸의 네이티브 세션을 끊는다). 다른 칸을 눌러 포커스가 옮겨 가도 `cancel`이다.
+- **시뮬레이터 흐름이 보는 범위가 바뀌었다**(설계 3.6·5). Xcode 27 시뮬레이터는 availability 에 ko-KR 온디바이스 지원(`supported=true`)이라 답한다. 권한은 simctl(마이크)과 시뮬레이터 TCC 데이터베이스(음성 인식 — simctl 이 지원하지 않는 서비스)로 미리 줄 수 있어 권한 창 없이 `start`까지 가지만, 인식기가 곧바로 `error unsupported` + `ended`로 끝난다(오디오 엔진이 0.1초 켜졌다 멈춤). 그래서 흐름 확인 1은 "실제 채널로 시작까지 가고 미지원 안내가 뜬다"이고, 받아쓰기 삽입·저장은 인식기 대역(확인 2)으로 본다. 안드로이드 에뮬레이터(API 37)는 온디바이스 서비스는 있으나 한국어 모델이 없어 availability 가 `locale`이다.
+- **음성 인식 권한 창의 OS 고정 문구가 "음성 데이터가 Apple에 전송됩니다"라고 쓴다.** `requiresOnDeviceRecognition`과 무관하게 OS 가 붙이고, 같은 창에 우리 문구 "말한 것을 기기 안에서 글로 바꿔 메모에 넣어요."가 함께 보인다. 우리가 고칠 수 없다.
+- **마이크 권한 문구를 영상·받아쓰기 둘 다 덮게 고쳤다**: "영상을 찍을 때 소리를 담고, 말해서 메모를 적을 때 목소리를 들어요."
+- `AppSnackBar.show`에 `action`(`SnackBarAction`) 인자를 더했다 — 권한 거부 안내의 [설정 열기]. 액션이 있는 스낵바는 Flutter 기본대로 닫을 때까지 남는다(`persist`).
+
+### 이 계획에서 새로 정한 것
+
+- **키보드 받아쓰기로만 두지 않고 앱 안 마이크를 뒀다.** 키보드의 🎤 는 iOS·안드로이드 모두 서버 인식일 수 있고 우리가 막을 수 없다. 보호자 이름·반려동물 상태 같은 말이 매장 밖 서버로 나가지 않게 하려면 앱이 인식기를 직접 잡아 온디바이스를 강제해야 한다. 미지원 기기에서는 안내 문구가 키보드의 🎤 를 권한다(그 선택은 사용자 몫).
+- **온디바이스 강제의 대가**: iOS 는 온디바이스 한국어 모델이 있는 기기, 안드로이드는 API 31+ 이면서 한국어 온디바이스 모델이 깔린 기기만 된다(33+ 는 `installedOnDeviceLanguages`로 미리 알고, 31~32 는 누른 뒤에야 `unsupported`로 안다). 미지원 기기에서도 버튼은 보이고 누르면 이유를 안내한다.
+- **토글·무음 10초·Dart 가 재는 무음.** 누르고 있는 방식 대신 토글이다(미용 중 손이 바쁘다). 네이티브의 자체 종료 기준(안드로이드 몇 초, iOS 약 1분 세션)이 달라 무음은 Dart 가 마지막 결과 뒤 10초로 재고, 그 안에 네이티브가 끝내면 다시 시작해 이어 듣는다 — 두 플랫폼의 체감이 같다.
+- **자체 네이티브 채널**(`chagocnote/speech`). `speech_to_text` 패키지는 안드로이드에서 온디바이스 인식을 보장할 수 없다(`createOnDeviceSpeechRecognizer`를 쓰지 않는다). 영상 압축과 같은 틀(메서드 + 이벤트 채널, `core/proxy` 프로바이더, 테스트 대역)이다.
+- **진행 중 구간은 회색**(`DictationTextEditingController.buildTextSpan`, `AppColors.secondary`)이고 확정되면 검게 굳는다. `TextField`는 그대로 쓴다.
+- 화면이 사라질 때(`dispose`)와 앱이 뒤로 갈 때(`AppLifecycleListener.onHide`)도 `cancel`한다. 오류 스낵바는 칸마다 마지막으로 띄운 오류를 기억해 한 번만 띄운다.
+
+### 남는 것 — 알고 미룬다
+
+- **실기기 인식률** — 매장 소음·드라이어 소리 속 한국어 온디바이스 인식이 쓸 만한지 모른다. 시뮬레이터·에뮬레이터 모두 실제 `partial`·`final`을 한 번도 받지 못했다.
+- **iOS 1분 세션 이어 듣기**, `stop` 뒤 끝 콜백이 안 올 때(Dart 는 기다리지 않는다) — 실기기에서 본다.
+- **오디오 인터럽션**(전화·다른 앱 소리)과 라우트 변경은 `ended`로 끝나는 것까지만 짰다. 실기에서 보지 못했다.
+- **권한 창 순서** — iOS 는 음성 인식 창과 마이크 창이 차례로 뜬다. 한 번 거부하면 창 없이 `denied`이고 [설정 열기]로만 돌아온다. 헤드리스 시뮬레이터에서는 시스템 창을 누를 수 없어 순서를 보지 못했다(흐름은 권한을 미리 준다).
+- **안드로이드 한국어 모델 내려받기 안내**는 하지 않는다(설정 → 음성 인식 언어 팩을 사용자가 알아서). 31~32 는 누른 뒤에야 미지원을 안다.
+- **문장 부호·음성 명령**("줄바꿈")·다른 언어·녹음 보관은 하지 않는다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test --timeout 60s --update-goldens test/features/visit/screens/record_screen_test.dart` → `goldens/record_screen.png` 갱신(마이크 둘). 눈으로 본다.

Run (`app/`): `flutter test --timeout 60s test/features/visit/screens/record_screen_test.dart test/design/copy_tone_test.dart test/design/plugin_imports_test.dart` → 통과

Run (`app/`): `flutter analyze` → `No issues found!`

Run (`app/`): `flutter test --timeout 60s` → 773 passed(골든 포함, `git status`에 `test/**/failures/`가 없다)

- [ ] **Step 5: 시뮬레이터 흐름을 돌린다**

Run: `xcrun simctl privacy <UDID> grant microphone com.chagocnote.app`, 그리고 `sqlite3 ~/Library/Developer/CoreSimulator/Devices/<UDID>/data/Library/TCC/TCC.db` 에 `kTCCServiceSpeechRecognition`/`com.chagocnote.app` 행을 `auth_value 2` 로 넣고(`.schema access` 로 컬럼 확인) `xcrun simctl spawn <UDID> launchctl kickstart -k system/com.apple.tccd` — 하네스의 "앱 흐름 확인" 행에 적힌 대로.

Run (`infra/`): `D=$(bash ../app/tool/prepare_record_flow.sh | tail -1)`(실행마다 새로)

Run (`app/`): `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/dictation_flow_test.dart -d <UDID> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 ${=D}` → `PASS 1`·`PASS 2`, `All tests passed.` 스크린샷 5장을 눈으로 본다. 하얗게 찍히면 시뮬레이터를 껐다 켜고 다시.

- [ ] **Step 6: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_toggleDictation` 에서 앞 칸 `cancel` 제거 → `record_screen_test.dart::듣는 중에 내부 메모의 마이크를 누르면 앞 것이 끝나고 뒤 것이 시작한다` 실패(대역의 `calls` 차례).
- `availability` 확인 제거 → `::지원하지 않는 기기면 안내 스낵바가 뜨고 시작하지 않는다` 실패.
- [설정 열기] 액션 제거 → `::권한을 거부하면 안내와 [설정 열기]가 뜨고 누르면 설정을 연다` 실패.
- `dispose` 의 `cancel` 제거 → `::포커스를 잃었다는 알림 없이 화면이 사라져도 cancel 한다` 실패(pop 테스트는 포커스 리스너가 대신 cancel 해 못 잡는다).

- [ ] **Step 7: 커밋한다**

```bash
git add -A
git commit -m "feat(app): 기록 화면 말로 기록하기 — 메모 칸의 마이크, 미지원·권한·인식 실패 안내, 시뮬레이터 흐름, 앱 규칙·하네스·결정 기록 007

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---
