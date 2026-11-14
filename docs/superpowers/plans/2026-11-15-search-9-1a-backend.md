# ⑨-1a 기록 검색 — 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장이 적어 둔 글(케어 노트·내부 메모·예약 메모·특이사항·지병·보호자 메모)을 글자와 뜻으로 찾는 `GET /v1/shops/{shop_id}/search` 를 만든다. 과금 0, 매장 데이터는 밖으로 나가지 않는다.

**Architecture:** 새 스포크 `search` 가 글 사본과 벡터를 `search_documents` 에 갖는다. visit·customer 는 글에 닿는 쓰기마다 허브 이벤트 `SearchSourceChanged` 를 내고, search 의 구독자가 같은 트랜잭션에서 `search_jobs` 에 줄 하나를 넣는다. API 프로세스 안의 색인기(알림 디스패처와 같은 모양)가 줄을 집어 허브 포트 `SearchSourcePort` 로 글을 읽고, 별도 프로세스 `embed`(ONNX, CPU)에서 벡터를 받아 갈아 끼운다. 검색은 trigram 후보와 벡터 후보를 RRF 로 합친다. `embed` 가 죽어도 글자 검색은 된다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 asyncio · Alembic · PostgreSQL 17(pg_trgm · pgvector) · onnxruntime · tokenizers · pytest

**Spec:** `docs/superpowers/specs/2026-11-14-record-search-design.md`. 규칙은 루트 `CLAUDE.md`, `_docs/architecture.md`, `backend/apps/notification/CLAUDE.md`(디스패처의 모양), `backend/apps/visit/CLAUDE.md`, `backend/apps/customer/CLAUDE.md`.

## Global Constraints

- 브랜치 `feat/search-9-1a-backend`. 커밋·주석·테스트 이름은 한국어, 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·병합은 사용자가 말할 때만. 앱·웹은 바꾸지 않는다.
- **과금 0** — 유료 API·유료 서비스·배포 없음. 밖으로 나가는 통신은 `embed` 이미지를 지을 때 공개 저장소에서 모델 파일을 받는 것 하나뿐이고 매장 데이터는 보내지 않는다. 품질 기준에 못 미쳐 유료 모델이 필요해 보이면 **멈추고 사용자에게 묻는다.**
- **검색어·걸린 문장(snippet)·글(body)·벡터를 로그·오류 메시지·예외 문자열·테스트 출력에 남기지 않는다.** 로그는 shop_id·scope·ref_id·건수·걸린 시간·예외의 형 이름뿐.
- 스포크끼리 import 하지 않는다 — `search` 는 허브 포트와 이벤트만 안다. `.importlinter` 의 일곱 군데에 `search` 를 더한다(`tests/test_importlinter_lists_spokes.py` 가 잡는다). 슬라이스 1:1. 매장 범위 저장소 메서드의 첫 인자는 `ShopContext`. 전 매장 질의(줄 집기)는 `ShopContext` 를 받지 않는 별도 포트에 둔다(`NotificationQueueRepository` 와 같은 예외).
- 잠금 순서에 더한다: **고객 행 → 검색 표**. 색인기는 잠금을 쥔 채 `embed` 를 부르지 않는다. 구독자는 외부를 부르지 않는다.
- 가드 없이 `ShopContext` 를 만드는 곳은 늘리지 않는다 — `system_context` 를 `hub/app/dtos/shop_context.py` 로 옮겨 디스패처와 색인기가 함께 쓴다.
- 기준값(고정, 품질 확인으로만 바꾼다): 검색어 2~100자(다듬은 뒤) · 글자 후보 50(`word_similarity` ≥ 0.3) · 뜻 후보 5(유사도 ≥ 0.80 이고 가장 가까운 글에서 0.02 안쪽 — 품질 확인으로 바꾼 값, 처음 계획은 50·0.80, 결정 기록 013) · RRF k=60 · 결과 30 · snippet 80자 · 임베딩 시간 제한 질의 1.5초·색인 10초 · 벡터 384차원 · 색인기 간격 2초·한 번에 20줄 · 재시도 `min(30 × 2^attempts, 3600)`초.
- 새 권한 없음. 읽기는 `get_shop_context`(매장 멤버). 공개·보호자 경로는 건드리지 않는다(`routes_without_login` 의 넷 그대로).
- 마이그레이션은 `0017`. `docker compose down -v` 같은 파괴 명령은 쓰지 않는다 — 스키마는 `alembic upgrade head` 로만 올린다.
- 검증(전부 `infra/` 에서): 단위 `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` · 통합 `… -m integration` · `docker compose run --rm --no-deps backend lint-imports --config .importlinter` · 라우트 표 `docker compose run --rm --no-deps auth python scripts/print_routes.py`. CI 에는 `embed` 가 없다 — 단위·통합 테스트는 가짜 임베딩으로만 돈다.

## Review Focus

