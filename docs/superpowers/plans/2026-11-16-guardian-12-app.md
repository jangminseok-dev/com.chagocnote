# ⑫-3 앱 — 리뷰 주소 · 몸무게가 보이는 모습 · 가족 수 · 미리보기의 리뷰 줄 · 연결 줄의 가족 수 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 매장이 알림장 설정에서 리뷰 주소·문구를 넣고([열어 보기]로 맞는 곳인지 보고) 보호자가 받는 모습을 보며, 몸무게 보이기가 보호자에게 무엇을 바꾸는지 보고, 고객 한 명당 함께 볼 가족 수를 정한다. 보내기 전 미리보기에서 그 알림장만 리뷰 줄을 뺄 수 있고, 반려동물 상세의 보호자 연결 줄에 가족 수가 보인다.

**Architecture:** 백엔드 ⑫-1 의 계약(`_docs/decisions/015-guardian-archive.md` 의 "API 계약")을 부른다. 호출은 지금 자리(`features/visit/api/report_api.dart`, `features/customer/api/customer_api.dart`)에 더한다 — 기능 사이 import 를 늘리지 않는다. 바깥 주소 열기는 공유 시트와 같은 모양의 자체 네이티브 채널 `chagocnote/external_link`(패키지 추가 없음, 웹뷰 금지).

**Tech Stack:** Flutter · Riverpod 3 · go_router · 네이티브 Swift(`UIApplication.open`)·Kotlin(`ACTION_VIEW`).

**Spec:** `docs/superpowers/specs/2026-11-16-guardian-archive-design.md` 3.3·3.6·5.4·8절(8절의 답이 앞선다). 앱 규칙 `app/CLAUDE.md`.

## Global Constraints

- 웹뷰 패키지·`url_launcher` 를 넣지 않는다. 바깥 주소 열기는 `https` 만 — Dart 가 먼저 보고, 네이티브도 다시 본다.
- 알림장 설정은 지금처럼 **누르면 바로 전체 교체**(이제 일곱 칸 — 다섯 칸 + `review_url`·`review_text`), 낙관적으로 그리지 않고 다시 읽은 서버 값으로 그린다. 글을 치는 리뷰 구역만 [저장]이 있다. 사장만 바꾼다(직원은 읽기 전용 — [열어 보기]는 직원도).
- 리뷰 주소 규칙(서버와 같다): 빈 칸이면 지움(null) · `https://` 로 시작(대소문자 무관) · 300자 이하 · 호스트가 있다 · `@`(계정 정보)·공백·제어·보이지 않는 문자(유니코드 Cc·Cf·Zl·Zp) 없음 · 포트가 숫자. 틀리면 칸 아래에 까닭(`https:// 로 시작하는 주소를 넣어 주세요` 등).
- 리뷰 문구 규칙: 빈 칸이면 기본 문구(null) · 60자 이하 · 줄바꿈·제어·보이지 않는 문자 없음 · `http`·`www.` 를 넣지 못한다.
- 몸무게 보이기 아래 **보호자가 받는 모습**: 켜짐 → 몸무게 한 줄과 작은 변화 그림의 본, 꺼짐 → `꺼져 있어요 — 보호자에게 몸무게와 몸무게 변화가 보이지 않아요`.
- 가족 수: `가족과 함께 보기 — 고객 한 명당 N명까지`, 0~10, 기본 3. 줄 아래 `줄여도 이미 함께 보는 가족은 그대로예요. 새 초대만 막아요`, 0 이면 `0명이면 보호자가 가족을 초대할 수 없어요`. 값은 `guardian-settings`(따로 읽고 따로 쓴다 — 읽지 못하면 그 구역만 한 줄 다시 시도).
- 미리보기: 매장이 리뷰 주소를 넣었을 때만(`report.review_url` 이 있을 때) `리뷰 남기기 줄 넣기` 스위치(기본 켜짐, 살아 있는 링크면 그 링크의 값)와 켜졌을 때 리뷰 줄의 본. 보내기·고르기 저장은 **늘 `show_review` 를 싣는다**(서버는 빠지면 켬으로 본다 — 앞서 뺀 것이 되살아나지 않게).
- 연결 줄: `보호자 계정 연결됨 · 11월 13일 · 가족 2명`(가족이 있을 때만), 끊기 확인에 `함께 보던 가족도 볼 수 없어요`(가족이 있을 때만). 보호자·가족이 누구인지는 받지도 그리지도 않는다.
- 리뷰 주소는 비밀이 아니지만 알림장 주소(토큰)는 그렇다 — 테스트 출력·스크린샷 설명에 알림장 링크를 남기지 않는다(지금 규칙 그대로). 문구는 해요체, "AI"·"법적 효력" 없음.

