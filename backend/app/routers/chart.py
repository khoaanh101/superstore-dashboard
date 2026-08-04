from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import SuperstoreSale
from app.schemas import ChartDataPoint, ChartResponse, ChartType

router = APIRouter(prefix="/chart", tags=["chart"])

# Maps each public chart_type to (group column, aggregated column).
# Keeping this as a lookup table (instead of if/elif) makes adding a new
# chart a one-line change: add to ChartType enum + this dict.
_CHART_CONFIG: dict[ChartType, tuple] = {
    ChartType.SALES_BY_CATEGORY: (SuperstoreSale.category, SuperstoreSale.sales),
    ChartType.SALES_BY_REGION: (SuperstoreSale.region, SuperstoreSale.sales),
    ChartType.SALES_BY_SEGMENT: (SuperstoreSale.segment, SuperstoreSale.sales),
    ChartType.SALES_BY_STATE: (SuperstoreSale.state, SuperstoreSale.sales),
    ChartType.PROFIT_BY_SUBCATEGORY: (SuperstoreSale.sub_category, SuperstoreSale.profit),
    ChartType.PROFIT_BY_CATEGORY: (SuperstoreSale.category, SuperstoreSale.profit),
}


@router.get("/types", response_model=list[ChartType])
async def list_chart_types() -> list[ChartType]:
    """Return all chart types the frontend can request, e.g. to build a dropdown."""
    return list(ChartType)


@router.get("", response_model=ChartResponse, status_code=200)
async def get_chart(
    chart_type: ChartType = Query(..., title="Chart type"),
    limit: int = Query(20, ge=1, le=100, description="Max number of groups returned"),
    state: str | None = Query(default=None, description="Filter by exact state"),
    region: str | None = Query(default=None, description="Filter by exact region"),
    category: str | None = Query(default=None, description="Filter by exact category"),
    segment: str | None = Query(default=None, description="Filter by exact segment"),
    session: AsyncSession = Depends(get_session),
) -> ChartResponse:
    """Get aggregated chart data for the Superstore dataset.

    All filter values are bound as query parameters via SQLAlchemy (.where(col == value)),
    never string-interpolated, so this is safe against SQL injection.
    """
    group_col, agg_col = _CHART_CONFIG[chart_type]
    value_expr = func.sum(agg_col)

    stmt = (
        select(group_col.label("label"), value_expr.label("value"))
        .group_by(group_col)
    )

    # Apply optional filters (bound safely, never interpolated into raw SQL)
    filter_map = {
        SuperstoreSale.state: state,
        SuperstoreSale.region: region,
        SuperstoreSale.category: category,
        SuperstoreSale.segment: segment,
    }
    for col, val in filter_map.items():
        if val is not None:
            stmt = stmt.where(func.lower(col) == val.lower())

    stmt = stmt.order_by(value_expr.desc()).limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    return ChartResponse(
        chart_type=chart_type,
        data=[ChartDataPoint(label=r.label, value=float(r.value)) for r in rows],
    )