1. **매장 경계** — 글자 후보·뜻 후보·`pet_id` 거르기·`forget_customer`·색인기의 지우기 어디에서도 다른 매장의 문서가 읽히거나 지워지지 않는다. 다른 매장의 `pet_id` 를 주면 빈 목록이다. 색인기가 만든 컨텍스트는 그 줄의 `shop_id` 다.
2. **되살아남** — 색인기가 글을 읽은 뒤·임베딩하는 사이에 익명화·삭제·수정이 끼어들면 옛 글이 쓰이지 않는다(고객 행 잠금 뒤 다시 읽어 견줌, 줄의 `generation`). 익명화 트랜잭션이 롤백되면 문서도 그대로 남는다.
3. **임베딩이 없을 때** — `embed` 가 꺼졌거나 느리거나 깨진 응답을 줘도 검색은 200(`semantic: false`), 저장은 성공, 문서는 `embedding` 없이 들어가 글자로 찾아지고, 줄은 남아 나중에 벡터가 채워진다. 차원이 다른 벡터·개수가 안 맞는 응답은 "없음"으로 친다.
4. **새는 글** — 422·500 응답 본문, 색인기·어댑터의 로그, 예외 문자열에 검색어·글이 없다. LIKE 의 `%`·`_`·`\` 는 글자 그대로 찾는다. 검색어의 앞뒤 공백·줄바꿈은 다듬는다.
5. **문서의 끝** — 공백뿐인 글은 문서가 없고, 글을 비우면 문서가 사라지고, 메모 없는 지병은 이름만으로 문서가 되고, 방문 날짜를 옮기면 `happened_on` 이 바뀌고(매장 시간대, 자정 앞뒤), 지병을 빼면 그 문서만 사라진다. 같은 방문의 세 kind 가 함께 걸리면 한 줄이다.

---

### Task 1: 임베딩 프로세스 `embed` — 모델이 실제로 올라가는지부터

**Files:** Create `embed/app.py`, `embed/encoder.py`, `embed/requirements.txt`, `embed/tests/test_encoder.py`, `embed/tests/test_app.py`, `infra/docker/embed.Dockerfile`; Modify `infra/docker-compose.yml`(서비스 `embed` — 포트를 밖에 열지 않는다, `backend` 의 `depends_on` 에 넣지 않는다), `_docs/harness.md`

**Interfaces — Produces:**

```python
# embed/encoder.py — 토치 없이 onnxruntime(CPU) + tokenizers
MODEL_NAME = "intfloat/multilingual-e5-small"; DIMENSIONS = 384; MAX_TOKENS = 512
PREFIX = {"query": "query: ", "passage": "passage: "}
class Encoder:
    def __init__(self, model_dir: str) -> None            # model.onnx + tokenizer.json 을 읽는다
    def encode(self, kind: str, texts: list[str]) -> list[list[float]]
        # 접두어 → 토큰(512 에서 자름) → 추론 → 주의 마스크로 평균 풀링 → L2 정규화. 빈 목록이면 [].
# embed/app.py — FastAPI
GET  /health                      → {"status": "ok", "model": MODEL_NAME}
POST /embed {kind: "query"|"passage", texts: [str]}   → {"model": MODEL_NAME, "vectors": [[float × 384]]}
    # texts 1~64개, 하나는 4000자까지. 벗어나면 422(본문에 입력을 되돌리지 않는다). 추론은 스레드로 넘긴다.
# compose: 서비스 이름 embed, 안쪽 주소 http://embed:8100
```

- 모델 파일은 **이미지를 지을 때** 받는다(`huggingface_hub` 로 `onnx/model.onnx`·`tokenizer.json` 만, `/models/e5-small` 에). 기동 때 인터넷이 필요 없게 `HF_HUB_OFFLINE=1`.
- 그 저장소에 ONNX 파일이 없으면 `Xenova/multilingual-e5-small` 의 것으로, 그것도 안 되면 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`(384차원, 접두어 없음 — `PREFIX` 를 빈 글로)로 바꾸고 `Ruling:` 으로 적는다. 어느 쪽이든 유료가 아니다.
- 접근 로그를 끈다(`--no-access-log`). 로그는 건수와 걸린 시간(ms)뿐.
- 테스트는 `embed` 컨테이너 안에서 돈다: `docker compose run --rm --no-deps embed pytest -q`.

- [ ] 테스트 먼저(`test_encoder.py`: 벡터 384칸·길이 1, 같은 글은 같은 벡터, 빈 목록, 아주 긴 글도 됨, **뜻 확인 — `query: 귀 만지는 걸 싫어하던 아이` 가 `passage: 귀 청소할 때 예민하게 반응해요` 와 `passage: 다음 달에 가위컷으로 예약 원하심` 가운데 앞의 것에 더 가깝다**; `test_app.py`: 200 의 모양, `kind` 가 다른 값·`texts` 0개·65개면 422 이고 본문에 입력이 없다, 로그에 글이 없다) → 실패 확인(`Encoder` 없음) → 구현 → `docker compose build embed && docker compose run --rm --no-deps embed pytest -q` 통과 → `docker compose up -d embed` 뒤 `docker compose exec backend python -c "import httpx; print(httpx.get('http://embed:8100/health').json())"` 가 `{'status': 'ok', 'model': …}`. 커밋 `feat(embed): 임베딩 프로세스 — e5-small ONNX, 안쪽 HTTP 하나`.

### Task 2: 허브 — 이벤트 넓히기, 포트 둘, `system_context` 옮기기

**Files:** Create `hub/app/dtos/search_events.py`, `hub/app/dtos/search_source.py`, `hub/app/ports/search_source_port.py`, `hub/app/ports/search_index_port.py`; Modify `hub/app/ports/domain_event_port.py`, `core/observer/in_process_event_bus.py`, `hub/app/dtos/shop_context.py`, `hub/app/ports/customer_directory_port.py`(+ customer 의 구현·가짜), `main.py`(`subscribe(handle_visit_event, VisitEvent)`), `notification` 의 `system_context` 를 쓰는 곳 전부(`dispatcher.py`, `scripts/reregister_templates.py`, 테스트) ; Delete `notification/app/services/system_context.py`; Test `tests/test_in_process_event_bus.py`, `customer/tests/app/test_customer_directory_interactor.py`(이름은 있는 파일을 따른다)

