# ⑥-2 알림톡 앱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장이 앱에서 카카오톡 채널을 연동하고 알림톡 종류를 켜고 끄며, 방문 상세에서 발송 내역을 보고 실패한 알림을 다시 보내고, 알림장을 알림톡으로 보낸다.

**Architecture:** 알림장(⑤-3)과 같은 모양이다 — `visit/api/notification_api.dart`·`notification_models.dart`, `visit/state/notification_providers.dart`·`notification_commands.dart`, 화면 `visit/screens/settings/notification_settings_screen.dart` 하나(연동 전·후를 한 화면이 가른다)와 방문 상세의 블록 위젯, 미리보기 화면의 보내기 뒤 폴링. 백엔드는 바꾸지 않는다.

**Tech Stack:** Flutter 3.41 · Riverpod · go_router · dio. 새 플러그인·패키지 없음.

**Spec:** `docs/superpowers/specs/2026-10-14-notification-design.md` 8절·11.2(앱), 7절(API). API 의 실제 모양은 `_docs/decisions/009-notification.md` "⑥-2 앱이 기댈 API 계약"이 정본이다(설계 7절과 다르면 009 를 따른다). 앱 규칙은 `app/CLAUDE.md`.

## Global Constraints

- 주석·테스트 이름·커밋 메시지는 한국어, 화면 문구는 해요체이고 전부 `lib/l10n/app_strings.dart`에 둔다(`copy_tone_test`).
- 기능 폴더 안은 `screens/`·`state/`·`api/` 세 층뿐. 새 파일은 전부 `lib/features/visit/` 아래다. `shop` 기능의 설정 허브는 경로 글자(`/settings/notification`)로만 연다(`feature_imports_test`).
- 서버에서 읽는 화면 본문은 `AsyncBody`. 매장 범위 화면은 `selectedShopIdProvider`·`isOwnerProvider`만 watch 한다. 모든 서버 호출은 `runShopScoped`를 거친다.
- 모델은 평범한 클래스 + `fromJson`. 서버 문자열은 `fromJson`에서 enum 으로 한 번만 바꾸고 화면의 `switch`는 `_ =>` 없이 완전 열거한다.
- 설정은 [저장] 없이 누르면 바로 **아홉 칸 전체** PUT. 낙관적으로 그리지 않고 응답(다시 읽은 값)으로 그린다. 보내는 중·다시 읽는 중·읽기 실패 중에는 누름을 받지 않는다. 바꾸는 것은 사장만(`isOwnerProvider`), 직원은 읽기 전용.
- 전화번호·인증번호·`share_text`(알림장 주소가 들 수 있다)·알림장 주소를 로그·테스트 출력·스크린샷 설명에 남기지 않는다. `print`·`debugPrint` 금지. 온보딩 입력값(검색 아이디·관리자 번호·카테고리)은 화면 상태에만 두고 저장하지 않는다.
- `ReportCommands.send`와 [다시 공유]의 동작은 바꾸지 않는다. 하루 목록·피드·달력은 바꾸지 않는다.
- 검증은 `app/`에서 `flutter analyze`(경고 0)·`flutter test`. 골든은 새로 만드는 것만 `--update-goldens`로 만들고 기존 골든은 바뀌면 안 된다(방문 상세 기존 골든 셋은 빈 내역이라 그대로다).
- 커밋은 `feat/notification-6-2-app` 브랜치에 작업마다 하나. 푸시·병합은 사용자가 요청할 때.

## 이 계획이 정한 것 (설계가 비워 둔 곳)

1. **업종 카테고리는 글자 입력 칸이다**(설계 8.1 "입력 세 칸"). 실제 카카오 카테고리 코드의 모양은 실계정에서만 확인된다(009 "남는 것") — 확인되면 고르기로 바꾼다.
2. **실패 문구는 `error_kind`로만 고른다**(응답에 오류 코드가 없다): 일시 "잠시 문제가 있었어요", 영구 "알림톡을 받을 수 없는 번호예요". 설계의 예시 "카카오톡을 쓰지 않는 번호예요"는 쓰지 않는다.
3. **알림장 보내기 뒤에는 "이번 보내기가 만든 줄"만 본다.** 보내기 전에 그 방문의 `report` 줄 ID 들을 읽어 두고, 보낸 뒤 그 밖의 새 줄만 결과로 친다 — 링크를 끊고 다시 보낼 때 옛 `sent` 줄을 새 발송으로 잘못 알리지 않게. 새 줄이 `canceled`면 줄이 없는 것으로 친다(공유 시트).
4. **발송 내역은 방문 상세를 따라 다시 읽는다** — `visitNotificationsProvider`가 `visitDetailProvider`를 watch 한다. 예약 변경·취소·당겨 새로고침이 상세를 무효화하면 내역도 따라온다. `VisitCommands`·`ReportCommands`는 고치지 않는다.
5. 내역을 읽는 중이거나 읽지 못했으면 **블록을 그리지 않는다**(상세 본문을 막지 않는다).
6. **모르는 `kind`·`status` 문자열의 줄은 목록에서 뺀다**(서버가 값을 더해도 방문 상세가 죽지 않게). `canceled_reason`은 앱이 읽지 않는다.
7. [다시 보내기]·[다른 방법으로 보내기]는 **그 종류의 가장 최근 줄에만** 둔다(재발송 API 가 가장 최근 줄을 다시 보낸다).
8. 고르기 값: 리마인드 시각 08:00~21:00 30분 간격, 다음 예약 제안 "지난 방문 간격대로"(null)·2·3·4·5·6·8·10·12주, 쿨다운 14·30·60·90일. 서버 값이 목록에 없으면 그 값을 목록 맨 앞에 더해 보인다.
9. 채널이 `token_requested`인 채 화면을 다시 열면 입력 첫 단계부터다(입력값을 저장하지 않는다).
10. 발신번호 인증이 끝나면 곧바로 문자 대체를 켜는 PUT 을 한 번 보낸다(스위치를 켜려던 것이다).
11. 시뮬레이터 흐름은 매장 둘을 쓴다 — 연동 화면을 직접 밟는 새 매장(템플릿은 "심사 중"까지만 본다)과, 준비 스크립트가 연동·승인까지 끝낸 매장(발송을 본다). 앱 안에서 템플릿 승인을 당길 방법이 없다(디스패처 10분 주기 또는 `reregister_templates.py --refresh`).

## Review Focus

