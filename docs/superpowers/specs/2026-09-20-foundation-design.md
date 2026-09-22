# 차곡노트 — 서브 프로젝트 ① 기반 설계

- 작성일: 2026-09-20
- 상태: 사용자 검토 대기
- 범위: 백엔드 골격, 신원·매장별 RBAC, 계정 연결·회원 탈퇴, Flutter 골격과 디자인 시스템
- 다음 단계: 이 문서가 승인되면 구현 계획을 작성한다.

---

## 1. 배경

### 1.1 무엇을 만드는가

**차곡노트**는 반려동물 미용 매장과 보호자를 잇는 양면 플랫폼이다. 매장은 예약, 고객, 미용 기록(미용 전·후 사진과 영상, 매출, 메모)을 관리하고, 보호자는 매장이 보낸 미용 알림장을 받아 본다. 이름은 기록이 "차곡차곡" 쌓인다는 뜻에서 왔다.

- 첫 입점 매장은 **Hiss Haus**다. 사장님 혼자 운영하는 1인샵이고, 지금은 예약·고객 응대·사진 전송을 모두 카카오톡으로 한다. 그래서 첫 출시의 합격 기준은 "카카오톡으로 하던 것보다 쉬운가"이다.
- Hiss Haus는 플랫폼 이름이 아니라 입점 매장(테넌트) 이름이다. 코드, 패키지명, 문서에서 플랫폼 이름으로 쓰지 않는다.
- 경쟁 서비스(그루머노트, 반짝, 티피, 포들리 파트너스 등)가 이미 있고 상당수가 무료다. 사용자는 정면 승부를 택했다. 차별 무기는 사진 중심 UI, 빠른 고화질 미디어, 보호자 쪽 기록 누적, AI 기능(말로 기록하기, 대화형 검색)이다.
- 추후 네일아트 같은 사람 뷰티 업종으로 넓힐 수 있다. 그래서 이름과 데이터 모델을 반려동물에 묶지 않는다.

### 1.2 이름과 주소

| 항목 | 값 | 비고 |
|---|---|---|
| 이름 | 차곡노트 | 확정. 다만 바뀔 가능성을 열어 둔다. |
| 영문 표기 | chagocnote | |
| 도메인 | 아직 구매하지 않는다 | 웹은 Vercel 기본 주소로 시작한다. 후보는 chagocnote.com이다. |
| 폴더명 | `com.chagocnote` | 2026-09-20에 `app.hisshaus`에서 옮겼다. |
| 앱 패키지 ID | `com.chagocnote.app` (임시) | 첫 스토어 제출 직전에 확정한다. 그 전에는 자유롭게 바꿀 수 있다. |

### 1.3 전체 서브 프로젝트 순서

각 서브 프로젝트는 설계 → 계획 → 구현을 따로 거친다. 이 문서는 ①만 다룬다.

| 순서 | 서브 프로젝트 |
|---|---|
| **①** | **기반 (이 문서)** |
| ② | 고객·반려동물 + 기본 검색 |
| ③ | 예약 + 사진 달력 + 체크리스트 자동 판정 + 주의 고객·노쇼 관리 |
| ④ | 미용 기록 + 피드 + 말로 기록하기 |
| ⑤ | 미용 알림장 (1회용 웹 페이지 + 공유 버튼) |
| ⑥ | 알림톡 자동 발송 |
| ⑦ | 고객 회원 (로그인 후 전체 기록 보기) |
| ⑧ | 매출 통계 |
| ⑨ | 대화형 RAG 검색 (개인정보 마스킹 계층 포함) |
| ⑩ | 자유 공지·홍보 메시지, 전자 동의서 등 경쟁사 기능 따라잡기 |

①~⑤까지가 Hiss Haus에 실제로 투입하는 1차 버전이다.

---

## 2. ① 기반의 범위

### 2.1 만드는 것

1. 모노레포와 개발 환경: docker compose 하나로 전체가 뜬다.
2. 백엔드 골격: 헥사고날 구조, 허브-스포크, import-linter 계약 5종.
3. 소셜 로그인(카카오, Apple, 구글)과 자체 JWT 발급.
4. 매장(테넌트), 매장별 역할·권한, 초대 코드로 합류.
5. 플랫폼 운영자의 매장 개설.
6. 계정 연결·해제, 회원 탈퇴.
7. Flutter 앱 골격: 로그인부터 홈 셸과 설정까지의 흐름, 디자인 토큰, 기본 위젯 9개.
8. 하네스 문서: `CLAUDE.md`, `_docs/architecture.md`, `_docs/harness.md`, 앱별 문서.

### 2.2 만들지 않는 것

- 고객, 예약, 기록, 미디어 업로드, 알림, 검색, 통계 (②~⑨).
- 도메인 이벤트 포트: 첫 구독자가 생기는 ④에서 도입한다. 빈 껍데기 포트를 만들지 않는다는 규칙 때문이다.
- 오프라인 캐시: 캐시할 데이터가 생기는 ③에서 넣는다.
- 매장 셀프 가입, 구독·결제, 운영자 콘솔 화면, 사용량 대시보드.
- 매장 데이터 파기: 매장을 닫는 표시(`closed_at`)까지만 만든다. 실제 파기는 데이터가 생기는 ④ 이후에 운영자 기능으로 만든다.
- 계정 자동 병합.
- 클라우드 배포, CI.

---

## 3. 저장소와 개발 환경

### 3.1 저장소 구성

```
com.chagocnote/
├── CLAUDE.md                 # 하네스: 규칙·명령어·주의사항 (한국어)
├── README.md
├── .gitignore                # .env*, .superpowers/, 빌드 산출물
├── .env.example              # 키 목록만 (값 없음)
├── _docs/
│   ├── architecture.md       # 계층·슬라이스 규칙, GoF 폴더 대응표, 이벤트 도입 계획
│   ├── harness.md            # 검증 장치 (pytest, lint-imports, flutter analyze/test)
│   └── decisions/            # 결정 기록
├── docs/superpowers/specs/   # 서브 프로젝트별 설계 문서
├── backend/
│   ├── main.py               # API 프로세스 (토큰을 발급할 수 없다)
│   ├── auth_main.py          # 인증 프로세스 (JWT 개인키 보유)
│   ├── core/                 # database, config, singleton/, security
│   ├── apps/                 # hub, auth, tenancy, platform_admin
│   ├── alembic/ · alembic.ini
│   ├── .importlinter · pytest.ini · requirements.txt
│   └── scripts/              # grant_operator.py, print_routes.py
├── app/                      # Flutter 3.41 이상, iOS 15 이상 / Android
└── infra/
    ├── docker-compose.yml
    ├── docker/Dockerfile
    └── caddy/Caddyfile
```

