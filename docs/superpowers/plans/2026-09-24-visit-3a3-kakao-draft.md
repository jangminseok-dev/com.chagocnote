# 차곡노트 ③-A 예약·방문 — 계획 ③-A3: 카톡 예약 초안 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카톡으로 온 예약 문의 글을 앱에 넣으면(붙여넣기 또는 카톡 [공유] → 차곡노트) 서버가 규칙으로 해석해 날짜·시각·보호자 후보·반려동물·메뉴를 채운 초안을 주고, 사장이 초안 화면에서 확인한 뒤 기존 예약 ② 폼으로 이어 저장한다. 함께 ③-A2 가 사용자 판단으로 남긴 6건(등록 `VISIT_DUPLICATE` 안내, 상태가 섞인 가족 카드, 노쇼 라벨 중복, 옅은 칸·줄 그은 칸 색, 미리보기 "외 N건", 30분 블록)을 마무리한다.

**Architecture:** 백엔드는 visit 스포크에 슬라이스 하나(`POST /visit-drafts`)를 더한다. 해석은 도메인 서비스 `visit/domain/services/draft_parser.py`(날짜·시간·메뉴·낱말, 표 기반 테스트)가 하고, 유스케이스는 아웃바운드 포트 `VisitDraftParserPort` 뒤의 어댑터로 부른다(⑨ 뒤에 LLM 어댑터로 바꾸는 자리). 보호자 후보는 허브 포트 `CustomerDirectoryPort.find_draft_candidates(ctx, words)`(customer 구현 — 새 `CustomerSearchPort.match_any` OR 검색 + 순위)로 찾는다. 초안은 저장하지 않고 글·낱말을 로그·DB·오류 응답에 남기지 않는다(V9). 앱은 `VisitApi.parseDraft` → 초안 화면 `/visits/draft`(A안: 받은 글 + 후보·날짜·시각·메뉴 + 짐작 뱃지) → [예약 이어서]가 `VisitPrefill`로 기존 예약 ② 폼을 채워 연다. 입구는 둘 — 예약 ①의 [카톡 붙여넣기](클립보드)와 공유 받기(iOS Share Extension + 안드로이드 `ACTION_SEND`, **직접 쓴 네이티브 코드, 글만 넘김, 의존성 0**). 공유 확장은 토큰·네트워크에 접근하지 않고 App Group 에 글만 두고 URL 스킴으로 본체를 연다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · pytest / Flutter 3.44.8 · Dart 3.12 · flutter_riverpod 3.4 · go_router 18 · dio 5 · flutter_test(골든) / Swift(Share Extension·SceneDelegate) · Kotlin(MainActivity) — **새 의존성 없음**(백엔드·앱 모두).

**Spec:** `docs/superpowers/specs/2026-09-23-visit-reservation-design.md` — 이 계획은 12절의 "③-A3 카톡 초안"이다: 2절 표의 "카톡 예약 초안" 행, 3.1절 1(카톡 초안 해석)·5(카톡 붙여넣기, iOS 공유 확장·안드로이드 텍스트 인텐트), 4절의 `draft_parser`·`VisitDraftParserPort`, 4.1절 `find_draft_candidates`, 7절 전부, 8절 표의 `POST /visit-drafts`, 10절 위협 점검표 V9·V12, 11절의 초안 해석기 테스트·V9·완료 기준의 "카톡 붙여넣기 초안"과 "공유 확장은 실기기에서". 실행자는 설계 문서와 함께 `_docs/decisions/006-visit-reservation.md`(③-A1 의 API 계약과 ③-A2 절 — 특히 "사용자 판단으로 남긴 것"), `app/CLAUDE.md`, `backend/apps/{visit,customer,hub}/_docs/CLAUDE.md`를 읽는다.

**계획의 위치:** ③-A 의 구현 계획 세 개 가운데 마지막이다. ③-A1(백엔드) → ③-A2(앱) → **③-A3(이 문서, 백엔드 슬라이스 하나 + 앱 화면 하나 + 네이티브 공유 받기 + A2 마무리)**. 모두 `main`에 들어가 있다. 이 계획이 끝나면 설계 11절 완료 기준의 마지막 항목(카톡 붙여넣기 초안)을 시뮬레이터에서, 공유 받기를 실기기에서 사용자와 확인한다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 백엔드 명령은 `infra/`에서, 앱 명령은 `app/`에서 돌린다.
- 작업 브랜치는 `feat/visit-3a3-kakao-draft`다(`main` `5072504`에서 따고, 이 계획서 커밋이 첫 커밋이다). `main`에서 직접 작업하지 않는다.
- **사용자가 작업 단위 커밋을 허용했다(2026-09-22 이후 계속).** 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 앱 이름은 "차곡노트", iOS 번들 ID 는 `com.chagocnote.app`, 안드로이드 `applicationId`도 `com.chagocnote.app`(네임스페이스는 `com.chagocnote.chagocnote`).
- 이 계획은 **새 의존성을 추가하지 않는다**(`pubspec.yaml`·`requirements` 그대로). 공유 받기는 직접 쓴 Swift·Kotlin 이다.
- **`dart format`은 이 계획이 새로 만든 파일에만, 파일 이름을 짚어 돌린다.** 기존 파일은 diff 그대로만 바꾼다(③-A2 와 같은 이유).
- 볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다. 이 계획에는 마이그레이션이 없다.
- 비밀값·토큰·**카톡 글·고객의 이름·전화번호·메모**를 로그에 남기지 않는다. 백엔드는 글·낱말을 `logging`에 넘기지 않고 오류 응답에 되돌려주지 않는다. 앱은 `print`·`debugPrint`·dio `LogInterceptor`를 쓰지 않고, 모델에 `toString`을 두지 않는다. 공유 확장은 글을 App Group 에만 두고 본체가 읽은 뒤 바로 지운다.
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (백엔드 — `_docs/architecture.md`, 스포크 `CLAUDE.md` 그대로)
- 스포크끼리 직접 import 하지 않는다. visit 은 customer 를 허브 포트 `CustomerDirectoryPort`로만 쓰고, 자리는 `visit/dependencies/hub_ports.py`, 구현은 `main.py`가 꽂는다(이미 있다 — 메서드만 는다).
- `visit.domain`은 core·pydantic·hub 를 import 하지 않는다(구조 계약 "도메인 순수성"). 해석기는 `text`·`today`·영업시간·메뉴 이름만 받는다.
- 매장 범위 경로는 `require_permission("reservation:write")`로 `ShopContext`를 받는다. 초안은 쓰기 권한이다(예약을 만들려는 사람만 부른다).
- 초안 요청은 `schedule.ensure`(설정 행이 없으면 만든다 — 하루 목록과 같다) 외에 아무것도 쓰지 않는다. 잠금도 없다(저장하지 않는다).
- 오류 응답은 `{code, message}` 한 형식이고 도메인 오류 → 상태 코드는 `error_map.py`. 이 슬라이스는 새 도메인 오류를 만들지 않는다(입력 검증은 pydantic 422).

구조 (앱 — `app/CLAUDE.md`, 결정 기록 004·005·006 그대로)
- 기능 폴더 `lib/features/visit/` 안은 `api/` · `state/` · `screens/` 세 층. 네이티브 채널은 `lib/core/proxy/`에 둔다(외부 세계와의 경계).
- 서버 응답의 필드명은 바꾸지 않는다. 모델은 평범한 클래스에 `fromJson`. 코드 생성기 없음.
- 화면은 `lib/design/widgets`만 쓴다. 새 위젯(`AppSnackBar`)은 `design/widgets`에 더한다. `liquid_glass_widgets`는 `lib/design/bridge/` 밖에서 import 하지 않는다.
- 새 화면 파일은 불투명 `AppCard`만 쓰고 `test/design/glass_boundary_test.dart` 목록에 더한다.
- 사용자에게 보이는 문구는 `lib/l10n/app_strings.dart`의 상수만 쓴다. 오류 문구는 `messageFor`.
- 매장 범위 조회는 `autoDispose` + `runShopScoped`. 오류 화면에는 [다시 시도]와 뒤로 가기가 있고, 모든 하위 화면 머리에 `AppBackButton`.
- 저장·쓰기 버튼은 요청 중 비활성. **응답 시각은 매장 시간대다** — 초안의 `date`·`time`도 그대로 폼에 넣고 앱은 시간대를 계산하지 않는다.
- 웹뷰 금지. 공유 받기는 네이티브 코드다.

검증 명령 (`infra/`에서)
- 백엔드 단위: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"`
- 백엔드 통합(실제 Postgres): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration`
- 구조 계약: `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept
- 라우트 표: `docker compose run --rm --no-deps auth python scripts/print_routes.py` → visit 경로 21개(20 + `POST /v1/shops/{shop_id}/visit-drafts`)
- 흐름 스크립트: `docker compose restart backend && bash ../backend/scripts/check_visit_flow.sh` (백엔드 코드를 바꾼 뒤 실서버 확인 전엔 재시작 — ③-A2 교훈: `--reload`가 변경을 놓칠 수 있다)

검증 명령 (`app/`에서)
- `flutter analyze` → `No issues found!`
- `flutter test --timeout 30s` → 작업마다 적은 개수
- 파일 몇 개만: `flutter test <test 경로들> --timeout 20s`
- 골든: `flutter test --update-goldens <골든 테스트 경로>` — 이 계획의 골든 테스트와 **의도한 변경(작업 8 의 UI 5건)**에만 쓴다. 그 밖의 기존 골든이 바뀌면 멈추고 보고한다.
- 네이티브 빌드(작업 6): `flutter build ios --simulator`, `flutter build apk --debug`

## 이 계획에서 새로 정한 것

설계와 모순되는 것은 없다. 설계 7절의 빈틈을 사용자와 정한 것(1~3)과 가장 작게 메운 것, 참조 구현을 만들며 정한 것이다. 마지막 작업에서 결정 기록 006 에 옮긴다.

1. **③-A2 가 남긴 사용자 판단 6건을 이 계획에서 끝낸다**(사용자 결정 2026-09-24): 등록·다음 예약 ②의 `VISIT_DUPLICATE`는 스낵바 문구로 알리고 닫는다, 상태가 섞인 가족 카드는 아이별 상태와 진행 가능한 버튼을 보인다, 보호자 탭의 노쇼 카드는 "노쇼 횟수 / N회", 시간 칸은 휴무·영업 밖(옅은 바탕)과 겹침(줄긋기)이 다르게 보인다, 미리보기는 4줄 뒤 "외 N건", 30분 블록은 이름 뒤에 메뉴를 같은 줄에 잇는다.
2. **공유 받기는 직접 쓴다**(사용자 결정): iOS Share Extension(Swift, `UIViewController`, 글만 App Group 에 저장 → URL 스킴 `chagocnote://share`로 본체 열기) + 안드로이드 `ACTION_SEND` `text/plain` intent-filter(`launchMode="singleTask"`). Dart 와는 `MethodChannel('com.chagocnote.app/share')` 하나(`getPending` / `onSharedText`). 패키지 `receive_sharing_intent`는 사진·파일까지 딸려 오고 Flutter 대판 갱신 뒤 깨진 이력이 있어 기각했다 — 사진 받기가 ④에 확실히 들어오면 다시 본다.
3. **초안 화면은 하나다(A안, 사용자 결정)**: 붙여넣기든 공유든 `/visits/draft`로 온다. 받은 글(3줄, 눌러 펼침) + 보호자 후보(하나면 고른 상태, 여럿이면 골라야 함, 없으면 [고객 찾기]) + 날짜·시작·메뉴 줄(짐작이면 "짐작" 칩) + [예약 이어서]. 기존 예약 ①·② 폼은 `VisitPrefill`을 받는 것 외에 바꾸지 않는다.
4. **`VisitPrefill`(앱)** — 초안이 예약 폼에 넘기는 값(보호자 ID·날짜·시각·반려동물·메뉴). `NextVisitDraft`(다음 예약)와 별개다: 다음 예약은 소요·주기까지 확정값이고, 카톡 초안은 비어 있을 수 있는 짐작값이라 폼의 규칙이 다르다(메뉴가 있으면 "지난번처럼"으로 덮어쓰지 않되 안내 문구는 없음, 반려동물은 후보의 `matched_pet_ids`만).
5. **후보 순위**(customer 구현): 반려동물 이름 정확 일치 → 보호자 이름 정확 일치 → 전화(8자리 이상 포함, 4자리는 뒷자리) → 부분 일치, 같은 순위면 `customer_id` 오름차순, 최대 5가족. 익명화한 고객과 무지개다리 아이는 뺀다. `guessed.who`는 후보가 정확히 하나가 아니거나 하나인데 정확 일치가 아닐 때다. `pet_ids`는 후보가 정확히 하나일 때만 그 후보의 `matched_pet_ids`.
6. **낱말 나누기**(visit 도메인): 한글 연속 토큰과 숫자 토큰(4자리 = 뒷자리, 8자리 이상 = 전화). 한글 토큰은 원형과 끝 조사를 뗀 형을 함께 넣는다(맞는 조사를 모두 떼어 본다 — 콩이랑 → 콩이랑·콩·콩이, 15 참고). 날짜·시간·인사·메뉴 낱말은 상수 집합으로 뺀다. 중복 제거, 최대 20개. OR 검색은 `CustomerSearchPort.match_any(ctx, words, limit)`(기존 `search`는 AND 라 새 메서드).
7. **날짜·시간 해석의 짐작 규칙**(설계 7절 보완): `다음 주 X요일`·`D일`(달 없음)·오늘보다 앞인 `M월 D일`/`M/D`(내년으로) 는 짐작. 시각 표지(오전·오후·저녁·밤·낮·아침) 없이 H<12 이면 H 와 H+12 가운데 영업시간 안쪽을 고르고 항상 짐작(`14:00` 같은 24시 표기는 짐작 아님). `HH:MM`도 H<12 이고 표지 없으면 같은 짐작. 존재하지 않는 날짜·25시·60분은 무시(None). 여러 표현이 있으면 우선순위 표의 첫 히트.
8. **메뉴 일치**: 보관 안 된 메뉴 이름을 글이 포함하면(공백을 지운 뒤 맞으면 `guessed.menu`). 메뉴표 순서.
9. **초안 요청의 권한은 `reservation:write`**(예약을 만들 사람만). 설정 행이 없으면 `ensure`로 만든다(하루 목록과 같다).
10. **공유로 받은 글은 로그인·매장 선택 뒤에 연다.** 앱이 꺼져 있을 때 공유되면(콜드 스타트) 네이티브가 글을 들고 있다가 Dart 의 `getPending`에 주고, Dart 는 세션이 `SignedIn`이고 매장이 골라진 뒤 `/visits/draft`를 연다. 1000자를 넘는 글은 앞 1000자만(서버 제한).
11. **스낵바 관례를 만든다**(`AppSnackBar.show`, `design/widgets`) — 검정 바탕·흰 글자·둥근 모서리·floating. 처음 쓰는 곳은 `VISIT_DUPLICATE`. 문구는 "이미 같은 시각에 잡힌 예약이 있어요. 그날 목록을 확인해 주세요."(저장 두 번과, 다음 예약 ②에서 한 아이가 이미 예약된 경우 — 그때는 서버가 전체를 되돌려 아무것도 저장되지 않았다 — 둘 다).
12. **섞인 상태 가족 카드의 버튼은 "진행 가능한 구성원 집합"으로**: 예약됨인 아이들만 [시작], 미용 중인 아이들만 [완료하기]. 집합의 상태가 하나가 아니거나(예약됨+미용 중) 비어 있으면(완료·취소·노쇼만) 칩. 보내는 `ids`는 그 집합뿐이다(V14 — 상태가 다른 형제를 섞지 않는다).
13. **응답 `time`은 `HH:MM`이다**(pydantic 기본 `HH:MM:SS`가 아니라 — 앱이 시간 칸의 `at`로 그대로 쓴다). 스키마의 `field_serializer` 한 줄.
14. **카톡 대화를 여러 줄 복사하면 붙는 머리말 `[김민지] [오후 2:31]`의 시각은 지우고 해석한다.** 보낸 사람 이름은 낱말로 남긴다(보호자 이름일 수 있다). 위협 점검표 A12.
15. **한 글자 낱말은 버리지 않고 통단어로만 찾는다.** "봄"·"달" 같은 한 글자 이름의 아이를 후보에서 놓치지 않으려는 것이다 — 흔한 한 글자 말(저·그·좀·꼭…)만 불용어로 뺀다. `match_any`는 한 글자 텍스트 낱말을 `' ' || terms || ' ' LIKE '% 봄 %'`로 찾는다. 조사는 맞는 것을 **모두** 떼어 본다("콩이랑" → 콩이랑·콩·콩이). 숫자에 바로 붙은 한글("2시에", "5678이요")은 숫자 토큰이 삼킨다.
16. **`D일`(달 없음)은 이번 달에 없거나 지났으면 다음 달까지만 본다**(2/30 → 3/30, 둘 다 없으면 없음). 표지 없는 시각은 12시 이후("15시")도 짐작함이고, `HH:MM`은 12시 이후면 확정이다. "N시간"의 "시"는 시각이 아니다.
17. **초안 화면의 [예약 이어서]는 메뉴표(`menusProvider`)를 기다린 뒤 연다.** 기다리지 않으면 화면이 뜨자마자 누를 때 글의 메뉴가 빠진다. 기다리는 동안 버튼은 `busy`, 두 번 눌리지 않는다. 메뉴표를 못 읽으면 메뉴 없이 넘긴다.
18. **iOS 는 `SceneDelegate.swift`를 손대지 않는다.** `AppDelegate.swift` 안의 `SharedTextPlugin`(`FlutterPlugin` + `FlutterSceneLifeCycleDelegate`, `registrar.addSceneDelegate`)이 씬의 URL 열림(콜드 스타트는 연결 옵션, 떠 있으면 `openURLContexts`)을 받는다. `getPending`은 들고 있던 글이 없으면 App Group 을 한 번 더 본다(연결 옵션을 놓친 경우의 안전망). 안드로이드 `launchMode`는 `singleTask`(공유가 다른 앱의 태스크에 새 액티비티를 만들지 않게).
19. **후보 읽기는 `CustomerRepository.list_active`로**(전화 원본이 필요하고 익명화 제외가 저절로 된다) — `FamilyBriefRepository`가 아니다. 인터랙터 생성자는 그대로다. 방문 상세의 "노쇼 N회"는 그대로 두고 보호자 탭 카드만 "노쇼 횟수 / N회"다.

## 이 계획의 코드는 어떻게 검증했나

②-2·③-A1·③-A2 와 같은 방식이다. **이 계획서의 코드는 저장소 안의 임시 작업 트리에서 실제로 만들어 돌린 것을 그대로 옮겼다.**

- 작업 트리(git 무시 대상): `.superpowers/ref/wt-visit-3a3-app`(브랜치 `ref/visit-3a3`, `main` `5072504`에서 땄다). 백엔드(작업 1~3)와 앱(작업 4~8)을 별도 작업 트리에서 포크 에이전트 둘이 병렬로 만든 뒤 한 브랜치로 합쳤다. 계획서의 코드 블록과 diff 는 이 브랜치의 작업별 커밋 8개에서 기계적으로 뽑았다(생성기 `build_plan.py`, 세션 스크래치패드).
- 백엔드 테스트는 작업 트리의 `infra/`에서 `docker compose -p chagocnote run --rm --no-deps backend …`로 돌렸다 — 프로젝트 이름을 개발 스택과 같게 주면 컨테이너가 그 스택의 네트워크(pgvector·redis)에 붙고 코드는 작업 트리 것을 마운트한다. **단위·통합·구조 계약 모두 돌렸다.** 흐름 스크립트(게이트웨이 = 개발 스택의 `main` 코드)와 라우트 표는 돌리지 못했다 — Task 3 에서 실행자가 돌린다.
- 앱은 작업마다 `flutter analyze`·`flutter test --timeout 30s`를 돌리고 커밋했다. 작업 6 은 `flutter build ios --simulator`와 `flutter build apk --debug`까지.

  | 작업 | 그 작업의 테스트 | 전체 | 그 밖 |
  |---|---|---|---|
  | 기준(`main` `5072504`) | — | 앱 476 / 백엔드 단위 627·통합 254 | 계약 6 kept |
  | 1(백엔드) | customer 인터랙터 7 + pg 어댑터 4(통합) | 단위 634·통합 258 | 6 kept |
  | 2(백엔드) | 해석기 73(표 기반) | 단위 707 | 6 kept |
  | 3(백엔드) | 인터랙터 8 + 라우터 4 + 통합 3 | 단위 719·통합 261 | 6 kept, 흐름 스크립트·라우트 표는 미실행 |
  | 4(앱) | API 2 + 예약 화면 4 | 482 | analyze 0 |
  | 5(앱) | 초안 화면 7 | 489 | analyze 0 |
  | 6(앱) | 채널 4 + 관문 3 | 496 | analyze 0, iOS 시뮬레이터 빌드·APK 빌드 통과 |
  | 7(앱) | 스낵바 1 + 예약 화면 1(+기존 1 확장) | 497 | analyze 0 |
  | 8(앱) | 하루 1 + 캘린더 1(+기존 3 확장) | 500 | analyze 0, 골든 `register_visit_form.png` 갱신(의도) |
- **변이로 판별력을 확인했다.** 각 작업의 "판별력 확인" 단계가 그 변이들이다 — 방어 코드를 하나씩 빼면 적힌 테스트가 실패한다. 한 번 판별력이 없던 것(`(?<!\d)` 경계, 로그인·매장 관문)은 테스트를 더해 판별하게 했다.
- 참조 구현이 계획 초안을 바꾼 것(아래 "새로 정한 것" 13~19): 응답 `time`을 `HH:MM`으로 직렬화, 카톡 머리말 시각 제거, 한 글자 이름의 통단어 검색, 초안 화면이 메뉴표를 기다림, 조사를 모두 떼어 봄, `SceneDelegate`는 손대지 않고 `AppDelegate`의 플러그인이 URL 을 받음, 안드로이드 `singleTask`.
- **검증하지 않은 것 — Task 9 에서 실행자가 사용자와 확인한다:** 실제 백엔드·게이트웨이에 붙은 앱의 붙여넣기 초안 흐름(참조 구현은 가짜 HTTP 어댑터로만 돌렸다), iOS 공유 확장·안드로이드 공유(시뮬레이터엔 카톡이 없고 코드사인 없이는 App Group 이 붙는지 알 수 없다 — **실기기**), 카톡이 넘기는 글의 실제 형태(보낸 사람·시각이 붙는지), 응답자 체인 `openURL:` 우회가 현재 iOS 에서 되는지.

그래도 규칙은 같다. **검토자는 이 계획서의 코드를 검토되지 않은 것으로 본다.** 작업 트리는 "컴파일되고 자기 테스트를 통과한다"까지만 보장한다. 테스트가 옳은 것을 확인하는지, 빠진 시나리오가 없는지는 아래 위협 점검표와 설계를 기준으로 판단한다.

수정하는 기존 파일은 `diff` 블록으로 보인다 — `-` 줄을 지우고 `+` 줄을 더한다. 줄 번호(`@@`)는 앞 작업이 끝난 상태 기준이다. 골든 png 는 이 문서에 넣지 않는다 — 그 작업의 골든 테스트를 `--update-goldens`로 돌려 만들고 눈으로 본다.

## 위협 점검표

설계 10절의 이 계획 몫(V1·V9·V12)과, 참조 구현을 만들며 찾은 A1~A12 다. **구현자와 검토자는 이 표를 코드와 대조한다. 표에 없는 시나리오를 찾으면 보고한다.**

