"""ORM 모듈 등록 목록 — import 하면 모든 테이블이 Base.metadata 에 올라간다.

스포크의 ORM 을 한꺼번에 import 하는 곳은 여기 하나다. alembic/env.py 와 스키마 불일치 테스트가 쓴다.
core 는 스포크를 import 할 수 없어서 core 밖에 둔다. 새 ORM 모듈을 만들면 여기에 한 줄을 더한다.
"""
import auth.adapter.outbound.orm.user_orm  # noqa: F401
import auth.adapter.outbound.orm.operator_orm  # noqa: F401
import tenancy.adapter.outbound.orm.tenancy_orm  # noqa: F401
import customer.adapter.outbound.orm.customer_orm  # noqa: F401
import visit.adapter.outbound.orm.visit_orm  # noqa: F401
import media.adapter.outbound.orm.media_orm  # noqa: F401
