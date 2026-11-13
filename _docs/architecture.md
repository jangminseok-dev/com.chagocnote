# 아키텍처 규칙

## 계층

앱 내부는 `adapter → app → domain` 방향으로만 의존한다. `dependencies/`는 조립 전용이라 어느 계층이든 import할 수 있다.

    <app>/
    ├── domain/{entities,value_objects,services}/   # 표준 라이브러리만
    ├── app/{ports/{input,output},use_cases,dtos,services}/
    ├── adapter/inbound/api/{schemas,v1}/
    ├── adapter/outbound/{orm,pg,mappers,redis,gateways, …GoF 이름 폴더}/
    ├── dependencies/
    └── tests/

## 수직 슬라이스 1:1

유스케이스마다 `<이름>_router` · `<이름>_schema` · `<이름>_dto` · `ports/input/<이름>_use_case` · 아웃바운드 포트 · `<이름>_interactor` · `<이름>_provider` · `test_<이름>_interactor`를 하나씩 둔다. 한 파일에 여러 슬라이스를 넣지 않는다.

허용하는 예외는 세 가지다.
1. HTTP 표면이 없는 슬라이스는 schema와 router를 생략한다.
2. DTO와 리포지토리는 도메인 말로 이름 지을 수 있다 (`token_dto`, `user_repository`).
3. entity·VO·mapper는 로직이 있을 때만 만든다.

새 라우터 묶음에는 `GET <prefix>/myself`를 둔다. 제공하는 엔드포인트, 다루는 데이터, 제약을 실제대로 적는다. 배역이나 은유를 쓰지 않는다.

유스케이스는 어댑터 스키마가 아니라 app DTO(frozen dataclass)를 받는다. 스키마와 DTO 사이의 변환은 라우터가 한다. 아웃바운드 포트는 인터랙터가 실제로 호출하는 메서드만 가진다.

## 허브-스포크

- 허브는 `apps/hub`다. 포트(ABC)와 DTO만 가진다.
- 스포크는 허브의 추상에만 의존한다. 스포크끼리 import하지 않고, 허브는 스포크를 import하지 않는다.
- 스포크를 넘는 외래 키는 걸지 않는다. 다른 스포크의 ID는 인덱스만 있는 정수 컬럼이다.
- `core/`는 인프라 공유(DB 세션, 설정, 토큰 검증)만 맡는다. `core/security.py`가 `users` 테이블을 원시 SQL로 조회하는 것은 의도한 예외다. core가 스포크의 ORM을 import할 수 없기 때문이다. 정책(예: 재인증의 최근 로그인 창)은 core에 두지 않고 그 스포크의 도메인에 둔다 — `auth/domain/services/recent_login.py`.
- `core/`는 허브의 추상(포트 ABC와 DTO)을 import할 수 있다. 스포크는 import할 수 없다.
- 허브 포트를 구현하는 슬라이스는 그 포트를 입력 포트로 삼는다. 인터랙터가 허브 포트 ABC를 직접 상속하고, HTTP 표면이 없으므로 schema와 router를 생략한다.
- 허브 포트가 던지는 오류는 `hub/app/errors.py`의 `HubPortError` 하위 타입뿐이다. 구현 스포크는 자기 도메인 오류를 잡아 허브 오류로 바꿔 던지고, 소비 스포크와 테스트 스텁은 그 타입만 안다. HTTP 상태는 `core/hub_errors.py`에 적고 `install_error_handlers`가 두 진입점에 자동으로 등록한다(`tests/test_hub_errors.py`가 빠진 것을 잡는다).

## 허브 포트 조립

스포크의 `dependencies/`도 다른 스포크를 import하지 않는다. 다른 스포크가 구현한 허브 포트가 필요하면 다음과 같이 한다.

1. 소비하는 스포크의 `dependencies/hub_ports.py`에 "자리" 함수를 둔다. 반환 타입은 허브 포트이고, 호출되면 `RuntimeError`를 던진다.
2. 프로바이더는 `Depends(자리)`로 포트를 받는다.
3. 진입점(`main.py`, `auth_main.py`)이 `app.dependency_overrides[자리] = 구현 스포크의 프로바이더`로 채운다.

매장 접근 확인(`ShopAccessPort`) 자리는 모든 매장 범위 스포크가 쓰므로 `core/shop_guard.py`에 있다. 매장 범위의 라우터는 `Depends(get_shop_context)`(소속만 확인) 또는 `Depends(require_permission("…"))`(권한까지 확인)로 `ShopContext`를 받는다. 결정 경위는 `_docs/decisions/002-hub-port-assembly.md`에 있다.

## 프로세스 배치

`/v1/auth/*` 경로의 라우터는 인증 프로세스(`auth_main.py`)에, 나머지는 전부 API 프로세스(`main.py`)에 장착한다. 게이트웨이도 같은 규칙으로 경로를 나눈다.

## GoF 폴더 작명 규칙

통상적인 폴더 이름은 그대로 쓴다. 그 밖에 기능을 묶으려고 새로 만드는 폴더에는 GoF 패턴 이름을 붙인다. 조건은 두 가지다.
1. 폴더의 코드가 실제로 그 패턴을 구현할 때만 붙인다. 맞는 패턴이 없으면 평범한 도메인 단어를 쓴다.
2. 스포크 이름은 도메인의 말을 유지한다. `hub`도 그대로 둔다.