각 앱은 `apps/<app>/_docs/CLAUDE.md`를 두고, `apps/<app>/CLAUDE.md`는 그 파일로 가는 심볼릭 링크로 만든다. redoceanmap과 같은 방식이다.

### 3.2 개발 환경

이 맥북이 개발 기기다. 실사용 시점에 소형 클라우드로 옮기며, 어느 클라우드를 쓸지는 그때 정한다.

compose 서비스는 다음과 같다. 포트는 모두 `127.0.0.1`에만 바인딩한다.

| 서비스 | 역할 |
|---|---|
| `pgvector` | PostgreSQL 17 + pgvector. ⑨에서 DB를 갈아엎지 않으려고 처음부터 이 이미지를 쓴다. |
| `redis` | 리프레시 토큰 저장 |
| `minio` | 로컬 S3. ①에서는 기동만 하고 ④부터 쓴다. 운영에서는 AWS S3 서울 리전으로 교체한다. |
| `backend` | API 프로세스. 코드는 볼륨 마운트로 핫리로드된다. 기동할 때 `alembic upgrade head`를 실행한다. |
| `auth` | 인증 프로세스 |
| `gateway` | Caddy. `/v1/auth/*`는 `auth`로, 나머지는 `backend`로 보낸다. 앱은 주소 하나만 안다. |

k3s는 쓰지 않는다. 백엔드 테스트와 구조 검증은 컨테이너 안에서 돌린다.

```bash
cd infra && docker compose up -d
docker compose run --rm backend pytest apps -q -p no:cacheprovider
docker compose run --rm backend lint-imports --config .importlinter
cd ../app && flutter analyze && flutter test
```

### 3.3 비밀값