1. 알림장을 보낸 뒤 결과를 기다리는 10초 안에 미리보기를 뒤로 닫는다 — 예외 없이 멈추고, 닫힌 화면에 스낵바·공유 시트를 띄우지 않는다. → 작업 6.
2. 링크를 끊고 다시 보내는데 그 사이 알림장 알림톡을 꺼 두었다 — 옛 `sent` 줄이 있어도 "알림톡으로 보냈어요"가 아니라 공유 시트가 뜬다. → 작업 2·6.
3. 묶음 줄이 다른 방문으로 옮겨진 뒤(⑥-1b) 낡은 화면에서 [다시 보내기] — 404 `NOTIFICATION_MESSAGE_NOT_FOUND`를 스낵바로 알리고 블록을 다시 읽는다. → 작업 5.
4. 설정을 다시 읽는 중이거나 읽기에 실패한 화면에서 스위치를 누른다 — 요청이 나가지 않는다(낡은 값으로 아홉 칸을 덮지 않는다). → 작업 4.
5. 서버가 모르는 `kind`·`status`를 준다 — 그 줄만 빠지고 방문 상세는 그대로 보인다. → 작업 1·5.

## File Structure

| 파일 | 일 |
|---|---|
| 만듦 `app/lib/features/visit/api/notification_models.dart` | enum 과 `NotificationOverview`·`NotificationChannel`·`NotificationSettings`·`NotificationTemplate`·`NotificationMessage` |
| 만듦 `…/api/notification_api.dart` | 열 경로(`/myself` 는 부르지 않는다) |
| 만듦 `…/state/notification_providers.dart` | `notificationApiProvider`·`notificationOverviewProvider`·`visitNotificationsProvider` |
| 만듦 `…/state/notification_commands.dart` | 쓰기와 폴링(`awaitReport`·`resend`) |
| 만듦 `…/state/notification_rules.dart` | 순수 규칙 — 내역 줄 고르기·문구·고르기 값 |
| 만듦 `…/screens/settings/notification_settings_screen.dart` | 연동 전 폼·연동 후 설정·발신번호 인증 시트 |
| 만듦 `…/screens/visit_notifications_block.dart` | 방문 상세의 "알림톡" 블록 |
| 고침 `…/screens/visit_detail_screen.dart`, `…/screens/report_preview_screen.dart` | 블록 끼우기, 보내기 뒤 폴링 |
| 고침 `lib/core/router/app_router.dart`·`screen_keys.dart`, `lib/features/shop/screens/settings_screen.dart`, `lib/core/error/error_messages.dart`, `lib/l10n/app_strings.dart` | 경로·키·허브 줄·오류 문구·문구 |
| 고침 `app/test/support/visit_fixtures.dart`·`visit_test_backend.dart` | 가짜 응답과 기본 경로 |
| 만듦 `app/integration_test/notification_flow_test.dart`, `app/tool/prepare_notification_flow.sh` | 시뮬레이터 흐름 |

---

### Task 1: 모델·API·테스트 대역

**Files:**
- Create: `lib/features/visit/api/notification_models.dart`, `lib/features/visit/api/notification_api.dart`
- Modify: `lib/core/error/error_messages.dart`, `test/support/visit_fixtures.dart`, `test/support/visit_test_backend.dart`
- Test: `test/features/visit/api/notification_api_test.dart`

**Interfaces — Produces:**

```dart
enum NotificationKind { confirm, reminder, report, change, cancel, nextVisit }   // 서버 "next_visit"
enum NotificationStatus { scheduled, sending, accepted, sent, fallbackSent, failed, canceled }
enum NotificationErrorKind { transient, permanent }
enum ChannelStatus { none, tokenRequested, linked, unlinked }
enum TemplateStatus { pending, approved, rejected }

class NotificationChannel { ChannelStatus status; ShopTime? linkedAt; String? senderNumber; bool senderVerified; bool smsFallbackEnabled; }
class NotificationSettings {   // overview.settings (여덟 칸)
  bool confirmEnabled, reminderEnabled, reportEnabled, changeEnabled, nextVisitEnabled;
  String reminderTime;         // "HH:MM"
  int? nextVisitAfterWeeks; int nextVisitCooldownDays;
}
class NotificationTemplate { NotificationKind kind; TemplateStatus status; }
class NotificationOverview {
  NotificationChannel channel; NotificationSettings? settings; List<NotificationTemplate> templates;
  TemplateStatus? templateOf(NotificationKind kind);
  /// PUT 본문 아홉 칸 — settings 여덟 + channel.smsFallbackEnabled. [field] 한 칸만 [value]로 바꾼다.
  Map<String, dynamic> settingsBody({String? field, Object? value});   // settings 가 null 이면 StateError
}
class NotificationMessage {
  int messageId; NotificationKind kind; NotificationStatus status; ShopTime scheduledAt; ShopTime? sentAt;
  NotificationErrorKind? errorKind; String? shareText;
  static List<NotificationMessage> listFromJson(Map<String, dynamic> json);   // 모르는 kind·status 의 줄은 뺀다
}

class NotificationApi {
  Future<NotificationOverview> overview(int shopId);                                   // GET  /notification
  Future<void> requestChannelToken(int shopId, {required String searchId, required String adminPhone, required String categoryCode});   // POST /notification/channel/token
  Future<NotificationOverview> linkChannel(int shopId, {…위 셋, required String token});   // POST /notification/channel
  Future<void> unlinkChannel(int shopId);                                              // DELETE /notification/channel
  Future<NotificationOverview> updateSettings(int shopId, Map<String, dynamic> body);  // PUT  /notification/settings
  Future<void> requestSenderVerification(int shopId, String phone);                    // POST /notification/sender/verification
  Future<NotificationOverview> confirmSender(int shopId, {required String phone, required String code});   // POST /notification/sender
  Future<List<NotificationMessage>> forVisit(int shopId, int visitId);                 // GET  /visits/{id}/notifications
  Future<int> resend(int shopId, int visitId, NotificationKind kind);                  // POST …/{kind}/resend → message_id
  Future<NotificationMessage> message(int shopId, int messageId);                      // GET  /notifications/{id}
}
```

요청 본문의 칸 이름은 009 그대로(`search_id`·`admin_phone`·`category_code`·`token`·`phone`·`code`). `NotificationKind`에 서버 글자를 돌려주는 `wire`(`nextVisit` → `"next_visit"`)를 둔다. 템플릿의 `rejected_reason`은 읽지 않는다(009: 앱은 `status`로만 문구를 고른다).

