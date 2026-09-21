# 검증 장치

모든 명령은 `infra/`에서 실행한다.

| 무엇을 | 명령 |
|---|---|
| 단위 테스트 | `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` |
| 통합 테스트 (실제 Postgres·Redis) | `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` |
| 구조 계약 | `docker compose run --rm --no-deps backend lint-imports --config .importlinter` |
| 라우트 표 | `docker compose run --rm --no-deps auth python scripts/print_routes.py` (인증 프로세스를 import하려면 개인키가 필요해서 `auth` 서비스에서 돌린다) |
| 로그인 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_auth_flow.sh` |
| 매장 개설·합류 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_shop_flow.sh` — 개발 DB에 확인용 매장과 유저가 남는다 |
| 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |

- 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 쓴다. 개발 데이터를 건드리지 않는다. pytest가 세션마다 한 번 `scripts/prepare_test_db.py`를 돌려 스키마를 비우고 `alembic upgrade head`로 다시 만든다. 테스트 사이에는 시드 표(`roles`, `permissions`, `role_permissions`)를 뺀 모든 표를 비운다.
- 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 마이그레이션 결과와 ORM이 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에 등록한다.
- 구조 위반은 테스트가 아니라 import-linter가 잡는다. 구조를 건드린 변경은 테스트와 구조 계약을 둘 다 돌린다.
- 라우터를 추가하거나 옮긴 변경은 라우트 표를 변경 전후로 비교한다.
- 유스케이스는 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다.
- `tests/integration/`은 두 프로세스의 실제 앱 객체에 붙어 프로바이더·DB 커밋·Redis까지 통과한다. 인증 프로세스의 개인키는 테스트마다 새로 만든 키로 바꿔 넣는다.
- 스포크를 새로 만들면 첫 통합 테스트로 "A매장 멤버가 B매장의 경로를 부르면 403"(테넌트 격리)을 둔다. 허브 포트 자리를 새로 만들면 `tests/test_hub_port_binding.py`에 더한다.