**Interfaces — Produces:**

```python
# hub/app/dtos/search_events.py
SEARCH_SCOPES = ("visit", "pet", "customer")
@dataclass(frozen=True)
class SearchSourceChanged:
    ctx: ShopContext; scope: str; ref_id: int          # scope 는 SEARCH_SCOPES 가운데 하나
# hub/app/dtos/search_source.py
@dataclass(frozen=True)
class SourceDocument:
    kind: str            # care_note · internal_note · visit_memo · pet_memo · condition_note · customer_memo
    source_id: int; customer_id: int; pet_id: int | None; visit_id: int | None
    happened_on: date | None; body: str
# hub/app/ports/search_source_port.py — 구현: visit(scope "visit"), customer(scope "pet"·"customer")
class SearchSourcePort(ABC):
    async def documents(self, ctx: ShopContext, scope: str, ref_id: int) -> list[SourceDocument]
        # 지금의 문서 전부. 없거나 지워졌거나 익명화됐거나 다른 매장이면 []. 잠그지 않는다. 글을 로그에 남기지 않는다.
# hub/app/ports/search_index_port.py — 구현: search. 사용: customer(익명화)
class SearchIndexPort(ABC):
    async def forget_customer(self, ctx: ShopContext, customer_id: int) -> None
        # 그 고객의 문서를 kind 와 상관없이 전부 지우고 다시 맞출 줄을 하나 넣는다. 부르는 쪽 트랜잭션 안에서.
# hub/app/ports/domain_event_port.py
DomainEvent = VisitEvent | SearchSourceChanged
class DomainEventPort(ABC):
    async def publish(self, event: DomainEvent) -> None
# core/observer/in_process_event_bus.py
def subscribe(handler: Subscriber, event_type: type) -> None      # 같은 (handler, event_type) 는 한 번만
def unsubscribe(handler: Subscriber) -> None
def subscribers() -> tuple[tuple[Subscriber, type], ...]
class InProcessEventBus: publish 는 isinstance(event, event_type) 인 구독자만 부른다
# hub/app/dtos/shop_context.py
def system_context(shop_id: int, timezone: str = "Asia/Seoul") -> ShopContext     # 옮긴 것 — 본문·주석 그대로
# hub/app/ports/customer_directory_port.py
async def first_pets(self, ctx: ShopContext, customer_ids: tuple[int, ...]) -> dict[int, int]
    # {고객 ID: 열 반려동물 ID} — 무지개다리가 아닌 가장 먼저 등록한 아이, 없으면 가장 먼저 등록한 아이(ID 오름차순).
    # 아이가 없거나 익명화했거나 다른 매장의 고객은 빠진다. 한 번의 질의.
```

- `VisitEvent` 를 내도 `SearchSourceChanged` 구독자는 불리지 않고 그 반대도 같다 — 알림 구독자가 새 이벤트마다 질의하지 않는다.
- `tests/test_hub_port_binding.py` 가 `subscribers()` 를 쓰면 새 모양에 맞춘다.

- [ ] 테스트(버스: 형으로 거르기·등록 순서·중복 등록·예외 전파·`unsubscribe`; `first_pets`: 무지개다리만 있는 가족·아이 없는 고객·익명화·다른 매장; `system_context` 의 값) → 실패 확인 → 구현 → 단위 전체·import-linter 통과. 커밋 `refactor(hub): 이벤트 버스가 형으로 거른다, 검색 포트 둘, system_context 를 허브로`.

### Task 3: `search` 스포크 — 표, 줄, 구독자, 잊기

**Files:** Create `backend/apps/search/`(`__init__.py`, `CLAUDE.md`, `domain/…`, `app/…`, `adapter/…`, `dependencies/…`, `tests/…`), `backend/alembic/versions/0017_search.py`, `search/adapter/outbound/orm/search_orm.py`, `search/adapter/outbound/pg/search_document_pg_repository.py`·`search_job_pg_repository.py`, `search/adapter/inbound/observer/source_changed_subscriber.py`, `search/app/services/indexer_wakeup.py`(`wake()`·`wait(timeout)` — 알림 디스패처의 것과 같은 모양), `search/app/use_cases/enqueue_reindex_interactor.py`·`forget_customer_interactor.py`(+ dto·input port·provider), `search/tests/helpers/fakes.py`; Modify `backend/.importlinter`, `backend/orm_registry.py`, `backend/requirements.in`·`requirements.txt`(`pgvector` — 파일 머리의 pip-compile 명령으로 다시 만든다), `main.py`(구독), `infra/docker/Dockerfile` 는 그대로(이미지 다시 짓기만); Test `search/tests/domain/…`, `search/tests/app/…`, `tests/integration/test_search_schema.py`, `tests/test_schema_drift.py` 가 통과

**Interfaces — Consumes:** Task 2 의 전부.

**Interfaces — Produces:**

