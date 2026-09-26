# 차곡노트 — ④-3a 영상 설계

- 작성일: 2026-09-26
- 상태: 승인(2026-09-26), 계획서 `docs/superpowers/plans/2026-09-26-video.md`
- 범위: Flutter 앱만. 영상 고르기·찍기, 앱 안 압축(1080p H.264·앞 60초)과 포스터, 업로드 대기열의 영상 항목, 타일·넘기기의 재생 표시, 크게 보기 재생과 원본 저장, 시뮬레이터 흐름. 서버는 바꾸지 않는다. 말로 기록하기(음성)는 ④-3b 로 뗀다.
- 앞선 문서: `docs/superpowers/specs/2026-09-24-record-media-design.md` 11절(영상)·7절(업로드)·10.2(대기열), `docs/superpowers/specs/2026-09-26-error-polish-design.md`(오류 원인·대기열 멈춤), `_docs/decisions/007-record-media.md`
- 다음 단계: 이 문서가 승인되면 구현 계획 하나를 쓴다(참조 트리에서 먼저 검증).

---

## 1. 목표

지금 앱은 영상을 받아서 보여 주기만 한다.

- 서버(④-1)는 이미 `kind: video` 를 받는다. 원본 mp4 + 썸네일 jpg 둘, 길이 1~60초, 200MB, 방문당 3편(`media_rules.py`, `visit_record_rules.py`).
- 앱(④-2b)은 상세 넘기기와 크게 보기에서 영상에 재생 아이콘을 그리지만 재생하지 못하고, 올리지도 못한다. `MediaKind.video` 와 `RecordMedia.durationSeconds` 는 이미 있다.
- 앱에 영상 압축·재생 패키지가 없고, 마이크 권한 문자열이 없다.

이 문서가 끝나면:

1. 기록 화면에서 앨범 영상을 고르거나 카메라로 60초까지 찍어 붙일 수 있다.
2. 앱이 1080p H.264 MP4 로 압축하고 포스터 한 장을 뽑아 사진과 같은 3단계(발급 → PUT → 확인 → 덧붙이기)로 올린다. 60초를 넘으면 앞 60초만 올리고 알린다.
3. 타일·넘기기에 재생 표시와 길이가 보이고, 크게 보기에서 그 자리에서 재생하며 원본 mp4 를 앨범에 저장할 수 있다.
4. 압축·포스터는 플랫폼이 유지하는 API(iOS `AVAssetExportSession`, Android `Media3 Transformer`)로 앱 안에 둔다. 외부 압축 패키지를 들이지 않는다.

**실기기가 없어 미루는 것**: 카메라 촬영·실기기 압축 시간·단일 PUT 실패율에 따른 멀티파트 판단. 코드는 넣고 확인은 8절에 적는다.

## 2. 사용자 흐름

- 기록 화면 [사진 추가] 시트가 넷이 된다: [앨범에서 사진] [사진 찍기] [앨범에서 영상] [영상 찍기]. 전/후 선택은 지금과 같다.
- 영상은 한 번에 한 편만 고른다. 고르면 타일이 바로 나오고 준비 링(압축 진행률)이 돈 뒤 사진처럼 올라간다.
- 60초를 넘는 영상은 앞 60초만 압축한다. 타일이 준비되면 스낵바 "60초까지만 올릴 수 있어 앞부분 60초를 올렸어요."
- 방문당 영상 3편. 붙은 영상 + 대기열의 영상으로 남은 수를 세고, 차면 시트 대신 한도 문구(사진 30장과 같은 방식, 따로 센다).
- 앨범의 원본 영상은 건드리지 않는다. 플러그인이 앱 임시 폴더에 준 복사본으로 압축본·포스터를 만들고, 올린 뒤 앱 폴더의 파일만 지운다(사진과 같다). 카메라로 찍은 영상도 앱 폴더에만 생기고 앨범에 자동으로 들어가지 않는다.
- 대표 사진 규칙(후 → 전 → 영상 포스터)은 서버가 정한다. 앱은 받은 순서대로 보인다.
- 영상의 [전/후 바꾸기]·[대표로]·[삭제]는 사진과 같은 코드다. 영상 편집(자르기 UI·회전)은 없다.