## Review Focus

1. 고르기 저장·다시 보내기가 `show_review` 를 빠뜨려 뺀 리뷰 줄이 되살아난다(낡은 화면·다시 읽은 링크 값).
2. 리뷰 주소 칸에 붙여넣은 앞뒤 공백·줄바꿈·대문자 스킴·한글 도메인·포트가 서버와 다르게 판정돼 [저장]이 422 로 떨어지거나 막지 말 것을 막는다.
3. 설정의 일곱 칸 전체 교체가 리뷰 칸을 고치는 중(저장 전) 다른 스위치를 누르면 적던 글을 서버 값으로 덮거나, 반대로 적던 글을 같이 보낸다.
4. 가족 수 구역의 읽기 실패·저장 실패가 알림장 설정 본문을 가리거나, 빠르게 두 번 누른 + 가 두 번 보내 범위를 넘는다.
5. [열어 보기]가 https 가 아닌 주소·빈 칸·네이티브 실패(브라우저 없음)에서 조용히 아무 일도 안 하거나 죽는다.

---

### Task 1: 바깥 주소 열기 채널

**Files:** Create `lib/core/proxy/external_link.dart`(`abstract class ExternalLink { Future<void> open(Uri url); }`, `ChannelExternalLink`, `externalLinkProvider`, 채널 `chagocnote/external_link` 의 `open({url})`), `ios/Runner/ExternalLink.swift`(`ExternalLinkPlugin` — `UIApplication.shared.open`, 완료가 false 면 `FAILED`), `android/.../ExternalLink.kt`(`ExternalLinkChannel` — `ACTION_VIEW` + `CATEGORY_BROWSABLE`, `ActivityNotFoundException` → `NO_BROWSER`), 등록(`AppDelegate.swift`, `MainActivity.kt`, `tool/add_ios_file.rb ExternalLink.swift`), `test/support/fake_external_link.dart`(연 주소를 모은다), `test/core/proxy/external_link_test.dart`.

- Dart 의 `open` 은 `https` 가 아니거나 호스트가 없으면 채널을 부르지 않고 `ArgumentError` 를 던진다. 채널 오류(`PlatformException`)는 그대로 던진다 — 화면이 `on Exception`·`on ArgumentError` 로 잡아 알린다.
- 네이티브도 `https` 가 아니면 `BAD_URL`.
- 테스트(RED 먼저): 채널에 `open` 과 `url` 문자열이 그대로 가는지, `http:`·`javascript:`·호스트 없음은 채널을 부르지 않는지, 채널 오류가 던져지는지. `CustomerTestSetup`·설정 테스트 도우미에 대역을 기본으로 꽂는다.

### Task 2: 모델 · API · 규칙 · 명령

**Files:** `features/visit/api/report_models.dart`(`ReportSettings` 에 `reviewUrl`·`reviewText`·`reviewTextDefault` — `toJson` 은 일곱 칸, 기본 문구는 싣지 않는다 / `VisitReportPreview` 에 `reviewUrl`·`reviewText` / `ReportLink` 에 `showReview`(bool?) / 새 `GuardianSettings{familyMax, defaultFamilyMax}`), `report_api.dart`(`send(..., showReview:)`, `guardianSettings(shopId)`, `updateGuardianSettings(shopId, familyMax)`), `state/report_rules.dart`(`reviewUrlProblem(String) → String?`, `reviewTextProblem(String) → String?`, `cleanReviewUrl(String) → String?` — 앞뒤 공백을 걷고 빈 칸은 null), `state/report_providers.dart`(`guardianSettingsProvider`), `state/report_commands.dart`(`send` 의 `showReview: bool?` — null 이면 다시 읽은 링크의 값(없으면 true)을 싣는다, `updateGuardianSettings` — 성공하든 실패하든 다시 읽는다), `features/customer/api/customer_models.dart`(`GuardianLink.familyCount`, 없으면 0), `l10n/app_strings.dart`, `test/support/visit_fixtures.dart`(`reportSettingsJson`·미리보기 json 에 새 칸).

- 테스트(RED 먼저): 모델이 칸이 없는 예전 응답도 읽는다(리뷰 null·`showReview` null·`familyCount` 0), `toJson` 일곱 칸, `send` 본문에 `show_review` 가 늘 있다(고른 값 / 고르지 않았으면 다시 읽은 링크의 값 / 링크가 없으면 true), 규칙의 경계(299·300·301자, `HTTPS://`, 공백·`@`·`​`·`\n`, 포트 `:abc`, 호스트 없음 `https://`, 문구 60·61자·`www.`·`HTTP`), 가족 설정 읽기·쓰기 본문.

