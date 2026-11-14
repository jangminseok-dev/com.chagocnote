from __future__ import annotations

from search.app.dtos.search_myself_dto import SearchMyselfQuery, SearchMyselfResponse
from search.app.ports.input.search_myself_use_case import SearchMyselfUseCase
from search.app.ports.output.search_myself_record_port import SearchMyselfRecordPort


class SearchMyselfInteractor(SearchMyselfUseCase):
    def __init__(self, record: SearchMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: SearchMyselfQuery) -> SearchMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return SearchMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장이 적어 둔 글을 글자와 뜻으로 찾습니다. 경로는 GET /v1/shops/{shop_id}/search?q=&pet_id= 하나이고 "
                "매 요청마다 매장 소속을 확인합니다(사장·직원 모두, 새 권한 없음). 찾는 글은 여섯 종류입니다 — 방문 기록의 "
                "케어 노트(care_note)와 내부 메모(internal_note), 예약 메모(visit_memo), 반려동물 특이사항(pet_memo), "
                "지병(condition_note — 이름과 메모), 보호자 메모(customer_memo). 주의 고객 사유는 찾지 않습니다. "
                "q 는 앞뒤 공백을 떼고 2~100자여야 합니다(아니면 422 VALIDATION_ERROR). pet_id 를 주면 그 아이의 글과 "
                "그 아이 보호자의 메모 안에서만 찾고, 이 매장의 아이가 아니면 빈 결과입니다. "
                "응답은 {items, semantic} 입니다. items 는 가까운 순으로 최대 30줄이고 한 줄은 kind, owner{customer_id, "
                "name}, pet{pet_id, name, photo} 또는 null, visit_id 또는 null, open_pet_id 또는 null, date 또는 null, "
                "snippet(걸린 자리 앞뒤 80자) 입니다. visit_id 가 있으면 방문 상세로, 없으면 open_pet_id 의 반려동물 "
                "상세로 갑니다. 같은 방문의 글이 여럿 걸리면 한 줄만 나옵니다. semantic 은 뜻 검색이 함께 됐는지입니다 — "
                "임베딩 프로세스가 응답하지 않으면 false 이고 글자 일치만으로 답합니다(오류가 아닙니다). "
                "글을 저장하면 색인기가 잠시 뒤(보통 몇 초) 반영합니다. 기록·반려동물을 지우면 검색에서도 사라지고, 고객을 "
                "익명화하면 그 요청 안에서 곧바로 사라집니다. 다른 매장의 글은 섞이지 않습니다. 문장을 지어내지 않고 "
                "매장 데이터를 밖으로 보내지 않습니다. 검색어와 걸린 문장은 로그에 남기지 않습니다."
            ),
        )