## 3. 압축·포스터 플러그 자리

### 3.1 Dart — `core/proxy/video_transcoder.dart`

```dart
class VideoTranscodeResult {
  final String video;      // outDir/video.mp4 — 1080p H.264·AAC, 앞 maxSeconds
  final String thumb;      // outDir/thumb.jpg — 1초 지점 프레임, 긴 변 300px(사진 썸네일과 같다)
  final int width, height; // 압축본 기준(회전 반영)
  final int durationSeconds;
  final bool trimmed;      // 원본이 maxSeconds 를 넘어 잘랐는지
}

abstract class VideoTranscoder {
  Future<VideoTranscodeResult> transcode(
    String source, Directory outDir, {
    int maxSeconds = 60,
    void Function(double)? onProgress,
  });
  Future<void> cancel();
}
```

- 실제 구현 `ChannelVideoTranscoder`: 메서드 채널 `chagocnote/video_transcoder`(`transcode`·`cancel`)와 진행률 이벤트 채널 `chagocnote/video_transcoder/progress`. 프로바이더 `videoTranscoderProvider` 로만 노출한다.
- 테스트 대역 `FakeVideoTranscoder`(`test/support/upload_fakes.dart`): 원본을 `video.mp4` 로 복사하고 작은 jpg 를 쓰며, 정해진 크기·길이·`trimmed` 를 돌려준다. 진행률을 원하는 대로 흘릴 수 있다.
- 실패는 `ApiException` 이 아닌 `VideoTranscodeException(code)` 로 던진다. 코드는 `UNSUPPORTED`(코덱·손상), `TOO_SHORT`(압축 뒤 길이 0), `CANCELLED`.
- 사진의 `PhotoRenditionMaker` 와 같은 모양이다. 화면·대기열은 이 프로바이더만 본다(`app/CLAUDE.md` 플러그인 규칙).

### 3.2 iOS — `ios/Runner/VideoTranscoder.swift`

- `AVAssetExportSession(asset:, presetName: AVAssetExportPreset1920x1080)`, `outputFileType = .mp4`, `timeRange = 0…min(길이, maxSeconds)`. 세로 영상은 프리셋이 방향을 유지한다. `shouldOptimizeForNetworkUse = true`(moov 를 앞으로 — 스트리밍 재생이 바로 시작된다).
- `AVAssetImageGenerator`(`appliesPreferredTrackTransform = true`)로 1초 지점(길이가 1초 미만이면 0초) 프레임 → JPEG, 긴 변 300px.
- 크기·길이는 압축본을 `AVAsset` 으로 다시 읽어 `naturalSize`(transform 적용)와 `duration` 에서 얻는다.
- 진행률은 `exportSession.progress` 를 0.2초마다 이벤트로. `cancel` 은 `cancelExport()`.
- `AppDelegate` 가 채널을 등록한다(공유 받기 채널과 같은 자리).

### 3.3 Android — `android/app/src/main/kotlin/.../VideoTranscoder.kt`

- Gradle 의존성 `androidx.media3:media3-transformer`·`media3-effect`·`media3-common`(앱의 첫 미디어 라이브러리 추가). `Transformer.Builder(context).setVideoMimeType(MimeTypes.VIDEO_H264).setAudioMimeType(MimeTypes.AUDIO_AAC)`, `EditedMediaItem` 에 `ClippingConfiguration(0…maxSeconds)` 와 `Presentation.createForHeight(h)` — 회전을 반영한 표시 크기에서 **짧은 변 ≤1080·긴 변 ≤1920 안으로 줄이고 키우지 않는다**(iOS 의 1920×1080 프리셋과 같은 규칙. 2026-09-26 계획에서 정정 — "긴 변 1080" 은 세로 영상을 608×1080 으로 만든다).
- `MediaMetadataRetriever` 로 1초 프레임(`getFrameAtTime`, `OPTION_CLOSEST_SYNC`)과 회전을 반영한 가로·세로·길이.
- 진행률은 `Transformer.getProgress` 를 200ms 폴링해 이벤트로. `cancel` 은 `Transformer.cancel()`.
- 에뮬레이터는 소프트웨어 인코더(`c2.android.avc.encoder`)로 돈다.