| # | 시나리오 | 막는 것 | 확인하는 테스트 |
|---|---|---|---|
| V1 | B매장의 가족이 A매장 초안의 후보에 오른다 | `match_any`가 검색 줄의 `shop_id`로 거르고, 후보 읽기도 `ShopContext`를 거친다 | Task 1 통합 `match_any_는_다른_매장과_익명화한_가족을_찾지_않고…`, Task 3 통합 `다른_매장의_가족은_후보에_오르지_않는다` |
| V9 | 카톡 글(개인정보)이 로그·DB·오류 응답에 남는다 | 저장 없음(`ensure` 외 쓰기 없음), `logging` 호출 없음, 422·403 본문에 글 없음, 접근 로그는 본문을 쓰지 않음, 앱은 글을 저장·출력하지 않음 | Task 3 `빈_글_긴_글_제어_문자는_422_이고_글을_되돌려주지_않는다`·`reservation_write_가_없으면_403_이고_글을_되돌려주지_않는다`·통합 `실제_배선으로_후보_메뉴_날짜_시각을_채운다`(`caplog` DEBUG 에 낱말 없음)·`직원도_초안을_받고_초안은_아무것도_저장하지_않는다` |
| V12 | 공유 확장이 토큰에 접근한다 | 확장은 App Group 에 글만 적고 URL 스킴으로 본체를 연다. `ShareViewController.swift`의 import 는 `UIKit`·`UniformTypeIdentifiers`뿐이고 키체인·네트워크 코드가 없다. 서버 호출은 본체의 Dart | 자동 테스트 없음 — Task 6 검토자가 Swift 파일을 눈으로 확인하고, Task 9 실기기 확인 |
| A1 | 초안이 다른 집 아이를 예약 폼에 넘긴다(후보와 `pet_ids`가 어긋남) | 폼의 `_initPets`가 그 보호자의 아이만 남긴다. 서버 등록은 `lock_family`가 다시 확인한다(③-A1) | Task 4 `카톡 초안이 넘긴 아이가 이 보호자의 아이가 아니면 버리고, 하나뿐인 아이를 고른다` |
| A2 | 후보가 여럿인데 첫 후보로 자동 진행한다 | 여럿이면 고르기 전까지 [예약 이어서] 비활성, "짐작" 칩 | Task 5 `후보가 여럿이면 골라야 [예약 이어서]가 열리고, 고른 보호자의 ②로 간다` |
| A3 | 공유로 받은 글이 로그아웃 상태에서 열려 로그인 화면 뒤로 사라지거나, 세션이 바뀔 때마다 다시 열린다 | 관문 프로바이더(`SignedIn` + 매장 선택)에서만 열고, 한 번 열면 `clear` | Task 6 `로그아웃 상태에서는 받아 둔 글을 열지 않고 들고 있다가, 로그인·매장 선택 뒤에 연다`·`앱이 떠 있을 때 공유가 오면 초안 화면을 연다`·`앱이 뜨기 전에 받아 둔 글(콜드 스타트)은…` |
| A4 | 1000자 넘는 글로 422 | 붙여넣기·공유·확장 셋 다 앞 1000자만 | Task 5 `붙여넣은 글이 1000자를 넘으면 앞 1000자만 보낸다`, Task 6 `빈 글은 무시하고, 1000자를 넘으면 앞 1000자만 둔다` |
| A5 | 낱말이 없는 글(숫자·이모지·불용어만)로 허브 포트를 불러 빈 OR 검색이 나간다 | `words`가 비면 포트를 부르지 않고, `match_any`도 빈 낱말에 빈 목록 | Task 3 `낱말이_없으면_후보를_묻지_않는다`, Task 1 `낱말이_없으면_검색을_부르지_않고_빈_목록이다` |
| A6 | 낱말 하나에 수십 가족이 걸려 후보가 넘치거나 느려진다 | `match_any` limit 20 → 순위 뒤 5 | Task 1 `후보는_다섯_가족까지_ID_오름차순이다`·`검색은_낱말을_OR_로_20가족까지_묻는다` |
| A7 | LIKE 특수 문자(`%`·`_`·`\`)가 든 글이 모든 가족에 걸린다 | `_like_escape` | Task 1 통합 `match_any_도_LIKE_특수_문자를_글자_그대로_찾는다` |
| A8 | 표지 없는 시각("2시")을 확정으로 보여 잘못된 시각에 저장한다 | 영업시간 안쪽으로 짐작하되 늘 "짐작"으로 표시, 저장은 ②에서 사람이 확인 | Task 2 `시각_표현`·`표지_없는_시각은_영업시간에_따라_다르게_읽는다`, Task 5 `후보가 하나면 고른 상태로 보이고 짐작한 칸에 표시가 붙으며…` |
| A9 | 상태가 섞인 카드의 버튼이 완료·취소한 아이까지 보내 409 | `DayGroup.actionableIds`만 보낸다(V14) | Task 8 `상태가 섞인 가족 카드는 아이별 상태를 적고, 아직 진행 가능한 아이만 버튼으로 보낸다` |
| A10 | 다음 예약 ②에서 한 아이가 이미 예약돼 있어 아무것도 저장되지 않았는데 조용히 닫힌다 | 스낵바 문구 뒤 닫기 | Task 7 `다음 예약 초안의 저장이 VISIT_DUPLICATE 면(한 아이가 이미 예약됨) 문구를 보이고 닫는다` |
| A11 | 입력 경계에서 500 — 1001자·제어 문자·빈 글·"25시"·"2/30"·"99일"·"123일" | 본문은 pydantic 422, 해석기는 없는 값을 `None`으로 | Task 3 `빈_글_긴_글_제어_문자는_422_이고…`, Task 2 표의 `25시`·`2/30`·`123일`·`달_없는_날짜는_이번_달_아니면_다음_달까지만_본다` |
| A12 | 카톡 대화를 여러 줄 복사하면 붙는 머리말 `[김민지] [오후 2:31]`의 시각이 예약 시각으로 잡힌다 | 해석 전에 `[오전/오후 H:MM]` 머리말을 지운다(보낸 사람 이름은 낱말로 남긴다) | Task 2 `시각_표현[[김민지] [오후 2:31] 내일 3시 콩이 목욕]`·`누구_낱말[[김민지] [오후 2:31] 콩이 내일요]` |

**이 계획으로도 남는 것 (Task 9 에서 결정 기록에 적는다):**
- 해석은 규칙이다 — "다다음 주", "2주 뒤", "점심때", "오픈 시간에", "저녁 늦게" 같은 표현은 못 읽는다(빈 칸으로 두고 사람이 채운다). ⑨ 뒤 LLM 어댑터의 몫.
- 낱말이 불용어 집합 밖의 흔한 말("부탁드려요", "가능할까요")까지 OR 검색에 들어간다 — 이름과 겹칠 때만 부분 일치 후보가 되고, 정확 일치가 앞서므로 해가 없다. 한 글자 낱말은 통단어로만 찾는다.
- "X이"에서 조사 "이"를 뗀 "X"도 낱말이라("콩이" → "콩") 한 글자 이름 "콩"을 찾는다 — 대신 낱말 목록에 한 글자 형이 늘 하나 더 든다.
- 초안 화면의 [예약 이어서]는 메뉴표를 기다린다. 메뉴표를 못 읽으면(오류) 메뉴 없이 ②로 간다 — ②가 메뉴표를 다시 부른다.
- 다음 예약·카톡 초안·클립보드 글은 메모리에만 있다. 초안 화면의 `visitDraftProvider` 키에 글이 들어 있으나 `autoDispose`라 화면을 떠나면 버린다.
- iOS 공유 확장의 "본체 열기"는 애플이 공식으로 열어 두지 않은 응답자 체인 `openURL:` 우회다. iOS 갱신으로 막히면 확장이 글만 남기고 본체를 못 열 수 있다 — 그때는 사용자가 앱을 열면 `getPending`의 App Group 안전망이 글을 집어 온다.
- 시뮬레이터 빌드는 코드사인이 없어 App Group entitlement 가 실제로 붙는지 확인하지 못한다 — 실기기(개발 팀 서명)에서 본다(Task 9).
- 안드로이드 `launchMode`를 `singleTop`에서 `singleTask`로 바꿨다 — 공유가 다른 앱의 태스크에 새 액티비티를 만들지 않게. 앱 링크·알림(⑥) 설계 때 다시 본다.
- 방문 상세의 "노쇼 N회"(`noShowCount`)는 그대로다 — 보호자 탭 카드만 "노쇼 횟수 / N회"로 바꿨다.
- 초안 요청은 첫 호출에서 매장 설정 행과 기본 메뉴를 만든다(`ensure`) — 하루 목록과 같은 부작용이다.

## Review Focus

설계가 말하지 않지만 사람이 쓰면 만나는 입력이다. 각 줄의 테스트는 그 작업에 들어 있다.

1. **카톡 대화를 여러 줄 복사한 글** — `[김민지] [오후 2:31] 내일 3시 콩이 목욕`: 머리말의 시각이 아니라 본문의 3시를 읽고, 보낸 사람 이름은 후보 낱말로 남아야 한다 → Task 2 `시각_표현[[김민지] [오후 2:31] …]`·`누구_낱말[[김민지] [오후 2:31] 콩이 내일요]`.
2. **한 글자 이름의 아이("봄"·"달")** — 이름이 한 글자라고 후보에서 빠지면 안 되고, 그 글자가 든 다른 이름("봄이")이 함께 걸려도 안 된다 → Task 2 `누구_낱말[봄 내일 갈게요]`, Task 1 통합 `한_글자_낱말은_통단어로만_찾는다`.
3. **메뉴표를 아직 못 읽은 채 [예약 이어서]** — 초안 화면이 뜨자마자 누르면 글에 있던 메뉴가 빠진 채 ②가 열리면 안 된다 → Task 5 `메뉴표를 아직 못 읽었으면 [예약 이어서]가 메뉴표를 기다린 뒤 메뉴를 채워 연다`.
4. **"2시간 걸려요"처럼 시각이 아닌 "시"** — 소요·기간의 "시간"을 시각으로 읽으면 안 된다 → Task 2 `시각_표현[2시간 걸려요]`·`[오후 2시간쯤 뒤 4시]`.
5. **후보는 없고 날짜·시각만 있는 글**("내일 2시 가능한가요") — 글이 버려지지 않고 [고객 찾기] → ①에서 고른 뒤 ②에 날짜·시각이 채워져야 한다 → Task 5 `후보가 없으면 [고객 찾기]로 ①에 가고, 고른 뒤 ②가 초안의 날짜·시각·메뉴로 채워진다`, Task 4 `카톡 초안(보호자 없음)으로 열면 ①에서 고른 뒤 ②가 초안의 날짜·시각·메뉴로 채워진다`.

---

### Task 1: 허브 포트 `find_draft_candidates`와 customer 구현(낱말 OR 검색, 순위, 최대 5 가족)

**Files:**
- Create: `backend/apps/hub/app/dtos/draft_candidate.py`
- Modify: `backend/apps/hub/app/ports/customer_directory_port.py`
- Modify: `backend/apps/customer/app/ports/output/customer_search_port.py`
- Modify: `backend/apps/customer/_docs/CLAUDE.md`
- Modify: `backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py`
- Modify: `backend/apps/customer/app/use_cases/customer_directory_interactor.py`
- Modify: `backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`
- Modify: `backend/apps/customer/tests/helpers/fakes.py`
- Modify: `backend/apps/hub/_docs/CLAUDE.md`

**Interfaces:**
- Consumes: 기존 `CustomerDirectoryPort`(hub), `CustomerDirectoryInteractor`(customer — `customers`·`pets`·`briefs`·`search` 생성자 그대로), `CustomerSearchPgAdapter._like_escape`·`Entry`, `parse_query`(`search_terms.py`), `mask_phone`.
- Produces: `hub.app.dtos.draft_candidate.DraftCandidate(customer: CustomerBrief, pets: tuple[PetBrief, ...], matched_pet_ids: tuple[int, ...], exact: bool)`; `CustomerDirectoryPort.find_draft_candidates(ctx, words: tuple[str, ...]) -> list[DraftCandidate]`(Task 3 의 인터랙터가 부른다); `CustomerSearchPort.match_any(ctx, words: tuple[SearchWord, ...], limit: int) -> list[int]`; customer 스텁 `FakeSearch.match_any`(`match_any_ids` 속성, journal `("match_any", words, limit)`).

허브 포트에 메서드 하나를 더한다. visit 의 `FakeDirectory`(`visit/tests/helpers/fakes.py`)는 Task 3 에서 넓힌다 — 이 작업이 끝난 시점에는 ABC 에 추상 메서드가 늘어도 visit 테스트의 스텁은 ABC 를 상속하지 않아 그대로 통과한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py`:

```diff
@@ -236,3 +236,46 @@ async def test_최근_방문순의_커서를_다른_정렬에_쓰면_VALIDATION_
     page = await _find(db_session, "", sort="last_visit", limit=1)
     with pytest.raises(CustomerInputError):
         await _find(db_session, "", sort="recent", cursor=page.next_cursor)
+
+
+# --- 카톡 초안 후보 — 낱말 하나라도 걸리는 가족(match_any) ---
+
+
+async def _any(session, q, shop=A, limit=20):
+    return await CustomerSearchPgAdapter(session).match_any(shop, parse_query(q), limit=limit)
+
+
+async def test_낱말_하나라도_걸리면_고객_ID_오름차순으로_찾는다(db_session):
+    kong = await _family(db_session, "김민지", "01012345678", ["콩이"])
+    dubu = await _family(db_session, "박서준", "01098765678", ["두부"])
+    await _family(db_session, "이하나", "01011112222", ["구름"])
+    assert await _any(db_session, "두부 콩이 없는이름") == [kong, dubu]
+    assert await _any(db_session, "5678") == [kong, dubu]              # 뒷자리
+    assert await _any(db_session, "01098765678") == [dubu]             # 전체 번호
+    assert await _any(db_session, "두부 콩이", limit=1) == [kong]
+    assert await _any(db_session, "") == []
+
+
+async def test_match_any_는_다른_매장과_익명화한_가족을_찾지_않고_무지개다리만_남은_가족은_찾는다(db_session):
+    await _family(db_session, "김민지", "01012345678", ["콩이"], shop=B)
+    gone = await _family(db_session, "박서준", "01098765678", ["콩이"])
+    await CustomerPgRepository(db_session).anonymize(A, gone)
+    await CustomerSearchPgAdapter(db_session).rebuild_search_entry(A, gone)
+    passed = await _family(db_session, "이하나", "01011112222", ["콩이"])
+    pet_id = (await PetPgRepository(db_session).list_for_customers(A, [passed]))[0].id
+    await PetPgRepository(db_session).set_passed_away(A, pet_id, True)
+    assert await _any(db_session, "콩이") == [passed]
+
+
+async def test_한_글자_낱말은_통단어로만_찾는다(db_session):
+    bom = await _family(db_session, "김민지", "01012345678", ["봄"])
+    bomi = await _family(db_session, "박서준", "01098765678", ["봄이"])
+    assert await _any(db_session, "봄") == [bom]          # "봄이"·"봄" 둘 다가 아니라 통단어 "봄"만
+    assert await _any(db_session, "봄이") == [bomi]
+
+
+async def test_match_any_도_LIKE_특수_문자를_글자_그대로_찾는다(db_session):
+    percent = await _family(db_session, "100%보호자", "01012345678", ["콩이"])
+    await _family(db_session, "김민지", "01098765678", ["두부"])
+    assert await _any(db_session, "%보") == [percent]   # "%" 는 글자 그대로(두 글자라 부분 일치)
+    assert await _any(db_session, "\\") == []
```

`backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`:

```diff
@@ -88,3 +88,78 @@ async def test_마지막_방문_시각은_검색_포트로_넘긴다():
     await directory.set_last_visit(ctx(), 1, at)
     await directory.set_last_visit(ctx(), 1, None)
     assert journal == [("set_last_visit", 1, at), ("set_last_visit", 1, None)]
+
+
+# --- 카톡 초안 후보(find_draft_candidates) ---
+
+
+def _directory_with_search():
+    journal, customers, pets, _, search = family()
+    return journal, customers, pets, search, CustomerDirectoryInteractor(customers, pets, _FakeBriefs(), search)
+
+
+async def test_낱말이_없으면_검색을_부르지_않고_빈_목록이다():
+    journal, _, _, _, directory = _directory_with_search()
+    assert await directory.find_draft_candidates(ctx(), ()) == []
+    assert journal == []
+
+
+async def test_반려동물_이름_정확_일치가_보호자_이름_전화_부분_일치보다_앞선다():
+    _, customers, pets, search, directory = _directory_with_search()
+    partial = customers.seed(name="콩순이맘", phone="01000000001")     # "콩" 부분 일치뿐
+    by_phone = customers.seed(name="박서준", phone="01098765678")      # 뒷자리 5678
+    by_owner = customers.seed(name="김민지", phone="01000000003")      # 보호자 이름
+    by_pet = customers.seed(name="이하나", phone="01000000004")        # 반려동물 이름
+    pets.seed(by_pet.id, "콩이"), pets.seed(by_pet.id, "두부"), pets.seed(partial.id, "콩")
+    search.matches = [partial.id, by_phone.id, by_owner.id, by_pet.id]
+
+    found = await directory.find_draft_candidates(ctx(), ("콩이", "김민지", "5678"))
+
+    assert [c.customer.customer_id for c in found] == [by_pet.id, by_owner.id, by_phone.id, partial.id]
+    assert [c.exact for c in found] == [True, True, False, False]
+    kong = next(p.id for p in pets.rows.values() if p.name == "콩이")
+    assert found[0].matched_pet_ids == (kong,)
+    assert [p.name for p in found[0].pets] == ["콩이", "두부"]
+    assert found[0].customer.phone_masked == "010-00··-0004"
+
+
+async def test_전체_번호_8자리_이상은_포함으로_맞춘다():
+    _, customers, _, search, directory = _directory_with_search()
+    customer = customers.seed(name="박서준", phone="01098765678")
+    search.matches = [customer.id]
+    found = await directory.find_draft_candidates(ctx(), ("01098765678",))
+    assert (found[0].customer.customer_id, found[0].exact) == (customer.id, False)
+
+
+async def test_후보는_다섯_가족까지_ID_오름차순이다():
+    _, customers, _, search, directory = _directory_with_search()
+    ids = [customers.seed(name=f"보호자{i}", phone=f"0100000000{i}").id for i in range(7)]
+    search.matches = ids
+    found = await directory.find_draft_candidates(ctx(), ("보호자",))
+    assert [c.customer.customer_id for c in found] == ids[:5]
+
+
+async def test_검색은_낱말을_OR_로_20가족까지_묻는다():
+    journal, _, _, _, directory = _directory_with_search()
+    await directory.find_draft_candidates(ctx(), ("콩이", "010-1234-5678"))
+    assert journal == [("match_any", ("콩이", "01012345678"), 20)]
+
+
+async def test_무지개다리_아이는_후보의_반려동물에서_빠진다():
+    _, customers, pets, search, directory = _directory_with_search()
+    customer = customers.seed()
+    pets.seed(customer.id, "콩이", passed_away=True)
+    pets.seed(customer.id, "두부")
+    search.matches = [customer.id]
+    found = await directory.find_draft_candidates(ctx(), ("콩이",))
+    assert [p.name for p in found[0].pets] == ["두부"]
+    assert (found[0].matched_pet_ids, found[0].exact) == ((), False)   # 무지개다리 아이의 이름은 일치로 치지 않는다
+
+
+async def test_익명화한_고객과_다른_매장의_ID_는_후보가_아니다():
+    _, customers, _, search, directory = _directory_with_search()
+    gone = customers.seed()
+    other = customers.seed(shop_id=2, phone="01099990000")
+    await customers.anonymize(ctx(), gone.id)
+    search.matches = [gone.id, other.id]
+    assert await directory.find_draft_candidates(ctx(), ("김민지",)) == []
```

`backend/apps/customer/tests/helpers/fakes.py`:

```diff
@@ -167,6 +167,7 @@ class FakeSearch:
         self.page = page or SearchPage(customer_ids=[], next_cursor=None)
         self.pet_count = pet_count
         self.requests = []
+        self.matches: list[int] = []
 
     async def rebuild_search_entry(self, ctx, customer_id):
         self.journal.append(("rebuild", customer_id))
@@ -182,6 +183,11 @@ class FakeSearch:
         self.requests.append((ctx, words, include_passed))
         return self.pet_count
 
+    async def match_any(self, ctx, words, limit):
+        """낱말 하나라도 걸리는 가족 — 스텁은 미리 넣어 둔 ID 를 그대로 준다(순위는 인터랙터 몫)."""
+        self.journal.append(("match_any", tuple(w.value for w in words), limit))
+        return self.matches[:limit]
+
 
 class FakeLedger:
     """VisitLedgerPort 스텁. 반려동물·고객마다 방문이 있는지, 앞으로의 예약이 있는지를 정해 둔다."""
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/customer/tests/app/use_cases/test_customer_directory_interactor.py -q -p no:cacheprovider`
Expected: 새 테스트 7개가 `AttributeError`(`find_draft_candidates`·`match_any` 없음)로 실패, 기존 8개 통과.

Run (`infra/`): `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_search_pg_adapter.py -q -p no:cacheprovider -m integration`
Expected: `match_any` 테스트 4개 `AttributeError` 로 실패, 나머지 26개 통과.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/dtos/draft_candidate.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.family_brief import CustomerBrief, PetBrief


@dataclass(frozen=True)
class DraftCandidate:
    """카톡 예약 초안의 "누구" 후보 — 글의 낱말에 걸린 가족 하나.

    pets 는 무지개다리를 건너지 않은 아이만이다. matched_pet_ids 는 글의 낱말과 이름이 정확히 같은 아이,
    exact 는 반려동물이나 보호자 이름이 정확히 일치했는지(아니면 전화·부분 일치)다.
    """

    customer: CustomerBrief
    pets: tuple[PetBrief, ...]
    matched_pet_ids: tuple[int, ...]
    exact: bool
```

`backend/apps/hub/app/ports/customer_directory_port.py`:

```diff
@@ -3,12 +3,13 @@ from __future__ import annotations
 from abc import ABC, abstractmethod
 from datetime import datetime
 
+from hub.app.dtos.draft_candidate import DraftCandidate
 from hub.app.dtos.family_brief import FamilyBriefs
 from hub.app.dtos.shop_context import ShopContext
 
 
 class CustomerDirectoryPort(ABC):
-    """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순)."""
+    """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순, 카톡 초안 후보)."""
 
     @abstractmethod
     async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
@@ -29,3 +30,12 @@ class CustomerDirectoryPort(ABC):
     @abstractmethod
     async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
         """고객 목록 '최근 방문순'의 키를 바꾼다. 원본(visits)에서 다시 계산한 값을 같은 트랜잭션에서 넘긴다."""
+
+    @abstractmethod
+    async def find_draft_candidates(self, ctx: ShopContext, words: tuple[str, ...]) -> list[DraftCandidate]:
+        """카톡 예약 초안의 "누구" 후보. 낱말 하나라도 걸리는 이 매장의 가족을 최대 5 가족 돌려준다.
+
+        순서는 반려동물 이름 정확 일치 → 보호자 이름 정확 일치 → 전화(8자리 이상 포함 / 4자리 뒷자리) → 부분 일치,
+        같은 순위면 고객 ID 오름차순. 익명화한 고객은 후보가 아니고, 무지개다리를 건넌 아이는 pets 에서 뺀다.
+        낱말은 저장하지도 로그에 남기지도 않는다(설계 10절 V9).
+        """
```

`backend/apps/customer/app/ports/output/customer_search_port.py`:

```diff
@@ -37,3 +37,11 @@ class CustomerSearchPort(ABC):
         self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool
     ) -> int:
         """검색에 걸린 가족들의 반려동물 수(목록 제목의 'N마리'). 쪽과 상관없이 전체를 센다."""
+
+    @abstractmethod
+    async def match_any(self, ctx: ShopContext, words: tuple[SearchWord, ...], limit: int) -> list[int]:
+        """낱말 **하나라도** 걸리는(OR) 이 매장의 가족(검색 줄이 있는 = 익명화하지 않은)의 고객 ID.
+
+        고객 ID 오름차순으로 limit 개까지. 무지개다리만 남은 가족도 든다(보호자만의 예약이 있다).
+        카톡 초안의 후보 찾기가 쓴다 — 순위는 부르는 쪽이 이름을 읽어 매긴다.
+        """
```

`backend/apps/customer/_docs/CLAUDE.md`:

```diff
@@ -13,5 +13,5 @@
 - 목록과 반려동물 상세의 번호는 가린다(`010-12··-5678`). 전체 번호는 고객 상세에서만 준다. 전화번호·이름을 로그에 남기지 않는다. 검색어와 번호 조회는 쿼리 문자열로 오므로 API 프로세스가 접근 로그의 쿼리를 가린다(`core/access_log.py`).
 - 고객 삭제는 익명화다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행을 지우고 `deleted_at`을 찍는다. 행과 틀(종류·품종·성별 등)은 남긴다. 익명화한 고객은 모든 조회·검색·번호 조회에서 없는 것으로 본다.
 - 반려동물은 질병을 하나 이상 고르거나 "질병 없음"을 직접 확인해야 저장된다(두 표에 걸친 규칙이라 도메인이 확인한다). 질병 종류는 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다.
-- 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각). `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
+- 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각·카톡 초안 후보). 초안 후보(`find_draft_candidates`)는 낱말 하나라도 걸리는 가족(`CustomerSearchPort.match_any`, OR)을 읽어 반려동물 이름 정확 일치 → 보호자 이름 → 전화 → 부분 일치 순으로 최대 5 가족만 돌려주고, 낱말을 저장하거나 로그에 남기지 않는다. `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
 - 검색 줄의 `last_visit_at`(최근 방문순)은 원본이 visits 다 — 검색 줄을 다시 만들 때 건드리지 않고, visit 이 `set_last_visit`로 알려 준다.
```

`backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py`:

```diff
@@ -117,6 +117,27 @@ class CustomerSearchPgAdapter(CustomerSearchPort):
             )
         return conditions
 