- `.env`는 실제 값을 담고 git에서 제외한다. `.env.example`에는 키 이름만 등록한다.
- `.env.auth`는 인증 프로세스 전용 비밀값(`JWT_PRIVATE_KEY_B64`, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)을 담는다. 코드에서는 `core/auth_config.py`만 이 값들을 읽는다. 자동으로 로드되지 않으며, `load_auth_env()`를 명시적으로 호출한 프로세스(`auth_main.py`)만 읽는다.
- `load_dotenv`는 `core/singleton/secret_manager.py` 한 곳에서만 호출한다. redoceanmap의 `core/key/`에 해당하는 자리이며, 4.3절의 작명 규칙에 따라 폴더 이름이 바뀌었다. 런타임 코드는 `core/config.py`의 상수만 쓴다. 스크립트와 엔트리포인트는 `get_secret_manager()`를 쓴다.
- ①에서 필요한 키: `DATABASE_URL`, `REDIS_URL`, `JWT_PUBLIC_KEY_B64`, `JWT_PRIVATE_KEY_B64`, `KAKAO_APP_ID`(카카오 토큰이 우리 앱에서 발급됐는지 확인한다), `KAKAO_REST_API_KEY`, `KAKAO_ADMIN_KEY`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_B64`, `APPLE_BUNDLE_ID`, `GOOGLE_CLIENT_ID_IOS`, `GOOGLE_CLIENT_ID_ANDROID`, `IDENTITY_TOKEN_ENC_KEY`(Apple 리프레시 토큰 암호화용), `S3_*`(minio).

### 3.4 작업 규칙

- 주석, 문서, 커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이다.
- 커밋과 푸시는 사용자가 요청할 때만 한다. CI는 두지 않고 로컬에서 검증한다.
- I/O 작업은 `async def`, CPU 작업은 `def`로 작성한다. 포트와 구현체의 `def`/`async def`를 일치시킨다.

---

## 4. 백엔드 구조

### 4.1 원칙

- **모듈러 모놀리식**이다. 앱 내부는 `adapter → app → domain` 방향으로만 의존한다. 앱 사이는 허브-스포크이며, 스포크끼리 직접 import하지 않고 허브는 스포크를 모른다.
- **수직 슬라이스 1:1**: 유스케이스마다 router, schema, dto, input port, output port, interactor, provider, test 파일을 하나씩 둔다. 한 파일에 여러 슬라이스를 넣지 않는다. 허용하는 예외는 세 가지다. HTTP 표면이 없는 슬라이스는 schema와 router를 생략한다. DTO와 리포지토리는 도메인 말로 이름 지을 수 있다. entity, VO, mapper는 로직이 있을 때만 만든다.
- **새 라우터에는 `GET <prefix>/myself`를 둔다.** 실제 기능(엔드포인트, 데이터, 제약)을 설명하며, 자기소개도 스키마 → DTO → 포트 → 인터랙터 → 기록 포트 → 로그 어댑터 → 프로바이더 → 스텁 테스트의 전체 단면을 거친다.
- 유스케이스는 어댑터 스키마가 아니라 app DTO(frozen dataclass)를 받는다.
- 엔티티는 `int` 단일 PK `id`, SQLAlchemy 2.0 스타일로 만든다.
- **스포크를 넘는 외래 키는 걸지 않는다.** 다른 스포크의 ID는 인덱스만 있는 정수 컬럼으로 둔다.

### 4.2 앱 내부 폴더

```
<app>/
├── domain/{entities,value_objects,services}/
├── app/{ports/{input,output},use_cases,dtos}/
├── adapter/
│   ├── inbound/api/{schemas,v1}/
│   └── outbound/{orm,pg,mappers,gateways, …GoF 이름 폴더}/
├── dependencies/
├── tests/
└── _docs/CLAUDE.md
```

### 4.3 GoF 폴더 작명 규칙

통상적으로 쓰는 폴더 이름(위 구조의 이름들, `core`, `lib`, `widgets`, `features`, `screens` 등)은 그대로 쓴다. 그 밖에 기능을 묶으려고 새로 만드는 폴더에는 GoF 디자인 패턴 이름을 붙인다. 조건은 두 가지다.

1. 폴더의 코드가 **실제로 그 패턴을 구현할 때만** 붙인다. 맞는 패턴이 없으면 평범한 도메인 단어를 쓴다.
2. 스포크 이름은 도메인의 말을 유지한다. `hub`도 그대로 둔다.

①에서 생기는 패턴 폴더는 다음과 같다. 이후 서브 프로젝트의 대응표는 `_docs/architecture.md`에 둔다.

| 위치 | 패턴 | 내용 |
|---|---|---|
| `auth/adapter/outbound/strategy/` | Strategy | 카카오·Apple·구글별 `SocialProviderPort` 구현 3개 |
| `auth/adapter/outbound/factory/` | Factory | 설정에 따라 제공자 구현을 만들어 담아 두고 이름으로 골라 준다 |
| `core/singleton/` | Singleton | 비밀값 관리자처럼 프로세스에 하나만 있는 객체 |
| `app/lib/core/proxy/` | Proxy | 토큰을 붙이고 401이면 갱신 후 재시도하는 API 클라이언트 |
| `app/lib/design/bridge/` | Bridge | 글래스 구현을 교체하는 지점 |


### 4.4 앱과 슬라이스

| 앱 | 범위 | 소유 데이터 | 슬라이스 |
|---|---|---|---|
| `hub` | — | 없음 (포트 ABC와 DTO만) | — |
| `auth` | 플랫폼 | 유저, 소셜 신원, 플랫폼 운영자, 리프레시 토큰(Redis) | `myself`, `social_login`, `refresh_token`, `logout`, `get_me`, `link_identity`, `unlink_identity`, `withdraw` |
| `tenancy` | 플랫폼 | 매장, 역할·권한, 소속, 초대 | `myself`, `create_invite`, `accept_invite`, `list_members`, `change_member_role`, `remove_member`, `get_shop`, `update_shop` |
| `platform_admin` | 플랫폼 | 없음 (허브 포트만 소비) | `myself`, `create_shop` |

허브 포트를 구현하는 쪽은 HTTP 표면이 없는 슬라이스를 하나씩 더 가진다. tenancy는 `resolve_shop_access`·`provision_shop`·`list_memberships`, auth는 `check_operator`·`get_user_profiles`다. auth의 `grant_operator`도 HTTP 표면이 없고 `scripts/grant_operator.py`가 부른다. 직원용 초대의 역할은 언제나 직원이며, 사장을 늘리려면 합류한 뒤 역할을 바꾼다. 매장 정보 수정은 폼 전체를 보내는 `PUT`이다.

### 4.5 API 표면

| 경로 | 프로세스 | 인증 |
|---|---|---|
| `POST /v1/auth/social` · `/refresh` · `/logout` · `GET /v1/auth/myself` | auth | 없음 또는 리프레시 토큰 |
| `POST·DELETE /v1/auth/identities` · `DELETE /v1/auth/account` | auth | 액세스 토큰 |
| `GET /v1/me` | backend | 액세스 토큰 |
| `/v1/shops/{shop_id}/members` · `/invites` · `/settings` | backend | 액세스 토큰 + 매장 소속 + 권한 |
| `GET /v1/shops/myself` | backend | 없음 |
| `POST /v1/invites/accept` | backend | 액세스 토큰 |
| `POST /v1/platform/shops` · `GET /v1/platform/myself` | backend | 액세스 토큰 + 플랫폼 운영자 |

프로세스 배치 규칙은 하나다. `/v1/auth/*` 경로의 라우터는 auth 프로세스에 장착하고, 나머지는 전부 backend 프로세스에 장착한다. `get_me`는 auth 앱의 슬라이스지만 토큰을 발급하지 않으므로 backend 프로세스에 장착한다. 게이트웨이도 같은 규칙으로 경로를 나눈다.

이후 서브 프로젝트에서 표면 두 개가 더 생긴다. `/v1/me/…`(보호자 회원, ⑦)와 `/v1/public/reports/{token}`(게스트, ⑤)이다. 표면마다 인증 방식과 노출 필드를 분리해서, 매장의 내부 메모가 보호자에게 새는 사고를 구조로 막는다.

### 4.6 허브 계약

| 포트 | 구현 | 사용처 | 용도 |
|---|---|---|---|
| `ShopAccessPort.resolve(user_id, shop_id) → ShopContext` | tenancy | 매장 범위의 모든 스포크 | 소속, 역할, 권한, 매장 정지·닫힘 여부를 매 요청마다 DB에서 조회한다. 소속이 아니면 403이다. |
| `MembershipDirectoryPort.list_for_user(user_id)` | tenancy | auth (`get_me`) | 내가 속한 매장 목록 |
| `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy | auth (`withdraw`, 인증 프로세스) | 소속 해제와 매장 닫기. 미리 조회하는 메서드는 두지 않는다 — 조회와 적용 사이에 사장 수가 바뀔 수 있어서, 적용이 매장 행을 잠근 뒤 스스로 확인하고 409로 막는다. |
| `UserDirectoryPort.get_profiles(user_ids)` | auth | tenancy (`list_members`) | 멤버 이름과 프로필 사진 |
| `ShopProvisioningPort.create_shop(name, business_type)` | tenancy | platform_admin (`create_shop`) | 매장 생성과 사장용 초대 코드 발급 |
| `OperatorDirectoryPort.is_operator(user_id)` | auth | platform_admin | 플랫폼 운영자 여부 |
| `ActiveUserGuardPort.lock_active(user_id)` | auth | tenancy (`accept_invite`) | 초대 수락도 맨 앞에서 유저 행을 잠그고 활동 중인지(탈퇴·정지하지 않았는지) 다시 본다 — 탈퇴와 겹치면 기다렸다가, 탈퇴 뒤에는 거절된다. 유저 행을 보지 않던 옛 수락은 탈퇴와 겹치면 탈퇴한 유저의 소속을 되살렸다. |

계정을 바꾸는 유스케이스(`link_identity`·`unlink_identity`·`withdraw`)와 멤버십을 바꾸는 유스케이스는 맨 앞에서 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행 순서로 잠근 뒤 대상을 다시 읽는다. 잠금을 쥔 채 외부 HTTP는 부르지 않는다.

`ShopContext`는 허브 DTO의 값 객체다. 필드는 `shop_id`, `member_id`, `role`, `permissions`다. **이후 만드는 모든 매장 범위 리포지토리 포트는 이 값을 필수 첫 인자로 받는다.** 매장 컨텍스트 없이는 조회할 수 없게 해서, 다른 매장의 데이터가 섞이는 사고를 구조로 막는다.

auth와 backend는 별개 프로세스지만 같은 코드베이스와 같은 DB를 쓴다. 각 프로세스는 자기가 쓰는 허브 포트의 구현체를 프로바이더로 주입받는다.

권한 검사는 `require_permission("member:manage")` 형태의 FastAPI 의존성으로 만들고, 안에서 `ShopAccessPort`를 호출한다. 모든 매장 범위 스포크가 함께 쓰므로 `core/shop_guard.py`에 둔다. 허브 포트의 구현은 진입점이 소비하는 쪽의 자리에 꽂는다(`_docs/decisions/002-hub-port-assembly.md`).

### 4.7 import-linter 계약 5종

1. 앱 내부 계층: `adapter → app → domain`만 허용한다.
2. 스포크 상호 독립: 스포크끼리 import하지 않는다.
3. 프레임워크 격리: `app`과 `domain`에서 fastapi, sqlalchemy, redis를 import하지 않는다.
4. 도메인 순수성: `domain`은 표준 라이브러리만 쓴다.
5. 허브 격리: 허브는 어떤 스포크도 import하지 않는다.

---

## 5. 신원과 RBAC

### 5.1 신원 모델

**User는 플랫폼에 하나만 있는 신원이다. 사장, 직원, 보호자는 계정의 종류가 아니라 그 사람과 매장 사이의 관계다.** 같은 사람이 A매장의 사장이면서 B매장의 고객일 수 있다.

- 사장이나 직원이 되는 것은 `shop_members`에 행이 하나 생기는 것이다.
- 보호자로서의 관계는 ⑦에서 매장의 고객 카드와 User를 잇는 claim으로 만든다. ①에서는 만들지 않는다.
- 토큰은 "이 사람이 누구인가"만 식별한다. 사장으로 행동하는지 보호자로 행동하는지는 호출하는 API 표면과 매 요청의 DB 조회가 결정한다.
- 플랫폼 운영자는 User에 붙는 전역 지정이다.
- 데이터 접근은 언제나 컨텍스트(매장 또는 본인)를 거친다. User 신원만으로는 매장 데이터를 조회할 수 없다. 이 규칙 하나로 세 가지가 지켜진다. B매장 직원은 고객이 다른 매장의 사장인지 알 수 없다. 고객은 매장이 자신에 대해 적은 내부 메모를 볼 수 없다. 매장 사이에 고객 명단이 넘어가지 않는다.

### 5.2 테이블

모든 테이블은 `id`(int PK), `created_at`, `updated_at`을 가진다.

| 소유 앱 | 테이블 | 핵심 컬럼 |
|---|---|---|
| auth | `users` | `display_name`, `profile_image_url`, `phone`(선택), `suspended_at`, `deleted_at` |
| auth | `social_identities` | `user_id`, `provider`(kakao/apple/google), `provider_user_id`, `email`(선택), `provider_refresh_token_enc`(Apple 전용, 암호화) — (`provider`, `provider_user_id`) 유일, (`user_id`, `provider`) 유일(한 유저는 제공자마다 하나) |
| auth | `platform_operators` | `user_id`(유일), `granted_at` |
| auth | Redis | `auth:refresh:{해시}` → 발급 시점의 세대 (30일), `auth:refresh:used:{해시}` → 쓸 때의 세대, `auth:refresh:gen:{user_id}` → 현재 세대. 토큰은 `{user_id}.{난수}` 모양이고 원문은 저장하지 않는다. |
| tenancy | `shops` | `name`, `business_type`(기본값 `pet_grooming`), `phone`, `address`, `timezone`(기본값 `Asia/Seoul`), `suspended_at`, `closed_at` |
| tenancy | `roles` | `code`(owner/staff), `name` |
| tenancy | `permissions` | `code`, `description` |
| tenancy | `role_permissions` | `role_id`, `permission_id` |
| tenancy | `shop_members` | `shop_id`, `user_id`, `role_id`, `joined_at`, `removed_at` — 활성 행 기준 (`shop_id`, `user_id`) 유일 |
| tenancy | `shop_invites` | `shop_id`, `role_id`, `code_hash`, `created_by_member_id`(사장용 첫 초대는 null), `expires_at`, `max_uses`(기본값 1), `used_count`, `revoked_at` |

역할과 권한은 Alembic 시드로 넣는다.

| 권한 코드 | 뜻 | 사장 | 직원 |
|---|---|---|---|
| `reservation:write` | 예약 등록·수정 | ✅ | ✅ |
| `customer:write` | 고객·반려동물 등록·수정 | ✅ | ✅ |
| `record:write` | 미용 기록·사진 업로드 | ✅ | ✅ |
| `sales:write` | 기록할 때 매출 금액 입력 | ✅ | ✅ |
| `sales:read` | 매출 통계·합계 열람 | ✅ | ⛔ |
| `record:delete` | 기록 삭제 | ✅ | ⛔ |
| `customer:delete` | 고객 삭제 | ✅ | ⛔ |
| `member:manage` | 직원 초대·내보내기·역할 변경 | ✅ | ⛔ |
| `shop:update` | 매장 정보 수정 | ✅ | ⛔ |

①에서 실제로 검사하는 권한은 `member:manage`와 `shop:update`다. 나머지는 이후 서브 프로젝트가 쓰도록 시드에만 넣어 둔다.

### 5.3 토큰

- JWT는 RS256이다. 개인키는 auth 프로세스만 가지며, API 프로세스는 공개키로 검증만 한다.
- 액세스 토큰은 15분이다. 클레임은 `sub`(user_id), `jti`, `iat`, `exp`, `typ`이고, 소셜 로그인으로 받은 토큰에만 `auth_time`(로그인 시각)이 더 들어간다. 갱신으로 받은 토큰에는 없다. 역할과 권한은 넣지 않는다.
- 연결·해제·탈퇴는 로그인 300초 이내의 토큰만 받는다(`core/security.py`의 `require_recent_login`). 아니면 403(`REAUTH_REQUIRED`)이고, 앱은 다시 로그인한 뒤 한 번 재요청한다. 해제가 준 새 토큰은 원래 `auth_time`을 물려받는다 — 해제를 되풀이해 "최근 로그인"을 늘릴 수 없다.
- 리프레시 토큰은 30일이고, 사용할 때마다 새 토큰으로 교체한다. 이미 사용된 토큰이 다시 들어오면 탈취로 판단해서 그 유저의 모든 세션을 폐기한다. "모든 세션 폐기"는 유저의 세대를 하나 올리는 것이다. 토큰에 발급 시점의 세대가 찍혀 있어, 폐기와 동시에 발급되던 토큰도 함께 무효가 된다.
- 정지되거나 탈퇴한 유저는 매 요청의 조회에서 걸러진다. 이미 발급된 액세스 토큰으로도 탈퇴한 유저는 401(`UNAUTHENTICATED`), 정지된 유저는 403(`ACCOUNT_SUSPENDED`)을 받는다(`core/security.py`).

### 5.4 로그인 흐름

```
① 앱: 카카오/Apple/구글 SDK로 로그인 → 제공자 토큰 획득
② 앱 → POST /v1/auth/social { provider, token, authorization_code(Apple만), nonce(Apple만) }
③ auth: factory가 제공자에 맞는 SocialProviderPort 구현을 고른다 → verify()
     · 카카오: 카카오 API에 토큰으로 사용자 조회
     · Apple: ID 토큰 서명을 Apple 공개키로 검증 (대상 앱 ID와 nonce 확인),
              인가 코드를 Apple 리프레시 토큰으로 교환해 암호화 저장
     · 구글: ID 토큰 서명을 구글 공개키로 검증 (대상 클라이언트 ID 확인)
④ (provider, provider_user_id)로 유저 조회, 없으면 생성
⑤ 기존 유저면 그 유저 행을 잠그고 신원을 다시 조회한다. 정지된 계정이면 403
     · 잠금을 얻는 사이에 그 수단이 해제·탈퇴로 사라졌으면 조회를 처음부터 한 번 다시 한다.
       해제된 수단은 빈 새 계정이 된다. 두 번째에도 어긋나면 401이다.
     · Apple 리프레시 토큰을 채우는 것도 잠근 뒤에 한다.
⑥ 액세스 + 리프레시 토큰 발급
⑦ 앱: 기기 보안 저장소에 보관. 401이 오면 자동 갱신 후 재시도
⑧ 앱 → GET /v1/me → 소속 매장 0곳: 초대 코드 입력 / 1곳: 바로 입장 / 2곳 이상: 매장 선택
```

`SocialProviderPort`의 메서드는 `verify(credentials) → SocialProfile`과 `revoke(identity)` 두 개다.

제공자 등록을 마치기 전에도 개발이 막히지 않도록 **개발 환경 전용 제공자 `dev`**를 둔다. `APP_ENV=dev`일 때만 factory에 등록되고, 입력한 이름으로 바로 로그인된다. 운영 설정에서는 등록 자체가 되지 않으며, 이 동작을 테스트로 고정한다.

### 5.5 첫 매장 개설과 직원 합류

1. 본인이 앱에 로그인한 뒤 `scripts/grant_operator.py <user_id>`로 플랫폼 운영자가 된다. `user_id`는 `GET /v1/me` 응답에서 확인한다. 여러 번 실행해도 결과가 같다.
2. 운영자가 `POST /v1/platform/shops`를 호출하면 매장이 생기고 **사장용 초대 코드**가 응답으로 돌아온다.
3. Hiss Haus 사장님이 카카오로 로그인하고 그 코드를 입력하면 사장(owner)으로 합류한다.
4. 사장은 앱에서 직원용 초대 코드를 만든다. 직원은 로그인한 뒤 코드를 입력해 직원(staff)으로 합류한다.
5. 사장은 직원의 역할을 바꾸거나 내보낼 수 있다. 내보내면 다음 요청부터 바로 403이다. 초대 생성·내보내기·역할 변경은 매장 행을 잠근 뒤 **행위자 본인의 소속과 역할을 다시 읽는다** — 권한을 확인한 뒤 잠금을 얻는 사이에 내보내지거나 낮춰졌으면 403(`NOT_A_MEMBER`)이다.
6. 사장은 여러 명일 수 있다. 다만 **매장에는 사장이 항상 한 명 이상 있어야 한다.** 마지막 사장은 역할을 낮추거나 내보낼 수 없다.

초대 코드는 사람이 입력할 수 있는 8자리 영숫자(헷갈리는 글자 제외)다. DB에는 해시만 저장하고, 기본 유효 기간은 7일, 기본 사용 횟수는 1회다. 입력 시도는 유저당 분당 5회로 제한한다.

### 5.6 계정 연결과 해제

- 연결·해제 모두 먼저 최근 로그인을 확인한다(5.3). 로그인한 지 300초가 넘은 토큰이나 갱신으로 받은 토큰이면 403(`REAUTH_REQUIRED`)이다.
- `POST /v1/auth/identities { provider, token, … }`: 로그인한 유저에 소셜 신원을 하나 더 붙인다.
- 연결하려는 소셜 계정이 이미 다른 유저에 붙어 있으면 409로 거절한다. 자동 병합은 하지 않으며, "그 계정에서 탈퇴한 뒤 다시 연결해 주세요"라고 안내한다.
- `DELETE /v1/auth/identities/{provider}`: 로그인 수단이 두 개 이상일 때만 허용한다. 마지막 하나는 해제할 수 없다. 해제한 뒤(커밋 뒤) 제공자 쪽 연결도 끊는다(`revoke`). 구글은 서버가 끊지 않고 앱이 `disconnect()`를 부른다.
- `GET /v1/me` 응답에 연결된 로그인 수단 목록을 넣는다.
- 한 유저는 제공자마다 신원을 하나만 가진다. 같은 제공자의 두 번째 계정은 409(`PROVIDER_ALREADY_LINKED`)다.
- 해제하면 모든 세션을 폐기하고, 요청한 기기에만 새 토큰을 응답으로 돌려준다. 해제한 수단으로 만든 세션이 다른 기기에 남지 않게 하려는 것이다.
- 연결·해제는 맨 앞에서 유저 행을 잠그고 탈퇴·정지 여부를 다시 본다(잠금 순서: 유저 → 매장 → 멤버 → 초대). 제공자 쪽 저장된 토큰을 복호화할 수 없으면 그 신원의 연결 끊기만 포기하고 연결·해제·탈퇴는 그대로 진행한다.

### 5.7 회원 탈퇴

`DELETE /v1/auth/account { confirm_close_shops: bool }` (엄격한 불리언 — `"yes"`·`1` 같은 값은 받지 않고 422다)

1. 최근 로그인을 확인한다(5.3). 아니면 403(`REAUTH_REQUIRED`)이다. 그다음 auth가 유저 행을 잠그고 다시 읽는다. 이미 탈퇴했으면 아무것도 하지 않는다.
2. auth가 `MembershipLifecyclePort.apply_withdrawal`을 부른다. tenancy는 매장마다 행을 잠근 뒤 판단한다.
   - **혼자 사장인 매장에 다른 멤버가 있으면** 409(`OWNERSHIP_TRANSFER_REQUIRED`)로 막고 "사장 권한을 먼저 넘겨 주세요"라고 안내한다. 역할 변경으로 다른 멤버를 사장으로 만들면 풀린다.
   - **혼자 사장인 매장에 멤버가 본인뿐이면** `confirm_close_shops`가 참일 때만 진행한다. 아니면 409(`SHOP_CLOSE_CONFIRM_REQUIRED`)다. 진행하면 매장에 `closed_at`을 기록한다.
   - 그 밖에는 소속을 해제하고, 그 멤버가 만든 미사용 초대를 무효화한다.
3. auth가 운영자 지정을 거두고, 유저를 익명화한다. `display_name`은 "탈퇴한 사용자"로 바꾸고, 사진과 전화번호를 지우고, `deleted_at`을 기록한다.
4. 소셜 신원 행을 완전히 삭제한다. 같은 소셜 계정으로 새로 가입할 수 있다.
5. 모든 세션을 폐기한다.
6. 1~4는 요청 하나의 트랜잭션이다. 어디서든 실패하면 전부 되돌아간다. 5(Redis 세대 올리기)는 그 트랜잭션 밖이라 되돌아가지 않는다 — 세션이 한 번 더 끊길 뿐이라 안전한 쪽으로 어긋난다.
7. 커밋이 끝난 뒤 제공자 쪽 연결을 끊는다(`revoke`): Apple은 저장해 둔 리프레시 토큰을 REST API로 폐기하고(App Store 5.1.1(v)), 카카오는 어드민 키로 연결을 끊는다. 구글은 서버에 폐기할 토큰이 없어 앱이 `disconnect()`를 부른다.

DB 변경이 한 트랜잭션이라 중간 상태가 남지 않는다. 같은 유저의 탈퇴가 동시에 두 번 와도 한 번만 처리된다. 제공자 쪽 연결 끊기가 실패해도 탈퇴는 완료하고 실패를 로그로 남긴다. 매장의 업무 기록은 지우지 않으며, 탈퇴한 직원은 "탈퇴한 직원"으로 표시된다.

---

## 6. Flutter 앱 골격

### 6.1 폴더 구조

```
app/
├── lib/
│   ├── main.dart · app.dart
│   ├── core/
│   │   ├── config/        # 환경별 API 주소 (--dart-define으로 주입)
│   │   ├── proxy/         # ApiClient: 토큰 자동 첨부, 401 시 갱신 후 재시도
│   │   ├── storage/       # 기기 보안 저장소 래퍼
│   │   ├── router/        # go_router + 로그인·매장 선택 가드
│   │   └── error/         # 서버 오류 코드 → 사용자 문구
│   ├── design/
│   │   ├── tokens/        # 색·글꼴·간격·모서리·그림자·스프링 값
│   │   ├── bridge/        # 글래스 구현 교체 지점
│   │   └── widgets/       # 기본 위젯 9개
│   ├── features/          # 기능별: screens/ · state/ · api/
│   │   ├── auth/          # 로그인, 초대 코드 입력, 매장 선택
│   │   ├── shop/          # 멤버 목록, 초대, 역할 변경, 매장 정보
│   │   ├── account/       # 계정 연결, 회원 탈퇴
│   │   └── home/          # 탭 셸 (캘린더·고객·매출 자리)
│   └── l10n/
└── test/
```

- 상태 관리는 Riverpod(기능별 `AsyncNotifier`), 라우팅은 go_router, 통신은 dio를 쓴다.
- 앱은 서버 데이터를 보여주는 얇은 클라이언트다. 기능 폴더 안은 화면, 상태, API 클라이언트 세 층만 둔다.
- 서버 응답의 필드명은 변환하지 않는다. 모델은 평범한 클래스에 `fromJson`을 직접 쓰며, 코드 생성기는 도입하지 않는다.
- 화면 코드는 글래스 패키지를 직접 import하지 않고 `design/widgets`만 쓴다.
- 의존 패키지: `flutter_riverpod`, `go_router`, `dio`, `flutter_secure_storage`, `kakao_flutter_sdk_user`, `sign_in_with_apple`, `google_sign_in`, `liquid_glass_widgets`, `flutter_animate`. Rive와 Lottie는 도입하지 않는다.

### 6.2 디자인 방향

확정한 톤은 **무채색 에디토리얼**이다. 기준 목업은 `.superpowers/brainstorm/*/content/mono-tone.html`이다.

- 색: 바탕은 `#f5f5f5`에서 `#ececec`로 이어지는 그라데이션, 글자와 포인트는 `#161616` 한 가지, 보조는 `#8d8d8d`, 선은 `#dcdcdc`다. 색은 사진이 담당한다.
- 글꼴: 본문은 Pretendard다. 큰 숫자와 영문 제목은 고대비 세리프, 한글 제목은 명조다. 목업의 Didot은 안드로이드에 없고 앱에 넣을 수 있는 라이선스도 아니다. 그래서 **Bodoni Moda**(세리프)와 **마루 부리**(명조)를 앱에 포함한다. ③에서 달력 화면을 만들 때 실제 모습을 목업으로 비교해서 최종 확정한다.
- 사진: 흰 테두리의 둥근 사각형이다. 마릿수는 사진 안쪽 우측 하단의 흰 동그라미 숫자로 표시한다.
- 글래스는 떠 있는 조작 계층(탭바, 시트, 카드)에만 쓴다. 스크롤되는 콘텐츠에는 쓰지 않는다. iOS 27의 방향에 맞춰 투명도는 낮게, 테두리는 또렷하게 잡는다.
- 움직임: 고정된 속도 곡선 대신 스프링 물리를 쓴다. 누르는 위젯은 0.96배로 눌렸다가 스프링으로 돌아오고 가벼운 햅틱을 준다.
- 접근성: 시스템의 "동작 줄이기"가 켜져 있으면 스프링을 페이드로 대체한다. "투명도 줄이기"가 켜져 있으면 글래스를 불투명한 면으로 대체한다.
- iOS와 안드로이드에 같은 룩을 적용한다. 저사양 안드로이드에서는 글래스를 단순한 반투명 면으로 대체한다.