### 3.4 권한 문자열

- iOS `Info.plist`: `NSMicrophoneUsageDescription`(영상 찍기의 소리). 카메라·앨범 문자열은 이미 있다.
- Android `AndroidManifest.xml`: `CAMERA`·`RECORD_AUDIO`. 카메라 촬영은 실기기에서 못 보지만 문자열은 이번에 넣는다.

## 4. 대기열과 API

### 4.1 `UploadJob`

- 칸 셋을 더한다: `kind`(`photo`/`video`, 옛 `queue.json` 에 없으면 `photo`), `durationSeconds`(영상만), `trimmed`(앞 60초를 잘랐는지 — 앱을 다시 켜도 같은 안내를 하려고 함께 저장).
- 파일 경로 규칙은 그대로다. 사진 `original.jpg`·`display.jpg`·`thumb.jpg`, 영상 `video.mp4`·`thumb.jpg`. `displayPath` 는 영상이면 null.

### 4.2 넣기 — `addVideo`

- `addPhotos` 와 같은 순서: 타일을 먼저 만들고(`preparing`), `videoTranscoderProvider.transcode` 로 압축·포스터를 만든 뒤 `prepared` 로 바꾸고 펌프를 돌린다.
- 압축 진행률은 `progress` 칸에 흘린다(올리기 진행률과 같은 칸을 순서대로 쓴다). 준비 링이 돈다.
- `trimmed` 면 스낵바 한 번(기록 화면이 대기열의 `trimmed` 항목을 보고 띄우고 표시했다고 적는다 — 새로고침에 다시 뜨지 않는다).
- 압축이 실패하면(`UNSUPPORTED`·`TOO_SHORT`) 대기열에서 빼고 스낵바 "이 영상은 올릴 수 없어요." / "너무 짧은 영상이에요." 사진의 "읽을 수 없는 파일" 과 같은 길. `CANCELLED` 는 문구 없음.
- 압축은 한 번에 하나만 돈다. 둘을 연달아 고르면 둘째는 첫째가 끝난 뒤 시작하고 타일은 둘 다 먼저 보인다.
- 압축 중 [올리기 취소]: `cancel()` 로 네이티브 작업을 취소하고 폴더를 지운다.
- 압축 중 앱 종료: 사진과 같다. `preparing` 은 기기에 남기지 않으니 다시 켜면 타일이 없다.

### 4.3 올리기

- `_upload` 가 `kind` 로 갈린다. 영상은 `issueVideo` 로 발급받고 PUT 둘(mp4 `video/mp4`, thumb `image/jpeg`)을 동시에 보낸다. 확인·덧붙이기·실패·멈춤 판정(`stopsUpload`)·재시도·복귀·취소·세션 바뀔 때 정리는 사진과 같은 코드다.
- 200MB 초과는 서버 422(업무 4xx) → 멈춤. 느낌표 시트 문구 "영상은 200MB까지만 올릴 수 있어요.", 시트에 [올리기 취소]만(다시 해도 같다). 1080p 60초는 보통 60MB 안쪽이라 드물다.

### 4.4 API — `MediaApi.issueVideo`

```
POST /v1/shops/{shop}/media/uploads
{ "kind": "video", "content_type": "video/mp4", "byte_size", "width", "height", "duration_seconds" }
→ { media_id, puts: { original, display: null, thumb }, expires_at }
```

`puts.display` 는 이미 nullable 이다. 서버 코드는 바꾸지 않는다.

### 4.5 한도

기록 화면이 `maxVideosPerVisit = 3` 을 두고, 붙은 영상 + 대기열의 영상으로 남은 수를 센다. 사진 30장과 따로 센다.

## 5. 화면

### 5.1 모양 위젯(`design/widgets`, Riverpod 모름)

