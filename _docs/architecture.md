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
- `core/`는 인프라 공유(DB 세션, 설정, 토큰 검증)만 맡는다. `core/security.py`가 `users` 테이블을 원시 SQL로 조회하는 것은 의도한 예외다. core가 스포크의 ORM을 import할 수 없기 때문이다.
- `core/`는 허브의 추상(포트 ABC와 DTO)을 import할 수 있다. 스포크는 import할 수 없다.
- 허브 포트를 구현하는 슬라이스는 그 포트를 입력 포트로 삼는다. 인터랙터가 허브 포트 ABC를 직접 상속하고, HTTP 표면이 없으므로 schema와 router를 생략한다.

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
| `visit/domain/state/` (예정) | State | 방문 상태 전이 |
| `core/observer/`, `<app>/adapter/inbound/observer/` (예정) | Observer | 도메인 이벤트 발행과 구독 |
| `visit/domain/chain/` (예정) | Chain of Responsibility | 예약 체크리스트 규칙 |
| `search/adapter/outbound/decorator/` (예정) | Decorator | LLM 포트를 감싼 개인정보 마스킹 |
| `visit/app/template/` (예정) | Template Method | 말로 기록하기 절차의 뼈대 |
| `search/app/facade/` (예정) | Facade | RAG 단일 입구 |
| `notification/adapter/outbound/strategy/` (예정) | Strategy | 알림 발송 수단 |
| `app/lib/core/proxy/` (예정) | Proxy | 토큰 자동 첨부·갱신 API 클라이언트 |
| `app/lib/design/bridge/` (예정) | Bridge | 글래스 구현 교체 지점 |

새 패턴 폴더를 만들면 이 표에 한 줄을 더한다.

## 도메인 이벤트 도입 계획

이벤트 발행 포트는 첫 구독자가 생길 때(미용 완료 → 통계·검색·알림) 허브에 도입한다. 처음에는 같은 프로세스 안의 단순한 구현으로 시작하고, 신뢰성이 필요해지면 아웃박스 방식으로 어댑터만 바꾼다. 그 전에는 포트를 만들지 않는다.
