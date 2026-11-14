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