### Task 3: 알림장 설정 화면

**Files:** `features/visit/screens/settings/report_settings_screen.dart`(+ 필요하면 같은 폴더에 `report_review_section.dart`·`report_family_section.dart`), 테스트 `test/features/visit/screens/settings/report_settings_screen_test.dart`, 골든 `goldens/report_settings.png` 갱신.

- 몸무게 줄 바로 아래 **보호자가 받는 모습**(켜짐·꺼짐 두 모양).
- 리뷰 구역 `알림장 끝에 리뷰 남기기 줄 넣기`: 주소 칸(붙여넣기, 키 `report-review-url`) · [열어 보기] · 문구 칸(서버 문구, 없으면 기본 문구로 채움, 키 `report-review-text`) · [저장](바뀐 것이 있고 사장일 때만 눌린다) · 칸 아래 까닭 · **보호자가 받는 모습**(매장 카드 → 리뷰 줄 → 꼬리, 주소가 비면 줄 없이 흐린 본과 `주소를 넣으면 알림장 끝에 이렇게 나와요`). 저장은 화면이 보이는 서버 값의 다섯 칸 + 적은 두 칸으로 일곱 칸을 보낸다. 다른 스위치·칩은 **서버의 리뷰 값**을 실어 보낸다(적던 글은 칸에 남고 보내지 않는다).
- 가족 구역: `가족과 함께 보기 — 고객 한 명당 N명까지` + [−]·[+](0·10 에서 막힘, 보내는 중 막힘) + 줄 아래 문구 두 가지 중 하나. 읽지 못하면 `AppErrorRetry.row`.
- [열어 보기]: 칸의 주소가 규칙에 맞으면 `externalLinkProvider.open`, 아니면 그 칸 아래 까닭, 네이티브 실패면 스낵바 `주소를 열지 못했어요. 주소를 다시 확인해 주세요.`
- 테스트: 보이는 모습 둘, 저장 본문 일곱 칸, 틀린 주소는 보내지 않고 까닭, 저장 전 다른 스위치를 눌러도 적던 글이 칸에 남고 본문에는 서버 값, 직원 읽기 전용([열어 보기]는 된다), 가족 수 +·− 본문·끝에서 막힘·0 의 문구·읽기 실패의 한 줄, 열어 보기의 세 갈래.

### Task 4: 미리보기의 리뷰 줄과 스위치

**Files:** `features/visit/screens/report_preview_screen.dart`, 테스트 `report_preview_screen_test.dart`, 골든.

- `report.review_url` 이 있을 때만: `리뷰 남기기 줄 넣기` 스위치(키 `report-preview-review`, 처음 값 = 링크의 `show_review` ?? true) + 켜졌을 때 리뷰 줄의 본(누르지 않는다, 문구는 서버가 준 것). 주소가 없으면 아무것도 더하지 않는다.
- [보내기]·[저장](고르기)이 `send(showReview: 스위치를 건드렸으면 그 값, 아니면 null)` — 명령이 다시 읽은 값으로 채운다.
- 테스트: 주소 없음 → 스위치 없음, 끄고 보내면 본문 `show_review: false`, 건드리지 않고 고르기 저장 → 링크의 false 그대로, 켜짐일 때만 본.

### Task 5: 반려동물 상세의 연결 줄

**Files:** `features/customer/screens/guardian_link_row.dart`, `l10n/app_strings.dart`, 테스트 `guardian_link_row_test.dart`.

- `family_count > 0` 이면 `… · 가족 N명`, 끊기 확인 글에 `함께 보던 가족도 볼 수 없어요` 를 붙인다. 0 이면 지금 그대로.

### Task 6: 시뮬레이터 흐름 · 문서

**Files:** `tool/prepare_archive_flow.sh`(매장·고객·방문 하나·사진·보낸 알림장, 보호자 웹 세션으로 잇고 가족 하나를 잇는다 — `check_guardian_flow.sh` 의 호출 모양), `integration_test/archive_flow_test.dart`(설정: 몸무게 켜기 → 보이는 모습 / 리뷰 주소 넣고 저장 → 다시 읽은 값 / [열어 보기] → 대역 채널이 그 주소를 받음 / 가족 수 + → 다시 읽은 값; 미리보기: 스위치 끄고 [저장](고르기) → 서버의 `show_review` false(공개 알림장에 칸 없음은 흐름 밖 — 백엔드 흐름이 본다); 반려동물 상세: `· 가족 1명`), `app/CLAUDE.md`(바깥 주소 열기 채널·설정 일곱 칸·가족 구역·미리보기의 `show_review`), 015 에 "⑫-3 앱에서 정한 것". `flutter analyze`·`flutter test`·iOS·안드로이드 흐름.
