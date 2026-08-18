import csv
import io
from enum import Enum
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models import SuperstoreSale
from app.schemas import (
    AggregateFunction,
    AggregateRequest,
    AggregateResponse,
    AggregateRow,
    GroupableColumn,
    SaleListResponse,
    SaleRead,
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


class SortableColumn(str, Enum):
    """Whitelist of columns that the client is allowed to sort by."""

    id = "id"
    ship_mode = "ship_mode"
    segment = "segment"
    city = "city"
    state = "state"
    region = "region"
    category = "category"
    sub_category = "sub_category"
    sales = "sales"
    quantity = "quantity"
    discount = "discount"
    profit = "profit"


# Map SortableColumn → ORM attribute
_SORT_COL_MAP: dict[SortableColumn, object] | None = None


def _get_sort_col(col: SortableColumn):
    global _SORT_COL_MAP
    if _SORT_COL_MAP is None:
        _SORT_COL_MAP = {
            SortableColumn.id: SuperstoreSale.id,
            SortableColumn.ship_mode: SuperstoreSale.ship_mode,
            SortableColumn.segment: SuperstoreSale.segment,
            SortableColumn.city: SuperstoreSale.city,
            SortableColumn.state: SuperstoreSale.state,
            SortableColumn.region: SuperstoreSale.region,
            SortableColumn.category: SuperstoreSale.category,
            SortableColumn.sub_category: SuperstoreSale.sub_category,
            SortableColumn.sales: SuperstoreSale.sales,
            SortableColumn.quantity: SuperstoreSale.quantity,
            SortableColumn.discount: SuperstoreSale.discount,
            SortableColumn.profit: SuperstoreSale.profit,
        }
    return _SORT_COL_MAP[col]


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
    id: int | None = Query(default=None, description="Filter by exact row ID", ge=1),
    id_from: int | None = Query(
        default=None, description="ID range start (inclusive)", ge=1
    ),
    id_to: int | None = Query(
        default=None, description="ID range end (inclusive)", ge=1
    ),
    ship_mode: str | None = Query(
        default=None, description="Filter by exact ship mode"
    ),
    segment: str | None = Query(default=None, description="Filter by exact segment"),
    country: str | None = Query(default=None, description="Filter by exact country"),
    city: str | None = Query(default=None, description="Filter by exact city"),
    state: str | None = Query(default=None, description="Filter by state"),
    region: str | None = Query(default=None, description="Filter by exact region"),
    category: str | None = Query(default=None, description="Filter by exact category"),
    sub_category: str | None = Query(
        default=None, description="Filter by exact sub-category"
    ),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: SortableColumn = Query(
        default=SortableColumn.id, description="Column to sort by"
    ),
    sort_dir: Literal["asc", "desc"] = Query(
        default="asc", description="Sort direction"
    ),
    session: AsyncSession = Depends(get_session),
) -> SaleListResponse:
    """
    List raw sale rows with optional filters, returning rows + total count.

    Filters are bound as parameters via SQLAlchemy (.where(col == value)),
    never string-interpolated, so this is safe against SQL injection.
    """
    base_stmt = select(SuperstoreSale)
    count_stmt = select(func.count(SuperstoreSale.id))

    # Exact ID match (indexed primary key — very fast)
    if id is not None:
        base_stmt = base_stmt.where(SuperstoreSale.id == id)
        count_stmt = count_stmt.where(SuperstoreSale.id == id)

    # ID range filter (BETWEEN id_from AND id_to)
    if id_from is not None:
        base_stmt = base_stmt.where(SuperstoreSale.id >= id_from)
        count_stmt = count_stmt.where(SuperstoreSale.id >= id_from)
    if id_to is not None:
        base_stmt = base_stmt.where(SuperstoreSale.id <= id_to)
        count_stmt = count_stmt.where(SuperstoreSale.id <= id_to)

    # Case-insensitive exact filters on text columns
    text_filters = {
        SuperstoreSale.ship_mode: ship_mode,
        SuperstoreSale.segment: segment,
        SuperstoreSale.country: country,
        SuperstoreSale.city: city,
        SuperstoreSale.state: state,
        SuperstoreSale.region: region,
        SuperstoreSale.category: category,
        SuperstoreSale.sub_category: sub_category,
    }
    for column, value in text_filters.items():
        if value is not None:
            base_stmt = base_stmt.where(func.lower(column) == value.lower())
            count_stmt = count_stmt.where(func.lower(column) == value.lower())

    # Total count (for pagination indicator)
    total: int = (await session.execute(count_stmt)).scalar_one()

    # Paginated rows
    sort_col = _get_sort_col(sort_by)
    sort_expr = asc(sort_col) if sort_dir == "asc" else desc(sort_col)
    rows_stmt = base_stmt.order_by(sort_expr).offset(offset).limit(limit)
    result = await session.execute(rows_stmt)
    rows = result.scalars().all()

    has_active_filters = (
        id is not None
        or id_from is not None
        or id_to is not None
        or any(v is not None for v in text_filters.values())
    )
    if not rows and has_active_filters:
        raise HTTPException(status_code=404, detail="No rows matched the given filters")

    return SaleListResponse(
        total=total,
        data=[SaleRead.model_validate(row) for row in rows],
    )