+    async def match_any(self, ctx: ShopContext, words: tuple[SearchWord, ...], limit: int) -> list[int]:
+        if not words:
+            return []
+        any_word = []
+        for word in words:
+            pattern = _like_escape(word.value)
+            if word.kind == "last4":
+                any_word.append(Entry.phone_last4.like(pattern + "%", escape="\\"))
+            elif len(word.value) == 1:
+                # 한 글자 이름("봄")은 통단어로만 — 부분 일치면 그 글자가 든 이름이 전부 걸린다.
+                any_word.append(func.concat(" ", Entry.terms, " ").like("% " + pattern + " %", escape="\\"))
+            else:
+                any_word.append(Entry.terms.ilike("%" + pattern + "%", escape="\\"))
+        stmt = (
+            select(Entry.customer_id)
+            .where(Entry.shop_id == ctx.shop_id, or_(*any_word))
+            .order_by(Entry.customer_id)
+            .limit(limit)
+        )
+        return list((await self._session.execute(stmt)).scalars())
+
     async def search(self, ctx: ShopContext, request: SearchRequest) -> SearchPage:
         key_column = {
             "recent": Entry.last_activity_at, "name": Entry.sort_name, "last_visit": Entry.last_visit_at,
```

`backend/apps/customer/app/use_cases/customer_directory_interactor.py`:

```diff
@@ -2,12 +2,18 @@ from __future__ import annotations
 
 from datetime import datetime
 
+DRAFT_CANDIDATE_LIMIT = 5
+_MATCH_LIMIT = 20   # 순위를 매기기 전에 읽는 가족 수 — 낱말 하나에 수십 가족이 걸려도 여기서 자른다
+
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
 from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
 from customer.app.ports.output.pet_repository import PetRepository
 from customer.domain.errors import PetNotFoundError, PetPassedAwayError
-from hub.app.dtos.family_brief import FamilyBriefs
+from customer.domain.services.phone_number import mask_phone
+from customer.domain.services.search_terms import parse_query
+from hub.app.dtos.draft_candidate import DraftCandidate
+from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from hub.app.dtos.shop_context import ShopContext
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 
@@ -45,3 +51,43 @@ class CustomerDirectoryInteractor(CustomerDirectoryPort):
 
     async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
         await self._search.set_last_visit(ctx, customer_id, at)
+
+    async def find_draft_candidates(self, ctx: ShopContext, words: tuple[str, ...]) -> list[DraftCandidate]:
+        if not words:
+            return []
+        customer_ids = await self._search.match_any(ctx, parse_query(" ".join(words)), limit=_MATCH_LIMIT)
+        if not customer_ids:
+            return []
+        customers = await self._customers.list_active(ctx, customer_ids)   # 익명화한 고객은 여기서 빠진다
+        pets_of = {c.id: [] for c in customers}
+        for pet in await self._pets.list_for_customers(ctx, [c.id for c in customers]):
+            if not pet.passed_away:
+                pets_of[pet.customer_id].append(pet)
+        digits = [w for w in words if w.isdigit()]
+        ranked = []
+        for customer in customers:
+            matched = tuple(p.id for p in pets_of[customer.id] if p.name in words)
+            if matched:
+                rank = 0
+            elif customer.name in words:
+                rank = 1
+            elif any((len(d) >= 8 and d in customer.phone) or (len(d) == 4 and customer.phone.endswith(d))
+                     for d in digits):
+                rank = 2
+            else:
+                rank = 3
+            ranked.append((rank, customer.id, customer, matched))
+        ranked.sort(key=lambda r: (r[0], r[1]))
+        return [
+            DraftCandidate(
+                customer=CustomerBrief(customer_id=c.id, name=c.name, phone_masked=mask_phone(c.phone)),
+                pets=tuple(
+                    PetBrief(pet_id=p.id, customer_id=c.id, name=p.name, species=p.species, breed=p.breed,
+                             weight_kg=p.weight_kg, passed_away=False)
+                    for p in pets_of[c.id]
+                ),
+                matched_pet_ids=matched,
+                exact=rank <= 1,
+            )
+            for rank, _, c, matched in ranked[:DRAFT_CANDIDATE_LIMIT]
+        ]
```

`backend/apps/hub/_docs/CLAUDE.md`:

```diff
@@ -16,3 +16,5 @@
 | `UserDirectoryPort.get_profiles(user_ids) → dict[int, UserProfile]` | auth `get_user_profiles` | tenancy `list_members` |
 | `ActiveUserGuardPort.lock_active(user_id) → bool` | auth `guard_active_user` | tenancy `accept_invite` |
 | `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy `apply_withdrawal` | auth `withdraw` (인증 프로세스) |
+| `CustomerDirectoryPort.lock_family · briefs · set_last_visit · find_draft_candidates(ctx, words) → list[DraftCandidate]` | customer `customer_directory` | visit (방문 쓰기의 가족 잠금, 이름 표시, 최근 방문순, 카톡 초안 후보) |
+| `VisitLedgerPort` (방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기) | visit `visit_ledger` | customer (삭제·익명화·무지개다리 규칙, 고객 상세) |
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/customer/tests/app/use_cases/test_customer_directory_interactor.py -q -p no:cacheprovider` → 15 passed(이 작업 7)

Run (`infra/`): `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_search_pg_adapter.py -q -p no:cacheprovider -m integration` → 30 passed(이 작업 4)

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 634 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `find_draft_candidates`에서 `if not pet.passed_away` 조건을 뺀다 → `무지개다리_아이는_후보의_반려동물에서_빠진다` 실패.
- `ranked.sort(...)` 줄을 뺀다 → `반려동물_이름_정확_일치가_보호자_이름_전화_부분_일치보다_앞선다` 실패.
- `ranked[:DRAFT_CANDIDATE_LIMIT]`를 `ranked`로 → `후보는_다섯_가족까지_ID_오름차순이다` 실패.
- pg 어댑터 `match_any`의 `or_(*any_word)`를 `and_(*any_word)`로 → `낱말_하나라도_걸리면_고객_ID_오름차순으로_찾는다` 실패(통합).
- pg 어댑터 `match_any`의 한 글자 분기(`elif len(word.value) == 1`)를 뺀다 → `한_글자_낱말은_통단어로만_찾는다` 실패(통합).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(customer): 허브 포트 find_draft_candidates — 카톡 초안의 누구 후보(낱말 OR 검색, 순위, 최대 5 가족)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: visit 도메인 해석기 `draft_parser` — 날짜·시각·메뉴·누구 낱말(표 기반 테스트)

**Files:**
- Create: `backend/apps/visit/domain/services/draft_parser.py`
- Create: `backend/apps/visit/tests/domain/test_draft_parser.py`

**Interfaces:**
- Consumes: 표준 라이브러리만(`re`·`datetime`). 도메인은 core·pydantic·hub 를 import 하지 않는다.
- Produces: `visit.domain.services.draft_parser.parse_draft(text: str, today: date, opens_at: time, closes_at: time, menu_names: Sequence[str]) -> DraftParse`; `DraftParse(date: date | None, time: time | None, guessed_date: bool, guessed_time: bool, menu_names: tuple[str, ...], guessed_menu: bool, words: tuple[str, ...])`; `STOP_WORDS`·`MAX_WORDS`(Task 3 의 어댑터가 `parse_draft`를 부른다).

표 기반(`parametrize`) 테스트다. **오늘은 2026-09-24 목요일**로 고정한다 — 표의 요일 계산이 이 날짜에 묶여 있다. 규칙은 "이 계획에서 새로 정한 것" 6~8 이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/domain/test_draft_parser.py`:

```python
"""카톡 초안 해석기 — 표 기반. 오늘은 2026-09-24(목), 영업시간 10:00~19:00, 기본 메뉴표."""
from datetime import date, time

import pytest

from visit.domain.services.draft_parser import MAX_WORDS, parse_draft

TODAY = date(2026, 9, 24)   # 목요일
OPENS, CLOSES = time(10, 0), time(19, 0)
MENUS = ["목욕", "위생", "부분 미용", "전체 미용", "스포팅"]


def parse(text, today=TODAY, opens=OPENS, closes=CLOSES, menus=MENUS):
    return parse_draft(text, today, opens, closes, menus)


@pytest.mark.parametrize("text, expected, guessed", [
    ("내일 2시", date(2026, 9, 25), False),
    ("모레 갈게요", date(2026, 9, 26), False),
    ("내일모레 괜찮아요?", date(2026, 9, 26), False),          # 긴 표현이 이긴다
    ("글피", date(2026, 9, 27), False),
    ("오늘 저녁", date(2026, 9, 24), False),
    ("이번 주 금요일", date(2026, 9, 25), False),
    ("이번주 월요일", date(2026, 9, 21), True),                # 이번 주의 지난 요일
    ("다음 주 월요일", date(2026, 9, 28), True),               # 다음 주는 늘 짐작함
    ("다음주 수요일", date(2026, 9, 30), True),
    ("금요일 괜찮을까요", date(2026, 9, 25), False),
    ("목요일에요", date(2026, 10, 1), False),                  # 오늘은 빼고 가장 가까운 앞날
    ("수요일", date(2026, 9, 30), False),
    ("10월 2일", date(2026, 10, 2), False),
    ("10월2일", date(2026, 10, 2), False),
    ("10/2", date(2026, 10, 2), False),
    ("9월 3일", date(2027, 9, 3), True),                       # 지난 날짜는 내년으로 짐작
    ("2일", date(2026, 10, 2), True),                          # 달이 없고 지났으면 다음 달
    ("25일", date(2026, 9, 25), True),
    ("24일", date(2026, 9, 24), True),                         # 오늘은 지난 게 아니다
    ("11일", date(2026, 10, 11), True),                        # 1일로 읽지 않는다
    ("123일", None, False),                                    # 세 자리 숫자의 뒤 두 자리를 날짜로 읽지 않는다
    ("1월 1일", date(2027, 1, 1), True),
    ("2/30", None, False),                                     # 없는 날짜
    ("10분 뒤", None, False),
    ("31일", date(2026, 10, 31), True),                        # 이번 달에 없으면 다음 달
    ("안녕하세요", None, False),
])
def test_날짜_표현(text, expected, guessed):
    result = parse(text)
    assert (result.date, result.guessed_date) == (expected, guessed)


def test_달_없는_날짜는_이번_달_아니면_다음_달까지만_본다():
    assert parse("30일", today=date(2026, 2, 10)).date == date(2026, 3, 30)   # 2월엔 없다
    assert parse("30일", today=date(2026, 3, 31)).date == date(2026, 4, 30)   # 3/30 은 지났다
    assert parse("31일", today=date(2026, 4, 1)).date == date(2026, 5, 31)    # 4/31 은 없다
    assert parse("32일", today=date(2026, 4, 1)).date is None


@pytest.mark.parametrize("text, expected, guessed", [
    ("오후 2시", time(14, 0), False),
    ("오후2시반", time(14, 30), False),
    ("2시", time(14, 0), True),                                # 10~19시 안쪽으로
    ("11시", time(11, 0), True),
    ("6시", time(18, 0), True),
    ("10시", time(10, 0), True),                               # 10시는 안, 22시는 밖
    ("12시", time(12, 0), True),                               # 표지가 없으면 늘 짐작함
    ("2시간 걸려요", None, False),                              # "시간"의 "시"는 시각이 아니다
    ("[김민지] [오후 2:31] 내일 3시 콩이 목욕", time(15, 0), True),   # 카톡 머리말의 2:31 은 보낸 시각이다
    ("오후 2시간쯤 뒤 4시", time(16, 0), True),                 # 표지는 "2시간"에 붙어 4시는 표지 없음
    ("15시", time(15, 0), True),
    ("저녁 7시 반", time(19, 30), False),
    ("14:00", time(14, 0), False),
    ("2:30", time(14, 30), True),
    ("오전 10시 30분", time(10, 30), False),
    ("아침 9시", time(9, 0), False),
    ("낮 12시", time(12, 0), False),
    ("낮 2시", time(14, 0), False),
    ("밤 9시", time(21, 0), False),
    ("오전 13시", time(13, 0), False),
    ("3시반", time(15, 30), True),
    ("2시 30분", time(14, 30), True),
    ("25시", None, False),
    ("오후 2시 70분", None, False),
    ("두 시", None, False),
])
def test_시각_표현(text, expected, guessed):
    result = parse(text)
    assert (result.time, result.guessed_time) == (expected, guessed)


def test_표지_없는_시각은_영업시간에_따라_다르게_읽는다():
    assert parse("6시", opens=time(6, 0), closes=time(15, 0)).time == time(6, 0)
    assert parse("8시", opens=time(20, 0), closes=time(23, 0)).time == time(20, 0)
    assert parse("3시", opens=time(10, 0), closes=time(12, 0)).time == time(3, 0)   # 둘 다 밖이면 그대로


@pytest.mark.parametrize("text, expected, guessed", [
    ("전체 미용 부탁드려요", ("전체 미용",), False),
    ("전체미용이요", ("전체 미용",), True),                    # 공백을 빼야 맞으면 짐작함
    ("위생이랑 목욕", ("목욕", "위생"), False),                # 메뉴표 순서
    ("미용 예약", (), False),
    ("스포팅", (), False),
])
def test_메뉴(text, expected, guessed):
    result = parse(text, menus=["목욕", "위생", "부분 미용", "전체 미용"])
    assert (result.menu_names, result.guessed_menu) == (expected, guessed)


@pytest.mark.parametrize("text, expected", [
    ("콩이랑 두부 내일 오후 2시 목욕 부탁드려요", ("콩이랑", "콩", "콩이", "두부", "부탁드려요", "부탁드려")),
    ("콩이가 요즘", ("콩이가", "콩", "콩이", "요즘")),
    ("010-1234-5678 김민지입니다", ("01012345678", "김민지입니다")),
    ("5678이요", ("5678",)),                                   # 숫자에 붙은 한글은 단위·조사다
    ("5678 이요", ("5678",)),
    ("콩이 2시에 목욕탕에서", ("콩이", "콩", "목욕탕에서", "목욕탕")),
    ("123 456", ()),                                           # 뒷자리 4자리도 전체 8자리도 아니다
    ("콩이 콩이 콩이", ("콩이", "콩")),
    ("안녕하세요 월요일 오전 예약 가능할까요", ("가능할까요", "가능할까")),
    ("저 내일 갈게요", ("갈게요", "갈게")),                     # 흔한 한 글자 말은 낱말이 아니다
    ("봄 내일 갈게요", ("봄", "갈게요", "갈게")),                # 한 글자 이름은 낱말이다(customer 가 통단어로 찾는다)
    ("[김민지] [오후 2:31] 콩이 내일요", ("김민지", "콩이", "콩", "내일요")),   # 카톡 머리말의 시각은 지우고 보낸 사람은 남긴다
    ("부분 미용 부분미용", ()),                                 # 메뉴 이름과 그 조각은 낱말이 아니다
])
def test_누구_낱말(text, expected):
    assert parse(text).words == expected


def test_낱말은_스무_개까지다():
    names = " ".join(f"이름{chr(0xAC00 + i)}" for i in range(25))
    assert len(parse(names).words) == MAX_WORDS


def test_한_문장에서_날짜_시각_메뉴_낱말을_함께_뽑는다():
    result = parse("안녕하세요 콩이 내일 오후 2시에 목욕 가능할까요?")
    assert (result.date, result.time, result.menu_names) == (date(2026, 9, 25), time(14, 0), ("목욕",))
    assert result.words == ("콩이", "콩", "가능할까요", "가능할까")
    assert (result.guessed_date, result.guessed_time, result.guessed_menu) == (False, False, False)
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_draft_parser.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError: visit.domain.services.draft_parser`로 수집 단계에서 실패.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/services/draft_parser.py`:

```python
"""카톡 예약 초안 — 보호자가 보낸 글에서 날짜·시각·메뉴·"누구" 낱말을 규칙으로 뽑는다(설계 7절).

외부 전송이 없다. 못 찾은 칸은 비우고, 두 가지로 읽히는 표현은 "짐작함"으로 표시한다 — 결과는 사람이 확인한 뒤
저장한다. 글과 낱말은 이 함수 밖에 남기지 않는다(로그·DB·오류 응답 금지, V9).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import Sequence

_WEEKDAYS = "월화수목금토일"
# 긴 상대 표현부터 본다 — "내일모레"는 모레다.
_RELATIVE = (("글피", 3), ("모레", 2), ("내일", 1), ("오늘", 0))
_WEEK_DAY = re.compile(r"(이번|다음) ?주 ?([월화수목금토일])요일")
_PLAIN_DAY = re.compile(r"([월화수목금토일])요일")
_MONTH_DAY = re.compile(r"(?<!\d)(\d{1,2}) ?월 ?(\d{1,2}) ?일(?!\d)")
_SLASH_DAY = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)")
_DAY_ONLY = re.compile(r"(?<!\d)(\d{1,2}) ?일(?!\d)")

# "2시간"의 "시"는 시각이 아니다 — 뒤에 "간"이 붙으면 건너뛴다.
_MARKED_TIME = re.compile(r"(오전|아침|오후|저녁|밤|낮) ?(\d{1,2}) ?시(?!간) ?(?:(반)|(\d{1,2}) ?분)?")
_CLOCK_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_HOUR_TIME = re.compile(r"(?<!\d)(\d{1,2}) ?시(?!간) ?(?:(반)|(\d{1,2}) ?분)?")
_AFTERNOON = ("오후", "저녁", "밤")
# 카톡 대화를 여러 줄 복사하면 줄마다 "[보낸 사람] [오후 2:31]" 머리말이 붙는다 — 그 시각은 예약 시각이 아니다.
_KAKAO_STAMP = re.compile(r"\[(오전|오후) ?\d{1,2}:\d{2}\]")

# 숫자에 바로 붙은 한글("2시에", "25일", "5678이요")은 단위·조사라 숫자 토큰에 삼킨다.
_TOKEN = re.compile(r"\d[\d-]*[가-힣]*|[가-힣]+")
# 끝에서 조사 하나를 뗀 형도 낱말로 둔다 — "콩이랑"은 콩이+랑(콩이)일 수도 콩+이랑(콩)일 수도 있어 맞는 조사를 모두 떼어 본다.
_PARTICLES = ("이랑", "하고", "한테", "에게", "까지", "부터", "이는", "이가", "이도", "이를",
              "에서", "으로", "은", "는", "이", "가", "을", "를", "도", "랑", "와", "과", "의", "야", "요", "님",
              "에", "로", "께")
# 날짜·시간·인사·예약 낱말은 "누구"가 아니다.
STOP_WORDS = frozenset({
    "안녕하세요", "안녕", "예약", "미용", "가능", "오늘", "내일", "모레", "글피", "이번", "다음", "주",
    "오전", "오후", "저녁", "밤", "낮", "아침", "시", "분", "반", "요일", "이요",
    *(f"{d}요일" for d in _WEEKDAYS),
    # 한 글자 낱말은 이름일 수 있어("봄"·"달") 버리지 않는다 — 흔한 한 글자 말만 뺀다.
    "저", "그", "이", "네", "좀", "꼭", "잘", "더", "또", "안", "못", "뭐", "왜", "나", "너", "애", "것", "게",
    "요", "은", "는", "을", "를", "가", "도", "와", "과", "의", "에", "로",
})
_PHONE_LENGTHS = (4,)   # 뒷자리
_PHONE_MIN = 8          # 전체 번호
MAX_WORDS = 20


@dataclass(frozen=True)
class DraftParse:
    date: date | None
    time: time | None
    guessed_date: bool
    guessed_time: bool
    menu_names: tuple[str, ...]
    guessed_menu: bool
    words: tuple[str, ...]


def parse_draft(text: str, today: date, opens_at: time, closes_at: time, menu_names: Sequence[str]) -> DraftParse:
    text = _KAKAO_STAMP.sub(" ", text)
    day, guessed_day = _parse_date(text, today)
    clock, guessed_clock = _parse_time(text, opens_at, closes_at)
    menus, guessed_menu = _parse_menus(text, menu_names)
    return DraftParse(
        date=day, time=clock, guessed_date=guessed_day, guessed_time=guessed_clock,
        menu_names=menus, guessed_menu=guessed_menu, words=_words(text, menu_names),
    )


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_date(text: str, today: date) -> tuple[date | None, bool]:
    for word, offset in _RELATIVE:
        if word in text:
            return today + timedelta(days=offset), False
    monday = today - timedelta(days=today.weekday())
    if m := _WEEK_DAY.search(text):
        weekday = _WEEKDAYS.index(m.group(2))
        if m.group(1) == "다음":
            return monday + timedelta(days=7 + weekday), True
        day = monday + timedelta(days=weekday)
        return day, day < today   # 이번 주의 지난 요일은 짐작함
    if m := _PLAIN_DAY.search(text):
        ahead = (_WEEKDAYS.index(m.group(1)) - today.weekday()) % 7 or 7   # 오늘은 빼고 가장 가까운 앞날
        return today + timedelta(days=ahead), False
    if m := _MONTH_DAY.search(text) or _SLASH_DAY.search(text):
        day = _safe_date(today.year, int(m.group(1)), int(m.group(2)))
        if day is None:
            return None, False
        if day < today:
            return _safe_date(today.year + 1, day.month, day.day), True   # 지난 날짜면 내년으로 짐작
        return day, False
    if m := _DAY_ONLY.search(text):
        number = int(m.group(1))
        day = _safe_date(today.year, today.month, number)
        if day is None or day < today:
            next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
            day = _safe_date(next_month.year, next_month.month, number)
        return day, day is not None   # 달이 없으니 늘 짐작함
    return None, False


def _clock(hour: int, minute: int) -> time | None:
    return time(hour, minute) if hour < 24 and minute < 60 else None


def _minutes(half: str | None, minute: str | None) -> int:
    return 30 if half else int(minute or 0)


def _parse_time(text: str, opens_at: time, closes_at: time) -> tuple[time | None, bool]:
    if m := _MARKED_TIME.search(text):
        marker, hour, minute = m.group(1), int(m.group(2)), _minutes(m.group(3), m.group(4))
        if marker in _AFTERNOON and hour < 12:
            hour += 12
        elif marker == "낮" and hour < 6:
            hour += 12
        return _clock(hour, minute), False
    if m := _CLOCK_TIME.search(text):
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour >= 12:
            return _clock(hour, minute), False   # 24시 표기는 그대로
    elif m := _HOUR_TIME.search(text):
        hour, minute = int(m.group(1)), _minutes(m.group(2), m.group(3))
    else:
        return None, False
    # 오전·오후 표지가 없다 — 짐작함. 12시 전이면 영업시간 안쪽으로 읽히는 쪽을 고른다.
    clock = _clock(hour, minute)
    if clock is None or hour >= 12:
        return clock, clock is not None
    later = time(hour + 12, minute)
    within = lambda t: opens_at <= t < closes_at   # noqa: E731
    return (later if within(later) and not within(clock) else clock), True


def _parse_menus(text: str, menu_names: Sequence[str]) -> tuple[tuple[str, ...], bool]:
    squeezed = text.replace(" ", "")
    found, guessed = [], False
    for name in menu_names:
        if name in text:
            found.append(name)
        elif name.replace(" ", "") in squeezed:
            found.append(name)
            guessed = True
    return tuple(found), guessed


def _words(text: str, menu_names: Sequence[str]) -> tuple[str, ...]:
    stop = STOP_WORDS | {n for name in menu_names for n in (name, name.replace(" ", ""), *name.split())}
    words: list[str] = []
    for token in _TOKEN.findall(text):
        if token[0].isdigit():
            digits = re.sub(r"\D", "", token)
            if len(digits) in _PHONE_LENGTHS or len(digits) >= _PHONE_MIN:
                words.append(digits)
            continue
        if token in stop:
            continue
        forms = [token] + [token[: -len(p)] for p in _PARTICLES if token.endswith(p) and len(token) > len(p)]
        words += [f for f in forms if f not in stop]
    return tuple(dict.fromkeys(words))[:MAX_WORDS]
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_draft_parser.py -q -p no:cacheprovider` → 73 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 707 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept(도메인 순수성 — 해석기가 core·pydantic 을 모른다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_parse_date`의 `% 7 or 7`에서 `or 7`을 뺀다(오늘 요일을 오늘로 읽음) → `날짜_표현[목요일…]` 실패.
- `_RELATIVE`의 순서를 뒤집는다(오늘·내일·모레·글피) → `날짜_표현[내일모레…]` 실패.
- `_parse_time`의 영업시간 짐작(`later if within(later) and not within(clock) else clock`)을 `clock`으로 → `시각_표현[2시]`·`[6시]`·`[2:30]`·`[3시반]` 실패.
- `_parse_menus`의 공백 제거 비교(`elif`)를 뺀다 → `메뉴[전체미용…]` 실패.
- `_MONTH_DAY`·`_DAY_ONLY`의 `(?<!\d)`를 뺀다 → `달_없는_날짜…`의 `"123일"` 행 실패.
- `_HOUR_TIME`의 `(?!간)`을 뺀다 → `시각_표현[2시간 걸려요]` 실패.
- `parse_draft`의 `_KAKAO_STAMP.sub(" ", text)`를 뺀다 → `시각_표현[[김민지] [오후 2:31] 내일 3시…]`·`누구_낱말[[김민지] [오후 2:31] 콩이 내일요]` 실패.
- `_words`에서 한 글자 낱말을 버리게(`len(f) >= 2`) 바꾼다 → `누구_낱말[봄 내일 갈게요]` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 카톡 초안 해석기 — 날짜·시각·메뉴·누구 낱말을 규칙으로 뽑고 짐작함을 표시한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: `POST /visit-drafts` 슬라이스 — 파서 포트·유스케이스·스키마·라우터·배선·통합 테스트·흐름 스크립트

**Files:**
- Create: `backend/apps/visit/app/ports/output/visit_draft_parser_port.py`
- Create: `backend/apps/visit/adapter/outbound/rule_draft_parser_adapter.py`
- Create: `backend/apps/visit/app/dtos/parse_visit_draft_dto.py`
- Create: `backend/apps/visit/app/ports/input/parse_visit_draft_use_case.py`
- Create: `backend/apps/visit/app/use_cases/parse_visit_draft_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/parse_visit_draft_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/parse_visit_draft_router.py`
- Create: `backend/apps/visit/dependencies/parse_visit_draft_provider.py`
- Modify: `backend/main.py`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`
- Modify: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/tests/adapter/test_parse_visit_draft_router.py`
- Create: `backend/apps/visit/tests/app/use_cases/test_parse_visit_draft_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/scripts/check_visit_flow.sh`
- Create: `backend/tests/integration/test_visit_draft_wiring.py`

**Interfaces:**
- Consumes: Task 1 의 `CustomerDirectoryPort.find_draft_candidates`·`DraftCandidate`, Task 2 의 `parse_draft`·`DraftParse`, 기존 `ScheduleRepository.ensure`·`MenuRepository.list`·`local_date`·`utc_now`·`require_permission`·`reject_control_chars`·`get_customer_directory` 자리.
- Produces: `POST /v1/shops/{shop_id}/visit-drafts`(200, 계약은 아래 스키마 그대로 — `time`은 `HH:MM`); `ParseVisitDraftUseCase.parse_visit_draft(ParseVisitDraftCommand(ctx, text)) -> VisitDraftView`; `VisitDraftParserPort.parse(text, today, opens_at, closes_at, menu_names) -> DraftParse`와 `RuleDraftParserAdapter`; visit 스텁 `FakeDirectory.find_draft_candidates`(`candidates` 속성, journal `("find_draft_candidates", words)`). 앱(Task 4~)은 이 응답 JSON 을 그대로 읽는다.

새 도메인 오류는 없다 — 입력 검증은 pydantic 422, 권한은 기존 가드 403. 유스케이스는 `schedule.ensure` 외에 아무것도 쓰지 않고 잠그지 않는다. 글·낱말은 `logging`에 넘기지 않고(V9) 오류 응답에 되돌려주지 않는다(라우터 테스트가 422·403 본문을 본다). 흐름 스크립트는 판정 4개를 더한다('통과' 줄 27 → 31) — 이 작업의 마지막에 실제로 돌린다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_parse_visit_draft_router.py`:

```python
from datetime import date, time

from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
from visit.app.dtos.parse_visit_draft_dto import (
    DraftCandidateView,
    DraftGuessView,
    DraftPetView,
    VisitDraftView,
)
from visit.dependencies.parse_visit_draft_provider import get_parse_visit_draft_use_case
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of

DRAFT = VisitDraftView(
    date=date(2026, 9, 25), time=time(14, 0),
    customer_candidates=[DraftCandidateView(customer_id=7, name="이수진", phone_masked="010-12··-5678",
                                            pets=[DraftPetView(pet_id=11, name="두부")], matched_pet_ids=[11])],
    pet_ids=[11], menu_ids=[1, 3], guessed=DraftGuessView(date=False, time=True, who=False, menu=False),
)
TEXT = "안녕하세요 두부 내일 2시 목욕 가능할까요?"


def _app(stub, access=None):
    return build_app(parse_visit_draft_router, get_parse_visit_draft_use_case, stub, access)


async def test_카톡_글을_초안으로_돌려준다():
    stub = Recorder(DRAFT)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/visit-drafts", json={"text": f"  {TEXT}\n"})
    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-09-25", "time": "14:00",
        "customer_candidates": [{"customer_id": 7, "name": "이수진", "phone_masked": "010-12··-5678",
                                 "pets": [{"pet_id": 11, "name": "두부"}], "matched_pet_ids": [11]}],
        "pet_ids": [11], "menu_ids": [1, 3],
        "guessed": {"date": False, "time": True, "who": False, "menu": False},
    }
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].text) == (3, TEXT)   # 앞뒤 공백은 뗀다


async def test_빈_칸은_null_과_빈_목록이다():
    empty = VisitDraftView(date=None, time=None, customer_candidates=[], pet_ids=[], menu_ids=[],
                           guessed=DraftGuessView(date=False, time=False, who=True, menu=False))
    async with client(_app(Recorder(empty))) as c:
        body = (await c.post("/v1/shops/3/visit-drafts", json={"text": "안녕하세요"})).json()
    assert (body["date"], body["time"], body["customer_candidates"], body["pet_ids"]) == (None, None, [], [])


async def test_빈_글_긴_글_제어_문자는_422_이고_글을_되돌려주지_않는다():
    stub = Recorder(DRAFT)
    async with client(_app(stub)) as c:
        for text in ("", "   ", "가" * 1001, "콩이\x00", "콩이\x07"):
            response = await c.post("/v1/shops/3/visit-drafts", json={"text": text})
            assert error_of(response) == (422, "VALIDATION_ERROR"), text
            assert "콩이" not in response.text and "가가" not in response.text
        assert (await c.post("/v1/shops/3/visit-drafts", json={"text": "콩이\n내일"})).status_code == 200   # 줄바꿈은 된다
        assert (await c.post("/v1/shops/3/visit-drafts", json={})).status_code == 422
    assert len(stub.calls) == 1


async def test_reservation_write_가_없으면_403_이고_글을_되돌려주지_않는다():
    stub = Recorder(DRAFT)
    async with client(_app(stub, READ_ONLY)) as c:
        response = await c.post("/v1/shops/3/visit-drafts", json={"text": TEXT})
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert "두부" not in response.text
    assert stub.calls == []
```

`backend/apps/visit/tests/app/use_cases/test_parse_visit_draft_interactor.py`:

```python
from datetime import date, time
from decimal import Decimal

from hub.app.dtos.draft_candidate import DraftCandidate
from hub.app.dtos.family_brief import CustomerBrief, PetBrief
from visit.adapter.outbound.rule_draft_parser_adapter import RuleDraftParserAdapter
from visit.app.dtos.parse_visit_draft_dto import ParseVisitDraftCommand
from visit.app.use_cases.parse_visit_draft_interactor import ParseVisitDraftInteractor
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, Journal

NOW = kst(9, 24, 15)   # 2026-09-24(목) 15:00 KST


def _candidate(customer_id, name, pets=(), matched=(), exact=True):
    return DraftCandidate(
        customer=CustomerBrief(customer_id=customer_id, name=name, phone_masked="010-12··-5678"),
        pets=tuple(PetBrief(pet_id=pet_id, customer_id=customer_id, name=pet_name, species="dog", breed="말티즈",
                            weight_kg=Decimal("3.2"), passed_away=False) for pet_id, pet_name in pets),
        matched_pet_ids=tuple(matched), exact=exact,
    )


def _setup(settings=None):
    journal = Journal()
    schedule = FakeSchedule(journal) if settings is None else FakeSchedule(journal, settings=settings)
    menus, directory = FakeMenus(journal), FakeDirectory(journal)
    interactor = ParseVisitDraftInteractor(schedule, menus, directory, RuleDraftParserAdapter(), now=lambda: NOW)
    return journal, menus, directory, interactor


async def _parse(interactor, text):
    return await interactor.parse_visit_draft(ParseVisitDraftCommand(ctx=ctx(), text=text))


async def test_후보가_하나면_그_아이를_고른_초안이다():
    journal, menus, directory, interactor = _setup()
    bath = menus.seed("목욕", 60)
    menus.seed("전체 미용", 150, archived=True)
    directory.candidates = [_candidate(7, "이수진", pets=((11, "두부"), (12, "콩이")), matched=(12,))]

    draft = await _parse(interactor, "안녕하세요 콩이 내일 오후 2시에 목욕 가능할까요?")

    assert (draft.date, draft.time) == (date(2026, 9, 25), time(14, 0))
    assert [c.customer_id for c in draft.customer_candidates] == [7]
    assert [(p.pet_id, p.name) for p in draft.customer_candidates[0].pets] == [(11, "두부"), (12, "콩이")]
    assert (draft.customer_candidates[0].matched_pet_ids, draft.pet_ids) == ([12], [12])
    assert draft.menu_ids == [bath.id]
    assert (draft.guessed.date, draft.guessed.time, draft.guessed.who, draft.guessed.menu) == (False, False, False, False)
    assert ("find_draft_candidates", ("콩이", "콩", "가능할까요", "가능할까")) in journal


async def test_후보가_여럿이면_아이를_고르지_않고_누구는_짐작함이다():
    _, _, directory, interactor = _setup()
    directory.candidates = [_candidate(7, "이수진", pets=((11, "콩이"),), matched=(11,)),
                            _candidate(8, "김민지", pets=((21, "콩이"),), matched=(21,))]
    draft = await _parse(interactor, "콩이 2시")
    assert ([c.customer_id for c in draft.customer_candidates], draft.pet_ids) == ([7, 8], [])
    assert (draft.guessed.who, draft.guessed.time, draft.time) == (True, True, time(14, 0))


async def test_후보가_하나라도_부분_일치면_누구는_짐작함이다():
    _, _, directory, interactor = _setup()
    directory.candidates = [_candidate(7, "이수진", pets=((11, "콩순이"),), exact=False)]
    draft = await _parse(interactor, "콩순 내일")
    assert (draft.pet_ids, draft.guessed.who) == ([], True)


async def test_낱말이_없으면_후보를_묻지_않는다():
    journal, _, _, interactor = _setup()
    draft = await _parse(interactor, "내일 오후 2시")
    assert (draft.customer_candidates, draft.guessed.who) == ([], True)
    assert not any(entry[0] == "find_draft_candidates" for entry in journal)


async def test_메뉴는_보관하지_않은_것만_메뉴표_순서로():
    _, menus, _, interactor = _setup()
    menus.seed("전체 미용", 150, archived=True)
    hygiene, bath = menus.seed("위생", 60), menus.seed("목욕", 60)
    draft = await _parse(interactor, "목욕이랑 위생, 전체미용도")
    assert (draft.menu_ids, draft.guessed.menu) == ([hygiene.id, bath.id], False)


async def test_표지_없는_시각은_매장의_영업시간으로_짐작한다():
    _, _, _, interactor = _setup(ScheduleSettings(opens_at=time(6, 0), closes_at=time(15, 0),
                                                  default_duration_minutes=60, closed_weekdays=frozenset()))
    draft = await _parse(interactor, "6시")
    assert (draft.time, draft.guessed.time) == (time(6, 0), True)


async def test_설정이_없으면_준비하고_그_영업시간을_쓴다__아무것도_저장하지_않는다():
    journal, _, _, interactor = _setup()
    draft = await _parse(interactor, "2시")
    assert (draft.time, draft.date) == (time(14, 0), None)
    assert journal == [("ensure", 1)]   # 쓰기 호출이 없다


async def test_오늘은_매장_시간대로_센다():
    _, _, _, interactor = _setup()
    interactor._now = lambda: kst(9, 25, 0, 30)   # 한국 9/25 00:30 = UTC 9/24 15:30
    draft = await _parse(interactor, "오늘")
    assert draft.date == date(2026, 9, 25)
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -116,6 +116,7 @@ class FakeDirectory:
         self.journal = journal if journal is not None else Journal()
         self.families: dict[int, tuple[int, dict[int, bool]]] = {}
         self.names: dict[int, str | None] = {}
+        self.candidates: list = []
 
     def family(self, customer_id=1, pets=(101,), shop_id=1, name="김민지", passed=()) -> None:
         self.families[customer_id] = (shop_id, {p: p in passed for p in pets})
@@ -143,6 +144,11 @@ class FakeDirectory:
     async def set_last_visit(self, ctx, customer_id, at):
         self.journal.append(("set_last_visit", customer_id, at))
 
+    async def find_draft_candidates(self, ctx, words):
+        """카톡 초안 후보 — 미리 넣어 둔 후보(self.candidates)를 그대로 준다."""
+        self.journal.append(("find_draft_candidates", tuple(words)))
+        return list(self.candidates)
+
 
 class FakeVisits:
     def __init__(self, journal: Journal | None = None) -> None:
```

`backend/tests/integration/test_visit_draft_wiring.py`:

```python
"""카톡 예약 초안(POST /visit-drafts)을 실제 배선(허브 포트 조립·DB·매장 접근 확인)으로 확인한다. 첫 테스트는 테넌트 격리다."""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
PET = {
    "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
    "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True,
}
TEXT = "안녕하세요 내일 오후 2시 콩이 목욕 가능할까요?"


async def _family(wired, shop_id, headers, name="김민지", phone="010-1234-5678", pets=("콩이", "두부")):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers",
        json={"customer": {"name": name, "phone": phone, "marketing_consent": True}, "pet": {**PET, "name": pets[0]}},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    customer_id = response.json()["customer"]["customer_id"]
    pet_ids = [response.json()["pets"][0]["pet_id"]]
    for pet_name in pets[1:]:
        added = await wired.api.post(
            f"/v1/shops/{shop_id}/customers/{customer_id}/pets", json={**PET, "name": pet_name}, headers=headers
        )
        assert added.status_code == 201, added.text
        pet_ids.append(added.json()["pet"]["pet_id"])
    return customer_id, pet_ids


async def _draft(wired, shop_id, headers, text=TEXT):
    return await wired.api.post(f"/v1/shops/{shop_id}/visit-drafts", json={"text": text}, headers=headers)


async def test_다른_매장의_가족은_후보에_오르지_않는다(wired):
    """V1 — B매장에 콩이가 있어도 A매장의 초안에는 없다. B매장 경로는 403."""
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    await _family(wired, b_shop, b)

    mine = await _draft(wired, a_shop, a)
    assert mine.status_code == 200, mine.text
    assert (mine.json()["customer_candidates"], mine.json()["pet_ids"], mine.json()["guessed"]["who"]) == ([], [], True)
    assert error_of(await _draft(wired, b_shop, a)) == (403, "NOT_A_MEMBER")


async def test_실제_배선으로_후보_메뉴_날짜_시각을_채운다(wired, caplog):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, (kong, dubu) = await _family(wired, shop_id, headers)
    await _family(wired, shop_id, headers, name="박서준", phone="010-9876-5678", pets=("보리",))
    menus = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=headers)).json()["items"]
    bath = next(m["menu_id"] for m in menus if m["name"] == "목욕")
    tomorrow = (datetime.now(SEOUL).date() + timedelta(days=1)).isoformat()

    with caplog.at_level(logging.DEBUG):
        response = await _draft(wired, shop_id, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["date"], body["time"], body["menu_ids"]) == (tomorrow, "14:00", [bath])
    assert body["customer_candidates"] == [{
        "customer_id": customer_id, "name": "김민지", "phone_masked": "010-12··-5678",
        "pets": [{"pet_id": kong, "name": "콩이"}, {"pet_id": dubu, "name": "두부"}], "matched_pet_ids": [kong],
    }]
    assert (body["pet_ids"], body["guessed"]) == ([kong], {"date": False, "time": False, "who": False, "menu": False})
    # V9 — 글의 낱말이 어느 로그에도 남지 않는다.
    assert not any("콩이" in record.getMessage() for record in caplog.records)
    assert "콩이" not in caplog.text


async def test_직원도_초안을_받고_초안은_아무것도_저장하지_않는다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    await _family(wired, shop_id, headers)
    tomorrow = (datetime.now(SEOUL).date() + timedelta(days=1)).isoformat()

    response = await _draft(wired, shop_id, bearer(staff["access_token"]))
    assert response.status_code == 200, response.text
    assert len(response.json()["customer_candidates"]) == 1
    day = await wired.api.get(f"/v1/shops/{shop_id}/visits?date={tomorrow}", headers=headers)
    assert day.json()["items"] == []
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/app/use_cases/test_parse_visit_draft_interactor.py apps/visit/tests/adapter/test_parse_visit_draft_router.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError`(`parse_visit_draft_dto` 등)로 수집 단계에서 실패.

Run (`infra/`): `docker compose run --rm backend pytest tests/integration/test_visit_draft_wiring.py -q -p no:cacheprovider -m integration`
Expected: 3개 모두 404(라우트 없음)로 실패.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/ports/output/visit_draft_parser_port.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, time

from visit.domain.services.draft_parser import DraftParse


class VisitDraftParserPort(ABC):
    """카톡 글 → 초안 해석. 지금 구현은 규칙 기반 도메인 서비스(외부 전송 없음)다.

    ⑨ 이후 LLM 어댑터로 바꿀 때 이 포트 뒤에서 어댑터만 바꾸고, 외부로 보내기 전 마스킹 Decorator 를 거친다(설계 13절).
    글은 여기서 해석만 하고 어디에도 남기지 않는다.
    """

    @abstractmethod
    def parse(
        self, text: str, today: date, opens_at: time, closes_at: time, menu_names: Sequence[str]
    ) -> DraftParse: ...
```

`backend/apps/visit/adapter/outbound/rule_draft_parser_adapter.py`:

```python
"""규칙 기반 초안 해석 어댑터 — 도메인 서비스 draft_parser 를 그대로 부른다. LLM 어댑터의 자리다."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, time

from visit.app.ports.output.visit_draft_parser_port import VisitDraftParserPort
from visit.domain.services.draft_parser import DraftParse, parse_draft


class RuleDraftParserAdapter(VisitDraftParserPort):
    def parse(
        self, text: str, today: date, opens_at: time, closes_at: time, menu_names: Sequence[str]
    ) -> DraftParse:
        return parse_draft(text, today, opens_at, closes_at, menu_names)
```

`backend/apps/visit/app/dtos/parse_visit_draft_dto.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ParseVisitDraftCommand:
    """카톡 글 하나. 저장하지 않고 초안만 돌려준다 — 글은 로그·DB·오류 응답에 남기지 않는다(V9)."""

    ctx: ShopContext
    text: str


@dataclass(frozen=True)
class DraftPetView:
    pet_id: int
    name: str


@dataclass(frozen=True)
class DraftCandidateView:
    customer_id: int
    name: str
    phone_masked: str
    pets: list[DraftPetView]        # 무지개다리 제외
    matched_pet_ids: list[int]      # 글의 낱말과 이름이 같은 아이


@dataclass(frozen=True)
class DraftGuessView:
    """짐작함 — 사람이 확인해야 하는 칸."""

    date: bool
    time: bool
    who: bool
    menu: bool


@dataclass(frozen=True)
class VisitDraftView:
    date: date | None
    time: time | None
    customer_candidates: list[DraftCandidateView]   # 최대 5 가족
    pet_ids: list[int]                              # 후보가 하나일 때 그 후보의 matched_pet_ids
    menu_ids: list[int]                             # 메뉴표 순서
    guessed: DraftGuessView
```

`backend/apps/visit/app/ports/input/parse_visit_draft_use_case.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.parse_visit_draft_dto import ParseVisitDraftCommand, VisitDraftView


class ParseVisitDraftUseCase(ABC):
    @abstractmethod
    async def parse_visit_draft(self, command: ParseVisitDraftCommand) -> VisitDraftView: ...
```

`backend/apps/visit/app/use_cases/parse_visit_draft_interactor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.parse_visit_draft_dto import (
    DraftCandidateView,
    DraftGuessView,
    DraftPetView,
    ParseVisitDraftCommand,
    VisitDraftView,
)
from visit.app.ports.input.parse_visit_draft_use_case import ParseVisitDraftUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_draft_parser_port import VisitDraftParserPort
from visit.domain.services.visit_schedule import local_date


class ParseVisitDraftInteractor(ParseVisitDraftUseCase):
    """카톡 글 → 예약 초안(설계 7절). 아무것도 쓰지 않는다 — 설정 준비(ensure)만 다른 조회와 같다.

    날짜·시각·메뉴는 해석기가, "누구"는 허브 포트(customer)가 글의 낱말로 찾는다. 결과는 사람이 확인한 뒤 등록 API 로 저장한다.
    """

    def __init__(
        self, schedule: ScheduleRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        parser: VisitDraftParserPort, now: Callable[[], datetime],
    ) -> None:
        self._schedule = schedule
        self._menus = menus
        self._directory = directory
        self._parser = parser
        self._now = now

    async def parse_visit_draft(self, command: ParseVisitDraftCommand) -> VisitDraftView:
        ctx = command.ctx
        settings = await self._schedule.ensure(ctx)
        menus = await self._menus.list(ctx, include_archived=False)
        parsed = self._parser.parse(
            command.text, local_date(self._now(), ctx.timezone), settings.opens_at, settings.closes_at,
            [m.name for m in menus],
        )
        candidates = await self._directory.find_draft_candidates(ctx, parsed.words) if parsed.words else []
        only = candidates[0] if len(candidates) == 1 else None
        return VisitDraftView(
            date=parsed.date,
            time=parsed.time,
            customer_candidates=[
                DraftCandidateView(
                    customer_id=c.customer.customer_id, name=c.customer.name or "",
                    phone_masked=c.customer.phone_masked or "",
                    pets=[DraftPetView(pet_id=p.pet_id, name=p.name or "") for p in c.pets],
                    matched_pet_ids=list(c.matched_pet_ids),
                )
                for c in candidates
            ],
            pet_ids=list(only.matched_pet_ids) if only else [],
            menu_ids=[m.id for m in menus if m.name in parsed.menu_names],
            guessed=DraftGuessView(
                date=parsed.guessed_date, time=parsed.guessed_time,
                who=only is None or not only.exact, menu=parsed.guessed_menu,
            ),
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/parse_visit_draft_schema.py`:

```python
from __future__ import annotations

from datetime import date, time
from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints, field_serializer

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
from visit.app.dtos.parse_visit_draft_dto import VisitDraftView

MAX_DRAFT_TEXT = 1000


class VisitDraftRequestSchema(BaseModel):
    """카톡에서 붙여넣거나 공유받은 글. 1,000자까지, 줄바꿈 말고는 제어 문자를 받지 않는다."""

    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_DRAFT_TEXT),
        AfterValidator(lambda v: reject_control_chars(v, allow_newline=True)),
    ]


class DraftPetSchema(BaseModel):
    pet_id: int
    name: str


class DraftCandidateSchema(BaseModel):
    customer_id: int
    name: str
    phone_masked: str
    pets: list[DraftPetSchema]
    matched_pet_ids: list[int]


class DraftGuessSchema(BaseModel):
    date: bool
    time: bool
    who: bool
    menu: bool


class VisitDraftSchema(BaseModel):
    date: date | None
    time: time | None   # HH:MM 으로 나간다(계약) — 앱이 시간 칸의 at 로 그대로 쓴다
    customer_candidates: list[DraftCandidateSchema]
    pet_ids: list[int]
    menu_ids: list[int]
    guessed: DraftGuessSchema

    @field_serializer("time")
    def _hhmm(self, value: time | None) -> str | None:
        return None if value is None else value.strftime("%H:%M")

    @classmethod
    def of(cls, view: VisitDraftView) -> VisitDraftSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/v1/parse_visit_draft_router.py`:

```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.parse_visit_draft_schema import (
    VisitDraftRequestSchema,
    VisitDraftSchema,
)
from visit.app.dtos.parse_visit_draft_dto import ParseVisitDraftCommand
from visit.app.ports.input.parse_visit_draft_use_case import ParseVisitDraftUseCase
from visit.dependencies.parse_visit_draft_provider import get_parse_visit_draft_use_case

parse_visit_draft_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@parse_visit_draft_router.post("/{shop_id}/visit-drafts", response_model=VisitDraftSchema)
async def parse_visit_draft(
    body: VisitDraftRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: ParseVisitDraftUseCase = Depends(get_parse_visit_draft_use_case),
) -> VisitDraftSchema:
    """카톡 글 → 예약 초안. 저장하지 않는다(사람이 확인한 뒤 POST /visits 로 저장)."""
    return VisitDraftSchema.of(await use_case.parse_visit_draft(ParseVisitDraftCommand(ctx=ctx, text=body.text)))
```

`backend/apps/visit/dependencies/parse_visit_draft_provider.py`:

```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.adapter.outbound.rule_draft_parser_adapter import RuleDraftParserAdapter
from visit.app.ports.input.parse_visit_draft_use_case import ParseVisitDraftUseCase
from visit.app.use_cases.parse_visit_draft_interactor import ParseVisitDraftInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_menu_repository, build_schedule_repository
from visit.domain.services.visit_schedule import utc_now


def get_parse_visit_draft_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> ParseVisitDraftUseCase:
    return ParseVisitDraftInteractor(
        schedule=build_schedule_repository(db), menus=build_menu_repository(db), directory=directory,
        parser=RuleDraftParserAdapter(), now=utc_now,
    )
```

`backend/main.py`:

```diff
@@ -71,6 +71,7 @@ from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_da
 from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
 from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
 from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
+from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
 from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
 from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
 from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
@@ -142,6 +143,7 @@ app.include_router(list_day_visits_router)
 app.include_router(register_visit_router)
 app.include_router(reschedule_visits_router)
 app.include_router(transition_visits_router)
+app.include_router(parse_visit_draft_router)
 app.include_router(get_visit_router)
 app.include_router(update_visit_router)
 app.include_router(get_next_visit_draft_router)
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -12,3 +12,4 @@
 - "오늘"과 하루의 경계는 매장 시간대(`ShopContext.timezone`)로 센다. 요청 시각은 시간대가 붙어 와야 하고, 응답 시각은 매장 시간대로 나간다.
 - 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각을 `CustomerDirectoryPort.set_last_visit`로 같은 트랜잭션에서 넘긴다(고객 목록 '최근 방문순'). 어긋나면 `scripts/rebuild_last_visit.py`로 복구한다.
 - 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
+- 카톡 예약 초안(`POST /visit-drafts`)은 **아무것도 저장하지 않는다.** 글은 `app/ports/output/visit_draft_parser_port.py` 뒤의 규칙 어댑터(`adapter/outbound/rule_draft_parser_adapter.py` → `domain/services/draft_parser.py`)가 날짜·시각·메뉴·낱말로 읽고, "누구"는 허브 포트 `CustomerDirectoryPort.find_draft_candidates`가 낱말로 찾는다(최대 5 가족). 글과 낱말을 로그·DB·오류 응답에 남기지 않는다(설계 10절 V9). ⑨ 이후 LLM 해석은 같은 포트 뒤에서 어댑터만 바꾼다.
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:

```diff
@@ -27,6 +27,8 @@ class VisitMyselfInteractor(VisitMyselfUseCase):
                 "GET·PUT /visits/{visit_id} 는 상세·수정, POST /visits/reschedule 는 같은 보호자의 예약을 함께 옮기기, "
                 "POST /visits/transitions 는 start·complete·cancel·no_show·revert(같은 보호자의 방문만, 전부 되거나 "
                 "전부 안 됨), GET /visits/{visit_id}/next-draft 는 다음 예약 초안입니다(취소·노쇼한 방문은 409). "
+                "POST /visit-drafts 는 카톡 글을 규칙으로 읽어 날짜·시각·보호자 후보·메뉴를 짐작한 초안입니다"
+                "(저장하지 않고, 글을 남기지 않습니다). "
                 "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                 "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}, "
                 "POST /menus/{menu_id}/archive(메뉴표 — 지우지 않고 보관)도 있습니다. "
```

`backend/scripts/check_visit_flow.sh`:

```diff
@@ -39,6 +39,14 @@ kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
 dubu=$(call POST "$S/customers/$customer_id/pets" "$staff_token" "$(pet 두부)" | field "['pet']['pet_id']")
 echo "통과  고객 $customer_id 과 반려동물 $kong, $dubu"
 
+# 카톡 예약 초안(③-A3) — 저장하지 않고 후보·메뉴·날짜·시각만 짐작한다.
+tomorrow=$(TZ=Asia/Seoul python3 -c "import datetime as d; print(d.date.today()+d.timedelta(days=1))")
+kakao=$(call POST "$S/visit-drafts" "$staff_token" '{"text":"안녕하세요 내일 오후 2시 콩이 목욕 부탁드려요"}')
+expect "카톡 초안의 보호자 후보" "$(echo "$kakao" | field "['customer_candidates'][0]['customer_id']")" "$customer_id"
+expect "카톡 초안이 콩이를 고른다" "$(echo "$kakao" | field "['pet_ids']")" "[$kong]"
+expect "카톡 초안의 메뉴·날짜·시각" "$(echo "$kakao" | calc "(len(d['menu_ids']) > 0, d['date'], d['time'])")" "(True, '$tomorrow', '14:00')"
+expect "카톡 초안은 저장하지 않는다" "$(call GET "$S/visits?date=$tomorrow" "$staff_token" | calc "len(d['items'])")" "0"
+
 expect "기본 메뉴가 준비된다" "$(call GET "$S/menus" "$staff_token" | calc "[m['name'] for m in d['items']]")" \
   "['목욕', '위생', '부분 미용', '전체 미용', '스포팅']"
 bath=$(call GET "$S/menus" "$staff_token" | field "['items'][0]['menu_id']")
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/app/use_cases/test_parse_visit_draft_interactor.py apps/visit/tests/adapter/test_parse_visit_draft_router.py -q -p no:cacheprovider` → 12 passed

Run (`infra/`): `docker compose run --rm backend pytest tests/integration/test_visit_draft_wiring.py -q -p no:cacheprovider -m integration` → 3 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 719 passed(허브 포트 배선·라우트 점검 포함)

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 261 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept

Run (`infra/`): `docker compose run --rm --no-deps auth python scripts/print_routes.py` → visit 경로 21개(`POST /v1/shops/{shop_id}/visit-drafts` 가 API 프로세스에)

Run (`infra/`): `docker compose restart backend && bash ../backend/scripts/check_visit_flow.sh` → '통과' 줄 31개(초안 판정 4개 포함). 개발 DB 에 확인용 매장·고객·방문이 남는다.

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- 인터랙터의 `if parsed.words else []` 가드를 뺀다(낱말이 없어도 포트를 부른다) → `낱말이_없으면_후보를_묻지_않는다`·`설정이_없으면_준비하고…` 실패.
- `who=only is None or not only.exact`를 `who=only is None`으로 → `후보가_하나라도_부분_일치면_누구는_짐작함이다` 실패.
- `menus.list(ctx, include_archived=False)`를 `True`로 → `메뉴는_보관하지_않은_것만_메뉴표_순서로` 실패.
- 라우터의 `require_permission("reservation:write")`를 `get_shop_context`로 → `reservation_write_가_없으면_403_이고…` 실패.
- 스키마의 `_hhmm` 직렬화를 뺀다 → `카톡_글을_초안으로_돌려준다`(`"14:00"`)와 통합 `실제_배선으로_후보_메뉴_날짜_시각을_채운다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): POST /visit-drafts — 카톡 글을 초안으로(파서 포트, 허브 포트 후보, 저장·로그 없음)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 앱 — 초안 모델·API·명령과 예약 화면의 미리 채움(`VisitPrefill`) 일반화

**Files:**
- Modify: `app/lib/features/visit/api/visit_models.dart`
- Modify: `app/lib/features/visit/api/visit_api.dart`
- Modify: `app/lib/features/visit/state/visit_commands.dart`
- Create: `app/lib/features/visit/state/visit_prefill.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Modify: `app/lib/features/visit/screens/visit_form.dart`
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/test/features/visit/api/visit_api_test.dart`
- Modify: `app/test/features/visit/screens/register_visit_screen_test.dart`
- Modify: `app/test/support/visit_fixtures.dart`

**Interfaces:**
- Consumes: Task 3 의 응답 JSON(`date`·`time`·`customer_candidates`·`pet_ids`·`menu_ids`·`guessed`), 기존 `VisitApi._get`/`_client.post`, `VisitCommands`·`runShopScoped`, `RegisterVisitScreen`(`date`·`draft`), `VisitForm`·`VisitFormInitial`(`prefilled`), `menuDuration`.
- Produces: `VisitDraft`(date: DateTime?, time: String? `HH:MM`, candidates: List<DraftCandidate>, petIds, menuIds, guessed: DraftGuess) · `DraftCandidate`(customerId, name, phoneMasked, pets: List<DraftPet>, matchedPetIds) · `DraftPet` · `DraftGuess`(date, time, who, menu); `VisitApi.parseDraft(int shopId, String text) → Future<VisitDraft>`; `VisitCommands.parseDraft(shopId, text)`; `VisitPrefill({int? customerId, DateTime? date, String? at, Set<int> petIds, List<MenuBrief> menus})`(`lib/features/visit/state/visit_prefill.dart`); `RegisterVisitScreen(prefill:)`과 `/visits/new`의 `extra`가 `VisitPrefill`이면 그것으로 여는 라우트(Task 5 의 초안 화면이 쓴다); 픽스처 `visitDraftJson`·`draftCandidateJson`·`draftPetJson`(`test/support/visit_fixtures.dart`).

새 플래그를 두지 않는다. `VisitFormInitial.prefilled`(지난번처럼으로 덮어쓰지 않음)를 `prefill.menus.isNotEmpty`로 넘기고, 폼에 "메뉴는 있는데 소요가 없으면 메뉴 기본 소요 합으로 시작"과 "미리 골라진 아이는 이 보호자의 아이만 남긴다"를 더한다. 다음 예약 초안(`NextVisitDraft`)·수정 화면은 소요를 늘 주므로 영향이 없다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/visit/api/visit_api_test.dart`:

```diff
@@ -430,6 +430,66 @@ void main() {
     );
   });
 
+  test('카톡 초안은 text 를 본문으로 보내고 날짜·시간·후보·짐작을 읽는다', () async {
+    final s = _build(
+      (options, body) => FakeResponse(
+        statusCode: 200,
+        data: visitDraftJson(
+          time: '14:30',
+          menuIds: [1, 3],
+          guessedTime: true,
+          candidates: [
+            draftCandidateJson(),
+            draftCandidateJson(
+              customerId: 8,
+              name: '김민지',
+              pets: [draftPetJson(petId: 21, name: '콩이')],
+              matchedPetIds: [],
+            ),
+          ],
+        ),
+      ),
+    );
+
+    final draft = await s.api.parseDraft(3, '내일 2시반 두부 목욕이랑 부분미용');
+    expect(s.adapter.requests.last.path, '/v1/shops/3/visit-drafts');
+    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/visit-drafts']), {
+      'text': '내일 2시반 두부 목욕이랑 부분미용',
+    });
+    expect(draft.date, DateTime(2026, 10, 2));
+    expect(draft.time, '14:30');
+    expect(draft.petIds, [11]);
+    expect(draft.menuIds, [1, 3]);
+    expect(draft.guessed.time, isTrue);
+    expect(draft.guessed.date, isFalse);
+    expect(draft.candidates.map((c) => c.customerId), [7, 8]);
+    expect(draft.candidates.first.phoneMasked, '010-12··-5678');
+    expect(draft.candidates.first.pets.single.name, '두부');
+    expect(draft.candidates.last.matchedPetIds, isEmpty);
+  });
+
+  test('카톡 초안의 날짜·시간·후보는 비어 있을 수 있다', () async {
+    final s = _build(
+      (options, body) => FakeResponse(
+        statusCode: 200,
+        data: visitDraftJson(
+          date: null,
+          time: null,
+          candidates: [],
+          petIds: [],
+          menuIds: [],
+        ),
+      ),
+    );
+
+    final draft = await s.api.parseDraft(3, '안녕하세요');
+    expect(draft.date, isNull);
+    expect(draft.time, isNull);
+    expect(draft.candidates, isEmpty);
+    expect(draft.petIds, isEmpty);
+    expect(draft.menuIds, isEmpty);
+  });
+
   test('서버 오류는 코드 그대로 ApiException 이 된다', () async {
     final s = _build(
       (options, body) => const FakeResponse(
```

`app/test/features/visit/screens/register_visit_screen_test.dart`:

```diff
@@ -5,6 +5,7 @@ import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/features/home/state/today_provider.dart';
 import 'package:chagocnote/features/visit/api/visit_models.dart';
+import 'package:chagocnote/features/visit/state/visit_prefill.dart';
 import 'package:chagocnote/l10n/app_strings.dart';
 import 'package:flutter/material.dart';
 import 'package:flutter_test/flutter_test.dart';
@@ -514,6 +515,117 @@ void main() {
     expect(setup.calls, isNot(contains('GET /v1/shops/3/visits/defaults')));
   });
 
+  testWidgets('카톡 초안(보호자 있음)으로 열면 ①을 건너뛰고 날짜·시각·메뉴로 채우며, 뒤로 가면 닫힌다', (
+    tester,
+  ) async {
+    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    final result = await _open(
+      tester,
+      setup,
+      path: '/visits/new',
+      extra: VisitPrefill(
+        customerId: 7,
+        date: DateTime(2026, 10, 2),
+        at: '14:30',
+        petIds: const {11},
+        menus: const [MenuBrief(menuId: 3, name: '부분 미용')],
+      ),
+    );
+
+    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
+    expect(find.text(AppStrings.changeCustomer), findsNothing);
+    expect(
+      find.text(AppStrings.saveReservation('10월 2일 금 14:30')),
+      findsOneWidget,
+    );
+    // 소요는 메뉴 기본 소요의 합(부분 미용 90분)이고, "지난번처럼"은 부르지 않는다.
+    expect(find.text(AppStrings.durationText(90)), findsOneWidget);
+    expect(find.text(AppStrings.prefilledFromLast), findsNothing);
+    expect(setup.calls, isNot(contains('GET /v1/shops/3/visits/defaults')));
+    expect(_slotQueries(setup), contains('2026-10-02 14:30'));
+
+    await tester.tap(find.bySemanticsLabel(AppStrings.back));
+    await settle(tester);
+    expect(result.closed, isTrue);
+    expect(result.value, isNull);
+  });
+
+  testWidgets('카톡 초안(보호자 없음)으로 열면 ①에서 고른 뒤 ②가 초안의 날짜·시각·메뉴로 채워진다', (
+    tester,
+  ) async {
+    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _open(
+      tester,
+      setup,
+      path: '/visits/new',
+      extra: VisitPrefill(
+        date: DateTime(2026, 10, 3),
+        at: '11:00',
+        menus: const [MenuBrief(menuId: 1, name: '목욕')],
+      ),
+    );
+
+    expect(find.text(AppStrings.reserveWhoTitle), findsOneWidget);
+    await _pickCustomer(tester);
+
+    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
+    expect(
+      find.text(AppStrings.saveReservation('10월 3일 토 11:00')),
+      findsOneWidget,
+    );
+    expect(find.text(AppStrings.durationText(60)), findsOneWidget);
+    expect(setup.calls, isNot(contains('GET /v1/shops/3/visits/defaults')));
+    // 보호자를 골랐으니 [바꾸기]와 뒤로 가기는 ①로 돌아간다.
+    expect(find.text(AppStrings.changeCustomer), findsOneWidget);
+  });
+
+  testWidgets('카톡 초안이 넘긴 아이가 이 보호자의 아이가 아니면 버리고, 하나뿐인 아이를 고른다', (
+    tester,
+  ) async {
+    final backend = VisitTestBackend();
+    Map<String, dynamic>? sent;
+    backend.routes['POST /v1/shops/3/visits'] = (o, body) {
+      sent = bodyOf(body);
+      return FakeResponse(statusCode: 201, data: savedJson([visitJson()]));
+    };
+    final setup = CustomerTestSetup(backend.call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _open(
+      tester,
+      setup,
+      path: '/visits/new',
+      extra: VisitPrefill(
+        customerId: 7,
+        date: DateTime(2026, 10, 2),
+        at: '14:00',
+        petIds: const {99},
+        menus: const [MenuBrief(menuId: 1, name: '목욕')],
+      ),
+    );
+
+    await tester.tap(_save());
+    await settle(tester);
+    expect(sent?['pet_ids'], [11]);
+  });
+
+  testWidgets('카톡 초안에 메뉴가 없으면 "지난번처럼"으로 채운다', (tester) async {
+    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _open(
+      tester,
+      setup,
+      path: '/visits/new',
+      extra: VisitPrefill(customerId: 7, date: DateTime(2026, 10, 2)),
+    );
+
+    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
+    expect(setup.calls, contains('GET /v1/shops/3/visits/defaults'));
+    expect(find.text(AppStrings.prefilledFromLast), findsOneWidget);
+    expect(find.text(AppStrings.pickTimeFirst), findsOneWidget);
+  });
+
   testWidgets('[바꾸기]와 뒤로 가기는 ①로 돌아간다', (tester) async {
     final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
     addTearDown(setup.container.dispose);
```

`app/test/support/visit_fixtures.dart`:

```diff
@@ -258,3 +258,47 @@ List<Map<String, dynamic>> defaultMenusJson() => [
   menuJson(menuId: 4, name: '전체 미용', defaultDurationMinutes: 150, sortOrder: 4),
   menuJson(menuId: 5, name: '스포팅', defaultDurationMinutes: 120, sortOrder: 5),
 ];
+
+/// 카톡 예약 초안 응답(③-A3). 후보가 없으면 `candidates: []`.
+Map<String, dynamic> visitDraftJson({
+  String? date = '2026-10-02',
+  String? time = '14:00',
+  List<Map<String, dynamic>>? candidates,
+  List<int> petIds = const [11],
+  List<int> menuIds = const [1],
+  bool guessedDate = false,
+  bool guessedTime = false,
+  bool guessedWho = false,
+  bool guessedMenu = false,
+}) => {
+  'date': date,
+  'time': time,
+  'customer_candidates': candidates ?? [draftCandidateJson()],
+  'pet_ids': petIds,
+  'menu_ids': menuIds,
+  'guessed': {
+    'date': guessedDate,
+    'time': guessedTime,
+    'who': guessedWho,
+    'menu': guessedMenu,
+  },
+};
+
+Map<String, dynamic> draftCandidateJson({
+  int customerId = 7,
+  String name = '이수진',
+  String phoneMasked = '010-12··-5678',
+  List<Map<String, dynamic>>? pets,
+  List<int> matchedPetIds = const [11],
+}) => {
+  'customer_id': customerId,
+  'name': name,
+  'phone_masked': phoneMasked,
+  'pets': pets ?? [draftPetJson()],
+  'matched_pet_ids': matchedPetIds,
+};
+
+Map<String, dynamic> draftPetJson({int petId = 11, String name = '두부'}) => {
+  'pet_id': petId,
+  'name': name,
+};
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test test/features/visit/api/visit_api_test.dart test/features/visit/screens/register_visit_screen_test.dart --timeout 20s`
Expected: 컴파일 오류(`VisitDraft`·`VisitPrefill`·`parseDraft` 없음)로 실패.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/api/visit_models.dart`:

```diff
@@ -585,3 +585,100 @@ class VisitUpdate {
     'memo': memo,
   };
 }
+
+/// 카톡 글을 해석한 예약 초안(설계 7절). 서버는 저장하지 않는다 — 사람이
+/// 확인한 뒤 등록 API 로 저장한다. 못 찾은 칸은 null·빈 목록이다.
+class VisitDraft {
+  const VisitDraft({
+    required this.date,
+    required this.time,
+    required this.candidates,
+    required this.petIds,
+    required this.menuIds,
+    required this.guessed,
+  });
+
+  factory VisitDraft.fromJson(Map<String, dynamic> json) => VisitDraft(
+    date: json['date'] == null ? null : parseDay(json['date'] as String),
+    time: json['time'] as String?,
+    candidates: (json['customer_candidates'] as List)
+        .map((e) => DraftCandidate.fromJson(e as Map<String, dynamic>))
+        .toList(),
+    petIds: (json['pet_ids'] as List).cast<int>(),
+    menuIds: (json['menu_ids'] as List).cast<int>(),
+    guessed: DraftGuess.fromJson(json['guessed'] as Map<String, dynamic>),
+  );
+
+  final DateTime? date;
+
+  /// `HH:MM`.
+  final String? time;
+
+  /// 글의 낱말로 찾은 보호자 후보(최대 5). 하나면 그 보호자로 짐작한 것이다.
+  final List<DraftCandidate> candidates;
+
+  /// 후보가 하나일 때 글에 이름이 나온 그 집 아이들.
+  final List<int> petIds;
+  final List<int> menuIds;
+  final DraftGuess guessed;
+}
+
+class DraftCandidate {
+  const DraftCandidate({
+    required this.customerId,
+    required this.name,
+    required this.phoneMasked,
+    required this.pets,
+    required this.matchedPetIds,
+  });
+
+  factory DraftCandidate.fromJson(Map<String, dynamic> json) => DraftCandidate(
+    customerId: json['customer_id'] as int,
+    name: json['name'] as String,
+    phoneMasked: json['phone_masked'] as String,
+    pets: (json['pets'] as List)
+        .map((e) => DraftPet.fromJson(e as Map<String, dynamic>))
+        .toList(),
+    matchedPetIds: (json['matched_pet_ids'] as List).cast<int>(),
+  );
+
+  final int customerId;
+  final String name;
+  final String phoneMasked;
+  final List<DraftPet> pets;
+
+  /// 글의 낱말과 이름이 맞은 아이.
+  final List<int> matchedPetIds;
+}
+
+class DraftPet {
+  const DraftPet({required this.petId, required this.name});
+
+  factory DraftPet.fromJson(Map<String, dynamic> json) =>
+      DraftPet(petId: json['pet_id'] as int, name: json['name'] as String);
+
+  final int petId;
+  final String name;
+}
+
+/// 해석기가 확신하지 못한 칸 — 화면에 "짐작" 표시를 단다.
+class DraftGuess {
+  const DraftGuess({
+    required this.date,
+    required this.time,
+    required this.who,
+    required this.menu,
+  });
+
+  factory DraftGuess.fromJson(Map<String, dynamic> json) => DraftGuess(
+    date: json['date'] as bool,
+    time: json['time'] as bool,
+    who: json['who'] as bool,
+    menu: json['menu'] as bool,
+  );
+
+  final bool date;
+  final bool time;
+  final bool who;
+  final bool menu;
+}
```

`app/lib/features/visit/api/visit_api.dart`:

```diff
@@ -116,6 +116,16 @@ class VisitApi {
         await _get('/v1/shops/$shopId/visits/$visitId/next-draft'),
       );
 
+  /// 카톡 글 → 예약 초안(③-A3). 서버는 글을 저장하지 않는다.
+  Future<VisitDraft> parseDraft(int shopId, String text) async =>
+      VisitDraft.fromJson(
+        await _client.post(
+              '/v1/shops/$shopId/visit-drafts',
+              data: {'text': text},
+            )
+            as Map<String, dynamic>,
+      );
+
   Future<VisitSettings> settings(int shopId) async =>
       VisitSettings.fromJson(await _get('/v1/shops/$shopId/visit-settings'));
```

`app/lib/features/visit/state/visit_commands.dart`:

```diff
@@ -57,6 +57,10 @@ class VisitCommands {
   Future<NextVisitDraft> nextDraft(int shopId, int visitId) =>
       runShopScoped(_ref, () => _api.nextDraft(shopId, visitId));
 
+  /// 카톡 초안(저장하지 않는다 — 읽기라 아무것도 다시 부르지 않는다).
+  Future<VisitDraft> parseDraft(int shopId, String text) =>
+      runShopScoped(_ref, () => _api.parseDraft(shopId, text));
+
   Future<VisitSettings> updateSettings(int shopId, VisitSettings settings) =>
       _scheduleWrite(() => _api.updateSettings(shopId, settings));
```

`app/lib/features/visit/state/visit_prefill.dart`:

```dart
import '../api/visit_models.dart';

/// 카톡 초안이 예약 등록 화면에 미리 채우는 값(③-A3). 다음 예약 초안
/// (`NextVisitDraft`)과 달리 어느 칸이든 비어 있을 수 있다.
///
/// [customerId]가 있으면 ①(고객 찾기)을 건너뛰고 ②로 바로 간다. 없으면 ①에서
/// 고른 뒤 ②가 나머지 칸으로 채워진다. [petIds]는 그 보호자의 아이만 남는다.
/// [menus]가 있으면 소요를 메뉴 기본 소요의 합으로 채우고 "지난번처럼"으로
/// 덮어쓰지 않는다. 없으면 기존처럼 "지난번처럼"을 부른다.
class VisitPrefill {
  const VisitPrefill({
    this.customerId,
    this.date,
    this.at,
    this.petIds = const {},
    this.menus = const [],
  });

  final int? customerId;
  final DateTime? date;

  /// `HH:MM`.
  final String? at;
  final Set<int> petIds;
  final List<MenuBrief> menus;
}
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -25,6 +25,7 @@ import '../../customer/state/search_debouncer.dart';
 import '../../home/state/today_provider.dart';
 import '../api/visit_models.dart';
 import '../state/visit_commands.dart';
+import '../state/visit_prefill.dart';
 import 'visit_form.dart';
 import 'visit_labels.dart';
 
@@ -34,18 +35,27 @@ import 'visit_labels.dart';
 ///
 /// 저장하면 저장한 날짜를 돌려주며 닫는다 — 부른 화면이 그 날로 옮겨 간다.
 class RegisterVisitScreen extends ConsumerStatefulWidget {
-  const RegisterVisitScreen({super.key, this.date, this.draft});
+  const RegisterVisitScreen({
+    super.key,
+    this.date,
+    this.draft,
+    this.prefill,
+  });
 
   final DateTime? date;
   final NextVisitDraft? draft;
 
+  /// 카톡 초안(③-A3). 보호자가 있으면 ①을 건너뛴다.
+  final VisitPrefill? prefill;
+
   @override
   ConsumerState<RegisterVisitScreen> createState() =>
       _RegisterVisitScreenState();
 }
 
 class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
-  late int? _customerId = widget.draft?.customerId;
+  late int? _customerId =
+      widget.draft?.customerId ?? widget.prefill?.customerId;
   bool _busy = false;
   String? _errorText;
 
@@ -115,7 +125,7 @@ class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
     final customerId = _customerId;
     final onSearch = customerId == null;
     // 초안으로 열었으면 ①이 없다 — 뒤로 가면 닫는다.
-    final backToSearch = !onSearch && widget.draft == null;
+    final backToSearch = !onSearch && !_skippedSearch;
     return PopScope(
       canPop: !backToSearch,
       onPopInvokedWithResult: (didPop, _) {
@@ -171,8 +181,13 @@ class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
     );
   }
 
+  /// 다음 예약 초안이나 보호자가 있는 카톡 초안으로 열었으면 ①이 없었다.
+  bool get _skippedSearch =>
+      widget.draft != null || widget.prefill?.customerId != null;
+
   Widget _formFor(int shopId, int customerId) {
     final draft = widget.draft;
+    final prefill = widget.prefill;
     final initial = draft != null
         ? VisitFormInitial(
             date: draft.startsAt.day,
@@ -183,6 +198,15 @@ class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
             menus: draft.menus,
             prefilled: true,
           )
+        : prefill != null
+        ? VisitFormInitial(
+            date: prefill.date ?? ref.read(todayProvider),
+            petIds: prefill.petIds,
+            at: prefill.at,
+            menus: prefill.menus,
+            // 메뉴가 글에 있었으면 "지난번처럼"으로 덮어쓰지 않는다.
+            prefilled: prefill.menus.isNotEmpty,
+          )
         : VisitFormInitial(date: widget.date ?? ref.read(todayProvider));
     return VisitForm(
       // 보호자를 바꾸면 폼을 새로 만든다 — 앞 보호자의 아이 선택이 남지 않게.
@@ -193,7 +217,7 @@ class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
       header: _OwnerCard(
         shopId: shopId,
         customerId: customerId,
-        onChange: draft == null ? _backToSearch : null,
+        onChange: _skippedSearch ? null : _backToSearch,
       ),
       submitLabel: (date, at) =>
           AppStrings.saveReservation('${dayLabel(date)} $at'),
```

`app/lib/features/visit/screens/visit_form.dart`:

```diff
@@ -154,10 +154,12 @@ class _VisitFormState extends ConsumerState<VisitForm> {
   int _effectiveDuration(VisitSettings settings) =>
       _duration ?? settings.defaultDurationMinutes;
 
-  /// 반려동물이 하나뿐인 보호자면 그 아이를 미리 고른다.
+  /// 반려동물이 하나뿐인 보호자면 그 아이를 미리 고른다. 미리 골라진 아이는
+  /// 이 보호자의 아이만 남긴다(카톡 초안이 다른 집 아이를 넘길 수 없게).
   void _initPets(List<Pet> living) {
     if (_petsInitialized) return;
     _petsInitialized = true;
+    _petIds.removeWhere((id) => !living.any((p) => p.petId == id));
     if (_petIds.isNotEmpty || _ownerOnly || living.length != 1) return;
     _petIds = {living.single.petId};
     WidgetsBinding.instance.addPostFrameCallback(
@@ -327,6 +329,14 @@ class _VisitFormState extends ConsumerState<VisitForm> {
   }
 
   Widget _buildForm(VisitSettings settings, List<Pet> pets, List<Menu> menus) {
+    // 메뉴만 있고 소요가 없는 초안(카톡)은 메뉴 기본 소요의 합으로 시작한다.
+    if (_duration == null && _menuIds.isNotEmpty && !_durationTouched) {
+      final byId = {for (final m in menus) m.menuId: m};
+      _duration = menuDuration([
+        for (final id in _menuIds)
+          byId[id]?.defaultDurationMinutes ?? settings.defaultDurationMinutes,
+      ], settings.defaultDurationMinutes);
+    }
     final duration = _effectiveDuration(settings);
     final selection = _at == null
         ? null
```

`app/lib/core/router/app_router.dart`:

```diff
@@ -25,6 +25,7 @@ import '../../features/visit/screens/day_screen.dart';
 import '../../features/visit/screens/register_visit_screen.dart';
 import '../../features/visit/screens/visit_detail_screen.dart';
 import '../../features/visit/screens/visit_edit_screen.dart';
+import '../../features/visit/state/visit_prefill.dart';
 
 /// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
 /// 바뀔 때마다 이걸로 "redirect를 다시 평가해라"라고 알린다.
@@ -162,9 +163,11 @@ final routerProvider = Provider<GoRouter>((ref) {
         path: '/visits/new',
         builder: (context, state) {
           final date = state.uri.queryParameters['date'];
+          final extra = state.extra;
           return RegisterVisitScreen(
             date: date == null ? null : parseDay(date),
-            draft: state.extra as NextVisitDraft?,
+            draft: extra is NextVisitDraft ? extra : null,
+            prefill: extra is VisitPrefill ? extra : null,
           );
         },
       ),
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test test/features/visit/api/visit_api_test.dart test/features/visit/screens/register_visit_screen_test.dart --timeout 20s` → 통과(이 작업 6: API 2, 예약 화면 4)

Run (`app/`): `flutter test --timeout 30s` → 전부 통과(482개)

Run (`app/`): `flutter analyze` → `No issues found!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_initPets`의 `_petIds.removeWhere(...)`를 뺀다 → `카톡 초안이 넘긴 아이가 이 보호자의 아이가 아니면 버리고, 하나뿐인 아이를 고른다` 실패.
- `prefilled: prefill.menus.isNotEmpty`를 `prefilled: false`로 → `카톡 초안(보호자 있음)으로 열면 ①을 건너뛰고…`("지난번처럼"이 메뉴를 덮는다) 실패.
- 폼의 "메뉴만 있고 소요가 없으면 합으로 시작" 블록을 뺀다 → 같은 테스트(소요 표시) 실패.
- `backToSearch = !onSearch && !_skippedSearch`를 `!onSearch && widget.draft == null`로 → `…뒤로 가면 닫힌다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 카톡 초안 모델·API·명령과 예약 화면의 미리 채움(VisitPrefill) 일반화

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 앱 — 초안 화면 `/visits/draft`와 예약 ①의 [카톡 붙여넣기]

**Files:**
- Modify: `app/lib/features/visit/state/visit_providers.dart`
- Create: `app/lib/features/visit/screens/draft_screen.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Modify: `app/lib/core/router/app_router.dart`
- Modify: `app/lib/core/router/screen_keys.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/test/design/glass_boundary_test.dart`
- Create: `app/test/features/visit/screens/draft_screen_test.dart`
- Modify: `app/test/support/visit_test_backend.dart`

**Interfaces:**
- Consumes: Task 4 의 `VisitDraft`·`VisitPrefill`·`VisitCommands.parseDraft`·`RegisterVisitScreen(prefill:)`, 기존 `menusProvider`·`runShopScoped`·`messageFor`·`dayLabel`·`maskedTail`·`Pressable(selected:)`·`AppChip`·`AppButton(icon:)`·`Clipboard`.
- Produces: 라우트 `/visits/draft`(extra: `String` 글) → `DraftScreen(text:)`(`ScreenKeys.visitDraft`) — 저장한 날짜를 `pop`으로 돌려준다(Task 6 의 관문이 `push`한다); `visitDraftProvider = FutureProvider.autoDispose.family<VisitDraft, ({int shopId, String text})>`; `AppStrings`의 "카톡 예약 초안" 절(`draftTitle`·`draftReceivedText`·`draftOwnerSection`·`draftGuessed`·`draftNoCandidates`·`draftEmptyValue`·`draftHint`·`draftContinue`·`draftFindCustomer`·`pasteFromKakao`·`clipboardEmpty`); `VisitTestBackend`의 `POST /v1/shops/3/visit-drafts` 기본 응답.

A안("이 계획에서 새로 정한 것" 3). 닫힘은 연쇄다: ② 저장 → 날짜를 돌려주며 닫힘 → 초안 화면이 그 날짜로 닫힘 → ①이 그 날짜로 닫힘 → 홈이 그날을 고른다. 클립보드는 테스트에서 `SystemChannels.platform`의 `Clipboard.getData`를 흉내 낸다. 화면은 글을 어디에도 남기지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/glass_boundary_test.dart`:

```diff
@@ -24,6 +24,7 @@ void main() {
       'lib/features/visit/screens/visit_detail_screen.dart',
       'lib/features/visit/screens/visit_actions.dart',
       'lib/features/visit/screens/day_screen.dart',
+      'lib/features/visit/screens/draft_screen.dart',
       'lib/features/shop/screens/schedule_settings_screen.dart',
       'lib/features/shop/screens/menu_settings_screen.dart',
     ];
```

`app/test/features/visit/screens/draft_screen_test.dart`:

```dart
import 'dart:async';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_chip.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];
const _text = '안녕하세요 내일 2시반에 두부 부분미용 될까요?';

Future<Closed<DateTime>> _open(
  WidgetTester tester,
  CustomerTestSetup setup, {
  String path = '/visits/draft',
  Object? extra = _text,
}) {
  useTallView(tester);
  return pushOnHome<DateTime>(tester, setup, path, extra: extra);
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Finder _guessChips() => find.byWidgetPredicate(
  (w) => w is AppChip && w.label == AppStrings.draftGuessed,
);

/// `Clipboard.getData`가 [text]를 돌려주게 한다(null 이면 빈 클립보드).
void _mockClipboard(WidgetTester tester, String? text) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(SystemChannels.platform, (call) async {
        if (call.method == 'Clipboard.getData') {
          return text == null ? null : {'text': text};
        }
        return null;
      });
  addTearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, null),
  );
}

void main() {
  testWidgets(
    '후보가 하나면 고른 상태로 보이고 짐작한 칸에 표시가 붙으며, [예약 이어서]가 ②를 채워 열고 저장한 날짜를 돌려준다',
    (tester) async {
      final backend = VisitTestBackend();
      Map<String, dynamic>? draftBody;
      backend.routes['POST /v1/shops/3/visit-drafts'] = (o, body) {
        draftBody = bodyOf(body);
        return FakeResponse(
          statusCode: 200,
          data: visitDraftJson(time: '14:30', guessedTime: true, menuIds: [3]),
        );
      };
      Map<String, dynamic>? sent;
      backend.routes['POST /v1/shops/3/visits'] = (o, body) {
        sent = bodyOf(body);
        return FakeResponse(statusCode: 201, data: savedJson([visitJson()]));
      };
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      final result = await _open(tester, setup);

      expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
      expect(draftBody, {'text': _text});
      expect(find.text(_text), findsOneWidget);
      expect(find.text('이수진 · ··5678'), findsOneWidget);
      expect(find.text('두부'), findsOneWidget);
      expect(find.text('10월 2일 금'), findsOneWidget);
      expect(find.text('14:30'), findsOneWidget);
      expect(find.text('부분 미용'), findsOneWidget);
      // 짐작 표시는 시각에만 붙는다.
      expect(_guessChips(), findsOneWidget);
      expect(
        tester.widget<AppButton>(_button(AppStrings.draftContinue)).onPressed,
        isNotNull,
      );

      await tester.tap(_button(AppStrings.draftContinue));
      await settle(tester);
      expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
      expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
      expect(
        find.text(AppStrings.saveReservation('10월 2일 금 14:30')),
        findsOneWidget,
      );
      expect(find.text(AppStrings.durationText(90)), findsOneWidget);

      await tester.tap(
        find.byWidgetPredicate(
          (w) => w is AppButton && w.label.startsWith('예약 저장'),
        ),
      );
      await settle(tester);
      expect(sent?['customer_id'], 7);
      expect(sent?['pet_ids'], [11]);
      expect(sent?['menu_ids'], [3]);
      // ②가 닫히면 초안 화면도 그 날짜로 닫힌다.
      expect(result.closed, isTrue);
      expect(result.value, DateTime(2026, 10, 2));
      expect(find.byKey(ScreenKeys.visitDraft), findsNothing);
    },
  );

  testWidgets('메뉴표를 아직 못 읽었으면 [예약 이어서]가 메뉴표를 기다린 뒤 메뉴를 채워 연다', (tester) async {
    final backend = VisitTestBackend();
    final menus = Completer<FakeResponse>();
    backend.routes['GET /v1/shops/3/menus'] = (o, b) => menus.future;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) =>
        FakeResponse(statusCode: 200, data: visitDraftJson(menuIds: [3]));
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(find.text('부분 미용'), findsNothing); // 메뉴표 전이라 메뉴 줄은 비어 있다

    await tester.tap(_button(AppStrings.draftContinue));
    await tester.pump();
    expect(find.byKey(ScreenKeys.registerVisit), findsNothing); // 메뉴표를 기다린다
    menus.complete(
      FakeResponse(statusCode: 200, data: {'items': defaultMenusJson()}),
    );
    await settle(tester);
    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    // 글에 있던 "부분 미용"(90분)이 ②에 채워져 있다.
    expect(find.text(AppStrings.durationText(90)), findsOneWidget);
  });

  testWidgets('후보가 여럿이면 골라야 [예약 이어서]가 열리고, 고른 보호자의 ②로 간다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDraftJson(
        guessedWho: true,
        petIds: [],
        candidates: [
          draftCandidateJson(),
          draftCandidateJson(
            customerId: 8,
            name: '김민지',
            phoneMasked: '010-98··-4321',
            pets: [draftPetJson(petId: 21, name: '콩이')],
            matchedPetIds: [],
          ),
        ],
      ),
    );
    backend.routes['GET /v1/shops/3/customers/8'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(
          customerId: 8,
          name: '김민지',
          phone: '01098764321',
        ),
        pets: [petJson(petId: 21, name: '콩이')],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(
      tester.widget<AppButton>(_button(AppStrings.draftContinue)).onPressed,
      isNull,
    );
    // 누구인지 짐작이라 보호자 줄에도 표시가 붙는다.
    expect(_guessChips(), findsOneWidget);

    await tester.tap(find.text('김민지 · ··4321'));
    await settle(tester);
    expect(
      tester.widget<AppButton>(_button(AppStrings.draftContinue)).onPressed,
      isNotNull,
    );

    await tester.tap(_button(AppStrings.draftContinue));
    await settle(tester);
    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(find.text('김민지 · ··4321'), findsOneWidget);
  });

  testWidgets('후보가 없으면 [고객 찾기]로 ①에 가고, 고른 뒤 ②가 초안의 날짜·시각·메뉴로 채워진다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDraftJson(
        candidates: [],
        petIds: [],
        time: '11:00',
        menuIds: [1],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.text(AppStrings.draftNoCandidates), findsOneWidget);
    expect(_button(AppStrings.draftContinue), findsNothing);
    await tester.tap(_button(AppStrings.draftFindCustomer));
    await settle(tester);
    expect(find.text(AppStrings.reserveWhoTitle), findsOneWidget);

    await tester.tap(find.text('두부').first);
    await settle(tester);
    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(
      find.text(AppStrings.saveReservation('10월 2일 금 11:00')),
      findsOneWidget,
    );
    expect(find.text(AppStrings.durationText(60)), findsOneWidget);
  });

  testWidgets('날짜·시각·메뉴를 못 찾으면 빈 표시를 보이고, 해석에 실패하면 문구와 [다시 시도]를 보인다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    var calls = 0;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, b) {
      calls++;
      if (calls == 1) {
        return const FakeResponse(
          statusCode: 422,
          data: {'code': 'VALIDATION_ERROR', 'message': 'x'},
        );
      }
      return FakeResponse(
        statusCode: 200,
        data: visitDraftJson(date: null, time: null, menuIds: []),
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.text('입력한 내용을 확인해 주세요.'), findsOneWidget);
    await tester.tap(_button(AppStrings.retry));
    await settle(tester);

    expect(calls, 2);
    expect(find.text('이수진 · ··5678'), findsOneWidget);
    expect(find.text(AppStrings.draftEmptyValue), findsNWidgets(3));
    expect(_guessChips(), findsNothing);
  });

  testWidgets('붙여넣은 글이 1000자를 넘으면 앞 1000자만 보낸다', (tester) async {
    final backend = VisitTestBackend();
    Map<String, dynamic>? draftBody;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, body) {
      draftBody = bodyOf(body);
      return FakeResponse(statusCode: 200, data: visitDraftJson());
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(
      tester,
      setup,
      path: '/visits/new?date=2026-10-02',
      extra: null,
    );

    _mockClipboard(tester, '가' * 1200);
    await tester.tap(_button(AppStrings.pasteFromKakao));
    await settle(tester);
    expect((draftBody?['text'] as String).length, 1000);
  });

  testWidgets('①의 [카톡 붙여넣기]는 클립보드 글로 초안 화면을 열고, 비어 있으면 문구를 보인다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    Map<String, dynamic>? draftBody;
    backend.routes['POST /v1/shops/3/visit-drafts'] = (o, body) {
      draftBody = bodyOf(body);
      return FakeResponse(statusCode: 200, data: visitDraftJson());
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(
      tester,
      setup,
      path: '/visits/new?date=2026-10-02',
      extra: null,
    );

    _mockClipboard(tester, null);
    await tester.tap(_button(AppStrings.pasteFromKakao));
    await settle(tester);
    expect(find.text(AppStrings.clipboardEmpty), findsOneWidget);
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);

    _mockClipboard(tester, '  $_text  ');
    await tester.tap(_button(AppStrings.pasteFromKakao));
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
    expect(draftBody, {'text': _text});

    // 초안 → ② → 저장하면 ①도 그 날짜로 닫힌다(홈이 그날을 고른다).
    await tester.tap(_button(AppStrings.draftContinue));
    await settle(tester);
    await tester.tap(
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label.startsWith('예약 저장'),
      ),
    );
    await settle(tester);
    expect(result.closed, isTrue);
    expect(result.value, DateTime(2026, 10, 2));
    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
  });
}
```

`app/test/support/visit_test_backend.dart`:

```diff
@@ -62,6 +62,8 @@ class VisitTestBackend {
         FakeResponse(statusCode: 200, data: defaultsJson()),
     'POST /v1/shops/3/visits': (o, b) =>
         FakeResponse(statusCode: 201, data: savedJson([visitJson()])),
+    'POST /v1/shops/3/visit-drafts': (o, b) =>
+        FakeResponse(statusCode: 200, data: visitDraftJson()),
   };
 
   static Map<String, dynamic> _family() => familyJson(
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test test/features/visit/screens/draft_screen_test.dart test/design/glass_boundary_test.dart --timeout 20s`
Expected: 컴파일 오류(`DraftScreen`·`ScreenKeys.visitDraft` 없음)로 실패.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/state/visit_providers.dart`:

```diff
@@ -64,6 +64,16 @@ final visitSlotsProvider = FutureProvider.autoDispose
       ),
     );
 
+/// 카톡 글의 해석(③-A3). 글이 키다 — 같은 글은 한 번만 묻고, 화면을 떠나면
+/// 버린다. 서버는 저장하지 않는다.
+final visitDraftProvider = FutureProvider.autoDispose
+    .family<VisitDraft, ({int shopId, String text})>(
+      (ref, key) => runShopScoped(
+        ref,
+        () => ref.read(visitApiProvider).parseDraft(key.shopId, key.text),
+      ),
+    );
+
 final visitDetailProvider = FutureProvider.autoDispose
     .family<VisitDetail, VisitKey>(
       (ref, key) => runShopScoped(
```

`app/lib/features/visit/screens/draft_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../customer/state/customer_input.dart';
import '../api/visit_models.dart';
import '../state/visit_prefill.dart';
import '../state/visit_providers.dart';
import 'visit_labels.dart';

/// 카톡 글을 해석한 예약 초안을 확인하는 화면(설계 7절, ③-A3 A안). 붙여넣기와
/// 공유 받기가 같은 화면으로 온다.
///
/// 받은 글, 보호자 후보(하나면 고른 상태, 여럿이면 골라야 한다), 날짜·시작·
/// 메뉴 줄(짐작한 칸에 "짐작" 표시)을 보이고, [예약 이어서]가 기존 예약 ②를
/// 미리 채워 연다. 후보가 없으면 [고객 찾기]로 ①에 간 뒤 ②가 채워진다.
/// 서버도 이 화면도 글을 저장하지 않는다 — 저장은 사람이 확인한 뒤 ②에서.
class DraftScreen extends ConsumerStatefulWidget {
  const DraftScreen({super.key, required this.text});

  final String text;

  @override
  ConsumerState<DraftScreen> createState() => _DraftScreenState();
}

class _DraftScreenState extends ConsumerState<DraftScreen> {
  int? _pickedCustomerId;
  bool _expanded = false;
  bool _continuing = false;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  /// 예약 ②(보호자가 있으면 바로, 없으면 ① 뒤)를 초안으로 채워 연다. 저장한
  /// 날짜가 돌아오면 이 화면도 그 날짜로 닫힌다.
  Future<void> _continue(
    int shopId,
    VisitDraft draft,
    DraftCandidate? picked,
  ) async {
    if (_continuing) return;
    setState(() => _continuing = true);
    // 메뉴표를 아직 못 읽었으면 기다린다 — 안 그러면 글에 있던 메뉴가 빠진 채 ②가 열린다.
    List<Menu> menus;
    try {
      menus = await ref.read(
        menusProvider((shopId: shopId, includeArchived: false)).future,
      );
    } catch (_) {
      menus = const []; // 메뉴표를 못 읽으면 메뉴 없이 넘긴다 — ②에서 고른다.
    }
    if (!mounted) return;
    setState(() => _continuing = false);
    final byId = {for (final m in menus) m.menuId: m};
    final prefill = VisitPrefill(
      customerId: picked?.customerId,
      date: draft.date,
      at: draft.time,
      petIds: {...?picked?.matchedPetIds},
      menus: [
        for (final id in draft.menuIds)
          if (byId[id] case final m?) MenuBrief(menuId: id, name: m.name),
      ],
    );
    final saved = await context.push<DateTime>('/visits/new', extra: prefill);
    if (saved != null && mounted) context.pop(saved);
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final key = (shopId: shopId ?? 0, text: widget.text);
    final draft = shopId == null
        ? const AsyncValue<VisitDraft>.loading()
        : ref.watch(visitDraftProvider(key));
    return Scaffold(
      key: ScreenKeys.visitDraft,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.sm,
                  AppSpacing.lg,
                  AppSpacing.sm,
                ),
                child: const Row(
                  children: [
                    AppBackButton(),
                    SizedBox(width: AppSpacing.sm),
                    Text(AppStrings.draftTitle, style: AppTypography.titleKo),
                  ],
                ),
              ),
              Expanded(
                child: draft.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(messageFor(error), style: AppTypography.body),
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: AppStrings.retry,
                          onPressed: () =>
                              ref.invalidate(visitDraftProvider(key)),
                        ),
                      ],
                    ),
                  ),
                  data: (draft) => _body(shopId!, draft),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _body(int shopId, VisitDraft draft) {
    final candidates = draft.candidates;
    // 후보가 하나면 고른 상태로 시작한다. 여럿이면 골라야 한다.
    final pickedId =
        _pickedCustomerId ??
        (candidates.length == 1 ? candidates.single.customerId : null);
    final picked = candidates
        .where((c) => c.customerId == pickedId)
        .firstOrNull;
    final menus = ref
        .watch(menusProvider((shopId: shopId, includeArchived: false)))
        .value;
    final menuNames = menus == null
        ? null
        : [
            for (final id in draft.menuIds)
              for (final m in menus)
                if (m.menuId == id) m.name,
          ];
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        0,
        AppSpacing.lg,
        AppSpacing.xxl,
      ),
      children: [
        const Text(AppStrings.draftReceivedText, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xs),
        Pressable(
          semanticLabel: AppStrings.draftReceivedText,
          onTap: () => setState(() => _expanded = !_expanded),
          child: AppCard(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: SizedBox(
              width: double.infinity,
              child: ExcludeSemantics(
                child: Text(
                  widget.text,
                  style: AppTypography.body,
                  maxLines: _expanded ? null : 3,
                  overflow: _expanded ? null : TextOverflow.ellipsis,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Row(
          children: [
            const Text(
              AppStrings.draftOwnerSection,
              style: AppTypography.caption,
            ),
            if (draft.guessed.who && candidates.isNotEmpty) ...[
              const SizedBox(width: AppSpacing.sm),
              const AppChip(label: AppStrings.draftGuessed),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        if (candidates.isEmpty)
          const Text(AppStrings.draftNoCandidates, style: AppTypography.body)
        else
          for (final c in candidates)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: _CandidateRow(
                candidate: c,
                selected: c.customerId == pickedId,
                onTap: () => setState(() => _pickedCustomerId = c.customerId),
              ),
            ),
        const SizedBox(height: AppSpacing.md),
        _Line(
          label: AppStrings.visitDateLabel,
          value: draft.date == null ? null : dayLabel(draft.date!),
          guessed: draft.guessed.date,
        ),
        _Line(
          label: AppStrings.visitTimeLabel,
          value: draft.time,
          guessed: draft.guessed.time,
        ),
        _Line(
          label: AppStrings.menuLabel,
          value: menuNames == null || menuNames.isEmpty
              ? null
              : menuNames.join(' · '),
          guessed: draft.guessed.menu,
        ),
        const SizedBox(height: AppSpacing.lg),
        const Text(AppStrings.draftHint, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.sm),
        if (candidates.isEmpty)
          AppButton(
            label: AppStrings.draftFindCustomer,
            filled: true,
            busy: _continuing,
            onPressed: () => _continue(shopId, draft, null),
          )
        else
          AppButton(
            label: AppStrings.draftContinue,
            filled: true,
            busy: _continuing,
            onPressed: picked == null
                ? null
                : () => _continue(shopId, draft, picked),
          ),
      ],
    );
  }
}

/// 보호자 후보 한 줄 — 이름 · 번호 뒷자리, 아이 이름들. 고르면 체크.
class _CandidateRow extends StatelessWidget {
  const _CandidateRow({
    required this.candidate,
    required this.selected,
    required this.onTap,
  });

  final DraftCandidate candidate;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = candidate;
    final pets = c.pets.map((p) => p.name).join(' · ');
    return Pressable(
      semanticLabel: '${c.name} $pets',
      selected: selected,
      onTap: onTap,
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        child: ExcludeSemantics(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${c.name} · ${maskedTail(c.phoneMasked)}',
                      style: AppTypography.bodyStrong,
                    ),
                    if (pets.isNotEmpty)
                      Text(pets, style: AppTypography.caption),
                  ],
                ),
              ),
              if (selected) const Icon(Icons.check, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

/// 날짜·시작·메뉴 한 줄. 값이 없으면 "—", 짐작이면 칩.
class _Line extends StatelessWidget {
  const _Line({
    required this.label,
    required this.value,
    required this.guessed,
  });

  final String label;
  final String? value;
  final bool guessed;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        children: [
          SizedBox(width: 48, child: Text(label, style: AppTypography.caption)),
          Expanded(
            child: Text(
              value ?? AppStrings.draftEmptyValue,
              style: AppTypography.body,
            ),
          ),
          if (value != null && guessed)
            const AppChip(label: AppStrings.draftGuessed),
        ],
      ),
    );
  }
}
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -1,4 +1,5 @@
 import 'package:flutter/material.dart';
+import 'package:flutter/services.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
@@ -287,6 +288,7 @@ class _CustomerSearchState extends ConsumerState<_CustomerSearch> {
     onSearch: (q) => setState(() => _q = q),
   );
   String _q = '';
+  String? _pasteNote;
 
   @override
   void initState() {
@@ -301,6 +303,22 @@ class _CustomerSearchState extends ConsumerState<_CustomerSearch> {
     super.dispose();
   }
 
+  /// 클립보드의 카톡 글로 초안 화면을 연다(③-A3). 초안에서 예약을 저장하고
+  /// 돌아오면 ①도 그 날짜로 닫힌다 — 홈이 그날을 고른다.
+  Future<void> _pasteFromKakao(BuildContext context) async {
+    final data = await Clipboard.getData(Clipboard.kTextPlain);
+    var text = data?.text?.trim() ?? '';
+    if (!context.mounted) return;
+    if (text.isEmpty) {
+      setState(() => _pasteNote = AppStrings.clipboardEmpty);
+      return;
+    }
+    if (text.length > 1000) text = text.substring(0, 1000);
+    setState(() => _pasteNote = null);
+    final saved = await context.push<DateTime>('/visits/draft', extra: text);
+    if (saved != null && context.mounted) context.pop(saved);
+  }
+
   /// 새 고객을 등록하고 돌아오면 그 고객으로 ②에 바로 간다.
   Future<void> _registerNew(BuildContext context) async {
     final customerId = await context.push<int>('/customers/new?pick=1');
@@ -318,6 +336,29 @@ class _CustomerSearchState extends ConsumerState<_CustomerSearch> {
     final list = ref.watch(customerListControllerProvider(query));
     return Column(
       children: [
+        Padding(
+          padding: const EdgeInsets.fromLTRB(
+            AppSpacing.lg,
+            0,
+            AppSpacing.lg,
+            AppSpacing.sm,
+          ),
+          child: Row(
+            children: [
+              AppButton(
+                label: AppStrings.pasteFromKakao,
+                icon: Icons.content_paste,
+                onPressed: () => _pasteFromKakao(context),
+              ),
+              if (_pasteNote != null) ...[
+                const SizedBox(width: AppSpacing.sm),
+                Expanded(
+                  child: Text(_pasteNote!, style: AppTypography.caption),
+                ),
+              ],
+            ],
+          ),
+        ),
         Padding(
           padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
           child: TextField(
```

`app/lib/core/router/app_router.dart`:

```diff
@@ -22,6 +22,7 @@ import '../../features/shop/screens/settings_screen.dart';
 import '../../features/shop/screens/shop_settings_screen.dart';
 import '../../features/visit/api/visit_models.dart';
 import '../../features/visit/screens/day_screen.dart';
+import '../../features/visit/screens/draft_screen.dart';
 import '../../features/visit/screens/register_visit_screen.dart';
 import '../../features/visit/screens/visit_detail_screen.dart';
 import '../../features/visit/screens/visit_edit_screen.dart';
@@ -171,6 +172,11 @@ final routerProvider = Provider<GoRouter>((ref) {
           );
         },
       ),
+      GoRoute(
+        path: '/visits/draft',
+        builder: (context, state) =>
+            DraftScreen(text: state.extra as String),
+      ),
       GoRoute(
         path: '/visits/day/:date',
         builder: (context, state) =>
```

`app/lib/core/router/screen_keys.dart`:

```diff
@@ -20,6 +20,7 @@ class ScreenKeys {
   static const petForm = Key('screen_pet_form');
   static const petDetail = Key('screen_pet_detail');
   static const registerVisit = Key('screen_register_visit');
+  static const visitDraft = Key('screen_visit_draft');
   static const visitEdit = Key('screen_visit_edit');
   static const visitDetail = Key('screen_visit_detail');
   static const day = Key('screen_day');
```

`app/lib/l10n/app_strings.dart`:

```diff
@@ -247,6 +247,19 @@ class AppStrings {
   static const warningClosedDay = '쉬는 날이에요';
   static const warningOutsideHours = '영업시간 밖이에요';
 
+  // 카톡 예약 초안(③-A3)
+  static const pasteFromKakao = '카톡 붙여넣기';
+  static const clipboardEmpty = '복사한 글이 없어요';
+  static const draftTitle = '카톡 예약 초안';
+  static const draftReceivedText = '받은 글';
+  static const draftOwnerSection = '보호자';
+  static const draftNoCandidates = '찾은 보호자가 없어요';
+  static const draftGuessed = '짐작';
+  static const draftEmptyValue = '—';
+  static const draftContinue = '예약 이어서';
+  static const draftFindCustomer = '고객 찾기';
+  static const draftHint = '확인한 뒤 저장돼요. 짐작한 칸은 다음 화면에서 고칠 수 있어요.';
+
   static const editVisitTitle = '예약 수정';
   static const moveTogether = '같이 옮기기';
   static const moveOnlyThis = '이 방문만';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test test/features/visit/screens/draft_screen_test.dart test/design/glass_boundary_test.dart --timeout 20s` → 통과(이 작업 7)

Run (`app/`): `flutter test --timeout 30s` → 전부 통과(489개)

Run (`app/`): `flutter analyze` → `No issues found!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_body`의 `candidates.length == 1 ? candidates.single.customerId : null`을 `null`로 → `후보가 하나면 고른 상태로 보이고…` 실패.
- `draft.guessed.who && candidates.isNotEmpty` 칩을 뺀다 → `후보가 여럿이면 골라야 [예약 이어서]가 열리고…` 실패.
- `_pasteFromKakao`의 빈 글 확인(`clipboardEmpty`)을 뺀다 → `①의 [카톡 붙여넣기]는 클립보드 글로 초안 화면을 열고, 비어 있으면 문구를 보인다` 실패.
- `_continue`의 `if (saved != null && mounted) context.pop(saved)`를 뺀다 → `후보가 하나면…저장한 날짜를 돌려준다` 실패.
- `_pasteFromKakao`의 1000자 자르기를 뺀다 → `붙여넣은 글이 1000자를 넘으면 앞 1000자만 보낸다` 실패.
- `VisitPrefill(menus: [...])`를 `menus: const []`로 → `후보가 없으면 [고객 찾기]로 ①에 가고…메뉴로 채워진다` 실패.
- `_continue`의 `await ref.read(menusProvider(...).future)`를 `.value ?? const []`(기다리지 않음)로 → `메뉴표를 아직 못 읽었으면 [예약 이어서]가 메뉴표를 기다린 뒤 메뉴를 채워 연다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 카톡 예약 초안 화면과 예약 ①의 [카톡 붙여넣기]

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 앱 — 공유 받기(직접 쓴 iOS Share Extension·안드로이드 `ACTION_SEND` → 채널 → 초안 화면)

**Files:**
- Create: `app/lib/core/proxy/shared_text_channel.dart`
- Modify: `app/lib/app.dart`
- Modify: `app/android/app/src/main/AndroidManifest.xml`
- Modify: `app/android/app/src/main/kotlin/com/chagocnote/chagocnote/MainActivity.kt`
- Modify: `app/ios/Runner/Info.plist`
- Create: `app/ios/Runner/Runner.entitlements`
- Modify: `app/ios/Runner/AppDelegate.swift`
- Create: `app/ios/ShareExtension/ShareViewController.swift`
- Create: `app/ios/ShareExtension/Info.plist`
- Create: `app/ios/ShareExtension/ShareExtension.entitlements`
- Modify: `app/ios/Runner.xcodeproj/project.pbxproj`
- Create: `app/test/core/proxy/shared_text_channel_test.dart`
- Create: `app/test/features/visit/screens/shared_text_gate_test.dart`

**Interfaces:**
- Consumes: Task 5 의 `/visits/draft`, 기존 `routerProvider`·`sessionControllerProvider`(`SignedIn.selectedShopId`), Flutter 3.44 의 `FlutterPlugin`·`FlutterSceneLifeCycleDelegate`·`registrar.addSceneDelegate`, 안드로이드 `FlutterActivity.configureFlutterEngine`.
- Produces: `MethodChannel('com.chagocnote.app/share')` — Dart → 네이티브 `getPending() → String?`(주고 비운다), 네이티브 → Dart `onSharedText(String)`; `SharedTextChannel.start(onText)`·`sharedTextChannelProvider`·`pendingSharedTextProvider`(`Notifier<String?>`, `set`은 다듬고 1000자로 자름, `clear`)(`lib/core/proxy/shared_text_channel.dart`); `sharedTextToOpenProvider`(`lib/app.dart` — `SignedIn`이고 매장이 골라졌을 때만 값) 와 `App`의 `ref.listen`이 `/visits/draft`를 `push`; iOS: URL 스킴 `chagocnote`, App Group `group.com.chagocnote.app`(키 `sharedText`), 타깃 `ShareExtension`(번들 `com.chagocnote.app.ShareExtension`, `ios/ShareExtension/`), `Runner.entitlements`; 안드로이드: `ACTION_SEND` `text/plain` intent-filter, `launchMode="singleTask"`.

**pbxproj 는 손으로 편집한다**(아래 diff 그대로 — UUID 는 `A3A3…` 고정값). 확장은 글만 App Group 에 적고 `chagocnote://share`로 본체를 연 뒤 끝난다 — 토큰·키체인·네트워크에 접근하지 않는다(V12). 본체(`AppDelegate.swift`의 `SharedTextPlugin`)가 씬의 URL 열림(콜드 스타트는 연결 옵션, 떠 있으면 `openURLContexts`)을 받아 글을 읽고 지운 뒤 Dart 로 넘긴다. `SceneDelegate.swift`는 손대지 않는다. 시뮬레이터 빌드는 코드사인이 없어 App Group 이 실제로 붙는지는 실기기(개발 팀 서명)에서 확인한다(Task 9).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/core/proxy/shared_text_channel_test.dart`:

```dart
// 공유 받기(③-A3)의 Dart 쪽 — 네이티브 채널을 흉내 내 pending 글이 들어오고,
// 다듬어지고(앞뒤 공백·1000자), 비면 무시되는지 본다.
import 'package:chagocnote/core/proxy/shared_text_channel.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _channel = MethodChannel(SharedTextChannel.name);

void _mockPending(String? pending, List<String> calls) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_channel, (call) async {
        calls.add(call.method);
        return call.method == 'getPending' ? pending : null;
      });
  addTearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_channel, null),
  );
}

/// 네이티브가 Dart 를 부르는 것을 흉내 낸다.
Future<void> _nativeSends(String text) => TestDefaultBinaryMessengerBinding
    .instance
    .defaultBinaryMessenger
    .handlePlatformMessage(
      SharedTextChannel.name,
      const StandardMethodCodec().encodeMethodCall(
        MethodCall('onSharedText', text),
      ),
      (_) {},
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('시작 때 getPending 을 한 번 부르고, 받아 둔 글이 pending 에 들어간다', () async {
    final calls = <String>[];
    _mockPending('  내일 2시 두부  ', calls);
    final container = ProviderContainer.test();

    expect(container.read(pendingSharedTextProvider), isNull);
    await Future<void>.delayed(Duration.zero);
    expect(calls, ['getPending']);
    expect(container.read(pendingSharedTextProvider), '내일 2시 두부');
  });

  test('네이티브가 onSharedText 를 부르면 pending 이 바뀌고, 비우면 null 이다', () async {
    _mockPending(null, []);
    final container = ProviderContainer.test();
    container.read(pendingSharedTextProvider);
    await Future<void>.delayed(Duration.zero);

    await _nativeSends('모레 오후 3시 콩이 목욕');
    expect(container.read(pendingSharedTextProvider), '모레 오후 3시 콩이 목욕');

    container.read(pendingSharedTextProvider.notifier).clear();
    expect(container.read(pendingSharedTextProvider), isNull);
  });

  test('빈 글은 무시하고, 1000자를 넘으면 앞 1000자만 둔다', () async {
    _mockPending(null, []);
    final container = ProviderContainer.test();
    container.read(pendingSharedTextProvider);
    await Future<void>.delayed(Duration.zero);

    await _nativeSends('   ');
    expect(container.read(pendingSharedTextProvider), isNull);

    await _nativeSends('가' * 1200);
    expect(container.read(pendingSharedTextProvider)!.length, 1000);
  });

  test('채널이 없는 플랫폼(테스트·웹)에서는 조용히 넘어간다', () async {
    final container = ProviderContainer.test();
    container.read(pendingSharedTextProvider);
    await Future<void>.delayed(Duration.zero);
    expect(container.read(pendingSharedTextProvider), isNull);
  });
}
```

`app/test/features/visit/screens/shared_text_gate_test.dart`:

```dart
// 공유로 받은 글은 로그인·매장 선택이 끝난 뒤 초안 화면으로 간다(③-A3).
// 앱 루트(App)에 붙은 관문을 실제 라우터·세션과 함께 본다.
import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/shared_text_channel.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/visit_test_backend.dart';

const _channel = MethodChannel(SharedTextChannel.name);
const _text = '내일 2시반 두부 부분미용';

void _mockPending(String? pending) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(
        _channel,
        (call) async => call.method == 'getPending' ? pending : null,
      );
  addTearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_channel, null),
  );
}

Future<void> _nativeSends(String text) => TestDefaultBinaryMessengerBinding
    .instance
    .defaultBinaryMessenger
    .handlePlatformMessage(
      SharedTextChannel.name,
      const StandardMethodCodec().encodeMethodCall(
        MethodCall('onSharedText', text),
      ),
      (_) {},
    );

Future<CustomerTestSetup> _pumpApp(WidgetTester tester) async {
  useTallView(tester);
  final setup = CustomerTestSetup(
    VisitTestBackend().call,
    overrides: [todayProvider.overrideWithValue(DateTime(2026, 9, 23))],
  );
  addTearDown(setup.container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: setup.container,
      child: const GlassBridge(factory: OpaqueSurfaceFactory(), child: App()),
    ),
  );
  await settle(tester);
  return setup;
}

void main() {
  testWidgets('앱이 뜨기 전에 받아 둔 글(콜드 스타트)은 로그인·매장 선택 뒤 초안 화면으로 간다', (
    tester,
  ) async {
    _mockPending(_text);
    final setup = await _pumpApp(tester);

    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
    expect(find.text(_text), findsOneWidget);
    // 한 번 열었으면 비운다 — 다시 열리지 않게.
    expect(setup.container.read(pendingSharedTextProvider), isNull);
  });

  test('로그아웃 상태에서는 받아 둔 글을 열지 않고 들고 있다가, 로그인·매장 선택 뒤에 연다', () async {
    _mockPending(null);
    final setup = CustomerTestSetup(VisitTestBackend().call);
    addTearDown(setup.container.dispose);
    setup.gateway.meOnRestore = null;
    await setup.container.read(sessionControllerProvider.future);
    expect(
      setup.container.read(sessionControllerProvider).value,
      isA<SignedOut>(),
    );

    setup.container.read(pendingSharedTextProvider.notifier).set(_text);
    expect(setup.container.read(sharedTextToOpenProvider), isNull);
    expect(setup.container.read(pendingSharedTextProvider), _text);

    // 로그인해 매장이 골라지면 그때 연다.
    setup.gateway.meOnRestore = customerTestMe();
    setup.container.invalidate(sessionControllerProvider);
    await setup.container.read(sessionControllerProvider.future);
    expect(setup.container.read(sharedTextToOpenProvider), _text);
  });

  testWidgets('앱이 떠 있을 때 공유가 오면 초안 화면을 연다', (tester) async {
    _mockPending(null);
    await _pumpApp(tester);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);

    await _nativeSends(_text);
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test test/core/proxy/shared_text_channel_test.dart test/features/visit/screens/shared_text_gate_test.dart --timeout 20s`
Expected: 컴파일 오류(`SharedTextChannel`·`sharedTextToOpenProvider` 없음)로 실패.

- [ ] **Step 3: 구현한다**

`app/lib/core/proxy/shared_text_channel.dart`:

```dart
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 공유 받기(③-A3) — 네이티브(iOS 공유 확장 → 본체, 안드로이드 `ACTION_SEND`)가
/// 넘긴 글을 받는 채널. 오가는 것은 글뿐이다. 토큰과 서버 호출은 앱 본체의
/// 몫이다(설계 7절 — 확장은 글만 앱 본체에 넘기고 앱을 연다).
///
/// - 네이티브 → Dart: `onSharedText(text)`.
/// - Dart → 네이티브: `getPending()` — 앱(Dart)이 뜨기 전에 받아 둔 글을 한 번
///   가져온다(콜드 스타트). 네이티브는 준 뒤 비운다.
class SharedTextChannel {
  SharedTextChannel([MethodChannel? channel])
    : _channel = channel ?? const MethodChannel(name);

  static const name = 'com.chagocnote.app/share';

  final MethodChannel _channel;

  /// 네이티브의 호출을 받기 시작하고, 받아 둔 글이 있으면 [onText]로 넘긴다.
  Future<void> start(void Function(String text) onText) async {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onSharedText' && call.arguments is String) {
        onText(call.arguments as String);
      }
    });
    try {
      final pending = await _channel.invokeMethod<String>('getPending');
      if (pending != null) onText(pending);
    } on MissingPluginException {
      // 이 플랫폼에는 공유 받기가 없다(테스트·웹) — 조용히 넘어간다.
    }
  }
}

final sharedTextChannelProvider = Provider<SharedTextChannel>(
  (ref) => SharedTextChannel(),
);

/// 아직 열지 않은, 공유로 받은 글. 앱 루트가 로그인·매장 선택이 끝난 뒤
/// 초안 화면을 열고 [clear]한다.
class PendingSharedText extends Notifier<String?> {
  static const _maxLength = 1000;

  @override
  String? build() {
    // 처음 지켜보는 순간 채널을 연다. 받아 둔 글은 비동기로 들어온다.
    ref.read(sharedTextChannelProvider).start(set);
    return null;
  }

  /// 앞뒤 공백을 걷고 서버가 받는 길이(1000자)로 자른다. 비면 무시한다.
  void set(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    state = trimmed.length > _maxLength
        ? trimmed.substring(0, _maxLength)
        : trimmed;
  }

  void clear() => state = null;
}

final pendingSharedTextProvider = NotifierProvider<PendingSharedText, String?>(
  PendingSharedText.new,
);
```

`app/lib/app.dart`:

```diff
@@ -1,9 +1,20 @@
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import 'core/proxy/shared_text_channel.dart';
 import 'core/router/app_router.dart';
 import 'design/app_theme.dart';
 import 'design/bridge/glass_setup.dart';
+import 'features/auth/state/session.dart';
+import 'features/auth/state/session_controller.dart';
+
+/// 공유로 받은 글 가운데 지금 열 수 있는 것 — 로그인했고 매장을 골랐을 때만.
+/// 콜드 스타트에서 로그인 뒤에, 또는 앱이 떠 있을 때 바로 열린다(③-A3).
+final sharedTextToOpenProvider = Provider<String?>((ref) {
+  final session = ref.watch(sessionControllerProvider).value;
+  final text = ref.watch(pendingSharedTextProvider);
+  return session is SignedIn && session.selectedShopId != null ? text : null;
+});
 
 class App extends ConsumerWidget {
   const App({super.key});
@@ -11,6 +22,12 @@ class App extends ConsumerWidget {
   @override
   Widget build(BuildContext context, WidgetRef ref) {
     final router = ref.watch(routerProvider);
+    ref.listen<String?>(sharedTextToOpenProvider, (_, text) {
+      if (text == null) return;
+      // 한 번 열면 비운다 — 세션이 바뀌어도 다시 열리지 않게.
+      ref.read(pendingSharedTextProvider.notifier).clear();
+      router.push('/visits/draft', extra: text);
+    });
     return MaterialApp.router(
       routerConfig: router,
       title: '차곡노트',
```

`app/android/app/src/main/AndroidManifest.xml`:

```diff
@@ -7,7 +7,7 @@
         <activity
             android:name=".MainActivity"
             android:exported="true"
-            android:launchMode="singleTop"
+            android:launchMode="singleTask"
             android:taskAffinity=""
             android:theme="@style/LaunchTheme"
             android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
@@ -25,6 +25,12 @@
                 <action android:name="android.intent.action.MAIN"/>
                 <category android:name="android.intent.category.LAUNCHER"/>
             </intent-filter>
+            <!-- 공유 받기(③-A3): 카톡 등에서 [공유]한 글을 받는다. 글(text/plain)만. -->
+            <intent-filter>
+                <action android:name="android.intent.action.SEND"/>
+                <category android:name="android.intent.category.DEFAULT"/>
+                <data android:mimeType="text/plain"/>
+            </intent-filter>
         </activity>
         <!-- Don't delete the meta-data below.
              This is used by the Flutter tool to generate GeneratedPluginRegistrant.java -->
```

`app/android/app/src/main/kotlin/com/chagocnote/chagocnote/MainActivity.kt`:

```diff
@@ -1,5 +1,58 @@
 package com.chagocnote.chagocnote
 
+import android.content.Intent
+import android.os.Bundle
 import io.flutter.embedding.android.FlutterActivity
+import io.flutter.embedding.engine.FlutterEngine
+import io.flutter.plugin.common.MethodChannel
 
-class MainActivity : FlutterActivity()
+/**
+ * 공유 받기(③-A3) — 다른 앱이 ACTION_SEND 로 넘긴 글을 Dart 로 전한다.
+ *
+ * 글만 오간다. 토큰·서버 호출은 Dart(앱 본체)가 한다. Dart 가 아직 뜨기 전에
+ * 온 글은 들고 있다가 `getPending` 으로 준다(콜드 스타트). 떠 있으면 바로
+ * `onSharedText` 로 부른다(launchMode 가 singleTask 라 onNewIntent 로 온다).
+ */
+class MainActivity : FlutterActivity() {
+    private var channel: MethodChannel? = null
+    private var pending: String? = null
+
+    override fun onCreate(savedInstanceState: Bundle?) {
+        super.onCreate(savedInstanceState)
+        take(intent)
+    }
+
+    override fun onNewIntent(intent: Intent) {
+        super.onNewIntent(intent)
+        setIntent(intent)
+        take(intent)
+    }
+
+    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
+        super.configureFlutterEngine(flutterEngine)
+        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).also { ch ->
+            ch.setMethodCallHandler { call, result ->
+                if (call.method == "getPending") {
+                    result.success(pending)
+                    pending = null
+                } else {
+                    result.notImplemented()
+                }
+            }
+        }
+    }
+
+    private fun take(intent: Intent?) {
+        if (intent?.action != Intent.ACTION_SEND || intent.type?.startsWith("text/") != true) return
+        val text = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim().orEmpty()
+        // 회전 등으로 같은 인텐트를 다시 읽지 않게 비운다.
+        intent.removeExtra(Intent.EXTRA_TEXT)
+        if (text.isEmpty()) return
+        val ch = channel
+        if (ch != null) ch.invokeMethod("onSharedText", text) else pending = text
+    }
+
+    private companion object {
+        const val CHANNEL = "com.chagocnote.app/share"
+    }
+}
```

`app/ios/Runner/Info.plist`:

```diff
@@ -24,6 +24,19 @@
 	<string>????</string>
 	<key>CFBundleVersion</key>
 	<string>$(FLUTTER_BUILD_NUMBER)</string>
+	<key>CFBundleURLTypes</key>
+	<array>
+		<dict>
+			<key>CFBundleTypeRole</key>
+			<string>Editor</string>
+			<key>CFBundleURLName</key>
+			<string>com.chagocnote.app</string>
+			<key>CFBundleURLSchemes</key>
+			<array>
+				<string>chagocnote</string>
+			</array>
+		</dict>
+	</array>
 	<key>LSRequiresIPhoneOS</key>
 	<true/>
 	<key>NSAppTransportSecurity</key>
```

`app/ios/Runner/Runner.entitlements`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>com.apple.security.application-groups</key>
	<array>
		<string>group.com.chagocnote.app</string>
	</array>
</dict>
</plist>
```

`app/ios/Runner/AppDelegate.swift`:

```diff
@@ -12,5 +12,75 @@ import UIKit
 
   func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
     GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
+    SharedTextPlugin.register(with: engineBridge.pluginRegistry.registrar(forPlugin: "SharedTextPlugin")!)
+  }
+}
+
+/// 공유 받기(③-A3) — 공유 확장이 App Group 에 남긴 글을 Dart 로 넘긴다.
+///
+/// 확장은 글을 적고 `chagocnote://share` 로 본체를 연다. 이 플러그인은 씬의
+/// URL 열림(콜드 스타트는 연결 옵션, 떠 있으면 openURLContexts)을 받아 글을
+/// 읽고 지운 뒤 `onSharedText` 로 부른다. Dart 가 아직 준비 전이면 들고 있다가
+/// `getPending` 으로 준다. 토큰·서버 호출은 없다 — Dart 의 몫이다.
+final class SharedTextPlugin: NSObject, FlutterPlugin, FlutterSceneLifeCycleDelegate {
+  static let channelName = "com.chagocnote.app/share"
+  static let appGroup = "group.com.chagocnote.app"
+  static let sharedTextKey = "sharedText"
+
+  private let channel: FlutterMethodChannel
+  private var pending: String?
+
+  static func register(with registrar: FlutterPluginRegistrar) {
+    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: registrar.messenger())
+    let plugin = SharedTextPlugin(channel: channel)
+    registrar.addMethodCallDelegate(plugin, channel: channel)
+    registrar.addSceneDelegate(plugin)
+  }
+
+  private init(channel: FlutterMethodChannel) {
+    self.channel = channel
+    super.init()
+  }
+
+  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
+    guard call.method == "getPending" else {
+      result(FlutterMethodNotImplemented)
+      return
+    }
+    // 준비 전에 들고 있던 글, 없으면 App Group 에 남은 글(연결 옵션을 놓친 경우의 안전망).
+    let text = pending ?? takeFromAppGroup()
+    pending = nil
+    result(text)
+  }
+
+  func scene(_ scene: UIScene, willConnectTo session: UISceneSession,
+             options connectionOptions: UIScene.ConnectionOptions?) -> Bool {
+    guard let contexts = connectionOptions?.urlContexts else { return false }
+    return open(contexts)
+  }
+
+  func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) -> Bool {
+    return open(URLContexts)
+  }
+
+  private func open(_ contexts: Set<UIOpenURLContext>) -> Bool {
+    guard contexts.contains(where: { $0.url.scheme == "chagocnote" && $0.url.host == "share" }),
+          let text = takeFromAppGroup() else { return false }
+    // Dart 쪽 핸들러가 아직 없으면 invoke 가 버려진다 — 들고 있다가 getPending 으로 준다.
+    pending = text
+    channel.invokeMethod("onSharedText", arguments: text) { [weak self] reply in
+      if !(reply is FlutterError) && reply as? NSObject != FlutterMethodNotImplemented {
+        self?.pending = nil
+      }
+    }
+    return true
+  }
+
+  private func takeFromAppGroup() -> String? {
+    let defaults = UserDefaults(suiteName: SharedTextPlugin.appGroup)
+    guard let text = defaults?.string(forKey: SharedTextPlugin.sharedTextKey) else { return nil }
+    defaults?.removeObject(forKey: SharedTextPlugin.sharedTextKey)
+    let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
+    return trimmed.isEmpty ? nil : trimmed
   }
 }
```

`app/ios/ShareExtension/ShareViewController.swift`:

```swift
import UIKit
import UniformTypeIdentifiers

/// 카톡 등에서 [공유] → 차곡노트(③-A3, 설계 7절).
///
/// 글만 App Group 에 적고 본체 앱을 연 뒤 바로 끝난다 — 화면을 그리지 않는다.
/// 토큰·키체인·네트워크에 접근하지 않는다. 서버 호출은 본체가 한다.
final class ShareViewController: UIViewController {
  private static let appGroup = "group.com.chagocnote.app"
  private static let sharedTextKey = "sharedText"
  private static let hostURL = URL(string: "chagocnote://share")!
  private static let maxLength = 1000

  override func viewDidLoad() {
    super.viewDidLoad()
    view.backgroundColor = .clear
    let items = (extensionContext?.inputItems as? [NSExtensionItem]) ?? []
    let providers = items.flatMap { $0.attachments ?? [] }
    guard let provider = providers.first(where: {
      $0.hasItemConformingToTypeIdentifier(UTType.plainText.identifier)
    }) else {
      finish()
      return
    }
    provider.loadItem(forTypeIdentifier: UTType.plainText.identifier, options: nil) { [weak self] data, _ in
      let text = (data as? String)
        ?? (data as? NSAttributedString)?.string
        ?? (data as? Data).flatMap { String(data: $0, encoding: .utf8) }
      DispatchQueue.main.async {
        guard let self else { return }
        if let text = text?.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
          UserDefaults(suiteName: Self.appGroup)?
            .set(String(text.prefix(Self.maxLength)), forKey: Self.sharedTextKey)
          self.openHostApp()
        }
        self.finish()
      }
    }
  }

  /// 확장에서 본체를 여는 공식 API 는 없다 — 응답자 체인에서 UIApplication 을
  /// 찾아 `openURL:` 을 부른다(널리 쓰이는 방법).
  private func openHostApp() {
    let selector = sel_registerName("openURL:")
    var responder: UIResponder? = self
    while let current = responder {
      if current.responds(to: selector) && !(current is UIViewController) {
        current.perform(selector, with: Self.hostURL)
        return
      }
      responder = current.next
    }
  }

  private func finish() {
    extensionContext?.completeRequest(returningItems: nil)
  }
}
```

`app/ios/ShareExtension/Info.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>$(DEVELOPMENT_LANGUAGE)</string>
	<key>CFBundleDisplayName</key>
	<string>차곡노트</string>
	<key>CFBundleExecutable</key>
	<string>$(EXECUTABLE_NAME)</string>
	<key>CFBundleIdentifier</key>
	<string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>$(PRODUCT_NAME)</string>
	<key>CFBundlePackageType</key>
	<string>XPC!</string>
	<key>CFBundleShortVersionString</key>
	<string>$(FLUTTER_BUILD_NAME)</string>
	<key>CFBundleVersion</key>
	<string>$(FLUTTER_BUILD_NUMBER)</string>
	<key>NSExtension</key>
	<dict>
		<key>NSExtensionAttributes</key>
		<dict>
			<key>NSExtensionActivationRule</key>
			<dict>
				<key>NSExtensionActivationSupportsText</key>
				<true/>
			</dict>
		</dict>
		<key>NSExtensionPointIdentifier</key>
		<string>com.apple.share-services</string>
		<key>NSExtensionPrincipalClass</key>
		<string>$(PRODUCT_MODULE_NAME).ShareViewController</string>
	</dict>
</dict>
</plist>
```

`app/ios/ShareExtension/ShareExtension.entitlements`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>com.apple.security.application-groups</key>
	<array>
		<string>group.com.chagocnote.app</string>
	</array>
</dict>
</plist>
```

`app/ios/Runner.xcodeproj/project.pbxproj`:

```diff
@@ -16,6 +16,8 @@
 		97C146FC1CF9000F007C117D /* Main.storyboard in Resources */ = {isa = PBXBuildFile; fileRef = 97C146FA1CF9000F007C117D /* Main.storyboard */; };
 		97C146FE1CF9000F007C117D /* Assets.xcassets in Resources */ = {isa = PBXBuildFile; fileRef = 97C146FD1CF9000F007C117D /* Assets.xcassets */; };
 		97C147011CF9000F007C117D /* LaunchScreen.storyboard in Resources */ = {isa = PBXBuildFile; fileRef = 97C146FF1CF9000F007C117D /* LaunchScreen.storyboard */; };
+		A3A3000000000000000000A1 /* ShareViewController.swift in Sources */ = {isa = PBXBuildFile; fileRef = A3A3000000000000000000B1 /* ShareViewController.swift */; };
+		A3A3000000000000000000A2 /* ShareExtension.appex in Embed Foundation Extensions */ = {isa = PBXBuildFile; fileRef = A3A3000000000000000000B2 /* ShareExtension.appex */; settings = {ATTRIBUTES = (RemoveHeadersOnCopy, ); }; };
 /* End PBXBuildFile section */
 
 /* Begin PBXContainerItemProxy section */
@@ -26,6 +28,13 @@
 			remoteGlobalIDString = 97C146ED1CF9000F007C117D;
 			remoteInfo = Runner;
 		};
+		A3A3000000000000000000C1 /* PBXContainerItemProxy */ = {
+			isa = PBXContainerItemProxy;
+			containerPortal = 97C146E61CF9000F007C117D /* Project object */;
+			proxyType = 1;
+			remoteGlobalIDString = A3A3000000000000000000D1;
+			remoteInfo = ShareExtension;
+		};
 /* End PBXContainerItemProxy section */
 
 /* Begin PBXCopyFilesBuildPhase section */
@@ -39,6 +48,17 @@
 			name = "Embed Frameworks";
 			runOnlyForDeploymentPostprocessing = 0;
 		};
+		A3A3000000000000000000C2 /* Embed Foundation Extensions */ = {
+			isa = PBXCopyFilesBuildPhase;
+			buildActionMask = 2147483647;
+			dstPath = "";
+			dstSubfolderSpec = 13;
+			files = (
+				A3A3000000000000000000A2 /* ShareExtension.appex in Embed Foundation Extensions */,
+			);
+			name = "Embed Foundation Extensions";
+			runOnlyForDeploymentPostprocessing = 0;
+		};
 /* End PBXCopyFilesBuildPhase section */
 
 /* Begin PBXFileReference section */
@@ -59,6 +79,11 @@
 		97C146FD1CF9000F007C117D /* Assets.xcassets */ = {isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = "<group>"; };
 		97C147001CF9000F007C117D /* Base */ = {isa = PBXFileReference; lastKnownFileType = file.storyboard; name = Base; path = Base.lproj/LaunchScreen.storyboard; sourceTree = "<group>"; };
 		97C147021CF9000F007C117D /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };
+		A3A3000000000000000000B1 /* ShareViewController.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ShareViewController.swift; sourceTree = "<group>"; };
+		A3A3000000000000000000B2 /* ShareExtension.appex */ = {isa = PBXFileReference; explicitFileType = "wrapper.app-extension"; includeInIndex = 0; path = ShareExtension.appex; sourceTree = BUILT_PRODUCTS_DIR; };
+		A3A3000000000000000000B3 /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };
+		A3A3000000000000000000B4 /* ShareExtension.entitlements */ = {isa = PBXFileReference; lastKnownFileType = text.plist.entitlements; path = ShareExtension.entitlements; sourceTree = "<group>"; };
+		A3A3000000000000000000B5 /* Runner.entitlements */ = {isa = PBXFileReference; lastKnownFileType = text.plist.entitlements; path = Runner.entitlements; sourceTree = "<group>"; };
 /* End PBXFileReference section */
 
 /* Begin PBXFrameworksBuildPhase section */
@@ -70,6 +95,13 @@
 			);
 			runOnlyForDeploymentPostprocessing = 0;
 		};
+		A3A3000000000000000000C3 /* Frameworks */ = {
+			isa = PBXFrameworksBuildPhase;
+			buildActionMask = 2147483647;
+			files = (
+			);
+			runOnlyForDeploymentPostprocessing = 0;
+		};
 /* End PBXFrameworksBuildPhase section */
 
 /* Begin PBXGroup section */
@@ -98,6 +130,7 @@
 			children = (
 				9740EEB11CF90186004384FC /* Flutter */,
 				97C146F01CF9000F007C117D /* Runner */,
+				A3A3000000000000000000C4 /* ShareExtension */,
 				97C146EF1CF9000F007C117D /* Products */,
 				331C8082294A63A400263BE5 /* RunnerTests */,
 			);
@@ -108,6 +141,7 @@
 			children = (
 				97C146EE1CF9000F007C117D /* Runner.app */,
 				331C8081294A63A400263BE5 /* RunnerTests.xctest */,
+				A3A3000000000000000000B2 /* ShareExtension.appex */,
 			);
 			name = Products;
 			sourceTree = "<group>";
@@ -124,10 +158,21 @@
 				74858FAE1ED2DC5600515810 /* AppDelegate.swift */,
 				7884E8672EC3CC0400C636F2 /* SceneDelegate.swift */,
 				74858FAD1ED2DC5600515810 /* Runner-Bridging-Header.h */,
+				A3A3000000000000000000B5 /* Runner.entitlements */,
 			);
 			path = Runner;
 			sourceTree = "<group>";
 		};
+		A3A3000000000000000000C4 /* ShareExtension */ = {
+			isa = PBXGroup;
+			children = (
+				A3A3000000000000000000B1 /* ShareViewController.swift */,
+				A3A3000000000000000000B3 /* Info.plist */,
+				A3A3000000000000000000B4 /* ShareExtension.entitlements */,
+			);
+			path = ShareExtension;
+			sourceTree = "<group>";
+		};
 /* End PBXGroup section */
 
 /* Begin PBXNativeTarget section */
@@ -157,11 +202,13 @@
 				97C146EB1CF9000F007C117D /* Frameworks */,
 				97C146EC1CF9000F007C117D /* Resources */,
 				9705A1C41CF9048500538489 /* Embed Frameworks */,
+				A3A3000000000000000000C2 /* Embed Foundation Extensions */,
 				3B06AD1E1E4923F5004D2608 /* Thin Binary */,
 			);
 			buildRules = (
 			);
 			dependencies = (
+				A3A3000000000000000000D3 /* PBXTargetDependency */,
 			);
 			name = Runner;
 			packageProductDependencies = (
@@ -171,6 +218,23 @@
 			productReference = 97C146EE1CF9000F007C117D /* Runner.app */;
 			productType = "com.apple.product-type.application";
 		};
+		A3A3000000000000000000D1 /* ShareExtension */ = {
+			isa = PBXNativeTarget;
+			buildConfigurationList = A3A3000000000000000000D2 /* Build configuration list for PBXNativeTarget "ShareExtension" */;
+			buildPhases = (
+				A3A3000000000000000000C5 /* Sources */,
+				A3A3000000000000000000C3 /* Frameworks */,
+				A3A3000000000000000000C6 /* Resources */,
+			);
+			buildRules = (
+			);
+			dependencies = (
+			);
+			name = ShareExtension;
+			productName = ShareExtension;
+			productReference = A3A3000000000000000000B2 /* ShareExtension.appex */;
+			productType = "com.apple.product-type.app-extension";
+		};
 /* End PBXNativeTarget section */
 
 /* Begin PBXProject section */
@@ -189,6 +253,9 @@
 						CreatedOnToolsVersion = 7.3.1;
 						LastSwiftMigration = 1100;
 					};
+					A3A3000000000000000000D1 = {
+						CreatedOnToolsVersion = 15.0;
+					};
 				};
 			};
 			buildConfigurationList = 97C146E91CF9000F007C117D /* Build configuration list for PBXProject "Runner" */;
@@ -209,6 +276,7 @@
 			targets = (
 				97C146ED1CF9000F007C117D /* Runner */,
 				331C8080294A63A400263BE5 /* RunnerTests */,
+				A3A3000000000000000000D1 /* ShareExtension */,
 			);
 		};
 /* End PBXProject section */
@@ -232,6 +300,13 @@
 			);
 			runOnlyForDeploymentPostprocessing = 0;
 		};
+		A3A3000000000000000000C6 /* Resources */ = {
+			isa = PBXResourcesBuildPhase;
+			buildActionMask = 2147483647;
+			files = (
+			);
+			runOnlyForDeploymentPostprocessing = 0;
+		};
 /* End PBXResourcesBuildPhase section */
 
 /* Begin PBXShellScriptBuildPhase section */
@@ -287,6 +362,14 @@
 			);
 			runOnlyForDeploymentPostprocessing = 0;
 		};
+		A3A3000000000000000000C5 /* Sources */ = {
+			isa = PBXSourcesBuildPhase;
+			buildActionMask = 2147483647;
+			files = (
+				A3A3000000000000000000A1 /* ShareViewController.swift in Sources */,
+			);
+			runOnlyForDeploymentPostprocessing = 0;
+		};
 /* End PBXSourcesBuildPhase section */
 
 /* Begin PBXTargetDependency section */
@@ -295,6 +378,11 @@
 			target = 97C146ED1CF9000F007C117D /* Runner */;
 			targetProxy = 331C8085294A63A400263BE5 /* PBXContainerItemProxy */;
 		};
+		A3A3000000000000000000D3 /* PBXTargetDependency */ = {
+			isa = PBXTargetDependency;
+			target = A3A3000000000000000000D1 /* ShareExtension */;
+			targetProxy = A3A3000000000000000000C1 /* PBXContainerItemProxy */;
+		};
 /* End PBXTargetDependency section */
 
 /* Begin PBXVariantGroup section */
@@ -375,6 +463,7 @@
 			buildSettings = {
 				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
 				CLANG_ENABLE_MODULES = YES;
+				CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;
 				CURRENT_PROJECT_VERSION = "$(FLUTTER_BUILD_NUMBER)";
 				ENABLE_BITCODE = NO;
 				INFOPLIST_FILE = Runner/Info.plist;
@@ -554,6 +643,7 @@
 			buildSettings = {
 				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
 				CLANG_ENABLE_MODULES = YES;
+				CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;
 				CURRENT_PROJECT_VERSION = "$(FLUTTER_BUILD_NUMBER)";
 				ENABLE_BITCODE = NO;
 				INFOPLIST_FILE = Runner/Info.plist;
@@ -576,6 +666,7 @@
 			buildSettings = {
 				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
 				CLANG_ENABLE_MODULES = YES;
+				CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;
 				CURRENT_PROJECT_VERSION = "$(FLUTTER_BUILD_NUMBER)";
 				ENABLE_BITCODE = NO;
 				INFOPLIST_FILE = Runner/Info.plist;
@@ -591,6 +682,86 @@
 			};
 			name = Release;
 		};
+		A3A3000000000000000000E1 /* Debug */ = {
+			isa = XCBuildConfiguration;
+			baseConfigurationReference = 9740EEB21CF90195004384FC /* Debug.xcconfig */;
+			buildSettings = {
+				APPLICATION_EXTENSION_API_ONLY = YES;
+				CODE_SIGN_ENTITLEMENTS = ShareExtension/ShareExtension.entitlements;
+				CODE_SIGN_STYLE = Automatic;
+				CURRENT_PROJECT_VERSION = "$(FLUTTER_BUILD_NUMBER)";
+				GENERATE_INFOPLIST_FILE = NO;
+				INFOPLIST_FILE = ShareExtension/Info.plist;
+				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
+				LD_RUNPATH_SEARCH_PATHS = (
+					"$(inherited)",
+					"@executable_path/Frameworks",
+					"@executable_path/../../Frameworks",
+				);
+				MARKETING_VERSION = "$(FLUTTER_BUILD_NAME)";
+				PRODUCT_BUNDLE_IDENTIFIER = com.chagocnote.app.ShareExtension;
+				PRODUCT_NAME = "$(TARGET_NAME)";
+				SKIP_INSTALL = YES;
+				SWIFT_EMIT_LOC_STRINGS = YES;
+				SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;
+				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
+				SWIFT_VERSION = 5.0;
+				TARGETED_DEVICE_FAMILY = "1,2";
+			};
+			name = Debug;
+		};
+		A3A3000000000000000000E2 /* Release */ = {
+			isa = XCBuildConfiguration;
+			baseConfigurationReference = 7AFA3C8E1D35360C0083082E /* Release.xcconfig */;
+			buildSettings = {
+				APPLICATION_EXTENSION_API_ONLY = YES;
+				CODE_SIGN_ENTITLEMENTS = ShareExtension/ShareExtension.entitlements;
+				CODE_SIGN_STYLE = Automatic;
+				CURRENT_PROJECT_VERSION = "$(FLUTTER_BUILD_NUMBER)";
+				GENERATE_INFOPLIST_FILE = NO;
+				INFOPLIST_FILE = ShareExtension/Info.plist;
+				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
+				LD_RUNPATH_SEARCH_PATHS = (
+					"$(inherited)",
+					"@executable_path/Frameworks",
+					"@executable_path/../../Frameworks",
+				);
+				MARKETING_VERSION = "$(FLUTTER_BUILD_NAME)";
+				PRODUCT_BUNDLE_IDENTIFIER = com.chagocnote.app.ShareExtension;
+				PRODUCT_NAME = "$(TARGET_NAME)";
+				SKIP_INSTALL = YES;
+				SWIFT_EMIT_LOC_STRINGS = YES;
+				SWIFT_VERSION = 5.0;
+				TARGETED_DEVICE_FAMILY = "1,2";
+			};
+			name = Release;
+		};
+		A3A3000000000000000000E3 /* Profile */ = {
+			isa = XCBuildConfiguration;
+			baseConfigurationReference = 7AFA3C8E1D35360C0083082E /* Release.xcconfig */;
+			buildSettings = {
+				APPLICATION_EXTENSION_API_ONLY = YES;
+				CODE_SIGN_ENTITLEMENTS = ShareExtension/ShareExtension.entitlements;
+				CODE_SIGN_STYLE = Automatic;
+				CURRENT_PROJECT_VERSION = "$(FLUTTER_BUILD_NUMBER)";
+				GENERATE_INFOPLIST_FILE = NO;
+				INFOPLIST_FILE = ShareExtension/Info.plist;
+				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
+				LD_RUNPATH_SEARCH_PATHS = (
+					"$(inherited)",
+					"@executable_path/Frameworks",
+					"@executable_path/../../Frameworks",
+				);
+				MARKETING_VERSION = "$(FLUTTER_BUILD_NAME)";
+				PRODUCT_BUNDLE_IDENTIFIER = com.chagocnote.app.ShareExtension;
+				PRODUCT_NAME = "$(TARGET_NAME)";
+				SKIP_INSTALL = YES;
+				SWIFT_EMIT_LOC_STRINGS = YES;
+				SWIFT_VERSION = 5.0;
+				TARGETED_DEVICE_FAMILY = "1,2";
+			};
+			name = Profile;
+		};
 /* End XCBuildConfiguration section */
 
 /* Begin XCConfigurationList section */
@@ -624,6 +795,16 @@
 			defaultConfigurationIsVisible = 0;
 			defaultConfigurationName = Release;
 		};
+		A3A3000000000000000000D2 /* Build configuration list for PBXNativeTarget "ShareExtension" */ = {
+			isa = XCConfigurationList;
+			buildConfigurations = (
+				A3A3000000000000000000E1 /* Debug */,
+				A3A3000000000000000000E2 /* Release */,
+				A3A3000000000000000000E3 /* Profile */,
+			);
+			defaultConfigurationIsVisible = 0;
+			defaultConfigurationName = Release;
+		};
 /* End XCConfigurationList section */
 
 /* Begin XCLocalSwiftPackageReference section */
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test test/core/proxy/shared_text_channel_test.dart test/features/visit/screens/shared_text_gate_test.dart --timeout 20s` → 통과(이 작업 7: 채널 4, 관문 3)

Run (`app/`): `flutter test --timeout 30s` → 전부 통과(496개)

Run (`app/`): `flutter analyze` → `No issues found!`

- [ ] **Step 5: 네이티브 빌드를 확인한다**

Run (`app/`): `xcodebuild -list -project ios/Runner.xcodeproj` → Targets 에 `Runner`·`RunnerTests`·`ShareExtension`

Run (`app/`): `flutter build ios --simulator` → 통과. `ls build/ios/iphonesimulator/Runner.app/PlugIns/` 에 `ShareExtension.appex`, `plutil -p build/ios/iphonesimulator/Runner.app/PlugIns/ShareExtension.appex/Info.plist | grep NSExtensionPointIdentifier` → `com.apple.share-services`

Run (`app/`): `flutter build apk --debug` → 통과

빌드가 깨지면 Swift 오류 문구를 그대로 보고한다(참조 구현에서는 `UIScene.ConnectionOptions` 형 이름 하나를 고쳤다). pbxproj 편집이 잘못돼 Xcode 가 프로젝트를 못 열면 멈추고 보고한다 — GUI 대안은 File → New → Target → Share Extension(이름 `ShareExtension`, 언어 Swift, storyboard 없음)을 만든 뒤 이 작업의 `ShareViewController.swift`·`Info.plist`·entitlements 로 바꿔 넣고 두 타깃에 App Group 을 켜는 것이다.

- [ ] **Step 6: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `SharedTextChannel.start`의 `if (pending != null) onText(pending)`을 뺀다 → `시작 때 getPending 을 한 번 부르고, 받아 둔 글이 pending 에 들어간다` 실패.
- `PendingSharedText.set`의 `if (trimmed.isEmpty) return`을 뺀다 → `빈 글은 무시하고, 1000자를 넘으면 앞 1000자만 둔다` 실패.
- 같은 메서드의 1000자 자르기를 뺀다 → 같은 테스트 실패.
- `App`의 `ref.listen`에서 `clear()`를 뺀다 → `앱이 떠 있을 때 공유가 오면 초안 화면을 연다` 실패(두 번 열린다).
- `sharedTextToOpenProvider`의 `session is SignedIn && session.selectedShopId != null` 조건을 뺀다 → `로그아웃 상태에서는 받아 둔 글을 열지 않고 들고 있다가…` 실패.

- [ ] **Step 7: 커밋한다**

```bash
git add -A
git commit -m "feat(visit): 공유 받기 — iOS 공유 확장·안드로이드 ACTION_SEND 가 글만 본체에 넘기고 초안 화면을 연다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 앱 — 스낵바 관례 `AppSnackBar`와 `VISIT_DUPLICATE` 안내

**Files:**
- Create: `app/lib/design/widgets/app_snack_bar.dart`
- Modify: `app/lib/features/visit/screens/register_visit_screen.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Create: `app/test/design/app_snack_bar_test.dart`
- Modify: `app/test/features/visit/screens/register_visit_screen_test.dart`

**Interfaces:**
- Consumes: `ScaffoldMessenger`, `AppColors.ink/white`·`AppTypography.body`·`AppRadius`, Task 4 의 `RegisterVisitScreen._save`의 `VISIT_DUPLICATE` 분기.
- Produces: `AppSnackBar.show(BuildContext context, String text)`(`lib/design/widgets/app_snack_bar.dart`) — 검정 바탕·흰 글자·둥근 모서리·floating, 화면이 닫힌 뒤에도 남는다; `AppStrings.duplicateVisitNotice`.

닫는 동작은 그대로다(날짜를 돌려주며 pop). 저장 두 번(이미 저장됨)과 다음 예약 ②에서 한 아이가 이미 예약된 경우(서버가 전체를 되돌려 아무것도 저장되지 않음) 둘 다 같은 문구다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/app_snack_bar_test.dart`:

```dart
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_snack_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('앱 톤(잉크 바탕·흰 글자)의 스낵바를 띄우고, 화면이 닫힌 뒤에도 남는다', (tester) async {
    final navigatorKey = GlobalKey<NavigatorState>();
    await tester.pumpWidget(
      MaterialApp(
        navigatorKey: navigatorKey,
        home: const Scaffold(body: SizedBox()),
      ),
    );
    navigatorKey.currentState!.push(
      MaterialPageRoute<void>(
        builder: (context) => Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () {
                AppSnackBar.show(context, '이미 저장됐어요');
                Navigator.of(context).pop();
              },
              child: const Text('닫기'),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('닫기'));
    await tester.pumpAndSettle();

    expect(find.text('닫기'), findsNothing);
    expect(find.text('이미 저장됐어요'), findsOneWidget);
    final bar = tester.widget<SnackBar>(find.byType(SnackBar));
    expect(bar.backgroundColor, AppColors.ink);
    expect(bar.behavior, SnackBarBehavior.floating);
    final text = tester.widget<Text>(find.text('이미 저장됐어요'));
    expect(text.style?.color, AppColors.white);
  });
}
```

`app/test/features/visit/screens/register_visit_screen_test.dart`:

```diff
@@ -352,6 +352,34 @@ void main() {
 
     expect(result.closed, isTrue);
     expect(result.value, DateTime(2026, 10, 2));
+    // 닫힌 뒤 홈 위에 스낵바로 알린다(A2 잔여 — 설계 6.2 "이미 저장됐어요").
+    expect(find.text(AppStrings.duplicateVisitNotice), findsOneWidget);
+  });
+
+  testWidgets('다음 예약 초안의 저장이 VISIT_DUPLICATE 면(한 아이가 이미 예약됨) 문구를 보이고 닫는다', (
+    tester,
+  ) async {
+    final backend = VisitTestBackend();
+    backend.routes['POST /v1/shops/3/visits'] = (o, b) => const FakeResponse(
+      statusCode: 409,
+      data: {'code': 'VISIT_DUPLICATE', 'message': 'x'},
+    );
+    final setup = CustomerTestSetup(backend.call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    final result = await _open(
+      tester,
+      setup,
+      path: '/visits/new',
+      extra: NextVisitDraft.fromJson(nextDraftJson(petIds: [11, 12])),
+    );
+
+    await tester.tap(_save());
+    await settle(tester);
+
+    expect(result.closed, isTrue);
+    expect(result.value, DateTime(2026, 10, 30));
+    expect(find.text(AppStrings.duplicateVisitNotice), findsOneWidget);
+    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
   });
 
   testWidgets('서버가 거절하면 문구를 보이고 폼에 남는다', (tester) async {
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test test/design/app_snack_bar_test.dart test/features/visit/screens/register_visit_screen_test.dart --timeout 20s`
Expected: 컴파일 오류(`AppSnackBar`·`duplicateVisitNotice` 없음)로 실패.

- [ ] **Step 3: 구현한다**

`app/lib/design/widgets/app_snack_bar.dart`:

```dart
import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// 화면 아래에 잠깐 떠서 알리는 한 줄("이미 같은 시각에 잡힌 예약이 있어요").
///
/// 루트 `MaterialApp`의 `ScaffoldMessenger`에 띄우므로, 부른 화면이 곧 닫혀도
/// 그 아래 화면 위에 남는다. 확인이 필요한 일에는 시트를 쓴다 — 이것은
/// 답을 받지 않는 알림이다.
abstract final class AppSnackBar {
  static void show(BuildContext context, String text) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            text,
            style: AppTypography.body.copyWith(color: AppColors.white),
          ),
          backgroundColor: AppColors.ink,
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            0,
            AppSpacing.lg,
            AppSpacing.lg,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          duration: const Duration(seconds: 3),
        ),
      );
  }
}
```

`app/lib/features/visit/screens/register_visit_screen.dart`:

```diff
@@ -14,6 +14,7 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_back_button.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_card.dart';
+import '../../../design/widgets/app_snack_bar.dart';
 import '../../../design/widgets/pressable.dart';
 import '../../../l10n/app_strings.dart';
 import '../../auth/state/session.dart';
@@ -96,9 +97,12 @@ class _RegisterVisitScreenState extends ConsumerState<RegisterVisitScreen> {
       // 서버가 저장한 날짜를 돌려준다 — [지금 시작]은 보던 날과 다를 수 있다.
       if (mounted) context.pop(saved.visits.first.startsAt.day);
     } on ApiException catch (e) {
-      // 저장을 두 번 누른 경우다 — 이미 저장됐으니 닫는다(결정 기록 006).
+      // 저장을 두 번 눌렀거나(이미 저장됐다), 다음 예약의 한 아이가 그 시각에
+      // 이미 예약돼 있다(아무것도 저장되지 않았다). 둘 다 그날 목록을 보면
+      // 알 수 있으니 알리고 그날로 닫는다(결정 기록 006, ③-A3).
       if (e.code == 'VISIT_DUPLICATE') {
         if (mounted) {
+          AppSnackBar.show(context, AppStrings.duplicateVisitNotice);
           final today = ref.read(todayProvider);
           context.pop(
             walkIn ? DateTime(today.year, today.month, today.day) : value.date,
```

`app/lib/l10n/app_strings.dart`:

```diff
@@ -260,6 +260,8 @@ class AppStrings {
   static const draftFindCustomer = '고객 찾기';
   static const draftHint = '확인한 뒤 저장돼요. 짐작한 칸은 다음 화면에서 고칠 수 있어요.';
 
+  static const duplicateVisitNotice = '이미 같은 시각에 잡힌 예약이 있어요. 그날 목록을 확인해 주세요.';
+
   static const editVisitTitle = '예약 수정';
   static const moveTogether = '같이 옮기기';
   static const moveOnlyThis = '이 방문만';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test test/design/app_snack_bar_test.dart test/features/visit/screens/register_visit_screen_test.dart --timeout 20s` → 통과(이 작업 2: 스낵바 1, 다음 예약 409 1 + 기존 `저장을 두 번 눌러…` 확장)

Run (`app/`): `flutter test --timeout 30s` → 전부 통과(497개)

Run (`app/`): `flutter analyze` → `No issues found!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_save`의 `AppSnackBar.show(context, AppStrings.duplicateVisitNotice)`를 뺀다 → `저장을 두 번 눌러 VISIT_DUPLICATE 면 이미 저장된 것으로 보고 닫는다`·`다음 예약 초안의 저장이 VISIT_DUPLICATE 면(한 아이가 이미 예약됨) 문구를 보이고 닫는다` 실패.
- `AppSnackBar.show`의 `backgroundColor: AppColors.ink`를 뺀다 → `앱 톤(잉크 바탕·흰 글자)의 스낵바를 띄우고, 화면이 닫힌 뒤에도 남는다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "feat(design): 스낵바 관례(AppSnackBar)와 VISIT_DUPLICATE 안내 — 이미 잡힌 예약을 알리고 그날로 닫는다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: 앱 — ③-A2 잔여 UI 5건(섞인 상태 가족 카드, 미리보기 "외 N건", 노쇼 횟수 카드, 시간 칸 색 구분, 30분 블록 메뉴)

**Files:**
- Modify: `app/lib/features/visit/state/day_layout.dart`
- Modify: `app/lib/features/visit/screens/visit_labels.dart`
- Modify: `app/lib/features/visit/screens/day_screen.dart`
- Modify: `app/lib/features/visit/screens/calendar_tab.dart`
- Modify: `app/lib/features/visit/screens/visit_form.dart`
- Modify: `app/lib/features/customer/screens/pet_detail_screen.dart`
- Modify: `app/lib/l10n/app_strings.dart`
- Modify: `app/test/features/customer/screens/pet_detail_screen_test.dart`
- Modify: `app/test/features/visit/screens/calendar_tab_test.dart`
- Modify: `app/test/features/visit/screens/day_screen_test.dart`
- Modify: `app/test/features/visit/screens/goldens/register_visit_form.png`
- Modify: `app/test/features/visit/screens/register_visit_screen_test.dart`

**Interfaces:**
- Consumes: `DayGroup`(`day_layout.dart`), `_GroupCard`·`_Block`(`day_screen.dart`), `_DayPreview`(`calendar_tab.dart`), `_SlotTile`(`visit_form.dart`), `_InfoCard`(`pet_detail_screen.dart`), `statusLabel`(`visit_labels.dart`), `askVisitAction`/`sendVisitAction`.
- Produces: `DayGroup.actionable`·`actionableStatus`·`actionableIds`; `statusSummary(List<Visit>)`(`visit_labels.dart` — "콩이 완료 · 두부 미용 중"); `AppStrings.moreGroups(int)`("외 N건")·`noShowCountLabel`("노쇼 횟수")·`timesCount(int)`("N회"). 골든 `register_visit_form.png`가 바뀐다(시간 칸 색 — 의도한 변경).

"이 계획에서 새로 정한 것" 1·12. 섞인 카드의 버튼은 진행 가능한 구성원 집합(예약됨끼리 [시작], 미용 중끼리 [완료하기])이고 보내는 `ids`도 그 집합뿐이다(V14). `_act`의 다음 예약 초안 앵커도 그 첫 아이다. 30분 블록은 `Text.rich`라 테스트는 `find.text(..., findRichText: true)`로 찾는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/customer/screens/pet_detail_screen_test.dart`:

```diff
@@ -113,7 +113,9 @@ void main() {
 
     await tester.tap(find.text(AppStrings.petTabOwner));
     await tester.pumpAndSettle();
-    expect(find.text(AppStrings.noShowCount(2)), findsOneWidget);
+    expect(find.text(AppStrings.noShowCountLabel), findsOneWidget);
+    expect(find.text(AppStrings.timesCount(2)), findsOneWidget);
+    expect(find.text('노쇼 2회'), findsNothing);
     expect(find.text('10월 2일 금 14:00'), findsOneWidget);
     expect(find.text('10월 5일 월 11:00'), findsOneWidget);
     expect(find.text(AppStrings.ownerOnly), findsOneWidget);
@@ -141,7 +143,7 @@ void main() {
     await tester.tap(find.text(AppStrings.petTabOwner));
     await tester.pumpAndSettle();
 
-    expect(find.text(AppStrings.noShowCount(0)), findsOneWidget);
+    expect(find.text(AppStrings.timesCount(0)), findsOneWidget);
     expect(find.text(AppStrings.noUpcomingVisits), findsOneWidget);
   });
```

`app/test/features/visit/screens/calendar_tab_test.dart`:

```diff
@@ -141,6 +141,35 @@ void main() {
     expect(dayQueries, ['2026-09-22', '2026-09-25']);
   });
 
+  testWidgets('미리보기가 4줄을 넘으면 "외 N건"을 적는다', (tester) async {
+    final backend = _backend();
+    backend.routes['GET /v1/shops/3/visits'] = (o, b) => FakeResponse(
+      statusCode: 200,
+      data: dayJson(
+        date: '2026-09-22',
+        items: [
+          for (var i = 0; i < 6; i++)
+            dayItemJson(
+              visitJson(
+                visitId: 100 + i,
+                date: '2026-09-22',
+                start: '1$i:00',
+                pet: visitPetJson(petId: 20 + i, name: '아이$i'),
+              ),
+              groupKey: 'g$i',
+            ),
+        ],
+      ),
+    );
+    final setup = CustomerTestSetup(backend.call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _pumpHome(tester, setup);
+
+    expect(find.text('아이3'), findsOneWidget);
+    expect(find.text('아이4'), findsNothing);
+    expect(find.text(AppStrings.moreGroups(2)), findsOneWidget);
+  });
+
   testWidgets('예약이 없는 날과 휴무일은 미리보기에 그렇게 적는다', (tester) async {
     final setup = CustomerTestSetup(_backend().call, overrides: _today);
     addTearDown(setup.container.dispose);
```

`app/test/features/visit/screens/day_screen_test.dart`:

```diff
@@ -157,6 +157,90 @@ void main() {
     expect(find.text(AppStrings.statusCompleted), findsOneWidget);
   });
 
+  testWidgets('상태가 섞인 가족 카드는 아이별 상태를 적고, 아직 진행 가능한 아이만 버튼으로 보낸다', (
+    tester,
+  ) async {
+    final backend = _backend([
+      dayItemJson(
+        _v(
+          2,
+          '13:00',
+          status: 'completed',
+          pet: '두부',
+          owner: '이수진',
+          customerId: 8,
+        ),
+        groupKey: 'duo',
+      ),
+      dayItemJson(
+        _v(
+          3,
+          '13:00',
+          status: 'in_progress',
+          pet: '보리',
+          petId: 12,
+          owner: '이수진',
+          customerId: 8,
+        ),
+        groupKey: 'duo',
+      ),
+      dayItemJson(
+        _v(
+          4,
+          '15:00',
+          status: 'canceled',
+          pet: '몽이',
+          owner: '박하늘',
+          customerId: 9,
+        ),
+        groupKey: 'trio',
+      ),
+      dayItemJson(
+        _v(
+          5,
+          '15:00',
+          status: 'completed',
+          pet: '코코',
+          petId: 13,
+          owner: '박하늘',
+          customerId: 9,
+        ),
+        groupKey: 'trio',
+      ),
+    ]);
+    Map<String, dynamic>? sent;
+    backend.routes['POST /v1/shops/3/visits/transitions'] = (o, body) {
+      sent = bodyOf(body);
+      return FakeResponse(
+        statusCode: 200,
+        data: {
+          'visits': [_v(3, '13:00', status: 'completed', pet: '보리', petId: 12)],
+        },
+      );
+    };
+    backend.routes['GET /v1/shops/3/visits/3/next-draft'] = (o, b) =>
+        FakeResponse(statusCode: 200, data: nextDraftJson(petIds: [12]));
+    final setup = CustomerTestSetup(backend.call, overrides: _today);
+    addTearDown(setup.container.dispose);
+    await _open(tester, setup);
+
+    expect(find.text('두부 완료 · 보리 미용 중'), findsOneWidget);
+    // 진행 가능한 아이가 없는 묶음(취소·완료)은 칩만.
+    expect(find.text('몽이 취소 · 코코 완료'), findsOneWidget);
+    expect(_button(AppStrings.actionCompleteShort), findsOneWidget);
+    expect(_button(AppStrings.actionStart), findsNothing);
+
+    await tester.tap(_button(AppStrings.actionCompleteShort));
+    await settle(tester);
+    await tester.tap(find.text(AppStrings.actionComplete));
+    await settle(tester);
+    expect(sent, {
+      'visit_ids': [3],
+      'action': 'complete',
+    });
+    expect(setup.calls, contains('GET /v1/shops/3/visits/3/next-draft'));
+  });
+
   testWidgets('카드의 [시작]은 묶음 전체를 한 번에 보내고 그날 목록을 다시 불러온다', (tester) async {
     final backend = _backend(_mockupItems(duoStatus: 'reserved'));
     Map<String, dynamic>? sent;
@@ -383,6 +467,9 @@ void main() {
     await _open(tester, setup);
 
     expect(tester.takeException(), isNull);
+    // 이름만으로는 아쉽다 — 메뉴를 같은 줄에 잇는다(A2 잔여).
+    expect(find.text('콩이 · 목욕', findRichText: true), findsOneWidget);
+    expect(find.text('콩이'), findsNothing);
   });
 
   testWidgets('마감이 19:30 이면 시간표가 20:00 까지 그린다', (tester) async {
```

`app/test/features/visit/screens/goldens/register_visit_form.png`: 골든 이미지 — 이 문서에 넣지 않는다. 이 작업의 골든 테스트를 `--update-goldens`로 돌려 다시 만들고 눈으로 본다(의도한 변경).

`app/test/features/visit/screens/register_visit_screen_test.dart`:

```diff
@@ -2,6 +2,7 @@ import 'dart:async';
 
 import 'package:chagocnote/core/router/app_router.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
+import 'package:chagocnote/design/tokens/app_colors.dart';
 import 'package:chagocnote/design/widgets/app_button.dart';
 import 'package:chagocnote/features/home/state/today_provider.dart';
 import 'package:chagocnote/features/visit/api/visit_models.dart';
@@ -116,6 +117,8 @@ void main() {
             ? slotsJson(
                 warnings: {
                   15: ['overlap'],
+                  16: ['closed_day'],
+                  17: ['overlap', 'outside_hours'],
                 },
               )
             : slotAtJson(at: at, warnings: ['overlap']),
@@ -126,10 +129,33 @@ void main() {
     await _open(tester, setup);
     await _pickCustomer(tester);
 
+    // 겹침은 흰 바탕에 잉크색 줄긋기, 휴무·영업 밖은 옅은 바탕에 옅은 글자 —
+    // 둘이 구분된다(A2 잔여). 둘 다면 옅은 바탕에 줄긋기.
+    Color tileColor(String at) =>
+        (tester
+                    .widget<Container>(
+                      find.ancestor(
+                        of: find.text(at),
+                        matching: find.byType(Container),
+                      ).first,
+                    )
+                    .decoration
+                as BoxDecoration)
+            .color!;
     final struck = tester.widget<Text>(find.text('15:00'));
     expect(struck.style!.decoration, TextDecoration.lineThrough);
+    expect(struck.style!.color, AppColors.ink);
+    expect(tileColor('15:00'), AppColors.white);
+    final faint = tester.widget<Text>(find.text('16:00'));
+    expect(faint.style!.decoration, isNot(TextDecoration.lineThrough));
+    expect(faint.style!.color, AppColors.secondary);
+    expect(tileColor('16:00'), AppColors.backgroundTop);
+    final both = tester.widget<Text>(find.text('17:00'));
+    expect(both.style!.decoration, TextDecoration.lineThrough);
+    expect(tileColor('17:00'), AppColors.backgroundTop);
     final plain = tester.widget<Text>(find.text('14:00'));
     expect(plain.style!.decoration, isNot(TextDecoration.lineThrough));
+    expect(tileColor('14:00'), AppColors.white);
 
     await _tapLabel(tester, '15:00');
     expect(find.text('· ${AppStrings.warningOverlap}'), findsOneWidget);
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`app/`): `flutter test test/features/visit/screens/day_screen_test.dart test/features/visit/screens/calendar_tab_test.dart test/features/customer/screens/pet_detail_screen_test.dart test/features/visit/screens/register_visit_screen_test.dart --timeout 20s`
Expected: 컴파일 오류(`actionableIds`·`moreGroups`·`timesCount` 없음)로 실패.

- [ ] **Step 3: 구현한다**

`app/lib/features/visit/state/day_layout.dart`:

```diff
@@ -33,6 +33,23 @@ class DayGroup {
     final statuses = {for (final i in items) i.visit.status};
     return statuses.length == 1 ? statuses.single : null;
   }
+
+  /// 아직 진행할 수 있는 구성원(예약됨·미용 중). 상태가 섞인 묶음에서 카드
+  /// 버튼은 이 아이들만 다룬다 — 완료·취소한 아이를 함께 보내 409 가 나지 않게.
+  List<Visit> get actionable => [
+    for (final i in items)
+      if (i.visit.status == VisitStatus.reserved ||
+          i.visit.status == VisitStatus.inProgress)
+        i.visit,
+  ];
+
+  /// 진행 가능한 구성원의 상태가 하나면 그 상태(버튼을 낼 수 있다), 아니면 null.
+  String? get actionableStatus {
+    final statuses = {for (final v in actionable) v.status};
+    return statuses.length == 1 ? statuses.single : null;
+  }
+
+  List<int> get actionableIds => [for (final v in actionable) v.visitId];
 }
 
 /// 같은 `group_key`끼리 묶는다. 처음 나온 순서(=서버의 시작 순)를 지킨다 —
```

`app/lib/features/visit/screens/visit_labels.dart`:

```diff
@@ -45,3 +45,10 @@ String visitsTitle(List<Visit> visits) {
 
 String menusLabel(List<MenuBrief> menus) =>
     menus.isEmpty ? AppStrings.noMenu : menus.map((m) => m.name).join(', ');
+
+/// 상태가 섞인 묶음의 아이별 상태 — "두부 완료 · 보리 미용 중".
+String statusSummary(List<Visit> visits) => [
+  for (final v in visits)
+    '${v.pet == null ? AppStrings.ownerOnly : (v.pet!.name ?? AppStrings.deletedCustomer)} '
+        '${statusLabel(v.status)}',
+].join(' · ');
```

`app/lib/features/visit/screens/day_screen.dart`:

```diff
@@ -60,6 +60,9 @@ class _DayScreenState extends ConsumerState<DayScreen> {
   Future<void> _act(DayGroup group, String action) async {
     final shopId = _shopId;
     if (shopId == null || _busyVisitId != null || _asking) return;
+    // 상태가 섞인 묶음이면 아직 진행 가능한 아이들만(다음 예약 초안도 그 아이 기준).
+    final ids = group.actionableIds;
+    final anchorVisitId = ids.isEmpty ? group.first.visitId : ids.first;
     setState(() => _asking = true);
     VisitChoice? choice;
     try {
@@ -68,7 +71,7 @@ class _DayScreenState extends ConsumerState<DayScreen> {
         ref,
         shopId: shopId,
         action: action,
-        anchorVisitId: group.first.visitId,
+        anchorVisitId: anchorVisitId,
       );
     } finally {
       if (mounted) setState(() => _asking = false);
@@ -84,8 +87,8 @@ class _DayScreenState extends ConsumerState<DayScreen> {
         ref,
         shopId: shopId,
         choice: choice,
-        ids: group.ids,
-        anchorVisitId: group.first.visitId,
+        ids: ids,
+        anchorVisitId: anchorVisitId,
       );
     } catch (e) {
       if (mounted) setState(() => _errorText = messageFor(e));
@@ -395,9 +398,12 @@ class _GroupCard extends StatelessWidget {
       if (group.unresolved) AppStrings.markUnresolved,
     ];
     final status = group.uniformStatus;
+    // 상태가 섞였으면 아직 진행 가능한 아이들의 상태로 버튼을 정한다(A2 잔여).
+    final mixed = status == null;
+    final buttonStatus = mixed ? group.actionableStatus : status;
     VoidCallback? on(String action) =>
         busy || otherBusy ? null : () => onAction(action);
-    final Widget trailing = switch (status) {
+    final Widget trailing = switch (buttonStatus) {
       VisitStatus.reserved => AppButton(
         label: AppStrings.actionStart,
         filled: true,
@@ -412,6 +418,11 @@ class _GroupCard extends StatelessWidget {
       ),
       _ => AppChip(label: statusLabel(status ?? first.status)),
     };
+    final caption = [
+      menusLabel(first.menus),
+      ownerLabel(first.customer),
+      ...marks,
+    ].join(' · ');
     return Opacity(
       opacity: group.occupiesTime ? 1 : 0.5,
       child: Pressable(
@@ -444,14 +455,12 @@ class _GroupCard extends StatelessWidget {
                       visitsTitle(group.visits),
                       style: AppTypography.bodyStrong,
                     ),
-                    Text(
-                      [
-                        menusLabel(first.menus),
-                        ownerLabel(first.customer),
-                        ...marks,
-                      ].join(' · '),
-                      style: AppTypography.caption,
-                    ),
+                    Text(caption, style: AppTypography.caption),
+                    if (mixed)
+                      Text(
+                        statusSummary(group.visits),
+                        style: AppTypography.caption,
+                      ),
                   ],
                 ),
               ),
@@ -620,11 +629,30 @@ class _Block extends StatelessWidget {
               crossAxisAlignment: CrossAxisAlignment.start,
               mainAxisSize: MainAxisSize.min,
               children: [
-                Text(
-                  visitsTitle(group.visits),
-                  style: AppTypography.bodyStrong,
-                  overflow: TextOverflow.ellipsis,
-                ),
+                // 둘째 줄이 없으면 메뉴를 이름 뒤에 같은 줄로 잇는다(A2 잔여).
+                if (showCaption)
+                  Text(
+                    visitsTitle(group.visits),
+                    style: AppTypography.bodyStrong,
+                    overflow: TextOverflow.ellipsis,
+                  )
+                else
+                  Text.rich(
+                    TextSpan(
+                      children: [
+                        TextSpan(
+                          text: visitsTitle(group.visits),
+                          style: AppTypography.bodyStrong,
+                        ),
+                        TextSpan(
+                          text: ' · ${menusLabel(group.first.menus)}',
+                          style: AppTypography.caption,
+                        ),
+                      ],
+                    ),
+                    maxLines: 1,
+                    overflow: TextOverflow.ellipsis,
+                  ),
                 if (showCaption)
                   Text(
                     [
```

`app/lib/features/visit/screens/calendar_tab.dart`:

```diff
@@ -508,6 +508,14 @@ class _DayPreview extends ConsumerWidget {
                       ],
                     ),
                   ),
+              if (groups.length > _maxRows)
+                Padding(
+                  padding: const EdgeInsets.only(top: 2),
+                  child: Text(
+                    AppStrings.moreGroups(groups.length - _maxRows),
+                    style: AppTypography.caption,
+                  ),
+                ),
             ],
           ),
         ),
```

`app/lib/features/visit/screens/visit_form.dart`:

```diff
@@ -753,8 +753,14 @@ class _SlotChip extends StatelessWidget {
       child: Container(
         width: 64,
         padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
+        // 휴무·영업 밖은 옅은 바탕에 옅은 글자, 겹침은 흰 바탕에 줄긋기 —
+        // 둘이 한눈에 구분된다(A2 잔여).
         decoration: BoxDecoration(
-          color: selectedHere ? AppColors.ink : AppColors.white,
+          color: selectedHere
+              ? AppColors.ink
+              : faint
+              ? AppColors.backgroundTop
+              : AppColors.white,
           borderRadius: BorderRadius.circular(AppRadius.pill),
           border: Border.all(
             color: selectedHere ? AppColors.ink : AppColors.line,
@@ -767,7 +773,7 @@ class _SlotChip extends StatelessWidget {
             style: AppTypography.body.copyWith(
               color: selectedHere
                   ? AppColors.white
-                  : faint || overlap
+                  : faint
                   ? AppColors.secondary
                   : AppColors.ink,
               decoration: overlap ? TextDecoration.lineThrough : null,
```

`app/lib/features/customer/screens/pet_detail_screen.dart`:

```diff
@@ -429,8 +429,8 @@ class _OwnerTab extends ConsumerWidget {
                   value: c.memo ?? AppStrings.none,
                 ),
                 _InfoCard(
-                  label: AppStrings.actionNoShow,
-                  value: AppStrings.noShowCount(detail.noShowCount),
+                  label: AppStrings.noShowCountLabel,
+                  value: AppStrings.timesCount(detail.noShowCount),
                 ),
                 _UpcomingVisits(visits: detail.upcomingVisits),
                 const SizedBox(height: AppSpacing.sm),
```

`app/lib/l10n/app_strings.dart`:

```diff
@@ -293,6 +293,8 @@ class AppStrings {
   static const noShowConfirm = '노쇼로 기록할까요? 보호자의 노쇼 횟수에 더해집니다.';
 
   static String noShowCount(int count) => '노쇼 $count회';
+  static const noShowCountLabel = '노쇼 횟수';
+  static String timesCount(int count) => '$count회';
   static const dayTitleEn = 'Schedule';
   static const viewAsTimeline = '시간표로 보기';
   static const actionCompleteShort = '완료하기';
@@ -325,6 +327,7 @@ class AppStrings {
   static const prevMonth = '이전 달';
   static const nextMonth = '다음 달';
   static const closedShort = '휴무';
+  static String moreGroups(int count) => '외 $count건';
 
   static String unresolvedBanner(int count) => '정리 안 된 예약 $count건';
   static String dayHeading(int day, int weekday) => '$day일 ${weekdaysLong[weekday - 1]}';
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`app/`): `flutter test test/features/visit/screens/register_visit_screen_test.dart --update-goldens --timeout 20s` → `register_visit_form.png`가 새로 만들어진다(휴무·영업 밖 칸이 옅은 바탕). 눈으로 열어 본다. **다른 골든은 바뀌지 않아야 한다.**

Run (`app/`): `flutter test test/features/visit/screens/day_screen_test.dart test/features/visit/screens/calendar_tab_test.dart test/features/customer/screens/pet_detail_screen_test.dart test/features/visit/screens/register_visit_screen_test.dart --timeout 20s` → 통과(이 작업 새 테스트 2 + 확장 3)

Run (`app/`): `flutter test --timeout 30s` → 전부 통과(500개)

Run (`app/`): `flutter analyze` → `No issues found!`

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `_act`의 `ids = group.actionableIds`를 `group.ids`로 → `상태가 섞인 가족 카드는 아이별 상태를 적고, 아직 진행 가능한 아이만 버튼으로 보낸다` 실패.
- `buttonStatus = mixed ? group.actionableStatus : status`를 `status`로 → 같은 테스트 실패(버튼이 없다).
- `if (mixed) Text(statusSummary(...))`를 뺀다 → 같은 테스트 실패.
- `_DayPreview`의 "외 N건" 줄을 뺀다 → `미리보기가 4줄을 넘으면 "외 N건"을 적는다` 실패.
- `_SlotTile`의 `faint ? AppColors.backgroundTop : AppColors.white`를 `AppColors.white`로 → `겹치는 칸은 줄을 긋고, 눌러도 막지 않고 경고만 보인다`(`tileColor`) 실패.
- `_Block`의 `Text.rich`(메뉴 잇기)를 이름만으로 → `30분 방문도 시간표에서 넘치지 않는다` 실패.
- 노쇼 카드 값을 `noShowCount`로 되돌린다 → `보호자 탭은 노쇼 횟수와 다가오는 예약을 보이고…` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "fix(visit): A2 잔여 UI 5건 — 섞인 상태 가족 카드, 미리보기 초과 표시, 노쇼 횟수 카드, 시간 칸 색 구분, 30분 블록 메뉴

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: 시뮬레이터·실기기 흐름 확인과 결정 기록

**Files:**
- Modify: `_docs/decisions/006-visit-reservation.md` (③-A3 절을 더한다)
- Modify: `_docs/harness.md` (라우트 표 행에 visit 21개, 앱 표에 공유 받기 실기기 확인 한 줄)

**Interfaces:**
- Consumes: Task 1~8 전부, `infra/`의 개발 환경, `backend/scripts/check_visit_flow.sh`(초안 판정 4개 포함 — Task 3 이 돌렸다), iOS 실기기(개발 팀 서명이 되는 기기)와 카카오톡.
- Produces: 결정 기록 006 의 ③-A3 절, 사용자의 완료 판정.

- [ ] **Step 1: 개발 환경을 최신 코드로 띄운다**

`infra/`에서:

```bash
docker compose up -d
docker compose restart backend      # --reload 가 변경을 놓칠 수 있다(③-A2 교훈)
bash ../backend/scripts/check_visit_flow.sh
```

Expected: '통과' 줄 31개(초안 판정 "카톡 초안의 보호자 후보 / 콩이를 고른다 / 메뉴·날짜·시각 / 저장하지 않는다" 포함). 스크립트가 만든 매장의 사장 계정(`vflow-owner-<stamp>`, 개발용 로그인)으로 앱에서 로그인할 수 있다.

- [ ] **Step 2: 앱을 시뮬레이터로 띄운다**

`app/`에서 `tool/run_dev.sh`. Xcode 27 의 시뮬레이터는 Device Hub 에서 연다. **사용자가 화면을 보는 자리에서 진행한다.** 사용자가 자리에 없으면 ③-A2 Task 12 처럼 `integration_test`로 실서버에 붙여 확인하고 스크린샷을 남긴다(`.superpowers/ref/visit-3a3-check/`, git 무시).

- [ ] **Step 3: 붙여넣기 초안 흐름을 확인한다(설계 11절 완료 기준의 "카톡 붙여넣기 초안")**

사용자와 함께, 하나씩 결과를 적는다. 매장에는 고객 "김민지"(콩이·두부)와 "박서준"(보리)이 있고 메뉴표에 "목욕"·"부분 미용"이 있다.

1. 메모 앱에 `안녕하세요 내일 오후 2시에 콩이 목욕 부탁드려요`를 적어 복사 → 캘린더 + → ① 위 [카톡 붙여넣기] → (iOS 가 붙여넣기 허용을 물으면 허용) → 초안 화면: 받은 글, 보호자 "김민지 · ··5678"(콩이 · 두부)가 고른 상태, 날짜 내일, 시작 14:00(짐작 칩 없음), 메뉴 "목욕" → [예약 이어서] → ②에 콩이 칩·내일·14:00·목욕(60분) → 저장 → 초안·① 닫히고 달력이 내일을 고른다.
2. `내일 2시 콩이` → 초안의 시작 14:00 에 "짐작" 칩 → ②에서 시각을 바꿀 수 있다.
3. `[김민지] [오후 2:31] 콩이 다음 주 월요일 3시 될까요` → 날짜 다음 주 월요일(짐작), 시작 15:00(짐작), 후보 김민지.
4. `보리 모레 부분미용` → 후보 박서준(보리), 메뉴 "부분 미용"(짐작 칩 — 공백 없이 맞았다).
5. `콩` → 후보 없음("찾은 보호자가 없어요") → [고객 찾기] → ①에서 김민지를 고르면 ②가 (날짜 오늘) 빈 시각으로 열린다.
6. 클립보드가 비었을 때 [카톡 붙여넣기] → "복사한 글이 없어요".
7. 다음 예약 ②에서 한 아이의 시각이 이미 예약된 경우를 만든다(같은 아이·같은 시각을 먼저 예약) → 저장 → 스낵바 "이미 같은 시각에 잡힌 예약이 있어요…" 뒤 그날로 닫힌다.
8. 하루 목록: 두 마리 묶음에서 한 아이만 상세에서 완료 → 카드에 "콩이 완료 · 두부 미용 중"과 [완료하기](두부만) → 누르면 두부만 완료. 캘린더 미리보기: 묶음 5개 이상인 날에 "외 N건". 예약 ②: 휴무일 칸은 옅은 바탕, 이미 예약된 칸은 줄긋기. 시간표: 30분 방문 블록에 "이름 · 메뉴". 보호자 탭: "노쇼 횟수 / N회".

Expected: 8개 모두 설계·이 계획대로. **하나라도 어긋나면 멈추고 사용자에게 묻는다** — 설계를 바꾸는 일인지, 이 계획의 결함인지. 계획의 결함이면 그 작업의 테스트를 먼저 더해 재현한 뒤 고치고, 새 커밋(`fix(visit): …`)으로 남긴다.

- [ ] **Step 4: 공유 받기를 실기기에서 확인한다**

iOS 실기기(개발 팀 서명, `flutter run -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://<맥 IP>:8080` — 게이트웨이가 127.0.0.1 에만 열려 있으면 `infra/docker-compose.yml`의 게이트웨이 포트를 잠시 `0.0.0.0`으로 여는 대신, 기기와 맥을 같은 네트워크에 두고 `ssh` 포트 포워딩이나 Caddy 바인딩 변경 중 사용자가 고른 방법으로 연다). 카카오톡에서 손님 메시지를 길게 눌러 [공유] → 목록에 "차곡노트" → 고르면 차곡노트가 열리고 초안 화면이 그 글로 뜬다.

확인할 것:
1. 앱이 꺼진 상태에서 공유(콜드 스타트) → 로그인 상태면 바로 초안 화면, 로그아웃 상태면 로그인 뒤 초안 화면.
2. 앱이 떠 있는 상태에서 공유 → 초안 화면이 위에 뜬다.
3. 카톡이 넘기는 글의 형태를 적는다 — 글만인지, 보낸 사람·시각이 붙는지(붙으면 머리말 제거 규칙이 맞는지 본다).
4. Xcode 의 Signing & Capabilities 에서 Runner 와 ShareExtension 둘 다 App Groups `group.com.chagocnote.app`가 켜져 있고, 기기 빌드가 entitlement 오류 없이 된다.

안드로이드 실기기 또는 에뮬레이터(카톡이 없으면 다른 앱의 텍스트 공유): 공유 대상에 "차곡노트" → 초안 화면. 앱이 떠 있을 때(`onNewIntent`)와 꺼져 있을 때 둘 다.

Expected: 되면 결과와 카톡 글 형태를 적는다. **안 되면(공유 목록에 없음, 본체가 안 열림, entitlement 오류) 멈추고 원인을 적어 사용자에게 보고한다** — 응답자 체인 우회가 막힌 것인지, 서명·App Group 문제인지. 실기기가 없으면 이 단계는 "미확인"으로 결정 기록에 남기고 다음 세션 몫으로 둔다.

- [ ] **Step 5: 결정 기록 006 에 ③-A3 절을 더한다**

`_docs/decisions/006-visit-reservation.md` 맨 뒤에 "## ③-A3(카톡 예약 초안)에서 정한 것" 절을 더한다. 머리의 `- 대상 브랜치:`에 `feat/visit-3a3-kakao-draft`(③-A3 카톡 초안)를 더한다. 절의 내용:

1. **무엇을 만들었나** — `POST /visit-drafts`(visit 경로 21개째), 허브 포트 `find_draft_candidates`(customer 구현, `CustomerSearchPort.match_any`), 도메인 해석기 `draft_parser`, 포트 `VisitDraftParserPort`(규칙 어댑터, ⑨ 뒤 LLM 자리), 앱의 초안 화면·`VisitPrefill`·[카톡 붙여넣기]·공유 받기(직접 쓴 iOS Share Extension·안드로이드 `ACTION_SEND`), `AppSnackBar`, A2 잔여 6건.
2. **사용자와 정한 것(2026-09-24)** — A2 잔여 6건 포함, 공유 받기 직접 구현(패키지 기각 이유), 초안 화면 A안.
3. **이 계획에서 새로 정한 것** 1~19 를 옮긴다(이 문서의 절 그대로).
4. **위협 점검표** V1·V9·V12·A1~A12 와 확인 테스트.
5. **검증** — 단위 627 → 719, 통합 254 → 261, 계약 6, 앱 476 → 500, 흐름 스크립트 '통과' 31, 라우트 21. 작업별 검토·최종 검토에서 고친 것(실행 중 생긴 것을 적는다).
6. **이 계획으로도 남는 것** — 위 "남는 것" 목록 그대로 + Step 3·4 에서 사용자와 확인한 결과(어긋난 것과 고친 것, 카톡 글 형태, 공유 받기 확인 여부).

`_docs/harness.md`: 라우트 표 행 설명에 "visit 21개"가 있으면 갱신하고, 앱 표에 `공유 받기 확인 | 실기기에서 카톡 [공유] → 차곡노트 (시뮬레이터엔 카톡이 없고 App Group 은 서명이 있어야 붙는다)` 한 줄을 더한다.

- [ ] **Step 6: 최종 검증과 커밋**

`infra/`에서:

```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"   # 719 passed (Step 3·4 에서 고친 게 있으면 그만큼 더)
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration                          # 261 passed
docker compose run --rm --no-deps backend lint-imports --config .importlinter                                     # 6 kept
```

`app/`에서:

```bash
flutter analyze              # No issues found!
flutter test --timeout 30s   # 500 tests passed (고친 게 있으면 그만큼 더)
```

```bash
git add _docs/decisions/006-visit-reservation.md _docs/harness.md
git commit -m "docs(visit): 결정 기록 006 에 ③-A3 카톡 초안 몫을 더한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

푸시·머지는 하지 않는다. 사용자에게 `feat/visit-3a3-kakao-draft` 브랜치의 커밋 목록과 Step 3·4 의 결과를 보고한다.

---

## 자체 검토

- **설계 대조:** 7절 `POST /visit-drafts {text}` → 응답 모양 → Task 3(스키마 그대로, `time`만 `HH:MM`으로 좁힘); 1,000자 제한·글을 남기지 않음 → Task 3(pydantic + V9 테스트); 해석 규칙(날짜·시간·누구·메뉴, 짐작함) → Task 2 + "새로 정한 것" 6~8·13·14; `find_draft_candidates`(② 검색 재사용, 최대 5 가족) → Task 1(`match_any`가 같은 검색 줄을 쓴다); "못 찾은 칸은 비운다 / 사람이 확인한 뒤 등록 API 로 저장" → Task 5(초안 화면)·Task 4(②로 이어짐); 앱 입구 둘(예약 ① 위 [카톡 붙여넣기], 공유 받기 — 확장은 글만 넘기고 앱을 연다, 토큰 접근 없음, 서버 호출은 본체) → Task 5·Task 6; "카톡이 넘기는 형태는 실기기에서" → Task 9 Step 4. 4절 `VisitDraftParserPort`(⑨ 뒤 LLM 어댑터) → Task 3. 8절 표 `POST /visit-drafts reservation:write` → Task 3. 10절 V9·V12 → 위협 점검표. 11절 "초안 해석기(표 기반)" → Task 2, "초안이 로그에 남지 않음(V9)" → Task 3 통합, 완료 기준 "카톡 붙여넣기 초안" → Task 9 Step 3, "공유 확장은 실기기에서" → Task 9 Step 4. 12절 ③-A3 의 순서(해석기 → 초안 API → 앱 붙여넣기 → 공유 확장·인텐트 → 결정 기록 006) → Task 2 → 3 → 5 → 6 → 9 (Task 1 은 해석기보다 앞에 두었다 — 허브 포트가 먼저 있어야 Task 3 의 스텁이 선다). ③-A2 가 남긴 사용자 판단 6건 → Task 7·8.
- **자리표시자 없음:** 모든 단계에 실제 코드·diff·명령·기대값이 있다. 골든 png 만 "갱신해 만든다"로 적었다(문서에 넣을 수 없다).
- **형 일관성:** `DraftCandidate.exact`(Task 1) ↔ `only.exact`(Task 3); `DraftParse.words`(Task 2) ↔ `parsed.words`(Task 3); 응답 `time: "HH:MM"`(Task 3) ↔ `VisitDraft.time: String?` → `VisitPrefill.at`(Task 4) → `VisitFormInitial.at`(기존); `matched_pet_ids` ↔ `DraftCandidate.matchedPetIds` → `VisitPrefill.petIds`; `ScreenKeys.visitDraft`(Task 5) ↔ Task 6 관문 테스트; `pendingSharedTextProvider`(Task 6) ↔ `sharedTextToOpenProvider`; `DayGroup.actionableIds`(Task 8) ↔ `_act`. 뒤 작업이 앞 작업의 이름 그대로 쓴다(참조 브랜치가 컴파일되고 전부 통과한다).
- **Review Focus:** 다섯 줄 모두 그 작업의 테스트가 누른다(1·2·3 은 참조 구현을 검토하며 더했고, 그때 판별력도 변이로 확인했다).