### 6.3 기본 위젯 9개

| 위젯 | 모습 |
|---|---|
| `AppButton` | 알약 모양 테두리 버튼 ("기록 수정") |
| `AppFab` | 검정 원형 + 버튼 |
| `AppGlassBar` | 하단 3칸 글래스 탭바 (아이콘 + 라벨) |
| `AppGlassCard` | 반투명 카드 (미리보기, 이름 카드) |
| `AppSheet` | 끌어내려 닫는 바텀시트 |
| `AppSegment` | 밑줄이 있는 글자 탭 ("캘린더 · 기록") |
| `AppPhotoTile` | 흰 테두리의 둥근 사진 + 숫자 동그라미 |
| `AppBigDate` | 큰 세리프 숫자 + 기울인 월·요일 |
| `AppChip` | 상태 표시 ("완료") |

글래스를 쓰는 위젯(`AppGlassBar`, `AppGlassCard`, `AppSheet`)은 `design/bridge/`의 추상에 의존한다. 기본 구현은 `liquid_glass_widgets`다. Flutter 공식 Liquid Glass가 나오면 bridge의 구현만 바꾼다.

### 6.4 ①에서 완성되는 화면 흐름

```
시작 → 로그인(카카오·Apple·구글)
     → 소속 없음: 초대 코드 입력 → 홈
     → 소속 1곳: 홈
     → 소속 2곳 이상: 매장 선택 → 홈
홈: 탭 셸 (달력 머리말 AppBigDate + 빈 상태 안내, 글래스 탭바, + 버튼)
설정 → 매장: 멤버 목록, 초대 코드 만들기, 역할 변경, 내보내기, 매장 정보 수정
     → 계정: 연결된 로그인 수단, 연결·해제, 로그아웃, 회원 탈퇴
```

