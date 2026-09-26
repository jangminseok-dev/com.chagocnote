# CLAUDE.md — 차곡노트 앱 (Flutter)

저장소 루트의 `CLAUDE.md` 를 먼저 읽는다. 여기는 앱에만 해당하는 규칙이다.

## 꼭 지킬 것

- **웹뷰 방식 금지.** 웹뷰 패키지를 넣지 않고, 어떤 화면도 인앱 웹뷰로 만들지 않는다. 소셜 로그인도 네이티브 경로다(Apple 버튼은 iOS 만).
- 폴더는 `lib/core/{config,proxy,storage,router,error,time,plugs}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
- **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`의 `buildRoot`가 채운다(지금은 반려동물 상세의 [기록] 탭 `petRecordsPlugProvider` ← visit 의 `PetRecordsView`, 그 탭을 다시 읽는 `petRecordsRefreshPlugProvider` ← `petRecordsRefresher`). 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
- **매장 범위 화면**은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다. `auth/state/shop_selection.dart`의 파생 프로바이더(`selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider`·`shopCountProvider`·`currentUserIdProvider`)만 watch 한다. 매장 선택 전(account·auth 화면: 로그인·스플래시·초대·매장 선택·계정)은 세션 전체를 봐야 하므로 이 규칙 밖이다.
- 플러그인은 `lib/core/proxy/`의 프로바이더로만 부른다 — 클립보드 `clipboardProvider`, 사진 고르기·찍기 `mediaPickerProvider`, 렌디션(리사이즈·EXIF 제거) `photoRenditionMakerProvider`, 인터넷 복귀 신호 `networkWatcherProvider`, 업로드 폴더 `uploadsDirProvider`, 서명 URL 사진 보이기와 원본 받기 `mediaImagesProvider`, 앨범에 저장 `photoAlbumProvider`(확장자 `.mp4`면 영상으로), 영상 고르기·찍기 `MediaPicker.pickVideo`·`takeVideo(maxSeconds:)`, 영상 압축·포스터 `videoTranscoderProvider`(네이티브 `ios/Runner/VideoTranscoder.swift`·`android/app/src/main/kotlin/com/chagocnote/chagocnote/VideoTranscoder.kt` — 채널 `chagocnote/video_transcoder`의 `transcode({source, outDir, maxSeconds})` → `{video, thumb, width, height, durationSeconds, trimmed}`, `cancel()`, 실패 코드 `UNSUPPORTED`·`TOO_SHORT`·`CANCELLED`, 진행률은 이벤트 채널로 0…1), 영상 재생 `videoPlaybackFactoryProvider`(재생 추상 `VideoPlayback`은 `design/widgets/video_playback.dart`, 구현은 `core/proxy/video_playback.dart`), 큰 파일(영상 원본) 임시 받기 `mediaFilesProvider`, 음성 인식 `speechRecognizerProvider`(네이티브 `ios/Runner/SpeechRecognizer.swift`·`android/app/src/main/kotlin/com/chagocnote/chagocnote/SpeechRecognizer.kt` — 채널 `chagocnote/speech`의 `availability()` → `{supported, reason: device|locale}`, `requestPermission()` → `granted|denied`(마이크·음성 인식 둘 다), `start({locale})`·`stop()`·`cancel()`·`openSettings()`, 이벤트 채널 `chagocnote/speech/events`로 `{type: partial|final|ended|error, text?, code?}` — 오류 코드 `denied`·`unsupported`·`noSpeech`·`failed`, 시작 전 실패도 `error`+`ended` 이벤트로 온다). 화면은 `Clipboard`·`ImagePicker`·`Image.network`를 직접 부르지 않는다. **화면(`lib/features`)과 모양 위젯(`lib/design`)은 플러그인 패키지를 직접 import 하지 않고, 모양 위젯은 `core`를 import 하지 않는다**(`test/design/plugin_imports_test.dart` — 방향은 core → design 하나). 테스트는 프로바이더를 override 한다(`test/support/upload_fakes.dart`). 서명 URL 업로드는 `core/proxy/upload_client.dart`(인증 헤더 없음·진행률·재시도 없음)로 하고, 사용자가 취소한 업로드는 `ApiException`의 `CANCELLED`라 문구를 띄우지 않는다.
- **서버에서 읽는 화면 본문은 `core/error/async_body.dart`의 `AsyncBody`로 그린다**(`test/design/async_body_usage_test.dart`). 불러오는 중·처음 실패(원인 문구와 [다시 시도], 권한·없음은 뒤로 갈 수 있으면 [돌아가기])·받은 데이터 위 띠·인터넷 복귀 때 스스로 다시 불러오기·`onRefresh`의 당겨서 새로고침을 한 곳에서 한다. 화면은 `AppErrorRetry`의 가운데·inline 모양을 직접 만들지 않는다(한 줄 `AppErrorRetry.row`는 다음 쪽 실패 같은 좁은 자리에만). 오류 문구는 누른 일이면 `messageFor`, 화면을 불러오지 못했으면 `loadMessageFor`(원인은 `core/error/error_kind.dart`의 `kindOf`). 앱 문구는 해요체다(`test/design/copy_tone_test.dart`).
- **사진 올리기는 업로드 대기열(`features/visit/state/upload_queue.dart`)로만 한다.** 화면은 `uploadQueueProvider.notifier`의 `addPhotos`·`remove`·`retry`만 부르고, 다시 해도 안 되는 실패(`stopsUpload`)로 멈춘 항목은 스스로 다시 하지 않는다 — 사용자가 [다시 시도]하거나 [올리기 취소]한다. 대기 중인 사진은 `visitUploadsProvider(visitId)`로 본다. 대기열이 발급 → 올리기 셋 → 확인 → 덧붙이기를 하고 기기에 남긴다(설계 10.2). 기록 전체 교체(`saveRecord`)는 이미 붙은 사진만 보낸다 — 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 새 사진을 더해 한 번 더 보낸다(`record_screen.dart`).
- **영상은 대기열의 `addVideo`로 넣는다**(④-3a). 네이티브가 1080p(짧은 변 1080·긴 변 1920 안, 키우지 않음) H.264·AAC mp4 와 1초 지점 포스터(긴 변 300)를 만들고, 60초가 넘으면 **앞 60초만** 올린다 — `addVideo`의 반환값 `VideoAddOutcome.trimmed`로 화면이 한 번 안내한다(대기열 항목에 `trimmed` 칸은 없다). 압축은 **한 번에 하나**(뒤 것은 차례를 기다린다), 한도는 사진 30장·영상 3편을 따로 센다. 크게 보기의 재생은 서명 URL 을 그대로 스트리밍하고 **기기에 캐시하지 않는다**. 원본 저장은 mp4 를 임시 파일로 받아 앨범에 넣고 지운다.
- **말로 기록하기는 기록 화면의 케어 메모·내부 메모에만 있다**(④-3b). 칸 제목 줄의 마이크(`AppMicButton`)가 토글이고, 인식은 **기기 안에서만**(iOS `requiresOnDeviceRecognition`, 안드로이드 API 31+ `createOnDeviceSpeechRecognizer`) **한국어(`ko-KR`)**로 한다 — 온디바이스가 안 되는 기기는 미지원 안내만 하고 서버 인식으로 넘어가지 않는다. 받아쓰기 세션(`features/visit/state/dictation.dart`의 `Dictation`)이 커서 자리에 넣는다: 진행 중 구간은 회색(`DictationTextEditingController`), 확정되면 검게 굳고 구절 사이에 띄어쓰기 하나. **무음 10초는 Dart 가 잰다**(네이티브가 먼저 끝내면 10초 안에서는 다시 시작해 이어 듣는다). 손으로 고치거나 길이 상한에 닿으면 끝낸다. **한 번에 한 칸만 듣는다** — 다른 칸의 마이크·다른 칸 포커스·화면 나감·앱이 뒤로 감은 듣던 세션을 `stop`이 아니라 `cancel`한다(stop 뒤 네이티브의 늦은 결과가 다음 칸에 섞이지 않게, 회색 글은 굳혀 둔다). 미지원·권한 거부([설정 열기])·못 알아들음·실패는 스낵바로 알린다.
- **사진을 보이는 순서는 대표 규칙이다**(`features/visit/state/photo_edits.dart`의 `galleryOrder` — 후 → 전 → 영상, 첫 장이 대표). 크게 보기의 전/후 바꾸기·대표로·삭제는 `applyPhotoEdit` + `recordInputOf`로 기록 전체 교체 한 번이고, 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 같은 바꾸기를 한 번 더 보낸다.
- 글래스는 떠 있는 조작 계층에만 쓴다(`test/design/glass_boundary_test.dart`). 예외는 피드 카드의 이름 카드 하나(④ 설계 10.1 ②) — 실제 글래스는 비쳐 보이므로 그 위 글자는 잉크색으로 쓴다.
- 서버의 상태 문자열은 `fromJson`에서 enum(`VisitStatus`·`VisitAction`)으로 한 번만 바꾼다. 화면의 `switch`는 `_ =>` 폴백 없이 완전 열거한다 — 상태·행동을 더하면 컴파일러가 빠진 곳을 찾는다.
- 서버 응답의 필드명은 변환하지 않는다. 모델은 평범한 클래스에 `fromJson` 을 직접 쓴다. 코드 생성기를 도입하지 않는다.
- `liquid_glass_widgets` 는 `lib/design/bridge/` 안에서만 import 한다. 화면은 `lib/design/widgets` 만 쓴다.
- 토큰을 로그에 남기지 않는다. `print`·`debugPrint`·dio `LogInterceptor` 를 쓰지 않는다(`avoid_print` 는 오류다).
- 리프레시 토큰 재사용에는 유예가 없다. 갱신 요청은 동시에 하나만, 실패한 갱신은 자동으로 다시 보내지 않는다. `ProviderScope` 의 `retry` 는 꺼 둔다.
- Hiss Haus 는 첫 입점 매장 이름이다. 앱 이름은 "차곡노트"다.