```python
# 0017 — CREATE EXTENSION IF NOT EXISTS vector
# search_documents: id BIGINT PK, shop_id BIGINT, kind VARCHAR(20), source_id BIGINT, customer_id BIGINT,
#   pet_id BIGINT NULL, visit_id BIGINT NULL, happened_on DATE NULL, body TEXT, embedding vector(384) NULL,
#   model VARCHAR(80) NULL, updated_at TIMESTAMPTZ
#   UNIQUE uq_search_documents_source (shop_id, kind, source_id); CHECK kind IN (여섯)
#   INDEX: gin (body gin_trgm_ops), hnsw (embedding vector_cosine_ops), (shop_id, customer_id), (shop_id, pet_id)
# search_jobs: id BIGINT PK, shop_id BIGINT, scope VARCHAR(10), ref_id BIGINT, enqueued_at TIMESTAMPTZ,
#   generation INTEGER DEFAULT 1, attempts INTEGER DEFAULT 0, next_attempt_at TIMESTAMPTZ
#   UNIQUE uq_search_jobs_target (shop_id, scope, ref_id); CHECK scope IN (셋); INDEX (next_attempt_at)
# search/domain/entities/search_document.py
VISIT_KINDS = ("care_note", "internal_note", "visit_memo"); KINDS = VISIT_KINDS + ("pet_memo", "condition_note", "customer_memo")
@dataclass(frozen=True) class SearchDocument: kind, source_id, customer_id, pet_id, visit_id, happened_on, body, embedding: tuple[float, ...] | None, model: str | None
@dataclass(frozen=True) class ReindexJob: id, shop_id, scope, ref_id, generation, attempts
# search/app/ports/output/search_document_repository.py — 매장 범위
class SearchDocumentRepository(ABC):
    async def list_for_target(self, ctx, scope: str, ref_id: int) -> list[SearchDocument]
    async def replace_target(self, ctx, scope: str, ref_id: int, documents: list[SearchDocument], now: datetime) -> None
        # 그 대상의 문서를 documents 로 맞춘다 — 없는 것은 지우고 나머지는 (shop_id, kind, source_id) 로 upsert
    async def delete_for_customer(self, ctx, customer_id: int) -> None
# 대상 → 문서 (저장소가 쓰는 규칙, 도메인 함수 target_filter 로 한 곳에)
#   visit:    kind IN VISIT_KINDS AND source_id = ref_id
#   pet:      (kind = 'pet_memo' AND source_id = ref_id) OR (kind = 'condition_note' AND pet_id = ref_id)
#   customer: kind = 'customer_memo' AND source_id = ref_id
# search/app/ports/output/reindex_queue_repository.py
class ReindexQueueRepository(ABC):
    async def enqueue(self, ctx, scope: str, ref_id: int, now: datetime) -> None
        # INSERT … ON CONFLICT (shop_id, scope, ref_id) DO UPDATE SET generation = generation + 1, next_attempt_at = now
    # 아래는 ShopContext 를 받지 않는다 — 색인기(전 매장)용
    async def claim_due(self, now: datetime, limit: int) -> list[ReindexJob]        # FOR UPDATE SKIP LOCKED, next_attempt_at ≤ now
    async def finish(self, job: ReindexJob) -> None                                 # generation 이 집은 그대로일 때만 DELETE
    async def retry_later(self, job: ReindexJob, now: datetime) -> None             # attempts + 1, next_attempt_at = now + min(30 × 2^attempts, 3600)초
# 슬라이스
EnqueueReindexInteractor.enqueue_reindex(EnqueueReindexCommand(ctx, scope, ref_id))
ForgetCustomerInteractor(SearchIndexPort).forget_customer(ctx, customer_id)   # delete_for_customer + enqueue(ctx, "customer", customer_id)
get_forget_customer_use_case(db) -> SearchIndexPort
# search/adapter/inbound/observer/source_changed_subscriber.py
async def handle_source_changed(session: AsyncSession, event: SearchSourceChanged) -> None   # 줄 하나 + indexer_wakeup.wake()
# main.py
subscribe(handle_source_changed, SearchSourceChanged)
```

- `search/CLAUDE.md` 에 이 스포크의 규칙을 적는다(글 사본을 갖는 까닭, 지우기 세 겹, 로그 금지, 기준값).
- ORM 의 벡터 칸은 `pgvector.sqlalchemy.Vector(384)`. `tests/test_schema_drift.py` 가 확장·색인까지 맞는지 본다(색인 종류를 못 견주면 통합 테스트 `test_search_schema.py` 가 `pg_indexes` 로 확인한다).
- `claim_due` 는 집은 줄의 `next_attempt_at` 을 `now + 60초` 로 밀고 돌려준다 — 색인기는 집은 뒤 커밋해 잠금을 놓고, 죽으면 1분 뒤 다른 색인기가 다시 집는다.

- [ ] 테스트(도메인 `target_filter` 의 세 scope; 가짜 저장소로 `enqueue` 가 같은 대상에 한 줄·`generation` 이 오름, `forget_customer` 가 모든 kind 를 지우고 줄을 넣음·다른 매장 것은 남음; 통합 `test_search_schema.py`: 확장·유일·CHECK·색인, `replace_target` 의 지우기와 upsert, `claim_due` 의 SKIP LOCKED 와 밀기, `finish` 는 `generation` 이 올랐으면 지우지 않음, 버스로 `SearchSourceChanged` 를 내면 줄이 생기고 롤백하면 없다, `forget_customer` 가 부른 쪽 트랜잭션 안에서 지우고 롤백하면 남는다) → 실패 확인 → 구현 → `docker compose build backend` → 단위·통합·import-linter·`test_hub_port_binding`. 커밋 `feat(search): 스포크 뼈대 — 표(0017), 다시 색인할 줄, 구독자, 익명화 때 잊기`.

### Task 4: visit·customer — 글을 내주고, 바뀌었다고 알린다