- `app_video_badge.dart` — 재생 배지와 길이 라벨("0:42"). 타일·넘기기·피드 카드가 같이 쓴다.
- `app_video_player.dart` — `AppVideoPlayer(url, poster, onError)`. `video_player`(flutter.dev 공식, iOS `AVPlayer`·Android `ExoPlayer`)로 서명 URL 원본을 바로 스트리밍한다. 기기에 캐시하지 않는다(mp4 는 수십 MB 라 파일 캐시가 금방 찬다). 조작은 위젯이 직접 그린다: 가운데 재생/일시정지, 아래 진행 막대(끌어서 이동), 남은 시간. 소리는 켠다. dispose 때 컨트롤러를 해제한다. 두 손가락 확대는 없다.
- 화면은 `video_player` 를 직접 import 하지 않는다(구조 테스트).

### 5.2 기록 화면 사진 줄(`record_photos.dart`)

- 추가 시트 네 항목. [앨범에서 영상]은 `MediaPicker.pickVideo()`(한 편), [영상 찍기]는 `MediaPicker.takeVideo(maxSeconds: 60)`. `MediaPicker` 추상에 둘을 더하고 `image_picker` 의 `pickVideo(source:, maxDuration:)` 로 구현한다.
- 대기열 타일: 영상이면 포스터 위에 배지·길이. 준비 중이면 지금의 진행 링. 멈춘 항목의 느낌표·시트는 사진과 같다.
- 붙은 영상 타일: 서버 썸네일(포스터) 위에 배지·길이(`RecordMedia.durationSeconds`).

### 5.3 상세 넘기기(`app_photo_pager.dart`)

④-2b 가 이미 영상에 재생 아이콘을 그린다. 길이 라벨만 더한다(배지 위젯으로 통일).

### 5.4 크게 보기(`photo_viewer_screen.dart`)

- 영상 페이지: 포스터 위 재생 아이콘을 누르면 그 자리에서 `AppVideoPlayer` 로 재생한다. 페이지를 넘기거나 화면을 나가면 멈추고 해제한다.
- 재생 실패(URL 만료·인터넷 없음·서버): 포스터 위 `loadMessageFor` 원인 문구와 [다시 시도]. 서명 URL 은 최대 48시간이라 만료(403)면 상세를 다시 읽어 새 URL 로 다시 연다.
- [원본 저장]: mp4 를 임시 파일로 받아(`MediaImages.fileOf` 와 같은 자리에 `MediaFiles.download`) `PhotoAlbum.save` 로 넘긴다. `save` 가 확장자를 보고 `Gal.putVideo` 로 갈린다. 진행 중·완료·권한 거부 문구는 사진과 같다.
- [전/후 바꾸기]·[대표로]·[삭제]는 사진과 같은 코드.

### 5.5 피드·달력·[기록] 탭

서버 썸네일을 그대로 쓴다. 카드에 영상이면 작은 재생 배지 하나만 더한다 — 단, 피드 API 의 `FeedItemView` 가 대표의 `kind` 를 주지 않아 **이번에는 하지 않는다**(2026-09-26 계획에서 확인, 결정 기록 007 "남는 것").

## 6. 오류와 경계

| 상황 | 동작 |
|---|---|
| 60초보다 긴 영상 | 앞 60초만 압축. 준비되면 스낵바 "60초까지만 올릴 수 있어 앞부분 60초를 올렸어요." |
| 1초 미만 | 압축 뒤 길이 0이면 빼고 "너무 짧은 영상이에요." |
| 압축 실패(손상·미지원 코덱) | 빼고 "이 영상은 올릴 수 없어요." |
| 압축 중 앱 종료 | 타일 사라짐, 다시 고른다(사진과 같음). |
| 압축 중 [올리기 취소] | 네이티브 취소 + 폴더 삭제. 문구 없음. |
| 200MB 초과 | 서버 422 → 멈춤. 시트 "영상은 200MB까지만 올릴 수 있어요." + [올리기 취소]. |
| 3편 초과 | 시트 대신 한도 문구. |
| 인터넷 없음·서버·세션 만료·잦은 시도 | 사진과 같은 재시도·복귀·멈춤 규칙. 타임아웃은 `server`(오류 화면 다듬기 후속). |
| 재생 중 URL 만료·인터넷 없음 | 포스터 위 원인 문구 + [다시 시도]. 만료면 상세 다시 읽기. |
| 원본 저장 권한 거부 | `PhotoAlbumDenied` 문구(사진과 같음). |
| 영상 삭제 | 사진과 같은 확인 시트. 서버가 원본·포스터를 지운다. |
| 셀룰러 | 묻지 않고 올린다(사진과 같음). 데이터 절약 옵션은 미룬다. |