| 위치 | 패턴 | 내용 |
|---|---|---|
| `core/singleton/` | Singleton | 비밀값 관리자처럼 프로세스에 하나만 있는 객체 |
| `auth/adapter/outbound/strategy/` | Strategy | 제공자별 `SocialProviderPort` 구현 |
| `auth/adapter/outbound/factory/` | Factory | 설정에 따라 제공자 구현을 만들어 담아 두고 이름으로 골라 준다 |
| `visit/domain/state/` | State | 방문 상태 전이(예약됨·미용 중·완료·취소·노쇼) |
| `core/observer/`, `notification/adapter/inbound/observer/` | Observer | 도메인 이벤트 발행과 구독 — `core/observer/in_process_event_bus.py`가 허브 포트 `DomainEventPort`의 구현(같은 프로세스·같은 세션의 동기 버스, 구독자 목록은 `main.py`가 기동 때 채운다), notification 의 `visit_event_subscriber.py`가 구독자 |
| `visit/domain/chain/` (예정) | Chain of Responsibility | 예약 체크리스트 규칙 |
| `search/adapter/outbound/decorator/` (예정) | Decorator | LLM 포트를 감싼 개인정보 마스킹 |
| `visit/app/template/` (예정) | Template Method | 말로 기록하기 절차의 뼈대 |
| `search/app/facade/` (예정) | Facade | RAG 단일 입구 |
| `notification/adapter/outbound/strategy/` | Strategy | 발송 업체별 `MessageGatewayPort` 구현 — `solapi_gateway.py`(실제), `fake_gateway.py`(dev·흐름 확인). 키 유무와 `APP_ENV`로 하나를 고른다 |
| `app/lib/core/proxy/` (예정) | Proxy | 토큰 자동 첨부·갱신 API 클라이언트 |
| `app/lib/design/bridge/` (예정) | Bridge | 글래스 구현 교체 지점 |

새 패턴 폴더를 만들면 이 표에 한 줄을 더한다.

## 도메인 이벤트

첫 구독자(⑥ 알림톡)가 생기면서 허브에 `DomainEventPort`(`hub/app/ports/domain_event_port.py`)와 이벤트 DTO(`hub/app/dtos/visit_events.py`)를 두었다. 구현은 `core/observer/`의 **같은 프로세스·같은 세션의 동기 버스**다 — 발행한 인터랙터의 트랜잭션 안에서 구독자가 차례로 돌고, 구독자가 던지면 발행한 요청이 실패한다. 별도 이벤트 저장소는 없다. 구독자(notification)가 같은 트랜잭션에 쓰는 `notification_messages` 큐가 아웃박스 역할을 하고, 요청 밖의 디스패처가 그 큐를 집어 외부를 부른다. 메시지 브로커·다른 프로세스로 나갈 일이 생기면 버스 어댑터만 바꾼다.

- 발행은 `dependencies/hub_ports.py`의 자리(`get_domain_events`)로 받고 `main.py`가 `get_event_bus`를 꽂는다. 구독은 `main.py`가 기동 때 `subscribe(handler)`로 등록한다 — 구독자는 `(AsyncSession, VisitEvent)`를 받는 어댑터(`<app>/adapter/inbound/observer/`)이고 `app` 층에 두지 않는다(프레임워크 격리).
- 구독자는 외부(HTTP)를 부르지 않는다. 외부 호출은 요청 밖(디스패처)에서 잠금 없이 한다.
- 요청 밖에서 `ShopContext`가 필요하면 `notification/app/services/system_context.py` 하나로 만든다(권한 빔). 전 매장 질의는 `ShopContext`를 받지 않는 별도 포트(`NotificationQueueRepository`)에 둔다.

## 보호자 표면

⑦에서 세 번째 표면이 생겼다 — 매장 멤버(`/v1/shops/{shop_id}/…`, `ShopContext`), 로그인 없는 공개 알림장(`/v1/public/…`, 토큰의 서명이 범위), **로그인한 보호자(`/v1/me/guardian/…`, `GuardianContext`)**다.

- 보호자는 매장의 멤버가 아니다. 범위는 계정이 이어 둔 연결 하나(`link_id`)이고, `core/guardian_guard.py`의 `get_guardian_context`가 매 요청마다 허브 포트 `GuardianAccessPort`(구현: guardian)로 확인해 `GuardianContext(link_id, user_id, shop_id, customer_id)`를 준다. `core/shop_guard.py`와 같은 자리다.
- 연결(`guardian_links`)은 `guardian` 스포크가, 알림장 읽기는 `visit`이 소유한다. 둘은 허브 포트로만 만난다 — `ReportLinkPort`(visit 이 구현, 알림장 토큰 → 매장·고객·열림), `GuardianAccessPort`(guardian), `GuardianLifecyclePort`(guardian — auth 의 탈퇴와 customer 의 익명화가 부른다).
- `guardian`은 `ShopContext`를 만들지 않는다. 보호자용 읽기(visit)는 공개 알림장과 같은 읽기 전용 컨텍스트(`public_context`)와 같은 조립(`describe_report`)·같은 응답 스키마를 쓴다 — 내부 메모가 보호자에게 새는 사고를 구조로 막는다.
- `GuardianLinkRepository`는 `ShopContext`를 받지 않는다(범위가 계정이다) — `PublicReportRepository`·`NotificationQueueRepository`와 같은 예외다.

