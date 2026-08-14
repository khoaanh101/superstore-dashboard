"""
test_query.py — Integration tests for /query/* endpoints.

Endpoints tested:
  POST /query/aggregate
  GET  /query/summary
  GET  /query/rows
  GET  /query/columns/groupable
  GET  /query/values/{column}

All endpoints require authentication (enforced at router registration in main.py).

"""

from __future__ import annotations

import statistics
from collections import defaultdict

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SuperstoreSale, User
from tests.helpers import auth_headers

pytestmark = pytest.mark.asyncio


# ── seed helpers ──────────────────────────────────────────────────────────────


def _make_sale(**overrides) -> SuperstoreSale:
    defaults = dict(
        ship_mode="Standard Class",
        segment="Consumer",
        country="United States",
        city="Los Angeles",
        state="California",
        region="West",
        category="Technology",
        sub_category="Phones",
        sales=100.0,
        quantity=1,
        discount=0.0,
        profit=20.0,
    )
    return SuperstoreSale(**{**defaults, **overrides})


@pytest_asyncio.fixture()
async def seeded_sales(db_session: AsyncSession):
    """Insert a small, predictable dataset for query tests."""
    sales = [
        _make_sale(region="West",  category="Technology",      sales=300.0, profit=60.0),
        _make_sale(region="West",  category="Furniture",       sales=200.0, profit=40.0),
        _make_sale(region="East",  category="Technology",      sales=150.0, profit=30.0),
        _make_sale(region="East",  category="Office Supplies", sales=100.0, profit=10.0),
        _make_sale(region="South", category="Technology",      sales=50.0,  profit=5.0),
    ]
    for s in sales:
        db_session.add(s)
    await db_session.commit()
    return sales


# ── aggregate helpers ─────────────────────────────────────────────────────────


def _group_values(
    sales: list[SuperstoreSale], group_col: str, metric: str
) -> dict[str, list[float]]:
    """Collect all metric values per group key."""
    groups: dict[str, list[float]] = defaultdict(list)
    for s in sales:
        groups[str(getattr(s, group_col))].append(float(getattr(s, metric)))
    return dict(groups)


def _agg(sales: list[SuperstoreSale], group_col: str, metric: str, func: str) -> dict[str, float]:
    """Compute GROUP BY + aggregate (sum/avg/min/max/count) from the fixture list."""
    groups = _group_values(sales, group_col, metric)
    agg_fn = {
        "sum":   sum,
        "avg":   statistics.mean,
        "min":   min,
        "max":   max,
        "count": len,
    }[func]
    return {k: float(agg_fn(v)) for k, v in groups.items()}


# ════════════════════════════════════════════════════════════════
# 0. Auth guard (all endpoints require a token)
# ════════════════════════════════════════════════════════════════


async def test_query_requires_auth_summary(client: AsyncClient):
    resp = await client.get("/query/summary")
    assert resp.status_code == 401


async def test_query_requires_auth_aggregate(client: AsyncClient):
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "region", "metric": "sales"},
    )
    assert resp.status_code == 401


async def test_query_requires_auth_rows(client: AsyncClient):
    resp = await client.get("/query/rows")
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════
# 1. GET /query/summary
# ════════════════════════════════════════════════════════════════