오류 문구(`error_messages.dart`에 더한다):

| 코드 | 문구 |
|---|---|
| `NOTIFICATION_CHANNEL_NOT_LINKED` | 먼저 카카오톡 채널을 연동해 주세요. |
| `NOTIFICATION_CHANNEL_LINKED` | 이미 연동된 채널이 있어요. |
| `NOTIFICATION_TOKEN_INVALID` | 인증번호가 틀렸거나 시간이 지났어요. |
| `NOTIFICATION_SENDER_NOT_VERIFIED` | 발신번호를 먼저 인증해 주세요. |
| `NOTIFICATION_TEMPLATE_NOT_APPROVED` | 아직 심사가 끝나지 않은 알림이에요. |
| `NOTIFICATION_ALREADY_PENDING` | 이미 보내는 중이에요. |
| `NOTIFICATION_MESSAGE_NOT_FOUND` | 다시 보낼 알림을 찾지 못했어요. 화면을 새로 불러왔어요. |
| `NOTIFICATION_RATE_LIMITED` | 요청이 너무 잦아요. 잠시 뒤에 다시 해 주세요. |
| `NOTIFICATION_PROVIDER_UNAVAILABLE` | 카카오톡 연결이 잠시 원활하지 않아요. 다시 시도해 주세요. |

테스트 대역:

- `visit_fixtures.dart`: `notificationOverviewJson({String channel = 'linked', bool senderVerified = false, bool smsFallback = false, Map<String, dynamic>? settings, List<Map<String, dynamic>>? templates})`(기본: 009 의 연동 직후 값 + 템플릿 다섯 `approved`; `channel: 'none'`이면 `settings: null`·`templates: []`), `notificationSettingsJson({…})`, `notificationTemplateJson({String kind = 'confirm', String status = 'approved'})`, `notificationMessageJson({int messageId = 1, String kind = 'confirm', String status = 'sent', String? errorKind, String? shareText, String scheduledAt = '2026-10-02T14:02:00+09:00', String? sentAt})`.
- `VisitTestBackend.call`: 등록된 처리기가 없을 때 `GET /v1/shops/3/visits/<숫자>/notifications`는 `{"items": []}`로 답한다(방문 상세의 기존 테스트가 새 요청에 걸리지 않게). 그 밖은 지금처럼 `fail`.

- [ ] **Step 1: 테스트** (`report_api_test.dart`의 양식 — 가짜 어댑터로 메서드·경로·본문을 본다)
  - `overview_는_채널_설정_템플릿을_읽는다`: 기본 픽스처 → `channel.status == ChannelStatus.linked`, `settings!.reminderTime == '18:00'`, `settings!.nextVisitAfterWeeks == null`, `templateOf(NotificationKind.confirm) == TemplateStatus.approved`, `templateOf(NotificationKind.nextVisit) == null`.
  - `연동_전에는_설정이_없다`: `channel: 'none'` → `settings == null`, `templates.isEmpty`.
  - `settingsBody_는_아홉_칸이고_한_칸만_바꾼다`: `settingsBody(field: 'reminder_enabled', value: false)`의 키가 009 의 아홉 이름과 같고 그 칸만 false, `sms_fallback_enabled`는 채널 값.
  - `온보딩_요청_본문은_서버_칸_이름_그대로다`: `requestChannelToken`·`linkChannel`·`requestSenderVerification`·`confirmSender`의 메서드·경로·본문.
  - `내역은_모르는_종류와_상태의_줄을_뺀다`(Review Focus 5): `kind: 'brand_new'` 한 줄, `status: 'weird'` 한 줄, 정상 두 줄 → 길이 2.
  - `next_visit_과_fallback_sent_를_enum_으로_바꾼다`.
  - `재발송은_종류의_서버_글자로_부르고_message_id_를_돌려준다`: `POST /v1/shops/3/visits/101/notifications/next_visit/resend` → 201 `{"message_id": 9}` → 9.
  - `error_messages`: 위 아홉 코드가 표의 문구로 바뀐다(`messageFor(ApiException(code: …))`).
- [ ] **Step 2:** `flutter test test/features/visit/api/notification_api_test.dart` → 컴파일 실패.
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** 위 파일 통과, `flutter test test/features/visit` 전체 통과, `flutter analyze` 0.
- [ ] **Step 5:** 커밋 `feat(app): 알림톡 API·모델과 테스트 대역`

---

### Task 2: 상태 — 프로바이더·명령·규칙

**Files:**
- Create: `lib/features/visit/state/notification_providers.dart`, `notification_commands.dart`, `notification_rules.dart`
- Test: `test/features/visit/state/notification_commands_test.dart`, `notification_rules_test.dart`

**Interfaces — Consumes** Task 1 전부. **Produces:**

```dart
// notification_providers.dart
final notificationApiProvider = Provider<NotificationApi>(…);
final notificationOverviewProvider = FutureProvider.autoDispose.family<NotificationOverview, int>(…);        // shopId
/// 방문 상세를 따라 다시 읽는다 — 먼저 `ref.watch(visitDetailProvider(key).future)`를 기다린다.
final visitNotificationsProvider = FutureProvider.autoDispose.family<List<NotificationMessage>, VisitKey>(…);

// notification_commands.dart
sealed class ReportDelivery {}                        // 알림장 보내기 뒤 알림톡의 결과
class ReportNotSent extends ReportDelivery {}          // 이번 보내기가 만든 줄이 없다(또는 canceled) → 공유 시트
class ReportDelivered extends ReportDelivery {}        // sent·fallback_sent
class ReportFailed extends ReportDelivery { final String? shareText; }
class ReportPending extends ReportDelivery {}          // 10초가 지나도 scheduled·sending·accepted

class NotificationCommands {
  Future<void> requestChannelToken(int shopId, {required String searchId, required String adminPhone, required String categoryCode});
  Future<void> linkChannel(int shopId, {…, required String token});
  Future<void> unlinkChannel(int shopId);
  Future<void> updateSettings(int shopId, Map<String, dynamic> body);
  Future<void> requestSenderVerification(int shopId, String phone);
  Future<void> confirmSender(int shopId, {required String phone, required String code});
  /// 보내기 전에 부른다 — 그 방문의 report 줄 ID 들. 읽지 못하면 null.
  Future<Set<int>?> reportRowIds(int shopId, int visitId);
  /// [before] 밖의 가장 최근 report 줄을 1초 간격, 최대 10번 본다. [before]가 null 이면 곧바로 ReportNotSent.
  Future<ReportDelivery> awaitReport(int shopId, int visitId, {required Set<int>? before});
  /// 재발송하고 1초 간격 최대 5번 그 줄을 본다(끝난 상태면 멈춘다). 내역을 다시 읽게 한다.
  Future<void> resend(int shopId, int visitId, NotificationKind kind);
}
final notificationCommandsProvider = Provider<NotificationCommands>(…);

// notification_rules.dart
List<NotificationMessage> visibleRows(List<NotificationMessage> rows);              // canceled 를 뺀다(순서 그대로 — 서버가 최신순)
bool isLatestOfKind(List<NotificationMessage> rows, NotificationMessage row);       // 그 종류의 첫 줄인가
const reminderTimeChoices = <String>[…];   // "08:00" … "21:00" 30분 간격, 27개
const nextVisitWeekChoices = <int?>[null, 2, 3, 4, 5, 6, 8, 10, 12];
const cooldownDayChoices = <int>[14, 30, 60, 90];
List<T> withCurrent<T>(List<T> choices, T current);   // current 가 없으면 맨 앞에 더한다
```

