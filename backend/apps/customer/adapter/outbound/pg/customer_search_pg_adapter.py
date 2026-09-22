from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime

from sqlalchemy import delete, exists, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from customer.adapter.outbound.orm.customer_orm import CustomerOrm, CustomerSearchEntryOrm, PetOrm
from customer.app.dtos.customer_search_dto import SearchPage, SearchRequest, SortKey
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.domain.errors import CustomerInputError
from customer.domain.services.search_terms import SearchWord, build_search_entry
from hub.app.dtos.shop_context import ShopContext

Entry = CustomerSearchEntryOrm


def _like_escape(value: str) -> str:
    """LIKE 의 특수 문자(\\, %, _)를 글자 그대로 찾게 한다. 이스케이프 문자는 역슬래시다."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _encode_cursor(sort: SortKey, key: str, customer_id: int) -> str:
    raw = json.dumps([sort, key, customer_id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str, sort: SortKey) -> tuple[str | datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        cursor_sort, key, customer_id = json.loads(raw)
        if (
            cursor_sort != sort
            or not isinstance(key, str)
            or "\x00" in key
            or type(customer_id) is not int
            or not (1 <= customer_id <= 2**63 - 1)
        ):
            raise ValueError
        return (datetime.fromisoformat(key) if sort == "recent" else key), customer_id
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
        raise CustomerInputError("목록 위치(cursor)가 올바르지 않습니다.") from None


class CustomerSearchPgAdapter(CustomerSearchPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def rebuild_search_entry(self, ctx: ShopContext, customer_id: int) -> None:
        customer = (
            await self._session.execute(
                select(CustomerOrm)
                .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if customer is None or customer.deleted_at is not None:
            await self._session.execute(
                delete(Entry).where(Entry.customer_id == customer_id, Entry.shop_id == ctx.shop_id)
            )
            return
        pets = (
            await self._session.execute(
                select(PetOrm.name, PetOrm.updated_at)
                .where(PetOrm.customer_id == customer_id)
                .order_by(PetOrm.id)
            )
        ).all()
        built = build_search_entry(customer.name, customer.phone, [name for name, _ in pets])
        values = dict(
            shop_id=ctx.shop_id,
            terms=built.terms,
            phone_last4=built.phone_last4,
            sort_name=built.sort_name,
            # 원본의 마지막 변경 시각. 반려동물을 지운 것은 활동으로 치지 않는다.
            last_activity_at=max([customer.updated_at, *(updated for _, updated in pets)]),
        )
        stmt = insert(Entry).values(customer_id=customer_id, **values)
        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=[Entry.customer_id], set_=values)
        )

    def _matching(self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool):
        """검색어의 모든 낱말에 걸리는 이 매장의 가족. 기본은 살아 있는 반려동물이 한 마리라도 있는 가족만."""
        conditions = [Entry.shop_id == ctx.shop_id]
        for word in words:
            pattern = _like_escape(word.value)
            if word.kind == "last4":
                conditions.append(Entry.phone_last4.like(pattern + "%", escape="\\"))
            else:
                conditions.append(Entry.terms.ilike("%" + pattern + "%", escape="\\"))
        if not include_passed:
            live = aliased(PetOrm)   # 반려동물 수를 셀 때 바깥 쿼리의 pets 와 섞이지 않게 따로 부른다
            conditions.append(
                exists().where(live.customer_id == Entry.customer_id, live.passed_away_at.is_(None))
            )
        return conditions

    async def search(self, ctx: ShopContext, request: SearchRequest) -> SearchPage:
        key_column = Entry.last_activity_at if request.sort == "recent" else Entry.sort_name
        stmt = select(Entry.customer_id, key_column).where(
            *self._matching(ctx, request.words, request.include_passed)
        )
        if request.cursor is not None:
            key, after_id = _decode_cursor(request.cursor, request.sort)
            position, after = tuple_(key_column, Entry.customer_id), tuple_(key, after_id)
            stmt = stmt.where(position < after if request.sort == "recent" else position > after)
        if request.sort == "recent":
            stmt = stmt.order_by(key_column.desc(), Entry.customer_id.desc())
        else:
            stmt = stmt.order_by(key_column, Entry.customer_id)
        rows = (await self._session.execute(stmt.limit(request.limit + 1))).all()

        page = rows[: request.limit]
        next_cursor = None
        if len(rows) > request.limit:
            last_id, last_key = page[-1]
            key_text = last_key.isoformat() if request.sort == "recent" else last_key
            next_cursor = _encode_cursor(request.sort, key_text, last_id)
        return SearchPage(customer_ids=[customer_id for customer_id, _ in page], next_cursor=next_cursor)

    async def count_pets(
        self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool
    ) -> int:
        stmt = (
            select(func.count(PetOrm.id))
            .join(Entry, Entry.customer_id == PetOrm.customer_id)
            .where(*self._matching(ctx, words, include_passed))
        )
        if not include_passed:
            stmt = stmt.where(PetOrm.passed_away_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one()
