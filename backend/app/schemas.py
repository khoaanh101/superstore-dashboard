from enum import Enum
from typing import Optional

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
    SALES_BY_SHIP_MODE = "sales_by_ship_mode"
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


class UserRole(str, Enum):
    VIEWER = "viewer"
    ADMIN = "admin"


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    id: int
    email: str
    is_active: bool
    role: UserRole

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


class SaleCreate(BaseModel):
    """Payload for creating a new sale order (admin only)."""
    ship_mode: str
    segment: str
    country: str
    city: str
    state: str
    postal_code: Optional[str] = None
    region: str
    category: str
    sub_category: str
    sales: float = Field(ge=0)
    quantity: int = Field(ge=1)
    discount: float = Field(ge=0, le=1)
    profit: float


class SaleUpdate(BaseModel):
    """Partial update payload — all fields optional (admin only)."""
    ship_mode: Optional[str] = None
    segment: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    region: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    sales: Optional[float] = Field(default=None, ge=0)
    quantity: Optional[int] = Field(default=None, ge=1)
    discount: Optional[float] = Field(default=None, ge=0, le=1)
    profit: Optional[float] = None


class SaleListResponse(BaseModel):
    """Paginated list of rows with a total count for the pagination indicator."""
    total: int
    data: list[SaleRead]


class SummaryResponse(BaseModel):
    """Aggregated KPI totals computed in a single SQL query."""
    total_sales: float
    total_profit: float
    order_count: int