문구는 전부 해요체이고 `app_strings.dart` 에 둔다(`copy_tone_test`).

## 7. 검증

### 7.1 단위·위젯(`FakeVideoTranscoder`)

- 대기열: 영상 넣기 → 압축 진행률이 `progress` 에 흐름 → `prepared` → `issueVideo`(`duration_seconds` 포함) → PUT 둘(mp4·thumb, `display` 없음) → 확인 → 덧붙이기 → 폴더 삭제. `trimmed` 안내 한 번, 압축 실패 시 빼기, 압축 중 취소, 앱 재시작 뒤 `kind` 없는 옛 항목은 photo, 200MB 422 멈춤과 시트에 [다시 시도] 없음, 사진·영상 한도 따로 세기, 둘을 연달아 넣으면 압축은 순서대로.
- API: `issueVideo` 요청 JSON.
- 화면: 추가 시트 네 항목, 영상 타일의 배지·길이, 크게 보기에서 재생 아이콘 → 플레이어 표시(`video_player` 의 테스트용 플랫폼 대역으로 초기화·재생 호출만 확인), 재생 실패 문구·[다시 시도], [원본 저장]이 mp4 는 `putVideo` 로 가는지, 피드 카드의 배지.
- 골든: 영상 타일(준비 중·붙은 것), 크게 보기 영상 페이지.
- 구조 테스트: 화면이 `video_player`·채널을 직접 import 하지 않는다(`core/proxy`·`design/widgets` 만). 해요체.

### 7.2 시뮬레이터 흐름(`integration_test/video_flow_test.dart`)

- 표본 영상 둘을 `integration_test/assets/` 에 둔다. ffmpeg 로 한 번 만든다(맥에 있음): 5초 세로 1080p 클립(~300KB)과 65초 저화질 클립(~400KB). 명령은 `app/CLAUDE.md` 에 적는다. 흐름의 가짜 선택기(`GeneratedPicker` 와 같은 방식)가 파일을 임시 폴더에 복사해 돌려준다.
- 확인 넷: ① 5초 영상 → 준비 링 → 올라감 → 타일에 배지·"0:05" ② 65초 영상 → 자르기 스낵바 → 서버가 받은 길이 60 ③ 크게 보기 재생 → 첫 프레임 뒤 진행 → [원본 저장] 앨범 확인 ④ 3편 한도 문구. 실제 채널(압축·포스터)과 실서버를 쓴다.
- 안드로이드 에뮬레이터에서도 한 번 돌린다(Media3 Transformer 소프트웨어 인코더).

### 7.3 실기기 미확인

카메라 촬영, 실기기 압축 시간, 단일 PUT 실패율과 멀티파트 판단. 결정 기록 007 에 적고 실기기가 생기면 본다.

## 8. 문서

- `app/CLAUDE.md`: 플러그 자리에 `videoTranscoderProvider`·`MediaPicker.pickVideo/takeVideo`, 네이티브 파일 위치, 표본 영상 ffmpeg 명령, 화면이 `video_player` 를 직접 안 쓰는 규칙.
- `_docs/harness.md`: "앱 흐름 확인"에 `video_flow_test`, 에뮬레이터 행.
- `_docs/decisions/007-record-media.md`: "④-3a 영상에서 정한 것" — 자체 네이티브를 고른 이유(`video_compress` 19개월 무갱신, `ffmpeg_kit` 중단), 60초 앞부분 자르기, 재생 캐시 안 함, 한 번에 한 편, 미룬 것(카메라·멀티파트·실기기).

## 9. 이번에 하지 않는 것

- 말로 기록하기(④-3b).
- 영상 편집 UI, 여러 편 동시 고르기, 재생 캐시, 데이터 절약 옵션, 멀티파트 업로드.
- 서버 변경.