**Files:** Create `visit/app/use_cases/visit_search_source_interactor.py`, `visit/dependencies/visit_search_source_provider.py`, `visit/app/ports/output/visit_text_repository.py`(+ pg 구현은 `visit_pg_repository.py` 에, 가짜는 helpers 에), `customer/app/use_cases/customer_search_source_interactor.py`, `customer/dependencies/customer_search_source_provider.py`, `customer/app/ports/output/family_text_repository.py`(+ pg·가짜), `visit/domain/services/search_documents.py`, `customer/domain/services/search_documents.py`; Modify 발행하는 인터랙터와 그 프로바이더, `customer/dependencies/hub_ports.py`(`get_domain_events`, `get_search_index`), `main.py`(자리 채우기); Test `tests/integration/test_search_events_wiring.py`, 슬라이스마다 `test_<이름>_interactor.py`, 도메인 `test_search_documents.py`, 기존 인터랙터 테스트에 "이벤트를 낸다" 추가

**Interfaces — Consumes:** Task 2 의 `SearchSourceChanged`·`SourceDocument`·`SearchSourcePort`·`SearchIndexPort`·`DomainEventPort`, Task 3 의 `get_forget_customer_use_case`·`handle_source_changed`.

**Interfaces — Produces:**

```python
# visit/domain/services/search_documents.py — 순수
def visit_documents(visit_id, customer_id, pet_id, happened_on: date, memo, care_note, internal_note) -> list[SourceDocument 의 재료]
    # 글마다 strip, 비면 없음. kind 순서: care_note, internal_note, visit_memo. source_id = visit_id.
# customer/domain/services/search_documents.py — 순수
def condition_body(label: str, note: str | None) -> str      # note 가 비면 label, 아니면 f"{label} — {note}"
def pet_documents(pet_id, customer_id, memo, conditions: [(condition_id, label, note)]) -> list[…]
    # pet_memo(source_id=pet_id) + condition_note(source_id=지병 행 ID, pet_id=pet_id). label 은 기타면 custom_label.
def customer_documents(customer_id, memo) -> list[…]         # customer_memo(source_id=customer_id), pet_id None
# 구현 슬라이스 (HTTP 없음 — 허브 포트가 입력 포트)
VisitSearchSourceInteractor(SearchSourcePort)      # scope "visit" 만. happened_on 은 starts_at 을 ctx.timezone 의 날로.
CustomerSearchSourceInteractor(SearchSourcePort)   # scope "pet"·"customer". 익명화한 고객과 그 아이는 [].
get_visit_search_source_use_case(db) / get_customer_search_source_use_case(db)
```

**발행하는 곳** (쓰기가 끝난 뒤, 같은 트랜잭션 — `SearchSourceChanged(ctx, scope, ref_id)`):

| 인터랙터 | 내는 것 |
|---|---|
| visit `put_visit_record`·`delete_visit_record`·`update_visit` | `visit`, 그 방문 |
| visit `register_visit` | `visit`, 만든 방문마다(메모가 없어도 낸다 — 판단은 색인기가 한다) |
| visit `reschedule_visits` | `visit`, 옮긴 방문마다 |
| customer `register_customer` | `customer` + 만든 아이마다 `pet` |
| customer `update_customer` | `customer` |
| customer `add_pet`·`update_pet`·`delete_pet`·`mark_pet_passed_away`·`unmark_pet_passed_away` | `pet`, 그 아이 |
| customer `delete_customer` | 이벤트 대신 `SearchIndexPort.forget_customer(ctx, customer_id)` — `clear_customer_memos` 다음 줄 |

- 상태 전이(`transition_visits`)·사진 덧붙이기·알림장은 글을 바꾸지 않으므로 내지 않는다. 주의 표시·미용 동의도 내지 않는다(색인 대상이 아니다).
- visit 은 기존 자리 `get_domain_events` 를 쓴다. customer 는 `dependencies/hub_ports.py` 에 자리 둘(`get_domain_events`·`get_search_index`)을 더하고 `main.py` 가 채운다: `app.dependency_overrides[get_customer_domain_events] = get_event_bus`, `app.dependency_overrides[get_customer_search_index] = get_forget_customer_use_case`. `find_route_violations` 가 빈 자리 없음을 본다.

- [ ] 테스트(도메인: 공백뿐·None·세 글 다 있음·지병 이름만·기타 지병·메모 있는 지병; 구현 슬라이스: 다른 scope 는 [], 없는 ID·다른 매장·익명화는 [], 매장 시간대 자정 앞뒤의 `happened_on`; 발행: 표의 인터랙터마다 scope·ref_id, 실패한 쓰기는 내지 않음, 익명화가 `forget_customer` 를 한 번 부름; 통합 `test_search_events_wiring.py`: 실제 `register_customer`·`put_visit_record`·`update_pet` 를 부르면 줄이 생기고 롤백하면 없다, 익명화하면 같은 트랜잭션에서 그 고객의 문서가 전부 사라지고 다른 고객·다른 매장의 문서는 남는다) → 실패 확인 → 구현 → 단위·통합·import-linter. 커밋 `feat(visit,customer): 검색 원본 내주기와 바뀜 알리기`.

### Task 5: 색인기와 임베딩 어댑터, 맞춤 스크립트

**Files:** Create `search/app/ports/output/embedding_port.py`, `search/adapter/outbound/gateways/embed_http_gateway.py`, `search/app/services/indexer.py`, `search/dependencies/indexer_ports.py`·`indexer_provider.py`·`search_wiring.py`, `backend/scripts/reindex_search.py`; Modify `core/config.py`(`EMBED_BASE_URL`), `main.py`(lifespan·`configure_indexer_ports`), `scripts/generate_dev_env.py` 는 건드리지 않는다(기본값으로 돈다); Test `search/tests/app/test_indexer.py`, `search/tests/adapter/test_embed_http_gateway.py`, `tests/test_reindex_search.py`, `tests/integration/test_search_indexer_wiring.py`, `tests/test_app_lifespan.py`

