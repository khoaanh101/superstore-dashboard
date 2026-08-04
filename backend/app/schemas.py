from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums — whitelists that map directly to real ORM columns.
# Using an Enum means FastAPI validates input automatically (422 on bad value)
# and the value can never be used to build a raw/unsafe SQL fragment.
# ---------------------------------------------------------------------------


class GroupableColumn(str, Enum):
    SHIP_MODE = "ship_mode"
    SEGMENT = "segment"
    COUNTRY = "country"
    CITY = "city"
    STATE = "state"
    REGION = "region"
    CATEGORY = "category"
    SUB_CATEGORY = "sub_category"


class AggregatableColumn(str, Enum):
    SALES = "sales"
    QUANTITY = "quantity"
    DISCOUNT = "discount"
    PROFIT = "profit"


class AggregateFunction(str, Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"


class ChartType(str, Enum):
    SALES_BY_CATEGORY = "sales_by_category"
    SALES_BY_REGION = "sales_by_region"
    SALES_BY_SEGMENT = "sales_by_segment"
    SALES_BY_STATE = "sales_by_state"
    PROFIT_BY_SUBCATEGORY = "profit_by_subcategory"
    PROFIT_BY_CATEGORY = "profit_by_category"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ChartDataPoint(BaseModel):
    label: str
    value: float


class ChartResponse(BaseModel):
    chart_type: ChartType
    data: list[ChartDataPoint]


class AggregateRequest(BaseModel):
    """Request body for the generic /query/aggregate endpoint."""

    group_by: GroupableColumn
    metric: AggregatableColumn
    function: AggregateFunction = AggregateFunction.SUM
    limit: int = Field(default=20, ge=1, le=100)


class AggregateRow(BaseModel):
    label: str
    value: float


class AggregateResponse(BaseModel):
    group_by: GroupableColumn
    metric: AggregatableColumn
    function: AggregateFunction
    data: list[AggregateRow]


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    id: int
    email: str
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str



class SaleRead(BaseModel):
    """Row-level read schema, mirrors the ORM model."""

    id: int
    ship_mode: str
    segment: str
    country: str
    city: str
    state: str
    postal_code: str | None
    region: str
    category: str
    sub_category: str
    sales: float
    quantity: int
    discount: float
    profit: float

    model_config = {"from_attributes": True}


class SaleListResponse(BaseModel):
    """Paginated list of rows with a total count for the pagination indicator."""
    total: int
    data: list[SaleRead]


class SummaryResponse(BaseModel):
    """Aggregated KPI totals computed in a single SQL query."""
    total_sales: float
    total_profit: float
    order_count: int