- 마지막으로 고른 매장은 기기에 기억한다.
- 직원에게는 매장 관리 메뉴 중 권한이 없는 항목을 보여주지 않는다. 실제 보안 경계는 서버의 403이다.
- 회원 탈퇴 화면은 결과(되돌릴 수 없음, 매장 기록은 남음)를 설명한다. 혼자 사장인 매장이 있으면 "매장도 함께 닫힙니다"를 따로 확인받는다.
- Apple 로그인 버튼은 설정값으로 켜고 끈다. Apple Developer Program에 가입하기 전에는 꺼 둔다.

---

## 7. 오류 처리

- 서버 오류 응답은 `{ "code": "INVITE_EXPIRED", "message": "…" }` 형태로 통일한다. 앱은 `code`를 보고 `core/error/`에서 한국어 문구로 바꾼다.
- 주요 코드: `UNAUTHENTICATED`(401), `LAST_OWNER`·`ALREADY_A_MEMBER`(409), `NOT_A_MEMBER`·`PERMISSION_DENIED`·`ACCOUNT_SUSPENDED`·`REAUTH_REQUIRED`·`SHOP_CLOSED`·`SHOP_SUSPENDED`(403), `MEMBER_NOT_FOUND`·`IDENTITY_NOT_FOUND`(404), `INVITE_INVALID`·`INVITE_EXPIRED`·`INVITE_EXHAUSTED`(400), `IDENTITY_ALREADY_LINKED`·`PROVIDER_ALREADY_LINKED`·`LAST_IDENTITY`·`OWNERSHIP_TRANSFER_REQUIRED`·`SHOP_CLOSE_CONFIRM_REQUIRED`(409), `TOO_MANY_ATTEMPTS`(429), `PROVIDER_VERIFICATION_FAILED`(401).
- 도메인 규칙 위반은 도메인 예외로 던지고, 라우터 계층의 예외 핸들러 한 곳에서 HTTP 응답으로 바꾼다. 유스케이스는 HTTP를 모른다.
- 앱은 리프레시에 실패하면 저장된 토큰을 지우고 로그인 화면으로 보낸다. 네트워크 오류는 다시 시도 버튼이 있는 안내로 보여준다.
- 일어날 수 없는 상황에 대한 방어 코드는 넣지 않는다.

