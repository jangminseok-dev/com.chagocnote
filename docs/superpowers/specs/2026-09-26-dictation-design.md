# 차곡노트 — ④-3b 말로 기록하기 설계

- 작성일: 2026-09-26
- 상태: 사용자 검토 대기
- 범위: Flutter 앱만. 기록 화면의 케어 메모·내부 메모에 마이크 버튼을 두고 기기 안(온디바이스) 음성 인식으로 커서 자리에 받아쓴다. 서버·API 는 바꾸지 않는다.
- 앞선 문서: `docs/superpowers/specs/2026-09-24-record-media-design.md` 11절(말로 기록하기), `docs/superpowers/specs/2026-09-26-video-design.md`(자체 네이티브 채널의 틀), `_docs/decisions/007-record-media.md`
- 다음 단계: 이 문서가 승인되면 구현 계획 하나를 쓴다(참조 트리에서 먼저 검증).

---

## 1. 목표

지금 기록 화면의 케어 메모·내부 메모는 평범한 `TextField` 둘이다. 앱에 음성 인식 플러그인·권한 문자열이 없다(`NSMicrophoneUsageDescription`·`RECORD_AUDIO` 는 ④-3a 가 넣었다).

이 문서가 끝나면:

1. 두 메모 칸에 마이크 버튼이 있고, 누르면 커서 자리에 받아쓴 글이 실시간으로 들어간다. 사람이 고친 뒤 저장한다.
2. 인식은 **기기 안에서만** 한다(iOS `requiresOnDeviceRecognition`, Android `createOnDeviceSpeechRecognizer`). 음성은 우리 서버로도, 애플·구글 서버로도 나가지 않는다.
3. 지원하지 않는 기기·언어, 권한 거부, 인식 실패는 문구로 안내하고 손 입력(또는 키보드 받아쓰기)으로 이어진다.

사용자가 정한 것(2026-09-26): 키보드 받아쓰기만으로 두지 않고 앱 안 버튼을 둔다(C — 온디바이스 강제), 토글 조작(A), 무음 **10초**면 끝, 미지원·거부 때도 버튼은 보이고 누르면 이유를 안내(A), 자체 네이티브 채널(A — 패키지로는 안드로이드 온디바이스를 보장할 수 없다).

## 2. 사용자 흐름

- 케어 메모·내부 메모 칸의 제목 줄 오른쪽에 마이크 버튼(`AppMicButton`)이 하나씩 있다. 다른 화면(초안·예약 폼)은 손대지 않는다.
- 누르면 듣기 시작. 버튼은 "듣는 중"(붉은 점 깜빡임)으로 바뀌고, 인식 중인 글이 **그 칸의 커서 자리**에 회색으로 실시간으로 나타난다. 한 구절이 확정되면 검게 굳고 커서가 그 뒤로 간다. 다음 구절은 이어 붙는다.
- 끝나는 조건: 버튼을 다시 누름 / 마지막 인식 뒤 무음 10초 / 그 칸에 손으로 타이핑하거나 다른 칸을 누름. 어느 경우든 확정된 글은 남고 회색 글은 마지막 결과로 굳는다.
- 한 번에 한 칸만 듣는다. 다른 칸의 마이크를 누르면 앞 것이 끝나고 뒤 것이 시작한다.
- 메모 길이 상한(`maxNoteLength`)을 넘으면 넘는 부분은 넣지 않고 끝낸다.
- 한국어 고정(`ko-KR`).
- 저장은 지금과 같다(사용자가 고친 뒤 [완료하기]/[저장]).

**하지 않는 것**: 문장 부호 자동 삽입, 음성 명령("줄바꿈"), 다른 언어, 녹음 파일 보관, 초안·예약 폼의 마이크, LLM 분리(⑨ 이후).

## 3. 플러그 자리와 네이티브

### 3.1 Dart — `core/proxy/speech_recognizer.dart`

```dart
enum SpeechUnsupported { device, locale }
class SpeechAvailability { final bool supported; final SpeechUnsupported? reason; }
enum SpeechPermission { granted, denied }
sealed class SpeechEvent {}                       // SpeechPartial(text) · SpeechFinal(text) · SpeechEnded() · SpeechError(code)
enum SpeechErrorCode { denied, unsupported, noSpeech, failed }

abstract class SpeechRecognizer {
  Future<SpeechAvailability> availability();
  Future<SpeechPermission> requestPermission();   // 마이크 + 음성 인식 둘 다
  Stream<SpeechEvent> get events;
  Future<void> start({String locale = 'ko-KR'});
  Future<void> stop();                            // 마지막 결과를 확정하고 끝
  Future<void> cancel();                          // 결과 없이 끝
  Future<void> openSettings();
}
```

- 실제 구현 `ChannelSpeechRecognizer`: 메서드 채널 `chagocnote/speech`(`availability`·`requestPermission`·`start{locale}`·`stop`·`cancel`·`openSettings`), 이벤트 채널 `chagocnote/speech/events`(`{type: partial|final|ended|error, text?, code?}`). 프로바이더 `speechRecognizerProvider` 로만 노출. `MissingPluginException` 은 `unsupported`.
- 테스트 대역 `FakeSpeechRecognizer`(`test/support/`): 가용성·권한·이벤트를 마음대로 흘리고 호출을 기록한다.

