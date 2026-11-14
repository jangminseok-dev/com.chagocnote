from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from search.app.dtos.search_records_dto import SearchItemView, SearchRecordsQuery, SearchResultView
from search.app.ports.input.search_records_use_case import SearchRecordsUseCase
from search.app.ports.output.embedding_port import QUERY_TIMEOUT, EmbeddingPort
from search.app.ports.output.search_candidate_repository import SearchCandidateRepository
from search.domain.entities.search_document import Candidate, PetScope
from search.domain.services.rank_fusion import RESULT_LIMIT, collapse_visits, fuse
from search.domain.services.search_query import clean_query, like_pattern
from search.domain.services.snippet import snippet


class SearchRecordsInteractor(SearchRecordsUseCase):
    """매장이 적어 둔 글을 글자와 뜻으로 찾는다(⑨ 설계 3.7). 문장을 지어내지 않는다 — 찾아 줄 뿐이다.

    임베딩을 못 받으면 글자 후보만으로 답한다(오류가 아니다). 이름·사진은 저장하지 않고 허브 포트로 읽어 붙인다 —
    줄 수와 상관없이 한 번씩. 검색어·걸린 문장을 로그에 남기지 않는다(이 클래스는 아무것도 찍지 않는다).
    """

    def __init__(
        self, candidates: SearchCandidateRepository, embedder: EmbeddingPort, directory: CustomerDirectoryPort,
        ledger: VisitLedgerPort, library: MediaLibraryPort,
    ) -> None:
        self._candidates = candidates
        self._embedder = embedder
        self._directory = directory
        self._ledger = ledger
        self._library = library

    async def search_records(self, query: SearchRecordsQuery) -> SearchResultView:
        ctx, q = query.ctx, clean_query(query.q)
        scope = None
        if query.pet_id is not None:
            pet = (await self._directory.briefs(ctx, [], [query.pet_id])).pets.get(query.pet_id)
            if pet is None:   # 이 매장의 아이가 아니다 — 있는지 없는지도 알려 주지 않는다
                return SearchResultView(items=[], semantic=False)
            scope = PetScope(pet_id=pet.pet_id, customer_id=pet.customer_id)

        embedded = await self._embedder.embed("query", [q], QUERY_TIMEOUT)
        lexical = await self._candidates.lexical(ctx, q, like_pattern(q), scope)
        semantic = await self._candidates.semantic(ctx, embedded.vectors[0], scope) if embedded is not None else []
        found = {c.id: c for c in (*lexical, *semantic)}
        ranked = collapse_visits([found[i] for i in fuse([c.id for c in lexical], [c.id for c in semantic])])
        return SearchResultView(
            items=await self._describe(ctx, ranked[:RESULT_LIMIT], q), semantic=embedded is not None)

    async def _describe(self, ctx, ranked: list[Candidate], q: str) -> list[SearchItemView]:
        if not ranked:
            return []
        customer_ids = sorted({c.customer_id for c in ranked})
        pet_ids = sorted({c.pet_id for c in ranked if c.pet_id is not None})
        briefs = await self._directory.briefs(ctx, customer_ids, pet_ids)
        memo_owners = tuple(sorted({c.customer_id for c in ranked if c.kind == "customer_memo"}))
        first_pets = await self._directory.first_pets(ctx, memo_owners) if memo_owners else {}
        covers = await self._ledger.latest_covers(ctx, pet_ids) if pet_ids else {}
        urls = await self._library.read_urls(ctx, sorted(set(covers.values()))) if covers else {}

        items = []
        for c in ranked:
            owner = briefs.customers.get(c.customer_id)
            pet = briefs.pets.get(c.pet_id) if c.pet_id is not None else None
            # 익명화·삭제가 색인기보다 먼저 닿은 짧은 틈 — 이름 없는 줄은 보이지 않는다.
            if owner is None or owner.name is None or (c.pet_id is not None and (pet is None or pet.name is None)):
                continue
            cover = urls.get(covers.get(c.pet_id)) if c.pet_id is not None else None
            if c.visit_id is not None:
                open_pet_id = None
            elif c.kind == "customer_memo":
                open_pet_id = first_pets.get(c.customer_id)
            else:
                open_pet_id = c.pet_id
            items.append(SearchItemView(
                kind=c.kind, customer_id=c.customer_id, owner_name=owner.name,
                pet_id=c.pet_id, pet_name=pet.name if pet is not None else None,
                photo=cover.thumb_url if cover is not None else None,
                visit_id=c.visit_id, open_pet_id=open_pet_id, date=c.happened_on, snippet=snippet(c.body, q),
            ))
        return items