@router.get("/rows/export", status_code=200)
async def export_rows_csv(
    id: int | None = Query(default=None, description="Filter by exact row ID", ge=1),
    id_from: int | None = Query(
        default=None, description="ID range start (inclusive)", ge=1
    ),
    id_to: int | None = Query(
        default=None, description="ID range end (inclusive)", ge=1
    ),
    ship_mode: str | None = Query(
        default=None, description="Filter by exact ship mode"
    ),
    segment: str | None = Query(default=None, description="Filter by exact segment"),
    country: str | None = Query(default=None, description="Filter by exact country"),
    city: str | None = Query(default=None, description="Filter by exact city"),
    state: str | None = Query(default=None, description="Filter by state"),
    region: str | None = Query(default=None, description="Filter by exact region"),
    category: str | None = Query(default=None, description="Filter by exact category"),
    sub_category: str | None = Query(
        default=None, description="Filter by exact sub-category"
    ),
    sort_by: SortableColumn = Query(
        default=SortableColumn.id, description="Column to sort by"
    ),
    sort_dir: Literal["asc", "desc"] = Query(
        default="asc", description="Sort direction"
    ),
    session: AsyncSession = Depends(get_session),
    _current_user=Depends(get_current_user),
):
    """Export all rows matching the given filters as a CSV file (no pagination)."""
    stmt = select(SuperstoreSale)

    if id is not None:
        stmt = stmt.where(SuperstoreSale.id == id)
    if id_from is not None:
        stmt = stmt.where(SuperstoreSale.id >= id_from)
    if id_to is not None:
        stmt = stmt.where(SuperstoreSale.id <= id_to)

    text_filters = {
        SuperstoreSale.ship_mode: ship_mode,
        SuperstoreSale.segment: segment,
        SuperstoreSale.country: country,
        SuperstoreSale.city: city,
        SuperstoreSale.state: state,
        SuperstoreSale.region: region,
        SuperstoreSale.category: category,
        SuperstoreSale.sub_category: sub_category,
    }
    for column, value in text_filters.items():
        if value is not None:
            stmt = stmt.where(func.lower(column) == value.lower())

    sort_col = _get_sort_col(sort_by)
    sort_expr = asc(sort_col) if sort_dir == "asc" else desc(sort_col)
    stmt = stmt.order_by(sort_expr)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    # Stream CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "ship_mode", "segment", "country", "city", "state",
        "postal_code", "region", "category", "sub_category",
        "sales", "quantity", "discount", "profit",
    ])
    for row in rows:
        writer.writerow([
            row.id, row.ship_mode, row.segment, row.country, row.city,
            row.state, row.postal_code, row.region, row.category,
            row.sub_category, row.sales, row.quantity, row.discount, row.profit,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=superstore_export.csv"},
    )


@router.get("/columns/groupable", response_model=list[GroupableColumn])
async def list_groupable_columns() -> list[GroupableColumn]:
    return list(GroupableColumn)


@router.get("/values/{column}", response_model=list[str], status_code=200)
async def list_column_values(
    column: GroupableColumn,
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Return all distinct values for a given column, sorted alphabetically."""
    col_attr = getattr(SuperstoreSale, column.value)
    stmt = (
        select(col_attr)
        .where(col_attr.is_not(None))
        .distinct()
        .order_by(col_attr.asc())
    )
    result = await session.execute(stmt)
    return [
        str(val)
        for val in result.scalars().all()
        if val is not None and str(val).strip()
    ]
