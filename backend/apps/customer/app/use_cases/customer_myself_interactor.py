from __future__ import annotations

from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery, CustomerMyselfResponse
from customer.app.ports.input.customer_myself_use_case import CustomerMyselfUseCase
from customer.app.ports.output.customer_myself_record_port import CustomerMyselfRecordPort


class CustomerMyselfInteractor(CustomerMyselfUseCase):
    def __init__(self, record: CustomerMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: CustomerMyselfQuery) -> CustomerMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return CustomerMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장의 고객(보호자)과 반려동물, 반려동물의 질병을 관리합니다. "
                "경로는 모두 /v1/shops/{shop_id} 아래이고 매 요청마다 매장 소속을 확인합니다. "
                "GET /customers 는 가족 카드 목록입니다(q 검색: 전화 뒷자리·보호자 이름·반려동물 이름·한글 초성, "
                "sort=recent|name|last_visit, include_passed, cursor, 한 쪽에 30 가족). "
                "GET /customers/lookup?phone= 는 등록 전 번호 조회, POST /customers 는 보호자와 첫 반려동물 등록, "
                "GET·PUT·DELETE /customers/{customer_id} 는 고객 상세·수정·삭제, "
                "POST /customers/{customer_id}/pets 는 반려동물 추가입니다. "
                "GET·PUT·DELETE /pets/{pet_id} 는 반려동물 상세·수정·삭제, "
                "POST·DELETE /pets/{pet_id}/passed-away 는 무지개다리 표시와 되돌리기, "
                "GET /pet-condition-types 는 정해진 질병 종류입니다. "
                "등록·수정은 customer:write(사장·직원), 고객 삭제는 customer:delete(사장)가 필요합니다. "
                "전화번호는 숫자만 저장하고 매장 안에서 살아 있는 고객끼리 겹치지 않습니다(겹치면 409). "
                "목록과 반려동물 상세의 번호는 가리고, 전체 번호는 고객 상세에서만 줍니다. "
                "고객 삭제는 이름·전화·메모와 반려동물 이름·메모·질병, 미용 기록의 두 메모를 지우는 익명화이고"
                "(사진은 매장의 기록이라 남깁니다), "
                "삭제한 고객은 조회·검색·번호 조회에서 없는 것으로 봅니다. "
                "반려동물은 질병을 하나 이상 고르거나 '질병 없음'을 직접 확인해야 저장됩니다. "
                "고객 상세는 노쇼 횟수와 다가오는 예약(최대 3건)도 줍니다. "
                "목록·고객 상세·반려동물 상세(GET)의 반려동물에는 photo(사진이 붙은 가장 최근 완료 기록의 대표 사진 "
                "썸네일, 없으면 null)가 있습니다. "
                "방문 기록이 있는 반려동물은 지우지 않고(409 PET_HAS_VISITS), 앞으로의 예약이 남은 아이의 "
                "무지개다리와 고객 삭제는 막습니다(409 PET_HAS_UPCOMING_VISITS·CUSTOMER_HAS_UPCOMING_VISITS). "
                "다른 매장의 고객·반려동물 ID 는 404 입니다."
            ),
        )
