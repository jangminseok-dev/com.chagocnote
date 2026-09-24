# 검증 장치

백엔드 명령은 `infra/`에서, 앱 명령은 `app/`에서 실행한다.

| 무엇을 | 명령 |
|---|---|
| 단위 테스트 | `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` |
| 통합 테스트 (실제 Postgres·Redis) | `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` |
| 구조 계약 | `docker compose run --rm --no-deps backend lint-imports --config .importlinter` |
| 라우트 표 | `docker compose run --rm --no-deps auth python scripts/print_routes.py` (인증 프로세스를 import하려면 개인키가 필요해서 `auth` 서비스에서 돌린다) |
| 로그인 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_auth_flow.sh` |
| 매장 개설·합류 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_shop_flow.sh` — 개발 DB에 확인용 매장과 유저가 남는다 |
| 회원 탈퇴 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_account_flow.sh` — 개발 DB에 "탈퇴한 사용자" 행이 남는다 |
| 고객·반려동물 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_customer_flow.sh` — 개발 DB에 확인용 매장·유저와 익명화한 고객이 남는다 |
| 고객 검색 줄 재생성 | `docker compose run --rm backend python scripts/rebuild_customer_search.py` (검색 줄이 원본과 어긋났을 때) |
| 예약·방문 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_visit_flow.sh` — 개발 DB에 확인용 매장·유저·고객·방문이 남는다 |
| 최근 방문순 키 복구 | `docker compose run --rm backend python scripts/rebuild_last_visit.py` (고객 목록 '최근 방문순'이 방문 기록과 어긋났을 때) |
| 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
| 앱 정적 분석 | `flutter analyze` (`app/`에서, 경고 0) |
| 앱 테스트 (위젯·골든·`ApiClient` 포함) | `flutter test --timeout 30s` (`app/`에서. 화면이 닫히기를 잘못 기다리는 테스트가 기본 10분을 멈추지 않게) |
| 앱 골든 갱신 | `flutter test --update-goldens` (`app/`에서, 의도해서 바꿀 때만) |
| 앱 개발용 실행 | `app/tool/run_dev.sh` (백엔드를 `infra/`에서 먼저 띄운 뒤) |
| 앱 흐름 확인 (시뮬레이터 + 실서버) | `SHOTS_DIR=<폴더> flutter drive --driver=test_driver/integration_test.dart --target=integration_test/<파일> -d <기기> --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 …` (`app/`에서. 파일 머리 주석에 준비와 추가 `--dart-define`이 있다 — `visit_flow_test.dart`(③-A2), `draft_flow_test.dart`(③-A3 카톡 초안)) |
| 공유 받기 확인 | 실기기에서 카톡 [공유] → 차곡노트 (시뮬레이터엔 카톡이 없고 App Group 은 서명이 있어야 붙는다) |

- 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 쓴다. 개발 데이터를 건드리지 않는다. pytest가 세션마다 한 번 `scripts/prepare_test_db.py`를 돌려 스키마를 비우고 `alembic upgrade head`로 다시 만든다. 테스트 사이에는 시드 표(`roles`, `permissions`, `role_permissions`, `pet_condition_types`)와 마이그레이션 버전 표(`alembic_version`)를 뺀 모든 표를 비운다.
- 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 마이그레이션 결과와 ORM이 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에 등록한다.
- 구조 위반은 테스트가 아니라 import-linter가 잡는다. 구조를 건드린 변경은 테스트와 구조 계약을 둘 다 돌린다. 계약은 6종이다 — 설계 문서가 말하는 5종에 "core는 스포크를 import하지 않는다"를 하네스에서 더했다.
- 라우터를 추가하거나 옮긴 변경은 라우트 표를 변경 전후로 비교한다.
- 유스케이스는 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다. 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간 잡힌다(`apps/*/tests/test_fakes_are_ports.py`). 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 상속하지 않는다.
- `tests/integration/`은 두 프로세스의 실제 앱 객체에 붙어 프로바이더·DB 커밋·Redis까지 통과한다. 인증 프로세스의 개인키는 테스트마다 새로 만든 키로 바꿔 넣는다.
- 스포크를 새로 만들면 첫 통합 테스트로 "A매장 멤버가 B매장의 경로를 부르면 403"(테넌트 격리)을 둔다.
- 허브 포트 자리를 새로 만들어도 더할 목록은 없다. `tests/route_inspection.py`가 두 앱의 라우트 의존성 트리를 훑어 ① 채우지 않은 허브 포트 자리 ② `{shop_id}` 경로인데 `get_shop_context`를 거치지 않는 라우트 ③ `/v1/platform/` 경로인데 `require_operator`를 거치지 않는 라우트를 잡는다. API 프로세스는 `tests/test_hub_port_binding.py`가, 인증 프로세스는 `tests/integration/test_route_wiring.py`가 돌린다.
- 권한이나 불변식이 걸린 슬라이스를 계획할 때는 악의적이거나 운 나쁜 시나리오(내보내진 사람이 쥔 것, 같은 요청이 동시에 두 번, 읽기와 쓰기 사이)를 먼저 표로 적고, 각각을 막는 코드와 테스트를 작업에 넣는다. 작업별 검토는 계획서와의 일치가 아니라 그 표를 기준으로 한다.
- 통합 테스트에서 두 번째 로그인 수단이 필요하면 `fake_kakao` 픽스처를 쓴다.
- 마이그레이션에 시드 표를 새로 만들면 루트 `conftest.py`의 `_KEEP_TABLES`에 더한다. 빠뜨리면 첫 테스트가 시드를 비워 그다음 테스트부터 실패한다.
- 두 세션 경합 테스트는 막힌 호출을 `asyncio.create_task`로 들고 있다가 앞선 세션이 커밋한 뒤의 결과를 본다. "기다렸다"만으로 판별하지 않는다 — 외래 키의 암묵적 잠금이나 같은 행의 다른 잠금 때문에 잠금 코드가 없어도 기다릴 수 있다. 잠금 코드를 빼는 변이로 테스트가 실패하는지 확인한다.