규칙:

- 설정·온보딩·발신번호·해제 쓰기는 **성공하든 실패하든** `notificationOverviewProvider`를 무효화한다(`ReportCommands.updateSettings`와 같은 이유).
- `resend`는 POST 직후와 폴링이 끝난 뒤 `visitNotificationsProvider`를 무효화한다. POST 가 실패해도(404·409) 무효화하고 예외는 그대로 던진다.
- `awaitReport`의 읽기 한 번이 실패하면 그 회차는 건너뛴다(다음 초에 다시). 끝나면 `visitNotificationsProvider`를 무효화한다. 폴링의 읽기는 `runShopScoped`를 거친다.
- 기다림은 `Future.delayed(const Duration(seconds: 1))`. 처음 읽기는 기다리지 않고 바로 한다.

- [ ] **Step 1: 테스트** (`report_commands_test.dart`의 양식. 시간은 `fakeAsync`로 흘린다)
  - `awaitReport`: ① before 밖의 새 줄이 없다 → 요청 한 번 뒤 `ReportNotSent` ② 새 줄 `sent` → `ReportDelivered` ③ 새 줄 `fallback_sent` → `ReportDelivered` ④ `accepted` 두 번 뒤 `failed`(`share_text: '문안'`) → `ReportFailed`, `shareText == '문안'`, 요청 세 번 ⑤ 줄곧 `accepted` → 요청 열 번 뒤 `ReportPending`(10초를 넘겨 흘려도 열한 번째가 없다) ⑥ before 가 null → 요청 없이 `ReportNotSent` ⑦ **옛 `sent` 줄(before 안)만 있다 → `ReportNotSent`**(Review Focus 2) ⑧ 새 줄이 `canceled` → `ReportNotSent` ⑨ 둘째 읽기가 500 → 건너뛰고 셋째에서 `sent` → `ReportDelivered`.
  - `reportRowIds`: report 줄의 ID 만(다른 종류 제외), 읽기 실패 → null.
  - `resend`: POST 201 → `sending` → `sent`에서 멈춘다(요청 수), 다섯 번 뒤에도 `accepted`면 멈춘다, 404 면 예외가 올라오고 내역이 다시 읽힌다(Review Focus 3 — 프로바이더를 listen 해 두고 다시 읽은 횟수를 센다).
  - 쓰기 여섯: 각각 성공·실패(409) 뒤 overview 가 다시 읽힌다.
  - `visitNotificationsProvider`: `visitDetailProvider`를 무효화하면 내역도 다시 읽힌다(요청 수 2).
  - `notification_rules_test.dart`: `visibleRows`가 canceled 를 빼고 순서를 지킨다, `isLatestOfKind`(같은 종류 둘 중 첫 줄만 true), `reminderTimeChoices.length == 27`·처음 `'08:00'`·끝 `'21:00'`, `withCurrent(cooldownDayChoices, 45).first == 45`, `withCurrent(cooldownDayChoices, 30)`은 그대로.
- [ ] **Step 2:** 실패 확인. **Step 3:** 구현. **Step 4:** 두 파일과 `flutter test test/features/visit/state` 통과, analyze 0.
- [ ] **Step 5:** 커밋 `feat(app): 알림톡 상태 — 설정·온보딩 쓰기, 알림장 발송 결과 기다리기, 다시 보내기`

---

### Task 3: 설정 화면 — 경로와 연동 전

**Files:**
- Create: `lib/features/visit/screens/settings/notification_settings_screen.dart`
- Modify: `lib/core/router/app_router.dart`(`/settings/notification`), `lib/core/router/screen_keys.dart`(`ScreenKeys.notificationSettings = Key('screen_notification_settings')`), `lib/features/shop/screens/settings_screen.dart`(알림장 줄 바로 아래 "알림톡" 줄), `lib/l10n/app_strings.dart`
- Test: `test/features/visit/screens/settings/notification_settings_screen_test.dart`, `test/features/shop/screens/settings_screen_test.dart`(허브 줄), 골든 `settings/goldens/notification_settings_unlinked.png`

화면 뼈대는 `report_settings_screen.dart`와 같다(뒤로 + 제목 + `AsyncBody`, `_busy`·`_errorText`). `overview.channel.status`가 `linked`가 아니면 이 작업의 "연동 전" 본문, `linked`면 작업 4 의 본문이다.

**연동 전 본문**(사장):

- 안내 카드 세 줄(번호 1·2·3) — 아래 문구.
- 입력 셋: 키 `notification_search_id`·`notification_admin_phone`(숫자 자판)·`notification_category`. 셋 다 채워지고 관리자 번호가 `^01[0-9]{8,9}$`일 때만 [인증번호 받기]가 눌린다.
- [인증번호 받기] → `requestChannelToken` 성공 → 입력 셋을 잠그고 그 아래 6자리 칸(키 `notification_token`, 숫자 자판, 최대 6자)과 [연동하기]가 나온다. [다시 입력]으로 첫 단계로 돌아간다. [연동하기]는 6자리일 때만 눌린다.
- [연동하기] → `linkChannel` 성공 → overview 가 다시 읽혀 연동 후 본문으로 바뀐다. 실패하면 맨 위 한 줄에 `messageFor` 문구(입력은 그대로).
- 보내는 중(`_busy`)에는 단추·칸을 받지 않는다.

