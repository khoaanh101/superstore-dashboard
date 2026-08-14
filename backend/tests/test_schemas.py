"""
test_schemas.py — Unit tests for Pydantic schemas in app/schemas.py.
No database or HTTP client is needed; all tests are synchronous.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    AggregateFunction,
    AggregateRequest,
    AggregatableColumn,
    ChartType,
    GroupableColumn,
    SaleCreate,
    SaleUpdate,
    SummaryResponse,
    UserCreate,
    UserRead,
    UserRole,
)


# ════════════════════════════════════════════════════════════════
# 1. UserCreate
# ════════════════════════════════════════════════════════════════


def test_user_create_valid():
    u = UserCreate(email="test@example.com", password="strongpass")
    assert u.email == "test@example.com"
    assert u.password == "strongpass"


def test_user_create_password_too_short():
    """Password must be at least 8 characters."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(email="a@b.com", password="short")
    assert "min_length" in str(exc_info.value) or "8" in str(exc_info.value)


def test_user_create_empty_password():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password="")


# ════════════════════════════════════════════════════════════════
# 2. SaleCreate
# ════════════════════════════════════════════════════════════════

VALID_SALE = dict(
    ship_mode="Standard Class",
    segment="Consumer",
    country="United States",
    city="Los Angeles",
    state="California",
    region="West",
    category="Technology",
    sub_category="Phones",
    sales=250.0,
    quantity=2,
    discount=0.1,
    profit=50.0,
)


def test_sale_create_valid():
    sale = SaleCreate(**VALID_SALE)
    assert sale.sales == 250.0
    assert sale.discount == 0.1


def test_sale_create_discount_above_one():
    """discount must be ≤ 1 (i.e. ≤ 100%)."""
    with pytest.raises(ValidationError):
        SaleCreate(**{**VALID_SALE, "discount": 1.5})


def test_sale_create_discount_negative():
    """discount must be ≥ 0."""
    with pytest.raises(ValidationError):
        SaleCreate(**{**VALID_SALE, "discount": -0.1})


def test_sale_create_quantity_zero():
    """quantity must be ≥ 1."""
    with pytest.raises(ValidationError):
        SaleCreate(**{**VALID_SALE, "quantity": 0})


def test_sale_create_sales_negative():
    """sales must be ≥ 0."""
    with pytest.raises(ValidationError):
        SaleCreate(**{**VALID_SALE, "sales": -1.0})


def test_sale_create_optional_postal_code():
    """postal_code is optional; omitting it should not raise."""
    data = {k: v for k, v in VALID_SALE.items() if k != "postal_code"}
    sale = SaleCreate(**data)
    assert sale.postal_code is None


# ════════════════════════════════════════════════════════════════
# 3. SaleUpdate (partial update)
# ════════════════════════════════════════════════════════════════


def test_sale_update_all_optional():
    """Empty SaleUpdate is valid — all fields are optional."""
    update = SaleUpdate()
    assert update.sales is None
    assert update.city is None


def test_sale_update_partial():
    """Only the provided fields are set; the rest remain None."""
    update = SaleUpdate(city="New York", quantity=5)
    assert update.city == "New York"
    assert update.quantity == 5
    assert update.sales is None


def test_sale_update_discount_validation():
    """Discount constraints still apply even in partial update."""
    with pytest.raises(ValidationError):
        SaleUpdate(discount=2.0)


# ════════════════════════════════════════════════════════════════
# 4. AggregateRequest
# ════════════════════════════════════════════════════════════════


def test_aggregate_request_defaults():
    req = AggregateRequest(group_by=GroupableColumn.REGION, metric=AggregatableColumn.SALES)
    assert req.function == AggregateFunction.SUM
    assert req.limit == 20


def test_aggregate_request_limit_zero():
    with pytest.raises(ValidationError):
        AggregateRequest(
            group_by=GroupableColumn.REGION,
            metric=AggregatableColumn.SALES,
            limit=0,
        )


def test_aggregate_request_limit_too_large():
    with pytest.raises(ValidationError):
        AggregateRequest(
            group_by=GroupableColumn.REGION,
            metric=AggregatableColumn.SALES,
            limit=101,
        )


def test_aggregate_request_invalid_group_by():
    """Random string is not a valid GroupableColumn."""
    with pytest.raises(ValidationError):
        AggregateRequest(group_by="not_a_column", metric=AggregatableColumn.SALES)


# ════════════════════════════════════════════════════════════════
# 5. SummaryResponse
# ════════════════════════════════════════════════════════════════


def test_summary_response_valid():
    s = SummaryResponse(total_sales=1000.5, total_profit=200.0, order_count=42)
    assert s.total_sales == 1000.5
    assert s.order_count == 42


def test_summary_response_zero_values():
    s = SummaryResponse(total_sales=0.0, total_profit=0.0, order_count=0)
    assert s.total_profit == 0.0


# ════════════════════════════════════════════════════════════════
# 6. Enums
# ════════════════════════════════════════════════════════════════


def test_groupable_column_values():
    assert GroupableColumn.REGION == "region"
    assert GroupableColumn.CATEGORY == "category"


def test_aggregate_function_values():
    assert AggregateFunction.SUM == "sum"
    assert AggregateFunction.COUNT == "count"


def test_chart_type_values():
    assert ChartType.SALES_BY_CATEGORY == "sales_by_category"


def test_user_role_values():
    assert UserRole.ADMIN == "admin"
    assert UserRole.VIEWER == "viewer"
