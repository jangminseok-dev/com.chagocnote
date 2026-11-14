# search — 기록 검색(⑨): 매장이 적어 둔 글을 글자와 뜻으로 찾는다

소유 데이터: `search_documents`(글 사본·벡터 — (shop_id, kind, source_id) 유일), `search_jobs`(다시 색인할 줄 — (shop_id, scope, ref_id) 유일). **원본은 visit·customer 의 것이다.** 여기 있는 것은 언제든 다시 만들 수 있는 사본이다.

- **다른 스포크를 import 하지 않는다.** 글은 허브 포트 `SearchSourcePort` 로 읽고, 바뀌었다는 사실은 허브 이벤트 `SearchSourceChanged(ctx, scope, ref_id)` 로 듣는다. 이름은 `CustomerDirectoryPort`, 사진은 `VisitLedgerPort.latest_covers` → `MediaLibraryPort.read_urls`.
- **문서 여섯 종류**(`domain/entities/search_document.py` 의 `KINDS`): `care_note`·`internal_note`·`visit_memo`(방문), `pet_memo`·`condition_note`(반려동물), `customer_memo`(보호자). 주의 고객 사유는 색인하지 않는다. 빈 글은 문서가 없다(지병은 이름만으로 문서가 된다).
- **다시 색인하는 단위는 셋**(`SCOPES`): `visit`·`pet`·`customer`. 어느 문서가 어느 대상에 드는지는 `domain/services/targets.py` 한 곳이 정한다 — 지병은 원본 ID 가 지병 행이라 `pet_id` 로 묶인다.
- **구독자는 줄 하나만 쓴다**(`adapter/inbound/observer/source_changed_subscriber.py`). 발행한 쓰기와 같은 세션·같은 트랜잭션이다 — 원본을 읽지도 임베딩을 부르지도 않는다. 같은 대상의 줄은 하나이고 다시 바뀌면 `generation` 이 오른다.
- **글 사본을 갖는 까닭**: 글자 검색(trigram)과 걸린 문장 보이기를 스포크 경계를 넘지 않고 한 질의로 끝낸다. 대가는 개인 글이 한 벌 더 있다는 것 — 그래서 **지우는 길이 세 겹**이다: ① 이벤트 → 줄 → 색인기가 빈 목록을 읽고 지움 ② 고객 익명화는 그 트랜잭션 안에서 `SearchIndexPort.forget_customer`(구현 `forget_customer_interactor.py`)로 곧바로 ③ `scripts/reindex_search.py`.
- **`ShopContext` 를 받지 않는 메서드는 `ReindexQueueRepository` 의 `claim_due`·`finish`·`retry_later` 뿐이다**(색인기의 전 매장 질의 — `NotificationQueueRepository` 와 같은 예외). 문서 저장소는 전부 `ShopContext` 가 첫 인자이고 `shop_id` 로 거른다.
- **검색어·걸린 문장·글·벡터를 로그·오류 메시지·예외 문자열에 남기지 않는다.** 로그는 shop_id·scope·ref_id·건수·걸린 시간·예외의 형 이름뿐이다.
- 잠금 순서의 끝이다 — 고객 행 → **검색 표**.
- **색인기**(`app/services/indexer.py`)는 기동 때 프로세스에 하나 도는 asyncio 작업이다(`dependencies/indexer_provider.py`, `main.py` 의 lifespan). 한 줄의 차례는 **집고 커밋 → 원본(`SearchSourcePort`)과 저장된 문서를 읽고 커밋 → 바뀐 글만 임베딩(트랜잭션·잠금 없이) → `lock_family` 로 고객 행을 잠그고 원본을 다시 읽어 같을 때만 갈아 끼움 → 줄을 지우거나 미룸 → 커밋**. 2초마다 또는 깨우면(`app/services/indexer_wakeup.wake` — 구독자와 `forget_customer` 가 부른다) 0.5초 뒤 돌고, 한 묶음(20)이 가득 집히면 기다리지 않고 이어 돈다. 테스트는 `build_indexer(session, embedder=…, now=…).run_once()`.
- **줄(`search_jobs`)**: 집으면 60초 뒤로 민다(집은 채 죽어도 다시 집힌다). 끝내기·미루기는 **집었을 때의 `generation` 그대로일 때만** 듣는다 — 처리하는 사이의 변경이 사라지지 않는다. 미루기는 30초에서 두 배씩, 한 시간에서 멈춘다(끝없이). 다시 바뀌면 시도 횟수가 0 으로 돌아간다.
- **임베딩**: 포트 `EmbeddingPort.embed(kind, texts, timeout)` 는 **던지지 않고** 못 받으면 `None` 이다(`adapter/outbound/gateways/embed_http_gateway.py` — 시간 초과·연결 실패·오류 상태·모양·차원·개수·다른 모델). 색인기는 `None` 이면 글만 넣고 줄을 남기고, 검색은 글자만으로 답한다(`semantic: false`). 지금 모델의 이름은 `domain/services/embedding_model.py` 의 `CURRENT_MODEL` — 임베딩 프로세스(`embed/encoder.py`)의 이름과 같아야 한다. `EMBED_BASE_URL` 이 비면 뜻 검색 없이 돈다.
- **검색**(`GET /v1/shops/{shop_id}/search?q=&pet_id=`, 매장 멤버, 새 권한 없음): 검색어는 다듬어 2~100자(`domain/services/search_query.py`, 아니면 422 `VALIDATION_ERROR` — 메시지에 검색어 없음). 글자 후보(그대로 든 글 먼저, 그다음 trigram `word_similarity` ≥ 0.3, 50개)와 뜻 후보(지금 모델의 벡터, 유사도 ≥ 0.80 이고 **가장 가까운 글에서 0.04 안쪽**, 10개)를 RRF(k=60)로 합쳐 같은 방문을 한 줄로 접고 30줄. 기준값은 `domain/services/rank_fusion.py` 한 곳이고 근거는 `_docs/decisions/013-record-search.md` 다 — 바꾸면 `scripts/check_search_quality.py` 로 다시 잰다(실제 모델, 기준 24/30 과 여럿 재현 12/18).
- **결과 줄의 이름·사진은 저장하지 않는다** — 읽을 때 허브 포트로 붙인다(`briefs` 한 번, 보호자 메모가 있을 때 `first_pets` 한 번, `latest_covers` → `read_urls` 한 번씩; 줄 수와 상관없다). 익명화·삭제가 색인기보다 먼저 닿은 틈에 걸린 줄은 뺀다. 응답 스키마는 칸을 하나하나 적고 글 전체가 아니라 걸린 토막(80자)만 싣는다.
- 이 매장에 없는 아이(`pet_id`)로 좁히면 빈 결과다(404 가 아니다).
- **뜻 검색은 맞는 글이 없어도 가까운 글 몇 개(최대 10)를 준다** — 이 모델의 점수로는 "관계없음"을 가를 수 없다(결정 기록 013). 테스트에서 "검색에서 사라졌다"는 줄 수가 아니라 그 글이 없는지로 본다.