### 3.2 Dart — 받아쓰기 세션 `features/visit/state/dictation.dart`

- `Dictation` 은 `SpeechRecognizer` 와 그 칸의 `DictationTextEditingController` 를 받아 상태(`idle`·`listening`)를 알린다(`ChangeNotifier`).
- `start()`: 커서 위치를 "진행 중 구간"의 시작으로 잡는다. `SpeechPartial` 이 오면 그 구간을 새 글로 갈아 끼운다. `SpeechFinal` 이 오면 굳히고(회색 해제) 커서를 그 뒤로 옮기며 다음 구간을 그 뒤에서 연다. 구절 사이에 띄어쓰기 하나를 넣는다(앞 글자가 공백·줄바꿈이 아니면).
- **무음 10초는 Dart 가 잰다** — 마지막 `partial`/`final` 이후 10초 타이머. 네이티브가 제 기준으로 먼저 `SpeechEnded` 를 보내면(안드로이드는 몇 초, iOS 는 약 1분 세션) 10초 안이면 `start()` 를 다시 불러 이어 듣고, 넘었으면 끝낸다. 두 플랫폼의 체감이 같아진다.
- 끝(`stop`): 회색 구간을 마지막 결과로 굳힌다. `cancel`(화면을 나감·앱이 뒤로 감): 회색 구간을 굳혀 두고 끝낸다(잃지 않는다).
- 사용자가 손으로 고치면(우리가 넣은 변경이 아닌 텍스트 변화) 끝낸다.
- 길이 상한: 넣을 글이 `maxNoteLength` 를 넘으면 상한까지 잘라 넣고 끝낸다.
- `DictationTextEditingController extends TextEditingController` 가 `buildTextSpan` 을 덮어써 진행 중 구간만 회색(`AppColors` 토큰)으로 그린다. `TextField` 은 그대로다.
- 기록 화면은 칸마다 `Dictation` 을 하나씩 들고, 한 번에 하나만 `listening` 이게 한다(둘째를 시작하면 첫째를 `stop`).

### 3.3 모양 위젯 — `design/widgets/app_mic_button.dart`

`AppMicButton({required bool listening, required VoidCallback onTap})`. 듣는 중이면 붉은 점이 깜빡인다(`AnimationController`, 골든은 정지 프레임). Riverpod 모름.

### 3.4 iOS — `ios/Runner/SpeechRecognizer.swift`

- `SFSpeechRecognizer(locale: ko-KR)`. `availability`: 인식기가 없으면 `locale`, `supportsOnDeviceRecognition == false` 면 `device`.
- `requestPermission`: `SFSpeechRecognizer.requestAuthorization` + `AVAudioSession.requestRecordPermission` 둘 다 허용이어야 `granted`.
- `start`: `AVAudioSession`(`.record`, `.measurement`) → `AVAudioEngine` 입력 탭 → `SFSpeechAudioBufferRecognitionRequest` 에 `requiresOnDeviceRecognition = true`, `shouldReportPartialResults = true`. 결과 콜백에서 `partial`(`bestTranscription.formattedString`)·`final`(`isFinal`), 오류는 코드 매핑(권한 → `denied`, 언어·기기 → `unsupported`, 아무 말 없음 → `noSpeech`, 그 밖 → `failed`). iOS 가 세션을 끝내면(약 1분) `ended`.
- 인터럽션(전화 등)·오디오 라우트 변경은 `ended`.
- `stop`: 오디오 탭을 떼고 `endAudio()` → 마지막 `final` 뒤 `ended`. `cancel`: `task.cancel()`.
- `openSettings`: `UIApplication.openSettingsURLString`.
- `Info.plist`: `NSSpeechRecognitionUsageDescription`(해요체) 추가.

### 3.5 Android — `SpeechRecognizer.kt`

- API 31+ 만 지원: `SpeechRecognizer.isOnDeviceRecognitionAvailable(context)` 가 참이어야 하고 `createOnDeviceSpeechRecognizer(context)` 로 만든다(온디바이스 보장). API 33+ 는 `checkRecognitionSupport(intent)` 로 `ko-KR` 이 `supportedOnDeviceLanguages` 에 있는지 본다(`installedOnDeviceLanguages` 에 없고 다운로드 가능이면 `locale` 미지원으로 안내 — 모델 내려받기 유도는 하지 않는다). 31~32 는 시작 뒤 `ERROR_LANGUAGE_NOT_SUPPORTED`/`ERROR_LANGUAGE_UNAVAILABLE` 로 `unsupported`. 30 이하는 `device`.
- `requestPermission`: `RECORD_AUDIO` 런타임 권한(Activity 의 `requestPermissions` 결과를 채널로).
- `start`: `RecognizerIntent.ACTION_RECOGNIZE_SPEECH`, `EXTRA_LANGUAGE ko-KR`, `EXTRA_PARTIAL_RESULTS true`, `EXTRA_LANGUAGE_MODEL LANGUAGE_MODEL_FREE_FORM`. `RecognitionListener`: `onPartialResults` → `partial`, `onResults` → `final` + `ended`, `onError` 매핑(`NO_MATCH`·`SPEECH_TIMEOUT` → `noSpeech`, `INSUFFICIENT_PERMISSIONS` → `denied`, 언어 오류 → `unsupported`, 그 밖 → `failed`) 뒤 `ended`.
- `stop`: `stopListening()`. `cancel`: `cancel()`. `openSettings`: `ACTION_APPLICATION_DETAILS_SETTINGS`.
- 메인 스레드에서 만들고 부른다. `RECORD_AUDIO` 는 이미 있다.