async def test_summary_empty_db(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    resp = await client.get("/query/summary", headers=auth_headers(viewer_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_sales"] == 0.0
    assert body["total_profit"] == 0.0
    assert body["order_count"] == 0


async def test_summary_with_data(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.get("/query/summary", headers=auth_headers(viewer_token))
    assert resp.status_code == 200
    body = resp.json()

    expected_sales  = sum(float(s.sales)  for s in seeded_sales)
    expected_profit = sum(float(s.profit) for s in seeded_sales)
    expected_count  = len(seeded_sales)

    assert body["total_sales"]  == pytest.approx(expected_sales)
    assert body["total_profit"] == pytest.approx(expected_profit)
    assert body["order_count"]  == expected_count


# ════════════════════════════════════════════════════════════════
# 2. POST /query/aggregate
# ════════════════════════════════════════════════════════════════


async def test_aggregate_response_schema(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    """Response body must contain group_by, metric, function, and data list."""
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "region", "metric": "sales", "function": "sum"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["group_by"]  == "region"
    assert body["metric"]    == "sales"
    assert body["function"]  == "sum"
    assert isinstance(body["data"], list)
    for row in body["data"]:
        assert "label" in row
        assert "value" in row


async def test_aggregate_sum_by_region(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "region", "metric": "sales", "function": "sum"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    labels = {row["label"]: row["value"] for row in resp.json()["data"]}
    expected = _agg(seeded_sales, "region", "sales", "sum")
    assert set(labels.keys()) == set(expected.keys())
    for key, val in expected.items():
        assert labels[key] == pytest.approx(val)


async def test_aggregate_sum_by_category(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "category", "metric": "profit", "function": "sum"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    labels = {row["label"]: row["value"] for row in resp.json()["data"]}
    expected = _agg(seeded_sales, "category", "profit", "sum")
    assert set(labels.keys()) == set(expected.keys())
    for key, val in expected.items():
        assert labels[key] == pytest.approx(val)


async def test_aggregate_count_by_category(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "category", "metric": "sales", "function": "count"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    labels = {row["label"]: int(row["value"]) for row in resp.json()["data"]}
    expected = _agg(seeded_sales, "category", "sales", "count")
    assert set(labels.keys()) == set(expected.keys())
    for key, val in expected.items():
        assert labels[key] == int(val)


async def test_aggregate_avg_by_region(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "region", "metric": "sales", "function": "avg"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    labels = {row["label"]: row["value"] for row in resp.json()["data"]}
    expected = _agg(seeded_sales, "region", "sales", "avg")
    assert set(labels.keys()) == set(expected.keys())
    for key, val in expected.items():
        assert labels[key] == pytest.approx(val)


async def test_aggregate_invalid_group_by(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "not_a_column", "metric": "sales"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 422


async def test_aggregate_invalid_function(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "region", "metric": "sales", "function": "median"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 422


async def test_aggregate_limit_returns_at_most_n_rows(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    """limit=1 should return exactly 1 row."""
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "region", "metric": "sales", "function": "sum", "limit": 1},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


async def test_aggregate_limit_returns_top_row(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    """limit=1 must return the group with the highest aggregated value (desc order)."""
    resp = await client.post(
        "/query/aggregate",
        json={"group_by": "region", "metric": "sales", "function": "sum", "limit": 1},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    top_label = resp.json()["data"][0]["label"]
    expected = _agg(seeded_sales, "region", "sales", "sum")
    best = max(expected, key=lambda k: expected[k])
    assert top_label == best


# ════════════════════════════════════════════════════════════════
# 3. GET /query/rows
# ════════════════════════════════════════════════════════════════


async def test_list_rows_no_filter(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.get("/query/rows", headers=auth_headers(viewer_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(seeded_sales)
    assert len(body["data"]) == len(seeded_sales)


async def test_list_rows_filter_by_region(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    filter_region = "West"
    resp = await client.get(
        f"/query/rows?region={filter_region}", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 200
    body = resp.json()

    expected_count = sum(1 for s in seeded_sales if s.region == filter_region)
    assert body["total"] == expected_count
    assert all(row["region"] == filter_region for row in body["data"])


async def test_list_rows_filter_by_category(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    filter_category = "Technology"
    resp = await client.get(
        f"/query/rows?category={filter_category}", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 200
    body = resp.json()

    expected_count = sum(1 for s in seeded_sales if s.category == filter_category)
    assert body["total"] == expected_count
    assert all(row["category"] == filter_category for row in body["data"])


async def test_list_rows_filter_no_match(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.get(
        "/query/rows?region=NonExistentRegion", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 404


async def test_list_rows_pagination_limit(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    """limit=2 returns only 2 rows but total reflects the full count."""
    page_size = 2
    resp = await client.get(
        f"/query/rows?limit={page_size}&offset=0", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(seeded_sales)
    assert len(body["data"]) == page_size


async def test_list_rows_pagination_offset(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    """offset beyond total should return empty data but correct total."""
    resp = await client.get(
        f"/query/rows?offset={len(seeded_sales)}", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(seeded_sales)
    assert body["data"] == []


async def test_list_rows_empty_db(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    """When there are no rows and no filters, return 200 with empty list."""
    resp = await client.get("/query/rows", headers=auth_headers(viewer_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["data"] == []


# ════════════════════════════════════════════════════════════════
# 4. GET /query/columns/groupable
# ════════════════════════════════════════════════════════════════


async def test_list_groupable_columns(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    resp = await client.get(
        "/query/columns/groupable", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 200
    columns = resp.json()
    assert isinstance(columns, list)
    # These columns must always be present (they are part of the enum)
    for expected_col in ("region", "category", "segment", "state", "city"):
        assert expected_col in columns


# ════════════════════════════════════════════════════════════════
# 5. GET /query/values/{column}
# ════════════════════════════════════════════════════════════════


async def test_list_column_values(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    resp = await client.get(
        "/query/values/region", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 200
    values = resp.json()
    assert isinstance(values, list)

    expected_regions = {str(s.region) for s in seeded_sales}
    assert set(values) == expected_regions


async def test_list_column_values_sorted(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
):
    """Distinct column values must be returned in alphabetical order."""
    resp = await client.get(
        "/query/values/category", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 200
    values = resp.json()
    assert values == sorted(values)


async def test_list_column_values_invalid_column(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    resp = await client.get(
        "/query/values/not_a_column", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 422
