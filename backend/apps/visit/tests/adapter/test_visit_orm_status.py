"""ORM 의 CHECK 와 부분 색인이 도메인 상태 표에서 나온 것인지 — 상태 이름을 손으로 적은 곳이 다시 생기면 걸린다."""
from sqlalchemy import CheckConstraint, Index

from visit.adapter.outbound.orm.visit_orm import VisitOrm
from visit.domain.state.visit_status import ACTIVE_STATUSES, ALL_STATUSES, STARTED_STATUSES, status_list_sql


def _constraint(name: str) -> str:
    for arg in VisitOrm.__table_args__:
        if isinstance(arg, CheckConstraint) and arg.name == name:
            return str(arg.sqltext)
    raise AssertionError(name)


def _index_where(name: str) -> str:
    for arg in VisitOrm.__table_args__:
        if isinstance(arg, Index) and arg.name == name:
            return str(arg.dialect_options["postgresql"]["where"])
    raise AssertionError(name)


def test_상태_CHECK_는_표의_모든_상태를_담는다():
    assert _constraint("ck_visits_status") == f"status IN ({status_list_sql(ALL_STATUSES)})"


def test_시작_시각_CHECK_는_시작_시각이_있는_상태만_담는다():
    assert _constraint("ck_visits_started_at") == (
        f"(status IN ({status_list_sql(STARTED_STATUSES)})) = (started_at IS NOT NULL)"
    )


def test_중복_예약_부분_색인은_살아_있는_상태만_담는다():
    active = f"status IN ({status_list_sql(ACTIVE_STATUSES)})"
    assert _index_where("uq_visits_pet_start_active") == f"pet_id IS NOT NULL AND {active}"
    assert _index_where("uq_visits_customer_start_active") == f"pet_id IS NULL AND {active}"