---

## 8. 테스트와 검증

### 8.1 백엔드

| 종류 | 대상 | 방법 |
|---|---|---|
| 유스케이스 단위 테스트 | 슬라이스마다 `test_<이름>_interactor.py` 1개 | 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다. |
| 도메인 테스트 | 초대 코드 만료·횟수, 리프레시 토큰 재사용 감지, 탈퇴 규칙(혼자 사장), 마지막 사장 보호, 마지막 로그인 수단 해제 금지 | 순수 파이썬 |
| 어댑터 통합 테스트 | PG 리포지토리, Redis 토큰 저장소 | compose의 실제 Postgres·Redis에 붙는다. 마커 `integration` |
| 소셜 제공자 어댑터 | 서명 검증, 대상 앱 ID·nonce 확인 | 테스트용으로 만든 키로 서명한 토큰과 가짜 공개키 목록으로 검증한다. 실제 제공자 호출은 마커 `network`로 분리하고 기본 검증에서 뺀다. |
| API 테스트 | 표면별 인증 | 토큰 없음 401, 소속 아님 403, 권한 없는 직원 403, 내보낸 직원 즉시 403 |
| **테넌트 격리 테스트** | tenancy | "A매장 멤버가 B매장의 멤버 목록·초대·설정을 요청하면 403". 이후 스포크마다 같은 형태의 테스트를 하나씩 추가한다. |
| 구조 검증 | 전체 | `lint-imports` 5종 계약 |
| 라우트 표 | 전체 | `scripts/print_routes.py`로 라우트 표를 출력해서 변경 전후를 비교한다. |

