# 007 — 미용 기록·미디어(④)에서 내린 결정

설계: `docs/superpowers/specs/2026-09-24-record-media-design.md`. 이 기록은 계획마다 절을 더한다.

## ④-0 SOLID 정리(백엔드)에서 정한 것

2026-09-24 감사(설계 4.1절 B1~B10)를 기능 코드 없이 먼저 적용했다. 검증 기준은 "기존 단위·통합·구조 계약이 전후로 통과하고 라우트 표가 같다"였고, 그대로 지켰다(단위 727 → 766, 통합 262 → 260 — 재인증 테스트 8개가 auth 로 옮겨 6개가 되고 도메인 단위 4개가 생겼다, 계약 6종, 라우트 표 동일).

### 설계와 다르게 간 것

- **찾기·잠금 포트 이름과 범위.** 설계 B1 은 `get_many`·`lock` 둘만 가진 `VisitLockRepository`를 말했다. 실제로는 `get`도 같은 축(ID 로 찾기)이고 상세·초안 조회가 `get`만 쓰므로, 셋을 가진 `VisitLookupRepository`로 두고 `VisitWriteRepository`가 이를 상속한다. 조회 유스케이스가 쓰기 포트를 받지 않게 하는 것이 목적이었고 그 목적은 지켰다(`apps/visit/tests/app/test_visit_port_segregation.py`가 쓰기 포트를 받는 유스케이스를 넷으로 고정한다).
- **허브 오류는 포트 셋.** 설계 B2 는 `CustomerDirectoryPort`와 "기존 포트 둘"을 말했지만, 감사에서 같은 누수가 `ShopAccessPort`(tenancy 오류가 core 로)와 `MembershipLifecyclePort`(tenancy 오류가 auth 로)에도 있었다. 셋 다 허브 오류로 바꿨다. 탈퇴 오류 둘(`OWNERSHIP_TRANSFER_REQUIRED`·`SHOP_CLOSE_CONFIRM_REQUIRED`)은 tenancy 도메인에서 지우고 허브로 옮겼다(그 유스케이스만 던졌다). 매장 접근 거절 셋은 tenancy 가 자기 라우터에서도 쓰므로 tenancy 오류는 남기고, 포트 구현만 허브 오류를 던진다.
- **허브 오류의 HTTP 상태는 `core/hub_errors.py` 한 곳.** 설계는 소비 스포크의 `error_map.py`에 매핑하라고 했다. core 자신이 `ShopAccessPort`를 소비하고, 같은 오류가 두 프로세스에서 같은 상태로 나가야 하므로 맵을 core 에 두고 `install_error_handlers`가 자동으로 등록한다. `tests/test_hub_errors.py`가 HubPortError 의 모든 하위 클래스가 맵에 있고 두 진입점에 핸들러가 있는지 확인한다.
- **재인증 가드의 위치(설계 B8 의 두 갈래).** 연결·해제·탈퇴 라우터는 모두 인증 프로세스에 있었다. 그래서 자리 없이 `auth/dependencies/recent_login_guard.py`로 옮기고, 창(300초)·시계 차 허용폭은 `auth/domain/services/recent_login.py`가 정한다. core 는 `get_access_claims`(토큰 검증 + 계정 상태)만 남았고 `get_current_user_id`의 서명은 그대로다.
- **스텁 ABC 상속은 공용 스텁만.** 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 상속하지 않는다(하네스 문서에 적었다).

### 계획서 코드와 실행이 다르지 않았던 것

작업 8개 모두 참조 작업 트리에서 먼저 돌려 검증한 코드다. 실행 중 작업 5 의 검토가 하나를 더했다 — `apps/visit/tests/app/test_day_counts_view.py`(하루 집계 칸 집합이 상태 표와 같은지; 상태를 더하고 칸을 잊으면 걸린다). 참조 브랜치 `ref/record-4-0-be`와 다른 파일은 이것뿐이다. 상태 집합의 단일 원천은 `domain/state/visit_status.py` 표이고, 상태 클래스(`visit_state.py`)·`ACTIVE_STATUSES`·`COUNTED_STATUSES`·ORM CHECK·부분 색인·`DayCountsView.of`가 거기서 파생한다. ORM 문자열은 마이그레이션 0006 과 글자까지 같아 스키마 드리프트가 없다.

### 남는 것 — 알고 미룬다

- `transition_visits`가 잠그기 전에 `get_many`를 한 번 더 읽는다(되돌리기가 아니어도). `lock_visits`도 같은 것을 읽으므로 방문당 조회 하나가 늘었다. 조회 결과를 `lock_visits`에 넘기는 인자를 두면 없앨 수 있으나 잠금 순서 서비스의 서명을 늘리는 값어치가 없다고 봤다.
- 행동 축의 스키마 `Literal`(`transition_visits_schema.py`)은 API 계약이라 남긴다. 행동을 더하면 `ACTIONS`·바탕 메서드·스키마 셋을 고친다.
- 상태를 더하면 여전히 새 마이그레이션을 손으로 써야 한다(CHECK·부분 색인). `test_schema_drift`는 이를 잡지 못하므로(compare_metadata 는 CHECK·부분 색인 WHERE 를 비교하지 않는다 — 최종 검토가 확인) `tests/integration/test_visit_status_schema.py`가 실제 DB 를 표와 대조한다.