**Interfaces — Consumes:** Task 1 의 `POST /embed`, Task 2 의 `SearchSourcePort`·`system_context`·`CustomerDirectoryPort.lock_family`, Task 3 의 저장소 둘.

**Interfaces — Produces:**

```python
# core/config.py
EMBED_BASE_URL: str = _m.get("EMBED_BASE_URL", "http://embed:8100") or ""     # 빈 값이면 임베딩을 쓰지 않는다
# search/app/ports/output/embedding_port.py
@dataclass(frozen=True) class Embedded: model: str; vectors: tuple[tuple[float, ...], ...]
QUERY_TIMEOUT = 1.5; INDEX_TIMEOUT = 10.0; DIMENSIONS = 384
class EmbeddingPort(ABC):
    async def embed(self, kind: str, texts: list[str], timeout: float) -> Embedded | None
        # 실패(시간 초과·연결 거절·상태 코드·모양 다름·차원 다름·개수 다름)는 전부 None. 던지지 않는다.
# search/app/services/indexer.py
@dataclass(frozen=True) class IndexReport: claimed: int; indexed: int; deferred: int
class Indexer:
    def __init__(self, *, queue, documents, embedder, sources: Mapping[str, SearchSourcePort], shops: ShopProfilePort,
                 directory: CustomerDirectoryPort, commit, rollback, now, batch: int = 20) -> None
    async def run_once(self) -> IndexReport
# search/dependencies/indexer_ports.py
@dataclass(frozen=True) class IndexerPorts: shop_profile; customer_directory; visit_source; customer_source   # 세션을 받는 공장
def configure_indexer_ports(ports: IndexerPorts) -> None; def indexer_ports() -> IndexerPorts
# search/dependencies/indexer_provider.py
def build_indexer(db, *, embedder=None, now=None) -> Indexer; async def run_once() -> IndexReport
def start_indexer() -> tuple[asyncio.Task, asyncio.Event]          # 이름 "search-indexer", 간격 2초, 깨우면 0.5초 뒤
# scripts/reindex_search.py [--shop <id>] [--purge-orphans]
```

**색인기의 한 줄** (이 차례 그대로):

1. `claim_due(now, batch)` → 커밋(잠금을 놓는다).
2. 줄마다: 매장 정보(`public_profile`)가 없으면 그 대상의 문서를 지우고 `finish`. 있으면 `ctx = system_context(shop_id, profile.timezone)`.
3. `docs = sources[scope].documents(ctx, scope, ref_id)`. 비면 `replace_target(ctx, scope, ref_id, [], now)` → `finish` → 커밋.
4. 저장된 문서와 견줘 **글이 같고 벡터가 지금 모델의 것인 문서는 다시 임베딩하지 않는다.** 나머지 글을 `embed("passage", …, INDEX_TIMEOUT)` — 이 사이에는 트랜잭션이 열려 있지 않다.
5. 새 트랜잭션: `directory.lock_family(ctx, customer_id, ())`(`docs[0].customer_id`) — `FamilyNotFoundError` 면 문서를 지우고 `finish`. 통과하면 원본을 **다시 읽어** 3 에서 읽은 것과 같을 때만 `replace_target`. 다르면 쓰지 않고 줄을 그대로 둔다(다음 번에 다시).
6. 임베딩이 None 이었으면 벡터 없이 쓰고 `retry_later`, 아니면 `finish`. 커밋.
7. 한 줄의 예외는 롤백하고 `retry_later` 로 넘긴 뒤 다음 줄로 — 로그는 shop_id·scope·ref_id·예외의 형 이름만.

- `main.py` lifespan: `start_dispatcher()` 옆에서 `start_indexer()`, 끝낼 때 `stop.set()`·`wake()`·`await task`. `configure_indexer_ports` 는 `configure_dispatcher_ports` 옆.
- 어댑터는 `httpx.AsyncClient` 하나를 프로세스에 두고, `EMBED_BASE_URL` 이 비면 늘 None 을 주는 구현을 쓴다. `search/app` 은 `httpx` 를 모른다(프레임워크 격리).
- `reindex_search.py` — 매장(또는 전 매장)의 방문·반려동물·고객을 훑어 줄에 넣는다. 원본을 훑는 것은 스포크의 표를 직접 읽지 않고 **허브 포트로는 할 수 없으므로 스크립트가 진입점으로서 조립한다**(`rebuild_customer_search.py` 가 하는 방식을 따른다 — ID 목록만 읽는다). `--purge-orphans` 는 문서마다 그 대상을 줄에 넣어 색인기가 지우게 한다. 글을 출력하지 않고 건수만 찍는다.

- [ ] 테스트(가짜 임베딩·가짜 원본으로: 문서가 들어감, 글을 비우면 지워짐, 임베딩 None 이면 벡터 없이 들어가고 줄이 남아 `next_attempt_at` 이 밀림, 다음 번에 벡터가 채워짐, 글이 같으면 임베딩을 다시 부르지 않음, 읽은 뒤 원본이 바뀌면 쓰지 않고 줄이 남음, 익명화가 끼어들면 지움, 처리 중 `generation` 이 오르면 줄이 남음, 한 줄이 던져도 다음 줄은 처리, 로그에 글 없음(`caplog`), 어댑터: 시간 초과·500·깨진 JSON·383차원·개수 다름 → None; 통합: 실제 PG 에서 쓰기 → `run_once` → 문서, 두 색인기가 같은 줄을 겹쳐 집지 않음; lifespan 이 색인기를 띄우고 멈춤) → 실패 확인 → 구현 → 단위·통합·import-linter. 커밋 `feat(search): 색인기와 임베딩 어댑터, 맞춤 스크립트`.