### 3.6 규칙

- 화면·모양 위젯은 채널·플러그인을 모른다(`test/design/plugin_imports_test.dart`). `design` 은 `core` 를 import 하지 않는다.
- 네이티브는 단위 테스트가 없다. 시뮬레이터는 온디바이스 인식이 없어 "지원 안 함" 경로만 실제 채널로 확인된다.

## 4. 오류와 경계

| 상황 | 동작 |
|---|---|
| 기기·언어 미지원 | 누르면 스낵바 "이 기기는 한국어 받아쓰기를 지원하지 않아요. 키보드의 🎤 를 써 보세요." 버튼은 그대로. |
| 권한 거부 | 스낵바 "마이크와 음성 인식 권한이 필요해요." + [설정 열기]. |
| `noSpeech` | 스낵바 "못 알아들었어요. 다시 말해 주세요." 넣은 글 없음. |
| `failed` | 스낵바 "받아쓰기를 이어가지 못했어요." 확정된 글은 남음. |
| 무음 10초 | 조용히 끝. 회색 글은 굳음. |
| 네이티브 `ended`(iOS 1분·안드로이드 자체 종료) | 10초 안이면 이어 듣고, 넘었으면 끝. |
| 손 타이핑·다른 칸 | 끝. 확정된 글은 남음. |
| 길이 상한 | 상한까지 넣고 끝(문구 없음). |
| 화면 나감·앱 뒤로 감 | `cancel`. 회색 글은 굳혀 둠. |
| 오디오 인터럽션 | `ended` → 위 규칙. |

문구는 전부 해요체이고 `app_strings.dart` 에 둔다(`copy_tone_test`). 서버는 바꾸지 않는다.

## 5. 검증

- **단위(`FakeSpeechRecognizer`, `fakeAsync`)** — `Dictation`: 커서 자리에 partial 갈아 끼우기·final 굳히기, 두 구절 연속(띄어쓰기), 커서가 중간일 때 삽입, 손 타이핑으로 종료, 무음 10초 종료, 네이티브 `ended` 뒤 10초 안 재시작·넘으면 종료, 길이 상한, 한 번에 한 칸, `cancel` 때 굳힘, 오류 코드별 상태. `DictationTextEditingController` 의 회색 구간.
- **채널** — `ChannelSpeechRecognizer` 의 메서드·이벤트·오류 매핑(영상 채널 테스트와 같은 방식).
- **위젯** — 기록 화면에 마이크 둘, 누르면 듣는 중·partial 회색, 미지원·권한 거부·`noSpeech` 스낵바, [설정 열기] 호출. 골든 `app_mic_button.png` 하나(두 상태).
- **구조** — `plugin_imports_test`(새 채널 파일 포함), `copy_tone_test`.
- **시뮬레이터 흐름** — 실제 채널로 `availability()` 가 "지원 안 함"을 돌려주고 스낵바가 뜨는 것만(iOS). 안드로이드 에뮬레이터는 온디바이스 모델이 있으면 실제 인식을 한 번 시도, 없으면 같은 경로.
- **실기기 미확인(알고 미룬다)** — 실제 인식률, iOS 1분 세션 이어 듣기, 인터럽션, 권한 창 순서, 안드로이드 모델 내려받기 안내.

## 6. 문서

- `app/CLAUDE.md`: 플러그 자리에 `speechRecognizerProvider`, 네이티브 파일 위치, 받아쓰기 규칙(온디바이스만·한국어·토글·10초).
- `_docs/harness.md`: 흐름 행에 확인 범위("지원 안 함" 경로) 한 줄.
- `_docs/decisions/007-record-media.md`: "④-3b 말로 기록하기에서 정한 것" — 키보드 받아쓰기 대신 앱 버튼을 둔 이유, 온디바이스 강제와 대가(미지원 기기), 토글·10초, 자체 네이티브(패키지는 안드로이드 온디바이스 보장 불가), 미룬 것.

## 7. 이번에 하지 않는 것

문장 부호·명령어, 다른 언어, 녹음 보관, 다른 화면의 마이크, 안드로이드 모델 내려받기 유도, LLM 분리, 서버 변경.
