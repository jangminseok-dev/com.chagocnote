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