**직원**: 입력·단추 없이 안내 한 줄만.

문구(`AppStrings`):

| 이름 | 글 |
|---|---|
| `settingsNotification` | 알림톡 |
| `notificationSettingsTitle` | 알림톡 설정 |
| `notificationOwnerOnly` | 사장만 바꿀 수 있어요. |
| `notificationOwnerLinks` | 사장님이 연동할 수 있어요. |
| `notificationPrepareTitle` | 연동하기 전에 준비해 주세요 |
| `notificationPrepare1` | 카카오톡 채널을 만들어요. |
| `notificationPrepare2` | 채널의 비즈니스 인증을 받아요. 며칠 걸려요. |
| `notificationPrepare3` | 채널 관리자센터에서 "관리자 추가 인증"을 꺼요. |
| `notificationSearchIdLabel` / `Hint` | 채널 검색 아이디 / @로 시작하는 아이디예요. |
| `notificationAdminPhoneLabel` / `Hint` | 채널 관리자 휴대폰 번호 / 이 번호의 카카오톡으로 인증번호가 와요. |
| `notificationCategoryLabel` / `Hint` | 업종 카테고리 코드 / 카카오톡 채널 관리자센터에서 확인해 주세요. |
| `notificationRequestToken` | 인증번호 받기 |
| `notificationTokenLabel` / `Hint` | 인증번호 6자리 / 관리자 카카오톡으로 보냈어요. |
| `notificationLink` | 연동하기 |
| `notificationEditInputs` | 다시 입력 |

- [ ] **Step 1: 테스트** (`report_settings_screen_test.dart`의 `_Server`·`_open` 양식 — `pushOnHome(tester, setup, '/settings/notification')`)
  - `설정_허브의_알림톡_줄이_알림톡_설정을_연다`(settings_screen_test).
  - `연동_전에는_안내_세_줄과_입력_세_칸이_보인다`.
  - `세_칸을_채우고_번호가_맞아야_인증번호_받기가_눌린다`: 번호 `0101234`면 `AppButton.onPressed == null`.
  - `인증번호_받기는_세_칸을_보내고_6자리_칸을_연다`: POST 본문 `{search_id: '@hisshaus', admin_phone: '01012345678', category_code: '00100010001'}`, 그 뒤 `notification_token` 칸이 보이고 입력 셋은 `enabled == false`.
  - `연동하기는_세_칸과_인증번호를_보내고_연동_뒤_화면으로_바뀐다`: POST 본문에 넷, 서버가 linked overview 로 답하면 입력 칸이 사라진다.
  - `인증번호가_틀리면_문구를_보이고_입력을_지우지_않는다`: 400 `NOTIFICATION_TOKEN_INVALID` → "인증번호가 틀렸거나 시간이 지났어요.", 칸 넷의 글 그대로.
  - `요청이_잦으면_429_문구를_보인다`.
  - `다시_입력을_누르면_첫_단계로_돌아간다`.
  - `직원에게는_사장님이_연동할_수_있어요만_보인다`(`role: 'staff'`): `TextField` 0개, 단추 0개.
  - `채널이_token_requested_나_unlinked_여도_연동_전_화면이다`(parametrize 둘).
  - `읽지_못하면_AsyncBody_의_다시_시도가_보인다`.
  - 골든 `notification_settings_unlinked.png`(사장, 연동 전).
- [ ] **Step 2:** 실패 확인. **Step 3:** 구현. **Step 4:** 통과 + `flutter test test/design`(`app_router_test`가 있으면 그것도) 통과, analyze 0.
- [ ] **Step 5:** 커밋 `feat(app): 알림톡 설정 화면 — 채널 연동`

---

### Task 4: 설정 화면 — 연동 후

**Files:** Task 3 의 화면·문구·테스트 파일. 골든 `notification_settings_pending.png`·`notification_settings_approved.png`·`notification_sender_sheet.png`.

**Interfaces — Consumes** Task 2 `updateSettings`·`unlinkChannel`·`requestSenderVerification`·`confirmSender`, 규칙의 고르기 값.

**연동 후 본문**(위에서 아래로):

1. 맨 위 한 줄 — 직원이면 `notificationOwnerOnly`, 사장이면 마지막 실패 문구.
2. 채널 카드: "연동됨 · 10월 14일"(`linkedAt`) + 사장에게만 `···`(semantic `more`) → 시트의 [연동 해제] → 확인 시트("예정된 알림톡이 모두 취소돼요. 연동을 해제할까요?" / [연동 해제]) → `unlinkChannel`.
3. 종류 카드 — 스위치 다섯 줄. 줄마다 이름·템플릿 상태 문구·`AppSwitch`. 딸린 고르기 줄은 그 스위치가 켜져 있을 때만 보인다.

| 줄 | 서버 칸 | 템플릿(문구를 고르는 종류) | 딸린 고르기 |
|---|---|---|---|
| 예약 접수 | `confirm_enabled` | confirm | — |
| 전날 리마인드 | `reminder_enabled` | reminder | 보내는 시각(`reminder_time`) |
| 예약 변경·취소 | `change_enabled` | change 와 cancel 가운데 나쁜 쪽(rejected > pending > approved) | — |
| 알림장 | `report_enabled` | report | — |
| 다음 예약 제안 | `next_visit_enabled` | nextVisit(없으면 문구 없음 — 켜면 등록된다) | 몇 주 뒤(`next_visit_after_weeks`)·다시 보내지 않는 기간(`next_visit_cooldown_days`) |

4. 문자 대체 카드: 스위치(`sms_fallback_enabled`) + 안내 한 줄 + 인증한 번호가 있으면 "발신번호 0212345678". 켜려는데 `senderVerified`가 false 면 PUT 대신 **발신번호 인증 시트**를 연다.

누름은 `report_settings_screen.dart`의 `_set`과 같은 문지기를 쓴다 — `_busy`거나 overview 가 `isLoading`·`hasError`면 아무것도 하지 않는다. 본문은 `overview.settingsBody(field:, value:)`. 고르기는 `AppSheet`의 목록에서 하나를 누르면 닫히고 그때 PUT 한 번(같은 값을 고르면 보내지 않는다).