### Task 6: 검색 — `GET /v1/shops/{shop_id}/search`

**Files:** Create `search/domain/services/search_query.py`·`snippet.py`·`rank_fusion.py`, 슬라이스 `search_records`(router·schema·dto·input port·interactor·provider)와 `search_myself`(같은 묶음), `search/app/ports/output/search_candidate_repository.py`(+ pg·가짜), `search/dependencies/hub_ports.py`(`get_customer_directory`·`get_visit_ledger`·`get_media_library`), `search/adapter/inbound/api/error_map.py`; Modify `main.py`(라우터 둘·자리 셋·오류 표), `tests/route_inspection.py` 의 프로세스별 목록; Test `search/tests/domain/…`, `search/tests/app/test_search_records_interactor.py`, `search/tests/adapter/test_search_records_router.py`, `tests/integration/test_search_wiring.py`, `tests/test_access_log.py`, `tests/test_http_errors.py`

**Interfaces — Consumes:** Task 2 의 `first_pets`, Task 3 의 표, Task 5 의 `EmbeddingPort`·`QUERY_TIMEOUT`, 기존 `CustomerDirectoryPort.briefs`·`VisitLedgerPort.latest_covers`·`MediaLibraryPort.read_urls`.

**Interfaces — Produces:**

```python
# search/domain/services/search_query.py
Q_MIN = 2; Q_MAX = 100
def clean_query(raw: str) -> str            # 공백류를 빈칸 하나로, strip. 2~100자 아니면 SearchQueryError(code "SEARCH_QUERY_INVALID" → 422)
def like_pattern(q: str) -> str             # \ % _ 를 \ 로 막고 앞뒤에 %
# search/domain/services/snippet.py
SNIPPET_MAX = 80
def snippet(body: str, q: str) -> str       # 줄바꿈을 빈칸으로. 대소문자 없이 q 가 있으면 그 자리가 들게(앞 20자쯤), 없으면 앞에서. 잘린 쪽에 "…"
# search/domain/services/rank_fusion.py
RRF_K = 60; RESULT_LIMIT = 30
def fuse(lexical: list[int], semantic: list[int]) -> list[int]       # 문서 ID 의 순위 목록 둘 → 점수 Σ 1/(60 + 순위) 내림차순, 같으면 lexical 이 앞
def collapse_visits(ranked: list[Candidate]) -> list[Candidate]      # 같은 visit_id 의 VISIT_KINDS 는 가장 앞의 하나만
# search/app/ports/output/search_candidate_repository.py
@dataclass(frozen=True) class Candidate: id, kind, source_id, customer_id, pet_id, visit_id, happened_on, body
class SearchCandidateRepository(ABC):
    async def lexical(self, ctx, q: str, pattern: str, pet_scope: PetScope | None, limit: int = 50) -> list[Candidate]
        # ILIKE 로 든 것 먼저, 그다음 word_similarity(q, body) ≥ 0.3 — 내림차순, 같으면 happened_on 최신·id
    async def semantic(self, ctx, vector: tuple[float, ...], model: str, pet_scope: PetScope | None, limit: int = 50) -> list[Candidate]
        # model 이 같고 embedding 이 있는 것 가운데 1 − (embedding <=> vector) ≥ 0.80, 가까운 순
@dataclass(frozen=True) class PetScope: pet_id: int; customer_id: int   # pet_id = :pet_id OR (kind = 'customer_memo' AND customer_id = :customer_id)
# 경로
GET /v1/shops/{shop_id}/search?q=<str>&pet_id=<int>      → 200 SearchResultSchema, 매장 멤버
GET /v1/shops/{shop_id}/search/myself                     → 제공 경로·다루는 데이터·제약
# 응답 — 칸을 하나하나 적는다
{"items": [{"kind": str, "owner": {"customer_id": int, "name": str}, "pet": {"pet_id": int, "name": str, "photo": str | None} | None,
            "visit_id": int | None, "open_pet_id": int | None, "date": "YYYY-MM-DD" | None, "snippet": str}],
 "semantic": bool}
```

- 차례: `clean_query` → `pet_id` 가 있으면 `briefs(ctx, [], [pet_id])` 로 보호자를 찾아 `PetScope`(이 매장에 없는 아이면 **빈 결과** `{items: [], semantic: false}` — 내 결정) → 글자 후보와 `embed("query", [q], QUERY_TIMEOUT)` 를 **함께** 돌린다(`asyncio.gather` 는 같은 세션을 겹쳐 쓰지 않게 임베딩만 따로 — 임베딩 → 두 질의 순서여도 된다) → `fuse` → `collapse_visits` → 위 30 → 이름·사진 붙이기.
- 붙이기: `briefs` 한 번(걸린 고객·아이 전부), `first_pets` 한 번(`customer_memo` 가 있을 때만), `latest_covers` → `read_urls` 한 번씩. 줄 수와 상관없이 포트 호출 수가 같다. `photo` 는 `thumb_url`.
- 줄을 빼는 경우: 고객 요약이 없거나 이름이 None(익명화), 아이가 있어야 하는 줄인데 아이 요약이 없음.
- `open_pet_id`: 방문 계열은 None, `pet_memo`·`condition_note` 는 그 `pet_id`, `customer_memo` 는 `first_pets` 의 값(없으면 None).
- `date` 는 `happened_on`. `semantic` 은 임베딩을 받았는가.
- `q` 의 길이 검증은 FastAPI 의 `Query(min_length…)` 에 맡기지 않고 `clean_query` 가 한다(다듬은 뒤의 길이). `q` 가 아예 없으면 기존 422(`VALIDATION_ERROR`).