`pytest.ini`는 `asyncio_mode = auto`로 두고 마커 `integration`, `network`를 등록한다.

### 8.2 Flutter

| 종류 | 대상 |
|---|---|
| 위젯 테스트 | 로그인 후 분기(소속 0곳·1곳·2곳 이상), 초대 코드 오류 표시, 권한에 따른 메뉴 노출, 탈퇴 확인 흐름 |
| ApiClient 테스트 | 401 → 갱신 → 재시도 성공, 갱신 실패 → 로그아웃. 가짜 어댑터로 검증한다. |
| 골든 테스트 | 기본 위젯 9개. 글래스 위젯은 "투명도 줄이기" 대체 모습도 찍는다. |
| 정적 분석 | `flutter analyze` 경고 0 |

### 8.3 사용자가 미리 준비해야 하는 것

실제 소셜 로그인을 돌려 보려면 제공자 쪽 등록이 필요하다. 이 작업은 사용자만 할 수 있다.

| 항목 | 비용 | 없으면 |
|---|---|---|
| Kakao Developers 앱 등록 (네이티브 앱 키, REST 키, 어드민 키) | 무료 | 카카오 로그인 실기기 확인 불가 |
| Google Cloud OAuth 클라이언트 (iOS, Android) | 무료 | 구글 로그인 확인 불가 |
| Apple Developer Program 가입 | 연 약 13만원 | Apple 로그인 확인 불가. 어댑터는 단위 테스트까지만 하고 버튼은 꺼 둔다. iOS 실기기 설치도 제한된다. |