**발신번호 인증 시트**: 번호 칸(키 `notification_sender_phone`, `^[0-9]{9,11}$`일 때 [인증번호 받기]) → `requestSenderVerification` → 코드 칸(키 `notification_sender_code`, 6자리)과 [확인] → `confirmSender` 성공 → 시트를 닫고 `updateSettings(settingsBody(field: 'sms_fallback_enabled', value: true))`. 실패 문구는 시트 안 한 줄.

문구:

| 이름 | 글 |
|---|---|
| `notificationLinkedOn(month, day)` | 연동됨 · {month}월 {day}일 |
| `notificationUnlink` | 연동 해제 |
| `notificationUnlinkConfirm` | 예정된 알림톡이 모두 취소돼요. 연동을 해제할까요? |
| `notificationKindConfirm`·`Reminder`·`ChangeCancel`·`Report`·`NextVisit` | 예약 접수 · 전날 리마인드 · 예약 변경·취소 · 알림장 · 다음 예약 제안 |
| `notificationTemplatePending` | 심사 중이에요(보통 1~3일) |
| `notificationTemplateApproved` | 승인됨 |
| `notificationTemplateRejected` | 반려됐어요 · 운영자가 확인 중 |
| `notificationReminderTimeLabel` | 보내는 시각 |
| `notificationNextVisitWeeksLabel` | 지난 미용 뒤 |
| `notificationWeeks(n)` / `notificationWeeksAuto` | {n}주 / 지난 방문 간격대로 |
| `notificationCooldownLabel` | 다시 보내지 않는 기간 |
| `notificationDays(n)` | {n}일 |
| `notificationNextVisitHint` | 마케팅 수신에 동의한 보호자에게만 보내요. |
| `notificationSmsFallback` | 문자로 대신 보내기 |
| `notificationSmsFallbackHint` | 알림톡을 못 받는 번호에 문자로 보내요. 문자는 알림톡보다 비싸요. |
| `notificationSenderNumber(number)` | 발신번호 {number} |
| `notificationSenderTitle` | 발신번호 인증 |
| `notificationSenderPhoneLabel` / `Hint` | 문자를 보낼 매장 번호 / 숫자만 적어 주세요. |
| `notificationSenderCodeLabel` | 인증번호 6자리 |
| `notificationSenderConfirm` | 확인 |

- [ ] **Step 1: 테스트**
  - `연동_뒤에는_채널_줄과_스위치_다섯과_문자_대체가_보인다`: 스위치 여섯(`AppSwitch`), 값이 픽스처와 같다.
  - `스위치를_누르면_아홉_칸_전체를_보내고_응답으로_다시_그린다`: `reminder_enabled`를 끔 → PUT 본문이 아홉 칸이고 그 칸만 false, 응답 뒤 스위치 false.
  - `보내는_중에는_다른_누름을_받지_않는다`(putGate): PUT 한 번.
  - `다시_읽는_중이거나_읽기에_실패했으면_누름을_보내지_않는다`(Review Focus 4, getGate·getError): PUT 0번.
  - `서버가_거절하면_문구를_보이고_서버_값으로_돌아간다`(409).
  - `템플릿_상태_문구_셋`(parametrize pending·approved·rejected → confirm 줄의 글).
  - `변경_취소_줄은_둘_가운데_나쁜_쪽_문구다`: change approved + cancel pending → "심사 중이에요(보통 1~3일)".
  - `다음_예약_제안은_템플릿이_없으면_문구가_없고_켜면_응답의_pending_을_보인다`.
  - `리마인드가_켜져_있을_때만_시각_줄이_보이고_고르면_닫히며_한_번_보낸다`: '09:30' → PUT 본문 `reminder_time: '09:30'`. 같은 값을 고르면 PUT 0번.
  - `주_고르기의_지난_방문_간격대로는_null_을_보낸다`, `쿨다운_고르기`.
  - `서버_값이_목록에_없으면_그_값도_고를_수_있게_보인다`: `next_visit_cooldown_days: 45`.
  - `직원은_스위치가_눌리지_않고_더보기가_없다`: 모든 `AppSwitch.onChanged == null`, PUT 0번.
  - `연동_해제는_확인_뒤_DELETE_하고_연동_전_화면으로_돌아간다` / `확인에서_취소하면_보내지_않는다`.
  - `발신번호_인증_없이_문자_대체를_켜면_시트가_뜨고_PUT_은_나가지_않는다`.
  - `시트에서_인증을_마치면_닫히고_문자_대체를_켜는_PUT_이_한_번_나간다`: POST 둘의 본문(`{phone}`, `{phone, code}`), 그 뒤 PUT 의 `sms_fallback_enabled: true`.
  - `시트의_인증번호가_틀리면_시트_안에_문구를_보이고_닫지_않는다`.
  - `발신번호를_이미_인증했으면_문자_대체는_바로_PUT_한다`.
  - 골든 셋.
- [ ] **Step 2~4:** 실패 확인 → 구현 → 통과, analyze 0, `flutter test test/design`.
- [ ] **Step 5:** 커밋 `feat(app): 알림톡 설정 화면 — 종류별 스위치, 시각·주기 고르기, 문자 대체와 발신번호 인증, 연동 해제`

---

### Task 5: 방문 상세의 알림톡 블록

**Files:**
- Create: `lib/features/visit/screens/visit_notifications_block.dart`
- Modify: `lib/features/visit/screens/visit_detail_screen.dart`(`_Body`의 `_ReportCard` 바로 아래에 `VisitNotificationsBlock(visitKey: …)` 한 줄), `lib/l10n/app_strings.dart`
- Test: `test/features/visit/screens/visit_detail_screen_test.dart`(새 그룹), 골든 `goldens/visit_detail_notifications.png`

**Interfaces — Consumes** `visitNotificationsProvider`, `visibleRows`·`isLatestOfKind`, `NotificationCommands.resend`, `shareSheetProvider`, `todayProvider`.

`VisitNotificationsBlock`은 `ConsumerStatefulWidget`이다. `visitNotificationsProvider(key)`가 데이터가 아니거나 `visibleRows`가 비면 `SizedBox.shrink()`. 있으면 `AppCard` 하나에 제목 "알림톡"과 줄들(서버 순서 = 최신순).

줄의 글(시각 `at`은 `_ReportCard._at`과 같은 규칙 — 오늘이면 `hhmm`, 아니면 `dayLabel hhmm`):