## 명령어 (`app/` 에서)

    flutter analyze                     # 경고 0
    flutter test                        # 골든 포함
    flutter test --update-goldens       # 골든을 의도해서 바꿀 때만
    tool/run_dev.sh                     # 개발용 실행 (APP_ENV=dev, 게이트웨이 http://127.0.0.1:8080)

## 표본 영상 (`integration_test/assets/`)

시뮬레이터 흐름 `video_flow_test.dart`가 쓴다. 맥의 ffmpeg 로 한 번 만들었다(pubspec assets 에 넣지 않는다 — 흐름이 `--dart-define=VIDEO_ASSETS=<폴더>`로 받아 복사한다).

    ffmpeg -y -f lavfi -i "smptebars=size=1080x1920:rate=30:duration=5" -f lavfi -i "sine=frequency=440:duration=5" -c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p -c:a aac -b:a 48k -movflags +faststart sample-5s-portrait.mp4
    ffmpeg -y -f lavfi -i "smptebars=size=480x270:rate=15:duration=65" -f lavfi -i "sine=frequency=330:duration=65" -c:v libx264 -preset veryfast -crf 34 -pix_fmt yuv420p -c:a aac -b:a 32k -movflags +faststart sample-65s-small.mp4
    ffmpeg -y -f lavfi -i "smptebars=size=1920x1080:rate=30:duration=4" -c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p -an landscape-4s-silent.mp4
    ffmpeg -y -display_rotation 90 -i landscape-4s-silent.mp4 -c copy sample-4s-rot90-silent.mp4   # 회전 메타만 붙인다(-metadata rotate 는 안 붙는다)