등록을 마치기 전에는 5.4절의 개발 환경 전용 제공자 `dev`로 개발과 흐름 확인을 진행한다.

### 8.4 완료 기준

1. `docker compose up -d` 한 번으로 전체가 뜨고, `/v1/auth/myself`, `/v1/shops/myself`, `/v1/platform/myself`가 응답한다.
2. `pytest`가 전부 통과하고 `lint-imports` 5종이 통과한다.
3. 시뮬레이터에서 다음 흐름이 끝까지 된다: 로그인 → 운영자 지정 스크립트 → 매장 개설 → 사장용 초대 코드로 합류 → 직원용 초대 코드 발급 → 다른 계정이 직원으로 합류 → 역할 변경 → 내보내기 → 내보낸 계정은 즉시 접근 불가.
4. 계정 연결·해제, 직원의 탈퇴, 혼자 사장인 계정의 탈퇴(매장 닫기 확인 포함)가 동작한다.
5. 테넌트 격리 테스트가 통과한다.
6. 기본 위젯 9개의 골든 테스트가 통과하고, 홈 셸이 기준 목업의 톤과 맞는다.
7. `flutter analyze` 경고가 0이다.
8. 문서가 있다: `CLAUDE.md`, `_docs/architecture.md`(GoF 대응표와 이벤트 도입 계획 포함), `_docs/harness.md`, 앱별 `_docs/CLAUDE.md`와 심볼릭 링크, `.env.example`.

---

## 9. 이후 서브 프로젝트로 넘기는 결정

①의 구조에 영향을 주었거나 나중에 잊으면 안 되는 결정이다.

- **데이터 모델**: 고객(사람)이 기본이고 반려동물은 선택적인 하위 대상이다. 방문은 반려동물 없이도 성립한다. 고객을 등록할 때 마케팅 수신 동의 필드를 처음부터 둔다(②).
- **방문 애그리거트**: 예약 → 미용 중 → 완료 → 알림장 발송됨은 하나의 애그리거트다. 예약, 기록, 알림장을 별개 스포크로 쪼개지 않는다. 상태 전이는 `visit/domain/state/`에 둔다(③, ④).
- **스포크 구성**: `customer`, `visit`, `media`, `notification`, `search`, `analytics`를 차례로 추가한다.
- **도메인 이벤트**: ④에서 허브에 발행 포트를 도입한다. 처음에는 같은 프로세스 안의 단순한 구현으로 시작하고, 신뢰성이 필요해지면 아웃박스 방식으로 어댑터만 바꾼다.
- **미디어**: AWS S3 서울 리전, S3 호환 포트, presigned URL 직접 업로드, 키는 `shops/{shop_id}/…` 접두사. 사진은 긴 변 약 3000px, 영상은 1080p. 1년이 지난 영상은 저가 스토리지로 옮기는 수명주기 정책을 둔다(④).
- **알림장**: 방문 1회가 알림장 1장이고 1회용 웹 링크 1개다. 내부 메모와 알림장 내용을 분리한다. 웹 페이지는 Vercel에 올리며, 카카오톡 링크 미리보기를 위해 서버 렌더링 방식을 검토한다. 나중에 도메인을 바꿔도 옛 링크가 열리도록 기존 주소에서 넘겨준다(⑤).
- **사용량 기록**: 알림 발송 건수와 저장 용량을 매장별로 기록한다. 과금 모델은 나중에 정한다(⑥).
- **주의 고객 정보는 매장 안에서만 보인다.** 매장 사이에 공유하지 않는다(③).
- **개인정보 마스킹**: 외부 LLM에 보내기 전에 전화번호와 이름을 가린다. LLM 포트를 감싸는 Decorator로 만든다(⑨).
- **스토어 제출 전 필수**: 앱 패키지 ID 확정, 개인정보 처리방침과 이용약관, 매장과의 개인정보 처리위탁 조항.
- **CallGuard에서 가져오는 것은 패턴뿐이다.** 팀 프로젝트의 코드는 복사하지 않고 새로 작성한다.