| 상태 | 글 |
|---|---|
| scheduled | `{종류} · {at(scheduledAt)} 예정` |
| sending · accepted | `{종류} · 보내는 중` |
| sent | `{종류} · 보냄 · {at(sentAt)}` |
| fallbackSent | `{종류} · 문자로 보냄 · {at(sentAt)}` |
| failed + transient | `{종류} · 못 보냈어요 · 잠시 문제가 있었어요` + [다시 보내기] |
| failed + permanent | `{종류} · 못 보냈어요 · 알림톡을 받을 수 없는 번호예요` + [다른 방법으로 보내기](`shareText`가 null 이면 단추 없음) |
| canceled | (그리지 않는다) |

종류 이름은 `notificationRowKind*` — 예약 접수 · 전날 리마인드 · 알림장 · 예약 변경 · 예약 취소 · 다음 예약 제안. 단추는 `isLatestOfKind`인 줄에만. [다시 보내기]는 `resend`를 부르고 그동안 블록의 단추를 잠근다. 예외는 `AppSnackBar`로 `messageFor`. [다른 방법으로 보내기]는 누른 단추의 자리(`origin`)와 `shareText`를 공유 시트에 넘기고, 공유 시트 예외는 `reportShareAgainFailed` 스낵바.

문구: `notificationBlockTitle` "알림톡", `notificationScheduled(at)` "{at} 예정", `notificationSending` "보내는 중", `notificationSent(at)` "보냄 · {at}", `notificationSentBySms(at)` "문자로 보냄 · {at}", `notificationFailed` "못 보냈어요", `notificationFailedTransient` "잠시 문제가 있었어요", `notificationFailedPermanent` "알림톡을 받을 수 없는 번호예요", `notificationResend` "다시 보내기", `notificationShareInstead` "다른 방법으로 보내기".

- [ ] **Step 1: 테스트** (기존 방문 상세 테스트의 서버 구성에 `GET /v1/shops/3/visits/101/notifications`를 더해)
  - `내역이_없으면_알림톡_블록이_없다`(기본 대역의 빈 목록).
  - `줄_다섯_상태의_글`: scheduled·accepted·sent·fallback_sent·failed 한 줄씩 → 위 표의 글 그대로(시각은 픽스처의 날짜로 계산한 글).
  - `취소된_줄은_보이지_않는다`.
  - `내역을_읽지_못해도_방문_상세는_보이고_블록만_없다`(500).
  - `모르는_종류의_줄만_빠지고_상세는_보인다`(Review Focus 5).
  - `일시_실패의_가장_최근_줄에만_다시_보내기가_있다`: 같은 종류의 옛 실패 줄에는 단추가 없다.
  - `다시_보내기는_재발송하고_보내는_중을_거쳐_보냄으로_바뀐다`: POST 한 번, 응답 뒤 "보내는 중", 1초 뒤 "보냄".
  - `직원도_다시_보내기를_누를_수_있다`(`role: 'staff'`).
  - `재발송이_404_면_문구를_알리고_블록을_다시_읽는다`(Review Focus 3): 스낵바 "다시 보낼 알림을 찾지 못했어요. 화면을 새로 불러왔어요.", 내역 GET 이 한 번 더.
  - `재발송이_409_면_이미_보내는_중이에요를_알린다`.
  - `영구_실패는_다른_방법으로_보내기가_share_text_를_공유_시트에_넘긴다`: `setup.shareSheet`가 받은 글 == 픽스처의 `shareText`.
  - `share_text_가_없으면_단추가_없다`.
  - `당겨_새로고침하면_상세와_내역을_둘_다_다시_읽는다`.
  - 골든 `visit_detail_notifications.png`(줄 넷: 예정·보냄·문자로 보냄·영구 실패).
  - 기존 골든 `visit_detail*.png` 셋은 바뀌지 않는다(실행해 확인).
- [ ] **Step 2~4:** 실패 확인 → 구현 → `flutter test test/features/visit` 통과, analyze 0.
- [ ] **Step 5:** 커밋 `feat(app): 방문 상세의 알림톡 내역 — 다시 보내기, 다른 방법으로 보내기`

---

### Task 6: 알림장 보내기 — 알림톡 결과 기다리기

**Files:**
- Modify: `lib/features/visit/screens/report_preview_screen.dart`(`_send`), `lib/l10n/app_strings.dart`
- Test: `test/features/visit/screens/report_preview_screen_test.dart`(새 그룹)

**Interfaces — Consumes** `NotificationCommands.reportRowIds`·`awaitReport`, `ReportDelivery`.

`_send`의 새 순서(고르기 `widget.picking`은 지금 그대로 — 알림톡을 보지 않는다):

1. `before = await reportRowIds(shopId, visitId)` → `ReportCommands.send(…)`(지금 그대로, 실패 처리도 그대로).
2. 보낸 뒤 `_busy`는 그대로 두되 **뒤로 가기는 푼다**(`_awaiting = true` — `PopScope`의 `canPop`은 `!_busy || _awaiting`). 단추는 진행 표시 그대로.
3. `delivery = await awaitReport(shopId, visitId, before: before)`. 돌아왔을 때 `!mounted`면 아무것도 하지 않고 끝낸다.
4. `switch (delivery)` 완전 열거:
   - `ReportNotSent` → 지금의 공유 시트 경로 그대로(`sent.link.url`), 닫는다.
   - `ReportDelivered` → 닫고 스낵바 `reportSentByAlimtalk`.
   - `ReportFailed` → 스낵바 `reportAlimtalkFailed`, 공유 시트에 `shareText ?? sent.link.url!`, 닫는다(공유 시트 예외는 지금처럼 `reportShareFailed`).
   - `ReportPending` → 닫고 스낵바 `reportAlimtalkPending`.

문구: `reportSentByAlimtalk` "알림톡으로 보냈어요.", `reportAlimtalkFailed` "알림톡을 못 보내서 다른 방법으로 보내요.", `reportAlimtalkPending` "알림톡을 보내는 중이에요."