- [ ] 테스트(도메인: 다듬기와 경계 1·2·100·101자, `%`·`_`·`\`, snippet 의 앞·가운데·끝·없음·80자 딱·줄바꿈, RRF 의 순서와 한쪽에만 있는 문서, 접기; 인터랙터(가짜): 임베딩 None 이면 글자만·`semantic: false`, `pet_id` 거르기와 보호자 메모 포함, 다른 매장의 `pet_id` 는 빈 결과, 익명화한 줄 빠짐, `open_pet_id` 세 경우, 포트 호출 수; 라우터: 멤버 아님 403·로그인 없음 401·422 본문에 검색어 없음; 통합(실제 PG·가짜 임베딩으로 정해 둔 벡터): 매장 격리(같은 글을 두 매장에), 글자만 걸림·뜻만 걸림·둘 다, 유사도 0.80 미만은 빠짐, `model` 이 다른 문서는 뜻 후보에 없음, 오타에 가까운 말이 `word_similarity` 로 걸림; `test_access_log`: `/v1/shops/3/search?q=…` 가 가려짐) → 실패 확인 → 구현 → 단위·통합·import-linter·라우트 표. 커밋 `feat(search): 기록 검색 — 글자와 뜻을 합쳐 위 30`.

### Task 7: 품질 확인·흐름 스크립트·문서

**Files:** Create `backend/scripts/check_search_quality.py`, `backend/scripts/search_quality_set.py`(문장 60·질문 30), `backend/scripts/check_search_flow.sh`, `_docs/decisions/013-record-search.md`; Modify 루트 `CLAUDE.md`(스포크 목록의 compose 줄에 `embed`, 가드 없이 `ShopContext` 를 만드는 곳 줄, 잠금 순서 줄, 검색어·글 로그 금지 줄, 명령어에 스크립트 셋), `_docs/architecture.md`(도메인 이벤트 절 — 형으로 거르기와 `SearchSourceChanged`, GoF 표의 `search` 예정 줄은 그대로 두고 색인기는 표에 없음), `_docs/harness.md`, `backend/apps/visit/CLAUDE.md`·`customer/CLAUDE.md`(발행하는 곳), `.github/workflows/backend.yml` 은 **바꾸지 않는다**

**Interfaces — Consumes:** 앞의 전부. 개발 스택(`docker compose up -d`)에 `embed` 가 떠 있어야 한다.

- `check_search_quality.py` — 테스트 DB 가 아니라 **개발 DB 의 새 매장 하나**에 문서 60개를 `search_documents` 로 바로 넣고(임베딩은 실제 `embed`), 질문 30개(글자로 되는 것 15·말을 바꾼 것 15)를 검색 유스케이스로 돌려 정답이 위 5개 안에 드는 수를 찍고 **24개 미만이면 종료 코드 1**. 끝나면 넣은 매장의 문서를 지운다. 문장은 실제 같은 미용 기록(사람 이름·전화번호 없음). 틀린 질문은 번호만 찍는다(글을 찍지 않는다 — 문장은 지어낸 것이지만 버릇을 지킨다).
- 기준에 못 미치면 이 차례로만 고친다: ① 유사도 기준(0.78~0.85)·후보 수 ② `intfloat/multilingual-e5-base`(768차원 — 0017 과 ORM 의 차원을 바꾼다, 아직 배포 전이라 0017 을 고친다) ③ **멈추고 사용자에게 묻는다.** 바꾼 값은 Global Constraints 의 줄과 013 에 적는다.
- `check_search_flow.sh`(게이트웨이 경유, 다른 흐름 스크립트의 모양을 따른다): 매장 둘 준비 → 기록 저장 → 5초 안에 글자로 찾아짐 → 말을 바꿔도 찾아짐(`semantic: true`) → `pet_id` 로 좁힘 → 기록을 지우면 사라짐 → 지병 이름으로 찾아짐 → 익명화하면 **곧바로** 사라짐 → 다른 매장에서는 0건 → `docker compose stop embed` 뒤에도 글자 검색 200·`semantic: false` → `docker compose start embed`. 줄마다 `ok`/`FAIL`, 검색어와 응답 본문은 찍지 않는다.
- 013 에 적는 것: 내가 정한 것(모델·기준값·글 사본·`system_context` 를 허브로·다른 매장의 `pet_id` 는 빈 결과·`first_pets`), 품질 확인 결과(숫자), 받아들인 한계(512토큰 뒤는 글자로만, HNSW 와 매장 거르기, 색인 지연 2초쯤), 남는 것.

- [ ] `docker compose up -d --build` → `alembic upgrade head` 가 0017 까지 → `docker compose run --rm backend python scripts/reindex_search.py` → `docker compose run --rm backend python scripts/check_search_quality.py` 가 `24/30` 이상 → `bash ../backend/scripts/check_search_flow.sh` 전부 `ok` → 단위·통합·import-linter·라우트 표 전부 통과 → 문서. 커밋 `test(search): 품질 확인과 흐름 스크립트. docs: ⑨-1a 규칙, 결정 기록 013`.
