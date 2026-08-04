from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import SuperstoreSale
from app.schemas import (
    AggregateFunction,
    AggregateRequest,
    AggregateResponse,
    AggregateRow,
    GroupableColumn,
    SaleRead,
    SaleListResponse,
    SummaryResponse,
)

router = APIRouter(prefix="/query", tags=["query"])

# Whitelisted function map — never build SQL functions from a raw string.
_FUNCTION_MAP = {
    AggregateFunction.SUM: func.sum,
    AggregateFunction.AVG: func.avg,
    AggregateFunction.MIN: func.min,
    AggregateFunction.MAX: func.max,
    AggregateFunction.COUNT: func.count,
}


@router.post("/aggregate", response_model=AggregateResponse, status_code=200)
async def aggregate_query(
    payload: AggregateRequest,
    session: AsyncSession = Depends(get_session),
) -> AggregateResponse:
    """
    Generic GROUP BY / aggregate endpoint.

    Both `group_by` and `metric` are Pydantic Enums bound to whitelisted
    ORM columns, and `function` maps to a fixed set of SQLAlchemy func
    callables — so no user-supplied string ever reaches raw SQL.
    """
    group_col = getattr(SuperstoreSale, payload.group_by.value)
    metric_col = getattr(SuperstoreSale, payload.metric.value)
    agg_func = _FUNCTION_MAP[payload.function]
    value_expr = agg_func(metric_col)

    stmt = (
        select(group_col.label("label"), value_expr.label("value"))
        .group_by(group_col)
        .order_by(value_expr.desc())
        .limit(payload.limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return AggregateResponse(
        group_by=payload.group_by,
        metric=payload.metric,
        function=payload.function,
        data=[AggregateRow(label=str(r.label), value=float(r.value)) for r in rows],
    )


@router.get("/summary", response_model=SummaryResponse, status_code=200)
async def get_summary(
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    """
    Return total sales, total profit and order count in a single SQL query.
    More accurate than aggregating per-group and summing client-side.
    """
    stmt = select(
        func.sum(SuperstoreSale.sales).label("total_sales"),
        func.sum(SuperstoreSale.profit).label("total_profit"),
        func.count(SuperstoreSale.id).label("order_count"),
    )
    result = await session.execute(stmt)
    row = result.one()
    return SummaryResponse(
        total_sales=float(row.total_sales or 0),
        total_profit=float(row.total_profit or 0),
        order_count=int(row.order_count or 0),
    )


@router.get("/rows", response_model=SaleListResponse, status_code=200)
async def list_rows(
    ship_mode: str | None = Query(default=None, description="Filter by exact ship mode"),
    segment: str | None = Query(default=None, description="Filter by exact segment"),
    country: str | None = Query(default=None, description="Filter by exact country"),
    city: str | None = Query(default=None, description="Filter by exact city"),
    state: str | None = Query(default=None, description="Filter by state"),
    region: str | None = Query(default=None, description="Filter by exact region"),
    category: str | None = Query(default=None, description="Filter by exact category"),
    sub_category: str | None = Query(default=None, description="Filter by exact sub-category"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> SaleListResponse:
    """
    List raw sale rows with optional filters, returning rows + total count.

    Filters are bound as parameters via SQLAlchemy (.where(col == value)),
    never string-interpolated, so this is safe against SQL injection.
    """
    filters = {
        SuperstoreSale.ship_mode: ship_mode,
        SuperstoreSale.segment: segment,
        SuperstoreSale.country: country,
        SuperstoreSale.city: city,
        SuperstoreSale.state: state,
        SuperstoreSale.region: region,
        SuperstoreSale.category: category,
        SuperstoreSale.sub_category: sub_category,
    }

    base_stmt = select(SuperstoreSale)
    count_stmt = select(func.count(SuperstoreSale.id))
    for column, value in filters.items():
        if value is not None:
            base_stmt  = base_stmt.where(func.lower(column) == value.lower())
            count_stmt = count_stmt.where(func.lower(column) == value.lower())

    # Total count (for pagination indicator)
    total: int = (await session.execute(count_stmt)).scalar_one()

    # Paginated rows
    rows_stmt = base_stmt.offset(offset).limit(limit)
    result = await session.execute(rows_stmt)
    rows = result.scalars().all()

    has_active_filters = any(value is not None for value in filters.values())
    if not rows and has_active_filters:
        raise HTTPException(status_code=404, detail="No rows matched the given filters")

    return SaleListResponse(
        total=total,
        data=[SaleRead.model_validate(row) for row in rows],
    )


@router.get("/columns/groupable", response_model=list[GroupableColumn])
async def list_groupable_columns() -> list[GroupableColumn]:
    return list(GroupableColumn)