- [ ] **Step 1: 테스트** (미리보기 테스트의 서버에 `GET …/visits/101/notifications`를 더해)
  - `알림톡_줄이_없으면_지금처럼_공유_시트가_뜬다`: 공유 시트가 링크 주소를 받는다(기존 보내기 테스트는 고치지 않고 통과해야 한다 — 기본 대역이 빈 목록이다).
  - `알림톡이_나가면_닫고_알림톡으로_보냈어요를_알리며_공유_시트는_뜨지_않는다`: 보낸 뒤 내역이 `report`·`sent` → 스낵바, `setup.shareSheet` 비어 있음, 닫힘 값 true.
  - `알림톡이_실패하면_알리고_share_text_로_공유_시트가_뜬다`.
  - `실패했는데_share_text_가_없으면_링크_주소로_공유_시트가_뜬다`.
  - `10초가_지나도_접수_중이면_닫고_보내는_중이에요를_알린다`: `tester.pump(const Duration(seconds: 1))` 열 번.
  - `끊고_다시_보낼_때_옛_보냄_줄은_새_발송으로_치지_않는다`(Review Focus 2): 보내기 전후 내역이 같은 `sent` 한 줄 → 공유 시트.
  - `기다리는_중에_뒤로_가면_닫히고_그_뒤에는_아무것도_띄우지_않는다`(Review Focus 1): 2초 뒤 뒤로 → 화면 닫힘, 나머지 8초를 흘려도 스낵바·공유 시트 없음, 예외 없음.
  - `보내기_전_내역을_읽지_못하면_공유_시트로_간다`.
  - `보낼_사진_고르기의_저장은_알림톡을_보지_않는다`: `?pick=1` → 내역 GET 0번.
- [ ] **Step 2~4:** 실패 확인 → 구현 → `flutter test` 전체 통과(골든 포함, 기존 골든 무변), analyze 0.
- [ ] **Step 5:** 커밋 `feat(app): 알림장 보내기 — 알림톡으로 나갔는지 기다렸다가 알리고, 못 보내면 공유 시트로`

---

### Task 7: 시뮬레이터 흐름·문서·전체 검증

**Files:**
- Create: `app/tool/prepare_notification_flow.sh`, `app/integration_test/notification_flow_test.dart`
- Modify: `app/CLAUDE.md`, `_docs/harness.md`(앱 흐름 줄), `_docs/decisions/009-notification.md`("⑥-2 앱에서 정한 것" 절)

**준비 스크립트**(`infra/`에서, `prepare_report_flow.sh`의 양식 — 게이트웨이 경유, 번호·토큰·주소를 찍지 않는다). 만드는 것과 마지막 줄의 `--dart-define`:

- 매장 A(`SHOP`): 사장 `OWNER`·직원 `STAFF`. API 로 채널 연동(토큰 `000000`) → `docker compose exec -T backend python scripts/reregister_templates.py --shop <A> --refresh`로 템플릿 승인. 보호자 둘 — 보통 번호(`CUSTOMER_OK`의 이름)와 끝 네 자리 `0000`(`CUSTOMER_FAIL`의 이름, 가짜 게이트웨이의 영구 실패). 보통 번호 보호자의 완료·기록 있는 방문 하나(`VISIT_DONE` — 알림장 보내기용, `prepare_report_flow.sh`와 같은 방법).
- 매장 B(`SHOP_NEW`): 사장 `OWNER_NEW`. 연동하지 않는다.

**흐름**(`step`마다 스크린샷, iOS 시뮬레이터와 Android 에뮬레이터 각 한 번):

1. `OWNER_NEW` 로그인 → 설정 → 알림톡 → 안내 세 줄 → 세 칸 입력 → [인증번호 받기] → `000000` → [연동하기] → 채널 줄 "연동됨", 스위치 다섯, "심사 중이에요(보통 1~3일)".
2. `OWNER` 로그인(매장 A) → 알림톡 설정에 "승인됨" → 전날 리마인드 시각을 바꾼다 → 다시 열어도 그 값.
3. 예약 등록(보통 번호 보호자, 모레) → 방문 상세의 알림톡 블록에 "예약 접수 · 보냄"이 뜰 때까지 당겨 새로고침하며 기다린다(최대 20초), "전날 리마인드 · … 예정".
4. 예약 등록(`0000` 보호자) → 상세에 "예약 접수 · 못 보냈어요 · 알림톡을 받을 수 없는 번호예요" → [다른 방법으로 보내기] → 공유 시트 대역이 글을 받았다(길이 > 0 만 본다, 찍지 않는다).
5. `VISIT_DONE` → [알림장 보내기] → [보내기] → "알림톡으로 보냈어요." 스낵바, 공유 시트 대역은 비어 있다 → 상세 블록에 "알림장 · 보냄".
6. `STAFF` 로그인 → 알림톡 설정이 읽기 전용("사장만 바꿀 수 있어요.").

- [ ] **Step 1:** 스크립트와 흐름을 쓴다(흐름의 머리 주석에 준비·실행 명령).
- [ ] **Step 2:** 개발 스택을 띄우고 iOS 시뮬레이터에서 6/6, Android 에뮬레이터에서 6/6. 실패한 단계는 스크린샷으로 원인을 보고 고친다. 판별력 한 번: 흐름의 "알림톡으로 보냈어요." 기대를 다른 글로 바꾸면 5단계에서 멈춘다.
- [ ] **Step 3: 문서**
  - `app/CLAUDE.md` "꼭 지킬 것"에 알림톡 항 하나: 쓰기는 `NotificationCommands`로만, 설정은 [저장] 없이 아홉 칸 전체 PUT, 알림장 보내기 뒤의 결과 기다리기 규칙(이번 보내기가 만든 줄만·10초·기다리는 중 뒤로 가기 허용), 내역은 방문 상세를 따라 다시 읽는다, 모르는 종류·상태의 줄은 뺀다, 번호·인증번호·`share_text`를 남기지 않는다, 온보딩 입력값은 화면 상태에만. 폴더 규칙의 괄호에 "알림톡 설정"을 더한다.
  - `_docs/harness.md` 앱 흐름 줄에 `notification_flow_test.dart`와 준비 스크립트.
  - 009 에 "⑥-2 앱에서 정한 것" 절 — 이 계획의 "정한 것" 열하나와 검증 숫자, 실기기에서만 볼 수 있는 것(실제 공유 시트에 `share_text`, 실계정 카테고리 코드).
- [ ] **Step 4: 전체 검증** — `flutter analyze` 0, `flutter test` 전체(수를 적는다, 기존 861 + 새 테스트), 기존 골든 무변(`git status`에 새 골든만), 백엔드는 건드리지 않았다(`git diff --stat main -- backend` 빈 결과).
- [ ] **Step 5:** 커밋 `test(app): 알림톡 시뮬레이터 흐름` + `docs: ⑥-2 알림톡 앱 — 앱 규칙, 검증 장치, 결정 기록 009`
